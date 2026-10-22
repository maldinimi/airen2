"""Gabungkan dua cabang migrasi: checklist (0003–0005) dan panduan (0003–0009), keduanya berangkat dari 0002.

Tanpa ini `alembic upgrade head` gagal karena ada dua head. Kedua cabang mengubah tabel yang berbeda, jadi urutan
penerapannya tidak berpengaruh; migrasi ini tidak mengubah skema.

Revision ID: 0010_gabung_checklist_panduan
Revises: 0005_checklist_histori, 0009_panduan_histori
Create Date: 2026-10-22
"""

revision = "0010_gabung_checklist_panduan"
down_revision = ("0005_checklist_histori", "0009_panduan_histori")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
