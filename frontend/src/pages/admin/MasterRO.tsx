/** Master RO (khusus Reviewer): CRUD berjenjang Program → Kegiatan → KRO → RO.
 *  Tampilan mengikuti menu Satuan Kerja: SATU tabel berkolom Kode Program, Program, Kode Kegiatan, Kegiatan, Kode KRO,
 *  KRO, Kode RO, RO (tiap baris = satu data beserta induk-induknya; kolom tingkat di bawahnya kosong), filter berurutan
 *  sesuai kolom, 3 ikon aksi, detail & form sebagai halaman sendiri. Aturan induk/kode/hapus dijaga backend
 *  (app/api/master_ro.py). Format kode mengikuti SEB No. 6/2025; KRO diberi saran dari Lampiran II (bukan wajib).
 *  Kolom tabel = kolom database `master_ro` (Unit Eselon I/II dan Prioritas dihapus, migrasi 0019; permintaan pemilik
 *  produk). Tabel dipaginasi (pilihan 10/20/50/100 baris), bawaan 20 baris per halaman. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Upload } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { api } from "../../api";
import { Aksi, HalamanDetail, HalamanForm, type Jejak, LencanaAktif, PilihBawah, TD, barisJejak, th, usePesanSukses } from "../../components/Kelola";
import { FormFilter, type NilaiFilter, OPSI_STATUS, Paginasi, ThUrut, cocok, lolosJejak, lolosStatus, usePaginasi, useUrut } from "../../components/TabelData";
import { waktuAngka } from "../../format";
import { Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Memuat, Peringatan, Saklar, TanggalJam, Tombol, cx } from "../../ui";

type Tingkat = "PROGRAM" | "KEGIATAN" | "KRO" | "RO";
// Kolom datar tabel `master_ro` (dikirim backend apa adanya; kosong untuk jenjang di bawah data ini).
type KolomDb = "kode_program" | "program" | "kode_kegiatan" | "kegiatan" | "kode_kro" | "kro" | "kode_ro" | "ro";
type BarisRO = {
  id: string; tingkat: Tingkat; kode: string; kode_lengkap: string; nama: string; aktif: boolean;
  induk_id: string | null; jumlah_turunan: number;
} & Record<KolomDb, string> & Jejak;
// `jalur` = id data terpilih per jenjang di atas data ini (Program → … → induk), dipilih berurut di form; induk = jenjang
// terakhirnya.
type Isian = { id?: string; tingkat: Tingkat; jalur: Partial<Record<Tingkat, string>>; kode: string; nama: string; aktif: boolean };

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
type KolomUrut = KolomDb | "aktif" | "oleh" | "tanggal";
type Kolom = { k: KolomUrut; t?: Tingkat; label: string; jenis: "kode" | "nama" | "status" | "oleh" | "tanggal" };
const kodeNama = (t: Tingkat): Kolom[] => [{ k: KOLOM_DB[t][0], t, label: `Kode ${NAMA[t]}`, jenis: "kode" }, { k: KOLOM_DB[t][1], t, label: NAMA[t], jenis: "nama" }];
const KOLOM_JENJANG = TINGKAT.flatMap((t) => KOLOM_DB[t]);
const KOLOM: Kolom[] = [...TINGKAT.flatMap(kodeNama), { k: "aktif", label: "Status", jenis: "status" },
  { k: "oleh", label: "Diinput Oleh", jenis: "oleh" }, { k: "tanggal", label: "Tanggal Input", jenis: "tanggal" }];


const teksInduk = (x: { kode: string; nama: string }) => `${x.kode} — ${x.nama}`;

type HasilImpor = { baris: number; dibuat: Record<Tingkat, number>; total_dibuat: number; sudah_ada: number };

/** Halaman Import Excel: isian file bawaan browser, .xlsx (maks. 5 MB), lalu POST /api/master-ro/impor. Format
 *  kolom = KOLOM_JENJANG; aturan & penyimpanan semua-atau-tidak dijaga backend, daftar kesalahan per baris Excel
 *  ditampilkan apa adanya (satu kesalahan per baris teks). */
