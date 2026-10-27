"""Kategori dapat diatur urutannya oleh Admin ("Atur Urutan", seperti checklist): kolom `kategori.no_urut`.

Hanya mengubah database lama; database baru dibuat langsung dari model lalu di-stamp ke head (app/migrasi.py).
Urutan awal = urutan sebelumnya, yaitu kode alami (K1, K2, …, K10).

Revision ID: 0003_kategori_no_urut
Revises: 0002_kategori_per_kategori
Create Date: 2026-10-27
"""
import re

import sqlalchemy as sa
from alembic import op

revision = "0003_kategori_no_urut"
down_revision = "0002_kategori_per_kategori"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("kategori", sa.Column("no_urut", sa.Integer))
    c = op.get_bind()
    # Urut kode alami di Python (sama dengan app.checklist.kunci_kode; disalin agar migrasi tidak bergantung kode aplikasi).
    kunci = lambda kode: [int(x) if n % 2 else x for n, x in enumerate(re.split(r"(\d+)", kode))]  # noqa: E731
    for n, (kid, _) in enumerate(sorted(c.execute(sa.text("SELECT id, kode FROM kategori")), key=lambda b: kunci(b[1])), 1):
        c.execute(sa.text("UPDATE kategori SET no_urut = :n WHERE id = :id"), {"n": n, "id": kid})
    op.alter_column("kategori", "no_urut", nullable=False)
    op.create_index("ix_kategori_no_urut", "kategori", ["no_urut"])


def downgrade() -> None:
    op.drop_index("ix_kategori_no_urut", "kategori")
    op.drop_column("kategori", "no_urut")
