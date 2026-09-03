# Yang belum menyala

Dua jenis: **terhalang** (terbangun, tidak bisa dijalankan) dan **belum ada**.
Keduanya dipisah karena jaraknya ke "menyala" sangat berbeda.

---

## Terhalang — terbangun, tidak bisa dijalankan

### Papan tidak bisa di-flash

Place-and-route **gagal**. Desainnya **159% dari LUT4** papan dan nextpnr
berhenti pada `no BELs remaining to implement cell type 'LUT4'`.

```
LUT4    13.777 / 8.640   159%   ← tidak muat
DFF      4.410 / 6.480    68%
BSRAM       17 /    26    65%
Fmax    tidak terukur — routing tidak selesai, jadi tak ada laporan timing
```

Ia pernah muat, dan angka lamanya jujur saat ditulis. Bisect, satu run sintesis
per komit:

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

Dua jalan keluar, dan pilihannya bukan milik saya:

- **Kecilkan memori instruksi.** Sekarang 4096 kata; loader menulis dari alamat
  64. Memotongnya ke 1024 memotong empat kali lipat.
- **Tulis ulang port tulisnya** agar terinfer bersih ke BSRAM. Lebih tepat kalau
  jembatan itu mau dipertahankan utuh.

Rekamannya ada di header `rtl/fpga/gowin/hcpu_gowin_top.v`, terikat pada **hash
isi RTL** — bukan pada tanggal, dan bukan pada siapa yang ingat memeriksanya.
Sentuh berkas RTL mana pun dan `tests/test_integrity/test_place_and_route.py`
jatuh, meminta pengukuran ulang.

Label: `EH`. Turun dari `CC`, dan itu memang arah yang benar.

### Fmax Kabah top

Belum pernah ditempatkan sama sekali, karena sebab berbeda: **1.665 bit port
melawan 276 IOB**. Ia butuh wrapper yang mempersempit antarmukanya sebelum bisa
ditempatkan. Label: `EH`.

---

## Belum ada

### 26 opcode belum di RTL

70 dari 96 terimplementasi. Yang belum:

```
CALL RET                        panggilan bersarang
VMOV VCMP VDOT VDIST VNORM      vektor
VSCL VRHO VPROJ_K VPROJ_N
VPROJ_Q VPROJ_T
CSUB CHASH CSIGN                codex
HCHK HDCMP HDES HEXMT
HPROJ HSER
JGF JGP JNP PRINTH              lompatan dan cetak
```

`CALL`/`RET` yang paling menghalangi: tanpanya tidak ada subrutin, dan tanpa
subrutin sebuah kernel harus ditulis lurus. `kernel.hasm` memang ditulis lurus.

Label: `AT`.

### HFS dan HOS

Buku menetapkan tumpukan tujuh lapis, dan itu yang menentukan urutan kerjanya:

```
7  Aplikasi          program HC, alat analisis                 ✅
6  HVM / HCPU        eksekusi bytecode (perangkat lunak/keras)  ✅
5  Layanan Hybit     akses HAR, protokol HISAB, daemon pengaman ⬜
4  HFS               sistem berkas yang sadar hybit             ⬜
3  H-Kernel          manajemen proses, memori, dan I/O          ◐  2 dari 4
2  HAL               lapisan abstraksi perangkat keras          ⬜  tak ada berkasnya
1  Perangkat keras   CPU/HCPU, memori, I/O                      ✅
```

Perhatikan lapis 2. **HAL tidak ada sama sekali** — bukan "terancang", tak ada
berkasnya. H-Kernel sekarang berbicara langsung ke MMIO. Selama itu begitu,
setiap papan baru berarti menulis ulang kernelnya.

#### HFS — sistem berkas

Yang buku minta: **penyimpanan guard-on-write**. Setiap tulisan divalidasi
terhadap constraint G1–G4 pada saat menulis, bukan saat membaca. Itu satu dari
empat hal yang buku klaim tidak dimiliki Linux maupun Windows.

Yang menghalangi, berurutan:

| butuh | keadaan |
|---|---|
| penyimpanan blok | **tak ada** — tak ada driver, tak ada media |
| heap | **tak ada** — buku menyebut 64 KB dengan `malloc`/`free`; mesin ini tak punya |
| I/O lewat kernel | **tak ada** — proses user tak bisa menyentuh periferal, dan tak ada syscall I/O |
| `CALL`/`RET` | **belum di RTL** — tanpa subrutin, sistem berkas harus ditulis lurus |
| Guard saat menulis | ✅ **ada** — G1–G4 sudah di RTL, 34 asersi |

Jadi satu-satunya bagian yang sudah siap justru bagian yang menamai HFS.
Sisanya belum.

#### HOS — sistem operasi

Yang buku minta: **manajemen sumber daya**, dengan empat sifat yang secara
eksplisit dibedakan dari Linux dan Windows:

| sifat | keadaan |
|---|---|
| validasi berkas saat menulis (guard-on-write) | butuh HFS |
| penjajaran 18-wide | ✅ ada di mesin — `GPR_COUNT 18`, H-Reg 18×8 = 144 bit |
| HAR sebagai layanan sistem (tingkat kernel) | **belum** — HAR ada di Python, bukan layanan |
| daemon guard (HCHECK periodik) | **belum dijadwalkan** |

Baris terakhir kini paling dekat. Buku memisahkan dua kelas error
(Proposisi IIIH.3.2.1, `DP`):

```
Guard    per-operasi, O(1)        inkonsistensi constraint tiap HCADD/HGRD
HCHECK   periodik, O(n×25)        bit flip, drift akumulatif, HC-00…HC-03
```

Guard sudah operasional di perangkat keras. HCHECK **tidak sepenuhnya**: yang
ada di RTL hanyalah tiga jebakan — `HC-01` indeks ROM tak sah, `HC-02` stack
overflow, `HC-03` underflow. **`HC-00` tidak ada di mana pun**, dan pemindai
periodiknya hanya ada di Python (`src/hijaiyyah/hisa/hcheck.py`). Menjadikannya
daemon justru butuh penjadwal — dan penjadwal itulah yang baru saja ada.

#### Urutan yang masuk akal

1. **`CALL`/`RET`** — tanpa subrutin semuanya ditulis lurus; ini yang paling menghalangi.
2. **Syscall I/O** — melengkapi tanggung jawab ketiga H-Kernel.
3. **HCHECK sebagai daemon** — proses ketiga di penjadwal; tanggung jawab keempat.
4. **HAL** — sebelum papan kedua, bukan sesudah.
5. **Heap** — prasyarat HFS.
6. **HFS**, lalu **HOS**.

Label: `AT` untuk keduanya, dan `AT` yang jujur — tak ada dokumen desain untuk
HFS maupun HOS di pohon ini, hanya baris tabel.

### Yang H-Kernel belum punya

Kernelnya berjalan, dan ruang lingkupnya sempit dengan sengaja:

| ada | belum |
|---|---|
| dua proses tetap | pembuatan proses dinamis |
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
menyala   matematika, bahasa, mesin, sistem operasi, kripto, jembatan (simulasi)
terhalang bitstream papan (159% LUT4), Fmax HCPU, Fmax Kabah top
belum ada 26 opcode, HFS, HOS, proses dinamis, ASIC
```

Lima lapis berjalan. Yang keenam berhenti di gerbang silikon, dan sebabnya
sudah punya nama, komit, dan angka.
