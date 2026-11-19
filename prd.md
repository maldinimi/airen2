# PRD — Asisten AI Offline untuk Review Dokumen TOR & RAB

**Status:** Disetujui | **Pemilik:** Maldini | **Versi:** 2.5 | **Tanggal:** 2026-11-18 (v1: 2026-10-12, v2: 2026-10-20, v2.1: 2026-10-21, v2.2: 2026-10-26, v2.3: 2026-10-26, v2.4: 2026-11-09)

**Perubahan v2 (2026-10-20):** Modul D — Acuan direvisi berdasarkan keputusan pemilik produk: unggah satu file per form dengan Nama Acuan, Deskripsi, dan Status; status Aktif/Nonaktif; edit tanpa ganti file; hapus permanen; daftar berupa tabel; halaman detail dengan riwayat versi; data terkini disimpan terpisah dari riwayat versi; catatan acuan pada review tidak berubah walaupun acuan diedit (D2, D4–D9, §7.3, §9).

**Perubahan v2.1 (2026-10-21):** Modul D — riwayat versi pada detail acuan disebut **Acuan Histori**; form unggah dilengkapi **pratinjau PDF** sebelum diunggah dan tombol **Reset**; Nama Acuan maksimal 500 karakter; konfirmasi hapus menampilkan ringkasan acuan yang akan dihapus; file yang pemrosesannya terhenti ditandai gagal agar dapat diproses ulang; penjelasan data yang ikut terhapus (D2, D4, D6, D9, §9).

**Perubahan v2.2 (2026-10-26):** Modul C — Kategori direvisi berdasarkan keputusan pemilik produk: kategori dikelola satu per satu (tidak lagi sebagai versi seluruh daftar); daftar berupa tabel; tambah, edit, dan detail di halaman tersendiri; riwayat per kategori disebut **Kategori Histori**; hapus permanen; setiap review menyimpan salinan kategori yang dipakai dan menampilkan definisinya (C1, C3, C5–C8, input Screening 1, §7.3, §9).

**Perubahan v2.3 (2026-10-26):** Modul C — kategori memakai **Status Aktif/Nonaktif** seperti acuan: kategori Nonaktif tetap tampil tetapi tidak dipakai review berikutnya; kolom Status di daftar kategori; status diatur saat Edit (kategori baru selalu Aktif); definisi keempat kategori isi awal tidak lagi menetapkan status, karena dipakai atau tidaknya kategori mana pun ditentukan lewat Status (C1, C3, C5–C8, §7.2).

**Perubahan v2.4 (2026-11-09):** Modul A & verifikasi direvisi: pengajuan diajukan lewat halaman **Pengajuan Baru** berisi **hierarki anggaran RKA-K/L** (Program → Kegiatan → KRO → RO, dipilih dari daftar Renja), **kategori pengajuan**, dan unggah **TOR dan/atau RAB** (minimal satu), lalu langsung direview AI; halaman Pengajuan berupa histori pengajuan; halaman **Detail** pengajuan dengan **Histori Dokumen** per revisi; halaman **Pemeriksaan** dengan jumlah checklist Lolos/Tidak Lolos (AI dan verifikator), tabel checklist, serta kartu **Keputusan Akhir**; Pengusul baru melihat hasil setelah diverifikasi; edit/revisi hanya mengganti PDF; Satker dapat **menghapus** usulannya sendiri (mis. karena salah input) lalu mengajukan ulang (Glosarium, §4, §5, A1–A8, Screening 1, Override & Finalisasi, §7.3, §9).

**Perubahan v2.5 (2026-11-18):** Modul A — Pengajuan Baru wajib mengunggah **TOR dan RAB** (keduanya); revisi dan penggantian dokumen tetap boleh TOR saja, RAB saja, atau keduanya. Pilihan hierarki anggaran mengikuti data **Master RO** (Modul F) yang Aktif, bukan daftar tetap: data Nonaktif, atau yang induknya Nonaktif, tidak dapat dipilih, sedangkan pengajuan yang sudah diajukan tetap menyimpan pilihannya. Master RO dapat diisi dari file Excel dan tidak membawa data bawaan (F5). Hak kelola pengajuan pindah ke Reviewer: Reviewer membetulkan hierarki anggaran dan kategori (dan bila perlu mengganti TOR/RAB) lewat **Edit**, dan hanya Reviewer yang dapat **menghapus** pengajuan. Pengusul membaca hasil review AI segera setelah selesai; penilaian verifikator setelah final. Halaman Riwayat/Perbandingan dan fitur arsip dihapus; riwayat revisi tampil di Histori Dokumen. Mengganti password mengakhiri sesi di perangkat lain (§4, §5, A3, A5, A7, A8, F5, §8). Revisi berikutnya: revisi setelah Tidak Lolos wajib mengunggah TOR dan RAB; Edit Reviewer terkunci setelah pengajuan diverifikasi (terbuka lagi setelah revisi baru); Tanggal Pengajuan mengikuti unggahan terakhir; tombol "Revisi" Pengusul menjadi "Perbaiki"; mengganti Tahun Anggaran di halaman menu Pengajuan kembali ke daftar Pengajuan (di menu lain halaman tetap) (§5, A2, A3, O).

---

## 0. Cara Membaca Dokumen Ini (untuk AI Agent)

- Dokumen ini menjelaskan **APA** yang dibutuhkan dan **MENGAPA**. Pilihan teknologi, arsitektur, desain database fisik, dan pipeline AI **sepenuhnya ditentukan oleh Anda** (lihat §11).
- Kata **WAJIB** = tidak dapat ditawar. Kata **SEBAIKNYA** = diharapkan, boleh disesuaikan dengan alasan yang jelas.
- Keputusan teknis (§11) sudah ditetapkan dan disetujui di **`desain.md`**. Ikuti dokumen tersebut.
- Jika ada hal kecil yang tidak diatur di dokumen ini maupun di `desain.md`, gunakan asumsi yang wajar dan catat asumsinya (lihat `CLAUDE.md`). Jangan berhenti untuk bertanya kecuali hal tersebut bertentangan dengan ketentuan WAJIB.
- Tahapan kerja pada §12.

### Glosarium

