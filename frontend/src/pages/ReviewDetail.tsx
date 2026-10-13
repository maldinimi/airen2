/** Detail Review (desain §5.3): hasil Screening 1 & 2, rujukan yang dapat diklik ke PDF, override, catatan, finalisasi. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BookOpen, Check, ChevronDown, ExternalLink, History, Lock, Pencil, RotateCcw, X } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import PdfViewer, { type Sorotan } from "../components/PdfViewer";
import { InfoProses } from "../components/Usulan";
import { waktu } from "../format";
import type { DetailReview, ItemReview, Override, Rekomendasi, Rujukan } from "../types";
import { AreaTeks, Dialog, Kartu, Kolom, Lencana, LencanaKategori, LencanaLabel, LencanaStatus, Memuat, Peringatan, Pilih, Tab,
  TandaAI, TandaUbah, Tombol, cx } from "../ui";

type Panel = { fileId: string; judul: string; sorot: Sorotan };
type TabNama = "checklist" | "tor" | "rab" | "catatan" | "dokumen" | "override";

const infoOverride = (o: Override | null) => (o ? `Diubah oleh ${o.oleh}, ${waktu(o.at)}. Alasan: ${o.alasan}` : undefined);

export default function ReviewDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["review", id], queryFn: () => api.get<DetailReview>(`/api/review/${id}`),
    refetchInterval: (x) => (x.state.data && ["ANTRE", "DIPROSES"].includes(x.state.data.status) ? 5000 : false),
  });
  const [panel, setPanel] = useState<Panel | null>(null);
  const [tab, setTab] = useState<TabNama>("checklist");
  const [dialog, setDialog] = useState<{ target: "ITEM" | "LABEL" | "KATEGORI"; item?: ItemReview } | null>(null);
  const [finalkan, setFinalkan] = useState(false);
  const layarKecil = useLayarKecil();
  const r = q.data;

  useEffect(() => { if (r && !panel) setPanel({ fileId: r.revisi.tor.file_id, judul: `TOR — ${r.revisi.tor.nama}`, sorot: null }); }, [r, panel]);

  const simpan = (d: DetailReview) => qc.setQueryData(["review", id], d);
  const batal = useMutation({ mutationFn: (oid: string) => api.post<DetailReview>(`/api/override/${oid}/batal`), onSuccess: simpan,
    onError: (e) => alert((e as Error).message) });

  if (q.isLoading) return <Memuat />;
  if (q.error || !r) return <Peringatan>{(q.error as Error)?.message ?? "Review tidak ditemukan."}</Peringatan>;

  const buka = (x: Rujukan) => {
    setPanel({ fileId: x.file_id, judul: `${x.dokumen === "PANDUAN" ? "Panduan" : x.dokumen} — ${x.judul_dokumen}`, sorot: { halaman: x.halaman, bbox: x.bbox } });
    if (layarKecil) setTab("dokumen");
  };
  const bukaDok = (fileId: string, judul: string) => { setPanel({ fileId, judul, sorot: null }); if (layarKecil) setTab("dokumen"); };
  const reviewer = r.boleh_override;
  const devModel = r.model_info && r.model_info.profil !== "prod";

  const kepala = (
    <div className="mb-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Link to="/usulan" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />Usulan</Link>
        <span className="text-sm text-slate-400">/</span>
        <h1 className="text-lg font-semibold text-slate-900">{r.usulan.kode_ro} · {r.usulan.nama_ro}</h1>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
        <span>{r.usulan.satker} · TA {r.usulan.tahun_anggaran} · Revisi {r.revisi.nomor}</span>
        <LencanaStatus status={r.revisi.status} />
        {devModel && <Lencana className="bg-orange-50 text-orange-700 ring-orange-300" title={r.model_info?.model}>Model {r.model_info?.profil === "tiruan" ? "AI tiruan" : "development"}</Lencana>}
        <div className="ml-auto flex gap-2">
          <Link to={`/usulan/${r.usulan.id}/riwayat`}><Tombol varian="sekunder" kecil><History className="size-4" />Riwayat</Tombol></Link>
          {reviewer && r.status === "SELESAI" && <Tombol kecil onClick={() => setFinalkan(true)}><Lock className="size-4" />Finalkan</Tombol>}
        </div>
      </div>
      {r.status === "SELESAI" && (r.final
        ? <Peringatan jenis="info">Hasil final — difinalkan oleh {r.difinalkan_oleh} pada {waktu(r.difinalkan_at)}. Nilai AI tetap ditampilkan sebagai pembanding.</Peringatan>
        : r.tampilan === "pengusul"
          ? <Peringatan jenis="warn"><b>Hasil AI — belum diverifikasi reviewer.</b> Hasil final dapat berbeda setelah diperiksa reviewer.</Peringatan>
          : reviewer ? null : <Peringatan jenis="warn">Hasil AI menunggu verifikasi reviewer.</Peringatan>)}
      {r.disalin_dari_revisi && <Peringatan jenis="info">Dokumen dan acuan identik dengan revisi ke-{r.disalin_dari_revisi}; hasil AI disalin agar konsisten.</Peringatan>}
    </div>
  );

  if (r.status !== "SELESAI") {
    return (
      <div className="max-w-2xl">{kepala}
        <Kartu className="space-y-3 p-5">
          <h2 className="font-medium">{r.status === "GAGAL" ? "Review AI gagal" : "Review AI sedang berjalan"}</h2>
          <InfoProses p={r.proses} />
          {r.status !== "GAGAL" && <p className="text-sm text-slate-500">Anda dapat meninggalkan halaman ini; proses tetap berjalan di latar belakang.</p>}
        </Kartu>
      </div>
    );
  }

  const item = r.item!, label = r.label!, kat = r.kategori!;
  const panelPdf = panel && <PdfViewer key={panel.fileId} fileId={panel.fileId} judul={panel.judul} sorot={panel.sorot} />;

  return (
    <div>
      {kepala}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-4">
          {/* Ringkasan: label & kategori */}
          <Kartu className="divide-y divide-slate-100">
            <div className="flex flex-wrap items-center gap-3 p-4">
              <span className="w-20 text-xs font-semibold uppercase text-slate-500">Label</span>
              <LencanaLabel label={label.final} />
              {label.diubah ? <><TandaUbah title={infoOverride(label.override)} /><span className="text-xs text-slate-400 line-through">AI: {label.ai.replace("_", " ")}</span></> : <TandaAI />}
              <span className="text-sm text-slate-600">{label.terpenuhi}/{label.total} item terpenuhi</span>
              {reviewer && (
                <span className="ml-auto flex gap-1">
                  {label.override && <Tombol varian="hantu" kecil onClick={() => batal.mutate(label.override!.id)}><RotateCcw className="size-3.5" />Batalkan</Tombol>}
                  <Tombol varian="hantu" kecil className="text-ubah-700" onClick={() => setDialog({ target: "LABEL" })}><Pencil className="size-3.5" />Override</Tombol>
                </span>
              )}
              {label.tidak_konsisten && <div className="w-full"><Peringatan jenis="warn">Label akhir tidak konsisten dengan status checklist (hitungan checklist: {label.hitung.replace("_", " ")}).</Peringatan></div>}
            </div>
            <div className="space-y-2 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="w-20 text-xs font-semibold uppercase text-slate-500">Kategori</span>
                <LencanaKategori k={kat.final} />
                {kat.diubah ? <><TandaUbah title={infoOverride(kat.override)} /><span className="text-xs text-slate-400 line-through">AI: {kat.ai?.kode}</span></> : <TandaAI />}
                <span className="text-sm text-slate-600">{kat.final?.nama}</span>
                {reviewer && (
                  <span className="ml-auto flex gap-1">
                    {kat.override && <Tombol varian="hantu" kecil onClick={() => batal.mutate(kat.override!.id)}><RotateCcw className="size-3.5" />Batalkan</Tombol>}
                    <Tombol varian="hantu" kecil className="text-ubah-700" onClick={() => setDialog({ target: "KATEGORI" })}><Pencil className="size-3.5" />Override</Tombol>
                  </span>
                )}
              </div>
              <Lipat judul={`Alasan AI (kategori ${kat.ai?.kode})`}>
                <p className="whitespace-pre-line text-sm text-slate-700">{kat.alasan}</p>
                <DaftarRujukan rujukan={kat.rujukan} buka={buka} />
              </Lipat>
              {kat.override && <p className="text-xs text-ubah-700">Alasan override: {kat.override.alasan} — {kat.override.oleh}</p>}
            </div>
            <div className="p-4 text-xs text-slate-500">
              <span className="font-semibold uppercase">Acuan</span>: Checklist v{r.acuan!.checklist_versi.nomor} · Kategori v{r.acuan!.kategori_versi.nomor} · {r.acuan!.panduan.length} panduan
              <Lipat judul="Lihat panduan yang dipakai">
                <ul className="space-y-1">{r.acuan!.panduan.map((p) => (
                  <li key={p.file_id}><button className="text-left text-utama-600 hover:underline" onClick={() => bukaDok(p.file_id, `Panduan — ${p.judul}`)}>{p.judul} (v{p.nomor})</button></li>
                ))}{!r.acuan!.panduan.length && <li>Tidak ada panduan aktif saat review.</li>}</ul>
              </Lipat>
              <div className="mt-2 flex flex-wrap gap-3">
                <button className="text-utama-600 hover:underline" onClick={() => bukaDok(r.revisi.tor.file_id, `TOR — ${r.revisi.tor.nama}`)}>Buka TOR</button>
                <button className="text-utama-600 hover:underline" onClick={() => bukaDok(r.revisi.rab.file_id, `RAB — ${r.revisi.rab.nama}`)}>Buka RAB</button>
              </div>
            </div>
          </Kartu>

          <Tab<TabNama> aktif={tab} ubah={setTab} pilihan={[
            { nilai: "checklist", label: `Checklist (${label.terpenuhi}/${label.total})` },
            { nilai: "tor", label: "Rekomendasi TOR" },
            { nilai: "rab", label: "Rekomendasi RAB" },
            ...(r.tampilan === "reviewer" || r.final ? [{ nilai: "catatan" as const, label: "Catatan Reviewer" }] : []),
            ...(r.riwayat_override?.length ? [{ nilai: "override" as const, label: "Riwayat Override" }] : []),
            ...(layarKecil ? [{ nilai: "dokumen" as const, label: "Dokumen" }] : []),
          ]} />

          {tab === "checklist" && <div className="space-y-3">{item.map((i) => (
            <KartuItem key={i.id} i={i} reviewer={reviewer} buka={buka} override={() => setDialog({ target: "ITEM", item: i })}
              batal={() => i.override && batal.mutate(i.override.id)} />))}</div>}
          {tab === "tor" && <DaftarRekomendasi rek={r.rekomendasi!.TOR} buka={buka} />}
          {tab === "rab" && <DaftarRekomendasi rek={r.rekomendasi!.RAB} buka={buka} />}
          {tab === "catatan" && <Catatan r={r} simpan={simpan} />}
          {tab === "override" && <RiwayatOverride r={r} />}
          {tab === "dokumen" && <div className="h-[75vh] overflow-hidden rounded-xl border border-slate-200 xl:hidden">{panelPdf}</div>}
        </div>

        <div className="hidden xl:block">
          <div className="sticky top-0 h-[calc(100vh-8rem)] overflow-hidden rounded-xl border border-slate-200 bg-white">{panelPdf}</div>
        </div>
      </div>

      {dialog && <DialogOverride r={r} d={dialog} tutup={() => setDialog(null)} simpan={simpan} />}
      <DialogFinalkan r={r} buka={finalkan} ubahBuka={setFinalkan} simpan={simpan} />
    </div>
  );
}

