"""Kolom `jenis_pemeriksaan` (`Kelengkapan`/`Kualitas`) pada `checklist_item` & `checklist_histori`.

Posisinya mengikuti tabel Checklist di layar: setelah `berlaku_untuk`, sebelum `aktif` (Status), sesuai aturan urutan
kolom desain.md §7 no. 32. PostgreSQL tidak dapat menyisipkan kolom di tengah, jadi kolom ditambahkan lalu tabel dibuat
ulang dengan helper `_bangun_ulang` dari revisi 0015 (data, constraint, indeks, FK tetap). Item yang sudah ada diisi
`Kelengkapan`. Satu transaksi Alembic: gagal = tidak ada yang berubah.

Revision ID: 0022_jenis_pemeriksaan_checklist
Revises: 0021_gabung_usulan_master_ro
Create Date: 2026-11-18
"""
import importlib.util
from pathlib import Path

from alembic import op

revision = "0022_jenis_pemeriksaan_checklist"
down_revision = "0021_gabung_usulan_master_ro"
branch_labels = None
depends_on = None

_spec = importlib.util.spec_from_file_location("_m0015", Path(__file__).with_name("0015_seragam_kolom_master.py"))
_m0015 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m0015)
_bangun_ulang = _m0015._bangun_ulang

_JEJAK = ["updated_by", "updated_date", "created_by", "created_date"]
_AWAL = {"checklist_item": ["id", "no_urut"], "checklist_histori": ["id", "checklist_id", "no_urut"]}
_ISI = ["kode", "checklist", "kriteria", "berlaku_untuk"]


def upgrade() -> None:
    for tabel, awal in _AWAL.items():
        op.execute(f"ALTER TABLE {tabel} ADD COLUMN jenis_pemeriksaan VARCHAR(20) DEFAULT 'Kelengkapan' NOT NULL")
        _bangun_ulang(tabel, [*awal, *_ISI, "jenis_pemeriksaan", "aktif", *_JEJAK], {})


def downgrade() -> None:
    for tabel in _AWAL:
        op.execute(f"ALTER TABLE {tabel} DROP COLUMN jenis_pemeriksaan")
