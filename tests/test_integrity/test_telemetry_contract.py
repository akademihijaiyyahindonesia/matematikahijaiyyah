"""The telemetry contract, held against what actually measures anything.

cosmictera/TELEMETRY.md records the owner's contract of 20 September 2026. A
contract is where numbers get copied from, so the failure that matters is not
a typo: it is a field quietly acquiring a source it does not have. Every field
the contract names must appear in the table, and every row must either point
at a file that exists or say in plain words that there is no source yet.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "cosmictera" / "TELEMETRY.md"
TEXT = DOC.read_text(encoding="utf-8")
NO_SOURCE = ("belum ada sumbernya", "belum terpisah")

# The four the board cannot answer today, 20 September 2026. Two are
# derivations NUI will compute (priority 7, not started), one needs a digest
# the owner has not chosen -- there is no SHA-256 core in RTL (R10) -- and one
# is a step the loader performs without reporting separately. Pinned because
# the failure that matters is a field quietly acquiring evidence: a row can be
# flipped to "ada" and pointed at a real file while nothing measured it.
WITHOUT_SOURCE = {"anomaly_score", "corruption_score", "state_hash",
                  "last_relocation"}


def fields() -> list[str]:
    """The field names, read from the contract block rather than retyped."""
    block = TEXT.split("```")[1]
    names = []
    for line in block.splitlines():
        body = line.split(None, 1)
        tail = body[1] if len(body) > 1 and body[0].isupper() else line
        names += [n.strip() for n in tail.split("·") if n.strip()]
    return [n for n in names if re.fullmatch(r"[a-z_0-9]+", n)]


def rows() -> dict[str, str]:
    out = {}
    for line in TEXT.splitlines():
        m = re.match(r"\| `([a-z_0-9]+)` \| (.*)$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def test_the_contract_names_the_fields_the_owner_wrote() -> None:
    assert len(fields()) == 27, fields()
    assert fields()[0] == "uptime"
    assert "state_hash" in fields()
    assert "collapse_count" in fields()


def test_every_field_has_a_row() -> None:
    missing = [f for f in fields() if f not in rows()]
    assert not missing, missing
    extra = [f for f in rows() if f not in fields()]
    assert not extra, extra


def test_exactly_the_four_unmeasured_fields_are_marked_as_such() -> None:
    marked = {f for f, row in rows().items() if any(s in row for s in NO_SOURCE)}
    assert marked == WITHOUT_SOURCE, marked


def test_every_row_either_points_at_a_file_or_says_there_is_none() -> None:
    """The one that matters. A row with neither is a field that has quietly
    acquired evidence nobody measured."""
    for field, row in rows().items():
        links = re.findall(r"\]\(([^)]+)\)", row)
        # only backticked things that look like repo paths; "cube.py" in prose
        # is a reference to a module, not a citation of where a number lives
        backticked = re.findall(r"`([^`]+/[^`]+\.(?:hasm|py|v|md))`", row)
        paths = [(DOC.parent / p).resolve() for p in links]
        paths += [(ROOT / p).resolve() for p in backticked]
        if any(s in row for s in NO_SOURCE):
            assert not paths, f"{field} says it has no source and then cites one"
            continue
        assert paths, f"{field} claims a source without naming where it is"
        for path in paths:
            assert path.exists(), f"{field} points at {path}, which is not there"


def test_the_density_that_moved_columns_is_named() -> None:
    """4.75 is mod 3, and hijrah/README.md prints it in a GF(4) column. A
    contract that carried it as mod 4 would spread the error, so the page says
    so out loud and the measured table is quoted beside it."""
    assert "4,75 adalah mod 3" in TEXT or "**4,75 adalah mod 3**" in TEXT
    assert "| `density_mod4` | **ada** — 4,81" in TEXT
    measured = (ROOT / "cosmictera-build" / "validasi" / "HIJRAH.md").read_text()
    assert "| panjang 1 | 4,58 | 4,75 | 4,81 | 4,81 | 1,00 |" in measured


# -- the time hierarchy, and the three that are still open ----------------

LEVELS = ("pencacah siklus FPGA", "uptime papan", "cap waktu host")
OPEN = ("`state_hash`", "`last_relocation`", "`anomaly_score`")


def test_the_time_hierarchy_is_recorded_in_its_order() -> None:
    """Host time is not the truth, and the order is the whole of the rule.
    A page that listed the three without their order would be decoration."""
    found = [TEXT.index(level) for level in LEVELS]
    assert found == sorted(found), "the levels are out of order"
    assert "Waktu host bukan sumber kebenaran" in TEXT
    assert "140 detik" in TEXT, "the measurement that forced the rule is missing"


def test_the_three_open_contracts_are_not_quietly_settled() -> None:
    """Each is the owner's to decide. The failure that matters is one of them
    acquiring an answer in this page without him giving it."""
    section = TEXT.split("## Tiga kontrak yang belum diputuskan")[1]
    for name in OPEN:
        assert name in section, name
    assert "bukan pilihan yang diambil sepihak" in section
    # the owner's leaning on state_hash is recorded as a leaning
    assert "Dicatat sebagai" in section and "penilaian" in section


def test_what_the_open_contracts_are_held_against_still_exists() -> None:
    """The numbers quoted for the options come from files, not from memory."""
    for path in ("cosmictera-build/attack-lab/README.md",
                 "rtl/scripts/burn_in_report.py"):
        assert (ROOT / path).exists(), path