/** Di bawah 1280px panel PDF menjadi tab "Dokumen" (desain §5.3: ponsel/tablet). */
function useLayarKecil() {
  const [mq] = useState(() => window.matchMedia("(max-width: 1279px)"));
  const [kecil, setKecil] = useState(mq.matches);
  useEffect(() => {
    const ubah = (e: MediaQueryListEvent) => setKecil(e.matches);
    mq.addEventListener("change", ubah);
    return () => mq.removeEventListener("change", ubah);
  }, [mq]);
  return kecil;
}

function Lipat({ judul, children }: { judul: string; children: ReactNode }) {
  const [buka, setBuka] = useState(false);
  return (
    <div>
      <button className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800" onClick={() => setBuka(!buka)} aria-expanded={buka}>
        <ChevronDown className={cx("size-3.5 transition-transform", buka && "rotate-180")} />{judul}
      </button>
      {buka && <div className="mt-2 space-y-2">{children}</div>}
    </div>
  );
}

function TautanRujukan({ x, buka }: { x: Rujukan; buka: (x: Rujukan) => void }) {
  const panduan = x.peran === "dasar_panduan";
  return (
    <button onClick={() => buka(x)} className={cx("block w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:border-utama-500 hover:bg-utama-50",
      panduan ? "border-sky-200 bg-sky-50/50" : "border-slate-200 bg-slate-50/60")}>
      <span className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-slate-600">
        {panduan ? <BookOpen className="size-3.5 text-sky-700" /> : <ExternalLink className="size-3.5 text-utama-600" />}
        <span className="text-slate-900">{x.dokumen === "PANDUAN" ? x.judul_dokumen : x.dokumen}</span> hlm {x.halaman} · {x.label_lokasi}
        {x.sumber === "vlm" && <Lencana className="bg-orange-50 text-orange-700 ring-orange-200">deskripsi gambar oleh AI</Lencana>}
        {x.sumber === "ocr" && <Lencana className="bg-slate-100 text-slate-600 ring-slate-200">hasil OCR</Lencana>}
      </span>
      <span className="mt-1 block text-slate-700">“{x.kutipan.length > 400 ? x.kutipan.slice(0, 400) + "…" : x.kutipan}”</span>
    </button>
  );
}

