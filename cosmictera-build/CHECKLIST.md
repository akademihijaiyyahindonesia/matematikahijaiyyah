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
| ✅ | **4.961 tes lulus**, 0 dilewati † | `python3 -m pytest -q` |
| ✅ | ruff bersih | `make lint` |
| ✅ | mypy bersih, 128 berkas | `make typecheck` |
| ✅ | Master Table utuh | `make verify` |
| ✅ | Citra ROM terbangkitkan | `make rom` |
| ✅ | ROM cocok dengan tabel | `python3 rtl/scripts/cross_verify_rom.py` |
| ✅ | Suite deterministik | 40 jalan berturut `test_memscan`, 0 gagal |

† Cacah **terkumpul** kini dijaga; cacah **lulus** tidak bisa. Catatan ini
pernah berbunyi "satu-satunya angka yang tidak dijaga ... tidak bisa diperiksa
tanpa menjalankan pytest di dalam pytest", dan separuhnya keliru:
`pytest --collect-only -q` mencacah 4.961 dalam 9 detik tanpa menjalankan satu
tes pun. Selama tak dijaga, ketiga berkas hanyut sendiri-sendiri — halaman ini
mengatakan 4.565 sementara [ON.md](ON.md) dan [README.md](README.md) tertinggal
di 4.454. `test_build_list.py` sekarang mencacah ulang dan menuntut ketiganya
sama. Yang tetap tak terjaga hanyalah berapa yang **lulus**: untuk itu memang
harus menjalankan pytest, dan perintah di sebelahnya yang jadi kebenarannya.

**Angka "0 dilewati" itu sendiri sebuah koreksi.** Empat tes dulu melewati diri
sendiri dengan pesan `not present` — dokumen paten di
`Matematika Hijaiyyah/OFFICIAL_PATENT_RELEASE/`, folder yang sudah berganti nama
jadi `Buku Matematika Hijaiyyah/`. Berkasnya ada sepanjang waktu; yang tidak ada
adalah jalurnya. Sebuah instrumen hukum berhenti diperiksa karena sebuah
direktori diganti nama — persis kegagalan yang `test_authorship.py` ada untuk
mencegahnya. Kini jalurnya di-glob, bukan disebut, seperti `test_bab_satu.py`
sudah lakukan.

**Dan "0 dilewati" hanya benar di mesin yang memegang naskah dan
bitstream-nya.** Pada checkout bersih repositori ini — diukur di worktree
terpisah pada `0a910f0` — **0 gagal dan 23 dilewati**, dan setiap yang
dilewati disengaja: 9 membutuhkan PDF buku (`test_book_anchor.py`,
`test_bab_satu.py`, `test_bab_dua.py`), 13 membutuhkan `CERTIFICATE.json`
serta dokumen `OFFICIAL_PATENT_RELEASE/` (`test_authorship.py`) — keduanya
di `Buku Matematika Hijaiyyah/`, yang `.gitignore` tahan dari riwayat
publik — dan 1 membutuhkan bitstream yang sudah dibangun (`test_rack.py`),
karena berkas `.fs` adalah keluaran build, bukan isi repositori. Tak satu
pun menandakan cacat; yang berbeda hanya apa yang ada di disk.

Baris terakhir bukan hiasan. `test_every_clue_is_distinctive_enough_to_be_worth_having`
mengambil `os.urandom` lalu menuntut penanda tidak muncul di dalamnya — dua
penanda panjangnya 3 byte, jadi suite gagal kira-kira **1 dari 127 jalan**.
Berkas itu sendiri sudah menulis pelajarannya satu fungsi di atasnya. Sekarang
sifatnya diasersi secara aritmetika dan deraunya berbenih.

---

## Perangkat keras — simulasi

