"""Uji unit logika inti tanpa database: aturan label §7.1, nilai final & override O1–O8,
transisi status §5, verifikasi rujukan E3, fingerprint §4.6."""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from alembic.script import ScriptDirectory

from app import status as st
from app.galat import Galat
from app.migrasi import konfigurasi_alembic
from app.nilai_final import LOLOS, TERPENUHI, TIDAK_LOLOS, TIDAK_TERPENUHI, hitung_label, hitung_nilai_final
from app.pekerja.rujukan import cocokkan_kutipan, nomor_kalimat, verifikasi
from app.pekerja.sidik import fingerprint

T0 = datetime(2026, 10, 12, tzinfo=timezone.utc)


@dataclass
class O:
    target: str
    nilai_sesudah: str
    created_at: datetime
    checklist_item_id: uuid.UUID | None = None
    dibatalkan_at: datetime | None = None


# ------------------------------------------------------------------ aturan label
def test_label_lolos_hanya_bila_semua_terpenuhi():
    assert hitung_label([True, True, True]) == LOLOS
    assert hitung_label([True, False, True]) == TIDAK_LOLOS
    assert hitung_label([False]) == TIDAK_LOLOS


def test_label_tanpa_item_tidak_lolos():
    assert hitung_label([]) == TIDAK_LOLOS


# ------------------------------------------------------------------ nilai final & override
A, B = uuid.uuid4(), uuid.uuid4()
K_AI, K_LAIN = str(uuid.uuid4()), str(uuid.uuid4())


def test_tanpa_override_nilai_final_sama_dengan_ai():
    nf = hitung_nilai_final({str(A): True, str(B): False}, K_AI, [])
    assert nf.label == TIDAK_LOLOS and nf.kategori_id == K_AI and not nf.item_diubah


def test_override_item_menghitung_ulang_label():
    nf = hitung_nilai_final({str(A): True, str(B): False}, K_AI, [O("ITEM", TERPENUHI, T0, B)])
    assert nf.item[str(B)] is True and nf.label_hitung == LOLOS and nf.label == LOLOS
    assert nf.item_diubah == {str(B)} and not nf.label_tidak_konsisten


def test_override_terakhir_yang_aktif_menang_dan_pembatalan_diabaikan():
    o = [O("ITEM", TERPENUHI, T0, B), O("ITEM", TIDAK_TERPENUHI, T0 + timedelta(minutes=1), B),
         O("ITEM", TERPENUHI, T0 + timedelta(minutes=2), B, dibatalkan_at=T0 + timedelta(minutes=3))]
    nf = hitung_nilai_final({str(A): True, str(B): True}, K_AI, o)
    assert nf.item[str(B)] is False and nf.label == TIDAK_LOLOS


def test_batal_semua_override_kembali_ke_nilai_ai():
    o = [O("ITEM", TERPENUHI, T0, B, dibatalkan_at=T0), O("KATEGORI", K_LAIN, T0, dibatalkan_at=T0)]
    nf = hitung_nilai_final({str(A): True, str(B): False}, K_AI, o)
    assert nf.label == TIDAK_LOLOS and nf.kategori_id == K_AI and not nf.kategori_diubah


def test_override_label_tidak_konsisten_ditandai():
    nf = hitung_nilai_final({str(A): True, str(B): False}, K_AI, [O("LABEL", LOLOS, T0)])
    assert nf.label == LOLOS and nf.label_hitung == TIDAK_LOLOS and nf.label_tidak_konsisten


def test_override_kategori():
    nf = hitung_nilai_final({str(A): True}, K_AI, [O("KATEGORI", K_LAIN, T0)])
    assert nf.kategori_id == K_LAIN and nf.kategori_diubah


# ------------------------------------------------------------------ transisi status
@dataclass
class R:
    status: str


@pytest.mark.parametrize("dari,ke", [(st.DRAF, st.ANTRE), (st.ANTRE, st.DIPROSES_AI), (st.DIPROSES_AI, st.MENUNGGU_VERIFIKASI),
                                     (st.DIPROSES_AI, st.GAGAL), (st.GAGAL, st.ANTRE), (st.MENUNGGU_VERIFIKASI, st.LOLOS),
                                     (st.MENUNGGU_VERIFIKASI, st.TIDAK_LOLOS)])
