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

## HCPU: 24 program

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
| `mem_protect` | 28 | halt, lapor siklus |
| `syscall` | 30 | halt, lapor siklus |
| `syscall_io` | 46 | `42` — dan `99` tidak pernah sampai ke kabel |
| `trap_timer` | 19 | halt, lapor siklus — trap menyala, ERET kembali |
| `user_mode` | 22 | halt, lapor siklus |
| `test_cset` | 17 | `5 6 2 0` |
| `test_hfs` | 373 | `1 1 1 2 1` |
| `test_codex` | 32 | `8 0 0 1 1 0 1 5` |

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

## Lima program trap/supervisor — nol byte jadi berjalan

**11 September 2026.** Kelimanya dulu mengembalikan **nol byte** sementara
lulus di testbench masing-masing. Butuh **dua** cacat berbeda untuk
menjalankannya, dan keduanya luput dari simulasi karena alasan struktural
yang sama: **di testbench program mulai di alamat 0 dan pencacah mulai di 0.**

**Cacat 1 — label tak direlokasi.** `send_program.py` merakit dengan basis 0,
lalu loader menulis program itu ke alamat 64. `MOVI R1, handler` karena itu
memasang vektor trap ke kata di dalam kode loader sendiri. Sekarang alat itu
merakit di `LOAD_BASE = 64`. Hanya **satu kata** yang bergeser pada
`trap_timer` — labelnya — dan alamat periferal tidak tersentuh; itu diperiksa
`test_relocation_moves_the_absolute_labels_and_nothing_else`.

**Cacat 2 — tenggat absolut pada pencacah bebas.** `trap_timer` memasang
`COMPARE = 12`. `hcpu_timer.v` adalah pencacah yang tak pernah berhenti,
dibandingkan dengan **kesamaan**, bukan `>=`. Saat program tiba lewat kabel,
pencacah sudah lewat empat puluh juta, jadi 12 baru cocok setelah pembungkusan
32-bit — **sekitar 157 detik pada 27 MHz**. Program sekarang membaca pencacah
lebih dulu dan membangun tenggat relatif terhadapnya.

Hasil di papan, setelah keduanya:

| program | byte | keluaran |
|---|---:|---|
| `mem_protect` | 19 | halt, lapor siklus |
| `syscall` | 19 | halt, lapor siklus |
| **`syscall_io`** | **3** | **`42` — dan `99` tidak pernah sampai ke kabel** |
| `trap_timer` | 19 | halt, lapor siklus — trap menyala, ERET kembali |
| `user_mode` | 19 | halt, lapor siklus |

`syscall_io` yang paling tajam: testbench-nya menuntut *"the wire must carry
42 and must never carry 99"*. Papan memberi `42` saja. Itu I/O yang dimediasi
kernel, terbukti di silikon — bukan "ada keluaran", melainkan **keluaran yang
benar dan yang salah tidak lolos.**

---

## CSET di papan — 11 September 2026

`CSET` (0x45) menutup separuh yang hilang dari `CGET`: ia menulis satu nilai
GPR ke dalam satu komponen H-Reg. Setelah jalur RTL-nya masuk, bitstream
loader dibangun ulang (`make bridge`) dan dinyalakan, lalu program dikirim
lewat kabel — papan direkonfigurasi sebagai reset di antara program, sama
seperti seluruh tabel di atas.

| program | kata | keluaran papan | interpreter |
|---|---:|---|---|
| `test_bsm` | 9 | `112` | `112` |
| `test_cset` | 17 | `5 6 2 0` | `5 6 2 0` |
| `test_hfs` | 373 | `1 1 1 2 1` | `1 1 1 2 1` |
| `e3_sweep28` | 113 | 28 nilai Θ̂ | identik `MASTER_TABLE` |

**Apa yang dibuktikan tiap baris.**

