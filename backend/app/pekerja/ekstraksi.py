"""Ekstraksi PDF → halaman + elemen berkoordinat (desain §4.1). Pipeline sama untuk TOR, RAB, Panduan.

Dua ekstraktor (dipilih lewat `EKSTRAKTOR`):
- `docling`  : layout, urutan baca, tabel per sel, gambar, OCR Tesseract (ind+eng) untuk halaman scan.
- `sederhana`: pdfplumber (teks + tabel, tanpa OCR). Dipakai mode tiruan/CI agar image ringan.

Semua koordinat bbox: poin PDF, origin kiri-atas, [x0, y0, x1, y1] — sama dengan PDF.js di frontend.
Nomor halaman = indeks halaman file PDF (1..n), bukan nomor tercetak, agar klik rujukan selalu tepat (E3).
"""
import io
import logging
import os
import re
from dataclasses import dataclass, field

import pypdfium2 as pdfium

from app.konfigurasi import konfigurasi

logger = logging.getLogger("pekerja.ekstraksi")


@dataclass
class HalamanEkstrak:
    nomor: int
    lebar: float
    tinggi: float
    hasil_scan: bool = False


@dataclass
class ElemenEkstrak:
    halaman: int
    jenis: str  # paragraf | judul | butir | sel_tabel | gambar
    teks: str
    bbox: list[float] | None
    sumber: str = "teks"  # teks | ocr | vlm
    label_lokasi: str = ""
    tabel: dict = field(default_factory=dict)  # {nomor, baris, kolom, kolom_nama} untuk sel_tabel


RE_BAB = re.compile(r"^BAB\s+([IVXLC]+|\d+)\b", re.I)
RE_PASAL = re.compile(r"^Pasal\s+(\d+[A-Z]?)\b")
RE_AYAT = re.compile(r"^\((\d+)\)\s")
RE_HURUF = re.compile(r"^([a-z])[\.\)]\s")
RE_POIN = re.compile(r"^(\d+(?:\.\d+)*)[\.\)]?\s+\S")
RE_ROMAWI = re.compile(r"^([IVX]+)\.\s+\S")
RE_BUTIR = re.compile(r"^(\(?\d+[\.\)]|\(?[a-z][\.\)]|[•\-–▪●◦*])\s")


def halaman_scan(path: str) -> set[int]:
    """Halaman tanpa lapisan teks (hasil scan) → perlu OCR."""
    doc = pdfium.PdfDocument(path)
    try:
        return {i + 1 for i in range(len(doc)) if doc[i].get_textpage().count_chars() < 10}
    finally:
        doc.close()


def potong_gambar(path: str, halaman: int, bbox: list[float] | None, skala: float = 2.0) -> bytes:
    """Render bagian halaman (bbox, atau seluruh halaman) menjadi PNG untuk dideskripsikan VLM."""
    doc = pdfium.PdfDocument(path)
    try:
        gambar = doc[halaman - 1].render(scale=skala).to_pil()
    finally:
        doc.close()
    if bbox:
        x0, y0, x1, y1 = (max(0, int(v * skala)) for v in bbox)
        gambar = gambar.crop((x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)))
    gambar.thumbnail((1600, 1600))
    keluar = io.BytesIO()
    gambar.save(keluar, format="PNG")
    return keluar.getvalue()


def ekstrak(path: str) -> tuple[list[HalamanEkstrak], list[ElemenEkstrak]]:
    """Ekstrak PDF. Error dari library diteruskan (job menandai GAGAL dengan pesan ramah)."""
    k = konfigurasi()
    scan = halaman_scan(path)
    if k.ekstraktor == "docling":
        halaman, elemen = _docling(path)
    else:
        halaman, elemen = _sederhana(path, scan)
    for h in halaman:
        h.hasil_scan = h.nomor in scan
    for e in elemen:
        if e.halaman in scan and e.sumber == "teks":
            e.sumber = "ocr"
    beri_label_lokasi(elemen)
    return halaman, elemen


