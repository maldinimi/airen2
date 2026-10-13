import { useQuery } from "@tanstack/react-query";
import { Server } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AksiUsulan, InfoProses } from "../components/Usulan";
import { waktu } from "../format";
import type { BarisUsulan, StatusRevisi } from "../types";
import { Judul, Kartu, Kosong, LencanaStatus, Memuat, NAMA_STATUS, Peringatan } from "../ui";

type Data = {
  total: number; per_status: Partial<Record<StatusRevisi, number>>; per_kategori: Record<string, number>;
  per_satker: { satker: string; total: number; lolos: number; tidak_lolos: number; proses: number }[];
  perlu_tindakan: BarisUsulan[];
  antrean?: { antre: number; diproses: number; rata_menit_per_review: number | null; perkiraan_selesai_menit: number | null;
    node: { nama: string; terakhir_terlihat: string; info: Record<string, string> | null }[] };
};

const URUT: StatusRevisi[] = ["DRAF", "ANTRE", "DIPROSES_AI", "GAGAL", "MENUNGGU_VERIFIKASI", "LOLOS", "TIDAK_LOLOS"];

export default function Dashboard() {
  const { pengguna } = useAuth();
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<Data>("/api/dashboard"), refetchInterval: 15000 });
  if (q.isLoading) return <Memuat />;
  if (q.error || !q.data) return <Peringatan>{(q.error as Error)?.message}</Peringatan>;
  const d = q.data;
  const maksKat = Math.max(1, ...Object.values(d.per_kategori));

  return (
    <div className="space-y-6">
      <Judul judul={`Selamat datang, ${pengguna?.nama}`} sub={`${d.total} usulan aktif`} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-7">
        {URUT.map((s) => (
          <Link key={s} to={`/usulan?status=${s}`}>
            <Kartu className="p-4 transition-shadow hover:shadow-md">
              <div className="text-2xl font-semibold text-slate-900">{d.per_status[s] ?? 0}</div>
              <div className="mt-1"><LencanaStatus status={s} /></div>
            </Kartu>
          </Link>
        ))}
      </div>

      {d.antrean && (
        <Kartu className="p-4">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Server className="size-4" />Antrean AI</h2>
          <div className="grid gap-4 text-sm sm:grid-cols-4">
            <div><div className="text-2xl font-semibold">{d.antrean.antre}</div>antre</div>
            <div><div className="text-2xl font-semibold">{d.antrean.diproses}</div>sedang diproses</div>
            <div><div className="text-2xl font-semibold">{d.antrean.node.length}</div>node AI aktif</div>
            <div><div className="text-2xl font-semibold">{d.antrean.perkiraan_selesai_menit != null ? `±${d.antrean.perkiraan_selesai_menit} mnt` : "—"}</div>
              perkiraan antrean selesai{d.antrean.rata_menit_per_review ? ` (rata-rata ${d.antrean.rata_menit_per_review} mnt/review)` : ""}</div>
          </div>
          {d.antrean.node.length === 0 && <div className="mt-3"><Peringatan jenis="warn">Tidak ada node AI yang aktif. Review tetap aman di antrean dan diproses begitu node dinyalakan.</Peringatan></div>}
          {d.antrean.node.length > 0 && <p className="mt-3 text-xs text-slate-500">{d.antrean.node.map((n) => `${n.nama} (${n.info?.model ?? "?"}, terakhir ${waktu(n.terakhir_terlihat)})`).join(" · ")}</p>}
        </Kartu>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Kartu className="p-4">
          <h2 className="mb-3 font-semibold">Kategori final</h2>
          {Object.keys(d.per_kategori).length === 0 ? <p className="text-sm text-slate-500">Belum ada usulan yang difinalkan.</p> : (
            <div className="space-y-2">{Object.entries(d.per_kategori).sort().map(([k, n]) => (
              <div key={k} className="flex items-center gap-3 text-sm">
                <span className="w-8 font-medium">{k}</span>
                <div className="h-5 flex-1 rounded bg-slate-100"><div className="h-5 rounded bg-utama-500" style={{ width: `${(n / maksKat) * 100}%` }} /></div>
                <span className="w-8 text-right">{n}</span>
              </div>))}</div>
          )}
        </Kartu>
        <Kartu className="overflow-x-auto p-4">
          <h2 className="mb-3 font-semibold">Ringkasan per Satker</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500 [&_th]:px-2"><tr><th className="py-1">Satker</th><th>Total</th><th>{NAMA_STATUS.LOLOS}</th><th>{NAMA_STATUS.TIDAK_LOLOS}</th><th>Dalam proses</th></tr></thead>
            <tbody className="divide-y divide-slate-100 [&_td]:px-2">{d.per_satker.map((s) => (
              <tr key={s.satker}><td className="py-1.5">{s.satker}</td><td>{s.total}</td><td className="text-emerald-700">{s.lolos}</td><td className="text-red-700">{s.tidak_lolos}</td><td>{s.proses}</td></tr>))}</tbody>
          </table>
        </Kartu>
      </div>

      <section>
        <h2 className="mb-3 font-semibold">Perlu tindakan saya</h2>
        {d.perlu_tindakan.length === 0 ? <Kosong>Tidak ada yang perlu ditindaklanjuti.</Kosong> : (
          <div className="grid gap-3 md:grid-cols-2">{d.perlu_tindakan.map((u) => (
            <Kartu key={u.id} className="space-y-2 p-4">
              <div className="flex items-start justify-between gap-2">
                <div><div className="font-medium">{u.kode_ro} · {u.nama_ro}</div><div className="text-xs text-slate-500">{u.satker.nama} · Revisi {u.revisi_nomor}</div></div>
                <LencanaStatus status={u.status} />
              </div>
              <InfoProses p={u.proses} />
              <AksiUsulan u={u} />
            </Kartu>))}</div>
        )}
      </section>
    </div>
  );
}
