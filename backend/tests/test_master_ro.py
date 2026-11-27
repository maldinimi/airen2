"""Uji menu Master RO: CRUD berjenjang Program → Kegiatan → KRO → RO, aturan induk & kode, hapus, dan hak akses
(khusus Reviewer), format kode sesuai SEB No. 6/2025, dan referensi KRO Lampiran II.
Master RO tidak di-seed (data Renja hanya dari input/impor menu ini), jadi tiap uji mulai dari tabel kosong."""
import pytest
from sqlalchemy import text

from app.db import engine

# Kolom Renja Unit Eselon I/II & Prioritas tidak disimpan di master_ro (database mengikuti tabel daftar).
_DIHAPUS = ("kode_eselon1", "unit_eselon1", "kode_eselon2", "unit_eselon2", "prioritas")


def _satker_aktif(c, n: int = 1) -> list[str]:
    """`n` Satuan Kerja (Eselon II) Aktif pertama dari menu Satuan Kerja (seed)."""
    return [s["id"] for s in c.get("/api/satker").json() if s["nama"] and s["aktif"]][:n]


def _ta() -> int:
    """Tahun Anggaran uji = tahun berjalan (bawaan bilah atas)."""
    from app.api.master_ro import tahun_berjalan
    return tahun_berjalan()


def _reviewer(klien, satker: bool = True):
    """Klien Reviewer untuk uji Master RO: tambah/ubah tanpa `tahun_anggaran` otomatis diberi tahun berjalan (Master RO
    per tahun), dan tanpa `satker_ids` otomatis diberi satu Satker (wajib sejak Revisi 7; `satker=False` untuk uji aturan
    Satker sendiri), agar uji lain tetap fokus pada aturannya sendiri."""
    c = klien("reviewer")
    bawaan = {"tahun_anggaran": _ta(), **({"satker_ids": _satker_aktif(c)} if satker else {})}
    post, put = c.post, c.put

    def isi(url: str, kw: dict) -> dict:
        if url.startswith("/api/master-ro") and isinstance(kw.get("json"), dict):
            kw["json"] = {**bawaan, **kw["json"]}
        return kw
    c.post = lambda url, **kw: post(url, **isi(url, kw))  # type: ignore[method-assign]
    c.put = lambda url, **kw: put(url, **isi(url, kw))  # type: ignore[method-assign]
    return c


