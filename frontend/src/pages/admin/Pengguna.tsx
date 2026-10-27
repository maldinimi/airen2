/** Kelola pengguna (multi-role, Satker, aktif, reset password). Satker dipilih dari menu Satker. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { api } from "../../api";
import { Aksi, HalamanDetail, HalamanForm, type Jejak, LencanaAktif, PilihBawah, type Satker, TD, barisJejak, th, usePesanSukses } from "../../components/Kelola";
import { waktuAngka } from "../../format";
import type { Role } from "../../types";
import { Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Lencana, Memuat, Peringatan, Tombol, cx } from "../../ui";

type P = { id: string; username: string; roles: Role[]; aktif: boolean; satker: Satker | null; last_login_at: string | null } & Jejak;
const ROLE: Role[] = ["PENGUSUL", "REVIEWER", "ADMIN"];
const NAMA_ROLE: Record<Role, string> = { PENGUSUL: "Pengusul", REVIEWER: "Reviewer", ADMIN: "Admin" };

const LencanaRole = ({ roles }: { roles: Role[] }) =>
  <div className="flex flex-wrap justify-center gap-1">{roles.map((r) => <Lencana key={r} className="bg-utama-50 text-utama-700 ring-utama-100">{NAMA_ROLE[r]}</Lencana>)}</div>;

const TANPA_UK = "__tanpa";  // nilai pilihan untuk Satker yang Unit Kerja-nya kosong

/** Dua langkah seperti dokumen sumber: pilih Unit Kerja (UKE I), lalu Satker (UKE II) di bawahnya.
 *  Satker Nonaktif disembunyikan kecuali yang sedang dipakai. */
function PilihSatker({ daftar, unitKerja, nilai, ubah }: {
  daftar: Satker[]; unitKerja: string; nilai: string; ubah: (unitKerja: string, satkerId: string) => void;
}) {
  const tampil = daftar.filter((s) => s.aktif !== false || s.id === nilai);
  // Unit Kerja unik (urut kemunculan) beserta Kode UKE I-nya untuk label "01 — SEKRETARIAT JENDERAL".
  const unit = [...new Map(tampil.map((s) => [s.unit_kerja ?? "", s.kode_uke1 ?? ""]))];
  const label = (s: Satker) => `${[s.kode_uke2, s.nama || "(tanpa nama)"].filter(Boolean).join(" — ")}${s.aktif === false ? " (Nonaktif)" : ""}`;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Kolom label="Unit Kerja (Eselon I)">
        <PilihBawah nilai={unitKerja} ubah={(uk) => ubah(uk, "")} kosong="— pilih Unit Kerja —"
          opsi={unit.map(([uk, kode]) => ({ nilai: uk || TANPA_UK, label: uk ? [kode, uk].filter(Boolean).join(" — ") : "Tanpa Unit Kerja" }))} />
      </Kolom>
      <Kolom label="Satuan Kerja (Eselon II)" petunjuk="Wajib untuk Pengusul (membatasi data yang dapat dilihat).">
        <PilihBawah nilai={nilai} ubah={(id) => ubah(unitKerja, id)} disabled={!unitKerja}
          opsi={tampil.filter((s) => s.nama && (s.unit_kerja || TANPA_UK) === unitKerja).map((s) => ({ nilai: s.id, label: label(s) }))} />
      </Kolom>
    </div>
  );
}

