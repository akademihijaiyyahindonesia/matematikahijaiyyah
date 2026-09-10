# Yang belum menyala

Dua jenis: **terhalang** (terbangun, tidak bisa dijalankan) dan **belum ada**.
Keduanya dipisah karena jaraknya ke "menyala" sangat berbeda.

---

## Terhalang — terbangun, tidak bisa dijalankan

### Papan 9K: bukan diperbaiki, diganti

Tang Nano 9K adalah papan target sampai commit sebelum ini. Place-and-route
di sana **gagal**: desainnya **162% dari 8.640 LUT4** papan itu dan nextpnr
berhenti pada `no BELs remaining to implement cell type 'LUT4'`.

```
LUT4    14.005 / 8.640   162%   ← tidak muat di 9K
DFF      4.480 / 6.480    69%
BSRAM       17 /    26    65%
```

Ia pernah muat di 9K, dan angka lamanya jujur saat ditulis. Bisect, satu run
sintesis per komit, terhadap budget 9K:

| komit | | LUT4 | |
|---|---|---:|---|
| `ae83fd2` | perkakas dan bitstream pertama | 6.753 (78%) | muat |
| `096e392` | mode supervisor | 6.740 (78%) | muat |
| **`348e9c6`** | **jalur boot** | **13.644 (157%)** | **gagal** |
| `e5bd781` | satu huruf satu instruksi | 13.710 (158%) | gagal |
| `a606ed5` | proteksi memori | 13.800 (159%) | gagal |
| `34ca28c` | syscall | 13.817 (159%) | gagal |

**Satu komit yang melakukannya.** Jalur boot menambah tiga baris port tulis
loader ke memori instruksi, dan itu mengubah larik hanya-baca menjadi memori
baca-tulis: BSRAM 4 → 17, sisanya jatuh ke fabric — **+5.015 LUT4, +2.666 DFF**.

Jembatannya nyata dan bench-nya lulus. **Biayanya yang tidak pernah diukur**,
karena lima komit mendarat setelah pengukuran dan tak satu pun menjalankan ulang
tools.

