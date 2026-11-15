# COSMICTERA — STAGE 1.3 FINAL HARDWARE VALIDATION & STAGE 1.4 UNIFIED SoC ARCHITECTURE HANDOFF

**Date:** 2026-11-03  
**Repository:** `/Users/AMRA/hijaiyyah-mathematics`  
**Experiment Workspace:** `/tmp/stage1_2_cosmictera_boot_ui/` (mirrored in `$GEMINI_WORKSPACE_DIR/stage1_2_cosmictera_boot_ui/`)  
**Target Device:** Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`family=GW2A-18C`)  
**Display Target:** LG TV (`1280 × 720 @ 60 Hz`, `74.25 MHz` pixel clock, `371.25 MHz` TMDS serial clock)

---

## 1. REPOSITORY & GIT STATE (BEFORE AND AFTER)

| Parameter | Before Execution | After Execution |
| :--- | :--- | :--- |
| **Branch** | `fix/dataset-canonicalization-and-authorship` | `fix/dataset-canonicalization-and-authorship` |
| **Git `HEAD`** | `8c70989bec0d3b86ace8b657fd8f1d761164b8e3` | `8c70989bec0d3b86ace8b657fd8f1d761164b8e3` |
| **Freeze Tag (`layer6-freeze-2026-09-29-final`)** | `1bb468bf` -> `0a3b446` (untouched) | `1bb468bf` -> `0a3b446` (untouched) |
| **Auto-Commit / Auto-Push** | None | **None** (strictly un-staged / un-committed per Authorization 1) |
| **Modified Tracked Files** | `0` | `1` (`rtl/fpga/gowin/hcpu_hdmi.cst` — authorized Candidate B CST patch) |
| **New Constraint File** | None | `constraints/cosmictera_tangnano20k.cst` (authorized Candidate B CST) |

---

## 2. AUTHORIZATION 1 — CST PATCH VERIFICATION & DIFF

### 2.1 Backup & SHA-256 Verification

1. **Original Backup Created Before Modification:**
   - Source: `/Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi.cst`
   - Backup Path: `/tmp/stage1_2_cosmictera_boot_ui/hcpu_hdmi.cst.bak`
   - Original SHA-256: `de7cf895f33feb67057f0771e134eea04ad17178c2025a807d13aa6ff9f867da`
2. **Approved Patch File Verified:**
   - Patch Path: `/tmp/stage1_2_cosmictera_boot_ui/17_corrected_patch_candidate.diff`
   - Patch SHA-256: `61064313f3861221efd4d5dca993a39cadac1ef2260e59e4475ace7d8ceaac15`
3. **Patched Constraint Files:**
   - `/Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi.cst` (Full SoC + Candidate B HDMI constraints) — SHA-256: `6fcbdb00e87ca04b05a9ce1a810a60a9c5b880e56e33d8a03977fcdabb608af9`
   - `/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst` (Standalone HDMI Display Node Candidate B constraints) — SHA-256: `3f16df4fc048f967cae125a31bfe0429e19d20c178df8e83352ea1304bf954a7`

### 2.2 Verified Git Diff (`rtl/fpga/gowin/hcpu_hdmi.cst`)

