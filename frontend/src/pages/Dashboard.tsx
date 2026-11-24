/** Dashboard (Pengusul & Reviewer) — hanya informasi, tanpa tombol tindakan; angka mengikuti Tahun Anggaran di header
 *  (desain.md §7 no. 75, 80–81). Semua role: sapaan dan 4 kartu status (menyegarkan sendiri tiap 15 detik). Reviewer:
 *  Ringkasan per Satuan Kerja. Pengusul: jumlah Lolos per kategori dan diagram batang checklist Tidak Lolos.
 *  Kartu tidak dapat diklik. */
import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleX, ClipboardList, Hourglass, Server, Tags } from "lucide-react";
import type { ReactNode } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { KonteksLayout } from "../components/Layout";
import { waktu } from "../format";
import type { StatusRevisi } from "../types";
import { Judul, Kartu, Memuat, NAMA_STATUS, Peringatan, cx } from "../ui";

type Data = {
  total: number; per_status: Partial<Record<StatusRevisi, number>>;
  per_satker: { satker: string; total: number; lolos: number; tidak_lolos: number; menunggu: number }[];
  kategori_lolos?: { kode: string; nama: string; jumlah: number }[];  // Pengusul saja
  checklist_tidak_lolos?: { kode: string; checklist: string; ai: number; verifikator: number }[];  // Pengusul saja
  antrean?: { antre: number; diproses: number; rata_menit_per_review: number | null; perkiraan_selesai_menit: number | null;
    node: { nama: string; terakhir_terlihat: string; info: Record<string, string> | null }[] };
};

const JUDUL_BAGIAN = "mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500";

