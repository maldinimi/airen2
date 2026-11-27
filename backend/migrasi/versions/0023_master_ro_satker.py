"""Tabel `master_ro_satker`: Unit Kerja (Eselon I) & Satuan Kerja (Eselon II) pelaksana tiap RO di Master RO
(Revisi 7, permintaan pemilik produk, 2026-11-24).

- Satu RO boleh punya beberapa Satker (bullet di tabel), jadi disimpan di tabel penghubung yang merujuk `satker`
  (permintaan pemilik produk: pakai JOIN). Nama Unit Kerja & Satuan Kerja diambil lewat JOIN ke `satker`, sehingga
  ganti nama di menu Satuan Kerja otomatis ikut.
- PK (master_ro_id, satker_id): Satker yang sama tidak tercatat dua kali di satu RO. `no_urut` = urutan isian form.
- master_ro_id ON DELETE CASCADE (hapus RO ikut menghapus daftarnya); satker_id tanpa CASCADE, jadi Satker yang
  masih dipakai RO tidak dapat dihapus dari menu Satuan Kerja.
- Khusus jenis RO: minimal satu Satker saat Tambah/Ubah RO (dijaga backend); Program/Kegiatan/KRO tanpa baris di sini.
  RO yang sudah ada sebelum revisi ini belum punya Satker.

Revision ID: 0023_master_ro_satker
Revises: 0022_jenis_pemeriksaan_checklist
Create Date: 2026-11-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0023_master_ro_satker"
down_revision = "0022_jenis_pemeriksaan_checklist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "master_ro_satker",
        sa.Column("master_ro_id", UUID(as_uuid=True), sa.ForeignKey("master_ro.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("satker_id", UUID(as_uuid=True), sa.ForeignKey("satker.id"), primary_key=True),
        sa.Column("no_urut", sa.Integer(), nullable=False),
    )
    op.create_index("ix_master_ro_satker_satker_id", "master_ro_satker", ["satker_id"])


def downgrade() -> None:
    op.drop_table("master_ro_satker")
