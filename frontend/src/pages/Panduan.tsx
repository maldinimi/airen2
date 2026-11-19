/** Panduan (Modul D): Pengusul & Reviewer dapat membaca; Reviewer mengunggah, mengubah (versi baru), mengaktifkan/menonaktifkan, menghapus. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, FileText, ListOrdered, Pencil, RotateCcw, Trash2, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import AturUrutan from "../components/AturUrutan";
import { TOMBOL_IKON, usePesanSukses } from "../components/Kelola";
import { FormFilter, type NilaiFilter, OPSI_STATUS, Paginasi, ThUrut, cocok, lolosJejak, lolosStatus, usePaginasi, useUrut, TabelGeser } from "../components/TabelData";
import { waktuAngka } from "../format";
import type { Panduan, VersiPanduan } from "../types";
import { Judul, Kartu, Konfirmasi, Kosong, Lencana, Memuat, Peringatan, Ringkasan, TanggalJam, Tombol, cx } from "../ui";

// Tombol ikon aksi tabel — sama dengan Kelola Checklist.
const tombol = TOMBOL_IKON;

// Dipakai daftar & detail: muat ulang tiap 5 detik selama ada file yang masih Antre/Diproses.
const kueriPanduan = {
  queryKey: ["panduan"], queryFn: () => api.get<Panduan[]>("/api/panduan"),
  refetchInterval: (x: { state: { data?: Panduan[] } }) => (x.state.data?.some((p) => ["BELUM", "DIPROSES"].includes(p.terkini.status_proses)) ? 5000 : false),
};

export default function PanduanPage() {
  const { punya } = useAuth();
  const kelola = punya("REVIEWER");  // Reviewer mengelola; Pengusul hanya melihat
  const qc = useQueryClient();
  const nav = useNavigate();
  const q = useQuery(kueriPanduan);
  const [f, setF] = useState<NilaiFilter>({});
  const semua = q.data ?? [];
  // Satu filter per kolom tabel (urut kolom).
  const lolos = useMemo(() => semua.filter((p) => cocok(f.cari, p.terkini.judul) && cocok(f.dokumen, p.terkini.nama_file)
    && cocok(f.deskripsi, p.terkini.deskripsi) && lolosStatus(f.status, p.aktif)
    && lolosJejak(f, p)), [semua, f]);
  // Default = urutan yang diatur Reviewer (no_urut dari server); klik judul kolom mengurutkan tampilan saja.
  const { baris, urut, klik } = useUrut<Panduan, "judul" | "dokumen" | "deskripsi" | "aktif" | "oleh" | "tanggal">(lolos, {
    judul: (p) => p.terkini.judul, dokumen: (p) => p.terkini.nama_file, deskripsi: (p) => p.terkini.deskripsi ?? "", aktif: (p) => +!p.aktif, oleh: (p) => p.diubah_oleh ?? "", tanggal: (p) => p.diubah_at,
  });
  // Paginasi di browser seperti Satuan Kerja & Master RO (bawaan 20 baris); kembali ke halaman 1 setiap filter/urutan berubah.
  const pg = usePaginasi(baris, [f, urut], 20);
  const segarkan = () => qc.invalidateQueries({ queryKey: ["panduan"] });
  const [dihapus, setDihapus] = useState<Panduan | null>(null);
  // Gagal (mis. 409 dipakai review berjalan) → pesan tampil di pop-up konfirmasi.
  const hapus = useMutation({ mutationFn: (id: string) => api.del(`/api/panduan/${id}`), onSuccess: () => { setDihapus(null); segarkan(); } });
  const ulang = useMutation({ mutationFn: (id: string) => api.post(`/api/panduan/${id}/proses-ulang`), onSuccess: segarkan, onError: (e) => alert((e as Error).message) });
  // Atur Urutan seperti Checklist & Kategori (khusus Reviewer); disimpan lewat PUT /api/panduan/urutan.
  const [atur, setAtur] = useState(false);
  const [sukses, setSukses] = usePesanSukses();

  if (atur && kelola) return <AturUrutan judul="Atur Urutan Acuan" endpoint="/api/panduan"
    item={semua.map((p) => ({ id: p.id, judul: p.judul }))} tutup={() => setAtur(false)}
    disimpan={() => { segarkan(); setSukses("Urutan berhasil disimpan."); setAtur(false); }} />;

  return (
    <div>
      <Judul judul="Acuan"
        aksi={kelola && <>
          <Tombol varian="sekunder" onClick={() => setAtur(true)} disabled={semua.length < 2}><ListOrdered className="size-4" />Atur Urutan</Tombol>
          <Tombol onClick={() => nav("/panduan/unggah")}><Upload className="size-4" />Unggah Acuan</Tombol>
        </>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {!!q.data?.length && (
        <FormFilter judul="Acuan" nilai={f} terapkan={setF} bidang={[
          { jenis: "teks", kunci: "cari", label: "Nama Acuan", placeholder: "Cari nama acuan…" },
          { jenis: "teks", kunci: "dokumen", label: "Nama Dokumen", placeholder: "Cari nama dokumen, mis. .pdf…" },
          { jenis: "teks", kunci: "deskripsi", label: "Deskripsi", placeholder: "Cari deskripsi…" },
          { jenis: "pilih", kunci: "status", label: "Status", semua: "Semua Status", opsi: OPSI_STATUS, kecil: true },
          { jenis: "teks", kunci: "oleh", label: "Diinput Oleh", placeholder: "Cari nama penginput…" },
          { jenis: "tanggal", kunci: "tanggal", label: "Tanggal Input", kecil: true },
        ]} />
      )}
      {q.isLoading ? <Memuat /> : !q.data?.length ? <Kosong>Belum ada acuan.</Kosong> : baris.length === 0 ? <Kosong>Tidak ada acuan yang cocok dengan filter.</Kosong> : (
        <Kartu><TabelGeser>
          {/* Gaya tabel mengikuti Kelola Checklist; semua kolom (judul & isi) rata tengah; kolom teks diberi lebar maksimum agar baris rapi. */}
          <table className="w-full min-w-[72rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700"><tr>
              <th scope="col" className="w-12 whitespace-nowrap px-3 py-2.5 text-center">No</th>
              <ThUrut label="Nama Acuan" kolom="judul" urut={urut} klik={klik} />
              <ThUrut label="Nama Dokumen" kolom="dokumen" urut={urut} klik={klik} />
              <ThUrut label="Deskripsi" kolom="deskripsi" urut={urut} klik={klik} />
              <ThUrut label="Status" kolom="aktif" urut={urut} klik={klik} />
              <ThUrut label="Diinput Oleh" kolom="oleh" urut={urut} klik={klik} />
              <ThUrut label="Tanggal Input" kolom="tanggal" urut={urut} klik={klik} />
              <th scope="col" className="whitespace-nowrap px-3 py-2.5 text-center">Aksi</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">{pg.tampil.map((p, i) => {
              const v = p.terkini;
              return (
                <tr key={p.id} className="align-middle transition-colors hover:bg-slate-50">
                  <td className="px-3 py-2.5 text-center text-slate-500">{pg.awal + i + 1}</td>
                  <td className="min-w-[14rem] max-w-xs px-3 py-2.5 text-center">
                    <Link to={pdf(v)} className="font-medium text-utama-700 hover:underline">{v.judul}</Link>
                    {/* Keterangan file (status proses · nama file · halaman · versi) sengaja tidak ditampilkan. Pesan gagal
                        tetap untuk Reviewer agar tahu kapan tombol Proses ulang perlu dipakai. */}
                    {kelola && v.status_proses === "GAGAL" && <p className="mt-1 text-xs text-red-700">{v.pesan_gagal ?? "Pemrosesan gagal."}</p>}
                  </td>
                  {/* Nama Dokumen = nama file PDF yang diunggah (versi terkini). */}
                  <td className="min-w-[12rem] max-w-xs break-words px-3 py-2.5 text-center text-slate-600">{v.nama_file}</td>
                  {/* Deskripsi panjang dipotong 2 baris agar tinggi baris seragam; teks lengkap muncul saat kursor diarahkan dan di halaman detail. */}
                  <td className="min-w-[16rem] max-w-md px-3 py-2.5 text-center text-slate-600">
                    <p className="line-clamp-2" title={v.deskripsi ?? undefined}>{v.deskripsi ?? "—"}</p>
                  </td>
                  <td className="py-2.5 pl-5 pr-3 text-center"><LencanaAktif aktif={p.aktif} /></td>
                  <td className="min-w-[9rem] whitespace-nowrap px-3 py-2.5 text-center text-slate-600">{p.diubah_oleh ?? "Sistem"}</td>
                  <td className="min-w-[9.5rem] whitespace-nowrap py-2.5 pl-5 pr-3 text-center text-slate-600"><TanggalJam iso={p.diubah_at} /></td>
                  <td className="whitespace-nowrap px-3 py-2 text-center">
                    <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700")} title="Detail"
                      aria-label={`Detail ${v.judul}`} onClick={() => nav(`/panduan/${p.id}`)}><Eye className="size-4" /></button>
                    {kelola && <>
                      <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50 hover:text-utama-700")} title="Edit"
                        aria-label={`Edit ${v.judul}`} onClick={() => nav(`/panduan/${p.id}/ubah`)}><Pencil className="size-4" /></button>
                      {v.status_proses === "GAGAL" && <button type="button" className={cx(tombol, "text-slate-500 hover:bg-slate-100 hover:text-slate-800")} title="Proses ulang"
                        aria-label={`Proses ulang ${v.judul}`} onClick={() => ulang.mutate(p.id)}><RotateCcw className="size-4" /></button>}
                      <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50 hover:text-red-700")} title="Hapus"
                        aria-label={`Hapus ${v.judul}`} onClick={() => { hapus.reset(); setDihapus(p); }}><Trash2 className="size-4" /></button>
                    </>}
                  </td>
                </tr>
              );
            })}</tbody>
          </table></TabelGeser>
        </Kartu>
      )}
      {baris.length > 0 && <Paginasi {...pg} />}
      {dihapus && (
        <Konfirmasi bahaya buka judul="Hapus acuan secara permanen?" teksYa="Ya, hapus" teksBatal="Batal"
          baris={[["Nama Acuan", dihapus.judul], ["File", dihapus.terkini.nama_file], ["Status", dihapus.aktif ? "Aktif" : "Nonaktif"],
            ["Acuan Histori", dihapus.versi.length > 1 ? `${dihapus.versi.length - 1} versi` : "—"]]}
          pesan="Acuan beserta Acuan Histori dan file PDF-nya dihapus dari database dan tidak dapat dikembalikan. Hasil review lama kehilangan rujukan ke acuan ini."
          galat={hapus.error?.message} memuat={hapus.isPending} batal={() => setDihapus(null)} ya={() => hapus.mutate(dihapus.id)} />
      )}
    </div>
  );
}

