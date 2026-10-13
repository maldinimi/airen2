"""Hak akses: role + Satker, selalu dicek di backend (CLAUDE.md aturan 8, PRD §4).

- Pengusul : hanya usulan milik Satker-nya; membuat/merevisi/mengajukan.
- Reviewer : seluruh usulan; override & finalisasi.
- Admin    : seluruh data; kelola master & pengguna.
Satu pengguna dapat memiliki beberapa role; haknya adalah gabungan.
"""
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import sesi_db
from app.galat import Galat
from app.keamanan import hash_token
from app.log import set_konteks
from app.model import Pengguna, Sesi, Usulan

PENGUSUL, REVIEWER, ADMIN = "PENGUSUL", "REVIEWER", "ADMIN"
NAMA_COOKIE = "sesi"
METODE_AMAN = {"GET", "HEAD", "OPTIONS"}


def boleh_lihat_semua(p: Pengguna) -> bool:
    return bool(p.daftar_role & {REVIEWER, ADMIN})


def boleh_lihat_usulan(p: Pengguna, u: Usulan) -> bool:
    return boleh_lihat_semua(p) or (PENGUSUL in p.daftar_role and p.satker_id is not None and u.satker_id == p.satker_id)


def boleh_kelola_usulan(p: Pengguna, u: Usulan) -> bool:
    """Membuat revisi, mengajukan review, menghapus draf, mengarsipkan: Pengusul Satker yang sama."""
    return PENGUSUL in p.daftar_role and p.satker_id is not None and u.satker_id == p.satker_id


def pastikan(syarat: bool, pesan: str = "Anda tidak memiliki akses ke data ini.") -> None:
    if not syarat:
        raise Galat(403, pesan)


def pengguna_saat_ini(request: Request, db: Session = Depends(sesi_db)) -> Pengguna:
    """Dependency: pengguna dari cookie sesi. Untuk metode yang mengubah data, header
    `X-CSRF-Token` wajib sama dengan token CSRF sesi (double submit).

    Error: 401 bila belum login/sesi habis; 403 bila CSRF tidak cocok.
    """
    token = request.cookies.get(NAMA_COOKIE)
    if not token:
        raise Galat(401, "Silakan login terlebih dahulu.")
    sesi = db.scalar(select(Sesi).where(Sesi.token_hash == hash_token(token)))
    if sesi is None or sesi.expires_at < datetime.now(timezone.utc):
        raise Galat(401, "Sesi Anda telah berakhir. Silakan login kembali.")
    if request.method not in METODE_AMAN and request.headers.get("X-CSRF-Token") != sesi.csrf:
        raise Galat(403, "Permintaan ditolak (token keamanan tidak valid). Muat ulang halaman.")
    p = db.get(Pengguna, sesi.pengguna_id)
    if p is None or not p.aktif:
        raise Galat(401, "Akun tidak aktif.")
    set_konteks(pengguna_id=p.id)
    request.state.pengguna = p
    return p


def wajib_role(*roles: str):
    """Dependency factory: pengguna harus memiliki salah satu role yang disebut."""
    def cek(p: Pengguna = Depends(pengguna_saat_ini)) -> Pengguna:
        pastikan(bool(p.daftar_role & set(roles)), "Fitur ini tidak tersedia untuk role Anda.")
        return p
    return cek
