"""Audit log aktivitas pengguna (PRD §7.3). Hanya-tambah; ditulis dalam transaksi yang sama
dengan perubahan datanya sehingga tidak ada perubahan tanpa jejak."""
from fastapi import Request
from sqlalchemy.orm import Session

from app.model import AuditLog


def catat(db: Session, request: Request | None, aksi: str, entitas: str, entitas_id=None,
          sebelum: dict | None = None, sesudah: dict | None = None, pengguna_id=None) -> None:
    """Tambahkan entri audit. Jangan sertakan password/token di `sebelum`/`sesudah`."""
    if pengguna_id is None and request is not None:
        p = getattr(request.state, "pengguna", None)
        pengguna_id = p.id if p else None
    db.add(AuditLog(
        pengguna_id=pengguna_id, aksi=aksi, entitas=entitas,
        entitas_id=str(entitas_id) if entitas_id else None,
        data_sebelum=sebelum, data_sesudah=sesudah,
        ip=request.client.host if request is not None and request.client else None,
    ))
