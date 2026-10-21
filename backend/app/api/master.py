"""Endpoint Modul B (Checklist) & C (Kategori).

Checklist: CRUD per item; `checklist_item` = isi terbaru, isi sebelum setiap ubah disalin ke `checklist_histori`.
Isi checklist review disusun ulang dari kedua tabel pada waktu review dimulai (lihat app/checklist.py).
Kategori: admin menyunting daftar lengkap lalu "Simpan sebagai versi baru" (salinan seluruh item per versi).
"""
import uuid
from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.akses import ADMIN, pengguna_saat_ini, wajib_role
from app.audit import catat
from app.checklist import rapikan_fisik, urut_ulang
from app.db import sesi_db
from app.galat import Galat
from app.model import ChecklistHistory, ChecklistItem, KategoriItem, KategoriVersi, Pengguna

router = APIRouter(prefix="/api", tags=["checklist & kategori"])

# Kolom yang disalin dari checklist_item ke checklist_histori (id baru, isi & jejak buat/ubah sama).
KOLOM_SALIN = ("created_by", "create_date", "update_by", "update_date", "no_urut", "kode", "checklist", "kriteria",
               "berlaku_untuk", "aktif")


class ItemChecklistMasuk(BaseModel):
    kode: str
    judul: str
    kriteria: str
    berlaku_untuk: Literal["TOR", "RAB", "TOR & RAB"]
    aktif: bool = True


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


def _versi_kategori(db: Session, v: KategoriVersi) -> dict:
    return {"id": str(v.id), "nomor": v.nomor, "aktif": v.aktif, "catatan": v.catatan, "dibuat_at": v.created_at.isoformat(),
            "dibuat_oleh": _nama(db, v.dibuat_oleh),
            "item": [{"id": str(i.id), "urutan": i.urutan, "kode": i.kode, "nama": i.nama, "definisi": i.definisi,
                      "diteruskan": i.diteruskan} for i in v.item]}


def _item(db: Session, i: ChecklistItem | ChecklistHistory) -> dict:
    # Nama field API tetap (judul/urutan/diubah_*) agar frontend tidak berubah; kolom DB memakai nama baru.
    return {"id": str(i.id), "urutan": i.no_urut, "kode": i.kode, "judul": i.checklist, "kriteria": i.kriteria,
            "berlaku_untuk": i.berlaku_untuk, "aktif": i.aktif, "diubah_oleh": _nama(db, i.update_by),
            "diubah_at": i.update_date.isoformat()}


def _isi_item(db: Session, data: ItemChecklistMasuk, kecuali: uuid.UUID | None = None) -> dict:
    """Validasi & normalisasi isian (nama kolom DB). Error: 400."""
    isi = {"kode": data.kode.strip().upper(), "checklist": data.judul.strip(), "kriteria": data.kriteria.strip(),
           "berlaku_untuk": data.berlaku_untuk, "aktif": data.aktif}
    if not (isi["kode"] and isi["checklist"] and isi["kriteria"]):
        raise Galat(400, "Kode, checklist, dan kriteria lolos wajib diisi.")
    for k, maks, nama in (("kode", 50, "Kode"), ("checklist", 500, "Checklist")):
        if len(isi[k]) > maks:
            raise Galat(400, f"{nama} maksimal {maks} karakter.")
    if db.scalar(select(ChecklistItem.id).where(ChecklistItem.kode == isi["kode"], ChecklistItem.id != kecuali)):
        raise Galat(400, f"Kode {isi['kode']} sudah dipakai, gunakan kode lain.")
    return isi


def _catat_history(db: Session, i: ChecklistItem) -> None:
    """Salin isi item SAAT INI ke `checklist_histori` (setiap tambah & ubah → riwayat memuat semua versi)."""
    db.add(ChecklistHistory(checklist_id=i.id, **{c: getattr(i, c) for c in KOLOM_SALIN}))
    rapikan_fisik(db, "checklist_histori", "ix_checklist_histori_update_date")  # terbaru paling atas


def _jam_db(db: Session):
    """Waktu dari jam DATABASE: dibandingkan dengan review.mulai_at dari worker (mungkin di server GPU lain)."""
    return db.scalar(select(func.now()))


@contextmanager
def _kode_unik(db: Session):
    """Dua Admin menyimpan kode yang sama bersamaan: DB menolak (unik) → pesan 400, bukan error 500."""
    try:
        yield
    except IntegrityError:
        db.rollback()
        raise Galat(400, "Kode sudah dipakai, gunakan kode lain.") from None


def _wajib_ada_aktif(db: Session) -> None:
    db.flush()
    if not db.scalar(select(ChecklistItem.id).where(ChecklistItem.aktif).limit(1)):
        raise Galat(400, "Minimal satu item checklist harus berstatus Aktif.")


def _ambil_item(db: Session, item_id: uuid.UUID) -> ChecklistItem:
    i = db.get(ChecklistItem, item_id)
    if i is None:
        raise Galat(404, "Item checklist tidak ditemukan. Muat ulang halaman.")
    return i


