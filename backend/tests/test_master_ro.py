"""Uji menu Master RO: CRUD berjenjang Program → Kegiatan → KRO → RO, aturan induk & kode, hapus, dan hak akses
(khusus Reviewer), format kode sesuai SEB No. 6/2025, dan referensi KRO Lampiran II.
Master RO tidak di-seed (data Renja hanya dari input/impor menu ini), jadi tiap uji mulai dari tabel kosong."""
import pytest
from sqlalchemy import text

from app.db import engine

# Kolom Renja Unit Eselon I/II & Prioritas tidak disimpan di master_ro (database mengikuti tabel daftar).
_DIHAPUS = ("kode_eselon1", "unit_eselon1", "kode_eselon2", "unit_eselon2", "prioritas")


def test_master_ro_crud_berjenjang(klien):
    rv = klien("reviewer")
    prog = rv.post("/api/master-ro", json={"tingkat": "PROGRAM", "kode": " WA ", "nama": "Program Dukungan Manajemen"})
    assert prog.status_code == 200, prog.text
    prog = prog.json()
    assert prog["kode"] == "WA" and prog["induk"] is None and prog["diubah_oleh"] == "reviewer" and prog["aktif"]
    keg = rv.post("/api/master-ro", json={"tingkat": "KEGIATAN", "induk_id": prog["id"], "kode": "1234", "nama": "Kegiatan A"}).json()
    kro = rv.post("/api/master-ro", json={"tingkat": "KRO", "induk_id": keg["id"], "kode": "EBA", "nama": "Layanan Dukungan"}).json()
    ro = rv.post("/api/master-ro", json={"tingkat": "RO", "induk_id": kro["id"], "kode": "994", "nama": "Layanan Perkantoran"}).json()
    assert ro["kode_lengkap"] == "WA.1234.EBA.994" and ro["induk"] == {"kode": "WA.1234.EBA", "nama": "Layanan Dukungan"}

    # Induk wajib & harus tingkat tepat di atasnya; kode wajib, unik di bawah induk yang sama.
    assert rv.post("/api/master-ro", json={"tingkat": "RO", "kode": "001", "nama": "x"}).status_code == 400
    assert rv.post("/api/master-ro", json={"tingkat": "RO", "induk_id": keg["id"], "kode": "001", "nama": "x"}).status_code == 400
    assert rv.post("/api/master-ro", json={"tingkat": "RO", "induk_id": kro["id"], "kode": "994", "nama": "x"}).status_code == 400
    assert rv.post("/api/master-ro", json={"tingkat": "PROGRAM", "kode": "WA", "nama": "x"}).status_code == 400
    assert rv.post("/api/master-ro", json={"tingkat": "RO", "induk_id": kro["id"], "kode": " ", "nama": "x"}).status_code == 400
    assert rv.post("/api/master-ro", json={"tingkat": "LAIN", "kode": "X", "nama": "x"}).status_code == 400
    # Kode RO sama boleh di KRO lain.
    kro2 = rv.post("/api/master-ro", json={"tingkat": "KRO", "induk_id": keg["id"], "kode": "EBB", "nama": "KRO B"}).json()
    assert rv.post("/api/master-ro", json={"tingkat": "RO", "induk_id": kro2["id"], "kode": "994", "nama": "RO B"}).status_code == 200

    # Ubah: kode/nama/induk/status; tingkat tidak dapat diubah.
    ubah = rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "nama": "Layanan Perkantoran Baru", "aktif": False})
    assert ubah.status_code == 200 and ubah.json()["nama"] == "Layanan Perkantoran Baru" and ubah.json()["aktif"] is False
    assert rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "tingkat": "KRO"}).status_code == 400
    assert rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "induk_id": kro2["id"]}).status_code == 400  # 994 sudah ada di KRO B
    # Induk Nonaktif tidak dapat dipilih untuk data baru.
    rv.put(f"/api/master-ro/{kro2['id']}", json={**kro2, "aktif": False})
    assert rv.post("/api/master-ro", json={"tingkat": "RO", "induk_id": kro2["id"], "kode": "001", "nama": "x"}).status_code == 400

    daftar = rv.get("/api/master-ro").json()
    assert sorted(d["tingkat"] for d in daftar) == ["KEGIATAN", "KRO", "KRO", "PROGRAM", "RO", "RO"]
    # Urut bawaan: yang paling baru ditambahkan paling atas (RO B 994 dibuat terakhir, Program pertama).
    dibuat = [d["dibuat_at"] for d in daftar]
    assert dibuat == sorted(dibuat, reverse=True)
    assert (daftar[0]["tingkat"], daftar[0]["kode"]) == ("RO", "994") and daftar[-1]["id"] == prog["id"]
    # Database juga: urutan fisik (SELECT tanpa ORDER BY, seperti pgAdmin "View Data") = urutan di layar.
    with engine.connect() as c:
        assert [str(i) for i in c.scalars(text("SELECT id FROM master_ro"))] == [d["id"] for d in daftar]
    assert next(d for d in daftar if d["id"] == kro["id"])["jumlah_turunan"] == 1

    # Hapus: ditolak selama masih punya turunan; dari bawah ke atas berhasil.
    assert rv.delete(f"/api/master-ro/{prog['id']}").status_code == 409
    assert rv.delete(f"/api/master-ro/{ro['id']}").status_code == 200
    assert rv.delete(f"/api/master-ro/{ro['id']}").status_code == 404
    assert rv.delete(f"/api/master-ro/{kro['id']}").status_code == 200
    assert rv.get("/api/audit").status_code == 403  # audit tetap khusus Admin
    aksi = {a["aksi"] for a in klien("admin", "GantiSegera!2026").get("/api/audit").json()["data"]}
    assert {"MASTER_RO_TAMBAH", "MASTER_RO_UBAH", "MASTER_RO_HAPUS"} <= aksi


