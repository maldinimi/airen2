"""Verifikasi rujukan — penjaga anti-halusinasi (desain §4.3, PRD E3–E4).

LLM hanya menyebut alias elemen (E1, E2, …) + kutipan. Kode yang memutuskan:
- alias harus ada di konteks yang diberikan untuk tugas tersebut;
- kutipan harus benar-benar ada di teks elemen (setelah normalisasi spasi/tanda baca/huruf);
- kutipan yang disimpan adalah potongan ASLI teks elemen dari database, bukan ketikan LLM;
- halaman, lokasi, bbox selalu dibaca dari tabel elemen.
"""
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model import Elemen, Rujukan

PANJANG_KUTIPAN_DEFAULT = 300
_TANDA = re.compile(r"[^\w]+", re.UNICODE)


def _normal_dengan_peta(teks: str) -> tuple[str, list[int]]:
    """Normalisasi (huruf kecil, tanda baca/spasi → satu spasi) sambil menyimpan peta indeks ke teks asli."""
    keluar: list[str] = []
    peta: list[int] = []
    spasi = True
    for i, ch in enumerate(teks):
        ch = unicodedata.normalize("NFKC", ch).lower()
        if not ch or _TANDA.fullmatch(ch):
            if not spasi:
                keluar.append(" ")
                peta.append(i)
                spasi = True
            continue
        for c in ch:
            keluar.append(c)
            peta.append(i)
        spasi = False
    if keluar and keluar[-1] == " ":
        keluar.pop()
        peta.pop()
    return "".join(keluar), peta


def normalisasi(teks: str) -> str:
    return _normal_dengan_peta(teks)[0]


def cocokkan_kutipan(teks_elemen: str, kutipan: str) -> str | None:
    """Kembalikan potongan ASLI `teks_elemen` yang cocok dengan `kutipan`, atau None bila tidak ada.

    Kutipan kosong → awal teks elemen (maks. 300 karakter), tetap substring asli.
    Kutipan LLM yang terpotong "…" di ujung diterima bila bagian sebelum elipsis cocok.
    """
    if not teks_elemen.strip():
        return None
    kutipan = (kutipan or "").strip().strip("\"'“”").rstrip("…").removesuffix("...").strip()
    if not kutipan:
        return teks_elemen[:PANJANG_KUTIPAN_DEFAULT].strip()
    n_elemen, peta = _normal_dengan_peta(teks_elemen)
    n_kutipan = normalisasi(kutipan)
    if len(n_kutipan) < 3:
        return None
    posisi = n_elemen.find(n_kutipan)
    if posisi < 0:
        return None
    awal, akhir = peta[posisi], peta[posisi + len(n_kutipan) - 1] + 1
    return teks_elemen[awal:akhir]


@dataclass
class RujukanSah:
    elemen: Elemen
    kutipan: str
    peran: str


def verifikasi(rujukan_llm: list[dict], peta_alias: dict[str, Elemen], peran: str) -> tuple[list[RujukanSah], list[str]]:
    """Periksa rujukan dari LLM. Kembalikan (rujukan sah, daftar keterangan rujukan tidak sah)."""
    sah: list[RujukanSah] = []
    tidak_sah: list[str] = []
    terlihat: set[tuple] = set()
    for r in rujukan_llm or []:
        alias = str(r.get("id", "")).strip().strip("[]").upper()
        e = peta_alias.get(alias)
        if e is None:
            tidak_sah.append(f"{alias or '(kosong)'}: ID tidak ada dalam konteks")
            continue
        asli = cocokkan_kutipan(e.teks, str(r.get("kutipan", "")))
        if asli is None:
            tidak_sah.append(f"{alias}: kutipan tidak ditemukan di teks elemen")
            continue
        if (e.id, asli) not in terlihat:
            terlihat.add((e.id, asli))
            sah.append(RujukanSah(e, asli, peran))
    return sah, tidak_sah


def periksa_invarian(db: Session, review_id) -> list[str]:
    """Pemeriksaan terakhir sebelum hasil disimpan (CLAUDE.md aturan 3): setiap kutipan rujukan
    review WAJIB ada di teks elemen pada halaman yang dirujuk. Kembalikan daftar pelanggaran (kosong = aman)."""
    pelanggaran = []
    for r, e in db.execute(select(Rujukan, Elemen).join(Elemen, Elemen.id == Rujukan.elemen_id)
                           .where(Rujukan.review_id == review_id)).all():
        if not r.kutipan or r.kutipan not in e.teks:
            pelanggaran.append(f"rujukan {r.id}: kutipan tidak ada di elemen {e.id} (hlm {e.halaman})")
    return pelanggaran


def nomor_kalimat(teks: str, kutipan: str) -> int | None:
    """Kalimat ke-berapa kutipan dimulai dalam elemen (untuk lokasi presisi 'kalimat n'); None bila 1 kalimat."""
    posisi = teks.find(kutipan)
    kalimat = [m.end() for m in re.finditer(r"[.!?](\s+|$)", teks)]
    if posisi < 0 or len(kalimat) <= 1:
        return None
    return sum(1 for akhir in kalimat if akhir <= posisi) + 1
