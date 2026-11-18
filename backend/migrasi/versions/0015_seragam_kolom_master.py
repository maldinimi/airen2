"""Tabel master (checklist, kategori, satker, master RO, pengguna) diseragamkan dengan `panduan` (permintaan pemilik
produk, desain.md §7 no. 32):

1. Nama kolom jejak sama di semua tabel: `create_date` → `created_date`, `update_by` → `updated_by`,
   `update_date` → `updated_date` (`kategori*` & `panduan*` sudah memakai nama ini). Nama constraint/indeks yang
   memuat nama kolom lama ikut diganti (mis. `satker_update_by_fkey` → `satker_updated_by_fkey`), sama seperti nama
   yang dibuat model untuk database baru.
2. Urutan kolom mengikuti kolom tabel di layar: kolom isi sesuai urutan tabel (Status = `aktif` di posisinya), lalu
   Diinput Oleh (`updated_by`), Tanggal Input (`updated_date`), `created_by`, `created_date`.

PostgreSQL tidak dapat memindah urutan kolom, jadi tiap tabel dibuat ulang: definisi kolom, constraint, indeks, dan FK
dari tabel lain dibaca dari katalog, data disalin apa adanya (id tetap), lalu semuanya dipasang lagi dengan nama yang
sama. Satu transaksi Alembic: gagal = tidak ada yang berubah. Tipe data tidak diubah.

Revision ID: 0015_seragam_kolom_master
Revises: 0014_urutan_kolom_panduan
Create Date: 2026-11-11
"""
from alembic import op
from sqlalchemy import text

revision = "0015_seragam_kolom_master"
down_revision = "0014_urutan_kolom_panduan"
branch_labels = None
depends_on = None

_GANTI = {"create_date": "created_date", "update_by": "updated_by", "update_date": "updated_date"}
_J_BARU = ["updated_by", "updated_date", "created_by", "created_date"]
_J_LAMA = ["created_by", "create_date", "update_by", "update_date"]

# Urutan kolom isi = urutan kolom tabel di layar (kolom teknis seperti no_urut/checklist_id/password di dekat awal).
_ISI = {
    "checklist_item": ["no_urut", "kode", "checklist", "kriteria", "berlaku_untuk", "aktif"],
    "checklist_histori": ["checklist_id", "no_urut", "kode", "checklist", "kriteria", "berlaku_untuk", "aktif"],
    "kategori": ["no_urut", "kode", "kategori", "aktif", "deskripsi"],
    "kategori_histori": ["kategori_id", "kode", "kategori", "aktif", "deskripsi"],
    "satker": ["kode_uke1", "unit_kerja", "kode_uke2", "satuan_kerja", "aktif"],
    "master_ro": ["kode_program", "program", "kode_kegiatan", "kegiatan", "kode_kro", "kro", "kode_ro", "ro", "aktif"],
    "pengguna": ["username", "password", "satker_id", "aktif", "last_login_at"],
}
# Urutan sebelum migrasi ini (untuk downgrade).
_ISI_LAMA = {
    "checklist_item": ["no_urut", "kode", "checklist", "kriteria", "berlaku_untuk", "aktif"],
    "checklist_histori": ["checklist_id", "no_urut", "kode", "checklist", "kriteria", "berlaku_untuk", "aktif"],
    "kategori": ["aktif", "kode", "kategori", "deskripsi", "no_urut"],
    "kategori_histori": ["kategori_id", "kategori", "aktif", "kode", "deskripsi"],
    "satker": ["kode_uke1", "unit_kerja", "kode_uke2", "satuan_kerja", "aktif"],
    "master_ro": ["kode_program", "program", "kode_kegiatan", "kegiatan", "kode_kro", "kro", "kode_ro", "ro", "aktif"],
    "pengguna": ["username", "password", "satker_id", "aktif", "last_login_at"],
}
_NAMA_LAMA = {"checklist_item", "checklist_histori", "satker", "master_ro", "pengguna"}  # tabel yang memakai create_date dst.


def _ganti_nama(s: str, peta: dict[str, str]) -> str:
    for a, b in peta.items():
        s = s.replace(a, b)
    return s


