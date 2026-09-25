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

## M4.1 — HFS: create → write → read → verify, 13 September 2026

Empat operasi sebuah sistem berkas, dalam satu riwayat hidup berkas, dibaca
dari kabel serial. `rtl/programs/hfs_lifecycle.hasm`:

| keluar | langkah | apa yang ditanyakan |
|---:|---|---|
| `1` | create | file 3 belum ada, dan sekarang ada |
| `0` | create | id yang sama ditolak — sebuah berkas dibuat **sekali** |
| `1` | write | vektor terjaga dikomit; `HGRD` jalan sebelum menyimpan |
| `1` | read | entri bilang ia ada, dan mengembalikan penunjuknya |
| `1` | verify | yang kembali **sama persis** dengan yang masuk, 144 bit |
| `1` | verify | dan masih lolos guardnya sendiri |
| `0` | read | file 5 tak pernah dibuat, dan ia mengatakannya |

**`create` kini operasi bernama.** Sebelumnya ia efek samping dari tulis
pertama — itu bekerja, dan menyembunyikan perbedaan yang justru menjadi dasar
sebuah sistem berkas: berkas yang **ada dan kosong** bukan berkas yang tak
pernah dibuat. Baris kedua tabel itu yang membuat perbedaannya bisa
dinyatakan. `size` tetap 0 sampai ada yang dikomit.

**`verify` bukan "read mengembalikan sesuatu".** Ia `CEQ` terhadap salinan
yang diambil **sebelum** tulis — delapan belas komponen termasuk H\*, yang
tidak diturunkan dari tujuh belas lainnya dan karena itu tak bisa kembali
benar karena kebetulan. H0 sengaja ditimpa Haa di antara tulis dan baca, jadi
baca yang diam-diam mengembalikan register alih-alih kata tersimpan akan
kembali sebagai Haa dan baris ini akan mengatakannya.

**Yang belum dibuktikan: persistensi.** HFS masih RAM data dari 0xE00 ke atas
dan hilang saat reset. Itu butir tersendiri di [OFF.md](OFF.md), tidak
dilipat ke sini.

### Satu blind spot yang terulang

Sabotase ketiga — menghapus `CSET` komponen 17 di jalur baca — mula-mula
**tidak menggigit**. Programnya menyimpan Lam dan menimpa dengan Haa, dan
keduanya H\* = 0: komponen yang dijatuhkan terakhir oleh rekonstruksi parsial
bernilai nol di kedua sisi, jadi perbandingannya tak bisa melihatnya. **Kaf
satu-satunya huruf di seluruh tabel yang H\*-nya 1**, jadi ia satu-satunya
pilihan yang membuat komponen kedelapan belas terlihat. Ini persis blind spot
yang `f0dd0f8` sudah catat, dan saya ulangi.

Dan `HLOAD 23` itu **Lam**, bukan Kaf: ROM 1-berindeks, Kaf ada di 22.

---

## M4.2 — jendela kartu di silikon, dan slot yang kosong, 14 September 2026

**Papan menjawab `0 0 0 196`, dua kali, dan itu jawaban yang benar.** Slotnya
memang kosong — dipastikan pemilik, bukan disimpulkan dari kabel.

`rtl/programs/sdio_verify.hasm` dikirim lewat loader ke bitstream H-ISA v1.2
(`make bridge`, lalu `send_program.py`). Programnya **tidak menulis apa pun ke
kartu**: tidak ada `SD_CMD` 3 di dalamnya. Empat angka keluar:

```
0     init    tak ada yang menjawab urutan identifikasi
0     read    ditolak: tak pernah ada init yang berhasil
0     verify  128 kata itu masih 7, angka pengotor yang ditulis sendiri
196   status  0b1100_0100 — err=1, card_ready=0, err_code=12 (E_NOT_INIT)
```

Dijalankan dua kali, yang kedua sesudah rekonfigurasi penuh papan: sama persis.
Dan **identik byte-per-byte dengan simulasi slot-kosong** (`tb_nocard`,
2.733.168 siklus ≈ 101 ms — satu timeout CMD8 penuh).

### Yang ini buktikan, dan tak ada bench yang bisa membuktikannya

| | |
|---|---|
| jendela peripheral v1.2 di silikon | `LOAD`/`STORE` ke `0xFE0`–`0xFE4` sampai ke blok kartu, dan `0xFF0`–`0xFFF` tidak terusik: UART tetap mencetak, pencacah siklus tetap jalan |
| pemisahan `is_core`/`is_sd` menahan | tulisan ke `SD_CONTROL` (`0xFE4`) membawa empat bit rendah **yang sama** dengan compare timer (`0xFF4`). Kalau pemisahan itu salah, memasang kartu akan diam-diam melengan ulang timer. Ia tidak |
| pengontrol melapor, bukan menggantung | timeout berjalan, kode galat keluar, mesin sampai ke `HALT` |
| jalur program utuh di papan | loader → relokasi ke alamat 64 → `CALL`/`RET` → gelung polling berbatas → `PRINT` |

### Yang ini TIDAK buktikan

Tidak ada satu bit pun lalu lintas kartu. **Pinout SDIO di `hcpu_gowin.cst`
masih klaim, bukan bukti** — ia diambil dari skema revisi 3921, dan komentarnya
sendiri mencatat bahwa revisi lebih lama memetakan pin ini berbeda. Selama
belum ada kartu yang menjawab, salah-pinout dan slot-kosong punya gejala yang
sama persis: diam.

Papan ini **tidak punya jalur card-detect** — itu sebabnya bit 3 dinamai
"kartu pernah menjawab", bukan "ada kartu". Perangkat lunak di sini tidak bisa,
dan tidak akan pernah bisa, membedakan slot kosong dari kartu yang gagal init.

### Catatan operasional yang mengubah bentuk langkah berikutnya

- **Satu program per konfigurasi.** Program berakhir `HALT`, jadi loader habis
  dan kiriman kedua tidak dijawab siapa pun. Diukur: kiriman kedua mengembalikan
  0 byte. Mengulang butuh rekonfigurasi atau tombol reset.
- **Bitstream ini dimuat ke SRAM, bukan flash papan.** Ia hilang saat daya
  dicabut. Langkah "power off → power on → verify" karena itu butuh bitstream
  ditulis ke flash SPI papan, atau dimuat ulang sesudah menyala — yang diuji
  tetap kartunya, bukan papannya.

---

## M4.2 — kartu menjawab, dan menyimpan, 15 September 2026

**Kartu: MicroSD 4 GB, SDHC, terformat FAT32, terbukti sehat di komputer
(keterangan pemilik). SDIO 1-bit. Sektor mentah LBA 1.**

