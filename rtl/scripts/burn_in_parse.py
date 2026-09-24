#!/usr/bin/env python3
"""burn_in_parse.py -- a raw capture read afterwards, and strictly.

    python3 rtl/scripts/burn_in_parse.py cosmictera-build/burn-in/<id>-capture.json
    python3 rtl/scripts/burn_in_parse.py <id>-capture.raw --write

The owner's step P1, 24 September 2026. The 72-hour run of tier 2 wrote two
`error` rows that were never the board's: a number arrived stuck to the next
beat's marker -- `0H` -- the line separator was gone, and what followed was
read as a heartbeat with its fields shifted one place. `errors` then held 7,440
and 8,058, the size of the beat numbers beside them. The board's own counter
never left 0, which is how P0 could prove it; but a parser that can turn a lost
newline into an error count is a parser that can invent one.

So this reads a capture against a grammar rather than by counting numbers:

    beat      := "H" NL field NL field NL field NL field NL field NL field NL
    first     := field NL x7                 -- once, before the first "H"
    field     := [0-9]+ , below 2^32

Anything else is a **parse error**, carrying its byte offset, the text as it
arrived, and a reason. A parse error never becomes a board error, and it drops
whatever fields were pending: a group interrupted by a bad line cannot be
completed by the lines after it, because that is exactly how a shifted beat is
manufactured. The two counts are kept apart to the end -- `board_errors` comes
only from the `errors` field of a beat that parsed whole; `parse_errors` is the
host's own trouble reading the wire.

What the owner listed for P1, and where each lands here:

    merged records          `merged_record`         "0H", "HH", "12H34"
    truncated records       `truncated_record`      a beat with fewer than six
    invalid field           `non_numeric_field`     "335544;<", "1A2B", "error"
    missing field           `truncated_record`      same shape, named once
    unexpected field count  `unexpected_field_count` seven where six are due
    partial line            `partial_line`          bytes with no newline yet

The owner wrote "invalid hexadecimal field". This wire is decimal -- PRINT
renders decimal, and the program keeps every number below a million because
PRINT is wrong above 2^22 (cosmictera-build/OFF.md) -- so a hexadecimal digit
is one case of `non_numeric_field`, and it is not called hexadecimal here
rather than implying a format the board does not emit.

Nothing in this module reads the board. It takes bytes that were captured by
burn_in_capture.py, and it can be run again on the same bytes as many times as
a question needs -- which is what "raw capture is the primary evidence" means.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from burn_in import FIELDS, FIRST, HEARTBEAT_CYCLES, uptime_s  # noqa: E402

VERSION = 1
MARKER = "H"
FIELD = re.compile(r"[0-9]{1,10}\Z")
FIELD_MAX = 2 ** 32


class Parsed:
    """What a capture turned into: beats, a first cycle, and parse errors."""

    def __init__(self) -> None:
        self.beats: list[dict[str, Any]] = []
        self.first_cycle: dict[str, Any] | None = None
        self.errors: list[dict[str, Any]] = []
        self.lines = 0

    @property
    def board_errors(self) -> int:
        """The board's own count, from beats that parsed whole. Never touched
        by a parse error -- that is the separation P1 exists for."""
        return max((b["errors"] for b in self.beats), default=0)

    @property
    def board_error_growth(self) -> list[dict[str, Any]]:
        """Every beat where the board's own counter rose. It never falls."""
        grew, seen = [], 0
        for beat in self.beats:
            if beat["errors"] > seen:
                grew.append(beat)
                seen = beat["errors"]
        return grew

    @property
    def reasons(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for bad in self.errors:
            out[bad["reason"]] = out.get(bad["reason"], 0) + 1
        return dict(sorted(out.items()))

    def summary(self) -> dict[str, Any]:
        return {
            "parser_version": VERSION,
            "lines": self.lines,
            "beats": len(self.beats),
            "first_cycle": self.first_cycle,
            "board_errors": self.board_errors,
            "board_error_growth": len(self.board_error_growth),
            "sd_read_failures": max((b["sd_fails"] for b in self.beats), default=0),
            "cycles": max((b["cycles"] for b in self.beats), default=0),
            "parse_errors": len(self.errors),
            "parse_error_reasons": self.reasons,
        }


class _Times:
    """Host arrival time for a byte offset, from the capture's sidecar."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = sorted(rows, key=lambda r: r["offset"])

    def at(self, offset: int) -> str | None:
        found = None
        for row in self.rows:
            if row["offset"] > offset:
                break
            found = row["utc"]
        return found


def _clean(raw: bytes) -> str:
    """Printable ASCII only, as burn_in.py does -- a control byte is not part
    of a number, and stripping it down to digits is how `335544;<` becomes
    335544 in a lab that has stopped being careful."""
    return bytes(c for c in raw if 32 <= c < 127).decode("ascii").strip()


def _reason(text: str) -> str:
    if MARKER in text:
        return "merged_record"
    return "non_numeric_field"


def parse(raw: bytes, times: _Times | None = None) -> Parsed:
    """Bytes to beats, strictly. Every rejection is recorded, never repaired."""
    out = Parsed()
    offset = 0
    in_beat = False
    seen_marker = False
    beat_at = 0
    pending: list[int] = []
    before_first_marker: list[int] = []

    def fail(reason: str, text: str, at: int) -> None:
        nonlocal in_beat, pending
        out.errors.append({"kind": "parse_error", "reason": reason, "offset": at,
                           "utc": times.at(at) if times else None, "text": text[:64]})
        # Whatever was pending is dropped: a group interrupted by a bad line
        # must not be completed by the lines that follow it.
        in_beat, pending = False, []

    def close(at: int) -> None:
        nonlocal in_beat, pending
        if in_beat and len(pending) != len(FIELDS):
            fail("truncated_record", f"{len(pending)} of {len(FIELDS)} fields", at)
        in_beat, pending = False, []

    lines = raw.split(b"\n")
    tail = lines.pop() if lines else b""
    for line in lines:
        at = offset
        offset += len(line) + 1
        text = _clean(line)
        out.lines += 1
        if not text:
            continue
        if text == MARKER:
            close(at)
            if not seen_marker and before_first_marker:
                if len(before_first_marker) == len(FIRST):
                    first = dict(zip(FIRST, before_first_marker, strict=True))
                    first["card_word"] = first.pop("card_hi") << 16 | first.pop("card_lo")
                    first["offset"] = at
                    out.first_cycle = first
                else:
                    fail("unexpected_field_count",
                         f"{len(before_first_marker)} numbers before the first {MARKER}", at)
                before_first_marker = []
            seen_marker, in_beat, pending, beat_at = True, True, [], at
        elif FIELD.match(text) and int(text) < FIELD_MAX:
            if not in_beat:
                # Before the first marker these are the first cycle's seven.
                # After it, a number outside a beat is a number whose beat was
                # lost -- it is never collected into a group of its own, which
                # is how a dropped newline manufactured a shifted beat.
                if not seen_marker and len(before_first_marker) < len(FIRST):
                    before_first_marker.append(int(text))
                else:
                    fail("unexpected_field_count", text, at)
                continue
            pending.append(int(text))
            if len(pending) == len(FIELDS):
                beat = dict(zip(FIELDS, pending, strict=True))
                beat["cycles"] = beat["heartbeats"] * HEARTBEAT_CYCLES
                beat["board_uptime_s"] = round(uptime_s(beat["wraps"],
                                                        beat["counter_hi"]), 3)
                # The marker's offset, not the last field's: a beat is the
                # bytes from `H` to its sixth number, and a reader holding
                # this record must be able to find exactly those bytes again.
                beat["offset"] = beat_at
                beat["utc"] = times.at(beat_at) if times else None
                out.beats.append(beat)
                in_beat, pending = False, []
        elif text.isdigit():
            fail("field_out_of_range", text, at)
        else:
            fail(_reason(text), text, at)
    if tail:
        out.lines += 1
        fail("partial_line", _clean(tail), offset)
    else:
        close(offset)
    return out


def load_capture(path: Path) -> tuple[bytes, _Times | None, dict[str, Any] | None]:
    """A manifest, or the raw file itself. Given the manifest, the raw file's
    SHA256 is checked against it before a byte is read as anything."""
    if path.suffix == ".json":
        record = json.loads(path.read_text(encoding="utf-8"))
        raw_path = path.parent / str(record["raw"])
        raw = raw_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != record["raw_sha256"]:
            raise SystemExit(f"{raw_path.name}: sha256 {digest} is not the "
                             f"{record['raw_sha256']} the manifest recorded")
        times_path = path.parent / str(record["times"])
        times = _Times([json.loads(ln) for ln in
                        times_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
                       ) if times_path.exists() else None
        return raw, times, record
    return path.read_bytes(), None, None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture", type=Path, help="a capture manifest (.json) or its .raw")
    ap.add_argument("--write", action="store_true",
                    help="write <id>-parsed.jsonl and <id>-parsed.json beside it")
    args = ap.parse_args(argv)

    raw, times, record = load_capture(args.capture)
    parsed = parse(raw, times)
    summary = parsed.summary()
    if record is not None:
        summary["capture"] = {k: record[k] for k in
                              ("run_id", "bitstream", "bitstream_sha256", "started",
                               "ended_utc", "bytes", "raw_sha256", "ended")
                              if k in record}
    print(json.dumps(summary, indent=2))
    if parsed.errors:
        print("\nparse errors, none of which is a board error:")
        for bad in parsed.errors[:20]:
            print(f"  {bad['offset']:>9}  {bad['reason']:<22} {bad['text']!r}")
    if args.write:
        stem = args.capture.name.split("-capture")[0]
        out = args.capture.parent / f"{stem}-parsed.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            if parsed.first_cycle:
                fh.write(json.dumps({"kind": "first_cycle", **parsed.first_cycle}) + "\n")
            for beat in parsed.beats:
                fh.write(json.dumps({"kind": "heartbeat", **beat}) + "\n")
            for bad in parsed.errors:
                fh.write(json.dumps(bad) + "\n")
        (args.capture.parent / f"{stem}-parsed.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"\nparsed: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
