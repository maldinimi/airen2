"""Endpoint administrasi: pengguna & role, Satker, node AI, audit log."""
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.akses import ADMIN, PENGUSUL, REVIEWER, wajib_role
from app.audit import catat
from app.data_satker import SATKER
from app.db import sesi_db
from app.galat import Galat
from app.keamanan import hash_password, hash_token, token_baru, validasi_password
from app.model import AuditLog, NodeAI, Pengguna, PenggunaRole, Satker, Sesi

router = APIRouter(prefix="/api", tags=["administrasi"])
ROLE_SAH = {PENGUSUL, REVIEWER, ADMIN}
PESAN_SATKER_GANDA = "Satuan Kerja tersebut sudah ada pada Unit Kerja yang sama, atau Kode UKE II sudah dipakai."
PESAN_KODE_GANDA = "Kode UKE II sudah dipakai Satuan Kerja lain."


class PenggunaMasuk(BaseModel):
    username: str
    roles: list[str]
    satker_id: uuid.UUID | None = None
    aktif: bool = True
    password: str | None = None  # wajib saat membuat; saat ubah = reset password bila diisi


class SatkerMasuk(BaseModel):
    """Isian Satker; semua opsional. UKE I = Unit Kerja (Eselon I), UKE II = Satuan Kerja (Eselon II)."""
    model_config = ConfigDict(str_strip_whitespace=True)  # spasi di awal/akhir dibuang; spasi saja = kosong
    kode_uke1: str = ""
    unit_kerja: str = ""
    kode_uke2: str = ""
    nama: str = ""
    aktif: bool = True

    def isian(self) -> dict:
        return self.model_dump(exclude={"aktif"})


class NodeMasuk(BaseModel):
    nama: str


def _jam_db(db: Session) -> datetime:
    return db.scalar(select(func.now()))


def _jejak(db: Session, x: Pengguna | Satker) -> dict:
    """Siapa & kapan data dibuat/terakhir diubah (kolom created_by/create_date/update_by/update_date). None = sistem."""
    def nama(pid):
        return db.get(Pengguna, pid).nama if pid else None
    return {"dibuat_oleh": nama(x.created_by), "dibuat_at": x.create_date.isoformat(),
            "diubah_oleh": nama(x.update_by), "diubah_at": x.update_date.isoformat()}


def _satker(db: Session, s: Satker) -> dict:
    return {"id": str(s.id), "kode_uke1": s.kode_uke1, "unit_kerja": s.unit_kerja, "kode_uke2": s.kode_uke2,
            "nama": s.nama, "aktif": s.aktif, **_jejak(db, s)}


