# AIREN — Asisten AI Offline untuk Review TOR & RAB

Aplikasi web untuk mereview dokumen TOR & RAB usulan anggaran dengan AI lokal:

- **Screening 1**: menilai pemenuhan setiap item checklist, dengan bukti (halaman, lokasi, kutipan) dari TOR/RAB dan Panduan. Label LOLOS/TIDAK LOLOS **dihitung oleh kode**.
- **Screening 2**: merekomendasikan kategori K1–K4 berdasarkan definisi kategori Aktif terbaru saat review dimulai.
- **Reviewer** memverifikasi, meng-override (dengan alasan), lalu memfinalkan. Pengusul mengunggah revisi hingga LOLOS.
- **Panduan** (PDF acuan AI): Admin mengunggah satu PDF per form dengan Nama Acuan (maks. 500 karakter), Deskripsi, dan Status Aktif/Nonaktif; PDF dapat **dipratinjau** sebelum diunggah dan tombol **Reset** mengosongkan form. Hanya panduan **Aktif** yang sudah **Siap** dipakai review. Setiap edit (nama, deskripsi, status) tercatat di **Panduan Histori**. **Hapus bersifat permanen** setelah konfirmasi: panduan, histori, file PDF beserta hasil pemrosesannya, dan rujukannya di hasil review lama ikut terhapus dari database (PDF yang sama yang masih dipakai panduan lain atau TOR/RAB tetap disimpan; jejaknya tetap ada di audit log). Untuk sekadar berhenti memakai panduan, ubah statusnya menjadi Nonaktif.
- **Kategori** (acuan Screening 2): Admin mengelola kategori satu per satu dalam tabel Kode, Kategori, Status, Deskripsi. **Tambah** dan **Edit** di halaman form (Kode unik maks. 20 karakter, Kategori maks. 255 karakter, Deskripsi; Edit juga mengatur Status Aktif/Nonaktif) dengan pop-up periksa kembali. Isi sebelum tiap edit tercatat di **Kategori Histori** (halaman Detail). **Hapus bersifat permanen** beserta historinya; minimal satu kategori Aktif harus ada. Hanya kategori Aktif yang dipakai review berikutnya. Setiap review menyimpan salinan kategori yang dipakai, sehingga hasil review lama tidak berubah dan definisinya dapat dilihat di hasil review ("Lihat kategori yang dipakai").

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

`make setup` adalah satu-satunya langkah yang membutuhkan internet (build image + unduh model). Setelah itu aplikasi berjalan tanpa internet. Saat `make up`, migrasi database dan seed (4 kategori sesuai PRD C1 + admin) berjalan otomatis. Database yang dibuat sebelum 22 Oktober 2026 tidak dapat di-upgrade dan harus dibuat ulang (lihat `docs/asumsi.md`).

> Karena hapus panduan bersifat permanen, jalankan `make backup` secara berkala di production.

### Memperbarui aplikasi yang sudah berjalan

1. `make backup` (wajib di production).
2. Tarik kode terbaru, lalu:
   - **Dev & tiruan** (kode di-mount): `make up`, lalu `docker compose restart worker`. `api` memuat ulang kode otomatis, `worker` tidak.
   - **Production** (kode di dalam image): bangun ulang image (`make setup`, atau `make bundle` + `make install-offline` untuk server tanpa internet), lalu `make up`.

   Migrasi skema berjalan otomatis setiap `make up`, sebelum `api` dan `worker` menyala.

Catatan untuk pembaruan menu Panduan & Kategori (Oktober 2026):

- Skema database kini dibuat langsung dari model; migrasi lama (`0002`–`0013`) dihapus. Database yang dibuat **sebelum 22 Oktober 2026 tidak dapat di-upgrade**. Buat ulang dengan `docker compose down -v` (hanya menghapus volume database `pgdata`; file di `./data` tetap) lalu `make up`. Data usulan dan review di database lama ikut hilang, dan backup lama tidak dapat dipulihkan ke kode ini.
- Database yang dibuat **sejak 22 Oktober 2026** (kategori masih berupa versi daftar) dinaikkan **otomatis** saat `make up` oleh revisi `0002_kategori_per_kategori`: kategori dari versi aktif terakhir (semuanya Aktif), salinan kategori tiap review, dan id yang sama sehingga hasil review lama tetap cocok. Riwayat versi daftar lama tidak dipindah ke Kategori Histori.
- Nama tabel & kolom berubah: panduan (`panduan_versi` → `panduan_histori`, `judul` → `panduan`, dll.; [desain.md](desain.md) §7 no. 17–19) dan kategori (`kategori_versi`/`kategori_item` → `kategori` + `kategori_histori` + `review_kategori`, `nama` → `kategori`, `definisi` → `deskripsi`; §7 no. 23–25). Query atau laporan SQL buatan sendiri yang memakai nama lama perlu disesuaikan.
- API panduan tidak berubah. API kategori berubah: `GET /api/kategori` mengembalikan daftar kategori terbaru, endpoint versi kategori diganti tambah/ubah/hapus per kategori dan `/api/kategori/{id}/riwayat` (lihat [docs/api.md](docs/api.md)).

### Mengakses database (dev & tiruan)

- **Terminal:** `docker compose exec db psql -U airen -d airen` (`\dt` daftar tabel, `\q` keluar).
- **GUI** (DBeaver, pgAdmin, ekstensi VS Code): host `127.0.0.1`, port `5433`, database/user/password `airen`. Hanya dapat diakses dari laptop itu sendiri, lewat layanan penerus `db-gui`. Kontainer `db` tetap tanpa jalur ke internet. Production tidak membuka port database.
- **Tabel panduan:**
  - `panduan` = data terkini: `id`, `created_by`/`created_date` (pengunggah & waktu unggah pertama), `updated_by`/`updated_date` (penginput & waktu versi terkini), `panduan` (Nama Acuan), `aktif`, `file_id`, `nama_file`, `deskripsi`.
  - `panduan_histori` = riwayat saja (Panduan Histori): salinan utuh baris `panduan` sebelum tiap perubahan, ditambah `panduan_id`; tidak pernah diubah.
  - Nomor versi tidak disimpan: histori ke-n menurut `updated_date` = versi n, versi terkini = jumlah histori + 1.
  - `review_panduan` = salinan panduan + nomor versi (`nomor`) yang dipakai tiap review.
- **Tabel kategori:**
  - `kategori` = data terkini: `id`, `created_by`/`created_date` (pembuat & waktu dibuat), `updated_by`/`updated_date` (penginput & waktu versi terkini), `aktif` (Nonaktif = tidak dipakai review berikutnya), `kode`, `kategori` (nama), `deskripsi` (definisi yang dipakai AI).
  - `kategori_histori` = riwayat saja (Kategori Histori): salinan utuh baris kategori sebelum tiap perubahan (`created_by`/`created_date` = pembuat & waktu kategori dibuat, `updated_by`/`updated_date` = penginput & waktu versi itu), ditambah `kategori_id`; ikut terhapus bila kategorinya dihapus.
  - `review_kategori` = salinan kategori Aktif (`kode`, `nama`, `definisi`) yang dipakai tiap review; tidak berubah walau kategori diedit atau dihapus.
  - Field API tetap memakai `nama` dan `definisi`.

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
- versioning checklist/kategori/panduan, status Aktif/Nonaktif panduan dan kategori, hapus panduan permanen, serta CRUD, riwayat, dan hapus permanen kategori tanpa mengubah review lama;
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
