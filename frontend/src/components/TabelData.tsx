/** Filter & sorting bersama untuk tabel daftar (Panduan, Checklist, Kategori, Satuan Kerja, Pengguna).
 *  Semuanya dikerjakan di browser atas data yang sudah dimuat; tidak mengubah data di server. */
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ChevronLeft, ChevronRight, Filter, RotateCcw, Search } from "lucide-react";
import { type CSSProperties, type FocusEvent, Fragment, type KeyboardEvent, type ReactNode, useEffect, useId, useLayoutEffect, useMemo, useRef,
  useState } from "react";
import { Input, Kartu, Pilih, Tombol, cx, gayaInput } from "../ui";

/** Wadah tabel lebar (desain.md §7 no. 52 & 56): baris judul menempel di atas saat halaman digulir ke bawah, `beku` kolom
 *  pertama diam saat tabel digeser ke kanan (hanya menu Pengajuan; menu lain tanpa kolom beku = 0), dan bilah geser
 *  kiri/kanan menempel di bawah layar. Gulir atas/bawah memakai gulir halaman. Letakkan langsung di dalam `Kartu` tanpa
 *  overflow; gaya di index.css (`.tabel-geser`).
 *
 *  Cara kerja: wadah gulir mana pun akan membuat judul kolom sticky terhadap wadah itu, bukan halaman. Karena itu wadah
 *  hanya memotong (clip) dan tabel digeser dengan CSS `--geser` dari bilah bawah; geser trackpad/Shift+roda, sentuh, dan
 *  fokus keyboard diteruskan ke bilah itu. */
export function TabelGeser({ beku = 0, children }: { beku?: 0 | 1 | 2 | 3; children: ReactNode }) {
  const wadah = useRef<HTMLDivElement>(null), bilah = useRef<HTMLDivElement>(null), sentuh = useRef<{ x: number; y: number; kiri: number } | null>(null);
  const [lebar, setLebar] = useState(0);  // lebar tabel bila melebihi wadah; 0 = muat, bilah disembunyikan
  const geser = () => wadah.current?.style.setProperty("--geser", `${bilah.current?.scrollLeft ?? 0}px`);
  // Tanpa deps: tabel di dalamnya bisa berganti (data dimuat ulang); observer lama diputus tiap render.
  useLayoutEffect(() => {
    const w = wadah.current, t = w?.firstElementChild as HTMLElement | null;
    if (!w || !t) return;
    const ukur = () => { setLebar(t.offsetWidth > w.clientWidth + 1 ? t.offsetWidth : 0); geser(); };
    const ro = new ResizeObserver(ukur);
    ro.observe(w); ro.observe(t);
    return () => ro.disconnect();
  });
  const tambah = (d: number) => { if (bilah.current) bilah.current.scrollLeft += d; };
  // Fokus (Tab) ke sel yang tertutup kolom beku atau berada di luar sisi kanan → geser sampai terlihat.
  const tampakkan = (e: FocusEvent) => {
    const w = wadah.current, sel = (e.target as HTMLElement).closest("td, th") as HTMLTableCellElement | null;
    if (!w || !lebar || !sel || sel.cellIndex < beku) return;
    const r = (e.target as HTMLElement).getBoundingClientRect(), k = w.getBoundingClientRect();
    const kiri = (beku && w.querySelector(`thead th:nth-child(${beku})`)?.getBoundingClientRect().right) || k.left;
    if (r.right > k.right) tambah(r.right - k.right + 16);
    else if (r.left < kiri) tambah(r.left - kiri - 16);
  };
  return (
    <>
      <div ref={wadah} className="tabel-geser" data-beku={beku} onFocus={tampakkan}
        onWheel={(e) => tambah(e.deltaX || (e.shiftKey ? e.deltaY : 0))}
        onTouchStart={(e) => { const t = e.touches[0]; sentuh.current = { x: t.clientX, y: t.clientY, kiri: bilah.current?.scrollLeft ?? 0 }; }}
        onTouchMove={(e) => {
          const s = sentuh.current, t = e.touches[0];
          if (s && bilah.current && Math.abs(t.clientX - s.x) > Math.abs(t.clientY - s.y)) bilah.current.scrollLeft = s.kiri - (t.clientX - s.x);
        }}>
        {children}
      </div>
      <div ref={bilah} onScroll={geser} aria-hidden className={cx("tabel-geser-bilah rounded-b-[inherit] border-t border-slate-200 bg-white", !lebar && "hidden")}>
        <div className="h-px" style={{ width: lebar }} />
      </div>
    </>
  );
}

