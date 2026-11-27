"""Kolom `tahun_anggaran` pada `master_ro`: Master RO per Tahun Anggaran (permintaan pemilik produk, 2026-11-25).

- Menu Master RO menampilkan, menambah, dan mengimpor data menurut Tahun Anggaran pilihan bilah atas; form Pengajuan
  tahun X hanya memakai Master RO tahun X.
- Data yang sudah ada diisi 2026: isinya Laporan Renja K/L TA 2026 (docs/asumsi.md).
- UNIQUE `uq_master_ro_kode` kini (tahun_anggaran, kode_program, kode_kegiatan, kode_kro, kode_ro): kode yang sama boleh
  ada di tahun berbeda.
- Posisi kolom tepat setelah `id`. PostgreSQL tidak dapat menyisipkan kolom di tengah, jadi tabel dibuat ulang dengan
  `_bangun_ulang` dari revisi 0015 (data, constraint, indeks, CLUSTER, dan FK master_ro_satker tetap).

Revision ID: 0024_master_ro_tahun_anggaran
Revises: 0023_master_ro_satker
Create Date: 2026-11-25
"""
import importlib.util
from pathlib import Path

from alembic import op

revision = "0024_master_ro_tahun_anggaran"
down_revision = "0023_master_ro_satker"
branch_labels = None
depends_on = None

_spec = importlib.util.spec_from_file_location("_m0015", Path(__file__).with_name("0015_seragam_kolom_master.py"))
_m0015 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m0015)
_bangun_ulang = _m0015._bangun_ulang

_KOLOM = ["kode_program", "program", "kode_kegiatan", "kegiatan", "kode_kro", "kro", "kode_ro", "ro", "aktif",
          "updated_by", "updated_date", "created_by", "created_date"]
_KODE = "kode_program, kode_kegiatan, kode_kro, kode_ro"
_TAHUN_DATA_LAMA = 2026


def upgrade() -> None:
    op.execute("ALTER TABLE master_ro ADD COLUMN tahun_anggaran INTEGER")
    op.execute(f"UPDATE master_ro SET tahun_anggaran = {_TAHUN_DATA_LAMA}")
    op.execute("ALTER TABLE master_ro ALTER COLUMN tahun_anggaran SET NOT NULL")
    op.execute("ALTER TABLE master_ro DROP CONSTRAINT uq_master_ro_kode")
    op.execute(f"ALTER TABLE master_ro ADD CONSTRAINT uq_master_ro_kode UNIQUE (tahun_anggaran, {_KODE})")
    op.execute("CREATE INDEX ix_master_ro_tahun_anggaran ON master_ro (tahun_anggaran)")
    _bangun_ulang("master_ro", ["id", "tahun_anggaran", *_KOLOM], {})


def downgrade() -> None:
    # Gagal (UNIQUE) bila kode yang sama sudah ada di lebih dari satu tahun; hapus data tahun lain terlebih dahulu.
    op.execute("ALTER TABLE master_ro DROP CONSTRAINT uq_master_ro_kode")
    op.execute(f"ALTER TABLE master_ro ADD CONSTRAINT uq_master_ro_kode UNIQUE ({_KODE})")
    op.execute("DROP INDEX ix_master_ro_tahun_anggaran")
    op.execute("ALTER TABLE master_ro DROP COLUMN tahun_anggaran")
