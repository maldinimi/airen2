"""satker: kolom `nama` (UKE II / Satuan Kerja, Eselon II) diganti nama menjadi `satuan_kerja` (permintaan pemilik produk).
Constraint/indeks yang memakai kolom ini (uq_satker_unit_kerja_nama) ikut otomatis oleh PostgreSQL.

Revision ID: 0013_satker_kolom_satuan_kerja
Revises: 0012_master_ro
Create Date: 2026-11-11
"""
from alembic import op

revision = "0013_satker_kolom_satuan_kerja"
down_revision = "0012_master_ro"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("satker", "nama", new_column_name="satuan_kerja")


def downgrade() -> None:
    op.alter_column("satker", "satuan_kerja", new_column_name="nama")
