"""Status Aktif/Tidak Aktif dan jejak perubahan terakhir pada panduan.

Revision ID: 0003_status_panduan
Revises: 0002_versi_panduan
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_status_panduan"
down_revision = "0002_versi_panduan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("panduan", sa.Column("aktif", sa.Boolean, server_default="true", nullable=False))
    op.add_column("panduan", sa.Column("diubah_oleh", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True))
    op.add_column("panduan", sa.Column("diubah_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    # Perubahan terakhir panduan lama = versi terbarunya.
    op.execute("""
        UPDATE panduan p SET diubah_oleh = pv.dibuat_oleh, diubah_at = pv.created_at
        FROM (SELECT DISTINCT ON (panduan_id) panduan_id, dibuat_oleh, created_at
              FROM panduan_versi ORDER BY panduan_id, nomor DESC) pv
        WHERE pv.panduan_id = p.id
    """)


def downgrade() -> None:
    op.drop_column("panduan", "diubah_at")
    op.drop_column("panduan", "diubah_oleh")
    op.drop_column("panduan", "aktif")
