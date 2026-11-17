"""Checklist: `checklist_item` = isi terbaru, `checklist_histori` = semua versi item (`checklist_id` → item).

Isi checklist yang dipakai review disusun ulang dari kedua tabel pada waktu review dimulai (`review.mulai_at`): untuk
tiap item yang sudah ada saat itu, dipakai versi dengan `updated_date` terakhir ≤ waktu tersebut. Perubahan isi item
setelahnya tidak mengubah review lama. Item yang dihapus permanen ikut hilang dari review lama — penyimpangan PRD B4
atas keputusan pemilik produk (desain.md §7).
"""
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import Request
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.audit import catat
from app.galat import Galat
from app.model import ChecklistHistory, ChecklistItem, Kategori, Panduan, Review

ModelUrut = type[ChecklistItem] | type[Kategori] | type[Panduan]  # tabel yang punya `no_urut` + Atur Urutan


@dataclass(frozen=True)
class IsiItem:
    """Isi satu item pada suatu waktu (aman dipakai lintas thread, tidak terikat sesi)."""
    item_id: uuid.UUID
    kode: str
    urutan: int
    judul: str
    kriteria: str
    berlaku_untuk: str
    aktif: bool


def kunci_kode(kode: str) -> list:
    """Kunci urut alami: angka dibandingkan sebagai angka (A.2 < A.10 < B.1)."""
    return [int(x) if n % 2 else x for n, x in enumerate(re.split(r"(\d+)", kode))]


def urut_ulang(db: Session, baru: ChecklistItem | Kategori | None = None, urutan: list[uuid.UUID] | None = None,
               model: ModelUrut = ChecklistItem) -> None:
    """Rapikan `no_urut` tabel `model` (checklist_item, kategori, atau panduan) jadi 1..n. Urutan diatur Admin (`urutan` = daftar id); item `baru` ditaruh tepat setelah item
    dengan kode sebelumnya (E.02 sesudah E.01) walau urutan lain sudah diatur bebas.

    Baris tabel juga disusun ulang di disk menurut no_urut (CLUSTER), karena pgAdmin "View Data → All Rows" menampilkan
    urutan fisik tanpa ORDER BY. Tabel kecil (puluhan baris) sehingga cepat; kunci tabel hanya sampai commit.
    """
    db.flush()
    item = sorted((i for i in db.scalars(select(model)) if i is not baru), key=lambda i: i.no_urut)
    if urutan is not None:
        posisi = {iid: n for n, iid in enumerate(urutan)}
        item.sort(key=lambda i: posisi[i.id])
    if baru is not None:
        sebelum = [n for n, i in enumerate(item) if kunci_kode(i.kode) < kunci_kode(baru.kode)]
        letak = max(sebelum, key=lambda n: kunci_kode(item[n].kode)) + 1 if sebelum else 0
        item.insert(letak, baru)
    for n, i in enumerate(item, 1):
        i.no_urut = n
    rapikan_fisik(db, model.__tablename__, f"ix_{model.__tablename__}_no_urut")


class UrutanMasuk(BaseModel):
    """Isian Atur Urutan: semua id data sesuai urutan baru."""
    id: list[uuid.UUID]


def terapkan_urutan(db: Session, request: Request, model: ModelUrut, ids: list[uuid.UUID], aksi: str, label: str,
                    urut_kedua: InstrumentedAttribute) -> None:
    """Atur Urutan bersama (Checklist, Kategori, Panduan): hanya `no_urut` yang berubah — tidak membuat riwayat, jejak
    Diinput Oleh/Tanggal Input tetap. `ids` wajib memuat tepat semua id tabel (daftar di layar bisa basi bila ada data
    yang baru ditambah/dihapus). Dicatat di audit (`aksi`) dengan urutan sebelum & sesudah; commit oleh pemanggil.
    Error: 400 daftar tidak memuat tepat semua data (`label` = nama data di pesan, mis. "checklist")."""
    sebelum = [str(i) for i in db.scalars(select(model.id).order_by(model.no_urut, urut_kedua))]
    if len(ids) != len(sebelum) or set(map(str, ids)) != set(sebelum):
        raise Galat(400, f"Daftar {label} sudah berubah. Muat ulang halaman lalu atur urutan lagi.")
    urut_ulang(db, urutan=ids, model=model)
    catat(db, request, aksi, model.__tablename__, None, sebelum={"id": sebelum}, sesudah={"id": [str(i) for i in ids]})


def rapikan_fisik(db: Session, tabel: str, indeks: str) -> None:
    """CLUSTER tabel (urutan fisik untuk pgAdmin) hanya bila tidak sedang dipakai: tunggu kunci ≤1 detik, selain itu
    dilewati. Tanpa batas ini, simpan Admin menunggu worker yang sedang membaca checklist sambil menunggu jawaban AI,
    dan semua pembaca lain ikut antre. Urutan fisik dirapikan lagi pada simpan berikutnya; no_urut tetap benar.
    """
    db.flush()
    try:
        with db.begin_nested():
            db.execute(text("SET LOCAL lock_timeout = '1s'"))
            db.execute(text(f"CLUSTER {tabel} USING {indeks}"))  # nama tetap dari kode, bukan input pengguna
            db.execute(text("SET LOCAL lock_timeout = 0"))
    except OperationalError:  # kunci tidak didapat / deadlock → lewati
        pass


def isi_checklist(db: Session, waktu: datetime) -> list[IsiItem]:
    """Isi checklist (termasuk nonaktif) pada `waktu`, urut nomor urut."""
    item = db.scalars(select(ChecklistItem).where(ChecklistItem.created_date <= waktu)).all()
    versi: dict[str, list] = {}
    for h in db.scalars(select(ChecklistHistory).where(ChecklistHistory.updated_date <= waktu)):
        versi.setdefault(h.checklist_id, []).append(h)
    hasil = []
    for i in item:
        x = max([v for v in [i, *versi.get(i.id, [])] if v.updated_date <= waktu], key=lambda v: v.updated_date, default=i)
        hasil.append(IsiItem(i.id, x.kode, x.no_urut, x.checklist, x.kriteria, x.berlaku_untuk, x.aktif))
    return sorted(hasil, key=lambda r: (r.urutan, r.kode))


def isi_review(db: Session, review: Review) -> list[IsiItem]:
    """Item aktif yang dipakai review (`item_id` = id item pada hasil review). Kosong bila review belum dimulai."""
    return [r for r in isi_checklist(db, review.mulai_at) if r.aktif] if review.mulai_at else []


def sidik_checklist(isi: list[IsiItem]) -> str:
    """Hash isi checklist review untuk fingerprint (desain §4.6): isi sama → hasil AI boleh disalin."""
    return hashlib.sha256(repr([(i.kode, i.judul, i.kriteria, i.berlaku_untuk) for i in isi]).encode()).hexdigest()
