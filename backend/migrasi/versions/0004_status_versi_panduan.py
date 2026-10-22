"""Status Aktif/Tidak Aktif dicatat per versi panduan (riwayat versi menampilkan status).

Revision ID: 0004_status_versi_panduan
Revises: 0003_status_panduan
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_status_versi_panduan"
down_revision = "0003_status_panduan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("panduan_versi", sa.Column("aktif", sa.Boolean, server_default="true", nullable=False))
    # Riwayat status lama tidak tercatat per versi: versi terbaru = status panduan saat ini, versi lama = Aktif.
    op.execute("""
        UPDATE panduan_versi pv SET aktif = p.aktif
        FROM panduan p
        WHERE pv.panduan_id = p.id AND pv.nomor = (SELECT max(nomor) FROM panduan_versi WHERE panduan_id = p.id)
    """)


def downgrade() -> None:
    op.drop_column("panduan_versi", "aktif")
