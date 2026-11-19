"""Endpoint Modul A — usulan, revisi, pengajuan review, riwayat."""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File as FormFile, Form, Query, Request, UploadFile
from sqlalchemy import delete, exists, func, or_, select, tuple_, update
from sqlalchemy.orm import Session, aliased

from app import status as st
from app.akses import (PENGUSUL, REVIEWER, boleh_kelola_usulan, boleh_lihat_semua, boleh_lihat_usulan, pastikan,
                       pengguna_saat_ini, wajib_role)
from app.audit import catat
from app.db import sesi_db
from app.galat import Galat
from app.layanan_review import ajukan_review, info_proses, review_terbaru
from app.checklist import kunci_kode
from app.model import (CatatanItem, CatatanReviewer, Elemen, HasilItem, HasilKategori, Job, Kategori, MasterRO, Override, Pengguna,
                       Rekomendasi, Review, ReviewKategori, ReviewPanduan, Revisi, Rujukan, Satker, Usulan)
from app.penyimpanan import hapus_berkas, hapus_file_tak_terpakai, simpan_unggahan

router = APIRouter(prefix="/api/usulan", tags=["usulan"])
WIB = timezone(timedelta(hours=7))  # tanpa musim panas, jadi offset tetap cukup (tidak butuh tzdata)


def tahun_berjalan() -> int:
    """Tahun berjalan menurut WIB, sama dengan pilihan Tahun Anggaran di bilah atas (components/Layout.tsx). Dengan jam UTC,
    pada 1 Januari 00.00–07.00 WIB tahun terakhir di bilah atas ditolak."""
    return datetime.now(WIB).year


def revisi_terbaru():
    """Subquery nomor revisi terbaru per usulan (alias agar tidak ter-korelasi dengan join Revisi utama)."""
    r2 = aliased(Revisi)
    return select(func.max(r2.nomor)).where(r2.usulan_id == Usulan.id).scalar_subquery()


def _ambil(db: Session, usulan_id: uuid.UUID, p: Pengguna, kunci: bool = False) -> Usulan:
    """`kunci=True` untuk endpoint yang mengubah usulan: baris usulan dikunci (FOR UPDATE) SEBELUM revisinya dibaca, sehingga
    dua permintaan bersamaan (mis. dua kali Ajukan, atau Pengusul kirim ulang saat Reviewer mengganti dokumen) diproses
    bergiliran dan yang kedua melihat status terbaru — tidak ada dua review AI untuk satu revisi."""
    u = db.get(Usulan, usulan_id, with_for_update={"of": Usulan} if kunci else None)  # "of": satker ikut di-join (LEFT JOIN)
    if u is None:
        raise Galat(404, "Pengajuan tidak ditemukan.")
    pastikan(boleh_lihat_usulan(p, u))
    return u


def _dok(file_id, nama: str | None, **lain) -> dict | None:
    return {"file_id": str(file_id), "nama": nama, **lain} if file_id else None


def baris_usulan(db: Session, u: Usulan, p: Pengguna) -> dict:
    """Satu baris tabel daftar usulan (A2–A4). Status = status revisi terbaru."""
    r = u.revisi[-1]
    rv = review_terbaru(db, r.id)
    kategori = None
    if rv is not None and rv.status == "SELESAI" and rv.difinalkan_at:
        k = db.get(ReviewKategori, (rv.id, rv.kategori_final_id)) if rv.kategori_final_id else None  # kategori saat review (C4)
        kategori = {"kode": k.kode, "nama": k.nama} if k else None
    return {
        "id": str(u.id), "satker": {"id": str(u.satker.id), "kode": u.satker.kode, "nama": u.satker.nama},
        "tahun_anggaran": u.tahun_anggaran, "kode_ro": u.kode_ro, "nama_ro": u.nama_ro,
        "revisi_id": str(r.id), "revisi_nomor": r.nomor, "status": r.status,
        "tor": _dok(r.tor_file_id, r.tor_nama), "rab": _dok(r.rab_file_id, r.rab_nama),
        "hierarki": u.hierarki, "kategori_usulan": u.kategori_usulan, "dibuat_at": u.created_date.isoformat(),
        # Tanggal Pengajuan = unggahan terakhir (revisi terbaru), bukan pengajuan pertama (desain.md §7 no. 51).
        "diajukan_at": r.created_at.isoformat(),
        "kategori_final": kategori, "diarsipkan": u.diarsipkan_at is not None, "review_id": str(rv.id) if rv else None,
        "proses": info_proses(db, rv) if r.status in (st.ANTRE, st.DIPROSES_AI, st.GAGAL) else None,
        "boleh_kelola": boleh_kelola_usulan(p, u),
    }


