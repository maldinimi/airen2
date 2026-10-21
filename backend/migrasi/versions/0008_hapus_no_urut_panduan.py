"""Hapus `no_urut` dari `panduan` & `panduan_versi` (permintaan pemilik produk 2026-10-21).

Nomor versi kini dihitung: riwayat ke-n menurut `updated_date` = versi n, terkini = jumlah riwayat + 1
(`Panduan.daftar_versi`). `review_panduan.nomor` (salinan untuk D5) tidak berubah.

Revision ID: 0008_hapus_no_urut_panduan
Revises: 0007_kolom_panduan
Create Date: 2026-10-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_hapus_no_urut_panduan"
down_revision = "0007_kolom_panduan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("panduan_versi", "no_urut")  # ikut menghapus UNIQUE (panduan_id, no_urut)
    op.drop_column("panduan", "no_urut")


def downgrade() -> None:
    # Kolom ditambahkan di akhir tabel (urutan kolom tidak dikembalikan); isinya dihitung dengan aturan yang sama.
    for tabel in ("panduan", "panduan_versi"):
        op.add_column(tabel, sa.Column("no_urut", sa.Integer, nullable=True))
    op.execute("""
        UPDATE panduan_versi v SET no_urut = x.n FROM (
            SELECT id, row_number() OVER (PARTITION BY panduan_id ORDER BY updated_date, id) AS n FROM panduan_versi) x
        WHERE x.id = v.id
    """)
    op.execute("UPDATE panduan p SET no_urut = (SELECT count(*) + 1 FROM panduan_versi v WHERE v.panduan_id = p.id)")
    for tabel in ("panduan", "panduan_versi"):
        op.alter_column(tabel, "no_urut", nullable=False)
    op.create_unique_constraint("panduan_versi_panduan_id_no_urut_key", "panduan_versi", ["panduan_id", "no_urut"])
