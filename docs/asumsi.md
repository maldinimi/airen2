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
- Daftar usulan: bawaan 10 baris per halaman. Paging selalu tampil (walau hanya satu halaman): nomor halaman ‹ 1 2 3 › di kiri, pilihan "Baris per halaman" (10/20/50/100) di kanan — label berbahasa Indonesia, bukan "Show rows" (CLAUDE.md aturan 7).
- Form filter daftar usulan: Satuan Kerja/Rincian Output/Dokumen berupa pencarian teks sebagian (tidak peka huruf besar), Dokumen mencari nama file TOR atau RAB revisi terbaru, Tanggal Pengajuan dibandingkan per tanggal WIB. Urut Status berdasarkan kode status. Di layar kecil (kartu) urut per kolom tidak tersedia; urutan mengikuti pilihan terakhir di layar lebar.
- Program/Kegiatan/KRO/RO di form Pengajuan Baru diambil dari "Revisi_laporan_renja_2026.xlsx" (sheet "Laporan RENJA KL") dan disalin ke `backend/app/data_rka.py`: 4 program, 44 kegiatan, 422 RO. Jalur dobel disimpan sekali; 5 kegiatan tanpa KRO/RO di file tersebut (7452, 7454, 7456, 7658, 7899) tidak dapat dipilih; spasi ganda dirapikan; nama KRO mengikuti baris kegiatannya (kode AAG & CCL punya dua versi nama). Kolom unit eselon & prioritas nasional tidak dipakai (dropdown tidak dibatasi per Satker). Bila Renja diperbarui, `data_rka.py` perlu dibuat ulang; usulan lama tetap menyimpan salinannya.
- Filter status di halaman Usulan hanya tiga pilihan sesuai permintaan: Lolos, Menunggu Reviewer (= MENUNGGU_VERIFIKASI), Tidak Lolos. Usulan berstatus lain (Gagal, Draf, Antre, Diproses AI) hanya terlihat dengan "Semua Status". Label status di tabel tidak diubah.
- TOR/RAB lama yang diganti (Ganti Dokumen saat Draf/Gagal, atau Edit Usulan oleh Reviewer) langsung dihapus bila tidak dipakai/dikutip apa pun; bila masih dikutip rujukan review lama, file disimpan sampai usulannya dihapus, agar review lama tetap utuh dan "hapus permanen" tidak meninggalkan dokumen.
- Form filter Usulan awalnya terlipat, kecuali bila halaman dibuka dengan filter yang sudah aktif (mis. kembali dari Detail), agar filter yang berlaku tidak tersembunyi.
- Catatan AI kategori pada AI tiruan berbeda per kategori (K1–K4, disusun dari definisinya; kalimat pemilik produk "RO bukan merupakan prioritas nasional, …" dipakai untuk K4 dengan perbaikan susunan kata). Tetap diawali "(AI tiruan)" seperti catatan tiruan lain. AI sungguhan menulis alasannya sendiri.
- "Tampilkan arsip" dihapus; tombol Arsipkan/Keluarkan dari arsip juga dihapus, karena usulan yang diarsipkan tidak dapat lagi dibuka dari daftar. Usulan yang sudah terlanjur diarsipkan tetap ada di database (endpoint arsip tetap).
- Tombol Bukti & Rujukan (halaman Pemeriksaan) dan Perbandingan Revisi (Detail Usulan) dihapus atas permintaan; halamannya (`/review/:id/rinci`, `/usulan/:id/riwayat`) kemudian dihapus (desain.md §7 no. 40) karena tidak terjangkau dan punya cara override sendiri; kategori kini dinilai di tabel Kategori halaman Pemeriksaan.
- Catatan Verifikator per item disimpan terpisah dari Status Verifikator (`catatan_item`). Penilaian verifikator di halaman Pemeriksaan belum tersimpan sampai Simpan Sebagai Draf/Finalkan; berpindah halaman atau memuat ulang sebelum menyimpan membuang perubahan (sesuai permintaan), tanpa peringatan.
- Edit Usulan oleh Reviewer: TOR/RAB pengganti dipasang di revisi terakhir yang sama (tidak menambah baris Histori Dokumen) dan revisi itu diajukan ulang ke AI, juga bila sudah final; review lama tetap tersimpan di database tetapi halaman memakai review terbaru. File lama tidak dihapus karena masih dirujuk review lama.
- "Halaman responsif (semua halaman)" diterapkan pada halaman menu Usulan dan bilah atas; tabel menu lain (Checklist, Kategori, Panduan, Pengguna, Audit) tetap dapat digeser mendatar di layar kecil.
- Jam ditampilkan 24 jam di semua halaman (format waktu diberi `hourCycle: h23` secara eksplisit).
- AI tiruan: Catatan AI dibentuk dari Kriteria Lolos item — lolos: "Dokumen telah menunjukkan bahwa …"; tidak lolos: "Dokumen belum sepenuhnya menunjukkan bahwa …" atau "Belum ditemukan bagian dokumen yang menunjukkan bahwa …" Rekomendasi AI item tidak lolos: "Lengkapi dokumen agar jelas menunjukkan bahwa …" atau "Tambahkan uraian pada dokumen yang menunjukkan bahwa …" (`catatan_tiruan` di `pekerja/llm.py`). Versi AI tiruan di `model_info` = `ai-tiruan-5` agar review baru tidak menyalin hasil lama lewat fingerprint. Review lama tidak diubah di database; saat ditampilkan, kalimat lama AI tiruan diganti dengan kalimat baru (`layanan_review.detail_review`). Mode AI sungguhan tidak terpengaruh.
- Label "Jumlah Checklist" di halaman Pemeriksaan = jumlah item yang Lolos menurut verifikator / total item (status bawaan mengikuti AI, sehingga "sudah diperiksa / total" selalu penuh dan tidak lagi informatif).
- Label pil (AI, Verifikator, Jumlah Checklist) dipakai untuk semua role agar tampilan seragam; Jumlah Checklist hanya tampil bila penilaian verifikator terlihat.
- Pilihan tahun di bilah atas (header) tampil di semua menu tetapi hanya menyaring menu Usulan (daftar usulan); pilihan dibatasi 5 tahun (tahun berjalan ±2, mengikuti jam perangkat), tanpa "Semua tahun", bawaan tahun berjalan; usulan di luar rentang itu tidak dapat ditampilkan lewat daftar; disimpan di browser (localStorage) per pengguna perangkat, bukan di server. Dashboard dan menu lain tidak terpengaruh.
- Tahun anggaran usulan baru = pilihan **Tahun Anggaran** di bilah atas saat Pengajuan Baru dikirim (ditampilkan di bawah judul form), divalidasi backend pada rentang tahun berjalan ±2 seperti pilihan di bilah atas. Revisi tetap memakai tahun anggaran usulannya.
- Kolom jejak `usulan` (`created_by`, `created_date`, `updated_by`, `updated_date`) mengikuti pola kategori. Usulan lama: pengubah terakhir tidak tercatat, sehingga `updated_by` diisi pembuatnya (`dibuat_oleh`). `dibuat_oleh` dipertahankan karena dipakai kode (isinya sama dengan `created_by`).
- Pengusul melihat hasil AI di halaman Pemeriksaan sejak AI selesai; Status/Catatan Verifikator dan Keputusan Akhir baru terlihat setelah final (sebelumnya label Verifikator bertuliskan "Menunggu verifikasi"), agar penilaian yang belum selesai tidak dibaca sebagai hasil.
- Aksi daftar usulan: Satker hanya Detail untuk usulan yang sudah terkirim (menunggu verifikasi, lolos, tidak lolos); saat **Gagal** ("gagal mengirimkan") Satker tetap dapat Edit untuk mengganti dokumen lalu mengirim ulang. Revisi setelah Tidak Lolos lewat tombol "Revisi" di Histori Dokumen → "Unggah Revisi" di halaman Pemeriksaan. Admin hanya Detail.
- Edit oleh Reviewer (ROCAN) ditafsirkan sebagai membetulkan salah input **hierarki anggaran & kategori usulan** (plus TOR/RAB pengganti pada revisi yang sama). Hapus usulan hanya oleh Reviewer (Admin & Satker tidak), **permanen dari database** untuk status apa pun kecuali antre/diproses AI — termasuk file PDF TOR/RAB dan hasil ekstraksinya bila tidak dipakai usulan/panduan lain (file dengan isi identik dipakai bersama). Yang tersisa hanya catatan di Audit Log (kode & nama RO, Satker, jumlah revisi/review/file), tanpa isi dokumen.
- Kategori yang dipilih Pengusul disimpan dan ditampilkan, tetapi belum dipakai AI; Screening 2 tetap merekomendasikan kategori sendiri.
- Image worker GPU berukuran besar (±15 GB: PyTorch + CUDA + Docling); siapkan disk kosong ≥60 GB untuk dev (image + model) — dependensi AI tidak dapat diperkecil tanpa mengorbankan B3.
- WireGuard dikonfigurasi di host (wg-quick), bukan sebagai kontainer — butuh modul kernel/akses jaringan host; panduan ada di docs/instalasi-offline.md.
- Mode dev & tiruan membuka akses database untuk GUI di `127.0.0.1:5433` lewat penerus TCP `db-gui` (scripts/teruskan_tcp.py, image backend yang sudah ada). Kontainer `db` tetap hanya di jaringan internal: menyambungkannya langsung ke jaringan lain memberi jalur ke internet di Docker Desktop (opsi tanpa NAT tidak dihormati), melanggar B1.
- Setelah migrasi 0005, review berikutnya untuk TOR/RAB yang identik tidak menyalin hasil review sebelum migrasi (kunci fingerprint panduan berubah menjadi `panduan_id:nomor`), melainkan dijalankan ulang sekali.
- Kode checklist diisi manual oleh Admin (huruf dijadikan kapital, maks. 50 karakter), juga dapat diganti lewat Edit; harus unik di antara item yang ada. Kode yang sudah dihapus boleh dipakai lagi. Riwayat terhubung lewat `checklist_id`, sehingga ganti kode tidak memutus riwayat dan kode lama tetap tercatat; review lama tetap menampilkan kode saat itu.
- Urutan checklist (`no_urut`) diatur Admin lewat "Atur Urutan" (seret atau naik/turun) dan dipakai di tabel, database (urutan fisik tabel), serta urutan penilaian AI. Item baru otomatis ditaruh tepat setelah item berkode sebelumnya (E.02 di bawah E.01); mengganti kode tidak memindahkan item. Mengatur urutan tidak dicatat di `checklist_histori` karena isi item tidak berubah (tercatat di Audit Log).
- Urutan fisik tabel checklist (untuk pgAdmin "All Rows") dirapikan dengan CLUSTER hanya bila tabel tidak sedang dipakai (tunggu kunci ≤1 detik); bila sedang dibaca (mis. worker menunggu jawaban AI) dilewati dan dirapikan pada simpan berikutnya — agar simpan Admin tidak menahan seluruh aplikasi. Waktu `update_date` checklist dan `review.mulai_at` diambil dari jam database, karena worker bisa berjalan di server GPU lain.
- Status checklist per item: Nonaktif = item tetap tersimpan, tetapi tidak dinilai AI dan tidak dihitung dalam label LOLOS; minimal satu item harus Aktif — PRD tidak mengatur status item, ini tafsiran paling aman agar label tetap "semua item (aktif) terpenuhi".
- Kolom jejak checklist: `created_by`/`create_date` = siapa & kapan item ditambah, `update_by`/`update_date` = perubahan terakhir. Menyimpan tanpa perubahan isi tidak dicatat dan tidak membuat riwayat. Isi checklist review lama disusun ulang dari waktu review dimulai (`review.mulai_at`).
- Urutan kategori (`no_urut`) diatur Admin lewat "Atur Urutan", sama dengan checklist (desain.md §7 no. 28); urutan awal = kode alami (K1, K2, …, K10). Kategori baru ditaruh setelah kategori berkode sebelumnya; mengganti kode tidak memindahkan kategori. Urutan hanya dipakai di tabel Kelola Kategori, bukan di salinan kategori review (tetap urut kode).
- Minimal satu kategori Aktif harus ada (hapus atau nonaktifkan kategori Aktif terakhir ditolak): Screening 2 membutuhkan kategori, dan seed akan mengisi ulang 4 kategori awal bila tabel kosong.
- Pop-up periksa kembali kategori juga tampil saat Edit (bukan hanya Tambah), sama dengan Panduan. Menyimpan Edit tanpa perubahan tidak menambah Kategori Histori.
- Detail kategori menampilkan versi sebelum tiap perubahan di Kategori Histori; versi terkini (beserta penginput & tanggalnya) hanya tampil di bagian atas — sama dengan Panduan.
- Kolom `kategori_histori` (id, created_by, created_date, updated_by, updated_date, kategori_id, kategori, aktif, kode, deskripsi) diartikan sama dengan `panduan_histori`: `created_by`/`created_date` = pembuat & waktu kategori dibuat, `updated_by`/`updated_date` = penginput & waktu versi itu (yang tampil di Kategori Histori). Baris riwayat yang sudah ada di database lokal disalin dengan arti tersebut (pembuat kategori diambil dari tabel `kategori`).
- Migrasi Alembic lama (0002–0013) dihapus; database baru dibuat langsung dari model dan di-stamp ke `0001_dasar`. Database yang dibuat sebelum 22 Oktober 2026 tidak punya jalur upgrade dan harus dibuat ulang — aplikasi belum dipakai di production, sehingga tidak ada data yang perlu dipindahkan.
- Perubahan kategori ke CRUD per kategori (PRD v2.2–v2.3) memakai revisi Alembic `0002_kategori_per_kategori`, karena database rekan sudah berisi data uji sejak 22 Oktober 2026. Riwayat versi daftar lama tidak dipindah ke Kategori Histori (bentuknya berbeda; jejaknya tetap di audit log), dan kalimat lama "tidak diteruskan" dibuang dari definisi kategori terkini, tetapi tetap ada di salinan review lama (C3).
- Status kategori (PRD v2.3) memakai teks "Aktif/Nonaktif" (bukan "Tidak aktif") agar sama dengan panduan dan komponen saklar; status hanya diatur di form Edit, Tambah selalu Aktif (API tetap menerima `aktif`). Keempat kategori isi awal berstatus Aktif.
- Unit Kerja (Eselon I) disimpan sebagai kolom teks `satker.unit_kerja` (bukan tabel terpisah, keputusan pemilik produk); diketik bebas di form Satker (tanpa daftar saran), jadi Admin perlu menulis nama Unit Kerja secara seragam. Satuan Kerja dan Unit Kerja sama-sama opsional (keputusan pemilik produk); kosong disimpan sebagai teks kosong, bukan NULL, agar halaman lain (usulan, dashboard) yang menampilkan nama Satker tidak perlu diubah.
- Tabel `pengguna` dan `satker` memakai kolom jejak seperti checklist (`created_by`, `create_date`, `update_by`, `update_date`); `update_*` diisi saat data diubah lewat menu Pengguna/Satker, bukan saat login. Data lama/seed: pembuat tidak diketahui → ditampilkan "Sistem". Satker tidak lagi punya kode (kolom database = yang tampil di web); keunikan Satker = pasangan Unit Kerja + Satuan Kerja.
- Data awal Satker diambil dari dokumen "Data Satker dan Unit Kerja" (9 UKE I, 56 UKE II, beserta kodenya; nama pejabat tidak disimpan) dan diisi otomatis bila tabel satker kosong (juga di produksi) atau lewat migrasi 0006 untuk database lama; tabel Satuan Kerja diurutkan menurut kode (01.01, 01.02, …). Akun contoh dev (`pengusul`, `pengusul_b`) memakai Biro Perencanaan (01.04) dan Pusat Data dan Sarana Informatika (01.06).
- Tabel `pengguna` tidak punya kolom nama (keputusan pemilik produk). Di seluruh aplikasi (header, sapaan dashboard, "Dibuat Oleh"/"Diubah Oleh", riwayat, audit) yang tampil adalah username.
- Kode Satuan Kerja mengikuti dokumen: Kode UKE I = 2 digit (`01`), Kode UKE II = `NN.NN` diawali Kode UKE I induknya (`01.04`), dijaga di backend dan CHECK database. Kode UKE I tidak dapat diubah bila Satuan Kerja di bawahnya sudah berkode.
