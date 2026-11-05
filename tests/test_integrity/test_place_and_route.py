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
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"
WRAPPER = (GOWIN / "hcpu_gowin_top.v").read_text(encoding="utf-8")

CRYSTAL_MHZ = 27.0

# What place and route reported at THIS commit, on the Tang Nano 20K.
# Re-measured 2026-11-02 for Paket 8 (CODEX_PROFILE 2 on this slot), with
# `make -C rtl/fpga/gowin bitstream`; the wrapper's header carries the run.
#
# Before that, re-measured 2026-09-15, after hcpu_gowin_top.v was split into
# hcpu_gowin_core (everything, including the telemetry sideband) and a
# pin-level hcpu_gowin_top. The split was forced by a measurement: with the
# sideband on the top level, `make -C rtl/fpga/gowin bitstream` died on
# `ERROR: Unconstrained IO:tele_pc_OBUF_O_9` -- a top level must find a pin
# for every output, and eighty-four bits of telemetry never will.
#
# +143 LUT4 and nothing else moves. DFF, BSRAM and IOB are identical, which is
# the check that one more level of hierarchy added no function; the wrapper's
# own header carries the controlled before/after that separates yosys remapping
# from logic.
UTILISATION = {"LUT4": (15367, 20736), "DFF": (5166, 15552),
               "BSRAM": (18, 46), "IOB": (11, 384)}
