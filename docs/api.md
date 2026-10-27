# Dokumentasi API

- **Basis URL**: `/api`, dilayani lewat `web`.
- **Skema lengkap**: OpenAPI di `GET /api/openapi.json`. Swagger UI dimatikan karena memuat aset dari CDN (B1).
- **Autentikasi**: cookie `sesi` (HttpOnly, SameSite=Strict) dari `POST /api/auth/login`.
- **CSRF**: setiap metode selain GET wajib membawa header `X-CSRF-Token` berisi nilai `csrf` dari respons login atau `GET /api/auth/saya`.
- **Error**: `{"pesan": "…"}` dengan status 400 (data tidak valid), 401 (belum login), 403 (tidak berhak), 404, 409 (status tidak mengizinkan), 413 (file terlalu besar), 422 (field kurang), 429 (terlalu banyak percobaan login), 500 (`{"pesan", "trace_id"}`). Setiap respons membawa header `X-Trace-Id`.

Hak akses selalu dicek di backend:

- **Pengusul** hanya dapat mengakses usulan Satker-nya.
- **Reviewer** dan **Admin** dapat mengakses seluruh usulan.
- **Unduhan file** diperiksa per file.

## Auth

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| POST | `/auth/login` | publik | `{username, password}` → profil + `csrf`; 429 bila ≥5 gagal/15 menit |
| POST | `/auth/logout` | login | Hapus sesi |
| GET | `/auth/saya` | login | Profil + `csrf` |
| POST | `/auth/ganti-password` | login | `{password_lama, password_baru}` |

## Usulan (Modul A)

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/usulan` | login | Filter: `satker_id, tahun, status, kategori, q, arsip, halaman, per_halaman`. Respons `{total, data: BarisUsulan[]}` |
| POST | `/usulan` | Pengusul | multipart: `tahun_anggaran, kode_ro, nama_ro, tor(PDF), rab(PDF), ajukan(bool)` |
| GET | `/usulan/{id}` | login + Satker | Satu `BarisUsulan` |
| PUT | `/usulan/{id}/draf` | Pengusul Satker | multipart opsional `tahun_anggaran, kode_ro, nama_ro, tor, rab, ajukan`; hanya status DRAF/GAGAL |
| POST | `/usulan/{id}/revisi` | Pengusul Satker | multipart `tor` dan/atau `rab`, `ajukan`; hanya setelah TIDAK LOLOS |
| POST | `/usulan/{id}/ajukan` | Pengusul Satker | Ajukan review revisi terbaru (DRAF atau ulang setelah GAGAL) |
| DELETE | `/usulan/{id}` | Pengusul Satker | Hanya bila belum pernah diajukan review (409 bila pernah) |
| POST | `/usulan/{id}/arsip` | Pengusul Satker / Admin | `{arsip: bool}` |
| GET | `/usulan/{id}/riwayat` | login + Satker | `{usulan, revisi[] (+review[]), perbandingan{kolom, baris}}` |
| GET | `/usulan/opsi/filter` | login | Pilihan dropdown filter |

`BarisUsulan` berisi:

- identitas: `id, satker, tahun_anggaran, kode_ro, nama_ro`;
- revisi terbaru: `revisi_id, revisi_nomor, status`, dokumen `tor{file_id,nama}`, `rab{…}`;
- hasil: `kategori_final{kode,nama}`, `checklist{terpenuhi,total,item[],final}`;
- proses: `proses{status, progres, posisi_antrean, menunggu_kapasitas, error_pesan, trace_id}`;
- status lain: `updated_at, diarsipkan, pernah_direview, review_id, boleh_kelola`.

## Review (Modul E)

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/review/{id}` | login + Satker | Detail review; Pengusul tidak melihat override/catatan sebelum final |
| GET | `/revisi/{id}/review` | login + Satker | Review terbaru suatu revisi |
| POST | `/review/{id}/override` | Reviewer | `{target: ITEM\|LABEL\|KATEGORI, checklist_item_id?, nilai, alasan}`. Nilai: `TERPENUHI/TIDAK_TERPENUHI`, `LOLOS/TIDAK_LOLOS`, atau id kategori dari `kategori.pilihan` review tersebut |
| POST | `/override/{id}/batal` | Reviewer | Batalkan override (sebelum final) |
| PUT | `/review/{id}/catatan` | Reviewer | `{dokumen: TOR\|RAB\|UMUM, teks}`; teks kosong = hapus |
| POST | `/review/{id}/finalkan` | Reviewer | Kunci hasil, salin nilai final, ubah status revisi |

Detail review berisi:

- **status**: `status, final, tampilan (reviewer|pengusul), boleh_override, proses, model_info`;
- **acuan**: `acuan{checklist{jumlah_item}, kategori{jumlah}, panduan[{judul, nomor, file_id, nama_file}]}`;
- **hasil**:
  - `label{ai, hitung, final, diubah, tidak_konsisten, terpenuhi, total, override}`;
  - `kategori{ai, final, alasan, rujukan[], pilihan[], override}`; `ai`, `final`, dan `pilihan[]` berbentuk `{id, kode, nama, definisi}` dari salinan kategori Aktif saat review dimulai (C3);
  - `item[]{kode, judul, kriteria, ai_terpenuhi, terpenuhi, diubah, override, ditemukan, alasan, yang_kurang, rujukan[]}`;
  - `rekomendasi{TOR[], RAB[]}`;
- **catatan reviewer**: `catatan[]`, `riwayat_override[]`.

