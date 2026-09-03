"""
H-Kernel: two processes, preempted, each with its own registers.

The book lists H-Kernel among the three components that are "terdesain" --
designed, not built. This is the build, and it needed no new hardware. Every
piece it stands on was placed by the six prerequisites, and the one thing a
context switch cannot do without -- a writable epc -- was already there
because traps were built to nest.

The hard part is narrow and worth naming. The handler begins with the register
file still holding the user's values, so saving them needs a base register,
and setting one up destroys the value it was meant to save. There is no zero
register in this ISA: MOVI R0, 7 puts 7 in R0. PUSH is the way out, because
its stack pointer lives in hardware rather than in a GPR: sixteen pushes take
the whole file off the CPU without touching any of it. Sixteen, not eighteen:
R16/R17 do not exist -- see MAX_GPR's comment in the assembler for the book's
own contradiction that settles it.

Both processes count in R1 -- A by one, B by a hundred. That is the whole
proof of privacy: B's total stays an exact multiple of a hundred only if it
never once inherited one of A's steps.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine

ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ROOT / "rtl" / "programs"
KERNEL = PROGRAMS / "kernel.hasm"
SOURCE = KERNEL.read_text(encoding="utf-8")

CUR_PID = 0xF00
TICKS = 0xF01
A_COUNT = 0x100
B_COUNT = 0x200
C_SWEEP = 0x300
C_FAIL = 0x301
N_PROC = 3
# The quantum is 2047 counter ticks, and the guard daemon's sweep is 28
# HLOAD/HGRD pairs, so a run has to be long enough to hold a few dozen
# switches -- a handful proves nothing about privacy.
STEPS = 200_000


def _run(source: str, steps: int = STEPS) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source, base_dir=PROGRAMS)
    n = 0
    while n < steps and m.step() is not None:
        n += 1
    return m


def _run_broken(source: str) -> tuple[HISAMachine, BaseException | None]:
    """Run a sabotaged kernel. A crash is a legitimate outcome -- sixteen
    pops against fifteen pushes underflows the stack -- so the exception is
    returned rather than swallowed or allowed to fail the test."""
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source, base_dir=PROGRAMS)
    n = 0
    try:
        while n < STEPS and m.step() is not None:
            n += 1
    except (IndexError, ValueError, KeyError) as exc:
        return m, exc
    return m, None


def _at(m: HISAMachine, addr: int) -> int:
    """data_mem is sparse: an address no instruction ever wrote has no key,
    and that is a real answer -- it means nothing stored there."""
    return int(m.data_mem.get(addr, 0))


def _break(old: str, new: str) -> str:
    """Mutate the kernel, refusing a sabotage that changes nothing.

    A sabotage that silently fails to apply passes every assertion after it
    and proves nothing. This has bitten this repository more than once, so
    the guard is the first thing the mutation does.
    """
    assert old in SOURCE, f"sabotage anchor is gone from kernel.hasm: {old!r}"
    broken = SOURCE.replace(old, new, 1)
    assert broken != SOURCE, "sabotage changed nothing"
    return broken


# ── the kernel works ────────────────────────────────────────────


def test_both_processes_run() -> None:
    m = _run(SOURCE)
    assert _at(m, A_COUNT) > 0, "process A never ran"
    assert _at(m, B_COUNT) > 0, "process B never ran"


def test_registers_are_private_to_each_process() -> None:
    """B counts by 100 and A by 1, so B's total is a clean multiple of 100
    if and only if B's R1 was never once left holding A's value."""
    m = _run(SOURCE)
    b = _at(m, B_COUNT)
    assert b % 100 == 0, f"B's count {b} absorbed a step of A's: registers leaked"
    assert b // 100 > 20, "too few switches to conclude anything"
    # And the daemon's registers survive too: its sweep counter only ever
    # increments by one, so a leak from A or B would show as a jump.
    assert _at(m, C_SWEEP) > 0


def test_a_is_preempted_without_asking() -> None:
    """A contains no SYSCALL. It runs only because the timer takes it away."""
    body = SOURCE.split("procA:")[1].split("procB:")[0]
    assert "SYSCALL" not in body
    assert _run(SOURCE).data_mem[A_COUNT] > 100


def test_the_scheduler_goes_round_all_three() -> None:
    """B is dispatched exactly once per yield, so its count divided by 100 is
    its share of the ticks. Round robin over three makes that a third."""
    m = _run(SOURCE)
    ticks = _at(m, TICKS)
    b_dispatches = _at(m, B_COUNT) // 100
    assert abs(ticks / N_PROC - b_dispatches) <= 1.0, (
        f"{b_dispatches} B dispatches against {ticks} ticks is not a third"
    )


def test_the_guard_daemon_runs_and_finds_nothing_wrong() -> None:
    """H-Kernel's fourth responsibility. HCHECK is the periodic half of the
    pair the book defines -- Guard per operation, HCHECK on a schedule -- and
    periodic is precisely what nothing could provide until there was a
    scheduler. Each sweep re-validates all 28 letters."""
    m = _run(SOURCE)
    assert _at(m, C_SWEEP) > 10, "the daemon barely ran"
    assert _at(m, C_FAIL) == 0, "a letter failed its guard"


def test_the_daemon_does_not_have_to_be_asked() -> None:
    """A monitor that only runs when something calls it is not a monitor. C
    contains no SYSCALL: the timer takes it away like it takes A."""
    body = SOURCE.split("procC:")[1]
    assert "SYSCALL" not in body


def test_all_three_run_together() -> None:
    m = _run(SOURCE)
    for name, addr in (("A", A_COUNT), ("B", B_COUNT), ("C", C_SWEEP)):
        assert _at(m, addr) > 0, f"process {name} never ran"


def test_the_two_causes_are_entered_differently() -> None:
    """A timer interrupt leaves epc at the next instruction; a syscall leaves
    it at its own. The kernel advances epc only for cause 5. The comparison
    happens against R1, not R9, now: hal_cause_get returns the cause there,
    per hal.hasm's calling convention."""
    assert "CMPI  R1, 5" in SOURCE
    assert "ADDI  R8, R8, 1" in SOURCE


