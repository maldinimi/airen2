import EditorVersi from "../../components/EditorVersi";
import type { ItemKategori } from "../../types";
import { LencanaKategori } from "../../ui";

export default function KelolaKategori() {
  return (
    <EditorVersi<ItemKategori>
      judul="Kelola Kategori" endpoint="/api/kategori"
      sub="AI selalu memakai definisi dari versi aktif saat review dimulai. Setiap penyimpanan menghasilkan versi baru."
      kosong={{ kode: "", nama: "", definisi: "", diteruskan: true }}
      kolom={[
        { nama: "kode", label: "Kode", jenis: "teks", petunjuk: "mis. K1" },
        { nama: "nama", label: "Nama", jenis: "teks" },
        { nama: "definisi", label: "Definisi", jenis: "area" },
        { nama: "diteruskan", label: "Diteruskan ke tahap berikutnya (hapus centang untuk kategori seperti K4)", jenis: "cek" },
      ]}
      ringkas={(i) => (
        <div><div className="flex items-center gap-2 font-medium text-slate-900"><LencanaKategori k={i} />{i.nama}</div>
          <div className="text-slate-600">{i.definisi}</div></div>
      )}
    />
  );
}
