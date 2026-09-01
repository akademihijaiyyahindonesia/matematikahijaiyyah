"""
The board experiments, verified in simulation before the board arrives.

rtl/programs/bench/ holds the programs to run on the Tang Nano 9K. Each is
checked here on the H-ISA machine so that what reaches the device is already
known-good: a wrong program on real hardware costs a flash cycle and a
debugging session to discover something a second of simulation would have
caught.

E5 is the one that mattered most to check. It loads ROM index 31 — the
deliberately corrupt vector — and the Python machine did not have that entry
at all. An index naming no letter left the register holding zeros, which is
the monoid identity and passes every guard, so the program reported 404 here
and 200 on the HCPU. Same program, opposite answer, and no parity test used
the index.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import ROM_TEST_INDEX, ROM_TEST_VECTOR, HISAMachine

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "rtl" / "programs" / "bench"
PROGRAMS = sorted(BENCH.glob("*.hasm"))


def run(path: Path) -> Dict:
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble(path.read_text(encoding="utf-8")))
    trace = machine.run()
    return {"retired": len(trace), "state": machine.dump_state()}


def test_the_experiments_exist() -> None:
    assert len(PROGRAMS) >= 9, f"only {len(PROGRAMS)} bench programs"


@pytest.mark.parametrize("path", PROGRAMS, ids=[p.stem for p in PROGRAMS])
def test_every_experiment_assembles_and_halts(path: Path) -> None:
    words = assemble(path.read_text(encoding="utf-8"))
    assert words[-1] >> 24 in (0x01, 0xA0), "a program that runs off the end hangs"
    assert run(path)["retired"] > 0


# ── E2: the guard's cost, measured by difference ─────────────────

def test_the_guard_costs_one_instruction() -> None:
    """
    Ten guards minus one guard is nine guards, so every setup cost cancels.
    On the board the same subtraction gives cycles instead of instructions,
    which is the number pipeline effects hide.
    """
    one = run(BENCH / "e2_guard_x1.hasm")["retired"]
    ten = run(BENCH / "e2_guard_x10.hasm")["retired"]
    assert (ten - one) == 9, f"nine extra guards cost {ten - one}"


@pytest.mark.parametrize("n", [2, 4, 8, 12])
def test_the_guard_does_not_grow_with_string_length(n: int) -> None:
    """
    §IIIC.3.2.1: the aggregate of n letters is itself one codex, so guarding
    it is six checks over eighteen integers whatever n was. Aggregation is
    linear; validation is flat.
    """
    retired = run(BENCH / f"e2_scale_n{n:02d}.hasm")["retired"]
    aggregation = 2 * n - 1          # one HLOAD, then HLOAD+HCADD per letter
    assert retired == aggregation + 2, (
        "exactly one guard and one halt beyond loading, whatever n is"
    )


# ── E3: the sealed table, letter by letter ───────────────────────

def test_the_sweep_reads_every_sealed_theta() -> None:
    words = assemble((BENCH / "e3_sweep28.hasm").read_text(encoding="utf-8"))
    loads = [w & 0xFFF for w in words if w >> 24 == 0x40]
    assert loads == list(range(1, 29)), "the sweep must cover all 28 letters"

    expected = [e.vector[0] for e in MASTER_TABLE.all_entries()]
    header = (BENCH / "e3_sweep28.hasm").read_text(encoding="utf-8")
    quoted = [int(x) for x in header.split("diharapkan:")[-1].split("\n")[0].split()] \
        if "diharapkan:" in header else None
    if quoted is None:
        quoted = [int(x) for x in header.split("Keluaran yang diharapkan:")[1]
                  .split("\n")[0].split()]
    assert quoted == expected, "the comment must quote the sealed Θ̂ values"


# ── E4: a whole HISAB frame ──────────────────────────────────────

def test_the_frame_experiment_emits_all_three_words_and_a_digest() -> None:
    state = run(BENCH / "e4_frame.hasm")["state"]
    from hijaiyyah.hisab.serialize import (
        _compute_guard_status,
        _nibble_pack,
        serialize_letter,
    )

    entry = MASTER_TABLE.get_by_char("ب")
    assert entry is not None
    v = list(entry.vector)
    packed = _nibble_pack(v)

    assert state["gpr"][1] == int.from_bytes(packed[0:4], "little")
    assert state["gpr"][2] == int.from_bytes(packed[4:8], "little")
    assert state["gpr"][3] == (_compute_guard_status(v) << 8) | packed[8]
    assert state["gpr"][4] == serialize_letter(v).digest
    assert len({state["gpr"][i] for i in (1, 2, 3)}) == 3, "three distinct words"


# ── E5: the corrupt vector, on both machines ─────────────────────

def test_the_negative_experiment_rejects_the_corrupt_vector() -> None:
    assert run(BENCH / "e5_negative.hasm")["state"]["gpr"][1] == 200


def test_the_python_rom_carries_the_same_test_vector_as_the_rtl() -> None:
    """
    hcpu_rom.v index 31. The two ROMs must hold the same bytes or the same
    program means different things on the two machines.
    """
    source = (ROOT / "rtl" / "hcpu_rom.v").read_text(encoding="utf-8")
    import re

    match = re.search(r"5'd31:\s*data_out\s*=\s*\{([^}]*)\}", source)
    assert match, "hcpu_rom.v has no index 31"
    rtl = list(reversed([int(x) for x in re.findall(r"8'd(\d+)", match.group(1))]))
    assert rtl == list(ROM_TEST_VECTOR)
    assert ROM_TEST_INDEX == 31


def test_an_index_naming_no_entry_halts_rather_than_loading_zeros() -> None:
    """
    Zeros are the monoid identity and pass every guard, so a silent zero load
    turned an invalid index into a value that validated.
    """
    machine = HISAMachine(MASTER_TABLE)
    machine.load_program(assemble("HLOAD H0, #29\nMOVI R1, #7\nHALT\n"))
    machine.run()
    assert machine.dump_state()["gpr"][1] == 0, "execution must stop at the load"


# ── E6: structural triage of a guarded record ────────────────────

def test_the_record_triage_accepts_a_well_formed_record() -> None:
    """
    Sixteen sealed letters, one guard each, on the processor. The letters are
    the base-28 encoding crypto/guarded_record.py produces, so the program on
    the board and the library in Python are validating the same record.
    """
    assert run(BENCH / "e6_record_triage.hasm")["state"]["gpr"][1] == 200


def test_the_triage_program_encodes_the_payload_the_library_would() -> None:
    """
    A hand-typed letter sequence would drift from the encoder. This checks the
    program carries exactly what encode_bytes() produces.
    """
    from hijaiyyah.crypto.guarded_record import encode_bytes

    source = (BENCH / "e6_record_triage.hasm").read_text(encoding="utf-8")
    words = assemble(source)
    loaded = [w & 0xFFF for w in words if w >> 24 == 0x40]

    payload = source.split("Payload ")[1].split(" dikodekan")[0]
    assert list(encode_bytes(eval(payload))) == loaded


def test_one_guard_per_letter_and_nothing_more() -> None:
    """
    Triage is O(1) per element: the cost is the record's length, not its
    content. Any extra work per letter would show up here as a second guard.
    """
    words = assemble((BENCH / "e6_record_triage.hasm").read_text(encoding="utf-8"))
    loads = sum(1 for w in words if w >> 24 == 0x40)
    guards = sum(1 for w in words if w >> 24 == 0x60)
    assert loads == guards == 16