@router.get("")
def daftar(db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(PENGUSUL, REVIEWER)),
           satker_id: uuid.UUID | None = None, tahun: int | None = None, status: str | None = None,
           kategori: str | None = None, q: str | None = None,
           satker: str | None = None, dokumen: str | None = None, tanggal: date | None = None,
           urut: Literal["satker", "rincian", "dokumen", "status", "tanggal"] | None = None, arah: Literal["asc", "desc"] = "asc",
           halaman: int = Query(1, ge=1), per_halaman: int = Query(10, ge=1, le=100)) -> dict:
    """Daftar usulan dengan filter A5 dan filter per kolom tabel (desain.md §7 no. 45): `satker` (nama Satuan Kerja), `q`
    (kode/nama RO), `dokumen` (nama file TOR/RAB revisi terbaru), `status`, `tanggal` (tanggal pengajuan revisi terbaru, WIB). `urut` + `arah`
    mengurutkan per kolom; tanpa `urut` = perubahan terbaru dulu. Pengusul otomatis dibatasi ke Satker-nya."""
    kueri = (select(Usulan).join(Revisi, (Revisi.usulan_id == Usulan.id) & (Revisi.nomor == revisi_terbaru()))
             .join(Satker, Satker.id == Usulan.satker_id))
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
                                           ReviewKategori.review_id == Review.id, ReviewKategori.kategori_id == Review.kategori_final_id,
                                           ReviewKategori.kode == kategori))
    if q:
        pola = f"%{q.strip()}%"
        kueri = kueri.where(or_(Usulan.kode_ro.ilike(pola), Usulan.nama_ro.ilike(pola)))
    if satker:
        kueri = kueri.where(Satker.nama.ilike(f"%{satker.strip()}%"))
    if dokumen:
        pola = f"%{dokumen.strip()}%"
        kueri = kueri.where(or_(Revisi.tor_nama.ilike(pola), Revisi.rab_nama.ilike(pola)))
    if tanggal:
        kueri = kueri.where(func.date(func.timezone("Asia/Jakarta", Revisi.created_at)) == tanggal)
    kueri = kueri.where(Usulan.diarsipkan_at.is_(None))  # fitur arsip dihapus (desain.md §7 no. 50); arsip lama tetap tersembunyi
    total = db.scalar(select(func.count()).select_from(kueri.subquery()))
    # Halaman di luar jangkauan (mis. ganti Tahun Anggaran di halaman 2, atau baris terakhir dihapus) → halaman terakhir.
    halaman = min(halaman, max(1, -(-total // per_halaman)))
    kolom = {"satker": Satker.nama, "rincian": Usulan.kode_ro, "dokumen": func.coalesce(Revisi.tor_nama, Revisi.rab_nama),
             "status": Revisi.status, "tanggal": Revisi.created_at}.get(urut or "")
    urutan = [kolom.desc() if arah == "desc" else kolom.asc()] if kolom is not None else [Revisi.updated_at.desc()]
    baris = db.scalars(kueri.order_by(*urutan, Usulan.id).offset((halaman - 1) * per_halaman).limit(per_halaman)).unique().all()
    return {"total": total, "halaman": halaman, "per_halaman": per_halaman, "data": [baris_usulan(db, u, p) for u in baris]}


# Jenjang Master RO: (kolom kode, kolom nama, nama daftar anak di pohon form Pengajuan).
JENJANG = (("kode_program", "program", "kegiatan"), ("kode_kegiatan", "kegiatan", "kro"), ("kode_kro", "kro", "ro"),
           ("kode_ro", "ro", None))


def _pohon(db: Session) -> list[dict]:
    """Pohon Program → Kegiatan → KRO → RO dari menu Master RO untuk form Pengajuan. Hanya data Aktif yang induknya juga
    Aktif (Nonaktif tidak dapat dipilih). Kode per jenjang apa adanya, mis. KRO "EBA", RO "994"."""
    akar: dict[str, dict] = {}
    # Urut kode: baris induk (kode jenjang bawah kosong) selalu sebelum turunannya.
    for m in db.scalars(select(MasterRO).where(MasterRO.aktif).order_by(*(getattr(MasterRO, k) for k, _, _ in JENJANG))):
        kode = [getattr(m, k) for k, _, _ in JENJANG if getattr(m, k)]
        tingkat = akar
        for k in kode[:-1]:
            if k not in tingkat:
                break  # induk Nonaktif/tidak ada → turunannya tidak dapat dipilih
            tingkat = tingkat[k]["anak"]
        else:
            tingkat[kode[-1]] = {"kode": kode[-1], "nama": getattr(m, JENJANG[len(kode) - 1][1]), "anak": {}}

    def daftar(t: dict, n: int) -> list[dict]:
        anak = JENJANG[n][2]
        return [{"kode": x["kode"], "nama": x["nama"], **({anak: daftar(x["anak"], n + 1)} if anak else {})} for x in t.values()]
    return daftar(akar, 0)


def _cari_ro(db: Session, program: str, kegiatan: str, kro: str, ro: str) -> dict | None:
    """Salinan hierarki untuk usulan bila jalur Program/Kegiatan/KRO/RO ada di Master RO dan keempatnya Aktif, selain itu None.
    Kode KRO & RO disimpan lengkap dari Kegiatan (mis. "4490.EBA.994"), sama dengan usulan lama."""
    if not all((program, kegiatan, kro, ro)):
        return None
    jalur = [(program, "", "", ""), (program, kegiatan, "", ""), (program, kegiatan, kro, ""), (program, kegiatan, kro, ro)]
    kunci = tuple_(*(getattr(MasterRO, k) for k, _, _ in JENJANG))
    baris = {(m.kode_program, m.kode_kegiatan, m.kode_kro, m.kode_ro): m
             for m in db.scalars(select(MasterRO).where(MasterRO.aktif, kunci.in_(jalur)))}
    if len(baris) != len(jalur):
        return None
    m = baris[jalur[-1]]
    return {"program": {"kode": program, "nama": m.program}, "kegiatan": {"kode": kegiatan, "nama": m.kegiatan},
            "kro": {"kode": f"{kegiatan}.{kro}", "nama": m.kro}, "ro": {"kode": f"{kegiatan}.{kro}.{ro}", "nama": m.ro}}


def _isian(db: Session, program: str, kegiatan: str, kro: str, ro: str, kategori_id: uuid.UUID) -> tuple[dict, dict]:
    """Validasi pilihan form Pengajuan (hierarki dari Master RO & kategori Aktif). Kembalikan salinan (hierarki, kategori).
    Error: 400 bila jalur hierarki tidak ada/Nonaktif di Master RO atau kategori tidak Aktif."""
    hierarki = _cari_ro(db, program, kegiatan, kro, ro)
    if hierarki is None:
        raise Galat(400, "Program, Kegiatan, KRO, dan RO wajib dipilih dari daftar Master RO yang Aktif.")
    k = db.get(Kategori, kategori_id)
    if k is None or not k.aktif:
        raise Galat(400, "Kategori wajib dipilih dari kategori yang Aktif.")
    return hierarki, {"id": str(k.id), "kode": k.kode, "nama": k.kategori, "deskripsi": k.deskripsi}


def _ada(f: UploadFile | None) -> bool:
    return f is not None and bool(f.filename)


def _pasang_dokumen(db: Session, r: Revisi, tor: UploadFile | None, rab: UploadFile | None) -> set:
    """Pasang TOR dan/atau RAB pengganti pada revisi `r`. Kembalikan id file lama yang tidak lagi dipakai revisi ini.
    Error: 400 bukan PDF; 413 terlalu besar."""
    lama = set()
    if _ada(tor):
        lama.add(r.tor_file_id)
        f, r.tor_nama = simpan_unggahan(db, tor)
        r.tor_file_id = f.id
    if _ada(rab):
        lama.add(r.rab_file_id)
        f, r.rab_nama = simpan_unggahan(db, rab)
        r.rab_file_id = f.id
    return lama - {r.tor_file_id, r.rab_file_id, None}


def _hapus_file_lepas(db: Session, file_ids) -> list[str]:
    """`hapus_file_tak_terpakai` untuk TOR/RAB usulan: file yang masih dikutip rujukan review mana pun dibiarkan, agar review
    lama yang dokumennya sudah diganti tetap utuh (file identik dipakai bersama antar-usulan). Kembalikan path PDF untuk
    `hapus_berkas` setelah commit."""
    ids = {f for f in file_ids if f}
    if not ids:
        return []
    dikutip = set(db.scalars(select(Elemen.file_id).join(Rujukan, Rujukan.elemen_id == Elemen.id)
                             .where(Elemen.file_id.in_(ids)).distinct()))
    return hapus_file_tak_terpakai(db, ids - dikutip)


@router.get("/opsi/pengajuan")
def opsi_pengajuan(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(PENGUSUL, REVIEWER))) -> dict:
    """Pilihan form Pengajuan Baru: pohon Program → Kegiatan → KRO → RO dari menu Master RO (Aktif) dan kategori Aktif
    (urutan Kelola Kategori)."""
    kategori = db.scalars(select(Kategori).where(Kategori.aktif).order_by(Kategori.no_urut, Kategori.kode))
    return {"hierarki": _pohon(db),
            "kategori": [{"id": str(k.id), "kode": k.kode, "nama": k.kategori, "deskripsi": k.deskripsi} for k in kategori]}


@router.post("")
def buat(request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(PENGUSUL)),
         program: str = Form(...), kegiatan: str = Form(...), kro: str = Form(...), ro: str = Form(...),
         kategori_id: uuid.UUID = Form(...), tahun_anggaran: int = Form(...), tor: UploadFile | None = FormFile(None),
         rab: UploadFile | None = FormFile(None), ajukan: bool = Form(False)) -> dict:
    """Pengajuan Baru — Satker = Satker pengusul; TOR dan RAB wajib keduanya (desain.md §7 no. 38). `tahun_anggaran` = pilihan
    Tahun Anggaran di bilah atas (tahun berjalan ±2, desain.md §7 no. 41). `ajukan=true` langsung mengajukan review.

    Error: 400 bila akun belum punya Satker / tahun di luar rentang / pilihan tidak valid / TOR atau RAB kosong / file bukan
    PDF; 413 file terlalu besar.
    """
    if p.satker_id is None:
        raise Galat(400, "Akun Anda belum terhubung ke Satker. Hubungi Admin.")
    sekarang = tahun_berjalan()
    if abs(tahun_anggaran - sekarang) > 2:  # sama dengan pilihan di bilah atas (components/Layout.tsx)
        raise Galat(400, f"Tahun anggaran harus antara {sekarang - 2} dan {sekarang + 2}.")
    hierarki, kategori = _isian(db, program, kegiatan, kro, ro, kategori_id)
    if not (_ada(tor) and _ada(rab)):
        raise Galat(400, "TOR dan RAB wajib diunggah.")
    f_tor, n_tor = simpan_unggahan(db, tor)
    f_rab, n_rab = simpan_unggahan(db, rab)
    u = Usulan(satker_id=p.satker_id, tahun_anggaran=tahun_anggaran, kode_ro=hierarki["ro"]["kode"],
               nama_ro=hierarki["ro"]["nama"], hierarki=hierarki, kategori_usulan=kategori, dibuat_oleh=p.id,
               created_by=p.id, updated_by=p.id)
    db.add(u)
    db.flush()
    r = Revisi(usulan_id=u.id, nomor=1, tor_file_id=f_tor.id, tor_nama=n_tor, rab_file_id=f_rab.id, rab_nama=n_rab,
               status=st.DRAF, dibuat_oleh=p.id)
    db.add(r)
    db.flush()
    catat(db, request, "BUAT_USULAN", "usulan", u.id, sesudah={"kode_ro": u.kode_ro, "kategori": kategori["kode"], "tor": n_tor, "rab": n_rab})
    if ajukan:
        ajukan_review(db, request, r, p)
    db.commit()
    db.refresh(u)
    return baris_usulan(db, u, p)


def _buat_revisi(db: Session, request: Request, u: Usulan, tor: UploadFile | None, rab: UploadFile | None, p: Pengguna) -> Revisi:
    """Revisi baru berisi TOR dan RAB (keduanya wajib, desain.md §7 no. 51). File yang isinya sama dengan revisi
    sebelumnya dipakai ulang (per SHA), sehingga Histori Dokumen tidak menandainya "diganti".
    Error: 400 TOR/RAB kosong / bukan PDF; 413 terlalu besar."""
    if not (_ada(tor) and _ada(rab)):
        raise Galat(400, "TOR dan RAB wajib diunggah.")
    r = Revisi(usulan_id=u.id, nomor=u.revisi[-1].nomor + 1, status=st.DRAF, dibuat_oleh=p.id)
    _pasang_dokumen(db, r, tor, rab)
    db.add(r)
    u.updated_by = p.id
    db.flush()
    catat(db, request, "REVISI_BARU", "revisi", r.id, sesudah={"nomor": r.nomor, "tor": r.tor_nama, "rab": r.rab_nama})
    return r


@router.put("/{usulan_id}")
def ubah_parameter(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(REVIEWER)),
                   program: str = Form(...), kegiatan: str = Form(...), kro: str = Form(...), ro: str = Form(...),
                   kategori_id: uuid.UUID = Form(...), tor: UploadFile | None = FormFile(None),
                   rab: UploadFile | None = FormFile(None)) -> dict:
    """Edit usulan oleh Reviewer (ROCAN), desain.md §7 no. 38, 40 & 43: membetulkan hierarki anggaran & kategori usulan, dan
    (opsional) mengganti TOR dan/atau RAB. Dokumen pengganti dipasang di **revisi terakhir yang sama** (tidak menambah baris
    Histori Dokumen), lalu revisi itu langsung direview AI ulang; review lama tetap tersimpan (hasil AI tidak ditimpa).

    Error: 400 pilihan tidak valid / kategori tidak Aktif / file bukan PDF; 403 bukan Reviewer; 404; 409 revisi terakhir
    sudah diverifikasi (Lolos/Tidak Lolos), atau dokumen diganti saat revisi terakhir masih antre/diproses AI.
    """
    u = _ambil(db, usulan_id, p, kunci=True)
    # Sudah diverifikasi = terkunci (desain.md §7 no. 51); Edit terbuka lagi setelah Pengusul mengunggah revisi baru.
    if u.revisi[-1].status in (st.LOLOS, st.TIDAK_LOLOS):
        raise Galat(409, "Pengajuan yang sudah diverifikasi tidak dapat diedit.")
    sebelum = {"hierarki": u.hierarki, "kategori": u.kategori_usulan}
    u.hierarki, u.kategori_usulan = _isian(db, program, kegiatan, kro, ro, kategori_id)
    u.kode_ro, u.nama_ro = u.hierarki["ro"]["kode"], u.hierarki["ro"]["nama"]
    u.updated_by = p.id
    catat(db, request, "UBAH_USULAN", "usulan", u.id, sebelum=sebelum, sesudah={"hierarki": u.hierarki, "kategori": u.kategori_usulan})
    path_dihapus = []
    if _ada(tor) or _ada(rab):
        r = u.revisi[-1]
        st.ajukan_ulang_oleh_reviewer(r)
        lama = _pasang_dokumen(db, r, tor, rab)
        r.updated_at = datetime.now(timezone.utc)
        catat(db, request, "GANTI_DOKUMEN", "revisi", r.id, sesudah={"nomor": r.nomor, "ganti_tor": _ada(tor), "ganti_rab": _ada(rab)})
        ajukan_review(db, request, r, p, oleh_reviewer=True)
        db.flush()
        # File lama yang dikutip review sebelumnya tetap disimpan; ikut terhapus saat usulan dihapus.
        path_dihapus = _hapus_file_lepas(db, lama)
    db.commit()
    hapus_berkas(path_dihapus)
    db.refresh(u)
    return baris_usulan(db, u, p)


