# Usulan Desain — Asisten AI Offline untuk Review TOR & RAB

**Status:** Disetujui pemilik produk (2026-10-12) | **Versi:** 1 | **Mengacu:** prd.md v1 | **Tanggal:** 2026-10-12

Dokumen ini menjawab §12 langkah 1: arsitektur + alasan teknologi, desain database, dan alur logika AI. Belum ada kode.

---

## 1. Ringkasan Keputusan

| Area | Pilihan | Alasan singkat |
| --- | --- | --- |
| Frontend | React + TypeScript (Vite), Tailwind CSS + komponen shadcn/ui, PDF.js | Responsif (B5), komponen modern & aksesibel; PDF.js dibundel lokal → viewer + lompat halaman + sorot tanpa CDN (B1, E3). |
| Backend API | Python + FastAPI | Ekosistem AI/PDF ada di Python; satu bahasa untuk API dan pipeline AI → lebih mudah dipelihara. Dokumentasi API OpenAPI otomatis (§8.1). |
| Database | PostgreSQL + ekstensi pgvector | Satu database untuk data relasional, vektor pencarian, dan antrean job. Tidak perlu vector DB / Redis terpisah → lebih sedikit komponen, backup cukup satu `pg_dump`. |
| Antrean review | Tabel `job` di PostgreSQL (`SELECT … FOR UPDATE SKIP LOCKED`) + proses *worker* terpisah | Antrean di database cukup untuk ±50 pengguna, tahan restart, tidak menambah layanan, dan banyak worker (di banyak GPU/server) dapat mengambil job dari antrean yang sama tanpa koordinasi tambahan. |
| Penyimpanan file | Folder lokal (volume Docker), nama file = hash SHA-256 isi | File tidak pernah ditimpa → rujukan review lama tetap dapat dibuka selama filenya tidak dihapus (hapus panduan permanen, PRD v2 D6); file identik otomatis tidak terduplikasi. |
| Ekstraksi PDF | Docling (layout, tabel, urutan baca) + OCR lokal (RapidOCR/Tesseract `ind`) untuk halaman scan | Menghasilkan elemen per halaman **beserta koordinat (bbox)** → rujukan halaman presisi dan penyorotan di viewer (B3, E1, E3). |
| Model AI (penalaran + gambar) | **Satu model vision-language bermode *thinking*** keluarga Qwen3-VL (atau setara terbaru saat implementasi), disajikan dengan vLLM. **Dev:** 8B terkuantisasi 4-bit. **Prod:** 32B BF16. Rincian §2.1. | Satu model menangani penalaran (B2) sekaligus grafik/diagram/scan (B3) → hanya satu layanan model, lebih mudah dijalankan. Kuat berbahasa Indonesia (B6), lisensi terbuka, mendukung keluaran JSON terstruktur (*guided decoding*). Dev & prod satu keluarga model → perilaku & format keluaran sama, hanya akurasi berbeda. Model diganti lewat konfigurasi. |
| Embedding & reranker | BGE-M3 (dense + sparse) + bge-reranker-v2-m3 | Multibahasa, pencarian hibrida (makna + kata kunci) → pasal/ayat spesifik tidak terlewat. |
| Deployment | Docker Compose (semua komponen di kontainer, B7): `web`, `api`, `worker`, `llm` (vLLM), `db`. Satu file compose + file environment per skenario (`dev`/`prod`). | Satu perintah jalan di laptop, server kantor, maupun server GPU on demand. Docker Compose dipilih (bukan Kubernetes) karena skala ±50 pengguna tidak memerlukan orkestrator; kontainer yang sama dapat dipindah ke Kubernetes nanti bila perlu. Instal offline: image `docker save` + folder model. |
| Auth | Sesi cookie (HttpOnly, SameSite=Strict), password Argon2 | Sederhana dan aman untuk aplikasi intranet. |

Tidak ada fine-tuning pada versi pertama (§10): akurasi dikejar lewat ekstraksi yang baik, retrieval hibrida, penalaran per item, dan verifikasi rujukan. Fine-tuning dipertimbangkan hanya jika evaluasi menunjukkan kebutuhan.

---

## 2. Arsitektur Sistem

```
 Browser (desktop/tablet/ponsel)
        │ HTTPS (intranet)
        ▼
 ┌─────────────┐   REST/JSON    ┌──────────────────┐
 │ web (nginx  │ ─────────────▶ │ api (FastAPI)    │── auth, RBAC, CRUD, unduh file berizin
 │ + build SPA)│                └───────┬──────────┘
 └─────────────┘                        │ SQL
                                        ▼
                               ┌──────────────────┐
                               │ db (PostgreSQL   │  data + pgvector + tabel job + audit
                               │  + pgvector)     │
                               └───────┬──────────┘
                                       │ ambil job (SKIP LOCKED)
                                       ▼
 ┌───────────────┐  HTTP lokal  ┌──────────────────┐   ┌───────────────────┐
 │ llm (vLLM:    │ ◀─────────── │ worker (Python)  │ ─▶│ /data/files (SHA) │
 │ LLM + VLM)    │              │ ekstraksi, OCR,  │   │ /data/models      │
 └───────────────┘              │ embedding, review│   │ /data/logs        │
                                └──────────────────┘   └───────────────────┘
```

- Semua kontainer berada di jaringan Docker **internal tanpa gateway keluar** (`internal: true`); hanya `web` yang membuka port ke LAN. Ini sekaligus menjadi cara verifikasi B1. Satu-satunya pengecualian: terowongan terenkripsi ke node AI di GPU sewaan (§2.4).
- Telemetri dimatikan eksplisit (vLLM, HuggingFace `HF_HUB_OFFLINE=1`, dsb.). Font & aset frontend dibundel.
- `worker` memproses dua jenis job: **pemrosesan panduan** (D4) dan **review usulan** (Modul E). Antrean FIFO; posisi antrean ditampilkan ke pengguna.
- `worker` dan `llm` hanya berbicara lewat alamat yang dikonfigurasi (`LLM_URL`, `DATABASE_URL`). Karena itu keduanya dapat berjalan di mesin yang sama dengan aplikasi (dev) atau di server GPU terpisah (prod, §2.3).

### 2.1 Skenario Development & Production (PRD §8.2)

Basis kode, image kontainer, dan alur AI **sama**. Yang berbeda hanya isi file environment.

