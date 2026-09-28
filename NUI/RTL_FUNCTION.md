# Model RTL sebagai fungsi — Lapis 6

Dihasilkan `src/hijaiyyah/nui/rtl_function.py` dari `NUI/spec/rtl_function.json`. RTL dan bench dikompilasi apa adanya dengan satu modul probe di sampingnya yang mencetak register desain sekali tiap siklus; tidak ada port atau baris yang berubah. Simulator: Icarus Verilog version 14.0 (devel) (s20260301-394-g9edaf7b6a-dirty).

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

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.rtl_function --verify
```