Lima checkpoint, berurutan, tiap satu didahului rekonfigurasi FPGA penuh:

| # | program | keluaran papan | yang dibuktikan |
|---|---|---|---|
| 1 | `sdio_probe.hasm` | **`10`** | CMD0→CMD8→ACMD41→CMD2→CMD3→CMD7→CMD16 lengkap; kartu menjawab |
| 2 | `sdio_verify.hasm` | **`1 1 0 10`** | sektor 1 terbaca lewat DAT0, CRC16 lolos; polanya belum ada — kartu perawan |
| 3 | `sdio_write.hasm` | **`1 1 1 1 10`** | CMD24, kartu menerima blok, status CRC `010`, lalu baca ulang cocok |
| 4 | `sdio_verify.hasm` | **`1 1 1 10`** ×2 | bertahan melewati reset CPU/FPGA, daya kartu tak putus |
| 5 | `sdio_verify.hasm` | **`1 1 1 10`** | **bertahan melewati daya dicabut** |

`10` = `0b1010`: ok, card_ready, err 0, `err_code` 0 (§15.4).

### Kenapa checkpoint 5 bukan cache kartu

Kartu SD punya buffer sendiri dan tidak wajib mengosongkannya ke NAND sampai
catunya putus, jadi checkpoint 4 — sekuat apa pun — tidak bisa memisahkan
"tersimpan" dari "masih menumpang di cache". Yang memisahkannya dua hal, dan
keduanya terukur:

- **Papan menyala sebagai SoC LiteX pabrikannya** sebelum disentuh — Memtest,
  banner, prompt `litex>` di port serial. Bitstream kita ada di SRAM, dan SRAM
  hanya hilang kalau 3,3 V benar-benar putus, termasuk ke slot kartu. Itu bukti
  independen bahwa daya memang dicabut, bukan papan direkonfigurasi.
- **`sdio_verify.hasm` tidak punya `SD_CMD` 3 sama sekali**, dan ia menimpa
  seluruh 128 kata buffer dengan nilai 7 sebelum mengirim CMD17. Buffer itu
  BSRAM: reset membersihkan mesin keadaan, bukan larik memori, jadi tanpa
  pengotoran itu sebuah READ yang diam-diam tidak melakukan apa pun akan
  mengembalikan bacaan boot sebelumnya dan lolos. Dengan pengotoran itu, `1`
  pada angka ketiga hanya bisa datang dari kartu.

### Akar masalahnya: N_CC, dan papan yang menemukannya

Sebelum perbaikan, kartu SDHC sehat yang sama menjawab **`0 0 0 196`** —
`err_code` 12, timeout CMD8 penuh 100 ms — **empat kali**, dan itu identik
dengan jawaban slot kosong. Pinout dan pull-up sempat jadi tersangka; keduanya
dicoret pemilik lewat skema resmi 3921 (pin 83/82/84 benar, pull-up 10 kΩ
eksternal ada).

Yang salah ada di `rtl/hcpu_sdio.v`: **jarak antar-perintah nol clock, di mana
standar menuntut delapan.** Komentar kodenya sendiri menjanjikan *"give the
card its eight idle clocks"* dan kodenya tidak melakukannya.

Pengukuran pertama menyesatkan dan dicatat di sini supaya tidak diulang: ia
menghitung dari awal frame ke awal frame, sehingga 48 bit balasan kartu ikut
terhitung sebagai jeda, dan menyimpulkan hanya CMD0→CMD8 yang melanggar.
Dihitung benar — clock di mana tak ada yang menggerakkan jalur — **jaraknya nol
di setiap batas**; model kartu menolak CMD55 pada gap 0 begitu ia diajari peduli.

`S_CMD_GAP` karena itu dilewati **setiap** perintah, bukan hanya CMD8:

```
gap CMD0 → CMD8     0 clock  →  8 clock
perintah ditolak    1        →  0
```

Harganya **+1 LUT4 dan +9 DFF** (15.600→15.601, 5.056→5.065): pencacah delapan
bit dan satu keadaan. Fmax 116,44→116,35 MHz, derau penempatan.

`rtl/tb/sd_card_model.v` berhenti menjadi model yang memaafkan: ia menegakkan
N_CC ≥ 8 dan menjatuhkan perintah yang datang kepagian, seperti kartu sungguhan.
Disabotase pada gap 7 — kartu menolak, bench merah, 12 gagal (R3).

**Kenapa simulasi tidak pernah menangkapnya:** model kartunya menulis sendiri
di kepalanya *"Not a timing model"*. Dua belas pemeriksaan hijau, dan kartu di
papan diam seratus milidetik. Ini butir kedua di repo ini yang penghalangnya
hanya bisa ditemukan papan — yang pertama `abe9300`, opcode huruf yang tak
pernah dijalankan perangkat keras.

---

## M5.3a — node display berdiri sendiri, 15 September 2026

Dua kali dashboard ditaruh di penempatan yang sama dengan CPU, dan dua kali
nextpnr menolaknya: 16.882 LUT4 untuk RAM + painter, 16.849 untuk ROM +
compositor, melawan kontrol 15.933 yang terrout bersih. Sintesis diferensial
sudah mengukur seluruh tumpukan display di 571 LUT terhadap celah 916 pasca
perutean — yang harus dibuang lebih besar daripada seluruh yang ada untuk
dibuang. Jadi display berhenti berbagi die dengan CPU.

| | Terukur |
|---|---|
| `cosmictera_display_top` | **685 LUT4 / 20.736 — 3%** |
| Fmax `pixel_clk` | **102,44 MHz** (butuh 74,25) |
| Pelanggaran | **0 hold, 0 setup** |
| Flash | SRAM, exit 0 |

**Dari 16.849 yang ditolak ke 685 yang ter-place.** Bukan dashboard-nya yang
dikecilkan — yang berubah adalah pertanyaannya, dari "muat di sisa fabric CPU"
jadi "berdiri sendiri". Ini contoh terukur pertama dari memecah sistem jadi
node-node mandiri di repo ini, dan angkanya yang membuatnya argumen dan bukan
selera.

| Di papan | Hasil | Jenis bukti |
|---|---|---|
| Monitor | **mengunci 1280×720** | pengamatan pengguna |
| Teks | **terbaca, di sel yang benar** | pengamatan pengguna |
| Pixel latar | **garis vertikal rapat, berkedip** | pengamatan pengguna |

Baris ketiga adalah alasan node ini **tidak** dihitung selesai. Video timing,
renderer, font ROM, dan page key terbukti benar oleh fakta bahwa kata-katanya
terbaca sama sekali — tidak ada cara menggambar `READY` tanpa keempatnya. Yang
tidak terbukti adalah bahwa pipeline pixel menghasilkan gambar bersih.

