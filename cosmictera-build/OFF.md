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

### Pixel HDMI rusak, dan sambungannya sendiri sehat

Dibekukan sebagai cacat terbuka atas keputusan pemilik, 17 September 2026,
setelah investigasi satu-variabel yang panjang gagal menamai akarnya. Yang
dibekukan adalah penyelidikannya, bukan faktanya: faktanya terukur.

**Yang sudah terbukti, dan tidak boleh diragukan lagi oleh yang melanjutkan:**

| | bukti |
|---|---|
| Monitor mengunci 1280×720 | pengamatan pengguna, berulang |
| HSYNC/VSYNC, geometri, posisi area aktif | benar — teks muncul di sel yang tepat |
| Node display ter-place dan ter-flash | **685 LUT4 (3%)**, Fmax 102,44 MHz, 0 hold, 0 setup |
| Tumpukan M5 bukan penyebabnya | build diagnostik tanpa font, layout ROM, compositor maupun renderer — empat bilah warna solid — menunjukkan artefak yang sama |

**Yang belum terbukti:** bahwa pipeline pixel menghasilkan gambar bersih, dan
apa penyebab tunggalnya.

**Tereliminasi oleh pengukuran — jangan diulang.** Masing-masing ini sudah
diuji dan gugur, dan mengulangnya adalah membelanjakan waktu yang sama dua
kali:

- **Seluruh M5** — font ROM, layout ROM, compositor, renderer, telemetri,
  BSRAM. Build diagnostik tanpa satupun tetap bergaris.
- **CALIB** — 1 dan 0 dibangun keduanya; tidak ada beda di layar.
- **Urutan bit TMDS** — dibalik, dan tautan monitor **mati sama sekali**.
  Tautan yang mati ketika kata dibalik adalah tautan yang katanya sudah benar.
- **PLL/CLKDIV** — aritmatikanya tutup tanpa sisa: 1650 × 750 × 60 = 74,25 MHz;
  27 × 55/4 = 371,25 MHz; 371,25/5 = 74,25 MHz. fPFD 6,75 MHz, fVCO 742,5 MHz.
- **Timing fabric** — `pixel_clk` Fmax terukur 276,24 MHz melawan 74,25 MHz yang
  dibutuhkan: margin 3,7×. `serial_clk` tidak punya satu pun jalur fabric.
- **Jaringan clock** — `serial_clk` dan `pixel_clk` keduanya *"routed using
  global resources only"*.
- **Encoder TMDS** — cacat **nyata** ditemukan di sini dan diperbaiki: ketiga
  cabang disparitas tidak konsisten terhadap data yang dikirimnya, 30 dari 256
  byte gagal round-trip dan `disparity` lari ke −10.240 pada register
  `signed [5:0]` yang hanya memuat −32..+31. Sesudah perbaikan: 0 dari 1.024
  gagal, |disparity| tak pernah lewat 8. **Layar tidak berubah** — yang
  membuktikan cacat itu nyata tetapi bukan cacat ini.
- **Tahap output TMDS** — tereliminasi oleh perangkat kerasnya sendiri. Tiga
  cara menggerakkan belahan N dengan logika, ketiganya ditolak sebelum ada
  bitstream: `ELVDS_OBUF` dijatuhkan penempatan (sintesis 4 → penempatan 0);
  inverter pada aliran serial memicu `out_iob != nullptr && out_iob->bel !=
  BelId()` di `pack_iologic.cc:183` karena OSER10 wajib mencapai pad langsung;
  dan OSER10 kedua ditolak dengan `Can't place u_lane_r.u_oser at X39Y54/IOBB
  because it's already taken by tmds_data_n_OBUF_O`. Netlist ter-route
  memperlihatkan sebabnya — satu `IOLOGIC_DUMMY` per OSER10, karena satu
  serialiser 10:1 menduduki IOLOGIC **kedua** belahan pasangan. Maka pad N
  tidak bisa digerakkan logika **di sini maupun di desain rujukan**, dan
  `O_tmds_*_n` milik Sipeed pasti berasal dari buffer pad diferensial yang
  diberi satu aliran — konstruksi yang sama dengan `IO_LOC "…_OBUF_O" 33,34`
  pada `LVCMOS33D` milik kita. Tidak pernah ada perbedaan untuk diuji.

