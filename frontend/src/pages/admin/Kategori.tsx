/** Kelola Kategori (Modul C): tabel kategori; tambah/edit/detail di halaman tersendiri, hapus permanen. Isi terbaru ada
 *  di tabel kategori, isi sebelum tiap perubahan dicatat backend di kategori_histori. Review menyimpan salinan kategori yang
 *  dipakai, sehingga edit/hapus tidak mengubah review lama (C4). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import { waktuAngka } from "../../format";
import type { ItemKategori } from "../../types";
import { AreaTeks, Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Lencana, Memuat, Peringatan, Ringkasan, Saklar, Tombol, cx } from "../../ui";

const ENDPOINT = "/api/kategori";
const DASAR = "/kelola/kategori";
const kueri = { queryKey: [ENDPOINT], queryFn: () => api.get<{ item: ItemKategori[] }>(ENDPOINT) };
const riwayat = (id: string) => ({ queryKey: [ENDPOINT, "riwayat", id], queryFn: () => api.get<ItemKategori[]>(`${ENDPOINT}/${id}/riwayat`) });

// Sama dengan status panduan: Nonaktif = tetap tampil, tetapi tidak dipakai review berikutnya.
const LencanaAktif = ({ aktif }: { aktif: boolean }) =>
  <Lencana className={aktif ? "bg-emerald-50 text-emerald-700 ring-emerald-300" : "bg-red-50 text-red-700 ring-red-200"}>{aktif ? "Aktif" : "Nonaktif"}</Lencana>;

const Kembali = ({ ke = DASAR, teks = "Kembali" }: { ke?: string; teks?: string }) =>
  <Link to={ke} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />{teks}</Link>;

export default function KelolaKategori() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useQuery(kueri);
  const [hapus, setHapus] = useState<ItemKategori | null>(null);
  const [memuat, setMemuat] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);
  const jumlahHistori = useQuery({ ...riwayat(hapus?.id ?? ""), enabled: !!hapus });

  if (q.isLoading) return <Memuat />;
  if (q.error) return <Peringatan>{(q.error as Error).message}</Peringatan>;
  const item = q.data!.item;

  const yaHapus = async () => {
    setMemuat(true);
    try {
      await api.del(`${ENDPOINT}/${hapus!.id}`);
      // exact: riwayat kategori yang baru dihapus jangan ikut dimuat ulang (404).
      await qc.invalidateQueries({ queryKey: [ENDPOINT], exact: true });
      setHapus(null);
    } catch (e) { setGalat((e as Error).message); }
    finally { setMemuat(false); }
  };
  const tombol = "rounded-lg p-1.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";

  return (
    <div className="w-full">
      <Judul judul="Kelola Kategori"
        sub="AI memakai daftar kategori terbaru saat review dimulai. Setiap tambah dan perubahan tercatat di Kategori Histori; review lama tetap menampilkan kategori saat itu."
        aksi={<Tombol onClick={() => nav(`${DASAR}/tambah`)}><Plus className="size-4" />Tambah Kategori</Tombol>} />
      {item.length === 0 ? <Kosong>Belum ada kategori.</Kosong> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full min-w-[54rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
              <tr>{["Kode", "Kategori", "Status", "Deskripsi", "Aksi"].map((h) => <th key={h} scope="col" className="whitespace-nowrap px-3 py-2.5 text-center">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {item.map((k) => (
                <tr key={k.id} className="align-middle transition-colors hover:bg-slate-50">
                  <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{k.kode}</td>
                  <td className="min-w-[12rem] px-3 py-2.5 text-slate-900">{k.nama}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-center"><LencanaAktif aktif={k.aktif} /></td>
                  <td className="min-w-[24rem] px-3 py-2.5 text-slate-600">{k.definisi}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-center">
                    <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700")} title="Detail" aria-label={`Detail ${k.kode}`} onClick={() => nav(`${DASAR}/${k.id}`)}><Eye className="size-4" /></button>
                    <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50 hover:text-utama-700")} title="Edit" aria-label={`Edit ${k.kode}`} onClick={() => nav(`${DASAR}/${k.id}/ubah`)}><Pencil className="size-4" /></button>
                    <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50 hover:text-red-700")} title="Hapus" aria-label={`Hapus ${k.kode}`} onClick={() => { setGalat(null); setHapus(k); }}><Trash2 className="size-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Kartu>
      )}
      {hapus && (
        <Konfirmasi buka bahaya judul="Hapus kategori secara permanen?" teksYa="Ya, hapus" teksBatal="Batal" memuat={memuat} galat={galat}
          batal={() => setHapus(null)} ya={yaHapus}
          pesan="Kategori beserta Kategori Histori-nya dihapus dari database dan tidak dapat dikembalikan. Hasil review lama tidak berubah karena menyimpan salinan kategori yang dipakai."
          baris={[["Kode", hapus.kode], ["Kategori", hapus.nama],
            ["Kategori Histori", jumlahHistori.data ? `${jumlahHistori.data.length} versi` : "…"]]} />
      )}
    </div>
  );
}

/** Tambah (`/kelola/kategori/tambah`) atau Edit (`/kelola/kategori/:id/ubah`); sebelum disimpan tampil pop-up periksa kembali. */
export function KategoriForm({ mode }: { mode: "tambah" | "ubah" }) {
  const { id } = useParams();
  const q = useQuery({ ...kueri, enabled: mode === "ubah" });
  if (mode === "tambah") return <IsiForm />;
  if (q.isLoading) return <Memuat />;
  const k = q.data?.item.find((x) => x.id === id);
  return k ? <IsiForm key={k.id} k={k} /> : <Kosong>Kategori tidak ditemukan.</Kosong>;
}

