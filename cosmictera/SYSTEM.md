# CosmicTera — sistem teknis

Dokumen ini menjelaskan **bagaimana** sistemnya bekerja. Untuk angka dan
jejaknya, lihat [`CONCRETE.md`](CONCRETE.md); untuk aturan yang mengikat, lihat
[`RULES.md`](RULES.md).

---

## 1. Geometri: kubus, bukan vektor

Keadaannya **25 lajur × 64 bit = 1600 bit**. Yang membedakan bukan ukurannya —
itu ukuran Keccak — melainkan **cara membacanya**:

```
cincin luar   16 lajur   1024 bit   ← rate; masukan hanya menyentuh ini
inti           9 lajur    576 bit   ← capacity; masukan tidak pernah menyentuhnya
              ──────────────────
              25 lajur   1600 bit
```

Kapasitas 576 bit memberi **keamanan 288 bit** terhadap tabrakan internal.

Yang penting: pemisahan rate/capacity di sini adalah **geometri**, bukan aturan
yang ditegakkan. Tidak ada pemeriksaan indeks yang bisa dilewati, tidak ada
kondisi yang bisa salah tulis. Masukan diserap ke cincin luar karena hanya
cincin luar yang punya kabel ke sana.

**Rotasi yang membawa data ke inti** — satu ronde untuk mencapai, tiga untuk
menjenuhkan. Itulah arti "rotasi menuju inti": bukan metafora, melainkan jalur
sebenarnya yang ditempuh sebuah bit.

## 2. Rotasi: apa yang membuat keluaran terdefinisi

Permutasinya menyusun π (permutasi lajur) dengan ρ (rotasi dalam lajur).

- **π terurai menjadi siklus `[12, 12, 1]`.** Lajur 0 tetap — dan **itulah
  sebabnya konstanta ronde ditaruh di sana**. Kalau tidak, lajur yang tidak
  bergerak akan menjadi jalur yang tidak pernah teraduk.
- **Orde ρ·π bersama adalah 768 = 12 × 64.** Dua belas untuk mengembalikan
  lajur ke tempatnya, enam puluh empat karena rotasi terakumulasi harus kembali
  nol modulo lebar lajur.
- **28 ronde adalah 27,4× di bawah periodenya.** Jumlah ronde di dekat 768 akan
  berjalan di dalam struktur yang berulang.

28 ronde itu sendiri **7 CIRCUIT × 4 TAWAF**.

## 3. Substitusi: satu S‑box, dua wujud

`GF(2⁸)` dengan polinomial `0x12B`, konstanta afin `0xE7`, generator 2.
Inversinya lewat menara `GF((2⁴)²)` dengan ν = `0xD`, β = `0x71` — teknik
Canright, dipakai apa adanya.

| Sifat | Nilai |
|---|---|
| Keseragaman diferensial | 4 |
| Non‑linearitas | 112 |
| Titik tetap | 0 |

Di silikon ia punya dua wujud yang **harus** memberi hasil identik pada 256
masukan:

```
sebagai tabel   274 LUT4
sebagai logika   76 LUT4      ← 3,6× lebih kecil
```

Versi logika bukan sekadar lebih kecil; ia yang tanpa celah timing tabel.

> **Jebakan yang pernah terjadi.** `gf4_inv` ditulis sebagai `case`, dan yosys
> menyimpulkan memori 16×4 di bawah komentar yang berbunyi "empat LUT4".
> Diganti dengan ANF.

## 4. Lipatan: bit → clock → tera

Ini mekanismenya, dan urutannya penting.

```
bit          aliran mentah, tanpa batas byte yang diketahui
  │          batas ditemukan lewat indeks koinsidensi (statistik gabungan,
  │          bukan marginal — statistik marginal tidak bisa melihat batas)
  ▼
byte         8 clock per byte   ← deserialiser; INI bottleneck‑nya
  │
  ▼
clock        gerbang jamrah + pencacah node, 1 clock per byte  (gratis)
  │
  ▼
lajur        16 lajur cincin luar dirakit
  │
  ▼
permutasi    310 clock @ SLICE=25   →  56 denyut impulser
  │
  ▼
tera         satuan tempat biayanya konstan
```

**Penemuan fase adalah perangkat lunak**, dijalankan sekali per aliran, bukan
per clock. Ia butuh histogram indeks koinsidensi 256 bin. `phase` adalah
*masukan* ke perangkat keras.

## 5. Impulser: irama yang ditentukan data

Impulser **tidak berjalan bebas terhadap waktu**. Ia:

- **berhenti** saat datapath sibuk (`stall`),
- **maju** saat spons butuh permutasi.

Karena itu tidak ada jumlah waktu berlalu yang memajukannya tanpa data. Ini
bukan pilihan gaya — ia konsekuensi dari backpressure, dan ia yang membuat
"per terabit" menjadi satuan yang benar.

