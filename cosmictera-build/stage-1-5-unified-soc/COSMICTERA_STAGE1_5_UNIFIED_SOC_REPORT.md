# Laporan Rekayasa Prototipe COSMICTERA CT-01-REV13 Unified SoC Stage 1.5

**Target Perangkat Keras:** Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`family=GW2A-18C`)  
**Baseline Awal:** `HEAD = ea3c5b22` (Cabang Terisolasi: `stage-1-5-unified-soc`)  
**Direktori Kerja Terisolasi:** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/`  
**Status Pemrograman Perangkat Keras:** **TIDAK DIPROGRAM** (SRAM maupun External Flash tidak disentuh sesuai mandat prototipe Stage 1.5)

## 1. Ringkasan Eksekutif & Pencapaian Target Penerimaan

Prototipe **Unified SoC Stage 1.5** (`cosmictera_unified_soc_top`) yang menyatukan subsistem komputasi **HCPU Core** (`hcpu_gowin_core` dari `rtl/fpga/gowin/hcpu_gowin_top.v`) dengan subsistem **Boot Display Stage 1.5 Berbasis BSRAM** (`P0–P12`, `1280x720@60Hz` HDMI, 16-entry Compute Ecosystem Grid, dan 87-bit CDC Telemetry Bridge) telah selesai dibangun, diverifikasi (`33 PASS, 0 FAIL`, `0 / 194.048` selisih piksel golden frame), disintesis, ditempatkan dan dirutekan (`nextpnr-himbaechel`), serta dikemas menjadi bitstream prototipe (`cosmictera_unified_soc_stage1_5.fs`).

| Metrik Penerimaan | Kapasitas `GW2AR-LV18QN88C8/I7` | Target Prototipe | Hasil Aktual Unified SoC Stage 1.5 | Status |
| :--- | :--- | :--- | :--- | :--- |
| **LUT4 (Post-Pack)** | `20.736` | `<= 18.500` (`89,22%`) / `<= 18.247` (`88,00%`) | **`14.695 / 20.736` (`70,87%`)** | **LULUS (`-3.805` LUT4 dari target awal; `-3.552` LUT4 dari batas 88%)** |
| **LUT1–4 (Pre-Pack Yosys)** | `20.736` | Di bawah kapasitas | **`12.047`** (`1.054` LUT1 + `1.132` LUT2 + `2.340` LUT3 + `7.521` LUT4) | **LULUS (`58,10%`)** |
| **ALU (Pre-Pack / Post-Pack)** | `15.552` | Di bawah kapasitas | **`2.231` (Pre-Pack) / `2.600` (Post-Pack, `16,72%`)** | **LULUS** |
| **DFF (Total Flip-Flop)** | `15.552` | Di bawah kapasitas | **`5.546` (Pre-Pack) / `5.572` (Post-Pack, `35,83%`)** | **LULUS (`1.137` Constrained LUTFF pairs)** |
| **BSRAM (`18 Kbit`)** | `46` | Di bawah kapasitas | **`38 / 46` (`82,61%`)** (`18` HCPU + `20` Boot Display) | **LULUS (`8` BSRAM tersisa)** |
| **DSP (`MULT36X36` / `MULT9X9`)** | `12` / `96` | Di bawah kapasitas | **`1 / 12` (`8,33%`) `MULT36X36`, `14 / 96` (`14,58%`) `MULT9X9`** | **LULUS (HMCL Layer A1 DSP aktif)** |
| **SSRAM (`RAM16SDP4`)** | `648` | Di bawah kapasitas | **`6 / 648` (`0,93%`)** | **LULUS** |
| **Unrouted Net** | `0` | `0` | **`0` dari `68.942` routed arcs** | **LULUS** |
| **DRC / Congestion Error** | `0` | `0` | **`0 error, 0 warning, 0 combinational loop`** | **LULUS** |
| **Fmax Post-Route `clk_27m`** | Target `27,00 MHz` (`37,04 ns`) | `>= 27,00 MHz` | **`120,88 MHz` (jalur kritis `8,27 ns`, slack `+28,76 ns`)** | **LULUS (`4,48x` target)** |
| **Fmax Post-Route `pixel_clk`** | Target `74,25 MHz` (`13,47 ns`) | `>= 74,25 MHz` | **`75,83 MHz` (jalur kritis `13,19 ns`, slack `+0,28 ns`)** | **LULUS** |

## 2. Arsitektur Integrasi & Optimasi BSRAM (Tahap A, B, dan C)

1. **Tahap A — Isolasi & Hierarki Subsistem (`hcpu_gowin_core`)**:
   - Cabang Git `stage-1-5-unified-soc` dibuat dari `HEAD = ea3c5b22` tanpa mengubah satu byte pun pada artefak Stage 1.4 (`cosmictera-build/stage-1-4-boot-rom/`), bitstream standalone HCPU (`hcpu_gowin_top_standalone.fs`), file constraint `constraints/cosmictera_tangnano20k.cst`, maupun RTL kanonik `rtl/hcpu_*.v`.
   - Top-level baru `rtl/cosmictera_unified_soc_top.v` menginstansiasi `hcpu_gowin_core` (`USE_PLL=0`, `USE_DSP=1`, `PROGRAM_HEX="program.hex"`, `BAUD=115200`) secara langsung sebagai subsistem komputasi tanpa duplikasi generator clock atau pengontrol reset top-level.
2. **Tahap B — Optimasi Tabel Teks, Tag Sel, Chrome & Emblem ke BSRAM (`20 BSRAM` Boot Display)**:
   - `boot_text_rom.hex` (`4.096 x 12-bit`, `3 SP` BSRAM): menyimpan matriks karakter dasar 25 baris (`160` kolom), termasuk stempel waktu statis `EV01..EV05` (`00:00:00` dalam `C_GOLD`) dan digit puluhan FIFO `0`.
   - `boot_comp_rom.hex` (`4.096 x 12-bit`, `3 SP` BSRAM): menyimpan 60 irisan string dinamis dan seluruh 12 halaman inspektor arsitektur `P1–P12` yang diindeks oleh `{comp_slice[5:0], la_col[5:0]}`.
   - `boot_cell_tag_rom.hex` (`4.096 x 8-bit`, `2 SP` BSRAM): menggantikan pohon dekoder koordinat kombinasional `160x90` pada `cosmictera_boot_compositor.v` dengan tag per-sel sinkron `{tag_gold[7], is_r56_nib[6], tag_code[5:0]}` pada Stage 0 -> Stage 1.
   - `boot_bg_x_rom.hex` (`2.048 x 8-bit`, `1 SP` BSRAM) & `boot_bg_y_rom.hex` (`1.024 x 8-bit`, `1 SP` BSRAM): menggantikan dekoder kolom/baris kombinasional pada `cosmictera_boot_render.v` dengan pembacaan BSRAM sinkron yang diselaraskan tepat 1 siklus sebelum koordinat aktif `(h_count, v_count)`.
   - `boot_emblem_rom.hex` (`4.096 x 4-bit`, `1 SP` BSRAM): menggantikan tabel kuadran radial 24x24 Header Mini-Emblem (`x = 28..51, y = 18..41`) pada `cosmictera_boot_logo_rom.v`.
   - `logo_rle_rom.hex` (`16.384 x 9-bit`, `8 SPX9` BSRAM) & `hcpu_font8x8.hex` (`1.024 x 8-bit`, `1 SPX9` BSRAM): dipertahankan utuh tanpa pengurangan resolusi atau glyph.
3. **Tahap C — Infrastruktur Bersama & Jembatan Telemetri CDC 87-Bit**:
   - Referensi clock `27,000 MHz` (`clk_27m`, Pin 4) dibagi bersama antara `u_hcpu_core`, `TMDS_rPLL`, `u_reset_seq`, `u_uptime`, dan `u_subsys_bridge`.
   - Synchronizer reset peka-tepi (`btn_rst_n`, Pin 87) memulihkan HCPU sekaligus men-toggle `live_hcpu_mode` pada `u_subsys_bridge`, mengalirkan bus telemetri perangkat keras 84-bit (`hcpu_tele_pc`, `hcpu_tele_instr`, `hcpu_tele_halted`, `hcpu_tele_guard`, `hcpu_tele_cycles`, `hcpu_tele_flags`) melintasi jembatan CDC toggle-handshake (`clk_27m -> pixel_clk`) ke Region 5.

## 3. Perbandingan Resource Terhadap Baseline Standalone

| Metrik Perangkat Keras | HCPU Standalone (`hcpu_gowin_top`) | Boot Display Stage 1.4 (`cosmictera_boot_top`) | Boot Display Stage 1.5 (`cosmictera_boot_top`) | Penjumlahan Naif (HCPU + Stage 1.4) | Unified SoC Stage 1.5 (`cosmictera_unified_soc_top`) | Selisih vs Penjumlahan Naif |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pre-Pack Yosys `LUT1–4`** | `12.767` | `3.892` | **`1.268`** | `16.659` | **`12.047`** | **`-4.612` LUT (`-27,68%`)** |
| **Post-Pack `nextpnr` `LUT4`** | `15.377` (`74,16%`) | `5.438` (`26,22%`) | **`1.804` (`8,70%`)** | `20.815` (`100,38%`) | **`14.695` (`70,87%`)** | **`-6.120` LUT4 (`-29,40%`)** |
| **Post-Pack `ALU`** | `2.225` (`14,31%`) | `1.546` (`9,94%`) | **`536` (`3,45%`)** | `3.771` (`24,25%`) | **`2.600` (`16,72%`)** | **`-1.171` ALU (`-31,05%`)** |
| **Post-Pack `DFF`** | `5.166` (`33,22%`) | `655` (`4,21%`) | **`427` (`2,75%`)** | `5.821` (`37,43%`) | **`5.572` (`35,83%`)** | **`-249` DFF (`-4,28%`)** |
| **Post-Pack `BSRAM`** | `18 / 46` (`39,13%`) | `9 / 46` (`19,57%`) | **`20 / 46` (`43,48%`)** | `27 / 46` (`58,70%`) | **`38 / 46` (`82,61%`)** | **`+11` BSRAM (optimasi ROM)** |
| **DSP (`MULT36X36` / `MULT9X9`)** | `0` / `0` (`-nodsp`) | `0` / `0` | **`0` / `0`** | `0` / `0` | **`1` / `14`** | **Aktif (HMCL Layer A1 DSP)** |
| **Fmax Post-Route `clk_27m`** | `54,69 MHz` | `60,18 MHz` | **`142,92 MHz`** | — | **`120,88 MHz`** | **`+66,19 MHz` di atas HCPU** |
| **Fmax Post-Route `pixel_clk`** | — | `60,18 MHz` | **`96,53 MHz`** | — | **`75,83 MHz`** | **`+15,65 MHz` di atas Stage 1.4** |

## 4. Bukti Verifikasi RTL (`33 PASS, 0 FAIL`) & Kesamaan Piksel Golden Frame (`0 Diff`)

Simulasi terpadu `tb_unified_soc_stage1_5.v` (`tb_unified_soc_stage1_5.log`) menguji seluruh 33 gerbang verifikasi:
- **T01–T24f (29 Pengujian Kanonik Boot Display Stage 1.4)**:
  - Ketepatan waktu VESA `1280x720@60Hz` (`1650 x 750`), disparitas TMDS `[-8..+8]`, kualifikasi PLL lock `2 ms`, transisi `STARTUP -> READY -> ERROR`, event FIFO `EV01..EV06`, BCD uptime CDC, 16-entry Compute Ecosystem grid (`32'hAAAA_AAAA`), isolasi fault per-subsistem (`HMCL` & `HIJRAH`), dan navigasi tombol Pin 88 melintasi seluruh 13 halaman `P0 -> P1..P12 -> P0`.
