/** Detail usulan (`/usulan/:id`, desain.md §7 no. 36 & 38): parameter hierarki anggaran + Histori Dokumen per revisi (urut naik).
 *  Aksi per revisi → halaman Pemeriksaan: Reviewer "Review" bila menunggu verifikasi, Pengusul "Revisi" bila revisi
 *  terbaru Tidak Lolos (tombol Unggah Revisi ada di bawah halaman Pemeriksaan), selain itu ikon mata (Detail). */
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Eye, Pencil } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { InfoProses, TautanDokumen, bolehUbahDokumen } from "../components/Usulan";
import { waktuAngka } from "../format";
import type { BarisUsulan, Dok, StatusRevisi } from "../types";
import { Judul, Kartu, Kosong, LencanaStatus, Memuat, Peringatan, Ringkasan, TanggalJam, Tombol } from "../ui";

type Revisi = { id: string; nomor: number; status: StatusRevisi; dibuat_at: string; tor: Dok | null; rab: Dok | null;
  review: { id: string; status: string; difinalkan_at: string | null }[] };

export default function UsulanDetail() {
  const { id } = useParams();
  const { punya } = useAuth();
  const q = useQuery({
    queryKey: ["riwayat", id], queryFn: () => api.get<{ usulan: BarisUsulan; revisi: Revisi[] }>(`/api/usulan/${id}/riwayat`),
    refetchInterval: (x) => (x.state.data && ["ANTRE", "DIPROSES_AI"].includes(x.state.data.usulan.status) ? 5000 : false),
  });
  if (q.isLoading) return <Memuat />;
  if (q.error || !q.data) return <Peringatan>{(q.error as Error)?.message ?? "Usulan tidak ditemukan."}</Peringatan>;
  const { usulan: u, revisi } = q.data;
  const h = u.hierarki;
  const reviewer = punya("REVIEWER");

  const aksi = (r: Revisi, reviewId: string, terbaru: boolean) => {
    if (terbaru && reviewer && r.status === "MENUNGGU_VERIFIKASI")
      return <Link to={`/review/${reviewId}`}><Tombol kecil>Review</Tombol></Link>;
    if (terbaru && u.boleh_kelola && !u.diarsipkan && r.status === "TIDAK_LOLOS")
      return <Link to={`/review/${reviewId}`}><Tombol kecil>Revisi</Tombol></Link>;
    return (
      <Link to={`/review/${reviewId}`} title="Detail" aria-label={`Detail revisi ${r.nomor}`}
        className="inline-flex rounded-lg p-1.5 text-emerald-600 hover:bg-emerald-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
        <Eye className="size-4" /></Link>
    );
  };

  return (
    <div className="w-full space-y-4">
      <div>
        <Link to="/usulan" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />Usulan</Link>
        <Judul judul="Detail Usulan" sub={`${u.kode_ro} — ${u.nama_ro}`}
          aksi={bolehUbahDokumen(u) && <Link to={`/usulan/${u.id}/ubah`}><Tombol><Pencil className="size-4" />Edit</Tombol></Link>} />
      </div>
      <Kartu className="space-y-3 p-5">
        <h2 className="font-semibold text-slate-900">Parameter Hierarki Anggaran RKA-K/L</h2>
        <Ringkasan baris={[
          ["Satuan Kerja", u.satker.nama],
          ["Program", h ? `${h.program.kode} — ${h.program.nama}` : "—"],
          ["Kegiatan", h ? `${h.kegiatan.kode} — ${h.kegiatan.nama}` : "—"],
          ["Klasifikasi Rincian Output (KRO)", h ? `${h.kro.kode} — ${h.kro.nama}` : "—"],
          ["Rincian Output (RO)", `${u.kode_ro} — ${u.nama_ro}`],
          ["Kategori", u.kategori_usulan ? `${u.kategori_usulan.kode} — ${u.kategori_usulan.nama}` : "—"],
          ["Deskripsi Kategori", <span className="block whitespace-pre-line text-justify">{u.kategori_usulan?.deskripsi ?? "—"}</span>],
          ["Tanggal Pengajuan", <TanggalJam iso={u.dibuat_at} />],
        ]} />
      </Kartu>
      <Kartu className="space-y-3 p-5">
        <h2 className="font-semibold text-slate-900">Histori Dokumen</h2>
        {revisi.length === 0 ? <Kosong>Belum ada dokumen.</Kosong> : (<>
          {/* Layar kecil: kartu per revisi; md ke atas: tabel. */}
          <div className="space-y-3 md:hidden">{revisi.map((r) => {
            const rv = r.review[r.review.length - 1];
            const terbaru = r.nomor === u.revisi_nomor;
            return (
              <div key={r.id} className="space-y-2 rounded-lg border border-slate-200 p-3 text-sm">
                <div className="flex items-center justify-between gap-2"><span className="font-semibold">Revisi {r.nomor}</span><LencanaStatus status={r.status} /></div>
                {terbaru && <InfoProses p={u.proses} />}
                <TautanDokumen tor={r.tor} rab={r.rab} />
                <dl className="grid grid-cols-2 gap-1 text-xs text-slate-600">
                  <dt className="text-slate-500">Tanggal Pengajuan</dt><dd>{waktuAngka(r.dibuat_at)}</dd>
                  <dt className="text-slate-500">Tanggal Verifikasi</dt><dd>{waktuAngka(rv?.difinalkan_at)}</dd>
                </dl>
                {rv && <div className="flex justify-end">{aksi(r, rv.id, terbaru)}</div>}
              </div>
            );
          })}</div>
          <div className="hidden overflow-x-auto rounded-lg border border-slate-200 md:block">
            <table className="w-full min-w-[52rem] text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
                <tr>{["No", "Dokumen", "Tanggal Pengajuan", "Tanggal Verifikasi", "Status Verifikasi", "Aksi"].map((x) => (
                  <th key={x} scope="col" className={x === "Dokumen" ? "px-3 py-2 text-left" : "px-3 py-2 text-center"}>{x}</th>))}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">{revisi.map((r) => {
                const rv = r.review[r.review.length - 1];  // review terakhir revisi ini (review gagal boleh diulang)
                const terbaru = r.nomor === u.revisi_nomor;
                return (
                  <tr key={r.id} className="align-top">
                    <td className="px-3 py-2.5 text-center text-slate-500">{r.nomor}</td>
                    <td className="px-3 py-2.5"><TautanDokumen tor={r.tor} rab={r.rab} /></td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-600"><TanggalJam iso={r.dibuat_at} /></td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-center text-slate-600"><TanggalJam iso={rv?.difinalkan_at} /></td>
                    <td className="min-w-44 space-y-1.5 px-3 py-2.5 text-center"><LencanaStatus status={r.status} />{terbaru && <InfoProses p={u.proses} />}</td>
                    <td className="px-3 py-2 text-center">{rv ? aksi(r, rv.id, terbaru) : <span className="text-slate-400">—</span>}</td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        </>)}
      </Kartu>
    </div>
  );
}
