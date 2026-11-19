"""Uji integrasi alur PRD §5 ujung ke ujung (AI tiruan): buat usulan → ajukan → hasil AI → override →
finalkan → revisi → riwayat; plus invarian rujukan, konsistensi (fingerprint), hak akses, versioning, offline."""
import io
import socket
import threading
import uuid

from sqlalchemy import func, select, text, update

from app.db import SessionLokal
from app.model import Elemen, File, Kategori, KategoriHistori, Panduan, Review, Revisi, Rujukan, Usulan
from tests.conftest import RAB_CONTOH, TOR_CONTOH, buat_pdf, isian, jalankan_antrean, unggah

TOR = buat_pdf(TOR_CONTOH)
RAB = buat_pdf(["RINCIAN ANGGARAN BIAYA"], RAB_CONTOH)


def _usulan_diajukan(klien, ajukan=True):
    p = klien("pengusul")
    r = unggah(p, tor=TOR, rab=RAB, **isian(p), ajukan=ajukan)
    assert r.status_code == 200, r.text
    return p, r.json()


def _review(klien, review_id) -> dict:
    """Detail review dilihat Reviewer: Pengusul baru melihat hasil setelah final (desain.md §7 no. 36)."""
    return klien("reviewer").get(f"/api/review/{review_id}").json()


def test_alur_lengkap(klien):
    pengusul, u = _usulan_diajukan(klien)
    assert u["status"] == "ANTRE"
    assert jalankan_antrean() >= 1

    rv = _review(klien, pengusul.get(f'/api/usulan/{u['id']}').json()['review_id'])
    assert rv["status"] == "SELESAI" and rv["tampilan"] == "reviewer" and not rv["final"]
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

    # Reviewer menilai item (Simpan Sebagai Draf) → label dihitung ulang; pengusul belum melihat penilaian
    reviewer = klien("reviewer")
    url = f"/api/review/{rv['id']}/keputusan"
    item = rv["item"][0]
    nilai = "TIDAK_TERPENUHI" if item["terpenuhi"] else "TERPENUHI"
    d = reviewer.put(url, json={"item": [{"checklist_item_id": item["id"], "nilai": nilai, "catatan": "Bukti kurang"}]}).json()
    assert d["item"][0]["diubah"] and d["item"][0]["ai_terpenuhi"] == item["ai_terpenuhi"]  # hasil AI tetap (O2)
    belum = pengusul.get(f"/api/review/{rv['id']}").json()  # Pengusul: hasil AI terlihat, override belum (sebelum final)
    assert belum["item"][0]["diubah"] is False and pengusul.get(f"/api/usulan/{u['id']}").json()["review_id"] == rv["id"]
    # Kembali ke nilai AI (O5); catatan item tidak dikirim → catatan tersimpan tetap
    d = reviewer.put(url, json={"item": [{"checklist_item_id": item["id"], "nilai": "TERPENUHI" if item["ai_terpenuhi"] else "TIDAK_TERPENUHI"}]}).json()
    assert d["item"][0]["terpenuhi"] == item["ai_terpenuhi"] and d["item"][0]["catatan_verifikator"]["teks"] == "Bukti kurang"
    # Keputusan akhir berbeda dari hitungan item → peringatan tidak konsisten; lalu TIDAK LOLOS + kategori K4 + catatan akhir
    d = reviewer.put(url, json={"label": "TIDAK_LOLOS" if d["label"]["hitung"] == "LOLOS" else "LOLOS"}).json()
    assert d["label"]["tidak_konsisten"]
    k4 = next(k for k in d["kategori"]["pilihan"] if k["kode"] == "K4")
    d = reviewer.put(url, json={"label": "TIDAK_LOLOS", "kategori_id": k4["id"], "catatan": "Perbaiki indikator."}).json()
    # Simpan ulang tanpa `catatan` tidak menghapus catatan akhir, dan teks yang sama tidak menambah Audit Log
    audit = lambda: klien("admin", "GantiSegera!2026").get("/api/audit", params={"aksi": "CATATAN_REVIEWER"}).json()["total"]  # noqa: E731
    jumlah_audit = audit()
    reviewer.put(url, json={"label": "TIDAK_LOLOS"})
    reviewer.put(url, json={"catatan": "Perbaiki indikator."})
    assert audit() == jumlah_audit
    # Pengusul tidak dapat menilai/finalkan
    assert pengusul.put(url, json={"label": "LOLOS"}).status_code == 403
    assert pengusul.post(f"/api/review/{rv['id']}/finalkan").status_code == 403

    d = reviewer.post(f"/api/review/{rv['id']}/finalkan").json()
    assert d["final"] and d["label"]["final"] == "TIDAK_LOLOS" and d["kategori"]["final"]["kode"] == "K4"
    # Terkunci (O7)
    assert reviewer.put(url, json={"label": "LOLOS"}).status_code == 409
    # Pengusul kini melihat hasil final + catatan, berdampingan dengan hasil AI
    lihat = pengusul.get(f"/api/review/{rv['id']}").json()
    assert lihat["final"] and lihat["catatan"][0]["teks"] == "Perbaiki indikator." and lihat["label"]["ai"] is not None
    baris = pengusul.get(f"/api/usulan/{u['id']}").json()
    assert baris["status"] == "TIDAK_LOLOS" and baris["kategori_final"]["kode"] == "K4"
    # Tombol "Unggah Revisi" di halaman Pemeriksaan: hanya Pengusul Satker ini, revisi terbaru yang Tidak Lolos
    assert pengusul.get(f"/api/review/{rv['id']}").json()["boleh_unggah_revisi"] and not _review(klien, rv["id"])["boleh_unggah_revisi"]

    # Tidak boleh dihapus setelah direview; revisi wajib TOR dan RAB (TOR isinya sama, RAB beda) → ajukan → tidak disalin
    assert klien("pengusul_b").delete(f"/api/usulan/{u['id']}").status_code == 403  # Satker lain
    rab2 = buat_pdf(["RINCIAN ANGGARAN BIAYA REVISI"], RAB_CONTOH + [["Konsumsi", "5", "OK", "50.000"]])
    assert unggah(pengusul, f"/api/usulan/{u['id']}/revisi", rab=rab2, ajukan=True).status_code == 400  # RAB saja
    r2 = unggah(pengusul, f"/api/usulan/{u['id']}/revisi", tor=TOR, rab=rab2, ajukan=True).json()
    assert r2["revisi_nomor"] == 2 and r2["tor"]["file_id"] == u["tor"]["file_id"] and r2["rab"]["file_id"] != u["rab"]["file_id"]
    # Tanggal Pengajuan mengikuti unggahan terakhir (revisi), bukan pengajuan pertama
    assert r2["diajukan_at"] > u["diajukan_at"] and r2["dibuat_at"] == u["dibuat_at"]
    assert not pengusul.get(f"/api/review/{rv['id']}").json()["boleh_unggah_revisi"]  # bukan revisi terbaru lagi
    jalankan_antrean()
    riwayat = reviewer.get(f"/api/usulan/{u['id']}/riwayat").json()
    assert len(riwayat["revisi"]) == 2 and all(r["review"][-1]["status"] == "SELESAI" for r in riwayat["revisi"])
    assert pengusul.get(f"/api/usulan/{u['id']}/riwayat").json()["revisi"][1]["review"][-1]["status"] == "SELESAI"  # Histori Dokumen
    assert riwayat["revisi"][1]["rab"]["diganti"] and not riwayat["revisi"][1]["tor"]["diganti"]


