"""
H-ISA Machine: fetch-decode-execute cycle.

Bab III §3.30: HVM — Hybit Virtual Machine
  - 16 H-registers (R0–R15), each holding one 18D hybit
  - Hybit Engine: native operations (HCADD, HGRD, HPROJ, HDCMP, HEXMT)
  - Guard System: per-operation validation G1–G4, T1–T2
  - HCHECK: periodic integrity monitor
  - GUARD_STRICT mode: every HCADD auto-checks guard
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..core.exomatrix import build_exomatrix
from ..core.guards import compute_U, full_guard_check, guard_check
from ..core.master_table import MasterTable
from .opcodes import InstructionWord, OpCode
from .registers import HREG_COUNT, RegisterFile

#: The HCPU ROM carries a twenty-ninth entry used only for negative testing.
#: hcpu_rom.v index 31: Θ̂ = 1 with Qc = 2 and A_Q = 2, so U = 8 and
#: ρ = 1 − 8 = −7. It fails G4 and only G4 — the sum-checks and the
#: topological guards all pass, so a failure isolates the one guard that is a
#: cross-constraint rather than a checksum.
ROM_TEST_INDEX = 31
ROM_TEST_VECTOR = (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 2, 0)



@dataclass
class TraceEntry:
    """One line in the execution trace."""

    cycle: int
    description: str


class HISAMachine:
    """
    H-ISA Virtual Machine (HVM).

    Bab III §3.30 — 5 components:
      1. Loader: parse bytecode, setup memory
      2. Interpreter: fetch-decode-execute loop
      3. Hybit Engine: native hybit operations
      4. Guard System: per-operation G1–G4, T1–T2
      5. HCHECK: periodic integrity monitor
    """

    def __init__(
        self,
        table: MasterTable,
        *,
        guard_strict: bool = False,
        hcheck_interval: int = 100,
    ) -> None:
        self.table = table
        self.regs = RegisterFile()
        self.code: List[int] = []
        # Sparse stand-in for hcpu_dataram: 4096 x 32-bit words, zero-filled.
        self.data_mem: Dict[int, int] = {}

        # Peripheral state, mirroring hcpu_mmio.v. `rx_queue` is what a test
        # or a host feeds in; the pipeline gets its bytes off a wire instead,
        # which is why only the deterministic registers are compared.
        self.rx_queue: List[int] = []
        self.timer_compare: int = 0xFFFFFFFF
        self.timer_expired: bool = False

        # Trap state, mirroring hcpu_trap.v. `trap_active` is the whole
        # difficulty: the sources are level-sensitive, so without it the first
        # trap would re-enter every step and the handler's first instruction
        # would never run.
        self.trap_vector: int = 0
        self.trap_epc: int = 0
        self.trap_cause: int = 0
        self.trap_enable: int = 0
        self.trap_active: bool = False
        # Reset lands in supervisor. There is no other way in: entering user
        # mode is a deliberate act -- set `trap_prev` then ERET -- and a
        # machine that came up in user mode could never configure itself,
        # because configuring it means touching the window user mode cannot.
        self.mode: int = self.MODE_SUPER
        self.trap_prev: int = self.MODE_SUPER
        self._priv_fault: bool = False
        # The boot path. Without it a program lives inside the bitstream and
        # changing one means resynthesising -- which makes the board something
        # you flash rather than something you develop on.
        self.imem_waddr: int = 0
        self.trace: List[TraceEntry] = []
        self.cycle: int = 0
        self._halted: bool = False
        self._exit_code: int = 0

        # Bab III §3.25 flags
        self.guard_strict = guard_strict
        self.hcheck_interval = hcheck_interval

    def load_program(self, code: List[int]) -> None:
        """Load bytecode into code memory."""
        self.code = list(code)
        self.data_mem.clear()
        self.regs.pc = 0
        self._halted = False
        self._exit_code = 0

    def step(self) -> Optional[TraceEntry]:
        """Execute one instruction. Returns trace entry or None if done."""
        if self._halted or self.regs.pc >= len(self.code):
            return None

        # HCHECK periodic scan (§3.31)
        if self.hcheck_interval > 0 and self.cycle % self.hcheck_interval == 0 and self.cycle > 0:
            corruption = self._hcheck_scan()
            if corruption:
                entry = TraceEntry(self.cycle, f"HCHECK CORRUPTION: {corruption}")
                self.trace.append(entry)
                self._halted = True
                return entry

        # The timer's own tick. hcpu_timer.v sets `expired` on `counter ==
        # compare` -- a single match, not a level -- and clears it on a write.
        # Modelling it as `>=` here would make the VM re-expire forever after
        # the deadline while the RTL fired once, so a handler correct on one
        # would spin on the other. The MECHANISM matches; the timing cannot,
        # because this counter counts instructions and the RTL's counts clocks.
        if self.cycle == self.timer_compare:
            self.timer_expired = True

        trapped = self._maybe_trap()
        if trapped is not None:
            return trapped

        raw = self.code[self.regs.pc]
        iw = InstructionWord(raw)
        self.regs.pc += 1
        self.cycle += 1

        desc = self._execute(iw)
        entry = TraceEntry(self.cycle, desc)
        self.trace.append(entry)
        return entry

    def run(self) -> List[TraceEntry]:
        """Run until HALT or end of code. Returns all trace entries."""
        result: List[TraceEntry] = []
        while True:
            entry = self.step()
            if entry is None:
                break
            result.append(entry)
        return result

    # ── HCPU arithmetic model ────────────────────────────────────
    # The HCPU is a 32-bit machine with a 12-bit immediate field. Python
    # integers are unbounded, so every result is masked back to 32 bits or the
    # two machines diverge the moment anything overflows.

    XLEN = 32
    _MASK = (1 << 32) - 1
    _SIGN = 1 << 31
    DATA_DEPTH = 4096          # rtl/hcpu_pkg.vh DATA_DEPTH
    DATA_ADDR_MASK = 0xFFF     # DATA_ADDR_W = 12

    @classmethod
    def _u32(cls, value: int) -> int:
        """Wrap to an unsigned 32-bit word, as the RTL does."""
        return value & cls._MASK

    @classmethod
    def _sext12(cls, imm: int) -> int:
        """Sign-extend the 12-bit immediate — `imm_sext` in hcpu_execute.v."""
        return imm - 0x1000 if imm & 0x800 else imm

    def _set_compare_flags(self, difference: int) -> None:
        """
        Flags from a comparison, as hcpu_execute.v sets them: Z from the
        32-bit result being zero, LT from its sign bit. The overflow flag is
        left alone — the RTL does not touch it here either.
        """
        result = self._u32(difference)
        self.regs.sr.zero = result == 0
        self.regs.sr.overflow = bool(result & self._SIGN)

    # ── Memory-mapped I/O ────────────────────────────────────────
    #
    # The top sixteen words of the data space are peripherals, exactly as
    # hcpu_mmio.v decodes them. Modelling them here is not optional: without
    # it a `LOAD` from 0xFF4 reads RAM in this interpreter and the timer in
    # the pipeline, and the two engines quietly disagree about what a program
    # does.
    #
    # **What can and cannot be checked in parity.** The compare register and
    # the status words are deterministic and are compared. The free-running
    # counter is not: it counts real clock cycles, and this interpreter does
    # not model the pipeline's timing. Reporting a counter here that "agrees"
    # with the RTL would mean one of the two was lying.

    PERIPH_BASE = 0xFF0

    REG_RX_DATA = 0x0
    REG_RX_STATUS = 0x1
    REG_TX_STATUS = 0x2
    REG_COUNTER = 0x4
    REG_COMPARE = 0x5
    REG_TIMER_STATUS = 0x6
    REG_TRAP_VECTOR = 0x8
    REG_TRAP_EPC = 0x9
    REG_TRAP_CAUSE = 0xA
    REG_TRAP_ENABLE = 0xB
    REG_TRAP_PENDING = 0xC
    REG_TRAP_MODE = 0xD
    CODE_DEPTH = 4096
    REG_IMEM_ADDR = 0x3
    REG_IMEM_DATA = 0x7

    # Trap causes. One bit each in ENABLE and PENDING; CAUSE holds the index.
    TRAP_TIMER = 0
    TRAP_UART_RX = 1
    TRAP_ILLEGAL = 2
    TRAP_PRIV = 3
    TRAP_CAUSES = 4
    TRAP_MASK_W = 8

    MODE_USER = 0
    MODE_SUPER = 1

    # Exceptions ignore the enable mask; interrupts obey it. A maskable
    # protection is not a protection: user code would clear one bit and the
    # privilege check would stop firing.
    NONMASKABLE = 1 << TRAP_PRIV

    def _mem_read(self, addr: int) -> int:
        masked = addr & self.DATA_ADDR_MASK
        if masked >= self.PERIPH_BASE:
            if self.mode == self.MODE_USER:
                # Suppressed, not performed and undone. A read of RX_DATA
                # consumes the byte, so letting it through would destroy state
                # the handler is about to be told did not happen.
                self._priv_fault = True
                return 0
            return self._periph_read(masked & 0xF)
        return self.data_mem.get(masked, 0)

    def _mem_write(self, addr: int, value: int) -> None:
        masked = addr & self.DATA_ADDR_MASK
        if masked >= self.PERIPH_BASE:
            if self.mode == self.MODE_USER:
                self._priv_fault = True
                return
            self._periph_write(masked & 0xF, self._u32(value))
            return
        self.data_mem[masked] = self._u32(value)

    def _periph_read(self, reg: int) -> int:
        if reg == self.REG_RX_DATA:
            byte = self.rx_queue.pop(0) if self.rx_queue else 0
            return byte
        if reg == self.REG_RX_STATUS:
            return 1 if self.rx_queue else 0
        if reg == self.REG_TX_STATUS:
            return 0                     # this interpreter never stalls on TX
        if reg == self.REG_COUNTER:
            return self._u32(self.cycle)
        if reg == self.REG_COMPARE:
            return self.timer_compare
        if reg == self.REG_TIMER_STATUS:
            return 1 if self.timer_expired else 0
        if reg == self.REG_TRAP_VECTOR:
            return self.trap_vector
        if reg == self.REG_TRAP_EPC:
            return self.trap_epc
        if reg == self.REG_TRAP_CAUSE:
            return self.trap_cause
        if reg == self.REG_TRAP_ENABLE:
            return self.trap_enable
        if reg == self.REG_TRAP_PENDING:
            return self._trap_pending()
        if reg == self.REG_TRAP_MODE:
            return (self.trap_prev << 1) | self.mode
        if reg == self.REG_IMEM_ADDR:
            return self.imem_waddr
        return 0

    def _periph_write(self, reg: int, value: int) -> None:
        if reg == self.REG_COMPARE:
            self.timer_compare = value
            self.timer_expired = False
        elif reg == self.REG_TIMER_STATUS:
            self.timer_expired = False
        elif reg == self.REG_TRAP_VECTOR:
            self.trap_vector = value
        elif reg == self.REG_TRAP_EPC:
            self.trap_epc = value
        elif reg == self.REG_TRAP_ENABLE:
            self.trap_enable = value & ((1 << self.TRAP_MASK_W) - 1)
        elif reg == self.REG_IMEM_ADDR:
            self.imem_waddr = value & (self.CODE_DEPTH - 1)
        elif reg == self.REG_IMEM_DATA:
            # One store per word: the address advances on its own. A loader
            # that had to write the address each time would spend two
            # instructions per word, and it has to fit in front of what it
            # loads.
            while len(self.code) <= self.imem_waddr:
                self.code.append(0)
            self.code[self.imem_waddr] = value
            self.imem_waddr = (self.imem_waddr + 1) & (self.CODE_DEPTH - 1)
        elif reg == self.REG_TRAP_MODE:
            # Bit 1 only. Bit 0 is the current mode and is read-only: if it
            # were writable, dropping privilege and raising it again would be
            # the same instruction.
            self.trap_prev = (value >> 1) & 1
        # CAUSE and PENDING are read-only, in the RTL and here.

    def _trap_pending(self) -> int:
        """The raw source bits, masked or not — same as the RTL's `pending`."""
        bits = 0
        if self.timer_expired:
            bits |= 1 << self.TRAP_TIMER
        if self.rx_queue:
            bits |= 1 << self.TRAP_UART_RX
        if self._priv_fault:
            bits |= 1 << self.TRAP_PRIV
        # TRAP_ILLEGAL is defined but nothing raises it, in the RTL or here.
        return bits

    def _maybe_trap(self) -> Optional[TraceEntry]:
        """Enter a trap before fetching, if one is armed and none is running.

        Priority is the lowest set index, fixed, because two causes arriving
        together must resolve the same way every time or the machine is not
        deterministic.
        """
        if self.trap_active:
            return None
        pending = self._trap_pending()
        armed = (pending & self.trap_enable) | (pending & self.NONMASKABLE)
        if not armed:
            return None
        cause = (armed & -armed).bit_length() - 1
        # An exception names the instruction that caused it -- which has
        # already advanced the PC -- while an interrupt returns to the
        # instruction that has not run yet.
        self.trap_epc = (self.regs.pc - 1) if cause == self.TRAP_PRIV else self.regs.pc
        self.trap_cause = cause
        self.trap_active = True
        self._priv_fault = False
        self.imem_waddr = 0
        self.trap_prev = self.mode
        self.mode = self.MODE_SUPER
        self.regs.pc = self.trap_vector
        self.cycle += 1
        entry = TraceEntry(
            self.cycle, f"TRAP {cause} → {self.trap_vector} (epc={self.trap_epc})")
        self.trace.append(entry)
        return entry

    def _execute(self, iw: InstructionWord) -> str:
        """Execute a decoded instruction. Returns description string."""
        op = iw.opcode
        dst = iw.dst % HREG_COUNT
        s1 = iw.src1 % HREG_COUNT
        s2 = iw.src2 % HREG_COUNT
        imm = iw.imm
        # The PC has already advanced past this instruction; branches are
        # resolved against the instruction's own address, as `id_pc` is in the
        # RTL.
        own_pc = self.regs.pc - 1

        entries = self.table.all_entries()

        # ── HLOAD (CLOAD): load letter into H-register ──────────
        # IMM is a 1-based letter index, 1..28, matching the Master Table's own
        # numbering (CodexEntry.index = i + 1) and the HCPU ROM, whose address
        # port is documented as "letter index (1-28)" and reports valid = 0 for
        # address 0. Indexing `entries` directly with IMM was off by one, so
        # HLOAD H0, #2 loaded Ba on hardware and Ta here — silently, since every
        # canonical letter passes the guards.
        if op == OpCode.HLOAD:
            if 1 <= imm <= len(entries):
                entry = entries[imm - 1]
                self.regs.hreg[dst] = list(entry.vector)
                return f"HLOAD H{dst} ← {entry.char} ({entry.name}) [idx={imm}]"

            if imm == ROM_TEST_INDEX:
                self.regs.hreg[dst] = list(ROM_TEST_VECTOR)
                return f"HLOAD H{dst} ← corrupt test vector [idx={imm}]"

            # An index naming no entry used to leave the register holding
            # zeros, which is the monoid identity and passes every guard. So
            # `HLOAD H0, #31` followed by `HGRD H0` reported PASS here and
            # FAIL on the HCPU, whose ROM carries a deliberately corrupt
            # vector at that address. Same program, opposite answer, and no
            # parity test used the index.
            self.regs.hreg[dst] = [0] * 18
            self._halted = True
            self._exit_code = 1
            return f"HLOAD H{dst} ← index {imm} names no entry — HALT_ERR"

        # ── HCADD (CADD): H[dst] = H[s1] + H[s2] ──────────────
        if op == OpCode.HCADD:
            a = self.regs.hreg[s1]
            b = self.regs.hreg[s2]
            result = [a[i] + b[i] for i in range(18)]

            # GUARD_STRICT mode (§3.25 bit 2)
            if self.guard_strict:
                if not guard_check(result):
                    self.regs.sr.guard_pass = False
                    return f"HCADD H{dst} = H{s1} + H{s2} → GUARD_FAIL (strict mode)"
                self.regs.sr.guard_pass = True

            self.regs.hreg[dst] = result
            return f"HCADD H{dst} = H{s1} + H{s2}"

        # ── HGRD (VCHK): guard check ────────────────────────────
        if op == OpCode.HGRD:
            h = self.regs.hreg[s1]
            ok = guard_check(h)
            self.regs.sr.guard_pass = ok
            return f"HGRD H{s1} → {'PASS ✓' if ok else 'FAIL ✗'}"

        # ── HPROJ: projection to layer (software only, 0x80) ────
        if op == OpCode.HPROJ:
            h = self.regs.hreg[s1]
            layer = imm & 0x3
            r = [0] * 18
            if layer == 0:  # THETA
                r[0] = h[0]
                label = "Θ"
            elif layer == 1:  # N
                r[1], r[2], r[3] = h[1], h[2], h[3]
                label = "N"
            elif layer == 2:  # K
                for k in range(4, 9):
                    r[k] = h[k]
                label = "K"
            else:  # Q
                for k in range(9, 14):
                    r[k] = h[k]
                label = "Q"
            self.regs.hreg[dst] = r
            return f"HPROJ H{dst} = Π_{label}(H{s1})"

        # ── HDCMP: decompose Θ̂ → (U, ρ) ────────────────────────
        if op == OpCode.HDCMP:
            h = self.regs.hreg[s1]
            U = compute_U(h)
            rho = h[0] - U
            # Two results, so this one takes a register pair: DST and DST+1.
            second = (dst + 1) % len(self.regs.gpr)
            self.regs.gpr[dst] = U
            self.regs.gpr[second] = rho
            return f"HDCMP H{s1}: U={U}, ρ={rho} → GPR[{dst}],GPR[{second}]"

        # ── HNRM2: squared norm ─────────────────────────────────
        # Scalar results go to GPR[DST], not GPR[0]. Writing GPR[0] ignored the
        # instruction's own destination field: on the HCPU, `HNRM2 R5, H0` puts
        # the norm in R5, so the two machines left the answer in different
        # registers while both reporting success.
        if op == OpCode.HNRM2:
            h = self.regs.hreg[s1]
            n2 = sum(x * x for x in h[:14])
            self.regs.gpr[dst] = n2
            return f"HNRM2 GPR[{dst}] = ‖H{s1}‖² = {n2}"

        # ── CGET: read one codex component ─────────────────────
        # The projection Bab III §IIIH.3.1.1 names for the Hybit Engine and
        # §IIIM.3.1 never encoded. Without it nothing can read Θ̂, N, K or Q
        # out of an H-Reg: H-ISA has no AND, no shift and no DIV, and HPACK
        # cannot be unpacked.
        if op == OpCode.CGET:
            if imm > 17:
                self.regs.gpr[dst] = 0
                return f"CGET GPR[{dst}] = 0 (index {imm} names no component)"
            value = self.regs.hreg[s1][imm]
            self.regs.gpr[dst] = value
            return f"CGET GPR[{dst}] = H{s1}[{imm}] = {value}"

        # ── HDIST: squared Euclidean distance ───────────────────
        if op == OpCode.HDIST:
            a = self.regs.hreg[s1]
            b = self.regs.hreg[s2]
            d2 = sum((a[i] - b[i]) ** 2 for i in range(14))
            self.regs.gpr[dst] = d2
            return f"HDIST GPR[{dst}] = ‖H{s1} - H{s2}‖² = {d2}"

        # ── HEXMT: build exomatrix ──────────────────────────────
        if op == OpCode.HEXMT:
            h = self.regs.hreg[s1]
            exo = build_exomatrix(h)
            # Store exomatrix rows in consecutive registers dst..dst+4
            for row_idx in range(5):
                reg_idx = (dst + row_idx) % HREG_COUNT
                r = [0] * 18
                for col_idx in range(5):
                    r[col_idx] = exo[row_idx][col_idx]
                self.regs.hreg[reg_idx] = r
            return f"HEXMT H{dst}..H{(dst+4)%HREG_COUNT} ← Exo(H{s1})"

        # ── HCHK: runtime integrity check ───────────────────────
        if op == OpCode.HCHK:
            h = self.regs.hreg[s1]
            detail = full_guard_check(h)
            if detail["all_pass"]:
                return f"HCHK H{s1} → INTEGRITY OK"
            failed = [k for k, v in detail.items() if k != "all_pass" and not v]
            return f"HCHK H{s1} → INTEGRITY FAIL: {failed}"

        # ── CSUB: H[dst] = H[s1] - H[s2] (14D) ────────────────
        if op == OpCode.CSUB:
            a = self.regs.hreg[s1]
            b = self.regs.hreg[s2]
            self.regs.hreg[dst] = [a[i] - b[i] for i in range(14)] + [0] * 4
            return f"CSUB H{dst} = H{s1} - H{s2} (14D)"

        # ── VMOV: copy register ─────────────────────────────────
        if op == OpCode.VMOV:
            self.regs.hreg[dst] = list(self.regs.hreg[s1])
            return f"VMOV H{dst} = H{s1}"

        # ── PRINT: output register ──────────────────────────────
        if op == OpCode.PRINT:
            h = self.regs.hreg[dst]
            return f"PRINT H{dst} = ({', '.join(str(x) for x in h)})"

        # ── HALT: stop execution ────────────────────────────────
        if op == OpCode.HALT:
            if self.mode == self.MODE_USER:
                self._priv_fault = True
                return "HALT → privilege fault (user mode)"
            self._halted = True
            self._exit_code = imm
            return f"HALT — execution stopped (code={imm})"

        # ── ERET: return from a trap ────────────────────────────
        # Clearing the latch and redirecting have to happen together. As a
        # load and a jump they could not: a trap arriving between the two
        # would be taken with the old epc still in place, and the first
        # handler's return address would be gone.
        if op == OpCode.ERET:
            if self.mode == self.MODE_USER:
                # A faulting ERET must not also return, or user code escapes by
                # executing one and letting the fault be handled afterwards.
                self._priv_fault = True
                return "ERET → privilege fault (user mode)"
            self.regs.pc = self.trap_epc
            self.trap_active = False
            self.mode = self.trap_prev
            return f"ERET → {self.trap_epc}"

        # ── Legacy VPROJ_T / VPROJ_N / VPROJ_K / VPROJ_Q ───────
        if op == OpCode.VPROJ_T:
            h = self.regs.hreg[s1]
            self.regs.hreg[dst] = [h[0]] + [0] * 17
            return f"VPROJ_T H{dst} = Π_Θ(H{s1})"

        if op == OpCode.VPROJ_N:
            h = self.regs.hreg[s1]
            r = [0] * 18
            r[1], r[2], r[3] = h[1], h[2], h[3]
            self.regs.hreg[dst] = r
            return f"VPROJ_N H{dst} = Π_N(H{s1})"

        if op == OpCode.VPROJ_K:
            h = self.regs.hreg[s1]
            r = [0] * 18
            for k in range(4, 9):
                r[k] = h[k]
            self.regs.hreg[dst] = r
            return f"VPROJ_K H{dst} = Π_K(H{s1})"

        if op == OpCode.VPROJ_Q:
            h = self.regs.hreg[s1]
            r = [0] * 18
            for k in range(9, 14):
                r[k] = h[k]
            self.regs.hreg[dst] = r
            return f"VPROJ_Q H{dst} = Π_Q(H{s1})"

        # ── Integer ops ─────────────────────────────────────────
        # ADD / SUB / MUL / CMP — IADD, ISUB, IMUL and ICMP are aliases of
        # these. Results wrap at 32 bits: Python integers do not, so without
        # the mask a subtraction below zero or a large product left this
        # machine holding a value the HCPU could not represent.
        if op == OpCode.ADD:
            self.regs.gpr[dst] = self._u32(self.regs.gpr[s1] + self.regs.gpr[s2])
            return f"ADD R{dst} = R{s1} + R{s2} = {self.regs.gpr[dst]}"

        # ── Bitwise and shift ────────────────────────────────────
        #
        # Shift amounts are masked to 5 bits and logical immediates are
        # zero-extended. Both are stated in opcodes.py and both must match
        # hcpu_execute.v exactly — an interpreter and a pipeline that disagree
        # about a shift of 33 disagree about the program.
        if op == OpCode.AND:
            self.regs.gpr[dst] = self.regs.gpr[s1] & self.regs.gpr[s2]
            return f"AND R{dst} = R{s1} & R{s2} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.OR:
            self.regs.gpr[dst] = self.regs.gpr[s1] | self.regs.gpr[s2]
            return f"OR R{dst} = R{s1} | R{s2} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.XOR:
            self.regs.gpr[dst] = self.regs.gpr[s1] ^ self.regs.gpr[s2]
            return f"XOR R{dst} = R{s1} ^ R{s2} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.NOT:
            self.regs.gpr[dst] = self._u32(~self.regs.gpr[s1])
            return f"NOT R{dst} = ~R{s1} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.SHL:
            shift = self.regs.gpr[s2] & 0x1F
            self.regs.gpr[dst] = self._u32(self.regs.gpr[s1] << shift)
            return f"SHL R{dst} = R{s1} << {shift} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.SHR:
            shift = self.regs.gpr[s2] & 0x1F
            self.regs.gpr[dst] = self.regs.gpr[s1] >> shift
            return f"SHR R{dst} = R{s1} >> {shift} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.ANDI:
            self.regs.gpr[dst] = self.regs.gpr[s1] & imm
            return f"ANDI R{dst} = R{s1} & {imm:#x} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.ORI:
            self.regs.gpr[dst] = self.regs.gpr[s1] | imm
            return f"ORI R{dst} = R{s1} | {imm:#x} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.XORI:
            self.regs.gpr[dst] = self.regs.gpr[s1] ^ imm
            return f"XORI R{dst} = R{s1} ^ {imm:#x} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.SHLI:
            shift = imm & 0x1F
            self.regs.gpr[dst] = self._u32(self.regs.gpr[s1] << shift)
            return f"SHLI R{dst} = R{s1} << {shift} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.SHRI:
            shift = imm & 0x1F
            self.regs.gpr[dst] = self.regs.gpr[s1] >> shift
            return f"SHRI R{dst} = R{s1} >> {shift} = {self.regs.gpr[dst]:#x}"

        if op == OpCode.SUB:
            self.regs.gpr[dst] = self._u32(self.regs.gpr[s1] - self.regs.gpr[s2])
            return f"SUB R{dst} = R{s1} - R{s2} = {self.regs.gpr[dst]}"

        if op == OpCode.MUL:
            self.regs.gpr[dst] = self._u32(self.regs.gpr[s1] * self.regs.gpr[s2])
            return f"MUL R{dst} = R{s1} * R{s2} = {self.regs.gpr[dst]}"

        if op == OpCode.CMP:
            self._set_compare_flags(self.regs.gpr[s1] - self.regs.gpr[s2])
            return (
                f"CMP R{s1}={self.regs.gpr[s1]} vs R{s2}={self.regs.gpr[s2]} "
                f"→ Z={self.regs.sr.zero}"
            )

        # ── Legacy scalar ops ───────────────────────────────────
        if op == OpCode.VDIST:
            a = self.regs.hreg[s1]
            b = self.regs.hreg[s2]
            d2 = sum((a[i] - b[i]) ** 2 for i in range(14))
            self.regs.gpr[dst] = d2
            return f"VDIST GPR[{dst}] = ‖H{s1} - H{s2}‖² = {d2}"

        if op == OpCode.VRHO:
            h = self.regs.hreg[s1]
            U = compute_U(h)
            rho = h[0] - U
            self.regs.gpr[dst] = rho
            return f"VRHO GPR[{dst}] = ρ(H{s1}) = Θ̂({h[0]}) - U({U}) = {rho}"

        if op == OpCode.VNORM:
            h = self.regs.hreg[s1]
            n2 = sum(x * x for x in h[:14])
            self.regs.gpr[dst] = n2
            return f"VNORM GPR[{dst}] = ‖H{s1}‖² = {n2}"

        if op == OpCode.VDOT:
            a = self.regs.hreg[s1]
            b = self.regs.hreg[s2]
            ip = sum(a[i] * b[i] for i in range(14))
            self.regs.gpr[dst] = ip
            return f"VDOT GPR[{dst}] = ⟨H{s1}, H{s2}⟩ = {ip}"

        # ── Control Flow ────────────────────────────────────────
        if op == OpCode.JMP:
            self.regs.pc = imm
            return f"JMP → {imm}"

        if op == OpCode.JGP:
            if self.regs.sr.guard_pass:
                self.regs.pc = imm
                return f"JGP → {imm} (guard PASS)"
            return "JGP — no jump (guard FAIL)"

        if op == OpCode.JGF:
            if not self.regs.sr.guard_pass:
                self.regs.pc = imm
                return f"JGF → {imm} (guard FAIL)"
            return "JGF — no jump (guard PASS)"

        if op == OpCode.JNP:
            if not self.regs.sr.guard_pass:
                self.regs.pc = imm
                return f"JNP → {imm} (not pass)"
            return "JNP — no jump (pass)"

        # Conditional branches are PC-relative in the RTL —
        # `branch_target = id_pc + imm_sext` — while JMP is absolute. These
        # used to set pc = imm, so `JNE #0xFFE` (the -2 of the RTL's own loop
        # test) jumped to address 4094 here and to PC-2 on the hardware.
        if op == OpCode.JEQ:
            if self.regs.sr.zero:
                self.regs.pc = own_pc + self._sext12(imm)
                return f"JEQ → {self.regs.pc} (equal)"
            return "JEQ — no jump (not equal)"

        if op == OpCode.JNE:
            if not self.regs.sr.zero:
                self.regs.pc = own_pc + self._sext12(imm)
                return f"JNE → {self.regs.pc} (not equal)"
            return "JNE — no jump (equal)"

        if op == OpCode.JGD:
            if self.regs.sr.guard_pass:
                self.regs.pc = own_pc + self._sext12(imm)
                return f"JGD → {self.regs.pc} (guard PASS)"
            return "JGD — no jump (guard FAIL)"

        if op == OpCode.JNGD:
            if not self.regs.sr.guard_pass:
                self.regs.pc = own_pc + self._sext12(imm)
                return f"JNGD → {self.regs.pc} (guard FAIL)"
            return "JNGD — no jump (guard PASS)"

        # ── Subroutine ──────────────────────────────────────────
        if op == OpCode.CALL:
            self.regs.push(self.regs.pc)
            self.regs.pc = imm
            return f"CALL → {imm} (return addr pushed)"

        if op == OpCode.RET:
            ret_addr = self.regs.pop()
            self.regs.pc = ret_addr
            return f"RET → {ret_addr}"

        # ── Stack ───────────────────────────────────────────────
        if op == OpCode.PUSH:
            self.regs.push(self.regs.gpr[s1 % 18])
            return f"PUSH GPR[{s1%18}]"

        if op == OpCode.POP:
            self.regs.gpr[dst % 18] = self.regs.pop()
            return f"POP → GPR[{dst%18}]"

        # ── Integer and data movement (RTL semantics) ───────────
        # hcpu_execute.v: MOVI zero-extends its immediate, ADDI and CMPI
        # sign-extend theirs, and every result wraps at 32 bits.

        if op == OpCode.NOP:
            return "NOP"

        if op == OpCode.MOV:
            self.regs.gpr[dst] = self.regs.gpr[s1]
            return f"MOV R{dst} = R{s1} ({self.regs.gpr[dst]})"

        if op == OpCode.MOVI:
            self.regs.gpr[dst] = imm  # imm_zext
            return f"MOVI R{dst} = {imm}"

        if op == OpCode.ADDI:
            value = self._u32(self.regs.gpr[s1] + self._sext12(imm))
            self.regs.gpr[dst] = value
            return f"ADDI R{dst} = R{s1} + {self._sext12(imm)} = {value}"

        if op == OpCode.CMPI:
            self._set_compare_flags(self.regs.gpr[s1] - self._sext12(imm))
            return f"CMPI R{s1}, {self._sext12(imm)} → Z={self.regs.sr.zero}"

        # ── Data memory ─────────────────────────────────────────
        # LOAD:  addr = GPR[S1] + IMM, DST <- MEM[addr]
        # STORE: addr = GPR[S2] + IMM, MEM[addr] <- GPR[S1]

        if op == OpCode.LOAD:
            addr = self._u32(self.regs.gpr[s1] + self._sext12(imm))
            self.regs.gpr[dst] = self._mem_read(addr)
            return f"LOAD R{dst} = MEM[{addr & self.DATA_ADDR_MASK}]"

        if op == OpCode.STORE:
            addr = self._u32(self.regs.gpr[s2] + self._sext12(imm))
            self._mem_write(addr, self.regs.gpr[s1])
            return f"STORE MEM[{addr & self.DATA_ADDR_MASK}] = R{s1}"

        # ── HISAB serialization ─────────────────────────────────

        if op == OpCode.HPACK:
            from ..hisab.serialize import _compute_guard_status, _nibble_pack

            # Little-endian, matching hcpu_hisab.v and rtl/tb/gen_golden.py.
            # S2 selects the word. Only word 0 used to be reachable, so a
            # nine-byte HISAB frame could never be assembled from the machine.
            packed = _nibble_pack(self.regs.hreg[s1])
            words = [
                int.from_bytes(bytes(packed[0:4]), "little"),
                int.from_bytes(bytes(packed[4:8]), "little"),
                (_compute_guard_status(self.regs.hreg[s1]) << 8) | packed[8],
            ]
            value = words[s2] if s2 <= 2 else 0
            self.regs.gpr[dst] = value
            return f"HPACK R{dst} = word{s2} = 0x{value:08X}"

        if op == OpCode.HCRC:
            from ..hisab.serialize import serialize_letter

            crc = serialize_letter(self.regs.hreg[s1]).digest
            self.regs.gpr[dst] = crc
            return f"HCRC R{dst} = 0x{crc:08X}"

        if op == OpCode.HALT_ERR:
            self._halted = True
            self._exit_code = 1
            return "HALT_ERR — stopped on a faulting instruction"

        # Anything left is not implemented by this machine. The HCPU raises
        # HALT_ERR rather than continuing, and so does this.
        self._halted = True
        self._exit_code = 1
        return f"UNKNOWN opcode 0x{op:02X} — HALT_ERR"

    def _hcheck_scan(self) -> Optional[str]:
        """
        HCHECK: periodic integrity scan of all H-registers.

        §3.31: Detects corruption — bit flip, buffer overflow.
        Scans all registers and validates guards on each.
        """
        for i in range(HREG_COUNT):
            h = self.regs.hreg[i]
            if any(x != 0 for x in h):  # Skip zero registers
                if any(x < 0 for x in h):
                    return f"H{i}: negative component detected"
                # Only check guard on non-zero registers that look like hyperbolic data
                if h[14] != 0 or h[15] != 0 or h[16] != 0:
                    if not guard_check(h):
                        return f"H{i}: guard check failed"
        return None

    def dump_state(self) -> dict:
        """Return full machine state as dict."""
        return {
            "pc": self.regs.pc,
            "cycle": self.cycle,
            "halted": self._halted,
            "exit_code": self._exit_code,
            "gpr": list(self.regs.gpr),
            "hreg": [list(h) for h in self.regs.hreg],
            "sr": {
                "guard": self.regs.sr.guard_pass,
                "zero": self.regs.sr.zero,
                "overflow": self.regs.sr.overflow,
            },
            "stack_depth": len(self.regs.stack),
            "guard_strict": self.guard_strict,
        }

    def reset(self) -> None:
        """Reset machine to initial state."""
        self.regs = RegisterFile()
        self.code = []
        self.trace = []
        self.cycle = 0
        self._halted = False
        self._exit_code = 0

        # Peripheral state, declared in __init__ and only re-set here.
        self.rx_queue = []
        self.timer_compare = 0xFFFFFFFF
        self.timer_expired = False
        self.trap_vector = 0
        self.trap_epc = 0
        self.trap_cause = 0
        self.trap_enable = 0
        self.trap_active = False
        self.mode = self.MODE_SUPER
        self.trap_prev = self.MODE_SUPER
        self._priv_fault = False