- `test_cset` menulis dua komponen ke `H2` berurutan, jadi yang kedua harus
  membaca hasil yang pertama lewat jalur forwarding dan bukan lewat register
  file — tulisannya masih dua tahap dari commit. Lalu keduanya dibaca kembali
  dan guard ditanya. Keluaran `0` di akhir bukan kegagalan: vektor yang
  komponen Khaṭṭ-nya 5 dan 6 sementara ringkasan A_K-nya masih 1 memang bukan
  hybit, dan G2 menolaknya. CSET bisa membangun vektor tak sah, dan guard yang
  mengatakannya — alasan yang sama kenapa `hos_fs_write` menjalankan `HGRD`
  sebelum menyimpan.
- `test_hfs` menulis Kaf ke berkas, menimpa `H0` dengan Haa, lalu membaca
  kembali: H\* (komponen 17) kembali **1** dan Θ̂ kembali **2** — keduanya
  hanya bisa datang dari delapan belas `CSET` di `hos_fs_read` — dan `HGRD`
  atas hasilnya lulus. Lapis 4 buku, baca dan tulis, di silikon.
- `e3_sweep28` dijalankan ulang justru karena RTL berubah: 28 nilai Θ̂ dari
  ROM tersegel masih identik dengan `MASTER_TABLE`, jadi opcode baru tidak
  menggeser jalur yang lama.

Angka `CYCLES` lewat kabel tetap tidak sebanding dengan yang dipanggang,
dengan sebab yang sama seperti di bagian atas halaman ini.

---

## Blok codex di papan — 12 September 2026

Enam opcode codex yang dinamai spesifikasi dan belum pernah dieksekusi apa pun:
`CMOV` (0x46), `CZERO` (0x47), `CEQ` (0x48), `CRHO` (0x4C), `CU` (0x4D),
`CMOD4` (0x4F). Slot yang membawanya ke papan adalah `hcpu_hdmi_top` dengan
loader dipanggang; papan direkonfigurasi sebagai reset di antara program.

| program | kata | keluaran papan | interpreter |
|---|---:|---|---|
| `test_codex` | 32 | `8 0 0 1 1 0 1 5` | `8 0 0 1 1 0 1 5` |
| `test_cset` | 17 | `5 6 2 0` | `5 6 2 0` |
| `test_hfs` | 373 | `1 1 1 2 1` | `1 1 1 2 1` |
| `e3_sweep28` | 113 | 28 nilai Θ̂ | identik `MASTER_TABLE` |

Slot HCPU biasa dijalankan di sesi yang sama, bitstream-nya sendiri:
**23 byte**, `112` — ‖BSM‖², angka yang sama yang dihitung testbench.

**Apa yang dibuktikan tiap kolom `test_codex`.** Haa dipilih karena ia huruf
paling tajam untuk tiga besaran turunan sekaligus: Θ̂ = 8 dan Qc = 2, jadi
`CU` = 4·2 = **8**, `CRHO` = Θ̂ − U = **0**, dan `CMOD4` = 8 mod 4 = **0**.
Lalu `CZERO` diuji lewat **sifatnya**, bukan lewat dirinya sendiri: `HCADD`
menambahkan hasilnya ke Haa dan `CEQ` menanyakan apakah jumlahnya masih Haa →
**1**. Bentuk pertama membandingkan dua register yang sama-sama di-`CZERO`, dan
itu buta: sabotase yang menaruh 1 di komponen 0 menulis vektor salah yang sama
dua kali dan tetap lulus. `HCADD` menyentuh delapan belas komponen dan `CEQ`
membandingkan seluruh 144 bit, jadi komponen tak-nol mana pun terlihat (R3). `CMOV` menyalin Haa dan `CEQ` atas
salinannya → **1**; `CEQ` antara Haa dan Ba → **0**. Dua kolom terakhir Waw,
Θ̂ = 5: `CMOD4` = **1** dan `CU` = **5** — Haa sendirian tidak bisa melihat
kesalahan mod-8, karena 8 mod 4 dan 8 mod 8 dua-duanya 0.