def test_konsistensi_fingerprint_hasil_identik(klien):
    """Dokumen yang sama persis + acuan sama → hasil AI disalin, sama persis (PRD §8 Akurasi)."""
    pengusul, u1 = _usulan_diajukan(klien)
    r = unggah(pengusul, tor=TOR, rab=RAB, **isian(pengusul), ajukan=True)
    jalankan_antrean()
    a = _review(klien, pengusul.get(f'/api/usulan/{u1['id']}').json()['review_id'])
    b = _review(klien, pengusul.get(f'/api/usulan/{r.json()['id']}').json()['review_id'])
    assert b.get("disalin_dari_revisi") == 1 or a.get("disalin_dari_revisi") == 1
    ringkas = lambda d: ([(i["kode"], i["ai_terpenuhi"], [(x["halaman"], x["kutipan"]) for x in i["rujukan"]]) for i in d["item"]],
                         d["label"]["ai"], d["kategori"]["ai"]["kode"])  # noqa: E731
    assert ringkas(a) == ringkas(b)


def test_edit_kategori_mencegah_salin_hasil(klien):
    """Isi kategori ikut fingerprint: dokumen identik disalin dari hasil lama, kecuali definisi kategori sudah diedit."""
    pengusul, _ = _usulan_diajukan(klien)
    jalankan_antrean()

    def ajukan_lagi() -> dict:
        _, u = _usulan_diajukan(klien)
        jalankan_antrean()
        return _review(klien, pengusul.get(f'/api/usulan/{u['id']}').json()['review_id'])

    assert ajukan_lagi().get("disalin_dari_revisi") == 1  # kontrol: acuan sama → disalin
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    k = kelola.get("/api/kategori").json()["item"][0]
    assert kelola.put(f"/api/kategori/{k['id']}", json={**k, "definisi": k["definisi"] + " (diubah)"}).status_code == 200
    b = ajukan_lagi()
    assert b["status"] == "SELESAI" and b.get("disalin_dari_revisi") is None


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
    assert unggah(reviewer, tor=TOR, rab=RAB, **isian(reviewer)).status_code == 403
    admin = klien("admin", "GantiSegera!2026")
    # Pengguna, Node AI & Audit Log: khusus Admin.
    for c in (pengusul, reviewer):
        assert c.get("/api/pengguna").status_code == 403
        assert c.get("/api/audit").status_code == 403
        assert c.get("/api/node-ai").status_code == 403
    # Checklist, Panduan, Satker, Master RO dikelola Reviewer; Pengusul melihat Checklist (view only); Admin tidak
    # punya menu-menu ini.
    i = reviewer.get("/api/checklist").json()["item"][0]
    assert pengusul.get("/api/checklist").status_code == 200 and pengusul.get(f"/api/checklist/item/{i['id']}/riwayat").status_code == 200
    assert pengusul.get("/api/panduan").status_code == 200
    assert admin.get("/api/checklist").status_code == 403 and admin.get(f"/api/checklist/item/{i['id']}/riwayat").status_code == 403
    assert admin.get("/api/panduan").status_code == 403
    for c in (pengusul, admin):
        assert c.post("/api/checklist/item", json={"kode": "Z1", "judul": "a", "kriteria": "b", "berlaku_untuk": "TOR"}).status_code == 403
        assert c.put(f"/api/checklist/item/{i['id']}", json={**i, "judul": "x"}).status_code == 403
        assert c.delete(f"/api/checklist/item/{i['id']}").status_code == 403
        assert c.put("/api/checklist/urutan", json={"id": [i["id"]]}).status_code == 403
        assert c.put("/api/panduan/00000000-0000-0000-0000-000000000000", data={"judul": "x", "aktif": "false"}).status_code == 403
        assert c.post("/api/satker", json={"unit_kerja": "UK X"}).status_code == 403
        assert c.get("/api/master-ro").status_code == 403
    assert pengusul.get("/api/satker").status_code == 403
    # Admin tidak lagi mengakses Dashboard & Usulan (termasuk file TOR/RAB).
    assert admin.get("/api/dashboard").status_code == 403
    assert admin.get("/api/usulan").status_code == 403
    assert admin.get(f"/api/usulan/{u['id']}").status_code == 403
    assert admin.get(f"/api/file/{u['tor']['file_id']}").status_code == 404
    anonim = klien()
    assert anonim.get("/api/usulan").status_code == 401
    assert anonim.get(f"/api/file/{u['tor']['file_id']}").status_code == 401
    tanpa_csrf = klien("pengusul")
    tanpa_csrf.headers.pop("X-CSRF-Token")
    assert tanpa_csrf.post(f"/api/usulan/{u['id']}/ajukan").status_code == 403
    # Hapus khusus Reviewer
    assert klien("admin", "GantiSegera!2026").delete(f"/api/usulan/{u['id']}").status_code == 403
    assert reviewer.delete(f"/api/usulan/{u['id']}").status_code == 200


