import EditorVersi from "../../components/EditorVersi";
import type { ItemChecklist } from "../../types";
import { Lencana } from "../../ui";

const BERLAKU = { TOR: "TOR", RAB: "RAB", KEDUANYA: "TOR & RAB" };

export default function KelolaChecklist() {
  return (
    <EditorVersi<ItemChecklist>
      judul="Kelola Checklist" endpoint="/api/checklist"
      sub="Setiap penyimpanan menghasilkan versi baru. Review lama tetap menampilkan checklist yang dipakai saat itu."
      kosong={{ kode: "", judul: "", kriteria: "", berlaku_untuk: "TOR" }}
      kolom={[
        { nama: "kode", label: "Kode", jenis: "teks", petunjuk: "Unik, mis. C09. Dipakai untuk membandingkan item antar-revisi." },
        { nama: "judul", label: "Judul", jenis: "teks" },
        { nama: "kriteria", label: "Deskripsi / kriteria pemenuhan", jenis: "area", petunjuk: "Tuliskan sejelas mungkin; AI menilai berdasarkan kriteria ini." },
        { nama: "berlaku_untuk", label: "Berlaku untuk", jenis: "pilih", opsi: Object.entries(BERLAKU).map(([nilai, label]) => ({ nilai, label })) },
      ]}
      ringkas={(i) => (
        <div><div className="font-medium text-slate-900">{i.kode}. {i.judul} <Lencana className="ml-1 bg-slate-100 text-slate-600 ring-slate-200">{BERLAKU[i.berlaku_untuk]}</Lencana></div>
          <div className="text-slate-600">{i.kriteria}</div></div>
      )}
    />
  );
}
