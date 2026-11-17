"""Endpoint Modul D — Panduan (berversi, status Aktif/Nonaktif, hapus permanen D6, status pemrosesan).

Tiap panduan berversi: isi terkini di tabel `panduan`, versi sebelumnya (riwayat) di `panduan_histori`.
Panduan + versi yang dipakai tiap review disalin ke `review_panduan` (D5).
"""
import os
import uuid

from fastapi import APIRouter, Depends, File as FormFile, Form, Request, UploadFile
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.akses import PENGUSUL, REVIEWER, wajib_role
from app.audit import catat
from app.checklist import UrutanMasuk, terapkan_urutan, urut_ulang
from app.db import jam_db, sesi_db
from app.galat import Galat
from app.model import (Chunk, Elemen, File, Halaman, Job, Panduan, PanduanHistori, Pengguna, Review, ReviewPanduan, Revisi,
                       Rujukan)
from app.penyimpanan import path_absolut, simpan_unggahan

router = APIRouter(prefix="/api/panduan", tags=["panduan"])


def antrekan_ekstraksi(db: Session, f: File) -> None:
    """Antrekan pemrosesan file panduan bila belum siap/diproses (ekstraksi per file, D4)."""
    if f.status_ekstraksi in ("BELUM", "GAGAL"):
        f.status_ekstraksi, f.pesan_ekstraksi = "BELUM", None
        if db.scalar(select(Job.id).where(Job.ref_id == f.id, Job.status.in_(("ANTRE", "DIPROSES")))) is None:
            db.add(Job(jenis="PROSES_PANDUAN", ref_id=f.id, trace_id=uuid.uuid4().hex))


def _nama_acuan(judul: str) -> str:
    """Nama Acuan wajib, maks. 500 karakter (kolom `panduan`). Dicek sebelum PDF disimpan agar tidak ada file yatim."""
    judul = judul.strip()
    if not judul or len(judul) > 500:
        raise Galat(400, "Nama acuan wajib diisi, maksimal 500 karakter.")
    return judul


def _tandai(db: Session, pd: Panduan, p: Pengguna) -> None:
    """Catat pengubah & waktu perubahan terakhir (kolom "Diinput Oleh"/"Tanggal Input" di daftar panduan). Waktu dari
    jam DATABASE, sama seperti menu master lain."""
    pd.updated_by, pd.updated_date = p.id, jam_db(db)


def _versi(nomor: int, x: Panduan | PanduanHistori) -> dict:
    f = x.file
    return {"id": str(x.id), "nomor": nomor, "judul": x.panduan, "deskripsi": x.deskripsi, "file_id": str(f.id),
            "nama_file": x.nama_file, "aktif": x.aktif, "status_proses": f.status_ekstraksi, "pesan_gagal": f.pesan_ekstraksi,
            "jumlah_halaman": f.jumlah_halaman, "dibuat_at": x.updated_date.isoformat(),
            "dibuat_oleh": x.pengubah.nama if x.pengubah else None}


def _panduan(p: Panduan) -> dict:
    """Bentuk respons tetap: `versi` = [terkini (dari `panduan`), lalu riwayat terbaru dulu (dari `panduan_histori`)]."""
    versi = [_versi(n, x) for n, x in p.daftar_versi()]
    terkini = versi[0]
    return {"id": str(p.id), "urutan": p.no_urut, "judul": p.panduan, "aktif": p.aktif, "diubah_oleh": terkini["dibuat_oleh"],
            "diubah_at": terkini["dibuat_at"], "terkini": terkini, "versi": versi}


@router.get("")
def daftar(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(REVIEWER, PENGUSUL))) -> list[dict]:
    """Daftar panduan beserta versi & status proses. Reviewer & Pengusul dapat membaca panduan (D3); Admin tidak memiliki
    menu ini (desain.md §7 no. 29). Error: 403."""
    kueri = select(Panduan).order_by(Panduan.no_urut, Panduan.panduan)
    return [_panduan(p) for p in db.scalars(kueri)]


