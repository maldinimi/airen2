"""Primitif keamanan: hash password (Argon2), token sesi & CSRF.

Token sesi hanya disimpan sebagai SHA-256 di database, sehingga kebocoran tabel `sesi`
tidak dapat dipakai untuk login.
"""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_ph = PasswordHasher()
PANJANG_PASSWORD_MIN = 8


def hash_password(password: str) -> str:
    return _ph.hash(password)


def cek_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def token_baru() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validasi_password(password: str) -> str | None:
    """Kembalikan pesan error (Bahasa Indonesia) bila password terlalu lemah, None bila valid."""
    if len(password) < PANJANG_PASSWORD_MIN:
        return f"Password minimal {PANJANG_PASSWORD_MIN} karakter."
    if password.isalpha() or password.isdigit():
        return "Password harus memuat kombinasi huruf dan angka/simbol."
    return None
