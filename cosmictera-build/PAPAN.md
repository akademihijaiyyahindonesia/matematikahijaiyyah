# Papan: hasil menjalankan seluruh program di silikon

**Diukur 10 September 2026**, Tang Nano 20K (GW2AR-LV18QN88C8/I7), papan
fisik pertama proyek ini. Sebelum tanggal itu tidak satu pun bitstream di
repositori ini pernah benar-benar dinyalakan — semua bukti berhenti di
Icarus Verilog atau di `gowin_pack` menghasilkan `.fs`.

Berkas ini mencatat apa yang **dijalankan** dan apa yang **keluar**.
[ON.md](ON.md) dan [OFF.md](OFF.md) mencatat keadaan; [ROADMAP.md](ROADMAP.md)
mencatat yang belum. Ini mencatat pengukuran.

---

## Cara program sampai ke papan

Dua jalur, dan perbedaannya menentukan cara membaca angka di bawah.

**Dipanggang.** `PROGRAM=<x>.hasm make bitstream` menaruh program di
`imem` lewat `$readmemh` saat sintesis. Program mulai di alamat 0 begitu
reset lepas. Satu program per bitstream, dan tiap penggantian menuntut P&R
ulang — 10–17 menit.

**Lewat kabel.** Bitstream memanggang `loader.hasm`, lalu
`rtl/scripts/send_program.py` mengirim program lewat UART: 4 byte jumlah
kata big-endian, lalu 4N byte. Loader menulisnya ke `imem` **mulai alamat
64** dan melompat ke sana. Penggantian program jadi hitungan detik.

