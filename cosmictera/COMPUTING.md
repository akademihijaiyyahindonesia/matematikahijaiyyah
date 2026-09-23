# Cosmictera Computing — apa itu, secara program

`README.md` menjelaskan **CosmicTera** sebagai racikan kriptografis: bahan
standar (GF(2⁸), spons Keccak, HMAC-SHA256), diracik beda. Itu satu bagian.
**Cosmictera Computing** adalah nama yang lebih besar — bukan cipher-nya
saja, tapi **seluruh komputasi nyata yang repositori ini bangun**: satu CPU
sungguhan, satu cipher, satu tumpukan tujuh lapis di atasnya, dan sekarang
satu jaringan terlatih yang ternyata dibangun dengan disiplin yang sama.
Dokumen ini tidak menambah konsep baru — ia menunjuk ke program yang sudah
ada, satu per satu, supaya "Cosmictera Computing" berhenti jadi istilah dan
mulai jadi daftar berkas yang bisa dijalankan.

Tidak ada satu proses pun yang menyatukan keempatnya secara administratif.
Yang menyatukan adalah **disiplin yang sama, ditemukan berulang kali di
bagian yang ditulis pada waktu berbeda** — angka dihitung dari konstanta
nyata, bukan diasumsikan; label kejujuran (`VF`/`CC`/`DP`/`EH`/`AT`,
[`RULES.md` R2](RULES.md)) ditempel pada keadaan SEKARANG, bukan pada
tujuan; dan setiap sisi diperiksa dengan cara yang bisa dijalankan ulang,
bukan dipercaya.

---

## Empat program, bukan empat proyek

### 1. HCPU — CPU sungguhan, dua wujud yang harus setuju

**Yang berjalan:** `rtl/hcpu_top.v` (RTL, dijalankan di Tang Nano 20K —
68% LUT4, Fmax 84,26 MHz pasca-perutean, UART cocok byte-per-byte dengan
simulasi, [`PAPAN.md`](../cosmictera-build/PAPAN.md)) dan
`src/hijaiyyah/hisa/machine.py` (interpreter Python, `HISAMachine`) —
dua mesin yang HARUS memberi hasil identik pada program yang sama. Ini
bukan slogan: `hisa/machine.py`'s sendiri punya batas eksplisit soal di
mana keduanya BOLEH beda (komentar `REG_COUNTER`: interpreter tidak
memodelkan waktu pipeline, jadi cacah clock tidak dibandingkan) dan di
mana mereka TIDAK BOLEH beda (register, memori, guard, trap — semua
diperiksa paritas).

**Cara memeriksa:** `python3 -m pytest tests/test_integrity/` (paritas
RTL/interpreter), `make -C rtl/tb all` (408 asersi, 39 testbench, Icarus
Verilog, siklus demi siklus).

**Tampilan — dari timing generator ke layar sungguhan.**
`rtl/hcpu_video_timing.v`: penghitung hsync/vsync/data-enable yang
diparameterkan, diverifikasi terhadap standar VESA 640x480@60Hz yang
diterbitkan (800 piksel/baris, 525 baris/frame, hsync 96 klik di offset
656 — dihitung ulang di `rtl/tb/tb_hcpu_video_timing.v`, `make -C rtl/tb
sim_video_timing`). Di papan ia berjalan dengan parameter 1280x720:
`rtl/fpga/gowin/hcpu_hdmi_top.v` mengirim TMDS lewat pasangan pin 33–40,
dan satu bitstream membawa video, loader, dan HCPU sekaligus — dibuktikan
dengan mengirim `e3_sweep28` lewat kabel saat layar menyala dan menerima
28 nilai yang sama ([`PAPAN.md`](../cosmictera-build/PAPAN.md)).

