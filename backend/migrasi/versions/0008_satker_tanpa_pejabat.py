"""satker: kolom pejabat_uke1 & pejabat_uke2 dihapus (menu Satker tidak lagi menampilkan nama pejabat).

Revision ID: 0008_satker_tanpa_pejabat
Revises: 0007_pengguna_tanpa_nama
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_satker_tanpa_pejabat"
down_revision = "0007_pengguna_tanpa_nama"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("satker", "pejabat_uke1")
    op.drop_column("satker", "pejabat_uke2")


def downgrade() -> None:
    # Isi nama pejabat sudah hilang; kolom dikembalikan kosong.
    op.add_column("satker", sa.Column("pejabat_uke1", sa.String(255), nullable=False, server_default=""))
    op.add_column("satker", sa.Column("pejabat_uke2", sa.String(255), nullable=False, server_default=""))
