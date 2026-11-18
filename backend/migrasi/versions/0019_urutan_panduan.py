"""panduan: kolom `no_urut` untuk Atur Urutan seperti Checklist & Kategori (permintaan pemilik produk, 2026-11-13).

- `no_urut` INTEGER NOT NULL, diletakkan tepat setelah `id` (sama dengan `checklist_item` & `kategori`); tabel dibuat
  ulang dengan fungsi milik migrasi 0015 agar urutan kolom di pgAdmin sesuai. Data, constraint, dan FK tetap.
- Nilai awal = urutan daftar sebelumnya (urut Nama Acuan), 1..n.
- Indeks `ix_panduan_no_urut` dipakai CLUSTER agar "View Data" pgAdmin juga mengikuti urutan (lihat checklist.rapikan_fisik).
- `panduan_histori` tidak diberi `no_urut`: urutan bukan isi versi, jadi mengatur urutan tidak membuat riwayat.

Revision ID: 0019_urutan_panduan
Revises: 0018_nama_dokumen_panduan
Create Date: 2026-11-13
"""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0019_urutan_panduan"
down_revision = "0018_nama_dokumen_panduan"
branch_labels = None
depends_on = None

_KOLOM = ["panduan", "nama_dokumen", "file_id", "deskripsi", "aktif", "updated_by", "updated_date", "created_by", "created_date"]


def _bangun_ulang(urutan: list[str]) -> None:
    """Pakai fungsi pembuat-ulang tabel milik migrasi 0015 (berkas versi tidak dapat di-import biasa)."""
    berkas = Path(__file__).with_name("0015_seragam_kolom_master.py")
    spec = importlib.util.spec_from_file_location("_m0015", berkas)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._bangun_ulang("panduan", urutan, {})


def upgrade() -> None:
    op.add_column("panduan", sa.Column("no_urut", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE panduan p SET no_urut = u.n FROM "
               "(SELECT id, row_number() OVER (ORDER BY panduan, id) AS n FROM panduan) u WHERE u.id = p.id")
    op.alter_column("panduan", "no_urut", server_default=None)
    _bangun_ulang(["id", "no_urut", *_KOLOM])
    op.create_index("ix_panduan_no_urut", "panduan", ["no_urut"])
    op.execute("CLUSTER panduan USING ix_panduan_no_urut")


def downgrade() -> None:
    op.drop_index("ix_panduan_no_urut", table_name="panduan")
    op.drop_column("panduan", "no_urut")
