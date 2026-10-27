"""satker: Satuan Kerja (nama) & Unit Kerja (unit_kerja) menjadi opsional.

Kosong disimpan '' (bukan NULL) agar halaman lain yang menampilkan nama Satker tidak menampilkan "null" dan
keunikan (unit_kerja, nama) tetap berlaku. Isian sementara "Belum diisi" dari revisi 0003 dikosongkan.

Revision ID: 0005_satker_isian_opsional
Revises: 0004_jejak_pengguna_satker
Create Date: 2026-10-26
"""
from alembic import op

revision = "0005_satker_isian_opsional"
down_revision = "0004_jejak_pengguna_satker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_satker_nama_isi", "satker", type_="check")
    op.drop_constraint("ck_satker_unit_kerja_isi", "satker", type_="check")
    op.alter_column("satker", "nama", server_default="")
    op.alter_column("satker", "unit_kerja", server_default="")
    op.execute("UPDATE satker SET unit_kerja = '' WHERE unit_kerja = 'Belum diisi'")


def downgrade() -> None:
    op.execute("UPDATE satker SET unit_kerja = 'Belum diisi' WHERE btrim(unit_kerja) = ''")
    op.execute("UPDATE satker SET nama = 'Belum diisi' WHERE btrim(nama) = ''")
    op.alter_column("satker", "unit_kerja", server_default=None)
    op.alter_column("satker", "nama", server_default=None)
    op.create_check_constraint("ck_satker_unit_kerja_isi", "satker", "btrim(unit_kerja) <> ''")
    op.create_check_constraint("ck_satker_nama_isi", "satker", "btrim(nama) <> ''")
