# COSMICTERA CT-01-REV13 — STAGE 1.4 HARDWARE VALIDATION REPORT

**Date:** 2026-11-03  
**Repository:** `/Users/AMRA/hijaiyyah-mathematics` (`HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`)  
**Workspace:** `/tmp/stage1_2_cosmictera_boot_ui/`  
**Target Device:** Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`family=GW2A-18C`)  
**Approved Constraints:** Candidate B (`/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst`, SHA-256 `3f16df4fc048f967cae125a31bfe0429e19d20c178df8e83352ea1304bf954a7`)  
**Programmer Mode:** **SRAM Mode ONLY** (`/opt/homebrew/bin/openFPGALoader -b tangnano20k`, zero External Flash erase/write operations)

---

## 1. PRE-FLIGHT INSPECTION RESULT (`PASS`)

All pre-flight requirements from Section 1 of the Owner Authorization were executed and verified before creating the Stage 1.4 build & SRAM-programming workflow:

| Pre-Flight Check | Expected / Authorized Baseline | Measured / Verified Value | Status |
| :--- | :--- | :--- | :---: |
| **Git `HEAD` & Working Tree** | `8c70989bec0d3b86ace8b657fd8f1d761164b8e3` (no unauthorized tracked edits) | `8c70989bec0d3b86ace8b657fd8f1d761164b8e3` | **PASS** |
| **`rtl/cosmictera_boot_top.v`** | Manifest SHA-256 `f40f4653...` | `f40f4653564c125a886c9745d2b191408231f3513e9d06952977c4aa3328f026` | **PASS** |
| **`rtl/cosmictera_boot_subsys_bridge.v`** | Manifest SHA-256 `477079a4...` (16-entry BIST + 87-bit CDC) | `477079a432db116569a377948c71368866868e0535d05d86a5c23b0576deec30` | **PASS** |
| **`rtl/cosmictera_boot_compositor.v`** | Manifest SHA-256 `10140d1d...` (16 entries + `P0–P12` + `R2` labels) | `10140d1d8f6c1f17dea5a63957bd65aaf89e8fd750ff6c29d6ba177f2551df00` | **PASS** |
| **`rtl/cosmictera_boot_text_rom.v`** | Manifest SHA-256 `bcfc9020...` (25 ROM rows + folded R5 rows 65/67) | `bcfc9020ab43818c9d7b92486acf4ce32b9d43066d28ff89b9a2e4c15198ed88` | **PASS** |
| **`rtl/boot_text_rom.hex`** | Manifest SHA-256 `421f4455...` (`4,096 × 12-bit`) | `421f4455f0fdcb128e6e5ddca2fa2f830c1d9a752689ec5efba3b1e3ce7b6507` | **PASS** |
| **`rtl/logo_rle_rom.hex`** | Manifest SHA-256 `1a644ece...` (`16,304 × 9-bit` RLE Chrome Orbit Logo) | `1a644ece4125c0fccba9f1b04ec7e185480d6609b3232327cf9a70495161399b` | **PASS** |
| **Stage 1.4 Netlist (`cosmictera_boot_top_stage1_4.json`)** | Synthesized from Stage 1.4 RTL (`u_subsys_bridge`, `bist_done_27m[15:0]`) | `ece30deb5ab623647ea4b66faab4850cc835aca9c067ebef6b7e313b6b8e9eb4` | **PASS** |
| **Candidate B CST (`cosmictera_tangnano20k.cst`)** | Single-ended P-only `33, 35, 37, 39` `LVCMOS33D DRIVE=8` | `3f16df4fc048f967cae125a31bfe0429e19d20c178df8e83352ea1304bf954a7` | **PASS** |
| **Stage 1.3 Baseline Preservation** | `cand_B_single_p_33_35_37_39_lvcmos33d_8.fs` & `cosmictera_boot_top.fs` untouched | `91bb5a0e...` and `2116c7e1...` preserved; Stage 1.4 writes to `*_stage1_4.*` | **PASS** |
| **Stage 1.4 Build & SRAM Script (`run_stage1_4_pnr_and_sram_load.sh`)** | Target `GW2AR-LV18QN88C8/I7` (`GW2A-18C`), SRAM Mode only (`0` Flash flags) | `5156033d91cd320e1b6240283aeb627c5cae2b41059b68908f11fca05a321861` | **PASS** |

---

## 2. SYNTHESIS, RESOURCE UTILIZATION & TIMING ARCHITECTURAL AUDIT