@router.get("/{usulan_id}")
def detail(usulan_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    return baris_usulan(db, _ambil(db, usulan_id, p), p)


@router.put("/{usulan_id}/draf")
def ubah_draf(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
              p: Pengguna = Depends(wajib_role(PENGUSUL)), tor: UploadFile | None = FormFile(None),
              rab: UploadFile | None = FormFile(None), ajukan: bool = Form(False)) -> dict:
    """Ganti PDF TOR dan/atau RAB revisi terbaru selama masih DRAF atau GAGAL (belum ada hasil AI). Hierarki & kategori
    tidak dapat diubah: bila salah input, Satker menghapus usulan lalu mengajukan ulang (desain.md §7 no. 36).

    Error: 409 bila revisi sedang/sudah direview (dokumen terkunci, PRD §5).
    """
    u = _ambil(db, usulan_id, p, kunci=True)
    pastikan(boleh_kelola_usulan(p, u))
    r = u.revisi[-1]
    if r.status not in st.BOLEH_UBAH_DOKUMEN:
        raise Galat(409, "Dokumen pada revisi ini tidak dapat diubah karena sedang/sudah direview.")
    sebelum = {"tor": r.tor_nama, "rab": r.rab_nama}
    lama = _pasang_dokumen(db, r, tor, rab)
    r.updated_at = datetime.now(timezone.utc)
    u.updated_by = p.id
    catat(db, request, "UBAH_DRAF", "revisi", r.id, sebelum=sebelum,
          sesudah={"tor": r.tor_nama, "rab": r.rab_nama})
    if ajukan:
        ajukan_review(db, request, r, p)
    db.flush()
    path_dihapus = _hapus_file_lepas(db, lama)  # Draf/Gagal belum punya hasil AI yang mengutip file lama
    db.commit()
    hapus_berkas(path_dihapus)
    db.refresh(u)
    return baris_usulan(db, u, p)


@router.post("/{usulan_id}/revisi")
def revisi_baru(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                p: Pengguna = Depends(wajib_role(PENGUSUL)), tor: UploadFile | None = FormFile(None),
                rab: UploadFile | None = FormFile(None), ajukan: bool = Form(False)) -> dict:
    """Unggah revisi (TOR dan RAB, keduanya wajib) setelah hasil final TIDAK LOLOS.

    Error: 400 TOR/RAB kosong; 409 status revisi terakhir belum TIDAK LOLOS.
    """
    u = _ambil(db, usulan_id, p, kunci=True)
    pastikan(boleh_kelola_usulan(p, u))
    if u.diarsipkan_at:
        raise Galat(409, "Pengajuan diarsipkan.")
    if u.revisi[-1].status not in st.BOLEH_REVISI_BARU:
        raise Galat(409, "Revisi baru hanya dapat diunggah setelah hasil review final TIDAK LOLOS.")
    r = _buat_revisi(db, request, u, tor, rab, p)
    if ajukan:
        ajukan_review(db, request, r, p)
    db.commit()
    db.refresh(u)
    return baris_usulan(db, u, p)


@router.post("/{usulan_id}/ajukan")
def ajukan(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
           p: Pengguna = Depends(wajib_role(PENGUSUL))) -> dict:
    """Ajukan review AI untuk revisi terbaru (status DRAF, atau GAGAL untuk mengulang)."""
    u = _ambil(db, usulan_id, p, kunci=True)
    ajukan_review(db, request, u.revisi[-1], p)
    db.commit()
    return baris_usulan(db, u, p)


@router.delete("/{usulan_id}")
def hapus(usulan_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
          p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Hapus PERMANEN usulan dari database, apa pun statusnya (lolos, tidak lolos, menunggu verifikasi, gagal) — khusus Reviewer
    (ROCAN), desain.md §7 no. 38 & 42: revisi, review, hasil AI, rujukan, override, catatan, salinan acuan, job, serta file PDF
    TOR/RAB beserta hasil ekstraksinya bila tidak dipakai usulan/panduan lain. Jejak penghapusan (tanpa isi dokumen) tercatat
    di Audit Log.

    Error: 403 bukan Reviewer; 404; 409 bila antre/diproses AI (worker masih menulis hasilnya).
    """
    u = _ambil(db, usulan_id, p, kunci=True)
    if u.revisi[-1].status in (st.ANTRE, st.DIPROSES_AI):
        raise Galat(409, "Pengajuan sedang diproses AI dan belum dapat dihapus.")
    review_ids = list(db.scalars(select(Review.id).where(Review.revisi_id.in_([r.id for r in u.revisi]))))
    file_ids = {f for r in u.revisi for f in (r.tor_file_id, r.rab_file_id)}
    sebelum = {"kode_ro": u.kode_ro, "nama_ro": u.nama_ro, "satker": u.satker.nama, "jumlah_revisi": len(u.revisi),
               "jumlah_review": len(review_ids)}
    if review_ids:
        # TOR/RAB lama yang sudah diganti (Edit Verifikator) tidak ada di revisi lagi, hanya dikutip rujukan review usulan ini.
        file_ids |= set(db.scalars(select(Elemen.file_id).join(Rujukan, Rujukan.elemen_id == Elemen.id)
                                   .where(Rujukan.review_id.in_(review_ids)).distinct()))
        # Review lain yang menyalin hasil dari review ini tetap utuh (punya baris hasil sendiri); hanya penunjuknya dilepas.
        db.execute(update(Review).where(Review.disalin_dari_id.in_(review_ids)).values(disalin_dari_id=None))
        for model in (Rujukan, Rekomendasi, HasilItem, HasilKategori, Override, CatatanReviewer, CatatanItem, ReviewKategori,
                      ReviewPanduan):
            db.execute(delete(model).where(model.review_id.in_(review_ids)))
        db.execute(delete(Job).where(Job.jenis == "REVIEW", Job.ref_id.in_(review_ids)))
        db.execute(delete(Review).where(Review.id.in_(review_ids)))
    for r in u.revisi:
        db.delete(r)
    db.flush()
    db.delete(u)
    db.flush()
    path_dihapus = _hapus_file_lepas(db, file_ids)
    catat(db, request, "HAPUS_USULAN", "usulan", usulan_id, sebelum={**sebelum, "file_dihapus": len(path_dihapus)})
    db.commit()
    hapus_berkas(path_dihapus)
    return {"ok": True}




@router.get("/{usulan_id}/riwayat")
def riwayat(usulan_id: uuid.UUID, db: Session = Depends(sesi_db), p: Pengguna = Depends(pengguna_saat_ini)) -> dict:
    """Detail Usulan + Histori Dokumen: semua revisi beserta review-nya (urut naik). Perbandingan checklist antar-revisi
    dihapus bersama halaman Riwayat (desain.md §7 no. 39)."""
    u = _ambil(db, usulan_id, p)
    revisi_data = []
    for idx, r in enumerate(u.revisi):
        sebelumnya = u.revisi[idx - 1] if idx else None
        reviews = db.scalars(select(Review).where(Review.revisi_id == r.id).order_by(Review.created_at)).all()
        daftar_review = []
        for rv in reviews:
            kat = db.get(ReviewKategori, (rv.id, rv.kategori_final_id)) if rv.kategori_final_id else None
            daftar_review.append({
                "id": str(rv.id), "status": rv.status, "trace_id": rv.trace_id, "error_pesan": rv.error_pesan,
                "dibuat_at": rv.created_at.isoformat(), "selesai_at": rv.selesai_at.isoformat() if rv.selesai_at else None,
                "label_ai": rv.label_ai, "label_final": rv.label_final,
                "kategori_final": {"kode": kat.kode, "nama": kat.nama} if kat else None,
                "difinalkan_oleh": db.get(Pengguna, rv.difinalkan_oleh).nama if rv.difinalkan_oleh else None,
                "difinalkan_at": rv.difinalkan_at.isoformat() if rv.difinalkan_at else None,
                "diajukan_oleh": db.get(Pengguna, rv.diajukan_oleh).nama,
            })
        revisi_data.append({
            "id": str(r.id), "nomor": r.nomor, "status": r.status, "dibuat_at": r.created_at.isoformat(),
            "dibuat_oleh": db.get(Pengguna, r.dibuat_oleh).nama,
            "tor": _dok(r.tor_file_id, r.tor_nama, diganti=sebelumnya is None or sebelumnya.tor_file_id != r.tor_file_id),
            "rab": _dok(r.rab_file_id, r.rab_nama, diganti=sebelumnya is None or sebelumnya.rab_file_id != r.rab_file_id),
            "review": daftar_review,
        })
    return {"usulan": baris_usulan(db, u, p), "revisi": revisi_data}


# Pilihan filter status di halaman Usulan (permintaan pemilik produk, desain.md §7 no. 46). Status lain (Draf, Antre,
# Diproses AI, Gagal) tetap tampil dengan "Semua Status".
FILTER_STATUS = {st.LOLOS: "Lolos", st.MENUNGGU_VERIFIKASI: "Menunggu Reviewer", st.TIDAK_LOLOS: "Tidak Lolos"}


@router.get("/opsi/filter")
def opsi_filter(db: Session = Depends(sesi_db), p: Pengguna = Depends(wajib_role(PENGUSUL, REVIEWER))) -> dict:
    """Pilihan untuk dropdown filter (Satker, tahun, kategori)."""
    kueri_satker = select(Satker).order_by(Satker.nama)
    if not boleh_lihat_semua(p):
        kueri_satker = kueri_satker.where(Satker.id == p.satker_id)
    tahun = db.scalars(select(Usulan.tahun_anggaran).distinct().order_by(Usulan.tahun_anggaran.desc())).all()
    kode = sorted(set(db.scalars(select(Kategori.kode))) | set(db.scalars(select(ReviewKategori.kode).distinct())), key=kunci_kode)
    return {"satker": [{"id": str(s.id), "kode": s.kode, "nama": s.nama} for s in db.scalars(kueri_satker)],
            "tahun": tahun, "kategori": kode, "status": [{"kode": k, "nama": v} for k, v in FILTER_STATUS.items()]}
