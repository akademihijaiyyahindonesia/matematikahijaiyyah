# COSMICTERA CT-01-REV13 — STAGE 1.4 ARCHITECTURE & IMPLEMENTATION

**Date:** 2026-11-03  
**Repository:** `/Users/AMRA/hijaiyyah-mathematics` (`HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`)  
**Workspace:** `/tmp/stage1_2_cosmictera_boot_ui/`  
**Target Platform:** Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`family=GW2A-18C`), HDMI `1280 × 720 @ 60 Hz` (`74.25 MHz` pixel clock)

---

## 1. CANONICAL GOVERNANCE & SOURCE VERIFICATION ORDER

All Stage 1.4 design and implementation decisions were verified against the 12 mandatory canonical documents in exact order:
1. `AGENTS.md` — Repository map, BAB I & BAB II foundation, naming discipline, and rules `K1–K15`.
2. `cosmictera/RULES.md` — Binding rules `R1–R13`, including **`R2` (Epistemic Labels `VF`, `CC`, `DP`, `EH`, `AT`)**, `R4` (re-measurement mandatory on module changes), and `R10` (Layer 3 HMAC-SHA256 as the sole security bearer in Ka'bah).
3. `COSMICTERA_CT01_REV13_AUDIT.md` — 13-layer ecosystem audit (`CT-01-REV13`) and reconciliation notes.
4. `cosmictera/SYSTEM.md` — Technical architecture of the 25-lane (`1600-bit`) sponge, Canright `GF((2^4)^2)` S-box, and 7-layer stack.
5. `cosmictera/COMPUTING.md` — The four executable pillars (`HCPU`, `Ka'bah`, `7-Layer HOS/HFS Stack`, `NUI`).
6. `teknologi/ISTILAH.md` & `istilah/*.md` — Canonical acronym definitions, file locations, and `R2` epistemic labels.
7. `docs/ARCHITECTURE.md` — HOM / Hijaiyyah system architecture and phase roadmap.
8. `cosmictera-build/ROADMAP.md` — Phased hardware roadmap (`Tang Nano 20K -> Kria KV260`).
9. `cosmictera-build/ON.md` — Verified operational subsystems, commands, and `R2` labels (`VF` for monoid closure, `CC` for guard coverage, HCPU, HOS, HFS, Ka'bah wrapper).
10. `cosmictera-build/OFF.md` — Named blockers (`hijaiyyah_kabah_top` raw 1,665-bit port count = `EH`, Stages 3–6 toward KV260 = `OFF`).
11. `cosmictera-build/CHECKLIST.md` — Reproducible tool and test inventory (`6,347` collected pytest tests, `408` RTL assertions across `39` benches).
12. `cosmictera-build/PAPAN.md` — Physical Tang Nano 20K board execution logs (`HCPU`, `Ka'bah`, `HFS SDIO LBA1`, `HPG1 Loader`).

---

## 2. EPISTEMIC LABEL ENFORCEMENT (`cosmictera/RULES.md` R2) & AUDIT RECONCILIATION

Per Section 2 & Section 3 of the Stage 1.4 mandate, only the **five official epistemic labels defined in `cosmictera/RULES.md` (`R2`)** are used:

| Label | Verbatim Definition in `cosmictera/RULES.md` (`R2`) |
| :---: | :--- |
| **`VF`** | *Verified Formally — terbukti, bukan diuji sampel* |
| **`CC`** | *Computationally Confirmed — dijalankan atas ruang yang habis atau sampel besar* |
| **`DP`** | *Design Property — benar karena konstruksinya, bukan temuan* |
| **`EH`** | *Engineering Hypothesis — terukur, belum dikriptanalisis* |
| **`AT`** | *Aspirational Target — belum dikerjakan* |

### 2.1 Documented Discrepancies Between Earlier Audit Summary and Canonical Repository Sources

In strict compliance with Section 2 (*"Jika laporan audit berbeda dari implementasi atau hasil pengujian terkini, jangan memilih secara sepihak. Catat perbedaannya dan ikuti aturan repository"*) and Section 13, the following discrepancies between `COSMICTERA_CT01_REV13_AUDIT.md` and the canonical repository files were identified and resolved in favor of the canonical repository sources:

1. **Definition of `VF` and Per-Component Labels (`cosmictera/RULES.md` R2 & `teknologi/ISTILAH.md` vs `COSMICTERA_CT01_REV13_AUDIT.md`)**:
   - `COSMICTERA_CT01_REV13_AUDIT.md` §1 redefined `VF` as *"Verified in Hardware"* and assigned `VF` to `HCPU`, `HISA`, `HOS`, `HFS`, `JAMRAH`, `PORTAL 8888`, and `HYBIT`.
   - In **`cosmictera/RULES.md` (`R2`)**, `VF` strictly means *Verified Formally*, while `CC` means *Computationally Confirmed*. In `teknologi/ISTILAH.md`, `cosmictera/CONCRETE.md`, `cosmictera-build/ON.md`, and `portal8888/ARCHITECTURE.md`:
     - `HCPU`, `H-ISA`, `Hybit`, `HISAB`, `HAR`, `CSGI`, `HOM`, `HFS`, `HOS`, `HVM`, `HC`, `HCC`, `HASM`, `HBC`, `Jamrah`, `Hijrah`, and `Codex Jim` carry **`CC`** (`HCPU` is explicitly annotated `CC — berjalan di papan`).
     - `Master Table / Monoid Closure` carries **`VF`** and `Six Guard (93.1% coverage)` carries **`CC`** (`cosmictera-build/ON.md` §1: *"Label: VF untuk closure, CC untuk cakupan guard"*).
     - `Ka'bah` carries **`VF`** for Layer 3 HMAC-SHA256 & $\rho\cdot\pi = 768$, **`DP`** for rate/capacity geometry, **`CC`** for the 20K UART wrapper, and **`EH`** for the 1600-bit sponge (`RULES.md` R2: *"Spons berlabel [EH] dan tetap [EH]"*).
     - `Portal 8888` carries **`EH`** (`portal8888/ARCHITECTURE.md` line 3: *"Label: [EH] / DESAIN"*).
     - `NUI` carries **`CC`** for `nui_embedding.hasm` / `L0–L7` parity and **`AT`** for Roadmap Phases 1–5 (`NUI/ROADMAP.md` & `cosmictera/COMPUTING.md`).
   - **Resolution Implemented in Stage 1.4 RTL**: Every entry in Region 5 (`Page 0`) and `P1–P12` displays its exact canonical `R2` label (`CC`, `VF/CC`, `VF/EH`, `CC/AT`, `EH`) in the text badge, while hardware operational state is displayed separately via the status icon (`✓` `G_CHK`, `○` `G_RNG`, `✕` `G_ERR`) and the `row 56` `CDC:LIVE` telemetry bar.
2. **Source File Paths for `HIJRAH GF(5)` and `COSMIC CODEX JIM / J-MACHINE`**:
   - `COSMICTERA_CT01_REV13_AUDIT.md` §2 listed `hijrah/engine.py` and `cosmic-codex-jim/j_machine.py`.
   - Direct filesystem inspection confirms that `hijrah/` contains `README.md`, `UNIT.md`, `INSTRUCTION.md`, and `JUMP.md` (with executable operator code in `tests/test_integrity/test_hijrah.py`, `test_letter_instructions.py`, `test_degree_panels.py`, `test_degree_function.py`, and `test_letter_machines.py`), and `cosmic-codex-jim/` contains `README.md`, `MACHINE.md`, `WAVE.md`, and `LIMITS.md` (with executable verification in `tests/test_integrity/test_cosmic_codex_jim.py`, `test_letter_machines.py`, and `rtl/hijaiyyah_wave.v`).
3. **Bab II Algebraic Branch Names & Exomatrix Dimension (`P11`)**:
   - `COSMICTERA_CT01_REV13_AUDIT.md` §3.4 used the names `Statimetric, Dynametric, Aggregametric, Intrametric, Exometric` and `Exomatrix 28×28`.
   - In `src/hijaiyyah/algebra/__init__.py`, the five Bab II modules are `vektronometry.py` (`VTM`, Bab II-A), `normivektor.py` (`NMV`, Bab II-B), `aggregametric.py` (`AGM`, Bab II-C), `intrametric.py` (`ITM`, Bab II-D, which computes the `28×28` distance matrix), and `exometric.py` (`EXM`, Bab II-E, which analyzes the `5×5` Exomatrix defined in `src/hijaiyyah/core/exomatrix.py` Def. 32.1.1).
   - **Resolution on `P11`**: The `P11` inspector line (`P11 ALG:STAT/DYN/AGM/ITM/EXM VTM/NMV EXOMATRIX  VF/CC `) includes both the mandate nomenclature (`STAT/DYN/AGM/ITM/EXM`) and the Bab II module abbreviations (`VTM/NMV`), and the full reconciliation is documented in `COSMICTERA_STAGE1_4_P9_P12_INSPECTORS.md`.

---

## 3. OFFICIAL VISUAL IDENTITY & THREE LOGO ASSETS (SECTION 10)

The Boot Display preserves the exact approved visual identity and proportions across the three official brand elements:
1. **CosmicTera Emblem (`cosmictera_emblem.png` / `Logo Logo (5).png`)**:
   - Rendered at the top-left of the Region 1 Header (`x = 28..51, y = 18..41`, `24 × 24` pixels) without cropping or aspect-ratio distortion.
2. **CosmicTera Wordmark & Chrome Orbit Hero Identity (`cosmictera_wordmark.png` / `Logo Logo (6).png` & `cosmictera/Logo CosmicTera Chrome Orbit Logo (1).png`, SHA-256 `8bb2bc13577b1c06a9e19edce0ea9a3076b1eee1ce6c57706b0eef2b9ddf8ead`)**:
   - Rendered in Region 2 (`x = 384..895, y = 76..259`, `512 × 184` pixels) from the lossless-decoded 32-color 9-bit RLE ROM (`logo_rle_rom.hex`, `16,304 / 16,384` words, PSNR `31.98 dB`, `8 BSRAMs`).
3. **Hijaiyyah / Hybit Companion Identity (`hijaiyyah_wordmark.png` / `Logo Logo (7).png` / `data/logo/matematika-hijaiyyah-logo.png` / `hom-gui/public/Hybit Logo Master 001.png`)**:
   - Rendered directly beneath the Hero Wordmark at `rows 34 & 36` (`HIJAIYYAH MATHEMATICAL COMPUTING ARCHITECTURE` / `--- COMPUTING ECOSYSTEM ---`).

---

## 4. SILICON & FPGA TARGET HONESTY (SECTION 8)

Per `cosmictera-build/ROADMAP.md`, `ON.md`, `OFF.md`, `CHECKLIST.md`, and `PAPAN.md`:
- **Tang Nano 20K (`GW2AR-LV18QN88C8/I7` / `GW2A-18C`)**: Active physical FPGA target (`ON` / verified on board in `PAPAN.md` and on LG TV at `1280×720@60Hz`).
- **Sky130 MPW ASIC Shuttle (`rtl/mpw/user_project_wrapper.v`, `hcpu_wishbone_wrapper.v`)**: Designed & planned (`DP` / `OFF` in `OFF.md` — awaiting licensed OpenRAM `sky130_sram_2kbyte_1rw1r_32x512_8` macro views and full PDK DRC/LVS/STA closure; never displayed as active silicon).
- **Xilinx Kria KV260 Master Node Target**: Planned master node target (`DP` / `OFF` in `ROADMAP.md` & `AGENTS.md` §3 — Stages 1–2 `HFS SDIO` and `HPG1 Loader` completed on Tang Nano 20K; Stages 3–6 `Overlay Runtime`, `On-Board HVM`, `Semantic Memory`, `TCP/IP over SLIP` remain `OFF` and are never claimed as active hardware).