def test_pengajuan_baru_keputusan_akhir_edit_dan_hapus_reviewer(klien):
    """Revisi Menu Usulan (desain.md §7 no. 36 & 38): hierarki & kategori divalidasi, TOR dan RAB wajib, Pengusul melihat
    hasil AI segera tetapi penilaian verifikator setelah final, draf Keputusan Akhir, Reviewer mengedit & menghapus usulan."""
    p = klien("pengusul")
    form = isian(p)
    assert unggah(p, tor=TOR, rab=RAB, **{**form, "kro": "EBD"}).status_code == 400  # RO 994 bukan anak KRO EBD
    assert unggah(p, rab=RAB, **form).status_code == 400  # TOR kosong
    assert unggah(p, **form).status_code == 400  # keduanya kosong
    assert unggah(p, tor=TOR, rab=RAB, **{**form, "tahun_anggaran": form["tahun_anggaran"] + 3}).status_code == 400  # di luar ±2
    lain = unggah(p, tor=TOR, rab=RAB, **{**form, "tahun_anggaran": form["tahun_anggaran"] + 1}).json()
    assert lain["tahun_anggaran"] == form["tahun_anggaran"] + 1  # mengikuti Tahun Anggaran pilihan di bilah atas
    u = unggah(p, tor=TOR, rab=RAB, **form, ajukan=True).json()
    assert u["tor"] and u["rab"] and u["hierarki"]["ro"]["kode"] == "4490.EBA.994" and u["kategori_usulan"]["kode"] == "K1"
    jalankan_antrean()
    rid = p.get(f"/api/usulan/{u['id']}").json()["review_id"]
    # Verifikator boleh mengonfirmasi nilai AI tanpa catatan; Pengusul melihat hasil AI, tetapi belum penilaian verifikator
    reviewer = klien("reviewer")
    rv = _review(klien, rid)
    i0 = rv["item"][0]
    nilai_ai = "TERPENUHI" if i0["ai_terpenuhi"] else "TIDAK_TERPENUHI"
    url_keputusan = f"/api/review/{rid}/keputusan"
    d = reviewer.put(url_keputusan, json={"item": [{"checklist_item_id": i0["id"], "nilai": nilai_ai}]}).json()
    assert d["item"][0]["override"]["nilai_sesudah"] == nilai_ai
    # Simpan Sebagai Draf: status (bawaan = nilai AI) & Catatan Verifikator per item tersimpan bersama
    i1 = rv["item"][1]
    nilai_i1 = "TERPENUHI" if i1["ai_terpenuhi"] else "TIDAK_TERPENUHI"
    d = reviewer.put(url_keputusan, json={"item": [{"checklist_item_id": i1["id"], "nilai": nilai_i1, "catatan": " Cek ulang volume. "}]}).json()
    assert d["item"][1]["catatan_verifikator"]["teks"] == "Cek ulang volume." and d["item"][1]["override"]["nilai_sesudah"] == nilai_i1
    jumlah = len(d["riwayat_override"])
    reviewer.put(url_keputusan, json={"item": [{"checklist_item_id": i1["id"], "nilai": nilai_i1, "catatan": "Cek ulang volume."}]})
    assert len(_review(klien, rid)["riwayat_override"]) == jumlah  # simpan ulang tanpa perubahan tidak menambah override
    asing = {"item": [{"checklist_item_id": str(uuid.uuid4()), "nilai": "TERPENUHI"}]}
    assert reviewer.put(url_keputusan, json=asing).status_code == 400
    assert p.put(url_keputusan, json=asing).status_code == 403
    lihat = p.get(f"/api/review/{rid}").json()
    assert lihat["item"] and lihat["item"][0]["override"] is None and lihat["catatan"] == [] and not lihat["boleh_unggah_revisi"]
    assert lihat["item"][1]["catatan_verifikator"] is None  # Pengusul: catatan verifikator setelah final
    # Draf Keputusan Akhir: tersimpan untuk reviewer, tersembunyi dari Pengusul; finalkan tanpa body memakai draf itu
    catatan = lambda x, dok: next((c["teks"] for c in x["catatan"] if c["dokumen"] == dok), None)  # noqa: E731
    assert reviewer.put(url_keputusan, json={"kategori_id": str(uuid.uuid4())}).status_code == 400
    kat_lain = next(k for k in d["kategori"]["pilihan"] if k["id"] != d["kategori"]["ai"]["id"])
    d = reviewer.put(f"/api/review/{rid}/keputusan", json={"label": "LOLOS", "catatan": "Disetujui.", "kategori_id": kat_lain["id"],
                                                          "catatan_kategori": "Lebih tepat."}).json()
    assert not d["final"] and d["label"]["final"] == "LOLOS" and catatan(d, "UMUM") == "Disetujui."
    assert d["kategori"]["final"]["id"] == kat_lain["id"] and catatan(d, "KATEGORI") == "Lebih tepat."
    sebelum_final = p.get(f"/api/review/{rid}").json()
    assert sebelum_final["catatan"] == [] and sebelum_final["kategori"]["final"]["id"] == d["kategori"]["ai"]["id"]  # Pengusul: belum
    assert p.put(f"/api/review/{rid}/keputusan", json={"label": "LOLOS"}).status_code == 403
    d = reviewer.post(f"/api/review/{rid}/finalkan").json()
    assert d["final"] and d["label"]["final"] == "LOLOS"
    lihat = p.get(f"/api/review/{rid}").json()
    assert lihat["item"][0]["override"]["nilai_sesudah"] == nilai_ai and catatan(lihat, "UMUM") == "Disetujui."
    assert lihat["kategori"]["final"]["id"] == kat_lain["id"] and catatan(lihat, "KATEGORI") == "Lebih tepat."
    assert p.get(f"/api/usulan/{u['id']}").json()["kategori_final"]["kode"] == kat_lain["kode"]
    assert lihat["item"][1]["catatan_verifikator"]["teks"] == "Cek ulang volume."
    assert reviewer.put(url_keputusan, json={"catatan": "terlambat"}).status_code == 409  # terkunci setelah final
    assert p.get(f"/api/usulan/{u['id']}").json()["status"] == "LOLOS"
    # Edit usulan khusus Reviewer: hierarki/kategori; terkunci setelah diverifikasi (desain.md §7 no. 51). Penggantian
    # dokumen oleh Reviewer diuji di test_dokumen_diganti_review_lama_terkunci_dan_file_lama_ikut_terhapus.
    k2 = isian(p, "K2")["kategori_id"]
    ubah = {**form, "ro": "962", "kategori_id": k2}
    assert reviewer.put(f"/api/usulan/{u['id']}", data=ubah).status_code == 409  # sudah Lolos
    assert p.put(f"/api/usulan/{lain['id']}", data=ubah).status_code == 403
    assert reviewer.put(f"/api/usulan/{lain['id']}", data={**ubah, "ro": "999"}).status_code == 400
    e = reviewer.put(f"/api/usulan/{lain['id']}", data=ubah).json()
    assert e["kode_ro"] == "4490.EBA.962" and e["kategori_usulan"]["kode"] == "K2" and e["revisi_nomor"] == 1
    # Hapus khusus Reviewer (Admin & Pengusul hanya melihat)
    assert p.delete(f"/api/usulan/{u['id']}").status_code == 403
    assert klien("admin", "GantiSegera!2026").delete(f"/api/usulan/{u['id']}").status_code == 403
    assert reviewer.delete(f"/api/usulan/{u['id']}").status_code == 200
    assert p.get(f"/api/usulan/{u['id']}").status_code == 404
    with SessionLokal() as db:
        assert db.get(Review, uuid.UUID(rid)) is None
        assert db.get(File, uuid.UUID(u["rab"]["file_id"])) is not None  # file identik masih dipakai usulan `lain`


def test_pengajuan_mengikuti_master_ro(klien):
    """Hierarki Pengajuan Baru = data menu Master RO (desain.md §7 no. 48): RO yang baru diinput Reviewer langsung dapat
    dipilih; RO Nonaktif hilang dari pilihan dan ditolak saat dikirim."""
    p, reviewer = klien("pengusul"), klien("reviewer")
    form = isian(p)
    eba = next(x for x in reviewer.get("/api/master-ro").json() if x["tingkat"] == "KRO" and x["kode"] == "EBA")
    ro = reviewer.post("/api/master-ro", json={"tingkat": "RO", "induk_id": eba["id"], "kode": "955", "nama": "Layanan Uji Baru"}).json()
    pilihan_ro = lambda: [r["kode"] for g in p.get("/api/usulan/opsi/pengajuan").json()["hierarki"] for k in g["kegiatan"]  # noqa: E731
                          for x in k["kro"] if x["kode"] == "EBA" for r in x["ro"]]
    assert "955" in pilihan_ro()
    u = unggah(p, tor=TOR, rab=RAB, **{**form, "ro": "955"}).json()
    assert u["hierarki"]["ro"] == {"kode": "4490.EBA.955", "nama": "Layanan Uji Baru"} and u["kode_ro"] == "4490.EBA.955"
    assert reviewer.put(f"/api/master-ro/{ro['id']}", json={"tingkat": "RO", "induk_id": eba["id"], "kode": "955",
                                                           "nama": "Layanan Uji Baru", "aktif": False}).status_code == 200
    assert "955" not in pilihan_ro()
    assert unggah(p, tor=TOR, rab=RAB, **{**form, "ro": "955"}).status_code == 400
    assert p.get(f"/api/usulan/{u['id']}").json()["hierarki"]["ro"]["nama"] == "Layanan Uji Baru"  # salinan usulan tetap
    # Induk Nonaktif: RO 994 sendiri masih Aktif, tetapi KRO EBA dinonaktifkan → ikut hilang dan ditolak.
    assert reviewer.put(f"/api/master-ro/{eba['id']}", json={"tingkat": "KRO", "induk_id": eba["induk_id"], "kode": "EBA",
                                                             "nama": eba["nama"], "aktif": False}).status_code == 200
    assert "994" not in pilihan_ro() and unggah(p, tor=TOR, rab=RAB, **form).status_code == 400


