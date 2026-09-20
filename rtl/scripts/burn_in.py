#!/usr/bin/env python3
"""burn_in.py -- the board kept at work, and a log that says whether it stayed.

    python3 rtl/scripts/burn_in.py --port /dev/tty.usbserial-X --hours 24
    python3 rtl/scripts/burn_in.py                     # what it would run

The owner's sixth priority, and the first question here that no simulation can
answer: does this machine keep running? rtl/programs/burn_in.hasm does the
work -- the jamrah gate, the 28 codex vectors, sixteen words of memory, the
stack, and a sector of the card, over and over -- and this script listens.

-- what is being measured -------------------------------------------------
Two different things, and they are not the same thing:

  the board's own count   errors, in the heartbeat. Every cycle compares what
                          it computed against what the FIRST cycle computed;
                          a mismatch raises it and it never falls.
  the host's observation  heartbeats arriving, and the gap between them. A
                          machine that has stopped cannot report that it has
                          stopped, so silence is the measurement. There is no
                          watchdog in this design -- no such module exists in
                          rtl/ -- and this script does not pretend to be one.

-- the heartbeat ----------------------------------------------------------
"H", then six numbers: heartbeats, errors, reads the card did not complete,
counter wraps, the counter shifted right 12, and the card's status word.
Errors and card failures are counted apart: a card having a bad moment is not
memory corruption, and this tier's criterion is about the second kind.

The counter at 0xFF4 is 32 bits at 27 MHz and wraps every 159.07 seconds, so
uptime is wraps and counter together. The board counts its own wraps; this
script keeps the host's clock beside it, and a run that drifts between the two
has something to explain.

Neither the cycle count nor the counter goes out whole, and the reason was
measured on 20 September 2026: PRINT renders large values wrongly on this
board. A ladder of 2^0..2^31 came back correct to 4,194,304, and from
33,554,432 upward it emits characters ABOVE '9' -- 2^25 arrives as
"335544;<", where ':' to '?' are '0' + 10 to '0' + 15. So the program keeps
every number it prints below a million and this script multiplies: cycles are
heartbeats x 1024, and the counter is its printed value x 4096, a grain of
152 microseconds.

-- the first cycle's seven numbers ----------------------------------------
Before the heartbeats, the program prints what its first cycle produced. Three
of them have an answer from elsewhere and are checked here, not assumed:

  pulse sum  28    the letters, 1..28 -- rtl/tb/jamrah_vectors.txt
  node sum   3072  three levels of the tree, each summing to the 1024 bits set
                   across all 256 bytes
  codex sum  178   sum of theta + U + rho over the Master Table

Then the first word of sector 1 in two halves, because PRINT cannot render it
whole, and how many attempts the card needed to come up. The word is reported
rather than demanded: a card carrying HFS answers 0x48465331 (`HFS1`), and a
blank one does not. The attempts matter because a card that never comes up
makes every later read pay the full bounded wait -- measured at about 3.3
seconds, which is what turned one run into six minutes without a heartbeat.

-- the card, and why a launch may be retried ------------------------------
Measured 20 September 2026, eight launches out of eight: reconfiguring the
board WHILE the SD controller is mid-read leaves the card unable to
initialise on the next run, and the run after that one -- whose card never
came up, so it never read -- finds it healthy again. The alternation was
exact. So a launch whose first cycle reports no card is not accepted: the
board is configured again and the program sent again, and the record says how
many launches it took. The finding itself belongs to the owner, not to this
script: nothing in rtl/ is touched for it.

-- the log ----------------------------------------------------------------
cosmictera-build/burn-in/<id>.jsonl, and a summary in <id>.json that is
rewritten every minute, not only at the end: a run measured in days should not
lose its verdict because the host was closed on the last one. Every
heartbeat that changes the error count is written, every gap over the
threshold is written, and one heartbeat a minute is sampled so the run has a
shape as well as a verdict. Writing all of them would be millions of lines
saying the same thing.

The board does not need this script after the program is sent. If the host
goes away the machine keeps working; what is lost is the log, not the run.
"""
from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from hijaiyyah.hisa.assembler import assemble  # noqa: E402

