"""Ganti nama tabel `panduan_versi` → `panduan_histori` (permintaan pemilik produk 2026-10-21).

Index & constraint ikut diganti nama agar sama dengan database baru yang dibuat langsung dari model.

Revision ID: 0009_panduan_histori
Revises: 0008_hapus_no_urut_panduan
Create Date: 2026-10-21
"""
from alembic import op

revision = "0009_panduan_histori"
down_revision = "0008_hapus_no_urut_panduan"
branch_labels = None
depends_on = None

KOLOM_FK = ("created_by", "updated_by", "panduan_id", "file_id")


def _ganti(dari: str, ke: str) -> None:
    op.rename_table(dari, ke)
    op.execute(f"ALTER INDEX {dari}_pkey RENAME TO {ke}_pkey")  # ikut mengganti nama constraint primary key
    op.execute(f"ALTER INDEX ix_{dari}_panduan_id RENAME TO ix_{ke}_panduan_id")
    for kolom in KOLOM_FK:
        op.execute(f"ALTER TABLE {ke} RENAME CONSTRAINT {dari}_{kolom}_fkey TO {ke}_{kolom}_fkey")


def upgrade() -> None:
    _ganti("panduan_versi", "panduan_histori")


def downgrade() -> None:
    _ganti("panduan_histori", "panduan_versi")
