const fmt = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short", hourCycle: "h23", timeZone: "Asia/Jakarta" });
const fmtTanggal = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeZone: "Asia/Jakarta" });

export const waktu = (iso?: string | null) => (iso ? fmt.format(new Date(iso)) : "—");
export const tanggal = (iso?: string | null) => (iso ? fmtTanggal.format(new Date(iso)) : "—");

const fmtAngka = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  hourCycle: "h23", timeZone: "Asia/Jakarta" });
/** DD/MM/YYYY HH:mm (WIB). */
export const waktuAngka = (iso?: string | null) => (iso ? fmtAngka.format(new Date(iso)).replace(",", "") : "—");

/** Nama tahap revisi untuk tampilan (desain.md §7 no. 73–74): revisi 1 = "Dokumen", revisi n ≥ 2 = "Perbaikan n−1".
 *  Nomor revisi di data/API tetap. */
export const namaRevisi = (nomor: number) => (nomor === 1 ? "Dokumen" : `Perbaikan ${nomor - 1}`);