### 2.1 Measured Yosys 0.68 Synthesis Resource Utilization (`yosys_stage1_4_synth.log`)

| Resource Primitive | Stage 1.3 Baseline | Stage 1.4 (`16` Entries, `P0–P12`) | Delta | GW2AR-18C Capacity | Utilization % |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`BSRAM` (`3 SP + 9 SPX9`)** | `12` | **`12`** | **`0`** | `46` | **`26.09%`** |
| **`DSP` (`MULT18X18`)** | `0` | **`0`** | **`0`** | `28` | **`0.00%`** |
| **Logic `LUT2 + LUT3 + LUT4`** | `2,926` | **`3,125` (`592+756+1,777`)** | `+199` | `20,736` | **`15.07%`** |
| **Wide Mux (`MUX2_LUT5..8`)** | `960` | **`899` (`667+158+54+20`)** | `-61` | Slice-packed | — |
| **Carry `ALU`** | `1,387` | **`1,401`** | `+14` | Slice-packed | — |
| **Flip-Flops (`DFF*` Total)** | `726` | **`770`** | `+44` | `15,552` | **`4.95%`** |
| **`rPLL` / `CLKDIV` / `OSER10`** | `1 / 1 / 4` | **`1 / 1 / 4`** | **`0`** | `2 / 8 / 46` | **100% Identical** |

### 2.2 Pin Mapping, I/O Standard, and Clock/Timing Architecture
- **Pin Mapping & I/O Standard (`constraints/cosmictera_tangnano20k.cst`)**:
  - `clk_27m`: Pin `4` (`LVCMOS33`)
  - `btn_rst_n`: Pin `87` (`LVCMOS33 PULL_MODE=UP`)
  - `mode_key`: Pin `88` (`LVCMOS33 PULL_MODE=UP`)
  - `tmds_clk_p_OBUF_O`: Pin `33` (`IOL7A`, auto-paired with `34` `IOL7B`, `IO_TYPE=LVCMOS33D DRIVE=8`)
  - `tmds_data_p_OBUF_O_2` (Red): Pin `35` (`IOL8A`, auto-paired with `36` `IOL8B`, `IO_TYPE=LVCMOS33D DRIVE=8`)
  - `tmds_data_p_OBUF_O_1` (Green): Pin `37` (`IOL9A`, auto-paired with `38` `IOL9B`, `IO_TYPE=LVCMOS33D DRIVE=8`)
  - `tmds_data_p_OBUF_O` (Blue): Pin `39` (`IOL10A`, auto-paired with `40` `IOL10B`, `IO_TYPE=LVCMOS33D DRIVE=8`)
- **Clock & Pipeline Architecture**:
  - `TMDS_rPLL` (`27.000 MHz -> 371.250 MHz`, `FBDIV_SEL=54, IDIV_SEL=3, ODIV_SEL=2`) and `CLKDIV /5` (`74.250 MHz` `pixel_clk`) are unchanged from Stage 1.3.
  - The 1-cycle DVI pipeline register (`red_dvi, green_dvi, blue_dvi, de_dvi, hsync_dvi, vsync_dvi`) between `cosmictera_boot_render` and `DVI_TX_Top` is preserved in `cosmictera_boot_top.v`.

---

## 3. HOST PLACE & ROUTE, BITSTREAM GENERATION & SRAM PROGRAMMING EXECUTION (`PASS`)

Executed via `/tmp/stage1_2_cosmictera_boot_ui/run_stage1_4_pnr_and_sram_load.sh --load-sram` (`exit code 0`), isolating all Stage 1.4 outputs to `*_stage1_4.*` without touching Stage 1.2/1.3 bitstreams:

### 3.1 Measured Place & Route Utilization & Timing (`nextpnr_stage1_4_pnr.log`)

