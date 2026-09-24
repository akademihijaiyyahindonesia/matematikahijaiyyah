"""Layer 4 held to the rule that a parity claim is a comparison that ran.

The model is rebuilt from the repository and the committed one must match it.
Then each claim it can make is broken on purpose and must be denied by name:
a PARITY that is not one, a register value that did not happen, a board
record the record does not hold. And the comparator itself is broken from
the engine side -- an interpreter that adds one to every ADD -- to prove it
names the step, the register and the opcode rather than only saying "differs".
"""
from __future__ import annotations

import copy
import functools
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

pytestmark = pytest.mark.skipif(
    shutil.which("iverilog") is None and os.environ.get("HOM_REQUIRE_IVERILOG") != "1",
    reason="Icarus Verilog is required to execute the RTL",
)

from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402
from hijaiyyah.hisa.opcodes import OpCode  # noqa: E402
from hijaiyyah.nui import parity_model as pm  # noqa: E402


@functools.cache
def _fresh() -> dict:
    """Built on first use, not at import -- see test_nui_execution.py."""
    return json.loads(json.dumps(pm.build()))
COMMITTED = json.loads(pm.MODEL.read_text(encoding="utf-8"))
STOPPED = [f"rtl/programs/{p}.hasm" for p in (
    "bench/e6_record_triage", "hal_sd", "hos_hctx", "hos_prog_load", "mem_protect",
    "subroutine", "syscall", "test_hfs", "trap_epc", "user_mode")]
#: One word behind a stop, per kind: what the RTL then does, as (stream, value).
PROBES = {"stop-probe:halt-then-print": ("TX", ord("5")),
          "stop-probe:halt-then-store": ("RAM", 5),
          "stop-probe:ret-then-print": ("TX", ord("5"))}


@pytest.fixture
def model() -> dict:
    return copy.deepcopy(COMMITTED)


