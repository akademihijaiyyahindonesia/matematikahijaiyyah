# Daftar cek

Setiap ✅ di bawah ini **dijalankan**, bukan diingat. Kolom terakhir adalah
perintahnya: salin, jalankan, dan Anda mendapat centang yang sama atau tahu
persis apa yang berubah.

Sebuah baris hanya boleh hijau kalau ada pemeriksaan otomatis yang lulus
**sekarang**. Tidak ada centang untuk "sudah ditulis", "pernah jalan", atau
"tinggal sedikit lagi".

---

## Perkakas

| | apa | perintah |
|---|---|---|
| ✅ | Python, pytest, ruff, mypy | `python3 -m pytest --version` |
| ✅ | Icarus Verilog | `iverilog -V` |
| ✅ | yosys | `yosys -V` |
| ✅ | nextpnr-himbaechel | `nextpnr-himbaechel --version` |
| ✅ | gowin_pack | `gowin_pack --help` |
| ✅ | openFPGALoader | `openFPGALoader --Version` |

Kelimanya terpasang di `~/opt/oss-cad-suite`. Satu perintah memeriksa semuanya:
`make -C rtl/fpga/gowin tools`.

---

## Kebersihan pohon

| | apa | perintah |
|---|---|---|
| ✅ | **4.300 tes lulus**, 4 dilewati † | `python3 -m pytest -q` |
| ✅ | ruff bersih | `make lint` |
| ✅ | mypy bersih, 108 berkas | `make typecheck` |
| ✅ | Master Table utuh | `make verify` |
| ✅ | Citra ROM terbangkitkan | `make rom` |
| ✅ | ROM cocok dengan tabel | `python3 rtl/scripts/cross_verify_rom.py` |
| ✅ | Suite deterministik | 40 jalan berturut `test_memscan`, 0 gagal |

† Satu-satunya angka di halaman ini yang **tidak dijaga**. Cacah bench dan
asersi dibaca ulang dari Makefile oleh
[`test_build_list.py`](../tests/test_integrity/test_build_list.py), tapi cacah
pytest tidak bisa diperiksa tanpa menjalankan pytest di dalam pytest. Ia
cuplikan 3 September 2026; perintah di sebelahnya yang menjadi kebenarannya.

Baris terakhir bukan hiasan. `test_every_clue_is_distinctive_enough_to_be_worth_having`
mengambil `os.urandom` lalu menuntut penanda tidak muncul di dalamnya — dua
penanda panjangnya 3 byte, jadi suite gagal kira-kira **1 dari 127 jalan**.
Berkas itu sendiri sudah menulis pelajarannya satu fungsi di atasnya. Sekarang
sifatnya diasersi secara aritmetika dan deraunya berbenih.

---

## Perangkat keras — simulasi

| | apa | perintah |
|---|---|---|
| ✅ | **240 asersi, 17 bench, 0 gagal** | `make -C rtl/tb all` |
| ✅ | ROM 28 huruf | `make -C rtl/tb sim_rom` |
| ✅ | Guard G1–G4, T1–T2 | `make -C rtl/tb sim_guard` |
| ✅ | Codex ALU | `make -C rtl/tb sim_codex_alu` |
| ✅ | HISAB, sapuan 28 huruf | `make -C rtl/tb sim_hisab` |
| ✅ | Integrasi top-level | `make -C rtl/tb sim_top` |
| ✅ | Unit trap, 6 penyebab | `make -C rtl/tb sim_trap` |
| ✅ | MMIO, timer, UART RX | `make -C rtl/tb sim_mmio sim_timer sim_uart_rx` |
| ✅ | **H-Kernel: tiga proses + daemon guard** | `make -C rtl/tb sim_kernel` |
| ✅ | **28 instruksi huruf** | `make -C rtl/tb sim_letters` |
| ✅ | **`CALL`/`RET`, sarang 8 tingkat** | `make -C rtl/tb sim_subroutine` |
| ✅ | **I/O lewat kernel, dua sisi** | `make -C rtl/tb sim_syscall_io` |
| ✅ | Wrapper papan | `make -C rtl/tb sim_board` |
| ✅ | Boot lewat kabel | `make -C rtl/tb sim_loader` |
| ✅ | **Cabang & interupsi bertabrakan** | `make -C rtl/tb sim_branch_trap_race` |
| ✅ | **HOS: heap, HFS guard-on-write, HAR** | `make -C rtl/tb sim_hos` |

