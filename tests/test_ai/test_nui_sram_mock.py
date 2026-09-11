"""sram_mock.py: the vendored sky130_sram macros' twin-port protocol
mocked -- every check here reproduces a scenario already run against the
real behavioural Verilog model (rtl/mpw/sky130_sram_macros/
sky130_sram_1kbyte_1rw1r_32x256_8/*.v) via Icarus Verilog directly, not
assumed from its comments.
"""
from __future__ import annotations

import pytest

from hijaiyyah.nui.sram_mock import TwinPortSRAM


def test_dout_is_none_before_any_tick():
    """Reading before a clock has ever ticked is meaningless -- the real
    macro's dout0/dout1 are undefined at power-on too."""
    sram = TwinPortSRAM(depth=256)
    assert sram.dout0 is None
    assert sram.dout1 is None


def test_write_takes_one_full_cycle_to_become_readable():
    """Measured against the real macro: presenting a write on tick N and
    a read of the SAME address on tick N+1 returns the NEW value -- not
    on tick N itself (inputs are registered, one cycle of latency)."""
    sram = TwinPortSRAM(depth=256)
    sram.tick(csb0=0, web0=0, wmask0=0b1111, addr0=5, din0=0xDEADBEEF)
    sram.tick(csb0=0, web0=1, addr0=5)
    assert sram.dout0 == 0xDEADBEEF


def test_reading_the_same_tick_as_the_write_does_not_see_it_yet():
    """The write and a same-tick read of the same address are two
    different port-0 modes (web0 selects one or the other) -- this checks
    the mock does not let a write also populate dout0 out of turn."""
    sram = TwinPortSRAM(depth=256)
    sram.mem[5] = 0x11111111
    sram.tick(csb0=0, web0=0, wmask0=0b1111, addr0=5, din0=0xDEADBEEF)
    assert sram.dout0 is None  # write cycle -- dout0 untouched, not the new value


def test_port1_read_has_the_same_one_cycle_latency_as_port0():
    sram = TwinPortSRAM(depth=256)
    sram.tick(csb0=0, web0=0, wmask0=0b1111, addr0=5, din0=0xCAFEF00D)
    sram.tick(csb1=0, addr1=5)
    assert sram.dout1 == 0xCAFEF00D


def test_write_mask_lane0_only_touches_the_low_byte():
    """Measured directly: wmask0=0b0001 on a word seeded to 0x11223344
    changes only the low byte, landing on 0x112233AA -- the other three
    survive untouched."""
    sram = TwinPortSRAM(depth=256)
    sram.tick(csb0=0, web0=0, wmask0=0b1111, addr0=9, din0=0x11223344)
    sram.tick(csb0=0, web0=0, wmask0=0b0001, addr0=9, din0=0xAAAAAAAA)
    sram.tick(csb0=0, web0=1, addr0=9)
    assert sram.dout0 == 0x112233AA


def test_write_mask_lane2_only_touches_bits_23_16():
    """Measured directly: wmask0=0b0100 on 0x112233AA changes bits
    [23:16] only, landing on 0x119933AA."""
    sram = TwinPortSRAM(depth=256)
    sram.mem[9] = 0x112233AA
    sram.tick(csb0=0, web0=0, wmask0=0b0100, addr0=9, din0=0x99999999)
    sram.tick(csb0=0, web0=1, addr0=9)
    assert sram.dout0 == 0x119933AA


def test_deselected_port_does_not_write_or_read():
    """csb0=1 (deselected, the default) must leave mem untouched even if
    web0/addr0/din0 carry stale write-looking values."""
    sram = TwinPortSRAM(depth=256)
    sram.mem[5] = 0x42
    sram.tick(csb0=1, web0=0, addr0=5, din0=0xFFFFFFFF)
    assert sram.mem[5] == 0x42


def test_byte_back_round_trip_across_multiple_ticks():
    """"Bikin byte back": write four different bytes to four addresses
    (one per clock tick), then read all four back on later ticks, port 0
    and port 1 both -- the round trip the whole mock exists to prove."""
    sram = TwinPortSRAM(depth=256)
    values = [0x01020304, 0x11121314, 0x21222324, 0x31323334]
    for addr, value in enumerate(values):
        sram.tick(csb0=0, web0=0, wmask0=0b1111, addr0=addr, din0=value)

    read_back_port0 = []
    read_back_port1 = []
    for addr in range(len(values)):
        sram.tick(csb0=0, web0=1, addr0=addr, csb1=0, addr1=addr)
        read_back_port0.append(sram.dout0)
        read_back_port1.append(sram.dout1)

    assert read_back_port0 == values
    assert read_back_port1 == values


def test_cycle_counts_every_tick_including_idle_ones():
    sram = TwinPortSRAM(depth=16)
    for _ in range(7):
        sram.tick()
    assert sram.cycle == 7


def test_mem_length_must_match_depth_when_preseeded():
    with pytest.raises(ValueError, match="depth"):
        TwinPortSRAM(depth=256, mem=[0] * 10)
