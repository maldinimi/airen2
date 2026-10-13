"""Transisi status revisi (PRD §5). Semua perubahan `revisi.status` WAJIB lewat `pindah_status`."""
from app.galat import Galat

DRAF, ANTRE, DIPROSES_AI, GAGAL = "DRAF", "ANTRE", "DIPROSES_AI", "GAGAL"
MENUNGGU_VERIFIKASI, LOLOS, TIDAK_LOLOS = "MENUNGGU_VERIFIKASI", "LOLOS", "TIDAK_LOLOS"

TRANSISI: dict[str, set[str]] = {
    DRAF: {ANTRE},
    ANTRE: {DIPROSES_AI, GAGAL},
    # DIPROSES_AI → ANTRE terjadi bila worker mati dan job dilepas kembali ke antrean.
    DIPROSES_AI: {MENUNGGU_VERIFIKASI, GAGAL, ANTRE},
    GAGAL: {ANTRE},  # review gagal boleh diajukan ulang (belum ada hasil yang dilihat siapa pun)
    MENUNGGU_VERIFIKASI: {LOLOS, TIDAK_LOLOS},
    LOLOS: set(),
    TIDAK_LOLOS: set(),
}

# Dokumen hanya boleh diganti saat belum ada hasil AI pada revisi tersebut.
BOLEH_UBAH_DOKUMEN = {DRAF, GAGAL}
# Revisi baru hanya setelah hasil final TIDAK LOLOS (diagram PRD §5).
BOLEH_REVISI_BARU = {TIDAK_LOLOS}
BOLEH_AJUKAN = {DRAF, GAGAL}

NAMA_STATUS = {
    DRAF: "Belum direview", ANTRE: "Antre", DIPROSES_AI: "Diproses AI", GAGAL: "Gagal",
    MENUNGGU_VERIFIKASI: "Menunggu verifikasi reviewer", LOLOS: "Lolos", TIDAK_LOLOS: "Tidak lolos",
}


def pindah_status(revisi, ke: str) -> None:
    """Ubah status revisi bila transisinya sah.

    Error: `Galat` 409 bila transisi tidak diizinkan.
    """
    if ke not in TRANSISI.get(revisi.status, set()):
        raise Galat(409, f"Status tidak dapat diubah dari '{NAMA_STATUS.get(revisi.status, revisi.status)}' "
                         f"ke '{NAMA_STATUS.get(ke, ke)}'.")
    revisi.status = ke