**Wrapper loader ke papan sungguhan, dan padanan mass-mock-nya di host.**
`rtl/fpga/gowin/hcpu_gowin_top.v` adalah SATU wrapper (10 pin: `clk_27m`,
`btn_rst_n`, `uart_rxd`, `uart_txd`, `led[5:0]`) yang bisa dibakar dengan
program APAPUN — `make bridge` membakarnya dengan `loader.hasm` khusus,
setelah itu bitstream-nya berhenti jadi satu program dan menjadi "yang
menerima program apapun lewat kabel." `make send PORT=... PROG=...`
mengirim program itu ke papan sungguhan yang sedang menjalankan loader,
dari MacBook ini, lewat `rtl/scripts/send_program.py`.

`nui/freeze.py`'s `freeze_load()` adalah PADANAN wrapper yang sama,
di-mass-mock supaya jalan tanpa papan sama sekali: `LOADER_HASM`-nya
adalah **berkas yang sama persis** yang `make bridge` bakar (dicek
langsung, bukan diasumsikan), dan `mock_wire()` menghasilkan byte yang
SAMA persis dengan yang `make send`'s `send_program.py` kirim ke kabel
sungguhan (dicek byte-demi-byte). Bedanya cuma satu: `HISAMachine.rx_queue`
— list Python biasa di RAM MacBook ini — berdiri di tempat kabel
USB-serial dan RAM papan yang sesungguhnya. Protokolnya sama; papannya
tidak perlu ada untuk mengujinya.

**Cara memeriksa:** `make -C rtl/fpga/gowin bridge` (papan sungguhan,
perlu Tang Nano 20K tersambung, lalu `make send PORT=... PROG=...`) versus
`pytest tests/test_ai/test_nui_freeze.py -k "bridge or send"` (mass-mock,
tanpa papan, < 0,15 detik).

### 2. Ka'bah — cipher CosmicTera, racikan bukan primitif baru

**Yang berjalan:** `src/hijaiyyah/crypto/cube.py` (kubus 25×64 bit, rate/
capacity sebagai geometri) + `sbox_logic.py` (S-box dua wujud: tabel 274
LUT4 vs logika 76 LUT4, HARUS identik di 256 masukan) + `hashing.py`/
`signing.py` (lapis 3, HMAC-SHA256 — satu-satunya pemikul keamanan,
[`RULES.md` R10](RULES.md)). Jalur nyatanya, bit ke segel, ada di
[`CONCRETE.md`](CONCRETE.md); mekanismenya di [`SYSTEM.md`](SYSTEM.md).

**Cara memeriksa:** `rtl/tb/tb_hijaiyyah_kabah_top.v` (3.069 bit mentah →
segel, jejak nyata) dan `python3 -m pytest tests/test_integrity/test_kabah*.py`.

### 3. Tumpukan tujuh lapis — apa yang HCPU dan Ka'bah layani

```
7  Aplikasi          program HC, alat analisis                 ✅
6  HVM / HCPU        eksekusi bytecode (perangkat lunak/keras)  ✅
5  Layanan Hybit     akses HAR, protokol HISAB, daemon pengaman ◐
4  HFS               sistem berkas yang sadar hybit             ◐
3  H-Kernel          manajemen proses, memori, dan I/O          ✅
2  HAL               lapisan abstraksi perangkat keras          ✅
1  Perangkat keras   CPU/HCPU, memori, I/O                      ✅
```

