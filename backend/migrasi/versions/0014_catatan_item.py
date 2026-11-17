"""Tabel catatan_item: Catatan Verifikator per item checklist, terpisah dari Status Verifikator (override ITEM) agar dapat
diisi sebelum status dipilih (desain.md §7 no. 32).

Catatan yang sudah tersimpan sebagai alasan override ITEM aktif disalin ke tabel baru (satu per item, yang terbaru),
sehingga tetap tampil di kolom Catatan Verifikator. Override-nya sendiri tidak diubah.

Revision ID: 0014_catatan_item
Revises: 0013_usulan_created_updated_date
Create Date: 2026-11-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0014_catatan_item"
down_revision = "0013_usulan_created_updated_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catatan_item",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id", UUID(as_uuid=True), sa.ForeignKey("review.id"), nullable=False),
        sa.Column("checklist_item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("teks", sa.Text, nullable=False),
        sa.Column("oleh", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=False),
        sa.Column("diubah_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("review_id", "checklist_item_id"),
    )
    op.create_index("ix_catatan_item_review_id", "catatan_item", ["review_id"])
    op.execute("""
        INSERT INTO catatan_item (id, review_id, checklist_item_id, teks, oleh, diubah_at)
        SELECT DISTINCT ON (review_id, checklist_item_id) gen_random_uuid(), review_id, checklist_item_id, btrim(alasan), oleh, created_at
        FROM override
        WHERE target = 'ITEM' AND dibatalkan_at IS NULL AND btrim(alasan) <> ''
        ORDER BY review_id, checklist_item_id, created_at DESC""")


def downgrade() -> None:
    op.drop_table("catatan_item")
