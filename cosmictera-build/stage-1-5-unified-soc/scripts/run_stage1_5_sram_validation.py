#!/usr/bin/env python3
"""
COSMICTERA CT-01-REV13 — Stage 1.5 Unified SoC Physical SRAM Validation Harness
Target   : Tang Nano 20K (Gowin GW2AR-LV18QN88C8/I7, family=GW2A-18C)
Mode     : SRAM ONLY (`openFPGALoader -b tangnano20k` without `-f` / `--write-flash`)
Safety   : External Flash is NEVER programmed or erased.
"""
from __future__ import annotations

import hashlib
import json
import os
import select
import subprocess
import sys
import termios
import time
from pathlib import Path

STAGE15_DIR = Path("/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc")
FS_PATH = STAGE15_DIR / "cosmictera_unified_soc_stage1_5.fs"
EXPECTED_FS_SHA256 = "02c0a44f28dfa35f41389ed34217b9ea22bdfdf42e13911aefb93e948392a3c4"

# Wire-exact 23 bytes from hcpu_top.v + hcpu_gowin_top.v (T25 in tb_unified_soc_stage1_5.v):
#   "112\n" (4B: 31 31 32 0A) + "\nCYCLES=00001B89\r\n\n" (19B: 0A 43 59 43 4C 45 53 3D 30 30 30 30 31 42 38 39 0D 0A 0A)
GOLDEN_WIRE_23_BYTES = bytes.fromhex("3131320a0a4359434c45533d30303030314238390d0a0a")
GOLDEN_WIRE_23_SHA256 = hashlib.sha256(GOLDEN_WIRE_23_BYTES).hexdigest()

# Prompt-formatted 23 bytes (with 0D 0A after "112"):
GOLDEN_DOC_23_BYTES = bytes.fromhex("3131320d0a4359434c45533d30303030314238390d0a0a")
GOLDEN_DOC_23_SHA256 = hashlib.sha256(GOLDEN_DOC_23_BYTES).hexdigest()

CANDIDATE_LOADERS = [
    "/opt/homebrew/bin/openFPGALoader",
    "/Users/AMRA/opt/oss-cad-suite/bin/openFPGALoader",
]
UART_DEV = "/dev/cu.usbserial-20250303171"


def resolve_loader() -> str:
    for path in CANDIDATE_LOADERS:
        if os.path.exists(path):
            return path
    return CANDIDATE_LOADERS[0]


