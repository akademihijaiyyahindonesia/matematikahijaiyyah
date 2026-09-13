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

Empat operasinya kini utuh dan bernama: `hos_fs_create` dibuat di M4.1, jadi
"berkas ini sudah ada" akhirnya bisa dinyatakan, dan siklus
create → write → read → verify berjalan di papan sebagai `1 0 1 1 1 1 0`
(`rtl/programs/hfs_lifecycle.hasm`). Yang masih hilang tetap satu:

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
terhalang top level gabungan, HFS baca (tanpa CSET), penyimpanan persisten
belum ada 24 opcode, proses dinamis, ASIC
```

Enam lapis berjalan. Silikon dedikasi (ASIC, bukan FPGA) belum dimulai, dan
sebabnya sudah punya nama dan angka — lihat [ROADMAP.md](ROADMAP.md).
