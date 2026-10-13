#!/bin/sh
# Paket instalasi offline (make bundle): image kontainer + model + kode/konfigurasi → airen-bundle-<waktu>.tar
# Jalankan di mesin ber-internet SETELAH `make setup`, bawa arsipnya ke server tujuan, lalu `make install-offline FILE=…`.
set -e
WAKTU=$(date +%Y%m%d-%H%M%S)
KERJA="bundle-$WAKTU"
mkdir -p "$KERJA"
docker compose --profile setup config --images | sort -u > "$KERJA/images.txt"
echo "Menyimpan image: $(tr '\n' ' ' < "$KERJA/images.txt")"
docker save $(cat "$KERJA/images.txt") -o "$KERJA/images.tar"
git ls-files > /dev/null 2>&1 && git archive --format=tar HEAD -o "$KERJA/kode.tar" || tar --exclude=./data --exclude=./backup --exclude="./bundle-*" --exclude=./frontend/node_modules -cf "$KERJA/kode.tar" .
[ -d data/models ] && tar -cf "$KERJA/models.tar" -C data models || echo "(tidak ada folder model — mode tiruan)"
tar -cf "airen-bundle-$WAKTU.tar" "$KERJA" && rm -rf "$KERJA"
echo "Selesai: airen-bundle-$WAKTU.tar"
