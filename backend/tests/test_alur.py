"""Uji integrasi alur PRD §5 ujung ke ujung (AI tiruan): buat usulan → ajukan → hasil AI → override →
finalkan → revisi → riwayat; plus invarian rujukan, konsistensi (fingerprint), hak akses, versioning, offline."""
import socket
import uuid

from sqlalchemy import select, update

from app.db import SessionLokal
from app.model import Elemen, Panduan, Review, Rujukan
from tests.conftest import RAB_CONTOH, TOR_CONTOH, buat_pdf, jalankan_antrean, unggah

TOR = buat_pdf(TOR_CONTOH)
RAB = buat_pdf(["RINCIAN ANGGARAN BIAYA"], RAB_CONTOH)


def _usulan_diajukan(klien, ajukan=True):
    p = klien("pengusul")
    r = unggah(p, tor=TOR, rab=RAB, tahun_anggaran=2027, kode_ro="1234.ABC", nama_ro="Layanan Digital", ajukan=ajukan)
    assert r.status_code == 200, r.text
    return p, r.json()


def test_alur_lengkap(klien):
    pengusul, u = _usulan_diajukan(klien)
    assert u["status"] == "ANTRE"
    assert jalankan_antrean() >= 1

    rv = pengusul.get(f"/api/review/{pengusul.get(f'/api/usulan/{u['id']}').json()['review_id']}").json()
    assert rv["status"] == "SELESAI" and rv["tampilan"] == "pengusul" and not rv["final"]
    assert rv["revisi"]["status"] == "MENUNGGU_VERIFIKASI"
    # Label dihitung kode dari item (§7.1)
    semua = all(i["ai_terpenuhi"] for i in rv["item"])
    assert rv["label"]["ai"] == ("LOLOS" if semua else "TIDAK_LOLOS")
    assert rv["kategori"]["ai"]["kode"] in {"K1", "K2", "K3", "K4"}
    assert rv["rekomendasi"]["TOR"] and rv["rekomendasi"]["RAB"]
    # Item terpenuhi wajib punya bukti; semua rujukan menunjuk halaman & kutipan nyata (E3)
    for i in rv["item"]:
        if i["ai_terpenuhi"]:
            assert any(r["peran"] == "bukti_dokumen" for r in i["rujukan"])
    with SessionLokal() as db:
        for r, e in db.execute(select(Rujukan, Elemen).join(Elemen, Elemen.id == Rujukan.elemen_id)).all():
            assert r.kutipan in e.teks and e.halaman >= 1

    # Reviewer override item → label dihitung ulang; pengusul belum melihat override
    reviewer = klien("reviewer")
    item = rv["item"][0]
    nilai = "TIDAK_TERPENUHI" if item["terpenuhi"] else "TERPENUHI"
    assert reviewer.post(f"/api/review/{rv['id']}/override", json={"target": "ITEM", "checklist_item_id": item["id"], "nilai": nilai, "alasan": ""}).status_code == 400
    d = reviewer.post(f"/api/review/{rv['id']}/override", json={"target": "ITEM", "checklist_item_id": item["id"], "nilai": nilai, "alasan": "Bukti kurang"}).json()
    assert d["item"][0]["diubah"] and d["item"][0]["ai_terpenuhi"] == item["ai_terpenuhi"]  # hasil AI tetap (O2)
    assert pengusul.get(f"/api/review/{rv['id']}").json()["item"][0]["diubah"] is False  # override belum terlihat Pengusul
    # Batal override (O5)
    d = reviewer.post(f"/api/override/{d['item'][0]['override']['id']}/batal").json()
    assert not d["item"][0]["diubah"]
    # Override label tidak konsisten → peringatan; kategori override
    d = reviewer.post(f"/api/review/{rv['id']}/override", json={"target": "LABEL", "nilai": "TIDAK_LOLOS" if d["label"]["final"] == "LOLOS" else "LOLOS", "alasan": "Pertimbangan reviewer"}).json()
    assert d["label"]["tidak_konsisten"]
    d = reviewer.post(f"/api/review/{rv['id']}/override", json={"target": "LABEL", "nilai": "TIDAK_LOLOS", "alasan": "Dikembalikan"}).json() \
        if d["label"]["final"] == "LOLOS" else d
    k4 = next(k for k in d["kategori"]["pilihan"] if k["kode"] == "K4")
    if d["kategori"]["final"]["kode"] != "K4":
        d = reviewer.post(f"/api/review/{rv['id']}/override", json={"target": "KATEGORI", "nilai": k4["id"], "alasan": "Tidak terkait tusi"}).json()
    reviewer.put(f"/api/review/{rv['id']}/catatan", json={"dokumen": "UMUM", "teks": "Perbaiki indikator."})
    # Pengusul tidak dapat override/finalkan
    assert pengusul.post(f"/api/review/{rv['id']}/finalkan").status_code == 403

    d = reviewer.post(f"/api/review/{rv['id']}/finalkan").json()
    assert d["final"] and d["label"]["final"] == "TIDAK_LOLOS" and d["kategori"]["final"]["kode"] == "K4"
    # Terkunci (O7)
    assert reviewer.post(f"/api/review/{rv['id']}/override", json={"target": "LABEL", "nilai": "LOLOS", "alasan": "x"}).status_code == 409
    # Pengusul kini melihat hasil final + catatan, berdampingan dengan hasil AI
    lihat = pengusul.get(f"/api/review/{rv['id']}").json()
    assert lihat["final"] and lihat["catatan"][0]["teks"] == "Perbaiki indikator." and lihat["label"]["ai"] is not None
    baris = pengusul.get(f"/api/usulan/{u['id']}").json()
    assert baris["status"] == "TIDAK_LOLOS" and baris["kategori_final"]["diteruskan"] is False

    # Tidak boleh dihapus setelah direview; boleh revisi (RAB saja) → ajukan → hasil identik disalin? (TOR sama, RAB beda → tidak)
    assert pengusul.delete(f"/api/usulan/{u['id']}").status_code == 409
    rab2 = buat_pdf(["RINCIAN ANGGARAN BIAYA REVISI"], RAB_CONTOH + [["Konsumsi", "5", "OK", "50.000"]])
    r2 = unggah(pengusul, f"/api/usulan/{u['id']}/revisi", rab=rab2, ajukan=True).json()
    assert r2["revisi_nomor"] == 2 and r2["tor"]["file_id"] == u["tor"]["file_id"] and r2["rab"]["file_id"] != u["rab"]["file_id"]
    jalankan_antrean()
    riwayat = pengusul.get(f"/api/usulan/{u['id']}/riwayat").json()
    assert len(riwayat["revisi"]) == 2 and len(riwayat["perbandingan"]["kolom"]) == 2
    assert riwayat["revisi"][1]["rab"]["diganti"] and not riwayat["revisi"][1]["tor"]["diganti"]


