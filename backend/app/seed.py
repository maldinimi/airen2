"""Data awal: 4 kategori PERSIS sesuai PRD C1 + akun admin awal.

Bila `SEED_CONTOH=true` (mode dev/tiruan), juga dibuat Satker, akun Pengusul/Reviewer, dan
checklist contoh agar alur lengkap dapat langsung dicoba. Seed hanya berjalan bila tabel kosong.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.keamanan import hash_password
from app.konfigurasi import konfigurasi
from app.model import (ChecklistHistory, ChecklistItem, Kategori, Pengguna, PenggunaRole,
                       Satker)

logger = logging.getLogger(__name__)

# Teks definisi WAJIB persis seperti PRD C1 — jangan diubah.
KATEGORI_AWAL = [
    ("K1", "RO Wajib",
     "RO yang bersifat wajib, mengikat, ditetapkan melalui kebijakan penganggaran nasional, dan harus tetap berjalan "
     "secara berkelanjutan. Penilaian terhadap RO pada kategori ini tidak ditujukan untuk menilai perlu atau tidaknya "
     "RO, melainkan untuk memvalidasi kesesuaian ruang lingkup, kejelasan kebutuhan dasar, dan keterkaitan komponen "
     "dengan RO yang diusulkan."),
    ("K2", "RO Prioritas Strategis",
     "RO prioritas yang ditetapkan secara resmi oleh Menteri, dan/atau penguatan layanan esensial. Penilaian RO "
     "terhadap kategori ini dilaksanakan secara penuh sesuai parameter penilaian substansi."),
    ("K3", "RO Strategis/Diskresioner",
     "RO yang memiliki keterkaitan dengan prioritas pembangunan nasional dan pencapaian sasaran kementerian, serta "
     "mendukung tugas dan fungsi Satker, namun tidak memenuhi kriteria Kategori 1 maupun Kategori 2."),
    ("K4", "RO Non-Strategis",
     "RO yang tidak memenuhi kriteria Kategori 1, Kategori 2, maupun Kategori 3, serta tidak memiliki keterkaitan "
     "dengan tugas dan fungsi Satker pengusul, maupun pencapaian sasaran strategis kementerian."),
]

CHECKLIST_CONTOH = [
    ("C01", "Latar belakang dan dasar hukum", "TOR menjelaskan latar belakang kebutuhan kegiatan dan menyebutkan dasar hukum/kebijakan yang relevan.", "TOR"),
    ("C02", "Tujuan dan sasaran", "TOR menyatakan tujuan dan sasaran kegiatan secara jelas dan spesifik.", "TOR"),
    ("C03", "Indikator keluaran terukur", "TOR memuat indikator keluaran (output) dengan target kuantitatif dan satuan yang jelas.", "TOR"),
    ("C04", "Metode dan tahapan pelaksanaan", "TOR menjelaskan metode pelaksanaan serta tahapan kegiatan.", "TOR"),
    ("C05", "Jadwal pelaksanaan", "TOR memuat jadwal/waktu pelaksanaan kegiatan.", "TOR"),
    ("C06", "Penerima manfaat", "TOR menyebutkan penerima manfaat kegiatan.", "TOR"),
    ("C07", "Rincian biaya sesuai standar biaya", "RAB merinci komponen biaya dengan volume, satuan, dan harga satuan yang sesuai standar biaya yang berlaku.", "RAB"),
    ("C08", "Kesesuaian komponen biaya dengan kegiatan", "Setiap komponen biaya pada RAB memiliki dasar kegiatan pada TOR.", "TOR & RAB"),
]


def jalankan_seed(db: Session) -> None:
    """Isi data awal bila belum ada. Aman dipanggil berulang (idempoten)."""
    k = konfigurasi()
    if db.scalar(select(Kategori.id).limit(1)) is None:
        for kode, nama, definisi in KATEGORI_AWAL:
            db.add(Kategori(kode=kode, kategori=nama, deskripsi=definisi))
        logger.info("seed kategori dibuat")

    if db.scalar(select(Pengguna.id).limit(1)) is None:
        admin = Pengguna(username=k.admin_username, nama="Administrator", password_hash=hash_password(k.admin_password_awal))
        admin.roles = [PenggunaRole(role="ADMIN")]
        db.add(admin)
        logger.info("akun admin awal dibuat", extra={"ekstra": {"username": k.admin_username}})
        if k.seed_contoh:
            _seed_contoh(db)
    db.commit()


def _seed_contoh(db: Session) -> None:
    satker = Satker(kode="SATKER-A", nama="Satker Contoh A")
    satker_b = Satker(kode="SATKER-B", nama="Satker Contoh B")
    db.add_all([satker, satker_b])
    db.flush()
    sandi = hash_password("Contoh!2026")
    for username, nama, roles, satker_id in [
        ("pengusul", "Pengusul Contoh A", ["PENGUSUL"], satker.id),
        ("pengusul_b", "Pengusul Contoh B", ["PENGUSUL"], satker_b.id),
        ("reviewer", "Reviewer Contoh", ["REVIEWER"], None),
    ]:
        p = Pengguna(username=username, nama=nama, password_hash=sandi, satker_id=satker_id)
        p.roles = [PenggunaRole(role=r) for r in roles]
        db.add(p)
    for i, (kode, judul, kriteria, berlaku) in enumerate(CHECKLIST_CONTOH, 1):
        isi = {"no_urut": i, "kode": kode, "checklist": judul, "kriteria": kriteria, "berlaku_untuk": berlaku, "aktif": True}
        item = ChecklistItem(**isi)
        db.add(item)
        db.flush()
        db.add(ChecklistHistory(checklist_id=item.id, **isi))
    logger.info("seed contoh dibuat (satker, pengusul, reviewer, checklist)")
