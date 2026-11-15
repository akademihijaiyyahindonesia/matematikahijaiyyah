#!/usr/bin/env bash
# ============================================================================
# run_stage1_4_pnr_and_sram_load.sh — COSMICTERA CT-01-REV13 Stage 1.4
# Place & Route, Bitstream Generation, and Tang Nano 20K SRAM Validation
#
# Target Device : Gowin GW2AR-LV18QN88C8/I7 (family=GW2A-18C)
# Constraints   : Candidate B (/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst)
#                 Single-ended P-only pins 33, 35, 37, 39 with IO_TYPE=LVCMOS33D DRIVE=8
# Output Files  : Dedicated `_stage1_4` filenames (NEVER overwrites Stage 1.3 artifacts):
#                 - cosmictera_boot_top_stage1_4_pnr.json
#                 - nextpnr_stage1_4_pnr.log
#                 - cosmictera_boot_top_stage1_4.fs
#                 - sram_load_stage1_4.log
# Programmer    : openFPGALoader -b tangnano20k (SRAM Mode ONLY — NO Flash erase/write)
# ============================================================================
set -euo pipefail

WORK_DIR="/tmp/stage1_2_cosmictera_boot_ui"
CST_FILE="/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst"
NETLIST_IN="$WORK_DIR/cosmictera_boot_top_stage1_4.json"
PNR_JSON_OUT="$WORK_DIR/cosmictera_boot_top_stage1_4_pnr.json"
PNR_LOG_OUT="$WORK_DIR/nextpnr_stage1_4_pnr.log"
FS_OUT="$WORK_DIR/cosmictera_boot_top_stage1_4.fs"
SRAM_LOG_OUT="$WORK_DIR/sram_load_stage1_4.log"

NEXTPNR_BIN="/Users/AMRA/opt/oss-cad-suite/bin/nextpnr-himbaechel"
GOWIN_PACK_BIN="/Users/AMRA/hijaiyyah-mathematics/.venv-mac/bin/gowin_pack"
OPENFPGALOADER_BIN="/opt/homebrew/bin/openFPGALoader"

cd "$WORK_DIR"

echo "=== [PRE-FLIGHT] Verifying Stage 1.4 Source, Netlist & CST SHA-256 ==="
shasum -a 256 \
  "$WORK_DIR/rtl/cosmictera_boot_top.v" \
  "$WORK_DIR/rtl/cosmictera_boot_subsys_bridge.v" \
  "$WORK_DIR/rtl/cosmictera_boot_compositor.v" \
  "$WORK_DIR/rtl/cosmictera_boot_text_rom.v" \
  "$WORK_DIR/rtl/boot_text_rom.hex" \
  "$NETLIST_IN" \
  "$CST_FILE"

echo "=== [1/3] Running Stage 1.4 Place & Route (GW2AR-LV18QN88C8/I7, 74.25 MHz) ==="
"$NEXTPNR_BIN" \
  --json "$NETLIST_IN" \
  --write "$PNR_JSON_OUT" \
  --device GW2AR-LV18QN88C8/I7 \
  --vopt family=GW2A-18C \
  --vopt cst="$CST_FILE" \
  --freq 74.25 \
  --timing-allow-fail > "$PNR_LOG_OUT" 2>&1

echo "=== [P&R SUMMARY] ==="
grep -E "Device utilisation|SLICE|RAMW|BSRAM|OSER10|CLKDIV|rPLL|Max frequency|critical path|Programmed|0 errors" -B 1 -A 6 "$PNR_LOG_OUT" || tail -n 35 "$PNR_LOG_OUT"

echo "=== [2/3] Packing Stage 1.4 Bitstream cosmictera_boot_top_stage1_4.fs (GW2A-18C) ==="
"$GOWIN_PACK_BIN" \
  -d GW2A-18C \
  -o "$FS_OUT" \
  "$PNR_JSON_OUT"

echo "=== [BITSTREAM SHA-256] ==="
shasum -a 256 "$FS_OUT"

if [[ "${1:-}" == "--load-sram" ]]; then
  echo "=== [3/3] Detecting Tang Nano 20K & Programming SRAM ONLY (NO FLASH) ==="
  "$OPENFPGALOADER_BIN" -b tangnano20k --detect
  "$OPENFPGALOADER_BIN" -b tangnano20k "$FS_OUT" 2>&1 | tee "$SRAM_LOG_OUT"
else
  echo "=== [3/3] Stage 1.4 Bitstream ready at $FS_OUT. Pass --load-sram to program SRAM. ==="
fi