Lima baris tebal itu baru hijau **hari ini**, dan semuanya sempat berbohong:

- **H-Kernel** hijau karena `B = 127400 = 1274 × 100`. Kelipatan yang bersih
  hanya mungkin bila R1 milik B tak pernah memegang nilai A.
- **Instruksi huruf** hijau karena `||Ba+Sin+Mim||² = 112` lewat jalur huruf —
  angka yang sama yang sudah dibuktikan jalur HLOAD/HCADD. Sebelum hari ini
  jawabannya **0**: `default:` kedua di tengah `case` membuat kedua puluh
  delapan opcode menulis nol, dan tak ada bench yang pernah menjalankan satu
  pun. Enam bench di kolom ini juga tidak punya target `make` sama sekali.
- **`R0`-`R17` bukan enam belas register — kecuali dua tak pernah bisa
  dipakai.** Buku sendiri berkontradiksi: §IIIJ.3.3.1 (hal. 133) memberi GPR
  bank 18 register, R0–R17, bahkan menugaskan R17 sebagai register tautan.
  §IIIF.3.3.1 (hal. 127), format word instruksi, memberi tiap field register
  **4 bit** — tidak bisa menamai lebih dari 15. Assembler dulu memangkas
  dengan `& 0xF` alih-alih memeriksa, jadi `MOVI R16, 7` terakit **identik**
  dengan `MOVI R0, 7`, diam-diam. Kernel yang barusan dibangun sebelum
  temuan ini menyimpan "18 register" per proses — sebenarnya menyimpan R0
  dan R1 dua kali, kebetulan tak merusak apa pun karena mendorong lalu
  memuat nilai yang sama dua kali adalah no-op. Sekarang assembler menolak
  R16/R17 dengan pesan yang mengutip kedua bagian buku, dan kernel menyimpan
  enam belas yang sungguh ada — lihat `MAX_GPR` di
  `src/hijaiyyah/hisa/assembler.py` dan
  [`test_the_code_follows_the_field_width_not_the_count`](../tests/test_integrity/test_book_anchor.py).
- **Cabang yang diambil bisa kalah dari interupsi yang bertepatan — dan
  epc-nya salah, bukan cabangnya.** Ditemukan lewat daemon penjaga: sebuah
  `JGD` yang baru saja lulus guard-nya kembali ke jalur "guard gagal", sekali
  dalam 400.000 siklus. Sebabnya: `pc_now` (yang disimpan interupsi
  maskable sebagai alamat kembali) memakai `if_pc` — tebakan sekuensial
  spekulatif Fetch, satu tahap di depan Execute yang justru sedang
  menyelesaikan cabang itu SAAT itu juga. Jika interupsi tiba tepat di
  siklus itu, `if_pc` masih menunjukkan alamat jatuh-lanjut cabang, bukan
  targetnya — dan cabang itu tak pernah "diputar ulang": efek sampingnya
  (misalnya dorongan stack alamat-kembali `CALL`) sudah terlanjur commit.
  Diperbaiki dengan satu mux: `branch_taken_w ? branch_target_w : if_pc`.
  `tb_hcpu_branch_trap_race.v` mereproduksinya sesuai permintaan, dengan
  menyapu tenggat timer sampai bertepatan persis dengan siklus Execute —
  bukan menunggu 1-dari-532 keberuntungan.