def _validasi_satker(db: Session, data: SatkerMasuk, satker_id: uuid.UUID | None = None) -> None:
    """Error 400 bila isian terlalu panjang; 409 bila kode UKE II dipakai Satker lain atau Satuan Kerja yang sama
    sudah ada di Unit Kerja itu."""
    if data.kode_uke1 and not re.fullmatch(r"\d{2}", data.kode_uke1):
        raise Galat(400, "Kode UKE I harus 2 digit angka, mis. 01.")
    if data.kode_uke2 and not re.fullmatch(r"\d{2}\.\d{2}", data.kode_uke2):
        raise Galat(400, "Kode UKE II harus berformat NN.NN, mis. 01.04.")
    if data.kode_uke1 and data.kode_uke2 and data.kode_uke2[:2] != data.kode_uke1:
        raise Galat(400, f"Kode UKE II harus diawali kode Unit Kerja induknya ({data.kode_uke1}.xx).")
    # Mengubah baris Unit Kerja saja: Satuan Kerja di bawahnya (masih bernama Unit Kerja lama) ikut diganti, jadi
    # bukan bentrokan.
    lama = db.get(Satker, satker_id) if satker_id else None
    anak_sendiri = Satker.unit_kerja == lama.unit_kerja if lama is not None and not lama.nama and lama.unit_kerja else None
    # Satu Kode UKE I = satu Unit Kerja (kode tidak boleh dipakai Unit Kerja lain).
    kueri = select(Satker.id).where(Satker.kode_uke1 == data.kode_uke1, Satker.unit_kerja != data.unit_kerja, Satker.id != satker_id)
    if data.kode_uke1 and db.scalar((kueri if anak_sendiri is None else kueri.where(~anak_sendiri)).limit(1)):
        raise Galat(409, "Kode UKE I sudah dipakai Unit Kerja lain.")
    if max(len(data.unit_kerja), len(data.nama)) > 255:
        raise Galat(400, "Unit Kerja dan Satuan Kerja maksimal 255 karakter.")
    if data.kode_uke2 and db.scalar(select(Satker.id).where(Satker.kode_uke2 == data.kode_uke2, Satker.id != satker_id)):
        raise Galat(409, PESAN_KODE_GANDA)
    # Unit Kerja saja (tanpa Satuan Kerja): ditolak bila Unit Kerja itu sudah tercatat di baris lain, kecuali
    # Satuan Kerja di bawahnya sendiri saat mengubah.
    if not data.nama and data.unit_kerja:
        kueri = select(Satker.id).where(Satker.unit_kerja == data.unit_kerja, Satker.id != satker_id)
        if db.scalar((kueri if anak_sendiri is None else kueri.where(~anak_sendiri | (Satker.nama == ""))).limit(1)):
            raise Galat(409, "Unit Kerja tersebut sudah ada.")
    if db.scalar(select(Satker.id).where(Satker.nama == data.nama, Satker.unit_kerja == data.unit_kerja,
                                         Satker.id != satker_id)):
        raise Galat(409, PESAN_SATKER_GANDA)


def _simpan(db: Session, pesan_bentrok: str) -> None:
    """flush ke database; pelanggaran UNIQUE (dua admin menyimpan data sama bersamaan) → 409, bukan 500."""
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Galat(409, pesan_bentrok)


def _pengguna(db: Session, p: Pengguna) -> dict:
    return {"id": str(p.id), "username": p.username, "roles": sorted(p.daftar_role), "aktif": p.aktif,
            "satker": {"id": str(p.satker.id), "nama": p.satker.nama, "unit_kerja": p.satker.unit_kerja} if p.satker else None,
            "last_login_at": p.last_login_at.isoformat() if p.last_login_at else None, **_jejak(db, p)}


def _validasi_pengguna(db: Session, data: PenggunaMasuk, satker_lama: uuid.UUID | None = None) -> None:
    """Error 400 bila isian tidak valid. `satker_lama` = Satker pengguna saat ini (boleh tetap dipakai walau Nonaktif)."""
    if not data.username.strip():
        raise Galat(400, "Username wajib diisi.")
    if len(data.username.strip()) > 100:
        raise Galat(400, "Username maksimal 100 karakter.")
    if not data.roles or not set(data.roles) <= ROLE_SAH:
        raise Galat(400, "Pilih minimal satu role yang valid.")
    if PENGUSUL in data.roles and data.satker_id is None:
        raise Galat(400, "Pengusul wajib terhubung ke Satuan Kerja.")
    if data.satker_id:
        s = db.get(Satker, data.satker_id)
        if s is None:
            raise Galat(400, "Satuan Kerja tidak ditemukan.")
        if not s.aktif and s.id != satker_lama:
            raise Galat(400, "Satuan Kerja nonaktif tidak dapat dipilih.")
    if data.password and (pesan := validasi_password(data.password)):
        raise Galat(400, pesan)


