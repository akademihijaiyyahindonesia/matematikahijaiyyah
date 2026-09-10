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
    assert top.name == "hcpu" and top.lut4 == 14_005

    assert rack.naive_sum_lut4() == 14_005 + 12_061 == 26_066
    assert rack.naive_sum_lut4() > rack.BOARD_LUT4, (
        "the slots would still fit side by side, so sequencing buys nothing")
    assert top.lut4 < rack.BOARD_LUT4, "the largest slot no longer fits alone"

    assert int(top.lut4 / rack.BOARD_LUT4 * 100) == 67
    assert int(rack.naive_sum_lut4() / rack.BOARD_LUT4 * 100) == 125


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
    assert largest.spare_lut4 == 6_731, "the tightest comparator budget moved"


def test_percentages_truncate_the_way_nextpnr_does() -> None:
    """67%, not 68%. A third number next to two that agree is a bug."""
    top = rack.largest()
    assert round(top.lut4 / rack.BOARD_LUT4 * 100) == 68, (
        "the rounding hazard this test exists for is gone -- check the render")
    assert f"{int(top.occupancy * 100)}%" == "67%"
    assert "67%" in rack.render() and "68%" not in rack.render()


# ── the manifest describes things that exist ─────────────────────

def test_every_slot_names_a_bitstream_that_is_built() -> None:
    assert len(rack.SLOTS) == 3
    for slot in rack.SLOTS:
        assert slot.built, f"{slot.name}: {slot.bitstream} is not on disk"
        assert slot.path.stat().st_size > 1_000_000, f"{slot.name} looks empty"


def test_the_three_bitstreams_are_distinct_designs() -> None:
    """Two of them are byte-for-byte the same SIZE, which is not the same
    thing -- the device's frame count is fixed, so size proves nothing."""
    import hashlib

    digests = {s.name: hashlib.sha256(s.path.read_bytes()).hexdigest()
               for s in rack.SLOTS}
    assert len(set(digests.values())) == 3, f"two slots share a bitstream: {digests}"


def test_the_figures_come_from_the_wrapper_that_measured_them() -> None:
    """One source. The wrappers carry these under a fingerprint; the rack
    must not become a second place where they can drift."""
    hcpu = (GOWIN / "hcpu_gowin_top.v").read_text(encoding="utf-8")
    kabah = (GOWIN / "hijaiyyah_kabah_gowin_top.v").read_text(encoding="utf-8")

    slots = {s.name: s for s in rack.SLOTS}
    assert re.search(r"LUT4\s+14,005 /\s+20,736\s+67%", hcpu)
    assert slots["hcpu"].lut4 == 14_005 and slots["hcpu"].dff == 4_480
    assert slots["hcpu"].fmax_mhz == 118.43 and "118.43 MHz" in hcpu

    assert re.search(r"LUT4\s+12,061/\s+20,736\s+58%", kabah)
    assert slots["kabah"].lut4 == 12_061 and slots["kabah"].dff == 1_965
    assert slots["kabah"].fmax_mhz == 165.98 and "165.98 MHz" in kabah


def test_the_board_constants_are_the_board() -> None:
    assert (rack.BOARD_LUT4, rack.BOARD_DFF, rack.BOARD_BSRAM) == (20_736, 15_552, 46)


# ── an unmeasured column stays unmeasured ────────────────────────

def test_the_hdmi_slot_is_unmeasured_and_says_so() -> None:
    """It runs. Its cost was never recorded, and zero is not "unknown".

    This is the same defect class as `OP_NOP = 8'h00` and a frequency of 0.0
    for silence: a legal-looking value standing in for an absent one. The
    slot is real, the bitstream is built and has run on the board -- only the
    utilisation was never captured, so the column is None.
    """
    hdmi = next(s for s in rack.SLOTS if s.name == "hdmi")
    assert hdmi.built, "the HDMI bitstream is missing"
    assert not hdmi.measured
    assert hdmi.lut4 is None and hdmi.dff is None
    assert hdmi.bsram is None and hdmi.fmax_mhz is None
    assert hdmi.occupancy is None and hdmi.spare_lut4 is None

    rendered = rack.render()
    assert "—" in rendered, "the unmeasured columns were filled in"
    assert "Belum terukur: hdmi" in rendered

    # And it must not be counted as a zero-cost slot in either figure.
    assert rack.naive_sum_lut4() == sum(
        s.lut4 for s in rack.SLOTS if s.measured)
    assert rack.largest().name != "hdmi"


def test_an_unmeasured_slot_cannot_win_the_maximum() -> None:
    """A None must never sort as small and let the rack understate itself."""
    measured = [s for s in rack.SLOTS if s.measured]
    assert rack.largest() in measured
    assert all(rack.largest().lut4 >= s.lut4 for s in measured)


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
