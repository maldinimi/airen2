"""Aplikasi FastAPI (layanan `api`).

Dokumentasi interaktif (Swagger) dimatikan karena memuat aset dari CDN (melanggar B1);
skema OpenAPI tetap tersedia di /api/openapi.json dan ringkasannya di docs/api.md.
"""
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import admin, auth, dashboard, master, panduan, review, usulan
from app.galat import Galat
from app.log import bersihkan_konteks, log, set_konteks, siapkan_logging, trace_id_saat_ini

siapkan_logging("api.log")
logger = logging.getLogger("api")

app = FastAPI(title="AIREN — Review TOR & RAB", version="1.0.0", docs_url=None, redoc_url=None,
              openapi_url="/api/openapi.json")
for r in (auth, usulan, review, master, panduan, admin, dashboard):
    app.include_router(r.router)


@app.middleware("http")
async def konteks_request(request: Request, call_next):
    """Setiap request punya trace_id sendiri (header X-Trace-Id) untuk ditelusuri di log."""
    bersihkan_konteks()
    trace_id = uuid.uuid4().hex
    set_konteks(trace_id=trace_id)
    mulai = time.monotonic()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    if request.url.path != "/api/sehat":
        log(logger, logging.INFO, "request", metode=request.method, path=request.url.path, status=response.status_code,
            durasi_ms=int((time.monotonic() - mulai) * 1000))
    return response


@app.exception_handler(Galat)
async def tangani_galat(request: Request, e: Galat) -> JSONResponse:
    return JSONResponse({"pesan": e.pesan}, status_code=e.status)


@app.exception_handler(RequestValidationError)
async def tangani_validasi(request: Request, e: RequestValidationError) -> JSONResponse:
    kolom = ", ".join(str(err["loc"][-1]) for err in e.errors())
    return JSONResponse({"pesan": f"Data tidak lengkap atau tidak valid: {kolom}."}, status_code=422)


@app.exception_handler(Exception)
async def tangani_error(request: Request, e: Exception) -> JSONResponse:
    """Error tak terduga: detail teknis ke log, pengguna hanya melihat pesan ramah + ID pelacakan."""
    logger.exception("error tak terduga")
    return JSONResponse({"pesan": "Terjadi kesalahan pada server. Laporkan ID pelacakan berikut ke Admin.",
                         "trace_id": trace_id_saat_ini()}, status_code=500)


@app.get("/api/sehat", include_in_schema=False)
def sehat() -> dict:
    return {"ok": True}
