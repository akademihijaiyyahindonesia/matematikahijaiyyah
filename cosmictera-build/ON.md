# Yang menyala

Enam lapis. Setiap baris menyebut **perintahnya**, **tempatnya**, dan **apa yang
gagal kalau ia rusak** — karena daftar tanpa itu hanya klaim.

---

## 1 — Matematika: dasarnya

| menyala | apa persisnya | bukti |
|---|---|---|
| Master Table | 28 huruf, nilai kanonik dari PDF bersegel | `src/hijaiyyah/core/master_table.py` |
| Aljabar monoid | closure dibuktikan, bukan disampel | `tests/test_algebra/` — 15 tes |
| Guard G1–G4 + T1–T2 | deteksi korupsi vektor, **93,1%** langit-langit | `rtl/hcpu_guard.v`, 34 asersi |
| Teorema | suite penuh | `tests/test_theorems/` |

**93,1% bukan kegagalan menuju 100%.** N/K/Q dan agregatnya tertutup penuh; Θ̂
hanya 11% karena ρ aditif — batas atas berhingga apa pun akan merusak closure —
dan H\* nol karena ia indikator non-geometrik (ID.1.3 di buku). Rinciannya di
[`matematika-hijaiyyah/GUARD.md`](../matematika-hijaiyyah/GUARD.md).

Label: `VF` untuk closure, `CC` untuk cakupan guard.

---

## 2 — Bahasa dan perkakas

| menyala | apa persisnya | bukti |
|---|---|---|
| HVM | mesin virtual, lima komponen | `src/hijaiyyah/vm/`, 45 tes |
| HASM | perakit `.hasm` → kata mesin | `src/hijaiyyah/hisa/assembler.py`, 16 tes |
| HC / HCC | bahasa dan kompilator (**parsial**) | `src/hijaiyyah/compiler/`, 59 tes |
| HAR | registri alfabet (**parsial**) | `src/hijaiyyah/har/`, 15 tes |
| LSP + REPL | `python3 -m hijaiyyah repl` | `src/hijaiyyah/lsp.py`, `cli.py` |
| Bahasa | 102 tes | `tests/test_language/` |

HCC dan HAR ditulis **parsial** di sini dengan sengaja: keduanya berjalan dan
diuji, tapi belum menutup spesifikasinya sendiri. Lihat
`docs/hybit_pipeline_spec.md`.

Label: `CC`.

---

## 3 — Mesin: H-ISA dan HCPU

| menyala | apa persisnya | bukti |
|---|---|---|
| Pipeline HCPU | fetch → decode → execute → mem → writeback | `rtl/hcpu_top.v` |
| Opcode | **72 dari 96** terimplementasi di RTL | `RTL_IMPLEMENTED` di `src/hijaiyyah/hisa/opcodes.py` |
| Opcode huruf | **28** (`0xE0`–`0xFB`), dijalankan di pipeline | `rtl/tb/tb_hcpu_letters.v`, `rtl/programs/letters.hasm` |
| Codex ALU | HCADD, HNRM2, HDIST | `rtl/hcpu_codex_alu.v`, 6 asersi |
| Hisab | penyapuan 28 huruf, 124 asersi | `rtl/hcpu_hisab.v` |
| Interlock | load-use, store-load, **termasuk POP** | `rtl/hcpu_decode.v` |
| Stack perangkat keras | 256 entri, LIFO, PUSH tanpa register basis | `rtl/hcpu_memory.v` |
| **Subrutin** | `CALL`/`RET`, stack kembali 32 tingkat terpisah | `rtl/tb/tb_hcpu_subroutine.v`, `rtl/programs/subroutine.hasm` |
| UART TX + RX | 115200 baud dari 27 MHz | `rtl/hcpu_uart_*.v` |
| Timer | pencacah bebas + satu compare | `rtl/hcpu_timer.v` |

**Satu huruf adalah satu instruksi utuh.** Itu inti resepnya: `0xE0`–`0xFB`
mengindeks ROM codex langsung di tahap Execute, jadi perintah tidak perlu
ditulis sebagai deretan angka.

Sampai `f57793e` klaim itu **salah di perangkat keras**, dan tidak ada yang
mengatakannya: tak satu pun bench atau program pernah menjalankan salah satu
dari dua puluh delapan. `RTL_IMPLEMENTED` mendaftarkannya, tapi himpunan itu
sebuah **deklarasi, bukan pengukuran**. Penyebabnya `default:` kedua di tengah
`case` codex — iverilog memilih yang akhir, jadi setiap huruf menulis nol,
sementara penafsir Python tetap menghitung benar. `tb_hcpu_letters` sekarang
mengadu keduanya: 112 untuk Ba+Sin+Mim lewat jalur huruf, angka yang sama yang
sudah dibuktikan jalur HLOAD/HCADD.

