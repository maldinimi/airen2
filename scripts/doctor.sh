#!/bin/sh
# Pemeriksaan prasyarat (make doctor). Pesan perbaikan dalam Bahasa Indonesia.
ok() { printf "  [OK]    %s\n" "$1"; }
gagal() { printf "  [GAGAL] %s\n          → %s\n" "$1" "$2"; MASALAH=1; }
info() { printf "  [INFO]  %s\n" "$1"; }
MASALAH=0
nilai() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2-; }

echo "Pemeriksaan AIREN"
command -v docker >/dev/null && ok "Docker terpasang" || gagal "Docker tidak ditemukan" "Pasang Docker Desktop (Windows/Mac) atau Docker Engine (Linux)."
docker info >/dev/null 2>&1 && ok "Docker daemon berjalan" || gagal "Docker daemon tidak berjalan" "Jalankan Docker Desktop / sudo systemctl start docker."
docker compose version >/dev/null 2>&1 && ok "Docker Compose v2 tersedia" || gagal "Docker Compose v2 tidak ada" "Perbarui Docker."
[ -f .env ] && ok ".env ada (profil: $(nilai PROFIL))" || gagal ".env belum ada" "cp .env.tiruan .env   (atau .env.dev / .env.prod)"

MODE=$(nilai AI_MODE)
if [ "$MODE" = "nyata" ] && [ "$(nilai WORKER_REPLIKA)" != "0" ]; then
  if docker info 2>/dev/null | grep -qi nvidia; then ok "NVIDIA Container Toolkit terdeteksi"
  else gagal "Runtime GPU NVIDIA tidak terdeteksi di Docker" "Pasang NVIDIA Container Toolkit (Linux) atau aktifkan GPU di Docker Desktop + WSL2. Tanpa GPU: gunakan .env.tiruan."; fi
  if command -v nvidia-smi >/dev/null 2>&1; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
    [ -n "$VRAM" ] && info "VRAM GPU: ${VRAM} MiB"
    case "$(nilai PROFIL)" in dev) [ "${VRAM:-0}" -ge 15000 ] 2>/dev/null && ok "VRAM cukup untuk model dev (≥16 GB)" || gagal "VRAM kurang dari 16 GB" "Gunakan GPU 16 GB atau .env.tiruan." ;; esac
  fi
  MODEL=$(nilai LLM_MODEL)
  [ -f "data/models/$MODEL/config.json" ] && ok "Model $MODEL sudah diunduh" || gagal "Model $MODEL belum diunduh" "Jalankan: make setup (butuh internet)."
  [ -d "data/models/$(nilai EMBEDDING_MODEL)" ] && ok "Model embedding ada" || gagal "Model embedding belum diunduh" "Jalankan: make setup."
else
  info "Mode AI tiruan / tanpa worker lokal — GPU & model tidak diperlukan"
fi

PORT=$(nilai PORT_WEB); PORT=${PORT:-8080}
if docker compose ps --status running 2>/dev/null | grep -q web; then ok "Aplikasi berjalan di port $PORT"
elif (command -v ss >/dev/null && ss -ltn | grep -q ":$PORT ") || (command -v netstat >/dev/null && netstat -an 2>/dev/null | grep -q "[:.]$PORT .*LISTEN"); then
  gagal "Port $PORT sudah dipakai program lain" "Ubah PORT_WEB di .env."
else ok "Port $PORT bebas"; fi

[ $MASALAH -eq 0 ] && echo "Semua pemeriksaan lolos." || { echo "Ada masalah; perbaiki sesuai petunjuk di atas."; exit 1; }
