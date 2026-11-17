# Dokumentasi API

- **Basis URL**: `/api`, dilayani lewat `web`.
- **Skema lengkap**: OpenAPI di `GET /api/openapi.json`. Swagger UI dimatikan karena memuat aset dari CDN (B1).
- **Autentikasi**: cookie `sesi` (HttpOnly, SameSite=Strict) dari `POST /api/auth/login`.
- **CSRF**: setiap metode selain GET wajib membawa header `X-CSRF-Token` berisi nilai `csrf` dari respons login atau `GET /api/auth/saya`.
- **Error**: `{"pesan": "…"}` dengan status 400 (data tidak valid), 401 (belum login), 403 (tidak berhak), 404, 409 (status tidak mengizinkan), 413 (file terlalu besar), 422 (field kurang), 429 (terlalu banyak percobaan login), 500 (`{"pesan", "trace_id"}`). Setiap respons membawa header `X-Trace-Id`.

Hak akses selalu dicek di backend:

- **Pengusul** hanya dapat mengakses usulan Satker-nya.
- **Reviewer** dapat mengakses seluruh usulan serta mengelola Panduan, Checklist, Kategori, Satuan Kerja, dan Master RO.
- **Admin** hanya mengelola Pengguna, Node AI, dan Audit Log; Dashboard dan Usulan (termasuk file TOR/RAB) ditolak.
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
| POST | `/usulan/{id}/arsip` | Pengusul Satker | `{arsip: bool}` |
| GET | `/usulan/{id}/riwayat` | login + Satker | `{usulan, revisi[] (+review[]), perbandingan{kolom, baris}}` |
| GET | `/usulan/opsi/filter` | Pengusul, Reviewer | Pilihan dropdown filter |

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
| GET | `/checklist` | Reviewer, Pengusul | Isi terbaru `{item: [{id, urutan, kode, judul, kriteria, berlaku_untuk, aktif, diubah_oleh, diubah_at}]}` |
| POST | `/checklist/item` | Reviewer | Tambah item `{kode, judul, kriteria, berlaku_untuk: TOR\|RAB\|TOR & RAB, aktif?}` (disimpan ke kolom `checklist`). `kode` wajib, maks. 50 karakter, dijadikan kapital, unik → 400 bila bentrok; `judul` maks. 500 karakter |
| PUT | `/checklist/item/{id}` | Reviewer | Ubah item (isian sama, kode boleh diganti). Isi baru dicatat ke `checklist_histori` (terhubung lewat `checklist_id`). 400 bila tidak ada item aktif tersisa; 404 item tidak ada |
| DELETE | `/checklist/item/{id}` | Reviewer | Hapus item beserta riwayatnya secara permanen (ikut hilang dari tampilan review lama) |
| PUT | `/checklist/urutan` | Reviewer | Atur urutan `{id: [semua id item sesuai urutan baru]}` → `no_urut` 1..n (tidak membuat riwayat). 400 bila daftar tidak memuat tepat semua item |
| GET | `/checklist/item/{id}/riwayat` | Reviewer, Pengusul | Semua versi item dari `checklist_histori`, terbaru dulu (baris pertama = isi saat ini; format sama dengan item `/checklist`) |
| GET | `/kategori` | Reviewer, Pengusul (lihat saja) | Isi terbaru `{item: [{id, kode, nama, definisi, aktif, diubah_oleh, diubah_at}]}`, urut `no_urut` yang diatur Reviewer |
| POST | `/kategori` | Reviewer | Tambah `{kode, nama, definisi, aktif?}` (bawaan Aktif), ditaruh setelah kategori berkode sebelumnya. `kode` wajib, maks. 20 karakter, dijadikan kapital, unik → 400 bila bentrok; `nama` maks. 255 karakter |
| PUT | `/kategori/urutan` | Reviewer | Atur urutan `{id: [semua id kategori sesuai urutan baru]}` → `no_urut` 1..n (tidak membuat riwayat). 400 bila daftar tidak memuat tepat semua kategori |
| PUT | `/kategori/{id}` | Reviewer | Ubah kategori (isian sama, kode boleh diganti). Isi **sebelum** diubah disalin ke `kategori_histori`; tanpa perubahan = tidak menambah riwayat. 400 bila menonaktifkan kategori Aktif terakhir; 404 kategori tidak ada |
| DELETE | `/kategori/{id}` | Reviewer | Hapus kategori beserta riwayatnya secara permanen; review lama tidak berubah (salinan di `review_kategori`). 400 bila tidak ada kategori Aktif tersisa |
| GET | `/kategori/{id}/riwayat` | Reviewer, Pengusul (lihat saja) | Versi sebelum tiap perubahan dari `kategori_histori`, terbaru dulu (isi saat ini tidak termasuk; kosong bila belum pernah diubah) |