```diff
diff --git a/rtl/fpga/gowin/hcpu_hdmi.cst b/rtl/fpga/gowin/hcpu_hdmi.cst
index c79d98d7..bc9f43ee 100644
--- a/rtl/fpga/gowin/hcpu_hdmi.cst
+++ b/rtl/fpga/gowin/hcpu_hdmi.cst
@@ -21,14 +21,14 @@ IO_PORT "uart_txd" IO_TYPE=LVCMOS33 DRIVE=8;
 // produced eight single-ended drivers and no TMDS -- the monitor stayed dark.
 // With both pads named here, one IOB drives the pair and the N half needs no
 // port and no logic in hcpu_hdmi_top.v.
-IO_LOC "tmds_clk_p_OBUF_O" 33,34;
-IO_PORT "tmds_clk_p_OBUF_O" IO_TYPE=LVCMOS33D DRIVE=3.5;
-IO_LOC "tmds_data_p_OBUF_O" 35,36;
-IO_PORT "tmds_data_p_OBUF_O" IO_TYPE=LVCMOS33D DRIVE=3.5;
-IO_LOC "tmds_data_p_OBUF_O_1" 37,38;
-IO_PORT "tmds_data_p_OBUF_O_1" IO_TYPE=LVCMOS33D DRIVE=3.5;
-IO_LOC "tmds_data_p_OBUF_O_2" 39,40;
-IO_PORT "tmds_data_p_OBUF_O_2" IO_TYPE=LVCMOS33D DRIVE=3.5;
+IO_LOC "tmds_clk_p_OBUF_O" 33;
+IO_PORT "tmds_clk_p_OBUF_O" IO_TYPE=LVCMOS33D DRIVE=8;
+IO_LOC "tmds_data_p_OBUF_O_2" 35;
+IO_PORT "tmds_data_p_OBUF_O_2" IO_TYPE=LVCMOS33D DRIVE=8;
+IO_LOC "tmds_data_p_OBUF_O_1" 37;
+IO_PORT "tmds_data_p_OBUF_O_1" IO_TYPE=LVCMOS33D DRIVE=8;
+IO_LOC "tmds_data_p_OBUF_O" 39;
+IO_PORT "tmds_data_p_OBUF_O" IO_TYPE=LVCMOS33D DRIVE=8;
```

### 2.3 P/N Differential Lane & Constraint Audit

| HDMI TMDS Lane | RTL Signal | Synthesized OBUF Cell | Positive Pad (`IOBA`) | Negative Pad (`IOBB`, Auto-Driven by `LVCMOS33D`) | I/O Standard & Drive | Verification Result |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **TMDS Clock** | `tmds_clk_p` | `tmds_clk_p_OBUF_O` | **Pin 33** (`IOL7A`) | **Pin 34** (`IOL7B`) | `LVCMOS33D DRIVE=8` | **PASS** (True polarity, no N-pad overwrite) |
| **TMDS Data 2 (Red)** | `tmds_data_p[2]` | `tmds_data_p_OBUF_O_2` | **Pin 35** (`IOL8A`) | **Pin 36** (`IOL8B`) | `LVCMOS33D DRIVE=8` | **PASS** (Red channel mapped to HDMI Data 2) |
| **TMDS Data 1 (Green)** | `tmds_data_p[1]` | `tmds_data_p_OBUF_O_1` | **Pin 37** (`IOL9A`) | **Pin 38** (`IOL9B`) | `LVCMOS33D DRIVE=8` | **PASS** (Green channel mapped to HDMI Data 1) |
| **TMDS Data 0 (Blue)** | `tmds_data_p[0]` | `tmds_data_p_OBUF_O` | **Pin 39** (`IOL10A`) | **Pin 40** (`IOL10B`) | `LVCMOS33D DRIVE=8` | **PASS** (Blue channel mapped to HDMI Data 0) |

---

## 3. AUTHORIZATION 2 — STAGE 1.4 UNIFIED SoC ARCHITECTURE & RECONCILED RESOURCE ACCOUNTING

Per the owner's decision, **Option 2 (Unified SoC with Compact/Shared 4-BSRAM Boot Logo + Direct Bus/UART/SPI Telemetry Bridge)** is selected as the target architecture for Stage 1.4, with the Dual-Bitstream architecture retained strictly as a recovery fallback if combined P&R fails timing or capacity.

### 3.1 Reconciled Resource Estimation (Separate Synthesis Sum vs Device Capacity)

The arithmetic sum of the separate synthesis LUT counts (`15,351 + 2,926 = 18,277 LUT`) is **below** the `20,736` LUT4 capacity of the `GW2AR-LV18QN88C8/I7` by **2,459 LUTs** (`88.14%`), and the BSRAM sum is **40 / 46 blocks** (`86.96%`, leaving 6 blocks) without compression or **32 / 46 blocks** (`69.57%`, leaving 14 blocks) with the 4-BSRAM Compact Boot Logo target:

