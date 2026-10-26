"""Endpoint Modul B (Checklist) & C (Kategori).

Checklist: CRUD per item; `checklist_item` = isi terbaru, isi sebelum setiap ubah disalin ke `checklist_histori`.
Isi checklist review disusun ulang dari kedua tabel pada waktu review dimulai (lihat app/checklist.py).
Kategori: CRUD per kategori dengan pola yang sama (`kategori` + `kategori_histori`); review menyimpan salinan
kategori yang dipakai di `review_kategori` (lihat pekerja/review.py:kunci_acuan).
"""
import uuid
from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.akses import ADMIN, pengguna_saat_ini, wajib_role
from app.audit import catat
from app.checklist import kunci_kode, rapikan_fisik, urut_ulang
from app.db import sesi_db
from app.galat import Galat
from app.model import ChecklistHistory, ChecklistItem, Kategori, KategoriHistori, Pengguna

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
    aktif: bool = True


def _nama(db: Session, pid) -> str | None:
    return db.get(Pengguna, pid).nama if pid else None


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


def _kategori(db: Session, k: Kategori | KategoriHistori) -> dict:
    # Field API tetap (nama/definisi/diubah_*) agar frontend tidak berubah; kolom DB memakai nama baru.
    return {"id": str(k.id), "kode": k.kode, "nama": k.kategori, "definisi": k.deskripsi, "aktif": k.aktif,
            "diubah_oleh": _nama(db, k.updated_by), "diubah_at": k.updated_date.isoformat()}


def _isi_kategori(db: Session, data: ItemKategoriMasuk, kecuali: uuid.UUID | None = None) -> dict:
    """Validasi & normalisasi isian kategori (nama kolom DB). Error: 400."""
    isi = {"aktif": data.aktif, "kode": data.kode.strip().upper(), "kategori": data.nama.strip(),
           "deskripsi": data.definisi.strip()}
    if not (isi["kode"] and isi["kategori"] and isi["deskripsi"]):
        raise Galat(400, "Kode, kategori, dan deskripsi wajib diisi.")
    for k, maks, nama in (("kode", 20, "Kode"), ("kategori", 255, "Kategori")):
        if len(isi[k]) > maks:
            raise Galat(400, f"{nama} maksimal {maks} karakter.")
    if db.scalar(select(Kategori.id).where(Kategori.kode == isi["kode"], Kategori.id != kecuali)):
        raise Galat(400, f"Kode {isi['kode']} sudah dipakai, gunakan kode lain.")
    return isi


def _catat_histori_kategori(db: Session, k: Kategori) -> None:
    """Salin isi kategori SEBELUM diubah ke `kategori_histori` (riwayat saja; versi terkini hanya di `kategori`)."""
    db.add(KategoriHistori(created_by=k.created_by, created_date=k.created_date, updated_by=k.updated_by, updated_date=k.updated_date,
                           kategori_id=k.id, kategori=k.kategori, aktif=k.aktif, kode=k.kode, deskripsi=k.deskripsi))


def _wajib_ada_kategori_aktif(db: Session) -> None:
    """Screening 2 membutuhkan minimal satu kategori Aktif (seed hanya mengisi ulang tabel yang kosong). Error: 400."""
    db.flush()
    if not db.scalar(select(Kategori.id).where(Kategori.aktif).limit(1)):
        raise Galat(400, "Minimal satu kategori harus berstatus Aktif.")


def _ambil_kategori(db: Session, kategori_id: uuid.UUID, kunci: bool = False) -> Kategori:
    k = db.get(Kategori, kategori_id, with_for_update=kunci)
    if k is None:
        raise Galat(404, "Kategori tidak ditemukan. Muat ulang halaman.")
    return k


@router.get("/kategori")
def kategori(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Daftar kategori terbaru, urut kode alami (K1, K2, …, K10). Khusus Admin (C5, C7). Error: 403."""
    return {"item": [_kategori(db, k) for k in sorted(db.scalars(select(Kategori)), key=lambda k: kunci_kode(k.kode))]}


@router.post("/kategori")
def kategori_tambah(data: ItemKategoriMasuk, request: Request, db: Session = Depends(sesi_db),
                    p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Tambah kategori; dipakai AI mulai review berikutnya (C2). Error: 400 isian tidak valid / kode sudah dipakai."""
    isi = _isi_kategori(db, data)
    sekarang = _jam_db(db)
    k = Kategori(**isi, created_by=p.id, created_date=sekarang, updated_by=p.id, updated_date=sekarang)
    with _kode_unik(db):
        db.add(k)
        db.flush()
    catat(db, request, "KATEGORI_TAMBAH", "kategori", k.id, sesudah=isi)
    db.commit()
    return _kategori(db, k)


@router.put("/kategori/{kategori_id}")
def kategori_ubah(kategori_id: uuid.UUID, data: ItemKategoriMasuk, request: Request, db: Session = Depends(sesi_db),
                  p: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Ubah kategori (termasuk kode). Isi SEBELUM diubah disalin ke `kategori_histori`; review lama memakai salinannya
    sendiri (`review_kategori`) sehingga tidak berubah (C4). Error: 400 isian tidak valid / kode sudah dipakai; 404."""
    # Baris dikunci: dua edit bersamaan tidak menyalin versi lama yang sama dua kali.
    k = _ambil_kategori(db, kategori_id, kunci=True)
    isi = _isi_kategori(db, data, kecuali=k.id)
    sebelum = {c: getattr(k, c) for c in isi}
    if sebelum == isi:
        return _kategori(db, k)
    _catat_histori_kategori(db, k)
    for c, v in isi.items():
        setattr(k, c, v)
    k.updated_by, k.updated_date = p.id, _jam_db(db)
    with _kode_unik(db):
        db.flush()
    _wajib_ada_kategori_aktif(db)
    catat(db, request, "KATEGORI_UBAH", "kategori", k.id, sebelum=sebelum, sesudah=isi)
    db.commit()
    return _kategori(db, k)


@router.delete("/kategori/{kategori_id}")
def kategori_hapus(kategori_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                   _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Hapus kategori beserta riwayatnya secara permanen. Review lama tidak berubah (salinan di `review_kategori`).
    Error: 400 tidak ada kategori Aktif tersisa; 404."""
    k = _ambil_kategori(db, kategori_id)
    sebelum = {**{c: getattr(k, c) for c in ("kode", "kategori", "deskripsi", "aktif")},
               "jumlah_histori": db.scalar(select(func.count()).where(KategoriHistori.kategori_id == k.id))}
    db.delete(k)  # riwayatnya ikut terhapus (FK kategori_histori.kategori_id ON DELETE CASCADE)
    _wajib_ada_kategori_aktif(db)
    catat(db, request, "KATEGORI_HAPUS", "kategori", kategori_id, sebelum=sebelum)
    db.commit()
    return {"ok": True}


@router.get("/kategori/{kategori_id}/riwayat")
def kategori_riwayat(kategori_id: uuid.UUID, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    """Versi sebelum tiap perubahan dari `kategori_histori`, terbaru dulu (isi saat ini tidak termasuk). Khusus Admin (C5).
    Error: 403, 404."""
    k = _ambil_kategori(db, kategori_id)
    baris = db.scalars(select(KategoriHistori).where(KategoriHistori.kategori_id == k.id)
                       .order_by(KategoriHistori.updated_date.desc())).all()
    return [_kategori(db, r) for r in baris]
