#!/bin/sh
# Verifikasi B1 (make cek-offline): stack berjalan tanpa jalur keluar ke internet.
# 1) Jaringan Docker `internal` bertanda internal (tanpa gateway).
# 2) Dari dalam kontainer api & worker: DNS publik dan koneksi TCP ke internet harus GAGAL.
# 3) Build frontend tidak memuat aset dari domain luar (cek-offline.mjs dijalankan saat build image web).
set -e
PROYEK=${COMPOSE_PROJECT_NAME:-airen}
JARINGAN="${PROYEK}_internal"
[ "$(docker network inspect -f '{{.Internal}}' "$JARINGAN")" = "true" ] && echo "[OK] jaringan $JARINGAN internal (tanpa gateway keluar)" || { echo "[GAGAL] $JARINGAN bukan jaringan internal"; exit 1; }

UJI='import socket,sys
for host,port in (("1.1.1.1",443),("8.8.8.8",53),("huggingface.co",443)):
    try:
        socket.create_connection((host,port),timeout=5).close(); print("TERHUBUNG",host); sys.exit(1)
    except OSError: pass
print("tidak ada koneksi keluar")'
for layanan in api worker; do
  if docker compose ps --status running "$layanan" | grep -q "$layanan"; then
    docker compose exec -T "$layanan" python -c "$UJI" && echo "[OK] $layanan: $(echo tidak ada koneksi keluar)" || { echo "[GAGAL] $layanan dapat terhubung ke internet"; exit 1; }
  fi
done
echo "Verifikasi offline selesai. Uji otomatis tambahan: tests/test_alur.py::test_tidak_ada_koneksi_keluar_selama_review"