def test_konsistensi_fingerprint_hasil_identik(klien):
    """Dokumen yang sama persis + acuan sama → hasil AI disalin, sama persis (PRD §8 Akurasi)."""
    pengusul, u1 = _usulan_diajukan(klien)
    r = unggah(pengusul, tor=TOR, rab=RAB, tahun_anggaran=2027, kode_ro="9999.XYZ", nama_ro="Duplikat", ajukan=True)
    jalankan_antrean()
    a = pengusul.get(f"/api/review/{pengusul.get(f'/api/usulan/{u1['id']}').json()['review_id']}").json()
    b = pengusul.get(f"/api/review/{pengusul.get(f'/api/usulan/{r.json()['id']}').json()['review_id']}").json()
    assert b.get("disalin_dari_revisi") == 1 or a.get("disalin_dari_revisi") == 1
    ringkas = lambda d: ([(i["kode"], i["ai_terpenuhi"], [(x["halaman"], x["kutipan"]) for x in i["rujukan"]]) for i in d["item"]],
                         d["label"]["ai"], d["kategori"]["ai"]["kode"])  # noqa: E731
    assert ringkas(a) == ringkas(b)


def test_hak_akses(klien):
    pengusul, u = _usulan_diajukan(klien, ajukan=False)
    lain = klien("pengusul_b")
    assert lain.get(f"/api/usulan/{u['id']}").status_code == 403
    assert lain.get(f"/api/file/{u['tor']['file_id']}").status_code == 404
    assert lain.post(f"/api/usulan/{u['id']}/ajukan").status_code == 403
    assert all(x["id"] != u["id"] for x in lain.get("/api/usulan").json()["data"])
    assert pengusul.get(f"/api/file/{u['tor']['file_id']}").status_code == 200
    reviewer = klien("reviewer")
    assert reviewer.get(f"/api/usulan/{u['id']}").status_code == 200
    assert unggah(reviewer, tor=TOR, rab=RAB, tahun_anggaran=2027, kode_ro="X", nama_ro="Y").status_code == 403
    for c in (pengusul, reviewer):
        assert c.get("/api/pengguna").status_code == 403
        assert c.post("/api/checklist/versi", json={"item": []}).status_code == 403
        assert c.get("/api/audit").status_code == 403
        assert c.put("/api/panduan/00000000-0000-0000-0000-000000000000", data={"judul": "x", "aktif": "false"}).status_code == 403
    anonim = klien()
    assert anonim.get("/api/usulan").status_code == 401
    assert anonim.get(f"/api/file/{u['tor']['file_id']}").status_code == 401
    tanpa_csrf = klien("pengusul")
    tanpa_csrf.headers.pop("X-CSRF-Token")
    assert tanpa_csrf.post(f"/api/usulan/{u['id']}/ajukan").status_code == 403
    # Draf boleh dihapus pengusul
    assert pengusul.delete(f"/api/usulan/{u['id']}").status_code == 200