def _bangun_ulang(tabel: str, urutan: list[str], peta_nama: dict[str, str]) -> None:
    """Buat ulang `tabel` dengan urutan kolom `urutan`; constraint/indeks milik tabel dipasang lagi (namanya diganti
    lewat `peta_nama`), FK dari tabel lain yang merujuk ke `tabel` dipasang lagi dengan nama semula."""
    db = op.get_bind()
    q = lambda sql: db.execute(text(sql), {"t": tabel}).all()  # noqa: E731
    kolom = q("""SELECT a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull, pg_get_expr(d.adbin, d.adrelid)
                 FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                 WHERE a.attrelid = CAST(:t AS regclass) AND a.attnum > 0 AND NOT a.attisdropped""")
    ada = {k[0] for k in kolom}
    assert ada == set(urutan), f"kolom {tabel} tidak sesuai: {sorted(ada ^ set(urutan))}"
    defs = {n: f'"{n}" {tipe}' + (f" DEFAULT {bawaan}" if bawaan else "") + (" NOT NULL" if wajib else "")
            for n, tipe, wajib, bawaan in kolom}
    # Constraint milik tabel: PK/UNIQUE/CHECK dulu, FK terakhir.
    milik = q("""SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = CAST(:t AS regclass)
                 ORDER BY contype = 'f', conname""")
    rujukan = q("""SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) FROM pg_constraint
                   WHERE confrelid = CAST(:t AS regclass) AND conrelid <> confrelid ORDER BY 1, 2""")
    indeks = q("""SELECT i.relname, pg_get_indexdef(x.indexrelid), x.indisclustered FROM pg_index x
                  JOIN pg_class i ON i.oid = x.indexrelid
                  WHERE x.indrelid = CAST(:t AS regclass)
                    AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = x.indexrelid)""")
    klaster = [n for n, _, c in indeks if c] + [n for n, _ in q(
        """SELECT c.conname, 1 FROM pg_constraint c JOIN pg_index x ON x.indexrelid = c.conindid
           WHERE c.conrelid = CAST(:t AS regclass) AND x.indisclustered""")]

    for t, n, _ in rujukan:
        op.execute(f'ALTER TABLE {t} DROP CONSTRAINT "{n}"')
    sementara = f"{tabel}__baru"
    op.execute(f"CREATE TABLE {sementara} (" + ", ".join(defs[k] for k in urutan) + ")")
    kol = ", ".join(f'"{k}"' for k in urutan)
    op.execute(f"INSERT INTO {sementara} ({kol}) SELECT {kol} FROM {tabel}")
    op.execute(f"DROP TABLE {tabel}")
    op.execute(f"ALTER TABLE {sementara} RENAME TO {tabel}")
    for n, d in milik:
        op.execute(f'ALTER TABLE {tabel} ADD CONSTRAINT "{_ganti_nama(n, peta_nama)}" {d}')
    for _, d, _ in indeks:
        op.execute(_ganti_nama(d, peta_nama))
    for n in klaster:
        op.execute(f'ALTER TABLE {tabel} CLUSTER ON "{_ganti_nama(n, peta_nama)}"')
    # FK tabel lain: nama & kolomnya milik tabel itu, jadi dipasang lagi persis seperti semula.
    for t, n, d in rujukan:
        op.execute(f'ALTER TABLE {t} ADD CONSTRAINT "{n}" {d}')


def upgrade() -> None:
    for tabel, isi in _ISI.items():
        if tabel in _NAMA_LAMA:
            for a, b in _GANTI.items():
                op.execute(f"ALTER TABLE {tabel} RENAME COLUMN {a} TO {b}")
        _bangun_ulang(tabel, ["id", *isi, *_J_BARU], _GANTI)


def downgrade() -> None:
    balik = {b: a for a, b in _GANTI.items()}
    for tabel, isi in _ISI_LAMA.items():
        if tabel in _NAMA_LAMA:
            for b, a in balik.items():
                op.execute(f"ALTER TABLE {tabel} RENAME COLUMN {b} TO {a}")
            _bangun_ulang(tabel, ["id", *_J_LAMA, *isi], balik)
        else:
            _bangun_ulang(tabel, ["id", "created_by", "created_date", "updated_by", "updated_date", *isi], {})
