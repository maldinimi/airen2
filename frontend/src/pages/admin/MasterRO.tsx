/** Master RO (khusus Reviewer): CRUD berjenjang Program → Kegiatan → KRO → RO.
 *  Tampilan mengikuti menu Satuan Kerja: SATU tabel berkolom Kode Program, Program, Kode Kegiatan, Kegiatan, Kode KRO,
 *  KRO, Kode RO, RO (tiap baris = satu data beserta induk-induknya; kolom tingkat di bawahnya kosong), filter berurutan
 *  sesuai kolom, 3 ikon aksi, detail & form sebagai halaman sendiri. Aturan induk/kode/hapus dijaga backend
 *  (app/api/master_ro.py). Format kode mengikuti SEB No. 6/2025; KRO diberi saran dari Lampiran II (bukan wajib).
 *  Kolom tabel = kolom database `master_ro` (Unit Eselon I/II dan Prioritas dihapus, migrasi 0019; permintaan pemilik
 *  produk). Tabel dipaginasi (pilihan 10/20/50/100 baris), bawaan 20 baris per halaman.
 *  Revisi 7: tiap RO punya Satker pelaksana (Unit Kerja Eselon I + Satuan Kerja Eselon II), di form berupa daftar
 *  bullet yang bisa ditambah/dihapus (minimal 1 baris); di tabel, 2 Satker atau lebih tampil sebagai bullet list.
 *  Per Tahun Anggaran: tabel, Tambah, dan Import Excel mengikuti Tahun Anggaran pilihan bilah atas (Pengajuan tahun X
 *  memakai Master RO tahun X). Mengganti tahun menutup form/detail/import yang terbuka (induknya milik tahun lama). */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Upload } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../../api";
import type { KonteksLayout } from "../../components/Layout";
import { Aksi, HalamanDetail, HalamanForm, type Jejak, LencanaAktif, PilihBawah, type Satker, TD, TOMBOL_IKON, barisJejak, labelSatker,
  nilaiUnitKerja, opsiUnitKerja, th, usePesanSukses } from "../../components/Kelola";
import { FormFilter, type NilaiFilter, OPSI_STATUS, Paginasi, ThUrut, cocok, lolosJejak, lolosStatus, usePaginasi, useUrut, TabelGeser } from "../../components/TabelData";
import { waktuAngka } from "../../format";
import { Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Memuat, Peringatan, Saklar, TanggalJam, Tombol, cx } from "../../ui";

type Tingkat = "PROGRAM" | "KEGIATAN" | "KRO" | "RO";
// Kolom datar tabel `master_ro` (dikirim backend apa adanya; kosong untuk jenjang di bawah data ini).
type KolomDb = "kode_program" | "program" | "kode_kegiatan" | "kegiatan" | "kode_kro" | "kro" | "kode_ro" | "ro";
// Satker pelaksana RO (urut isian form) = baris menu Satuan Kerja (tabel master_ro_satker, JOIN ke satker).
type SatkerRO = { id: string; kode_uke1: string; unit_kerja: string; kode_uke2: string; nama: string; aktif: boolean };
type BarisRO = {
  id: string; tahun_anggaran: number; tingkat: Tingkat; kode: string; kode_lengkap: string; nama: string; aktif: boolean;
  induk_id: string | null; jumlah_turunan: number; satker: SatkerRO[];
} & Record<KolomDb, string> & Jejak;
// Satu baris bullet Satker di form: Unit Kerja (Eselon I) lalu Satuan Kerja (Eselon II) di bawahnya.
type IsianSatker = { unit_kerja: string; satker_id: string };
const SATKER_KOSONG: IsianSatker = { unit_kerja: "", satker_id: "" };
// `jalur` = id data terpilih per jenjang di atas data ini (Program → … → induk), dipilih berurut di form; induk = jenjang
// terakhirnya.
type Isian = { id?: string; tingkat: Tingkat; jalur: Partial<Record<Tingkat, string>>; kode: string; nama: string; aktif: boolean; satker: IsianSatker[] };

