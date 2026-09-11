"""From the machine to the table, automatically -- so a doc cannot drift again.

`identify.py` records a correction: `cosmic-codex-jim/WAVE.md` tabulated
matrix order and described it as the frequency each letter emits, and for
six letters those are different numbers. The error survived because the
table was **transcribed**. Nothing recomputed it, so nothing could notice.

This module removes the transcription step. The bank is derived from the
exomatrices every time it is asked for, rendered as the table the document
carries, and compared against what the document actually says. A disagreement
is reported as rows, with the derived table ready to replace them -- so the
next mismatch is caught by a test rather than by someone reading carefully.

Two banks are produced, because both quantities are real:

    wire        what a receiver measures  -- {1: 22, 3: 4, 31: 2}
    matrix      order of M over GF(2)     -- {1: 16, 2: 2, 3: 7, 4: 1, 31: 2}

The wire bank is the one that may be labelled a frequency.

Run it directly to print the current tables:

    python3 -m hijaiyyah.receiver.tabulate
"""
from __future__ import annotations

import collections
import re
from typing import Dict, List, NamedTuple, Tuple

from ..core.master_table import MASTER_TABLE
from .identify import BOARD_CLOCK_HZ, MATRIX_ORDERS, MOTIFS, WIRE_PERIODS, tone_hz

__all__ = [
    "BankRow",
    "Disagreement",
    "matrix_bank",
    "parse_bank",
    "reconcile",
    "render_bank",
    "wire_bank",
]


class BankRow(NamedTuple):
    """One period of the oscillator bank."""

    period: int
    hz: float
    letters: Tuple[str, ...]

    @property
    def silent(self) -> bool:
        return self.hz == 0.0

    @property
    def n(self) -> int:
        """Named `n` because that is the column header it fills.

        It was `count`, which overrode `tuple.count` on a NamedTuple --
        so `row.count(x)` stopped counting occurrences and started
        returning the number of letters, whatever you asked it about.
        """
        return len(self.letters)


class Disagreement(NamedTuple):
    """A row where the document and the machine do not match."""

    period: int
    field: str
    documented: str
    derived: str


def _order() -> Dict[str, int]:
    return {e.char: i for i, e in enumerate(MASTER_TABLE.all_entries())}


def _bank(periods: Dict[str, int], as_frequency: bool) -> Tuple[BankRow, ...]:
    order = _order()
    grouped: Dict[int, List[str]] = collections.defaultdict(list)
    for char, period in periods.items():
        grouped[period].append(char)
    rows = []
    for period in sorted(grouped):
        letters = tuple(sorted(grouped[period], key=order.__getitem__))
        hz = 0.0
        if as_frequency:
            hz = tone_hz(letters[0])
        rows.append(BankRow(period, hz, letters))
    return tuple(rows)


def wire_bank() -> Tuple[BankRow, ...]:
    """What the alphabet emits. The only bank that may be called a frequency."""
    return _bank(WIRE_PERIODS, as_frequency=True)


def matrix_bank() -> Tuple[BankRow, ...]:
    """Order of each exomatrix. A real property, and not a frequency.

    Frequencies are left at 0.0 on purpose: filling them in is exactly the
    substitution that produced the error this module exists to prevent.
    """
    return _bank(MATRIX_ORDERS, as_frequency=False)


def _hz_text(hz: float) -> str:
    if hz == 0.0:
        return "**diam**"
    mhz = hz / 1_000_000
    return f"{mhz:.3f} MHz".replace(".", ",")


def render_bank(rows: Tuple[BankRow, ...] = (), frequency: bool = True) -> str:
    """The bank as the markdown table the document carries.

    `frequency=False` drops the column entirely rather than printing zeros
    in it. The matrix bank has no frequency, and a column of "diam" would
    read as a measurement instead of an absence.
    """
    rows = rows or wire_bank()
    longest = max(r.period for r in rows)
    if frequency:
        out = ["| periode | frekuensi | n | huruf |", "|---:|---:|---:|---|"]
    else:
        out = ["| orde | n | huruf |", "|---:|---:|---|"]
    for row in rows:
        em = "**" if row.period == longest else ""
        cells = [f"{em}{row.period}{em}"]
        if frequency:
            cells.append(_hz_text(row.hz))
        cells += [str(row.n), f"{em}{' '.join(row.letters)}{em}"]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


_ROW = re.compile(r"^\|\s*\*{0,2}(\d+)\*{0,2}\s*\|(.+?)\|\s*(\d+)\s*\|(.+?)\|\s*$")


def parse_bank(markdown: str) -> Tuple[BankRow, ...]:
    """Read a bank table back out of a document, for comparison."""
    rows = []
    for line in markdown.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            continue
        period, hz_text, _count, letters = match.groups()
        letters = tuple(letters.replace("*", "").split())
        hz = 0.0
        if "MHz" in hz_text:
            hz = float(hz_text.replace("*", "").replace("MHz", "")
                       .replace(",", ".").strip()) * 1_000_000
        rows.append(BankRow(int(period), hz, letters))
    return tuple(rows)


def reconcile(markdown: str,
              derived: Tuple[BankRow, ...] = ()) -> Tuple[Disagreement, ...]:
    """Every row where a document disagrees with the machine.

    Empty means the document is current. Anything else is the list of edits
    the document needs, and `render_bank()` produces the replacement.
    """
    derived = derived or wire_bank()
    documented = {row.period: row for row in parse_bank(markdown)}
    machine = {row.period: row for row in derived}
    found: List[Disagreement] = []

    for period in sorted(set(documented) | set(machine)):
        doc, mine = documented.get(period), machine.get(period)
        if mine is None:
            found.append(Disagreement(period, "period", "present", "absent"))
            continue
        if doc is None:
            found.append(Disagreement(period, "period", "absent", "present"))
            continue
        if doc.letters != mine.letters:
            found.append(Disagreement(period, "letters",
                                      " ".join(doc.letters), " ".join(mine.letters)))
        # Compared as rendered, not as raw Hz: the table prints three
        # decimals of MHz, so 870_967.7 and a documented 0,871 MHz are the
        # same row. Comparing floats flagged it as a disagreement and would
        # have taught the reader to ignore this report.
        if _hz_text(doc.hz) != _hz_text(mine.hz):
            found.append(Disagreement(period, "frequency",
                                      _hz_text(doc.hz), _hz_text(mine.hz)))
    return tuple(found)


def _main() -> None:  # pragma: no cover - a convenience entry point
    print(f"Bank kawat -- yang diukur penerima (clock {BOARD_CLOCK_HZ:,} Hz)\n")
    print(render_bank(wire_bank()))
    print("\n\nOrde matriks -- sifat nyata mesin, bukan frekuensi\n")
    print(render_bank(matrix_bank(), frequency=False))
    disagree = [c for c in MOTIFS if MATRIX_ORDERS[c] != WIRE_PERIODS[c]]
    print(f"\n\nHuruf yang keduanya berbeda: {' '.join(sorted(disagree))}")


if __name__ == "__main__":  # pragma: no cover
    _main()
