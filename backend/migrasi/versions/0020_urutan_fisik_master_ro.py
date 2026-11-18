"""master_ro: urutan fisik baris = urutan tabel Master RO di layar (permintaan pemilik produk, 2026-11-17): data yang
paling baru ditambahkan paling atas; data yang dibuat bersamaan (seed / satu kali impor) berjenjang Program → Kegiatan →
KRO → RO. Indeks `ix_master_ro_created_date` dipakai CLUSTER (pgAdmin "View Data" tanpa ORDER BY), dirapikan lagi
setiap tambah/ubah/impor (api/master_ro.py, lihat checklist.rapikan_fisik). Isi data tidak berubah.

Revision ID: 0020_urutan_fisik_master_ro
Revises: 0019_urutan_panduan
Create Date: 2026-11-17
"""
from alembic import op

revision = "0020_urutan_fisik_master_ro"
down_revision = "0019_urutan_panduan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX ix_master_ro_created_date ON master_ro "
               "(created_date DESC, kode_program, kode_kegiatan, kode_kro, kode_ro)")
    op.execute("CLUSTER master_ro USING ix_master_ro_created_date")


def downgrade() -> None:
    op.drop_index("ix_master_ro_created_date", table_name="master_ro")
