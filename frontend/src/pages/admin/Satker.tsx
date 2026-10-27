/** Kelola Satker: Satuan Kerja = UKE II (Eselon II) beserta Unit Kerja induknya = UKE I (Eselon I), kolom mengikuti
 *  dokumen "Data Satker dan Unit Kerja". Pengguna merujuk ke Satker ini. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { api } from "../../api";
import { Aksi, HalamanDetail, HalamanForm, LencanaAktif, PilihBawah, type Satker, TD, barisJejak, daftarUke1, kunciUke1, th, usePesanSukses } from "../../components/Kelola";
import { Input, Judul, Kartu, Kolom, Konfirmasi, Kosong, Memuat, Peringatan, Tombol, cx } from "../../ui";

type Isian = Pick<Satker, KolomIsi> & { id?: string; aktif: boolean };
type KolomIsi = "kode_uke1" | "unit_kerja" | "kode_uke2" | "nama";

// Satu daftar kolom (urutan dokumen) untuk tabel, detail, dan konfirmasi hapus.
const KOLOM: { k: KolomIsi; label: string; lebar: string }[] = [
  { k: "kode_uke1", label: "Kode UKE I", lebar: "whitespace-nowrap" },
  { k: "unit_kerja", label: "Unit Kerja (Eselon I)", lebar: "min-w-[14rem]" },
  { k: "kode_uke2", label: "Kode UKE II", lebar: "whitespace-nowrap" },
  { k: "nama", label: "Satuan Kerja (Eselon II)", lebar: "min-w-[16rem] font-medium text-slate-900" },
];

const KOSONG: Isian = { kode_uke1: "", unit_kerja: "", kode_uke2: "", nama: "", aktif: true };
type Referensi = Pick<Satker, KolomIsi>;
const pesan = (nama: string, aksi: string) => `Satuan Kerja ${nama.trim() || "(tanpa nama)"} berhasil ${aksi}.`;
// Form Tambah & Ubah: Unit Kerja (UKE I) saja, atau Satuan Kerja (UKE II) di bawah Unit Kerja induk.
type Jenis = "unit" | "satuan";
const jenisDari = (s: Pick<Satker, "nama" | "unit_kerja">): Jenis => (!s.nama && s.unit_kerja ? "unit" : "satuan");

export default function KelolaSatker() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["satker"], queryFn: () => api.get<Satker[]>("/api/satker") });
  const [sukses, setSukses] = usePesanSukses();
  const [form, setForm] = useState<Isian | null>(null);
  // Unit Kerja induk dipilih dari daftar resmi dokumen + Unit Kerja yang sudah ada, agar penulisannya seragam di database.
  const ref = useQuery({ queryKey: ["satker", "referensi"], queryFn: () => api.get<Referensi[]>("/api/satker/referensi") });
  const uke1 = daftarUke1([...(ref.data ?? []), ...(q.data ?? [])]);
  const [modeUke1, setModeUke1] = useState("");  // kunci Unit Kerja induk terpilih ("" = belum dipilih)
  const [jenis, setJenis] = useState<Jenis>("satuan");
  const [galatForm, setGalatForm] = useState<string | null>(null);
  const simpan = useMutation({
    mutationFn: () => (form!.id ? api.put(`/api/satker/${form!.id}`, form) : api.post("/api/satker", form)),
    onSuccess: () => {
      setSukses(jenis === "unit" ? `Unit Kerja ${(form!.unit_kerja ?? "").trim()} berhasil disimpan.` : pesan(form!.nama, "disimpan"));
      setForm(null);
      qc.invalidateQueries({ queryKey: ["satker"] }); qc.invalidateQueries({ queryKey: ["pengguna"] });
    },
  });
  const buka = (s?: Satker) => {
    simpan.reset();
    setGalatForm(null);
    setJenis(s ? jenisDari(s) : "satuan");
    setForm(s ? { ...KOSONG, ...Object.fromEntries(KOLOM.map(({ k }) => [k, s[k] ?? ""])), id: s.id, aktif: s.aktif ?? true } : KOSONG);
    setModeUke1(s && uke1.some((u) => u.kunci === kunciUke1(s)) ? kunciUke1(s) : "");
  };
  const pilihUke1 = (nilai: string) => {
    const u = uke1.find((x) => x.kunci === nilai);
    setModeUke1(nilai);
    setForm({ ...form!, kode_uke1: u?.kode_uke1 ?? "", unit_kerja: u?.unit_kerja ?? "" });
  };
  // Ganti jenis = isi ulang dari awal; di Ubah, id & status baris tetap.
  const pilihJenis = (j: Jenis) => { setJenis(j); setModeUke1(""); setGalatForm(null); setForm({ ...KOSONG, id: form!.id, aktif: form!.aktif }); };
  const kirim = () => {
    if (jenis === "satuan" && !modeUke1) return setGalatForm("Pilih Unit Kerja induk terlebih dahulu.");
    setGalatForm(null);
    simpan.mutate();
  };
  const [lihat, setLihat] = useState<Satker | null>(null);
  const [dihapus, setDihapus] = useState<Satker | null>(null);
  const hapus = useMutation({
    mutationFn: (s: Satker) => api.del(`/api/satker/${s.id}`),
    onSuccess: (_, s) => { setSukses(pesan(s.nama, "dihapus")); setDihapus(null); qc.invalidateQueries({ queryKey: ["satker"] }); },
  });
  const isian = (k: KolomIsi, label: string, maks: number, wajib = false) => (
    <Kolom label={label} wajib={wajib}>
      <Input required={wajib} maxLength={maks} value={form?.[k] ?? ""} onChange={(e) => setForm({ ...form!, [k]: e.target.value })} />
    </Kolom>
  );
  // Kode UKE I yang sudah dipakai Unit Kerja lain (selain baris yang sedang diubah) — ditampilkan sebagai petunjuk.
  const kodeUke1Terpakai = [...new Set(uke1.filter((u) => u.kode_uke1 && u.unit_kerja !== form?.unit_kerja).map((u) => u.kode_uke1))]
    .sort().join(", ");
  const pilihanUke1 = uke1.map((u) => ({ nilai: u.kunci, label: [u.kode_uke1, u.unit_kerja].filter(Boolean).join(" — ") }));
  const isi = (s: Satker) => KOLOM.map(({ k, label }): [string, string] => [label, s[k] || "—"]);

  if (lihat) return (
    <HalamanDetail kembali="Satuan Kerja" judul="Detail Satuan Kerja" sub={lihat.nama || "—"} tutup={() => setLihat(null)}
      info={[...isi(lihat), ["Status", <LencanaAktif aktif={lihat.aktif !== false} />], ...barisJejak(lihat)]} />
  );

  if (form) return (
    <HalamanForm judul={form.id ? "Ubah Satuan Kerja" : "Tambah Satuan Kerja"} sub={form.id ? "Perbarui data Unit Kerja (Eselon I) atau Satuan Kerja (Eselon II)." : "Pilih tingkat yang ditambahkan: Unit Kerja (Eselon I), atau Satuan Kerja (Eselon II) beserta Unit Kerja induknya."}
      tutup={() => setForm(null)} kirim={kirim} reset={form.id ? undefined : () => buka()}
      galat={galatForm ? new Error(galatForm) : simpan.error} sibuk={simpan.isPending}>
      <fieldset className="space-y-1.5">
        <legend className="text-sm font-medium text-slate-700">Tingkat<span className="text-red-600"> *</span></legend>
        <div className="flex flex-wrap gap-6">
          {([["unit", "Unit Kerja"], ["satuan", "Satuan Kerja"]] as const).map(([j, label]) => (
            <label key={j} className="flex items-center gap-2 text-sm">
              <input type="radio" name="jenis" checked={jenis === j} onChange={() => pilihJenis(j)} />{label}
            </label>
          ))}
        </div>
      </fieldset>
      {jenis === "unit" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <Kolom label="Kode UKE I" petunjuk={`Format NN, mis. 01.${kodeUke1Terpakai ? ` Sudah dipakai: ${kodeUke1Terpakai}.` : ""}`}>
            <Input maxLength={2} inputMode="numeric" placeholder="NN" value={form.kode_uke1 ?? ""}
              onChange={(e) => setForm({ ...form, kode_uke1: e.target.value })} />
          </Kolom>
          {isian("unit_kerja", "Nama Unit Kerja", 255, true)}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {/* Kode → nama → dropdown induk. */}
          <Kolom label="Kode UKE II" petunjuk={form.kode_uke1 ? `Format ${form.kode_uke1}.NN, mis. ${form.kode_uke1}.01.` : "Format NN.NN, mis. 01.04."}>
            <Input maxLength={5} placeholder={form.kode_uke1 ? `${form.kode_uke1}.` : "NN.NN"} value={form.kode_uke2 ?? ""}
              onChange={(e) => setForm({ ...form, kode_uke2: e.target.value })} />
          </Kolom>
          {isian("nama", "Nama Satuan Kerja", 255, true)}
          <Kolom label="Unit Kerja (induk)" wajib>
            <PilihBawah nilai={modeUke1} ubah={pilihUke1} kosong="— pilih Unit Kerja —" opsi={pilihanUke1} />
          </Kolom>
        </div>
      )}
    </HalamanForm>
  );

  return (
    <div className="w-full">
      <Judul judul="Satuan Kerja" sub="Kelola Unit Kerja (Eselon I) dan Satuan Kerja (Eselon II) beserta kodenya. Satuan Kerja dipilih saat membuat akun Pengusul."
        aksi={<Tombol onClick={() => buka()}><Plus className="size-4" />Tambah Satuan Kerja</Tombol>} />
      {sukses && <div className="mb-3"><Peringatan jenis="sukses">{sukses}</Peringatan></div>}
      {q.isLoading ? <Memuat /> : q.error ? <Peringatan>{(q.error as Error).message}</Peringatan> : !q.data?.length ? <Kosong>Belum ada Satuan Kerja.</Kosong> : (
        <Kartu className="overflow-x-auto">
          <table className="w-full min-w-[60rem] text-sm">
            <thead className="bg-slate-100 text-xs font-semibold text-slate-700">
              <tr>{["No", ...KOLOM.map((x) => x.label), "Aksi"].map(th)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">{q.data.map((s, i) => (
              <tr key={s.id} className={cx("align-middle transition-colors hover:bg-slate-50", s.aktif === false && "bg-slate-50 text-slate-400")}>
                <td className={cx(TD, "text-slate-500")}>{i + 1}</td>
                {KOLOM.map(({ k, lebar }) => (
                  <td key={k} className={cx(TD, s.aktif === false ? "text-slate-400" : "text-slate-700", lebar)}>
                    {s[k] || "—"}{k === "nama" && s.aktif === false && <div className="mt-1"><LencanaAktif aktif={false} /></div>}
                  </td>
                ))}
                <Aksi nama={s.nama || "Satuan Kerja"} lihat={() => setLihat(s)} ubah={() => buka(s)} hapus={() => { hapus.reset(); setDihapus(s); }} />
              </tr>))}</tbody>
          </table>
        </Kartu>
      )}
      {dihapus && (
        <Konfirmasi bahaya buka judul="Hapus Satuan Kerja secara permanen?" teksYa="Ya, hapus" teksBatal="Batal" baris={isi(dihapus)}
          pesan="Satuan Kerja dihapus dan tidak dapat dikembalikan. Satuan Kerja yang masih dipakai pengguna atau usulan tidak dapat dihapus."
          galat={hapus.error?.message} memuat={hapus.isPending} batal={() => setDihapus(null)} ya={() => hapus.mutate(dihapus)} />
      )}
    </div>
  );
}