@router.put("/urutan")
def atur_urutan(data: UrutanMasuk, request: Request, db: Session = Depends(sesi_db),
                p: Pengguna = Depends(wajib_role(REVIEWER))) -> list[dict]:
    """Atur urutan panduan (`id` = semua id panduan sesuai urutan baru), seperti Checklist & Kategori. Hanya `no_urut`
    yang berubah: tidak membuat riwayat, Diinput Oleh/Tanggal Input tetap, dan review tidak terpengaruh.
    Didaftarkan sebelum PUT /{panduan_id} agar "urutan" tidak dicocokkan sebagai id.
    Output: daftar panduan urutan baru. Error: 400 daftar tidak memuat tepat semua panduan; 403."""
    terapkan_urutan(db, request, Panduan, data.id, "PANDUAN_URUTAN", "panduan", Panduan.panduan)
    db.commit()
    return daftar(db, p)


@router.post("")
def unggah(request: Request, file: UploadFile = FormFile(...), judul: str = Form(...), deskripsi: str | None = Form(None),
           aktif: bool = Form(True), db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Unggah satu PDF panduan beserta nama, deskripsi, dan status (D2). Error: 400 Nama Acuan tidak valid / file tidak valid."""
    judul = _nama_acuan(judul)
    f, nama = simpan_unggahan(db, file)
    # Panduan baru ditaruh di urutan paling akhir.
    akhir = db.scalar(select(func.coalesce(func.max(Panduan.no_urut), 0)))
    pd = Panduan(panduan=judul, deskripsi=(deskripsi or "").strip() or None, file_id=f.id, nama_file=nama,
                 aktif=aktif, no_urut=akhir + 1, created_by=p.id, updated_by=p.id)
    db.add(pd)
    db.flush()
    antrekan_ekstraksi(db, f)
    catat(db, request, "PANDUAN_UNGGAH", "panduan", pd.id, sesudah={"judul": judul, "file": nama, "sha256": f.sha256, "aktif": aktif})
    db.commit()
    db.refresh(pd)
    return _panduan(pd)


@router.put("/{panduan_id}")
def ubah(panduan_id: uuid.UUID, request: Request, judul: str = Form(...), deskripsi: str | None = Form(None),
         aktif: bool | None = Form(None), db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Ubah Nama Acuan/deskripsi/status (`aktif`, kosong = tetap) → isi lama disalin ke riwayat (`panduan_histori`),
    lalu `panduan` diperbarui sebagai versi baru (D9). File tidak dapat diganti (D2): unggah panduan baru.
    Yang Nonaktif tidak dipakai review berikutnya. Tanpa perubahan apa pun = tidak membuat versi. Error: 400 Nama Acuan tidak valid, 404."""
    # Kunci baris: dua edit bersamaan tidak boleh menyalin versi yang sama dua kali (nomor versi dihitung dari riwayat).
    pd = db.get(Panduan, panduan_id, with_for_update={"of": Panduan})
    if pd is None:
        raise Galat(404, "Panduan tidak ditemukan.")
    judul, deskripsi = _nama_acuan(judul), (deskripsi or "").strip() or None
    aktif = pd.aktif if aktif is None else aktif
    if (judul, deskripsi, aktif) == (pd.panduan, pd.deskripsi, pd.aktif):
        return _panduan(pd)
    # Baris terkini disalin utuh ke riwayat (termasuk pengunggah pertama & penginput versi itu), lalu panduan memuat versi baru.
    nomor_lama = len(pd.versi) + 1
    lama = PanduanHistori(created_by=pd.created_by, created_date=pd.created_date, updated_by=pd.updated_by,
                        updated_date=pd.updated_date, panduan_id=pd.id, panduan=pd.panduan, aktif=pd.aktif,
                        file_id=pd.file_id, nama_file=pd.nama_file, deskripsi=pd.deskripsi)
    db.add(lama)
    pd.panduan, pd.deskripsi, pd.aktif = judul, deskripsi, aktif
    _tandai(db, pd, p)
    catat(db, request, "PANDUAN_UBAH", "panduan", pd.id,
          sebelum={"versi": nomor_lama, "judul": lama.panduan, "deskripsi": lama.deskripsi, "aktif": lama.aktif},
          sesudah={"versi": nomor_lama + 1, "judul": judul, "deskripsi": deskripsi, "aktif": aktif})
    db.commit()
    db.refresh(pd)
    return _panduan(pd)


@router.delete("/{panduan_id}")
def hapus(panduan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Hapus PERMANEN panduan beserta semua versinya; file PDF + hasil ekstraksinya ikut dihapus bila tidak dipakai data lain.

    Keputusan pemilik produk 2026-10-19 (PRD v2 D6, lihat desain.md §7 no. 14): review lama kehilangan
    catatan panduan ini dan rujukan dasar panduannya. Error: 404; 409 bila dipakai review yang berjalan / file sedang diproses.
    """
    pd = db.get(Panduan, panduan_id)
    if pd is None:
        raise Galat(404, "Panduan tidak ditemukan.")
    jumlah_versi, file_ids = len(pd.versi) + 1, {pd.file_id, *(v.file_id for v in pd.versi)}
    # Hapus permanen (riwayat versi ikut terhapus) → isi semua versi disimpan di Audit Log agar tetap dapat ditelusuri,
    # sama seperti hapus Checklist/Kategori.
    sebelum = {"judul": pd.panduan, "jumlah_versi": jumlah_versi, "versi": [
        {"nomor": n, "judul": x.panduan, "deskripsi": x.deskripsi, "nama_file": x.nama_file, "aktif": x.aktif,
         "sha256": x.file.sha256, "diubah_at": x.updated_date.isoformat()} for n, x in pd.daftar_versi()]}
    # ponytail: review yang mengunci acuan bersamaan dengan hapus ini bisa gagal (FK); cukup diajukan ulang.
    if db.scalar(select(Review.id).join(ReviewPanduan, ReviewPanduan.review_id == Review.id)
                 .where(ReviewPanduan.panduan_id == pd.id, Review.status.in_(("ANTRE", "DIPROSES"))).limit(1)):
        raise Galat(409, "Panduan sedang dipakai review yang berjalan. Coba lagi setelah review selesai.")
    for fid in file_ids:  # worker memegang kunci yang sama selama ekstraksi (pekerja/proses_file.py)
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(hashtext(:id))"), {"id": str(fid)}):
            raise Galat(409, "File panduan sedang diproses. Coba lagi setelah selesai.")
    for tabel in (ReviewPanduan, PanduanHistori):
        db.execute(delete(tabel).where(tabel.panduan_id == pd.id))
    db.execute(delete(Panduan).where(Panduan.id == pd.id))
    urut_ulang(db, model=Panduan)  # no_urut sisanya dirapatkan lagi jadi 1..n
    path_dihapus = []
    for fid in file_ids:
        # File identik (SHA sama) bisa dipakai panduan lain (terkini/riwayat/salinan) atau TOR/RAB — biarkan.
        if any(db.scalar(select(kolom).where(kolom == fid).limit(1)) for kolom in (
                Panduan.file_id, PanduanHistori.file_id, ReviewPanduan.file_id)) or db.scalar(
                select(Revisi.id).where(or_(Revisi.tor_file_id == fid, Revisi.rab_file_id == fid)).limit(1)):
            continue
        db.execute(delete(Rujukan).where(Rujukan.elemen_id.in_(select(Elemen.id).where(Elemen.file_id == fid))))
        for tabel in (Chunk, Elemen, Halaman):
            db.execute(delete(tabel).where(tabel.file_id == fid))
        db.execute(delete(Job).where(Job.ref_id == fid))
        f = db.get(File, fid)
        path_dihapus.append(path_absolut(f))
        db.delete(f)
    catat(db, request, "PANDUAN_HAPUS", "panduan", panduan_id, sebelum={**sebelum, "file_dihapus": len(path_dihapus)})
    db.commit()
    for path in path_dihapus:  # setelah commit: bila transaksi gagal, PDF tetap ada
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    return {"ok": True}


@router.post("/{panduan_id}/proses-ulang")
def proses_ulang(panduan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Ulangi pemrosesan file panduan versi terkini yang GAGAL."""
    pd = db.get(Panduan, panduan_id)
    if pd is None:
        raise Galat(404, "Panduan tidak ditemukan.")
    f = pd.file
    if f.status_ekstraksi != "GAGAL":
        raise Galat(409, "Hanya panduan berstatus Gagal yang dapat diproses ulang.")
    antrekan_ekstraksi(db, f)
    catat(db, request, "PANDUAN_PROSES_ULANG", "panduan", pd.id)
    db.commit()
    db.refresh(pd)
    return _panduan(pd)
