#!/usr/bin/env python3
"""
COSMICTERA — Option A Standalone HDMI Wrapper (`hcpu_hdmi_top.fs`) Physical SRAM Loader & Validator
Target   : Tang Nano 20K (Gowin GW2AR-LV18QN88C8/I7, family=GW2A-18C)
Bitstream: rtl/fpga/gowin/hcpu_hdmi_top.fs (loader.hasm baked in)
SHA-256  : a416ada780a50dc8262f4effc8cad61eaff8af4787fadb5f6211acca5f5b413f
Mode     : SRAM ONLY (`openFPGALoader -b tangnano20k` without `-f` / `--write-flash`)
Safety   : External Flash is NEVER programmed or erased.
"""
from __future__ import annotations

import hashlib
import json
import os
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

ROOT = Path("/Users/AMRA/hijaiyyah-mathematics")
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.hisa.assembler import assemble  # noqa: E402

OUT_DIR = ROOT / "cosmictera-build" / "stage-1-5-unified-soc" / "hdmi_option_a_11452b9c"
FS_PATH = ROOT / "rtl" / "fpga" / "gowin" / "hcpu_hdmi_top.fs"
BSM_PATH = ROOT / "rtl" / "programs" / "test_bsm.hasm"
EXPECTED_FS_SHA256 = "a416ada780a50dc8262f4effc8cad61eaff8af4787fadb5f6211acca5f5b413f"
LOAD_BASE = 64

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


def write_uart_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    sent = 0
    while sent < len(payload):
        _, w, _ = select.select([], [fd], [], 1.0)
        if not w:
            raise TimeoutError("Timed out writing payload to UART")
        n = os.write(fd, view[sent:])
        sent += n


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


