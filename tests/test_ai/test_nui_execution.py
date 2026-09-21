"""Layer 3 held to the rule that nothing in it is predicted.

Every edge in the execution model came from a run. So the test that matters
is the one the owner named: rebuild the model from the repository and require
it to deny a false execution edge, a register that never moved, and a
memory-mapped register that was never touched. Each is injected here and
each must be caught by name.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui.execution_graph import (  # noqa: E402
    LOADER_SCENARIO,
    MODEL,
    PAGE,
    build,
    control_transfer,
    page,
    print_trace,
    verify,
)
from hijaiyyah.nui.execution_trace import (  # noqa: E402
    HARDWARE_GPRS,
    source_map,
    trace_program,
)
from hijaiyyah.nui.program_index import mmio_names, programs  # noqa: E402

FRESH = build()
COMMITTED = json.loads(MODEL.read_text())


@pytest.fixture
def model() -> dict:
    return copy.deepcopy(COMMITTED)


def test_the_committed_model_is_what_the_repository_produces() -> None:
    assert verify(COMMITTED, FRESH) == []


def test_a_stop_by_the_machine_is_a_fault_not_a_halt() -> None:
    """HALT_ERR stops the machine without a HALT. The run must say so, in the
    machine's own words -- not count a HALT that never ran, and not claim the
    program simply ran off its code."""
    from hijaiyyah.core.master_table import MASTER_TABLE
    from hijaiyyah.hisa.assembler import assemble
    from hijaiyyah.hisa.machine import HISAMachine
    from hijaiyyah.nui.execution_trace import run

    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble("        MOVI R1, 1\n        HALT_ERR\n        HALT\n"))
    trace = run(machine, {}, "<probe>")
    assert (trace.exit, trace.total_steps) == ("fault", 2)
    assert trace.exit_detail.startswith("HALT_ERR")


def test_a_step_that_executed_nothing_is_not_recorded_as_an_instruction() -> None:
    """The interpreter's periodic HCHECK runs before the fetch and, on
    corruption, halts without executing the word at pc. That step is the
    HCHECK, not an instruction: no EXECUTES edge, no executed line."""
    lines: list[str] = []
    trace = trace_program("rtl/programs/hfs_lifecycle.hasm", keep=0, sink=lines.append)
    assert trace.exit == "hcheck"
    last = [line for line in lines if line.startswith("STEP ")][-1]
    assert " HCHECK -> " in last, last
    assert trace.opcodes["HCHECK"] == 1


def test_the_page_is_drawn_from_the_model() -> None:
    """NUI/EXECUTION.md carries no sentence the model does not: it is
    page(model), byte for byte, or it is stale."""
    assert PAGE.read_text(encoding="utf-8") == page(COMMITTED)


def test_every_program_has_a_trace() -> None:
    assert set(programs().hasm) <= set(FRESH["programs"])
    assert LOADER_SCENARIO in FRESH["programs"]
    for name, summary in FRESH["programs"].items():
        assert summary["steps"] > 0, name
        assert summary["exit"] in ("halt", "fault", "hcheck", "end_of_code", "step_cap"), name
        assert re.fullmatch(r"[0-9a-f]{64}", summary["trace_sha256"]), name


def _printed(program: str, capsys: pytest.CaptureFixture[str]) -> list[str]:
    print_trace(program)
    return capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("program", [LOADER_SCENARIO, "rtl/programs/subroutine.hasm"])
def test_the_printed_trace_is_the_one_the_model_holds(
        program: str, capsys: pytest.CaptureFixture[str]) -> None:
    """ENTRY, then every STEP with its CHANGE lines or NO_CHANGE, then EXIT --
    and the text printed is the text the model's digest covers."""
    lines = _printed(program, capsys)
    assert lines[0].startswith("ENTRY pc=") and lines[-1].startswith("EXIT ")
    steps = [i for i, line in enumerate(lines) if line.startswith("STEP ")]
    assert len(steps) == FRESH["programs"][program]["steps"]
    for start, end in zip(steps, [*steps[1:], len(lines) - 1], strict=True):
        block = lines[start + 1:end]
        assert any(b == "  NO_CHANGE" or b.startswith("  CHANGE ") for b in block), lines[start]
        assert not ("  NO_CHANGE" in block and any(b.startswith("  CHANGE ") for b in block))
    digest = hashlib.sha256("".join(f"{line}\n" for line in lines).encode()).hexdigest()
    assert digest == COMMITTED["programs"][program]["trace_sha256"]