```
56 denyut per permutasi   =   28 linear  +  28 substitusi
 1 permutasi per 128 byte
```

**Permutasi tidak bersembunyi di balik deserialiser.** Ia menegaskan
backpressure dan menghentikannya selama 310 clock penuh, jadi biayanya
**berjumlah**:

```
8,00  clock/byte   deserialiser
2,42  clock/byte   permutasi (310 per 128)
─────────────────
10,42 clock/byte   sistem      →  2,59 MB/s @ 27 MHz
```

Sebuah FIFO akan memulihkan sebagian besar ini — 310 clock muat di dalam 1.024
clock yang dibutuhkan 128 byte berikutnya untuk tiba, jadi permutasi bisa
bersembunyi penuh dan sistem berjalan di 8,00. **Belum dibangun, belum diukur —
[EH].**

## 6. Lapisan Ka'bah

**Ka'bah** = **K**riptografi **A**bsorpsi **B**yte **A**tas **H**ijaiyyah.

| Lapis | Nama | Jaminan | Label | Kunci |
|---|---|---|---|---|
| 0 | Canonical | satu bacaan per nilai; tanpa ambiguitas parsing | DP | — |
| 1 | Guard | menolak masukan malformed dalam O(1), tanpa kunci | CC | — |
| 2 | Absorption | spons tawaf, S‑box kelas AES, kapasitas 288 bit | EH | — |
| 3 | **Authentic** | **HMAC‑SHA256 atas kunci terikat segel** | **VF** | ya |
| 4 | Confidential | **ditolak** — pakai AES‑256‑GCM dari pustaka teruji | — | ya |

**Lapis 3 memikul seluruh keamanan.** Di RTL ia ada **sebagai slot sendiri**
(`rtl/hijaiyyah_hmac.v`, 1 Oktober 2026), tidak di jalur `hijaiyyah_kabah_top`
dan **tidak tersambung ke HCPU**. Yang keluar dari perangkat keras Ka'bah
**belum terautentikasi** sampai ditandatangani.

## 7. Segel: menutup setiap penentu

Manifes CosmicTera menyegel bukan hanya data, melainkan **segala yang
menentukan hasilnya**.

```
HMF1   manifes            12 pola sumber sistem
HEX1   pemeriksaan        fase default −1 = "tidak ada yang melihat"
```

Fase default **−1**, bukan 0, karena "tidak ada yang melihat" harus bisa
dibedakan dari "diperiksa pada fase 0".

Dua belas pola itu menutup: RTL, wrapper FPGA, testbench, vektor uji, header,
berkas papan (`.cst`, `.xdc`, `.tcl`, `Makefile`, `program.hex`), dan skrip
alat. Lima produk build dikecualikan karena bisa diturunkan ulang: `.vvp`,
`.fs`, `.bit`, `.bin`, `.o`.

`check_board_hex` **merakit ulang** hex dari `PROGRAM` di Makefile dan
membandingkannya — supaya hex yang ada di papan tidak bisa menyimpang dari
sumber yang menghasilkannya.

Program H‑ISA disegel oleh `seal_program`, dan opcode dibaca **dari
`hisa.opcodes`**, bukan dari daftar yang disalin — R1.

## 8. Yang tidak dilakukan sistem ini

- **Core SHA‑256 di RTL hanya slot sendiri.** Ia tidak tersambung ke HCPU
  maupun ke jalur Ka'bah, dan `CHASH`/`CSIGN` tetap pertanyaan untuk pemilik.
- **Tidak ada kerahasiaan.** Lapis 4 ditolak, disengaja.
- **HCPU tidak dilebur dengan blok kripto.** CosmicTera **membungkus** program
  yang berjalan di H‑ISA; ia tidak menyuntikkan kripto ke datapath.
- **Fmax HCPU [CC].** 86,18 MHz pasca-perutean di Tang Nano 20K, 75% LUT4
  (15.744 dari 20.736), diukur ulang 18 September 2026 dari build bersih dan
  cocok dengan header `rtl/fpga/gowin/hcpu_gowin_top.v`; angka lama 84,26 MHz
  dan 68% berasal dari desain sebelum SDIO, codex, dan pemisahan core/top.
  Papan menjalankannya — UART membalas byte-per-byte sama dengan
  simulasi. **Kabah top sendiri** (`hijaiyyah_kabah_top.v`) tetap tidak bisa
  jadi top level papan mana pun — 1.665 bit port melawan 384 IOB, dan itu
  memang tujuannya, persis seperti `hcpu_top` bukan top level. Wrapper-nya
  (`hijaiyyah_kabah_gowin_top.v`) menyempitkan itu ke 10 pin dan
  **dijalankan di papan**: 58% LUT4, 165,98 MHz, 400/400 byte cocok
  `cube.py` — lihat [`CONCRETE.md`](CONCRETE.md#wrapper-kabah--antarmuka-10-pin-dijalankan-di-papan).
