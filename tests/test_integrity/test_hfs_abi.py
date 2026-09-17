"""ABI HFS v1 — the precondition that makes a hybit argument survivable.

HFS passes its payload in H0. hos_fs_write takes its vector there and
hos_fs_read returns one there, so a file syscall carries a 144-bit register
across a trap boundary — and the machine protects nothing. Banking the codex
registers in hardware was built and measured at +336 LUT4 for H0 alone, which
this board refuses to place; rtl/programs/hos_hctx.hasm carries those figures.

What ships instead is a software save into a per-process slot, and it is
correct only under one condition:

    No instruction between trap entry and the HFS syscall arms may modify a
    caller H-register.

rtl/programs/shell.hasm satisfies that today by containing no codex
instruction at all. That is the kind of correctness this repository has twice
watched expire quietly — rtl/programs/kernel.hasm holds thirty codex
instructions and sweeps the guard periodically — so it is asserted here rather
than remembered.

The failure this prevents does not look like a failure. A vector read from a
register the handler has since overwritten is still eighteen plausible bytes,
and hos_fs_write commits them without complaint.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ROOT / "rtl" / "programs"
SHELL = PROGRAMS / "shell.hasm"

# Everything that can write a caller-visible H-register. CGET only reads one,
# so it is not here; HGRD sets the GUARD flag from one and writes none.
CODEX_WRITERS = ("HLOAD", "CSET", "CMOV", "CZERO", "HCADD", "CSTORE")


def _instructions(text: str) -> list[tuple[int, str]]:
    """Line number and mnemonic for every instruction, comments stripped.

    Comments carry these mnemonics constantly -- the file explains what it
    does not do -- so a naive substring search would fail on prose and pass on
    code, which is the wrong way round.
    """
    out: list[tuple[int, str]] = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        body = line.split(":", 1)[1] if re.match(r"^\w+:", line) else line
        m = re.match(r"\s*\.?(\w+)", body)
        if m:
            out.append((n, m.group(1).upper()))
    return out


def test_the_shell_handler_never_writes_a_codex_register() -> None:
    """The precondition itself, read off the file that has to satisfy it."""
    text = SHELL.read_text(encoding="utf-8")
    # The includes bring in hos.hasm, whose HFS routines legitimately write
    # H-registers -- they are the callee, not the path to it. Only this file's
    # own body is the trap path.
    own = text.split('.include', 1)[0]
    offenders = [(n, op) for n, op in _instructions(own) if op in CODEX_WRITERS]
    assert not offenders, (
        "ABI HFS v1: shell.hasm's trap path now modifies a codex register at "
        f"{offenders}. The HFS syscall arms save the CALLER's H0 into its "
        "per-process slot, and anything writing an H-register before them "
        "destroys the argument they are meant to preserve. Either move the "
        "save to trap entry -- 36 instructions on every trap, timer "
        "preemptions included -- or keep this path free of codex writes."
    )


def test_the_hfs_arms_take_their_vector_from_the_slot_not_the_register() -> None:
    """WRITE must read back what it saved, not trust what it was handed.

    The register is correct today precisely because of the test above. This
    one asserts the arm does not DEPEND on that: it saves, reloads, and only
    then calls hos_fs_write. Delete the reload and the arm still passes every
    functional bench, because the register still holds the right value -- it
    just stops being guaranteed to.
    """
    text = SHELL.read_text(encoding="utf-8")
    arm = text.split("sc_fw:", 1)
    assert len(arm) == 2, "shell.hasm no longer has an HFS_WRITE arm"
    body = arm[1].split("JMP   sc_ret", 1)[0]

    order = [op for _, op in _instructions(body) if op in
             ("HOS_H0_SLOT", "HOS_H0_SAVE", "HOS_H0_LOAD", "HOS_FS_WRITE", "CALL")]
    calls = re.findall(r"CALL\s+(\w+)", body)
    assert calls == ["hos_h0_slot", "hos_h0_save", "hos_h0_load", "hos_fs_write"], (
        f"HFS_WRITE's call order is {calls}. It must address the caller's own "
        "slot, save the vector as it arrived, read it back from memory, and "
        "only then write the file -- so the value committed belongs to the "
        "calling process rather than to whatever last touched the register."
    )
    assert order, "no calls found in the HFS_WRITE arm"


def test_the_hfs_read_arm_saves_the_callers_h0_first() -> None:
    """READ saves before it reads, as ABI HFS v1 requires.

    This arm shipped once WITHOUT the save while a comment above it described
    one, and the structural tests of the day did not look at it. A functional
    bench would not catch the omission either: READ overwrites H0 with the
    file's vector, so the result looks right whether or not the caller's H0
    was captured first.
    """
    text = SHELL.read_text(encoding="utf-8")
    arm = text.split("sc_fr:", 1)
    assert len(arm) == 2, "shell.hasm no longer has an HFS_READ arm"
    body = arm[1].split("JMP   sc_ret", 1)[0]
    calls = re.findall(r"CALL\s+(\w+)", body)
    assert calls == ["hos_h0_slot", "hos_h0_save", "hos_fs_read"], (
        f"HFS_READ's call order is {calls}. ABI HFS v1 saves the caller's H0 "
        "into its own slot before the read replaces it."
    )


def test_the_shell_initialises_the_heap_before_serving_files() -> None:
    """hos_fs_create allocates, and an uninitialised heap refuses everything.

    0xE00 reads 0 until hos_heap_init runs, and hos_alloc treats 0 as empty.
    Every other HFS program calls the initialiser; shell.hasm did not when its
    HFS syscalls were added, so HFS_CREATE would have refused every file.
    """
    text = SHELL.read_text(encoding="utf-8")
    own = text.split(".include", 1)[0]
    body = own.split("sc_fc:", 1)[0]
    calls = [c for _, c in _instructions(body) if c == "CALL"]
    assert calls, "no calls found before the HFS arms"
    assert re.search(r"^\s*CALL\s+hos_heap_init\b", body, re.M), (
        "shell.hasm never calls hos_heap_init before its HFS syscall arms, so "
        "the heap is empty and HFS_CREATE refuses every file"
    )


def test_the_result_path_does_not_trust_r7_across_hos_calls() -> None:
    """sc_ret must find the caller's block again, not assume R7 survived.

    hos.hasm clobbers R6-R12 by convention and hos_alloc walks the heap with R7.
    With `sc_ret: STORE R1, R7, 1` trusting R7, HFS_CREATE wrote its result into
    a heap block header, the caller saw its own call number come back (6), and
    the heap was silently corrupted -- measured by tb_hcpu_hfs_syscall.v. Only
    CREATE allocates on the path that bench takes, so WRITE and READ passed
    beside it and hid nothing but their own luck.
    """
    text = SHELL.read_text(encoding="utf-8")
    body = text.split("sc_ret:", 1)
    assert len(body) == 2, "shell.hasm no longer has sc_ret"
    ret = body[1].split("RET", 1)[0]
    store = ret.find("STORE R1, R7, 1")
    recompute = ret.find("CALL  pcb_of")
    assert store != -1, "sc_ret no longer writes the result into the caller's block"
    assert recompute != -1 and recompute < store, (
        "sc_ret writes the result through R7 without re-deriving it from the "
        "current pid first. Every HFS arm calls into hos.hasm, which clobbers "
        "R6-R12 -- hos_alloc walks the heap with R7 -- so the result lands in "
        "whatever R7 last pointed at."
    )


def test_every_syscall_arm_reads_its_own_permission_word() -> None:
    """One word per call, so disabling one disables exactly one.

    The table moved out of 0xF08+n because PCB[0] begins at 0xF10: call 8's
    permission word would have landed on process 0's saved R0, and `serve`
    reads that word to decide whether the call is allowed. It would have
    worked most of the time.
    """
    text = SHELL.read_text(encoding="utf-8")
    words = {int(m, 16) for m in re.findall(r"LOAD\s+R3, R5, 0x([0-9A-F]{3})", text)}
    assert len(words) == 8, f"expected eight permission words, found {sorted(words)}"
    assert min(words) == 0xECE and max(words) == 0xED5, (
        f"the permission table sits at {hex(min(words))}..{hex(max(words))}; "
        "ABI HFS v1 places it at 0xECE-0xED5, inside the HOS region"
    )
    assert max(words) < 0xF10, (
        "the permission table has grown into PCB[0] at 0xF10 -- the exact "
        "collision it was moved to avoid"
    )
