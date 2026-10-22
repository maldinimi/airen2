"""Pipeline review AI (desain §4): Screening 1 per item → keselarasan RAB–TOR → rekomendasi → Screening 2.

Jaminan utama:
- Label dihitung KODE dari hasil per item (§7.1), bukan oleh LLM.
- Semua rujukan diverifikasi (rujukan.py); sebelum hasil disimpan, invarian kutipan diperiksa.
  Bila gagal → review GAGAL, tidak ada rujukan salah yang tersimpan (CLAUDE.md aturan 3).
- Hasil per item disimpan bertahap; worker yang mati dilanjutkan node lain dari item terakhir.
"""
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import status as st
from app.db import SessionLokal
from app.konfigurasi import konfigurasi
from app.log import log, set_konteks, tahap
from app.checklist import IsiItem, isi_review, sidik_checklist
from app.model import (ChecklistItem, Elemen, File, HasilItem, HasilKategori, KategoriVersi, Panduan,
                       Rekomendasi, Review, ReviewPanduan, Revisi, Rujukan, Usulan)
from app.nilai_final import hitung_label
from app.pekerja import prompt as pr
from app.pekerja.llm import info_model
from app.pekerja.pencarian import cari, elemen_urut
from app.pekerja.proses_file import GalatPengguna, proses_file
from app.pekerja.rujukan import RujukanSah, periksa_invarian, verifikasi
from app.pekerja.sidik import fingerprint

logger = logging.getLogger("pekerja.review")
MAKS_TEKS_ELEMEN = 2000


class GalatInvarian(Exception):
    pass


@dataclass
class Konteks:
    """Data yang dibagikan ke penilaian item (dibaca thread pekerja; hanya ID, bukan objek sesi)."""
    tor_id: uuid.UUID
    rab_id: uuid.UUID
    panduan: dict[uuid.UUID, str] = field(default_factory=dict)  # file_id → judul panduan

    def nama(self, file_id) -> str:
        return {self.tor_id: "TOR", self.rab_id: "RAB"}.get(file_id) or self.panduan.get(file_id, "Panduan")


def format_konteks(elemen: list[Elemen], awalan: str, ktx: Konteks) -> tuple[str, dict[str, Elemen], list[tuple[str, str]]]:
    """Beri alias stabil (E1.. / P1..) — urutan elemen sudah stabil (file, halaman, urutan)."""
    baris, peta, alias = [], {}, []
    for i, e in enumerate(elemen, 1):
        a = f"{awalan}{i}"
        peta[a] = e
        alias.append((a, e.teks))
        catatan = " (deskripsi gambar oleh AI)" if e.sumber == "vlm" else (" (hasil OCR)" if e.sumber == "ocr" else "")
        baris.append(f"[{a}] {ktx.nama(e.file_id)} hlm {e.halaman} · {e.label_lokasi}{catatan}\n{e.teks[:MAKS_TEKS_ELEMEN]}")
    return "\n\n".join(baris), peta, alias


def _seluruh_atau_cari(db: Session, file_id, kueri: str, k: int) -> list[Elemen]:
    """Dokumen kecil (mis. RAB ±10 hlm) disertakan utuh; bila melebihi anggaran konteks, pakai pencarian."""
    total = db.scalar(select(func.sum(func.length(Elemen.teks))).where(Elemen.file_id == file_id)) or 0
    if total <= konfigurasi().konteks_maks_karakter // 2:
        return list(db.scalars(select(Elemen).where(Elemen.file_id == file_id).order_by(Elemen.halaman, Elemen.urutan)))
    return cari(db, [file_id], kueri, konfigurasi().kandidat_dokumen)