PROGRAM = ROOT / "rtl" / "programs" / "burn_in.hasm"
BITSTREAM = ROOT / "rtl" / "fpga" / "gowin" / "hcpu_gowin_top_loader.fs"
OUT = ROOT / "cosmictera-build" / "burn-in"
LOAD_BASE = 64
OSC_HZ = 27_000_000
WRAP_S = 2 ** 32 / OSC_HZ            # 159.0728... seconds per counter wrap
HEARTBEAT_CYCLES = 1024              # the ANDI in burn_in.hasm
COUNTER_SHIFT = 12                   # the SHRI in burn_in.hasm
FIELDS = ("heartbeats", "errors", "sd_fails", "wraps", "counter_hi", "sd_status")
FIRST = ("pulse_sum", "node_sum", "codex_sum", "card_hi", "card_lo",
         "init_attempts", "read_attempts")
EXPECT = {"pulse_sum": 28, "node_sum": 3072, "codex_sum": 178}
HFS1 = 0x48465331


def expected_first_cycle() -> dict[str, int]:
    """The three numbers that have an answer away from this board."""
    from hijaiyyah.core.master_table import MASTER_TABLE
    codex = sum(e.theta_hat + e.U + e.rho for e in MASTER_TABLE.all_entries())
    vectors = (ROOT / "rtl" / "tb" / "jamrah_vectors.txt").read_text().split("\n")
    pulses = sum(int(ln.split()[1]) for ln in vectors if len(ln.split()) == 9)
    return {"pulse_sum": pulses, "node_sum": 3 * sum(bin(b).count("1")
                                                     for b in range(256)),
            "codex_sum": codex}


def uptime_s(wraps: int, counter_hi: int) -> float:
    """The board's own idea of how long it has been running."""
    return wraps * WRAP_S + (counter_hi << COUNTER_SHIFT) / OSC_HZ


class Run:
    """One burn-in run, from the wire to the log."""

    def __init__(self, path: Path, started: datetime, port: str = "") -> None:
        self.log = path.open("a", buffering=1)
        self.port = port
        self.summary_path: Path | None = None
        self.started = started
        self.heartbeats = 0
        self.errors = 0
        self.sd_fails = 0
        self.cycles = 0
        self.last_seen = time.time()
        self.longest_gap = 0.0
        self.longest_gap_at: float | None = None
        self.unparsed = 0
        self.last_sample = 0.0
        self.board_uptime = 0.0
        self.first: dict[str, int] = {}

    def write(self, kind: str, **fields: object) -> None:
        self.log.write(json.dumps({"t": round(time.time() - self.started.timestamp(), 3),
                                   "kind": kind, **fields}) + "\n")

    def heartbeat(self, values: list[int], gap_threshold: float) -> None:
        now = time.time()
        gap = now - self.last_seen
        self.last_seen = now
        self.heartbeats += 1
        beat = dict(zip(FIELDS, values, strict=True))
        beat["cycles"] = beat["heartbeats"] * HEARTBEAT_CYCLES
        self.board_uptime = uptime_s(beat["wraps"], beat["counter_hi"])
        grew = beat["errors"] > self.errors or beat["sd_fails"] > self.sd_fails
        if grew:
            self.write("error", gap=round(gap, 3), **beat)
        if gap > gap_threshold:
            self.write("gap", gap=round(gap, 3), **beat)
        if gap > self.longest_gap:
            self.longest_gap, self.longest_gap_at = gap, now - self.started.timestamp()
        if now - self.last_sample >= 60:
            self.last_sample = now
            self.write("sample", gap=round(gap, 3),
                       host_s=round(now - self.started.timestamp(), 1),
                       board_s=round(self.board_uptime, 1), **beat)
            if self.summary_path is not None:
                self.summary_path.write_text(
                    json.dumps(self.summary(self.port, "still running"), indent=2)
                    + "\n")
        self.errors, self.cycles = beat["errors"], beat["cycles"]
        self.sd_fails = beat["sd_fails"]

    def summary(self, port: str, note: str) -> dict[str, object]:
        host_s = time.time() - self.started.timestamp()
        return {
            "target": "burn-in",
            "program": str(PROGRAM.relative_to(ROOT)),
            "board": "Tang Nano 20K",
            "clock_hz": OSC_HZ,
            "port": port,
            "started": self.started.isoformat(),
            "first_cycle": self.first,
            "host_seconds": round(host_s, 1),
            "board_seconds": round(self.board_uptime, 1),
            "board_minus_host_s": round(self.board_uptime - host_s, 1),
            "heartbeats": self.heartbeats,
            "cycles": self.cycles,
            "errors": self.errors,
            "sd_read_failures": self.sd_fails,
            "longest_gap_s": round(self.longest_gap, 3),
            "longest_gap_at_s": (round(self.longest_gap_at, 1)
                                 if self.longest_gap_at else None),
            "unparsed_lines": self.unparsed,
            "heartbeat_cycles": HEARTBEAT_CYCLES,
            "ended": note,
        }