function DaftarRujukan({ rujukan, buka }: { rujukan: Rujukan[]; buka: (x: Rujukan) => void }) {
  const bukti = rujukan.filter((x) => x.peran === "bukti_dokumen");
  const dasar = rujukan.filter((x) => x.peran === "dasar_panduan");
  return (
    <div className="space-y-2">
      {bukti.length > 0 && <div className="space-y-1.5"><div className="text-xs font-semibold text-slate-500">Bukti dokumen</div>{bukti.map((x) => <TautanRujukan key={x.id} x={x} buka={buka} />)}</div>}
      {dasar.length > 0 && <div className="space-y-1.5"><div className="text-xs font-semibold text-slate-500">Dasar panduan</div>{dasar.map((x) => <TautanRujukan key={x.id} x={x} buka={buka} />)}</div>}
    </div>
  );
}

function KartuItem({ i, reviewer, buka, override, batal }: { i: ItemReview; reviewer: boolean; buka: (x: Rujukan) => void; override: () => void; batal: () => void }) {
  const [buka_, setBuka] = useState(!i.terpenuhi);
  return (
    <Kartu className={cx("p-4", i.diubah && "ring-2 ring-ubah-600/30")}>
      <button className="flex w-full items-start gap-3 text-left" onClick={() => setBuka(!buka_)} aria-expanded={buka_}>
        {i.terpenuhi ? <Check className="mt-0.5 size-5 shrink-0 rounded-full bg-emerald-100 p-0.5 text-emerald-700" aria-label="Terpenuhi" />
          : <X className="mt-0.5 size-5 shrink-0 rounded-full bg-red-100 p-0.5 text-red-700" aria-label="Tidak terpenuhi" />}
        <span className="min-w-0 flex-1">
          <span className="font-medium text-slate-900">{i.kode}. {i.judul}</span>
          <span className="ml-2 inline-flex flex-wrap gap-1 align-middle">
            <span className={cx("text-xs font-medium", i.terpenuhi ? "text-emerald-700" : "text-red-700")}>{i.terpenuhi ? "Terpenuhi" : "Tidak terpenuhi"}</span>
            {i.diubah ? <><TandaUbah title={infoOverride(i.override)} /><span className="text-xs text-slate-400 line-through">AI: {i.ai_terpenuhi ? "terpenuhi" : "tidak terpenuhi"}</span></> : <TandaAI />}
            <Lencana className="bg-white text-slate-500 ring-slate-200">{i.berlaku_untuk === "KEDUANYA" ? "TOR & RAB" : i.berlaku_untuk}</Lencana>
          </span>
        </span>
        <ChevronDown className={cx("size-4 shrink-0 text-slate-400 transition-transform", buka_ && "rotate-180")} />
      </button>
      {buka_ && (
        <div className="mt-3 space-y-3 pl-8 text-sm">
          <p className="text-xs text-slate-500">Kriteria: {i.kriteria}</p>
          <p><span className="font-medium">Alasan AI:</span> <span className="whitespace-pre-line">{i.alasan}</span></p>
          {i.yang_kurang && <p className="text-red-800"><span className="font-medium">Yang kurang:</span> {i.yang_kurang}</p>}
          {!i.ditemukan && <Peringatan jenis="warn">Tidak ditemukan di dokumen.</Peringatan>}
          {i.override && <p className="rounded-lg bg-ubah-50 px-3 py-2 text-xs text-ubah-700">Override: {infoOverride(i.override)}</p>}
          <DaftarRujukan rujukan={i.rujukan} buka={buka} />
          {reviewer && (
            <div className="flex gap-2">
              <Tombol varian="sekunder" kecil className="text-ubah-700" onClick={override}><Pencil className="size-3.5" />Override</Tombol>
              {i.override && <Tombol varian="hantu" kecil onClick={batal}><RotateCcw className="size-3.5" />Batalkan override</Tombol>}
            </div>
          )}
        </div>
      )}
    </Kartu>
  );
}

