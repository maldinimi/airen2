# Panduan Instalasi Offline & Node GPU

## 1. Gambaran

| Mesin | Menjalankan | File env |
| --- | --- | --- |
| Server aplikasi instansi (tanpa GPU) | `web`, `api`, `db`, `migrasi` | `.env.prod` |
| Node AI, GPU sewaan H100 NVL 94 GB (satu atau lebih) | `worker`, `llm` | `.env.node-ai` |
| Laptop developer | semua layanan (`.env.dev` dengan GPU, `.env.tiruan` tanpa GPU) | `.env.dev` / `.env.tiruan` |

Database, file PDF asli, audit log, dan aplikasi **tetap di server instansi** (B1). Node AI hanya memproses dan tidak menyimpan dokumen di disk (lihat §4).

## 2. Spesifikasi yang disarankan

| Komponen | Spesifikasi |
| --- | --- |
| Server aplikasi | 8 core, 16–32 GB RAM, SSD ≥500 GB (tumbuh sesuai jumlah PDF), Docker 24+ |
| Node AI | 1× H100 NVL 94 GB, 16–32 vCPU, ±128 GB RAM, NVMe ±500 GB (model ±70 GB), Docker + NVIDIA Container Toolkit, WireGuard |
| Laptop dev | RTX A6000 Laptop 16 GB, RAM ≥32 GB, disk kosong ≥100 GB |

Perkiraan kapasitas: 1 node ≈ 4–6 usulan/jam, sehingga 50 pengajuan selesai dalam ±9–12 jam. Dengan 3 node, waktunya ±3–4 jam. Lihat desain.md §2.3.

## 3. Instalasi server tanpa internet

**Di mesin yang memiliki internet** (sama arsitekturnya, x86_64):

```bash
cp .env.prod .env
```
```bash
make setup
```
```bash
make bundle
```

Untuk paket node AI, ulangi langkah di atas dengan `.env.node-ai`. Hasilnya `airen-bundle-<waktu>.tar` berisi image, model, dan kode.

**Di server tujuan** (salin arsip lewat disk):

```bash
make install-offline FILE=airen-bundle-<waktu>.tar
```
```bash
cp .env.prod .env
```

Sunting `.env`: `POSTGRES_PASSWORD`, `DATABASE_URL`, `ADMIN_PASSWORD_AWAL`, `COOKIE_SECURE=true` bila di belakang HTTPS, dan `DB_BIND_WIREGUARD`. Kemudian:

```bash
make up
```

Login sebagai `admin`, segera ganti password, buat Satker, pengguna, checklist, dan unggah panduan.

HTTPS: letakkan aplikasi di belakang reverse proxy/terminator TLS instansi yang meneruskan ke port `PORT_WEB` (default 8080), lalu set `COOKIE_SECURE=true`.

## 4. Node AI di GPU sewaan (cloud publik)

### 4.1 Terowongan WireGuard

Server aplikasi bertindak sebagai hub (mis. `10.66.0.1`); setiap node mendapat IP sendiri (`10.66.0.11`, …).

Server aplikasi `/etc/wireguard/wg0.conf`:

```ini
[Interface]
Address = 10.66.0.1/24
ListenPort = 51820
PrivateKey = <kunci privat server>

[Peer]  # gpu-h100-1
PublicKey = <kunci publik node>
AllowedIPs = 10.66.0.11/32
```

Node AI `/etc/wireguard/wg0.conf`:

```ini
[Interface]
Address = 10.66.0.11/24
PrivateKey = <kunci privat node>

[Peer]
PublicKey = <kunci publik server>
Endpoint = <IP publik/NAT server instansi>:51820
AllowedIPs = 10.66.0.1/32
PersistentKeepalive = 25
```

Aktifkan dengan `wg-quick up wg0`. Di `.env.prod` server, set `DB_BIND_WIREGUARD=10.66.0.1` agar PostgreSQL **hanya** terbuka pada antarmuka WireGuard.

### 4.2 Firewall node (blokir semua lalu lintas keluar selain terowongan)

Jalankan **setelah** `make setup-ai`, yaitu setelah model terunduh:

```bash
iptables -P OUTPUT DROP
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -o wg0 -j ACCEPT
iptables -A OUTPUT -p udp -d <IP server instansi> --dport 51820 -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -I DOCKER-USER -o eth0 -j DROP
```

Node tidak membuka port publik apa pun selain SSH administrasi, yang sebaiknya dibatasi ke IP instansi.

### 4.3 Menjalankan node

1. Admin aplikasi membuka **Kelola › Node AI › Daftarkan node GPU sewaan**, lalu menyalin token (hanya ditampilkan sekali).
2. Di node:

```bash
cp .env.node-ai .env
```

Isi `NODE_NAMA`, `NODE_TOKEN`, password di `DATABASE_URL`, serta `API_INTERNAL_URL=http://10.66.0.1:8080`. Kemudian:

```bash
make setup-ai
```
```bash
make up-ai
```

3. Node akan tampil "Terhubung" di menu Node AI dan Dashboard, lalu langsung mengambil job dari antrean.

Jaminan data di node:

- PDF diambil lewat `/api/internal/file/{sha}` ke `tmpfs` (`/tmp/kerja`, di RAM) dan dihapus setelah diproses.
- Hasil ditulis langsung ke database instansi.
- Model dibawa dari `make setup-ai` atau paket offline, sehingga node tidak mengunduh apa pun saat berjalan.

**Menambah kapasitas**: ulangi §4 untuk node berikutnya; tidak ada perubahan kode.
**Mematikan node**: `make down-ai` atau hapus VM. Job yang sedang berjalan otomatis kembali ke antrean dalam 5 menit dan dilanjutkan node lain. Untuk mencabut akses, gunakan menu Node AI › Cabut akses.

## 5. Verifikasi offline (B1)

- **Tanpa jaringan**: cabut kabel jaringan atau matikan internet, lalu jalankan `make up` dan coba alur lengkap.
- **`make cek-offline`**: memastikan jaringan `airen_internal` bertanda internal (tanpa gateway), serta `api` dan `worker` tidak dapat membuka koneksi ke internet (DNS publik, 1.1.1.1, huggingface.co).
- **`make test`**: `test_tidak_ada_koneksi_keluar_selama_review` mencatat semua `socket.connect` selama review dan memastikan hanya database yang dihubungi.
- **Frontend**: build gagal bila ada aset dari domain luar (`frontend/scripts/cek-offline.mjs`). nginx mengirim CSP `default-src 'self'; connect-src 'self'`, sehingga browser menolak permintaan ke domain lain.
- **Telemetri dimatikan**: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1`. Swagger UI (yang memakai CDN) dimatikan.