| | apa | perintah |
|---|---|---|
| ✅ | **334 asersi, 28 bench, 0 gagal** | `make -C rtl/tb all` |
| ✅ | ROM 28 huruf | `make -C rtl/tb sim_rom` |
| ✅ | Guard G1–G4, T1–T2 | `make -C rtl/tb sim_guard` |
| ✅ | Codex ALU | `make -C rtl/tb sim_codex_alu` |
| ✅ | HISAB, sapuan 28 huruf | `make -C rtl/tb sim_hisab` |
| ✅ | Integrasi top-level | `make -C rtl/tb sim_top` |
| ✅ | Unit trap, 6 penyebab | `make -C rtl/tb sim_trap` |
| ✅ | MMIO, timer, UART RX | `make -C rtl/tb sim_mmio sim_timer sim_uart_rx` |
| ✅ | **H-Kernel: tiga proses + daemon guard** | `make -C rtl/tb sim_kernel` |
| ✅ | **Shell: perintah masuk lewat UART, jawaban keluar lewat kernel** | `make -C rtl/tb sim_shell` |
| ✅ | **Bayangan redirect: di mana interupsi menyimpan `epc` = 0** | `make -C rtl/tb sim_redirect_shadow` |
| ✅ | **Jarak `STORE TRAP_EPC` sebelum `ERET`: nol pun benar** | `make -C rtl/tb sim_epc_eret` |
| ✅ | **FLAGS milik prosesnya, melewati preemption** | `make -C rtl/tb sim_flags_ctx` |
| ✅ | **`EMITS` mencetak `Hijaiyyah`, penutup menghentikan** | `make -C rtl/tb sim_emits` |
| ✅ | **HFS create → write → read → verify, di RAM** — persistensi masih terbuka, lihat [OFF.md](OFF.md) | `make -C rtl/tb sim_hfs_lifecycle` |
| ✅ | **SDIO 1-bit: init, baca, tulis, baca ulang, dan N_CC 8 clock** — model kartu memeriksa CRC7, menolak transfer sebelum CMD7, dan menjatuhkan perintah yang datang kepagian; disabotase gap 7 → merah | `make -C rtl/tb sim_sdio` |
| ✅ | **Kartu dicapai sebuah program, bukan kabel bench** — `sdio_write.hasm` jalan di pipeline dan menyentuh `0xFE0`–`0xFE4` lewat `LOAD`/`STORE`; kartu model menyimpan polanya, satu CMD17 dan satu CMD24 | `make -C rtl/tb sim_sdio_prog` |
| ✅ | **28 instruksi huruf** | `make -C rtl/tb sim_letters` |
| ✅ | **`CALL`/`RET`, sarang 8 tingkat** | `make -C rtl/tb sim_subroutine` |
| ✅ | **I/O lewat kernel, dua sisi** | `make -C rtl/tb sim_syscall_io` |
| ✅ | Wrapper papan | `make -C rtl/tb sim_board` |
| ✅ | Boot lewat kabel | `make -C rtl/tb sim_loader` |
| ✅ | **Cabang & interupsi bertabrakan** | `make -C rtl/tb sim_branch_trap_race` |
| ✅ | **HOS: heap, HFS guard-on-write, HAR** | `make -C rtl/tb sim_hos` |
| ✅ | NUI: penjumlahan embedding fisika (titik/garis/lengkung/theta/rho) | `make -C rtl/tb sim_nui_embedding` |
| ✅ | NUI: opcode huruf (L_JIM/L_KHA) dimuat lewat kabel loader, bukan disintesis langsung | `make -C rtl/tb sim_loader_nui` |
| ✅ | Video timing generator (hsync/vsync/de) cocok persis standar VESA 640x480@60Hz | `make -C rtl/tb sim_video_timing` |

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
  Direproduksi minimal di `tb_hcpu_hos.v` dan seluruh 18 bench tetap hijau
  sesudahnya.

---

## Perangkat keras — sintesis

| | apa | perintah |
|---|---|---|
| ✅ | **Bitstream HCPU, Tang Nano 20K: 75% LUT4, 116,44 MHz** | `make -C rtl/fpga/gowin bitstream` |
| ✅ | **Bitstream Ka'bah, Tang Nano 20K: 58% LUT4, 165,98 MHz** | `make -C rtl/fpga/gowin kabah_bitstream` |
| ✅ | **`CSET` (0x45) dijalankan di papan: `5 6 2 0`** | `make -C rtl/fpga/gowin bridge` lalu `make -C rtl/fpga/gowin send PORT=<port> PROG=../../programs/test_cset.hasm` |
| ✅ | **HFS baca mengembalikan H-Reg hidup di papan: `1 1 1 2 1`** | `make -C rtl/fpga/gowin send PORT=<port> PROG=../../programs/test_hfs.hasm` |
| ✅ | **Kartu MicroSD bertahan melewati mati daya: `1 1 1 10`** — SDIO 1-bit, LBA 1; lima checkpoint `10` → `1 1 0 10` → `1 1 1 1 10` → reset → mati daya ([PAPAN.md](PAPAN.md)) | `make -C rtl/fpga/gowin bridge` lalu `send PROG=../../programs/sdio_verify.hasm` |
| ✅ | **Blok codex (`CMOV` `CZERO` `CEQ` `CRHO` `CU` `CMOD4`) di papan: `8 0 0 1 1 0 1 5`** | `make -C rtl/fpga/gowin hdmi_bridge` lalu `make -C rtl/fpga/gowin send PORT=<port> PROG=../../programs/test_codex.hasm` |