- **T25 (Paritas UART 23-Byte HCPU Standalone & LED)**:
  - `u_hcpu_core` mengeksekusi `program.hex` pada `27 MHz`, berhenti (`halted = 1`) dengan `guard_ok = 1` (`led[1:0] = 2'b00` aktif-rendah), dan memancarkan tepat **23 byte** melalui Pin 69 (`uart_txd`) pada `115.200` baud:
    `31 31 32 0d 0a 43 59 43 4c 45 53 3d 30 30 30 30 31 42 38 39 0d 0a 0a` (`"112\r\nCYCLES=00001B89\r\n\n"`), identik bit-demi-bit dengan hasil uji perangkat keras SRAM Tang Nano 20K (`PAPAN.md`).
- **T26 (Jembatan Telemetri CDC Live HCPU -> Layar HDMI Region 5)**:
  - Saat `sim_use_live_hcpu = 1`, jembatan CDC 87-bit menangkap status aktual `u_hcpu_core` (`snap_cycles = 32'h0000_1B89`, `snap_halted = 1'b1`, `snap_guard = 1'b0`) dan merender string `CY:00001B89 ... G:OK HLT CDC:LIVE` secara koheren pada baris 56 Region 5 tanpa pergeseran karakter.
- **T27 (Paritas HISA `CTHETA=0x4E`, `HDOT=0x52`, & `GAP-02` Guard-HISAB)**:
  - Di dalam top-level Unified SoC, eksekusi `HLOAD H1, [27]` diikuti `CTHETA R10, H1` menghasilkan `R10 = 8`, `HDOT R11, H1, H1` selesai dalam 14 siklus menghasilkan `<Haa, Haa>_14 = 69`, dan `HPACK` (ketika `id_is_hisab = 1`) menulis `guard_status = 32'h0000_003F` (`G1..G4` + `T1..T2` aktif) ke `RAM[18]`, membuktikan perbaikan `GAP-02` tetap utuh.

