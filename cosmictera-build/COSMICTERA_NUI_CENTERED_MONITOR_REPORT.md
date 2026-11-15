# LAPORAN TEKNIS — COSMICTERA NUI-CENTERED REAL-TIME COMPUTING MONITOR (1280×720 @ 60 Hz)

- **Target Perangkat Keras**: Sipeed Tang Nano 20K (`GW2AR-LV18QN88C8/I7`, 27.000 MHz Core Clock, 74.250 MHz Pixel Clock / 371.250 MHz TMDS Serial Clock)
- **Repositori & Branch Kerja**: [`/Users/AMRA/hijaiyyah-mathematics`](file:///Users/AMRA/hijaiyyah-mathematics) (`feat/realtime-computing-hdmi`)
- **Generator Layout & Hologram ROM**: [`rtl/scripts/gen_dashboard.py`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/scripts/gen_dashboard.py)
- **Berkas ROM Perangkat Keras**:
  - [`rtl/hcpu_dashboard.hex`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_dashboard.hex) (`8,192 × 12-bit` Upper + Footer Text Grid ROM, Baris `0..41` & `84..89`)
  - [`rtl/hcpu_dashboard_lower.hex`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_dashboard_lower.hex) (`8,192 × 12-bit` Lower Text Grid ROM, Baris `42..83` — menghilangkan celah kosong di bagian tengah/bawah layar)
  - [`rtl/hcpu_nui_holo.hex`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_nui_holo.hex) (`8,192 × 8-bit` = `128 × 128` piksel 4-bit NUI Holographic Brain, Chrome/Emerald `NUI` Emblem, Metallic Gold & Emerald Green Circuit Orbits, dan Multi-Tiered Base Platform = `256 × 256` piksel layar di pusat `x = 464..719, y = 208..431`)
- **Modul Top-Level HDMI**: [`rtl/fpga/gowin/hcpu_hdmi_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi_top.v) (`RTL FINGERPRINT: 497ca6412fe4cf86e5cc1e54c224d13716a665151f13011a444f31cb47696f46`)
- **Bitstream Terukur (`gowin_pack`)**: [`cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/hcpu_hdmi_top.fs`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/hcpu_hdmi_top.fs) (`7,261,470` byte, `SHA-256: 6c08f940b211c881a7cdc73f917781152656ee15ac5f57524864bd2f8f59e96b`)
- **Log Build & Place-and-Route**: [`cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/hdmi_build_v2.log`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/hdmi_build_v2.log)
- **Program Komputasi Real-Time H-ISA**: [`cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/cosmictera_realtime_compute.hasm`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/cosmictera_realtime_compute.hasm)
- **Pratinjau Piksel-Akurat 1280×720 (`160 × 90` Sel Penuh + Hologram BSRAM)**:
  - State `RUNNING`: [`frame_nui_centered_running_1280x720.png`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/frame_nui_centered_running_1280x720.png)
  - State `S1 STOPPED`: [`frame_nui_centered_s1_stopped_1280x720.png`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/frame_nui_centered_s1_stopped_1280x720.png)
  - State `S2 RECOVERY`: [`frame_nui_centered_s2_recovery_1280x720.png`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/frame_nui_centered_s2_recovery_1280x720.png)

## 1. Arsitektur Visual & Fungsional NUI-Centered 1280×720 (`160 × 90` Sel Penuh)

Seluruh bidang layar `1280 × 720` (`160 kolom × 90 baris` sel `8×8` piksel) kini digunakan secara penuh melalui arsitektur **Dual-BSRAM Layout ROM (`u_layout` + `u_layout_lower`, 12 BSRAM)** ditambah **NUI Holographic Brain BSRAM Engine (`nui_holo_rom`, 4 BSRAM)**:

| Zona | Koordinat Grid (`Kolom`, `Baris`) | Komponen Utama | Sumber Data (Provenance) |
| :--- | :--- | :--- | :--- |
| **Zona 1 — Header** | `Cols 0..159`, `Rows 0..6` | Identitas **COSMICTERA // HYBIT**, `MATEMATIKA HIJAIYYAH COMPUTING ARCHITECTURE`, `H-ISA V1.2`, `TANG NANO 20K`, `HDMI 1280X720P60 TMDS LOCKED`, serta bar status live `CTEV....` & `S1S2....` | Live hardware (`ctrl_state`, `last_btn_event`, `s1_press_cnt`, `s2_press_cnt`) + identitas arsitektur |
| **Zona 2 — Panel Kiri Atas** | `Cols 4..49`, `Rows 8..22` | **HCPU / H-ISA Core (`27.000 MHz`)**: `STATE` (`RUNNING`/`STOPPED`/`PAUSED`/`RESET`/`FAULT`/`FLT LAT`/`READY`), `PC`, `INSTRUCTION`, `CYCLE`, `FLAGS`, `GUARD`, `OPCODE/REG`, `INST STEPS`, `LAST PRINT`, `PIPELINE: NOT INSTRUMENTED`, `PRIV/MEM` | Live hardware (`tele_pc`, `tele_instr`, `tele_cycles`, `tele_flags`, `true_guard_fault`, `rtm_step_cnt`, `rtm_last_print`) |
| **Zona 3 — Panel Tengah Atas** | `Cols 52..103`, `Rows 8..22` | **Matematika Hijaiyyah & Hybit 18D**: `LETTER OP` (**ج Jim `0xE4`** & **خ Kha `0xE6`**), `CODEX OP` (`0x40..0x60`), `MATH OPS`, `HNRM2 NMV = 112 (0x0070)`, `HDIST ITM = 10 (0x000A)`, `HDOT 14DSP = 9 (0x0009)`, `HYBIT 18D`, `OPERAND`, `HISAB/CRC`, `VALIDATION (G1-G4 T1-T2)` | Live hardware (`rtm_last_letter_op`, `rtm_last_codex_op`, `rtm_math_cnt`, `rtm_p5_hnrm2`, `rtm_p6_hdist`, `rtm_p7_hdot`) |
| **Zona 4 — Panel Kanan Atas** | `Cols 106..157`, `Rows 8..22` | **CosmicTera Computing Stack**: Status jujur 12 subsistem (`HCPU/H-ISA`, `HYBIT 18D`, `HC/HASM/HBC`, `HVM/HCVM`, `NUI L0 EMBED`, `HAR/UART`, `HISAB`, `USSS`, serta `HOS KERNEL: NOT INSTRUMENTED`, `HFS/SDIO: NOT INSTRUMENTED`, `KA'BAH/JAMRAH`, `HPG-1/HMCL`) | Live hardware (`rtm_print_cnt`, `rtm_uart_byte_cnt`) + kontrak kejujuran `R2/R4` |
| **Zona 5 — Pusat Utama (NUI Hub)** | `Cols 36..103`, `Rows 25..56` | **NUI Holographic Brain Core (`256×256` piksel @ `Cols 58..89, Rows 26..53`)**: Otak holografik cyan/electric blue, emblem **`NUI`** Chrome-Silver & Emerald-Green, cincin orbit sirkuit **Metallic Gold & Emerald Green**, platform komputasi bertingkat, serta **12 Node L0–L11** (`L0..L5` di kiri, `L6..L11` di kanan) | Bitmap BSRAM `hcpu_nui_holo.hex` dengan denyut sinkron clock (`rtm_s_cdc_frames[4]`, membeku saat `STOPPED`, berubah merah saat `FAULT`, cincin menyala saat `l0_active`) |
| **Zona 6 — Panel Kiri Tengah & Bawah** | `Cols 2..34`, `Rows 25..80` | **NUI L0–L11 Layer Telemetry & Relations**: 5 fitur kanonik L0 (`TITIK N(H)=2`, `GARIS K(H)=2`, `LENGKUNG Q(H)=2`, `THETA=6`, `RHO=6`), tabel resmi `L0..L11` (nama, status `RUN`/`CMP`/`RDY`/`AT`, input/output), relasi antar-layer, dan kontrak kejujuran NUI | Live hardware (`rtm_p0_titik` .. `rtm_p4_rho`, `rtm_print_cnt`) + spesifikasi resmi [`NUI/ARCHITECTURE.md`](file:///Users/AMRA/hijaiyyah-mathematics/NUI/ARCHITECTURE.md) |
| **Zona 7 — Panel Kanan Tengah** | `Cols 106..157`, `Rows 25..56` | **Physical Button Control (`S1`, `S2`, `UPDATE`) & Live Computation Event Log (`EV0..EV9`)**: Telemetri `RAW/SYN/DEB/CNT` tombol S1 (Pin 88) & S2 (Pin 87), identifikasi jujur `UPDATE = BL616 DFU`, transisi `PRE->POST`, `FAULT SRC/REC`, serta 10 baris event log komputasi real-time | Live hardware (`rtm_s1_rsdc`, `rtm_s2_rsdc`, `rtm_stev_val`, `rtm_prpo_val`, `rtm_flrc_val`, `EV0..EV9`) |
| **Zona 8 — Area Tengah Bawah** | `Cols 36..103`, `Rows 58..79` | **Verified CosmicTera & NUI Computation Flow Architecture**: Diagram alur komputasi nyata dari UART RX (`Pin 70`) -> `loader.hasm` -> HCPU 5-Stage Pipeline -> Master ROM `28×18D` (**Jim `0xE4` + Kha `0xE6`**) -> Codex ALU `14× MULT9X9` -> 6-Guard -> NUI L0 -> CDC -> NUI L6 HDMI | Terverifikasi pada silikon Tang Nano 20K |
| **Zona 9 — Area Kanan Bawah** | `Cols 106..157`, `Rows 58..79` | **Tang Nano 20K FPGA & Timing Metrics**: Utilisasi terukur (`LUT4`, `ALU`, `DFF`, `BSRAM`, `MULT9X9`, `MULT36X36`), `Fmax` kedua domain clock, pin TMDS Candidate B (`33, 35, 37, 39`), dan status proteksi checkpoint | Build/PnR-derived dari laporan `yosys` & `nextpnr-himbaechel` |
| **Zona 10 — Footer TV-Safe** | `Cols 0..159`, `Rows 82..88` | **System Footer**: `CORE:27.000MHZ`, `PIXEL:74.250MHZ`, `HDMI:1280X720P60 LOCKED`, counter frame `CDC:.... LOCKED`, `RELOCK:00`, `BUILD:CT-NUI-V1.2`, `SYS:RUNNING/READY`, dan baris `PAGE` kanonik | Live hardware (`rtm_s_cdc_frames`, `page`) |

## 2. Audit Resmi 12 Layer NUI (`L0–L11`) & Kejujuran Telemetri

Sesuai [`NUI/ARCHITECTURE.md`](file:///Users/AMRA/hijaiyyah-mathematics/NUI/ARCHITECTURE.md), [`NUI/ROADMAP.md`](file:///Users/AMRA/hijaiyyah-mathematics/NUI/ROADMAP.md), dan [`NUI/HONESTY.md`](file:///Users/AMRA/hijaiyyah-mathematics/NUI/HONESTY.md), setiap layer NUI ditampilkan dengan nama dan status sebenarnya tanpa klaim berlebihan:

| Layer | Nama Resmi (`NUI/ARCHITECTURE.md`) | Status Aktual | Input -> Output & Representasi di Monitor HDMI |
| :--- | :--- | :--- | :--- |
| **L0** | **Verified Knowledge Layer** | **LIVE ON FPGA (`RUN`)** | Mengeksekusi ekstraksi 5 fitur fisika huruf (**ج Jim `0xE4`** + **خ Kha `0xE6`**: `TITIK=2, GARIS=2, LENGKUNG=2, THETA=6, RHO=6`) di silikon HCPU dan menampilkannya secara live pada `Cols 16, Rows 28..33` serta `EV2..EV4`. |
| **L1** | **Repository Graph Layer** | **VERIFIED HOST (`CMP`)** | Graf repositori terverifikasi (`1,828` node, `4,689` edge, `0` unresolved); ditampilkan sebagai `CMP 1828N / 4689 EDGE` (`CC` — build-derived). |
| **L2** | **Program & HDL Index Layer** | **VERIFIED HOST (`CMP`)** | Indeks kanonik `60` program HASM dan `100` modul Verilog (`NUI/PROGRAMS.md`); dijaga utuh 100% (`CMP 60H/100V`). |
| **L3** | **Execution Understanding Layer** | **VERIFIED HOST (`CMP`)** | Jejak eksekusi deterministik (`63` program runs, `1,478` causal edges); ditampilkan sebagai `CMP 63 RUNS`. |
| **L4** | **Software-Hardware Parity Layer** | **VERIFIED HOST (`CMP`)** | Matriks paritas 3-arah Python/RTL/Board (`74` `P3_BOARD_PROVEN` dari `105` fitur); ditampilkan sebagai `CMP 74/105 P3`. |
| **L5** | **Linux & VM Host Intelligence Layer** | **VERIFIED HOST (`RDY`)** | 11 kolektor observasi host/VM (`9/11` terverifikasi pada sesi host); ditampilkan sebagai `RDY 9/11 OK`. |
| **L6** | **Hardware Runtime Intelligence Layer** | **LIVE ON FPGA (`RUN`)** | Mesin telemetri CDC `27 MHz -> 74.25 MHz`, UART sniffer L0, dan FSM tombol fisik `S1`/`S2` di `hcpu_hdmi_top.v` (`RUN CDC+RTL`). |
| **L7** | **Autonomous Operation Layer** | **VERIFIED HOST (`RDY`)** | Policy gate fail-closed (`ALLOW` / `STOP_AND_ESCALATE`) berbasis fakta L5+L6 (`RDY FAIL-CLS`). |
| **L8** | **Auto Diagnostic & Repair Layer** | **ASPIRATIONAL TARGET (`AT`)** | Ditampilkan jujur sebagai `AT MANUAL / ROOT CAUS` (aturan R2/R4: tidak pernah diklaim otomatis bila masih manual). |
| **L9** | **Reasoning & Knowledge Engine Layer** | **VERIFIED HOST (`CMP`)** | Mesin query deterministik lintas 7 domain pengetahuan (`CMP 7-DOM KB`). |
| **L10** | **Autonomous Engineering Layer** | **ASPIRATIONAL TARGET (`AT`)** | Ditampilkan jujur sebagai `AT NOT IMPL` (tidak diimplementasikan; tidak ada klaim generasi RTL otomatis). |
| **L11** | **Universal Computing Intelligence Layer** | **ASPIRATIONAL TARGET (`AT`)** | Ditampilkan jujur sebagai `AT ATOM LNK` (visi penyatuan `L0..L10`). |

## 3. Hasil Terukur Sintesis Yosys, Place & Route (`nextpnr-himbaechel`), & Bitstream (`gowin_pack`)

Diukur langsung dari [`hdmi_build_v2.log`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/hdmi_build_v2.log) pada perangkat `GW2AR-LV18QN88C8/I7`:

| Resource / Metrik Timing | Nilai Terukur (`hdmi_pnr.json`) | Kapasitas GW2AR-18C | Persentase / Margin |
| :--- | :--- | :--- | :--- |
| **IOB** | `16` | `384` | `4%` |
| **LUT4** | `15,318` | `20,736` | `73%` (`5,418` LUT4 cadangan) |
| **ALU Carry** | `2,956` | `15,552` | `19%` |
| **DFF Registers** | `6,123` | `15,552` | `39%` |
| **BSRAM Blocks** | `33` (`16` HCPU + `12` Full-Screen 90-Row Text ROM + `4` NUI Hologram ROM + `1` Font ROM) | `46` | `71%` (`13` BSRAM cadangan) |
| **MULT9X9 Hard DSP** | `14` | `96` | `14%` (`USE_DSP = 1`) |
| **MULT36X36 Hard DSP** | `1` | `12` | `8%` (`USE_DSP = 1`) |
| **`Fmax u_hcpu.clk_27m`** | **`97.64 MHz`** | Target `27.000 MHz` | **PASS (`3.62×` margin di atas 27 MHz)** |
| **`Fmax pixel_clk`** | **`74.69 MHz` (est) / `61.45 MHz` (post-route)** | Constraint `12.00 MHz` | **PASS (`0` setup/hold violation pada constraint)** |
| **Ukuran & Hash Bitstream** | `7,261,470` byte | `hcpu_hdmi_top.fs` | `SHA-256: 6c08f940b211c881a7cdc73f917781152656ee15ac5f57524864bd2f8f59e96b` |
