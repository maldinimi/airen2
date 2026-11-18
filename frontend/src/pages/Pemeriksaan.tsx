/** Pemeriksaan revisi (`/review/:id`, desain.md §7 no. 36, 38–40).
 *  - Label: AI (Lolos/Ditolak), Verifikator (Lolos/Ditolak), Jumlah Checklist (lolos menurut verifikator / total).
 *  - Checklist (tabel di layar lebar, kartu di layar kecil): hasil AI (alasan + bukti & rujukan yang dapat diklik ke PDF),
 *    Rujukan Checklist (Nama Acuan panduan), rekomendasi AI, Status & Catatan Verifikator.
 *  - Pengusul melihat hasil AI segera; penilaian verifikator & Keputusan Akhir setelah final (backend tidak mengirimnya
 *    sebelum itu). Tombol "Unggah Revisi" di bawah bila revisi terbaru Tidak Lolos.
 *  - Reviewer: status per item bawaan = nilai AI (atau draf tersimpan), catatan per item, Keputusan Akhir. Semua penilaian
 *    hanya ada di halaman sampai "Simpan Sebagai Draf"/"Finalkan Keputusan" — muat ulang halaman kembali ke draf terakhir. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleCheck, CircleX, Lock, Save, Upload } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { InfoProses } from "../components/Usulan";
import { waktu } from "../format";
import type { DetailReview, ItemReview, Rujukan } from "../types";
import { AreaTeks, Judul, Kartu, KonfirmasiYakin, Lencana, LencanaStatus, Memuat, Peringatan, Pilih, Tombol, cx } from "../ui";

const LOLOS = "TERPENUHI", TIDAK = "TIDAK_TERPENUHI";
type Penilaian = Record<string, { lolos: boolean; catatan: string }>;
// Status Verifikator tersimpan = override ITEM aktif (boleh sama dengan nilai AI); belum ada = null.
const statusTersimpan = (i: ItemReview) => (i.override ? i.override.nilai_sesudah === LOLOS : null);
const urlPdf = (fileId: string, judul: string, hlm?: number, bbox?: number[] | null) =>
  `/pdf/${fileId}?${new URLSearchParams({ judul, ...(hlm ? { hlm: String(hlm) } : {}), ...(bbox ? { bbox: bbox.join(",") } : {}) })}`;
const Pil = ({ kelas, children }: { kelas: string; children: ReactNode }) =>
  <span className={cx("inline-flex items-center rounded-full px-3.5 py-1 text-sm font-semibold ring-1 ring-inset", kelas)}>{children}</span>;
const LencanaItem = ({ lolos }: { lolos: boolean | null }) => lolos === null
  ? <span className="text-slate-400">—</span> : lolos
    ? <Lencana className="bg-emerald-50 text-emerald-700 ring-emerald-300">Lolos</Lencana>
    : <Lencana className="bg-red-50 text-red-700 ring-red-200">Tidak Lolos</Lencana>;

export default function Pemeriksaan() {
  const { id } = useParams();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["review", id], queryFn: () => api.get<DetailReview>(`/api/review/${id}`),
    refetchInterval: (x) => (x.state.data && ["ANTRE", "DIPROSES"].includes(x.state.data.status) ? 5000 : false),
  });
  if (q.isLoading) return <Memuat />;
  if (q.error || !q.data) return <Peringatan>{(q.error as Error)?.message ?? "Review tidak ditemukan."}</Peringatan>;
  const simpan = (d: DetailReview) => {
    qc.setQueryData(["review", id], d);
    qc.invalidateQueries({ queryKey: ["usulan"] });
    qc.invalidateQueries({ queryKey: ["riwayat"] });
  };
  // Dipasang ulang saat status review berubah (mis. AI selesai) agar penilaian awal mengikuti hasil terbaru.
  return <Isi key={`${q.data.id}:${q.data.status}`} r={q.data} simpan={simpan} />;
}

function Isi({ r, simpan }: { r: DetailReview; simpan: (d: DetailReview) => void }) {
  const ada = r.status === "SELESAI";
  const item = ada ? r.item ?? [] : [];
  const reviewer = r.tampilan === "reviewer";
  const menilai = r.boleh_override;
  const lihatVerifikator = reviewer || r.final;  // Pengusul: penilaian verifikator baru terlihat setelah final
  // Penilaian di halaman: dari draf tersimpan bila ada, selain itu mengikuti AI (status) dan kosong (catatan).
  const [penilaian, setPenilaian] = useState<Penilaian>(() => Object.fromEntries(item.map((i) =>
    [i.id, { lolos: statusTersimpan(i) ?? i.ai_terpenuhi, catatan: i.catatan_verifikator?.teks ?? "" }])));
  const [tersimpan, setTersimpan] = useState(false);
  // Kategori pilihan verifikator: bawaan = kategori final (override tersimpan) atau rekomendasi AI.
  const [kat, setKat] = useState(() => ({ id: r.kategori?.final?.id ?? r.kategori?.ai?.id ?? "",
    catatan: r.catatan?.find((c) => c.dokumen === "KATEGORI")?.teks ?? "" }));
  const ubahKat = (x: Partial<typeof kat>) => { setKat((k) => ({ ...k, ...x })); setTersimpan(false); };
  const ubahItem = (iid: string, x: Partial<Penilaian[string]>) => {
    setPenilaian((p) => ({ ...p, [iid]: { ...p[iid], ...x } }));
    setTersimpan(false);
  };
  const statusV = (i: ItemReview) => (menilai ? penilaian[i.id]?.lolos ?? null : lihatVerifikator ? statusTersimpan(i) : null);
  const catatanV = (i: ItemReview) => (menilai ? penilaian[i.id]?.catatan ?? "" : lihatVerifikator ? i.catatan_verifikator?.teks ?? "" : "");
  const rekomendasi = [...(r.rekomendasi?.TOR ?? []), ...(r.rekomendasi?.RAB ?? [])];
  // Item "TOR & RAB" bisa mendapat rekomendasi TOR dan RAB yang teksnya sama → tampilkan sekali saja.
  const rekItem = (i: ItemReview) => [...new Set(rekomendasi.filter((x) => x.item_kode === i.kode && !x.tidak_diperlukan).map((x) => x.teks.trim()))];
  const hitung = (f: (i: ItemReview) => boolean | null, nilai: boolean) => item.filter((i) => f(i) === nilai).length;
  const vLolos = hitung(statusV, true), vTolak = hitung(statusV, false);
  const catatanAkhir = r.catatan?.find((c) => c.dokumen === "UMUM");

  const selStatus = (i: ItemReview) => {
    if (menilai) return <SaklarVerifikator v={penilaian[i.id]?.lolos ?? i.ai_terpenuhi} ai={i.ai_terpenuhi} kode={i.kode} ubah={(b) => ubahItem(i.id, { lolos: b })} />;
    if (!lihatVerifikator) return <span className="text-xs text-slate-500">Menunggu verifikasi</span>;
    const v = statusTersimpan(i);
    return <><LencanaItem lolos={v} />{v !== null && v !== i.ai_terpenuhi && <p className="mt-1 text-[11px] font-medium text-amber-600">*Diubah dari AI</p>}</>;
  };
  const selCatatan = (i: ItemReview) => menilai
    ? <AreaTeks aria-label={`Catatan verifikator ${i.kode}`} rows={2} className="min-h-16" value={catatanV(i)} placeholder="Tulis catatan (opsional)"
        onChange={(e) => ubahItem(i.id, { catatan: e.target.value })} />
    : <span className="whitespace-pre-line text-slate-700">{catatanV(i) || <span className="text-slate-400">—</span>}</span>;

  const kolom: [string, string?][] = [["No"], ["Kode Checklist"], ["Checklist"], ["Kriteria Lolos"], ["Status AI"], ["Catatan AI"],
    ["Rujukan Checklist"], ["Rekomendasi AI"], ["Status Verifikator", menilai ? "(bisa diubah)" : undefined],
    ["Catatan Verifikator", menilai ? "(bisa diubah)" : undefined]];
  const td = "px-3 py-2.5 align-top";

  return (
    <div className="w-full space-y-4">
      <div>
        <Link to={`/usulan/${r.usulan.id}`} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" />Detail Usulan</Link>
        <Judul judul={`Pemeriksaan Revisi ${r.revisi.nomor}`}
          sub={`${r.usulan.kode_ro} — ${r.usulan.nama_ro}`} />
        <div className="flex items-center gap-2 text-sm text-slate-600">Status: <LencanaStatus status={r.revisi.status} /></div>
      </div>

      {!ada && (
        <Kartu className="space-y-3 p-5">
          <h2 className="font-medium">{r.status === "GAGAL" ? "Review AI gagal" : "Review AI sedang berjalan"}</h2>
          <InfoProses p={r.proses} />
        </Kartu>
      )}

      {ada && (
        <div className="flex flex-wrap items-center gap-2">
          <Pil kelas="bg-indigo-50 text-indigo-800 ring-indigo-200">AI: {hitung((i) => i.ai_terpenuhi, true)} Lolos / {hitung((i) => i.ai_terpenuhi, false)} Ditolak</Pil>
          <Pil kelas="bg-cyan-50 text-cyan-800 ring-cyan-200">Verifikator: {lihatVerifikator ? `${vLolos} Lolos / ${vTolak} Ditolak` : "Menunggu verifikasi"}</Pil>
          {lihatVerifikator && <Pil kelas="bg-slate-100 text-slate-700 ring-slate-300">Jumlah Checklist: {vLolos} / {item.length}</Pil>}
        </div>
      )}

      {item.length === 0 ? <Kartu className="px-3 py-8 text-center text-sm text-slate-500">Belum ada hasil.</Kartu> : (
        <>
          {/* Layar kecil: kartu per item. */}
          <div className="space-y-3 lg:hidden">{item.map((i, n) => (
            <Kartu key={i.id} className="space-y-3 p-4 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0"><span className="text-slate-500">{n + 1}. </span><span className="font-semibold text-slate-900">{i.kode}</span> — {i.judul}</div>
                <LencanaItem lolos={i.ai_terpenuhi} />
              </div>
              <Bidang label="Kriteria Lolos"><p className="whitespace-pre-line text-slate-600">{i.kriteria}</p></Bidang>
              <Bidang label="Catatan AI"><CatatanAI i={i} /></Bidang>
              <Bidang label="Rujukan Checklist"><RujukanChecklist i={i} /></Bidang>
              <Bidang label="Rekomendasi AI"><RekomendasiAI daftar={rekItem(i)} /></Bidang>
              <Bidang label="Status Verifikator">{selStatus(i)}</Bidang>
              <Bidang label="Catatan Verifikator">{selCatatan(i)}</Bidang>
            </Kartu>
          ))}</div>
          {/* Layar lebar: tabel. */}
          <Kartu className="hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[90rem] text-sm">
              <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
                <tr>{kolom.map(([h, sub]) => (
                  <th key={h} scope="col" className="whitespace-nowrap px-3 py-2.5 text-center">{h}
                    {sub && <span className="block text-[10px] font-medium normal-case text-utama-600">{sub}</span>}</th>))}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">{item.map((i, n) => (
                <tr key={i.id} className="hover:bg-slate-50/60">
                  <td className={cx(td, "text-center text-slate-500")}>{n + 1}</td>
                  <td className={cx(td, "whitespace-nowrap text-center font-medium text-slate-900")}>{i.kode}</td>
                  <td className={cx(td, "min-w-40 text-slate-900")}>{i.judul}</td>
                  <td className={cx(td, "min-w-56 whitespace-pre-line text-slate-600")}>{i.kriteria}</td>
                  <td className={cx(td, "text-center")}><LencanaItem lolos={i.ai_terpenuhi} /></td>
                  <td className={cx(td, "min-w-72")}><CatatanAI i={i} /></td>
                  <td className={cx(td, "min-w-44")}><RujukanChecklist i={i} /></td>
                  <td className={cx(td, "min-w-56 text-slate-700")}><RekomendasiAI daftar={rekItem(i)} /></td>
                  <td className={cx(td, "min-w-48 text-center")}>{selStatus(i)}</td>
                  <td className={cx(td, "min-w-64")}>{selCatatan(i)}</td>
                </tr>
              ))}</tbody>
            </table>
          </Kartu>
        </>
      )}

      {ada && r.kategori && <TabelKategori r={r} menilai={menilai} lihatVerifikator={lihatVerifikator} kat={kat} ubahKat={ubahKat} />}
      {menilai && ada && <KeputusanAkhir r={r} item={item} penilaian={penilaian} kat={kat} simpan={simpan} awalCatatan={catatanAkhir?.teks ?? ""}
        tersimpan={tersimpan} setTersimpan={setTersimpan} />}
      {r.final && <HasilAkhir lolos={r.label!.final === "LOLOS"} oleh={r.difinalkan_oleh} at={r.difinalkan_at} catatan={catatanAkhir?.teks} />}
      {r.boleh_unggah_revisi && (
        <div className="flex justify-end">
          <Link to={`/usulan/${r.usulan.id}/ubah`}><Tombol><Upload className="size-4" />Unggah Revisi</Tombol></Link>
        </div>
      )}
    </div>
  );
}

