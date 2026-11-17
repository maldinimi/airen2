"""Koneksi database (SQLAlchemy 2.0, PostgreSQL + pgvector)."""
from collections.abc import Iterator

from datetime import datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.konfigurasi import konfigurasi


class Base(DeclarativeBase):
    pass


engine = create_engine(konfigurasi().database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
SessionLokal = sessionmaker(bind=engine, expire_on_commit=False)


def sesi_db() -> Iterator[Session]:
    """Dependency FastAPI: satu sesi database per request, di-rollback bila error."""
    db = SessionLokal()
    try:
        yield db
    finally:
        db.close()


def jam_db(db: Session) -> datetime:
    """Waktu dari jam DATABASE (bukan jam server API): dibandingkan dengan review.mulai_at yang dicatat worker (mungkin
    di server GPU lain), dan dipakai untuk kolom jejak Diinput Oleh/Tanggal Input di semua menu master."""
    return db.scalar(select(func.now()))
