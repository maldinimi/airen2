"""Endpoint Detail Review: lihat hasil, override (O1–O6), catatan reviewer, finalisasi (O7–O8)."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import status as st
from app.akses import REVIEWER, boleh_lihat_usulan, pastikan, pengguna_saat_ini, wajib_role
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.layanan_review import detail_review, nilai_final_review, review_terbaru
from app.model import CatatanItem, CatatanReviewer, HasilItem, HasilKategori, Override, Pengguna, Review, ReviewKategori, Revisi, Usulan
from app.nilai_final import LOLOS, TERPENUHI, TIDAK_LOLOS, TIDAK_TERPENUHI, override_aktif

router = APIRouter(prefix="/api", tags=["review"])


def _ambil_review(db: Session, review_id: uuid.UUID, p: Pengguna, kunci: bool = False) -> tuple[Review, Revisi]:
    kueri = select(Review).where(Review.id == review_id)
    review = db.scalar(kueri.with_for_update() if kunci else kueri)
    if review is None:
        raise Galat(404, "Review tidak ditemukan.")
    revisi = db.get(Revisi, review.revisi_id)
    pastikan(boleh_lihat_usulan(p, db.get(Usulan, revisi.usulan_id)))
    return review, revisi


def _wajib_dapat_diubah(db: Session, review: Review, revisi: Revisi) -> None:
    """Override/catatan hanya sebelum final (O5, O7), saat hasil AI tersedia, dan hanya pada review terbaru revisi itu.
    Review lama tersisa bila Reviewer mengganti dokumen lewat Edit Usulan (revisi yang sama direview ulang, desain.md §7
    no. 36); memfinalkannya akan menetapkan status revisi dari dokumen yang sudah diganti."""
    if review.difinalkan_at is not None:
        raise Galat(409, "Review sudah difinalkan dan terkunci. Perubahan hanya melalui revisi baru dari Pengusul.")
    if review_terbaru(db, revisi.id).id != review.id:
        raise Galat(409, "Dokumen revisi ini sudah diganti dan direview ulang. Muat ulang halaman untuk membuka review terbaru.")
    if review.status != "SELESAI" or revisi.status != st.MENUNGGU_VERIFIKASI:
        raise Galat(409, "Review belum siap diverifikasi.")


@router.get("/review/{review_id}")
def lihat(review_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Detail review sesuai role. Pengusul: hasil AI segera; override/catatan setelah final."""
    review, _ = _ambil_review(db, review_id, p)
    return detail_review(db, review, p)