def test_the_loader_trace_walks_the_owners_seven_steps_in_order(
        capsys: pytest.CaptureFixture[str]) -> None:
    """The sequence the owner wrote as the example of a trace, found in the
    loader's own run, in that order -- not written, observed."""
    lines = _printed(LOADER_SCENARIO, capsys)
    wanted = ["  read mmio RX_STATUS@", "  read mmio RX_DATA@", "  write mmio IMEM_ADDR@",
              "  write mmio IMEM_DATA@", "  write mmio TRAP_EPC@", "  write mmio TRAP_MODE@",
              " ERET -> pc=0x040"]
    at = [next(i for i, line in enumerate(lines) if w in line) for w in wanted]
    assert at == sorted(at), dict(zip(wanted, at, strict=True))


def test_the_state_model_records_before_and_after(capsys: pytest.CaptureFixture[str]) -> None:
    """Registers, data memory, and the machine state a memory-mapped write
    lands in -- each as before -> after -- and NO_CHANGE where nothing moved."""
    loader = _printed(LOADER_SCENARIO, capsys)
    assert "  CHANGE state trap_epc 0 -> 64" in loader
    assert "  CHANGE code[0x040] absent -> 0x04100007" in loader
    assert "  CHANGE R1 1 -> 7" in loader
    assert "  NO_CHANGE" in loader
    sub = _printed("rtl/programs/subroutine.hasm", capsys)
    assert "  CHANGE mem 0x100 0 -> 21" in sub
    assert "  CHANGE state len(return_stack) 0 -> 1" in sub


def test_every_call_lands_on_a_label_the_assembler_bound() -> None:
    """A CALL's target is a function node: the label the assembler's first
    pass bound to that address, not a bare number."""
    calls = [e for e in FRESH["edges"] if e["kind"] == "CALLS"]
    assert calls
    assert all(str(e["target"]).startswith("label:") for e in calls), [
        e for e in calls if not str(e["target"]).startswith("label:")]


def test_how_the_loader_hands_over_control_read_from_the_model() -> None:
    """The owner's required question, answered without reading the code."""
    rows = control_transfer(FRESH, LOADER_SCENARIO)
    kinds = [(r["kind"], str(r["target"]).split("@")[0]) for r in rows]
    assert kinds[-3:] == [("WRITES", "mmio:TRAP_EPC"), ("WRITES", "mmio:TRAP_MODE"),
                          ("RESUMES", "pc:0x040")]
    assert rows[-1]["where"] == "rtl/programs/loader.hasm:74"


def test_reads_and_observes_are_told_apart_by_measurement() -> None:
    """RX_DATA pops a byte, RX_STATUS does not. Classified by whether the
    queue shrank during the read, not by the register's name."""
    loader = {(e["kind"], e["target"]) for e in FRESH["edges"]
              if e["source"] == LOADER_SCENARIO}
    assert ("READS", "mmio:RX_DATA@0xff0") in loader
    assert ("OBSERVES", "mmio:RX_STATUS@0xff1") in loader
    assert ("READS", "mmio:RX_STATUS@0xff1") not in loader


def test_every_trap_has_a_source_and_a_destination() -> None:
    """Destination 0 is a real destination: no handler was installed, and the
    trap lands on the program's own first word. It is listed as such rather
    than treated as a missing answer."""
    traps = [t for s in FRESH["programs"].values() for t in s["traps"]]
    assert traps, "no trap was taken anywhere"
    for trap in traps:
        assert isinstance(trap["epc"], int) and isinstance(trap["vector"], int), trap
    unset = FRESH["unknown"]["trap_to_an_uninstalled_vector"]
    assert unset == [f"rtl/tb/{name}: cause [5]" for name in
                     ("hfs_persist_probe.hasm", "hfs_syscall_probe.hasm",
                      "prog_load_probe.hasm")]


def test_every_memory_mapped_edge_names_a_real_register() -> None:
    names = mmio_names()
    for edge in FRESH["edges"]:
        if str(edge["target"]).startswith("mmio:"):
            name, address = str(edge["target"])[5:].split("@")
            assert names.get(int(address, 16)) == name, edge


def test_no_program_touches_a_register_the_hardware_does_not_have() -> None:
    """The interpreter holds 18 general registers; the RTL has 16 (e239964).
    A program writing R16 or R17 would pass here and diverge on the board."""
    for name, summary in FRESH["programs"].items():
        assert all(r < HARDWARE_GPRS for r in summary["gprs_modified"]), name


def test_the_source_map_agrees_with_the_assembler_for_every_program() -> None:
    for path in programs().hasm:
        assert source_map(path)       # refuses outright if the counts disagree