# ------------------------------------------------------------------ ekstraktor sederhana (pdfplumber)
def _sederhana(path: str, scan: set[int]) -> tuple[list[HalamanEkstrak], list[ElemenEkstrak]]:
    import pdfplumber

    halaman, elemen, nomor_tabel = [], [], 0
    with pdfplumber.open(path) as pdf:
        for no, page in enumerate(pdf.pages, 1):
            halaman.append(HalamanEkstrak(no, float(page.width), float(page.height)))
            tabel = page.find_tables()
            kotak = [t.bbox for t in tabel]

            def di_luar_tabel(obj, kotak=kotak) -> bool:
                if obj.get("object_type") != "char":
                    return True
                x, y = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
                return not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in kotak)

            baris_teks = page.filter(di_luar_tabel).extract_text_lines(return_chars=False)
            blok: list[ElemenEkstrak] = []
            for paragraf in _kelompokkan_baris(baris_teks):
                blok.append(ElemenEkstrak(no, _jenis_teks(paragraf["teks"]), paragraf["teks"], paragraf["bbox"]))
            for t in tabel:
                nomor_tabel += 1
                data = t.extract()
                kepala = [(c or "").strip().replace("\n", " ") for c in (data[0] if data else [])]
                for r, row in enumerate(t.rows):
                    for c, sel in enumerate(row.cells):
                        teks = (data[r][c] or "").strip() if r < len(data) and c < len(data[r]) else ""
                        if sel is None or not teks:
                            continue
                        blok.append(ElemenEkstrak(no, "sel_tabel", teks, [float(v) for v in sel], tabel={
                            "nomor": nomor_tabel, "baris": r + 1, "kolom": c + 1,
                            "kolom_nama": kepala[c] if c < len(kepala) and r > 0 else ""}))
            for img in page.images:
                if (img["x1"] - img["x0"]) > 60 and (img["bottom"] - img["top"]) > 60:
                    blok.append(ElemenEkstrak(no, "gambar", "", [float(img["x0"]), float(img["top"]), float(img["x1"]), float(img["bottom"])]))
            if no in scan and not any(b.jenis == "gambar" for b in blok):
                blok.append(ElemenEkstrak(no, "gambar", "", None))  # halaman scan utuh → dideskripsikan VLM
            blok.sort(key=lambda b: (b.bbox[1], b.bbox[0]) if b.bbox else (0, 0))
            elemen.extend(blok)
    return halaman, elemen


def _kelompokkan_baris(baris: list[dict]) -> list[dict]:
    """Gabungkan baris teks menjadi paragraf: baris baru bila jarak vertikal besar atau diawali penomoran."""
    hasil: list[dict] = []
    for b in baris:
        teks = b["text"].strip()
        if not teks:
            continue
        tinggi = b["bottom"] - b["top"]
        if hasil and b["top"] - hasil[-1]["bbox"][3] < 0.6 * tinggi and not RE_BUTIR.match(teks) \
                and not RE_BAB.match(teks) and not RE_PASAL.match(teks):
            p = hasil[-1]
            p["teks"] = f"{p['teks']} {teks}"
            p["bbox"] = [min(p["bbox"][0], b["x0"]), p["bbox"][1], max(p["bbox"][2], b["x1"]), b["bottom"]]
        else:
            hasil.append({"teks": teks, "bbox": [float(b["x0"]), float(b["top"]), float(b["x1"]), float(b["bottom"])]})
    return hasil


def _jenis_teks(teks: str) -> str:
    if RE_BAB.match(teks) or RE_PASAL.match(teks) or (len(teks) < 90 and teks.isupper()):
        return "judul"
    if RE_BUTIR.match(teks) or RE_POIN.match(teks):
        return "butir"
    return "paragraf"


# ------------------------------------------------------------------ ekstraktor docling
_konverter = None


