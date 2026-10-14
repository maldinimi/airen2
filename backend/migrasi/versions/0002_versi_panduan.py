"""Versi daftar panduan (seperti versi checklist/kategori).

Revision ID: 0002_versi_panduan
Revises: 0001_dasar
Create Date: 2026-10-13
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_versi_panduan"
down_revision = "0001_dasar"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column("panduan_versi_id", UUID(as_uuid=True), sa.ForeignKey("panduan_versi.id"), nullable=False),
    )
    op.add_column("review", sa.Column("panduan_koleksi_versi_id", UUID(as_uuid=True),
                                      sa.ForeignKey("panduan_koleksi_versi.id"), nullable=True))
    # Panduan yang sudah ada menjadi versi 1.
    op.execute("""
        WITH v AS (
            INSERT INTO panduan_koleksi_versi (id, nomor, aktif, catatan)
            SELECT gen_random_uuid(), 1, true, 'Versi awal (daftar panduan yang sudah ada)'
            WHERE EXISTS (SELECT 1 FROM panduan WHERE dihapus_at IS NULL)
            RETURNING id)
        INSERT INTO panduan_koleksi_item (id, versi_id, urutan, panduan_versi_id)
        SELECT gen_random_uuid(), v.id, row_number() OVER (ORDER BY p.judul_terkini), pv.id
        FROM v, panduan p
        JOIN LATERAL (SELECT id FROM panduan_versi WHERE panduan_id = p.id ORDER BY nomor DESC LIMIT 1) pv ON true
        WHERE p.dihapus_at IS NULL
    """)


def downgrade() -> None:
    op.drop_column("review", "panduan_koleksi_versi_id")
    op.drop_table("panduan_koleksi_item")
    op.drop_table("panduan_koleksi_versi")