export default function Dashboard() {
  const { pengguna, punya } = useAuth();
  const semuaSatker = punya("REVIEWER");  // Reviewer melihat semua Satker; Pengusul hanya Satker-nya (dibatasi backend)
  const { tahun } = useOutletContext<KonteksLayout>();
  const q = useQuery({ queryKey: ["dashboard", tahun], queryFn: () => api.get<Data>(`/api/dashboard?tahun=${tahun}`), refetchInterval: 15000 });
  if (q.isLoading) return <Memuat />;
  if (q.error || !q.data) return <Peringatan>{(q.error as Error)?.message}</Peringatan>;
  const d = q.data;
  const n = (s: StatusRevisi) => d.per_status[s] ?? 0;

  return (
    <div className="space-y-6">
      <Judul judul="Dashboard" sub={<span className="block text-lg font-medium text-slate-800 sm:text-xl">Selamat datang, {pengguna?.nama}.</span>} />

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Angka label="Total Pengajuan" nilai={d.total} ikon={<ClipboardList className="size-5" />} warna={WARNA.utama} />
        <Angka label="Menunggu Verifikasi" nilai={n("MENUNGGU_VERIFIKASI")}
          ikon={<Hourglass className="size-5" />} warna={WARNA.kuning} />
        <Angka label="Lolos" nilai={n("LOLOS")} ikon={<CircleCheck className="size-5" />} warna={WARNA.hijau} />
        <Angka label="Tidak Lolos" nilai={n("TIDAK_LOLOS")} ikon={<CircleX className="size-5" />} warna={WARNA.merah} />
      </div>

      {d.kategori_lolos && (
        <section aria-labelledby="judul-kategori">
          <h2 id="judul-kategori" className={JUDUL_BAGIAN}>Lolos per Kategori</h2>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            {d.kategori_lolos.map((k) => (
              <Angka key={k.kode} label={`${k.kode} · ${k.nama}`} nilai={k.jumlah}
                ikon={<Tags className="size-5" />} warna={WARNA.netral} />))}
          </div>
        </section>
      )}

      {d.checklist_tidak_lolos && (
        <Panel judul="Checklist Tidak Lolos">
          {d.checklist_tidak_lolos.length === 0 ? <Kosong>Belum ada checklist yang tidak lolos.</Kosong>
            : <BatangChecklist data={d.checklist_tidak_lolos} />}
        </Panel>
      )}

      {semuaSatker && (
        <Panel judul="Ringkasan per Satuan Kerja">
          {d.per_satker.length === 0 ? <Kosong>Belum ada pengajuan.</Kosong> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
                  <tr><th scope="col" className="px-3 py-2 text-left">Satuan Kerja</th>
                    {["Total", NAMA_STATUS.LOLOS, NAMA_STATUS.TIDAK_LOLOS, "Menunggu Verifikasi"].map((h) =>
                      <th key={h} scope="col" className="whitespace-nowrap px-3 py-2 text-right">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100 tabular-nums">{d.per_satker.map((s) => (
                  <tr key={s.satker} className="hover:bg-slate-50">
                    <td className="px-3 py-2 text-slate-800">{s.satker}</td>
                    <td className="px-3 py-2 text-right font-semibold text-slate-900">{s.total}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{s.lolos}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{s.tidak_lolos}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{s.menunggu}</td>
                  </tr>))}</tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      {d.antrean && <AntreanAI a={d.antrean} />}
    </div>
  );
}

// Warna tipis per kartu: latar & garis tepi lembut, judul berwarna, angka tetap gelap. Kelas ditulis utuh (dibaca Tailwind).
const WARNA = {
  utama: { kartu: "border-utama-100 bg-utama-50/60", label: "text-utama-700", ikon: "bg-white text-utama-700" },
  kuning: { kartu: "border-amber-200 bg-amber-50/60", label: "text-amber-700", ikon: "bg-white text-amber-700" },
  hijau: { kartu: "border-emerald-200 bg-emerald-50/60", label: "text-emerald-700", ikon: "bg-white text-emerald-700" },
  merah: { kartu: "border-red-200 bg-red-50/60", label: "text-red-700", ikon: "bg-white text-red-700" },
  netral: { kartu: "border-slate-200 bg-white", label: "text-slate-500", ikon: "bg-utama-50 text-utama-700" },  // Lolos per Kategori
};

/** Kartu angka (informasi saja, bukan tombol): label, angka besar, keterangan opsional, ikon berwarna (warna status selalu
 *  disertai ikon & label). */
function Angka({ label, nilai, sub, ikon, warna }: { label: string; nilai: number | string; sub?: string; ikon: ReactNode; warna: typeof WARNA.utama }) {
  return (
    <div className={cx("flex h-full items-center justify-between gap-3 rounded-xl border p-5 shadow-sm", warna.kartu)}>
      <div>
        <div className={cx("text-xs font-semibold uppercase tracking-wide", warna.label)}>{label}</div>
        {/* Teks (mis. tanggal) lebih kecil agar muat satu baris; tinggi baris sama dengan angka agar kartu sejajar. */}
        <div className={cx("mt-1 font-semibold tabular-nums text-slate-900", typeof nilai === "string" ? "text-xl/9" : "text-3xl")}>{nilai}</div>
        {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
      </div>
      <span className={cx("grid size-11 shrink-0 place-items-center rounded-xl shadow-sm", warna.ikon)} aria-hidden>{ikon}</span>
    </div>
  );
}

function Panel({ judul, keterangan, aksi, className, children }: {
  judul: string; keterangan?: string; aksi?: ReactNode; className?: string; children: ReactNode;
}) {
  return (
    <Kartu className={cx("p-5", className)}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div><h2 className="font-semibold text-slate-900">{judul}</h2>
          {keterangan && aksi && <p className="text-xs text-slate-500">{keterangan}</p>}</div>
        {aksi ?? (keterangan && <span className="text-xs text-slate-500">{keterangan}</span>)}
      </div>
      {children}
    </Kartu>
  );
}

const Kosong = ({ children }: { children: ReactNode }) => <p className="py-6 text-center text-sm text-slate-500">{children}</p>;

// Dua seri diagram batang Checklist Tidak Lolos. Biru–oranye lolos uji buta warna (ΔE 31); legenda selalu tampil.
const SERI = [
  { kunci: "ai", label: "AI", warna: "#2553e0" },
  { kunci: "verifikator", label: "Verifikator", warna: "#ea580c" },
] as const;

/** Diagram batang berkelompok Checklist Tidak Lolos (Pengusul): satu kelompok per item checklist (kode di sumbu bawah), dua
 *  batang berdampingan (AI, Verifikator) dengan celah 2px; angka & nama item di tooltip saat diarahkan; tabel tersembunyi untuk
 *  pembaca layar. Banyak item → diagram dapat digeser (sumbu angka tetap). */
function BatangChecklist({ data }: { data: NonNullable<Data["checklist_tidak_lolos"]> }) {
  const skala = Math.max(4, Math.ceil(Math.max(...data.flatMap((c) => [c.ai, c.verifikator])) / 4) * 4);
  const akhir = data.length - 1;
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600">
        {SERI.map((s) => (
          <span key={s.kunci} className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-sm" style={{ backgroundColor: s.warna }} aria-hidden />{s.label}
          </span>))}
      </div>
      <div className="flex gap-2">
        <div className="relative mt-3 h-52 w-7 shrink-0 text-right text-[11px] tabular-nums text-slate-400" aria-hidden>
          {[0, 50, 100].map((p) => <span key={p} className="absolute right-0 translate-y-1/2" style={{ bottom: `${p}%` }}>{(skala * p) / 100}</span>)}
        </div>
        <div className="min-w-0 flex-1 overflow-x-auto pb-1 pt-3">
          <div aria-hidden style={{ minWidth: `${data.length * 4}rem` }}>
            <div className="relative h-52">
              {[0, 50, 100].map((p) => <div key={p} className={cx("absolute inset-x-0 border-t", p ? "border-dashed border-slate-200" : "border-slate-300")}
                style={{ bottom: `${p}%` }} />)}
              <div className="absolute inset-0 flex">
                {data.map((c, i) => (
                  <div key={c.kode} className="group relative flex h-full flex-1 items-end justify-center gap-0.5 px-2">
                    {SERI.map((s) => (
                      <div key={s.kunci} className="w-full max-w-7 rounded-t transition-[filter] group-hover:brightness-90"
                        style={{ height: `${(c[s.kunci] / skala) * 100}%`, minHeight: c[s.kunci] ? 2 : 0, backgroundColor: s.warna }} />))}
                    {/* Tooltip di dalam area diagram (bukan di atasnya): wadah geser memotong apa pun di luar tingginya. */}
                    <div className={cx("pointer-events-none absolute top-0 z-10 hidden whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow-lg group-hover:block",
                      i === 0 ? "left-0" : i === akhir ? "right-0" : "left-1/2 -translate-x-1/2")}>
                      <div className="font-semibold">{c.kode} · {c.checklist}</div>
                      {SERI.map((s) => <div key={s.kunci}>{s.label}: <b>{c[s.kunci]}</b></div>)}
                    </div>
                  </div>))}
              </div>
            </div>
            <div className="mt-2 flex text-[11px] text-slate-500">
              {data.map((c) => <span key={c.kode} className="flex-1 truncate text-center" title={c.checklist}>{c.kode}</span>)}
            </div>
          </div>
        </div>
      </div>
      <div className="sr-only"><table>
        <caption>Jumlah pemeriksaan yang tidak lolos per item checklist</caption>
        <thead><tr><th scope="col">Checklist</th>{SERI.map((s) => <th key={s.kunci} scope="col">{s.label}</th>)}</tr></thead>
        <tbody>{data.map((c) => <tr key={c.kode}><td>{c.kode} · {c.checklist}</td>{SERI.map((s) => <td key={s.kunci}>{c[s.kunci]}</td>)}</tr>)}</tbody>
      </table></div>
    </div>
  );
}

/** Antrean AI (hanya pengguna yang juga ber-role Admin). */
function AntreanAI({ a }: { a: NonNullable<Data["antrean"]> }) {
  const isi: [string, ReactNode][] = [["Antre", a.antre], ["Sedang diproses", a.diproses], ["Node AI aktif", a.node.length],
    ["Perkiraan selesai", a.perkiraan_selesai_menit != null ? `±${a.perkiraan_selesai_menit} mnt` : "—"]];
  return (
    <Panel judul="Antrean AI" keterangan={a.rata_menit_per_review ? `Rata-rata ${a.rata_menit_per_review} mnt/review` : undefined}>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">{isi.map(([l, v]) => (
        <div key={l}><div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{l}</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{v}</div></div>))}</div>
      {a.node.length === 0
        ? <div className="mt-4"><Peringatan jenis="warn">Tidak ada node AI yang aktif. Review tetap aman di antrean dan diproses begitu node dinyalakan.</Peringatan></div>
        : <p className="mt-4 flex items-center gap-1.5 text-xs text-slate-500"><Server className="size-3.5" aria-hidden />
            {a.node.map((x) => `${x.nama} (${x.info?.model ?? "?"}, terakhir ${waktu(x.terakhir_terlihat)})`).join(" · ")}</p>}
    </Panel>
  );
}