Dan itu **tidak diperbaiki**. Investigasinya dibekukan atas keputusan pemilik
pada 17 September 2026 setelah puluhan eksperimen satu-variabel gagal menamai
akarnya; delapan penyebab tereliminasi dengan angkanya, dan petunjuk terkuat
yang tersisa — 30 muatan bitstream bit-identik yang menghasilkan gambar
berbeda-beda — dicatat utuh di [OFF.md](OFF.md). Yang dibekukan penyelidikannya,
bukan faktanya.

Setiap field yang perangkat kerasnya tidak laporkan berbunyi `NOT INSTRUMENTED`
di layar, bukan angka: node ini tidak punya CPU untuk ditanyai, `snap_valid`
diikat rendah, dan `hcpu_compositor.v` mengubah keenam field hidup jadi
`NOT INSTRUMENTED` ketika ia rendah. Node display yang mencetak PC sebagai
`0X000` akan mencetak nilai yang tidak ada apa-apanya di belakangnya.

---

## Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026

**Empat lari, satu papan, satu kartu.** Slot CPU adalah `hcpu_gowin_top` hasil
pemisahan `e4c251e`, dibangun ulang dari sumber hari ini; citra yang dipanggang
untuk tiga lari terakhir adalah **berkas yang sama** yang dijalankan
`rtl/tb/tb_hcpu_hfs_persist.v`, `rtl/tb/shell_persist.hex`, disalin bukan
dirakit ulang.

| # | citra | daya | keluaran papan |
|---:|---|---|---|
| 1 | `test_bsm` | — | **23 byte** — `112`, lalu `CYCLES=00001B89` |
| 2 | `shell_persist` | — | **18 byte** — `HIJAIYYAH`, `> `, lalu **`1 1 1`** |
| 3 | `shell_persist` | rekonfigurasi FPGA penuh | **14 byte** — `HIJAIYYAH`, **`2`**, `> ` |
| 4 | `shell_persist` | **kabel dicabut, lalu dicolok** | **14 byte** — `HIJAIYYAH`, **`2`**, `> ` |

**Apa yang dibuktikan tiap lari.**

- **Lari 1 menutup lubang yang bukan HFS.** Slot hasil pemisahan belum pernah
  dijalankan di papan; sembilan kata dengan jawaban yang sudah diketahui
  dijalankan lebih dulu, supaya papan yang diam tidak salah menuduh HFS.
  `CYCLES=00001B89` = 7.049, angka yang sama dengan yang tercatat sejak hari
  papan tiba.
- **Lari 2 adalah CREATE dan WRITE yang sampai ke kartu.** `1 1 1` berarti
  berkas 0 belum ada, lalu HFS_CREATE dan HFS_WRITE keduanya mengembalikan 1 —
  dan kontraknya menuntut RAM **dan** kartu sama-sama berhasil, jadi satu nol di
  antara ketiganya sudah cukup untuk menyatakan kartu menolak. Ketiganya lewat
  `SYSCALL` dari mode pengguna: **HFS lewat kernel juga baru terbukti di papan
  di sini**, bukan hanya di simulasi.
- **Lari 3 belum cukup, dan sengaja dijalankan.** Rekonfigurasi FPGA penuh
  membersihkan seluruh RAM data — `hcpu_dataram.v` memuat isinya dari bitstream
  — jadi `2` hanya bisa datang dari kartu. Tetapi kartu punya cache sendiri dan
  tidak wajib menulis ke NAND sampai catunya putus, jadi lari ini memisahkan
  "dari kartu" dari "dari RAM", bukan "tersimpan" dari "masih di cache".
  Bentuk yang sama dengan M4.2 checkpoint 4.
- **Lari 4 yang menutup tahap 1.** Kabel USB dicabut pemilik, ditunggu, lalu
  dicolok kembali; rekamannya berisi banner **LiteX pabrikan** — Memtest, SDRAM,
  prompt `litex>` — sebelum bitstream kita dimuat. Bitstream kita ada di SRAM
  dan SRAM hanya hilang kalau 3,3 V benar-benar putus, termasuk ke slot kartu,
  jadi banner itu bukti independen bahwa daya memang dicabut. Sesudah itu papan
  menjawab **`2`**: berkas 0 ada, dan `CEQ` atas delapan belas komponennya
  melawan Kaf mengembalikan sama. **Kaf satu-satunya huruf yang H\*-nya 1**,
  jadi komponen yang paling mudah tertinggal nol pun ikut diperiksa.

**Apa yang TIDAK dibuktikan.** Tidak ada berkas kedua, tidak ada berkas yang
lebih besar dari satu vektor, tidak ada metadata, direktori, atau izin — dan
ketiganya memang belum dibuka pemilik. Tabel berkas di kartu menampung delapan
entri; yang dijalankan di papan satu.

**Tiga program lama dijalankan lagi di slot yang sama, dan jawabannya tidak
bergerak.** Slot hasil pemisahan sampai di sini baru dibuktikan oleh `test_bsm`
dan HFS; pemilik meminta tiga yang lain diulang sebelum tahap 2 dimulai. Slot
`hcpu_gowin_top` dengan `loader.hasm` dipanggang (Fmax 79,23 MHz pada build
ini), program dikirim lewat kabel, papan direkonfigurasi di antara program:

| program | kata | keluaran papan | catatan sebelumnya |
|---|---:|---|---|
| `test_codex` | 32 | `8 0 0 1 1 0 1 5` | sama |
| `test_cset` | 17 | `5 6 2 0` | sama |
| `test_hfs` | 373 | `1 1 1 2 1` | sama |

Ketiganya dulu dijalankan di slot `hcpu_hdmi_top` dengan loader; kali ini di
slot CPU hasil pemisahan. Jadi yang berubah antara dua rekaman itu adalah
slotnya, dan angkanya tidak. `CYCLES` tetap tidak sebanding antar-lari, dengan
sebab yang sama seperti di atas.

**Urutan `1 1 1` dan `2` di kabel berbeda tempat**, dan itu penjadwalan, bukan
cacat: di lari 2 banner dan prompt shell keluar lebih dulu (`HIJAIYYAH`, `> `,
lalu angka), di lari 3 dan 4 angka pid 0 menyelip di antara banner dan prompt.
Kedua urutan terbaca sama oleh bench, yang membaca digit saja.

---

## Tahap 2A — loader membaca kartu di silikon, 18 September 2026

**Enam lari, satu papan, satu kartu, dan kontrolnya ikut dijalankan.** Slot CPU
dengan `loader.hasm` dipanggang; `sd_writer.hasm` dan `test_prog_load.hasm`
dikirim lewat kabel, papan direkonfigurasi di antara tiap lari.