# ---------------------------------------------------------------- Screening 1: per item
def nilai_item(item: IsiItem, ktx: Konteks, llm) -> dict:
    """Nilai satu item checklist (dijalankan di thread) memakai isinya saat review dikunci.
    Kembalikan dict hasil + rujukan sah."""
    k = konfigurasi()
    with SessionLokal() as db:
        kueri = f"{item.judul}. {item.kriteria}"
        dok: list[Elemen] = []
        if item.berlaku_untuk in ("TOR", "TOR & RAB"):
            dok += cari(db, [ktx.tor_id], kueri, k.kandidat_dokumen)
        if item.berlaku_untuk in ("RAB", "TOR & RAB"):
            dok += _seluruh_atau_cari(db, ktx.rab_id, kueri, k.kandidat_dokumen)
        ringkas = " ".join(e.teks for e in dok)[:600]
        pdn = cari(db, list(ktx.panduan), f"{kueri} {ringkas}", k.kandidat_panduan)
        umpan_balik, sapuan_selesai = None, item.berlaku_untuk == "RAB"
        for percobaan in range(3):
            teks_dok, peta_dok, alias_dok = format_konteks(dok, "E", ktx)
            teks_pdn, peta_pdn, alias_pdn = format_konteks(pdn, "P", ktx)
            out = llm.json("nilai_item", pr.prompt_nilai_item(item, teks_dok, teks_pdn, umpan_balik),
                           pr.skema_nilai_item(list(peta_dok), list(peta_pdn)),
                           konteks={"kode": item.kode, "alias_dok": alias_dok, "alias_panduan": alias_pdn})
            if not out.get("ditemukan", True) and not sapuan_selesai:
                # Sapuan konfirmasi (desain §4.2 langkah 4): jangan nyatakan "tidak ditemukan" hanya karena retrieval meleset.
                sapuan_selesai = True
                temuan = sapuan(db, item, ktx, llm)
                if temuan:
                    dok = elemen_urut(db, {e.id for e in dok} | {e.id for e in temuan})
                    continue
            bukti, salah_b = verifikasi(out.get("bukti", []), peta_dok, "bukti_dokumen")
            dasar, salah_p = verifikasi(out.get("dasar_panduan", []), peta_pdn, "dasar_panduan")
            if (salah_b or salah_p) and percobaan < 2:
                umpan_balik = "; ".join(salah_b + salah_p)
                log(logger, logging.WARNING, "rujukan tidak valid, nilai ulang", item=item.kode, jumlah=len(salah_b + salah_p))
                continue
            break
        ditemukan = bool(out.get("ditemukan", True))
        terpenuhi = bool(out.get("terpenuhi")) and ditemukan
        alasan = (out.get("alasan") or "").strip()
        yang_kurang = (out.get("yang_kurang") or "").strip() or None
        if not ditemukan:
            bukti = []
            alasan = alasan or "Tidak ditemukan di dokumen."
            yang_kurang = yang_kurang or "Bagian yang menjawab kriteria ini tidak ditemukan di dokumen."
        if terpenuhi and not bukti:
            # Memilih aman: tidak meloloskan item tanpa bukti yang dapat diverifikasi (desain §4.3).
            terpenuhi = False
            alasan = f"Bukti tidak dapat diverifikasi. {alasan}".strip()
            yang_kurang = yang_kurang or "Bukti pemenuhan tidak dapat diverifikasi pada dokumen."
        return {"item_id": item.item_id, "kode": item.kode, "terpenuhi": terpenuhi, "ditemukan": ditemukan, "alasan": alasan,
                "yang_kurang": None if terpenuhi else yang_kurang, "rujukan": bukti + dasar}


def sapuan(db: Session, item, ktx: Konteks, llm) -> list[Elemen]:
    """Pindai seluruh TOR per jendela ±8 halaman dengan pertanyaan pendek; kembalikan elemen bukti yang terverifikasi."""
    k = konfigurasi()
    jumlah = db.scalar(select(File.jumlah_halaman).where(File.id == ktx.tor_id)) or 0
    hasil: list[Elemen] = []
    for awal in range(1, jumlah + 1, k.jendela_sapuan_halaman):
        elemen = list(db.scalars(select(Elemen).where(Elemen.file_id == ktx.tor_id, Elemen.halaman >= awal,
                                                      Elemen.halaman < awal + k.jendela_sapuan_halaman)
                                 .order_by(Elemen.halaman, Elemen.urutan)))
        if not elemen:
            continue
        teks, peta, alias = format_konteks(elemen, "E", ktx)
        out = llm.json("sapuan", pr.prompt_sapuan(item, teks[:k.konteks_maks_karakter]), pr.skema_sapuan(list(peta)),
                       konteks={"kode": item.kode, "alias_dok": alias})
        if out.get("ada"):
            sah, _ = verifikasi(out.get("bukti", []), peta, "bukti_dokumen")
            hasil += [r.elemen for r in sah]
    return hasil


