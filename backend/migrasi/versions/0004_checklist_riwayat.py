"""Checklist: `checklist_item` jadi isi terbaru (1 baris per item), `checklist_versi` jadi versi LAMA item.

Sebelumnya setiap simpan menyalin SELURUH item ke versi baru. Konversi (lihat app/checklist.py untuk aturan baru):
- item dikenali dari `kode`; baris di versi terakhir yang memuat kode itu menjadi baris item (id-nya dipertahankan);
- versi lama ditelusuri berurutan; setiap perubahan mendapat nomor: item muncul = ditambah (`dibuat_nomor`),
  isi berbeda = isi SEBELUMNYA disimpan ke `checklist_versi`, item hilang = dihapus (`dihapus_nomor`);
- review mendapat `checklist_nomor` = nomor perubahan terakhir pada versi yang dipakainya → isi checklist sama persis;
- hasil/rekomendasi/override dipindah ke id item.

Revision ID: 0004_checklist_riwayat
Revises: 0003_checklist_status
Create Date: 2026-10-20
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_checklist_riwayat"
down_revision = "0003_checklist_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    c = op.get_bind()
    versi = c.execute(sa.text("SELECT id, dibuat_oleh, created_at FROM checklist_versi ORDER BY nomor")).all()
    baris = c.execute(sa.text("SELECT id, versi_id, urutan, kode, judul, kriteria, berlaku_untuk, aktif, diubah_oleh, diubah_at "
                              "FROM checklist_item ORDER BY urutan")).all()
    per_versi: dict = {}
    for b in baris:
        per_versi.setdefault(b.versi_id, []).append(b)
    item_id = {}  # kode → id baris di versi terakhir yang memuat kode itu
    for v in versi:
        for b in per_versi.get(v.id, []):
            item_id[b.kode] = b.id

    n, isi, terakhir, dibuat, dihapus, arsip, peta_versi = 0, {}, {}, {}, {}, [], {}
    for v in versi:
        sekarang = {b.kode: b for b in per_versi.get(v.id, [])}
        for kode, b in sekarang.items():
            baru = {"kode": kode, "urutan": b.urutan, "judul": b.judul, "kriteria": b.kriteria, "berlaku_untuk": b.berlaku_untuk,
                    "aktif": b.aktif, "diubah_oleh": b.diubah_oleh or v.dibuat_oleh, "diubah_at": b.diubah_at or v.created_at}
            konten = (b.judul, b.kriteria, b.berlaku_untuk, b.aktif)
            if kode not in isi:
                n += 1
                if kode in terakhir:
                    # shortcut: kode muncul lagi setelah hilang (hanya mungkin sebelum kode wajib unik) dianggap item yang
                    # sama; isi lamanya diarsipkan, tetapi masa "terhapus" di antaranya tidak tercatat.
                    arsip.append({"id": uuid.uuid4(), "nomor": n, "item_id": item_id[kode], **terakhir[kode]})
                dibuat.setdefault(kode, n)
                dihapus.pop(kode, None)
            elif isi[kode] != konten:
                n += 1
                arsip.append({"id": uuid.uuid4(), "nomor": n, "item_id": item_id[kode], **terakhir[kode]})
            else:
                continue  # salinan tanpa perubahan
            isi[kode], terakhir[kode] = konten, baru
        for kode in [k for k in isi if k not in sekarang]:
            n += 1
            dihapus[kode] = (n, v.created_at)
            del isi[kode]
        peta_versi[v.id] = n or None

    op.add_column("review", sa.Column("checklist_nomor", sa.Integer, nullable=True))
    for v_lama, nomor in peta_versi.items():
        c.execute(sa.text("UPDATE review SET checklist_nomor = :n WHERE checklist_versi_id = :v"), {"n": nomor, "v": v_lama})
    op.drop_constraint("review_checklist_versi_id_fkey", "review", type_="foreignkey")
    op.drop_column("review", "checklist_versi_id")

    for b in baris:
        if item_id[b.kode] != b.id:
            for tabel in ("hasil_item", "rekomendasi", "override"):
                c.execute(sa.text(f"UPDATE {tabel} SET checklist_item_id = :b WHERE checklist_item_id = :l"),
                          {"b": item_id[b.kode], "l": b.id})
    op.drop_constraint("checklist_item_versi_id_fkey", "checklist_item", type_="foreignkey")
    c.execute(sa.text("DELETE FROM checklist_item WHERE NOT (id = ANY(:ids))"), {"ids": list(item_id.values())})
    op.drop_index("ix_checklist_item_versi_id", "checklist_item")
    op.drop_column("checklist_item", "versi_id")
    op.add_column("checklist_item", sa.Column("dibuat_nomor", sa.Integer, nullable=True))
    op.add_column("checklist_item", sa.Column("dihapus_nomor", sa.Integer, nullable=True))
    op.add_column("checklist_item", sa.Column("dihapus_at", sa.DateTime(timezone=True), nullable=True))
    for kode, t in terakhir.items():
        hapus_nomor, hapus_at = dihapus.get(kode, (None, None))
        c.execute(sa.text("UPDATE checklist_item SET urutan = :urutan, judul = :judul, kriteria = :kriteria, berlaku_untuk = :b, "
                          "aktif = :aktif, diubah_oleh = :oleh, diubah_at = :at, dibuat_nomor = :dn, dihapus_nomor = :hn, "
                          "dihapus_at = :ha WHERE id = :id"),
                  {"urutan": t["urutan"], "judul": t["judul"], "kriteria": t["kriteria"], "b": t["berlaku_untuk"],
                   "aktif": t["aktif"], "oleh": t["diubah_oleh"], "at": t["diubah_at"], "dn": dibuat[kode],
                   "hn": hapus_nomor, "ha": hapus_at, "id": item_id[kode]})
    # Sama dengan aturan hapus di API: item terhapus yang tidak pernah termasuk checklist review mana pun dibuang permanen.
    nomor_review = [r[0] for r in c.execute(sa.text("SELECT checklist_nomor FROM review WHERE checklist_nomor IS NOT NULL"))]
    buang = [item_id[k] for k in dihapus if not any(n >= dibuat[k] for n in nomor_review)]
    if buang:
        arsip = [a for a in arsip if a["item_id"] not in set(buang)]
        c.execute(sa.text("DELETE FROM checklist_item WHERE id = ANY(:ids)"), {"ids": buang})
    op.alter_column("checklist_item", "dibuat_nomor", nullable=False)
    op.create_unique_constraint("checklist_item_kode_key", "checklist_item", ["kode"])
    op.drop_table("checklist_versi")

    tabel = op.create_table(
        "checklist_versi",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nomor", sa.Integer, unique=True),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("checklist_item.id"), nullable=False, index=True),
        sa.Column("kode", sa.String(50), nullable=False),
        sa.Column("urutan", sa.Integer, nullable=False),
        sa.Column("judul", sa.String(500), nullable=False),
        sa.Column("kriteria", sa.Text, nullable=False),
        sa.Column("berlaku_untuk", sa.String(10), nullable=False),
        sa.Column("aktif", sa.Boolean, nullable=False),
        sa.Column("diubah_oleh", UUID(as_uuid=True), sa.ForeignKey("pengguna.id"), nullable=True),
        sa.Column("diubah_at", sa.DateTime(timezone=True), nullable=True),
    )
    if arsip:
        op.bulk_insert(tabel, arsip)


def downgrade() -> None:
    raise NotImplementedError("Konversi checklist tidak dapat dibalik; pulihkan dari backup database.")
