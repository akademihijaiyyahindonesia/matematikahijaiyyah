"""The attack lab's own claims, checked without a board.

Three things here would rot quietly: the generator's period, which is the only
measured fact cosmic-codex-jim offers; the two cases the loader ACCEPTS, which
are accepted by specification rather than by accident -- the 32-bit sum covers
the program words only -- so a future loader that starts refusing them has
changed its contract; and the control the timing class leans on, which proves
nothing unless it really does take a different number of steps for different
bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from attack_lab import (  # noqa: E402
    CHAIN_CONTROL,
    JimSource,
    base_container,
    cases,
    jamrah_measure,
    jim_cases,
    timed_sweep,
)
from build_container import HEADER_WORDS  # noqa: E402
from jamrah_board import GATE, gate_body  # noqa: E402
from jim_stream import PERIODS, period, stream  # noqa: E402

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.assembler import assemble  # noqa: E402
from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402


def _sweep(inner: str) -> dict[str, object]:
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble(timed_sweep(inner)))
    machine.run()
    return jamrah_measure(list(machine.output), "instructions")


def test_jim_reaches_the_period_cosmic_codex_jim_records() -> None:
    for field, want in PERIODS.items():
        assert period(field) == want, field


def test_the_stream_is_deterministic_and_repeats_with_its_period() -> None:
    """A generator whose bytes depend on anything unstated cannot be a
    reproducible test case."""
    assert stream(2, 64) == stream(2, 64)
    over_gf2 = stream(2, 31 * 5 // 8 + 1)
    assert len(set(over_gf2)) > 1, "a constant stream would test nothing"


def test_every_case_damages_exactly_one_word() -> None:
    container = base_container()
    for case in cases(container):
        word = int(case["word"])  # type: ignore[call-overload]
        assert 0 <= word < len(container)
        assert int(case["value"]) & 0xFFFFFFFF != container[word], case["id"]  # type: ignore[call-overload]


def test_the_two_cases_outside_the_checksum_are_named_as_accepted() -> None:
    """The sum covers program words only, so a damaged relocation table and a
    WORDS that reaches into the sector's zero padding both pass. Measured on
    the board, 20 September 2026, and predicted from the loader's own code."""
    by_id = {c["id"]: c for c in cases(base_container())}
    assert by_id["reloc_index_moved"]["expect"] == "accept"
    assert by_id["words_plus_one"]["expect"] == "accept"
    assert int(by_id["reloc_index_moved"]["word"]) == HEADER_WORDS  # type: ignore[call-overload]
    rejects = [c for c in cases(base_container()) if c["expect"] == "reject"]
    assert len(rejects) == 8


def test_the_timed_sweep_carries_the_gate_body_verbatim() -> None:
    """One definition, not two: the timed program is the gate file's body."""
    body = gate_body(GATE.read_text(encoding="utf-8"))
    program = timed_sweep("\n".join(body))
    for line in body:
        assert line in program


def test_the_gate_takes_the_same_count_for_every_byte() -> None:
    """The claim rtl/programs/jamrah_gate.hasm makes in its own comment. The
    board says 33 clocks; the interpreter counts instructions, and the unit
    that matters here is only that there is ONE of them."""
    measured = _sweep("\n".join(gate_body(GATE.read_text(encoding="utf-8"))))
    assert measured["distinct_counts"] == 1
    assert measured["accepted"] == 28
    assert measured["rejected"] == 228
    assert measured["pulse_disagreements"] == []


def test_the_control_gives_the_same_answer_and_leaks_its_input() -> None:
    """Without this, a constant reading from the gate would prove only that
    the harness cannot see a difference (R3)."""
    control = _sweep(CHAIN_CONTROL)
    assert control["accepted"] == 28
    assert control["pulse_disagreements"] == []
    assert control["distinct_counts"] > 1, "a control that cannot leak proves nothing"
    assert control["max"] > 4 * control["min"]  # type: ignore[operator]


def test_the_codex_source_repeats_exactly_and_knows_its_own_period() -> None:
    first = [JimSource(5).randrange(256) for _ in range(64)]
    again = [JimSource(5).randrange(256) for _ in range(64)]
    assert first == again
    for field, want in JimSource.BYTE_PERIOD.items():
        data = stream(field, want * 2 + 512)
        assert data[:512] == data[want:want + 512], field
        assert not any(data[:512] == data[n:n + 512] for n in range(1, want))


def test_codex_cases_only_damage_words_the_sum_reaches() -> None:
    """Their prediction is `reject` for all of them, so they must land where
    the 32-bit sum looks: the program words, never the header."""
    container = base_container()
    first = HEADER_WORDS + container[5]
    plan = jim_cases(container, JimSource(5), 16)
    assert len({c["id"] for c in plan}) == 16
    for case in plan:
        word = int(case["word"])  # type: ignore[call-overload]
        assert first <= word < len(container)
        assert case["value"] != container[word]
        assert case["expect"] == "reject"