const ENDPOINT = "/api/master-ro";
const TINGKAT: Tingkat[] = ["PROGRAM", "KEGIATAN", "KRO", "RO"];
const NAMA: Record<Tingkat, string> = { PROGRAM: "Program", KEGIATAN: "Kegiatan", KRO: "KRO", RO: "RO" };
const INDUK: Partial<Record<Tingkat, Tingkat>> = { KEGIATAN: "PROGRAM", KRO: "KEGIATAN", RO: "KRO" };
const ANAK: Partial<Record<Tingkat, Tingkat>> = { PROGRAM: "KEGIATAN", KEGIATAN: "KRO", KRO: "RO" };
// Kode = teks bebas (tanpa batasan huruf/angka), maks. 50 karakter = MAKS_KODE di backend.
const MAKS_KODE = 50;
type RefKRO = { kode: string; nama: string; satuan: string; pn: boolean };
// Kolom tabel: Kode Program, Program, Kode Kegiatan, Kegiatan, Kode KRO, KRO, Kode RO, RO, Status, Diinput Oleh,
// Tanggal Input (urutan akhir sama dengan Checklist). `t` = jenjang pemilik kolom (ditebalkan pada baris jenjang itu).
// `k` kolom jenjang = nama kolom database, sekaligus kunci filternya.
const KOLOM_DB: Record<Tingkat, [KolomDb, KolomDb]> = {
  PROGRAM: ["kode_program", "program"], KEGIATAN: ["kode_kegiatan", "kegiatan"], KRO: ["kode_kro", "kro"], RO: ["kode_ro", "ro"],
};
type KolomSatker = "unit_kerja" | "satuan_kerja";
type KolomUrut = KolomDb | KolomSatker | "aktif" | "oleh" | "tanggal";
type Kolom = { k: KolomUrut; t?: Tingkat; label: string; jenis: "kode" | "nama" | "satker" | "status" | "oleh" | "tanggal" };
const kodeNama = (t: Tingkat): Kolom[] => [{ k: KOLOM_DB[t][0], t, label: `Kode ${NAMA[t]}`, jenis: "kode" }, { k: KOLOM_DB[t][1], t, label: NAMA[t], jenis: "nama" }];
const KOLOM_JENJANG = TINGKAT.flatMap((t) => KOLOM_DB[t]);
// Kolom nama RO (tingkat terbawah) diberi latar tipis agar mudah dibedakan dari kolom induknya (desain.md §7 no. 66).
const kolomRO = (c: Kolom) => c.t === "RO" && c.jenis === "nama";
const KOLOM: Kolom[] = [...TINGKAT.flatMap(kodeNama),
  { k: "unit_kerja", label: "Unit Kerja (Eselon I)", jenis: "satker" }, { k: "satuan_kerja", label: "Satuan Kerja (Eselon II)", jenis: "satker" },
  { k: "aktif", label: "Status", jenis: "status" },
  { k: "oleh", label: "Diinput Oleh", jenis: "oleh" }, { k: "tanggal", label: "Tanggal Input", jenis: "tanggal" }];
// Isi kolom Unit Kerja / Satuan Kerja per Satker (urut sama di kedua kolom, jadi bullet ke-n saling berpasangan).
const isiSatker = (x: BarisRO, k: KolomSatker) => x.satker.map((s) => (k === "unit_kerja" ? s.unit_kerja : s.nama) || "—");

/** Bullet Satker: titik + teks, huruf tiap baris lurus. Sama di tabel (SatkerSejajar) dan halaman Detail. */
// Titik bullet sebaris dengan teks (inline), jadi ikut rata tengah bersama teksnya; teks panjang terbungkus rata tengah
// seperti sel 1 Satker.
const Butir = ({ teks }: { teks: string }) => (
  <span className="block"><span className="mr-2 inline-block size-1.5 rounded-full bg-current align-middle opacity-60" aria-hidden />{teks}</span>
);

/** Isi detail Satker: 1 Satker = teks biasa, 2 atau lebih = bullet list (Revisi 7), gaya sama dengan tabel. */
function DaftarSatker({ isi }: { isi: string[] }) {
  if (!isi.length) return <>—</>;
  if (isi.length === 1) return <>{isi[0]}</>;
  return <div className="space-y-1.5">{isi.map((v, i) => <Butir key={i} teks={v} />)}</div>;
}

// Lebar kolom Unit Kerja & Satuan Kerja di tabel: SAMA dan tetap, agar grid di sel gabungan (SatkerSejajar) lurus
// dengan judul kolomnya.
const LEBAR_KOLOM_SATKER = "w-[18rem] min-w-[18rem]";

/** Isi tabel kolom Unit Kerja + Satuan Kerja dalam SATU sel (colSpan 2) berisi grid 2 kolom: tiap Satker = satu baris
 *  grid, jadi bullet Unit Kerja ke-n selalu sejajar dengan Satuan Kerja ke-n walau salah satu namanya terbungkus 2
 *  baris. Jarak antarkolom grid (gap-x-6) = padding kanan + kiri dua sel judul (px-3 + px-3), sehingga isi lurus dengan
 *  judulnya. 1 Satker = teks biasa rata tengah; 2 atau lebih = rata tengah juga, dengan bullet di depan tiap nama. */
function SatkerSejajar({ daftar }: { daftar: SatkerRO[] }) {
  if (daftar.length <= 1) {
    const s = daftar[0];
    return <div className="grid grid-cols-2 gap-x-6"><span>{s ? s.unit_kerja || "—" : "—"}</span><span>{s ? s.nama : "—"}</span></div>;
  }
  // 2 Satker atau lebih: gaya sama dengan sel 1 Satker (rata tengah, nama panjang terbungkus rata tengah), ditambah
  // bullet di depan tiap nama. Tiap Satker = satu baris grid (Unit Kerja | Satuan Kerja), jadi baris ke-n kedua kolom
  // tetap sejajar walau salah satu namanya terbungkus.
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
      {daftar.map((s) => [<Butir key={`u${s.id}`} teks={s.unit_kerja || "—"} />, <Butir key={`s${s.id}`} teks={s.nama} />])}
    </div>
  );
}

/** Satker pelaksana di form: daftar bullet, tiap baris = Unit Kerja (Eselon I) → Satuan Kerja (Eselon II) di bawahnya.
 *  Baris bisa ditambah & dihapus, minimal 1 baris (tombol hapus nonaktif saat tinggal satu). Satuan Kerja yang sudah
 *  dipilih di baris lain tidak muncul lagi. Satker Nonaktif disembunyikan kecuali yang sudah tercatat (`dipakai`).
 *  Selama daftar Satker dimuat / gagal dimuat, pilihan diganti pesan (tanpa itu dropdown kosong tanpa penjelasan). */
