# COSMICTERA CT-01-REV13 — STAGE 1.4 PAGE 0 EXPANSION (16 VISUAL ENTRIES)

**Date:** 2026-11-03  
**Target Region:** Region 5 (`cols 97..156`, `rows 53..72`, `y = 424..583` on `1280 × 720` grid)  
**Layout Geometry:** 2 Columns × 8 Rows = **16 Visual Entries** (`rows 57, 59, 61, 63, 65, 67, 69, 71` with uniform 2-row / `16 px` vertical pitch) + Header (`row 54`) + 87-Bit Live Telemetry / Inspector Bar (`row 56`)

---

## 1. COMPLETE MAPPING OF THE 16 PAGE-0 VISUAL ENTRIES

Note per Section 4 of the Owner Mandate: *Combined visual entries on a single cell slot (`CODEX JIM/J-MAC`, `HM-28/SIX GUARD`, `HPG1 / HCVM`) are strictly a visual layout arrangement and do not merge their underlying implementations or verification records.*

| # | Visual Entry on Page 0 | Grid Position (`Row, Col`) | Canonical Sources Verified in Repository | Canonical `R2` Label | Displayed Badge (`Normal` / `Fault`) | Hardware vs Software Execution Reality |
| :-: | :--- | :---: | :--- | :---: | :---: | :--- |
| **1** | `HCPU` | `Row 57, Left` (`cols 99..123`) | `rtl/hcpu_top.v`, `rtl/hcpu_fetch.v`..`hcpu_writeback.v`, `cosmictera-build/PAPAN.md` | **`CC`** | `CC 120M` / `ER HALT` | **Hardware Silicon (`ON-BOARD`)**: 5-stage pipeline running on Tang Nano 20K (`Fmax 120.63 MHz` post-P&R). |
| **2** | `HISA` | `Row 57, Right` (`cols 126..152`) | `docs/HISA_SPEC.md`, `src/hijaiyyah/hisa/opcodes.py`, `rtl/hcpu_pkg.vh`, `rtl/hcpu_decode.v` | **`CC`** | `CC 82/104 OP` / `ER OPCODE` | **Hardware + SW**: `82` opcodes implemented in RTL (`54` general + `28` letter opcodes `0xE0–0xFB`, incl. `OP_HDOT 0x4E`); `22` opcodes in software HVM. |
| **3** | `HIJAIYYAH CELLS` | `Row 59, Left` (`cols 99..123`) | `src/hijaiyyah/cells/` (`spec.py`, `ir.py`, `hisa_backend.py`), `src/hijaiyyah/compiler/` | **`CC`** | `CC 4GRD` / `ER GRD ` | **Compiler/IR + HCPU**: `.hc` & `.hcell` lowered to `H-ISA` with 4-guard verification. |
| **4** | `HOS` | `Row 59, Right` (`cols 126..152`) | `rtl/programs/hos.hasm`, `rtl/programs/kernel.hasm`, `rtl/tb/tb_hcpu_hos.v` | **`CC`** | `CC 3-PROC OK` / `ER KERNEL` | **Hardware Silicon (`ON-BOARD`)**: 3-process preemptive H-Kernel (`A`, `B`, `C` guard daemon) + heap + mediated `SYSCALL` I/O. |
| **5** | `HFS` | `Row 61, Left` (`cols 99..123`) | `rtl/programs/hos_hfs_disk.hasm`, `rtl/hcpu_sdio.v`, `cosmictera-build/PAPAN.md` | **`CC`** | `CC LBA1` / `ER LBA ` | **Hardware Silicon (`ON-BOARD`)**: Guard-on-Write filesystem persisted across power cycles on microSD `LBA 1..3`. |
| **6** | `HMCL` | `Row 61, Right` (`cols 126..152`) | `src/hijaiyyah/hmcl/`, `rtl/hcpu_codex_alu.v`, `rtl/tb/tb_hmcl_rtl_alternatives.v` | **`CC`** | `CC HDOT 14C ` / `ER CODEX` | **Hardware RTL + Sim**: Multilevel `A1–A3` Codex ALU (`Profile C` Nibble-Split + 14-cycle `HDOT` on board). |
| **7** | `NUI` | `Row 63, Left` (`cols 99..123`) | `src/hijaiyyah/nui/`, `NUI/LAYERS.md`, `NUI/ROADMAP.md`, `rtl/programs/nui_embedding.hasm` | **`CC/AT`** | `CC/AT  ` / `ER NUI ` | **Hybrid**: `nui_embedding.hasm` & `L0–L7` parity confirmed (`CC`); Roadmap Phases 1–5 are aspirational targets (`AT`). |
| **8** | `JAMRAH` | `Row 63, Right` (`cols 126..152`) | `rtl/hijaiyyah_jamrah_gate.v`, `rtl/programs/jamrah.hasm`, `istilah/KABAH.md` | **`CC`** | `CC 33-CLK/B ` / `ER TIMING` | **Hardware RTL + HASM**: 7-node constant-time triage gate (`33 clocks/byte`, `0` secret-dependent branches, `256/256` parity). |
| **9** | `KA'BAH` | `Row 65, Left` (`cols 99..123`) | `src/hijaiyyah/crypto/cube.py`, `rtl/hijaiyyah_kabah_top.v`, `cosmictera/CONCRETE.md` | **`VF/EH`** | `VF/EH  ` / `ER MAC ` | **Hardware Wrapper (`ON-BOARD`) + Crypto**: Layer 3 HMAC-SHA256 & $\rho\cdot\pi=768$ (`VF`), 20K UART wrapper 400/400B (`CC`), 1600-bit sponge (`EH`). |
| **10** | `PORTAL 8888` | `Row 65, Right` (`cols 126..152`) | `portal8888/ARCHITECTURE.md`, `src/hijaiyyah/nui/portal_8888.py` | **`EH`** | `EH P8 SEALED` / `ER UNSEALED` | **Experimental Workstream (`EH`)**: 125-byte canonical provenance body & `P8-1..P8-4` sealer validated in simulation + limited UART runs. |
| **11** | `HYBIT 18D` | `Row 67, Left` (`cols 99..123`) | `src/hijaiyyah/core/hybit.py`, `Hybit/Bab_III_Hybit_Paradigma_Komputasi_Ketiga.md`, `rtl/hcpu_regfile.v`, `rtl/hcpu_guard.v` | **`CC`** | `CC 144B` / `ER HREG` | **Hardware Silicon (`ON-BOARD`)**: $V \subset \mathbb{N}_0^{18}$ (`144-bit = 18×8` in `H0–H15` / banked `H-Reg` + hardware `HGRD`). |
| **12** | `HIJRAH GF(5)` | `Row 67, Right` (`cols 126..152`) | `hijrah/README.md`, `hijrah/UNIT.md`, `hijrah/INSTRUCTION.md`, `hijrah/JUMP.md`, `tests/test_integrity/test_hijrah.py` | **`CC`** | `CC 700/700  ` / `ER GF5 OP` | **Letter Instructions (`RTL`) + Operator Analysis (`SW`)**: 28 letter opcodes `0xE0–0xFB` in HCPU RTL + `700/700` $\text{GF}(5)$ operator compositions (`4.56 bits/letter` at depth 5). |
| **13** | `CODEX JIM/J-MAC` | `Row 69, Left` (`cols 99..123`) | `cosmic-codex-jim/README.md`, `MACHINE.md`, `WAVE.md`, `LIMITS.md`, `rtl/hijaiyyah_wave.v`, `tests/test_integrity/test_cosmic_codex_jim.py` | **`CC`** | `CC 5X5 ` / `ER WAVE` | **Mathematical Measurement & Wave RTL**: `5×5` Exomatrix of Jim (`0xE4`) reaches maximal order in both $\text{GF}(2)=31$ and $\text{GF}(5)=3124$ + Golomb postulates. |
| **14** | `HISAB ENGINE` | `Row 69, Right` (`cols 126..152`) | `rtl/hcpu_hisab.v`, `src/hijaiyyah/hisab/` (`digest.py`, `protocol.py`, `serialize.py`, `validate.py`) | **`CC`** | `CC CRC32/28 ` / `ER HISAB` | **Hardware RTL + Protocol**: Nibble-packing + CRC32 auditable bridging (`rtl/hcpu_hisab.v` verified across 28 letters, 124 assertions). |
| **15** | `HM-28/SIX GUARD` | `Row 71, Left` (`cols 99..123`) | `src/hijaiyyah/core/master_table.py`, `rtl/hcpu_rom.v`, `src/hijaiyyah/core/guards.py`, `rtl/hcpu_guard.v` | **`VF/CC`** | `VF/CC  ` / `ER ROM ` | **Hardware Silicon (`ON-BOARD`)**: `28 × 72-bit` sealed Master Table ROM + 1-cycle `G1–G4` & `T1–T2` guard verifier (`VF` closure, `CC` 93.1% coverage). |
| **16** | `HPG1 / HCVM` | `Row 71, Right` (`cols 126..152`) | `rtl/programs/hos_prog_load.hasm`, `src/hijaiyyah/cells/hpg1_bridge.py`, `hcvm.py`, `src/hijaiyyah/vm/` | **`CC`** | `CC L9/SW-VM ` / `ER LOADER` | **Separated Hardware Loader + Host VM**: `HPG1` (`SYSCALL 9` `LOAD_PROGRAM` + `CHECKSUM32`) runs on board; `HCVM` (`hcvm.py`, `src/hijaiyyah/vm/`) is the host software bytecode VM (`SW-VM`). |

---

## 2. NON-COLLISION & BSRAM PACKING GEOMETRY

- **Vertical Non-Collision**:
  - Region 5 occupies `rows 53..72` (`y = 424..583`).
  - Header is on `row 54` (`y = 432..439`), divider line at `y = 444` (`row 55`), Telemetry/Inspector Bar on `row 56` (`y = 448..455`), and the 8 subsystem rows sit on `rows 57, 59, 61, 63, 65, 67, 69, 71` (`y = 456..575`), leaving a full `8 px` margin above the Region 5 bottom border (`y = 583`) and `16 px` above the Region 6 Hardware Event Console (`row 74`, `y = 592`).
- **Zero-Extra-BSRAM Folding in `cosmictera_boot_text_rom.v`**:
  - Screen rows `56, 59, 61` use previously spare ROM rows `22, 23, 24` inside the `4,096 × 12-bit` BSRAM (`25 × 160 = 4,000 <= 4,096`).
  - Screen rows `65` and `67` (which only contain text in Region 5, `la_col >= 96`) fold into the unused right halves (`la_col >= 96`) of ROM rows `11` (`row 60`) and `13` (`row 66`), keeping total Text ROM utilization at **exactly 3 BSRAMs (`0` additional BSRAMs)**.
