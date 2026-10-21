"""Status aktif dan jejak "terakhir diubah" per item checklist.

Item lama: aktif, dan dianggap terakhir diubah oleh pembuat versinya pada waktu versi dibuat.

Revision ID: 0003_checklist_status
Revises: 0002_versi_panduan
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_checklist_status"
down_revision = "0002_versi_panduan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checklist_item", sa.Column("aktif", sa.Boolean, server_default=sa.true(), nullable=False))
    op.add_column("checklist_item", sa.Column("diubah_oleh", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True))
    op.add_column("checklist_item", sa.Column("diubah_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("""
        UPDATE checklist_item i SET diubah_oleh = v.dibuat_oleh, diubah_at = v.created_at
        FROM checklist_versi v WHERE v.id = i.versi_id
    """)


def downgrade() -> None:
    for kolom in ("diubah_at", "diubah_oleh", "aktif"):
        op.drop_column("checklist_item", kolom)
