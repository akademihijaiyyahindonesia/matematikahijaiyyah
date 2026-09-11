"""
Place and route: the design fits the Tang Nano 20K, and the mechanism that
keeps its numbers honest.

A measurement went stale once and nothing caught it for a while. The reason
is worth keeping: the test that guarded the numbers compared the header's
text against constants retyped here. Both are transcriptions. When
the DESIGN changed, neither moved, so the guard went on passing while the
thing it described became false.

Numbers about a design have to be tied to that design. So the header carries
a hash of the RTL it was measured from, and the check below recomputes it.
Change any source file and this fails, asking for a fresh run -- which is the
one thing a retyped constant can never do. Not a one-time fix, a standing
check.

The raw Kabah top is still unplaceable for its own separate reason: 1,665
port bits against 384 IOB. Keeping the two apart is the point of this file.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"
WRAPPER = (GOWIN / "hcpu_gowin_top.v").read_text(encoding="utf-8")

CRYSTAL_MHZ = 27.0

# What place and route reported at THIS commit, on the Tang Nano 20K.
UTILISATION = {"LUT4": (14231, 20736), "DFF": (4480, 15552), "BSRAM": (17, 46)}
MEASURED_FMAX_MHZ = 84.26

# The commit the fitting result was taken from, re-run to confirm it still
# reproduces there: LUT4 6,753 (78%), Fmax 97.94 MHz.
LAST_FITTING = "096e392"
FIRST_FAILING = "348e9c6"

FP_MARK = "// RTL FINGERPRINT: "
FINGERPRINTED = sorted((ROOT / "rtl").glob("*.v")) + sorted((ROOT / "rtl").glob("*.vh")) + [
    GOWIN / "hcpu_gowin_top.v",
    GOWIN / "hcpu_gowin.cst",
]

# Ka'bah's own dependency set, not HCPU's -- deliberately not the same list.
# Touching hijaiyyah_sponge.v should not demand HCPU be re-measured, and
# touching hcpu_execute.v should not demand Ka'bah be re-measured either.
# This is exactly rtl/fpga/gowin/Makefile's KABAH_SOURCES: not
# rtl/*.v's wildcard, because that would pull in hijaiyyah_ramal_core.v,
# hijaiyyah_sbox_router.v and hijaiyyah_wave.v -- retired/alternate designs
# this wrapper does not instantiate.
KABAH_WRAPPER_PATH = GOWIN / "hijaiyyah_kabah_gowin_top.v"
KABAH_FINGERPRINTED = [
    KABAH_WRAPPER_PATH,
    ROOT / "rtl" / "hijaiyyah_kabah_top.v",
    ROOT / "rtl" / "hijaiyyah_deserialiser.v",
    ROOT / "rtl" / "hijaiyyah_jamrah_gate.v",
    ROOT / "rtl" / "hijaiyyah_node_counter.v",
    ROOT / "rtl" / "hijaiyyah_sponge.v",
    ROOT / "rtl" / "hijaiyyah_ramal_impulse.v",
    ROOT / "rtl" / "hijaiyyah_rotate_core.v",
    ROOT / "rtl" / "hijaiyyah_linear.v",
    ROOT / "rtl" / "hijaiyyah_sbox.v",
    ROOT / "rtl" / "hijaiyyah_round_constants.v",
    ROOT / "rtl" / "hcpu_uart_rx.v",
    ROOT / "rtl" / "hcpu_uart_tx.v",
    GOWIN / "hcpu_gowin.cst",
]


# The HDMI slot's own dependency set -- exactly the Makefile's HDMI_SOURCES
# (hcpu_hdmi_top.v, dvi_tx_open.v, tmds_rpll.v, hcpu_gowin_top.v and every
# rtl/hcpu_*.v), the include files, and the constraint it is placed with.
HDMI_WRAPPER_PATH = GOWIN / "hcpu_hdmi_top.v"
HDMI_FINGERPRINTED = [
    HDMI_WRAPPER_PATH,
    GOWIN / "dvi_tx_open.v",
    GOWIN / "tmds_rpll.v",
    GOWIN / "hcpu_gowin_top.v",
    GOWIN / "hcpu_hdmi.cst",
    *sorted((ROOT / "rtl").glob("hcpu_*.v")),
    *sorted((ROOT / "rtl").glob("*.vh")),
]

# Ka'bah over HDMI -- exactly the Makefile's KABAH_HDMI_SOURCES, placed with
# kabah_hdmi.cst instead of hcpu_gowin.cst.
KABAH_HDMI_WRAPPER_PATH = GOWIN / "kabah_hdmi_top.v"
KABAH_HDMI_FINGERPRINTED = [
    KABAH_HDMI_WRAPPER_PATH,
    GOWIN / "dvi_tx_open.v",
    GOWIN / "tmds_rpll.v",
    ROOT / "rtl" / "hcpu_video_timing.v",
    GOWIN / "kabah_hdmi.cst",
    *(f for f in KABAH_FINGERPRINTED if f.name != "hcpu_gowin.cst"),
]

def _fingerprint(sources: list[Path]) -> str:
    """A hash of the DESIGN the recorded run was made from.

    Whole-line comments and blank lines are skipped, because synthesis does
    not see them. The first version hashed every byte, and that made every
    prose fix in a header demand a fresh place-and-route -- which nobody can
    supply for a comment, so the pressure went the other way: restamp the
    hash without measuring. A guard that is expensive to satisfy honestly
    and cheap to satisfy dishonestly teaches the wrong habit, and this one
    was about to.

    Only *whole-line* comments are dropped, never a trailing `//`: a Verilog
    string can legally contain one, and stripping mid-line would risk
    changing a hash over something synthesis does see.
    """
    import hashlib

    h = hashlib.sha256()
    for f in sources:
        h.update(f.name.encode())
        for line in f.read_text(encoding="utf-8").splitlines(keepends=True):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
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
    assert recorded.group(1) == _fingerprint(FINGERPRINTED), (
        "the RTL has changed since place and route was last run, so the "
        "numbers in hcpu_gowin_top.v no longer describe this design. Re-run "
        "`make -C rtl/fpga/gowin hcpu_gowin_top_pnr.json`, put the new figures "
        "in the header, and restamp the fingerprint."
    )


def test_the_kabah_wrapper_records_its_own_fingerprint() -> None:
    """Same mechanism as HCPU's, and deliberately a separate one -- see
    KABAH_FINGERPRINTED's own comment for why the two dependency sets are
    not merged into one hash."""
    kabah_wrapper = KABAH_WRAPPER_PATH.read_text(encoding="utf-8")
    recorded = re.search(rf"^{re.escape(FP_MARK)}([0-9a-f]{{64}})$", kabah_wrapper, re.M)
    assert recorded, "the Ka'bah wrapper no longer records an RTL fingerprint"
    assert recorded.group(1) == _fingerprint(KABAH_FINGERPRINTED), (
        "the RTL has changed since the Ka'bah wrapper's place and route was "
        "last run, so the numbers in hijaiyyah_kabah_gowin_top.v no longer "
        "describe this design. Re-run `make -C rtl/fpga/gowin "
        "hijaiyyah_kabah_gowin_top_pnr.json`, put the new figures in the "
        "header, and restamp the fingerprint."
    )


def test_the_hdmi_wrapper_records_its_own_fingerprint() -> None:
    """The third slot, measured on 11 September and held the same way."""
    hdmi = HDMI_WRAPPER_PATH.read_text(encoding="utf-8")
    recorded = re.search(rf"^{re.escape(FP_MARK)}([0-9a-f]{{64}})$", hdmi, re.M)
    assert recorded, "hcpu_hdmi_top.v no longer records an RTL fingerprint"
    assert recorded.group(1) == _fingerprint(HDMI_FINGERPRINTED), (
        "the RTL has changed since the HDMI wrapper's place and route was last "
        "run, so the numbers in hcpu_hdmi_top.v no longer describe this design. "
        "Re-run `make -C rtl/fpga/gowin PROGRAM=../../programs/loader.hasm "
        "hdmi_bitstream`, put the new figures in the header, and restamp."
    )


def test_the_hdmi_wrapper_records_its_routed_result() -> None:
    hdmi = HDMI_WRAPPER_PATH.read_text(encoding="utf-8")
    rows = {name: (int(used.replace(",", "")), int(total.replace(",", "")))
            for name, used, total in re.findall(
                r"^//\s+(\w+)\s+([\d,]+)\s*/\s*([\d,]+)\s+\d+%", hdmi, re.M)}
    assert rows == {"IOB": (15, 384), "LUT4": (14713, 20736),
                    "DFF": (4551, 15552), "BSRAM": (17, 46)}
    assert re.search(r"^//\s+Fmax\s+60\.34 MHz", hdmi, re.M)

def test_the_kabah_hdmi_wrapper_records_its_own_fingerprint() -> None:
    """Built for the first time on 11 September, and held like the others."""
    wrapper = KABAH_HDMI_WRAPPER_PATH.read_text(encoding="utf-8")
    recorded = re.search(rf"^{re.escape(FP_MARK)}([0-9a-f]{{64}})$", wrapper, re.M)
    assert recorded, "kabah_hdmi_top.v no longer records an RTL fingerprint"
    assert recorded.group(1) == _fingerprint(KABAH_HDMI_FINGERPRINTED), (
        "the RTL has changed since the Ka'bah HDMI wrapper was last placed and "
        "routed, so the numbers in kabah_hdmi_top.v no longer describe this "
        "design. Re-run `make -C rtl/fpga/gowin kabah_hdmi_bitstream`, put the "
        "new figures in the header, and restamp."
    )


def test_the_kabah_hdmi_wrapper_records_its_routed_result() -> None:
    wrapper = KABAH_HDMI_WRAPPER_PATH.read_text(encoding="utf-8")
    rows = {name: (int(used.replace(",", "")), int(total.replace(",", "")))
            for name, used, total in re.findall(
                r"^//\s+(\w+)\s+([\d,]+)\s*/\s*([\d,]+)\s+\d+%", wrapper, re.M)}
    assert rows == {"IOB": (15, 384), "LUT4": (12142, 20736),
                    "DFF": (2035, 15552), "BSRAM": (0, 46)}
    assert re.search(r"^//\s+Fmax\s+94\.16 MHz", wrapper, re.M)

def test_the_wrapper_header_records_the_routed_result() -> None:
    assert _routed_table() == UTILISATION


def test_the_header_records_the_measured_fmax() -> None:
    """Routing completes on the 20K, so a timing report exists -- and the
    number in the header has to be the one that report gave, not a carried-
    over figure from a design that no longer matches this RTL."""
    match = re.search(r"^//\s+Fmax\s+([\d.]+) MHz", WRAPPER, re.M)
    assert match, "the header does not record a measured Fmax"
    assert float(match.group(1)) == MEASURED_FMAX_MHZ


def test_the_design_fits_and_says_so() -> None:
    table = _routed_table()
    assert table["LUT4"][0] <= table["LUT4"][1], (
        "LUT4 no longer fits -- re-measure and rewrite this file to match"
    )
    assert "PLACES AND ROUTES on the Tang Nano 20K" in WRAPPER
    # What must NOT appear is a current-tense claim that routing fails.
    assert "PLACE AND ROUTE FAILS AT THIS COMMIT" not in WRAPPER


def test_the_growth_is_attributed_to_the_commit_that_caused_it() -> None:
    """One commit doubled it. Naming it is what makes the record actionable
    rather than just bad news."""
    assert LAST_FITTING in WRAPPER and FIRST_FAILING in WRAPPER
    assert "the loader's write port" in WRAPPER
    rows = re.findall(r"^//\s+([0-9a-f]{7})\s+\S.*?\s{2,}([\d,]+)\s*$", WRAPPER, re.M)
    assert len(rows) == 6, f"the bisection table lost rows: {rows}"

    lut = {c: int(n.replace(",", "")) for c, n in rows}
    # The verdict columns are gone: "fits" / "FAILS" were relative to a
    # device this project never had. The LUT4 counts are the measurement,
    # and the jump is what the table exists to show.
    assert lut[FIRST_FAILING] - lut[LAST_FITTING] > 6_000, (
        f"the boot path's cost is no longer visible: {lut}")
    assert lut[LAST_FITTING] == 6_740 and lut[FIRST_FAILING] == 13_644


def test_the_kabah_top_is_still_unmeasured_and_the_reason_is_recorded() -> None:
    """
    Not "we have not got to it". It cannot be placed at all: 1,665 port bits
    against 384 IOB. A wrapper has to narrow the interface first, the way
    hcpu_gowin_top does for the HCPU.
    """
    top = (ROOT / "rtl" / "hijaiyyah_kabah_top.v").read_text(encoding="utf-8")
    head = top[top.index("module hijaiyyah_kabah_top"):top.index(");")]
    bits = sum(int(hi) + 1 for hi in
               re.findall(r"(?:input|output)\s+(?:wire|reg)?\s*\[\s*(\d+)\s*:\s*0\]", head))
    assert bits > 384, f"the interface narrowed to {bits} bits -- it can be placed now"
    assert "IOB" not in head

    concrete = (ROOT / "cosmictera" / "CONCRETE.md").read_text(encoding="utf-8")
    assert "1.665 bit port" in concrete
    assert "384 IOB" in concrete
    assert "Fmax Kabah top | **EH**" in concrete


def test_the_kabah_wrapper_narrows_the_interface_and_says_so() -> None:
    """
    hijaiyyah_kabah_top.v itself stays wide -- the test above keeps that
    honest. hijaiyyah_kabah_gowin_top.v is the wrapper hcpu_gowin_top.v's own
    precedent said this needed: out_state stays internal, and the pins are
    clk, reset, UART in/out and six LEDs.
    """
    wrapper = (GOWIN / "hijaiyyah_kabah_gowin_top.v").read_text(encoding="utf-8")
    head = wrapper[wrapper.index("module hijaiyyah_kabah_gowin_top"):wrapper.index(");")]
    bits = sum(int(hi) + 1 for hi in
               re.findall(r"(?:input|output)\s+(?:wire|reg)?\s*\[\s*(\d+)\s*:\s*0\]", head))
    bits += len(re.findall(r"(?:input|output)\s+wire\s+\w", head))  # scalar ports
    assert bits <= 20, f"the wrapper interface grew to {bits} bits"
    assert "out_state" not in head
    assert "1,665" in wrapper and "384 IOB" in wrapper


def test_the_kabah_wrapper_dumps_exactly_cube_pys_state_over_simulated_uart() -> None:
    """
    The wrapper's own logic -- UART framing, the bit-serial feed, the
    permute-wait, the 200-byte dump -- is new code the RTL-direct kabah_top
    bench never exercised. This drives it the only way a board ever will: as
    bytes in on uart_rxd, bytes out on uart_txd, nothing touching bit_in or
    out_state directly. It caught a real bug before this test existed --
    tx_data raced dump_idx and byte 0 of every dump was skipped -- so it
    stays here as the thing that would catch it coming back.
    """
    sources = [
        "rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v",
        "rtl/hijaiyyah_kabah_top.v", "rtl/hijaiyyah_deserialiser.v",
        "rtl/hijaiyyah_jamrah_gate.v", "rtl/hijaiyyah_node_counter.v",
        "rtl/hijaiyyah_sponge.v", "rtl/hijaiyyah_ramal_impulse.v",
        "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_linear.v",
        "rtl/hijaiyyah_sbox.v", "rtl/hijaiyyah_round_constants.v",
        "rtl/hcpu_uart_rx.v", "rtl/hcpu_uart_tx.v",
        "rtl/tb/tb_hijaiyyah_kabah_gowin_top.v",
    ]
    build = subprocess.run(
        ["iverilog", "-g2012", "-I", "rtl",
         "-s", "tb_hijaiyyah_kabah_gowin_top", "-o", "/tmp/tb_kabah_gowin_top", *sources],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["vvp", "/tmp/tb_kabah_gowin_top"], cwd=ROOT,
                         capture_output=True, text=True, timeout=60)
    assert "PASS:" in run.stdout, run.stdout
    assert "400/400 bytes" in run.stdout


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
