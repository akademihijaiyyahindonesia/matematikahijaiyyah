# Yang belum menyala

Dua jenis: **terhalang** (terbangun, tidak bisa dijalankan) dan **belum ada**.
Keduanya dipisah karena jaraknya ke "menyala" sangat berbeda.

---

## Terhalang — terbangun, tidak bisa dijalankan

### Modul Ka'bah mentah masih tak bisa ditempatkan

`hijaiyyah_kabah_top` sendirian: **1.665 bit port melawan 384 IOB.** Yang
berjalan di papan adalah wrapper-nya (`hijaiyyah_kabah_gowin_top.v`), yang
menyempitkan antarmuka ke 10 pin. Modul mentahnya belum pernah, dan
perbedaan itu bukan rincian: wrapper yang lulus tidak menjadikan modul di
dalamnya sudah teruji ditempatkan.

Label: **EH**.

---

## Belum ada

### 21 opcode belum di RTL

79 dari 100 terimplementasi. Yang belum:

```
VDIST VNORM VSCL                vektor
VPROJ_K VPROJ_N VPROJ_Q VPROJ_T
CSUB CDOT CHASH CSIGN           codex
HCHK HDCMP HDES HEXMT
HPROJ HSER
JGF JGP JNP PRINTH              lompatan dan cetak
```

`CALL`/`RET` dulu yang paling menghalangi dan **sudah tidak**: keduanya kini di
perangkat keras, di 0x2E/0x2F tempat spec memesannya. Blok codex juga sudah
sebagian besar turun ke silikon — `CGET`, `CSET`, `CMOV`, `CZERO`, `CEQ`,
`CRHO`, `CU`, `CMOD4`.

**Lima dari sisanya bukan sekadar "belum dikerjakan", dan sebabnya dicatat di
sini supaya tidak dikerjakan diam-diam:**

| butir | kenapa menunggu |
|---|---|
| `CSUB` (0x43) | **Tunda — keputusan pemilik spesifikasi.** Selisihnya meninggalkan monoid (Domain C, §IA.1.11) dan bisa negatif, sementara komponen H-Reg adalah byte tak bertanda di perangkat keras. Representasi hasil negatif belum ditetapkan, dan semantik perangkat keras tidak boleh dikarang lebih dulu |
| `CDOT` (0x49) | **Dikeluarkan dari batch atas keputusan pemilik — penghalangnya tempat, bukan semantik.** RTL-nya benar dan lulus bench; yang tidak muat adalah papannya. Hasil-kali dalam atas 14 komponen adalah **14 pengali 8×8**. Dengan `CDOT`, `hcpu_gowin_top` mencapai **16.015 LUT4 (77%)** dan nextpnr menjawab *"Unable to find legal placement for all cells"* — dua kali, pesan sama, jadi bukan variasi placer. Tanpa `CDOT`: **14.714 LUT4 (70%)**, ter-place, terrout, dan dijalankan di papan (12 September 2026). Tetap berjalan di HVM; naik ke RTL ketika ada tempat (papan lebih besar, atau ASIC Fase 6) |
| `VNORM` (0x4A), `VDIST` (0x4B) | RTL **sudah** menjalankan operasinya dengan nama yang dibekukan buku: `HNRM2` (0x06) dan `HDIST` (0x07). Menambah encoding kedua untuk satu operasi adalah cacat yang `7582ae5` bersihkan dari seluruh pohon |
| `VPROJ_K/N/Q/T`, `HCHK` | **tidak ada di `docs/HISA_SPEC.md`**. Tidak dikerjakan atas inisiatif sendiri |
| `CHASH` (0x70), `CSIGN` (0x72) | menaruh inti hash/tanda tangan di RTL, bersinggungan langsung dengan R10 (lapis 3 satu-satunya pemikul keamanan) |

**Satu konflik di dalam spesifikasi, dicatat bukan dirapikan.**
`docs/HISA_SPEC.md` §6.2 menaruh `AND`/`OR`/`XOR`/`NOT`/`SHL`/`SHR` di dua
tempat: blok Arithmetic & Logic 0x17–0x1C dan blok Bitwise 0xB0–0xB5. Yang
berjalan di perangkat keras adalah 0xB0–0xB5 (`8e92825`), dan `hcpu_pkg.vh`
adalah sumber kebenaran encoding menurut §6.0 dokumen itu sendiri. Perbaikan
dokumennya menunggu keputusan pemilik proyek; tidak disentuh sepihak.

Label: `AT`.

### HFS dan HOS

Buku menetapkan tumpukan tujuh lapis:

