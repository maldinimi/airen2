"""Uji fitur menu Pengguna & Satuan Kerja: hapus, integritas data (CHECK/UNIQUE/DEFAULT), kolom jejak, kode UKE,
data awal dari dokumen "Data Satker dan Unit Kerja", hak akses Admin, dan simpan bersamaan."""
import uuid

from sqlalchemy import text

from app.db import SessionLokal


def test_hapus_pengguna_dan_satker(klien):
    admin = klien("admin", "GantiSegera!2026")
    s = admin.post("/api/satker", json={"nama": "Satker Hapus", "unit_kerja": "UK Uji"}).json()
    p = admin.post("/api/pengguna", json={"username": "akun_hapus", "roles": ["PENGUSUL"],
                                          "satker_id": s["id"], "password": "Rahasia!2026"}).json()
    # Satker masih dipakai pengguna → ditolak; non-admin tidak boleh menghapus.
    assert admin.delete(f"/api/satker/{s['id']}").status_code == 409
    assert klien("reviewer").delete(f"/api/pengguna/{p['id']}").status_code == 403
    assert admin.delete(f"/api/pengguna/{p['id']}").status_code == 200
    assert admin.delete(f"/api/satker/{s['id']}").status_code == 200
    assert admin.delete(f"/api/satker/{s['id']}").status_code == 404
    # Akun yang sudah punya jejak (login → audit log) dan akun sendiri tidak dapat dihapus.
    pengusul = next(x for x in admin.get("/api/pengguna").json() if x["username"] == "pengusul")
    klien("pengusul")
    assert admin.delete(f"/api/pengguna/{pengusul['id']}").status_code == 409
    sendiri = next(x for x in admin.get("/api/pengguna").json() if x["username"] == "admin")
    assert admin.delete(f"/api/pengguna/{sendiri['id']}").status_code == 400


def test_check_constraint_pengguna_satker(klien):
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.model import PenggunaRole
    admin = klien("admin", "GantiSegera!2026")
    s = admin.post("/api/satker", json={"nama": "Satker Cek", "unit_kerja": "UK Cek"}).json()
    assert s["unit_kerja"] == "UK Cek" and "kode" not in s
    assert s["dibuat_oleh"] == s["diubah_oleh"] == "admin"
    # Keduanya opsional (kosong disimpan ''), tetapi isian kosong yang sama tetap tidak boleh ganda.
    kosong = admin.post("/api/satker", json={"nama": "Satker Tanpa UK", "unit_kerja": "  "})
    assert kosong.status_code == 200 and kosong.json()["unit_kerja"] == ""
    assert admin.post("/api/satker", json={"nama": "Satker Tanpa UK"}).status_code == 409
    assert admin.post("/api/satker", json={"nama": "x" * 256}).status_code == 400
    # Satker yang sama di Unit Kerja yang sama → 409 (bukan 500); nama sama di Unit Kerja lain boleh.
    assert admin.put(f"/api/satker/{s['id']}", json={"nama": "BIRO PERENCANAAN", "unit_kerja": "SEKRETARIAT JENDERAL"}).status_code == 409
    assert admin.post("/api/satker", json={"nama": "BIRO PERENCANAAN", "unit_kerja": "UK Lain"}).status_code == 200
    # Kode UKE II unik bila diisi.
    assert admin.post("/api/satker", json={"kode_uke2": "01.04", "nama": "Lain"}).status_code == 409
    assert admin.post("/api/satker", json={"kode_uke2": "x" * 11}).status_code == 400
    ubah = admin.put(f"/api/satker/{s['id']}", json={"nama": "Satker Cek", "unit_kerja": "UK Baru"})
    assert ubah.status_code == 200 and ubah.json()["unit_kerja"] == "UK Baru"
    assert ubah.json()["diubah_at"] >= s["diubah_at"] and ubah.json()["dibuat_at"] == s["dibuat_at"]
    # Daftar Satker (memuat nama admin) hanya untuk Admin.
    assert klien("pengusul").get("/api/satker").status_code == 403
    # Satker Nonaktif tidak bisa dipilih untuk pengguna baru; isian terlalu panjang → 400, bukan 500.
    admin.put(f"/api/satker/{s['id']}", json={"nama": "Satker Cek", "unit_kerja": "UK Baru", "aktif": False})
    baru = {"username": "uji_nonaktif", "nama": "Uji", "roles": ["PENGUSUL"], "satker_id": s["id"], "password": "Rahasia!2026"}
    assert admin.post("/api/pengguna", json=baru).status_code == 400
    assert admin.post("/api/pengguna", json={**baru, "username": "u" * 101}).status_code == 400
    pengguna = admin.get("/api/pengguna").json()[0]
    # Database sendiri menolak nilai di luar domain, walau ditulis tanpa lewat API.
    for baris in (PenggunaRole(pengguna_id=uuid.UUID(pengguna["id"]), role="SUPERADMIN"),):
        with SessionLokal() as db, pytest.raises(IntegrityError):
            db.add(baris)
            db.commit()


