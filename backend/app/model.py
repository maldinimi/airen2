"""Model database (desain.md §3).

Prinsip:
- Snapshot tidak berubah: versi checklist/kategori/panduan tidak pernah di-UPDATE/DELETE;
  perubahan = baris versi baru. Review menunjuk ke versi sehingga tampilan review lama tetap.
- Hasil AI dan override dipisah; nilai final dihitung (app/nilai_final.py), tidak ditimpa.
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (BigInteger, Boolean, Computed, DateTime, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, func)
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
    __tablename__ = "satker"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    kode: Mapped[str] = mapped_column(String(50), unique=True)
    nama: Mapped[str] = mapped_column(String(255))
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)


class Pengguna(Base):
    __tablename__ = "pengguna"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    username: Mapped[str] = mapped_column(String(100), unique=True)
    nama: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    satker_id: Mapped[uuid.UUID | None] = _fk("satker", nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roles: Mapped[list["PenggunaRole"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    satker: Mapped[Satker | None] = relationship(lazy="joined")

    @property
    def daftar_role(self) -> set[str]:
        return {r.role for r in self.roles}


class PenggunaRole(Base):
    __tablename__ = "pengguna_role"
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
class ChecklistVersi(Base):
    __tablename__ = "checklist_versi"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    nomor: Mapped[int] = mapped_column(Integer, unique=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    dibuat_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    catatan: Mapped[str | None] = mapped_column(Text)
    item: Mapped[list["ChecklistItem"]] = relationship(order_by="ChecklistItem.urutan", lazy="selectin")


class ChecklistItem(Base):
    __tablename__ = "checklist_item"
    id: Mapped[uuid.UUID] = _id()
    versi_id: Mapped[uuid.UUID] = _fk("checklist_versi")
    urutan: Mapped[int] = mapped_column(Integer)
    kode: Mapped[str] = mapped_column(String(50))
    judul: Mapped[str] = mapped_column(String(500))
    kriteria: Mapped[str] = mapped_column(Text)
    berlaku_untuk: Mapped[str] = mapped_column(String(10))  # TOR|RAB|KEDUANYA


class KategoriVersi(Base):
    __tablename__ = "kategori_versi"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    nomor: Mapped[int] = mapped_column(Integer, unique=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    dibuat_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    catatan: Mapped[str | None] = mapped_column(Text)
    item: Mapped[list["KategoriItem"]] = relationship(order_by="KategoriItem.urutan", lazy="selectin")


class KategoriItem(Base):
    __tablename__ = "kategori_item"
    id: Mapped[uuid.UUID] = _id()
    versi_id: Mapped[uuid.UUID] = _fk("kategori_versi")
    urutan: Mapped[int] = mapped_column(Integer)
    kode: Mapped[str] = mapped_column(String(20))
    nama: Mapped[str] = mapped_column(String(255))
    definisi: Mapped[str] = mapped_column(Text)
    diteruskan: Mapped[bool] = mapped_column(Boolean, default=True)  # False = "tidak diteruskan" (K4), tidak di-hardcode


class Panduan(Base):
    __tablename__ = "panduan"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    judul_terkini: Mapped[str] = mapped_column(String(500))
    dihapus_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # soft delete (D6)
    versi: Mapped[list["PanduanVersi"]] = relationship(order_by="PanduanVersi.nomor", lazy="selectin")


class PanduanVersi(Base):
    """Setiap ganti judul/deskripsi/file → versi baru. Status pemrosesan mengikuti `file.status_ekstraksi`."""
    __tablename__ = "panduan_versi"
    __table_args__ = (UniqueConstraint("panduan_id", "nomor"),)
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    panduan_id: Mapped[uuid.UUID] = _fk("panduan")
    nomor: Mapped[int] = mapped_column(Integer)
    judul: Mapped[str] = mapped_column(String(500))
    deskripsi: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[uuid.UUID] = _fk("file", index=False)
    nama_file: Mapped[str] = mapped_column(String(255))
    dibuat_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    file: Mapped[File] = relationship(lazy="joined")


class PanduanKoleksiVersi(Base):
    """Snapshot daftar panduan (seperti versi checklist/kategori): setiap unggah/ubah/hapus → versi baru.
    Isi = versi terbaru tiap panduan yang tidak dihapus saat itu; baris lama tidak pernah diubah."""
    __tablename__ = "panduan_koleksi_versi"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    nomor: Mapped[int] = mapped_column(Integer, unique=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    dibuat_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    catatan: Mapped[str | None] = mapped_column(Text)
    item: Mapped[list["PanduanKoleksiItem"]] = relationship(order_by="PanduanKoleksiItem.urutan", lazy="selectin")


class PanduanKoleksiItem(Base):
    __tablename__ = "panduan_koleksi_item"
    id: Mapped[uuid.UUID] = _id()
    versi_id: Mapped[uuid.UUID] = _fk("panduan_koleksi_versi")
    urutan: Mapped[int] = mapped_column(Integer)
    panduan_versi_id: Mapped[uuid.UUID] = _fk("panduan_versi", index=False)
    panduan_versi: Mapped[PanduanVersi] = relationship(lazy="joined")


# ---------------------------------------------------------------- review
class Review(Base):
    """Satu revisi = satu review sukses. Review GAGAL boleh diulang → baris baru."""
    __tablename__ = "review"
    id: Mapped[uuid.UUID] = _id()
    created_at: Mapped[datetime] = _dibuat()
    revisi_id: Mapped[uuid.UUID] = _fk("revisi")
    trace_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ANTRE")  # ANTRE|DIPROSES|SELESAI|GAGAL
    checklist_versi_id: Mapped[uuid.UUID | None] = _fk("checklist_versi", nullable=True, index=False)
    kategori_versi_id: Mapped[uuid.UUID | None] = _fk("kategori_versi", nullable=True, index=False)
    # Versi daftar panduan saat dikunci; file yang benar-benar dipakai (hanya yang SIAP) ada di review_panduan.
    panduan_koleksi_versi_id: Mapped[uuid.UUID | None] = _fk("panduan_koleksi_versi", nullable=True, index=False)
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
    kategori_final_id: Mapped[uuid.UUID | None] = _fk("kategori_item", nullable=True, index=False)
    difinalkan_oleh: Mapped[uuid.UUID | None] = _fk("pengguna", nullable=True, index=False)
    difinalkan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewPanduan(Base):
    __tablename__ = "review_panduan"
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review.id"), primary_key=True)
    panduan_versi_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("panduan_versi.id"), primary_key=True)


class HasilItem(Base):
    __tablename__ = "hasil_item"
    __table_args__ = (UniqueConstraint("review_id", "checklist_item_id"),)
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = _fk("review")
    checklist_item_id: Mapped[uuid.UUID] = _fk("checklist_item", index=False)
    terpenuhi: Mapped[bool]
    ditemukan: Mapped[bool] = mapped_column(Boolean, default=True)  # False = "tidak ditemukan di dokumen"
    alasan: Mapped[str] = mapped_column(Text)
    yang_kurang: Mapped[str | None] = mapped_column(Text)


class HasilKategori(Base):
    __tablename__ = "hasil_kategori"
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review.id"), unique=True)
    kategori_item_id: Mapped[uuid.UUID] = _fk("kategori_item", index=False)
    alasan: Mapped[str] = mapped_column(Text)


class Rekomendasi(Base):
    __tablename__ = "rekomendasi"
    id: Mapped[uuid.UUID] = _id()
    review_id: Mapped[uuid.UUID] = _fk("review")
    dokumen: Mapped[str] = mapped_column(String(10))  # TOR|RAB
    urutan: Mapped[int] = mapped_column(Integer)
    teks: Mapped[str] = mapped_column(Text)
    checklist_item_id: Mapped[uuid.UUID | None] = _fk("checklist_item", nullable=True, index=False)
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
    checklist_item_id: Mapped[uuid.UUID | None] = _fk("checklist_item", nullable=True, index=False)
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
