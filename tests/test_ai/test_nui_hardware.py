"""Layer 6.1's hardware inventory, held to the evidence it was built from.

The owner opened Layer 6, Hardware Intelligence, on 27 September 2026: take
stock of the hardware from what is already recorded -- no RTL, no board, no
sensor, no debug port, no new telemetry -- and keep MEASURED (proven
physically), SIMULATED (RTL or interpreter) and UNKNOWN (no path observes it)
apart. Every answer carries hardware, evidence, source, run and hash.

What is held here: the inventory reads back exactly from its sources; a class
follows its evidence; MEASURED rests on the board; UNKNOWN has no value; each
of the owner's questions has an answer; every piece of evidence is already
committed; and a Markdown page's hash moves only when a cited line does.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import hardware  # noqa: E402

MODEL = json.loads(hardware.MODEL.read_text(encoding="utf-8"))
SPEC = hardware.load()
#: The rules hold for what is committed AND for what the spec builds today, so
#: a spec that breaks one cannot be hidden by regenerating the model.
BOTH = pytest.mark.parametrize("model", [MODEL, json.loads(json.dumps(hardware.build()))],
                               ids=["committed", "built"])
BOARD_RECORD = re.compile(r"cosmictera-build/(burn-in|parity-board|attack-lab)/")
BOARD_PAGES = {"cosmictera-build/PAPAN.md", "cosmictera-build/OFF.md", "NUI/layer4_freeze.json"}


def test_the_inventory_reads_back_exactly() -> None:
    assert hardware.verify() == []


def test_the_page_is_drawn_from_the_inventory() -> None:
    assert hardware.PAGE.read_text(encoding="utf-8") == hardware.page(MODEL)


@BOTH
def test_a_class_follows_its_evidence_kind(model: dict) -> None:  # type: ignore[type-arg]
    for item in model["items"]:
        assert item["evidence_kind"] in SPEC["classes"][item["class"]]["evidence_kinds"], item["id"]
    assert model["counts"] == {c: sum(1 for i in model["items"] if i["class"] == c)
                               for c in hardware.CLASSES}


def _board(path: str) -> bool:
    if BOARD_RECORD.match(path) or path in BOARD_PAGES:
        return True
    if path.startswith("facts/"):
        fact = json.loads((ROOT / path).read_text(encoding="utf-8"))
        return bool(fact["confidence"] == "board-measured")
    return False


@BOTH
def test_measured_rests_on_the_board(model: dict) -> None:  # type: ignore[type-arg]
    """MEASURED means proven physically: a committed board record, a
    board-measured fact, a board section of PAPAN.md or OFF.md, or the Layer 4
    freeze built from board records. Nothing else makes an item MEASURED."""
    for item in model["items"]:
        paths = [e["path"] for e in item["evidence"]] + (
            [item["source"]["path"]] if item["source"] else [])
        if item["class"] == "MEASURED":
            assert any(_board(p) for p in paths), item["id"]


@BOTH
def test_unknown_has_no_value_and_the_others_have_one(model: dict) -> None:  # type: ignore[type-arg]
    for item in model["items"]:
        if item["class"] == "UNKNOWN":
            assert item["value"] is None and item["source"] is None, item["id"]
        else:
            assert item["value"] is not None and item["source"]["sha256"], item["id"]
        assert item["evidence"] and all(e["sha256"] for e in item["evidence"]), item["id"]


def test_every_question_of_the_owner_is_answered() -> None:
    assert set(MODEL["questions"]) == {"hardware", "fpga", "cpu", "clock", "memory",
                                       "peripheral", "program", "telemetry"}
    for key in MODEL["questions"]:
        assert any(key in i["answers"] for i in MODEL["items"]), key


@BOTH
def test_what_the_evidence_says_the_hardware_is(model: dict) -> None:  # type: ignore[type-arg]
    items = {i["id"]: i for i in model["items"]}
    assert items["board"]["value"] == "Tang Nano 20K"
    assert items["fpga_device"]["value"] == "GW2AR-LV18QN88C8/I7"
    assert items["clock"]["value"] == "27 MHz" and items["clock_pll"]["value"] == "0"
    assert items["uart"]["value"] == "115200"
    no_source = json.loads((ROOT / "facts/telemetry/four_fields_have_no_source.json")
                           .read_text(encoding="utf-8"))["value"]
    assert items["telemetry_fields"]["value"] == 27 - no_source
    assert items["program_now"]["class"] == "UNKNOWN"


def test_every_piece_of_evidence_is_already_committed() -> None:
    """Layer 6.1 starts from evidence that exists: nothing it rests on is new
    or outside the repository."""
    tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.split("\n"))
    for item in MODEL["items"]:
        for path in [e["path"] for e in item["evidence"]] + (
                [item["source"]["path"]] if item["source"] else []):
            assert path in tracked, (item["id"], path)


def test_a_page_hash_moves_only_with_the_lines_it_cites(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    page = tmp_path / "PAGE.md"
    page.write_text("# title\n## Tahap 1 — kartu\nother\n", encoding="utf-8")
    monkeypatch.setattr(hardware, "ROOT", tmp_path)
    item = {"id": "x", "value": {"file": "PAGE.md", "pattern": "^## (Tahap 1[^\\n]*)"}}
    before = hardware._evidence("PAGE.md", item)
    page.write_text("# title changed\n## Tahap 1 — kartu\nother edited\n", encoding="utf-8")
    assert hardware._evidence("PAGE.md", item)["sha256"] == before["sha256"]
    page.write_text("# title\n## Tahap 1 — kartu, dibetulkan\nother\n", encoding="utf-8")
    assert hardware._evidence("PAGE.md", item)["sha256"] != before["sha256"]
    with pytest.raises(LookupError, match="without the lines it cites"):
        hardware._evidence("PAGE.md", {"id": "y", "value": None})
