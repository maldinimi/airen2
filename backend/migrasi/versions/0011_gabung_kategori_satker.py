"""Menggabungkan dua cabang migrasi yang sama-sama bermula dari 0001_dasar: Kategori (0003_kategori_no_urut,
PR #5) dan Pengguna & Satuan Kerja (0010_satker_tanpa_no_urut, PR #6). Tanpa perubahan skema — hanya agar
Alembic kembali punya satu head sehingga `upgrade head`/`stamp head` berjalan.

Revision ID: 0011_gabung_kategori_satker
Revises: 0003_kategori_no_urut, 0010_satker_tanpa_no_urut
Create Date: 2026-11-02
"""
revision = "0011_gabung_kategori_satker"
down_revision = ("0003_kategori_no_urut", "0010_satker_tanpa_no_urut")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
