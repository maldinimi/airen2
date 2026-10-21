/** Unggah (D2): Nama Acuan, Deskripsi, Status, file PDF. Edit: sama tanpa ganti file. Hanya Admin. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import PdfViewer from "../components/PdfViewer";
import Unggah from "../components/Unggah";
import type { Panduan } from "../types";
import { AreaTeks, Dialog, Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Memuat, Peringatan, Saklar, Tombol } from "../ui";

export default function PanduanForm({ mode }: { mode: "unggah" | "ubah" }) {
  const { id } = useParams();
  // Memakai daftar panduan (kunci cache sama dengan halaman Panduan) — tidak perlu endpoint per panduan.
  const q = useQuery({ queryKey: ["panduan"], queryFn: () => api.get<Panduan[]>("/api/panduan"), enabled: mode === "ubah" });
  if (mode === "unggah") return <Isi />;
  if (q.isLoading) return <Memuat />;
  const p = q.data?.find((x) => x.id === id);
  return p ? <Isi key={p.id} p={p} /> : <Kosong>Panduan tidak ditemukan.</Kosong>;
}

function Isi({ p }: { p?: Panduan }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [judul, setJudul] = useState(p?.terkini.judul ?? "");
  const [deskripsi, setDeskripsi] = useState(p?.terkini.deskripsi ?? "");
  const [aktif, setAktif] = useState(p?.aktif ?? true);
  const [file, setFile] = useState<File | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [memuat, setMemuat] = useState(false);
  const [periksa, setPeriksa] = useState(false);
  const [pratinjau, setPratinjau] = useState(false);
  const [ulang, setUlang] = useState(0);
  const kosong = !judul && !deskripsi && aktif && !file;
  // Reset (mode Unggah): semua isian kembali awal; key Unggah berganti agar pesan galat di kotak PDF ikut hilang.
  const reset = () => { setJudul(""); setDeskripsi(""); setAktif(true); setFile(null); setGalat(null); setUlang((n) => n + 1); };

  const cek = (e: FormEvent) => {
    e.preventDefault();
    setGalat(null);
    if (!p && !file) return setGalat("File PDF wajib diunggah.");
    setPeriksa(true);
  };

  const kirim = async () => {
    const fd = new FormData();
    fd.set("judul", judul);
    fd.set("deskripsi", deskripsi);
    fd.set("aktif", String(aktif));
    if (file) fd.set("file", file);
    setMemuat(true);
    try {
      if (p) await api.put(`/api/panduan/${p.id}`, fd); else await api.post("/api/panduan", fd);
      await qc.invalidateQueries({ queryKey: ["panduan"] });
      nav("/panduan");
    } catch (err) { setGalat((err as Error).message); setPeriksa(false); }
    finally { setMemuat(false); }
  };

  return (
    <div className="max-w-3xl">
      <Link to="/panduan" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"><ArrowLeft className="size-4" />Kembali</Link>
      <Judul judul={p ? "Edit Panduan" : "Unggah Panduan"} sub={p ? p.terkini.judul : "File diproses (teks, tabel, gambar, scan) sebelum siap dirujuk AI."} />
      <Kartu className="p-5">
        <form className="space-y-5" onSubmit={cek}>
          {galat && <Peringatan>{galat}</Peringatan>}
          <Kolom label="Nama Acuan" wajib><Input required maxLength={500} value={judul} onChange={(e) => setJudul(e.target.value)} placeholder="mis. PMK Standar Biaya Masukan 2027" /></Kolom>
          <Kolom label="Deskripsi"><AreaTeks value={deskripsi} onChange={(e) => setDeskripsi(e.target.value)} /></Kolom>
          <div className="space-y-1.5">
            <span className="text-sm font-medium text-slate-700">Status</span>
            <div className="flex items-center gap-2 text-sm">
              <Saklar nyala={aktif} ubah={setAktif} label="Status panduan" />
              <span className={aktif ? "text-emerald-700" : "text-red-600"}>{aktif ? "Aktif" : "Nonaktif"}</span>
            </div>
            <span className="block text-xs text-slate-500">Hanya panduan Aktif yang dipakai review berikutnya.</span>
          </div>
          {/* Nama Acuan diisi otomatis dari nama file bila masih kosong. */}
          {!p && <Unggah key={ulang} label="File PDF *" file={file} lihat={() => setPratinjau(true)}
            ubah={(f) => { setFile(f[0] ?? null); if (!judul.trim() && f[0]) setJudul(f[0].name.replace(/\.pdf$/i, "")); }} />}
          {p && <Peringatan jenis="info">Perubahan nama, deskripsi, atau status disimpan sebagai versi baru. Versi lama tetap tersimpan untuk rujukan review sebelumnya.</Peringatan>}
          <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
            {!p && <Tombol type="button" varian="sekunder" disabled={kosong} onClick={reset}>Reset</Tombol>}
            <Tombol type="submit">{p ? "Simpan" : "Unggah"}</Tombol>
          </div>
        </form>
      </Kartu>
      {/* Pratinjau sebelum unggah (pop-up agar form tidak memanjang); isi dibaca ulang setiap dibuka. */}
      {file && (
        <Dialog buka={pratinjau} ubahBuka={setPratinjau} judul={`Pratinjau — ${file.name}`} lebar="max-w-5xl">
          <div className="h-[75vh] overflow-hidden rounded-lg border border-slate-200"><PdfViewer file={file} /></div>
        </Dialog>
      )}
      <Konfirmasi buka={periksa} batal={() => setPeriksa(false)} ya={kirim} memuat={memuat} baris={[
        ["Nama Acuan", judul.trim()], ["Deskripsi", deskripsi.trim() || "—"], ["Status", aktif ? "Aktif" : "Nonaktif"],
        ["File", p ? p.terkini.nama_file : file?.name ?? "—"]]} />
    </div>
  );
}