MEASURED_FMAX_MHZ = 54.86

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
KABAH_BASE = [
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
# Layer 3 (owner, 3 October 2026): the UART slot's own build reads
# kabah_with_hmac.vh first, which defines KABAH_WITH_HMAC, and these three
# sources as well -- the Makefile's KABAH_L3_DEFINE and KABAH_L3_SOURCES.
# Ka'bah over HDMI defines nothing and does not read them, so its fingerprint
# is taken over KABAH_BASE alone.
KABAH_L3 = [
    GOWIN / "kabah_with_hmac.vh",
    ROOT / "rtl" / "hijaiyyah_hmac.v",
    ROOT / "rtl" / "hijaiyyah_sha256_stream.v",
    ROOT / "rtl" / "hijaiyyah_sha256_core.v",
]
KABAH_FINGERPRINTED = [*KABAH_BASE, *KABAH_L3]


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
    *(f for f in KABAH_BASE if f.name != "hcpu_gowin.cst"),
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


# A fingerprint has to be a function of what a checkout holds. A fingerprinted file git does not
# track is listed here with the script that makes it from tracked sources. Measured 23 October
# 2026: in a clean clone, where rtl/hcpu_dashboard_pos.vh had not been generated, the CPU
# fingerprint was taken over one file fewer than in the source tree, and the test said the RTL
# had changed.
GENERATED = {ROOT / "rtl" / "hcpu_dashboard_pos.vh": ROOT / "rtl" / "scripts" / "gen_dashboard.py"}
MAKE_GENERATED = "make -C rtl/fpga/gowin ../../hcpu_dashboard_pos.vh"


def _tracked() -> set[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    return {p for p in out.split("\0") if p}


def _generated_problems(sources: list[Path], tracked: set[str],
                        generated: dict[Path, Path]) -> list[str]:
    """Why a fingerprint over `sources` would not be a function of the checkout, if it would not:
    a file neither tracked nor generated, or a generated file that is absent or not what its
    script makes now. The script is run in a temporary root, never over the working tree."""
    problems = [f"{f.relative_to(ROOT)} is fingerprinted but neither tracked nor generated"
                for f in sources if f.relative_to(ROOT).as_posix() not in tracked
                and f not in generated]
    for out, script in generated.items():
        rel = out.relative_to(ROOT)
        if not out.exists():
            problems.append(f"{rel} is generated, not tracked, and absent: run `{MAKE_GENERATED}`")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / script.relative_to(ROOT)
            copy.parent.mkdir(parents=True)
            shutil.copy(script, copy)
            subprocess.run([sys.executable, str(copy)], cwd=tmp, capture_output=True, check=True)
            made = Path(tmp) / rel
            if not made.exists() or made.read_bytes() != out.read_bytes():
                problems.append(f"{rel} is not what {script.relative_to(ROOT)} makes now: "
                                f"run `{MAKE_GENERATED}`")
    return problems


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
    assert _generated_problems(FINGERPRINTED, _tracked(), GENERATED) == []
    assert recorded.group(1) == _fingerprint(FINGERPRINTED), (
        "the RTL has changed since place and route was last run, so the "
        "numbers in hcpu_gowin_top.v no longer describe this design. Re-run "
        "`make -C rtl/fpga/gowin hcpu_gowin_top_pnr.json`, put the new figures "
        "in the header, and restamp the fingerprint."
    )


def test_every_fingerprinted_file_is_tracked_or_generated_from_tracked_sources() -> None:
    sources = {*FINGERPRINTED, *KABAH_FINGERPRINTED, *HDMI_FINGERPRINTED, *KABAH_HDMI_FINGERPRINTED}
    assert _generated_problems(sorted(sources), _tracked(), GENERATED) == []


def test_a_generated_file_that_is_absent_or_stale_is_named_not_read_as_an_rtl_change(
    tmp_path: Path,
) -> None:
    script = GENERATED[ROOT / "rtl" / "hcpu_dashboard_pos.vh"]
    absent = _generated_problems([], set(), {ROOT / "rtl" / "no_such_generated.vh": script})
    assert absent and "absent" in absent[0] and MAKE_GENERATED in absent[0], absent
    stale = _generated_problems([], set(), {ROOT / "rtl" / "hcpu_pkg.vh": script})
    assert stale and "not what" in stale[0], stale
    untracked = _generated_problems([ROOT / "rtl" / "hcpu_pkg.vh"], set(), {})
    assert untracked and "neither tracked nor generated" in untracked[0], untracked
    # And when the generated header is valid while a tracked RTL file changes,
    # _generated_problems stays empty and _fingerprint catches the RTL change.
    pkg = ROOT / "rtl" / "hcpu_pkg.vh"
    changed_pkg = tmp_path / "hcpu_pkg.vh"
    changed_pkg.write_text(pkg.read_text(encoding="utf-8") + "\nwire _qb4_probe = 1'b0;\n",
                           encoding="utf-8")
    sources = [changed_pkg if f == pkg else f for f in FINGERPRINTED]
    assert _generated_problems(FINGERPRINTED, _tracked(), GENERATED) == []
    assert _fingerprint(sources) != _fingerprint(FINGERPRINTED)


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
    # The HDMI slot instantiates hcpu_gowin_top, so it carries the SD
    # controller too: +746 LUT4, +525 DFF and the buffer's BSRAM block.
    assert rows == {"IOB": (15, 384), "LUT4": (15994, 20736),
                    "DFF": (5134, 15552), "BSRAM": (18, 46)}
    assert re.search(r"^//\s+Fmax\s+115\.43 MHz", hdmi, re.M)

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
    # Re-measured 2026-09-15 after dvi_tx_open.v's TMDS encoder was repaired:
    # all three running-disparity branches accounted for an encoding their data
    # path did not perform, 30 of 256 bytes failed a decoder round trip, and
    # `disparity` ran to -10,240 in a signed [5:0] register that wraps at 31.
    # This wrapper instantiates that encoder, so it had to be placed again.
    # -9 LUT4, +1 DFF against 12,142 / 2,035.
    assert rows == {"IOB": (15, 384), "LUT4": (12133, 20736),
                    "DFF": (2036, 15552), "BSRAM": (0, 46)}
    assert re.search(r"^//\s+Fmax\s+104\.35 MHz", wrapper, re.M)

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


KABAH_BENCH_SOURCES = [
    "rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v",
    "rtl/hijaiyyah_kabah_top.v", "rtl/hijaiyyah_deserialiser.v",
    "rtl/hijaiyyah_jamrah_gate.v", "rtl/hijaiyyah_node_counter.v",
    "rtl/hijaiyyah_sponge.v", "rtl/hijaiyyah_ramal_impulse.v",
    "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_linear.v",
    "rtl/hijaiyyah_sbox.v", "rtl/hijaiyyah_round_constants.v",
    "rtl/hcpu_uart_rx.v", "rtl/hcpu_uart_tx.v",
    "rtl/tb/tb_hijaiyyah_kabah_gowin_top.v",
]
KABAH_L3_BENCH_SOURCES = ["rtl/hijaiyyah_hmac.v", "rtl/hijaiyyah_sha256_stream.v",
                          "rtl/hijaiyyah_sha256_core.v"]


def _kabah_bench(layer3: bool) -> str:
    out = "/tmp/tb_kabah_gowin_top_l3" if layer3 else "/tmp/tb_kabah_gowin_top"
    # The Makefile's order: the bench, then -- for layer 3 -- the file that
    # defines the macro, ahead of the wrapper it switches.
    bench, design = KABAH_BENCH_SOURCES[-1], KABAH_BENCH_SOURCES[:-1]
    sources = [bench, *(["rtl/fpga/gowin/kabah_with_hmac.vh"] if layer3 else []), *design,
               *(KABAH_L3_BENCH_SOURCES if layer3 else [])]
    build = subprocess.run(
        ["iverilog", "-g2012", "-I", "rtl",
         "-s", "tb_hijaiyyah_kabah_gowin_top", "-o", out, *sources],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["vvp", out], cwd=ROOT, capture_output=True, text=True, timeout=60)
    return run.stdout


def test_the_kabah_wrapper_dumps_exactly_cube_pys_state_over_simulated_uart() -> None:
    """
    The wrapper's own logic -- UART framing, the bit-serial feed, the
    permute-wait, the 200-byte dump -- is new code the RTL-direct kabah_top
    bench never exercised. This drives it the only way a board ever will: as
    bytes in on uart_rxd, bytes out on uart_txd, nothing touching bit_in or
    out_state directly. It caught a real bug before this test existed --
    tx_data raced dump_idx and byte 0 of every dump was skipped -- so it
    stays here as the thing that would catch it coming back.

    This is the wrapper WITHOUT layer 3 -- kabah_with_hmac.vh not read, no
    SHA-256 source read -- which is what Ka'bah over HDMI and the combined top
    build: 200 bytes a reply and nothing after them.
    """
    stdout = _kabah_bench(layer3=False)
    assert "PASS:" in stdout, stdout
    assert "400/400 bytes" in stdout
    assert "HMAC" not in stdout and "64/64" not in stdout


def test_the_uart_slot_signs_each_reply_over_simulated_uart() -> None:
    """Layer 3 in the UART slot (owner, 3 October 2026): with kabah_with_hmac.vh
    read first, as the slot's own build reads it, each 200-byte reply is
    followed by its 32-byte HMAC-SHA256 tag, and both are checked -- the state
    against cube.py, the tag against hmac/hashlib."""
    stdout = _kabah_bench(layer3=True)
    assert "PASS:" in stdout, stdout
    assert "400/400 bytes" in stdout and "64/64 bytes" in stdout


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
