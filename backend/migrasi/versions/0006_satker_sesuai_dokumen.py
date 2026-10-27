"""satker mengikuti dokumen "Data Satker dan Unit Kerja": kolom no_urut, kode_uke1, pejabat_uke1, kode_uke2,
pejabat_uke2 (kode UKE II unik bila diisi), lalu 56 Satker dari app/data_satker.py diisi.

Satker yang sudah ada tidak diubah; baris dokumen yang bentrok (kode UKE II atau pasangan Unit Kerja + Satuan Kerja
sudah ada) dilewati. Database baru mendapatkan data ini dari seed.

Revision ID: 0006_satker_sesuai_dokumen
Revises: 0005_satker_isian_opsional
Create Date: 2026-10-26
"""
import uuid

import sqlalchemy as sa
from alembic import op

from app.data_satker import SATKER

revision = "0006_satker_sesuai_dokumen"
down_revision = "0005_satker_isian_opsional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("satker", sa.Column("no_urut", sa.Integer(), nullable=False, server_default="0"))
    for kolom, panjang in (("kode_uke1", 10), ("pejabat_uke1", 255), ("kode_uke2", 10), ("pejabat_uke2", 255)):
        op.add_column("satker", sa.Column(kolom, sa.String(panjang), nullable=False, server_default=""))
    op.create_index("ux_satker_kode_uke2", "satker", ["kode_uke2"], unique=True, postgresql_where=sa.text("kode_uke2 <> ''"))
    op.get_bind().execute(sa.text(
        "INSERT INTO satker (id, no_urut, kode_uke1, unit_kerja, kode_uke2, nama, aktif) "
        "VALUES (:id, :no_urut, :kode_uke1, :unit_kerja, :kode_uke2, :nama, true) "
        "ON CONFLICT DO NOTHING"), [{"id": uuid.uuid4(), "no_urut": i, **s} for i, s in enumerate(SATKER, 1)])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM satker WHERE kode_uke2 <> '' AND id NOT IN "
                       "(SELECT satker_id FROM pengguna WHERE satker_id IS NOT NULL UNION SELECT satker_id FROM usulan)"))
    op.drop_index("ux_satker_kode_uke2", "satker")
    for kolom in ("pejabat_uke2", "kode_uke2", "pejabat_uke1", "kode_uke1", "no_urut"):
        op.drop_column("satker", kolom)
