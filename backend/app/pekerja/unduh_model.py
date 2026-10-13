"""Unduh model AI ke `<DATA_DIR>/models` — HANYA dijalankan saat persiapan (`make setup`), bukan saat runtime (B1).

Model yang diunduh mengikuti `.env`: LLM_MODEL, EMBEDDING_MODEL, RERANKER_MODEL, serta model layout/tabel Docling.
Mode tiruan tidak membutuhkan model apa pun.
"""
import os
import subprocess
import sys

from app.konfigurasi import konfigurasi


def main() -> None:
    k = konfigurasi()
    if k.tiruan:
        print("Mode AI tiruan: tidak ada model yang perlu diunduh.")
        return
    from huggingface_hub import snapshot_download

    folder = os.path.join(k.data_dir, "models")
    for nama in (k.llm_model, k.embedding_model, k.reranker_model):
        tujuan = os.path.join(folder, nama)
        print(f"Mengunduh {nama} → {tujuan} …", flush=True)
        snapshot_download(nama, local_dir=tujuan)
    print("Mengunduh model Docling (layout, tabel) …", flush=True)
    subprocess.run(["docling-tools", "models", "download", "-o", os.path.join(folder, "docling"), "layout", "tableformer",
                    "picture_classifier"], check=True)
    print("Selesai. Aplikasi kini dapat berjalan tanpa internet.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # pesan ramah untuk `make setup`
        print(f"Gagal mengunduh model: {e}\nPeriksa koneksi internet, ruang disk, dan nama model di .env.", file=sys.stderr)
        sys.exit(1)
