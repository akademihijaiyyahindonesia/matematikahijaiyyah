# Silikon: nama yang hanya ada di RTL

Kosakata yang tidak punya padanan di perangkat lunak, karena ia menyebut kawat,
tahap pipeline, atau batas papan.

---

## Register dan lebarnya

| istilah | arti | di mana |
|---|---|---|
| **H-Reg** | register hybit: **144 bit = 18 × 8** | `hcpu_pkg.vh` — `HREG_W` |
| **GPR** | register umum 32 bit, **delapan belas** (R0–R17), bukan enam belas | `hcpu_pkg.vh` — `GPR_COUNT` |
| **bank codex** | H0–H15, **enam belas** (`HREG_COUNT`) | `hcpu_regfile.v` |
| **COMP_W** | lebar satu komponen codex: 8 bit | `hcpu_pkg.vh` |

**Delapan belas GPR, bukan enam belas, dan sebabnya bukan kenyamanan.** Buku
§IIIJ.3.3.1 memberi bank 18 register dan menugaskan R17 sebagai register
tautan; `AGENTS.md` mencatat dua di antaranya sempat tak pernah bisa dipakai.

---

## Pipeline lima tahap

```
Fetch → Decode → Execute → Memory → Writeback
```

| istilah | arti | di mana |
|---|---|---|
| **forwarding** | EX→ID dan MEM→ID, GPR dan H-Reg | `hcpu_forward.v` |
| **load-use hazard** | interlock satu siklus | `hcpu_top.v` |
| **redirect** | cabang **atau** trap; keduanya jalur yang sama | `hcpu_top.v` |
| **bayangan redirect** | dua siklus yang dibayar sebuah redirect, tempat `if_pc` tidak sah | `073b968` |
| **write-through** | register file transparan pada siklus tulisnya sendiri | `hcpu_regfile.v` |

**Bayangan redirect** adalah istilah yang lahir dari cacat, bukan dari desain:
`073b968` mengukur 60 trap, 21 di antaranya menyimpan `epc = 0`, dan semuanya
tepat di dua siklus itu.

---

## Guard di perangkat keras

| istilah | arti | di mana |
|---|---|---|
| **HGRD** | opcode 0x60: jalankan G1–G4, T1–T2 atas H[S1] → flag GUARD | `hcpu_guard.v` |
| **VCHK** | **nama kedua untuk `HGRD`** — `VCHK = 0x60 # → HGRD` | `hisa/opcodes.py` |
| **flag GUARD** | bit 0 FLAGS, dibaca `JGD`/`JNGD` — **bukan** flag aritmetika | `hcpu_execute.v` |

> **`CMP` lalu `JGD` tidak berarti "lompat kalau lebih besar".** Flag G adalah
> bit yang sama di register FLAGS, tetapi ia flag lulus-guard dan tidak ada
> hubungannya dengan aritmetika. `hos.hasm` mencatatnya sebagai jebakan yang
> pernah menggigit, dan `hos_size_ge` adalah jalan memutarnya.

**Tidak ada cabang yang membaca LT.** FLAGS punya Z dan LT, tetapi kelima
lompatan ISA ini — `JMP`, `JEQ`, `JNE`, `JGD`, `JNGD` — tak satu pun membacanya.

---

## Jamrah

| istilah | arti | di mana |
|---|---|---|
| **gerbang jamrah** | pohon reduksi 8-daun, **tujuh simpul dalam**, tiap simpul disadap | `rtl/hijaiyyah_jamrah_gate.v` |
| **tap** | sadapan pada simpul dalam; menyimpan jumlah parsial yang popcount buang | `rtl/hijaiyyah_jamrah_gate.v` |

Namanya dari **Jamrat al-Aqabah** — tujuh kerikil pada satu tiang — dan
berkasnya menolak dibaca sebagai kiasan: pohon reduksi 8-daun punya 7 simpul
dalam karena alasan yang sama ritus 7-kerikil punya satu tiang, **keduanya
reduksi biner yang lengkap**.

---

## Batas papan

| istilah | arti | di mana |
|---|---|---|
| **plafon penempatan** | ≈16.000 LUT4, bukan 20.736 nominal | `cosmictera-build/OFF.md` |
| **rack** | slot bitstream berurutan; biayanya **max**, bukan **sum** | `rtl/scripts/rack.py` |
| **slot** | satu konfigurasi fabric; dua slot tak pernah hidup bersama | `rtl/scripts/rack.py` |
| **sidik jari RTL** | hash sumber yang mengikat angka ke desain yang mengukurnya | `test_place_and_route.py` |
| **OSER10** | serialiser 10:1; menduduki IOLOGIC **kedua** belahan pasangan IO | `dvi_tx_open.v` |
| **MODE1** | pin 87, ditahan rendah papan — pernah mengunci reset | `hcpu_hdmi.cst` |

**Plafon penempatan** adalah istilah yang harus dibaca sebelum mendesain apa
pun: empat desain yang benar secara logika sudah ditolak di sana, dan tiap kali
ditemukan **sesudah** pekerjaannya rampung.

---

Dijangkarkan oleh `tests/test_integrity/test_place_and_route.py` dan
`test_istilah.py`.
