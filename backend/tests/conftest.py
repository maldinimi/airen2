"""Fixture pengujian. Dijalankan di kontainer `api` (lihat `make test`) terhadap database terpisah `<db>_uji`,
dengan AI tiruan dan ekstraktor sederhana sehingga cepat dan deterministik."""
import os
import tempfile

_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://airen:airen@db:5432/airen")
_DB_UJI = _url.rsplit("/", 1)[0] + "/" + _url.rsplit("/", 1)[1].split("?")[0] + "_uji"
os.environ.update(DATABASE_URL=_DB_UJI, AI_MODE="tiruan", EKSTRAKTOR="sederhana", SEED_CONTOH="true",
                  DATA_DIR=tempfile.mkdtemp(prefix="airen-uji-"), ITEM_PARALEL="2", LOG_LEVEL="WARNING")

import io  # noqa: E402

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fpdf import FPDF  # noqa: E402


def _buat_database() -> None:
    dasar = _DB_UJI.replace("postgresql+psycopg://", "postgresql://")
    nama = dasar.rsplit("/", 1)[1]
    with psycopg.connect(dasar.rsplit("/", 1)[0] + "/postgres", autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (nama,)).fetchone():
            c.execute(f'CREATE DATABASE "{nama}"')


_buat_database()

from sqlalchemy import text  # noqa: E402

from app import model  # noqa: E402,F401
from app.db import Base, SessionLokal, engine  # noqa: E402

with engine.begin() as _c:
    # Skema dibuat ulang dari nol (bukan drop_all): sisa tabel/constraint dari model versi lama ikut terhapus.
    _c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public; CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(engine)


@pytest.fixture
def db_bersih():
    """Kosongkan seluruh tabel lalu isi seed (kategori, admin, contoh)."""
    from app.seed import jalankan_seed

    with engine.begin() as c:
        c.execute(text("TRUNCATE " + ", ".join(t.name for t in Base.metadata.sorted_tables) + " CASCADE"))
    with SessionLokal() as db:
        jalankan_seed(db)
    yield


@pytest.fixture
def klien(db_bersih):
    from fastapi.testclient import TestClient

    from app.main import app

    def buat(username: str | None = None, password: str = "Contoh!2026") -> TestClient:
        c = TestClient(app)
        if username:
            r = c.post("/api/auth/login", json={"username": username, "password": password})
            assert r.status_code == 200, r.text
            c.headers["X-CSRF-Token"] = r.json()["csrf"]
        return c
    return buat


def buat_pdf(paragraf: list[str], tabel: list[list[str]] | None = None) -> bytes:
    """PDF sederhana untuk uji: paragraf teks + tabel opsional."""
    pdf = FPDF()
    pdf.set_font("helvetica", size=11)
    pdf.add_page()
    for p in paragraf:
        if p == "<halaman>":
            pdf.add_page()
            continue
        pdf.multi_cell(0, 6, p)
        pdf.ln(4)
    if tabel:
        with pdf.table() as t:
            for baris in tabel:
                row = t.row()
                for sel in baris:
                    row.cell(sel)
    return bytes(pdf.output())


TOR_CONTOH = [
    "BAB I PENDAHULUAN",
    "1.1 Latar Belakang",
    "Kegiatan ini dilaksanakan berdasarkan Peraturan Menteri Nomor 5 Tahun 2025 tentang layanan digital pemerintah.",
    "1.2 Tujuan",
    "Tujuan kegiatan adalah meningkatkan kualitas layanan digital bagi masyarakat di 34 provinsi.",
    "<halaman>",
    "BAB II PELAKSANAAN",
    "2.1 Indikator Keluaran",
    "Keluaran kegiatan berupa 10 aplikasi layanan yang terintegrasi dengan target 1.000 pengguna.",
    "2.2 Jadwal",
    "Kegiatan dilaksanakan pada Januari sampai Desember 2027 dengan metode swakelola.",
    "Penerima manfaat kegiatan adalah masyarakat umum dan aparatur sipil negara.",
]
RAB_CONTOH = [["Komponen", "Volume", "Satuan", "Harga Satuan"],
              ["Honor narasumber", "10", "OJ", "1.700.000"],
              ["Paket rapat", "20", "OK", "450.000"]]


