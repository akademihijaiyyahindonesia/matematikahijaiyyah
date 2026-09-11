"""Testing "Point -> Transform -> Line" as an ORDER effect, not a slogan.

nui/dataset.py already proved v18 accumulation is order-independent, so
this uses a genuinely order-sensitive operation -- GF(2) matrix
multiplication of letters' exomatrices -- to ask whether composing letters
titik-first, garis-last (the shape the external "Codex NUI" document's
formula gestures at without ever defining precisely enough to test)
produces a different result than a random order of the same letters.

It does not, robustly. A first configuration looked promising (52.7% of
non-tied paired comparisons favoured pipeline order); replicating across
other size ranges and seeds flips the direction (down to 37.5% in one
config) rather than confirming it -- the signature of noise, not a real
effect. This file locks those specific numbers to the code that produces
them, including the instability itself.
"""
from __future__ import annotations

from hijaiyyah.core.exomatrix import compose_mod, gf2_rank
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.nui.pattern_language import (
    ALL_CHARS,
    composed_rank,
    pipeline_order,
    run_trials,
    summarize,
)

ENTRIES = {e.char: e for e in MASTER_TABLE.all_entries()}


def test_pipeline_order_sorts_titik_heavy_first():
    order = pipeline_order(("ا", "ج", "د"))  # Alif(0,1,0) Jim(1,1,1) Dal(0,0,1)
    # titik-garis: Alif=-1, Jim=0, Dal=0 -- Jim/Dal tie, broken by Master
    # Table index (Jim=5 before Dal=8), Alif (titik-garis most negative)
    # sorts LAST under "descending -(titik-garis)".
    assert order == ("ج", "د", "ا")


def test_composed_rank_matches_direct_computation():
    letters = ("ج", "ا", "خ")
    expected = gf2_rank(compose_mod([ENTRIES[c].vector for c in letters], 2))
    assert composed_rank(letters) == expected


def test_composition_is_order_sensitive_on_about_a_third_of_pairs():
    """Confirmed before any hypothesis was tested, not assumed -- see
    pattern_language.py's own module docstring. Locks the exact count."""
    diff = 0
    total = 0
    for i, a in enumerate(ALL_CHARS):
        for b in ALL_CHARS[i + 1:]:
            total += 1
            r1 = composed_rank((a, b))
            r2 = composed_rank((b, a))
            if r1 != r2:
                diff += 1
    assert total == 378  # 28 choose 2
    assert diff == 118  # unordered pairs where SOME ordering differs... see below


def test_ordered_pair_asymmetry_count():
    """The 236-of-756 figure this module's docstring quotes: every ORDERED
    pair (i, j), i != j, both directions counted separately."""
    diff = 0
    total = 0
    for a in ALL_CHARS:
        for b in ALL_CHARS:
            if a == b:
                continue
            total += 1
            if composed_rank((a, b)) != composed_rank((b, a)):
                diff += 1
    assert total == 756
    assert diff == 236


def test_run_trials_is_reproducible():
    a = run_trials(subsets=30, shuffles_per_subset=20, min_size=3, max_size=5, seed=0)
    b = run_trials(subsets=30, shuffles_per_subset=20, min_size=3, max_size=5, seed=0)
    assert a == b


def test_the_effect_is_small_and_flips_direction_across_configurations():
    """The actual finding: not a consistent effect in either direction.
    Two configurations, run at reduced scale for test speed -- large enough
    to keep the qualitative result (favours pipeline order in one config,
    favours random order in the other), not the exact percentages this
    module's docstring quotes at full scale.
    """
    favouring_pipeline = run_trials(
        subsets=600, shuffles_per_subset=40, min_size=3, max_size=5, seed=0
    )
    favouring_random = run_trials(
        subsets=600, shuffles_per_subset=40, min_size=2, max_size=2, seed=0
    )

    def frac_pipeline_wins(trials) -> float:
        pos = neg = 0
        for t in trials:
            rmean = sum(t.random_ranks) / len(t.random_ranks)
            if t.pipeline_rank > rmean:
                pos += 1
            elif t.pipeline_rank < rmean:
                neg += 1
        return pos / (pos + neg) if (pos + neg) else float("nan")

    frac_a = frac_pipeline_wins(favouring_pipeline)
    frac_b = frac_pipeline_wins(favouring_random)

    # The instability itself is the finding: one configuration leans
    # (mildly) toward pipeline order, the other leans toward random order.
    assert frac_a > 0.5, f"expected size 3-5 to lean pipeline-favouring, got {frac_a}"
    assert frac_b < 0.5, f"expected size-2 to lean random-favouring, got {frac_b}"

    # And neither lean is large -- a real, robust effect would not need
    # replication across configurations to even see its sign agree.
    assert abs(frac_a - 0.5) < 0.15
    assert abs(frac_b - 0.5) < 0.30


def test_summarize_reports_both_the_mean_and_the_percentile_view():
    trials = run_trials(subsets=50, shuffles_per_subset=20, min_size=3, max_size=5, seed=0)
    s = summarize(trials)
    assert s.n_trials == 50
    assert s.pipeline_rank_higher + s.pipeline_rank_lower + s.pipeline_rank_tied == 50
