#!/usr/bin/env python3
"""
COSMICTERA CT-01-REV13 — Stage 1.5 + USSS Physical SRAM Loader & Audit Harness (Run 2)
Target   : Tang Nano 20K (Gowin GW2AR-LV18QN88C8/I7, family=GW2A-18C)
Mode     : SRAM ONLY (`openFPGALoader -b tangnano20k` without `-f` / `--write-flash`)
Safety   : External Flash is NEVER programmed or erased. Run 1 artifacts are preserved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import subprocess
import sys
import termios
import time
from pathlib import Path

USSS_DIR = Path("/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-security-integration")
LOGS_DIR = USSS_DIR / "logs"
FS_PATH = USSS_DIR / "cosmictera_unified_soc_usss.fs"
NEXTPNR_LOG_PATH = LOGS_DIR / "nextpnr_unified_soc_usss.log"
EXPECTED_FS_SHA256 = "723ce67f0098157042a1bd389071d41fb28cee9a1eeb3282424f8ef4c7fdae18"

GOLDEN_WIRE_23_BYTES = bytes.fromhex("3131320a0a4359434c45533d30303030314238390d0a0a")
GOLDEN_WIRE_23_HEX = " ".join(f"{b:02X}" for b in GOLDEN_WIRE_23_BYTES)
GOLDEN_WIRE_23_SHA256 = hashlib.sha256(GOLDEN_WIRE_23_BYTES).hexdigest()

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


def open_uart_raw(dev_path: str) -> int | None:
    if not os.path.exists(dev_path):
        return None
    try:
        fd = os.open(dev_path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = termios.B115200
        attrs[5] = termios.B115200
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
    except OSError:
        return None


def read_uart_window(fd: int | None, duration_sec: float = 2.0) -> bytes:
    if fd is None:
        return b""
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


def parse_nextpnr_timing(log_path: Path) -> dict[str, object]:
    if not log_path.exists():
        return {"available": False}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    sha256 = hashlib.sha256(log_path.read_bytes()).hexdigest()
    fmax_lines = re.findall(r"Info: Max frequency for clock .*", text)
    return {
        "available": True,
        "log_path": str(log_path),
        "log_sha256": sha256,
        "fmax_report_lines": fmax_lines,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="COSMICTERA Stage 1.5 + USSS SRAM Loader & Audit Harness")
    parser.add_argument("--run-id", default="run2", help="Run identifier (default: run2, preserves Run 1 logs)")
    parser.add_argument("--uart-window", type=float, default=2.0, help="UART capture duration in seconds (default: 2.0)")
    args = parser.parse_args()

    run_tag = args.run_id.strip()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t_total_start = time.monotonic()

    print(f"=== [COSMICTERA STAGE 1.5 + USSS — SRAM & UART VALIDATION ({run_tag.upper()})] ===")

    # 1. Bitstream Identity Verification
    if not FS_PATH.exists():
        print(f"[FAIL] Bitstream file not found: {FS_PATH}")
        return 1
    fs_bytes = FS_PATH.read_bytes()
    actual_sha = hashlib.sha256(fs_bytes).hexdigest()
    fs_size = len(fs_bytes)
    print(f"Bitstream : {FS_PATH} ({fs_size} bytes)")
    print(f"SHA-256   : {actual_sha}")
    if actual_sha != EXPECTED_FS_SHA256:
        print(f"[FAIL] Bitstream SHA-256 mismatch! Expected {EXPECTED_FS_SHA256}")
        return 1
    print("[PASS] Bitstream SHA-256 verified against USSS manifest.")

    loader = resolve_loader()
    jtag_cmd = [loader, "-b", "tangnano20k", "--detect"]
    sram_cmd = [loader, "-b", "tangnano20k", str(FS_PATH)]
    forbidden_flags = {"-f", "--write-flash", "--external-flash"}
    has_flash_flag = any(flag in forbidden_flags for flag in sram_cmd)
    if has_flash_flag:
        print("[FAIL] Safety violation: Flash programming flag detected!")
        return 1
    print(f"Programmer: {loader} (SRAM ONLY — 0 flash flags)")

    # 2. JTAG Detection (measured separately)
    t_jtag0 = time.monotonic()
    det = subprocess.run(jtag_cmd, capture_output=True, text=True, check=False)
    jtag_elapsed_sec = time.monotonic() - t_jtag0
    det_out = (det.stdout or "") + (det.stderr or "")
    jtag_log_path = LOGS_DIR / f"jtag_detect_usss_{run_tag}.log"
    jtag_log_path.write_text(det_out, encoding="utf-8")
    print(det_out.strip())
    if det.returncode != 0:
        print(f"[FAIL] JTAG detection failed (returncode={det.returncode}).")
        return 2
    print(f"[PASS] JTAG detection completed in {jtag_elapsed_sec:.3f} s.")

    # 3. SRAM Programming (measured separately from UART capture window)
    fd = open_uart_raw(UART_DEV)
    if fd is None:
        print(f"[WARN] UART device {UART_DEV} could not be opened prior to SRAM load.")

    try:
        t_prog0 = time.monotonic()
        proc = subprocess.run(sram_cmd, capture_output=True, text=True, check=False)
        programming_elapsed_sec = time.monotonic() - t_prog0
        load_out = (proc.stdout or "") + (proc.stderr or "")
        sram_log_path = LOGS_DIR / f"sram_load_usss_{run_tag}.log"
        sram_log_path.write_text(load_out, encoding="utf-8")
        print(load_out.strip())
        if proc.returncode != 0:
            print(f"[FAIL] Bitstream programming to SRAM failed (returncode={proc.returncode}).")
            return 3
        print(f"[PASS] Bitstream programming to SRAM completed in {programming_elapsed_sec:.3f} s.")

        # 4. UART Capture Window (measured separately)
        t_uart0 = time.monotonic()
        uart_data = read_uart_window(fd, duration_sec=args.uart_window)
        uart_capture_elapsed_sec = time.monotonic() - t_uart0
    finally:
        if fd is not None:
            os.close(fd)

    total_elapsed_sec = time.monotonic() - t_total_start

    bin_path = LOGS_DIR / f"uart_usss_{run_tag}.bin"
    bin_path.write_bytes(uart_data)
    uart_sha256 = hashlib.sha256(uart_data).hexdigest()
    hex_spaced = " ".join(f"{b:02X}" for b in uart_data)
    uart_matches_golden = uart_data == GOLDEN_WIRE_23_BYTES

    print(f"Programming Elapsed : {programming_elapsed_sec:.3f} s")
    print(f"UART Capture Window : {uart_capture_elapsed_sec:.3f} s")
    print(f"Total Elapsed       : {total_elapsed_sec:.3f} s")
    print(f"UART Bytes          : {len(uart_data)} bytes")
    print(f"UART Hex            : {hex_spaced}")
    print(f"Golden Hex (23B)    : {GOLDEN_WIRE_23_HEX}")
    print(f"UART ASCII          : {uart_data!r}")

    if uart_matches_golden:
        print("[PASS] UART matches golden 23-byte reference.")
    else:
        print("[FAIL] UART does not match golden reference.")

    print("[INFO] Physical HDMI 1280x720@60Hz display, USSS Row 83 status, and S1/S2 button")
    print("       interactions are NOT verified by this script and require separate physical monitor evidence.")

    timing_info = parse_nextpnr_timing(NEXTPNR_LOG_PATH)

    evidence = {
        "run_id": run_tag,
        "bitstream_identity": {
            "bitstream": str(FS_PATH),
            "size_bytes": fs_size,
            "bitstream_sha256": actual_sha,
            "expected_sha256": EXPECTED_FS_SHA256,
            "sha256_match": actual_sha == EXPECTED_FS_SHA256,
        },
        "jtag_detection": {
            "command": jtag_cmd,
            "returncode": det.returncode,
            "jtag_detect_elapsed_sec": round(jtag_elapsed_sec, 3),
            "log_path": str(jtag_log_path),
            "log_sha256": hashlib.sha256(jtag_log_path.read_bytes()).hexdigest(),
        },
        "sram_programming": {
            "programmer": loader,
            "command": sram_cmd,
            "mode": "SRAM_ONLY",
            "flash_flags_present": has_flash_flag,
            "returncode": proc.returncode,
            "programming_elapsed_sec": round(programming_elapsed_sec, 3),
            "log_path": str(sram_log_path),
            "log_sha256": hashlib.sha256(sram_log_path.read_bytes()).hexdigest(),
            "status": "PASS",
        },
        "uart_validation": {
            "device": UART_DEV,
            "uart_capture_elapsed_sec": round(uart_capture_elapsed_sec, 3),
            "raw_bin_path": str(bin_path),
            "raw_sha256": uart_sha256,
            "uart_bytes": len(uart_data),
            "uart_hex": hex_spaced,
            "uart_ascii": repr(uart_data),
            "expected_golden_bytes": 23,
            "expected_golden_hex": GOLDEN_WIRE_23_HEX,
            "expected_golden_sha256": GOLDEN_WIRE_23_SHA256,
            "uart_match_golden_t25": uart_matches_golden,
            "status": "PASS" if uart_matches_golden else "FAIL",
        },
        "timing_summary": {
            "jtag_detect_elapsed_sec": round(jtag_elapsed_sec, 3),
            "programming_elapsed_sec": round(programming_elapsed_sec, 3),
            "uart_capture_elapsed_sec": round(uart_capture_elapsed_sec, 3),
            "total_elapsed_sec": round(total_elapsed_sec, 3),
        },
        "static_timing_report_evidence": timing_info,
        "physical_verification_scope": {
            "sram_load_verified_by_script": True,
            "uart_23b_verified_by_script": uart_matches_golden,
            "hdmi_1280x720_verified_by_script": False,
            "usss_row83_verified_by_script": False,
            "buttons_s1_s2_verified_by_script": False,
            "note": (
                "UART output (23 bytes: 112 and CYCLES=00001B89) only verifies HCPU execution and UART TX. "
                "HDMI 1280x720@60Hz, Row 83 USSS panel, and S1/S2 buttons require separate physical visual evidence."
            ),
        },
    }

    evidence_path = LOGS_DIR / f"sram_load_usss_{run_tag}_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence JSON saved to: {evidence_path}")

    return 0 if uart_matches_golden else 4


if __name__ == "__main__":
    sys.exit(main())
