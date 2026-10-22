# PRD — Asisten AI Offline untuk Review Dokumen TOR & RAB

**Status:** Disetujui | **Pemilik:** Maldini | **Versi:** 2.1 | **Tanggal:** 2026-10-21 (v1: 2026-10-12, v2: 2026-10-20)

**Perubahan v2 (2026-10-20):** Modul D — Panduan direvisi berdasarkan keputusan pemilik produk: unggah satu file per form dengan Nama Acuan, Deskripsi, dan Status; status Aktif/Nonaktif; edit tanpa ganti file; hapus permanen; daftar berupa tabel; halaman detail dengan riwayat versi; data terkini disimpan terpisah dari riwayat versi; catatan panduan pada review tidak berubah walaupun panduan diedit (D2, D4–D9, §7.3, §9).

**Perubahan v2.1 (2026-10-21):** Modul D — riwayat versi pada detail panduan disebut **Panduan Histori**; form unggah dilengkapi **pratinjau PDF** sebelum diunggah dan tombol **Reset**; Nama Acuan maksimal 500 karakter; konfirmasi hapus menampilkan ringkasan panduan yang akan dihapus; file yang pemrosesannya terhenti ditandai gagal agar dapat diproses ulang; penjelasan data yang ikut terhapus (D2, D4, D6, D9, §9).

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
| **RO** | Rincian Output. Unit keluaran kegiatan yang diusulkan anggarannya. Satu pasang TOR + RAB = satu RO. |
| **Satker** | Satuan Kerja. Unit organisasi yang mengusulkan RO. |
| **Usulan** | Satu pasang dokumen TOR + RAB untuk satu RO, beserta seluruh riwayat revisi dan review-nya. |
| **Checklist** | Daftar hal yang wajib dipenuhi/dijawab oleh TOR dan RAB. |
| **Panduan** | Kumpulan PDF referensi (peraturan, kebijakan, standar biaya, dsb.) yang wajib dirujuk AI. Setiap panduan memiliki **Nama Acuan**, deskripsi, dan status **Aktif/Nonaktif**. |
| **Panduan Histori** | Riwayat versi sebuah panduan: isi panduan sebelum tiap perubahan (nama, deskripsi, status), beserta tanggal dan penginputnya. |
| **Kategori** | Klasifikasi prioritas anggaran RO: K1, K2, K3, K4. |
| **Screening 1** | Penilaian AI terhadap pemenuhan checklist → label LOLOS / TIDAK LOLOS + alasan + rekomendasi. |
| **Screening 2** | Rekomendasi kategori (K1–K4) oleh AI untuk RO tersebut. |
| **Override** | Tindakan reviewer mengubah hasil AI. |

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

1. Proses review yang **seragam, cepat, dan akurat** dengan tetap merujuk peraturan, kebijakan, dan standar (Panduan).
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
| B3 | **PDF multi-modal** | TOR, RAB, dan Panduan dapat berisi teks, tabel, gambar, grafik/chart, diagram, dan **hasil scan**. Semuanya harus dapat dibaca dan dipahami. |
| B4 | **Production-ready** | Kode rapi, terstruktur, efisien, mengikuti *best practice* terkini, andal, mudah dipelihara. Bukan prototipe. Kode **WAJIB** dilengkapi **dokumentasi** dan **logging** yang rapi, mudah ditelusuri, dan mudah dipelihara (rincian di §8.1). |
| B5 | **UI modern & responsif** | Tampil baik di desktop, tablet, dan ponsel. Intuitif, profesional, menarik. |
| B6 | **Bahasa Indonesia** | Seluruh antarmuka dan seluruh keluaran AI (alasan, rekomendasi) dalam Bahasa Indonesia. |
| B7 | **Berbasis kontainer** | Seluruh komponen (aplikasi, database, layanan AI, model) **WAJIB** berjalan di kontainer (Docker atau sejenisnya). Aplikasi kemungkinan dijalankan di server dan GPU yang disediakan sesuai kebutuhan (*on demand*), sehingga harus dapat dipindah dan dijalankan di berbagai lingkungan dengan langkah minimal. **Kemudahan menjalankan adalah kunci**: developer baru harus dapat menjalankan aplikasi lengkap dengan satu perintah dan panduan singkat. |