**Petunjuk terkuat yang tersisa, dan ia belum selesai dibaca.** Bitstream yang
bit-identik dimuat **30 kali** berturut-turut (`04596c98b780995d`, 10 muatan lalu
20 muatan). Gambarnya **berubah-ubah**, dan sebagian muatan menghasilkan gambar
diam sementara sebagian lain berkedip. Desainnya tidak berbeda sedikit pun antar
muatan, jadi yang memutuskan bukan desainnya — dan itu menjatuhkan seluruh kelas
cacat statis, termasuk yang sudah diperbaiki di atas.

Satu mekanisme menjelaskan ketiga wajah itu tanpa sebab kedua: `DIV_MODE="5"`
punya lima fase keluaran yang mungkin, dan seluruh rantai keluar dari reset pada
`pll_locked` yang **asinkron dan tidak disinkronkan** — `CLKDIV.RESETN` dan
keempat `OSER10.RESET` dilepas pada instan yang sama, sehingga serialiser keluar
dari reset tepat ketika `PCLK`-nya baru lahir. Fase yang jauh dari batas memberi
gambar diam yang salah; fase dekat batas setup/hold memberi kedipan, karena yang
terkunci adalah fasenya dan bukan hasil samplingnya; fase yang benar memberi
gambar bersih.

**Yang belum dijawab, dan menentukan:** apakah dari 30 muatan itu pernah ada satu
yang **bersih**. Kalau pernah, seluruh rantai TMDS terbukti benar dan yang
tersisa hanya menguncinya — reset yang disinkronkan dan diurutkan. Kalau tidak
pernah, "satu fase benar dari lima" tinggal ~1% peluangnya dan ada cacat kedua
yang bertahan di semua fase. Pertanyaan itu hanya bisa dijawab dari layar.

**Variabel yang belum pernah diubah sama sekali:** papan ini, kabel ini, monitor
ini. Setiap eksperimen mengubah desain kita dan membiarkan ketiganya tetap.

Label: **EH**.

---

## Belum ada

### 21 opcode belum di RTL