**`CDOT` (0x49) tidak ikut, dan penghalangnya diukur, bukan diduga.** RTL-nya
benar dan lulus bench; yang tidak muat adalah papannya. Empat belas pengali
8×8 membawa `hcpu_gowin_top` ke **16.015 LUT4 (77%)** dan nextpnr menjawab
*"Unable to find legal placement for all cells"* — dua kali, pesan sama, jadi
bukan variasi placer. Tanpa `CDOT`: **14.714 LUT4 (70%)**, ter-place dan
ter-route. Pemilik memutuskan mengeluarkannya; `CDOT` tetap berjalan di HVM
dan tercatat di [OFF.md](OFF.md) dengan penghalang bernama.

Angka `CYCLES` lewat kabel tetap tidak sebanding dengan yang dipanggang,
dengan sebab yang sama seperti di bagian atas halaman ini.

---

## M3 — shell menjawab kabel serial, 12 September 2026

Perintah masuk lewat UART, dilayani kernel, dan jawabannya keluar lewat kabel
yang sama. Slot `hcpu_hdmi_top` dengan loader dipanggang; `shell.hasm` (305 kata) dikirim lewat kabel, lalu diketik satu byte per perintah.

| diketik | keluar dari papan | apa yang dibuktikan |
|---|---|---|
| `A` | `65` | ASCII `A`. Byte menyeberang kabel ke register RX, **shell** memintanya lewat `SYSCALL` — ia tidak bisa menjangkau 0xFF0 sendiri, alamat itu di luar jendelanya — kernel membacanya lewat `hal_uart_rx_get`, mengembalikannya di blok proses, lalu shell meminta kernel mencetaknya |
| `p` | `2` `0` `1` | `ps`. Cacah **dibaca** dari kata yang kernel terbitkan ke jendela shell sendiri, lalu setiap pid di bawahnya |
| `0` | `48` | ASCII `0` — bukan angka nol; gemanya byte, bukan nilainya |
| `z` | `122` | ASCII `z` |

Rute itu satu-satunya yang ada, bukan sekadar yang dianjurkan: setiap alamat
periferal tinggal di `hal.hasm`, di dalam jendela yang ditolak untuk mode user.

```
shell → SYSCALL → kernel → HAL → UART
```

**Tabel syscall** ada di memori data pada 0xF08+n — 1 `write`, 2 `read`,
3 `yield`, 4 `exit` — satu kata per panggilan, dan tiap lengan membaca katanya
sendiri lebih dulu. Ia **tabel, bukan tabel lompat**: ISA ini tidak punya
lompatan terhitung, setiap sasaran di §6.2 adalah immediate. Menolkan satu kata
mematikan tepat satu panggilan.

### Mekanisme M3 lainnya, diukur ulang di papan hari ini

RTL berubah dua kali sejak 11 September (`CSET`, lalu blok codex), jadi semua
dijalankan ulang, bukan disalin dari catatan:

| program | keluaran papan | apa |
|---|---|---|
| `user_mode` | halt, lapor siklus | batas supervisor/user nyata |
| `mem_protect` | halt, lapor siklus | jendela memori ditegakkan |
| `syscall` | halt, lapor siklus | masuk dan kembali dari syscall |
| `syscall_io` | **`42` saja** | I/O dimediasi kernel; `99` tidak pernah sampai kabel |
| `trap_timer` | halt, lapor siklus | trap timer menyala, `ERET` kembali |
| `timer_poll` | halt, lapor siklus | timer terbaca dari program |
| `hal` | halt, lapor siklus | lapisan HAL merakit dan berjalan |
| `trap_resume` | **`84` `84`** | timer mengembalikan PC yang benar — di tenggat ini |
| `trap_flags` | **`0`** | FLAGS **tidak** selamat melewati trap |
| `trap_shadow` | **`0 0 88 89 88 0 0 88`** | delapan tenggat digeser satu siklus; loop di 88, **empat dikembalikan ke alamat 0** |

### Dua angka yang bukan kabar baik

`trap_flags` mencetak `0`, dan itu jawaban yang benar dari mesin ini: FLAGS
bukan bagian dari konteks proses dan tak ada instruksi yang bisa membacanya ke
register. `shell.hasm` menjaga disiplin yang satu-satunya mungkin — tiap `CMP`
diikuti langsung oleh cabang yang membacanya — dan itu hanya menutup trap yang
ia pilih sendiri, bukan timer.

