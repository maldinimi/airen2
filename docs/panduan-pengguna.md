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

Label **"Tidak diteruskan"** menandai kategori K4.

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

## Admin

Lihat [panduan-admin.md](panduan-admin.md) untuk administrasi teknis. Fitur di aplikasi:

- **Checklist / Kategori**: tambah, ubah, hapus, dan urutkan item pada draf, lalu klik **Simpan sebagai versi baru** (sertakan catatan perubahan). Tab **Daftar versi** menampilkan isi setiap versi. Review yang sedang berjalan atau sudah selesai tidak terpengaruh.
  - Kategori dengan centang "Diteruskan" dihapus akan ditandai "Tidak diteruskan".
- **Panduan**: ditampilkan sebagai tabel (No, Nama Acuan, Deskripsi, Status, Diinput Oleh, Tanggal Input, Aksi; keduanya menunjukkan input/perubahan terakhir). Klik **Nama Acuan** untuk membuka PDF-nya. Klik judul kolom **Status** lalu pilih urutan: **Default** (urut nama), **Aktif** (Aktif di atas), atau **Nonaktif** (Nonaktif di atas).
  - Kolom **Aksi** berisi ikon (arahkan kursor untuk melihat namanya): **Lihat detail** (ikon mata, semua pengguna) membuka halaman berisi data lengkap panduan dan **Panduan Histori**-nya; **Edit** (ikon pensil) dan **Hapus** (ikon tempat sampah) khusus Admin.
  - **Unggah Panduan** membuka halaman form: Nama Acuan, Deskripsi, Status, dan file PDF. Setelah file dipilih, klik **Pratinjau** pada baris file untuk membuka PDF di jendela pop-up (bisa diperbesar dan dipindah halaman) agar file dapat diperiksa sebelum diunggah; file yang rusak langsung ditandai. Tombol **Reset** mengosongkan semua isian (termasuk PDF) dan mengembalikan Status ke Aktif. **Edit** membuka halaman form untuk mengubah Nama Acuan, Deskripsi, dan Status; file tidak dapat diganti (unggah panduan baru bila perlu).
  - Saat **Unggah** atau **Simpan** (Edit), muncul pop-up **Periksa kembali** berisi ringkasan isian. Klik **Ya, simpan** untuk menyimpan, atau **Periksa kembali** untuk kembali ke form.
  - Status pemrosesan file **Antre → Diproses → Siap** tampil di bawah nama. Hanya panduan **Siap** dan berstatus **Aktif** yang dipakai review berikutnya.
  - **Status** Aktif/Nonaktif diatur saat unggah atau lewat **Edit**, tanpa menghapus panduan. Setiap perubahan (termasuk status) tercatat sebagai versi baru di Panduan Histori.
  - Mengubah nama atau deskripsi lewat **Edit** membuat versi baru; halaman **Lihat detail** menampilkan data panduan dengan tombol **Lihat PDF**, tanggal input, dan akun yang menginput, serta tabel **Panduan Histori** berisi versi-versi **sebelum** perubahan terakhir (tanggal input, akun yang menginput, status, nama, dan deskripsi). Versi terkini hanya tampil di bagian atas.
  - **Hapus** (setelah konfirmasi di pop-up berisi ringkasan panduan, tombol merah **Ya, hapus**) menghapus panduan secara **permanen** dari database, termasuk Panduan Histori dan file PDF-nya, dan tidak dapat dikembalikan. Hasil review lama kehilangan rujukan ke panduan tersebut. Untuk sekadar tidak memakainya di review berikutnya, ubah Status menjadi **Nonaktif** lewat Edit.
  - Panduan berstatus Gagal dapat diproses ulang.
  - Halaman hasil review menampilkan daftar panduan yang dipakai beserta nomor versinya (mis. "PMK Standar Biaya (v2)"); catatan ini tidak berubah walaupun panduan diedit kemudian.
- **Satker**: daftar Satuan Kerja (UKE II / Eselon II) beserta Unit Kerja (UKE I / Eselon I)-nya, lengkap dengan kodenya; data awal sesuai dokumen "Data Satker dan Unit Kerja". Tambah/Ubah memilih jenis: Unit Kerja (kode & nama) atau Satuan Kerja (Unit Kerja induk, nama, kode NN.NN). Satuan Kerja yang masih dipakai pengguna atau usulan tidak dapat dihapus.
- **Pengguna**: buat akun, pilih satu atau beberapa role, dan hubungkan Pengusul ke Satker (wajib, dipilih dari menu Satker). Anda juga dapat menonaktifkan akun atau mereset password. Satker tempat Reviewer bernaung mengusulkan dengan **akun Pengusul tersendiri**.
- **Node AI**: memantau server AI yang terhubung, mendaftarkan node GPU sewaan (token sekali tampil), dan mencabut akses.
- **Dashboard**: menampilkan panjang antrean, node aktif, dan perkiraan waktu selesai, sebagai dasar memutuskan penambahan atau pematian node GPU.
- **Audit Log**: aktivitas pengguna (login, perubahan master, override, finalisasi, dll.), dapat difilter, dengan detail data sebelum dan sesudah.
