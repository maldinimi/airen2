"""Menggabungkan dua cabang migrasi yang sama-sama bermula dari 0011_gabung_kategori_satker: Menu Usulan
(0014_catatan_item, cabang development-usulan) dan Master RO / Satuan Kerja / Panduan (0020_urutan_fisik_master_ro,
PR #8). Tanpa perubahan skema — hanya agar Alembic kembali punya satu head sehingga `upgrade head`/`stamp head` berjalan.

Revision ID: 0021_gabung_usulan_master_ro
Revises: 0014_catatan_item, 0020_urutan_fisik_master_ro
Create Date: 2026-11-17
"""
revision = "0021_gabung_usulan_master_ro"
down_revision = ("0014_catatan_item", "0020_urutan_fisik_master_ro")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