export default function KelolaPengguna() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["pengguna"], queryFn: () => api.get<P[]>("/api/pengguna") });
  const satker = useQuery({ queryKey: ["satker"], queryFn: () => api.get<Satker[]>("/api/satker") });
  const [sukses, setSukses] = usePesanSukses();
  const [form, setForm] = useState<{ id?: string; username: string; roles: Role[]; unit_kerja: string; satker_id: string; aktif: boolean; password: string } | null>(null);
  const simpan = useMutation({
    mutationFn: () => { const { unit_kerja: _, ...isi } = form!; const b = { ...isi, satker_id: form!.satker_id || null, password: form!.password || null };
      return form!.id ? api.put(`/api/pengguna/${form!.id}`, b) : api.post("/api/pengguna", b); },
    onSuccess: () => { setSukses(`Pengguna ${form!.username} berhasil disimpan.`); setForm(null); qc.invalidateQueries({ queryKey: ["pengguna"] }); },
  });
  const buka = (p?: P) => { simpan.reset(); setForm(p
    ? { id: p.id, username: p.username, roles: p.roles, unit_kerja: p.satker ? p.satker.unit_kerja || TANPA_UK : "", satker_id: p.satker?.id ?? "", aktif: p.aktif, password: "" }
    : { username: "", roles: ["PENGUSUL"], unit_kerja: "", satker_id: "", aktif: true, password: "" }); };
  const [lihat, setLihat] = useState<P | null>(null);
  const [dihapus, setDihapus] = useState<P | null>(null);
  const hapus = useMutation({
    mutationFn: (p: P) => api.del(`/api/pengguna/${p.id}`),
    onSuccess: (_, p) => { setSukses(`Pengguna ${p.username} berhasil dihapus.`); setDihapus(null); qc.invalidateQueries({ queryKey: ["pengguna"] }); },
  });

  if (lihat) return (
    <HalamanDetail kembali="Pengguna" judul={`Detail Pengguna ${lihat.username}`} sub={lihat.username} tutup={() => setLihat(null)} info={[
      ["Username", lihat.username],
      ["Role", <div className="[&>div]:justify-start"><LencanaRole roles={lihat.roles} /></div>],
      ["Satuan Kerja (Eselon II)", lihat.satker?.nama || "—"], ["Unit Kerja (Eselon I)", lihat.satker?.unit_kerja || "—"],
      ["Status", <LencanaAktif aktif={lihat.aktif} />], ["Login Terakhir", waktuAngka(lihat.last_login_at)], ...barisJejak(lihat),
    ]} />
  );

  if (form) return (
    <HalamanForm judul={form.id ? `Ubah Pengguna ${form.username}` : "Tambah Pengguna"} sub={form.id ? "Perbarui data akun. Kosongkan password bila tidak ingin mereset." : "Lengkapi data akun baru. Akun Pengusul wajib dihubungkan ke Satuan Kerja."}
      tutup={() => setForm(null)} kirim={() => simpan.mutate()} reset={form.id ? undefined : () => buka()} galat={simpan.error} sibuk={simpan.isPending}>
      <Kolom label="Username" wajib><Input required maxLength={100} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Kolom>
      <fieldset className="space-y-1.5"><legend className="text-sm font-medium text-slate-700">Role<span className="text-red-600"> *</span></legend>
        <div className="flex flex-wrap gap-4">{ROLE.map((r) => (
          <label key={r} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.roles.includes(r)}
            onChange={(e) => setForm({ ...form, roles: e.target.checked ? [...form.roles, r] : form.roles.filter((x) => x !== r) })} />{NAMA_ROLE[r]}</label>))}</div>
      </fieldset>
      <PilihSatker daftar={satker.data ?? []} unitKerja={form.unit_kerja} nilai={form.satker_id}
        ubah={(unit_kerja, satker_id) => setForm({ ...form, unit_kerja, satker_id })} />
      <Kolom label={form.id ? "Reset password (kosongkan bila tidak diubah)" : "Password"} wajib={!form.id} petunjuk="Minimal 8 karakter, kombinasi huruf dan angka/simbol.">
        <Input type="password" autoComplete="new-password" required={!form.id} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Kolom>
    </HalamanForm>
  );

  return (
    <div className="w-full">
      <Judul judul="Pengguna" sub="Kelola akun pengguna beserta role dan Satuan Kerja-nya."
        aksi={<Tombol onClick={() => buka()}><Plus className="size-4" />Tambah Pengguna</Tombol>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {q.isLoading ? <Memuat /> : q.error ? <Peringatan>{(q.error as Error).message}</Peringatan> : !q.data?.length ? <Kosong>Belum ada pengguna.</Kosong> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full min-w-[48rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
              <tr>{["No", "Username", "Role", "Status", "Login Terakhir", "Aksi"].map(th)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">{q.data.map((p, i) => (
              <tr key={p.id} className="align-middle transition-colors hover:bg-slate-50">
                <td className={cx(TD, "text-slate-500")}>{i + 1}</td>
                <td className={cx(TD, "whitespace-nowrap font-medium text-slate-900")}>{p.username}</td>
                <td className={TD}><LencanaRole roles={p.roles} /></td>
                <td className={TD}><LencanaAktif aktif={p.aktif} /></td>
                <td className={cx(TD, "whitespace-nowrap text-slate-600")}>{waktuAngka(p.last_login_at)}</td>
                <Aksi nama={p.username} lihat={() => setLihat(p)} ubah={() => buka(p)} hapus={() => { hapus.reset(); setDihapus(p); }} />
              </tr>))}</tbody>
          </table>
        </Kartu>
      )}
      {dihapus && (
        <Konfirmasi bahaya buka judul="Hapus pengguna secara permanen?" teksYa="Ya, hapus" teksBatal="Batal"
          baris={[["Username", dihapus.username], ["Status", dihapus.aktif ? "Aktif" : "Nonaktif"]]}
          pesan="Akun dihapus dan tidak dapat dikembalikan. Akun yang sudah memiliki riwayat aktivitas tidak dapat dihapus."
          galat={hapus.error?.message} memuat={hapus.isPending} batal={() => setDihapus(null)} ya={() => hapus.mutate(dihapus)} />
      )}
    </div>
  );
}
