// Pemeriksaan build frontend: tidak ada aset/permintaan ke domain luar (B1).
// String URL di dalam pustaka (mis. tautan dokumentasi pada pesan error) bukan permintaan jaringan;
// yang diperiksa adalah pemuatan aset (src/href/url()/import) dan panggilan fetch/XHR ke URL absolut.
// Lapis kedua: header CSP nginx `default-src 'self'` memblokir semua permintaan lintas domain di browser.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const akar = process.argv[2] ?? "dist";
const POLA = [
  /<(script|link|img|iframe)[^>]+(src|href)=["']https?:\/\//i,
  /url\(\s*["']?https?:\/\//i,
  /@import\s+["']?(url\()?\s*["']?https?:\/\//i,
  /\bfetch\(\s*["'`]https?:\/\//i,
  /\bimport\(\s*["'`]https?:\/\//i,
  /\.open\(\s*["'`](GET|POST)["'`]\s*,\s*["'`]https?:\/\//i,
];
const temuan = [];
const telusuri = (d) => {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) telusuri(p);
    else if (/\.(html|js|mjs|css)$/.test(n)) {
      const isi = readFileSync(p, "utf8");
      for (const pola of POLA) { const m = isi.match(pola); if (m) temuan.push(`${p}: ${m[0]}`); }
    }
  }
};
telusuri(akar);
if (temuan.length) {
  console.error("Ditemukan pemuatan aset/permintaan ke domain luar:\n" + temuan.join("\n"));
  process.exit(1);
}
console.log("cek-offline: tidak ada aset atau permintaan ke domain luar.");
