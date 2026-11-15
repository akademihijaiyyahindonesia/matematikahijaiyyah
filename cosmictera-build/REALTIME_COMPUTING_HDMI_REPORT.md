# Laporan Pengembangan & Verifikasi: CosmicTera Real-Time Computing & 5-Panel NUI HDMI Monitor

- **Branch Kerja**: `feat/realtime-computing-hdmi` (bercabang dari `920f3e61`)
- **Perangkat Keras Target**: Tang Nano 20K (`GW2AR-LV18QN88C8/I7`, keluarga `GW2A-18C`, resolusi HDMI `1280×720 @ 60 Hz`)
- **Identitas Bitstream Baru (`hcpu_hdmi_top.fs`)**: `7.261.470` byte · SHA-256: `da26838e4f7a90468a2673c0caeb43971c4519c7a91d17a4a8a9d586182197f9`

## 1. Perlindungan Checkpoint & Baseline Sebelumnya

Seluruh baseline dan checkpoint yang telah teruji fisik sebelumnya dijaga tetap utuh 100% dan tidak tertimpa:

| Komponen / Arsip | Identitas Commit / Hash | Status Verifikasi |
| :--- | :--- | :--- |
| **Baseline `stage-1-5-security-integration`** | `ea3c5b22445ed322b8e10348f930b4fa75731885` | **Terkunci (23 / 23 OK)** pada `COSMICTERA_USSS_STAGE1_5_SHA256_MANIFEST.txt` |
| **Checkpoint Opsi A HDMI (`11452b9c`)** | `a416ada7...b413f` | **Utuh (8 / 8 OK)** pada `cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/` |
| **Checkpoint M5.2B Fix (`920f3e61`)** | `1fd4c35b698f5385c60b3922dc5ce16c2e2c3edabcc2048b8626a5d1de462f54` | **Utuh (7 / 7 OK)** pada `cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_m52b_fix_920f3e61/` + salinan `hcpu_hdmi_top_920f3e61.fs` |
| **Koordinat Pos Kompositor (`rtl/hcpu_dashboard_pos.vh`)** | 8 field hidup (`state`, `pc`, `instr`, `cycle`, `flags`, `guard`, `page`, `banner`) | **0 bit berubah** (`git diff rtl/hcpu_dashboard_pos.vh` bersih; `sim_dashboard` **13 / 13 PASS**) |
| **Sidik Jari `hcpu_gowin_top.v` & Segel Lapis 6** | `a866810782d7b2dbaaf331481e5806ec09d86ac031c1a50906b171ecca5d5291` | **100% Utuh** (`hcpu_realtime_monitor` ditempatkan di dalam `rtl/fpga/gowin/hcpu_hdmi_top.v`) |

## 2. Audit Jujur 15 Komponen CosmicTera & NUI L0–L11 pada Tang Nano 20K

