/** Menu Usulan — halaman pertama: histori usulan (desain.md §7 no. 36 & 45). Form filter per kolom tabel (diterapkan lewat
 *  tombol) dan urut per kolom; keduanya di URL dan diproses backend karena daftar berhalaman. Pengusul hanya melihat usulan
 *  Satker-nya (dicek backend). */
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, ArrowUpDown, CalendarDays, ChevronDown, ChevronUp, Filter, Plus, RotateCcw, Search } from "lucide-react";
import { type FormEvent, type ReactNode, useRef, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { api, qs } from "../api";
import { useAuth } from "../auth";
import type { KonteksLayout } from "../components/Layout";
import { AksiUsulan, InfoProses, TautanDokumen } from "../components/Usulan";
import { waktuAngka } from "../format";
import type { BarisUsulan, Satker, StatusRevisi } from "../types";
import { Halaman, Input, Judul, Kartu, Kosong, LencanaStatus, Memuat, NAMA_STATUS, Peringatan, Pilih, TanggalJam, Tombol, cx, kelasGalat } from "../ui";

type Opsi = { satker: Satker[]; tahun: number[]; kategori: string[]; status: { kode: string; nama: string }[] };
// Kunci filter (= parameter API) sesuai kolom tabel, kecuali No & Aksi.
const KOSONG = { satker: "", q: "", dokumen: "", status: "", tanggal: "" };
type Saring = typeof KOSONG;
// Kolom yang dapat diurutkan → nilai `urut` API.
const KOLOM: [string, string | null][] = [["No", null], ["Satuan Kerja", "satker"], ["Rincian Output", "rincian"], ["Dokumen", "dokumen"],
  ["Status", "status"], ["Tanggal Pengajuan", "tanggal"], ["Aksi", null]];

export default function UsulanList() {
  const { punya, pengguna } = useAuth();
  const [sp, setSp] = useSearchParams();
  // Tahun dipilih di header (components/Layout.tsx), bukan di URL halaman ini.
  const { tahun } = useOutletContext<KonteksLayout>();
  const f: Record<string, string> = { ...Object.fromEntries(sp.entries()), tahun };
  const ubah = (k: string, v: string) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); if (k !== "halaman") n.delete("halaman"); setSp(n, { replace: true }); };
  const terpasang: Saring = { satker: f.satker ?? "", q: f.q ?? "", dokumen: f.dokumen ?? "", status: f.status ?? "", tanggal: f.tanggal ?? "" };
  const terapkan = (x: Saring) => {
    const n = new URLSearchParams(sp);
    Object.entries(x).forEach(([k, v]) => (v ? n.set(k, v) : n.delete(k)));
    n.delete("halaman");
    setSp(n, { replace: true });
  };
  const klikUrut = (k: string) => {
    const n = new URLSearchParams(sp);
    n.set("arah", f.urut === k && f.arah !== "desc" ? "desc" : "asc");
    n.set("urut", k);
    n.delete("halaman");
    setSp(n, { replace: true });
  };
  const adaFilter = Object.values(terpasang).some(Boolean);
  // Form filter awalnya terlipat; tetap terbuka bila URL sudah berisi filter. Di induk agar tidak terlipat lagi saat form dipasang ulang.
  const [bukaFilter, setBukaFilter] = useState(adaFilter);
  const opsi = useQuery({ queryKey: ["opsi-filter"], queryFn: () => api.get<Opsi>("/api/usulan/opsi/filter") });
  const data = useQuery({
    queryKey: ["usulan", f],
    queryFn: () => api.get<{ total: number; halaman: number; per_halaman: number; data: BarisUsulan[] }>(`/api/usulan${qs(f)}`),
    refetchInterval: (q) => (q.state.data?.data.some((u) => ["ANTRE", "DIPROSES_AI"].includes(u.status)) ? 5000 : false),
  });

  return (
    <div>
      {/* Pengusul hanya melihat usulan Satker-nya (dibatasi backend); Reviewer melihat semua Satker. */}
      <Judul judul="Usulan" sub={punya("REVIEWER") ? "Histori usulan seluruh Satuan Kerja."
        : `Histori usulan ${pengguna?.satker?.nama ?? "Satuan Kerja Anda"}.`}
        aksi={punya("PENGUSUL") && <Link to="/usulan/baru"><Tombol><Plus className="size-4" />Pengajuan Baru</Tombol></Link>} />
      <FormFilter key={JSON.stringify(terpasang)} terpasang={terpasang} terapkan={terapkan} status={opsi.data?.status ?? []}
        buka={bukaFilter} setBuka={setBukaFilter}
        info={data.data ? `Menampilkan ${data.data.data.length} dari ${data.data.total} usulan` : ""} />

      {data.isLoading ? <Memuat /> : data.error ? <Peringatan>{(data.error as Error).message}</Peringatan> : !data.data?.data.length ? (
        adaFilter ? <Kosong>Tidak ada usulan yang sesuai dengan filter.</Kosong>
          : <Kosong>Belum ada usulan{punya("PENGUSUL") && <> — <Link className="text-utama-600 underline" to="/usulan/baru">buat pengajuan pertama</Link></>}.</Kosong>
      ) : (
        <>
          {/* Layar kecil: kartu per usulan; md ke atas: tabel. */}
          <div className="space-y-3 md:hidden">
            {data.data.data.map((u) => (
              <Kartu key={u.id} className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900">{u.kode_ro}</div>
                    <div className="text-sm text-slate-600">{u.nama_ro}</div>
                    <div className="mt-1 text-xs text-slate-500">{u.satker.nama} · {waktuAngka(u.dibuat_at)}</div>
                  </div>
                  <LencanaStatus status={u.status} />
                </div>
                <InfoProses p={u.proses} />
                <div className="flex items-end justify-between gap-2"><TautanDokumen tor={u.tor} rab={u.rab} /><AksiUsulan u={u} /></div>
              </Kartu>
            ))}
          </div>
          <Kartu className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[52rem] text-sm">
              <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
                <tr>{KOLOM.map(([h, k]) => {
                  const aktif = k !== null && f.urut === k;
                  const Ikon = !aktif ? ArrowUpDown : f.arah === "desc" ? ArrowDown : ArrowUp;
                  return (
                    <th key={h} scope="col" aria-sort={aktif ? (f.arah === "desc" ? "descending" : "ascending") : undefined}
                      className={cx("whitespace-nowrap px-3 py-2.5", ["No", "Status", "Tanggal Pengajuan", "Aksi"].includes(h) ? "text-center" : "text-left")}>
                      {k === null ? h : (
                        <button type="button" onClick={() => klikUrut(k)} title={`Urutkan berdasarkan ${h}`}
                          className="inline-flex items-center gap-1 rounded font-semibold hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
                          {h}<Ikon className={cx("size-3.5", aktif ? "text-utama-600" : "text-slate-400")} aria-hidden />
                        </button>
                      )}
                    </th>
                  );
                })}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.data.data.map((u, i) => (
                  <tr key={u.id} className="align-top transition-colors hover:bg-slate-50">
                    <td className="px-3 py-3 text-center text-slate-500">{(data.data.halaman - 1) * data.data.per_halaman + i + 1}</td>
                    <td className="max-w-48 px-3 py-3 text-slate-900">{u.satker.nama}</td>
                    <td className="max-w-72 px-3 py-3"><div className="font-medium text-slate-900">{u.kode_ro}</div><div className="text-slate-500">{u.nama_ro}</div></td>
                    <td className="px-3 py-3"><TautanDokumen tor={u.tor} rab={u.rab} /></td>
                    <td className="min-w-44 space-y-1.5 px-3 py-3 text-center"><LencanaStatus status={u.status} /><InfoProses p={u.proses} /></td>
                    <td className="whitespace-nowrap px-3 py-3 text-center text-slate-600"><TanggalJam iso={u.dibuat_at} /></td>
                    <td className="px-3 py-2"><AksiUsulan u={u} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Kartu>
          <Halaman total={data.data.total} halaman={data.data.halaman} per={data.data.per_halaman} ubah={(h) => ubah("halaman", String(h))}
            ubahPer={(n) => ubah("per_halaman", String(n))} />
        </>
      )}
    </div>
  );
}

/** Form filter per kolom (seperti Form Filter Panduan): isian baru dipakai setelah "Terapkan"; "Reset" mengosongkan
 *  semua filter. Dapat dilipat. */
function FormFilter({ terpasang, terapkan, status, info, buka, setBuka }: {
  terpasang: Saring; terapkan: (x: Saring) => void; status: { kode: string; nama: string }[]; info: string;
  buka: boolean; setBuka: (b: boolean) => void;
}) {
  // Di draf, tanggal berupa teks dd/mm/yyyy; di URL/API berupa ISO yyyy-mm-dd.
  const [draf, setDraf] = useState({ ...terpasang, tanggal: keTeks(terpasang.tanggal) });
  const [galatTgl, setGalatTgl] = useState(false);
  const set = (k: keyof Saring, v: string) => setDraf({ ...draf, [k]: v });
  const kirim = (e: FormEvent) => {
    e.preventDefault();
    const iso = draf.tanggal ? keIso(draf.tanggal) : "";
    if (iso === null) { setGalatTgl(true); return; }
    terapkan({ ...draf, tanggal: iso });
  };
  const teks = (k: keyof Saring, no: number, label: string, placeholder: string) => (
    <Isian no={no} label={label}>
      <div className="relative">
        <Search className="absolute left-3 top-3 size-4 text-slate-400" aria-hidden />
        <Input className="pl-9" placeholder={placeholder} value={draf[k]} onChange={(e) => set(k, e.target.value)} aria-label={label} />
      </div>
    </Isian>
  );
  return (
    <Kartu className="mb-4">
      <button type="button" onClick={() => setBuka(!buka)} aria-expanded={buka}
        className="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
        <span className="flex items-center gap-2 text-sm font-bold uppercase text-slate-800"><Filter className="size-4 text-utama-600" aria-hidden />Form Filter Pencarian Usulan</span>
        <span className="text-slate-500">{buka ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}</span>
      </button>
      {buka && (
        <form onSubmit={kirim} className="space-y-4 p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {teks("satker", 1, "Satuan Kerja", "Cari satuan kerja…")}
            {teks("q", 2, "Rincian Output", "Cari kode/nama RO…")}
            {teks("dokumen", 3, "Dokumen", "Cari nama dokumen, mis. .pdf…")}
            <Isian no={4} label="Status">
              <Pilih aria-label="Status" value={draf.status} onChange={(e) => set("status", e.target.value)}>
                <option value="">Semua Status</option>{status.map((x) => <option key={x.kode} value={x.kode}>{x.nama}</option>)}
                {/* Status di luar 3 pilihan (mis. dari kartu Dashboard "Gagal") tetap terlihat, bukan tampil "Semua Status". */}
                {draf.status && !status.some((x) => x.kode === draf.status) &&
                  <option value={draf.status}>{NAMA_STATUS[draf.status as StatusRevisi] ?? draf.status}</option>}
              </Pilih>
            </Isian>
            <Isian no={5} label="Tanggal Pengajuan">
              <InputTanggal teks={draf.tanggal} galat={galatTgl} ubah={(t) => { set("tanggal", t); setGalatTgl(false); }} />
              {galatTgl && <p className="text-xs text-red-600">Tanggal tidak valid. Gunakan format dd/mm/yyyy.</p>}
            </Isian>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-slate-600">{info}</span>
            <div className="flex flex-wrap gap-2">
              <Tombol type="button" varian="sekunder" onClick={() => { setDraf(KOSONG); terapkan(KOSONG); }}><RotateCcw className="size-4" />Reset</Tombol>
              <Tombol type="submit"><Filter className="size-4" />Terapkan</Tombol>
            </div>
          </div>
        </form>
      )}
    </Kartu>
  );
}

const keTeks = (iso: string) => (iso ? iso.split("-").reverse().join("/") : "");
/** "dd/mm/yyyy" → "yyyy-mm-dd"; null bila format salah atau tanggalnya tidak ada (mis. 31/02/2026). */
const keIso = (t: string) => {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(t);
  if (!m) return null;
  const iso = `${m[3]}-${m[2]}-${m[1]}`;
  const d = new Date(`${iso}T00:00:00Z`);
  return !isNaN(d.getTime()) && d.toISOString().startsWith(iso) ? iso : null;
};

/** Isian tanggal dd/mm/yyyy. Input date bawaan tidak dipakai karena formatnya mengikuti bahasa browser (mis. "dd/mm/tttt").
 *  Garis miring disisipkan otomatis; ikon kalender membuka pemilih tanggal bawaan browser. */
function InputTanggal({ teks, galat, ubah }: { teks: string; galat: boolean; ubah: (teks: string) => void }) {
  const pemilih = useRef<HTMLInputElement>(null);
  const rapikan = (v: string) => { const d = v.replace(/\D/g, "").slice(0, 8); return [d.slice(0, 2), d.slice(2, 4), d.slice(4)].filter(Boolean).join("/"); };
  const bukaKalender = () => { try { pemilih.current?.showPicker(); } catch { /* browser lama: cukup ketik manual */ } };
  return (
    <div className="relative">
      <Input aria-label="Tanggal Pengajuan" placeholder="dd/mm/yyyy" inputMode="numeric" value={teks} aria-invalid={galat || undefined}
        onChange={(e) => ubah(rapikan(e.target.value))} className={cx("pr-10", kelasGalat(galat))} />
      <input ref={pemilih} type="date" tabIndex={-1} aria-hidden className="pointer-events-none absolute bottom-0 right-0 size-px opacity-0"
        value={keIso(teks) ?? ""} onChange={(e) => ubah(keTeks(e.target.value))} />
      <button type="button" onClick={bukaKalender} title="Pilih dari kalender" aria-label="Pilih dari kalender"
        className="absolute right-1 top-1 grid size-8 place-items-center rounded text-slate-500 hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
        <CalendarDays className="size-4" aria-hidden />
      </button>
    </div>
  );
}

const Isian = ({ no, label, children }: { no: number; label: string; children: ReactNode }) => (
  <div className="space-y-1.5"><span className="block text-xs font-semibold uppercase text-slate-700">{no}. {label}</span>{children}</div>
);