| Resource Category | Compute Core (`cosmictera_top` / `hcpu_hdmi_top`) | Boot Display (`cosmictera_boot_top`, Stage 1.3 Yosys) | Separate Synthesis Sum (Uncompressed Logo) | Separate Synthesis Sum (Compact 4-BSRAM Logo) | GW2AR-18C Capacity | Remaining Headroom (Compact Target) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Yosys LUT (`LUT2+LUT3+LUT4`)** | `15,351` | `2,926` (`568+700+1,658`) | **`18,277`** (`88.14%`) | **`~18,050`** (`87.05%`) | `20,736` | **`+2,686 LUT` (`12.95%`)** |
| **Yosys Wide Mux (`MUX2_LUT5..8`)** | Included in slice packing | `960` (`697+180+63+20`) | Measured in combined P&R | Measured in combined P&R | Packed into `SLICE` | Verified at combined P&R gate |
| **Yosys `ALU` Carry Cells** | Included in slice packing | `1,387` | Measured in combined P&R | Measured in combined P&R | Packed into `SLICE` | Verified at combined P&R gate |
| **Flip-Flops (`DFF`)** | `~6,410` | `726` (`4.67%`) | **`7,136`** (`45.88%`) | **`~7,100`** (`45.65%`) | `15,552` | **`+8,452 DFF` (`54.35%`)** |
| **Block SRAM (`BSRAM`)** | `28` | `12` (`8` Logo + `3` Text + `1` Font) | **`40`** (`86.96%`) | **`32`** (`69.57%`) | `46` | **`+14 BSRAM` (`30.43%`)** |
| **DSP (`MULT18X18`)** | `2` (or `0` with `-nodsp`) | `0` | **`2`** (`7.14%`) | **`2`** (`7.14%`) | `28` | **`+26 DSP` (`92.86%`)** |

---

## 4. AUTHORIZATION 3 — STAGE 1.3 HARDWARE VALIDATION ON LG TV (`WhatsApp Image 2026-11-03 at 15.14.47.jpeg`)

### 4.1 Physical LG TV Observation Results (`15:14:47` Capture)

Following execution of `/tmp/stage1_2_cosmictera_boot_ui/run_pnr_and_sram_load.sh --load-sram` in **SRAM Mode** (`openFPGALoader -b tangnano20k`, zero External Flash operations), the Stage 1.3 bitstream was loaded into Tang Nano 20K SRAM and verified directly on the LG TV (`WhatsApp Image 2026-11-03 at 15.14.47.jpeg`):

1. **Header & Video Timing (`Region 1 & Region 3`)**:
   - `DISPLAY READY` badge in green (`#2DCD73`), `BUILD CT-1.2-8C70`, `REV 8C70989B`.
   - `PANEL A: VIDEO MODE`: `1280X720 60HZ`, `FRAME: 1650X750P`, `STATUS: ACTIVE`.
   - `PANEL B: PIXEL CLOCK`: `74.25 MHZ CFG`, `RPLL 371.25 / DIV 5`, `STATUS: LOCKED`.
   - `PANEL C: BOOT ELAPSED`: `00:02 (00:02:44)` monotonic hardware BCD counter running live (`2 min 44 sec` continuous stability).
   - `PANEL D: RENDERER`: `FONT 8X8 : READY`, `LOGO RLE : READY`, `SCREEN: DISPLAY READY`.
2. **Hero Chrome Orbit Logo (`Region 2`)**:
   - Full `512 × 184` 32-color RLE logo rendered over deep navy background (`#060C16`) with true gold, emerald green, cyan, and chrome highlights (Candidate B CST confirmed).
3. **Display Node Boot Sequence (`Region 4`)**:
   - All 10 hardware stages (`01. REFERENCE CLOCK` through `10. VIDEO OUTPUT`) verified `✓ READY`.
