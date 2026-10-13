/** Editor daftar berversi (Checklist & Kategori): sunting draf → "Simpan sebagai versi baru"; tab Versi menampilkan isi tiap versi. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Pencil, Plus, Trash2 } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { api } from "../api";
import { waktu } from "../format";
import type { RingkasVersi, Versi } from "../types";
import { AreaTeks, Dialog, Input, Judul, Kartu, Kolom, Kosong, Lencana, Memuat, Peringatan, Pilih, Tab, Tombol } from "../ui";

export type DefKolom<T> = { nama: keyof T & string; label: string; jenis: "teks" | "area" | "pilih" | "cek"; opsi?: { nilai: string; label: string }[]; petunjuk?: string };

export default function EditorVersi<T extends { kode: string }>({ judul, sub, endpoint, kolom, kosong, ringkas }: {
  judul: string; sub: string; endpoint: string; kolom: DefKolom<T>[]; kosong: T; ringkas: (i: T) => ReactNode;
}) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: [endpoint], queryFn: () => api.get<{ aktif: Versi<T> | null; versi: RingkasVersi[] }>(endpoint) });
  const [tab, setTab] = useState<"sunting" | "versi">("sunting");
  const [draf, setDraf] = useState<T[]>([]);
  const [berubah, setBerubah] = useState(false);
  const [catatan, setCatatan] = useState("");
  const [form, setForm] = useState<{ idx: number | null; nilai: T } | null>(null);
  const [lihat, setLihat] = useState<string | null>(null);

  useEffect(() => { if (q.data && !berubah) setDraf((q.data.aktif?.item ?? []).map(({ ...i }) => i)); }, [q.data, berubah]);
  const ubahDraf = (d: T[]) => { setDraf(d); setBerubah(true); };
  const simpan = useMutation({
    mutationFn: () => api.post(`${endpoint}/versi`, { catatan, item: draf.map((i) => Object.fromEntries(kolom.map((k) => [k.nama, i[k.nama]]))) }),
    onSuccess: () => { setBerubah(false); setCatatan(""); qc.invalidateQueries({ queryKey: [endpoint] }); },
  });
  const isiVersi = useQuery({ queryKey: [endpoint, "versi", lihat], queryFn: () => api.get<Versi<T>>(`${endpoint}/versi/${lihat}`), enabled: !!lihat });

  if (q.isLoading) return <Memuat />;
  const pindah = (i: number, arah: number) => { const d = [...draf]; [d[i], d[i + arah]] = [d[i + arah], d[i]]; ubahDraf(d); };

  return (
    <div className="max-w-4xl">
      <Judul judul={judul} sub={sub} />
      <Tab aktif={tab} ubah={setTab} pilihan={[{ nilai: "sunting", label: `Versi aktif${q.data?.aktif ? ` (v${q.data.aktif.nomor})` : ""}` }, { nilai: "versi", label: "Daftar versi" }]} />
      {tab === "sunting" ? (
        <div className="mt-4 space-y-3">
          {berubah && <Peringatan jenis="warn">Ada perubahan yang belum disimpan. Perubahan baru berlaku setelah disimpan sebagai versi baru; review yang sudah berjalan tidak terpengaruh.</Peringatan>}
          {simpan.error && <Peringatan>{(simpan.error as Error).message}</Peringatan>}
          {draf.length === 0 && <Kosong>Belum ada item.</Kosong>}
          {draf.map((i, n) => (
            <Kartu key={n} className="flex gap-3 p-3">
              <div className="flex flex-col">
                <button disabled={n === 0} onClick={() => pindah(n, -1)} className="rounded p-1 text-slate-400 hover:bg-slate-100 disabled:opacity-30" aria-label="Naikkan"><ArrowUp className="size-4" /></button>
                <button disabled={n === draf.length - 1} onClick={() => pindah(n, 1)} className="rounded p-1 text-slate-400 hover:bg-slate-100 disabled:opacity-30" aria-label="Turunkan"><ArrowDown className="size-4" /></button>
              </div>
              <div className="min-w-0 flex-1 text-sm">{ringkas(i)}</div>
              <div className="flex shrink-0 gap-1">
                <Tombol varian="hantu" kecil onClick={() => setForm({ idx: n, nilai: { ...i } })} aria-label="Ubah"><Pencil className="size-4" /></Tombol>
                <Tombol varian="hantu" kecil className="text-red-600" onClick={() => confirm(`Hapus item ${i.kode}?`) && ubahDraf(draf.filter((_, x) => x !== n))} aria-label="Hapus"><Trash2 className="size-4" /></Tombol>
              </div>
            </Kartu>
          ))}
          <Tombol varian="sekunder" onClick={() => setForm({ idx: null, nilai: { ...kosong } })}><Plus className="size-4" />Tambah item</Tombol>
          <Kartu className="space-y-3 p-4">
            <Kolom label="Catatan perubahan (opsional)"><Input value={catatan} onChange={(e) => setCatatan(e.target.value)} placeholder="mis. Menambah item indikator kinerja" /></Kolom>
            <div className="flex gap-2">
              <Tombol disabled={!berubah || !draf.length} memuat={simpan.isPending} onClick={() => simpan.mutate()}>Simpan sebagai versi baru</Tombol>
              {berubah && <Tombol varian="hantu" onClick={() => setBerubah(false)}>Batalkan perubahan</Tombol>}
            </div>
          </Kartu>
        </div>
      ) : (
        <div className="mt-4 space-y-2">
          {q.data?.versi.map((v) => (
            <Kartu key={v.id} className="p-3">
              <button className="flex w-full flex-wrap items-center gap-2 text-left text-sm" onClick={() => setLihat(lihat === v.id ? null : v.id)}>
                <span className="font-semibold">Versi {v.nomor}</span>{v.aktif && <Lencana className="bg-emerald-50 text-emerald-700 ring-emerald-300">Aktif</Lencana>}
                <span className="text-slate-500">{v.jumlah_item} item · {waktu(v.dibuat_at)} · {v.dibuat_oleh ?? "sistem"}</span>
                {v.catatan && <span className="w-full text-xs text-slate-500">{v.catatan}</span>}
              </button>
              {lihat === v.id && (isiVersi.isLoading ? <Memuat /> : (
                <ol className="mt-3 space-y-2 border-t border-slate-100 pt-3">{isiVersi.data?.item.map((i) => <li key={i.kode} className="text-sm">{ringkas(i)}</li>)}</ol>
              ))}
            </Kartu>
          ))}
        </div>
      )}

      {form && (
        <Dialog buka ubahBuka={(b) => !b && setForm(null)} judul={form.idx === null ? "Tambah item" : `Ubah item ${form.nilai.kode}`}>
          <form className="space-y-4" onSubmit={(e) => {
            e.preventDefault();
            const kodeBaru = form.nilai.kode.trim().toUpperCase();
            if (draf.some((d, x) => x !== form.idx && d.kode.toUpperCase() === kodeBaru)) return alert("Kode sudah dipakai.");
            const nilai = { ...form.nilai, kode: kodeBaru };
            ubahDraf(form.idx === null ? [...draf, nilai] : draf.map((d, x) => (x === form.idx ? nilai : d)));
            setForm(null);
          }}>
            {kolom.map((k) => {
              const v = form.nilai[k.nama] as unknown;
              const set = (x: unknown) => setForm({ ...form, nilai: { ...form.nilai, [k.nama]: x } });
              if (k.jenis === "cek") return <label key={k.nama} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!v} onChange={(e) => set(e.target.checked)} />{k.label}</label>;
              return (
                <Kolom key={k.nama} label={k.label} wajib petunjuk={k.petunjuk}>
                  {k.jenis === "area" ? <AreaTeks required value={String(v ?? "")} onChange={(e) => set(e.target.value)} />
                    : k.jenis === "pilih" ? <Pilih value={String(v)} onChange={(e) => set(e.target.value)}>{k.opsi!.map((o) => <option key={o.nilai} value={o.nilai}>{o.label}</option>)}</Pilih>
                    : <Input required value={String(v ?? "")} onChange={(e) => set(e.target.value)} />}
                </Kolom>
              );
            })}
            <div className="flex justify-end gap-2"><Tombol type="button" varian="hantu" onClick={() => setForm(null)}>Batal</Tombol><Tombol type="submit">Simpan ke draf</Tombol></div>
          </form>
        </Dialog>
      )}
    </div>
  );
}
