"""Klien LLM/VLM (vLLM, API kompatibel OpenAI) + LLM tiruan untuk mode tanpa GPU.

Konsistensi (desain §4.6 lapis 1): temperatur 0, seed tetap, prompt berversi, keluaran JSON
dipaksa skema (guided decoding). Lapis 2 (fingerprint) ada di pipeline review.
Panggilan hanya ke `LLM_URL` (jaringan internal / terowongan WireGuard) — tidak ada layanan eksternal.
"""
import base64
import hashlib
import json
import logging
import re
import time

import httpx

from app.konfigurasi import konfigurasi
from app.log import log
from app.pekerja.prompt import PROMPT_VERSI, SISTEM

logger = logging.getLogger("pekerja.llm")


class GalatLLM(Exception):
    pass


def info_model() -> dict:
    """Dicatat di setiap review (PRD §8.2) dan masuk fingerprint."""
    k = konfigurasi()
    return {"model": "ai-tiruan" if k.tiruan else k.llm_model, "profil": k.profil, "ai_mode": k.ai_mode,
            "prompt_versi": PROMPT_VERSI, "embedding": "hash-tiruan" if k.tiruan else k.embedding_model,
            "reranker": "leksikal-tiruan" if k.tiruan else k.reranker_model, "ekstraktor": k.ekstraktor}


class KlienLLM:
    def __init__(self):
        k = konfigurasi()
        self.k = k
        self.http = httpx.Client(base_url=k.llm_url, timeout=k.llm_timeout_detik)

    def json(self, tugas: str, prompt: str, skema: dict, gambar: bytes | None = None, konteks: dict | None = None) -> dict:
        """Panggil LLM dan kembalikan objek JSON sesuai `skema`. Diulang hingga 3× untuk error sementara.

        Error: GalatLLM bila LLM tidak dapat dihubungi atau keluaran tidak valid setelah percobaan ulang.
        """
        isi: list | str = prompt
        if gambar is not None:
            isi = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(gambar).decode()}},
                   {"type": "text", "text": prompt}]
        badan = {
            "model": self.k.llm_model, "temperature": 0, "seed": self.k.llm_seed, "max_tokens": self.k.llm_maks_token,
            "messages": [{"role": "system", "content": SISTEM}, {"role": "user", "content": isi}],
            "response_format": {"type": "json_schema", "json_schema": {"name": tugas, "schema": skema, "strict": True}},
        }
        galat = None
        for percobaan in range(1, 4):
            mulai = time.monotonic()
            try:
                r = self.http.post("/chat/completions", json=badan)
                r.raise_for_status()
                data = r.json()
                teks = data["choices"][0]["message"]["content"] or ""
                teks = re.sub(r"^.*?</think>", "", teks, flags=re.S).strip()  # bila reasoning parser tidak aktif
                hasil = json.loads(teks)
                pakai = data.get("usage", {})
                log(logger, logging.INFO, "panggilan llm", tugas=tugas, durasi_ms=int((time.monotonic() - mulai) * 1000),
                    token_masuk=pakai.get("prompt_tokens"), token_keluar=pakai.get("completion_tokens"), panjang_prompt=len(prompt))
                return hasil
            except (httpx.HTTPError, KeyError, ValueError) as e:
                galat = e
                log(logger, logging.WARNING, "panggilan llm gagal", tugas=tugas, percobaan=percobaan, error=type(e).__name__,
                    detail=str(e)[:300])
                time.sleep(min(30, 5 * percobaan))
        raise GalatLLM(f"LLM tidak memberikan jawaban valid untuk tugas {tugas}: {type(galat).__name__}")


class LLMTiruan:
    """Jawaban AI tiruan yang tetap (deterministik) untuk developer tanpa GPU dan uji otomatis.
    Memakai konteks yang sama dengan LLM sungguhan sehingga seluruh alur (rujukan, verifikasi, UI) teruji."""

    @staticmethod
    def _h(*bagian) -> int:
        return int(hashlib.sha256("|".join(map(str, bagian)).encode()).hexdigest(), 16)

    @staticmethod
    def _rujuk(alias: list[tuple[str, str]], n: int = 1) -> list[dict]:
        return [{"id": a, "kutipan": t[:80]} for a, t in alias[:n] if t.strip()]

    def json(self, tugas: str, prompt: str, skema: dict, gambar: bytes | None = None, konteks: dict | None = None) -> dict:
        k = konteks or {}
        dok, pdn = k.get("alias_dok", []), k.get("alias_panduan", [])
        if tugas == "nilai_item":
            if not dok:
                return {"ditemukan": False, "terpenuhi": False, "alasan": "(AI tiruan) Tidak ditemukan bagian dokumen yang relevan.",
                        "yang_kurang": "Bagian yang menjawab kriteria ini belum ada di dokumen.", "bukti": [], "dasar_panduan": []}
            ok = self._h(k.get("kode"), dok[0][1]) % 3 != 0
            return {"ditemukan": True, "terpenuhi": ok,
                    "alasan": f"(AI tiruan) Penilaian item {k.get('kode')} berdasarkan potongan dokumen yang ditemukan.",
                    "yang_kurang": "" if ok else "(AI tiruan) Rincian yang diminta kriteria belum lengkap.",
                    "bukti": self._rujuk(dok, 2), "dasar_panduan": self._rujuk(pdn, 1)}
        if tugas == "sapuan":
            return {"ada": False, "bukti": []}
        if tugas == "keselarasan":
            temuan = [] if self._h(dok[0][1] if dok else "") % 2 else [
                {"jenis": "TIDAK_SELARAS", "uraian": "(AI tiruan) Volume pada RAB perlu diselaraskan dengan kegiatan di TOR.",
                 "bukti": self._rujuk(dok, 1)}]
            return {"ringkasan": "(AI tiruan) Pemeriksaan keselarasan RAB–TOR.", "temuan": temuan}
        if tugas == "rekomendasi":
            return {"rekomendasi": [{"teks": f"(AI tiruan) Lengkapi dokumen sesuai kriteria item {kode}.", "kode_item": kode,
                                     "dasar_panduan": self._rujuk(pdn, 1)} for kode in k.get("kode_item", [])] or
                    [{"teks": "(AI tiruan) Selaraskan komponen biaya dengan kegiatan.", "kode_item": "", "dasar_panduan": []}]}
        if tugas == "kategori":
            kode = k.get("kode", ["K3"])
            return {"kode": kode[self._h(dok[0][1] if dok else "") % len(kode)], "bukti": self._rujuk(dok, 1),
                    "alasan": "(AI tiruan) Kategori dipilih berdasarkan definisi kategori yang aktif.", "dasar_panduan": self._rujuk(pdn, 1)}
        if tugas == "gambar":
            return {"deskripsi": f"(AI tiruan) Gambar/diagram pada halaman {k.get('halaman', '?')}."}
        raise GalatLLM(f"tugas tidak dikenal: {tugas}")


def klien() -> KlienLLM | LLMTiruan:
    return LLMTiruan() if konfigurasi().tiruan else KlienLLM()
