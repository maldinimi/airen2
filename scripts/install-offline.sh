#!/bin/sh
# Instal dari paket offline: make install-offline FILE=airen-bundle-<waktu>.tar  (tanpa internet)
set -e
ARSIP="$1"
[ -f "$ARSIP" ] || { echo "Pakai: make install-offline FILE=airen-bundle-<waktu>.tar"; exit 1; }
tar -xf "$ARSIP"
KERJA=$(tar -tf "$ARSIP" | head -1 | cut -d/ -f1)
docker load -i "$KERJA/images.tar"
tar -xf "$KERJA/kode.tar"
mkdir -p data
[ -f "$KERJA/models.tar" ] && tar -xf "$KERJA/models.tar" -C data
rm -rf "$KERJA"
echo "Instalasi offline selesai. Siapkan .env (cp .env.prod .env lalu sunting), kemudian: make up"
