const fmt = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Jakarta" });
const fmtTanggal = new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeZone: "Asia/Jakarta" });

export const waktu = (iso?: string | null) => (iso ? fmt.format(new Date(iso)) : "—");
export const tanggal = (iso?: string | null) => (iso ? fmtTanggal.format(new Date(iso)) : "—");
