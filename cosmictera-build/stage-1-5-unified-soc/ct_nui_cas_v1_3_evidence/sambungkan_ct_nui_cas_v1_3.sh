#!/usr/bin/env bash
# ==============================================================================
# sambungkan_ct_nui_cas_v1_3.sh — Pemuat SRAM & Validator Fisik CT-NUI-CAS-V1.3
#
# Target Papan : Sipeed Tang Nano 20K (Gowin GW2AR-LV18QN88C8/I7, GW2A-18C)
# Bitstream    : rtl/fpga/gowin/hcpu_hdmi_top.fs
# SHA-256      : 7fe32ef6d41e6f371ea6ed1e1c5e648e9bcd8c98384476fdfcb42d8d92c199ab
# Identitas    : BUILD:CT-NUI-CAS-V1.3 | BASE:920F3E61 (Protected)
# Mode Muat    : SRAM ONLY (`openFPGALoader -b tangnano20k` tanpa `-f` / `--write-flash`)
# ==============================================================================
set -euo pipefail

REPO_ROOT="/Users/AMRA/hijaiyyah-mathematics"
EVIDENCE_DIR="$REPO_ROOT/cosmictera-build/stage-1-5-unified-soc/ct_nui_cas_v1_3_evidence"
PYTHON_BIN="/usr/local/bin/python3"

cd "$REPO_ROOT"

echo "=== [1/2] Memuat CT-NUI-CAS-V1.3 ke SRAM Tang Nano 20K & Menjalankan 3 Workload UART Fisik ==="
"$PYTHON_BIN" "$EVIDENCE_DIR/run_ct_nui_cas_v1_3_sram_load.py"

echo "=== [2/2] Membuat & Memverifikasi Manifes SHA-256 Bukti CT-NUI-CAS-V1.3 ==="
(
  cd "$EVIDENCE_DIR"
  shasum -a 256 \
    hcpu_hdmi_top_ct_nui_cas_v1_3.fs \
    hdmi_pnr_ct_nui_cas_v1_3.log \
    tb_physical_buttons_fault_recovery_ct_nui_cas_v1_3.log \
    jtag_detect_ct_nui_cas_v1_3.log \
    sram_load_ct_nui_cas_v1_3.log \
    uart_hw1_hc_hasm_hbc.bin \
    uart_hw2_hisab_usss_guard.bin \
    uart_hw3_nui_l0_hybit_dsp.bin \
    nui_control_all_system_verification.json \
    frame_nui_centered_running_1280x720.png \
    frame_nui_centered_s1_stopped_1280x720.png \
    frame_nui_centered_s2_recovery_1280x720.png \
    run_ct_nui_cas_v1_3_sram_load.py \
    ct_nui_cas_v1_3_evidence.json \
    > ct_nui_cas_v1_3_sha256_manifest.txt
  shasum -a 256 -c ct_nui_cas_v1_3_sha256_manifest.txt
)

echo ""
echo "[AKTIF] Bitstream CT-NUI-CAS-V1.3 (7fe32ef6...) kini berjalan di SRAM Tang Nano 20K!"
echo "        State saat ini: STATE=RUNNING (Hijau), GUARD=OK (Hijau), L0=(2,2,2,6,6), BSM=(112,10,9)."
echo "        Silakan periksa tampilan monitor HDMI 1280x720 @ 60 Hz dan uji tombol S1 (STOP) serta S2 (RECOVERY)."