| # | program | yang ada di kartu | keluaran papan |
|---:|---|---|---|
| 1 | `sd_writer` | menulis container `subroutine` @0x900 | **`1 1`** — ditulis, satu sektor |
| 2 | `test_prog_load` | container itu | **`1`** |
| 3 | `sd_writer` | menulis container yang **satu katanya dirusak** | **`1 1`** |
| 4 | `test_prog_load` | container rusak itu | **`0`** |
| 5 | `sd_writer` | menulis container yang benar lagi | **`1 1`** |
| 6 | `test_prog_load` | container benar | **`1`** |

**Lari 4 adalah alasan lari 2 dan 6 berarti apa-apa.** Angka `1` yang tidak
pernah bisa menjadi `0` tidak membuktikan apa pun. Kata keempat program di
dalam container diganti `DEADBEEF` di host, ditulis ke kartu yang sama lewat
papan, dan jumlah 32-bit menolaknya: papan menjawab `0`, dan **tidak satu kata
pun masuk ke memori instruksi**, karena checksum diperiksa sebelum tulis
pertama.

**Yang ini buktikan:** tabel program di sektor 16 dibaca dari kartu nyata,
container di sektor 17 dibaca, `MAGIC` `HPG1`, `VERSION`, `WORDS`, `ENTRY`,
`RELOC_CNT` dan jumlah 32-bit diperiksa di silikon, tabel relokasi disalin ke
0x300–0x37F, dan kata-kata ditulis lewat `IMEM_ADDR`/`IMEM_DATA` tanpa satu pun
penolakan.

**Yang ini TIDAK buktikan, dan pemilik menetapkan batas klaimnya sendiri:**
bahwa isi memori instruksi benar. Memori instruksi tidak punya port baca, jadi
`1` berarti loader selesai tanpa menolak — bukan bahwa bitnya mendarat benar.
Buktinya menuntut program yang dimuat **berjalan** dan berbicara sendiri, dan
itu tahap 2B, yang belum dibuka.

**Satu batas yang hanya papan ini temukan, dan diukur di sini.** Container
empat sektor (437 kata, `test_hfs` @0x200) membuat papan **diam total**: tidak ada satu pun
byte keluar. `sd_writer.hasm` membaca kabel byte demi byte, dan register RX
menampung satu byte — saat ia sedang menulis satu sektor ke kartu, byte yang
datang hilang, lalu ia menunggu selamanya byte yang tidak akan pernah ada.
Container satu sektor tidak pernah menyentuh batas itu karena tulisannya
terjadi sesudah byte terakhir. Dicatat di [OFF.md](OFF.md) dengan penghalang
bernama; kendali alirnya keputusan pemilik.

---

## 2B kecil — program dari kartu berjalan sendiri, 18 September 2026

**Papan mencetak `1 2 3`, dan angka itu hanya bisa datang dari kartu.**

| # | yang ada di kartu | keluaran papan |
|---:|---|---|
| 1 | container `test_from_card` @0x900 ditulis | **`1 1`** |
| 2 | program itu dimuat lalu **dijalankan** | **`1 2 3`** |
| 3 | container yang satu katanya dirusak ditulis | **`1 1`** |
| 4 | dimuat | **`0`** — ditolak, tidak dijalankan |
| 5 | container benar ditulis lagi | **`1 1`** |
| 6 | dimuat lalu dijalankan | **`1 2 3`** |

**Kenapa `1 2 3` membuktikan lebih dari `1`.** Tahap 2A hanya bisa berkata
loader selesai tanpa menolak; memori instruksi tidak punya port baca, jadi
isinya tak bisa diperiksa dari papan. Di sini isinya **berbicara sendiri**:
`test_from_card.hasm` menutup gelungnya dengan `JMP`, satu-satunya lompatan
yang membawa alamat **absolut** di ISA ini — cabang bersyarat ternyata relatif,
`JNE` merakit jadi `0x24000FFD`, offset −3, dan tidak perlu relokasi sama
sekali. Dibangun untuk 0x900, `JMP` itu membawa 0x901; dimuat tanpa relokasi ia
membawa 0x001 dan mendarat di tempat lain. Terukur di simulasi: sabotase yang
menghapus penambahan relokasi mengubah kabel dari `123` jadi `111`.

**Penyerahannya bukan mekanisme baru.** `TRAP_EPC` ditulis, `TRAP_MODE` bit 1
dipasang, lalu `ERET` — bentuk yang sama yang `loader.hasm` pakai sejak papan
ini pertama jadi jembatan, karena ISA ini memang tidak punya lompatan lewat
register.

**Lalu pemuatnya dipanggang, dan host berhenti mengirim apa pun.**
`test_prog_run.hasm` dirakit di alamat 0 dan dipanggang ke bitstream slot CPU
(15.744 LUT4, 86,18 MHz — angka header yang sama). Pembaca serial dibuka,
bitstream dimuat, dan **tidak satu byte pun dikirim host**:

| lari | keluaran papan | siklus konfigurasi → halt |
|---:|---|---|
| 1 | **`1 2 3`** | `0008D6B7` = 579.255 ≈ 21,5 ms |
| 2 | **`1 2 3`** | `0008D6A1` = 579.233 |

Angka `1 2 3` hanya bisa datang dari kartu: program yang dipanggang sendiri
hanya bisa mencetak `0`, lewat jalur penolakannya. Selisih 22 siklus antara dua
lari adalah waktu kartu, bukan desain.

**Dan inilah batas yang masih tersisa, dinyatakan persis.** Bitstream tetap
dimuat host lewat JTAG ke SRAM FPGA — yang hilang saat daya dicabut, sehingga
papan menyala sebagai SoC LiteX pabrikannya. Syarat tahap 2 secara harfiah,
*"tanpa host tersambung"*, menuntut bitstream ini tinggal di **flash SPI**
papan sehingga daya saja cukup untuk memulainya. Menulis flash itu **menimpa
citra LiteX pabrikan**, dan itu keputusan pemilik, bukan agent.

**Satu batas ABI yang ikut terlihat.** `ENTRY` ditulis oleh program uji, bukan
dikembalikan loader: `hos_prog_load` menjawab 1 atau 0, sementara di mana
program mulai hanya ada di header yang ia baca. Sebuah uji boleh tahu apa yang
host bangun; kernel yang melayani `SYSCALL` 9 tidak bisa menebaknya.
Mengembalikan `ENTRY` lewat ABI adalah keputusan pemilik.

---

## Lintas sektor dan ACK — shell naik dari sebelas sektor kartu, 18 September 2026