export type Urut<K extends string> = { kolom: K | null; naik: boolean };
type Ambil<T, K extends string> = Record<K, (x: T) => string | number>;

/** Pengurutan kolom: klik 1× naik, 2× turun, 3× kembali ke urutan bawaan (urutan dari server). sort() stabil, jadi
 *  baris dengan nilai sama tetap dalam urutan bawaan. `banding` mengganti pembanding teks untuk kolom tertentu. */
export function useUrut<T, K extends string>(data: T[], ambil: Ambil<T, K>, banding: Partial<Record<K, (a: string, b: string) => number>> = {}) {
  const [urut, setUrut] = useState<Urut<K>>({ kolom: null, naik: true });
  const baris = useMemo(() => {
    const k = urut.kolom;
    if (k === null) return data;
    const f = ambil[k];
    return [...data].sort((a, b) => {
      const x = f(a), y = f(b);
      const h = typeof x === "number" && typeof y === "number" ? x - y
        : (banding[k] ?? ((p: string, q: string) => p.localeCompare(q, "id", { numeric: true, sensitivity: "base" })))(String(x), String(y));
      return urut.naik ? h : -h;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, urut]);
  const klik = (k: K) => setUrut((u) => (u.kolom !== k ? { kolom: k, naik: true } : u.naik ? { kolom: k, naik: false } : { kolom: null, naik: true }));
  return { baris, urut, klik };
}

/** Sel judul kolom yang bisa diurutkan. */
export function ThUrut<K extends string>({ label, kolom, urut, klik, className }: {
  label: string; kolom: K; urut: Urut<K>; klik: (k: K) => void; className?: string;
}) {
  const aktif = urut.kolom === kolom;
  const Ikon = !aktif ? ArrowUpDown : urut.naik ? ArrowUp : ArrowDown;
  return (
    <th scope="col" className={cx("whitespace-nowrap px-3 py-2.5 text-center", className)} aria-sort={aktif ? (urut.naik ? "ascending" : "descending") : undefined}>
      <button type="button" onClick={() => klik(kolom)} title={`Urutkan berdasarkan ${label}`}
        className="inline-flex items-center gap-1 rounded font-semibold hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100">
        {/* Penyeimbang selebar ikon agar teks judul tepat di tengah kolom (sejajar dengan isi yang rata tengah). */}
        <span className="size-3.5 shrink-0" aria-hidden />{label}<Ikon className={cx("size-3.5", aktif ? "text-utama-600" : "text-slate-400")} aria-hidden />
      </button>
    </th>
  );
}

/** Cocokkan teks pencarian (tanpa memedulikan huruf besar/kecil) ke salah satu isi baris. */
export const cocok = (cari: string | undefined, ...isi: (string | null | undefined)[]) => {
  const k = (cari ?? "").trim().toLowerCase();
  return !k || isi.some((s) => (s ?? "").toLowerCase().includes(k));
};

/** Filter Status: "" = semua, "aktif", "nonaktif". */
export const lolosStatus = (f: string | undefined, aktif: boolean) => !f || (f === "aktif") === aktif;
export const OPSI_STATUS = [{ nilai: "aktif", label: "Aktif" }, { nilai: "nonaktif", label: "Nonaktif" }];

/** Tanggal lokal (zona waktu browser) YYYY-MM-DD dari ISO, agar sama dengan tanggal yang tampil di tabel. */
const tanggalLokal = (iso?: string | null) => {
  const d = iso ? new Date(iso) : null;
  if (!d || Number.isNaN(+d)) return "";
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
/** Apakah tanggal `iso` jatuh pada tanggal `tgl` (YYYY-MM-DD, zona waktu browser). `tgl` kosong = semua lolos;
 *  baris tanpa tanggal tidak lolos bila `tgl` diisi. */
export const padaTanggal = (iso: string | null | undefined, tgl?: string) => !tgl || tanggalLokal(iso) === tgl;

/** Filter jejak yang sama di semua menu master: "Diinput Oleh" (`f.oleh`, kosong = "Sistem") & "Tanggal Input" (`f.tanggal`). */
export const lolosJejak = (f: Record<string, string>, x: { diubah_oleh?: string | null; diubah_at?: string | null }) =>
  cocok(f.oleh, x.diubah_oleh ?? "Sistem") && padaTanggal(x.diubah_at, f.tanggal);

export type NilaiFilter = Record<string, string>;
// Kelas ditulis utuh agar terbaca Tailwind (nama kelas tidak boleh dirakit dari variabel).
const KOLOM_XL: Record<number, string> = { 1: "xl:grid-cols-1", 2: "xl:grid-cols-2", 3: "xl:grid-cols-3", 4: "xl:grid-cols-4", 5: "xl:grid-cols-5" };
type Opsi = { nilai: string; label: string };
/** Satu kolom form filter. `tanggal` = satu tanggal (data pada tanggal itu).
 *  `kecil`: di layar lebar kolom ini lebih sempit dari kolom lain (untuk isian pendek, mis. Status/Tanggal). */
export type Bidang = (
  | { jenis: "teks"; kunci: string; label: string; placeholder: string }
  | { jenis: "pilih"; kunci: string; label: string; semua: string; opsi: Opsi[] }
  | { jenis: "tanggal"; kunci: string; label: string }
) & { kecil?: boolean };

/** Dropdown pilihan (dipakai <Paginasi>). Sengaja tidak memakai <select> bawaan: daftar bawaan browser selebar opsi
 *  terpanjang dan digeser ke kiri bila tidak muat, sehingga tidak sejajar dengan kotaknya (mis. nama Satuan Kerja yang
 *  panjang). Daftar ini selalu dimulai tepat di bawah kotak (tepi kiri sama), minimal selebar kotak, dan dibatasi sampai
 *  tepi kanan layar; nama yang lebih panjang turun ke baris berikutnya, tidak dipotong.
 *  Keyboard: ↑/↓/Home/End memindah sorotan, Enter/Spasi memilih, Esc/Tab menutup.
 *  Opsional (default tidak berubah): `semua` kosong = tanpa opsi "Semua …"; `kecil` = kotak h-8 selebar isinya;
 *  `keAtas` = daftar terbuka ke atas (mis. di bawah tabel). */
function PilihDaftar({ labelId, nilai, ubah, semua, opsi, kecil, keAtas }: {
  labelId: string; nilai: string; ubah: (v: string) => void; semua?: string; opsi: Opsi[]; kecil?: boolean; keAtas?: boolean;
}) {
  const daftarOpsi = useMemo(() => (semua ? [{ nilai: "", label: semua }, ...opsi] : opsi), [semua, opsi]);
  const [buka, setBuka] = useState(false);
  const [sorot, setSorot] = useState(0);
  const [lebarMaks, setLebarMaks] = useState<number>();
  const akar = useRef<HTMLDivElement>(null);
  const daftar = useRef<HTMLUListElement>(null);
  const idDaftar = useId();
  const terpilih = daftarOpsi.find((o) => o.nilai === nilai) ?? daftarOpsi[0];

  // Klik di luar dropdown menutup daftar.
  useEffect(() => {
    if (!buka) return;
    const tutup = (e: MouseEvent) => { if (!akar.current?.contains(e.target as Node)) setBuka(false); };
    document.addEventListener("mousedown", tutup);
    return () => document.removeEventListener("mousedown", tutup);
  }, [buka]);
  // Opsi yang disorot selalu terlihat saat daftar digulir dengan keyboard.
  useEffect(() => { if (buka) daftar.current?.children[sorot]?.scrollIntoView({ block: "nearest" }); }, [buka, sorot]);

  const bukaDaftar = () => {
    const r = akar.current?.getBoundingClientRect();
    if (r) setLebarMaks(Math.max(r.width, document.documentElement.clientWidth - r.left - 16));
    setSorot(Math.max(0, daftarOpsi.findIndex((o) => o.nilai === nilai)));
    setBuka(true);
  };
  const pilih = (i: number) => { ubah(daftarOpsi[i].nilai); setBuka(false); };
  const tekan = (e: KeyboardEvent<HTMLButtonElement>) => {
    const akhir = daftarOpsi.length - 1;
    if (!buka) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); bukaDaftar(); }
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); setSorot((i) => Math.min(i + 1, akhir)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSorot((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Home") { e.preventDefault(); setSorot(0); }
    else if (e.key === "End") { e.preventDefault(); setSorot(akhir); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pilih(sorot); }
    else if (e.key === "Escape") { e.preventDefault(); setBuka(false); }
    else if (e.key === "Tab") setBuka(false);
  };

  return (
    <div ref={akar} className="relative">
      <button type="button" role="combobox" aria-haspopup="listbox" aria-expanded={buka} aria-controls={idDaftar}
        aria-labelledby={labelId} aria-activedescendant={buka ? `${idDaftar}-${sorot}` : undefined}
        onClick={() => (buka ? setBuka(false) : bukaDaftar())} onKeyDown={tekan} title={terpilih.label}
        className={cx(gayaInput, "relative box-border flex items-center pr-8 text-left leading-normal", kecil ? "h-8 w-auto! min-w-16" : "h-10")}>
        {/* Gaya kotak sama persis dengan <Pilih> (gayaInput); panah dibuat setebal & segelap panah <select> bawaan. */}
        <span className="truncate">{terpilih.label}</span>
        <ChevronDown strokeWidth={2.5} className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-slate-900" aria-hidden />
      </button>
      {buka && (
        <ul ref={daftar} id={idDaftar} role="listbox" aria-labelledby={labelId} style={{ maxWidth: lebarMaks }}
          className={cx("absolute left-0 z-30 max-h-[min(600px,70vh)] w-max min-w-full overflow-auto border border-slate-400 bg-white text-sm shadow-md",
            keAtas ? "bottom-full" : "top-full")}>
          {/* Sorotan biru warna utama (#2553e0) + teks putih, sama dengan dropdown form (PilihBawah); tanpa huruf tebal. */}
          {daftarOpsi.map((o, i) => (
            <li key={o.nilai} id={`${idDaftar}-${i}`} role="option" aria-selected={o.nilai === nilai}
              onMouseDown={(e) => e.preventDefault()} onMouseEnter={() => setSorot(i)} onClick={() => pilih(i)}
              className={cx("cursor-default py-[5px] pl-[18px] pr-4", i === sorot ? "bg-utama-600 text-white" : "text-slate-900")}>
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Form filter pencarian di atas tabel, berupa kartu yang dapat di-minimize (bawaan: minimize; klik judul kartu untuk
 *  membuka/menutup). Isian baru berlaku setelah klik "Terapkan" (Enter tidak menerapkan); "Reset" mengosongkan semua isian
 *  dan langsung menampilkan semua data.
 *  `kolomPerBaris` (bawaan: semua isian satu baris): untuk isian banyak yang tidak muat satu baris (mis. Master RO = 6).
 *  Lebar kolom grid mengikuti isian baris pertama, jadi halaman pemakai menyusun isian agar pola kecil/lebar tiap baris sama. */
export function FormFilter({ judul, bidang, nilai, terapkan, kolomPerBaris = bidang.length }: {
  judul: string; bidang: Bidang[]; nilai: NilaiFilter; terapkan: (n: NilaiFilter) => void; kolomPerBaris?: number;
}) {
  const [draf, setDraf] = useState<NilaiFilter>(nilai);
  const ubah = (k: string, v: string) => setDraf((d) => ({ ...d, [k]: v }));
  const adaKecil = bidang.some((b) => b.kecil);
  // Kartu filter minimize secara bawaan (hanya judul yang tampil); isian & filter yang berlaku tetap saat di-minimize.
  const [buka, setBuka] = useState(false);
  const idForm = useId();
  // Sudut putar ikon Reset: tiap klik berputar satu putaran berlawanan jarum jam (arah panah ikon).
  const [putar, setPutar] = useState(0);
  const label = (i: number, b: Bidang) => (
    <span className="block text-xs font-semibold uppercase tracking-wide text-slate-700">{i + 1}. {b.label}</span>
  );

  return (
    <Kartu className="mb-4 overflow-hidden">
      {/* Seluruh baris judul = tombol minimize/buka: judul di kiri, panah di kanan. */}
      <button type="button" aria-expanded={buka} aria-controls={idForm} onClick={() => setBuka(!buka)}
        title={buka ? "Minimize filter" : "Buka filter"}
        className="flex w-full flex-wrap items-center justify-between gap-x-4 gap-y-1 px-5 py-4 text-left hover:bg-slate-50/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-utama-100">
        <span className="flex items-center gap-2.5 text-sm font-bold uppercase tracking-wide text-slate-900">
          <Filter className="size-4 text-utama-600" aria-hidden />Form Filter Pencarian {judul}
        </span>
        <ChevronDown className={cx("ml-auto size-4 text-slate-500 transition-transform motion-reduce:transition-none", buka && "rotate-180")} aria-hidden />
      </button>
      {/* Enter di isian tidak menerapkan filter: filter hanya berlaku lewat tombol "Terapkan" (permintaan pemilik produk). */}
      <form id={idForm} hidden={!buka} role="search" aria-label={`Filter ${judul}`} onSubmit={(e) => e.preventDefault()}
        className="border-t border-slate-100 p-5">
        {/* Jumlah kolom di layar lebar = jumlah isian, agar kolom selalu memenuhi lebar form (tidak ada sisa kosong di kanan). */}
        {/* Bila ada kolom `kecil`, semua isian dibuat satu baris dengan lebar proporsional (kolom kecil 0,7 bagian). */}
        <div className={cx("grid gap-4 sm:grid-cols-2", adaKecil ? "xl:grid-cols-(--kolom-filter)" : KOLOM_XL[Math.min(bidang.length, 5)])}
          /* Dropdown sempit (`pilih` + `kecil`, mis. Status) minimal selebar pilihan terpanjangnya (max-content) agar teks
             seperti "Semua Dokumen" tidak terpotong; kolom lain boleh menyempit (minimal 0). Dropdown lebar (mis. Unit
             Kerja) tidak, karena pilihannya sangat panjang dan akan mendesak kolom lain. */
          style={adaKecil ? { "--kolom-filter": bidang.slice(0, kolomPerBaris)
            .map((b) => `minmax(${b.jenis === "pilih" && b.kecil ? "max-content" : "0"},${b.kecil ? 0.7 : 1}fr)`).join(" ") } as CSSProperties : undefined}>
          {bidang.map((b, i) => (
            <Fragment key={i}>
              {b.jenis === "teks" && (
                <label className="block space-y-1.5">
                  {label(i, b)}
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
                    <Input value={draf[b.kunci] ?? ""} onChange={(e) => ubah(b.kunci, e.target.value)} placeholder={b.placeholder} className="pl-9" />
                  </div>
                </label>
              )}
              {b.jenis === "pilih" && (
                <label className="block space-y-1.5">
                  {label(i, b)}
                  {/* Isi daftar pilihan digeser ke kanan (jarak kiri) agar tidak menempel di tepi. */}
                  <Pilih value={draf[b.kunci] ?? ""} onChange={(e) => ubah(b.kunci, e.target.value)} className="[&_option]:pl-6">
                    <option value="">{b.semua}</option>
                    {b.opsi.map((o) => <option key={o.nilai} value={o.nilai}>{o.label}</option>)}
                  </Pilih>
                </label>
              )}
              {b.jenis === "tanggal" && (
                <label className="block space-y-1.5">
                  {label(i, b)}
                  <Input type="date" value={draf[b.kunci] ?? ""} onChange={(e) => ubah(b.kunci, e.target.value)} />
                </label>
              )}
            </Fragment>
          ))}
        </div>
        <div className="mt-5 flex justify-end">
          {/* Dua tombol satu baris di kanan. Di layar HP (< sm) tombol diperkecil (tinggi, teks, ikon, jarak); di layar ≥ sm
              ukuran normal. */}
          <div className="flex gap-1.5 sm:gap-2 [&>button]:max-sm:h-8 [&>button]:max-sm:gap-1 [&>button]:max-sm:px-2 [&>button]:max-sm:text-xs [&_svg]:max-sm:size-3.5">
            <Tombol type="button" varian="sekunder" onClick={() => {
              // Hanya berputar bila memang ada isian/filter yang dikosongkan (draf di form atau filter yang sedang berlaku).
              if ([...Object.values(draf), ...Object.values(nilai)].some((v) => v)) setPutar((d) => d - 360);
              setDraf({}); terapkan({});
            }}>
              <RotateCcw className="size-4 transition-transform duration-500 ease-out motion-reduce:transition-none" style={{ transform: `rotate(${putar}deg)` }} aria-hidden />Reset
            </Tombol>
            <Tombol type="button" onClick={() => terapkan(draf)}><Filter className="size-4" />Terapkan</Tombol>
          </div>
        </div>
      </form>
    </Kartu>
  );
}

/** Pilihan jumlah baris per halaman untuk <Paginasi>. */
export const OPSI_BARIS = [10, 20, 50, 100];

/** Paginasi di browser atas baris yang sudah difilter & diurutkan. `reset` = nilai yang bila berubah (mis. filter,
 *  urutan) mengembalikan ke halaman 1. Halaman dibatasi ke halaman terakhir, mis. setelah baris terakhir dihapus. */
export function usePaginasi<T>(baris: T[], reset: unknown[], bawaan = 20) {
  const [halaman, setHalaman] = useState(1);
  const [per, setPer] = useState(bawaan);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setHalaman(1), reset);
  const maks = Math.max(1, Math.ceil(baris.length / per));
  const hlm = Math.min(halaman, maks);
  const awal = (hlm - 1) * per;
  return {
    tampil: baris.slice(awal, awal + per), awal, halaman: hlm, maks, per,
    ubahHalaman: setHalaman, ubahPer: (n: number) => { setPer(n); setHalaman(1); },
  };
}

/** Nomor halaman yang ditampilkan: selalu halaman pertama & terakhir, plus 1 halaman di kiri-kanan halaman aktif;
 *  sisanya diganti "…". */
const nomorHalaman = (h: number, maks: number): (number | "…")[] => {
  const hasil: (number | "…")[] = [];
  for (let i = 1; i <= maks; i++) {
    if (i === 1 || i === maks || Math.abs(i - h) <= 1) hasil.push(i);
    else if (hasil[hasil.length - 1] !== "…") hasil.push("…");
  }
  return hasil;
};

/** Navigasi halaman di bawah tabel: kiri = ‹ nomor halaman ›, kanan = "Tampilkan baris" + pilihan jumlah baris. */
export function Paginasi({ halaman, maks, per, ubahHalaman, ubahPer }: {
  halaman: number; maks: number; per: number; ubahHalaman: (h: number) => void; ubahPer: (n: number) => void;
}) {
  const tombol = "flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-utama-100";
  const idLabel = useId();
  return (
    <nav aria-label="Paginasi" className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-700">
      <div className="flex items-center gap-1">
        <button type="button" className={cx(tombol, "text-slate-500 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent")}
          disabled={halaman <= 1} onClick={() => ubahHalaman(halaman - 1)} aria-label="Halaman sebelumnya"><ChevronLeft className="size-4" /></button>
        {nomorHalaman(halaman, maks).map((n, i) => n === "…"
          ? <span key={`l${i}`} className="px-1 text-slate-400">…</span>
          : <button key={n} type="button" onClick={() => ubahHalaman(n)} aria-current={n === halaman ? "page" : undefined}
              className={cx(tombol, n === halaman ? "bg-utama-600 font-semibold text-white" : "hover:bg-slate-100")}>{n}</button>)}
        <button type="button" className={cx(tombol, "text-slate-500 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent")}
          disabled={halaman >= maks} onClick={() => ubahHalaman(halaman + 1)} aria-label="Halaman berikutnya"><ChevronRight className="size-4" /></button>
      </div>
      <div className="flex items-center gap-2">
        <span id={idLabel}>Tampilkan baris</span>
        {/* Dropdown sama dengan dropdown filter (PilihDaftar), terbuka ke atas karena letaknya di bawah tabel. */}
        <PilihDaftar labelId={idLabel} nilai={String(per)} ubah={(v) => ubahPer(Number(v))} kecil keAtas
          opsi={OPSI_BARIS.map((n) => ({ nilai: String(n), label: String(n) }))} />
      </div>
    </nav>
  );
}