---

## 4. Pengguna & Hak Akses

Aplikasi **WAJIB** memiliki login dan pembatasan akses per role.

| Role | Tanggung jawab | Akses data |
| --- | --- | --- |
| **Pengusul** (penginput TOR & RAB) | Membuat usulan, mengunggah TOR & RAB, **mengajukan review** (yang langsung menjalankan review AI), memantau status, membaca **hasil review AI** (segera setelah selesai) dan **hasil final** dari reviewer, mengunggah revisi. | Hanya usulan milik Satker-nya. |
| **Reviewer** | Memeriksa hasil review AI, melakukan **override**, memberi catatan, dan **memfinalkan** hasil review. Reviewer **tidak dapat** menjalankan review AI ulang. | Seluruh usulan (dapat difilter per Satker). |
| **Admin** | Mengelola Checklist, Kategori, Panduan, pengguna & role, serta melihat audit log. | Seluruh data. |

Satu pengguna dapat memiliki lebih dari satu role.

Satker tempat Reviewer bernaung juga dapat mengusulkan TOR & RAB. Untuk itu disediakan **akun Pengusul tersendiri**, sama seperti Satker lain; usulan tidak dibuat dengan akun Reviewer.

---

## 5. Alur Kerja Utama

```
Pengusul unggah TOR + RAB
        │
        ▼
[DRAF / BELUM DIREVIEW]
        │ Pengusul klik "Ajukan Review"
        ▼
[DIPROSES AI] ──gagal──▶ [GAGAL] (dapat diulang)
        │ selesai (Screening 1 + Screening 2)
        ▼
[MENUNGGU VERIFIKASI REVIEWER]
  (reviewer memeriksa & boleh override)
        │ Reviewer klik "Finalkan"
        ├─────────────────────────────┐
        ▼                             ▼
     [LOLOS]                    [TIDAK LOLOS]
                                      │
                Pengusul unggah revisi TOR dan/atau RAB
                                      │
                                      ▼
                       [DRAF] (revisi ke-n) → "Ajukan Review" lagi
```

Aturan alur:
- Review AI **dipicu oleh Pengusul** melalui tombol **"Ajukan Review"**, dan langsung berjalan tanpa menunggu reviewer. Reviewer baru bekerja setelah hasil AI tersedia (status MENUNGGU VERIFIKASI REVIEWER).
- Selama review berjalan atau menunggu verifikasi, Pengusul tidak dapat mengubah dokumen pada revisi tersebut.
- Status yang dilihat di tabel adalah status **revisi terbaru** dari usulan.
- Pengusul **dapat langsung melihat hasil review AI** begitu AI selesai, tanpa menunggu finalisasi reviewer. Hasil ini ditandai jelas sebagai **"Hasil AI — belum diverifikasi reviewer"**. Setelah reviewer memfinalkan, Pengusul juga melihat **hasil final** (termasuk override dan catatan reviewer), berdampingan dengan hasil AI.
- Override yang sedang dikerjakan reviewer (belum difinalkan) tidak ditampilkan kepada Pengusul.
- Revisi boleh mengganti **TOR saja, RAB saja, atau keduanya**. Dokumen yang tidak diganti terbawa dari revisi sebelumnya.
- **Satu revisi = satu hasil review AI.** Reviewer **tidak dapat** menjalankan review AI ulang. Tujuannya agar Pengusul dan Reviewer selalu melihat hasil review AI yang **sama**. Review AI baru hanya terjadi bila Pengusul mengajukan revisi baru.
- Pengecualian: bila review AI **GAGAL** (tidak menghasilkan keluaran), Pengusul dapat mengulang pengajuannya. Karena belum ada hasil, tidak ada hasil berbeda yang dilihat kedua pihak.
- Review AI berjalan **di latar belakang**. Pengguna dapat meninggalkan halaman dan melihat progres/status. Jika beberapa review diminta bersamaan, sistem mengantrekannya.