def test_master_ro_satker_pelaksana(klien):
    """Revisi 7: Unit Kerja (Eselon I) + Satuan Kerja (Eselon II) pelaksana KHUSUS RO, minimal satu, urut isian, tanpa
    dobel; Satker Nonaktif hanya boleh tetap dipakai data lama; disimpan di tabel penghubung master_ro_satker (FK ke
    satker, nama lewat JOIN). Program/Kegiatan/KRO tanpa Satker (isian diabaikan)."""
    from app.db import SessionLokal
    rv = _reviewer(klien, satker=False)
    s1, s2, s3 = _satker_aktif(rv, 3)
    post = lambda **x: rv.post("/api/master-ro", json=x)  # noqa: E731
    # Program/Kegiatan/KRO: tanpa Satker; isian Satker diabaikan.
    prog = post(tingkat="PROGRAM", kode="WA", nama="Program A", satker_ids=[s1])
    assert prog.status_code == 200 and prog.json()["satker"] == [], prog.text
    keg = post(tingkat="KEGIATAN", induk_id=prog.json()["id"], kode="1234", nama="Kegiatan A").json()
    kro = post(tingkat="KRO", induk_id=keg["id"], kode="EBA", nama="KRO A").json()
    assert keg["satker"] == [] and kro["satker"] == []
    isi = {"tingkat": "RO", "induk_id": kro["id"], "kode": "001", "nama": "RO A"}
    r = post(**isi)
    assert r.status_code == 400 and "minimal satu" in r.json()["pesan"]
    assert post(**isi, satker_ids=[s1, s1]).status_code == 400
    assert post(**isi, satker_ids=["00000000-0000-0000-0000-000000000000"]).status_code == 400

    ro = post(**isi, satker_ids=[s2, s1])
    assert ro.status_code == 200, ro.text
    ro = ro.json()
    assert [s["id"] for s in ro["satker"]] == [s2, s1]  # urut isian form = urut bullet
    assert all(s["unit_kerja"] and s["nama"] for s in ro["satker"])
    assert next(x for x in rv.get("/api/master-ro").json() if x["id"] == ro["id"])["satker"] == ro["satker"]

    # Ubah: ganti/urut ulang; minimal satu tetap berlaku.
    ubah = rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "satker_ids": [s1, s3]})
    assert ubah.status_code == 200 and [s["id"] for s in ubah.json()["satker"]] == [s1, s3]
    assert rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "satker_ids": []}).status_code == 400

    # Satker Nonaktif: tidak dapat dipilih untuk data baru, tetapi data yang sudah memakainya tetap dapat disimpan.
    with SessionLokal() as db:
        db.execute(text("UPDATE satker SET aktif = false WHERE id = :i"), {"i": s3})
        db.commit()
    assert post(**{**isi, "kode": "002", "nama": "RO B"}, satker_ids=[s3]).status_code == 400
    assert rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "nama": "RO A2", "satker_ids": [s1, s3]}).status_code == 200

    # Database: tabel penghubung master_ro_satker (id Satker urut isian), nama Unit Kerja/Satuan Kerja lewat JOIN satker;
    # master_ro sendiri tanpa kolom Satker. Hapus RO ikut menghapus barisnya (CASCADE).
    nama = {s["id"]: (s["unit_kerja"], s["nama"]) for s in rv.get("/api/satker").json()}
    with SessionLokal() as db:
        kolom = set(db.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'master_ro'")))
        gabung = db.execute(text("SELECT s.unit_kerja, s.satuan_kerja FROM master_ro_satker x JOIN satker s ON s.id = x.satker_id "
                                 "WHERE x.master_ro_id = :i ORDER BY x.no_urut"), {"i": ro["id"]}).all()
        assert db.scalar(text("SELECT count(*) FROM master_ro_satker x JOIN master_ro r ON r.id = x.master_ro_id "
                              "WHERE r.kode_ro = ''")) == 0
    assert not kolom & {"unit_kerja", "satuan_kerja"}
    assert [tuple(g) for g in gabung] == [nama[s1], nama[s3]]
    assert rv.delete(f"/api/master-ro/{ro['id']}").status_code == 200
    with SessionLokal() as db:
        assert db.scalar(text("SELECT count(*) FROM master_ro_satker WHERE master_ro_id = :i"), {"i": ro["id"]}) == 0


def test_master_ro_crud_berjenjang(klien):
    rv = _reviewer(klien)
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
    rv = _reviewer(klien)
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
    rv = _reviewer(klien)
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
    rv = _reviewer(klien)
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
        db.execute(text("INSERT INTO master_ro (id, tahun_anggaran, kode_program, program) VALUES (gen_random_uuid(), 2026, 'a1', 'Program X')"))
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


_JUDUL = ("kode_program", "program", "kode_kegiatan", "kegiatan", "kode_kro", "kro", "kode_ro", "ro", "unit_kerja", "satuan_kerja")


def _nama_satker(c, n: int = 1) -> list[tuple[str, str]]:
    """(Unit Kerja, Satuan Kerja) `n` Satker Aktif pertama, untuk isi kolom unit_kerja & satuan_kerja file impor."""
    return [(s["unit_kerja"], s["nama"]) for s in c.get("/api/satker").json() if s["nama"] and s["aktif"]][:n]


def _impor(c, isi: bytes, nama: str = "master-ro.xlsx", tahun: int | None = None):
    """Import Excel ke Tahun Anggaran `tahun` (bawaan: tahun berjalan, seperti pilihan bilah atas)."""
    import io
    return c.post("/api/master-ro/impor", files={"file": (nama, io.BytesIO(isi), "application/vnd.ms-excel")},
                  data={"tahun_anggaran": str(tahun or _ta())})


def test_master_ro_impor_excel(klien):
    """Impor Excel: baris lengkap membuat Program/Kegiatan/KRO/RO yang belum ada, memakai yang sudah ada, kode teks
    bebas disimpan apa adanya, impor ulang aman, dan satu baris salah = tidak ada yang tersimpan."""
    rv = _reviewer(klien)
    sk = _nama_satker(rv)[0]  # Satker pelaksana (wajib untuk data baru)
    berkas = _xlsx(
        _JUDUL,
        ("ZZ", "Program Contoh", 1234, "Kegiatan Contoh", "", "", "", "", "", ""),         # sampai Kegiatan; kode angka
        ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", 1, "RO Satu", *sk),  # RO 1 tetap "1"
        (None,) * 10,                                                                       # baris kosong dilewati
        ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", "Z01", "RO Dua", *sk),
    )
    r = _impor(rv, berkas)
    assert r.status_code == 200, r.text
    assert r.json() == {"tahun_anggaran": _ta(), "baris": 3, "dibuat": {"PROGRAM": 1, "KEGIATAN": 1, "KRO": 1, "RO": 2}, "total_dibuat": 5, "sudah_ada": 5,
                        "satker_diisi": 0}
    daftar = {d["kode_lengkap"]: d for d in rv.get("/api/master-ro").json()}
    assert set(daftar) == {"ZZ", "ZZ.1234", "ZZ.1234.ABC", "ZZ.1234.ABC.1", "ZZ.1234.ABC.Z01"}
    assert daftar["ZZ.1234.ABC.1"]["induk_id"] == daftar["ZZ.1234.ABC"]["id"] and daftar["ZZ"]["diubah_oleh"] == "reviewer"

    # Impor ulang file yang sama: tidak ada yang dibuat.
    assert _impor(rv, berkas).json()["total_dibuat"] == 0

    # Kode teks bebas disimpan apa adanya (huruf kecil & simbol tidak diubah), sama dengan Tambah manual.
    bebas = _impor(rv, _xlsx(_JUDUL, ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", "ro-a/1", "RO Bebas", *sk)))
    assert bebas.status_code == 200, bebas.text
    assert any(d["kode_ro"] == "ro-a/1" for d in rv.get("/api/master-ro").json())
    rv.delete(f"/api/master-ro/{next(d['id'] for d in rv.get('/api/master-ro').json() if d['kode_ro'] == 'ro-a/1')}")

    # Semua-atau-tidak: baris 2 valid, baris 3 & 4 salah → tidak ada yang tersimpan, kesalahan per nomor baris Excel.
    salah = _impor(rv, _xlsx(_JUDUL,
                             ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh", "002", "RO Tiga", *sk),
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


def test_master_ro_impor_satker(klien):
    """Impor Excel kolom unit_kerja & satuan_kerja (Revisi 7): beberapa Satker dipisah ";" / baris baru, dicocokkan ke
    menu Satuan Kerja tanpa membedakan huruf besar/kecil, wajib untuk data baru; data lama tanpa Satker dilengkapi,
    Satker berbeda ditolak."""
    from app.db import SessionLokal
    rv = _reviewer(klien)
    (u1, s1), (u2, s2), (u3, s3) = _nama_satker(rv, 3)
    jalur = ("ZZ", "Program Contoh", "1234", "Kegiatan Contoh", "ABC", "KRO Contoh")
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "001", "RO Satu", f"{u1.lower()}; {u2}", f"{s1.upper()}\n{s2}")))
    assert r.status_code == 200, r.text
    ro = next(d for d in rv.get("/api/master-ro").json() if d["kode_ro"] == "001")
    assert [(s["unit_kerja"], s["nama"]) for s in ro["satker"]] == [(u1, s1), (u2, s2)]  # nama resmi, urut file
    # Induk (Program/Kegiatan/KRO) yang ikut dibuat otomatis tanpa Satker: Satker khusus RO.
    assert next(d for d in rv.get("/api/master-ro").json() if d["tingkat"] == "PROGRAM")["satker"] == []

    pesan = _impor(rv, _xlsx(_JUDUL, (*jalur, "002", "RO Dua", u1, ""),
                             (*jalur, "003", "RO Tiga", u1, "Satker Tidak Ada"),
                             (*jalur, "004", "RO Empat", "", ""),
                             (*jalur, "005", "RO Lima", f"{u1};{u1}", f"{s1};{s1}"),
                             ("", "", "", "", "", "", "", "", u1, s1),
                             (*jalur, "", "", u1, s1))).json()["pesan"]
    assert "Baris 2: Jumlah Unit Kerja (1) dan Satuan Kerja (0) harus sama" in pesan
    assert f'Baris 3: Satuan Kerja "Satker Tidak Ada" dengan Unit Kerja "{u1}" tidak ada' in pesan
    assert "Baris 4: Unit Kerja dan Satuan Kerja RO 004 wajib diisi" in pesan
    assert f"Baris 5: Satuan Kerja {s1} ditulis lebih dari sekali" in pesan
    assert "Baris 6: Unit Kerja dan Satuan Kerja hanya diisi pada baris RO" in pesan
    assert "Baris 7: Unit Kerja dan Satuan Kerja hanya diisi pada baris RO" in pesan  # baris KRO

    # RO yang sudah ada: Satker dari file DITAMBAHKAN (yang lama tidak dihapus); yang sudah tercatat = aman.
    nama_ro = lambda i: [s["nama"] for s in next(d for d in rv.get("/api/master-ro").json() if d["id"] == i)["satker"]]  # noqa: E731
    with SessionLokal() as db:
        db.execute(text("DELETE FROM master_ro_satker WHERE master_ro_id = :i"), {"i": ro["id"]})
        db.commit()
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "001", "RO Satu", u3, s3)))
    assert r.status_code == 200 and r.json()["satker_diisi"] == 1 and r.json()["total_dibuat"] == 0, r.text
    assert nama_ro(ro["id"]) == [s3]
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "001", "RO Satu", u1, s1)))
    assert r.status_code == 200 and r.json()["satker_diisi"] == 1, r.text
    assert nama_ro(ro["id"]) == [s3, s1]
    assert _impor(rv, _xlsx(_JUDUL, (*jalur, "001", "RO Satu", u3, s3))).json()["satker_diisi"] == 0

    # Bebas: RO yang sama di beberapa baris → Satker digabung urut baris; RO baru boleh mendapat Satker dari baris mana
    # saja (baris pertamanya kosong pun boleh); campuran ";" dan baris terpisah juga boleh.
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "010", "RO Sepuluh", "", ""),
                         (*jalur, "010", "RO Sepuluh", u2, s2),
                         (*jalur, "010", "RO Sepuluh", f"{u1}; {u2}", f"{s1}; {s2}")))
    assert r.status_code == 200 and r.json()["dibuat"]["RO"] == 1 and r.json()["satker_diisi"] == 0, r.text
    assert nama_ro(next(d["id"] for d in rv.get("/api/master-ro").json() if d["kode_ro"] == "010")) == [s2, s1]

    # Impor ulang tetap aman walau Satker yang sudah dipakai RO kini Nonaktif; Nonaktif ditolak bila baru dipasang.
    with SessionLokal() as db:
        db.execute(text("UPDATE satker SET aktif = false WHERE unit_kerja = :u AND satuan_kerja = :s"), {"u": u3, "s": s3})
        db.commit()
    ulang = _impor(rv, _xlsx(_JUDUL, (*jalur, "001", "RO Satu", u3, s3)))
    assert ulang.status_code == 200 and ulang.json()["total_dibuat"] == 0, ulang.text
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "006", "RO Enam", u3, s3)))
    assert r.status_code == 400 and "Nonaktif" in r.json()["pesan"]

    # Satker tanpa Unit Kerja (pilihan "Tanpa Unit Kerja" di form): sel unit_kerja kosong.
    with SessionLokal() as db:
        db.execute(text("INSERT INTO satker (id, unit_kerja, satuan_kerja) VALUES (gen_random_uuid(), '', 'Satker Mandiri')"))
        db.commit()
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "007", "RO Tujuh", "", "satker mandiri"),
                         (*jalur, "008", "RO Delapan", f"; {u1}", f"Satker Mandiri; {s1}")))
    assert r.status_code == 200, r.text
    daftar = {d["kode_ro"]: d for d in rv.get("/api/master-ro").json()}
    assert [(s["unit_kerja"], s["nama"]) for s in daftar["007"]["satker"]] == [("", "Satker Mandiri")]
    assert [(s["unit_kerja"], s["nama"]) for s in daftar["008"]["satker"]] == [("", "Satker Mandiri"), (u1, s1)]
    r = _impor(rv, _xlsx(_JUDUL, (*jalur, "009", "RO Sembilan", u1, "")))
    assert r.status_code == 400 and "Jumlah Unit Kerja (1) dan Satuan Kerja (0)" in r.json()["pesan"]


