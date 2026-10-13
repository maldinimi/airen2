/** Viewer PDF (PDF.js dibundel lokal, tanpa CDN — B1). Lompat ke halaman & sorot bbox rujukan (E3). */
import * as pdfjs from "pdfjs-dist";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { ChevronLeft, ChevronRight, Download, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { urlFile } from "../api";
import { Memuat, Peringatan, Tombol } from "../ui";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export type Sorotan = { halaman: number; bbox: number[] | null } | null;

export default function PdfViewer({ fileId, judul, sorot }: { fileId: string; judul?: string; sorot?: Sorotan }) {
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const [hlm, setHlm] = useState(sorot?.halaman ?? 1);
  const [zoom, setZoom] = useState(1);
  const [ukuran, setUkuran] = useState<{ skala: number; w: number; h: number } | null>(null);
  const wadah = useRef<HTMLDivElement>(null);
  const kanvas = useRef<HTMLCanvasElement>(null);
  const kotakSorot = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setDoc(null); setGalat(null);
    const tugas = pdfjs.getDocument({ url: urlFile(fileId), withCredentials: true, isEvalSupported: false,
      cMapUrl: "/pdfjs/cmaps/", cMapPacked: true, standardFontDataUrl: "/pdfjs/standard_fonts/" });
    let batal = false;
    tugas.promise.then((d) => !batal && setDoc(d), () => !batal && setGalat("PDF tidak dapat dibuka atau Anda tidak memiliki akses."));
    return () => { batal = true; tugas.destroy(); };
  }, [fileId]);

  useEffect(() => { if (sorot?.halaman) setHlm(sorot.halaman); }, [sorot]);

  useEffect(() => {
    if (!doc || !kanvas.current || !wadah.current) return;
    let render: RenderTask | null = null;
    let batal = false;
    doc.getPage(Math.min(Math.max(1, hlm), doc.numPages)).then((page) => {
      if (batal || !kanvas.current || !wadah.current) return;
      const dasar = page.getViewport({ scale: 1 });
      const skala = ((wadah.current.clientWidth - 2) / dasar.width) * zoom;
      const vp = page.getViewport({ scale: skala });
      const dpr = window.devicePixelRatio || 1;
      const c = kanvas.current;
      c.width = Math.floor(vp.width * dpr); c.height = Math.floor(vp.height * dpr);
      c.style.width = `${vp.width}px`; c.style.height = `${vp.height}px`;
      render = page.render({ canvasContext: c.getContext("2d")!, viewport: vp, transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined });
      render.promise.then(() => setUkuran({ skala, w: vp.width, h: vp.height }), () => undefined);
    });
    return () => { batal = true; render?.cancel(); };
  }, [doc, hlm, zoom]);

  // Gulir hanya panel PDF (bukan halaman) agar bagian yang disorot terlihat.
  useEffect(() => {
    const k = kotakSorot.current, w = wadah.current;
    if (k && w) w.scrollTo({ top: Math.max(0, k.offsetTop - w.clientHeight / 3), behavior: "smooth" });
  }, [ukuran, sorot]);

  if (galat) return <div className="p-4"><Peringatan>{galat}</Peringatan></div>;
  const kotak = sorot && sorot.halaman === hlm && ukuran
    ? sorot.bbox
      ? { left: sorot.bbox[0] * ukuran.skala - 3, top: sorot.bbox[1] * ukuran.skala - 3,
          width: (sorot.bbox[2] - sorot.bbox[0]) * ukuran.skala + 6, height: (sorot.bbox[3] - sorot.bbox[1]) * ukuran.skala + 6 }
      : { left: 0, top: 0, width: ukuran.w, height: ukuran.h }
    : null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-3 py-2">
        <span className="mr-auto truncate text-sm font-medium text-slate-700" title={judul}>{judul}</span>
        <Tombol varian="hantu" kecil onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} aria-label="Perkecil"><ZoomOut className="size-4" /></Tombol>
        <Tombol varian="hantu" kecil onClick={() => setZoom((z) => Math.min(3, z + 0.25))} aria-label="Perbesar"><ZoomIn className="size-4" /></Tombol>
        <Tombol varian="hantu" kecil disabled={hlm <= 1} onClick={() => setHlm(hlm - 1)} aria-label="Halaman sebelumnya"><ChevronLeft className="size-4" /></Tombol>
        <span className="text-sm text-slate-600">
          hlm <input aria-label="Nomor halaman" className="w-12 rounded border border-slate-300 px-1 text-center" value={hlm}
            onChange={(e) => { const n = Number(e.target.value); if (n >= 1 && (!doc || n <= doc.numPages)) setHlm(n); }} /> / {doc?.numPages ?? "…"}
        </span>
        <Tombol varian="hantu" kecil disabled={!doc || hlm >= doc.numPages} onClick={() => setHlm(hlm + 1)} aria-label="Halaman berikutnya"><ChevronRight className="size-4" /></Tombol>
        <a href={urlFile(fileId)} target="_blank" rel="noreferrer" className="rounded p-1.5 text-slate-600 hover:bg-slate-100" title="Buka di tab baru"><Download className="size-4" /></a>
      </div>
      <div ref={wadah} className="min-h-0 flex-1 overflow-auto bg-slate-200 p-px">
        {!doc && <Memuat teks="Membuka PDF…" />}
        <div className="relative mx-auto w-fit bg-white shadow">
          <canvas ref={kanvas} />
          {kotak && <div ref={kotakSorot} className="sorot pointer-events-none absolute" style={kotak} aria-label="Bagian yang dirujuk" />}
        </div>
      </div>
    </div>
  );
}
