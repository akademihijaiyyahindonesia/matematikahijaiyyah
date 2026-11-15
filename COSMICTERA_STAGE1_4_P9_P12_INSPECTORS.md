# COSMICTERA CT-01-REV13 — STAGE 1.4 INSPECTOR PAGES P1–P12 SPECIFICATION

**Date:** 2026-11-03  
**Navigation Input:** `mode_key` (Pin 88, active-low button via `rtl/hcpu_page_key.v`, `PAGES = 13`)  
**Display Bar Coordinates:** `row 56, cols 99..152` (`54` characters) + Footer indicator `row 88, cols 118..119` (`PIN88 PAGE: 00..12`)

---

## 1. PRESERVED PAGES `P0–P8` (SECTION 6)

All existing functions and mappings of `P0–P8` are preserved intact, with their trailing status field aligned to canonical `cosmictera/RULES.md` (`R2`) epistemic labels:

| Page | Exact 54-Character Display String (`row 56, cols 99..152`) | Canonical Sources | `R2` Label |
| :---: | :--- | :--- | :---: |
| **`P0`** | `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE` | `rtl/hcpu_telemetry.v`, `cosmictera_boot_subsys_bridge.v` | Live 87-bit CDC |
| **`P1`** | `P1 HM-28 ROM:28X72B HYBIT:18D GUARD:G1-G4/T1-T2 VF/CC ` | `master_table.py`, `hcpu_rom.v`, `hybit.py`, `hcpu_guard.v` | `VF/CC` |
| **`P2`** | `P2 HISA:82/104 RTL CODEX:PROFILE-C HDOT:14-CYC  [CC]  ` | `docs/HISA_SPEC.md`, `opcodes.py`, `hcpu_codex_alu.v` | `CC` |
| **`P3`** | `P3 CELLS:.HCELL-IR-HISA PSI:331/331 HPG1:4-B'   [CC]  ` | `src/hijaiyyah/cells/`, `psi_injector.py`, `hos_prog_load.hasm` | `CC` |
| **`P4`** | `P4 HOS:3-PROC PREEMPT HFS:SDIO LBA1+16 PERSIST  [CC]  ` | `rtl/programs/hos.hasm`, `hos_hfs_disk.hasm`, `hcpu_sdio.v` | `CC` |
| **`P5`** | `P5 HMCL:L0-L12 A1:DSP A2:RADIX4 A3:NIBBLE-SPLIT [CC]  ` | `src/hijaiyyah/hmcl/multilevel_sim.py`, `hcpu_codex_alu.v` | `CC` |
| **`P6`** | `P6 NUI:12-LAYER L0-L7:PARITY THEOREMS:18/18     CC/AT ` | `src/hijaiyyah/nui/`, `NUI/LAYERS.md`, `NUI/ROADMAP.md`, `theorems/` | `CC/AT` |
| **`P7`** | `P7 JAMRAH:7-NODE 33-CLK/B HIJRAH:GF(5) 700/700  [CC]  ` | `rtl/hijaiyyah_jamrah_gate.v`, `hijrah/README.md`, `test_hijrah.py` | `CC` |
| **`P8`** | `P8 KABAH:1600B+HMAC-L3 207/207 PORTAL8888:SEAL  VF/EH ` | `src/hijaiyyah/crypto/cube.py`, `portal8888/ARCHITECTURE.md` | `VF/EH` |

---

## 2. NEW INSPECTOR PAGES `P9–P12` (SECTION 7)

### 2.1 `P9` — COSMIC CODEX JIM / J-MACHINE
- **Exact 54-Char Inspector String (`row 56, cols 99..152`):**
  ```
  P9 JIM:0XE4 5X5 LFSR/J-MACH GF2:31 GF5:3124 WAVE [CC] 
  ```
- **Canonical Sources & Tests:**
  - `cosmic-codex-jim/README.md`, `cosmic-codex-jim/MACHINE.md`, `cosmic-codex-jim/WAVE.md`, `cosmic-codex-jim/LIMITS.md`, `istilah/CODEX-JIM.md`
  - `rtl/hijaiyyah_wave.v`, `src/hijaiyyah/crypto/wave.py`
  - `tests/test_integrity/test_cosmic_codex_jim.py` & `tests/test_integrity/test_letter_machines.py`
- **Verified Technical Facts Displayed:**
  - Letter **Jim (`ج`)**, index `4`, H-ISA opcode **`0xE4`**, $\hat{\Theta} = 3$ (`270°`), $\rho = 3$, $U = 0$, `8 / 25` non-zero cells in its **`5 × 5` Exomatrix face**.
  - Iterated as a linear map (LFSR / J-Machine), Jim is the **only letter among the 28** that achieves maximal multiplicative order in two distinct finite fields simultaneously: **$\text{GF}(2)$ period $2^5 - 1 = 31$** and **$\text{GF}(5)$ period $5^5 - 1 = 3124$**, satisfying all three Golomb randomness postulates (`WAVE.md`).
  - Epistemic label: **`CC`** (*Computationally Confirmed* across exhaustive state spaces).

