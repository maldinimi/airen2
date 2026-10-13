"""Endpoint Modul B (Checklist) & C (Kategori) — berversi.

Versioning: admin menyunting daftar lengkap di UI lalu "Simpan sebagai versi baru". Backend
membuat baris versi baru + salinan seluruh item; versi lama hanya dinonaktifkan, isinya tidak
pernah diubah/dihapus, sehingga review lama tetap menampilkan checklist/kategori persis saat itu.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.akses import ADMIN, pengguna_saat_ini, wajib_role
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.model import ChecklistItem, ChecklistVersi, KategoriItem, KategoriVersi, Pengguna

router = APIRouter(prefix="/api", tags=["checklist & kategori"])


class ItemChecklistMasuk(BaseModel):
    kode: str
    judul: str
    kriteria: str
    berlaku_untuk: Literal["TOR", "RAB", "KEDUANYA"]


class VersiChecklistMasuk(BaseModel):
    catatan: str | None = None
    item: list[ItemChecklistMasuk]


class ItemKategoriMasuk(BaseModel):
    kode: str
    nama: str
    definisi: str
    diteruskan: bool = True


class VersiKategoriMasuk(BaseModel):
    catatan: str | None = None
    item: list[ItemKategoriMasuk]


def _nama(db: Session, pid) -> str | None:
    return db.get(Pengguna, pid).nama if pid else None


def _validasi(item: list, wajib: tuple[str, ...]) -> None:
    if not item:
        raise Galat(400, "Daftar tidak boleh kosong.")
    kode = [i.kode.strip().upper() for i in item]
    if len(set(kode)) != len(kode):
        raise Galat(400, "Kode tidak boleh ganda.")
    for i in item:
        if any(not getattr(i, f).strip() for f in wajib):
            raise Galat(400, f"Semua kolom ({', '.join(wajib)}) wajib diisi.")


def _versi_checklist(db: Session, v: ChecklistVersi) -> dict:
    return {"id": str(v.id), "nomor": v.nomor, "aktif": v.aktif, "catatan": v.catatan, "dibuat_at": v.created_at.isoformat(),
            "dibuat_oleh": _nama(db, v.dibuat_oleh),
            "item": [{"id": str(i.id), "urutan": i.urutan, "kode": i.kode, "judul": i.judul, "kriteria": i.kriteria,
                      "berlaku_untuk": i.berlaku_untuk} for i in v.item]}


def _versi_kategori(db: Session, v: KategoriVersi) -> dict:
    return {"id": str(v.id), "nomor": v.nomor, "aktif": v.aktif, "catatan": v.catatan, "dibuat_at": v.created_at.isoformat(),
            "dibuat_oleh": _nama(db, v.dibuat_oleh),
            "item": [{"id": str(i.id), "urutan": i.urutan, "kode": i.kode, "nama": i.nama, "definisi": i.definisi,
                      "diteruskan": i.diteruskan} for i in v.item]}


@router.get("/checklist")
def checklist(db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Versi aktif + daftar semua versi (B5)."""
    semua = db.scalars(select(ChecklistVersi).order_by(ChecklistVersi.nomor.desc())).all()
    aktif = next((v for v in semua if v.aktif), None)
    return {"aktif": _versi_checklist(db, aktif) if aktif else None,
            "versi": [{"id": str(v.id), "nomor": v.nomor, "aktif": v.aktif, "catatan": v.catatan, "jumlah_item": len(v.item),
                       "dibuat_at": v.created_at.isoformat(), "dibuat_oleh": _nama(db, v.dibuat_oleh)} for v in semua]}


@router.get("/checklist/versi/{versi_id}")
def checklist_versi(versi_id: uuid.UUID, db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    v = db.get(ChecklistVersi, versi_id)
    if v is None:
        raise Galat(404, "Versi checklist tidak ditemukan.")
    return _versi_checklist(db, v)


@router.post("/checklist/versi")
def checklist_simpan(data: VersiChecklistMasuk, request: Request, db: Session = Depends(sesi_db),
                     p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Simpan daftar checklist sebagai versi baru (B1, B3). Error: 400 data tidak valid."""
    _validasi(data.item, ("kode", "judul", "kriteria"))
    db.execute(select(ChecklistVersi.id).with_for_update())  # serialisasi penomoran versi
    nomor = (db.scalar(select(func.max(ChecklistVersi.nomor))) or 0) + 1
    db.execute(update(ChecklistVersi).where(ChecklistVersi.aktif).values(aktif=False))
    v = ChecklistVersi(nomor=nomor, aktif=True, dibuat_oleh=p.id, catatan=(data.catatan or "").strip() or None)
    db.add(v)
    db.flush()
    for urutan, i in enumerate(data.item, 1):
        db.add(ChecklistItem(versi_id=v.id, urutan=urutan, kode=i.kode.strip().upper(), judul=i.judul.strip(),
                             kriteria=i.kriteria.strip(), berlaku_untuk=i.berlaku_untuk))
    db.flush()
    db.refresh(v)
    catat(db, request, "CHECKLIST_VERSI_BARU", "checklist_versi", v.id,
          sesudah={"nomor": nomor, "catatan": v.catatan, "item": [i.model_dump() for i in data.item]})
    db.commit()
    return _versi_checklist(db, v)


@router.get("/kategori")
def kategori(db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    semua = db.scalars(select(KategoriVersi).order_by(KategoriVersi.nomor.desc())).all()
    aktif = next((v for v in semua if v.aktif), None)
    return {"aktif": _versi_kategori(db, aktif) if aktif else None,
            "versi": [{"id": str(v.id), "nomor": v.nomor, "aktif": v.aktif, "catatan": v.catatan, "jumlah_item": len(v.item),
                       "dibuat_at": v.created_at.isoformat(), "dibuat_oleh": _nama(db, v.dibuat_oleh)} for v in semua]}


@router.get("/kategori/versi/{versi_id}")
def kategori_versi(versi_id: uuid.UUID, db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    v = db.get(KategoriVersi, versi_id)
    if v is None:
        raise Galat(404, "Versi kategori tidak ditemukan.")
    return _versi_kategori(db, v)


@router.post("/kategori/versi")
def kategori_simpan(data: VersiKategoriMasuk, request: Request, db: Session = Depends(sesi_db),
                    p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Simpan daftar kategori sebagai versi baru (C1, C3). AI selalu memakai versi aktif (C2)."""
    _validasi(data.item, ("kode", "nama", "definisi"))
    db.execute(select(KategoriVersi.id).with_for_update())
    nomor = (db.scalar(select(func.max(KategoriVersi.nomor))) or 0) + 1
    db.execute(update(KategoriVersi).where(KategoriVersi.aktif).values(aktif=False))
    v = KategoriVersi(nomor=nomor, aktif=True, dibuat_oleh=p.id, catatan=(data.catatan or "").strip() or None)
    db.add(v)
    db.flush()
    for urutan, i in enumerate(data.item, 1):
        db.add(KategoriItem(versi_id=v.id, urutan=urutan, kode=i.kode.strip().upper(), nama=i.nama.strip(),
                            definisi=i.definisi.strip(), diteruskan=i.diteruskan))
    db.flush()
    db.refresh(v)
    catat(db, request, "KATEGORI_VERSI_BARU", "kategori_versi", v.id,
          sesudah={"nomor": nomor, "catatan": v.catatan, "item": [i.model_dump() for i in data.item]})
    db.commit()
    return _versi_kategori(db, v)