function DaftarRekomendasi({ rek, buka }: { rek: Rekomendasi[]; buka: (x: Rujukan) => void }) {
  return (
    <div className="space-y-3">
      {rek.map((x, n) => (
        <Kartu key={x.id} className={cx("space-y-2 p-4", x.tidak_diperlukan && "border-emerald-200 bg-emerald-50/50")}>
          <div className="flex gap-2 text-sm">
            {x.tidak_diperlukan ? <Check className="size-5 shrink-0 text-emerald-600" /> : <span className="font-semibold text-slate-500">{n + 1}.</span>}
            <div className="flex-1 whitespace-pre-line">{x.teks}{x.item_kode && <Lencana className="ml-2 bg-slate-100 text-slate-600 ring-slate-200">Item {x.item_kode}</Lencana>}</div>
          </div>
          {x.rujukan.length > 0 && <div className="pl-7"><DaftarRujukan rujukan={x.rujukan} buka={buka} /></div>}
        </Kartu>
      ))}
    </div>
  );
}

function Catatan({ r, simpan }: { r: DetailReview; simpan: (d: DetailReview) => void }) {
  const awal = Object.fromEntries((r.catatan ?? []).map((c) => [c.dokumen, c.teks]));
  const [teks, setTeks] = useState<Record<string, string>>(awal);
  const [pesan, setPesan] = useState<string | null>(null);
  const kirim = useMutation({
    mutationFn: (dok: string) => api.put<DetailReview>(`/api/review/${r.id}/catatan`, { dokumen: dok, teks: teks[dok] ?? "" }),
    onSuccess: (d) => { simpan(d); setPesan("Catatan disimpan."); }, onError: (e) => setPesan((e as Error).message),
  });
  if (!r.boleh_override) {
    return r.catatan?.length ? (
      <div className="space-y-3">{r.catatan.map((c) => (
        <Kartu key={c.dokumen} className="p-4 text-sm"><div className="mb-1 text-xs font-semibold text-slate-500">{c.dokumen === "UMUM" ? "Catatan umum" : `Catatan ${c.dokumen}`} · {c.oleh}</div>
          <p className="whitespace-pre-line">{c.teks}</p></Kartu>))}</div>
    ) : <p className="text-sm text-slate-500">Tidak ada catatan reviewer.</p>;
  }
  return (
    <div className="space-y-4">
      <Peringatan jenis="info">Catatan baru terlihat oleh Pengusul setelah review difinalkan.</Peringatan>
      {pesan && <p className="text-sm text-slate-600">{pesan}</p>}
      {(["UMUM", "TOR", "RAB"] as const).map((d) => (
        <Kartu key={d} className="space-y-2 p-4">
          <Kolom label={d === "UMUM" ? "Catatan umum untuk Pengusul" : `Catatan/rekomendasi tambahan ${d}`}>
            <AreaTeks value={teks[d] ?? ""} onChange={(e) => setTeks({ ...teks, [d]: e.target.value })} />
          </Kolom>
          <Tombol kecil varian="sekunder" memuat={kirim.isPending && kirim.variables === d} onClick={() => kirim.mutate(d)}>Simpan</Tombol>
        </Kartu>
      ))}
    </div>
  );
}