function IsianSatkerRO({ daftar, baris, ubah, dipakai, memuat, galat }: {
  daftar: Satker[]; baris: IsianSatker[]; ubah: (b: IsianSatker[]) => void; dipakai: Set<string>;
  memuat: boolean; galat: Error | null;
}) {
  if (memuat || galat) return (
    <div className="space-y-2 sm:col-span-2">
      <span className="text-sm font-medium text-slate-700">Unit Kerja & Satuan Kerja<span className="text-red-600"> *</span></span>
      {galat ? <Peringatan>Daftar Satuan Kerja gagal dimuat: {galat.message} Muat ulang halaman lalu coba lagi.</Peringatan> : <Memuat />}
    </div>
  );
  const tampil = daftar.filter((s) => s.nama && (s.aktif !== false || dipakai.has(s.id)));
  const opsiUnit = opsiUnitKerja(tampil);  // pilihan bersama dengan form Pengguna (components/Kelola.tsx)
  const ganti = (i: number, isi: IsianSatker) => ubah(baris.map((b, j) => (j === i ? isi : b)));
  // Tata letak tiap baris bullet: [bullet][Unit Kerja][Satuan Kerja][hapus], semua rata tengah vertikal terhadap kotak
  // dropdown (judul kolom ditulis SEKALI di atas daftar, bukan per baris, agar bullet & tombol hapus tidak sejajar
  // dengan judul). Judul digeser selebar bullet + jarak (pl) dan tombol hapus + jarak (pr) agar lurus dengan dropdown.
  return (
    <div className="space-y-2 sm:col-span-2">
      <span className="block text-sm font-medium text-slate-700">Unit Kerja & Satuan Kerja<span className="text-red-600"> *</span></span>
      <div className="hidden gap-3 pl-[1.125rem] pr-10 text-xs font-medium text-slate-500 sm:grid sm:grid-cols-2" aria-hidden>
        <span>Unit Kerja (Eselon I)</span><span>Satuan Kerja (Eselon II)</span>
      </div>
      <ul className="space-y-2">
        {baris.map((b, i) => {
          const lain = new Set(baris.filter((_, j) => j !== i).map((x) => x.satker_id));
          const opsiSatker = tampil.filter((s) => nilaiUnitKerja(s) === b.unit_kerja && !lain.has(s.id))
            .map((s) => ({ nilai: s.id, label: labelSatker(s) }));
          return (
            <li key={i} className="flex items-center gap-3">
              <span className="size-1.5 shrink-0 rounded-full bg-slate-500" aria-hidden />
              <div className="grid flex-1 gap-2 sm:grid-cols-2 sm:gap-3">
                <PilihBawah nilai={b.unit_kerja} ubah={(uk) => ganti(i, { unit_kerja: uk, satker_id: "" })} kosong="— pilih Unit Kerja (Eselon I) —" opsi={opsiUnit} />
                <PilihBawah nilai={b.satker_id} ubah={(id) => ganti(i, { ...b, satker_id: id })} disabled={!b.unit_kerja}
                  kosong={b.unit_kerja ? "— pilih Satuan Kerja (Eselon II) —" : "— pilih Unit Kerja terlebih dahulu —"} opsi={b.unit_kerja ? opsiSatker : []} />
              </div>
              <button type="button" disabled={baris.length === 1} onClick={() => ubah(baris.filter((_, j) => j !== i))}
                title={baris.length === 1 ? "Minimal 1 Satuan Kerja" : "Hapus baris"} aria-label={`Hapus Satuan Kerja baris ${i + 1}`}
                className={cx(TOMBOL_IKON, "text-red-600 hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent")}>
                <Trash2 className="size-4" />
              </button>
            </li>
          );
        })}
      </ul>
      <Tombol type="button" varian="sekunder" kecil onClick={() => ubah([...baris, SATKER_KOSONG])}><Plus className="size-4" />Tambah Satuan Kerja</Tombol>
    </div>
  );
}

const teksInduk = (x: { kode: string; nama: string }) => `${x.kode} — ${x.nama}`;

type HasilImpor = { tahun_anggaran: number; baris: number; dibuat: Record<Tingkat, number>; total_dibuat: number; sudah_ada: number; satker_diisi: number };
// Judul kolom file import = KOLOM_IMPOR backend: kolom jenjang + Satker pelaksana (Revisi 7).
const KOLOM_IMPOR = [...KOLOM_JENJANG, "unit_kerja", "satuan_kerja"];

/** Halaman Import Excel: isian file bawaan browser, .xlsx (maks. 5 MB), lalu POST /api/master-ro/impor. Format
 *  kolom = KOLOM_IMPOR; aturan & penyimpanan semua-atau-tidak dijaga backend, daftar kesalahan per baris Excel
 *  ditampilkan apa adanya (satu kesalahan per baris teks). */