82 dari 103 terimplementasi. Yang belum:

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
4  HFS               sistem berkas yang sadar hybit             ◐  empat operasi ada, persisten tersimulasi, belum di papan
3  H-Kernel          manajemen proses, memori, dan I/O          ✅  4 dari 4
2  HAL               lapisan abstraksi perangkat keras          ✅
1  Perangkat keras   CPU/HCPU, memori, I/O                      ✅
```

Enam dari tujuh lapis kini punya sesuatu yang nyata. Yang tersisa, berurutan:

#### HFS — mediumnya sudah hidup lebih lama dari catu dayanya

Jalur tulis (`hos_fs_write` di `rtl/programs/hos.hasm`) nyata: `HGRD`
dijalankan sebelum berkomitmen, vektor korup ditolak. Jalur bacanya kini utuh
juga: `CSET` (0x45) ada di RTL, jadi `hos_fs_read` membangun ulang vektor
tersimpan ke H0 komponen demi komponen — bukan lagi sekadar penunjuk ke 18
kata mentah.

Empat operasinya kini utuh dan bernama: `hos_fs_create` dibuat di M4.1, jadi
"berkas ini sudah ada" akhirnya bisa dinyatakan, dan siklus
create → write → read → verify berjalan di papan sebagai `1 0 1 1 1 1 0`
(`rtl/programs/hfs_lifecycle.hasm`).

**Medianya menyala 15 September 2026, dan bertahan melewati mati daya.**
Kartu TF onboard, SDIO 1-bit, sektor mentah LBA 1, MicroSD 4 GB SDHC FAT32:
`10` → `1 1 0 10` → `1 1 1 1 10` → `1 1 1 10` sesudah reset → `1 1 1 10`
sesudah daya dicabut. Rinciannya, termasuk kenapa yang terakhir bukan cache
kartu, ada di [PAPAN.md](PAPAN.md). Ketiga penghalang yang berkas ini catat
kemarin — kartu di slot, pinout, rantai persistensi — ketiganya tutup, dan
pinout `.cst` berhenti menjadi klaim.

Yang membuka jalannya: `S_CMD_GAP`, karena `hcpu_sdio.v` mengirim tiap perintah
dengan jarak **nol** clock di mana standar menuntut delapan. Kartu sehat
menjawabnya dengan diam 100 ms, empat kali, dan simulasi tidak bisa melihatnya
karena model kartunya bukan model timing. Sekarang model itu menegakkan N_CC,
dan sabotase gap 7 membuatnya merah.

**Yang tersisa untuk lapis 4, dan ini pekerjaan lain:** HFS sendiri masih
memakai RAM data (`0xE00`+) dan hilang saat reset. Yang terbukti persisten
adalah **jalur ke kartunya**, bukan HFS di atasnya — menyambungkan keduanya,
sehingga `hos_fs_write` mendarat di sektor kartu alih-alih di RAM, **dibuka
pemilik 17 September 2026** sebagai tahap 1 gerbang KV260, dan **kini
tersambung di simulasi**. CREATE dan WRITE di-commit ke kartu, boot memuat HFS
dari kartu, dan sebuah berkas melewati reboot dengan seluruh RAM data dinolkan
(`rtl/tb/tb_hcpu_hfs_persist.v`). Tata letak di kartu — keputusan pemilik —
tinggal di satu tempat, kepala `rtl/programs/hos_hfs_disk.hasm`.

Penutupnya tetap fisik: berkas bertahan melewati **mati daya** di papan dan
dibaca kembali identik. Model kartu tidak bisa kehilangan daya, jadi simulasi
membuktikan logikanya dan tidak lebih. Tahap ini menunggu papan tersambung —
`openFPGALoader` menjawab `unable to open ftdi device: -3`, 18 September 2026.

**Yang sudah siap, sehingga yang tersisa hanya papan.** Probe yang dijalankan
bench melaporkan hasilnya lewat syscall `write`, jadi ia terbaca dari kabel
serial dan bukan hanya dari RAM bench:

```
make -C rtl/tb shell_persist.hex
make -C rtl/fpga/gowin PROGRAM=../../tb/shell_persist.hex bitstream   # 15.744 LUT4, 86,18 MHz
# pembaca serial dibuka DULU, baru bitstream dimuat: keluaran datang segera
make -C rtl/fpga/gowin PROGRAM=../../tb/shell_persist.hex flash
make -C rtl/fpga/gowin program.hex      # kembalikan: program.hex terlacak git
```

Baris terakhir bukan kerapian. `rtl/fpga/gowin/program.hex` adalah berkas
terlacak yang dijaga menyamai `PROGRAM` bawaan, dan memanggang citra lain
menimpanya: terukur, empat tes gagal dan enam error sampai ia dikembalikan.

Yang dipanggang adalah **berkas yang sama** yang dijalankan bench,
`rtl/tb/shell_persist.hex`, disalin bukan dirakit ulang — jadi papan dan bench
tidak bisa menyimpang diam-diam. Yang dibaca dari kabel, terukur di bench:

| kabel | artinya |
|---|---|
| `1 1 1` | boot pertama: berkas belum ada, CREATE dan WRITE sampai ke kartu |
| `2` | boot sesudahnya: berkas ada dan vektornya Kaf — **ini yang menutup tahap 1**, sesudah daya dicabut |
| `3` | berkas ada, isinya bukan yang ditulis |
| `1 0 0` | kartu tak pernah di-init: RAM menerima, kartu menolak — terukur lewat sabotase yang menghapus `hos_fs_mount` |

Bitstream dimuat ke SRAM, bukan flash SPI papan, sama seperti M4.2: sesudah
daya dicabut papan menyala sebagai SoC LiteX pabrikannya, dan itu bukti
independen bahwa daya memang putus, lalu bitstream dimuat lagi.

| butuh | keadaan |
|---|---|
| medium persisten | ✅ **terbukti di papan**, 15 September 2026 |
| HFS lewat kernel | ✅ **di RAM** — syscall 6/7/8 dari mode pengguna (`a5e4f3f`), tersimulasi, belum di papan |
| HFS memakai medium itu | **tersimulasi** — CREATE/WRITE commit ke sektor 1–3, boot memuat dari kartu, berkas melewati reboot dengan RAM dinolkan. **Belum di papan**: mati daya fisik belum dijalankan |

#### H0 diselamatkan di dalam syscall, tidak saat pergantian proses

Ini batas, bukan celah yang terlupa, dan ia harus terbaca di sini supaya tidak
diam-diam dianggap tertutup.

Yang **terbukti** (`rtl/tb/tb_hcpu_trap_hreg.v`, `rtl/tb/tb_hcpu_hfs_syscall.v`):
handler syscall HFS menyimpan H0 pemanggil ke slot per-proses di `0xE98 +
pid×18` dan memulihkannya, jadi kode kernel boleh memakai register codex tanpa
menghancurkan argumen pemanggil.

Yang **tidak terbukti, dan tidak benar secara umum**: H0 selamat ketika sebuah
proses **dipreempt** di antara memuat H0 dan memanggil syscall. Pergantian
konteks di `rtl/programs/shell.hasm` menyimpan R0–R15 dan FLAGS; ia tidak
menyimpan H-register satu pun, dan slot per-proses baru diisi di dalam syscall.

```
proses A  HLOAD H0, ...     vektor A di H0
timer     → dispatch → proses B memakai H0 untuk codex-nya
timer     → kembali ke A    H0 kini milik B
proses A  SYSCALL 8         menulis vektor B ke berkas A
```

Hari ini tak satu pun proses selain pemanggil HFS yang menulis register codex,
jadi urutan itu tidak terjadi — **selamat karena kebetulan**, bentuk yang sama
yang tes ABI HFS ada untuk berhenti diandalkan.

Kenapa belum ditutup, terukur:

| cara | biaya | hasil |
|---|---|---|
| bank ke-16 H-register di RTL | +3.286 LUT4 | ditolak placement |
| bank H0 saja di RTL | +336 LUT4 | ditolak placement |
| simpan ke-16 lewat `CGET`/`STORE` di tiap pergantian | 1.152 instruksi, 28% citra | terlalu mahal |
| opcode simpan/muat H-register utuh | `CSTORE` 0x41 ada di spesifikasi, pasangan muatnya **tidak** | keputusan ISA v1.3, ditunda |

Pemilik menunda konteks hybit penuh ke KV260, 17 September 2026. Label: **AT**.

Papan ini **tidak punya jalur card-detect**, jadi bit `CARD_PRESENT` menyatakan
"kartu pernah menjawab", bukan "ada kartu". Perbedaan itu tidak bisa ditutup
dari perangkat lunak, dan tidak akan bisa — tapi sejak kartu menjawab, bit itu
menjadi informasi yang berguna, bukan sekadar peringatan.

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

**Keempat penghalang ditutup 13 September 2026.** Bagian ini disimpan utuh —
sebab, angka, dan sabotasenya — karena bagaimana sesuatu ditutup adalah yang
membuatnya tetap tertutup.

**12 September 2026.** Shell-nya berjalan di papan fisik: perintah masuk lewat
UART, dijawab lewat kernel (`rtl/programs/shell.hasm`, `make -C rtl/tb
sim_shell`). Dua hal menghalanginya menjadi shell yang digambar pemilik, dan
keduanya diukur, bukan diduga.

#### 1. ~~Tidak ada jalur keluaran karakter~~ — DIPERBAIKI 13 September 2026, H-ISA v1.1

**Yang menghalanginya.** `PRINT` adalah satu-satunya jalan keluar dan ia
mencetak **angka desimal** diikuti newline (`rtl/hcpu_top.v`, keadaan
`P_CONV`: `8'h30 + val % 10`). Tidak ada cara menaruh satu karakter di kabel,
jadi tidak ada prompt, tidak ada gema baris, tidak ada editor baris. Slot
`EMITS` (0xA2) sudah dinamai spesifikasi sejak v1.0 — tetapi **bentuk stringnya
di RAM 32-bit tidak pernah ditetapkan**, dan memilihnya berarti mengarang
semantik perangkat keras.