@router.get("/revisi/{revisi_id}/review")
def lihat_per_revisi(revisi_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Review terbaru dari suatu revisi."""
    review = review_terbaru(db, revisi_id)
    if review is None:
        raise Galat(404, "Revisi ini belum pernah diajukan review.")
    return lihat(review.id, db, p)


class OverrideMasuk(BaseModel):
    target: Literal["ITEM", "LABEL", "KATEGORI"]
    checklist_item_id: uuid.UUID | None = None
    nilai: str
    alasan: str


@router.post("/review/{review_id}/override")
def override(review_id: uuid.UUID, data: OverrideMasuk, request: Request, db: Session = Depends(sesi_db),
             p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Override status item / label / kategori. Hasil AI tidak diubah; override disimpan terpisah (O2).

    ITEM = penilaian verifikator per item: Status & Catatan Verifikator (catatan opsional, nilai boleh sama dengan AI
    sebagai konfirmasi; desain.md §7 no. 29). LABEL/KATEGORI: alasan wajib & nilai harus berbeda.
    `nilai_sebelum` = nilai final saat ini (bisa nilai AI atau override sebelumnya) — tercatat untuk O4.
    Error: 400 alasan kosong / nilai tidak valid / nilai sama; 409 review sudah final.
    """
    review, revisi = _ambil_review(db, review_id, p, kunci=True)
    _wajib_dapat_diubah(db, review, revisi)
    alasan = data.alasan.strip()
    if not alasan and data.target != "ITEM":
        raise Galat(400, "Alasan override wajib diisi.")
    nf, _ = nilai_final_review(db, review, True)
    if data.target == "ITEM":
        if data.nilai not in (TERPENUHI, TIDAK_TERPENUHI) or data.checklist_item_id is None:
            raise Galat(400, "Nilai override item tidak valid.")
        if db.scalar(select(HasilItem).where(HasilItem.review_id == review.id, HasilItem.checklist_item_id == data.checklist_item_id)) is None:
            raise Galat(400, "Item checklist tidak termasuk review ini.")
        sebelum = TERPENUHI if nf.item[str(data.checklist_item_id)] else TIDAK_TERPENUHI
    elif data.target == "LABEL":
        if data.nilai not in (LOLOS, TIDAK_LOLOS):
            raise Galat(400, "Nilai label tidak valid.")
        sebelum = nf.label
    else:
        k = db.get(ReviewKategori, (review.id, uuid.UUID(data.nilai))) if _uuid_valid(data.nilai) else None
        if k is None:
            raise Galat(400, "Kategori tidak termasuk daftar kategori review ini.")
        sebelum = nf.kategori_id or ""
    if sebelum == data.nilai and data.target != "ITEM":
        raise Galat(400, "Nilai baru sama dengan nilai saat ini.")
    o = Override(review_id=review.id, target=data.target, checklist_item_id=data.checklist_item_id if data.target == "ITEM" else None,
                 nilai_sebelum=sebelum, nilai_sesudah=data.nilai, alasan=alasan, oleh=p.id)
    db.add(o)
    db.flush()
    catat(db, request, "OVERRIDE", "review", review.id,
          sebelum={"target": data.target, "item": str(data.checklist_item_id) if data.checklist_item_id else None, "nilai": sebelum},
          sesudah={"nilai": data.nilai, "alasan": alasan, "override_id": str(o.id)})
    db.commit()
    return detail_review(db, review, p)


def _uuid_valid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False


@router.post("/override/{override_id}/batal")
def batal_override(override_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                   p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Batalkan override (kembali ke nilai sebelumnya/AI) selama belum final (O5). Riwayat tetap tersimpan."""
    o = db.get(Override, override_id)
    if o is None or o.dibatalkan_at is not None:
        raise Galat(404, "Override tidak ditemukan atau sudah dibatalkan.")
    review, revisi = _ambil_review(db, o.review_id, p, kunci=True)
    _wajib_dapat_diubah(db, review, revisi)
    o.dibatalkan_at = datetime.now(timezone.utc)
    o.dibatalkan_oleh = p.id
    catat(db, request, "BATAL_OVERRIDE", "review", review.id, sebelum={"override_id": str(o.id), "nilai": o.nilai_sesudah})
    db.commit()
    return detail_review(db, review, p)


class CatatanMasuk(BaseModel):
    dokumen: Literal["TOR", "RAB", "UMUM"]
    teks: str


@router.put("/review/{review_id}/catatan")
def simpan_catatan(review_id: uuid.UUID, data: CatatanMasuk, request: Request, db: Session = Depends(sesi_db),
                   p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Tambah/ubah catatan reviewer untuk Pengusul (teks kosong = hapus). Disembunyikan dari Pengusul sebelum final."""
    review, revisi = _ambil_review(db, review_id, p, kunci=True)
    _wajib_dapat_diubah(db, review, revisi)
    _simpan_catatan(db, request, review, data.dokumen, data.teks, p)
    db.commit()
    return detail_review(db, review, p)


def _simpan_catatan(db: Session, request: Request, review: Review, dokumen: str, teks: str, p: Pengguna) -> None:
    """Upsert satu catatan reviewer per dokumen (teks kosong = hapus) + audit log."""
    c = db.scalar(select(CatatanReviewer).where(CatatanReviewer.review_id == review.id, CatatanReviewer.dokumen == dokumen))
    sebelum = c.teks if c else None
    if not teks.strip():
        if c:
            db.delete(c)
    elif c:
        c.teks, c.oleh = teks.strip(), p.id
    else:
        db.add(CatatanReviewer(review_id=review.id, dokumen=dokumen, teks=teks.strip(), oleh=p.id))
    catat(db, request, "CATATAN_REVIEWER", "review", review.id, sebelum={"dokumen": dokumen, "teks": sebelum},
          sesudah={"dokumen": dokumen, "teks": teks.strip()})


class ItemKeputusan(BaseModel):
    checklist_item_id: uuid.UUID
    nilai: Literal["TERPENUHI", "TIDAK_TERPENUHI"]
    catatan: str = ""


class KeputusanMasuk(BaseModel):
    label: Literal["LOLOS", "TIDAK_LOLOS"] | None = None
    catatan: str = ""
    item: list[ItemKeputusan] = []
    kategori_id: uuid.UUID | None = None  # kategori pilihan verifikator (dari salinan kategori review ini)
    catatan_kategori: str | None = None   # Catatan Verifikator tabel Kategori (catatan reviewer dokumen "KATEGORI")


def _simpan_kategori(db: Session, request: Request, review: Review, data: KeputusanMasuk, p: Pengguna) -> None:
    """Kategori pilihan verifikator (tabel Kategori, desain.md §7 no. 37): override KATEGORI bila berbeda dari rekomendasi AI
    (dibatalkan bila sama), catatannya sebagai catatan reviewer "KATEGORI". Error: 400 kategori bukan milik review ini."""
    if data.kategori_id is not None:
        if db.get(ReviewKategori, (review.id, data.kategori_id)) is None:
            raise Galat(400, "Kategori tidak termasuk daftar kategori review ini.")
        nf, overrides = nilai_final_review(db, review, True)
        ai = db.scalar(select(HasilKategori.kategori_item_id).where(HasilKategori.review_id == review.id))
        aktif = override_aktif(overrides).get(("KATEGORI", None))
        if data.kategori_id == ai:
            if aktif is not None:
                aktif.dibatalkan_at, aktif.dibatalkan_oleh = datetime.now(timezone.utc), p.id
        elif aktif is None or aktif.nilai_sesudah != str(data.kategori_id):
            db.add(Override(review_id=review.id, target="KATEGORI", nilai_sebelum=nf.kategori_id or "", nilai_sesudah=str(data.kategori_id),
                            alasan=(data.catatan_kategori or "").strip() or "Kategori pilihan verifikator.", oleh=p.id))
    if data.catatan_kategori is not None:
        _simpan_catatan(db, request, review, "KATEGORI", data.catatan_kategori, p)


def _simpan_item(db: Session, review: Review, daftar: list[ItemKeputusan], p: Pengguna) -> None:
    """Status & Catatan Verifikator per item dari halaman Pemeriksaan (desain.md §7 no. 33). Status disimpan sebagai override
    ITEM hanya bila berbeda dari override aktif (hasil AI tidak diubah, O2); catatan di `catatan_item` (kosong = hapus).
    Error: 400 item tidak termasuk review ini."""
    if not daftar:
        return
    milik = set(db.scalars(select(HasilItem.checklist_item_id).where(HasilItem.review_id == review.id)))
    if any(x.checklist_item_id not in milik for x in daftar):
        raise Galat(400, "Item checklist tidak termasuk review ini.")
    nf, overrides = nilai_final_review(db, review, True)
    aktif = override_aktif(overrides)
    catatan = {c.checklist_item_id: c for c in db.scalars(select(CatatanItem).where(CatatanItem.review_id == review.id))}
    for x in daftar:
        iid, teks = str(x.checklist_item_id), x.catatan.strip()
        o = aktif.get(("ITEM", iid))
        if o is None or o.nilai_sesudah != x.nilai:
            db.add(Override(review_id=review.id, target="ITEM", checklist_item_id=x.checklist_item_id,
                            nilai_sebelum=TERPENUHI if nf.item[iid] else TIDAK_TERPENUHI, nilai_sesudah=x.nilai, alasan=teks, oleh=p.id))
        c = catatan.get(x.checklist_item_id)
        if not teks:
            if c:
                db.delete(c)
        elif c is None:
            db.add(CatatanItem(review_id=review.id, checklist_item_id=x.checklist_item_id, teks=teks, oleh=p.id))
        elif c.teks != teks:
            c.teks, c.oleh = teks, p.id


def _simpan_keputusan(db: Session, request: Request, review: Review, data: KeputusanMasuk, p: Pengguna) -> None:
    """Simpan penilaian verifikator tanpa mengunci: status & catatan per item, catatan akhir (catatan UMUM), dan label. Label
    pilihan verifikator disimpan sebagai override LABEL bila berbeda dari label hitungan item (dibatalkan bila sama), sehingga
    tetap terpilih saat halaman dibuka lagi dan tetap tersembunyi dari Pengusul sebelum final (O2, O4)."""
    _simpan_kategori(db, request, review, data, p)
    _simpan_item(db, review, data.item, p)
    _simpan_catatan(db, request, review, "UMUM", data.catatan, p)
    if data.label is not None:
        nf, overrides = nilai_final_review(db, review, True)  # setelah item di atas (autoflush)
        aktif = override_aktif(overrides).get(("LABEL", None))
        if data.label == nf.label_hitung:
            if aktif is not None:
                aktif.dibatalkan_at, aktif.dibatalkan_oleh = datetime.now(timezone.utc), p.id
        elif aktif is None or aktif.nilai_sesudah != data.label:
            db.add(Override(review_id=review.id, target="LABEL", nilai_sebelum=nf.label, nilai_sesudah=data.label,
                            alasan=data.catatan.strip() or "Keputusan akhir verifikator.", oleh=p.id))
    catat(db, request, "KEPUTUSAN_AKHIR", "review", review.id, sesudah={
        "label": data.label, "jumlah_item": len(data.item), "kategori_id": str(data.kategori_id) if data.kategori_id else None})


@router.put("/review/{review_id}/keputusan")
def simpan_keputusan(review_id: uuid.UUID, data: KeputusanMasuk, request: Request, db: Session = Depends(sesi_db),
                     p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Tombol "Simpan Sebagai Draf": simpan status & catatan per item serta Keputusan Akhir tanpa memfinalkan. Penilaian
    yang belum disimpan hanya ada di halaman (hilang bila dimuat ulang), desain.md §7 no. 33.
    Error: 409 review sudah final / belum siap diverifikasi."""
    review, revisi = _ambil_review(db, review_id, p, kunci=True)
    _wajib_dapat_diubah(db, review, revisi)
    _simpan_keputusan(db, request, review, data, p)
    db.commit()
    return detail_review(db, review, p)


@router.post("/review/{review_id}/finalkan")
def finalkan(review_id: uuid.UUID, request: Request, data: KeputusanMasuk | None = None, db: Session = Depends(sesi_db),
             p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Kunci hasil review (O7). Nilai final disalin ke review sebagai snapshot; status revisi → LOLOS/TIDAK LOLOS.

    Kartu Keputusan Akhir: body = keputusan verifikator (disimpan seperti draf, lalu dikunci). Tanpa body: nilai final
    saat ini (label hitungan item atau override/draf keputusan yang sudah tersimpan).
    """
    review, revisi = _ambil_review(db, review_id, p, kunci=True)
    _wajib_dapat_diubah(db, review, revisi)
    if data is not None:
        _simpan_keputusan(db, request, review, data, p)
    nf, overrides = nilai_final_review(db, review, True)
    review.label_final = nf.label
    review.kategori_final_id = uuid.UUID(nf.kategori_id) if nf.kategori_id else None
    review.difinalkan_oleh = p.id
    review.difinalkan_at = datetime.now(timezone.utc)
    st.pindah_status(revisi, st.LOLOS if nf.label == LOLOS else st.TIDAK_LOLOS)
    catat(db, request, "FINALKAN_REVIEW", "review", review.id, sesudah={
        "label_final": nf.label, "kategori_final_id": nf.kategori_id,
        "jumlah_override": sum(1 for o in overrides if o.dibatalkan_at is None)})
    db.commit()
    return detail_review(db, review, p)