Setiap `rujukan` berisi `{peran (bukti_dokumen|dasar_panduan), dokumen (TOR|RAB|PANDUAN), judul_dokumen, file_id, halaman, label_lokasi, kutipan, bbox[x0,y0,x1,y1], sumber (teks|ocr|vlm)}`.

## Checklist & Kategori (Modul B, C)

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/checklist` | login | Isi terbaru `{item: [{id, urutan, kode, judul, kriteria, berlaku_untuk, aktif, diubah_oleh, diubah_at}]}` |
| POST | `/checklist/item` | Admin | Tambah item `{kode, judul, kriteria, berlaku_untuk: TOR\|RAB\|TOR & RAB, aktif?}` (disimpan ke kolom `checklist`). `kode` wajib, maks. 50 karakter, dijadikan kapital, unik → 400 bila bentrok; `judul` maks. 500 karakter |
| PUT | `/checklist/item/{id}` | Admin | Ubah item (isian sama, kode boleh diganti). Isi baru dicatat ke `checklist_histori` (terhubung lewat `checklist_id`). 400 bila tidak ada item aktif tersisa; 404 item tidak ada |
| DELETE | `/checklist/item/{id}` | Admin | Hapus item beserta riwayatnya secara permanen (ikut hilang dari tampilan review lama) |
| PUT | `/checklist/urutan` | Admin | Atur urutan `{id: [semua id item sesuai urutan baru]}` → `no_urut` 1..n (tidak membuat riwayat). 400 bila daftar tidak memuat tepat semua item |
| GET | `/checklist/item/{id}/riwayat` | login | Semua versi item dari `checklist_histori`, terbaru dulu (baris pertama = isi saat ini; format sama dengan item `/checklist`) |
| GET | `/kategori` | Admin | Isi terbaru `{item: [{id, kode, nama, definisi, aktif, diubah_oleh, diubah_at}]}`, urut `no_urut` yang diatur Admin |
| POST | `/kategori` | Admin | Tambah `{kode, nama, definisi, aktif?}` (bawaan Aktif), ditaruh setelah kategori berkode sebelumnya. `kode` wajib, maks. 20 karakter, dijadikan kapital, unik → 400 bila bentrok; `nama` maks. 255 karakter |
| PUT | `/kategori/urutan` | Admin | Atur urutan `{id: [semua id kategori sesuai urutan baru]}` → `no_urut` 1..n (tidak membuat riwayat). 400 bila daftar tidak memuat tepat semua kategori |
| PUT | `/kategori/{id}` | Admin | Ubah kategori (isian sama, kode boleh diganti). Isi **sebelum** diubah disalin ke `kategori_histori`; tanpa perubahan = tidak menambah riwayat. 400 bila menonaktifkan kategori Aktif terakhir; 404 kategori tidak ada |
| DELETE | `/kategori/{id}` | Admin | Hapus kategori beserta riwayatnya secara permanen; review lama tidak berubah (salinan di `review_kategori`). 400 bila tidak ada kategori Aktif tersisa |
| GET | `/kategori/{id}/riwayat` | Admin | Versi sebelum tiap perubahan dari `kategori_histori`, terbaru dulu (isi saat ini tidak termasuk; kosong bila belum pernah diubah) |

## Panduan (Modul D)

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/panduan` | login | Daftar panduan yang tidak dihapus + versi + `status_proses` (BELUM/DIPROSES/SIAP/GAGAL) |
| POST | `/panduan` | Admin | multipart `file, judul, deskripsi?, aktif?` (default `true`) |
| PUT | `/panduan/{id}` | Admin | multipart `judul, deskripsi?, aktif?`. Ubah nama/deskripsi/status → versi panduan baru; file tidak dapat diganti (unggah panduan baru) (status dicatat per versi) (Nonaktif = tidak dipakai review berikutnya). Tanpa perubahan = tidak membuat versi |
| DELETE | `/panduan/{id}` | Admin | Hapus **permanen**: panduan, semua versi, dan file + ekstraksinya (bila tidak dipakai data lain). Review lama kehilangan catatan & rujukan panduan ini. 409 bila dipakai review yang berjalan / file sedang diproses |
| POST | `/panduan/{id}/proses-ulang` | Admin | Ulangi pemrosesan yang GAGAL |

## File, Dashboard, Administrasi

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/file/{file_id}` | login + hak | PDF inline. Panduan: semua pengguna. TOR/RAB: sesuai hak usulan. 404 bila tidak berhak |
| GET | `/internal/file/{sha}` | token node | `Authorization: Bearer <token node>`; untuk node AI jarak jauh |
| GET | `/dashboard` | login | `per_status, per_kategori, per_satker, perlu_tindakan[]`, + `antrean` untuk Admin |
| GET/POST | `/pengguna` | Admin | `{username, nama, roles[], satker_id?, aktif, password}` |
| PUT | `/pengguna/{id}` | Admin | Ubah; `password` diisi = reset (sesi dicabut) |
| GET | `/satker` | login | Daftar Satker |
| POST/PUT | `/satker`, `/satker/{id}` | Admin | `{kode, nama, aktif}` |
| GET/POST | `/node-ai` | Admin | POST `{nama}` → `{token}` (sekali tampil) |
| POST | `/node-ai/{id}/cabut` | Admin | Cabut akses node |
| GET | `/audit` | Admin | Filter `pengguna_id, aksi, entitas, dari, sampai, halaman` |