def test_filter_dan_urut_daftar_usulan(klien):
    """Filter per kolom tabel (Satuan Kerja, Rincian Output, Dokumen, Status, Tanggal Pengajuan) dan urut per kolom."""
    p = klien("pengusul")
    form = isian(p)
    a = unggah(p, tor=TOR, rab=RAB, **form).json()
    b = unggah(p, tor=TOR, rab=RAB, **{**form, "ro": "962"}).json()
    r = klien("reviewer")
    cari = lambda **x: [u["id"] for u in r.get("/api/usulan", params={"tahun": form["tahun_anggaran"], **x}).json()["data"]]  # noqa: E731
    assert set(cari(satker=a["satker"]["nama"][-5:])) == {a["id"], b["id"]} and cari(satker="tidak-ada") == []
    assert cari(q="962") == [b["id"]] and set(cari(dokumen="tor")) == {a["id"], b["id"]} and cari(dokumen="xyz") == []
    assert set(cari(status="DRAF")) == {a["id"], b["id"]} and cari(status="LOLOS") == []
    hari_ini = a["diajukan_at"][:10]  # UTC; uji berjalan jauh dari tengah malam WIB dianggap cukup
    assert cari(tanggal="2000-01-01") == [] and r.get("/api/usulan", params={"tanggal": hari_ini}).status_code == 200
    # 4490.EBA.962 < 4490.EBA.994
    assert cari(urut="rincian", arah="asc") == [b["id"], a["id"]] and cari(urut="rincian", arah="desc") == [a["id"], b["id"]]
    assert r.get("/api/usulan", params={"urut": "kolom-asing"}).status_code == 422
    # Halaman di luar jangkauan (ganti tahun di halaman 2 / baris terakhir dihapus) → halaman terakhir, bukan daftar kosong.
    x = r.get("/api/usulan", params={"tahun": form["tahun_anggaran"], "halaman": 99, "per_halaman": 1}).json()
    assert x["halaman"] == x["total"] >= 2 and len(x["data"]) == 1


def test_keputusan_kembali_ke_pilihan_ai_membatalkan_override(klien):
    """Verifikator mengganti kategori & keputusan akhir lalu mengembalikannya ke pilihan AI (desain.md §7 no. 40 & 44):
    override sebelumnya dibatalkan, sehingga nilai final kembali ke AI/hitungan item dan tidak ditandai diubah."""
    _, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rid = klien("pengusul").get(f"/api/usulan/{u['id']}").json()["review_id"]
    reviewer = klien("reviewer")
    url = f"/api/review/{rid}/keputusan"
    d = _review(klien, rid)
    ai, hitung = d["kategori"]["ai"]["id"], d["label"]["hitung"]
    lain = next(k["id"] for k in d["kategori"]["pilihan"] if k["id"] != ai)
    kebalikan = "TIDAK_LOLOS" if hitung == "LOLOS" else "LOLOS"
    d = reviewer.put(url, json={"kategori_id": lain, "label": kebalikan, "catatan": "Sementara."}).json()
    assert d["kategori"]["final"]["id"] == lain and d["kategori"]["diubah"] and d["label"]["final"] == kebalikan and d["label"]["diubah"]
    d = reviewer.put(url, json={"kategori_id": ai, "label": hitung, "catatan": "Kembali ke AI."}).json()
    assert d["kategori"]["final"]["id"] == ai and not d["kategori"]["diubah"]
    assert d["label"]["final"] == hitung and not d["label"]["diubah"]
    d = reviewer.post(f"/api/review/{rid}/finalkan").json()
    assert d["kategori"]["final"]["id"] == ai and d["label"]["final"] == hitung


def test_dokumen_diganti_review_lama_terkunci_dan_file_lama_ikut_terhapus(klien):
    """Setelah Reviewer mengganti TOR (revisi yang sama direview ulang), review lama tidak dapat dinilai/difinalkan; TOR lama
    tetap disimpan selama dikutip review lama dan ikut terhapus saat usulan dihapus. Ganti dokumen Draf langsung
    menghapus file lama yang tidak dipakai lagi."""
    p = klien("pengusul")
    form = isian(p)
    berkas = lambda nama, teks: {"tor": (nama, io.BytesIO(buat_pdf(TOR_CONTOH + [teks])), "application/pdf")}  # noqa: E731
    u = unggah(p, tor=buat_pdf(TOR_CONTOH + ["Versi awal kerangka acuan uji ganti dokumen."]), rab=RAB, **form, ajukan=True).json()
    lama_id = uuid.UUID(u["tor"]["file_id"])
    jalankan_antrean()
    r1 = p.get(f"/api/usulan/{u['id']}").json()["review_id"]
    reviewer = klien("reviewer")
    e = reviewer.put(f"/api/usulan/{u['id']}", data=form, files=berkas("tor-baru.pdf", "Versi perbaikan uji ganti dokumen.")).json()
    assert e["revisi_nomor"] == 1 and e["status"] == "ANTRE" and e["rab"]["file_id"] == u["rab"]["file_id"]  # tanpa baris Histori baru
    assert reviewer.delete(f"/api/usulan/{u['id']}").status_code == 409  # masih antre
    jalankan_antrean()
    assert len(reviewer.get(f"/api/usulan/{u['id']}/riwayat").json()["revisi"][0]["review"]) == 2  # review lama tetap tersimpan
    r2 = p.get(f"/api/usulan/{u['id']}").json()["review_id"]
    assert r2 != r1 and _review(klien, r2)["boleh_override"] and not _review(klien, r1)["boleh_override"]
    assert reviewer.put(f"/api/review/{r1}/keputusan", json={"label": "LOLOS"}).status_code == 409
    assert reviewer.post(f"/api/review/{r1}/finalkan").status_code == 409
    with SessionLokal() as db:
        dikutip = db.scalar(select(func.count()).select_from(Rujukan).join(Elemen, Elemen.id == Rujukan.elemen_id)
                            .where(Rujukan.review_id == uuid.UUID(r1), Elemen.file_id == lama_id))
        assert dikutip and db.get(File, lama_id) is not None  # masih dikutip rujukan review lama
    assert reviewer.post(f"/api/review/{r2}/finalkan").status_code == 200
    assert reviewer.delete(f"/api/usulan/{u['id']}").status_code == 200
    with SessionLokal() as db:
        assert db.get(File, lama_id) is None
        assert db.scalar(select(func.count()).select_from(Elemen).where(Elemen.file_id == lama_id)) == 0
    # Pengusul mengganti TOR saat Draf: file lama tidak dipakai apa pun → langsung terhapus.
    d = unggah(p, tor=buat_pdf(TOR_CONTOH + ["Draf awal uji ganti dokumen."]), rab=RAB, **form).json()
    draf_lama = uuid.UUID(d["tor"]["file_id"])
    assert p.put(f"/api/usulan/{d['id']}/draf", files=berkas("tor-draf.pdf", "Draf pengganti uji ganti dokumen.")).status_code == 200
    with SessionLokal() as db:
        assert db.get(File, draf_lama) is None


