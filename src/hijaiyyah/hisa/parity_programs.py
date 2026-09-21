"""The execution-parity corpus: programs both engines implement, as words.

Moved here from tests/test_hisa/test_execution_parity.py so that the test and
NUI layer 4 (src/hijaiyyah/nui/parity_model.py) run ONE corpus rather than two
copies that could drift apart (R1). The test still owns the comparison; this
module owns only the programs and the encoder they are written in.

Only opcodes both machines implement can appear here. RTL_IMPLEMENTED lists
what the hardware executes; anything outside it would halt the HCPU with
HALT_ERR and prove nothing.
"""

from __future__ import annotations

from typing import Dict, List

from .opcodes import RTL_IMPLEMENTED, OpCode

HREG_COUNT = 16


# ── Assembly helper ──────────────────────────────────────────────

def enc(op: OpCode, dst: int = 0, s1: int = 0, s2: int = 0, imm: int = 0) -> int:
    """Same field layout as `enc` in the Verilog testbenches."""
    assert op in RTL_IMPLEMENTED, f"{op.name} is not implemented by the HCPU"
    return (
        (int(op) << 24)
        | ((dst & 0xF) << 20)
        | ((s1 & 0xF) << 16)
        | ((s2 & 0xF) << 12)
        | (imm & 0xFFF)
    )


# ── Programs ─────────────────────────────────────────────────────
# Letter indices are 1-based, matching the ROM and CodexEntry.index.

BA, SIN, MIM, HAA, WAW = 2, 12, 24, 27, 26
#: The deliberately corrupt ROM entry every guard bench already uses. It fails
#: G4, which is exactly the statement that its residue is negative.
CORRUPT = 31

