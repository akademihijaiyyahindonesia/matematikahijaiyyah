"""The board run, held before it happens.

The board carries the 72-hour burn-in, so nothing here touches it. What can
be held now is everything the run will rest on: which programs go and why the
rest do not, that no program sent can reach the card, that every observation
epilogue prints the state it replaced, that the RTL puts the same bytes on the
wire as the interpreter wherever the timer is not read, that a capture is
parsed without losing a byte quietly -- and that the runner refuses to start
while a burn-in is alive.
"""
from __future__ import annotations

import functools
import importlib.util
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.hisa.opcodes import OpCode  # noqa: E402
from hijaiyyah.nui import board_parity as bp  # noqa: E402
from hijaiyyah.nui.parity_model import (  # noqa: E402
    Program,
    _printed_text,
    compile_rtl,
    cycle_budget,
    run_interpreter,
    run_rtl,
)


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
    assert (len(_sent()), len(_corpus())) == (83, 107)
    reasons = [b.excluded.split(":")[0].split(" (")[0] for b in _corpus() if b.excluded]
    assert reasons.count("touches the SD window") == 9
    assert reasons.count("does not halt under the loader") == 15
    assert not [b.name for b in _corpus() if "epilogue" in b.excluded], "an epilogue failed"
    assert {"print-ladder", "stop-probe:halt-then-print", "stop-probe:halt-then-store",
            "stop-probe:ret-then-print"} <= {b.name for b in _sent()}


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
def test_the_rtl_puts_the_same_bytes_on_the_wire() -> None:
    """Every payload, epilogue included, at address 64 behind NOPs on both
    engines: the wire agrees everywhere except the four that read the timer.
    The stop probes are left out -- their difference is what they measure."""
    nop = int(OpCode.NOP) << 24
    work = Path(tempfile.mkdtemp())
    sim = compile_rtl(work)

    def one(b: bp.BoardProgram) -> tuple[str, bool]:
        words = [nop] * bp.LOAD_BASE + b.payload
        prog = Program(b.name, words, {}, {})
        i = run_interpreter(prog, max_steps=len(words) * 40 + 20_000, hcheck_interval=0)
        r = run_rtl(sim, words, cycle_budget(i) + 2_000, work)
        return b.name, _printed_text(i.events["TX"]) == _printed_text(r.events["TX"])

    checked = [b for b in _sent() if not b.name.startswith("stop-probe")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(pool.map(one, checked))
    assert {n for n, same in results.items() if not same} == TIMED
    assert all(_by_name()[n].reads & {"COUNTER"} for n in TIMED)


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


def test_the_runner_refuses_while_a_burn_in_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "corpus", lambda: _corpus())
    monkeypatch.setattr(runner, "burn_in_running", lambda: True)

    def must_not(*_: object) -> None:
        raise AssertionError("configured the board during a burn-in")

    monkeypatch.setattr(runner, "configure", must_not)
    assert runner.main(["--port", "/dev/null"]) == 2


def test_the_runner_plans_without_a_board(monkeypatch: pytest.MonkeyPatch,
                                          capsys: pytest.CaptureFixture[str]) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "corpus", lambda: _corpus())
    assert runner.main([]) == 0
    assert "83 of 107 programs would be sent" in capsys.readouterr().out