---

## 6. Modul Fungsional

### Modul A — Data Usulan (TOR & RAB)

**Kebutuhan:**
- A1. Form untuk membuat usulan: **Satker**, **Tahun Anggaran**, **nama/kode RO**, **unggah PDF TOR**, **unggah PDF RAB**. Keduanya wajib PDF.
- A2. Tabel daftar usulan, menampilkan minimal: Satker, Tahun Anggaran, RO, nama file TOR, nama file RAB, nomor revisi, **status review** (BELUM DIREVIEW / LOLOS / TIDAK LOLOS, serta status proses lain pada §5), kategori final, tanggal update.
- A3. Tombol aksi per baris sesuai role dan status: **"Ajukan Review"** (Pengusul, saat status DRAF/BELUM DIREVIEW), **"Lihat Hasil AI"** (Pengusul, setelah AI selesai), **"Periksa Hasil"** (Reviewer, saat MENUNGGU VERIFIKASI REVIEWER).
- A4. Untuk baris yang sudah direview, tabel dapat menampilkan **checklist mana saja yang terpenuhi dan belum terpenuhi** (mis. ringkasan "8/10 terpenuhi" yang dapat dibuka untuk rincian per item).
- A5. Filter & pencarian: Satker, Tahun Anggaran, status, kategori, RO.
- A6. Lihat isi PDF TOR & RAB langsung di aplikasi.
- A7. Halaman **Riwayat** per usulan: daftar semua revisi dan semua review, termasuk perbandingan pemenuhan checklist antar-revisi (item yang berubah dari tidak terpenuhi → terpenuhi, dan sebaliknya).
- A8. Usulan yang sudah pernah direview **tidak boleh dihapus**, hanya dapat **diarsipkan**, demi menjaga riwayat usulan. Usulan arsip tetap dapat dilihat beserta seluruh riwayatnya. Usulan yang belum pernah diajukan review (DRAF) boleh dihapus oleh Pengusul.

### Modul B — Checklist

- B1. CRUD item checklist (tambah, ubah, hapus) melalui form tersendiri.
- B2. Setiap item memiliki minimal: judul, deskripsi/kriteria pemenuhan, dan berlaku untuk **TOR / RAB / keduanya**.
- B3. **Versioning:** setiap perubahan pada daftar checklist menghasilkan versi baru. Setiap review **WAJIB** mencatat versi checklist yang dipakai, sehingga untuk review mana pun pengguna dapat melihat **persis checklist apa saja** (beserta isinya saat itu) yang digunakan.
- B4. Menghapus atau mengubah item tidak boleh mengubah tampilan hasil review lama.
- B5. Admin dapat melihat daftar versi dan isi setiap versi.

### Modul C — Kategori

- C1. CRUD kategori (tambah, ubah, hapus) melalui form tersendiri. Isi awal (seed) **WAJIB** berisi 4 kategori berikut, dengan teks definisi persis seperti di bawah:

| Kode | Nama | Definisi |
| --- | --- | --- |
| **K1** | RO Wajib | RO yang bersifat wajib, mengikat, ditetapkan melalui kebijakan penganggaran nasional, dan harus tetap berjalan secara berkelanjutan. Penilaian terhadap RO pada kategori ini tidak ditujukan untuk menilai perlu atau tidaknya RO, melainkan untuk memvalidasi kesesuaian ruang lingkup, kejelasan kebutuhan dasar, dan keterkaitan komponen dengan RO yang diusulkan. |
| **K2** | RO Prioritas Strategis | RO prioritas yang ditetapkan secara resmi oleh Menteri, dan/atau penguatan layanan esensial. Penilaian RO terhadap kategori ini dilaksanakan secara penuh sesuai parameter penilaian substansi. |
| **K3** | RO Strategis/Diskresioner | RO yang memiliki keterkaitan dengan prioritas pembangunan nasional dan pencapaian sasaran kementerian, serta mendukung tugas dan fungsi Satker, namun tidak memenuhi kriteria Kategori 1 maupun Kategori 2. |
| **K4** | RO Non-Strategis | RO yang tidak memenuhi kriteria Kategori 1, Kategori 2, maupun Kategori 3, serta tidak memiliki keterkaitan dengan tugas dan fungsi Satker pengusul, maupun pencapaian sasaran strategis kementerian. RO pada kategori ini **tidak diteruskan ke tahap berikutnya**. |

- C2. AI **WAJIB** memakai definisi kategori yang aktif saat review berjalan (bukan definisi yang di-hardcode).
- C3. **Versioning:** setiap perubahan pada daftar kategori menghasilkan versi baru. Setiap review **WAJIB** mencatat versi kategori yang dipakai, sehingga untuk review mana pun pengguna dapat melihat **persis definisi kategori apa saja** (beserta isinya saat itu) yang digunakan.
- C4. Menghapus atau mengubah kategori tidak boleh mengubah tampilan hasil review lama.
- C5. Admin dapat melihat daftar versi dan isi setiap versi.
- C6. Usulan dengan kategori final **K4** ditandai jelas sebagai "tidak diteruskan".

### Modul D — Panduan

- D1. Penyimpanan khusus (folder di dalam aplikasi) untuk file PDF panduan.
- D2. **Unggah** dilakukan di halaman form tersendiri: satu file PDF per unggahan, beserta **Nama Acuan** (wajib, maksimal 500 karakter), **Deskripsi**, dan **Status** (Aktif/Nonaktif, bawaan Aktif). File yang dipilih dapat **dipratinjau** (dibuka dan dibaca) sebelum diunggah, sehingga Admin dapat memastikan file yang benar; file PDF yang rusak langsung ditandai. Tombol **Reset** mengosongkan seluruh isian, termasuk file. **Edit** juga di halaman form tersendiri untuk mengubah Nama Acuan, Deskripsi, dan Status; file **tidak dapat diganti** (untuk mengganti file, unggah panduan baru lalu nonaktifkan atau hapus yang lama). Sebelum unggah/edit disimpan, tampil ringkasan isian untuk **diperiksa kembali dan dikonfirmasi**. Unggah, edit, dan hapus hanya oleh Admin.
- D3. Semua pengguna dapat melihat daftar dan detail panduan serta **membaca isi PDF panduan** di dalam aplikasi.
- D4. Panduan baru harus diproses (dibaca, termasuk tabel, gambar, dan scan) agar siap dirujuk AI. Status pemrosesan tiap file ditampilkan (mis. antre / diproses / siap / gagal), dan file yang gagal dapat diproses ulang. Pemrosesan yang terhenti berulang kali (mis. file terlalu berat) tidak boleh tertahan di status "diproses"; file tersebut ditandai gagal beserta keterangannya agar dapat diproses ulang.
- D5. **Versioning:** setiap review **WAJIB** mencatat panduan apa saja (dan versinya) yang berlaku saat review, sehingga pengguna dapat mengetahui TOR & RAB tersebut direview dengan acuan panduan apa saja. Catatan ini adalah **salinan** saat review dijalankan, sehingga **tidak berubah** walaupun panduan diedit kemudian; catatan hanya hilang bila panduan dihapus (lihat D6).
- D6. **Hapus bersifat permanen:** panduan, seluruh Panduan Histori-nya, dan file PDF-nya (beserta hasil pemrosesannya) dihapus dari aplikasi dan database, dan tidak dapat dikembalikan. File PDF yang isinya sama dan masih dipakai data lain (panduan lain atau TOR/RAB) tetap disimpan. Jejak siapa dan kapan menghapus tetap tercatat di audit log (§7.3), tanpa isi dokumen. Akibatnya, hasil review lama kehilangan catatan dan rujukan ke panduan tersebut — sebelum menghapus, Admin diberi peringatan jelas berisi ringkasan panduan yang akan dihapus (Nama Acuan, file, status, jumlah versi di Panduan Histori) dan harus mengonfirmasinya. Penghapusan ditolak bila panduan sedang dipakai review yang berjalan atau filenya sedang diproses. Untuk berhenti memakai panduan **tanpa kehilangan data**, gunakan status Nonaktif (D7).
- D7. **Status Aktif/Nonaktif:** hanya panduan **Aktif** yang sudah **siap** yang dipakai review berikutnya. Panduan Nonaktif tetap tampil di daftar, tetap dapat dibuka, dan dapat diaktifkan kembali lewat Edit.
- D8. **Daftar panduan** berupa tabel: No, Nama Acuan, Deskripsi, Status, Diinput Oleh, Tanggal Input (input/perubahan terakhir), dan Aksi berupa ikon — **Lihat detail** (semua pengguna), **Edit** dan **Hapus** (Admin). Kolom Status dapat diurutkan: Default (urut nama), Aktif, atau Nonaktif.
- D9. **Detail panduan** (halaman tersendiri) menampilkan Nama Acuan, Deskripsi, Status, status pemrosesan, file, tombol **Lihat PDF**, Tanggal Input, dan Diinput Oleh (unggahan pertama), serta **Panduan Histori** (riwayat versi): setiap unggah dan setiap edit (nama, deskripsi, maupun status) tercatat sebagai versi; tabel Panduan Histori menampilkan versi-versi sebelum perubahan terakhir (Tanggal Input, Diinput Oleh, Status, Nama Acuan, Deskripsi), sedangkan versi terkini ditampilkan di bagian atas detail. **Data terkini disimpan terpisah dari riwayat:** riwayat hanya berisi versi sebelum perubahan; setiap edit memindahkan data terkini ke riwayat (dengan tanggal dan penginput aslinya), lalu data terkini diperbarui. Riwayat tidak pernah diubah.