| Istilah | Arti |
| --- | --- |
| **TOR** | *Term of Reference* / Kerangka Acuan Kerja. Dokumen naratif yang menjelaskan latar belakang, tujuan, ruang lingkup, dan keluaran suatu kegiatan. Rata-rata ±50 halaman. |
| **RAB** | Rencana Anggaran Biaya. Rincian biaya kegiatan, umumnya berbentuk tabel. Rata-rata ±10 halaman. |
| **RO** | Rincian Output. Unit keluaran kegiatan yang diusulkan anggarannya. Satu pengajuan (TOR dan RAB) = satu RO. |
| **Hierarki anggaran RKA-K/L** | Jenjang Program → Kegiatan → Klasifikasi Rincian Output (KRO) → Rincian Output (RO), mengikuti Rencana Kerja (Renja) kementerian dan dikelola di menu **Master RO**. Dipilih Pengusul saat Pengajuan Baru. |
| **Satker** | Satuan Kerja. Unit organisasi yang mengusulkan RO. |
| **Pengajuan** | Dokumen TOR dan RAB untuk satu RO, beserta hierarki anggaran, kategori pengajuan, serta seluruh riwayat revisi dan review-nya. |
| **Checklist** | Daftar hal yang wajib dipenuhi/dijawab oleh TOR dan RAB. |
| **Acuan** | Kumpulan PDF referensi (peraturan, kebijakan, standar biaya, dsb.) yang wajib dirujuk AI. Setiap acuan memiliki **Nama Acuan**, deskripsi, dan status **Aktif/Nonaktif**. |
| **Acuan Histori** | Riwayat versi sebuah acuan: isi acuan sebelum tiap perubahan (nama, deskripsi, status), beserta tanggal dan penginputnya. |
| **Kategori** | Klasifikasi prioritas anggaran RO: K1, K2, K3, K4. |
| **Kategori Histori** | Riwayat sebuah kategori: isi kategori sebelum tiap perubahan (kode, nama, deskripsi, status Aktif/Nonaktif), beserta tanggal dan penginputnya. |
| **Screening 1** | Penilaian AI terhadap pemenuhan checklist → label LOLOS / TIDAK LOLOS + alasan + rekomendasi. |
| **Screening 2** | Rekomendasi kategori (K1–K4) oleh AI untuk RO tersebut. |
| **Override** | Tindakan reviewer mengubah hasil AI. |
| **Verifikator** | Sebutan Reviewer (ROCAN) saat menilai ulang setiap item checklist: **Status Verifikator** (Lolos/Tidak Lolos) dan **Catatan Verifikator**. |
| **Keputusan Akhir** | Putusan verifikator atas pengajuan (LOLOS/TIDAK LOLOS) beserta catatan akhir; mengunci hasil review. |

---

## 1. Latar Belakang & Masalah

Instansi pemerintah mengajukan program dan anggaran dengan dokumen pendukung berupa TOR dan RAB. Saat ini review dokumen tersebut dilakukan **manual**, sehingga:

1. **Lambat.** Satu TOR berisi ±50 halaman dan harus dicocokkan dengan banyak peraturan.
2. **Subjektif.** Hasil review berbeda-beda antar-reviewer.
3. **Tersebar.** Peraturan, kebijakan, dan standar yang menjadi acuan jumlahnya banyak.
4. **Tidak terlacak.** Belum ada riwayat perbaikan dokumen.
5. **Sulit menentukan prioritas anggaran.**

Dokumen bersifat **sensitif**, sehingga tidak boleh diproses oleh layanan di luar lingkungan instansi.

## 2. Tujuan

1. Proses review yang **seragam, cepat, dan akurat** dengan tetap merujuk peraturan, kebijakan, dan standar (Acuan).
2. **Rekomendasi perbaikan yang konkret** agar dokumen dapat LOLOS.
3. **Riwayat perbaikan** TOR & RAB yang rapi dan **dapat difilter berdasarkan Satker**.
4. **Rekomendasi kategori prioritas anggaran** (K1–K4) untuk setiap RO.
5. Keputusan akhir tetap di tangan **manusia (reviewer)**. AI berperan sebagai asisten.

---

## 3. Batasan Mutlak (WAJIB)

| # | Batasan | Penjelasan |
| --- | --- | --- |
| B1 | **100% offline** | Seluruh pemrosesan (AI, OCR, embedding, dll.) berjalan lokal. Tidak boleh ada panggilan ke OpenAI, Google, Anthropic, atau layanan eksternal mana pun, termasuk telemetri/analytics dan CDN saat runtime. Aplikasi harus tetap berfungsi penuh tanpa koneksi internet. **Toleransi:** komponen AI boleh dijalankan di **GPU yang disewa dari penyedia cloud publik** (sewa infrastruktur, bukan layanan AI pihak ketiga), karena model tetap berjalan di mesin yang dikendalikan instansi dan data tidak otomatis dapat dibaca penyedia. Syaratnya: database dan file asli tetap di server instansi, hubungan ke GPU sewaan terenkripsi, dan tidak ada dokumen yang tertinggal di mesin sewaan setelah diproses. |
| B2 | **Akurasi review** | Akurasi adalah prioritas utama, di atas kecepatan. AI harus menalar secara mendalam (*deep thinking*), bukan sekadar mencocokkan kata kunci. |
| B3 | **PDF multi-modal** | TOR, RAB, dan Acuan dapat berisi teks, tabel, gambar, grafik/chart, diagram, dan **hasil scan**. Semuanya harus dapat dibaca dan dipahami. |
| B4 | **Production-ready** | Kode rapi, terstruktur, efisien, mengikuti *best practice* terkini, andal, mudah dipelihara. Bukan prototipe. Kode **WAJIB** dilengkapi **dokumentasi** dan **logging** yang rapi, mudah ditelusuri, dan mudah dipelihara (rincian di §8.1). |
| B5 | **UI modern & responsif** | Tampil baik di desktop, tablet, dan ponsel. Intuitif, profesional, menarik. |
| B6 | **Bahasa Indonesia** | Seluruh antarmuka dan seluruh keluaran AI (alasan, rekomendasi) dalam Bahasa Indonesia. |
| B7 | **Berbasis kontainer** | Seluruh komponen (aplikasi, database, layanan AI, model) **WAJIB** berjalan di kontainer (Docker atau sejenisnya). Aplikasi kemungkinan dijalankan di server dan GPU yang disediakan sesuai kebutuhan (*on demand*), sehingga harus dapat dipindah dan dijalankan di berbagai lingkungan dengan langkah minimal. **Kemudahan menjalankan adalah kunci**: developer baru harus dapat menjalankan aplikasi lengkap dengan satu perintah dan acuan singkat. |

---

## 4. Pengguna & Hak Akses

Aplikasi **WAJIB** memiliki login dan pembatasan akses per role.

