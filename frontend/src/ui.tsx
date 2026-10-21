/** Komponen UI bersama (gaya shadcn/ui di atas Radix + Tailwind). */
import * as D from "@radix-ui/react-dialog";
import { AlertTriangle, Loader2, X } from "lucide-react";
import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes,
  type TextareaHTMLAttributes, forwardRef } from "react";
import type { KategoriRingkas, StatusRevisi } from "./types";

export const cx = (...k: (string | false | null | undefined)[]) => k.filter(Boolean).join(" ");

type Varian = "utama" | "lembut" | "sekunder" | "bahaya" | "hantu" | "ubah";
const gayaTombol: Record<Varian, string> = {
  utama: "bg-utama-600 text-white hover:bg-utama-700 shadow-sm",
  lembut: "bg-utama-100 text-utama-700 hover:brightness-95 shadow-sm",
  sekunder: "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 shadow-sm",
  bahaya: "bg-red-600 text-white hover:bg-red-700 shadow-sm",
  hantu: "text-slate-600 hover:bg-slate-100",
  ubah: "bg-ubah-600 text-white hover:bg-ubah-700 shadow-sm",
};

export const Tombol = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { varian?: Varian; kecil?: boolean; memuat?: boolean }>(
  ({ varian = "utama", kecil, memuat, className, children, disabled, ...p }, ref) => (
    <button ref={ref} disabled={disabled || memuat} {...p}
      className={cx("inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-utama-500 disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap",
        kecil ? "h-8 px-2.5 text-xs" : "h-10 px-4 text-sm", gayaTombol[varian], className)}>
      {memuat && <Loader2 className="size-4 animate-spin" aria-hidden />}{children}
    </button>
  ));

const gayaInput = "w-full rounded-lg border border-slate-300 bg-white px-3 text-sm shadow-sm placeholder:text-slate-400 focus:border-utama-500 focus:outline-none focus:ring-2 focus:ring-utama-100 disabled:bg-slate-100";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) =>
  <input ref={ref} {...p} className={cx(gayaInput, "h-10", className)} />);
export const Pilih = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...p }, ref) =>
  <select ref={ref} {...p} className={cx(gayaInput, "h-10 pr-8", className)} />);
export const AreaTeks = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) =>
  <textarea ref={ref} {...p} className={cx(gayaInput, "py-2 min-h-24", className)} />);

export function Kolom({ label, wajib, petunjuk, children }: { label: string; wajib?: boolean; petunjuk?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}{wajib && <span className="text-red-600"> *</span>}</span>
      {children}
      {petunjuk && <span className="block text-xs text-slate-500">{petunjuk}</span>}
    </label>
  );
}

/** Saklar Aktif/Nonaktif (role="switch" agar terbaca pembaca layar). */
export function Saklar({ nyala, ubah, label, disabled }: { nyala: boolean; ubah: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button type="button" role="switch" aria-checked={nyala} aria-label={label} disabled={disabled} onClick={() => ubah(!nyala)}
      className={cx("relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-utama-500 disabled:opacity-50",
        nyala ? "bg-emerald-500" : "bg-slate-300")}>
      <span className={cx("inline-block size-4 rounded-full bg-white shadow transition-transform", nyala ? "translate-x-4" : "translate-x-0.5")} />
    </button>
  );
}

export const Kartu = ({ className, children }: { className?: string; children: ReactNode }) =>
  <div className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>{children}</div>;

export function Judul({ judul, sub, aksi }: { judul: ReactNode; sub?: ReactNode; aksi?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{judul}</h1>
        {sub && <p className="mt-1 text-sm text-slate-500">{sub}</p>}
      </div>
      {aksi && <div className="flex flex-wrap gap-2">{aksi}</div>}
    </div>
  );
}

export const Lencana = ({ className, children, title }: { className?: string; children: ReactNode; title?: string }) =>
  <span title={title} className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap", className)}>{children}</span>;

