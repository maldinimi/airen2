import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, qs } from "../../api";
import { waktu } from "../../format";
import { Dialog, Halaman, Input, Judul, Kartu, Kolom, Memuat, Pilih } from "../../ui";

type Baris = { id: string; at: string; pengguna: string | null; aksi: string; entitas: string; entitas_id: string | null;
  data_sebelum: unknown; data_sesudah: unknown; ip: string | null };

export default function Audit() {
  const [f, setF] = useState({ aksi: "", entitas: "", dari: "", sampai: "", halaman: 1 });
  const [detail, setDetail] = useState<Baris | null>(null);
  const q = useQuery({ queryKey: ["audit", f], queryFn: () => api.get<{ total: number; data: Baris[]; aksi: string[] }>(`/api/audit${qs({
    ...f, dari: f.dari ? `${f.dari}T00:00:00+07:00` : "", sampai: f.sampai ? `${f.sampai}T23:59:59+07:00` : "" })}`) });
  const ubah = (k: string, v: string) => setF({ ...f, [k]: v, halaman: 1 });

  return (
    <div>
      <Judul judul="Audit Log" sub="Aktivitas pengguna: perubahan checklist, kategori, panduan, pengguna, override, dan lainnya." />
      <Kartu className="mb-4 grid gap-3 p-3 sm:grid-cols-4">
        <Kolom label="Aksi"><Pilih value={f.aksi} onChange={(e) => ubah("aksi", e.target.value)}><option value="">Semua</option>{q.data?.aksi.map((a) => <option key={a}>{a}</option>)}</Pilih></Kolom>
        <Kolom label="Entitas"><Pilih value={f.entitas} onChange={(e) => ubah("entitas", e.target.value)}><option value="">Semua</option>
          {["usulan", "revisi", "review", "checklist_item", "checklist_versi", "kategori", "panduan", "pengguna", "satker", "node_ai"].map((x) => <option key={x}>{x}</option>)}</Pilih></Kolom>
        <Kolom label="Dari tanggal"><Input type="date" value={f.dari} onChange={(e) => ubah("dari", e.target.value)} /></Kolom>
        <Kolom label="Sampai tanggal"><Input type="date" value={f.sampai} onChange={(e) => ubah("sampai", e.target.value)} /></Kolom>
      </Kartu>
      {q.isLoading ? <Memuat /> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{["Waktu", "Pengguna", "Aksi", "Entitas", "IP", ""].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
            <tbody className="divide-y divide-slate-100">{q.data?.data.map((b) => (
              <tr key={b.id}><td className="whitespace-nowrap px-3 py-2">{waktu(b.at)}</td><td className="px-3 py-2">{b.pengguna ?? "—"}</td>
                <td className="px-3 py-2 font-medium">{b.aksi}</td><td className="px-3 py-2">{b.entitas}</td><td className="px-3 py-2 text-slate-500">{b.ip}</td>
                <td className="px-3 py-2">{!!(b.data_sebelum || b.data_sesudah) && <button className="text-utama-600 hover:underline" onClick={() => setDetail(b)}>Detail</button>}</td></tr>))}</tbody>
          </table>
        </Kartu>
      )}
      {q.data && <Halaman total={q.data.total} halaman={f.halaman} per={50} ubah={(h) => setF({ ...f, halaman: h })} />}
      <Dialog buka={!!detail} ubahBuka={() => setDetail(null)} judul={`${detail?.aksi} · ${detail?.entitas}`} lebar="max-w-3xl">
        <div className="grid gap-3 text-xs sm:grid-cols-2">
          <div><div className="mb-1 font-semibold">Sebelum</div><pre className="max-h-96 overflow-auto rounded-lg bg-slate-100 p-3">{JSON.stringify(detail?.data_sebelum, null, 2) ?? "—"}</pre></div>
          <div><div className="mb-1 font-semibold">Sesudah</div><pre className="max-h-96 overflow-auto rounded-lg bg-slate-100 p-3">{JSON.stringify(detail?.data_sesudah, null, 2) ?? "—"}</pre></div>
        </div>
      </Dialog>
    </div>
  );
}
