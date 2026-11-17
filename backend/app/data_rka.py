"""Hierarki anggaran RKA-K/L untuk form Pengajuan Baru: Program → Kegiatan → KRO → RO (dropdown bertingkat).

Sumber: "Revisi_laporan_renja_2026.xlsx" (sheet "Laporan RENJA KL", kolom program, kegiatan, kro, ro; format "kode-nama").
Jalur dobel disimpan sekali; kegiatan tanpa KRO/RO dilewati (tidak dapat dipilih sampai RO):
7452 Penyelenggaraan Pelindungan Data Pribadi Masyarakat
7454 Penyidikan di ruang digital
7456 Tata kelola pengawasan ruang digital
7658 SDM Vokasi Bidang Komdigi
7899 Tata Kelola Pengembangan Ekosistem Digital Nasional.
Kolom unit eselon & prioritas tidak dipakai. Usulan menyimpan salinan kode & nama tiap tingkat (usulan.hierarki),
sehingga memperbarui daftar ini tidak mengubah usulan lama.
Setiap tingkat: (kode, nama, anak). Kode RO memuat kode kegiatan & KRO-nya, seperti di RKA-K/L.
"""

PROGRAM = [
    ('059.GH', 'Program Komunikasi Publik dan Media', [
        ('4511', 'Implementasi Undang-Undang Keterbukaan Informasi Publik', [
            ('PBM', 'Kebijakan Bidang Pelayanan Publik', [
                ('001', 'Rekomendasi hasil Survey Indeks Keterbukaan Informasi Publik'),
            ]),
            ('QCB', 'Perkara Hukum Lembaga', [
                ('001', 'Sengketa Informasi Publik yang diselesaikan'),
            ]),
            ('QIC', 'Pengawasan dan Pengendalian Lembaga', [
                ('001', 'Badan Publik Pemerintah yang Informatif'),
            ]),
        ]),
        ('4523', 'Penguatan Lembaga Pers dan Jurnalis', [
            ('BMB', 'Komunikasi Publik', [
                ('001', 'Layanan Pengembangan Pers dan Kerjasama Dewan Pers dengan Masyarakat Pers'),
            ]),
            ('PBD', 'Kebijakan Bidang Hukum dan HAM', [
                ('002', 'Rekomendasi Terkait Tanggung Jawab Perusahaan Platform Digital untuk Mendukung Jurnalisme Berkualitas'),
            ]),
            ('PDD', 'Standarisasi Lembaga', [
                ('001', 'Perusahaan Pers yang diverifikasi'),
                ('002', 'Perusahaan Pers yang Mengikuti Pendampingan Pengembangan Kapasitas Pengelolaan Perusahaan Pers'),
            ]),
            ('PDI', 'Sertifikasi Profesi dan SDM', [
                ('001', 'Wartawan Peserta Fasilitasi Uji Kompetensi Wartawan'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('001', 'Layanan Pengaduan Masyarakat atas Kasus Pers'),
                ('002', 'Layanan Ahli Pers'),
            ]),
            ('SCA', 'Pelatihan Bidang Komunikasi dan Informatika', [
                ('001', 'Wartawan Peserta Pelatihan Jurnalistik'),
            ]),
        ]),
        ('4524', 'Peningkatan Kualitas Konten Penyiaran', [
            ('BMB', 'Komunikasi Publik', [
                ('301', 'Diseminasi Penyiaran'),
            ]),
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('PBM', 'Kebijakan Bidang Pelayanan Publik', [
                ('051', 'Rekomendasi Hasil Pemeringkatan Indeks Penyiaran Indonesia'),
                ('052', 'Rekomendasi Pengembangan Kebijakan dan Sistem Penyiaran'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('701', 'Layanan Pengaduan Masyarakat Terhadap Konten Siaran TV dan Radio'),
            ]),
            ('QIC', 'Pengawasan dan Pengendalian Lembaga', [
                ('501', 'Lembaga Penyiaran TV dan Radio yang diawasi'),
            ]),
            ('SCA', 'Pelatihan Bidang Komunikasi dan Informatika', [
                ('601', 'Pelatihan SDM Bidang Penyiaran'),
            ]),
        ]),
        ('7431', 'Penguatan Komunikasi dan Informasi Publik Nasional', [
            ('AAG', 'Peraturan Menteri', [
                ('001', 'Rancangan Peraturan Menteri tentang Layanan Komunikasi dan Informasi Publik Berbasis Digital Bagi Penyandang Disabilitas'),
            ]),
            ('AFA', 'Norma, Standard, Prosedur dan Kriteria', [
                ('001', 'NSPK Bidang Komunikasi Publik'),
            ]),
            ('BAA', 'Pelayanan Publik kepada masyarakat', [
                ('001', 'Layanan Pemanfaatan Informasi Media Cetak dan Koleksi Benda Bersejarah Bagi Masyarakat'),
                ('002', 'Layanan Informasi Benda-Benda Bersejarah di Bidang Komunikasi dan Informasi'),
            ]),
            ('FAC', 'Peningkatan Kapasitas Aparatur Negara', [
                ('001', 'Peningkatan Kapasitas SDM Bidang Keterbukaan Informasi Publik'),
                ('002', 'Bimbingan Teknis Bidang Komunikasi Publik'),
            ]),
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('PAA', 'Undang-Undang', [
                ('001', 'Rancangan Revisi UU KIP No. 14 Tahun 2008'),
            ]),
            ('PAD', 'Peraturan Presiden', [
                ('001', 'Rancangan Peraturan Presiden Sistem Komunikasi Publik Nasional (SKPN)'),
            ]),
            ('PBL', 'Kebijakan Bidang Tata Kelola Pemerintahan', [
                ('001', 'Rekomendasi hasil survey Komunikasi Pembangunan dan Informasi Publik (KPIP)'),
            ]),
            ('PEF', 'Sosialisasi dan Diseminasi', [
                ('001', 'Sosialisasi dan Bimtek Kebijakan Standarisasi Pengelolaan Akses dan Aset Konten Informasi Publik'),
            ]),
            ('PFA', 'Norma, Standard, Prosedur dan Kriteria', [
                ('001', 'NSPK Pengelolaan Akses dan Aset Konten Informasi Publik'),
                ('002', 'NSPK Standarisasi Konten Program Prioritas Pemerintah'),
                ('003', 'NSPK Bidang Konkuren Komunikasi Publik'),
            ]),
            ('QMA', 'Data dan Informasi Publik', [
                ('001', 'Rencana komunikasi strategis pemerintah tahunan'),
            ]),
            ('QMB', 'Komunikasi Publik', [
                ('001', 'Konten Informasi Publik Program Prioritas Pemerintah'),
                ('003', 'Monitoring Isu dalam Pengelolaan Komunikasi Publik'),
                ('004', 'Pengelolaan Konten Kontra Narasi'),
                ('005', 'Manajemen pengelolaan komunikasi strategis pemerintah'),
                ('006', 'Pengelolaan krisis komunikasi nasional'),
                ('007', 'Pengelolaan Komunikasi Publik Makan Bergizi Gratis'),
                ('008', 'Supervisi Implementasi Konkuren Bidang Komunikasi Publik'),
                ('009', 'Pengelolaan komunikasi publik terkait Pertahanan Semesta'),
                ('011', 'Pengelolaan Komunikasi Publik terkait Akselerasi Investasi dan Perdagangan Global'),
                ('012', 'Pengelolaan Komunikasi Publik Terkait Ketahanan Energi'),
            ]),
        ]),
        ('7432', 'Pengembangan Ekosistem Media, Kehumasan, dan Kemitraan Komunikasi Publik', [
            ('AAG', 'Peraturan Menteri dan Kepala Lembaga', [
                ('002', 'Peraturan Menteri Komdigi terkait Pengembangan Kemitraan Komunikasi Strategis'),
                ('003', 'Rancangan Peraturan Menteri terkait Standar Kompentesi JF Penyiaran'),
            ]),
            ('ACD', 'Perizinan Lembaga', [
                ('001', 'Pengelolaan penerbitan izin dan rekomendasi kegiatan jurnalistik media asing'),
            ]),
            ('FAC', 'Peningkatan Kapasitas Aparatur Negara', [
                ('001', 'Pembinaan Jabatan Fungsional Bidang Penyiaran'),
                ('002', 'Pembinaan Jabatan Fungsional Bidang Komunikasi'),
            ]),
            ('PBM', 'Kebijakan Bidang Pelayanan Publik', [
                ('001', 'Rekomendasi Kebijakan Terkait Pengembangan Ekosistem Media'),
            ]),
            ('QDB', 'Fasilitasi dan Pembinaan Lembaga', [
                ('001', 'Pengembangan Kelembagaan Kehumasan Pemerintah (K/L/D dan BUMN)'),
                ('002', 'Pengembangan Kemitraan Komunikasi Strategis'),
            ]),
            ('QMB', 'Komunikasi Publik', [
                ('001', 'Pengelolaan Relasi Media'),
                ('002', 'Pengelolaan Kerja Sama Media Massa'),
                ('003', 'Pengelolaan komunikasi publik terkait Program Kesehatan'),
                ('004', 'Pengelolaan komunikasi publik terkait Ketahanan Pangan'),
                ('006', 'Pengelolaan Komunikasi Publik terkait Pembangunan Desa, Koperasi, UMKM'),
                ('007', 'Pengelolaan Komunikasi Publik terkait Swasembada Air'),
                ('008', 'Pengelolaan Komunikasi Publik terkait Perlindungan Sosial'),
                ('009', 'Pengelolaan Komunikasi Publik terkait Program Pendidikan'),
            ]),
        ]),
    ]),
    ('059.GK', 'Program Pengembangan dan Penguatan Ekosistem dan Ruang Digital', [
        ('7440', 'Pengembangan Aplikasi dan infrastruktur digital Pemerintahan Terpadu', [
            ('CBT', 'Prasarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Manajemen Pengembangan Pusat Data Nasional'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('002', 'OM Teknologi Baru Pemerintah Digital'),
            ]),
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'OM Layanan Aplikasi Pemerintah Digital'),
                ('002', 'OM Sistem Penghubung Layanan Pemerintah (SPLP)'),
                ('004', 'OM SPPT-TI'),
            ]),
            ('RDS', 'OP Prasarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'OM Pusat Data Nasional'),
                ('002', 'OM Government Cloud'),
            ]),
            ('UAB', 'Sistem Informasi Pemerintahan', [
                ('001', 'Sistem Penghubung Layanan Pemerintah'),
                ('002', 'Sistem Peradilan Pidana Terpadu berbasis Teknologi Informasi'),
                ('003', 'Portal Pelayanan Publik'),
                ('005', 'Jaringan Intra Pemerintah'),
            ]),
        ]),
        ('7441', 'Tata kelola teknologi pemerintah digital', [
            ('AAG', 'Peraturan Menteri dan Kepala Lembaga', [
                ('001', 'PM Pendekatan Kota Cerdas'),
                ('002', 'PM Penyelenggaraan Situs Web Instansi Pusat dan Pemerintah Daerah'),
            ]),
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Rekomendasi Kebijakan Tata Kelola Pusat Data Pemerintah dan Ekosistem Pendukungnya'),
                ('005', 'Pemberian Pertimbangan Kelaikan Infrastruktur Pemerintah Digital'),
                ('006', 'Rekomendasi Kebijakan Penyelenggaraan Government Technology'),
            ]),
            ('BAH', 'Pelayanan Publik Lainnya', [
                ('001', 'Layanan Evaluasi Belanja SPBE (Clearance) Instansi Pusat dan Pemerintah Daerah'),
                ('002', 'Penyelenggaraan PSE Lingkup Publik'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Pengelolaan Sistem Layanan Clearance SPBE'),
                ('002', 'OM Layanan Pendaftaran PSE Lingkup Publik'),
            ]),
            ('FAE', 'Pemantauan dan Evaluasi serta Pelaporan', [
                ('001', 'Pemantauan dan Evaluasi Kebijakan Teknologi Pemerintah Digital'),
            ]),
            ('PAG', 'Peraturan Menteri dan Kepala Lembaga', [
                ('001', 'PM Manajemen Aset TIK dan Manajemen Layanan SPBE'),
                ('003', 'PM Penyelenggaraan Pusat Data Nasional'),
            ]),
            ('PBO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Masterplan Pemanfaatan Teknologi Baru di Pemerintahan'),
            ]),
        ]),
        ('7442', 'Percepatan transformasi digital daerah', [
            ('UBA', 'Fasilitasi dan Pembinaan Pemerintah Daerah', [
                ('001', 'Pendampingan Penyusunan Masterplan Provinsi Cerdas'),
                ('002', 'Use case teknologi digital pada kota cerdas'),
                ('003', 'Pendampingan Smart City - Pusat'),
            ]),
        ]),
        ('7443', 'Pengembangan Ekosistem untuk Startup Digital dan Gim Nasional', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Pengukuran Ekosistem Startup Digital'),
                ('002', 'Regulasi dan Kebijakan Strategis terkait Industri Gim'),
                ('003', 'Rekomendasi Kebijakan terkait Rancangan Peraturan Pemerintah Ekosistem Digital'),
            ]),
            ('BDJ', 'Fasilitasi dan Pembinaan Start Up', [
                ('001', 'Kemitraan dan Investasi Gim'),
            ]),
            ('FAB', 'Sistem Informasi Pemerintahan', [
                ('002', 'Sistem Informasi Ekosistem Gim'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('001', 'Layanan klasifikasi gim'),
            ]),
            ('QDJ', 'Fasilitasi dan Pembinaan Start Up', [
                ('001', 'Startup Digital Terakselerasi'),
                ('002', 'Akselerator dan Inkubator Gim'),
            ]),
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Sistem Klasifikasi Gim/IGRS (OP)'),
            ]),
            ('UAB', 'Sistem Informasi Pemerintahan', [
                ('002', 'Sistem Klasifikasi Gim/IGRS'),
            ]),
            ('UBA', 'Fasilitasi dan Pembinaan Pemerintah Daerah', [
                ('001', 'Eksosistem Startup Digital Kota'),
            ]),
        ]),
        ('7444', 'Pemanfaatan dan Pengembangan Ekosistem AI dan Teknologi Baru', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Kajian terkait Pengembangan Industri AI dan Teknologi Baru'),
            ]),
            ('BDH', 'Fasilitasi dan Pembinaan Badan Usaha', [
                ('001', 'Fasilitasi Pemanfaatan Teknologi Digital di Sektor Energi'),
            ]),
            ('BDI', 'Fasilitasi dan Pembinaan Industri', [
                ('001', 'Fasilitasi pengembangan inovasi kecerdasan artifisial dan teknologi baru'),
                ('002', 'Fasilitasi kemitraan dan investasi untuk pengembangan industri teknologi baru'),
            ]),
            ('FAB', 'Sistem Informasi Pemerintahan', [
                ('001', 'Sistem informasi, publikasi, dan promosi bidang AI dan teknologi baru'),
            ]),
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('PAG', 'Peraturan Menteri dan Kepala Lembaga', [
                ('001', 'PM terkait Roadmap Emerging Technologies'),
            ]),
            ('QDC', 'Fasilitasi dan Pembinaan Masyarakat', [
                ('001', 'Pemanfaatan Teknologi Digital di Sektor Pertanian'),
                ('002', 'Pemanfaatan Teknologi Digital di Sektor Perikanan'),
            ]),
            ('QDI', 'Fasilitasi dan Pembinaan Industri', [
                ('001', 'Sandbox Regulasi Digital'),
            ]),
            ('QDJ', 'Fasilitasi dan Pembinaan Start Up', [
                ('001', 'Fasilitasi Green Tech'),
            ]),
        ]),
        ('7445', 'Pengembangan Industri Pos dan Penyiaran', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Rekomendasi teknis tentang penyelenggaraan Layanan Pos Universal'),
                ('002', 'Rekomendasi Kebijakan Peningkatan Postal Development Level Indonesia'),
            ]),
            ('BDB', 'Fasilitasi dan Pembinaan Lembaga', [
                ('001', 'Fasilitasi Peningkatan Kualitas Lembaga Penyiaran Jasa Penyiaran'),
            ]),
            ('CBT', 'Prasarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Kemitraan Penyelenggara Pos dengan Mitra Strategis'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Sistem Informasi Pengembangan Pos (OM)'),
            ]),
            ('DDB', 'Penelitian dan Pengembangan Purwarupa', [
                ('001', 'Prototype Desain Prangko'),
            ]),
            ('FAB', 'Sistem Informasi Pemerintahan', [
                ('002', 'Sistem Informasi Manajemen LPU'),
                ('005', 'Sistem Informasi Pengembangan Pos'),
            ]),
            ('FAE', 'Pemantauan dan Evaluasi serta Pelaporan', [
                ('001', 'Pengawasan dan Penilaian Indeks Kinerja dan Status Mutu serta Pengawasan Iklim Usaha Pos'),
            ]),
            ('PAA', 'Undang-Undang', [
                ('001', 'Rancangan UU Pos'),
            ]),
            ('PAG', 'Peraturan Menteri dan Kepala Lembaga', [
                ('001', 'Rancangan Peraturan Menteri Dalam Penyelenggaraan Penyiaran Menggunakan Free To Air (FTA) Satelit'),
            ]),
            ('PBO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Rekomendasi Kebijakan terkait Penyelenggaraan Penyiaran Radio Secara Simulcast'),
                ('002', 'Rekomendasi Kebijakan Penyelenggaraan Penyiaran Menggunakan Integrated Broadcast Broadband (IBB)'),
                ('003', 'Peta Jalan Penyiaran Nasional'),
                ('004', 'Rekomendasi Kebijakan Terkait Tata Kelola Industri Penyiaran'),
            ]),
            ('QDH', 'Fasilitasi dan Pembinaan Badan Usaha', [
                ('200', 'Fasilitasi Digitalisasi Pos'),
            ]),
            ('RBT', 'Prasarana Bidang Teknologi Informasi dan Komunikasi', [
                ('008', 'Kemitraan Kantor Layanan Pos Universal (LPU) yang Bermitra dengan Koperasi Merah Putih (KMP)'),
            ]),
        ]),
        ('7446', 'Layanan Publik Bidang Pos Logistik, Penyiaran, Telekomunikasi, dan Informatika', [
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Sistem Informasi Manajemen Layanan Publik Bidang Penyiaran (OM)'),
            ]),
            ('FAB', 'Sistem Informasi Pemerintahan', [
                ('003', 'Sistem Informasi Manajemen Layanan Publik Bidang Penyiaran'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('001', 'Layanan Publik Bidang Telekomunikasi'),
                ('002', 'Layanan Publik Bidang Penyiaran'),
                ('003', 'Layanan Publik Bidang Pos'),
            ]),
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Sistem Perizinan Telekomunikasi (OM)'),
            ]),
            ('UAB', 'Sistem Informasi Pemerintahan', [
                ('001', 'Sistem Perizinan Online Bidang Pos'),
            ]),
        ]),
        ('7447', 'Pengelolaan data dan pengendalian bidang ekosistem digital', [
            ('BIF', 'Pengawasan dan Pengendalian Layanan', [
                ('001', 'Layanan Pengawasan dan Pengendalian Sektor Telekomunikasi'),
                ('002', 'Layanan Pengawasan dan Pengendalian Sektor Pos'),
                ('003', 'Layanan Pengawasan dan Pengendalian Sektor Penyiaran'),
            ]),
            ('CAN', 'Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Perangkat Pengukuran QoS Penyiaran dan Perangkat Pengukuran Capaian Komitmen Jaringan Telekomunikasi'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Sistem informasi pengolahan data dan pelaporan penyelenggaraan pos dan Informatika (OP)'),
            ]),
            ('FAB', 'Sistem Informasi Pemerintahan', [
                ('001', 'Sistem informasi pengolahan data dan pelaporan penyelenggaraan pos dan Informatika'),
            ]),
        ]),
        ('7448', 'Pengembangan keterampilan digital dasar dan literasi digital bagi masyarakat', [
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('SCA', 'Pelatihan Bidang Komunikasi dan Informatika', [
                ('001', 'Pelatihan Keterampilan Digital Dasar'),
                ('002', 'Pelatihan literasi digital'),
            ]),
        ]),
        ('7449', 'Pengembangan Talenta Digital Masyarakat', [
            ('PDI', 'Sertifikasi Profesi dan SDM', [
                ('001', 'Pelatihan berbasis SKKNI bidang Komdigi'),
            ]),
            ('SCA', 'Pelatihan Bidang Komunikasi dan Informatika', [
                ('001', 'Pemberdayaan Talenta Digital'),
                ('002', 'Pelatihan talenta digital'),
            ]),
        ]),
        ('7450', 'Pengembangan Kompetensi SDM Aparatur dan Kepemimpinan Digital', [
            ('DCA', 'Pelatihan Bidang Komunikasi dan Informatika', [
                ('002', 'Pelatihan Aparatur Digital Skema Pembiayaan PNBP'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('996', 'Layanan Pendidikan dan Pelatihan Lainnya'),
            ]),
            ('SCA', 'Pelatihan Bidang Komunikasi dan Informatika', [
                ('001', 'Pelatihan Aparatur Digital'),
                ('002', 'Pelatihan Kepemimpinan Nasional Bidang Digital'),
            ]),
        ]),
        ('7451', 'Pengembangan Ekosistem SDM Komdigi', [
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'OM Sistem informasi Pengembangan SDM Digital Nasional'),
            ]),
        ]),
        ('7453', 'Pengendalian di ruang digital', [
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('QIC', 'Pengawasan dan Pengendalian Lembaga', [
                ('001', 'Peningkatan Kapasitas Sistem Pengendalian Tata Kelola PSE dan Transaksi PSE'),
            ]),
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'OM Sistem Pengendalian Tata Kelola PSE dan Transaksi PSE'),
                ('005', 'Sistem Penanganan dan Penanggulangan Konten Ilegal'),
            ]),
        ]),
        ('7455', 'Penyelenggaraan pengawasan aktivitas dan transaksi elektronik', [
            ('BAH', 'Pelayanan Publik Lainnya', [
                ('006', 'Layanan Pengelolaan PNBP Domain ID'),
            ]),
        ]),
        ('7657', 'Penyelenggaraan Pendidikan Tinggi Bidang Komdigi', [
            ('ADE', 'Akreditasi Lembaga', [
                ('001', 'Akreditasi Program Studi pada Perguruan Tinggi Kementerian Komdigi'),
            ]),
            ('AEC', 'Kerja sama', [
                ('001', 'Kerjasama Program Studi Perguruan Tinggi dengan Industri Digital'),
            ]),
            ('CAA', 'Sarana Bidang Pendidikan', [
                ('001', 'Peralatan dan Fasilitas Pengembangan Kependidikan Perguruan Tinggi Bidang Komdigi'),
            ]),
            ('DBA', 'Pendidikan Tinggi', [
                ('001', 'Peserta didik perguruan tinggi bidang komdigi'),
                ('002', 'Penelitian dan Inovasi Bidang Komdigi'),
                ('003', 'Pengabdian Masyarakat Bidang Komdigi'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('001', 'Peningkatan karir dosen'),
            ]),
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
        ]),
    ]),
    ('059.GL', 'Program Pengembangan dan Penguatan Infrastruktur Digital', [
        ('7433', 'Akselerasi pengembangan infrastruktur digital', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Fasilitasi Akselerasi Penyediaan Fiber Optik Pada Daerah (kecamatan)'),
                ('002', 'Rekomendasi Rancangan Kebijakan tentang Penyediaan Infrastruktur Pasif'),
            ]),
            ('BDH', 'Fasilitasi dan Pembinaan Badan Usaha', [
                ('001', 'Fasilitasi, Koordinasi dan Kerjasama dalam rangka Mendukung Percepatan Penyelenggaraan SKKL'),
            ]),
            ('FBB', 'Fasilitasi dan Pembinaan Pemerintah Desa', [
                ('001', 'Fasilitasi Penyelenggaraan Layanan Seluler pada Wilayah Pelayanan Universal Telekomunikasi dan Informatika'),
                ('002', 'Fasilitasi Penyelenggaraan Layanan Akses Internet Tetap pada Wilayah Tidak Terjangkau Serat Optik'),
                ('003', 'Akses Internet Tetap Pitalebar untuk Pelaku Usaha Rumah Tangga dan Fasilitas Umum (Fasilitas Pendidikan, Kesehatan dan Kantor Pemerintah)'),
            ]),
            ('PBO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Rekomendasi Kebijakan Penyelenggaraan Layanan Telekomunikasi Universal'),
                ('002', 'Rekomendasi Kebijakan tentang Penyediaan Sistem Komunikasi Nasional untuk Pelindungan Masyarakat dan Penanggulangan Bencana (PMPB)'),
            ]),
            ('QDB', 'Fasilitasi dan Pembinaan Lembaga', [
                ('001', 'Lembaga/Instansi yang Terintegrasi Sistem Informasi Kebencanaan'),
            ]),
            ('QDH', 'Fasilitasi dan Pembinaan Badan Usaha', [
                ('001', 'Fasilitasi Penggelaran Infrastruktur dan Peningkatan Kualitas Layanan Seluler 4G oleh Penyelenggara Jaringan Bergerak Seluler'),
                ('002', 'Fasilitasi Penyelenggara Jaringan Bergerak Seluler dalam Penggelaran Jaringan 5G di Kawasan dan sektor Prioritas'),
            ]),
            ('RDS', 'OP Prasarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Sistem Informasi Kebencanaan (OM)'),
            ]),
            ('UBA', 'Fasilitasi dan Pembinaan Pemerintah Daerah', [
                ('001', 'Kabupaten/Kota yang difasilitasi Menerapkan Infrastruktur Pasif Bersama (Tiang Bersama dan SJUT)'),
                ('002', 'Fasilitasi Pengembangan Gigabit City'),
                ('004', 'Kab/Kota yang Sudah Terintegrasi Layanan Panggilan Darurat 112 dan Sistem Informasi Bencana'),
            ]),
        ]),
        ('7434', 'Penataan Spektrum Frekuensi Radio dan Standarisasi Perangkat Digital', [
            ('PBO', 'Kebijakan Bidang Teknologi Informasi', [
                ('401', 'Rekomendasi Kebijakan Penyediaan Spektrum Frekuensi Radio untuk Layanan Broadband'),
                ('402', 'Rekomendasi Kebijakan Untuk Perlindungan Pengguna Perangkat Telekomunikasi'),
                ('403', 'Rekomendasi Kebijakan Standardisasi Perangkat Digital Data Center, Cloud, CDN, Internet Exchange dan Infrastruktur Pasif'),
                ('404', 'Rekomendasi Kebijakan Pengaturan Spektrum Frekuensi Radio untuk Keperluan Layanan Publik dan Instansi Pemerintah'),
                ('405', 'Rekomendasi Kebijakan Pengelolaan Limbah Elektronik (e-waste)'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('501', 'Layanan Kesesuaian dan Harmonisasi Perangkat Digital'),
            ]),
            ('QDB', 'Fasilitasi dan Pembinaan Lembaga', [
                ('601', 'Fasilitasi Pengembangan Industri Perangkat Digital Dalam Negeri'),
            ]),
        ]),
        ('7435', 'Pengembangan Strategi dan Kebijakan Infrastruktur Digital', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('202', 'Rekomendasi Kebijakan Evaluasi Penerapan Pentarifan, Interkoneksi Dan Kompetisi'),
                ('303', 'Rekomendasi Kebijakan Optimalisasi Pemanfaatan Spektrum Frekuensi Radio'),
                ('505', 'Rekomendasi Kebijakan Peningkatan Dan Penyediaan Layanan Broadband Pada Pemerintah Daerah'),
                ('606', 'Rekomendasi Kebijakan Strategi Gigabyte City'),
                ('707', 'Rekomendasi Modernisasi Kebijakan Infrastruktur Digital Atas Reviu Regulasi Penyelenggaraan Telekomunikasi'),
                ('909', 'Rekomendasi Kebijakan Regulatory Sandbox layanan dan teknologi infrastruktur digital'),
                ('910', 'Rekomendasi Kebijakan Percepatan Implementasi IPv6'),
            ]),
            ('PBO', 'Kebijakan Bidang Teknologi Informasi', [
                ('101', 'Rekomendasi Kebijakan Peta Jalan (Roadmap) Infrastruktur Digital'),
                ('404', 'Rekomendasi Kebijakan Rasionalisasi Regulatory Cost'),
                ('808', 'Rekomendasi Kebijakan Pengembangan Data Center'),
            ]),
        ]),
        ('7436', 'Layanan Publik Bidang Sumber Daya dan Perangkat Digital', [
            ('BAH', 'Pelayanan Publik Lainnya', [
                ('602', 'Akreditasi, Sertifikasi, dan Recognisi Ruang Lingkup BBPPT'),
                ('604', 'Layanan Kalibrasi Alat Ukur Perangkat Telekomunikasi dan Digital'),
                ('606', 'Layanan Pengelolaan Bisnis Proses Pengujian Perangkat Telekomunikasi Digital dan Kalibrasi Alat Ukur'),
                ('609', 'Persiapan, Pelaksanaan Dan Evaluasi On Site Kalibrasi Wilayah Pulau Jawa'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('203', 'Pemeliharaan Sistem Informasi Manajemen Spektrum (SIMS)'),
                ('605', 'Pemeliharaan dan Kalibrasi Alat Pengujian Perangkat Telekomunikasi dan Digital'),
                ('608', 'Pengelolaan Teknologi Informasi BBPPT'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('201', 'LAYANAN PERIZINAN SPEKTRUM FREKUENSI RADIO,SOR,SERTIFIKASI PERANGKAT, DATA CENTER,CLOUD DAN TELEKOMUNIKASI KHUSUS'),
                ('204', 'LAYANAN PENGELOLAAN PNBP BHP SFR'),
                ('603', 'Layanan Pengujian Perangkat Digital'),
            ]),
            ('QDI', 'Fasilitasi dan Pembinaan Industri', [
                ('607', 'Fasilitasi Pengujian untuk Inovasi dan Pengembangan Perangkat Digital Dalam Negeri'),
            ]),
            ('RAN', 'Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('202', 'Sistem Informasi Manajemen Spektrum (SIMS)'),
                ('601', 'Pemenuhan Kapasitas Pengujian Perangkat TIK di BBPPT'),
            ]),
        ]),
        ('7437', 'Monitoring dan Pengendalian Spektrum Frekuensi Radio, Perangkat Digital dan Kualitas Layanan Telekomunikasi', [
            ('BAH', 'Pelayanan Publik Lainnya', [
                ('078', 'Layanan Dukungan Pengawasan Spektrum Frekuensi Radio UPT'),
                ('101', 'LAYANAN PENANGANAN PELANGGARAN STANDAR DAN/ATAU PERANGKAT TELEKOMUNIKASI'),
                ('102', 'PENGAWASAN KUALITAS LAYANAN TELEKOMUNIKASI'),
                ('U00', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO DALAM KOTA WILAYAH SUMATERA'),
                ('U01', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT WILAYAH SUMATERA'),
                ('U02', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI UDARA WILAYAH SUMATERA'),
                ('U03', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH SUMATERA'),
                ('U04', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA DALAM KOTA WILAYAH SUMATERA'),
                ('U05', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI DARAT WILAYAH SUMATERA'),
                ('U06', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH SUMATERA'),
                ('U07', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO DALAM KOTA WILAYAH JAWA'),
                ('U08', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT WILAYAH JAWA'),
                ('U09', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH JAWA'),
                ('U10', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA DALAM KOTA WILAYAH JAWA'),
                ('U11', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI DARAT WILAYAH JAWA'),
                ('U13', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO DALAM KOTA WILAYAH KALIMANTAN'),
                ('U14', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT WILAYAH KALIMANTAN'),
                ('U15', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI UDARA WILAYAH KALIMANTAN'),
                ('U16', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH KALIMANTAN'),
                ('U17', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA DALAM KOTA WILAYAH KALIMANTAN'),
                ('U18', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI DARAT WILAYAH KALIMANTAN'),
                ('U19', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI UDARA WILAYAH KALIMANTAN'),
                ('U20', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH KALIMANTAN'),
                ('U21', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO DALAM KOTA WILAYAH SULAWESI'),
                ('U22', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT WILAYAH SULAWESI'),
                ('U23', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI UDARA WILAYAH SULAWESI'),
                ('U24', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI SUNGAI/LAUT WILAYAH SULAWESI'),
                ('U25', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA DALAM KOTA WILAYAH SULAWESI'),
                ('U26', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI DARAT WILAYAH SULAWESI'),
                ('U27', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH SULAWESI'),
                ('U28', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO DALAM KOTA WILAYAH PAPUA'),
                ('U29', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT WILAYAH PAPUA'),
                ('U30', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI UDARA WILAYAH PAPUA'),
                ('U31', 'PEMANTAUAN PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH PAPUA'),
                ('U33', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA DALAM KOTA WILAYAH PAPUA'),
                ('U34', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI UDARA/DARAT WILAYAH PAPUA'),
                ('U35', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO DALAM KOTA WILAYAH KEPULAUAN'),
                ('U36', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT WILAYAH KEPULAUAN'),
                ('U37', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI UDARA WILAYAH KEPULAUAN'),
                ('U38', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH KEPULAUAN'),
                ('U39', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI UDARA/LAUT/SUNGAI WILAYAH KEPULAUAN'),
                ('U40', 'PEMANTAUAN, PENGUKURAN DAN PENANGANAN GANGGUAN FREKUENSI RADIO LUAR KOTA TRANSPORTASI DARAT/LAUT WILAYAH KEPULAUAN'),
                ('U41', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA DALAM KOTA WILAYAH KEPULAUAN'),
                ('U42', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI DARAT WILAYAH KEPULAUAN'),
                ('U43', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI UDARA WILAYAH KEPULAUAN'),
                ('U44', 'PENERTIBAN FREKUENSI RADIO DAN STANDAR PERANGKAT POS DAN INFORMATIKA LUAR KOTA TRANSPORTASI LAUT/SUNGAI WILAYAH KEPULAUAN'),
            ]),
            ('BIF', 'Pengawasan dan Pengendalian Layanan', [
                ('101', 'LAYANAN PENGAWASAN KEPATUHAN SANKSI ADMINISTRASI SPEKTRUM FREKUENSI RADIO DAN ALAT PERANGKAT TELEKOMUNIKASI'),
            ]),
            ('CAN', 'Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('101', 'Perangkat Monitoring UPT'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('101', 'Pemeliharaan Alat Monitoring UPT'),
                ('102', 'PEMELIHARAAN SISTEM MONITORING FREKUENSI RADIO (SMFR)'),
            ]),
            ('FAN', 'Pemenuhan Prioritas Direktif Presiden', [
                ('ZZ1', 'Pemenuhan Prioritas Direktif Presiden'),
            ]),
            ('QAH', 'Pelayanan Publik Lainnya', [
                ('101', 'LAYANAN PENGAWASAN DAN PENGENDALIAN SFR'),
                ('102', 'LAYANAN PERLINDUNGAN PENGGUNA PERANGKAT TELEKOMUNIKASI'),
            ]),
            ('RAN', 'Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('101', 'SISTEM MONITORING FREKUENSI RADIO (SMFR)'),
            ]),
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('101', 'O.M. PUSAT MONITORING TELEKOMUNIKASI'),
            ]),
        ]),
        ('7438', 'Penyediaan dan Pengelolaan Infrastruktur Digital di Wilayah Universal', [
            ('BDD', 'Fasilitasi dan Pembinaan Kelompok Masyarakat', [
                ('001', 'Fasilitasi Pemanfaatan Teknologi Digital bagi Masyarakat di Wilayah Pelayanan Universal Telekomunikasi dan Informasi (WPUTI)'),
            ]),
            ('QDH', 'Fasilitasi dan Pembinaan Badan Usaha', [
                ('001', 'Kerjasama Badan Usaha'),
            ]),
            ('RCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Operasional Monitoring Jaringan Infrastruktur'),
            ]),
            ('RDS', 'OP Prasarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'OM Palapa Ring'),
                ('002', 'OM BTS 4G /Lastmile'),
                ('003', 'OM BTS 4G /Lastmile Wilayah Papua'),
                ('004', 'OM Akses Internet'),
                ('005', 'OM Akses Internet Wilayah Papua'),
                ('006', 'OM SATRIA 1'),
            ]),
        ]),
    ]),
    ('059.WA', 'Program Dukungan Manajemen', [
        ('4485', 'Pengelolaan Keuangan, BMN dan Umum Badan Pengembangan Sumber Daya Manusia Komunikasi dan Digital', [
            ('AEC', 'Kerja sama', [
                ('001', 'Kerjasama Badan Pengembangan SDM dengan Mitra'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('956', 'Layanan BMN'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
                ('962', 'Layanan Umum'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
                ('971', 'Layanan Prasarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
                ('974', 'Layanan Penyelenggaraan Kearsipan'),
            ]),
        ]),
        ('4486', 'Pengelolaan Keuangan, BMN dan Umum Direktorat Jenderal Komunikasi Publik dan Media', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('956', 'Layanan BMN'),
                ('957', 'Layanan Hukum.'),
                ('962', 'Layanan Umum'),
                ('963', 'Layanan Data dan Informasi'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
            ]),
        ]),
        ('4490', 'Pengelolaan Keuangan, BMN dan Umum BAKTI', [
            ('AEC', 'Kerja sama', [
                ('001', 'Layanan Kerjasama Kegiatan BAKTI'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('956', 'Layanan BMN'),
                ('957', 'Layanan Hukum.'),
                ('958', 'Layanan Hubungan Masyarakat dan Informasi'),
                ('962', 'Layanan Umum'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
                ('965', 'Layanan Audit Internal'),
            ]),
        ]),
        ('4491', 'Pengelolaan Keuangan, BMN dan Umum Inspektorat Jenderal', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('001', 'Layanan Pemantauan Tindak Lanjut Hasil Pengawasan'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
                ('962', 'Layanan Umum'),
                ('963', 'Layanan Data dan Informasi'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
            ]),
        ]),
        ('4492', 'Pengelolaan Keuangan, BMN dan Umum Sekretariat Jenderal', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('001', 'Layanan Umum Komisi Informasi Pusat'),
                ('003', 'Layanan Umum Dewan Pers'),
                ('006', 'Layanan BMN Sekretariat Dewan Pers'),
                ('902', 'Layanan BMN KPI Pusat'),
                ('956', 'Layanan BMN'),
                ('958', 'Layanan Hubungan Masyarakat dan Informasi'),
                ('962', 'Layanan Umum'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('001', 'Layanan Sarana Internal KI Pusat'),
                ('002', 'Layanan Sarana Internal KPI'),
                ('003', 'Layanan Sarana Internal Dewan Pers'),
                ('004', 'Layanan Prasarana Internal Dewan Pers'),
                ('951', 'Layanan Sarana Internal'),
                ('971', 'Layanan Prasarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('906', 'Layanan Manajemen SDM KPI Pusat'),
                ('907', 'Layanan Pendidikan dan Pelatihan KPI Pusat'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('001', 'Layanan Perencanaan dan Penganggaran KI Pusat'),
                ('002', 'Layanan Pemantauan dan Evaluasi KI Pusat'),
                ('007', 'Layanan Perencanaan dan Penganggaran Dewan Pers'),
                ('008', 'Layanan Pemantauan dan Evaluasi Dewan Pers'),
                ('009', 'Layanan Manajemen Keuangan Dewan Pers'),
                ('904', 'Layanan Manajemen Keuangan KPI Pusat'),
                ('905', 'Layanan Penyelenggaraan Kearsipan KPI Pusat'),
                ('955', 'Layanan Manajemen Keuangan'),
            ]),
        ]),
        ('4493', 'Pengelolaan Organisasi dan SDM', [
            ('AAG', 'Peraturan Menteri dan Kepala Lembaga', [
                ('001', 'Rancangan Peraturan Tentang Kelembagaan Kementerian Kominfo dalam Kerangka Transformasi Digital'),
            ]),
            ('AAH', 'Peraturan lainnya', [
                ('001', 'Rancangan Peraturan tentang JF Binaan Komdigi'),
                ('002', 'Rancangan Regulasi Tentang Manajemen Jabatan'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('001', 'Dokumen Usulan Evaluasi RB dan Pelayanan Publik'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('001', 'Pengembangan Kompetensi ASN Komdigi Bidang Digital'),
                ('954', 'Layanan Manajemen SDM'),
            ]),
        ]),
        ('4497', 'Pengelolaan Resiko, Pengandalian dan Pengawasan Internal', [
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('001', 'Layanan Audit Internal Bidang Pengelolaan Infrastruktur Digital dan Bidang Pembangunan Aksesibilitas Telekomunikasi dan Informasi'),
                ('002', 'Layanan Audit Internal Bidang Penyelenggaraan Ekosistem Digital, Bidang Pengawasan Ruang Digital, dan Bidang Pengawasan Intern'),
                ('003', 'Layanan Audit Internal Bidang Pengelolaan Komunikasi Publik dan Media serta Bidang Pengembangan SDM Komunikasi dan Digital'),
                ('004', 'Layanan Audit Internal Bidang Penatakelolaan Teknologi Pemerintah Digital serta Bidang Pembinaan dan Pemberian Dukungan Administrasi'),
            ]),
        ]),
        ('4513', 'Legislasi dan Litigasi', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('957', 'Layanan Hukum.'),
                ('969', 'Layanan Bantuan Hukum'),
            ]),
        ]),
        ('4518', 'Pengelolaan administrasi dan kerjasama internasional', [
            ('AEC', 'Kerja sama', [
                ('001', 'Pertemuan Kelembagaan Internasional'),
                ('002', 'Layanan Dukungan Penyelenggaraan Sidang Internasional'),
            ]),
        ]),
        ('4519', 'Pengelolaan Akuntabilitas Kinerja', [
            ('AEA', 'Koordinasi', [
                ('001', 'Fasilitasi pendampingan Clearance Belanja TIK Kemenkominfo'),
            ]),
            ('AEC', 'Kerja sama', [
                ('001', 'Layanan Kerja Sama dan Sinergi Program Transformasi Digital K/L/D/I dan Non-Pemerintah'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('001', 'Layanan Manajemen Risiko dan Kepatuhan Internal'),
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
            ]),
            ('FAC', 'Peningkatan Kapasitas Aparatur Negara', [
                ('001', 'Fasilitasi Pengembangan Kompetensi Eksklusif bidang Perencanaan dan Penganggaran'),
            ]),
            ('PBO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Pengukuran Indeks Transformasi Digital Nasional (TDN)'),
            ]),
        ]),
        ('4520', 'Pengelolaan Komunikasi dan Informasi Publik Kementerian Komunikasi dan Digital', [
            ('BMB', 'Komunikasi Publik', [
                ('001', 'Diseminasi Rebranding Kementerian Kominfo untuk Akselerasi Transformasi Digital'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('958', 'Layanan Hubungan Masyarakat dan Informasi'),
            ]),
        ]),
        ('4521', 'Pengelolaan Sistem Informasi dan Teknologi', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Kebijakan Tata Kelola TI Komdigi'),
            ]),
            ('BMA', 'Data dan Informasi Publik', [
                ('001', 'Layanan Komdigi Smart Services'),
            ]),
            ('CCL', 'OM Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('001', 'Layanan Pengelolaan dan Pemeliharaan Sarana TIK'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('963', 'Layanan Data dan Informasi'),
            ]),
        ]),
        ('6995', 'Pengelolaan Keuangan, BMN dan Umum Pendidikan Tinggi', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
            ]),
        ]),
        ('7426', 'Pengembangan Analisis Kebijakan Strategis bidang Komunikasi dan Digital', [
            ('ABO', 'Kebijakan Bidang Teknologi Informasi', [
                ('001', 'Rekomendasi Analisis dan Pemantauan Kebijakan Transformasi Bidang Komunikasi dan Digital'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('001', 'Rekomendasi Harmonisasi dan Penguatan Strategi Kebijakan Transformasi Bidang Komunikasi dan Digital'),
            ]),
        ]),
        ('7427', 'Pengelolaan Keuangan, BMN dan Umum Direktorat Jenderal Infrastruktur Digital', [
            ('CAN', 'Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('101', 'Pengembangan Infrastruktur TIK Perkantoran'),
            ]),
            ('CCL', 'OP Sarana Bidang Teknologi Informasi dan Komunikasi', [
                ('101', 'Infrastruktur dan Internet Perkantoran'),
            ]),
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('956', 'Layanan BMN'),
                ('957', 'Layanan Hukum.'),
                ('958', 'Layanan Hubungan Masyarakat dan Informasi'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
                ('962', 'Layanan Umum'),
                ('963', 'Layanan Data dan Informasi'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
                ('956', 'Layanan Kepatuhan Internal dan Manajemen Risiko'),
            ]),
        ]),
        ('7428', 'Pengelolaan Keuangan, BMN dan Umum Direktorat Jenderal Teknologi Pemerintah Digital', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('956', 'Layanan BMN'),
                ('957', 'Layanan Hukum.'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
                ('962', 'Layanan Umum'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
            ]),
        ]),
        ('7429', 'Pengelolaan Keuangan, BMN dan Umum Direktorat Jenderal Ekosistem Digital', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('957', 'Layanan Hukum.'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
                ('962', 'Layanan Umum'),
                ('963', 'Layanan Data dan Informasi'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
                ('956', 'Layanan Manajemen Risiko dan Kepatuhan Internal'),
            ]),
        ]),
        ('7430', 'Pengelolaan Keuangan, BMN dan Umum Direktorat Jenderal Pengawasan Ruang Digital', [
            ('EBA', 'Layanan Dukungan Manajemen Internal', [
                ('956', 'Layanan BMN'),
                ('957', 'Layanan Hukum.'),
                ('960', 'Layanan Organisasi dan Tata Kelola Internal.'),
                ('962', 'Layanan Umum'),
                ('963', 'Layanan Data dan Informasi'),
                ('994', 'Layanan Perkantoran'),
            ]),
            ('EBB', 'Layanan Sarana dan Prasarana Internal', [
                ('951', 'Layanan Sarana Internal'),
                ('971', 'Layanan Prasarana Internal'),
            ]),
            ('EBC', 'Layanan Manajemen SDM Internal', [
                ('954', 'Layanan Manajemen SDM'),
            ]),
            ('EBD', 'Layanan Manajemen Kinerja Internal', [
                ('952', 'Layanan Perencanaan dan Penganggaran.'),
                ('953', 'Layanan Pemantauan dan Evaluasi'),
                ('955', 'Layanan Manajemen Keuangan'),
                ('975', 'Layanan Manajemen Kinerja'),
            ]),
        ]),
    ]),
]


def cari_ro(program: str, kegiatan: str, kro: str, ro: str) -> dict | None:
    """Kembalikan salinan {program, kegiatan, kro, ro} berisi {kode, nama} bila keempat kode membentuk jalur yang ada, selain
    itu None. Kode RO disimpan lengkap (`kegiatan.KRO.RO`)."""
    for kp, np, keg in PROGRAM:
        for kk, nk, kros in keg if kp == program else []:
            for kr, nr, ros in kros if kk == kegiatan else []:
                for ko, no in ros if kr == kro else []:
                    if ko == ro:
                        return {"program": {"kode": kp, "nama": np}, "kegiatan": {"kode": kk, "nama": nk},
                                "kro": {"kode": f"{kk}.{kr}", "nama": nr}, "ro": {"kode": f"{kk}.{kr}.{ko}", "nama": no}}
    return None


def pohon() -> list[dict]:
    """PROGRAM sebagai JSON bertingkat untuk dropdown (kode tiap tingkat seperti diisi di form)."""
    return [{"kode": kp, "nama": np, "kegiatan": [{"kode": kk, "nama": nk, "kro": [{"kode": kr, "nama": nr, "ro": [
        {"kode": ko, "nama": no} for ko, no in ros]} for kr, nr, ros in kros]} for kk, nk, kros in keg]} for kp, np, keg in PROGRAM]