```
7  Aplikasi          program HC, alat analisis                 ✅
6  HVM / HCPU        eksekusi bytecode (perangkat lunak/keras)  ✅
5  Layanan Hybit     akses HAR, protokol HISAB, daemon pengaman ◐  HAR ada, HISAB belum layanan
4  HFS               sistem berkas yang sadar hybit             ◐  tulis dan baca ada, penyimpanan persisten belum
3  H-Kernel          manajemen proses, memori, dan I/O          ✅  4 dari 4
2  HAL               lapisan abstraksi perangkat keras          ✅
1  Perangkat keras   CPU/HCPU, memori, I/O                      ✅
```

Enam dari tujuh lapis kini punya sesuatu yang nyata. Yang tersisa, berurutan:

#### HFS — satu celah bersisa

Jalur tulis (`hos_fs_write` di `rtl/programs/hos.hasm`) nyata: `HGRD`
dijalankan sebelum berkomitmen, vektor korup ditolak. Jalur bacanya kini utuh
juga: `CSET` (0x45) ada di RTL, jadi `hos_fs_read` membangun ulang vektor
tersimpan ke H0 komponen demi komponen — bukan lagi sekadar penunjuk ke 18
kata mentah. Yang masih hilang satu:

| butuh | keadaan |
|---|---|
| penyimpanan persisten | **belum diverifikasi** — HFS sekarang murni RAM data (`0xE00`+), hilang saat reset. Tang Nano 20K punya jalur SDRAM/PSRAM di chipdb-nya (`IO_sdram_dq[0:31]` muncul saat PNR), tapi belum dipastikan papan fisiknya benar-benar memasang chip PSRAM |

Verifikasi PSRAM Tang Nano 20K adalah pertanyaan perangkat keras: apakah chip
itu benar-benar terpasang di papan yang dipegang, bukan hanya ada di chipdb.

#### Layanan Hybit — HAR ada, HISAB belum

`hos_har_get` memenuhi "HAR sebagai layanan sistem" persis seperti yang buku
minta: titik masuk bernama dan stabil, bukan indeks ROM mentah. Protokol
HISAB (HPACK/HCRC, sudah di RTL sejak lama) belum dibungkus jadi layanan
kernel yang sama — masih dipanggil langsung sebagai instruksi, bukan lewat
`SYSCALL` bernama. Daemon pengaman sudah ada (proses C, sejak H-Kernel).

#### Apa yang HOS-nya sendiri sudah selesaikan

