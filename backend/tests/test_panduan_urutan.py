"""Uji Atur Urutan Panduan: panduan baru di urutan akhir, urutan disimpan Reviewer, rapat lagi setelah hapus,
daftar yang tidak lengkap ditolak, dan hanya Reviewer yang boleh mengatur urutan."""
import io

from tests.conftest import buat_pdf


def _unggah(c, judul: str) -> dict:
    pdf = buat_pdf([f"Isi panduan {judul}."])  # isi berbeda → file (SHA-256) berbeda
    r = c.post("/api/panduan", files={"file": (f"{judul}.pdf", io.BytesIO(pdf), "application/pdf")}, data={"judul": judul})
    assert r.status_code == 200, r.text
    return r.json()


def test_panduan_atur_urutan(klien):
    rv = klien("reviewer")
    a, b, c = (_unggah(rv, j) for j in ("Bravo", "Alfa", "Charlie"))
    # Panduan baru selalu di akhir (bukan urut abjad).
    daftar = rv.get("/api/panduan").json()
    assert [(d["judul"], d["urutan"]) for d in daftar] == [("Bravo", 1), ("Alfa", 2), ("Charlie", 3)]

    r = rv.put("/api/panduan/urutan", json={"id": [c["id"], a["id"], b["id"]]})
    assert r.status_code == 200 and [d["judul"] for d in r.json()] == ["Charlie", "Bravo", "Alfa"]
    daftar = rv.get("/api/panduan").json()
    assert [(d["judul"], d["urutan"]) for d in daftar] == [("Charlie", 1), ("Bravo", 2), ("Alfa", 3)]
    # Mengatur urutan tidak membuat versi baru.
    assert all(len(d["versi"]) == 1 for d in daftar)

    # Daftar tidak lengkap / berisi id asing → ditolak.
    assert rv.put("/api/panduan/urutan", json={"id": [c["id"], a["id"]]}).status_code == 400
    assert rv.put("/api/panduan/urutan", json={"id": [c["id"], a["id"], "00000000-0000-0000-0000-000000000000"]}).status_code == 400

    # Setelah hapus, no_urut sisanya dirapatkan jadi 1..n.
    assert rv.delete(f"/api/panduan/{b['id']}").status_code == 200  # b = Alfa
    daftar = rv.get("/api/panduan").json()
    assert [(d["judul"], d["urutan"]) for d in daftar] == [("Charlie", 1), ("Bravo", 2)]


def test_panduan_atur_urutan_hanya_reviewer(klien):
    rv = klien("reviewer")
    a = _unggah(rv, "Alfa")
    for c in (klien("pengusul"), klien("admin", "GantiSegera!2026")):
        assert c.put("/api/panduan/urutan", json={"id": [a["id"]]}).status_code == 403


def test_pdf_panduan_hanya_reviewer_dan_pengusul(klien):
    """PDF panduan mengikuti hak baca daftar Panduan: Reviewer & Pengusul boleh, Admin 404 (tidak membocorkan file)."""
    rv = klien("reviewer")
    fid = _unggah(rv, "Alfa")["terkini"]["file_id"]
    assert rv.get(f"/api/file/{fid}").status_code == 200
    assert klien("pengusul").get(f"/api/file/{fid}").status_code == 200
    assert klien("admin", "GantiSegera!2026").get(f"/api/file/{fid}").status_code == 404
