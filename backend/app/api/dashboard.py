"""Endpoint Dashboard + unduhan file berizin."""
import uuid

from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import status as st
from app.akses import ADMIN, PENGUSUL, REVIEWER, boleh_lihat_semua, boleh_lihat_usulan, pastikan, pengguna_saat_ini, wajib_role
from app.api.usulan import revisi_terbaru
from app.db import sesi_db
from app.galat import Galat
from app.keamanan import hash_token
from app.layanan_review import node_aktif
from app.model import (ChecklistItem, File, HasilItem, Job, Kategori, NodeAI, Override, Panduan, PanduanHistori, Pengguna, Review,
                       ReviewKategori, Revisi, Usulan)
from app.nilai_final import TERPENUHI
from app.penyimpanan import path_absolut

router = APIRouter(prefix="/api", tags=["dashboard & file"])


def _saring(kueri, p: Pengguna, tahun: int | None):
    """Batas data Dashboard (kueri harus memuat tabel `usulan`): pengajuan yang tidak diarsipkan, Satker sendiri bagi Pengusul,
    dan Tahun Anggaran pilihan header bila dikirim (sama dengan daftar Pengajuan, desain.md §7 no. 75)."""
    kueri = kueri.where(Usulan.diarsipkan_at.is_(None))
    if not boleh_lihat_semua(p):
        kueri = kueri.where(Usulan.satker_id == p.satker_id)
    return kueri if tahun is None else kueri.where(Usulan.tahun_anggaran == tahun)


def _kategori_lolos(db: Session, revisi_ids: list[uuid.UUID]) -> list[dict]:
    """Pengusul: jumlah pengajuan yang Lolos (keputusan akhir verifikator) per kategori final. Semua kategori Aktif tampil
    (0 bila belum ada), urut seperti menu Kategori; kategori final yang kini Nonaktif/terhapus ditambahkan di akhir.
    Kategori final dibaca dari salinan kategori review itu sendiri (setiap review menyalin semua kategori dengan id sama)."""
    hitung: dict[str, list] = {}
    if revisi_ids:
        for kode, nama, n in db.execute(
                select(ReviewKategori.kode, ReviewKategori.nama, func.count())
                .join(Review, (Review.id == ReviewKategori.review_id) & (Review.kategori_final_id == ReviewKategori.kategori_id))
                .where(Review.revisi_id.in_(revisi_ids), Review.difinalkan_at.is_not(None))
                .group_by(ReviewKategori.kode, ReviewKategori.nama)):
            hitung.setdefault(kode, [nama, 0])[1] += n
    aktif = db.execute(select(Kategori.kode, Kategori.kategori).where(Kategori.aktif).order_by(Kategori.no_urut)).all()
    return ([{"kode": k, "nama": nm, "jumlah": hitung.pop(k, [nm, 0])[1]} for k, nm in aktif]
            + [{"kode": k, "nama": nm, "jumlah": n} for k, (nm, n) in hitung.items()])


def _checklist_tidak_lolos(db: Session, usulan_ids: list[uuid.UUID]) -> list[dict]:
    """Pengusul: item checklist yang Tidak Lolos pada pengajuan Satker-nya, dihitung per **pemeriksaan** = review berhasil
    terakhir di setiap revisi, termasuk revisi lama (docs/asumsi.md, desain.md §7 no. 75):
    - `ai`: pemeriksaan dengan hasil AI tidak terpenuhi;
    - `verifikator`: pemeriksaan yang sudah final dengan nilai final tidak terpenuhi (override ITEM aktif terakhir, selain
      itu nilai AI — sama dengan app/nilai_final.py, O8).
    Item yang dihapus permanen tidak ditampilkan (namanya tidak tersimpan). Output urut seperti menu Checklist."""
    if not usulan_ids:
        return []
    review: dict[uuid.UUID, tuple] = {}  # revisi → (review, final?, pengajuan, nomor revisi); yang dibuat terakhir menang
    for rid, revisi_id, final, usulan_id, nomor in db.execute(
            select(Review.id, Review.revisi_id, Review.difinalkan_at.is_not(None), Revisi.usulan_id, Revisi.nomor)
            .join(Revisi, Revisi.id == Review.revisi_id)
            .where(Revisi.usulan_id.in_(usulan_ids), Review.status == "SELESAI").order_by(Review.created_at)):
        review[revisi_id] = (rid, final, usulan_id, nomor)
    if not review:
        return []
    final_per_review = {rid: final for rid, final, _, _ in review.values()}
    override: dict[tuple, bool] = {}  # (review, item) → override ITEM aktif terakhir
    for rid, iid, nilai in db.execute(
            select(Override.review_id, Override.checklist_item_id, Override.nilai_sesudah)
            .where(Override.review_id.in_(list(final_per_review)), Override.target == "ITEM", Override.dibatalkan_at.is_(None))
            .order_by(Override.created_at)):
        override[(rid, iid)] = nilai == TERPENUHI
    per_item: dict[uuid.UUID, dict] = {}
    for rid, iid, ai in db.execute(select(HasilItem.review_id, HasilItem.checklist_item_id, HasilItem.terpenuhi)
                                   .where(HasilItem.review_id.in_(list(final_per_review)))):
        gagal_verifikator = final_per_review[rid] and not override.get((rid, iid), ai)
        if ai and not gagal_verifikator:
            continue
        t = per_item.setdefault(iid, {"ai": 0, "verifikator": 0})
        t["ai"] += not ai
        t["verifikator"] += gagal_verifikator
    if not per_item:
        return []
    return [{"kode": k, "checklist": c, **per_item[i]} for i, k, c in db.execute(
        select(ChecklistItem.id, ChecklistItem.kode, ChecklistItem.checklist).where(ChecklistItem.id.in_(list(per_item)))
        .order_by(ChecklistItem.no_urut))]