def test_master_ro_ikut_perubahan_menu_satker(klien):
    """Satker Master RO lewat JOIN: ganti nama Satuan Kerja / Unit Kerja di menu Satuan Kerja otomatis tampil di RO;
    hapus atau kosongkan nama Satker yang masih dipakai RO ditolak 409."""
    rv = _reviewer(klien, satker=False)
    unit = rv.post("/api/satker", json={"unit_kerja": "UNIT UJI"}).json()
    sk = rv.post("/api/satker", json={"unit_kerja": "UNIT UJI", "nama": "Satker Uji"}).json()
    lain = next(i for i in _satker_aktif(rv, 2) if i != sk["id"])  # Satker seed, bukan Satker uji
    post = lambda **x: rv.post("/api/master-ro", json=x).json()  # noqa: E731
    prog = post(tingkat="PROGRAM", kode="WA", nama="Program A")
    keg = post(tingkat="KEGIATAN", induk_id=prog["id"], kode="1234", nama="Kegiatan A")
    kro = post(tingkat="KRO", induk_id=keg["id"], kode="EBA", nama="KRO A")
    ro = post(tingkat="RO", induk_id=kro["id"], kode="001", nama="RO A", satker_ids=[lain, sk["id"]])
    satker_ro = lambda: [(s["unit_kerja"], s["nama"], s["id"]) for s in  # noqa: E731
                         next(d for d in rv.get("/api/master-ro").json() if d["id"] == ro["id"])["satker"]]
    asli = satker_ro()[0]

    # Ganti nama Satuan Kerja → RO ikut (id tetap tertaut), Satker lain di RO yang sama tidak berubah.
    r = rv.put(f"/api/satker/{sk['id']}", json={"unit_kerja": "UNIT UJI", "nama": "Satker Uji Baru"})
    assert r.status_code == 200, r.text
    assert satker_ro() == [asli, ("UNIT UJI", "Satker Uji Baru", sk["id"])]
    # Ganti nama Unit Kerja (baris Unit Kerja saja) → Satuan Kerja di bawahnya & RO ikut.
    assert rv.put(f"/api/satker/{unit['id']}", json={"unit_kerja": "UNIT UJI BARU"}).status_code == 200
    assert satker_ro() == [asli, ("UNIT UJI BARU", "Satker Uji Baru", sk["id"])]

    # Masih dipakai RO: hapus & kosongkan nama Satuan Kerja ditolak; setelah dilepas dari RO, boleh dihapus.
    r = rv.delete(f"/api/satker/{sk['id']}")
    assert r.status_code == 409 and "masih dipakai 1 RO" in r.json()["pesan"]
    assert rv.put(f"/api/satker/{sk['id']}", json={"unit_kerja": "UNIT UJI BARU"}).status_code == 409
    assert rv.put(f"/api/master-ro/{ro['id']}", json={**ro, "satker_ids": [lain]}).status_code == 200
    assert rv.delete(f"/api/satker/{sk['id']}").status_code == 200