def test_validasi_unggahan(klien):
    p = klien("pengusul")
    r = unggah(p, tor=b"bukan pdf sama sekali", rab=RAB, **isian(p))
    assert r.status_code == 400 and "PDF" in r.json()["pesan"]


def test_versioning_tidak_mengubah_review_lama(klien):
    pengusul, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rid = pengusul.get(f"/api/usulan/{u['id']}").json()["review_id"]
    sebelum = _review(klien, rid)
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    ck = kelola.get("/api/checklist").json()["item"]
    for i in ck:  # ubah semua item: review lama tetap menampilkan isi saat review dimulai
        assert kelola.put(f"/api/checklist/item/{i['id']}", json={**i, "judul": i["judul"] + " (diubah)"}).status_code == 200
    # Item yang ditambah SETELAH review dimulai tidak ikut ke review lama
    assert kelola.post("/api/checklist/item", json={"kode": "Z99", "judul": "Item baru", "kriteria": "K", "berlaku_untuk": "TOR"}).status_code == 200
    kat = kelola.get("/api/kategori").json()["item"]
    # Seed kategori persis PRD C1
    assert [k["kode"] for k in kat] == ["K1", "K2", "K3", "K4"] and all(k["aktif"] for k in kat)
    assert kat[1]["definisi"].startswith("RO prioritas yang ditetapkan secara resmi oleh Menteri")
    assert [k["definisi"] for k in sebelum["kategori"]["pilihan"]] == [k["definisi"] for k in kat]  # C3: definisi tampil di review
    for k in kat:
        assert kelola.put(f"/api/kategori/{k['id']}", json={**k, "nama": k["nama"] + " X", "definisi": k["definisi"] + " X"}).status_code == 200
    sesudah = _review(klien, rid)
    assert [(i["kode"], i["judul"], i["kriteria"]) for i in sesudah["item"]] == [(i["kode"], i["judul"], i["kriteria"]) for i in sebelum["item"]]
    assert sesudah["acuan"] == sebelum["acuan"] and sesudah["kategori"] == sebelum["kategori"]


def test_dashboard_dan_filter_per_kategori_final(klien):
    # Setiap review menyalin semua kategori dengan id yang sama, jadi join ke review_kategori wajib memakai review yang sama.
    pengusul, u = _usulan_diajukan(klien)
    _usulan_diajukan(klien)  # review kedua (belum final) juga menyalin K4
    jalankan_antrean()
    reviewer = klien("reviewer")
    rid = pengusul.get(f"/api/usulan/{u['id']}").json()["review_id"]
    kat = _review(klien, rid)["kategori"]
    if kat["final"]["kode"] != "K4":
        k4 = next(k for k in kat["pilihan"] if k["kode"] == "K4")
        reviewer.put(f"/api/review/{rid}/keputusan", json={"kategori_id": k4["id"], "catatan_kategori": "Tidak terkait tusi"})
    assert reviewer.post(f"/api/review/{rid}/finalkan").status_code == 200
    assert [x["id"] for x in reviewer.get("/api/usulan", params={"kategori": "K4"}).json()["data"]] == [u["id"]]
    assert reviewer.get("/api/usulan", params={"kategori": "K1"}).json()["data"] == []
    # Kartu Data Master: jumlah baris tiap menu & yang Aktif (dibandingkan langsung dengan database)
    from app.model import ChecklistItem, MasterRO
    with SessionLokal() as db:
        db.execute(update(Kategori).where(Kategori.kode == "K4").values(aktif=False))
        db.commit()
        harap = {nama: {"total": db.scalar(select(func.count()).select_from(m)), "aktif": db.scalar(select(func.count()).where(m.aktif)),
                        "diubah_at": x.isoformat() if (x := db.scalar(select(func.max(m.updated_date)))) else None}
                 for nama, m in (("checklist", ChecklistItem), ("acuan", Panduan), ("kategori", Kategori), ("master_ro", MasterRO))}
        # Semua pengajuan uji ini milik Satker `pengusul`; yang terakhir = revisi yang terakhir diunggah.
        r, u_ = db.execute(select(Revisi, Usulan).join(Usulan, Usulan.id == Revisi.usulan_id).order_by(Revisi.created_at.desc())).first()
        terakhir = {"kode_ro": u_.kode_ro, "nama_ro": u_.nama_ro, "revisi_nomor": r.nomor, "status": r.status, "diajukan_at": r.created_at.isoformat()}
    d = pengusul.get("/api/dashboard").json()
    master = d["master"]
    assert master == harap and {k: master["kategori"][k] for k in ("total", "aktif")} == {"total": 4, "aktif": 3} and master["checklist"]["total"] > 0
    # Pengusul: pengajuan Satker-nya yang terakhir diunggah; Reviewer & Pengusul Satker lain (tanpa pengajuan) tidak menerimanya
    assert d["terakhir"] == terakhir
    assert "terakhir" not in reviewer.get("/api/dashboard").json() and "terakhir" not in klien("pengusul_b").get("/api/dashboard").json()


def test_grafik_jumlah_pengajuan_per_periode(klien):
    """Dashboard: jumlah pengajuan baru per hari/minggu/bulan/tahun (WIB), periode kosong = 0; Pengusul hanya Satker-nya."""
    from datetime import datetime, timedelta, timezone
    _usulan_diajukan(klien, ajukan=False)
    _usulan_diajukan(klien, ajukan=False)
    hari_ini = datetime.now(timezone(timedelta(hours=7))).date()
    reviewer, lain = klien("reviewer"), klien("pengusul_b")
    for per, banyak in (("hari", 30), ("minggu", 12), ("bulan", 12), ("tahun", 5)):
        d = reviewer.get("/api/dashboard/tren", params={"per": per}).json()["data"]
        assert len(d) == banyak and [x["jumlah"] for x in d] == [0] * (banyak - 1) + [2]  # pengajuan hari ini di periode terakhir
        assert [x["mulai"] for x in d] == sorted(x["mulai"] for x in d)
    assert reviewer.get("/api/dashboard/tren", params={"per": "hari"}).json()["data"][-1]["mulai"] == hari_ini.isoformat()
    assert reviewer.get("/api/dashboard/tren", params={"per": "minggu"}).json()["data"][-1]["mulai"] == \
        (hari_ini - timedelta(days=hari_ini.weekday())).isoformat()
    assert reviewer.get("/api/dashboard/tren", params={"per": "bulan"}).json()["data"][0]["mulai"].endswith("-01")
    assert sum(x["jumlah"] for x in lain.get("/api/dashboard/tren").json()["data"]) == 0  # Satker lain
    assert reviewer.get("/api/dashboard/tren", params={"per": "jam"}).status_code == 422
    assert klien("admin", "GantiSegera!2026").get("/api/dashboard/tren").status_code == 403


