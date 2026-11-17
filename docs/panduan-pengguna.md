# Panduan Pengguna

Masuk dengan username dan password dari Admin. Menu yang tampil menyesuaikan role Anda. Ganti password lewat menu **Ganti password** di kiri bawah.

**Warna status**:

| Warna | Status |
| --- | --- |
| Abu-abu | Belum direview |
| Biru (berputar) | Antre / Diproses AI |
| Merah tua | Gagal |
| Kuning | Menunggu verifikasi |
| Hijau | Lolos |
| Merah | Tidak lolos |

## Pengusul

Anda hanya melihat usulan milik Satker Anda.

1. **Buat usulan**: buka menu **Usulan › Buat Usulan**. Isi Tahun Anggaran, Kode RO, dan Nama RO, lalu unggah PDF TOR dan RAB (maks. 100 MB per file).
   - **Simpan Draf**: menyimpan tanpa mereview. Draf masih dapat diubah atau dihapus.
   - **Simpan & Ajukan Review**: langsung menjalankan review AI.
2. **Pantau progres**: kolom Status menampilkan posisi antrean atau tahap proses (mis. "Menilai item 3/15"). Anda boleh menutup halaman; proses tetap berjalan. "Menunggu kapasitas AI" berarti server AI belum menyala, dan review tetap aman di antrean.
3. **Lihat Hasil AI**: tersedia begitu AI selesai, ditandai **"Hasil AI — belum diverifikasi reviewer"**.
   - **Label** (LOLOS/TIDAK LOLOS) dan **kategori** rekomendasi.
   - **Checklist**: status setiap item beserta alasan, apa yang kurang, dan **bukti**. Klik bukti untuk membuka PDF di halaman tersebut dengan bagian yang disorot.
   - **Rekomendasi TOR/RAB**: langkah perbaikan beserta dasar panduan.
4. **Hasil final**: setelah reviewer memfinalkan, Anda melihat nilai final (termasuk perubahan reviewer, bertanda ungu "Diubah reviewer") berdampingan dengan nilai AI, serta tab **Catatan Reviewer**.
5. **Unggah revisi** (bila TIDAK LOLOS): klik **Unggah Revisi**. Ganti TOR saja, RAB saja, atau keduanya; dokumen yang tidak diganti terbawa otomatis. Lalu ajukan review lagi.
6. **Gagal**: bila review AI gagal, pesan menampilkan ID pelacakan (laporkan ke Admin). Anda dapat mengganti file lalu klik **Ajukan Ulang**.
7. **Riwayat**: menampilkan semua revisi, siapa memfinalkan, dan tabel perbandingan checklist. Sel hijau berarti item berubah menjadi terpenuhi; sel merah berarti sebaliknya.
8. **Arsip**: usulan yang pernah direview tidak dapat dihapus, tetapi dapat diarsipkan dari halaman Riwayat. Usulan arsip tetap dapat dilihat dengan mencentang "Tampilkan arsip".
9. **Acuan review (lihat saja)**: menu **Panduan**, **Checklist**, dan **Kategori** menampilkan acuan yang dipakai AI. Anda dapat mencari, memfilter, mengurutkan, dan membuka detail beserta riwayatnya, tetapi tidak dapat menambah, mengubah, atau menghapus.

Satu revisi hanya direview AI **sekali**, agar Anda dan reviewer selalu melihat hasil yang sama. Bila dokumen dan acuan identik dengan revisi sebelumnya, hasilnya disalin persis.

## Reviewer

Anda melihat seluruh usulan dan dapat memfilternya per Satker, tahun, status, kategori, atau RO.

1. Dari Dashboard (**Perlu tindakan saya**) atau Daftar Usulan, klik **Periksa Hasil** pada usulan berstatus Menunggu verifikasi.
2. Periksa setiap item checklist dan klik bukti untuk mencocokkannya dengan PDF di panel kanan. Di ponsel atau tablet, PDF tampil di tab **Dokumen**.
3. **Override**: klik **Override** pada item, label, atau kategori, pilih nilai baru, dan **isi alasan (wajib)**.
   - Override item membuat label dihitung ulang otomatis.
   - Bila Anda mengubah label sehingga tidak konsisten dengan checklist, muncul peringatan; jelaskan alasannya.
   - Override dapat **dibatalkan** selama belum final. Riwayatnya tetap tersimpan di tab Riwayat Override.
   - Hasil asli AI tidak pernah diubah dan selalu terlihat (dicoret di sebelah nilai baru).
