"""Testing an external reference document's claims, not repeating them.

"Codex NUI 1.1.1 ORBIT" was supplied as reference material for the nui/
work. Most of it is unfalsifiable (Quranic verses cited as evidence for a
rotation angle; the same 270 degrees applied to DNA, planets, brainwaves,
and emotions with no derivation) and none of that is encoded anywhere in
this repo. Two things in it ARE testable against the sealed Master Table --
see claims.py's module docstring -- and both come back negative. This file
locks those numbers to the code that produces them, the same discipline
tests/test_integrity/test_cosmic_codex_jim.py already applies to a much
more careful document about the same letter.
"""
from __future__ import annotations

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.nui.claims import (
    DOCUMENT_ANGLE_CLAIMS,
    LETTER_GROUPS,
    actual_theta_degrees,
    check_angle_claims,
    group_coherence,
)


def test_every_claimed_letter_is_a_real_master_table_entry():
    chars = {e.char for e in MASTER_TABLE.all_entries()}
    for claim in DOCUMENT_ANGLE_CLAIMS:
        assert claim.letter in chars, claim
    for group in LETTER_GROUPS.values():
        for ch in group:
            assert ch in chars, ch


def test_actual_theta_matches_jims_own_established_fact():
    """cosmic-codex-jim/'s own number, cross-checked here: Jim's Theta-hat
    is 3, times the 90-degree quantum, is 270."""
    assert actual_theta_degrees("ج") == 270


def test_the_angle_claims_are_mostly_wrong():
    """The measured verdict: 2 of 7 explicit AMM angle claims in the
    document match the Master Table's own Theta-hat; the other 5 do not."""
    results = check_angle_claims()
    matches = sum(1 for _claim, _actual, ok in results if ok)
    assert len(results) == 7
    assert matches == 2

    mismatched = {claim.letter for claim, _actual, ok in results if not ok}
    assert mismatched == {"ر", "ق", "ض", "ص", "ن"}


def test_jim_and_dal_are_the_two_that_actually_match():
    results = {claim.letter: ok for claim, _actual, ok in check_angle_claims()}
    assert results["ج"] is True
    assert results["د"] is True


def test_neither_claimed_group_is_more_coherent_than_a_random_group():
    """A real structural claim would put the observed group in the LOW
    percentiles (tightly clustered relative to random same-size draws).
    Both land near the middle of the random distribution -- statistically
    indistinguishable from picking that many letters by chance. Loose
    bounds (20-80%) because the permutation draw is randomised; the point
    is "not extreme in either direction," not an exact percentile.
    """
    for result in group_coherence(samples=4000, seed=1):
        assert 20.0 <= result.percentile <= 80.0, (
            f"{result.group} looks more structured than expected -- "
            f"re-examine before this test is loosened further: {result}"
        )


def test_group_coherence_is_reproducible():
    a = group_coherence(samples=500, seed=7)
    b = group_coherence(samples=500, seed=7)
    assert a == b
