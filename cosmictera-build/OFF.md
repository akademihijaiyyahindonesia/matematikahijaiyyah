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