4. **Catatan Reviewer**: tambahkan catatan umum, catatan TOR, atau catatan RAB untuk Pengusul. Catatan baru terlihat oleh Pengusul setelah final.
5. **Finalkan**: periksa ringkasan, lalu konfirmasi. Hasil terkunci; perubahan hanya dapat dilakukan melalui revisi baru dari Pengusul.

Reviewer tidak dapat menjalankan ulang review AI.

### Mengelola acuan & data master

Reviewer juga mengelola acuan review dan data master. Pengusul dapat melihat Panduan, Checklist, dan Kategori tanpa dapat mengubahnya; Satuan Kerja dan Master RO khusus Reviewer.

- **Checklist**: tabel item dengan tombol **Tambah Item** dan **Atur Urutan**, serta ikon Detail, Edit, dan Hapus per item. Setiap perubahan tercatat di riwayat item.
- **Kategori**: tabel berisi Kode, Kategori, Status (Aktif/Nonaktif), Deskripsi, Diinput Oleh, Tanggal Input, dan Aksi (ikon mata = Detail, pensil = Edit, tempat sampah = Hapus). **Tanggal Input** berisi tanggal dan jam, sama seperti Checklist.
  - **Atur Urutan** (kanan atas): seret baris atau pakai tombol naik/turun, lalu klik **Simpan Urutan**. Kategori baru otomatis ditempatkan setelah kode sebelumnya.
  - **Tambah Kategori** (kanan atas) dan **Edit** membuka halaman form: Kode, Kategori, dan Deskripsi. Form **Edit** juga memuat saklar **Status** (kategori baru selalu Aktif). Sebelum disimpan tampil pop-up untuk memeriksa kembali isian.
  - **Detail** menampilkan data terkini serta tabel **Kategori Histori**: isi kategori sebelum tiap perubahan, tanggal input, dan akun yang menginput.
  - **Hapus** bersifat permanen (kategori beserta riwayatnya). Hasil review lama tetap menampilkan kategori yang dipakai saat itu. Minimal satu kategori Aktif harus ada.
  - Perubahan dipakai AI mulai review berikutnya; review yang sedang berjalan atau sudah selesai tidak terpengaruh.
  - Hanya kategori **Aktif** yang dipakai AI pada review berikutnya. Kategori **Nonaktif** tetap tampil dan dapat diaktifkan kembali lewat Edit tanpa dihapus.