## Panduan (Modul D)

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/panduan` | Reviewer, Pengusul | Daftar panduan yang tidak dihapus + versi + `status_proses` (BELUM/DIPROSES/SIAP/GAGAL), urut `urutan` (no_urut) |
| PUT | `/panduan/urutan` | Reviewer | `{id: [semua id panduan sesuai urutan baru]}`. Hanya urutan yang berubah (tanpa versi baru, Diinput Oleh/Tanggal Input tetap). Panduan baru ditaruh di akhir; setelah hapus, urutan dirapatkan. 400 bila daftar tidak memuat tepat semua panduan |
| POST | `/panduan` | Reviewer | multipart `file, judul, deskripsi?, aktif?` (default `true`) |
| PUT | `/panduan/{id}` | Reviewer | multipart `judul, deskripsi?, aktif?`. Ubah nama/deskripsi/status → versi panduan baru; file tidak dapat diganti (unggah panduan baru) (status dicatat per versi) (Nonaktif = tidak dipakai review berikutnya). Tanpa perubahan = tidak membuat versi |
| DELETE | `/panduan/{id}` | Reviewer | Hapus **permanen**: panduan, semua versi, dan file + ekstraksinya (bila tidak dipakai data lain). Review lama kehilangan catatan & rujukan panduan ini. 409 bila dipakai review yang berjalan / file sedang diproses |
| POST | `/panduan/{id}/proses-ulang` | Reviewer | Ulangi pemrosesan yang GAGAL |

## Master RO

Data berjenjang Program → Kegiatan → KRO → RO. Di database berupa satu tabel datar `master_ro` seperti `satker` (`kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro, kode_ro, ro, aktif`); API menyajikannya per data (`tingkat` = jenjang terdalam yang terisi, `induk_id` = id baris induk). Khusus **Reviewer** (403 untuk role lain).

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/master-ro` | Reviewer | Semua baris `[{id, tingkat (PROGRAM\|KEGIATAN\|KRO\|RO), kode, kode_lengkap, nama, aktif, kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro, kode_ro, ro, induk_id, induk{kode, nama}, jumlah_turunan, dibuat_oleh, dibuat_at, diubah_oleh, diubah_at}]` (`kode_program` … `ro` = kolom datar tabel, kosong untuk jenjang di bawah data itu; `kode_lengkap` = kode Program sampai baris itu dipisah titik, mis. `WA.1234.EBA.994`), urut data yang paling baru ditambahkan (`dibuat_at`) paling atas; data yang dibuat bersamaan (seed/satu kali impor) urut berjenjang: Program diikuti Kegiatan-nya, lalu KRO, lalu RO |
| POST | `/master-ro` | Reviewer | `{tingkat, induk_id?, kode, nama, aktif?}`. `induk_id` wajib kecuali Program dan harus tingkat tepat di atasnya serta Aktif. `kode` wajib, teks bebas maks. 50 karakter (disimpan apa adanya, tanpa batasan huruf/angka), unik di antara saudara (tingkat + induk sama); `nama` wajib, maks. 255 karakter; nama Program diawali "Program"; nama RO unik dalam satu KRO (tanpa membedakan huruf besar/kecil). 400 bila tidak valid / bentrok |
| GET | `/master-ro/referensi-kro` | Reviewer | Daftar KRO Lampiran II SEB No. 6/2025 untuk saran di form: `[{kode, nama, satuan, pn}]` (kode PN menjadi baris sendiri, `pn=true`), urut kode |
| POST | `/master-ro/impor` | Reviewer | Multipart `file` (.xlsx, maks. 5 MB, maks. 5000 baris data; file dibaca bertahap dan hanya sampai baris ke-50.000 termasuk baris kosong serta 100 kolom pertama, agar file terkompresi berisi jutaan baris tidak menghabiskan memori server). Lembar pertama; baris pertama yang tidak kosong = judul kolom `kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro, kode_ro, ro` (urutan bebas). Tiap baris = satu data beserta induknya; jenjang yang belum ada dibuat (Aktif, aturan sama dengan POST `/master-ro`), yang sudah ada dipakai (nama harus sama). Isi sel disimpan apa adanya (kode teks bebas; sel angka `1` tersimpan `1`, jadi kode seperti `001` ditulis sebagai teks di Excel). Semua-atau-tidak: ada baris salah → 400 berisi daftar kesalahan per nomor baris Excel, tidak ada yang tersimpan. Output `{baris, dibuat: {PROGRAM, KEGIATAN, KRO, RO}, total_dibuat, sudah_ada}`. 400 file bukan .xlsx / kolom kurang / tanpa data; 409 data berubah bersamaan; 413 file terlalu besar |
| PUT | `/master-ro/{id}` | Reviewer | Isian sama; `tingkat` tidak dapat diubah (400). Perubahan kode/nama/induk ikut diterapkan ke semua baris turunannya. Induk Nonaktif yang sudah dipakai boleh dipertahankan. Tanpa perubahan = jejak tidak berubah. 404 bila tidak ada |
| DELETE | `/master-ro/{id}` | Reviewer | Hapus permanen. 409 bila masih punya turunan; 404 bila tidak ada |