- **FLAGS tidak punya write-through — GPR dan H-Reg punya.** Ditemukan lewat
  HOS: `CMP R1,R2` untuk dua alamat heap yang genuinely berbeda (3587,
  3594) menghasilkan Z=1 (salah — seharusnya 0) tepat di titik `JNE`
  membacanya. `hcpu_regfile.v` punya baris eksplisit "GPR read (with
  transparent write-through)" untuk GPR dan H-Reg —
  `gpr_rdata1 = (gpr_we && gpr_waddr==gpr_raddr1) ? gpr_wdata : gpr[...]` —
  tapi FLAGS hanya `assign flags_out = flags;`, murni nilai teregister
  siklus lalu, tanpa bypass. Rantai forward di `hcpu_execute.v`
  (`forwarded_flags`) menutupi konsumen 1-2 tahap di belakang produsen
  (EX-forward, MEM-forward) lalu jatuh ke `current_flags` — dan `current_flags`
  itulah yang, tanpa write-through, tetap basi tepat di siklus tulisannya
  sendiri commit. Celah ini sempit: **setiap** pasangan CMP-lalu-cabang yang
  sudah ada di seluruh repositori ini berdampingan langsung (jarak nol
  instruksi), selalu masuk jendela EX-forward, tak pernah menyentuh
  register ini sama sekali. `hos_alloc` adalah kode pertama yang punya satu
  instruksi di antara perbandingan dan cabangnya, DAN cukup stall (dari
  interlock load-use pada dua LOAD berurutan) untuk menaruh pembacaan
  cabang itu tepat di siklus tabrakan. Diperbaiki dengan satu baris,
  menyalin pola GPR persis: `assign flags_out = flags_we ? flags_in : flags;`
  Direproduksi minimal di `tb_hcpu_hos.v` dan seluruh 17 bench tetap hijau
  sesudahnya.

---

## Matematika dan angka

| | apa | bukti |
|---|---|---|
| ✅ | 28 huruf kanonik dari PDF bersegel | `make verify` |
| ✅ | Closure monoid dibuktikan, bukan disampel | `tests/test_algebra/` |
| ✅ | Cakupan guard **93,1%**, dan itu langit-langitnya | `matematika-hijaiyyah/GUARD.md` |
| ✅ | Throughput **2,59 MB/s**, hambatan = deserialiser | `src/hijaiyyah/crypto/kabah.py` |
| ✅ | 72 dari 96 opcode di RTL, 24 sisanya dinamai | [OFF.md](OFF.md) |

---

## Belum hijau

Dua, dan keduanya dinamai supaya centang di atas berarti sesuatu.

| | apa | keadaan |
|---|---|---|
| ⬜ | `python3 rtl/scripts/lint_hcpu.py` | **0 error struktural** (dulu 1), sisa **76 peringatan** — keluar bukan-nol |
| 🔴 | `make -C rtl/fpga/gowin bitstream` | **gagal**: 13.945 / 8.640 LUT4 = **161%** |

Error Verilator hilang justru karena `default:` ganda itu diperbaiki — jadi
lint yang selama ini merah sebenarnya sedang menunjuk cacat huruf, dan tak ada
yang membacanya. Peringatan yang tersisa soal bit yang tak terpakai.

Bitstream merah, bukan kosong: **papan tidak bisa di-flash dari komit ini.**
Sebabnya satu komit dan sudah dibisect — lihat [OFF.md](OFF.md).

---

## Satu tarikan napas

```bash
make -C rtl/fpga/gowin tools     # 5/5 perkakas
make lint typecheck verify rom   # bersih
python3 -m pytest -q             # 4.300 lulus, 4 dilewati
make -C rtl/tb all               # 240 asersi, 17 bench, 0 gagal
make -C rtl/fpga/gowin bitstream # ← merah, dan memang seharusnya terlihat
```

Perintah terakhir sengaja ikut. Daftar cek yang berhenti sebelum baris merah
bukan daftar cek.
