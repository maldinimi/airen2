/** Komponen UI bersama (gaya shadcn/ui di atas Radix + Tailwind). */
import * as D from "@radix-ui/react-dialog";
import { AlertTriangle, ChevronLeft, ChevronRight, CircleCheck, Loader2, X } from "lucide-react";
import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes,
  type TextareaHTMLAttributes, forwardRef } from "react";
import { waktuAngka } from "./format";
import type { StatusRevisi } from "./types";

export const cx = (...k: (string | false | null | undefined)[]) => k.filter(Boolean).join(" ");

/** Sel tanggal di tabel (Usulan, Panduan, Checklist): tanggal (dd/mm/yyyy) di atas, jam di bawahnya dengan huruf lebih kecil.
 *  Kosong → "—". */
export function TanggalJam({ iso }: { iso?: string | null }) {
  const [tgl, jam] = waktuAngka(iso).split(" ");
  return <><div>{tgl}</div>{jam && <div className="text-xs text-slate-500">{jam}</div>}</>;
}

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

export const gayaInput = "w-full rounded-lg border border-slate-300 bg-white px-3 text-sm shadow-sm placeholder:text-slate-400 focus:border-utama-500 focus:outline-none focus:ring-2 focus:ring-utama-100 disabled:bg-slate-100";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) =>
  <input ref={ref} {...p} className={cx(gayaInput, "h-10", className)} />);
export const Pilih = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...p }, ref) =>
  <select ref={ref} {...p} className={cx(gayaInput, "h-10 pr-8", className)} />);
export const AreaTeks = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) =>
  <textarea ref={ref} {...p} className={cx(gayaInput, "py-2 min-h-24", className)} />);

export function Kolom({ label, wajib, petunjuk, galat, children }: { label: string; wajib?: boolean; petunjuk?: string; galat?: string | null; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}{wajib && <span className="text-red-600"> *</span>}</span>
      {children}
      {petunjuk && <span className="block text-xs text-slate-500">{petunjuk}</span>}
      {galat && <span className="block text-xs font-medium text-red-600" role="alert">{galat}</span>}
    </label>
  );
}

/** Kelas isian yang belum diisi/salah: seluruh kotak merah (latar & bingkai), dipakai bersama `Kolom galat`.
 *  `!` (important) agar menang atas latar bawaan `bg-white`/`disabled:bg-slate-100` di `gayaInput`. */
export const kelasGalat = (salah: boolean) =>
  (salah ? "border-red-500! bg-red-100! text-red-900 ring-2 ring-red-200 disabled:bg-red-100!" : undefined);

export const Kartu = ({ className, children }: { className?: string; children: ReactNode }) =>
  <div className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>{children}</div>;