const MAKS_MB_IMPOR = 5;
function ImporExcel({ tutup, berhasil }: { tutup: () => void; berhasil: (h: HasilImpor) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const masukan = useRef<HTMLInputElement>(null);
  const impor = useMutation({
    mutationFn: () => { const fd = new FormData(); fd.append("file", file!); return api.post<HasilImpor>(`${ENDPOINT}/impor`, fd); },
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
          {/* Nama kolom = KOLOM_JENJANG, sama dengan yang dibaca backend. */}
          {KOLOM_JENJANG.map((k, i) => (
            <span key={k}>
              <code className="rounded bg-white px-1 py-0.5 font-mono text-xs font-semibold text-slate-800 ring-1 ring-slate-200">{k}</code>
              {i < KOLOM_JENJANG.length - 2 ? ", " : i === KOLOM_JENJANG.length - 2 ? ", dan " : ""}
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

export default function KelolaMasterRO() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: [ENDPOINT], queryFn: () => api.get<BarisRO[]>(ENDPOINT) });
  const semua = q.data ?? [];
  const [sukses, setSukses] = usePesanSukses();
  const [form, setForm] = useState<Isian | null>(null);
  const [impor, setImpor] = useState(false);  // halaman Impor Excel
  const [lihat, setLihat] = useState<BarisRO | null>(null);
  const [dihapus, setDihapus] = useState<BarisRO | null>(null);
  const [f, setF] = useState<NilaiFilter>({});
  // Referensi KRO Lampiran II SEB 6/2025, dimuat saat form KRO dibuka.
  const qKro = useQuery({ queryKey: [ENDPOINT, "referensi-kro"], queryFn: () => api.get<RefKRO[]>(`${ENDPOINT}/referensi-kro`),
    enabled: form?.tingkat === "KRO", staleTime: Infinity });
  const refKro = useMemo(() => new Map((qKro.data ?? []).map((k) => [k.kode, k])), [qKro.data]);

  const simpan = useMutation({
    mutationFn: ({ jalur, ...x }: Isian) => {
      const ti = INDUK[x.tingkat];
      const isi = { ...x, induk_id: (ti && jalur[ti]) || null };  // induk = pilihan jenjang tepat di atasnya
      return x.id ? api.put<BarisRO>(`${ENDPOINT}/${x.id}`, isi) : api.post<BarisRO>(ENDPOINT, isi);
    },
    // exact: referensi KRO ([ENDPOINT, "referensi-kro"]) statis, tidak perlu dimuat ulang.
    // Tambah: kembali ke halaman 1, tempat data baru tampil (urut bawaan = terbaru ditambahkan paling atas).
    onSuccess: (r, x) => { setSukses(`${NAMA[r.tingkat]} ${r.kode} berhasil disimpan.`); setForm(null); if (!x.id) pg.ubahHalaman(1); qc.invalidateQueries({ queryKey: [ENDPOINT], exact: true }); },
  });
  const hapus = useMutation({
    mutationFn: (x: BarisRO) => api.del(`${ENDPOINT}/${x.id}`),
    onSuccess: (_, x) => { setSukses(`${NAMA[x.tingkat]} ${x.kode} berhasil dihapus.`); setDihapus(null); qc.invalidateQueries({ queryKey: [ENDPOINT], exact: true }); },
  });

  // Urutan bawaan = urutan server (terbaru ditambahkan paling atas; data yang dibuat bersamaan tetap berjenjang).
  // Isian filter = kolom tabel dengan urutan yang sama (kunci filter = nama kolom); kotak teks (dicari sebagian),
  // kecuali Status (pilihan) & Tanggal Input.
  const lolos = useMemo(() => semua.filter((x) => KOLOM_JENJANG.every((k) => cocok(f[k], x[k]))
    && lolosStatus(f.status, x.aktif) && lolosJejak(f, x)), [semua, f]);
  const nilai = (x: BarisRO, { k, jenis }: Kolom) => {
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
    setForm(x ? { id: x.id, tingkat: x.tingkat, jalur: jalurDari(x), kode: x.kode, nama: x.nama, aktif: x.aktif }
      : { tingkat: "PROGRAM", jalur: {}, kode: "", nama: "", aktif: true });
  };

  if (impor) return (
    <ImporExcel tutup={() => setImpor(false)} berhasil={(h) => {
      const baru = TINGKAT.filter((t) => h.dibuat[t]).map((t) => `${h.dibuat[t]} ${NAMA[t]}`).join(", ");
      setSukses(h.total_dibuat ? `Import selesai: ${baru} ditambahkan dari ${h.baris} baris.`
        : "Import selesai: semua data di file sudah ada, tidak ada data baru.");
      setImpor(false);
      pg.ubahHalaman(1);  // data baru tampil paling atas, sama seperti setelah Tambah
      qc.invalidateQueries({ queryKey: [ENDPOINT], exact: true });
    }} />
  );

  if (lihat) {
    return (
      <HalamanDetail kembali="Master RO" judul={`Detail ${NAMA[lihat.tingkat]} ${lihat.kode}`} tutup={() => setLihat(null)} info={[
        ["Jenis", NAMA[lihat.tingkat]],  // tanpa Kode Lengkap: kode tiap jenjang sudah tampil sendiri-sendiri di bawah
        // Isi = kolom tabel yang terisi (urut Laporan Renja), yaitu sampai jenjang data ini.
        ...KOLOM.filter((c) => c.t).map((c) => [c.label, nilai(lihat, c)] as [string, string]).filter(([, v]) => v),
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
    const pilihTingkat = (t: Tingkat) => { simpan.reset(); setForm({ tingkat: t, jalur: {}, kode: "", nama: "", aktif: true }); };
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
          { jenis: "pilih", kunci: "status", label: "Status", semua: "Semua Status", opsi: OPSI_STATUS, kecil: true },
          { jenis: "teks", kunci: "oleh", label: "Diinput Oleh", placeholder: "Cari nama penginput…" },
          { jenis: "tanggal", kunci: "tanggal", label: "Tanggal Input", kecil: true },
        ]} />
      )}
      {q.isLoading ? <Memuat /> : q.error ? <Peringatan>{(q.error as Error).message}</Peringatan> : !semua.length ? <Kosong>Belum ada data Master RO.</Kosong>
        : baris.length === 0 ? <Kosong>Tidak ada data Master RO yang cocok dengan filter.</Kosong> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full min-w-[96rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
              <tr>{th("No")}{KOLOM.map((x) => <ThUrut key={x.k} label={x.label} kolom={x.k} urut={urut} klik={klik} />)}{th("Aksi")}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">{tampil.map((x, i) => (
              <tr key={x.id} className={cx("align-middle transition-colors hover:bg-slate-50", !x.aktif && "bg-slate-50")}>
                <td className={cx(TD, "text-slate-500")}>{awal + i + 1}</td>
                {KOLOM.map((c) => {
                  if (c.jenis === "status") return <td key={c.k} className={cx(TD, "whitespace-nowrap")}><LencanaAktif aktif={x.aktif} /></td>;
                  // Diinput Oleh & Tanggal Input: gaya sama dengan tabel Checklist.
                  if (c.jenis === "oleh" || c.jenis === "tanggal")
                    return <td key={c.k} className={cx(TD, "whitespace-nowrap text-slate-600", c.jenis === "oleh" ? "min-w-[9rem]" : "min-w-[9.5rem]")}>
                      {c.jenis === "tanggal" ? <TanggalJam iso={x.diubah_at} /> : nilai(x, c)}</td>;
                  const milik = c.t === x.tingkat;  // kolom milik baris ini sendiri (bukan induknya)
                  return (
                    <td key={c.k} className={cx(TD, c.jenis === "kode" ? "whitespace-nowrap" : "min-w-[12rem]",
                      !x.aktif ? "text-slate-400" : milik ? "font-medium text-slate-900" : "text-slate-700")}>
                      {nilai(x, c) || "—"}
                    </td>
                  );
                })}
                <Aksi nama={`${NAMA[x.tingkat]} ${x.kode}`} lihat={() => setLihat(x)} ubah={() => buka(x)} hapus={() => { hapus.reset(); setDihapus(x); }} />
              </tr>))}</tbody>
          </table>
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
