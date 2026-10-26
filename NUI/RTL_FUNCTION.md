# Model RTL sebagai fungsi — Lapis 6

Dihasilkan `src/hijaiyyah/nui/rtl_function.py` dari `NUI/spec/rtl_function.json`. RTL dan bench dikompilasi apa adanya dengan satu modul probe di sampingnya yang mencetak register desain sekali tiap siklus; tidak ada port atau baris yang berubah. Simulator: Icarus Verilog version 14.0 (devel) (s20260301-394-g9edaf7b6a-dirty).

**Revisi pasca-freeze (pin kanonik LF).** Freeze Lapis 6 (`NUI/LAYER6.md`, tag `layer6-freeze-2026-09-29-final` di `d003cac`) memegang objek git historis `NUI/rtl_function.json` (`9b92b7293fa6…`), dan `layer6_freeze --verify` memeriksa objek git di tag itu, bukan pohon kerja. Di pohon kerja aktif, pin sumber dihitung atas isi ber-akhir-baris LF (`_file_sha`), bentuk yang disimpan git, sehingga dua pin di `/modules/6/pinned_sha256` (`src/hijaiyyah/hisa/registers.py` dan `src/hijaiyyah/hisab/protocol.py`, yang di pohon sumber saat freeze tertulis CRLF) diperbarui sebagai revisi aktif pasca-freeze tanpa mengubah tag historis.

## `hcpu_uart_rx`

`rtl/hcpu_uart_rx.v` `3dbb9f127825…`, bench `rtl/tb/tb_hcpu_uart_rx.v` `0b422f1855e6…`. CLK_HZ 27000000, BAUD 115200, DIVISOR 234, HALF 117, CNT_W 8.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah, 15915 transisi | 0 berbeda |
| F2 lingkar terbuka dari reset, 15916 siklus | 0 berbeda |
| F3 frame yang diprediksi | 0x41, 0x00, 0xFF, 0x5A, 0x3C; framing error [False, False, False, False, True] |
| F3 bench | PASS: 5 frames, glitch rejected, framing error caught |
| waktu input: perubahan line, ditangkap nilai baru, ditangkap nilai lama | 24, 24, 0 |
| jejak RTL | `106c5aaa8cbd…` |

| aturan | baris RTL | arti | dijalankan bench |
|---|---|---|---|
| `reset` | 52, 57, 64 | rst_n rendah: sinkroniser 11, IDLE, semua nol | 2 |
| `sync` | 53 | dua flop sinkroniser: rx_meta <- rx_in, rx_sync <- rx_meta | 15913 |
| `outputs_drop` | 66, 67 | rx_valid dan rx_frame_err hanya satu siklus | 15913 |
| `idle_wait` | 70, 75 | IDLE, rx_sync tinggi: tetap | 4557 |
| `idle_falling_edge` | 71, 72, 73 | IDLE, rx_sync rendah: START, count 0 | 7 |
| `start_count` | 86, 87 | START sebelum tengah bit: count + 1 | 812 |
| `start_confirmed` | 78, 79, 80, 81, 82 | START di tengah bit dan masih rendah: DATA, count 0, index 0 | 5 |
| `start_glitch` | 78, 83, 84 | START di tengah bit dan sudah tinggi: kembali IDLE | 2 |
| `data_count` | 97, 98 | DATA sebelum tengah bit: count + 1 | 9320 |
| `data_sample` | 92, 93, 94, 96 | DATA di tengah bit: geser rx_sync masuk dari atas (LSB dulu), index + 1 | 35 |
| `data_last` | 92, 93, 94, 95 | DATA di tengah bit ke-8: geser, lalu STOP | 5 |
| `stop_count` | 109, 110 | STOP sebelum tengah bit: count + 1 | 1165 |
| `stop_deliver` | 103, 104, 105, 106, 107, 108 | STOP di tengah bit: IDLE, rx_data <- shifter, rx_valid 1, rx_frame_err <- bukan rx_sync | 5 |

Tidak tercakup bench: tidak ada.

**Waktu input.** input transisi t -> t+1 adalah line sesudah posedge t+1: bench mengubah line di region aktif yang sama dengan posedge tempat DUT menyampel rx_in; iverilog menjalankan penugasan bench lebih dulu. Diukur ulang tiap build dan disimpan di model (input_timing): di tiap perubahan line, rx_meta menangkap nilai baru, tidak pernah nilai lama. Ini sifat penjadwalan bench di simulator, bukan sifat kabel -- di papan line asinkron dan dua flop sinkroniser menanggungnya.

## `hcpu_mmio`

`rtl/hcpu_mmio.v` `7fa8e3111150…`, bench `rtl/tb/tb_hcpu_mmio.v` `4a82b30baf80…`. CLK_HZ 27000000, BAUD 115200, DIVISOR 234, HALF 117, CNT_W 8.

Ikut dimodelkan: `rtl/hcpu_uart_rx.v` `3dbb9f127825…`, `rtl/hcpu_timer.v` `4847d722d2ca…`.

Di luar model — masuk sebagai input, tidak diprediksi:

- `rtl/hcpu_sdio.v` — pengendali kartu: keluarannya (busy, ok, err, card_ready, err_code, isi penyangga) masuk sebagai input, tidak diprediksi.
- `rtl/hcpu_dataram.v` — RAM data -- butir SRAM sendiri di urutan pemilik: kata yang dibacanya masuk sebagai input; model memprediksi kapan dan apakah bus mengembalikannya.
- `unit trap` — tidak ada di bench; trap_reg_rdata tak tersambung (z) dan hanya dibaca bila addr[3:0] = 8..D.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah, 7757 transisi | 0 berbeda |
| F1 keluaran kombinasional, 7758 siklus | 0 berbeda |
| F2 lingkar terbuka dari reset, 7758 siklus | 0 berbeda |
| F3 baca yang diprediksi | 0x010 → 3735928559, 0x010 → 3735928559, 0xFF5 → 4660, 0xFF4 → 13, 0xFF4 → 26, 0xFF1 → 1, 0xFF0 → 65, 0xFF1 → 0, 0xFF1 → 5; tulis RAM di jendela periferal: 0 |
| F3 bench | PASS: RAM, peripherals, latency, hold, and overrun |
| waktu input: perubahan line, ditangkap nilai baru, ditangkap nilai lama | 18, 18, 0 |
| jejak RTL | `068ae10e534a…` |

| aturan | baris RTL | arti | dijalankan bench |
|---|---|---|---|
| `reset` | 150, 188, 238, 270, 330 | rst_n rendah: register MMIO, penerima, dan timer ke nilai reset-nya | 2 |
| `decode` | 123, 124, 125, 126 | satu pembanding: >= 0xFE0 periferal; addr[4] memilih blok inti atau kartu; addr[3:0] register | 7755 |
| `rx_hold` | 156, 157, 158, 159 | rx_valid penerima: byte, galat, dan ready ditahan | 3 |
| `rx_overrun_set` | 160 | byte datang sementara ready masih tinggi: overrun | 1 |
| `rx_read_clear` | 147, 161, 162, 163 | baca 0xFF0: ready dan overrun turun | 1 |
| `timer_count` | `hcpu_timer.v` 36 | pencacah bebas + 1 tiap siklus | 7755 |
| `timer_compare_write` | `hcpu_timer.v` 38, 39, 40 | tulis 0xFF5: compare baru, expired turun | 1 |
| `timer_clear` | `hcpu_timer.v` 41, 42 | tulis 0xFF6: expired turun | 1 |
| `timer_expire` | `hcpu_timer.v` 43, 44 | pencacah sama dengan compare: expired naik dan lengket | 1 |
| `mem_base_write` | 184, 192 | tulis 0xFFE: batas bawah mode pengguna | 0 |
| `mem_limit_write` | 185, 193 | tulis 0xFFF: batas atas mode pengguna | 0 |
| `imem_addr_write` | 228, 241, 242 | tulis 0xFF3: alamat tulis memori instruksi | 0 |
| `imem_data_advance` | 229, 243, 244 | tulis 0xFF7: alamat tulis memori instruksi maju satu | 0 |
| `sd_cmd_write` | 259, 284, 285, 286 | tulis 0xFE0: denyut start dan op kartu | 0 |
| `sd_sector_write` | 260, 288 | tulis 0xFE2: nomor sektor | 0 |
| `sd_control_write` | 263, 290, 291, 292, 293 | tulis 0xFE4: pembagi clock, reset indeks, reset pengendali | 0 |
| `sd_data_advance` | 261, 262, 294, 295 | baca atau tulis 0xFE3: indeks penyangga maju | 0 |
| `read_rx_data` | 352 | jalur baca terdaftar, addr[3:0]=0 di blok inti: byte yang ditahan | 9 |
| `read_rx_status` | 353, 354 | addr[3:0]=1: overrun, galat, ready | 5152 |
| `read_tx_status` | 355 | addr[3:0]=2: pengirim sibuk | 0 |
| `read_imem_addr` | 365, 366 | addr[3:0]=3: alamat tulis memori instruksi | 0 |
| `read_counter` | 356 | addr[3:0]=4: pencacah | 2588 |
| `read_compare` | 357 | addr[3:0]=5: compare | 4 |
| `read_timer_status` | 358 | addr[3:0]=6: expired | 2 |
| `read_trap` | 359, 360, 361, 362, 363, 364 | addr[3:0]=8..D: register trap, dari unit trap | 0 |
| `read_mem_base` | 367, 368 | addr[3:0]=E: batas bawah | 0 |
| `read_mem_limit` | 369, 370 | addr[3:0]=F: batas atas | 0 |
| `read_other` | 371 | addr[3:0]=7 di blok inti: nol | 0 |
| `read_sd_status` | 337, 343, 344, 345 | blok kartu, addr[3:0]=1: status pengendali | 0 |
| `read_sd_sector` | 346 | blok kartu, addr[3:0]=2: sektor | 0 |
| `read_sd_control` | 347 | blok kartu, addr[3:0]=4: pembagi | 0 |
| `read_sd_other` | 348 | blok kartu, register lain: nol | 0 |
| `u_rx.sync` | `hcpu_uart_rx.v` 53 | dua flop sinkroniser: rx_meta <- rx_in, rx_sync <- rx_meta | 7755 |
| `u_rx.outputs_drop` | `hcpu_uart_rx.v` 66, 67 | rx_valid dan rx_frame_err hanya satu siklus | 7755 |
| `u_rx.idle_wait` | `hcpu_uart_rx.v` 70, 75 | IDLE, rx_sync tinggi: tetap | 1083 |
| `u_rx.idle_falling_edge` | `hcpu_uart_rx.v` 71, 72, 73 | IDLE, rx_sync rendah: START, count 0 | 3 |
| `u_rx.start_count` | `hcpu_uart_rx.v` 86, 87 | START sebelum tengah bit: count + 1 | 348 |
| `u_rx.start_confirmed` | `hcpu_uart_rx.v` 78, 79, 80, 81, 82 | START di tengah bit dan masih rendah: DATA, count 0, index 0 | 3 |
| `u_rx.start_glitch` | `hcpu_uart_rx.v` 78, 83, 84 | START di tengah bit dan sudah tinggi: kembali IDLE | 0 |
| `u_rx.data_count` | `hcpu_uart_rx.v` 97, 98 | DATA sebelum tengah bit: count + 1 | 5592 |
| `u_rx.data_sample` | `hcpu_uart_rx.v` 92, 93, 94, 96 | DATA di tengah bit: geser rx_sync masuk dari atas (LSB dulu), index + 1 | 21 |
| `u_rx.data_last` | `hcpu_uart_rx.v` 92, 93, 94, 95 | DATA di tengah bit ke-8: geser, lalu STOP | 3 |
| `u_rx.stop_count` | `hcpu_uart_rx.v` 109, 110 | STOP sebelum tengah bit: count + 1 | 699 |
| `u_rx.stop_deliver` | `hcpu_uart_rx.v` 103, 104, 105, 106, 107, 108 | STOP di tengah bit: IDLE, rx_data <- shifter, rx_valid 1, rx_frame_err <- bukan rx_sync | 3 |

Tidak tercakup bench: mem_base_write, mem_limit_write, imem_addr_write, imem_data_advance, sd_cmd_write, sd_sector_write, sd_control_write, sd_data_advance, read_tx_status, read_imem_addr, read_trap, read_mem_base, read_mem_limit, read_other, read_sd_status, read_sd_sector, read_sd_control, read_sd_other, u_rx.start_glitch.

- `mem_base_write` — bench tidak pernah menulis 0xFFE (jendela proteksi).
- `mem_limit_write` — bench tidak pernah menulis 0xFFF (jendela proteksi).
- `imem_addr_write` — bench tidak pernah menulis 0xFF3 (port tulis memori instruksi).
- `imem_data_advance` — bench tidak pernah menulis 0xFF7 (port tulis memori instruksi).
- `sd_cmd_write` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `sd_sector_write` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `sd_control_write` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `sd_data_advance` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `read_tx_status` — bench tidak pernah menaruh 0xFF2 di bus; uart_tx_busy diikat 0.
- `read_imem_addr` — bench tidak pernah menaruh addr[3:0]=3 di blok inti.
- `read_trap` — bench tidak pernah menaruh 0xFF8-0xFFD di bus; unit trap tidak ada di bench.
- `read_mem_base` — bench tidak pernah menaruh 0xFFE di bus.
- `read_mem_limit` — bench tidak pernah menaruh 0xFFF di bus.
- `read_other` — akses tak terpetakan di blok inti (addr[3:0]=7): bench tidak pernah menaruhnya di bus.
- `read_sd_status` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `read_sd_sector` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `read_sd_control` — bench tidak pernah menyentuh blok kartu 0xFE0-0xFEF.
- `read_sd_other` — akses tak terpetakan di blok kartu: bench tidak pernah menyentuh blok kartu.
- `u_rx.start_glitch` — bench MMIO tidak mengirim glitch; aturan ini dicakup bench UART RX sendiri.

