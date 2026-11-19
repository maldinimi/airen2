import { BookOpen, Building2, FileText, History, KeyRound, Landmark, LayoutDashboard, ListChecks, LogOut, Menu, PanelLeftClose, PanelLeftOpen, Server,
  Tags, Users, X } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import type { Role } from "../types";
import { Pilih, cx } from "../ui";

type Menu = { ke: string; label: string; ikon: ReactNode; role: Role[] };
const KERJA: Role[] = ["PENGUSUL", "REVIEWER"];
/** Satu daftar tanpa judul grup (permintaan pemilik produk). Hak akses (juga dicek backend):
 *  - Pengusul : Dashboard, Pengajuan (route /usulan), dan Acuan (route /panduan)/Checklist/Kategori untuk dilihat saja.
 *  - Reviewer : Dashboard, Pengajuan, serta mengelola Acuan, Checklist, Kategori, Master RO, Satuan Kerja.
 *  - Admin    : Pengguna (CRUD & reset password), Node AI, Audit Log. */
const MENU: Menu[] = [
  { ke: "/", label: "Dashboard", ikon: <LayoutDashboard className="size-4" />, role: KERJA },
  { ke: "/usulan", label: "Pengajuan", ikon: <FileText className="size-4" />, role: KERJA },
  { ke: "/panduan", label: "Acuan", ikon: <BookOpen className="size-4" />, role: KERJA },
  { ke: "/kelola/checklist", label: "Checklist", ikon: <ListChecks className="size-4" />, role: KERJA },
  { ke: "/kelola/kategori", label: "Kategori", ikon: <Tags className="size-4" />, role: KERJA },
  { ke: "/kelola/master-ro", label: "Master RO", ikon: <Landmark className="size-4" />, role: ["REVIEWER"] },
  { ke: "/kelola/satker", label: "Satuan Kerja", ikon: <Building2 className="size-4" />, role: ["REVIEWER"] },
  { ke: "/kelola/pengguna", label: "Pengguna", ikon: <Users className="size-4" />, role: ["ADMIN"] },
  { ke: "/kelola/node-ai", label: "Node AI", ikon: <Server className="size-4" />, role: ["ADMIN"] },
  { ke: "/audit", label: "Audit Log", ikon: <History className="size-4" />, role: ["ADMIN"] },
];
const NAMA_ROLE: Record<Role, string> = { PENGUSUL: "Pengusul", REVIEWER: "Reviewer", ADMIN: "Admin" };

/** Tahun anggaran pilihan di header: tampil di semua menu, tetapi hanya menyaring Dashboard & menu Usulan (lewat Outlet context).
 *  Disimpan di browser agar tetap terpilih saat berpindah menu/memuat ulang; storage bisa tidak tersedia → abaikan. */
