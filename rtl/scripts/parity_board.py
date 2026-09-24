#!/usr/bin/env python3
"""Run a layer 4 board experiment, keep what came back, and read it.

    python3 rtl/scripts/parity_board.py                              # the plan; no board
    python3 rtl/scripts/parity_board.py --experiment print           # one experiment's plan
    python3 rtl/scripts/parity_board.py --experiment parity --port /dev/tty.usbserial-X
    python3 rtl/scripts/parity_board.py --report cosmictera-build/parity-board/<rec>.json

Three experiments, the owner's of 22 September 2026, each run on its own:
`parity` (layer 4's corpus), `print` (PRINT in silicon) and `stop` (the word
behind HALT and behind a RET fault). src/hijaiyyah/nui/board_parity.py
decides what each sends and holds what each should print, frozen in
NUI/board_expected.json before the board is asked.

For each program: configure the board with the loader bitstream -- a fresh
start, as every recorded board run in cosmictera-build/PAPAN.md did between
programs -- send the payload over the wire the way rtl/scripts/send_program.py
does, and read until the wrapper's CYCLES= report or a deadline. The raw
bytes are kept, in hex, beside what was parsed out of them, in
cosmictera-build/parity-board/<UTC>-<experiment>.json. Nothing is compared
while the board is being asked; --report reads a record afterwards against the
frozen expectation and writes <record>.report.json beside it.

It refuses to start while a burn-in process is alive: configuring the board
would end that run. It refuses a payload whose hash is not the one the
expectation froze: an answer is only read against what was written down
before it.
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

from hijaiyyah.nui.board_parity import (  # noqa: E402
    EXPECTED,
    EXPERIMENTS,
    RECORDS,
    load_expected,
    parse_capture,
    payload_sha256,
    programs_for,
    report,
)

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
        # Drain what the wire still holds before this program is sent.
        # reset_input_buffer() alone was not enough on 24 September 2026: the
        # board had been left running the burn-in program, and the first
        # capture of the parity corpus opened with 482 of its heartbeats --
        # bytes the driver had buffered while nothing was reading. A program's
        # answer must be the program's.
        while link.read(4096):
            pass
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


def stale(programs: list, expected: dict) -> list[str]:  # type: ignore[type-arg]
    """Programs whose payload is not the one the expectation froze."""
    out = []
    for bp in programs:
        if bp.excluded:
            continue
        frozen = expected["programs"].get(bp.name, {})
        if frozen.get("payload_sha256") != payload_sha256(bp.payload):
            out.append(bp.name)
    return out


def write_report(path: Path) -> Path:
    record = json.loads(path.read_text(encoding="utf-8"))
    out = path.with_suffix(".report.json")
    out.write_text(json.dumps(report(record), indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiment", choices=EXPERIMENTS, default=None,
                    help="one experiment; without --port and without it, all three plans")
    ap.add_argument("--port", help="serial device; without it, print the plan only")
    ap.add_argument("--bitstream", type=Path, default=BITSTREAM)
    ap.add_argument("--only", nargs="*", default=None, help="program names to send")
    ap.add_argument("--report", type=Path, help="read a record against the expectation")
    args = ap.parse_args(argv)

    if args.report:
        out = write_report(args.report)
        counts = json.loads(out.read_text(encoding="utf-8"))["counts"]
        print(f"report: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} {counts}")
        return 0

    experiments = [args.experiment] if args.experiment else list(EXPERIMENTS)
    if not args.port:
        for experiment in experiments:
            programs = programs_for(experiment)
            send = [bp for bp in programs if not bp.excluded]
            print(f"{experiment}: {len(send)} of {len(programs)} programs would be sent")
            for bp in programs:
                mark = "skip" if bp.excluded else "send"
                print(f"  {mark} {bp.name:<50} {len(bp.payload):>5} words  {bp.excluded}")
        return 0
    if args.experiment is None:
        print("refused: name the experiment to run -- each runs on its own")
        return 2
    if burn_in_running():
        print("refused: a burn-in process is running, and this would end it")
        return 2

    programs = programs_for(args.experiment)
    if args.only:
        programs = [bp for bp in programs if bp.name in args.only]
    expected = load_expected()[args.experiment]
    changed = stale(programs, expected)
    if changed:
        print(f"refused: {len(changed)} payload(s) differ from the frozen expectation "
              f"({', '.join(changed[:3])}...). Regenerate {EXPECTED.relative_to(ROOT)} and "
              f"commit it before asking the board.")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    record = {"date": stamp, "commit": commit, "experiment": args.experiment,
              "expected_sha256": hashlib.sha256(EXPECTED.read_bytes()).hexdigest(),
              "bitstream": args.bitstream.relative_to(ROOT).as_posix(),
              "bitstream_sha256": hashlib.sha256(args.bitstream.read_bytes()).hexdigest(),
              "programs": {}}
    for bp in programs:
        if bp.excluded:
            record["programs"][bp.name] = {"excluded": bp.excluded}
            continue
        configure(args.bitstream)
        raw, timed_out = run_one(args.port, bp.payload, len(bp.expected))
        record["programs"][bp.name] = {"words": len(bp.payload),
                                       "payload_sha256": payload_sha256(bp.payload),
                                       "timed_out": timed_out, "raw_hex": raw.hex(),
                                       **parse_capture(raw)}
        state = "timed out" if timed_out else "ok"
        print(f"  {bp.name:<50} {len(raw):>6} bytes  {state}")
    RECORDS.mkdir(parents=True, exist_ok=True)
    out = RECORDS / f"{stamp}-{args.experiment}.json"
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"record: {out.relative_to(ROOT)}")
    print(f"report: {write_report(out).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