def test_kategori_crud_riwayat_dan_hapus_permanen(klien):
    pengusul, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rid = pengusul.get(f"/api/usulan/{u['id']}").json()["review_id"]
    sebelum = _review(klien, rid)["kategori"]
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    kat = {k["kode"]: k for k in kelola.get("/api/kategori").json()["item"]}
    baru = {"kode": " k5 ", "nama": "RO Baru", "definisi": "Definisi baru", "aktif": True}
    k5 = kelola.post("/api/kategori", json=baru).json()
    assert k5["kode"] == "K5" and k5["diubah_oleh"] == "reviewer"
    assert kelola.post("/api/kategori", json={**baru, "kode": "K1"}).status_code == 400  # kode sudah dipakai
    assert kelola.post("/api/kategori", json={**baru, "kode": "K6", "nama": " "}).status_code == 400
    admin = klien("admin", "GantiSegera!2026")
    assert admin.post("/api/kategori", json={**baru, "kode": "K7"}).status_code == 403
    # Pengusul boleh melihat daftar & Kategori Histori (view only); mengubah khusus Reviewer. Admin tidak punya menu ini.
    assert pengusul.get("/api/kategori").status_code == 200 and pengusul.get(f"/api/kategori/{k5['id']}/riwayat").status_code == 200
    assert pengusul.post("/api/kategori", json={**baru, "kode": "K8"}).status_code == 403
    assert pengusul.put(f"/api/kategori/{k5['id']}", json={**k5, "nama": "X"}).status_code == 403
    assert pengusul.delete(f"/api/kategori/{k5['id']}").status_code == 403
    assert pengusul.put("/api/kategori/urutan", json={"id": [k5["id"]]}).status_code == 403
    assert admin.get("/api/kategori").status_code == 403
    # Override kategori hanya ke salinan review (C3): K5 ditambah setelah review dimulai → ditolak
    assert klien("reviewer").put(f"/api/review/{rid}/keputusan", json={"kategori_id": k5["id"]}).status_code == 400
    assert kelola.get(f"/api/kategori/{k5['id']}/riwayat").json() == []  # riwayat hanya versi sebelum perubahan
    # Ubah → isi sebelumnya masuk riwayat (terbaru dulu); simpan tanpa perubahan tidak menambah riwayat
    url = f"/api/kategori/{kat['K2']['id']}"
    for _ in range(2):
        assert kelola.put(url, json={**kat["K2"], "nama": "Diubah"}).status_code == 200
    assert kelola.put(url, json={**kat["K2"], "nama": "Diubah lagi"}).json()["nama"] == "Diubah lagi"
    assert [r["nama"] for r in kelola.get(f"{url}/riwayat").json()] == ["Diubah", kat["K2"]["nama"]]
    # Hapus permanen: kategori & riwayatnya hilang dari database; review lama tetap menampilkan kategori saat itu (C4)
    assert kelola.delete(url).status_code == 200
    assert kelola.get(f"{url}/riwayat").status_code == 404
    with SessionLokal() as db:
        assert db.scalar(select(func.count()).where(KategoriHistori.kategori_id == uuid.UUID(kat["K2"]["id"]))) == 0
    assert _review(klien, rid)["kategori"] == sebelum
    # Kategori Nonaktif tetap tampil tetapi tidak dipakai review berikutnya (seperti panduan)
    assert kelola.put(f"/api/kategori/{k5['id']}", json={**k5, "aktif": False}).json()["aktif"] is False
    assert kelola.get(f"/api/kategori/{k5['id']}/riwayat").json()[0]["aktif"] is True
    # Review berikutnya memakai daftar terbaru yang Aktif
    p2, u2 = _usulan_diajukan(klien)
    jalankan_antrean()
    rid2 = p2.get(f"/api/usulan/{u2['id']}").json()["review_id"]
    r2 = _review(klien, rid2)
    assert [k["kode"] for k in r2["kategori"]["pilihan"]] == ["K1", "K3", "K4"]
    # Minimal satu kategori Aktif harus ada: hapus atau nonaktifkan yang terakhir ditolak
    for k in kelola.get("/api/kategori").json()["item"][1:]:
        assert kelola.delete(f"/api/kategori/{k['id']}").status_code == 200
    sisa = kelola.get("/api/kategori").json()["item"]
    assert len(sisa) == 1 and kelola.delete(f"/api/kategori/{sisa[0]['id']}").status_code == 400
    assert kelola.put(f"/api/kategori/{sisa[0]['id']}", json={**sisa[0], "aktif": False}).status_code == 400


def test_kategori_atur_urutan(klien):
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    kat = kelola.get("/api/kategori").json()["item"]
    assert [k["kode"] for k in kat] == ["K1", "K2", "K3", "K4"]
    baru = [kat[3]["id"], kat[0]["id"], kat[1]["id"], kat[2]["id"]]
    r = kelola.put("/api/kategori/urutan", json={"id": baru})
    assert r.status_code == 200 and [k["id"] for k in r.json()["item"]] == baru
    assert kelola.put("/api/kategori/urutan", json={"id": baru[:3]}).status_code == 400  # daftar tidak lengkap
    assert klien("admin", "GantiSegera!2026").put("/api/kategori/urutan", json={"id": baru}).status_code == 403
    # Audit Atur Urutan menyimpan urutan sebelum & sesudah.
    log = next(x for x in klien("admin", "GantiSegera!2026").get("/api/audit").json()["data"] if x["aksi"] == "KATEGORI_URUTAN")
    assert log["data_sesudah"]["id"] == baru and sorted(log["data_sebelum"]["id"]) == sorted(baru) and log["data_sebelum"]["id"] != baru
    assert kelola.get(f"/api/kategori/{kat[0]['id']}/riwayat").json() == []  # atur urutan tidak membuat riwayat
    # Kategori baru ditaruh setelah kode sebelumnya walau urutan sudah diatur bebas; hapus merapikan nomor urut
    kelola.post("/api/kategori", json={"kode": "K5", "nama": "RO Baru", "definisi": "Definisi baru"})
    assert [k["kode"] for k in kelola.get("/api/kategori").json()["item"]] == ["K4", "K5", "K1", "K2", "K3"]
    assert kelola.delete(f"/api/kategori/{kat[0]['id']}").status_code == 200
    with SessionLokal() as db:
        assert db.scalars(select(Kategori.no_urut).order_by(Kategori.no_urut)).all() == [1, 2, 3, 4]


