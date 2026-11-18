"""master_ro: tipe data kolom disesuaikan dengan isinya (permintaan pemilik produk):

- Kode = teks bebas tanpa batasan huruf/angka: `kode_program`, `kode_kegiatan`, `kode_kro`, `kode_ro` VARCHAR(50)
  — sebelumnya VARCHAR(20).
- Nama VARCHAR(255) seperti `satker` — sebelumnya VARCHAR(500).

Gagal bila ada nama lebih dari 255 karakter (isian Reviewer sudah dibatasi backend dengan panjang yang sama).

Revision ID: 0017_tipe_kolom_master_ro
Revises: 0016_penginput_data_awal
Create Date: 2026-11-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0017_tipe_kolom_master_ro"
down_revision = "0016_penginput_data_awal"
branch_labels = None
depends_on = None

_BARU = {"kode_program": 50, "program": 255, "kode_kegiatan": 50, "kegiatan": 255, "kode_kro": 50, "kro": 255,
         "kode_ro": 50, "ro": 255}
_LAMA = {"kode_program": 20, "program": 500, "kode_kegiatan": 20, "kegiatan": 500, "kode_kro": 20, "kro": 500, "kode_ro": 20, "ro": 500}


def upgrade() -> None:
    for k, n in _BARU.items():
        op.alter_column("master_ro", k, type_=sa.String(n))


def downgrade() -> None:
    for k, n in _LAMA.items():
        op.alter_column("master_ro", k, type_=sa.String(n))
