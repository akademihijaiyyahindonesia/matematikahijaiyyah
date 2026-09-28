"""rtl/programs/loader.hasm as a function, held to its two benches.

The fifth item of the Layer 6 order of 28 September 2026: the loader, with
rtl/tb/tb_gowin_loader.v and rtl/tb/tb_gowin_loader_nui.v as oracles -- not
assumed to be one: what each runs and checks is measured, and coverage is kept
per bench, then as union and intersection. loader.hasm, the RTL and both
benches are unchanged. What is held here:

    at every MMIO read boundary of both benches, from the RTL's own state and
    from reset alike, the function gives the RTL's next state and every event
    between -- register writes, MMIO stores, instruction-memory writes, ERET;
    the owner's list -- RX_STATUS, RX_DATA, IMEM_ADDR, IMEM_DATA, TRAP_EPC,
    TRAP_MODE, ERET -- appears in the RTL's own trace in that order;
    the entry is never fetched before ERET: the loader's one JMP is its
    receive loop;
    what each bench checks is what the function predicts;
    the path neither bench runs is named, not claimed; and each covered rule,
    broken, is red, while the uncovered one, broken, stays unseen.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import rtl_function as rf  # noqa: E402

MODEL = json.loads(rf.MODEL.read_text(encoding="utf-8"))
SPEC = next(m for m in rf.load()["modules"] if m["name"] == "loader")
M = next(m for m in MODEL["modules"] if m["name"] == "loader")
BENCHES = ("tb_gowin_loader", "tb_gowin_loader_nui")


@pytest.fixture(scope="module")
def runs() -> list[dict[str, Any]]:
    return rf.loader_runs(SPEC)


def test_every_boundary_of_both_benches_is_the_rtls() -> None:
    assert (M["runs"], M["steps"]) == (2, 71065)
    assert M["one_step_mismatches"] == M["open_loop_mismatches"] == []
    assert M["output_mismatches"] == []
    assert [b for b in rf.check(MODEL) if b.split()[1:2] == ["loader:"]] == []


def test_the_function_as_written_now_agrees_with_the_rtl(runs: list[dict[str, Any]]) -> None:
    got = rf.loader_compare(SPEC, runs)
    assert got["one_step_mismatches"] == got["open_loop_mismatches"] == []
    assert got["output_mismatches"] == [] and got["rules_fired"] == M["rules_fired"]


def test_each_bench_is_measured_on_its_own_then_joined() -> None:
    assert list(M["benches"]) == list(BENCHES)
    assert (M["benches"]["tb_gowin_loader"]["boundaries"],
            M["benches"]["tb_gowin_loader_nui"]["boundaries"]) == (5379, 65688)
    cov = M["coverage"]
    assert cov["union"] == cov["intersection"] == cov["tb_gowin_loader"]
    assert cov["tb_gowin_loader_nui"] == cov["union"] and len(cov["union"]) == 12
    assert M["not_covered"] == list(SPEC["not_covered"]) == ["count_empty"]


def test_the_owners_list_appears_in_the_rtls_own_order(runs: list[dict[str, Any]]) -> None:
    want = [("read", rf.RX_STATUS), ("read", rf.RX_DATA), ("write", rf.IMEM_ADDR),
            ("write", rf.IMEM_DATA), ("write", rf.TRAP_EPC), ("write", rf.TRAP_MODE),
            ("eret", None)]
    for run in runs:
        cut = rf.loader_boundaries(run["rows"])
        seen: list[tuple[str, Any]] = []
        for bound, segment in zip(cut["bounds"], cut["segments"], strict=False):
            if bound["at"].endswith("_status"):
                seen.append(("read", rf.RX_STATUS))
            elif bound["at"].endswith("_data"):
                seen.append(("read", rf.RX_DATA))
            seen += [(e[0], e[1] if len(e) > 1 else None) for e in segment
                     if e[0] in ("write", "eret")]
        firsts = sorted(want, key=seen.index)
        assert firsts == want, run["bench"]


def test_the_one_jmp_is_the_receive_loop_and_eret_the_only_handover() -> None:
    source = (ROOT / SPEC["rtl"]).read_text(encoding="utf-8")
    code = [ln.split(";")[0].split(":")[-1].split() for ln in source.splitlines()]
    assert [c for c in code if c[:1] == ["JMP"]] == [["JMP", "words"]]
    assert [c for c in code if c[:1] == ["ERET"]] == [["ERET"]]
    for name in BENCHES:
        b = M["benches"][name]
        assert b["entry_fetched_before_eret"] is False
        assert b["entry_fetched_cycles_after_eret"] == 1
        assert b["after_eret"] == {"epc": 64, "mode": 1}     # the trap unit's, observed


def test_what_each_bench_checks_is_what_the_function_predicts() -> None:
    lines = {b["bench"]: (ROOT / b["bench"]).read_text(encoding="utf-8").splitlines()
             for b in SPEC["benches"]}
    loader, nui = SPEC["benches"]
    for addr, word in loader["expects"]["imem"].items():
        assert M["benches"]["tb_gowin_loader"]["imem_written"][addr] == word
        assert any(f"imem[{addr}] == 32'h{word >> 16:04x}_{word & 0xFFFF:04x}" in ln
                   for ln in lines[loader["bench"]])

    def cited(b: dict[str, Any], text: str) -> bool:
        return any(text in lines[b["bench"]][n - 1] for n in b["expects_lines"])

    assert M["benches"]["tb_gowin_loader"]["waddr"] == 67
    assert cited(loader, "imem_waddr == 67") and cited(loader, "imem[64]")
    assert M["benches"]["tb_gowin_loader_nui"]["waddr"] == 112
    assert cited(nui, "imem_waddr == 64 + 48")
    assert M["bench_pass"]


def test_the_status_word_was_only_ever_zero_or_one(runs: list[dict[str, Any]]) -> None:
    """The limit named on count_ready and word_ready, measured."""
    values = {b["value"] for run in runs for b in rf.loader_boundaries(run["rows"])["bounds"]
              if b["at"].endswith("_status")}
    assert values == {0, 1}


def test_the_input_timing_is_measured() -> None:
    timing = M["input_timing"]
    assert timing["captured_new"] == timing["line_changes"] == 71063
    assert timing["captured_old"] == 0 and SPEC["input_timing"]["takes"] == "new"


# -- R3: each covered rule, broken, is red ---------------------------------------------------

Step = Callable[[dict[str, Any], Any, dict[str, int]],
                tuple[dict[str, Any], list[list[Any]], list[str]]]


def _bend(change: Callable[[dict[str, Any], dict[str, Any], list[list[Any]], list[str], Any],
                           None]) -> Step:
    def step(s: dict[str, Any], value: Any,
             p: dict[str, int]) -> tuple[dict[str, Any], list[list[Any]], list[str]]:
        n, events, fired = rf.loader_step(s, value, p)
        change(s, n, events, fired, value)
        return n, events, fired
    return step


def _lsb_first(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]], f: list[str],
               v: Any) -> None:
    if s["at"].endswith("_data"):
        n["R3"] = (v << 24 | s["R3"] >> 8) & rf.MASK32


def _spin_as_ready(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]], f: list[str],
                   v: Any) -> None:
    if s["at"].endswith("_status") and v == 0:
        n["at"] = s["at"].replace("_status", "_data")


def _pointer_stuck(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]], f: list[str],
                   v: Any) -> None:
    if "imem_data_advance" in f:
        n["waddr"] = s["waddr"]


def _no_trap_mode(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]], f: list[str],
                  v: Any) -> None:
    ev[:] = [e for e in ev if e[:2] != ["write", rf.TRAP_MODE]]


def _jump_into_program(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]],
                       f: list[str], v: Any) -> None:
    if "word_stored" in f:
        ev.append(["eret"])
        n["at"] = "done"


RED: dict[str, Step] = {
    "bytes assembled LSB first": _bend(_lsb_first),
    "a spin taken as a byte": _bend(_spin_as_ready),
    "a write pointer that does not advance": _bend(_pointer_stuck),
    "a handover without TRAP_MODE": _bend(_no_trap_mode),
    "a jump into the program after a word": _bend(_jump_into_program),
}


@pytest.mark.parametrize("name", RED)
def test_each_broken_covered_rule_is_red(name: str, runs: list[dict[str, Any]]) -> None:
    got = rf.loader_compare(SPEC, runs, step=RED[name])
    assert got["open_loop_mismatches"], name
    assert got["one_step_mismatches"] or got["output_mismatches"], name


# -- what "not covered" means: broken, the uncovered path stays unseen -----------------------


def _empty_skips_epc(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]], f: list[str],
                     v: Any) -> None:
    if "count_empty" in f:
        ev[:] = [e for e in ev if e[:2] != ["write", rf.TRAP_EPC]]


def _error_bits_spin(s: dict[str, Any], n: dict[str, Any], ev: list[list[Any]], f: list[str],
                     v: Any) -> None:
    if s["at"].endswith("_status") and v != 0 and not v & 1:
        n["at"] = s["at"]


@pytest.mark.parametrize("change", [_empty_skips_epc, _error_bits_spin])
def test_a_broken_path_the_benches_never_run_stays_unseen(
        change: Callable[..., None], runs: list[dict[str, Any]]) -> None:
    """Were one of these ever red, a bench would have begun to send N = 0 or
    a status with only its error bits set, and the spec would be stale."""
    got = rf.loader_compare(SPEC, runs, step=_bend(change))
    assert got["one_step_mismatches"] == got["open_loop_mismatches"] == []
    assert got["output_mismatches"] == []


# -- the spec cannot claim more than the benches show ------------------------------------------


def test_a_coverage_claim_the_spec_does_not_make_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "loader")["not_covered"].pop("count_empty")
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F4 loader") for b in rf.check(MODEL))


def test_an_expectation_a_bench_does_not_hold_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = rf.load()
    next(m for m in spec["modules"] if m["name"] == "loader")["benches"][1]["expects"][
        "waddr"] = 113
    monkeypatch.setattr(rf, "load", lambda: spec)
    assert any(b.startswith("F3 loader") for b in rf.check(MODEL))


def test_an_entry_fetched_before_eret_is_red() -> None:
    bent = json.loads(json.dumps(MODEL))
    next(m for m in bent["modules"] if m["name"] == "loader")["benches"]["tb_gowin_loader"][
        "entry_fetched_before_eret"] = True
    assert any(b.startswith("F3 loader") for b in rf.check(bent))


def test_the_rules_cite_lines_of_the_loader_and_of_the_mmio() -> None:
    source = (ROOT / SPEC["rtl"]).read_text(encoding="utf-8").splitlines()
    for r in SPEC["rules"]:
        text = (ROOT / r.get("file", SPEC["rtl"])).read_text(encoding="utf-8").splitlines()
        assert all(text[n - 1].strip() for n in r["lines"]), r["id"]
    assert re.search(r"JMP\s+words", source[67 - 1])