PROGRAMS: Dict[str, List[int]] = {
    "load_one_letter": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HALT),
    ],
    "load_three_letters": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HLOAD, dst=1, imm=SIN),
        enc(OpCode.HLOAD, dst=3, imm=MIM),
        enc(OpCode.HALT),
    ],
    "guard_a_letter": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HGRD, s1=0),
        enc(OpCode.HALT),
    ],
    "codex_add": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HLOAD, dst=1, imm=SIN),
        enc(OpCode.HCADD, dst=2, s1=0, s2=1),
        enc(OpCode.HALT),
    ],
    "string_integral_bsm": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HLOAD, dst=1, imm=SIN),
        enc(OpCode.HLOAD, dst=3, imm=MIM),
        enc(OpCode.HCADD, dst=2, s1=0, s2=1),
        enc(OpCode.HCADD, dst=2, s1=2, s2=3),
        enc(OpCode.HGRD, s1=2),
        enc(OpCode.HALT),
    ],
    "norm_of_a_letter": [
        enc(OpCode.HLOAD, dst=0, imm=MIM),
        enc(OpCode.HNRM2, dst=5, s1=0),
        enc(OpCode.HALT),
    ],
    "distance_between_letters": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HLOAD, dst=1, imm=SIN),
        enc(OpCode.HDIST, dst=4, s1=0, s2=1),
        enc(OpCode.HALT),
    ],
    "every_letter_loads": [
        *(enc(OpCode.HLOAD, dst=i % HREG_COUNT, imm=i + 1) for i in range(28)),
        enc(OpCode.HALT),
    ],

    # ── CSET: the write half of CGET ────────────────────────────
    # CSET reads the register it writes, which is the part that can diverge:
    # the seventeen components it does not name have to arrive unchanged in
    # both machines, and the byte it does name has to be the same byte.
    "cset_writes_one_component": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.MOVI, dst=1, imm=5),
        enc(OpCode.CSET, dst=0, s1=1, imm=4),
        enc(OpCode.HALT),
    ],
    "cset_then_reads_it_back": [
        enc(OpCode.HLOAD, dst=0, imm=MIM),
        enc(OpCode.MOVI, dst=2, imm=7),
        enc(OpCode.CSET, dst=0, s1=2, imm=17),
        enc(OpCode.CGET, dst=3, s1=0, imm=17),
        enc(OpCode.CGET, dst=4, s1=0, imm=0),
        enc(OpCode.HALT),
    ],
    "cset_past_seventeen_names_nothing": [
        enc(OpCode.HLOAD, dst=1, imm=SIN),
        enc(OpCode.MOVI, dst=4, imm=9),
        enc(OpCode.CSET, dst=1, s1=4, imm=18),
        enc(OpCode.HALT),
    ],
    "cset_takes_the_low_byte": [
        enc(OpCode.MOVI, dst=5, imm=300),
        enc(OpCode.CSET, dst=2, s1=5, imm=2),
        enc(OpCode.HALT),
    ],
    # Two CSETs to the same H-Reg back to back. The second must see what the
    # first wrote, which on hardware means the forwarding bypass rather than
    # the register file -- the write is still two stages away from committing.
    "cset_twice_into_the_same_register": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.MOVI, dst=1, imm=3),
        enc(OpCode.CSET, dst=0, s1=1, imm=1),
        enc(OpCode.CSET, dst=0, s1=1, imm=2),
        enc(OpCode.HALT),
    ],

    # ── The rest of the codex block ─────────────────────────────
    # CEQ's result is a flag, and this harness compares registers, so each
    # equality is read back the way the ISA reads any flag: with a branch that
    # writes one.
    "codex_copy_and_zero": [
        enc(OpCode.HLOAD, dst=0, imm=HAA),
        enc(OpCode.CMOV, dst=2, s1=0),
        enc(OpCode.HLOAD, dst=3, imm=BA),
        enc(OpCode.CZERO, dst=3),
        enc(OpCode.HALT),
    ],
    "codex_equality_sets_zero": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.CMOV, dst=1, s1=0),
        enc(OpCode.MOVI, dst=6, imm=0),
        enc(OpCode.CEQ, s1=0, s2=1),
        enc(OpCode.JNE, imm=2),
        enc(OpCode.MOVI, dst=6, imm=1),
        enc(OpCode.HALT),
    ],
    "codex_inequality_clears_zero": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HLOAD, dst=1, imm=SIN),
        enc(OpCode.MOVI, dst=6, imm=0),
        enc(OpCode.CEQ, s1=0, s2=1),
        enc(OpCode.JNE, imm=2),
        enc(OpCode.MOVI, dst=6, imm=1),
        enc(OpCode.HALT),
    ],
    # Haa and Waw together, because one of them alone cannot see a mistake:
    # Haa's turning is 8, and 8 mod 4 and 8 mod 8 are both 0. Waw's is 5, where
    # the two answers differ.
    "codex_turning_budget_and_residue": [
        enc(OpCode.HLOAD, dst=0, imm=HAA),
        enc(OpCode.CU, dst=1, s1=0),
        enc(OpCode.CRHO, dst=2, s1=0),
        enc(OpCode.CMOD4, dst=3, s1=0),
        enc(OpCode.HLOAD, dst=1, imm=WAW),
        enc(OpCode.CU, dst=4, s1=1),
        enc(OpCode.CRHO, dst=5, s1=1),
        enc(OpCode.CMOD4, dst=6, s1=1),
        enc(OpCode.HALT),
    ],
    # H-ISA v1.1. FLAGS is eight bits and the two machines have to agree about
    # every one of them, including the ones neither interprets -- FWR writes
    # all eight and FRD hands all eight back, which is what lets a context
    # switch return a process what it actually had.
    #
    # The third program is the one that would catch a lazy packing: it writes
    # every low bit, then lets a comparison overwrite exactly two of them (Z
    # and LT) and leave the rest, so the answer is only right if both machines
    # put the sign bit in the same place. They did not agree about that by
    # accident -- hcpu_pkg.vh puts LT at bit 3 while machine.py keeps it in a
    # field named `overflow`, and the packing had to follow the hardware.
    "flags_read_after_compare": [
        enc(OpCode.MOVI, dst=1, imm=0),
        enc(OpCode.CMPI, s1=1, imm=0),
        enc(OpCode.FRD, dst=3),
        enc(OpCode.HALT),
    ],
    "flags_write_then_read": [
        enc(OpCode.MOVI, dst=4, imm=0x0F),
        enc(OpCode.FWR, s1=4),
        enc(OpCode.FRD, dst=5),
        enc(OpCode.HALT),
    ],
    "flags_survive_a_compare": [
        enc(OpCode.MOVI, dst=4, imm=0x0F),
        enc(OpCode.FWR, s1=4),
        enc(OpCode.MOVI, dst=6, imm=7),
        enc(OpCode.CMPI, s1=6, imm=9),
        enc(OpCode.FRD, dst=7),
        enc(OpCode.HALT),
    ],
    # A vector that fails G4 has a NEGATIVE residue, and the two machines have
    # to agree about how a negative lands in a 32-bit register.
    "codex_negative_residue": [
        enc(OpCode.HLOAD, dst=0, imm=CORRUPT),
        enc(OpCode.CU, dst=1, s1=0),
        enc(OpCode.CRHO, dst=2, s1=0),
        enc(OpCode.HGRD, s1=0),
        enc(OpCode.HALT),
    ],

    # ── The twelve opcodes the HVM gained ───────────────────────

    "move_and_immediate": [
        enc(OpCode.MOVI, dst=1, imm=100),
        enc(OpCode.MOVI, dst=2, imm=4095),      # widest 12-bit immediate
        enc(OpCode.MOV, dst=3, s1=2),
        enc(OpCode.NOP),
        enc(OpCode.HALT),
    ],
    "integer_arithmetic": [
        enc(OpCode.MOVI, dst=1, imm=300),
        enc(OpCode.MOVI, dst=2, imm=7),
        enc(OpCode.ADD, dst=3, s1=1, s2=2),
        enc(OpCode.SUB, dst=4, s1=1, s2=2),
        enc(OpCode.MUL, dst=5, s1=1, s2=2),
        enc(OpCode.HALT),
    ],
    "add_immediate_signed": [
        enc(OpCode.MOVI, dst=1, imm=10),
        enc(OpCode.ADDI, dst=2, s1=1, imm=5),
        # 0xFFE is -2 once sign-extended; a zero-extended reading gives 4094.
        enc(OpCode.ADDI, dst=3, s1=1, imm=0xFFE),
        enc(OpCode.HALT),
    ],
    "subtraction_wraps_at_32_bits": [
        enc(OpCode.MOVI, dst=1, imm=1),
        enc(OpCode.MOVI, dst=2, imm=5),
        enc(OpCode.SUB, dst=3, s1=1, s2=2),     # 1 - 5 wraps to 0xFFFFFFFC
        enc(OpCode.HALT),
    ],
    "compare_sets_flags": [
        enc(OpCode.MOVI, dst=1, imm=42),
        enc(OpCode.MOVI, dst=2, imm=42),
        enc(OpCode.CMP, s1=1, s2=2),
        enc(OpCode.HALT),
    ],
    "compare_immediate": [
        enc(OpCode.MOVI, dst=1, imm=9),
        enc(OpCode.CMPI, s1=1, imm=9),
        enc(OpCode.HALT),
    ],
    "store_then_load": [
        enc(OpCode.MOVI, dst=1, imm=1234),
        enc(OpCode.MOVI, dst=2, imm=64),        # base address
        enc(OpCode.NOP),
        enc(OpCode.STORE, s1=1, s2=2, imm=3),   # MEM[R2+3] <- R1
        enc(OpCode.MOVI, dst=1, imm=0),
        enc(OpCode.NOP),
        enc(OpCode.LOAD, dst=5, s1=2, imm=3),   # R5 <- MEM[R2+3]
        enc(OpCode.NOP),
        enc(OpCode.HALT),
    ],
    "backward_branch_loop": [
        # Straight from tb_hcpu_top.v Program 3. Branch targets are
        # PC-relative: 0xFFE is -2, back to the ADDI.
        enc(OpCode.MOVI, dst=0, imm=0),
        enc(OpCode.MOVI, dst=1, imm=3),
        enc(OpCode.ADDI, dst=0, s1=0, imm=1),
        enc(OpCode.CMP, s1=0, s2=1),
        enc(OpCode.JNE, imm=0xFFE),
        enc(OpCode.HALT),
    ],
    "forward_branch_taken": [
        enc(OpCode.MOVI, dst=1, imm=1),
        enc(OpCode.MOVI, dst=2, imm=1),
        enc(OpCode.CMP, s1=1, s2=2),
        enc(OpCode.JEQ, imm=3),                 # skip the next two
        enc(OpCode.MOVI, dst=7, imm=999),       # must not run
        enc(OpCode.MOVI, dst=8, imm=888),       # must not run
        enc(OpCode.MOVI, dst=9, imm=5),
        enc(OpCode.HALT),
    ],
    "branch_on_guard": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HGRD, s1=0),
        enc(OpCode.JGD, imm=2),                 # guard passes, skip one
        enc(OpCode.MOVI, dst=6, imm=111),       # must not run
        enc(OpCode.MOVI, dst=7, imm=222),
        enc(OpCode.HALT),
    ],
    "branch_on_guard_not_taken": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HGRD, s1=0),
        enc(OpCode.JNGD, imm=2),                # guard passes, so no jump
        enc(OpCode.MOVI, dst=6, imm=111),       # must run
        enc(OpCode.HALT),
    ],
    "hisab_pack_and_crc": [
        enc(OpCode.HLOAD, dst=0, imm=BA),
        enc(OpCode.HPACK, dst=1, s1=0),
        enc(OpCode.HCRC, dst=2, s1=0),
        enc(OpCode.HALT),
    ],
    # ── Bitwise and shift ────────────────────────────────────────
    #
    # The prerequisite that was missing until now. Every value below is
    # checked in both engines: an interpreter and a pipeline that disagree
    # about a shift of 33 disagree about the program, so the shift-amount
    # masking and the zero-extended logical immediates are exercised here
    # rather than trusted to two comments that happen to match.
    "bitwise_register": [
        enc(OpCode.MOVI, dst=1, imm=0x0F0),
        enc(OpCode.MOVI, dst=2, imm=0x03C),
        enc(OpCode.AND, dst=3, s1=1, s2=2),
        enc(OpCode.OR,  dst=4, s1=1, s2=2),
        enc(OpCode.XOR, dst=5, s1=1, s2=2),
        enc(OpCode.NOT, dst=6, s1=1),
        enc(OpCode.HALT),
    ],
    "bitwise_shift": [
        enc(OpCode.MOVI, dst=1, imm=0x0F0),
        enc(OpCode.MOVI, dst=2, imm=4),
        enc(OpCode.SHL, dst=3, s1=1, s2=2),
        enc(OpCode.SHR, dst=4, s1=1, s2=2),
        enc(OpCode.SHLI, dst=5, s1=1, imm=8),
        enc(OpCode.SHRI, dst=6, s1=1, imm=4),
        enc(OpCode.HALT),
    ],
    "bitwise_immediate": [
        enc(OpCode.MOVI, dst=1, imm=0x0F0),
        enc(OpCode.ANDI, dst=2, s1=1, imm=0x0FF),
        enc(OpCode.ORI,  dst=3, s1=1, imm=0x00F),
        enc(OpCode.XORI, dst=4, s1=1, imm=0x0FF),
        enc(OpCode.HALT),
    ],
    # Zero- against sign-extension, and it took two attempts to test at all.
    #
    # The immediate must have bit 11 set OR the two extensions agree. That was
    # the first mistake. The second: the *operand* must also carry bits above
    # bit 11, because 0x0F0 & 0xFFFFFFFF and 0x0F0 & 0x00000FFF are the same
    # value. Swapping imm_zext for imm_sext in the RTL passed every parity
    # test twice before this program existed.
    #
    # R1 = ~0 = 0xFFFFFFFF, so ANDI with 0xFFF gives 0x00000FFF zero-extended
    # and 0xFFFFFFFF sign-extended. Nothing subtle survives that.
    "bitwise_immediate_extension": [
        enc(OpCode.MOVI, dst=0, imm=0),
        enc(OpCode.NOT,  dst=1, s1=0),              # R1 = 0xFFFFFFFF
        enc(OpCode.ANDI, dst=2, s1=1, imm=0xFFF),
        enc(OpCode.ANDI, dst=3, s1=1, imm=0x800),
        enc(OpCode.XORI, dst=4, s1=1, imm=0xFFF),
        enc(OpCode.HALT),
    ],
    # ── Memory-mapped I/O ────────────────────────────────────────
    #
    # The top sixteen words of the data space are peripherals in both
    # engines. Only the deterministic registers appear here: the timer's
    # free-running counter counts real clock cycles, and this interpreter
    # does not model the pipeline's timing, so a "parity" check on it would
    # mean one of the two was lying about what it measures.
    "mmio_compare_round_trip": [
        enc(OpCode.MOVI, dst=5, imm=0),
        enc(OpCode.MOVI, dst=6, imm=0x123),
        enc(OpCode.STORE, s1=6, s2=5, imm=0xFF5),   # timer compare
        enc(OpCode.LOAD, dst=1, s1=5, imm=0xFF5),
        enc(OpCode.HALT),
    ],
    "mmio_status_when_idle": [
        enc(OpCode.MOVI, dst=5, imm=0),
        enc(OpCode.LOAD, dst=1, s1=5, imm=0xFF1),   # rx status, nothing sent
        enc(OpCode.LOAD, dst=2, s1=5, imm=0xFF6),   # timer status
        enc(OpCode.HALT),
    ],
    # A peripheral write must not disturb RAM, and RAM below the base must
    # keep working with peripherals present.
    "mmio_does_not_disturb_ram": [
        enc(OpCode.MOVI, dst=5, imm=0),
        enc(OpCode.MOVI, dst=6, imm=0x0AA),
        enc(OpCode.STORE, s1=6, s2=5, imm=0x010),
        enc(OpCode.MOVI, dst=7, imm=0x7FF),
        enc(OpCode.STORE, s1=7, s2=5, imm=0xFF5),
        enc(OpCode.LOAD, dst=1, s1=5, imm=0x010),
        enc(OpCode.HALT),
    ],

    # A shift of 33 must mask to 1 in both engines, not be undefined.
    "shift_overflow": [
        enc(OpCode.MOVI, dst=1, imm=0x0F0),
        enc(OpCode.MOVI, dst=2, imm=33),
        enc(OpCode.SHL, dst=3, s1=1, s2=2),
        enc(OpCode.SHR, dst=4, s1=1, s2=2),
        enc(OpCode.SHLI, dst=5, s1=1, imm=33),
        enc(OpCode.HALT),
    ],

}
