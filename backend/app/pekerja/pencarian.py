"""Chunking, embedding, dan pencarian hibrida (desain §4.1 langkah 5, §4.2).

Hibrida = dense (BGE-M3, pgvector cosine) + kata kunci (full-text search PostgreSQL 'indonesian'),
digabung dengan Reciprocal Rank Fusion, lalu diurutkan ulang oleh reranker (bge-reranker-v2-m3).
Mode tiruan memakai embedding hash & reranker leksikal yang deterministik (tanpa GPU/model).
"""
import hashlib
import math
import os
import re
import threading
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.konfigurasi import konfigurasi
from app.model import DIMENSI_EMBEDDING, Chunk, Elemen

MAKS_CHUNK = 1200
RE_KATA = re.compile(r"[0-9a-zA-ZÀ-ɏ]+")


class Penyemat:
    """Embedding + reranker. Model dimuat sekali per proses worker (thread-safe untuk inferensi)."""

    def __init__(self):
        self._kunci = threading.Lock()
        self._dense = self._rerank = None

    def _muat(self):
        if self._dense is None:
            with self._kunci:
                if self._dense is None:
                    from sentence_transformers import CrossEncoder, SentenceTransformer

                    k = konfigurasi()
                    folder = os.path.join(k.data_dir, "models")
                    # Path lokal hasil `make setup`; HF_HUB_OFFLINE=1 mencegah unduhan saat runtime (B1).
                    self._dense = SentenceTransformer(os.path.join(folder, k.embedding_model))
                    self._rerank = CrossEncoder(os.path.join(folder, k.reranker_model))

    def sematkan(self, teks: list[str]) -> list[list[float]]:
        if konfigurasi().tiruan:
            return [_hash_vektor(t) for t in teks]
        self._muat()
        return self._dense.encode(teks, normalize_embeddings=True, batch_size=16).tolist()

    def skor_ulang(self, kueri: str, teks: list[str]) -> list[float]:
        if not teks:
            return []
        if konfigurasi().tiruan:
            q = set(_kata(kueri))
            return [len(q & set(_kata(t))) / (1 + math.log(1 + len(t))) for t in teks]
        self._muat()
        return [float(s) for s in self._rerank.predict([(kueri, t) for t in teks], batch_size=16)]


penyemat = Penyemat()


def _kata(t: str) -> list[str]:
    return [w.lower() for w in RE_KATA.findall(t)]


def _hash_vektor(t: str) -> list[float]:
    """Embedding tiruan: bag-of-words di-hash ke 1024 dimensi, dinormalisasi. Deterministik."""
    v = [0.0] * DIMENSI_EMBEDDING
    for w in _kata(t):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIMENSI_EMBEDDING] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def buat_chunk(db: Session, file_id: uuid.UUID, elemen: list[Elemen]) -> None:
    """Gabungkan elemen berurutan dengan konteks lokasi yang sama (satu pasal/sub-bab/kelompok baris tabel)
    hingga ±1200 karakter, lalu embed. Chunk selalu menyimpan ID elemen asalnya."""
    kelompok: list[list[Elemen]] = []
    for e in elemen:
        if not e.teks.strip():
            continue
        konteks = _konteks(e)
        if kelompok and _konteks(kelompok[-1][-1]) == konteks and sum(len(x.teks) for x in kelompok[-1]) + len(e.teks) < MAKS_CHUNK:
            kelompok[-1].append(e)
        else:
            kelompok.append([e])
    teks = [f"[{g[0].label_lokasi}] " + "\n".join(e.teks for e in g) for g in kelompok]
    for i in range(0, len(teks), 64):
        vektor = penyemat.sematkan(teks[i:i + 64])
        for g, t, v in zip(kelompok[i:i + 64], teks[i:i + 64], vektor):
            db.add(Chunk(file_id=file_id, elemen_ids=[e.id for e in g], teks=t, embedding=v))


def _konteks(e: Elemen) -> str:
    """Kunci pengelompokan: bagian label sebelum unsur terakhir (mis. 'Bab II › poin 2.3', 'Pasal 5 ayat (2)', 'Tabel 3')."""
    if e.jenis == "sel_tabel":
        return e.label_lokasi.split(", baris")[0] + f"#{e.halaman}"
    return e.label_lokasi.rsplit(" › ", 1)[0]


def cari(db: Session, file_ids: list[uuid.UUID], kueri: str, k: int) -> list[Elemen]:
    """Pencarian hibrida pada file tertentu. Kembalikan elemen dari ≤k chunk terbaik,
    diurutkan stabil (file, halaman, urutan) agar konteks LLM konsisten (desain §4.6)."""
    if not file_ids or not kueri.strip():
        return []
    vektor = penyemat.sematkan([kueri])[0]
    dense = db.execute(select(Chunk.id).where(Chunk.file_id.in_(file_ids))
                       .order_by(Chunk.embedding.cosine_distance(vektor), Chunk.id).limit(40)).scalars().all()
    kata = sorted(set(w for w in _kata(kueri) if len(w) > 2))[:40]
    leksikal = []
    if kata:
        leksikal = db.execute(text(
            "SELECT id FROM chunk WHERE file_id = ANY(:f) AND tsv @@ to_tsquery('indonesian', :q) "
            "ORDER BY ts_rank_cd(tsv, to_tsquery('indonesian', :q)) DESC, id LIMIT 40"),
            {"f": list(file_ids), "q": " | ".join(kata)}).scalars().all()
    skor: dict[uuid.UUID, float] = {}
    for daftar in (dense, leksikal):
        for posisi, cid in enumerate(daftar):
            skor[cid] = skor.get(cid, 0.0) + 1.0 / (60 + posisi)  # Reciprocal Rank Fusion
    kandidat = sorted(skor, key=lambda c: (-skor[c], str(c)))[:max(3 * k, 20)]
    chunks = {c.id: c for c in db.scalars(select(Chunk).where(Chunk.id.in_(kandidat)))}
    urut = [chunks[c] for c in kandidat if c in chunks]
    nilai = penyemat.skor_ulang(kueri, [c.teks for c in urut])
    terbaik = [c for _, c in sorted(zip(nilai, urut), key=lambda x: (-x[0], str(x[1].id)))[:k]]
    ids = {eid for c in terbaik for eid in c.elemen_ids}
    return elemen_urut(db, ids)


def elemen_urut(db: Session, ids) -> list[Elemen]:
    if not ids:
        return []
    return list(db.scalars(select(Elemen).where(Elemen.id.in_(list(ids)))
                           .order_by(Elemen.file_id, Elemen.halaman, Elemen.urutan)))