| Role | Tanggung jawab | Akses data |
| --- | --- | --- |
| **Pengusul** (penginput TOR & RAB) | Membuat **Pengajuan Baru** (hierarki anggaran, kategori, TOR dan RAB) yang langsung menjalankan review AI, memantau status, membaca **hasil review AI** (segera setelah selesai) dan **hasil final** dari reviewer, serta mengunggah revisi. | Hanya pengajuan milik Satker-nya. |
| **Reviewer** (verifikator/ROCAN) | Memeriksa hasil review AI, mengisi **Status & Catatan Verifikator** per item, melakukan **override**, memberi catatan, dan menetapkan **Keputusan Akhir** (memfinalkan), serta membetulkan hierarki anggaran/kategori pengajuan dan menghapus pengajuan. Reviewer **tidak dapat** menjalankan review AI ulang atas dokumen yang sama. Reviewer juga **mengelola** Acuan, Checklist, Kategori, Satuan Kerja, dan Master RO. | Seluruh pengajuan (dapat difilter per Satker). |
| **Admin** | Mengelola pengguna & role (termasuk reset password) dan node AI, serta melihat audit log. Admin tidak mengelola pengajuan maupun acuan review. | Data pengguna, node AI, dan audit log. |

Pengusul dapat **melihat** (tanpa mengubah) Acuan, Checklist, dan Kategori yang menjadi acuan review.

Satu pengguna dapat memiliki lebih dari satu role.

Satker tempat Reviewer bernaung juga dapat mengusulkan TOR & RAB. Untuk itu disediakan **akun Pengusul tersendiri**, sama seperti Satker lain; pengajuan tidak dibuat dengan akun Reviewer.

---

## 5. Alur Kerja Utama

```
Pengusul: Pengajuan Baru (hierarki anggaran + kategori + TOR dan RAB) → "Kirim"
        │
        ▼
[ANTRE / DIPROSES AI] ──gagal──▶ [GAGAL] (Pengusul ganti PDF lalu kirim ulang, atau Reviewer menghapus)
        │ selesai (Screening 1 + Screening 2)
        ▼
[MENUNGGU VERIFIKASI REVIEWER]
  (verifikator menilai tiap item & boleh override; Pengusul melihat "Menunggu verifikasi")
        │ Reviewer menetapkan Keputusan Akhir
        ├─────────────────────────────┐
        ▼                             ▼
     [LOLOS]                    [TIDAK LOLOS]
                                      │
          Pengusul unggah revisi: PDF TOR dan RAB → langsung direview AI (revisi ke-n)

Salah input hierarki/kategori: Reviewer membetulkannya lewat Edit usulan.
```

Aturan alur:
- Review AI **dipicu oleh Pengusul** saat mengirim Pengajuan Baru atau revisi, dan langsung berjalan tanpa menunggu reviewer. Reviewer baru bekerja setelah hasil AI tersedia (status MENUNGGU VERIFIKASI REVIEWER).
- Selama review berjalan atau menunggu verifikasi, Pengusul tidak dapat mengubah dokumen pada revisi tersebut.
- Status yang dilihat di tabel adalah status **revisi terbaru** dari pengajuan.
- Pengusul dapat membaca hasil review AI segera setelah selesai, agar dapat langsung menyiapkan perbaikan. Penilaian verifikator (Status & Catatan Verifikator) dan Keputusan Akhir beserta catatannya baru ditampilkan kepada Pengusul setelah final; sebelum itu bagian verifikator berketerangan **"Menunggu verifikasi"**.
- Penilaian verifikator yang sedang dikerjakan (belum final) tidak ditampilkan kepada Pengusul.
- Revisi wajib mengunggah **PDF TOR dan RAB** (keduanya), termasuk dokumen yang tidak berubah. Hierarki anggaran dan kategori tidak diubah lewat revisi; bila salah input, Reviewer membetulkannya lewat Edit pengajuan (A3).
- **Satu revisi = satu hasil review AI.** Reviewer **tidak dapat** menjalankan review AI ulang. Tujuannya agar Pengusul dan Reviewer selalu melihat hasil review AI yang **sama**. Review AI baru hanya terjadi bila Pengusul mengajukan revisi baru.
- Pengecualian: bila review AI **GAGAL** (tidak menghasilkan keluaran), Pengusul dapat mengulang pengajuannya. Karena belum ada hasil, tidak ada hasil berbeda yang dilihat kedua pihak.
- Pengecualian kedua: bila Reviewer mengganti TOR dan/atau RAB lewat Edit pengajuan, revisi tersebut direview AI ulang dengan dokumen pengganti. Hasil review sebelumnya tetap tersimpan tetapi tidak dapat diubah lagi; yang dinilai adalah review terbaru, sehingga kedua pihak tetap melihat hasil yang sama.
- Review AI berjalan **di latar belakang**. Pengguna dapat meninggalkan halaman dan melihat progres/status. Jika beberapa review diminta bersamaan, sistem mengantrekannya.

---

## 6. Modul Fungsional

### Modul A — Data Pengajuan (TOR & RAB)

**Kebutuhan:**
- A1. Halaman **Pengajuan Baru** (halaman tersendiri, bukan pop-up), Satker otomatis dari akun Pengusul:
  - **A. Parameter Hierarki Anggaran RKA-K/L**: dropdown bertingkat dan wajib — **Program**, **Kegiatan**, **Klasifikasi Rincian Output (KRO)**, **Rincian Output (RO)** — sesuai data **Master RO** (Modul F) yang Aktif; data Nonaktif, atau yang induknya Nonaktif, tidak dapat dipilih. Pilihan tingkat bawah mengikuti tingkat di atasnya.
  - **B. Klasifikasi Kategori Pengajuan**: **Kategori** (wajib, dari kategori Aktif di menu Kategori) dan **Deskripsi** kategori yang terisi otomatis.
  - **C. Unggah Berkas Dokumen**: PDF **TOR** dan **RAB**; keduanya wajib.
  - Setelah dikirim (dengan konfirmasi), pengajuan langsung direview AI. Tahun anggaran tercatat otomatis.