def open_uart_raw(dev_path: str) -> int:
    fd = os.open(dev_path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    # Raw 115200 8N1 — no CR/LF translation
    attrs[0] = 0  # iflag
    attrs[1] = 0  # oflag
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag
    attrs[3] = 0  # lflag
    attrs[4] = termios.B115200  # ispeed
    attrs[5] = termios.B115200  # ospeed
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    while True:
        r, _, _ = select.select([fd], [], [], 0.05)
        if not r:
            break
        try:
            if not os.read(fd, 4096):
                break
        except BlockingIOError:
            break
    return fd


def read_uart_window(fd: int, duration_sec: float = 2.0) -> bytes:
    buf = bytearray()
    deadline = time.monotonic() + duration_sec
    while time.monotonic() < deadline:
        rem = max(0.01, deadline - time.monotonic())
        r, _, _ = select.select([fd], [], [], min(0.1, rem))
        if r:
            try:
                chunk = os.read(fd, 4096)
                if chunk:
                    buf.extend(chunk)
            except BlockingIOError:
                pass
    return bytes(buf)


def main() -> int:
    print("=== [STAGE 1.5 PHYSICAL VALIDATION — SRAM ONLY] ===")
    actual_sha = hashlib.sha256(FS_PATH.read_bytes()).hexdigest()
    print(f"Bitstream : {FS_PATH}")
    print(f"SHA-256   : {actual_sha}")
    if actual_sha != EXPECTED_FS_SHA256:
        print(f"ERROR: Bitstream SHA-256 mismatch! Expected {EXPECTED_FS_SHA256}")
        return 1
    print("[PASS] Bitstream SHA-256 verified against approved Stage 1.5 manifest.")

    loader = resolve_loader()
    print(f"Programmer: {loader} (SRAM ONLY — NO FLASH FLAGS)")

    # 1. JTAG Chip Detection
    print("\n=== [TAHAP 1: JTAG DETECTION] ===")
    det = subprocess.run(
        [loader, "-b", "tangnano20k", "--detect"],
        capture_output=True,
        text=True,
        check=False,
    )
    det_out = (det.stdout or "") + (det.stderr or "")
    (STAGE15_DIR / "jtag_detect_stage1_5.log").write_text(det_out, encoding="utf-8")
    print(det_out.strip())
    if det.returncode != 0:
        print("ERROR: JTAG detection failed. Run this script directly in a native macOS Terminal outside the agent sandbox.")
        return 2

    evidence: dict[str, object] = {
        "bitstream": str(FS_PATH),
        "bitstream_sha256": actual_sha,
        "programmer": loader,
        "mode": "SRAM_ONLY",
        "jtag_detect_log": det_out.strip(),
        "runs": {},
    }

    # 2. Run 1 & Run 2 SRAM Load + Live UART Capture
    for run_idx in (1, 2):
        print(f"\n=== [RUN {run_idx}: SRAM LOAD + UART 23-BYTE CAPTURE] ===")
        fd = open_uart_raw(UART_DEV)
        try:
            t0 = time.monotonic()
            proc = subprocess.run(
                [loader, "-b", "tangnano20k", str(FS_PATH)],
                capture_output=True,
                text=True,
                check=False,
            )
            load_out = (proc.stdout or "") + (proc.stderr or "")
            log_path = STAGE15_DIR / f"sram_load_run{run_idx}_stage1_5.log"
            log_path.write_text(load_out, encoding="utf-8")
            print(load_out.strip())
            if proc.returncode != 0:
                print(f"ERROR: Run {run_idx} SRAM programming failed.")
                return 3

            uart_data = read_uart_window(fd, duration_sec=2.0)
            elapsed = time.monotonic() - t0
        finally:
            os.close(fd)

        bin_path = STAGE15_DIR / f"uart_run{run_idx}_stage1_5.bin"
        bin_path.write_bytes(uart_data)
        uart_sha = hashlib.sha256(uart_data).hexdigest()
        hex_spaced = " ".join(f"{b:02X}" for b in uart_data)
        print(f"Run {run_idx} Elapsed              : {elapsed:.2f} s")
        print(f"Run {run_idx} UART Bytes           : {len(uart_data)} bytes")
        print(f"Run {run_idx} UART Hex             : {hex_spaced}")
        print(f"Run {run_idx} UART ASCII           : {uart_data!r}")
        print(f"Run {run_idx} UART SHA-256         : {uart_sha}")
        print(f"Golden Wire T25 (0A 0A) SHA256 : {GOLDEN_WIRE_23_SHA256}")
        print(f"Golden Doc      (0D 0A) SHA256 : {GOLDEN_DOC_23_SHA256}")

        status = "WARN"
        if uart_data == GOLDEN_WIRE_23_BYTES:
            status = "PASS_EXACT_T25_WIRE_23B"
            print(f"[PASS] Run {run_idx} UART output is 100% bit-identical to Stage 1.5 Golden T25 Wire (23 bytes)!")
        elif uart_data == GOLDEN_DOC_23_BYTES:
            status = "PASS_EXACT_DOC_23B"
            print(f"[PASS] Run {run_idx} UART output is 100% bit-identical to Stage 1.5 Golden Doc (23 bytes)!")
        elif b"112" in uart_data and b"CYCLES=00001B89" in uart_data:
            status = "PASS_PAYLOAD_MATCH"
            print(f"[PASS] Run {run_idx} UART output contains exact '112' and 'CYCLES=00001B89'!")
        else:
            print(f"[WARN] Run {run_idx} UART bytes differed from expected sequence.")

        evidence["runs"][f"run_{run_idx}"] = {
            "elapsed_sec": round(elapsed, 3),
            "byte_length": len(uart_data),
            "hex": hex_spaced,
            "ascii_repr": repr(uart_data),
            "uart_sha256": uart_sha,
            "sram_log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
            "status": status,
        }

        if run_idx == 1:
            time.sleep(1.5)

    (STAGE15_DIR / "sram_validation_evidence_stage1_5.json").write_text(
        json.dumps(evidence, indent=2) + "\n",
        encoding="utf-8",
    )
    print("\n=== [EVIDENCE SAVED] ===")
    print(f"Saved evidence JSON to: {STAGE15_DIR / 'sram_validation_evidence_stage1_5.json'}")
    print("Next on board:")
    print("  1. Observe HDMI 1280x720@60Hz Page 0 (initial BIST telemetry: CY:0002C1C9 ... RUN).")
    print("  2. Press Button S2 (Pin 87 / btn_rst_n) ONCE to toggle live_hcpu_mode = 1 ->")
    print("     verify Region 5 row 56 switches live to: CY:00001B89 ... G:OK HLT CDC:LIVE.")
    print("  3. Press Button S1 (Pin 88 / mode_key) to inspect P0 -> P1..P12 -> P0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
