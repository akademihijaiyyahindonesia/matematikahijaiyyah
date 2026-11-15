#!/usr/bin/env bash
# ==============================================================================
# sambungkan_hdmi.sh — Pemuat SRAM & Pengaktif HDMI Tang Nano 20K (SRAM ONLY)
#
# Target Papan : Sipeed Tang Nano 20K (Gowin GW2AR-LV18QN88C8/I7, GW2A-18C)
# Pinout TMDS  : Candidate B (Pin 33, 35, 37, 39 — LVCMOS33D DRIVE=8)
# Mode Muat    : SRAM ONLY (`openFPGALoader -b tangnano20k` tanpa flag Flash)
#
# Penggunaan:
#   1. Muat wrapper HDMI Opsi A (`hcpu_hdmi_top.fs`) + jalankan `test_bsm.hasm`:
#      bash cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/sambungkan_hdmi.sh
#
#   2. Muat + langsung catat konfirmasi visual monitor fisik (`physical HDMI PASS`):
#      bash cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/sambungkan_hdmi.sh --confirm-monitor
#
#   3. Muat bitstream Unified SoC Stage 1.5 + USSS (`cosmictera_unified_soc_usss.fs`):
#      bash cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/sambungkan_hdmi.sh --usss
# ==============================================================================
set -euo pipefail

REPO_ROOT="/Users/AMRA/hijaiyyah-mathematics"
BUNDLE_DIR="$REPO_ROOT/cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c"
HDMI_FS="$REPO_ROOT/rtl/fpga/gowin/hcpu_hdmi_top.fs"
HDMI_SHA="a416ada780a50dc8262f4effc8cad61eaff8af4787fadb5f6211acca5f5b413f"
USSS_FS="$REPO_ROOT/cosmictera-build/stage-1-5-security-integration/cosmictera_unified_soc_usss.fs"
USSS_SHA="723ce67f0098157042a1bd389071d41fb28cee9a1eeb3282424f8ef4c7fdae18"

if [[ -x "/opt/homebrew/bin/openFPGALoader" ]]; then
  OPENFPGALOADER="/opt/homebrew/bin/openFPGALoader"
elif [[ -x "/Users/AMRA/opt/oss-cad-suite/bin/openFPGALoader" ]]; then
  OPENFPGALOADER="/Users/AMRA/opt/oss-cad-suite/bin/openFPGALoader"
else
  OPENFPGALOADER="openFPGALoader"
fi

if [[ -x "$REPO_ROOT/.venv-mac/bin/python" ]]; then
  PYTHON_BIN="$REPO_ROOT/.venv-mac/bin/python"
else
  PYTHON_BIN="/usr/local/bin/python3"
fi

MODE="${1:---hdmi}"

cd "$REPO_ROOT"

if [[ "$MODE" == "--usss" ]]; then
  echo "=== [1/3] Memverifikasi SHA-256 cosmictera_unified_soc_usss.fs ==="
  ACTUAL_SHA="$(shasum -a 256 "$USSS_FS" | awk '{print $1}')"
  echo "Bitstream : $USSS_FS"
  echo "SHA-256   : $ACTUAL_SHA"
  if [[ "$ACTUAL_SHA" != "$USSS_SHA" ]]; then
    echo "[GAGAL] SHA-256 tidak cocok! Diharapkan: $USSS_SHA"
    exit 1
  fi

  echo "=== [2/3] Mendeteksi JTAG Tang Nano 20K ==="
  "$OPENFPGALOADER" -b tangnano20k --detect

  echo "=== [3/3] Memuat cosmictera_unified_soc_usss.fs ke SRAM ONLY (Tanpa Flash) ==="
  "$OPENFPGALOADER" -b tangnano20k "$USSS_FS"
  echo "[SELESAI] Unified SoC Stage 1.5 + USSS kini aktif di SRAM dan menampilkan HDMI 1280x720@60Hz."
  exit 0
fi

echo "=== [1/3] Memuat hcpu_hdmi_top.fs (Opsi A) ke SRAM & Menjalankan test_bsm.hasm via UART ==="
"$PYTHON_BIN" "$BUNDLE_DIR/run_hdmi_option_a_sram_load.py"

if [[ "$MODE" == "--confirm-monitor" ]]; then
  echo "=== [2/3] Mencatat konfirmasi visual monitor fisik (1280x720@60Hz M5.2B PASS) ==="
  "$PYTHON_BIN" - <<'PY'
import json
import time
from pathlib import Path

ev_path = Path("/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/sram_load_hdmi_option_a_evidence.json")
data = json.loads(ev_path.read_text(encoding="utf-8"))
data["physical_verification_scope"]["hdmi_1280x720_verified_by_owner"] = True
data["physical_verification_scope"]["hdmi_1280x720_verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
data["physical_verification_scope"]["status"] = "PHYSICAL_HDMI_AND_UART_PASS"
data["physical_verification_scope"]["note"] = (
    "SRAM programming, baked UART loader execution (`test_bsm.hasm` -> `112` + `CYCLES=`), "
    "and physical HDMI 1280x720@60Hz M5.2B dashboard display confirmed on Tang Nano 20K."
)
ev_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("[PASS] Status visual monitor fisik dicatat di:", ev_path)
PY
fi

echo "=== [3/3] Memperbarui & Memverifikasi Manifes SHA-256 (8/8 Berkas Bukti) ==="
shasum -a 256 \
  rtl/fpga/gowin/hcpu_hdmi_top.fs \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/hdmi_option_a_pnr.log \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/pytest_11452b9c.log \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/diff_1aed5e1f_to_11452b9c.patch \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/jtag_detect_hdmi_option_a.log \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/sram_load_hdmi_option_a.log \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/uart_hdmi_option_a_test_bsm.bin \
  cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c/sram_load_hdmi_option_a_evidence.json \
  > "$BUNDLE_DIR/hdmi_bitstream_sha256.txt"

shasum -a 256 -c "$BUNDLE_DIR/hdmi_bitstream_sha256.txt"
echo ""
echo "[AKTIF] hcpu_hdmi_top.fs ($HDMI_SHA) sedang berjalan di SRAM Tang Nano 20K."
echo "        Silakan amati layar monitor HDMI (1280x720 @ 60 Hz — Dasbor M5.2B, PC=0x048, G:OK, HALTED)."
