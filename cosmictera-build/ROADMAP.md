# Peta jalan: Tang Nano 20K → HCPU fisik nyata → satu komputasi utuh

[README.md](README.md), [CHECKLIST.md](CHECKLIST.md), [ON.md](ON.md), dan
[OFF.md](OFF.md) mencatat apa yang **sudah** benar, hari ini, dengan bukti,
dan [PAPAN.md](PAPAN.md) mencatat apa yang benar-benar dijalankan di papan
fisik beserta keluarannya.
Berkas ini beda arah: ia menyusun apa yang **belum**, sebagai fase, supaya
jaraknya ke "satu komputasi utuh" — HCPU, Ka'bah, dan tumpukan tujuh lapis
di [cosmictera/RULES.md](../cosmictera/RULES.md#label-epistemik) — punya
langkah dan bukan cuma harapan.

Setiap fase membawa label epistemik proyek ini (VF/CC/DP/EH/AT, lihat
[RULES.md R2](../cosmictera/RULES.md)) untuk keadaannya **sekarang**, bukan
untuk tujuannya. Kalau labelnya AT, itu jujur: belum dikerjakan.

---

## Peta jalan berfase

### Fase 1 — SELESAI: Tang Nano 20K target HCPU yang nyata dan berulang

**Kenapa ini duluan, dan kenapa sudah beres.** Setiap fase sesudahnya butuh
papan yang bisa memuat HCPU. 20K secara rasio LUT4 bisa itu sudah diverifikasi
lewat perutean sungguhan, bukan cuma dihitung — dan sekarang bisa dijalankan
ulang dengan satu perintah.

**Yang sudah dikerjakan:**
1. `rtl/fpga/gowin/Makefile` diganti total ke
   `DEVICE=GW2AR-LV18QN88C8/I7`, `FAMILY=GW2A-18C`, `BOARD=tangnano20k` —
   satu-satunya papan target.
2. `rtl/fpga/gowin/hcpu_gowin.cst` ditulis ulang dengan pinout 20K yang
   diverifikasi terhadap skema resmi (clk=4, uart_txd=69, uart_rxd=70,
   btn_rst_n=87, led=15..20) — pola yang sama yang sudah dites untuk
   `hijaiyyah_kabah_gowin_top.v`.
3. `make -C rtl/fpga/gowin bitstream` dijalankan sampai selesai:
   `nextpnr-himbaechel` melapor perutean selesai, bukan cuma dihitung dari
   persentase LUT4 — **67% LUT4, 28% DFF, 36% BSRAM, Fmax 114,65 MHz, PASS**
   pada batas 12,00 MHz, dan `gowin_pack` keluar 0 menghasilkan bitstream
   7.261.470 byte.
4. Fingerprint RTL baru ditempel di header `hcpu_gowin_top.v`, dan
   `tests/test_integrity/test_place_and_route.py` ditulis ulang: bukan lagi
   menguji bahwa desainnya gagal dan Fmax tidak ada, tapi bahwa ia muat dan
   Fmax-nya seperti yang diukur.

**Cara memeriksa:** `make -C rtl/fpga/gowin bitstream` keluar 0;
`pytest tests/test_integrity/test_place_and_route.py` lulus (11/11).
Keduanya sudah dijalankan, bukan cuma direncanakan.

### Fase 2 — Nyalakan yang pertama: flash sungguhan, papan sungguhan

**Kenapa ini yang membuat "fisik" berarti fisik.** Fase 1 dan 3 menghasilkan
`.fs`. Berkas itu bukan bukti sampai UART papan sungguhan membacanya balik
dan cocok dengan simulasi. Papan sudah dipesan; berkas ini bagian yang bisa
disiapkan sebelum ia tiba, supaya hari ia sampai tidak dihabiskan menebak.

**Sudah disiapkan, menunggu papannya saja:**
- `hcpu_gowin_top.fs` dan `hijaiyyah_kabah_gowin_top.fs` — dua-duanya sudah
  dibangun dari sumber hari ini (Fase 1, 3), tinggal `make -C rtl/fpga/gowin
  flash` / `kabah_flash`.
- `rtl/scripts/kabah_uart_test.py` — Ka'bah tidak punya "program" seperti
  HCPU; alat ini yang mengirim 128 byte dan membandingkan 200 byte balasan
  dengan `cube.py`, bukan mata menatap dump heksadesimal. Sudah diverifikasi
  reproduksi persis vektor emas `tb_hijaiyyah_kabah_gowin_top.v`
  (`tests/test_integrity/test_kabah_folder.py`).
- `pyserial` — ditambahkan sebagai extra `board` di `pyproject.toml` dan
  sudah terpasang di environment ini; tanpa ini `send_program.py` dan
  `kabah_uart_test.py` menolak jalan ke port sungguhan (`pip install
  pyserial` kalau environment lain).
- LED sebagai pemeriksaan pertama, tanpa terminal sama sekali (lihat
  komentar di `hcpu_gowin.cst` — satu `.cst`, dua arti tergantung yang
  di-flash): HCPU → LED1 menyala saat halt, LED4 saat laporan siklus
  terkirim. Ka'bah → LED0/1/2 berkedip mengikuti absorb/permute/dump,
  LED5 menyala kalau framing UART pernah salah.

**Langkah hari papan tiba:**
1. `openFPGALoader --scan-usb` — pastikan papan terlihat sama sekali
   sebelum mencoba flash apa pun. Kalau tidak ada `/dev/cu.usbserial-*`
   yang muncul setelah dicolok, itu driver FTDI, bukan `openFPGALoader`
   atau bitstream-nya — pasang driver VCP FTDI resmi, coba lagi.
   FT2232 di papan ini biasanya muncul sebagai **dua** port serial (dua
   kanal chip); satu untuk pemrograman (dipakai `openFPGALoader` sendiri,
   bukan dibuka manual), satu untuk UART data — kalau port yang dicoba
   diam total, coba port sebelahnya.
2. `make -C rtl/fpga/gowin flash` — HCPU, program default `test_bsm.hasm`
   sudah terbakar di dalamnya sejak sintesis, tidak perlu jembatan loader
   untuk uji pertama ini.
3. Buka port UART di 115200 8N1 (`screen /dev/cu.usbserial-X 115200`,
   Ctrl-A K untuk keluar), tekan tombol reset (S1). Yang harus muncul,
   persis: `1`, baris baru, `1`, baris baru, `2`, baris baru (digit demi
   digit `PRINT`, `\n` polos tanpa CR), lalu `\r\nCYCLES=00001B89\r\n`
   (00001B89 heksa = 7.049 desimal — angka yang diverifikasi ulang sesi
   ini setelah perbaikan stall `PRINT` di `hcpu_controller.v`). LED1 dan
   LED4 menyala begitu ini selesai, bahkan tanpa terminal terbuka.
4. `make -C rtl/fpga/gowin kabah_flash`, lalu `python3 rtl/scripts/
   kabah_uart_test.py /dev/tty.usbserial-X` — mengirim `bytes(range(256))`
   sebagai dua frame berturut tanpa reset di antaranya, membandingkan
   400 byte balasan dengan `cube.py` sendiri, mencetak `PASS`/`FAIL` per
   frame. Ini uji "tanpa reset antar-blok benar-benar menyerap berantai",
   bukan cuma "wrapper membalas sesuatu."
5. `PROGRAM=rtl/programs/nui_embedding.hasm make -C rtl/fpga/gowin
   bitstream flash` — bangun ulang HCPU dengan program NUI alih-alih
   `test_bsm.hasm`, lalu baca `2\n2\n2\n6\n6\n` — konfirmasi fisik pertama
   untuk embedding fisika (titik/garis/lengkung/theta/rho) yang selama
   ini cuma tervalidasi di simulator.
6. Kalau baud, framing, atau isi menyimpang dari simulasi: itu bug wrapper
   nyata (persis seperti `tx_data` balapan `dump_idx` yang ditemukan
   `tb_hijaiyyah_kabah_gowin_top.v` — [kabah/SILICON.md](../kabah/SILICON.md)),
   bukan sesuatu yang bisa "diperbaiki" dengan menaikkan margin waktu.

**Cara memeriksa:** manusia membaca terminal serial (atau `kabah_uart_test.py`
membaca dan membandingkan sendiri untuk Ka'bah) dan mencocokkannya dengan
keluaran `vvp` — langkah ini secara definisi tidak bisa diotomatisasi penuh
sampai ada papan yang selalu terhubung ke CI, jadi ia dicatat manual di
berkas ini/`ON.md` dengan tanggal, sama seperti pengukuran Fmax lain di
proyek ini.

### Fase 3 — SELESAI: Ka'bah masuk ke alur build yang sama

**Kenapa ini sebelum digabung, dan kenapa sebagian sudah beres.** Angka
Ka'bah-di-20K (58%, 117,91 MHz — kini 165,98 MHz sesudah penyerempak reset diperbaiki) dulu nyata tapi tidak bisa dijalankan ulang
dengan satu perintah. R4 berlaku di sini juga: angka yang cuma bisa
direproduksi lewat command manual yang diingat, bukan Makefile, adalah
angka yang gampang basi diam-diam — dan sekarang tidak lagi begitu.

**Yang sudah dikerjakan:**
1. `rtl/fpga/gowin/Makefile` dapat target `kabah_synth`/`kabah_bitstream`/
   `kabah_flash`/`sim_kabah`, memakai `hcpu_gowin.cst` yang sama (port-nya
   identik: `clk_27m`, `btn_rst_n`, `uart_rxd`, `uart_txd`, `led[5:0]`) —
   tidak ada `.cst` kedua yang bisa menyimpang dari yang pertama (R1).
   Sumbernya ditulis eksplisit, bukan `$(wildcard hijaiyyah_*.v)`, karena
   family `hijaiyyah_*` punya anggota pensiun (`hijaiyyah_ramal_core.v`,
   `hijaiyyah_sbox_router.v`, `hijaiyyah_wave.v`) yang wildcard HCPU sendiri
   tidak punya padanannya.
2. `make -C rtl/fpga/gowin kabah_bitstream` dijalankan sampai selesai dengan
   sumber hari ini: **58% LUT4, 12% DFF, 0% BSRAM, Fmax 117,91 MHz PASS** — kini 165,98 MHz, diukur ulang 10 September sesudah penyerempak reset diperbaiki,
   bitstream 4.618.782 byte — angka yang sama persis dengan pengukuran
   4 September, sekarang terverifikasi ulang dan direproduksi, bukan
   diasumsikan tetap benar.
3. Fingerprint RTL ditambahkan ke `hijaiyyah_kabah_gowin_top.v`, dengan
   himpunan sumber sendiri (`KABAH_FINGERPRINTED` di
   `test_place_and_route.py`) — terpisah dari fingerprint HCPU, supaya
   menyentuh satu tidak memaksa yang lain diukur ulang tanpa alasan.
4. `sim_kabah` menemukan bug nyata sebelum lolos: testbench-nya
   `$readmemh` dua berkas `.hex` lewat jalur relatif-ke-root-repo
   (`rtl/tb/kabah_uart_want.hex`), yang cuma pernah dijalankan dari
   `test_place_and_route.py` dengan `cwd=ROOT` — target `make` ini berjalan
   dari `rtl/fpga/gowin/`, jadi jalurnya pecah sampai target itu sendiri
   pindah direktori ke root sebelum memanggil `vvp`.

**Yang belum:** tidak ada lagi di fase ini. Bitstream-nya di-flash dan
dijalankan 10 September: 2/2 frame, 400/400 byte cocok `cube.py`
([PAPAN.md](PAPAN.md)).

**Cara memeriksa:** `make -C rtl/fpga/gowin sim_kabah` dan `kabah_bitstream`
keluar 0; `pytest tests/test_integrity/test_place_and_route.py` lulus
(12/12, termasuk `test_the_kabah_wrapper_records_its_own_fingerprint`).
Keduanya sudah dijalankan.

### Fase 4 — HCPU dan Ka'bah sebagai satu chip, satu top level

**Terjawab — dan bukan dengan cara yang fase ini rancang.** Fase ini
mengandaikan HCPU dan Ka'bah harus menempati fabric bersamaan. Tidak harus:
papan memuatnya sebagai slot bitstream berurutan (`rtl/scripts/rack.py`),
jadi biayanya adalah slot terbesar — HDMI, 70% — bukan jumlah naif
67% + 58% = 125%. Ketiga slot sudah dijalankan berurutan dalam satu sesi
([PAPAN.md](PAPAN.md)). Pengukuran top level gabungan di bawah tetap nyata
dan tetap dicatat; ia berhenti menjadi penghalang.

**DIUKUR 10 September 2026 — dan ketiga penghematan yang pernah dinamai di
sini ternyata tidak ada isinya.** `rtl/fpga/gowin/hijaiyyah_cosmictera_gowin_top.v`
menanam kedua wrapper utuh (kasus terburuk: dua UART, dua penyerempak
reset) dan disintesis untuk GW2AR-18C:

```
LUT   21.696 / 20.736  = 105%     ← lewat 960 sel
DFF    6.404 / 15.552  =  41%
BSRAM     16 /     46  =  35%
```

105%, bukan 125%. Tapi yang penting bukan itu — melainkan ke mana LUT-nya
pergi. Rincian per modul:

```
10.198  47,0%  u_hcpu.u_execute
 9.517  43,9%  u_kabah.u_sponge
   898   4,1%  u_hcpu.u_decode
   355   1,6%  u_hcpu.u_mmio
    34   0,2%  u_hcpu.imem
```

**Dua modul adalah 91% desain.** Karena itu, masing-masing tebakan lama
diuji dan gugur, semuanya lewat sintesis nyata:

| Penghematan yang dinamai | Terukur menghemat |
|---|---|
| Kecilkan memori instruksi 4096 → 1024 | **15 sel** |
| Tulis ulang port tulis agar ter-infer SDP | **2 sel** (tetap dipetakan DP) |
| Berbagi satu UART, bukan dua | tidak masuk 14 besar; glue seluruh top level 104 sel |

Memori instruksi ada di BSRAM apa pun bentuknya, jadi mengecilkannya tidak
memindahkan LUT. Perbandingan "tanpa port tulis" yang sempat menunjukkan
72% **tidak sah** dan dicatat di sini supaya tidak diulang: tanpa port tulis
`imem` menjadi ROM konstan berisi 36 kata loader dan yosys mengompresinya ke
4 BSRAM — yang secara aritmetika tidak mungkin memuat 4096x32 bit — jadi
angka itu mencampur biaya port tulis dengan hilangnya kompresi.

**Yang tersisa, dan belum dikerjakan:** 960 sel harus keluar dari
`hcpu_execute` atau `hijaiyyah_sponge`. Tidak ada tempat lain yang cukup
besar. Itu pekerjaan pada inti komputasi, bukan pada perkakas di sekitarnya
— lebih berat daripada yang dibayangkan berkas ini sebelumnya, dan sekarang
diketahui sebelum ada yang menghabiskan waktu pada UART bersama.

**Langkah konkret:** satu wrapper baru (`hijaiyyah_cosmictera_gowin_top.v`
atau nama senada) yang menanamkan `hcpu_top` dan `hijaiyyah_kabah_top`
sebagai dua co-processor di bawah satu clock/reset/UART bersama, dengan
GPIO atau MMIO sebagai jalur HCPU memanggil Ka'bah — ini juga langkah
pertama yang membuat Ka'bah benar-benar "layanan Hybit" (lapis 5 di tabel
7-lapis) alih-alih dua sistem terpisah yang kebetulan berbagi repositori.

**Cara memeriksa:** PNR pertama yang benar-benar menyasar top level
gabungan. Kalau gagal, dibisect: LUT4 keluar berapa, apa yang paling
boros, urutan pengurangan mana yang dicoba lebih dulu.

### Fase 5 — Tutup celah yang membuat "komputasi" belum lengkap

Ini tidak menunggu Fase 1–4 selesai — bisa berjalan paralel, sebagian besar
di simulator dulu, karena celahnya di ISA dan kernel, bukan di sintesis.
Semua sudah bernama di [OFF.md](OFF.md), diringkas di sini sebagai daftar
kerja:

| Celah | Yang dibutuhkan | Menutup lapis |
|---|---|---|
| Penyimpanan persisten | ✅ **terbukti di papan 15 September 2026** — kartu TF, SDIO 1-bit, bertahan melewati reset dan mati daya ([PAPAN.md](PAPAN.md)). Sisa lapis 4: menyambungkan `hos_fs_*` ke sektor kartu, yang masih menulis ke RAM data ([OFF.md](OFF.md)) | 4 (HFS) |
| HISAB langsung, bukan `SYSCALL` | bungkus `HPACK`/`HCRC` sebagai layanan kernel bernama, seperti `hos_har_get` | 5 |
| 21 opcode (vektor, codex, `JGF`/`JGP`/`JNP`/`PRINTH`) | RTL + bench per opcode — empat di antaranya menunggu keputusan pemilik, lihat [OFF.md](OFF.md) | 6/7 (dipakai program lengkap) |
| Proses dinamis, stack per proses, tabel syscall, tidur/tunggu/sinyal | perluasan H-Kernel | 3 |

**Cara memeriksa:** setiap baris dapat bench-nya sendiri mengikuti pola
`tb_hcpu_hos.v`/`tb_hcpu_branch_trap_race.v` — sengaja merusak apa yang
dijaganya (R3), bukan cuma jalur normal.

### Fase 6 — Melampaui FPGA: silikon fisik yang didedikasikan

**Kenapa ini fase terpisah, bukan lanjutan Fase 1–4.** Tang Nano 20K adalah
chip *reconfigurable* off-the-shelf — proksi, bukan tujuan akhir kalau
"HCPU fisik nyata" dibaca harfiah sebagai chip yang *menjadi* HCPU. Jalur
ke sana kategoris berbeda: butuh pemetaan sel standar dan akses fab, bukan
`yosys`+`nextpnr` open-source yang sudah dipakai sejauh ini.

**Keadaan sekarang, dari [OFF.md](OFF.md#asic):** belum ada pemetaan sel
standar sama sekali. Sintesis gerbang generik memberi 384.840 sel — **70%
di antaranya `hcpu_dataram`**, 4096×32 yang tersintesis sebagai larik
register, bukan makro memori. Ini pola yang persis sama dengan yang sudah
terbukti di FPGA (jalur boot mengubah data RAM dari BSRAM ke register array
dan menggandakan LUT4 — [OFF.md](OFF.md#papan-9k-bukan-diperbaiki-diganti)):
larik register untuk memori besar mahal di **mana pun** ia disintesis,
bukan cuma di FPGA.

**Langkah konkret, berurutan:**
1. Pilih PDK (proses fab) — ini keputusan yang bukan milik saya untuk
   diambil: shuttle akademik/terbuka (mis. Skywater 130nm lewat efabless)
   atau proses komersial berbayar, tergantung anggaran dan tujuan (belajar
   vs produksi).
2. Sintesis ulang menyasar sel standar PDK itu, bukan gerbang generik —
   angka 384.840 sel akan berubah total begitu ini terjadi, dan sampai
   itu terjadi angka itu sendiri berlabel AT untuk tujuan tape-out.
3. Ganti `hcpu_dataram` jadi makro SRAM (biasanya disediakan PDK-nya) atau
   kecilkan sampai register array masuk akal — pertanyaan yang sama dengan
   Fase 4, dijawab untuk target yang berbeda.
4. DRC/LVS bersih di atas layout PDK itu.
5. Tape-out — run MPW (*multi-project wafer*) atau run khusus, tergantung
   pilihan di langkah 1.

**Cara memeriksa:** tidak ada `pytest` untuk fase ini — buktinya adalah
laporan DRC/LVS bersih, lalu chip yang kembali dari fab dan diuji dengan
tester fisik. Label seluruh fase ini **AT**, dan akan tetap AT sampai
langkah 1 benar-benar diputuskan.

### Fase 7 — "Satu komputasi utuh": definisi konkretnya

Bukan slogan — tabel 7-lapis di Bagian 1 adalah checklist-nya secara
harfiah. "Utuh" berarti setiap baris ✅, diukur di perangkat keras fisik
(Fase 2 atau Fase 6), bukan di simulator:

1. Perangkat keras: HCPU + Ka'bah satu chip (Fase 4 atau Fase 6), Fmax
   terukur, bukan "tidak sampai routing."
2. HAL: sudah ✅, tidak berubah oleh fase-fase di atas.
3. H-Kernel: proses dinamis, stack per proses, tabel syscall (Fase 5).
4. HFS: penyimpanan persisten terverifikasi fisik (Fase 5) — `CSET` sudah ada,
   jadi jalur bacanya mengembalikan H-Reg hidup.
5. Layanan Hybit: HISAB sebagai `SYSCALL`, bukan instruksi langsung
   (Fase 5) — dan Ka'bah bisa dipanggil dari sana (Fase 4).
6. HVM/HCPU: 103/103 opcode, bukan 82/103 (Fase 5).
7. Aplikasi: sudah ✅ — program HC berjalan di atas semua ini begitu
   lapis 1–6 berhenti jadi simulasi dan mulai jadi perangkat keras yang
   benar-benar dinyalakan.

---

## COSMICTERA COMPUTER M0 — target papan Tang Nano 20K

**Ditetapkan pemilik proyek, 12 September 2026.** Cakupannya dikecilkan dengan
sengaja: bukan "CosmicTera Computer penuh", melainkan **satu komputer CosmicTera
minimal yang benar-benar hidup di papan**. GUI penuh, NUI inference, jaringan,
penyimpanan besar dan jalur ASIC menunggu papan yang lebih besar — itu M1,
bukan M0.

Papan sudah membuktikan HCPU, Ka'bah, program trap, HDMI, rack/slot, `CGET` dan
`CSET` ([PAPAN.md](PAPAN.md)). Yang dituju sekarang adalah melengkapi rantainya
sampai menjadi satu sistem yang bisa dipakai:

```
             COSMICTERA COMPUTER v1
                    ON TANG NANO 20K
                           │
                    ┌──────▼──────┐
                    │    HCPU     │
                    │  H-ISA      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  H-KERNEL   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
         HFS             HISAB            KA'BAH
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────▼──────┐
                    │    HCVM*    │
                    │ reference   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ COSMICTERA  │
                    │   SHELL     │
                    └─────────────┘

* HCVM sebagai reference/verification,
  bukan berarti seluruh runtime Python masuk FPGA.
```

### Tangga milestone, berurutan

| # | Milestone | Keadaan hari ini | Yang kurang |
|---|---|---|---|
| M1 | HCPU + `CGET`/`CSET` | **selesai di papan** — `f0dd0f8`, keluaran `5 6 2 0` dan `1 1 1 2 1` | — |
| M2 | Batch ISA berikutnya | **selesai di papan** — enam opcode codex (`CMOV` `CZERO` `CEQ` `CRHO` `CU` `CMOD4`), `test_codex` menjawab `8 0 0 1 1 0 1 5` | — (`CSUB` ditunda, `CDOT` dikeluarkan karena tempat, `CNORM`/`CDIST` duplikat — lihat [OFF.md](OFF.md)) |
| M3 | H-Kernel boot → shell | **selesai di papan** — banner `HIJAIYYAH`, prompt `> `, gema karakter, perintah dijawab lewat kernel (`A`→`65`, `p`→`2 0 1`), tabel syscall, HAL UART, PID 0/PID 1 | — keempat penghalang ditutup dan terbukti di papan: resume setelah preemption (`e7b5a2d`), FLAGS sebagai konteks (H-ISA v1.1, `a3e2a15`), hazard `TRAP_EPC`→`ERET` (`346984d`), dan jalur keluaran karakter (`EMITS` 0xA2, `37cbbad`) |
| M4 | Proses + syscall + timer | trap, supervisor, proteksi memori, syscall, timer semuanya di RTL dan dijalankan di papan (`81fbd2e`) | proses dinamis, stack per proses, tabel syscall |
| M5 | HFS baca/tulis | **create → write → read → verify jalan di papan** (`1 0 1 1 1 1 0`), dan **medianya kini persisten**: kartu TF terbukti bertahan melewati mati daya, 15 September 2026 | `hos_fs_*` masih menulis ke RAM data — jalur kartu hidup, keduanya belum disambung |
| M6 | HISAB | `HPACK`/`HCRC` di RTL, 124 asersi | dibungkus jadi layanan kernel bernama, bukan instruksi langsung |
| M7 | Ka'bah dipanggil dari HCPU | Ka'bah jalan sendiri di papan, 400/400 byte cocok `cube.py` | jadi co-processor: perintah lewat MMIO, hasil kembali ke HCPU |
| M8 | JIM/HIJRAH di perangkat keras | 28 opcode huruf `0xE0`–`0xFB` dijalankan di pipeline | instruksi JIM yang dirakit, didekode, dieksekusi, lalu diverifikasi di papan |
| M9 | Program loader | loader UART menaruh program di alamat 64 | memuat program dari penyimpanan, bukan dari kabel |
| M10 | Konsol HDMI | 1280×720 menyala bersama HCPU dan loader | framebuffer + perender teks + layanan display di kernel |
| M11 | Jembatan NUI | `nui_embedding` jalan di papan, `2 2 2 6 6` | protokol PC→papan untuk data inferensi |
| M12 | **COSMICTERA COMPUTER M0** | — | seluruh rantai di atas dalam satu boot |

**Penomoran.** Pemilik membuka pekerjaan berikutnya dengan nama **"M4 — HFS +
System Services"**; di tangga ini HFS adalah baris **M5**. Dua penomoran itu
**tidak disatukan sepihak** — yang dikerjakan adalah isinya, dan nomornya
keputusan pemilik. Butir pertamanya, `create → write → read → verify` di papan,
sudah selesai (`b2a0595`); metadata, persistensi, lapisan layanan, dan
integrasi kernel ↔ filesystem **belum dibuka**.

**Diperbarui 17 September 2026.** Persistensi dan integrasi kernel ↔ filesystem
**kini dibuka** oleh gerbang enam tahap menuju KV260 — keputusannya tercatat di
`AGENTS.md` bagian 4, dan tidak diulang di sini. Metadata, direktori, dan izin
**tetap belum dibuka**.

Yang ditambahkan halaman ini adalah syarat terimanya, karena tahap hanya tutup
kalau ada yang bisa diukur:

| | Tahap | Tutup ketika |
|---|---|---|
| 1 | HFS ke kartu SD nyata | ✅ **tutup 18 September 2026** — berkas bertahan melewati mati daya dan dibaca kembali identik: `1 1 1` → kabel dicabut → `2` ([PAPAN.md](PAPAN.md)) |
| 2 | Loader program | ✅ **tutup 20 September 2026, opsi B pemilik** — boot dari kartu tanpa satu byte pun dari host (`1 2 3`, dua kali), loader membaca container dan menolak yang rusak (`1` / `0`), relokasi lintas sektor, dan shell 11 sektor naik dari kartu lalu menjawab kabel ([PAPAN.md](PAPAN.md)). Boot dari flash SPI tanpa JTAG dinilai pemilik sebagai **varian metode boot, bukan pembuktian baru** atas arsitektur loader |
| 3 | Overlay runtime | Dua program yang jumlah katanya melebihi 4.096 berjalan berurutan |
| 4 | HVM di papan | Bytecode yang sama memberi jawaban yang sama di HVM dan di perangkat keras |
| 5 | Semantic memory | Belum ditetapkan pemilik — tahap ini tidak dimulai sebelum syarat terimanya ada. Batasnya sudah (18 September 2026): memori atas operasi vektor codex, bukan arti huruf |
| 6 | TCP/IP lewat SLIP | Sebuah paket dijawab dari papan |

Tahap 2 syaratnya sengaja menyebut "tanpa host tersambung": `loader.hasm` hari
ini membaca `0xFF0` — RX_DATA — jadi sebuah program yang jalan dengan kabel
terpasang belum membuktikan apa pun tentang jalur kartu.

### Yang tidak boleh dikerjakan atas inisiatif sendiri

- Opcode yang **tidak ada di** `docs/HISA_SPEC.md` (`VPROJ_K/N/Q/T`, `HCHK`).
- Semantik perangkat keras yang belum ditetapkan pemilik spesifikasi — `CSUB`
  dan representasi hasil negatifnya.
- Encoding kedua untuk operasi yang sudah berjalan (`CNORM` vs `HNRM2`,
  `CDIST` vs `HDIST`, `CTHETA` vs `CGET` 0).
- Merapikan tabel spesifikasi sepihak; konflik dicatat, keputusan milik pemilik.

### Definisi selesai — tidak berubah

Bukan "kodenya sudah ada", bukan "testbench hijau", bukan "bitstream jadi".
**Program CosmicTera yang sama dibangun, disimulasikan, disintesis, diprogram ke
Tang Nano 20K, lalu mengeluarkan hasil yang benar di papan fisik** — tingkat 4
pada tangga bukti di `AGENTS.md`.

---

## Belum dikerjakan: buku dan sertifikat

Dicatat di sini karena sudah diputuskan tapi belum dikerjakan, dan hal yang
diputuskan-tapi-belum-dikerjakan adalah yang paling mudah dikira sudah beres.

### Struktur buku

| | Isi | Keadaan |
|---|---|---|
| **Edisi I** | BAB I + BAB II sebagai satu buku utuh | **AT** |
| **BAB III** | dirombak menyesuaikan hasil akhir Tang Nano 20K | **AT** |
| **Edisi II** | penuh Cosmictera/Hybit + seluruh hasil uji fisik | **AT** |

Penerbitnya Yayasan Akademi Hijaiyyah Indonesia untuk keduanya.

### `verification_summary` di CERTIFICATE.json masih angka lama

Konsekuensi langsung dari yang di atas: sertifikat paten belum disinkronkan
dengan hasil papan.

```
software_tests      1611/1611     ← sekarang 5.807
rtl_hardware_tests   174/174      ← lihat catatan di bawah
```

**Dan labelnya sendiri keliru, sejak sebelum ada papan.** Angka 174 itu asersi
**simulasi** RTL di Icarus Verilog, bukan uji perangkat keras. Sekarang hasil
perangkat keras yang sungguhan benar-benar ada — 23 byte UART cocok
byte-per-byte, 28 nilai Θ̂ identik dengan tabel kanonik, Ka'bah 400/400 byte,
keenam guard menangkap di silikon — sehingga satu label kini menutupi dua
hal yang berbeda. Sinkronisasinya harus memisahkan keduanya, bukan sekadar
mengganti angkanya.

Sertifikat itu ada di folder ter-gitignore, jadi perubahannya lokal dan tidak
pernah ter-commit; catatan ini yang membuatnya tidak terlupakan.

### Yang sudah beres di sertifikat

Segelnya. `master_table.sha256` dulu berisi `f85251e0…`, yang ternyata hash
artefak perkakas `MH-28-v.1.0-HC18D.hb` (`data/hm28_manifest.json` →
`artifacts.hb.hash`), bukan segel dataset kanonik `f82d3859…`. Sertifikat
paten menyegel **benda yang salah dengan label yang benar**, dan bertahan
lama justru karena keduanya hash sungguhan di repositori ini — tidak ada yang
tampak salah, dan tidak ada tes yang membaca keduanya berdampingan.
Sekarang dipatok ke konstanta yang sama dengan `NOTICE`, dijaga
`test_authorship.py`.

---

## Ringkasan

| Fase | Apa | Label sekarang | Bergantung pada |
|---|---|---|---|
| 1 | HCPU di-PNR sungguhan ke 20K, jadi target `make` | **CC — selesai**, `make bitstream` hijau, 68% LUT4, 84,26 MHz | tidak ada |
| 2 | Flash + baca UART papan fisik, pertama kalinya | **VF — selesai 10 Sep 2026**, 23 byte cocok byte-per-byte dengan simulasi, 7.049 siklus; 28 nilai Θ̂ identik dengan `MASTER_TABLE` | Fase 1 (selesai) |
| 3 | Ka'bah jadi target `make` yang direproduksi | **VF — selesai 10 Sep 2026**, 58% LUT4, 165,98 MHz, dan dijalankan di papan: 2/2 frame, 400/400 byte cocok `cube.py` | tidak ada, paralel ke 2 |
| 4 | HCPU + Ka'bah satu chip | **Dijawab rack** — slot berurutan, biaya 70%; top level gabungan **DP, diukur 105%**: lewat 960 sel, dan 91% desain ada di `hcpu_execute` + `hijaiyyah_sponge`; ketiga penghematan yang pernah dinamai terbukti kosong | Fase 1, 3 (keduanya selesai) |
| 5 | ISA lengkap, H-Kernel matang, HFS baca, HISAB sebagai layanan | AT, per-baris — sebagian bisa mulai sekarang di simulator | tidak ada, paralel |
| 6 | Silikon dedikasi (ASIC), ada tape-out | AT — pemetaan sel standar belum dimulai | keputusan PDK milik pengguna |
| 7 | Tujuh lapis ✅ di perangkat keras fisik | AT — definisi konkretnya di atas | 1, 3 (selesai), 2, 4–6 |

Baris-baris itu naik persis dengan cara yang seharusnya: bukti baru —
nextpnr menyasar 20K sungguhan, `gowin_pack` sungguhan, direproduksi lewat
`make`, lalu dijalankan di papan — bukan ditulis ulang begitu saja (R2).
Fase 1–3 selesai di papan. Fase 4 dijawab oleh rack, bukan oleh
penggabungan: top level gabungan diukur 105%, dan slot berurutan membuat
angka itu tak perlu dipenuhi. Fase 5–7 tetap AT. Yang sudah VF/CC
lainnya ada di [CHECKLIST.md](CHECKLIST.md), dan peta jalan ini berhenti
berguna kalau berhenti mengacu ke sana setiap kali sebuah fase selesai.