**Keputusan pemilik, 13 September 2026.** Satu karakter ASCII per word 32-bit,
word `0x00000000` sebagai penutup:

```
EMITS IMM
addr = IMM
while MEM[addr] != 0:
    keluarkan MEM[addr] & 0xFF
    addr = addr + 1        ; word berikutnya
```

Dipilih **bukan karena paling hemat** melainkan karena paling mudah
diverifikasi: tidak ada ambiguitas urutan byte, tidak ada empat karakter
dikemas dalam satu word, penutupnya gampang diuji dan gampang disabotase.
Borosnya empat kali lipat diterima — yang dibuktikan di tahap ini adalah jalur
keluaran karakter, bukan kepadatan penyimpanan. §13.1.1.

**Alamatnya alamat WORD.** Tabel keputusan pemilik menuliskannya sebagai
alamat byte (`0x1000`, `0x1004`, `+4`); RAM data mesin ini 4096 × 32 bit dan
`LOAD`/`STORE` mengalamatinya per word, jadi "word berikutnya" di sini `+1`.
Tata letaknya sama, satuan alamatnya berbeda.

**Bukan pemancar kedua.** `rtl/hcpu_mmio.v` menolak driver kedua di port
serial — *"a second driver on the same port is a bus conflict rather than a
feature"* — dan penolakan itu dipegang: mesin keadaan cetak di `hcpu_top.v`
bertambah tiga keadaan dan satu sumber, tidak ada perangkat keras baru yang
menyentuh `hcpu_uart_tx`. Port RAM data di-**mux**, bukan digandakan, dan itu
aman karena pipeline berhenti selama mencetak, persis seperti untuk `PRINT`.