Label: `CC`.

---

## 4 — Sistem operasi: enam prasyarat, lalu kernelnya

| menyala | apa persisnya | bukti |
|---|---|---|
| 1 Bitwise | `0xB0`–`0xBA` | `rtl/hcpu_execute.v` |
| 2 UART RX + timer | dua sumber level-sensitif | `rtl/tb/tb_hcpu_uart_rx.v`, `tb_hcpu_timer.v` |
| 3 Trap | **6 penyebab**, prioritas indeks terendah | `rtl/hcpu_trap.v`, `tb_hcpu_trap.v` |
| 4 Mode supervisor | jendela periferal tertutup bagi user | `rtl/hcpu_execute.v` |
| 5 Proteksi memori | jendela `[base, limit)` per proses | `rtl/hcpu_mmio.v` |
| 6 Syscall | `0x09`, non-maskable, epc menunjuk dirinya | `rtl/programs/syscall.hasm` |
| **I/O lewat kernel** | `PRINT` istimewa; user meminta, supervisor mencetak | `rtl/tb/tb_hcpu_syscall_io.v` |
| **HOS** | heap, HFS guard-on-write, HAR sebagai layanan kernel | `rtl/tb/tb_hcpu_hos.v` |
| **H-Kernel** | **tiga proses, dipreempt, register masing-masing** | `rtl/programs/kernel.hasm` |

H-Kernel berjalan di **dua tempat**: penafsir Python dan pipeline RTL.

```
make -C rtl/tb sim_kernel
  A (dipreempt)  B (menyerah, kelipatan bersih 100)  C (daemon: sapuan, 0 gagal)
```

Angka B itu buktinya. Kedua proses menghitung di **R1** — A menambah 1, B
menambah 100 — jadi total B tetap kelipatan bersih 100 **hanya jika** R1-nya
tak pernah sekali pun memegang nilai A. Itu definisi register privat, diukur.

A dipreempt timer dan B menyerah lewat `SYSCALL`, jadi kedua jalur masuk trap
teruji sekaligus: tanpa `epc` dimajukan untuk cause 5, B akan mengulang
`SYSCALL`-nya sendiri selamanya.

Ruang lingkupnya jujur, dan buku menetapkan ukurannya. H-Kernel di sana punya
**empat** tanggung jawab — proses, memori, I/O, daemon guard. **Keempatnya
berjalan:**

| tanggung jawab | keadaan |
|---|---|
| proses | tiga slot tetap, round-robin — tanpa pembuatan dinamis |
| memori | jendela `[base, limit)` per proses — tanpa heap |
| I/O | **ada, dimediasi** — `PRINT` istimewa, keluaran lewat `SYSCALL` |
| daemon guard | proses C: menyapu 28 huruf lewat `HLOAD`+`HGRD` tiap giliran |

Klaim lama di baris I/O salah, dan kenyataannya lebih buruk daripada yang
ditulis: `PRINT` **tidak** istimewa, jadi mode user menulis ke jalur serial
tanpa perantara — bukan *tanpa* I/O, tapi I/O *tanpa wasit*. Sekarang ia
istimewa dan keluaran melewati kernel.

Yang tersisa bukan tanggung jawabnya, melainkan skalanya: tiga slot tetap,
tanpa pembuatan proses dinamis, dan **stack alamat-kembali tidak ikut
disimpan** saat pergantian konteks. Rinciannya di [OFF.md](OFF.md).

Label: `CC`.

### HOS: heap, HFS, HAR

Buku memberi HOS empat sifat yang secara eksplisit dibedakan dari Linux dan
Windows. Keempatnya kini nyata, dengan batasnya masing-masing dinamai:

| sifat | keadaan |
|---|---|
| guard-on-write | ✅ `hos_fs_write` menolak vektor korup sebelum tersimpan |
| penjajaran 18-wide | ✅ `HREG_W` = 144 bit = 18×8 |
| HAR tingkat kernel | ✅ `hos_har_get`, titik masuk bernama, bukan indeks ROM mentah |
| daemon guard | ✅ proses C di `kernel.hasm`, sudah sejak H-Kernel |

**Heap** (`hos_alloc`/`hos_free`) adalah free-list first-fit dengan
pemisahan blok, header 2-kata, penanda pakai `0xFFFFFFFF` (alamat yang
mustahil nyata, `DATA_ADDR_W`=12 bit) menolak double-free alih-alih diam-diam
merusak daftar bebas.

