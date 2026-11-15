#!/usr/bin/env bash
# ============================================================================
# run_stage1_5_build_and_pnr.sh — Reproducible COSMICTERA Stage 1.5 Build & P&R
# Target Device : Tang Nano 20K — Gowin GW2AR-LV18QN88C8/I7 (family=GW2A-18C)
# Baseline      : HEAD = ea3c5b22 (branch `stage-1-5-unified-soc`)
# ============================================================================
set -euo pipefail

STAGE15_DIR="/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc"
REPO_ROOT="/Users/AMRA/hijaiyyah-mathematics"
CAD_BIN="/Users/AMRA/opt/oss-cad-suite/bin"

cd "${STAGE15_DIR}"
echo "[1/5] Generating Stage 1.5 BSRAM ROM initialization tables..."
python3 scripts/build_stage1_5_roms.py

echo "[2/5] Running Unified SoC Stage 1.5 RTL integration testbench (33 tests)..."
cd "${STAGE15_DIR}/rtl"
"${CAD_BIN}/iverilog" -g2012 -I "${REPO_ROOT}/rtl" -I . \
  -o ../tb_unified_soc_stage1_5.vvp \
  tb_unified_soc_stage1_5.v cosmictera_unified_soc_top.v \
  "${REPO_ROOT}/rtl/fpga/gowin/hcpu_gowin_top.v" \
  "${REPO_ROOT}/rtl/hcpu_codex_alu.v" \
  "${REPO_ROOT}/rtl/hcpu_controller.v" \
  "${REPO_ROOT}/rtl/hcpu_dataram.v" \
  "${REPO_ROOT}/rtl/hcpu_decode.v" \
  "${REPO_ROOT}/rtl/hcpu_execute.v" \
  "${REPO_ROOT}/rtl/hcpu_fetch.v" \
  "${REPO_ROOT}/rtl/hcpu_forward.v" \
  "${REPO_ROOT}/rtl/hcpu_guard.v" \
  "${REPO_ROOT}/rtl/hcpu_hisab.v" \
  "${REPO_ROOT}/rtl/hcpu_memory.v" \
  "${REPO_ROOT}/rtl/hcpu_mmio.v" \
  "${REPO_ROOT}/rtl/hcpu_mul.v" \
  "${REPO_ROOT}/rtl/hcpu_regfile.v" \
  "${REPO_ROOT}/rtl/hcpu_rom.v" \
  "${REPO_ROOT}/rtl/hcpu_sdio.v" \
  "${REPO_ROOT}/rtl/hcpu_timer.v" \
  "${REPO_ROOT}/rtl/hcpu_top.v" \
  "${REPO_ROOT}/rtl/hcpu_trap.v" \
  "${REPO_ROOT}/rtl/hcpu_uart_rx.v" \
  "${REPO_ROOT}/rtl/hcpu_uart_tx.v" \
  "${REPO_ROOT}/rtl/hcpu_writeback.v" \
  hcpu_video_timing.v hcpu_page_key.v hcpu_font_rom.v tmds_rpll.v \
  cosmictera_boot_compositor.v cosmictera_boot_events.v cosmictera_boot_logo_rom.v \
  cosmictera_boot_render.v cosmictera_boot_reset_seq.v cosmictera_boot_subsys_bridge.v \
  cosmictera_boot_text_rom.v cosmictera_boot_uptime.v dvi_tx_open.v
"${CAD_BIN}/vvp" ../tb_unified_soc_stage1_5.vvp > ../tb_unified_soc_stage1_5.log 2>&1
grep "=== UNIFIED SOC STAGE 1.5 SUMMARY" ../tb_unified_soc_stage1_5.log