# ---------------------------------------------------------------- simpan
def simpan_rujukan(db: Session, review_id, pemilik_jenis: str, pemilik_id, rujukan: list[RujukanSah]) -> None:
    for i, r in enumerate(rujukan):
        db.add(Rujukan(review_id=review_id, pemilik_jenis=pemilik_jenis, pemilik_id=pemilik_id, elemen_id=r.elemen.id,
                       kutipan=r.kutipan, peran=r.peran, urutan=i))


def _progres(db: Session, review: Review, tahap_nama: str, persen: int) -> None:
    review.progres = {"tahap": tahap_nama, "persen": persen}
    db.commit()


# ---------------------------------------------------------------- orkestrasi
def kunci_acuan(db: Session, review: Review) -> None:
    """Kunci versi checklist, kategori, panduan saat review mulai diproses (desain §4.7)."""
    # Checklist review = isi pada review.mulai_at (diisi pemanggil), disusun ulang oleh app/checklist.py.
    ada_item = db.scalar(select(ChecklistItem.id).where(ChecklistItem.aktif).limit(1)) is not None
    review.kategori_versi_id = db.scalar(select(KategoriVersi.id).where(KategoriVersi.aktif))
    if not ada_item or review.kategori_versi_id is None:
        raise GalatPengguna("Checklist atau kategori aktif belum diatur oleh Admin.")
    # Per panduan berstatus Aktif: versi terbaru (terkini, lalu riwayat) yang filenya sudah SIAP.
    # Disalin ke review_panduan agar catatan tetap benar walau panduan diedit kemudian (D5).
    for pd in db.scalars(select(Panduan).where(Panduan.aktif)):
        pilih = next(((n, x) for n, x in pd.daftar_versi() if x.file.status_ekstraksi == "SIAP"), None)
        if pilih:
            nomor, x = pilih
            db.add(ReviewPanduan(review_id=review.id, panduan_id=pd.id, nomor=nomor, judul=x.panduan, file_id=x.file_id,
                                 nama_file=x.nama_file))
    review.model_info = info_model()


def jalankan_review(review_id, llm) -> None:
    """Jalankan (atau lanjutkan) review. Error apa pun → review & revisi GAGAL dengan pesan ramah + trace_id."""
    with SessionLokal() as db:
        review = db.get(Review, review_id)
        revisi = db.get(Revisi, review.revisi_id)
        set_konteks(trace_id=review.trace_id, review_id=review.id, revisi_id=revisi.id, usulan_id=revisi.usulan_id)
        if review.status in ("SELESAI", "GAGAL"):
            return
        try:
            with tahap(logger, "review"):
                _jalankan(db, review, revisi, llm)
        except Exception as e:
            db.rollback()
            review, revisi = db.get(Review, review_id), db.get(Revisi, review.revisi_id)
            pesan = str(e) if isinstance(e, GalatPengguna) else "Review AI gagal diproses."
            review.status, review.error_pesan = "GAGAL", f"{pesan} Silakan ajukan ulang. ID pelacakan: {review.trace_id}"
            review.selesai_at = datetime.now(timezone.utc)
            review.progres = {"tahap": "Gagal", "persen": 0}
            if revisi.status != st.GAGAL:
                st.pindah_status(revisi, st.GAGAL)
            db.commit()
            raise