def test_pengguna_default_dan_username_unik_tanpa_beda_huruf(klien):
    import pytest
    from sqlalchemy.exc import IntegrityError
    admin = klien("admin", "GantiSegera!2026")
    assert admin.post("/api/pengguna", json={"username": "PENGUSUL", "roles": ["REVIEWER"],
                                             "password": "Rahasia!2026"}).status_code == 409
    with SessionLokal() as db:
        # INSERT lewat SQL tanpa id/aktif → diisi DEFAULT database.
        aktif = db.scalar(text("INSERT INTO pengguna (username, password) VALUES ('sql_langsung', 'x') RETURNING aktif"))
        assert aktif is True
        with pytest.raises(IntegrityError):
            db.execute(text("INSERT INTO pengguna (username, password) VALUES ('SQL_LANGSUNG', 'x')"))


def test_simpan_bersamaan_jadi_409(klien, monkeypatch):
    """Dua admin menyimpan data sama di saat bersamaan: cek awal lolos, UNIQUE database menolak → 409, bukan 500."""
    from app.api import admin as modul
    admin = klien("admin", "GantiSegera!2026")
    assert admin.post("/api/satker", json={"nama": "Satker Balapan", "unit_kerja": "UK"}).status_code == 200
    monkeypatch.setattr(modul, "_validasi_satker", lambda *a, **k: None)  # tiru cek awal yang sudah lolos
    assert admin.post("/api/satker", json={"nama": " Satker Balapan ", "unit_kerja": "UK"}).status_code == 409


def test_seed_satker_sesuai_dokumen(klien):
    """56 Satker (UKE II) dari dokumen "Data Satker dan Unit Kerja", urut menurut kode, akun contoh memakai Satker asli."""
    admin = klien("admin", "GantiSegera!2026")
    daftar = admin.get("/api/satker").json()
    assert len(daftar) == 56 and len({s["unit_kerja"] for s in daftar}) == 9
    assert daftar[0].items() >= {"kode_uke1": "01", "unit_kerja": "SEKRETARIAT JENDERAL", "kode_uke2": "01.01",
                                 "nama": "BIRO HUKUM"}.items()
    assert [s["kode_uke2"] for s in daftar] == sorted(s["kode_uke2"] for s in daftar)
    assert not any(k.startswith("pejabat") for k in daftar[0])
    assert daftar[-1]["kode_uke2"] == "12.10"
    pengusul = next(p for p in admin.get("/api/pengguna").json() if p["username"] == "pengusul")
    assert pengusul["satker"]["nama"] == "BIRO PERENCANAAN"


def test_pengguna_tanpa_kolom_nama(klien):
    """Tabel pengguna tanpa kolom nama: nama tampilan (header, jejak "Dibuat Oleh") = username."""
    admin = klien("admin", "GantiSegera!2026")
    p = admin.post("/api/pengguna", json={"username": "tanpa_nama", "roles": ["REVIEWER"], "password": "Rahasia!2026"})
    assert p.status_code == 200 and "nama" not in p.json() and p.json()["dibuat_oleh"] == "admin"
    assert klien("tanpa_nama", "Rahasia!2026").get("/api/auth/saya").json()["nama"] == "tanpa_nama"


def test_referensi_satker_hanya_admin(klien):
    """Daftar resmi UKE I/UKE II (sumber pilihan form Satker) = isi dokumen; hanya untuk Admin."""
    ref = klien("admin", "GantiSegera!2026").get("/api/satker/referensi").json()
    assert len(ref) == 56 and ref[0] == {"kode_uke1": "01", "unit_kerja": "SEKRETARIAT JENDERAL", "kode_uke2": "01.04",
                                         "nama": "BIRO PERENCANAAN"}
    assert klien("reviewer").get("/api/satker/referensi").status_code == 403


