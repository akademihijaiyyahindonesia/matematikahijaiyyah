"""
The board path, checked before the board arrives rather than on the day.

Two failures were sitting here, and neither would have shown up until someone
tried to build for silicon:

1. rtl/fpga/gowin/Makefile hand-listed its sources, exactly the way
   rtl/tb/Makefile did. hcpu_mmio.v and hcpu_trap.v were added to the design
   and not to that list, so `make sim`, `make synth` and `make bitstream` all
   died on "Unknown module type".

2. hcpu_top gained an input -- `uart_rx` -- and NEITHER board wrapper brought
   it out. An unconnected input is not an error in Verilog: it floats. The
   receiver, the timer interrupt and every trap that depends on them would
   have been dead on the board while simulating perfectly, which is the worst
   shape a fault can take.

So: every input hcpu_top declares must be connected in every wrapper, and
every wrapper port that reaches a pin must have one.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl"
BOARDS = {
    "gowin": (RTL / "fpga" / "gowin" / "hcpu_gowin_top.v",
              RTL / "fpga" / "gowin" / "hcpu_gowin.cst"),
    "xilinx": (RTL / "fpga" / "xilinx" / "hcpu_xilinx_top.v",
               RTL / "fpga" / "xilinx" / "hcpu_xilinx.xdc"),
}


def _top_inputs() -> set[str]:
    """The input ports hcpu_top declares, from its own port list."""
    text = (RTL / "hcpu_top.v").read_text(encoding="utf-8")
    head = text[text.index("module hcpu_top"):text.index(");")]
    return set(re.findall(r"input\s+wire\s+(?:\[[^\]]+\]\s*)?(\w+)", head))


@pytest.mark.parametrize("board", sorted(BOARDS))
def test_every_core_input_is_connected_in_the_wrapper(board: str) -> None:
    """
    An unconnected input floats. It does not fail synthesis, it does not fail
    simulation of the core, and it does not fail until the hardware misbehaves.
    """
    wrapper = BOARDS[board][0].read_text(encoding="utf-8")
    inst = wrapper[wrapper.index("hcpu_top #("):]
    connected = set(re.findall(r"\.(\w+)\s*\(", inst))
    missing = _top_inputs() - connected
    assert not missing, f"{board} leaves these hcpu_top inputs floating: {missing}"


def _wrapper_ports(src: Path) -> list[str]:
    """Port names of the BOARD TOP, expanded per bit -- led[5:0] is six pins.

    Named, not guessed by position. This used to take the first `module hcpu_`
    in the file, which held while every wrapper was one module. hcpu_gowin_top.v
    is now two -- hcpu_gowin_core carries the telemetry sideband, and a
    pin-level hcpu_gowin_top wraps it -- and the old rule silently walked the
    core's port list instead, which is the one list that must NOT have pins.

    The module this test means is the one the file is named for, so that is
    what it asks for. A file that stops containing it fails loudly here rather
    than checking something else and passing.
    """
    text = src.read_text(encoding="utf-8")
    marker = f"module {src.stem}"
    assert marker in text, f"{src.name} does not declare {src.stem}"
    head = text[text.index(marker):]
    head = head[:head.index(");")]
    out: list[str] = []
    for width, name in re.findall(
            r"(?:input|output|inout)\s+wire\s+(\[[^\]]+\]\s*)?(\w+)", head):
        if width:
            # A width the board must be able to count, so a macro or a
            # parameter is a failure to report rather than a crash to debug:
            # a pin list cannot be checked against a bound nobody can read.
            bound = re.search(r"\[\s*(\d+)", width)
            assert bound, (
                f"{src.name}: port `{name}` is declared `{width.strip()}` -- "
                "a board top must give a literal width, or its pins cannot be "
                "counted against the constraints file"
            )
            out.extend(f"{name}[{i}]" for i in range(int(bound.group(1)) + 1))
        else:
            out.append(name)
    return out


def _assigned_pins(constraints: Path) -> set[str]:
    """
    Ports that actually have a LOCATION, not merely a mention.

    Substring searching was not enough and sabotage proved it: deleting an
    IO_LOC line leaves the matching IO_PORT behind, so the name is still in
    the file; and `led` is a substring of `led[0]`, so a bus port matched even
    with every one of its pins gone.
    """
    text = constraints.read_text(encoding="utf-8")
    gowin = re.findall(r'^\s*IO_LOC\s+"([^"]+)"\s+\S+', text, re.M)
    xilinx = re.findall(r"PACKAGE_PIN\s+\S+.*?get_ports\s*\{?\s*([\w\[\]]+)",
                        text)
    return {p.strip() for p in gowin + xilinx}


@pytest.mark.parametrize("board", sorted(BOARDS))
def test_every_wrapper_port_has_a_pin(board: str) -> None:
    src, constraints = BOARDS[board]
    pins = _assigned_pins(constraints)
    missing = [p for p in _wrapper_ports(src) if p not in pins]
    assert not missing, f"{board}: no pin location for {missing}"


def test_uart_receive_reaches_a_pin_on_both_boards() -> None:
    """
    Named on its own because it is the one that was missing, and because the
    whole interrupt story rests on it: no rx pin, no rx byte, no UART trap.
    """
    for board, (src, constraints) in BOARDS.items():
        assert "uart_rxd" in src.read_text(encoding="utf-8"), board
        assert "uart_rxd" in _assigned_pins(constraints), f"{board}: no rx pin"


def test_the_gowin_makefile_finds_its_sources_instead_of_listing_them() -> None:
    makefile = (RTL / "fpga" / "gowin" / "Makefile").read_text(encoding="utf-8")
    assert "$(wildcard $(RTL_DIR)/hcpu_*.v)" in makefile
    body = makefile.split("SOURCES")[1].split("\n\n")[0]
    for stale in ("hcpu_fetch.v", "hcpu_decode.v", "hcpu_hisab.v"):
        assert stale not in body, "a hand-written source list is back"


def test_the_xilinx_flow_globs_too() -> None:
    """It already did, which is why only the Gowin path broke."""
    tcl = (RTL / "fpga" / "xilinx" / "build.tcl").read_text(encoding="utf-8")
    assert "glob" in tcl and "../../*.v" in tcl
