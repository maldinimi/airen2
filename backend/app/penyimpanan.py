"""Penyimpanan file PDF: nama file = SHA-256 isi, tidak pernah ditimpa (rujukan review lama tetap dapat dibuka; hapus panduan permanen, PRD D6).

File identik otomatis tidak terduplikasi; baris `file` yang sama dipakai ulang.
"""
import hashlib
import os
import re
import tempfile

import pypdfium2 as pdfium
from fastapi import UploadFile
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.galat import Galat
from app.konfigurasi import konfigurasi
from app.model import Chunk, Elemen, File, Halaman, Job, Panduan, PanduanHistori, ReviewPanduan, Revisi, Rujukan

POTONGAN = 1024 * 1024


def folder_file() -> str:
    return os.path.join(konfigurasi().data_dir, "files")


def path_sha(sha: str) -> str:
    return os.path.join(folder_file(), sha[:2], sha[2:4], f"{sha}.pdf")


def sanitasi_nama(nama: str | None) -> str:
    """Nama file untuk ditampilkan: tanpa path, karakter aman, maks. 200 karakter."""
    nama = os.path.basename((nama or "dokumen.pdf").replace("\\", "/"))
    nama = re.sub(r"[^\w.\- ()]+", "_", nama).strip() or "dokumen.pdf"
    return nama[:200]


def periksa_pdf(path: str) -> int:
    """Validasi bahwa file benar PDF yang dapat dibuka dan tidak terenkripsi. Kembalikan jumlah halaman.

    Error: `Galat` 400 dengan pesan ramah.
    """
    with open(path, "rb") as f:
        if f.read(5) != b"%PDF-":
            raise Galat(400, "File bukan PDF yang valid.")
    try:
        doc = pdfium.PdfDocument(path)
    except pdfium.PdfiumError as e:
        if "password" in str(e).lower():
            raise Galat(400, "PDF terenkripsi/berkata sandi. Unggah PDF tanpa kata sandi.") from e
        raise Galat(400, "PDF rusak atau tidak dapat dibuka.") from e
    try:
        jumlah = len(doc)
    finally:
        doc.close()
    if jumlah == 0:
        raise Galat(400, "PDF tidak memiliki halaman.")
    return jumlah


def simpan_unggahan(db: Session, unggahan: UploadFile) -> tuple[File, str]:
    """Simpan PDF unggahan (maks. `MAKS_UKURAN_PDF_MB`). Kembalikan (baris File, nama file tersanitasi).

    Error: `Galat` 400 (bukan PDF/rusak/terenkripsi) atau 413 (terlalu besar).
    """
    k = konfigurasi()
    nama = sanitasi_nama(unggahan.filename)
    if not nama.lower().endswith(".pdf"):
        raise Galat(400, f"File '{nama}' harus berformat PDF.")
    os.makedirs(folder_file(), exist_ok=True)
    sha = hashlib.sha256()
    ukuran = 0
    fd, sementara = tempfile.mkstemp(dir=folder_file(), suffix=".unggah")
    try:
        with os.fdopen(fd, "wb") as keluar:
            while potongan := unggahan.file.read(POTONGAN):
                ukuran += len(potongan)
                if ukuran > k.maks_ukuran_pdf:
                    raise Galat(413, f"Ukuran file '{nama}' melebihi batas {k.maks_ukuran_pdf_mb} MB.")
                sha.update(potongan)
                keluar.write(potongan)
        digest = sha.hexdigest()
        ada = db.scalar(select(File).where(File.sha256 == digest))
        if ada is not None:
            return ada, nama
        jumlah = periksa_pdf(sementara)
        tujuan = path_sha(digest)
        os.makedirs(os.path.dirname(tujuan), exist_ok=True)
        os.replace(sementara, tujuan)
        f = File(sha256=digest, nama_asli=nama, ukuran=ukuran, jumlah_halaman=jumlah,
                 path=os.path.relpath(tujuan, folder_file()), status_ekstraksi="BELUM")
        db.add(f)
        db.flush()
        return f, nama
    finally:
        if os.path.exists(sementara):
            os.remove(sementara)


def path_absolut(f: File) -> str:
    return os.path.join(folder_file(), f.path)


def hapus_file_tak_terpakai(db: Session, file_ids) -> list[str]:
    """Hapus PERMANEN baris `file` beserta hasil ekstraksinya (halaman, elemen, chunk, rujukan ke elemennya, job) untuk file
    yang tidak lagi dipakai TOR/RAB revisi mana pun maupun panduan (terkini, riwayat, salinan review). File identik (SHA sama)
    dipakai bersama, jadi file yang masih dipakai dibiarkan. Kembalikan path PDF yang harus dihapus SETELAH commit
    (`hapus_berkas`), agar PDF tetap ada bila transaksi gagal."""
    path = []
    for fid in {f for f in file_ids if f}:
        if any(db.scalar(select(kolom).where(kolom == fid).limit(1)) for kolom in (
                Panduan.file_id, PanduanHistori.file_id, ReviewPanduan.file_id)) or db.scalar(
                select(Revisi.id).where(or_(Revisi.tor_file_id == fid, Revisi.rab_file_id == fid)).limit(1)):
            continue
        db.execute(delete(Rujukan).where(Rujukan.elemen_id.in_(select(Elemen.id).where(Elemen.file_id == fid))))
        for tabel in (Chunk, Elemen, Halaman):
            db.execute(delete(tabel).where(tabel.file_id == fid))
        db.execute(delete(Job).where(Job.ref_id == fid))
        f = db.get(File, fid)
        path.append(path_absolut(f))
        db.delete(f)
    return path


def hapus_berkas(daftar: list[str]) -> None:
    """Hapus PDF di disk (dipanggil setelah commit)."""
    for p in daftar:
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
