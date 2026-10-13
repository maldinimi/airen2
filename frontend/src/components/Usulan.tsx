/** Potongan UI untuk baris usulan: ringkasan checklist (A4), status proses, dan tombol aksi per role/status (A3). */
import * as Pop from "@radix-ui/react-popover";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, History, Send, Upload, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { BarisUsulan, Proses, RingkasChecklist } from "../types";
import { Lencana, Peringatan, Progres, Tombol, cx } from "../ui";

export function RingkasanChecklist({ c }: { c: RingkasChecklist | null }) {
  if (!c) return <span className="text-slate-400">—</span>;
  return (
    <Pop.Root>
      <Pop.Trigger className={cx("rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset hover:opacity-80",
        c.terpenuhi === c.total ? "bg-emerald-50 text-emerald-700 ring-emerald-300" : "bg-red-50 text-red-700 ring-red-300")}>
        {c.terpenuhi}/{c.total} terpenuhi
      </Pop.Trigger>
      <Pop.Portal>
        <Pop.Content sideOffset={6} className="z-50 w-80 rounded-xl border border-slate-200 bg-white p-3 shadow-xl">
          <div className="mb-2 text-xs font-medium text-slate-500">{c.final ? "Hasil final" : "Hasil AI — belum diverifikasi reviewer"}</div>
          <ul className="max-h-72 space-y-1.5 overflow-y-auto">
            {c.item.map((i) => (
              <li key={i.kode} className="flex gap-2 text-sm">
                {i.terpenuhi ? <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-label="Terpenuhi" />
                  : <X className="mt-0.5 size-4 shrink-0 text-red-600" aria-label="Tidak terpenuhi" />}
                <span><span className="font-medium">{i.kode}</span> {i.judul}</span>
              </li>
            ))}
          </ul>
          <Pop.Arrow className="fill-white" />
        </Pop.Content>
      </Pop.Portal>
    </Pop.Root>
  );
}

export function InfoProses({ p }: { p: Proses | null }) {
  if (!p) return null;
  if (p.status === "GAGAL") return <Peringatan>{p.error_pesan ?? "Review AI gagal."}</Peringatan>;
  if (p.status === "ANTRE")
    return <p className="text-xs text-blue-700">{p.menunggu_kapasitas ? "Menunggu kapasitas AI · " : ""}Antrean ke-{p.posisi_antrean ?? "?"}</p>;
  return <Progres persen={p.progres?.persen ?? 0} tahap={p.progres?.tahap ?? "Diproses"} />;
}

export function AksiUsulan({ u }: { u: BarisUsulan }) {
  const { punya } = useAuth();
  const nav = useNavigate();
  const qc = useQueryClient();
  const ajukan = useMutation({
    mutationFn: () => api.post(`/api/usulan/${u.id}/ajukan`),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e) => alert((e as Error).message),
  });
  const hapus = useMutation({
    mutationFn: () => api.del(`/api/usulan/${u.id}`),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e) => alert((e as Error).message),
  });
  const ada_hasil = !!u.review_id && ["MENUNGGU_VERIFIKASI", "LOLOS", "TIDAK_LOLOS"].includes(u.status);
  const pengusul = u.boleh_kelola && !u.diarsipkan;

  return (
    <div className="flex flex-wrap gap-1.5">
      {pengusul && (u.status === "DRAF" || u.status === "GAGAL") && (
        <>
          <Tombol kecil memuat={ajukan.isPending} onClick={() => ajukan.mutate()}><Send className="size-3.5" />{u.status === "GAGAL" ? "Ajukan Ulang" : "Ajukan Review"}</Tombol>
          <Tombol kecil varian="sekunder" onClick={() => nav(`/usulan/${u.id}/draf`)}>Ubah</Tombol>
        </>
      )}
      {pengusul && u.status === "DRAF" && !u.pernah_direview && (
        <Tombol kecil varian="hantu" className="text-red-600" memuat={hapus.isPending}
          onClick={() => confirm("Hapus usulan draf ini?") && hapus.mutate()}>Hapus</Tombol>
      )}
      {ada_hasil && punya("REVIEWER") && u.status === "MENUNGGU_VERIFIKASI" && (
        <Tombol kecil varian="ubah" onClick={() => nav(`/review/${u.review_id}`)}>Periksa Hasil</Tombol>
      )}
      {ada_hasil && !(punya("REVIEWER") && u.status === "MENUNGGU_VERIFIKASI") && (
        <Tombol kecil varian="sekunder" onClick={() => nav(`/review/${u.review_id}`)}>{u.status === "MENUNGGU_VERIFIKASI" ? "Lihat Hasil AI" : "Lihat Hasil"}</Tombol>
      )}
      {pengusul && u.status === "TIDAK_LOLOS" && (
        <Tombol kecil onClick={() => nav(`/usulan/${u.id}/revisi`)}><Upload className="size-3.5" />Unggah Revisi</Tombol>
      )}
      <Link to={`/usulan/${u.id}/riwayat`} className="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-medium text-slate-600 hover:bg-slate-100">
        <History className="size-3.5" />Riwayat
      </Link>
      {u.diarsipkan && <Lencana className="bg-slate-100 text-slate-600 ring-slate-300">Arsip</Lencana>}
    </div>
  );
}
