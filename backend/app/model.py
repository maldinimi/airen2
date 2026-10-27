"""Model database (desain.md §3).

Prinsip:
- Snapshot tidak berubah: baris riwayat checklist/kategori/panduan tidak pernah di-UPDATE; perubahan = baris versi
  baru. Review menunjuk ke versi atau menyimpan salinannya (review_kategori, review_panduan) sehingga tampilan
  review lama tetap.
- Hasil AI dan override dipisah; nilai final dihitung (app/nilai_final.py), tidak ditimpa.
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Computed, DateTime, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, func, text)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

DIMENSI_EMBEDDING = 1024  # BGE-M3


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _dibuat() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _fk(tabel: str, nullable: bool = False, index: bool = True) -> Mapped:
    return mapped_column(UUID(as_uuid=True), ForeignKey(f"{tabel}.id"), nullable=nullable, index=index)


# ---------------------------------------------------------------- pengguna & akses
class Satker(Base):
    """Satuan Kerja = UKE II (Eselon II) beserta Unit Kerja induknya = UKE I (Eselon I), mengikuti dokumen
    "Data Satker dan Unit Kerja" (app/data_satker.py). Kolom = yang tampil di menu Satker."""
    __tablename__ = "satker"
    # Satker dikenali dari pasangan (unit_kerja, nama): nama sama boleh di Unit Kerja berbeda; kode UKE II unik bila diisi.
    # Semua isian opsional; kosong disimpan '' (bukan NULL) agar halaman lain yang menampilkan nama Satker tidak
    # menampilkan "null", dan agar keunikan tetap berlaku untuk isian kosong.
    # Format kode seperti dokumen: UKE I = NN (01), UKE II = NN.NN (01.04) dan diawali kode UKE I-nya.
    __table_args__ = (UniqueConstraint("unit_kerja", "nama", name="uq_satker_unit_kerja_nama"),
                      Index("ux_satker_kode_uke2", "kode_uke2", unique=True, postgresql_where=text("kode_uke2 <> ''")),
                      CheckConstraint("kode_uke1 = '' OR kode_uke1 ~ '^[0-9]{2}$'", name="ck_satker_kode_uke1_format"),
                      CheckConstraint("kode_uke2 = '' OR kode_uke2 ~ '^[0-9]{2}\\.[0-9]{2}$'", name="ck_satker_kode_uke2_format"),
                      CheckConstraint("kode_uke1 = '' OR kode_uke2 = '' OR left(kode_uke2, 2) = kode_uke1",
                                      name="ck_satker_kode_uke2_induk"))
    id: Mapped[uuid.UUID] = _id()
    # pengguna.satker_id → satker dan satker.*_by → pengguna saling merujuk: FK ini dibuat setelah kedua tabel ada.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pengguna.id", use_alter=True, name="satker_created_by_fkey"))
    create_date: Mapped[datetime] = _dibuat()
    update_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pengguna.id", use_alter=True, name="satker_update_by_fkey"))
    update_date: Mapped[datetime] = _dibuat()
    kode_uke1: Mapped[str] = mapped_column(String(10), server_default="")  # Kode UKE I, mis. 01
    unit_kerja: Mapped[str] = mapped_column(String(255), server_default="")  # UKE I / Unit Kerja (Eselon I)
    kode_uke2: Mapped[str] = mapped_column(String(10), server_default="")  # Kode UKE II, mis. 01.04
    nama: Mapped[str] = mapped_column(String(255), server_default="")  # UKE II / Satuan Kerja (Eselon II)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")  # Nonaktif: tak bisa dipilih pengguna

    @property
    def kode(self) -> str:
        """Kode Satker = Kode UKE II (kolom kode lama sudah dihapus); dipakai profil login & daftar usulan."""
        return self.kode_uke2


class Pengguna(Base):
    __tablename__ = "pengguna"
    # Username unik tanpa membedakan huruf besar/kecil (aturan yang sama dipakai API & login) — juga indeks untuk login.
    __table_args__ = (CheckConstraint("btrim(username) <> ''", name="ck_pengguna_username_isi"),
                      Index("ux_pengguna_username_lower", func.lower(text("username")), unique=True))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
                                          server_default=func.gen_random_uuid())
    # Jejak seperti checklist_item: NULL = dibuat sistem (seed). update_* diisi saat data akun diubah, bukan saat login.
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    create_date: Mapped[datetime] = _dibuat()
    update_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    update_date: Mapped[datetime] = _dibuat()
    username: Mapped[str] = mapped_column(String(100))  # unik lewat ux_pengguna_username_lower
    password_hash: Mapped[str] = mapped_column("password", String(255))
    satker_id: Mapped[uuid.UUID | None] = _fk("satker", nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roles: Mapped[list["PenggunaRole"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    satker: Mapped[Satker | None] = relationship(lazy="joined", foreign_keys=[satker_id])

    @property
    def nama(self) -> str:
        """Nama tampilan (header, "Dibuat Oleh", riwayat) = username; tabel pengguna tidak lagi punya kolom nama."""
        return self.username

    @property
    def daftar_role(self) -> set[str]:
        return {r.role for r in self.roles}


class PenggunaRole(Base):
    __tablename__ = "pengguna_role"
    __table_args__ = (CheckConstraint("role IN ('PENGUSUL', 'REVIEWER', 'ADMIN')", name="ck_pengguna_role_role"),)
    pengguna_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pengguna.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), primary_key=True)  # PENGUSUL | REVIEWER | ADMIN


class Sesi(Base):
    __tablename__ = "sesi"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    pengguna_id: Mapped[uuid.UUID] = _fk("pengguna")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------- file & ekstraksi
class File(Base):
    """File PDF di penyimpanan. Satu baris per isi (SHA-256) — file identik tidak diduplikasi.
    Ekstraksi disimpan per file sehingga dokumen yang terbawa ke revisi berikutnya tidak diekstraksi ulang."""
    __tablename__ = "file"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    nama_asli: Mapped[str] = mapped_column(String(255))
    ukuran: Mapped[int] = mapped_column(BigInteger)
    jumlah_halaman: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(String(500))
    status_ekstraksi: Mapped[str] = mapped_column(String(20), default="BELUM")  # BELUM|DIPROSES|SIAP|GAGAL
    pesan_ekstraksi: Mapped[str | None] = mapped_column(Text)
    ekstraktor: Mapped[str | None] = mapped_column(String(50))


class Halaman(Base):
    __tablename__ = "halaman"
    __table_args__ = (UniqueConstraint("file_id", "nomor"),)
    id: Mapped[uuid.UUID] = _id()
    file_id: Mapped[uuid.UUID] = _fk("file")
    nomor: Mapped[int] = mapped_column(Integer)  # indeks halaman PDF (1..n), bukan nomor tercetak
    lebar: Mapped[float]
    tinggi: Mapped[float]
    hasil_scan: Mapped[bool] = mapped_column(Boolean, default=False)


class Elemen(Base):
    """Unit terkecil yang dapat dirujuk AI. Halaman, lokasi, bbox, dan teks rujukan SELALU diambil dari sini."""
    __tablename__ = "elemen"
    __table_args__ = (Index("ix_elemen_file_hlm", "file_id", "halaman", "urutan"),)
    id: Mapped[uuid.UUID] = _id()
    file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    halaman: Mapped[int] = mapped_column(Integer)
    urutan: Mapped[int] = mapped_column(Integer)
    jenis: Mapped[str] = mapped_column(String(20))  # paragraf|judul|butir|sel_tabel|gambar
    label_lokasi: Mapped[str] = mapped_column(String(500))
    teks: Mapped[str] = mapped_column(Text)
    bbox: Mapped[list | None] = mapped_column(JSONB)  # [x0, y0, x1, y1] dalam poin PDF, origin kiri-atas
    sumber: Mapped[str] = mapped_column(String(10), default="teks")  # teks|ocr|vlm


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (
        Index("ix_chunk_tsv", "tsv", postgresql_using="gin"),
        Index("ix_chunk_embedding", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
    id: Mapped[uuid.UUID] = _id()
    file_id: Mapped[uuid.UUID] = _fk("file")
    elemen_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    teks: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(DIMENSI_EMBEDDING))
    # Komponen "sparse" pencarian hibrida = full-text search PostgreSQL berbahasa Indonesia
    # (penyimpangan dari desain: menggantikan bobot sparse BGE-M3, lihat desain.md §7).
    tsv = mapped_column(TSVECTOR, Computed("to_tsvector('indonesian', teks)", persisted=True))


# ---------------------------------------------------------------- usulan
class Usulan(Base):
    __tablename__ = "usulan"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    satker_id: Mapped[uuid.UUID] = _fk("satker")
    tahun_anggaran: Mapped[int] = mapped_column(Integer, index=True)
    kode_ro: Mapped[str] = mapped_column(String(100))
    nama_ro: Mapped[str] = mapped_column(String(500))
    dibuat_oleh: Mapped[uuid.UUID] = _fk("pengguna", index=False)
    diarsipkan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    satker: Mapped[Satker] = relationship(lazy="joined")
    revisi: Mapped[list["Revisi"]] = relationship(order_by="Revisi.nomor", lazy="selectin", back_populates="usulan")


class Revisi(Base):
    __tablename__ = "revisi"
    __table_args__ = (UniqueConstraint("usulan_id", "nomor"),)
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    usulan_id: Mapped[uuid.UUID] = _fk("usulan")
    nomor: Mapped[int] = mapped_column(Integer)
    tor_file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    tor_nama: Mapped[str] = mapped_column(String(255))
    rab_file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    rab_nama: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="DRAF", index=True)
    dibuat_oleh: Mapped[uuid.UUID] = _fk("pengguna", index=False)
    usulan: Mapped[Usulan] = relationship(back_populates="revisi")


# ---------------------------------------------------------------- checklist, kategori, panduan (berversi)
class ChecklistItem(Base):
    """Isi TERBARU satu item checklist (satu baris per item). Isi sebelum setiap ubah disimpan di `checklist_histori`."""
    __tablename__ = "checklist_item"
    id: Mapped[uuid.UUID] = _id()
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    create_date: Mapped[datetime] = _dibuat()
    update_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    update_date: Mapped[datetime] = _dibuat()
    no_urut: Mapped[int] = mapped_column(Integer, index=True)  # dipakai CLUSTER (app/checklist.py:urut_ulang)
    kode: Mapped[str] = mapped_column(String(50), unique=True)
    checklist: Mapped[str] = mapped_column(String(500))
    kriteria: Mapped[str] = mapped_column(Text)
    berlaku_untuk: Mapped[str] = mapped_column(String(10))  # TOR | RAB | TOR & RAB
    # Item nonaktif tidak dinilai AI dan tidak dihitung dalam label.
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class ChecklistHistory(Base):
    """Semua versi item checklist: salinan baris `checklist_item` setiap tambah & ubah (termasuk versi terbaru).
    `checklist_id` → item asalnya (FK, ikut terhapus bila item dihapus); `kode` = kode pada versi itu.
    Isi checklist review disusun ulang dari kedua tabel (app/checklist.py)."""
    __tablename__ = "checklist_histori"
    # Dipakai CLUSTER agar baris terbaru tersimpan paling atas (pgAdmin "All Rows" tanpa ORDER BY), lihat master.py.
    __table_args__ = (Index("ix_checklist_histori_update_date", text("update_date DESC")),)
    id: Mapped[uuid.UUID] = _id()
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    create_date: Mapped[datetime] = _dibuat()
    update_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    update_date: Mapped[datetime] = _dibuat()
    checklist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("checklist_item.id", ondelete="CASCADE"), index=True)
    no_urut: Mapped[int] = mapped_column(Integer)
    kode: Mapped[str] = mapped_column(String(50))
    checklist: Mapped[str] = mapped_column(String(500))
    kriteria: Mapped[str] = mapped_column(Text)
    berlaku_untuk: Mapped[str] = mapped_column(String(10))  # TOR | RAB | TOR & RAB
    # Item nonaktif tidak dinilai AI dan tidak dihitung dalam label.
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Kategori(Base):
    """Isi TERBARU satu kategori (satu baris per kategori). Versi sebelum tiap perubahan ada di `kategori_histori`;
    review memakai salinan di `review_kategori`, sehingga kategori boleh diubah/dihapus permanen (C4).
    Nama & urutan kolom ditetapkan pemilik produk (desain.md §7 no. 24)."""
    __tablename__ = "kategori"
    id: Mapped[uuid.UUID] = _id()
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    created_date: Mapped[datetime] = _dibuat()
    updated_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)  # penginput versi terkini
    updated_date: Mapped[datetime] = _dibuat()
    # Nonaktif = tetap tampil, tetapi tidak dipakai review berikutnya (sama dengan panduan).
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    kode: Mapped[str] = mapped_column(String(20), unique=True)
    kategori: Mapped[str] = mapped_column(String(255))
    deskripsi: Mapped[str] = mapped_column(Text)  # definisi yang dipakai AI (C2)
    # Kolom terakhir agar database lama (ditambah migrasi 0003) dan baru berurutan kolom sama; dipakai CLUSTER (urut_ulang).
    no_urut: Mapped[int] = mapped_column(Integer, index=True)


class KategoriHistori(Base):
    """Riwayat kategori: salinan utuh baris `kategori` SEBELUM tiap perubahan (versi terkini hanya di `kategori`), seperti
    `panduan_histori`. Tidak diubah. `created_by`/`created_date` tetap milik pembuat kategori; `updated_by`/`updated_date` =
    penginput & waktu versi ini. `kategori_id` → kategori asalnya (ikut terhapus bila kategori dihapus)."""
    __tablename__ = "kategori_histori"
    id: Mapped[uuid.UUID] = _id()
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    created_date: Mapped[datetime] = _dibuat()
    updated_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    updated_date: Mapped[datetime] = _dibuat()
    kategori_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("kategori.id", ondelete="CASCADE"), index=True)
    kategori: Mapped[str] = mapped_column(String(255))
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")  # status saat versi itu
    kode: Mapped[str] = mapped_column(String(20))
    deskripsi: Mapped[str] = mapped_column(Text)


class Panduan(Base):
    """Panduan beserta isi versi TERKINI (panduan = Nama Acuan, deskripsi, file, status). Versi sebelumnya ada di `panduan_histori`.
    Nama & urutan kolom ditetapkan pemilik produk (desain.md §7 no. 17)."""
    __tablename__ = "panduan"
    id: Mapped[uuid.UUID] = _id()
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)  # pengunggah pertama (versi 1)
    created_date: Mapped[datetime] = _dibuat()
    updated_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)  # yang menginput versi terkini
    updated_date: Mapped[datetime] = _dibuat()  # waktu input versi terkini
    panduan: Mapped[str] = mapped_column(String(500))
    # Nonaktif = tetap tampil, tetapi tidak dipakai review berikutnya.
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    nama_file: Mapped[str] = mapped_column(String(255))
    deskripsi: Mapped[str | None] = mapped_column(Text)
    pengubah: Mapped[Pengguna | None] = relationship(foreign_keys=[updated_by], lazy="joined")
    file: Mapped[File] = relationship(lazy="joined")
    versi: Mapped[list["PanduanHistori"]] = relationship(order_by="PanduanHistori.updated_date", lazy="selectin")  # riwayat saja

    def daftar_versi(self) -> list[tuple[int, "Panduan | PanduanHistori"]]:
        """[(nomor versi, baris)], terbaru dulu: terkini lalu riwayat. Nomor versi tidak disimpan (desain.md §7 no. 18):
        riwayat ke-n menurut `updated_date` = versi n, terkini = jumlah riwayat + 1. Stabil karena riwayat tidak pernah
        diubah dan hanya terhapus bersama panduannya (D6)."""
        return [(len(self.versi) + 1, self), *((n, v) for n, v in reversed(list(enumerate(self.versi, 1))))]


class PanduanHistori(Base):
    """Riwayat (Panduan Histori): salinan utuh baris `panduan` SEBELUM tiap perubahan — created_by/created_date tetap
    milik pengunggah pertama, updated_by/updated_date = penginput & waktu versi itu. Versi terkini ada di `panduan`.
    Baris tidak pernah diubah. Status pemrosesan mengikuti `file.status_ekstraksi`."""
    __tablename__ = "panduan_histori"
    id: Mapped[uuid.UUID] = _id()
    created_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    created_date: Mapped[datetime] = _dibuat()
    updated_by: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    updated_date: Mapped[datetime] = _dibuat()
    panduan_id: Mapped[uuid.UUID] = _fk("panduan")
    panduan: Mapped[str] = mapped_column(String(500))
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")  # status saat versi dibuat
    file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    nama_file: Mapped[str] = mapped_column(String(255))
    deskripsi: Mapped[str | None] = mapped_column(Text)
    file: Mapped[File] = relationship(lazy="joined")
    pengubah: Mapped[Pengguna | None] = relationship(foreign_keys=[updated_by], lazy="joined")


# ---------------------------------------------------------------- review
class Review(Base):
    """Satu revisi = satu review sukses. Review GAGAL boleh diulang → baris baru."""
    __tablename__ = "review"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    revisi_id: Mapped[uuid.UUID] = _fk("revisi")
    trace_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ANTRE")  # ANTRE|DIPROSES|SELESAI|GAGAL
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    disalin_dari_id: Mapped[uuid.UUID | None] = _fk("review", nullable=True, index=False)
    model_info: Mapped[dict | None] = mapped_column(JSONB)
    diajukan_oleh: Mapped[uuid.UUID] = _fk("pengguna", index=False)
    mulai_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selesai_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progres: Mapped[dict | None] = mapped_column(JSONB)
    error_pesan: Mapped[str | None] = mapped_column(Text)
    label_ai: Mapped[str | None] = mapped_column(String(20))  # dihitung KODE dari hasil_item (PRD §7.1)
    label_final: Mapped[str | None] = mapped_column(String(20))  # snapshot saat Finalkan
    kategori_final_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # id kategori di review_kategori, tanpa FK
    difinalkan_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    difinalkan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewPanduan(Base):
    """Panduan + versi yang dipakai review (D5): salinan saat acuan dikunci, sehingga tetap benar walau panduan diedit
    (versi terkini tidak punya baris di `panduan_histori`)."""
    __tablename__ = "review_panduan"
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review.id"), primary_key=True)
    panduan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("panduan.id"), primary_key=True)
    nomor: Mapped[int] = mapped_column(Integer)
    judul: Mapped[str] = mapped_column(String(500))
    file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    nama_file: Mapped[str] = mapped_column(String(255))


class ReviewKategori(Base):
    """Salinan daftar kategori yang dipakai review (C3/C4), dibuat saat acuan dikunci. `kategori_id` tanpa FK: kategori
    boleh diubah/dihapus permanen tanpa mengubah review lama. hasil_kategori, kategori_final_id, dan override KATEGORI
    menunjuk `kategori_id` ini."""
    __tablename__ = "review_kategori"
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review.id"), primary_key=True)
    kategori_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    kode: Mapped[str] = mapped_column(String(20))
    nama: Mapped[str] = mapped_column(String(255))
    definisi: Mapped[str] = mapped_column(Text)


class HasilItem(Base):
    __tablename__ = "hasil_item"
    __table_args__ = (UniqueConstraint("review_id", "checklist_item_id"),)
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = _fk("review")
    # Tanpa FK: item boleh dihapus permanen (lihat app/checklist.py).
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    terpenuhi: Mapped[bool]
    ditemukan: Mapped[bool] = mapped_column(Boolean, default=True)  # False = "tidak ditemukan di dokumen"
    alasan: Mapped[str] = mapped_column(Text)
    yang_kurang: Mapped[str | None] = mapped_column(Text)


class HasilKategori(Base):
    __tablename__ = "hasil_kategori"
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review.id"), unique=True)
    kategori_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))  # id kategori di review_kategori, tanpa FK
    alasan: Mapped[str] = mapped_column(Text)


class Rekomendasi(Base):
    __tablename__ = "rekomendasi"
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = _fk("review")
    dokumen: Mapped[str] = mapped_column(String(10))  # TOR|RAB
    urutan: Mapped[int] = mapped_column(Integer)
    teks: Mapped[str] = mapped_column(Text)
    checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # tanpa FK, lihat HasilItem
    tidak_diperlukan: Mapped[bool] = mapped_column(Boolean, default=False)


class Rujukan(Base):
    """Bukti E1/E2. Hanya menunjuk `elemen`; file, halaman, lokasi, bbox diambil dari elemen (E3)."""
    __tablename__ = "rujukan"
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = _fk("review")
    pemilik_jenis: Mapped[str] = mapped_column(String(20))  # hasil_item|rekomendasi|hasil_kategori
    pemilik_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    elemen_id: Mapped[uuid.UUID] = _fk("elemen", index=False)
    kutipan: Mapped[str] = mapped_column(Text)  # selalu substring asli teks elemen
    peran: Mapped[str] = mapped_column(String(20))  # bukti_dokumen|dasar_panduan
    urutan: Mapped[int] = mapped_column(Integer, default=0)


class Override(Base):
    """Override reviewer, terpisah dari hasil AI (O2). Batal = isi `dibatalkan_at`; riwayat tetap ada."""
    __tablename__ = "override"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    review_id: Mapped[uuid.UUID] = _fk("review")
    target: Mapped[str] = mapped_column(String(10))  # ITEM|LABEL|KATEGORI
    checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # tanpa FK, lihat HasilItem
    nilai_sebelum: Mapped[str] = mapped_column(String(100))
    nilai_sesudah: Mapped[str] = mapped_column(String(100))
    alasan: Mapped[str] = mapped_column(Text)
    oleh: Mapped[uuid.UUID] = _fk("pengguna", index=False)
    dibatalkan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dibatalkan_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)


class CatatanReviewer(Base):
    __tablename__ = "catatan_reviewer"
    __table_args__ = (UniqueConstraint("review_id", "dokumen"),)
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = _fk("review")
    dokumen: Mapped[str] = mapped_column(String(10))  # TOR|RAB|UMUM
    teks: Mapped[str] = mapped_column(Text)
    oleh: Mapped[uuid.UUID] = _fk("pengguna", index=False)
    diubah_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------- operasional
class Job(Base):
    __tablename__ = "job"
    __table_args__ = (Index("ix_job_antre", "status", "created_at"),)
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    jenis: Mapped[str] = mapped_column(String(20))  # REVIEW|PROSES_PANDUAN
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ANTRE")  # ANTRE|DIPROSES|SELESAI|GAGAL
    percobaan: Mapped[int] = mapped_column(Integer, default=0)
    dikunci_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dikunci_oleh: Mapped[str | None] = mapped_column(String(100))
    trace_id: Mapped[str] = mapped_column(String(32))
    selesai_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NodeAI(Base):
    """Node AI (worker + llm). Node jarak jauh memakai token sendiri yang dapat dicabut Admin (desain §2.4)."""
    __tablename__ = "node_ai"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    nama: Mapped[str] = mapped_column(String(100), unique=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    terakhir_terlihat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    info: Mapped[dict | None] = mapped_column(JSONB)


class AuditLog(Base):
    """Aktivitas pengguna (PRD §7.3). Hanya-tambah; terpisah dari log teknis."""
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = _id()
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    pengguna_id: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True)
    aksi: Mapped[str] = mapped_column(String(50), index=True)
    entitas: Mapped[str] = mapped_column(String(50))
    entitas_id: Mapped[str | None] = mapped_column(String(100))
    data_sebelum: Mapped[dict | None] = mapped_column(JSONB)
    data_sesudah: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