echo "[3/5] Synthesizing and P&R Stage 1.5 Boot Display standalone baseline..."
"${CAD_BIN}/yosys" -p "read_verilog -I ${REPO_ROOT}/rtl -I . cosmictera_boot_top.v hcpu_video_timing.v hcpu_page_key.v hcpu_font_rom.v tmds_rpll.v cosmictera_boot_compositor.v cosmictera_boot_events.v cosmictera_boot_logo_rom.v cosmictera_boot_render.v cosmictera_boot_reset_seq.v cosmictera_boot_subsys_bridge.v cosmictera_boot_text_rom.v cosmictera_boot_uptime.v dvi_tx_open.v; synth_gowin -nodsp -top cosmictera_boot_top -json ../cosmictera_boot_top_stage1_5.json; check" > ../yosys_boot_top_stage1_5.log 2>&1
"${CAD_BIN}/nextpnr-himbaechel" --json ../cosmictera_boot_top_stage1_5.json --write ../cosmictera_boot_top_stage1_5_pnr.json --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst="${REPO_ROOT}/constraints/cosmictera_tangnano20k.cst" > ../nextpnr_boot_top_stage1_5.log 2>&1
"${CAD_BIN}/gowin_pack" -d GW2A-18C -o ../cosmictera_boot_top_stage1_5.fs ../cosmictera_boot_top_stage1_5_pnr.json

echo "[4/5] Synthesizing and P&R Unified SoC Stage 1.5 (hcpu_gowin_core + Boot Display)..."
"${CAD_BIN}/yosys" -p "read_verilog -I ${REPO_ROOT}/rtl -I . cosmictera_unified_soc_top.v ${REPO_ROOT}/rtl/fpga/gowin/hcpu_gowin_top.v ${REPO_ROOT}/rtl/hcpu_codex_alu.v ${REPO_ROOT}/rtl/hcpu_controller.v ${REPO_ROOT}/rtl/hcpu_dataram.v ${REPO_ROOT}/rtl/hcpu_decode.v ${REPO_ROOT}/rtl/hcpu_execute.v ${REPO_ROOT}/rtl/hcpu_fetch.v ${REPO_ROOT}/rtl/hcpu_forward.v ${REPO_ROOT}/rtl/hcpu_guard.v ${REPO_ROOT}/rtl/hcpu_hisab.v ${REPO_ROOT}/rtl/hcpu_memory.v ${REPO_ROOT}/rtl/hcpu_mmio.v ${REPO_ROOT}/rtl/hcpu_mul.v ${REPO_ROOT}/rtl/hcpu_regfile.v ${REPO_ROOT}/rtl/hcpu_rom.v ${REPO_ROOT}/rtl/hcpu_sdio.v ${REPO_ROOT}/rtl/hcpu_timer.v ${REPO_ROOT}/rtl/hcpu_top.v ${REPO_ROOT}/rtl/hcpu_trap.v ${REPO_ROOT}/rtl/hcpu_uart_rx.v ${REPO_ROOT}/rtl/hcpu_uart_tx.v ${REPO_ROOT}/rtl/hcpu_writeback.v hcpu_video_timing.v hcpu_page_key.v hcpu_font_rom.v tmds_rpll.v cosmictera_boot_compositor.v cosmictera_boot_events.v cosmictera_boot_logo_rom.v cosmictera_boot_render.v cosmictera_boot_reset_seq.v cosmictera_boot_subsys_bridge.v cosmictera_boot_text_rom.v cosmictera_boot_uptime.v dvi_tx_open.v; synth_gowin -top cosmictera_unified_soc_top -json ../cosmictera_unified_soc_stage1_5.json; check" > ../yosys_unified_soc_stage1_5.log 2>&1
"${CAD_BIN}/nextpnr-himbaechel" --json ../cosmictera_unified_soc_stage1_5.json --write ../cosmictera_unified_soc_stage1_5_pnr.json --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst=../constraints/cosmictera_unified_soc_stage1_5.cst > ../nextpnr_unified_soc_stage1_5.log 2>&1

echo "[5/5] Packing Unified SoC Stage 1.5 prototype bitstream (offline only — SRAM/Flash NOT programmed)..."
"${CAD_BIN}/gowin_pack" -d GW2A-18C -o ../cosmictera_unified_soc_stage1_5.fs ../cosmictera_unified_soc_stage1_5_pnr.json
echo "DONE."
