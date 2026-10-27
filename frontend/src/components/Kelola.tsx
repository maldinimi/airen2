/** Potongan tampilan bersama halaman kelola (Pengguna, Satker) — bergaya Kelola Checklist:
 *  tabel rata tengah dengan 3 ikon aksi, halaman detail label–nilai, form sebagai halaman dengan tombol Kembali. */
import * as Pop from "@radix-ui/react-popover";
import { ArrowLeft, ChevronDown, Eye, Pencil, Trash2 } from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { waktuAngka } from "../format";
import type { Satker as SatkerDasar } from "../types";

/** Jejak data (kolom created_by/create_date/update_by/update_date); oleh = null berarti dibuat sistem. */
export type Jejak = { dibuat_oleh?: string | null; dibuat_at?: string; diubah_oleh?: string | null; diubah_at?: string };
/** Satuan Kerja di menu Satuan Kerja/Pengguna: nama = UKE II (Eselon II), unit_kerja = UKE I (Eselon I). */
export type Satker = Omit<SatkerDasar, "kode"> & { kode?: string; unit_kerja?: string; kode_uke1?: string; kode_uke2?: string } & Jejak;
import { Judul, Kartu, Lencana, Peringatan, Tombol, cx } from "../ui";

export type Opsi = { nilai: string; label: string };

/** Dropdown yang selalu terbuka ke bawah (tinggi terbatas, bisa di-scroll). Bukan <select> bawaan: untuk daftar
 *  panjang browser membuka <select> ke atas bila ruang di bawah sempit. */
export function PilihBawah({ opsi, nilai, ubah, kosong = "— tidak ada —", disabled }: {
  opsi: Opsi[]; nilai: string; ubah: (nilai: string) => void; kosong?: string | null; disabled?: boolean;
}) {
  const [buka, setBuka] = useState(false);
  const daftarRef = useRef<HTMLDivElement>(null);
  const terpilih = opsi.find((o) => o.nilai === nilai);
  const tombolOpsi = (o: Opsi) => (
    <button key={o.nilai || "kosong"} type="button" role="option" aria-selected={o.nilai === nilai} onClick={() => { ubah(o.nilai); setBuka(false); }}
      className={cx("block w-full rounded-md px-3 py-1.5 text-left text-sm hover:bg-slate-100",
        o.nilai === nilai && "bg-utama-50 font-medium text-utama-700")}>{o.label}</button>
  );
  return (
    <Pop.Root open={buka} onOpenChange={setBuka}>
      <Pop.Trigger type="button" disabled={disabled} className="flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-slate-300 bg-white px-3 text-left text-sm shadow-sm focus:border-utama-500 focus:outline-none focus:ring-2 focus:ring-utama-100 disabled:bg-slate-100 disabled:text-slate-500">
        <span className={cx("truncate", !terpilih && "text-slate-500")}>{terpilih?.label ?? kosong ?? "— pilih —"}</span>
        <ChevronDown className="size-4 shrink-0 text-slate-500" aria-hidden />
      </Pop.Trigger>
      <Pop.Portal>
        <Pop.Content side="bottom" align="start" sideOffset={4} avoidCollisions={false}
          onOpenAutoFocus={(e) => { e.preventDefault(); daftarRef.current?.querySelector("[aria-selected=true]")?.scrollIntoView({ block: "center" }); }}
          className="z-50 w-[var(--radix-popover-trigger-width)] rounded-lg border border-slate-200 bg-white shadow-xl">
          <div ref={daftarRef} role="listbox" className="max-h-80 overflow-y-auto p-1">
            {kosong !== null && tombolOpsi({ nilai: "", label: kosong })}
            {opsi.map(tombolOpsi)}
          </div>
        </Pop.Content>
      </Pop.Portal>
    </Pop.Root>
  );
}

/** UKE I (Unit Kerja, Eselon I) unik dari daftar Satker, urut kemunculan pertama. `kunci` = kode|nama. */
type Uke1 = { kunci: string; kode_uke1: string; unit_kerja: string };
export const kunciUke1 = (s: Pick<Satker, "kode_uke1" | "unit_kerja">) => [s.kode_uke1 ?? "", s.unit_kerja ?? ""].join("|");
export function daftarUke1(daftar: Pick<Satker, "kode_uke1" | "unit_kerja">[]): Uke1[] {
  const hasil = new Map<string, Uke1>();
  for (const s of daftar) {
    const kunci = kunciUke1(s);
    if (s.unit_kerja && !hasil.has(kunci))
      hasil.set(kunci, { kunci, kode_uke1: s.kode_uke1 ?? "", unit_kerja: s.unit_kerja });
  }
  return [...hasil.values()];
}