| | **Development** | **Production** |
| --- | --- | --- |
| Perangkat acuan | Laptop RTX A6000 Laptop **16 GB VRAM**, RAM ≥32 GB, disk kosong ≥100 GB. Windows (Docker Desktop + WSL2) atau Linux. | Node AI: GPU sewaan on demand **NVIDIA H100 NVL 94 GB** (cloud publik). Server aplikasi: milik instansi. Lihat §2.3. |
| Model | Qwen3-VL **8B** *Thinking*, terkuantisasi **4-bit (AWQ)** ±6 GB | Qwen3-VL **32B** *Thinking*, **BF16** (±66 GB) — presisi penuh tanpa kuantisasi, sesuai prioritas akurasi (B2) |
| Konteks maks. | 32k token (cukup karena penilaian per item, §4.2) | 64k token |
| Alokasi GPU | vLLM ±70% VRAM (model + cache), sisanya untuk embedding, reranker, dan model layout/OCR Docling | vLLM ±85% VRAM (model ±66 GB + cache ±14 GB); sisanya ±12 GB untuk embedding, reranker, dan Docling. Bila cache ternyata kurang untuk paralelisme yang dibutuhkan, beralih ke FP8 (didukung native oleh H100) cukup lewat `.env`. |
| Item dinilai paralel | 2 | 8–16 |
| Perkiraan waktu/usulan* | ±40–70 menit | ±10–20 menit |
| Akurasi | Cukup untuk menguji alur, format rujukan, dan UI. **Tidak** dipakai untuk menilai akurasi akhir. | Acuan akurasi (B2). |
| Pengguna | 1–3 developer | ±50 bersamaan |

\*TOR 50 hlm + RAB 10 hlm, checklist ±15 item. Perkiraan ini divalidasi saat uji beban.

**Mode tanpa GPU** (`AI_MODE=tiruan`): layanan `llm` tidak dijalankan; worker memakai jawaban AI tiruan yang tetap. Dipakai developer frontend/backend tanpa GPU dan untuk uji otomatis (CI).

Setiap review mencatat model & profil yang dipakai (`review.model_info`). Hasil dari model dev diberi badge "Model development" di UI agar tidak tertukar dengan hasil production.

### 2.2 Menjalankan aplikasi (B7: kemudahan adalah kunci)

Prasyarat di semua lingkungan hanya: **Docker + NVIDIA Container Toolkit** (untuk mode tanpa GPU cukup Docker).

```
cp .env.dev .env        # atau .env.prod / .env.tiruan
make setup              # sekali saja: unduh model sesuai .env ke ./data/models, build image
make up                 # jalankan semua layanan; buka http://localhost:8080
```

- `make` hanya pembungkus tipis `docker compose`; perintah compose aslinya ditulis di README untuk pengguna Windows tanpa `make`.
- `make setup` adalah satu-satunya langkah yang butuh internet. Setelah itu aplikasi berjalan sepenuhnya offline (B1). Untuk server tanpa internet: `make bundle` menghasilkan satu arsip (image + model) yang dibawa via disk, lalu `make install-offline` di server tujuan.
- Saat `make up`, layanan menunggu satu sama lain (*healthcheck*), migrasi database dan seed 4 kategori + akun admin awal berjalan otomatis.
- Mode dev: kode backend & frontend di-*mount* ke kontainer dengan *hot reload*, sehingga developer tidak perlu menginstal Python/Node di laptop.
- `make doctor` memeriksa prasyarat (Docker, GPU terdeteksi di kontainer, VRAM cukup untuk model di `.env`, model sudah terunduh, port bebas) dan memberi pesan perbaikan dalam Bahasa Indonesia.

### 2.3 Kapasitas ±50 pengguna & GPU on demand

**Bagian aplikasi (web, api, db)** ringan: 50 pengguna dengan polling progres tiap 5 detik ≈ 10 permintaan/detik. Cukup dengan `api` berisi 4–8 proses worker HTTP, *connection pool* database, dan file statis dilayani nginx. Server aplikasi: 8 core, 16–32 GB RAM, tanpa GPU.

**Bagian AI** adalah pembatasnya. Strategi:
1. **Paralel di dalam satu GPU:** item checklist dalam satu review dinilai bersamaan, dan beberapa review dapat berjalan bersamaan; vLLM menggabungkannya (*continuous batching*) sehingga GPU tetap penuh.
2. **Tambah GPU = tambah node AI:** satu "node AI" = kontainer `worker` + `llm` di satu server GPU. Node baru cukup dijalankan dengan `make up-ai` dan `DATABASE_URL` yang menunjuk ke database pusat; ia langsung mengambil job dari antrean yang sama. Tidak ada perubahan kode.
3. **GPU on demand:** bila tidak ada node AI yang aktif, job tetap aman di antrean dengan status "Menunggu kapasitas AI". Begitu server GPU dinyalakan, job diproses. Hasil antara tersimpan di database, sehingga bila node dimatikan di tengah proses, job dilanjutkan oleh node lain dari tahap terakhir.

| Production | Kapasitas perkiraan | 50 pengajuan selesai dalam |
| --- | --- | --- |
| 1 node AI: 1× H100 NVL 94 GB, ±16–32 vCPU, ±128 GB RAM, ±500 GB NVMe | ±4–6 usulan/jam | ±9–12 jam |
| 2 node AI | ±8–12 usulan/jam | ±4–6 jam |
| 3 node AI | ±12–18 usulan/jam | ±3–4 jam |

**Pola beban:** puncak ±50 pengajuan/hari, hanya pada momen tertentu (mis. menjelang tenggat usulan). Karena GPU disewa on demand:
- **Hari biasa:** 1 node, atau dinyalakan hanya saat ada antrean.
- **Momen puncak:** tambah node sementara (2–3 node) agar 50 pengajuan selesai dalam hari kerja yang sama, lalu matikan.
- Dashboard Admin menampilkan panjang antrean, perkiraan waktu selesai dengan jumlah node yang aktif saat itu, dan node yang sedang terhubung. Ini membantu memutuskan kapan menambah atau mematikan node.

Angka kapasitas di atas perkiraan dan divalidasi saat uji beban pertama di H100.

### 2.4 Keamanan node AI di GPU sewaan (cloud publik)

Pemilik produk menerima toleransi keamanan untuk **menyewa GPU (infrastruktur)** di cloud publik. Ini berbeda dari memakai layanan AI pihak ketiga: model berjalan di mesin yang dikendalikan instansi, dan penyedia tidak menerima dokumen sebagai bagian dari layanannya. Untuk memperkecil risiko:

- **Hanya node AI** (`worker` + `llm`) yang berjalan di cloud. Database, file asli, audit log, dan aplikasi tetap di server instansi.
- **Terowongan terenkripsi** (WireGuard) dari node AI ke server instansi. Node AI tidak membuka port publik apa pun. Selain terowongan, lalu lintas keluar node diblokir (tidak ada panggilan ke layanan lain, B1).
- **Tidak ada data permanen di node.** File PDF diambil lewat API internal saat job berjalan, disimpan di `tmpfs` (RAM), dan dihapus begitu job selesai. Hasil ditulis langsung ke database instansi. Mematikan atau menghapus node tidak menghapus data apa pun, dan tidak meninggalkan dokumen di disk sewaan.
- **Node terdaftar:** setiap node memakai kunci terowongan & token worker sendiri yang dapat dicabut Admin. Koneksi node tercatat di audit log.
- **Model** dibawa dalam image/volume yang disiapkan sebelumnya, sehingga node tidak perlu mengunduh apa pun dari internet saat berjalan.
- Log node tidak memuat isi dokumen (§6) dan dikirim ke server instansi lewat terowongan.

Bila nanti GPU dipindah ke server milik instansi, cukup jalankan node AI yang sama di sana tanpa terowongan. Tidak ada perubahan kode.

---

## 3. Desain Database

Prinsip:
- **Snapshot tidak berubah (immutable).** Checklist, Kategori, dan Panduan diversikan dengan menyalin isi ke versi baru; baris versi lama tidak pernah diubah/dihapus (pengecualian: hapus panduan permanen, §7 no. 14). Review menunjuk ke versi → tampilan review lama tidak terpengaruh (B4, C4, D6).
- **Hasil AI dan override dipisah** (O2). Nilai final dihitung, bukan ditimpa (O8).
- Semua tabel punya `id` (UUID) dan `created_at`; kolom di bawah hanya yang bermakna.

### 3.1 Pengguna & akses

| Tabel | Kolom penting | Kegunaan |
| --- | --- | --- |
| `satker` | `kode_uke1`, `unit_kerja` (UKE I / Unit Kerja, Eselon I), `kode_uke2`, `nama` (UKE II / Satuan Kerja, Eselon II) (semua opsional), `aktif`, `created_by`, `create_date`, `update_by`, `update_date` | Daftar Satker (dikelola Admin di menu Satker). Unik per (`unit_kerja`, `nama`) dan per `kode_uke2` bila diisi. Data awal 56 Satker dari dokumen "Data Satker dan Unit Kerja" (`app/data_satker.py`). |
| `pengguna` | `username`, `password`, `satker_id`, `aktif`, `last_login_at`, `created_by`, `create_date`, `update_by`, `update_date` | Akun. `satker_id` membatasi data Pengusul. |
| `pengguna_role` | `pengguna_id`, `role` (`PENGUSUL`/`REVIEWER`/`ADMIN`) | Satu pengguna dapat banyak role (§4). |
| `sesi` | `pengguna_id`, `token_hash`, `expires_at` | Sesi login; token disimpan dalam bentuk hash. |

### 3.2 Usulan & dokumen

| Tabel | Kolom penting | Kegunaan |
| --- | --- | --- |
| `usulan` | `satker_id`, `tahun_anggaran`, `kode_ro`, `nama_ro`, `dibuat_oleh`, `diarsipkan_at` | Satu RO. Arsip = isi `diarsipkan_at` (A8). Hapus fisik hanya bila belum pernah ada review. |
| `revisi` | `usulan_id`, `nomor` (1,2,…), `tor_file_id`, `rab_file_id`, `status`, `dibuat_oleh` | Satu revisi = satu pasang TOR+RAB. Dokumen yang tidak diganti menunjuk file revisi sebelumnya (§5). `status`: `DRAF`, `ANTRE`, `DIPROSES_AI`, `GAGAL`, `MENUNGGU_VERIFIKASI`, `LOLOS`, `TIDAK_LOLOS`. |
| `file` | `sha256`, `nama_asli`, `ukuran`, `jumlah_halaman`, `path` | File PDF di penyimpanan (TOR, RAB, panduan). Tidak pernah dihapus bila pernah dirujuk. |
| `halaman` | `file_id`, `nomor`, `lebar`, `tinggi`, `hasil_scan` (bool) | Metadata halaman; ukuran untuk menskalakan sorotan. |
| `elemen` | `file_id`, `halaman`, `urutan`, `jenis` (paragraf/judul/butir/sel_tabel/gambar), `label_lokasi` (mis. "Bab II, poin 2.3, paragraf 2" / "Pasal 5 ayat (2)" / "Tabel 3 baris 4 kolom Volume"), `teks`, `bbox`, `sumber` (teks/ocr/vlm) | Hasil ekstraksi terstruktur. Inilah unit yang dirujuk AI; `bbox` dipakai untuk menyorot. Deskripsi gambar dari VLM ditandai `sumber=vlm`. |
| `chunk` | `file_id`, `elemen_ids[]`, `teks`, `embedding` (vector), `sparse` (jsonb) | Potongan untuk pencarian; tetap tahu elemen asalnya. |

Ekstraksi disimpan per `file` (berdasarkan SHA), sehingga file yang terbawa ke revisi berikutnya tidak diekstraksi ulang.

### 3.3 Checklist, Kategori, Panduan (berversi)

| Tabel | Kolom penting | Kegunaan |
| --- | --- | --- |
| `checklist_item` | `id`, `created_by`, `create_date`, `update_by`, `update_date`, `no_urut`, `kode` (unik), `checklist`, `kriteria` (text), `berlaku_untuk` (`TOR`/`RAB`/`TOR & RAB`), `aktif` | Isi **terbaru** item, satu baris per item. Hapus item selalu permanen (beserta riwayatnya). `hasil_item`/`rekomendasi`/`override.checklist_item_id` tanpa FK karena item boleh dihapus. |
| `checklist_histori` | `id`, `checklist_id` (FK → `checklist_item.id`, ON DELETE CASCADE), lalu kolom sama dengan `checklist_item` | **Semua versi** item: setiap tambah & ubah menyalin isi item saat itu (termasuk versi terbaru); `kode` = kode pada versi itu, jadi ganti kode tetap tercatat. Isi checklist sebuah review disusun ulang dari kedua tabel pada `review.mulai_at`: versi dengan `update_date` terakhir ≤ waktu itu (`app/checklist.py`). |
| `kategori_versi` | `nomor`, `aktif`, `dibuat_oleh` | Sama seperti checklist (C3). |
| `kategori_item` | `versi_id`, `kode` (K1…), `nama`, `definisi`, `diteruskan` (bool) | Definisi yang dipakai AI (C2). `diteruskan=false` untuk K4 (C6) — tidak di-hardcode. Seed: 4 kategori persis PRD C1. |
| `panduan` | `id`, `created_by`, `created_date`, `updated_by`, `updated_date`, `panduan`, `aktif`, `file_id`, `nama_file`, `deskripsi` (urutan kolom ini, §7 no. 17–18) | Panduan beserta isi **versi terkini**. `panduan` = Nama Acuan; nomor versi tidak disimpan: terkini = jumlah riwayat + 1 (§7 no. 18); `created_by/date` = pengunggah & waktu unggah pertama; `updated_by/date` = penginput & waktu versi terkini. Hapus = permanen (§7 no. 14); `aktif=false` (Nonaktif) = tetap tampil, tetapi tidak dipakai review berikutnya. |
| `panduan_histori` | `id`, `created_by`, `created_date`, `updated_by`, `updated_date`, `panduan_id`, `panduan`, `aktif`, `file_id`, `nama_file`, `deskripsi` | **Riwayat saja (Panduan Histori; dulu `panduan_versi`, §7 no. 19)**: salinan utuh baris `panduan` sebelum tiap perubahan; `updated_by/date` = penginput & waktu versi itu; riwayat ke-n menurut `updated_date` = versi n. Baris tidak pernah diubah. Status proses dibaca dari `file.status_ekstraksi` (D4, D5, D9). |