const pdf = (x: VersiPanduan) => `/pdf/${x.file_id}?judul=${encodeURIComponent(x.judul)}`;

const LencanaAktif = ({ aktif }: { aktif: boolean }) =>
  <Lencana className={aktif ? "bg-emerald-50 text-emerald-700 ring-emerald-300" : "bg-red-50 text-red-700 ring-red-200"}>{aktif ? "Aktif" : "Nonaktif"}</Lencana>;

/** Halaman detail panduan: data terkini (+ tombol Lihat PDF) dan Panduan Histori. Semua pengguna (D3). */
export function PanduanDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  // Memakai daftar panduan (kunci cache sama dengan halaman Panduan) — tidak perlu endpoint per panduan.
  const q = useQuery(kueriPanduan);
  if (q.isLoading) return <Memuat />;
  const p = q.data?.find((x) => x.id === id);
  if (!p) return <Kosong>Acuan tidak ditemukan.</Kosong>;
  const v = p.terkini;
  return (
    <div className="w-full space-y-4">
      <div>
        <Link to="/panduan" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />Acuan</Link>
        <Judul judul="Detail Acuan" />
      </div>
      <Kartu className="space-y-5 p-5">
        {/* Urutan, label, dan nilai disamakan dengan kolom tabel Panduan. */}
        <Ringkasan baris={[
          ["Nama Acuan", v.judul],
          ["Nama Dokumen", v.nama_file],
          ["PDF", <Tombol kecil varian="sekunder" onClick={() => nav(pdf(v))}><FileText className="size-4" />Lihat PDF</Tombol>],
          ["Deskripsi", v.deskripsi ?? "—"],
          ["Status", <LencanaAktif aktif={p.aktif} />],
          ["Diinput Oleh", p.diubah_oleh ?? "Sistem"],
          ["Tanggal Input", waktuAngka(p.diubah_at)],
        ]} />
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Acuan Histori</h2>
          {p.versi.length < 2 ? <p className="text-sm text-slate-500">Belum ada perubahan.</p> : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500"><tr>
                {["Tanggal Input", "Diinput Oleh", "Status", "Nama Acuan", "Deskripsi"].map((h) => <th key={h} className="px-3 py-2 text-center">{h}</th>)}
              </tr></thead>
              {/* versi[0] = terkini, sudah tampil di bagian atas; riwayat hanya versi sebelumnya. */}
              <tbody className="divide-y divide-slate-100">{p.versi.slice(1).map((x) => (
                <tr key={x.id} className="align-top">
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500"><TanggalJam iso={x.dibuat_at} /></td>
                  <td className="px-3 py-2">{x.dibuat_oleh ?? "sistem"}</td>
                  <td className="px-3 py-2"><LencanaAktif aktif={x.aktif} /></td>
                  <td className="px-3 py-2">{x.judul}</td>
                  <td className="px-3 py-2 text-slate-600">{x.deskripsi ?? "—"}</td>
                </tr>))}</tbody>
            </table>
          </div>)}
        </div>
      </Kartu>
    </div>
  );
}
