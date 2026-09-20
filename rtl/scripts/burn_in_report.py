#!/usr/bin/env python3
"""burn_in_report.py -- a run's log turned into the normal it establishes.

    python3 rtl/scripts/burn_in_report.py cosmictera-build/burn-in/<id>.jsonl

The owner's reason for this tier, in his own words: *"Anomali tidak bisa
didefinisikan tanpa mengetahui normal."* A run that ends with "0 errors" says
the machine did not break. It does not yet say what the machine's ordinary
behaviour LOOKS like, and that is the number the monitoring layer will later
have to compare against.

So this reads a run and states the normal it found: how fast the work goes, how
far apart the beats are, how the board's own clock tracks the host's, and where
the outliers were. It writes <id>-baseline.json beside the log so a later run,
or NUI, can hold its numbers against these rather than against a feeling.

-- a silence has two possible owners --------------------------------------
The host measures the gap between beats it PARSED, and a machine that stopped
and a host that stopped reading look identical in that number. They are not
identical in the log, because every beat carries the board's own clock:

  the host stopped    the beats after the gap are OLD -- the board's clock
                      lags the host's, then catches up as the backlog drains
  the board stopped   the beat after the gap is CURRENT -- the board's clock
                      tracks the host's, and the beat COUNT barely moved

So each gap is classified rather than reported bare. Measured 20 September
2026 on the 24-hour run: a 140-second silence at 14,496 s was the host's --
the board's clock had fallen 138 seconds behind and recovered within a minute,
and 127 beats drained in the 61 seconds after. The board never stopped. A
report that called that "the machine hung for two minutes" would have been
wrong in the one direction that matters.

-- one number is the host's, not the board's -----------------------------
The interval between beats as MEASURED here is quantised by the host's serial
read timeout: tier 1 ran with a one-second timeout, so its intervals pile up
at 1.0 and 2.0 seconds although the board beats every 1.58. The honest board
number is derived instead -- 1024 cycles divided by the measured cycle rate --
and it is reported as such. Later runs use a shorter timeout, so their
intervals will be nearer the truth; that does not change what tier 1 measured,
and tier 1's figure is not quietly re-labelled.

-- what the numbers rest on ----------------------------------------------
The log is not every heartbeat. burn_in.py writes one sample a minute plus
every anomaly, because a day of beats is hundreds of thousands of lines saying
the same thing. So the interval and rate statistics here are over the SAMPLED
beats and are named as such; the counters -- errors, unfinished card reads,
the longest silence -- come from the run's own summary and cover every beat.
Saying which is which is the difference between a baseline and a guess.
"""
from __future__ import annotations

import argparse
import json
from itertools import pairwise
from pathlib import Path

OSC_HZ = 27_000_000
WRAP_S = 2 ** 32 / OSC_HZ
COUNTER_SHIFT = 12


def uptime_s(wraps: int, counter_hi: int) -> float:
    """burn_in.py's, repeated here so a log can be read without a board."""
    return wraps * WRAP_S + (counter_hi << COUNTER_SHIFT) / OSC_HZ

ROOT = Path(__file__).resolve().parents[2]
HEARTBEAT_CYCLES = 1024      # burn_in.py's, and burn_in.hasm's