def _docling(path: str) -> tuple[list[HalamanEkstrak], list[ElemenEkstrak]]:
    from docling_core.types.doc import DocItemLabel, ListItem, PictureItem, TableItem, TextItem

    global _konverter
    if _konverter is None:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        opsi = PdfPipelineOptions(
            artifacts_path=os.path.join(konfigurasi().data_dir, "models", "docling"),
            do_ocr=True, do_table_structure=True, ocr_options=TesseractCliOcrOptions(lang=["ind", "eng"]))
        _konverter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opsi)})
    doc = _konverter.convert(path).document
    ukuran = {no: (p.size.width, p.size.height) for no, p in doc.pages.items()}
    halaman = [HalamanEkstrak(no, w, h) for no, (w, h) in sorted(ukuran.items())]
    elemen: list[ElemenEkstrak] = []
    nomor_tabel = 0
    abaikan = {DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER}
    for item, _ in doc.iterate_items():
        if not getattr(item, "prov", None):
            continue
        prov = item.prov[0]
        tinggi = ukuran[prov.page_no][1]
        bb = prov.bbox.to_top_left_origin(tinggi)
        bbox = [bb.l, bb.t, bb.r, bb.b]
        if isinstance(item, TableItem):
            nomor_tabel += 1
            sel = item.data.table_cells
            kepala = {c.start_col_offset_idx: c.text.strip() for c in sel if c.start_row_offset_idx == 0}
            for c in sel:
                if not c.text.strip():
                    continue
                cb = c.bbox.to_top_left_origin(tinggi) if c.bbox else bb
                elemen.append(ElemenEkstrak(prov.page_no, "sel_tabel", c.text.strip(), [cb.l, cb.t, cb.r, cb.b], tabel={
                    "nomor": nomor_tabel, "baris": c.start_row_offset_idx + 1, "kolom": c.start_col_offset_idx + 1,
                    "kolom_nama": kepala.get(c.start_col_offset_idx, "") if c.start_row_offset_idx > 0 else ""}))
        elif isinstance(item, PictureItem):
            elemen.append(ElemenEkstrak(prov.page_no, "gambar", "", bbox))
        elif isinstance(item, TextItem) and item.label not in abaikan and item.text.strip():
            teks = item.text.strip()
            if isinstance(item, ListItem):
                penanda = (item.marker or "").strip()
                if penanda and not teks.startswith(penanda):
                    teks = f"{penanda} {teks}"
                jenis = "butir"
            elif item.label in (DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE):
                jenis = "judul"
            else:
                jenis = _jenis_teks(teks)
            elemen.append(ElemenEkstrak(prov.page_no, jenis, teks, bbox))
    return halaman, elemen


# ------------------------------------------------------------------ label lokasi
def beri_label_lokasi(elemen: list[ElemenEkstrak]) -> None:
    """Lacak hierarki penomoran (Bab → poin → paragraf; Pasal → ayat → huruf; Tabel → baris → kolom)
    agar setiap elemen punya lokasi yang dapat dibaca manusia (E1, E2)."""
    bab = poin = pasal = ayat = None
    paragraf = 0
    for e in elemen:
        t = e.teks.strip()
        if e.jenis == "sel_tabel":
            kolom = f"kolom “{e.tabel['kolom_nama']}”" if e.tabel.get("kolom_nama") else f"kolom {e.tabel['kolom']}"
            e.label_lokasi = _gabung(bab, poin, pasal, f"Tabel {e.tabel['nomor']}, baris {e.tabel['baris']}, {kolom}")
            continue
        if e.jenis == "gambar":
            e.label_lokasi = _gabung(bab, poin, pasal, "Gambar")
            continue
        if m := RE_BAB.match(t):
            bab, poin, pasal, ayat, paragraf = f"Bab {m.group(1).upper()}", None, None, None, 0
            e.label_lokasi = bab
        elif m := RE_PASAL.match(t):
            pasal, ayat, paragraf = f"Pasal {m.group(1)}", None, 0
            e.label_lokasi = _gabung(bab, None, pasal, None)
        elif pasal and (m := RE_AYAT.match(t)):
            ayat = f"ayat ({m.group(1)})"
            e.label_lokasi = _gabung(bab, None, f"{pasal} {ayat}", None)
        elif m := RE_HURUF.match(t):
            konteks = f"{pasal} {ayat}" if pasal and ayat else pasal
            e.label_lokasi = _gabung(bab, poin, konteks, f"huruf {m.group(1)}")
        elif e.jenis in ("judul", "butir") and (m := RE_POIN.match(t) or RE_ROMAWI.match(t)):
            if e.jenis == "judul" or "." in m.group(1) or not poin:
                poin, paragraf = f"poin {m.group(1)}", 0
                e.label_lokasi = _gabung(bab, poin, pasal, None)
            else:
                e.label_lokasi = _gabung(bab, poin, pasal, f"butir {m.group(1)}")
        elif e.jenis == "judul":
            paragraf = 0
            e.label_lokasi = _gabung(bab, poin, pasal, f"judul “{t[:60]}”")
        else:
            paragraf += 1
            e.label_lokasi = _gabung(bab, poin, pasal, f"paragraf {paragraf}")


def _gabung(bab, poin, pasal, akhir) -> str:
    bagian = [b for b in (bab, pasal or poin, akhir) if b]
    return " › ".join(bagian) or "Awal dokumen"
