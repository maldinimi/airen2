# AIREN — Asisten AI Offline untuk Review TOR & RAB

Aplikasi web untuk mereview dokumen TOR & RAB usulan anggaran dengan AI lokal:

- **Screening 1**: menilai pemenuhan setiap item checklist, dengan bukti (halaman, lokasi, kutipan) dari TOR/RAB dan Panduan. Label LOLOS/TIDAK LOLOS **dihitung oleh kode**.
- **Screening 2**: merekomendasikan kategori K1–K4 berdasarkan definisi kategori yang aktif.
- **Reviewer** memverifikasi, meng-override (dengan alasan), lalu memfinalkan. Pengusul mengunggah revisi hingga LOLOS.

Seluruh pemrosesan berjalan **offline** di kontainer. Satu-satunya pengecualian adalah terowongan terenkripsi ke node GPU sewaan. Acuan kebutuhan ada di [prd.md](prd.md) dan acuan teknis di [desain.md](desain.md).

## Menjalankan

Prasyarat: **Docker** (Docker Desktop di Windows/Mac). Untuk mode dev dengan GPU, tambahkan **NVIDIA Container Toolkit**.

| Skenario | Perintah | Kebutuhan |
| --- | --- | --- |
| **AI tiruan** (tanpa GPU, untuk UI/backend/CI) | `cp .env.tiruan .env && make setup && make up` | Docker saja |
| **Development** (RTX A6000 Laptop 16 GB, Qwen3-VL 8B AWQ) | `cp .env.dev .env && make setup && make up` | GPU NVIDIA ≥16 GB, ±40 GB disk untuk model |
| **Production** server aplikasi | `cp .env.prod .env` (sunting password), `make setup && make up` | Lihat [docs/instalasi-offline.md](docs/instalasi-offline.md) |
| **Node AI** production (H100 NVL sewaan) | `cp .env.node-ai .env && make setup-ai && make up-ai` | GPU H100 94 GB + WireGuard |

Buka **http://localhost:8080**. Akun awal:

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `GantiSegera!2026` (dari `ADMIN_PASSWORD_AWAL`) | Admin |
| `pengusul`, `pengusul_b` | `Contoh!2026` | Pengusul (Satker Contoh A / B), **hanya dev & tiruan** |
| `reviewer` | `Contoh!2026` | Reviewer, **hanya dev & tiruan** |

Mode dev & tiruan juga membuat checklist contoh. PDF contoh untuk dicoba tersedia di folder [contoh/](contoh/).

`make setup` adalah satu-satunya langkah yang membutuhkan internet (build image + unduh model). Setelah itu aplikasi berjalan tanpa internet. Saat `make up`, migrasi database dan seed (4 kategori sesuai PRD C1 + admin) berjalan otomatis.

### Tanpa `make` (mis. Windows PowerShell)

`make` hanya membungkus `docker compose`. Skenario dipilih otomatis lewat `COMPOSE_FILE` di `.env`.

```bash
docker compose build
```
```bash
docker compose --profile setup run --rm pengunduh
```
```bash
docker compose up -d
```
```bash
docker compose run --rm api pytest -q
```

Perintah lain: `docker compose logs -f`, `docker compose ps`, `docker compose down`.

## Perintah `make`

| Perintah | Fungsi |
| --- | --- |
| `make setup` / `make up` / `make down` | Persiapan (internet), jalankan, hentikan |
| `make logs` / `make status` | Log & status layanan |
| `make test` | Pengujian otomatis (database uji terpisah, AI tiruan) |
| `make doctor` | Periksa prasyarat (Docker, GPU, VRAM, model, port) |
| `make cek-offline` | Verifikasi tidak ada jalur keluar ke internet |
| `make backup` / `make restore FILE=backup/<waktu>` | Backup & restore database + file PDF |
| `make bundle` / `make install-offline FILE=…` | Paket instalasi untuk server tanpa internet |
| `make setup-ai` / `make up-ai` | Node AI di server GPU |

## Pengujian

Jalankan `make test`. Cakupannya:

- aturan label §7.1;
- nilai final & override O1–O8;
- transisi status;
- verifikasi rujukan (E3) dan invarian kutipan;
- fingerprint/konsistensi hasil;
- versioning checklist/kategori/panduan;
- hak akses role + Satker, CSRF, dan validasi unggahan;
- alur ujung ke ujung (buat → ajukan → AI → override → finalkan → revisi → riwayat);
- **tidak ada koneksi keluar** selama review.

`make cek-offline` memeriksa jaringan kontainer yang sedang berjalan. Build frontend juga gagal bila ada aset dari domain luar.

## Struktur folder

```
backend/            FastAPI (api), worker AI, migrasi, pengujian
  app/api/          endpoint REST per modul
  app/pekerja/      worker: ekstraksi PDF, pencarian hibrida, LLM, verifikasi rujukan, pipeline review
  app/nilai_final.py  aturan label & nilai final (satu sumber kebenaran)
  app/status.py     transisi status revisi
  migrasi/          revisi skema Alembic
  tests/            pengujian otomatis
frontend/           React + TypeScript + Tailwind, PDF.js dibundel
docs/               arsitektur, API, instalasi offline, panduan pengguna & admin, asumsi
scripts/            doctor, backup/restore, bundle offline, cek-offline
contoh/             PDF contoh TOR/RAB/Panduan
docker-compose*.yml komposisi dasar + gpu + dev + prod + node-ai
.env.*              konfigurasi per skenario (tiruan, dev, prod, node-ai)
```

## Dokumentasi

- [Arsitektur & alur AI](docs/arsitektur.md)
- [API](docs/api.md)
- [Instalasi offline & node GPU](docs/instalasi-offline.md)
- [Panduan pengguna](docs/panduan-pengguna.md)
- [Panduan administrasi](docs/panduan-admin.md)
- [Daftar asumsi](docs/asumsi.md)