class Feed:
    """Bytes from the wire, turned into first cycles and heartbeats.

    Its own class because a day-long run cannot be re-run to test its parser,
    and because this parser has been wrong once already: it counted numbers
    instead of marking groups, read the first cycle's seven values as a
    six-field heartbeat, and wrote 3,072 errors that did not exist into a log.
    """

    def __init__(self, run: Run, want: dict[str, int], gap_threshold: float,
                 beating: bool = False) -> None:
        self.run, self.want, self.gap_threshold = run, want, gap_threshold
        self.beating = beating          # has an "H" arrived yet
        self.buf = bytearray()
        self.pending: list[int] = []

    def take(self, chunk: bytes) -> None:
        if chunk:
            self.buf += chunk
        while b"\n" in self.buf:
            line, _, rest = self.buf.partition(b"\n")
            self.buf = bytearray(rest)
            self.line(bytes(c for c in line if 32 <= c < 127).decode("ascii").strip())

    def line(self, text: str) -> None:
        if text == "H":
            # The first cycle's numbers come before any H, so what a group
            # means is decided by whether one has arrived -- not by how many
            # numbers are in hand.
            self.beating, self.pending = True, []
        elif text.isdigit():
            self.pending.append(int(text))
            if not self.beating and not self.run.first:
                if len(self.pending) == len(FIRST):
                    self.first_cycle()
            elif self.beating and len(self.pending) == len(FIELDS):
                self.run.heartbeat(self.pending, self.gap_threshold)
                self.pending = []
        elif text:
            # Dropped whole, never stripped down to its digits: "335544;<" is
            # not 335544, and a lab that quietly makes it so is the lab that
            # lost a line in jamrah_board.py.
            self.run.unparsed += 1
            self.run.write("unparsed", text=text[:64])

    def first_cycle(self) -> None:
        first = dict(zip(FIRST, self.pending, strict=True))
        first["card_word"] = first.pop("card_hi") << 16 | first.pop("card_lo")
        ok = all(first[k] == v for k, v in self.want.items())
        self.run.first = first
        self.run.write("first_cycle", ok=ok, **first)
        print(f"first cycle: {first}, card word {first['card_word']:#010x}"
              f"{' -- HFS1' if first['card_word'] == HFS1 else ''} "
              f"{'as expected' if ok else 'DISAGREES with Python'}")
        self.pending = []


def configure(bitstream: Path) -> None:
    subprocess.run(["openFPGALoader", "-b", "tangnano20k", str(bitstream)],
                   check=True, capture_output=True)
    time.sleep(0.8)


def send(port: str):
    """The program to the board, and the open port back."""
    import serial
    from send_program import encode
    words = assemble(PROGRAM.read_text(encoding="utf-8"),
                     base_dir=PROGRAM.parent, base=LOAD_BASE)
    link = serial.Serial(port, 115200, timeout=1)
    link.reset_input_buffer()
    link.write(encode(words))
    link.flush()
    return link, len(words)


