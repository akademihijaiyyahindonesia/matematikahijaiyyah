"""Layer 2 held against the code it describes -- and, once, against execution.

The rule carried over from layer 1: nothing here may be an inference. So a
derived effect is checked two ways. First against the text: the line it
names must hold the instruction that produced it. Then, for the loader,
against what actually happens when it runs -- freeze_load() executes
loader.hasm in the interpreter, and the effects layer 2 read out of the
source have to be the effects the machine shows.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui.program_graph import (  # noqa: E402
    hasm_calls,
    module_homes,
    unresolved,
    verilog_instances,
)
from hijaiyyah.nui.program_index import mmio_names, programs  # noqa: E402
from hijaiyyah.nui.program_summary import explain  # noqa: E402

FOUND = programs()
LOADER = "rtl/programs/loader.hasm"


def test_every_program_parses_with_the_assemblers_own_opcode_table() -> None:
    """parse_hasm refuses a mnemonic the assembler does not know, so reaching
    this line means all of them are real."""
    assert len(FOUND.hasm) >= 60
    assert len(FOUND.python) > 1000
    assert len(FOUND.verilog) >= 100


def test_memory_mapped_names_come_from_the_two_real_tables() -> None:
    names = mmio_names()
    assert names[0xFF0] == "RX_DATA"         # HISAMachine.REG_RX_DATA
    assert names[0xFF7] == "IMEM_DATA"       # HISAMachine.REG_IMEM_DATA
    assert names[0xFE3] == "SD_DATA"         # rtl/hcpu_pkg.vh `define
    assert names[0xFE0] == "SD_CMD"


def test_every_derived_effect_points_at_the_line_that_produced_it() -> None:
    for path in FOUND.hasm:
        summary = explain(path)
        text = (ROOT / path).read_text(encoding="utf-8").splitlines()
        for effect in summary.effects:
            line = text[effect.line - 1].upper()
            if effect.what.startswith(("reads", "writes")):
                address = effect.what.split("(")[1].rstrip(")")
                assert address[2:].upper() in line, (path, effect)
            elif effect.what.startswith("calls"):
                assert "CALL" in line, (path, effect)
            elif effect.what == "prints to the UART":
                assert "PRINT" in line or "EMITS" in line, (path, effect)


def test_what_the_loader_does_read_out_of_its_instructions() -> None:
    """The owner's expected answer: reads the UART, writes instruction memory,
    hands over to the loaded program. All three are derived -- and the
    handover is ERET after TRAP_EPC and TRAP_MODE, not a jump."""
    effects = {e.what for e in explain(LOADER).effects}
    assert "reads RX_DATA (0xff0)" in effects
    assert "reads RX_STATUS (0xff1)" in effects
    assert "writes IMEM_ADDR (0xff3)" in effects
    assert "writes IMEM_DATA (0xff7)" in effects
    assert "writes TRAP_EPC (0xff9)" in effects
    assert "returns from a trap (ERET)" in effects
    writes_addr = [e for e in explain(LOADER).effects if e.what.startswith("writes IMEM_ADDR")]
    assert writes_addr[0].times == 1, "the address is set once; the hardware advances it"


def test_the_loaders_derived_effects_are_what_execution_shows() -> None:
    """Layer 2 read "writes IMEM_DATA" and "hands over by ERET" out of the
    source. freeze_load runs the loader for real, in the interpreter: the
    write port must have advanced by the program's length, and the loaded
    program's own output must appear -- which only happens if the handover
    reached it."""
    from hijaiyyah.hisa.assembler import assemble
    from hijaiyyah.nui.freeze import freeze_load

    program = "        MOVI  R1, 7\n        PRINT R1\n        HALT\n"
    machine = freeze_load(program)
    assert machine.imem_waddr >= len(assemble(program))
    assert list(machine.output)[-1:] == [7]


def test_the_functions_the_directive_asked_about() -> None:
    freeze = explain("src/hijaiyyah/nui/freeze.py::freeze_load")
    for name in ("assemble", "HISAMachine", "mock_wire", "step"):
        assert name in freeze.interface[1], name
    assert "loader.hasm" in freeze.stated
    run = explain("src/hijaiyyah/nui/clockwork.py::run")
    for name in ("gf2_rank", "matrix_order_of", "Tick", "step"):
        assert name in run.interface[1], name
    assert run.stated.endswith("."), "the whole first sentence, not a cut line"


def test_every_call_and_instance_resolves_or_is_a_named_vendor_primitive() -> None:
    missing = unresolved()
    assert missing == {"hasm": [], "verilog": []}, missing
    links, _ = hasm_calls(LOADER)
    assert all(":" in link.target for link in links)


def test_a_module_with_two_homes_is_not_resolved_by_guessing() -> None:
    """hcpu_dataram (FPGA RAM and sky130 macro) and hcpu_top (RTL and
    synthesised netlist) each have two homes, chosen by the build flow. Both
    are linked; neither is picked."""
    homes = module_homes()
    assert len(homes["hcpu_dataram"]) == 2
    assert len(homes["hcpu_top"]) == 2
    for key in FOUND.verilog:
        links, _, _ = verilog_instances(key)
        targets = [link.target for link in links if link.target.endswith("::hcpu_dataram")]
        if targets:
            assert len(targets) == 2, (key, targets)
            assert all("one of several homes" in link.via for link in links
                       if link.target.endswith("::hcpu_dataram"))
            break
    else:
        raise AssertionError("nothing instantiates hcpu_dataram")


def test_the_authors_words_are_quoted_not_written() -> None:
    """stated is the unit's own opening sentence -- it must appear in the
    file, character for character once whitespace is collapsed."""
    for key in ("src/hijaiyyah/nui/freeze.py::freeze_load",
                "src/hijaiyyah/nui/clockwork.py::run"):
        summary = explain(key)
        source = " ".join((ROOT / key.split("::")[0]).read_text().split())
        assert summary.stated in source, key
