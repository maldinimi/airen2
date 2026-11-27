"""Endpoint Master RO (khusus Reviewer): CRUD Program → Kegiatan → KRO → RO.

Tabel `master_ro` berbentuk datar seperti `satker` (lihat model.MasterRO): satu baris memuat kode & nama dirinya
beserta induk-induknya. Respons API memuat kolom datar itu apa adanya (untuk tabel & filter), ditambah bentuk per data
(`tingkat`, `kode`, `nama`, `induk_id`) untuk form: `tingkat` = jenjang terdalam yang terisi dan `induk_id` = id baris
induknya (dicari lewat kode).

Tiap RO juga mencatat Satker pelaksananya di tabel penghubung `master_ro_satker` (JOIN ke `satker`), KHUSUS jenis RO:
dipilih dari menu Satuan Kerja, minimal satu saat Tambah/Ubah RO; Program/Kegiatan/KRO tanpa Satker. Impor Excel
mengisinya dari kolom unit_kerja & satuan_kerja baris RO (dicocokkan ke nama di menu Satuan Kerja).

Master RO per Tahun Anggaran (kolom `tahun_anggaran`): daftar, tambah, dan impor memakai tahun pilihan bilah atas;
induk & turunan selalu setahun; kode unik per induk dalam satu tahun. Form Pengajuan tahun X memakai Master RO tahun X.

Aturan: induk wajib ada & Aktif saat menambah; kode unik per induk; mengubah kode/nama/induk ikut memperbarui baris
turunannya; hapus permanen ditolak bila masih punya turunan. Setiap perubahan dicatat di audit log.

Kode tiap jenjang berupa teks bebas (wajib, maks. MAKS_KODE karakter, disimpan apa adanya; tanpa batasan huruf/angka
atau panjang tetap, permintaan pemilik produk). Aturan dari SEB Menteri PPN & Menteri Keuangan No. 6/2025 (Lampiran I):
nama Program diawali "Program"; nama RO tidak boleh sama dalam satu KRO. Daftar KRO Lampiran II (app/data_kro.py, berkas opsional yang tidak di-commit) hanya menjadi saran di form,
TIDAK menolak kode di luar daftar:
Renja TA 2026 revisi masih memakai KRO yang tidak ada di Lampiran II (mis. UBA, FBB), dan rentang KODE RO per KRO di Lampiran III
juga belum diikuti data Renja (mis. RO FAE 001), sehingga keduanya tidak divalidasi (docs/asumsi.md).
"""
import io
import re
import uuid
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.akses import REVIEWER, wajib_role
from app.audit import catat
from app.checklist import rapikan_fisik
from app.db import jam_db, sesi_db
from app.galat import Galat
from app.model import MasterRO, MasterROSatker, Pengguna, Satker
from app.tahun import tahun_berjalan, tahun_sah

# Berkas data KRO Lampiran II bersifat OPSIONAL: tidak di-commit (.gitignore, permintaan pemilik produk). Tanpa berkas
# ini daftar referensi kosong: form KRO tanpa saran nama, aplikasi tetap berjalan.
try:
    from app.data_kro import KRO
except ModuleNotFoundError as e:
    if e.name != "app.data_kro":
        raise
    KRO: list[tuple[str, str, str, str]] = []

router = APIRouter(prefix="/api/master-ro", tags=["master RO"])

TINGKAT = ("PROGRAM", "KEGIATAN", "KRO", "RO")
INDUK = {"KEGIATAN": "PROGRAM", "KRO": "KEGIATAN", "RO": "KRO"}  # jenis → jenis induknya
NAMA_TINGKAT = {"PROGRAM": "Program", "KEGIATAN": "Kegiatan", "KRO": "KRO", "RO": "RO"}
# Kolom (kode, nama) per jenjang, urut Program → RO. Keduanya ikut tersalin ke baris turunan.
KOLOM = {"PROGRAM": ("kode_program", "program"), "KEGIATAN": ("kode_kegiatan", "kegiatan"),
         "KRO": ("kode_kro", "kro"), "RO": ("kode_ro", "ro")}
SEMUA_KOLOM = tuple(k for t in TINGKAT for k in KOLOM[t])
# Kode = teks bebas (tanpa batasan huruf/angka), hanya dibatasi panjang kolom: kode String(50), nama String(255).
MAKS_KODE = 50
MAKS_NAMA = 255

Kunci = tuple[str, str, str, str]


class MasterROMasuk(BaseModel):
    """Isian tambah/ubah. `induk_id` wajib kecuali Program. `tingkat` (jenis) tidak dapat diubah saat ubah.
    `satker_ids` = Satuan Kerja (Eselon II) pelaksana, urut isian form; khusus RO, minimal satu (diabaikan untuk
    Program/Kegiatan/KRO)."""
    model_config = ConfigDict(str_strip_whitespace=True)
    tingkat: str
    induk_id: uuid.UUID | None = None
    kode: str
    nama: str
    aktif: bool = True
    satker_ids: list[uuid.UUID] = []
    # Tahun Anggaran data baru (Tambah; pilihan bilah atas). Saat Ubah diabaikan: tahun data tidak dapat dipindah.
    tahun_anggaran: int | None = None



def _kunci(m: MasterRO) -> Kunci:
    return (m.kode_program, m.kode_kegiatan, m.kode_kro, m.kode_ro)


def _jenis(m: MasterRO) -> str:
    """Jenjang terdalam yang terisi."""
    return next(t for t in reversed(TINGKAT) if getattr(m, KOLOM[t][0]))


