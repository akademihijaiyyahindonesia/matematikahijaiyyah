"""CHECKSUM32, held to one reading across the three places that compute it.

The owner's step P6, 26 September 2026, on K-8 and K-10: one 32-bit sum, mod
2^32, over the sector-16 table entry, the container's header with its own
checksum field counted as zero, the relocation table and the program words --
and nothing outside the container. The owner's condition before calling it
final: decide the canonical byte and word order and test it, so that the
builder, the Python loader and the HCPU loader do not hold three different
ideas of what is being summed.

So the order is tested first, against the two places that already fix it -- the
SD buffer in rtl/hcpu_sdio.v and the wire in send_program.py. Then every
loader case in rtl/scripts/attack_lab.py is judged three times: the category's
intent (the owner's), the Python loader's verdict on the case's card, and the
simulated HCPU loader's verdict on the SAME card, bit for bit. The three must
agree on every case, and the owner's six categories each have one of their own.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
TB = ROOT / "rtl" / "tb"

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from attack_lab import INTENT, base_container, cases  # noqa: E402
from build_container import (  # noqa: E402
    CHECKSUM_AT,
    FLAGS_VALID,
    PROGRAM_ID,
    START_SECTOR,
    VERSION,
    card_bytes,
    card_image,
    card_words,
    checksum32,
    load_check,
    table_record,
)
from send_program import encode  # noqa: E402

CASES = cases(base_container())
OWNER_SIX = ("header", "program-table", "relocation", "program-body",
             "checksum-field", "out-of-container")


# -- one order ------------------------------------------------------------------------


def test_the_card_holds_a_word_most_significant_byte_first() -> None:
    """rtl/hcpu_sdio.v fixes it -- buf[31:24] is byte 0 -- and the Python side
    must read the same bytes into the same words."""
    sdio = (ROOT / "rtl" / "hcpu_sdio.v").read_text(encoding="utf-8")
    assert "most significant byte\n    // first: buf[31:24] is byte 0" in sdio
    assert card_bytes([0x01020304, 0xA0B0C0D0]) == bytes.fromhex("01020304A0B0C0D0")
    container = base_container()
    assert card_words(card_bytes(container)) == container


def test_the_wire_carries_the_same_words_in_the_same_order() -> None:
    """send_program.py frames a container for sd_writer: a count, then each word
    most significant byte first -- the order the card keeps it in."""
    container = base_container()
    stream = encode(container)
    assert stream[:4] == len(container).to_bytes(4, "big")
    assert stream[4:] == card_bytes(container)


def test_the_table_entry_is_the_one_sd_writer_writes() -> None:
    """PROGRAM_ID, FLAGS and START_SECTOR in the builder are read back out of
    rtl/programs/sd_writer.hasm, the program that really writes sector 16."""
    text = (ROOT / "rtl" / "programs" / "sd_writer.hasm").read_text(encoding="utf-8")
    found = {m.group(2): int(m.group(1)) for m in re.finditer(
        r"MOVI\s+R1,\s*(\d+)\s*;\s*(PROGRAM_ID|FLAGS|START_SECTOR)", text)}
    assert found == {"PROGRAM_ID": PROGRAM_ID, "FLAGS": FLAGS_VALID,
                     "START_SECTOR": START_SECTOR}
    assert table_record(129) == [1, 1, 17, 2], "SECTOR_COUNT rounds up"


def test_the_sum_is_the_owners_definition_written_out() -> None:
    """CHECKSUM32 by hand, from K-10's words, against the builder's: the record,
    then the header with the checksum as zero, the table, the program."""
    container = base_container()
    record = table_record(len(container))
    by_hand = sum(record) + sum(w for i, w in enumerate(container) if i != CHECKSUM_AT)
    assert container[CHECKSUM_AT] == checksum32(record, container) == by_hand % 2 ** 32
    assert container[1] == VERSION == 2


# -- the Python loader against the owner's intent --------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[str(c["id"]) for c in CASES])
def test_the_python_loader_does_what_the_category_asks(case: dict[str, Any]) -> None:
    assert case["expect"] == case["intent"] == INTENT[str(case["category"])], case["by"]
    assert load_check(case["card"]) == (case["expect"] == "accept", case["by"])


def test_each_of_the_owners_six_categories_has_its_own_case() -> None:
    have = {str(c["category"]) for c in CASES}
    assert set(OWNER_SIX) <= have, set(OWNER_SIX) - have
    for category in OWNER_SIX[:-1]:
        assert any(c["category"] == category and c["by"] == "CHECKSUM32"
                   for c in CASES), f"{category}: no case the sum alone refuses"


def test_what_version_one_let_through_is_refused_now() -> None:
    """The attack lab's two accepted cases of 20 September 2026 are why K-8
    exists. They are CHECKSUM32's to refuse now, not a range check's."""
    by_id = {c["id"]: c for c in CASES}
    for cid in ("words_plus_one", "reloc_index_moved"):
        assert (by_id[cid]["expect"], by_id[cid]["by"]) == ("reject", "CHECKSUM32"), cid


def test_the_limits_of_a_sum_are_named_not_hidden() -> None:
    """A sum is public and does not see order: two words exchanged, or a body
    changed and resealed, both load. Written down as what K-10's algorithm
    is, not as a defect of this implementation."""
    by_id = {c["id"]: c for c in CASES}
    for cid in ("words_swapped", "body_changed_and_resealed"):
        assert by_id[cid]["expect"] == "accept"
        assert by_id[cid]["category"] == "limit-of-a-sum"
    assert card_image(by_id["words_swapped"]["stream"]) != card_image(base_container())


# -- the HCPU loader against the Python one ---------------------------------------------

HAVE_SIM = shutil.which("iverilog") is not None and shutil.which("vvp") is not None


@pytest.fixture(scope="module")
def bench() -> Path:
    if not HAVE_SIM and os.environ.get("HOM_REQUIRE_IVERILOG") != "1":
        pytest.skip("Icarus Verilog is required to run the HCPU loader")
    subprocess.run(["make", "-s", "tb_hcpu_prog_load_card.vvp", "shell_progload.hex"],
                   cwd=TB, check=True, capture_output=True)
    return TB / "tb_hcpu_prog_load_card.vvp"


def _hcpu(bench: Path, card: dict[int, list[int]]) -> dict[str, int]:
    words = [w for s in range(16, 24) for w in card.get(s, [0] * 128)]
    with tempfile.NamedTemporaryFile("w", suffix=".hex", delete=False) as fh:
        fh.write("\n".join(f"{w:08X}" for w in words) + "\n")
        name = fh.name
    try:
        out = subprocess.run(["vvp", bench.name, f"+CARD={name}"], cwd=TB,
                             capture_output=True, text=True, timeout=600).stdout
    finally:
        os.unlink(name)
    line = next(ln for ln in out.splitlines() if ln.startswith("DONE="))
    return {k: int(v) for k, v in (p.split("=") for p in line.split())}


def test_the_hcpu_loader_gives_the_python_loaders_verdict_on_every_card(
        bench: Path) -> None:
    """Same card, bit for bit, to both loaders. One run of the simulated HCPU per
    case, in parallel: the probe asks for PROGRAM_ID 1 and records the answer."""
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
        got = dict(zip([c["id"] for c in CASES],
                       pool.map(lambda c: _hcpu(bench, c["card"]), CASES), strict=True))
    wrong = []
    for case in CASES:
        answer = got[case["id"]]
        want = 1 if case["expect"] == "accept" else 0
        if (answer["DONE"], answer["ANSWER"], answer["ABSENT"]) != (1, want, 0):
            wrong.append((case["id"], case["expect"], answer))
    assert not wrong, wrong
