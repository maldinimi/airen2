/** Panduan (Modul D): semua pengguna dapat membaca; Admin mengunggah, mengubah (versi baru), mengganti file, menghapus. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil, RotateCcw, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import Unggah from "../components/Unggah";
import { tanggal, waktu } from "../format";
import type { Panduan, RingkasVersi, Versi, VersiPanduan } from "../types";
import { AreaTeks, Dialog, Input, Judul, Kartu, Kolom, Kosong, Lencana, Memuat, Peringatan, Tab, Tombol } from "../ui";

const STATUS: Record<VersiPanduan["status_proses"], [string, string]> = {
  BELUM: ["Antre", "bg-blue-50 text-blue-700 ring-blue-200"], DIPROSES: ["Diproses", "bg-blue-50 text-blue-700 ring-blue-200"],
  SIAP: ["Siap", "bg-emerald-50 text-emerald-700 ring-emerald-300"], GAGAL: ["Gagal", "bg-red-100 text-red-900 ring-red-300"],
};

export default function PanduanPage() {
  const { punya } = useAuth();
  const admin = punya("ADMIN");
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["panduan"], queryFn: () => api.get<Panduan[]>("/api/panduan"),
    refetchInterval: (x) => (x.state.data?.some((p) => ["BELUM", "DIPROSES"].includes(p.terkini.status_proses)) ? 5000 : false),
  });
  const daftarVersi = useQuery({ queryKey: ["panduan", "versi"], queryFn: () => api.get<{ aktif: RingkasVersi | null; versi: RingkasVersi[] }>("/api/panduan/versi") });
  const [tab, setTab] = useState<"aktif" | "versi">("aktif");
  const [unggahBuka, setUnggahBuka] = useState(false);
  const [ubah, setUbah] = useState<Panduan | null>(null);
  const segarkan = () => qc.invalidateQueries({ queryKey: ["panduan"] });
  const hapus = useMutation({ mutationFn: (id: string) => api.del(`/api/panduan/${id}`), onSuccess: segarkan, onError: (e) => alert((e as Error).message) });
  const ulang = useMutation({ mutationFn: (id: string) => api.post(`/api/panduan/${id}/proses-ulang`), onSuccess: segarkan, onError: (e) => alert((e as Error).message) });

  return (
    <div>
      <Judul judul="Panduan" sub="Peraturan, kebijakan, dan standar yang menjadi acuan review AI. Hanya panduan berstatus Siap yang dipakai review."
        aksi={admin && <Tombol onClick={() => setUnggahBuka(true)}><Upload className="size-4" />Unggah Panduan</Tombol>} />
      <Tab aktif={tab} ubah={setTab} pilihan={[{ nilai: "aktif", label: `Panduan aktif${daftarVersi.data?.aktif ? ` (v${daftarVersi.data.aktif.nomor})` : ""}` }, { nilai: "versi", label: "Daftar versi" }]} />
      <div className="mt-4">
      {tab === "versi" ? <DaftarVersi data={daftarVersi.data?.versi} /> : <>
      {q.isLoading ? <Memuat /> : !q.data?.length ? <Kosong>Belum ada panduan.</Kosong> : (
        <div className="grid gap-3 md:grid-cols-2">
          {q.data.map((p) => {
            const v = p.terkini;
            const [nama, warna] = STATUS[v.status_proses];
            return (
              <Kartu key={p.id} className="space-y-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <Link to={`/pdf/${v.file_id}?judul=${encodeURIComponent(v.judul)}`} className="font-medium text-utama-700 hover:underline">{v.judul}</Link>
                  <Lencana className={warna}>{(v.status_proses === "DIPROSES" || v.status_proses === "BELUM") && <Loader2 className="size-3 animate-spin" />}{nama}</Lencana>
                </div>
                {v.deskripsi && <p className="text-sm text-slate-600">{v.deskripsi}</p>}
                <p className="text-xs text-slate-500">{v.nama_file} · {v.jumlah_halaman} hlm · versi {v.nomor} · {tanggal(v.dibuat_at)}</p>
                {v.status_proses === "GAGAL" && <Peringatan>{v.pesan_gagal ?? "Pemrosesan gagal."}</Peringatan>}
                {admin && (
                  <div className="flex flex-wrap gap-1.5">
                    <Tombol kecil varian="sekunder" onClick={() => setUbah(p)}><Pencil className="size-3.5" />Ubah / ganti file</Tombol>
                    {v.status_proses === "GAGAL" && <Tombol kecil varian="sekunder" onClick={() => ulang.mutate(p.id)}><RotateCcw className="size-3.5" />Proses ulang</Tombol>}
                    <Tombol kecil varian="hantu" className="text-red-600" onClick={() => confirm(`Hapus panduan "${v.judul}"? File tetap disimpan untuk rujukan review lama.`) && hapus.mutate(p.id)}>
                      <Trash2 className="size-3.5" />Hapus</Tombol>
                  </div>
                )}
                {p.versi.length > 1 && (
                  <details className="text-xs text-slate-500"><summary className="cursor-pointer">Versi sebelumnya ({p.versi.length - 1})</summary>
                    <ul className="mt-1 space-y-0.5">{p.versi.slice(1).map((x) => (
                      <li key={x.id}>v{x.nomor}: <Link className="text-utama-600 hover:underline" to={`/pdf/${x.file_id}?judul=${encodeURIComponent(x.judul)}`}>{x.judul}</Link> · {x.nama_file} · {tanggal(x.dibuat_at)}</li>))}</ul>
                  </details>
                )}
              </Kartu>
            );
          })}
        </div>
      )}
      </>}
      </div>
      {unggahBuka && <DialogUnggah tutup={() => { setUnggahBuka(false); segarkan(); }} />}
      {ubah && <DialogUbah p={ubah} tutup={() => { setUbah(null); segarkan(); }} />}
    </div>
  );
}

/** Daftar versi daftar panduan; klik untuk melihat panduan (dan versinya) yang tercatat pada versi itu. */
function DaftarVersi({ data }: { data?: RingkasVersi[] }) {
  const [lihat, setLihat] = useState<string | null>(null);
  const isi = useQuery({ queryKey: ["panduan", "versi", lihat], queryFn: () => api.get<Versi<VersiPanduan>>(`/api/panduan/versi/${lihat}`), enabled: !!lihat });
  if (!data) return <Memuat />;
  if (!data.length) return <Kosong>Belum ada versi. Versi pertama dibuat saat panduan pertama diunggah.</Kosong>;
  return (
    <div className="space-y-2">
      {data.map((v) => (
        <Kartu key={v.id} className="p-3">
          <button className="flex w-full flex-wrap items-center gap-2 text-left text-sm" onClick={() => setLihat(lihat === v.id ? null : v.id)}>
            <span className="font-semibold">Versi {v.nomor}</span>{v.aktif && <Lencana className="bg-emerald-50 text-emerald-700 ring-emerald-300">Aktif</Lencana>}
            <span className="text-slate-500">{v.jumlah_item} panduan · {waktu(v.dibuat_at)} · {v.dibuat_oleh ?? "sistem"}</span>
            {v.catatan && <span className="w-full text-xs text-slate-500">{v.catatan}</span>}
          </button>
          {lihat === v.id && (isi.isLoading ? <Memuat /> : (
            <ol className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">{isi.data?.item.map((x) => (
              <li key={x.id}><Link className="text-utama-600 hover:underline" to={`/pdf/${x.file_id}?judul=${encodeURIComponent(x.judul)}`}>{x.judul}</Link>
                <span className="text-xs text-slate-500"> · v{x.nomor} · {x.nama_file}</span></li>))}
              {!isi.data?.item.length && <li className="text-slate-500">Tidak ada panduan pada versi ini.</li>}</ol>
          ))}
        </Kartu>
      ))}
    </div>
  );
}

