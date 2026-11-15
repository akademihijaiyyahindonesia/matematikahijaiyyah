#!/usr/bin/env python3
"""
COSMICTERA CT-01-REV13 — Physical Silicon Negative & Recovery Security Test Runner
Target   : Tang Nano 20K (`GW2AR-LV18QN88C8/I7`)
Mode     : SRAM ONLY (`/opt/homebrew/bin/openFPGALoader -b tangnano20k` without `-f`)
Safety   :
  - External Flash is NEVER programmed or erased.
  - Baseline `cosmictera_unified_soc_usss.fs` (`723ce67f...`) is preserved untouched.
  - Executes `cosmictera_unified_soc_usss_negtest.fs` (which has 100% identical
    placement, routing, LUTs, and timing as `723ce67f...`, with only BSRAM `imem`
    initialized to `usss_negative_silicon_suite.hasm`).
  - Captures live UART verdicts for all 8 Negative & Recovery Security Scenarios
    and verifies each against the expected hardware `SEC_STATUS` and `SEC_REASON`.
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

USSS_DIR = Path("/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-security-integration")
BASE_FS = USSS_DIR / "cosmictera_unified_soc_usss.fs"
EXPECTED_BASE_SHA256 = "723ce67f0098157042a1bd389071d41fb28cee9a1eeb3282424f8ef4c7fdae18"
NEGTEST_FS = USSS_DIR / "cosmictera_unified_soc_usss_negtest.fs"
LOG_DIR = USSS_DIR / "logs"

CANDIDATE_LOADERS = [
    "/opt/homebrew/bin/openFPGALoader",
    "/Users/AMRA/opt/oss-cad-suite/bin/openFPGALoader",
]
UART_DEV = "/dev/cu.usbserial-20250303171"

EXPECTED_SCENARIOS = [
    ("S0_POWER_ON_BIST_AUTH_OK", 6, 1),
    ("S1_HMAC_TAG_MISMATCH_REJECT", 10, 16),
    ("S2_TIMESTAMP_EXPIRED_REJECT", 10, 52),
    ("S3_NONCE_REUSED_REJECT", 10, 52),
    ("S4_UNAUTHORIZED_PORT_REJECT", 10, 128),
    ("S5_OUT_OF_ALPHABET_SYMBOL_REJECT", 26, 112),
    ("S6_KEY_UNPROVISIONED_BLOCKED_ERROR", 26, 24),
    ("S7_SECURITY_ABORT_HALTS_KABAH", 26, 304),
    ("S8_VALID_REQUEST_AFTER_FAULT_AUTH_OK", 6, 1),
]


def resolve_loader() -> str:
    for path in CANDIDATE_LOADERS:
        if os.path.exists(path):
            return path
    return CANDIDATE_LOADERS[0]


def open_uart_raw(dev_path: str) -> int:
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


def read_uart_window(fd: int, duration_sec: float = 2.5) -> bytes:
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
    print("=== [USSS NEGATIVE & RECOVERY SILICON VALIDATION — SRAM ONLY] ===")
    base_sha = hashlib.sha256(BASE_FS.read_bytes()).hexdigest()
    if base_sha != EXPECTED_BASE_SHA256:
        print(f"ERROR: Baseline bitstream SHA-256 changed! {base_sha}")
        return 1
    print(f"[PASS] Baseline cosmictera_unified_soc_usss.fs untouched ({base_sha}).")

    if not NEGTEST_FS.exists():
        print("Building cosmictera_unified_soc_usss_negtest.fs first...")
        subprocess.run(
            [sys.executable, str(USSS_DIR / "scripts" / "build_and_sim_usss_negtest.py")],
            check=True,
        )

    neg_sha = hashlib.sha256(NEGTEST_FS.read_bytes()).hexdigest()
    print(f"Negtest Bitstream : {NEGTEST_FS}")
    print(f"Negtest SHA-256   : {neg_sha}")

    loader = resolve_loader()
    fd = open_uart_raw(UART_DEV)
    try:
        t0 = time.monotonic()
        proc = subprocess.run(
            [loader, "-b", "tangnano20k", str(NEGTEST_FS)],
            capture_output=True,
            text=True,
            check=False,
        )
        load_out = (proc.stdout or "") + (proc.stderr or "")
        (LOG_DIR / "sram_load_usss_negtest.log").write_text(load_out, encoding="utf-8")
        print(load_out.strip())
        if proc.returncode != 0:
            print("ERROR: SRAM load failed.")
            return 2
        uart_data = read_uart_window(fd, duration_sec=2.5)
        elapsed = time.monotonic() - t0
    finally:
        os.close(fd)

    bin_path = LOG_DIR / "uart_usss_negtest.bin"
    bin_path.write_bytes(uart_data)
    uart_sha = hashlib.sha256(uart_data).hexdigest()
    text = uart_data.decode("ascii", errors="replace")
    lines = [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]

    print(f"\nElapsed     : {elapsed:.3f} s")
    print(f"UART Bytes  : {len(uart_data)} bytes (SHA-256: {uart_sha})")
    print(f"UART Lines  : {lines}")

    num_lines = [int(x) for x in lines if x.isdigit()]
    scenarios_out = {}
    all_pass = True

    if len(num_lines) >= 20:
        for idx, (name, exp_status, exp_reason) in enumerate(EXPECTED_SCENARIOS):
            got_status = num_lines[2 * idx]
            got_reason = num_lines[2 * idx + 1]
            ok = (got_status == exp_status) and (got_reason == exp_reason)
            if not ok:
                all_pass = False
            scenarios_out[name] = {
                "status_bits_4_0": got_status,
                "expected_status": exp_status,
                "reason_mask": got_reason,
                "expected_reason": exp_reason,
                "pass": ok,
            }
            tag = "PASS" if ok else "FAIL"
            print(f"  [{tag}] {name}: status={got_status} (exp {exp_status}), reason=0x{got_reason:03X} (exp 0x{exp_reason:03X})")

        tot_req = num_lines[18]
        tot_fail = num_lines[19]
        cnt_ok = (tot_req == 9) and (tot_fail == 7)
        if not cnt_ok:
            all_pass = False
        print(f"  [{'PASS' if cnt_ok else 'FAIL'}] TOTAL_REQ={tot_req} (exp 9), TOTAL_FAIL={tot_fail} (exp 7)")
    else:
        all_pass = False
        print(f"[WARN] Expected 20 numeric lines, got {len(num_lines)}: {num_lines}")

    evidence = {
        "baseline_bitstream_sha256": base_sha,
        "negtest_bitstream": str(NEGTEST_FS),
        "negtest_bitstream_sha256": neg_sha,
        "mode": "SRAM_ONLY",
        "elapsed_sec": round(elapsed, 3),
        "uart_bytes": len(uart_data),
        "uart_sha256": uart_sha,
        "uart_hex": " ".join(f"{b:02X}" for b in uart_data),
        "uart_lines": lines,
        "scenarios": scenarios_out,
        "all_pass": all_pass,
    }
    ev_path = LOG_DIR / "sram_load_usss_negtest_evidence.json"
    ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved silicon negative-test evidence to: {ev_path}")
    print("On HDMI Monitor Row 83, verify live display now shows:")
    print("  USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:09 FL:07 R:0")
    return 0 if all_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
