"""The Hijaiyyah Registry, held to the places each column is read from.

Letter -> operator -> HC -> HISA, as the owner ordered it on 22 September 2026.
What would rot quietly: the JSON drifting from what builds it, a letter
quietly becoming nameable in HC, a word that no longer assembles from the
letter itself, and Jim's periods -- the one thing cosmic-codex-jim/ measures --
moving without anyone reading it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.opcodes import OpCode  # noqa: E402
from hijaiyyah.nui import registry  # noqa: E402

RECORDS = registry.build()
BY_NAME = {r["name"]: r for r in RECORDS}


def test_the_registry_is_built_not_written() -> None:
    assert json.loads(registry.DB.read_text(encoding="utf-8")) == RECORDS


def test_twenty_eight_letters_in_master_table_order() -> None:
    """Twenty-eight, because the Master Table and the slots 0xE0-0xFB hold
    28. The 29 in the owner's message was a slip -- the owner, 22 September
    2026 -- and is not part of the specification."""
    entries = MASTER_TABLE.all_entries()
    assert len(RECORDS) == len(entries) == 28
    assert [r["char"] for r in RECORDS] == [e.char for e in entries]
    assert [r["index"] for r in RECORDS] == list(range(1, 29))
    assert [int(r["operator"]["instruction"]["opcode"], 16) for r in RECORDS] == list(
        range(0xE0, 0xFC))


def test_each_letter_assembles_from_itself_to_its_own_instruction() -> None:
    for r in RECORDS:
        op = OpCode[r["operator"]["instruction"]["mnemonic"]]
        assert int(r["hisa"]["word"], 16) == int(op) << 24, r["char"]
        assert r["operator"]["instruction"]["rom_address"] == r["index"]


def test_the_operator_is_read_from_the_line_that_states_it() -> None:
    source = RECORDS[0]["operator"]["instruction"]["source"]
    path, line = source.rsplit(":", 1)
    text = (ROOT / path).read_text(encoding="utf-8").splitlines()[int(line) - 1]
    assert "HREG[0] <- HREG[0] + v(letter)" in text


def test_a_letter_is_a_value_in_hc_and_never_a_name() -> None:
    """The owner: a single letter stays a mathematical object. HC already
    holds it -- the parser refuses every one of the 28 as a variable name."""
    for r in RECORDS:
        assert r["hc"]["compiles_to"] == f"HLOAD H0, #{r['index']}", r["char"]
        assert "Expected variable name" in (r["hc"]["as_a_name"] or ""), r["char"]


def test_jim_and_kha_keep_the_periods_cosmic_codex_jim_records() -> None:
    """cosmic-codex-jim/MACHINE.md: Jim 31 over GF(2) and 3124 over GF(5),
    Kha 31 over GF(2), Ha 2 -- one dot moves the period from 2 to 31."""
    jim, kha, ha = BY_NAME["Jim"]["operator"]["face"], BY_NAME["Kha"]["operator"]["face"], \
        BY_NAME["Ha"]["operator"]["face"]
    assert (jim["gf2"], jim["gf5"]) == ({"tail": 1, "period": 31}, {"tail": 1, "period": 3124})
    assert kha["gf2"] == {"tail": 1, "period": 31}
    assert ha["gf2"]["period"] == 2
    maximal = sorted(r["name"] for r in RECORDS if r["operator"]["face"]["gf2"]["period"] == 31)
    assert maximal == ["Jim", "Kha"]


def test_a_tail_of_one_is_not_invertibility() -> None:
    """The page says so, against the docstrings of matrix_order and gf2_rank:
    seven letters sit in their own cycle over GF(2) with a rank below 5. Dal
    is the plainest -- tail 1, period 1, rank 3."""
    dal = BY_NAME["Dal"]["operator"]["face"]
    assert (dal["gf2"]["tail"], dal["gf2"]["period"], dal["rank_gf2"]) == (1, 1, 3)
    singular = [r["name"] for r in RECORDS if r["operator"]["face"]["gf2"]["tail"] == 1
                and r["operator"]["face"]["rank_gf2"] < 5]
    assert singular == ["Dal", "Dzal", "Tha", "Ain", "Ghain", "Mim", "Ya"]
    invertible = [r["name"] for r in RECORDS if r["operator"]["face"]["rank_gf2"] == 5]
    assert invertible == ["Jim", "Kha"]