export const LencanaAktif = ({ aktif }: { aktif: boolean }) => aktif
  ? <Lencana className="bg-emerald-50 text-emerald-700 ring-emerald-300">Aktif</Lencana>
  : <Lencana className="bg-slate-100 text-slate-600 ring-slate-300">Nonaktif</Lencana>;

export const th = (h: string) => <th key={h} scope="col" className={cx("whitespace-nowrap px-3 py-2.5 text-center", h === "No" && "w-12")}>{h}</th>;
export const TD = "px-3 py-2.5 text-center";
const tombol = "rounded-lg p-1.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";

/** Baris detail untuk kolom jejak database (created_by, create_date, update_by, update_date). */
export const barisJejak = (x: Jejak): [string, ReactNode][] => [
  ["Dibuat Oleh", x.dibuat_oleh ?? "Sistem"], ["Tanggal Dibuat", waktuAngka(x.dibuat_at)],
  ["Diubah Oleh", x.diubah_oleh ?? "Sistem"], ["Terakhir Diubah", waktuAngka(x.diubah_at)],
];

/** Pesan sukses yang hilang sendiri setelah 4 detik. */
export function usePesanSukses() {
  const [sukses, setSukses] = useState<string | null>(null);
  useEffect(() => { if (!sukses) return; const t = setTimeout(() => setSukses(null), 4000); return () => clearTimeout(t); }, [sukses]);
  return [sukses, setSukses] as const;
}

/** Tiga ikon aksi: Detail, Edit, Hapus. */
export function Aksi({ nama, lihat, ubah, hapus }: { nama: string; lihat: () => void; ubah: () => void; hapus: () => void }) {
  return (
    <td className="whitespace-nowrap px-3 py-2 text-center">
      <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700")} title="Detail" aria-label={`Detail ${nama}`} onClick={lihat}><Eye className="size-4" /></button>
      <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50 hover:text-utama-700")} title="Edit" aria-label={`Edit ${nama}`} onClick={ubah}><Pencil className="size-4" /></button>
      <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50 hover:text-red-700")} title="Hapus" aria-label={`Hapus ${nama}`} onClick={hapus}><Trash2 className="size-4" /></button>
    </td>
  );
}

function Kembali({ label, tutup }: { label: string; tutup: () => void }) {
  return (
    <button type="button" onClick={tutup} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
      <ArrowLeft className="size-4" />{label}
    </button>
  );
}

/** Halaman detail: tabel label–nilai. */
export function HalamanDetail({ kembali, judul, sub, info, tutup }: { kembali: string; judul: string; sub: string; info: [string, ReactNode][]; tutup: () => void }) {
  useEffect(() => { document.querySelector("main")?.scrollTo(0, 0); }, []);
  return (
    <div className="w-full">
      <Kembali label={kembali} tutup={tutup} />
      <Judul judul={judul} sub={sub} />
      <Kartu className="p-5">
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-100">{info.map(([l, v]) => (
              <tr key={l} className="align-top">
                <th scope="row" className="w-40 px-3 py-2.5 text-left font-normal text-slate-500 sm:w-60">{l}</th>
                <td className="px-3 py-2.5 text-slate-800">{v}</td>
              </tr>))}</tbody>
          </table>
        </div>
      </Kartu>
    </div>
  );
}

/** Halaman form. `reset` diisi saat Tambah: tombol Reset (kosongkan form); keluar lewat "Kembali". */
export function HalamanForm({ judul, sub, tutup, kirim, reset, galat, sibuk, children }: {
  judul: string; sub: string; tutup: () => void; kirim: () => void; reset?: () => void; galat: Error | null; sibuk: boolean; children: ReactNode;
}) {
  useEffect(() => { document.querySelector("main")?.scrollTo(0, 0); }, []);
  return (
    <div className="w-full">
      <Kembali label="Kembali" tutup={tutup} />
      <Judul judul={judul} sub={sub} />
      <Kartu className="p-5">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); kirim(); }}>
          {galat && <Peringatan>{galat.message}</Peringatan>}
          {children}
          <div className="flex justify-end gap-2">
            {reset && <Tombol type="button" varian="sekunder" onClick={reset}>Reset</Tombol>}
            <Tombol type="submit" memuat={sibuk}>Simpan</Tombol>
          </div>
        </form>
      </Kartu>
    </div>
  );
}