def _jalankan(db: Session, review: Review, revisi: Revisi, llm) -> None:
    if review.status == "ANTRE":
        kunci_acuan(db, review)
        # Jam DATABASE, bukan jam worker: dibandingkan dengan update_date checklist (app/checklist.py).
        review.status, review.mulai_at = "DIPROSES", db.scalar(select(func.now()))
    if revisi.status != st.DIPROSES_AI:
        st.pindah_status(revisi, st.DIPROSES_AI)
    _progres(db, review, "Ekstraksi TOR", 5)
    proses_file(revisi.tor_file_id, llm)
    _progres(db, review, "Ekstraksi RAB", 15)
    proses_file(revisi.rab_file_id, llm)

    pv = db.scalars(select(ReviewPanduan).where(ReviewPanduan.review_id == review.id)).all()
    tor, rab = db.get(File, revisi.tor_file_id), db.get(File, revisi.rab_file_id)
    review.fingerprint = fingerprint(tor.sha256, rab.sha256, sidik_checklist(isi_review(db, review)), review.kategori_versi_id,
                                     [f"{v.panduan_id}:{v.nomor}" for v in pv], review.model_info)
    db.commit()
    asal = db.scalar(select(Review).where(Review.fingerprint == review.fingerprint, Review.status == "SELESAI",
                                          Review.id != review.id, Review.disalin_dari_id.is_(None))
                     .order_by(Review.selesai_at).limit(1))
    if asal is not None:
        _progres(db, review, "Menyalin hasil identik", 50)
        salin_hasil(db, asal, review)
    else:
        ktx = Konteks(tor_id=tor.id, rab_id=rab.id, panduan={v.file_id: f"{v.judul} (v{v.nomor})" for v in pv})
        screening_1(db, review, ktx, llm)
        keselarasan_dan_rekomendasi(db, review, ktx, llm)
        _progres(db, review, "Kategori", 92)
        screening_2(db, review, revisi, ktx, llm)

    hasil = db.scalars(select(HasilItem.terpenuhi).where(HasilItem.review_id == review.id)).all()
    review.label_ai = hitung_label(hasil)  # label oleh KODE (§7.1)
    db.flush()
    if pelanggaran := periksa_invarian(db, review.id):
        log(logger, logging.ERROR, "invarian rujukan gagal", pelanggaran=pelanggaran[:20])
        raise GalatInvarian("invarian rujukan gagal")
    review.status, review.selesai_at = "SELESAI", datetime.now(timezone.utc)
    review.progres = {"tahap": "Selesai", "persen": 100}
    st.pindah_status(revisi, st.MENUNGGU_VERIFIKASI)
    db.commit()
    log(logger, logging.INFO, "review selesai", label_ai=review.label_ai, disalin=asal is not None)


def screening_1(db: Session, review: Review, ktx: Konteks, llm) -> None:
    item = isi_review(db, review)
    sudah = set(db.scalars(select(HasilItem.checklist_item_id).where(HasilItem.review_id == review.id)))
    sisa = [i for i in item if i.item_id not in sudah]
    selesai = len(sudah)
    _progres(db, review, f"Menilai item {selesai}/{len(item)}", 20)
    with ThreadPoolExecutor(max_workers=konfigurasi().item_paralel) as pool:
        tugas = {pool.submit(nilai_item, i, ktx, llm): i for i in sisa}
        for t in as_completed(tugas):
            h = t.result()
            baris = HasilItem(review_id=review.id, checklist_item_id=h["item_id"], terpenuhi=h["terpenuhi"],
                              ditemukan=h["ditemukan"], alasan=h["alasan"], yang_kurang=h["yang_kurang"])
            db.add(baris)
            db.flush()
            simpan_rujukan(db, review.id, "hasil_item", baris.id, h["rujukan"])
            selesai += 1
            log(logger, logging.INFO, "item dinilai", item=h["kode"], terpenuhi=h["terpenuhi"], rujukan=len(h["rujukan"]))
            _progres(db, review, f"Menilai item {selesai}/{len(item)}", 20 + int(60 * selesai / max(1, len(item))))


