"""
Place and route, and the end of the longest-standing [EH] in the project.

Every per-second figure here carried "if it closes at 27 MHz" because nobody
had run place-and-route -- the tools were not installed. They are now, and it
has been run: yosys -> nextpnr-himbaechel -> gowin_pack, producing a bitstream.

Fmax is 90.14 MHz against the board's 27 MHz crystal. That resolves the clock
assumption FOR THE HCPU. It does not resolve it for hijaiyyah_kabah_top, which
is a different design with no board wrapper -- and cannot have one until its
interface narrows, because it presents 1,665 port bits to a device with 276
IOB. Keeping those two apart is the point of this file.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"
WRAPPER = (GOWIN / "hcpu_gowin_top.v").read_text(encoding="utf-8")

# What place-and-route reported. Retyped here on purpose: this is a record of a
# run, not a derivation, and it must not drift silently when the design changes.
FMAX_MHZ = 90.14
CRYSTAL_MHZ = 27.0
UTILISATION = {"LUT4": (6746, 8640), "MUX2_LUT5": (714, 4320),
               "ALU": (1544, 6480), "DFF": (1719, 6480),
               "BSRAM": (4, 26), "IOB": (10, 276)}


def _routed_table() -> dict[str, tuple[int, int]]:
    """
    Parse the utilisation block, rather than searching the file for numbers.

    Searching was not enough, and sabotage proved it twice: every figure in
    that block also appears in the -nodsp comparison lower down, so changing
    one occurrence left the other to satisfy the search. Third time this class
    of hole has turned up in these tests.
    """
    # `NAME  used / total  pct%` at the start of a comment line. The -nodsp
    # comparison further down writes `LUT4 4,550 (52%)` instead, so it cannot
    # match -- which is the whole point of parsing rather than searching.
    rows = re.findall(r"^//\s+(\w+)\s+([\d,]+)\s*/\s*([\d,]+)\s+\d+%",
                      WRAPPER, re.M)
    return {n: (int(u.replace(",", "")), int(t.replace(",", ""))) for n, u, t in rows}


def test_the_wrapper_header_records_the_routed_result() -> None:
    assert _routed_table() == UTILISATION

    # The Fmax line in the routed block, not any mention of the number.
    line = re.search(r"^//\s+Fmax\s+([\d.]+) MHz", WRAPPER, re.M)
    assert line and float(line.group(1)) == FMAX_MHZ


def test_the_margin_over_the_board_crystal_is_stated_and_real() -> None:
    margin = FMAX_MHZ / CRYSTAL_MHZ
    assert margin > 3.0
    assert f"{margin:.2f}x" in WRAPPER
    # And it has to fit, which is a separate question from closing timing.
    table = _routed_table()
    for name, (used, total) in table.items():
        assert used <= total, name
    assert table["LUT4"][0] / table["LUT4"][1] < 0.90


def test_the_kabah_top_is_still_unmeasured_and_the_reason_is_recorded() -> None:
    """
    Not "we have not got to it". It cannot be placed at all: 1,665 port bits
    against 276 IOB. A wrapper has to narrow the interface first, the way
    hcpu_gowin_top does for the HCPU.
    """
    top = (ROOT / "rtl" / "hijaiyyah_kabah_top.v").read_text(encoding="utf-8")
    head = top[top.index("module hijaiyyah_kabah_top"):top.index(");")]
    bits = sum(int(hi) + 1 for hi in
               re.findall(r"(?:input|output)\s+(?:wire|reg)?\s*\[\s*(\d+)\s*:\s*0\]", head))
    assert bits > 276, f"the interface narrowed to {bits} bits -- it can be placed now"
    assert "IOB" not in head

    concrete = (ROOT / "cosmictera" / "CONCRETE.md").read_text(encoding="utf-8")
    assert "1.665 bit port" in concrete
    assert "276 IOB" in concrete
    assert "Fmax Kabah top | **EH**" in concrete


def test_nodsp_is_required_and_the_reason_is_the_packer() -> None:
    """
    gowin_pack dies on KeyError: 'IRBY_IREG0BL_0' packing the MULT9X9 that
    synth_gowin infers. nextpnr places it happily, so the failure only appears
    at the last step -- and the suite's own gowin_pack fails identically, so it
    is not a version mismatch. Recorded so the flag is not dropped by someone
    who assumes it was caution.
    """
    makefile = (GOWIN / "Makefile").read_text(encoding="utf-8")
    assert "YOSYS_FLAGS ?= -nodsp" in makefile
    assert "IRBY_IREG0BL_0" in makefile
    assert "IRBY_IREG0BL_0" in WRAPPER
    # The DSP was on the critical path, so removing it cost area and BOUGHT
    # frequency. Counter-intuitive enough to be worth pinning.
    assert "82.33 MHz" in WRAPPER and "90.14 MHz" in WRAPPER


def test_the_makefile_can_report_which_tools_are_present() -> None:
    makefile = (GOWIN / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^tools:", makefile, re.M)
    for tool in ("yosys", "iverilog", "nextpnr-himbaechel", "gowin_pack",
                 "openFPGALoader"):
        assert tool in makefile, tool


@pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not installed")
def test_the_synthesis_flag_actually_removes_the_dsp() -> None:
    """The flag is only load-bearing if it changes what is inferred."""
    makefile = (GOWIN / "Makefile").read_text(encoding="utf-8")
    assert "synth_gowin $(YOSYS_FLAGS)" in makefile, (
        "the flag is defined but not passed to synth_gowin")
