/** Kelola pengguna (multi-role, Satker, aktif, reset password) dan daftar Satker. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { api } from "../../api";
import { waktu } from "../../format";
import type { Role, Satker } from "../../types";
import { Dialog, Input, Judul, Kartu, Kolom, Lencana, Memuat, Peringatan, Pilih, Tab, Tombol } from "../../ui";

type P = { id: string; username: string; nama: string; roles: Role[]; aktif: boolean; satker: Satker | null; last_login_at: string | null };
const ROLE: Role[] = ["PENGUSUL", "REVIEWER", "ADMIN"];

export default function KelolaPengguna() {
  const [tab, setTab] = useState<"pengguna" | "satker">("pengguna");
  return (
    <div>
      <Judul judul="Pengguna & Satker" sub="Satker tempat Reviewer bernaung mengusulkan dengan akun Pengusul tersendiri." />
      <Tab aktif={tab} ubah={setTab} pilihan={[{ nilai: "pengguna", label: "Pengguna" }, { nilai: "satker", label: "Satker" }]} />
      <div className="mt-4">{tab === "pengguna" ? <DaftarPengguna /> : <DaftarSatker />}</div>
    </div>
  );
}

function DaftarPengguna() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["pengguna"], queryFn: () => api.get<P[]>("/api/pengguna") });
  const satker = useQuery({ queryKey: ["satker"], queryFn: () => api.get<Satker[]>("/api/satker") });
  const [form, setForm] = useState<{ id?: string; username: string; nama: string; roles: Role[]; satker_id: string; aktif: boolean; password: string } | null>(null);
  const simpan = useMutation({
    mutationFn: () => { const b = { ...form!, satker_id: form!.satker_id || null, password: form!.password || null };
      return form!.id ? api.put(`/api/pengguna/${form!.id}`, b) : api.post("/api/pengguna", b); },
    onSuccess: () => { setForm(null); qc.invalidateQueries({ queryKey: ["pengguna"] }); },
  });
  if (q.isLoading) return <Memuat />;
  return (
    <>
      <Tombol className="mb-3" onClick={() => { simpan.reset(); setForm({ username: "", nama: "", roles: ["PENGUSUL"], satker_id: "", aktif: true, password: "" }); }}><Plus className="size-4" />Tambah pengguna</Tombol>
      <Kartu className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500"><tr>{["Username", "Nama", "Role", "Satker", "Status", "Login terakhir", ""].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">{q.data?.map((p) => (
            <tr key={p.id}>
              <td className="px-3 py-2 font-medium">{p.username}</td><td className="px-3 py-2">{p.nama}</td>
              <td className="px-3 py-2"><div className="flex flex-wrap gap-1">{p.roles.map((r) => <Lencana key={r} className="bg-utama-50 text-utama-700 ring-utama-100">{r}</Lencana>)}</div></td>
              <td className="px-3 py-2">{p.satker?.nama ?? "—"}</td>
              <td className="px-3 py-2">{p.aktif ? "Aktif" : <span className="text-red-600">Nonaktif</span>}</td>
              <td className="whitespace-nowrap px-3 py-2 text-slate-500">{waktu(p.last_login_at)}</td>
              <td className="px-3 py-2"><Tombol varian="hantu" kecil onClick={() => { simpan.reset(); setForm({ id: p.id, username: p.username, nama: p.nama, roles: p.roles, satker_id: p.satker?.id ?? "", aktif: p.aktif, password: "" }); }}><Pencil className="size-4" />Ubah</Tombol></td>
            </tr>))}</tbody>
        </table>
      </Kartu>
      {form && (
        <Dialog buka ubahBuka={(b) => !b && setForm(null)} judul={form.id ? `Ubah ${form.username}` : "Tambah pengguna"}>
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); simpan.mutate(); }}>
            {simpan.error && <Peringatan>{(simpan.error as Error).message}</Peringatan>}
            <Kolom label="Username" wajib><Input required disabled={!!form.id} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Kolom>
            <Kolom label="Nama" wajib><Input required value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} /></Kolom>
            <fieldset className="space-y-1"><legend className="text-sm font-medium text-slate-700">Role *</legend>
              <div className="flex flex-wrap gap-4">{ROLE.map((r) => (
                <label key={r} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.roles.includes(r)}
                  onChange={(e) => setForm({ ...form, roles: e.target.checked ? [...form.roles, r] : form.roles.filter((x) => x !== r) })} />{r}</label>))}</div>
            </fieldset>
            <Kolom label="Satker" petunjuk="Wajib untuk Pengusul (membatasi data yang dapat dilihat).">
              <Pilih value={form.satker_id} onChange={(e) => setForm({ ...form, satker_id: e.target.value })}>
                <option value="">— tidak ada —</option>{satker.data?.map((s) => <option key={s.id} value={s.id}>{s.nama}</option>)}
              </Pilih>
            </Kolom>
            <Kolom label={form.id ? "Reset password (kosongkan bila tidak diubah)" : "Password awal"} wajib={!form.id} petunjuk="Minimal 8 karakter, kombinasi huruf dan angka/simbol.">
              <Input type="password" autoComplete="new-password" required={!form.id} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Kolom>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.aktif} onChange={(e) => setForm({ ...form, aktif: e.target.checked })} />Akun aktif</label>
            <div className="flex justify-end gap-2"><Tombol type="button" varian="hantu" onClick={() => setForm(null)}>Batal</Tombol><Tombol type="submit" memuat={simpan.isPending}>Simpan</Tombol></div>
          </form>
        </Dialog>
      )}
    </>
  );
}

function DaftarSatker() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["satker"], queryFn: () => api.get<Satker[]>("/api/satker") });
  const [form, setForm] = useState<{ id?: string; kode: string; nama: string; aktif: boolean } | null>(null);
  const simpan = useMutation({
    mutationFn: () => (form!.id ? api.put(`/api/satker/${form!.id}`, form) : api.post("/api/satker", form)),
    onSuccess: () => { setForm(null); qc.invalidateQueries({ queryKey: ["satker"] }); },
  });
  if (q.isLoading) return <Memuat />;
  return (
    <>
      <Tombol className="mb-3" onClick={() => { simpan.reset(); setForm({ kode: "", nama: "", aktif: true }); }}><Plus className="size-4" />Tambah Satker</Tombol>
      <Kartu className="divide-y divide-slate-100">{q.data?.map((s) => (
        <div key={s.id} className="flex items-center gap-3 px-4 py-3 text-sm">
          <span className="w-32 font-medium">{s.kode}</span><span className="flex-1">{s.nama}</span>{!s.aktif && <span className="text-red-600">Nonaktif</span>}
          <Tombol varian="hantu" kecil onClick={() => { simpan.reset(); setForm({ id: s.id, kode: s.kode, nama: s.nama, aktif: s.aktif ?? true }); }}><Pencil className="size-4" />Ubah</Tombol>
        </div>))}</Kartu>
      {form && (
        <Dialog buka ubahBuka={(b) => !b && setForm(null)} judul={form.id ? "Ubah Satker" : "Tambah Satker"}>
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); simpan.mutate(); }}>
            {simpan.error && <Peringatan>{(simpan.error as Error).message}</Peringatan>}
            <Kolom label="Kode" wajib><Input required value={form.kode} onChange={(e) => setForm({ ...form, kode: e.target.value })} /></Kolom>
            <Kolom label="Nama" wajib><Input required value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} /></Kolom>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.aktif} onChange={(e) => setForm({ ...form, aktif: e.target.checked })} />Aktif</label>
            <div className="flex justify-end gap-2"><Tombol type="button" varian="hantu" onClick={() => setForm(null)}>Batal</Tombol><Tombol type="submit" memuat={simpan.isPending}>Simpan</Tombol></div>
          </form>
        </Dialog>
      )}
    </>
  );
}
