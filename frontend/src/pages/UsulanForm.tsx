/** Form usulan (desain.md §7 no. 36 & 38):
 *  - `baru` (`/usulan/baru`, Pengusul): A. Hierarki anggaran RKA-K/L bertingkat, B. Kategori + Deskripsi otomatis,
 *    C. PDF TOR dan RAB (keduanya wajib).
 *  - `ubah` (`/usulan/:id/ubah`, Pengusul): hanya PDF TOR dan/atau RAB pengganti — Gagal = kirim ulang, Tidak Lolos = revisi.
 *  - `parameter` (`/usulan/:id/parameter`, Reviewer): betulkan hierarki & kategori; TOR/RAB pengganti (opsional) menjadi
 *    revisi baru yang langsung direview AI.
 *  Kolom wajib yang kosong ditandai merah + pop-up singkat; sebelum dikirim → pop-up "Apakah Anda Yakin?". */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { type FormEvent, type ReactNode, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { api } from "../api";
import type { KonteksLayout } from "../components/Layout";
import Unggah from "../components/Unggah";
import type { BarisUsulan } from "../types";
import { Dialog, Judul, Kartu, Kolom, KonfirmasiYakin, Kosong, Memuat, Peringatan, Pilih, Tombol, kelasGalat } from "../ui";

type Simpul = { kode: string; nama: string };
type Kro = Simpul & { ro: Simpul[] };
type Kegiatan = Simpul & { kro: Kro[] };
type Program = Simpul & { kegiatan: Kegiatan[] };
type Opsi = { hierarki: Program[]; kategori: { id: string; kode: string; nama: string; deskripsi: string }[] };
type Pilihan = { program: string; kegiatan: string; kro: string; ro: string };
type Mode = "baru" | "ubah" | "parameter";

const KOSONG: Pilihan = { program: "", kegiatan: "", kro: "", ro: "" };
// Hierarki tersimpan memakai kode KRO/RO lengkap dari Kegiatan (4490.EBA.994); form memakai kode per jenjang seperti Master RO.
// Awalan induk dilepas (bukan dipotong di titik terakhir) karena kode Master RO berupa teks bebas yang boleh memuat titik.
const lepasAwalan = (kode: string, induk: string) => (kode.startsWith(`${induk}.`) ? kode.slice(induk.length + 1) : kode);

export default function UsulanForm({ mode }: { mode: Mode }) {
  const { id } = useParams();
  const opsi = useQuery({ queryKey: ["opsi-pengajuan"], queryFn: () => api.get<Opsi>("/api/usulan/opsi/pengajuan"), enabled: mode !== "ubah" });
  const ada = useQuery({ queryKey: ["usulan", id], queryFn: () => api.get<BarisUsulan>(`/api/usulan/${id}`), enabled: mode !== "baru" });
  if (opsi.isLoading || ada.isLoading) return <Memuat />;
  if (opsi.error || ada.error) return <Peringatan>{((opsi.error ?? ada.error) as Error).message}</Peringatan>;
  if (mode !== "baru" && !ada.data) return <Kosong>Usulan tidak ditemukan.</Kosong>;
  return <Isi key={id ?? "baru"} mode={mode} opsi={opsi.data} u={ada.data} />;
}

function Isi({ mode, opsi, u }: { mode: Mode; opsi?: Opsi; u?: BarisUsulan }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const { tahun } = useOutletContext<KonteksLayout>();  // Tahun Anggaran pilihan di bilah atas
  const revisi = mode === "ubah" && u?.status === "TIDAK_LOLOS";
  const h = mode === "parameter" ? u?.hierarki : null;
  const [pilih, setPilih] = useState<Pilihan>(h ? { program: h.program.kode, kegiatan: h.kegiatan.kode, kro: lepasAwalan(h.kro.kode, h.kegiatan.kode),
    ro: lepasAwalan(h.ro.kode, h.kro.kode) } : KOSONG);
  const [kategoriId, setKategoriId] = useState(mode === "parameter" ? u?.kategori_usulan?.id ?? "" : "");
  const [tor, setTor] = useState<File | null>(null);
  const [rab, setRab] = useState<File | null>(null);
  const [ulang, setUlang] = useState(0);
  const [dicoba, setDicoba] = useState(false);  // setelah klik kirim, kolom kosong ditandai merah (hilang begitu diisi)
  const [belumLengkap, setBelumLengkap] = useState(false);
  const [periksa, setPeriksa] = useState(false);
  const [memuat, setMemuat] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);

  const program = opsi?.hierarki.find((x) => x.kode === pilih.program);
  const kegiatan = program?.kegiatan.find((x) => x.kode === pilih.kegiatan);
  const kro = kegiatan?.kro.find((x) => x.kode === pilih.kro);
  const ro = kro?.ro.find((x) => x.kode === pilih.ro);
  const kategori = opsi?.kategori.find((k) => k.id === kategoriId);
  // Memilih tingkat atas mengosongkan tingkat di bawahnya.
  const ubah = (k: keyof Pilihan, v: string) => {
    const urut: (keyof Pilihan)[] = ["program", "kegiatan", "kro", "ro"];
    setPilih({ ...pilih, [k]: v, ...Object.fromEntries(urut.slice(urut.indexOf(k) + 1).map((x) => [x, ""])) });
  };
  const pesanDokumen = mode === "ubah" ? "Unggah minimal satu dokumen (TOR atau RAB)." : "Wajib diunggah.";
  const reset = () => { setPilih(KOSONG); setKategoriId(""); setTor(null); setRab(null); setGalat(null); setDicoba(false); setUlang((n) => n + 1); };

  const kosong = () => {
    const k = new Set<string>();
    if (mode !== "ubah") {
      if (!program) k.add("program");
      if (!kegiatan) k.add("kegiatan");
      if (!kro) k.add("kro");
      if (!ro) k.add("ro");
      if (!kategori) k.add("kategori");
    }
    if (mode === "baru") {
      if (!tor) k.add("tor");
      if (!rab) k.add("rab");
    }
    if (mode === "ubah" && !tor && !rab) { k.add("tor"); k.add("rab"); }
    return k;
  };
  const salah = dicoba ? kosong() : new Set<string>();
  const cek = (e: FormEvent) => {
    e.preventDefault();
    setGalat(null);
    setDicoba(true);
    if (kosong().size) setBelumLengkap(true); else setPeriksa(true);
  };
  const kirim = async () => {
    setMemuat(true);
    try {
      const fd = new FormData();
      if (mode !== "ubah") {
        Object.entries(pilih).forEach(([k, v]) => fd.set(k, v));
        fd.set("kategori_id", kategoriId);
      }
      if (tor) fd.set("tor", tor);
      if (rab) fd.set("rab", rab);
      if (mode === "parameter") await api.put(`/api/usulan/${u!.id}`, fd);
      else {
        fd.set("ajukan", "true");
        if (mode === "baru") fd.set("tahun_anggaran", tahun);
        if (mode === "baru") await api.post("/api/usulan", fd);
        else if (revisi) await api.post(`/api/usulan/${u!.id}/revisi`, fd);
        else await api.put(`/api/usulan/${u!.id}/draf`, fd);
      }
      await qc.invalidateQueries();
      nav(u ? `/usulan/${u.id}` : "/usulan");
    } catch (err) { setGalat((err as Error).message); }
    finally { setMemuat(false); setPeriksa(false); }
  };

  const dropdown = (k: keyof Pilihan, label: string, daftar: Simpul[] | undefined, kodeTampil: (x: Simpul) => string) => (
    <Kolom label={label} wajib galat={salah.has(k) ? "Wajib dipilih." : null}>
      <Pilih disabled={!daftar} value={pilih[k]} onChange={(e) => ubah(k, e.target.value)} aria-invalid={salah.has(k)} className={kelasGalat(salah.has(k))}>
        <option value="">Pilih {label}</option>
        {daftar?.map((x) => <option key={x.kode} value={x.kode}>{kodeTampil(x)} — {x.nama}</option>)}
      </Pilih>
    </Kolom>
  );

  return (
    <div className="w-full space-y-4">
      <div>
        <Link to={u ? `/usulan/${u.id}` : "/usulan"} className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-4" />Kembali</Link>
        <Judul judul={mode === "baru" ? "Pengajuan Baru" : mode === "parameter" ? "Edit Usulan" : revisi ? "Unggah Revisi" : "Ganti Dokumen"}
          sub={u ? `${u.kode_ro} — ${u.nama_ro}` : `Tahun Anggaran ${tahun}`} />
      </div>
      <form className="space-y-4" onSubmit={cek} noValidate>
        {galat && <Peringatan>{galat}</Peringatan>}
        {opsi && (
          <>
            <Bagian judul="A. Parameter Hierarki Anggaran RKA-K/L">
              {opsi.hierarki.length === 0 && (
                <Peringatan jenis="warn">Belum ada data Master RO yang Aktif. Hubungi Reviewer untuk mengisi menu Master RO.</Peringatan>)}
              {dropdown("program", "Program", opsi.hierarki, (x) => x.kode)}
              {dropdown("kegiatan", "Kegiatan", program?.kegiatan, (x) => x.kode)}
              {dropdown("kro", "Klasifikasi Rincian Output (KRO)", kegiatan?.kro, (x) => `${pilih.kegiatan}.${x.kode}`)}
              {dropdown("ro", "Rincian Output (RO)", kro?.ro, (x) => `${pilih.kegiatan}.${pilih.kro}.${x.kode}`)}
            </Bagian>
            <Bagian judul="B. Klasifikasi Kategori Usulan">
              <div className="grid gap-4 sm:grid-cols-2">
                <Kolom label="Kategori" wajib galat={salah.has("kategori") ? "Wajib dipilih." : null}>
                  <Pilih value={kategoriId} onChange={(e) => setKategoriId(e.target.value)} aria-invalid={salah.has("kategori")}
                    className={kelasGalat(salah.has("kategori"))}>
                    <option value="">Pilih Kategori</option>
                    {opsi.kategori.map((k) => <option key={k.id} value={k.id}>{k.kode} — {k.nama}</option>)}
                  </Pilih>
                </Kolom>
                {/* Teks biasa (bukan kolom isian): tidak dapat diklik/diubah, terisi otomatis dari kategori terpilih. */}
                <div className="space-y-1.5">
                  <span className="block text-sm font-medium text-slate-700">Deskripsi</span>
                  <div aria-live="polite" className="pointer-events-none min-h-[2.625rem] select-none whitespace-pre-line text-justify rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                    {kategori?.deskripsi ?? <span className="text-slate-400">Terisi otomatis setelah kategori dipilih.</span>}
                  </div>
                </div>
              </div>
            </Bagian>
          </>
        )}
        <Bagian judul={mode === "ubah" ? "Unggah Berkas Dokumen" : "C. Unggah Berkas Dokumen"}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Unggah key={`tor${ulang}`} label={mode === "baru" ? "TOR (PDF) *" : "TOR (PDF)"} file={tor} ubah={(f) => setTor(f[0] ?? null)}
              keterangan={u?.tor && !tor ? `Saat ini: ${u.tor.nama}` : undefined} galatLuar={salah.has("tor") ? pesanDokumen : null} />
            <Unggah key={`rab${ulang}`} label={mode === "baru" ? "RAB (PDF) *" : "RAB (PDF)"} file={rab} ubah={(f) => setRab(f[0] ?? null)}
              keterangan={u?.rab && !rab ? `Saat ini: ${u.rab.nama}` : undefined} galatLuar={salah.has("rab") ? pesanDokumen : null} />
          </div>
        </Bagian>
        <div className="flex flex-wrap justify-end gap-2">
          <Tombol type="button" varian="hantu" onClick={() => nav(-1)}>Batal</Tombol>
          {mode === "baru" && <Tombol type="button" varian="sekunder" onClick={reset}>Reset</Tombol>}
          <Tombol type="submit">{mode === "baru" ? "Kirim Pengajuan" : mode === "parameter" ? "Simpan" : revisi ? "Kirim Revisi" : "Kirim Ulang"}</Tombol>
        </div>
      </form>
      <Dialog buka={belumLengkap} ubahBuka={setBelumLengkap} judul="Data belum lengkap" lebar="max-w-sm">
        <div className="space-y-4 text-sm">
          <p className="text-slate-700">Mohon lengkapi isian yang masih kosong sebelum melanjutkan.</p>
          <div className="flex justify-end"><Tombol onClick={() => setBelumLengkap(false)}>Tutup</Tombol></div>
        </div>
      </Dialog>
      <KonfirmasiYakin buka={periksa} batal={() => setPeriksa(false)} ya={kirim} memuat={memuat} />
    </div>
  );
}

function Bagian({ judul, children }: { judul: string; children: ReactNode }) {
  return (
    <Kartu className="space-y-4 p-5">
      <h2 className="font-semibold text-slate-900">{judul}</h2>
      {children}
    </Kartu>
  );
}
