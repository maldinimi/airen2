"""Tabel usulan: kolom jejak seperti kategori/panduan — `created_by`, `created_date`, `updated_by`, `updated_date` tepat
setelah `id`, menggantikan `created_at`/`updated_at` (desain.md §7 no. 37).

PostgreSQL tidak dapat menyisipkan kolom di tengah, sehingga tabel dibuat ulang dengan urutan baru dan datanya disalin
dalam satu transaksi (pola yang sama dengan pembuatan ulang tabel panduan, §7 no. 17). Baris lama: `created_date` =
`created_at`, `updated_date` = `updated_at`, `created_by` = `updated_by` = `dibuat_oleh` (pengubah terakhir tidak tercatat).
Indeks dan relasi (termasuk `revisi.usulan_id`) dipasang kembali dengan nama yang sama.

Revision ID: 0013_usulan_created_updated_date
Revises: 0012_usulan_hierarki_kategori
Create Date: 2026-11-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0013_usulan_created_updated_date"
down_revision = "0012_usulan_hierarki_kategori"
branch_labels = None
depends_on = None


def _waktu(nama: str) -> sa.Column:
    return sa.Column(nama, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.drop_constraint("revisi_usulan_id_fkey", "revisi", type_="foreignkey")
    op.rename_table("usulan", "usulan_lama")
    # Nama indeks unik per skema → tabel lama dipindah namanya dulu agar tabel baru memakai nama aslinya.
    for indeks in ("usulan_pkey", "ix_usulan_satker_id", "ix_usulan_tahun_anggaran"):
        op.execute(f"ALTER INDEX {indeks} RENAME TO {indeks}_lama")
    op.create_table(
        "usulan",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by", UUID(as_uuid=True)), _waktu("created_date"),
        sa.Column("updated_by", UUID(as_uuid=True)), _waktu("updated_date"),
        sa.Column("satker_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tahun_anggaran", sa.Integer, nullable=False),
        sa.Column("kode_ro", sa.String(100), nullable=False),
        sa.Column("nama_ro", sa.String(500), nullable=False),
        sa.Column("dibuat_oleh", UUID(as_uuid=True), nullable=False),
        sa.Column("diarsipkan_at", sa.DateTime(timezone=True)),
        sa.Column("hierarki", JSONB),
        sa.Column("kategori_usulan", JSONB),
    )
    op.create_index("ix_usulan_satker_id", "usulan", ["satker_id"])
    op.create_index("ix_usulan_tahun_anggaran", "usulan", ["tahun_anggaran"])
    op.execute("INSERT INTO usulan (id, created_by, created_date, updated_by, updated_date, satker_id, tahun_anggaran, kode_ro, "
               "nama_ro, dibuat_oleh, diarsipkan_at, hierarki, kategori_usulan) "
               "SELECT id, dibuat_oleh, created_at, dibuat_oleh, updated_at, satker_id, tahun_anggaran, kode_ro, nama_ro, "
               "dibuat_oleh, diarsipkan_at, hierarki, kategori_usulan FROM usulan_lama")
    op.drop_table("usulan_lama")
    # FK dipasang setelah tabel lama dihapus agar namanya tetap sama (bukan *_fkey1).
    op.create_foreign_key("usulan_created_by_fkey", "usulan", "pengguna", ["created_by"], ["id"])
    op.create_foreign_key("usulan_updated_by_fkey", "usulan", "pengguna", ["updated_by"], ["id"])
    op.create_foreign_key("usulan_satker_id_fkey", "usulan", "satker", ["satker_id"], ["id"])
    op.create_foreign_key("usulan_dibuat_oleh_fkey", "usulan", "pengguna", ["dibuat_oleh"], ["id"])
    op.create_foreign_key("revisi_usulan_id_fkey", "revisi", "usulan", ["usulan_id"], ["id"])


def downgrade() -> None:
    # Urutan kolom tidak dikembalikan; nama & isi created_at/updated_at kembali seperti semula.
    op.drop_column("usulan", "updated_by")
    op.drop_column("usulan", "created_by")
    op.alter_column("usulan", "created_date", new_column_name="created_at")
    op.alter_column("usulan", "updated_date", new_column_name="updated_at")
