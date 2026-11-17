import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Akun from "./pages/Akun";
import Audit from "./pages/admin/Audit";
import KelolaChecklist from "./pages/admin/Checklist";
import KelolaKategori, { KategoriDetail, KategoriForm } from "./pages/admin/Kategori";
import KelolaMasterRO from "./pages/admin/MasterRO";
import NodeAI from "./pages/admin/NodeAI";
import KelolaPengguna from "./pages/admin/Pengguna";
import KelolaSatker from "./pages/admin/Satker";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import PanduanPage, { PanduanDetail } from "./pages/Panduan";
import PanduanForm from "./pages/PanduanForm";
import Pdf from "./pages/Pdf";
import ReviewDetail from "./pages/ReviewDetail";
import Riwayat from "./pages/Riwayat";
import UsulanForm from "./pages/UsulanForm";
import UsulanList from "./pages/UsulanList";
import type { Role } from "./types";
import { Memuat } from "./ui";

const KERJA: Role[] = ["PENGUSUL", "REVIEWER"];

function Wajib({ role, children }: { role?: Role[]; children: JSX.Element }) {
  const { pengguna, memuat, punya } = useAuth();
  if (memuat) return <Memuat />;
  if (!pengguna) return <Navigate to="/login" replace />;
  if (role && !punya(...role)) return <Navigate to="/" replace />;
  return children;
}

/** Halaman awal: Dashboard untuk Pengusul/Reviewer. Admin tidak memiliki Dashboard → langsung ke menu Pengguna. */
function Beranda() {
  const { punya } = useAuth();
  return punya(...KERJA) ? <Dashboard /> : <Navigate to="/kelola/pengguna" replace />;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Wajib><Layout /></Wajib>}>
          <Route index element={<Beranda />} />
          {/* Usulan, review, Panduan & PDF: Pengusul dan Reviewer (Admin tidak memiliki menu ini). */}
          <Route path="usulan" element={<Wajib role={KERJA}><UsulanList /></Wajib>} />
          <Route path="usulan/baru" element={<Wajib role={["PENGUSUL"]}><UsulanForm mode="baru" /></Wajib>} />
          <Route path="usulan/:id/draf" element={<Wajib role={["PENGUSUL"]}><UsulanForm mode="draf" /></Wajib>} />
          <Route path="usulan/:id/revisi" element={<Wajib role={["PENGUSUL"]}><UsulanForm mode="revisi" /></Wajib>} />
          <Route path="usulan/:id/riwayat" element={<Wajib role={KERJA}><Riwayat /></Wajib>} />
          <Route path="review/:id" element={<Wajib role={KERJA}><ReviewDetail /></Wajib>} />
          <Route path="pdf/:fileId" element={<Wajib role={KERJA}><Pdf /></Wajib>} />
          <Route path="panduan" element={<Wajib role={KERJA}><PanduanPage /></Wajib>} />
          <Route path="panduan/:id" element={<Wajib role={KERJA}><PanduanDetail /></Wajib>} />
          <Route path="panduan/unggah" element={<Wajib role={["REVIEWER"]}><PanduanForm mode="unggah" /></Wajib>} />
          <Route path="panduan/:id/ubah" element={<Wajib role={["REVIEWER"]}><PanduanForm mode="ubah" /></Wajib>} />
          <Route path="akun" element={<Akun />} />
          {/* Checklist & Kategori: Reviewer mengelola; Pengusul hanya melihat (daftar + detail). */}
          <Route path="kelola/checklist" element={<Wajib role={KERJA}><KelolaChecklist /></Wajib>} />
          <Route path="kelola/kategori" element={<Wajib role={KERJA}><KelolaKategori /></Wajib>} />
          <Route path="kelola/kategori/tambah" element={<Wajib role={["REVIEWER"]}><KategoriForm mode="tambah" /></Wajib>} />
          <Route path="kelola/kategori/:id" element={<Wajib role={KERJA}><KategoriDetail /></Wajib>} />
          <Route path="kelola/kategori/:id/ubah" element={<Wajib role={["REVIEWER"]}><KategoriForm mode="ubah" /></Wajib>} />
          <Route path="kelola/satker" element={<Wajib role={["REVIEWER"]}><KelolaSatker /></Wajib>} />
          <Route path="kelola/master-ro" element={<Wajib role={["REVIEWER"]}><KelolaMasterRO /></Wajib>} />
          <Route path="kelola/pengguna" element={<Wajib role={["ADMIN"]}><KelolaPengguna /></Wajib>} />
          <Route path="kelola/node-ai" element={<Wajib role={["ADMIN"]}><NodeAI /></Wajib>} />
          <Route path="audit" element={<Wajib role={["ADMIN"]}><Audit /></Wajib>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
