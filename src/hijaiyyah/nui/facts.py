"""Layer 0 of NUI: an inventory of facts, each one with its own proof.

The owner's instruction, 21 September 2026: *"Jangan mulai dengan AI. Mulai
dengan inventaris fakta."* Every layer above this one asks the same question
in a different domain -- what is known to be true about this opcode, this
module, this target -- and none of them can answer it from a model. They
answer it from here.

A fact carries the fields he named: fact_id, statement, source, evidence,
verification_method, status, timestamp, and confidence. Nothing else is a
fact. `domain` is not stored -- it is the first segment of the fact_id, and
the folder a fact sits in must match it, which the guard checks.

-- confidence is not a probability ---------------------------------------
A number there would be invented, and this repository has no way to measure
one. What the field records instead is WHAT THE FACT RESTS ON, and the guard
requires it to agree with the verification method rather than be asserted
beside it:

    recomputed       the value is derived again every test run
    test-backed      a named test node carries it
    board-measured   it came off the Tang Nano 20K and cannot be re-run here

If the owner meant a graded number, that is a decision to take before any
number goes in -- not after.

-- the status vocabulary is the repository's, not a new one ---------------
cosmictera/RULES.md already labels claims VF, CC, DP, EH, AT, and R2 forbids
raising a label without new evidence. This module uses those five and no
others: inventing "verified" beside them would leave two vocabularies for one
idea, which ENGINEERING_STANDARD.md calls a defect by name.

-- the part that makes this an inventory rather than a list ---------------
Three kinds of verification, and the difference between them is the whole
point:

  derive   the value is RECOMPUTED from the repository every time the tests
           run, and the fact fails if the two disagree. The strongest kind:
           such a fact cannot rot, because nothing else in the repo can move
           without it noticing.
  pytest   the fact names a test node that must exist and pass. The proof is
           real but indirect -- the guard checks the node is there, and the
           suite checks the node is green.
  board    the fact came off the Tang Nano 20K. It CANNOT be re-run here, and
           this module says so rather than pretending: the record it points
           at is the evidence, and re-running it needs the hardware.

JSON, not YAML, and for a plain reason: PyYAML is not installed, and pulling
a dependency in needs the owner's permission (AGENTS.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[3]
FACTS = ROOT / "facts"
#: cosmictera/RULES.md's table, in its own order.
STATUSES = ("VF", "CC", "DP", "EH", "AT")
KINDS = ("derive", "pytest", "board")
FIELDS = ("fact_id", "statement", "source", "evidence", "verification_method",
          "status", "timestamp", "confidence")
#: What each verification method leaves a fact resting on. The guard requires
#: the stored confidence to be exactly this -- a fact cannot claim to be
#: recomputed while naming a board command.
CONFIDENCE_OF_KIND = {"derive": "recomputed", "pytest": "test-backed",
                      "board": "board-measured"}


@dataclass(frozen=True)
class Fact:
    fact_id: str
    statement: str
    source: tuple[str, ...]
    evidence: tuple[str, ...]
    verification_method: dict[str, object]
    status: str
    timestamp: str
    confidence: str
    value: object = None
    path: Path | None = None

    @property
    def domain(self) -> str:
        return self.fact_id.split(".", 1)[0]

    @property
    def kind(self) -> str:
        return str(self.verification_method["kind"])


# -- the derivations -------------------------------------------------------
#
# Each one recomputes a fact's value from the repository's own sources. They
# are deliberately tiny: a derivation that needed explaining would be a
# second implementation of the thing it checks.


def codex_theta_u_rho_sum() -> int:
    from ..core.master_table import MASTER_TABLE
    return sum(e.theta_hat + e.U + e.rho for e in MASTER_TABLE.all_entries())


def letter_count() -> int:
    from ..core.master_table import MASTER_TABLE
    return len(MASTER_TABLE.all_entries())


def _jamrah_rows() -> list[list[str]]:
    text = (ROOT / "rtl" / "tb" / "jamrah_vectors.txt").read_text()
    return [ln.split() for ln in text.split("\n") if len(ln.split()) == 9]


def jamrah_pulse_count() -> int:
    return sum(int(r[1]) for r in _jamrah_rows())


def jamrah_node_sum() -> int:
    return sum(sum(int(x) for x in r[2:8]) + int(r[8], 16) for r in _jamrah_rows())


def counter_wrap_seconds() -> float:
    """The free-running counter at 0xFF4: 32 bits at the board's 27 MHz."""
    return round(2 ** 32 / 27_000_000, 6)


