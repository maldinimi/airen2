"""panduan & panduan_histori: kolom `nama_file` diganti nama menjadi `nama_dokumen` (permintaan pemilik produk,
2026-11-13), sama dengan label "Nama Dokumen" di tabel Panduan. Isi, tipe, dan posisi kolom tidak berubah.
Atribut Python & field API tetap `nama_file` (lihat model.Panduan).

Revision ID: 0018_nama_dokumen_panduan
Revises: 0017_tipe_kolom_master_ro
Create Date: 2026-11-13
"""
from alembic import op

revision = "0018_nama_dokumen_panduan"
down_revision = "0017_tipe_kolom_master_ro"
branch_labels = None
depends_on = None

_TABEL = ("panduan", "panduan_histori")


def upgrade() -> None:
    for t in _TABEL:
        op.alter_column(t, "nama_file", new_column_name="nama_dokumen")


def downgrade() -> None:
    for t in _TABEL:
        op.alter_column(t, "nama_dokumen", new_column_name="nama_file")