Seluruh tabel di bawah memakai jalur kedua kecuali disebut lain, dengan
rekonfigurasi FPGA sebagai reset di antara program — tombol reset papan
tidak bisa dipakai, dan sebabnya ada di bagian [cacat](#tiga-cacat-yang-hanya-papan-bisa-temukan).

---

## HCPU: 21 program

| Program | kata | Keluaran |
|---|---:|---|
| `test_bsm` | 9 | `112` |
| `test_distance` | 11 | `1 2 3` |
| `test_guard` | 143 | `28` |
| `test_hisab` | 6 | `65824` / `2586986;>:` |
| `test_loop` | 7 | `10` |
| `test_negative` | 9 | `200` |
| `nui_embedding` | 48 | `2 2 2 6 6` |
| `hal` | 28 | halt, lapor siklus |
| `hos` | 318 | halt, lapor siklus |
| `hos_demo` | 391 | halt, lapor siklus |
| `kernel` | 372 | halt, lapor siklus |
| `jamrah_gate` | 31 | halt, lapor siklus |
| `letters` | 37 | halt, lapor siklus |
| `payload` | 3 | halt, lapor siklus |
| `subroutine` | 51 | halt, lapor siklus |
| `timer_poll` | 9 | halt, lapor siklus |
| `mem_protect` | 28 | **nol byte** |
| `syscall` | 30 | **nol byte** |
| `syscall_io` | 46 | **nol byte** |
| `trap_timer` | 19 | **nol byte** |
| `user_mode` | 22 | **nol byte** |

## Bench: 11 program

| Program | kata | Keluaran |
|---|---:|---|
| `e2_guard_x1` | 17 | halt, lapor siklus |
| `e2_guard_x10` | 26 | halt, lapor siklus |
| `e2_hisab` | 20 | halt, lapor siklus |
| `e2_scale_n02` | 5 | halt, lapor siklus |
| `e2_scale_n04` | 9 | halt, lapor siklus |
| `e2_scale_n08` | 17 | halt, lapor siklus |
| `e2_scale_n12` | 25 | halt, lapor siklus |
| `e3_sweep28` | 113 | 28 nilai Θ̂ — lihat di bawah |
| `e4_frame` | 10 | `65824` / `28521=6:7` / `16144` / `2586977>::` |
| `e5_negative` | 9 | `200` |
| `e6_record_triage` | 54 | `200` |

### Angka `CYCLES` dari jalur loader tidak sebanding dengan yang dipanggang

`test_bsm` dipanggang melapor **7.049** siklus, cocok persis dengan
testbench. `test_bsm` yang sama lewat loader melapor **11.333.893**. Bukan
program yang melambat: pencacah berjalan sejak reset lepas sampai halt, dan
lewat loader itu termasuk seluruh waktu loader menunggu byte UART tiba pada
115.200 baud. Angka siklus lewat kabel karenanya **tidak** mengukur program;
ia mengukur program plus transportasinya. Hanya angka dari bitstream yang
dipanggang yang boleh dibandingkan dengan simulasi.

---

## Yang paling berarti: 28 huruf, dibaca balik dari silikon

`e3_sweep28` mengeksekusi ROM bersegel huruf demi huruf dan mengembalikan
komponen Θ̂ tiap entri:

```
0 2 2 2 3 3 3 1 1 1 1 4 4 6 6 4 4 3 3 5 6 2 1 4 2 5 8 3
```

Dibandingkan langsung dengan `MASTER_TABLE` kanonik
(`src/hijaiyyah/core/master_table.py`, `[e.vector[0] for e in
MASTER_TABLE.all_entries()]`):

```
IDENTICAL: True
```

Dua puluh delapan dari dua puluh delapan, tanpa penyimpangan. Ini memenuhi
syarat pertama yang `rtl/mpw/MPW_SHUTTLE_PLAN.md` sebut **kritis** sebelum
tapeout MPW: seluruh entri ROM terverifikasi di perangkat keras, bukan di
simulator.

`nui_embedding` mengembalikan `2 2 2 6 6` — titik, garis, lengkung, theta,
rho — konfirmasi fisik pertama untuk embedding fisika yang selama ini hanya
pernah tervalidasi di simulator.

---

## Ka'bah

`rtl/scripts/kabah_uart_test.py` terhadap `hijaiyyah_kabah_gowin_top.fs`:

```
frame1: PASS, 200/200 bytes match cube.py
frame2: PASS, 200/200 bytes match cube.py
PASS: 2/2 frame(s), 400 bytes total, all match cube.py
```

Dua frame 128 byte dikirim berturut **tanpa reset di antaranya**, jadi ini
menguji penyerapan berantai lintas blok — bukan satu blok yang kebetulan
benar sendirian. Terukur: 12.061 LUT4 (58%), 1.965 DFF (12%), 0 BSRAM,
Fmax 165,98 MHz.

## Video

`hcpu_hdmi_top` menghasilkan 1280x720 lewat TMDS pada pasangan diferensial
pin 33–40, `pixel_clk` 477,78 MHz dan `u_hcpu.clk_27m` 124,61 MHz pasca
perutean. Satu bitstream membawa ketiganya sekaligus — video, loader, dan
HCPU — dibuktikan dengan mengirim `e3_sweep28` lewat kabel saat layar
menyala dan menerima 28 nilai yang sama.

---

## Lima program yang tidak berjalan, dan sebabnya bukan CPU

`mem_protect`, `syscall`, `syscall_io`, `trap_timer`, `user_mode` —
kelimanya program mode-terproteksi atau trap, dan kelimanya mengembalikan
nol byte.

Kelimanya **lulus di testbench masing-masing**. Sebabnya ada di jalur
loader: program dimuat mulai alamat 64, tetapi `MOVI Rx, label` dirakit
sebagai alamat **absolut** dengan asumsi basis 0 dan tidak direlokasi.
Program yang memasang vektor trap dari sebuah label —
`rtl/programs/trap_timer.hasm:22`, `rtl/programs/user_mode.hasm:28` —
mengarahkan trap ke wilayah kode loader; CPU tersesat, tidak pernah halt,
tidak pernah mencetak.

Cabang relatif tidak terpengaruh, dan itu sebabnya `test_guard` (143 kata,
penuh cabang) berjalan normal.

**Untuk mengujinya di papan, program-program ini harus dipanggang langsung
ke bitstream**, bukan dikirim lewat loader. Itu belum dilakukan.

---

## Tiga cacat yang hanya papan bisa temukan

Ketiganya lolos 20 testbench RTL dan 4.500-an tes Python. Simulasi bukan
lalai — ia secara struktural buta terhadap ketiganya.

**1. Reset yang digerbangi level pin MODE1.** `btn_rst_n` ada di pin 87,
yang papan tahan rendah. Sebagai reset asinkron level-sensitif ia mengunci
`sys_rst_n` di 0 selamanya: bitstream terkonfigurasi lalu tidak
mengeksekusi apa pun. Muncul **empat kali di tiga wrapper** — HCPU, kedua
wrapper HDMI, dan Ka'bah. `PULL_MODE=UP` terverifikasi masuk basis data
P&R dan tidak menolongnya; papan menang atas pull-up internal. Perbaikannya
deteksi tepi turun yang sinkron. Testbench menggerakkan pin itu tinggi,
jadi tidak pernah melihatnya.

**2. Memori instruksi kosong di setiap bitstream yang pernah dibangun.**
For-loop pengisi NOP sebelum `$readmemh` membuat yosys membuang readmemh
tanpa peringatan. Diisolasi di kasus 14 baris tanpa HCPU sama sekali:

| Bentuk | INIT terbawa | Pemetaan |
|---|---|---|
| `$readmemh` saja | 11 bit | `SP` |
| for-loop + `$readmemh` | **0 bit** | `SPX9` |
| guard `` `ifndef YOSYS `` | 11 bit | `SP` |

Tak terlihat selama ini karena `OP_NOP` bernilai `8'h00` — "memori
dikosongkan" dan "memori terisi NOP" adalah bit yang identik. Bitstream 9
September juga diukur: `imem` nol total. Setelah perbaikan, INIT berisi 30
bit satu, sama persis dengan 30 bit di `program.hex`.

**3. Driver diferensial TMDS tidak pernah ada di bitstream.**
`TLVDS_TBUF` yang di-instantiate tangan tidak selamat: yosys tetap
menyisipkan `OBUF`-nya sendiri di tiap port top-level, sehingga netlist
menjadi `TLVDS_TBUF → OBUF → pad` — mustahil, karena `TLVDS_TBUF` **adalah**
buffer pad. nextpnr lalu membuang keempatnya dan meninggalkan delapan OBUF
single-ended di pin 33–40. Terukur di `hdmi_pnr.json`: nol sel TLVDS
ditempatkan. Perbaikannya menghapus primitif, bukan menambahnya: hanya P
yang jadi port, dan `IO_LOC "<sel>" 33,34;` dengan `LVCMOS33D` yang
membuat pasangannya diferensial.

---

## Suite yang mendampingi

| | Hasil |
|---|---|
| `python3 -m pytest -q` | 4.606 lulus, 0 dilewati, 0 gagal |
| `make -C rtl/tb all` | 20 testbench, 253 pemeriksaan, 0 gagal |

Rincian per testbench, dijumlah dari baris ringkasan tiap testbench: ROM 30,
Guard 34, Codex ALU 6, HISAB 124, `tb_hcpu_top` 13, NUI embedding 10, H-Kernel
7, syscall I/O 6, HOS 6, subrutin 4, huruf 3, wrapper Gowin 2, dan delapan
testbench yang melapor satu pernyataan lulus tunggal — 253, semuanya 0 FAIL.

> **Angka 253 ini mengoreksi dua angka yang tidak konsisten.** Baris ini pernah
> berbunyi "160 pemeriksaan" sementara rinciannya sendiri berjumlah 308, dan
> keduanya salah. 308 menghitung ganda: sapuan 28 huruf yang 112 itu **sub-total
> di dalam** HISAB 124, bukan tambahannya, dan `tb_hisab` sendiri mencetak
> keduanya. "Gowin wrapper: 1" lalu "2" juga bukan dua ringkasan melainkan satu
> pencacah `pass_count` yang dicetak dua kali (`rtl/tb/tb_gowin_top.v:137,194`),
> jadi wrapper menyumbang 2 dan bukan 3. Sedangkan 160 tidak cocok dengan
> perhitungan mana pun — ia tidak pernah diturunkan dari log. 253 diambil dari
> keluaran `make -C rtl/tb all` yang dijalankan ulang, satu baris ringkasan per
> testbench.

> **Angka pytest juga dikoreksi, dan sebabnya bukan desain.** Baris ini pernah
> berbunyi 4.519 lulus / 16 dilewati. Dijalankan ulang, 24 tes gagal dengan
> `OSError: [Errno 8] Exec format error` — bukan regresi desain, melainkan cara
> tes meluncurkan simulator. iverilog menandai keluarannya dengan `#!` yang
> menunjuk ke `vvp`, dan pada oss-cad-suite `vvp` itu sendiri skrip bash;
> shebang yang menunjuk ke skrip shebang lain tidak bisa diselesaikan `execve`,
> jadi `subprocess.run([path])` gagal sementara testbench-nya sendiri lulus
> sepanjang waktu. Lima belas titik panggil di empat berkas tes kini memanggil
> `vvp` dengan nama, seperti lima berkas lain di suite yang sama sudah lakukan.
> 4.606 lulus, 0 dilewati, 0 gagal — 24 tes lebih banyak yang benar-benar
> dieksekusi, bukan dilewati.

> **Dan selisih tiga yang tersisa akhirnya punya nama.** `--collect-only`
> melaporkan 4.534 sementara run melaporkan 4.537, berapa pun angka yang
> dikutip — jadi tidak ada pasangan angka yang bisa membuat penjaganya hijau
> tanpa berbohong. Sebabnya: **modul yang dilewati saat impor**. Tiga berkas
> (`test_nui.py`, `test_nui_atom.py`, `test_nui_multitask.py`) memanggil
> `importorskip("torch")` di puncak berkas, sehingga masing-masing dihitung
> satu skip di ringkasan tetapi **tidak menghasilkan satu pun item terkumpul**.
> Sembilan skip `pymupdf` sisanya ada di dalam berkas, jadi terkumpul dan
> muncul per tes. Identitasnya karena itu bukan `lulus + dilewati =
> terkumpul`, melainkan `lulus + dilewati = terkumpul + skip-modul`:
> 4.525 + 12 = 4.534 + 3. Penjaganya di `test_build_list.py` sudah dibetulkan
> untuk menghitung suku yang hilang itu, dan tetap murah — `-rs` melaporkannya
> pada koleksi yang sama, tanpa menjalankan satu tes pun.

---

## Yang belum

- Lima program trap/supervisor belum pernah dipanggang langsung ke
  bitstream, jadi belum pernah benar-benar diuji di papan.
- HCPU + Ka'bah sebagai satu top level: **105%, lewat 960 sel** — diukur,
  belum muat. Rinciannya di [ROADMAP.md](ROADMAP.md) Fase 4.
- Tombol reset papan tidak berfungsi sebagai reset di ketiga wrapper, dan
  itu diterima: rekonfigurasi FPGA yang jadi reset. Pin MODE1 tidak akan
  pernah bisa dipakai sebagai tombol di papan ini.