@router.get("/checklist")
def checklist(db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Isi checklist terbaru, urut nomor urut."""
    item = db.scalars(select(ChecklistItem).order_by(ChecklistItem.no_urut, ChecklistItem.kode)).all()
    return {"item": [_item(db, i) for i in item]}


@router.post("/checklist/item")
def checklist_tambah(data: ItemChecklistMasuk, request: Request, db: Session = Depends(sesi_db),
                     p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Tambah item (ditaruh setelah item berkode sebelumnya). Error: 400 isian tidak valid / kode sudah dipakai."""
    isi = _isi_item(db, data)
    sekarang = _jam_db(db)
    i = ChecklistItem(**isi, no_urut=0, created_by=p.id, create_date=sekarang, update_by=p.id, update_date=sekarang)
    with _kode_unik(db):
        db.add(i)
        urut_ulang(db, baru=i)
    _catat_history(db, i)
    _wajib_ada_aktif(db)
    catat(db, request, "CHECKLIST_TAMBAH", "checklist_item", i.id, sesudah=isi)
    db.commit()
    return _item(db, i)


@router.put("/checklist/item/{item_id}")
def checklist_ubah(item_id: uuid.UUID, data: ItemChecklistMasuk, request: Request, db: Session = Depends(sesi_db),
                   p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Ubah item (termasuk kode & status). Isi baru juga dicatat ke `checklist_histori` (versi sebelumnya sudah ada di
    sana), sehingga review yang sudah berjalan tetap menampilkan isi saat itu.

    Error: 400 isian tidak valid / kode sudah dipakai / tidak ada item aktif; 404 item tidak ada.
    """
    i = _ambil_item(db, item_id)
    isi = _isi_item(db, data, kecuali=i.id)
    sebelum = {k: getattr(i, k) for k in isi}
    if sebelum == isi:
        return _item(db, i)
    for k, v in isi.items():
        setattr(i, k, v)
    i.update_by, i.update_date = p.id, _jam_db(db)
    with _kode_unik(db):
        urut_ulang(db)
    _catat_history(db, i)
    _wajib_ada_aktif(db)
    catat(db, request, "CHECKLIST_UBAH", "checklist_item", i.id, sebelum=sebelum, sesudah=isi)
    db.commit()
    return _item(db, i)


@router.delete("/checklist/item/{item_id}")
def checklist_hapus(item_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                    _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Hapus item beserta riwayatnya secara permanen; item ini ikut hilang dari tampilan review lama (keputusan
    pemilik produk, desain.md §7). Error: 400 tidak ada item aktif tersisa; 404 item tidak ada."""
    i = _ambil_item(db, item_id)
    # Hapus permanen (riwayat ikut terhapus) → isi lengkap disimpan di Audit Log agar tetap dapat ditelusuri.
    sebelum = {**{k: getattr(i, k) for k in ("kode", "checklist", "kriteria", "berlaku_untuk", "aktif")},
               "jumlah_histori": db.scalar(select(func.count()).where(ChecklistHistory.checklist_id == i.id))}
    db.delete(i)  # riwayatnya ikut terhapus (FK checklist_histori.checklist_id ON DELETE CASCADE)
    urut_ulang(db)
    _wajib_ada_aktif(db)
    catat(db, request, "CHECKLIST_HAPUS", "checklist_item", item_id, sebelum=sebelum)
    db.commit()
    return {"ok": True}


class UrutanMasuk(BaseModel):
    id: list[uuid.UUID]


@router.put("/checklist/urutan")
def checklist_urutan(data: UrutanMasuk, request: Request, db: Session = Depends(sesi_db),
                     _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Atur urutan item (`id` = semua id item sesuai urutan baru). Hanya `no_urut` yang berubah — tidak membuat
    riwayat karena isi item tidak berubah. Error: 400 daftar tidak memuat tepat semua item (mis. ada yang baru ditambah)."""
    semua = set(db.scalars(select(ChecklistItem.id)))
    if len(data.id) != len(semua) or set(data.id) != semua:
        raise Galat(400, "Daftar checklist sudah berubah. Muat ulang halaman lalu atur urutan lagi.")
    urut_ulang(db, urutan=data.id)
    catat(db, request, "CHECKLIST_URUTAN", "checklist_item", None, sesudah={"id": [str(i) for i in data.id]})
    db.commit()
    return checklist(db, _)


@router.get("/checklist/item/{item_id}/riwayat")
def checklist_riwayat(item_id: uuid.UUID, db: Session = Depends(sesi_db), _: Pengguna = Depends(pengguna_saat_ini)) -> list[dict]:
    """Semua versi item dari `checklist_histori`, terbaru dulu (baris pertama = isi saat ini). Error: 404."""
    i = _ambil_item(db, item_id)
    baris = db.scalars(select(ChecklistHistory).where(ChecklistHistory.checklist_id == i.id)
                       .order_by(ChecklistHistory.update_date.desc())).all()
    return [_item(db, r) for r in baris]


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