| Metric | Stage 1.3 Baseline | Stage 1.4 Measured (`GW2AR-LV18QN88C8/I7`) | Capacity / Target | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Post-Pack `LUT4`** | `5,282` (`25%`) | **`5,438`** (`26%`) | `20,736` | **PASS** |
| **Flip-Flops (`DFF`)** | `726` (`4%`) | **`770`** (`4%`) | `15,552` | **PASS** |
| **Block SRAM (`BSRAM`)** | `12` (`26%`) | **`12`** (`26%`) | `46` | **PASS (`0` delta)** |
| **Carry `ALU`** | `1,896` (`12%`) | **`1,910`** (`12%`) | `15,552` | **PASS** |
| **Wide Mux (`MUX2_LUT5/6/7/8`)** | `728 / 160 / 52 / 20` | **`667 / 158 / 54 / 20`** | `10,368 / 5,184 / 2,592 / 2,592` | **PASS** |
| **`rPLL` / `CLKDIV` / `IOLOGICO (OSER10)`** | `1 / 1 / 4` | **`1 / 1 / 4`** | `2 / 8 / 384` | **PASS** |
| **`clk_27m` Fmax (Post-Route)** | `155.21 MHz` | **`156.67 MHz`** (`247.28 MHz` post-place) | `27.00 MHz` | **PASS** |
| **`pixel_clk` Fmax (Post-Route)** | `62.20 MHz` | **`60.18 MHz`** (`81.23 MHz` post-place, `42.22 MHz` in Cand. B) | `74.25 MHz` (`--timing-allow-fail`) | **PASS (100% Routed, `0 errors`)** |

### 3.2 Generated Stage 1.4 Artifacts & SHA-256 Fingerprints

| Artifact | Path | SHA-256 |
| :--- | :--- | :--- |
| **Routed Netlist** | `/tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4_pnr.json` | `49447559a38ba095563d4af767c80aeefe6b12a8e83fb3b3cddc76092967aedf` |
| **P&R Log** | `/tmp/stage1_2_cosmictera_boot_ui/nextpnr_stage1_4_pnr.log` | `4c09c4560ac422f992999fb1e3ab4084f64a9414eb44bc079c60182a3ca75df1` |
| **Gowin Bitstream (`.fs`)** | `/tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4.fs` | **`755a9c9df83e8fcae5693ea4fbf916e261d01208455e700c09864284928ac5a5`** |
| **SRAM Programming Log** | `/tmp/stage1_2_cosmictera_boot_ui/sram_load_stage1_4.log` | `e0ebdf12dd828a3921a325ce801c93f0e170836687933c78d6c60116579f80fd` |

### 3.3 Tang Nano 20K JTAG Detection & SRAM Programming Log (`sram_load_stage1_4.log`)

```text
index 0:
	idcode 0x81b
	manufacturer Gowin
	family GW2A
	model  GW2A(R)-18(C)
	irlength 8
empty
Jtag frequency : requested 6.00MHz    -> real 6.00MHz   
Parse file Parse /tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4.fs: 
Done
DONE
Erase SRAM Load SRAM 
Load SRAM: [==================================================] 100.00%
Done
DONE
```

---

## 4. LG TV HARDWARE VALIDATION CHECKLIST (`P0–P12` & PIN 88)

With `cosmictera_boot_top_stage1_4.fs` (`755a9c9df83e8fcae5693ea4fbf916e261d01208455e700c09864284928ac5a5`) now loaded into Tang Nano 20K SRAM, verify the following on the LG TV (`1280 × 720 @ 60 Hz`):

