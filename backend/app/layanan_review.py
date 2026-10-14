"""Logika layanan review yang dipakai beberapa endpoint: pengajuan, antrean, tampilan hasil.

Aturan visibilitas (PRD §5): Pengusul melihat hasil AI segera setelah AI selesai (ditandai
"belum diverifikasi"); override & catatan reviewer baru terlihat setelah difinalkan.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import status as st
from app.akses import boleh_kelola_usulan, boleh_lihat_semua, pastikan
from app.audit import catat
from app.galat import Galat
from app.model import (CatatanReviewer, ChecklistItem, ChecklistVersi, Elemen, HasilItem, HasilKategori, Job,
                       KategoriItem, KategoriVersi, NodeAI, Override, PanduanVersi, Pengguna, Rekomendasi, Review,
                       PanduanKoleksiVersi, ReviewPanduan, Revisi, Rujukan, Usulan)
from app.nilai_final import NilaiFinal, hitung_nilai_final
from app.pekerja.rujukan import nomor_kalimat

NODE_AKTIF_DETIK = 90


def review_terbaru(db: Session, revisi_id) -> Review | None:
    return db.scalar(select(Review).where(Review.revisi_id == revisi_id).order_by(Review.created_at.desc()).limit(1))


def ajukan_review(db: Session, request: Request | None, revisi: Revisi, p: Pengguna) -> Review:
    """Pengusul menekan "Ajukan Review": revisi → ANTRE, buat review + job antrean.

    Versi checklist/kategori/panduan dikunci saat job mulai diproses (desain §4.7).
    Error: 403 bukan Pengusul Satker ini; 409 status tidak mengizinkan; 400 checklist/kategori belum ada.
    """
    usulan = db.get(Usulan, revisi.usulan_id)
    pastikan(boleh_kelola_usulan(p, usulan), "Hanya Pengusul dari Satker ini yang dapat mengajukan review.")
    if usulan.diarsipkan_at:
        raise Galat(409, "Usulan diarsipkan.")
    if revisi.status not in st.BOLEH_AJUKAN:
        raise Galat(409, "Revisi ini sudah diajukan. Review AI hanya dijalankan sekali per revisi.")
    versi = db.scalar(select(ChecklistVersi).where(ChecklistVersi.aktif))
    if versi is None or not versi.item:
        raise Galat(400, "Checklist belum diatur oleh Admin. Review belum dapat diajukan.")
    if db.scalar(select(KategoriVersi.id).where(KategoriVersi.aktif)) is None:
        raise Galat(400, "Kategori belum diatur oleh Admin.")
    st.pindah_status(revisi, st.ANTRE)
    trace_id = uuid.uuid4().hex
    review = Review(revisi_id=revisi.id, trace_id=trace_id, status="ANTRE", diajukan_oleh=p.id,
                    progres={"tahap": "Antre", "persen": 0})
    db.add(review)
    db.flush()
    db.add(Job(jenis="REVIEW", ref_id=review.id, trace_id=trace_id))
    catat(db, request, "AJUKAN_REVIEW", "revisi", revisi.id, sesudah={"review_id": str(review.id), "trace_id": trace_id})
    return review


def node_aktif(db: Session) -> list[NodeAI]:
    batas = datetime.now(timezone.utc) - timedelta(seconds=NODE_AKTIF_DETIK)
    return list(db.scalars(select(NodeAI).where(NodeAI.aktif, NodeAI.terakhir_terlihat > batas)))


def posisi_antrean(db: Session, review_id) -> int | None:
    """Posisi job dalam antrean FIFO (1 = berikutnya), None bila tidak sedang antre."""
    job = db.scalar(select(Job).where(Job.ref_id == review_id, Job.jenis == "REVIEW", Job.status == "ANTRE"))
    if job is None:
        return None
    return db.scalar(select(func.count()).select_from(Job).where(Job.status == "ANTRE", Job.created_at <= job.created_at))


def info_proses(db: Session, review: Review | None) -> dict | None:
    """Progres review yang sedang berjalan untuk ditampilkan (polling 5 detik)."""
    if review is None:
        return None
    data = {"review_id": str(review.id), "status": review.status, "progres": review.progres,
            "trace_id": review.trace_id, "error_pesan": review.error_pesan}
    if review.status == "ANTRE":
        data["posisi_antrean"] = posisi_antrean(db, review.id)
        data["menunggu_kapasitas"] = not node_aktif(db)
    return data


def nilai_final_review(db: Session, review: Review, sertakan_override: bool) -> tuple[NilaiFinal, list[Override]]:
    """Nilai final untuk ditampilkan. `sertakan_override=False` → nilai AI murni (tampilan Pengusul sebelum final)."""
    hasil = db.scalars(select(HasilItem).where(HasilItem.review_id == review.id)).all()
    kat = db.scalar(select(HasilKategori).where(HasilKategori.review_id == review.id))
    overrides = list(db.scalars(select(Override).where(Override.review_id == review.id).order_by(Override.created_at))) \
        if sertakan_override else []
    nf = hitung_nilai_final({str(h.checklist_item_id): h.terpenuhi for h in hasil},
                            str(kat.kategori_item_id) if kat else None, overrides)
    if review.difinalkan_at:  # snapshot terkunci menang
        nf.label = review.label_final
        nf.kategori_id = str(review.kategori_final_id) if review.kategori_final_id else nf.kategori_id
    return nf, overrides


def lihat_sebagai_reviewer(p: Pengguna) -> bool:
    return boleh_lihat_semua(p)


def ringkasan_checklist(db: Session, review: Review | None, p: Pengguna) -> dict | None:
    """Ringkasan "8/10 terpenuhi" + rincian per item untuk tabel usulan (A4)."""
    if review is None or review.status != "SELESAI":
        return None
    nf, _ = nilai_final_review(db, review, lihat_sebagai_reviewer(p) or review.difinalkan_at is not None)
    item = db.scalars(select(ChecklistItem).where(ChecklistItem.versi_id == review.checklist_versi_id)
                      .order_by(ChecklistItem.urutan)).all()
    rincian = [{"kode": i.kode, "judul": i.judul, "terpenuhi": nf.item.get(str(i.id), False)} for i in item]
    return {"terpenuhi": sum(r["terpenuhi"] for r in rincian), "total": len(rincian), "item": rincian,
            "label": nf.label, "final": review.difinalkan_at is not None}


def _kategori_ringkas(k: KategoriItem | None) -> dict | None:
    return {"id": str(k.id), "kode": k.kode, "nama": k.nama, "diteruskan": k.diteruskan} if k else None


def _nama(db: Session, pengguna_id) -> str | None:
    if pengguna_id is None:
        return None
    p = db.get(Pengguna, pengguna_id)
    return p.nama if p else None


def _override_dict(db: Session, o: Override) -> dict:
    return {"id": str(o.id), "target": o.target, "checklist_item_id": str(o.checklist_item_id) if o.checklist_item_id else None,
            "nilai_sebelum": o.nilai_sebelum, "nilai_sesudah": o.nilai_sesudah, "alasan": o.alasan,
            "oleh": _nama(db, o.oleh), "at": o.created_at.isoformat(),
            "dibatalkan_at": o.dibatalkan_at.isoformat() if o.dibatalkan_at else None,
            "dibatalkan_oleh": _nama(db, o.dibatalkan_oleh)}


def _rujukan(db: Session, review: Review, revisi: Revisi, pemilik_ids: list) -> dict[str, list[dict]]:
    """Rujukan per pemilik; file, halaman, lokasi, bbox SELALU dari tabel elemen (E3)."""
    if not pemilik_ids:
        return {}
    baris = db.execute(select(Rujukan, Elemen).join(Elemen, Elemen.id == Rujukan.elemen_id)
                       .where(Rujukan.review_id == review.id, Rujukan.pemilik_id.in_(pemilik_ids))
                       .order_by(Rujukan.urutan)).all()
    panduan = {pv.file_id: pv for pv in db.scalars(
        select(PanduanVersi).join(ReviewPanduan, ReviewPanduan.panduan_versi_id == PanduanVersi.id)
        .where(ReviewPanduan.review_id == review.id))}
    hasil: dict[str, list[dict]] = {}
    for r, e in baris:
        if e.file_id == revisi.tor_file_id:
            dokumen, judul = "TOR", revisi.tor_nama
        elif e.file_id == revisi.rab_file_id:
            dokumen, judul = "RAB", revisi.rab_nama
        else:
            pv = panduan.get(e.file_id)
            dokumen, judul = "PANDUAN", (f"{pv.judul} (v{pv.nomor})" if pv else "Panduan")
        kalimat = nomor_kalimat(e.teks, r.kutipan)
        hasil.setdefault(str(r.pemilik_id), []).append({
            "id": str(r.id), "peran": r.peran, "dokumen": dokumen, "judul_dokumen": judul, "file_id": str(e.file_id),
            "halaman": e.halaman, "label_lokasi": e.label_lokasi + (f", kalimat {kalimat}" if kalimat else ""),
            "kutipan": r.kutipan, "bbox": e.bbox,
            "sumber": e.sumber, "jenis": e.jenis,
        })
    return hasil


def detail_review(db: Session, review: Review, p: Pengguna) -> dict:
    """Seluruh data halaman Detail Review, disesuaikan dengan role yang melihat."""
    revisi = db.get(Revisi, review.revisi_id)
    usulan = db.get(Usulan, revisi.usulan_id)
    sebagai_reviewer = lihat_sebagai_reviewer(p)
    final = review.difinalkan_at is not None
    data = {
        "id": str(review.id), "status": review.status, "trace_id": review.trace_id,
        "tampilan": "reviewer" if sebagai_reviewer else "pengusul", "final": final,
        "difinalkan_oleh": _nama(db, review.difinalkan_oleh),
        "difinalkan_at": review.difinalkan_at.isoformat() if review.difinalkan_at else None,
        "selesai_at": review.selesai_at.isoformat() if review.selesai_at else None,
        "model_info": review.model_info, "proses": info_proses(db, review),
        "usulan": {"id": str(usulan.id), "satker": usulan.satker.nama, "tahun_anggaran": usulan.tahun_anggaran,
                   "kode_ro": usulan.kode_ro, "nama_ro": usulan.nama_ro, "diarsipkan": usulan.diarsipkan_at is not None},
        "revisi": {"id": str(revisi.id), "nomor": revisi.nomor, "status": revisi.status,
                   "tor": {"file_id": str(revisi.tor_file_id), "nama": revisi.tor_nama},
                   "rab": {"file_id": str(revisi.rab_file_id), "nama": revisi.rab_nama}},
        "boleh_override": "REVIEWER" in p.daftar_role and not final and revisi.status == st.MENUNGGU_VERIFIKASI,
    }
    if review.disalin_dari_id:
        asal = db.get(Review, review.disalin_dari_id)
        data["disalin_dari_revisi"] = db.get(Revisi, asal.revisi_id).nomor if asal else None
    if review.status != "SELESAI":
        return data

    tampil_override = sebagai_reviewer or final
    nf, overrides = nilai_final_review(db, review, tampil_override)
    aktif_per_target = {}
    for o in overrides:
        if o.dibatalkan_at is None:
            aktif_per_target[(o.target, str(o.checklist_item_id) if o.checklist_item_id else None)] = o

    cv = db.get(ChecklistVersi, review.checklist_versi_id)
    kv = db.get(KategoriVersi, review.kategori_versi_id)
    pk = db.get(PanduanKoleksiVersi, review.panduan_koleksi_versi_id) if review.panduan_koleksi_versi_id else None
    panduan = db.scalars(select(PanduanVersi).join(ReviewPanduan, ReviewPanduan.panduan_versi_id == PanduanVersi.id)
                         .where(ReviewPanduan.review_id == review.id).order_by(PanduanVersi.judul)).all()
    data["acuan"] = {
        "checklist_versi": {"id": str(cv.id), "nomor": cv.nomor},
        "kategori_versi": {"id": str(kv.id), "nomor": kv.nomor},
        "panduan_versi": {"id": str(pk.id), "nomor": pk.nomor} if pk else None,
        "panduan": [{"judul": pv.judul, "nomor": pv.nomor, "file_id": str(pv.file_id), "nama_file": pv.nama_file} for pv in panduan],
    }

    hasil = {h.checklist_item_id: h for h in db.scalars(select(HasilItem).where(HasilItem.review_id == review.id))}
    rek = db.scalars(select(Rekomendasi).where(Rekomendasi.review_id == review.id).order_by(Rekomendasi.dokumen, Rekomendasi.urutan)).all()
    kat = db.scalar(select(HasilKategori).where(HasilKategori.review_id == review.id))
    rujukan = _rujukan(db, review, revisi, [h.id for h in hasil.values()] + [r.id for r in rek] + ([kat.id] if kat else []))

    item = []
    for ci in cv.item:
        h = hasil.get(ci.id)
        if h is None:
            continue
        o = aktif_per_target.get(("ITEM", str(ci.id)))
        item.append({
            "id": str(ci.id), "kode": ci.kode, "judul": ci.judul, "kriteria": ci.kriteria, "berlaku_untuk": ci.berlaku_untuk,
            "ai_terpenuhi": h.terpenuhi, "terpenuhi": nf.item.get(str(ci.id), h.terpenuhi), "diubah": str(ci.id) in nf.item_diubah,
            "override": _override_dict(db, o) if o else None, "ditemukan": h.ditemukan, "alasan": h.alasan,
            "yang_kurang": h.yang_kurang, "rujukan": rujukan.get(str(h.id), []),
        })
    data["item"] = item
    data["label"] = {"ai": review.label_ai, "hitung": nf.label_hitung, "final": nf.label, "diubah": nf.label_diubah,
                     "tidak_konsisten": nf.label_tidak_konsisten, "terpenuhi": nf.jumlah_terpenuhi, "total": len(item),
                     "override": _override_dict(db, o) if (o := aktif_per_target.get(("LABEL", None))) else None}
    kat_ai = db.get(KategoriItem, kat.kategori_item_id) if kat else None
    kat_final = db.get(KategoriItem, uuid.UUID(nf.kategori_id)) if nf.kategori_id else None
    data["kategori"] = {"ai": _kategori_ringkas(kat_ai), "final": _kategori_ringkas(kat_final), "diubah": nf.kategori_diubah,
                        "alasan": kat.alasan if kat else None, "rujukan": rujukan.get(str(kat.id), []) if kat else [],
                        "override": _override_dict(db, o) if (o := aktif_per_target.get(("KATEGORI", None))) else None,
                        "pilihan": [_kategori_ringkas(k) for k in kv.item]}
    kode_item = {ci.id: ci.kode for ci in cv.item}
    data["rekomendasi"] = {d: [{"id": str(r.id), "teks": r.teks, "tidak_diperlukan": r.tidak_diperlukan,
                                "item_kode": kode_item.get(r.checklist_item_id), "rujukan": rujukan.get(str(r.id), [])}
                               for r in rek if r.dokumen == d] for d in ("TOR", "RAB")}
    if tampil_override:
        catatan = db.scalars(select(CatatanReviewer).where(CatatanReviewer.review_id == review.id)).all()
        data["catatan"] = [{"dokumen": c.dokumen, "teks": c.teks, "oleh": _nama(db, c.oleh), "diubah_at": c.diubah_at.isoformat()} for c in catatan]
        data["riwayat_override"] = [_override_dict(db, o) for o in overrides]
    else:
        data["catatan"], data["riwayat_override"] = [], []
    return data
