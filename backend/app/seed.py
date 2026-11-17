"""Data awal: 4 kategori PERSIS sesuai PRD C1 + akun admin awal.

Daftar Satker awal dari dokumen "Data Satker dan Unit Kerja" (app/data_satker.py) diisi bila tabel satker kosong.
Master RO awal dari Laporan Renja K/L TA 2026 revisi (app/data_master_ro.py) diisi bila tabel master_ro kosong. Berkas
data itu OPSIONAL dan tidak di-commit (.gitignore); tanpa berkas itu Master RO mulai kosong.

Bila `SEED_CONTOH=true` (mode dev/tiruan), juga dibuat akun Pengusul/Reviewer, dan
checklist contoh agar alur lengkap dapat langsung dicoba. Seed hanya berjalan bila tabel kosong.
"""
import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.checklist import rapikan_fisik
from app.data_satker import SATKER
from app.keamanan import hash_password
from app.konfigurasi import konfigurasi
from app.model import (ChecklistHistory, ChecklistItem, Kategori, MasterRO, Pengguna, PenggunaRole,
                       Satker)



def baris_master_ro() -> list[dict]:
    """Baris data awal Master RO dari berkas opsional `app/data_master_ro.py`; [] bila berkas tidak ada."""
    try:
        from app.data_master_ro import baris_lengkap
    except ModuleNotFoundError as e:
        if e.name != "app.data_master_ro":
            raise
        return []
    return baris_lengkap()


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
    """Isi data awal bila belum ada. Aman dipanggil berulang (idempoten).

    Penginput (`created_by`/`updated_by`) data awal mengikuti role pengelolanya (desain.md §7 no. 29), agar kolom
    "Diinput Oleh" tidak menampilkan "Sistem" bila akunnya ada (docs/asumsi.md):
    - Kategori, Satuan Kerja, Master RO, checklist contoh → akun contoh `reviewer` (hanya ada bila `SEED_CONTOH=true`). Tanpa
      akun Reviewer (instalasi produksi) dibiarkan kosong = "Sistem", sebab memang dibuat sistem.
    - Akun contoh → akun admin awal. Akun admin awal sendiri tetap tanpa pembuat (dibuat sistem)."""
    k = konfigurasi()
    data_awal: list = []  # baris seed yang dikelola Reviewer, diberi penginput setelah akun Reviewer ada
    if db.scalar(select(Kategori.id).limit(1)) is None:
        for n, (kode, nama, definisi) in enumerate(KATEGORI_AWAL, 1):
            data_awal.append(Kategori(kode=kode, kategori=nama, deskripsi=definisi, no_urut=n))
        db.add_all(data_awal)
        logger.info("seed kategori dibuat")

    if db.scalar(select(Satker.id).limit(1)) is None:
        satker = [Satker(**s) for s in SATKER]
        db.add_all(satker)
        data_awal += satker
        db.flush()
        logger.info("seed satker dibuat", extra={"ekstra": {"jumlah": len(SATKER)}})

    if db.scalar(select(MasterRO.id).limit(1)) is None:
        # Berkas data Renja (opsional) dapat memuat kolom lain (Unit Eselon I/II & Prioritas) yang tidak ada di tabel
        # master_ro, jadi hanya kolom yang ada di model yang diisi.
        kolom = set(MasterRO.__table__.columns.keys())
        master_ro = [MasterRO(**{k: v for k, v in b.items() if k in kolom}) for b in baris_master_ro()]
        db.add_all(master_ro)
        data_awal += master_ro
        db.flush()
        logger.info("seed master RO dibuat", extra={"ekstra": {"jumlah": len(master_ro)}})

    if db.scalar(select(Pengguna.id).limit(1)) is None:
        admin = Pengguna(username=k.admin_username, password_hash=hash_password(k.admin_password_awal))
        admin.roles = [PenggunaRole(role="ADMIN")]
        db.add(admin)
        db.flush()
        logger.info("akun admin awal dibuat", extra={"ekstra": {"username": k.admin_username}})
        if k.seed_contoh:
            reviewer = _seed_contoh(db, admin, data_awal)
            # Satu UPDATE per tabel, bukan satu per baris (±800 baris termasuk Master RO).
            per_tabel: dict[type, list] = {}
            for x in data_awal:
                per_tabel.setdefault(type(x), []).append(x.id)
            for model, ids in per_tabel.items():
                db.execute(update(model).where(model.id.in_(ids)).values(created_by=reviewer.id, updated_by=reviewer.id))
    if any(isinstance(x, MasterRO) for x in data_awal):
        # Urutan fisik Master RO = urutan di layar (pgAdmin "View Data"), sama seperti setelah tambah/impor.
        rapikan_fisik(db, "master_ro", "ix_master_ro_created_date")
    db.commit()


def _seed_contoh(db: Session, admin: Pengguna, data_awal: list) -> Pengguna:
    """Akun contoh (dibuat oleh `admin`) + checklist contoh (ditambahkan ke `data_awal`). Kembalikan akun `reviewer`."""
    # Akun contoh memakai Satker asli dari daftar seed (Biro Perencanaan & Pusat Data dan Sarana Informatika).
    satker = db.scalar(select(Satker).where(Satker.kode_uke2 == "01.04"))
    satker_b = db.scalar(select(Satker).where(Satker.kode_uke2 == "01.06"))
    sandi = hash_password("Contoh!2026")
    akun: dict[str, Pengguna] = {}
    for username, roles, satker_id in [
        ("pengusul", ["PENGUSUL"], satker.id),
        ("pengusul_b", ["PENGUSUL"], satker_b.id),
        ("reviewer", ["REVIEWER"], None),
    ]:
        p = Pengguna(username=username, password_hash=sandi, satker_id=satker_id, created_by=admin.id, updated_by=admin.id)
        p.roles = [PenggunaRole(role=r) for r in roles]
        db.add(p)
        akun[username] = p
    for i, (kode, judul, kriteria, berlaku) in enumerate(CHECKLIST_CONTOH, 1):
        isi = {"no_urut": i, "kode": kode, "checklist": judul, "kriteria": kriteria, "berlaku_untuk": berlaku, "aktif": True}
        item = ChecklistItem(**isi)
        db.add(item)
        db.flush()
        h = ChecklistHistory(checklist_id=item.id, **isi)
        db.add(h)
        data_awal += [item, h]
    db.flush()
    logger.info("seed contoh dibuat (pengusul, reviewer, checklist)")
    return akun["reviewer"]
