"""The two HDMI wrappers must share the output stage the board proved.

hcpu_hdmi_top.v went dark on the board until its TMDS stage was rebuilt. A
hand-placed TLVDS_TBUF per lane did not survive synthesis: yosys added its
own OBUF behind each one, nextpnr discarded all four, and eight single-ended
drivers reached pins 33..40. The fix moved the differential pairing into the
constraint file -- LVCMOS33D, both pads of a pair in one IO_LOC.

kabah_hdmi_top.v was copied from the first version and not built until 11
September, so it kept the broken stage for exactly as long as nothing
compared the two. This file is that comparison.

It reads source structure only, with comments stripped -- prose describing
why TLVDS_TBUF was removed must not count as an instance of it. It says
nothing about whether either wrapper puts a picture on a screen; only a
board can say that. Both have now been on one -- hcpu_hdmi_top.v since 10
September, kabah_hdmi_top.v since its first build on 11 September.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"

WRAPPERS = (
    ("hcpu_hdmi_top.v", "hcpu_hdmi.cst"),
    ("kabah_hdmi_top.v", "kabah_hdmi.cst"),
)


def _code(path: Path) -> str:
    """Everything before `//` on each line: what the tools read."""
    return "\n".join(line.split("//", 1)[0]
                     for line in path.read_text(encoding="utf-8").splitlines())


def _tmds_lines(cst: str) -> list[str]:
    return sorted(line.strip() for line in _code(GOWIN / cst).splitlines()
                  if '"tmds_' in line)


@pytest.mark.parametrize("top", [t for t, _ in WRAPPERS])
def test_no_hand_placed_lvds_buffer_in_the_wrapper(top: str) -> None:
    code = _code(GOWIN / top)
    assert not re.search(r"\bTLVDS_TBUF\b", code), (
        f"{top} instantiates TLVDS_TBUF again -- nextpnr discards it behind "
        f"yosys's own OBUF, and the pins carry no TMDS")
    assert re.search(r"assign\s+tmds_clk_p\s*=\s*tmds_clk_serial\s*;", code)
    assert re.search(r"assign\s+tmds_data_p\s*=\s*tmds_data_serial\s*;", code)


@pytest.mark.parametrize("cst", [c for _, c in WRAPPERS])
def test_the_pairs_are_made_differential_by_the_constraint(cst: str) -> None:
    code = _code(GOWIN / cst)
    assert "LVDS25" not in code, f"{cst} constrains TMDS as true LVDS again"

    pairs = re.findall(r'IO_LOC\s+"(tmds_\w+)"\s+(\d+),(\d+)\s*;', code)
    assert sorted((int(p), int(n)) for _, p, n in pairs) == [
        (33, 34), (35, 36), (37, 38), (39, 40)], f"{cst}: {pairs}"
    for name, _, _ in pairs:
        assert re.search(rf'IO_PORT\s+"{name}"\s+IO_TYPE=LVCMOS33D\b', code), name


def test_both_wrappers_constrain_the_same_cells_the_same_way() -> None:
    """The copy may not drift from the proven original again."""
    assert _tmds_lines("kabah_hdmi.cst") == _tmds_lines("hcpu_hdmi.cst")
    assert len(_tmds_lines("hcpu_hdmi.cst")) == 8, "four lanes, IO_LOC and IO_PORT each"


def test_the_kabah_wrapper_says_what_was_measured_and_what_was_seen() -> None:
    """It was labelled NEVER BUILT until its first build, and the label had to
    move with the evidence. The instrument readings and the human observation
    of the screen are both evidence, and are recorded as different kinds."""
    header = (GOWIN / "kabah_hdmi_top.v").read_text(encoding="utf-8")
    assert "NEVER BUILT" not in header, "the label outlived the build"
    assert "MEASURED" in header and "RTL FINGERPRINT" in header
    assert "400/400" in header, "the board result belongs next to the figures"
    assert "an observation, not an instrument reading" in header
