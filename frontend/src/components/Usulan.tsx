/** Potongan UI untuk baris usulan: tautan dokumen, status proses, dan ikon aksi Detail/Edit/Hapus (desain.md §7 no. 36). */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, FileText, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { BarisUsulan, Dok, Proses } from "../types";
import { KonfirmasiYakin, Peringatan, Progres, cx } from "../ui";

/** TOR/RAB yang diunggah; klik membuka isi PDF. Dokumen yang tidak diunggah tidak ditampilkan. */
export function TautanDokumen({ tor, rab }: { tor: Dok | null; rab: Dok | null }) {
  return (
    <div className="space-y-1">
      {([["TOR", tor], ["RAB", rab]] as const).map(([jenis, d]) => d && (
        <Link key={jenis} to={`/pdf/${d.file_id}?judul=${encodeURIComponent(`${jenis} — ${d.nama}`)}`} title={d.nama}
          className="flex max-w-56 items-center gap-1.5 text-xs text-utama-600 hover:underline">
          <FileText className="size-3.5 shrink-0" aria-hidden /><span className="truncate"><b>{jenis}</b> · {d.nama}</span>
        </Link>
      ))}
    </div>
  );
}

export function InfoProses({ p }: { p: Proses | null }) {
  if (!p) return null;
  if (p.status === "GAGAL") return <Peringatan>{p.error_pesan ?? "Review AI gagal."}</Peringatan>;
  if (p.status === "ANTRE")
    return <p className="text-xs text-blue-700">{p.menunggu_kapasitas ? "Menunggu kapasitas AI · " : ""}Antrean ke-{p.posisi_antrean ?? "?"}</p>;
  return <Progres persen={p.progres?.persen ?? 0} tahap={p.progres?.tahap ?? "Diproses"} />;
}

/** Satker (Pengusul Satker ini) hanya boleh mengganti dokumen lalu mengirim ulang saat pengiriman Gagal (atau masih Draf);
 *  usulan yang sudah terkirim (menunggu verifikasi, lolos, tidak lolos) cukup dilihat — revisi lewat halaman Pemeriksaan. */
export const bolehUbahDokumen = (u: BarisUsulan) => u.boleh_kelola && !u.diarsipkan && ["DRAF", "GAGAL"].includes(u.status);

/** Aksi per role (desain.md §7 no. 38): semua = Detail; Reviewer (ROCAN) = Edit hierarki/kategori + Hapus;
 *  Satker = Edit dokumen hanya saat Gagal/Draf; Admin = Detail saja. Hak akses tetap dicek backend. */
export function AksiUsulan({ u }: { u: BarisUsulan }) {
  const { punya } = useAuth();
  const nav = useNavigate();
  const qc = useQueryClient();
  const reviewer = punya("REVIEWER");
  const [konfirmasi, setKonfirmasi] = useState(false);
  const hapus = useMutation({
    mutationFn: () => api.del(`/api/usulan/${u.id}`),
    onSuccess: () => { setKonfirmasi(false); qc.invalidateQueries(); },
  });
  const ubah = reviewer ? `/usulan/${u.id}/parameter` : bolehUbahDokumen(u) ? `/usulan/${u.id}/ubah` : null;
  const tombol = "rounded-lg p-1.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";
  return (
    <div className="flex items-center justify-center">
      <button type="button" className={cx(tombol, "text-emerald-600 hover:bg-emerald-50")} title="Detail" aria-label={`Detail ${u.kode_ro}`}
        onClick={() => nav(`/usulan/${u.id}`)}><Eye className="size-4" /></button>
      {ubah && (
        <button type="button" className={cx(tombol, "text-utama-600 hover:bg-utama-50")} title="Edit" aria-label={`Edit ${u.kode_ro}`}
          onClick={() => nav(ubah)}><Pencil className="size-4" /></button>
      )}
      {reviewer && !["ANTRE", "DIPROSES_AI"].includes(u.status) && (
        <button type="button" className={cx(tombol, "text-red-600 hover:bg-red-50")} title="Hapus" aria-label={`Hapus ${u.kode_ro}`}
          onClick={() => { hapus.reset(); setKonfirmasi(true); }}><Trash2 className="size-4" /></button>
      )}
      <KonfirmasiYakin buka={konfirmasi} bahaya batal={() => setKonfirmasi(false)} ya={() => hapus.mutate()} memuat={hapus.isPending}
        galat={hapus.error ? (hapus.error as Error).message : null} />
    </div>
  );
}
