"""freeze.py: the loader's wire protocol mocked -- checked against the same
claims rtl/tb/tb_gowin_loader_nui.v proves on simulated hardware, and against
rtl/scripts/send_program.py's own encode(), so "frozen" cannot quietly mean
"different protocol" instead of "no clock."
"""
from __future__ import annotations

import re
import struct
import sys
import time
from pathlib import Path

import pytest

from hijaiyyah.nui.freeze import (
    HCPU_CLK_HZ,
    LOADER_HASM,
    UART_BAUD,
    bit_period_seconds,
    clock_period_seconds,
    clocks_per_uart_bit,
    executed_letters,
    freeze_load,
    mock_wire,
    rack_heartbeat_clocks,
    rack_heartbeat_seconds,
    uart_bit_midpoint_clocks,
    wire_bytes_per_second,
    wire_seconds,
)
from hijaiyyah.nui.rack import NUM_SLOTS, RACK

ROOT = Path(__file__).resolve().parents[2]
NUI_EMBEDDING = ROOT / "rtl" / "programs" / "nui_embedding.hasm"
LETTERS_HASM = ROOT / "rtl" / "programs" / "letters.hasm"

sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
from send_program import encode  # noqa: E402


def test_mock_wire_matches_send_programs_own_encode_byte_for_byte():
    words = [0xE0, 0xE4, 0x12345678, 0]
    assert bytes(mock_wire(words)) == encode(words)


def test_mock_wire_is_big_endian_count_then_words():
    words = [1, 2, 3]
    stream = mock_wire(words)
    assert stream[:4] == list(struct.pack(">I", 3))
    assert stream[4:8] == list(struct.pack(">I", 1))


def test_freeze_load_matches_the_proven_physical_output():
    """tb_gowin_loader_nui.v proves this exact program, loaded over a real
    bit-serial UART wire in Icarus simulation, prints "2\\n2\\n2\\n6\\n6\\n".
    Freeze mode mocks the wire and the clock, not the protocol or the
    program -- so it must land on the same five numbers, read directly off
    m.output rather than decoded from UART bytes."""
    machine = freeze_load(NUI_EMBEDDING.read_text(encoding="utf-8"),
                           base_dir=NUI_EMBEDDING.parent)
    assert machine.output == [2, 2, 2, 6, 6]


def test_freeze_load_really_went_through_the_write_port():
    """Same check tb_gowin_loader_nui.v makes of imem_waddr -- 48 words
    written starting at address 64 -- so this cannot pass by coincidence if
    the mocked wire were silently skipped and the payload just happened to
    already be sitting in memory."""
    machine = freeze_load(NUI_EMBEDDING.read_text(encoding="utf-8"),
                           base_dir=NUI_EMBEDDING.parent)
    assert machine.imem_waddr == 64 + 48


def test_freeze_load_relocates_absolute_labels_like_the_real_loader():
    """The claim this module makes -- same bytes as the real wire -- was only
    true for label-free programs. Measured before the fix: trap_timer.hasm at
    base 0 took 2,120 traps and never halted, exactly as the board did before
    send_program.py assembled at LOAD_BASE. Every program these tests used
    was label-free, so nothing here could see it."""
    trap_timer = ROOT / "rtl" / "programs" / "trap_timer.hasm"
    machine = freeze_load(trap_timer.read_text(encoding="utf-8"),
                          base_dir=trap_timer.parent)
    assert machine._halted, "the handler address still names a word inside the loader"
    assert machine.regs.gpr[8] == 1
    assert sum("TRAP" in t.description for t in machine.trace) == 1


def test_freeze_loads_base_is_the_host_tools_base():
    """One load address, written in two places -- they have to agree."""
    import send_program

    from hijaiyyah.nui.freeze import LOAD_BASE

    assert LOAD_BASE == send_program.LOAD_BASE == 64


def test_uart_baud_matches_the_real_rtl_peripherals():
    """UART_BAUD must be the same constant the board actually uses, not a
    number chosen independently for this module -- rtl/hcpu_uart_rx.v and
    rtl/hcpu_uart_tx.v both default BAUD to this exact value."""
    rx = (ROOT / "rtl" / "hcpu_uart_rx.v").read_text(encoding="utf-8")
    tx = (ROOT / "rtl" / "hcpu_uart_tx.v").read_text(encoding="utf-8")
    assert f"parameter BAUD   = {UART_BAUD}" in rx
    assert f"parameter BAUD     = {UART_BAUD}" in tx


def test_wire_bytes_per_second_is_the_real_boards_throughput():
    """115200 baud / 10 bits per byte (8N1) = 11520 bytes/s exactly -- the
    real wire's speed, not freeze_load's incidental Python wall-clock time."""
    assert wire_bytes_per_second() == 11520.0