Setiap tambah/ubah/hapus tercatat di audit log (`MASTER_RO_TAMBAH`, `MASTER_RO_UBAH`, `MASTER_RO_HAPUS`).

## File, Dashboard, Administrasi

| Metode | Path | Role | Keterangan |
| --- | --- | --- | --- |
| GET | `/file/{file_id}` | login + hak | PDF inline. Panduan: Reviewer & Pengusul (sama dengan `GET /panduan`; Admin 404). TOR/RAB: sesuai hak usulan. 404 bila tidak berhak |
| GET | `/internal/file/{sha}` | token node | `Authorization: Bearer <token node>`; untuk node AI jarak jauh |
| GET | `/dashboard` | Pengusul, Reviewer | `per_status, per_kategori, per_satker, perlu_tindakan[]`, + `antrean` bila pengguna juga ber-role Admin |
| GET/POST | `/pengguna` | Admin | `{username, roles[], satker_id?, aktif, password}` (tanpa nama; nama tampilan = username) |
| PUT | `/pengguna/{id}` | Admin | Ubah; `password` diisi = reset (sesi dicabut) |
| DELETE | `/pengguna/{id}` | Admin | Hapus permanen. 400 untuk akun sendiri; 409 bila sudah punya riwayat (usulan, review, audit log, …) — nonaktifkan saja |
| GET | `/satker` | Reviewer, Admin | Daftar Satker (+ jejak dibuat/diubah). Admin memakainya untuk memilih Satker di form Pengguna |
| GET | `/satker/referensi` | Reviewer | Daftar resmi UKE I/UKE II dari dokumen "Data Satker dan Unit Kerja" `{kode_uke1, unit_kerja, kode_uke2, nama}[]` — sumber pilihan form Satker |
| POST/PUT | `/satker`, `/satker/{id}` | Reviewer | `{kode_uke1?, unit_kerja? (UKE I / Eselon I), kode_uke2?, nama? (UKE II / Eselon II), aktif}` — semua opsional, kosong disimpan `""`. `kode_uke1` = `NN`, `kode_uke2` = `NN.NN` diawali `kode_uke1` (400 bila salah); `aktif=false` = nonaktifkan (tidak bisa dipilih pengguna). 409 bila `kode_uke2`/`kode_uke1` sudah dipakai, atau Unit Kerja sudah ada. Respons + `dibuat_oleh, dibuat_at, diubah_oleh, diubah_at`. 400 isian terlalu panjang; 409 Satuan Kerja sama dalam satu Unit Kerja |
| DELETE | `/satker/{id}` | Reviewer | Hapus permanen. 409 bila masih dipakai pengguna atau usulan |
| GET/POST | `/node-ai` | Admin | POST `{nama}` → `{token}` (sekali tampil) |
| POST | `/node-ai/{id}/cabut` | Admin | Cabut akses node |
| GET | `/audit` | Admin | Filter `pengguna_id, aksi, entitas, dari, sampai, halaman` |
