# Pembungkus tipis docker compose. Skenario dipilih oleh isi .env (COMPOSE_FILE, AI_MODE, model).
# Tanpa make (mis. Windows): lihat padanan perintah docker compose di README.md.
.PHONY: setup up down restart logs status test doctor cek-offline backup restore bundle install-offline setup-ai up-ai down-ai

cek-env:
	@test -f .env || (echo "File .env belum ada. Jalankan: cp .env.tiruan .env  (atau .env.dev / .env.prod)"; exit 1)

## Persiapan sekali (butuh internet): build image + unduh model sesuai .env
setup: cek-env
	docker compose build
	docker compose --profile setup run --rm pengunduh

## Jalankan seluruh layanan (migrasi + seed otomatis)
up: cek-env
	docker compose up -d
	@echo "Aplikasi berjalan di http://localhost:$$(grep -E '^PORT_WEB=' .env | cut -d= -f2 || echo 8080)  (log: make logs)"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=100

status:
	docker compose ps

## Pengujian otomatis backend (database uji terpisah, AI tiruan)
test: cek-env
	docker compose run --rm api pytest -q

doctor:
	@sh scripts/doctor.sh

cek-offline:
	@sh scripts/cek-offline.sh

backup:
	@sh scripts/backup.sh

restore:
	@sh scripts/restore.sh $(FILE)

## Paket instalasi offline: image + model + konfigurasi dalam satu arsip
bundle: cek-env
	@sh scripts/bundle.sh

install-offline:
	@sh scripts/install-offline.sh $(FILE)

## Node AI di server GPU (gunakan .env.node-ai)
setup-ai: cek-env
	docker compose build worker
	docker compose --profile setup run --rm pengunduh

up-ai: cek-env
	docker compose up -d llm worker

down-ai:
	docker compose down
