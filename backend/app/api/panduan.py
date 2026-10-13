"""Endpoint Modul D — Panduan (berversi, soft delete, status pemrosesan)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File as FormFile, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.akses import ADMIN, pengguna_saat_ini, wajib_role
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.model import File, Job, Panduan, PanduanVersi, Pengguna
from app.penyimpanan import simpan_unggahan

router = APIRouter(prefix="/api/panduan", tags=["panduan"])


def antrekan_ekstraksi(db: Session, f: File) -> None:
    """Antrekan pemrosesan file panduan bila belum siap/diproses (ekstraksi per file, D4)."""
    if f.status_ekstraksi in ("BELUM", "GAGAL"):
        f.status_ekstraksi, f.pesan_ekstraksi = "BELUM", None
        if db.scalar(select(Job.id).where(Job.ref_id == f.id, Job.status.in_(("ANTRE", "DIPROSES")))) is None:
            db.add(Job(jenis="PROSES_PANDUAN", ref_id=f.id, trace_id=uuid.uuid4().hex))


def _versi(v: PanduanVersi) -> dict:
    return {"id": str(v.id), "nomor": v.nomor, "judul": v.judul, "deskripsi": v.deskripsi, "file_id": str(v.file_id),
            "nama_file": v.nama_file, "status_proses": v.file.status_ekstraksi, "pesan_gagal": v.file.pesan_ekstraksi,
            "jumlah_halaman": v.file.jumlah_halaman, "dibuat_at": v.created_at.isoformat()}


def _panduan(p: Panduan) -> dict:
    terkini = p.versi[-1]
    return {"id": str(p.id), "judul": terkini.judul, "dihapus": p.dihapus_at is not None, "terkini": _versi(terkini),
            "versi": [_versi(v) for v in reversed(p.versi)]}


@router.get("")
def daftar(termasuk_dihapus: bool = False, db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> list[dict]:
    """Daftar panduan beserta versi & status proses. Semua pengguna dapat membaca panduan (D3)."""
    kueri = select(Panduan).order_by(Panduan.judul_terkini)
    if not termasuk_dihapus:
        kueri = kueri.where(Panduan.dihapus_at.is_(None))
    return [_panduan(p) for p in db.scalars(kueri)]


@router.post("")
def unggah(request: Request, files: list[UploadFile] = FormFile(...), db: Session = Depends(sesi_db),
           p: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    """Unggah satu atau beberapa PDF panduan sekaligus; judul awal = nama file (D2)."""
    hasil = []
    for unggahan in files:
        f, nama = simpan_unggahan(db, unggahan)
        judul = nama.rsplit(".", 1)[0]
        pd = Panduan(judul_terkini=judul)
        db.add(pd)
        db.flush()
        db.add(PanduanVersi(panduan_id=pd.id, nomor=1, judul=judul, file_id=f.id, nama_file=nama, dibuat_oleh=p.id))
        antrekan_ekstraksi(db, f)
        catat(db, request, "PANDUAN_UNGGAH", "panduan", pd.id, sesudah={"judul": judul, "file": nama, "sha256": f.sha256})
        db.flush()
        db.refresh(pd)
        hasil.append(_panduan(pd))
    db.commit()
    return hasil


@router.put("/{panduan_id}")
def ubah(panduan_id: uuid.UUID, request: Request, judul: str = Form(...), deskripsi: str | None = Form(None),
         file: UploadFile | None = FormFile(None), db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Ubah judul/deskripsi dan/atau ganti file → versi baru. Versi lama tetap ada (D5, D6)."""
    pd = db.get(Panduan, panduan_id)
    if pd is None or pd.dihapus_at:
        raise Galat(404, "Panduan tidak ditemukan.")
    if not judul.strip():
        raise Galat(400, "Judul wajib diisi.")
    lama = pd.versi[-1]
    file_id, nama_file = lama.file_id, lama.nama_file
    if file is not None and file.filename:
        f, nama_file = simpan_unggahan(db, file)
        file_id = f.id
        antrekan_ekstraksi(db, f)
    v = PanduanVersi(panduan_id=pd.id, nomor=lama.nomor + 1, judul=judul.strip(), deskripsi=(deskripsi or "").strip() or None,
                     file_id=file_id, nama_file=nama_file, dibuat_oleh=p.id)
    db.add(v)
    pd.judul_terkini = v.judul
    catat(db, request, "PANDUAN_UBAH", "panduan", pd.id, sebelum={"versi": lama.nomor, "judul": lama.judul, "file": lama.nama_file},
          sesudah={"versi": v.nomor, "judul": v.judul, "file": nama_file})
    db.commit()
    db.refresh(pd)
    return _panduan(pd)


@router.delete("/{panduan_id}")
def hapus(panduan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Soft delete: panduan tidak dipakai review berikutnya, tetapi file & versinya tetap ada (D6)."""
    pd = db.get(Panduan, panduan_id)
    if pd is None or pd.dihapus_at:
        raise Galat(404, "Panduan tidak ditemukan.")
    pd.dihapus_at = datetime.now(timezone.utc)
    catat(db, request, "PANDUAN_HAPUS", "panduan", pd.id, sebelum={"judul": pd.judul_terkini})
    db.commit()
    return {"ok": True}


@router.post("/{panduan_id}/proses-ulang")
def proses_ulang(panduan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Ulangi pemrosesan file panduan versi terkini yang GAGAL."""
    pd = db.get(Panduan, panduan_id)
    if pd is None:
        raise Galat(404, "Panduan tidak ditemukan.")
    f = pd.versi[-1].file
    if f.status_ekstraksi != "GAGAL":
        raise Galat(409, "Hanya panduan berstatus Gagal yang dapat diproses ulang.")
    antrekan_ekstraksi(db, f)
    catat(db, request, "PANDUAN_PROSES_ULANG", "panduan", pd.id)
    db.commit()
    db.refresh(pd)
    return _panduan(pd)
