"""One negative vector per guard, and the two copies of them kept identical.

`HGRD` returning 0 says something was caught. It does not say WHAT, and for
five of the six guards nothing on this board could say it at all: index 31 was
the only corrupt entry in `hcpu_rom.v`, so silicon proved that G4 catches and
proved nothing about G1, G2, G3, T1 or T2.

Five more entries close that, and each one violates exactly one constraint --
the same discipline index 31 was built with, where A_Q is 2 rather than 0 so
that G3 does not fall alongside G4 and blur which guard fired. A vector that
trips two guards tests neither.

The second failure this file guards against already happened once, and its
scar is in machine.py: an index naming no ROM entry left the Python register
holding zeros, which is the monoid identity and passes every guard, so
`HLOAD H0, #31` reported PASS in software and FAIL on the HCPU. Modelling a
corrupt vector in one copy and not the other reopens exactly that gap, so both
copies are compared here rather than trusted to stay in step.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from hijaiyyah.core.guards import full_guard_check
from hijaiyyah.hisa.machine import ROM_NEGATIVE_VECTORS

ROOT = Path(__file__).resolve().parents[2]
ROM_V = (ROOT / "rtl" / "hcpu_rom.v").read_text(encoding="utf-8")
GUARDS = ("G1", "G2", "G3", "G4", "T1", "T2")


def _rom_vector(index: int) -> list[int]:
    """The 18 components carried at `index`, in vector order.

    The Verilog literal is written most-significant byte first, so it lists
    the vector backwards -- component 17 leftmost, Theta-hat last. Reading it
    forwards is how a hand-written entry silently becomes a different vector.
    """
    m = re.search(rf"\d+'d{index}: data_out = \{{(.*?)\}};", ROM_V, re.S)
    assert m, f"hcpu_rom.v carries no entry at index {index}"
    bytes_ = [int(x) for x in re.findall(r"8'd(\d+)", m.group(1))]
    assert len(bytes_) == 18, f"index {index} has {len(bytes_)} bytes, not 18"
    return list(reversed(bytes_))


@pytest.mark.parametrize(
    "index,guard",
    [(i, g) for i, (_, g) in sorted(ROM_NEGATIVE_VECTORS.items())],
)
def test_each_negative_vector_fails_exactly_one_guard(index: int, guard: str) -> None:
    """Attributable, not merely rejected."""
    vector, _ = ROM_NEGATIVE_VECTORS[index]
    result = full_guard_check(list(vector))
    failed = [g for g in GUARDS if not result[g]]
    assert failed == [guard], (
        f"index {index} was built to isolate {guard} but fails {failed}; a "
        f"vector that trips more than one guard cannot say which one caught it")


@pytest.mark.parametrize("index", sorted(ROM_NEGATIVE_VECTORS))
def test_silicon_carries_the_same_vector_the_software_models(index: int) -> None:
    """Software passing where the board fails is the bug this closes."""
    modelled = list(ROM_NEGATIVE_VECTORS[index][0])
    assert _rom_vector(index) == modelled, (
        f"index {index}: hcpu_rom.v and machine.py disagree. The Verilog "
        f"literal is written backwards -- check the byte order before "
        f"changing either side")


def test_every_guard_has_a_negative_vector() -> None:
    """The gap this file exists to close, asserted rather than assumed."""
    covered = {g for _, g in ROM_NEGATIVE_VECTORS.values()}
    assert covered == set(GUARDS), f"no negative vector for {set(GUARDS) - covered}"


def test_the_address_space_admits_them() -> None:
    """ROM_ADDR_W was 5 bits, which stops at 31 -- one slot, six guards.

    Widening it is what made the other five reachable at all, so the width and
    the highest index are checked together: a later narrowing would make the
    entries unreachable while leaving every other test in this file green.
    """
    pkg = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
    m = re.search(r"`define ROM_ADDR_W\s+(\d+)", pkg)
    assert m, "hcpu_pkg.vh no longer defines ROM_ADDR_W"
    width = int(m.group(1))
    assert max(ROM_NEGATIVE_VECTORS) < (1 << width), (
        f"index {max(ROM_NEGATIVE_VECTORS)} does not fit in {width} bits")


def test_the_program_that_runs_them_on_the_board_exists_and_counts_six() -> None:
    """`guard_negative.hasm` is the artefact that turns this into a figure."""
    src = (ROOT / "rtl" / "programs" / "guard_negative.hasm").read_text(encoding="utf-8")
    loaded = [int(x) for x in re.findall(r"HLOAD H0, (\d+)", src)]
    assert loaded == sorted(ROM_NEGATIVE_VECTORS), (
        f"the program loads {loaded}, the ROM carries {sorted(ROM_NEGATIVE_VECTORS)}")
    assert src.count("JGD") == len(ROM_NEGATIVE_VECTORS), (
        "one fall-through per vector, or the count means something else")