export const NAMA_STATUS: Record<StatusRevisi, string> = {
  DRAF: "Belum direview", ANTRE: "Antre", DIPROSES_AI: "Diproses AI", GAGAL: "Gagal",
  MENUNGGU_VERIFIKASI: "Menunggu verifikasi", LOLOS: "Lolos", TIDAK_LOLOS: "Tidak lolos",
};
const WARNA_STATUS: Record<StatusRevisi, string> = {
  DRAF: "bg-slate-100 text-slate-700 ring-slate-300",
  ANTRE: "bg-blue-50 text-blue-700 ring-blue-200",
  DIPROSES_AI: "bg-blue-50 text-blue-700 ring-blue-200",
  GAGAL: "bg-red-100 text-red-900 ring-red-300",
  MENUNGGU_VERIFIKASI: "bg-amber-50 text-amber-800 ring-amber-300",
  LOLOS: "bg-emerald-50 text-emerald-700 ring-emerald-300",
  TIDAK_LOLOS: "bg-red-50 text-red-700 ring-red-300",
};

export function LencanaStatus({ status }: { status: StatusRevisi }) {
  return (
    <Lencana className={WARNA_STATUS[status]}>
      {(status === "ANTRE" || status === "DIPROSES_AI") && <Loader2 className="size-3 animate-spin" aria-hidden />}
      {NAMA_STATUS[status]}
    </Lencana>
  );
}

export function LencanaLabel({ label }: { label: string }) {
  const lolos = label === "LOLOS";
  return <Lencana className={lolos ? WARNA_STATUS.LOLOS : WARNA_STATUS.TIDAK_LOLOS}>{lolos ? "LOLOS" : "TIDAK LOLOS"}</Lencana>;
}

export function LencanaKategori({ k }: { k: KategoriRingkas | null | undefined }) {
  if (!k) return <span className="text-slate-400">—</span>;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <Lencana className="bg-utama-50 text-utama-700 ring-utama-100" title={k.nama}>{k.kode}</Lencana>
      {!k.diteruskan && <Lencana className="bg-red-600 text-white ring-red-600">Tidak diteruskan</Lencana>}
    </span>
  );
}

export const TandaAI = () => <Lencana className="bg-slate-100 text-slate-600 ring-slate-200">AI</Lencana>;
export const TandaUbah = ({ title }: { title?: string }) =>
  <Lencana className="bg-ubah-100 text-ubah-700 ring-ubah-600/30" title={title}>Diubah reviewer</Lencana>;

export const Memuat = ({ teks = "Memuat…" }: { teks?: string }) =>
  <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500"><Loader2 className="size-5 animate-spin" />{teks}</div>;

export function Peringatan({ jenis = "error", children }: { jenis?: "error" | "info" | "warn"; children: ReactNode }) {
  const g = { error: "bg-red-50 text-red-800 border-red-200", info: "bg-utama-50 text-utama-900 border-utama-100", warn: "bg-amber-50 text-amber-900 border-amber-200" }[jenis];
  return <div role={jenis === "error" ? "alert" : "status"} className={cx("flex gap-2 rounded-lg border px-3 py-2.5 text-sm", g)}>
    <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden /><div>{children}</div></div>;
}

