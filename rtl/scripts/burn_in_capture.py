#!/usr/bin/env python3
"""burn_in_capture.py -- the wire, kept as bytes, and nothing read into it.

    python3 rtl/scripts/burn_in_capture.py --port /dev/tty.usbserial-X --minutes 12
    python3 rtl/scripts/burn_in_capture.py                  # what it would run

The owner's step P1, 24 September 2026: *"raw capture menjadi evidence primer;
parser tidak lagi menjadi sumber bukti primer."* So this tool does one thing --
it writes down what arrived -- and burn_in_parse.py reads it afterwards, away
from the board, as many times as a question needs.

-- why a second path instead of a change to burn_in.py --------------------
The owner's instruction, same day: burn_in.py is not turned into the capture
tool, so the historical function stays whole. Every record it has written --
including the 72-hour run closed on 24 September -- keeps meaning what it
meant. This module imports burn_in for the things that must not exist twice
(R1): the program, the bitstream, how the board is configured, and how the
program is sent.

-- what this refuses to do ------------------------------------------------
It does not parse. Not a heartbeat, not a first cycle, not an error count.
That is the whole point: the 72-hour run cannot be re-parsed from its bytes
because no bytes were kept, and the two `error` rows in its log are what a
parser writes when a line arrives merged. A capture that interpreted as it
recorded would have the same blind spot.

-- what is written --------------------------------------------------------
    <id>-capture.raw          every byte, in the order it arrived
    <id>-capture.times.jsonl  one line per read: byte offset, host UTC, length
    <id>-capture.json         the manifest

The times file is beside the bytes rather than inside them so the raw file
stays exactly what the wire gave. It is what lets an offline parser say when a
line arrived -- the host's clock, tier 3 of the time hierarchy, for recording
and not for judging (cosmictera/TELEMETRY.md).

The manifest carries what the owner asked P1 to record: start and end in host
time, the device, the bitstream's fingerprint, the byte count, and the SHA256
of the raw file. The fingerprint is computed from the file that was loaded,
not quoted from a note: on 24 September a note disagreed with the file, and
the file is what the board was given.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from burn_in import BITSTREAM, OUT, PROGRAM, configure, send  # noqa: E402

VERSION = 1


def _rel(path: Path) -> str:
    """The repo-relative path where there is one. A bitstream given from
    somewhere else is recorded as it was given, not rewritten."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fingerprint(path: Path) -> str:
    """The SHA256 of a file, read as bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _same_device(a: str, b: str) -> bool:
    """/dev/tty.X and /dev/cu.X are one device on macOS (dial-in / call-out)."""
    def stem(p: str) -> str:
        name = p.rsplit("/", 1)[-1]
        for prefix in ("tty.", "cu."):
            if name.startswith(prefix):
                return name[len(prefix):]
        return name
    return a == b or (a.startswith("/dev/") and b.startswith("/dev/")
                      and stem(a) == stem(b))


def device_identity(port: str) -> dict[str, str]:
    """What the host knows about the device the bytes came from.

    pyserial's port listing carries the adapter's own serial number and VID:PID
    where the driver exposes them; where it does not, the fields say so rather
    than being filled in.

    On macOS the listing holds only the call-out node, /dev/cu.X, while a
    capture may be given the dial-in node, /dev/tty.X, of the same device.
    Matched by path alone, the P1 capture of 24 September 2026 wrote "not in
    this host's listing" with the adapter attached (measured in 08f1e36), so
    the two nodes are taken as one device.
    """
    found: dict[str, str] = {"port": port}
    try:
        from serial.tools import list_ports
    except ImportError:
        return {**found, "note": "pyserial's port listing is not available here"}
    for info in list_ports.comports():
        if _same_device(info.device, port):
            found.update({k: str(v) for k, v in (
                ("serial_number", info.serial_number), ("vid_pid", info.hwid),
                ("manufacturer", info.manufacturer), ("product", info.product))
                if v is not None})
            return found
    return {**found, "note": "the port is not in this host's listing"}


class Capture:
    """One capture: bytes to one file, arrival times to another."""

    def __init__(self, raw: Path, times: Path) -> None:
        self.raw = raw.open("wb", buffering=0)
        self.times = times.open("w", buffering=1, encoding="utf-8")
        self.bytes_written = 0
        self.reads = 0
        self.digest = hashlib.sha256()

    def take(self, chunk: bytes, at: float) -> None:
        """One read from the wire. Empty reads are not recorded: they are the
        host's timeout expiring, not something the board sent."""
        if not chunk:
            return
        self.times.write(json.dumps({"offset": self.bytes_written,
                                     "utc": datetime.fromtimestamp(
                                         at, timezone.utc).isoformat(),
                                     "n": len(chunk)}) + "\n")
        self.raw.write(chunk)
        self.digest.update(chunk)
        self.bytes_written += len(chunk)
        self.reads += 1

    def close(self) -> None:
        self.raw.close()
        self.times.close()


