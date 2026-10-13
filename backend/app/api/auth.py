"""Endpoint autentikasi: login, logout, profil, ganti password."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.akses import NAMA_COOKIE, pengguna_saat_ini
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.keamanan import cek_password, hash_password, hash_token, token_baru, validasi_password
from app.konfigurasi import konfigurasi
from app.model import AuditLog, Pengguna, Sesi

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginMasuk(BaseModel):
    username: str
    password: str


class GantiPassword(BaseModel):
    password_lama: str
    password_baru: str


def profil(p: Pengguna, csrf: str | None = None) -> dict:
    data = {
        "id": str(p.id), "username": p.username, "nama": p.nama, "roles": sorted(p.daftar_role),
        "satker": {"id": str(p.satker.id), "kode": p.satker.kode, "nama": p.satker.nama} if p.satker else None,
    }
    if csrf:
        data["csrf"] = csrf
    return data


@router.post("/login")
def login(masuk: LoginMasuk, request: Request, response: Response, db: Session = Depends(sesi_db)) -> dict:
    """Login dengan username & password. Set cookie sesi HttpOnly + kembalikan token CSRF.

    Error: 401 kredensial salah (pesan umum, tidak membocorkan akun mana yang ada);
    429 bila terlalu banyak percobaan gagal dari username/IP yang sama.
    """
    k = konfigurasi()
    ip = request.client.host if request.client else None
    batas = datetime.now(timezone.utc) - timedelta(minutes=k.login_jendela_menit)
    gagal = db.scalar(select(func.count()).select_from(AuditLog).where(
        AuditLog.aksi == "LOGIN_GAGAL", AuditLog.at > batas,
        or_(AuditLog.entitas_id == masuk.username.lower(), AuditLog.ip == ip)))
    if gagal >= k.login_maks_gagal:
        raise Galat(429, f"Terlalu banyak percobaan login. Coba lagi dalam {k.login_jendela_menit} menit.")
    p = db.scalar(select(Pengguna).where(func.lower(Pengguna.username) == masuk.username.lower()))
    if p is None or not p.aktif or not cek_password(p.password_hash, masuk.password):
        catat(db, request, "LOGIN_GAGAL", "pengguna", masuk.username.lower())
        db.commit()
        raise Galat(401, "Username atau password salah.")
    token, csrf = token_baru(), token_baru()
    db.add(Sesi(pengguna_id=p.id, token_hash=hash_token(token), csrf=csrf,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=k.sesi_jam)))
    p.last_login_at = datetime.now(timezone.utc)
    catat(db, request, "LOGIN", "pengguna", p.id, pengguna_id=p.id)
    db.commit()
    response.set_cookie(NAMA_COOKIE, token, httponly=True, samesite="strict", secure=k.cookie_secure,
                        max_age=k.sesi_jam * 3600, path="/")
    return profil(p, csrf)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(sesi_db),
           p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    token = request.cookies.get(NAMA_COOKIE)
    sesi = db.scalar(select(Sesi).where(Sesi.token_hash == hash_token(token)))
    if sesi:
        db.delete(sesi)
    catat(db, request, "LOGOUT", "pengguna", p.id)
    db.commit()
    response.delete_cookie(NAMA_COOKIE, path="/")
    return {"ok": True}


@router.get("/saya")
def saya(request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Profil pengguna yang login + token CSRF sesi (dipakai frontend setelah muat ulang halaman)."""
    sesi = db.scalar(select(Sesi).where(Sesi.token_hash == hash_token(request.cookies.get(NAMA_COOKIE))))
    return profil(p, sesi.csrf)


@router.post("/ganti-password")
def ganti_password(data: GantiPassword, request: Request, db: Session = Depends(sesi_db),
                   p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Ganti password sendiri. Error: 400 password lama salah / password baru lemah."""
    if not cek_password(p.password_hash, data.password_lama):
        raise Galat(400, "Password lama salah.")
    if pesan := validasi_password(data.password_baru):
        raise Galat(400, pesan)
    p.password_hash = hash_password(data.password_baru)
    catat(db, request, "GANTI_PASSWORD", "pengguna", p.id)
    db.commit()
    return {"ok": True}
