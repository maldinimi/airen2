#!/bin/sh
# Restore dari folder backup: make restore FILE=backup/20261012-101500
# PERHATIAN: menimpa isi database & folder data/files saat ini.
set -e
SUMBER="$1"
[ -f "$SUMBER/database.dump" ] || { echo "Pakai: make restore FILE=backup/<waktu>"; exit 1; }
printf "Database dan file saat ini akan DITIMPA dari %s. Lanjut? (ketik YA) " "$SUMBER"; read -r JAWAB
[ "$JAWAB" = "YA" ] || { echo "Dibatalkan."; exit 1; }
U=$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-); D=$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)
docker compose stop api worker web || true
docker compose exec -T db pg_restore -U "${U:-airen}" -d "${D:-airen}" --clean --if-exists < "$SUMBER/database.dump"
tar -xzf "$SUMBER/files.tar.gz" -C data
docker compose up -d
echo "Restore selesai."