Dan **proses yang diambil timer tidak pernah berjalan lagi**: pid 0 membeku,
seperti proses A di `kernel.hasm` yang membeku pada 337 sejak penjadwal
dibangun. Keduanya di [OFF.md](OFF.md) dengan angka dan tanda tangannya.

---

## Penghalang A ditutup di papan — 13 September 2026

Interupsi termaskable dulu menyimpan **alamat 0** sebagai tempat kembali
selama dua siklus yang dibayar sebuah redirect. `pc_valid` berhenti diikat
tinggi: `hcpu_fetch` sekarang berkata apakah PC yang ia sajikan nyata, dan unit
trap menunggu kalau tidak. Sebab lengkapnya di [OFF.md](OFF.md).

| program | sebelum | sesudah |
|---|---|---|
| `trap_shadow` | `0 0 88 89 88 0 0 88` | **`88 88 88 89 88 88 88 88 21`** |
| `trap_resume` | `84 84` — satu sampel, kebetulan di luar bayangan | **`86 86 27`** |

`trap_resume` yang menjadi buktinya, bukan `trap_shadow`: handler-nya **tidak
pernah menyentuh `TRAP_EPC`**, hanya mempersenjatai ulang timer. Jadi tempat
prosesnya melanjut adalah jawaban perangkat keras dan bukan yang lain. Delapan
preemption, tiap resume benar, dan pencacah prosesnya sampai **27** — sebuah
proses yang dilanjutkan di alamat salah akan menjalankan kode boot dalam mode
user, gagal pada simpanan periferal pertamanya, dan berhenti mencacah.

`trap_shadow` sengaja menaruh prosesnya kembali tiap sampel, karena ia mengukur
ke mana perangkat keras **menunjuk**; angka ke-sembilannya hanya berkata
loop-nya hidup.

### Yang tidak boleh rusak, dan tidak rusak

Semua dijalankan ulang di papan sesudah perubahan RTL:

| program | keluaran papan |
|---|---|
| `syscall_io` | **`42`** — `99` tetap tidak pernah sampai kabel |
| `shell` | `A`→`65`, `p`→`2 0 1`, `0`→`48`, `z`→`122` |
| `test_codex` | `8 0 0 1 1 0 1 5` |
| `test_cset` | `5 6 2 0` |
| `test_hfs` | `1 1 1 2 1` |
| `e3_sweep28` | 28 nilai Θ̂ identik `MASTER_TABLE` |
| `trap_flags` | `0` — FLAGS tetap bukan bagian konteks (penghalang tersendiri) |
| `mem_protect`, `user_mode`, `trap_timer`, `timer_poll`, `hal` | halt, lapor siklus |
| slot HCPU biasa | **23 byte**, `112` |

**Dan gate barunya tidak pernah menelan exception.** Diukur per program, jumlah
siklus di mana sebuah exception tertunda oleh `pc_valid`:

```
syscall_io 0   mem_protect 0   user_mode 0   shell 0
kernel 0       branch_trap_race 0            redirect_shadow 0
```

Yang tertahan hanya timer: 0, 0, 0, 1, 13, 3, 30. Itu memang maksudnya.

**Caveat yang diukur, bukan didiamkan:** sumber exception di mesin ini adalah
**pulse satu siklus**. Kalau suatu saat sebuah exception bersamaan dengan
`pc_valid == 0`, ia akan **hilang**, bukan tertunda. Pada cakupan di atas itu
tidak pernah terjadi; cakupan bukan bukti universal.

---

## Penghalang C ditutup di papan — 13 September 2026

`STORE` ke `TRAP_EPC` tepat sebelum `ERET` dulu kembali ke epc **lama**, jadi
handler yang ditulis ringkas mengulang instruksi yang menjebaknya — diam-diam.
Perbaikannya bentuk yang sudah ada untuk `TRAP_MODE` di berkas yang sama.