- A2. Halaman pertama menu Pengajuan = **histori pengajuan** dengan tombol **"Pengajuan Baru"** di kanan atas, berupa tabel: **No**, **Satuan Kerja**, **Rincian Output** (kode dan nama RO), **Dokumen** (dapat diklik untuk melihat isinya), **Status** (status revisi terbaru, §5), **Tanggal Pengajuan**, dan **Aksi**.
- A3. Aksi per baris: **Detail** (semua); **Edit** — Pengusul Satker tersebut saat pengajuan Gagal (hanya mengganti PDF TOR dan/atau RAB), dan Reviewer untuk membetulkan hierarki anggaran serta kategori pengajuan, bila perlu sekaligus mengganti TOR dan/atau RAB (§5) — hanya selama revisi terbaru belum diverifikasi (Lolos/Tidak Lolos); setelah Pengusul mengunggah revisi, Edit tersedia lagi; **Hapus** (Reviewer, A8). Revisi setelah Tidak Lolos diunggah Pengusul lewat tombol **Perbaiki** (Detail Pengajuan) lalu **Unggah Revisi** di halaman Pemeriksaan. Kolom **Tanggal Pengajuan** berisi waktu unggahan terakhir (revisi terbaru), bukan pengajuan pertama.
- A4. Halaman **Detail** pengajuan: (A) parameter hierarki anggaran yang diisi saat pengajuan beserta kategori pengajuan; (B) **Histori Dokumen** berupa tabel **No | Dokumen | Tanggal Verifikasi | Status Verifikasi | Aksi**, satu baris per revisi (dokumen yang diunggah ketika diminta revisi). Aksi: Pengusul **"Detail"** (lihat saja), Reviewer **"Review"** (menilai) — keduanya membuka halaman Pemeriksaan (Override & Finalisasi).
- A5. Filter & pencarian: Satuan Kerja, Rincian Output (kode/nama RO), Dokumen (nama file), Status, dan Tanggal Pengajuan; Tahun Anggaran dipilih di bilah atas. Judul kolom tabel dapat diklik untuk mengurutkan.
- A6. Lihat isi PDF TOR & RAB langsung di aplikasi.
- A7. Riwayat perbaikan per pengajuan tampil di **Histori Dokumen** (A4): setiap revisi beserta tanggal dan status verifikasinya, dan hasil review tiap revisi dapat dibuka di halaman Pemeriksaan. Tidak ada halaman Riwayat/Perbandingan tersendiri.
- A8. **Hapus pengajuan** bersifat permanen (seluruh revisi dan hasil review-nya ikut terhapus; jejak penghapusan tetap di audit log). Hanya Reviewer yang dapat menghapus pengajuan, apa pun statusnya (Gagal, Menunggu verifikasi, Lolos, Tidak Lolos), setelah konfirmasi; pengajuan yang sedang diproses AI tidak dapat dihapus. Tidak ada fitur arsip pengajuan.

### Modul B — Checklist

- B1. CRUD item checklist (tambah, ubah, hapus) melalui form tersendiri.
- B2. Setiap item memiliki minimal: judul, deskripsi/kriteria pemenuhan, dan berlaku untuk **TOR / RAB / keduanya**.
- B3. **Versioning:** setiap perubahan pada daftar checklist menghasilkan versi baru. Setiap review **WAJIB** mencatat versi checklist yang dipakai, sehingga untuk review mana pun pengguna dapat melihat **persis checklist apa saja** (beserta isinya saat itu) yang digunakan.
- B4. Menghapus atau mengubah item tidak boleh mengubah tampilan hasil review lama.
- B5. Reviewer dapat melihat daftar versi dan isi setiap versi.

### Modul C — Kategori

- C1. CRUD kategori (tambah, ubah, hapus) satu per satu melalui halaman form tersendiri (C7). Isi awal (seed) **WAJIB** berisi 4 kategori berikut, dengan teks definisi persis seperti di bawah:

| Kode | Nama | Definisi |
| --- | --- | --- |
| **K1** | RO Wajib | RO yang bersifat wajib, mengikat, ditetapkan melalui kebijakan penganggaran nasional, dan harus tetap berjalan secara berkelanjutan. Penilaian terhadap RO pada kategori ini tidak ditujukan untuk menilai perlu atau tidaknya RO, melainkan untuk memvalidasi kesesuaian ruang lingkup, kejelasan kebutuhan dasar, dan keterkaitan komponen dengan RO yang diusulkan. |
| **K2** | RO Prioritas Strategis | RO prioritas yang ditetapkan secara resmi oleh Menteri, dan/atau penguatan layanan esensial. Penilaian RO terhadap kategori ini dilaksanakan secara penuh sesuai parameter penilaian substansi. |
| **K3** | RO Strategis/Diskresioner | RO yang memiliki keterkaitan dengan prioritas pembangunan nasional dan pencapaian sasaran kementerian, serta mendukung tugas dan fungsi Satker, namun tidak memenuhi kriteria Kategori 1 maupun Kategori 2. |
| **K4** | RO Non-Strategis | RO yang tidak memenuhi kriteria Kategori 1, Kategori 2, maupun Kategori 3, serta tidak memiliki keterkaitan dengan tugas dan fungsi Satker pengusul, maupun pencapaian sasaran strategis kementerian. |

- C2. AI **WAJIB** memakai definisi kategori yang aktif saat review berjalan (bukan definisi yang di-hardcode).
- C3. **Versioning:** setiap review **WAJIB** mencatat daftar kategori yang dipakai (kode, nama, dan definisi kategori berstatus **Aktif**) berupa **salinan** saat review dimulai, sehingga untuk review mana pun pengguna dapat melihat **persis definisi kategori apa saja** (beserta isinya saat itu) yang digunakan. Daftar ini ditampilkan di halaman hasil review dan **tidak berubah** walaupun kategori kemudian diubah atau dihapus.
- C4. Menghapus atau mengubah kategori tidak boleh mengubah tampilan hasil review lama.
- C5. **Detail kategori** (halaman tersendiri, Reviewer) menampilkan Kode, Kategori, Deskripsi, Status, Tanggal Input, dan Diinput Oleh (perubahan terakhir), serta **Kategori Histori**: isi kategori sebelum tiap perubahan (Tanggal Input, Diinput Oleh, Kode, Kategori, Deskripsi, Status), terbaru di atas. Versi terkini hanya ditampilkan di bagian atas detail. Menambah kategori atau menyimpan tanpa perubahan tidak menambah riwayat. Riwayat tidak pernah diubah.
- C6. Setiap kategori berstatus **Aktif** atau **Nonaktif**, seperti acuan. Hanya kategori Aktif yang dipakai AI pada review berikutnya; kategori Nonaktif tetap tampil di daftar dan dapat diaktifkan kembali tanpa dihapus. Kategori baru selalu Aktif (termasuk keempat kategori isi awal); status diubah lewat Edit. Minimal satu kategori harus berstatus Aktif.
- C7. **Daftar kategori** berupa tabel: Kode, Kategori, Status (hanya ditampilkan), Deskripsi, dan Aksi berupa ikon — **Detail**, **Edit**, dan **Hapus** — diurutkan menurut kode (K1, K2, …, K10). **Tambah** dan **Edit** di halaman form tersendiri: Kode (wajib, unik, maksimal 20 karakter, otomatis huruf kapital; boleh diganti saat edit), Kategori (wajib, maksimal 255 karakter), dan Deskripsi (wajib; dipakai AI apa adanya, C2); form **Edit** juga memuat **Status** Aktif/Nonaktif (C6). Sebelum disimpan, tampil ringkasan isian untuk **diperiksa kembali dan dikonfirmasi**. Tambah, edit, dan hapus hanya oleh Reviewer; perubahan dipakai AI mulai review berikutnya.
- C8. **Hapus bersifat permanen:** kategori beserta seluruh Kategori Histori-nya dihapus dan tidak dapat dikembalikan; jejak siapa dan kapan menghapus beserta isi kategori tetap tercatat di audit log (§7.3). Hasil review lama **tidak berubah** karena memakai salinannya sendiri (C3, C4). Sebelum menghapus, Reviewer diberi peringatan berisi ringkasan kategori (Kode, Kategori, jumlah versi di Kategori Histori) dan harus mengonfirmasinya. Minimal satu kategori Aktif harus tetap ada, karena Screening 2 membutuhkan kategori.

