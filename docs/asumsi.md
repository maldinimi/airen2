# Daftar Asumsi

Hal kecil yang tidak diatur PRD/desain.md, diputuskan dengan asumsi wajar (CLAUDE.md). Satu baris: asumsi — alasan.

**Akun & sesi**

- Sesi login berlaku 12 jam (`SESI_JAM`) — cukup untuk satu hari kerja tanpa login ulang berkali-kali.
- Lupa password tanpa email: Admin mereset password lewat menu Pengguna; reset mencabut sesi aktif — aplikasi intranet tanpa server email.
- Kebijakan password: minimal 8 karakter, kombinasi huruf dan angka/simbol — standar dasar tanpa membebani pengguna.
- Login dibatasi 5 kali gagal per 15 menit per username atau IP, dihitung dari audit log — perlindungan brute force yang tetap berlaku di banyak proses API.
- Password admin awal diambil dari `ADMIN_PASSWORD_AWAL` dan tidak dipaksa diganti saat login pertama; panduan instalasi meminta menggantinya segera — menyederhanakan alur login.
- Pengguna dengan beberapa role memperoleh gabungan hak aksesnya — PRD §4 mengizinkan multi-role.

**Status, revisi, dan arsip**

- Arsip/keluar arsip boleh dilakukan Pengusul dari Satker tersebut dan Admin — PRD tidak menyebut pelakunya.
- Revisi baru hanya dapat diunggah setelah hasil final TIDAK LOLOS, bukan setelah LOLOS — mengikuti diagram PRD §5.
- Dokumen dan data RO boleh diubah selama revisi berstatus DRAF atau GAGAL — belum ada hasil AI yang dilihat siapa pun.

**Penilaian & override**

- Override baru pada target yang sama menggantikan override sebelumnya; yang dipakai adalah override aktif terakhir, dan riwayatnya tetap tersimpan — O4/O5.
- Checklist tanpa item: label TIDAK LOLOS dan pengajuan review ditolak — tanpa item tidak ada yang dapat dibuktikan.

**Panduan**

- Panduan yang dipakai review adalah versi terbaru berstatus SIAP dari setiap panduan Aktif yang tidak dihapus. Selama versi baru diproses, versi lama yang SIAP tetap dipakai — panduan tidak "hilang" sementara.
- Unggah panduan satu file per form (Nama Acuan, Deskripsi, Status diisi per file), menggantikan unggah banyak file sekaligus (PRD D2) — permintaan pemilik produk 2026-10-19; nama, deskripsi, dan status berlaku per file.
- Panduan berstatus Nonaktif tetap tampil di daftar tetapi tidak dipakai review berikutnya; berbeda dengan Hapus yang menghapusnya permanen — permintaan saklar Aktif/Nonaktif.
- Kolom "Last Modify By/Date" ditampilkan sebagai "Diinput Oleh"/"Tanggal Input" (input/perubahan terakhir) dan diperbarui saat unggah atau ubah (termasuk ganti status), bukan saat proses ulang — antarmuka wajib berbahasa Indonesia.
- Form Edit panduan mengubah Nama Acuan, Deskripsi, dan Status; file tidak dapat diganti, baik dari antarmuka maupun API (PRD v2 D2; jalur ganti file di `PUT /api/panduan/{id}` dihapus 2026-10-21). Nama Acuan maksimal 500 karakter (batas kolom database). Untuk mengganti file: unggah panduan baru lalu nonaktifkan yang lama.
- Menyimpan form Edit tanpa perubahan apa pun tidak membuat versi baru — menghindari versi kembar. Mengubah status saja membuat versi baru agar tampil di Panduan Histori (kolom Status).
- Status per versi untuk data sebelum migrasi 0004 tidak diketahui: versi terbaru diisi status panduan saat itu, versi lama dianggap Aktif.
- "Tanggal Input" di detail panduan = tanggal versi pertama (saat diunggah).
- `panduan_histori` (dulu `panduan_versi`) menyalin utuh baris `panduan` sebelum perubahan: `created_by`/`created_date` = pengunggah & waktu unggah pertama (sama untuk semua versi), `updated_by`/`updated_date` = penginput & waktu versi itu — kolom permintaan pemilik produk 2026-10-21 sama di kedua tabel, dan riwayat tetap menampilkan siapa/kapan tiap versi diinput.
- Migrasi 0007 mengisi `panduan.created_by` dari penginput versi 1 (riwayat tertua, atau penginput versi terkini bila belum ada riwayat), dan menghapus permanen sisa panduan *soft delete* lama — tanpa `dihapus_at` panduan itu akan tampil lagi; hapus sudah permanen sejak PRD v2 D6.
- Nama kolom API (`judul`, `nomor`, `dibuat_oleh`, `dibuat_at`, `diubah_oleh`, `diubah_at`) tidak ikut diganti — permintaan hanya untuk kolom database; frontend tidak perlu diubah.

