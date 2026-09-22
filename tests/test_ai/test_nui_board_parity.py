"""The board runs, held before they happen.

The board carries the 72-hour burn-in, so nothing here touches it. What can
be held now is everything the three experiments rest on: which programs go
and why the rest do not, that no program sent can reach the card, that every
observation epilogue prints the state it replaced, that the expected answers
frozen in NUI/board_expected.json are what the engines give today, that the
RTL and the interpreter agree wherever the timer is not read, that a capture
is parsed without losing a byte quietly, that a record is classified and
rolled up per opcode by stated rules -- and that the runner refuses to start
while a burn-in is alive, without an experiment named, or with a payload the
expectation did not freeze.
"""
from __future__ import annotations

import functools
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import board_parity as bp  # noqa: E402
from hijaiyyah.nui import board_probes  # noqa: E402


@functools.cache
def _corpus() -> list[bp.BoardProgram]:
    """Built on first use, not at import -- see test_nui_execution.py."""
    return bp.corpus()


def _sent() -> list[bp.BoardProgram]:
    return [b for b in _corpus() if not b.excluded]


def _by_name() -> dict[str, bp.BoardProgram]:
    return {b.name: b for b in _corpus()}


#: The four that read the free-running counter: clocks on the RTL,
#: instructions in the interpreter (layer 4).
TIMED = {"rtl/programs/timer_poll.hasm", "rtl/programs/trap_resume.hasm",
         "rtl/programs/trap_shadow.hasm", "rtl/programs/trap_timer.hasm"}


def test_the_plan_sends_what_it_can_and_names_why_not() -> None:
    assert (len(_sent()), len(_corpus())) == (79, 103)
    reasons = [b.excluded.split(":")[0].split(" (")[0] for b in _corpus() if b.excluded]
    assert reasons.count("touches the SD window") == 9
    assert reasons.count("does not halt under the loader") == 15
    assert not [b.name for b in _corpus() if "epilogue" in b.excluded], "an epilogue failed"


def test_print_and_the_stop_probes_are_experiments_of_their_own() -> None:
    """The owner, 22 September 2026: neither rides in the parity corpus."""
    names = {b.name for b in _corpus()}
    assert board_probes.PRINT_NAME not in names
    assert not {n for n in names if n.startswith("stop-probe")}
    assert [b.name for b in bp.programs_for("print")] == ["print-silicon"]
    assert [b.name for b in bp.programs_for("stop")] == list(board_probes.STOP_QUESTIONS)
    assert board_probes.PRINT_VALUES == [1 << k for k in (22, 23, 24, 25, 26, 27, 31)]


def test_nothing_sent_reaches_the_card() -> None:
    """The card is the burn-in's: sector 1 is read every cycle."""
    for b in _sent():
        run = b.run or bp.run_under_loader(b.name, b.payload)
        touched = [a.address for s in run.steps for a in s.accesses
                   if a.address in bp.SD_WINDOW]
        assert not touched, b.name


def test_an_epilogue_prints_the_state_it_replaced() -> None:
    """integer_arithmetic ends with R1=300, R2=7, R3=307, R4=293, R5=2100.
    Its epilogue prints FLAGS, then each of the five a byte at a time."""
    b = _by_name()["parity:integer_arithmetic"]
    assert b.epilogue
    got = bp._dump(b.expected, [1, 2, 3, 4, 5], [])
    assert got is not None
    assert got["gpr"] == {1: 300, 2: 7, 3: 307, 4: 293, 5: 2100}


def test_an_epilogue_that_prints_wrong_is_not_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    """R3: break the epilogue -- mask every byte to seven bits -- and the
    program it instruments must be excluded, not sent. The program is one
    whose state has a byte above 127 (1 - 5 wraps to 0xFFFFFFFC), or the
    sabotage could not bite."""
    real = bp.epilogue
    monkeypatch.setattr(bp, "epilogue",
                        lambda g, h, s: real(g, h, s).replace(", 255", ", 127"))
    from hijaiyyah.hisa.parity_programs import PROGRAMS
    name = "subtraction_wraps_at_32_bits"
    broken = bp._instrument(f"parity:{name}", list(PROGRAMS[name]))
    assert "not trusted" in broken.excluded


def test_the_board_reference_runs_without_the_interpreters_own_hcheck() -> None:
    """Under the loader the periodic HCHECK's clock is shifted, and it stopped
    these two where the board never stops. They are sent."""
    for name in ("parity:codex_negative_residue", "parity:cset_twice_into_the_same_register"):
        assert not _by_name()[name].excluded, name


