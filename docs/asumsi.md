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
- Kode checklist diisi manual oleh Admin (huruf dijadikan kapital, maks. 50 karakter), juga dapat diganti lewat Edit; harus unik di antara item yang ada. Kode yang sudah dihapus boleh dipakai lagi. Riwayat terhubung lewat `checklist_id`, sehingga ganti kode tidak memutus riwayat dan kode lama tetap tercatat; review lama tetap menampilkan kode saat itu.
- Urutan checklist (`no_urut`) diatur Admin lewat "Atur Urutan" (seret atau naik/turun) dan dipakai di tabel, database (urutan fisik tabel), serta urutan penilaian AI. Item baru otomatis ditaruh tepat setelah item berkode sebelumnya (E.02 di bawah E.01); mengganti kode tidak memindahkan item. Mengatur urutan tidak dicatat di `checklist_histori` karena isi item tidak berubah (tercatat di Audit Log).
- Urutan fisik tabel checklist (untuk pgAdmin "All Rows") dirapikan dengan CLUSTER hanya bila tabel tidak sedang dipakai (tunggu kunci ≤1 detik); bila sedang dibaca (mis. worker menunggu jawaban AI) dilewati dan dirapikan pada simpan berikutnya — agar simpan Admin tidak menahan seluruh aplikasi. Waktu `update_date` checklist dan `review.mulai_at` diambil dari jam database, karena worker bisa berjalan di server GPU lain.
- Status checklist per item: Nonaktif = item tetap tersimpan, tetapi tidak dinilai AI dan tidak dihitung dalam label LOLOS; minimal satu item harus Aktif — PRD tidak mengatur status item, ini tafsiran paling aman agar label tetap "semua item (aktif) terpenuhi".
- Kolom jejak checklist: `created_by`/`create_date` = siapa & kapan item ditambah, `update_by`/`update_date` = perubahan terakhir. Menyimpan tanpa perubahan isi tidak dicatat dan tidak membuat riwayat. Isi checklist review lama disusun ulang dari waktu review dimulai (`review.mulai_at`).
- Unit Kerja (Eselon I) disimpan sebagai kolom teks `satker.unit_kerja` (bukan tabel terpisah, keputusan pemilik produk); diketik bebas di form Satker (tanpa daftar saran), jadi Admin perlu menulis nama Unit Kerja secara seragam. Satuan Kerja dan Unit Kerja sama-sama opsional (keputusan pemilik produk); kosong disimpan sebagai teks kosong, bukan NULL, agar halaman lain (usulan, dashboard) yang menampilkan nama Satker tidak perlu diubah.
- Tabel `pengguna` dan `satker` memakai kolom jejak seperti checklist (`created_by`, `create_date`, `update_by`, `update_date`); `update_*` diisi saat data diubah lewat menu Pengguna/Satker, bukan saat login. Data lama/seed: pembuat tidak diketahui → ditampilkan "Sistem". Satker tidak lagi punya kode (kolom database = yang tampil di web); keunikan Satker = pasangan Unit Kerja + Satuan Kerja.
- Data awal Satker diambil dari dokumen "Data Satker dan Unit Kerja" (9 UKE I, 56 UKE II, beserta kodenya; nama pejabat tidak disimpan) dan diisi otomatis bila tabel satker kosong (juga di produksi) atau lewat migrasi 0006 untuk database lama; tabel Satuan Kerja diurutkan menurut kode (01.01, 01.02, …). Akun contoh dev (`pengusul`, `pengusul_b`) memakai Biro Perencanaan (01.04) dan Pusat Data dan Sarana Informatika (01.06).
- Tabel `pengguna` tidak punya kolom nama (keputusan pemilik produk). Di seluruh aplikasi (header, sapaan dashboard, "Dibuat Oleh"/"Diubah Oleh", riwayat, audit) yang tampil adalah username.
- Kode Satuan Kerja mengikuti dokumen: Kode UKE I = 2 digit (`01`), Kode UKE II = `NN.NN` diawali Kode UKE I induknya (`01.04`), dijaga di backend dan CHECK database. Kode UKE I tidak dapat diubah bila Satuan Kerja di bawahnya sudah berkode.