# Data menu Master RO untuk uji usulan: (kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro, kode_ro, ro).
_P, _G = ("059.WA", "Program Dukungan Manajemen"), ("4490", "Pengelolaan Keuangan, BMN dan Umum BAKTI")
_EBA, _EBD = ("EBA", "Layanan Dukungan Manajemen Internal"), ("EBD", "Layanan Manajemen Kinerja Internal")
MASTER_RO_UJI = [(*_P, "", "", "", "", "", ""), (*_P, *_G, "", "", "", ""), (*_P, *_G, *_EBA, "", ""), (*_P, *_G, *_EBD, "", ""),
                 (*_P, *_G, *_EBA, "994", "Layanan Perkantoran"), (*_P, *_G, *_EBA, "962", "Layanan Umum")]


def isi_master_ro(tahun: int | None = None) -> None:
    """Isi menu Master RO Tahun Anggaran `tahun` (bawaan: tahun berjalan) dengan jalur uji bila tahun itu belum berisi:
    Pengajuan Baru tahun X memilih hierarki dari Master RO tahun X. RO uji diberi Satker pelaksana = Satker akun Pengusul contoh (01.04 & 01.06, seed.py), karena Pengusul hanya dapat memilih RO
    Satker-nya sendiri."""
    from sqlalchemy import select
    from app.api.master_ro import tahun_berjalan
    from app.model import MasterRO, MasterROSatker, Satker
    kolom = ("kode_program", "program", "kode_kegiatan", "kegiatan", "kode_kro", "kro", "kode_ro", "ro")
    tahun = tahun or tahun_berjalan()
    with SessionLokal() as db:
        if db.scalar(select(MasterRO.id).where(MasterRO.tahun_anggaran == tahun).limit(1)) is None:
            baris = [MasterRO(**dict(zip(kolom, b)), tahun_anggaran=tahun) for b in MASTER_RO_UJI]
            db.add_all(baris)
            db.flush()
            satker = list(db.scalars(select(Satker.id).where(Satker.kode_uke2.in_(("01.04", "01.06")))))
            db.add_all(MasterROSatker(master_ro_id=m.id, satker_id=s, no_urut=n)
                       for m in baris if m.kode_ro for n, s in enumerate(satker, start=1))
            db.commit()


def isian(c, kode_kategori: str = "K1") -> dict:
    """Pilihan form Pengajuan yang sah: hierarki dari Master RO (jalur uji) + kategori Aktif + tahun berjalan (WIB)."""
    from app.api.usulan import tahun_berjalan
    isi_master_ro()
    k = next(k for k in c.get("/api/usulan/opsi/pengajuan").json()["kategori"] if k["kode"] == kode_kategori)
    return {"program": "059.WA", "kegiatan": "4490", "kro": "EBA", "ro": "994", "kategori_id": k["id"],
            "tahun_anggaran": tahun_berjalan()}


def unggah(c, path="/api/usulan", tor=None, rab=None, **form):
    """Kirim form multipart usulan/revisi."""
    files = {}
    if tor is not None:
        files["tor"] = ("tor.pdf", io.BytesIO(tor), "application/pdf")
    if rab is not None:
        files["rab"] = ("rab.pdf", io.BytesIO(rab), "application/pdf")
    return c.post(path, data={k: str(v) for k, v in form.items()}, files=files)


def jalankan_antrean() -> int:
    """Jalankan semua job antre secara sinkron (meniru worker). Kembalikan jumlah job."""
    from app.pekerja.llm import klien as klien_llm
    from app.pekerja.utama import ambil_job, daftar_node, jalankan_job

    daftar_node()
    n = 0
    while (job := ambil_job("node-uji")) is not None:
        jalankan_job(job, klien_llm())
        n += 1
    return n