def test_the_recorder_changes_nothing_about_the_run() -> None:
    """The instrumented machine must behave exactly as an uninstrumented one:
    same output, same step count, same final registers."""
    from hijaiyyah.core.master_table import MASTER_TABLE
    from hijaiyyah.hisa.assembler import assemble
    from hijaiyyah.hisa.machine import HISAMachine

    for path in ("rtl/programs/test_guard.hasm", "rtl/programs/trap_resume.hasm",
                 "rtl/programs/letters.hasm"):
        source = ROOT / path
        plain = HISAMachine(MASTER_TABLE)
        plain.load_program(assemble(source.read_text(), base_dir=source.parent))
        steps = 0
        while plain.step() is not None and steps < 20_000:
            steps += 1
        traced = trace_program(path, keep=0)
        assert traced.total_steps == steps, path
        assert traced.printed == list(plain.output), path


def test_the_unknown_inventory_is_there_and_says_what_it_cannot_show() -> None:
    unknown = FRESH["unknown"]
    for key in ("branch_seen_one_way", "did_not_halt_within_budget",
                "ran_off_its_code", "stopped_by_interpreter_hcheck",
                "sd_card_absent_in_interpreter", "timer_counts_instructions",
                "registers_the_hardware_lacks", "trap_to_an_uninstalled_vector",
                "state_the_machine_never_declared", "scope"):
        assert key in unknown, key
    assert unknown["registers_the_hardware_lacks"] == []
    assert any("hfs_lifecycle" in u for u in unknown["stopped_by_interpreter_hcheck"])


def test_no_run_sets_state_the_machine_never_declared() -> None:
    """How layer 3's first run caught HC-04/HC-05 not stopping the machine:
    the fault paths set `halted`, an attribute nothing reads, beside the
    `_halted` everything does. It showed as an integer that appeared on the
    machine mid-run. Fixed; this holds the category empty, so the next
    misspelled attribute is named the day it is written."""
    assert FRESH["unknown"]["state_the_machine_never_declared"] == []


def test_the_library_programs_stop_at_their_first_return() -> None:
    """Run alone, each of these reaches a RET with nothing to return to. The
    spec (0x2F) and the RTL halt there as HC-05; so does the interpreter now,
    instead of running on through every function after it."""
    faults = {name: s["exit_detail"] for name, s in FRESH["programs"].items()
              if s["exit"] == "fault"}
    assert faults == {f"rtl/programs/{p}.hasm": "RET → HC-05 return stack underflow"
                      for p in ("hal", "hal_sd", "hos", "hos_hctx",
                                "hos_hfs_disk", "hos_prog_load")}


# -- the three sabotages the owner requires to be red -----------------------


def test_a_false_execution_edge_is_denied(model: dict) -> None:
    model["edges"].append({"source": "rtl/programs/letters.hasm", "kind": "EXECUTES",
                           "target": "opcode:ERET", "step": 0, "pc": 0,
                           "where": "rtl/programs/letters.hasm:1", "times": 1})
    problems = verify(model, FRESH)
    assert any("letters.hasm EXECUTES opcode:ERET" in p for p in problems), problems


def test_a_false_register_is_denied(model: dict) -> None:
    model["edges"].append({"source": LOADER_SCENARIO, "kind": "MODIFIES",
                           "target": "reg:R13", "step": 5, "pc": 4,
                           "where": "rtl/programs/loader.hasm:38", "times": 1})
    problems = verify(model, FRESH)
    assert any("MODIFIES reg:R13" in p for p in problems), problems


def test_a_false_memory_mapped_access_is_denied(model: dict) -> None:
    model["edges"].append({"source": LOADER_SCENARIO, "kind": "READS",
                           "target": "mmio:SD_DATA@0xfe3", "step": 9, "pc": 8,
                           "where": "rtl/programs/loader.hasm:40", "times": 1})
    problems = verify(model, FRESH)
    assert any("READS mmio:SD_DATA@0xfe3" in p for p in problems), problems


def test_a_false_trace_is_denied(model: dict) -> None:
    """The full trace is held by its digest; a trace that did not run is
    caught the same way an edge that did not run is."""
    model["programs"][LOADER_SCENARIO]["trace_sha256"] = "0" * 64
    problems = verify(model, FRESH)
    assert any(f"summary differs: {LOADER_SCENARIO} trace_sha256" in p
               for p in problems), problems


def test_a_false_count_is_denied(model: dict) -> None:
    """An edge that is real, at the right step, but claims the wrong number
    of times -- the one mismatch the first verifier let through."""
    edge = next(e for e in model["edges"]
                if e["source"] == LOADER_SCENARIO and e["kind"] == "READS")
    edge["times"] += 1
    problems = verify(model, FRESH)
    assert any(p.startswith("count differs") and "READS" in p for p in problems), problems


def test_moved_evidence_is_denied_too(model: dict) -> None:
    """An edge that is real but claims the wrong step is still a false claim."""
    edge = next(e for e in model["edges"]
                if e["source"] == LOADER_SCENARIO and e["kind"] == "RESUMES")
    edge["step"] = 1
    problems = verify(model, FRESH)
    assert any("evidence moved" in p and "RESUMES" in p for p in problems), problems