- **Filter & sorting** (Panduan, Checklist, Kategori, Satuan Kerja, Master RO, dan Pengguna milik Admin): kartu **Form Filter Pencarian** di atas tabel awalnya ter-minimize; klik judul kartu untuk membuka isiannya dan klik lagi untuk me-minimize; form berisi kotak cari dan pilihan filter sesuai isi tabel (satu filter per kolom tabel, urut sesuai kolom: Nama Acuan, Nama Dokumen, Deskripsi, Status, Diinput Oleh, dan Tanggal Input di Panduan; Kode, Checklist, Kriteria Lolos, Berlaku Untuk, Status, Diinput Oleh, dan Tanggal Input di Checklist; Kode, Kategori, Status, Deskripsi, Diinput Oleh, dan Tanggal Input di Kategori; Kode UKE I, Unit Kerja, Kode UKE II, Satuan Kerja, Status, Diinput Oleh, dan Tanggal Input di Satuan Kerja — urut sesuai kolom tabel; semua kolom tabel di Master RO (Kode Program, Program, Kode Kegiatan, Kegiatan, Kode KRO, KRO, Kode RO, RO, Status, Diinput Oleh, Tanggal Input) — urut sesuai kolom tabel; semuanya kotak cari kecuali Status (pilihan) dan Tanggal Input (pilih tanggal); Role dan Login Terakhir di Pengguna). Filter tanggal berisi satu tanggal dan menampilkan data pada tanggal itu. Isian baru berlaku setelah klik **Terapkan** (menekan Enter tidak menerapkan filter); **Reset** (ikon putar balik) menampilkan kembali semua data. Klik judul kolom untuk mengurutkan: sekali naik, dua kali turun, tiga kali kembali ke urutan bawaan.
- **Panduan**: ditampilkan sebagai tabel (No, Nama Acuan, Nama Dokumen, Deskripsi, Status, Diinput Oleh, Tanggal Input, Aksi; Nama Dokumen = nama file PDF; Diinput Oleh dan Tanggal Input menunjukkan input/perubahan terakhir). Klik **Nama Acuan** untuk membuka PDF-nya.
  - Kolom **Aksi** berisi ikon (arahkan kursor untuk melihat namanya): **Lihat detail** (ikon mata, semua pengguna) membuka halaman berisi data lengkap panduan dan **Panduan Histori**-nya; **Edit** (ikon pensil) dan **Hapus** (ikon tempat sampah) khusus Reviewer.
  - **Atur Urutan** (kanan atas, khusus Reviewer): seret baris atau pakai tombol naik/turun, lalu klik **Simpan Urutan**. Urutan ini menjadi urutan bawaan tabel Panduan. Panduan yang baru diunggah ditempatkan di urutan paling akhir.
  - **Unggah Panduan** membuka halaman form: Nama Acuan, Deskripsi, Status, dan file PDF. Setelah file dipilih, klik **Pratinjau** pada baris file untuk membuka PDF di jendela pop-up (bisa diperbesar dan dipindah halaman) agar file dapat diperiksa sebelum diunggah; file yang rusak langsung ditandai. Tombol **Reset** mengosongkan semua isian (termasuk PDF) dan mengembalikan Status ke Aktif. **Edit** membuka halaman form untuk mengubah Nama Acuan, Deskripsi, dan Status; file tidak dapat diganti (unggah panduan baru bila perlu).
  - Saat **Unggah** atau **Simpan** (Edit), muncul pop-up **Periksa kembali** berisi ringkasan isian. Klik **Ya, simpan** untuk menyimpan, atau **Periksa kembali** untuk kembali ke form.
  - File diproses otomatis setelah diunggah (status pemrosesan tidak ditampilkan di daftar maupun detail). Hanya panduan yang selesai diproses dan berstatus **Aktif** yang dipakai review berikutnya.
  - **Status** Aktif/Nonaktif diatur saat unggah atau lewat **Edit**, tanpa menghapus panduan. Setiap perubahan (termasuk status) tercatat sebagai versi baru di Panduan Histori.
  - Mengubah nama atau deskripsi lewat **Edit** membuat versi baru; halaman **Lihat detail** menampilkan data panduan dengan tombol **Lihat PDF**, tanggal input, dan akun yang menginput, serta tabel **Panduan Histori** berisi versi-versi **sebelum** perubahan terakhir (tanggal input, akun yang menginput, status, nama, dan deskripsi). Versi terkini hanya tampil di bagian atas.
  - **Hapus** (setelah konfirmasi di pop-up berisi ringkasan panduan, tombol merah **Ya, hapus**) menghapus panduan secara **permanen** dari database, termasuk Panduan Histori dan file PDF-nya, dan tidak dapat dikembalikan. Hasil review lama kehilangan rujukan ke panduan tersebut. Untuk sekadar tidak memakainya di review berikutnya, ubah Status menjadi **Nonaktif** lewat Edit.
  - Bila pemrosesan gagal, pesan merah tampil di bawah nama (khusus Reviewer) dan ikon **Proses ulang** muncul di kolom Aksi.
  - Halaman hasil review menampilkan daftar panduan yang dipakai beserta nomor versinya (mis. "PMK Standar Biaya (v2)"); catatan ini tidak berubah walaupun panduan diedit kemudian.