const Bidang = ({ label, children }: { label: string; children: ReactNode }) => (
  <div><div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>{children}</div>
);

/** Alasan AI apa adanya, lalu bukti & rujukannya. */
function CatatanAI({ i }: { i: ItemReview }) {
  return (
    <div className="space-y-1 text-slate-700">
      {i.alasan && <p className="whitespace-pre-line">{i.alasan}</p>}
      {i.yang_kurang && <p className="whitespace-pre-line">{i.yang_kurang}</p>}
      <BuktiRujukan rujukan={i.rujukan} />
    </div>
  );
}

/** Panduan (Nama Acuan) yang dipakai menilai item, satu kali per file, tertaut ke PDF-nya. */
function RujukanChecklist({ i }: { i: ItemReview }) {
  const acuan = [...new Map(i.rujukan.filter((x) => x.dokumen === "PANDUAN").map((x) => [x.file_id, x])).values()];
  if (!acuan.length) return <span className="text-slate-400">—</span>;
  return (
    <ul className="space-y-1">{acuan.map((x) => (
      <li key={x.file_id}><Link to={urlPdf(x.file_id, x.nama_acuan ?? "Panduan")} className="text-utama-600 hover:underline">{x.nama_acuan}</Link></li>))}</ul>
  );
}

const RekomendasiAI = ({ daftar }: { daftar: string[] }) => daftar.length
  ? <ul className="list-disc space-y-1 pl-4">{daftar.map((t) => <li key={t}>{t}</li>)}</ul> : <span className="text-slate-400">—</span>;

