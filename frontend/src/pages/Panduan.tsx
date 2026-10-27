/** Panduan (Modul D): semua pengguna dapat membaca; Admin mengunggah, mengubah (versi baru), mengaktifkan/menonaktifkan, menghapus. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, FileText, Loader2, Pencil, RotateCcw, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { waktu } from "../format";
import type { Panduan, VersiPanduan } from "../types";
import { Judul, Kartu, KepalaStatus, Konfirmasi, Kosong, Lencana, Memuat, Ringkasan, Tombol, type UrutStatus, urutkanStatus } from "../ui";

const STATUS: Record<VersiPanduan["status_proses"], [string, string]> = {
  BELUM: ["Antre", "bg-blue-50 text-blue-700 ring-blue-200"], DIPROSES: ["Diproses", "bg-blue-50 text-blue-700 ring-blue-200"],
  SIAP: ["Siap", "bg-emerald-50 text-emerald-700 ring-emerald-300"], GAGAL: ["Gagal", "bg-red-100 text-red-900 ring-red-300"],
};

// Dipakai daftar & detail: muat ulang tiap 5 detik selama ada file yang masih Antre/Diproses.
const kueriPanduan = {
  queryKey: ["panduan"], queryFn: () => api.get<Panduan[]>("/api/panduan"),
  refetchInterval: (x: { state: { data?: Panduan[] } }) => (x.state.data?.some((p) => ["BELUM", "DIPROSES"].includes(p.terkini.status_proses)) ? 5000 : false),
};

export default function PanduanPage() {
  const { punya } = useAuth();
  const admin = punya("ADMIN");
  const qc = useQueryClient();
  const nav = useNavigate();
  const q = useQuery(kueriPanduan);
  const [urut, setUrut] = useState<UrutStatus>("");
  const baris = urutkanStatus(q.data ?? [], urut);  // Default = urut nama dari server
  const segarkan = () => qc.invalidateQueries({ queryKey: ["panduan"] });
  const [dihapus, setDihapus] = useState<Panduan | null>(null);
  // Gagal (mis. 409 dipakai review berjalan) → pesan tampil di pop-up konfirmasi.
  const hapus = useMutation({ mutationFn: (id: string) => api.del(`/api/panduan/${id}`), onSuccess: () => { setDihapus(null); segarkan(); } });
  const ulang = useMutation({ mutationFn: (id: string) => api.post(`/api/panduan/${id}/proses-ulang`), onSuccess: segarkan, onError: (e) => alert((e as Error).message) });

  return (
    <div>
      <Judul judul="Panduan" sub="Peraturan, kebijakan, dan standar yang menjadi acuan review AI. Hanya panduan Aktif yang berstatus Siap yang dipakai review."
        aksi={admin && <Tombol onClick={() => nav("/panduan/unggah")}><Upload className="size-4" />Unggah Panduan</Tombol>} />
      {q.isLoading ? <Memuat /> : !q.data?.length ? <Kosong>Belum ada panduan.</Kosong> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>
              {["No", "Nama Acuan", "Deskripsi", "Status", "Diinput Oleh", "Tanggal Input", "Aksi"].map((h) => h === "Status"
                ? <KepalaStatus key={h} urut={urut} ubah={setUrut} className="px-3 py-2 text-center" />
                : <th key={h} className="px-3 py-2 text-center">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y divide-slate-100">{baris.map((p, i) => {
              const v = p.terkini;
              return (
                <tr key={p.id} className="align-top">
                  <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                  <td className="min-w-56 space-y-1 px-3 py-2">
                    <Link to={pdf(v)} className="font-medium text-utama-700 hover:underline">{v.judul}</Link>
                    <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                      <LencanaProses v={v} />{v.nama_file} · {v.jumlah_halaman} hlm · v{v.nomor}
                    </div>
                    {v.status_proses === "GAGAL" && <p className="text-xs text-red-700">{v.pesan_gagal ?? "Pemrosesan gagal."}</p>}
                  </td>
                  <td className="max-w-md px-3 py-2 text-slate-600">{v.deskripsi ?? "—"}</td>
                  <td className="px-3 py-2"><LencanaAktif aktif={p.aktif} /></td>
                  <td className="px-3 py-2">{p.diubah_oleh ?? "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">{waktu(p.diubah_at)}</td>
                  <td className="px-3 py-2">
                    <div className="flex justify-center gap-1">
                      <Tombol kecil varian="hantu" title="Lihat detail" aria-label={`Lihat detail ${v.judul}`} onClick={() => nav(`/panduan/${p.id}`)}>
                        <Eye className="size-4 text-emerald-600" /></Tombol>
                      {admin && <>
                        <Tombol kecil varian="hantu" title="Edit" aria-label={`Edit ${v.judul}`} onClick={() => nav(`/panduan/${p.id}/ubah`)}>
                          <Pencil className="size-4 text-blue-600" /></Tombol>
                        {v.status_proses === "GAGAL" && <Tombol kecil varian="hantu" title="Proses ulang" aria-label={`Proses ulang ${v.judul}`} onClick={() => ulang.mutate(p.id)}>
                          <RotateCcw className="size-4" /></Tombol>}
                        <Tombol kecil varian="hantu" title="Hapus" aria-label={`Hapus ${v.judul}`}
                          onClick={() => { hapus.reset(); setDihapus(p); }}>
                          <Trash2 className="size-4 text-red-600" /></Tombol>
                      </>}
                    </div>
                  </td>
                </tr>
              );
            })}</tbody>
          </table>
        </Kartu>
      )}
      {dihapus && (
        <Konfirmasi bahaya buka judul="Hapus panduan secara permanen?" teksYa="Ya, hapus" teksBatal="Batal"
          baris={[["Nama Acuan", dihapus.judul], ["File", dihapus.terkini.nama_file], ["Status", dihapus.aktif ? "Aktif" : "Nonaktif"],
            ["Panduan Histori", dihapus.versi.length > 1 ? `${dihapus.versi.length - 1} versi` : "—"]]}
          pesan="Panduan beserta Panduan Histori dan file PDF-nya dihapus dari database dan tidak dapat dikembalikan. Hasil review lama kehilangan rujukan ke panduan ini."
          galat={hapus.error?.message} memuat={hapus.isPending} batal={() => setDihapus(null)} ya={() => hapus.mutate(dihapus.id)} />
      )}
    </div>
  );
}

const pdf = (x: VersiPanduan) => `/pdf/${x.file_id}?judul=${encodeURIComponent(x.judul)}`;

function LencanaProses({ v }: { v: VersiPanduan }) {
  const [nama, warna] = STATUS[v.status_proses];
  return <Lencana className={warna}>{(v.status_proses === "DIPROSES" || v.status_proses === "BELUM") && <Loader2 className="size-3 animate-spin" />}{nama}</Lencana>;
}

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
  if (!p) return <Kosong>Panduan tidak ditemukan.</Kosong>;
  const v = p.terkini, awal = p.versi[p.versi.length - 1]; // versi pertama = saat diunggah
  return (
    <div className="max-w-3xl space-y-6">
      <Link to="/panduan" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />Panduan</Link>
      <Judul judul="Detail Panduan" sub={v.judul} />
      <Kartu className="space-y-5 p-5">
        <Ringkasan baris={[
          ["Nama Acuan", v.judul],
          ["Deskripsi", v.deskripsi ?? "—"],
          ["Status", <LencanaAktif aktif={p.aktif} />],
          ["Pemrosesan", <><LencanaProses v={v} />{v.status_proses === "GAGAL" && <span className="ml-2 text-xs text-red-700">{v.pesan_gagal ?? "Pemrosesan gagal."}</span>}</>],
          ["File", `${v.nama_file} · ${v.jumlah_halaman} hlm`],
          ["PDF", <Tombol kecil varian="sekunder" onClick={() => nav(pdf(v))}><FileText className="size-4" />Lihat PDF</Tombol>],
          ["Tanggal Input", waktu(awal.dibuat_at)],
          ["Diinput Oleh", awal.dibuat_oleh ?? "—"],
        ]} />
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-700">Panduan Histori</h2>
          {p.versi.length < 2 ? <p className="text-sm text-slate-500">Belum ada perubahan.</p> : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500"><tr>
                {["Tanggal Input", "Diinput Oleh", "Status", "Nama Acuan", "Deskripsi"].map((h) => <th key={h} className="px-3 py-2 text-center">{h}</th>)}
              </tr></thead>
              {/* versi[0] = terkini, sudah tampil di bagian atas; riwayat hanya versi sebelumnya. */}
              <tbody className="divide-y divide-slate-100">{p.versi.slice(1).map((x) => (
                <tr key={x.id} className="align-top">
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">{waktu(x.dibuat_at)}</td>
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