export type KonteksLayout = { tahun: string };
const KUNCI_TAHUN = "airen.tahun";
const KUNCI_CIUT = "airen.sidebar-kecil";
// Pilihan dibatasi 5 tahun: 2 tahun ke belakang hingga 2 tahun ke depan; bawaan = tahun berjalan menurut WIB, sama dengan
// batas di backend (api/usulan.py `tahun_berjalan`), agar pengguna WITA/WIT tidak ditolak saat pergantian tahun.
const SEKARANG = Number(new Intl.DateTimeFormat("en", { year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date()));
const DAFTAR_TAHUN = [-2, -1, 0, 1, 2].map((d) => String(SEKARANG + d));
const bacaTahun = () => {
  let t: string | null = null;
  try { t = localStorage.getItem(KUNCI_TAHUN); } catch { /* storage tidak tersedia */ }
  return t && DAFTAR_TAHUN.includes(t) ? t : String(SEKARANG);
};

export default function Layout() {
  const { pengguna, keluar, punya } = useAuth();
  const [laci, setLaci] = useState(false);
  const lokasi = useLocation();
  const nav = useNavigate();
  const [tahun, setTahun] = useState(bacaTahun);
  // Di halaman turunan menu Usulan (detail, pemeriksaan, form, dan PDF yang dibuka dari sana: `?dari=pengajuan`) → kembali ke
  // daftar Usulan tahun itu. Di menu lain (termasuk PDF dari menu Acuan) halaman tetap (desain.md §7 no. 51 & 72).
  const pilihTahun = (t: string) => {
    setTahun(t);
    try { localStorage.setItem(KUNCI_TAHUN, t); } catch { /* abaikan */ }
    if (/^\/(usulan|review)\//.test(lokasi.pathname) || new URLSearchParams(lokasi.search).get("dari") === "pengajuan") nav("/usulan");
  };
  // Sidebar diperkecil (layar lebar saja), diingat di browser seperti tahun.
  const [ciut, setCiut] = useState(() => { try { return localStorage.getItem(KUNCI_CIUT) === "1"; } catch { return false; } });
  const ubahCiut = (c: boolean) => { setCiut(c); try { localStorage.setItem(KUNCI_CIUT, c ? "1" : "0"); } catch { /* abaikan */ } };
  // Halaman digulir oleh browser (tanpa gulir di dalam <main>), jadi pindah menu/halaman dimulai dari atas.
  useEffect(() => { window.scrollTo(0, 0); }, [lokasi.pathname]);

  // `kecil` = sidebar diperkecil (hanya ikon; nama menu jadi tooltip & teks pembaca layar). Laci di layar kecil selalu lebar.
  // `tombol` = tampilkan tombol perkecil/perbesar (sidebar layar lebar; laci layar kecil punya tombol tutup sendiri).
  const sisi = (kecil: boolean, tombol: boolean) => {
    const label = (t: string) => <span className={cx(kecil && "sr-only")}>{t}</span>;
    const kelas = (aktif = false) => cx("flex items-center gap-2.5 rounded-lg py-2 text-sm", kecil ? "justify-center px-0" : "px-3",
      aktif ? "bg-white/15 text-white" : "text-utama-100 hover:bg-white/10 hover:text-white");
    return (
      <div className={cx("flex h-full flex-col bg-utama-900 text-white transition-[width] duration-200", kecil ? "w-16" : "w-64")}>
        <div className={cx("flex h-16 shrink-0 items-center gap-2.5 border-b border-white/10", kecil ? "justify-center" : "pl-5 pr-3")}>
          {/* Saat diperkecil, tombol perbesar menggantikan logo karena lebar sidebar hanya muat satu ikon. */}
          {!kecil && <img src="/favicon.svg" alt="" className="size-8" />}
          {!kecil && <div className="min-w-0 flex-1"><div className="font-semibold leading-tight">AIREN</div><div className="truncate text-xs text-utama-100/80">Review TOR & RAB</div></div>}
          {tombol && (
            <button type="button" onClick={() => ubahCiut(!kecil)} aria-expanded={!kecil}
              aria-label={kecil ? "Perbesar menu samping" : "Perkecil menu samping"} title={kecil ? "Perbesar menu samping" : "Perkecil menu samping"}
              className="shrink-0 rounded-lg p-2 text-utama-100 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40">
              {kecil ? <PanelLeftOpen className="size-5" /> : <PanelLeftClose className="size-5" />}
            </button>
          )}
        </div>
        <nav className={cx("flex flex-1 flex-col gap-1 overflow-y-auto overflow-x-hidden py-4", kecil ? "px-2" : "px-3")} aria-label="Menu utama">
          {MENU.filter((m) => punya(...m.role)).map((m) => (
            <NavLink key={m.ke} to={m.ke} end={m.ke === "/"} onClick={() => setLaci(false)} title={kecil ? m.label : undefined}
              className={({ isActive }) => cx(kelas(isActive), "font-medium")}>
              {m.ikon}{label(m.label)}
            </NavLink>
          ))}
        </nav>
        <div className={cx("space-y-1 border-t border-white/10", kecil ? "p-2" : "p-3")}>
          <NavLink to="/akun" onClick={() => setLaci(false)} title={kecil ? "Ganti password" : undefined} className={kelas()}><KeyRound className="size-4" />{label("Ganti password")}</NavLink>
          <button onClick={keluar} title={kecil ? "Keluar" : undefined} className={cx(kelas(), "w-full")}><LogOut className="size-4" />{label("Keluar")}</button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-dvh shrink-0 lg:block">{sisi(ciut, true)}</aside>
      {laci && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setLaci(false)} />
          <div className="relative h-full w-64">{sisi(false, false)}
            <button className="absolute right-2 top-4 text-white" onClick={() => setLaci(false)} aria-label="Tutup menu"><X className="size-5" /></button>
          </div>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-35 flex h-16 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
          <button className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setLaci(true)} aria-label="Buka menu"><Menu className="size-5" /></button>
          {/* Tahun hanya menyaring Dashboard & menu Usulan, jadi tidak ditampilkan bagi Admin (tidak punya keduanya). */}
          {punya(...KERJA) && (
            <label className="flex shrink-0 items-center gap-2">
              <span className="whitespace-nowrap text-base font-bold uppercase text-slate-800">Tahun Anggaran</span>
              <Pilih className="w-24" title="Tahun anggaran — menyaring Dashboard & menu Pengajuan" value={tahun} onChange={(e) => pilihTahun(e.target.value)}>
                {DAFTAR_TAHUN.map((t) => <option key={t} value={t}>{t}</option>)}
              </Pilih>
            </label>
          )}
          <div className="ml-auto min-w-0 text-right">
            <div className="truncate text-sm font-medium text-slate-900">{pengguna?.nama}</div>
            <div className="hidden truncate text-xs text-slate-500 sm:block">
              {pengguna?.roles.map((r) => NAMA_ROLE[r]).join(" · ")}{pengguna?.satker && ` · ${pengguna.satker.nama}`}
            </div>
          </div>
        </header>
        <main key={lokasi.pathname} className="min-w-0 flex-1 p-(--tepi)"><Outlet context={{ tahun } satisfies KonteksLayout} /></main>
      </div>
    </div>
  );
}