/** Saklar Lolos/Tidak Lolos per item + keterangan apakah sama dengan AI. Perubahan tersimpan lewat Simpan Sebagai Draf/Finalkan. */
function SaklarVerifikator({ v, ai, kode, ubah }: { v: boolean; ai: boolean; kode: string; ubah: (b: boolean) => void }) {
  const tombol = "inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";
  return (
    <div className="inline-flex flex-col items-center gap-1">
      <div role="radiogroup" aria-label={`Status verifikator ${kode}`} className="inline-flex gap-1 rounded-full border border-slate-200 bg-white p-0.5">
        <button type="button" role="radio" aria-checked={v} title="Tetapkan Lolos" onClick={() => ubah(true)}
          className={cx(tombol, v ? "bg-emerald-600 text-white shadow-sm" : "text-emerald-700 hover:bg-emerald-50")}><CircleCheck className="size-3.5" aria-hidden />Lolos</button>
        <button type="button" role="radio" aria-checked={!v} title="Tetapkan Tidak Lolos" onClick={() => ubah(false)}
          className={cx(tombol, !v ? "bg-red-600 text-white shadow-sm" : "text-red-600 hover:bg-red-50")}><CircleX className="size-3.5" aria-hidden />Tidak Lolos</button>
      </div>
      <p className={cx("text-[11px] font-medium", v === ai ? "text-slate-500" : "text-amber-600")}>{v === ai ? "Sesuai AI" : "*Diubah dari AI"}</p>
    </div>
  );
}

