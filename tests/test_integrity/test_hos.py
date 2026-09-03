"""
HOS: heap, a guarded filesystem, and HAR as a kernel-level service.

The book gives HOS four properties Linux and Windows are explicitly said not
to have. Two existed already -- 18-wide alignment (HREG_W = 144 = 18x8) and
the guard daemon (kernel.hasm's process C). This is the other two, and both
ran into the same fact on the way in: the codex instructions -- HLOAD, CGET --
take their ROM index or component number as a compile-time IMMEDIATE, never
from a register. `rom_addr = is_letter ? letter_index : id_imm[...]` and
`calu_index = id_imm` in hcpu_execute.v both say so directly. HLOAD used to
accept a register operand anyway (the parser had a fallback for it) and
silently ignore it; a loop over CGET with a register component index would
have made the same mistake if it had assembled at all. hos_har_get and
hos_fs_write's copy loop are both unrolled -- twenty-eight and eighteen
compile-time cases -- for exactly this reason, the same pattern kernel.hasm's
guard daemon and test_guard.hasm already use.

The other finding on the way in: this ISA has no branch on magnitude. CMP
computes S1-S2 and sets a LT flag, but no opcode ever reads it -- the five
jumps are JMP, JEQ/JNE (on Z), and JGD/JNGD (on G, the GUARD-pass flag HGRD
sets, unrelated to arithmetic). `CMP a,b / JGD label` reads like "branch if
a>b" and branches on the guard flag instead. hos_size_ge is the workaround:
SUB into a real register, SHRI 31 to isolate the sign bit as a logical shift,
XORI to flip the sense, JEQ to close the loop.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine

ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ROOT / "rtl" / "programs"
HOS = (PROGRAMS / "hos.hasm").read_text(encoding="utf-8")

#: The corrupt vector every RTL guard bench already uses (tb_guard.v,
#: the VM's own HLOAD path at index 31). Real, not invented for this file.
CORRUPT_INDEX = 31


def _run(body: str, steps: int = 12_000, init: bool = True) -> HISAMachine:
    prelude = "        CALL  hos_heap_init\n" if init else ""
    src = f"{prelude}{body}\n        HALT\n        .include \"hos.hasm\"\n"
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(src, base_dir=PROGRAMS)
    n = 0
    while n < steps and m.step() is not None:
        n += 1
    return m


def _at(m: HISAMachine, addr: int) -> int:
    return int(m.data_mem.get(addr, 0))


# ── the missing comparison ──────────────────────────────────────


@pytest.mark.parametrize("a,b,want", [(5, 3, 1), (3, 5, 0), (3, 3, 1), (0, 0, 1)])
def test_hos_size_ge(a: int, b: int, want: int) -> None:
    m = _run(
        f"        MOVI  R1, {a}\n        MOVI  R2, {b}\n"
        "        CALL  hos_size_ge\n        MOVI  R5, 0\n        STORE R3, R5, 0x100\n"
    )
    assert _at(m, 0x100) == want, f"{a} >= {b} should be {want}"


def test_jgd_does_not_mean_greater_than() -> None:
    """The defect hos_size_ge exists to route around. G is bit 0 of the
    flags register, the GUARD-pass flag -- not an arithmetic comparison."""
    execute = (ROOT / "rtl" / "hcpu_execute.v").read_text(encoding="utf-8")
    pkg = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
    assert "FLAG_G          0           // GUARD pass" in pkg
    assert "FLAG_LT         3" in pkg
    assert "alu_flags[`FLAG_LT] = alu_result[`XLEN-1]" in execute
    # And nothing decodes a branch on LT: hcpu_pkg.vh's jump opcodes are
    # exactly JMP, JEQ, JNE, JGD, JNGD.
    jumps = {ln.split()[1] for ln in pkg.splitlines() if "`define OP_J" in ln}
    assert jumps == {"OP_JMP", "OP_JEQ", "OP_JNE", "OP_JGD", "OP_JNGD"}


# ── the heap ─────────────────────────────────────────────────────


def test_alloc_returns_a_pointer_past_the_header() -> None:
    m = _run(
        "        MOVI  R1, 5\n        CALL  hos_alloc\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
    )
    assert _at(m, 0x100) == 0xE03  # 0xE01 (arena start) + 2-word header


def test_two_allocations_do_not_overlap() -> None:
    m = _run(
        "        MOVI  R1, 5\n        CALL  hos_alloc\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        MOVI  R1, 5\n        CALL  hos_alloc\n"
        "        STORE R1, R5, 0x101\n"
    )
    p1, p2 = _at(m, 0x100), _at(m, 0x101)
    assert p1 != p2
    assert p2 - p1 >= 5 + 2, "the second block starts inside the first"


def test_free_then_realloc_the_same_size_reuses_the_address() -> None:
    m = _run(
        "        MOVI  R1, 5\n        CALL  hos_alloc\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        CALL  hos_free\n"
        "        MOVI  R1, 5\n        CALL  hos_alloc\n"
        "        STORE R1, R5, 0x101\n"
    )
    assert _at(m, 0x100) == _at(m, 0x101)


def test_double_free_is_refused_not_silently_corrupting() -> None:
    """hos_free checks the block's tag word for the 0xFFFFFFFF in-use
    sentinel before touching the free list. Without the check, a second free
    of the same pointer pushes it onto the list twice -- the same node
    reachable from two places, which the next two allocations would then both
    hand out as if they were distinct blocks."""
    m = _run(
        "        MOVI  R1, 5\n        CALL  hos_alloc\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        CALL  hos_free\n        STORE R1, R5, 0x101\n"
        "        LOAD  R1, R5, 0x100\n        CALL  hos_free\n"
        "        STORE R1, R5, 0x102\n"
    )
    assert _at(m, 0x101) == 1, "the first free should succeed"
    assert _at(m, 0x102) == 0, "the second free of the same pointer must be refused"


def test_out_of_memory_returns_zero_rather_than_a_bad_pointer() -> None:
    m = _run(
        "        MOVI  R1, 200\n        CALL  hos_alloc\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
    )
    assert _at(m, 0x100) == 0, "the arena is 125 payload words; 200 must fail"


def test_a_near_exact_fit_does_not_leave_an_unusable_sliver() -> None:
    """Splitting only happens when the remainder is at least 3 words (a
    2-word header plus something to hold). Ask for everything but 2 words and
    the whole block should be handed over rather than split into a payload
    and a free sliver too small for its own header."""
    m = _run(
        "        MOVI  R1, 123\n        CALL  hos_alloc\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        MOVI  R1, 1\n        CALL  hos_alloc\n"
        "        STORE R1, R5, 0x101\n"
    )
    assert _at(m, 0x100) != 0, "123 of 125 should still succeed"
    assert _at(m, 0x101) == 0, "no sliver was left to satisfy a second request"


def test_freeing_a_pointer_hos_never_allocated_is_refused() -> None:
    """An address inside the OS-reserved region but never returned by
    hos_alloc has an unpredictable tag word; refusing anything that is not
    exactly the in-use sentinel is what makes this safe rather than lucky."""
    m = _run(
        "        MOVI  R1, 0xE50\n        CALL  hos_free\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
    )
    assert _at(m, 0x100) == 0


# ── HFS: guard-on-write ─────────────────────────────────────────


def test_a_canonical_letter_writes_and_reads_back_byte_for_byte() -> None:
    m = _run(
        "        HLOAD H0, 4\n        MOVI  R1, 0\n        CALL  hos_fs_write\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        MOVI  R1, 0\n        CALL  hos_fs_read\n"
        "        STORE R1, R5, 0x101\n        STORE R2, R5, 0x102\n"
    )
    assert _at(m, 0x100) == 1, "the write should succeed"
    assert _at(m, 0x101) == 1, "the read should find the file"
    ptr = _at(m, 0x102)
    stored = [_at(m, ptr + i) for i in range(18)]
    assert stored == list(MASTER_TABLE.all_entries()[3].vector)


def test_a_corrupt_vector_is_refused_and_never_persisted() -> None:
    """The whole feature. HLOAD H0, 31 is the same corrupt test vector every
    RTL guard bench already uses -- not invented for this test."""
    m = _run(
        f"        HLOAD H0, {CORRUPT_INDEX}\n        MOVI  R1, 3\n        CALL  hos_fs_write\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        MOVI  R1, 3\n        CALL  hos_fs_read\n"
        "        STORE R1, R5, 0x101\n"
    )
    assert _at(m, 0x100) == 0, "the write must be refused"
    assert _at(m, 0x101) == 0, "nothing should have been persisted to file 3"


def test_reading_an_empty_slot_reports_not_found() -> None:
    m = _run(
        "        MOVI  R1, 5\n        CALL  hos_fs_read\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n        STORE R2, R5, 0x101\n"
    )
    assert _at(m, 0x100) == 0
    assert _at(m, 0x101) == 0, "no heap pointer should be handed out for a miss"


def test_rewriting_the_same_file_reuses_its_slot_rather_than_leaking() -> None:
    m = _run(
        "        HLOAD H0, 1\n        MOVI  R1, 0\n        CALL  hos_fs_write\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        MOVI  R1, 0\n        CALL  hos_fs_read\n"
        "        STORE R2, R5, 0x101\n"
        "        HLOAD H0, 2\n        MOVI  R1, 0\n        CALL  hos_fs_write\n"
        "        STORE R1, R5, 0x102\n"
        "        MOVI  R1, 0\n        CALL  hos_fs_read\n"
        "        STORE R2, R5, 0x103\n"
    )
    assert _at(m, 0x100) == 1 and _at(m, 0x102) == 1
    assert _at(m, 0x101) == _at(m, 0x103), (
        "the second write should reuse file 0's existing heap block, not leak a new one"
    )
    ptr = _at(m, 0x103)
    stored = [_at(m, ptr + i) for i in range(18)]
    assert stored == list(MASTER_TABLE.all_entries()[1].vector), (
        "the reused slot should hold letter 2 now"
    )


@pytest.mark.parametrize("letter_index", [1, 5, 14, 28])
def test_every_sampled_letter_round_trips(letter_index: int) -> None:
    m = _run(
        f"        HLOAD H0, {letter_index}\n        MOVI  R1, 1\n        CALL  hos_fs_write\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
        "        MOVI  R1, 1\n        CALL  hos_fs_read\n"
        "        STORE R2, R5, 0x101\n"
    )
    assert _at(m, 0x100) == 1
    ptr = _at(m, 0x101)
    stored = [_at(m, ptr + i) for i in range(18)]
    assert stored == list(MASTER_TABLE.all_entries()[letter_index - 1].vector)


def test_no_cset_means_no_h_register_reconstruction() -> None:
    """The read path's real limit, stated where the routine is defined:
    there is no opcode that writes a GPR value into an H-Reg component, so
    hos_fs_read can only hand back raw words, never a live H-Reg."""
    from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

    names = {o.name for o in OpCode}
    assert "CSET" not in names
    assert OpCode.CGET in RTL_IMPLEMENTED
    assert "there is no CSET" in HOS


# ── HAR ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("index", [1, 4, 10, 28])
def test_har_get_returns_the_canonical_vector(index: int) -> None:
    m = _run(
        f"        MOVI  R1, {index}\n        CALL  hos_har_get\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
    )
    assert _at(m, 0x100) == 1
    entry = MASTER_TABLE.all_entries()[index - 1]
    m2 = _run(
        f"        MOVI  R1, {index}\n        CALL  hos_har_get\n"
        "        CGET  R2, H0, 0\n        MOVI  R5, 0\n        STORE R2, R5, 0x100\n"
    )
    assert _at(m2, 0x100) == entry.vector[0]


@pytest.mark.parametrize("index", [0, 29, 99])
def test_har_get_refuses_out_of_range(index: int) -> None:
    m = _run(
        f"        MOVI  R1, {index}\n        CALL  hos_har_get\n"
        "        MOVI  R5, 0\n        STORE R1, R5, 0x100\n"
    )
    assert _at(m, 0x100) == 0


def test_har_service_is_unrolled_not_register_indexed() -> None:
    """HLOAD H0, Rn used to assemble and silently always load ROM index 0.
    The assembler refuses it now; this pins that hos_har_get never regresses
    into the pattern that made it necessary in the first place."""
    body = HOS.split("hos_har_get:")[1].split(".include")[0]
    # Labels sit inline with the instruction (`har_1:  HLOAD H0, 1`), so
    # split each line into its label and body rather than requiring HLOAD
    # to open the line.
    hloads = [ln for ln in body.splitlines() if "HLOAD" in ln.split(";")[0]]
    assert len(hloads) == 28
    for ln in hloads:
        operand = ln.split(",", 1)[1].strip()
        assert operand.isdigit(), f"a register-operand HLOAD crept back in: {ln!r}"


# ── the layer sits on HAL, not on peripherals ───────────────────


def test_hos_names_no_peripheral_address() -> None:
    import re

    peripheral = re.compile(r"0x[Ff][Ff][0-9A-Fa-f]\b")
    code_only = "\n".join(ln.split(";")[0] for ln in HOS.splitlines())
    found = peripheral.findall(code_only)
    assert not found, f"hos.hasm reaches the hardware directly: {found}"
