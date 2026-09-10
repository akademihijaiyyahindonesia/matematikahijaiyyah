# Istilah: kepanjangan, fungsi, dan di mana ia tinggal

Singkatan di proyek ini menyebut **peran**, bukan hiasan. Halaman ini
mencatat kepanjangan tiap istilah, apa yang dikerjakannya, dan berkas mana
yang mengimplementasikannya — supaya sebuah nama bisa diperiksa, bukan
sekadar dihafal.

Sebelum halaman ini ada, sebagian kepanjangan hanya hidup di kepala
penulisnya. `HISAB` yang paling jelas: singkatannya dipakai di seluruh kode,
spesifikasinya ada, tapi kepanjangannya tidak tertulis di mana pun.

Kolom **Label** memakai konvensi [RULES.md](../cosmictera/RULES.md).

---

## Inti

| Istilah | Kepanjangan | Fungsi | Di mana | Label |
|---|---|---|---|---|
| **Hybit** | Hijaiyyah Hyperdimensional Bit Integration | Satuan informasi terstruktur: elemen V ⊂ ℕ₀¹⁸ yang memenuhi G1–G4 dan T1–T2. `(V, +)` monoid komutatif terbatas | `core/hybit.py` | CC |
| **H\*** | — (nama slot) | Komponen ke-17, satu-satunya yang tidak dibatasi guard mana pun | `core/constants.py`, `hcpu_pkg.vh` | DP |

## Bahasa dan perkakas

| Istilah | Kepanjangan | Fungsi | Di mana | Label |
|---|---|---|---|---|
| **HC** | Hybit Code | Bahasa tingkat tinggi dengan hybit sebagai tipe data primitif bawaan. Ekstensi `.hc` | `language/` | CC |
| **HCC** | HC Compiler | Kompilator 6-tahap dari HC ke HASM, termasuk **Ψ-Injector** yang menyuntikkan guard otomatis | `compiler/` | CC |
| **HASM** | Hybit Assembly | Bahasa rakitan untuk H-ISA. Ekstensi `.hasm` | `hisa/assembler.py` | CC |
| **HBC** | Hybit Bytecode | Format biner executable, kata instruksi 32-bit fixed-width. Ekstensi `.hbc` | `hisa/hbc_format.py` | CC |
| **HVM** | Hybit Virtual Machine | Lingkungan eksekusi perangkat lunak untuk bytecode Hybit | `vm/` | CC |

## Instruksi dan silikon

| Istilah | Kepanjangan | Fungsi | Di mana | Label |
|---|---|---|---|---|
| **H-ISA** | Hybit Instruction Set Architecture | Set instruksi kustom, operasi skalar dan codex secara natif. 72 opcode: 44 umum + 28 asli-huruf | `hisa/`, `hcpu_pkg.vh` | CC |
| **HCPU** | Hijaiyyah Core Processing Unit | Mikroprosesor kustom: ALU Codex natif, pipeline 5 tahap, operasi Hybit di level silikon | `rtl/hcpu_*.v` | CC — berjalan di papan |
| **HCHECK** | — (monitor runtime) | Pemantau integritas saat program berjalan | `hisa/hcheck.py` | CC |

## Pertukaran data dan registri

| Istilah | Kepanjangan | Fungsi | Di mana | Label |
|---|---|---|---|---|
| **HISAB** | Hijaiyyah Inter-System Standard for Auditable Bridging | Protokol nibble-packing + CRC32 untuk pertukaran codex antar-sistem secara terauditasi | `hisab/`, `hcpu_hisab.v` | CC |
| **HAR** | HISAB Alphabet Registry | Inventaris tersertifikat — `HAR-001` untuk 28 huruf Hijaiyyah. Registri yang menjamin integritas alfabet | `core/har.py`, `har/` | CC |
| **HGEO** | — (format geometri) | Keluaran Ψ-Compiler, masukan perakitan HAR. Ekstensi `.hgeo` | `core/hgeo.py` | CC |
| **CSGI** | Canonical Skeleton Graph Interface | Jalur dari bentuk huruf ke graf kanonik | `skeleton/csgi.py` | CC |

## Slot arsitektural — terbuka, menunggu uji fisik