**HFS** membaca "sistem berkas yang sadar hybit" secara harfiah: satu berkas
adalah satu vektor hybit 18-komponen, dan `hos_fs_write` menjalankan `HGRD`
sebelum berkomitmen — vektor korup (indeks ROM 31, vektor uji yang sama
dipakai setiap bench guard) ditolak, tak pernah tersimpan. Jalur bacanya
**setengah**, dan itu batas perangkat keras, bukan pilihan desain: `CGET`
membaca satu komponen H-Reg ke GPR, tapi **tidak ada `CSET`** — tidak ada
instruksi yang menulis nilai GPR ke komponen H-Reg. `hos_fs_read` karena itu
mengembalikan penunjuk ke 18 kata mentah, bukan H-Reg hidup.

**HAR** sebagai layanan: `hos_har_get(index)` memberi titik masuk bernama
dan stabil, bukan mengharuskan pemanggil tahu pengindeksan ROM sendiri —
tepat perbedaan yang buku klaim atas Linux dan Windows. Dibangun 28 kali
`HLOAD` bercabang compile-time, bukan satu `HLOAD` terindeks-register: field
ROM-nya immediate, `rom_addr = is_letter ? letter_index : id_imm[...]` di
`hcpu_execute.v` tak pernah membaca register untuk itu.

Membangun ini menemukan dua celah lagi. Pertama, `HLOAD H0, Rn` **dulu bisa
dirakit** dan diam-diam selalu memuat indeks ROM 0 — assembler menolaknya
sekarang, dan `rtl/programs/test_guard.hasm` (ada sejak lama, tak pernah
benar-benar dijalankan dan diperiksa) ternyata mencetak 0, bukan 28, karena
persis bug ini. Kedua, **FLAGS tidak punya write-through** yang sudah dimiliki
GPR dan H-Reg — `CMP` lalu satu instruksi lalu `JNE` bisa membaca hasil basi
satu siklus, dan `hos_alloc` adalah kode pertama di seluruh repositori yang
punya jarak itu (semua `CMP`-lalu-cabang lain berdampingan langsung).
Keduanya di [CHECKLIST.md](CHECKLIST.md) dengan rincian penuh.

Label: `CC`. Bukti: `rtl/tb/tb_hcpu_hos.v`, `tests/test_integrity/test_hos.py`
(30 tes).

---

## 5 — Kripto Ka'bah

| menyala | apa persisnya | bukti |
|---|---|---|
| Spons | 25×64 = 1600 bit, rate 128 B, kapasitas 576 | `rtl/hijaiyyah_sponge.v` |
| Permutasi | 28 ronde = 7 CIRCUIT × 4 TAWAF | `rtl/hijaiyyah_rotate_core.v` |
| S-box + router | 28 huruf | `rtl/hijaiyyah_sbox*.v` |
| Gerbang Jamrah | mode gerbang | `rtl/hijaiyyah_jamrah_gate.v` |
| Lapis 3 (HMAC-SHA256) | **satu-satunya pemikul keamanan** | `src/hijaiyyah/crypto/kabah.py` |

**Hanya lapis 3 yang memikul keamanan**, dan ia **tidak ada di RTL**. Empat
lapis lain adalah struktur, bukan jaminan. Menyebut sistem ini "aman" karena
ada lima lapis adalah salah membaca susunannya.

Throughput terukur, dan hambatannya bukan yang diduga:

```
deserialiser   8,00 clock/byte   ← hambatan
sponge (25)    2,42 clock/byte
sistem        10,42 clock/byte = 2,59 MB/s pada 27 MHz
```

Biayanya **dijumlah, bukan disembunyikan**: permutasi menghentikan aliran, jadi
deserialiser bit-serial 8 clock/byte menentukan hasilnya.

Label: `CC` untuk angka, `EH` untuk ketahanan kriptanalisis.

### Wrapper papan Ka'bah: antarmuka 1.665 bit jadi 10 pin

`hijaiyyah_kabah_top` sendiri tak pernah bisa jadi top level papan — 1.665
bit port, dan `out_state` sendirian 1.600 bit (96%) darinya, satu-satunya
pemakainya adalah perbandingan testbench sendiri. `hijaiyyah_kabah_gowin_top.v`
adalah wrapper yang menyempitkannya, persis seperti `hcpu_gowin_top` untuk
HCPU: `out_state` tetap internal (diakses lewat hierarki, seperti biasa), dan
yang keluar ke pin papan hanya clk, reset, UART RX/TX, 6 LED — **10 pin**.

