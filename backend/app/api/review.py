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
from app.model import CatatanReviewer, HasilItem, KategoriItem, Override, Pengguna, Review, Revisi, Usulan
from app.nilai_final import LOLOS, TERPENUHI, TIDAK_LOLOS, TIDAK_TERPENUHI

router = APIRouter(prefix="/api", tags=["review"])


def _ambil_review(db: Session, review_id: uuid.UUID, p: Pengguna, kunci: bool = False) -> tuple[Review, Revisi]:
    kueri = select(Review).where(Review.id == review_id)
    review = db.scalar(kueri.with_for_update() if kunci else kueri)
    if review is None:
        raise Galat(404, "Review tidak ditemukan.")
    revisi = db.get(Revisi, review.revisi_id)
    pastikan(boleh_lihat_usulan(p, db.get(Usulan, revisi.usulan_id)))
    return review, revisi


def _wajib_dapat_diubah(review: Review, revisi: Revisi) -> None:
    """Override/catatan hanya sebelum final (O5, O7) dan saat hasil AI tersedia."""
    if review.difinalkan_at is not None:
        raise Galat(409, "Review sudah difinalkan dan terkunci. Perubahan hanya melalui revisi baru dari Pengusul.")
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

    `nilai_sebelum` = nilai final saat ini (bisa nilai AI atau override sebelumnya) — tercatat untuk O4.
    Error: 400 alasan kosong / nilai tidak valid / nilai sama; 409 review sudah final.
    """
    review, revisi = _ambil_review(db, review_id, p, kunci=True)
    _wajib_dapat_diubah(review, revisi)
    alasan = data.alasan.strip()
    if not alasan:
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
        k = db.get(KategoriItem, uuid.UUID(data.nilai)) if _uuid_valid(data.nilai) else None
        if k is None or k.versi_id != review.kategori_versi_id:
            raise Galat(400, "Kategori tidak valid untuk versi kategori review ini.")
        sebelum = nf.kategori_id or ""
    if sebelum == data.nilai:
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
    _wajib_dapat_diubah(review, revisi)
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
    _wajib_dapat_diubah(review, revisi)
    c = db.scalar(select(CatatanReviewer).where(CatatanReviewer.review_id == review.id, CatatanReviewer.dokumen == data.dokumen))
    sebelum = c.teks if c else None
    if not data.teks.strip():
        if c:
            db.delete(c)
    elif c:
        c.teks, c.oleh = data.teks.strip(), p.id
    else:
        db.add(CatatanReviewer(review_id=review.id, dokumen=data.dokumen, teks=data.teks.strip(), oleh=p.id))
    catat(db, request, "CATATAN_REVIEWER", "review", review.id, sebelum={"dokumen": data.dokumen, "teks": sebelum},
          sesudah={"dokumen": data.dokumen, "teks": data.teks.strip()})
    db.commit()
    return detail_review(db, review, p)


@router.post("/review/{review_id}/finalkan")
def finalkan(review_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
             p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Kunci hasil review (O7). Nilai final disalin ke review sebagai snapshot; status revisi → LOLOS/TIDAK LOLOS."""
    review, revisi = _ambil_review(db, review_id, p, kunci=True)
    _wajib_dapat_diubah(review, revisi)
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
