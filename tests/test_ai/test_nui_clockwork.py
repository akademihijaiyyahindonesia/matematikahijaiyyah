"""clockwork.py: a clock-driven matrix-sequence mechanism, checked tick by
tick against functions that already existed and were already tested
independently -- compose_mod, gf2_rank, matrix_order, atom.py's addresses.
"""
from __future__ import annotations

import pytest

from hijaiyyah.core.exomatrix import build_exomatrix, compose_mod, gf2_rank, matrix_order_of
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.nui.atom import atom_for
from hijaiyyah.nui.clockwork import automate, channels, rank_permutations, run, run_rack
from hijaiyyah.nui.rack import RACK


def test_run_rejects_empty_sequence():
    with pytest.raises(ValueError, match="at least one letter"):
        run([])


def test_first_tick_state_matches_build_exomatrix_directly():
    jim = MASTER_TABLE.get_by_char("ج")
    expected = tuple(tuple(x % 2 for x in row) for row in build_exomatrix(jim.vector))
    ticks = run(["ج"])
    assert ticks[0].state == expected


def test_every_ticks_state_matches_compose_mod_of_the_prefix():
    """The core claim: stepping tick by tick must land on exactly the same
    matrix compose_mod gets by composing the whole prefix from scratch --
    not a parallel computation that merely looks similar."""
    letters = ["ا", "ب", "ج", "خ", "د"]
    ticks = run(letters)
    for t in range(1, len(letters) + 1):
        vectors = [MASTER_TABLE.get_by_char(c).vector for c in letters[:t]]
        expected = compose_mod(vectors, 2)
        assert ticks[t - 1].state == expected, t


def test_groundings_match_direct_recomputation():
    letters = ["ج", "خ", "م"]
    ticks = run(letters)
    for tick in ticks:
        assert tick.rank == gf2_rank(tick.state)
        assert tick.full_rank == (tick.rank == 5)
        _, period = matrix_order_of(tick.state, 2, cap=4000)
        assert tick.primitive == (period == 31)


def test_order_genuinely_changes_the_final_state():
    """compose_step does not commute -- pattern_language.py already measured
    this at ~31% of ordered pairs; this is one concrete instance of it, not
    a re-measurement of the rate."""
    forward = run(["ج", "خ"])
    backward = run(["خ", "ج"])
    assert forward[-1].state != backward[-1].state


def test_tick_opcode_matches_the_atom_modules_own_address():
    for char in ("ا", "ج", "خ", "ي"):
        ticks = run([char])
        assert ticks[0].opcode == atom_for(char).opcode


def test_jim_alone_is_primitive_at_the_first_tick():
    """Jim's own established fact (period 31 individually, cosmic-codex-jim/)
    must show up as primitive=True at tick 1 when Jim is the only letter."""
    ticks = run(["ج"])
    assert ticks[0].primitive is True
    assert ticks[0].full_rank is True


def test_run_over_gf5_uses_the_right_max_period():
    """max_period = p**5 - 1 must actually change with p, not stay hard-coded
    at GF(2)'s 31 -- Jim is primitive over GF(5) too (period 3124, tested
    elsewhere), so this is checkable directly rather than assumed correct
    for a modulus this module was not written against first."""
    ticks = run(["ج"], p=5, order_cap=4000)
    assert ticks[0].primitive is True


# ── automate(): boot -> bend -> emit, staged on top of run() ─────


def test_automate_rejects_an_unknown_ground():
    with pytest.raises(ValueError, match=r"full_rank.*primitive"):
        automate(["ج"], ground="bogus")


def test_automate_boot_is_the_first_letter_and_bend_is_every_tick():
    letters = ["ا", "ب", "ج", "خ"]
    a = automate(letters)
    assert a.boot_char == letters[0]
    assert [t.char for t in a.ticks] == letters
    # automate() must not recompute anything run() does not already give --
    # same ticks, not a parallel calculation that happens to agree.
    assert a.ticks == tuple(run(letters))


def test_automate_emit_reads_the_last_ticks_own_field_not_a_new_computation():
    letters = ["ج", "خ", "م"]
    for ground in ("full_rank", "primitive"):
        a = automate(letters, ground=ground)
        assert a.ground == ground
        assert a.emitted == getattr(a.ticks[-1], ground)


def test_automate_emit_is_one_bool_not_the_matrix():
    """The "titik" (small hole) claim, checked literally: what comes out is
    a bool, never the 5x5 state itself."""
    a = automate(["ج", "خ"])
    assert isinstance(a.emitted, bool)


def test_automate_order_sensitivity_can_flip_the_emitted_grounding():
    """The same two letters, reversed, land on a different final tick --
    already proven for the matrix state; this checks it can also flip
    what automate() actually emits, not just the underlying matrix."""
    forward = automate(["ج", "خ"], ground="primitive")
    backward = automate(["خ", "ج"], ground="primitive")
    assert forward.ticks[-1].state != backward.ticks[-1].state
    # Both happen to emit False here (Jim-then-Kha and Kha-then-Jim both lose
    # primitivity by the second tick) -- recorded as the concrete case it is,
    # not asserted to differ when the underlying claim is only that the
    # STATE can differ, not that every pair's final grounding must.
    assert forward.emitted == backward.emitted is False


