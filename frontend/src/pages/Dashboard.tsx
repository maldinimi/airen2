/** Dashboard (Pengusul & Reviewer) — hanya informasi, tanpa tombol tindakan: 4 kartu angka utama, (Pengusul) pengajuan terakhir,
 *  Data Master, lalu ringkasan per Satuan Kerja (Reviewer saja) di samping grafik jumlah pengajuan. Kartu tidak dapat diklik. */
import { useQuery } from "@tanstack/react-query";
import { BookOpen, CalendarClock, CircleCheck, CircleX, ClipboardList, Hourglass, Landmark, ListChecks, Server, Tags, type LucideIcon }
  from "lucide-react";
import { type ReactNode, useLayoutEffect, useRef, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { namaRevisi, tanggal, waktu } from "../format";
import type { StatusRevisi } from "../types";
import { Judul, Kartu, LencanaStatus, Memuat, NAMA_STATUS, Peringatan, cx } from "../ui";

type KunciMaster = "checklist" | "acuan" | "kategori" | "master_ro";
// Kartu Data Master: [kunci respons, label, ikon (sama dengan menu samping)].
const MASTER: [KunciMaster, string, LucideIcon][] = [["checklist", "Checklist", ListChecks], ["acuan", "Acuan", BookOpen],
  ["kategori", "Kategori", Tags], ["master_ro", "Master RO", Landmark]];

type Data = {
  total: number; per_status: Partial<Record<StatusRevisi, number>>;
  per_satker: { satker: string; total: number; lolos: number; tidak_lolos: number; proses: number }[];
  master: Record<KunciMaster, { total: number; aktif: number; diubah_at: string | null }>;
  terakhir?: { kode_ro: string; nama_ro: string; revisi_nomor: number; status: StatusRevisi; diajukan_at: string };  // Pengusul saja
  antrean?: { antre: number; diproses: number; rata_menit_per_review: number | null; perkiraan_selesai_menit: number | null;
    node: { nama: string; terakhir_terlihat: string; info: Record<string, string> | null }[] };
};

export default function Dashboard() {
  const { pengguna, punya } = useAuth();
  // Pengusul hanya melihat Satker-nya sendiri, jadi Ringkasan per Satuan Kerja tidak ditampilkan (desain.md §7 no. 70).
  const semuaSatker = punya("REVIEWER");
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<Data>("/api/dashboard"), refetchInterval: 15000 });
  if (q.isLoading) return <Memuat />;
  if (q.error || !q.data) return <Peringatan>{(q.error as Error)?.message}</Peringatan>;
  const d = q.data;
  const n = (s: StatusRevisi) => d.per_status[s] ?? 0;
  const diperbarui = new Date(q.dataUpdatedAt).toISOString();
  // Pengusul (desain.md §7 no. 71): persentase Lolos/Tidak Lolos dari pengajuan yang sudah diverifikasi, dan kartu Master RO
  // (menu yang tidak dimilikinya) diganti waktu acuan review (Checklist/Acuan/Kategori) terakhir diperbarui.
  const diverifikasi = n("LOLOS") + n("TIDAK_LOLOS");
  const porsi = (x: number) => (!semuaSatker && diverifikasi ? `${Math.round((100 * x) / diverifikasi)}% dari terverifikasi` : undefined);
  const masterTampil = semuaSatker ? MASTER : MASTER.filter(([k]) => k !== "master_ro");
  const [ubahKunci, ubahLabel] = MASTER.filter(([k]) => k !== "master_ro" && d.master[k].diubah_at)
    .sort(([a], [b]) => Date.parse(d.master[b].diubah_at!) - Date.parse(d.master[a].diubah_at!))[0] ?? [];
  const ubahAt = ubahKunci && d.master[ubahKunci].diubah_at;

  return (
    <div className="space-y-6">
      <Judul judul="Dashboard" sub={`Selamat datang, ${pengguna?.nama}. Ringkasan pengajuan · diperbarui ${tanggal(diperbarui)} pukul ${jam(diperbarui)}.`} />

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Angka label="Total Pengajuan" nilai={d.total} ikon={<ClipboardList className="size-5" />} warna={WARNA.utama} />
        <Angka label="Menunggu Verifikasi" nilai={n("MENUNGGU_VERIFIKASI")}
          ikon={<Hourglass className="size-5" />} warna={WARNA.kuning} />
        <Angka label="Lolos" nilai={n("LOLOS")} sub={porsi(n("LOLOS"))} ikon={<CircleCheck className="size-5" />} warna={WARNA.hijau} />
        <Angka label="Tidak Lolos" nilai={n("TIDAK_LOLOS")} sub={porsi(n("TIDAK_LOLOS"))} ikon={<CircleX className="size-5" />} warna={WARNA.merah} />
      </div>

      {d.terakhir && (
        <section aria-labelledby="judul-terakhir">
          <h2 id="judul-terakhir" className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Pengajuan Terakhir</h2>
          <Kartu className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 p-5">
            <div className="min-w-0">
              <div className="font-semibold text-slate-900">{d.terakhir.kode_ro}</div>
              <div className="text-sm text-slate-600">{d.terakhir.nama_ro}</div>
            </div>
            <dl className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
              <div><dt className="text-xs text-slate-500">Tahap</dt><dd className="font-medium text-slate-900">{namaRevisi(d.terakhir.revisi_nomor)}</dd></div>
              <div><dt className="text-xs text-slate-500">Tanggal Pengajuan</dt><dd className="font-medium text-slate-900">{waktu(d.terakhir.diajukan_at)}</dd></div>
              <div><dt className="text-xs text-slate-500">Status</dt><dd className="mt-0.5"><LencanaStatus status={d.terakhir.status} /></dd></div>
            </dl>
          </Kartu>
        </section>
      )}

      <section aria-labelledby="judul-data-master">
        <h2 id="judul-data-master" className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Data Master</h2>
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          {masterTampil.map(([k, label, Ikon]) => (
            <Angka key={k} label={label} nilai={d.master[k].total}
              sub={`${d.master[k].aktif} Aktif · ${d.master[k].total - d.master[k].aktif} Nonaktif`} ikon={<Ikon className="size-5" />} warna={WARNA.netral} />
          ))}
          {!semuaSatker && <Angka label="Terakhir Diperbarui" nilai={ubahAt ? tanggal(ubahAt) : "—"} ikon={<CalendarClock className="size-5" />}
            sub={ubahAt ? `${ubahLabel} · pukul ${jam(ubahAt)}` : undefined} warna={WARNA.netral} />}
        </div>
      </section>

      {/* grid-cols-1 = minmax(0, 1fr): tanpa ini kolom tunggal selebar isi grafik yang bergeser dan panel keluar layar. */}
      <div className={cx("grid grid-cols-1 gap-6", semuaSatker && "xl:grid-cols-2")}>
        {semuaSatker && <Panel judul="Ringkasan per Satuan Kerja">
          {d.per_satker.length === 0 ? <Kosong>Belum ada pengajuan.</Kosong> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-600">
                  <tr><th scope="col" className="px-3 py-2 text-left">Satuan Kerja</th>
                    {["Total", NAMA_STATUS.LOLOS, NAMA_STATUS.TIDAK_LOLOS, "Dalam proses"].map((h) =>
                      <th key={h} scope="col" className="whitespace-nowrap px-3 py-2 text-right">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100 tabular-nums">{d.per_satker.map((s) => (
                  <tr key={s.satker} className="hover:bg-slate-50">
                    <td className="px-3 py-2 text-slate-800">{s.satker}</td>
                    <td className="px-3 py-2 text-right font-semibold text-slate-900">{s.total}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{s.lolos}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{s.tidak_lolos}</td>
                    <td className="px-3 py-2 text-right text-slate-700">{s.proses}</td>
                  </tr>))}</tbody>
              </table>
            </div>
          )}
        </Panel>}
        <GrafikPengajuan />
      </div>

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
  netral: { kartu: "border-slate-200 bg-white", label: "text-slate-500", ikon: "bg-utama-50 text-utama-700" },  // Data Master
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

