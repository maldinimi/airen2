"""Kategori dikelola per kategori (PRD v2.2–v2.3): `kategori_versi` + `kategori_item` → `kategori`, `kategori_histori`,
`review_kategori`.

Hanya mengubah database lama. Database baru dibuat langsung dari model lalu di-stamp ke head (app/migrasi.py), dan
database yang sudah memakai skema baru dilewati.

Data dipindah tanpa mengganti id, sehingga `hasil_kategori.kategori_item_id`, `review.kategori_final_id`, dan nilai
override KATEGORI tetap menunjuk kategori yang sama:
- `kategori` = item versi aktif terbaru, semuanya Aktif; kalimat lama "tidak diteruskan" dibuang dari definisi (PRD v2.3 C1).
- `review_kategori` = item versi yang dipakai tiap review, apa adanya (C3: definisi saat review tidak diubah).
Riwayat versi daftar lama tidak dipindah ke `kategori_histori` (bentuknya berbeda); jejaknya tetap ada di audit log.

Revision ID: 0002_kategori_per_kategori
Revises: 0001_dasar
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_kategori_per_kategori"
down_revision = "0001_dasar"
branch_labels = None
depends_on = None


def _uuid(nama: str, *args, **kw) -> sa.Column:
    return sa.Column(nama, UUID(as_uuid=True), *args, **kw)


def _waktu(nama: str) -> sa.Column:
    return sa.Column(nama, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("kategori_versi"):
        return  # skema sudah baru (dibuat dari model)
    op.create_table(
        "kategori",
        _uuid("id", primary_key=True),
        _uuid("created_by", sa.ForeignKey("pengguna.id")), _waktu("created_date"),
        _uuid("updated_by", sa.ForeignKey("pengguna.id")), _waktu("updated_date"),
        sa.Column("aktif", sa.Boolean, server_default="true", nullable=False),
        sa.Column("kode", sa.String(20), unique=True, nullable=False),
        sa.Column("kategori", sa.String(255), nullable=False),
        sa.Column("deskripsi", sa.Text, nullable=False),
    )
    op.create_table(
        "kategori_histori",
        _uuid("id", primary_key=True),
        _uuid("created_by", sa.ForeignKey("pengguna.id")), _waktu("created_date"),
        _uuid("updated_by", sa.ForeignKey("pengguna.id")), _waktu("updated_date"),
        _uuid("kategori_id", sa.ForeignKey("kategori.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kategori", sa.String(255), nullable=False),
        sa.Column("aktif", sa.Boolean, server_default="true", nullable=False),
        sa.Column("kode", sa.String(20), nullable=False),
        sa.Column("deskripsi", sa.Text, nullable=False),
    )
    op.create_table(
        "review_kategori",
        _uuid("review_id", sa.ForeignKey("review.id"), primary_key=True),
        _uuid("kategori_id", primary_key=True),
        sa.Column("kode", sa.String(20), nullable=False),
        sa.Column("nama", sa.String(255), nullable=False),
        sa.Column("definisi", sa.Text, nullable=False),
    )
    # DISTINCT ON: kode wajib unik di tabel baru, sedangkan versi lama tidak menjaminnya.
    op.execute("""
        INSERT INTO kategori (id, created_by, created_date, updated_by, updated_date, aktif, kode, kategori, deskripsi)
        SELECT DISTINCT ON (ki.kode) ki.id, v.dibuat_oleh, v.created_at, v.dibuat_oleh, v.created_at, true, ki.kode, ki.nama,
               replace(ki.definisi, ' RO pada kategori ini tidak diteruskan ke tahap berikutnya.', '')
        FROM kategori_item ki
        JOIN (SELECT * FROM kategori_versi WHERE aktif ORDER BY nomor DESC LIMIT 1) v ON v.id = ki.versi_id
        ORDER BY ki.kode, ki.urutan""")
    op.execute("""
        INSERT INTO review_kategori (review_id, kategori_id, kode, nama, definisi)
        SELECT r.id, ki.id, ki.kode, ki.nama, ki.definisi
        FROM review r JOIN kategori_item ki ON ki.versi_id = r.kategori_versi_id""")
    op.drop_column("review", "kategori_versi_id")
    # CASCADE ikut melepas FK review.kategori_final_id & hasil_kategori.kategori_item_id; kolomnya tetap (kini menunjuk
    # review_kategori.kategori_id tanpa FK).
    op.execute("DROP TABLE kategori_item CASCADE")
    op.drop_table("kategori_versi")


def downgrade() -> None:
    raise NotImplementedError("Tidak ada jalan turun: versi daftar kategori lama tidak dapat disusun ulang.")
