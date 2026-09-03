"""
Hisab al-Jummal against the measured codex: assigned value against measured
geometry, and how much of one survives in the other.

The lineage is the point. Letters carried numeric values for a very long time
-- abjad order, ا=1 through غ=1000 -- and al-Khwarizmi's work moved reckoning
off the letter and onto position, which is the road that ends at the digit and
then at the bit. Matematika Hijaiyyah goes back to the letter, but not to the
assigned number: it MEASURES the shape.

So the question is whether the old assignment knows anything about the
geometry. Measured: almost nothing, with one exact exception that turns out to
be historical rather than mathematical.
"""
from __future__ import annotations

import math
import statistics

from hijaiyyah.core.guards import _to_vec, compute_U
from hijaiyyah.core.master_table import MASTER_TABLE

# أبجد هوز حطي كلمن سعفص قرشت ثخذ ضظغ
JUMMAL = {
    "ا": 1, "ب": 2, "ج": 3, "د": 4, "هـ": 5, "و": 6, "ز": 7,
    "ح": 8, "ط": 9, "ي": 10, "ك": 20, "ل": 30, "م": 40, "ن": 50,
    "س": 60, "ع": 70, "ف": 80, "ص": 90, "ق": 100, "ر": 200,
    "ش": 300, "ت": 400, "ث": 500, "خ": 600, "ذ": 700,
    "ض": 800, "ظ": 900, "غ": 1000,
}

# The six Arabic added beyond the 22-letter Semitic abjad.
RAWADIF = ["ث", "خ", "ذ", "ض", "ظ", "غ"]

ENTRIES = MASTER_TABLE.all_entries()
BY_CHAR = {e.char: list(_to_vec(e)) for e in ENTRIES}


def _dots(char: str) -> int:
    v = BY_CHAR[char]
    return v[1] + v[2] + v[3]


def _corr(a: list[float], b: list[float]) -> float:
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def test_every_letter_has_a_jummal_value() -> None:
    assert len(JUMMAL) == 28 == len(ENTRIES)
    assert set(JUMMAL) == {e.char for e in ENTRIES}
    assert sorted(JUMMAL.values())[-1] == 1000


def test_the_assigned_value_does_not_predict_the_measured_turning() -> None:
    """
    The number a letter was given says nothing about how much it turns. U and
    rho -- the whole curvature account -- are uncorrelated with it.
    """
    logs = [math.log(JUMMAL[e.char]) for e in ENTRIES]
    vectors = [BY_CHAR[e.char] for e in ENTRIES]

    u = [float(compute_U(v)) for v in vectors]
    rho = [float(v[0] - compute_U(v)) for v in vectors]

    assert abs(_corr(logs, u)) < 0.20
    assert abs(_corr(logs, rho)) < 0.30


def test_the_one_component_it_does_track_is_dots_and_the_reason_is_history() -> None:
    """
    Na correlates about 0.6 with log(jummal), which looks like the old system
    knowing something. It is not: the abjad order inherits the 22-letter
    Semitic sequence, and the six letters Arabic ADDED are dotted variants of
    skeletons already in it. Being added, they were appended -- so they hold
    the six highest values and are dotted by construction.

    The correlation is the shape of how the alphabet grew, not a measurement
    anyone took.
    """
    logs = [math.log(JUMMAL[e.char]) for e in ENTRIES]
    na = [float(BY_CHAR[e.char][1]) for e in ENTRIES]
    assert 0.5 < _corr(logs, na) < 0.75

    order = sorted(JUMMAL, key=lambda c: JUMMAL[c])
    assert order[-6:] == RAWADIF
    assert all(_dots(c) > 0 for c in RAWADIF), "a rawadif letter lost its dots"

    lower = sum(_dots(c) for c in order[:14])
    upper = sum(_dots(c) for c in order[14:])
    assert upper > 2 * lower, f"{upper} against {lower}"

    # And the six lowest are mostly undotted, which is the same fact.
    assert sum(1 for c in order[:6] if _dots(c)) <= 2


def test_the_two_systems_disagree_about_which_letter_is_largest() -> None:
    """
    Plainest statement of the difference. Ghain is the largest by assignment,
    at 1000. By measured turning it is unremarkable, and the letter that turns
    most is Haa -- which the old system values at 5.
    """
    biggest_assigned = max(JUMMAL, key=lambda c: JUMMAL[c])
    biggest_measured = max(BY_CHAR, key=lambda c: BY_CHAR[c][0])

    assert biggest_assigned == "غ" and JUMMAL[biggest_assigned] == 1000
    assert biggest_measured == "هـ" and BY_CHAR[biggest_measured][0] == 8
    assert JUMMAL[biggest_measured] == 5
    assert biggest_assigned != biggest_measured
