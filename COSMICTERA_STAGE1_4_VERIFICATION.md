# COSMICTERA CT-01-REV13 — STAGE 1.4 HARDWARE & GOLDEN FRAME VERIFICATION REPORT

**Date:** 2026-11-03  
**Testbench:** `/tmp/stage1_2_cosmictera_boot_ui/rtl/tb_boot_top.v`  
**Golden Frame Verifier:** `/tmp/stage1_2_cosmictera_boot_ui/verify_frames_and_render_previews.py`  
**Result:** **30 / 30 RTL Assertions PASS (`0 FAIL`)** and **0 / 194,048 Pixel Mismatches (`100% Bit-Exact`)**

---

## 1. PIN 88 (`mode_key`) NAVIGATION & WRAPAROUND VERIFICATION (SECTION 9)

- **Module Inspected:** `rtl/hcpu_page_key.v` (instantiated in `cosmictera_boot_top.v` with `.PAGES(13)`).
- **Register Width Verification:** `output reg [3:0] page` is 4 bits wide (`0..15`), supporting `PAGES = 13` (`4'd0` through `4'd12`) with zero truncation.
- **Wraparound Condition:** `(page == PAGES - 1) ? 4'd0 : page + 4'd1` transitions cleanly from `4'd12` (`P12`) back to `4'd0` (`P0`) on short-press release, while long-press (`held == LONG_MAX - 1`) resets `page <= 4'd0` from any page.
- **Footer Display (`row 88, cols 118..119`):** Upgraded to 2 decimal digits (`00` through `12`) so `P10`, `P11`, and `P12` render as decimal `10`, `11`, `12` rather than hexadecimal `A`, `B`, `C`.

---

## 2. FULL RTL TESTBENCH LOG (`tb_boot_top.log` — 30 PASS, 0 FAIL)

```text
=== COSMICTERA STAGE 1.2 BOOT DISPLAY RTL VERIFICATION ===
[PASS] T14a PLL lock glitch before 2ms threshold resets qualification
[PASS] T14b PLL lock qualified after full threshold
[PASS] T13 Reset order: CLKDIV.RESETN -> OSER10.RESET -> vid_rst_n
[PASS] T12/T18 Initial screen state is SCREEN_STARTUP (2'd0)
[PASS] 08/T20 Captured 26 region scanlines (incl. all 16 entries) with 0 blanking leaks
[PASS] T05 Full 512x184 RLE Hero Logo streamed exact 16,304 words (rom_ok=1)
[PASS] T01a H_FRONT (h_count=1280): de=0, hsync=0
[PASS] T01b H_SYNC (h_count=1390..1429): hsync=1 positive pulse
[PASS] T01c H_BACK (h_count=1430..1649): hsync=0
[PASS] T01d V_SYNC (v_count=725..729): vsync=1 positive pulse, de=0
[PASS] T02/T03 TMDS 8b/10b disparity bounded [-8..+8] & OSER10 active
[PASS] T12 All 10 stages READY -> SCREEN_READY (2'd1)
[PASS] T10 Event FIFO recorded 6 hardware boot events (EV01..EV06)
[PASS] T09/T20b Uptime BCD counter + CDC incremented to 00:05:42
[PASS] 08/T20 Captured 26 region scanlines (incl. all 16 entries) with 0 blanking leaks
[PASS] T15 PLL lock loss immediately asserts safe staged resets
[PASS] T16 PLL relock recovery increments relock_count_pix to 01
[PASS] T17 Mid-scanline reset clears timing counters, snap_valid=0, and blanks RGB
[PASS] T11/T19 Fault state SCREEN_ERROR (2'd2) & FIFO overflow indicator set
[PASS] 08/T20 Captured 26 region scanlines (incl. all 16 entries) with 0 blanking leaks
[PASS] T19b Logo ROM fault flag activates text fallback
[PASS] T21 All 16 CosmicTera ecosystem entries operational (32'hAAAA_AAAA)
[PASS] T22 Coherent 87-bit HCPU telemetry CDC captured PC=3F8 IN=4E030400 CY=00108888
[PASS] T23 16-bit fault mask isolates HMCL & HIJRAH faults while HCPU stays OK
[PASS] T24a Pin 88 mode_key reaches preserved PAGE 8 (KA'BAH / PORTAL 8888)
[PASS] T24b Pin 88 transitions P8 -> P9 (COSMIC CODEX JIM / J-MACHINE)
[PASS] T24c Pin 88 transitions P9 -> P10 (HISAB & RAMAL)
[PASS] T24d Pin 88 transitions P10 -> P11 (FIVE ALGEBRAIC BRANCHES)
[PASS] T24e Pin 88 transitions P11 -> P12 (SOFTWARE COMPUTE ECOSYSTEM)
[PASS] T24f Pin 88 wraps around cleanly from P12 -> P0 (HOME)
=== SUMMARY: 30 PASS, 0 FAIL ===
```

---

## 3. GOLDEN FRAME PIXEL-BY-PIXEL COMPARISON (`1280 × 720`)

`verify_frames_and_render_previews.py` generated full `1280 × 720` PNG golden frames for:
- `frame_startup_1280x720.png` (`SCREEN_STARTUP = 0`)
- `frame_ready_1280x720.png` (`SCREEN_READY = 1`, `PAGE 0` with all 16 ecosystem entries + 87-bit telemetry bar)
- `frame_error_1280x720.png` (`SCREEN_ERROR = 2`, fault injection & FIFO overflow)
- `frame_page_p01_1280x720.png` through `frame_page_p12_1280x720.png` (all 12 inspector pages `P1–P12`)

And compared the RTL simulation dumps across **26 scanlines** (`y = [0, 18, 34, 62, 76, 274, 290, 320, 330, 354, 386, 434, 450, 458, 474, 482, 490, 506, 522, 538, 554, 570, 602, 618, 650, 706]`, covering `row 54` header, `row 56` telemetry/inspector bar, and **every single row `57, 59, 61, 63, 65, 67, 69, 71` of the 16-entry grid**):

| Verification Target | Pixels Compared | Mismatches | Status |
| :--- | :---: | :---: | :---: |
| **512 × 184 Hero Chrome Orbit Logo (`rtl_hero_logo_512x184.raw`)** | `94,208` | **`0`** | **PASS** |
| **26 Region Scanlines — `SCREEN_STARTUP` (`rtl_scanlines_startup.raw`)** | `33,280` | **`0`** | **PASS** |
| **26 Region Scanlines — `SCREEN_READY` (`rtl_scanlines_ready.raw`)** | `33,280` | **`0`** | **PASS** |
| **26 Region Scanlines — `SCREEN_ERROR` (`rtl_scanlines_error.raw`)** | `33,280` | **`0`** | **PASS** |
| **Total Bit-Exact Pixels Verified** | **`194,048`** | **`0`** | **PASS** |
