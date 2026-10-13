"""Endpoint administrasi: pengguna & role, Satker, node AI, audit log."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.akses import ADMIN, PENGUSUL, REVIEWER, pengguna_saat_ini, wajib_role
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.keamanan import hash_password, hash_token, token_baru, validasi_password
from app.model import AuditLog, NodeAI, Pengguna, PenggunaRole, Satker, Sesi

router = APIRouter(prefix="/api", tags=["administrasi"])
ROLE_SAH = {PENGUSUL, REVIEWER, ADMIN}


class PenggunaMasuk(BaseModel):
    username: str
    nama: str
    roles: list[str]
    satker_id: uuid.UUID | None = None
    aktif: bool = True
    password: str | None = None  # wajib saat membuat; saat ubah = reset password bila diisi


class SatkerMasuk(BaseModel):
    kode: str
    nama: str
    aktif: bool = True


class NodeMasuk(BaseModel):
    nama: str


def _pengguna(p: Pengguna) -> dict:
    return {"id": str(p.id), "username": p.username, "nama": p.nama, "roles": sorted(p.daftar_role), "aktif": p.aktif,
            "satker": {"id": str(p.satker.id), "kode": p.satker.kode, "nama": p.satker.nama} if p.satker else None,
            "last_login_at": p.last_login_at.isoformat() if p.last_login_at else None}


def _validasi_pengguna(db: Session, data: PenggunaMasuk) -> None:
    if not data.username.strip() or not data.nama.strip():
        raise Galat(400, "Username dan nama wajib diisi.")
    if not data.roles or not set(data.roles) <= ROLE_SAH:
        raise Galat(400, "Pilih minimal satu role yang valid.")
    if PENGUSUL in data.roles and data.satker_id is None:
        raise Galat(400, "Pengusul wajib terhubung ke Satker.")
    if data.satker_id and db.get(Satker, data.satker_id) is None:
        raise Galat(400, "Satker tidak ditemukan.")
    if data.password and (pesan := validasi_password(data.password)):
        raise Galat(400, pesan)


@router.get("/pengguna")
def daftar_pengguna(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    return [_pengguna(p) for p in db.scalars(select(Pengguna).order_by(Pengguna.username))]


@router.post("/pengguna")
def buat_pengguna(data: PenggunaMasuk, request: Request, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    _validasi_pengguna(db, data)
    if not data.password:
        raise Galat(400, "Password awal wajib diisi.")
    if db.scalar(select(Pengguna.id).where(func.lower(Pengguna.username) == data.username.strip().lower())):
        raise Galat(409, "Username sudah dipakai.")
    p = Pengguna(username=data.username.strip(), nama=data.nama.strip(), satker_id=data.satker_id, aktif=data.aktif,
                 password_hash=hash_password(data.password))
    p.roles = [PenggunaRole(role=r) for r in sorted(set(data.roles))]
    db.add(p)
    db.flush()
    catat(db, request, "PENGGUNA_BUAT", "pengguna", p.id, sesudah=_pengguna(p))
    db.commit()
    return _pengguna(p)


@router.put("/pengguna/{pengguna_id}")
def ubah_pengguna(pengguna_id: uuid.UUID, data: PenggunaMasuk, request: Request, db: Session = Depends(sesi_db),
                  admin: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Ubah data/role/Satker/status aktif; isi `password` untuk reset password. Menonaktifkan akun mencabut sesinya."""
    p = db.get(Pengguna, pengguna_id)
    if p is None:
        raise Galat(404, "Pengguna tidak ditemukan.")
    _validasi_pengguna(db, data)
    if p.id == admin.id and (ADMIN not in data.roles or not data.aktif):
        raise Galat(400, "Anda tidak dapat mencabut role Admin atau menonaktifkan akun sendiri.")
    sebelum = _pengguna(p)
    p.nama, p.satker_id, p.aktif = data.nama.strip(), data.satker_id, data.aktif
    # Hanya selisihnya: mengganti seluruh list memicu INSERT sebelum DELETE → bentrok primary key.
    p.roles = [r for r in p.roles if r.role in data.roles] + \
        [PenggunaRole(role=r) for r in sorted(set(data.roles) - p.daftar_role)]
    if data.password:
        p.password_hash = hash_password(data.password)
    if data.password or not data.aktif:
        db.query(Sesi).filter(Sesi.pengguna_id == p.id).delete()
    db.flush()
    db.refresh(p)
    catat(db, request, "PENGGUNA_UBAH", "pengguna", p.id, sebelum=sebelum, sesudah={**_pengguna(p), "reset_password": bool(data.password)})
    db.commit()
    return _pengguna(p)