def instruction_memory_words() -> int:
    from ..hisa.machine import HISAMachine
    return int(HISAMachine.CODE_DEPTH)


def data_memory_words() -> int:
    from ..hisa.machine import HISAMachine
    return int(HISAMachine.DATA_DEPTH)


def address_unification_holds() -> bool:
    """Master Table index = H-ISA opcode = HCPU ROM address, for all 28."""
    from .atom import verify_address_unification
    verify_address_unification()
    return True


def no_computed_jump() -> bool:
    """JMP and CALL both take an immediate; there is no JALR in the set. It is
    why the syscall table lives in data memory and why an interpreter's
    dispatch loop pays a comparison chain."""
    from ..hisa.opcodes import OpCode
    return not any(name in OpCode.__members__ for name in ("JALR", "JMPR", "CALLR"))


def tail_one_below_full_rank() -> list[str]:
    """Letters whose face over GF(2) is already inside its own cycle (tail 1)
    and yet has rank below 5 -- each one a case where tail 1 is not
    invertibility, which the docstrings of matrix_order and gf2_rank equate."""
    from ..core.exomatrix import build_exomatrix, gf2_rank, matrix_order
    from ..core.master_table import MASTER_TABLE
    return [e.name for e in MASTER_TABLE.all_entries()
            if matrix_order(e.vector, 2)[0] == 1
            and gf2_rank(tuple(tuple(x % 2 for x in row)
                               for row in build_exomatrix(e.vector))) < 5]


DERIVATIONS: dict[str, Callable[[], object]] = {
    "codex_theta_u_rho_sum": codex_theta_u_rho_sum,
    "letter_count": letter_count,
    "jamrah_pulse_count": jamrah_pulse_count,
    "jamrah_node_sum": jamrah_node_sum,
    "counter_wrap_seconds": counter_wrap_seconds,
    "instruction_memory_words": instruction_memory_words,
    "data_memory_words": data_memory_words,
    "address_unification_holds": address_unification_holds,
    "no_computed_jump": no_computed_jump,
    "tail_one_below_full_rank": tail_one_below_full_rank,
}


# -- loading and checking --------------------------------------------------


def load(root: Path = FACTS) -> list[Fact]:
    """Every fact in the inventory, in fact_id order."""
    facts = []
    for path in sorted(root.rglob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        missing = [f for f in FIELDS if f not in raw]
        if missing:
            raise ValueError(f"{path}: missing {missing}")
        facts.append(Fact(
            fact_id=raw["fact_id"], statement=raw["statement"],
            source=tuple(raw["source"]), evidence=tuple(raw["evidence"]),
            verification_method=raw["verification_method"],
            status=raw["status"], timestamp=raw["timestamp"],
            confidence=raw["confidence"], value=raw.get("value"), path=path))
    return sorted(facts, key=lambda f: f.fact_id)


def verify(fact: Fact) -> tuple[bool, str]:
    """(held, what happened). A `board` fact returns False for held with the
    reason -- it is not a failure, it is a statement that the proof lives on
    hardware this process cannot reach."""
    kind = fact.kind
    if kind == "derive":
        name = str(fact.verification_method["derivation"])
        if name not in DERIVATIONS:
            return False, f"no derivation named {name}"
        got = DERIVATIONS[name]()
        if got != fact.value:
            return False, f"recomputed {got!r}, the fact says {fact.value!r}"
        return True, f"recomputed {got!r}"
    if kind == "pytest":
        return True, f"proved by {fact.verification_method['node']}"
    return False, "measured on the board; re-running it needs the hardware"


def by_domain(facts: list[Fact] | None = None) -> dict[str, list[Fact]]:
    out: dict[str, list[Fact]] = {}
    for fact in facts if facts is not None else load():
        out.setdefault(fact.domain, []).append(fact)
    return out


def main() -> int:
    facts = load()
    for domain, group in sorted(by_domain(facts).items()):
        print(f"{domain} ({len(group)})")
        for fact in group:
            held, why = verify(fact)
            mark = "ok " if held else "-- "
            print(f"  {mark}{fact.fact_id:<38} [{fact.status}] {why}")
    print()
    for name in sorted(set(CONFIDENCE_OF_KIND.values())):
        print(f"  {name:<16} {sum(1 for f in facts if f.confidence == name)}")
    print(f"\n{len(facts)} facts, "
          f"{sum(1 for f in facts if f.kind == 'derive')} recomputed here, "
          f"{sum(1 for f in facts if f.kind == 'pytest')} proved by a test, "
          f"{sum(1 for f in facts if f.kind == 'board')} measured on the board")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