| No | Komponen | Status Aktual di Tang Nano 20K | Bukti Implementasi & Sinyal HDMI yang Tersedia |
| :---: | :--- | :--- | :--- |
| 1 | **HCPU & H-ISA** | Berfungsi Penuh di Hardware | 84 opcode RTL aktif (`rtl/hcpu_pkg.vh`); mengekspos `tele_pc`, `tele_instr`, `tele_halted`, `tele_guard`, `tele_cycles`, `tele_flags`, dan `uart_txd` |
| 2 | **Decoder & Execution Unit** | Berfungsi Penuh di Hardware | `rtl/hcpu_decode.v` & `rtl/hcpu_execute.v` dengan `USE_DSP=1` (`14× MULT9X9`, `1× MULT36X36`) |
| 3 | **HCPU Pipeline & Register** | Berfungsi di Hardware (State Internal Tidak Diekspos) | Pipeline 5-tahap (`IF/ID/EX/MEM/WB`), 16 GPR teralamati 4-bit (`R0–R15`), 16 H-Reg 144-bit (`H0–H15`); status internal pipeline ditampilkan jujur sebagai `NOT INSTRUMENTED` |
| 4 | **Hybit 18D** | Berfungsi Penuh di Hardware | Vektor 144-bit (`18 × 8-bit`) di `rtl/hcpu_regfile.v` dan `rtl/hcpu_rom.v` (28 huruf + 6 vektor negatif) |
| 5 | **Matematika Hijaiyyah & Aljabar** | Berfungsi Penuh di Hardware | `HLOAD`, `HCADD`, `CGET`, `CSET`, `CMOV`, `CZERO`, `CEQ`, `CTHETA`, `CU`, `CRHO`, `CMOD4`, `HNRM2`, `HDIST`, `HDOT`, `HGRD`, dan 28 opcode huruf (`0xE0–0xFB`) di `rtl/hcpu_codex_alu.v` dan `rtl/hcpu_guard.v` |
| 6 | **HC, HASM, HBC, HVM, HCVM** | HASM/HBC Loader di Hardware; HC/HVM/HCVM di Host Python | `rtl/programs/loader.hasm` terpanggang di ROM FPGA (`LOAD_BASE = 64`); compiler HC dan VM berjalan di host Python |
| 7 | **HOS & Layanan Kernel** | Program HASM Tersedia, Belum Terinstrumentasi ke HDMI | `rtl/programs/kernel.hasm` dan `rtl/hcpu_trap.v` mendukung mode supervisor/user, timer, dan `SYSCALL`; sinyal internal trap dicatat `NOT INSTRUMENTED` |
| 8 | **HFS & Operasi Penyimpanan** | Controller SDIO Ada di RTL, Tidak Terinstrumentasi ke HDMI | `rtl/hcpu_sdio.v` terhubung di `0xFE0–0xFEF`, namun status internal kartu dicatat `NOT INSTRUMENTED` |
| 9 | **HAR & Komunikasi** | UART 115200 Aktif di Hardware; HAR di Host Python | `rtl/hcpu_uart_tx.v` & `rtl/hcpu_uart_rx.v` berjalan nyata pada pin 69/70 |
| 10 | **HPG-1** | Tersedia di Host Python | Paket protokol/gerbang di `src/hijaiyyah/`; belum disintesis sebagai blok RTL mandiri |
| 11 | **HMCL** | Tersedia di Host Python | Pustaka komputasi matriks/aljabar di Python |
| 12 | **HISAB** | Berfungsi Penuh di Hardware | `rtl/hcpu_hisab.v` mengeksekusi `HPACK` (`0x50`) dan `HCRC` (`0x51`) dalam 1 siklus |
| 13 | **Ka'bah & Jamrah** | Enam Guard Hardware Aktif; Topologi Penuh di Slot Terpisah | Enam guard aljabar (`G1–G4, T1–T2`) aktif di `rtl/hcpu_guard.v`; inti spons Ka'bah/Jamrah berada pada top-level tersendiri (`NOT INSTRUMENTED` pada slot HCPU HDMI) |
| 14 | **USSS & Security** | Berfungsi di Hardware | Enam guard invarian (`tele_guard`), proteksi memori `[mem_base, mem_limit)`, privilege `MODE_USER/MODE_SUPER`, dan pre-scan SDIO (`SD_CSUM/SD_PRESCAN`) |
| 15 | **NUI L0–L11** | L0 & L6 Terbukti di Hardware; L1–L5 & L7–L11 di Host/Kontrak | L0 (ekstraksi 5 fitur embedding fisika: `titik, garis, lengkung, theta, rho`) dan L6 (pipeline tampilan HDMI M5.2B 720p60 + telemetri CDC) berjalan langsung di FPGA |

## 3. Arsitektur `hcpu_realtime_monitor` & Optimasi Sumber Daya FPGA