**Tiga jalur keluaran, tiga domain, tidak saling meminjam:**

| instruksi | mencetak |
|---|---|
| `PRINT` 0xA0 | bilangan bulat, desimal, diakhiri newline |
| `PRINTH` 0xA1 | codex/hybit — **tetap perangkat lunak saja** |
| `EMITS` 0xA2 | karakter dan string |

**Di papan:**

```
Hijaiyyah                  uji penerimaan
HIJAIYYAH                  banner shell
> A                        'A' menggema sebagai A, bukan 65
> 2 0 1                    'p' tetap menjawab angka
>                          prompt tanpa newline — kursornya menunggu
```

`EMITS` **tidak** menambahkan newline. `PRINT` menambahkannya karena ia
mencetak satu bilangan; sebuah string membawa akhirannya sendiri kalau memang
mau — dan itulah yang membuat sebuah prompt mungkin.

Disabotase bertiga sesuai perintah pemilik, dan ketiganya merah: penutup
dihapus → `HijaiyyahZZZ`; satu karakter diubah → `HijaXyyah`; langkahnya
dijadikan `+4` → `Hih`. **Sabotase pertama mula-mula tidak menggigit** karena
RAM simulasi mulai dari nol, jadi penutup yang tak ditulis tetap nol;
`rtl/tb/tb_hcpu_emits.v` sekarang menulis `Z` ke word penutupnya lebih dulu,
supaya penutup itu benar-benar yang menghentikan (R3).

