"""Checklist: kolom & tabel sesuai permintaan pemilik produk.

- `checklist_item` (isi terbaru) & `checklist_histori` (semua versi, termasuk terbaru; pengganti `checklist_versi`)
  memakai kolom yang sama, berurutan:
  id, created_by, create_date, update_by, update_date, no_urut, kode, checklist, kriteria (TEXT),
  berlaku_untuk (TOR | RAB | TOR & RAB), aktif; checklist_histori juga punya `checklist_id` (FK ke item, CASCADE).
- Kolom dibuat_nomor, dihapus_nomor, dihapus_at dan `review.checklist_nomor` dihapus; isi checklist review disusun
  ulang dari kedua tabel pada `review.mulai_at` (app/checklist.py).
- Item yang sudah dihapus dibuang permanen (ikut hilang dari review lama — keputusan pemilik produk, desain.md §7).

Revision ID: 0005_checklist_histori
Revises: 0004_checklist_riwayat
Create Date: 2026-10-21
"""
import re
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0005_checklist_histori"
down_revision = "0004_checklist_riwayat"
branch_labels = None
depends_on = None

BERLAKU = {"KEDUANYA": "TOR & RAB"}


def _kolom_checklist(history: bool) -> list:
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True),
        sa.Column("create_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_by", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True),
        sa.Column("update_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *([sa.Column("checklist_id", UUID(as_uuid=True), sa.ForeignKey("checklist_item.id", ondelete="CASCADE"),
                     nullable=False, index=True)] if history else []),
        sa.Column("no_urut", sa.Integer, nullable=False),
        sa.Column("kode", sa.String(50), nullable=False, unique=not history),
        sa.Column("checklist", sa.String(500), nullable=False),
        sa.Column("kriteria", sa.Text, nullable=False),
        sa.Column("berlaku_untuk", sa.String(10), nullable=False),
        sa.Column("aktif", sa.Boolean, server_default=sa.true(), nullable=False),
    ]


def upgrade() -> None:
    c = op.get_bind()
    item = c.execute(sa.text("SELECT * FROM checklist_item")).mappings().all()
    versi = c.execute(sa.text("SELECT * FROM checklist_versi ORDER BY nomor")).mappings().all()
    sekarang = datetime.now(timezone.utc)

    op.drop_column("review", "checklist_nomor")  # isi checklist review kini disusun ulang dari waktu review.mulai_at

    # Hasil review menunjuk id item tanpa FK: item boleh dihapus permanen.
    for tabel in ("hasil_item", "rekomendasi", "override"):
        op.drop_constraint(f"{tabel}_checklist_item_id_fkey", tabel, type_="foreignkey")

    # Tabel checklist dibuat ulang dengan urutan kolom baru; item terhapus dibuang permanen.
    aktif = [i for i in item if i["dihapus_at"] is None]
    dibuat = {}  # id item → (oleh, waktu) versi pertamanya
    for v in versi:
        dibuat.setdefault(v["item_id"], (v["diubah_oleh"], v["diubah_at"]))
    baris_item, baris_history = [], []
    for i in aktif:
        oleh, waktu = dibuat.get(i["id"], (i["diubah_oleh"], i["diubah_at"]))
        jejak = {"created_by": oleh, "create_date": waktu or sekarang}
        baris_item.append({"id": i["id"], **jejak, "update_by": i["diubah_oleh"], "update_date": i["diubah_at"] or sekarang,
                           "no_urut": i["urutan"], "kode": i["kode"], "checklist": i["judul"], "kriteria": i["kriteria"],
                           "berlaku_untuk": BERLAKU.get(i["berlaku_untuk"], i["berlaku_untuk"]), "aktif": i["aktif"]})
        for v in versi:
            if v["item_id"] == i["id"]:
                baris_history.append({"id": v["id"], "checklist_id": i["id"], **jejak, "update_by": v["diubah_oleh"],
                                      "update_date": v["diubah_at"] or v["created_at"], "no_urut": v["urutan"],
                                      "kode": v["kode"],  # kode pada versi itu
                                      "checklist": v["judul"], "kriteria": v["kriteria"],
                                      "berlaku_untuk": BERLAKU.get(v["berlaku_untuk"], v["berlaku_untuk"]), "aktif": v["aktif"]})
    # no_urut item = urutan alami kode (A.2 < A.10), sama dengan app/checklist.py:urut_ulang.
    kunci = lambda k: [int(x) if n % 2 else x for n, x in enumerate(re.split(r"(\d+)", k))]  # noqa: E731
    for n, b in enumerate(sorted(baris_item, key=lambda b: kunci(b["kode"])), 1):
        b["no_urut"] = n
    # checklist_histori memuat SEMUA versi, termasuk isi terbaru tiap item (sama dengan app: setiap tambah/ubah dicatat).
    baris_history += [{**b, "id": uuid.uuid4(), "checklist_id": b["id"]} for b in baris_item]
    op.drop_table("checklist_versi")
    op.drop_table("checklist_item")
    op.bulk_insert(op.create_table("checklist_item", *_kolom_checklist(False)), baris_item)
    op.bulk_insert(op.create_table("checklist_histori", *_kolom_checklist(True)), baris_history)
    op.create_index("ix_checklist_item_no_urut", "checklist_item", ["no_urut"])
    op.execute("CLUSTER checklist_item USING ix_checklist_item_no_urut")  # urutan fisik = no_urut (lihat urut_ulang)
    op.create_index("ix_checklist_histori_update_date", "checklist_histori", [sa.text("update_date DESC")])
    op.execute("CLUSTER checklist_histori USING ix_checklist_histori_update_date")  # terbaru paling atas


def downgrade() -> None:
    raise NotImplementedError("Konversi checklist tidak dapat dibalik; pulihkan dari backup database.")