def test_master_ro_tabel_datar_dan_ubah_berantai(klien):
    """Tabel master_ro berbentuk datar seperti satker; ubah kode/nama/induk ikut memperbarui baris turunannya."""
    from sqlalchemy import text

    from app.db import SessionLokal
    rv = klien("reviewer")
    tambah = lambda **x: rv.post("/api/master-ro", json=x).json()  # noqa: E731
    p1 = tambah(tingkat="PROGRAM", kode="WA", nama="Program A")
    p2 = tambah(tingkat="PROGRAM", kode="WB", nama="Program B")
    keg = tambah(tingkat="KEGIATAN", induk_id=p1["id"], kode="1234", nama="Kegiatan A")
    kro = tambah(tingkat="KRO", induk_id=keg["id"], kode="EBA", nama="KRO A")
    tambah(tingkat="RO", induk_id=kro["id"], kode="994", nama="RO A")
    with SessionLokal() as db:
        baris = db.execute(text("SELECT kode_program, program, kode_kegiatan, kegiatan, kode_kro, kro, kode_ro, ro FROM master_ro "
                                "ORDER BY kode_program, kode_kegiatan, kode_kro, kode_ro")).all()
    assert ("WA", "Program A", "1234", "Kegiatan A", "EBA", "KRO A", "994", "RO A") in [tuple(b) for b in baris]
    assert tuple(baris[0]) == ("WA", "Program A", "", "", "", "", "", "")
    # Ganti nama Program → semua turunan ikut; pindahkan Kegiatan ke Program lain → KRO & RO ikut pindah.
    assert rv.put(f"/api/master-ro/{p1['id']}", json={**p1, "nama": "Program A Baru"}).status_code == 200
    assert rv.put(f"/api/master-ro/{keg['id']}", json={**keg, "induk_id": p2["id"]}).status_code == 200
    daftar = {d["kode_lengkap"]: d for d in rv.get("/api/master-ro").json()}
    assert set(daftar) == {"WA", "WB", "WB.1234", "WB.1234.EBA", "WB.1234.EBA.994"}
    assert daftar["WB.1234.EBA.994"]["induk"] == {"kode": "WB.1234.EBA", "nama": "KRO A"}
    assert daftar["WB"]["jumlah_turunan"] == 1 and daftar["WA"]["jumlah_turunan"] == 0
    with SessionLokal() as db:
        assert db.scalar(text("SELECT count(*) FROM master_ro WHERE program = 'Program A'")) == 0