/** Bukti (TOR/RAB) & dasar panduan; klik membuka PDF di halaman tersebut dengan bagian yang dirujuk disorot (E3). */
function BuktiRujukan({ rujukan }: { rujukan: Rujukan[] }) {
  if (!rujukan.length) return null;
  return (
    <div className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Bukti & rujukan</div>
      {rujukan.map((x) => (
        <div key={x.id} className="text-xs">
          <Link to={urlPdf(x.file_id, `${x.dokumen === "PANDUAN" ? "Panduan" : x.dokumen} — ${x.judul_dokumen}`, x.halaman, x.bbox)}
            className="font-medium text-utama-600 hover:underline">
            {x.peran === "dasar_panduan" ? "Dasar" : "Bukti"}: {x.dokumen === "PANDUAN" ? x.nama_acuan : x.dokumen} hlm {x.halaman}
          </Link>
          <span className="text-slate-500"> · {x.label_lokasi}</span>
          <q className="mt-0.5 line-clamp-3 block italic text-slate-600">{x.kutipan}</q>
        </div>
      ))}
    </div>
  );
}

type PilihanKategori = { id: string; catatan: string };

/** Tabel Kategori: kategori pilihan Pengusul, rekomendasi AI (Screening 2) + alasan & rujukan, dan pilihan/catatan verifikator. */
function TabelKategori({ r, menilai, lihatVerifikator, kat, ubahKat }: {
  r: DetailReview; menilai: boolean; lihatVerifikator: boolean; kat: PilihanKategori; ubahKat: (x: Partial<PilihanKategori>) => void;
}) {
  const k = r.kategori!;
  const nama = (x: { kode: string; nama: string } | null | undefined) => (x ? `${x.kode} — ${x.nama}` : "—");
  const catatanTersimpan = r.catatan?.find((c) => c.dokumen === "KATEGORI")?.teks;
  const verifikator = menilai ? (
    <div className="space-y-1">
      <Pilih aria-label="Kategori verifikator" value={kat.id} onChange={(e) => ubahKat({ id: e.target.value })}>
        {k.pilihan.map((x) => <option key={x.id} value={x.id}>{nama(x)}</option>)}
      </Pilih>
      <p className={cx("text-[11px] font-medium", kat.id === k.ai?.id ? "text-slate-500" : "text-amber-600")}>
        {kat.id === k.ai?.id ? "Sesuai AI" : "*Diubah dari AI"}</p>
    </div>
  ) : lihatVerifikator ? (
    <>{nama(k.final)}{k.diubah && <p className="mt-1 text-[11px] font-medium text-amber-600">*Diubah dari AI</p>}</>
  ) : <span className="text-xs text-slate-500">Menunggu verifikasi</span>;
  const catatan = menilai
    ? <AreaTeks aria-label="Catatan verifikator kategori" rows={2} className="min-h-16" value={kat.catatan} placeholder="Tulis catatan (opsional)"
        onChange={(e) => ubahKat({ catatan: e.target.value })} />
    : <span className="whitespace-pre-line text-slate-700">{(lihatVerifikator && catatanTersimpan) || <span className="text-slate-400">—</span>}</span>;
  const catatanAi = <div className="space-y-1 text-slate-700">{k.alasan && <p className="whitespace-pre-line">{k.alasan}</p>}<BuktiRujukan rujukan={k.rujukan} /></div>;
  const kolom: [string, ReactNode][] = [["Kategori Usulan", nama(r.usulan.kategori_usulan)], ["AI", nama(k.ai)], ["Catatan AI", catatanAi],
    ["Verifikator", verifikator], ["Catatan Verifikator", catatan]];
  return (
    <Kartu className="space-y-3 p-5">
      <h2 className="font-semibold text-slate-900">Kategori</h2>
      {/* Layar kecil: bidang bertumpuk; layar lebar: tabel. */}
      <div className="space-y-3 text-sm lg:hidden">{kolom.map(([h, isi]) => <Bidang key={h} label={h}>{isi}</Bidang>)}</div>
      <div className="hidden overflow-x-auto rounded-lg border border-slate-200 lg:block">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
            <tr>{kolom.map(([h]) => <th key={h} scope="col" className="whitespace-nowrap px-3 py-2.5 text-center">{h}
              {menilai && h.includes("Verifikator") && <span className="block text-[10px] font-medium normal-case text-utama-600">(bisa diubah)</span>}</th>)}</tr>
          </thead>
          <tbody><tr>{kolom.map(([h, isi]) => (
            <td key={h} className={cx("px-3 py-2.5 align-top", h === "Catatan AI" ? "min-w-72" : h === "Catatan Verifikator" ? "min-w-64" : "min-w-44")}>{isi}</td>))}</tr></tbody>
        </table>
      </div>
    </Kartu>
  );
}

