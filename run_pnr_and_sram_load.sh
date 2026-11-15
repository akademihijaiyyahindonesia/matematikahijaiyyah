#!/usr/bin/env bash
# ============================================================================
# run_pnr_and_sram_load.sh — Stage 1.3 Place & Route, Bitstream Pack & SRAM Load
#
# Target Device : Gowin GW2AR-LV18QN88C8/I7 (family=GW2A-18C)
# Constraints   : Candidate B (/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst)
#                 Single-ended P-only pins 33, 35, 37, 39 with IO_TYPE=LVCMOS33D DRIVE=8
# Programmer    : openFPGALoader -b tangnano20k (SRAM Mode ONLY — NO Flash erase/write)
# ============================================================================
set -euo pipefail

WORK_DIR="/tmp/stage1_2_cosmictera_boot_ui"
CST_FILE="/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst"
NEXTPNR_BIN="/Users/AMRA/opt/oss-cad-suite/bin/nextpnr-himbaechel"
GOWIN_PACK_BIN="/Users/AMRA/hijaiyyah-mathematics/.venv-mac/bin/gowin_pack"
OPENFPGALOADER_BIN="/opt/homebrew/bin/openFPGALoader"

cd "$WORK_DIR"

echo "=== [PRE-CHECK] Verifying source SHA-256 hashes ==="
shasum -a 256 \
  "$WORK_DIR/rtl/cosmictera_boot_top.v" \
  "$WORK_DIR/rtl/cosmictera_boot_subsys_bridge.v" \
  "$WORK_DIR/rtl/cosmictera_boot_compositor.v" \
  "$WORK_DIR/cosmictera_boot_top.json" \
  "$CST_FILE"

echo "=== [1/3] Running nextpnr-himbaechel Place & Route (GW2AR-LV18QN88C8/I7, 74.25 MHz) ==="
"$NEXTPNR_BIN" \
  --json "$WORK_DIR/cosmictera_boot_top.json" \
  --write "$WORK_DIR/cosmictera_boot_top_pnr.json" \
  --device GW2AR-LV18QN88C8/I7 \
  --vopt family=GW2A-18C \
  --vopt cst="$CST_FILE" \
  --freq 74.25 > "$WORK_DIR/nextpnr_pnr.log" 2>&1

echo "=== [2/3] Packing Gowin bitstream cosmictera_boot_top.fs (GW2A-18C) ==="
"$GOWIN_PACK_BIN" \
  -d GW2A-18C \
  -o "$WORK_DIR/cosmictera_boot_top.fs" \
  "$WORK_DIR/cosmictera_boot_top_pnr.json"

echo "=== [VERIFY] Bitstream SHA-256 ==="
shasum -a 256 "$WORK_DIR/cosmictera_boot_top.fs"

if [[ "${1:-}" == "--load-sram" ]]; then
  echo "=== [3/3] Loading cosmictera_boot_top.fs into Tang Nano 20K SRAM ONLY (NO FLASH) ==="
  "$OPENFPGALOADER_BIN" -b tangnano20k "$WORK_DIR/cosmictera_boot_top.fs" 2>&1 | tee "$WORK_DIR/sram_load_stage1_3.log"
else
  echo "=== [3/3] Bitstream ready. Pass --load-sram to program Tang Nano 20K SRAM. ==="
fi
