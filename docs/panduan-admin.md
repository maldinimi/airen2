# Panduan Administrasi

## Operasional harian

| Kebutuhan | Perintah |
| --- | --- |
| Status layanan | `make status` |
| Log semua layanan | `make logs` (atau `docker compose logs -f worker`) |
| Restart | `make restart` |
| Pemeriksaan prasyarat | `make doctor` |
| Verifikasi offline | `make cek-offline` |

Log teknis (JSON per baris, rotasi 50 MB × 10) tersimpan di `data/logs/`:

- `api.log`: setiap request (metode, path, status, durasi, `trace_id`, `pengguna_id`);
- `worker.log`: setiap tahap review (ekstraksi, item, panggilan LLM beserta durasi & jumlah token, penyebab error);
- `migrasi.log`.

**Menelusuri review bermasalah**: Pengusul melihat pesan dengan *ID pelacakan* (trace_id). Cari dengan:

```bash
grep "<trace_id>" data/logs/worker.log
```

Hasilnya menampilkan seluruh perjalanan review dari pengajuan hingga gagal/selesai, termasuk detail teknis error.

## Backup & restore

```bash
make backup
```

Perintah ini membuat `backup/<waktu>/database.dump` (pg_dump format custom) dan `files.tar.gz` (seluruh PDF). Jadwalkan via cron, mis. setiap malam:

```bash
0 1 * * * cd /opt/airen && make backup
```

Lalu salin folder `backup/` ke media terpisah. Model AI tidak perlu dibackup; dapat diunduh ulang atau diambil dari paket offline.

Restore (menimpa data saat ini; diminta konfirmasi "YA"):

```bash
make restore FILE=backup/20261012-010000
```

## Mengganti model AI

1. Ubah `LLM_MODEL` di `.env` node AI (atau `.env.dev`). Contoh: `Qwen/Qwen3-VL-32B-Thinking-FP8` bila cache GPU kurang. Sesuaikan juga `LLM_KONTEKS`, `LLM_GPU_UTIL`, `LLM_MAKS_PARALEL`, dan `LLM_MAKS_TOKEN` bila perlu.
2. Jalankan `make setup-ai` (atau `make setup` di dev) untuk mengunduh model; ini membutuhkan internet. Untuk server tanpa internet, gunakan `make bundle`.
3. Jalankan `make up-ai` / `make up`.

Nama model dan versi prompt tercatat di setiap review (`model_info`). Model termasuk dalam fingerprint, sehingga hasil model lama tidak disalin ke review dengan model baru. Hasil dari model non-production ditandai lencana "Model development" di halaman review.

Model embedding/reranker (`EMBEDDING_MODEL`, `RERANKER_MODEL`) juga dapat diganti dengan cara yang sama. **Setelah mengganti model embedding**, embedding lama tidak cocok lagi; hapus hasil ekstraksi agar diproses ulang:

```bash
docker compose exec db psql -U airen -c "UPDATE file SET status_ekstraksi='BELUM'; DELETE FROM chunk;"
```

Panduan perlu diproses ulang (unggah ulang atau "Proses ulang"). TOR/RAB diproses ulang otomatis saat review berikutnya.

## Mengubah prompt

Prompt berada di `backend/app/pekerja/prompt.py`. **Naikkan `PROMPT_VERSI`** setiap kali prompt atau skema berubah, agar hasil lama tidak disalin (fingerprint).

## Perubahan skema database

1. Ubah model di `backend/app/model.py`.
2. Buat revisi Alembic:

```bash
docker compose run --rm api python -m app.migrasi revisi "tambah kolom x"
```

3. Periksa file baru di `backend/migrasi/versions/`. Migrasi berjalan otomatis saat `make up`.

## Kapasitas GPU

- **Dashboard Admin** menampilkan antrean, node aktif, rata-rata menit per review, dan perkiraan waktu selesai.
- **Menambah node**: lihat docs/instalasi-offline.md §4. Tidak ada perubahan kode.
- **Paralelisme dalam satu node**: `ITEM_PARALEL` (item dinilai bersamaan) dan `LLM_MAKS_PARALEL` (batch vLLM).

## Troubleshooting

| Gejala | Penyebab umum | Tindakan |
| --- | --- | --- |
| Status "Menunggu kapasitas AI" terus | Tidak ada worker/node aktif | `make status`; di node: `make up-ai`; periksa WireGuard (`wg show`) dan token node (menu Node AI) |
| Review GAGAL "Gagal memproses file" | PDF rusak/aneh, atau OCR gagal | Lihat `worker.log` dengan trace_id. Minta Pengusul mengunggah PDF lain (cetak ulang ke PDF) lalu Ajukan Ulang |
| Review GAGAL "LLM tidak memberikan jawaban valid" | vLLM mati/kehabisan memori, keluaran terpotong | `docker compose logs llm`. Naikkan `LLM_MAKS_TOKEN` atau turunkan `LLM_MAKS_PARALEL`/`ITEM_PARALEL` |
| `llm` tidak pernah sehat | Model belum diunduh / VRAM kurang | `make doctor`; `make setup`; turunkan `LLM_GPU_UTIL` atau `LLM_KONTEKS` |
| Ekstraksi/embedding lambat di worker GPU | Driver NVIDIA host lebih lama dari yang dibutuhkan PyTorch di image (CUDA 13 → driver ≥580); worker jatuh ke CPU | Perbarui driver NVIDIA host; cek `docker compose exec worker python -c "import torch;print(torch.cuda.is_available())"` |
| Panduan status Gagal | PDF terenkripsi/rusak | Lihat pesan di bawah nama panduan pada tabel; perbaiki PDF-nya, unggah sebagai panduan baru, lalu nonaktifkan atau hapus yang lama (file tidak dapat diganti lewat Edit) |
| Login "Terlalu banyak percobaan" | ≥5 gagal dalam 15 menit dari username/IP | Tunggu 15 menit, atau reset password oleh Admin |
| Admin lupa password | — | `docker compose exec api python -c "from app.db import SessionLokal; from app.model import Pengguna; from app.keamanan import hash_password; db=SessionLokal(); p=db.query(Pengguna).filter_by(username='admin').one(); p.password_hash=hash_password('PasswordBaru!1'); db.commit()"` |
| Port 8080 dipakai | Program lain | Ubah `PORT_WEB` di `.env` |
| Windows: perubahan kode tidak ter-reload | Bind mount | Vite memakai polling; untuk backend restart `docker compose restart api worker` |
