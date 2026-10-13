import { type FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Input, Kolom, Peringatan, Tombol } from "../ui";

export default function Login() {
  const { pengguna, masuk } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [galat, setGalat] = useState<string | null>(null);
  const [memuat, setMemuat] = useState(false);
  if (pengguna) return <Navigate to="/" replace />;

  const kirim = async (e: FormEvent) => {
    e.preventDefault();
    setMemuat(true); setGalat(null);
    try { await masuk(username, password); nav("/"); }
    catch (err) { setGalat((err as Error).message); }
    finally { setMemuat(false); }
  };

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-utama-900 via-utama-700 to-utama-500 p-4">
      <form onSubmit={kirim} className="w-full max-w-sm space-y-5 rounded-2xl bg-white p-7 shadow-2xl">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-11" />
          <div>
            <h1 className="text-lg font-semibold text-slate-900">AIREN</h1>
            <p className="text-sm text-slate-500">Asisten AI Review TOR & RAB</p>
          </div>
        </div>
        {galat && <Peringatan>{galat}</Peringatan>}
        <Kolom label="Username"><Input autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required /></Kolom>
        <Kolom label="Password"><Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></Kolom>
        <Tombol type="submit" memuat={memuat} className="w-full">Masuk</Tombol>
        <p className="text-center text-xs text-slate-400">Seluruh pemrosesan berjalan di lingkungan instansi.</p>
      </form>
    </div>
  );
}
