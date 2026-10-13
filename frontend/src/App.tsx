import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Akun from "./pages/Akun";
import Audit from "./pages/admin/Audit";
import KelolaChecklist from "./pages/admin/Checklist";
import KelolaKategori from "./pages/admin/Kategori";
import NodeAI from "./pages/admin/NodeAI";
import KelolaPengguna from "./pages/admin/Pengguna";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import PanduanPage from "./pages/Panduan";
import Pdf from "./pages/Pdf";
import ReviewDetail from "./pages/ReviewDetail";
import Riwayat from "./pages/Riwayat";
import UsulanForm from "./pages/UsulanForm";
import UsulanList from "./pages/UsulanList";
import type { Role } from "./types";
import { Memuat } from "./ui";

function Wajib({ role, children }: { role?: Role[]; children: JSX.Element }) {
  const { pengguna, memuat, punya } = useAuth();
  if (memuat) return <Memuat />;
  if (!pengguna) return <Navigate to="/login" replace />;
  if (role && !punya(...role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Wajib><Layout /></Wajib>}>
          <Route index element={<Dashboard />} />
          <Route path="usulan" element={<UsulanList />} />
          <Route path="usulan/baru" element={<Wajib role={["PENGUSUL"]}><UsulanForm mode="baru" /></Wajib>} />
          <Route path="usulan/:id/draf" element={<Wajib role={["PENGUSUL"]}><UsulanForm mode="draf" /></Wajib>} />
          <Route path="usulan/:id/revisi" element={<Wajib role={["PENGUSUL"]}><UsulanForm mode="revisi" /></Wajib>} />
          <Route path="usulan/:id/riwayat" element={<Riwayat />} />
          <Route path="review/:id" element={<ReviewDetail />} />
          <Route path="pdf/:fileId" element={<Pdf />} />
          <Route path="panduan" element={<PanduanPage />} />
          <Route path="akun" element={<Akun />} />
          <Route path="kelola/checklist" element={<Wajib role={["ADMIN"]}><KelolaChecklist /></Wajib>} />
          <Route path="kelola/kategori" element={<Wajib role={["ADMIN"]}><KelolaKategori /></Wajib>} />
          <Route path="kelola/pengguna" element={<Wajib role={["ADMIN"]}><KelolaPengguna /></Wajib>} />
          <Route path="kelola/node-ai" element={<Wajib role={["ADMIN"]}><NodeAI /></Wajib>} />
          <Route path="audit" element={<Wajib role={["ADMIN"]}><Audit /></Wajib>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
