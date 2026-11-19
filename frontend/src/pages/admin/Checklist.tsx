/** Kelola Checklist (Modul B): tabel item; tambah/ubah/hapus langsung disimpan per item. Isi terbaru ada di
 *  checklist_item, setiap versi (termasuk terbaru) dicatat backend di checklist_histori, sehingga review
 *  lama tetap menampilkan checklist yang dipakai saat itu. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, ListOrdered, Pencil, Plus, Trash2, TriangleAlert } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import AturUrutan from "../../components/AturUrutan";
import { TOMBOL_IKON } from "../../components/Kelola";
import { FormFilter, type NilaiFilter, OPSI_STATUS, Paginasi, ThUrut, cocok, lolosJejak, lolosStatus, usePaginasi, useUrut, TabelGeser } from "../../components/TabelData";
import { waktuAngka } from "../../format";
import type { ItemChecklist } from "../../types";
import { AreaTeks, Dialog, Input, Judul, Kartu, Kolom, Kosong, Lencana, Memuat, Peringatan, Pilih, Saklar, TanggalJam, Tombol, cx } from "../../ui";

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
  ["Berlaku Untuk", "berlaku_untuk"], ["Status", "aktif"], ["Diinput Oleh", "diubah_oleh"], ["Tanggal Input", "diubah_at"], ["Aksi", null]];

const LencanaStatus = ({ aktif }: { aktif: boolean }) => aktif
  ? <Lencana className="bg-emerald-50 text-emerald-700 ring-emerald-300">Aktif</Lencana>
  : <Lencana className="bg-slate-100 text-slate-600 ring-slate-300">Nonaktif</Lencana>;

const LencanaBerlaku = ({ b }: { b: ItemChecklist["berlaku_untuk"] }) =>
  <Lencana className="bg-slate-100 text-slate-600 ring-slate-200">{BERLAKU[b]}</Lencana>;

export default function KelolaChecklist() {
  const qc = useQueryClient();
  // Reviewer mengelola; Pengusul membuka halaman ini hanya untuk melihat (backend menolak perubahan dari non-Reviewer).
  const kelola = useAuth().punya("REVIEWER");
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
  useEffect(() => { window.scrollTo(0, 0); }, [halaman]);

  if (q.isLoading) return <Memuat />;
  if (q.error) return <Peringatan>{(q.error as Error).message}</Peringatan>;

  const buka = (idx: number | null) => {
    simpan.reset();
    setForm({ idx, nilai: idx === null ? { kode: "", judul: "", kriteria: "", berlaku_untuk: "TOR", aktif: true } : { ...item[idx] } });
  };

  if (form && kelola) return (
    <FormItem form={form} sibuk={simpan.isPending} galat={simpan.error} tutup={() => setForm(null)}
      kirim={(nilai) => simpan.mutate(form.idx === null ? { jenis: "tambah", nilai } : { jenis: "ubah", nilai: { ...nilai, id: item[form.idx].id } },
        { onSuccess: () => { if (form.idx === null) setSukses(`Item ${nilai.kode.trim().toUpperCase()} berhasil disimpan.`); setForm(null); } })} />
  );

  const dilihat = lihat ? item.find((x) => x.id === lihat) : undefined;
  if (dilihat) return <DetailItem i={dilihat} tutup={() => setLihat(null)} />;
  if (atur && kelola) return <AturUrutan judul="Atur Urutan Checklist" endpoint={ENDPOINT} item={item} tutup={() => setAtur(false)}
    disimpan={() => { setSukses("Urutan berhasil disimpan."); setAtur(false); }} />;

  return (
    <div className="w-full">
      <Judul judul="Checklist"
        aksi={kelola && <>
          <Tombol varian="sekunder" onClick={() => setAtur(true)} disabled={item.length < 2}><ListOrdered className="size-4" />Atur Urutan</Tombol>
          <Tombol onClick={() => buka(null)}><Plus className="size-4" />Tambah Item</Tombol>
        </>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {simpan.error && <div className="mb-3"><Peringatan>{(simpan.error as Error).message}</Peringatan></div>}
      {item.length === 0 ? <Kosong>Belum ada checklist.</Kosong> : (
        <TabelChecklist item={item} kelola={kelola} sibuk={simpan.isPending} ubah={buka}
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
      <Judul judul={form.idx === null ? "Tambah Item" : `Ubah Checklist ${form.nilai.kode}`} />
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

function TabelChecklist({ item, kelola, sibuk, ubah, hapus, lihat }: {
  item: ItemChecklist[]; kelola: boolean; sibuk: boolean; ubah: (n: number) => void;
  hapus: (id: string, selesai: () => void) => void; lihat: (kode: string) => void;
}) {
  // Simpan itemnya (bukan indeks baris): setelah hapus daftar dimuat ulang & bergeser sebelum dialog tertutup.
  const [konfirmasi, setKonfirmasi] = useState<ItemChecklist | null>(null);
  const idHapus = konfirmasi?.id;
  const jumlahHistori = useQuery({ queryKey: [ENDPOINT, "riwayat", idHapus], enabled: !!idHapus,
    queryFn: () => api.get<unknown[]>(`${ENDPOINT}/item/${idHapus}/riwayat`) });
  // Filter & pengurutan hanya tampilan; `n` di bawah tetap indeks item asli sehingga Edit/Hapus/Detail mengenai baris yang benar.
  // Bawaan (kolom null) = urutan yang diatur Reviewer (no_urut dari server).
  const [f, setF] = useState<NilaiFilter>({});
  // useMemo: tanpanya array baru tiap render (mis. dialog hapus dibuka) membuat useUrut mengurutkan ulang.
  const lolos = useMemo(() => item.map((_, n) => n).filter((n) => {
    const i = item[n];
    // Satu filter per kolom tabel (urut kolom); penginput kosong tampil "Sistem" seperti di tabel.
    return cocok(f.kode, i.kode) && cocok(f.cari, i.judul) && cocok(f.kriteria, i.kriteria) && (!f.berlaku || i.berlaku_untuk === f.berlaku)
      && lolosStatus(f.status, i.aktif !== false) && lolosJejak(f, i);
  }), [item, f]);
  const { baris, urut, klik: klikUrut } = useUrut<number, KolomUrut>(lolos, {
    kode: (n) => item[n].kode, judul: (n) => item[n].judul, kriteria: (n) => item[n].kriteria, berlaku_untuk: (n) => item[n].berlaku_untuk,
    aktif: (n) => (item[n].aktif === false ? 1 : 0), diubah_oleh: (n) => item[n].diubah_oleh ?? "Sistem", diubah_at: (n) => item[n].diubah_at ?? "",
  }, { kode: bandingKode });
  // Paginasi di browser seperti Satuan Kerja & Master RO (bawaan 20 baris); kembali ke halaman 1 setiap filter/urutan berubah.
  const pg = usePaginasi(baris, [f, urut], 20);
  const tombol = TOMBOL_IKON;

  return (
    <>
      <FormFilter judul="Checklist" nilai={f} terapkan={setF} bidang={[
        { jenis: "teks", kunci: "kode", label: "Kode", placeholder: "Cari kode, mis. C01…" },
        { jenis: "teks", kunci: "cari", label: "Checklist", placeholder: "Cari checklist…" },
        { jenis: "teks", kunci: "kriteria", label: "Kriteria Lolos", placeholder: "Cari kriteria lolos…" },
        { jenis: "pilih", kunci: "berlaku", label: "Berlaku Untuk", semua: "Semua Dokumen", opsi: Object.entries(BERLAKU).map(([nilai, label]) => ({ nilai, label })), kecil: true },
        { jenis: "pilih", kunci: "status", label: "Status", semua: "Semua Status", opsi: OPSI_STATUS, kecil: true },
        { jenis: "teks", kunci: "oleh", label: "Diinput Oleh", placeholder: "Cari nama penginput…" },
        { jenis: "tanggal", kunci: "tanggal", label: "Tanggal Input", kecil: true },
      ]} />
      {baris.length === 0 && <Kosong>Tidak ada checklist yang cocok dengan filter.</Kosong>}
      {baris.length > 0 && <Kartu><TabelGeser>
        <table className="w-full min-w-[64rem] text-sm">
          <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
            <tr>{HEADER.map(([h, k]) => k === null
              ? <th key={h} scope="col" className="whitespace-nowrap px-3 py-2.5 text-center">{h}</th>
              : <ThUrut key={h} label={h} kolom={k} urut={urut} klik={klikUrut} />)}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {pg.tampil.map((n) => { const i = item[n]; return (
              <tr key={i.kode} className="align-middle transition-colors hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{i.kode}</td>
                <td className="min-w-[12rem] px-3 py-2.5 text-slate-900">{i.judul}</td>
                <td className="min-w-[20rem] px-3 py-2.5 text-justify text-slate-600">{i.kriteria}</td>
                <td className="px-3 py-2.5 text-center"><LencanaBerlaku b={i.berlaku_untuk} /></td>
                <td className="px-3 py-2.5 text-center"><LencanaStatus aktif={i.aktif !== false} /></td>
                <td className="min-w-[9rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600">{i.diubah_oleh ?? "Sistem"}</td>
                <td className="min-w-[9.5rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600"><TanggalJam iso={i.diubah_at} /></td>
                <td className="whitespace-nowrap px-3 py-2 text-center">
                  <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700")} title="Detail" aria-label={`Detail ${i.kode}`} onClick={() => lihat(i.id!)}><Eye className="size-4" /></button>
                  {kelola && <>
                    <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50 hover:text-utama-700")} title="Edit" aria-label={`Edit ${i.kode}`} onClick={() => ubah(n)}><Pencil className="size-4" /></button>
                    <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50 hover:text-red-700")} title="Hapus" aria-label={`Hapus ${i.kode}`} onClick={() => setKonfirmasi(i)}><Trash2 className="size-4" /></button>
                  </>}
                </td>
              </tr>
            ); })}
          </tbody>
        </table></TabelGeser>
      </Kartu>}
      {baris.length > 0 && <Paginasi {...pg} />}

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
    ["Tanggal Input", waktuAngka(i.diubah_at)],
    ["Diinput Oleh", i.diubah_oleh ?? "Sistem"],
  ];
  return (
    <div className="w-full space-y-4">
      <div>
        <button type="button" onClick={tutup} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" />Checklist
        </button>
        <Judul judul={`Detail Checklist ${kode}`} />
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
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-500"><TanggalJam iso={r.diubah_at} /></td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-700">{r.diubah_oleh ?? "Sistem"}</td>
                    <td className="px-3 py-2.5 text-center"><LencanaStatus aktif={r.aktif} /></td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{r.kode}</td>
                    <td className="min-w-[12rem] px-3 py-2.5 text-slate-800">{r.judul}</td>
                    <td className="min-w-[20rem] whitespace-pre-line px-3 py-2.5 text-justify text-slate-700">{r.kriteria}</td>
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