const MAKS_MB_IMPOR = 5;
function ImporExcel({ tahun, tutup, berhasil }: { tahun: string; tutup: () => void; berhasil: (h: HasilImpor) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const masukan = useRef<HTMLInputElement>(null);
  const impor = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append("file", file!);
      fd.append("tahun_anggaran", tahun);  // semua data file masuk ke Tahun Anggaran pilihan bilah atas
      return api.post<HasilImpor>(`${ENDPOINT}/impor`, fd);
    },
    onSuccess: berhasil,
  });
  // Validasi ringan di browser (jenis & ukuran); isi file tetap diperiksa backend.
  const pilih = (fs: FileList | null) => {
    const f = fs?.[0];
    if (!f) return;
    impor.reset();
    const tolak = !f.name.toLowerCase().endsWith(".xlsx") ? `"${f.name}" bukan file Excel (.xlsx).`
      : f.size > MAKS_MB_IMPOR * 1024 * 1024 ? `"${f.name}" melebihi ${MAKS_MB_IMPOR} MB.` : null;
    setGalat(tolak);
    setFile(tolak ? null : f);
    if (tolak && masukan.current) masukan.current.value = "";
  };
  const kirim = () => {
    if (!file) return setGalat("Pilih file Excel (.xlsx) terlebih dahulu.");
    setGalat(null);
    impor.mutate();
  };
  const ulang = () => { setFile(null); setGalat(null); impor.reset(); if (masukan.current) masukan.current.value = ""; };
  const pesan = galat ?? impor.error?.message;
  return (
    <HalamanForm judul="Import Master RO dari Excel" tutup={tutup} kirim={kirim} reset={ulang} teksKirim="Import"
      galat={null} sibuk={impor.isPending}>
      {/* Pesan sendiri (bukan `galat` HalamanForm): daftar kesalahan per baris perlu baris baru & bisa panjang. */}
      {pesan && <Peringatan><p className="max-h-72 overflow-y-auto whitespace-pre-line">{pesan}</p></Peringatan>}
      {/* Keterangan singkat fungsi halaman import. */}
      <div className="rounded-2xl border border-emerald-100 bg-linear-to-br from-emerald-50 via-white to-sky-50/60 p-5">
        {/* Ikon unggah sama dengan tombol "Import Excel" di halaman Master RO. */}
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <Upload className="size-5 text-emerald-600" aria-hidden />Import File Excel
        </h2>
        <p className="mt-0.5 text-sm text-slate-600">
          Tambahkan data Program, Kegiatan, KRO, dan RO sekaligus dari satu file Excel (.xlsx). Berisi judul kolom{" "}
          {/* Nama kolom = KOLOM_IMPOR, sama dengan yang dibaca backend. */}
          {KOLOM_IMPOR.map((k, i) => (
            <span key={k}>
              <code className="rounded bg-white px-1 py-0.5 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">{k}</code>
              {i < KOLOM_IMPOR.length - 2 ? ", " : i === KOLOM_IMPOR.length - 2 ? ", dan " : ""}
            </span>
          ))}
          .
        </p>
      </div>
      {/* Isian file bawaan browser ("Choose File" + nama file); hanya tombolnya diberi warna. */}
      <Kolom label="File Excel" wajib petunjuk={`.xlsx, maks. ${MAKS_MB_IMPOR} MB`}>
        <input ref={masukan} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(e) => pilih(e.target.files)}
          className="block w-full cursor-pointer rounded-lg border border-slate-300 bg-white text-sm text-slate-600 shadow-sm file:mr-3 file:cursor-pointer file:border-0 file:border-r file:border-solid file:border-slate-300 file:bg-emerald-50 file:px-4 file:py-2.5 file:text-sm file:font-medium file:text-emerald-700 hover:file:bg-emerald-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-100" />
      </Kolom>
    </HalamanForm>
  );
}

// Isian form Tambah kosong untuk jenis `t` (juga saat jenis diganti).
const isianBaru = (t: Tingkat): Isian => ({ tingkat: t, jalur: {}, kode: "", nama: "", aktif: true, satker: [SATKER_KOSONG] });

// Kunci cache daftar Master RO per tahun; [ENDPOINT, "daftar"] = semua tahun (dimuat ulang setelah simpan/hapus/import).
const KUNCI_DAFTAR = [ENDPOINT, "daftar"];