def test_master_ro_hanya_reviewer(klien):
    for c in (klien("pengusul"), klien("admin", "GantiSegera!2026")):
        assert c.get("/api/master-ro").status_code == 403
        assert c.post("/api/master-ro", json={"tingkat": "PROGRAM", "kode": "X", "nama": "x"}).status_code == 403
    assert klien().get("/api/master-ro").status_code == 401


def test_master_ro_kode_teks_bebas(klien):
    """Kode teks bebas (tanpa batasan huruf/angka, disimpan apa adanya, maks. 50 karakter); nama Program diawali
    "Program"; nama RO tidak boleh sama dalam satu KRO (SEB 6/2025 Lampiran I)."""
    rv = klien("reviewer")
    post = lambda **x: rv.post("/api/master-ro", json=x)  # noqa: E731
    for kode in ("W1", "wax-01", "Program 1.2"):
        r = post(tingkat="PROGRAM", kode=kode, nama="Program X")
        assert r.status_code == 200 and r.json()["kode"] == kode, r.text
    r = post(tingkat="PROGRAM", kode="X" * 51, nama="Program X")
    assert r.status_code == 400 and "maksimal 50" in r.json()["pesan"]
    assert post(tingkat="PROGRAM", kode="  ", nama="Program X").status_code == 400
    r = post(tingkat="PROGRAM", kode="AC", nama="Belanja Kebutuhan")
    assert r.status_code == 400 and "Program" in r.json()["pesan"]
    prog = post(tingkat="PROGRAM", kode="GH", nama="program Komunikasi Publik dan Media").json()
    assert post(tingkat="KEGIATAN", induk_id=prog["id"], kode="45A1", nama="K").status_code == 200
    keg = post(tingkat="KEGIATAN", induk_id=prog["id"], kode="4511", nama="Kegiatan A").json()
    assert post(tingkat="KRO", induk_id=keg["id"], kode="EB1", nama="K").status_code == 200
    kro = post(tingkat="KRO", induk_id=keg["id"], kode="PBM", nama="Kebijakan Bidang Pelayanan Publik").json()
    # KRO PN & Non-PN boleh bernama sama di satu Kegiatan; KRO di luar Lampiran II tetap boleh (Renja masih memakainya).
    assert post(tingkat="KRO", induk_id=keg["id"], kode="ABM", nama="Kebijakan Bidang Pelayanan Publik").status_code == 200
    kro2 = post(tingkat="KRO", induk_id=keg["id"], kode="UBA", nama="Fasilitasi dan Pembinaan Pemerintah Daerah")
    assert kro2.status_code == 200
    for i, kode in enumerate(("01", "0011", "0-1")):
        assert post(tingkat="RO", induk_id=kro["id"], kode=kode, nama=f"R{i}").status_code == 200
    ro = post(tingkat="RO", induk_id=kro["id"], kode="z01", nama="Rekomendasi Kebijakan").json()
    assert ro["kode"] == "z01"
    r = post(tingkat="RO", induk_id=kro["id"], kode="002", nama="rekomendasi kebijakan")
    assert r.status_code == 400 and "Nama RO" in r.json()["pesan"]
    assert post(tingkat="RO", induk_id=kro2.json()["id"], kode="001", nama="Rekomendasi Kebijakan").status_code == 200
    ro2 = post(tingkat="RO", induk_id=kro["id"], kode="002", nama="RO Lain").json()
    assert rv.put(f"/api/master-ro/{ro2['id']}", json={**ro2, "nama": "Rekomendasi Kebijakan"}).status_code == 400
    assert rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "aktif": False}).status_code == 200  # nama sendiri tidak dihitung


def test_master_ro_referensi_kro(klien):
    """Daftar KRO Lampiran II untuk saran di form: kode PN menjadi baris sendiri, urut kode; khusus Reviewer.
    `app/data_kro.py` opsional (tidak di-commit): isi dicek terhadap daftar yang dimuat API (kosong bila berkas tidak ada)."""
    from app.api.master_ro import KRO
    ref = klien("reviewer").get("/api/master-ro/referensi-kro")
    assert ref.status_code == 200
    assert len(ref.json()) == len(KRO) + sum(1 for k in KRO if k[1])
    assert [k["kode"] for k in ref.json()] == sorted(k["kode"] for k in ref.json())
    assert not any(k["kode"] == "" for k in ref.json())
    for non_pn, pn, nama, satuan in KRO[:5]:
        assert {"kode": non_pn, "nama": nama, "satuan": satuan, "pn": False} in ref.json()
        if pn:
            assert {"kode": pn, "nama": nama, "satuan": satuan, "pn": True} in ref.json()
    assert klien("pengusul").get("/api/master-ro/referensi-kro").status_code == 403


