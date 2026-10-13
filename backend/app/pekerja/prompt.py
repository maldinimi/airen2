"""Prompt & skema JSON untuk setiap tugas LLM. Skema dipaksakan lewat guided decoding (vLLM),
dan ID rujukan dibatasi `enum` alias yang ada di konteks sehingga LLM tidak dapat mengarang ID.

PROMPT_VERSI masuk fingerprint (desain §4.6) — naikkan setiap kali prompt/skema diubah.
"""
PROMPT_VERSI = "2026.10.1"

SISTEM = (
    "Anda adalah reviewer dokumen usulan anggaran pemerintah (TOR dan RAB) yang sangat teliti. "
    "Nalar secara mendalam sebelum menjawab, jangan sekadar mencocokkan kata kunci. "
    "Gunakan HANYA potongan dokumen yang diberikan; setiap potongan diawali ID dalam kurung siku, misalnya [E3] untuk "
    "TOR/RAB dan [P2] untuk Panduan. Jangan pernah mengarang isi dokumen, isi panduan, maupun rujukan. "
    "Setiap rujukan WAJIB berisi ID potongan dan kutipan yang disalin PERSIS dari teks potongan tersebut "
    "(boleh sebagian, minimal satu frasa utuh). Jika informasi tidak ada, katakan tidak ditemukan. "
    "Seluruh jawaban dalam Bahasa Indonesia yang baku dan jelas. Jawab hanya dengan JSON sesuai skema."
)


def _skema_rujukan(alias: list[str]) -> dict:
    if not alias:
        return {"type": "array", "maxItems": 0, "items": {"type": "object"}}
    return {"type": "array", "maxItems": 6, "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "kutipan"],
        "properties": {"id": {"type": "string", "enum": alias}, "kutipan": {"type": "string"}}}}


def skema_nilai_item(alias_dok: list[str], alias_panduan: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False,
            "required": ["ditemukan", "terpenuhi", "alasan", "yang_kurang", "bukti", "dasar_panduan"],
            "properties": {
                "ditemukan": {"type": "boolean"}, "terpenuhi": {"type": "boolean"},
                "alasan": {"type": "string"}, "yang_kurang": {"type": "string"},
                "bukti": _skema_rujukan(alias_dok), "dasar_panduan": _skema_rujukan(alias_panduan)}}


def skema_sapuan(alias_dok: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["ada", "bukti"],
            "properties": {"ada": {"type": "boolean"}, "bukti": _skema_rujukan(alias_dok)}}


def skema_keselarasan(alias_dok: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["ringkasan", "temuan"], "properties": {
        "ringkasan": {"type": "string"},
        "temuan": {"type": "array", "maxItems": 15, "items": {
            "type": "object", "additionalProperties": False, "required": ["jenis", "uraian", "bukti"],
            "properties": {"jenis": {"type": "string", "enum": ["RAB_TANPA_DASAR_TOR", "TOR_TANPA_ANGGARAN", "TIDAK_SELARAS"]},
                           "uraian": {"type": "string"}, "bukti": _skema_rujukan(alias_dok)}}}}}


def skema_rekomendasi(kode_item: list[str], alias_panduan: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["rekomendasi"], "properties": {
        "rekomendasi": {"type": "array", "maxItems": 20, "items": {
            "type": "object", "additionalProperties": False, "required": ["teks", "kode_item", "dasar_panduan"],
            "properties": {"teks": {"type": "string"}, "kode_item": {"type": "string", "enum": kode_item + [""]},
                           "dasar_panduan": _skema_rujukan(alias_panduan)}}}}}


def skema_kategori(kode: list[str], alias_dok: list[str], alias_panduan: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["kode", "alasan", "bukti", "dasar_panduan"],
            "properties": {"kode": {"type": "string", "enum": kode}, "alasan": {"type": "string"},
                           "bukti": _skema_rujukan(alias_dok), "dasar_panduan": _skema_rujukan(alias_panduan)}}


SKEMA_GAMBAR = {"type": "object", "additionalProperties": False, "required": ["deskripsi"],
                "properties": {"deskripsi": {"type": "string"}}}


