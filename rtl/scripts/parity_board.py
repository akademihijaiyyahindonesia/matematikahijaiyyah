#!/usr/bin/env python3
"""Run layer 4's parity corpus on the board, and keep what came back.

    python3 rtl/scripts/parity_board.py                 # the plan; no board
    python3 rtl/scripts/parity_board.py --port /dev/tty.usbserial-X

For each program src/hijaiyyah/nui/board_parity.py decides to send: configure
the board with the loader bitstream -- a fresh start, as every recorded board
run in cosmictera-build/PAPAN.md did between programs -- send the payload over
the wire the way rtl/scripts/send_program.py does, and read until the
wrapper's CYCLES= report or a deadline. The raw bytes are kept, in hex, beside
what was parsed out of them, in cosmictera-build/parity-board/<UTC>.json;
nothing is compared here. src/hijaiyyah/nui/parity_model.py reads the newest
record and does that.

It refuses to start while a burn-in process is alive: the board carries the
72-hour run, and configuring it would end that run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from burn_in import BITSTREAM, configure  # noqa: E402
from send_program import encode  # noqa: E402

from hijaiyyah.nui.board_parity import RECORDS, corpus, parse_capture  # noqa: E402

BAUD = 115_200
SLACK_S = 5.0


def burn_in_running() -> bool:
    """True while any process is running rtl/scripts/burn_in.py."""
    out = subprocess.run(["pgrep", "-f", "rtl/scripts/burn_in.py"],
                         capture_output=True, text=True)
    return bool(out.stdout.strip())


def deadline_s(sent_bytes: int, expected_bytes: int) -> float:
    """Ten bits a byte each way at 115,200 baud, and slack for the run."""
    return (sent_bytes + expected_bytes) * 10 / BAUD + SLACK_S


def run_one(port: str, payload: list[int], expected_bytes: int) -> tuple[bytes, bool]:
    import serial  # pyserial, optional
    stream = encode(payload)
    raw = bytearray()
    timed_out = True
    with serial.Serial(port, BAUD, timeout=0.2) as link:
        link.reset_input_buffer()
        link.write(stream)
        link.flush()
        end = time.time() + deadline_s(len(stream), expected_bytes)
        while time.time() < end:
            raw += link.read(4096)
            if b"CYCLES=" in raw and raw.split(b"CYCLES=", 1)[1].count(b"\n"):
                timed_out = False
                break
    return bytes(raw), timed_out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial device; without it, print the plan only")
    ap.add_argument("--bitstream", type=Path, default=BITSTREAM)
    ap.add_argument("--only", nargs="*", default=None, help="program names to send")
    args = ap.parse_args(argv)

    programs = corpus()
    if args.only:
        programs = [bp for bp in programs if bp.name in args.only]
    send = [bp for bp in programs if not bp.excluded]
    if not args.port:
        print(f"{len(send)} of {len(programs)} programs would be sent")
        for bp in programs:
            mark = "skip" if bp.excluded else "send"
            print(f"  {mark} {bp.name:<50} {len(bp.payload):>5} words  {bp.excluded}")
        return 0
    if burn_in_running():
        print("refused: a burn-in process is running, and this would end it")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    record = {"date": stamp, "commit": commit,
              "bitstream": args.bitstream.relative_to(ROOT).as_posix(),
              "bitstream_sha256": hashlib.sha256(args.bitstream.read_bytes()).hexdigest(),
              "programs": {}}
    for bp in programs:
        if bp.excluded:
            record["programs"][bp.name] = {"excluded": bp.excluded}
            continue
        configure(args.bitstream)
        raw, timed_out = run_one(args.port, bp.payload, len(bp.expected))
        record["programs"][bp.name] = {"words": len(bp.payload), "timed_out": timed_out,
                                       "raw_hex": raw.hex(), **parse_capture(raw)}
        state = "timed out" if timed_out else "ok"
        print(f"  {bp.name:<50} {len(raw):>6} bytes  {state}")
    RECORDS.mkdir(parents=True, exist_ok=True)
    out = RECORDS / f"{stamp}.json"
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"record: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
