"""Endpoint Dashboard + unduhan file berizin."""
import uuid

from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import status as st
from app.akses import ADMIN, boleh_lihat_semua, boleh_lihat_usulan, pastikan, pengguna_saat_ini
from app.api.usulan import baris_usulan, revisi_terbaru
from app.db import sesi_db
from app.galat import Galat
from app.keamanan import hash_token
from app.layanan_review import node_aktif
from app.model import File, Job, NodeAI, Panduan, PanduanHistori, Pengguna, Review, ReviewKategori, Revisi, Usulan
from app.penyimpanan import path_absolut

router = APIRouter(prefix="/api", tags=["dashboard & file"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Ringkasan jumlah usulan per status/kategori/Satker + daftar "Perlu tindakan saya".
    Admin juga melihat antrean AI, node aktif, dan perkiraan waktu selesai (desain §2.3)."""
    dasar = (select(Usulan, Revisi).join(Revisi, (Revisi.usulan_id == Usulan.id) & (Revisi.nomor == revisi_terbaru()))
             .where(Usulan.diarsipkan_at.is_(None)))
    if not boleh_lihat_semua(p):
        dasar = dasar.where(Usulan.satker_id == p.satker_id)
    baris = db.execute(dasar).all()

    per_status: dict[str, int] = {}
    per_satker: dict[str, dict] = {}
    for u, r in baris:
        per_status[r.status] = per_status.get(r.status, 0) + 1
        s = per_satker.setdefault(str(u.satker_id), {"satker": u.satker.nama, "total": 0, "lolos": 0, "tidak_lolos": 0, "proses": 0})
        s["total"] += 1
        s["lolos"] += r.status == st.LOLOS
        s["tidak_lolos"] += r.status == st.TIDAK_LOLOS
        s["proses"] += r.status not in (st.LOLOS, st.TIDAK_LOLOS)

    revisi_ids = [r.id for _, r in baris]
    per_kategori = dict(db.execute(
        select(ReviewKategori.kode, func.count())
        .join(Review, (Review.id == ReviewKategori.review_id) & (Review.kategori_final_id == ReviewKategori.kategori_id))
        .where(Review.revisi_id.in_(revisi_ids), Review.difinalkan_at.is_not(None)).group_by(ReviewKategori.kode)).all()) if revisi_ids else {}

    perlu = []
    roles = p.daftar_role
    for u, r in baris:
        if ("PENGUSUL" in roles and u.satker_id == p.satker_id and r.status in (st.DRAF, st.GAGAL, st.TIDAK_LOLOS)) or \
           ("REVIEWER" in roles and r.status == st.MENUNGGU_VERIFIKASI):
            perlu.append(u)
    perlu.sort(key=lambda u: u.updated_at)
    data = {"total": len(baris), "per_status": per_status, "per_kategori": per_kategori,
            "per_satker": sorted(per_satker.values(), key=lambda s: s["satker"]),
            "perlu_tindakan": [baris_usulan(db, u, p) for u in perlu[:20]]}

    if ADMIN in roles:
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

    Boleh bila: file panduan (semua pengguna), atau TOR/RAB dari usulan yang boleh dilihat pengguna.
    Error: 404 bila tidak ada atau tidak berhak (tidak membocorkan keberadaan file).
    """
    f = db.get(File, file_id)
    if f is None:
        raise Galat(404, "File tidak ditemukan.")
    boleh = any(db.scalar(select(kolom).where(kolom == f.id).limit(1)) for kolom in (Panduan.file_id, PanduanHistori.file_id))
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
