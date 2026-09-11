"""The bitstream rack, and the arithmetic that makes sequencing different.

The rack's whole claim is one substitution: `max` where the old framing used
`sum`. Slots are loaded one at a time, so they never share the fabric, so
their costs never add. 105% was a measurement of a question nobody had to
ask.

None of these tests need a board. They check the manifest and the
arithmetic, which is what can go wrong silently -- a bitstream path that
stops existing, a figure that drifts from the wrapper that measured it, or
an unmeasured column quietly filled with a zero. The board half was run by
hand and its results are in `cosmictera-build/PAPAN.md`; a test that needs
hardware attached is a test that does not run.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"

_spec = importlib.util.spec_from_file_location(
    "rack", ROOT / "rtl" / "scripts" / "rack.py")
rack = importlib.util.module_from_spec(_spec)
# Registered before exec: @dataclass resolves annotations through
# sys.modules[cls.__module__], and an unregistered module makes that None.
sys.modules["rack"] = rack
_spec.loader.exec_module(rack)


# ── the substitution the rack exists for ─────────────────────────

def test_the_rack_costs_its_largest_slot_not_their_sum() -> None:
    """Sequencing turns an addition into a maximum, and that is the finding.

    Both numbers are asserted, not just the flattering one: the naive sum
    has to stay visible next to the max, or the comparison the rack is
    making disappears and it looks like the design simply got smaller.
    """
    top = rack.largest()
    assert top.name == "hdmi" and top.lut4 == 14_713, (
        "the video slot -- HCPU plus TMDS -- is the largest, and that only "
        "became visible once its cost was measured")

    assert rack.naive_sum_lut4() == 14_231 + 12_061 + 14_713 == 41_005
    assert rack.naive_sum_lut4() > rack.BOARD_LUT4, (
        "the slots would still fit side by side, so sequencing buys nothing")
    assert top.lut4 < rack.BOARD_LUT4, "the largest slot no longer fits alone"

    assert int(top.lut4 / rack.BOARD_LUT4 * 100) == 70
    assert int(rack.naive_sum_lut4() / rack.BOARD_LUT4 * 100) == 197


def test_the_spare_is_largest_where_the_slot_is_smallest() -> None:
    """What a comparator gets is the complement of the slot, per slot."""
    measured = [s for s in rack.SLOTS if s.measured]
    assert len(measured) >= 2
    for slot in measured:
        assert slot.spare_lut4 == rack.BOARD_LUT4 - slot.lut4
        assert slot.spare_lut4 > 0

    smallest = min(measured, key=lambda s: s.lut4)
    largest = max(measured, key=lambda s: s.lut4)
    assert smallest.spare_lut4 > largest.spare_lut4
    assert largest.spare_lut4 == 6_023, "the tightest comparator budget moved"


def test_percentages_truncate_the_way_nextpnr_does() -> None:
    """68%, not 69%. A third number next to two that agree is a bug."""
    hcpu = next(s for s in rack.SLOTS if s.name == "hcpu")
    assert round(hcpu.lut4 / rack.BOARD_LUT4 * 100) == 69, (
        "the rounding hazard this test exists for is gone -- check the render")
    assert f"{int(hcpu.occupancy * 100)}%" == "68%"
    assert "68%" in rack.render() and "69%" not in rack.render()


# ── the manifest describes things that exist ─────────────────────

def _makefile_products() -> set[str]:
    """Every .fs the gowin Makefile's pack steps write, with variables expanded."""
    text = (GOWIN / "Makefile").read_text(encoding="utf-8")
    assigns = dict(re.findall(r"^([A-Z_]+)\s*\??=\s*(\S+)\s*$", text, re.M))
    return {f"{assigns[var]}.fs" for var in re.findall(r"-o\s+\$\((\w+)\)\.fs", text)}


def test_every_slot_is_a_bitstream_the_makefile_builds() -> None:
    """A slot has to be rebuildable from a clean tree, not merely on disk here.

    The first version asserted each .fs existed. They are build outputs that
    git ignores, so it passed on the machine that built them and failed on
    every clean checkout -- measured, in a worktree at 81fbd2e. And the HDMI
    slot had no Makefile target at all: it existed only as a remembered
    command, and `make clean` deletes *.fs.
    """
    assert len(rack.SLOTS) == 3
    products = _makefile_products()
    for slot in rack.SLOTS:
        assert slot.path.parent == GOWIN, slot.bitstream
        assert slot.path.name in products, (
            f"{slot.name}: no Makefile target writes {slot.path.name}")


