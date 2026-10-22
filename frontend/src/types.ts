export type Role = "PENGUSUL" | "REVIEWER" | "ADMIN";
export type Satker = { id: string; kode: string; nama: string; aktif?: boolean };
export type Pengguna = { id: string; username: string; nama: string; roles: Role[]; satker: Satker | null; csrf?: string };

export type StatusRevisi = "DRAF" | "ANTRE" | "DIPROSES_AI" | "GAGAL" | "MENUNGGU_VERIFIKASI" | "LOLOS" | "TIDAK_LOLOS";
export type KategoriRingkas = { id?: string; kode: string; nama: string; diteruskan: boolean };
export type Dok = { file_id: string; nama: string; diganti?: boolean };

export type Proses = {
  review_id: string; status: string; progres: { tahap: string; persen: number } | null; trace_id: string;
  error_pesan: string | null; posisi_antrean?: number | null; menunggu_kapasitas?: boolean;
};

export type RingkasChecklist = {
  terpenuhi: number; total: number; label: string; final: boolean;
  item: { kode: string; judul: string; terpenuhi: boolean }[];
};

export type BarisUsulan = {
  id: string; satker: Satker; tahun_anggaran: number; kode_ro: string; nama_ro: string; revisi_id: string;
  revisi_nomor: number; status: StatusRevisi; tor: Dok; rab: Dok; kategori_final: KategoriRingkas | null;
  updated_at: string; diarsipkan: boolean; pernah_direview: boolean; review_id: string | null;
  checklist: RingkasChecklist | null; proses: Proses | null; boleh_kelola: boolean;
};

export type Rujukan = {
  id: string; peran: "bukti_dokumen" | "dasar_panduan"; dokumen: "TOR" | "RAB" | "PANDUAN"; judul_dokumen: string;
  file_id: string; halaman: number; label_lokasi: string; kutipan: string; bbox: number[] | null; sumber: string; jenis: string;
};

export type Override = {
  id: string; target: string; checklist_item_id: string | null; nilai_sebelum: string; nilai_sesudah: string;
  alasan: string; oleh: string; at: string; dibatalkan_at: string | null; dibatalkan_oleh: string | null;
};

export type ItemReview = {
  id: string; kode: string; judul: string; kriteria: string; berlaku_untuk: string; ai_terpenuhi: boolean;
  terpenuhi: boolean; diubah: boolean; override: Override | null; ditemukan: boolean; alasan: string;
  yang_kurang: string | null; rujukan: Rujukan[];
};

export type Rekomendasi = { id: string; teks: string; tidak_diperlukan: boolean; item_kode: string | null; rujukan: Rujukan[] };

export type DetailReview = {
  id: string; status: string; trace_id: string; tampilan: "reviewer" | "pengusul"; final: boolean;
  difinalkan_oleh: string | null; difinalkan_at: string | null; selesai_at: string | null;
  model_info: Record<string, string> | null; proses: Proses | null; disalin_dari_revisi?: number | null;
  usulan: { id: string; satker: string; tahun_anggaran: number; kode_ro: string; nama_ro: string; diarsipkan: boolean };
  revisi: { id: string; nomor: number; status: StatusRevisi; tor: Dok; rab: Dok };
  boleh_override: boolean;
  acuan?: { checklist: { jumlah_item: number }; kategori_versi: { id: string; nomor: number };
    panduan: { judul: string; nomor: number; file_id: string; nama_file: string }[] };
  item?: ItemReview[];
  label?: { ai: string; hitung: string; final: string; diubah: boolean; tidak_konsisten: boolean; terpenuhi: number; total: number; override: Override | null };
  kategori?: { ai: KategoriRingkas | null; final: KategoriRingkas | null; diubah: boolean; alasan: string | null;
    rujukan: Rujukan[]; override: Override | null; pilihan: KategoriRingkas[] };
  rekomendasi?: { TOR: Rekomendasi[]; RAB: Rekomendasi[] };
  catatan?: { dokumen: string; teks: string; oleh: string; diubah_at: string }[];
  riwayat_override?: Override[];
};

export type ItemChecklist = {
  id?: string; kode: string; judul: string; kriteria: string; berlaku_untuk: "TOR" | "RAB" | "TOR & RAB"; aktif: boolean;
  diubah_oleh?: string | null; diubah_at?: string;
};
export type ItemKategori = { id?: string; kode: string; nama: string; definisi: string; diteruskan: boolean };
export type Versi<T> = { id: string; nomor: number; aktif: boolean; catatan: string | null; dibuat_at: string; dibuat_oleh: string | null; item: T[] };
export type RingkasVersi = { id: string; nomor: number; aktif: boolean; catatan: string | null; jumlah_item: number; dibuat_at: string; dibuat_oleh: string | null };

export type VersiPanduan = { id: string; nomor: number; judul: string; deskripsi: string | null; file_id: string; nama_file: string; aktif: boolean;
  status_proses: "BELUM" | "DIPROSES" | "SIAP" | "GAGAL"; pesan_gagal: string | null; jumlah_halaman: number; dibuat_at: string; dibuat_oleh: string | null };
export type Panduan = { id: string; judul: string; aktif: boolean; diubah_oleh: string | null; diubah_at: string; terkini: VersiPanduan; versi: VersiPanduan[] };
