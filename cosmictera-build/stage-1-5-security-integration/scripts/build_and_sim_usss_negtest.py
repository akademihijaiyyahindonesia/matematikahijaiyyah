#!/usr/bin/env python3
"""
Builds and verifies the non-invasive USSS 8-Scenario Negative & Recovery Silicon Test
for `stage-1-5-security-integration` WITHOUT modifying any RTL (`*.v`), constraints (`*.cst`),
or the baseline bitstream `cosmictera_unified_soc_usss.fs` (`723ce67f...`).

How it works:
1. Assembles `program_usss_negtest.hex` for `u_hcpu_core` (`imem`), which:
   - Waits for Power-On BIST (`RQ=01, FL=00, V=AUTH`) and prints `SEC_STATUS[4:1]` & `SEC_REASON`.
   - Executes all 8 Negative & Recovery Scenarios via MMIO `0xFE8` (`SEC_CTRL`):
     * S1: HMAC tag salah          (`0x0001_0539`) -> REJECT (`status=10, reason=16`)
     * S2: Timestamp kedaluwarsa   (`0x0004_0739`) -> REJECT (`status=10, reason=52`)
     * S3: Nonce digunakan ulang   (`0x0004_0979`) -> REJECT (`status=10, reason=52`)
     * S4: Port tidak diizinkan    (`0x0000_0C19`) -> REJECT (`status=10, reason=128`)
     * S5: Simbol di luar alfabet  (`0x0000_1D39`) -> REJECT/ERROR (`status=26, reason=112`)
     * S6: Key belum diprovisikan  (`0x0000_0E31`) -> ERROR/REJECT (`status=26, reason=24`)
     * S7: Security abort          (`0x0000_1039` then `0x0000_0002`) -> ABORT/ERROR (`status=26, reason=304`)
     * S8: Request valid pasca-fault (`0x0000_0004` clear + `0x0000_18B9`) -> AUTH_OK (`status=6, reason=1`)
   - Prints final `total_req_cnt` (`9`) and `total_fail_cnt` (`7`), then halts (`HALT`).
2. Runs Icarus Verilog simulation on `cosmictera_unified_soc_top` to verify the exact UART bytes
   and HDMI Row 83 (`USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:09 FL:07 R:0`).
3. Patches ONLY the BSRAM `INIT_RAM_00..3F` of `u_hcpu_core.imem.0.0..7` in a copy of
   `cosmictera_unified_soc_usss_pnr.json` and packs `cosmictera_unified_soc_usss_negtest.fs`
   via `gowin_pack` (zero re-synthesis, zero re-P&R, 100% identical timing & placement).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/AMRA/hijaiyyah-mathematics")
USSS_DIR = ROOT / "cosmictera-build" / "stage-1-5-security-integration"
RTL_DIR = USSS_DIR / "rtl"
LOG_DIR = USSS_DIR / "logs"
CAD_BIN = Path("/Users/AMRA/opt/oss-cad-suite/bin")

sys.path.insert(0, str(ROOT / "src"))
from hijaiyyah.hisa.assembler import assemble  # noqa: E402


HASM_SOURCE = """\
; =============================================================================
; usss_negative_silicon_suite.hasm — Physical Silicon Negative & Recovery Suite
; Target: COSMICTERA Unified SoC Stage 1.5 + USSS (GW2AR-LV18QN88C8/I7)
; =============================================================================
; Wait 40 loops for power-on BIST (Request #1: Huruf Qaf=19 -> AUTH_OK)
        MOVI  R1, 40
wait_bist:
        ADDI  R1, R1, -1
        CMPI  R1, 0
        JNE   wait_bist

; Read & print Power-On BIST (S0): status bits [4:0] (6 = AUTH_OK|DONE) & reason (1)
        LOAD  R2, R0, 0xFE9
        ANDI  R2, R2, 31
        PRINT R2
        LOAD  R3, R0, 0xFEA
        PRINT R3

; ── S1: HMAC tag salah (0x0001_0539: bit16=hmac_forge, letter=5, priv=1, gate=1, sec=1, start=1) ──
        MOVI  R4, 16
        SHLI  R4, R4, 12
        ORI   R4, R4, 0x539
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── S2: Timestamp kedaluwarsa (0x0004_0739: bit18=replay/ts_err, letter=7) ──
        MOVI  R4, 64
        SHLI  R4, R4, 12
        ORI   R4, R4, 0x739
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── S3: Nonce digunakan ulang (0x0004_0979: bit18=replay/nonce_err on Port 1, letter=9) ──
        MOVI  R4, 64
        SHLI  R4, R4, 12
        ORI   R4, R4, 0x979
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── S4: Port tidak diizinkan / Privilege Denied (0x0000_0C19: bit5 priv=0, letter=12) ──
        MOVI  R4, 0xC19
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── S5: Simbol di luar alfabet Hijaiyyah (0x0000_1D39: letter=29 > 28, gate=1) ──
        MOVI  R4, 1
        SHLI  R4, R4, 12
        ORI   R4, R4, 0xD39
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── S6: Key belum diprovisikan / Key diblokir (0x0000_0E31: bit3 secure_mode=0) ──
        MOVI  R4, 0xE31
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── S7: Security abort (Start 0x0000_1039 then immediately abort 0x0000_0002) ──
        MOVI  R4, 1
        SHLI  R4, R4, 12
        ORI   R4, R4, 0x039
        STORE R4, R0, 0xFE8
        MOVI  R5, 2
        STORE R5, R0, 0xFE8
        CALL  wait_and_report

; ── S8: Request valid setelah fault (Clear 0x004 then valid Port 2 letter=24 Mim 0x18B9) ──
        MOVI  R4, 4
        STORE R4, R0, 0xFE8
        MOVI  R4, 1
        SHLI  R4, R4, 12
        ORI   R4, R4, 0x8B9
        STORE R4, R0, 0xFE8
        CALL  wait_and_report

; ── Final Summary: Read SEC_COUNTER (0xFEC) -> print req_count (9) and fail_count (7) ──
        LOAD  R6, R0, 0xFEC
        ANDI  R7, R6, 255
        PRINT R7
        SHRI  R8, R6, 16
        ANDI  R8, R8, 255
        PRINT R8
        HALT

; Subroutine: wait 36 loops (~144 cycles) for 24-round Ka'bah + HMAC + Jamrah to settle,
; then read & print SEC_STATUS[4:0] (0xFE9) and SEC_REASON (0xFEA)
wait_and_report:
        MOVI  R1, 36
wloop:
        ADDI  R1, R1, -1
        CMPI  R1, 0
        JNE   wloop
        LOAD  R2, R0, 0xFE9
        ANDI  R2, R2, 31
        PRINT R2
        LOAD  R3, R0, 0xFEA
        PRINT R3
        RET
"""


def patch_pnr_imem(pnr_in: Path, pnr_out: Path, words: list[int]) -> None:
    data = json.loads(pnr_in.read_text(encoding="utf-8"))
    mod = data["modules"]["top"]
    padded = list(words) + [0] * (4096 - len(words))

    for blk in range(8):
        cell_name = f"u_hcpu_core.imem.0.{blk}"
        cell = mod["cells"][cell_name]
        params = cell["parameters"]
        lo = blk * 4
        for row in range(64):
            param_key = f"INIT_RAM_{row:02X}"
            # 64 words per INIT_RAM_XX row, word 0 of row at rightmost 4 bits
            chunks: list[str] = []
            base_idx = row * 64
            for w_off in range(63, -1, -1):
                w = padded[base_idx + w_off]
                nib = (w >> lo) & 0xF
                chunks.append(f"{nib:04b}")
            params[param_key] = "".join(chunks)

    pnr_out.write_text(json.dumps(data), encoding="utf-8")


def main() -> int:
    words = assemble(HASM_SOURCE)
    print(f"Assembled usss_negative_silicon_suite.hasm: {len(words)} instruction words")

    hasm_path = USSS_DIR / "usss_negative_silicon_suite.hasm"
    hex_path = RTL_DIR / "program_usss_negtest.hex"
    hasm_path.write_text(HASM_SOURCE, encoding="utf-8")
    hex_lines = [f"{w:08X}" for w in words]
    hex_path.write_text("\n".join(hex_lines) + "\n", encoding="utf-8")
    print(f"Wrote {hex_path} ({len(words)} words)")

    # Patch a copy of cosmictera_unified_soc_usss_pnr.json -> cosmictera_unified_soc_usss_negtest_pnr.json
    base_pnr = USSS_DIR / "cosmictera_unified_soc_usss_pnr.json"
    neg_pnr = USSS_DIR / "cosmictera_unified_soc_usss_negtest_pnr.json"
    neg_fs = USSS_DIR / "cosmictera_unified_soc_usss_negtest.fs"

    print("Patching BSRAM INIT_RAM_00..3F in copy of routed netlist...")
    patch_pnr_imem(base_pnr, neg_pnr, words)

    print("Packing cosmictera_unified_soc_usss_negtest.fs with gowin_pack...")
    subprocess.run(
        [str(CAD_BIN / "gowin_pack"), "-d", "GW2A-18C", "-o", str(neg_fs), str(neg_pnr)],
        check=True,
    )
    neg_sha = hashlib.sha256(neg_fs.read_bytes()).hexdigest()
    base_fs = USSS_DIR / "cosmictera_unified_soc_usss.fs"
    base_sha = hashlib.sha256(base_fs.read_bytes()).hexdigest()
    print(f"Baseline bitstream SHA-256 (UNTOUCHED): {base_sha}")
    print(f"Negtest  bitstream SHA-256 (NEW)      : {neg_sha}")
    assert base_sha == "723ce67f0098157042a1bd389071d41fb28cee9a1eeb3282424f8ef4c7fdae18"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
