# Pemahaman program — Lapis 2 NUI

**Perintah pemilik, 21 September 2026.** Lapis 1 menjawab *apa terhubung dengan
apa*. Lapis ini menjawab *apa yang dilakukan* — untuk program HASM, fungsi
Python, dan modul Verilog.

Aturan dari Lapis 1 tetap berlaku: **tidak ada jawaban yang boleh berupa
inferensi.** Jadi NUI tidak *menulis* bahwa `loader.hasm` membaca UART; ia
harus *membacanya* dari instruksinya.

## Bentuknya

```
62 program HASM       semuanya terurai dengan tabel opcode assembler sendiri
1.501 fungsi Python   di src/, lewat ast
121 modul Verilog     port, blok clocked dan kombinasional, instansiasi

277 CALL HASM         semuanya mendarat di label nyata
126 instansiasi       terselesaikan, ditambah 8 primitif vendor
0 tak terselesaikan
```

## Dua hal yang tidak pernah dicampur

Tiap unit membawa **`stated`** — kalimat pembuka komentar atau docstring-nya
sendiri, **dikutip**, sebagai kata-kata penulisnya — dan **`observed`**, efek
yang diturunkan dari badannya, masing-masing dengan baris yang menghasilkannya.
Yang satu klaim penulis, yang lain apa yang kodenya tunjukkan. Pembaca harus
bisa membedakannya.

| jenis | yang diturunkan |
|---|---|
| HASM | `LOAD`/`STORE` yang offset-nya menamai register memory-mapped, `PRINT`/`EMITS`, `HALT`, `ERET`, `SYSCALL`, target `CALL` dan `JMP`, opcode codex, `.include` |
| Python | I/O yang dilakukan (berkas, subprocess, port serial, konsol), apakah ia mengembalikan nilai, dan nama yang dipanggilnya **apa adanya** |
| Verilog | port, blok clocked dan kombinasional, modul yang diinstansiasi |

Nama register diambil dari **dua tabel yang sudah ada**, tidak diketik ulang:
`0xFF0` ke atas dari konstanta `REG_*` interpreter, `0xFE0` ke atas dari
`define SD_*` di `rtl/hcpu_pkg.vh`.

## Tiga pertanyaan pemilik, dijawab

**Apa fungsi `loader.hasm`?**

```
stated:   "loader.hasm — the boot path. This is what makes the board a bridge."
observed:
  reads RX_STATUS (0xff1)      baris 36
  reads RX_DATA (0xff0)        baris 39
  writes IMEM_ADDR (0xff3)     baris 49, sekali
  writes IMEM_DATA (0xff7)     baris 65
  writes TRAP_EPC (0xff9)      baris 71
  writes TRAP_MODE (0xffd)     baris 73
  returns from a trap (ERET)   baris 74
```

Cocok dengan jawaban yang pemilik harapkan — membaca UART, menulis memori
instruksi, masuk ke program yang dimuat — **dengan dua ketelitian yang
diturunkan, bukan diduga**:

- ia **tidak melompat** ke program yang dimuat; ia menyerahkan kendali lewat
  `TRAP_EPC` + `TRAP_MODE` + `ERET`. `JMP words` di baris 67 adalah gelung
  penerima katanya sendiri;
- alamat tulis **ditulis sekali**. Kenaikannya dikerjakan perangkat keras
  `IMEM_DATA`, bukan instruksi.

**Dan klaim itu diperiksa terhadap eksekusi**, bukan hanya terhadap teks:
`freeze_load()` menjalankan `loader.hasm` di interpreter dengan sebuah
program kecil di kabelnya, dan port tulisnya harus maju sepanjang program
itu, serta keluaran program itu sendiri harus muncul — yang hanya terjadi
kalau serah-terimanya benar-benar sampai.

**Apa fungsi `freeze_load()`?** — *"Run loader.hasm against a mocked wire
carrying `program_src`, no RTL simulator and no real clock involved: …"*;
ia memanggil `assemble`, `HISAMachine`, `mock_wire`, `step`, membaca sebuah
berkas, dan mengembalikan nilai.

**Apa fungsi `clockwork.run()`?** — *"Step through `letters` IN ORDER — order
genuinely changes the result here (compose_step does not commute), unlike
dataset.py's v18 accumulation."*; ia memanggil `gf2_rank`, `matrix_order_of`,
`Tick`, `step`, `chip_for`, `atom_for`, dan mengembalikan nilai.

## Dua temuan dari membangunnya

**Satu modul, dua rumah.** `hcpu_dataram` punya implementasi FPGA dan makro
SRAM sky130; `hcpu_top` punya RTL dan netlist hasil sintesis. Yang dipilih
**alur build**, bukan teksnya. Versi pertama graf diam-diam memilih berkas
pertama yang ditemukan — sebuah tebakan — dan sekarang keduanya ditautkan
dengan keterangan bahwa ia salah satu dari beberapa rumah.

**Satu primitif vendor yang terlewat.** `MMCME2_BASE` kembali sebagai
satu-satunya instansiasi tak terselesaikan: pengelola clock Xilinx, di wrapper
Xilinx, tepat di tempatnya. Daftar vendor semula hanya Gowin dan sky130.

## Yang tidak ada, dan kenapa

**Tautan fungsi-ke-fungsi Python.** Fungsi mana yang dimaksud sebuah panggilan
ke `run` tidak ada di teksnya, dan menebaknya akan jadi inferensi pertama.
Nama yang dipanggil dicantumkan **apa adanya, dan ditandai tak
terselesaikan**.

**Apakah sebuah register benar-benar tercapai.** `LOAD R1, R5, 0xFF0` membaca
UART hanya kalau R5 bernilai nol saat dijalankan. Itu pertanyaan **eksekusi**
— Lapis 3. Di sini efek memory-mapped berarti instruksinya *menamai* register
itu, persis yang teksnya tunjukkan.

## Menjalankannya

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.program_index
PYTHONPATH=src python3 -m hijaiyyah.nui.program_graph
PYTHONPATH=src python3 -m hijaiyyah.nui.program_summary rtl/programs/loader.hasm
PYTHONPATH=src python3 -m hijaiyyah.nui.program_summary "src/hijaiyyah/nui/freeze.py::freeze_load"
PYTHONPATH=src python3 -m hijaiyyah.nui.program_summary "rtl/hcpu_uart_rx.v::hcpu_uart_rx"
python3 -m pytest -q tests/test_ai/test_nui_program_index.py
```

## Yang dijaga

`tests/test_ai/test_nui_program_index.py`, sembilan tes. Tiap efek turunan
di ke-62 program harus menunjuk ke baris yang memuat instruksi penghasilnya;
efek `loader.hasm` diperiksa terhadap eksekusi; tiap `CALL` dan instansiasi
terselesaikan atau adalah primitif vendor bernama; modul berumah dua tidak
diselesaikan dengan menebak; dan `stated` harus muncul kata demi kata di
berkasnya. Tiga sabotase diuji dan ketiganya merah: efek yang digeser satu
baris, rumah pertama dipilih diam-diam, dan tujuan yang diparafrasekan alih-alih
dikutip.
