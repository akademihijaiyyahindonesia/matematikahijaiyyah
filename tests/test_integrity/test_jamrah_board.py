"""The jamrah lab, held to what it claims before a board ever sees it.

rtl/scripts/jamrah_board.py generates the program the board runs from
rtl/programs/jamrah_gate.hasm, runs it, and compares all 256 answers -- the
pulse and the seven internal nodes -- with rtl/tb/jamrah_vectors.txt. These
tests pin the three things that would let it agree with itself while being
wrong: a generator that stops copying the gate, a comparison that cannot fail,
and a parser that loses a line quietly.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from jamrah_board import (  # noqa: E402
    GATE,
    compare,
    gate_body,
    parse,
    reference,
    run_interpreter,
    sweep_program,
)


def test_the_board_runs_the_gate_the_file_defines_twice_verbatim() -> None:
    source = GATE.read_text(encoding="utf-8")
    body = "\n".join(gate_body(source))
    program = sweep_program(source)
    assert program.count(body) == 2, "the timed pass and the printed pass"
    assert "MOVI  R1, 0xB5" not in program, "the fixed test byte must not survive"


def test_all_256_bytes_agree_in_the_interpreter() -> None:
    values = run_interpreter(sweep_program(GATE.read_text(encoding="utf-8")))
    agree, bad = compare(values[1:])
    assert agree == 256, bad[:3]


def test_the_reference_is_the_one_the_rtl_bench_reads() -> None:
    rows = reference()
    assert len(rows) == 256
    assert sum(r[1] for r in rows) == 28, "exactly the 28 letters pass"
    assert all(r[8] == bin(r[0]).count("1") for r in rows), "n6 is the popcount"


def test_a_gate_broken_at_one_node_is_seen() -> None:
    """R3: one level-2 node computed wrong must turn the comparison red."""
    source = GATE.read_text(encoding="utf-8")
    broken = source.replace("ADD   R10, R6, R7", "SUB   R10, R6, R7", 1)
    assert broken != source
    agree, _ = compare(run_interpreter(sweep_program(broken))[1:])
    assert agree < 256


def test_the_parser_drops_and_counts_non_printing_bytes() -> None:
    values, dropped, rejected = parse(b"\x00\xff9218\n0\n1\n")
    assert values == [9218, 0, 1] and dropped == 2 and rejected == []


def test_the_parser_reports_a_line_it_cannot_read() -> None:
    """The loss that happened once on the board must never be quiet again."""
    values, dropped, rejected = parse(b"92x18\n0\n")
    assert values == [0] and dropped == 0 and rejected == [b"92x18"]
