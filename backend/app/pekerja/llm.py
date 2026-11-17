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
    # Versi AI tiruan ikut fingerprint: naikkan bila jawaban tiruan berubah agar hasil lama tidak disalin ke review baru.
    return {"model": "ai-tiruan-7" if k.tiruan else k.llm_model, "profil": k.profil, "ai_mode": k.ai_mode,
            "prompt_versi": PROMPT_VERSI, "embedding": "hash-tiruan" if k.tiruan else k.embedding_model,
            "reranker": "leksikal-tiruan" if k.tiruan else k.reranker_model, "ekstraktor": k.ekstraktor}


_AWAL_TIRUAN = {"lolos": "Dokumen telah menunjukkan bahwa", "kurang": "Dokumen belum sepenuhnya menunjukkan bahwa",
                "tidak_ditemukan": "Belum ditemukan bagian dokumen yang menunjukkan bahwa",
                "saran_kurang": "Lengkapi dokumen agar jelas menunjukkan bahwa",
                "saran_tidak_ditemukan": "Tambahkan uraian pada dokumen yang menunjukkan bahwa"}


def catatan_tiruan(kriteria: str, keadaan: str) -> str:
    """Catatan/rekomendasi AI tiruan yang merujuk Kriteria Lolos item, formal dan komunikatif. `keadaan`: lolos | kurang |
    tidak_ditemukan (Catatan AI), saran_kurang | saran_tidak_ditemukan (Rekomendasi AI).
    Contoh kurang: "Setiap komponen biaya ... pada TOR." → "(AI tiruan) Dokumen belum sepenuhnya menunjukkan bahwa setiap
    komponen biaya ... pada TOR." Huruf awal kriteria dikecilkan kecuali singkatan (TOR, RAB)."""
    k = " ".join(kriteria.split()).rstrip(".")
    if k and not k.split(" ", 1)[0].isupper():
        k = k[0].lower() + k[1:]
    return f"(AI tiruan) {_AWAL_TIRUAN[keadaan]} {k}."


# Tampilan review lama AI tiruan (versi 1–4): kalimat umum yang kini diganti; hasil tersimpan tidak diubah (dipakai layanan_review).
ALASAN_TIRUAN_LAMA = re.compile(r"\(AI tiruan\) Penilaian item .+ berdasarkan potongan dokumen yang ditemukan\.")
REKOMENDASI_TIRUAN_LAMA = re.compile(r"\(AI tiruan\) Lengkapi dokumen sesuai kriteria item .+\.")
KURANG_TIRUAN_LAMA = {"(AI tiruan) Rincian yang diminta kriteria belum lengkap.", "Bagian yang menjawab kriteria ini belum ada di dokumen."}
# Semua versi lama Catatan AI kategori tiruan (kalimat umum, lalu kalimat K4 untuk semua kategori) → ditampilkan versi terbaru.
KATEGORI_TIRUAN_LAMA = re.compile(r"\(AI tiruan\) Kategori .+", re.S)

# Alasan per kategori, mengikuti definisi seed K1–K4 (PRD C1); kategori lain buatan Admin memakai kalimat umum.
_ALASAN_KATEGORI = {
    "K1": "RO bersifat wajib dan mengikat, ditetapkan melalui kebijakan penganggaran nasional, serta perlu terus berjalan "
          "secara berkelanjutan. Oleh karena itu, penilaian difokuskan pada kesesuaian ruang lingkup, kejelasan kebutuhan dasar, "
          "dan keterkaitan komponen dengan RO yang diusulkan.",
    "K2": "RO termasuk prioritas yang ditetapkan secara resmi oleh Menteri dan/atau mendukung penguatan layanan esensial. "
          "Oleh karena itu, RO ini dinilai secara penuh sesuai parameter penilaian substansi.",
    "K3": "RO berkaitan dengan prioritas pembangunan nasional dan sasaran kementerian serta mendukung tugas dan fungsi Satker, "
          "namun belum memenuhi kriteria K1 (RO Wajib) maupun K2 (RO Prioritas Strategis).",
    "K4": "RO tidak termasuk prioritas nasional, serta tidak berkaitan dengan tugas dan fungsi Satker maupun kinerja strategis "
          "kementerian.",
}


def alasan_kategori_tiruan(kode: str, nama: str) -> str:
    """Catatan AI kategori versi AI tiruan, sesuai kategori yang dipilih (desain.md §7 no. 39)."""
    pilihan = f"{kode} — {nama}" if nama else kode
    alasan = _ALASAN_KATEGORI.get(kode, "isi TOR dan RAB paling sesuai dengan definisi kategori ini dibandingkan kategori lain "
                                        "yang berlaku.")
    return f"(AI tiruan) Kategori {pilihan} dipilih karena {alasan}"


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
                        "yang_kurang": catatan_tiruan(k.get("kriteria", ""), "tidak_ditemukan"), "bukti": [], "dasar_panduan": []}
            ok = self._h(k.get("kode"), dok[0][1]) % 3 != 0
            return {"ditemukan": True, "terpenuhi": ok,
                    # Lolos → alasan dari kriteria; tidak lolos → cukup kekurangannya (permintaan pengguna).
                    "alasan": catatan_tiruan(k.get("kriteria", ""), "lolos") if ok else "",
                    "yang_kurang": "" if ok else catatan_tiruan(k.get("kriteria", ""), "kurang"),
                    "bukti": self._rujuk(dok, 2), "dasar_panduan": self._rujuk(pdn, 1)}
        if tugas == "sapuan":
            return {"ada": False, "bukti": []}
        if tugas == "keselarasan":
            temuan = [] if self._h(dok[0][1] if dok else "") % 2 else [
                {"jenis": "TIDAK_SELARAS", "uraian": "(AI tiruan) Volume pada RAB perlu diselaraskan dengan kegiatan di TOR.",
                 "bukti": self._rujuk(dok, 1)}]
            return {"ringkasan": "(AI tiruan) Pemeriksaan keselarasan RAB–TOR.", "temuan": temuan}
        if tugas == "rekomendasi":
            kriteria, ditemukan = k.get("kriteria", {}), k.get("ditemukan", {})
            return {"rekomendasi": [{"teks": catatan_tiruan(kriteria.get(kode, ""), "saran_kurang" if ditemukan.get(kode, True) else "saran_tidak_ditemukan"),
                                     "kode_item": kode, "dasar_panduan": self._rujuk(pdn, 1)} for kode in k.get("kode_item", [])] or
                    [{"teks": "(AI tiruan) Selaraskan komponen biaya dengan kegiatan.", "kode_item": "", "dasar_panduan": []}]}
        if tugas == "kategori":
            kode = k.get("kode", ["K3"])
            pilih = kode[self._h(dok[0][1] if dok else "") % len(kode)]
            return {"kode": pilih, "bukti": self._rujuk(dok, 1),
                    "alasan": alasan_kategori_tiruan(pilih, k.get("nama", {}).get(pilih, "")), "dasar_panduan": self._rujuk(pdn, 1)}
        if tugas == "gambar":
            return {"deskripsi": f"(AI tiruan) Gambar/diagram pada halaman {k.get('halaman', '?')}."}
        raise GalatLLM(f"tugas tidak dikenal: {tugas}")


def klien() -> KlienLLM | LLMTiruan:
    return LLMTiruan() if konfigurasi().tiruan else KlienLLM()