**Kalimat ini dulu berbunyi "belum ada `openFPGALoader` yang benar-benar
dijalankan terhadap perangkat keras dalam sejarah repositori ini". Itu tidak
lagi benar sejak 10 September 2026.** Kedua bitstream dipanggang ke papan
fisik dan dijalankan: HCPU mencetak `112` lalu `CYCLES=00001B89` di kabel
serial — 7.049 siklus, byte-per-byte identik dengan `make sim` — dan Ka'bah
mengembalikan 2/2 frame, 400/400 byte cocok dengan `cube.py`. Kedua angka
Fmax di atas adalah pengukuran ulang **pasca** bring-up, bukan angka pra-papan
yang digantikannya (114,65 dan 117,91): keduanya naik karena penyerempak reset
berhenti menggerbangi level pin 87 (MODE1) yang ditahan rendah oleh papan.

**Angka HCPU diukur ulang dua kali pada 13 September.** Sesudah `pc_valid`
berhenti diikat tinggi: 115,66 → 120,31 MHz, 14.714 → 14.726 LUT4, DFF naik
**satu** — tepat satu bit keadaan. Lalu sesudah `TRAP_EPC` mendapat bypass yang
sama dengan `TRAP_MODE`: 120,31 → 114,50 MHz, 14.726 → 14.746 LUT4, DFF **tidak
bergerak** — ia mux, bukan register. Sebelumnya, 12
September setelah blok codex: 84,26 → 115,66 MHz, 14.231 → 14.714 LUT4, DFF
tidak bergerak sama sekali — keenam opcode tidak menambah state. Jalur kritis yang dilaporkan
nextpnr masih di dalam Execute: berangkat dari `ex_gpr_we`, lewat `codex_hvec`
dan `would_addr`, berakhir di `ex_gpr_result`. Kenaikan Fmax tidak dipisah
antara desain dan penempatan, dan run ini tidak mengklaimnya. Yang tidak
berubah: papan menjalankannya, dan clock papan 27 MHz. (Pengukuran 11
September, setelah `CSET`: 118,43 → 84,26 MHz, 14.005 → 14.231 LUT4.)
Apa yang benar-benar keluar dari papan dicatat di [PAPAN.md](PAPAN.md); yang
masih belum ada di [ROADMAP.md](ROADMAP.md).

---

## Matematika dan angka

| | apa | bukti |
|---|---|---|
| ✅ | 28 huruf kanonik dari PDF bersegel | `make verify` |
| ✅ | Closure monoid dibuktikan, bukan disampel | `tests/test_algebra/` |
| ✅ | Cakupan guard **93,1%**, dan itu langit-langitnya | `matematika-hijaiyyah/GUARD.md` |
| ✅ | Throughput **2,59 MB/s**, hambatan = deserialiser | `src/hijaiyyah/crypto/kabah.py` |
| ✅ | 82 dari 103 opcode di RTL, 21 sisanya dinamai | [OFF.md](OFF.md) |

---

## Belum hijau

Satu, dan itu dinamai supaya centang di atas berarti sesuatu.

| | apa | keadaan |
|---|---|---|
| ⬜ | `python3 rtl/scripts/lint_hcpu.py` | **0 error struktural** (dulu 1), sisa **76 peringatan** — keluar bukan-nol |

Error Verilator hilang justru karena `default:` ganda itu diperbaiki — jadi
lint yang selama ini merah sebenarnya sedang menunjuk cacat huruf, dan tak ada
yang membacanya. Peringatan yang tersisa soal bit yang tak terpakai.

Bitstream pindah dari baris ini ke bagian hijau di bawah: desain muat dan
terrout di Tang Nano 20K (**75% LUT4, 116,44 MHz**, diukur 14 September),
papan di-flash, dan UART membalas 23 byte yang cocok byte-per-byte dengan
simulasi.
Rekamannya di [PAPAN.md](PAPAN.md).

---

## Satu tarikan napas

```bash
make -C rtl/fpga/gowin tools     # 5/5 perkakas
make lint typecheck verify rom   # bersih
python3 -m pytest -q             # 4.961 lulus, 0 dilewati
make -C rtl/tb all               # 334 asersi, 28 bench, 0 gagal
make -C rtl/fpga/gowin bitstream # ← hijau di Tang Nano 20K
```
