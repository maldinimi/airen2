/** Riwayat usulan (A7): timeline revisi & review + perbandingan checklist antar-revisi. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArchiveRestore, ArrowLeft, Check, Minus, X } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AksiUsulan } from "../components/Usulan";
import { waktu } from "../format";
import type { BarisUsulan, Dok, KategoriRingkas, StatusRevisi } from "../types";
import { Judul, Kartu, Lencana, LencanaKategori, LencanaLabel, LencanaStatus, Memuat, Peringatan, Tombol, cx } from "../ui";

type ReviewRingkas = { id: string; status: string; trace_id: string; error_pesan: string | null; dibuat_at: string; selesai_at: string | null;
  label_ai: string | null; label_final: string | null; kategori_final: KategoriRingkas | null; difinalkan_oleh: string | null;
  difinalkan_at: string | null; diajukan_oleh: string };
type DataRiwayat = {
  usulan: BarisUsulan;
  revisi: { id: string; nomor: number; status: StatusRevisi; dibuat_at: string; dibuat_oleh: string; tor: Dok; rab: Dok; review: ReviewRingkas[] }[];
  perbandingan: { kolom: { revisi_nomor: number; review_id: string; final: boolean }[];
    baris: { kode: string; judul: string; berbeda_versi: boolean; nilai: Record<string, boolean | null> }[] };
};

export default function Riwayat() {
  const { id } = useParams();
  const { punya } = useAuth();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["riwayat", id], queryFn: () => api.get<DataRiwayat>(`/api/usulan/${id}/riwayat`) });
  const arsip = useMutation({ mutationFn: (a: boolean) => api.post(`/api/usulan/${id}/arsip`, { arsip: a }),
    onSuccess: () => qc.invalidateQueries(), onError: (e) => alert((e as Error).message) });
  if (q.isLoading) return <Memuat />;
  if (q.error || !q.data) return <Peringatan>{(q.error as Error)?.message}</Peringatan>;
  const { usulan: u, revisi, perbandingan } = q.data;
  const bolehArsip = (u.boleh_kelola || punya("ADMIN")) && u.pernah_direview;

  return (
    <div className="space-y-6">
      <Link to="/usulan" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />Usulan</Link>
      <Judul judul={`Riwayat · ${u.kode_ro}`} sub={`${u.nama_ro} · ${u.satker.nama} · TA ${u.tahun_anggaran}`}
        aksi={<>
          <AksiUsulan u={u} />
          {bolehArsip && <Tombol varian="sekunder" kecil memuat={arsip.isPending} onClick={() => arsip.mutate(!u.diarsipkan)}>
            {u.diarsipkan ? <><ArchiveRestore className="size-4" />Keluarkan dari arsip</> : <><Archive className="size-4" />Arsipkan</>}</Tombol>}
        </>} />

      <section>
        <h2 className="mb-3 font-semibold text-slate-900">Perbandingan checklist antar-revisi</h2>
        {perbandingan.kolom.length === 0 ? <p className="text-sm text-slate-500">Belum ada review yang selesai.</p> : (
          <Kartu className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr><th className="px-3 py-2 text-left">Item</th>{perbandingan.kolom.map((k) => (
                  <th key={k.review_id} className="px-3 py-2 text-center">Rev. {k.revisi_nomor}<div className="font-normal">{k.final ? "final" : "AI"}</div></th>))}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {perbandingan.baris.map((b) => (
                  <tr key={b.kode}>
                    <td className="px-3 py-2"><span className="font-medium">{b.kode}</span> {b.judul}
                      {b.berbeda_versi && <Lencana className="ml-2 bg-amber-50 text-amber-800 ring-amber-200" title="Isi item berbeda antar versi checklist">berbeda versi</Lencana>}</td>
                    {perbandingan.kolom.map((k, i) => {
                      const v = b.nilai[k.review_id];
                      const sebelum = i > 0 ? b.nilai[perbandingan.kolom[i - 1].review_id] : undefined;
                      const naik = sebelum === false && v === true, turun = sebelum === true && v === false;
                      return (
                        <td key={k.review_id} className={cx("px-3 py-2 text-center", naik && "bg-emerald-100", turun && "bg-red-100")}
                          title={naik ? "Berubah: tidak terpenuhi → terpenuhi" : turun ? "Berubah: terpenuhi → tidak terpenuhi" : undefined}>
                          {v === true ? <Check className="mx-auto size-4 text-emerald-600" aria-label="Terpenuhi" />
                            : v === false ? <X className="mx-auto size-4 text-red-600" aria-label="Tidak terpenuhi" />
                            : <Minus className="mx-auto size-4 text-slate-300" aria-label="Tidak dinilai" />}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Kartu>
        )}
      </section>

      <section>
        <h2 className="mb-3 font-semibold text-slate-900">Timeline revisi & review</h2>
        <ol className="relative space-y-4 border-l-2 border-slate-200 pl-6">
          {[...revisi].reverse().map((r) => (
            <li key={r.id} className="relative">
              <span className="absolute -left-[33px] top-1 size-4 rounded-full border-2 border-white bg-utama-600 ring-2 ring-utama-100" />
              <Kartu className="space-y-3 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">Revisi {r.nomor}</span><LencanaStatus status={r.status} />
                  <span className="text-xs text-slate-500">{waktu(r.dibuat_at)} · {r.dibuat_oleh}</span>
                </div>
                <div className="grid gap-1 text-sm sm:grid-cols-2">
                  {(["tor", "rab"] as const).map((d) => (
                    <div key={d}>{d.toUpperCase()}: <Link className="text-utama-600 hover:underline" to={`/pdf/${r[d].file_id}?judul=${encodeURIComponent(`${d.toUpperCase()} — ${r[d].nama}`)}`}>{r[d].nama}</Link>
                      {r.nomor > 1 && <span className="ml-1 text-xs text-slate-500">{r[d].diganti ? "(diganti)" : `(terbawa)`}</span>}</div>
                  ))}
                </div>
                {r.review.map((v) => (
                  <div key={v.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs text-slate-500">Review diajukan {waktu(v.dibuat_at)} oleh {v.diajukan_oleh}</span>
                      {v.status === "SELESAI" && <Link to={`/review/${v.id}`} className="ml-auto text-xs font-medium text-utama-600 hover:underline">Buka hasil</Link>}
                    </div>
                    {v.status === "GAGAL" && <p className="text-red-700">Gagal: {v.error_pesan}</p>}
                    {v.status === "SELESAI" && (
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        {v.label_final ? <>Final: <LencanaLabel label={v.label_final} /> <LencanaKategori k={v.kategori_final} />
                          <span className="text-xs text-slate-500">oleh {v.difinalkan_oleh}, {waktu(v.difinalkan_at)}</span></>
                          : <span className="text-xs text-amber-700">Menunggu verifikasi reviewer</span>}
                      </div>
                    )}
                    {(v.status === "ANTRE" || v.status === "DIPROSES") && <p className="text-blue-700">Sedang diproses AI…</p>}
                  </div>
                ))}
              </Kartu>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