def test_validasi_unggahan(klien):
    p = klien("pengusul")
    r = unggah(p, tor=b"bukan pdf sama sekali", rab=RAB, tahun_anggaran=2027, kode_ro="A", nama_ro="B")
    assert r.status_code == 400 and "PDF" in r.json()["pesan"]


def test_versioning_tidak_mengubah_review_lama(klien):
    pengusul, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rid = pengusul.get(f"/api/usulan/{u['id']}").json()["review_id"]
    sebelum = pengusul.get(f"/api/review/{rid}").json()
    admin = klien("admin", "GantiSegera!2026")
    ck = admin.get("/api/checklist").json()["aktif"]
    baru = [{**i, "judul": i["judul"] + " (diubah)"} for i in ck["item"][1:]]  # hapus item pertama, ubah sisanya
    v2 = admin.post("/api/checklist/versi", json={"catatan": "uji", "item": baru}).json()
    assert v2["nomor"] == ck["nomor"] + 1
    kat = admin.get("/api/kategori").json()["aktif"]
    admin.post("/api/kategori/versi", json={"item": [{**k, "definisi": k["definisi"] + " X"} for k in kat["item"]]})
    sesudah = pengusul.get(f"/api/review/{rid}").json()
    assert [(i["kode"], i["judul"], i["kriteria"]) for i in sesudah["item"]] == [(i["kode"], i["judul"], i["kriteria"]) for i in sebelum["item"]]
    assert sesudah["acuan"]["checklist_versi"]["nomor"] == ck["nomor"]
    lama = admin.get(f"/api/checklist/versi/{ck['id']}").json()
    assert len(lama["item"]) == len(ck["item"]) and not lama["aktif"]
    # Seed kategori persis PRD C1
    k1 = admin.get(f"/api/kategori/versi/{kat['id']}").json()["item"]
    assert [k["kode"] for k in k1] == ["K1", "K2", "K3", "K4"] and k1[3]["diteruskan"] is False
    assert k1[1]["definisi"].startswith("RO prioritas yang ditetapkan secara resmi oleh Menteri")


def test_panduan_berversi_dan_dipakai_review(klien):
    import io
    admin = klien("admin", "GantiSegera!2026")
    pdf = buat_pdf(["Pasal 5", "(1) Indikator keluaran wajib memuat target kuantitatif dan satuan.",
                    "(2) Honor narasumber paling tinggi Rp1.700.000 per orang jam."])
    assert admin.post("/api/panduan", files={"file": ("pmk.pdf", io.BytesIO(pdf), "application/pdf")},
                      data={"judul": "x" * 501}).status_code == 400  # ditolak sebelum PDF disimpan
    pd = admin.post("/api/panduan", files={"file": ("pmk.pdf", io.BytesIO(pdf), "application/pdf")},
                    data={"judul": "pmk", "deskripsi": "Standar biaya", "aktif": "true"}).json()
    assert pd["terkini"]["status_proses"] == "BELUM" and pd["aktif"] and pd["diubah_oleh"] and pd["terkini"]["deskripsi"] == "Standar biaya"
    assert pd["terkini"]["dibuat_oleh"] == pd["diubah_oleh"]  # akun yang membuat versi
    jalankan_antrean()
    daftar = admin.get("/api/panduan").json()
    assert daftar[0]["terkini"]["status_proses"] == "SIAP"
    ubah = admin.put(f"/api/panduan/{pd['id']}", data={"judul": "PMK Standar Biaya"}).json()
    assert ubah["terkini"]["nomor"] == 2 and len(ubah["versi"]) == 2
    pengusul, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rv = pengusul.get(f"/api/review/{pengusul.get(f'/api/usulan/{u['id']}').json()['review_id']}").json()
    assert rv["acuan"]["panduan"][0]["judul"] == "PMK Standar Biaya"
    dasar = [r for i in rv["item"] for r in i["rujukan"] if r["peran"] == "dasar_panduan"]
    assert dasar and all(r["dokumen"] == "PANDUAN" for r in dasar)
    assert rv["acuan"]["panduan"][0]["nomor"] == 2  # review mencatat versi panduan yang dipakai (D5)
    nonaktif = admin.put(f"/api/panduan/{pd['id']}", data={"judul": "PMK Standar Biaya", "aktif": "false"}).json()
    assert nonaktif["aktif"] is False and nonaktif["terkini"]["nomor"] == 3 and nonaktif["terkini"]["aktif"] is False
    assert [x["aktif"] for x in nonaktif["versi"]] == [False, True, True]  # status tercatat per versi
    sama = admin.put(f"/api/panduan/{pd['id']}", data={"judul": "PMK Standar Biaya", "aktif": "false"}).json()
    assert sama["terkini"]["nomor"] == 3  # simpan tanpa perubahan tidak membuat versi
    # Database: versi terkini hanya di `panduan`; `panduan_histori` hanya riwayat (v1, v2).
    with SessionLokal() as db:
        pid = uuid.UUID(pd["id"])
        pdb = db.get(Panduan, pid)
        assert pdb.created_by and pdb.created_by == pdb.updated_by  # admin yang sama mengunggah & mengedit
        # Riwayat urut updated_date = versi 1, 2; terkini = versi 3 (nomor versi tidak disimpan).
        assert [v.panduan for v in pdb.versi] == ["pmk", "PMK Standar Biaya"] and pdb.daftar_versi()[0][0] == 3
        assert {v.created_by for v in pdb.versi} == {pdb.created_by}  # riwayat menyalin pengunggah pertama
    assert pengusul.get(f"/api/review/{rv['id']}").json()["acuan"]["panduan"][0]["nomor"] == 2  # catatan review tidak berubah (D5)
    assert pengusul.get(f"/api/file/{pd['terkini']['file_id']}").status_code == 200  # PDF panduan terbuka untuk semua pengguna
    assert admin.get("/api/panduan").json()[0]["aktif"] is False  # tetap tampil di daftar
    _, u2 = _usulan_diajukan(klien)
    jalankan_antrean()
    rv2 = pengusul.get(f"/api/review/{pengusul.get(f'/api/usulan/{u2['id']}').json()['review_id']}").json()
    assert rv2["acuan"]["panduan"] == []  # Nonaktif → tidak dipakai review
    # Hapus = permanen: panduan, versi, file & ekstraksinya hilang; review lama tetap terbuka tanpa rujukan panduan.
    assert admin.delete(f"/api/panduan/{pd['id']}").status_code == 200
    assert admin.get("/api/panduan").json() == []
    assert admin.get(f"/api/file/{pd['terkini']['file_id']}").status_code == 404
    rv_lama = pengusul.get(f"/api/review/{rv['id']}").json()
    assert rv_lama["acuan"]["panduan"] == [] and not [r for i in rv_lama["item"] for r in i["rujukan"] if r["peran"] == "dasar_panduan"]
    assert admin.get("/api/panduan/versi").status_code in (404, 405, 422)  # versi daftar panduan sudah dihapus