#### 2. ~~Proses yang diambil TIMER tidak pernah berjalan lagi~~ — DIPERBAIKI 13 September 2026

**Akarnya: bayangan sebuah redirect.** Lompatan yang diambil membuat ujung
depan di-redirect, dan `rtl/hcpu_fetch.v` menjawabnya dengan `if_pc <= 0` dan
`fetch_valid <= 0` — caranya berkata *"saya tidak sedang menyajikan
instruksi"*. `rtl/hcpu_top.v` menyambung alamat-kembali interupsi termaskable
ke `if_pc` **tanpa menanyakan** apakah PC itu nyata, jadi selama dua siklus
yang dibayar sebuah redirect ia membaca **alamat nol** dan menyimpannya sebagai
tempat kembali. Prosesnya lalu dilanjutkan di alamat 0 — kode boot, dalam mode
user — tempat simpanan periferal pertamanya gagal selamanya.

Perbaikan lama menutup siklus yang **dibagi** trap dan cabang
(`rtl/tb/tb_hcpu_branch_trap_race.v`); dua siklus **sesudahnya** tidak
tertutup, karena di sana `branch_taken_w` sudah turun lagi.

**Perbaikannya sudah tertulis di kode itu sendiri**, di komentar `hcpu_top.v`
yang memasang `pc_valid` ke `1'b1`:

> *"if the front end ever gains a state with no meaningful PC, this has to
> become that state's inverse or a trap will return into a bubble."*

Ujung depan memang punya keadaan itu, dan selalu punya. `hcpu_fetch` sekarang
membawa `pc_valid` — ditulis di tempat-tempat yang sama dengan `if_pc`, jadi
tak bisa hanyut darinya — dan `hcpu_top` menyetir unit trap dari situ. Trap
tidak menyala selagi ujung depan kosong; ia menyala satu-dua siklus kemudian
dengan PC yang nyata. Namanya bukan istilah baru: `hcpu_trap.v` sudah memanggil
konsep ini `pc_valid` sejak trap dibangun, dan `tb_hcpu_trap.v` sudah punya
pemeriksaan **"pc_valid gates entry"** sejak saat itu juga.

**Terukur, sebelum dan sesudah:**

| | sebelum | sesudah |
|---|---|---|
| sapuan 60 tenggat (`sim_redirect_shadow`) | 21 menyimpan `epc = 0` | **0** |
| papan, `trap_shadow` | `0 0 88 89 88 0 0 88` | **`88 88 88 89 88 88 88 88`** |
| papan, `trap_resume` (handler tak menyentuh epc) | — | **`86 86 27`** — delapan preemption, tiap resume benar, prosesnya masih mencacah |
| `kernel.hasm` proses A | beku di 337 | **14.491 → 28.982** |
| `shell.hasm` pid 0 | beku | **2.682 → 21.797** |

Biayanya **+12 LUT4 dan +1 DFF** di slot HCPU, +15/+1 di slot HDMI — satu bit
keadaan, persis `pc_valid`, dan tidak lebih.

**Caveat, dan ia diukur bukan didiamkan.** Sumber exception di mesin ini adalah
**pulse satu siklus** (`run exc maks = 1`, terukur). Kalau sebuah exception
pernah bersamaan dengan `pc_valid == 0`, ia akan **hilang**, bukan tertunda.
Pada cakupan yang diuji itu tidak pernah terjadi — `syscall_io`, `mem_protect`,
`user_mode`, `shell`, `kernel`, `branch_trap_race` dan sapuan bayangan
semuanya melaporkan **0** siklus exception tertahan, sementara timer tertahan
0/0/0/1/13/3/30. Slot yang di-flush berisi NOP, yang tidak memunculkan apa pun
— tetapi itu penjelasan sesudah pengukuran, bukan pengganti pengukuran, dan
cakupan bukan bukti universal.

