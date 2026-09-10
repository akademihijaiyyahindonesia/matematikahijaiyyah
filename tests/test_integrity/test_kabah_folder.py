"""
The kabah/ folder describes the system; docs/kabah/ specifies the cipher. These
bind the system view to the code.

The claim this file exists to protect is the first sentence of the README, and
it is the one most easily lost: FOUR OF THE FIVE LAYERS PROVE NOTHING ABOUT
ORIGIN. Layer 3 carries all of it, layer 3 is standard HMAC-SHA256, and layer 3
is not in the RTL at all.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from hijaiyyah.crypto import cube
from hijaiyyah.crypto.kabah import AUTHORITATIVE_LAYER, LAYERS, Kabah
from hijaiyyah.crypto.program import BUILD_PRODUCTS, SYSTEM_PATTERNS

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "kabah"
NAMES = ("README.md", "SUBSYSTEM.md", "FLOW.md", "SILICON.md")


def _text(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_the_folder_holds_and_indexes_its_documents() -> None:
    assert {p.name for p in DOCS.glob("*.md")} == set(NAMES)
    readme = _text("README.md")
    for name in NAMES[1:]:
        assert f"({name})" in readme, name
    # And it points at the specification rather than restating it.
    assert "docs/kabah/SPEC.md" in readme
    assert "docs/kabah/GAPS.md" in readme


def test_every_layer_appears_with_the_label_the_code_gives_it() -> None:
    readme = _text("README.md")
    for layer in LAYERS:
        assert layer.name in readme, layer.name
        if layer.label:
            assert layer.label in readme, f"{layer.name}: {layer.label}"
    assert AUTHORITATIVE_LAYER == 3


def test_the_folder_says_layer_three_carries_everything_and_is_not_in_rtl() -> None:
    """
    The sentence the whole folder is built around, checked as a fact rather
    than as a phrase: there is no SHA-256 core in this repository.
    """
    assert not list((ROOT / "rtl").glob("*sha*"))
    assert not list((ROOT / "rtl").glob("*hmac*"))

    readme, subsystem, silicon = (_text(n) for n in
                                  ("README.md", "SUBSYSTEM.md", "SILICON.md"))
    assert "SELURUHNYA" in readme
    assert re.search(r"tidak ada core SHA.256|tak ada core SHA.256",
                     subsystem + silicon, re.I)
    assert "AES-256-GCM" in readme, "the layer-4 refusal is missing"


def test_the_parameters_are_the_ones_cube_defines() -> None:
    readme = _text("README.md")
    state = cube.STATE_LANES * cube.LANE_BITS
    for value in (cube.STATE_LANES, cube.LANE_BITS, state, cube.RATE,
                  cube.CAPACITY_BITS, cube.SECURITY_BITS, cube.CIRCUITS,
                  len(cube.OUTER_RING), len(cube.CORE)):
        assert re.search(rf"\b{value:,}\b".replace(",", r"\.?"), readme), value
    assert f"0x{cube.POLYNOMIAL:X}" in readme
    assert f"0x{cube.AFFINE_C:X}" in readme
    assert "768" in readme and "27,4" in readme


def test_the_flow_page_matches_the_measured_trace() -> None:
    """
    The trace is the evidence for the whole cost story, and 622 = 2 x 310 is
    the part that says the permutation stalls rather than hides.
    """
    flow = _text("FLOW.md")
    for token in ("3.069", "383", "3.698", "9,66", "10,42",
                  "2,59 MB/s", "11,15 MB/s"):
        assert token in flow, token

    # The 622 = 2 x 310 identity is the evidence that the permutation stalls
    # rather than hides, so it is checked as a LINE stating the equality --
    # both numbers appear separately in the diagram above it, and a
    # substring search over the file passed while the claim was deleted.
    stated = [ln for ln in flow.splitlines()
              if "622" in ln and "310" in ln and ("=" in ln or "×" in ln)]
    assert len(stated) >= 2, stated          # the diagram and the claim
    assert any("tepat" in ln for ln in stated), "the equality is no longer asserted"
    assert 622 - 2 * 310 == 2

    numbers = Kabah.throughput()
    assert numbers["bottleneck"] == "deserialiser"
    assert "BOTTLENECK" in flow
    per_byte = 1.0 / numbers["paths"]["system_bit_serial"]["bytes_per_clock"]
    assert f"{per_byte:.2f}".replace(".", ",") in flow

    saving = numbers["triage_only_faster_by"]
    assert f"{saving:.2f}".replace(".", ",") in flow
    # Normalised across line breaks AND blockquote markers -- the sentence
    # wraps inside a `>` block, so plain whitespace joining leaves a stray `>`
    # in the middle of it.
    flat = " ".join(re.sub(r"^>\s?", "", flow, flags=re.M).split())
    assert "bukan karena apa yang ia hemat" in flat


def test_the_silicon_page_carries_the_numbers_the_rtl_header_carries() -> None:
    silicon = _text("SILICON.md")
    header = (ROOT / "rtl" / "hijaiyyah_kabah_top.v").read_text(encoding="utf-8")

    rows = dict(re.findall(r"^\|\s*(\d+)\s*\|\s*\*?\*?([\d.]+)\*?\*?\s*\|",
                           silicon, re.M))
    assert rows == {"8": "6.910", "25": "8.096"}, rows
    for lut in ("6,910", "8,096"):
        assert lut in header, lut

    # The stale pair is recorded as stale in both places.
    assert "7,426" in header and "7.426" in silicon
    assert "cd6a29c" in silicon


def test_the_silicon_page_states_why_kabah_fmax_is_unmeasurable() -> None:
    """
    Not "we have not got to it": the interface is wider than the device's pins.
    """
    top = (ROOT / "rtl" / "hijaiyyah_kabah_top.v").read_text(encoding="utf-8")
    head = top[top.index("module hijaiyyah_kabah_top"):top.index(");")]
    bits = sum(int(hi) + 1 for hi in re.findall(
        r"(?:input|output)\s+(?:wire|reg)?\s*\[\s*(\d+)\s*:\s*0\]", head))
    assert bits > 276


def test_the_silicon_page_carries_the_wrapper_numbers_too() -> None:
    """
    Not "the wrapper exists" as a claim -- the same measured-numbers
    discipline as everywhere else in this file: routed Fmax on the board it
    actually routes on, and the FAILS case named as a failure rather than
    left out.
    """
    silicon = _text("SILICON.md")
    wrapper = (ROOT / "rtl" / "fpga" / "gowin" / "hijaiyyah_kabah_gowin_top.v").read_text(
        encoding="utf-8")

    assert "hijaiyyah_kabah_gowin_top" in silicon
    for needle in ("140% — FAILS", "58%", "165,98 MHz", "4,6 MB",
                   "54.925.681"):
        assert needle in silicon, needle
    for needle in ("140%", "58%", "165.98 MHz", "4.6 MB", "54,925,681"):
        assert needle in wrapper, needle

    # The gap this wrapper closes is the pin count, not the LUT count -- both
    # papers say so, not just one.
    assert "3%" in silicon and "2%" in silicon

    silicon = _text("SILICON.md")
    assert "1.665 bit port" in silicon and "276 IOB" in silicon
    assert "[EH]" in silicon
    # And that Kabah and the HCPU cannot share the board. HCPU's own figure
    # here used to be 78% (rtl/hcpu_gowin_top.v's LAST_FITTING commit,
    # 096e392) -- the loader's write port pushed it to 161% several commits
    # later (see rtl/fpga/gowin/hcpu_gowin_top.v's bisection table) and this
    # page went on quoting the old number until ROADMAP.md's review caught it.
    assert "161%" in silicon and "94%" in silicon


def test_the_sealing_counts_come_from_program() -> None:
    subsystem = _text("SUBSYSTEM.md")
    assert f"{len(SYSTEM_PATTERNS)} pola sumber" in subsystem
    assert f"{len(BUILD_PRODUCTS)} produk build" in subsystem
    for magic in ("HMF1", "HEX1"):
        assert magic in subsystem
    # The examination phase default is -1, and the folder says why.
    assert "−1" in subsystem and "fase 0" in subsystem


@pytest.mark.parametrize("name", NAMES)
def test_no_page_promotes_layer_two_above_its_label(name: str) -> None:
    """
    Layer 2 is [EH]. A page that called the sponge proven would be the single
    most damaging error this folder could make.
    """
    text = _text(name)
    if "Absorption" in text or "spons" in text.lower():
        assert not re.search(r"spons.{0,40}(terbukti|aman secara)", text, re.I)
    assert "[VF]" not in text or "HMAC" in text


# ══════════════════════════════════════════════════════════════════
#  The host tool -- rtl/scripts/kabah_uart_test.py
# ══════════════════════════════════════════════════════════════════
#
# send_program.py has its own host-tool test in test_boot_path.py, right next
# to the loader it talks to; this is the same pattern for the wrapper Ka'bah
# is missing a host tool for until now. No board in a test run, so what is
# checked is that the computed expected bytes agree with the golden vectors
# rtl/tb/gen_kabah_uart_want.py already produced and tb_hijaiyyah_kabah_gowin_top.v
# already checked in simulation -- the same claim, verified a second way.

TOOL = ROOT / "rtl" / "scripts" / "kabah_uart_test.py"


def test_the_kabah_host_tool_reproduces_the_testbenchs_own_golden_vectors() -> None:
    out = subprocess.run([sys.executable, str(TOOL)],
                         cwd=ROOT, capture_output=True, text=True, check=True).stderr

    want1 = (ROOT / "rtl" / "tb" / "kabah_uart_want.hex").read_text().strip()
    want2 = (ROOT / "rtl" / "tb" / "kabah_uart_want2.hex").read_text().strip()
    assert f"frame1 want: {want1}" in out
    assert f"frame2 want: {want2}" in out


def test_the_kabah_host_tool_default_message_is_two_full_frames() -> None:
    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    import kabah_uart_test

    assert kabah_uart_test.RATE == cube.RATE == 128
    assert kabah_uart_test.STATE_BYTES == 200
    with pytest.raises(ValueError, match="multiple of 128"):
        kabah_uart_test.expected_states(bytes(127))
