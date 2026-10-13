/** Buat Usulan (A1) / Ubah Draf / Unggah Revisi (§5: TOR saja, RAB saja, atau keduanya). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import Unggah from "../components/Unggah";
import type { BarisUsulan } from "../types";
import { Input, Judul, Kartu, Kolom, Memuat, Peringatan, Tombol } from "../ui";

export default function UsulanForm({ mode }: { mode: "baru" | "draf" | "revisi" }) {
  const { id } = useParams();
  const { pengguna } = useAuth();
  const nav = useNavigate();
  const qc = useQueryClient();
  const ada = useQuery({ queryKey: ["usulan", id], queryFn: () => api.get<BarisUsulan>(`/api/usulan/${id}`), enabled: mode !== "baru" });
  const [tahun, setTahun] = useState("");
  const [kode, setKode] = useState("");
  const [nama, setNama] = useState("");
  const [tor, setTor] = useState<File | null>(null);
  const [rab, setRab] = useState<File | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [memuat, setMemuat] = useState<"draf" | "ajukan" | null>(null);

  if (mode !== "baru" && ada.isLoading) return <Memuat />;
  const u = ada.data;
  const kirim = async (e: FormEvent, ajukan: boolean) => {
    e.preventDefault();
    setGalat(null);
    if (mode === "baru" && (!tor || !rab)) return setGalat("TOR dan RAB wajib diunggah (PDF).");
    if (mode === "revisi" && !tor && !rab) return setGalat("Unggah minimal satu dokumen pengganti (TOR atau RAB).");
    const fd = new FormData();
    if (mode !== "revisi") {
      if (tahun || mode === "baru") fd.set("tahun_anggaran", tahun);
      if (kode || mode === "baru") fd.set("kode_ro", kode);
      if (nama || mode === "baru") fd.set("nama_ro", nama);
    }
    if (tor) fd.set("tor", tor);
    if (rab) fd.set("rab", rab);
    fd.set("ajukan", String(ajukan));
    setMemuat(ajukan ? "ajukan" : "draf");
    try {
      const url = mode === "baru" ? "/api/usulan" : mode === "draf" ? `/api/usulan/${id}/draf` : `/api/usulan/${id}/revisi`;
      if (mode === "draf") await api.put(url, fd); else await api.post(url, fd);
      await qc.invalidateQueries();
      nav("/usulan");
    } catch (err) { setGalat((err as Error).message); }
    finally { setMemuat(null); }
  };

  const judul = { baru: "Buat Usulan", draf: "Ubah Draf Usulan", revisi: "Unggah Revisi" }[mode];
  return (
    <div className="max-w-3xl">
      <Judul judul={judul} sub={u ? `${u.kode_ro} · ${u.nama_ro} · ${u.satker.nama}` : `Satker: ${pengguna?.satker?.nama ?? "—"}`} />
      <Kartu className="p-5">
        <form className="space-y-5" onSubmit={(e) => kirim(e, false)}>
          {galat && <Peringatan>{galat}</Peringatan>}
          {mode === "revisi" && u && (
            <Peringatan jenis="info">Revisi ke-{u.revisi_nomor + 1}. Unggah dokumen yang ingin diganti saja (TOR, RAB, atau keduanya);
              dokumen yang tidak diganti terbawa dari revisi {u.revisi_nomor}.</Peringatan>
          )}
          {mode !== "revisi" && (
            <div className="grid gap-4 sm:grid-cols-3">
              <Kolom label="Satker"><Input value={u?.satker.nama ?? pengguna?.satker?.nama ?? ""} disabled /></Kolom>
              <Kolom label="Tahun Anggaran" wajib={mode === "baru"}>
                <Input type="number" min={2000} max={2100} placeholder={u ? String(u.tahun_anggaran) : "2027"} value={tahun}
                  onChange={(e) => setTahun(e.target.value)} required={mode === "baru"} /></Kolom>
              <Kolom label="Kode RO" wajib={mode === "baru"}>
                <Input placeholder={u?.kode_ro ?? "mis. 1234.ABC.001"} value={kode} onChange={(e) => setKode(e.target.value)} required={mode === "baru"} /></Kolom>
              <div className="sm:col-span-3"><Kolom label="Nama RO" wajib={mode === "baru"}>
                <Input placeholder={u?.nama_ro ?? "Nama Rincian Output"} value={nama} onChange={(e) => setNama(e.target.value)} required={mode === "baru"} /></Kolom></div>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Unggah label={mode === "baru" ? "PDF TOR *" : "Ganti PDF TOR"} file={tor} ubah={(f) => setTor(f[0] ?? null)}
              keterangan={u && !tor ? `Saat ini: ${u.tor.nama}` : undefined} />
            <Unggah label={mode === "baru" ? "PDF RAB *" : "Ganti PDF RAB"} file={rab} ubah={(f) => setRab(f[0] ?? null)}
              keterangan={u && !rab ? `Saat ini: ${u.rab.nama}` : undefined} />
          </div>
          <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
            <Tombol type="button" varian="hantu" onClick={() => nav(-1)}>Batal</Tombol>
            <Tombol type="submit" varian="sekunder" memuat={memuat === "draf"} disabled={!!memuat}>Simpan Draf</Tombol>
            <Tombol type="button" memuat={memuat === "ajukan"} disabled={!!memuat} onClick={(e) => kirim(e, true)}>Simpan & Ajukan Review</Tombol>
          </div>
        </form>
      </Kartu>
    </div>
  );
}
