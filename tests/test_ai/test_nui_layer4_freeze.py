"""Layer 4 frozen, held to the records it rests on.

The owner's step P7, 26 September 2026: freeze the evidence of P0-P6, write
the final discrepancy report in four classes -- measured mismatch, known
semantic difference, unknown or not observable, and known tooling
discrepancy, the last never mixed with the rest -- and let Layer 4 be done not
because every colour is green but because every colour has a source.

What is held for as long as the freeze exists: the records' own bytes, and
what those records say when read again. What was derived from them at the
freeze -- the parity model, the frozen expectation -- is written down for the
tag and may be rebuilt afterwards; the verdicts it gives on the frozen records
may not change.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.hisa.opcodes import OpCode  # noqa: E402
from hijaiyyah.nui import layer4_freeze as l4  # noqa: E402

FROZEN = json.loads(l4.MODEL.read_text(encoding="utf-8"))
HARDWARE = ("measured_mismatch", "known_semantic_difference", "unknown_not_observable")


def test_what_the_records_say_is_what_the_freeze_wrote_down() -> None:
    assert l4.verify(FROZEN) == []


def test_the_page_is_drawn_from_the_freeze() -> None:
    assert l4.PAGE.read_text(encoding="utf-8") == l4.page(FROZEN)


def test_every_record_is_committed_and_its_bytes_have_not_moved() -> None:
    """The evidence is the record itself. A record rewritten after the freeze
    -- a report recomputed, a log edited -- is red here, by its hash."""
    tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.split("\n"))
    assert [e["phase"] for e in FROZEN["evidence"]].count("P0") == 3
    assert {e["phase"] for e in FROZEN["evidence"]} == {f"P{i}" for i in range(7)} - {"P3"}
    for e in FROZEN["evidence"]:
        assert e["path"] in tracked, e["path"]
        assert l4._sha(e["path"]) == e["sha256"], e["path"]


def test_the_verdicts_on_the_frozen_records_do_not_change() -> None:
    """Recomputed with today's code and today's expectation, every board
    report gives the same verdict on every program. At the freeze the only
    other difference was the exclusion reason of a program never sent,
    moved by P6's refreeze -- named, and the P2 reports left as they were."""
    for row in l4.reproducibility():
        assert row["verdicts_reproduce"], row["record"]
    for row in FROZEN["reproducibility"]:
        assert row["differs_at"] in ([], [l4.KNOWN_REPORT_DIFFERENCE]), row
    moved = {r["record"] for r in FROZEN["reproducibility"] if r["differs_at"]}
    assert moved == {l4.PARITY_CONTAMINATED, l4.PARITY_OF_RECORD}


def test_every_colour_is_counted_and_none_is_forced() -> None:
    s = FROZEN["status"]
    report = json.loads((ROOT / (l4.PARITY_OF_RECORD[:-5] + ".report.json"))
                        .read_text(encoding="utf-8"))
    assert s["programs"] == report["counts"] == {"PARITY": 73, "MISMATCH": 2, "UNKNOWN": 28}
    assert sum(s["opcodes"].values()) == len(OpCode)
    assert s["opcodes"] == {"PARITY": 74, "MISMATCH": 0, "UNKNOWN": 31}
    assert s["stop_probes"] == {"PARITY": 0, "MISMATCH": 3, "UNKNOWN": 3}
    assert s["loader_cases"]["findings"] == 0


def _ids(cls: str) -> dict[str, dict]:  # type: ignore[type-arg]
    return {e["id"]: e for e in FROZEN["discrepancies"][cls]}


def test_the_owners_classes_hold_what_the_records_show() -> None:
    measured = _ids("measured_mismatch")
    assert measured["print_large_values_in_p2"]["items"] == [
        "rtl/programs/bench/e4_frame.hasm", "rtl/programs/test_hisab.hasm"]
    assert measured["print_ladder_in_p4"]["first"] == "2^23"
    semantic = _ids("known_semantic_difference")["counter_programs"]["items"]
    assert semantic == [f"rtl/programs/{n}.hasm" for n in
                        ("timer_poll", "trap_resume", "trap_shadow", "trap_timer")]
    unknown = _ids("unknown_not_observable")
    assert unknown["opcodes_with_mixed_evidence"]["items"] == [
        "HALT", "HCRC", "HLOAD", "HPACK", "PRINT"]
    assert len(unknown["register_and_ram_after_a_stop"]["items"]) == 3


def test_a_tooling_discrepancy_is_never_counted_as_the_boards() -> None:
    """The host misreading the wire is not the board answering wrong. The
    program the stale burn-in bytes landed on stands in no hardware class,
    and no tooling id appears in one."""
    tooling = _ids("known_tooling_discrepancy")
    assert set(tooling) == {"burn_in_parser_artifacts", "cycles_report_one_byte_out",
                            "stale_burn_in_bytes_in_the_first_p2_run"}
    hardware_items = {i for cls in HARDWARE for e in FROZEN["discrepancies"][cls]
                      for i in e.get("items", [])}
    hardware_ids = {e["id"] for cls in HARDWARE for e in FROZEN["discrepancies"][cls]}
    assert not set(tooling) & hardware_ids
    assert tooling["stale_burn_in_bytes_in_the_first_p2_run"]["program"] not in hardware_items
    cycles = tooling["cycles_report_one_byte_out"]
    assert cycles["count"] == cycles["of"] > 0
    assert tooling["burn_in_parser_artifacts"]["count"] == 2


def test_every_record_that_names_the_bitstream_names_the_same_one() -> None:
    carried = FROZEN["bitstream_carried_by"]
    assert len(carried) == 7 and all(carried.values()), carried
    assert FROZEN["bitstream_sha256"].startswith("84fdc912")


def test_the_tag_carries_the_day_of_the_freeze_not_the_burn_ins() -> None:
    """The owner, 26 September 2026: the tag's date is the freeze's, not the
    day the burn-in ended."""
    assert FROZEN["tag"] == l4.TAG == "layer4-freeze-2026-09-26"