def encode_loader_stream(hasm_path: Path) -> tuple[list[int], bytes]:
    words = assemble(hasm_path.read_text(encoding="utf-8"), base_dir=hasm_path.parent, base=LOAD_BASE)
    out = bytearray(struct.pack(">I", len(words)))
    for w in words:
        out += struct.pack(">I", w & 0xFFFFFFFF)
    return words, bytes(out)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_total0 = time.monotonic()

    print("=== [COSMICTERA HDMI OPTION A (`hcpu_hdmi_top.fs`) — SRAM ONLY LOAD & VALIDATION] ===")
    if not FS_PATH.exists():
        print(f"[FAIL] Bitstream not found: {FS_PATH}")
        return 1

    fs_bytes = FS_PATH.read_bytes()
    actual_sha = hashlib.sha256(fs_bytes).hexdigest()
    print(f"Bitstream : {FS_PATH} ({len(fs_bytes)} bytes)")
    print(f"SHA-256   : {actual_sha}")
    if actual_sha != EXPECTED_FS_SHA256:
        print(f"[FAIL] Bitstream SHA-256 mismatch! Expected {EXPECTED_FS_SHA256}")
        return 1
    print("[PASS] Bitstream SHA-256 verified against Option A manifest.")

    loader = resolve_loader()
    jtag_cmd = [loader, "-b", "tangnano20k", "--detect"]
    sram_cmd = [loader, "-b", "tangnano20k", str(FS_PATH)]
    forbidden_flags = {"-f", "--write-flash", "--external-flash"}
    has_flash_flag = any(flag in forbidden_flags for flag in sram_cmd)
    if has_flash_flag:
        print("[FAIL] Safety violation: Flash programming flag detected!")
        return 1
    print(f"Programmer: {loader} (SRAM ONLY — 0 flash flags)")

    # 1. JTAG Detection (measured separately)
    t_jtag0 = time.monotonic()
    det = subprocess.run(jtag_cmd, capture_output=True, text=True, check=False)
    jtag_elapsed_sec = time.monotonic() - t_jtag0
    det_out = (det.stdout or "") + (det.stderr or "")
    jtag_log_path = OUT_DIR / "jtag_detect_hdmi_option_a.log"
    jtag_log_path.write_text(det_out, encoding="utf-8")
    print(det_out.strip())
    if det.returncode != 0:
        print(f"[FAIL] JTAG detection failed (returncode={det.returncode}).")
        return 2
    print(f"[PASS] JTAG detection completed in {jtag_elapsed_sec:.3f} s.")

    # 2. SRAM Programming (measured separately)
    fd = open_uart_raw(UART_DEV)
    if fd is None:
        print(f"[WARN] UART device {UART_DEV} could not be opened prior to SRAM load.")

    try:
        t_prog0 = time.monotonic()
        proc = subprocess.run(sram_cmd, capture_output=True, text=True, check=False)
        programming_elapsed_sec = time.monotonic() - t_prog0
        load_out = (proc.stdout or "") + (proc.stderr or "")
        sram_log_path = OUT_DIR / "sram_load_hdmi_option_a.log"
        sram_log_path.write_text(load_out, encoding="utf-8")
        print(load_out.strip())
        if proc.returncode != 0:
            print(f"[FAIL] Bitstream programming to SRAM failed (returncode={proc.returncode}).")
            return 3
        print(f"[PASS] Bitstream programming to SRAM completed in {programming_elapsed_sec:.3f} s.")

        # 3. Send test_bsm.hasm over baked UART loader & capture reply
        words, stream = encode_loader_stream(BSM_PATH)
        t_uart0 = time.monotonic()
        time.sleep(0.15)  # allow 2.0 ms staged PLL/CLKDIV/OSER10 reset + loader init
        if fd is not None:
            write_uart_all(fd, stream)
        uart_data = read_uart_window(fd, duration_sec=2.0)
        uart_capture_elapsed_sec = time.monotonic() - t_uart0
    finally:
        if fd is not None:
            os.close(fd)

    total_elapsed_sec = time.monotonic() - t_total0

    bin_path = OUT_DIR / "uart_hdmi_option_a_test_bsm.bin"
    bin_path.write_bytes(uart_data)
    uart_sha256 = hashlib.sha256(uart_data).hexdigest()
    hex_spaced = " ".join(f"{b:02X}" for b in uart_data)
    uart_pass = (len(uart_data) == 23) and (b"112\n" in uart_data) and (b"CYCLES=" in uart_data)

    print(f"Programming Elapsed : {programming_elapsed_sec:.3f} s")
    print(f"UART Loader Window  : {uart_capture_elapsed_sec:.3f} s")
    print(f"Total Elapsed       : {total_elapsed_sec:.3f} s")
    print(f"Sent Program        : {BSM_PATH.name} ({len(words)} words, {len(stream)} bytes @ base={LOAD_BASE})")
    print(f"UART Reply Bytes    : {len(uart_data)} bytes")
    print(f"UART Reply Hex      : {hex_spaced}")
    print(f"UART Reply ASCII    : {uart_data!r}")

    if uart_pass:
        print("[PASS] Baked UART loader executed `test_bsm.hasm` and returned 23-byte `112` + `CYCLES=`!")
    else:
        print("[FAIL] Baked UART loader reply did not match expected 23-byte `112` + `CYCLES=` format.")

    print("[INFO] Physical HDMI 1280x720@60Hz M5.2B display output requires visual monitor confirmation.")

    evidence = {
        "bitstream_identity": {
            "bitstream": str(FS_PATH),
            "size_bytes": len(fs_bytes),
            "bitstream_sha256": actual_sha,
            "expected_sha256": EXPECTED_FS_SHA256,
            "sha256_match": actual_sha == EXPECTED_FS_SHA256,
            "baked_program": "rtl/programs/loader.hasm",
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
        "uart_loader_validation": {
            "device": UART_DEV,
            "program_sent": str(BSM_PATH),
            "load_base": LOAD_BASE,
            "words_sent": len(words),
            "bytes_sent": len(stream),
            "uart_capture_elapsed_sec": round(uart_capture_elapsed_sec, 3),
            "raw_bin_path": str(bin_path),
            "raw_sha256": uart_sha256,
            "uart_bytes": len(uart_data),
            "uart_hex": hex_spaced,
            "uart_ascii": repr(uart_data),
            "status": "PASS" if uart_pass else "FAIL",
        },
        "timing_summary": {
            "jtag_detect_elapsed_sec": round(jtag_elapsed_sec, 3),
            "programming_elapsed_sec": round(programming_elapsed_sec, 3),
            "uart_capture_elapsed_sec": round(uart_capture_elapsed_sec, 3),
            "total_elapsed_sec": round(total_elapsed_sec, 3),
        },
        "physical_verification_scope": {
            "sram_load_verified_by_script": True,
            "uart_loader_verified_by_script": uart_pass,
            "hdmi_1280x720_verified_by_script": False,
            "note": (
                "SRAM programming and baked UART loader execution (`test_bsm.hasm` -> `112` + `CYCLES=`) "
                "are verified by script. Physical HDMI 1280x720@60Hz M5.2B display requires visual confirmation."
            ),
        },
    }
    evidence_path = OUT_DIR / "sram_load_hdmi_option_a_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence JSON saved to: {evidence_path}")
    return 0 if uart_pass else 4


if __name__ == "__main__":
    sys.exit(main())