**Data contoh & aturan AI**

- Checklist contoh, Satker contoh, dan akun pengusul/reviewer contoh hanya di-seed bila `SEED_CONTOH=true` (dev/tiruan) — production hanya mendapat 4 kategori + admin.
- Temuan keselarasan RAB–TOR ditampilkan sebagai rekomendasi RAB dan tidak memengaruhi label — sesuai desain §4.4.
- Sapuan konfirmasi "tidak ditemukan" hanya untuk TOR; RAB disertakan utuh bila muat di konteks — desain §4.2.

**Rujukan & lokasi**

- Lokasi "kalimat ke-n" dihitung dari posisi kutipan di dalam elemen dan hanya ditampilkan bila elemen berisi lebih dari satu kalimat — E1 meminta presisi sampai kalimat.
- Paragraf yang terpotong melintasi dua halaman dirujuk ke halaman awalnya (provenance pertama Docling) — kasus jarang; rujukan tetap pada isi yang benar.
- Nomor halaman tercetak tidak ditampilkan; yang dipakai selalu indeks halaman PDF — desain §4.1 menjadikan nomor tercetak hanya info tambahan.
- Mode tiruan memakai ekstraktor sederhana (pdfplumber, tanpa OCR); halaman scan dideskripsikan sebagai gambar oleh AI tiruan — agar image tiruan ringan tanpa torch/GPU.

**Worker & antrean**

- Job dianggap macet bila detak worker berhenti 5 menit; setelah 3 percobaan, job dan review ditandai GAGAL — mencegah loop crash tanpa akhir.
- Satu worker memproses satu review pada satu waktu dengan item paralel (`ITEM_PARALEL`); kapasitas ditambah dengan menambah node — sederhana dan sesuai desain §2.3.
- Log node AI disimpan di disk node (tanpa isi dokumen) dan tidak dikirim otomatis ke server — mengirim log memerlukan komponen tambahan; isinya tidak sensitif.

**Kontainer, UI, dan WireGuard**

- Kontainer backend berjalan sebagai root — menghindari masalah izin bind mount `./data` di Windows/Linux. Isolasi tetap terjaga oleh jaringan internal.
- Waktu ditampilkan dalam zona Asia/Jakarta (WIB); database menyimpan UTC — instansi berada di WIB.
- Daftar usulan menampilkan 25 baris per halaman — responsif untuk ±50 pengguna.
- Image worker GPU berukuran besar (±15 GB: PyTorch + CUDA + Docling); siapkan disk kosong ≥60 GB untuk dev (image + model) — dependensi AI tidak dapat diperkecil tanpa mengorbankan B3.
- WireGuard dikonfigurasi di host (wg-quick), bukan sebagai kontainer — butuh modul kernel/akses jaringan host; panduan ada di docs/instalasi-offline.md.
- Mode dev & tiruan membuka akses database untuk GUI di `127.0.0.1:5433` lewat penerus TCP `db-gui` (scripts/teruskan_tcp.py, image backend yang sudah ada). Kontainer `db` tetap hanya di jaringan internal: menyambungkannya langsung ke jaringan lain memberi jalur ke internet di Docker Desktop (opsi tanpa NAT tidak dihormati), melanggar B1.
- Setelah migrasi 0005, review berikutnya untuk TOR/RAB yang identik tidak menyalin hasil review sebelum migrasi (kunci fingerprint panduan berubah menjadi `panduan_id:nomor`), melainkan dijalankan ulang sekali.