export function Kosong({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-white py-12 text-center text-sm text-slate-500">{children}</div>;
}

/** `ikon` diisi → ikon di atas tengah, judul di tengah, tombol tutup di pojok kanan atas. */
export function Dialog({ buka, ubahBuka, judul, children, lebar = "max-w-lg", ikon }:
  { buka: boolean; ubahBuka: (b: boolean) => void; judul: string; children: ReactNode; lebar?: string; ikon?: ReactNode }) {
  return (
    <D.Root open={buka} onOpenChange={ubahBuka}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-40 bg-slate-900/40" />
        <D.Content className={cx("fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-white p-5 shadow-xl", lebar)}>
          {ikon && <div className="mb-3 flex justify-center">{ikon}</div>}
          <div className={cx("mb-4 flex items-start gap-4", ikon ? "justify-center text-center" : "justify-between")}>
            <D.Title className="text-lg font-semibold text-slate-900">{judul}</D.Title>
            <D.Close className={cx("rounded p-1 text-slate-500 hover:bg-slate-100", !!ikon && "absolute right-4 top-4")} aria-label="Tutup"><X className="size-5" /></D.Close>
          </div>
          <D.Description className="sr-only">{judul}</D.Description>
          {children}
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

/** Daftar label–nilai berbingkai (ringkasan isian, detail data). */
export function Ringkasan({ baris }: { baris: [string, ReactNode][] }) {
  return (
    <dl className="divide-y divide-slate-100 rounded-lg border border-slate-200 text-sm">
      {baris.map(([k, v]) => (
        <div key={k} className="grid grid-cols-3 gap-2 px-3 py-2"><dt className="text-slate-500">{k}</dt><dd className="col-span-2 break-words">{v}</dd></div>
      ))}
    </dl>
  );
}

/** Pop-up konfirmasi: ringkasan + pertanyaan. Bawaan = "Periksa kembali" sebelum menyimpan; `bahaya` = tindakan yang
 *  tidak dapat dibatalkan (ikon peringatan, tombol merah). Tombol batal menutup tanpa melakukan apa pun. */
export function Konfirmasi({ buka, baris, batal, ya, memuat, galat, bahaya, judul = "Periksa kembali",
  pesan = "Apakah Anda yakin data di atas sudah benar dan ingin menyimpannya?", teksYa = "Ya, simpan", teksBatal = "Periksa kembali" }:
  { buka: boolean; baris: [string, ReactNode][]; batal: () => void; ya: () => void; memuat?: boolean; galat?: string | null;
    bahaya?: boolean; judul?: string; pesan?: ReactNode; teksYa?: string; teksBatal?: string }) {
  return (
    <Dialog buka={buka} ubahBuka={(b) => !b && !memuat && batal()} judul={judul}
      ikon={bahaya && <span className="flex size-12 items-center justify-center rounded-full bg-red-100"><AlertTriangle className="size-6 text-red-600" aria-hidden /></span>}>
      <div className="space-y-4">
        <Ringkasan baris={baris} />
        <p className="text-sm text-slate-700">{pesan}</p>
        {galat && <Peringatan>{galat}</Peringatan>}
        <div className="flex justify-end gap-2">
          <Tombol varian="hantu" disabled={memuat} onClick={batal}>{teksBatal}</Tombol>
          <Tombol varian={bahaya ? "bahaya" : "utama"} memuat={memuat} onClick={ya}>{teksYa}</Tombol>
        </div>
      </div>
    </Dialog>
  );
}

export function Tab<T extends string>({ pilihan, aktif, ubah }: { pilihan: { nilai: T; label: ReactNode }[]; aktif: T; ubah: (t: T) => void }) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto overflow-y-hidden border-b border-slate-200 [scrollbar-width:thin]">
      {pilihan.map((p) => (
        <button key={p.nilai} role="tab" aria-selected={aktif === p.nilai} onClick={() => ubah(p.nilai)}
          className={cx("-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium",
            aktif === p.nilai ? "border-utama-600 text-utama-700" : "border-transparent text-slate-500 hover:text-slate-800")}>
          {p.label}
        </button>
      ))}
    </div>
  );
}

export function Halaman({ total, halaman, per, ubah }: { total: number; halaman: number; per: number; ubah: (h: number) => void }) {
  const maks = Math.max(1, Math.ceil(total / per));
  if (maks <= 1) return null;
  return (
    <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
      <span>{total} data · halaman {halaman} dari {maks}</span>
      <div className="flex gap-2">
        <Tombol varian="sekunder" kecil disabled={halaman <= 1} onClick={() => ubah(halaman - 1)}>Sebelumnya</Tombol>
        <Tombol varian="sekunder" kecil disabled={halaman >= maks} onClick={() => ubah(halaman + 1)}>Berikutnya</Tombol>
      </div>
    </div>
  );
}

export function Progres({ persen, tahap }: { persen: number; tahap: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-600"><span>{tahap}</span><span>{persen}%</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={persen} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-utama-600 transition-all" style={{ width: `${persen}%` }} />
      </div>
    </div>
  );
}