Dijaga oleh `rtl/tb/tb_hcpu_trap_redirect_shadow.v` (tujuh pemeriksaan) dan
oleh baris baru di `rtl/tb/tb_hcpu_kernel.v` yang menuntut proses A **masih**
berjalan, bukan sekadar pernah — pemeriksaan yang tak pernah ada, dan itulah
yang menyembunyikan cacat ini selama itu.

#### 3. ~~FLAGS bukan bagian dari konteks proses~~ — DIPERBAIKI 13 September 2026, H-ISA v1.1

**Yang diukur sebelum diperbaiki.** `rtl/programs/trap_flags.hasm` mencetak
**`0`** di papan: perbandingan yang dibuat di mode user tidak selamat melewati
trap, karena handler harus membandingkan `TRAP_CAUSE` dan perbandingannya
menimpa milik user. Dan bukan hanya trap sukarela — sebuah loop yang memuat
satu perbandingan, disapu 60 tenggat timer, **lima di antaranya membalik
cabangnya**, periodik dengan periode sebelas: satu siklus dari sebelas.

**Tiga jalan diperiksa, dan tak satu pun ada di spesifikasi.** §15.1 tidak
menyebut wilayah periferal sama sekali dan keenam belas kata MMIO sudah
terpakai; seluruh mnemonic §6.2, 28 opcode buku dan seluruh enum tidak memuat
satu pun pemindah FLAGS; dan §16.4 berbunyi *"H-ISA v1.0 tidak memiliki model
interrupt"* — spesifikasi tidak punya trap, jadi tidak punya konteks, jadi
tidak pernah menyebut isinya. FLAGS pun tidak sendirian: §4.3 mendaftar PC,
SP, FLAGS, CY dan tak satu pun bisa dibaca ke GPR.

**Yang spesifikasi tetapkan adalah prosedurnya**, §6.0 aturan 2 dan 4 — dan
itulah yang ditempuh.

**Keputusan pemilik, 13 September 2026: H-ISA v1.1.**

| opcode | mnemonic | operasi |
|---|---|---|
| `0x0A` | `FRD` | `GPR[DST] ← FLAGS`, diperluas nol |
| `0x0B` | `FWR` | `FLAGS ← GPR[S1][7:0]` |

Keduanya mengambil slot kosong di blok System & Control, blok yang §6.1 berikan
untuk keadaan mesin. Tak ada nilai opcode lama yang berubah; versi ISA naik,
sesuai aturan 4.

**Konteks proses sekarang lima hal**, bukan empat: enam belas GPR, PC, jendela
memori, dan FLAGS di `PCB+20`. `rtl/programs/shell.hasm` dan
`rtl/programs/flags_ctx.hasm` menyimpannya dengan `FRD` **sebelum kernel
membandingkan apa pun** — enam belas `PUSH` yang membuatnya mungkin — dan
memulihkannya dengan `FWR` tepat sebelum `ERET`.

**Terukur, sebelum dan sesudah:**

| | sebelum | sesudah |
|---|---|---|
| dua proses, pola sendiri-sendiri | tak bisa ditulis — tak ada yang membaca FLAGS | **`sim_flags_ctx`: 0x05 dan 0x0A, keduanya utuh** |
| papan, `flags_board` | — | **`5 10 1 1`** — dua ratus preemption, tiap proses membaca polanya sendiri, keduanya masih berjalan |
| sapuan 60 tenggat, satu perbandingan | 5 cabang terbalik | jalur penyelamatnya ada; disiplin `CMP` lalu cabang tetap dianjurkan |

**Satu cacat ditemukan saat menulisnya, oleh benchnya sendiri.** `FRD` mula-mula
ditaruh sesudah gelung simpan register — dan `pcb_of` serta uji cause sudah
membandingkan sebelum itu. Prosesnya yang menyetel `0x05` membaca `0x0d`, yang
menyetel `0x0a` membaca `0x08`: keduanya membawa perbandingan kernel.
`FRD` sekarang instruksi pertama sesudah enam belas `PUSH`.