Ada dua jalan yang tidak mengubah papan — kecilkan memori instruksi (4096 kata
→ 1024), atau tulis ulang port tulisnya agar terinfer bersih ke BSRAM — dan
satu yang mengubahnya. Yang diambil: **ganti papan.** Tang Nano 20K
(GW2AR-LV18QN88C8/I7) punya 20.736 LUT4, bukan 8.640, dan desain yang sama
tidak perlu dikecilkan sama sekali untuk masuk ke sana — lihat
[ON.md](ON.md#6--jembatan-papan) untuk angka rutenya. `no BELs remaining`
tetap dikutip di atas karena itu pesan nyata nextpnr terhadap 9K, bukan
klaim tentang keadaan sekarang.

Rekamannya ada di header `rtl/fpga/gowin/hcpu_gowin_top.v`, terikat pada **hash
isi RTL** — bukan pada tanggal, dan bukan pada siapa yang ingat memeriksanya.
Sentuh berkas RTL mana pun dan `tests/test_integrity/test_place_and_route.py`
jatuh, meminta pengukuran ulang — mekanisme yang sama yang menemukan 9K basi
sekarang menjaga angka 20K yang menggantikannya.

Label: `CC` di 20K. 9K sendiri ditinggalkan, bukan diperbaiki — lihat
[ROADMAP.md](ROADMAP.md) untuk apa yang masih terbuka (Ka'bah berbagi chip
yang sama, terutama).

### Fmax Kabah top di Tang Nano 9K

Bukan lagi soal port. `hijaiyyah_kabah_gowin_top.v` menyempitkan antarmukanya
ke 10 pin dan itu menyelesaikan **1.665 bit port vs 276 IOB** di kedua
papan — lihat [ON.md](ON.md#5--kripto-kabah). Yang tersisa di 9K sekarang
sebabnya sama seperti HCPU di atas: **LUT4**, bukan pin.

```
LUT4    12.102 / 8.640   140%   ← tidak muat
DFF      1.963 / 6.480    30%
Fmax    tidak ada — nextpnr: "Unable to find legal placement... after
        54.925.681 attempts" — tidak sampai routing, sama seperti HCPU di atas
```

Sebabnya sudah tercatat sebelum wrapper ini ada: `hijaiyyah_kabah_top`
sendirian sudah **94%** dari 9K di SLICE_BYTES=25. Menambah UART RX/TX dan
FSM umpan/dump di atas itu tidak punya tempat lagi.

Di GW2AR-18C (Tang Nano 20K) desain yang sama muat dan terrout: **58% LUT4,
117,91 MHz, `gowin_pack` sukses**. 9K bukan papan yang cukup besar untuk
Ka'bah plus jembatan UART-nya sekaligus; 20K sudah.

Label: `EH` untuk 9K. Turun dari `AT` — dulu tidak bisa ditempatkan sama
sekali, sekarang gagal sesudah tempat, penyebabnya bernama dan bisa diukur.

---

## Belum ada

### 24 opcode belum di RTL

72 dari 96 terimplementasi. Yang belum:

```
VMOV VCMP VDOT VDIST VNORM      vektor
VSCL VRHO VPROJ_K VPROJ_N
VPROJ_Q VPROJ_T
CSUB CHASH CSIGN                codex
HCHK HDCMP HDES HEXMT
HPROJ HSER
JGF JGP JNP PRINTH              lompatan dan cetak
```

`CALL`/`RET` dulu yang paling menghalangi dan **sudah tidak**: keduanya kini di
perangkat keras, di 0x2E/0x2F tempat spec memesannya. Sisanya vektor dan codex —
tak ada yang menghalangi HFS atau HOS.

Label: `AT`.

### HFS dan HOS

Buku menetapkan tumpukan tujuh lapis:

```
7  Aplikasi          program HC, alat analisis                 ✅
6  HVM / HCPU        eksekusi bytecode (perangkat lunak/keras)  ✅
5  Layanan Hybit     akses HAR, protokol HISAB, daemon pengaman ◐  HAR ada, HISAB belum layanan
4  HFS               sistem berkas yang sadar hybit             ◐  tulis ada, baca setengah
3  H-Kernel          manajemen proses, memori, dan I/O          ✅  4 dari 4
2  HAL               lapisan abstraksi perangkat keras          ✅
1  Perangkat keras   CPU/HCPU, memori, I/O                      ✅
```

Enam dari tujuh lapis kini punya sesuatu yang nyata. Yang tersisa, berurutan:

#### HFS — dua celah bersisa, keduanya bernama

Jalur tulis (`hos_fs_write` di `rtl/programs/hos.hasm`) nyata: `HGRD`
dijalankan sebelum berkomitmen, vektor korup ditolak. Dua hal masih hilang:

| butuh | keadaan |
|---|---|
| `CSET` (tulis satu komponen GPR ke H-Reg) | **tak ada di ISA** — `CGET` (0x44) hanya membaca. Tanpa ini, `hos_fs_read` tak bisa merekonstruksi H-Reg hidup dari kata tersimpan, hanya penunjuk ke 18 kata mentah |
| penyimpanan persisten | **belum diverifikasi** — HFS sekarang murni RAM data (`0xE00`+), hilang saat reset. Tang Nano 20K punya jalur SDRAM/PSRAM di chipdb-nya (`IO_sdram_dq[0:31]` muncul saat PNR), tapi belum dipastikan papan fisiknya benar-benar memasang chip PSRAM |

`CSET` adalah keputusan desain ISA (menambah opcode, jalur RTL, bench, PNR
ulang) — di luar cakupan kerja hari ini. Verifikasi PSRAM Tang Nano 20K adalah
pertanyaan perangkat keras yang bisa dijawab lebih cepat.

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
terhalang Fmax Kabah top (9K), HFS baca (tanpa CSET), penyimpanan persisten
belum ada 24 opcode, proses dinamis, ASIC
```

Enam lapis berjalan. Silikon dedikasi (ASIC, bukan FPGA) belum dimulai, dan
sebabnya sudah punya nama dan angka — lihat [ROADMAP.md](ROADMAP.md).