def test_checklist_crud_riwayat_dan_status(klien):
    from app.model import ChecklistItem
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    ck = kelola.get("/api/checklist").json()["item"]
    per_kode = {i["kode"]: i for i in ck}
    url = lambda kode: f"/api/checklist/item/{per_kode[kode]['id']}"  # noqa: E731
    isi = lambda i, **ubah: {**{k: i[k] for k in ("kode", "judul", "kriteria", "berlaku_untuk", "aktif")}, **ubah}  # noqa: E731
    # Ubah & nonaktifkan: hanya item itu yang dicap; checklist_item tetap satu baris per item
    c02 = kelola.put(url("C02"), json=isi(per_kode["C02"], judul="Judul diubah")).json()
    assert c02["judul"] == "Judul diubah" and c02["diubah_oleh"] == "reviewer"
    assert kelola.put(url("C03"), json=isi(per_kode["C03"], aktif=False)).json()["aktif"] is False
    terkini = kelola.get("/api/checklist").json()["item"]
    assert len(terkini) == len(ck) and terkini[0]["diubah_at"] == ck[0]["diubah_at"]
    # Tambah: kode manual dinormalisasi; kode kosong/ganda ditolak
    baru = {"judul": "Item baru", "kriteria": "Kriteria baru", "berlaku_untuk": "TOR"}
    assert kelola.post("/api/checklist/item", json={**baru, "kode": " c09 "}).json()["kode"] == "C09"
    # no_urut mengikuti urutan kode: item baru langsung berada di tempatnya, bukan di akhir
    c00 = kelola.post("/api/checklist/item", json={**baru, "kode": "C00"}).json()
    assert [i["kode"] for i in kelola.get("/api/checklist").json()["item"]][:2] == ["C00", "C01"] and c00["urutan"] == 1
    assert kelola.delete(f"/api/checklist/item/{c00['id']}").status_code == 200
    assert kelola.post("/api/checklist/item", json={**baru, "kode": "C01"}).status_code == 400
    assert kelola.post("/api/checklist/item", json={**baru, "kode": ""}).status_code == 400
    # Item nonaktif tidak dinilai dan tidak dihitung
    pengusul, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rv = _review(klien, pengusul.get(f'/api/usulan/{u['id']}').json()['review_id'])
    aktif = [i for i in kelola.get("/api/checklist").json()["item"] if i["aktif"]]
    assert "C03" not in [i["kode"] for i in rv["item"]] and rv["label"]["total"] == len(aktif)
    # checklist_histori memuat semua versi item (terbaru dulu), termasuk isi saat ini
    riwayat = kelola.get(f"{url('C02')}/riwayat").json()
    assert [r["judul"] for r in riwayat] == ["Judul diubah", per_kode["C02"]["judul"]]
    assert [r["judul"] for r in kelola.get(f"{url('C01')}/riwayat").json()] == [per_kode["C01"]["judul"]]
    assert kelola.get("/api/checklist/item/00000000-0000-0000-0000-000000000000/riwayat").status_code == 404
    # Hapus: permanen dari checklist_item & checklist_histori, ikut hilang dari review lama (keputusan pemilik produk)
    assert kelola.delete(url("C05")).status_code == 200
    with SessionLokal() as db:
        assert db.get(ChecklistItem, uuid.UUID(per_kode["C05"]["id"])) is None
        assert not db.scalars(text("SELECT 1 FROM checklist_histori WHERE checklist_id = :i"), {"i": per_kode["C05"]["id"]}).all()  # CASCADE
    assert "C05" not in [i["kode"] for i in _review(klien, rv['id'])["item"]]
    # Ganti kode: riwayat tetap tersambung lewat checklist_id dan kode lama tetap tercatat; review lama tetap kode saat itu
    assert kelola.put(url("C04"), json=isi(per_kode["C04"], kode="C01")).status_code == 400
    assert kelola.put(url("C04"), json=isi(per_kode["C04"], kode="x04")).json()["kode"] == "X04"
    assert [r["kode"] for r in kelola.get(f"{url('C04')}/riwayat").json()] == ["X04", "C04"]
    lama = {i["kode"]: i["judul"] for i in _review(klien, rv['id'])["item"]}
    assert lama["C04"] == per_kode["C04"]["judul"]
    # Atur urutan bebas (mis. dibalik); daftar yang tidak memuat semua item ditolak
    ids = [i["id"] for i in kelola.get("/api/checklist").json()["item"]]
    assert [i["id"] for i in kelola.put("/api/checklist/urutan", json={"id": ids[::-1]}).json()["item"]] == ids[::-1]
    assert kelola.put("/api/checklist/urutan", json={"id": ids[1:]}).status_code == 400
    # Item baru tetap ditaruh tepat setelah kode sebelumnya walau urutan sudah diatur bebas
    kelola.post("/api/checklist/item", json={**baru, "kode": "C10"})
    kode = [i["kode"] for i in kelola.get("/api/checklist").json()["item"]]
    assert kode.index("C10") == kode.index("C09") + 1
    # Urutan fisik tabel (yang ditampilkan pgAdmin "All Rows", tanpa ORDER BY) = no_urut, setelah tambah/ubah/hapus/atur
    with SessionLokal() as db:
        fisik = list(db.scalars(text("SELECT kode FROM checklist_item")))
        waktu = list(db.scalars(text("SELECT updated_date FROM checklist_histori")))
    assert fisik == kode
    assert waktu == sorted(waktu, reverse=True)  # checklist_histori: terbaru paling atas
    # Minimal satu item aktif
    aktif = [i for i in kelola.get("/api/checklist").json()["item"] if i["aktif"]]
    for i in aktif[:-1]:
        assert kelola.put(f"/api/checklist/item/{i['id']}", json=isi(i, aktif=False)).status_code == 200
    assert kelola.put(f"/api/checklist/item/{aktif[-1]['id']}", json=isi(aktif[-1], aktif=False)).status_code == 400


def test_simpan_checklist_tidak_menunggu_pembaca_lama(klien):
    """Transaksi lain yang sedang membaca checklist (mis. worker menunggu jawaban AI) tidak membuat simpan Admin
    tertahan: CLUSTER (urutan fisik) dilewati bila kunci tabel tidak didapat dalam 1 detik."""
    import time

    from app.db import engine
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    i = kelola.get("/api/checklist").json()["item"][0]
    with engine.connect() as c:
        c.execute(text("SELECT 1 FROM checklist_item LIMIT 1"))  # transaksi terbuka memegang kunci baca
        c.execute(text("SELECT 1 FROM checklist_histori LIMIT 1"))
        mulai = time.monotonic()
        r = kelola.put(f"/api/checklist/item/{i['id']}", json={**i, "judul": i["judul"] + " (diubah)"})
        assert r.status_code == 200 and time.monotonic() - mulai < 10
        c.rollback()
    assert kelola.get(f"/api/checklist/item/{i['id']}/riwayat").json()[0]["judul"].endswith("(diubah)")