export default function KelolaMasterRO() {
  const qc = useQueryClient();
  const { tahun } = useOutletContext<KonteksLayout>();  // Tahun Anggaran pilihan di bilah atas
  const q = useQuery({ queryKey: [...KUNCI_DAFTAR, tahun], queryFn: () => api.get<BarisRO[]>(`${ENDPOINT}?tahun=${tahun}`) });
  const semua = q.data ?? [];
  const [sukses, setSukses] = usePesanSukses();
  const [form, setForm] = useState<Isian | null>(null);
  const [impor, setImpor] = useState(false);  // halaman Impor Excel
  const [lihat, setLihat] = useState<BarisRO | null>(null);
  const [dihapus, setDihapus] = useState<BarisRO | null>(null);
  const [f, setF] = useState<NilaiFilter>({});
  // Ganti Tahun Anggaran di bilah atas: tutup form/detail/import/konfirmasi yang terbuka, karena isinya (induk, data)
  // milik tahun sebelumnya.
  useEffect(() => { setForm(null); setImpor(false); setLihat(null); setDihapus(null); }, [tahun]);
  // Referensi KRO Lampiran II SEB 6/2025, dimuat saat form KRO dibuka.
  const qKro = useQuery({ queryKey: [ENDPOINT, "referensi-kro"], queryFn: () => api.get<RefKRO[]>(`${ENDPOINT}/referensi-kro`),
    enabled: form?.tingkat === "KRO", staleTime: Infinity });
  const refKro = useMemo(() => new Map((qKro.data ?? []).map((k) => [k.kode, k])), [qKro.data]);
  // Pilihan Unit Kerja & Satuan Kerja di form = data menu Satuan Kerja (dimuat saat form dibuka).
  const qSatker = useQuery({ queryKey: ["satker"], queryFn: () => api.get<Satker[]>("/api/satker"), enabled: form?.tingkat === "RO" });

  const simpan = useMutation({
    mutationFn: async ({ jalur, satker, ...x }: Isian) => {
      // Satker khusus RO. Baris bullet yang belum lengkap ditolak di browser (backend tetap memeriksa minimal 1 & tidak dobel).
      const ro = x.tingkat === "RO";
      const kurang = ro ? satker.findIndex((s) => !s.satker_id) : -1;
      if (kurang >= 0) throw new Error(satker.length > 1
        ? `Lengkapi Unit Kerja dan Satuan Kerja pada baris ke-${kurang + 1}, atau hapus baris tersebut.`
        : "Pilih Unit Kerja (Eselon I) dan Satuan Kerja (Eselon II).");
      const ti = INDUK[x.tingkat];
      // induk = pilihan jenjang tepat di atasnya
      const isi = { ...x, induk_id: (ti && jalur[ti]) || null, satker_ids: ro ? satker.map((s) => s.satker_id) : [] };
      // Tambah: data baru masuk ke Tahun Anggaran bilah atas. Ubah: tahun data tetap (diabaikan backend).
      return x.id ? api.put<BarisRO>(`${ENDPOINT}/${x.id}`, isi) : api.post<BarisRO>(ENDPOINT, { ...isi, tahun_anggaran: Number(tahun) });
    },
    // Hanya daftar (KUNCI_DAFTAR) yang dimuat ulang; referensi KRO ([ENDPOINT, "referensi-kro"]) statis.
    // Tambah: kembali ke halaman 1, tempat data baru tampil (urut bawaan = terbaru ditambahkan paling atas).
    onSuccess: (r, x) => { setSukses(`${NAMA[r.tingkat]} ${r.kode} berhasil disimpan.`); setForm(null); if (!x.id) pg.ubahHalaman(1); qc.invalidateQueries({ queryKey: KUNCI_DAFTAR }); },
  });
  const hapus = useMutation({
    mutationFn: (x: BarisRO) => api.del(`${ENDPOINT}/${x.id}`),
    onSuccess: (_, x) => { setSukses(`${NAMA[x.tingkat]} ${x.kode} berhasil dihapus.`); setDihapus(null); qc.invalidateQueries({ queryKey: KUNCI_DAFTAR }); },
  });

  // Urutan bawaan = urutan server (terbaru ditambahkan paling atas; data yang dibuat bersamaan tetap berjenjang).
  // Isian filter = kolom tabel dengan urutan yang sama (kunci filter = nama kolom); kotak teks (dicari sebagian),
  // kecuali Status (pilihan) & Tanggal Input.
  const lolos = useMemo(() => semua.filter((x) => KOLOM_JENJANG.every((k) => cocok(f[k], x[k]))
    && cocok(f.unit_kerja, ...x.satker.map((s) => s.unit_kerja)) && cocok(f.satuan_kerja, ...x.satker.map((s) => s.nama))
    && lolosStatus(f.status, x.aktif) && lolosJejak(f, x)), [semua, f]);
  const nilai = (x: BarisRO, { k, jenis }: Kolom) => {
    if (jenis === "satker") return isiSatker(x, k as KolomSatker).join("; ");
    if (jenis === "status") return x.aktif ? "Aktif" : "Nonaktif";
    if (jenis === "oleh") return x.diubah_oleh ?? "Sistem";
    if (jenis === "tanggal") return waktuAngka(x.diubah_at);
    return x[k as KolomDb];
  };
  // Tanggal diurutkan dari nilai ISO (bukan teks tampilan) agar urut waktu benar.
  const ambil = Object.fromEntries(KOLOM.map((c) => [c.k, c.jenis === "tanggal" ? (x: BarisRO) => x.diubah_at ?? "" : (x: BarisRO) => nilai(x, c)]));
  const { baris, urut, klik } = useUrut<BarisRO, KolomUrut>(lolos, ambil as Record<KolomUrut, (x: BarisRO) => string>);
  // Paginasi di browser (bawaan 20 baris); kembali ke halaman 1 setiap filter/urutan berubah.
  const pg = usePaginasi(baris, [f, urut], 20);
  const { tampil, awal } = pg;

  const perId = useMemo(() => new Map(semua.map((x) => [x.id, x])), [semua]);
  // Jalur induk sebuah data dari Program sampai induknya, mis. RO → {PROGRAM, KEGIATAN, KRO}.
  const jalurDari = (x: BarisRO) => {
    const jalur: Partial<Record<Tingkat, string>> = {};
    for (let p = x.induk_id ? perId.get(x.induk_id) : undefined; p; p = p.induk_id ? perId.get(p.induk_id) : undefined) jalur[p.tingkat] = p.id;
    return jalur;
  };
  const buka = (x?: BarisRO) => {
    simpan.reset();
    // Satker: data lama (impor/sebelum Revisi 7) yang belum punya Satker mulai dari 1 baris kosong.
    setForm(x ? { id: x.id, tingkat: x.tingkat, jalur: jalurDari(x), kode: x.kode, nama: x.nama, aktif: x.aktif,
        satker: x.satker.length ? x.satker.map((s) => ({ unit_kerja: nilaiUnitKerja(s), satker_id: s.id })) : [SATKER_KOSONG] }
      : isianBaru("PROGRAM"));
  };

  if (impor) return (
    <ImporExcel tahun={tahun} tutup={() => setImpor(false)} berhasil={(h) => {
      const baru = TINGKAT.filter((t) => h.dibuat[t]).map((t) => `${h.dibuat[t]} ${NAMA[t]}`).join(", ");
      const diisi = h.satker_diisi ? ` Satker ditambahkan ke ${h.satker_diisi} RO yang sudah ada.` : "";
      setSukses((h.total_dibuat ? `Import selesai: ${baru} ditambahkan dari ${h.baris} baris.`
        : "Import selesai: semua data di file sudah ada, tidak ada data baru.") + diisi);
      setImpor(false);
      pg.ubahHalaman(1);  // data baru tampil paling atas, sama seperti setelah Tambah
      qc.invalidateQueries({ queryKey: KUNCI_DAFTAR });
    }} />
  );

  if (lihat) {
    return (
      <HalamanDetail kembali="Master RO" judul={`Detail ${NAMA[lihat.tingkat]} ${lihat.kode}`} tutup={() => setLihat(null)} info={[
        ["Jenis", NAMA[lihat.tingkat]],  // tanpa Kode Lengkap: kode tiap jenjang sudah tampil sendiri-sendiri di bawah
        // Isi = kolom tabel yang terisi (urut Laporan Renja), yaitu sampai jenjang data ini.
        ...KOLOM.filter((c) => c.t).map((c) => [c.label, nilai(lihat, c)] as [string, string]).filter(([, v]) => v),
        // Satker khusus RO: detail Program/Kegiatan/KRO tanpa baris ini.
        ...(lihat.tingkat === "RO" ? [["Unit Kerja (Eselon I)", <DaftarSatker isi={isiSatker(lihat, "unit_kerja")} />],
          ["Satuan Kerja (Eselon II)", <DaftarSatker isi={isiSatker(lihat, "satuan_kerja")} />]] as [string, ReactNode][] : []),
        ["Status", <LencanaAktif aktif={lihat.aktif} />],
        ...barisJejak(lihat),
      ]} />
    );
  }

  if (form) {
    // Pola sama dengan form Satuan Kerja: pilih Jenis (radio) → induk berurut Program → Kegiatan → KRO → Kode & Nama.
    const nama = NAMA[form.tingkat], ti = INDUK[form.tingkat];
    const lama = form.id ? perId.get(form.id) : undefined;
    // Ganti tingkat (hanya saat Tambah) = isi ulang dari awal, seperti ganti jenis di form Satuan Kerja.
    const pilihTingkat = (t: Tingkat) => { simpan.reset(); setForm(isianBaru(t)); };
    // Jenjang di atas data ini dipilih berurut dari Program; tiap pilihan hanya berisi turunan dari pilihan di atasnya.
    const atasan = TINGKAT.slice(0, TINGKAT.indexOf(form.tingkat));
    const jalurLama = lama ? jalurDari(lama) : {};
    // Mengganti satu jenjang mengosongkan pilihan di bawahnya (isinya bergantung pada jenjang ini).
    const pilihJalur = (t: Tingkat, v: string) => setForm({ ...form,
      jalur: Object.fromEntries(atasan.slice(0, atasan.indexOf(t)).map((a) => [a, form.jalur[a]]).concat([[t, v]])) });
    // Hanya data Aktif yang dapat dipilih; jalur lama data yang diubah tetap tampil walau Nonaktif.
    const opsiJenjang = (t: Tingkat, idAtas?: string) => semua
      .filter((x) => x.tingkat === t && (!idAtas || x.induk_id === idAtas) && (x.aktif || x.id === jalurLama[t]))
      .map((x) => ({ nilai: x.id, label: `${teksInduk(x)}${x.aktif ? "" : " (Nonaktif)"}` }));
    const ref = form.tingkat === "KRO" ? refKro.get(form.kode.toUpperCase()) : undefined;
    // Kode KRO yang dikenal mengisi nama otomatis, kecuali nama sudah diketik sendiri (bukan nama referensi lain).
    const ubahKode = (v: string) => {
      const kode = v, baru = form.tingkat === "KRO" ? refKro.get(kode.toUpperCase()) : undefined;
      const namaRef = !form.nama || [...refKro.values()].some((k) => k.nama === form.nama);
      setForm({ ...form, kode, nama: baru && namaRef ? baru.nama : form.nama });
    };
    return (
      <HalamanForm judul={form.id ? `Ubah ${nama}` : "Tambah Master RO"}
        tutup={() => setForm(null)} kirim={() => simpan.mutate(form)} galat={simpan.error} sibuk={simpan.isPending}
        reset={form.id ? undefined : () => pilihTingkat(form.tingkat)}>
        <fieldset className="space-y-1.5" disabled={!!form.id}>
          <legend className="text-sm font-medium text-slate-700">Jenis<span className="text-red-600"> *</span></legend>
          <div className="flex flex-wrap gap-6">
            {TINGKAT.map((t) => (
              <label key={t} className={cx("flex items-center gap-2 text-sm", form.id && t !== form.tingkat && "text-slate-400")}>
                <input type="radio" name="tingkat" checked={form.tingkat === t} onChange={() => pilihTingkat(t)} />{NAMA[t]}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="grid gap-3 sm:grid-cols-2">
          {atasan.map((t, n) => {
            // Induk dipilih lebih dulu, berurut dari Program (selebar form). Jenjang berikutnya terkunci sampai jenjang
            // di atasnya dipilih, dan hanya berisi turunannya (mis. Kegiatan milik Program terpilih saja).
            const atas = n > 0 ? atasan[n - 1] : undefined, idAtas = atas ? form.jalur[atas] : undefined;
            const terkunci = !!atas && !idAtas;
            return (
              <div key={t} className="sm:col-span-2">
                <Kolom label={t === ti ? `${NAMA[t]} (induk)` : NAMA[t]} wajib>
                  <PilihBawah nilai={form.jalur[t] ?? ""} ubah={(v) => pilihJalur(t, v)} disabled={terkunci}
                    kosong={terkunci ? `— pilih ${NAMA[atas!]} terlebih dahulu —` : `— pilih ${NAMA[t]} —`} opsi={terkunci ? [] : opsiJenjang(t, idAtas)} />
                </Kolom>
              </div>
            );
          })}
          <Kolom label={`Kode ${nama}`} wajib petunjuk={form.tingkat === "RO" ? "Nama RO tidak boleh sama dalam satu KRO." : undefined}>
            <Input required maxLength={MAKS_KODE} value={form.kode}
              onChange={(e) => ubahKode(e.target.value)} />
            {/* Tanpa daftar saran browser (datalist): kotak ketik biasa seperti Kode UKE di Satuan Kerja. */}
            {/* Daftar referensi kosong (data KRO tidak di-commit) = tanpa saran & tanpa peringatan. */}
            {form.tingkat === "KRO" && form.kode.length === 3 && !!qKro.data?.length && (ref
              ? <span className="block text-xs text-emerald-700">Lampiran II: {ref.nama}{ref.pn ? " (PN)" : ""} · satuan {ref.satuan}</span>
              : <span className="block text-xs text-amber-700">Kode ini tidak ada di Lampiran II SEB No. 6/2025. Periksa kembali kodenya.</span>)}
          </Kolom>
          <Kolom label={`Nama ${nama}`} wajib petunjuk={form.tingkat === "PROGRAM" ? "Diawali kata \"Program\", mis. Program Dukungan Manajemen." : undefined}>
            <Input required maxLength={255} placeholder={form.tingkat === "PROGRAM" ? "Program …" : undefined} value={form.nama}
              onChange={(e) => setForm({ ...form, nama: e.target.value })} />
          </Kolom>
          {/* Unit Kerja & Satuan Kerja khusus RO (permintaan pemilik produk). */}
          {form.tingkat === "RO" && (
            <IsianSatkerRO daftar={qSatker.data ?? []} baris={form.satker} ubah={(satker) => setForm({ ...form, satker })}
              dipakai={new Set(lama?.satker.map((s) => s.id))}
              memuat={qSatker.isLoading} galat={qSatker.error} />
          )}
          {form.id && (
            <div className="space-y-1.5">
              <span className="text-sm font-medium text-slate-700">Status</span>
              <div><Saklar aktif={form.aktif} ubah={(v) => setForm({ ...form, aktif: v })} label={`Status ${nama}`} /></div>
              <span className="block text-xs text-slate-500">{nama} Nonaktif tetap tampil, tetapi tidak dapat dipilih sebagai induk data baru.</span>
            </div>
          )}
        </div>
      </HalamanForm>
    );
  }

  return (
    <div className="w-full">
      <Judul judul="Master RO"
        aksi={<div className="flex flex-wrap gap-2">
          <Tombol varian="sekunder" onClick={() => setImpor(true)}><Upload className="size-4" />Import Excel</Tombol>
          <Tombol onClick={() => buka()}><Plus className="size-4" />Tambah Master RO</Tombol>
        </div>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {!!semua.length && (
        <FormFilter judul="Master RO" nilai={f} terapkan={setF} kolomPerBaris={6} bidang={[
          // Kotak teks (permintaan pemilik produk), urut sesuai kolom tabel; Status = pilihan, Tanggal Input = pilih tanggal.
          // Grid 6 kolom selang-seling sempit/lebar: baris 1 = kode & nama Program/Kegiatan/KRO; baris 2 = Kode RO, RO,
          // Status, Diinput Oleh, Tanggal Input — isian sempit (kode, Status, Tanggal) lurus di kolom sempit.
          { jenis: "teks", kunci: "kode_program", label: "Kode Program", placeholder: "Cari kode, mis. GH…", kecil: true },
          { jenis: "teks", kunci: "program", label: "Program", placeholder: "Cari nama program…" },
          { jenis: "teks", kunci: "kode_kegiatan", label: "Kode Kegiatan", placeholder: "Cari kode, mis. 4511…", kecil: true },
          { jenis: "teks", kunci: "kegiatan", label: "Kegiatan", placeholder: "Cari nama kegiatan…" },
          { jenis: "teks", kunci: "kode_kro", label: "Kode KRO", placeholder: "Cari kode, mis. EBA…", kecil: true },
          { jenis: "teks", kunci: "kro", label: "KRO", placeholder: "Cari nama KRO…" },
          { jenis: "teks", kunci: "kode_ro", label: "Kode RO", placeholder: "Cari kode, mis. 001…", kecil: true },
          { jenis: "teks", kunci: "ro", label: "RO", placeholder: "Cari nama RO…" },
          { jenis: "teks", kunci: "unit_kerja", label: "Unit Kerja (Eselon I)", placeholder: "Cari unit kerja…" },
          { jenis: "teks", kunci: "satuan_kerja", label: "Satuan Kerja (Eselon II)", placeholder: "Cari satuan kerja…" },
          { jenis: "pilih", kunci: "status", label: "Status", semua: "Semua Status", opsi: OPSI_STATUS, kecil: true },
          { jenis: "teks", kunci: "oleh", label: "Diinput Oleh", placeholder: "Cari nama penginput…" },
          { jenis: "tanggal", kunci: "tanggal", label: "Tanggal Input", kecil: true },
        ]} />
      )}
      {q.isLoading ? <Memuat /> : q.error ? <Peringatan>{(q.error as Error).message}</Peringatan> : !semua.length ? <Kosong>Belum ada data Master RO.</Kosong>
        : baris.length === 0 ? <Kosong>Tidak ada data Master RO yang cocok dengan filter.</Kosong> : (
        <Kartu><TabelGeser>
          <table className="w-full min-w-[124rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
              <tr>{th("No")}{KOLOM.map((x) => <ThUrut key={x.k} label={x.label} kolom={x.k} urut={urut} klik={klik}
                className={kolomRO(x) ? "bg-utama-100" : x.jenis === "satker" ? LEBAR_KOLOM_SATKER : undefined} />)}{th("Aksi")}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">{tampil.map((x, i) => (
              <tr key={x.id} className={cx("align-middle transition-colors hover:bg-slate-50", !x.aktif && "bg-slate-50")}>
                <td className={cx(TD, "text-slate-500")}>{awal + i + 1}</td>
                {KOLOM.map((c) => {
                  if (c.jenis === "status") return <td key={c.k} className={cx(TD, "whitespace-nowrap")}><LencanaAktif aktif={x.aktif} /></td>;
                  // Unit Kerja + Satuan Kerja = satu sel selebar dua kolom (bullet berpasangan sejajar); sel Satuan Kerja
                  // sendiri tidak dibuat.
                  if (c.k === "satuan_kerja") return null;
                  if (c.jenis === "satker")
                    return <td key={c.k} colSpan={2} className={cx(TD, !x.aktif ? "text-slate-400" : "text-slate-700")}>
                      <SatkerSejajar daftar={x.satker} /></td>;
                  // Diinput Oleh & Tanggal Input: gaya sama dengan tabel Checklist.
                  if (c.jenis === "oleh" || c.jenis === "tanggal")
                    return <td key={c.k} className={cx(TD, "whitespace-nowrap text-slate-600", c.jenis === "oleh" ? "min-w-[9rem]" : "min-w-[9.5rem]")}>
                      {c.jenis === "tanggal" ? <TanggalJam iso={x.diubah_at} /> : nilai(x, c)}</td>;
                  const milik = c.t === x.tingkat;  // kolom milik baris ini sendiri (bukan induknya)
                  return (
                    <td key={c.k} className={cx(TD, c.jenis === "kode" ? "whitespace-nowrap" : "min-w-[12rem]", kolomRO(c) && "bg-utama-50",
                      !x.aktif ? "text-slate-400" : milik ? "font-medium text-slate-900" : "text-slate-700")}>
                      {nilai(x, c) || "—"}
                    </td>
                  );
                })}
                <Aksi nama={`${NAMA[x.tingkat]} ${x.kode}`} lihat={() => setLihat(x)} ubah={() => buka(x)} hapus={() => { hapus.reset(); setDihapus(x); }} />
              </tr>))}</tbody>
          </table></TabelGeser>
        </Kartu>
      )}
      {baris.length > 0 && <Paginasi {...pg} />}

      {dihapus && (
        <Konfirmasi bahaya buka judul={`Hapus ${NAMA[dihapus.tingkat]} secara permanen?`} teksYa="Ya, hapus" teksBatal="Batal"
          baris={[["Jenis", NAMA[dihapus.tingkat]], ["Kode Lengkap", dihapus.kode_lengkap], [`Nama ${NAMA[dihapus.tingkat]}`, dihapus.nama],
            ...(ANAK[dihapus.tingkat] ? [[`Jumlah ${NAMA[ANAK[dihapus.tingkat]!]}`, String(dihapus.jumlah_turunan)] as [string, string]] : [])]}
          pesan={dihapus.jumlah_turunan > 0
            ? `${NAMA[dihapus.tingkat]} ini masih memiliki ${NAMA[ANAK[dihapus.tingkat]!]} di bawahnya sehingga tidak dapat dihapus. Hapus atau pindahkan turunannya terlebih dahulu.`
            : "Data dihapus dan tidak dapat dikembalikan."}
          galat={hapus.error?.message} memuat={hapus.isPending} batal={() => setDihapus(null)} ya={() => hapus.mutate(dihapus)} />
      )}
    </div>
  );
}