Modul di bawah ini **sengaja belum terisi**. Dalam arsitektur yang masih
dijelajahi, slot terbuka adalah afordansi, bukan cacat: uji fisik yang
memutuskan mana yang ditambal, diperkuat, ditambah, atau dipangkas. Menyempit
sebelum data itu ada berarti memotong kemungkinan yang justru jadi dasar
kemajuannya.

| Istilah | Kepanjangan | Peran yang disediakan | Di mana |
|---|---|---|---|
| **HL18E** | Hijaiyyah Lang 18 vektor dimensi EBNF | Slot **modul mesin-bahasa** — bukan bahasanya, melainkan mesin yang menjalankannya | `hisa/compiler.py` |
| **HCServer** | — (penamaan belum disesuaikan) | **Modul penerima rentang keluaran**, yang nanti menangkap *wave ground switch* | `net/server.py` |

`HCServer` membawa satu masalah yang nyata dan terpisah dari perannya:
**namanya menyesatkan**. Ia berbunyi seperti server HTTP — dan `net/server.py`
memang menuliskannya begitu — padahal perannya penerima rentang, bukan
pelayan permintaan. Kelas cacat yang sama dengan `OP_MSB` dan Ψ: nama yang
memberi tahu pembaca peran yang keliru. Penyesuaiannya belum dikerjakan.

Catatan serupa untuk paket **`net/`** sendiri: isinya HC18DC, format data
kanonik Lapis 7, bukan jaringan. Hanya `server.py` di dalamnya yang benar-benar
menyangkut jalur penerimaan.

---

## Sistem

| Istilah | Kepanjangan | Fungsi | Di mana | Label |
|---|---|---|---|---|
| **HOM** | Hijaiyyah Operating Machine | Antarmuka global dan simulator interaktif pusat untuk seluruh ekosistem | `gui/`, `__main__.py` | CC |
| **HGSS** | Hybit Guard + Signature System | Lapis keamanan (L6) | `crypto/` | EH |
| **HFS** | Hybit File System | Sistem berkas *Guard-on-Write*: setiap operasi tulis divalidasi guard sebelum disimpan | — | **AT** |
| **HOS** | Hybit Operating System | Arsitektur sistem operasi 7 lapis berbasis *Guard-on-the-fly* | — | **AT** |

---

## Dua istilah yang pernah tertukar

**Ψ tidak pernah berarti komponen 17.** Ia berarti **Ψ-Compiler** dan
**Ψ-Injector** — tahap yang mengekstraksi geometri dan menyuntikkan guard.
Komponen ke-17 bernama **H\***, dan hanya itu. Keduanya sempat memakai
simbol yang sama di berkas yang berbeda, sehingga pembaca yang mengenal satu
konvensi salah membaca yang lain. `test_terminology.py` sekarang menjaga
pemisahan itu di kedua arah: tidak ada berkas penamaan slot yang boleh
menyebut Ψ, dan berkas Ψ-Compiler tidak boleh kehilangan Ψ-nya.

**`OP_` berarti opcode, dan hanya opcode.** `OP_MSB` dan `OP_LSB` dulu adalah
posisi bit bidang opcode yang duduk di ruang nama yang sama, sehingga tiap
alat yang menghitung `` `define OP_ `` menghitung keduanya — begitulah angka
74 masuk ke tabel yang jawabannya 72. Sekarang keduanya `OPCODE_MSB` dan
`OPCODE_LSB`, sejajar dengan `DST_MSB`, dan tesnya memeriksa **bentuk
nilainya**, bukan daftar pengecualian: opcode adalah satu byte, posisi bit
bukan.

---

## Yang menjaga halaman ini

- `test_terminology.py` — kepanjangan, pemisahan Ψ / H\*, konvensi `OP_`,
  dan jumlah opcode yang dicetak inventaris
- `test_hybit.py` — kata "hyperdimensional" menyebut sebuah angka, dan
  angka itu harus tetap 18
- `test_recipe_folders.py` — struktur folder dan sensus inventaris

Istilah berlabel **AT** sengaja tidak punya kolom "di mana": belum ada
berkas yang mengimplementasikannya, dan menuliskan lokasi untuk sesuatu yang
belum dibangun adalah persis kebiasaan yang label ini ada untuk mencegahnya.