def test_master_ro_per_tahun_anggaran(klien):
    """Master RO per Tahun Anggaran (pilihan bilah atas): daftar/tambah/impor per tahun, kode yang sama boleh di tahun
    berbeda, induk harus setahun, tahun tidak pindah saat Ubah, dan pilihan form Pengajuan mengikuti tahunnya."""
    rv = _reviewer(klien)
    ta, depan = _ta(), _ta() + 1
    post = lambda **x: rv.post("/api/master-ro", json=x)  # noqa: E731
    ini = post(tingkat="PROGRAM", kode="WA", nama="Program A").json()
    lain = post(tingkat="PROGRAM", kode="WA", nama="Program A Tahun Depan", tahun_anggaran=depan)
    assert lain.status_code == 200 and lain.json()["tahun_anggaran"] == depan, lain.text  # kode sama, tahun beda
    lain = lain.json()
    assert post(tingkat="PROGRAM", kode="WA", nama="Program X", tahun_anggaran=depan).status_code == 400  # ganda di tahun itu
    assert ini["tahun_anggaran"] == ta

    # Daftar per tahun (bawaan = tahun berjalan).
    assert [d["id"] for d in rv.get(f"/api/master-ro?tahun={depan}").json()] == [lain["id"]]
    assert ini["id"] in {d["id"] for d in rv.get("/api/master-ro").json()}
    assert lain["id"] not in {d["id"] for d in rv.get("/api/master-ro").json()}

    # Induk tahun lain tidak sah; tahun wajib & dalam ±2; Ubah tidak memindah tahun.
    r = post(tingkat="KEGIATAN", induk_id=ini["id"], kode="1234", nama="Kegiatan", tahun_anggaran=depan)
    assert r.status_code == 400 and "induk" in r.json()["pesan"]
    assert post(tingkat="PROGRAM", kode="WZ", nama="Program Z", tahun_anggaran=ta + 3).status_code == 400
    r = klien("reviewer").post("/api/master-ro", json={"tingkat": "PROGRAM", "kode": "WY", "nama": "Program Y"})
    assert r.status_code == 400 and "Tahun Anggaran wajib" in r.json()["pesan"]
    ubah = rv.put(f"/api/master-ro/{lain['id']}", json={**lain, "nama": "Program A2", "tahun_anggaran": ta})
    assert ubah.status_code == 200 and ubah.json()["tahun_anggaran"] == depan

    # Import ke tahun pilihan: data tahun lain tidak dianggap "sudah ada".
    sk = _nama_satker(rv)[0]
    berkas = _xlsx(_JUDUL, ("WB", "Program B", "1234", "Kegiatan B", "ABC", "KRO B", "001", "RO B", *sk))
    r = _impor(rv, berkas, tahun=depan)
    assert r.status_code == 200 and r.json()["tahun_anggaran"] == depan and r.json()["total_dibuat"] == 4, r.text
    assert _impor(rv, berkas).json()["total_dibuat"] == 4  # tahun berjalan: dibuat terpisah
    assert _impor(rv, berkas, tahun=depan).json()["total_dibuat"] == 0  # impor ulang ke tahun yang sama: aman
    assert _impor(rv, berkas, tahun=ta + 3).status_code == 400

    # Form Pengajuan: pohon pilihan = Master RO tahun yang diminta.
    pohon = lambda t: {g["kode"] for g in rv.get(f"/api/usulan/opsi/pengajuan?tahun={t}").json()["hierarki"]}  # noqa: E731
    assert "WB" in pohon(depan) and "WA" in pohon(depan)
    assert pohon(ta + 2) == set()
