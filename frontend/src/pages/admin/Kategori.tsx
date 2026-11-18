/** Kelola Kategori (Modul C): tabel kategori (urutan diatur Reviewer lewat Atur Urutan); tambah/edit/detail di halaman tersendiri, hapus permanen. Isi terbaru ada
 *  di tabel kategori, isi sebelum tiap perubahan dicatat backend di kategori_histori. Review menyimpan salinan kategori yang
 *  dipakai, sehingga edit/hapus tidak mengubah review lama (C4). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, ListOrdered, Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import AturUrutan from "../../components/AturUrutan";
import { TOMBOL_IKON } from "../../components/Kelola";
import { FormFilter, type NilaiFilter, OPSI_STATUS, Paginasi, ThUrut, cocok, lolosJejak, lolosStatus, usePaginasi, useUrut } from "../../components/TabelData";
import { waktuAngka } from "../../format";
import type { ItemKategori } from "../../types";
import { AreaTeks, Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Lencana, Memuat, Peringatan, Ringkasan, Saklar, TanggalJam, Tombol, cx } from "../../ui";

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
  // Reviewer mengelola; Pengusul membuka halaman ini hanya untuk melihat (backend menolak perubahan dari non-Reviewer).
  const kelola = useAuth().punya("REVIEWER");
  const qc = useQueryClient();
  const q = useQuery(kueri);
  const [hapus, setHapus] = useState<ItemKategori | null>(null);
  const [memuat, setMemuat] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);
  const jumlahHistori = useQuery({ ...riwayat(hapus?.id ?? ""), enabled: !!hapus });
  const [atur, setAtur] = useState(false);
  const [sukses, setSukses] = useState<string | null>(null);
  const [f, setF] = useState<NilaiFilter>({});
  useEffect(() => { if (!sukses) return; const t = setTimeout(() => setSukses(null), 4000); return () => clearTimeout(t); }, [sukses]);
  const item = q.data?.item ?? [];
  // Default = urutan yang diatur Reviewer (no_urut dari server); klik judul kolom mengurutkan tampilan saja.
  // Satu filter per kolom tabel (urut kolom); penginput kosong tampil "Sistem" seperti di tabel.
  const lolos = useMemo(() => item.filter((k) => cocok(f.kode, k.kode) && cocok(f.cari, k.nama) && lolosStatus(f.status, k.aktif)
    && cocok(f.deskripsi, k.definisi) && lolosJejak(f, k)), [item, f]);
  const { baris, urut, klik } = useUrut<ItemKategori, "kode" | "nama" | "aktif" | "definisi" | "diubah_oleh" | "diubah_at">(lolos, {
    kode: (k) => k.kode, nama: (k) => k.nama, aktif: (k) => +!k.aktif, definisi: (k) => k.definisi,
    diubah_oleh: (k) => k.diubah_oleh ?? "Sistem", diubah_at: (k) => k.diubah_at,
  });
  // Paginasi di browser seperti Satuan Kerja & Master RO (bawaan 20 baris); kembali ke halaman 1 setiap filter/urutan berubah.
  const pg = usePaginasi(baris, [f, urut], 20);

  if (q.isLoading) return <Memuat />;
  if (q.error) return <Peringatan>{(q.error as Error).message}</Peringatan>;
  if (atur && kelola) return <AturUrutan judul="Atur Urutan Kategori" endpoint={ENDPOINT} item={item.map((k) => ({ id: k.id, kode: k.kode, judul: k.nama }))}
    tutup={() => setAtur(false)} disimpan={() => { setSukses("Urutan berhasil disimpan."); setAtur(false); }} />;

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
  const tombol = TOMBOL_IKON;

  return (
    <div className="w-full">
      <Judul judul="Kategori"
        aksi={kelola && <>
          <Tombol varian="sekunder" onClick={() => setAtur(true)} disabled={item.length < 2}><ListOrdered className="size-4" />Atur Urutan</Tombol>
          <Tombol onClick={() => nav(`${DASAR}/tambah`)}><Plus className="size-4" />Tambah Kategori</Tombol>
        </>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {item.length > 0 && (
        <FormFilter judul="Kategori" nilai={f} terapkan={setF} bidang={[
          { jenis: "teks", kunci: "kode", label: "Kode", placeholder: "Cari kode, mis. K1…" },
          { jenis: "teks", kunci: "cari", label: "Kategori", placeholder: "Cari kategori…" },
          { jenis: "pilih", kunci: "status", label: "Status", semua: "Semua Status", opsi: OPSI_STATUS, kecil: true },
          { jenis: "teks", kunci: "deskripsi", label: "Deskripsi", placeholder: "Cari deskripsi…" },
          { jenis: "teks", kunci: "oleh", label: "Diinput Oleh", placeholder: "Cari nama penginput…" },
          { jenis: "tanggal", kunci: "tanggal", label: "Tanggal Input", kecil: true },
        ]} />
      )}
      {item.length === 0 ? <Kosong>Belum ada kategori.</Kosong> : baris.length === 0 ? <Kosong>Tidak ada kategori yang cocok dengan filter.</Kosong> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full min-w-[72rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
              <tr>
                <ThUrut label="Kode" kolom="kode" urut={urut} klik={klik} />
                <ThUrut label="Kategori" kolom="nama" urut={urut} klik={klik} />
                <ThUrut label="Status" kolom="aktif" urut={urut} klik={klik} />
                <ThUrut label="Deskripsi" kolom="definisi" urut={urut} klik={klik} />
                {/* Diinput Oleh & Tanggal Input (tanggal + jam) sama dengan tabel Checklist. */}
                <ThUrut label="Diinput Oleh" kolom="diubah_oleh" urut={urut} klik={klik} />
                <ThUrut label="Tanggal Input" kolom="diubah_at" urut={urut} klik={klik} />
                <th scope="col" className="whitespace-nowrap px-3 py-2.5 text-center">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pg.tampil.map((k) => (
                <tr key={k.id} className="align-middle transition-colors hover:bg-slate-50">
                  <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{k.kode}</td>
                  <td className="min-w-[12rem] whitespace-nowrap py-2.5 pl-6 pr-3 text-left text-slate-900">{k.nama}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-center"><LencanaAktif aktif={k.aktif} /></td>
                  <td className="min-w-[24rem] px-3 py-2.5 text-justify text-slate-600">{k.definisi}</td>
                  <td className="min-w-[9rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600">{k.diubah_oleh ?? "Sistem"}</td>
                  <td className="min-w-[9.5rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600"><TanggalJam iso={k.diubah_at} /></td>
                  <td className="whitespace-nowrap px-3 py-2 text-center">
                    <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700")} title="Detail" aria-label={`Detail ${k.kode}`} onClick={() => nav(`${DASAR}/${k.id}`)}><Eye className="size-4" /></button>
                    {kelola && <>
                      <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50 hover:text-utama-700")} title="Edit" aria-label={`Edit ${k.kode}`} onClick={() => nav(`${DASAR}/${k.id}/ubah`)}><Pencil className="size-4" /></button>
                      <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50 hover:text-red-700")} title="Hapus" aria-label={`Hapus ${k.kode}`} onClick={() => { setGalat(null); setHapus(k); }}><Trash2 className="size-4" /></button>
                    </>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Kartu>
      )}
      {baris.length > 0 && <Paginasi {...pg} />}
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
    <div className="w-full">
      <Kembali />
      <Judul judul={k ? `Edit Kategori ${k.kode}` : "Tambah Kategori"} />
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
        <Judul judul={`Detail Kategori ${k.kode}`} />
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
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-500"><TanggalJam iso={h.diubah_at} /></td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-700">{h.diubah_oleh ?? "Sistem"}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center font-medium text-slate-900">{h.kode}</td>
                    <td className="min-w-[10rem] px-3 py-2.5 text-slate-800">{h.nama}</td>
                    <td className="min-w-[20rem] whitespace-pre-line px-3 py-2.5 text-justify text-slate-700">{h.definisi}</td>
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
