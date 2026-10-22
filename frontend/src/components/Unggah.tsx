/** Area seret-lepas PDF dengan validasi langsung (hanya PDF, maks. 100 MB). */
import { FileText, UploadCloud, X } from "lucide-react";
import { type DragEvent, useRef, useState } from "react";
import { cx, Tombol } from "../ui";

export const MAKS_MB = 100;

export function validasiPdf(f: File): string | null {
  if (!f.name.toLowerCase().endsWith(".pdf") && f.type !== "application/pdf") return `"${f.name}" bukan file PDF.`;
  if (f.size > MAKS_MB * 1024 * 1024) return `"${f.name}" melebihi ${MAKS_MB} MB.`;
  return null;
}

/** `lihat` diisi → tombol "Pratinjau" pada baris file terpilih. */
export default function Unggah({ label, file, ubah, banyak, keterangan, lihat }:
  { label: string; file: File | File[] | null; ubah: (f: File[] ) => void; banyak?: boolean; keterangan?: string; lihat?: (f: File) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [seret, setSeret] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);
  const daftar = file ? (Array.isArray(file) ? file : [file]) : [];

  const pilih = (fs: FileList | null) => {
    if (!fs?.length) return;
    const arr = Array.from(fs).slice(0, banyak ? 50 : 1);
    const g = arr.map(validasiPdf).find(Boolean);
    setGalat(g ?? null);
    if (!g) ubah(arr);
  };
  const lepas = (e: DragEvent) => { e.preventDefault(); setSeret(false); pilih(e.dataTransfer.files); };

  return (
    <div className="space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {/* File terpilih tampil di dalam kotak, menggantikan ajakan "Seret PDF". Kotak tetap menerima seret-lepas untuk mengganti file. */}
      <div onDragOver={(e) => { e.preventDefault(); setSeret(true); }} onDragLeave={() => setSeret(false)} onDrop={lepas}
        className={cx("rounded-xl border-2 border-dashed text-sm transition-colors",
          seret ? "border-utama-500 bg-utama-50" : cx("border-slate-300 bg-white", !daftar.length && "hover:border-utama-500"))}>
        {daftar.length ? daftar.map((f) => (
          <div key={f.name + f.size} className="flex items-center gap-2 px-4 py-3">
            <FileText className="size-4 shrink-0 text-utama-600" /><span className="truncate">{f.name}</span>
            <span className="ml-auto shrink-0 text-xs text-slate-500">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
            {lihat && <Tombol type="button" varian="lembut" onClick={() => lihat(f)}>Pratinjau</Tombol>}
            <button type="button" onClick={() => ubah([])} aria-label="Hapus pilihan" className="text-slate-400 hover:text-red-600"><X className="size-4" /></button>
          </div>
        )) : (
          <div role="button" tabIndex={0} onClick={() => input.current?.click()} onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
            className="flex cursor-pointer flex-col items-center justify-center gap-1 px-4 py-6 text-center">
            <UploadCloud className="size-6 text-slate-400" aria-hidden />
            <span className="text-slate-600">Seret PDF ke sini atau <span className="font-medium text-utama-600">pilih file</span></span>
            <span className="text-xs text-slate-400">{keterangan ?? `PDF, maks. ${MAKS_MB} MB`}</span>
          </div>
        )}
        {/* value dikosongkan agar file yang sama dapat dipilih lagi setelah dihapus (× ). */}
        <input ref={input} type="file" accept="application/pdf,.pdf" multiple={banyak} hidden
          onChange={(e) => { pilih(e.target.files); e.target.value = ""; }} />
      </div>
      {galat && <p className="text-xs text-red-600" role="alert">{galat}</p>}
    </div>
  );
}
