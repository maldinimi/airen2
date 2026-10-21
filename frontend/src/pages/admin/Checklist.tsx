/** Kelola Checklist (Modul B): tabel item; tambah/ubah/hapus langsung disimpan per item. Isi terbaru ada di
 *  checklist_item, setiap versi (termasuk terbaru) dicatat backend di checklist_histori, sehingga review
 *  lama tetap menampilkan checklist yang dipakai saat itu. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowLeft, ArrowUp, ArrowUpDown, Eye, GripVertical, ListOrdered, Pencil, Plus, Trash2, TriangleAlert } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { api } from "../../api";
import { waktuAngka } from "../../format";
import type { ItemChecklist } from "../../types";
import { AreaTeks, Dialog, Input, Judul, Kartu, Kolom, Kosong, Lencana, Memuat, Peringatan, Pilih, Saklar, Tombol, cx } from "../../ui";

const BERLAKU = { TOR: "TOR", RAB: "RAB", "TOR & RAB": "TOR & RAB" };
const ENDPOINT = "/api/checklist";
type Data = { item: ItemChecklist[] };
type Aksi = { jenis: "tambah"; nilai: ItemChecklist } | { jenis: "ubah"; nilai: ItemChecklist } | { jenis: "hapus"; id: string };
const isian = ({ kode, judul, kriteria, berlaku_untuk, aktif }: ItemChecklist) => ({ kode, judul, kriteria, berlaku_untuk, aktif });

/** Urut kode alami: angka dibandingkan sebagai angka (C2 < C10), selain itu per karakter (I.T.1 < II.A.1). */
function bandingKode(a: string, b: string): number {
  const pa = a.split(/(\d+)/), pb = b.split(/(\d+)/);
  for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
    if (pa[i] === pb[i]) continue;
    return i % 2 ? Number(pa[i]) - Number(pb[i]) : pa[i] < pb[i] ? -1 : 1;
  }
  return pa.length - pb.length;
}

type KolomUrut = "kode" | "judul" | "kriteria" | "berlaku_untuk" | "aktif" | "diubah_oleh" | "diubah_at";
const HEADER: [string, KolomUrut | null][] = [["Kode", "kode"], ["Checklist", "judul"], ["Kriteria Lolos", "kriteria"],
  ["Berlaku Untuk", "berlaku_untuk"], ["Status", "aktif"], ["Last Modified By", "diubah_oleh"], ["Last Modified Date", "diubah_at"], ["Aksi", null]];

const LencanaStatus = ({ aktif }: { aktif: boolean }) => aktif
  ? <Lencana className="bg-emerald-50 text-emerald-700 ring-emerald-300">Aktif</Lencana>
  : <Lencana className="bg-slate-100 text-slate-600 ring-slate-300">Nonaktif</Lencana>;

const LencanaBerlaku = ({ b }: { b: ItemChecklist["berlaku_untuk"] }) =>
  <Lencana className="bg-slate-100 text-slate-600 ring-slate-200">{BERLAKU[b]}</Lencana>;