@router.get("/pengguna")
def daftar_pengguna(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    return [_pengguna(db, p) for p in db.scalars(select(Pengguna).order_by(Pengguna.username))]


@router.post("/pengguna")
def buat_pengguna(data: PenggunaMasuk, request: Request, db: Session = Depends(sesi_db), admin: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    _validasi_pengguna(db, data)
    if not data.password:
        raise Galat(400, "Password wajib diisi.")
    if db.scalar(select(Pengguna.id).where(func.lower(Pengguna.username) == data.username.strip().lower())):
        raise Galat(409, "Username sudah dipakai.")
    sekarang = _jam_db(db)
    p = Pengguna(username=data.username.strip(), satker_id=data.satker_id, aktif=data.aktif,
                 password_hash=hash_password(data.password), created_by=admin.id, create_date=sekarang,
                 update_by=admin.id, update_date=sekarang)
    p.roles = [PenggunaRole(role=r) for r in sorted(set(data.roles))]
    db.add(p)
    _simpan(db, "Username sudah dipakai.")
    catat(db, request, "PENGGUNA_BUAT", "pengguna", p.id, sesudah=_pengguna(db, p))
    db.commit()
    return _pengguna(db, p)


@router.put("/pengguna/{pengguna_id}")
def ubah_pengguna(pengguna_id: uuid.UUID, data: PenggunaMasuk, request: Request, db: Session = Depends(sesi_db),
                  admin: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Ubah username/role/Satker/status aktif; isi `password` untuk reset password. Menonaktifkan akun mencabut sesinya.
    Error 409 bila username baru sudah dipakai akun lain (tanpa membedakan huruf besar/kecil)."""
    p = db.get(Pengguna, pengguna_id)
    if p is None:
        raise Galat(404, "Pengguna tidak ditemukan.")
    _validasi_pengguna(db, data, p.satker_id)
    if p.id == admin.id and (ADMIN not in data.roles or not data.aktif):
        raise Galat(400, "Anda tidak dapat mencabut role Admin atau menonaktifkan akun sendiri.")
    username = data.username.strip()
    if db.scalar(select(Pengguna.id).where(func.lower(Pengguna.username) == username.lower(), Pengguna.id != p.id)):
        raise Galat(409, "Username sudah dipakai.")
    sebelum = _pengguna(db, p)
    p.username, p.satker_id, p.aktif = username, data.satker_id, data.aktif
    p.update_by, p.update_date = admin.id, _jam_db(db)
    # Hanya selisihnya: mengganti seluruh list memicu INSERT sebelum DELETE → bentrok primary key.
    p.roles = [r for r in p.roles if r.role in data.roles] + \
        [PenggunaRole(role=r) for r in sorted(set(data.roles) - p.daftar_role)]
    if data.password:
        p.password_hash = hash_password(data.password)
    if data.password or not data.aktif:
        db.query(Sesi).filter(Sesi.pengguna_id == p.id).delete()
    _simpan(db, "Username sudah dipakai.")  # indeks unik lower(username) menolak bentrokan yang lolos cek di atas
    db.refresh(p)
    catat(db, request, "PENGGUNA_UBAH", "pengguna", p.id, sebelum=sebelum, sesudah={**_pengguna(db, p), "reset_password": bool(data.password)})
    db.commit()
    return _pengguna(db, p)


@router.delete("/pengguna/{pengguna_id}")
def hapus_pengguna(pengguna_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                   admin: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Hapus permanen akun yang belum punya jejak data. Error 404 bila tidak ada, 400 untuk akun sendiri,
    409 bila sudah dirujuk (usulan, review, audit log, dst.) — akun seperti itu cukup dinonaktifkan."""
    p = db.get(Pengguna, pengguna_id)
    if p is None:
        raise Galat(404, "Pengguna tidak ditemukan.")
    if p.id == admin.id:
        raise Galat(400, "Anda tidak dapat menghapus akun sendiri.")
    sebelum = _pengguna(db, p)
    try:
        db.query(Sesi).filter(Sesi.pengguna_id == p.id).delete()
        db.delete(p)
        db.flush()
    except IntegrityError:
        # Andalkan FK database: setiap tabel yang merujuk pengguna otomatis menolak, tanpa daftar manual.
        db.rollback()
        raise Galat(409, "Pengguna sudah memiliki riwayat aktivitas sehingga tidak dapat dihapus.")
    catat(db, request, "PENGGUNA_HAPUS", "pengguna", pengguna_id, sebelum=sebelum)
    db.commit()
    return {"ok": True}


@router.get("/satker/referensi")
def referensi_satker(_: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    """Daftar resmi UKE I/UKE II dari dokumen "Data Satker dan Unit Kerja" (app/data_satker.py), urut dokumen —
    sumber pilihan Unit Kerja & Satuan Kerja di form Tambah/Ubah Satker."""
    return [{k: s[k] for k in ("kode_uke1", "unit_kerja", "kode_uke2", "nama")} for s in SATKER]


@router.get("/satker")
def daftar_satker(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    """Daftar Satker untuk menu Satker & pilihan di form Pengguna (Admin saja: memuat nama pembuat/pengubah)."""
    return [_satker(db, s) for s in db.scalars(select(Satker).order_by(Satker.kode_uke1, Satker.kode_uke2, Satker.unit_kerja, Satker.nama))]


@router.post("/satker")
def buat_satker(data: SatkerMasuk, request: Request, db: Session = Depends(sesi_db), admin: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    _validasi_satker(db, data)
    sekarang = _jam_db(db)
    s = Satker(**data.isian(), aktif=data.aktif,
               created_by=admin.id, create_date=sekarang, update_by=admin.id, update_date=sekarang)
    db.add(s)
    _simpan(db, PESAN_SATKER_GANDA)
    catat(db, request, "SATKER_BUAT", "satker", s.id, sesudah=_satker(db, s))
    db.commit()
    return _satker(db, s)


@router.put("/satker/{satker_id}")
def ubah_satker(satker_id: uuid.UUID, data: SatkerMasuk, request: Request, db: Session = Depends(sesi_db),
                admin: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    s = db.get(Satker, satker_id)
    if s is None:
        raise Galat(404, "Satuan Kerja tidak ditemukan.")
    _validasi_satker(db, data, s.id)
    sebelum = _satker(db, s)
    sekarang = _jam_db(db)
    # Mengganti nama Unit Kerja (baris Unit Kerja saja) → Satuan Kerja di bawahnya ikut, agar satu Unit Kerja tidak
    # tercatat dengan dua nama berbeda (query WHERE unit_kerja = ... tetap mendapatkan semuanya).
    ikut = 0
    if not s.nama and not data.nama and s.unit_kerja and data.unit_kerja and \
            (s.unit_kerja, s.kode_uke1) != (data.unit_kerja, data.kode_uke1):
        anak = select(Satker.id).where(Satker.unit_kerja == s.unit_kerja, Satker.id != s.id)
        if data.kode_uke1 != s.kode_uke1 and db.scalar(anak.where(Satker.kode_uke2 != "").limit(1)):
            raise Galat(400, "Kode UKE I tidak dapat diubah karena sudah dipakai Kode UKE II Satuan Kerja di bawahnya.")
        ikut = db.execute(update(Satker).where(Satker.unit_kerja == s.unit_kerja, Satker.id != s.id)
                          .values(unit_kerja=data.unit_kerja, kode_uke1=data.kode_uke1, update_by=admin.id,
                                  update_date=sekarang)).rowcount
    for kolom, nilai in data.isian().items():
        setattr(s, kolom, nilai)
    s.aktif = data.aktif
    s.update_by, s.update_date = admin.id, sekarang
    _simpan(db, PESAN_SATKER_GANDA)
    catat(db, request, "SATKER_UBAH", "satker", s.id, sebelum=sebelum, sesudah={**_satker(db, s), "satuan_kerja_ikut_diubah": ikut})
    db.commit()
    return _satker(db, s)


@router.delete("/satker/{satker_id}")
def hapus_satker(satker_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db),
                 _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Hapus permanen Satker. Error 404 bila tidak ada, 409 bila masih dipakai pengguna atau usulan."""
    s = db.get(Satker, satker_id)
    if s is None:
        raise Galat(404, "Satuan Kerja tidak ditemukan.")
    sebelum = _satker(db, s)
    try:
        db.delete(s)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise Galat(409, "Satuan Kerja masih dipakai oleh pengguna atau usulan sehingga tidak dapat dihapus. Pindahkan dulu pengguna ke Satuan Kerja lain.")
    catat(db, request, "SATKER_HAPUS", "satker", satker_id, sebelum=sebelum)
    db.commit()
    return {"ok": True}


@router.get("/node-ai")
def daftar_node(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> list[dict]:
    return [{"id": str(n.id), "nama": n.nama, "aktif": n.aktif, "jarak_jauh": n.token_hash is not None,
             "terakhir_terlihat": n.terakhir_terlihat.isoformat() if n.terakhir_terlihat else None, "info": n.info}
            for n in db.scalars(select(NodeAI).order_by(NodeAI.nama))]


@router.post("/node-ai")
def daftarkan_node(data: NodeMasuk, request: Request, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Daftarkan node AI jarak jauh. Token hanya ditampilkan SEKALI; simpan di `.env` node (NODE_TOKEN)."""
    nama = data.nama.strip()
    if not nama or db.scalar(select(NodeAI.id).where(NodeAI.nama == nama)):
        raise Galat(400, "Nama node kosong atau sudah dipakai.")
    token = token_baru()
    n = NodeAI(nama=nama, token_hash=hash_token(token), aktif=True)
    db.add(n)
    db.flush()
    catat(db, request, "NODE_DAFTAR", "node_ai", n.id, sesudah={"nama": nama})
    db.commit()
    return {"id": str(n.id), "nama": nama, "token": token}


@router.post("/node-ai/{node_id}/cabut")
def cabut_node(node_id: uuid.UUID, request: Request, db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN))) -> dict:
    """Cabut akses node: token tidak lagi diterima dan worker node berhenti mengambil job."""
    n = db.get(NodeAI, node_id)
    if n is None:
        raise Galat(404, "Node tidak ditemukan.")
    n.aktif = False
    catat(db, request, "NODE_CABUT", "node_ai", n.id, sebelum={"nama": n.nama})
    db.commit()
    return {"ok": True}


@router.get("/audit")
def audit(db: Session = Depends(sesi_db), _: Pengguna = Depends(wajib_role(ADMIN)), pengguna_id: uuid.UUID | None = None,
          aksi: str | None = None, entitas: str | None = None, dari: datetime | None = None, sampai: datetime | None = None,
          halaman: int = Query(1, ge=1), per_halaman: int = Query(50, ge=1, le=200)) -> dict:
    """Audit log dengan filter pengguna, aksi, entitas, rentang tanggal."""
    kueri = select(AuditLog)
    if pengguna_id:
        kueri = kueri.where(AuditLog.pengguna_id == pengguna_id)
    if aksi:
        kueri = kueri.where(AuditLog.aksi == aksi)
    if entitas:
        kueri = kueri.where(AuditLog.entitas == entitas)
    if dari:
        kueri = kueri.where(AuditLog.at >= dari)
    if sampai:
        kueri = kueri.where(AuditLog.at <= sampai)
    total = db.scalar(select(func.count()).select_from(kueri.subquery()))
    baris = db.scalars(kueri.order_by(AuditLog.at.desc()).offset((halaman - 1) * per_halaman).limit(per_halaman)).all()
    nama = {p.id: p.nama for p in db.scalars(select(Pengguna).where(Pengguna.id.in_({b.pengguna_id for b in baris if b.pengguna_id})))}
    return {"total": total, "data": [{
        "id": str(b.id), "at": b.at.isoformat(), "pengguna": nama.get(b.pengguna_id), "aksi": b.aksi, "entitas": b.entitas,
        "entitas_id": b.entitas_id, "data_sebelum": b.data_sebelum, "data_sesudah": b.data_sesudah, "ip": b.ip} for b in baris],
        "aksi": db.scalars(select(AuditLog.aksi).distinct().order_by(AuditLog.aksi)).all()}