Dua prioritas pemilik, diukur di papan yang sama. `sd_writer.hasm` kini
mencetak `0` begitu kartu siap, lalu jumlah sektor tertulis sesudah tiap sektor;
`rtl/scripts/send_container.py` mengirim 128 kata lalu menunggu baris itu.

| # | yang dijalankan | keluaran papan |
|---:|---|---|
| 1 | container `test_hfs` @0x900, 437 kata = 4 sektor, ditulis | ACK `1` `2` `3` `4`, lalu **`1 4`** |
| 2 | `test_prog_load` memuat keempat sektor itu | **`1`** |
| 3 | container **shell** @0x900, 1.377 kata = 11 sektor, ditulis | ACK `1` … `11`, lalu **`1 11`** |
| 4 | `test_prog_run` memuat shell itu lalu menyerahkan kendali | **`HIJAIYYAH`**, `> ` |
| 5 | diketik `A`, `p`, `z` | **`A`**, **`2 0 1`**, **`z`** |

**Lari 1 adalah kegagalan yang sama, kini lewat.** Container 437 kata yang
sama persis pernah membuat papan diam total; sebabnya register RX satu byte dan
papan yang tuli selama menulis sektor. Dengan ACK, host tidak pernah bicara
saat papan tidak mendengar.

**Lari 3–5 adalah bukti terberat yang pernah dilalui loader ini.** Shell
adalah kernel utuh — penjadwal, HOS, HFS di kartu, dan loader itu sendiri —
1.245 kata dengan **125 relokasi**. Header 7 ditambah tabel 125 = 132 kata,
jadi tabel relokasinya sendiri menyeberang dari sektor 17 ke 18, lalu kata
programnya berjalan terus sampai sektor 27. Ia boot di 0x900 dan menjawab
kabel persis seperti catatan M3: `A` menggema, `p` menjawab dua proses, pid 0
dan 1. Artinya vektor trap yang dipasangnya — sebuah label, jadi ikut
direlokasi — benar, karena setiap `SYSCALL` dan setiap preemption timer lewat
situ.

**Batasnya tetap sama dengan lari-lari sebelumnya:** program pemuat masih
dikirim host lewat kabel ke `loader.hasm`. Yang terbukti adalah rantai
kartu → loader → relokasi → IMEM → eksekusi untuk program sebesar kernel.

---

## Lab serangan, lari pertama — sasaran loader, 20 September 2026

Catatan dan penjelasannya di [attack-lab/](attack-lab/README.md). Sepuluh
container, satu field dirusak per kasus, ditulis ke kartu lalu diminta dimuat:

| hasil | kasus |
|---|---|
| **ditolak, 8** | MAGIC, VERSION, WORDS = 0, LOAD_ADDR melewati memori instruksi, ENTRY di luar citra, RELOC_CNT > 128, CRC, satu kata program |
| **diterima, 2** | `words_plus_one` dan `reloc_index_moved` |

Keduanya diterima sesuai spesifikasi yang berlaku, bukan karena cacat: jumlah
32-bit **hanya menutupi kata program**, jadi tabel relokasi yang dirusak lolos,
dan WORDS yang dinaikkan satu menjumlahkan padding nol yang tidak mengubah
jumlah. Memperluas cakupan jumlah adalah perubahan spesifikasi, keputusan
pemilik.

Pembangkitnya `rtl/scripts/jim_stream.py`, mesin Jim: periode terukur ulang
**31** atas GF(2) dan **3.124** atas GF(5), cocok dengan `cosmic-codex-jim/`.

---

## Lab serangan, kelas A, C, dan D — 20 September 2026

Catatan dan angkanya di [attack-lab/](attack-lab/README.md).

**Kelas A — latensi Jamrah.** Tiap byte diukur sendiri di antara dua bacaan
pencacah 0xFF4, lima lari dari 256 byte: **33 clock untuk setiap byte**, satu
nilai saja, identik byte demi byte di kelima lari; 28 lolos dan 228 ditolak
tiap lari. Kontrolnya — predikat yang sama ditulis sebagai gelung banding,
milik lab, bukan varian gerbang proyek — **29 nilai berbeda, 13 sampai 232
clock**. Tanpa kontrol itu bacaan konstan tidak membuktikan apa pun (R3).
Klaim kanal waktu di komentar `rtl/programs/jamrah_gate.hasm` sekarang punya
angka dari silikon.

**Kelas C — Ka'bah di luar bit tunggal.** Garis dasarnya 0,4995 dari laporan
Ka'bah, yang hanya mengukur bit tunggal:

| lebar mutasi | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| rata-rata dari 1.600 bit | 0,4984 | 0,5035 | 0,5006 | 0,4984 | 0,5011 | 0,5016 | 0,5061 |

56 pasang, 0 kegagalan integritas. Permutasi empat blok memindahkan keadaan
akhir 0,4975 dan kedua urutan tetap cocok `cube.py`. Satu frame diulang empat
kali: 4/4 cocok, 4/4 keadaan berbeda.

**Frame terpotong — pernyataan tentang protokol, bukan tentang spons.** 64 byte
tidak menarik balasan sama sekali; 64 byte berikutnya menyelesaikan frame dan
balasan 200 byte-nya adalah `cube.py` dari **sambungan** keduanya. Wrapper
menyerap 128 byte tetap dan tidak punya field panjang, jadi tidak ada yang bisa
ditolaknya.

**Kelas D — aliran codex sebagai sumber kasus.** Kelas B dan C dijalankan ulang
dengan aliran Jim GF(5) menggantikan RNG. Loader: **16 dari 16 kata program
yang dirusak ditolak** — 100% untuk kategori yang memang harus ditolak.
Ka'bah: 0,5046 untuk bit tunggal, 0,4953–0,5055 untuk 2 sampai 64 bit,
permutasi 0,5056, terpotong dan diulang berperilaku sama persis. **Aliran
terstruktur tidak menemukan satu pun hal yang tidak ditemukan sumber acak** —
satu perbandingan pada ukuran ini, bukan pernyataan umum.

---

## Burn-in tingkat 1 — lab dibangun dan dijalankan, 20 September 2026

Catatan lengkapnya di [burn-in/](burn-in/README.md). `rtl/programs/burn_in.hasm`
(332 kata) mengulang satu siklus tanpa henti: gerbang Jamrah atas ke-256 byte,
ke-28 vektor codex dari ROM, enam belas kata memori data, satu `PUSH`/`POP`,
dan satu sektor kartu **dibaca** (tidak pernah ditulis). Siklus pertama
menyimpan hasilnya; tiap siklus sesudahnya membandingkan.

Tiga angka siklus pertama punya jawaban dari luar papan dan **cocok di papan**:
**28** (huruf 1..28, `jamrah_vectors.txt`), **3072** (tiga tingkat pohon, tiap
tingkat menjumlah 1.024 bit), **178** (θ + U + ρ dari Master Table). Kata
pertama sektor 1 kembali sebagai **0x48465331 — `HFS1`**.