def test_panduan_berversi_dan_dipakai_review(klien):
    import io
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    pdf = buat_pdf(["Pasal 5", "(1) Indikator keluaran wajib memuat target kuantitatif dan satuan.",
                    "(2) Honor narasumber paling tinggi Rp1.700.000 per orang jam."])
    assert kelola.post("/api/panduan", files={"file": ("pmk.pdf", io.BytesIO(pdf), "application/pdf")},
                      data={"judul": "x" * 501}).status_code == 400  # ditolak sebelum PDF disimpan
    pd = kelola.post("/api/panduan", files={"file": ("pmk.pdf", io.BytesIO(pdf), "application/pdf")},
                    data={"judul": "pmk", "deskripsi": "Standar biaya", "aktif": "true"}).json()
    assert pd["terkini"]["status_proses"] == "BELUM" and pd["aktif"] and pd["diubah_oleh"] and pd["terkini"]["deskripsi"] == "Standar biaya"
    assert pd["terkini"]["dibuat_oleh"] == pd["diubah_oleh"]  # akun yang membuat versi
    jalankan_antrean()
    daftar = kelola.get("/api/panduan").json()
    assert daftar[0]["terkini"]["status_proses"] == "SIAP"
    ubah = kelola.put(f"/api/panduan/{pd['id']}", data={"judul": "PMK Standar Biaya"}).json()
    assert ubah["terkini"]["nomor"] == 2 and len(ubah["versi"]) == 2
    pengusul, u = _usulan_diajukan(klien)
    jalankan_antrean()
    rv = _review(klien, pengusul.get(f'/api/usulan/{u['id']}').json()['review_id'])
    assert rv["acuan"]["panduan"][0]["judul"] == "PMK Standar Biaya"
    dasar = [r for i in rv["item"] for r in i["rujukan"] if r["peran"] == "dasar_panduan"]
    assert all(r["nama_acuan"] == "PMK Standar Biaya" for r in dasar)  # kolom Rujukan Checklist: Nama Acuan tanpa versi
    assert dasar and all(r["dokumen"] == "PANDUAN" for r in dasar)
    assert rv["acuan"]["panduan"][0]["nomor"] == 2  # review mencatat versi panduan yang dipakai (D5)
    nonaktif = kelola.put(f"/api/panduan/{pd['id']}", data={"judul": "PMK Standar Biaya", "aktif": "false"}).json()
    assert nonaktif["aktif"] is False and nonaktif["terkini"]["nomor"] == 3 and nonaktif["terkini"]["aktif"] is False
    assert [x["aktif"] for x in nonaktif["versi"]] == [False, True, True]  # status tercatat per versi
    sama = kelola.put(f"/api/panduan/{pd['id']}", data={"judul": "PMK Standar Biaya", "aktif": "false"}).json()
    assert sama["terkini"]["nomor"] == 3  # simpan tanpa perubahan tidak membuat versi
    # Database: versi terkini hanya di `panduan`; `panduan_histori` hanya riwayat (v1, v2).
    with SessionLokal() as db:
        pid = uuid.UUID(pd["id"])
        pdb = db.get(Panduan, pid)
        assert pdb.created_by and pdb.created_by == pdb.updated_by  # admin yang sama mengunggah & mengedit
        # Riwayat urut updated_date = versi 1, 2; terkini = versi 3 (nomor versi tidak disimpan).
        assert [v.panduan for v in pdb.versi] == ["pmk", "PMK Standar Biaya"] and pdb.daftar_versi()[0][0] == 3
        assert {v.created_by for v in pdb.versi} == {pdb.created_by}  # riwayat menyalin pengunggah pertama
    assert _review(klien, rv['id'])["acuan"]["panduan"][0]["nomor"] == 2  # catatan review tidak berubah (D5)
    assert pengusul.get(f"/api/file/{pd['terkini']['file_id']}").status_code == 200  # PDF panduan terbuka untuk semua pengguna
    assert kelola.get("/api/panduan").json()[0]["aktif"] is False  # tetap tampil di daftar
    _, u2 = _usulan_diajukan(klien)
    jalankan_antrean()
    rv2 = _review(klien, pengusul.get(f'/api/usulan/{u2['id']}').json()['review_id'])
    assert rv2["acuan"]["panduan"] == []  # Nonaktif → tidak dipakai review
    # Hapus = permanen: panduan, versi, file & ekstraksinya hilang; review lama tetap terbuka tanpa rujukan panduan.
    assert kelola.delete(f"/api/panduan/{pd['id']}").status_code == 200
    assert kelola.get("/api/panduan").json() == []
    assert kelola.get(f"/api/file/{pd['terkini']['file_id']}").status_code == 404
    rv_lama = _review(klien, rv['id'])
    assert rv_lama["acuan"]["panduan"] == [] and not [r for i in rv_lama["item"] for r in i["rujukan"] if r["peran"] == "dasar_panduan"]
    assert kelola.get("/api/panduan/versi").status_code in (404, 405, 422)  # versi daftar panduan sudah dihapus


def test_panduan_tidak_macet_bila_worker_mati_berulang(klien):
    """Worker mati 3× saat memproses panduan → file GAGAL (bukan "Diproses" selamanya) dan dapat diproses ulang."""
    import io
    from datetime import datetime, timedelta, timezone

    from app.model import File, Job
    from app.pekerja.utama import lepas_job_macet
    kelola = klien("reviewer")  # Reviewer mengelola Checklist/Kategori/Panduan
    pd = kelola.post("/api/panduan", files={"file": ("p.pdf", io.BytesIO(buat_pdf(["Pasal 1 uji macet"])), "application/pdf")},
                    data={"judul": "p"}).json()
    fid = uuid.UUID(pd["terkini"]["file_id"])
    with SessionLokal() as db:  # keadaan setelah worker mati pada percobaan ke-3
        db.execute(update(Job).where(Job.ref_id == fid).values(
            status="DIPROSES", percobaan=3, dikunci_at=datetime.now(timezone.utc) - timedelta(hours=1)))
        db.execute(update(File).where(File.id == fid).values(status_ekstraksi="DIPROSES"))
        db.commit()
    lepas_job_macet()
    assert kelola.get("/api/panduan").json()[0]["terkini"]["status_proses"] == "GAGAL"
    assert kelola.post(f"/api/panduan/{pd['id']}/proses-ulang").json()["terkini"]["status_proses"] == "BELUM"


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


def test_ajukan_bersamaan_diproses_bergiliran(klien):
    """Endpoint yang mengubah pengajuan mengunci baris usulan dulu: permintaan kedua menunggu, lalu melihat status terbaru
    (di sini revisi sudah Antre oleh "permintaan pertama") sehingga ditolak 409 — tidak ada review AI ganda."""
    p, u = _usulan_diajukan(klien, ajukan=False)
    uid, hasil = uuid.UUID(u["id"]), {}
    t = threading.Thread(target=lambda: hasil.setdefault("ajukan", p.post(f"/api/usulan/{uid}/ajukan").status_code))
    with SessionLokal() as db:
        db.execute(select(Usulan).where(Usulan.id == uid).with_for_update(of=Usulan))  # "permintaan pertama" memegang kunci
        t.start()
        t.join(1)
        assert t.is_alive()  # permintaan kedua menunggu kunci
        db.execute(update(Revisi).where(Revisi.usulan_id == uid).values(status="ANTRE"))
        db.commit()
    t.join(10)
    assert hasil["ajukan"] == 409
    with SessionLokal() as db:
        assert db.scalar(select(func.count()).select_from(Review).join(Revisi, Revisi.id == Review.revisi_id)
                         .where(Revisi.usulan_id == uid)) == 0
