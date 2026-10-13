"""Endpoint Modul A — usulan, revisi, pengajuan review, riwayat."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File as FormFile, Form, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app import status as st
from app.akses import (PENGUSUL, boleh_kelola_usulan, boleh_lihat_semua, boleh_lihat_usulan, pastikan,
                       pengguna_saat_ini, wajib_role)
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.layanan_review import ajukan_review, info_proses, nilai_final_review, review_terbaru, ringkasan_checklist
from app.model import ChecklistItem, KategoriItem, Pengguna, Review, Revisi, Satker, Usulan
from app.penyimpanan import simpan_unggahan

router = APIRouter(prefix="/api/usulan", tags=["usulan"])


def revisi_terbaru():
    """Subquery nomor revisi terbaru per usulan (alias agar tidak ter-korelasi dengan join Revisi utama)."""
    r2 = aliased(Revisi)
    return select(func.max(r2.nomor)).where(r2.usulan_id == Usulan.id).scalar_subquery()


def _ambil(db: Session, usulan_id: uuid.UUID, p: Pengguna) -> Usulan:
    u = db.get(Usulan, usulan_id)
    if u is None:
        raise Galat(404, "Usulan tidak ditemukan.")
    pastikan(boleh_lihat_usulan(p, u))
    return u


def baris_usulan(db: Session, u: Usulan, p: Pengguna) -> dict:
    """Satu baris tabel daftar usulan (A2–A4). Status = status revisi terbaru."""
    r = u.revisi[-1]
    rv = review_terbaru(db, r.id)
    kategori = None
    if rv is not None and rv.status == "SELESAI" and rv.difinalkan_at:
        k = db.get(KategoriItem, rv.kategori_final_id) if rv.kategori_final_id else None
        kategori = {"kode": k.kode, "nama": k.nama, "diteruskan": k.diteruskan} if k else None
    pernah_direview = db.scalar(select(exists().where(Review.revisi_id.in_([x.id for x in u.revisi])))) or False
    return {
        "id": str(u.id), "satker": {"id": str(u.satker.id), "kode": u.satker.kode, "nama": u.satker.nama},
        "tahun_anggaran": u.tahun_anggaran, "kode_ro": u.kode_ro, "nama_ro": u.nama_ro,
        "revisi_id": str(r.id), "revisi_nomor": r.nomor, "status": r.status,
        "tor": {"file_id": str(r.tor_file_id), "nama": r.tor_nama}, "rab": {"file_id": str(r.rab_file_id), "nama": r.rab_nama},
        "kategori_final": kategori, "updated_at": max(u.updated_at, r.updated_at).isoformat(),
        "diarsipkan": u.diarsipkan_at is not None, "pernah_direview": pernah_direview,
        "review_id": str(rv.id) if rv else None, "checklist": ringkasan_checklist(db, rv, p),
        "proses": info_proses(db, rv) if r.status in (st.ANTRE, st.DIPROSES_AI, st.GAGAL) else None,
        "boleh_kelola": boleh_kelola_usulan(p, u),
    }


@router.get("")
def daftar(db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini),
           satker_id: uuid.UUID | None = None, tahun: int | None = None, status: str | None = None,
           kategori: str | None = None, q: str | None = None, arsip: bool = False,
           halaman: int = Query(1, ge=1), per_halaman: int = Query(25, ge=1, le=100)) -> dict:
    """Daftar usulan dengan filter A5. Pengusul otomatis dibatasi ke Satker-nya."""
    kueri = select(Usulan).join(Revisi, (Revisi.usulan_id == Usulan.id) & (Revisi.nomor == revisi_terbaru()))
    if not boleh_lihat_semua(p):
        kueri = kueri.where(Usulan.satker_id == p.satker_id)
    if satker_id:
        kueri = kueri.where(Usulan.satker_id == satker_id)
    if tahun:
        kueri = kueri.where(Usulan.tahun_anggaran == tahun)
    if status:
        kueri = kueri.where(Revisi.status == status)
    if kategori:
        kueri = kueri.where(exists().where(Review.revisi_id == Revisi.id, Review.difinalkan_at.is_not(None),
                                           Review.kategori_final_id == KategoriItem.id, KategoriItem.kode == kategori))
    if q:
        pola = f"%{q.strip()}%"
        kueri = kueri.where(or_(Usulan.kode_ro.ilike(pola), Usulan.nama_ro.ilike(pola)))
    kueri = kueri.where(Usulan.diarsipkan_at.is_not(None) if arsip else Usulan.diarsipkan_at.is_(None))
    total = db.scalar(select(func.count()).select_from(kueri.subquery()))
    baris = db.scalars(kueri.order_by(Revisi.updated_at.desc()).offset((halaman - 1) * per_halaman).limit(per_halaman)).unique().all()
    return {"total": total, "halaman": halaman, "per_halaman": per_halaman, "data": [baris_usulan(db, u, p) for u in baris]}


@router.post("")
def buat(request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(PENGUSUL)),
         tahun_anggaran: int = Form(...), kode_ro: str = Form(...), nama_ro: str = Form(...),
         tor: UploadFile = FormFile(...), rab: UploadFile = FormFile(...), ajukan: bool = Form(False)) -> dict:
    """Buat usulan baru (A1) — Satker = Satker pengusul. `ajukan=true` langsung mengajukan review.

    Error: 400 bila akun belum punya Satker / data tidak lengkap / file bukan PDF; 413 file terlalu besar.
    """
    if p.satker_id is None:
        raise Galat(400, "Akun Anda belum terhubung ke Satker. Hubungi Admin.")
    if not (2000 <= tahun_anggaran <= 2100) or not kode_ro.strip() or not nama_ro.strip():
        raise Galat(400, "Tahun anggaran, kode RO, dan nama RO wajib diisi dengan benar.")
    f_tor, n_tor = simpan_unggahan(db, tor)
    f_rab, n_rab = simpan_unggahan(db, rab)
    u = Usulan(satker_id=p.satker_id, tahun_anggaran=tahun_anggaran, kode_ro=kode_ro.strip(), nama_ro=nama_ro.strip(), dibuat_oleh=p.id)
    db.add(u)
    db.flush()
    r = Revisi(usulan_id=u.id, nomor=1, tor_file_id=f_tor.id, tor_nama=n_tor, rab_file_id=f_rab.id, rab_nama=n_rab,
               status=st.DRAF, dibuat_oleh=p.id)
    db.add(r)
    db.flush()
    catat(db, request, "BUAT_USULAN", "usulan", u.id, sesudah={"kode_ro": u.kode_ro, "tahun": tahun_anggaran, "tor": n_tor, "rab": n_rab})
    if ajukan:
        ajukan_review(db, request, r, p)
    db.commit()
    db.refresh(u)
    return baris_usulan(db, u, p)


@router.get("/{usulan_id}")
def detail(usulan_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    return baris_usulan(db, _ambil(db, usulan_id, p), p)


@router.put("/{usulan_id}/draf")
def ubah_draf(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
              p: Pengguna = Depends(wajib_role(PENGUSUL)), tahun_anggaran: int | None = Form(None),
              kode_ro: str | None = Form(None), nama_ro: str | None = Form(None),
              tor: UploadFile | None = FormFile(None), rab: UploadFile | None = FormFile(None), ajukan: bool = Form(False)) -> dict:
    """Ubah data/dokumen revisi terbaru selama masih DRAF atau GAGAL (belum ada hasil AI).

    Error: 409 bila revisi sedang/sudah direview (dokumen terkunci, PRD §5).
    """
    u = _ambil(db, usulan_id, p)
    pastikan(boleh_kelola_usulan(p, u))
    r = u.revisi[-1]
    if r.status not in st.BOLEH_UBAH_DOKUMEN:
        raise Galat(409, "Dokumen pada revisi ini tidak dapat diubah karena sedang/sudah direview.")
    sebelum = {"kode_ro": u.kode_ro, "nama_ro": u.nama_ro, "tahun": u.tahun_anggaran, "tor": r.tor_nama, "rab": r.rab_nama}
    if tahun_anggaran:
        u.tahun_anggaran = tahun_anggaran
    if kode_ro and kode_ro.strip():
        u.kode_ro = kode_ro.strip()
    if nama_ro and nama_ro.strip():
        u.nama_ro = nama_ro.strip()
    if tor is not None and tor.filename:
        f, r.tor_nama = simpan_unggahan(db, tor)
        r.tor_file_id = f.id
    if rab is not None and rab.filename:
        f, r.rab_nama = simpan_unggahan(db, rab)
        r.rab_file_id = f.id
    r.updated_at = datetime.now(timezone.utc)
    catat(db, request, "UBAH_DRAF", "revisi", r.id, sebelum=sebelum,
          sesudah={"kode_ro": u.kode_ro, "nama_ro": u.nama_ro, "tahun": u.tahun_anggaran, "tor": r.tor_nama, "rab": r.rab_nama})
    if ajukan:
        ajukan_review(db, request, r, p)
    db.commit()
    db.refresh(u)
    return baris_usulan(db, u, p)


@router.post("/{usulan_id}/revisi")
def revisi_baru(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                p: Pengguna = Depends(wajib_role(PENGUSUL)), tor: UploadFile | None = FormFile(None),
                rab: UploadFile | None = FormFile(None), ajukan: bool = Form(False)) -> dict:
    """Unggah revisi (TOR saja, RAB saja, atau keduanya) setelah hasil final TIDAK LOLOS.
    Dokumen yang tidak diganti terbawa dari revisi sebelumnya.

    Error: 400 tidak ada file; 409 status revisi terakhir belum TIDAK LOLOS.
    """
    u = _ambil(db, usulan_id, p)
    pastikan(boleh_kelola_usulan(p, u))
    if u.diarsipkan_at:
        raise Galat(409, "Usulan diarsipkan.")
    lama = u.revisi[-1]
    if lama.status not in st.BOLEH_REVISI_BARU:
        raise Galat(409, "Revisi baru hanya dapat diunggah setelah hasil review final TIDAK LOLOS.")
    ada_tor, ada_rab = tor is not None and bool(tor.filename), rab is not None and bool(rab.filename)
    if not (ada_tor or ada_rab):
        raise Galat(400, "Unggah minimal satu dokumen (TOR atau RAB).")
    r = Revisi(usulan_id=u.id, nomor=lama.nomor + 1, tor_file_id=lama.tor_file_id, tor_nama=lama.tor_nama,
               rab_file_id=lama.rab_file_id, rab_nama=lama.rab_nama, status=st.DRAF, dibuat_oleh=p.id)
    if ada_tor:
        f, r.tor_nama = simpan_unggahan(db, tor)
        r.tor_file_id = f.id
    if ada_rab:
        f, r.rab_nama = simpan_unggahan(db, rab)
        r.rab_file_id = f.id
    db.add(r)
    db.flush()
    catat(db, request, "REVISI_BARU", "revisi", r.id, sesudah={"nomor": r.nomor, "ganti_tor": ada_tor, "ganti_rab": ada_rab})
    if ajukan:
        ajukan_review(db, request, r, p)
    db.commit()
    db.refresh(u)
    return baris_usulan(db, u, p)


@router.post("/{usulan_id}/ajukan")
def ajukan(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
           p: Pengguna = Depends(wajib_role(PENGUSUL))) -> dict:
    """Ajukan review AI untuk revisi terbaru (status DRAF, atau GAGAL untuk mengulang)."""
    u = _ambil(db, usulan_id, p)
    ajukan_review(db, request, u.revisi[-1], p)
    db.commit()
    return baris_usulan(db, u, p)


@router.delete("/{usulan_id}")
def hapus(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
          p: Pengguna = Depends(wajib_role(PENGUSUL))) -> dict:
    """Hapus usulan yang belum pernah diajukan review (A8). File PDF tetap disimpan.

    Error: 409 bila pernah direview (gunakan arsip).
    """
    u = _ambil(db, usulan_id, p)
    pastikan(boleh_kelola_usulan(p, u))
    if db.scalar(select(exists().where(Review.revisi_id.in_([r.id for r in u.revisi])))):
        raise Galat(409, "Usulan yang sudah pernah direview tidak dapat dihapus, hanya dapat diarsipkan.")
    catat(db, request, "HAPUS_USULAN", "usulan", u.id, sebelum={"kode_ro": u.kode_ro, "nama_ro": u.nama_ro})
    for r in u.revisi:
        db.delete(r)
    db.flush()
    db.delete(u)
    db.commit()
    return {"ok": True}


class Arsip(BaseModel):
    arsip: bool


@router.post("/{usulan_id}/arsip")
def arsipkan(usulan_id: uuid.UUID, data: Arsip, request: Request, db: Session = Depends(sesi_db),
             p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Arsipkan / keluarkan dari arsip. Boleh oleh Pengusul Satker tersebut atau Admin."""
    u = _ambil(db, usulan_id, p)
    pastikan(boleh_kelola_usulan(p, u) or "ADMIN" in p.daftar_role)
    if u.revisi[-1].status in (st.ANTRE, st.DIPROSES_AI):
        raise Galat(409, "Usulan sedang diproses AI dan belum dapat diarsipkan.")
    u.diarsipkan_at = datetime.now(timezone.utc) if data.arsip else None
    catat(db, request, "ARSIP_USULAN" if data.arsip else "BUKA_ARSIP_USULAN", "usulan", u.id)
    db.commit()
    return baris_usulan(db, u, p)