| program | keluaran papan | apa |
|---|---|---|
| `trap_epc` | **`1 1 1`** | tiga ronde pada jarak **0**, 1, dan 2 instruksi antara simpanan dan `ERET`; masing-masing masuk handler tepat sekali. Nol adalah ronde yang dulu berputar tanpa henti |

Seluruh papan diverifikasi ulang sesudahnya, dan tidak ada yang berubah:
`trap_resume` `86 86 27`, `trap_shadow` `88 88 88 89 88 88 88 88 21`,
`syscall_io` `42` saja, shell `A`→`65` `p`→`2 0 1` `0`→`48` `z`→`122`,
`test_codex` `8 0 0 1 1 0 1 5`, `test_cset` `5 6 2 0`, `test_hfs` `1 1 1 2 1`,
`e3_sweep28` 28 nilai Θ̂ identik `MASTER_TABLE`, `trap_flags` `0` — penghalang
FLAGS memang masih terbuka. `mem_protect`, `user_mode`, `trap_timer`,
`timer_poll` dan `hal` halt dan melapor siklus.

---

## Rack bitstream — slot berurutan

**11 September 2026.** "HCPU dan Ka'bah di satu chip" pernah diperlakukan
sebagai satu top level, diukur **105% — lewat 960 sel**, lalu dicatat sebagai
penghalang. Itu asumsi, bukan syarat: tidak ada yang menuntut keduanya
menempati fabric pada saat yang sama.

Rack tidak menuntut itu. Tiap slot satu bitstream, FPGA direkonfigurasi di
antaranya, jadi fabric dibelanjakan **berurutan**. Pertanyaan anggarannya
berubah bentuk:

```
  berdampingan   sum(slot)   harus muat serentak   14.804 + 12.061 + 15.332 = 203%
  berurutan      max(slot)   satu per satu                           15.332 =  73%
```

Dijalankan penuh di papan, berurutan, tanpa mencabut daya:

| # | slot | dimuat | hasil |
|---:|---|---|---|
| 1 | `hcpu_gowin_top` | SRAM, exit 0 | **23 byte** — `112`, lalu `CYCLES=…` |
| 2 | `hijaiyyah_kabah_gowin_top` | SRAM, exit 0 | **2/2 frame, 400/400 byte cocok `cube.py`** |
| 3 | `hcpu_hdmi_top` | SRAM, exit 0 | **23 byte** — `112`, layar 1280×720 menyala |

Tiga desain berbeda, fabric yang sama, dalam satu sesi. `112` di slot 1 dan
slot 3 adalah angka yang sama yang dihitung testbench.

**Pencacah siklus tidak sama antar-lari** (`02785D53`, `035BF689`) dan itu
benar: ia berjalan bebas sejak konfigurasi, bukan direset per program. Yang
harus cocok adalah hasilnya, dan hasilnya cocok.

Rekaman rack: [`rtl/scripts/rack.py`](../rtl/scripts/rack.py) — `python3
rtl/scripts/rack.py --detect`.

**Biaya HDMI kini terukur, dan ia slot terbesar.** Kolomnya sempat kosong —
`None`, bukan nol — dan selama itu rack mengutip **67%**: maksimum dari dua
slot yang punya angka, benar untuk keduanya dan salah untuk rack. Dibangun
ulang lewat target Makefile baru (`hdmi_bitstream`, loader dipanggang), hasil
pak-nya **identik byte-demi-byte** dengan bitstream yang menyala di papan, dan
di-flash lagi ia menjawab `test_bsm` lewat kabel: 23 byte, `112`.

```
  LUT4    15.332 / 20.736   73%
  DFF      4.600 / 15.552   29%
  BSRAM       17 /     46   36%
  IOB         15 /    384    3%
  Fmax     63,73 MHz (HCPU), 453,51 MHz (pixel)
```

Jalur video menambah 528 LUT4 di atas HCPU sendiri, jadi biaya rack **73%**,
bukan 71%. Kalau kolom itu diisi nol, 67% akan bertahan dan jalur video
tercatat gratis.