@router.get("/dashboard")
def dashboard(tahun: int | None = None, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(PENGUSUL, REVIEWER))) -> dict:
    """Ringkasan Dashboard (hanya informasi, tanpa daftar tindakan), desain.md §7 no. 75. `tahun` = Tahun Anggaran pilihan
    header (tanpa = semua tahun). Semua role: jumlah per status. Reviewer: `per_satker` (Total, Lolos, Tidak Lolos,
    Menunggu Verifikasi). Pengusul (Satker sendiri): `kategori_lolos` dan `checklist_tidak_lolos`.
    Pengusul & Reviewer saja (Admin tidak memiliki menu Dashboard → 403). Pengguna yang juga ber-role Admin melihat antrean
    AI, node aktif, dan perkiraan waktu selesai (desain §2.3)."""
    dasar = select(Usulan, Revisi).join(Revisi, (Revisi.usulan_id == Usulan.id) & (Revisi.nomor == revisi_terbaru()))
    baris = db.execute(_saring(dasar, p, tahun)).all()

    per_status: dict[str, int] = {}
    per_satker: dict[str, dict] = {}
    for u, r in baris:
        per_status[r.status] = per_status.get(r.status, 0) + 1
        s = per_satker.setdefault(str(u.satker_id), {"satker": u.satker.nama, "total": 0, "lolos": 0, "tidak_lolos": 0, "menunggu": 0})
        s["total"] += 1
        s["lolos"] += r.status == st.LOLOS
        s["tidak_lolos"] += r.status == st.TIDAK_LOLOS
        s["menunggu"] += r.status == st.MENUNGGU_VERIFIKASI

    data = {"total": len(baris), "per_status": per_status,
            "per_satker": sorted(per_satker.values(), key=lambda s: s["satker"])}
    if not boleh_lihat_semua(p):
        data["kategori_lolos"] = _kategori_lolos(db, [r.id for _, r in baris if r.status == st.LOLOS])
        data["checklist_tidak_lolos"] = _checklist_tidak_lolos(db, [u.id for u, _ in baris])

    if ADMIN in p.daftar_role:
        aktif = node_aktif(db)
        antre = db.scalar(select(func.count()).select_from(Job).where(Job.status == "ANTRE", Job.jenis == "REVIEW"))
        diproses = db.scalar(select(func.count()).select_from(Job).where(Job.status == "DIPROSES", Job.jenis == "REVIEW"))
        durasi = db.scalars(select(func.extract("epoch", Review.selesai_at - Review.mulai_at))
                            .where(Review.status == "SELESAI", Review.disalin_dari_id.is_(None), Review.mulai_at.is_not(None))
                            .order_by(Review.selesai_at.desc()).limit(20)).all()
        rata = float(sum(durasi) / len(durasi)) / 60 if durasi else None
        data["antrean"] = {
            "antre": antre, "diproses": diproses, "rata_menit_per_review": round(rata, 1) if rata else None,
            "perkiraan_selesai_menit": round((antre + diproses) * rata / len(aktif)) if rata and aktif else None,
            "node": [{"nama": n.nama, "terakhir_terlihat": n.terakhir_terlihat.isoformat(), "info": n.info} for n in aktif],
        }
    return data


@router.get("/file/{file_id}")
def unduh(file_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> FileResponse:
    """Unduh/tampilkan PDF dengan pemeriksaan hak akses (bukan URL statis).

    Boleh bila: file panduan bagi Reviewer & Pengusul (sama dengan hak baca GET /api/panduan; Admin tidak memiliki
    menu Panduan), atau TOR/RAB dari usulan yang boleh dilihat pengguna.
    Error: 404 bila tidak ada atau tidak berhak (tidak membocorkan keberadaan file).
    """
    f = db.get(File, file_id)
    if f is None:
        raise Galat(404, "File tidak ditemukan.")
    boleh = bool(p.daftar_role & {REVIEWER, PENGUSUL}) and any(
        db.scalar(select(kolom).where(kolom == f.id).limit(1)) for kolom in (Panduan.file_id, PanduanHistori.file_id))
    if not boleh:
        for u in db.scalars(select(Usulan).join(Revisi, Revisi.usulan_id == Usulan.id)
                            .where(or_(Revisi.tor_file_id == f.id, Revisi.rab_file_id == f.id)).distinct()):
            if boleh_lihat_usulan(p, u):
                boleh = True
                break
    if not boleh:
        raise Galat(404, "File tidak ditemukan.")
    return FileResponse(path_absolut(f), media_type="application/pdf", filename=f.nama_asli,
                        content_disposition_type="inline", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/internal/file/{sha}")
def unduh_internal(sha: str, authorization: str = Header(""), db: Session = Depends(sesi_db)) -> FileResponse:
    """Dipakai node AI jarak jauh (GPU sewaan) untuk mengambil PDF saat job berjalan (desain §2.4).
    Otorisasi: `Authorization: Bearer <token node>`; node yang dicabut ditolak."""
    token = authorization.removeprefix("Bearer ").strip()
    node = db.scalar(select(NodeAI).where(NodeAI.token_hash == hash_token(token), NodeAI.aktif)) if token else None
    pastikan(node is not None, "Token node tidak valid.")
    f = db.scalar(select(File).where(File.sha256 == sha))
    if f is None:
        raise Galat(404, "File tidak ditemukan.")
    return FileResponse(path_absolut(f), media_type="application/pdf")
