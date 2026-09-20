"""The fact inventory, checked against the repository it claims to describe.

Layer 0 exists so the layers above it stop answering "I think". A fact base
that is never re-checked becomes the opposite -- a tidy list of things that
used to be true -- so every fact here is held against its own proof:

  derive   recomputed from the repository now, in this test run. If anything
           the fact depends on moves, this goes red.
  pytest   the node it names must be in the tree.
  board    it must name the command that produced it, because nothing here
           can re-run it.

And every path a fact cites must exist. That is the failure this file exists
for: a fact whose evidence has been deleted still reads like a fact.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui.facts import (  # noqa: E402
    DERIVATIONS,
    FIELDS,
    KINDS,
    STATUSES,
    load,
    verify,
)

FACTS = load()
#: cosmictera/RULES.md's five labels, and no sixth. Two vocabularies for one
#: idea is what ENGINEERING_STANDARD.md calls a defect.
RULES = ROOT / "cosmictera" / "RULES.md"


def test_the_inventory_is_not_empty_and_has_no_duplicate_ids() -> None:
    assert len(FACTS) >= 20, len(FACTS)
    ids = [f.fact_id for f in FACTS]
    assert len(ids) == len(set(ids)), "a fact_id appears twice"


def test_every_fact_carries_the_seven_fields() -> None:
    for fact in FACTS:
        for field in FIELDS:
            assert getattr(fact, field), f"{fact.fact_id} has an empty {field}"


def test_the_status_vocabulary_is_the_one_rules_already_defines() -> None:
    rules = RULES.read_text(encoding="utf-8")
    for status in STATUSES:
        assert f"**{status}**" in rules, f"{status} is not in RULES.md's table"
    for fact in FACTS:
        assert fact.status in STATUSES, (fact.fact_id, fact.status)


def test_every_derived_fact_recomputes_to_what_it_says() -> None:
    """The strongest kind, and the reason this is an inventory rather than a
    list: these cannot rot quietly."""
    derived = [f for f in FACTS if f.kind == "derive"]
    assert len(derived) >= 8, len(derived)
    for fact in derived:
        held, why = verify(fact)
        assert held, f"{fact.fact_id}: {why}"


def test_every_file_a_fact_cites_exists() -> None:
    for fact in FACTS:
        for path in fact.source + fact.evidence:
            assert (ROOT / path).exists(), f"{fact.fact_id} cites {path}"


def test_every_verification_names_something_real() -> None:
    for fact in FACTS:
        assert fact.kind in KINDS, (fact.fact_id, fact.kind)
        if fact.kind == "pytest":
            node = str(fact.verification_method["node"])
            file, _, name = node.partition("::")
            assert (ROOT / file).exists(), f"{fact.fact_id} names {file}"
            if name:
                assert name in (ROOT / file).read_text(), f"{fact.fact_id}: {name}"
        elif fact.kind == "derive":
            assert str(fact.verification_method["derivation"]) in DERIVATIONS
        else:
            assert fact.verification_method["command"], fact.fact_id


def test_a_board_fact_says_it_cannot_be_re_run_here() -> None:
    """Not a failure -- a statement. Pretending otherwise would make the
    inventory claim the hardware was consulted when it was not."""
    board = [f for f in FACTS if f.kind == "board"]
    assert board, "the board facts went missing"
    for fact in board:
        held, why = verify(fact)
        assert not held
        assert "hardware" in why


def test_each_fact_sits_in_the_folder_its_id_names() -> None:
    for fact in FACTS:
        assert fact.path is not None
        assert fact.path.parent.name == fact.domain, fact.fact_id
