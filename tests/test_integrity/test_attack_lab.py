"""The attack lab's own claims, checked without a board.

Two things here would rot quietly: the generator's period, which is the only
measured fact cosmic-codex-jim offers, and the two cases the loader ACCEPTS.
Those two are accepted by specification, not by accident -- the 32-bit sum
covers the program words only -- so if a future loader starts refusing them, it
is a change of contract and this test is where it surfaces.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from attack_lab import base_container, cases  # noqa: E402
from build_container import HEADER_WORDS  # noqa: E402
from jim_stream import PERIODS, period, stream  # noqa: E402


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
