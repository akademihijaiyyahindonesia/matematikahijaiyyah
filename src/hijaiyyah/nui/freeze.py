"""Freeze mode: the loader's own wire protocol, mocked -- no RTL simulator,
no real clock, every test built on it landing in milliseconds instead of the
seconds an Icarus run costs.

rtl/tb/tb_gowin_loader_nui.v already proved the real claim: an actual
bit-serial UART transmission, timed in simulated nanoseconds, carrying
nui_embedding.hasm's 48 words into a running board. That test stays --
freeze mode does not replace it, because only a real bit-serial wire proves
the RTL's framing logic actually holds in time. What freeze mode drops is
the WAITING: HISAMachine.step() already runs loader.hasm as an interpreter,
one instruction per call, and its rx_queue already holds incoming bytes as
a plain Python list rather than a real per-bit UART signal (hisa/machine.py
pops one byte per REG_RX_DATA access, same as the real peripheral would,
just without the 27 MHz clock counting cycles in between). test_boot_path.py
already leaned on exactly this to prove the write port advances -- this
module only names the pattern and gives it one shared, tested home instead
of a private helper redefined per test file.

"Freeze" names what is missing, not what is faked: the BYTES are the same
bytes rtl/scripts/send_program.py's encode() would put on a real wire (most
significant byte first, word count then words -- mock_wire and encode must
agree, and a test below checks that directly), consumed in the same order
a real loader would see them. Only the clock is frozen -- collapsed to a
plain instruction-by-instruction loop, no Hz, no bit timing -- because
order is everything the protocol depends on (compose_step's own
order-sensitivity, the loader's SHLI-then-OR word assembly), and order is
exactly what a frozen list still preserves.

freeze_load's own wall-clock time is Python interpreter overhead -- it says
nothing about Hz. The functions below say something about Hz instead, by
computing it directly rather than measuring it: wire_seconds/
wire_bytes_per_second give the byte-level latency a real UART actually has
at 115200 baud; bit_period_seconds/clock_period_seconds/clocks_per_uart_bit
go one level down, to the electrical "signal pulling" itself -- one UART
bit's real duration versus one real HCPU clock edge's, both sourced from
the same CLK_HZ/BAUD constants rtl/hcpu_uart_rx.v computes its own DIVISOR
from. The gap between those two is not decoration: it is the actual reason
that DIVISOR exists in silicon -- the chip's own clock runs 234 times
faster than the wire it talks over, every real UART bit sampled 234 clock
edges into holding steady, not read on faith the instant it changes.

**One step this module deliberately does NOT take:** it never turns
freeze_load's own step count (machine.cycle) into a boot EXECUTION latency
by multiplying it against clock_period_seconds(). hisa/machine.py's own
comment on REG_COUNTER says exactly why not -- "it counts real clock
cycles, and this interpreter does not model the pipeline's timing.
Reporting a counter here that 'agrees' with the RTL would mean one of the
two was lying." The wire's latency (wire_seconds) is honestly computable
from constants alone, independent of any interpreter; how long loader.hasm's
receive loop plus a loaded program's own instructions actually take on
silicon is not -- that number belongs to rtl/fpga/gowin/hcpu_gowin_top.v's
own real CYCLES= UART report (rtl/tb/tb_gowin_top.v, rtl/tb/tb_parity.v),
or an actual RTL/hardware run, not to this module.

**The rack's own heartbeat, in click-bits.** uart_bit_midpoint_clocks()
names rtl/hcpu_uart_rx.v's own HALF constant -- the exact clock count into
a bit where the real receiver samples it, "so the first sample lands in
the middle of the start bit rather than on its edge." rack_heartbeat_
clocks()/rack_heartbeat_seconds() apply that same per-bit clock count
across all NUM_SLOTS (nui.rack) nodes, one real byte each, back to back --
not clockwork.run_rack()'s software ticks (those are GF(2) matrix
composition, zero real clocks), but what those same 28 nodes' own opcodes
would cost sent one at a time over the actual wire, counted in real
integer HCPU clock "clicks," the same unit uart_bit_midpoint_clocks()
already names.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Optional, Sequence

from ..core.master_table import MASTER_TABLE
from ..hisa.assembler import assemble
from ..hisa.machine import HISAMachine
from .rack import NUM_SLOTS

ROOT = Path(__file__).resolve().parents[3]
LOADER_HASM = ROOT / "rtl" / "programs" / "loader.hasm"

#: Where loader.hasm writes the program and enters it -- the address
#: rtl/scripts/send_program.py's LOAD_BASE names. Absolute labels have to be
#: assembled against it; see freeze_load's docstring for what happened when
#: they were not.
LOAD_BASE = 64

#: rtl/hcpu_uart_rx.v, rtl/hcpu_uart_tx.v, rtl/tb/tb_gowin_loader_nui.v's own
#: BAUD localparam -- the real board's default, not a number picked for this
#: module. Freezing the clock for freeze_load() drops this rate entirely
#: (an interpreter step is not a bit period); wire_seconds/wire_bytes_per_second
#: below put it back, as a fact ABOUT the real wire, checked separately from
#: whatever freeze_load happens to cost in wall-clock Python time.
UART_BAUD = 115200

#: 1 start + 8 data (LSB first) + 1 stop -- send_byte's own framing in
#: rtl/tb/tb_gowin_loader.v and tb_gowin_loader_nui.v, standard 8N1.
BITS_PER_UART_BYTE = 10


def wire_bytes_per_second(*, baud: int = UART_BAUD) -> float:
    """The real board's throughput at 8N1 framing -- not measured, computed
    directly from baud and framing width, the same arithmetic
    rtl/fpga/gowin/hcpu_gowin_top.v's own comments do for IDLE_CLKS."""
    return baud / BITS_PER_UART_BYTE


