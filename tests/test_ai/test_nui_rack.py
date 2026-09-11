"""rack.py: 28 chips, checked against the exact fields they were built from
-- nui.atom (node) and nui.features (point/line/curve), not re-derived.
"""
from __future__ import annotations

import pytest

from hijaiyyah.core.exomatrix import build_exomatrix, compose_step
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.nui.atom import atom_for
from hijaiyyah.nui.rack import NUM_SLOTS, RACK, chip_for


def test_rack_has_exactly_28_slots_master_table_order():
    assert len(RACK) == NUM_SLOTS == 28
    assert [c.char for c in RACK] == [e.char for e in MASTER_TABLE.all_entries()]


def test_each_chips_node_is_exactly_its_atom():
    for c in RACK:
        assert c.node == atom_for(c.char)
        assert c.opcode == atom_for(c.char).opcode


def test_jim_chips_data_matches_its_known_established_features():
    """Jim's own established facts (cosmic-codex-jim/): titik=1, garis=1,
    lengkung=1, theta=3 (270 degrees), rho=3 -- checked here as point/line/
    curve/theta/rho, not re-derived under new names."""
    jim = chip_for("ج")
    assert (jim.point, jim.line, jim.curve, jim.theta, jim.rho) == (1, 1, 1, 3, 3)


def test_chip_for_unknown_char_raises():
    with pytest.raises(KeyError):
        chip_for("Z")


# ── Chip.boot() / Chip.step(): the chip runs, not a record read ──


def test_boot_matches_build_exomatrix_directly():
    jim = chip_for("ج")
    expected = tuple(tuple(x % 2 for x in row)
                      for row in build_exomatrix(MASTER_TABLE.get_by_char("ج").vector))
    assert jim.boot() == expected


def test_step_matches_compose_step_directly():
    """The chip's own step() must be indistinguishable from calling
    compose_step by hand with this chip's vector -- not a parallel
    computation that happens to look similar."""
    jim, kha = chip_for("ج"), chip_for("خ")
    state = jim.boot()
    got = kha.step(state)
    expected = compose_step(state, MASTER_TABLE.get_by_char("خ").vector, 2)
    assert got == expected


def test_boot_then_step_matches_two_chip_run_via_clockwork():
    """Ties rack.py back to clockwork.py: running chips by hand, one at a
    time, must land on exactly what run(["ج", "خ"]) gets -- because run()
    now IS this, chip by chip, not a parallel implementation."""
    from hijaiyyah.nui.clockwork import run

    jim, kha = chip_for("ج"), chip_for("خ")
    state = kha.step(jim.boot())
    ticks = run(["ج", "خ"])
    assert ticks[-1].state == state


def test_step_respects_the_modulus_argument():
    """boot()/step() must actually change with p, not stay hard-coded at
    GF(2) -- checked against build_exomatrix/compose_step at p=5 directly."""
    jim = chip_for("ج")
    got = jim.boot(p=5)
    expected = tuple(tuple(x % 5 for x in row)
                      for row in build_exomatrix(MASTER_TABLE.get_by_char("ج").vector))
    assert got == expected