**Angka di blok ini diukur ulang 12 September setelah blok codex masuk**,
karena slot ini membawa seluruh HCPU: 14.713 → 15.126 LUT4, DFF tidak bergerak
sama sekali. Sesi rack tiga-slot di atas dijalankan dengan bitstream sebelum
`CSET` — yang waktu itu terukur 14.528 LUT4, Fmax 121,24 MHz (HCPU) dan
502,51 MHz (pixel) — dan hasil yang dilaporkan di tabel itu adalah hasil
bitstream tersebut. Slot HDMI versi ini **sudah di-flash dan dijalankan**:
lihat bagian blok codex di atas.

---

## Ka'bah lewat HDMI — dibangun pertama kali, dijalankan, dilihat

**11 September 2026.** `kabah_hdmi_top.v` belum pernah dibangun sampai hari ini,
dan ia masih membawa tahap keluaran TMDS yang rusak dari versi pertama
`hcpu_hdmi_top.v`. Setelah disamakan dengan pola yang terbukti, target baru
`make kabah_hdmi_bitstream` membangunnya untuk pertama kali:

```
  IOB       15 /    384    3%
  LUT4  12.142 / 20.736   58%
  DFF    2.035 / 15.552   13%
  BSRAM      0 /     46    0%
  Fmax  94,16 MHz (Ka'bah), 186,85 MHz (pixel) — pasca-perutean
```

Nol sel TLVDS, dan keempat sel IO TMDS bernama persis seperti yang
dikonstrain `kabah_hdmi.cst` — asumsi yang sebelumnya diwarisi, kini terbukti.

| Di papan | Hasil | Jenis bukti |
|---|---|---|
| Ka'bah lewat UART | **2/2 frame, 400/400 byte cocok `cube.py`** | instrumen |
| Monitor | **gambar 1280×720 muncul** | pengamatan pengguna |
| Tombol mode (S1, pin 88) | **warna bingkai berganti** | pengamatan pengguna |

Pin 88 (MODE0) ternyata bisa dipakai sebagai tombol — berbeda dengan pin 87
(MODE1), yang papan tahan rendah dan yang dulu mengunci reset.

Ka'bah sendirian terrout di 165,98 MHz; di sini, berbagi fabric dengan jalur
video, 94,16 MHz. Masih jauh di atas batas 12 MHz — itu harga nyata
tetangganya.

---

## Video

`hcpu_hdmi_top` menghasilkan 1280x720 lewat TMDS pada pasangan diferensial
pin 33–40, `pixel_clk` 502,51 MHz dan `u_hcpu.clk_27m` 121,24 MHz pasca
perutean — laporan timing bitstream yang berjalan hari ini, dibangun
ulang lewat `make hdmi_bitstream` dan identik byte-demi-byte dengan yang
di-flash. Satu bitstream membawa ketiganya sekaligus — video, loader, dan
HCPU — dibuktikan dengan mengirim `e3_sweep28` lewat kabel saat layar
menyala dan menerima 28 nilai yang sama.

---

## Tiga cacat yang hanya papan bisa temukan

Ketiganya lolos 36 testbench RTL — 20 lewat `make -C rtl/tb all`, sisanya dipanggil
langsung dari pytest — dan 4.949 tes Python. Simulasi bukan
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
| `python3 -m pytest -q` | 4.949 lulus, 0 dilewati, 0 gagal |
| `make -C rtl/tb all` | 25 testbench, 303 pemeriksaan, 0 gagal |

Rincian per testbench, dijumlah dari baris ringkasan tiap testbench: ROM 30,
Guard 34, Codex ALU 6, HISAB 124, `tb_hcpu_top` 15, NUI embedding 10, video
timing 8, H-Kernel 8, **shell 7**, syscall I/O 6, HOS 7, subrutin 4, huruf 3,
**bayangan redirect 7**, wrapper Gowin 2, dan tujuh testbench yang melapor
**epc→eret 10**, **flags-ctx 6**, **emits 4**, shell 12, satu pernyataan
lulus tunggal — 303, semuanya 0 FAIL. Lima yang baru: `tb_hcpu_shell` dan `tb_hcpu_trap_redirect_shadow` tujuh
pemeriksaan masing-masing, dan `tb_hcpu_trap_epc_eret` sepuluh.

