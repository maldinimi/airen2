"""Tahun Anggaran: satu sumber "tahun berjalan" & rentang tahun yang boleh dipilih, dipakai menu Pengajuan dan Master RO.

Rentang = pilihan Tahun Anggaran di bilah atas (frontend components/Layout.tsx): tahun berjalan ±2, menurut WIB.
"""
from datetime import datetime, timedelta, timezone

from app.galat import Galat

WIB = timezone(timedelta(hours=7))  # tanpa musim panas, jadi offset tetap cukup (tidak butuh tzdata)
RENTANG_TAHUN = 2


def tahun_berjalan() -> int:
    """Tahun berjalan menurut WIB, sama dengan pilihan Tahun Anggaran di bilah atas. Dengan jam UTC, pada 1 Januari
    00.00–07.00 WIB tahun terakhir di bilah atas ditolak."""
    return datetime.now(WIB).year


def tahun_sah(tahun: int | None) -> int:
    """Tahun Anggaran isian: wajib dan dalam pilihan bilah atas (tahun berjalan ±2). Error 400."""
    if tahun is None:
        raise Galat(400, "Tahun Anggaran wajib diisi. Pilih Tahun Anggaran di bilah atas.")
    sekarang = tahun_berjalan()
    if abs(tahun - sekarang) > RENTANG_TAHUN:
        raise Galat(400, f"Tahun Anggaran harus antara {sekarang - RENTANG_TAHUN} dan {sekarang + RENTANG_TAHUN}.")
    return tahun
