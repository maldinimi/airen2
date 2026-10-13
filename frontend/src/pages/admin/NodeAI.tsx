/** Node AI: daftar node (worker + llm), pendaftaran node GPU sewaan (token sekali tampil), pencabutan akses. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { api } from "../../api";
import { waktu } from "../../format";
import { Dialog, Input, Judul, Kartu, Kolom, Lencana, Memuat, Peringatan, Tombol } from "../../ui";

type Node = { id: string; nama: string; aktif: boolean; jarak_jauh: boolean; terakhir_terlihat: string | null; info: Record<string, string> | null };

export default function NodeAI() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["node"], queryFn: () => api.get<Node[]>("/api/node-ai"), refetchInterval: 15000 });
  const [buka, setBuka] = useState(false);
  const [nama, setNama] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const daftar = useMutation({ mutationFn: () => api.post<{ token: string }>("/api/node-ai", { nama }),
    onSuccess: (d) => { setToken(d.token); qc.invalidateQueries({ queryKey: ["node"] }); } });
  const cabut = useMutation({ mutationFn: (id: string) => api.post(`/api/node-ai/${id}/cabut`), onSuccess: () => qc.invalidateQueries({ queryKey: ["node"] }) });
  const aktif = (n: Node) => n.aktif && n.terakhir_terlihat && Date.now() - new Date(n.terakhir_terlihat).getTime() < 90_000;

  return (
    <div className="max-w-4xl">
      <Judul judul="Node AI" sub="Satu node = worker + model di satu server GPU. Tambah node untuk menambah kapasitas review tanpa mengubah kode."
        aksi={<Tombol onClick={() => { setBuka(true); setToken(null); setNama(""); daftar.reset(); }}><Plus className="size-4" />Daftarkan node GPU sewaan</Tombol>} />
      {q.isLoading ? <Memuat /> : (
        <Kartu className="divide-y divide-slate-100">{q.data?.map((n) => (
          <div key={n.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
            <span className="font-medium">{n.nama}</span>
            <Lencana className={aktif(n) ? "bg-emerald-50 text-emerald-700 ring-emerald-300" : "bg-slate-100 text-slate-600 ring-slate-300"}>{aktif(n) ? "Terhubung" : n.aktif ? "Tidak terhubung" : "Dicabut"}</Lencana>
            <span className="text-slate-500">{n.jarak_jauh ? "Jarak jauh (WireGuard)" : "Lokal"} · {n.info?.model ?? "—"} · terakhir {waktu(n.terakhir_terlihat)}</span>
            {n.aktif && n.jarak_jauh && <Tombol varian="hantu" kecil className="ml-auto text-red-600" onClick={() => confirm(`Cabut akses node ${n.nama}?`) && cabut.mutate(n.id)}>Cabut akses</Tombol>}
          </div>))}
          {!q.data?.length && <p className="p-4 text-sm text-slate-500">Belum ada node yang pernah terhubung.</p>}
        </Kartu>
      )}
      <Dialog buka={buka} ubahBuka={setBuka} judul="Daftarkan node AI">
        {token ? (
          <div className="space-y-3 text-sm">
            <Peringatan jenis="warn">Salin token ini sekarang — token hanya ditampilkan sekali.</Peringatan>
            <code className="block break-all rounded-lg bg-slate-100 p-3 text-xs">{token}</code>
            <p>Isi pada file <code>.env</code> node: <code>NODE_TOKEN=…</code> dan <code>NODE_NAMA={nama}</code>, lalu jalankan <code>make up-ai</code>. Lihat docs/instalasi-offline.md.</p>
            <div className="flex justify-end"><Tombol onClick={() => setBuka(false)}>Selesai</Tombol></div>
          </div>
        ) : (
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); daftar.mutate(); }}>
            {daftar.error && <Peringatan>{(daftar.error as Error).message}</Peringatan>}
            <Kolom label="Nama node" wajib petunjuk="mis. gpu-h100-1"><Input required value={nama} onChange={(e) => setNama(e.target.value)} /></Kolom>
            <div className="flex justify-end gap-2"><Tombol type="button" varian="hantu" onClick={() => setBuka(false)}>Batal</Tombol><Tombol type="submit" memuat={daftar.isPending}>Daftarkan</Tombol></div>
          </form>
        )}
      </Dialog>
    </div>
  );
}