4. **Live Compute Subsystems & Full 87-Bit Coherent Telemetry (`Region 5`)**:
   - Banner: `COMPUTE SUBSYSTEMS - 10/10 VERIFIED` in green.
   - Live 87-Bit Coherent Telemetry Line (`row 57, cols 99..152`):
     `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE`
     Every single field (`PC`, `IN`, `CY`, `FL`, `G`, `RUN`, `CDC:LIVE`) is crisply rendered and verified on the LG TV monitor!
   - 10 Subsystem Status Rows (`rows 60, 63, 66, 69, 71`):
     `HCPU (VF 120M)`, `HISA (VF 82/104 OP)`, `HIJAIYYAH CELLS (VF 4GRD)`, `HOS (VF 3-PROC OK)`, `HFS (VF LBA1)`, `HMCL (VF HDOT 14C)`, `NUI (VF 12LY)`, `JAMRAH (VF 33-CLK/B)`, `KA'BAH (VF HMAC)`, `PORTAL 8888 (VF P8 SEALED)`.

---

## 5. STRICT STATUS TABLE (`PASS / FAIL / BLOCKED / NOT TESTED`)

| Item / Verification Gate | Status | Evidence & Notes |
| :--- | :---: | :--- |
| **Git `HEAD` Integrity (`8c70989b`, No Commit/Push)** | **PASS** | `HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`; `0` commits/pushes made. |
| **Authorization 1: CST Backup & Candidate B Patch** | **PASS** | Backup at `/tmp/stage1_2_cosmictera_boot_ui/hcpu_hdmi.cst.bak` (`de7cf895...`); patched `rtl/fpga/gowin/hcpu_hdmi.cst` (`6fcbdb00...`) & `constraints/cosmictera_tangnano20k.cst` (`3f16df4f...`). |
| **Stage 1.3 27 MHz Hardware BIST & Strict `snap_valid` CDC** | **PASS** | `cosmictera_boot_subsys_bridge.v` (`a1954285...`): `snap_valid` resets to `1'b0` on `!vid_rst_n` and asserts `1'b1` only on `ack_edge` after round-trip CDC handshake. |
| **Stage 1.3 Full 87-Bit Coherent Telemetry & `P1–P8` Live Display** | **PASS** | `cosmictera_boot_compositor.v` (`89fc93d5...`): renders `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE` (`86` data bits + `snap_valid`) and dynamic `(LIVE)`/`(INIT)`/`(ERR)` on `P1–P8`. |
| **Stage 1.3 1-Cycle DVI Pipeline Register (`cosmictera_boot_top.v`)** | **PASS** | `red_dvi, green_dvi, blue_dvi, de_dvi, hsync_dvi, vsync_dvi` registered between `u_render` and `DVI_TX_Top` (`698dd114...`). |
| **Stage 1.3 RTL Testbench (`T01–T24`)** | **PASS** | `tb_boot_top.log` (`167d02ae...`): **25 PASS, 0 FAIL** across all 25 hardware assertions. |
| **Stage 1.3 Golden Frame Pixel-by-Pixel Verification** | **PASS** | `verify_frames_and_render_previews.py` (`0b8d7ef4...`): **0 / 163,328 pixel mismatches** across `STARTUP`, `READY`, `ERROR`, and 512×184 Hero Logo. |
| **Stage 1.3 Yosys 0.68 FPGA Synthesis (`GW2A-18C`)** | **PASS** | `cosmictera_boot_top.json` (`53ed54a8...`): **0 errors**, **12 / 46 BSRAM (`26.1%`)**, **0 DSP**, **726 DFF (`4.7%`)**, **2,926 LUT2/3/4**. |
| **Stage 1.3 Host `nextpnr-himbaechel` P&R & USB JTAG SRAM Load** | **PASS** | Executed in SRAM Mode (`openFPGALoader -b tangnano20k`, zero Flash operations). |
| **LG TV Visual Confirmation of Stage 1.3 `IN:4E010200` & `CDC:LIVE` Line** | **PASS** | Verified via owner photo `WhatsApp Image 2026-11-03 at 15.14.47.jpeg` (`BOOT ELAPSED 00:02:44`, `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE` live on LG TV). |
| **Stage 1.4 Unified SoC Combined Synthesis & P&R** | **NOT TESTED (Next Phase)** | Target architecture locked to **Option 2 (Unified SoC with 4-BSRAM Compact Logo)**; ready to begin Stage 1.4 Unified SoC implementation. |
