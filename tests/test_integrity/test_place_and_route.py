"""
Place and route: the design no longer fits, and how that went unnoticed.

Fmax was measured once, honestly, and the [EH] on it was retired. Five commits
later the design is 159% of the board's LUT4 and nextpnr stops with "no BELs
remaining". Nothing caught it, and the reason is worth keeping: the test that
guarded the numbers compared the header's text against constants retyped here.
Both are transcriptions. When the DESIGN changed, neither moved, so the guard
went on passing while the thing it described became false.

Numbers about a design have to be tied to that design. So the header now
carries a hash of the RTL it was measured from, and the check below recomputes
it. Change any source file and this fails, asking for a fresh run -- which is
the one thing a retyped constant can never do.

The Kabah top is still unmeasured for its own separate reason: 1,665 port bits
against 276 IOB. Keeping the two apart is still the point of this file.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"
WRAPPER = (GOWIN / "hcpu_gowin_top.v").read_text(encoding="utf-8")

CRYSTAL_MHZ = 27.0

# What place and route reported at THIS commit. It fails, so there is no Fmax.
UTILISATION = {"LUT4": (13945, 8640), "DFF": (4454, 6480), "BSRAM": (17, 26)}

# The commit the fitting result was taken from, re-run to confirm it still
# reproduces there: LUT4 6,753 (78%), Fmax 97.94 MHz.
LAST_FITTING = "096e392"
FIRST_FAILING = "348e9c6"

FP_MARK = "// RTL FINGERPRINT: "
FINGERPRINTED = sorted((ROOT / "rtl").glob("*.v")) + sorted((ROOT / "rtl").glob("*.vh")) + [
    GOWIN / "hcpu_gowin_top.v",
    GOWIN / "hcpu_gowin.cst",
]


def _fingerprint() -> str:
    """A hash of the sources the recorded run was made from.

    The wrapper carries the recorded hash in a comment, so that one line is
    skipped -- a record cannot hash itself.
    """
    import hashlib

    h = hashlib.sha256()
    for f in FINGERPRINTED:
        h.update(f.name.encode())
        for line in f.read_text(encoding="utf-8").splitlines(keepends=True):
            if line.startswith(FP_MARK):
                continue
            h.update(line.encode())
    return h.hexdigest()


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


def test_the_recorded_numbers_belong_to_this_rtl() -> None:
    """The guard the old one could not be. A retyped constant agrees with a
    retyped header no matter what the design does; a hash does not."""
    recorded = re.search(rf"^{re.escape(FP_MARK)}([0-9a-f]{{64}})$", WRAPPER, re.M)
    assert recorded, "the wrapper no longer records an RTL fingerprint"
    assert recorded.group(1) == _fingerprint(), (
        "the RTL has changed since place and route was last run, so the "
        "numbers in hcpu_gowin_top.v no longer describe this design. Re-run "
        "`make -C rtl/fpga/gowin hcpu_gowin_top_pnr.json`, put the new figures "
        "in the header, and restamp the fingerprint."
    )


def test_the_wrapper_header_records_the_routed_result() -> None:
    assert _routed_table() == UTILISATION


def test_the_header_does_not_claim_an_fmax_it_could_not_measure() -> None:
    """Routing never completes, so no timing report exists. A number here
    would be carried over from a design that no longer exists."""
    assert not re.search(r"^//\s+Fmax\s+[\d.]+ MHz", WRAPPER, re.M)
    assert "Fmax        unmeasured" in WRAPPER
    assert "[EH] on Fmax is back" in WRAPPER


def test_the_design_does_not_fit_and_says_so() -> None:
    table = _routed_table()
    assert table["LUT4"][0] > table["LUT4"][1], (
        "LUT4 fits again -- re-measure and rewrite this file to match"
    )
    assert "PLACE AND ROUTE FAILS AT THIS COMMIT" in WRAPPER
    assert "no BELs remaining" in WRAPPER


def test_the_growth_is_attributed_to_the_commit_that_caused_it() -> None:
    """One commit doubled it. Naming it is what makes the record actionable
    rather than just bad news."""
    assert LAST_FITTING in WRAPPER and FIRST_FAILING in WRAPPER
    assert "the loader's write port" in WRAPPER
    fits = re.findall(r"^//\s+([0-9a-f]{7})\s+.+?\s+([\d,]+)\s+\d+%\s+(fits|FAILS)",
                      WRAPPER, re.M)
    assert len(fits) == 6, f"the bisection table lost rows: {fits}"
    verdicts = dict((c, v) for c, _, v in fits)
    assert verdicts[LAST_FITTING] == "fits"
    assert verdicts[FIRST_FAILING] == "FAILS"


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
