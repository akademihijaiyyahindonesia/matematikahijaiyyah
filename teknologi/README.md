# Teknologi: apa yang dihasilkan Matematika Hijaiyyah

Empat folder resep lain menjelaskan **bagaimana** sistem ini bekerja —
[cosmictera](../cosmictera/README.md) melipat dan menyegel,
[hijrah](../hijrah/README.md) menjadikan huruf satuan pencacah,
[cosmic-codex-jim](../cosmic-codex-jim/README.md) membedah satu huruf,
[matematika-hijaiyyah](../matematika-hijaiyyah/README.md) membaca tabel
sebagai program.

Folder ini menjawab pertanyaan lain: **apa yang sudah jadi barang.**

Namanya sendiri sudah menyebutkan isinya. **Hybit — Hijaiyyah
Hyperdimensional Bit Integration**: 28 huruf sebagai sumber, ℕ₀¹⁸ sebagai
ruangnya, bit sebagai satuan yang digeneralisasi, dan *integration* dalam dua
arti sekaligus — ketertutupan monoid `(V, +)`, dan cara ia masuk silikon
bit-serial, satu kawat dan satu bit keadaan per clock. Kepanjangan itu dicatat
di `src/hijaiyyah/core/hybit.py`, dan dijaga `test_hybit.py`: kata
"hyperdimensional" menyebut sebuah angka, dan angka itu harus tetap 18.

Isinya inventaris, bukan katalog klaim. Tiap baris menunjuk kode yang
mengimplementasikannya, dan tiap angka diperiksa oleh
`test_recipe_folders.py` terhadap apa yang menghasilkannya — aturan yang
sama yang berlaku di empat folder lain, karena prosa melenceng dan kode
tidak.

---

## Inventaris

| | Jumlah | Sandaran |
|---|---:|---|
| Huruf × dimensi | 28 × 18 | `src/hijaiyyah/core/master_table.py` |
| Nilai tersegel | 504 | ROM 252 byte, nibble-packed |
| Opcode H-ISA | 82 | `rtl/hcpu_pkg.vh` |
| — di antaranya asli-huruf | 9 | `HLOAD HCADD HGRD HNRM2 HDIST HPACK HCRC JGD JNGD` |
| Paket Python | 20 | `src/hijaiyyah/` |
| Modul RTL HCPU | 30 | `rtl/hcpu_*.v` |
| Modul RTL Ka'bah | 13 | `rtl/hijaiyyah_*.v` |
| Testbench RTL | 55 | `rtl/tb/` |
| Wrapper papan | 8 | `rtl/fpga/` |
| Program HASM | 59 | `rtl/programs/` |
| Format berkas | 5 | `.hc` `.hasm` `.hbc` `.hgeo` `.hcai` |
| Alat baris perintah | 4 | `hc` `hom` `hybit-ai` `kabah` |
| Spesifikasi | 18 | `docs/` |

Empat halaman berikut membagi inventaris itu menurut apa yang dikerjakannya.

---

## Halaman

**[ISTILAH.md](ISTILAH.md)** — glosarium. Kepanjangan tiap singkatan, apa yang
dikerjakannya, berkas mana yang mengimplementasikannya, dan labelnya. Termasuk
dua istilah yang pernah tertukar dan kini dijaga tes.

**[BAHASA.md](BAHASA.md)** — tumpukan bahasa dan runtime. Dari `.hc` yang
ditulis manusia sampai bytecode yang dieksekusi mesin virtual: lexer, parser,
evaluator, kompilator dengan Ψ-injector, assembler, dan HVM.

**[SILIKON.md](SILIKON.md)** — dari ISA sampai papan. H-ISA, HCPU lima
tahap, dan apa yang benar-benar terjadi ketika bitstream-nya dinyalakan di
Tang Nano 20K pada 10 September 2026 — termasuk tiga cacat yang hanya
perangkat keras bisa temukan.

**[KRIPTO.md](KRIPTO.md)** — Ka'bah. Spons, deserialiser bit-serial, gerbang
Jamrah, dan angka throughput yang jauh lebih rendah daripada yang pernah
diklaim — beserta sebabnya.

**[INDUSTRI.md](INDUSTRI.md)** — kegunaan di industri nyata. Halaman ini
paling ketat labelnya, karena paling mudah dipakai berbohong: sifat yang
**terukur** dipisahkan tegas dari penerapan yang **belum ada**.

---

## Yang menjangkar halaman-halaman ini

Angka di folder ini tidak ditranskripsi. Yang memeriksanya:

- `test_recipe_folders.py` — struktur folder dan angka inventaris di atas
- `test_place_and_route.py` — utilisasi dan Fmax kedua wrapper di papan
- `test_kabah_folder.py` — angka Ka'bah dan halaman siliconnya
- `test_letter_instructions.py` — sembilan instruksi asli-huruf
- `test_table_as_program.py` — tabel yang dieksekusi sebagai program
- `test_build_list.py` — hitungan tes yang dikutip seluruh dokumentasi

Kalau salah satu angka di sini berubah tanpa kodenya berubah, atau
sebaliknya, salah satu tes itu gagal.

---

## Label

Halaman-halaman ini memakai label epistemik proyek
([RULES.md](../cosmictera/RULES.md)): **VF** terbukti formal, **CC**
terkonfirmasi komputasional, **DP** benar karena konstruksi, **EH** terukur
tapi belum dikriptanalisis, **AT** belum dikerjakan.

Label melekat pada keadaan **sekarang**, bukan pada tujuan.