### 3.4 Review, hasil AI, override

| Tabel | Kolom penting | Kegunaan |
| --- | --- | --- |
| `review` | `revisi_id`, `trace_id`, `kategori_versi_id`, `fingerprint`, `model_info` (jsonb: nama/versi model, versi prompt), `diajukan_oleh`, `mulai_at`, `selesai_at`, `progres` (jsonb: tahap & persen), `error_pesan`, `difinalkan_oleh`, `difinalkan_at` | Satu revisi = satu review sukses (§5). Review GAGAL boleh diulang → baris baru. `trace_id` muncul di semua log (§8.1). `fingerprint` dijelaskan di §4.6. |
| `review_panduan` | `review_id`, `panduan_id`, salinan `nomor`, `judul`, `file_id`, `nama_file` | Panduan + versi yang benar-benar dipakai review (hanya yang SIAP), disalin saat acuan dikunci sehingga tetap benar walau panduan diedit (D5, §7.3). |
| `hasil_item` | `review_id`, `checklist_item_id`, `terpenuhi` (bool), `alasan`, `yang_kurang` | Penilaian AI per item (Screening 1, keluaran #2). |
| `hasil_label` | `review_id`, `label_ai` | Label AI — **dihitung oleh kode** dari `hasil_item` (§7.1), bukan dari LLM. |
| `hasil_kategori` | `review_id`, `kategori_item_id`, `alasan` | Screening 2. |
| `rekomendasi` | `review_id`, `dokumen` (`TOR`/`RAB`), `urutan`, `teks`, `checklist_item_id` (nullable), `tidak_diperlukan` (bool) | Rekomendasi perbaikan (keluaran #3, #4, E5). |
| `rujukan` | `pemilik_jenis` (`hasil_item`/`rekomendasi`/`hasil_kategori`), `pemilik_id`, `elemen_id`, `kutipan`, `peran` (`bukti_dokumen`/`dasar_panduan`) | Bukti E1/E2. Menunjuk `elemen` → otomatis tahu file, halaman, lokasi, dan bbox (E3). |
| `override` | `review_id`, `target` (`ITEM`/`LABEL`/`KATEGORI`), `checklist_item_id` (nullable), `nilai_sebelum`, `nilai_sesudah`, `alasan` (wajib), `oleh`, `at`, `dibatalkan_at` | Override terpisah dari hasil AI (O1–O5). Batal = isi `dibatalkan_at`, riwayat tetap ada. Dikunci setelah `review.difinalkan_at` terisi (O7). |
| `catatan_reviewer` | `review_id`, `dokumen` (TOR/RAB/umum), `teks`, `oleh`, `diubah_at` | Catatan/rekomendasi tambahan untuk Pengusul. Disembunyikan dari Pengusul sebelum final (§5). |

**Nilai final** (O8) dihitung oleh satu fungsi di backend, tidak disimpan ganda:
- item final = override `ITEM` aktif terakhir, jika ada; selain itu `hasil_item.terpenuhi`;
- label hitung-ulang = LOLOS jika semua item final terpenuhi (O6);
- label final = override `LABEL` aktif bila ada, selain itu label hitung-ulang; bila override label ≠ label hitung-ulang → tampilkan peringatan, alasan wajib;
- kategori final = override `KATEGORI` aktif bila ada, selain itu `hasil_kategori`.

Saat **Finalkan**, nilai final disalin ke `review` (`label_final`, `kategori_final_id`) sebagai snapshot terkunci, dan `revisi.status` diubah ke `LOLOS`/`TIDAK_LOLOS`.

### 3.5 Operasional

| Tabel | Kolom penting | Kegunaan |
| --- | --- | --- |
| `job` | `jenis` (`REVIEW`/`PROSES_PANDUAN`), `ref_id`, `status`, `percobaan`, `dikunci_at`, `trace_id` | Antrean latar belakang (§5). Posisi antrean = urutan `created_at`. Job yang worker-nya mati dilepas kembali setelah batas waktu. |
| `audit_log` | `pengguna_id`, `aksi`, `entitas`, `entitas_id`, `data_sebelum`, `data_sesudah` (jsonb), `ip`, `at` | Aktivitas pengguna (§7.3). Hanya-tambah; terpisah dari log teknis. |

---

## 4. Alur Logika AI

### 4.1 Ekstraksi dokumen (TOR, RAB, Panduan — pipeline yang sama)

1. **Validasi**: benar PDF (cek *magic bytes* + dapat dibuka), batas ukuran, tidak terenkripsi.
2. **Per halaman**: Docling membaca layout → paragraf, judul, butir bernomor, tabel (per sel), gambar. Halaman tanpa lapisan teks (atau teks rusak) → di-render menjadi gambar lalu di-OCR; halaman campuran di-OCR hanya pada bagian gambarnya.
3. **Gambar, grafik, diagram**: dipotong sesuai bbox lalu dideskripsikan oleh VLM ("grafik batang realisasi 2022–2024: …"). Deskripsi disimpan sebagai `elemen` bersumber `vlm`, sehingga dapat dirujuk tetapi ditandai sebagai interpretasi gambar.
4. **Label lokasi**: penomoran hierarki dilacak (Bab → poin 2.3 → paragraf ke-n → kalimat; Pasal → ayat → huruf; Tabel → baris → kolom) sehingga setiap elemen punya `label_lokasi` yang dapat dibaca manusia.
5. **Chunking & embedding**: elemen digabung menurut struktur (satu pasal/ayat, satu sub-bab, satu kelompok baris tabel), lalu di-embed (dense + sparse). Chunk selalu menyimpan ID elemen asalnya.

Halaman PDF yang dipakai di semua rujukan adalah **indeks halaman file PDF** (1, 2, 3, …), bukan nomor yang tercetak di dokumen, sehingga klik rujukan selalu tepat (E3). Bila keduanya berbeda, nomor tercetak ditampilkan sebagai info tambahan.

### 4.2 Screening 1 — per item checklist

Setiap item dinilai **terpisah** dengan konteks yang fokus, bukan satu prompt raksasa. Ini meningkatkan akurasi dan membuat kegagalan satu item dapat diulang tanpa mengulang semuanya.

Untuk setiap item:
1. **Cari bukti dokumen**: pencarian hibrida (dense + sparse + reranker) pada TOR dan/atau RAB sesuai `berlaku_untuk`. RAB (±10 hlm) cukup kecil sehingga untuk item yang berlaku pada RAB, seluruh isi RAB disertakan.
2. **Cari dasar panduan**: pencarian hibrida yang sama pada panduan aktif, menggunakan kriteria item + bukti dokumen yang ditemukan sebagai kueri.
3. **Penalaran (mode thinking)**: LLM menerima kriteria item, kandidat bukti dokumen, dan kandidat ketentuan panduan — setiap potongan diberi ID elemen (mis. `[E-8f2a]`). LLM wajib menjawab dalam **JSON terstruktur** (dipaksa *guided decoding*): `terpenuhi`, `alasan`, `yang_kurang`, daftar `rujukan` berisi **ID elemen + kutipan**. LLM diinstruksikan: terpenuhi hanya jika isinya **sesuai ketentuan panduan yang relevan**, bukan sekadar menyebut topiknya (§7.1).
4. **Sapuan konfirmasi** bila hasilnya "tidak ditemukan": sebelum menyatakan "tidak ditemukan di dokumen", seluruh TOR dipindai per jendela ±8 halaman dengan pertanyaan pendek "adakah bagian yang menjawab kriteria ini?". Ini mencegah item gagal hanya karena retrieval meleset. Kalau sapuan menemukan bukti, langkah 3 diulang dengan bukti tersebut.

### 4.3 Verifikasi rujukan (penjaga anti-halusinasi, E3–E4)

Setiap rujukan dari LLM diperiksa kode, bukan dipercaya:
- ID elemen harus ada dan termasuk konteks yang diberikan untuk item itu;
- kutipan harus benar-benar ada di teks elemen (dicocokkan setelah normalisasi spasi/tanda baca); kutipan yang disimpan adalah **teks asli dari database**, bukan ketikan LLM;
- halaman, label lokasi, dan bbox **diambil dari database**, tidak pernah dari LLM.

Rujukan yang gagal verifikasi dibuang, lalu item dinilai ulang (maks. 2×) dengan umpan balik "rujukan X tidak valid". Bila penilaian "terpenuhi" tidak menyisakan satu pun rujukan valid, item dianggap tidak terpenuhi dengan alasan "bukti tidak dapat diverifikasi" — sistem memilih aman daripada meloloskan tanpa bukti.

### 4.4 Label, rekomendasi, dan keselarasan RAB–TOR

1. **Label** dihitung kode: LOLOS ⇔ semua item terpenuhi (§7.1). LLM tidak pernah menentukan label, sehingga label pasti konsisten dengan hasil per item.
2. **Keselarasan RAB–TOR**: LLM memetakan setiap komponen biaya RAB ke kegiatan/keluaran di TOR (dengan rujukan keduanya), lalu mencatat komponen RAB tanpa dasar di TOR dan kegiatan TOR tanpa anggaran. Hasilnya masuk ke rekomendasi RAB (keluaran #4) dan **tidak memengaruhi label** (disepakati pemilik produk). Bila keselarasan ini ingin menentukan LOLOS/TIDAK LOLOS, Admin menambahkannya sebagai item checklist (berlaku: KEDUANYA).
3. **Rekomendasi TOR & RAB**: dibangun dari item yang tidak terpenuhi + temuan keselarasan; tiap rekomendasi berisi langkah konkret dan rujukan panduan (diverifikasi seperti §4.3). Jika semua item untuk suatu dokumen terpenuhi dan tidak ada temuan, disimpan "Tidak diperlukan perbaikan" (E5).

### 4.5 Screening 2 — kategori

Dijalankan otomatis setelah Screening 1, apa pun labelnya. Input: definisi kategori dari **versi kategori aktif** (dibaca dari database, C2), ringkasan TOR yang relevan (dasar hukum, penetapan oleh Menteri, keterkaitan prioritas nasional & tusi Satker — dicari dengan retrieval), serta panduan terkait. LLM memilih satu kode kategori dari daftar versi tersebut (dibatasi *guided decoding*, sehingga tidak bisa mengarang kode lain), memberi alasan yang mengacu definisi, dan rujukan terverifikasi.

### 4.6 Konsistensi hasil (§8 Akurasi)

Dua lapis:
1. **Inferensi sedeterministik mungkin**: temperatur 0, *seed* tetap, model dan prompt berversi, urutan konteks diurutkan stabil (berdasarkan ID elemen).
2. **Fingerprint hasil**: `fingerprint = hash(SHA TOR, SHA RAB, versi checklist, versi kategori, daftar versi panduan, versi model, versi prompt)`. Jika revisi baru diajukan dengan fingerprint yang sama dengan review sukses sebelumnya, hasil AI **disalin** dari review tersebut (dicatat sebagai "hasil identik dengan revisi ke-n"). Inilah yang **menjamin** hasil sama persis. Inferensi GPU yang diparalelkan (§2.3) tidak 100% deterministik, sehingga konsistensi tidak boleh bergantung pada lapis 1 saja. Karena versi model termasuk fingerprint, hasil model dev tidak pernah dipakai ulang di production.

### 4.7 Progres, antrean, dan kegagalan

- Progres disimpan per tahap: `Antre (posisi n)` / `Menunggu kapasitas AI` → `Ekstraksi TOR` → `Ekstraksi RAB` → `Menilai item 3/15` → `Keselarasan RAB–TOR` → `Rekomendasi` → `Kategori` → `Selesai`. Frontend memantau dengan *polling* ringan (5 detik).
- Hasil antara (ekstraksi, hasil per item) disimpan bertahap; error di tengah tidak menghapus apa pun. Status → `GAGAL` dengan pesan ramah + `trace_id`. Pengusul dapat mengulang (§5).
- Saat review berjalan/menunggu verifikasi, endpoint unggah revisi menolak perubahan pada revisi tersebut.
- Versi checklist, kategori, dan panduan **dikunci saat review mulai diproses**. Perubahan oleh Admin setelah itu tidak memengaruhi review yang sedang berjalan, dan baru berlaku untuk review berikutnya.

---

## 5. Desain Antarmuka

### 5.1 Struktur & navigasi

- **Desktop**: sidebar kiri (Dashboard, Usulan, Kelola ▸ Checklist/Kategori/Panduan/Pengguna, Audit Log) — menu tampil sesuai role. Header: nama, role aktif, Satker.
- **Tablet/ponsel**: sidebar menjadi menu laci; tabel menjadi kartu; panel PDF menjadi tab terpisah.
- **Warna status konsisten** di seluruh aplikasi: DRAF abu-abu, ANTRE/DIPROSES biru (+ indikator berputar), GAGAL merah tua, MENUNGGU VERIFIKASI kuning, LOLOS hijau, TIDAK LOLOS merah. **K4** diberi badge "Tidak diteruskan". Status selalu disertai teks, bukan warna saja (aksesibilitas).
- **AI vs reviewer**: nilai AI berlabel kecil "AI"; nilai override berlabel "Diubah reviewer" berwarna ungu, dengan nilai AI dicoret di sebelahnya dan tooltip alasan/siapa/kapan (O3).

### 5.2 Halaman

| Halaman | Isi utama |
| --- | --- |
| Login | Username, password. Pesan error umum (tidak membocorkan akun mana yang ada). |
| Dashboard | Kartu jumlah per status; grafik per kategori final; tabel ringkas per Satker; daftar "Perlu tindakan saya" (Pengusul: draf/gagal/tidak lolos; Reviewer: menunggu verifikasi). |
| Daftar Usulan | Tabel A2 + filter A5 + pencarian. Kolom checklist "8/10" dapat diklik → popover rincian per item (A4). Tombol aksi per baris sesuai role/status (A3). Toggle "tampilkan arsip". |
| Buat Usulan / Unggah Revisi | Form A1; area seret-lepas PDF dengan validasi langsung. Pada revisi: pilih ganti TOR, RAB, atau keduanya; file lama ditampilkan sebagai "terbawa dari revisi n". Tombol "Simpan Draf" dan "Ajukan Review". |
| Detail Review | Lihat wireframe §5.3. |
| Riwayat Usulan | Timeline vertikal per revisi: file yang diganti, review, label & kategori final, siapa memfinalkan. Tabel perbandingan checklist antar-revisi (baris = item, kolom = revisi, sel ✓/✗; perubahan ✗→✓ disorot hijau, ✓→✗ merah). Item yang berbeda antar versi checklist ditandai. |
| Kelola Checklist / Kategori | Daftar item yang dapat diurutkan; form tambah/ubah; tombol "Simpan sebagai versi baru" dengan catatan perubahan; tab "Versi" untuk melihat isi setiap versi (B5, C5). |
| Kelola Panduan | Tabel: No, Nama Acuan (buka PDF), Deskripsi, Status (Aktif/Nonaktif, hanya tampilan, dapat diurutkan), Diinput Oleh, Tanggal Input (versi terbaru), Aksi (ikon: halaman detail `/panduan/:id` + riwayat versi untuk semua pengguna; edit, proses ulang, hapus untuk Admin); status proses (Antre/Diproses/Siap/Gagal + ulangi) di bawah nama. Unggah (`/panduan/unggah`, satu file + nama, deskripsi, status) dan edit (`/panduan/:id/ubah`, nama, deskripsi & status; tanpa ganti file) di halaman form yang sama, dengan pop-up konfirmasi; hapus (permanen, §7 no. 14). Panduan + versi yang dipakai tiap review tampil di hasil review. |
| Kelola Pengguna | Pengguna, multi-role, Satker, aktif/nonaktif, reset password; juga daftar Satker (dikelola Admin di sini). Satker tempat Reviewer bernaung diperlakukan sama seperti Satker lain: usulannya dibuat oleh akun Pengusul tersendiri, bukan oleh akun Reviewer. |
| Audit Log | Tabel dapat difilter (pengguna, aksi, entitas, tanggal); detail sebelum/sesudah. |

### 5.3 Wireframe Detail Review (desktop)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ‹ Usulan  Satker X · TA 2027 · RO 1234.ABC  · Revisi 3       [Riwayat] [Finalkan]│
│ ┌ Hasil AI — belum diverifikasi reviewer ┐   (banner untuk Pengusul sebelum final)│
├───────────────────────────────────────────┬──────────────────────────────────────┤
│ LABEL  [TIDAK LOLOS] AI  · 13/15 terpenuhi │  [TOR] [RAB] [Panduan ▾]   hlm 12/48 │
│ KATEGORI  [K2] AI  → [K3] Diubah reviewer │ ┌──────────────────────────────────┐ │
│   alasan AI · alasan override ⓘ           │ │                                  │ │
│ Acuan: Checklist v4 · Kategori v2 ·       │ │   (PDF.js — bagian yang dirujuk  │ │
│        7 panduan ▾                         │ │    disorot kuning)               │ │
├───────────────────────────────────────────┤ │                                  │ │
│ [Checklist] [Rekomendasi TOR] [Rek. RAB]  │ │                                  │ │
│ [Catatan Reviewer]                        │ │                                  │ │
│                                           │ └──────────────────────────────────┘ │
│ ✗ 4. Indikator keluaran terukur      AI ▾ │                                      │
│   Alasan: …                               │                                      │
│   Kurang: target kuantitatif belum ada    │                                      │
│   Bukti: TOR hlm 12, poin 3.2 par. 1  ↗   │                                      │
│     "…keluaran berupa peningkatan…"       │                                      │
│   Dasar: PMK xx/2025 hlm 7, Pasal 5(2) ↗  │                                      │
│   [Override ⇄]                            │                                      │
│ ✓ 5. …                                    │                                      │
└───────────────────────────────────────────┴──────────────────────────────────────┘
```

- Klik rujukan ↗ → panel kanan membuka dokumen yang tepat, lompat ke halaman, menyorot bbox elemen (E3).
- Tombol **Override** membuka dialog: nilai baru + alasan (wajib). Label dihitung ulang langsung; bila reviewer mengubah label sehingga tidak konsisten, muncul peringatan (O6).
- **Finalkan** membuka dialog ringkasan (label, kategori, jumlah override) → konfirmasi → terkunci (O7).
- Ponsel: panel PDF menjadi tab ketiga; klik rujukan berpindah ke tab tersebut.

---

## 6. Keamanan, Logging, Pengujian, Deployment

**Keamanan**
- Setiap endpoint memeriksa role **dan** Satker di backend (Pengusul hanya usulan Satker-nya); file PDF hanya diunduh lewat API yang memeriksa hak akses, bukan URL statis.
- Validasi unggahan: tipe PDF asli, batas ukuran **100 MB per PDF** (dapat diubah lewat `.env`), nama file disanitasi, file disimpan dengan nama hash.
- CSRF token, *rate limit* login, header keamanan (CSP tanpa sumber eksternal — sekaligus mencegah panggilan keluar dari browser).

**Logging** (§8.1)
- Log JSON per baris: `waktu`, `level`, `modul`, `pesan`, `trace_id`, `pengguna_id`, `usulan_id`, `revisi_id`, `review_id`, `durasi_ms`.
- `trace_id` dibuat saat "Ajukan Review", dibawa ke job, worker, dan setiap panggilan LLM. Log tidak memuat password/token/isi dokumen utuh (hanya ID & panjang).
- Ditulis ke `/data/logs` dengan rotasi ukuran (mis. 50 MB × 10 file). Audit log terpisah di database.

**Pengujian**
- Unit: aturan label §7.1, nilai final & override O1–O8, versioning (ubah item tidak mengubah review lama), hak akses per role/Satker, transisi status §5, verifikasi rujukan §4.3, fingerprint §4.6.
- Integrasi: alur lengkap dengan LLM tiruan (respons tetap) agar cepat & deterministik.
- Evaluasi akurasi: set kecil TOR/RAB nyata yang sudah direview manual sebagai acuan; dijalankan saat ganti model/prompt.
- **Verifikasi offline**: jalankan stack dengan jaringan Docker `internal: true` + uji otomatis yang memastikan tidak ada koneksi keluar (mis. mencatat koneksi via `ss`/firewall log selama review berjalan), dan uji frontend bahwa tidak ada request ke domain selain host aplikasi.

**Pengujian beban**: simulasi 50 pengguna (login, daftar usulan, buka detail + PDF, polling progres) dengan target respons halaman < 1 detik saat antrean review penuh, dijalankan pada mode AI tiruan agar tidak butuh GPU.

**Deployment** (rincian cara jalan di §2.2)
- Isi repo: `docker-compose.yml` (semua layanan), `.env.dev`, `.env.prod`, `.env.tiruan`, `Makefile`, skrip `backup`/`restore`.
- Paket offline (`make bundle`): image kontainer + folder `models/` + file di atas, dalam satu arsip.
- Backup = `pg_dump` + salinan folder `files/`. Ganti model = ubah nama model di `.env`, `make setup`, `make up` (versi model tercatat di setiap review).
- Server GPU on demand hanya menjalankan node AI (`make up-ai`, dengan konfigurasi terowongan §2.4); data tetap di server aplikasi.

---

## 7. Penyimpangan saat Implementasi (2026-10-12)

| # | Desain | Implementasi | Alasan |
| --- | --- | --- | --- |
| 1 | Dev: Qwen3-VL 8B Thinking AWQ 4-bit | `cyankiwi/Qwen3-VL-8B-Thinking-AWQ-4bit` (compressed-tensors W4A16) | Qwen belum merilis AWQ resmi untuk 8B Thinking. Kuantisasi komunitas mewarisi lisensi Apache-2.0 model induk. Prod tetap `Qwen/Qwen3-VL-32B-Thinking` BF16, dengan opsi `-FP8` resmi. |
| 2 | vLLM (versi tidak disebut) | `vllm/vllm-openai:v0.30.0`, `--reasoning-parser deepseek_r1`, `response_format: json_schema` | Rilis stabil ≥2 minggu. Parser `deepseek_r1` sesuai template chat Qwen3 Thinking yang menyisipkan `<think>`. |
| 3 | Sparse BGE-M3 (`chunk.sparse` jsonb) | Full-text search PostgreSQL `to_tsvector('indonesian')` (kolom `chunk.tsv`, indeks GIN) + dense BGE-M3 via sentence-transformers, digabung RRF lalu reranker | Tanpa dependensi FlagEmbedding yang rawan konflik versi. Stemmer Indonesia bawaan PostgreSQL menangkap kata kunci pasal/ayat dengan baik. Berfungsi juga di mode tiruan. |
| 4 | OCR RapidOCR/Tesseract | Tesseract CLI (`ind`+`eng`) melalui Docling | Model bahasa Indonesia sudah ada di paket OS, tanpa unduhan model OCR saat runtime. |
| 5 | Tabel `hasil_label` | Kolom `review.label_ai` | Satu nilai per review; tetap dihitung kode dari `hasil_item`. |
| 6 | `panduan_versi.status_proses`, `aktif` | Status dibaca dari `file.status_ekstraksi`; review memakai versi SIAP terbaru per panduan | Ekstraksi bersifat per file (SHA), sehingga status tidak disimpan ganda. Versi lama yang SIAP tetap dipakai selama versi baru diproses. |
| 7 | `file.nama_asli` | Nama tampilan disimpan juga di `revisi.tor_nama/rab_nama` dan `panduan_versi.nama_file` | File identik (SHA sama) yang diunggah dengan nama berbeda tetap tampil sesuai nama unggahannya. |
| 8 | ID elemen ke LLM (mis. `[E-8f2a]`) | Alias per prompt `E1…`/`P1…`, dibatasi `enum` pada JSON schema | LLM tidak mungkin menyebut ID di luar konteks; pemetaan alias → elemen dilakukan kode. |
| 9 | shadcn/ui | Primitif Radix (Dialog, Popover) + komponen Tailwind sendiri bergaya shadcn (`frontend/src/ui.tsx`) | Hasil visual sama tanpa generator/CLI. |
| 10 | Satu file compose + env per skenario | `docker-compose.yml` dasar + `gpu`/`dev`/`prod`/`node-ai`, dipilih lewat `COMPOSE_FILE` di `.env`; tambahan `.env.node-ai` | `cp .env.x .env && make up` tetap satu perintah. Server aplikasi prod tanpa GPU; node AI terpisah. |
| 11 | Dokumentasi API OpenAPI otomatis | Skema tersedia di `/api/openapi.json`; Swagger UI dimatikan; ringkasan di docs/api.md | Swagger UI memuat aset dari CDN (melanggar B1). |
| 12 | Tailwind CSS | Tailwind 4.1.13 | 4.0.0 gagal memproses CSS di Vite. |
| 13 | `panduan_versi.aktif` | `panduan_versi.aktif` (status saat versi dibuat, migrasi `0004`) + salinan status terkini di `panduan.aktif` (+ `diubah_oleh`, `diubah_at`, migrasi `0003`) (2026-10-19) | Setiap perubahan status membuat versi baru agar riwayat versi menampilkan status. `panduan.aktif` dipakai kueri review & versi daftar panduan (yang Nonaktif tidak masuk snapshot dan tidak dipakai review). |
| 14 | Hapus panduan = *soft delete*; file & versi yang pernah dipakai review tidak boleh hilang (PRD v1 D5, D6) | Hapus **permanen**: `review_panduan`, `panduan_koleksi_item`, `panduan_versi`, `panduan`; file + `halaman`/`elemen`/`chunk`/`rujukan` + PDF di disk bila file tidak dipakai panduan lain/TOR/RAB. Ditolak (409) bila dipakai review yang berjalan atau file sedang diekstraksi (advisory lock yang sama dengan worker). | Keputusan pemilik produk 2026-10-19. Akibat: review lama kehilangan daftar panduan & rujukan dasar panduan yang dihapus; versi daftar panduan lama kehilangan item tersebut. Alternatif tanpa kehilangan data: status Nonaktif. |
| 15 | `panduan_versi` memuat semua versi termasuk terkini; `review_panduan`/item versi daftar menunjuk `panduan_versi.id` | Versi terkini di `panduan`, `panduan_versi` hanya riwayat; `review_panduan` & `panduan_koleksi_item` menyimpan salinan (panduan, nomor, judul, file). Fingerprint memakai `panduan_id:nomor`. Migrasi `0005_terkini_di_panduan` (2026-10-20). | Permintaan pemilik produk: tabel database mencerminkan tampilan (data terkini di detail, riwayat terpisah). Salinan di review menjaga D5 tanpa baris versi terkini. Efek sekali: review berikutnya untuk TOR/RAB yang sama tidak menyalin hasil review sebelum migrasi (fingerprint berbeda). |
| 16 | Versi **daftar** panduan (`panduan_koleksi_versi/_item`, `review.panduan_koleksi_versi_id`) setara versi checklist/kategori | Dihapus (migrasi `0006_hapus_versi_daftar_panduan`, 2026-10-20). Acuan panduan per review cukup dari `review_panduan` (panduan + nomor versi). | Keputusan pemilik produk: tabel ini terus bertambah dan hanya dipakai label "Panduan vN" di detail review. D5 tetap terpenuhi oleh `review_panduan`. No. 13–15 di atas yang menyebut versi daftar panduan berlaku hingga migrasi 0006. |
| 17 | Istilah database berbahasa Indonesia (`nomor`, `judul_terkini`/`judul`, `diubah_oleh`, `diubah_at`, `created_at`, `dihapus_at`) | `panduan` & `panduan_versi`: `no_urut` (dihapus di no. 18), `panduan`, `created_by` (baru), `created_date`, `updated_by`, `updated_date`; `dihapus_at` dihapus; urutan kolom sesuai §3.3. Tabel dibuat ulang (migrasi `0007_kolom_panduan`, 2026-10-21). Nama kolom API tetap. | Permintaan pemilik produk 2026-10-21. PostgreSQL tidak dapat mengubah urutan kolom, sehingga kedua tabel dibuat ulang dan datanya disalin dalam satu transaksi. Sisa *soft delete* lama dihapus permanen (sesuai no. 14). Tabel lain tetap memakai istilah Indonesia. |
| 18 | Nomor versi panduan disimpan (`no_urut`, dulu `nomor`) | Kolom `no_urut` dihapus dari `panduan` & `panduan_versi` (migrasi `0008_hapus_no_urut_panduan`, 2026-10-21). Nomor versi dihitung `Panduan.daftar_versi()`: riwayat ke-n menurut `updated_date` = versi n, terkini = jumlah riwayat + 1. Edit panduan mengunci barisnya (`SELECT … FOR UPDATE`). `review_panduan.nomor` tetap disimpan. | Permintaan pemilik produk. D5 (WAJIB) tetap terpenuhi: review menyimpan salinan nomor versi. Hitungan stabil karena riwayat tidak pernah diubah dan hanya terhapus bersama panduannya (D6). Kunci baris menggantikan UNIQUE (`panduan_id`, `no_urut`) agar dua edit bersamaan tidak menyalin versi yang sama dua kali. |
| 19 | Tabel riwayat panduan bernama `panduan_versi` | Tabel diganti nama menjadi `panduan_histori` (class model `PanduanHistori`), beserta index & constraint-nya (migrasi `0009_panduan_histori`, 2026-10-21). Nama field API tetap. Baris §7 di atas yang menyebut `panduan_versi` berlaku sebelum migrasi ini. | Permintaan pemilik produk: sesuai judul "Panduan Histori" di halaman detail panduan. |
| 20 | Kelola Checklist: sunting draf → "Simpan sebagai versi baru", tab "Daftar versi" (PRD B5) | Tabel item; tambah/ubah/hapus langsung disimpan per item. `checklist_item` menyimpan isi terbaru, `checklist_versi` menyimpan versi lama tiap item (bukan salinan seluruh daftar). Admin melihat versi lama per item di halaman Detail ("Riwayat Data"), bukan daftar versi seluruh checklist | Keputusan pemilik produk (2026-10-19/20) demi tampilan dan tabel yang lebih sederhana. B3/B4 tetap terpenuhi: review menyimpan nomor perubahan saat dikunci dan isi checklist saat itu disusun ulang dari versi lama. Halaman Kategori tidak berubah. |
| 21 | Snapshot checklist tidak pernah dihapus (CLAUDE.md aturan 4); PRD B4 "menghapus/mengubah item tidak boleh mengubah tampilan hasil review lama" (WAJIB) | Hanya dua tabel checklist (`checklist_item`, `checklist_histori`). Item yang dihapus dihapus **permanen** beserta riwayatnya, sehingga **ikut hilang dari tampilan review lama** (jumlah item review lama bisa berkurang). Mengganti kode item ikut tampil di review lama. Perubahan isi item tetap tidak mengubah review lama | Keputusan pemilik produk (2026-10-21) setelah diberi tahu bahwa ini melanggar B4; alternatif yang ditolak: tabel salinan per review, atau melarang hapus item yang sudah dipakai review. Nama kolom & nilai `TOR & RAB` juga permintaan pemilik produk. |

---

Desain ini sudah disetujui; implementasi lengkap berjalan sesuai PRD §12 langkah 3 dan `CLAUDE.md`.
