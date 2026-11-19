"""Endpoint Dashboard + unduhan file berizin."""
import uuid
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app import status as st
from app.akses import ADMIN, PENGUSUL, REVIEWER, boleh_lihat_semua, boleh_lihat_usulan, pastikan, pengguna_saat_ini, wajib_role
from app.api.usulan import WIB, revisi_terbaru
from app.db import sesi_db
from app.galat import Galat
from app.keamanan import hash_token
from app.layanan_review import node_aktif
from app.model import (ChecklistItem, File, HasilItem, Job, Kategori, NodeAI, Override, Panduan, PanduanHistori, Pengguna, Review,
                       ReviewKategori, Revisi, Usulan)
from app.penyimpanan import path_absolut

router = APIRouter(prefix="/api", tags=["dashboard & file"])


def _saring(kueri, p: Pengguna, tahun: int | None):
    """Batas data Dashboard (kueri harus memuat tabel `usulan`): pengajuan yang tidak diarsipkan, Satker sendiri bagi Pengusul,
    dan Tahun Anggaran pilihan header bila dikirim (sama dengan daftar Pengajuan, desain.md §7 no. 75)."""
    kueri = kueri.where(Usulan.diarsipkan_at.is_(None))
    if not boleh_lihat_semua(p):
        kueri = kueri.where(Usulan.satker_id == p.satker_id)
    return kueri if tahun is None else kueri.where(Usulan.tahun_anggaran == tahun)


def _kategori_lolos(db: Session, p: Pengguna, tahun: int | None) -> list[dict]:
    """Jumlah pengajuan yang difinalkan Lolos oleh verifikator per kategori final (nama dari salinan kategori review). Semua
    kategori Aktif tetap tampil walau 0; kategori Nonaktif/terhapus hanya bila punya data."""
    lolos = {kode: (nama, n) for kode, nama, n in db.execute(_saring(
        select(ReviewKategori.kode, func.max(ReviewKategori.nama), func.count())
        .join(Review, (Review.id == ReviewKategori.review_id) & (Review.kategori_final_id == ReviewKategori.kategori_id))
        .join(Revisi, Revisi.id == Review.revisi_id).join(Usulan, Usulan.id == Revisi.usulan_id)
        .where(Review.difinalkan_at.is_not(None), Revisi.status == st.LOLOS), p, tahun).group_by(ReviewKategori.kode))}
    daftar = [{"kode": k.kode, "nama": k.kategori, "jumlah": lolos.pop(k.kode, (None, 0))[1]}
              for k in db.scalars(select(Kategori).order_by(Kategori.no_urut)) if k.aktif or k.kode in lolos]
    return daftar + [{"kode": kode, "nama": nama, "jumlah": n} for kode, (nama, n) in sorted(lolos.items())]


def _checklist_tidak_lolos(db: Session, p: Pengguna, tahun: int | None) -> list[dict]:
    """Item checklist yang tidak lolos per AI dan per verifikator, dihitung per pemeriksaan (review terakhir yang selesai di
    tiap revisi, termasuk revisi lama). Verifikator = nilai final review yang sudah difinalkan (override ITEM aktif terakhir,
    selain itu hasil AI — sama dengan app/nilai_final.py). Dari yang tidak lolos verifikator: "sudah diperbaiki" bila
    pengajuan itu sudah punya revisi berikutnya (perbaikan diunggah), selain itu "belum". Item yang dihapus permanen tidak tampil."""
    rv = _saring(select(Review.id, Review.difinalkan_at, Revisi.nomor, Revisi.usulan_id)
                 .join(Revisi, Revisi.id == Review.revisi_id).join(Usulan, Usulan.id == Revisi.usulan_id)
                 .where(Review.status == "SELESAI").distinct(Review.revisi_id)
                 .order_by(Review.revisi_id, Review.created_at.desc()), p, tahun).subquery()
    akhir = (select(Override.review_id, Override.checklist_item_id, Override.nilai_sesudah)
             .where(Override.target == "ITEM", Override.dibatalkan_at.is_(None))
             .distinct(Override.review_id, Override.checklist_item_id)
             .order_by(Override.review_id, Override.checklist_item_id, Override.created_at.desc())).subquery()
    lanjut = aliased(Revisi)
    item = (select(HasilItem.checklist_item_id, (~HasilItem.terpenuhi).label("ai"),
                   (rv.c.difinalkan_at.is_not(None) & ~func.coalesce(akhir.c.nilai_sesudah == "TERPENUHI", HasilItem.terpenuhi)).label("v"),
                   exists().where(lanjut.usulan_id == rv.c.usulan_id, lanjut.nomor > rv.c.nomor).label("diperbaiki"))
            .join(rv, rv.c.id == HasilItem.review_id)
            .outerjoin(akhir, (akhir.c.review_id == HasilItem.review_id) & (akhir.c.checklist_item_id == HasilItem.checklist_item_id))
            ).subquery()
    ai, v = func.count().filter(item.c.ai), func.count().filter(item.c.v)
    baris = db.execute(select(ChecklistItem.kode, ChecklistItem.checklist, ai, v, func.count().filter(item.c.v & item.c.diperbaiki))
                       .join(item, item.c.checklist_item_id == ChecklistItem.id).group_by(ChecklistItem.id)
                       .having(func.count().filter(item.c.ai | item.c.v) > 0).order_by(v.desc(), ai.desc(), ChecklistItem.no_urut)).all()
    return [{"kode": k, "checklist": c, "ai": a, "verifikator": n, "sudah_diperbaiki": d, "belum_diperbaiki": n - d} for k, c, a, n, d in baris]


