"""Logging terstruktur (JSON per baris) dengan konteks pelacakan (PRD §8.1).

Konteks (`trace_id`, `pengguna_id`, `usulan_id`, `revisi_id`, `review_id`) disimpan di
contextvars sehingga otomatis ikut di setiap entri log dalam request/job yang sama.
Log tidak boleh memuat password, token, atau isi dokumen utuh — hanya ID dan panjang.
"""
import contextvars
import json
import logging
import logging.handlers
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

_KONTEKS = ("trace_id", "pengguna_id", "usulan_id", "revisi_id", "review_id", "job_id")
_ctx: dict[str, contextvars.ContextVar] = {k: contextvars.ContextVar(k, default=None) for k in _KONTEKS}


def set_konteks(**nilai) -> None:
    """Pasang nilai konteks log untuk request/job yang sedang berjalan."""
    for k, v in nilai.items():
        if k in _ctx:
            _ctx[k].set(str(v) if v is not None else None)


def trace_id_saat_ini() -> str | None:
    return _ctx["trace_id"].get()


def bersihkan_konteks() -> None:
    for var in _ctx.values():
        var.set(None)


class FormatJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "waktu": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "modul": record.name,
            "pesan": record.getMessage(),
        }
        for k, var in _ctx.items():
            if var.get() is not None:
                data[k] = var.get()
        for k, v in getattr(record, "ekstra", {}).items():
            data[k] = v
        if record.exc_info:
            data["error"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def siapkan_logging(nama_file: str) -> None:
    """Pasang handler stdout + file berotasi di `<data_dir>/logs/<nama_file>`."""
    from app.konfigurasi import konfigurasi

    k = konfigurasi()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(k.log_level.upper())
    fmt = FormatJSON()
    keluar = logging.StreamHandler(sys.stdout)
    keluar.setFormatter(fmt)
    root.addHandler(keluar)
    folder = os.path.join(k.data_dir, "logs")
    try:
        os.makedirs(folder, exist_ok=True)
        berkas = logging.handlers.RotatingFileHandler(
            os.path.join(folder, nama_file), maxBytes=k.log_ukuran_mb * 1024 * 1024,
            backupCount=k.log_jumlah_file, encoding="utf-8")
        berkas.setFormatter(fmt)
        root.addHandler(berkas)
    except OSError:
        root.warning("Folder log tidak dapat ditulis, log hanya ke stdout")
    # Library pihak ketiga yang cerewet
    for nama in ("httpx", "httpcore", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(nama).setLevel(logging.WARNING)


def log(logger: logging.Logger, level: int, pesan: str, **ekstra) -> None:
    """Tulis log dengan field tambahan terstruktur (mis. durasi_ms, tahap)."""
    logger.log(level, pesan, extra={"ekstra": ekstra})


@contextmanager
def tahap(logger: logging.Logger, nama: str, **ekstra):
    """Catat mulai/selesai suatu tahap beserta durasinya; error dicatat lalu diteruskan."""
    mulai = time.monotonic()
    log(logger, logging.INFO, f"mulai {nama}", tahap=nama, **ekstra)
    try:
        yield
    except Exception:
        logger.exception(f"gagal {nama}", extra={"ekstra": {"tahap": nama, "durasi_ms": int((time.monotonic() - mulai) * 1000)}})
        raise
    log(logger, logging.INFO, f"selesai {nama}", tahap=nama, durasi_ms=int((time.monotonic() - mulai) * 1000), **ekstra)
