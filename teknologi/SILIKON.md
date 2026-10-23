# Silikon

Dua puluh satu modul Verilog, 3.728 baris, dan satu papan yang akhirnya
menjalankannya.

---

## HCPU — pipeline lima tahap

`rtl/hcpu_*.v`. Fetch, decode, execute, memory, writeback — bentuk yang
lazim, dengan isi yang tidak: `hcpu_codex_alu.v` mengerjakan aljabar
huruf sebagai unit fungsional, dan `hcpu_guard.v` memeriksa guard dalam
satu siklus, bukan sebagai rutin.

| Modul | Kerjanya |
|---|---|
| `hcpu_fetch/decode/execute/memory/writeback` | lima tahap pipeline |
| `hcpu_codex_alu` | aljabar codex 18D |
| `hcpu_guard` | pemeriksa guard, O(1) |
| `hcpu_rom` | ROM 252 byte, 28 entri tersegel |
| `hcpu_hisab` | nibble-packing dan CRC |
| `hcpu_trap`, `hcpu_timer`, `hcpu_mmio` | interupsi, pewaktu, I/O terpetakan |
| `hcpu_uart_rx/tx` | jalur serial |
| `hcpu_forward` | penerusan operand |
| `hcpu_video_timing` | pewaktuan video |

Tiga puluh enam testbench di `rtl/tb/` memeriksanya siklus demi siklus.

---

## Apa yang benar-benar terjadi di papan

**10 September 2026, Tang Nano 20K (GW2AR-LV18QN88C8/I7).** Sebelum tanggal
itu tidak satu pun bitstream proyek ini pernah dinyalakan di silikon.

### HCPU

```
LUT4   14.231 / 20.736   68%
DFF     4.480 / 15.552   28%
BSRAM      17 /     46   36%
Fmax   118,43 MHz
```

UART membalas **23 byte**, dan cocok **byte-per-byte** dengan simulasi:
`112`, lalu `CYCLES=00001B89` — 7.049 siklus, angka yang sama yang dihitung
testbench.

### Dua puluh delapan huruf

`e3_sweep28` mengeksekusi ROM tersegel huruf demi huruf dan mengembalikan
komponen Θ̂ tiap entri. Dibandingkan dengan `MASTER_TABLE` kanonik:
**identik, 28 dari 28.** Ini memenuhi syarat pertama yang
`rtl/mpw/MPW_SHUTTLE_PLAN.md` sebut kritis sebelum tapeout — seluruh entri
ROM terverifikasi di perangkat keras, bukan di simulator.

### Video

1280×720 lewat TMDS pada pasangan diferensial pin 33–40. Satu bitstream
membawa ketiganya sekaligus — video, loader, dan HCPU — dibuktikan dengan
mengirim program lewat kabel saat layar menyala.

Rekaman lengkap tiap program beserta keluarannya:
[`cosmictera-build/PAPAN.md`](../cosmictera-build/PAPAN.md).

---

## Tiga cacat yang hanya papan bisa temukan

Ketiganya lolos 36 testbench RTL — 20 lewat `make -C rtl/tb all`, sisanya dipanggil
langsung dari pytest — dan 6.212 tes Python. Simulasi bukan lalai
— ia secara struktural buta terhadap ketiganya, dan itu justru pelajaran
yang paling mahal dari hari itu.

**Reset yang digerbangi level pin MODE1.** `btn_rst_n` ada di pin 87, yang
papan tahan rendah. Sebagai reset asinkron level-sensitif ia mengunci CPU
selamanya: bitstream terkonfigurasi lalu tidak mengeksekusi apa pun. Muncul
**empat kali di tiga wrapper**. Testbench menggerakkan pin itu tinggi, jadi
tidak pernah melihatnya.

**Memori instruksi kosong di setiap bitstream yang pernah dibangun.**
For-loop pengisi NOP sebelum `$readmemh` membuat yosys membuang readmemh
tanpa peringatan. Tak terlihat selama bertahun-tahun karena `OP_NOP`
kebetulan bernilai `8'h00` — **memori dikosongkan dan memori terisi NOP
adalah bit yang identik.**

**Driver diferensial TMDS tidak pernah ada di bitstream.** `TLVDS_TBUF`
yang di-instantiate tangan tidak selamat: yosys menyisipkan `OBUF`-nya
sendiri, netlist jadi `TLVDS_TBUF → OBUF → pad` yang mustahil, dan nextpnr
membuang keempatnya. Perbaikannya menghapus primitif, bukan menambahnya.

---

## Yang belum muat

HCPU dan Ka'bah sebagai **satu top level**: diukur 105%, lewat 960 sel.
Dan rinciannya membatalkan tiga penghematan yang pernah direncanakan —
`hcpu_execute` dan `hijaiyyah_sponge` adalah 91% desain di antara keduanya,
sementara mengecilkan memori instruksi 4096→1024 hanya menghemat 15 sel dan
berbagi satu UART tidak masuk empat belas besar pemakai LUT.

Label: **AT**. Peta jalannya di
[`cosmictera-build/ROADMAP.md`](../cosmictera-build/ROADMAP.md) Fase 4.

## Jalur ASIC

`rtl/mpw/` — rencana shuttle MPW, makro SRAM sky130, dan laporan sintesis.
Label: **AT** — pemetaan sel standar belum dimulai, dan angka µm² sejati
baru bisa didapat dengan liberty terpasang.

---

**Label.** HCPU di FPGA: **CC** — dieksekusi di papan, keluarannya cocok
dengan referensi. Tabel 28 huruf di silikon: **CC**. ASIC dan top level
gabungan: **AT**.
