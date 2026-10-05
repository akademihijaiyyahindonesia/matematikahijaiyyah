"""
The kabah/ folder describes the system; docs/kabah/ specifies the cipher. These
bind the system view to the code.

The claim this file exists to protect is the first sentence of the README, and
it is the one most easily lost: FOUR OF THE FIVE LAYERS PROVE NOTHING ABOUT
ORIGIN. Layer 3 carries all of it, layer 3 is standard HMAC-SHA256, and layer 3
is not in the RTL at all.
"""
from __future__ import annotations

import hashlib
import hmac
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


def _code(path: Path) -> str:
    """Verilog without its `//` comments: what synthesis reads."""
    return "\n".join(line.split("//", 1)[0]
                     for line in path.read_text(encoding="utf-8").splitlines())


HMAC_CORE = re.compile(r"\bhijaiyyah_(hmac|sha256_core|sha256_stream)\b")


def test_the_folder_says_layer_three_carries_everything_and_is_its_own_rtl_slot() -> None:
    """
    The sentence the whole folder is built around, checked as a fact rather
    than as a phrase. Until 1 October 2026 it was "there is no SHA-256 core in
    this repository". Since then the owner's decision puts the SHA-256/HMAC
    core in RTL as a slot of its own, and the fact held is narrower: rtl/*sha*
    and rtl/*hmac* are exactly that slot's modules, and neither
    hijaiyyah_kabah_top nor hijaiyyah_wave instantiates them -- Ka'bah's output
    stays unauthenticated until it is signed.
    """
    assert sorted(p.name for p in (ROOT / "rtl").glob("*sha*")) == [
        "hijaiyyah_sha256_core.v", "hijaiyyah_sha256_stream.v"]
    assert sorted(p.name for p in (ROOT / "rtl").glob("*hmac*")) == ["hijaiyyah_hmac.v"]
    for name in ("hijaiyyah_kabah_top.v", "hijaiyyah_wave.v"):
        assert not HMAC_CORE.search(_code(ROOT / "rtl" / name)), name

    readme, subsystem, silicon = (_text(n) for n in
                                  ("README.md", "SUBSYSTEM.md", "SILICON.md"))
    assert "SELURUHNYA" in readme
    assert "slot sendiri" in subsystem and "slot sendiri" in silicon
    assert "tidak di jalur `hijaiyyah_kabah_top`" in subsystem + silicon
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
    assert bits > 384


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
    for needle in ("58%", "165,98 MHz", "4,6 MB", "105%"):
        assert needle in silicon, needle
    for needle in ("58%", "165.98 MHz", "4.6 MB"):
        assert needle in wrapper, needle
    # with layer 3, the default since 3 October 2026
    for needle in ("15.030 / 20.736", "**72%**", "4.132 / 15.552", "Fmax\ntidak diklaim"):
        assert needle in silicon, needle
    for needle in ("15,030/ 20,736   72%", "4,132/ 15,552   26%", "FMAX IS NOT QUOTED"):
        assert needle in wrapper, needle

    # The gap this wrapper closes is the pin count, not the LUT count -- both
    # papers say so, not just one.
    assert "3%" in silicon and "2%" in silicon

    silicon = _text("SILICON.md")
    assert "1.665 bit port" in silicon and "384 IOB" in silicon
    assert "[EH]" in silicon
    # And the measured relationship between the two: each fits alone, the
    # naive sum does not, and the combined top level was actually measured
    # rather than extrapolated from the sum.
    assert "67%" in silicon and "58%" in silicon
    assert "125%" in silicon, "the naive sum has to stay visible next to 105%"
    assert "105%" in silicon and "960 sel" in silicon


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


# ══════════════════════════════════════════════════════════════════
#  Layer 3 in the UART slot -- the owner's decision of 3 October 2026
# ══════════════════════════════════════════════════════════════════

GOWIN = ROOT / "rtl" / "fpga" / "gowin"
RFC4231_TC1_KEY = bytes([0x0B]) * 20


def _preprocessed(path: Path, defined: bool) -> list[str]:
    """The code lines synthesis sees with KABAH_WITH_HMAC defined or not."""
    out: list[str] = []
    keep = [True]
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t.startswith("`ifdef KABAH_WITH_HMAC"):
            keep.append(defined)
        elif t.startswith("`else") and len(keep) > 1:
            keep[-1] = not keep[-1]
        elif t.startswith("`endif") and len(keep) > 1:
            keep.pop()
        elif all(keep) and t and not t.startswith("//"):
            out.append(line)
    return out