> **Selisih tujuh dari angka 253 sebelumnya bukan tes baru.** `tb_hcpu_video_timing`
> menjaga delapan properti VESA — H_TOTAL, lebar dan posisi hsync, rentang `de`,
> x dan y maksimum, lebar vsync, dan satu `frame_tick` per frame — masing-masing
> menaikkan pencacah `errors` saat gagal. Yang tak pernah ada di sana adalah
> cacah yang **lulus**: ia mencetak `ALL PASS` tanpa angka, jadi setiap
> penjumlahan asersi memasukkannya sebagai satu, atau sebagai nol, tergantung
> cara menghitungnya — dan 253 memilih satu. Delapan properti itu dijaga
> sepanjang waktu; yang tidak ada hanyalah angkanya. Sekarang bench itu melapor
> `SEMUA LULUS (8 pemeriksaan)` seperti tujuh bench lain, sehingga totalnya
> berhenti bergantung pada cara pembacanya menebak.

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
> 4.949 lulus, 0 dilewati, 0 gagal — 24 tes lebih banyak yang benar-benar
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
>
> Suku itu kini **nol**, dan bukan karena penjaganya dicabut: `torch` dan
> `pymupdf` keduanya terpasang, jadi tidak satu pun berkas melewati dirinya
> saat impor dan `-rs` pada koleksi melaporkan nol skip-modul. Identitasnya
> tetap berlaku, sukunya saja yang sedang kosong — dan penjaganya tetap
> menghitungnya, supaya hari ketika salah satu paket itu hilang dari mesin
> tidak lagi tampak sebagai angka yang tiba-tiba tidak cocok tanpa sebab.

---

## Dua field yang menimpa metode tuple-nya sendiri

**11 September 2026.** `make typecheck` merah dengan enam error di
`src/hijaiyyah/receiver/`. Empat di antaranya anotasi yang tidak cocok dengan
badannya — `_all()` bertanda `-> str` sambil mengembalikan `list`,
`sorted(key=order.get)` yang bisa mengembalikan `None`, satu tuple yang
disempitkan `START_STATE` jadi lima elemen lalu ditulisi panjang bebas.
Diperbaiki di anotasinya, karena kodenya yang benar.

Dua sisanya cacat sungguhan, dan bentuknya sama persis:

| kelas | field | yang ditimpanya |
|---|---|---|
| `Anchor(NamedTuple)` | `index: int` | `tuple.index` |
| `BankRow(NamedTuple)` | `count` (properti) | `tuple.count` |

Sebuah `NamedTuple` **adalah** tuple. Field bernama `index` tidak menambah
atribut di sebelah `tuple.index` — ia **menggantikannya**. `anchor.index(x)`
berhenti mencari `x` dan mulai mengembalikan nomor sampel, apa pun yang
ditanyakan; `row.count(x)` mengembalikan jumlah huruf, bukan berapa kali `x`
muncul. Keduanya `int`, jadi pemanggilnya tidak meledak — ia hanya menjawab
pertanyaan yang berbeda dari yang diajukan.

Tidak ada yang tergigit karena tidak ada yang memanggil metode itu: tes hanya
membaca `.rung` dan `.residual_deg`, dan `BankRow.count` hanya dibaca sebagai
nilai. mypy yang menemukannya, bukan tes — persis jenis cacat yang lolos dari
setiap tes yang ada dan tetap benar-benar rusak. `index` jadi `sample`, dan
`count` jadi `n` — nama kolom yang memang sudah dipakai barisnya di
`render_bank`.

Angka di [CHECKLIST.md](CHECKLIST.md) untuk baris ini juga hanyut: "108
berkas" sementara mypy memeriksa **128**. Sekarang dijaga oleh
`test_the_quoted_mypy_file_count_is_what_mypy_actually_checks`, karena cacah
berkas yang menyusut diam-diam terbaca sama persis dengan lari yang bersih.