function DialogUnggah({ tutup }: { tutup: () => void }) {
  const [file, setFile] = useState<File[]>([]);
  const kirim = useMutation({
    mutationFn: () => { const fd = new FormData(); file.forEach((f) => fd.append("files", f)); return api.post("/api/panduan", fd); },
    onSuccess: tutup,
  });
  return (
    <Dialog buka ubahBuka={(b) => !b && tutup()} judul="Unggah panduan">
      <div className="space-y-4">
        {kirim.error && <Peringatan>{(kirim.error as Error).message}</Peringatan>}
        <Unggah label="File PDF (dapat beberapa sekaligus)" banyak file={file} ubah={setFile} />
        <p className="text-xs text-slate-500">Judul awal = nama file; dapat diubah setelah diunggah. File diproses (teks, tabel, gambar, scan) sebelum siap dirujuk AI.</p>
        <div className="flex justify-end gap-2"><Tombol varian="hantu" onClick={tutup}>Batal</Tombol>
          <Tombol disabled={!file.length} memuat={kirim.isPending} onClick={() => kirim.mutate()}>Unggah {file.length || ""} file</Tombol></div>
      </div>
    </Dialog>
  );
}

function DialogUbah({ p, tutup }: { p: Panduan; tutup: () => void }) {
  const [judul, setJudul] = useState(p.terkini.judul);
  const [deskripsi, setDeskripsi] = useState(p.terkini.deskripsi ?? "");
  const [file, setFile] = useState<File | null>(null);
  const kirim = useMutation({
    mutationFn: () => { const fd = new FormData(); fd.set("judul", judul); fd.set("deskripsi", deskripsi); if (file) fd.set("file", file); return api.put(`/api/panduan/${p.id}`, fd); },
    onSuccess: tutup,
  });
  return (
    <Dialog buka ubahBuka={(b) => !b && tutup()} judul="Ubah panduan">
      <div className="space-y-4">
        {kirim.error && <Peringatan>{(kirim.error as Error).message}</Peringatan>}
        <Kolom label="Judul" wajib><Input value={judul} onChange={(e) => setJudul(e.target.value)} /></Kolom>
        <Kolom label="Deskripsi"><AreaTeks value={deskripsi} onChange={(e) => setDeskripsi(e.target.value)} /></Kolom>
        <Unggah label="Ganti file (opsional)" file={file} ubah={(f) => setFile(f[0] ?? null)} keterangan={`Saat ini: ${p.terkini.nama_file}`} />
        <Peringatan jenis="info">Perubahan disimpan sebagai versi baru. Versi lama tetap tersimpan untuk rujukan review sebelumnya.</Peringatan>
        <div className="flex justify-end gap-2"><Tombol varian="hantu" onClick={tutup}>Batal</Tombol>
          <Tombol disabled={!judul.trim()} memuat={kirim.isPending} onClick={() => kirim.mutate()}>Simpan versi baru</Tombol></div>
      </div>
    </Dialog>
  );
}