function RiwayatOverride({ r }: { r: DetailReview }) {
  const nama = (o: Override, v: string) => o.target === "KATEGORI" ? r.kategori!.pilihan.find((k) => k.id === v)?.kode ?? v
    : o.target === "ITEM" ? (v === "TERPENUHI" ? "Terpenuhi" : "Tidak terpenuhi") : v.replace("_", " ");
  const judul = (o: Override) => o.target === "ITEM" ? `Item ${r.item!.find((i) => i.id === o.checklist_item_id)?.kode}` : o.target === "LABEL" ? "Label" : "Kategori";
  return (
    <Kartu className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{["Waktu", "Oleh", "Target", "Sebelum → Sesudah", "Alasan", "Status"].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">{r.riwayat_override!.map((o) => (
          <tr key={o.id}><td className="whitespace-nowrap px-3 py-2">{waktu(o.at)}</td><td className="px-3 py-2">{o.oleh}</td><td className="px-3 py-2">{judul(o)}</td>
            <td className="px-3 py-2">{nama(o, o.nilai_sebelum)} → <b>{nama(o, o.nilai_sesudah)}</b></td><td className="px-3 py-2">{o.alasan}</td>
            <td className="px-3 py-2 text-xs">{o.dibatalkan_at ? `Dibatalkan ${o.dibatalkan_oleh ?? ""}` : "Aktif"}</td></tr>))}</tbody>
      </table>
    </Kartu>
  );
}

