"""
The cosmictera/ folder states numbers. Numbers in prose drift; numbers in code
do not. These tests bind the prose to the code so a doc cannot quietly become
a claim about a system that no longer exists -- which is exactly what happened
to the synthesis figures in the RTL header (R4) and to 11.15 MB/s (R5).

Every constant asserted here is read from the module that defines it, never
retyped. Retyping it here would just move the duplicate (R1).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from hijaiyyah.crypto import cube
from hijaiyyah.crypto.kabah import AUTHORITATIVE_LAYER, DESERIAL_CLOCKS_PER_BYTE, LAYERS, Kabah
from hijaiyyah.crypto.program import BUILD_PRODUCTS, SYSTEM_PATTERNS, defined_opcodes

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "cosmictera"
NAMES = ("README.md", "RULES.md", "SYSTEM.md", "CONCRETE.md", "COMPUTING.md", "CODEX.md")


def _text(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def _all() -> str:
    return "\n".join(_text(n) for n in NAMES)


def _row(text: str, label: str, cells: int) -> list[str]:
    """The cells of the one table row whose first cell contains `label`.

    Substring-anywhere assertions are too weak for a number that appears in
    several places: changing one occurrence leaves the others to satisfy the
    search. Two sabotages passed against exactly that hole before this existed.
    """
    hits = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cut = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if len(cut) == cells and label in cut[0]:
            hits.append(cut)
    assert len(hits) == 1, f"{label!r} x {cells} cols matched {len(hits)} rows"
    return hits[0]


# ══════════════════════════════════════════════════════════════════
#  The folder exists and is indexed
# ══════════════════════════════════════════════════════════════════

def test_the_folder_carries_exactly_the_four_documents_it_indexes() -> None:
    assert DOCS.is_dir()
    found = {p.name for p in DOCS.glob("*.md")}
    assert found == set(NAMES), found
    readme = _text("README.md")
    for name in NAMES[1:]:
        assert f"({name})" in readme, f"README does not link {name}"


# ══════════════════════════════════════════════════════════════════
#  Geometry and the sponge -- read from cube, not retyped
# ══════════════════════════════════════════════════════════════════

def test_the_geometry_in_the_prose_is_the_geometry_in_the_code() -> None:
    state_bits = cube.STATE_LANES * cube.LANE_BITS

    # The ring/core diagram is the one place the split is drawn. Parse it, so a
    # wrong number there cannot be covered by a right number somewhere else.
    system = _text("SYSTEM.md")
    lanes_bits = re.findall(r"^(cincin luar|inti)\s+(\d+) lajur\s+(\d+) bit",
                            system, re.M)
    assert len(lanes_bits) == 2, lanes_bits
    got = {name: (int(la), int(bi)) for name, la, bi in lanes_bits}
    assert got["cincin luar"] == (len(cube.OUTER_RING), cube.RATE_BITS)
    assert got["inti"] == (len(cube.CORE), cube.CAPACITY_BITS)

    # the summed line under the rule
    sums = re.findall(r"^\s{10,}(\d+) lajur\s+(\d+) bit", system, re.M)
    assert (int(sums[-1][0]), int(sums[-1][1])) == (cube.STATE_LANES, state_bits)

    text = _all()
    for value in (cube.RATE, cube.SECURITY_BITS, cube.CIRCUITS):
        assert re.search(rf"\b{value}\b", text), value

    # The ring and the core have to add up, in the code and on the page.
    assert len(cube.OUTER_RING) + len(cube.CORE) == cube.STATE_LANES
    assert cube.RATE_BITS + cube.CAPACITY_BITS == state_bits
    assert cube.SECURITY_BITS * 2 == cube.CAPACITY_BITS


def test_the_field_constants_are_quoted_in_hex_as_the_code_holds_them() -> None:
    text = _all()
    assert f"0x{cube.POLYNOMIAL:X}" in text
    assert f"0x{cube.AFFINE_C:X}" in text


def test_the_rotation_order_is_stated_and_factors_as_claimed() -> None:
    text = _all()
    assert "768" in text and "12 × 64" in text
    assert 12 * cube.LANE_BITS == 768
    # 28 rounds is 27.4x below the period -- the margin, stated.
    assert "27,4" in text
    assert abs(768 / cube.CIRCUITS - 27.4) < 0.1


# ══════════════════════════════════════════════════════════════════
#  Cost -- the numbers that were wrong by 4x
# ══════════════════════════════════════════════════════════════════

def test_the_cost_model_in_the_prose_matches_throughput() -> None:
    concrete = _text("CONCRETE.md")
    numbers = Kabah.throughput()
    paths = numbers["paths"]

    assert str(DESERIAL_CLOCKS_PER_BYTE) in concrete
    assert numbers["bottleneck"] == "deserialiser"
    assert "bottleneck" in concrete.lower()

    # Each figure is read out of its own table cell, so changing one occurrence
    # cannot hide behind another.
    per_clock = paths["system_bit_serial"]["bytes_per_clock"]
    row = _row(concrete, "Sistem terbangun", 4)
    assert row[1] == f"{1.0 / per_clock:.2f}".replace(".", ",")        # 10,42
    assert row[2] == f"{27_000_000 * per_clock / 1e6:.2f}".replace(".", ",")  # 2,59

    for label, key in (("Deserialiser", "deserialiser"),
                       ("Spons SLICE=25", "sponge_slice_25"),
                       ("Triase", "triage")):
        cells = _row(concrete, label, 4)
        want = 1.0 / paths[key]["bytes_per_clock"]
        assert cells[1] == f"{want:.2f}".replace(".", ","), (label, cells)

    for label, key in (("Triase semuanya", "triage"),
                       ("Deserialiser saja", "deserialiser"),
                       ("Sistem terbangun", "system_bit_serial")):
        cells = _row(concrete, label, 2)
        assert cells[-1] == f"{paths[key]['hours']:.1f}".replace(".", ","), label

    saving = f"{numbers['triage_only_faster_by']:.2f}".replace(".", ",")
    assert saving in concrete                                # 1,30


def test_the_prose_never_offers_the_sponge_rate_as_the_system_rate() -> None:
    """
    11.15 is the sponge's own figure and may appear -- but every page that
    prints it must say, on the same page, that it is not the system's.
    """
    for name in NAMES:
        text = _text(name)
        if "11,15" not in text:
            continue
        assert "2,59" in text, f"{name} quotes 11,15 without the system figure"
        assert re.search(r"spons saja|laju \*\*spons\*\*|bukan laju sistem",
                         text), f"{name} does not disclaim 11,15"


def test_the_measured_trace_is_arithmetically_consistent_on_the_page() -> None:
    concrete = _text("CONCRETE.md")
    for token in ("3.069", "383", "3.698", "622", "9,66", "10,42"):
        assert token in concrete, token
    # 622 held is exactly two permutations, and the page has to show why.
    assert "2 × 310" in concrete
    assert 622 - 2 * 310 == 2
    # 383 bytes is 2.99 rate blocks, which is why only two fired.
    assert 383 // cube.RATE == 2
    assert "2,99" in concrete


# ══════════════════════════════════════════════════════════════════
#  Layers, sealing, and the limits
# ══════════════════════════════════════════════════════════════════

def test_every_layer_appears_with_the_label_the_code_gives_it() -> None:
    text = _all()
    for layer in LAYERS:
        assert layer.name in text, layer.name
        if layer.label:
            assert layer.label in text, f"{layer.name}: {layer.label}"
    assert str(AUTHORITATIVE_LAYER) in text
    assert re.search(r"[Ll]apis 3.*(seluruh|satu.?satunya)", text)


def test_the_sealing_counts_come_from_program_not_from_prose() -> None:
    text = _all()
    assert str(len(SYSTEM_PATTERNS)) in text
    assert str(len(BUILD_PRODUCTS)) in text
    for magic in ("HMF1", "HEX1"):
        assert magic in text

    # Read the opcode count out of its own table cell. As a search over the
    # whole folder this passed while the table said 66 and the code said 67,
    # because "67" happened to occur elsewhere -- the same substring-anywhere
    # hole that two other assertions here already had to lose.
    cells = _row(_text("CONCRETE.md"), "Opcode H‑ISA", 3)
    assert cells[1].split()[0] == str(len(defined_opcodes())), cells

    # The lookbehind matters: without it `LETTER_OP_FIRST` and `LETTER_OP_LAST`
    # match on their tails and two range bounds get counted as opcodes. That is
    # the same class of error as OP_MSB/OP_LSB, arriving by regex rather than by
    # name -- so the count is of things actually defined as 8-bit opcodes.
    rtl_ops = set(re.findall(r"(?<![A-Z0-9_])OP_[A-Z0-9_]+\s+8'h",
                             (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")))
    cells = _row(_text("CONCRETE.md"), "Opcode berencoding RTL", 3)
    assert cells[1] == str(len(rtl_ops)), (cells, len(rtl_ops))


def test_the_refusals_and_the_unmeasured_are_stated_not_buried() -> None:
    text = _all()
    assert "AES-256-GCM" in text or "AES‑256‑GCM" in text
    assert "Fmax" in text
    assert "[EH]" in text and "[AT]" in text
    # No SHA-256 core in RTL: the doc must say so, and it must stay true.
    assert re.search(r"tidak ada core SHA.256|SHA.256 di RTL", text, re.I)
    assert not list((ROOT / "rtl").glob("*sha*"))


# ══════════════════════════════════════════════════════════════════
#  The rules cite incidents that really happened
# ══════════════════════════════════════════════════════════════════

def test_each_rule_carries_a_scar() -> None:
    rules = _text("RULES.md")
    headings = re.findall(r"^## (R\d+) — (.+)$", rules, re.M)
    assert len(headings) >= 10, headings
    numbers = [int(r[1:]) for r, _ in headings]
    assert numbers == sorted(numbers) == list(range(1, len(numbers) + 1))

    # Split on the headings and require an incident in each section.
    parts = re.split(r"^## R\d+ — .+$", rules, flags=re.M)[1:]
    for (rule, title), body in zip(headings, parts, strict=True):
        assert "Bekas luka" in body or "bekas luka" in body, f"{rule} ({title})"


def test_the_stale_synthesis_incident_names_the_commits_that_caused_it() -> None:
    """R4 exists because a header went stale between two commits. Both must be
    real, and the second must really touch the module."""
    rules = _text("RULES.md")
    assert "cd6a29c" in rules and "4e0555e" in rules
    for sha in ("cd6a29c", "4e0555e"):
        out = subprocess.run(["git", "cat-file", "-t", sha], cwd=ROOT,
                             capture_output=True, text=True)
        assert out.stdout.strip() == "commit", sha
    touched = subprocess.run(
        ["git", "show", "--name-only", "--format=", "4e0555e"],
        cwd=ROOT, capture_output=True, text=True).stdout
    assert "rtl/hijaiyyah_kabah_top.v" in touched


# ══════════════════════════════════════════════════════════════════
#  Silicon -- freshly measured, and the header has to agree
# ══════════════════════════════════════════════════════════════════

def test_the_silicon_figures_agree_with_the_rtl_header() -> None:
    concrete = _text("CONCRETE.md")
    header = (ROOT / "rtl" / "hijaiyyah_kabah_top.v").read_text(encoding="utf-8")
    for lut in ("6,910", "8,096"):
        assert lut in header, lut
        assert lut.replace(",", ".") in concrete, lut
    assert "8,640" in header and "8.640" in concrete
    # And the stale pair must be recorded as stale in both places.
    assert "7,426" in header and "7.426" in concrete


def test_the_thesis_is_stated_in_the_readme() -> None:
    readme = _text("README.md")
    assert "Bahan sama" in readme
    assert "racikan" in readme.lower() and "rumus" in readme.lower()
    # The mechanism/summary structure, not three parallel principles.
    assert re.search(r"dirangkum oleh rotasi", readme)
    assert "bukan prinsip" in readme.lower()