### Modul D — Acuan

- D1. Penyimpanan khusus (folder di dalam aplikasi) untuk file PDF acuan.
- D2. **Unggah** dilakukan di halaman form tersendiri: satu file PDF per unggahan, beserta **Nama Acuan** (wajib, maksimal 500 karakter), **Deskripsi**, dan **Status** (Aktif/Nonaktif, bawaan Aktif). File yang dipilih dapat **dipratinjau** (dibuka dan dibaca) sebelum diunggah, sehingga Reviewer dapat memastikan file yang benar; file PDF yang rusak langsung ditandai. Tombol **Reset** mengosongkan seluruh isian, termasuk file. **Edit** juga di halaman form tersendiri untuk mengubah Nama Acuan, Deskripsi, dan Status; file **tidak dapat diganti** (untuk mengganti file, unggah acuan baru lalu nonaktifkan atau hapus yang lama). Sebelum unggah/edit disimpan, tampil ringkasan isian untuk **diperiksa kembali dan dikonfirmasi**. Unggah, edit, dan hapus hanya oleh Reviewer.
- D3. Semua pengguna dapat melihat daftar dan detail acuan serta **membaca isi PDF acuan** di dalam aplikasi.
- D4. Acuan baru harus diproses (dibaca, termasuk tabel, gambar, dan scan) agar siap dirujuk AI. Status pemrosesan tiap file ditampilkan (mis. antre / diproses / siap / gagal), dan file yang gagal dapat diproses ulang. Pemrosesan yang terhenti berulang kali (mis. file terlalu berat) tidak boleh tertahan di status "diproses"; file tersebut ditandai gagal beserta keterangannya agar dapat diproses ulang.
- D5. **Versioning:** setiap review **WAJIB** mencatat acuan apa saja (dan versinya) yang berlaku saat review, sehingga pengguna dapat mengetahui TOR & RAB tersebut direview dengan acuan apa saja. Catatan ini adalah **salinan** saat review dijalankan, sehingga **tidak berubah** walaupun acuan diedit kemudian; catatan hanya hilang bila acuan dihapus (lihat D6).
- D6. **Hapus bersifat permanen:** acuan, seluruh Acuan Histori-nya, dan file PDF-nya (beserta hasil pemrosesannya) dihapus dari aplikasi dan database, dan tidak dapat dikembalikan. File PDF yang isinya sama dan masih dipakai data lain (acuan lain atau TOR/RAB) tetap disimpan. Jejak siapa dan kapan menghapus tetap tercatat di audit log (§7.3), tanpa isi dokumen. Akibatnya, hasil review lama kehilangan catatan dan rujukan ke acuan tersebut — sebelum menghapus, Reviewer diberi peringatan jelas berisi ringkasan acuan yang akan dihapus (Nama Acuan, file, status, jumlah versi di Acuan Histori) dan harus mengonfirmasinya. Penghapusan ditolak bila acuan sedang dipakai review yang berjalan atau filenya sedang diproses. Untuk berhenti memakai acuan **tanpa kehilangan data**, gunakan status Nonaktif (D7).
- D7. **Status Aktif/Nonaktif:** hanya acuan **Aktif** yang sudah **siap** yang dipakai review berikutnya. Acuan Nonaktif tetap tampil di daftar, tetap dapat dibuka, dan dapat diaktifkan kembali lewat Edit.
- D8. **Daftar acuan** berupa tabel: No, Nama Acuan, Deskripsi, Status, Diinput Oleh, Tanggal Input (input/perubahan terakhir), dan Aksi berupa ikon — **Lihat detail** (semua pengguna), **Edit** dan **Hapus** (Reviewer). Kolom Status dapat diurutkan: Default (urut nama), Aktif, atau Nonaktif.
- D9. **Detail acuan** (halaman tersendiri) menampilkan Nama Acuan, Deskripsi, Status, status pemrosesan, file, tombol **Lihat PDF**, Tanggal Input, dan Diinput Oleh (unggahan pertama), serta **Acuan Histori** (riwayat versi): setiap unggah dan setiap edit (nama, deskripsi, maupun status) tercatat sebagai versi; tabel Acuan Histori menampilkan versi-versi sebelum perubahan terakhir (Tanggal Input, Diinput Oleh, Status, Nama Acuan, Deskripsi), sedangkan versi terkini ditampilkan di bagian atas detail. **Data terkini disimpan terpisah dari riwayat:** riwayat hanya berisi versi sebelum perubahan; setiap edit memindahkan data terkini ke riwayat (dengan tanggal dan penginput aslinya), lalu data terkini diperbarui. Riwayat tidak pernah diubah.

### Modul E — Review AI

#### Screening 1 — Pemenuhan Checklist

Dijalankan saat Pengusul mengirim Pengajuan Baru atau revisi, atau saat Reviewer mengganti dokumen lewat Edit pengajuan (§5). Input: TOR dan RAB, versi checklist aktif, acuan aktif, daftar kategori Aktif terbaru. Item checklist untuk dokumen yang tidak diunggah dinyatakan "tidak ditemukan di dokumen".

Keluaran **WAJIB**:

| # | Keluaran | Isi |
| --- | --- | --- |
| 1 | **Label** | LOLOS atau TIDAK LOLOS (lihat aturan §7.1). |
| 2 | **Alasan** | Mengapa label tersebut diberikan: **untuk setiap item checklist**, status terpenuhi/tidak terpenuhi beserta alasannya. |
| 3 | **Rekomendasi Perbaikan TOR** | Langkah konkret agar TOR menjadi LOLOS, sesuai/merujuk file-file acuan. |
| 4 | **Rekomendasi Perbaikan RAB** | Langkah konkret agar RAB menjadi LOLOS, sesuai/merujuk file-file acuan. RAB juga harus dinilai apakah mampu **menceritakan penganggaran berdasarkan apa yang dituangkan di TOR** (keselarasan komponen biaya dengan kegiatan/keluaran di TOR). |

