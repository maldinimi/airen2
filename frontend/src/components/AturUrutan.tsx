/** Atur urutan (Checklist, Kategori): seret baris atau tombol ▲▼ (untuk keyboard & layar sentuh), lalu simpan sekaligus
 *  lewat `PUT {endpoint}/urutan` dengan semua id sesuai urutan baru. */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowLeft, ArrowUp, GripVertical } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { Judul, Kartu, Peringatan, Tombol, cx } from "../ui";

type Baris = { id?: string; kode: string; judul: string };

export default function AturUrutan({ judul, sub, endpoint, item, tutup, disimpan }: {
  judul: string; sub: string; endpoint: string; item: Baris[]; tutup: () => void; disimpan: () => void;
}) {
  const qc = useQueryClient();
  const [daftar, setDaftar] = useState(item);
  const [seret, setSeret] = useState<number | null>(null);
  const simpan = useMutation({
    mutationFn: () => api.put(`${endpoint}/urutan`, { id: daftar.map((i) => i.id) }),
    onSuccess: async () => { await qc.invalidateQueries({ queryKey: [endpoint] }); disimpan(); },
  });
  const pindah = (dari: number, ke: number) => {
    if (ke < 0 || ke >= daftar.length || dari === ke) return;
    const d = [...daftar];
    d.splice(ke, 0, ...d.splice(dari, 1));
    setDaftar(d);
  };
  const tombol = "rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 disabled:opacity-30 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";
  return (
    <div className="w-full">
      <button type="button" onClick={tutup} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="size-4" />Kembali
      </button>
      <Judul judul={judul} sub={sub} />
      {simpan.error && <div className="mb-3"><Peringatan>{(simpan.error as Error).message}</Peringatan></div>}
      <Kartu className="divide-y divide-slate-100">
        {daftar.map((i, n) => (
          <div key={i.id} draggable onDragStart={() => setSeret(n)} onDragEnd={() => setSeret(null)}
            onDragOver={(e) => { e.preventDefault(); if (seret !== null && seret !== n) { pindah(seret, n); setSeret(n); } }}
            className={cx("flex items-center gap-3 px-3 py-2.5", seret === n && "bg-utama-50")}>
            <GripVertical className="size-4 shrink-0 cursor-grab text-slate-400" aria-hidden />
            <span className="w-6 shrink-0 text-right text-xs text-slate-400">{n + 1}</span>
            <span className="w-14 shrink-0 text-sm font-medium text-slate-900">{i.kode}</span>
            <span className="min-w-0 flex-1 truncate text-sm text-slate-700">{i.judul}</span>
            <button type="button" className={tombol} disabled={n === 0} onClick={() => pindah(n, n - 1)} aria-label={`Naikkan ${i.kode}`} title="Naikkan"><ArrowUp className="size-4" /></button>
            <button type="button" className={tombol} disabled={n === daftar.length - 1} onClick={() => pindah(n, n + 1)} aria-label={`Turunkan ${i.kode}`} title="Turunkan"><ArrowDown className="size-4" /></button>
          </div>
        ))}
      </Kartu>
      <div className="mt-4 flex justify-end gap-2">
        <Tombol memuat={simpan.isPending} onClick={() => simpan.mutate()}>Simpan Urutan</Tombol>
      </div>
    </div>
  );
}