Empat sifat HOS di buku semuanya berjalan sekarang — lihat
[ON.md](ON.md#hos-heap-hfs-har). Yang tertulis di sini adalah sisa di bawahnya
(HFS lapis 4, layanan HISAB lapis 5), bukan HOS-nya sendiri.

### M3 — shell: jalur keluaran karakter, dan resume setelah preemption

**12 September 2026.** Shell-nya berjalan di papan fisik: perintah masuk lewat
UART, dijawab lewat kernel (`rtl/programs/shell.hasm`, `make -C rtl/tb
sim_shell`). Dua hal menghalanginya menjadi shell yang digambar pemilik, dan
keduanya diukur, bukan diduga.

#### 1. Tidak ada jalur keluaran karakter — `PRINTH`/`EMITS` ditunda pemilik

`PRINT` adalah satu-satunya jalan keluar dan ia mencetak **angka desimal**
diikuti newline (`rtl/hcpu_top.v`, keadaan `P_CONV`: `8'h30 + val % 10`).
Tidak ada cara menaruh satu karakter di kabel, jadi tidak ada prompt, tidak ada
gema baris yang diketik, dan tidak ada editor baris. Karena itu **satu byte
adalah satu perintah**, dan jawabannya angka.

Spesifikasi menamai dua slot yang relevan dan **keduanya bertanda "perangkat
lunak saja"**:

| slot | apa | status |
|---|---|---|
| `PRINTH` 0xA1 | cetak codex | **BLOCKED** — perintah pemilik, 12 September |
| `EMITS` 0xA2 | cetak string di alamat IMM | **BLOCKED** — perintah pemilik, 12 September |

Dan `EMITS` punya penghalang kedua di atas itu: **spesifikasi tidak menetapkan
bentuk string di RAM 32-bit**. Satu karakter per kata, empat karakter per kata,
atau panjang di depan — ketiganya mungkin, dan memilihnya berarti mengarang
semantik perangkat keras. Pemilik spesifikasi yang menetapkan.

Yang **tidak boleh** dikerjakan atas inisiatif sendiri, tercatat di sini supaya
tidak terjadi diam-diam: menaruh `PRINTH`/`EMITS` di RTL, membuat driver TX
kedua (`rtl/hcpu_mmio.v` menolaknya: "a second driver on the same port is a bus
conflict"), memakai `rtl/hcpu_font8x8.hex`, atau mengubah semantik `PRINT`.

#### 2. Proses yang diambil TIMER tidak pernah berjalan lagi

Ini lebih dalam daripada shell, dan ia **sudah ada sejak penjadwal dibangun**.

`rtl/programs/kernel.hasm` — sudah di-commit, sudah dijalankan di papan —
membekukan proses A pada cacah **337**, dengan `pcbA.pc = 0` di bloknya.
Benchnya sendiri tidak melihatnya: `tb_hcpu_kernel.v` memeriksa kelipatan B dan
sapuan C, tidak memeriksa bahwa A masih bergerak. `shell.hasm` mewarisi persis
gejala yang sama untuk pid 0.

Yang terukur, pada `fire` timer pertama di kedua kernel:

```
FIRE#1 which=0 pc_now=0 if_pc=0 btaken=0 btarget=0 id_pc=0 stall=0
```

Ujung depan tidak memegang PC apa pun, jadi `epc <= pc_now` menyimpan **0**.
Kernel menyimpan 0 itu ke blok proses, melanjutkan prosesnya di alamat 0 —
kode boot — dalam mode user, dan simpanan periferal pertama di HAL
menggagalkannya sebagai **cause 3** selamanya. Sesudah itu `pcb.pc` berisi
alamat di dalam `hal.hasm`, yang adalah tanda tangan cacat ini.

**Sebabnya sudah diisolasi, 13 September 2026: bayangan redirect.**

Sebuah lompatan yang diambil membuat ujung depan di-redirect, dan
`rtl/hcpu_fetch.v` menjawab redirect dengan:

```verilog
end else if (flush || branch_taken) begin
    if_instruction <= {`OP_NOP, 24'h000000};
    if_pc          <= {`XLEN{1'b0}};
    fetch_valid    <= 1'b0;
```

Menolkan `if_pc` adalah cara Fetch berkata *"saya tidak sedang menyajikan
instruksi"*, dan `fetch_valid` turun mengatakan hal yang sama untuk siklus
berikutnya. Tetapi `pc_now` di `rtl/hcpu_top.v` membaca `if_pc` **tanpa
menanyakan `fetch_valid`**:

```verilog
.pc_now (branch_taken_w ? branch_target_w : if_pc),
```

Jadi selama **dua siklus** yang dibayar sebuah redirect, interupsi termaskable
tidak membaca "tidak ada apa-apa di sini" — ia membaca **alamat nol**, lalu
menyimpannya sebagai tempat kembali.

**Perbaikan yang sudah ada menutupi siklus yang lain.** `hcpu_top.v` sudah
memperbaiki kasus trap dan cabang yang **berbagi siklus** (`branch_taken_w ?
branch_target_w : …`), ditemukan lewat `tb_hcpu_branch_trap_race.v`. Yang tidak
tertutup adalah dua siklus **sesudahnya**, ketika `branch_taken_w` sudah turun
lagi sehingga perbaikan itu tidak berlaku.

Terukur, `make -C rtl/tb sim_redirect_shadow`, menyapu tenggat terhadap loop
tiga instruksi yang berakhir dengan `JMP`:

```
60 fire: 39 sah, 21 menyimpan 0
sekelas siklus dengan cabang: 10   bayangan redirect: 21
```

Setiap fire yang jatuh di bayangan menyimpan 0; tidak ada yang di luar
bayangan melakukannya. Sepuluh tabrakan sekelas-siklus tetap mengembalikan
sasaran cabang — perbaikan lama bekerja.

**Dan papan menjawab hal yang sama**, `rtl/programs/trap_shadow.hasm`, delapan
sampel dengan tenggat digeser satu siklus tiap kali, loop di alamat 88:

```
0  0  88  89  88  0  0  88
```

Empat dari delapan dikembalikan ke **alamat 0**.

Ini yang membunuh proses A: loop tiga instruksi memakan enam siklus, **dua di
antaranya** bayangan itu, jadi satu dari tiga tenggat mengirim prosesnya ke
alamat 0 — dan alamat 0 adalah kode boot, dalam mode user, tempat simpanan
periferal pertamanya gagal selamanya.

`rtl/programs/trap_resume.hasm` mengembalikan `84 84` di papan bukan karena
jalurnya benar, melainkan karena tenggatnya kebetulan jatuh di luar bayangan.
Itu keberuntungan, dan sekarang bisa dikatakan sebagai fakta terukur, bukan
dugaan.

**Perbaikannya tidak dikerjakan di sini** — ia ada di unit trap, dan itu
keputusan pemilik.

Akibatnya untuk M3: penjadwal **bergilir** (ticks naik, kedua blok dipilih
bergantian) tetapi **tidak melanjutkan** proses yang dipreempt. Yang berjalan
penuh adalah proses yang menyerahkan CPU-nya sendiri lewat `SYSCALL yield` —
dan itulah sebabnya shell-nya berjalan.

#### 3. FLAGS bukan bagian dari konteks proses, dan tak ada yang bisa menyimpannya

`rtl/programs/trap_flags.hasm` mencetak **`0`** di papan: perbandingan yang
dibuat di mode user tidak selamat melewati trap, karena handler harus
membandingkan `TRAP_CAUSE` dan perbandingannya menimpa yang milik user.

Enam belas GPR, PC, dan jendela memori semuanya disimpan oleh context switch.
FLAGS bukan salah satunya, dan **tidak ada instruksi di ISA ini yang membaca
FLAGS ke register** (§6.2 punya `CMP`/`CMPI` untuk menulisnya dan bentuk-J
untuk membacanya, tidak ada yang lain). Jadi ini bukan kernel yang lupa satu
field — ini field yang tak terjangkau perangkat lunak.

Trap sukarela bisa diatur: program cukup tidak meninggalkan perbandingan hidup
melewati `SYSCALL`-nya sendiri, dan `shell.hasm` menjaga disiplin itu di setiap
`CMP`. Trap **timer** tidak bisa diatur.

#### 4. `STORE` ke `TRAP_EPC` tepat sebelum `ERET` kembali ke epc lama

Terukur di papan saat menulis `trap_flags.hasm`: `SYSCALL` yang sama di PC 80
menjebak **tiga kali berturut-turut**, mencetak 80 setiap kali, sampai tiga
`NOP` disisipkan antara simpanan dan `ERET`.

`rtl/hcpu_trap.v` sudah membawa bypass untuk bahaya yang **sama persis** pada
`TRAP_MODE` (`prev_at_eret`), dan komentarnya menutup dengan kalimat *"One NOP
in between was enough to hide it; the fix is not to require one."*
`TRAP_EPC` tidak mendapat perlakuan itu: `trap_target = eret ? epc : vector`
membaca registernya. Sepuluh instruksi `hal_epc_set` → `hal_mode_user` →
`hal_timer_arm` → enam belas `LOAD` memberi jarak yang cukup, jadi kernel yang
ada tidak terkena — tetapi handler yang ringkas terkena, diam-diam.

Label: `AT`.

### Yang H-Kernel belum punya

Kernelnya berjalan, dan ruang lingkupnya sempit dengan sengaja:

| ada | belum |
|---|---|
| tiga proses tetap | pembuatan proses dinamis |
| register per proses | **stack alamat-kembali tidak disimpan** — proses yang memakai `CALL` akan melihat alamat kembali milik proses lain |
| round-robin | prioritas atau kuantum per proses |
| preemption timer + yield | tidur, tunggu, atau sinyal |
| jendela memori per proses | memori bersama antar proses |
| satu nomor panggilan syscall | tabel panggilan |

Satu batas layak disebut terang-terangan: **`PUSH` tidak dibatasi mode user**.
Proses user bisa menghabiskan stack 256 entri yang dipakai bersama kernel. Ia
*fault* lewat guard [HC-02] dan bukan merusak diam-diam — tapi itu tetap lubang
isolasi, dan menutupnya butuh stack per proses.

Label: `AT`.

### ASIC

Tidak ada pemetaan sel standar. Sintesis gerbang generik memberi 384.840 sel,
70% di antaranya `hcpu_dataram` — 4096×32 tersintesis sebagai larik register,
bukan makro memori. Sebelum tape-out ia harus jadi SRAM makro atau dikecilkan.

Label: `EH`.

---

## Ringkas

```
menyala   matematika, bahasa, mesin, sistem operasi, kripto,
          jembatan (simulasi + bitstream HCPU di Tang Nano 20K)
terhalang top level gabungan, HFS baca (tanpa CSET), penyimpanan persisten
belum ada 24 opcode, proses dinamis, ASIC
```

Enam lapis berjalan. Silikon dedikasi (ASIC, bukan FPGA) belum dimulai, dan
sebabnya sudah punya nama dan angka — lihat [ROADMAP.md](ROADMAP.md).