def capture(link, sink: Capture, deadline: float, read_size: int = 256) -> str:
    """Read until the deadline, and say truthfully why the reading stopped.

    The shape of `listen()` in burn_in.py, and for the reason written there: a
    record that says "duration reached" when the port vanished looks like a
    finished run.
    """
    try:
        while time.time() < deadline:
            sink.take(link.read(read_size), time.time())
    except KeyboardInterrupt:
        return "stopped before the duration"
    except Exception as exc:                      # the port vanishing, above all
        return f"STOPPED EARLY: {type(exc).__name__}: {exc}"
    return "duration reached"


def manifest(run_id: str, started: datetime, ended: datetime, note: str,
             port: str, bitstream: Path, sink: Capture, minutes: float) -> dict[str, object]:
    return {
        "target": "burn-in-capture",
        "capture_version": VERSION,
        "run_id": run_id,
        "program": _rel(PROGRAM),
        "board": "Tang Nano 20K",
        "device": device_identity(port),
        "bitstream": _rel(bitstream),
        "bitstream_sha256": fingerprint(bitstream),
        "started": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "minutes_requested": minutes,
        "seconds_captured": round(ended.timestamp() - started.timestamp(), 3),
        "bytes": sink.bytes_written,
        "reads": sink.reads,
        "raw_sha256": sink.digest.hexdigest(),
        "raw": f"{run_id}-capture.raw",
        "times": f"{run_id}-capture.times.jsonl",
        "ended": note,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", help="serial device; omit to print the plan only")
    ap.add_argument("--minutes", type=float, default=12.0)
    ap.add_argument("--label", default="burn-in",
                    help="added to the record's name, before -capture")
    ap.add_argument("--bitstream", type=Path, default=BITSTREAM)
    ap.add_argument("--no-configure", dest="configure", action="store_false",
                    help="do not load the bitstream; take the board as it is")
    args = ap.parse_args(argv)

    if args.port is None:
        print(f"program   {PROGRAM.relative_to(ROOT)}")
        print(f"bitstream {args.bitstream.relative_to(ROOT)}")
        print(f"          sha256 {fingerprint(args.bitstream)}")
        print(f"would capture {args.minutes} minute(s) of raw bytes into "
              f"{OUT.relative_to(ROOT)}/<id>-capture.raw")
        print("nothing is parsed here; burn_in_parse.py reads the bytes afterwards")
        return 0

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + f"-{args.label}"
    OUT.mkdir(parents=True, exist_ok=True)
    sink = Capture(OUT / f"{run_id}-capture.raw", OUT / f"{run_id}-capture.times.jsonl")
    print(f"capturing to {(OUT / f'{run_id}-capture.raw').relative_to(ROOT)}")

    if args.configure:
        configure(args.bitstream)
    link, words = send(args.port)
    link.timeout = 0.25
    print(f"{words} words sent; reading for {args.minutes} minute(s)")
    note = capture(link, sink, time.time() + args.minutes * 60)
    link.close()
    ended = datetime.now(timezone.utc)
    sink.close()

    record = manifest(run_id, started, ended, note, args.port, args.bitstream,
                      sink, args.minutes)
    (OUT / f"{run_id}-capture.json").write_text(json.dumps(record, indent=2) + "\n",
                                                encoding="utf-8")
    print(f"{record['bytes']} bytes in {record['reads']} read(s), "
          f"sha256 {record['raw_sha256']}")
    print(f"manifest: {(OUT / f'{run_id}-capture.json').relative_to(ROOT)}")
    return 0 if note == "duration reached" and sink.bytes_written else 1


if __name__ == "__main__":
    raise SystemExit(main())