def test_ubah_username(klien):
    """Username dapat diubah lewat Ubah Pengguna; username baru dipakai untuk login, bentrokan → 409."""
    admin = klien("admin", "GantiSegera!2026")
    p = admin.post("/api/pengguna", json={"username": "lama", "roles": ["REVIEWER"], "password": "Rahasia!2026"}).json()
    ubah = admin.put(f"/api/pengguna/{p['id']}", json={"username": " baru ", "roles": ["REVIEWER"]})
    assert ubah.status_code == 200 and ubah.json()["username"] == "baru"
    assert klien("baru", "Rahasia!2026").get("/api/auth/saya").json()["username"] == "baru"
    assert admin.put(f"/api/pengguna/{p['id']}", json={"username": "PENGUSUL", "roles": ["REVIEWER"]}).status_code == 409


def test_tambah_unit_kerja_saja(klien):
    """Halaman Tambah, pilihan Unit Kerja: hanya nama Unit Kerja; Unit Kerja yang sudah ada ditolak."""
    admin = klien("admin", "GantiSegera!2026")
    uk = admin.post("/api/satker", json={"unit_kerja": "UNIT KERJA UJI"})
    assert uk.status_code == 200 and uk.json()["nama"] == "" and uk.json()["unit_kerja"] == "UNIT KERJA UJI"
    assert admin.post("/api/satker", json={"unit_kerja": "UNIT KERJA UJI"}).status_code == 409
    assert admin.post("/api/satker", json={"unit_kerja": "SEKRETARIAT JENDERAL"}).status_code == 409
    sk = admin.post("/api/satker", json={"unit_kerja": "UNIT KERJA UJI", "nama": "SATUAN KERJA UJI"})
    assert sk.status_code == 200 and sk.json()["unit_kerja"] == "UNIT KERJA UJI"


def test_ubah_nama_unit_kerja_ikut_ke_satuan_kerja(klien):
    """Ubah baris Unit Kerja saja: nama baru ikut dipakai semua Satuan Kerja di bawahnya."""
    admin = klien("admin", "GantiSegera!2026")
    uk = admin.post("/api/satker", json={"unit_kerja": "UK LAMA"}).json()
    admin.post("/api/satker", json={"unit_kerja": "UK LAMA", "nama": "SATKER DI BAWAH"})
    assert admin.put(f"/api/satker/{uk['id']}", json={"unit_kerja": "UK BARU"}).status_code == 200
    daftar = {s["nama"]: s["unit_kerja"] for s in admin.get("/api/satker").json() if s["unit_kerja"] in ("UK LAMA", "UK BARU")}
    assert daftar == {"": "UK BARU", "SATKER DI BAWAH": "UK BARU"}


def test_kode_satker_dan_nonaktif(klien):
    """Format kode UKE I/UKE II & kecocokan induk dicek; Satuan Kerja dapat dinonaktifkan lalu diaktifkan lagi."""
    admin = klien("admin", "GantiSegera!2026")
    assert admin.post("/api/satker", json={"kode_uke1": "1", "unit_kerja": "UK FORMAT"}).status_code == 400
    assert admin.post("/api/satker", json={"kode_uke1": "01", "unit_kerja": "UK FORMAT"}).status_code == 409  # 01 = Setjen
    uk = admin.post("/api/satker", json={"kode_uke1": "77", "unit_kerja": "UK FORMAT"})
    assert uk.status_code == 200
    salah = {"kode_uke1": "77", "unit_kerja": "UK FORMAT", "nama": "SK FORMAT"}
    assert admin.post("/api/satker", json={**salah, "kode_uke2": "7701"}).status_code == 400
    assert admin.post("/api/satker", json={**salah, "kode_uke2": "01.99"}).status_code == 400
    sk = admin.post("/api/satker", json={**salah, "kode_uke2": "77.01"}).json()
    # Kode UKE I Unit Kerja yang Satuan Kerja-nya sudah berkode tidak dapat diubah.
    assert admin.put(f"/api/satker/{uk.json()['id']}", json={"kode_uke1": "78", "unit_kerja": "UK FORMAT"}).status_code == 400
    # Nonaktif → tidak dapat dipilih untuk pengguna baru; aktif lagi → bisa.
    nonaktif = admin.put(f"/api/satker/{sk['id']}", json={**salah, "kode_uke2": "77.01", "aktif": False})
    assert nonaktif.status_code == 200 and nonaktif.json()["aktif"] is False
    baru = {"username": "uji_sk_nonaktif", "roles": ["PENGUSUL"], "satker_id": sk["id"], "password": "Rahasia!2026"}
    assert admin.post("/api/pengguna", json=baru).status_code == 400
    admin.put(f"/api/satker/{sk['id']}", json={**salah, "kode_uke2": "77.01", "aktif": True})
    assert admin.post("/api/pengguna", json=baru).status_code == 200