def keselarasan_dan_rekomendasi(db: Session, review: Review, ktx: Konteks, llm) -> None:
    """Keselarasan RAB–TOR (tidak memengaruhi label) + rekomendasi TOR & RAB (keluaran #3, #4, E5)."""
    k = konfigurasi()
    db.execute(delete(Rujukan).where(Rujukan.review_id == review.id, Rujukan.pemilik_jenis == "rekomendasi"))
    db.execute(delete(Rekomendasi).where(Rekomendasi.review_id == review.id))
    _progres(db, review, "Keselarasan RAB–TOR", 82)
    rab = _seluruh_atau_cari(db, ktx.rab_id, "komponen biaya volume satuan harga", k.kandidat_dokumen)
    tor = cari(db, [ktx.tor_id], "kegiatan keluaran tahapan pelaksanaan volume jadwal rincian output", k.kandidat_dokumen)
    # Satu daftar alias untuk RAB lalu TOR; setiap baris konteks sudah menyebut dokumennya ("RAB hlm 3").
    teks, peta, alias = format_konteks(rab + tor, "E", ktx)
    out = llm.json("keselarasan", pr.prompt_keselarasan(teks), pr.skema_keselarasan(list(peta)), konteks={"alias_dok": alias})
    temuan = [(t, verifikasi(t.get("bukti", []), peta, "bukti_dokumen")[0]) for t in out.get("temuan", [])]

    _progres(db, review, "Rekomendasi", 86)
    item = {i.item_id: i for i in isi_review(db, review)}
    gagal = [(item[h.checklist_item_id], h) for h in db.scalars(select(HasilItem).where(HasilItem.review_id == review.id, ~HasilItem.terpenuhi))]
    nama_jenis = {"RAB_TANPA_DASAR_TOR": "Komponen RAB tanpa dasar di TOR", "TOR_TANPA_ANGGARAN": "Kegiatan TOR tanpa anggaran",
                  "TIDAK_SELARAS": "RAB tidak selaras dengan TOR"}
    for dokumen in ("TOR", "RAB"):
        urutan = 0
        relevan = [(i, h) for i, h in gagal if i.berlaku_untuk in (dokumen, "TOR & RAB")]
        if relevan:
            masalah = "\n".join(f"- [{i.kode}] {i.judul}: {h.yang_kurang or h.alasan}" for i, h in sorted(relevan, key=lambda x: x[0].urutan))
            pdn = cari(db, list(ktx.panduan), masalah, k.kandidat_panduan)
            teks_pdn, peta_pdn, alias_pdn = format_konteks(pdn, "P", ktx)
            kode = [i.kode for i, _ in relevan]
            hasil = llm.json("rekomendasi", pr.prompt_rekomendasi(dokumen, masalah, teks_pdn), pr.skema_rekomendasi(kode, list(peta_pdn)),
                             konteks={"kode_item": kode, "alias_panduan": alias_pdn}).get("rekomendasi", [])
            if not hasil:  # LLM kosong padahal ada masalah → rekomendasi minimal dari kekurangan item
                hasil = [{"teks": f"Perbaiki {i.judul}: {h.yang_kurang or h.alasan}", "kode_item": i.kode, "dasar_panduan": []} for i, h in relevan]
            per_kode = {i.kode: i.item_id for i, _ in relevan}
            for r in hasil:
                if not (r.get("teks") or "").strip():
                    continue
                urutan += 1
                rek = Rekomendasi(review_id=review.id, dokumen=dokumen, urutan=urutan, teks=r["teks"].strip(),
                                  checklist_item_id=per_kode.get(r.get("kode_item")))
                db.add(rek)
                db.flush()
                simpan_rujukan(db, review.id, "rekomendasi", rek.id, verifikasi(r.get("dasar_panduan", []), peta_pdn, "dasar_panduan")[0])
        if dokumen == "RAB":
            for t, bukti in temuan:
                urutan += 1
                rek = Rekomendasi(review_id=review.id, dokumen="RAB", urutan=urutan,
                                  teks=f"Keselarasan RAB–TOR ({nama_jenis.get(t.get('jenis'), 'Temuan')}): {t.get('uraian', '').strip()}")
                db.add(rek)
                db.flush()
                simpan_rujukan(db, review.id, "rekomendasi", rek.id, bukti)
        if urutan == 0:
            db.add(Rekomendasi(review_id=review.id, dokumen=dokumen, urutan=1, tidak_diperlukan=True,
                               teks=f"Tidak diperlukan perbaikan: seluruh item checklist untuk {dokumen} telah terpenuhi."))
    db.commit()


