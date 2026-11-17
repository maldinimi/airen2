"""Menu Usulan direvisi (desain.md §7 no. 29): usulan menyimpan salinan hierarki anggaran RKA-K/L dan kategori pilihan
Pengusul; TOR dan RAB pada revisi masing-masing opsional (minimal satu).

Usulan lama tidak punya hierarki/kategori (NULL, ditampilkan "—").

Revision ID: 0012_usulan_hierarki_kategori
Revises: 0011_gabung_kategori_satker
Create Date: 2026-11-09
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012_usulan_hierarki_kategori"
down_revision = "0011_gabung_kategori_satker"
branch_labels = None
depends_on = None

KOLOM_DOKUMEN = ("tor_file_id", "tor_nama", "rab_file_id", "rab_nama")


def upgrade() -> None:
    op.add_column("usulan", sa.Column("hierarki", JSONB))
    op.add_column("usulan", sa.Column("kategori_usulan", JSONB))
    for kolom in KOLOM_DOKUMEN:
        op.alter_column("revisi", kolom, nullable=True)


def downgrade() -> None:
    # Gagal bila sudah ada revisi tanpa TOR/RAB — sengaja, agar data tidak hilang diam-diam.
    for kolom in KOLOM_DOKUMEN:
        op.alter_column("revisi", kolom, nullable=False)
    op.drop_column("usulan", "kategori_usulan")
    op.drop_column("usulan", "hierarki")