def wire_seconds(num_bytes: int, *, baud: int = UART_BAUD) -> float:
    """How long num_bytes really takes over the wire at the real board's baud
    rate -- what mock_wire's bytes would cost a real UART, as opposed to
    freeze_load's own wall-clock time, which measures Python interpreter
    overhead and says nothing about Hz at all."""
    return num_bytes * BITS_PER_UART_BYTE / baud


#: rtl/fpga/gowin/hcpu_gowin_top.v's own OSC_HZ -- the real Tang Nano 20K
#: crystal, and SYS_HZ (what every other module's CLK_HZ is wired to) when
#: USE_PLL is off, which is how rtl/tb/tb_gowin_loader_nui.v's own
#: HALF_PERIOD (18.5 ns, 27 MHz) already runs it. Not hcpu_uart_tx.v's own
#: standalone default (50_000_000) -- that parameter is never instantiated
#: at that value on this board; the wrapper always overrides it with SYS_HZ.
HCPU_CLK_HZ = 27_000_000


def clock_period_seconds(*, clk_hz: int = HCPU_CLK_HZ) -> float:
    """One real HCPU clock edge's duration -- the fastest latency anywhere
    in this system, the "high speed processing unit"'s own internal clock,
    not the UART wire it happens to talk over. ~37 ns at the real 27 MHz."""
    return 1.0 / clk_hz


def bit_period_seconds(*, baud: int = UART_BAUD) -> float:
    """One UART bit's real electrical duration -- the "signal pulling" time
    a real rx_in/uart_rxd line actually holds a level for. Matches
    rtl/tb/tb_gowin_loader_nui.v's own BIT_NS (that one in nanoseconds,
    this one in seconds) -- the same number, not a re-derivation of a
    different one."""
    return 1.0 / baud


def clocks_per_uart_bit(*, baud: int = UART_BAUD, clk_hz: int = HCPU_CLK_HZ) -> int:
    """How many real HCPU clock cycles fit inside one UART bit -- the exact
    DIVISOR rtl/hcpu_uart_rx.v computes to sample the line at its middle,
    recomputed here independently from the same CLK_HZ/BAUD it uses, not
    copied from it (checked against the RTL file directly in
    test_nui_freeze.py). This is the real "cosmic speed" gap: the chip's
    own clock runs this many times faster than the wire it talks over."""
    return clk_hz // baud


def uart_bit_midpoint_clocks(*, baud: int = UART_BAUD, clk_hz: int = HCPU_CLK_HZ) -> int:
    """Real HCPU clock cycles from a bit's falling edge to its SAMPLING
    MIDPOINT -- rtl/hcpu_uart_rx.v's own HALF = DIVISOR / 2, "so the first
    sample lands in the middle of the start bit rather than on its edge --
    where a clock a few percent off still reads the right value." The
    whole correctness argument that module's own header gives for why UART
    receivers sample here at all, recomputed independently from the same
    CLK_HZ/BAUD clocks_per_uart_bit() already uses, not copied from the
    RTL's comment."""
    return clocks_per_uart_bit(baud=baud, clk_hz=clk_hz) // 2