def _kunci_induk(m: MasterRO) -> Kunci | None:
    """Kunci baris induk: kode jenjang milik baris ini dikosongkan. None untuk Program."""
    n = TINGKAT.index(_jenis(m))
    return None if n == 0 else tuple(k if i < n else "" for i, k in enumerate(_kunci(m)))  # type: ignore[return-value]


def _kode_lengkap(m: MasterRO) -> str:
    return ".".join(k for k in _kunci(m) if k)


def _kode_nama(m: MasterRO) -> tuple[str, str]:
    kk, kn = KOLOM[_jenis(m)]
    return getattr(m, kk), getattr(m, kn)


def _satker_per_ro(db: Session, ro_id: uuid.UUID | None = None, tahun: int | None = None) -> dict[uuid.UUID, list[Satker]]:
    """Satker pelaksana per RO lewat JOIN master_ro_satker → satker, urut isian form. `ro_id` = hanya satu RO;
    `tahun` = hanya RO Tahun Anggaran itu."""
    kueri = (select(MasterROSatker.master_ro_id, Satker).join(Satker, Satker.id == MasterROSatker.satker_id)
             .order_by(MasterROSatker.no_urut))
    if ro_id is not None:
        kueri = kueri.where(MasterROSatker.master_ro_id == ro_id)
    if tahun is not None:
        kueri = kueri.join(MasterRO, MasterRO.id == MasterROSatker.master_ro_id).where(MasterRO.tahun_anggaran == tahun)
    hasil: dict[uuid.UUID, list[Satker]] = defaultdict(list)
    for ro, s in db.execute(kueri):
        hasil[ro].append(s)
    return hasil


def _isi_satker(daftar: list[Satker]) -> list[dict]:
    return [{"id": str(s.id), "kode_uke1": s.kode_uke1, "unit_kerja": s.unit_kerja, "kode_uke2": s.kode_uke2,
             "nama": s.nama, "aktif": s.aktif} for s in daftar]


def _baris(m: MasterRO, per_kunci: dict[Kunci, MasterRO], nama_pengguna: dict, anak: Counter, satker: list[Satker]) -> dict:
    kunci_induk = _kunci_induk(m)
    induk = per_kunci.get(kunci_induk) if kunci_induk else None
    kode, nama = _kode_nama(m)
    return {
        "id": str(m.id), "tahun_anggaran": m.tahun_anggaran, "tingkat": _jenis(m), "kode": kode, "nama": nama, "aktif": m.aktif,
        **{k: getattr(m, k) for k in SEMUA_KOLOM},  # kolom datar (kosong untuk jenjang di bawah data ini)
        "kode_lengkap": _kode_lengkap(m),
        "induk_id": str(induk.id) if induk else None,
        "induk": {"kode": _kode_lengkap(induk), "nama": _kode_nama(induk)[1]} if induk else None,
        "jumlah_turunan": anak[_kunci(m)],
        "satker": _isi_satker(satker),  # [{id, kode_uke1, unit_kerja, kode_uke2, nama, aktif}], urut isian form
        "dibuat_oleh": nama_pengguna.get(m.created_by), "dibuat_at": m.created_date.isoformat(),
        "diubah_oleh": nama_pengguna.get(m.updated_by), "diubah_at": m.updated_date.isoformat(),
    }


def _respons(db: Session, tahun: int, hanya: MasterRO | None = None) -> list[dict] | dict:
    """Bentuk respons API untuk Tahun Anggaran `tahun`; `hanya` = satu baris (setelah tambah/ubah), selain itu semua baris
    tahun itu."""
    semua = list(db.scalars(select(MasterRO).where(MasterRO.tahun_anggaran == tahun)))
    per_kunci = {_kunci(m): m for m in semua}
    # Hanya id & username (Pengguna.nama = username); tanpa memuat relasi satker/roles.
    nama_pengguna = {i: u for i, u in db.execute(select(Pengguna.id, Pengguna.username))}
    anak = Counter(_kunci_induk(m) for m in semua)
    satker = _satker_per_ro(db, hanya.id) if hanya is not None else _satker_per_ro(db, tahun=tahun)
    if hanya is not None:
        return _baris(hanya, per_kunci, nama_pengguna, anak, satker.get(hanya.id, []))
    # Urut bawaan: data yang paling baru DITAMBAHKAN paling atas (permintaan pemilik produk), agar data yang baru disimpan
    # langsung terlihat. Data yang dibuat bersamaan (seed atau satu kali impor = waktu sama) tetap berjenjang: Program
    # diikuti Kegiatan-nya, lalu KRO, lalu RO (sort Python stabil: urut kode dulu, lalu waktu dibuat menurun).
    berjenjang = sorted(semua, key=_kunci)
    return [_baris(m, per_kunci, nama_pengguna, anak, satker.get(m.id, []))
            for m in sorted(berjenjang, key=lambda m: m.created_date, reverse=True)]


def _satker_ids(db: Session, m: MasterRO) -> list[uuid.UUID]:
    """Id Satker pelaksana `m`, urut isian form."""
    return list(db.scalars(select(MasterROSatker.satker_id).where(MasterROSatker.master_ro_id == m.id)
                           .order_by(MasterROSatker.no_urut)))


