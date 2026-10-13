# Image backend untuk layanan api, migrasi, dan worker.
# PROFIL=ringan  : api/migrasi/worker mode tiruan (tanpa Docling/torch, kecil, termasuk alat uji)
# PROFIL=lengkap : worker GPU (Docling + Tesseract OCR bahasa Indonesia + sentence-transformers)
FROM python:3.12-slim-bookworm

ARG PROFIL=ringan
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 \
    ANONYMIZED_TELEMETRY=false TOKENIZERS_PARALLELISM=false

RUN if [ "$PROFIL" = "lengkap" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng libgl1 libglib2.0-0 && \
      rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-uji.txt && \
    if [ "$PROFIL" = "lengkap" ]; then pip install --no-cache-dir -r requirements-lengkap.txt; fi

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