function IsiForm({ k }: { k?: ItemKategori }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  // Status hanya diatur saat Edit (PRD C7); kategori baru selalu Aktif.
  const awal = { kode: k?.kode ?? "", nama: k?.nama ?? "", definisi: k?.definisi ?? "", aktif: k?.aktif ?? true };
  const [n, setN] = useState(awal);
  const set = <K extends keyof typeof n>(kunci: K, v: (typeof n)[K]) => setN({ ...n, [kunci]: v });
  const [periksa, setPeriksa] = useState(false);
  const [memuat, setMemuat] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);
  const isi = { ...n, kode: n.kode.trim().toUpperCase(), nama: n.nama.trim(), definisi: n.definisi.trim() };

  const cek = (e: FormEvent) => { e.preventDefault(); setGalat(null); setPeriksa(true); };
  const kirim = async () => {
    setMemuat(true);
    try {
      if (k) await api.put(`${ENDPOINT}/${k.id}`, isi); else await api.post(ENDPOINT, isi);
      await qc.invalidateQueries({ queryKey: [ENDPOINT] });
      nav(DASAR);
    } catch (err) { setGalat((err as Error).message); setPeriksa(false); }
    finally { setMemuat(false); }
  };

  return (
    <div className="max-w-3xl">
      <Kembali />
      <Judul judul={k ? `Edit Kategori ${k.kode}` : "Tambah Kategori"}
        sub="Perubahan dipakai AI mulai review berikutnya; review yang sudah berjalan tidak terpengaruh." />
      <Kartu className="p-5">
        <form className="space-y-4" onSubmit={cek}>
          {galat && <Peringatan>{galat}</Peringatan>}
          <Kolom label="Kode" wajib><Input required maxLength={20} placeholder="mis. K5" value={n.kode} onChange={(e) => set("kode", e.target.value)} /></Kolom>
          <Kolom label="Kategori" wajib><Input required maxLength={255} placeholder="mis. RO Wajib" value={n.nama} onChange={(e) => set("nama", e.target.value)} /></Kolom>
          <Kolom label="Deskripsi" wajib petunjuk="Tuliskan sejelas mungkin; AI menentukan kategori berdasarkan deskripsi ini.">
            <AreaTeks required rows={5} value={n.definisi} onChange={(e) => set("definisi", e.target.value)} />
          </Kolom>
          {k && (
            <div className="space-y-1.5">
              <span className="text-sm font-medium text-slate-700">Status</span>
              <div><Saklar aktif={n.aktif} ubah={(v) => set("aktif", v)} label="Status kategori" /></div>
              <span className="block text-xs text-slate-500">Hanya kategori Aktif yang dipakai AI pada review berikutnya.</span>
            </div>
          )}
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
            {!k && <Tombol type="button" varian="sekunder" onClick={() => setN(awal)}>Reset</Tombol>}
            <Tombol type="submit">Simpan</Tombol>
          </div>
        </form>
      </Kartu>
      <Konfirmasi buka={periksa} batal={() => setPeriksa(false)} ya={kirim} memuat={memuat} baris={[
        ["Kode", isi.kode], ["Kategori", isi.nama], ["Deskripsi", <span className="whitespace-pre-line">{isi.definisi}</span>],
        ...(k ? [["Status", isi.aktif ? "Aktif" : "Nonaktif"] as [string, string]] : [])]} />
    </div>
  );
}