### Modul E — Review AI

#### Screening 1 — Pemenuhan Checklist

Dijalankan saat Pengusul menekan **"Ajukan Review"**. Input: TOR, RAB, versi checklist aktif, panduan aktif, versi kategori aktif.

Keluaran **WAJIB**:

| # | Keluaran | Isi |
| --- | --- | --- |
| 1 | **Label** | LOLOS atau TIDAK LOLOS (lihat aturan §7.1). |
| 2 | **Alasan** | Mengapa label tersebut diberikan: **untuk setiap item checklist**, status terpenuhi/tidak terpenuhi beserta alasannya. |
| 3 | **Rekomendasi Perbaikan TOR** | Langkah konkret agar TOR menjadi LOLOS, sesuai/merujuk file-file panduan. |
| 4 | **Rekomendasi Perbaikan RAB** | Langkah konkret agar RAB menjadi LOLOS, sesuai/merujuk file-file panduan. RAB juga harus dinilai apakah mampu **menceritakan penganggaran berdasarkan apa yang dituangkan di TOR** (keselarasan komponen biaya dengan kegiatan/keluaran di TOR). |

Kebutuhan tambahan:
- E1. **Bukti dari TOR/RAB (WAJIB).** Setiap penilaian item checklist WAJIB menyertakan rujukan bukti yang presisi:
  - dokumen (TOR atau RAB),
  - **nomor halaman**,
  - lokasi di halaman tersebut: **poin / nomor / paragraf / kalimat** (atau baris/sel tabel untuk isi berbentuk tabel),
  - **kutipan** teks aslinya.

  Jika item tidak terpenuhi, sebutkan apa yang kurang. Jika sama sekali tidak ditemukan, nyatakan "tidak ditemukan di dokumen" (tanpa rujukan palsu).
