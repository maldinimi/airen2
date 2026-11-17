"""panduan & panduan_histori: urutan kolom mengikuti kolom tabel Panduan di layar (permintaan pemilik produk,
desain.md §7 no. 31): Nama Acuan (`panduan`), Nama Dokumen (`nama_file`, `file_id`), `deskripsi`, Status (`aktif`),
Diinput Oleh (`updated_by`), Tanggal Input (`updated_date`), lalu `created_by`, `created_date`.

PostgreSQL tidak dapat memindah urutan kolom, jadi kedua tabel dibuat ulang dan datanya disalin apa adanya (id tetap,
sehingga `review_panduan` dan riwayat tetap menunjuk panduan yang sama). Satu transaksi Alembic: gagal = tidak berubah.
Nama tabel, kolom, constraint, dan indeks sama seperti sebelumnya.

Revision ID: 0014_urutan_kolom_panduan
Revises: 0013_satker_kolom_satuan_kerja
Create Date: 2026-11-11
"""
from alembic import op

revision = "0014_urutan_kolom_panduan"
down_revision = "0013_satker_kolom_satuan_kerja"
branch_labels = None
depends_on = None

_BARU = ["panduan", "nama_file", "file_id", "deskripsi", "aktif", "updated_by", "updated_date", "created_by", "created_date"]
_LAMA = ["created_by", "created_date", "updated_by", "updated_date", "panduan", "aktif", "file_id", "nama_file", "deskripsi"]

_DEF = {
    "panduan": "varchar(500) NOT NULL",
    "nama_file": "varchar(255) NOT NULL",
    "file_id": "uuid NOT NULL",
    "deskripsi": "text",
    "aktif": "boolean NOT NULL DEFAULT true",
    "updated_by": "uuid",
    "updated_date": "timestamptz NOT NULL DEFAULT now()",
    "created_by": "uuid",
    "created_date": "timestamptz NOT NULL DEFAULT now()",
}


def _susun(urutan: list[str]) -> None:
    """Buat ulang `panduan` dan `panduan_histori` dengan urutan kolom `urutan` (setelah id / id, panduan_id)."""
    kol = ", ".join(urutan)
    isi = ",\n".join(f"{k} {_DEF[k]}" for k in urutan)
    # FK dari tabel lain ke panduan dilepas dulu; dipasang lagi ke tabel baru di akhir.
    op.execute("ALTER TABLE review_panduan DROP CONSTRAINT review_panduan_panduan_id_fkey")
    op.execute("ALTER TABLE panduan_histori RENAME TO panduan_histori_lama")
    op.execute("ALTER TABLE panduan RENAME TO panduan_lama")
    # Nama pkey & indeks adalah nama relasi (unik per skema) → diganti agar tabel baru bisa memakai nama aslinya.
    op.execute("ALTER INDEX panduan_pkey RENAME TO panduan_lama_pkey")
    op.execute("ALTER INDEX panduan_histori_pkey RENAME TO panduan_histori_lama_pkey")
    op.execute("ALTER INDEX ix_panduan_histori_panduan_id RENAME TO ix_panduan_histori_lama_panduan_id")

    op.execute(f"CREATE TABLE panduan (id uuid NOT NULL, {isi})")
    op.execute(f"INSERT INTO panduan (id, {kol}) SELECT id, {kol} FROM panduan_lama")
    op.execute(f"CREATE TABLE panduan_histori (id uuid NOT NULL, panduan_id uuid NOT NULL, {isi})")
    op.execute(f"INSERT INTO panduan_histori (id, panduan_id, {kol}) SELECT id, panduan_id, {kol} FROM panduan_histori_lama")

    op.execute("DROP TABLE panduan_histori_lama")
    op.execute("DROP TABLE panduan_lama")

    op.execute("""
        ALTER TABLE panduan
          ADD CONSTRAINT panduan_pkey PRIMARY KEY (id),
          ADD CONSTRAINT panduan_file_id_fkey FOREIGN KEY (file_id) REFERENCES file(id),
          ADD CONSTRAINT panduan_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES pengguna(id),
          ADD CONSTRAINT panduan_created_by_fkey FOREIGN KEY (created_by) REFERENCES pengguna(id)""")
    op.execute("""
        ALTER TABLE panduan_histori
          ADD CONSTRAINT panduan_histori_pkey PRIMARY KEY (id),
          ADD CONSTRAINT panduan_histori_panduan_id_fkey FOREIGN KEY (panduan_id) REFERENCES panduan(id),
          ADD CONSTRAINT panduan_histori_file_id_fkey FOREIGN KEY (file_id) REFERENCES file(id),
          ADD CONSTRAINT panduan_histori_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES pengguna(id),
          ADD CONSTRAINT panduan_histori_created_by_fkey FOREIGN KEY (created_by) REFERENCES pengguna(id)""")
    op.execute("CREATE INDEX ix_panduan_histori_panduan_id ON panduan_histori (panduan_id)")
    op.execute("""ALTER TABLE review_panduan ADD CONSTRAINT review_panduan_panduan_id_fkey
                  FOREIGN KEY (panduan_id) REFERENCES panduan(id)""")


def upgrade() -> None:
    _susun(_BARU)


def downgrade() -> None:
    _susun(_LAMA)
