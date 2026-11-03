<div align="center">

# **H-ISA Specification**
## Hijaiyyah Instruction Set Architecture — Version 1.2

### Formal Instruction Set for Hijaiyyah Codex Computation

**HM-28-v1.0-HC18D · 2026**

</div>

---

## Daftar Isi

- [1. Pendahuluan](#1-pendahuluan)
- [2. Desain dan Prinsip](#2-desain-dan-prinsip)
- [3. Model Mesin](#3-model-mesin)
- [4. Register File](#4-register-file)
- [5. Format Instruction Word](#5-format-instruction-word)
- [6. Opcode Map](#6-opcode-map)
- [7. Operasi Codex Inti](#7-operasi-codex-inti)
- [8. Operasi Aritmetika dan Logika](#8-operasi-aritmetika-dan-logika)
- [9. Operasi Kontrol Alur](#9-operasi-kontrol-alur)
- [10. Operasi Guard dan Audit](#10-operasi-guard-dan-audit)
- [11. Operasi Memori](#11-operasi-memori)
- [12. Operasi Kriptografi](#12-operasi-kriptografi)
- [13. Operasi Sistem](#13-operasi-sistem)
- [14. Status Flags](#14-status-flags)
- [15. Model Memori](#15-model-memori)
- [16. Model Eksekusi](#16-model-eksekusi)
- [17. Encoding Biner](#17-encoding-biner)
- [18. Assembly Language](#18-assembly-language)
- [19. Contoh Program Assembly](#19-contoh-program-assembly)
- [20. Jalur Kompilasi HC → H-ISA](#20-jalur-kompilasi-hc--h-isa)
- [21. Hubungan dengan HCVM](#21-hubungan-dengan-hcvm)
- [22. Hubungan dengan HCPU](#22-hubungan-dengan-hcpu)
- [23. Batasan dan Rencana](#23-batasan-dan-rencana)
- [24. Referensi](#24-referensi)

---

## 1. Pendahuluan

### 1.1 Apa itu H-ISA?

**H-ISA** (*Hijaiyyah Instruction Set Architecture*) adalah arsitektur
instruksi formal yang dirancang untuk memproses operasi codex Hijaiyyah
pada level mesin. H-ISA menyediakan:

- model register,
- format instruction word,
- set opcode,
- model eksekusi,
- dan spesifikasi encoding biner.

H-ISA menempati posisi **L2** dalam Hijaiyyah Technology Stack
dan menjadi jembatan antara:
- **HC Language** (bahasa tingkat tinggi) di atasnya,
- dan **HCVM / HCPU** (mesin eksekusi) di bawahnya.

### 1.2 Mengapa H-ISA Diperlukan?

Matematika Hijaiyyah beroperasi pada vektor integer 18-dimensi
dengan operasi khusus (guard check, codex distance, turning
decomposition, dll.) yang tidak dimiliki oleh ISA konvensional
seperti x86, ARM, atau RISC-V.

H-ISA menyediakan instruksi native untuk operasi-operasi ini,
sehingga:
- operasi codex menjadi efisien,
- pipeline dari HC ke mesin menjadi jelas,
- dan target hardware (HCPU) memiliki spesifikasi yang tegas.

### 1.3 Posisi dalam Stack

```
HC Source Code (.hc)
      │
      ▼
HC Compiler
      │
      ▼
H-ISA Bytecode          ← spesifikasi ini
      │
      ├──► HCVM (software execution)
      └──► HCPU (hardware execution, masa depan)
```

### 1.4 Status

H-ISA v1.2 berstatus **OPERATIONAL** pada level emulator/VM.
Hardware-native execution masih berstatus **DESIGNED**.

**v1.1 menambahkan `EMITS` (0xA2)** — bentuk stringnya ditetapkan di §13.1.1,
satu karakter per word dengan penutup nol — sehingga karakter dan string punya
jalur keluaran. Slotnya sudah dinamai sejak v1.0; yang baru adalah
representasinya dan implementasinya.

**v1.1 menambahkan `FRD` (0x0A) dan `FWR` (0x0B)** — FLAGS dibaca ke GPR dan
ditulis kembali darinya, sehingga sebuah context switch dapat menyimpannya.
Keduanya mengambil slot kosong di blok System & Control sesuai §6.0 aturan 2,
dan kenaikan versi ini adalah aturan 4. Tak ada nilai opcode lama yang
berubah.

**v1.2 melebarkan jendela peripheral, dan tidak menambah opcode apa pun.**
Keputusan pemilik, 14 September 2026: kartu TF onboard menjadi media
penyimpanan persisten HFS, dijangkau `LOAD`/`STORE` seperti peripheral lain.

```
sebelum : 0xFF0-0xFFF   16 word
sesudah : 0xFE0-0xFFF   32 word
```

Keenam belas alamat lama **tidak bergerak satu pun**; yang baru hanya band
`0xFE0`-`0xFEF`, berisi lima register kartu (§15.4). Karena jendela peripheral
adalah batas supervisor, kartu otomatis tak terjangkau mode user kecuali lewat
`SYSCALL` — dan itulah alasan memilih jendela, bukan opcode baru.

Kenaikan versi ini adalah §6.0 aturan 4: peta memori berubah, jadi versinya
naik, sekalipun tak ada satu pun encoding instruksi yang tersentuh.

---

## 2. Desain dan Prinsip

### 2.1 Prinsip Desain

| Prinsip | Penjelasan |
|---|---|
| **Fixed-width** | semua instruksi 32-bit |
| **Integer-only** | semua operasi pada $\mathbb{N}_0$ atau $\mathbb{Z}$ |
| **Codex-native** | instruksi khusus untuk vektor 18D |
| **Guard-aware** | instruksi verifikasi structural bawaan |
| **Deterministic** | hasil eksekusi selalu reprodusibel |
| **Simple decode** | field alignment tetap untuk decode cepat |

### 2.2 Perbandingan dengan ISA Konvensional

| Aspek | x86/ARM/RISC-V | H-ISA |
|---|---|---|
| Unit data utama | scalar integer/float | vektor integer 18D |
| Register utama | 16–32 GPR | 18 GPR + 4 Codex Reg |
| Operasi khusus | SIMD, FPU | CLOAD, VCHK, VDIST |
| Guard hardware | tidak ada | bawaan (VCHK) |
| Instruction width | 16/32/variable | 32-bit fixed |
| Domain target | komputasi umum | komputasi codex |

### 2.3 Filosofi

H-ISA tidak berusaha menggantikan ISA umum. H-ISA dirancang
sebagai **co-processor ISA** atau **domain-specific ISA** yang:
- dapat dijalankan oleh VM (HCVM),
- dapat diimplementasikan sebagai accelerator (HCPU),
- atau dapat menjadi target kompilasi dari HC.

---

## 3. Model Mesin

### 3.1 Diagram Abstrak

```
┌─────────────────────────────────────────────┐
│                 H-ISA Machine               │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ GPR      │  │ H-Reg    │  │ FLAGS    │  │
│  │ R0–R15   │  │ H0–H3   │  │ G Z O    │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│                                             │
│  ┌──────────┐  ┌──────────┐                │
│  │ PC       │  │ SP       │                │
│  └──────────┘  └──────────┘                │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ ROM: 252 bytes (Master Table)       │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ RAM: data + stack                    │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │ ALU: integer + vector operations     │   │
│  └──────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

### 3.2 Spesifikasi Mesin

| Parameter | Nilai |
|---|---|
| Word size | 32 bit |
| Instruction width | 32 bit (fixed) |
| GPR count | 16 (R0–R15) — the book's own §IIIJ.3.3.1 says 18 (R0–R17); its instruction word (§IIIF.3.3.1) gives each register field 4 bits, which cannot address past 15. See §4.1's note. |
| Codex register count | 4 (H0–H3) |
| GPR width | 32 bit |
| Codex register width | 18 × 32 bit = 576 bit |
| Program counter | 32 bit |
| Stack pointer | 32 bit |
| Status register | 8 bit |
| ROM | 252 bytes (Master Table) |
| RAM | configurable |
| Endianness | big-endian (network byte order) |

---

## 4. Register File

### 4.1 General Purpose Registers (GPR)

| Register | Nama | Fungsi |
|---|---|---|
| R0 | `r0` | general purpose / zero convention |
| R1 | `r1` | general purpose |
| R2 | `r2` | general purpose |
| R3 | `r3` | general purpose |
| R4 | `r4` | general purpose |
| R5 | `r5` | general purpose |
| R6 | `r6` | general purpose |
| R7 | `r7` | general purpose |
| R8 | `r8` | general purpose |
| R9 | `r9` | general purpose |
| R10 | `r10` | general purpose |
| R11 | `r11` | general purpose |
| R12 | `r12` | general purpose |
| R13 | `r13` | general purpose |
| R14 | `r14` | general purpose |
| R15 | `r15` | general purpose |

**Enam belas, bukan delapan belas.** §IIIJ.3.3.1 (hal. 133) memberi GPR bank
18 register, R0–R17, dan bahkan memberi R17 peran: register tautan, menurut
konvensi. Tapi §IIIF.3.3.1 (hal. 127), format word instruksi `.hbc`, memberi
DST/S1/S2 masing-masing **4 bit** — `[23:20] [19:16] [15:12]` — yang tidak
bisa menamai lebih dari 15. Buku berkontradiksi dengan dirinya sendiri di
sini; RTL dan assembler mengikuti klaim field 4-bit, karena itulah yang
benar-benar dienkode setiap opcode di repositori ini. R16/R17 dulu bisa
ditulis di teks `.hasm` dan dialiaskan diam-diam ke R0/R1 (assembler memangkas
dengan `& 0xF`, bukan memeriksa); assembler sekarang menolaknya, dengan
kutipan kedua bagian buku dalam pesan galatnya. Lihat komentar `MAX_GPR` di
`src/hijaiyyah/hisa/assembler.py`.

**Catatan sejarah:** alasan buku memilih 18 tercatat di §IIIJ.3.3.1 — "agar
setiap komponen codex 18D dapat dimuat ke register individual jika
diperlukan." Alasan itu sah; field 4-bit yang dipesan di §IIIF.3.3.1 tidak
pernah bisa mewujudkannya.

### 4.2 Codex Registers (H-Reg)

| Register | Nama | Lebar | Fungsi |
|---|---|---|---|
| H0 | `h0` | 18 × 32 bit | codex register 0 |
| H1 | `h1` | 18 × 32 bit | codex register 1 |
| H2 | `h2` | 18 × 32 bit | codex register 2 |
| H3 | `h3` | 18 × 32 bit | codex register 3 |

Setiap H-Reg menyimpan satu vektor codex 18D lengkap.
Akses ke komponen individual dilakukan melalui instruksi
`CGET` dan `CSET`.

### 4.3 Special Registers

| Register | Nama | Lebar | Fungsi |
|---|---|---|---|
| PC | `pc` | 32 bit | Program Counter |
| SP | `sp` | 32 bit | Stack Pointer |
| FLAGS | `flags` | 8 bit | Status flags |
| CY | `cy` | 32 bit | Cycle counter |

### 4.4 Konvensi Register

| Register | Konvensi |
|---|---|
| R0 | return value / accumulator |
| R1–R5 | argument passing |
| R6–R15 | caller-saved temporaries |

R16 (frame pointer) dan R17 (link register) ada di rencana buku, bukan di
mesin ini — lihat §4.1. `CALL`/`RET` (0x2E/0x2F) yang sekarang membawa peran
"tautan" itu memakai stack alamat-kembali khusus di perangkat keras, bukan
sebuah register bernama, persis karena R17 tidak bisa dialamatkan.
| H0 | primary codex operand |
| H1 | secondary codex operand |
| H2 | codex result |
| H3 | codex temporary |

---

## 5. Format Instruction Word

### 5.1 Layout

Semua instruksi H-ISA berukuran **32 bit** dengan layout
tetap berikut:

```
31        24 23    20 19    16 15    12 11              0
┌──────────┬────────┬────────┬────────┬─────────────────┐
│   OP     │  DST   │  S1    │  S2    │      IMM        │
│  8 bit   │ 4 bit  │ 4 bit  │ 4 bit  │    12 bit       │
└──────────┴────────┴────────┴────────┴─────────────────┘
```

### 5.2 Field Definitions

| Field | Bits | Range | Fungsi |
|---|---|---|---|
| **OP** | 31–24 | 0x00–0xFF | Opcode (256 kemungkinan) |
| **DST** | 23–20 | 0x0–0xF | Destination register |
| **S1** | 19–16 | 0x0–0xF | Source register 1 |
| **S2** | 15–12 | 0x0–0xF | Source register 2 |
| **IMM** | 11–0 | 0x000–0xFFF | Immediate value (12-bit unsigned) |

### 5.3 Encoding Modes

#### R-Type (Register-Register)

```
OP  DST  S1   S2   IMM(unused)
```

Contoh: `ADD R3, R1, R2`

#### I-Type (Register-Immediate)

```
OP  DST  S1   _(0)  IMM
```

Contoh: `ADDI R3, R1, #42`

#### C-Type (Codex Operation)

```
OP  DST(H-reg)  S1(H-reg)  S2(H-reg/GPR)  IMM
```

Contoh: `CADD H2, H0, H1`

#### J-Type (Jump)

```
OP  _(0)  _(0)  _(0)  IMM(target)
```

Contoh: `JMP #0x100`

#### B-Type (Branch)

```
OP  _(0)  S1   _(0)  IMM(offset)
```

Contoh: `BEQ R1, #offset`

### 5.4 Extraction dari Hex

Untuk instruction word `0x1234ABCD`:

```
Binary: 0001 0010 0011 0100 1010 1011 1100 1101
OP:     0x12  = 18
DST:    0x3   = 3
S1:     0x4   = 4
S2:     0xA   = 10
IMM:    0xBCD = 3021
```

---

## 6. Opcode Map

### 6.0 Status pembekuan dan sumber kebenaran

**H-ISA v1.0 — encoding dibekukan.**

Sumber kebenaran encoding adalah **`rtl/hcpu_pkg.vh`**, bukan dokumen ini.
Bila keduanya berbeda, RTL yang benar dan dokumen ini yang diperbaiki.

Alasannya bukan preferensi melainkan asimetri biaya: RTL terverifikasi oleh
205 assertion dan menuju silikon, tempat nomor yang keliru tidak bisa ditambal.
Perangkat lunak dapat dirilis ulang; cetakan tidak.

Aturan yang mengikat sejak v1.0:

1. **Opcode yang sudah ada di RTL tidak boleh berubah nilainya.** Perubahan
   semacam itu memutus setiap berkas `.hbc` yang sudah ada.
2. **Opcode baru untuk perangkat keras** mengambil slot kosong pada blok yang
   sesuai fungsinya, lalu ditambahkan ke `RTL_IMPLEMENTED`.
3. **Opcode khusus perangkat lunak** — dijalankan HVM dan mesin HISA, tidak
   oleh HCPU — wajib menempati nilai yang tidak dipakai RTL, sehingga
   memindahkannya ke perangkat keras kelak tidak memaksa penomoran ulang.
4. Setiap perubahan menaikkan versi ISA.

`tests/test_hisa/test_isa_parity.py` menegakkan aturan 1 dan 3 secara
mekanis: ia mem-parse `hcpu_pkg.vh` langsung, bukan salinan yang disalin
tangan. Selisih apa pun membuat suite merah.

**Latar belakang.** Sampai v1.0, ketiga tempat ini memuat tiga encoding yang
berbeda. Sisi perangkat lunak memberi `HLOAD` nilai 0x01, sementara RTL membaca
0x01 sebagai `HALT` — artinya instruksi pertama dari program hasil kompilasi
akan menghentikan prosesor. Dari tiga belas mnemonic yang didefinisikan kedua
sisi, hanya empat yang sepakat. Rekonsiliasi v1.0 menyelaraskan seluruhnya ke
RTL dan memasang gerbang di atas.

Kolom **HCPU** pada tabel di bawah menandai opcode yang benar-benar dapat
dieksekusi perangkat keras. Entri bertanda "perangkat lunak saja" berjalan di
HVM dan mesin HISA saja; memakainya dalam program yang ditujukan ke HCPU akan
memicu `HALT_ERR` (0xFF).

### 6.1 Opcode Ranges

| Range | Kategori | Jumlah |
|---|---|---|
| 0x00–0x0F | System & Control | 16 |
| 0x10–0x1F | Arithmetic & Logic | 16 |
| 0x20–0x2F | Comparison & Branch | 16 |
| 0x30–0x3F | Memory | 16 |
| 0x40–0x5F | Codex Operations | 32 |
| 0x60–0x6F | Guard & Audit | 16 |
| 0x70–0x7F | Crypto | 16 |
| 0x80–0x8F | Vector Math | 16 |
| 0x90–0x9F | String Operations | 16 |
| 0xA0–0xAF | I/O & Debug | 16 |
| 0xB0–0xFF | Reserved | 80 |

### 6.2 Complete Opcode Table

#### System & Control (0x00–0x0F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| Opcode | Mnemonic | Format | HCPU | Deskripsi |
|---|---|---|---|---|
| 0x00 | `NOP` | — | ✅ | No operation |
| 0x01 | `HALT` | — | ✅ | Stop execution |
| 0x08 | `ERET` | — | ✅ | Kembali dari trap: PC ← epc, kunci in-trap dilepas |
| 0x02 | `RESET` | — | — | Reset machine state |
| 0x03 | `MOV` | R | ✅ | `DST ← S1` |
| 0x04 | `MOVI` | I | ✅ | `DST ← IMM` |
| 0x06 | `HNRM2` | C | ✅ | `GPR[DST] ← ‖v₁₄(H[S1])‖²` |
| 0x07 | `HDIST` | C | ✅ | `GPR[DST] ← ‖H[S1] − H[S2]‖²₁₄` |
| 0x09 | `SYSCALL` | — | ✅ | Trap disengaja: minta layanan supervisor (cause 5). Operand `—`, bukan `I`: handler tak bisa membaca immediate — memori instruksi Harvard dan hanya-tulis dari sisi CPU, dan keenam belas slot periferal sudah terpakai. Nomor panggilan lewat register. |
| 0x0A | `FRD` | R | ✅ | `GPR[DST] ← FLAGS`, diperluas nol ke 32 bit |
| 0x0B | `FWR` | R | ✅ | `FLAGS ← GPR[S1][7:0]` |
| 0x05, 0x0C–0x0F | — | — | — | Reserved |

> **Perubahan v1.0.** `PUSH` dan `POP` sebelumnya tercantum di 0x05/0x06 dan
> `CALL`/`RET` di 0x07/0x08. HCPU menempati 0x06/0x07 untuk `HNRM2`/`HDIST`,
> dan RTL adalah rujukan yang mengikat, sehingga keempatnya dipindahkan —
> `PUSH`/`POP` ke blok Memory (0x32/0x33) dan `CALL`/`RET` ke ekor blok
> Comparison & Branch (0x2E/0x2F).

#### Arithmetic & Logic (0x10–0x1F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x10 | `ADD` | R | `DST ← S1 + S2` |
| 0x11 | `ADDI` | I | `DST ← S1 + IMM` |
| 0x12 | `SUB` | R | `DST ← S1 - S2` |
| 0x13 | `SUBI` | I | `DST ← S1 - IMM` |
| 0x14 | `MUL` | R | `DST ← S1 × S2` |
| 0x15 | `DIV` | R | `DST ← S1 / S2` |
| 0x16 | `MOD` | R | `DST ← S1 % S2` |
| 0x17 | `AND` | R | `DST ← S1 & S2` |
| 0x18 | `OR` | R | `DST ← S1 \| S2` |
| 0x19 | `XOR` | R | `DST ← S1 ^ S2` |
| 0x1A | `NOT` | R | `DST ← ~S1` |
| 0x1B | `SHL` | R | `DST ← S1 << S2` |
| 0x1C | `SHR` | R | `DST ← S1 >> S2` |
| 0x1D | `NEG` | R | `DST ← -S1` |
| 0x1E | `ABS` | R | `DST ← \|S1\|` |
| 0x1F | `SQR` | R | `DST ← S1 × S1` |

#### Comparison & Branch (0x20–0x2F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x20 | `CMP` | R | Compare S1, S2 → set FLAGS |
| 0x21 | `CMPI` | I | Compare S1, IMM → set FLAGS |
| 0x22 | `JMP` | J | Jump to IMM |
| 0x23 | `JEQ` | B | Jump if equal (Z=1) |
| 0x24 | `JNE` | B | Jump if not equal (Z=0) |
| 0x25 | `JLT` | B | Jump if less than |
| 0x26 | `JGT` | B | Jump if greater than |
| 0x27 | `JLE` | B | Jump if less or equal |
| 0x28 | `JGE` | B | Jump if greater or equal |
| 0x29 | `JGD` | B | Jump if GUARD flag set |
| 0x2A | `JNGD` | B | Jump if GUARD flag not set |
| 0x2B | `JGP` | B | Jump if guard pass — perangkat lunak saja |
| 0x2C | `JGF` | B | Jump if guard fail — perangkat lunak saja |
| 0x2D | `JNP` | B | Jump if not pass — perangkat lunak saja |
| 0x2E | `CALL` | J | Panggil subrutin di IMM: dorong PC+1 ke stack alamat-kembali, lalu PC ← IMM. Stack itu **bukan** stack `PUSH`/`POP` — lihat `RA_DEPTH` di `hcpu_pkg.vh` |
| 0x2F | `RET` | — | Kembali dari subrutin: PC ← pop stack alamat-kembali. Kedalaman 32; luber/kosong menghentikan mesin sebagai HC-04/HC-05 alih-alih melompat ke alamat karangan |

#### Memory (0x30–0x3F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x30 | `LOAD` | I | `DST ← MEM[S1 + IMM]` |
| 0x31 | `STORE` | I | `MEM[S1 + IMM] ← S2` |
| 0x32 | `PUSH` | R | Push GPR[S1] to stack |
| 0x33 | `POP` | R | Pop stack into GPR[DST] |
| 0x34–0x3F | — | — | Reserved |

> **Perubahan v1.0.** 0x32/0x33 sebelumnya dialokasikan untuk `LOADR` dan
> `LEA`; HCPU sudah menggunakannya untuk `PUSH`/`POP`. Keduanya kini tercatat
> di sini, sesuai lokasi yang memang lebih tepat secara semantik. `LOADR` dan
> `LEA` belum dialokasikan ulang.

#### Bitwise dan Geser (0xB0–0xBA)

> **Perluasan pasca-buku.** Bab III §IIIM.3.1 membekukan 28 opcode dan
> **tak satu pun menyentuh bit** — tidak ada AND, OR, XOR, NOT, geser, DIV,
> atau MOD. Celah itu sudah tercatat ketika `CGET` ditambahkan: *"there is no
> AND, no shift and no DIV in the table"* adalah buktinya sendiri bahwa tabel
> itu tidak lengkap untuk keperluan bukunya.
>
> Yang dihalanginya bukan kenyamanan. Alokator memori butuh bitmap free-list,
> penjadwal butuh mask ready, driver butuh field register, filesystem butuh
> bitmap blok — tak satu pun bisa ditulis dengan tambah, kurang, dan kali.
> Ruang `0xB0–0xBF` kosong di peta buku, jadi tidak ada yang tergeser.
>
> **Dua keputusan yang harus disebut**, karena membiarkannya tersirat adalah
> cara VM dan RTL menyimpang:
>
> 1. **Jumlah geseran di-mask ke 5 bit.** Geseran 32 atau lebih tidak punya
>    jawaban alami di mesin 32-bit, dan "tak terdefinisi" berarti interpreter
>    dan silikon bebas berbeda. RISC-V mem-mask; ini juga.
> 2. **Immediate logika di-zero-extend**, sementara `ADDI` di-sign-extend.
>    `ANDI r, r, 0x0FF` harus mem-mask delapan bit terendah; sign-extension
>    akan menjadikannya `0xFFFFF0FF`, yang tidak pernah berarti sebuah mask.

| Nilai | Opcode | Operasi |
|:---|:---|:---|
| 0xB0 | `AND`  | `GPR[DST] ← GPR[S1] & GPR[S2]` |
| 0xB1 | `OR`   | `GPR[DST] ← GPR[S1] \| GPR[S2]` |
| 0xB2 | `XOR`  | `GPR[DST] ← GPR[S1] ^ GPR[S2]` |
| 0xB3 | `NOT`  | `GPR[DST] ← ~GPR[S1]` |
| 0xB4 | `SHL`  | `GPR[DST] ← GPR[S1] << GPR[S2][4:0]` |
| 0xB5 | `SHR`  | `GPR[DST] ← GPR[S1] >> GPR[S2][4:0]` (logis) |
| 0xB6 | `ANDI` | `GPR[DST] ← GPR[S1] & zext(IMM)` |
| 0xB7 | `ORI`  | `GPR[DST] ← GPR[S1] \| zext(IMM)` |
| 0xB8 | `XORI` | `GPR[DST] ← GPR[S1] ^ zext(IMM)` |
| 0xB9 | `SHLI` | `GPR[DST] ← GPR[S1] << IMM[4:0]` |
| 0xBA | `SHRI` | `GPR[DST] ← GPR[S1] >> IMM[4:0]` (logis) |

#### Codex Operations (0x40–0x5F)

> **`CGET` (0x44) adalah perluasan pasca-buku.** Bab III §IIIM.3.1 membekukan
> 28 opcode dan tidak memuatnya, tetapi §IIIH.3.1.1 menyebut Hybit Engine
> mengimplementasikan HCADD, HPROJ, HDCMP, dan HEXMT — dan hanya HCADD yang
> punya encoding. Tanpa pembacaan komponen, tidak ada yang bisa mengambil Θ̂,
> N, K, atau Q dari H-Reg: tabel itu tidak punya AND, geser, maupun DIV, dan
> HPACK tidak bisa dibongkar. Akibatnya contoh program buku sendiri di
> §IIIF.3.1.2, yang memakai `PROJ THETA`, tidak dapat dirakit terhadap tabel
> instruksinya sendiri. `CGET` menutup ketidakkonsistenan itu.
>
> Nama dan slotnya tidak dikarang: spesifikasi ini sudah mencantumkan `CGET`
> di 0x44 dengan semantik persis itu dan tidak pernah mengimplementasikannya.
> Bukan `HPROJ` — 0x80 memakai nama itu untuk proyeksi *lapisan*, yang
> menghasilkan sub-vektor dan tidak muat di GPR 32-bit.

> **`CSET` (0x45) menutup separuh yang lain.** §IIIM.3.1 hanya bisa membangun
> codex dengan dua cara — memuat huruf tersegel (`HLOAD`) atau menjumlahkan
> dua H-Reg (`HCADD`) — dan tidak satu pun menulis angka hasil hitungan ke
> satu komponen. Akibatnya `hos_fs_read` hanya bisa mengembalikan berkas
> tersimpan sebagai 18 kata mentah, tidak pernah sebagai H-Reg hidup; itu
> celah HFS yang dicatat [OFF.md](../cosmictera-build/OFF.md).
>
> Nama dan slotnya juga bukan karangan: tabel di bawah sudah menuliskan `CSET`
> di 0x45 dengan semantik persis itu, jauh sebelum ada yang menjalankannya.
> Komponen H-Reg selebar 8 bit (`HREG_W` = 18 × 8), jadi yang masuk adalah
> byte terendah `GPR[S1]`; interpreter menutupnya dengan masker yang sama,
> karena lebar yang berbeda antara dua mesin adalah persis cara pembagian
> 0-basis/1-basis `HLOAD` dulu bersembunyi.

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x40 | `HLOAD` | C | Load codex dari ROM ke H-Reg: `H[DST] ← ROM[IMM]` |
| 0x40 | `CLOAD` | C | Alias dari `HLOAD` (ejaan spesifikasi lama) |
| 0x41 | `CSTORE` | C | Store H-Reg ke memori |
| 0x42 | `HCADD` | C | `H[DST] ← H[S1] + H[S2]` (vektor 18D) |
| 0x42 | `CADD` | C | Alias dari `HCADD` (ejaan spesifikasi lama) |
| 0x43 | `CSUB` | C | `H[DST] ← H[S1] - H[S2]` (delta 14D) |
| 0x44 | `CGET` | C | ✅ `GPR[DST] ← H[S1][IMM]` (ambil komponen, IMM 0–17; di luar itu 0) |
| 0x45 | `CSET` | C | ✅ `H[DST][IMM] ← GPR[S1]` (set komponen, IMM 0–17; di luar itu tidak menulis) |
| 0x46 | `CMOV` | C | ✅ `H[DST] ← H[S1]` (copy codex) |
| 0x47 | `CZERO` | C | ✅ `H[DST] ← 0` (zero codex) |
| 0x48 | `CEQ` | C | ✅ Compare H[S1] == H[S2] → FLAGS |
| 0x49 | `CDOT` | C | `GPR[DST] ← ⟨H[S1], H[S2]⟩₁₄` (inner product) |
| 0x4A | `CNORM` | C | `GPR[DST] ← ‖H[S1]‖²₁₄` (norm squared) |
| 0x4B | `CDIST` | C | `GPR[DST] ← ‖H[S1] - H[S2]‖²₁₄` (distance sq) |
| 0x4C | `CRHO` | C | ✅ `GPR[DST] ← ρ(H[S1])` (residu turning) |
| 0x4D | `CU` | C | ✅ `GPR[DST] ← U(H[S1])` (turning budget) |
| 0x4E | `CTHETA` | C | ✅ `GPR[DST] ← Θ̂(H[S1])` (extract theta) |
| 0x4F | `CMOD4` | C | ✅ `GPR[DST] ← Θ̂(H[S1]) mod 4` |
| 0x50 | `HPACK` | C | Nibble-pack H[S1] ke kata HISAB |
| 0x51 | `HCRC` | C | CRC32 atas frame terpaket |
| 0x52 | `HDOT` | C | ✅ `GPR[DST] ← ⟨H[S1], H[S2]⟩₁₄` (20-bit inner product) |
| 0x53 | `CPHI` | C | `GPR[DST] ← Φ(H[S1])` (Frobenius energy) |
| 0x54 | `CIDENT` | C | `GPR[DST] ← identify(H[S1])` (huruf index) |
| 0x55 | `HEXMT` | C | Bangun exomatrix 5×5 — perangkat lunak saja |
| 0x56 | `HDCMP` | C | Dekomposisi ke (U, ρ) — perangkat lunak saja |
| 0x57 | `HSER` | C | Serialize ke frame HISAB — perangkat lunak saja |
| 0x58 | `HDES` | C | Deserialize frame HISAB — perangkat lunak saja |
| 0x59 | `VSCL` | C | Perkalian skalar — perangkat lunak saja |
| 0x52, 0x5A–0x5F | — | — | Reserved |

> **Perubahan v1.0.** 0x50/0x51 sebelumnya dialokasikan untuk `CAN`/`CAK`;
> HCPU sudah menggunakannya untuk `HPACK`/`HCRC`. `CAN`, `CAK`, dan `CAQ`
> belum dialokasikan ulang — ketiganya dapat dibaca lewat `CGET` (0x44)
> dengan IMM 14, 15, dan 16.

#### Guard & Audit (0x60–0x6F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x60 | `HGRD` | C | Guard check H[S1] → set GUARD flag |
| 0x60 | `VCHK` | C | Alias dari `HGRD` (ejaan spesifikasi lama) |
| 0x61 | `VCHK1` | C | Check G1 only: ρ ≥ 0 |
| 0x62 | `VCHK2` | C | Check G2 only: A_N = ΣN |
| 0x63 | `VCHK3` | C | Check G3 only: A_K = ΣK |
| 0x64 | `VCHK4` | C | Check G4 only: A_Q = ΣQ |
| 0x65 | `VAUDIT` | C | Full R1–R5 audit → GPR[DST] |
| 0x66 | `VINJ` | C | Check if H[S1] is in valid codex set |
| 0x67 | `VTOPO` | C | Check topology guards (Ks→Qc, Kc→Qc) |
| 0x68–0x6F | — | — | Reserved |

#### Crypto (0x70–0x7F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x70 | `CHASH` | C | `GPR[DST] ← hash(H[S1])` (truncated) |
| 0x71 | `CSEAL` | C | `GPR[DST] ← seal(ROM)` (dataset hash) |
| 0x72 | `CSIGN` | C | Sign H[S1] with key IMM |
| 0x73 | `CVRFY` | C | Verify signature on H[S1] |
| 0x74–0x7F | — | — | Reserved |

#### Vector Math (0x80–0x8F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x80 | `VPROJ` | C | Project H[S1] to layer IMM → H[DST] |
| 0x81 | `VSUM` | C | `GPR[DST] ← Σ H[S1][0..17]` |
| 0x82 | `VMAX` | C | `GPR[DST] ← max(H[S1])` |
| 0x83 | `VMIN` | C | `GPR[DST] ← min(H[S1])` |
| 0x84 | `VCOSINE` | C | `GPR[DST] ← cosine(H[S1], H[S2])` (fixed-point) |
| 0x85 | `VMAN` | C | `GPR[DST] ← manhattan(H[S1], H[S2])` |
| 0x86 | `VHAM` | C | `GPR[DST] ← hamming(H[S1], H[S2])` |
| 0x87–0x8F | — | — | Reserved |

#### String Operations (0x90–0x9F)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0x90 | `SAGG` | C | Aggregate string → H[DST] |
| 0x91 | `SLEN` | I | `GPR[DST] ← string length` |
| 0x92 | `SCHR` | I | `GPR[DST] ← char at position IMM` |
| 0x93–0x9F | — | — | Reserved |

#### I/O & Debug (0xA0–0xAF)

| Opcode | Mnemonic | Format | Deskripsi |
|---|---|---|---|
| 0xA0 | `PRINT` | R | Print GPR[S1] |
| 0xA0 | `EMIT` | R | Alias dari `PRINT` (ejaan spesifikasi lama) |
| 0xA1 | `PRINTH` | C | Print codex H[S1] — perangkat lunak saja |
| 0xA1 | `EMITC` | C | Alias dari `PRINTH` |
| 0xA2 | `EMITS` | I | ✅ Cetak string di alamat IMM: satu karakter per word, `0x00000000` mengakhiri |
| 0xA3 | `DUMP` | — | Dump machine state — perangkat lunak saja |
| 0xA4 | `TRACE` | I | Enable/disable trace (IMM=0/1) — perangkat lunak saja |
| 0xA5 | `BREAK` | — | Breakpoint — perangkat lunak saja |
| 0xA6–0xAF | — | — | Reserved |

#### Error (0xFF)

| Opcode | Mnemonic | Format | HCPU | Deskripsi |
|---|---|---|---|---|
| 0xE0 | `L_ALIF` | — | ✅ | ا — `H0 ← H0 + v(Alif)` |
| 0xE1 | `L_BA` | — | ✅ | ب — `H0 ← H0 + v(Ba)` |
| 0xE2 | `L_TA` | — | ✅ | ت — `H0 ← H0 + v(Ta)` |
| 0xE3 | `L_TSA` | — | ✅ | ث — `H0 ← H0 + v(Tsa)` |
| 0xE4 | `L_JIM` | — | ✅ | ج — `H0 ← H0 + v(Jim)` |
| 0xE5 | `L_HA` | — | ✅ | ح — `H0 ← H0 + v(Ha)` |
| 0xE6 | `L_KHA` | — | ✅ | خ — `H0 ← H0 + v(Kha)` |
| 0xE7 | `L_DAL` | — | ✅ | د — `H0 ← H0 + v(Dal)` |
| 0xE8 | `L_DZAL` | — | ✅ | ذ — `H0 ← H0 + v(Dzal)` |
| 0xE9 | `L_RA` | — | ✅ | ر — `H0 ← H0 + v(Ra)` |
| 0xEA | `L_ZAY` | — | ✅ | ز — `H0 ← H0 + v(Zay)` |
| 0xEB | `L_SIN` | — | ✅ | س — `H0 ← H0 + v(Sin)` |
| 0xEC | `L_SYIN` | — | ✅ | ش — `H0 ← H0 + v(Syin)` |
| 0xED | `L_SHAD` | — | ✅ | ص — `H0 ← H0 + v(Shad)` |
| 0xEE | `L_DHAD` | — | ✅ | ض — `H0 ← H0 + v(Dhad)` |
| 0xEF | `L_THA` | — | ✅ | ط — `H0 ← H0 + v(Tha)` |
| 0xF0 | `L_ZHA` | — | ✅ | ظ — `H0 ← H0 + v(Zha)` |
| 0xF1 | `L_AIN` | — | ✅ | ع — `H0 ← H0 + v(Ain)` |
| 0xF2 | `L_GHAIN` | — | ✅ | غ — `H0 ← H0 + v(Ghain)` |
| 0xF3 | `L_FA` | — | ✅ | ف — `H0 ← H0 + v(Fa)` |
| 0xF4 | `L_QAF` | — | ✅ | ق — `H0 ← H0 + v(Qaf)` |
| 0xF5 | `L_KAF` | — | ✅ | ك — `H0 ← H0 + v(Kaf)` |
| 0xF6 | `L_LAM` | — | ✅ | ل — `H0 ← H0 + v(Lam)` |
| 0xF7 | `L_MIM` | — | ✅ | م — `H0 ← H0 + v(Mim)` |
| 0xF8 | `L_NUN` | — | ✅ | ن — `H0 ← H0 + v(Nun)` |
| 0xF9 | `L_WAW` | — | ✅ | و — `H0 ← H0 + v(Waw)` |
| 0xFA | `L_HAA` | — | ✅ | هـ — `H0 ← H0 + v(Haa)` |
| 0xFB | `L_YA` | — | ✅ | ي — `H0 ← H0 + v(Ya)` |
| 0xFF | `HALT_ERR` | — | ✅ | Berhenti karena opcode tak terimplementasi atau instruksi gagal |

HCPU menaikkan `HALT_ERR` ketika menemui opcode di luar `RTL_IMPLEMENTED` —
termasuk setiap entri "perangkat lunak saja" di atas.

---

## 7. Operasi Codex Inti

### 7.1 `CLOAD` — Load Codex dari ROM

```
CLOAD H0, #5      ; H0 ← codex huruf index 5 (Jim)
```

**Operasi:**
1. Baca index dari IMM (1–28).
2. Lookup Master Table ROM di offset yang sesuai.
3. Unpack 18 komponen integer dari ROM.
4. Simpan ke H-Reg tujuan.

**Kompleksitas:** O(1)

### 7.2 `CADD` — Codex Addition

```
CADD H2, H0, H1   ; H2 ← H0 + H1 (component-wise, 18D)
```

**Operasi:**

$$
H[\text{DST}][k] = H[\text{S1}][k] + H[\text{S2}][k], \quad k = 0, \ldots, 17
$$

**Catatan:** Ini adalah operasi fundamental untuk string integral:

$$
\mathrm{Cod}_{18}(w) = \sum_{i=1}^{n} v_{18}(x_i)
$$

**Kompleksitas:** O(18) = O(1) (18 parallel ADD)

### 7.3 `VCHK` — Guard Check

```
VCHK H0            ; check guard G1–G4 on H0 → set GUARD flag
```

**Operasi:**
1. Hitung $U = H[S1][10] + H[S1][11] + H[S1][12] + 4 \times H[S1][13]$.
2. Hitung $\rho = H[S1][0] - U$.
3. Periksa $\rho \geq 0$.
4. Periksa $H[S1][14] = H[S1][1] + H[S1][2] + H[S1][3]$.
5. Periksa $H[S1][15] = H[S1][4] + \ldots + H[S1][8]$.
6. Periksa $H[S1][16] = H[S1][9] + \ldots + H[S1][13]$.
7. Set GUARD flag = 1 jika semua lulus, 0 jika gagal.

**Kompleksitas:** O(1) (4 pemeriksaan, beberapa penjumlahan)

### 7.4 `CDIST` — Codex Distance Squared

```
CDIST R0, H0, H1   ; R0 ← Σ(H0[k] - H1[k])² untuk k=0..13
```

**Operasi:**

$$
\text{GPR}[\text{DST}] = \sum_{k=0}^{13} \big(H[\text{S1}][k] - H[\text{S2}][k]\big)^2
$$

**Catatan:** Hanya 14 komponen pertama (codex14) yang dipakai
untuk jarak Euclidean.

**Kompleksitas:** O(14) = O(1)

### 7.5 `CRHO` — Compute Residue

```
CRHO R0, H0        ; R0 ← Θ̂(H0) - U(H0)
```

**Operasi:**

$$
U = H[S1][10] + H[S1][11] + H[S1][12] + 4 \times H[S1][13]
$$

$$
\text{GPR}[\text{DST}] = H[S1][0] - U
$$

### 7.6 `CPHI` — Frobenius Energy

```
CPHI R0, H0        ; R0 ← Φ(H0)
```

**Operasi:** Bangun Exomatrix dari H[S1], lalu hitung
$\Phi = \sum_{r,c} E_{r,c}^2$.

**Kompleksitas:** O(25) = O(1)

---

## 8. Operasi Aritmetika dan Logika

### 8.1 Integer Arithmetic

```
ADD  R3, R1, R2    ; R3 ← R1 + R2
ADDI R3, R1, #10   ; R3 ← R1 + 10
SUB  R3, R1, R2    ; R3 ← R1 - R2
MUL  R3, R1, R2    ; R3 ← R1 × R2
DIV  R3, R1, R2    ; R3 ← R1 / R2
MOD  R3, R1, R2    ; R3 ← R1 % R2
```

### 8.2 Bitwise Operations

```
AND  R3, R1, R2    ; R3 ← R1 & R2
OR   R3, R1, R2    ; R3 ← R1 | R2
XOR  R3, R1, R2    ; R3 ← R1 ^ R2
NOT  R3, R1        ; R3 ← ~R1
SHL  R3, R1, R2    ; R3 ← R1 << R2
SHR  R3, R1, R2    ; R3 ← R1 >> R2
```

---

## 9. Operasi Kontrol Alur

### 9.1 Jump

```
JMP  #0x100        ; PC ← 0x100
```

### 9.2 Conditional Branch

```
CMP  R1, R2        ; set flags
JEQ  #offset       ; jump if R1 == R2
JNE  #offset       ; jump if R1 != R2
JLT  #offset       ; jump if R1 < R2
JGT  #offset       ; jump if R1 > R2
```

### 9.3 Guard-Conditional Branch

```
VCHK H0            ; check guard → set GUARD flag
JGD  #ok_label     ; jump if GUARD = 1 (valid)
JNGD #fail_label   ; jump if GUARD = 0 (invalid)
```

### 9.4 Subroutine

```
CALL #sub_addr     ; push PC+1, jump to sub_addr
RET                ; pop PC, return
```

---

## 10. Operasi Guard dan Audit

### 10.1 Guard Check Penuh

```
VCHK H0            ; G1–G4 check → GUARD flag
```

### 10.2 Guard Check Per Relasi

```
VCHK1 H0           ; G1 only: ρ ≥ 0
VCHK2 H0           ; G2 only: A_N check
VCHK3 H0           ; G3 only: A_K check
VCHK4 H0           ; G4 only: A_Q check
```

### 10.3 Full Audit

```
VAUDIT R0, H0      ; R1–R5 audit → R0 (bitmask)
```

R0 bitmask:
- bit 0: R1 (Θ̂ = U + ρ)
- bit 1: R2 (A_N = ΣN)
- bit 2: R3 (A_K = ΣK)
- bit 3: R4 (A_Q = ΣQ)
- bit 4: R5 (U = Qx+Qs+Qa+4Qc)

Jika R0 = 0x1F (semua bit set), audit lulus penuh.

### 10.4 Topology Guard

```
VTOPO R0, H0       ; topology guards → R0
```

R0:
- bit 0: Ks > 0 ⇒ Qc ≥ 1
- bit 1: Kc > 0 ⇒ Qc ≥ 1

---

## 11. Operasi Memori

### 11.1 Load dan Store

```
LOAD  R1, R2, #4   ; R1 ← MEM[R2 + 4]
STORE R2, R1, #4   ; MEM[R2 + 4] ← R1
```

### 11.2 ROM Access

```
LOADR R1, R2       ; R1 ← ROM[R2]
```

---

## 12. Operasi Kriptografi

### 12.1 Hash

```
CHASH R0, H0       ; R0 ← hash(H0) (32-bit truncated SHA-256)
```

### 12.2 Dataset Seal

```
CSEAL R0           ; R0 ← SHA-256(ROM) (32-bit truncated)
```

### 12.3 Sign dan Verify

```
CSIGN H0, #key_id  ; sign codex H0 with key_id
CVRFY H0, #key_id  ; verify signature → GUARD flag
```

---

## 13. Operasi Sistem

### 13.1 I/O

```
EMIT  R1           ; print integer R1
EMITC H0           ; print codex H0
EMITS #addr        ; print string at memory address
```

Tiga jalur keluaran, tiga domain, tidak saling meminjam:

| instruksi | mencetak |
|---|---|
| `PRINT` / `EMIT` (0xA0) | bilangan bulat, desimal, diakhiri newline |
| `PRINTH` / `EMITC` (0xA1) | codex/hybit — **perangkat lunak saja** |
| `EMITS` (0xA2) | karakter dan string |

#### 13.1.1 `EMITS` — bentuk string di RAM

**Ditetapkan pemilik, 13 September 2026.** Satu karakter ASCII per word 32-bit,
word `0x00000000` sebagai penutup:

```
alamat   isi          arti
  +0     0x00000048   'H'
  +1     0x00000069   'i'
  ...
  +9     0x00000000   penutup
```

```
EMITS IMM

addr = IMM
while MEM[addr] != 0:
    keluarkan MEM[addr] & 0xFF
    addr = addr + 1        ; word berikutnya
```

**Alamatnya alamat WORD.** RAM data mesin ini 4096 × 32 bit dan `LOAD`/`STORE`
mengalamatinya per word, jadi "word berikutnya" adalah `addr + 1` di sini —
bukan `+ 4`. Tata letaknya sama dengan penulisan alamat-byte `+4` yang lazim;
yang berbeda hanya satuan alamat mesin ini.

Dipilih **bukan karena paling hemat** melainkan karena paling mudah
diverifikasi: tidak ada ambiguitas urutan byte, tidak ada empat karakter
dikemas dalam satu word, penutupnya gampang diuji dan gampang disabotase, dan
ia cocok langsung dengan RAM 32-bit. Borosnya empat kali lipat diterima: yang
dibuktikan di tahap ini adalah jalur keluaran karakter, bukan kepadatan
penyimpanan.

`EMITS` **tidak** menambahkan newline. `PRINT` menambahkannya karena ia
mencetak satu bilangan; sebuah string membawa akhirannya sendiri kalau memang
mau. Itulah yang memungkinkan sebuah prompt.

### 13.2 Debug

```
DUMP               ; dump full machine state
TRACE #1           ; enable trace
TRACE #0           ; disable trace
BREAK              ; breakpoint (untuk debugger)
```

### 13.3 System Call

```
SYSCALL #code      ; invoke system call
```

System call codes **[PLANNED]**:

| Code | Fungsi |
|---|---|
| 0 | exit |
| 1 | print string |
| 2 | read input |
| 3 | file open |
| 4 | file read |
| 5 | file write |

---

## 14. Status Flags

### 14.1 Flag Register Layout

```
7  6  5  4  3  2  1  0
┌──┬──┬──┬──┬──┬──┬──┬──┐
│  │  │  │  │  │ O│ Z│ G│
└──┴──┴──┴──┴──┴──┴──┴──┘
```

| Bit | Nama | Deskripsi |
|---|---|---|
| 0 | **G** (GUARD) | 1 jika guard check terakhir lulus |
| 1 | **Z** (ZERO) | 1 jika hasil operasi terakhir = 0 |
| 2 | **O** (OVERFLOW) | didefinisikan, **tidak ditulis siapa pun** — lihat catatan |
| 3 | **LT** (LESS-THAN) | bit tanda dari `CMP`/`CMPI`, `S1 − S2 < 0` |
| 4–7 | — | Reserved |

> **Bit 3 dicatat di sini karena `FRD` memaparkannya.** `rtl/hcpu_pkg.vh`
> mendefinisikan `FLAG_LT` di bit 3 dan `rtl/hcpu_execute.v` menulisnya pada
> setiap `CMP`/`CMPI`; dokumen ini sebelumnya menyebut bit 3–7 "Reserved".
> §6.0 menetapkan RTL sebagai sumber kebenaran encoding dan dokumen yang
> dibetulkan, jadi yang dibetulkan tabel ini. Selama FLAGS tak terjangkau
> program, perbedaan itu tak pernah terlihat; `FRD` membuatnya terlihat pada
> instruksi pertama.
>
> **Bit 2 didefinisikan tetapi tidak ditulis siapa pun.** Tak ada satu pun
> instruksi di RTL maupun HVM yang menyentuhnya. Ia tetap di sini sebagai slot
> bernama, bukan sebagai perilaku.

### 14.2 Instruksi yang Mengubah Flags

| Flag | Diubah oleh |
|---|---|
| G | `VCHK`, `VCHK1–4`, `CVRFY` |
| Z | `CMP`, `CMPI`, `SUB`, `CEQ` |
| O | `ADD`, `MUL`, `ADDI` (jika overflow) |

### 14.3 Instruksi yang Membaca Flags

| Flag | Dibaca oleh |
|---|---|
| G | `JGD`, `JNGD`, `FRD` |
| Z | `JEQ`, `JNE`, `FRD` |
| LT | `FRD` |
| O | `FRD` (tak ada yang menulisnya) |

### 14.4 `FRD` dan `FWR` — FLAGS sebagai nilai

```
FRD  R3            ; R3 ← FLAGS, diperluas nol
FWR  R3            ; FLAGS ← R3[7:0]
```

Sampai v1.1 FLAGS hanya bisa dibaca oleh bentuk-J dan tidak bisa disimpan.
Konsekuensinya bukan teoretis: sebuah proses yang dipreempt di antara `CMP` dan
cabang yang membacanya kehilangan perbandingannya, karena handler harus
membandingkan `TRAP_CAUSE` dan perbandingannya menimpa milik proses. Diukur
pada satu loop berisi satu perbandingan, disapu 60 tenggat timer: **lima di
antaranya membalik cabangnya**.

Enam belas GPR, PC, dan jendela memori sudah bisa disimpan dan dipulihkan
sebuah context switch. `FRD`/`FWR` menjadikan FLAGS yang kelima:

```
SAVE   A          RESTORE B
  GPR[0..15]        GPR[0..15]
  PC                PC
  FRD → simpan      FWR ← pulihkan
```

`FWR` menulis kedelapan bit, termasuk yang tak bernama, supaya nilai yang
disimpan `FRD` kembali utuh. Sebuah context switch memulihkan apa yang
disimpannya, bukan tafsirannya.

---

## 15. Model Memori

### 15.1 Address Space

```
0x0000 ┌──────────────────┐
       │ ROM (252 bytes)  │  Master Table
0x00FC ├──────────────────┤
       │ Code segment     │  H-ISA bytecode
       ├──────────────────┤
       │ Data segment     │  Variables
       ├──────────────────┤
       │ Stack            │  Call stack (grows down)
       ├──────────────────┤
       │ Heap (optional)  │  Dynamic allocation
0xFFFF └──────────────────┘
```

### 15.2 ROM Layout

```
Offset  Size   Content
0x00    9      Codex huruf #1 (Alif): 9 nibble pairs
0x09    9      Codex huruf #2 (Ba)
...
0xF3    9      Codex huruf #28 (Ya)
Total: 252 bytes
```

### 15.3 Alignment

- GPR: 32-bit aligned
- H-Reg: 576-bit aligned (18 × 32)
- Memory access: 32-bit aligned
- Stack: 32-bit aligned

### 15.4 Jendela peripheral, dan blok kartu — v1.2

Ruang data 4.096 word. **32 word teratas adalah peripheral, sisanya RAM**, dan
satu komparator yang memutuskan — itulah alasan letaknya di puncak ruang dan
bukan tersebar. `addr[4]` memisahkan dua bloknya.

```
0xFE0-0xFEF   blok kartu SD        (v1.2, lima dari enam belas terpakai)
0xFF0-0xFFF   UART, timer, trap, jendela memori, port imem   (tak berubah)
```

| Alamat | Register | Akses | Fungsi |
|---|---|---|---|
| `0xFE0` | `SD_CMD` | W | 1 = INIT, 2 = READ, 3 = WRITE |
| `0xFE1` | `SD_STATUS` | R | bit0 BUSY · bit1 OK · bit2 ERROR · bit3 CARD_PRESENT · bit7:4 kode galat |
| `0xFE2` | `SD_SECTOR` | RW | nomor blok (LBA) |
| `0xFE3` | `SD_DATA` | RW | satu word buffer, indeks maju sendiri |
| `0xFE4` | `SD_CONTROL` | RW | bit0 reset indeks · bit1 reset controller · bit3:2 pembagi clock |

`0xFE5`–`0xFEF` kosong dan tetap kosong sampai ada yang membutuhkannya.

**`SD_DATA` memajukan indeksnya sendiri**, bargain yang sama dengan
`REG_IMEM_DATA`: satu store per word, bukan dua, jadi 512 byte berharga 128
store. Buffernya 128 word di dalam controller, bukan di RAM data — RAM data
satu port, dan `EMITS` sudah memperlihatkan harganya.

**`CARD_PRESENT` menyatakan kartu PERNAH MENJAWAB inisialisasi**, bukan bahwa
ada kartu di slot. Pinout papan ini tidak membawa jalur card-detect, jadi tidak
ada yang bisa diindera; bit itu dinamai apa adanya daripada menjanjikan sesuatu
yang papannya tidak tahu.

**Mesin HISA perangkat lunak tidak punya kartu.** Blok ini terbaca nol di sana
dan tulisan ke sana tidak ke mana-mana — sebuah program yang menanyakan status
akan melihat "selesai, tidak ok" dan mengambil jalur galatnya, yang memang
benar untuk mesin bersslot kosong. Jalur kartu hanya ada di perangkat keras;
tercatat di [cosmictera-build/OFF.md](../cosmictera-build/OFF.md).

---

## 16. Model Eksekusi

### 16.1 Cycle

Setiap instruksi memerlukan minimal 1 cycle. Instruksi codex
yang melibatkan 18 komponen secara konseptual memerlukan
18 sub-operasi, tetapi pada hardware paralel ini dapat
dilakukan dalam 1 cycle.

### 16.2 Pipeline (Konseptual)

```
Fetch → Decode → Execute → Writeback
```

Untuk HCVM (software), pipeline disimulasikan secara sekuensial.
Untuk HCPU (hardware), pipeline dapat diimplementasikan
secara pipelined atau superscalar.

### 16.3 Execution Loop (HCVM)

```python
while not halted:
    instruction = fetch(PC)
    op, dst, s1, s2, imm = decode(instruction)
    execute(op, dst, s1, s2, imm)
    PC += 1
    cycle += 1
```

### 16.4 Interrupt Model **[PLANNED]**

H-ISA v1.0 tidak memiliki model interrupt. Eksekusi bersifat
run-to-completion atau halt.

---

## 17. Encoding Biner

### 17.1 Hex Representation

Setiap instruksi direpresentasikan sebagai 8 digit hex:

```
0x40000005   →   CLOAD H0, #5
0x42010000   →   CADD  H2, H0, H1
0x60000000   →   VCHK  H0
```

### 17.2 Binary File Format **[PLANNED]**

```
Header:
  4 bytes: magic number "HISA"
  4 bytes: version (0x00010000 = v1.0)
  4 bytes: code size (in words)
  4 bytes: data size (in bytes)

Code segment:
  N × 4 bytes: instruction words

Data segment:
  M bytes: initialized data
```

---

## 18. Assembly Language

### 18.1 Syntax

```asm
; comment
label:
    MNEMONIC  operand1, operand2, operand3
```

### 18.2 Operand Types

| Tipe | Syntax | Contoh |
|---|---|---|
| GPR | `R0`–`R15` | `R3` |
| H-Reg | `H0`–`H3` | `H0` |
| Immediate | `#value` | `#42`, `#0xFF` |
| Label | `name` | `loop:` |

### 18.3 Directives **[PLANNED]**

```asm
.org 0x100       ; set origin
.data            ; switch to data segment
.word 42         ; emit 32-bit word
.string "hello"  ; emit string
```

---

## 19. Contoh Program Assembly

### 19.1 Load dan Print Codex

```asm
; Load huruf Ba dan print codex-nya
start:
    CLOAD  H0, #2        ; H0 ← codex Ba
    EMITC  H0            ; print codex
    HALT
```

### 19.2 Guard Check

```asm
; Load huruf Jim, check guard, branch accordingly
start:
    CLOAD  H0, #5        ; H0 ← codex Jim
    VCHK   H0            ; check guard → GUARD flag
    JGD    #valid         ; jump if valid
    MOVI   R0, #0         ; R0 ← 0 (invalid)
    EMIT   R0
    HALT

valid:
    MOVI   R0, #1         ; R0 ← 1 (valid)
    EMIT   R0
    HALT
```

### 19.3 String Integral (Manual)

```asm
; Compute codex("بسم") = codex(Ba) + codex(Sin) + codex(Mim)
start:
    CZERO  H2            ; H2 ← zero
    CLOAD  H0, #2        ; H0 ← Ba
    CADD   H2, H2, H0    ; H2 += Ba
    CLOAD  H0, #12       ; H0 ← Sin
    CADD   H2, H2, H0    ; H2 += Sin
    CLOAD  H0, #24       ; H0 ← Mim
    CADD   H2, H2, H0    ; H2 += Mim
    EMITC  H2            ; print result
    VCHK   H2            ; guard check
    JGD    #ok
    MOVI   R0, #0
    EMIT   R0
    HALT
ok:
    MOVI   R0, #1
    EMIT   R0
    CRHO   R1, H2        ; R1 ← rho
    EMIT   R1
    HALT
```

### 19.4 Distance Computation

```asm
; Compute distance² antara Alif dan Haa
start:
    CLOAD  H0, #1        ; H0 ← Alif
    CLOAD  H1, #27       ; H1 ← Haa
    CDIST  R0, H0, H1    ; R0 ← ‖H0 - H1‖²₁₄
    EMIT   R0            ; print 70
    HALT
```

### 19.5 Full Audit

```asm
; Audit semua 28 huruf
start:
    MOVI   R1, #1         ; counter = 1
loop:
    CMPI   R1, #29
    JEQ    #done
    CLOAD  H0, R1         ; H0 ← codex[R1]
    VCHK   H0
    JNGD   #fail
    ADDI   R1, R1, #1
    JMP    #loop
fail:
    EMIT   R1             ; print failing index
    HALT
done:
    MOVI   R0, #28
    EMIT   R0             ; print 28 (all passed)
    HALT
```

---

## 20. Jalur Kompilasi HC → H-ISA

### 20.1 Pipeline

```
HC Source (.hc)
     │
     ▼
HC Lexer → Token Stream
     │
     ▼
HC Parser → AST
     │
     ▼
HC Compiler → H-ISA Assembly
     │
     ▼
H-ISA Assembler → Bytecode
     │
     ▼
HCVM / HCPU
```

### 20.2 Contoh Kompilasi

#### HC Source

```hc
let h = load('ب');
println(h.theta());
```

#### H-ISA Assembly Output

```asm
    CLOAD  H0, #2        ; load('ب')
    CTHETA R0, H0        ; h.theta()
    EMIT   R0            ; println(...)
    HALT
```

### 20.3 Status Compiler

HC → H-ISA compiler berstatus **awal**:
- subset operasi dasar sudah dapat dikompilasi,
- kontrol alur kompleks belum sepenuhnya didukung,
- optimasi belum diimplementasikan.

---

## 21. Hubungan dengan HCVM

HCVM (Hijaiyyah Codex Virtual Machine) adalah **implementasi
software** dari H-ISA.

| Aspek | H-ISA | HCVM |
|---|---|---|
| Tipe | Spesifikasi | Implementasi |
| Level | Arsitektur instruksi | Runtime software |
| Fungsi | Mendefinisikan instruksi | Mengeksekusi instruksi |
| Status | OPERATIONAL (spec) | OPERATIONAL (runtime) |

HCVM mengimplementasikan:
- fetch/decode/execute loop,
- register file (GPR + H-Reg),
- flag management,
- memory model,
- dan I/O primitives.

---

## 22. Hubungan dengan HCPU

HCPU (Hijaiyyah Core Processing Unit) adalah **target hardware**
dari H-ISA.

| Aspek | H-ISA | HCPU |
|---|---|---|
| Tipe | Spesifikasi | Hardware target |
| Level | Arsitektur instruksi | Prosesor fisik |
| Fungsi | Mendefinisikan ISA | Mengeksekusi ISA secara native |
| Status | OPERATIONAL (spec) | DESIGNED |

### 22.1 Jalur Realisasi

```
H-ISA Spec
     │
     ├──► HCVM (software, sekarang)
     │
     └──► HCPU
           ├── Fase 1: Softcore FPGA
           └── Fase 2: ASIC (jangka panjang)
```

### 22.2 Fitur HCPU Target

| Fitur | Deskripsi |
|---|---|
| 18-wide ALU | 18 integer operations per cycle |
| Onboard ROM | 252 bytes Master Table |
| Guard unit | Hardware guard checker |
| Codex register file | 4 × 576-bit H-Reg |
| Fixed 32-bit decode | Simple instruction decoder |

---

## 23. Batasan dan Rencana

### 23.1 Batasan v1.0

| Batasan | Penjelasan |
|---|---|
| Tidak ada interrupt | run-to-completion saja |
| Tidak ada MMU | flat address space |
| Tidak ada floating-point | integer only |
| Tidak ada virtual memory | direct mapping |
| Immediate hanya 12-bit | max value 4095 |
| Belum ada debug protocol | DUMP/TRACE saja |
| Compiler HC belum lengkap | subset operasi |

### 23.2 Rencana v1.1 **[PLANNED]**

```
□ Extended immediate (24-bit mode)
□ Interrupt model
□ Debug protocol
□ Memory-mapped I/O
□ Profiling counters
```

### 23.3 Rencana v2.0 **[PLANNED]**

```
□ SIMD-style codex operations (batch processing)
□ Multi-core codex pipeline
□ Virtual memory
□ Hardware guard acceleration
□ DMA for codex streaming
```

---

## 24. Referensi

| Referensi | Deskripsi |
|---|---|
| Bab I | Fondasi Formal Matematika Hijaiyyah |
| Bab II | Lima Bidang Matematika Hijaiyyah |
| | Hijaiyyah Technology Stack v1.0 |
| `docs/architecture.md` | Arsitektur HOM |
| `docs/hc_language.md` | Spesifikasi HC Language |
| `docs/hcvm_spec.md` | Spesifikasi HCVM |
| `src/hijaiyyah/hisa/` | Implementasi H-ISA |

---

<div align="center">

**H-ISA — Hijaiyyah Instruction Set Architecture**

*Version 1.0 · HM-28-v1.0-HC18D · 2026*

© 2026 Hijaiyyah Mathematical Computing Laboratory (HMCL)

</div>