- **Satuan Kerja**: daftar Satuan Kerja (UKE II / Eselon II) beserta Unit Kerja (UKE I / Eselon I)-nya, lengkap dengan kodenya, Status, Diinput Oleh, dan Tanggal Input; data awal sesuai dokumen "Data Satker dan Unit Kerja". Tabel menampilkan 20 data per halaman, dengan tombol ‹ › dan nomor halaman di kiri bawah serta pilihan **Tampilkan baris** (10, 20, 50, atau 100) di kanan bawah, sama seperti Master RO. Tambah/Ubah memilih jenis: Unit Kerja (kode & nama) atau Satuan Kerja (Unit Kerja induk, nama, kode NN.NN). Satuan Kerja yang masih dipakai pengguna atau usulan tidak dapat dihapus. Admin memilih Satuan Kerja dari daftar ini saat membuat akun Pengusul.
- **Master RO** (di menu, tepat sebelum Satuan Kerja): data berjenjang **Program → Kegiatan → KRO → RO** dalam satu tabel seperti Satuan Kerja, dengan kolom Kode Program, Program, Kode Kegiatan, Kegiatan, Kode KRO, KRO, Kode RO, RO, Status, Diinput Oleh, dan Tanggal Input. Tabel menampilkan 20 data per halaman. Di kiri bawah tabel ada tombol ‹ › dan nomor halaman, dan di kanan bawah ada pilihan **Tampilkan baris** (10, 20, 50, atau 100).
  - **Tambah Master RO** (kanan atas) membuka halaman form seperti form Satuan Kerja: pilih **Jenis** (Program, Kegiatan, KRO, atau RO), pilih induknya (Kegiatan di bawah Program, KRO di bawah Kegiatan, RO di bawah KRO), lalu isi Kode dan Nama. Mengganti Jenis mengosongkan isian. Pada **Edit**, Jenis tampil tetapi tidak dapat diubah. Kode berupa teks bebas (huruf, angka, atau tanda baca; maks. 50 karakter) dan disimpan persis seperti yang diketik. Kode tidak boleh sama dengan saudara di induk yang sama (kode RO yang sama boleh dipakai di KRO berbeda). Nama Program diawali kata "Program", dan nama RO tidak boleh sama dalam satu KRO. Saat mengisi KRO, kode yang ada di Lampiran II SEB mengisi nama KRO otomatis dan menampilkan satuannya. Kode di luar Lampiran II tetap dapat disimpan dengan peringatan. Halaman Detail menampilkan kode & nama tiap jenjang, Status, Diinput Oleh, dan Tanggal Input. Tombol **Reset** mengosongkan isian.
  - Pada instalasi baru Master RO masih kosong: isi berurut mulai dari **Program**, lalu Kegiatan, KRO, dan RO.
  - **Import Excel** (di samping Tambah Master RO): unggah file Excel (.xlsx) berkolom `kode_program`, `program`, `kode_kegiatan`, `kegiatan`, `kode_kro`, `kro`, `kode_ro`, `ro` (baris pertama = judul kolom, urutan bebas). Satu baris Excel = satu baris tabel Master RO; Program/Kegiatan/KRO yang belum ada dibuat otomatis. Bila ada baris yang salah, tidak ada data yang di-import dan kesalahannya ditampilkan per nomor baris, sehingga file dapat diperbaiki lalu di-import ulang. Meng-import file yang sama dua kali tidak membuat data ganda.
  - Kolom tabel: No, Kode Program, Program, Kode Kegiatan, Kegiatan, Kode KRO, KRO, Kode RO, RO, dan ikon Detail, Edit, Hapus. Setiap baris adalah satu data beserta induk-induknya (mis. baris Kegiatan mengisi kolom Program dan Kegiatan; kolom KRO dan RO berisi "—"). Data yang paling baru ditambahkan tampil paling atas; data yang ditambahkan bersamaan (data awal atau satu kali Import Excel) tersusun berjenjang: Program diikuti Kegiatan-nya, lalu KRO, lalu RO. Data Nonaktif tampil abu-abu dengan label Nonaktif.
  - Filter berurutan sesuai kolom: Program, Kegiatan, KRO (pilih), RO (cari kode/nama), lalu Status.
  - **Edit** dapat mengubah induk, kode, nama, dan **Status**. Data **Nonaktif** tetap tampil tetapi tidak dapat dipilih sebagai induk data baru.
  - **Hapus** bersifat permanen dan ditolak bila data masih memiliki turunan; hapus atau pindahkan turunannya terlebih dahulu.

## Admin

Admin hanya mengelola akun dan sistem; Admin tidak memiliki menu Dashboard, Usulan, maupun acuan review. Setelah login, Admin langsung diarahkan ke menu **Pengguna**. Lihat [panduan-admin.md](panduan-admin.md) untuk administrasi teknis.

- **Pengguna**: buat akun, pilih satu role (Pengusul, Reviewer, atau Admin), dan hubungkan Pengusul ke Satuan Kerja (wajib, dipilih dari daftar yang dikelola Reviewer). Anda juga dapat mengubah, menonaktifkan, atau menghapus akun, serta mereset password. Satker tempat Reviewer bernaung mengusulkan dengan **akun Pengusul tersendiri**.
- **Node AI**: memantau server AI yang terhubung, mendaftarkan node GPU sewaan (token sekali tampil), dan mencabut akses.
- **Audit Log**: aktivitas pengguna (login, perubahan master, override, finalisasi, dll.), dapat difilter, dengan detail data sebelum dan sesudah.