// Jam data Dashboard terakhir dimuat (angka menyegarkan sendiri tiap 15 detik).
const fmtJam = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "Asia/Jakarta" });
const jam = (iso: string) => fmtJam.format(new Date(iso));

type Per = "hari" | "minggu" | "bulan" | "tahun";
type Tren = { per: Per; data: { mulai: string; jumlah: number }[] };
const PILIHAN_PER: [Per, string][] = [["hari", "Per Tanggal"], ["minggu", "Per Minggu"], ["bulan", "Per Bulan"], ["tahun", "Per Tahun"]];
const KETERANGAN_PER: Record<Per, string> = { hari: "30 hari terakhir", minggu: "12 minggu terakhir (mulai Senin)",
  bulan: "12 bulan terakhir", tahun: "5 tahun terakhir" };
const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("id-ID", o);
const fmtHari = fmt({ day: "numeric", month: "short" }), fmtTgl = fmt({ day: "numeric", month: "short", year: "numeric" });
const fmtBulan = fmt({ month: "short", year: "2-digit" }), fmtBulanPanjang = fmt({ month: "long", year: "numeric" });

/** Label periode dari tanggal awalnya (YYYY-MM-DD): pendek untuk sumbu, panjang untuk tooltip. */
function labelPeriode(iso: string, per: Per, panjang: boolean) {
  const d = new Date(`${iso}T00:00:00`);
  if (per === "tahun") return iso.slice(0, 4);
  if (per === "bulan") return (panjang ? fmtBulanPanjang : fmtBulan).format(d);
  if (per === "minggu" && panjang) return `${fmtHari.format(d)} – ${fmtTgl.format(new Date(d.getTime() + 6 * 864e5))}`;
  return (panjang ? fmtTgl : fmtHari).format(d);
}

/** Grafik batang jumlah pengajuan baru per tanggal/minggu/bulan/tahun. Satu seri (tanpa legenda, judul menamainya); angka
 *  muncul di tooltip saat batang diarahkan; tabel tersembunyi untuk pembaca layar. */