def test_the_uart_slot_instantiates_layer_three_and_the_other_tops_do_not() -> None:
    """
    The owner's target: HMAC-SHA256 instantiated by the Ka'bah path, in the
    UART slot only. kabah_hdmi_top.v and the combined top instantiate the
    wrapper itself, so the choice is a compile-time one, KABAH_WITH_HMAC: the
    slot's own build defines it and reads the three layer-3 sources; the other
    two builds define nothing, and then the wrapper holds no SHA-256 core.
    hijaiyyah_kabah_top and hijaiyyah_wave are held without it by the test
    above.
    """
    wrapper = GOWIN / "hijaiyyah_kabah_gowin_top.v"
    with_l3 = "\n".join(_preprocessed(wrapper, True))
    without = "\n".join(_preprocessed(wrapper, False))
    assert len(re.findall(r"\bhijaiyyah_hmac\s+u_hmac\b", with_l3)) == 1
    assert not HMAC_CORE.search(without)
    assert "reg [1:0] st;" in without and "reg [2:0] st;" in with_l3

    make = (GOWIN / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^KABAH_L3_DEFINE\s*=\s*kabah_with_hmac\.vh$", make, re.M)
    define = _code(GOWIN / "kabah_with_hmac.vh").strip()
    assert define == "`define KABAH_WITH_HMAC"
    # one added line gives the define and the three sources to the slot's two
    # targets alone; the recipes themselves are untouched
    assert re.search(r"^sim_kabah kabah_synth: KABAH_SOURCES := \$\(KABAH_L3_DEFINE\) "
                     r"\$\(KABAH_SOURCES\) \$\(KABAH_L3_SOURCES\)$", make, re.M)
    hdmi = make[make.index("KABAH_HDMI_SOURCES ="):make.index("kabah_hdmi_flash:")]
    assert "KABAH_L3" not in hdmi and "KABAH_WITH_HMAC" not in hdmi

    for name in ("kabah_hdmi_top.v", "hijaiyyah_cosmictera_gowin_top.v"):
        code = _code(GOWIN / name)
        assert re.search(r"\bhijaiyyah_kabah_gowin_top\s+u_kabah\b", code), name
        assert not HMAC_CORE.search(code) and "KABAH_WITH_HMAC" not in code, name


def test_without_layer_three_the_wrapper_is_the_text_it_was() -> None:
    """
    Why the switch is a macro and not a parameter, held as a fact. With the
    layer switched off by a parameter the same wrapper placed at 11,728 LUT4
    against the 12,133 recorded for Ka'bah over HDMI: synthesis is sensitive
    to the text it is given. So with KABAH_WITH_HMAC undefined every code line
    is the line the wrapper had at the commit before layer 3 went in.
    """
    before = subprocess.run(
        ["git", "show", "16a5763:rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    was = [line for line in before.splitlines()
           if line.strip() and not line.strip().startswith("//")]
    assert _preprocessed(GOWIN / "hijaiyyah_kabah_gowin_top.v", False) == was


def test_the_key_is_the_published_test_key_everywhere_and_is_called_one() -> None:
    """One key, in three places that must agree -- the bitstream, the bench's
    generator and the host tool -- and every page that names it says it is a
    public test key. A tag under it proves the path and secures nothing."""
    wrapper = _code(GOWIN / "hijaiyyah_kabah_gowin_top.v")
    assert re.search(r"HMAC_KEY\s*=\s*\{\{20\{8'h0b\}\},\s*352'd0\}", wrapper)

    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    sys.path.insert(0, str(ROOT / "rtl" / "tb"))
    import gen_kabah_uart_want
    import kabah_uart_test

    assert kabah_uart_test.TEST_KEY == gen_kabah_uart_want.TEST_KEY == RFC4231_TC1_KEY
    # RFC 4231, test case 1: the published vector for this key.
    assert hmac.new(RFC4231_TC1_KEY, b"Hi There", hashlib.sha256).hexdigest() == (
        "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7")

    header = (GOWIN / "hijaiyyah_kabah_gowin_top.v").read_text(encoding="utf-8")
    assert "THE KEY IS A PUBLIC TEST KEY" in header and "secures nothing" in header
    for page in ("SILICON.md", "FLOW.md", "SUBSYSTEM.md"):
        text = _text(page)
        assert "kunci uji publik" in text and "RFC 4231" in text, page
        assert "bukan mengamankan apa" in text, page


def test_a_reply_is_the_state_and_then_its_tag() -> None:
    """232 bytes on the wire: the 200 state bytes cube.py computes, then
    HMAC-SHA256 of exactly those bytes. The bench's golden tags are that, and
    the host tool computes the same thing with hmac/hashlib."""
    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    import kabah_uart_test as tool

    assert (tool.STATE_BYTES, tool.TAG_BYTES, tool.REPLY_BYTES) == (200, 32, 232)
    states = tool.expected_states(bytes(range(256)))
    for state, want, tag in zip(states, ("kabah_uart_want.hex", "kabah_uart_want2.hex"),
                                ("kabah_uart_tag.hex", "kabah_uart_tag2.hex"), strict=True):
        assert (ROOT / "rtl" / "tb" / want).read_text().strip() == state.hex()
        golden = (ROOT / "rtl" / "tb" / tag).read_text().strip()
        assert golden == hmac.new(RFC4231_TC1_KEY, state, hashlib.sha256).hexdigest()
        assert golden == tool.expected_tag(state).hex()

    out = subprocess.run([sys.executable, str(TOOL)], cwd=ROOT, capture_output=True,
                         text=True, check=True).stderr
    for i, state in enumerate(states, 1):
        assert f"frame{i} tag:  {tool.expected_tag(state).hex()}" in out


def test_the_new_bitstream_is_not_claimed_to_have_run_on_the_board() -> None:
    """Until the board run exists, every place that carries the layer-3
    figures says so; the 400/400 board result belongs to the wrapper without
    layer 3."""
    header = (GOWIN / "hijaiyyah_kabah_gowin_top.v").read_text(encoding="utf-8")
    assert "THIS BITSTREAM HAS NOT RUN ON THE BOARD" in header
    assert "Bitstream ini belum dijalankan di papan" in _text("SILICON.md")
