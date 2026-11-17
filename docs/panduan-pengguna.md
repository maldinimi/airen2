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

1. **Usulan**: halaman pertama menampilkan histori usulan (No, Satuan Kerja, Rincian Output, Dokumen, Status, Tanggal Pengajuan, Aksi). Klik nama dokumen untuk membuka PDF-nya. **Form Filter Pencarian Usulan** di atas tabel (klik judulnya untuk membuka): isi Satuan Kerja, Rincian Output, Dokumen, Status (Lolos, Menunggu Reviewer, Tidak Lolos), dan/atau Tanggal Pengajuan (dd/mm/yyyy, atau pilih dari ikon kalender), lalu klik **Terapkan**; **Reset** mengosongkan semua. Klik judul kolom untuk mengurutkan naik/turun. Pilihan **Tahun** di bilah atas menyaring daftar ini. Aksi untuk Pengusul: **Detail** (ikon mata); saat Gagal juga **Edit**.
2. **Pengajuan Baru** (kanan atas) membuka halaman form. Usulan dicatat pada **Tahun Anggaran** yang sedang dipilih di bilah atas (tertulis di bawah judul form):
   - **A. Parameter Hierarki Anggaran RKA-K/L**: pilih Program, lalu Kegiatan, KRO, dan RO (semuanya wajib; pilihan berikutnya muncul setelah tingkat di atasnya dipilih).
   - **B. Klasifikasi Kategori Usulan**: pilih Kategori; Deskripsi terisi otomatis.
   - **C. Unggah Berkas Dokumen**: PDF TOR **dan** RAB (keduanya wajib, maks. 100 MB per file).
   - Klik **Kirim Pengajuan**. Isian wajib yang belum diisi ditandai merah. Bila lengkap, muncul "Apakah Anda Yakin?" → **Ya**; usulan langsung masuk antrean review AI.
3. **Pantau progres**: kolom Status menampilkan posisi antrean atau tahap proses. Anda boleh menutup halaman; proses tetap berjalan.
4. **Detail** (ikon mata): parameter hierarki dan **Histori Dokumen** (satu baris per revisi, urut dari revisi 1, dengan Tanggal Pengajuan dan Tanggal Verifikasi). Klik ikon mata pada baris revisi untuk melihat hasil pemeriksaan; bila revisi terbaru Tidak Lolos, tombolnya bertuliskan **Revisi**.
5. **Hasil pemeriksaan**: hasil AI dapat dilihat begitu AI selesai — label AI, tabel checklist dengan catatan AI (alasan AI beserta bukti & rujukan; klik untuk membuka PDF di halaman yang dirujuk), Rujukan Checklist (nama acuan), dan rekomendasi AI. Status & catatan verifikator serta **Keputusan Akhir** muncul setelah reviewer memfinalkan.
6. **Unggah Revisi** (bila Tidak Lolos): di Detail, klik **Revisi** pada revisi terbaru, lalu klik **Unggah Revisi** di paling bawah halaman pemeriksaan. Unggah PDF TOR, RAB, atau keduanya; dokumen yang tidak diganti terbawa otomatis. **Edit** (ikon pensil) hanya tersedia saat Gagal untuk mengganti dokumen lalu mengirim ulang.
7. **Gagal**: bila review AI gagal, pesan menampilkan ID pelacakan (laporkan ke Admin).
8. **Hapus** usulan dilakukan oleh Reviewer. Bila hierarki anggaran atau kategori salah input, hubungi Reviewer untuk membetulkannya (Edit) atau menghapus usulan.

Satu revisi hanya direview AI **sekali**, agar Anda dan reviewer selalu melihat hasil yang sama. Bila dokumen dan acuan identik dengan revisi sebelumnya, hasilnya disalin persis.

## Reviewer

Anda melihat seluruh usulan dan dapat memfilternya per Satker, tahun, status, kategori, atau RO.

