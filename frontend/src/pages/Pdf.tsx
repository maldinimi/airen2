import { ArrowLeft } from "lucide-react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import PdfViewer from "../components/PdfViewer";
import { Tombol } from "../ui";

/** Viewer PDF satu halaman penuh (A6, D3). */
export default function Pdf() {
  const { fileId } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const hlm = Number(sp.get("hlm") ?? 1);
  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col gap-3">
      <div><Tombol varian="sekunder" kecil onClick={() => nav(-1)}><ArrowLeft className="size-4" />Kembali</Tombol></div>
      <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200">
        <PdfViewer fileId={fileId!} judul={sp.get("judul") ?? "Dokumen"} sorot={{ halaman: hlm, bbox: null }} />
      </div>
    </div>
  );
}