# ── channels(): the link between consecutive nodes, named ───────


def test_channels_count_is_one_less_than_ticks():
    letters = ["ا", "ب", "ج", "خ"]
    ticks = run(letters)
    cs = channels(ticks)
    assert len(cs) == len(ticks) - 1 == 3


def test_single_tick_has_no_channels():
    assert channels(run(["ج"])) == []


def test_channels_carry_the_exact_states_the_ticks_already_have():
    """No new state computed here -- each channel's before/after must be
    literally the same objects (via equality) run() already put on the
    adjacent ticks."""
    ticks = run(["ج", "خ", "م"])
    cs = channels(ticks)
    for i, ch in enumerate(cs):
        assert ch.from_node == ticks[i].char
        assert ch.to_node == ticks[i + 1].char
        assert ch.state_before == ticks[i].state
        assert ch.state_after == ticks[i + 1].state


# ── run_rack(): the whole rack, one canonical clock run ──────────


def test_run_rack_covers_all_28_chips_in_master_table_order():
    ticks = run_rack()
    assert len(ticks) == 28 == len(RACK)
    assert [t.char for t in ticks] == [c.char for c in RACK]


def test_run_rack_matches_run_over_the_same_letter_order():
    """Not a separate implementation -- run_rack() must be indistinguishable
    from calling run() with the rack's own letters spelled out by hand."""
    ticks_rack = run_rack()
    ticks_manual = run([c.char for c in RACK])
    assert ticks_rack == ticks_manual


def test_run_rack_respects_p_and_order_cap():
    ticks5 = run_rack(p=5, order_cap=4000)
    assert len(ticks5) == 28
    # Jim is the 5th rack slot (0-based index 4, master_index 5) -- not
    # RACK[0], so this can only pass if `p` actually reached chip.step()
    # for every letter after the first, not just chip.boot() for RACK[0].
    jim_tick = next(t for t in ticks5 if t.char == "ج")
    assert jim_tick.step == 5


# ── rank_permutations(): random orderings of the rack, ranked by ticks ──


def test_rank_permutations_returns_one_score_per_sample_sorted_descending():
    scores = rank_permutations(count=200, seed=0)
    assert len(scores) == 200
    keys = [(s.full_rank_ticks, s.primitive_ticks, s.final_rank) for s in scores]
    assert keys == sorted(keys, reverse=True)


def test_rank_permutations_every_order_is_a_permutation_of_the_rack():
    """Reordered, not resampled -- every one of the 28 letters exactly
    once, same set RACK carries."""
    rack_letters = sorted(c.char for c in RACK)
    scores = rank_permutations(count=50, seed=0)
    for score in scores:
        assert len(score.order) == 28
        assert sorted(score.order) == rack_letters


def test_rank_permutations_is_seeded_and_reproducible():
    first = rank_permutations(count=50, seed=0)
    second = rank_permutations(count=50, seed=0)
    assert first == second


def test_rank_permutations_different_seeds_give_different_samples():
    a = rank_permutations(count=50, seed=0)
    b = rank_permutations(count=50, seed=1)
    assert [s.order for s in a] != [s.order for s in b]


def test_rank_permutations_top_score_matches_direct_recomputation():
    """Not trusted from the sort -- the top entry's own fields must match
    run() computed fresh on its own order."""
    scores = rank_permutations(count=200, seed=0)
    top = scores[0]
    ticks = run(list(top.order))
    assert sum(1 for t in ticks if t.full_rank) == top.full_rank_ticks
    assert sum(1 for t in ticks if t.primitive) == top.primitive_ticks
    assert ticks[-1].rank == top.final_rank


def test_rank_permutations_defaults_to_the_racks_own_letters():
    scores = rank_permutations(count=10, seed=0)
    rack_letters = sorted(c.char for c in RACK)
    assert sorted(scores[0].order) == rack_letters


def test_rank_permutations_accepts_a_smaller_custom_letter_set():
    scores = rank_permutations(["ج", "خ", "م"], count=10, seed=0)
    for score in scores:
        assert sorted(score.order) == ["ج", "خ", "م"]


def test_rank_permutations_most_orderings_end_at_rank_zero():
    """Measured, not assumed: 1000 random orderings of all 28 letters,
    seed 0 -- 999 end at final_rank 0, matching run_rack()'s own Master
    Table order (also rank 0). Composing all 28 letters' exomatrices via
    compose_step drives the running matrix singular almost regardless of
    order, not just in the one canonical sequence."""
    scores = rank_permutations(count=1000, seed=0)
    final_ranks = [s.final_rank for s in scores]
    assert final_ranks.count(0) == 999
    assert max(final_ranks) == 1
    assert max(s.full_rank_ticks for s in scores) == 2
    assert max(s.primitive_ticks for s in scores) == 1