- E2. **Bukti dari Panduan (WAJIB).** Setiap penilaian dan setiap rekomendasi yang didasarkan pada Panduan WAJIB menyertakan rujukan: **judul/nama file panduan, nomor halaman, dan poin / pasal / ayat / nomor / paragraf / kalimat**, beserta **kutipan** teks aslinya.
- E3. Rujukan WAJIB dapat diverifikasi. Nomor halaman mengikuti halaman pada file PDF dan sesuai dengan isi sebenarnya. **Kriteria penerimaan: 100% rujukan** (nomor halaman, lokasi, dan kutipan) yang ditampilkan harus benar ketika dicek ke PDF aslinya; tidak boleh ada satu pun rujukan yang salah halaman atau kutipan yang tidak ada di dokumen. Dari tampilan hasil review, setiap rujukan (TOR, RAB, maupun Panduan) **WAJIB dapat diklik** untuk membuka PDF terkait langsung di halaman tersebut. Bagian yang dirujuk **SEBAIKNYA** disorot.
- E4. AI tidak boleh mengarang isi dokumen, isi panduan, maupun rujukan. Jika informasi tidak ditemukan, katakan tidak ditemukan.
- E5. Jika rekomendasi untuk satu dokumen tidak diperlukan (sudah memenuhi), nyatakan demikian.

#### Screening 2 — Rekomendasi Kategori

- Dijalankan **otomatis setelah Screening 1 selesai**, apa pun label Screening 1.
- Keluaran: **rekomendasi kategori (K1/K2/K3/K4)** beserta alasan yang mengacu pada definisi di Modul C.

#### Override & Finalisasi oleh Reviewer

Hasil AI bersifat **rekomendasi**. Keputusan final ada pada Reviewer. Reviewer dapat meng-override:
1. **Status per item checklist** (terpenuhi ↔ tidak terpenuhi)
2. **Label akhir** (LOLOS ↔ TIDAK LOLOS)
3. **Kategori** (K1 / K2 / K3 / K4)

Reviewer juga dapat menambah atau mengubah **catatan/rekomendasi untuk Pengusul**.

Aturan:
- O1. Setiap override **WAJIB** disertai alasan.
- O2. Hasil asli AI **tetap tersimpan dan dapat dilihat**. Override disimpan terpisah, tidak menimpa hasil AI.
- O3. Tampilan membedakan dengan jelas nilai AI dan nilai yang diubah reviewer.
- O4. Tercatat siapa yang meng-override, kapan, nilai sebelum, dan nilai sesudah.
- O5. Override dapat dibatalkan (kembali ke nilai AI) selama review belum difinalkan.
- O6. Jika item checklist di-override, label akhir **dihitung ulang otomatis** sesuai §7.1. Reviewer tetap boleh meng-override label akhir secara langsung. Bila label tidak konsisten dengan status checklist, sistem menampilkan peringatan dan alasan override wajib diisi.
- O7. Tombol **"Finalkan"** mengunci hasil review. Setelah final, hasil tidak dapat diubah. Perubahan hanya melalui revisi baru dari Pengusul.
- O8. **Nilai final** = nilai override bila ada, selain itu nilai AI. Nilai final inilah yang dipakai untuk status usulan, kategori di tabel, dan tampilan bagi Pengusul.

---

## 7. Aturan Bisnis

### 7.1 Aturan Pelabelan (MUTLAK)
- **LOLOS** = TOR dan RAB **TELAH MEMENUHI/MENJAWAB SELURUH** item checklist, dengan tetap memperhatikan isi Panduan.
- **TIDAK LOLOS** = TOR dan RAB **BELUM MEMENUHI/MENJAWAB salah satu saja** item checklist, dengan tetap memperhatikan isi Panduan.
- Artinya: satu item checklist tidak terpenuhi → TIDAK LOLOS. Tidak ada label lain dan tidak ada nilai parsial.
- "Memperhatikan isi Panduan" berarti: suatu item checklist dianggap terpenuhi hanya jika isi TOR/RAB juga sesuai dengan ketentuan Panduan yang relevan, bukan sekadar menyebutkan topiknya.
- Label AI **WAJIB** konsisten dengan hasil per item. Label tidak boleh LOLOS jika ada item yang tidak terpenuhi.

