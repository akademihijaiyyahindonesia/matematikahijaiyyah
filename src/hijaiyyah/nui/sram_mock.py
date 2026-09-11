"""Mock of the vendored sky130_sram macros' twin-port protocol -- the same
freeze-mode discipline as nui/freeze.py, applied to a different piece of
silicon: fake the memory macro, run its real synchronous read/write
contract.

"Twin" names what every macro's own port list already is: port 0 is
read-write (clk0/csb0/web0/wmask0/addr0/din0/dout0), port 1 is read-only
(clk1/csb1/addr1/dout1) -- "1rw1r" in every filename under
rtl/mpw/sky130_sram_macros/. Two ports, not invented here.

The contract below is not read off the module's comments -- it is
measured, by compiling the real behavioural model
(rtl/mpw/sky130_sram_macros/sky130_sram_1kbyte_1rw1r_32x256_8/*.v) into
Icarus Verilog and running write-then-read-back sequences directly:

  * inputs are registered on the clock edge they are presented before --
    a write or read only takes effect for the NEXT clock, never the one
    it was presented on (checked: writing addr=5 then immediately trying
    to read addr=5 the same tick returns the OLD contents).
  * write-mask is byte-lane, lane N gates bits [8N+7:8N] of din0 --
    checked directly: wmask0=0b0001 on a seeded word changed only its
    low byte, wmask0=0b0100 changed only bits [23:16], both leaving the
    other three bytes untouched.
  * dout0 during a write cycle is not meaningful (the real macro drives
    it to X) -- this mock leaves it at whatever it last held, documented
    as unreliable, not simulated bit-for-bit as an X value.

One call to tick() is one clock cycle: present this cycle's control and
address lines, and dout0/dout1 come back holding what the real macro
would drive at the START of the next cycle -- one cycle of latency,
matching silicon, not zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

#: NUM_WMASKS in every vendored macro's own Verilog parameter list --
#: four byte lanes over a 32-bit word, not invented here.
WRITE_MASK_LANES = 4
LANE_BITS = 8
FULL_WRITE_MASK = (1 << WRITE_MASK_LANES) - 1  # 0b1111 -- write every lane


@dataclass
class TwinPortSRAM:
    """One sky130_sram_*_1rw1r_* macro, mocked. `depth` words, each
    `width_bits` wide (32 in every vendored macro this project ships).
    dout0/dout1 hold the PREVIOUS tick's read result until the next
    tick() call -- reading them before any tick() is meaningless, the
    same way real dout0/dout1 are undefined before the first clock."""

    depth: int
    width_bits: int = 32
    mem: List[int] = field(default_factory=list)
    dout0: Optional[int] = None
    dout1: Optional[int] = None
    cycle: int = 0

    def __post_init__(self) -> None:
        if not self.mem:
            self.mem = [0] * self.depth
        elif len(self.mem) != self.depth:
            raise ValueError(f"mem has {len(self.mem)} words, depth is {self.depth}")

    def tick(self, *, csb0: int = 1, web0: int = 1, wmask0: int = FULL_WRITE_MASK,
             addr0: int = 0, din0: int = 0, csb1: int = 1, addr1: int = 0) -> "TwinPortSRAM":
        """One clk0/clk1 edge. Active-low chip-select/write-enable,
        matching the real macro exactly: csb0=0 selects port 0, web0=0
        writes (wmask0 gates which byte lanes), web0=1 reads. csb1=0
        selects port 1's read. Returns self so a caller can chain reads
        off the same call that presented the address."""
        self.cycle += 1
        if csb0 == 0 and web0 == 0:
            self.mem[addr0] = self._masked_write(self.mem[addr0], din0, wmask0)
        elif csb0 == 0 and web0 == 1:
            self.dout0 = self.mem[addr0]
        if csb1 == 0:
            self.dout1 = self.mem[addr1]
        return self

    def _masked_write(self, word: int, din: int, wmask: int) -> int:
        for lane in range(WRITE_MASK_LANES):
            if (wmask >> lane) & 1:
                shift = lane * LANE_BITS
                lane_mask = ((1 << LANE_BITS) - 1) << shift
                word = (word & ~lane_mask) | (din & lane_mask)
        return word & ((1 << self.width_bits) - 1)