export function Judul({ judul, sub, aksi }: { judul: ReactNode; sub?: ReactNode; aksi?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{judul}</h1>
        {sub && <p className="mt-1 text-sm text-slate-500">{sub}</p>}
      </div>
      {aksi && <div className="ml-auto flex flex-wrap justify-end gap-2">{aksi}</div>}
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

export const Memuat = ({ teks = "Memuat…" }: { teks?: string }) =>
  <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500"><Loader2 className="size-5 animate-spin" />{teks}</div>;

export function Peringatan({ jenis = "error", children }: { jenis?: "error" | "info" | "warn" | "sukses"; children: ReactNode }) {
  const g = { error: "bg-red-50 text-red-800 border-red-200", info: "bg-utama-50 text-utama-900 border-utama-100",
    warn: "bg-amber-50 text-amber-900 border-amber-200", sukses: "bg-emerald-50 text-emerald-800 border-emerald-200" }[jenis];
  const Ikon = jenis === "sukses" ? CircleCheck : AlertTriangle;
  return <div role={jenis === "error" ? "alert" : "status"} className={cx("flex gap-2 rounded-lg border px-3 py-2.5 text-sm", g)}>
    <Ikon className="mt-0.5 size-4 shrink-0" aria-hidden /><div>{children}</div></div>;
}

export function Kosong({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-slate-300 bg-white py-12 text-center text-sm text-slate-500">{children}</div>;
}

/** `ikon` (opsional): judul ditampilkan di tengah dengan ikon di atasnya (dipakai dialog konfirmasi hapus). */
export function Dialog({ buka, ubahBuka, judul, children, lebar = "max-w-lg", ikon }:
  { buka: boolean; ubahBuka: (b: boolean) => void; judul: string; children: ReactNode; lebar?: string; ikon?: ReactNode }) {
  return (
    <D.Root open={buka} onOpenChange={ubahBuka}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-40 bg-slate-900/40" />
        <D.Content className={cx("fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-white p-5 shadow-xl", lebar)}>
          {ikon ? (
            <div className="relative mb-4 pt-2 text-center">
              <D.Close className="absolute -top-1 right-0 rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Tutup"><X className="size-5" /></D.Close>
              <div className="mx-auto mb-3 w-fit">{ikon}</div>
              <D.Title className="text-lg font-semibold text-slate-900">{judul}</D.Title>
            </div>
          ) : (
            <div className="mb-4 flex items-start justify-between gap-4">
              <D.Title className="text-lg font-semibold text-slate-900">{judul}</D.Title>
              <D.Close className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Tutup"><X className="size-5" /></D.Close>
            </div>
          )}
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

/** Nomor halaman (‹ 1 2 3 ›) di kiri dan pilihan jumlah baris di kanan (bila `ubahPer` diisi); selalu tampil walau satu halaman. */
export function Halaman({ total, halaman, per, ubah, ubahPer, pilihan = [10, 20, 50, 100] }:
  { total: number; halaman: number; per: number; ubah: (h: number) => void; ubahPer?: (n: number) => void; pilihan?: number[] }) {
  const maks = Math.max(1, Math.ceil(total / per));
  // Banyak halaman: tampilkan awal, akhir, dan sekitar halaman aktif; celah ditandai "…".
  const nomor = Array.from({ length: maks }, (_, i) => i + 1).filter((n) => maks <= 7 || n === 1 || n === maks || Math.abs(n - halaman) <= 1);
  const kotak = "inline-flex size-8 items-center justify-center rounded-md text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
      <nav aria-label="Halaman" className="flex items-center gap-1">
        <button type="button" className={cx(kotak, "text-slate-500 hover:bg-slate-100 disabled:opacity-40")} disabled={halaman <= 1}
          onClick={() => ubah(halaman - 1)} aria-label="Halaman sebelumnya"><ChevronLeft className="size-4" /></button>
        {nomor.map((n, i) => (
          <span key={n} className="flex items-center gap-1">
            {i > 0 && n - nomor[i - 1] > 1 && <span className="px-1 text-slate-400">…</span>}
            <button type="button" aria-current={n === halaman ? "page" : undefined} onClick={() => ubah(n)}
              className={cx(kotak, n === halaman ? "bg-utama-600 font-semibold text-white" : "text-slate-700 hover:bg-slate-100")}>{n}</button>
          </span>
        ))}
        <button type="button" className={cx(kotak, "text-slate-500 hover:bg-slate-100 disabled:opacity-40")} disabled={halaman >= maks}
          onClick={() => ubah(halaman + 1)} aria-label="Halaman berikutnya"><ChevronRight className="size-4" /></button>
      </nav>
      {ubahPer && (
        <label className="flex items-center gap-2">
          <span>Baris per halaman</span>
          <select className="h-8 rounded-md border border-slate-300 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-utama-100"
            value={per} onChange={(e) => ubahPer(Number(e.target.value))}>
            {pilihan.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      )}
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

/** Saklar on/off (role=switch) dengan label status di sampingnya; lebar label tetap agar tata letak tidak bergeser. */
/** Pop-up konfirmasi menu Usulan: cukup "Apakah Anda Yakin?" dengan tombol Tidak/Ya, tanpa ringkasan (desain.md §7 no. 38). */
export function KonfirmasiYakin({ buka, batal, ya, memuat, galat, bahaya }:
  { buka: boolean; batal: () => void; ya: () => void; memuat?: boolean; galat?: string | null; bahaya?: boolean }) {
  return (
    <Dialog buka={buka} ubahBuka={(b) => !b && !memuat && batal()} judul="Apakah Anda Yakin?" lebar="max-w-sm"
      ikon={<span className={cx("flex size-12 items-center justify-center rounded-full", bahaya ? "bg-red-100" : "bg-amber-100")}>
        <AlertTriangle className={cx("size-6", bahaya ? "text-red-600" : "text-amber-600")} aria-hidden /></span>}>
      <div className="space-y-4">
        {galat && <Peringatan>{galat}</Peringatan>}
        <div className="flex justify-center gap-2">
          <Tombol varian="sekunder" disabled={memuat} onClick={batal} className="min-w-24">Tidak</Tombol>
          <Tombol varian={bahaya ? "bahaya" : "utama"} memuat={memuat} onClick={ya} className="min-w-24">Ya</Tombol>
        </div>
      </div>
    </Dialog>
  );
}

export function Saklar({ aktif, label, ubah }: { aktif: boolean; label: string; ubah: (aktif: boolean) => void }) {
  const isi = <>
    <span className={cx("relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors", aktif ? "bg-emerald-500" : "bg-slate-300")}>
      <span className={cx("absolute top-0.5 size-4 rounded-full bg-white shadow transition-transform", aktif ? "translate-x-4.5" : "translate-x-0.5")} />
    </span>
    <span className={cx("w-14 text-left text-xs font-medium", aktif ? "text-emerald-700" : "text-slate-500")}>{aktif ? "Aktif" : "Nonaktif"}</span>
  </>;
  return (
    <button type="button" role="switch" aria-checked={aktif} aria-label={label} onClick={() => ubah(!aktif)}
      title={aktif ? "Klik untuk menonaktifkan" : "Klik untuk mengaktifkan"}
      className="inline-flex items-center gap-2 rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">{isi}</button>
  );
}
