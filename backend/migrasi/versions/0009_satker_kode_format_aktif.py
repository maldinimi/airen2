"""satker: CHECK format kode (UKE I = NN, UKE II = NN.NN diawali kode UKE I) dan DEFAULT true untuk aktif.

Revision ID: 0009_satker_kode_format_aktif
Revises: 0008_satker_tanpa_pejabat
Create Date: 2026-10-26
"""
from alembic import op

revision = "0009_satker_kode_format_aktif"
down_revision = "0008_satker_tanpa_pejabat"
branch_labels = None
depends_on = None

CEK = [
    ("ck_satker_kode_uke1_format", "kode_uke1 = '' OR kode_uke1 ~ '^[0-9]{2}$'"),
    ("ck_satker_kode_uke2_format", "kode_uke2 = '' OR kode_uke2 ~ '^[0-9]{2}\\.[0-9]{2}$'"),
    ("ck_satker_kode_uke2_induk", "kode_uke1 = '' OR kode_uke2 = '' OR left(kode_uke2, 2) = kode_uke1"),
]


def upgrade() -> None:
    for nama, kondisi in CEK:
        op.create_check_constraint(nama, "satker", kondisi)
    op.alter_column("satker", "aktif", server_default="true")


def downgrade() -> None:
    op.alter_column("satker", "aktif", server_default=None)
    for nama, _ in reversed(CEK):
        op.drop_constraint(nama, "satker", type_="check")