function DialogOverride({ r, d, tutup, simpan }: { r: DetailReview; d: { target: "ITEM" | "LABEL" | "KATEGORI"; item?: ItemReview }; tutup: () => void; simpan: (x: DetailReview) => void }) {
  const awal = d.target === "ITEM" ? (d.item!.terpenuhi ? "TIDAK_TERPENUHI" : "TERPENUHI")
    : d.target === "LABEL" ? (r.label!.final === "LOLOS" ? "TIDAK_LOLOS" : "LOLOS") : r.kategori!.pilihan.find((k) => k.id !== r.kategori!.final?.id)?.id ?? "";
  const [nilai, setNilai] = useState(awal);
  const [alasan, setAlasan] = useState("");
  const [galat, setGalat] = useState<string | null>(null);
  const kirim = useMutation({
    mutationFn: () => api.post<DetailReview>(`/api/review/${r.id}/override`, { target: d.target, checklist_item_id: d.item?.id, nilai, alasan }),
    onSuccess: (x) => { simpan(x); tutup(); }, onError: (e) => setGalat((e as Error).message),
  });
  const judul = d.target === "ITEM" ? `Override item ${d.item!.kode}` : d.target === "LABEL" ? "Override label akhir" : "Override kategori";
  const tidakKonsisten = d.target === "LABEL" && nilai !== r.label!.hitung;
  return (
    <Dialog buka ubahBuka={(b) => !b && tutup()} judul={judul}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); kirim.mutate(); }}>
        {galat && <Peringatan>{galat}</Peringatan>}
        <Kolom label="Nilai baru">
          <Pilih value={nilai} onChange={(e) => setNilai(e.target.value)}>
            {d.target === "ITEM" && <><option value="TERPENUHI">Terpenuhi</option><option value="TIDAK_TERPENUHI">Tidak terpenuhi</option></>}
            {d.target === "LABEL" && <><option value="LOLOS">LOLOS</option><option value="TIDAK_LOLOS">TIDAK LOLOS</option></>}
            {d.target === "KATEGORI" && r.kategori!.pilihan.map((k) => <option key={k.id} value={k.id}>{k.kode} — {k.nama}</option>)}
          </Pilih>
        </Kolom>
        {d.target === "ITEM" && <p className="text-xs text-slate-500">Label akhir akan dihitung ulang otomatis sesuai aturan pelabelan.</p>}
        {tidakKonsisten && <Peringatan jenis="warn">Label ini tidak konsisten dengan status checklist ({r.label!.hitung.replace("_", " ")}). Jelaskan alasannya dengan jelas.</Peringatan>}
        <Kolom label="Alasan" wajib><AreaTeks required value={alasan} onChange={(e) => setAlasan(e.target.value)} placeholder="Wajib diisi" /></Kolom>
        <div className="flex justify-end gap-2"><Tombol type="button" varian="hantu" onClick={tutup}>Batal</Tombol>
          <Tombol type="submit" varian="ubah" memuat={kirim.isPending} disabled={!alasan.trim()}>Simpan override</Tombol></div>
      </form>
    </Dialog>
  );
}