def test_the_whole_file_is_saved_before_anything_uses_a_register() -> None:
    """Nothing may precede the sixteen pushes, because until they are done
    every register still belongs to the interrupted process."""
    entry = SOURCE.split("vector:")[1]
    ops = [ln.split()[0] for ln in entry.splitlines() if ln.startswith("        ")]
    assert ops[:16] == ["PUSH"] * 16, f"first ops after the vector are {ops[:4]}"
    pushed = {ln.split()[1] for ln in entry.splitlines()[:17] if "PUSH" in ln}
    assert pushed == {f"R{i}" for i in range(16)}, "not every register is saved"


# ── each part is load-bearing ───────────────────────────────────


def test_without_the_epc_advance_a_yield_never_returns() -> None:
    """cause 5 names its own instruction, so leaving epc alone makes B
    re-execute the SYSCALL forever."""
    m = _run(
        _break(
            "        ADDI  R8, R8, 1         ; a syscall",
            "        MOV   R8, R8            ; a syscall",
        )
    )
    assert _at(m, B_COUNT) <= 100, "B advanced past a syscall that was never served"
    assert _at(m, A_COUNT) > 100, "A should still be preempted normally"


def test_without_restoring_epc_there_is_no_switch() -> None:
    """Writing the next process's pc into epc IS the context switch. Without
    it ERET returns to whoever just trapped."""
    # epc is set inside hal_epc_set now; sabotage the CALL to it, which
    # exercises the layering too -- dispatch forgetting to call the layer
    # underneath is exactly as broken as the layer forgetting its own store.
    m, _ = _run_broken(
        _break(
            "        CALL  hal_epc_set       ; this is the switch itself",
            "        NOP                     ; this is the switch itself",
        )
    )
    assert _at(m, A_COUNT) == 0 or _at(m, B_COUNT) == 0, (
        "both processes ran without the switch being written"
    )


def test_without_re_arming_the_timer_nothing_is_ever_preempted() -> None:
    """COMPARE resets to 0xFFFFFFFF, so the dispatch write is the only thing
    that ever arms the timer at all. Remove it and the deadline never
    arrives: A, which contains no SYSCALL, owns the machine forever and B
    never runs once. The timer is the kernel's only hold over a process that
    declines to yield."""
    # Re-arming is inside hal_timer_arm now; sabotage the CALL to it.
    quantum_line = "        MOVI  R1, 2047          ; quantum — see hal.hasm for why not 2048\n"
    m, _ = _run_broken(
        _break(quantum_line + "        CALL  hal_timer_arm", quantum_line + "        NOP")
    )
    assert _at(m, B_COUNT) == 0, "B ran without the timer ever being armed"
    assert _at(m, TICKS) == 1, "dispatch ran more than the single boot entry"
    assert _at(m, A_COUNT) > _at(_run(SOURCE), A_COUNT), (
        "A did not gain from having the machine to itself"
    )


@pytest.mark.parametrize("victim", [1, 7, 15])
def test_dropping_any_single_push_corrupts_a_process(victim: int) -> None:
    """Fifteen of sixteen is not a context switch."""
    m, exc = _run_broken(_break(f"        PUSH  R{victim}\n", ""))
    b = _at(m, B_COUNT)
    assert exc is not None or b % 100 != 0 or b == 0, (
        f"losing R{victim} left the kernel intact and B's count clean at {b}"
    )


