"""The oscillator bank in `WAVE.md` is derived, and this is what enforces it.

The table on that page was transcribed once and drifted: it tabulated matrix
order and called the numbers frequencies, and for six letters those are not
the same thing. Nothing recomputed it, so nothing could notice -- the error
was found by hand, months later, and only because a separate assertion
happened to fail.

`hijaiyyah.receiver.tabulate` removes the transcription. These tests are the
part that makes it binding: the page must equal what the machine produces,
and the reconciler must actually catch a page that does not. The second half
matters as much as the first -- a checker that passes on everything would be
worse than no checker, because it would look like coverage.
"""
from __future__ import annotations

import pathlib

from hijaiyyah.receiver.identify import MATRIX_ORDERS, MOTIFS, WIRE_PERIODS
from hijaiyyah.receiver.tabulate import (
    matrix_bank,
    parse_bank,
    reconcile,
    render_bank,
    wire_bank,
)

WAVE_MD = pathlib.Path(__file__).resolve().parents[2] / "cosmic-codex-jim" / "WAVE.md"


def test_wave_md_table_is_derived_not_transcribed() -> None:
    """The page and the exomatrices must agree, row for row.

    A failure here is not a bug in the code: it means the page is stale.
    Re-print it with `PYTHONPATH=src python3 -m hijaiyyah.receiver.tabulate`
    and paste the wire bank over the old one.
    """
    disagreements = reconcile(WAVE_MD.read_text(encoding="utf-8"))
    assert disagreements == (), "\n".join(
        f"  period {d.period}: {d.field} -- page says {d.documented!r}, "
        f"machine says {d.derived!r}" for d in disagreements)


def test_the_reconciler_catches_the_table_it_was_written_for() -> None:
    """The old table, fed back in, must be rejected -- and named precisely.

    This is the exact content that shipped for months. If the reconciler
    passed it, every other test on this page would be decoration.
    """
    stale = """
| periode | frekuensi | n | huruf |
|---:|---:|---:|---|
| 1 | **diam** | 16 | ا ت ث د ر س ش ص ض ع ق ك ن و هـ ي |
| 2 | 13,500 MHz | 2 | ح ل |
| 3 | 9,000 MHz | 7 | ذ ز ط ظ غ ف م |
| 4 | 6,750 MHz | 1 | ب |
| **31** | **0,871 MHz** | 2 | **ج خ** |
"""
    found = reconcile(stale)
    assert found, "the reconciler accepted the table it exists to reject"

    by_period = {(d.period, d.field) for d in found}
    assert (1, "letters") in by_period, "the silent row was not flagged"
    assert (2, "period") in by_period, "period 2 does not exist on the wire"
    assert (4, "period") in by_period, "period 4 does not exist on the wire"
    assert (3, "letters") in by_period, "the 9 MHz row lost three letters"
    assert not any(d.period == 31 for d in found), (
        "period 31 was always right; flagging it would be a false positive")


def test_a_correct_table_is_not_flagged() -> None:
    """The other half of the check: no false positives on freshly rendered output."""
    assert reconcile(render_bank(wire_bank())) == ()


def test_rendering_and_parsing_round_trip_to_display_precision() -> None:
    """Periods and letters survive exactly; frequency survives to 1 kHz.

    Not written as a plain inverse, because it is not one: the table prints
    three decimals of MHz, so 870_967.74 comes back as 871_000. That is the
    page's resolution rather than a defect, and `reconcile` compares rendered
    text for the same reason -- but the claim has to say so instead of
    asserting an equality that only looks true.
    """
    parsed = parse_bank(render_bank(wire_bank()))
    derived = wire_bank()

    assert [r.period for r in parsed] == [r.period for r in derived]
    assert [r.letters for r in parsed] == [r.letters for r in derived]
    for got, want in zip(parsed, derived, strict=True):
        assert abs(got.hz - want.hz) <= 500.0, f"period {want.period}"
        assert got.silent == want.silent


def test_the_matrix_bank_carries_no_frequency_column() -> None:
    """Filling it in is the substitution the whole module exists to prevent."""
    rendered = render_bank(matrix_bank(), frequency=False)
    assert "MHz" not in rendered and "diam" not in rendered
    assert rendered.splitlines()[0] == "| orde | n | huruf |"
    assert all(row.hz == 0.0 for row in matrix_bank())


def test_the_two_banks_disagree_on_exactly_six_letters() -> None:
    wire = {row.period: row.n for row in wire_bank()}
    matrix = {row.period: row.n for row in matrix_bank()}
    assert wire == {1: 22, 3: 4, 31: 2}
    assert matrix == {1: 16, 2: 2, 3: 7, 4: 1, 31: 2}

    disagree = sorted(c for c in MOTIFS if MATRIX_ORDERS[c] != WIRE_PERIODS[c])
    assert disagree == sorted(["ب", "ح", "ط", "ظ", "ل", "م"])
    assert sum(wire.values()) == sum(matrix.values()) == 28


def test_every_letter_appears_in_each_bank_exactly_once() -> None:
    """A census, not a spot check -- a dropped letter is how the last one hid."""
    for bank in (wire_bank(), matrix_bank()):
        letters = [c for row in bank for c in row.letters]
        assert len(letters) == 28 and len(set(letters)) == 28
        assert set(letters) == set(MOTIFS)
