"""Membuat PDF contoh (TOR, RAB, Panduan) untuk mencoba aplikasi di mode dev/tiruan.
Jalankan: docker compose run --rm -v ./contoh:/contoh api python /contoh/buat_contoh.py"""
from fpdf import FPDF


def pdf(nama, isi, tabel=None):
    d = FPDF()
    d.set_font("helvetica", size=11)
    d.add_page()
    for p in isi:
        if p == "<hlm>":
            d.add_page()
            continue
        if p.isupper() or p.startswith(("BAB", "Pasal")):
            d.set_font("helvetica", "B", 12)
        d.multi_cell(0, 6, p)
        d.set_font("helvetica", size=11)
        d.ln(3)
    if tabel:
        with d.table(col_widths=(50, 15, 15, 25, 30)) as t:
            for b in tabel:
                r = t.row()
                for s in b:
                    r.cell(s)
    d.output(f"/contoh/{nama}")


pdf("tor-contoh.pdf", [
    "KERANGKA ACUAN KERJA (TOR)", "Rincian Output: Layanan Aplikasi Pemerintahan Digital Terintegrasi",
    "BAB I PENDAHULUAN", "1.1 Latar Belakang",
    "Transformasi digital pemerintahan merupakan prioritas pembangunan nasional sebagaimana diamanatkan Peraturan Presiden Nomor 95 Tahun 2018 tentang Sistem Pemerintahan Berbasis Elektronik.",
    "Saat ini masih terdapat 120 aplikasi layanan yang belum terintegrasi sehingga menyulitkan masyarakat.",
    "1.2 Dasar Hukum", "a. Peraturan Presiden Nomor 95 Tahun 2018 tentang SPBE.", "b. Peraturan Menteri Keuangan tentang Standar Biaya Masukan Tahun Anggaran 2027.",
    "1.3 Tujuan dan Sasaran", "Tujuan kegiatan adalah mengintegrasikan layanan aplikasi pemerintah agar masyarakat memperoleh layanan yang cepat dan mudah.",
    "<hlm>", "BAB II KELUARAN DAN PELAKSANAAN", "2.1 Indikator Keluaran",
    "Keluaran kegiatan berupa 10 aplikasi layanan terintegrasi dengan target 50.000 pengguna aktif pada akhir tahun 2027.",
    "2.2 Metode Pelaksanaan", "Kegiatan dilaksanakan secara swakelola melalui tahapan analisis kebutuhan, pengembangan, uji coba, dan sosialisasi.",
    "2.3 Jadwal Pelaksanaan", "Kegiatan dilaksanakan mulai Januari sampai dengan Desember 2027.",
    "2.4 Penerima Manfaat", "Penerima manfaat kegiatan adalah masyarakat umum dan aparatur sipil negara pada instansi pusat dan daerah.",
])
pdf("rab-contoh.pdf", ["RENCANA ANGGARAN BIAYA (RAB)", "Rincian Output: Layanan Aplikasi Pemerintahan Digital Terintegrasi"], [
    ["Komponen", "Volume", "Satuan", "Harga Satuan", "Jumlah"],
    ["Honor narasumber", "40", "OJ", "1.700.000", "68.000.000"],
    ["Paket rapat fullday", "200", "OK", "450.000", "90.000.000"],
    ["Pengembangan aplikasi", "10", "Paket", "150.000.000", "1.500.000.000"],
    ["Sosialisasi", "5", "Kegiatan", "60.000.000", "300.000.000"],
])
pdf("panduan-contoh.pdf", [
    "PERATURAN CONTOH TENTANG PENYUSUNAN TOR DAN RAB", "BAB I KETENTUAN UMUM",
    "Pasal 1", "(1) TOR wajib memuat latar belakang, dasar hukum, tujuan, indikator keluaran, metode, jadwal, dan penerima manfaat.",
    "(2) Indikator keluaran wajib dinyatakan dengan target kuantitatif dan satuan yang jelas.",
    "Pasal 2", "(1) Honor narasumber paling tinggi Rp1.700.000 per orang jam.",
    "(2) Paket rapat fullday di dalam kantor paling tinggi Rp450.000 per orang per kegiatan.",
    "(3) Setiap komponen biaya pada RAB wajib memiliki dasar kegiatan pada TOR.",
])
print("PDF contoh dibuat di folder contoh/")
