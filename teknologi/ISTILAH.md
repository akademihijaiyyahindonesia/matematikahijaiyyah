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
| **H-ISA** | Hybit Instruction Set Architecture | Set instruksi kustom, operasi skalar dan codex secara natif. 82 opcode: 54 umum + 28 asli-huruf | `hisa/`, `hcpu_pkg.vh` | CC |
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

`HCServer` **sudah terisi.** Ia memang penerima rentang, bukan pelayan
permintaan, dan sekarang perannya punya implementasi: `RangeReceiver` di
`receiver/rx.py` — fase terbungkus masuk, barisan rung keluar, dengan
keadaan kunci yang bisa hilang. Nama lamanya dipertahankan sebagai alias
(`HCServer is RangeReceiver`, satu kelas, bukan turunan) karena nama yang
sudah masuk glosarium tidak dihapus diam-diam; tetapi implementasinya
tunggal, jadi tidak ada versi kedua yang menyimpang di balik nama lama.

| Istilah | Kepanjangan | Fungsi | Di mana | Label |
|---|---|---|---|---|
| **RangeReceiver** | — (dulu `HCServer`) | Penerima rentang mode-kunci: gelombang → barisan rung; jangkar kalibrasi di puncak putaran | `receiver/rx.py` | CC |
| **PhaseLock** | — | Akumulator fase: membuka lipatan 0/360/720 yang detektor terbungkus rautkan jadi satu | `receiver/lock.py` | CC |

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

## Titik, garis, lengkung, lingkaran — nama tiga blok itu

Tiga blok vektor 18D bukan label abstrak. Ketiganya bernama Arab untuk
unsur pembentuk huruf, dan urutannya adalah urutan konstruksi:
**titik → garis → lengkung → lingkaran**.

| Blok | Nama | Artinya | Slot |
|---|---|---|---|
| **N** | *nuqṭah* | titik | Na, Nb, Nd |
| **K** | *khaṭṭ* | garis lurus | Kp, Kx, Ks, Ka, Kc |
| **Q** | *qaws* | lengkung | Qp, Qx, Qs, Qa, Qc |

`docs/csgi_algorithm_spec.md` §4.1 memutuskannya persis begitu: tiap edge
diukur simpangannya dari garis lurus, lalu ditandai `KHATT` atau `QAWS`.

**Lingkaran bukan blok keempat.** Ia adalah lengkung yang menutup, dan
masuk ke aljabar sebagai **koefisien**: Definisi 11.1.1 menulis
`U = Qx + Qs + Qa + 4·Qc`, dan angka 4 itu harga satu kurva tertutup dalam
perempat putaran. Dari sanalah kuantum 90° berasal — 360/4 — jadi grid
gelombang di `receiver/lock.py` memakai angka yang sama dengan yang diperiksa
guard, bukan angka yang dipilih sendiri. `test_the_quantum_comes_from_the_closed_curve_coefficient`
mengikat keduanya.

Dan G4 (`ρ = Θ̂ − U ≥ 0`) adalah rantai itu yang menutup jadi hukum
kekekalan: putaran total harus setidaknya menutupi putaran yang dituntut
lengkungnya.

---

## Satu kata, tiga arti — dan mengapa paketnya bukan `wave/`

Kata **wave** sudah dipakai dua kali di repo ini, untuk hal yang berbeda:

| Di mana | "Wave" berarti | "Periode" di sana berarti |
|---|---|---|
| `crypto/wave.py` | pipeline CMASS → penghitung node → laporan → segel Ka'bah | **periode pembingkaian byte** yang ditemukan dari aliran bit tak selaras |
| `cosmic-codex-jim/WAVE.md` | barisan bit yang dipancarkan mesin huruf | **panjang orbit** eksomatriks atas GF(2) |
| `receiver/` | — (sengaja tidak memakai kata itu) | — |

Paket penerima yang baru **tidak** diberi nama `wave/` justru karena itu.
Pemakaian ketiga akan membuat ketiganya lebih sulit dibaca sekaligus, dan
kelas cacatnya sama persis dengan Ψ/H\* dan `OP_MSB`: satu simbol yang
memberi tahu pembaca peran yang keliru. Namanya `receiver/` — peran yang
memang dikerjakannya, dan peran yang dulu dicadangkan untuk `HCServer`.

Fase juga dua arti: `crypto/wave.py` menyebut fase batas byte;
`receiver/lock.py` menyebut sudut putaran. Keduanya dicatat di docstring
masing-masing supaya tidak ada yang membacanya sebagai satu besaran.

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