@pytest.mark.skipif(shutil.which("iverilog") is None
                    and os.environ.get("HOM_REQUIRE_IVERILOG") != "1",
                    reason="Icarus Verilog is required to execute the RTL")
def test_the_frozen_expectations_are_what_the_engines_give_today() -> None:
    """NUI/board_expected.json is recomputed -- interpreter under the loader,
    both engines at 64 behind NOPs -- and must be what was frozen, or the
    board would be read against a stale expectation."""
    frozen = bp.load_expected()
    for experiment in bp.EXPERIMENTS:
        assert bp.expectations(experiment) == frozen[experiment], experiment


def _frozen() -> dict:  # type: ignore[type-arg]
    return bp.load_expected()


def test_the_engines_agree_at_64_except_where_the_timer_is_read() -> None:
    """Every payload, epilogue included, at address 64 behind NOPs on both
    engines: the wire agrees everywhere except the four that read the timer."""
    programs = _frozen()["parity"]["programs"]
    differ = {n for n, e in programs.items()
              if e["sent"] and e["rtl_at_64"] != e["interpreter_at_64"]}
    assert differ == TIMED
    assert all("COUNTER" in programs[n]["reads"] for n in TIMED)


def test_the_rtl_answers_yes_to_all_four_stop_questions() -> None:
    """Measured on the simulated RTL, 22 September 2026: the word behind the
    stop commits in every case the owner asked about. The interpreter stops."""
    rows = {r["probe"]: r for r in board_probes.stop_table(_frozen()["stop"])}
    for probe in ("stop-probe:halt-then-register", "stop-probe:ret-then-register"):
        assert (rows[probe]["interpreter"], rows[probe]["rtl"]) == (5, 7), probe
    store = rows["stop-probe:halt-then-store"]
    assert (store["interpreter"], store["rtl"]) == (0, 5)
    for probe in ("stop-probe:ret-then-print", "stop-probe:halt-then-print"):
        assert (rows[probe]["interpreter_wire"], rows[probe]["rtl_wire"]) == ("", "5"), probe


def test_print_in_silicon_is_expected_right_by_both_engines() -> None:
    entry = _frozen()["print"]["programs"]["print-silicon"]
    want = "".join(f"{v}\n" for v in board_probes.PRINT_VALUES)
    assert entry["interpreter"] == entry["rtl_at_64"] == want


def _record(experiment: str, texts: dict[str, str] | None = None,
            halted: bool = True) -> dict:  # type: ignore[type-arg]
    """A record shaped as the runner writes one, built from the frozen
    expectation -- test data for the reader, never a board result."""
    section = _frozen()[experiment]["programs"]
    programs = {}
    for name, e in section.items():
        if not e["sent"]:
            programs[name] = {"excluded": e["excluded"]}
            continue
        text = (texts or {}).get(name, e["interpreter"])
        programs[name] = {"payload_sha256": e["payload_sha256"], "text": text,
                          "halted": halted, "dropped": 0, "timed_out": not halted}
    return {"experiment": experiment, "date": "test", "commit": "test", "programs": programs}


def test_a_record_is_classified_against_the_frozen_expectation() -> None:
    section = _frozen()["parity"]
    record = _record("parity", {"parity:integer_arithmetic": "0\n9\n"})
    got = bp.classify(record, section)
    assert got["parity:integer_arithmetic"]["status"] == "MISMATCH"
    assert got["parity:integer_arithmetic"]["line"] == 0
    assert got["rtl/programs/letters.hasm"]["status"] == "PARITY"
    for name in TIMED:
        assert got[name]["status"] == "UNKNOWN" and "counter" in got[name]["reason"], name
    sd = next(n for n, e in section["programs"].items() if "SD window" in e.get("excluded", ""))
    assert got[sd]["status"] == "UNKNOWN" and got[sd]["reason"].startswith("not sent")
    record["programs"]["rtl/programs/letters.hasm"]["payload_sha256"] = "0" * 64
    assert "froze" in bp.classify(record, section)["rtl/programs/letters.hasm"]["reason"]
    silent = bp.classify(_record("parity", halted=False), section)
    assert silent["rtl/programs/letters.hasm"]["kind"] == "no halt report"


