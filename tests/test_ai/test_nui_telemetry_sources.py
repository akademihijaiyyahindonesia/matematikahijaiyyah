"""Layer 6.2's telemetry sources, held to the contract and the evidence.

The owner's step 6.2, 27 September 2026: an inventory of the telemetry sources
that already exist -- not a hardware project -- and the distinction that a
source that exists is not a source that is streaming. What is held here, on
the committed registry and on what the spec builds today:

    the 27 fields are the contract's, read from cosmictera/TELEMETRY.md;
    a field is MEASURED exactly when the contract gives it a source;
    the four without one stay UNKNOWN, mapped to no RTL signal;
    nothing is live, because no live source is registered;
    every board run is committed and hashed;
    the RTL's tele_* signals are simulated, not a board stream;
    and the build refuses a spec that disagrees with the contract.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import telemetry_sources as ts  # noqa: E402

MODEL = json.loads(ts.MODEL.read_text(encoding="utf-8"))
BOTH = pytest.mark.parametrize("model", [MODEL, json.loads(json.dumps(ts.build()))],
                               ids=["committed", "built"])
FOUR = ["anomaly_score", "corruption_score", "state_hash", "last_relocation"]


def test_the_registry_reads_back_exactly() -> None:
    assert ts.verify() == []


def test_the_page_is_drawn_from_the_registry() -> None:
    assert ts.PAGE.read_text(encoding="utf-8") == ts.page(MODEL)


@BOTH
def test_the_fields_are_the_contracts_and_measured_means_it_has_a_source(
        model: dict[str, Any]) -> None:
    rows = ts.contract()
    assert [r["field"] for r in model["registry"]] == [r["field"] for r in rows]
    assert len(rows) == 27
    for r, row in zip(model["registry"], rows, strict=True):
        assert (r["status"] == "MEASURED") == row["today"].startswith("**ada"), r["field"]


@BOTH
def test_the_four_without_a_source_stay_unknown(model: dict[str, Any]) -> None:
    """Nothing fills them -- not an RTL signal's name, not a guess."""
    fact = json.loads((ROOT / "facts/telemetry/four_fields_have_no_source.json")
                      .read_text(encoding="utf-8"))
    missing = [m["field"] for m in model["missing"]]
    assert missing == FOUR and all(f in fact["statement"] for f in FOUR)
    for r in model["registry"]:
        if r["field"] in FOUR:
            assert (r["status"], r["live_or_historical"], r["board_run"], r["sha256"]) == (
                "UNKNOWN", ts.UNKNOWN, None, None)
            assert "tele_" not in json.dumps(r)


@BOTH
def test_a_source_that_exists_is_not_a_source_that_streams(model: dict[str, Any]) -> None:
    assert model["live_sources"] == []
    assert all(r["live_or_historical"] != ts.LIVE for r in model["registry"])
    for r in model["registry"]:
        if r["status"] == "MEASURED":
            assert r["live_or_historical"] == ts.HISTORICAL, r["field"]
    live = next(m for m in model["matrix"] if m["source"].startswith("live"))
    assert live["status"] == "UNKNOWN / tidak mengalir"


@BOTH
def test_every_board_run_is_committed_and_hashed(model: dict[str, Any]) -> None:
    tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.split("\n"))
    for r in model["registry"]:
        for e in r["evidence"]:
            assert e["path"] in tracked and e["sha256"], (r["field"], e["path"])
        if r["status"] == "MEASURED":
            board = [e for e in r["evidence"] if e["path"] == r["board_run"]]
            assert board and board[0]["sha256"] == r["sha256"], r["field"]


@BOTH
def test_the_rtl_signals_are_simulated_and_not_a_board_stream(model: dict[str, Any]) -> None:
    names = [s["name"] for s in model["rtl_signals"]["signals"]]
    assert names == ["tele_pc", "tele_instr", "tele_halted", "tele_guard", "tele_cycles",
                     "tele_flags"]
    assert all(s["status"] == "SIMULATED" for s in model["rtl_signals"]["signals"])
    assert ts.access("tele_cycles", model) == ts.SIMULATED
    assert ts.access("uptime", model) == ts.HISTORICAL
    assert ts.access("state_hash", model) == ts.UNKNOWN
    assert ts.access("no_such_field", model) == ts.UNKNOWN


@BOTH
def test_the_matrix_is_the_owners_five_rows(model: dict[str, Any]) -> None:
    assert [m["source"] for m in model["matrix"]] == [
        "UART/Tang Nano board runs", "historical board recordings",
        "live hardware telemetry sekarang", "4 medan tanpa sumber",
        "RTL telemetry signals tele_*"]
    measured = sum(1 for r in model["registry"] if r["status"] == "MEASURED")
    assert model["matrix"][0]["coverage"].startswith(f"{measured}/27") and measured == 23


def test_a_page_hash_moves_only_with_the_lines_it_cites(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from hijaiyyah.nui import hardware
    page = tmp_path / "PAGE.md"
    page.write_text("# a\n| avalanche | 0,4995 |\nother\n", encoding="utf-8")
    monkeypatch.setattr(ts, "ROOT", tmp_path)
    monkeypatch.setattr(hardware, "ROOT", tmp_path)
    cite = {"PAGE.md": "^\\| avalanche"}
    before = ts._hash("PAGE.md", cite)["sha256"]
    page.write_text("# b\n| avalanche | 0,4995 |\nother, edited\n", encoding="utf-8")
    assert ts._hash("PAGE.md", cite)["sha256"] == before
    page.write_text("# a\n| avalanche | 0,5 |\nother\n", encoding="utf-8")
    assert ts._hash("PAGE.md", cite)["sha256"] != before


def test_the_build_refuses_a_spec_that_disagrees_with_the_contract(
        monkeypatch: pytest.MonkeyPatch) -> None:
    spec = ts.load()
    spec["fields"]["anomaly_score"]["source_kind"] = "board_program"
    monkeypatch.setattr(ts, "load", lambda: spec)
    with pytest.raises(LookupError, match="anomaly_score"):
        ts.build()


def test_a_registered_live_source_would_be_named_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """The boundary is a rule, not a label: were a live source registered, its
    field would read live; today none is."""
    spec = ts.load()
    spec["live_sources"] = ["uptime"]
    monkeypatch.setattr(ts, "load", lambda: spec)
    model = json.loads(json.dumps(ts.build()))
    assert ts.access("uptime", model) == ts.LIVE
    assert ts.access("cycle_rate", model) == ts.HISTORICAL