def test_panduan_tidak_macet_bila_worker_mati_berulang(klien):
    """Worker mati 3× saat memproses panduan → file GAGAL (bukan "Diproses" selamanya) dan dapat diproses ulang."""
    import io
    from datetime import datetime, timedelta, timezone

    from app.model import File, Job
    from app.pekerja.utama import lepas_job_macet
    admin = klien("admin", "GantiSegera!2026")
    pd = admin.post("/api/panduan", files={"file": ("p.pdf", io.BytesIO(buat_pdf(["Pasal 1 uji macet"])), "application/pdf")},
                    data={"judul": "p"}).json()
    fid = uuid.UUID(pd["terkini"]["file_id"])
    with SessionLokal() as db:  # keadaan setelah worker mati pada percobaan ke-3
        db.execute(update(Job).where(Job.ref_id == fid).values(
            status="DIPROSES", percobaan=3, dikunci_at=datetime.now(timezone.utc) - timedelta(hours=1)))
        db.execute(update(File).where(File.id == fid).values(status_ekstraksi="DIPROSES"))
        db.commit()
    lepas_job_macet()
    assert admin.get("/api/panduan").json()[0]["terkini"]["status_proses"] == "GAGAL"
    assert admin.post(f"/api/panduan/{pd['id']}/proses-ulang").json()["terkini"]["status_proses"] == "BELUM"


def test_tidak_ada_koneksi_keluar_selama_review(klien, monkeypatch):
    """B1: selama review berjalan, satu-satunya koneksi jaringan adalah ke database."""
    from sqlalchemy.engine import make_url

    from app.konfigurasi import konfigurasi
    host_db = make_url(konfigurasi().database_url).host
    asli = socket.socket.connect
    tujuan = []

    def catat(self, alamat):
        tujuan.append(alamat)
        return asli(self, alamat)

    monkeypatch.setattr(socket.socket, "connect", catat)
    _usulan_diajukan(klien)
    jalankan_antrean()
    ip_db = {i[4][0] for i in socket.getaddrinfo(host_db, None)}
    keluar = [t for t in tujuan if isinstance(t, tuple) and t[0] not in ip_db | {host_db}]
    assert keluar == [], f"koneksi keluar terdeteksi: {keluar}"
    with SessionLokal() as db:
        assert db.scalar(select(Review.status).limit(1)) == "SELESAI"
