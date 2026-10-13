#!/bin/sh
# Backup = pg_dump database + arsip folder data/files (PDF). Hasil di ./backup/<waktu>/
set -e
WAKTU=$(date +%Y%m%d-%H%M%S)
TUJUAN="backup/$WAKTU"
mkdir -p "$TUJUAN"
U=$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-); D=$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)
docker compose exec -T db pg_dump -U "${U:-airen}" -d "${D:-airen}" -Fc > "$TUJUAN/database.dump"
tar -czf "$TUJUAN/files.tar.gz" -C data files
echo "Backup selesai: $TUJUAN (database.dump, files.tar.gz)"