### 2.2 `P10` — HISAB & RAMAL
- **Exact 54-Char Inspector String (`row 56, cols 99..152`):**
  ```
  P10 HISAB:JUMMAL/MOD-RED CRC32 RAMAL:CORE+IMPULSE [CC]
  ```
- **Canonical Sources & Tests:**
  - `rtl/hcpu_hisab.v` (`tb_hisab.v` — 28-letter sweep, 124 assertions), `src/hijaiyyah/hisab/` (`digest.py`, `protocol.py`, `serialize.py`, `validate.py`), `matematika-hijaiyyah/LINEAGE.md` (`test_jummal_lineage.py`)
  - `rtl/hijaiyyah_ramal_core.v`, `rtl/hijaiyyah_ramal_impulse.v`, `rtl/hijaiyyah_sponge.v`
- **Verified Technical Facts Displayed:**
  - **Hisab Engine**: Implements `HISAB` (*Hijaiyyah Inter-System Standard for Auditable Bridging*, `teknologi/ISTILAH.md`) nibble-packing, modular reduction, jummal lineage evaluation, and `CRC32` integrity verification in both Python and `rtl/hcpu_hisab.v`.
  - **Ramal Core & Ramal Impulse**: `rtl/hijaiyyah_ramal_core.v` and `rtl/hijaiyyah_ramal_impulse.v` generate the 112 impulser pulses per permutation (`2 × 310 = 622` hold clocks) that drive the Ka'bah sponge rounds (`istilah/KABAH.md`).
  - Epistemic label: **`CC`**.

### 2.3 `P11` — FIVE ALGEBRAIC BRANCHES
- **Exact 54-Char Inspector String (`row 56, cols 99..152`):**
  ```
  P11 ALG:STAT/DYN/AGM/ITM/EXM VTM/NMV EXOMATRIX  VF/CC 
  ```
- **Canonical Sources & Reconciliation Note:**
  - `src/hijaiyyah/algebra/__init__.py`:
    1. `vektronometry.py` (`VTM`, Bab II-A, Ch 17–21) — referred to as `Statimetric` in `COSMICTERA_CT01_REV13_AUDIT.md`
    2. `normivektor.py` (`NMV`, Bab II-B, Ch 22–24) — referred to as `Dynametric` in `COSMICTERA_CT01_REV13_AUDIT.md`
    3. `aggregametric.py` (`AGM`, Bab II-C, Ch 25–28) — monoid string integral $\text{Cod}_{18}(w) = \sum v_{18}(x_i)$
    4. `intrametric.py` (`ITM`, Bab II-D, Ch 29–31) — inner product, Euclidean metric $d(h_1, h_2)$, and `28 × 28` pairwise distance matrix
    5. `exometric.py` (`EXM`, Bab II-E, Ch 32–36) & `src/hijaiyyah/core/exomatrix.py` — builds and audits (`R1–R5`) the `5 × 5` Exomatrix per letter across all 28 letters (with documented transpose orientation verified by `tests/test_integrity/test_bab_dua.py`).
  - Epistemic label: **`VF/CC`** (`cosmictera-build/ON.md` §1: `VF` for monoid closure, `CC` for guard/metric verification).

### 2.4 `P12` — SOFTWARE COMPUTE ECOSYSTEM
- **Exact 54-Char Inspector String (`row 56, cols 99..152`):**
  ```
  P12 SW:HCVM HAR HYBIT-AI CSGI HOM-GUI (HOST/SW)  [CC] 
  ```
- **Canonical Sources:**
  - `hcvm.py` & `src/hijaiyyah/vm/` (`HVM` / `HCVM` — 45 tests in `tests/test_vm/`)
  - `src/hijaiyyah/har/` & `src/hijaiyyah/core/har.py` (`HAR-001` Alphabet Registry — 15 tests)
  - `src/hijaiyyah/ai/` (`hybit-ai` CLI & runtime)
  - `run_csgi_latin.py` & `src/hijaiyyah/skeleton/csgi.py` (`CSGI` Canonical Skeleton Graph Interface)
  - `hom-gui/` & `src/hijaiyyah/gui/` (`HOM` Hijaiyyah Operating Machine GUI)
- **Strict Hardware Honesty**:
  - Explicitly prefixed with `SW:` and tagged `(HOST/SW)` so that software-only ecosystem tools are never misrepresented as running inside the FPGA fabric.
  - Epistemic label: **`CC`** (`teknologi/ISTILAH.md` & `cosmictera-build/ON.md` §2).