def test_wire_seconds_matches_what_a_real_uart_would_take():
    """nui_embedding.hasm's own wire size (4-byte count + 48 words * 4 bytes
    = 196 bytes) at the real board's baud rate -- an independent arithmetic
    check, not a re-assertion of wire_seconds' own formula."""
    stream_bytes = len(mock_wire([0] * 48))
    assert stream_bytes == 196
    assert wire_seconds(stream_bytes) == pytest.approx(196 * 10 / 115200)
    assert wire_seconds(stream_bytes) == pytest.approx(0.017014, abs=1e-6)


def test_hcpu_clk_hz_matches_the_real_boards_oscillator():
    """HCPU_CLK_HZ must be the real Tang Nano 20K crystal
    (rtl/fpga/gowin/hcpu_gowin_top.v's OSC_HZ, which SYS_HZ equals with the
    PLL off -- the same clock rtl/tb/tb_gowin_loader_nui.v's own
    HALF_PERIOD=18.5ns runs at), not hcpu_uart_tx.v's own standalone
    default (50_000_000), which this board never actually instantiates."""
    wrapper = (ROOT / "rtl" / "fpga" / "gowin" / "hcpu_gowin_top.v").read_text(encoding="utf-8")
    match = re.search(r"OSC_HZ\s*=\s*([\d_]+)", wrapper)
    assert match is not None, "OSC_HZ localparam not found in hcpu_gowin_top.v"
    assert int(match.group(1).replace("_", "")) == HCPU_CLK_HZ


def test_clock_period_is_faster_than_bit_period_by_the_real_divisor():
    """The point of the whole hierarchy: one HCPU clock edge is much shorter
    than one UART bit -- checked as an actual inequality and an exact ratio,
    not just asserted to differ."""
    assert clock_period_seconds() < bit_period_seconds()
    ratio = bit_period_seconds() / clock_period_seconds()
    assert ratio == pytest.approx(HCPU_CLK_HZ / UART_BAUD)


def test_clocks_per_uart_bit_matches_hcpu_uart_rxs_own_divisor_formula():
    """rtl/hcpu_uart_rx.v computes DIVISOR = CLK_HZ / BAUD (integer, Verilog
    truncates) to find the middle of a bit for sampling. Recomputed here
    independently from the same two constants -- not copied from a comment
    -- and pinned to the concrete value so a future change to either
    constant cannot silently drift unnoticed."""
    assert clocks_per_uart_bit() == HCPU_CLK_HZ // UART_BAUD == 234


def test_hisamachines_own_cycle_counter_disclaims_real_pipeline_timing():
    """freeze.py's module docstring explains why it never turns
    freeze_load's step count into a boot-execution latency: HISAMachine
    itself already disclaims that its cycle counter models real pipeline
    timing. This pins the exact disclaimer -- if hisa/machine.py's own
    comment ever changes, this test forces freeze.py's docstring (and this
    test) to be reconsidered rather than silently going stale."""
    source = (ROOT / "src" / "hijaiyyah" / "hisa" / "machine.py").read_text(encoding="utf-8")
    assert "it counts real clock cycles, and this interpreter does" in source
    assert "not model the pipeline's timing" in source


# ── clocking speed test: midpoint sampling, the rack's own heartbeat ──


def test_uart_bit_midpoint_clocks_matches_hcpu_uart_rxs_own_half_formula():
    """rtl/hcpu_uart_rx.v's own HALF = DIVISOR / 2 -- "so the first sample
    lands in the middle of the start bit rather than on its edge." Checked
    against the RTL file's own text directly, and against the concrete
    value (234 // 2), not just trusted to agree."""
    source = (ROOT / "rtl" / "hcpu_uart_rx.v").read_text(encoding="utf-8")
    assert "localparam integer HALF    = DIVISOR / 2;" in source
    assert uart_bit_midpoint_clocks() == clocks_per_uart_bit() // 2 == 117


def test_rack_heartbeat_clocks_covers_every_node_one_real_byte_each():
    """28 rack nodes, one opcode byte each, back to back over the real
    wire -- NUM_SLOTS * BITS_PER_UART_BYTE * clocks_per_uart_bit(), an
    independent arithmetic check, not a re-assertion of the function's own
    formula."""
    assert NUM_SLOTS == 28
    assert rack_heartbeat_clocks() == 28 * 10 * 234 == 65520
    assert rack_heartbeat_clocks(num_nodes=1) == 10 * 234 == 2340


def test_rack_heartbeat_clocks_divided_by_cosmic_speed_gives_back_the_bit_count():
    """The byte/bit count and the "cosmic speed" ratio (clocks_per_uart_bit,
    the chip-vs-wire gap named in freeze.py's own docstring) are two
    descriptions of the SAME latency, not independent numbers: dividing the
    rack's clock-heartbeat by the cosmic-speed ratio must give back exactly
    the bit count the byte/bit counting started from (28 bytes * 10
    bits/byte = 280 bits) -- checked as an exact integer division, not an
    approximation."""
    total_bits = NUM_SLOTS * 10
    assert total_bits == 280
    assert rack_heartbeat_clocks() // clocks_per_uart_bit() == total_bits
    assert rack_heartbeat_clocks() % clocks_per_uart_bit() == 0