@router.get("/dashboard")
def dashboard(tahun: int | None = None, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(PENGUSUL, REVIEWER))) -> dict:
    """Ringkasan pengajuan (Dashboard hanya informasi, tanpa daftar tindakan). `tahun` = Tahun Anggaran pilihan header (tanpa =
    semua tahun). Semua: jumlah per status; Reviewer: per Satker; Pengusul: pengajuan Lolos per kategori (`kategori_lolos`) dan
    checklist yang tidak lolos (`checklist_tidak_lolos`), desain.md §7 no. 75. Pengusul & Reviewer saja (Admin tidak memiliki
    menu Dashboard → 403). Pengguna yang juga ber-role Admin melihat antrean AI, node aktif, dan perkiraan waktu selesai (desain §2.3)."""
    dasar = select(Usulan, Revisi).join(Revisi, (Revisi.usulan_id == Usulan.id) & (Revisi.nomor == revisi_terbaru()))
    baris = db.execute(_saring(dasar, p, tahun)).all()

    per_status: dict[str, int] = {}
    per_satker: dict[str, dict] = {}
    for u, r in baris:
        per_status[r.status] = per_status.get(r.status, 0) + 1
        s = per_satker.setdefault(str(u.satker_id), {"satker": u.satker.nama, "total": 0, "lolos": 0, "tidak_lolos": 0, "menunggu": 0})
        s["total"] += 1
        s["lolos"] += r.status == st.LOLOS
        s["tidak_lolos"] += r.status == st.TIDAK_LOLOS
        s["menunggu"] += r.status == st.MENUNGGU_VERIFIKASI  # sama dengan kartu Menunggu Verifikasi (draf/antre/gagal tidak dihitung)

    data = {"total": len(baris), "per_status": per_status}
    if boleh_lihat_semua(p):
        data["per_satker"] = sorted(per_satker.values(), key=lambda s: s["satker"])
    else:
        data["kategori_lolos"] = _kategori_lolos(db, p, tahun)
        data["checklist_tidak_lolos"] = _checklist_tidak_lolos(db, p, tahun)

    if ADMIN in p.daftar_role:
        aktif = node_aktif(db)
        antre = db.scalar(select(func.count()).select_from(Job).where(Job.status == "ANTRE", Job.jenis == "REVIEW"))
        diproses = db.scalar(select(func.count()).select_from(Job).where(Job.status == "DIPROSES", Job.jenis == "REVIEW"))
        durasi = db.scalars(select(func.extract("epoch", Review.selesai_at - Review.mulai_at))
                            .where(Review.status == "SELESAI", Review.disalin_dari_id.is_(None), Review.mulai_at.is_not(None))
                            .order_by(Review.selesai_at.desc()).limit(20)).all()
        rata = float(sum(durasi) / len(durasi)) / 60 if durasi else None
        data["antrean"] = {
            "antre": antre, "diproses": diproses, "rata_menit_per_review": round(rata, 1) if rata else None,
            "perkiraan_selesai_menit": round((antre + diproses) * rata / len(aktif)) if rata and aktif else None,
            "node": [{"nama": n.nama, "terakhir_terlihat": n.terakhir_terlihat.isoformat(), "info": n.info} for n in aktif],
        }
    return data


# Grafik "Jumlah Pengajuan": satuan date_trunc PostgreSQL & banyak periode terakhir yang ditampilkan per pilihan.
PERIODE = {"hari": ("day", 30), "minggu": ("week", 12), "bulan": ("month", 12), "tahun": ("year", 5)}