@router.get("/{usulan_id}/riwayat")
def riwayat(usulan_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Riwayat (A7): semua revisi & review + tabel perbandingan checklist antar-revisi.

    Baris perbandingan dikunci oleh `kode` item; item yang isinya berbeda antar versi checklist ditandai.
    Pengusul melihat nilai AI sebelum final, nilai final setelahnya.
    """
    u = _ambil(db, usulan_id, p)
    sebagai_reviewer = boleh_lihat_semua(p)
    revisi_data, kolom, baris = [], [], {}
    for idx, r in enumerate(u.revisi):
        sebelumnya = u.revisi[idx - 1] if idx else None
        reviews = db.scalars(select(Review).where(Review.revisi_id == r.id).order_by(Review.created_at)).all()
        daftar_review = []
        for rv in reviews:
            kat = db.get(KategoriItem, rv.kategori_final_id) if rv.kategori_final_id else None
            daftar_review.append({
                "id": str(rv.id), "status": rv.status, "trace_id": rv.trace_id, "error_pesan": rv.error_pesan,
                "dibuat_at": rv.created_at.isoformat(), "selesai_at": rv.selesai_at.isoformat() if rv.selesai_at else None,
                "label_ai": rv.label_ai, "label_final": rv.label_final,
                "kategori_final": {"kode": kat.kode, "nama": kat.nama, "diteruskan": kat.diteruskan} if kat else None,
                "difinalkan_oleh": db.get(Pengguna, rv.difinalkan_oleh).nama if rv.difinalkan_oleh else None,
                "difinalkan_at": rv.difinalkan_at.isoformat() if rv.difinalkan_at else None,
                "diajukan_oleh": db.get(Pengguna, rv.diajukan_oleh).nama,
            })
            if rv.status == "SELESAI":
                nf, _ = nilai_final_review(db, rv, sebagai_reviewer or rv.difinalkan_at is not None)
                kolom.append({"revisi_nomor": r.nomor, "review_id": str(rv.id), "final": rv.difinalkan_at is not None})
                for ci in db.scalars(select(ChecklistItem).where(ChecklistItem.versi_id == rv.checklist_versi_id)):
                    b = baris.setdefault(ci.kode, {"kode": ci.kode, "judul": ci.judul, "isi": set(), "nilai": {}})
                    b["isi"].add((ci.judul, ci.kriteria, ci.berlaku_untuk))
                    b["nilai"][str(rv.id)] = nf.item.get(str(ci.id))
        revisi_data.append({
            "id": str(r.id), "nomor": r.nomor, "status": r.status, "dibuat_at": r.created_at.isoformat(),
            "dibuat_oleh": db.get(Pengguna, r.dibuat_oleh).nama,
            "tor": {"file_id": str(r.tor_file_id), "nama": r.tor_nama, "diganti": sebelumnya is None or sebelumnya.tor_file_id != r.tor_file_id},
            "rab": {"file_id": str(r.rab_file_id), "nama": r.rab_nama, "diganti": sebelumnya is None or sebelumnya.rab_file_id != r.rab_file_id},
            "review": daftar_review,
        })
    perbandingan = [{"kode": b["kode"], "judul": b["judul"], "berbeda_versi": len(b["isi"]) > 1, "nilai": b["nilai"]}
                    for b in sorted(baris.values(), key=lambda b: b["kode"])]
    return {"usulan": baris_usulan(db, u, p), "revisi": revisi_data, "perbandingan": {"kolom": kolom, "baris": perbandingan}}


@router.get("/opsi/filter")
def opsi_filter(db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Pilihan untuk dropdown filter (Satker, tahun, kategori)."""
    kueri_satker = select(Satker).order_by(Satker.nama)
    if not boleh_lihat_semua(p):
        kueri_satker = kueri_satker.where(Satker.id == p.satker_id)
    tahun = db.scalars(select(Usulan.tahun_anggaran).distinct().order_by(Usulan.tahun_anggaran.desc())).all()
    kode = db.scalars(select(KategoriItem.kode).distinct().order_by(KategoriItem.kode)).all()
    return {"satker": [{"id": str(s.id), "kode": s.kode, "nama": s.nama} for s in db.scalars(kueri_satker)],
            "tahun": tahun, "kategori": kode, "status": [{"kode": k, "nama": v} for k, v in st.NAMA_STATUS.items()]}
