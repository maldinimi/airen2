"""Lingkungan Alembic. Buat revisi skema baru dengan:
`docker compose run --rm api python -m app.migrasi revisi "pesan perubahan"` (lihat docs/panduan-admin.md)."""
from alembic import context

from app import model  # noqa: F401
from app.db import Base, engine

with engine.connect() as koneksi:
    context.configure(connection=koneksi, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