/** Detail (`/kelola/kategori/:id`): isi terbaru + Kategori Histori (versi sebelum perubahan terakhir, terbaru dulu). */
export function KategoriDetail() {
  const { id } = useParams();
  const q = useQuery(kueri);
  const r = useQuery({ ...riwayat(id!), enabled: !!q.data?.item.some((x) => x.id === id) });
  if (q.isLoading) return <Memuat />;
  const k = q.data?.item.find((x) => x.id === id);
  if (!k) return <Kosong>Kategori tidak ditemukan.</Kosong>;
  return (
    <div className="w-full space-y-4">
      <div>
        <Kembali teks="Kategori" />
        <Judul judul={`Detail Kategori ${k.kode}`} sub={k.nama} />
      </div>
      <Kartu className="space-y-5 p-5">
        <Ringkasan baris={[
          ["Kode", k.kode], ["Kategori", k.nama], ["Deskripsi", <span className="whitespace-pre-line">{k.definisi}</span>],
          ["Status", <LencanaAktif aktif={k.aktif} />], ["Tanggal Input", waktuAngka(k.diubah_at)], ["Diinput Oleh", k.diubah_oleh ?? "Sistem"],
        ]} />
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Kategori Histori</h2>
          {/* kategori_histori hanya berisi versi sebelum tiap perubahan; versi terkini tampil di atas. */}
          {r.isLoading ? <Memuat /> : r.error ? <Peringatan>{(r.error as Error).message}</Peringatan> : r.data!.length === 0 ? <Kosong>Belum ada perubahan sebelumnya.</Kosong> : (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full min-w-[56rem] text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-500">
                  <tr>{["Tanggal Input", "Diinput Oleh", "Kode", "Kategori", "Deskripsi", "Status"].map((h) => (
                    <th key={h} scope="col" className="whitespace-nowrap px-3 py-2 text-center">{h}</th>))}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">{r.data!.map((h) => (
                  <tr key={h.id} className="align-middle">
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-500">{waktuAngka(h.diubah_at)}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-700">{h.diubah_oleh ?? "Sistem"}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{h.kode}</td>
                    <td className="min-w-[10rem] px-3 py-2.5 text-slate-800">{h.nama}</td>
                    <td className="min-w-[20rem] whitespace-pre-line px-3 py-2.5 text-slate-700">{h.definisi}</td>
                    <td className="px-3 py-2.5 text-center"><LencanaAktif aktif={h.aktif} /></td>
                  </tr>))}</tbody>
              </table>
            </div>
          )}
        </div>
      </Kartu>
    </div>
  );
}