def _simpan_satker(db: Session, m: MasterRO, ids: list[uuid.UUID]) -> None:
    """Ganti daftar Satker pelaksana `m` (DELETE langsung lalu INSERT saat flush: tidak bentrok primary key)."""
    db.execute(delete(MasterROSatker).where(MasterROSatker.master_ro_id == m.id))
    db.add_all(MasterROSatker(master_ro_id=m.id, satker_id=i, no_urut=n) for n, i in enumerate(ids, start=1))


def kunci_ro_satker(db: Session, satker_id: uuid.UUID | None, tahun: int) -> set[Kunci]:
    """Kunci (kode_program, kode_kegiatan, kode_kro, kode_ro) RO Tahun Anggaran `tahun` yang Satker-nya mencakup `satker_id`. Dipakai
    form Pengajuan: Pengusul hanya dapat memilih RO Satker-nya sendiri (RO tanpa Satker tidak termasuk)."""
    if satker_id is None:
        return set()
    kueri = (select(MasterRO.kode_program, MasterRO.kode_kegiatan, MasterRO.kode_kro, MasterRO.kode_ro)
             .join(MasterROSatker, MasterROSatker.master_ro_id == MasterRO.id)
             .where(MasterROSatker.satker_id == satker_id, MasterRO.tahun_anggaran == tahun))
    return {tuple(b) for b in db.execute(kueri)}  # type: ignore[misc]


def jumlah_ro_memakai_satker(db: Session, satker_id: uuid.UUID) -> int:
    """Jumlah RO Master RO yang memakai Satker ini. Dipakai menu Satuan Kerja untuk pesan tolak hapus yang jelas
    (FK master_ro_satker tetap menjaga di database) dan menolak mengosongkan nama Satuan Kerja yang dipakai RO."""
    return db.scalar(select(func.count()).where(MasterROSatker.satker_id == satker_id)) or 0


def _validasi_satker(db: Session, tingkat: str, ids: list[uuid.UUID], sudah: frozenset = frozenset()) -> list[uuid.UUID]:
    """Satker pelaksana, KHUSUS RO: minimal satu, tidak dobel, harus Satuan Kerja (Eselon II) yang ada & Aktif. Satker
    yang sudah tercatat di RO yang diubah (`sudah`) boleh tetap dipilih walau kini Nonaktif. Program/Kegiatan/KRO selalu tanpa
    Satker (isian diabaikan). Hasil = id Satker urut isian. Error 400."""
    if tingkat != "RO":
        return []
    if not ids:
        raise Galat(400, "Pilih minimal satu Unit Kerja (Eselon I) dan Satuan Kerja (Eselon II).")
    if len(set(ids)) != len(ids):
        raise Galat(400, "Satuan Kerja yang sama dipilih lebih dari sekali. Hapus salah satunya.")
    per_id = {s.id: s for s in db.scalars(select(Satker).where(Satker.id.in_(ids)))}
    for i in ids:
        s = per_id.get(i)
        if s is None or not s.nama:
            raise Galat(400, "Satuan Kerja tidak ditemukan. Muat ulang halaman lalu pilih lagi.")
        if not s.aktif and i not in sudah:
            raise Galat(400, f"Satuan Kerja {s.nama} berstatus Nonaktif sehingga tidak dapat dipilih.")
    return ids


def _syarat_turunan(m: MasterRO):
    """Filter SQL baris turunan `m`: tahun sama, kode jenjang sampai jenis `m` sama, dan jenjang berikutnya terisi."""
    n = TINGKAT.index(_jenis(m))
    if n == len(TINGKAT) - 1:
        return None  # RO tidak punya turunan
    syarat = [MasterRO.tahun_anggaran == m.tahun_anggaran,
              *(getattr(MasterRO, KOLOM[t][0]) == getattr(m, KOLOM[t][0]) for t in TINGKAT[:n + 1])]
    return and_(*syarat, getattr(MasterRO, KOLOM[TINGKAT[n + 1]][0]) != "")


