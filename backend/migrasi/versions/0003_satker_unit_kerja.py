"""satker: kolom unit_kerja (Unit Kerja, Eselon I); kolom nama = Satuan Kerja (Eselon II).

Baris lama diisi "Belum diisi" agar kolom dapat NOT NULL — Admin melengkapinya lewat menu Satker.

Revision ID: 0003_satker_unit_kerja
Revises: 0002_integritas_pengguna_satker
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_satker_unit_kerja"
down_revision = "0002_integritas_pengguna_satker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("satker", sa.Column("unit_kerja", sa.String(255), nullable=False, server_default="Belum diisi"))
    op.alter_column("satker", "unit_kerja", server_default=None)  # default hanya untuk mengisi baris lama
    op.create_check_constraint("ck_satker_unit_kerja_isi", "satker", "btrim(unit_kerja) <> ''")


def downgrade() -> None:
    op.drop_constraint("ck_satker_unit_kerja_isi", "satker", type_="check")
    op.drop_column("satker", "unit_kerja")