def test_master_ro_tanpa_kolom_unit_prioritas(klien):
    """Kolom database = kolom tabel di layar: Unit Eselon I/II & Prioritas tidak ada lagi; isian unit lama dari klien
    diabaikan (bukan error), dan tidak ada CHECK format kode (kode teks bebas)."""
    from app.db import SessionLokal
    with SessionLokal() as db:
        kolom = set(db.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'master_ro'")))
        cek = set(db.scalars(text("SELECT conname FROM pg_constraint WHERE conrelid = 'master_ro'::regclass AND contype = 'c'")))
    assert not kolom & set(_DIHAPUS)
    assert "ck_master_ro_format" not in cek and "ck_master_ro_unit" not in cek
    rv = klien("reviewer")
    prog = rv.post("/api/master-ro", json={"tingkat": "PROGRAM", "kode": "GH", "nama": "Program Komunikasi Publik dan Media"}).json()
    r = rv.post("/api/master-ro", json={"tingkat": "KEGIATAN", "induk_id": prog["id"], "kode": "4511", "nama": "K",
                                        "kode_unit": "01", "unit": "Sekretariat Jenderal"})
    assert r.status_code == 200 and not any(k in r.json() for k in (*_DIHAPUS, "kode_unit", "unit"))


def test_master_ro_tipe_dan_format_database(klien):
    """Kolom kode VARCHAR(50) teks bebas (database menerima huruf kecil/angka), nama VARCHAR(255)."""
    from app.db import SessionLokal
    with SessionLokal() as db:
        panjang = dict(db.execute(text("SELECT column_name, character_maximum_length FROM information_schema.columns "
                                       "WHERE table_name = 'master_ro' AND data_type = 'character varying'")).all())
        assert {k: panjang[k] for k in ("kode_program", "kode_kegiatan", "kode_kro", "kode_ro")} == {
            "kode_program": 50, "kode_kegiatan": 50, "kode_kro": 50, "kode_ro": 50}
        assert {panjang[k] for k in ("program", "kegiatan", "kro", "ro")} == {255}
        db.execute(text("INSERT INTO master_ro (id, kode_program, program) VALUES (gen_random_uuid(), 'a1', 'Program X')"))
        db.rollback()


def _xlsx(*baris) -> bytes:
    """File Excel uji: baris pertama = judul kolom, sisanya data."""
    import io

    from openpyxl import Workbook
    wb = Workbook()
    for b in baris:
        wb.active.append(list(b))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_JUDUL = ("kode_program", "program", "kode_kegiatan", "kegiatan", "kode_kro", "kro", "kode_ro", "ro")


def _impor(c, isi: bytes, nama: str = "master-ro.xlsx"):
    import io
    return c.post("/api/master-ro/impor", files={"file": (nama, io.BytesIO(isi), "application/vnd.ms-excel")})


def test_master_ro_impor_excel(klien):
    """Impor Excel: baris lengkap membuat Program/Kegiatan/KRO/RO yang belum ada, memakai yang sudah ada, kode teks
    bebas disimpan apa adanya, impor ulang aman, dan satu baris salah = tidak ada yang tersimpan."""
    rv = klien("reviewer")
    berkas = _xlsx(
        _JUDUL,
        ("ZZ", "Program Contoh", 1234, "Kegiatan Contoh", "", "", "", ""),            # sampai Kegiatan; kode angka
        ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", 1, "RO Satu"),  # RO 1 tetap "1"
        (None,) * 8,                                                                   # baris kosong dilewati
        ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", "Z01", "RO Dua"),
    )
    r = _impor(rv, berkas)
    assert r.status_code == 200, r.text
    assert r.json() == {"baris": 3, "dibuat": {"PROGRAM": 1, "KEGIATAN": 1, "KRO": 1, "RO": 2}, "total_dibuat": 5, "sudah_ada": 5}
    daftar = {d["kode_lengkap"]: d for d in rv.get("/api/master-ro").json()}
    assert set(daftar) == {"ZZ", "ZZ.1234", "ZZ.1234.ABC", "ZZ.1234.ABC.1", "ZZ.1234.ABC.Z01"}
    assert daftar["ZZ.1234.ABC.1"]["induk_id"] == daftar["ZZ.1234.ABC"]["id"] and daftar["ZZ"]["diubah_oleh"] == "reviewer"

    # Impor ulang file yang sama: tidak ada yang dibuat.
    assert _impor(rv, berkas).json()["total_dibuat"] == 0

    # Kode teks bebas disimpan apa adanya (huruf kecil & simbol tidak diubah), sama dengan Tambah manual.
    bebas = _impor(rv, _xlsx(_JUDUL, ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", "ro-a/1", "RO Bebas")))
    assert bebas.status_code == 200, bebas.text
    assert any(d["kode_ro"] == "ro-a/1" for d in rv.get("/api/master-ro").json())
    rv.delete(f"/api/master-ro/{next(d['id'] for d in rv.get('/api/master-ro').json() if d['kode_ro'] == 'ro-a/1')}")

    # Semua-atau-tidak: baris 2 valid, baris 3 & 4 salah → tidak ada yang tersimpan, kesalahan per nomor baris Excel.
    salah = _impor(rv, _xlsx(_JUDUL,
                             ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", "002", "RO Tiga"),
                             ("ZZ", "Program Contoh", "", "", "ABD", "KRO Lompat", "", ""),
                             ("ZZ", "Program Nama Lain", "", "", "", "", "", "")))
    assert salah.status_code == 400
    pesan = salah.json()["pesan"]
    assert "2 baris bermasalah" in pesan and "Baris 3: KRO diisi tetapi Kegiatan kosong" in pesan
    assert 'Baris 4: Nama Program ZZ berbeda dengan data yang sudah ada ("Program Contoh")' in pesan
    assert len(rv.get("/api/master-ro").json()) == 5
    # Aturan tambah manual tetap berlaku (panjang kode, nama Program).
    pesan = _impor(rv, _xlsx(_JUDUL, ("Y" * 51, "Program X", "", "", "", "", "", ""),
                             ("YY", "Bukan program", "", "", "", "", "", ""))).json()["pesan"]
    assert "Baris 2: Kode Program maksimal 50 karakter" in pesan and "Baris 3: Nama Program diawali" in pesan

    # File tidak valid.
    assert "Kolom berikut tidak ada" in _impor(rv, _xlsx(("kode_program", "program"), ("ZZ", "Program Contoh"))).json()["pesan"]
    assert "tidak berisi data" in _impor(rv, _xlsx(_JUDUL)).json()["pesan"]
    assert _impor(rv, b"bukan excel").status_code == 400
    assert _impor(rv, berkas, "data.csv").json()["pesan"] == "File harus berformat Excel (.xlsx)."
    # File berbaris sangat banyak dibaca bertahap & dihentikan di batas, bukan dimuat semua ke memori.
    banyak = _impor(rv, _xlsx(_JUDUL, *[("ZZ", "Program Contoh", "", "", "", "", "", "")] * 5001))
    assert banyak.status_code == 400 and "maksimal 5000 baris" in banyak.json()["pesan"]
    from app.api import master_ro
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(master_ro, "MAKS_BARIS_DIBACA", 10)
        kosong = _impor(rv, _xlsx(_JUDUL, *[(None,) * 8] * 20, ("ZZ", "Program Contoh", "", "", "", "", "", "")))
        assert kosong.status_code == 400 and "terlalu banyak baris" in kosong.json()["pesan"]
    # Khusus Reviewer.
    for c in (klien("pengusul"), klien("admin", "GantiSegera!2026")):
        assert _impor(c, berkas).status_code == 403
    aksi = [a for a in klien("admin", "GantiSegera!2026").get("/api/audit").json()["data"] if a["aksi"] == "MASTER_RO_IMPOR"]
    assert len(aksi) == 3  # hanya impor yang berhasil yang dicatat