def _validasi(db: Session, data: MasterROMasuk, tahun: int, lama: MasterRO | None = None) -> dict:
    """Periksa isian (kode & nama disimpan apa adanya, tanpa spasi di ujung). Hasil = nilai kolom jenjang sampai jenis data ini (kolom induk
    disalin dari baris induk). Semua dalam Tahun Anggaran `tahun`: induk tahun lain tidak sah, kode unik per tahun.
    Error 400: jenis/induk tidak sah, isian kosong/terlalu panjang, kode sudah dipakai."""
    if data.tingkat not in TINGKAT:
        raise Galat(400, "Jenis harus Program, Kegiatan, KRO, atau RO.")
    if lama is not None and data.tingkat != _jenis(lama):
        raise Galat(400, "Jenis tidak dapat diubah. Hapus lalu tambahkan dengan jenis yang benar.")
    nama_jenis = NAMA_TINGKAT[data.tingkat]
    kode, nama = data.kode, data.nama
    if not kode:
        raise Galat(400, f"Kode {nama_jenis} wajib diisi.")
    if len(kode) > MAKS_KODE:
        raise Galat(400, f"Kode {nama_jenis} maksimal {MAKS_KODE} karakter.")
    if not nama:
        raise Galat(400, f"Nama {nama_jenis} wajib diisi.")
    if len(nama) > MAKS_NAMA:
        raise Galat(400, f"Nama {nama_jenis} maksimal {MAKS_NAMA} karakter.")
    # Nama Program pada RKA-K/L selalu diawali "Program" (mis. Program Dukungan Manajemen); mencegah salah isi seperti
    # nama jenis belanja ("Belanja …") di kolom Program.
    if data.tingkat == "PROGRAM" and not re.match(r"program\s", nama, re.IGNORECASE):
        raise Galat(400, "Nama Program diawali kata \"Program\", mis. Program Dukungan Manajemen.")
    n = TINGKAT.index(data.tingkat)
    isi: dict = {k: "" for k in SEMUA_KOLOM}
    if n > 0:
        nama_induk = NAMA_TINGKAT[INDUK[data.tingkat]]
        induk = db.get(MasterRO, data.induk_id) if data.induk_id else None
        if induk is None or _jenis(induk) != INDUK[data.tingkat] or induk.tahun_anggaran != tahun:
            raise Galat(400, f"Pilih {nama_induk} induk yang valid.")
        # Induk Nonaktif tidak dapat dipilih untuk data baru, tetapi baris lama boleh tetap di bawahnya.
        if not induk.aktif and (lama is None or _kunci_induk(lama) != _kunci(induk)):
            raise Galat(400, f"{nama_induk} induk berstatus Nonaktif sehingga tidak dapat dipilih.")
        for t in TINGKAT[:n]:
            for k in KOLOM[t]:
                isi[k] = getattr(induk, k)
    isi[KOLOM[data.tingkat][0]], isi[KOLOM[data.tingkat][1]] = kode, nama
    kueri = select(MasterRO.id).where(MasterRO.tahun_anggaran == tahun,
                                      *(getattr(MasterRO, KOLOM[t][0]) == isi[KOLOM[t][0]] for t in TINGKAT))
    if lama is not None:
        kueri = kueri.where(MasterRO.id != lama.id)
    if db.scalar(kueri.limit(1)):
        raise Galat(400, _pesan_ganda(data.tingkat))
    # SEB 6/2025 Lampiran I: nomenklatur RO tidak boleh sama dalam satu KRO (tanpa membedakan huruf besar/kecil).
    # Hanya untuk RO: KRO PN & Non-PN di satu Kegiatan memang bernama sama (mis. ABL & PBL).
    if data.tingkat == "RO":
        sama = select(MasterRO.id).where(MasterRO.tahun_anggaran == tahun,
                                         *(getattr(MasterRO, KOLOM[t][0]) == isi[KOLOM[t][0]] for t in TINGKAT[:3]),
                                         MasterRO.kode_ro != "", func.lower(MasterRO.ro) == nama.lower())
        if lama is not None:
            sama = sama.where(MasterRO.id != lama.id)
        if db.scalar(sama.limit(1)):
            raise Galat(400, "Nama RO sudah dipakai di KRO yang sama.")
    return isi


def _pesan_ganda(tingkat: str) -> str:
    if tingkat == "PROGRAM":
        return "Kode Program sudah dipakai."
    return f"Kode {NAMA_TINGKAT[tingkat]} sudah dipakai di {NAMA_TINGKAT[INDUK[tingkat]]} yang sama."


def _simpan(db: Session, tingkat: str) -> None:
    """flush; dua Reviewer menyimpan kode sama bersamaan → UNIQUE database menolak → 400, bukan 500."""
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Galat(400, _pesan_ganda(tingkat))


def _rapikan(db: Session) -> None:
    """Urutan fisik tabel = urutan di layar (terbaru ditambahkan paling atas), untuk pgAdmin "View Data" tanpa ORDER BY.
    Dilewati bila tabel sedang dikunci; dirapikan lagi pada simpan berikutnya (checklist.rapikan_fisik)."""
    rapikan_fisik(db, "master_ro", "ix_master_ro_created_date")


def _ambil(db: Session, ro_id: uuid.UUID) -> MasterRO:
    m = db.get(MasterRO, ro_id)
    if m is None:
        raise Galat(404, "Data Master RO tidak ditemukan. Muat ulang halaman.")
    return m


def _isi_audit(db: Session, m: MasterRO) -> dict:
    """Isi audit: kolom jenjang, Satker pelaksana (nama saat itu, karena nama di menu Satuan Kerja dapat berubah), status."""
    satker = [f"{s.unit_kerja} / {s.nama}" for s in _satker_per_ro(db, m.id).get(m.id, [])]
    return {"tahun_anggaran": m.tahun_anggaran, **{k: getattr(m, k) for k in SEMUA_KOLOM}, "satker": satker, "aktif": m.aktif}


@router.get("")
def daftar(tahun: int | None = Query(None), db: Session = Depends(sesi_db),
           _: Pengguna = Depends(wajib_role(REVIEWER))) -> list[dict]:
    """Data Master RO Tahun Anggaran `tahun` (bawaan: tahun berjalan WIB), terbaru ditambahkan paling atas.
    Error: 403 bukan Reviewer."""
    return _respons(db, tahun or tahun_berjalan())


@router.get("/referensi-kro")
def referensi_kro(_: Pengguna = Depends(wajib_role(REVIEWER))) -> list[dict]:
    """Daftar KRO Lampiran II SEB 6/2025 untuk saran di form KRO: kode Non-PN dan kode PN (bila ada) masing-masing
    satu baris. Output: [{kode, nama, satuan, pn}]. Error: 403 bukan Reviewer."""
    hasil = []
    for non_pn, pn, nama, satuan in KRO:
        hasil.append({"kode": non_pn, "nama": nama, "satuan": satuan, "pn": False})
        if pn:
            hasil.append({"kode": pn, "nama": nama, "satuan": satuan, "pn": True})
    return sorted(hasil, key=lambda x: x["kode"])