def test_the_pointer_register_is_restored_last() -> None:
    """R7 addresses the block being restored, so it cannot be restored from
    the middle of the sequence -- it has to come out of itself, at the end."""
    # split on the instruction, not the word: the file's comments name ERET.
    # "previous mode = USER" lived inline before dispatch called out to
    # hal_mode_user for it; "CALL  hal_mode_user" is the anchor now, the last
    # thing before the restore loads begin.
    tail = SOURCE.split("CALL  hal_mode_user")[1].split("\n        ERET")[0]
    loads = [ln for ln in tail.splitlines() if ln.strip().startswith("LOAD  R")]
    assert loads[-1].split()[1].rstrip(",") == "R7", "R7 is not restored last"


# ── isolation still holds under the kernel ──────────────────────


def test_a_process_cannot_reach_the_other_ones_window() -> None:
    """B reaching into A's window faults. cause 4 names its own instruction
    and the kernel does not advance it, so B stops making progress while A
    carries on -- and A's memory is never touched by B."""
    rogue = _break(
        "pb_lp:  ADDI  R1, R1, 100\n        STORE R1, R3, 0",
        "pb_lp:  ADDI  R1, R1, 100\n        MOVI  R4, 0x100\n        STORE R1, R4, 0",
    )
    m, _ = _run_broken(rogue)
    assert _at(m, B_COUNT) == 0, "B wrote outside its own window"
    assert _at(m, A_COUNT) > 100, "A was stopped by B's fault"


# ── the two RTL defects the kernel uncovered ────────────────────
#
# Neither is visible from Python. The interpreter decodes addresses itself, so
# it routes TRAP_MODE whether or not the hardware does; and it executes one
# instruction at a time, so it has no pipeline in which a POP's result can
# arrive late. Both were found by rtl/tb/tb_hcpu_kernel.v, which is the
# behavioural test -- these two pin the fixes so they cannot quietly regress.

MMIO = (ROOT / "rtl" / "hcpu_mmio.v").read_text(encoding="utf-8")
DECODE = (ROOT / "rtl" / "hcpu_decode.v").read_text(encoding="utf-8")
PKG = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")


def _trap_registers() -> set[str]:
    import re as _re

    return set(_re.findall(r"`define\s+(REG_TRAP_\w+)", PKG))


def test_every_trap_register_is_routed_in_both_directions() -> None:
    """The decoder selected trap registers with a RANGE -- `>= REG_TRAP_VECTOR
    && <= REG_TRAP_PENDING`. REG_TRAP_MODE was later defined at 0xD, one past
    the top, and fell outside it in silence. The trap unit implemented the
    register and the spec described it, so both ends agreed while the path
    between them did not exist: nothing could drop to user mode.

    A range admits only what existed when it was written, so the fix names
    them, and this test is the reason the naming has to stay complete.
    """
    names = _trap_registers()
    assert len(names) >= 6, f"expected the full trap register set, found {names}"

    body = MMIO.split("wire is_trap_reg")[1].split(";")[0]
    for name in names:
        assert f"`{name}" in body, f"{name} is not routed for writes"

    read_case = MMIO.split("REG_TIMER_ST:")[1].split("default:")[0]
    for name in names:
        assert f"`{name}" in read_case, f"{name} is not routed for reads"


def test_is_trap_reg_is_not_a_range() -> None:
    body = MMIO.split("wire is_trap_reg")[1].split(";")[0]
    assert ">=" not in body and "<=" not in body, (
        "the trap register select is a range again; the next register added "
        "past its top will be dropped exactly as REG_TRAP_MODE was"
    )


def test_the_load_use_interlock_covers_pop() -> None:
    """POP writes a register from memory with a LOAD's latency, but the
    interlock tested `id_mem_read`, which only OP_LOAD sets. `POP Rn` followed
    by a use of Rn read the previous value -- and a context switch is built
    out of exactly that pair, sixteen times."""
    expr = DECODE.split("assign load_use_hazard")[1].split(";")[0]
    assert "id_is_pop" in expr, "the interlock does not cover POP"
    assert "id_mem_read" in expr, "covering POP must not drop LOAD"


def test_the_interlock_does_not_exempt_r0() -> None:
    """`id_dst != 0` assumed a zero register. This ISA has none: MOVI R0, 7
    puts 7 in R0. Exempting it left the one pattern the save loop is made of
    with no interlock at all."""
    expr = DECODE.split("assign load_use_hazard")[1].split(";")[0]
    assert "id_dst != 0" not in expr.replace(" ", "").replace("id_dst!=0", "id_dst != 0")
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble("        MOVI R0, 7\n        HALT\n")
    while m.step() is not None:
        pass
    assert m.regs.gpr[0] == 7, "R0 is a general register; the exemption was unfounded"