function DialogFinalkan({ r, buka, ubahBuka, simpan }: { r: DetailReview; buka: boolean; ubahBuka: (b: boolean) => void; simpan: (x: DetailReview) => void }) {
  const [galat, setGalat] = useState<string | null>(null);
  const kirim = useMutation({ mutationFn: () => api.post<DetailReview>(`/api/review/${r.id}/finalkan`),
    onSuccess: (x) => { simpan(x); ubahBuka(false); }, onError: (e) => setGalat((e as Error).message) });
  const aktif = (r.riwayat_override ?? []).filter((o) => !o.dibatalkan_at).length;
  return (
    <Dialog buka={buka} ubahBuka={ubahBuka} judul="Finalkan hasil review">
      <div className="space-y-4 text-sm">
        {galat && <Peringatan>{galat}</Peringatan>}
        <dl className="grid grid-cols-[8rem_1fr] gap-y-2">
          <dt className="text-slate-500">Label final</dt><dd><LencanaLabel label={r.label?.final ?? ""} /></dd>
          <dt className="text-slate-500">Kategori final</dt><dd><LencanaKategori k={r.kategori?.final} /></dd>
          <dt className="text-slate-500">Checklist</dt><dd>{r.label?.terpenuhi}/{r.label?.total} terpenuhi</dd>
          <dt className="text-slate-500">Override aktif</dt><dd>{aktif}</dd>
        </dl>
        {r.label?.tidak_konsisten && <Peringatan jenis="warn">Label final tidak konsisten dengan status checklist.</Peringatan>}
        <Peringatan jenis="warn">Setelah difinalkan, hasil terkunci dan tidak dapat diubah. Perubahan hanya melalui revisi baru dari Pengusul.</Peringatan>
        <div className="flex justify-end gap-2"><Tombol varian="hantu" onClick={() => ubahBuka(false)}>Batal</Tombol>
          <Tombol memuat={kirim.isPending} onClick={() => kirim.mutate()}><Lock className="size-4" />Finalkan</Tombol></div>
      </div>
    </Dialog>
  );
}