def rack_heartbeat_clocks(num_nodes: int = NUM_SLOTS, *, baud: int = UART_BAUD,
                           clk_hz: int = HCPU_CLK_HZ) -> int:
    """Real HCPU clock cycles to send one byte per rack node, back to back
    over the real UART: num_nodes * BITS_PER_UART_BYTE * clocks_per_uart_bit().
    Not clockwork.run_rack()'s 28 software ticks (those cost zero real
    clocks -- gf2_rank and matrix_order_of, not a wire) -- this is what
    those same 28 nodes would cost if each one's own byte (nui.rack's
    opcode) went out over the real board's wire, one HCPU clock "click" at
    a time, counted as an integer the way real hardware must (clocks_per_
    uart_bit() floors CLK_HZ/BAUD, so this is not identical to
    wire_seconds()'s idealised real-valued baud -- checked to be close but
    distinct in test_nui_freeze.py, honestly, not glossed over)."""
    return num_nodes * BITS_PER_UART_BYTE * clocks_per_uart_bit(baud=baud, clk_hz=clk_hz)


def rack_heartbeat_seconds(num_nodes: int = NUM_SLOTS, *, baud: int = UART_BAUD,
                            clk_hz: int = HCPU_CLK_HZ) -> float:
    """rack_heartbeat_clocks(), in real seconds: clock count times
    clock_period_seconds() -- the rack's own "heart sequence," counted in
    real integer clock-clicks rather than wire_seconds()'s idealised
    fractional baud."""
    clocks = rack_heartbeat_clocks(num_nodes, baud=baud, clk_hz=clk_hz)
    return clocks * clock_period_seconds(clk_hz=clk_hz)


def mock_wire(words: Sequence[int]) -> List[int]:
    """The loader's byte protocol, frozen into one ordered list: word count
    then every word, most significant byte first -- the exact byte sequence
    rtl/scripts/send_program.py's encode() puts on a real wire, not a
    parallel re-derivation of it (checked directly in test_nui_freeze.py)."""
    out = bytearray(struct.pack(">I", len(words)))
    for word in words:
        out += struct.pack(">I", word & 0xFFFFFFFF)
    return list(out)


def freeze_load(program_src: str, *, base_dir: Optional[Path] = None,
                 max_steps: int = 20000) -> HISAMachine:
    """Run loader.hasm against a mocked wire carrying `program_src`, no RTL
    simulator and no real clock involved: assemble the payload, hand its
    bytes to a fresh HISAMachine as rx_queue (mock_wire's frozen list, in
    place of a real bit-serial signal), then step the interpreter -- one
    instruction per call, the "unit bit per klik" granularity a real loader
    would also see, just without the wait -- until the loaded program HALTs
    or max_steps runs out.

    Returns the machine itself so a caller reads whatever the program left
    behind (m.output for PRINT, m.imem_waddr for how far the write port
    advanced, m.mem for stores) exactly the way rtl/tb/tb_gowin_loader_nui.v
    reads UART bytes and imem_waddr off simulated silicon -- same claims,
    mocked wire and clock, not a different mechanism.

    **Assembled at LOAD_BASE, not zero -- and until it was, this mock
    reproduced the board's own bug.** The loader writes the program to
    address 64, so a program that loads an absolute label
    (`MOVI R1, handler`) assembled at 0 points at a word inside loader.hasm
    instead. Measured on trap_timer.hasm through this exact path: at base 0,
    2,120 traps taken and no HALT; at LOAD_BASE, one trap, R8 = 1, HALT --
    the same split the Tang Nano 20K showed before send_program.py was
    fixed. None of the programs this module's tests used carries an
    absolute label (nui_embedding: 0 of 48 words move, letters: 0 of 37),
    which is why the mock looked faithful while it was not."""
    words = assemble(program_src, base_dir=base_dir, base=LOAD_BASE)
    machine = HISAMachine(MASTER_TABLE)
    machine.code = assemble(LOADER_HASM.read_text(encoding="utf-8"))
    machine.rx_queue = mock_wire(words)
    for _ in range(max_steps):
        if machine.step() is None:
            break
    return machine


def executed_letters(machine: HISAMachine) -> List[str]:
    """Which letters actually FIRED, in the order they fired -- read
    directly off machine.trace's own per-instruction description
    (hisa/machine.py's _execute writes "{char} → H0 += {name}" for every
    letter opcode, 0xE0..0xFB), not re-derived from the source program or
    from nui.rack.RACK. Answers "did the rack's own Master Table order
    survive being sent over freeze_load's mocked wire, loaded by
    loader.hasm, and executed instruction by instruction" with what the
    interpreter actually did, not what was merely assembled -- a wrong
    byte order, a wrong loader write, or a wrong ERET handoff would all
    show up here as a wrong sequence, not just a wrong final H0."""
    return [entry.description.split(" → ")[0] for entry in machine.trace
            if " → H0 += " in entry.description]