@router.get("/satker")
def daftar_satker(db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> list[dict]:
    return [{"id": str(s.id), "kode": s.kode, "nama": s.nama, "aktif": s.aktif} for s in db.scalars(select(Satker).order_by(Satker.nama))]


@router.post("/satker")
def buat_satker(data: SatkerMasuk, request: Request, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    if not data.kode.strip() or not data.nama.strip():
        raise Galat(400, "Kode dan nama Satker wajib diisi.")
    if db.scalar(select(Satker.id).where(Satker.kode == data.kode.strip())):
        raise Galat(409, "Kode Satker sudah dipakai.")
    s = Satker(kode=data.kode.strip(), nama=data.nama.strip(), aktif=data.aktif)
    db.add(s)
    db.flush()
    catat(db, request, "SATKER_BUAT", "satker", s.id, sesudah=data.model_dump())
    db.commit()
    return {"id": str(s.id), "kode": s.kode, "nama": s.nama, "aktif": s.aktif}


@router.put("/satker/{satker_id}")
def ubah_satker(satker_id: uuid.UUID, data: SatkerMasuk, request: Request, db: Session = Depends(sesi_db),
                _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    s = db.get(Satker, satker_id)
    if s is None:
        raise Galat(404, "Satker tidak ditemukan.")
    sebelum = {"kode": s.kode, "nama": s.nama, "aktif": s.aktif}
    s.kode, s.nama, s.aktif = data.kode.strip(), data.nama.strip(), data.aktif
    catat(db, request, "SATKER_UBAH", "satker", s.id, sebelum=sebelum, sesudah=data.model_dump())
    db.commit()
    return {"id": str(s.id), "kode": s.kode, "nama": s.nama, "aktif": s.aktif}


@router.get("/node-ai")
def daftar_node(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    return [{"id": str(n.id), "nama": n.nama, "aktif": n.aktif, "jarak_jauh": n.token_hash is not None,
             "terakhir_terlihat": n.terakhir_terlihat.isoformat() if n.terakhir_terlihat else None, "info": n.info}
            for n in db.scalars(select(NodeAI).order_by(NodeAI.nama))]


@router.post("/node-ai")
def daftarkan_node(data: NodeMasuk, request: Request, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Daftarkan node AI jarak jauh. Token hanya ditampilkan SEKALI; simpan di `.env` node (NODE_TOKEN)."""
    nama = data.nama.strip()
    if not nama or db.scalar(select(NodeAI.id).where(NodeAI.nama == nama)):
        raise Galat(400, "Nama node kosong atau sudah dipakai.")
    token = token_baru()
    n = NodeAI(nama=nama, token_hash=hash_token(token), aktif=True)
    db.add(n)
    db.flush()
    catat(db, request, "NODE_DAFTAR", "node_ai", n.id, sesudah={"nama": nama})
    db.commit()
    return {"id": str(n.id), "nama": nama, "token": token}


@router.post("/node-ai/{node_id}/cabut")
def cabut_node(node_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Cabut akses node: token tidak lagi diterima dan worker node berhenti mengambil job."""
    n = db.get(NodeAI, node_id)
    if n is None:
        raise Galat(404, "Node tidak ditemukan.")
    n.aktif = False
    catat(db, request, "NODE_CABUT", "node_ai", n.id, sebelum={"nama": n.nama})
    db.commit()
    return {"ok": True}


@router.get("/audit")
def audit(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN)), pengguna_id: uuid.UUID | None = None,
          aksi: str | None = None, entitas: str | None = None, dari: datetime | None = None, sampai: datetime | None = None,
          halaman: int = Query(1, ge=1), per_halaman: int = Query(50, ge=1, le=200)) -> dict:
    """Audit log dengan filter pengguna, aksi, entitas, rentang tanggal."""
    kueri = select(AuditLog)
    if pengguna_id:
        kueri = kueri.where(AuditLog.pengguna_id == pengguna_id)
    if aksi:
        kueri = kueri.where(AuditLog.aksi == aksi)
    if entitas:
        kueri = kueri.where(AuditLog.entitas == entitas)
    if dari:
        kueri = kueri.where(AuditLog.at >= dari)
    if sampai:
        kueri = kueri.where(AuditLog.at <= sampai)
    total = db.scalar(select(func.count()).select_from(kueri.subquery()))
    baris = db.scalars(kueri.order_by(AuditLog.at.desc()).offset((halaman - 1) * per_halaman).limit(per_halaman)).all()
    nama = {p.id: p.nama for p in db.scalars(select(Pengguna).where(Pengguna.id.in_({b.pengguna_id for b in baris if b.pengguna_id})))}
    return {"total": total, "data": [{
        "id": str(b.id), "at": b.at.isoformat(), "pengguna": nama.get(b.pengguna_id), "aksi": b.aksi, "entitas": b.entitas,
        "entitas_id": b.entitas_id, "data_sebelum": b.data_sebelum, "data_sesudah": b.data_sesudah, "ip": b.ip} for b in baris],
        "aksi": db.scalars(select(AuditLog.aksi).distinct().order_by(AuditLog.aksi)).all()}
