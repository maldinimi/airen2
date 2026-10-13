"""Konfigurasi aplikasi, dibaca dari variabel environment (file `.env`).

Perpindahan Development ↔ Production cukup mengganti `.env` (PRD §8.2), tidak mengubah kode.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Konfigurasi(BaseSettings):
    # Umum
    profil: str = "dev"  # dev | prod | tiruan — hanya informasi, dicatat di review.model_info
    ai_mode: str = "nyata"  # nyata | tiruan (tanpa GPU, jawaban AI tetap)
    database_url: str = "postgresql+psycopg://airen:airen@db:5432/airen"
    data_dir: str = "/data"
    log_level: str = "INFO"
    log_ukuran_mb: int = 50
    log_jumlah_file: int = 10

    # Keamanan & sesi
    sesi_jam: int = 12
    cookie_secure: bool = False  # set true bila diakses lewat HTTPS
    maks_ukuran_pdf_mb: int = 100
    login_maks_gagal: int = 5
    login_jendela_menit: int = 15

    # Seed awal
    admin_username: str = "admin"
    admin_password_awal: str = "GantiSegera!2026"
    seed_contoh: bool = False

    # AI
    llm_url: str = "http://llm:8000/v1"
    llm_model: str = "cyankiwi/Qwen3-VL-8B-Thinking-AWQ-4bit"
    llm_timeout_detik: int = 1800
    llm_seed: int = 20261012
    llm_maks_token: int = 8192
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    ekstraktor: str = "docling"  # docling | sederhana (tanpa OCR, untuk mode tiruan)
    item_paralel: int = 2
    kandidat_dokumen: int = 12
    kandidat_panduan: int = 10
    jendela_sapuan_halaman: int = 8
    konteks_maks_karakter: int = 60000  # anggaran teks konteks per panggilan LLM (dev 32k token, prod 64k)

    # Worker / node AI
    node_nama: str = "node-lokal"
    node_token: str = ""  # diisi pada node AI jarak jauh (GPU sewaan)
    sumber_file: str = "lokal"  # lokal | api (node jarak jauh mengambil PDF lewat API, disimpan di tmpfs)
    api_internal_url: str = "http://api:8000"
    job_batas_kunci_menit: int = 5  # detak worker tiap 20 detik; tanpa detak selama ini → job dianggap macet

    model_config = {"env_file": None, "extra": "ignore"}

    @property
    def maks_ukuran_pdf(self) -> int:
        return self.maks_ukuran_pdf_mb * 1024 * 1024

    @property
    def tiruan(self) -> bool:
        return self.ai_mode == "tiruan"


@lru_cache
def konfigurasi() -> Konfigurasi:
    return Konfigurasi()