def test_built_bitstreams_are_real_and_distinct() -> None:
    """Where the slots have been built. Two are the same SIZE, which proves
    nothing -- the device's frame count is fixed -- so the hash is the check."""
    import hashlib

    missing = [s.name for s in rack.SLOTS if not s.built]
    if missing:
        pytest.skip(f"bitstreams not built on this checkout: {missing} "
                    f"(the gowin Makefile's bitstream targets build them)")
    for slot in rack.SLOTS:
        assert slot.path.stat().st_size > 1_000_000, f"{slot.name} looks empty"
    digests = {s.name: hashlib.sha256(s.path.read_bytes()).hexdigest()
               for s in rack.SLOTS}
    assert len(set(digests.values())) == 3, f"two slots share a bitstream: {digests}"


def test_the_figures_come_from_the_wrapper_that_measured_them() -> None:
    """One source. The wrappers carry these under a fingerprint; the rack
    must not become a second place where they can drift."""
    hcpu = (GOWIN / "hcpu_gowin_top.v").read_text(encoding="utf-8")
    kabah = (GOWIN / "hijaiyyah_kabah_gowin_top.v").read_text(encoding="utf-8")

    slots = {s.name: s for s in rack.SLOTS}
    assert re.search(r"LUT4\s+14,231 /\s+20,736\s+68%", hcpu)
    assert slots["hcpu"].lut4 == 14_231 and slots["hcpu"].dff == 4_480
    assert slots["hcpu"].fmax_mhz == 84.26 and "84.26 MHz" in hcpu

    assert re.search(r"LUT4\s+12,061/\s+20,736\s+58%", kabah)
    assert slots["kabah"].lut4 == 12_061 and slots["kabah"].dff == 1_965
    assert slots["kabah"].fmax_mhz == 165.98 and "165.98 MHz" in kabah

    hdmi = (GOWIN / "hcpu_hdmi_top.v").read_text(encoding="utf-8")
    assert re.search(r"LUT4\s+14,713 /\s+20,736\s+70%", hdmi)
    assert slots["hdmi"].lut4 == 14_713 and slots["hdmi"].dff == 4_551
    assert slots["hdmi"].fmax_mhz == 60.34 and "60.34 MHz" in hdmi


def test_the_board_constants_are_the_board() -> None:
    assert (rack.BOARD_LUT4, rack.BOARD_DFF, rack.BOARD_BSRAM) == (20_736, 15_552, 46)


# ── an unmeasured column stays unmeasured ────────────────────────

def test_the_hdmi_slot_is_measured_and_it_sets_the_rack_cost() -> None:
    """It was None until 11 September, and while it was the rack quoted 67%.

    That figure was the maximum of the two slots that had numbers -- true of
    them, false of the rack. Measured, the video slot is the largest and the
    rack costs 70%. The None was still the right call: a zero in its place
    would have kept the 67% and called the video path free, the same defect
    class as OP_NOP = 8'h00 and a frequency of 0.0 for silence.
    """
    hdmi = next(s for s in rack.SLOTS if s.name == "hdmi")
    assert hdmi.measured
    assert (hdmi.lut4, hdmi.dff, hdmi.bsram, hdmi.fmax_mhz) == (14_713, 4_551, 17, 60.34)
    assert rack.largest() is hdmi
    assert "Belum terukur" not in rack.render()


def test_an_unmeasured_slot_cannot_move_the_rack_cost(monkeypatch) -> None:
    """A None must never sort as small or large and change what the rack costs."""
    ghost = rack.Slot(name="ghost", bitstream="rtl/fpga/gowin/ghost.fs",
                      runs="nothing", verified="nothing")
    monkeypatch.setattr(rack, "SLOTS", (*rack.SLOTS, ghost))
    assert not ghost.measured
    assert rack.largest().name == "hdmi"
    assert rack.naive_sum_lut4() == 41_005
    assert "Belum terukur: ghost" in rack.render()


# ── refusals ─────────────────────────────────────────────────────

def test_flashing_an_unbuilt_slot_is_refused_before_touching_the_board() -> None:
    missing = rack.Slot(name="ghost", bitstream="rtl/fpga/gowin/nope.fs",
                        runs="nothing", verified="nothing", lut4=1)
    assert not missing.built
    with pytest.raises(FileNotFoundError, match="has not been built"):
        rack.flash(missing)


def test_detect_reports_rather_than_raises_when_the_tool_is_absent(monkeypatch) -> None:
    """A CI box has no openFPGALoader, and asking should not be an error."""
    def boom(*_a, **_k):
        raise FileNotFoundError("openFPGALoader")

    monkeypatch.setattr(rack.subprocess, "run", boom)
    assert rack.detect() is False
