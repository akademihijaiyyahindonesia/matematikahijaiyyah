"""
HAL: layer 2 of the book's stack, which had no file at all.

Not "designed" -- absent. H-Kernel spoke straight to MMIO, so a second board
did not mean porting the kernel, it meant rewriting it. Every peripheral
address it touched was a literal in the middle of a scheduler.

It needed two things that did not exist a few commits ago. CALL and RET,
because without subroutines a layer can only be pasted, not placed; and an
include directive, because a layer that lives inside the one file it serves is
a section, not a layer.

What is checked here is the property, not the prose: kernel.hasm contains no
peripheral literal, hal.hasm contains the ones it needs, and the routines
really do preserve what they promise to preserve.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import AssemblyError, assemble, expand_includes
from hijaiyyah.hisa.machine import HISAMachine

ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ROOT / "rtl" / "programs"
HAL = (PROGRAMS / "hal.hasm").read_text(encoding="utf-8")
KERNEL = (PROGRAMS / "kernel.hasm").read_text(encoding="utf-8")

#: Every peripheral register in the map, by the address a program would write.
PERIPHERAL = re.compile(r"0x[Ff][Ff][0-9A-Fa-f]\b")


def _run(source: str, steps: int = 5000) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(source, base_dir=PROGRAMS)
    n = 0
    while n < steps and m.step() is not None:
        n += 1
    return m


# ── the include mechanism ───────────────────────────────────────


def test_include_splices_the_file_in() -> None:
    lines = expand_includes(['        .include "hal.hasm"'], PROGRAMS)
    assert any("hal_timer_arm:" in ln for ln in lines)


def test_including_twice_is_not_an_error_and_not_a_duplicate() -> None:
    """A shared layer invites being included twice, and pasting it twice would
    collide every label in it. The second include is a no-op, the way a header
    guard behaves, rather than something the caller has to route around."""
    lines = expand_includes(
        ['        .include "hal.hasm"', '        .include "hal.hasm"'], PROGRAMS
    )
    assert sum(1 for ln in lines if ln.startswith("hal_timer_arm:")) == 1


def test_include_without_a_directory_is_refused_not_guessed() -> None:
    with pytest.raises(AssemblyError) as exc:
        assemble('        .include "hal.hasm"\n')
    assert "base_dir" in str(exc.value)


def test_a_missing_include_names_the_file() -> None:
    with pytest.raises(AssemblyError) as exc:
        assemble('        .include "nothing_here.hasm"\n', base_dir=PROGRAMS)
    assert "nothing_here.hasm" in str(exc.value)


# ── the property the layer exists for ───────────────────────────


def test_the_kernel_names_no_peripheral_address() -> None:
    """The whole point. If this fails, the layer is decoration."""
    code_only = "\n".join(
        ln.split(";")[0] for ln in KERNEL.splitlines()
    )
    found = PERIPHERAL.findall(code_only)
    assert not found, f"kernel.hasm still reaches the hardware directly: {found}"


def test_the_hal_holds_the_addresses_the_kernel_needs() -> None:
    needed = {"0xFF4", "0xFF5", "0xFF8", "0xFF9", "0xFFA", "0xFFB",
              "0xFFD", "0xFFE", "0xFFF"}
    assert needed <= set(PERIPHERAL.findall(HAL)), (
        f"hal.hasm is missing: {sorted(needed - set(PERIPHERAL.findall(HAL)))}"
    )


def test_the_kernel_calls_the_layer_rather_than_inlining_it() -> None:
    for routine in ("hal_vector_set", "hal_trap_enable", "hal_epc_get",
                    "hal_cause_get", "hal_epc_set", "hal_mode_user",
                    "hal_window_set", "hal_timer_arm"):
        assert f"CALL  {routine}" in KERNEL, f"the kernel stopped using {routine}"
        assert f"{routine}:" in HAL, f"{routine} is not defined in the HAL"


def test_the_include_sits_where_nothing_can_fall_into_it() -> None:
    """procC's loop never exits, so the layer is unreachable by fallthrough --
    but only because it is last."""
    body = KERNEL.split('.include "hal.hasm"')[0]
    assert "procC:" in body and "pc_lp" in body


# ── it keeps its side of the convention ─────────────────────────


@pytest.mark.parametrize(
    "call,setup",
    [
        ("hal_epc_get", ""),
        ("hal_cause_get", ""),
        ("hal_mode_user", ""),
        ("hal_vector_set", "        MOVI  R1, 0\n"),
        ("hal_trap_enable", "        MOVI  R1, 1\n"),
        ("hal_epc_set", "        MOVI  R1, 0\n"),
        ("hal_window_set", "        MOVI  R1, 0\n        MOVI  R2, 16\n"),
        ("hal_timer_arm", "        MOVI  R1, 100\n"),
    ],
)
def test_a_hal_call_preserves_everything_it_says_it_does(call: str, setup: str) -> None:
    """R1, R2 and R12 are the documented casualties. A routine that quietly
    took a fourth would corrupt whichever caller happened to be holding it --
    and the kernel holds R5, R6 and R7 across every one of these."""
    # R16/R17 are not real registers -- see MAX_GPR's comment in the
    # assembler -- so the sentinel set stops at R15.
    marks = {r: 30 + r for r in list(range(3, 12)) + list(range(13, 16))}
    body = "".join(f"        MOVI  R{r}, {v}\n" for r, v in marks.items())
    m = _run(body + setup + f"        CALL  {call}\n        HALT\n"
             '        .include "hal.hasm"\n')
    for reg, value in marks.items():
        assert m.regs.gpr[reg] == value, (
            f"{call} clobbered R{reg}: {m.regs.gpr[reg]} instead of {value}"
        )


def test_timer_arm_sets_a_deadline_ahead_of_now() -> None:
    """An equality, not a threshold: a deadline already gone past is never met
    again, and the timer simply stops."""
    m = _run("        MOVI  R1, 100\n        CALL  hal_timer_arm\n        HALT\n"
             '        .include "hal.hasm"\n')
    counter = m._periph_read(m.REG_COUNTER)
    compare = m._periph_read(m.REG_COMPARE)
    assert compare > counter, f"deadline {compare} is not ahead of {counter}"