def prompt_nilai_item(item, konteks_dok: str, konteks_panduan: str, umpan_balik: str | None) -> str:
    teks = (
        f"Nilai apakah dokumen memenuhi item checklist berikut.\n\n"
        f"ITEM {item.kode} — {item.judul}\nBerlaku untuk: {item.berlaku_untuk}\nKriteria pemenuhan: {item.kriteria}\n\n"
        f"ATURAN:\n"
        f"- terpenuhi=true HANYA jika isi TOR/RAB memenuhi kriteria DAN sesuai ketentuan Panduan yang relevan, "
        f"bukan sekadar menyebutkan topiknya.\n"
        f"- ditemukan=false jika sama sekali tidak ada bagian dokumen yang membahas kriteria ini; maka terpenuhi=false dan bukti kosong.\n"
        f"- 'bukti' berisi rujukan potongan TOR/RAB [E..]; 'dasar_panduan' berisi rujukan potongan Panduan [P..] yang menjadi dasar penilaian.\n"
        f"- 'alasan' menjelaskan penilaian; 'yang_kurang' menyebut secara konkret apa yang belum ada/kurang (kosongkan bila terpenuhi).\n\n"
        f"POTONGAN DOKUMEN (TOR/RAB):\n{konteks_dok or '(tidak ada potongan yang relevan)'}\n\n"
        f"POTONGAN PANDUAN:\n{konteks_panduan or '(tidak ada panduan yang relevan)'}\n"
    )
    if umpan_balik:
        teks += f"\nPERHATIAN — jawaban sebelumnya memuat rujukan tidak valid: {umpan_balik}. Perbaiki: pakai ID yang ada dan kutipan persis.\n"
    return teks


def prompt_sapuan(item, konteks_dok: str) -> str:
    return (f"Apakah ada bagian pada potongan dokumen berikut yang menjawab kriteria ini?\n"
            f"Kriteria ({item.kode} — {item.judul}): {item.kriteria}\n\n"
            f"Jawab ada=true beserta bukti bila ada; ada=false dan bukti kosong bila tidak ada.\n\nPOTONGAN:\n{konteks_dok}\n")


def prompt_keselarasan(konteks: str) -> str:
    return ("Periksa keselarasan RAB dengan TOR: apakah RAB mampu menceritakan penganggaran berdasarkan kegiatan dan "
            "keluaran yang dituangkan di TOR. Petakan komponen biaya RAB ke kegiatan/keluaran TOR, lalu catat sebagai temuan:\n"
            "- RAB_TANPA_DASAR_TOR: komponen biaya RAB yang tidak memiliki dasar kegiatan di TOR;\n"
            "- TOR_TANPA_ANGGARAN: kegiatan/keluaran TOR yang tidak dianggarkan di RAB;\n"
            "- TIDAK_SELARAS: volume/satuan/waktu yang tidak konsisten antara TOR dan RAB.\n"
            "Sertakan bukti dari kedua dokumen bila ada. Bila selaras, temuan kosong.\n\n"
            f"POTONGAN RAB DAN TOR:\n{konteks}\n")


def prompt_rekomendasi(dokumen: str, masalah: str, konteks_panduan: str) -> str:
    return (f"Susun rekomendasi perbaikan {dokumen} agar dokumen menjadi LOLOS. Setiap rekomendasi berupa langkah konkret "
            f"yang dapat langsung dikerjakan penyusun {dokumen}, merujuk ketentuan Panduan bila relevan (isi dasar_panduan), "
            f"dan kode_item diisi kode item checklist yang diperbaiki (kosong untuk temuan keselarasan).\n\n"
            f"MASALAH YANG DITEMUKAN:\n{masalah}\n\nPOTONGAN PANDUAN:\n{konteks_panduan or '(tidak ada panduan yang relevan)'}\n")


def prompt_kategori(definisi: str, konteks_dok: str, konteks_panduan: str) -> str:
    return ("Tentukan SATU kategori prioritas anggaran yang paling tepat untuk Rincian Output (RO) ini berdasarkan "
            "definisi kategori di bawah (gunakan definisi ini apa adanya). Perhatikan dasar hukum, penetapan oleh Menteri, "
            "keterkaitan dengan prioritas pembangunan nasional, sasaran kementerian, serta tugas dan fungsi Satker. "
            "Alasan WAJIB mengacu pada definisi kategori yang dipilih dan menjelaskan mengapa kategori yang lebih tinggi "
            "tidak terpenuhi.\n\n"
            f"DEFINISI KATEGORI:\n{definisi}\n\nPOTONGAN DOKUMEN:\n{konteks_dok}\n\nPOTONGAN PANDUAN:\n{konteks_panduan or '(tidak ada)'}\n")


PROMPT_GAMBAR = ("Deskripsikan gambar/grafik/diagram/tabel pada potongan halaman dokumen anggaran ini secara faktual dalam "
                 "Bahasa Indonesia: jenis visual, judul, label, angka-angka penting, dan pesan utamanya. Jangan menebak "
                 "hal yang tidak terlihat. Bila berupa halaman hasil scan berisi teks, tuliskan ulang isinya.")