Kebutuhan tambahan:
- E1. **Bukti dari TOR/RAB (WAJIB).** Setiap penilaian item checklist WAJIB menyertakan rujukan bukti yang presisi:
  - dokumen (TOR atau RAB),
  - **nomor halaman**,
  - lokasi di halaman tersebut: **poin / nomor / paragraf / kalimat** (atau baris/sel tabel untuk isi berbentuk tabel),
  - **kutipan** teks aslinya.

  Jika item tidak terpenuhi, sebutkan apa yang kurang. Jika sama sekali tidak ditemukan, nyatakan "tidak ditemukan di dokumen" (tanpa rujukan palsu).
- E2. **Bukti dari Acuan (WAJIB).** Setiap penilaian dan setiap rekomendasi yang didasarkan pada Acuan WAJIB menyertakan rujukan: **judul/nama file acuan, nomor halaman, dan poin / pasal / ayat / nomor / paragraf / kalimat**, beserta **kutipan** teks aslinya.
- E3. Rujukan WAJIB dapat diverifikasi. Nomor halaman mengikuti halaman pada file PDF dan sesuai dengan isi sebenarnya. **Kriteria penerimaan: 100% rujukan** (nomor halaman, lokasi, dan kutipan) yang ditampilkan harus benar ketika dicek ke PDF aslinya; tidak boleh ada satu pun rujukan yang salah halaman atau kutipan yang tidak ada di dokumen. Dari tampilan hasil review, setiap rujukan (TOR, RAB, maupun Acuan) **WAJIB dapat diklik** untuk membuka PDF terkait langsung di halaman tersebut. Bagian yang dirujuk **SEBAIKNYA** disorot.
- E4. AI tidak boleh mengarang isi dokumen, isi acuan, maupun rujukan. Jika informasi tidak ditemukan, katakan tidak ditemukan.
- E5. Jika rekomendasi untuk satu dokumen tidak diperlukan (sudah memenuhi), nyatakan demikian.

#### Screening 2 — Rekomendasi Kategori

- Dijalankan **otomatis setelah Screening 1 selesai**, apa pun label Screening 1.
- Keluaran: **rekomendasi kategori (K1/K2/K3/K4)** beserta alasan yang mengacu pada definisi di Modul C.

#### Override & Finalisasi oleh Reviewer

Hasil AI bersifat **rekomendasi**. Keputusan final ada pada Reviewer. Pemeriksaan dilakukan di halaman **Pemeriksaan**:
- Dua label informasi: jumlah checklist **Lolos** dan jumlah checklist **Tidak Lolos**, masing-masing dari AI dan dari verifikator. Bagi Pengusul sebelum final, label hanya bertuliskan "Menunggu verifikasi" dan tabel checklist kosong.
- Tabel checklist: **No | Kode | Checklist | Kriteria Lolos | Status AI | Catatan AI | Rekomendasi AI | Status Verifikator | Catatan Verifikator**. Pengusul hanya melihat; Reviewer mengisi Status dan Catatan Verifikator.
- Kartu **Keputusan Akhir** (Reviewer): pilihan **LOLOS** / **TIDAK LOLOS** dan kolom **catatan akhir**.

Reviewer dapat meng-override:
1. **Status per item checklist** (Status Verifikator: Lolos / Tidak Lolos; boleh sama dengan AI sebagai konfirmasi)
2. **Label akhir** (Keputusan Akhir LOLOS ↔ TIDAK LOLOS)
3. **Kategori** (K1 / K2 / K3 / K4)

Reviewer juga dapat menambah atau mengubah **catatan/rekomendasi untuk Pengusul**.

Aturan:
- O1. Override label dan kategori **WAJIB** disertai alasan. Catatan Verifikator per item bersifat opsional.
- O2. Hasil asli AI **tetap tersimpan dan dapat dilihat**. Override disimpan terpisah, tidak menimpa hasil AI.
- O3. Tampilan membedakan dengan jelas nilai AI dan nilai yang diubah reviewer.
- O4. Tercatat siapa yang meng-override, kapan, nilai sebelum, dan nilai sesudah.
- O5. Override dapat dibatalkan (kembali ke nilai AI) selama review belum difinalkan.
- O6. Jika item checklist di-override, label akhir **dihitung ulang otomatis** sesuai §7.1. Reviewer tetap boleh meng-override label akhir secara langsung. Bila label tidak konsisten dengan status checklist, sistem menampilkan peringatan dan alasan override wajib diisi.
- O7. Menetapkan **Keputusan Akhir** (dengan konfirmasi) memfinalkan dan mengunci hasil review; keputusan verifikator menjadi label final. Setelah final, hasil tidak dapat diubah. Perubahan hanya melalui revisi baru dari Pengusul.
- O8. **Nilai final** = nilai override bila ada, selain itu nilai AI. Nilai final inilah yang dipakai untuk status pengajuan, kategori di tabel, dan tampilan bagi Pengusul.

---

### Modul F — Master RO

- F1. Reviewer mengelola data referensi RO secara berjenjang: **Program → Kegiatan → KRO → RO**. Setiap Kegiatan berada di bawah satu Program, setiap KRO di bawah satu Kegiatan, dan setiap RO di bawah satu KRO.
- F2. Setiap data memiliki Kode, Nama, dan Status (Aktif/Nonaktif). Kode tidak boleh sama dengan data lain di bawah induk yang sama.
- F3. Tambah, edit, dan hapus hanya oleh Reviewer. Data yang masih memiliki turunan tidak dapat dihapus. Setiap perubahan tercatat di audit log.
- F4. Data Master RO yang Aktif menjadi pilihan hierarki anggaran di Pengajuan Baru (A1). Menonaktifkan data membuatnya tidak dapat dipilih lagi, tanpa mengubah pengajuan yang sudah diajukan.
- F5. Data dapat ditambahkan satu per satu atau **diimpor dari file Excel** (mis. Laporan Renja). Bila ada baris yang salah, tidak ada data yang tersimpan dan semua kesalahan dilaporkan per nomor baris, agar file dapat diperbaiki lalu diimpor ulang. Aplikasi tidak membawa data Renja bawaan: Master RO mulai kosong dan diisi Reviewer sebelum Pengajuan Baru dapat dibuat.

## 7. Aturan Bisnis