### 7.2 Kategori
- K4 = RO tidak diteruskan ke tahap berikutnya.
- Rekomendasi kategori AI wajib beralasan dan merujuk definisi kategori.

### 7.3 Ketertelusuran (Audit)
- Setiap review menyimpan: revisi dokumen yang direview, versi checklist, daftar panduan + versinya (kecuali panduan yang kemudian dihapus permanen, D6), versi kategori, hasil AI, override, siapa yang menjalankan/memfinalkan, dan waktu.
- Perubahan pada Checklist, Kategori, Panduan, pengguna, dan override tercatat di audit log (siapa, kapan, apa).

---

## 8. Kebutuhan Non-Fungsional

| Area | Kebutuhan |
| --- | --- |
| **Privasi** | B1 (offline, dengan toleransi GPU sewaan). Dapat diverifikasi dengan menjalankan aplikasi tanpa jaringan sama sekali, serta dengan memastikan node GPU sewaan hanya berkomunikasi dengan server instansi. |
| **Akurasi** | Prioritas utama (B2). Kecepatan boleh dikorbankan demi akurasi. Hasil **WAJIB konsisten**: bila TOR & RAB yang **sama persis** direview kembali (mis. diajukan ulang sebagai revisi baru tanpa perubahan isi) dengan versi checklist, panduan, dan kategori yang sama, hasil AI (label, status per item checklist, kategori, dan rujukan bukti) harus sama. Tujuannya agar seluruh pengguna tidak kebingungan membaca hasil review AI. **100% rujukan halaman dan kutipan dapat dicek benar** (E3). Akurasi penilaian dievaluasi pemilik produk setelah aplikasi selesai dibangun, dan perbaikan dilakukan berdasarkan umpan baliknya. |
| **Volume dokumen** | TOR ±50 halaman, RAB ±10 halaman per usulan. Dokumen dapat berisi halaman scan. Jumlah panduan dapat puluhan file. Sistem harus tetap andal untuk dokumen yang lebih panjang dari rata-rata. Ukuran maksimum **100 MB per file PDF**. |
| **Beban review** | Puncak ±**50 pengajuan review per hari**, hanya pada momen tertentu (tidak setiap hari). Di luar momen tersebut beban jauh lebih rendah, sehingga kapasitas GPU **SEBAIKNYA** dapat dinaikkan saat puncak dan diturunkan setelahnya. |
| **Waktu proses** | Review dijalankan di latar belakang dengan indikator progres. Target waktu ditentukan Agent berdasarkan perangkat keras. |
| **Pengguna bersamaan** | ±**50 pengguna** memakai aplikasi bersamaan (production) tanpa penurunan responsivitas antarmuka. Review AI diantrekan; pengguna dapat melihat posisi antrean. Kapasitas pemrosesan review **SEBAIKNYA** dapat ditambah dengan menambah GPU/server tanpa mengubah kode. |
| **Keandalan** | Kegagalan pemrosesan (PDF rusak, AI error) tidak boleh menghilangkan data. Pengguna mendapat pesan yang jelas dan dapat mengulang. |
| **Keamanan** | Login, kontrol akses per role & Satker, validasi file unggahan (hanya PDF, maks. 100 MB), file tidak dapat diakses tanpa hak. |
| **Pemeliharaan** | Modular, terdokumentasi, mudah di-deploy ulang dan di-backup. Lihat §8.1. |
| **UI/UX** | B5. Status, progres, dan perbedaan AI vs override mudah dipahami sekilas. |

### 8.1 Dokumentasi & Logging (WAJIB)