**Dua temuan muncul dari membangun lab ini, dan keduanya dilaporkan bukan
diperbaiki (K9):**

1. **`PRINT` salah untuk angka besar.** Tangga `2^0..2^31` dikirim ke papan:
   benar sampai 4.194.304, lalu `8.388.608` kembali sebagai `8388600`, dan dari
   `2^25` ke atas muncul karakter `:` sampai `?` — yaitu nilai digit 10 sampai
   15 yang konversi desimalnya tidak bisa cetak. Karena itu program ini menjaga
   tiap angka yang dicetaknya di bawah sejuta.
2. **Kartu gagal init sesudah rekonfigurasi di tengah pembacaan** — delapan
   peluncuran dari delapan, berselang-seling tanpa kecuali. Satu percobaan
   gagal berharga ±3,3 detik (tunggu berbatas `hal_sd.hasm`), jadi lari yang
   kartunya tak pernah naik merangkak: satu lari enam menit **tanpa satu pun
   detak**.

Keduanya di [OFF.md](OFF.md) dengan angkanya.

**Tidak ada watchdog di mesin ini** — tidak ada modul semacam itu di `rtl/` —
jadi satu dari empat kriteria tingkat 1 tidak bisa diukur di papan ini, dan itu
dikatakan di muka. Yang diukur sebagai gantinya adalah **diam**: jarak antar
detak, dicatat host.

Tiga cacat saya sendiri ditemukan papan sebelum lari panjang dimulai, dan
ketiganya tercatat di kodenya: deteksi putaran pencacah yang memakai tanda
`(now - prev)` (papan menjawab 20,5 detik untuk 180,6 detik nyata — tepat satu
putaran kurang), pengurai host yang membaca tujuh angka siklus pertama sebagai
detak enam-kolom (melaporkan 3.072 kesalahan yang tidak ada), dan inisialisasi
kartu tanpa percobaan ulang.

**Tingkat 1 tutup 21 September 2026, 24 jam penuh, 0 error.**

```
86.405,4 detik jam host      86.401,5 detik jam papan sendiri
54.893 detak dipancarkan     52.282 terurai host
56.210.432 siklus            0 error   0 baca kartu gagal
kerja terhadap jam papan sendiri: 1,0002
```

Angka terakhir itu yang menjawab pertanyaan yang tidak bisa dijawab diamnya:
selama host tidak membaca — dan ia berhenti lima belas kali, dua di antaranya
lebih dari lima belas menit — tidak ada yang akan memperlihatkan papan yang
berhenti lalu jalan lagi. Kerja yang papan laporkan sendiri, dibagi lajunya,
menutupi seluruh uptime-nya. **Papan tidak pernah berhenti.**

Garis dasar yang ditinggalkannya, beku di
`cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json`:
**650,4 siklus per detik** (1,5375 ms per siklus), irama detak 1,5744 detik,
dan jam papan terhadap jam host hanyut **−0,0292 detik per jam** — 8,1 ppm
selama sehari penuh.

**Lima belas diam, tidak satu pun milik papan** — dan sebabnya kini terukur:
empat belas di antaranya adalah MacBook dalam Deep Idle yang DarkWake tiap ±16
menit (`pmset -g log`), dan logger hanya membaca selama DarkWake. Sembilan
baris tak terbaca, semuanya sesudah diam, semuanya dibuang utuh.

**Percobaan pertama 72 jam berhenti di menit ke-33**: baterai MacBook habis,
Mac berhibernasi, hibernasi memutus daya USB, dan papan kembali ke image
pabrik LiteX. Percobaan kedua berjalan dengan host ditahan terjaga.

---

## Burn-in tingkat 2 — 72 jam penuh, 0 error, 24 September 2026

Mulai 21 September 2026 05:34:30 UTC, tutup 24 September 05:34:30 UTC.
`burn_in.py` keluar sendiri dan ringkasannya berbunyi `duration reached`.
Angka dan bukti lengkapnya di [burn-in/](burn-in/README.md), tidak disalin ke
sini (R1).

```
259.204,9 detik jam host      259.198,5 detik jam papan sendiri
164.668 detak dipancarkan papan   160.967 terurai host
168.620.032 siklus

0 error                      0 baca kartu gagal
kerja terhadap jam papan sendiri: 1,0002 -- papan tidak pernah berhenti
```

Tiga hari, satu bitstream — `hcpu_gowin_top_loader.fs`, sha256 `84fdc912…`,
tidak dibangun ulang selama lari. Pencacah error papan kumulatif, dan nilai
tertingginya di seluruh 3.991 sampel adalah **0**. Dua baris `error` di log
adalah artefak pengurai, bukan error papan: keduanya didahului pada detik yang
sama oleh baris tak terurai `0H`, medannya bergeser, dan tiap sampel sesudahnya
berbunyi 0 (K-1, diperiksa pada log final).

Jam papan hanyut **−0,0375 detik per jam** terhadap jam host, 10,4 ppm, dan
berakhir −6,4 detik dalam 72 jam. Irama detak papan **1,5744 detik**, sama
persis dengan tingkat 1. Dua puluh lima diam, semuanya di enam jam pertama dan
tak satu pun milik papan; **66,2 jam terakhir tanpa satu pun diam**.

Yang **tidak** dibuktikan lari ini: pengurainya belum diadu dengan byte mentah
kabel, karena lari ini tidak menyimpannya — validasi itu menunggu lari
berikutnya.

---

## Paritas papan — 79 program, 24 September 2026

Langkah P2 urutan pemilik. Seluruh korpus Lapis 4 yang bisa dikirim dijalankan
di papan satu per satu, tiap program dengan bitstream loader dimuat ulang lebih
dulu. Jawabannya dibandingkan **hanya** terhadap `NUI/board_expected.json` yang
dibekukan sebelum papan ditanya; ekspektasi tidak diubah karena hasil papan.
Rekaman dan laporannya di `parity-board/20260924T105400Z-parity.json` dan
`.report.json`.

| | program |
|---|---:|
| **PARITY** | **73** |
| **MISMATCH** | **2** |
| **UNKNOWN** | **28** |
| dikirim | 79 dari 103 |

24 UNKNOWN adalah program yang memang tidak dikirim — 9 menyentuh jendela
kartu, 15 tidak berhenti di bawah loader — dan 4 sisanya membaca pencacah bebas
(`timer_poll`, `trap_resume`, `trap_shadow`, `trap_timer`): interpreter
menghitung instruksi, silikon menghitung clock, jadi kabel tidak bisa
memutuskan.