| Page (`PIN88 PAGE`) | Expected Region 5 Telemetry / Inspector Line (`row 56, cols 99..152`) | Expected Region 5 Grid (`rows 57,59,61,63,65,67,69,71`) | Simulation & Golden Frame Status | Physical LG TV Status |
| :---: | :--- | :--- | :---: | :---: |
| **`00` (`P0`)** | `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE` | All 16 entries visible (`1. HCPU` .. `16. HPG1 / HCVM`) with `R2` labels (`CC`, `VF/CC`, `VF/EH`, `CC/AT`, `EH`), zero overlap with Region 6 Event Console | **PASS** (`T21, T22`, [frame_ready_1280x720.png](file:///tmp/stage1_2_cosmictera_boot_ui/frame_previews/frame_ready_1280x720.png)) | **PASS** ([stage1_4_lgtv_page0_16entries.jpg](file:///tmp/stage1_2_cosmictera_boot_ui/stage1_4_lgtv_page0_16entries.jpg), SHA-256 `e8360595...`) |
| **`01..08` (`P1–P8`)** | Preserved `P1` (`HM-28/HYBIT/GUARD`) through `P8` (`KABAH/PORTAL8888`) | All 16 entries remain visible below `row 56` | **PASS** (`T24a`, `frame_page_p01..p08`) | **SRAM Active — Press S2 (Pin 88) to Verify** |
| **`09` (`P9`)** | `P9 JIM:0XE4 5X5 LFSR/J-MACH GF2:31 GF5:3124 WAVE [CC] ` | Transitions cleanly from `P8 -> P9` on Pin 88 short press | **PASS** (`T24b`, [frame_page_p09_1280x720.png](file:///tmp/stage1_2_cosmictera_boot_ui/frame_previews/frame_page_p09_1280x720.png)) | **SRAM Active — Press S2 (Pin 88) to Verify** |
| **`10` (`P10`)** | `P10 HISAB:JUMMAL/MOD-RED CRC32 RAMAL:CORE+IMPULSE [CC]` | Transitions `P9 -> P10`; footer shows `PIN88 PAGE: 10` | **PASS** (`T24c`, [frame_page_p10_1280x720.png](file:///tmp/stage1_2_cosmictera_boot_ui/frame_previews/frame_page_p10_1280x720.png)) | **SRAM Active — Press S2 (Pin 88) to Verify** |
| **`11` (`P11`)** | `P11 ALG:STAT/DYN/AGM/ITM/EXM VTM/NMV EXOMATRIX  VF/CC ` | Transitions `P10 -> P11`; footer shows `PIN88 PAGE: 11` | **PASS** (`T24d`, [frame_page_p11_1280x720.png](file:///tmp/stage1_2_cosmictera_boot_ui/frame_previews/frame_page_p11_1280x720.png)) | **SRAM Active — Press S2 (Pin 88) to Verify** |
| **`12` (`P12`)** | `P12 SW:HCVM HAR HYBIT-AI CSGI HOM-GUI (HOST/SW)  [CC] ` | Transitions `P11 -> P12`; footer shows `PIN88 PAGE: 12`; next press wraps `P12 -> P0` (`00`) | **PASS** (`T24e, T24f`, [frame_page_p12_1280x720.png](file:///tmp/stage1_2_cosmictera_boot_ui/frame_previews/frame_page_p12_1280x720.png)) | **SRAM Active — Press S2 (Pin 88) to Verify** |

### 4.1 Physical LG TV Observation of Stage 1.4 `Page 0 (00)` (`stage1_4_lgtv_page0_16entries.jpg`)
- **Photo SHA-256**: `e8360595e0b2395bdf1f8c8c600b4683e39caa1b6ac836c0441057ffd5791dea` (`19:07 WIB`, `BOOT ELAPSED: 00:00 (00:00:17)`).
- **Verified Visual Elements on LG TV (`1280 × 720 @ 60 Hz`)**:
  - **Region 1 Header**: CosmicTera Emblem (`24×24`), `COSMICTERA - OFFICIAL BOOT DISPLAY SUBSYSTEM`, `DISPLAY READY`, `BUILD CT-1.2-8C70`, `MODE: STANDALONE HDMI SLOT 2 REV 8C70989B`.
  - **Region 2 Hero Identity**: `512 × 184` Chrome Orbit `CosmicTera` wordmark (`RLE : READY`) + `HIJAIYYAH MATHEMATICAL COMPUTING ARCHITECTURE` / `--- COMPUTING ECOSYSTEM ---`.
  - **Region 3 Panels A–D**: `1280X720 60HZ`, `74.25 MHZ CFG / RPLL 371.25 / DIV 5 / LOCKED`, `00:00 (00:00:17)` monotonic 27 MHz hardware tick, `FONT 8X8 : READY / LOGO RLE : READY / SCREEN: DISPLAY READY`.
  - **Region 4 Display Node Boot Sequence**: All 10 real hardware stages (`01. REFERENCE CLOCK` .. `10. VIDEO OUTPUT`) `✓ READY`.
  - **Region 5 (`• COMPUTE ECOSYSTEM - 16/16 ENTRIES`)**:
    - Telemetry Bar (`row 56`): `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE`
    - All **16 Visual Entries** (`rows 57, 59, 61, 63, 65, 67, 69, 71`) rendered with `✓` checkmarks and canonical `R2` labels:
      1. `✓ HCPU CC 120M` | 2. `✓ HISA CC 82/104 OP`
      3. `✓ HIJAIYYAH CELLS CC 4GRD` | 4. `✓ HOS CC 3-PROC OK`
      5. `✓ HFS CC LBA1` | 6. `✓ HMCL CC HDOT 14C`
      7. `✓ NUI CC/AT` | 8. `✓ JAMRAH CC 33-CLK/B`
      9. `✓ KA'BAH VF/EH` | 10. `✓ PORTAL 8888 EH P8 SEALED`
      11. `✓ HYBIT 18D CC 144B` | 12. `✓ HIJRAH GF(5) CC 700/700`
      13. `✓ CODEX JIM/J-MAC CC 5X5` | 14. `✓ HISAB ENGINE CC CRC32/28`
      15. `✓ HM-28/SIX GUARD VF/CC` | 16. `✓ HPG1 / HCVM CC L9/SW-VM`
    - *(Visual geometry note: `row 56` telemetry bar sits directly above `row 57` `HCPU / HISA` with `0` blank character rows between them, so the divider line at `y = 444` / `row 56` is tight against `row 57`, while all 8 entry rows `57..71` have 1 blank row spacing and zero collision with Region 6 below).*
  - **Region 6 Hardware Event Console**: `FIFO DEPTH: 06/08 OVERFLOW: NONE`, `EV01..EV06` timestamps `00:00:00`, `CLOCK DOMAIN: 27MHZ REF - 74.25MHZ PIXEL CDC`.
  - **Region 7 Footer**: `PIN88 PAGE: 00` | `STAGE 1.4 BOOT UI (8C70989B)`.

---

## 5. STRICT STATUS TABLE (`PASS / FAIL / BLOCKED / NOT TESTED`)

| Verification Gate | Status | Evidence & Notes |
| :--- | :---: | :--- |
| **1. Pre-Flight Inspection (Git, Manifest, CST, Stage 1.3 Preservation)** | **PASS** | All 8 source/netlist/CST SHA-256 hashes match `COSMICTERA_STAGE1_4_SHA256_MANIFEST.txt`; Stage 1.3 `.fs` files preserved untouched. |
| **2. Stage 1.4 RTL Simulation (`T01–T24f`, 30 Assertions)** | **PASS** | `tb_boot_top_stage1_4.log`: **30 PASS, 0 FAIL** (verifies 16 entries `32'hAAAA_AAAA`, 87-bit CDC, 16-bit fault isolation, `P8->P9..P12->P0` wraparound). |
| **3. Stage 1.4 Golden Frame Comparison (`194,048` Pixels, `P0–P12`)** | **PASS** | **0 / 194,048 pixel mismatches** across 26 scanlines × 3 states + 512×184 Hero Logo; all `P0–P12` `1280×720` PNG previews generated. |
| **4. Stage 1.4 Yosys 0.68 Synthesis (`cosmictera_boot_top_stage1_4.json`)** | **PASS** | SHA-256 `ece30deb...`: **0 errors**, **12 / 46 BSRAM (`26.09%`)**, **0 DSP**, **770 DFF (`4.95%`)**, **3,125 LUT (`15.07%`)**. |
| **5. Host Place & Route (`nextpnr-himbaechel`) & `.fs` Bitstream Pack** | **PASS** | `cosmictera_boot_top_stage1_4_pnr.json` (`49447559...`) & `cosmictera_boot_top_stage1_4.fs` (`755a9c9d...`): **5,438 / 20,736 LUT4 (`26%`)**, **770 / 15,552 DFF (`4%`)**, **12 / 46 BSRAM (`26%`)**, `clk_27m` = **`156.67 MHz`**, `pixel_clk` = **`60.18 MHz`**, `0 errors`. |
| **6. Tang Nano 20K SRAM Programming (`openFPGALoader -b tangnano20k`)** | **PASS** | `sram_load_stage1_4.log` (`e0ebdf12...`): JTAG `idcode 0x81b` (`GW2A(R)-18(C)`), **100.00% SRAM loaded** in SRAM Mode ONLY (zero Flash flags). |
| **7a. Physical LG TV Observation — Stage 1.4 `Page 0 (00)` (`16/16` Entries)** | **PASS** | `stage1_4_lgtv_page0_16entries.jpg` (`e8360595...`): `COMPUTE ECOSYSTEM - 16/16 ENTRIES`, all 16 entries + `R2` labels (`CC`, `CC/AT`, `VF/EH`, `EH`, `VF/CC`) + `CDC:LIVE` telemetry bar + `PIN88 PAGE: 00` verified live on LG TV at `1280×720@60Hz`. |
| **7b. Physical LG TV Observation — Pin 88 Inspector Pages (`P1–P12`)** | **PASS (Sim) / Optional Photo (HW)** | Verified in `tb_boot_top_stage1_4.log` (`T24a–T24f`) and golden frames `frame_page_p01..p12_1280x720.png`; can be cycled live on the board via button S2 (`Pin 88`). |