1. **Penyatuan Label Statis di BSRAM ROM (`rtl/scripts/gen_dashboard.py`)**:
   - Seluruh label, bingkai 5 panel (**Panel A: HCPU Monitor**, **Panel B: Hijaiyyah & Hybit 18D**, **Panel C: Computing Stack**, **Panel D: NUI Monitor L0–L11**, dan **Panel E: Live Event Log**), serta prefiks/sufiks teks ditempatkan di dalam ROM tata letak BSRAM (`rtl/hcpu_dashboard.hex`, 8.192 sel × 12 bit).
   - Setiap medan angka hidup diselaraskan pada kolom kelipatan 16 (`col = 16, 32, 64, 112, 128`) dengan 4 digit heksadesimal hidup tepat pada indeks `pos = 4..7` (`pos[3:2] == 2'b01`).
2. **Dekoder Heksadesimal Tunggal & Sniffer UART On-Chip (`rtl/fpga/gowin/hcpu_hdmi_top.v`)**:
   - Di domain `clk_27m`, `hcpu_realtime_monitor` melacak langkah instruksi (`step_cnt`), opcode terakhir (`last_op`, `last_dst`, `last_s1`), opcode huruf (`0xE0..0xFB`), opcode kodeks (`0x40..0x4F, 0x60, 0x06, 0x07, 0x50..0x52`), cacah operasi matematika (`math_cnt`), serta menyadap jalur `hcpu_uart_txd` menggunakan `hcpu_uart_rx` untuk mem-parsing hingga 8 nilai desimal `OP_PRINT` ke dalam register `p0_titik..p7_hdot`.
   - Detektor `loader_entry` (`pc == 12'd64 && prev_pc < 12'd63`) secara otomatis mereset pencacah program dan slot `p0..p7` setiap kali `loader.hasm` melompat ke `0x040` untuk mengeksekusi program baru yang dikirim lewat UART.
   - Di domain `pixel_clk` (`74,25 MHz`), jabat tangan CDC 2-FF menyalin seluruh register secara koheren setiap `frame_tick`, dan satu fungsi `hexd(nib)` tunggal merender ke-25 medan heksadesimal hidup di kelima panel.

## 4. Hasil Sintesis Yosys, Place & Route `nextpnr-himbaechel`, dan Simulasi RTL

| Parameter Pengukuran | Checkpoint M5.2B Fix (`920f3e61`) | Real-Time 5-Panel Monitor (`da26838e`) | Batas Kapasitas GW2AR-18C | Status |
| :--- | :---: | :---: | :---: | :---: |
| **LUT4** | `14.193` (68%) | **`14.825` (71%)** | `20.736` | **LULUS** (Sisa 5.911 LUT4) |
| **ALU** | `2.698` (17%) | **`2.890` (18%)** | `15.552` | **LULUS** |
| **DFF** | `5.521` (35%) | **`5.964` (38%)** | `15.552` | **LULUS** |
| **BSRAM** | `24` (52%) | **`24` (52%)** | `46` | **LULUS** |
| **MULT9X9 (Hard DSP)** | `14` (14%) | **`14` (14%)** | `96` | **LULUS** |
| **MULT36X36 (Hard DSP)** | `1` (8%) | **`1` (8%)** | `12` | **LULUS** |
| **Fmax `u_hcpu.clk_27m`** | `102,05 MHz` | **`110,83 MHz`** | Target `27,00 MHz` | **LULUS** |
| **Fmax `pixel_clk`** | `90,44 MHz` | **`77,26 MHz`** | Target `74,25 MHz` | **LULUS** |
| **Simulasi `sim_dashboard`** | `13 / 13 PASS` | **`13 / 13 PASS`** | 13 pemeriksaan | **LULUS** |
| **Simulasi `tb_realtime_hdmi`** | — | **`8 / 8 Print + 5 Panel PASS`** | `2, 2, 2, 6, 6, 112, 10, 9` | **LULUS** |
