"""Data awal (seed) yang tercatat tanpa penginput — tampil "Sistem" di kolom Diinput Oleh — dicatat atas nama
akun pengelolanya (permintaan pemilik produk; desain.md §7 no. 29; docs/asumsi.md). Seed baru sudah mengisinya
langsung (app/seed.py).

- Checklist, Kategori, Satuan Kerja, Master RO (dikelola Reviewer) → akun ber-role REVIEWER yang paling dulu dibuat.
  Bila belum ada akun Reviewer (mis. instalasi produksi baru), tetap kosong = "Sistem".
- Pengguna (dikelola Admin) → akun ber-role ADMIN yang paling dulu dibuat; akun admin itu sendiri tetap tanpa pembuat.
- Hanya baris yang `created_by`/`updated_by`-nya masih kosong; `updated_date`/`created_date` tidak diubah.
- Tabel riwayat (`*_histori`) TIDAK diubah: riwayat tidak pernah diubah (CLAUDE.md aturan 4).

Downgrade tidak mengosongkan kembali (tidak dapat dibedakan dari isian pengguna) — no-op.

Revision ID: 0016_penginput_data_awal
Revises: 0015_seragam_kolom_master
Create Date: 2026-11-11
"""
from alembic import op

revision = "0016_penginput_data_awal"
down_revision = "0015_seragam_kolom_master"
branch_labels = None
depends_on = None

_OLEH_REVIEWER = ["checklist_item", "kategori", "satker", "master_ro"]


def _akun(role: str) -> str:
    """Subkueri id akun ber-`role` yang paling dulu dibuat (NULL bila tidak ada)."""
    return f"""(SELECT p.id FROM pengguna p JOIN pengguna_role r ON r.pengguna_id = p.id AND r.role = '{role}'
               ORDER BY p.created_date, p.id LIMIT 1)"""


def upgrade() -> None:
    for t, oleh, kecuali in [*((t, _akun("REVIEWER"), "") for t in _OLEH_REVIEWER),
                             ("pengguna", _akun("ADMIN"), f" AND id <> {_akun('ADMIN')}")]:
        op.execute(f"UPDATE {t} SET created_by = {oleh} WHERE created_by IS NULL{kecuali}")
        op.execute(f"UPDATE {t} SET updated_by = {oleh} WHERE updated_by IS NULL{kecuali}")


def downgrade() -> None:
    pass
