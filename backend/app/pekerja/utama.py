"""Proses worker (layanan `worker`): ambil job dari antrean PostgreSQL dan jalankan.

- Antrean FIFO dengan `SELECT … FOR UPDATE SKIP LOCKED`: banyak worker di banyak node GPU dapat
  mengambil dari antrean yang sama tanpa koordinasi tambahan (desain §2.3).
- Detak (heartbeat) tiap 20 detik memperbarui `node_ai.terakhir_terlihat` dan `job.dikunci_at`.
  Job yang detaknya berhenti (worker mati) dilepas kembali ke antrean lalu dilanjutkan node lain.
"""
import logging
import platform
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update

from app import status as st
from app.db import SessionLokal
from app.keamanan import hash_token
from app.konfigurasi import konfigurasi
from app.log import bersihkan_konteks, log, set_konteks, siapkan_logging
from app.model import File, Job, NodeAI, Review, Revisi
from app.pekerja.llm import klien
from app.pekerja.proses_file import proses_file
from app.pekerja.review import jalankan_review

logger = logging.getLogger("pekerja")
DETAK_DETIK = 20
MAKS_PERCOBAAN = 3

_job_aktif: uuid.UUID | None = None


def daftar_node() -> uuid.UUID | None:
    """Node lokal didaftarkan otomatis; node jarak jauh harus memakai token yang diterbitkan Admin."""
    k = konfigurasi()
    with SessionLokal() as db:
        if k.node_token:
            node = db.scalar(select(NodeAI).where(NodeAI.token_hash == hash_token(k.node_token)))
            if node is None or not node.aktif:
                return None
        else:
            node = db.scalar(select(NodeAI).where(NodeAI.nama == k.node_nama))
            if node is None:
                node = NodeAI(nama=k.node_nama, aktif=True)
                db.add(node)
            elif not node.aktif:
                return None
        node.terakhir_terlihat = datetime.now(timezone.utc)
        node.info = {"host": platform.node(), "model": k.llm_model if not k.tiruan else "ai-tiruan", "profil": k.profil}
        db.commit()
        return node.id


def detak(node_id: uuid.UUID, berhenti: threading.Event) -> None:
    while not berhenti.wait(DETAK_DETIK):
        try:
            with SessionLokal() as db:
                db.execute(update(NodeAI).where(NodeAI.id == node_id).values(terakhir_terlihat=datetime.now(timezone.utc)))
                if _job_aktif:
                    db.execute(update(Job).where(Job.id == _job_aktif).values(dikunci_at=datetime.now(timezone.utc)))
                db.commit()
        except Exception:
            logger.exception("detak gagal")


def tandai_review_gagal(db, job: Job) -> None:
    review = db.get(Review, job.ref_id)
    if review is None or review.status not in ("ANTRE", "DIPROSES"):
        return
    review.status, review.selesai_at = "GAGAL", datetime.now(timezone.utc)
    review.error_pesan = f"Review AI gagal diproses. Silakan ajukan ulang. ID pelacakan: {review.trace_id}"
    revisi = db.get(Revisi, review.revisi_id)
    if revisi.status in (st.ANTRE, st.DIPROSES_AI):
        st.pindah_status(revisi, st.GAGAL)


def lepas_job_macet() -> None:
    """Kembalikan job yang worker-nya mati (detak berhenti) ke antrean; tandai gagal bila terlalu sering."""
    batas = datetime.now(timezone.utc) - timedelta(minutes=konfigurasi().job_batas_kunci_menit)
    with SessionLokal() as db:
        for job in db.scalars(select(Job).where(Job.status == "DIPROSES", Job.dikunci_at < batas).with_for_update(skip_locked=True)):
            job.status = "ANTRE" if job.percobaan < MAKS_PERCOBAAN else "GAGAL"
            if job.status == "GAGAL" and job.jenis == "REVIEW":
                tandai_review_gagal(db, job)
            log(logger, logging.WARNING, "job macet dilepas", job_id=str(job.id), status_baru=job.status, trace_id_job=job.trace_id)
        db.commit()


def ambil_job(node_nama: str) -> Job | None:
    with SessionLokal() as db:
        jid = db.execute(text(
            "UPDATE job SET status='DIPROSES', dikunci_at=now(), dikunci_oleh=:n, percobaan=percobaan+1 "
            "WHERE id = (SELECT id FROM job WHERE status='ANTRE' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) "
            "RETURNING id"), {"n": node_nama}).scalar()
        db.commit()
        return db.get(Job, jid) if jid else None


def jalankan_job(job: Job, llm) -> None:
    global _job_aktif
    _job_aktif = job.id
    bersihkan_konteks()
    set_konteks(trace_id=job.trace_id, job_id=job.id)
    status = "SELESAI"
    try:
        if job.jenis == "REVIEW":
            jalankan_review(job.ref_id, llm)
        elif job.jenis == "PROSES_PANDUAN":
            proses_file(job.ref_id, llm)
    except Exception:
        status = "GAGAL"
        logger.exception("job gagal")
    finally:
        _job_aktif = None
        with SessionLokal() as db:
            db.execute(update(Job).where(Job.id == job.id).values(status=status, selesai_at=datetime.now(timezone.utc)))
            if status == "GAGAL" and job.jenis == "REVIEW":  # jaga-jaga bila review belum sempat ditandai gagal
                tandai_review_gagal(db, job)
            if status == "GAGAL" and job.jenis == "PROSES_PANDUAN":
                db.execute(update(File).where(File.id == job.ref_id, File.status_ekstraksi == "DIPROSES").values(status_ekstraksi="GAGAL"))
            db.commit()
        bersihkan_konteks()


def main() -> None:
    siapkan_logging("worker.log")
    k = konfigurasi()
    llm = klien()
    log(logger, logging.INFO, "worker mulai", node=k.node_nama, ai_mode=k.ai_mode, ekstraktor=k.ekstraktor)
    node_id = None
    while node_id is None:
        node_id = daftar_node()
        if node_id is None:
            log(logger, logging.ERROR, "node tidak terdaftar atau dicabut Admin; menunggu", node=k.node_nama)
            time.sleep(60)
    berhenti = threading.Event()
    threading.Thread(target=detak, args=(node_id, berhenti), daemon=True).start()
    while True:
        try:
            if daftar_node() is None:  # dicabut saat berjalan → berhenti mengambil job
                time.sleep(60)
                continue
            lepas_job_macet()
            job = ambil_job(k.node_nama)
            if job is None:
                time.sleep(2)
                continue
            log(logger, logging.INFO, "job diambil", jenis=job.jenis, job_id=str(job.id), trace_id_job=job.trace_id)
            jalankan_job(job, llm)
        except Exception:
            logger.exception("kesalahan loop worker")
            time.sleep(5)


if __name__ == "__main__":
    main()
