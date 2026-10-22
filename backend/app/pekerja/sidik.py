"""Fingerprint hasil review (desain §4.6 lapis 2).

Inferensi GPU paralel tidak 100% deterministik, sehingga konsistensi hasil untuk masukan yang
sama persis TIDAK boleh bergantung pada temperatur 0 saja. Bila fingerprint revisi baru sama
dengan review sukses sebelumnya, hasil AI disalin — inilah yang MENJAMIN hasil identik (PRD §8).
Versi model & prompt ikut di-hash sehingga hasil model dev tidak dipakai ulang di production.
"""
import hashlib
import json


def fingerprint(sha_tor: str, sha_rab: str, checklist: str, kategori_versi_id, panduan_versi_ids, model_info: dict) -> str:
    data = {
        "tor": sha_tor, "rab": sha_rab, "checklist": checklist, "kategori": str(kategori_versi_id),
        "panduan": sorted(str(i) for i in panduan_versi_ids),
        "model": {k: model_info.get(k) for k in ("model", "prompt_versi", "embedding", "reranker", "ekstraktor")},
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