def screening_2(db: Session, review: Review, revisi: Revisi, ktx: Konteks, llm) -> None:
    """Rekomendasi kategori dari definisi versi kategori yang dikunci untuk review ini (C2). Kode dibatasi enum."""
    k = konfigurasi()
    db.execute(delete(Rujukan).where(Rujukan.review_id == review.id, Rujukan.pemilik_jenis == "hasil_kategori"))
    db.execute(delete(HasilKategori).where(HasilKategori.review_id == review.id))
    usulan = db.get(Usulan, revisi.usulan_id)
    kv = db.get(KategoriVersi, review.kategori_versi_id)
    definisi = "\n".join(f"- {i.kode} ({i.nama}): {i.definisi}" for i in kv.item)
    kueri = (f"{usulan.nama_ro} dasar hukum penetapan Menteri prioritas nasional sasaran strategis kementerian "
             f"tugas dan fungsi satker layanan esensial kebijakan penganggaran wajib")
    dok = cari(db, [ktx.tor_id], kueri, k.kandidat_dokumen)
    pdn = cari(db, list(ktx.panduan), kueri, k.kandidat_panduan)
    teks_dok, peta_dok, alias_dok = format_konteks(dok, "E", ktx)
    teks_pdn, peta_pdn, alias_pdn = format_konteks(pdn, "P", ktx)
    kode = [i.kode for i in kv.item]
    teks_dok = f"RO: {usulan.kode_ro} — {usulan.nama_ro}; Satker: {usulan.satker.nama}\n\n{teks_dok}"
    out = llm.json("kategori", pr.prompt_kategori(definisi, teks_dok, teks_pdn), pr.skema_kategori(kode, list(peta_dok), list(peta_pdn)),
                   konteks={"kode": kode, "alias_dok": alias_dok, "alias_panduan": alias_pdn})
    pilih = next((i for i in kv.item if i.kode == out.get("kode")), None)
    if pilih is None:
        raise GalatPengguna("AI tidak menghasilkan kategori yang valid.")
    hk = HasilKategori(review_id=review.id, kategori_item_id=pilih.id, alasan=(out.get("alasan") or "").strip())
    db.add(hk)
    db.flush()
    simpan_rujukan(db, review.id, "hasil_kategori", hk.id,
                   verifikasi(out.get("bukti", []), peta_dok, "bukti_dokumen")[0] + verifikasi(out.get("dasar_panduan", []), peta_pdn, "dasar_panduan")[0])
    db.commit()


def salin_hasil(db: Session, asal: Review, tujuan: Review) -> None:
    """Salin hasil AI dari review dengan fingerprint sama (hasil identik dijamin, desain §4.6)."""
    for model in (Rujukan, Rekomendasi, HasilKategori, HasilItem):
        db.execute(delete(model).where(model.review_id == tujuan.id))
    peta: dict = {}
    for h in db.scalars(select(HasilItem).where(HasilItem.review_id == asal.id)):
        baru = HasilItem(review_id=tujuan.id, checklist_item_id=h.checklist_item_id, terpenuhi=h.terpenuhi, ditemukan=h.ditemukan,
                         alasan=h.alasan, yang_kurang=h.yang_kurang)
        db.add(baru)
        db.flush()
        peta[h.id] = baru.id
    for r in db.scalars(select(Rekomendasi).where(Rekomendasi.review_id == asal.id)):
        baru = Rekomendasi(review_id=tujuan.id, dokumen=r.dokumen, urutan=r.urutan, teks=r.teks,
                           checklist_item_id=r.checklist_item_id, tidak_diperlukan=r.tidak_diperlukan)
        db.add(baru)
        db.flush()
        peta[r.id] = baru.id
    if hk := db.scalar(select(HasilKategori).where(HasilKategori.review_id == asal.id)):
        baru = HasilKategori(review_id=tujuan.id, kategori_item_id=hk.kategori_item_id, alasan=hk.alasan)
        db.add(baru)
        db.flush()
        peta[hk.id] = baru.id
    for r in db.scalars(select(Rujukan).where(Rujukan.review_id == asal.id)):
        db.add(Rujukan(review_id=tujuan.id, pemilik_jenis=r.pemilik_jenis, pemilik_id=peta[r.pemilik_id], elemen_id=r.elemen_id,
                       kutipan=r.kutipan, peran=r.peran, urutan=r.urutan))
    tujuan.disalin_dari_id = asal.id
    db.commit()