function KeputusanAkhir({ r, item, penilaian, kat, simpan, awalCatatan, tersimpan, setTersimpan }: {
  r: DetailReview; item: ItemReview[]; penilaian: Penilaian; kat: PilihanKategori; simpan: (d: DetailReview) => void; awalCatatan: string;
  tersimpan: boolean; setTersimpan: (b: boolean) => void;
}) {
  // Bawaan: label draf tersimpan bila verifikator pernah memilih berbeda; selain itu mengikuti status item di halaman.
  const [pilihan, setPilihan] = useState<"LOLOS" | "TIDAK_LOLOS" | null>(null);
  const label = pilihan ?? (r.label!.diubah ? r.label!.final as "LOLOS" | "TIDAK_LOLOS"
    : item.every((i) => penilaian[i.id]?.lolos) ? "LOLOS" : "TIDAK_LOLOS");
  const [catatan, setCatatan] = useState(awalCatatan);
  const [periksa, setPeriksa] = useState(false);
  const badan = () => ({ label, catatan, kategori_id: kat.id || null, catatan_kategori: kat.catatan, item: item.map((i) => ({
    checklist_item_id: i.id, nilai: penilaian[i.id].lolos ? LOLOS : TIDAK, catatan: penilaian[i.id].catatan })) });
  const final = useMutation({
    mutationFn: () => api.post<DetailReview>(`/api/review/${r.id}/finalkan`, badan()),
    onSuccess: (d) => { setPeriksa(false); simpan(d); },
  });
  const draf = useMutation({ mutationFn: () => api.put<DetailReview>(`/api/review/${r.id}/keputusan`, badan()),
    onSuccess: (d) => { simpan(d); setTersimpan(true); } });
  return (
    <Kartu className="space-y-4 p-5">
      <h2 className="font-semibold text-slate-900">Keputusan Akhir</h2>
      <div role="radiogroup" aria-label="Keputusan akhir" className="inline-flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">
        {(["LOLOS", "TIDAK_LOLOS"] as const).map((x) => {
          const Ikon = x === "LOLOS" ? CircleCheck : CircleX;
          return (
            <button key={x} type="button" role="radio" aria-checked={label === x} onClick={() => { setPilihan(x); setTersimpan(false); }}
              className={cx("inline-flex items-center gap-1.5 rounded-lg px-5 py-2 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100",
                label === x ? (x === "LOLOS" ? "bg-emerald-600 text-white shadow-sm" : "bg-red-600 text-white shadow-sm")
                  : x === "LOLOS" ? "text-emerald-700 hover:bg-white" : "text-red-700 hover:bg-white")}>
              <Ikon className="size-4" aria-hidden />{x === "LOLOS" ? "LOLOS" : "TIDAK LOLOS"}
            </button>
          );
        })}
      </div>
      <label className="block space-y-1.5"><span className="text-sm font-medium text-slate-700">Catatan akhir</span>
        <AreaTeks rows={4} value={catatan} onChange={(e) => { setCatatan(e.target.value); setTersimpan(false); }} placeholder="Catatan untuk Pengusul" /></label>
      {tersimpan && <Peringatan jenis="sukses">Draf penilaian tersimpan.</Peringatan>}
      {draf.error && <Peringatan>{(draf.error as Error).message}</Peringatan>}
      <div className="flex flex-wrap justify-end gap-2">
        <Tombol varian="sekunder" memuat={draf.isPending} onClick={() => draf.mutate()}><Save className="size-4" />Simpan Sebagai Draf</Tombol>
        <Tombol onClick={() => { final.reset(); setPeriksa(true); }}><Lock className="size-4" />Finalkan Keputusan</Tombol>
      </div>
      <KonfirmasiYakin buka={periksa} batal={() => setPeriksa(false)} ya={() => final.mutate()} memuat={final.isPending}
        galat={final.error ? (final.error as Error).message : null} />
    </Kartu>
  );
}

function HasilAkhir({ lolos, oleh, at, catatan }: { lolos: boolean; oleh: string | null; at: string | null; catatan?: string }) {
  const Ikon = lolos ? CircleCheck : CircleX;
  return (
    <Kartu className="space-y-3 p-5">
      <h2 className="font-semibold text-slate-900">Keputusan Akhir</h2>
      <div className="flex flex-wrap items-center gap-2">
        <Ikon className={cx("size-6", lolos ? "text-emerald-600" : "text-red-600")} aria-hidden />
        <span className={cx("text-lg font-semibold", lolos ? "text-emerald-700" : "text-red-700")}>{lolos ? "LOLOS" : "TIDAK LOLOS"}</span>
        <span className="text-sm text-slate-500">oleh {oleh ?? "—"} · {waktu(at)}</span>
      </div>
      <div><div className="text-xs font-medium text-slate-500">Catatan akhir</div>
        <p className="whitespace-pre-line text-sm text-slate-800">{catatan || "—"}</p></div>
    </Kartu>
  );
}
