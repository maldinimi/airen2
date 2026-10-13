import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, qs } from "../api";
import { useAuth } from "../auth";
import { AksiUsulan, InfoProses, RingkasanChecklist } from "../components/Usulan";
import { tanggal } from "../format";
import type { BarisUsulan, Satker } from "../types";
import { Halaman, Input, Judul, Kartu, Kosong, LencanaKategori, LencanaStatus, Memuat, Peringatan, Pilih, Tombol } from "../ui";

type Opsi = { satker: Satker[]; tahun: number[]; kategori: string[]; status: { kode: string; nama: string }[] };

export default function UsulanList() {
  const { punya } = useAuth();
  const [sp, setSp] = useSearchParams();
  const f = Object.fromEntries(sp.entries());
  const ubah = (k: string, v: string) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); if (k !== "halaman") n.delete("halaman"); setSp(n, { replace: true }); };
  const [cari, setCari] = useState(f.q ?? "");
  const opsi = useQuery({ queryKey: ["opsi-filter"], queryFn: () => api.get<Opsi>("/api/usulan/opsi/filter") });
  const data = useQuery({
    queryKey: ["usulan", f],
    queryFn: () => api.get<{ total: number; halaman: number; per_halaman: number; data: BarisUsulan[] }>(`/api/usulan${qs({ ...f, arsip: f.arsip === "1" })}`),
    refetchInterval: (q) => (q.state.data?.data.some((u) => ["ANTRE", "DIPROSES_AI"].includes(u.status)) ? 5000 : false),
  });

  return (
    <div>
      <Judul judul="Daftar Usulan" sub="Status yang ditampilkan adalah status revisi terbaru."
        aksi={punya("PENGUSUL") && <Link to="/usulan/baru"><Tombol><Plus className="size-4" />Buat Usulan</Tombol></Link>} />
      <Kartu className="mb-4 grid gap-3 p-3 sm:grid-cols-2 lg:grid-cols-6">
        <form className="relative lg:col-span-2" onSubmit={(e) => { e.preventDefault(); ubah("q", cari); }}>
          <Search className="absolute left-3 top-3 size-4 text-slate-400" aria-hidden />
          <Input className="pl-9" placeholder="Cari kode/nama RO…" value={cari} onChange={(e) => setCari(e.target.value)} aria-label="Cari RO" />
        </form>
        <Pilih aria-label="Filter Satker" value={f.satker_id ?? ""} onChange={(e) => ubah("satker_id", e.target.value)}>
          <option value="">Semua Satker</option>{opsi.data?.satker.map((s) => <option key={s.id} value={s.id}>{s.nama}</option>)}
        </Pilih>
        <Pilih aria-label="Filter tahun" value={f.tahun ?? ""} onChange={(e) => ubah("tahun", e.target.value)}>
          <option value="">Semua tahun</option>{opsi.data?.tahun.map((t) => <option key={t}>{t}</option>)}
        </Pilih>
        <Pilih aria-label="Filter status" value={f.status ?? ""} onChange={(e) => ubah("status", e.target.value)}>
          <option value="">Semua status</option>{opsi.data?.status.map((s) => <option key={s.kode} value={s.kode}>{s.nama}</option>)}
        </Pilih>
        <Pilih aria-label="Filter kategori" value={f.kategori ?? ""} onChange={(e) => ubah("kategori", e.target.value)}>
          <option value="">Semua kategori</option>{opsi.data?.kategori.map((k) => <option key={k}>{k}</option>)}
        </Pilih>
        <label className="flex items-center gap-2 text-sm text-slate-600 lg:col-span-6">
          <input type="checkbox" checked={f.arsip === "1"} onChange={(e) => ubah("arsip", e.target.checked ? "1" : "")} /> Tampilkan arsip
        </label>
      </Kartu>

      {data.isLoading ? <Memuat /> : data.error ? <Peringatan>{(data.error as Error).message}</Peringatan> : !data.data?.data.length ? (
        <Kosong>Belum ada usulan{punya("PENGUSUL") && <> — <Link className="text-utama-600 underline" to="/usulan/baru">buat usulan pertama</Link></>}.</Kosong>
      ) : (
        <>
          {/* Desktop: tabel */}
          <Kartu className="hidden overflow-x-auto lg:block">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>{["Satker", "TA", "RO", "Dokumen", "Rev.", "Status", "Checklist", "Kategori", "Diperbarui", "Aksi"].map((h) => <th key={h} className="px-3 py-2.5 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.data.data.map((u) => (
                  <tr key={u.id} className="align-top hover:bg-slate-50/60">
                    <td className="px-3 py-3">{u.satker.nama}</td>
                    <td className="px-3 py-3">{u.tahun_anggaran}</td>
                    <td className="max-w-56 px-3 py-3"><div className="font-medium text-slate-900">{u.kode_ro}</div><div className="text-slate-500">{u.nama_ro}</div></td>
                    <td className="max-w-48 px-3 py-3 text-xs">
                      <Link className="block truncate text-utama-600 hover:underline" to={`/pdf/${u.tor.file_id}?judul=${encodeURIComponent("TOR — " + u.tor.nama)}`} title={u.tor.nama}>TOR: {u.tor.nama}</Link>
                      <Link className="block truncate text-utama-600 hover:underline" to={`/pdf/${u.rab.file_id}?judul=${encodeURIComponent("RAB — " + u.rab.nama)}`} title={u.rab.nama}>RAB: {u.rab.nama}</Link>
                    </td>
                    <td className="px-3 py-3 text-center">{u.revisi_nomor}</td>
                    <td className="min-w-40 space-y-1.5 px-3 py-3"><LencanaStatus status={u.status} /><InfoProses p={u.proses} /></td>
                    <td className="px-3 py-3"><RingkasanChecklist c={u.checklist} /></td>
                    <td className="px-3 py-3"><LencanaKategori k={u.kategori_final} /></td>
                    <td className="whitespace-nowrap px-3 py-3 text-slate-500">{tanggal(u.updated_at)}</td>
                    <td className="px-3 py-3"><AksiUsulan u={u} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Kartu>
          {/* Tablet/ponsel: kartu */}
          <div className="space-y-3 lg:hidden">
            {data.data.data.map((u) => (
              <Kartu key={u.id} className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div><div className="font-medium text-slate-900">{u.kode_ro} · {u.nama_ro}</div>
                    <div className="text-xs text-slate-500">{u.satker.nama} · TA {u.tahun_anggaran} · Revisi {u.revisi_nomor} · {tanggal(u.updated_at)}</div></div>
                  <LencanaStatus status={u.status} />
                </div>
                <InfoProses p={u.proses} />
                <div className="flex flex-wrap items-center gap-2 text-sm"><RingkasanChecklist c={u.checklist} /><LencanaKategori k={u.kategori_final} /></div>
                <div className="flex flex-wrap gap-3 text-xs">
                  <Link className="text-utama-600 underline" to={`/pdf/${u.tor.file_id}?judul=${encodeURIComponent("TOR — " + u.tor.nama)}`}>TOR</Link>
                  <Link className="text-utama-600 underline" to={`/pdf/${u.rab.file_id}?judul=${encodeURIComponent("RAB — " + u.rab.nama)}`}>RAB</Link>
                </div>
                <AksiUsulan u={u} />
              </Kartu>
            ))}
          </div>
          <Halaman total={data.data.total} halaman={data.data.halaman} per={data.data.per_halaman} ubah={(h) => ubah("halaman", String(h))} />
        </>
      )}
    </div>
  );
}