### Kesamaan Bit-demi-Bit Golden Frame (`0 / 194.048` Selisih Piksel)

| Berkas Golden Frame (`.raw`) | Dimensi / Cakupan | SHA-256 Stage 1.4 Kanonik | SHA-256 Unified SoC Stage 1.5 | Selisih Piksel |
| :--- | :--- | :--- | :--- | :--- |
| `rtl_hero_logo_512x184.raw` | `512 x 184` (`94.208` piksel) | `33734404bca030b129b3d7f0968af2d0f592693104068b4d476ebf0b9d85d7e5` | `33734404bca030b129b3d7f0968af2d0f592693104068b4d476ebf0b9d85d7e5` | **`0 / 94.208`** |
| `rtl_scanlines_startup.raw` | `26 x 1280` (`33.280` piksel) | `270dde9257d97d38fa0146eaf5a8ec1a91dafcbc165076ed9d5e8d8f4d290a14` | `270dde9257d97d38fa0146eaf5a8ec1a91dafcbc165076ed9d5e8d8f4d290a14` | **`0 / 33.280`** |
| `rtl_scanlines_ready.raw` | `26 x 1280` (`33.280` piksel) | `72c2aeb512f71338471a9f10fd1c512864db2b583a679ed04698296f9d43681f` | `72c2aeb512f71338471a9f10fd1c512864db2b583a679ed04698296f9d43681f` | **`0 / 33.280`** |
| `rtl_scanlines_error.raw` | `26 x 1280` (`33.280` piksel) | `ffd5b7449a9d80362488991a14670f812cc3a621d846e8f6ce6cb134c714028c` | `ffd5b7449a9d80362488991a14670f812cc3a621d846e8f6ce6cb134c714028c` | **`0 / 33.280`** |