**Waktu input.** keadaan dan input tepi t+1 dibaca dari baris yang dicetak $strobe di akhir timestep tepi t+1; keluaran modul luar (kartu, RAM, trap) yang diregister di sana dibaca dari baris t: bench menggerakkan bus di tepi turun, dan line kadang tepat di tepi naik, kadang sesudah tepi turun (send() yang menyusul bus_read mulai di #1 sesudahnya). Sampel 7 ns sesudah tepi naik terbukti salah pada dua perubahan line itu: ia melihat nilai yang baru flop ambil satu tepi kemudian. Dicetak dengan $strobe di akhir timestep tepi naik, baris memegang persis yang tepi itu ambil, dan pengukuran input_timing tiap build memastikannya.

## `hcpu_uart_tx`

`rtl/hcpu_uart_tx.v` `89dae1c3dbf1…`, bench `rtl/tb/tb_hcpu_top.v` `fe05c8ac2d53…`. CLK_HZ 50000000, BAUD 5000000, CLKS_PER_BIT 10, CNT_W 4.

**Oracle.** pemilik, 28 September 2026: oracle UART TX adalah tb_hcpu_top.v, dan cakupan buktinya dibatasi pada perilaku TX yang bench itu benar-benar jalankan dan amati. Bench top-level melewati modul ini tidak berarti seluruh aturannya terbukti.

Di luar model — masuk sebagai input, tidak diprediksi:

- `rtl/hcpu_top.v` — mesin keadaan cetak PRINT/EMITS (baris 286-390) yang menggerakkan tx_start dan tx_data: keduanya diregister di sana dan masuk sebagai input, tidak diprediksi. Pipeline dan HCPU adalah butir sendiri di urutan pemilik.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah, 232 transisi | 0 berbeda |
| F1 keluaran kombinasional, 233 siklus | 0 berbeda |
| F2 lingkar terbuka dari reset, 233 siklus | 0 berbeda |
| byte yang mulai dikirim, diprediksi fungsi | tidak ada |
| F3 yang bench amati dari modul ini | tidak ada dari pemancar: tak satu baris pun bench membaca uart_tx, uart_busy, atau register u_uart -- uart_tx hanya dideklarasikan (baris 12) dan disambung ke port DUT (baris 40), dan vonisnya membaca GPR, H-Reg, dan guard_led. uart_busy masuk ke hcpu_controller tetapi tidak dipakainya: print_stall = ex_is_print (rtl/hcpu_controller.v baris 69) |
| F3 bench | Total: 15 PASS, 0 FAIL |
| waktu input: perubahan tx_start, ditangkap nilai baru, ditangkap nilai lama | 0, 0, 0 |
| jejak RTL | `1f0ef7b073b7…` |

Daftar pemilik, di jejak RTL — daftar yang pemilik minta dibandingkan -- idle, start bit, bit data, stop bit, waktu bit/pencacah, busy/ready -- dihitung dari jejak RTL sendiri: berapa tepi naik yang menunjukkan tiap keadaan.

| perilaku | tepi naik |
|---|---|
| rst_n rendah | 54 |
| S_IDLE (diam), rst_n tinggi | 179 |
| S_START (start bit) | 0 |
| S_DATA (bit data) | 0 |
| S_STOP (stop bit) | 0 |
| pencacah bit bukan nol (waktu bit) | 0 |
| tx_busy 1 | 0 |
| tx_busy 0 | 233 |
| tx_start 1 | 0 |
| pin uart_tx 0 | 0 |

| aturan | baris RTL | arti | dijalankan bench |
|---|---|---|---|
| `reset` | 40, 41, 42, 43, 44, 45 | rst_n rendah: S_IDLE, pencacah, indeks bit, dan penggeser nol; tx_out 1 (diam tinggi) | 53 |
| `idle_wait` | 48, 49, 50 | S_IDLE tanpa tx_start: tx_out 1, keadaan tetap | 179 |
| `idle_start` | 49, 50, 51, 52, 53 | S_IDLE dengan tx_start: tx_data masuk penggeser, S_START, pencacah nol | 0 |
| `start_count` | 58, 59, 64 | S_START: tx_out 0 (start bit), pencacah naik | 0 |
| `start_end` | 58, 59, 60, 61, 62 | S_START, pencacah = CLKS_PER_BIT-1: pencacah dan indeks bit nol, S_DATA | 0 |
| `data_count` | 69, 70, 78 | S_DATA: tx_out = tx_shift[bit_idx], pencacah naik | 0 |
| `data_next` | 69, 70, 71, 75 | S_DATA, pencacah = CLKS_PER_BIT-1, bit_idx < 7: pencacah nol, bit_idx naik (LSB lebih dulu) | 0 |
| `data_last` | 69, 70, 71, 72, 73 | S_DATA, pencacah = CLKS_PER_BIT-1, bit_idx = 7: pencacah nol, S_STOP | 0 |
| `stop_count` | 83, 84, 88 | S_STOP: tx_out 1 (stop bit), pencacah naik | 0 |
| `stop_end` | 83, 84, 85, 86 | S_STOP, pencacah = CLKS_PER_BIT-1: pencacah nol, S_IDLE | 0 |
| `default` | 92 | state di luar keempat nama: S_IDLE | 0 |

Tidak tercakup bench: idle_start, start_count, start_end, data_count, data_next, data_last, stop_count, stop_end, default.

- `idle_start` — tb_hcpu_top.v tidak menjalankan PRINT atau EMITS, jadi mesin keadaan cetak hcpu_top tidak pernah menaikkan uart_start: tx_start 0 di setiap tepi dan pemancar tidak pernah meninggalkan S_IDLE.
- `start_count` — start bit tidak pernah dikirim: S_START tidak pernah dimasuki, dan pencacah bit tidak pernah bergerak -- CLKS_PER_BIT dari parameter bench tidak teruji perilakunya.
- `start_end` — akhir start bit: S_START tidak pernah dimasuki.
- `data_count` — bit data tidak pernah dikirim: S_DATA tidak pernah dimasuki.
- `data_next` — peralihan ke bit berikutnya, LSB lebih dulu: S_DATA tidak pernah dimasuki.
- `data_last` — bit kedelapan dan peralihan ke stop bit: S_DATA tidak pernah dimasuki.
- `stop_count` — stop bit tidak pernah dikirim: S_STOP tidak pernah dimasuki.
- `stop_end` — kembali ke S_IDLE sesudah stop bit: S_STOP tidak pernah dimasuki.
- `default` — state dua bit punya empat nilai dan keempatnya bernama; cabang ini hanya dicapai keadaan x atau z, dan bench mereset sejak waktu 0.

Batas yang tercakup — yang dijalankan bench, dan apa yang pemakaiannya tidak tunjukkan:

- `reset` — dijalankan hanya atas nilai reset-nya sendiri: pemancar tidak pernah punya keadaan lain untuk dikembalikan. Nilai reset terbukti; kembali dari keadaan lain tidak. Karena keadaan sesudah reset sama dengan keadaan sesudah idle_wait, jejak tidak membedakan tepi tempat rst_n naik: hitungan reset mengikuti aturan waktu input yang dinyatakan, tidak diukur.
- `idle_wait` — tx_out <= 1 selalu menimpa 1: garis diam tinggi terbukti dipertahankan, tidak terbukti dipulihkan sesudah stop bit.
- `tx_busy` — 0 di setiap tepi: ready terbukti, nilai 1-nya tidak pernah muncul.

**Waktu input.** keadaan dan rst_n tepi t+1 dibaca dari baris yang dicetak $strobe di akhir timestep tepi t+1; tx_start dan tx_data diregister mesin keadaan cetak hcpu_top, jadi tepi t+1 mengambil yang baris t tunjukkan: aturan MMIO untuk keluaran modul luar yang diregister. Di bench ini ia tidak terukur: tx_start tidak pernah berubah, jadi pengukuran input_timing tiap build mencatat 0 perubahan -- aturannya dinyatakan dari RTL, tidak dibuktikan.

## `hcpu_dataram`

`rtl/hcpu_dataram.v` `8731b42a61bb…`, bench `rtl/tb/tb_parity.v` `94d820fddc2d…`. XLEN 32, DATA_ADDR_W 12, DATA_DEPTH 4096.

**Oracle.** pemilik, 28 September 2026: oracle RAM data adalah tb_parity.v atas korpus Lapis 4 -- jalur hcpu_top.u_dataram yang sama dengan yang di papan jadi BSRAM. Harness, korpus, dan model paritas Lapis 4 hanya dibaca, tidak diubah; tidak ada bench RAM khusus, dan tidak ada yang dibuat.

Tiga level bukti, dan batas masing-masing:

- **software_model** — src/hijaiyyah/nui/sram_mock.py memodelkan protokol makro sky130_sram_1kbyte_1rw1r_32x256_8 -- perangkat lain, bukan rtl/hcpu_dataram.v -- dan oracle-nya sendiri, behavioural Verilog makro itu, ada di rtl/mpw/sky130_sram_macros/ yang tidak di-commit. Karena itu ia bukan oracle modul ini. Yang sama dengan hcpu_dataram: baca terdaftar, kata tersedia satu siklus sesudah alamat. Yang berbeda: dua port lawan satu; mask byte lawan tanpa mask; dout tak bermakna saat tulis lawan read-first yang RTL tulis (baris 40-42) dan oracle tidak pernah jalankan.
- **rtl** — rtl/hcpu_dataram.v di hcpu_top.u_dataram, di bawah tb_parity.v atas korpus Lapis 4 -- oracle modul ini. Harness mengamati sisi tulis (T ... RAM, saat ram_we && !emits_busy, gerbang yang sama dengan we instance itu); sisi baca hanya teramati lewat GPR sesudah LOAD, jalur milik butir pipeline.
- **hardware** — di papan hcpu_dataram jadi BSRAM Gowin. Buktinya tingkat program lewat kabel: baris LOAD dan STORE kolom P3, dibaca dari NUI/parity_model.json. Isi RAM tidak teramati dari luar papan (P5).

Di luar model — masuk sebagai input, tidak diprediksi:

- `rtl/hcpu_top.v` — apa yang sampai ke port RAM -- re, we, addr, wdata dari pipeline, dekode MMIO, dan mux EMITS (baris 828-835) -- masuk sebagai input, tidak diprediksi. Pipeline dan HCPU adalah butir sendiri di urutan pemilik.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah, 826030 transisi | 0 berbeda |
| F1 keluaran kombinasional, 826030 siklus | 0 berbeda |
| F2 lingkar terbuka dari reset, 826030 siklus | 0 berbeda |
| lari korpus | 107, 20 menyentuh RAM |
| F3 jejak tulis RAM harness = tulisan yang fungsi ambil, 26578 tulis | 0 program berbeda |
| F3 bench | 107 of 107 runs reached the harness's final block (HALTED=) |
| waktu input: perubahan re/we/addr/wdata, ditangkap nilai baru, ditangkap nilai lama | 419521, 0, 419521 |
| jejak RTL | `fd58a9384c89…` |

Program korpus yang menyentuh RAM, dan vonis model paritas Lapis 4 yang beku atasnya — dikutip, tidak dinilai ulang. Di model paritas Lapis 4 yang beku, satu-satunya perpisahan pertama berjenis RAM di antara program yang menyentuh RAM: RTL menulis RAM[0x100]=5 sesudah HALT, interpreter tidak (NUI/PARITY.md, cosmictera-build/OFF.md). Tulisan itu sampai ke port dari pipeline -- butir sendiri -- dan RAM menyimpannya persis seperti yang fungsi ramalkan.

| program | Lapis 4 | perpisahan pertama |
|---|---|---|
| `parity:mmio_does_not_disturb_ram` | PARITY | — |
| `parity:store_then_load` | PARITY | — |
| `rtl/programs/burn_in.hasm` | MISMATCH | GPR |
| `rtl/programs/flags_board.hasm` | MISMATCH | GPR |
| `rtl/programs/flags_ctx.hasm` | MISMATCH | GPR |
| `rtl/programs/hfs_lifecycle.hasm` | MISMATCH | EXIT |
| `rtl/programs/hijrah_sweep.hasm` | UNKNOWN | — |
| `rtl/programs/hos_demo.hasm` | MISMATCH | EXIT |
| `rtl/programs/kernel.hasm` | MISMATCH | GPR |
| `rtl/programs/letters.hasm` | PARITY | — |
| `rtl/programs/mem_protect.hasm` | MISMATCH | GPR |
| `rtl/programs/nui_embedding.hasm` | PARITY | — |
| `rtl/programs/shell.hasm` | MISMATCH | GPR |
| `rtl/programs/subroutine.hasm` | MISMATCH | GPR |
| `rtl/programs/test_hfs.hasm` | MISMATCH | GPR |
| `rtl/programs/trap_hreg.hasm` | UNKNOWN | — |
| `rtl/tb/hfs_persist_probe.hasm` | UNKNOWN | — |
| `rtl/tb/hfs_syscall_probe.hasm` | UNKNOWN | — |
| `rtl/tb/prog_load_probe.hasm` | UNKNOWN | — |
| `stop-probe:halt-then-store` | MISMATCH | RAM |

Bukti papan untuk jalur yang sama, kolom P3 (tingkat program):

| opcode | papan | program | cocok | berbeda | tak bisa diputuskan |
|---|---|---|---|---|---|
| `LOAD` | PARITY | 16 | 12 | 0 | 4 |
| `STORE` | PARITY | 17 | 14 | 0 | 3 |

| aturan | baris RTL | arti | dijalankan bench |
|---|---|---|---|
| `write` | 43, 44, 45 | we: mem[addr] <- wdata di tepi naik | 26578 |
| `read` | 43, 46, 47 | re tanpa we: rdata_r <- mem[addr], kata tersedia satu siklus sesudah alamat | 8620 |
| `hold` | 46, 50 | re rendah: rdata_r tetap, dan rdata adalah rdata_r | 817410 |
| `read_first` | 40, 41, 42, 44, 45, 46, 47 | re dan we di tepi yang sama, alamat sama: rdata_r mendapat kata lama (read-first) | 0 |
| `initial_zero` | 53, 55, 56, 57, 59 | baca kata yang belum pernah ditulis: nol dari blok initial -- hanya simulasi (synthesis translate_off) | 6 |

Tidak tercakup bench: read_first.

- `read_first` — di ke-107 program korpus, re dan we tidak pernah tinggi di tepi yang sama: kata lama yang dikembalikan read-first tidak pernah diminta. Satu port, satu addr: baca dan tulis di tepi yang sama selalu alamat yang sama.

Batas yang tercakup — yang dijalankan oracle, dan apa yang pemakaiannya tidak tunjukkan:

- `initial_zero` — nol awal berasal dari blok initial yang synthesis translate_off buang: terbukti untuk simulasi, bukan klaim tentang BSRAM di papan.
- `rdata` — rdata_r tidak punya reset: x sampai baca pertama tiap lari, dan fungsi memegangnya sebagai x, bukan nol.

**Waktu input.** probe mencatat input yang diambil tiap tepi di region aktif tepi itu, cara yang sama dengan jejak tb_parity.v sendiri menyampel ram_we; nilai sesudah tepi dicetak $strobe: input RAM digerakkan register hcpu_top. Diukur tiap build: di tiap tepi tempat input berubah, yang diambil adalah nilai yang dicetak baris sebelumnya sesudah tepinya -- tidak ada input yang berubah di antara dua tepi.

## `loader`

`rtl/programs/loader.hasm` `7d11249ab606…`, bench `rtl/tb/tb_gowin_loader.v` `ac908f0b53d9…`.

**Oracle.** pemilik, 28 September 2026: oracle loader adalah tb_gowin_loader.v dan tb_gowin_loader_nui.v, keduanya dengan loader.hex di hcpu_gowin_core, dan cakupannya diukur per bench lalu ditetapkan sebagai gabungan dan irisan -- kedua bench tidak dianggap identik. loader.hasm, RTL, dan kedua bench tidak diubah.

**Satu langkah.** PC hanya ada sampai tahap decode (id_pc), jadi keadaan per instruksi tidak teramati tanpa memodelkan pipeline. Fungsi ini berdiri di batas baca MMIO: tiap baca RX_STATUS atau RX_DATA, posisi loader ditentukan alamat yang dibaca dan fase (sebelum atau sesudah IMEM_ADDR ditulis), register dari urutan tulis GPR, dan penunjuk tulis dari hcpu_mmio. Satu langkah = dari satu batas ke batas berikutnya: input nilai yang perangkat keras kembalikan, keluaran tulis GPR, tulis MMIO, tulis port memori instruksi, dan ERET di antaranya, dalam urutan program (WB, lalu MEM, lalu EX dalam satu siklus). FLAGS tidak dibandingkan: tiap CMPI dipakai cabang di langkah yang sama, dan cabangnya teramati lewat kejadian sesudahnya.

Ikut dimodelkan: `rtl/hcpu_mmio.v` `7fa8e3111150…`.

Di luar model — masuk sebagai input, tidak diprediksi:

- `rtl/hcpu_trap.v` — apa yang ERET pasang -- sasaran dan mode -- milik unit trap: diamati di tiap bench, tidak diprediksi fungsi loader.
- `rtl/hcpu_top.v` — pipeline: kapan tiap instruksi sampai ke bus dan ke writeback. Model ini berdiri di batas baca MMIO, bukan per siklus; pipeline dan HCPU adalah butir sendiri.
- `program yang dimuat` — sesudah ERET yang berjalan program lain; jejak dipotong di ERET.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah, dari keadaan RTL di tiap batas baca, 71065 langkah | 0 berbeda |
| F1 kejadian di antara dua batas (GPR, MMIO, port IMEM, ERET), 71065 langkah | 0 berbeda |
| F2 lingkar terbuka dari reset, 71065 langkah, 497618 siklus sampai ERET | 0 berbeda |
| F3 bench | 2 of 2 benches print PASS |
| waktu input: perubahan RX_STATUS/RX_DATA, tiap baca, ditangkap nilai baru, ditangkap nilai lama | 71063, 71063, 0 |
| jejak RTL | `edb681646e35…` |

Per bench — kedua bench tidak dianggap satu:

| bench | batas baca | aturan dijalankan | penunjuk tulis akhir | alamat masuk diambil sebelum ERET | sesudah ERET: EPC, mode | vonis |
|---|---|---|---|---|---|---|
| `tb_gowin_loader` | 5379 | 12 | 67 | tidak — diambil 1 siklus sesudah ERET | 64, 1 | PASS: tb_gowin_loader — program dimuat lewat kabel dan berjalan |
| `tb_gowin_loader_nui` | 65688 | 12 | 112 | tidak — diambil 1 siklus sesudah ERET | 64, 1 | PASS: tb_gowin_loader_nui — L_JIM/L_KHA dimuat lewat kabel, dijalankan, dan mencetak 2\n2\n2\n6\n6\n lewat UART sungguhan |

Gabungan: start, count_spin, count_ready, count_byte, count_last_byte, word_spin, word_ready, word_byte, word_stored, last_word, imem_addr_write, imem_data_advance. Irisan: start, count_spin, count_ready, count_byte, count_last_byte, word_spin, word_ready, word_byte, word_stored, last_word, imem_addr_write, imem_data_advance.

Alamat masuk program yang dimuat (64) tidak pernah diambil fetch sebelum ERET: satu-satunya JMP loader adalah gelung terima, dan handover hanya lewat ERET. Diukur dari alamat fetch hcpu_gowin_core, bukan dari teks loader.hasm.

- `rtl/tb/tb_gowin_loader.v` juga memeriksa R9 = 42 dan R10 = 7 dari program yang dimuat (baris 83-86): bukti handover lewat ERET, milik program sesudahnya, bukan loader.
- `rtl/tb/tb_gowin_loader_nui.v` juga memeriksa sepuluh byte PRINT program yang dimuat, didekode dari uart_txd (baris 131-140): bukti handover lewat ERET, milik program sesudahnya, bukan loader. Kata-kata di memori instruksi tidak diperiksa bench ini.

| aturan | baris RTL | arti | dijalankan bench |
|---|---|---|---|
| `start` | 31, 34, 35 | dari reset: R5 <- 0, R3 <- 0, R4 <- 4, lalu baca RX_STATUS pertama | 2 |
| `count_spin` | 36, 37, 38 | RX_STATUS = 0 saat menerima jumlah kata: JEQ cnt_b, baca RX_STATUS lagi | 2696 |
| `count_ready` | 36, 37, 38, 39 | RX_STATUS bukan nol: baca RX_DATA | 8 |
| `count_byte` | 39, 40, 41, 42, 43, 44 | RX_DATA: R3 <- (R3 << 8) OR byte, R4 turun; R4 bukan nol: JNE cnt_b | 6 |
| `count_last_byte` | 39, 40, 41, 42, 43, 44, 45, 48, 49, 52, 53, 54, 55 | byte keempat jumlah kata: R6 <- N, IMEM_ADDR <- 64, N bukan nol: R3 <- 0, R4 <- 4, baca RX_STATUS kata pertama | 2 |
| `count_empty` | 39, 40, 41, 42, 43, 44, 45, 48, 49, 52, 53, 70, 71, 72, 73, 74 | N = 0: langsung ke done -- TRAP_EPC <- 64, TRAP_MODE <- 2, ERET -- tanpa satu kata pun | 0 |
| `word_spin` | 56, 57, 58 | RX_STATUS = 0 saat menerima kata: JEQ w_b | 67943 |
| `word_ready` | 56, 57, 58, 59 | RX_STATUS bukan nol: baca RX_DATA | 204 |
| `word_byte` | 59, 60, 61, 62, 63, 64 | RX_DATA: R3 <- (R3 << 8) OR byte, R4 turun; R4 bukan nol: JNE w_b | 153 |
| `word_stored` | 59, 60, 61, 62, 63, 64, 65, 66, 67, 52, 53, 54, 55 | byte keempat sebuah kata: IMEM_DATA <- R3, R6 turun, JMP words -- gelung terima, bukan program yang dimuat -- kata tersisa: R3 <- 0, R4 <- 4 | 49 |
| `last_word` | 59, 60, 61, 62, 63, 64, 65, 66, 67, 52, 53, 70, 71, 72, 73, 74 | kata terakhir tersimpan, R6 = 0: JEQ done, TRAP_EPC <- 64, TRAP_MODE <- 2, ERET -- satu-satunya jalan ke program yang dimuat | 2 |
| `imem_addr_write` | `hcpu_mmio.v` 228, 241, 242 | tulis IMEM_ADDR: penunjuk tulis memori instruksi <- nilai itu (aturan hcpu_mmio yang sama namanya) | 2 |
| `imem_data_advance` | `hcpu_mmio.v` 229, 235, 243, 244 | tulis IMEM_DATA: port menulis kata di penunjuk pada tepi yang sama, lalu penunjuk maju satu | 51 |

Tidak tercakup bench: count_empty.

- `count_empty` — kedua bench mengirim N bukan nol (3 dan 48): jalan langsung ke done tanpa kata tidak pernah dijalankan.

Batas yang tercakup — yang dijalankan kedua bench, dan apa yang pemakaiannya tidak tunjukkan:

- `count_ready` — status bukan nol hanya pernah bernilai 1 di kedua bench. CMPI R1, 0 membandingkan seluruh kata status, jadi bit framing error dan overrun (bit 1 dan 2) tanpa bit 0 juga akan membuat loader membaca RX_DATA -- tidak pernah terjadi, tidak diklaim.
- `word_ready` — sama: status bukan nol hanya pernah 1.
- `start` — dari reset saja: satu boot per bench.
- `eret` — sasaran dan mode sesudah ERET diamati dari unit trap, bukan diprediksi.

**Waktu input.** nilai baca ke-k adalah rdata MMIO satu siklus sesudah permintaannya -- jalur baca terdaftar hcpu_mmio: diukur tiap build: di tiap baca, tulis GPR tujuan LOAD-nya sama dengan rdata satu siklus sesudah permintaan (ditangkap nilai baru), bukan rdata pada siklus permintaan.

## `pipeline`

`rtl/hcpu_top.v` `98f70974c232…`, bench `rtl/tb/tb_hcpu_top.v` `fe05c8ac2d53…`.

**Oracle.** pemilik, 28 September 2026, sesudah audit bd8158c GREEN: satu fungsi transisi sinkron atas empat bundle register tahap yang audit catat -- bukan lima fungsi tahap -- dengan input rst_n dan imem_data, dan hasil subsistem luar sebagai input oracle, tidak diprediksi ulang. Dibandingkan per tepi terhadap jejak tb_hcpu_top.v, lalu GPR, H2[7:0], dan guard_led sebagai pemeriksaan terminal. Hanya 45 aturan yang tercakup diberi perilaku; ke-33 lainnya tetap not covered, dan pembekuan sesudah halted tidak diklaim. Interpreter bukan pengganti oracle.

**Bentuk.** `PIPELINE_STATE_t + INPUT_t + EXTERNAL_RESULTS_t -> PIPELINE_STATE_t+1`.

Keadaan — empat bundle register tahap yang audit catat:

- **IF** — pc, pc_prev, fetch_valid, if_instruction, if_pc, pc_valid.
- **ID/EX** — id_opcode, id_dst, id_s1, id_s2, id_imm, id_pc, id_gpr_s1, id_gpr_s2, id_hreg_s1, id_hreg_s2, id_gpr_we, id_hreg_we, id_mem_read, id_mem_write, id_is_branch, id_is_jump, id_is_call, id_is_ret, id_is_codex, id_is_halt, id_is_print, id_is_emits, id_is_push, id_is_pop.
- **EX/MEM** — ex_opcode, ex_dst, ex_gpr_result, ex_hreg_result, ex_gpr_we, ex_hreg_we, ex_flags_new, ex_flags_we, ex_is_halt, ex_is_print, ex_is_emits, ex_emits_addr, ex_print_data, ex_is_push, ex_is_pop, ex_push_data, ex_mem_read, ex_mem_write, ex_mem_addr, ex_mem_wdata, ra_sp.
- **MEM/WB** — mem_dst, mem_gpr_result_r, mem_hreg_result, mem_gpr_we, mem_hreg_we, mem_flags_new, mem_flags_we, mem_is_halt, mem_is_load, mem_is_pop, sp, stack_rd, stack_rd_valid.
- **halted** — register controller (hcpu_controller.v baris 72-77): aturan tercakup ctrl_halt_latch menulisnya; pembekuan yang ia sebabkan tidak tercakup.
- **register file** — companion state dan keluaran fungsi, bukan input oracle (keputusan pemilik, 28 September 2026): diturunkan deterministik dari writeback fungsi sendiri -- keadaan pipeline, lalu writeback, lalu keadaan register file berikutnya (hcpu_regfile.v baris 53-59, 63-68, 94, 111-118): 18 GPR, 16 H-Reg, FLAGS. Pemeriksaan terminal GPR adalah pemeriksaan tambahan, bukan sumber keadaan; register pc di dalamnya diikat pc_we = 0 (hcpu_top.v baris 645).
- **larik tumpukan** — stack[] hcpu_memory: tanpa reset, x sampai ditulis PUSH; di satu langkah dari keadaan RTL hanya kata di sp-1 yang teramati, lewat net probe.

ex_emits_addr ada di RTL (hcpu_execute.v) dan tidak ada di daftar keadaan audit; ia register EX/MEM yang di-latch tiap tepi, jadi ikut di bundle ini.

Input: `rst_n`, `imem_data`. Hasil luar, diambil dari jejak, tidak diprediksi ulang:

- **ROM** — rom_data, rom_valid.
- **guard** — guard_pass, guard_u, guard_rho.
- **ALU codex** — calu_result_vec, calu_result_scl.
- **HISAB** — hisab_pack0, hisab_pack1, hisab_pack2, hisab_crc.
- **unit trap** — trap_redirect_w, trap_in_user_w.
- **RAM dan MMIO** — dram_rdata.
- **mesin keadaan cetak hcpu_top** — print_active.

Pengali hanya dipakai MUL, yang tidak tercakup, jadi keluarannya tidak dibaca. Semua input luar adalah fungsi kombinasional dari keadaan sesudah tepi t, dan tepi t+1 mengambilnya dari baris itu (A1 audit).

**Terminal snapshot.** keputusan pemilik, 28 September 2026: baris sesudah tepi terakhir, ketika halted sudah naik dan bench memanggil $finish tanpa reset, dicatat sebagai terminal snapshot -- halted = 1, sinyal pipeline tertahan -- bukan tepi transisi. Ada tidaknya baris itu bergantung pada urutan $strobe/$finish, jadi ia tidak dipakai sebagai oracle ctrl_halted_stall, yang tetap not covered.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah dari keadaan RTL, 231 tepi transisi | 0 berbeda |
| F1 keluaran, 232 baris | 0 berbeda; berhenti not covered: ctrl_halted_stall (11 baris) |
| F2 lingkar terbuka dari reset | 0 berbeda, sampai tepi 231 |
| langkah yang berhenti not covered | tidak ada |
| terminal snapshot | baris 232: halted = 1, sinyal pipeline tertahan — dicatat, bukan tepi transisi |
| register yang tidak diprediksi | stack_rd (10 tepi) |
| F3 bacaan terminal bench, 32 | 0 berbeda |
| F3 bench | Total: 15 PASS, 0 FAIL |
| waktu input: perubahan rst_n, ditangkap nilai baru, ditangkap nilai lama | 21, 21, 0 |
| jejak RTL | `411860312c3c…` |

Aturan: fungsi menjalankan 45 dari 78, dengan hitungan per aturan sama persis dengan hitungan audit; tidak tercakup 33 — ke-33 aturan dan ke-27 arm opcode yang audit namai: fungsi berhenti dengan NotCovered, bukan memprediksi (bagian Pipeline di bawah).

| program | dibaca bench | fungsi | RTL |
|---|---|---|---|
| 1 | guard_led | 1 | 1 |
| 1 | R0 | 42 | 42 |
| 2 | H2[7:0] | 10 | 10 |
| 2 | R0 | 112 | 112 |
| 3 | R0 | 3 | 3 |
| 4 | R3 | 99 | 99 |
| 5 | R1 | 200 | 200 |
| 6 | R4 | 10 | 10 |
| 7 | R0 | 65824 | 65824 |
| 7 | R1 | 2586908108 | 2586908108 |
| 7 | R2 | 285212673 | 285212673 |
| 7 | R3 | 16144 | 16144 |
| 7 | R4 | 0 | 0 |
| 8 | R4 | 33 | 33 |
| 8 | R5 | 22 | 22 |
| 8 | R6 | 11 | 11 |
| 9 | R1 | 8 | 8 |
| 9 | R2 | 2 | 2 |
| 9 | R3 | 2 | 2 |
| 9 | R4 | 0 | 0 |
| 10 | R3 | 5 | 5 |
| 10 | R4 | 6 | 6 |
| 10 | R5 | 2 | 2 |
| 10 | R6 | 1 | 1 |
| 10 | R8 | 0 | 0 |
| 10 | R9 | 4 | 4 |
| 11 | R1 | 8 | 8 |
| 11 | R2 | 0 | 0 |
| 11 | R3 | 0 | 0 |
| 11 | R4 | 1 | 1 |
| 11 | R6 | 1 | 1 |
| 11 | R7 | 0 | 0 |

**Waktu input.** keadaan t = yang ditinggalkan tepi t; input dan hasil luar tepi t+1 = baris sesudah tepi t (A1 audit, 178 tepi); rst_n tepi t+1 = baris sesudah tepi t+1, karena bench mengubahnya di timestep tepi itu sendiri: diukur tiap build atas rst_n: di tiap tepi tempat rst_n berubah, desain mengikuti nilai baru -- turun: keadaan sesudahnya keadaan reset; naik: fetch melangkah.

## `hcpu`

`rtl/hcpu_top.v` `98f70974c232…`, bench `rtl/tb/tb_hcpu_top.v` `fe05c8ac2d53…`. CLK_HZ 50000000, BAUD 5000000.

**Oracle.** pemilik, 29 September 2026, sesudah audit f590bac GREEN: satu fungsi transisi tingkat sistem dengan state prediktif parsial -- hanya state yang punya aturan transisi tercakup dan dapat diverifikasi. Fungsi yang sudah punya oracle sendiri dikomposisikan apa adanya; yang belum punya oracle tetap hasil luar atau opaque, dan dinyatakan NOT COVERED. Dibandingkan per siklus terhadap tb_hcpu_top.v. RTL, bench, dan bitstream tidak disentuh.

**Bentuk.** `HCPU_STATE_t + rst_n + imem_data + hasil subsistem terverifikasi + hasil oracle luar -> HCPU_STATE_t+1 + OUTPUT_t+1`.

Dikomposisikan — fungsi yang sudah punya oracle sendiri, dipakai apa adanya:

- **pipeline** — fungsi pipeline (bf13941), dengan register file sebagai companion state-nya; aturannya aturan pipeline_audit.
- **peta memori** — fungsi hcpu_mmio (ecb417b), dengan penerima UART (6a9a541) di dalamnya sebagai u_rx, dan timer; bus datanya register EX/MEM pipeline.
- **RAM data** — fungsi hcpu_dataram (0e8b699); portnya lewat mux EMITS hcpu_top.v baris 828-835.
- **pemancar UART** — fungsi hcpu_uart_tx (604bbb8); hanya reset dan diam yang tercakup, jadi start, data, dan stop berhenti dengan NotCovered.
- **ALU codex** — handler interpreter src/hijaiyyah/hisa/machine.py untuk HCADD, HNRM2, HDIST, CGET, CSET, CMOD4, dijalankan pada register sementara; kode op dan keluaran mana yang diisi dibaca dari hcpu_codex_alu.v sendiri (localparam dan arm case-nya), dan keluaran lainnya nol (baris 125-126). Operandnya forwarding pipeline, yang tidak membaca hasil ALU -- diukur di setiap baris.
- **pengali** — handler MUL interpreter yang sama, atas forwarding pipeline; hasilnya tidak dipakai pipeline karena arm MUL tidak tercakup, dan hanya dibandingkan sebagai keluaran.
- **sambungan hcpu_top** — uart_rx yang tidak disambung dibaca 1 (hcpu_top.v baris 723), dan port debug register file (hcpu_regfile.v baris 98-99).

Input: `rst_n`, `imem_data`, `uart_rx`, `dbg_gpr_raddr`. Hasil luar, diambil dari jejak, tidak diprediksi:

- **ROM Master Table** — `rom_data`, `rom_valid`.
- **guard** — `guard_pass`, `guard_u`, `guard_rho`.
- **HISAB** — `hisab_pack0`, `hisab_pack1`, `hisab_pack2`, `hisab_crc`.
- **unit trap** — `trap_redirect_w`, `trap_in_user_w`, `trap_reg_rdata`.
- **mesin keadaan cetak** — `print_active`, `tx_start`, `tx_data`, `emits_busy`, `str_addr`.
- **pengendali kartu** — `sd_busy`, `sd_ok`, `sd_err`, `sd_card_ready`, `sd_err_code`, `sd_buf_rdata`.

keputusan pemilik, 29 September 2026: ROM Master Table tidak dijadikan fungsi (imem_data tetap input, rom_data dan rom_valid hasil jejak); guard kombinasional aktif dan dipakai HGRD, CU, CRHO, tetapi bukan subsistem prediktif; HISAB tetap hasil luar karena model Python-nya berbeda dari hcpu_hisab.v; unit trap, mesin keadaan cetak, dan pengendali kartu tidak punya oracle yang cukup. Semua hasil luar diambil dari baris sesudah tepi t untuk tepi t+1, titik sampel yang probe fungsi ini ukur sendiri.

Opaque — keadaan RTL yang tidak diprediksi dan tidak diklaim paritasnya:

- **unit trap** — tujuh register hcpu_trap.v; tidak pernah meninggalkan keadaan reset di bench ini (hcpu_audit), dan keluarannya masuk sebagai hasil luar.
- **mesin keadaan cetak** — sembilan register hcpu_top.v baris 286-390 dan larik digits[]; tetap P_IDLE.
- **pengendali kartu** — 41 register hcpu_sdio.v termasuk sbuf[]; tetap S_IDLE. Tujuh belas di antaranya tanpa reset dan x di setiap tepi: tidak diberi nilai, tidak masuk klaim paritas.
- **ra_stack[]** — tumpukan alamat kembali hcpu_execute.v; CALL dan RET tidak tercakup. Dipromosikan menjadi keadaan prediktif bila bench menjalankannya.
- **register pc di register file** — pc_we diikat 0 (hcpu_top.v baris 645).
- **guard berregister** — tujuh register yang tidak dielaborasi karena PIPELINE_GUARD(0); guard kombinasionalnya aktif, dan hasilnya diambil dari jejak.
- **is_kaf di hcpu_hisab.v** — override T2 yang tersisa di hcpu_hisab.v baris 72-74, sudah dicabut dari hcpu_guard.v; tidak pernah naik di jejak ini. Tidak dipakai sebagai dasar klaim, tidak diubah.
- **kata RAM yang belum ditulis** — nol awal simulasi adalah aturan initial_zero yang tidak tercakup di bench ini; fungsi tidak mengklaim kata yang belum ia tulis.

**Ketidaksesuaian yang diketahui, HISAB.** hisab/serialize.py (dan HPACK/HCRC interpreter yang memakainya) menaruh status guard dengan urutan bit lain dari hcpu_hisab.v: RTL dan core/guards.py bit 0 = G1 (A_N), bit 1 = G2 (A_K), bit 2 = G3 (A_Q), bit 3 = G4 (rho >= 0); hisab/protocol.py bit 0 = rho >= 0. Word 2 dan CRC berbeda bila sebuah guard gagal. Diukur ulang tiap build: 13 tepi, program 5, 10; di tepi yang memakai HPACK atau HCRC: 0. keputusan pemilik, 29 September 2026: urutan kanonik adalah RTL + core/guards.py; hisab/protocol.py tidak diubah di sini, dan perbaikannya butir HISAB tersendiri. HISAB di fungsi ini hasil luar, jadi selisihnya tidak dipoles menjadi paritas.

| pemeriksaan | hasil |
|---|---|
| titik sampel: yang diambil tepi t+1 = yang ditinggalkan tepi t, 231 tepi, setiap sinyal probe kecuali rst_n | 0 berbeda |
| F1 satu langkah dari keadaan RTL, 231 tepi | 0 berbeda |
| F1 keluaran, 57 per baris, 232 baris | 0 berbeda; berhenti not covered: ctrl_halted_stall (11 baris) |
| operand ALU tidak bergantung pada hasil ALU | 0 baris bergerak |
| F2 lingkar terbuka dari reset | 0 berbeda, sampai tepi 231 |
| F2 RAM: kata di port tiap baris | 115 dicek, 0 berbeda; 116 baris port di kata yang belum ditulis fungsi — tidak diklaim |
| F2 RAM saat $finish, kata bukan nol | fungsi 2, RTL 2, 0 berbeda |
| langkah yang berhenti not covered | tidak ada |
| register yang tidak diprediksi | stack_rd (10 tepi) |
| F3 bacaan terminal bench, 32 | 0 berbeda |
| F3 bench | Total: 15 PASS, 0 FAIL |
| waktu input: perubahan rst_n, ditangkap nilai baru, ditangkap nilai lama | 21, 21, 0 |
| jejak RTL | `7ae2e5792098…` |

Aturan: fungsi menjalankan 71 dari 149, dengan hitungan per aturan sama persis dengan hitungan kedua audit; tidak tercakup 78 — aturan kedua audit yang tidak dijalankan tb_hcpu_top.v: fungsi berhenti dengan NotCovered, tidak memprediksi.

Batas yang dinamai spec, di luar aturan RTL:

- `calu.width` — hasil handler interpreter lebih lebar dari kabel RTL -- komponen HCADD di atas 8 bit (hcpu_codex_alu.v baris 65), HNRM2 atau HDIST di atas 16 bit (baris 91, 107). Interpreter tidak memotong, dan handler-nya tidak diberi mask; apa yang RTL simpan di sana tidak punya oracle.

**Terminal snapshot.** probe fungsi ini mencetak tiap tepi di region aktif dan dengan $strobe; baris $strobe tepi terakhir tidak tercetak karena $finish bench jatuh di timestep-nya, jadi jejak ini tidak membawa terminal snapshot. Keputusan pemilik (e897ed0) tetap berlaku: snapshot sesudah halted = 1 hanya observasi terminal, bukan oracle transisi.

**Waktu input.** keadaan t = yang ditinggalkan tepi t; input dan hasil luar tepi t+1 = baris sesudah tepi t; rst_n tepi t+1 = baris sesudah tepi t+1: sama dengan fungsi pipeline, dan diukur ulang atas probe fungsi ini sendiri: untuk setiap sinyal kecuali rst_n, yang diambil tepi t+1 di region aktif sama dengan yang dicetak $strobe tepi t; rst_n diikuti desain di setiap perubahannya.

## Pipeline — audit oracle `tb_hcpu_top.v`, sebelum model

**Oracle.** pemilik, 28 September 2026: pipeline memakai tb_hcpu_top.v sebagai oracle sistem. Tidak ada bench per tahap, jadi kelima tahap tidak dimodelkan terpisah, dan langkah pertama adalah audit cakupan oracle -- keadaan yang teramati, input yang berubah, titik sampel, instruksi yang lewat tiap tahap, transisi yang dapat diprediksi, dan aturan yang tidak pernah dijalankan. Model fungsinya ditulis sesudah peta ini. Tidak ada bench baru, RTL pipeline tidak diubah, hasil interpreter bukan pengganti oracle, dan keadaan internal yang tidak teramati tidak diklaim.

Bench `rtl/tb/tb_hcpu_top.v` `fe05c8ac2d53…`; dipegang: `rtl/hcpu_top.v`, `rtl/hcpu_fetch.v`, `rtl/hcpu_decode.v`, `rtl/hcpu_forward.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_memory.v`, `rtl/hcpu_writeback.v`, `rtl/hcpu_controller.v`, `rtl/hcpu_regfile.v`, `rtl/hcpu_pkg.vh`.

**Titik sampel.** tiap tepi naik dicatat dua kali: di region aktif, sebelum pembaruan non-blocking mana pun mendarat (yang tepi itu ambil), dan dengan $strobe di akhir timestep (yang tepi itu tinggalkan). Aturan yang tepi t+1 jalankan dibaca dari baris $strobe tepi t. Tepi reset: rst_n rendah di akhir timestep-nya. Tepi pelepasan reset dinilai dari bukti desain sendiri: kalau pc fetch sesudahnya masih 0 dan fetch_valid 0, desain masih di reset: bench mengubah rst_n di region aktif yang sama dengan tepi, jadi urutannya terhadap probe di region aktif tidak pasti -- lari eksploratif pertama melihat empat dari sebelas program tanpa baris halted karena itu. Untuk sinyal desain, diukur tiap build: yang diambil tepi t+1 sama dengan yang dicetak $strobe tepi t. Terukur: 178 tepi hidup, dan yang diambil tiap tepi berbeda dari yang ditinggalkan tepi sebelumnya di tidak satu pun sinyal desain. Tepi pelepasan reset: 11 melangkah, 0 tertahan. Tepi terakhir tidak punya baris sesudah: `$finish` bench jatuh di timestep-nya.

**Yang bench sendiri amati.** sesudah tiap program berhenti: register GPR, H2[7:0] (program 2), dan pin guard_led (program 1), dibaca lewat hierarki; jumlah siklus sampai halted dicetak, tidak diperiksa. Tak satu pun register tahap pipeline dibaca bench. Vonis: Total: 15 PASS, 0 FAIL.

| program | baris bench | bench membaca | tepi hidup | diambil fetch | didekode | dieksekusi | sampai WB |
|---|---|---|---|---|---|---|---|
| 1 | 79 | guard_led, R0 | 9 | 8 | 7 | 6 | 5 |
| 2 | 119 | H2[7:0], R0 | 13 | 12 | 11 | 10 | 9 |
| 3 | 166 | R0 | 23 | 18 | 15 | 14 | 13 |
| 4 | 201 | R3 | 14 | 13 | 12 | 11 | 10 |
| 5 | 238 | R1 | 13 | 10 | 8 | 7 | 6 |
| 6 | 271 | R4 | 14 | 12 | 11 | 10 | 9 |
| 7 | 306 | R0, R1, R2, R3, R4 | 12 | 11 | 10 | 9 | 8 |
| 8 | 370 | R4, R5, R6 | 20 | 19 | 18 | 17 | 16 |
| 9 | 420 | R1, R2, R3, R4 | 12 | 11 | 10 | 9 | 8 |
| 10 | 470 | R3, R4, R5, R6, R8, R9 | 20 | 19 | 18 | 17 | 16 |
| 11 | 537 | R1, R2, R3, R4, R6, R7 | 28 | 25 | 23 | 22 | 21 |

| tahap | berkas | keadaan (register RTL) | identitas instruksi | keadaan berikut dari | di luar |
|---|---|---|---|---|---|
| IF | `hcpu_fetch.v` | pc, pc_prev, fetch_valid, if_instruction, if_pc, pc_valid | teramati: if_pc dan pc_valid menamai tiap instruksi di IF dan membedakan gelembung | keadaan IF, imem_data, pc_stall, if_flush, redirect_taken dan sasarannya | imem_data dari BRAM bench (terdaftar); sasaran redirect dari execute atau unit trap |
| ID/EX | `hcpu_decode.v` | id_opcode, id_dst, id_s1, id_s2, id_imm, id_pc, id_gpr_s1, id_gpr_s2, id_hreg_s1, id_hreg_s2, id_gpr_we, id_hreg_we, id_mem_read, id_mem_write, id_is_branch, id_is_jump, id_is_call, id_is_ret, id_is_codex, id_is_halt, id_is_print, id_is_emits, id_is_push, id_is_pop | teramati sebagian: id_pc dan id_opcode; gelembung dan NOP nyata di PC 0 tidak terbedakan -- tidak ada program yang punya NOP di PC 0 | if_instruction, if_pc, bacaan register file, id_stall, id_flush | register file (hcpu_regfile.v): bacaannya kombinasional, dengan tulis-tembus WB |
| EX/MEM | `hcpu_execute.v` | ex_opcode, ex_dst, ex_gpr_result, ex_hreg_result, ex_gpr_we, ex_hreg_we, ex_flags_new, ex_flags_we, ex_is_halt, ex_is_print, ex_is_emits, ex_print_data, ex_is_push, ex_is_pop, ex_push_data, ex_mem_read, ex_mem_write, ex_mem_addr, ex_mem_wdata, ra_sp | diturunkan: EX/MEM tidak membawa PC; identitasnya diturunkan dari ID/EX lewat ex_stall yang teramati, dan dicek terhadap ex_opcode | keadaan ID/EX sesudah forwarding, FLAGS, ex_stall | ROM, guard, ALU codex, HISAB, pengali, dan unit trap: keluarannya masuk sebagai input |
| MEM/WB | `hcpu_memory.v` | mem_dst, mem_gpr_result_r, mem_hreg_result, mem_gpr_we, mem_hreg_we, mem_flags_new, mem_flags_we, mem_is_halt, mem_is_load, mem_is_pop, sp, stack_rd, stack_rd_valid | diturunkan: MEM/WB tidak membawa PC maupun opcode; identitasnya diturunkan dari EX/MEM lewat ex_stall | keadaan EX/MEM, ex_stall | RAM data dan peta memori (sudah dimodelkan sendiri): rdata masuk sebagai input |
| WB | `hcpu_writeback.v` | — | kombinasional dari MEM/WB: tidak ada register sendiri | MEM/WB | - |
| controller | `hcpu_controller.v` | halted | - | wb_halt, print_active, hazard load-use dan store-load, redirect_taken | print_active dari mesin keadaan cetak hcpu_top |

Identitas turunan dicek di 178 tepi terhadap id_pc dan id_opcode (0 berbeda) dan terhadap ex_opcode (0 berbeda).

| aturan | tahap | baris RTL | arti | tepi | program |
|---|---|---|---|---|---|
| `fetch_reset` | IF | `hcpu_fetch.v` 72, 73, 74, 75, 76, 77, 78 | rst_n rendah: pc, pc_prev, fetch_valid nol, IF memegang NOP | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `fetch_redirect_branch` | IF | `hcpu_fetch.v` 79, 81, 82, 83, 84, 85, 86 | redirect dari cabang: IF jadi gelembung, pc <- sasaran | 4 | 3, 5, 11 |
| `fetch_redirect_trap` | IF | `hcpu_fetch.v` 79, 81, 82, 83, 84, 85, 86 | redirect dari unit trap: sama, sasaran dari trap | 0 | — |
| `fetch_flush_only` | IF | `hcpu_fetch.v` 79, 81, 82, 83, 84, 85 | flush tanpa redirect: IF jadi gelembung, pc tetap | 0 | — |
| `fetch_stall` | IF | `hcpu_fetch.v` 88 | pc_stall: semua ditahan | 1 | 6 |
| `fetch_latch` | IF | `hcpu_fetch.v` 92, 94, 95, 96, 97, 98 | fetch_valid: instruksi BRAM di-latch, pc maju | 158 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `fetch_warmup` | IF | `hcpu_fetch.v` 100, 103, 104, 105, 106, 107, 108 | fetch_valid rendah: gelembung, pc maju, fetch_valid naik | 15 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `decode_reset` | ID/EX | `hcpu_decode.v` 162 | rst_n rendah: ID/EX nol, NOP | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `decode_flush_redirect` | ID/EX | `hcpu_decode.v` 187 | id_flush karena redirect: gelembung ke ID/EX | 4 | 3, 5, 11 |
| `decode_flush_hazard` | ID/EX | `hcpu_decode.v` 187 | id_flush karena hazard data: gelembung ke ID/EX | 1 | 6 |
| `decode_stall` | ID/EX | `hcpu_decode.v` 369 | id_stall: ID/EX ditahan | 0 | — |
| `decode_latch_instruction` | ID/EX | `hcpu_decode.v` 212, 242 | instruksi nyata dari IF di-latch dan didekode | 143 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `decode_latch_bubble` | ID/EX | `hcpu_decode.v` 212, 242, 243 | gelembung IF di-latch sebagai NOP | 30 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `decode_letter` | ID/EX | `hcpu_decode.v` 350 | opcode huruf: codex, H0 | 0 | — |
| `decode_halt_err` | ID/EX | `hcpu_decode.v` 357, 360 | opcode tak dikenal: HALT_ERR | 0 | — |
| `hazard_load_use` | ID/EX | `hcpu_decode.v` 129 | LOAD di ID/EX, instruksi IF memakai tujuannya | 1 | 6 |
| `hazard_pop_use` | ID/EX | `hcpu_decode.v` 129 | POP di ID/EX, instruksi IF memakai tujuannya | 0 | — |
| `hazard_store_load` | ID/EX | `hcpu_decode.v` 142 | STORE di EX/MEM, LOAD di IF ke alamat yang sama | 0 | — |
| `fwd_gpr_s1_ex` | forward | `hcpu_forward.v` 53 | GPR[S1] dari EX/MEM | 5 | 3, 7, 10 |
| `fwd_gpr_s1_mem` | forward | `hcpu_forward.v` 55 | GPR[S1] dari MEM/WB | 6 | 3, 6, 7, 10 |
| `fwd_gpr_s1_rf` | forward | `hcpu_forward.v` 58 | GPR[S1] dari register file | 35 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `fwd_gpr_s2_ex` | forward | `hcpu_forward.v` 63 | GPR[S2] dari EX/MEM | 1 | 6 |
| `fwd_gpr_s2_mem` | forward | `hcpu_forward.v` 65 | GPR[S2] dari MEM/WB | 3 | 3, 4, 11 |
| `fwd_gpr_s2_rf` | forward | `hcpu_forward.v` 68 | GPR[S2] dari register file | 8 | 2, 3, 6, 11 |
| `fwd_hreg_s1_ex` | forward | `hcpu_forward.v` 73 | H[S1] dari EX/MEM | 9 | 1, 2, 5, 7, 9, 10 |
| `fwd_hreg_s1_mem` | forward | `hcpu_forward.v` 75 | H[S1] dari MEM/WB | 8 | 2, 7, 9, 10, 11 |
| `fwd_hreg_s1_rf` | forward | `hcpu_forward.v` 78 | H[S1] dari register file | 29 | 3, 4, 6, 7, 8, 9, 10, 11 |
| `fwd_hreg_s2_ex` | forward | `hcpu_forward.v` 83 | H[S2] dari EX/MEM | 3 | 2, 11 |
| `fwd_hreg_s2_mem` | forward | `hcpu_forward.v` 85 | H[S2] dari MEM/WB | 0 | — |
| `fwd_hreg_s2_rf` | forward | `hcpu_forward.v` 88 | H[S2] dari register file | 9 | 3, 4, 6, 11 |
| `ex_latch` | EX/MEM | `hcpu_execute.v` 434 | ex_stall rendah: EX/MEM di-latch | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `ex_stall` | EX/MEM | `hcpu_execute.v` 434 | ex_stall: EX/MEM ditahan | 0 | — |
| `ex_flush` | EX/MEM | `hcpu_execute.v` 413 | flush execute: gelembung ke EX/MEM | 0 | — |
| `flags_forward_self` | EX/MEM | `hcpu_execute.v` 280 | konsumen FLAGS (cabang, FRD) mengambil alu_flags instruksinya sendiri | 0 | — |
| `flags_forward_ex` | EX/MEM | `hcpu_execute.v` 281 | konsumen FLAGS mengambil ex_flags_new | 7 | 3, 5, 11 |
| `flags_forward_rf` | EX/MEM | `hcpu_execute.v` 282 | konsumen FLAGS mengambil register FLAGS | 0 | — |
| `branch_jmp` | EX/MEM | `hcpu_execute.v` 364 | JMP: redirect mutlak | 0 | — |
| `branch_call` | EX/MEM | `hcpu_execute.v` 367 | CALL: redirect, alamat kembali ke ra_stack | 0 | — |
| `branch_ret` | EX/MEM | `hcpu_execute.v` 370 | RET: redirect ke puncak ra_stack | 0 | — |
| `jeq_taken` | EX/MEM | `hcpu_execute.v` 375 | JEQ diambil | 0 | — |
| `jeq_not_taken` | EX/MEM | `hcpu_execute.v` 375 | JEQ tidak diambil | 0 | — |
| `jne_taken` | EX/MEM | `hcpu_execute.v` 376 | JNE diambil | 3 | 3, 11 |
| `jne_not_taken` | EX/MEM | `hcpu_execute.v` 376 | JNE tidak diambil | 3 | 3, 11 |
| `jgd_taken` | EX/MEM | `hcpu_execute.v` 377 | JGD diambil | 0 | — |
| `jgd_not_taken` | EX/MEM | `hcpu_execute.v` 377 | JGD tidak diambil | 0 | — |
| `jngd_taken` | EX/MEM | `hcpu_execute.v` 378 | JNGD diambil | 1 | 5 |
| `jngd_not_taken` | EX/MEM | `hcpu_execute.v` 378 | JNGD tidak diambil | 0 | — |
| `ra_overflow` | EX/MEM | `hcpu_execute.v` 340 | HC-04: CALL dengan ra_stack penuh | 0 | — |
| `ra_underflow` | EX/MEM | `hcpu_execute.v` 341 | HC-05: RET dengan ra_stack kosong | 0 | — |
| `hc01_invalid_rom` | EX/MEM | `hcpu_execute.v` 451 | HC-01: HLOAD indeks ROM tidak sah | 0 | — |
| `priv_fault` | EX/MEM | `hcpu_execute.v` 310 | tindakan istimewa di mode user | 0 | — |
| `mem_fault` | EX/MEM | `hcpu_execute.v` 317 | akses di luar jendela proteksi di mode user | 0 | — |
| `eret` | EX/MEM | `hcpu_execute.v` 325 | ERET di mode supervisor | 0 | — |
| `syscall` | EX/MEM | `hcpu_execute.v` 285 | SYSCALL | 0 | — |
| `flags_hgrd` | EX/MEM | `hcpu_execute.v` 490 | HGRD menulis bit GUARD | 3 | 1, 2, 5 |
| `flags_ceq` | EX/MEM | `hcpu_execute.v` 494 | CEQ menulis Z | 3 | 11 |
| `flags_fwr` | EX/MEM | `hcpu_execute.v` 505 | FWR menulis FLAGS | 0 | — |
| `flags_cmp` | EX/MEM | `hcpu_execute.v` 512 | CMP/CMPI menulis Z dan LT | 3 | 3 |
| `mem_latch` | MEM/WB | `hcpu_memory.v` 143 | ex_stall rendah: MEM/WB di-latch | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mem_stall` | MEM/WB | `hcpu_memory.v` 143 | ex_stall: MEM/WB ditahan | 0 | — |
| `dram_read` | MEM/WB | `hcpu_memory.v` 61 | LOAD ke bus | 2 | 4, 6 |
| `dram_write` | MEM/WB | `hcpu_memory.v` 62 | STORE ke bus | 2 | 4, 6 |
| `stack_push` | MEM/WB | `hcpu_memory.v` 78, 101 | PUSH: stack[sp] <- data, sp naik | 3 | 8 |
| `stack_pop` | MEM/WB | `hcpu_memory.v` 80 | POP: sp turun | 3 | 8 |
| `stack_overflow` | MEM/WB | `hcpu_memory.v` 69 | HC-02: PUSH dengan tumpukan penuh | 0 | — |
| `stack_underflow` | MEM/WB | `hcpu_memory.v` 70 | HC-03: POP dengan tumpukan kosong | 0 | — |
| `result_load` | WB | `hcpu_memory.v` 126 | WB mengambil rdata RAM/MMIO | 2 | 4, 6 |
| `result_pop` | WB | `hcpu_memory.v` 126 | WB mengambil puncak tumpukan | 3 | 8 |
| `wb_gpr` | WB | `hcpu_writeback.v` 33 | tulis GPR | 49 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `wb_hreg` | WB | `hcpu_writeback.v` 37 | tulis H-Reg | 20 | 1, 2, 5, 7, 9, 10, 11 |
| `wb_flags` | WB | `hcpu_writeback.v` 41 | tulis FLAGS | 9 | 1, 2, 3, 5, 11 |
| `wb_halt` | WB | `hcpu_writeback.v` 44 | HALT sampai writeback | 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `ctrl_print_stall` | controller | `hcpu_controller.v` 69, 80 | PRINT/EMITS sedang berjalan: stall global | 0 | — |
| `ctrl_halt_latch` | controller | `hcpu_controller.v` 75, 76 | wb_halt: halted naik | 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `ctrl_halted_stall` | controller | `hcpu_controller.v` 80, 91, 92, 93 | halted: stall global | 0 | — |
| `ctrl_data_hazard` | controller | `hcpu_controller.v` 88, 91, 99 | hazard data: stall front-end dan gelembung | 1 | 6 |
| `ctrl_if_flush` | controller | `hcpu_controller.v` 98 | redirect tanpa stall global: flush IF | 4 | 3, 5, 11 |
| `ctrl_id_flush` | controller | `hcpu_controller.v` 99 | redirect atau hazard tanpa stall global: flush ID | 5 | 3, 5, 6, 11 |

Tercakup 45 dari 78 aturan. Tidak tercakup — aturan RTL pipeline yang tidak dijalankan tb_hcpu_top.v: dinyatakan di sini dengan alasannya, tidak dianggap terbukti:

- `fetch_redirect_trap` — trap_redirect_w 0 di setiap tepi: tidak ada program yang menjalankan SYSCALL atau ERET, dan tidak ada trap yang menembak.
- `fetch_flush_only` — tidak terjangkau dari kabel hcpu_top: if_flush = branch_taken && !global_stall (hcpu_controller.v baris 98), dan masukan branch_taken controller itu adalah redirect_taken (hcpu_top.v baris 842) -- if_flush tanpa redirect tidak mungkin.
- `decode_stall` — stall global = PRINT/EMITS berjalan atau halted (hcpu_controller.v baris 80). Tidak ada PRINT atau EMITS. Tidak ada tepi transisi yang sah dalam jendela sampling pipeline yang membuktikan aturan ini: bench mereset pada tepi sesudah halted naik, kecuali sesudah program 11, tempat ia memanggil $finish. Sebuah terminal snapshot sesudah halted naik dapat muncul bergantung pada urutan $strobe/$finish, dan tidak digunakan sebagai oracle transisi.
- `decode_letter` — tidak ada opcode huruf (0xE0-0xFB) di kesebelas program.
- `decode_halt_err` — tiap opcode di kesebelas program punya arm di case decode.
- `hazard_pop_use` — program 8 menaruh NOP sesudah tiap POP; tidak ada instruksi yang memakai tujuan POP tepat sesudahnya.
- `hazard_store_load` — hazard ini butuh LOAD tepat dua instruksi sesudah STORE ke alamat yang sama; di program 4 dan 6 keduanya berjarak tiga instruksi.
- `fwd_hreg_s2_mem` — tidak ada pembaca S2 (daftar decode baris 100-105) yang H[S2]-nya ditulis tepat dua instruksi sebelumnya.
- `ex_stall` — stall global = PRINT/EMITS berjalan atau halted (hcpu_controller.v baris 80). Tidak ada PRINT atau EMITS. Tidak ada tepi transisi yang sah dalam jendela sampling pipeline yang membuktikan aturan ini: bench mereset pada tepi sesudah halted naik, kecuali sesudah program 11, tempat ia memanggil $finish. Sebuah terminal snapshot sesudah halted naik dapat muncul bergantung pada urutan $strobe/$finish, dan tidak digunakan sebagai oracle transisi.
- `ex_flush` — flush execute diikat 1'b0 di hcpu_top.v baris 489: tidak terjangkau.
- `flags_forward_self` — konsumen FLAGS (cabang dan FRD) bukan CMP, jadi alu_flags_we instruksinya sendiri tidak pernah tinggi saat ia memilih FLAGS.
- `flags_forward_rf` — ketiga cabang di bench -- JNE di program 3 dan 11, JNGD di program 5 -- semuanya tepat sesudah penulis FLAGS-nya (CMP, CEQ, HGRD): FLAGS selalu datang dari EX/MEM.
- `branch_jmp` — tidak ada JMP di kesebelas program.
- `branch_call` — tidak ada CALL di kesebelas program.
- `branch_ret` — tidak ada RET di kesebelas program.
- `jeq_taken` — tidak ada JEQ di kesebelas program.
- `jeq_not_taken` — tidak ada JEQ di kesebelas program.
- `jgd_taken` — tidak ada JGD di kesebelas program.
- `jgd_not_taken` — tidak ada JGD di kesebelas program.
- `jngd_not_taken` — satu-satunya JNGD (program 5) diambil: vektor indeks 31 gagal guard.
- `ra_overflow` — tidak ada CALL atau RET: ra_sp 0 sepanjang lari.
- `ra_underflow` — tidak ada CALL atau RET: ra_sp 0 sepanjang lari.
- `hc01_invalid_rom` — satu-satunya HLOAD di luar huruf 1-28 (program 5, indeks 31) adalah vektor negatif yang ROM simpan (hcpu_pkg.vh baris 176): rom_valid 1.
- `priv_fault` — mode supervisor sepanjang lari: in_user 0 di setiap tepi.
- `mem_fault` — mode supervisor sepanjang lari: in_user 0 di setiap tepi.
- `eret` — tidak ada ERET di kesebelas program.
- `syscall` — tidak ada SYSCALL di kesebelas program.
- `flags_fwr` — tidak ada FWR di kesebelas program.
- `mem_stall` — stall global = PRINT/EMITS berjalan atau halted (hcpu_controller.v baris 80). Tidak ada PRINT atau EMITS. Tidak ada tepi transisi yang sah dalam jendela sampling pipeline yang membuktikan aturan ini: bench mereset pada tepi sesudah halted naik, kecuali sesudah program 11, tempat ia memanggil $finish. Sebuah terminal snapshot sesudah halted naik dapat muncul bergantung pada urutan $strobe/$finish, dan tidak digunakan sebagai oracle transisi.
- `stack_overflow` — program 8 mendorong tiga dan mengambil tiga: sp 0 sampai 3.
- `stack_underflow` — program 8 mendorong tiga dan mengambil tiga: sp 0 sampai 3.
- `ctrl_print_stall` — tidak ada PRINT atau EMITS: print_active 0 di setiap tepi.
- `ctrl_halted_stall` — stall global = PRINT/EMITS berjalan atau halted (hcpu_controller.v baris 80). Tidak ada PRINT atau EMITS. Tidak ada tepi transisi yang sah dalam jendela sampling pipeline yang membuktikan aturan ini: bench mereset pada tepi sesudah halted naik, kecuali sesudah program 11, tempat ia memanggil $finish. Sebuah terminal snapshot sesudah halted naik dapat muncul bergantung pada urutan $strobe/$finish, dan tidak digunakan sebagai oracle transisi.

| opcode | baris decode | IF | ID/EX | EX/MEM | MEM/WB |
|---|---|---|---|---|---|
| `NOP` | 243 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `HALT` | 245 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `MOVI` | 252 | 1, 3, 4, 5, 6, 8, 10, 11 | 1, 3, 4, 5, 6, 8, 10, 11 | 1, 3, 4, 5, 6, 8, 10, 11 | 1, 3, 4, 5, 6, 8, 10, 11 |
| `ADD` | 254 | 6 | 6 | 6 | 6 |
| `ADDI` | 255 | 3 | 3 | 3 | 3 |
| `CMP` | 271 | 3 | 3 | 3 | 3 |
| `JNE` | 288 | 3, 11 | 3, 11 | 3, 11 | 3, 11 |
| `JNGD` | 290 | 5 | 5 | 5 | 5 |
| `PUSH` | 292 | 8 | 8 | 8 | 8 |
| `POP` | 293 | 8 | 8 | 8 | 8 |
| `LOAD` | 294 | 4, 6 | 4, 6 | 4, 6 | 4, 6 |
| `STORE` | 295 | 4, 6 | 4, 6 | 4, 6 | 4, 6 |
| `HLOAD` | 297 | 1, 2, 5, 7, 9, 10, 11 | 1, 2, 5, 7, 9, 10, 11 | 1, 2, 5, 7, 9, 10, 11 | 1, 2, 5, 7, 9, 10, 11 |
| `HCADD` | 298 | 2, 11 | 2, 11 | 2, 11 | 2, 11 |
| `HGRD` | 299 | 1, 2, 5 | 1, 2, 5 | 1, 2, 5 | 1, 2, 5 |
| `HNRM2` | 300 | 2 | 2 | 2 | 2 |
| `CGET` | 301 | 9, 10 | 9, 10 | 9, 10 | 9, 10 |
| `CSET` | 309 | 10 | 10 | 10 | 10 |
| `CMOV` | 320 | 11 | 11 | 11 | 11 |
| `CZERO` | 321 | 11 | 11 | 11 | 11 |
| `CEQ` | 323 | 11 | 11 | 11 | 11 |
| `CRHO` | 324 | 11 | 11 | 11 | 11 |
| `CU` | 325 | 11 | 11 | 11 | 11 |
| `CMOD4` | 326 | 11 | 11 | 11 | 11 |
| `HPACK` | 329 | 7 | 7 | 7 | 7 |
| `HCRC` | 330 | 7 | 7 | 7 | 7 |

Arm opcode yang tercakup: 26 dari 53; NOP di ID/EX dan sesudahnya termasuk NOP nyata yang diambil sesudah HALT. Tidak tercakup — arm case decode yang opcode-nya tidak ada di kesebelas program tb_hcpu_top.v: tidak pernah masuk ID/EX, jadi tidak ada tahap sesudahnya yang menjalankannya: `FRD`, `MOV`, `SUB`, `MUL`, `AND`, `OR`, `XOR`, `NOT`, `SHL`, `SHR`, `ANDI`, `ORI`, `XORI`, `SHLI`, `SHRI`, `CMPI`, `FWR`, `EMITS`, `CALL`, `RET`, `JMP`, `JEQ`, `JGD`, `HDIST`, `PRINT`, `ERET`, `SYSCALL`.

## HCPU — audit oracle integrasi `tb_hcpu_top.v`, sebelum model

**Oracle.** pemilik, 28 September 2026, ketika pipeline bf13941 diterima: langkah berikutnya model HCPU tingkat sistem dengan tb_hcpu_top.v sebagai oracle integrasi, tetapi audit cakupan HCPU lebih dulu, dengan prinsip yang sama seperti pipeline -- model HCPU tidak ditulis sebelum peta oracle dan batas keadaannya terukur. Tidak ada bench baru, RTL tidak diubah, hasil interpreter bukan pengganti oracle, dan keadaan yang tidak teramati tidak diklaim.

**Lari.** bench, top, instance, clock, daftar kompilasi, vonis, dan kesebelas program milik pipeline_audit -- satu tempat. Audit ini menjalankan bench yang sama dengan probe lain; transisi pipeline sendiri milik pipeline_audit dan tidak diukur dua kali. Bench `rtl/tb/tb_hcpu_top.v` `fe05c8ac2d53…`; dipegang 22 berkas RTL. Vonis: Total: 15 PASS, 0 FAIL.

**Titik sampel.** aturan pipeline_audit: tiap tepi naik dicatat di region aktif dan dengan $strobe, aturan tepi t+1 dibaca dari baris $strobe tepi t, dan tepi reset serta pelepasannya dinilai dengan bukti desain yang sama (pc fetch 0 dan fetch_valid 0); diukur ulang tiap build atas setiap sinyal probe audit ini, bukan diwarisi dari sinyal pipeline. Terukur: 178 tepi hidup dari 232, dan yang diambil tiap tepi berbeda dari yang ditinggalkan tepi sebelumnya di tidak satu pun sinyal probe. Tepi pelepasan reset: 11 melangkah, 0 tertahan.

**Input HCPU.** Port masukan `hcpu_top.v`, di setiap baris jejak termasuk tepi reset:

| port | disambung ke | perubahan | nilai |
|---|---|---|---|
| `rst_n` | register bench rst_n | 21 | 0, 1 |
| `imem_data` | BRAM bench dengan baca terdaftar dan imem_ce (tb_hcpu_top.v baris 20-27): memori instruksi di luar HCPU | 130 | 78 nilai |
| `uart_rx` | tidak disambung bench, jadi z; hcpu_top.v baris 723 menariknya ke 1 | 0 | z |
| `sd_cmd_in` | tidak disambung bench, jadi z | 0 | z |
| `sd_dat_in` | tidak disambung bench, jadi z | 0 | z |
| `dbg_gpr_raddr` | 5'd0 (tb_hcpu_top.v baris 44) | 0 | 0 |

Yang berubah hanya `rst_n`, `imem_data`: itulah input HCPU di bawah oracle ini.

| keluaran | dibaca | perubahan | nilai |
|---|---|---|---|
| `imem_addr` | alamat BRAM bench (baris 27, 37) | 187 | 27 nilai |
| `imem_ce` | clock-enable BRAM bench (baris 26, 38) | 23 | 0, 1 |
| `imem_we` | tidak disambung | 0 | 0 |
| `imem_waddr` | tidak disambung | 0 | 0 |
| `imem_wdata` | tidak disambung | 34 | 16 nilai |
| `uart_tx` | disambung ke wire bench (baris 12, 40) dan tidak pernah dibaca | 0 | 1 |
| `halted` | bench menunggunya tiap program (mis. baris 95) | 21 | 0, 1 |
| `guard_led` | dibaca vonis program 1 (baris 102), dicetak program 2 (baris 146) | 4 | 0, 1 |
| `sd_clk` | tidak disambung | 0 | 0 |
| `sd_cmd_out` | tidak disambung | 0 | 1 |
| `sd_cmd_oe` | tidak disambung | 0 | 1 |
| `sd_dat_out` | tidak disambung | 0 | 1 |
| `sd_dat_oe` | tidak disambung | 0 | 0 |
| `dbg_gpr_rdata` | tidak disambung (baris 45) | 10 | 7 nilai |
| `dbg_flags` | tidak disambung (baris 46) | 10 | 0, 1, 2, 8 |

**Batas keadaan.** 171 register di 21 berkas, dibaca dari penugasan non-blocking RTL sendiri, lalu dibandingkan dengan batas di spec: tidak dideklarasikan 0, hilang 0. Larik ditulis `nama[]` dan teramati lewat aturan yang menulisnya.

| subsistem | jenis | berkas | register | fungsi (oracle-nya) | bergerak | tetap | x di tiap tepi |
|---|---|---|---|---|---|---|---|
| pipeline | sinkron | `hcpu_fetch.v`, `hcpu_decode.v`, `hcpu_forward.v`, `hcpu_execute.v`, `hcpu_memory.v`, `hcpu_writeback.v`, `hcpu_controller.v` | 67 | `pipeline` (`tb_hcpu_top.v`; diukur pipeline_audit) | di pipeline_audit | di pipeline_audit | di pipeline_audit |
| register file | sinkron | `hcpu_regfile.v` | 4 | companion state `pipeline` | `flags` (7) | 1 | 0 |
| print | sinkron | `hcpu_top.v` | 10 | — | — | 9 | 0 |
| trap | sinkron | `hcpu_trap.v` | 7 | — | — | 7 | 0 |
| mmio | sinkron | `hcpu_mmio.v`, `hcpu_uart_rx.v`, `hcpu_timer.v` | 28 | `hcpu_mmio` (`tb_hcpu_mmio.v`) | `periph_rdata` (14), `counter` (178) | 26 | 0 |
| sdio | sinkron | `hcpu_sdio.v` | 41 | — | `div_cnt` (11), `wr_data` (30) | 21 | 17 |
| uart_tx | sinkron | `hcpu_uart_tx.v` | 5 | `hcpu_uart_tx` (`tb_hcpu_top.v`) | — | 5 | 0 |
| dataram | sinkron | `hcpu_dataram.v` | 2 | `hcpu_dataram` (`tb_parity.v`) | `rdata_r` (2) | 0 | 0 |
| rom | kombinasional | `hcpu_rom.v` | 0 | — | — | 0 | 0 |
| guard | kombinasional | `hcpu_guard.v` | 0 | — | — | 0 | 0 |
| calu | kombinasional | `hcpu_codex_alu.v` | 0 | — | — | 0 | 0 |
| hisab | kombinasional | `hcpu_hisab.v` | 0 | — | — | 0 | 0 |
| mul | kombinasional | `hcpu_mul.v` | 0 | — | — | 0 | 0 |

Di luar fungsi, atau tidak dielaborasi:

- `rtl/hcpu_execute.v:ra_stack[]` — tumpukan alamat kembali (baris 331): CALL menulisnya dan RET membacanya, keduanya tidak tercakup pipeline_audit, dan larik ini tidak ada di keadaan fungsi pipeline.
- `rtl/hcpu_regfile.v:pc` — pc_we diikat 1'b0 (hcpu_top.v baris 645): register ini tidak pernah ditulis dan bukan bagian register file fungsi pipeline.
- `rtl/hcpu_guard.v:g1_r, rtl/hcpu_guard.v:g2_r, rtl/hcpu_guard.v:g3_r, rtl/hcpu_guard.v:g4_r, rtl/hcpu_guard.v:t1_r, rtl/hcpu_guard.v:t2_r, rtl/hcpu_guard.v:guard_r` — cabang generate berregister hanya ada bila PIPELINE_GUARD 1; hcpu_top.v baris 662 memasangnya dengan PIPELINE_GUARD(0), jadi register itu tidak dielaborasi.

Tanpa reset dan tidak pernah ditulis, jadi x di setiap tepi hidup: `u_mmio.u_sdio.ack_sh`, `u_mmio.u_sdio.bit_cnt`, `u_mmio.u_sdio.buf_rdata`, `u_mmio.u_sdio.cmd_index`, `u_mmio.u_sdio.cmd_sh`, `u_mmio.u_sdio.crc16`, `u_mmio.u_sdio.crc16_rx`, `u_mmio.u_sdio.crc7`, `u_mmio.u_sdio.dat_cnt`, `u_mmio.u_sdio.fsm_addr`, `u_mmio.u_sdio.fsm_wdata`, `u_mmio.u_sdio.op_r`, `u_mmio.u_sdio.resp_len`, `u_mmio.u_sdio.resp_sh`, `u_mmio.u_sdio.sector_r`, `u_mmio.u_sdio.timeout`, `u_mmio.u_sdio.word_sh`.

| aturan | subsistem | baris RTL | arti | tepi | program |
|---|---|---|---|---|---|
| `print.reset` | print | `hcpu_top.v` 287, 288, 289, 290, 291, 292, 293, 294, 295, 296 | rst_n rendah: P_IDLE, uart_start dan print_active 0, semua pencacah dan str_addr nol | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `print.pulse_clear` | print | `hcpu_top.v` 298 | tiap tepi hidup: uart_start turun lagi -- denyut satu siklus ke pemancar | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `print.idle` | print | `hcpu_top.v` 301, 302, 303, 304, 309 | P_IDLE tanpa PRINT atau EMITS yang diterima: print_active dan emits_busy 0 | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `print.print_accept` | print | `hcpu_top.v` 304, 305, 306, 307, 308 | P_IDLE, ex_is_print dan EX tidak tertahan: nilai diambil, pipeline ditahan, P_CONV | 0 | — |
| `print.emits_accept` | print | `hcpu_top.v` 309, 310, 311, 312, 313 | P_IDLE, ex_is_emits dan EX tidak tertahan: alamat string diambil, port RAM diambil alih, P_S_ADDR | 0 | — |
| `print.conv_zero` | print | `hcpu_top.v` 318, 319, 320, 321, 322 | P_CONV, nilai 0 dan belum ada digit: satu digit '0', P_SEND | 0 | — |
| `print.conv_digit` | print | `hcpu_top.v` 323, 324, 325, 326 | P_CONV, nilai bukan nol: satu digit desimal dari % 10, nilai / 10 | 0 | — |
| `print.conv_done` | print | `hcpu_top.v` 327, 328, 329 | P_CONV, nilai habis: digit_idx ke digit terakhir, P_SEND | 0 | — |
| `print.send` | print | `hcpu_top.v` 334, 335, 336, 337 | P_SEND, pemancar bebas: satu digit ke uart_data, uart_start naik, P_WAIT | 0 | — |
| `print.send_hold` | print | `hcpu_top.v` 333, 334 | P_SEND, pemancar sibuk: tetap | 0 | — |
| `print.wait_newline` | print | `hcpu_top.v` 342, 343, 344 | P_WAIT, pemancar bebas, digit terakhir terkirim: P_NEWLN | 0 | — |
| `print.wait_next` | print | `hcpu_top.v` 342, 345, 346, 347 | P_WAIT, pemancar bebas, masih ada digit: digit_idx turun, P_SEND | 0 | — |
| `print.wait_hold` | print | `hcpu_top.v` 341, 342 | P_WAIT, pemancar sibuk atau denyut belum turun: tetap | 0 | — |
| `print.newline` | print | `hcpu_top.v` 353, 354, 355, 356 | P_NEWLN, pemancar bebas: '\n' ke uart_data, uart_start naik, P_IDLE | 0 | — |
| `print.newline_hold` | print | `hcpu_top.v` 352, 353 | P_NEWLN, pemancar sibuk: tetap | 0 | — |
| `print.s_addr` | print | `hcpu_top.v` 361, 363 | P_S_ADDR: alamat word keluar siklus ini, P_S_CHAR | 0 | — |
| `print.s_char_end` | print | `hcpu_top.v` 367, 372 | P_S_CHAR, word nol: penutup string, P_IDLE tanpa newline | 0 | — |
| `print.s_char_send` | print | `hcpu_top.v` 373, 374, 375, 376 | P_S_CHAR, word bukan nol, pemancar bebas: byte rendahnya ke uart_data, P_S_WAIT | 0 | — |
| `print.s_char_hold` | print | `hcpu_top.v` 366, 373 | P_S_CHAR, word bukan nol, pemancar sibuk: tetap | 0 | — |
| `print.s_wait_next` | print | `hcpu_top.v` 381, 382, 383 | P_S_WAIT, pemancar bebas: str_addr ke word berikutnya, P_S_ADDR | 0 | — |
| `print.s_wait_hold` | print | `hcpu_top.v` 380, 381 | P_S_WAIT, pemancar sibuk atau denyut belum turun: tetap | 0 | — |
| `print.default` | print | `hcpu_top.v` 387 | print_state di luar kedelapan nama: P_IDLE | 0 | — |
| `trap.reset` | trap | `hcpu_trap.v` 166, 167, 168, 169, 170, 171, 177, 178 | rst_n rendah: vector, epc, cause, enable nol, tidak dalam trap, mode dan prev supervisor | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `trap.idle` | trap | `hcpu_trap.v` 180, 183 | tanpa ERET dan tanpa fire: mode, prev, epc, cause, trap_active tetap | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `trap.eret` | trap | `hcpu_trap.v` 180, 181, 182, 162, 163 | ERET: keluar trap, mode <- prev; redirect ke epc | 0 | — |
| `trap.eret_mode_bypass` | trap | `hcpu_trap.v` 135, 136, 182 | ERET di tepi yang sama dengan tulis TRAP_MODE: mode mengambil bit tulis itu, bukan prev lama | 0 | — |
| `trap.eret_epc_bypass` | trap | `hcpu_trap.v` 156, 157, 163 | ERET di tepi yang sama dengan tulis TRAP_EPC: sasaran kembali adalah nilai tulis itu | 0 | — |
| `trap.fire_timer` | trap | `hcpu_trap.v` 110, 114, 117, 122, 183, 189, 190, 191, 192, 193 | sumber timer armed, tidak dalam trap, PC sah: epc <- pc_now, cause timer, mode supervisor | 0 | — |
| `trap.fire_uart_rx` | trap | `hcpu_trap.v` 110, 114, 117, 122, 183, 189, 190, 191, 192, 193 | sumber penerima UART armed: sama, cause uart_rx | 0 | — |
| `trap.fire_illegal` | trap | `hcpu_trap.v` 110, 114, 117, 122, 183, 189, 190, 191, 192, 193 | sumber instruksi ilegal armed: sama, cause illegal | 0 | — |
| `trap.fire_priv` | trap | `hcpu_trap.v` 107, 108, 110, 114, 183, 189, 190, 191, 192, 193 | fault hak istimewa, tak bisa dimask: epc <- pc_fault, cause priv | 0 | — |
| `trap.fire_mem` | trap | `hcpu_trap.v` 107, 108, 110, 114, 183, 189, 190, 191, 192, 193 | fault memori, tak bisa dimask: epc <- pc_fault, cause mem | 0 | — |
| `trap.fire_syscall` | trap | `hcpu_trap.v` 107, 108, 110, 114, 183, 189, 190, 191, 192, 193 | SYSCALL, tak bisa dimask: epc <- pc_fault, cause syscall | 0 | — |
| `trap.pending_masked` | trap | `hcpu_trap.v` 95, 96, 97, 110 | sumber yang bisa dimask naik tanpa bit enable-nya: tidak armed | 0 | — |
| `trap.held_active` | trap | `hcpu_trap.v` 114 | armed tetapi sudah dalam trap: tidak menembak | 0 | — |
| `trap.held_pc_invalid` | trap | `hcpu_trap.v` 114 | armed, tidak dalam trap, tetapi front end tanpa PC sah: tidak menembak | 0 | — |
| `trap.write_vector` | trap | `hcpu_trap.v` 199, 200, 201 | tulis TRAP_VECTOR: alamat handler | 0 | — |
| `trap.write_epc` | trap | `hcpu_trap.v` 199, 200, 202 | tulis TRAP_EPC: alamat kembali | 0 | — |
| `trap.write_enable` | trap | `hcpu_trap.v` 199, 200, 203 | tulis TRAP_ENABLE: mask per sebab | 0 | — |
| `trap.write_mode` | trap | `hcpu_trap.v` 199, 200, 207 | tulis TRAP_MODE: bit 1 ke prev; bit 0 hanya baca | 0 | — |
| `trap.write_readonly` | trap | `hcpu_trap.v` 199, 200, 208 | tulis TRAP_CAUSE atau TRAP_PENDING: diabaikan | 0 | — |
| `mmio.reset` | mmio | `hcpu_mmio.v` 150, 188, 238, 270, 330 | rst_n rendah: register MMIO, penerima, dan timer ke nilai reset-nya | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.decode` | mmio | `hcpu_mmio.v` 123, 124, 125, 126 | satu pembanding: >= 0xFE0 periferal; addr[4] memilih blok inti atau kartu; addr[3:0] register | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.rx_hold` | mmio | `hcpu_mmio.v` 156, 157, 158, 159 | rx_valid penerima: byte, galat, dan ready ditahan | 0 | — |
| `mmio.rx_overrun_set` | mmio | `hcpu_mmio.v` 160 | byte datang sementara ready masih tinggi: overrun | 0 | — |
| `mmio.rx_read_clear` | mmio | `hcpu_mmio.v` 147, 161, 162, 163 | baca 0xFF0: ready dan overrun turun | 0 | — |
| `mmio.timer_count` | mmio | `hcpu_timer.v` 36 | pencacah bebas + 1 tiap siklus | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.timer_compare_write` | mmio | `hcpu_timer.v` 38, 39, 40 | tulis 0xFF5: compare baru, expired turun | 0 | — |
| `mmio.timer_clear` | mmio | `hcpu_timer.v` 41, 42 | tulis 0xFF6: expired turun | 0 | — |
| `mmio.timer_expire` | mmio | `hcpu_timer.v` 43, 44 | pencacah sama dengan compare: expired naik dan lengket | 0 | — |
| `mmio.mem_base_write` | mmio | `hcpu_mmio.v` 184, 192 | tulis 0xFFE: batas bawah mode pengguna | 0 | — |
| `mmio.mem_limit_write` | mmio | `hcpu_mmio.v` 185, 193 | tulis 0xFFF: batas atas mode pengguna | 0 | — |
| `mmio.imem_addr_write` | mmio | `hcpu_mmio.v` 228, 241, 242 | tulis 0xFF3: alamat tulis memori instruksi | 0 | — |
| `mmio.imem_data_advance` | mmio | `hcpu_mmio.v` 229, 243, 244 | tulis 0xFF7: alamat tulis memori instruksi maju satu | 0 | — |
| `mmio.sd_cmd_write` | mmio | `hcpu_mmio.v` 259, 284, 285, 286 | tulis 0xFE0: denyut start dan op kartu | 0 | — |
| `mmio.sd_sector_write` | mmio | `hcpu_mmio.v` 260, 288 | tulis 0xFE2: nomor sektor | 0 | — |
| `mmio.sd_control_write` | mmio | `hcpu_mmio.v` 263, 290, 291, 292, 293 | tulis 0xFE4: pembagi clock, reset indeks, reset pengendali | 0 | — |
| `mmio.sd_data_advance` | mmio | `hcpu_mmio.v` 261, 262, 294, 295 | baca atau tulis 0xFE3: indeks penyangga maju | 0 | — |
| `mmio.read_rx_data` | mmio | `hcpu_mmio.v` 352 | jalur baca terdaftar, addr[3:0]=0 di blok inti: byte yang ditahan | 115 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.read_rx_status` | mmio | `hcpu_mmio.v` 353, 354 | addr[3:0]=1: overrun, galat, ready | 9 | 3, 8, 11 |
| `mmio.read_tx_status` | mmio | `hcpu_mmio.v` 355 | addr[3:0]=2: pengirim sibuk | 14 | 1, 2, 3, 5, 7, 9, 10, 11 |
| `mmio.read_imem_addr` | mmio | `hcpu_mmio.v` 365, 366 | addr[3:0]=3: alamat tulis memori instruksi | 6 | 3, 4 |
| `mmio.read_counter` | mmio | `hcpu_mmio.v` 356 | addr[3:0]=4: pencacah | 0 | — |
| `mmio.read_compare` | mmio | `hcpu_mmio.v` 357 | addr[3:0]=5: compare | 4 | 6, 10 |
| `mmio.read_timer_status` | mmio | `hcpu_mmio.v` 358 | addr[3:0]=6: expired | 4 | 8, 10 |
| `mmio.read_trap` | mmio | `hcpu_mmio.v` 359, 360, 361, 362, 363, 364 | addr[3:0]=8..D: register trap, dari unit trap | 24 | 1, 2, 5, 6, 8, 9, 10, 11 |
| `mmio.read_mem_base` | mmio | `hcpu_mmio.v` 367, 368 | addr[3:0]=E: batas bawah | 0 | — |
| `mmio.read_mem_limit` | mmio | `hcpu_mmio.v` 369, 370 | addr[3:0]=F: batas atas | 2 | 3, 5 |
| `mmio.read_other` | mmio | `hcpu_mmio.v` 371 | addr[3:0]=7 di blok inti: nol | 0 | — |
| `mmio.read_sd_status` | mmio | `hcpu_mmio.v` 337, 343, 344, 345 | blok kartu, addr[3:0]=1: status pengendali | 0 | — |
| `mmio.read_sd_sector` | mmio | `hcpu_mmio.v` 346 | blok kartu, addr[3:0]=2: sektor | 0 | — |
| `mmio.read_sd_control` | mmio | `hcpu_mmio.v` 347 | blok kartu, addr[3:0]=4: pembagi | 0 | — |
| `mmio.read_sd_other` | mmio | `hcpu_mmio.v` 348 | blok kartu, register lain: nol | 0 | — |
| `mmio.u_rx.sync` | mmio | `hcpu_uart_rx.v` 53 | dua flop sinkroniser: rx_meta <- rx_in, rx_sync <- rx_meta | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.u_rx.outputs_drop` | mmio | `hcpu_uart_rx.v` 66, 67 | rx_valid dan rx_frame_err hanya satu siklus | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.u_rx.idle_wait` | mmio | `hcpu_uart_rx.v` 70, 75 | IDLE, rx_sync tinggi: tetap | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `mmio.u_rx.idle_falling_edge` | mmio | `hcpu_uart_rx.v` 71, 72, 73 | IDLE, rx_sync rendah: START, count 0 | 0 | — |
| `mmio.u_rx.start_count` | mmio | `hcpu_uart_rx.v` 86, 87 | START sebelum tengah bit: count + 1 | 0 | — |
| `mmio.u_rx.start_confirmed` | mmio | `hcpu_uart_rx.v` 78, 79, 80, 81, 82 | START di tengah bit dan masih rendah: DATA, count 0, index 0 | 0 | — |
| `mmio.u_rx.start_glitch` | mmio | `hcpu_uart_rx.v` 78, 83, 84 | START di tengah bit dan sudah tinggi: kembali IDLE | 0 | — |
| `mmio.u_rx.data_count` | mmio | `hcpu_uart_rx.v` 97, 98 | DATA sebelum tengah bit: count + 1 | 0 | — |
| `mmio.u_rx.data_sample` | mmio | `hcpu_uart_rx.v` 92, 93, 94, 96 | DATA di tengah bit: geser rx_sync masuk dari atas (LSB dulu), index + 1 | 0 | — |
| `mmio.u_rx.data_last` | mmio | `hcpu_uart_rx.v` 92, 93, 94, 95 | DATA di tengah bit ke-8: geser, lalu STOP | 0 | — |
| `mmio.u_rx.stop_count` | mmio | `hcpu_uart_rx.v` 109, 110 | STOP sebelum tengah bit: count + 1 | 0 | — |
| `mmio.u_rx.stop_deliver` | mmio | `hcpu_uart_rx.v` 103, 104, 105, 106, 107, 108 | STOP di tengah bit: IDLE, rx_data <- shifter, rx_valid 1, rx_frame_err <- bukan rx_sync | 0 | — |
| `sdio.reset` | sdio | `hcpu_sdio.v` 139, 140, 141, 213, 214, 215, 216, 295 | rst_n pengendali rendah: pembagi, port tulis penyangga, dan mesin keadaan ke nilai reset-nya | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `sdio.soft_reset` | sdio | `hcpu_sdio.v` 304 | sd_soft_rst MMIO naik: rst_n pengendali rendah satu siklus (hcpu_mmio.v baris 293, 304) | 0 | — |
| `sdio.clk_off` | sdio | `hcpu_sdio.v` 142, 143, 144 | clk_en rendah: div_cnt <- divider, sd_clk 0 | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `sdio.clk_toggle` | sdio | `hcpu_sdio.v` 145, 146, 147 | clk_en, pencacah habis: sd_clk berbalik | 0 | — |
| `sdio.clk_count` | sdio | `hcpu_sdio.v` 148, 149 | clk_en, pencacah belum habis: turun satu | 0 | — |
| `sdio.port_host` | sdio | `hcpu_sdio.v` 218, 219, 220 | tidak sibuk: port tulis penyangga mengikuti bus host | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `sdio.port_fsm` | sdio | `hcpu_sdio.v` 218, 219, 220 | sibuk: port tulis penyangga mengikuti mesin keadaan | 0 | — |
| `sdio.buf_write` | sdio | `hcpu_sdio.v` 225 | wr_en: satu word ke sbuf -- blok tanpa reset | 0 | — |
| `sdio.buf_read` | sdio | `hcpu_sdio.v` 226 | tiap tepi: buf_rdata <- sbuf[rd_addr] -- blok tanpa reset | 231 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `sdio.idle_wait` | sdio | `hcpu_sdio.v` 320, 321, 322, 323, 324, 325 | S_IDLE tanpa start: jalur diam | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `sdio.idle_init` | sdio | `hcpu_sdio.v` 325, 333, 334, 335, 336, 337, 338, 339 | S_IDLE, start dengan op 1: init, S_POWERUP | 0 | — |
| `sdio.idle_not_init` | sdio | `hcpu_sdio.v` 325, 340, 344, 345 | S_IDLE, start baca/tulis sebelum init: E_NOT_INIT, S_FAIL | 0 | — |
| `sdio.idle_transfer` | sdio | `hcpu_sdio.v` 325, 346, 347, 348, 349 | S_IDLE, start baca/tulis sesudah init: S_CMD_SETUP | 0 | — |
| `sdio.s_powerup` | sdio | `hcpu_sdio.v` 355 | arm S_POWERUP: dimasuki bila state bernilai S_POWERUP di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_cmd_setup` | sdio | `hcpu_sdio.v` 372 | arm S_CMD_SETUP: dimasuki bila state bernilai S_CMD_SETUP di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_cmd_send` | sdio | `hcpu_sdio.v` 399 | arm S_CMD_SEND: dimasuki bila state bernilai S_CMD_SEND di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_cmd_gap` | sdio | `hcpu_sdio.v` 444 | arm S_CMD_GAP: dimasuki bila state bernilai S_CMD_GAP di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_resp_wait` | sdio | `hcpu_sdio.v` 459 | arm S_RESP_WAIT: dimasuki bila state bernilai S_RESP_WAIT di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_resp_recv` | sdio | `hcpu_sdio.v` 487 | arm S_RESP_RECV: dimasuki bila state bernilai S_RESP_RECV di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_resp_done` | sdio | `hcpu_sdio.v` 500 | arm S_RESP_DONE: dimasuki bila state bernilai S_RESP_DONE di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_dat_wait` | sdio | `hcpu_sdio.v` 564 | arm S_DAT_WAIT: dimasuki bila state bernilai S_DAT_WAIT di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_dat_recv` | sdio | `hcpu_sdio.v` 579 | arm S_DAT_RECV: dimasuki bila state bernilai S_DAT_RECV di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_dat_crc` | sdio | `hcpu_sdio.v` 597 | arm S_DAT_CRC: dimasuki bila state bernilai S_DAT_CRC di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_gap` | sdio | `hcpu_sdio.v` 619 | arm S_WR_GAP: dimasuki bila state bernilai S_WR_GAP di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_start` | sdio | `hcpu_sdio.v` 634 | arm S_WR_START: dimasuki bila state bernilai S_WR_START di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_data` | sdio | `hcpu_sdio.v` 642 | arm S_WR_DATA: dimasuki bila state bernilai S_WR_DATA di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_crc` | sdio | `hcpu_sdio.v` 664 | arm S_WR_CRC: dimasuki bila state bernilai S_WR_CRC di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_end` | sdio | `hcpu_sdio.v` 677 | arm S_WR_END: dimasuki bila state bernilai S_WR_END di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_ack` | sdio | `hcpu_sdio.v` 691 | arm S_WR_ACK: dimasuki bila state bernilai S_WR_ACK di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_wr_busy` | sdio | `hcpu_sdio.v` 719 | arm S_WR_BUSY: dimasuki bila state bernilai S_WR_BUSY di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_finish` | sdio | `hcpu_sdio.v` 731 | arm S_FINISH: dimasuki bila state bernilai S_FINISH di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.s_fail` | sdio | `hcpu_sdio.v` 740 | arm S_FAIL: dimasuki bila state bernilai S_FAIL di tepi yang mengambilnya -- cakupan per arm, bukan per cabang di dalamnya | 0 | — |
| `sdio.default` | sdio | `hcpu_sdio.v` 749 | state di luar kedua puluh nama: S_IDLE | 0 | — |
| `uart_tx.reset` | uart_tx | `hcpu_uart_tx.v` 40, 41, 42, 43, 44, 45 | rst_n rendah: S_IDLE, pencacah, indeks bit, dan penggeser nol; tx_out 1 (diam tinggi) | 53 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `uart_tx.idle_wait` | uart_tx | `hcpu_uart_tx.v` 48, 49, 50 | S_IDLE tanpa tx_start: tx_out 1, keadaan tetap | 178 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `uart_tx.idle_start` | uart_tx | `hcpu_uart_tx.v` 49, 50, 51, 52, 53 | S_IDLE dengan tx_start: tx_data masuk penggeser, S_START, pencacah nol | 0 | — |
| `uart_tx.start_count` | uart_tx | `hcpu_uart_tx.v` 58, 59, 64 | S_START: tx_out 0 (start bit), pencacah naik | 0 | — |
| `uart_tx.start_end` | uart_tx | `hcpu_uart_tx.v` 58, 59, 60, 61, 62 | S_START, pencacah = CLKS_PER_BIT-1: pencacah dan indeks bit nol, S_DATA | 0 | — |
| `uart_tx.data_count` | uart_tx | `hcpu_uart_tx.v` 69, 70, 78 | S_DATA: tx_out = tx_shift[bit_idx], pencacah naik | 0 | — |
| `uart_tx.data_next` | uart_tx | `hcpu_uart_tx.v` 69, 70, 71, 75 | S_DATA, pencacah = CLKS_PER_BIT-1, bit_idx < 7: pencacah nol, bit_idx naik (LSB lebih dulu) | 0 | — |
| `uart_tx.data_last` | uart_tx | `hcpu_uart_tx.v` 69, 70, 71, 72, 73 | S_DATA, pencacah = CLKS_PER_BIT-1, bit_idx = 7: pencacah nol, S_STOP | 0 | — |
| `uart_tx.stop_count` | uart_tx | `hcpu_uart_tx.v` 83, 84, 88 | S_STOP: tx_out 1 (stop bit), pencacah naik | 0 | — |
| `uart_tx.stop_end` | uart_tx | `hcpu_uart_tx.v` 83, 84, 85, 86 | S_STOP, pencacah = CLKS_PER_BIT-1: pencacah nol, S_IDLE | 0 | — |
| `uart_tx.default` | uart_tx | `hcpu_uart_tx.v` 92 | state di luar keempat nama: S_IDLE | 0 | — |
| `dataram.write` | dataram | `hcpu_dataram.v` 43, 44, 45 | we: mem[addr] <- wdata di tepi naik | 2 | 4, 6 |
| `dataram.read` | dataram | `hcpu_dataram.v` 43, 46, 47 | re tanpa we: rdata_r <- mem[addr], kata tersedia satu siklus sesudah alamat | 2 | 4, 6 |
| `dataram.hold` | dataram | `hcpu_dataram.v` 46, 50 | re rendah: rdata_r tetap, dan rdata adalah rdata_r | 229 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 |
| `dataram.read_first` | dataram | `hcpu_dataram.v` 40, 41, 42, 44, 45, 46, 47 | re dan we di tepi yang sama, alamat sama: rdata_r mendapat kata lama (read-first) | 0 | — |
| `dataram.initial_zero` | dataram | `hcpu_dataram.v` 53, 55, 56, 57, 59 | baca kata yang belum pernah ditulis: nol dari blok initial -- hanya simulasi (synthesis translate_off) | 0 | — |
| `rom.letter_entry` | rom | `hcpu_rom.v` 29, 30, 31 | alamat 1-28 diambil HLOAD atau opcode huruf: vektor huruf, valid 1 | 11 | 1, 2, 7, 9, 10, 11 |
| `rom.negative_entry` | rom | `hcpu_rom.v` 29, 30, 31 | alamat 31-36 diambil: vektor negatif uji guard, valid 1 | 1 | 5 |
| `rom.invalid` | rom | `hcpu_rom.v` 264, 265, 266 | alamat lain diambil: nol, valid 0 (HC-01 bila lewat HLOAD) | 0 | — |
| `guard.pass` | guard | `hcpu_guard.v` 104, 105 | HGRD dieksekusi, keenam guard lulus: FLAGS.G 1 (hcpu_execute.v baris 492) | 2 | 1, 2 |
| `guard.g1_fail` | guard | `hcpu_guard.v` 66, 68 | HGRD dieksekusi, G1 gagal: A_N bukan jumlah zona titik | 0 | — |
| `guard.g2_fail` | guard | `hcpu_guard.v` 71, 72 | HGRD dieksekusi, G2 gagal: A_K bukan jumlah zona garis | 0 | — |
| `guard.g3_fail` | guard | `hcpu_guard.v` 75, 76 | HGRD dieksekusi, G3 gagal: A_Q bukan jumlah zona lengkung | 0 | — |
| `guard.g4_fail` | guard | `hcpu_guard.v` 80, 82 | HGRD dieksekusi, G4 gagal: Theta kurang dari U | 1 | 5 |
| `guard.t1_fail` | guard | `hcpu_guard.v` 95 | HGRD dieksekusi, T1 gagal: Ks tanpa Qc | 0 | — |
| `guard.t2_fail` | guard | `hcpu_guard.v` 101 | HGRD dieksekusi, T2 gagal: Kc tanpa Qc | 0 | — |
| `guard.u` | guard | `hcpu_guard.v` 80, 91 | CU dieksekusi: U dari guard (hcpu_execute.v baris 248) | 1 | 11 |
| `guard.rho` | guard | `hcpu_guard.v` 90, 92 | CRHO dieksekusi: rho dari guard (hcpu_execute.v baris 249) | 1 | 11 |
| `calu.hcadd` | calu | `hcpu_codex_alu.v` 128 | HCADD dieksekusi: jumlah per komponen | 3 | 2, 11 |
| `calu.letter` | calu | `hcpu_codex_alu.v` 128 | opcode huruf dieksekusi: jumlah dengan vektor ROM (hcpu_execute.v baris 202, 219, 271) | 0 | — |
| `calu.hnrm2` | calu | `hcpu_codex_alu.v` 129 | HNRM2 dieksekusi: norma kuadrat | 1 | 2 |
| `calu.hdist` | calu | `hcpu_codex_alu.v` 130 | HDIST dieksekusi: jarak kuadrat | 0 | — |
| `calu.cget` | calu | `hcpu_codex_alu.v` 148, 149 | CGET dengan indeks 0-17: satu komponen | 9 | 9, 10 |
| `calu.cget_outside` | calu | `hcpu_codex_alu.v` 148, 149 | CGET dengan indeks di atas 17: nol | 1 | 9 |
| `calu.cset` | calu | `hcpu_codex_alu.v` 135 | CSET dengan indeks 0-17: satu komponen ditulis | 2 | 10 |
| `calu.cset_outside` | calu | `hcpu_codex_alu.v` 135 | CSET dengan indeks di atas 17: register tetap | 1 | 10 |
| `calu.cmod4` | calu | `hcpu_codex_alu.v` 139 | CMOD4 dieksekusi: dua bit rendah Theta | 1 | 11 |
| `calu.default` | calu | `hcpu_codex_alu.v` 150, 151, 152, 153 | op 6 atau 7: nol | 0 | — |
| `hisab.word0` | hisab | `hcpu_hisab.v` 94 | HPACK dengan S2 0: word nibble 0 (hcpu_execute.v baris 256) | 1 | 7 |
| `hisab.word1` | hisab | `hcpu_hisab.v` 95 | HPACK dengan S2 1: word nibble 1 (hcpu_execute.v baris 257) | 1 | 7 |
| `hisab.word2` | hisab | `hcpu_hisab.v` 96 | HPACK dengan S2 2: byte 8 dan status guard (hcpu_execute.v baris 258) | 1 | 7 |
| `hisab.word_none` | hisab | `hcpu_hisab.v` 96 | HPACK dengan S2 di atas 2: nol (hcpu_execute.v baris 259) | 1 | 7 |
| `hisab.crc` | hisab | `hcpu_hisab.v` 128, 141, 143 | HCRC dieksekusi: CRC32 frame huruf (hcpu_execute.v baris 260) | 1 | 7 |
| `mul.mul` | mul | `hcpu_mul.v` 27, 63 | MUL dieksekusi: 32 bit rendah perkalian (hcpu_execute.v baris 157) | 0 | — |

Tercakup 47 dari 162 transisi di luar pipeline; pipeline sendiri 45 dari 78 (pipeline_audit). Tidak tercakup — transisi RTL HCPU yang tidak dijalankan tb_hcpu_top.v: dinyatakan di sini dengan alasannya, tidak dianggap terbukti. Pemancar menjawab bench yang sama dengan fungsinya, jadi alasannya milik spec fungsi itu:

- `print.print_accept` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.emits_accept` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.conv_zero` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.conv_digit` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.conv_done` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.send` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.send_hold` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.wait_newline` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.wait_next` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.wait_hold` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.newline` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.newline_hold` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.s_addr` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.s_char_end` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.s_char_send` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.s_char_hold` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.s_wait_next` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.s_wait_hold` — arm PRINT dan EMITS tidak pernah didekode (pipeline_audit): ex_is_print dan ex_is_emits 0 di setiap tepi, jadi print_state tetap P_IDLE.
- `print.default` — tidak terjangkau: print_state tiga bit (hcpu_top.v baris 247) dan kedelapan nilainya bernama (baris 262-266, 279-281).
- `trap.eret` — arm ERET tidak pernah didekode (pipeline_audit): trap_is_eret_w 0 di setiap tepi.
- `trap.eret_mode_bypass` — tidak ada ERET, dan trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `trap.eret_epc_bypass` — tidak ada ERET, dan trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `trap.fire_timer` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik: expired timer tidak pernah naik, compare tetap 0xFFFFFFFF sejak reset, dan enable 0.
- `trap.fire_uart_rx` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik: rx_ready 0, karena uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `trap.fire_illegal` — tidak terjangkau: src_illegal diikat 1'b0 (hcpu_top.v baris 798).
- `trap.fire_priv` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik: fault hak istimewa hanya ada di mode pengguna (hcpu_execute.v baris 310), dan mode tetap supervisor sejak reset.
- `trap.fire_mem` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik: fault memori hanya ada di mode pengguna (hcpu_execute.v baris 317), dan mode tetap supervisor sejak reset.
- `trap.fire_syscall` — arm SYSCALL tidak pernah didekode (pipeline_audit): pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik.
- `trap.pending_masked` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik.
- `trap.held_active` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik.
- `trap.held_pc_invalid` — pending unit trap 0 di setiap tepi: tak satu pun sumbernya naik.
- `trap.write_vector` — trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `trap.write_epc` — trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `trap.write_enable` — trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `trap.write_mode` — trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `trap.write_readonly` — trap_reg_we 0 di setiap tepi: tidak ada tulis ke register trap 0xFF8-0xFFD.
- `mmio.rx_hold` — rx_valid penerima 0 di setiap tepi: uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.rx_overrun_set` — rx_valid penerima 0 di setiap tepi: uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.rx_read_clear` — tidak ada baca 0xFF0: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.timer_compare_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.timer_clear` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.timer_expire` — counter tidak pernah sama dengan compare: compare tetap 0xFFFFFFFF sejak reset, dan tiap program mulai dari reset.
- `mmio.mem_base_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.mem_limit_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.imem_addr_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.imem_data_advance` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.sd_cmd_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.sd_sector_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.sd_control_write` — tidak ada tulis ke jendela periferal: bus data membawa empat akses di seluruh bench, tulis dan baca ke alamat 0 dan 10.
- `mmio.sd_data_advance` — tidak ada alamat blok kartu 0xFE0-0xFEF di bus di tepi mana pun.
- `mmio.read_counter` — addr[3:0] 4 di luar blok kartu tidak pernah muncul di bus di tepi hidup mana pun.
- `mmio.read_mem_base` — addr[3:0] 0xE tidak pernah muncul di bus di tepi hidup mana pun.
- `mmio.read_other` — addr[3:0] 7 tidak pernah muncul di bus di tepi hidup mana pun.
- `mmio.read_sd_status` — tidak ada alamat blok kartu 0xFE0-0xFEF di bus di tepi mana pun.
- `mmio.read_sd_sector` — tidak ada alamat blok kartu 0xFE0-0xFEF di bus di tepi mana pun.
- `mmio.read_sd_control` — tidak ada alamat blok kartu 0xFE0-0xFEF di bus di tepi mana pun.
- `mmio.read_sd_other` — tidak ada alamat blok kartu 0xFE0-0xFEF di bus di tepi mana pun.
- `mmio.u_rx.idle_falling_edge` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.start_count` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.start_confirmed` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.start_glitch` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.data_count` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.data_sample` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.data_last` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.stop_count` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `mmio.u_rx.stop_deliver` — uart_rx tidak disambung bench dan ditarik ke 1 (hcpu_top.v baris 723): rx_sync 1 di setiap tepi, penerima tidak pernah meninggalkan IDLE.
- `sdio.soft_reset` — sd_soft_rst 0 di setiap tepi: tidak ada tulis SD_CONTROL (0xFE4).
- `sdio.clk_toggle` — clk_en 0 di setiap tepi: pengendali tidak pernah mulai.
- `sdio.clk_count` — clk_en 0 di setiap tepi: pengendali tidak pernah mulai.
- `sdio.port_fsm` — busy 0 di setiap tepi: pengendali tidak pernah mulai.
- `sdio.buf_write` — wr_en 0 di setiap tepi: tidak ada tulis SD_DATA (0xFE3) dan pengendali tidak pernah sibuk.
- `sdio.idle_init` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.idle_not_init` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.idle_transfer` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_powerup` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_cmd_setup` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_cmd_send` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_cmd_gap` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_resp_wait` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_resp_recv` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_resp_done` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_dat_wait` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_dat_recv` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_dat_crc` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_gap` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_start` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_data` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_crc` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_end` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_ack` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_wr_busy` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_finish` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.s_fail` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `sdio.default` — state pengendali tetap S_IDLE di setiap tepi: tidak ada tulis SD_CMD (0xFE0), jadi start tidak pernah naik.
- `uart_tx.idle_start` — tb_hcpu_top.v tidak menjalankan PRINT atau EMITS, jadi mesin keadaan cetak hcpu_top tidak pernah menaikkan uart_start: tx_start 0 di setiap tepi dan pemancar tidak pernah meninggalkan S_IDLE.
- `uart_tx.start_count` — start bit tidak pernah dikirim: S_START tidak pernah dimasuki, dan pencacah bit tidak pernah bergerak -- CLKS_PER_BIT dari parameter bench tidak teruji perilakunya.
- `uart_tx.start_end` — akhir start bit: S_START tidak pernah dimasuki.
- `uart_tx.data_count` — bit data tidak pernah dikirim: S_DATA tidak pernah dimasuki.
- `uart_tx.data_next` — peralihan ke bit berikutnya, LSB lebih dulu: S_DATA tidak pernah dimasuki.
- `uart_tx.data_last` — bit kedelapan dan peralihan ke stop bit: S_DATA tidak pernah dimasuki.
- `uart_tx.stop_count` — stop bit tidak pernah dikirim: S_STOP tidak pernah dimasuki.
- `uart_tx.stop_end` — kembali ke S_IDLE sesudah stop bit: S_STOP tidak pernah dimasuki.
- `uart_tx.default` — state dua bit punya empat nilai dan keempatnya bernama; cabang ini hanya dicapai keadaan x atau z, dan bench mereset sejak waktu 0.
- `dataram.read_first` — re dan we tidak pernah tinggi di tepi yang sama: empat akses di seluruh bench, dua tulis lalu dua baca.
- `dataram.initial_zero` — kedua baca membaca kata yang sudah ditulis program yang sama: alamat 0 di program 4, alamat 10 di program 6.
- `rom.invalid` — tidak ada HLOAD dengan indeks di luar 1-28 dan 31-36: HC-01 tidak tercakup pipeline_audit.
- `guard.g1_fail` — satu-satunya vektor negatif yang diambil adalah indeks 31 (program 5), yang hanya menjatuhkan G4; vektor 32-36 tidak pernah dimuat.
- `guard.g2_fail` — satu-satunya vektor negatif yang diambil adalah indeks 31 (program 5), yang hanya menjatuhkan G4; vektor 32-36 tidak pernah dimuat.
- `guard.g3_fail` — satu-satunya vektor negatif yang diambil adalah indeks 31 (program 5), yang hanya menjatuhkan G4; vektor 32-36 tidak pernah dimuat.
- `guard.t1_fail` — satu-satunya vektor negatif yang diambil adalah indeks 31 (program 5), yang hanya menjatuhkan G4; vektor 32-36 tidak pernah dimuat.
- `guard.t2_fail` — satu-satunya vektor negatif yang diambil adalah indeks 31 (program 5), yang hanya menjatuhkan G4; vektor 32-36 tidak pernah dimuat.
- `calu.letter` — tidak ada opcode huruf 0xE0-0xFB di kesebelas program: decode_letter tidak tercakup pipeline_audit.
- `calu.hdist` — arm HDIST tidak pernah didekode (pipeline_audit).
- `calu.default` — tidak terjangkau: hcpu_execute.v baris 202-207 hanya memberi op 0-5.
- `mul.mul` — arm MUL tidak pernah didekode (pipeline_audit).

Batas yang tercakup — yang dijalankan bench, dan apa yang pemakaiannya tidak tunjukkan:

- `mmio.read_*` — delapan aturan baca yang dijalankan adalah register periph_rdata, yang hcpu_mmio.v baris 329-373 perbarui dari alamat bus di setiap siklus, dengan atau tanpa re. periph_sel 0 di setiap tepi: tak satu pun nilai itu sampai ke rdata, jadi tidak ada baca MMIO yang terbukti.
- `rom.letter_entry` — hanya lewat HLOAD: tidak ada opcode huruf di kesebelas program.
- `rom.negative_entry` — hanya indeks 31, program 5.
- `sdio.buf_read` — sbuf tidak pernah ditulis: tiap tepi membaca word yang x, dan buf_rdata x di setiap tepi.
- `dataram.read` — dua baca, masing-masing kata yang program itu sendiri tulis sebelumnya.

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.rtl_function --verify
```
