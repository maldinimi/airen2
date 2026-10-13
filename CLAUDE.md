# CLAUDE.md — Instruksi untuk AI Agent

Aplikasi web untuk mereview dokumen TOR & RAB usulan anggaran dengan AI lokal: menilai pemenuhan checklist (Screening 1), merekomendasikan kategori K1–K4 (Screening 2), lalu reviewer manusia memverifikasi dan memfinalkan. Dokumen bersifat sensitif.

## Dokumen acuan

| File | Isi | Status |
| --- | --- | --- |
| `prd.md` | **Apa & mengapa.** Kebutuhan, aturan bisnis, batasan WAJIB. | Disetujui |
| `desain.md` | **Bagaimana.** Teknologi, arsitektur, database, alur AI, UI, deployment. | Disetujui |

- Baca keduanya sampai habis sebelum menulis kode.
- Bila bertentangan: **PRD menang** untuk kebutuhan & aturan bisnis; **desain.md menang** untuk pilihan teknis.
- Boleh menyimpang dari desain.md bila ada alasan kuat (mis. library/model tidak tersedia atau terbukti lebih buruk). Catat penyimpangan beserta alasannya di desain.md.
- `prd.md` tetap berisi apa/mengapa saja — jangan tambahkan detail teknis ke sana.

## Cara kerja

- **Langsung implementasi lengkap** (PRD §12 langkah 3–4), bukan prototipe dan bukan bertahap yang berhenti di tengah. Pemilik produk akan mengevaluasi setelah aplikasi selesai dan memberi umpan balik.
- **Hal kecil yang tidak diatur** (mis. lupa password tanpa email, batas waktu sesi, format tanggal): pakai asumsi wajar, jangan berhenti untuk bertanya. Catat setiap asumsi di `docs/asumsi.md` (satu baris: asumsi + alasan) agar mudah ditinjau pemilik produk.
- Bertanya hanya bila sebuah keputusan akan melanggar ketentuan **WAJIB** di PRD.
- Nama model AI di desain.md dipilih per Oktober 2026. Saat implementasi, pastikan model tersebut tersedia dan berlisensi terbuka; bila tidak, pilih penggantinya yang setara dan catat di desain.md.

## Aturan yang tidak boleh dilanggar

1. **Offline saat runtime (B1).** Tidak ada panggilan ke layanan eksternal, CDN, telemetri, atau analytics. Semua aset frontend (font, PDF.js, ikon) dibundel. Satu-satunya pengecualian: terowongan terenkripsi ke node AI di GPU sewaan (desain §2.4).
2. **Label dihitung oleh kode, bukan oleh LLM.** LOLOS ⇔ semua item checklist terpenuhi (PRD §7.1).
3. **100% rujukan harus benar (E3).** LLM hanya merujuk ID elemen. Halaman, lokasi, bbox, dan kutipan **diambil dari database**. Rujukan yang tidak lolos verifikasi dibuang (desain §4.3). Sebelum hasil review disimpan, jalankan pemeriksaan invarian: setiap kutipan ada di teks elemen pada halaman yang dirujuk. Jika gagal, review gagal — jangan simpan rujukan yang salah.
4. **Snapshot tidak berubah.** Versi checklist, kategori, dan panduan tidak pernah diubah atau dihapus. Hasil AI tidak pernah ditimpa; override disimpan terpisah (PRD O1–O8).
5. **Semua komponen berjalan di kontainer (B7).** Developer baru harus bisa menjalankan aplikasi lengkap dengan `cp .env.dev .env && make setup && make up`. Kemudahan menjalankan adalah kunci.
6. **Development harus jalan di laptop RTX A6000 16 GB** dengan model entry level, dan di **mode AI tiruan** tanpa GPU (desain §2.1).
7. **Bahasa Indonesia** untuk seluruh antarmuka, keluaran AI, pesan error untuk pengguna, dan dokumentasi pengguna.
8. **Hak akses dicek di backend** untuk setiap endpoint dan setiap unduhan file (role + Satker).
9. **Log** terstruktur dengan `trace_id` per review; tidak memuat password, token, atau isi dokumen utuh (PRD §8.1).

## Konvensi

- Istilah domain memakai Bahasa Indonesia sesuai desain.md (`usulan`, `revisi`, `checklist_item`, `override`, …), baik di database, API, maupun kode.
- Dokumentasi di `docs/`: arsitektur, API, instalasi offline, panduan pengguna per role, panduan administrasi, `asumsi.md`. README di root.
- Setiap fungsi/endpoint penting diberi docstring (tujuan, input, output, error). Logika yang tidak jelas dari kodenya (aturan label, versioning, override, fingerprint) diberi komentar alasannya.

## Definisi selesai

- `make up` (dev & mode tiruan) berjalan dari repo bersih tanpa langkah manual lain.
- Seluruh alur PRD §5 dapat dijalankan ujung ke ujung di mode dev: buat usulan → ajukan review → hasil AI → override → finalkan → unggah revisi → riwayat & perbandingan.
- Pengujian otomatis lulus: aturan label, override & nilai final, versioning, hak akses, transisi status, verifikasi rujukan, fingerprint, tidak ada koneksi keluar (desain §6).
- Seed 4 kategori persis sesuai PRD C1, plus akun admin awal.
- Dokumentasi PRD §8.1 lengkap.