### 7.1 Aturan Pelabelan (MUTLAK)
- **LOLOS** = TOR dan RAB **TELAH MEMENUHI/MENJAWAB SELURUH** item checklist, dengan tetap memperhatikan isi Acuan.
- **TIDAK LOLOS** = TOR dan RAB **BELUM MEMENUHI/MENJAWAB salah satu saja** item checklist, dengan tetap memperhatikan isi Acuan.
- Artinya: satu item checklist tidak terpenuhi → TIDAK LOLOS. Tidak ada label lain dan tidak ada nilai parsial.
- "Memperhatikan isi Acuan" berarti: suatu item checklist dianggap terpenuhi hanya jika isi TOR/RAB juga sesuai dengan ketentuan Acuan yang relevan, bukan sekadar menyebutkan topiknya.
- Label AI **WAJIB** konsisten dengan hasil per item. Label tidak boleh LOLOS jika ada item yang tidak terpenuhi.

### 7.2 Kategori
- Rekomendasi kategori AI wajib beralasan dan merujuk definisi kategori.

### 7.3 Ketertelusuran (Audit)
- Setiap review menyimpan: revisi dokumen yang direview, versi checklist, daftar acuan + versinya (kecuali acuan yang kemudian dihapus permanen, D6), salinan daftar kategori yang dipakai (C3), hasil AI, override, siapa yang menjalankan/memfinalkan, dan waktu.
- Perubahan pada Checklist, Kategori, Acuan, pengguna, override, dan penghapusan pengajuan tercatat di audit log (siapa, kapan, apa). Pengajuan yang dihapus (A8) beserta hasil review-nya tidak lagi tersimpan; yang tersisa hanya jejak di audit log.

---

## 8. Kebutuhan Non-Fungsional

| Area | Kebutuhan |
| --- | --- |
| **Privasi** | B1 (offline, dengan toleransi GPU sewaan). Dapat diverifikasi dengan menjalankan aplikasi tanpa jaringan sama sekali, serta dengan memastikan node GPU sewaan hanya berkomunikasi dengan server instansi. |
| **Akurasi** | Prioritas utama (B2). Kecepatan boleh dikorbankan demi akurasi. Hasil **WAJIB konsisten**: bila TOR & RAB yang **sama persis** direview kembali (mis. diajukan ulang sebagai revisi baru tanpa perubahan isi) dengan versi checklist, acuan, dan kategori yang sama, hasil AI (label, status per item checklist, kategori, dan rujukan bukti) harus sama. Tujuannya agar seluruh pengguna tidak kebingungan membaca hasil review AI. **100% rujukan halaman dan kutipan dapat dicek benar** (E3). Akurasi penilaian dievaluasi pemilik produk setelah aplikasi selesai dibangun, dan perbaikan dilakukan berdasarkan umpan baliknya. |
| **Volume dokumen** | TOR ±50 halaman, RAB ±10 halaman per pengajuan. Dokumen dapat berisi halaman scan. Jumlah acuan dapat puluhan file. Sistem harus tetap andal untuk dokumen yang lebih panjang dari rata-rata. Ukuran maksimum **100 MB per file PDF**. |
| **Beban review** | Puncak ±**50 pengajuan review per hari**, hanya pada momen tertentu (tidak setiap hari). Di luar momen tersebut beban jauh lebih rendah, sehingga kapasitas GPU **SEBAIKNYA** dapat dinaikkan saat puncak dan diturunkan setelahnya. |
| **Waktu proses** | Review dijalankan di latar belakang dengan indikator progres. Target waktu ditentukan Agent berdasarkan perangkat keras. |
| **Pengguna bersamaan** | ±**50 pengguna** memakai aplikasi bersamaan (production) tanpa penurunan responsivitas antarmuka. Review AI diantrekan; pengguna dapat melihat posisi antrean. Kapasitas pemrosesan review **SEBAIKNYA** dapat ditambah dengan menambah GPU/server tanpa mengubah kode. |
| **Keandalan** | Kegagalan pemrosesan (PDF rusak, AI error) tidak boleh menghilangkan data. Pengguna mendapat pesan yang jelas dan dapat mengulang. |
| **Keamanan** | Login, kontrol akses per role & Satker, validasi file unggahan (hanya PDF, maks. 100 MB), file tidak dapat diakses tanpa hak, mengganti password mengakhiri sesi login di perangkat lain. |
| **Pemeliharaan** | Modular, terdokumentasi, mudah di-deploy ulang dan di-backup. Lihat §8.1. |
| **UI/UX** | B5. Status, progres, dan perbedaan AI vs override mudah dipahami sekilas. |

### 8.1 Dokumentasi & Logging (WAJIB)

**Dokumentasi:**
- **Dokumentasi kode:** setiap modul, fungsi, dan endpoint penting memiliki penjelasan tujuan, input, output, dan kemungkinan error. Logika yang tidak jelas dari kodenya sendiri (mis. aturan pelabelan, versioning, override) diberi penjelasan alasannya.
- **README** project: gambaran sistem, struktur folder, cara menjalankan, cara menjalankan pengujian.
- **Dokumentasi arsitektur:** diagram komponen, alur data, dan alur pipeline AI.
- **Dokumentasi API:** daftar endpoint beserta request/response.
- **Acuan instalasi offline**, **panduan penggunaan** (per role), dan **panduan administrasi** (backup/restore, penggantian model AI, troubleshooting).

**Logging:**
- Log **terstruktur** dan konsisten, dengan level yang jelas (debug / info / warning / error).
- Setiap entri memuat minimal: waktu, level, modul/komponen, pesan, dan konteks (mis. ID pengguna, ID pengajuan, ID revisi, ID review).
- Setiap proses review AI memiliki **ID pelacakan** yang muncul di seluruh log terkait, sehingga satu review dapat ditelusuri dari pengajuan, ekstraksi PDF, setiap tahap AI, hingga hasil tersimpan, termasuk durasi tiap tahap dan penyebab bila gagal.
- Error dicatat beserta detail teknis yang cukup untuk diagnosis. Pengguna hanya melihat pesan yang ramah dan ID pelacakan untuk dilaporkan.
- Log **tidak boleh** memuat password, token, atau isi dokumen sensitif secara utuh.
- Log disimpan **lokal** (sesuai B1), dengan rotasi dan batas ukuran agar tidak memenuhi disk.
- Log aplikasi (teknis) terpisah dari audit log (§7.3, aktivitas pengguna).

### 8.2 Lingkungan Development & Production (WAJIB)

Langkah awal pengembangan **WAJIB** menyediakan dua skenario lingkungan dengan basis kode yang sama:

| | Development | Production |
| --- | --- | --- |
| **Tujuan** | Membangun & menguji fitur secara lokal. | Dipakai pengguna sebenarnya. |
| **Perangkat keras acuan** | Laptop dengan GPU **NVIDIA RTX A6000 Laptop (16 GB VRAM)** atau setara. | GPU sewaan *on demand* dari cloud publik: **NVIDIA H100 NVL (94 GB VRAM)**, satu atau lebih sesuai beban (lihat toleransi B1). Server aplikasi & data di instansi. |
| **Model AI** | Model *entry level* yang muat dan berjalan di perangkat acuan. Akurasi boleh lebih rendah, tetapi **seluruh alur** (ekstraksi, Screening 1 & 2, rujukan, override) harus berfungsi. | Model dengan akurasi terbaik untuk perangkat production (B2). |
| **Pengguna** | 1–3 developer. | ±50 pengguna bersamaan. |

Ketentuan:
- Perpindahan Development ↔ Production cukup dengan **mengganti konfigurasi** (mis. file environment), bukan mengubah kode.
- Model yang dipakai tercatat di setiap review (§7.3), sehingga hasil review dari model development dapat dibedakan dari hasil model production.
- Developer tanpa GPU **SEBAIKNYA** tetap dapat menjalankan aplikasi (mis. untuk pengembangan antarmuka) dengan mode AI tiruan.
- Kedua skenario tetap tunduk pada B1 saat runtime. Pengunduhan model dan dependensi hanya terjadi pada tahap persiapan/build, bukan saat aplikasi berjalan.

---

## 9. Halaman Utama (indikatif)

| Halaman | Role | Isi |
| --- | --- | --- |
| Login | Semua | — |
| Dashboard | Pengusul, Reviewer | Ringkasan jumlah pengajuan per status/kategori/Satker |
| Pengajuan (histori) | Pengusul (Satker sendiri), Reviewer | Tabel A2 + tombol Pengajuan Baru + filter |
| Pengajuan Baru | Pengusul | Form A1 (hierarki anggaran, kategori, TOR dan RAB) |
| Edit / Unggah Revisi | Pengusul | Edit (Gagal): unggah PDF TOR dan/atau RAB pengganti; Unggah Revisi (Tidak Lolos): PDF TOR dan RAB wajib |
| Edit Pengajuan | Reviewer | Hierarki anggaran, kategori, dan (opsional) TOR/RAB pengganti |
| Detail Pengajuan | Pengusul (Satker sendiri), Reviewer | Parameter hierarki anggaran + Histori Dokumen (A4) |
| Pemeriksaan | Reviewer (menilai), Pengusul (hasil AI segera; penilaian verifikator setelah final) | Label Lolos/Tidak Lolos (AI & verifikator), tabel checklist, Keputusan Akhir |
| Kelola Checklist | Reviewer (Pengusul: lihat saja) | CRUD + daftar versi |
| Kelola Kategori | Reviewer (Pengusul: lihat saja) | Tabel daftar kategori (C7), detail & Kategori Histori (C5), konfirmasi hapus (C8) |
| Tambah / Edit Kategori | Reviewer | Form C7 + konfirmasi periksa kembali |
| Acuan | Pengusul, Reviewer (kelola: Reviewer) | Tabel daftar acuan + urut status (D8), detail & Acuan Histori (D9), viewer PDF, status pemrosesan, konfirmasi hapus (D6) |
| Unggah / Edit Acuan | Reviewer | Form D2 (unggah: pratinjau PDF & Reset) + konfirmasi periksa kembali |
| Satuan Kerja | Reviewer | Unit Kerja (Eselon I) & Satuan Kerja (Eselon II) beserta kodenya |
| Master RO | Reviewer | Program → Kegiatan → KRO → RO (Modul F) |
| Kelola Pengguna | Admin | Pengguna, role, Satker, reset password |
| Node AI | Admin | Node AI yang terhubung, daftarkan & cabut node |
| Audit Log | Admin | — |

---

## 10. Di Luar Lingkup
- Integrasi dengan sistem pemerintah lain (mis. aplikasi penganggaran nasional).
- Aplikasi mobile native (cukup web responsif).
- Antarmuka multi-bahasa (Bahasa Indonesia saja).
- Fine-tuning model wajib *tidak* disyaratkan. Agent boleh mengusulkannya bila diperlukan untuk akurasi.

---

## 11. Keputusan Teknis yang Diserahkan kepada AI Agent

Agent bebas memilih dan **WAJIB menjelaskan alasannya**, terutama kaitannya dengan B1 (offline), B2 (akurasi), dan B3 (PDF multi-modal):
- Teknologi frontend, backend, database, penyimpanan file.
- Pipeline AI: model lokal yang dipakai, pendekatan (RAG, vision model, OCR, ekstraktor PDF, fine-tuning, atau kombinasi), strategi menangani dokumen panjang, dan cara menjamin label konsisten dengan hasil per item.
- Pilihan model untuk Development dan Production (§8.2) beserta perbedaan akurasi yang diharapkan.
- Kebutuhan perangkat keras Production selain GPU (CPU/RAM/disk server aplikasi dan node GPU) untuk ±50 pengguna bersamaan, beserta perkiraan waktu review per pengajuan, kapasitas per GPU H100 NVL, dan jumlah GPU yang disarankan saat beban puncak.
- Cara mengamankan pemrosesan di GPU sewaan sesuai toleransi B1.
- Desain database fisik.
- Detail deployment berbasis kontainer (B7), termasuk cara instalasi di lingkungan tanpa internet (model & dependensi dibundel/dapat dipindahkan secara offline) dan cara menambah kapasitas GPU.

---

## 12. Tahapan Kerja yang Diminta dari AI Agent

1. ~~**Pengajuan desain**~~ — **selesai**, lihat `desain.md`.
2. ~~**Persetujuan** pemilik produk~~ — **disetujui** (2026-10-12).
3. **Implementasi lengkap** (langsung seluruh aplikasi, bukan bertahap; kekurangan diperbaiki berdasarkan umpan balik pemilik produk setelahnya): dimulai dari lingkungan Development (§8.2) yang dapat dijalankan dengan satu perintah, lalu backend API, frontend UI, konfigurasi kontainer Development & Production (B7), data seed (4 kategori), serta dokumentasi dan logging lengkap sesuai §8.1.
4. **Pengujian:** sertakan pengujian otomatis untuk logika inti (aturan pelabelan §7.1, versioning, override, hak akses, verifikasi rujukan E3) dan cara memverifikasi bahwa aplikasi tidak melakukan koneksi keluar.
5. **Evaluasi oleh pemilik produk** setelah aplikasi selesai, lalu perbaikan berdasarkan umpan balik.