**Dokumentasi:**
- **Dokumentasi kode:** setiap modul, fungsi, dan endpoint penting memiliki penjelasan tujuan, input, output, dan kemungkinan error. Logika yang tidak jelas dari kodenya sendiri (mis. aturan pelabelan, versioning, override) diberi penjelasan alasannya.
- **README** project: gambaran sistem, struktur folder, cara menjalankan, cara menjalankan pengujian.
- **Dokumentasi arsitektur:** diagram komponen, alur data, dan alur pipeline AI.
- **Dokumentasi API:** daftar endpoint beserta request/response.
- **Panduan instalasi offline**, **panduan penggunaan** (per role), dan **panduan administrasi** (backup/restore, penggantian model AI, troubleshooting).

**Logging:**
- Log **terstruktur** dan konsisten, dengan level yang jelas (debug / info / warning / error).
- Setiap entri memuat minimal: waktu, level, modul/komponen, pesan, dan konteks (mis. ID pengguna, ID usulan, ID revisi, ID review).
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
| Dashboard | Semua | Ringkasan jumlah usulan per status/kategori/Satker |
| Daftar Usulan | Semua (Pengusul: Satker sendiri) | Tabel Modul A + filter |
| Buat Usulan / Unggah Revisi | Pengusul | Form A1 / unggah revisi, tombol "Ajukan Review" |
| Detail Review | Reviewer, Pengusul (hasil AI segera; hasil final setelah difinalkan) | Hasil Screening 1 & 2, rincian checklist, rekomendasi, override, finalisasi, viewer PDF |
| Riwayat Usulan | Semua | Timeline revisi & review, perbandingan |
| Kelola Checklist | Admin | CRUD + daftar versi |
| Kelola Kategori | Admin | CRUD + daftar versi |
| Panduan | Semua (kelola: Admin) | Tabel daftar panduan + urut status (D8), detail & Panduan Histori (D9), viewer PDF, status pemrosesan, konfirmasi hapus (D6) |
| Unggah / Edit Panduan | Admin | Form D2 (unggah: pratinjau PDF & Reset) + konfirmasi periksa kembali |
| Kelola Pengguna | Admin | Pengguna, role, Satker |
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
- Kebutuhan perangkat keras Production selain GPU (CPU/RAM/disk server aplikasi dan node GPU) untuk ±50 pengguna bersamaan, beserta perkiraan waktu review per usulan, kapasitas per GPU H100 NVL, dan jumlah GPU yang disarankan saat beban puncak.
- Cara mengamankan pemrosesan di GPU sewaan sesuai toleransi B1.
- Desain database fisik.
- Detail deployment berbasis kontainer (B7), termasuk cara instalasi di lingkungan tanpa internet (model & dependensi dibundel/dapat dipindahkan secara offline) dan cara menambah kapasitas GPU.

---

## 12. Tahapan Kerja yang Diminta dari AI Agent

1. ~~**Usulan desain**~~ — **selesai**, lihat `desain.md`.
2. ~~**Persetujuan** pemilik produk~~ — **disetujui** (2026-10-12).
3. **Implementasi lengkap** (langsung seluruh aplikasi, bukan bertahap; kekurangan diperbaiki berdasarkan umpan balik pemilik produk setelahnya): dimulai dari lingkungan Development (§8.2) yang dapat dijalankan dengan satu perintah, lalu backend API, frontend UI, konfigurasi kontainer Development & Production (B7), data seed (4 kategori), serta dokumentasi dan logging lengkap sesuai §8.1.
4. **Pengujian:** sertakan pengujian otomatis untuk logika inti (aturan pelabelan §7.1, versioning, override, hak akses, verifikasi rujukan E3) dan cara memverifikasi bahwa aplikasi tidak melakukan koneksi keluar.
5. **Evaluasi oleh pemilik produk** setelah aplikasi selesai, lalu perbaikan berdasarkan umpan balik.