def percentile(values: list[float], p: float) -> float:
    """The p-th percentile, nearest rank -- no interpolation, no numpy."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = max(1, min(len(ordered), round(p / 100 * len(ordered))))
    return ordered[rank - 1]


def spread(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "min": min(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def read(path: Path) -> tuple[list[dict], dict]:
    lines = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    summary_path = path.with_suffix(".json")
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    return lines, summary


def classify_gaps(lines: list[dict]) -> list[dict[str, object]]:
    """Whose silence each gap was -- the board's or the host's."""
    carrying = [ln for ln in lines if "counter_hi" in ln]
    out = []
    for i, ln in enumerate(carrying):
        if ln["kind"] != "gap" or i == 0:
            continue
        before = carrying[i - 1]
        host = ln["host_s"] - before["host_s"] if "host_s" in ln else float(ln["gap"])
        board = (uptime_s(ln["wraps"], ln["counter_hi"])
                 - uptime_s(before["wraps"], before["counter_hi"]))
        beats = ln["heartbeats"] - before["heartbeats"]
        whose = ("the host" if board < 0.5 * host else
                 "the board" if beats <= 2 else "unclear")
        out.append({"at_s": round(ln["t"], 1), "silence_s": float(ln["gap"]),
                    "host_advance_s": round(host, 1),
                    "board_advance_s": round(board, 1),
                    "beats_advanced": beats, "whose": whose})
    return out


def baseline(lines: list[dict], summary: dict) -> dict[str, object]:
    samples = [ln for ln in lines if ln["kind"] == "sample"]
    if len(samples) < 2:
        raise ValueError("a baseline needs at least two samples")

    gaps = [float(s["gap"]) for s in samples]
    silences = classify_gaps(lines)
    # A rate measured across a silence is not a work rate. During a host stall
    # the cycles are real and the host's seconds are spent waiting; in the
    # minute after, the backlog drains and the same ratio comes out four times
    # too high. On 20 September one stall produced both 188.9 and 2,121.5
    # cycles per second. An interval is set aside when the board's own clock
    # and the host's disagree about how long it was -- which is the event
    # itself, not a guess at where it was.
    rates, drifts, skipped = [], [], 0
    for a, b in pairwise(samples):
        span = b["host_s"] - a["host_s"]
        board_span = b["board_s"] - a["board_s"]
        if span <= 0:
            continue
        if abs(board_span - span) > 0.2 * span:
            skipped += 1
        else:
            rates.append((b["cycles"] - a["cycles"]) / span)
        drifts.append(b["board_s"] - b["host_s"])

    first, last = samples[0], samples[-1]
    hours = (last["host_s"] - first["host_s"]) / 3600
    return {
        "source": summary.get("started"),
        "ended": summary.get("ended"),
        "hours_covered_by_samples": round(hours, 3),
        "host_seconds": summary.get("host_seconds"),
        "board_seconds": summary.get("board_seconds"),
        # every beat, from the run's own counters
        "heartbeats": summary.get("heartbeats"),
        "cycles": summary.get("cycles"),
        "errors": summary.get("errors"),
        "sd_read_failures": summary.get("sd_read_failures"),
        "unparsed_lines": summary.get("unparsed_lines"),
        "longest_silence_s": summary.get("longest_gap_s"),
        "longest_silence_at_s": summary.get("longest_gap_at_s"),
        "silences": silences,
        "anomaly_lines": {kind: sum(1 for ln in lines if ln["kind"] == kind)
                          for kind in ("gap", "error", "unparsed", "launch")},
        # sampled beats only, and said so
        "sampled_beats": len(samples),
        "intervals_set_aside_for_silence": skipped,
        "heartbeat_interval_s_as_the_host_saw_it": spread(gaps),
        "cycles_per_second": spread(rates),
        # What the board actually does, free of the host's read timeout.
        "board_beat_period_s": round(HEARTBEAT_CYCLES / percentile(rates, 50), 4),
        "cycle_ms": round(1000 / percentile(rates, 50), 4),
        "board_minus_host_s": spread(drifts),
        "drift_per_hour_s": round(
            (drifts[-1] - drifts[0]) / hours, 4) if hours else None,
    }


def show(b: dict[str, object]) -> None:
    hb = b["heartbeat_interval_s_as_the_host_saw_it"]   # type: ignore[index]
    cps = b["cycles_per_second"]        # type: ignore[index]
    drift = b["board_minus_host_s"]     # type: ignore[index]
    print(f"{b['host_seconds']} s of host time, {b['board_seconds']} s by the "
          f"board's own counter")
    print(f"{b['heartbeats']} beats, {b['cycles']:,} cycles, "  # type: ignore[str-format]
          f"{b['errors']} error(s), {b['sd_read_failures']} unfinished card "
          f"read(s), {b['unparsed_lines']} unreadable line(s)")
    print(f"longest silence {b['longest_silence_s']} s "
          f"at {b['longest_silence_at_s']} s")
    for g in b["silences"]:          # type: ignore[union-attr]
        print(f"  {g['silence_s']:>7.1f} s at {g['at_s']:>9.1f} s -- {g['whose']}"
              f" (board moved {g['board_advance_s']} s while the host moved "
              f"{g['host_advance_s']} s, {g['beats_advanced']} beats)")
    print()
    print(f"over {b['sampled_beats']} sampled beats:")
    print(f"  interval       {hb['min']:.3f} / {hb['p50']:.3f} / {hb['p95']:.3f} "
          f"/ {hb['p99']:.3f} / {hb['max']:.3f} s   (min p50 p95 p99 max)")
    print(f"                 -- as the HOST saw it, quantised by its read "
          f"timeout; the board beats every {b['board_beat_period_s']} s")
    print(f"  cycles/second  {cps['min']:.1f} / {cps['p50']:.1f} / "
          f"{cps['p95']:.1f} / {cps['max']:.1f}   "
          f"({b['cycle_ms']} ms of work per cycle)")
    if b["intervals_set_aside_for_silence"]:
        print(f"                 -- {b['intervals_set_aside_for_silence']} "
              f"interval(s) set aside for containing a silence")
    print(f"  board - host   {drift['min']:.1f} to {drift['max']:.1f} s, "
          f"{b['drift_per_hour_s']} s per hour")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log", type=Path, help="a run's .jsonl")
    ap.add_argument("--write", action="store_true",
                    help="also write <id>-baseline.json beside the log")
    args = ap.parse_args(argv)

    lines, summary = read(args.log)
    b = baseline(lines, summary)
    show(b)
    if args.write:
        out = args.log.with_name(args.log.stem + "-baseline.json")
        out.write_text(json.dumps(b, indent=2) + "\n")
        print(f"\nbaseline: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
