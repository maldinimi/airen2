"""Nama & urutan kolom `panduan` dan `panduan_versi` (permintaan pemilik produk 2026-10-21).

created_at → created_date, diubah_oleh/dibuat_oleh → updated_by, diubah_at → updated_date, judul_terkini/judul → panduan,
nomor → no_urut, tambah created_by, hapus `dihapus_at`. PostgreSQL tidak dapat mengubah urutan kolom, jadi kedua tabel
dibuat ulang lalu datanya disalin (satu transaksi; gagal = tidak ada yang berubah).

`panduan_versi` = salinan utuh baris `panduan` sebelum perubahan: created_by/created_date = pengunggah & waktu unggah
pertama; updated_by/updated_date = penginput & waktu versi itu (dulu `dibuat_oleh`/`created_at`).

Revision ID: 0007_kolom_panduan
Revises: 0006_hapus_versi_daftar_panduan
Create Date: 2026-10-21
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0007_kolom_panduan"
down_revision = "0006_hapus_versi_daftar_panduan"
branch_labels = None
depends_on = None


def _fk(nama: str, tabel: str, nullable: bool = False) -> sa.Column:
    return sa.Column(nama, UUID(as_uuid=True), sa.ForeignKey(f"{tabel}.id"), nullable=nullable)


def _waktu(nama: str) -> sa.Column:
    return sa.Column(nama, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _awal() -> list[sa.Column]:
    return [sa.Column("id", UUID(as_uuid=True), primary_key=True), _fk("created_by", "pengguna", True), _waktu("created_date"),
            _fk("updated_by", "pengguna", True), _waktu("updated_date")]


def _isi() -> list[sa.Column]:
    return [sa.Column("panduan", sa.String(500), nullable=False),
            sa.Column("aktif", sa.Boolean, server_default="true", nullable=False),
            sa.Column("no_urut", sa.Integer, nullable=False), _fk("file_id", "file"),
            sa.Column("nama_file", sa.String(255), nullable=False), sa.Column("deskripsi", sa.Text)]


def upgrade() -> None:
    # Sisa soft delete lama (sebelum hapus permanen, PRD v2 D6) dihapus permanen; tanpa `dihapus_at` ia akan tampil lagi.
    for tabel in ("review_panduan", "panduan_versi"):
        op.execute(f"DELETE FROM {tabel} WHERE panduan_id IN (SELECT id FROM panduan WHERE dihapus_at IS NOT NULL)")
    op.execute("DELETE FROM panduan WHERE dihapus_at IS NOT NULL")
    # Kolom tabel sementara berurutan sama dengan tabel baru (dipakai INSERT ... SELECT *).
    # created_by = penginput versi 1: baris riwayat tertua bila ada, selain itu penginput versi terkini.
    op.execute("""
        CREATE TEMP TABLE _panduan ON COMMIT DROP AS
        SELECT p.id, CASE WHEN v1.id IS NULL THEN p.diubah_oleh ELSE v1.dibuat_oleh END AS created_by,
               p.created_at AS created_date, p.diubah_oleh AS updated_by, p.diubah_at AS updated_date,
               p.judul_terkini AS panduan, p.aktif, p.nomor AS no_urut, p.file_id, p.nama_file, p.deskripsi
        FROM panduan p
        LEFT JOIN LATERAL (SELECT id, dibuat_oleh FROM panduan_versi WHERE panduan_id = p.id ORDER BY nomor LIMIT 1) v1 ON true
    """)
    op.execute("""
        CREATE TEMP TABLE _panduan_versi ON COMMIT DROP AS
        SELECT v.id, p.created_by, p.created_date, v.dibuat_oleh AS updated_by, v.created_at AS updated_date,
               v.panduan_id, v.judul AS panduan, v.aktif, v.nomor AS no_urut, v.file_id, v.nama_file, v.deskripsi
        FROM panduan_versi v JOIN _panduan p ON p.id = v.panduan_id
    """)
    op.drop_table("panduan_versi")
    op.execute("DROP TABLE panduan CASCADE")  # CASCADE hanya melepas FK review_panduan.panduan_id; dibuat lagi di bawah
    op.create_table("panduan", *_awal(), *_isi())
    op.create_table("panduan_versi", *_awal(), _fk("panduan_id", "panduan"), *_isi(), sa.UniqueConstraint("panduan_id", "no_urut"))
    op.create_index("ix_panduan_versi_panduan_id", "panduan_versi", ["panduan_id"])
    op.execute("INSERT INTO panduan SELECT * FROM _panduan")
    op.execute("INSERT INTO panduan_versi SELECT * FROM _panduan_versi")
    op.create_foreign_key("review_panduan_panduan_id_fkey", "review_panduan", "panduan", ["panduan_id"], ["id"])


def downgrade() -> None:
    # Hanya nama kolom yang dikembalikan (urutan tidak); created_by & created_date riwayat hilang.
    op.drop_column("panduan", "created_by")
    for lama, baru in (("created_at", "created_date"), ("diubah_oleh", "updated_by"), ("diubah_at", "updated_date"),
                       ("judul_terkini", "panduan"), ("nomor", "no_urut")):
        op.alter_column("panduan", baru, new_column_name=lama)
    op.add_column("panduan", sa.Column("dihapus_at", sa.DateTime(timezone=True)))
    op.drop_column("panduan_versi", "created_by")
    op.drop_column("panduan_versi", "created_date")
    for lama, baru in (("dibuat_oleh", "updated_by"), ("created_at", "updated_date"), ("judul", "panduan"), ("nomor", "no_urut")):
        op.alter_column("panduan_versi", baru, new_column_name=lama)
