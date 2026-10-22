"""Hapus versi daftar panduan (`panduan_koleksi_versi/_item`, `review.panduan_koleksi_versi_id`).

Keputusan pemilik produk 2026-10-20: cukup `review_panduan` (panduan + versi yang dipakai tiap review, D5).
Data versi daftar yang ada dihapus permanen; downgrade hanya membuat ulang struktur kosong.

Revision ID: 0006_hapus_versi_daftar_panduan
Revises: 0005_terkini_di_panduan
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0006_hapus_versi_daftar_panduan"
down_revision = "0005_terkini_di_panduan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("panduan_koleksi_item")
    op.drop_column("review", "panduan_koleksi_versi_id")
    op.drop_table("panduan_koleksi_versi")


def downgrade() -> None:
    op.create_table(
        "panduan_koleksi_versi",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nomor", sa.Integer, unique=True),
        sa.Column("aktif", sa.Boolean),
        sa.Column("dibuat_oleh", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True),
        sa.Column("catatan", sa.Text),
    )
    op.create_table(
        "panduan_koleksi_item",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("versi_id", UUID(as_uuid=True), sa.ForeignKey("panduan_koleksi_versi.id"), nullable=False, index=True),
        sa.Column("urutan", sa.Integer),
        sa.Column("panduan_id", UUID(as_uuid=True), sa.ForeignKey("panduan.id"), nullable=False),
        sa.Column("nomor", sa.Integer, nullable=False),
        sa.Column("judul", sa.String(500), nullable=False),
        sa.Column("file_id", UUID(as_uuid=True), sa.ForeignKey("file.id"), nullable=False),
        sa.Column("nama_file", sa.String(255), nullable=False),
    )
    op.add_column("review", sa.Column("panduan_koleksi_versi_id", UUID(as_uuid=True),
                                      sa.ForeignKey("panduan_koleksi_versi.id"), nullable=True))