@pytest.fixture(scope="module")
def sim(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return pm.compile_rtl(tmp_path_factory.mktemp("rtl"))


def test_the_committed_model_is_what_the_repository_produces() -> None:
    assert pm.verify(COMMITTED, _fresh()) == []


def test_the_page_is_drawn_from_the_model() -> None:
    assert pm.PAGE.read_text(encoding="utf-8") == pm.page(COMMITTED)


def test_every_program_is_compared_and_every_opcode_has_a_row() -> None:
    names = {p.name for p in pm.corpus()}
    assert set(_fresh()["programs"]) == names
    assert set(_fresh()["opcodes"]) == {op.name for op in OpCode} | {"TRAP"}
    for name, result in _fresh()["programs"].items():
        assert result["status"] in ("PARITY", "MISMATCH", "UNKNOWN"), name
        if result["status"] == "MISMATCH":
            assert result["first_divergence"], name
        if result["status"] == "UNKNOWN":
            assert result["reason"], name


# -- the owner's targets --------------------------------------------------------


# -- P3: the hardware column, from the board corpus ---------------------------------

#: The owner's five, 24 September 2026: these run in programs that agreed and
#: in programs that did not, so the wire cannot say which instruction differed.
#: They stay UNKNOWN while the evidence is mixed, and are never moved to
#: PARITY to complete a table.
MIXED = ("HALT", "HCRC", "HLOAD", "HPACK", "PRINT")
#: The four that read the free-running counter. UNKNOWN for counter semantics:
#: the interpreter counts instructions and silicon counts clocks. Not a
#: hardware defect, and not written down as one.
COUNTER = [f"rtl/programs/{n}.hasm" for n in
           ("timer_poll", "trap_resume", "trap_shadow", "trap_timer")]


def test_the_hardware_column_is_recomputed_from_the_record_not_written_down() -> None:
    """Every cell of the matrix is what board_parity makes of the committed
    record's own bytes. A page that could be edited by hand would be a claim,
    not a measurement."""
    from hijaiyyah.nui import board_parity as bp

    corpus = COMMITTED["board_corpus"]
    record = bp.latest_record("parity")
    assert record is not None and record["date"] == corpus["record"]
    section = bp.load_expected()["parity"]
    again = bp.opcode_column(bp.classify(bp.reparsed(record), section), section)
    assert {n: c["board"] for n, c in again.items()} == {
        n: c["board"] for n, c in corpus["opcodes"].items()}
    assert corpus["expected_sha256"] == record["expected_sha256"]
    assert corpus["counts"] == {"PARITY": 74, "MISMATCH": 0, "UNKNOWN": 29}


def test_no_opcode_is_called_parity_without_agreeing_evidence() -> None:
    """The owner's rule, held cell by cell: PARITY only where hardware
    evidence bears on it and agrees; MISMATCH only where valid board evidence
    differs; UNKNOWN otherwise."""
    for name, cell in COMMITTED["board_corpus"]["opcodes"].items():
        if cell["board"] == "PARITY":
            assert cell["parity"] > 0 and cell["mismatch"] == 0, (name, cell)
        elif cell["board"] == "MISMATCH":
            assert cell["mismatch"] > 0 and cell["parity"] == 0, (name, cell)
        else:
            assert cell["parity"] == 0 or cell["mismatch"] > 0, (name, cell)
            assert cell["reason"], name


def test_the_five_with_mixed_evidence_stay_unknown() -> None:
    cells = COMMITTED["board_corpus"]["opcodes"]
    for name in MIXED:
        assert cells[name]["board"] == "UNKNOWN", (name, cells[name])
        assert cells[name]["parity"] and cells[name]["mismatch"], name
    mixed = {n for n, c in cells.items()
             if c["parity"] and c["mismatch"]}
    assert mixed == set(MIXED), mixed


def test_print_is_unknown_in_the_column_and_a_discrepancy_beside_it() -> None:
    """Status and discrepancy are two different things -- the owner, 24
    September 2026. The corpus cannot decide PRINT, and the two programs that
    differ are real silicon evidence all the same; both are written down."""
    cell = COMMITTED["board_corpus"]["opcodes"]["PRINT"]
    assert cell["board"] == "UNKNOWN"
    assert cell["differing_programs"] == ["rtl/programs/bench/e4_frame.hasm",
                                          "rtl/programs/test_hisab.hasm"]
    assert COMMITTED["opcodes"]["PRINT"]["board"] == "MISMATCH", (
        "the recorded ladder is the discrepancy, and it is not erased by the column")


def test_the_counter_programs_are_unknown_for_their_semantics_not_for_a_defect() -> None:
    from hijaiyyah.nui import board_parity as bp

    record = bp.latest_record("parity")
    assert record is not None
    classified = bp.classify(bp.reparsed(record), bp.load_expected()["parity"])
    for name in COUNTER:
        row = classified[name]
        assert row["status"] == "UNKNOWN", (name, row)
        assert "counter" in row["reason"], row
        assert "defect" not in row["reason"] and "bug" not in row["reason"]


def test_every_program_a_cell_names_is_in_the_record() -> None:
    """Source trace: no cell may rest on a program the record does not hold."""
    from hijaiyyah.nui import board_parity as bp

    record = bp.latest_record("parity")
    assert record is not None
    held = set(record["programs"])
    for name, cell in COMMITTED["board_corpus"]["opcodes"].items():
        for key in ("agreeing_programs", "differing_programs", "undecided_programs"):
            assert set(cell[key]) <= held, (name, key, set(cell[key]) - held)
        assert cell["evidence"] == cell["parity"] + cell["mismatch"] + cell["unknown_sent"]


def test_print_is_a_board_mismatch_and_only_the_board() -> None:
    """The first of the two RTL defects the owner named as a layer-4 target.
    The RTL as simulated prints all thirty-two ladder values exactly as the
    interpreter does; the board, built from the same RTL, printed three of
    the recorded ones wrong."""
    ladder = [r for r in _fresh()["board"] if r["program"] == pm.LADDER]
    assert all(r["interpreter"] == r["rtl"] == str(r["value"]) for r in ladder)
    wrong = {r["value"]: r["board"] for r in ladder if r["status"] == "MISMATCH"}
    assert wrong == {1 << 23: "8388600", 1 << 25: "335544;<", 1 << 31: "2147481?::"}
    entry = _fresh()["opcodes"]["PRINT"]
    assert (entry["rtl"], entry["board"], entry["status"]) == ("PARITY", "MISMATCH",
                                                               "MISMATCH")
    assert "print_val % 10" in _line(entry["source"])


def test_the_sd_init_defect_is_named_board_only() -> None:
    """The second target cannot be a parity row: no other engine here has a
    card or a reconfiguration. It is said so, not left out."""
    assert any("SD init" in s and "board-only" in s for s in _fresh()["unknown"]["scope"])


def test_the_word_after_a_stop_commits_on_the_rtl() -> None:
    """Found by this layer: the instruction behind HALT -- or behind a RET that
    stops the machine as HC-05 -- commits on the RTL, once, after the
    interpreter has stopped. Ten programs show it as a register write, and
    nowhere before the stop do the two disagree. The three probes ask the
    kinds the ten did not: a store reaches RAM, and a print reaches the wire
    -- which is what makes it visible on the board."""
    after = sorted(n for n, r in _fresh()["programs"].items()
                   if r["first_divergence"] and r["first_divergence"]["rtl"].get("after_stop"))
    assert after == sorted(STOPPED + list(PROBES))
    for name in STOPPED:
        d = _fresh()["programs"][name]["first_divergence"]
        assert d["kind"] == "GPR" and d["interpreter"]["opcode"] in ("HALT", "RET"), name
    for name, (kind, value) in PROBES.items():
        d = _fresh()["programs"][name]["first_divergence"]
        assert (d["kind"], d["rtl"]["value"]) == (kind, value), name
    sub = _fresh()["programs"]["rtl/programs/subroutine.hasm"]["first_divergence"]
    assert (sub["rtl"]["key"], sub["rtl"]["value"]) == (1, 10)     # 3 + the ADDI's 7
    for op in ("HALT", "RET"):
        entry = _fresh()["opcodes"][op]
        assert entry["rtl"] == "MISMATCH", op
        lines = [_line(s) for s in entry["source"].split(", ")]
        assert "else if (wb_halt)" in lines[0] and "assign wb_gpr_we" in lines[1]


def test_peripheral_differences_are_charged_to_the_register_not_the_load() -> None:
    """A LOAD of COUNTER that differs is the timer differing: the interpreter
    counts instructions, the RTL clocks. So LOAD stays PARITY."""
    assert sorted(_fresh()["mmio"]) == ["COUNTER", "SD_STATUS"]
    assert len(_fresh()["mmio"]["COUNTER"]) == 8 and len(_fresh()["mmio"]["SD_STATUS"]) == 7
    assert _fresh()["opcodes"]["LOAD"]["rtl"] == "PARITY"


def test_the_python_references_agree_and_a_trap_is_not_an_execution() -> None:
    """The four book functions agree with the interpreter on every execution.
    trap_hreg takes a trap on an HLOAD's word; the first version counted that
    as an HLOAD that loaded nothing, and reported a mismatch that never ran."""
    for name, row in _fresh()["python"].items():
        assert row["status"] == "PARITY" and row["checked"] > 0, name
    prog = next(p for p in pm.corpus() if p.name == "rtl/programs/trap_hreg.hasm")
    run = pm.run_interpreter(prog)
    assert all(r["agrees"] is not False for r in run.python)


# -- claims broken on purpose ---------------------------------------------------


def test_a_false_parity_is_denied(model: dict) -> None:
    model["programs"]["rtl/programs/subroutine.hasm"]["status"] = "PARITY"
    problems = pm.verify(model, _fresh())
    assert any("programs rtl/programs/subroutine.hasm status" in p for p in problems), problems


def test_a_false_register_value_is_denied(model: dict) -> None:
    model["programs"]["rtl/programs/subroutine.hasm"]["first_divergence"]["rtl"]["value"] = 11
    problems = pm.verify(model, _fresh())
    assert any("subroutine.hasm first_divergence" in p for p in problems), problems


def test_a_false_board_record_is_denied(model: dict) -> None:
    row = next(r for r in model["board"] if r.get("value") == 1 << 23)
    row["board"] = "8388608"
    row["status"] = "PARITY"
    problems = pm.verify(model, _fresh())
    assert any(p.startswith("differs: board row") for p in problems), problems


def test_a_false_opcode_status_is_denied(model: dict) -> None:
    model["opcodes"]["HALT"]["rtl"] = "PARITY"
    problems = pm.verify(model, _fresh())
    assert any("opcodes HALT rtl" in p for p in problems), problems


# -- the comparator broken from the engine side --------------------------------


def test_an_interpreter_that_adds_wrong_is_named_at_its_step(
        sim: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prog = next(p for p in pm.corpus() if p.name == "parity:integer_arithmetic")
    real = HISAMachine._execute

    def off_by_one(self, iw):  # type: ignore[no-untyped-def]
        out = real(self, iw)
        if iw.opcode == OpCode.ADD:
            self.regs.gpr[iw.dst] += 1
        return out

    monkeypatch.setattr(HISAMachine, "_execute", off_by_one)
    interp = pm.run_interpreter(prog)
    rtl = pm.run_rtl(sim, prog.words, pm.cycle_budget(interp), tmp_path)
    result = pm.compare(prog, interp, rtl)
    d = result["first_divergence"]
    assert result["status"] == "MISMATCH"
    assert (d["kind"], d["interpreter"]["opcode"], d["interpreter"]["key"]) == ("GPR", "ADD", 3)
    assert (d["interpreter"]["value"], d["rtl"]["value"]) == (308, 307)
    assert d["interpreter"]["step"] == 2


def test_an_rtl_value_that_differs_is_named(sim: Path, tmp_path: Path) -> None:
    prog = next(p for p in pm.corpus() if p.name == "parity:store_then_load")
    interp = pm.run_interpreter(prog)
    rtl = pm.run_rtl(sim, prog.words, pm.cycle_budget(interp), tmp_path)
    assert pm.compare(prog, interp, rtl)["status"] == "PARITY"
    rtl.events["RAM"][0].value += 1
    d = pm.compare(prog, interp, rtl)["first_divergence"]
    assert (d["kind"], d["interpreter"]["opcode"]) == ("RAM", "STORE")
    assert d["interpreter"]["key"] == 67 and d["rtl"]["value"] == 1235


# -- what the model rests on ----------------------------------------------------


def test_board_records_postdate_the_last_change_to_the_cpu_rtl() -> None:
    """A record older than the design it describes is about a design that is
    gone (R4). If the CPU's RTL changes, this fails until the board is rerun."""
    last = subprocess.run(
        ["git", "log", "-1", "--format=%h %cs", "--", ":(glob)rtl/*.v", ":(glob)rtl/*.vh",
         ":(glob)rtl/fpga/gowin/hcpu_gowin_*.v"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert tuple(last) == pm.LAST_CPU_RTL_CHANGE
    assert all(r["date"] > pm.LAST_CPU_RTL_CHANGE[1] for r in _fresh()["board"])


def test_every_halted_run_had_room_in_its_cycle_budget() -> None:
    for name, r in _fresh()["programs"].items():
        if r["rtl"]["halted"]:
            assert r["rtl"]["cycles"] < 0.9 * r["rtl"]["budget"], name
        elif r["interpreter"]["exit"] in pm.HALTED:
            # stopped short by a peripheral, not by the budget
            assert r["first_divergence"]["interpreter"].get("reads_mmio"), name


def test_the_harness_prints_no_trace_unless_asked(sim: Path, tmp_path: Path) -> None:
    """tests/test_hisa/test_execution_parity.py reads tb_parity.v's default
    output; +TRACE must add lines only when it is given."""
    hexfile = tmp_path / "p.hex"
    hexfile.write_text("".join(f"{w:08X}\n" for w in pm.PROGRAMS["integer_arithmetic"]))
    out = subprocess.run(["vvp", "-n", str(sim), f"+PROGRAM={hexfile}", "+CYCLES=400"],
                         capture_output=True, text=True, check=True).stdout
    assert not any(line.startswith("T ") for line in out.splitlines())
    assert "HALTED=1" in out


def test_the_owner_questions_are_answered_in_his_format() -> None:
    for name in ("ADD", "SUB", "LOAD", "STORE", "CALL", "RET", "TRAP", "PRINT"):
        block = pm.opcode_block(_fresh(), name)
        assert block.startswith(f"OPCODE: {name}") and "STATUS:" in block, name
        for engine in ("Python:", "Interpreter:", "RTL:", "Board:"):
            assert engine in block, (name, engine)
        if _fresh()["opcodes"][name]["status"] == "MISMATCH":
            assert "SOURCE:" in block, name


def _line(ref: str) -> str:
    path, number = ref.rsplit(":", 1)
    return (ROOT / path).read_text(encoding="utf-8").splitlines()[int(number) - 1]


def test_sources_point_at_real_lines() -> None:
    for name, entry in _fresh()["opcodes"].items():
        for ref in filter(None, entry.get("source", "").split(", ")):
            assert re.fullmatch(r"rtl/[\w/.]+:\d+", ref) and _line(ref).strip(), (name, ref)
