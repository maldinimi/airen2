"""Versi terkini panduan disimpan di `panduan`; `panduan_versi` hanya riwayat (versi sebelum perubahan).

`review_panduan` dan `panduan_koleksi_item` kini menyimpan salinan (panduan, nomor, judul, file) alih-alih menunjuk
baris `panduan_versi`, karena versi terkini tidak lagi punya baris di sana. Isi catatan lama tidak berubah.

Revision ID: 0005_terkini_di_panduan
Revises: 0004_status_versi_panduan
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0005_terkini_di_panduan"
down_revision = "0004_status_versi_panduan"
branch_labels = None
depends_on = None

SALINAN = ("panduan_id", "nomor", "judul", "file_id", "nama_file")


def _kolom_salinan(tabel: str) -> None:
    op.add_column(tabel, sa.Column("panduan_id", UUID(as_uuid=True), sa.ForeignKey("panduan.id"), nullable=True))
    op.add_column(tabel, sa.Column("nomor", sa.Integer, nullable=True))
    op.add_column(tabel, sa.Column("judul", sa.String(500), nullable=True))
    op.add_column(tabel, sa.Column("file_id", UUID(as_uuid=True), sa.ForeignKey("file.id"), nullable=True))
    op.add_column(tabel, sa.Column("nama_file", sa.String(255), nullable=True))


def upgrade() -> None:
    # 1) Salinan untuk review & versi daftar panduan (diisi dari baris panduan_versi yang ditunjuk).
    for tabel in ("review_panduan", "panduan_koleksi_item"):
        _kolom_salinan(tabel)
        op.execute(f"""
            UPDATE {tabel} t SET panduan_id = pv.panduan_id, nomor = pv.nomor, judul = pv.judul,
                                 file_id = pv.file_id, nama_file = pv.nama_file
            FROM panduan_versi pv WHERE pv.id = t.panduan_versi_id
        """)
        op.drop_column(tabel, "panduan_versi_id")  # ikut menghapus PK/FK lama yang memakai kolom ini
        for k in SALINAN:
            op.alter_column(tabel, k, nullable=False)
    op.create_primary_key("review_panduan_pkey", "review_panduan", ["review_id", "panduan_id"])

    # 2) Versi terkini pindah ke panduan. diubah_oleh/diubah_at sudah berisi input terakhir.
    op.add_column("panduan", sa.Column("nomor", sa.Integer, nullable=True))
    op.add_column("panduan", sa.Column("deskripsi", sa.Text, nullable=True))
    op.add_column("panduan", sa.Column("file_id", UUID(as_uuid=True), sa.ForeignKey("file.id"), nullable=True))
    op.add_column("panduan", sa.Column("nama_file", sa.String(255), nullable=True))
    op.execute("""
        UPDATE panduan p SET nomor = pv.nomor, judul_terkini = pv.judul, deskripsi = pv.deskripsi,
                             file_id = pv.file_id, nama_file = pv.nama_file, aktif = pv.aktif
        FROM (SELECT DISTINCT ON (panduan_id) * FROM panduan_versi ORDER BY panduan_id, nomor DESC) pv
        WHERE pv.panduan_id = p.id
    """)
    for k in ("nomor", "file_id", "nama_file"):
        op.alter_column("panduan", k, nullable=False)
    op.execute("DELETE FROM panduan_versi pv USING panduan p WHERE pv.panduan_id = p.id AND pv.nomor = p.nomor")


def downgrade() -> None:
    # Kembalikan versi terkini ke panduan_versi, lalu catatan review/daftar menunjuk barisnya lagi.
    op.execute("""
        INSERT INTO panduan_versi (id, created_at, panduan_id, nomor, judul, deskripsi, file_id, nama_file, aktif, dibuat_oleh)
        SELECT gen_random_uuid(), p.diubah_at, p.id, p.nomor, p.judul_terkini, p.deskripsi, p.file_id, p.nama_file,
               p.aktif, p.diubah_oleh
        FROM panduan p
    """)
    for tabel in ("review_panduan", "panduan_koleksi_item"):
        op.add_column(tabel, sa.Column("panduan_versi_id", UUID(as_uuid=True), sa.ForeignKey("panduan_versi.id"), nullable=True))
        op.execute(f"""
            UPDATE {tabel} t SET panduan_versi_id = pv.id FROM panduan_versi pv
            WHERE pv.panduan_id = t.panduan_id AND pv.nomor = t.nomor
        """)
        for k in SALINAN:
            op.drop_column(tabel, k)
        op.alter_column(tabel, "panduan_versi_id", nullable=False)
    op.create_primary_key("review_panduan_pkey", "review_panduan", ["review_id", "panduan_versi_id"])
    for k in ("nama_file", "file_id", "deskripsi", "nomor"):
        op.drop_column("panduan", k)
