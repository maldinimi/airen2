"""satker: kolom no_urut dihapus (tidak tampil di web; tabel Satuan Kerja diurutkan menurut kode).

Revision ID: 0010_satker_tanpa_no_urut
Revises: 0009_satker_kode_format_aktif
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_satker_tanpa_no_urut"
down_revision = "0009_satker_kode_format_aktif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("satker", "no_urut")


def downgrade() -> None:
    op.add_column("satker", sa.Column("no_urut", sa.Integer(), nullable=False, server_default="0"))
