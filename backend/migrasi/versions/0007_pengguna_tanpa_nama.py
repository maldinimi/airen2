"""pengguna: kolom nama dihapus (menu Pengguna tidak lagi memakai Nama). Nama tampilan di aplikasi = username
(property `Pengguna.nama` di app/model.py).

Revision ID: 0007_pengguna_tanpa_nama
Revises: 0006_satker_sesuai_dokumen
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_pengguna_tanpa_nama"
down_revision = "0006_satker_sesuai_dokumen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_pengguna_nama_isi", "pengguna", type_="check")
    op.drop_column("pengguna", "nama")


def downgrade() -> None:
    # Nama asli sudah hilang; diisi username agar tetap NOT NULL & tidak kosong.
    op.add_column("pengguna", sa.Column("nama", sa.String(255), nullable=True))
    op.execute("UPDATE pengguna SET nama = username")
    op.alter_column("pengguna", "nama", nullable=False)
    op.create_check_constraint("ck_pengguna_nama_isi", "pengguna", "btrim(nama) <> ''")