def test_transisi_sah(dari, ke):
    r = R(dari)
    st.pindah_status(r, ke)
    assert r.status == ke


@pytest.mark.parametrize("dari,ke", [(st.DRAF, st.LOLOS), (st.MENUNGGU_VERIFIKASI, st.ANTRE), (st.LOLOS, st.TIDAK_LOLOS),
                                     (st.TIDAK_LOLOS, st.ANTRE), (st.DIPROSES_AI, st.LOLOS)])
def test_transisi_tidak_sah(dari, ke):
    with pytest.raises(Galat):
        st.pindah_status(R(dari), ke)


def test_aturan_status_alur():
    assert st.BOLEH_REVISI_BARU == {st.TIDAK_LOLOS}
    assert st.MENUNGGU_VERIFIKASI not in st.BOLEH_UBAH_DOKUMEN and st.DIPROSES_AI not in st.BOLEH_UBAH_DOKUMEN


# ------------------------------------------------------------------ verifikasi rujukan
TEKS = "Kegiatan dilaksanakan pada Januari–Desember 2027. Penerima manfaat: masyarakat umum,  dan ASN."


def test_kutipan_dinormalisasi_dan_dikembalikan_teks_asli():
    asli = cocokkan_kutipan(TEKS, "penerima manfaat masyarakat umum dan asn")
    assert asli == "Penerima manfaat: masyarakat umum,  dan ASN"
    assert asli in TEKS


def test_kutipan_karangan_ditolak():
    assert cocokkan_kutipan(TEKS, "penerima manfaat adalah pelajar") is None


def test_kutipan_kosong_memakai_awal_teks_dan_elipsis_diterima():
    assert cocokkan_kutipan(TEKS, "") == TEKS[:300].strip()
    assert cocokkan_kutipan(TEKS, "Kegiatan dilaksanakan pada Januari…") in TEKS


@dataclass
class E:
    teks: str
    id: uuid.UUID = uuid.uuid4()


def test_verifikasi_membuang_id_asing_dan_kutipan_salah():
    peta = {"E1": E(TEKS)}
    sah, salah = verifikasi([{"id": "E1", "kutipan": "Januari–Desember 2027"}, {"id": "E9", "kutipan": "x"},
                             {"id": "E1", "kutipan": "tidak ada di teks"}], peta, "bukti_dokumen")
    assert len(sah) == 1 and sah[0].kutipan in TEKS and len(salah) == 2


def test_nomor_kalimat():
    assert nomor_kalimat(TEKS, "Penerima manfaat") == 2
    assert nomor_kalimat("Satu kalimat saja", "kalimat") is None


# ------------------------------------------------------------------ fingerprint
def test_fingerprint_stabil_dan_peka_perubahan():
    m = {"model": "x", "prompt_versi": "1", "embedding": "e", "reranker": "r", "ekstraktor": "d", "profil": "dev"}
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    dasar = fingerprint("a", "b", 1, 2, [p1, p2], m)
    assert dasar == fingerprint("a", "b", 1, 2, [p2, p1], {**m, "profil": "lain"})  # urutan panduan tidak berpengaruh
    assert dasar != fingerprint("a", "c", 1, 2, [p1, p2], m)
    assert dasar != fingerprint("a", "b", 1, 2, [p1], m)
    assert dasar != fingerprint("a", "b", 1, 2, [p1, p2], {**m, "model": "y"})


# ------------------------------------------------------------------ migrasi
def test_rantai_migrasi_utuh():
    """Semua file migrasi dapat dimuat dan hanya ada satu head. Tes lain membuat skema dengan create_all, sehingga
    induk migrasi yang hilang hanya ketahuan di sini, bukan saat `make up` gagal."""
    assert len(ScriptDirectory.from_config(konfigurasi_alembic()).get_heads()) == 1
