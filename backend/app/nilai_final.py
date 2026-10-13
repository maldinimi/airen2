"""Aturan label (PRD §7.1) dan perhitungan nilai final (PRD O1–O8, desain §3.4).

Satu-satunya tempat aturan ini diimplementasikan; dipakai worker (label AI), API (tampilan,
finalisasi), dan pengujian. Nilai final tidak disimpan ganda — selalu dihitung dari hasil AI
+ override aktif, kecuali snapshot terkunci saat Finalkan.
"""
from collections.abc import Iterable
from dataclasses import dataclass, field

LOLOS, TIDAK_LOLOS = "LOLOS", "TIDAK_LOLOS"
TERPENUHI, TIDAK_TERPENUHI = "TERPENUHI", "TIDAK_TERPENUHI"


def hitung_label(status_item: Iterable[bool]) -> str:
    """LOLOS ⇔ SEMUA item terpenuhi. Satu item tidak terpenuhi → TIDAK LOLOS. Tidak ada nilai parsial.

    Daftar kosong dianggap TIDAK LOLOS: tanpa item checklist tidak ada yang dapat dibuktikan.
    """
    daftar = list(status_item)
    return LOLOS if daftar and all(daftar) else TIDAK_LOLOS


@dataclass
class NilaiFinal:
    item: dict[str, bool]  # checklist_item_id → terpenuhi (final)
    item_diubah: set[str] = field(default_factory=set)
    label_hitung: str = TIDAK_LOLOS  # dihitung ulang dari item final (O6)
    label: str = TIDAK_LOLOS  # label final
    label_diubah: bool = False
    label_tidak_konsisten: bool = False  # override label ≠ label hitung-ulang → peringatan (O6)
    kategori_id: str | None = None
    kategori_diubah: bool = False

    @property
    def jumlah_terpenuhi(self) -> int:
        return sum(self.item.values())


def override_aktif(overrides: Iterable) -> dict[tuple[str, str | None], object]:
    """Override aktif terakhir per target (ITEM per item, LABEL, KATEGORI). Yang dibatalkan diabaikan."""
    aktif: dict[tuple[str, str | None], object] = {}
    for o in sorted(overrides, key=lambda o: o.created_at):
        if o.dibatalkan_at is None:
            kunci = (o.target, str(o.checklist_item_id) if o.checklist_item_id else None)
            aktif[kunci] = o
    return aktif


def hitung_nilai_final(item_ai: dict[str, bool], kategori_ai_id: str | None, overrides: Iterable) -> NilaiFinal:
    """Nilai final = nilai override aktif bila ada, selain itu nilai AI (O8).

    Input: `item_ai` (id item → terpenuhi menurut AI), `kategori_ai_id`, daftar override (objek dengan
    target, checklist_item_id, nilai_sesudah, created_at, dibatalkan_at).
    """
    aktif = override_aktif(overrides)
    hasil = NilaiFinal(item=dict(item_ai), kategori_id=kategori_ai_id)
    for (target, item_id), o in aktif.items():
        if target == "ITEM" and item_id in hasil.item:
            hasil.item[item_id] = o.nilai_sesudah == TERPENUHI
            hasil.item_diubah.add(item_id)
    hasil.label_hitung = hitung_label(hasil.item.values())
    hasil.label = hasil.label_hitung
    if (o := aktif.get(("LABEL", None))) is not None:
        hasil.label = o.nilai_sesudah
        hasil.label_diubah = True
        hasil.label_tidak_konsisten = hasil.label != hasil.label_hitung
    if (o := aktif.get(("KATEGORI", None))) is not None:
        hasil.kategori_id = o.nilai_sesudah
        hasil.kategori_diubah = True
    return hasil