def _awal_periode(d: date, per: str) -> date:
    """Awal periode yang memuat `d`; minggu dimulai Senin (sama dengan date_trunc('week'))."""
    return {"hari": d, "minggu": d - timedelta(days=d.weekday()), "bulan": d.replace(day=1), "tahun": date(d.year, 1, 1)}[per]


def _mundur(awal: date, per: str, n: int) -> date:
    """Awal periode ke-`n` sebelum periode `awal`."""
    if per == "hari":
        return awal - timedelta(days=n)
    if per == "minggu":
        return awal - timedelta(weeks=n)
    if per == "bulan":
        b = awal.year * 12 + awal.month - 1 - n
        return date(b // 12, b % 12 + 1, 1)
    return date(awal.year - n, 1, 1)


@router.get("/dashboard/tren")
def tren(per: Literal["hari", "minggu", "bulan", "tahun"] = "bulan", tahun: int | None = None, db: Session = Depends(sesi_db),
         p: Pengguna = Depends(wajib_role(PENGUSUL, REVIEWER))) -> dict:
    """Grafik Dashboard: jumlah pengajuan baru (tanggal pengajuan dibuat, WIB) per hari (30 terakhir), minggu (12, mulai
    Senin), bulan (12), atau tahun (5). Periode tanpa pengajuan bernilai 0. Pengusul hanya Satker-nya (sama dengan kartu
    Dashboard), `tahun` = hanya pengajuan Tahun Anggaran itu. Output: {per, data: [{mulai: YYYY-MM-DD, jumlah}]} urut lama → baru.
    Error: 422 `per` tidak dikenal."""
    satuan, banyak = PERIODE[per]
    kini = _awal_periode(datetime.now(WIB).date(), per)
    daftar = [_mundur(kini, per, i) for i in range(banyak - 1, -1, -1)]
    lokal = func.timezone("Asia/Jakarta", Usulan.created_date)
    kunci = func.date(func.date_trunc(satuan, lokal))
    jumlah = dict(db.execute(_saring(select(kunci, func.count()).where(lokal >= daftar[0]), p, tahun).group_by(kunci)).all())
    return {"per": per, "data": [{"mulai": d.isoformat(), "jumlah": jumlah.get(d, 0)} for d in daftar]}


@router.get("/file/{file_id}")
def unduh(file_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> FileResponse:
    """Unduh/tampilkan PDF dengan pemeriksaan hak akses (bukan URL statis).

    Boleh bila: file panduan bagi Reviewer & Pengusul (sama dengan hak baca GET /api/panduan; Admin tidak memiliki
    menu Panduan), atau TOR/RAB dari usulan yang boleh dilihat pengguna.
    Error: 404 bila tidak ada atau tidak berhak (tidak membocorkan keberadaan file).
    """
    f = db.get(File, file_id)
    if f is None:
        raise Galat(404, "File tidak ditemukan.")
    boleh = bool(p.daftar_role & {REVIEWER, PENGUSUL}) and any(
        db.scalar(select(kolom).where(kolom == f.id).limit(1)) for kolom in (Panduan.file_id, PanduanHistori.file_id))
    if not boleh:
        for u in db.scalars(select(Usulan).join(Revisi, Revisi.usulan_id == Usulan.id)
                            .where(or_(Revisi.tor_file_id == f.id, Revisi.rab_file_id == f.id)).distinct()):
            if boleh_lihat_usulan(p, u):
                boleh = True
                break
    if not boleh:
        raise Galat(404, "File tidak ditemukan.")
    return FileResponse(path_absolut(f), media_type="application/pdf", filename=f.nama_asli,
                        content_disposition_type="inline", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/internal/file/{sha}")
def unduh_internal(sha: str, authorization: str = Header(""), db: Session = Depends(sesi_db)) -> FileResponse:
    """Dipakai node AI jarak jauh (GPU sewaan) untuk mengambil PDF saat job berjalan (desain §2.4).
    Otorisasi: `Authorization: Bearer <token node>`; node yang dicabut ditolak."""
    token = authorization.removeprefix("Bearer ").strip()
    node = db.scalar(select(NodeAI).where(NodeAI.token_hash == hash_token(token), NodeAI.aktif)) if token else None
    pastikan(node is not None, "Token node tidak valid.")
    f = db.scalar(select(File).where(File.sha256 == sha))
    if f is None:
        raise Galat(404, "File tidak ditemukan.")
    return FileResponse(path_absolut(f), media_type="application/pdf")
