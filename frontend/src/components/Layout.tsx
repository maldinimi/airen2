import { BookOpen, FileText, History, KeyRound, LayoutDashboard, ListChecks, LogOut, Menu, Server, Tags, Users, X } from "lucide-react";
import { type ReactNode, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import type { Role } from "../types";
import { cx } from "../ui";

type Menu = { ke: string; label: string; ikon: ReactNode; role?: Role[] };
const MENU: { grup?: string; item: Menu[] }[] = [
  { item: [
    { ke: "/", label: "Dashboard", ikon: <LayoutDashboard className="size-4" /> },
    { ke: "/usulan", label: "Usulan", ikon: <FileText className="size-4" /> },
    { ke: "/panduan", label: "Panduan", ikon: <BookOpen className="size-4" /> },
  ] },
  { grup: "Kelola", item: [
    { ke: "/kelola/checklist", label: "Checklist", ikon: <ListChecks className="size-4" />, role: ["ADMIN"] },
    { ke: "/kelola/kategori", label: "Kategori", ikon: <Tags className="size-4" />, role: ["ADMIN"] },
    { ke: "/kelola/pengguna", label: "Pengguna & Satker", ikon: <Users className="size-4" />, role: ["ADMIN"] },
    { ke: "/kelola/node-ai", label: "Node AI", ikon: <Server className="size-4" />, role: ["ADMIN"] },
    { ke: "/audit", label: "Audit Log", ikon: <History className="size-4" />, role: ["ADMIN"] },
  ] },
];
const NAMA_ROLE: Record<Role, string> = { PENGUSUL: "Pengusul", REVIEWER: "Reviewer", ADMIN: "Admin" };

export default function Layout() {
  const { pengguna, keluar, punya } = useAuth();
  const [laci, setLaci] = useState(false);
  const lokasi = useLocation();

  const nav = (
    <nav className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 py-4" aria-label="Menu utama">
      {MENU.map((g, i) => {
        const item = g.item.filter((m) => !m.role || punya(...m.role));
        if (!item.length) return null;
        return (
          <div key={i} className="space-y-1">
            {g.grup && <div className="px-3 text-xs font-semibold uppercase tracking-wide text-utama-100/70">{g.grup}</div>}
            {item.map((m) => (
              <NavLink key={m.ke} to={m.ke} end={m.ke === "/"} onClick={() => setLaci(false)}
                className={({ isActive }) => cx("flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium",
                  isActive ? "bg-white/15 text-white" : "text-utama-100 hover:bg-white/10 hover:text-white")}>
                {m.ikon}{m.label}
              </NavLink>
            ))}
          </div>
        );
      })}
    </nav>
  );

  const sisi = (
    <div className="flex h-full w-64 flex-col bg-utama-900 text-white">
      <div className="flex h-16 items-center gap-2.5 border-b border-white/10 px-5">
        <img src="/favicon.svg" alt="" className="size-8" />
        <div><div className="font-semibold leading-tight">AIREN</div><div className="text-xs text-utama-100/80">Review TOR & RAB</div></div>
      </div>
      {nav}
      <div className="space-y-1 border-t border-white/10 p-3">
        <NavLink to="/akun" onClick={() => setLaci(false)} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-utama-100 hover:bg-white/10"><KeyRound className="size-4" />Ganti password</NavLink>
        <button onClick={keluar} className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-utama-100 hover:bg-white/10"><LogOut className="size-4" />Keluar</button>
      </div>
    </div>
  );

  return (
    <div className="flex h-full">
      <aside className="hidden lg:block">{sisi}</aside>
      {laci && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setLaci(false)} />
          <div className="relative h-full w-64">{sisi}
            <button className="absolute right-2 top-4 text-white" onClick={() => setLaci(false)} aria-label="Tutup menu"><X className="size-5" /></button>
          </div>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
          <button className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setLaci(true)} aria-label="Buka menu"><Menu className="size-5" /></button>
          <div className="ml-auto text-right">
            <div className="text-sm font-medium text-slate-900">{pengguna?.nama}</div>
            <div className="text-xs text-slate-500">
              {pengguna?.roles.map((r) => NAMA_ROLE[r]).join(" · ")}{pengguna?.satker && ` · ${pengguna.satker.nama}`}
            </div>
          </div>
        </header>
        <main key={lokasi.pathname} className="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6"><Outlet /></main>
      </div>
    </div>
  );
}
