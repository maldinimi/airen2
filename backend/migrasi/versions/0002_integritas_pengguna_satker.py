"""Integritas data tabel satker, pengguna, pengguna_role di level database.

- CHECK constraint: nilai kosong/di luar domain ditolak walau ditulis tanpa lewat API.
- pengguna: DEFAULT gen_random_uuid() untuk id & DEFAULT true untuk aktif (berlaku juga saat INSERT lewat SQL),
  serta indeks unik lower(username) (menggantikan unik biasa) agar "Admin" dan "admin" tidak bisa menjadi dua akun.

Database baru sudah mendapatkannya dari model (create_all); revisi ini untuk database yang sudah ada.

Revision ID: 0002_integritas_pengguna_satker
Revises: 0001_dasar
Create Date: 2026-10-23
"""
from alembic import op

revision = "0002_integritas_pengguna_satker"
down_revision = "0001_dasar"
branch_labels = None
depends_on = None

CEK = [
    ("ck_satker_kode_isi", "satker", "btrim(kode) <> ''"),
    ("ck_satker_nama_isi", "satker", "btrim(nama) <> ''"),
    ("ck_pengguna_username_isi", "pengguna", "btrim(username) <> ''"),
    ("ck_pengguna_nama_isi", "pengguna", "btrim(nama) <> ''"),
    ("ck_pengguna_role_role", "pengguna_role", "role IN ('PENGUSUL', 'REVIEWER', 'ADMIN')"),
]


def upgrade() -> None:
    for nama, tabel, kondisi in CEK:
        op.create_check_constraint(nama, tabel, kondisi)
    op.execute("ALTER TABLE pengguna ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE pengguna ALTER COLUMN aktif SET DEFAULT true")
    op.execute("CREATE UNIQUE INDEX ux_pengguna_username_lower ON pengguna (lower(username))")
    # Unik biasa (beda huruf) sudah tercakup indeks lower(username) → dihapus agar tidak ada indeks ganda.
    op.drop_constraint("pengguna_username_key", "pengguna", type_="unique")
    op.alter_column("pengguna", "password_hash", new_column_name="password")


def downgrade() -> None:
    op.alter_column("pengguna", "password", new_column_name="password_hash")
    op.create_unique_constraint("pengguna_username_key", "pengguna", ["username"])
    op.execute("DROP INDEX ux_pengguna_username_lower")
    op.execute("ALTER TABLE pengguna ALTER COLUMN aktif DROP DEFAULT")
    op.execute("ALTER TABLE pengguna ALTER COLUMN id DROP DEFAULT")
    for nama, tabel, _ in reversed(CEK):
        op.drop_constraint(nama, tabel, type_="check")