**Dan satu ketidaksepakatan lama jadi terlihat.** `rtl/hcpu_pkg.vh` menaruh
`FLAG_LT` di bit 3 dan `hcpu_execute.v` menulisnya pada setiap `CMP`, sementara
§14.1 dulu menyebut bit 3–7 "Reserved" dan `machine.py` menyimpan bit tanda itu
di field bernama `overflow`. Selama FLAGS tak terjangkau, perbedaan itu tak
pernah terlihat; `FRD` memaparkannya pada instruksi pertama. §14.1 dibetulkan
mengikuti RTL (§6.0), dan nama `overflow` yang memegang LT **dilaporkan, tidak
diganti** — itu keputusan pemilik.

Disabotase bertiga dan ketiganya merah: `FRD` mengembalikan nol, `FWR`
diabaikan, dan simpanan konteks dihapus (R3).

#### 4. ~~`STORE` ke `TRAP_EPC` tepat sebelum `ERET` kembali ke epc lama~~ — DIPERBAIKI 13 September 2026

**Jaraknya diukur persis sebelum diperbaiki.** Sebuah handler yang membaca
`TRAP_EPC`, menambah satu, menulisnya kembali, lalu `ERET` — jumlah `NOP` di
antaranya disapu 0 sampai 4, jendela pengamatan 200 siklus:

| jarak | sebelum | sesudah |
|---:|---|---|
| **0 NOP** | trap menyala **15 kali**, instruksi sesudah `SYSCALL` tak pernah tercapai | **1 kali, benar** |
| 1 NOP | benar | benar |
| 2–4 NOP | benar | benar |

Tepat **satu instruksi** adalah seluruh perbedaannya — dan itu sebabnya tidak
ada yang tersandung: `hal_epc_set` diikuti `hal_mode_user`, `hal_timer_arm` dan
enam belas `LOAD` pemulihan, sementara `rtl/programs/trap_flags.hasm` kebetulan
memakai tiga `NOP`. Handler yang ditulis ringkas salah **diam-diam**, dan
gejalanya instruksi yang berulang, bukan pesan kesalahan.

**Perbaikannya bentuk yang sudah ada di berkas itu, enam belas baris di atas
gejalanya.** `rtl/hcpu_trap.v` membawa `prev_at_eret` untuk bahaya yang sama
pada `TRAP_MODE`, dan komentarnya menutup dengan *"the fix is not to require
one"* — lalu hanya `TRAP_MODE` yang mendapatkannya. Sekarang `TRAP_EPC` juga:

```verilog
wire epc_write    = reg_we && (reg_sel == `REG_TRAP_EPC);
wire [`XLEN-1:0] epc_at_eret = epc_write ? reg_wdata : epc;
assign trap_target = eret ? epc_at_eret : vector;
```

**Papan menjawab `1 1 1`** — `rtl/programs/trap_epc.hasm`, tiga ronde pada
jarak nol, satu dan dua instruksi, masing-masing masuk handler tepat sekali.

Biayanya **+20 LUT4 dan +0 DFF** di slot HCPU, +21/+0 di slot HDMI: ia mux di
jalur kembali, bukan register, jadi tidak menambah keadaan sama sekali.

Dijaga dua tingkat: `rtl/tb/tb_hcpu_trap.v` pemeriksaan 18 menanyakan unitnya
(tulisan sekelas siklus dengan `ERET` harus menang), dan
`rtl/tb/tb_hcpu_trap_epc_eret.v` menyapu jaraknya di pipeline penuh. Disabotase
dengan mengembalikan `trap_target` ke `epc`: keduanya merah, baris 0 NOP
kembali ke 15 kali masuk (R3).

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
terhalang top level gabungan, penyimpanan persisten HFS
belum ada 24 opcode, proses dinamis, ASIC
```

Enam lapis berjalan. Silikon dedikasi (ASIC, bukan FPGA) belum dimulai, dan
sebabnya sudah punya nama dan angka — lihat [ROADMAP.md](ROADMAP.md).
