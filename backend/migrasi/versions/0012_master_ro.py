"""Tabel master_ro: Master RO (Program → Kegiatan → KRO → RO) yang dikelola Reviewer. Bentuk datar seperti `satker`:
kolom = kolom tabel di layar (kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro, kode_ro, ro).

Revision ID: 0012_master_ro
Revises: 0011_gabung_kategori_satker
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0012_master_ro"
down_revision = "0011_gabung_kategori_satker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    teks = lambda n, panjang, wajib=False: sa.Column(n, sa.String(panjang), nullable=False,  # noqa: E731
                                                     **({} if wajib else {"server_default": ""}))
    op.create_table(
        "master_ro",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True),
        sa.Column("create_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_by", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True),
        sa.Column("update_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        teks("kode_program", 20, True), teks("program", 500, True),
        teks("kode_kegiatan", 20), teks("kegiatan", 500),
        teks("kode_kro", 20), teks("kro", 500),
        teks("kode_ro", 20), teks("ro", 500),
        sa.Column("aktif", sa.Boolean(), server_default="true", nullable=False),
        sa.UniqueConstraint("kode_program", "kode_kegiatan", "kode_kro", "kode_ro", name="uq_master_ro_kode"),
        sa.CheckConstraint("kode_program <> '' AND program <> ''", name="ck_master_ro_program"),
        sa.CheckConstraint("(kode_kegiatan = '') = (kegiatan = '') AND (kode_kro = '') = (kro = '') AND (kode_ro = '') = (ro = '')",
                           name="ck_master_ro_kode_nama"),
        sa.CheckConstraint("(kode_kro = '' OR kode_kegiatan <> '') AND (kode_ro = '' OR kode_kro <> '')", name="ck_master_ro_jenjang"),
    )


def downgrade() -> None:
    op.drop_table("master_ro")