def test_the_opcode_column_attributes_only_what_the_wire_can_say() -> None:
    """An opcode seen only in agreeing runs is PARITY; seen in both, UNKNOWN;
    run by no program sent, UNKNOWN with that reason."""
    section = _frozen()["parity"]
    clean = bp.opcode_column(bp.classify(_record("parity"), section), section)
    assert clean["MOVI"]["board"] == "PARITY"
    assert clean["CDOT"]["board"] == "UNKNOWN"
    assert clean["CDOT"]["reason"] == "no program sent executes it"
    one_off = bp.classify(_record("parity", {"parity:integer_arithmetic": "x"}), section)
    column = bp.opcode_column(one_off, section)
    assert column["MOVI"]["board"] == "UNKNOWN"
    assert "parity:integer_arithmetic" in column["MOVI"]["differing"]


def test_print_reports_the_first_value_silicon_departs_on() -> None:
    """Fed the values OFF-PRINT-SILICON recorded -- 2^23 came back 8388600 --
    the table names 2^23 as the first divergence and nothing before it."""
    board = "4194304\n8388600\n16777216\n335544;<\n"
    rows = board_probes.print_table(_frozen()["print"], board)
    first = [r["value"] for r in rows if r["first_divergence"]]
    assert first == [1 << 23]
    assert rows[0]["board"] == rows[0]["python"] == "4194304"
    assert rows[4]["board"] is None


def test_a_report_rolls_each_experiment_up() -> None:
    expected = _frozen()
    parity = bp.report(_record("parity"), expected)
    assert parity["counts"] == {"PARITY": 75, "MISMATCH": 0, "UNKNOWN": 28}
    assert "opcodes" in parity
    stop = bp.report(_record("stop", {"stop-probe:halt-then-print": "5"}), expected)
    assert stop["programs"]["stop-probe:halt-then-print"]["board_equals_rtl"] is True
    assert len(stop["probes"]) == 5
    printed = bp.report(_record("print"), expected)
    assert not any(r["first_divergence"] for r in printed["ladder"])


def test_a_capture_is_parsed_without_losing_a_byte_quietly() -> None:
    clean = bp.parse_capture(b"12\n7\n\r\nCYCLES=00001B89\r\n")
    assert clean == {"text": "12\n7\n", "dropped": 0, "halted": True, "cycles": 7049}
    noisy = bp.parse_capture(b"1\x002\n\r\nCYCLES=0000000A\r\n")
    assert (noisy["text"], noisy["dropped"]) == ("12\n", 1)
    cut = bp.parse_capture(b"12\n")
    assert (cut["halted"], cut["cycles"]) == (False, None)


def test_the_comparison_names_the_first_line_that_differs() -> None:
    assert bp.compare_text("1\n2\n", "1\n2\n") == {"status": "PARITY"}
    diff = bp.compare_text("8388608\n", "8388600\n")
    assert (diff["status"], diff["line"], diff["board"]) == ("MISMATCH", 0, "8388600")
    extra = bp.compare_text("", "5")
    assert (extra["status"], extra["board"]) == ("MISMATCH", "5")


def _runner():  # type: ignore[no-untyped-def]
    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "parity_board", ROOT / "rtl" / "scripts" / "parity_board.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _must_not(*_: object) -> None:
    raise AssertionError("configured the board")


def _programs_for(experiment: str) -> list[bp.BoardProgram]:
    return _corpus() if experiment == "parity" else bp.programs_for(experiment)


def test_the_runner_refuses_while_a_burn_in_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "programs_for", _programs_for)
    monkeypatch.setattr(runner, "burn_in_running", lambda: True)
    monkeypatch.setattr(runner, "configure", _must_not)
    assert runner.main(["--experiment", "parity", "--port", "/dev/null"]) == 2


def test_the_runner_refuses_without_an_experiment_named(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "burn_in_running", lambda: False)
    monkeypatch.setattr(runner, "configure", _must_not)
    assert runner.main(["--port", "/dev/null"]) == 2


def test_the_runner_refuses_a_payload_the_expectation_did_not_freeze(
        monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner()
    frozen = json.loads(json.dumps(_frozen()))
    frozen["stop"]["programs"]["stop-probe:halt-then-print"]["payload_sha256"] = "0" * 64
    monkeypatch.setattr(runner, "load_expected", lambda: frozen)
    monkeypatch.setattr(runner, "burn_in_running", lambda: False)
    monkeypatch.setattr(runner, "configure", _must_not)
    assert runner.main(["--experiment", "stop", "--port", "/dev/null"]) == 2


def test_the_runner_plans_without_a_board(monkeypatch: pytest.MonkeyPatch,
                                          capsys: pytest.CaptureFixture[str]) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "programs_for", _programs_for)
    assert runner.main([]) == 0
    out = capsys.readouterr().out
    assert "parity: 79 of 103 programs would be sent" in out
    assert "print: 1 of 1 programs would be sent" in out
    assert "stop: 5 of 5 programs would be sent" in out
