"""Migrasi skema + seed, dijalankan otomatis oleh layanan `migrasi` saat `make up`.

Database baru: skema dibuat langsung dari model lalu di-`stamp` ke head Alembic
(pola "create from scratch" Alembic). Database lama: `alembic upgrade head`.
Perubahan skema berikutnya ditambahkan sebagai revisi Alembic di `backend/migrasi/versions`.
"""
import logging
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app import model  # noqa: F401  — mendaftarkan semua tabel ke Base.metadata
from app.db import Base, SessionLokal, engine
from app.log import siapkan_logging
from app.seed import jalankan_seed

logger = logging.getLogger("migrasi")


def konfigurasi_alembic() -> Config:
    folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(folder, "migrasi"))
    return cfg


def migrasi() -> None:
    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    cfg = konfigurasi_alembic()
    if not inspect(engine).has_table("alembic_version"):
        Base.metadata.create_all(engine)
        command.stamp(cfg, "head")
        logger.info("skema database dibuat")
    else:
        command.upgrade(cfg, "head")
        logger.info("skema database diperbarui")
    with SessionLokal() as db:
        jalankan_seed(db)


if __name__ == "__main__":
    import sys

    siapkan_logging("migrasi.log")
    if len(sys.argv) >= 3 and sys.argv[1] == "revisi":
        command.revision(konfigurasi_alembic(), message=sys.argv[2], autogenerate=True)
    else:
        migrasi()