@router.post("")
def tambah(data: MasterROMasuk, request: Request, db: Session = Depends(sesi_db),
           p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Tambah Program/Kegiatan/KRO/RO di Tahun Anggaran `tahun_anggaran` beserta Satker pelaksananya (khusus RO, minimal satu). Kolom induk disalin dari baris
    induk. Error: 400 isian tidak valid / kode sudah dipakai; 403."""
    tahun = tahun_sah(data.tahun_anggaran)
    isi = _validasi(db, data, tahun)
    satker = _validasi_satker(db, data.tingkat, data.satker_ids)
    sekarang = jam_db(db)
    m = MasterRO(**isi, tahun_anggaran=tahun, aktif=data.aktif, created_by=p.id, created_date=sekarang, updated_by=p.id, updated_date=sekarang)
    db.add(m)
    _simpan(db, data.tingkat)  # flush: id RO terisi untuk master_ro_satker
    _simpan_satker(db, m, satker)
    db.flush()
    _rapikan(db)
    catat(db, request, "MASTER_RO_TAMBAH", "master_ro", m.id, sesudah=_isi_audit(db, m))
    db.commit()
    return _respons(db, tahun, m)


# --- Impor dari Excel --------------------------------------------------------------------------------------------------
# Kolom wajib file impor = kolom tabel Master RO di layar (permintaan pemilik produk), termasuk unit_kerja & satuan_kerja
# (Revisi 7; disimpan ke master_ro_satker lewat id Satker). Urutan kolom di file bebas; judul kolom dicocokkan tanpa membedakan huruf besar/kecil dan spasi dianggap "_".
KOLOM_IMPOR = (*SEMUA_KOLOM, "unit_kerja", "satuan_kerja")
MAKS_BYTE_IMPOR = 5 * 1024 * 1024
MAKS_BARIS_IMPOR = 5000
# Batas pembacaan file: .xlsx terkompresi, jadi file 5 MB bisa berisi jutaan baris/kolom. Baris (termasuk baris kosong)
# & kolom di luar batas ini tidak dibaca, agar file seperti itu tidak menghabiskan memori/CPU server.
MAKS_BARIS_DIBACA = 50_000
MAKS_KOLOM_DIBACA = 100
MAKS_GALAT_IMPOR = 50  # pesan kesalahan yang ditampilkan; sisanya cukup dihitung
PESAN_RUSAK = "File tidak dapat dibaca. Pastikan file berformat Excel (.xlsx) dan tidak rusak."


def _sel(nilai, kolom: str) -> str:
    """Isi sel → teks apa adanya (kode teks bebas, tidak dilengkapi/diubah). Angka utuh (mis. 4511.0) jadi "4511"."""
    if nilai is None:
        return ""
    if isinstance(nilai, float) and nilai.is_integer():
        nilai = int(nilai)
    return str(nilai).strip()


def _pisah(teks: str) -> list[str]:
    """Beberapa Satker dalam satu sel: dipisah titik koma atau baris baru (Alt+Enter di Excel). Bagian kosong tetap
    dihitung (posisi berpasangan dengan kolom lain); sel kosong = tanpa isi."""
    return [x.strip() for x in re.split(r"[;\n]", teks)] if teks.strip() else []


def _normal(teks: str) -> str:
    return " ".join(teks.split()).lower()


def _satker_impor(unit_teks: str, satuan_teks: str,
                  peta: dict[tuple[str, str], Satker]) -> tuple[list[uuid.UUID], dict[uuid.UUID, str]]:
    """Isi sel unit_kerja & satuan_kerja → (id Satker urut sel, nama Satker Nonaktif) dicocokkan ke nama di menu
    Satuan Kerja. Pasangan dicocokkan per urutan, tanpa membedakan huruf besar/kecil & spasi ganda. Sel unit_kerja
    kosong seluruhnya = Satker tanpa Unit Kerja (pilihan "Tanpa Unit Kerja" di form). Satker Nonaktif tidak langsung
    ditolak: pemanggil menolaknya hanya bila Satker itu baru dipasang (RO baru / dilengkapi), bukan bila RO sudah
    memakainya (impor ulang tetap aman). Error 400: jumlah tidak sama, Satker tidak ada, Satker dobel."""
    unit, satuan = _pisah(unit_teks), _pisah(satuan_teks)
    if not unit and satuan:
        unit = [""] * len(satuan)
    if len(unit) != len(satuan):
        raise Galat(400, f"Jumlah Unit Kerja ({len(unit)}) dan Satuan Kerja ({len(satuan)}) harus sama. "
                         "Pisahkan beberapa Satker dengan titik koma (;) dengan urutan yang sama di kedua kolom.")
    hasil: list[uuid.UUID] = []
    nonaktif: dict[uuid.UUID, str] = {}  # id → nama Satker Nonaktif
    for uk, sk in zip(unit, satuan):
        if not uk and not sk:  # mis. titik koma di akhir sel
            continue
        if not sk:
            raise Galat(400, f'Satuan Kerja untuk Unit Kerja "{uk}" kosong. Isi Satuan Kerja pada urutan yang sama.')
        s = peta.get((_normal(uk), _normal(sk)))
        if s is None:
            tempat = f' dengan Unit Kerja "{uk}"' if uk else " tanpa Unit Kerja"
            raise Galat(400, f'Satuan Kerja "{sk}"{tempat} tidak ada di menu Satuan Kerja.')
        if s.id in hasil:
            raise Galat(400, f"Satuan Kerja {s.nama} ditulis lebih dari sekali.")
        if not s.aktif:
            nonaktif[s.id] = s.nama
        hasil.append(s.id)
    return hasil, nonaktif


def _kosong(baris: tuple) -> bool:
    return all(v is None or str(v).strip() == "" for v in baris)


def _baca_lembar(isi: bytes) -> tuple[tuple | None, list[tuple[int, tuple]]]:
    """Baca lembar pertama BARIS DEMI BARIS (tidak dimuat semua ke memori). Hasil: (baris judul = baris pertama yang
    tidak kosong, [(nomor baris Excel, isi)] baris tidak kosong sesudahnya). Berhenti begitu data melebihi
    MAKS_BARIS_IMPOR atau baris yang dibaca melebihi MAKS_BARIS_DIBACA. Error 400: file rusak / terlalu banyak baris."""
    try:
        wb = load_workbook(io.BytesIO(isi), read_only=True, data_only=True)
    except Exception:  # file rusak / bukan Excel: pesan ramah, bukan 500
        raise Galat(400, PESAN_RUSAK)
    judul: tuple | None = None
    data: list[tuple[int, tuple]] = []
    try:
        for no, b in enumerate(wb.worksheets[0].iter_rows(max_col=MAKS_KOLOM_DIBACA, values_only=True), start=1):
            if no > MAKS_BARIS_DIBACA:
                raise Galat(400, f"File terlalu banyak baris (maksimal {MAKS_BARIS_DIBACA} baris termasuk baris kosong). "
                                 "Hapus baris kosong di bawah data lalu import lagi.")
            if _kosong(b):
                continue
            if judul is None:
                judul = b
                continue
            data.append((no, b))
            if len(data) > MAKS_BARIS_IMPOR:
                raise Galat(400, f"Data terlalu banyak (maksimal {MAKS_BARIS_IMPOR} baris per import).")
    except Galat:
        raise
    except Exception:  # isi lembar rusak (baru ketahuan saat dibaca)
        raise Galat(400, PESAN_RUSAK)
    finally:
        wb.close()
    return judul, data


@router.post("/impor")
# Sengaja bukan async: baca Excel + ribuan query berjalan di threadpool, tidak membekukan worker uvicorn.
def impor(request: Request, file: UploadFile = File(...), tahun_anggaran: int | None = Form(None),
          db: Session = Depends(sesi_db),
          p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Impor Master RO dari file Excel (.xlsx) berkolom kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro,
    kode_ro, ro, unit_kerja, satuan_kerja (lembar pertama; baris pertama yang tidak kosong = judul kolom).

    Tiap baris = satu data beserta induknya, seperti satu baris tabel Master RO; jenjang di bawahnya boleh kosong.
    Jenjang yang belum ada dibuat (Aktif) dengan aturan yang sama dengan tambah manual (`_validasi`); jenjang yang sudah
    ada dipakai apa adanya, tetapi namanya harus sama dengan di file (tidak mengganti nama diam-diam).
    Semua-atau-tidak-sama-sekali: bila ada satu kesalahan, tidak ada yang tersimpan dan semua kesalahan dilaporkan per
    nomor baris Excel, agar file dapat diperbaiki lalu diimpor ulang. Mengimpor file yang sama dua kali aman (semua
    data sudah ada → tidak ada yang dibuat).
    unit_kerja & satuan_kerja = Satker pelaksana RO di baris itu (khusus baris RO; beberapa Satker dipisah ";"/baris
    baru, berpasangan per urutan, harus ada di menu Satuan Kerja). Bebas ditulis (permintaan pemilik produk): satu
    baris berisi beberapa Satker, atau RO yang sama di beberapa baris; Satker semua baris digabung urut baris. RO yang
    sudah ada: Satker dari file DITAMBAHKAN (yang belum tercatat; Satker lama tidak pernah dihapus lewat impor), dihitung
    `satker_diisi`. Satker Nonaktif ditolak hanya bila baru ditambahkan. RO baru wajib punya minimal satu Satker
    dari salah satu barisnya (dicek setelah semua baris dibaca); baris Program/Kegiatan/KRO harus mengosongkannya.
    `tahun_anggaran` (form) = Tahun Anggaran tujuan (pilihan bilah atas); "sudah ada" dicari di tahun itu saja.
    Output: {tahun_anggaran, baris, dibuat: {PROGRAM, KEGIATAN, KRO, RO}, total_dibuat, sudah_ada, satker_diisi}.
    Error: 400 file bukan .xlsx / kolom kurang / tidak ada data / ada baris tidak valid; 403; 409; 413 file terlalu besar."""
    tahun = tahun_sah(tahun_anggaran)  # semua data file masuk ke Tahun Anggaran ini (pilihan bilah atas)
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise Galat(400, "File harus berformat Excel (.xlsx).")
    isi = file.file.read(MAKS_BYTE_IMPOR + 1)
    if len(isi) > MAKS_BYTE_IMPOR:
        raise Galat(413, f"File terlalu besar (maksimal {MAKS_BYTE_IMPOR // (1024 * 1024)} MB).")
    baris_judul, data = _baca_lembar(isi)  # data = (nomor baris di Excel, isi); baris kosong dilewati
    if baris_judul is None:
        raise Galat(400, f"File kosong. Isi baris judul berkolom {', '.join(KOLOM_IMPOR)}, lalu datanya mulai baris berikutnya.")
    judul = [str(v or "").strip().lower().replace(" ", "_") for v in baris_judul]
    kurang = [k for k in KOLOM_IMPOR if k not in judul]
    if kurang:
        raise Galat(400, f"Kolom berikut tidak ada di baris judul: {', '.join(kurang)}. Baris judul harus berisi kolom {', '.join(KOLOM_IMPOR)}.")
    posisi = {k: judul.index(k) for k in KOLOM_IMPOR}
    if not data:
        raise Galat(400, "File tidak berisi data. Isi data mulai baris setelah judul kolom.")

    per_kunci: dict[Kunci, MasterRO] = {_kunci(m): m for m in db.scalars(select(MasterRO).where(MasterRO.tahun_anggaran == tahun))}
    sekarang = jam_db(db)
    dibuat: Counter = Counter()
    sudah_ada = 0
    galat: list[str] = []
    peta_satker = {(_normal(s.unit_kerja), _normal(s.nama)): s for s in db.scalars(select(Satker).where(Satker.nama != ""))}
    # Satker yang sudah tercatat per RO (id urut isian); ikut diperbarui untuk RO yang dibuat/ditambah file ini.
    satker_ada: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for ro, sid in db.execute(select(MasterROSatker.master_ro_id, MasterROSatker.satker_id)
                              .join(MasterRO, MasterRO.id == MasterROSatker.master_ro_id)
                              .where(MasterRO.tahun_anggaran == tahun).order_by(MasterROSatker.no_urut)):
        satker_ada[ro].append(sid)
    tautan_baru: list[MasterROSatker] = []  # ditulis sekali setelah semua baris lolos (impor hanya menambah)
    ro_baru: dict[uuid.UUID, tuple[int, str]] = {}  # RO yang dibuat impor ini → (nomor baris pembuatnya, kode RO)
    ro_ditambah: set[uuid.UUID] = set()  # RO lama yang Satker-nya ditambah impor ini
    for no, b in data:
        nilai = {k: _sel(b[posisi[k]] if posisi[k] < len(b) else None, k) for k in KOLOM_IMPOR}
        induk: MasterRO | None = None
        jalur: list[str] = []
        kosong_di: str | None = None  # jenjang pertama yang kosong; jenjang di bawahnya harus kosong juga
        baru_dibuat = False  # data terdalam baris ini (= induk setelah loop) baru dibuat oleh baris ini
        try:
            satker, nonaktif = _satker_impor(nilai["unit_kerja"], nilai["satuan_kerja"], peta_satker)
            for t in TINGKAT:
                kk, kn = KOLOM[t]
                kode, nama = nilai[kk], nilai[kn]  # teks bebas, disimpan apa adanya (sama dengan Tambah)
                if not kode and not nama:
                    kosong_di = kosong_di or t
                    continue
                if kosong_di:
                    raise Galat(400, f"{NAMA_TINGKAT[t]} diisi tetapi {NAMA_TINGKAT[kosong_di]} kosong.")
                if not kode or not nama:
                    raise Galat(400, f"Kode dan nama {NAMA_TINGKAT[t]} harus diisi bersama.")
                jalur.append(kode)
                kunci: Kunci = tuple(jalur + [""] * (len(TINGKAT) - len(jalur)))  # type: ignore[assignment]
                ada = per_kunci.get(kunci)
                if ada is not None:  # sudah ada (di database atau baris sebelumnya): dipakai, nama harus sama
                    nama_ada = _kode_nama(ada)[1]
                    if nama_ada.strip() != nama:
                        raise Galat(400, f'Nama {NAMA_TINGKAT[t]} {kode} berbeda dengan data yang sudah ada ("{nama_ada}").')
                    sudah_ada += 1
                    induk, baru_dibuat = ada, False
                    continue
                baru = _validasi(db, MasterROMasuk(tingkat=t, induk_id=induk.id if induk else None, kode=kode, nama=nama), tahun)
                m = MasterRO(**baru, tahun_anggaran=tahun, aktif=True, created_by=p.id, created_date=sekarang, updated_by=p.id, updated_date=sekarang)
                db.add(m)
                db.flush()  # id terisi: dapat menjadi induk jenjang/baris berikutnya
                per_kunci[kunci] = m
                dibuat[t] += 1
                induk, baru_dibuat = m, True
            if induk is None or _jenis(induk) != "RO":
                # Satker hanya untuk RO (permintaan pemilik produk); baris Program/Kegiatan/KRO tanpa Satker.
                if satker:
                    raise Galat(400, "Unit Kerja dan Satuan Kerja hanya diisi pada baris RO (kode_ro & ro terisi).")
            else:
                if baru_dibuat:
                    ro_baru[induk.id] = (no, induk.kode_ro)
                lama = satker_ada[induk.id]
                tambah = [i for i in satker if i not in lama]  # Satker baris ini yang belum tercatat di RO itu
                if bad := [nonaktif[i] for i in tambah if i in nonaktif]:
                    raise Galat(400, f"Satuan Kerja {', '.join(bad)} berstatus Nonaktif sehingga tidak dapat dipilih.")
                for i in tambah:
                    lama.append(i)
                    tautan_baru.append(MasterROSatker(master_ro_id=induk.id, satker_id=i, no_urut=len(lama)))
                if tambah and induk.id not in ro_baru:
                    induk.updated_by, induk.updated_date = p.id, sekarang
                    ro_ditambah.add(induk.id)
        except Galat as e:
            galat.append(f"Baris {no}: {e.pesan}")
        except IntegrityError:  # kode sama ditambahkan orang lain bersamaan
            db.rollback()
            raise Galat(409, "Data Master RO berubah saat import berjalan. Muat ulang halaman lalu import lagi.")

    # RO baru wajib punya minimal satu Satker dari salah satu barisnya (sama dengan Tambah).
    for ro_id, (no, kode_ro) in ro_baru.items():
        if not satker_ada[ro_id]:
            galat.append(f"Baris {no}: Unit Kerja dan Satuan Kerja RO {kode_ro} wajib diisi (minimal satu).")
    if galat:
        db.rollback()
        sisa = len(galat) - MAKS_GALAT_IMPOR
        raise Galat(400, f"Tidak ada data yang di-import karena {len(galat)} baris bermasalah. Perbaiki file lalu import lagi:\n"
                         + "\n".join(galat[:MAKS_GALAT_IMPOR]) + (f"\n… dan {sisa} kesalahan lainnya." if sisa > 0 else ""))
    db.add_all(tautan_baru)
    hasil = {"tahun_anggaran": tahun, "baris": len(data), "dibuat": {t: dibuat[t] for t in TINGKAT},
             "total_dibuat": sum(dibuat.values()), "sudah_ada": sudah_ada, "satker_diisi": len(ro_ditambah)}
    if hasil["total_dibuat"] or ro_ditambah:
        _rapikan(db)
    catat(db, request, "MASTER_RO_IMPOR", "master_ro", None, sesudah={"nama_file": file.filename, **hasil})
    db.commit()
    return hasil


@router.put("/{ro_id}")
def ubah(ro_id: uuid.UUID, data: MasterROMasuk, request: Request, db: Session = Depends(sesi_db),
         p: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Ubah kode, nama, induk, status, atau Satker pelaksana (khusus RO, minimal satu).
    Perubahan kode/nama/induk ikut diterapkan ke semua baris turunannya (kolom jenjang sampai jenis data ini), seperti
    Unit Kerja di Satuan Kerja. Tanpa perubahan = jejak tetap. Error: 400, 403, 404."""
    m = _ambil(db, ro_id)
    isi = _validasi(db, data, m.tahun_anggaran, m)  # tahun data tetap (tidak dapat dipindah lewat Ubah)
    satker_lama = _satker_ids(db, m)
    satker = _validasi_satker(db, data.tingkat, data.satker_ids, frozenset(satker_lama))
    sebelum = _isi_audit(db, m)
    jenjang = [k for t in TINGKAT[:TINGKAT.index(data.tingkat) + 1] for k in KOLOM[t]]
    berubah = {k: isi[k] for k in jenjang if getattr(m, k) != isi[k]}
    satker_berubah = satker_lama != satker
    if not berubah and m.aktif == data.aktif and not satker_berubah:
        return _respons(db, m.tahun_anggaran, m)
    sekarang = jam_db(db)
    ikut = 0
    syarat = _syarat_turunan(m)
    if berubah and syarat is not None:  # syarat dihitung dari nilai LAMA, sebelum m diubah
        ikut = db.execute(update(MasterRO).where(syarat).values(**berubah, updated_by=p.id, updated_date=sekarang)).rowcount
    for k, v in berubah.items():
        setattr(m, k, v)
    m.aktif = data.aktif
    m.updated_by, m.updated_date = p.id, sekarang
    if satker_berubah:
        _simpan_satker(db, m, satker)
    _simpan(db, data.tingkat)
    _rapikan(db)  # UPDATE menulis versi baris baru di akhir tabel → urutan fisik dirapikan lagi
    catat(db, request, "MASTER_RO_UBAH", "master_ro", m.id, sebelum=sebelum, sesudah={**_isi_audit(db, m), "turunan_ikut_diubah": ikut})
    db.commit()
    db.refresh(m)
    return _respons(db, m.tahun_anggaran, m)


@router.delete("/{ro_id}")
def hapus(ro_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
          _: Pengguna = Depends(wajib_role(REVIEWER))) -> dict:
    """Hapus permanen. Error: 403, 404; 409 bila masih punya turunan (hapus turunannya dulu)."""
    m = _ambil(db, ro_id)
    syarat = _syarat_turunan(m)
    jenis = _jenis(m)
    if syarat is not None:
        anak = TINGKAT[TINGKAT.index(jenis) + 1]
        cucu = [getattr(MasterRO, KOLOM[t][0]) == "" for t in TINGKAT[TINGKAT.index(anak) + 1:]]
        # Ditolak bila ada turunan di jenjang mana pun; pesan menyebut jumlah turunan langsung.
        if db.scalar(select(MasterRO.id).where(syarat).limit(1)):
            jumlah = db.scalar(select(func.count()).where(syarat, *cucu)) or 1
            raise Galat(409, f"{NAMA_TINGKAT[jenis]} {_kode_nama(m)[0]} masih memiliki {jumlah} {NAMA_TINGKAT[anak]} di bawahnya. "
                             f"Hapus atau pindahkan {NAMA_TINGKAT[anak]} tersebut terlebih dahulu.")
    sebelum = _isi_audit(db, m)
    db.delete(m)
    catat(db, request, "MASTER_RO_HAPUS", "master_ro", ro_id, sebelum=sebelum)
    db.commit()
    return {"ok": True}