**Kedua MISMATCH keduanya angka besar, dan keduanya OFF-PRINT-SILICON:**

| program | diharapkan | papan |
|---|---|---|
| `rtl/programs/bench/e4_frame.hasm` | `285212673` | `28521258?` |
| `rtl/programs/test_hisab.hasm` | `2586908108` | `2586908910` |

`?` adalah `'0'` + 15 — bentuk yang sama dengan yang burn-in temukan
20 September. Tidak ada MISMATCH lain di seluruh korpus.

### Kolom perangkat keras per opcode

Diagregasi dari rekaman yang sama: sebuah opcode PARITY kalau setiap program
yang menjalankannya cocok, MISMATCH kalau setiap program yang menjalankannya
berbeda, dan **UNKNOWN kalau kabel tidak bisa memutuskan** — tidak pernah
dipaksa jadi PARITY.

| | opcode |
|---|---:|
| **PARITY** | **74** |
| **MISMATCH** | **0** |
| **UNKNOWN** | **29** |

Matriks penuhnya — tiap opcode dengan cacah buktinya dan program sumbernya —
ada di [NUI/PARITY.md](../NUI/PARITY.md), dihitung ulang dari byte mentah
rekaman ini, bukan ditulis tangan.

Dari 29 UNKNOWN: **24** karena tak satu program yang dikirim menjalankannya,
dan **5** karena ia berjalan di program yang cocok **dan** di program yang
berbeda — `HALT`, `HCRC`, `HLOAD`, `HPACK`, `PRINT`. Kabel saja tidak bisa
menunjuk instruksi mana yang berbeda, dan itulah kenapa mereka UNKNOWN dan
bukan MISMATCH, meskipun `PRINT` sudah punya butir OFF sendiri.

**Dua temuan alat, keduanya di sisi host dan bukan di RTL:**

1. **Lari pertama P2 membaca 75 dari 79 sebagai MISMATCH**, dan itu pembacanya,
   bukan papan: laporan `CYCLES=` wrapper tiba tergeser satu byte, jadi tiap
   teks papan membawa satu baris kosong ekstra. Dicatat di
   [OFF.md](OFF.md) sebagai temuan RTL yang **dilaporkan, tidak diperbaiki**;
   yang dibetulkan pembacanya.
2. **Program pertama lari itu terkontaminasi 482 detak burn-in** yang masih
   tersangkut di penyangga driver sesudah capture P1. Runner sekarang menguras
   kabel sebelum mengirim, dan lari kedua bersih.

Keduanya membuat satu aturan P1 naik ke Lapis 4: **laporan membaca byte mentah
rekaman, bukan teks yang rekaman itu bawa sejak hari ia ditulis**. Dibaca ulang
begitu, tanpa papan ditanya lagi, kedua rekaman sepakat — lari pertama
**72 PARITY, 3 MISMATCH, 28 UNKNOWN**, dan yang ketiga persis program yang
terkontaminasi; lari kedua 73 dan 2.

---

## PRINT di silikon — tangga tujuh titik, tiga lari, 25 September 2026

Langkah P4. Satu program, tujuh `PRINT`: 2²², 2²³, 2²⁴, 2²⁵, 2²⁶, 2²⁷, 2³¹.
Jawabannya dibekukan di `NUI/board_expected.json` sebelum papan ditanya, dan
dijalankan **tiga kali** dengan bitstream `84fdc912…` dan payload yang sama.

| | hasil |
|---|---|
| benar di ketiga lari | 2²², 2²⁴ |
| salah di ketiga lari | 2²³, 2²⁵, 2²⁶, 2²⁷, 2³¹ |
| batas pertama | **2²³**, sama dengan 20 September |
| keluaran salah yang berbeda | **14 dari 15** |
| interpreter, Python, RTL tersimulasi | benar di ketujuh titik |

**Silikon tidak mengulang dirinya pada nilai-nilai ini**: lari yang identik
mencetak angka salah yang berbeda untuk nilai yang sama. Tabel per lari, dan
yang tidak diklaim tentang sebabnya, di [OFF.md](OFF.md) bagian
OFF-PRINT-SILICON (R1). Tidak ada RTL yang disentuh.

---

## HALT dan RET di silikon — enam probe, 25 September 2026

Langkah P5, bitstream `84fdc912…` tanpa dibangun ulang. Rekaman
`parity-board/20260925T163903Z-stop.json`.

| probe | interpreter | RTL tersimulasi | Tang Nano |
|---|---|---|---|
| HALT → tulis register | R1 = 5 | R1 = 7 | UNKNOWN — tidak teramati dari luar |
| HALT → tulis RAM | `MEM[0x100]` = 0 | `MEM[0x100]` = 5 | UNKNOWN — tidak teramati dari luar |
| RET fault → tulis register | R1 = 5 | R1 = 7 | UNKNOWN — tidak teramati dari luar |
| RET fault → PRINT | kosong | `5` | **`5`** |
| HALT → PRINT | kosong | `5` | **`5`** |
| RET fault → PRINT, sentinel `1234` | `1234` | `1234` | **`1234` lalu `5`** |

**Silikon mengirim `PRINT` yang berada sesudah titik berhenti** — sesudah
`HALT` dan sesudah RET fault — sedangkan interpreter berhenti sebelumnya.
Sentinel `1234` membuktikan program probe itu benar-benar berjalan. Keenam
probe mengirim `CYCLES=`, jadi mesinnya benar-benar berhenti.

Register dan RAM sesudah berhenti tidak punya jalur keluar di papan ini, dan
tidak ada port debug yang ditambahkan untuk membuatnya — ketiganya tetap
UNKNOWN. Dua selisih terhadap rekaman RTL (baris baru sesudah `5`, dan `5`
sesudah sentinel) juga tetap UNKNOWN: rekaman RTL ditutup saat `halted` naik,
kabel papan tidak. Rinciannya di [OFF.md](OFF.md), "Instruksi sesudah berhenti
ikut menulis register" (R1). Tidak ada RTL yang disentuh.

---

## Validasi Ka'bah — avalanche di silikon, 20 September 2026

Laporan lengkapnya di [validasi/KABAH.md](validasi/KABAH.md). Slot Ka'bah
dibangun ulang dari sumber lebih dulu: 12.061 LUT4 (58%), 1.965 DFF, 0 BSRAM,
Fmax 165,98 MHz — sama dengan catatan rack.

| yang diukur | hasil |
|---|---|
| integritas berantai, 8 frame acak | **8/8 cocok `cube.py`** |
| replay sesudah rekonfigurasi | identik — deterministik |
| frame sama dua kali tanpa reset | keadaan berbeda — spons berantai |
| avalanche, 32 bit-flip tunggal | **0,4995** dari 1.600 bit (min 0,4700, maks 0,5275) |
| masukan termutasi | 32/32 masih cocok `cube.py` |
| keadaan yang seharusnya berbeda | 73/73 berbeda |