(Tabel persis [`cosmictera-build/OFF.md`](../cosmictera-build/OFF.md#hfs-dan-hos)
— enam dari tujuh lapis nyata; dua celah HFS/Layanan Hybit dinamai di sana,
bukan disembunyikan.) Bukan paket Python terpisah — H-Kernel dan HOS adalah
program HASM sungguhan (`rtl/programs/kernel.hasm`, `rtl/programs/hos.hasm`),
dijalankan lewat mesin yang sama yang menjalankan segalanya di sini:
`hisa/machine.py` (interpreter) dan RTL (`rtl/hcpu_*.v`) berdampingan.

**Cara memeriksa:** `python3 -m pytest tests/test_integrity/test_hkernel.py
tests/test_integrity/test_hos.py`.

### 4. NUI — lapisan terbaru, disiplin yang sama ditemukan lagi

**Yang berjalan:** `src/hijaiyyah/nui/` — `atom.py` (satu alamat, tiga
sumber independen setuju), `clockwork.py`/`rack.py` (mekanisme berurutan,
bukan LLM), `freeze.py` (protokol kabel loader dipalsukan, disiplin
"bit → clock → X" yang sama dengan `SYSTEM.md`'s "Lipatan," ditemukan
bukan disalin — lihat [`../NUI/ROADMAP.md`](../NUI/ROADMAP.md#kenapa-nui-ada-di-rancangan-cosmictera-computing)),
`model.py`/`train.py`/`multitask.py` (jaringan terlatih sungguhan, bobot
dan angka terukur, bukan persona LLM — itu `src/hijaiyyah/ai/`, hal yang
berbeda).

**Cara memeriksa:** `python3 NUI/pipeline.py --quick`,
`python3 -m pytest tests/test_ai/test_nui*.py`.

---

## Apa yang benar-benar menyatukan keempatnya

Bukan satu `import` bersama, bukan satu proses yang memanggil keempatnya.
Yang menyatukan adalah **aturan yang sama berlaku di keempatnya**, ditulis
satu kali di [`RULES.md`](RULES.md) dan ditemukan taat padanya di bagian
yang ditulis bertahun kemudian tanpa merujuknya:

| Aturan | Di Ka'bah/HCPU | Di NUI |
|---|---|---|
| Angka dihitung dari konstanta nyata (R4/R12) | `CONCRETE.md`: 9,66 clock/byte dijelaskan dari `CLK_HZ`/spons, bukan diasumsikan | `freeze.py`: `wire_seconds`/`clocks_per_uart_bit` dihitung dari `hcpu_uart_rx.v`'s `CLK_HZ`/`BAUD` langsung |
| Laju komponen ≠ laju sistem (R5) | "2,59 MB/s bukan 11,15" — 11,15 itu laju **spons** saja, bukan laju sistem, kesalahan yang pernah terjadi 4× dan diperbaiki | `rack_heartbeat_seconds()` ≠ `wire_seconds()` — beda ~0,16%, dijelaskan bukan digelapkan |
| Label epistemik pada keadaan sekarang (R2) | FIFO belum dibangun = `[EH]`, bukan diklaim selesai | Fase 1-5 NUI = `AT`, tidak satu pun diklaim "kecerdasan umum" |
| Jangan laporkan angka yang salah satu sisi terpaksa berbohong | interpreter Python vs RTL: cacah clock TIDAK dibandingkan, komentarnya eksplisit | `machine.cycle` TIDAK dijadikan klaim latensi nyata — `CYCLES=` sungguhan itu di hardware, bukan Python |

Itulah "Cosmictera Computing" secara program: bukan satu binary, satu
disiplin, dibuktikan berulang kali taat pada dirinya sendiri di bagian
yang tidak saling menyalin.

---

## Satu perintah, seluruh sistem

```bash
python3 -m pytest -q                # seluruh Python: HCPU parity, Ka'bah, HFS/HOS, NUI
make -C rtl/tb all                  # seluruh RTL: HCPU, H-Kernel, Ka'bah, NUI embedding
python3 NUI/pipeline.py --quick     # NUI, ujung ke ujung, ~20 detik
```

Angka hari ini (bisa berubah — jalankan ulang, jangan dikutip dari sini):
5.394 tes Python lulus, 0 dilewati; 408 asersi RTL di 39 testbench
`make all`, 0 gagal — dari 36 berkas bench yang seluruhnya dijalankan
sesuatu, 16 di antaranya lewat pytest dan bukan lewat `make`.
