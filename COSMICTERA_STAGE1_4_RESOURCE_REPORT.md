# COSMICTERA CT-01-REV13 — STAGE 1.4 FPGA RESOURCE & TIMING REPORT

**Date:** 2026-11-03  
**Synthesis Tool:** Yosys `0.68+post` (`synth_gowin -nodsp -top cosmictera_boot_top`)  
**Target Device:** Gowin `GW2AR-LV18QN88C8/I7` (`Tang Nano 20K`, `family=GW2A-18C`)  
**Pin / Clock / Serializer Invariance:** HDMI pins (`33, 35, 37, 39` Candidate B `LVCMOS33D DRIVE=8`), `TMDS_rPLL` (`371.25 MHz`), `CLKDIV /5` (`74.25 MHz`), and `OSER10` serializers are **100% unchanged**.

---

## 1. MEASURED RESOURCE COMPARISON (STAGE 1.3 vs STAGE 1.4)

Per Section 5 & Section 11 of the Owner Mandate, resources were re-measured via full Yosys Gowin synthesis (`yosys_synth.log`) after expanding Page 0 from 10 to 16 entries and expanding the Pin 88 inspector from `P0–P8` (`9` pages) to `P0–P12` (`13` pages):

| Resource Primitive | Stage 1.3 (10 Entries, `P0–P8`) | Stage 1.4 (16 Entries, `P0–P12`) | Delta (`Stage 1.4 - Stage 1.3`) | GW2AR-18C Capacity | Stage 1.4 Utilization |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`BSRAM` (`SP` + `SPX9`)** | `12` (`3 SP + 9 SPX9`) | **`12` (`3 SP + 9 SPX9`)** | **`0` (`+0.0%`)** | `46` | **`26.09%`** |
| **`DSP` (`MULT18X18`)** | `0` | **`0`** | **`0`** | `28` | **`0.00%`** |
| **Logic `LUT2 + LUT3 + LUT4`** | `2,926` (`568+700+1,658`) | **`3,125` (`592+756+1,777`)** | **`+199 LUT`** | `20,736` | **`15.07%`** |
| **Wide Mux (`MUX2_LUT5..8`)** | `960` (`697+180+63+20`) | **`899` (`667+158+54+20`)** | **`-61 MUX`** | Packed in Slice | — |
| **Carry `ALU`** | `1,387` | **`1,401`** | **`+14 ALU`** | Packed in Slice | — |
| **Flip-Flops (`DFF*` Total)** | `726` | **`770`** | **`+44 DFF`** | `15,552` | **`4.95%`** |
| **Clock / IO Primitives** | `1 rPLL, 1 CLKDIV, 4 OSER10, 4 OBUF, 3 IBUF` | **`1 rPLL, 1 CLKDIV, 4 OSER10, 4 OBUF, 3 IBUF`** | **`0`** | — | **100% Identical** |

### 1.1 Why BSRAM Remained Strictly at `12 / 46` (`+0 BSRAM`)
- `cosmictera_boot_logo_rom.v`: `8` `SPX9` blocks (`16,304 × 9-bit` RLE words — unchanged).
- `hcpu_font_rom.v`: `1` `SPX9` block (`1,024 × 8-bit` glyphs — unchanged).
- `cosmictera_boot_text_rom.v`: `3` `SP` blocks (`4,096 × 12-bit`). By mapping the 3 new Region-5-only rows (`56, 59, 61`) to spare ROM rows `22, 23, 24` (`25 × 160 = 4,000 <= 4,096`) and folding the Region-5 cells (`la_col >= 96`) of rows `65` and `67` into the unused right halves of ROM rows `11` (`row 60`) and `13` (`row 66`), all 16 visual entries fit inside the **exact same 3 BSRAM blocks**!

### 1.2 Why LUTs Increased by `+199` and DFFs Increased by `+44`
- Expanding `cosmictera_boot_subsys_bridge.v` from 10 to 16 BIST stages (`bist_done_27m[15:0]`, `bist_err_27m[15:0]`) and 2-FF CDC synchronizers (`done_s1/s2[15:0]`, `err_s1/s2[15:0]`) added **44 DFFs** (`726 -> 770`).
- Expanding `cosmictera_boot_compositor.v` with `P9–P12` (`page_telem_char`), 8-row `sub_left_char` / `sub_right_char` tables, and 2-digit decimal page rendering added **199 LUTs** (`2,926 -> 3,125`) while reducing `MUX2_LUT5..8` by **61 cells** (`960 -> 899`).

---

## 2. UPDATED UNIFIED SoC SEPARATE-SYNTHESIS ESTIMATION TABLE

| Resource | Compute Core (`cosmictera_top`) | Stage 1.4 Boot Display (`cosmictera_boot_top`) | Separate Synthesis Sum (Uncompressed Logo) | Separate Synthesis Sum (Compact 4-BSRAM Logo) | GW2AR-18C Capacity | Remaining Headroom (Compact Target) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Yosys LUT (`LUT2+3+4`)** | `15,351` | `3,125` | **`18,476`** (`89.10%`) | **`~18,250`** (`88.01%`) | `20,736` | **`+2,486 LUT` (`11.99%`)** |
| **Flip-Flops (`DFF`)** | `~6,410` | `770` | **`7,180`** (`46.17%`) | **`~7,140`** (`45.91%`) | `15,552` | **`+8,412 DFF` (`54.09%`)** |
| **BSRAM** | `28` | `12` | **`40`** (`86.96%`) | **`32`** (`69.57%`) | `46` | **`+14 BSRAM` (`30.43%`)** |
| **DSP (`MULT18X18`)** | `2` (`0` w/ `-nodsp`) | `0` | **`2`** (`7.14%`) | **`2`** (`7.14%`) | `28` | **`+26 DSP` (`92.86%`)** |