Yang diukur lapis 2, spons — `cube.py` menandainya **[EH]**, dan lapis 3
(HMAC-SHA256) yang memikul keamanan. Ini pengukuran difusi, bukan klaim
keamanan.

---

## Validasi Hijrah — HCPU menghitung dari ROM-nya sendiri, 20 September 2026

Laporan lengkapnya di [validasi/HIJRAH.md](validasi/HIJRAH.md). Program
`rtl/programs/hijrah_sweep.hasm` membangun ke-28 muka dengan `HLOAD`, `CGET`,
`CU`, dan `CRHO`, lalu menghitung peta berbeda atas mod 2, 3, 4, dan 5. Tiga
lari, identik sampai ke siklusnya:

| | papan | Python |
|---|---|---|
| muka | 700/700 | `build_exomatrix` |
| panjang 1, mod 2 / 3 / 4 / 5 | **24 / 27 / 28 / 28** | sama |
| runtuh atas mod 2 | **ح–ل, ش–ن, ص–ق, ع–ي** | sama |
| panjang ≤ 2, mod 2 / 3 / 4 / 5 | **321 / 649 / 625 / 714** | sama |

Mod 5 tanpa instruksi bagi: 70,62 clock per sel hasil kali lawan 70,02 untuk
mod 2, selisih 0,86%.

---

## Validasi Jamrah — 256 byte, lima lari, 20 September 2026

Laporan lengkapnya di [validasi/JAMRAH.md](validasi/JAMRAH.md); di sini hanya
yang keluar dari papan. Program dibangkitkan dari `rtl/programs/jamrah_gate.hasm`,
dikirim ke `loader.hasm`, dan setiap byte 0x00–0xFF dicetak bersama pulse dan
ketujuh simpul pohonnya, lalu dibandingkan dengan `rtl/tb/jamrah_vectors.txt` —
acuan yang sama dengan bench RTL.

| lari | hasil | lintasan 256 byte |
|---:|---|---|
| 1–5 | **256/256**, pulse dan ketujuh simpul | **9.218 clock**, identik lima kali = 36,01 clock per byte |

Yang dijalankan adalah bentuk **program**. Gerbang RTL tidak ada di slot Ka'bah
papan ini: keluarannya tak tersambung dan sintesis membuang seluruh logikanya.

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
  berdampingan   sum(slot)   harus muat serentak   15.600 + 12.061 + 16.078 = 211%
  berurutan      max(slot)   satu per satu                           16.078 =  78%
```

Dijalankan penuh di papan, berurutan, tanpa mencabut daya:

| # | slot | dimuat | hasil |
|---:|---|---|---|
| 1 | `hcpu_gowin_top` | SRAM, exit 0 | **23 byte** — `112`, lalu `CYCLES=…` |
| 2 | `hijaiyyah_kabah_gowin_top` | SRAM, exit 0 | **2/2 frame, 400/400 byte cocok `cube.py`** |
| 3 | `hcpu_hdmi_top` | SRAM, exit 0 | **23 byte** — `112`, layar 1280×720 menyala |

Tiga desain berbeda, fabric yang sama, dalam satu sesi. `112` di slot 1 dan
slot 3 adalah angka yang sama yang dihitung testbench.

> **Slot 1 dipecah sesudah lari ini, lalu dijalankan lagi.** Pada 15 September
> 2026 `hcpu_gowin_top.v` dipecah jadi `hcpu_gowin_core` — CPU beserta sideband
> telemetri — dan sebuah `hcpu_gowin_top` setipis pin di atasnya, karena
> sideband itu di tingkat atas membuat slot CPU **tidak bisa dibangun sama
> sekali** (`ERROR: Unconstrained IO:tele_pc_OBUF_O_9`). Dibangun ulang dari
> sumber pada 18 September 2026 ia keluar **byte-identik** dengan `.fs` yang
> sudah ada di direktori sejak 15 September (sha256 `29c1aed5…`) — jadi berkas
> itu memang desain hasil pemisahan, dan tanggalnya yang lebih tua dari commit
> hanyalah jarak antara pekerjaan dan commit-nya. Angka route-nya terulang
> persis: LUT4 15.744, DFF 5.065, BSRAM 18, IOB 11, Fmax 86,18 MHz.
>
> **Dan 18 September 2026 ia dijalankan di papan**: 23 byte, `112`, lalu
> `CYCLES=00001B89`. Baris slot 1 di atas karena itu berlaku untuk desain
> sesudah pemisahan juga — buktinya kembali ke tingkat 4. Rinciannya di bagian
> [Tahap 1](#tahap-1--berkas-bertahan-melewati-mati-daya-18-september-2026).

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
  LUT4    16.078 / 20.736   77%
  DFF      5.125 / 15.552   32%
  BSRAM       18 /     46   39%
  IOB         15 /    384    3%
  Fmax     90,53 MHz (HCPU), 442,48 MHz (pixel)
```

Jalur video menambah 478 LUT4 di atas HCPU sendiri, jadi biaya rack **78%**,
bukan 75%. Kalau kolom itu diisi nol, 67% akan bertahan dan jalur video
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
langsung dari pytest — dan 5.444 tes Python. Simulasi bukan
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
| `python3 -m pytest -q` | 5.444 lulus, 0 dilewati — angka itu cacah **terkumpul**, dan hari ini satu di antaranya gagal: sidik jari `hcpu_hdmi_top.v` sengaja tak dicap sejak M5.2B ditunda ([OFF.md](OFF.md)) |
| `make -C rtl/tb all` | 39 testbench, 408 pemeriksaan, 0 gagal |

Rincian per testbench, dijumlah dari baris ringkasan tiap testbench: ROM 30,
Guard 34, Codex ALU 6, HISAB 124, `tb_hcpu_top` 15, NUI embedding 10, video
timing 8, H-Kernel 8, **shell 7**, syscall I/O 6, HOS 7, subrutin 4, huruf 3,
**bayangan redirect 7**, wrapper Gowin 2, dan tujuh testbench yang melapor
**epc→eret 10**, **flags-ctx 6**, **emits 4**, **hfs-lifecycle 8**, shell 12, satu
pernyataan lulus tunggal — 311, semuanya 0 FAIL. Enam yang baru: `tb_hcpu_shell` dan `tb_hcpu_trap_redirect_shadow` tujuh
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
> 4.961 lulus, 0 dilewati, 0 gagal — 24 tes lebih banyak yang benar-benar
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