export default function KelolaChecklist() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: [ENDPOINT], queryFn: () => api.get<Data>(ENDPOINT) });
  const [form, setForm] = useState<{ idx: number | null; nilai: ItemChecklist } | null>(null);
  const item = q.data?.item ?? [];
  // CRUD per item; jejak "terakhir diubah" & versi lama diisi server.
  const simpan = useMutation({
    mutationFn: (a: Aksi) => a.jenis === "tambah" ? api.post(`${ENDPOINT}/item`, isian(a.nilai))
      : a.jenis === "ubah" ? api.put(`${ENDPOINT}/item/${a.nilai.id}`, isian(a.nilai))
      : api.del(`${ENDPOINT}/item/${a.id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ENDPOINT] }),
  });
  const [lihat, setLihat] = useState<string | null>(null);
  const [atur, setAtur] = useState(false);
  const [sukses, setSukses] = useState<string | null>(null);
  useEffect(() => { if (!sukses) return; const t = setTimeout(() => setSukses(null), 4000); return () => clearTimeout(t); }, [sukses]);
  const halaman = form ? "form" : lihat ? "detail" : atur ? "atur" : "tabel";
  useEffect(() => { document.querySelector("main")?.scrollTo(0, 0); }, [halaman]);

  if (q.isLoading) return <Memuat />;
  if (q.error) return <Peringatan>{(q.error as Error).message}</Peringatan>;

  const buka = (idx: number | null) => {
    simpan.reset();
    setForm({ idx, nilai: idx === null ? { kode: "", judul: "", kriteria: "", berlaku_untuk: "TOR", aktif: true } : { ...item[idx] } });
  };

  if (form) return (
    <FormItem form={form} sibuk={simpan.isPending} galat={simpan.error} tutup={() => setForm(null)}
      kirim={(nilai) => simpan.mutate(form.idx === null ? { jenis: "tambah", nilai } : { jenis: "ubah", nilai: { ...nilai, id: item[form.idx].id } },
        { onSuccess: () => { if (form.idx === null) setSukses(`Item ${nilai.kode.trim().toUpperCase()} berhasil disimpan.`); setForm(null); } })} />
  );

  const dilihat = lihat ? item.find((x) => x.id === lihat) : undefined;
  if (dilihat) return <DetailItem i={dilihat} tutup={() => setLihat(null)} />;
  if (atur) return <AturUrutan item={item} tutup={() => setAtur(false)} disimpan={() => { setSukses("Urutan berhasil disimpan."); setAtur(false); }} />;

  return (
    <div className="w-full">
      <Judul judul="Kelola Checklist"
        sub="Setiap tambah dan perubahan item tercatat di riwayat. Review lama tetap menampilkan isi checklist saat review dimulai."
        aksi={<>
          <Tombol varian="sekunder" onClick={() => setAtur(true)} disabled={item.length < 2}><ListOrdered className="size-4" />Atur Urutan</Tombol>
          <Tombol onClick={() => buka(null)}><Plus className="size-4" />Tambah Item</Tombol>
        </>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {simpan.error && <div className="mb-3"><Peringatan>{(simpan.error as Error).message}</Peringatan></div>}
      {item.length === 0 ? <Kosong>Belum ada checklist.</Kosong> : (
        <TabelChecklist item={item} sibuk={simpan.isPending} ubah={buka}
          hapus={(id, selesai) => {
            const kode = item.find((x) => x.id === id)?.kode;
            simpan.mutate({ jenis: "hapus", id }, { onSuccess: () => setSukses(`Item ${kode} berhasil dihapus.`), onSettled: selesai });
          }}
          lihat={setLihat} />
      )}
    </div>
  );
}

function FormItem({ form, sibuk, galat, tutup, kirim }: {
  form: { idx: number | null; nilai: ItemChecklist }; sibuk: boolean; galat: Error | null;
  tutup: () => void; kirim: (nilai: ItemChecklist) => void;
}) {
  const [n, setN] = useState(form.nilai);
  const set = <K extends keyof ItemChecklist>(k: K, v: ItemChecklist[K]) => setN({ ...n, [k]: v });
  const submit = (e: FormEvent) => { e.preventDefault(); kirim({ ...n, kode: n.kode.trim().toUpperCase(), judul: n.judul.trim(), kriteria: n.kriteria.trim() }); };
  return (
    <div className="w-full">
      <button type="button" onClick={tutup} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="size-4" />Kembali
      </button>
      <Judul judul={form.idx === null ? "Tambah Item" : `Ubah Checklist ${form.nilai.kode}`}
        sub="Perubahan langsung disimpan sebagai versi checklist baru; review yang sudah berjalan tidak terpengaruh." />
      <Kartu className="p-5">
        <form className="space-y-4" onSubmit={submit}>
          {galat && <Peringatan>{galat.message}</Peringatan>}
          <Kolom label="Kode" wajib>
            <Input required maxLength={50} placeholder="mis. A.01" value={n.kode} onChange={(e) => set("kode", e.target.value)} />
          </Kolom>
          <Kolom label="Checklist" wajib><Input required value={n.judul} onChange={(e) => set("judul", e.target.value)} /></Kolom>
          <Kolom label="Kriteria lolos" wajib petunjuk="Tuliskan sejelas mungkin; AI menilai berdasarkan kriteria ini.">
            <AreaTeks required value={n.kriteria} onChange={(e) => set("kriteria", e.target.value)} />
          </Kolom>
          <Kolom label="Berlaku untuk" wajib>
            <Pilih value={n.berlaku_untuk} onChange={(e) => set("berlaku_untuk", e.target.value as ItemChecklist["berlaku_untuk"])}>
              {Object.entries(BERLAKU).map(([nilai, label]) => <option key={nilai} value={nilai}>{label}</option>)}
            </Pilih>
          </Kolom>
          <div className="space-y-1.5">
            <span className="block text-sm font-medium text-slate-700">Status</span>
            <Saklar aktif={n.aktif} label="Status" ubah={(aktif) => set("aktif", aktif)} />
            <span className="block text-xs text-slate-500">Hanya checklist Aktif yang dinilai AI pada review berikutnya.</span>
          </div>
          <div className="flex justify-end gap-2">
            {form.idx === null && <Tombol type="button" varian="sekunder" onClick={() => setN(form.nilai)}>Reset</Tombol>}
            <Tombol type="submit" memuat={sibuk}>Simpan</Tombol>
          </div>
        </form>
      </Kartu>
    </div>
  );
}

function TabelChecklist({ item, sibuk, ubah, hapus, lihat }: {
  item: ItemChecklist[]; sibuk: boolean; ubah: (n: number) => void;
  hapus: (id: string, selesai: () => void) => void; lihat: (kode: string) => void;
}) {
  // Simpan itemnya (bukan indeks baris): setelah hapus daftar dimuat ulang & bergeser sebelum dialog tertutup.
  const [konfirmasi, setKonfirmasi] = useState<ItemChecklist | null>(null);
  const idHapus = konfirmasi?.id;
  const jumlahHistori = useQuery({ queryKey: [ENDPOINT, "riwayat", idHapus], enabled: !!idHapus,
    queryFn: () => api.get<unknown[]>(`${ENDPOINT}/item/${idHapus}/riwayat`) });
  // Pengurutan hanya tampilan; `n` di bawah tetap indeks item asli sehingga Edit/Hapus/Detail mengenai baris yang benar.
  // Bawaan (kolom null) = urutan yang diatur Admin (no_urut dari server).
  const [urut, setUrut] = useState<{ kolom: KolomUrut | null; naik: boolean }>({ kolom: null, naik: true });
  const nilai = (n: number, kolom: KolomUrut): string | number => {
    const i = item[n];
    if (kolom === "aktif") return i.aktif === false ? 1 : 0;
    if (kolom === "diubah_oleh") return i.diubah_oleh ?? "Sistem";
    if (kolom === "diubah_at") return i.diubah_at ?? "";
    return i[kolom];
  };
  const baris = item.map((_, n) => n).sort((a, b) => {
    const k = urut.kolom;
    if (k === null) return a - b;
    const x = nilai(a, k), y = nilai(b, k);
    const h = typeof x === "number" ? x - (y as number) : k === "kode" ? bandingKode(x, y as string) : x.localeCompare(y as string, "id");
    return (urut.naik ? h : -h) || a - b;
  });
  const klikUrut = (k: KolomUrut) => setUrut((u) => ({ kolom: k, naik: u.kolom === k ? !u.naik : true }));
  const tombol = "rounded-lg p-1.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";

  return (
    <>
      <Kartu className="overflow-x-auto">
        <table className="w-full min-w-[64rem] text-sm">
          <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
            <tr>{HEADER.map(([h, k]) => {
              const aktif = k !== null && urut.kolom === k;
              const Ikon = !aktif ? ArrowUpDown : urut.naik ? ArrowUp : ArrowDown;
              return (
                <th key={h} scope="col" className={cx("whitespace-nowrap px-3 py-2.5", k !== "judul" && k !== "kriteria" && "text-center")} aria-sort={aktif ? (urut.naik ? "ascending" : "descending") : undefined}>
                  {k === null ? h : (
                    <button type="button" onClick={() => klikUrut(k)} title={`Urutkan berdasarkan ${h}`}
                      className="inline-flex items-center gap-1 rounded font-semibold hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
                      {h}<Ikon className={cx("size-3.5", aktif ? "text-utama-600" : "text-slate-400")} aria-hidden />
                    </button>
                  )}
                </th>
              );
            })}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {baris.map((n) => { const i = item[n]; return (
              <tr key={i.kode} className="align-middle transition-colors hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{i.kode}</td>
                <td className="min-w-[12rem] px-3 py-2.5 text-slate-900">{i.judul}</td>
                <td className="min-w-[20rem] px-3 py-2.5 text-slate-600">{i.kriteria}</td>
                <td className="px-3 py-2.5 text-center"><LencanaBerlaku b={i.berlaku_untuk} /></td>
                <td className="px-3 py-2.5 text-center"><LencanaStatus aktif={i.aktif !== false} /></td>
                <td className="min-w-[9rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600">{i.diubah_oleh ?? "Sistem"}</td>
                <td className="min-w-[9.5rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600">{waktuAngka(i.diubah_at)}</td>
                <td className="whitespace-nowrap px-3 py-2 text-center">
                  <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700")} title="Detail" aria-label={`Detail ${i.kode}`} onClick={() => lihat(i.id!)}><Eye className="size-4" /></button>
                  <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50 hover:text-utama-700")} title="Edit" aria-label={`Edit ${i.kode}`} onClick={() => ubah(n)}><Pencil className="size-4" /></button>
                  <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50 hover:text-red-700")} title="Hapus" aria-label={`Hapus ${i.kode}`} onClick={() => setKonfirmasi(i)}><Trash2 className="size-4" /></button>
                </td>
              </tr>
            ); })}
          </tbody>
        </table>
      </Kartu>

      {konfirmasi !== null && (
        <Dialog buka ubahBuka={(b) => !b && setKonfirmasi(null)} judul="Hapus checklist secara permanen?"
          ikon={<div className="flex size-14 items-center justify-center rounded-full bg-red-50 text-red-600"><TriangleAlert className="size-7" /></div>}>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-slate-100">{([
                ["Kode", konfirmasi.kode],
                ["Checklist", konfirmasi.judul],
                ["Status", konfirmasi.aktif === false ? "Nonaktif" : "Aktif"],
                ["Checklist Histori", jumlahHistori.data ? `${jumlahHistori.data.length} versi` : "…"],
              ] as const).map(([l, v]) => (
                <tr key={l} className="align-top">
                  <th scope="row" className="w-40 px-3 py-2.5 text-left font-normal text-slate-500">{l}</th>
                  <td className="px-3 py-2.5 text-slate-800">{v}</td>
                </tr>))}</tbody>
            </table>
          </div>
          <p className="mt-4 text-sm text-slate-600">
            Checklist beserta Checklist Histori-nya dihapus dari database dan tidak dapat dikembalikan. Hasil review lama
            kehilangan item ini.
          </p>
          <div className="mt-5 flex justify-end gap-2">
            <Tombol varian="hantu" onClick={() => setKonfirmasi(null)}>Batal</Tombol>
            <Tombol varian="bahaya" memuat={sibuk} onClick={() => hapus(konfirmasi.id!, () => setKonfirmasi(null))}>Ya, hapus</Tombol>
          </div>
        </Dialog>
      )}

    </>
  );
}

/** Atur urutan item: seret baris atau tombol ▲▼ (untuk keyboard & layar sentuh), lalu simpan sekaligus. */
function AturUrutan({ item, tutup, disimpan }: { item: ItemChecklist[]; tutup: () => void; disimpan: () => void }) {
  const qc = useQueryClient();
  const [daftar, setDaftar] = useState(item);
  const [seret, setSeret] = useState<number | null>(null);
  const simpan = useMutation({
    mutationFn: () => api.put(`${ENDPOINT}/urutan`, { id: daftar.map((i) => i.id) }),
    onSuccess: async () => { await qc.invalidateQueries({ queryKey: [ENDPOINT] }); disimpan(); },
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
      <Judul judul="Atur Urutan Checklist" sub="Seret baris atau gunakan tombol naik/turun, lalu klik Simpan Urutan. Urutan ini dipakai di tabel checklist dan saat AI menilai; item baru otomatis ditempatkan setelah kode sebelumnya." />
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

type EntriRiwayat = {
  id: string; kode: string; diubah_oleh: string | null; diubah_at: string;
} & Pick<ItemChecklist, KolomIsi>;
type KolomIsi = "judul" | "kriteria" | "berlaku_untuk" | "aktif";

/** Ikon mata: halaman detail (tabel label–nilai) + tabel riwayat semua perubahan (terbaru dulu), bergaya Detail Panduan. */
function DetailItem({ i, tutup }: { i: ItemChecklist; tutup: () => void }) {
  const kode = i.kode;
  const q = useQuery({ queryKey: [ENDPOINT, "riwayat", i.id], queryFn: () => api.get<EntriRiwayat[]>(`${ENDPOINT}/item/${i.id}/riwayat`) });
  const info: [string, ReactNode][] = [
    ["Kode", kode],
    ["Checklist", i.judul],
    ["Kriteria Lolos", <span className="whitespace-pre-line">{i.kriteria}</span>],
    ["Berlaku Untuk", <LencanaBerlaku b={i.berlaku_untuk} />],
    ["Status", <LencanaStatus aktif={i.aktif !== false} />],
    ["Terakhir Diubah", waktuAngka(i.diubah_at)],
    ["Diubah Oleh", i.diubah_oleh ?? "Sistem"],
  ];
  return (
    <div className="w-full space-y-4">
      <div>
        <button type="button" onClick={tutup} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" />Checklist
        </button>
        <Judul judul={`Detail Checklist ${kode}`} sub={i.judul} />
      </div>
      <Kartu className="space-y-5 p-5">
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-100">{info.map(([l, v]) => (
              <tr key={l} className="align-top">
                <th scope="row" className="w-40 px-3 py-2.5 text-left font-normal text-slate-500 sm:w-60">{l}</th>
                <td className="px-3 py-2.5 text-slate-800">{v}</td>
              </tr>))}</tbody>
          </table>
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Riwayat Data</h2>
          {/* checklist_histori memuat semua versi; versi terbaru sudah di tabel atas → Riwayat Data = versi sebelumnya. */}
          {q.isLoading ? <Memuat /> : q.error ? <Peringatan>{(q.error as Error).message}</Peringatan> : q.data!.length < 2 ? <Kosong>Belum ada perubahan sebelumnya.</Kosong> : (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full min-w-[56rem] text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-500">
                  <tr>{["Tanggal Input", "Diinput Oleh", "Status", "Kode", "Checklist", "Kriteria Lolos", "Berlaku Untuk"].map((h) => (
                    <th key={h} scope="col" className="whitespace-nowrap px-3 py-2 text-center">{h}</th>))}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">{q.data!.slice(1).map((r) => (
                  <tr key={r.id} className="align-middle">
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-500">{waktuAngka(r.diubah_at)}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-700">{r.diubah_oleh ?? "Sistem"}</td>
                    <td className="px-3 py-2.5 text-center"><LencanaStatus aktif={r.aktif} /></td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{r.kode}</td>
                    <td className="min-w-[12rem] px-3 py-2.5 text-slate-800">{r.judul}</td>
                    <td className="min-w-[20rem] whitespace-pre-line px-3 py-2.5 text-slate-700">{r.kriteria}</td>
                    <td className="px-3 py-2.5 text-center"><LencanaBerlaku b={r.berlaku_untuk} /></td>
                  </tr>))}</tbody>
              </table>
            </div>
          )}
        </div>
      </Kartu>
    </div>
  );
}
