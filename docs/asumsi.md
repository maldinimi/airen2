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

- Panduan yang dipakai review adalah versi terbaru berstatus SIAP dari setiap panduan yang tidak dihapus. Selama versi baru diproses, versi lama yang SIAP tetap dipakai — panduan tidak "hilang" sementara.
- Unggah panduan maksimal 50 file sekaligus, masing-masing ≤100 MB; nginx menerima hingga 1 GB per permintaan — PRD §8 membatasi per file.

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
- Kode checklist diisi manual oleh Admin (huruf dijadikan kapital, maks. 50 karakter), juga dapat diganti lewat Edit; harus unik di antara item yang ada. Kode yang sudah dihapus boleh dipakai lagi. Riwayat terhubung lewat `checklist_id`, sehingga ganti kode tidak memutus riwayat dan kode lama tetap tercatat; review lama tetap menampilkan kode saat itu.
- Urutan checklist (`no_urut`) diatur Admin lewat "Atur Urutan" (seret atau naik/turun) dan dipakai di tabel, database (urutan fisik tabel), serta urutan penilaian AI. Item baru otomatis ditaruh tepat setelah item berkode sebelumnya (E.02 di bawah E.01); mengganti kode tidak memindahkan item. Mengatur urutan tidak dicatat di `checklist_histori` karena isi item tidak berubah (tercatat di Audit Log).
- Urutan fisik tabel checklist (untuk pgAdmin "All Rows") dirapikan dengan CLUSTER hanya bila tabel tidak sedang dipakai (tunggu kunci ≤1 detik); bila sedang dibaca (mis. worker menunggu jawaban AI) dilewati dan dirapikan pada simpan berikutnya — agar simpan Admin tidak menahan seluruh aplikasi. Waktu `update_date` checklist dan `review.mulai_at` diambil dari jam database, karena worker bisa berjalan di server GPU lain.
- Status checklist per item: Nonaktif = item tetap tersimpan, tetapi tidak dinilai AI dan tidak dihitung dalam label LOLOS; minimal satu item harus Aktif — PRD tidak mengatur status item, ini tafsiran paling aman agar label tetap "semua item (aktif) terpenuhi".
- Kolom jejak checklist: `created_by`/`create_date` = siapa & kapan item ditambah, `update_by`/`update_date` = perubahan terakhir. Menyimpan tanpa perubahan isi tidak dicatat dan tidak membuat riwayat. Isi checklist review lama disusun ulang dari waktu review dimulai (`review.mulai_at`).
