"""Pemrosesan satu file PDF: ekstraksi → deskripsi gambar (VLM) → simpan elemen → chunk + embedding.

Hasil disimpan per file (SHA) dan dipakai ulang oleh revisi/review berikutnya. Advisory lock
PostgreSQL mencegah dua worker memproses file yang sama bersamaan.
"""
import logging
import os
import tempfile
from contextlib import contextmanager

import httpx
from sqlalchemy import delete, text

from app.db import SessionLokal
from app.konfigurasi import konfigurasi
from app.log import tahap
from app.model import Chunk, Elemen, File, Halaman
from app.pekerja.ekstraksi import ekstrak, potong_gambar
from app.pekerja.pencarian import buat_chunk
from app.pekerja.prompt import PROMPT_GAMBAR, SKEMA_GAMBAR
from app.penyimpanan import path_absolut

logger = logging.getLogger("pekerja.proses_file")


class GalatPengguna(Exception):
    """Error dengan pesan yang aman & ramah ditampilkan ke pengguna."""


@contextmanager
def berkas_kerja(f: File):
    """Path lokal file PDF. Node jarak jauh (SUMBER_FILE=api) mengambil PDF lewat API internal ke tmpfs
    dan menghapusnya begitu selesai — tidak ada dokumen tertinggal di mesin sewaan (desain §2.4)."""
    k = konfigurasi()
    if k.sumber_file == "lokal":
        yield path_absolut(f)
        return
    fd, path = tempfile.mkstemp(suffix=".pdf", dir=os.environ.get("FOLDER_KERJA", "/tmp/kerja"))
    try:
        with os.fdopen(fd, "wb") as keluar, httpx.stream(
                "GET", f"{k.api_internal_url}/api/internal/file/{f.sha256}",
                headers={"Authorization": f"Bearer {k.node_token}"}, timeout=600) as r:
            r.raise_for_status()
            for potongan in r.iter_bytes():
                keluar.write(potongan)
        yield path
    finally:
        os.remove(path)


def proses_file(file_id, llm) -> None:
    """Pastikan file sudah diekstraksi (status SIAP). Idempoten.

    Error: GalatPengguna (pesan ramah) bila PDF tidak dapat dibaca; error lain diteruskan.
    """
    with SessionLokal() as kunci:
        kunci.execute(text("SELECT pg_advisory_lock(hashtext(:id))"), {"id": str(file_id)})
        try:
            with SessionLokal() as db:
                f = db.get(File, file_id)
                if f.status_ekstraksi == "SIAP":
                    return
                f.status_ekstraksi, f.pesan_ekstraksi = "DIPROSES", None
                db.commit()
                try:
                    with tahap(logger, "ekstraksi file", file_id=str(f.id), halaman=f.jumlah_halaman):
                        _proses(db, f, llm)
                except Exception as e:
                    db.rollback()
                    f = db.get(File, file_id)
                    f.status_ekstraksi = "GAGAL"
                    f.pesan_ekstraksi = "PDF tidak dapat dibaca/diproses. Periksa file lalu unggah ulang." \
                        if not isinstance(e, GalatPengguna) else str(e)
                    db.commit()
                    raise GalatPengguna(f"Gagal memproses file '{f.nama_asli}': {f.pesan_ekstraksi}") from e
        finally:
            kunci.execute(text("SELECT pg_advisory_unlock(hashtext(:id))"), {"id": str(file_id)})


def _proses(db, f: File, llm) -> None:
    k = konfigurasi()
    with berkas_kerja(f) as path:
        halaman, elemen = ekstrak(path)
        for e in elemen:
            if e.jenis == "gambar":
                hasil = llm.json("gambar", PROMPT_GAMBAR, SKEMA_GAMBAR, gambar=potong_gambar(path, e.halaman, e.bbox),
                                 konteks={"halaman": e.halaman})
                e.teks, e.sumber = (hasil.get("deskripsi") or "").strip(), "vlm"
    for model in (Chunk, Elemen, Halaman):  # sisa percobaan sebelumnya yang gagal
        db.execute(delete(model).where(model.file_id == f.id))
    db.add_all(Halaman(file_id=f.id, nomor=h.nomor, lebar=h.lebar, tinggi=h.tinggi, hasil_scan=h.hasil_scan) for h in halaman)
    baris = [Elemen(file_id=f.id, halaman=e.halaman, urutan=i, jenis=e.jenis, label_lokasi=e.label_lokasi[:500],
                    teks=e.teks, bbox=e.bbox, sumber=e.sumber) for i, e in enumerate(elemen) if e.teks.strip()]
    if not baris:
        raise GalatPengguna("Tidak ada teks yang dapat dibaca dari PDF ini.")
    db.add_all(baris)
    db.flush()
    buat_chunk(db, f.id, baris)
    f.status_ekstraksi, f.ekstraktor = "SIAP", k.ekstraktor
    db.commit()