Protokolnya: host kirim 128 byte lewat UART (satu blok rate penuh), wrapper
mengembalikan 200 byte (`out_state`, MSB dulu). `load` menyala sekali saja
sesudah reset, jadi host yang terus mengirim blok mendapat penyerapan
multi-blok sungguhan, bukan 128 byte yang di-hash ulang terisolasi tiap kali.

Diukur 4 September 2026, direproduksi 5 September 2026 lewat
`make -C rtl/fpga/gowin kabah_bitstream` (bukan lagi command manual),
yosys 0.68 (`-nodsp`) → nextpnr-himbaechel 0.11.1 → `gowin_pack`,
GW2AR-LV18QN88C8/I7 (Tang Nano 20K, papan target — lihat [OFF.md](OFF.md)
untuk kenapa 9K ditinggalkan):

```
IOB     10 / 384    2%
LUT4    12.102 / 20.736   58%
Fmax    117,91 MHz, terrout, bitstream 4,6 MB
```

Fingerprint RTL-nya sendiri, terpisah dari fingerprint HCPU — lihat
`KABAH_FINGERPRINTED` di `tests/test_integrity/test_place_and_route.py`.

Diverifikasi bukan lewat `bit_in`/`out_state` langsung, tapi lewat framing
UART sungguhan (start bit, 8 bit data, stop bit) di `tb_hijaiyyah_kabah_gowin_top.v`
— dua blok 128 byte berturut-turut tanpa reset di antaranya, cocok 400/400
byte dengan `cube.py`. Testbench itu menemukan bug nyata sebelum lolos:
`tx_data` balapan dengan `dump_idx` pada tepi clock yang sama, jadi byte
pertama dari setiap dump selalu terlewat.

Label: `CC`. Bukti: `rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v`,
`rtl/tb/tb_hijaiyyah_kabah_gowin_top.v`,
`tests/test_integrity/test_place_and_route.py`.

---

## 6 — Jembatan papan

| menyala | apa persisnya | bukti |
|---|---|---|
| Loader | program masuk lewat kabel, bukan resintesis | `rtl/programs/loader.hasm` |
| Format kawir | 4 byte cacah + 4N byte, MSB dulu | `rtl/scripts/send_program.py` |
| Bench boot | tiga kata mendarat di 64, 65, 66 lalu berjalan | `rtl/tb/tb_gowin_loader.v` |
| Wrapper papan | 27 MHz, UART pada pin papan | `rtl/fpga/gowin/hcpu_gowin_top.v` |
| **Bitstream, Tang Nano 20K** | **muat, terrout, Fmax terukur** | `rtl/fpga/gowin/Makefile`, `hcpu_gowin.cst` |

Ini menyala **dalam simulasi, dan sekarang di bitstream juga**. Diukur ulang
7 September 2026 (rtl/hcpu_video_timing.v bergabung ke set sumber yang
di-fingerprint, memaksa pengukuran ulang), yosys 0.68 (`-nodsp`) →
nextpnr-himbaechel 0.11.1 → `gowin_pack`, GW2AR-LV18QN88C8/I7 (Tang Nano 20K):

```
LUT4    13.969 / 20.736   67%
DFF      4.453 / 15.552   28%
BSRAM       17 /     46   36%
Fmax    114,65 MHz (PASS pada batas 12,00 MHz)
```

Papan target sampai commit sebelumnya adalah Tang Nano 9K, yang desain ini
**tidak muat** (161% dari 8.640 LUT4) — lihat [OFF.md](OFF.md) untuk bisect
komit yang membuatnya tumbuh sebesar itu. Bukan diperbaiki di 9K; dipindah ke
papan dengan LUT4 lebih besar.

`make -C rtl/fpga/gowin bitstream` belum berarti "sudah dinyalakan di
perangkat keras nyata" — `gowin_pack` sukses dan hash RTL terikat di header
`hcpu_gowin_top.v`, tapi belum ada papan fisik yang benar-benar di-flash dan
dibaca lewat serial sungguhan. Itu langkah berikutnya, di
[ROADMAP.md](ROADMAP.md).

Label: `CC` untuk sintesis+PNR+pack; `AT` untuk flash ke papan fisik.

---

## Menjalankan semuanya

```bash
python3 -m pytest -q          # 4.570 lulus, 0 dilewati
make -C rtl/tb all            # 253 asersi, 20 bench, 0 gagal
make lint && make typecheck   # ruff, mypy
```
