"""Kolom jejak created_by/create_date/update_by/update_date di pengguna & satker (seperti checklist_item);
satker tanpa kolom kode — kolom database = yang tampil di menu Satker; Satker unik per (unit_kerja, nama).

`created_at` lama diganti nama menjadi `create_date`; `update_date` baris lama diisi sama dengan `create_date`.
Pembuat/pengubah baris lama tidak diketahui → NULL (ditampilkan "Sistem").

Revision ID: 0004_jejak_pengguna_satker
Revises: 0003_satker_unit_kerja
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_jejak_pengguna_satker"
down_revision = "0003_satker_unit_kerja"
branch_labels = None
depends_on = None


def _tambah_jejak(tabel: str) -> None:
    op.alter_column(tabel, "created_at", new_column_name="create_date")
    op.add_column(tabel, sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True))
    op.add_column(tabel, sa.Column("update_by", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True))
    op.add_column(tabel, sa.Column("update_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute(f"UPDATE {tabel} SET update_date = create_date")


def _hapus_jejak(tabel: str) -> None:
    op.drop_column(tabel, "update_date")
    op.drop_column(tabel, "update_by")
    op.drop_column(tabel, "created_by")
    op.alter_column(tabel, "create_date", new_column_name="created_at")


def upgrade() -> None:
    _tambah_jejak("pengguna")
    _tambah_jejak("satker")
    op.drop_constraint("ck_satker_kode_isi", "satker", type_="check")
    op.drop_column("satker", "kode")  # unique constraint-nya ikut terhapus
    op.create_unique_constraint("uq_satker_unit_kerja_nama", "satker", ["unit_kerja", "nama"])


def downgrade() -> None:
    op.drop_constraint("uq_satker_unit_kerja_nama", "satker", type_="unique")
    # Kode asli sudah hilang; diisi id agar tetap unik & tidak kosong.
    op.add_column("satker", sa.Column("kode", sa.String(50), nullable=True))
    op.execute("UPDATE satker SET kode = id::text")
    op.alter_column("satker", "kode", nullable=False)
    op.create_unique_constraint("satker_kode_key", "satker", ["kode"])
    op.create_check_constraint("ck_satker_kode_isi", "satker", "btrim(kode) <> ''")
    _hapus_jejak("satker")
    _hapus_jejak("pengguna")