1. Di halaman Usulan, aksi Reviewer: **Detail** (ikon mata), **Edit** (betulkan hierarki anggaran & kategori, dan bila perlu unggah TOR/RAB pengganti — dokumen diganti pada revisi yang sama, lalu langsung direview AI ulang), dan **Hapus**. Buka usulan berstatus Menunggu verifikasi, lalu klik **Review** pada revisi terbaru di **Histori Dokumen**.
2. Halaman Pemeriksaan menampilkan label **AI**, **Verifikator** (Lolos/Ditolak), dan **Jumlah Checklist** (lolos/total) yang langsung berubah saat Anda memeriksa. Status Verifikator setiap item sudah terisi mengikuti AI; ubah dengan saklar **Lolos**/**Ditolak** (keterangan "*Diubah dari AI" muncul bila berbeda). Tulis **Catatan Verifikator** langsung di kotaknya. Penilaian belum tersimpan sampai Anda klik **Simpan Sebagai Draf** atau **Finalkan Keputusan** — bila halaman dimuat ulang sebelum itu, penilaian kembali ke draf terakhir.
3. **Kategori** (di atas Keputusan Akhir): bandingkan Kategori Usulan (pilihan Pengusul) dengan rekomendasi AI beserta catatan dan rujukannya. Kolom **Verifikator** sudah terisi mengikuti AI; ubah bila perlu dan tulis Catatan Verifikator. Tersimpan bersama Simpan Sebagai Draf/Finalkan.
4. **Keputusan Akhir**: pilih **LOLOS** atau **TIDAK LOLOS** dan isi catatan akhir. **Simpan Sebagai Draf** menyimpan seluruh penilaian tanpa mengunci. **Finalkan Keputusan** → "Apakah Anda Yakin?" → **Ya** menyimpan dan mengunci hasil, lalu menampilkannya ke Pengusul.
5. Bukti & rujukan setiap item ada di kolom **Catatan AI**: klik untuk membuka PDF di halaman yang dirujuk dengan bagian yang disorot.
6. Catatan verifikator dan catatan akhir terlihat oleh Pengusul setelah final. Hasil asli AI tidak pernah diubah dan tetap ditampilkan di samping penilaian verifikator. Setelah final, perubahan hanya melalui revisi baru dari Pengusul.

Reviewer tidak dapat menjalankan ulang review AI.

## Admin

Lihat [panduan-admin.md](panduan-admin.md) untuk administrasi teknis. Fitur di aplikasi:

- **Checklist**: tabel item dengan tombol **Tambah Item** dan **Atur Urutan**, serta ikon Detail, Edit, dan Hapus per item. Setiap perubahan tercatat di riwayat item.
- **Kategori**: tabel berisi Kode, Kategori, Status (Aktif/Nonaktif), Deskripsi, dan Aksi (ikon mata = Detail, pensil = Edit, tempat sampah = Hapus). Klik judul kolom **Status** lalu pilih urutan: **Default** (urutan hasil Atur Urutan), **Aktif** (Aktif di atas), atau **Nonaktif** (Nonaktif di atas).
  - **Atur Urutan** (kanan atas): seret baris atau pakai tombol naik/turun, lalu klik **Simpan Urutan**. Kategori baru otomatis ditempatkan setelah kode sebelumnya.
  - **Tambah Kategori** (kanan atas) dan **Edit** membuka halaman form: Kode, Kategori, dan Deskripsi. Form **Edit** juga memuat saklar **Status** (kategori baru selalu Aktif). Sebelum disimpan tampil pop-up untuk memeriksa kembali isian.
  - **Detail** menampilkan data terkini serta tabel **Kategori Histori**: isi kategori sebelum tiap perubahan, tanggal input, dan akun yang menginput.
  - **Hapus** bersifat permanen (kategori beserta riwayatnya). Hasil review lama tetap menampilkan kategori yang dipakai saat itu. Minimal satu kategori Aktif harus ada.
  - Perubahan dipakai AI mulai review berikutnya; review yang sedang berjalan atau sudah selesai tidak terpengaruh.
  - Hanya kategori **Aktif** yang dipakai AI pada review berikutnya. Kategori **Nonaktif** tetap tampil dan dapat diaktifkan kembali lewat Edit tanpa dihapus.
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
