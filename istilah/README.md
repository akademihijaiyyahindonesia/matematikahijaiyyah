# Istilah: kamus domain CosmicTera

Folder ini menjawab satu pertanyaan: **apa arti kata ini, dan di berkas mana ia
dikerjakan.** Bukan pengantar, bukan tutorial — kamus, dibaca saat sebuah nama
muncul dan artinya tidak jelas.

## Kenapa ia ada, padahal sudah ada glosarium

[`teknologi/ISTILAH.md`](../teknologi/ISTILAH.md) mencatat **akronim sistem** —
HC, HASM, HVM, HCPU, HISAB, HFS, HOS. Tiga puluh entri, dan semuanya singkatan
yang dipakai lintas-lapisan.

Yang tidak dicatatnya adalah **kosakata subsistem**: spons, lajur, impulser,
muka, tap, derajat, panel, nuqṭah, ekor, denyut. Kata-kata itu hidup di judul
bagian dan diagram alir folder resep, tidak pernah di tabel, dan seorang
pembaca yang menemukannya tidak punya tempat bertanya.

Sapuan yang membuatnya diperlukan: **kelima operasi BAB II — VTM, NMV, AGM,
ITM, EXM — dipakai di seluruh `src/hijaiyyah/algebra/` dan tak satu pun ada di
glosarium mana pun.** Itu bukan istilah pinggiran; itu seluruh isi bab kedua.

## Batas antara kedua tempat, dan kenapa ia ketat

**Satu istilah, satu tempat** (R1). Tidak ada entri di folder ini yang juga ada
di `teknologi/ISTILAH.md`, dan sebaliknya:

| | isinya | contoh |
|---|---|---|
| `teknologi/ISTILAH.md` | akronim sistem lintas-lapisan | HC · HASM · HVM · HCPU · HISAB |
| folder ini | kosakata di dalam satu subsistem | spons · muka · derajat · lajur |

`tests/test_integrity/test_istilah.py` menegakkan pemisahan itu secara
mekanis: sebuah istilah yang muncul di kedua tempat membuat suite merah.

## Isi folder

- [MATEMATIKA.md](MATEMATIKA.md) — BAB I dan BAB II: primitif, invarian, guard,
  dan kelima operasi metrik
- [SILIKON.md](SILIKON.md) — H-Reg, pipeline, guard di perangkat keras, dan
  nama-nama yang hanya ada di RTL
- [SISTEM.md](SISTEM.md) — HOS, HFS, kernel, rack, slot, dan peta memorinya
- [KABAH.md](KABAH.md) — lima lapis, pipeline spons, dan kosakata kriptografinya
- [CODEX-JIM.md](CODEX-JIM.md) — muka, tap, orde matriks, dan apa yang gagal
  terukur

## Aturan halaman ini

1. **Tiap entri menyebut berkas yang mengerjakannya.** Istilah tanpa
   implementasi tidak masuk kamus; ia masuk `cosmictera-build/OFF.md`.
2. **Kepanjangan diambil dari repo, tidak dikarang.** Yang kepanjangannya tidak
   tertulis di mana pun ditulis begitu, apa adanya — itu temuan, bukan ruang
   kosong untuk diisi tebakan.
3. **Angka tidak ditranskripsi.** Kamus menunjuk ke tempat angkanya diukur;
   ia tidak menyimpan salinannya.