def first_cycle(link, timeout: float) -> dict[str, int] | None:
    """Read until the seven numbers the first cycle prints, or give up.

    They arrive before any "H", so the group is marked rather than counted --
    a lesson from a parser that read them as a six-field heartbeat and
    reported 3,072 errors that did not exist.
    """
    end = time.time() + timeout
    seen: list[int] = []
    buf = bytearray()
    while time.time() < end and len(seen) < len(FIRST):
        buf += link.read(64)
        while b"\n" in buf:
            line, _, rest = buf.partition(b"\n")
            buf = bytearray(rest)
            text = bytes(c for c in line if 32 <= c < 127).decode("ascii").strip()
            if text == "H":
                return None            # a heartbeat first: the group is gone
            if text.isdigit():
                seen.append(int(text))
            # Anything else is dropped rather than stripped down to its digits.
            # "335544;<" is not 335544, and a lab that quietly makes it so is
            # the lab that lost a line in jamrah_board.py.
    return dict(zip(FIRST, seen, strict=True)) if len(seen) == len(FIRST) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", help="serial device; omit to print the plan only")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--label", default="", help="added to the record's name")
    ap.add_argument("--gap-threshold", type=float, default=5.0,
                    help="seconds of silence worth writing down")
    ap.add_argument("--launches", type=int, default=4,
                    help="attempts, because the card does not always come up")
    ap.add_argument("--first-timeout", type=float, default=75.0,
                    help="seconds to wait for the first cycle; eight failed "
                         "card attempts take about 55")
    ap.add_argument("--bitstream", type=Path, default=BITSTREAM)
    ap.add_argument("--no-configure", dest="configure", action="store_false",
                    help="do not load the bitstream; take the board as it is")
    args = ap.parse_args(argv)

    want = expected_first_cycle()
    if want != EXPECT:
        print(f"the expected first cycle moved: {want} against {EXPECT}", file=sys.stderr)
        return 1
    words = len(assemble(PROGRAM.read_text(encoding="utf-8"),
                         base_dir=PROGRAM.parent, base=LOAD_BASE))
    if args.port is None:
        print(f"{PROGRAM.relative_to(ROOT)}: {words} words at {LOAD_BASE}")
        print(f"first cycle should print {want['pulse_sum']}, {want['node_sum']}, "
              f"{want['codex_sum']}, then the card's first word in two halves "
              f"({HFS1 >> 16}, {HFS1 & 0xFFFF} for a card carrying HFS)")
        print(f"heartbeat every {HEARTBEAT_CYCLES} cycles; the counter wraps "
              f"every {WRAP_S:.2f} s, and the board counts its own wraps")
        return 0

    started = datetime.now(timezone.utc)
    ident = started.strftime("%Y%m%dT%H%M%SZ") + "-burn-in" + (
        f"-{args.label}" if args.label else "")
    OUT.mkdir(parents=True, exist_ok=True)
    run = Run(OUT / f"{ident}.jsonl", started, args.port)
    run.summary_path = OUT / f"{ident}.json"

    def stop(signum: int, frame: types.FrameType | None) -> None:
        raise KeyboardInterrupt(f"signal {signum}")

    signal.signal(signal.SIGTERM, stop)
    run.write("start", program_words=words, hours=args.hours, expect=want)
    print(f"logging to {(OUT / f'{ident}.jsonl').relative_to(ROOT)}")
    link = None
    for launch in range(1, args.launches + 1):
        if args.configure:
            configure(args.bitstream)
        link, _ = send(args.port)
        first = first_cycle(link, args.first_timeout)
        run.write("launch", n=launch, first=first)
        if first:
            first["card_word"] = first.pop("card_hi") << 16 | first.pop("card_lo")
            ok = all(first[k] == v for k, v in want.items())
            print(f"launch {launch}: {first}, card word {first['card_word']:#010x}"
                  f"{' -- HFS1' if first['card_word'] == HFS1 else ''} "
                  f"{'as expected' if ok else 'DISAGREES with Python'}")
            if first["card_word"] or not args.configure:
                run.first = first
                run.first["launches"] = launch
                run.write("first_cycle", ok=ok, **first)
                break
            print(f"launch {launch}: the card did not come up; configuring again")
        else:
            print(f"launch {launch}: no first cycle within {args.first_timeout}s")
        link.close()
        link = None
    if link is None:
        print(f"{args.launches} launches, and the card never came up", file=sys.stderr)
        return 1

    # A shorter timeout than the launch used, so the gap between beats is the
    # board's cadence rather than the host's polling. Tier 1 ran at 1.0 s and
    # its intervals piled up at 1.0 and 2.0 against a true period of 1.58.
    link.timeout = 0.25
    # A shorter timeout than the launch used, so the gap between beats is the
    # board's cadence rather than the host's polling. Tier 1 ran at 1.0 s and
    # its intervals piled up at 1.0 and 2.0 against a true period of 1.58.
    link.timeout = 0.25
    deadline = time.time() + args.hours * 3600
    feed = Feed(run, want, args.gap_threshold, beating=bool(run.first))
    note = "duration reached"
    try:
        while time.time() < deadline:
            feed.take(link.read(256))
    except KeyboardInterrupt:
        note = "stopped before the duration"
    finally:
        link.close()
        record = run.summary(args.port, note)
        (OUT / f"{ident}.json").write_text(json.dumps(record, indent=2) + "\n")
        run.write("end", **record)
        run.log.close()
    print(f"\n{record['heartbeats']} heartbeats, {record['cycles']} cycles, "
          f"{record['errors']} error(s), {record['sd_read_failures']} card read(s) "
          f"unfinished; board {record['board_seconds']}s against host "
          f"{record['host_seconds']}s; longest silence {record['longest_gap_s']}s")
    print(f"record: {(OUT / f'{ident}.json').relative_to(ROOT)}")
    return 0 if record["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