def test_rack_heartbeat_seconds_is_close_to_but_not_identical_to_wire_seconds():
    """Both describe the same 28 real bytes over the same real wire, but
    from two different countings: wire_seconds() assumes an idealised
    real-valued 115200 baud; rack_heartbeat_seconds() counts real integer
    HCPU clock clicks (clocks_per_uart_bit() floors CLK_HZ/BAUD). They must
    agree to within a fraction of a percent -- and must NOT be bit-for-bit
    identical, or one of the two countings would be pointless."""
    heartbeat = rack_heartbeat_seconds()
    wire = wire_seconds(NUM_SLOTS)
    assert heartbeat == pytest.approx(wire, rel=2e-3)
    assert heartbeat != wire


# ── freeze_load is make bridge + make send, mass-mocked on this host ──


def test_freeze_loads_loader_is_the_exact_file_make_bridge_bakes_in():
    """rtl/fpga/gowin/Makefile's own `bridge` target flashes a REAL Tang
    Nano 20K bitstream with loader.hasm baked in
    (`PROGRAM=$(RTL_DIR)/programs/loader.hasm flash`), and `make send`
    ships a program to it over a real USB-serial wire from this same host
    (rtl/scripts/send_program.py). freeze_load's LOADER_HASM must be that
    EXACT file, not a copy -- so freeze_load is that same wrapper's own
    protocol, mass-mocked (HISAMachine.rx_queue standing in for the real
    wire and the real board's imem, both living in this host's RAM
    instead), not a separately-invented one."""
    makefile = (ROOT / "rtl" / "fpga" / "gowin" / "Makefile").read_text(encoding="utf-8")
    assert "PROGRAM=$(RTL_DIR)/programs/loader.hasm flash" in makefile
    assert LOADER_HASM == ROOT / "rtl" / "programs" / "loader.hasm"
    assert LOADER_HASM.exists()


def test_mock_wire_is_the_exact_bytes_make_send_would_put_on_the_real_wire():
    """rtl/fpga/gowin/Makefile's `send` target runs
    rtl/scripts/send_program.py PORT PROG -- the same encode() already
    checked against mock_wire byte-for-byte elsewhere in this file. Pinned
    again here specifically as the make-send claim, not a generic
    protocol claim, so this test fails first if that Makefile target ever
    stops calling send_program.py."""
    makefile = (ROOT / "rtl" / "fpga" / "gowin" / "Makefile").read_text(encoding="utf-8")
    assert "scripts/send_program.py $(PORT) $(PROG)" in makefile


# ── does the rack's order survive the wire? ──────────────────────


def test_freeze_loads_own_trace_preserves_the_racks_master_table_order():
    """rtl/programs/letters.hasm accumulates BA, SIN, MIM first (its own
    first check, HNRM2==112, cross-checked below), then all 28 letters in
    Master Table order -- the exact order nui.rack.RACK already carries.
    Assembled, sent over freeze_load's mocked wire, loaded by loader.hasm,
    and executed one instruction at a time: if byte order, word order, the
    loader's own write-port advance, or its ERET handoff into the loaded
    program were wrong, the letters would fire scrambled even though the
    final accumulated H0 (order-insensitive v18 addition) might still look
    fine. executed_letters() reads what actually fired, in order, off
    machine.trace -- not off the source program."""
    machine = freeze_load(LETTERS_HASM.read_text(encoding="utf-8"),
                           base_dir=LETTERS_HASM.parent)
    fired = executed_letters(machine)
    assert len(fired) == 3 + 28
    assert fired[:3] == ["ب", "س", "م"]
    assert fired[-28:] == [c.char for c in RACK]


def test_freeze_loads_letters_hasm_still_matches_its_own_proven_norm():
    """The other half of the same run: rtl/programs/letters.hasm's own
    header claims 0x100 == 112, "the same value tb_gowin_top reads" on
    real hardware. Checked here too, so this test is not only about order
    while silently ignoring whether the loaded program computed anything
    right at all."""
    machine = freeze_load(LETTERS_HASM.read_text(encoding="utf-8"),
                           base_dir=LETTERS_HASM.parent)
    assert machine.data_mem[0x100] == 112


def test_freeze_load_runs_in_well_under_a_second():
    """Not a race against Icarus itself -- just pins the property "very
    ultra fast" is actually about: no subprocess, no simulator, comfortably
    real-time."""
    start = time.perf_counter()
    freeze_load(NUI_EMBEDDING.read_text(encoding="utf-8"), base_dir=NUI_EMBEDDING.parent)
    assert time.perf_counter() - start < 1.0