function GrafikPengajuan() {
  const [per, setPer] = useState<Per>("hari");
  const q = useQuery({ queryKey: ["dashboard-tren", per], queryFn: () => api.get<Tren>(`/api/dashboard/tren?per=${per}`),
    placeholderData: (lama) => lama, refetchInterval: 60000 });
  const pilih = (
    <div role="radiogroup" aria-label="Periode grafik" className="inline-flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
      {PILIHAN_PER.map(([k, l]) => (
        <button key={k} type="button" role="radio" aria-checked={per === k} onClick={() => setPer(k)}
          className={cx("rounded-md px-3 py-1 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100",
            per === k ? "bg-white text-utama-700 shadow-sm" : "text-slate-600 hover:text-slate-900")}>{l}</button>))}
    </div>
  );
  return (
    <Panel judul="Jumlah Pengajuan" keterangan={`Pengajuan baru · ${KETERANGAN_PER[per]}`} aksi={pilih}>
      {q.isLoading ? <Memuat /> : q.error || !q.data ? <Peringatan>{(q.error as Error)?.message}</Peringatan> : <Batang t={q.data} />}
    </Panel>
  );
}

// Banyak batang yang terlihat per layar grafik; periode lebih lama dilihat dengan menggeser grafik ke kiri (desain.md §7 no. 68).
const PER_LAYAR = 7;

function Batang({ t }: { t: Tren }) {
  const gulir = useRef<HTMLDivElement>(null);
  const maks = Math.max(0, ...t.data.map((x) => x.jumlah));
  // Mulai dari periode terbaru (ujung kanan) saat grafik muncul atau jenis periode diganti; penyegaran otomatis tiap
  // menit tidak menggeser posisi yang sedang dilihat.
  useLayoutEffect(() => { const g = gulir.current; if (g) g.scrollLeft = g.scrollWidth; }, [t.per, maks === 0]);
  if (maks === 0) return <Kosong>Belum ada pengajuan pada periode ini.</Kosong>;
  const skala = Math.ceil(maks / 4) * 4;  // kelipatan 4 → garis bantu 0, ½, penuh selalu bilangan bulat
  const akhir = t.data.length - 1;
  return (
    <div>
      <div className="flex gap-2">
        <div className="relative mt-9 h-52 w-7 shrink-0 text-right text-[11px] tabular-nums text-slate-400" aria-hidden>
          {[0, 50, 100].map((p) => <span key={p} className="absolute right-0 translate-y-1/2" style={{ bottom: `${p}%` }}>{(skala * p) / 100}</span>)}
        </div>
        {/* Sumbu kiri tetap, area batang bergeser. pt-9 = ruang tooltip di atas batang tertinggi (wadah gulir memotong isinya). */}
        <div ref={gulir} role="region" tabIndex={0} aria-label="Grafik jumlah pengajuan, geser ke kiri untuk periode sebelumnya"
          className="min-w-0 flex-1 overflow-x-auto pb-1 pt-9 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
          <div aria-hidden style={{ width: `${Math.max(1, t.data.length / PER_LAYAR) * 100}%` }}>
          <div className="relative h-52">
            {[0, 50, 100].map((p) => <div key={p} className={cx("absolute inset-x-0 border-t", p ? "border-dashed border-slate-200" : "border-slate-300")}
              style={{ bottom: `${p}%` }} />)}
            <div className="absolute inset-0 flex items-end gap-0.5">
              {t.data.map((x, i) => (
                <div key={x.mulai} className="group flex h-full flex-1 items-end justify-center">
                  <div className="relative w-full max-w-10 rounded-t bg-utama-600 transition-colors group-hover:bg-utama-800"
                    style={{ height: `${(x.jumlah / skala) * 100}%`, minHeight: x.jumlah ? 2 : 0 }}>
                    {/* Batang pertama/terakhir: tooltip rata kiri/kanan agar tidak terpotong tepi grafik. */}
                    <div className={cx("pointer-events-none absolute bottom-full z-10 mb-1.5 hidden whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs text-white shadow-lg group-hover:block",
                      i === 0 ? "left-0" : i === akhir ? "right-0" : "left-1/2 -translate-x-1/2")}>
                      {labelPeriode(x.mulai, t.per, true)}: <b>{x.jumlah}</b> pengajuan
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {/* Setiap batang berlabel (tanpa lompatan), mis. 1 Nov, 2 Nov, 3 Nov. */}
          <div className="mt-2 flex gap-0.5 text-[11px] text-slate-500">
            {t.data.map((x) => <span key={x.mulai} className="flex-1 whitespace-nowrap text-center">{labelPeriode(x.mulai, t.per, false)}</span>)}
          </div>
          </div>
        </div>
      </div>
      {/* sr-only di <div>, bukan di <table>: tabel mengabaikan tinggi 1px sehingga memanjangkan halaman (ruang kosong di bawah). */}
      <div className="sr-only"><table>
        <caption>Jumlah pengajuan baru per periode</caption>
        <thead><tr><th scope="col">Periode</th><th scope="col">Jumlah</th></tr></thead>
        <tbody>{t.data.map((x) => <tr key={x.mulai}><td>{labelPeriode(x.mulai, t.per, true)}</td><td>{x.jumlah}</td></tr>)}</tbody>
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
