import { type FormEvent, useState } from "react";
import { api } from "../api";
import { Input, Judul, Kartu, Kolom, Peringatan, Tombol } from "../ui";

export default function Akun() {
  const [lama, setLama] = useState("");
  const [baru, setBaru] = useState("");
  const [ulang, setUlang] = useState("");
  const [pesan, setPesan] = useState<{ jenis: "error" | "info"; teks: string } | null>(null);
  const [memuat, setMemuat] = useState(false);

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    if (baru !== ulang) return setPesan({ jenis: "error", teks: "Konfirmasi password baru tidak sama." });
    setMemuat(true);
    try {
      await api.post("/api/auth/ganti-password", { password_lama: lama, password_baru: baru });
      setPesan({ jenis: "info", teks: "Password berhasil diganti." });
      setLama(""); setBaru(""); setUlang("");
    } catch (err) { setPesan({ jenis: "error", teks: (err as Error).message }); }
    finally { setMemuat(false); }
  };

  return (
    <div className="max-w-md">
      <Judul judul="Ganti password" />
      <Kartu className="p-5">
        <form onSubmit={kirim} className="space-y-4">
          {pesan && <Peringatan jenis={pesan.jenis}>{pesan.teks}</Peringatan>}
          <Kolom label="Password lama" wajib><Input type="password" value={lama} onChange={(e) => setLama(e.target.value)} required autoComplete="current-password" /></Kolom>
          <Kolom label="Password baru" wajib petunjuk="Minimal 8 karakter, kombinasi huruf dan angka/simbol.">
            <Input type="password" value={baru} onChange={(e) => setBaru(e.target.value)} required autoComplete="new-password" /></Kolom>
          <Kolom label="Ulangi password baru" wajib><Input type="password" value={ulang} onChange={(e) => setUlang(e.target.value)} required autoComplete="new-password" /></Kolom>
          <Tombol type="submit" memuat={memuat}>Simpan</Tombol>
        </form>
      </Kartu>
    </div>
  );
}
