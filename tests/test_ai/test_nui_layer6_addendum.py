"""Layer 6's post-freeze addendum, held beside the frozen records it amends.

The owner's decision of 1 October 2026, after the HMAC commit left three
Layer 6 --verify checks red with expected post-freeze drift: the frozen
registry stays immutable, the addendum is a new record, each entry gives the
old pointer or hash, the current state, a concrete reason, the causing commit
and evidence of equivalence, and nothing is mapped in bulk. The verifiers
read both -- historical freeze is not current repository state. What is held
here:

    the frozen records, pages and specs are the objects at the tag;
    the addendum covers exactly the drift, pointer by pointer;
    frozen plus addendum is today's build, and the freeze alone is not;
    every entry has its reason, its cause and evidence that holds;
    a file changed twice is a chain written out link by link (owner,
    5 October 2026), and a second change with no link is still refused;
    and each guard turns red when what it guards is broken (R3).
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import hardware  # noqa: E402
from hijaiyyah.nui import hardware_provenance as hp  # noqa: E402
from hijaiyyah.nui import layer6_addendum as la  # noqa: E402
from hijaiyyah.nui import telemetry_sources as ts  # noqa: E402
from hijaiyyah.nui.layer6_freeze import TAG, _diff  # noqa: E402

ADDENDUM = la.load()
MODULES = {"hardware": hardware, "telemetry_sources": ts, "hardware_provenance": hp}
CAUSE = "4bff781"
#: The Ka'bah layer 3 commit, which added lines to the Makefile a second time.
CAUSE2 = "004b9a0"
FIRST, SECOND = "Makefile — target HMAC", "Makefile — lapis 3 slot UART Ka'bah"


def _frozen(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / la.FROZEN[name][0]).read_text(encoding="utf-8"))
    return data


def _fresh(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(json.dumps(MODULES[name].build()))
    return data


def test_the_frozen_records_are_the_objects_at_the_tag() -> None:
    """Immutable: each record, its page and its spec, byte for byte."""
    for name, paths in la.FROZEN.items():
        for path in paths:
            held = subprocess.run(["git", "show", f"{TAG}:{path}"], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            assert (ROOT / path).read_bytes() == held, path
        assert la.problems(name) == [], name


def test_the_addendum_covers_exactly_the_drift() -> None:
    """Every pointer that moved since the freeze is named, and nothing else."""
    for name in la.FROZEN:
        drift = set(_diff(_frozen(name), _fresh(name)))
        named = [c["pointer"] for c in la.changes(name)]
        assert sorted(set(named)) == sorted(drift), name
        # Named once -- except the four pointers of the one chain, twice.
        twice = sorted(p for p in set(named) if named.count(p) > 1)
        assert all(named.count(p) == 2 for p in twice), name
        assert twice == (sorted(c["pointer"] for c in _entry(ADDENDUM, SECOND)["changes"])
                         if name == "hardware" else []), name
    assert {n: len(la.changes(n)) for n in la.FROZEN} == {
        "hardware": 23, "telemetry_sources": 8, "hardware_provenance": 39}
    assert len(ADDENDUM["entries"]) == 6


def test_the_historical_freeze_is_not_the_current_state() -> None:
    """Frozen plus addendum is what the evidence builds today; the freeze
    alone is not, and applying the addendum leaves the freeze as it was."""
    for name in la.FROZEN:
        frozen = _frozen(name)
        kept = copy.deepcopy(frozen)
        now = la.current(name, frozen)
        assert frozen == kept, name
        assert now == _fresh(name) and now != frozen, name


def test_the_freeze_read_against_today_is_red_and_the_current_state_is_not() -> None:
    """The R3 check `simulated -> measured` stands on this: the frozen claim
    no longer matches today's file, the current one does."""
    ctx = hp.context()

    def lut4(model: dict[str, Any]) -> dict[str, Any]:
        return next(c for c in model["claims"] if c["id"] == "6.1:fpga_lut4")
    assert [f["check"] for f in hp.check(lut4(_frozen("hardware_provenance")), ctx)] == [4, 5]
    assert hp.check(lut4(la.current("hardware_provenance")), ctx) == []


def test_every_entry_says_why_by_what_and_with_what_evidence() -> None:
    def touched(commit: str) -> list[str]:
        return subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
                              cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    for e in ADDENDUM["entries"]:
        assert e["cause"] == (CAUSE2 if e["id"] == SECOND else CAUSE), e["id"]
        assert e["reason"] and e["path"] in touched(e["cause"]), e["id"]
        assert ("after" in e) == (e["id"] == SECOND), e["id"]
        assert e["equivalence"]["kind"] in la.KINDS, e["id"]
        assert e["changes"] and all(set(c) == {"record", "pointer", "old", "new"}
                                    and c["old"] != c["new"] for c in e["changes"]), e["id"]
    assert list(ADDENDUM["kinds"]) == list(la.KINDS)
    assert {e["equivalence"]["kind"] for e in ADDENDUM["entries"]} == set(la.KINDS)


def _show(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def test_the_chain_is_written_out_and_every_link_of_it_is_checked() -> None:
    """Owner, 5 October 2026: frozen Makefile -> 4bff781 -> 004b9a0, each
    change pointing at the one before it, each hash read from git here and
    not from the module."""
    first, second = _entry(ADDENDUM, FIRST), _entry(ADDENDUM, SECOND)
    path = "rtl/fpga/gowin/Makefile"
    assert first["path"] == second["path"] == path and second["after"] == FIRST
    assert ADDENDUM["entries"].index(first) < ADDENDUM["entries"].index(second)
    assert (first["cause"], second["cause"]) == (CAUSE, CAUSE2)
    assert subprocess.run(["git", "merge-base", "--is-ancestor", CAUSE, CAUSE2],
                          cwd=ROOT).returncode == 0

    def sha(data: bytes) -> str:
        return la._sha(data)
    frozen, a, b = sha(_show(TAG, path)), sha(_show(CAUSE, path)), sha(_show(CAUSE2, path))
    assert len({frozen, a, b}) == 3
    assert sha(_show(CAUSE + "^", path)) == frozen     # nothing before the first cause
    assert sha(_show(CAUSE2 + "^", path)) == a         # nothing between the two causes
    assert sha((ROOT / path).read_bytes()) == b        # nothing since the second
    keys = [(c["record"], c["pointer"]) for c in first["changes"]]
    assert keys == [(c["record"], c["pointer"]) for c in second["changes"]] and len(keys) == 4
    assert {(c["old"], c["new"]) for c in first["changes"]} == {(frozen, a)}
    assert {(c["old"], c["new"]) for c in second["changes"]} == {(a, b)}
    links, unlinked = la._links(ADDENDUM)
    assert links == {FIRST: (None, SECOND), SECOND: (FIRST, None)}
    assert unlinked == {SECOND: []}
    # Each step only added lines, and so did the whole.
    for was, now in ((TAG, CAUSE), (CAUSE, CAUSE2), (TAG, CAUSE2)):
        rest = iter(_show(now, path).decode().splitlines())
        assert all(line in rest for line in _show(was, path).decode().splitlines()), (was, now)


def test_a_chain_is_never_inferred() -> None:
    """Without `after` the second entry is a pointer changed twice, and the
    record is refused before it is built."""
    addendum = copy.deepcopy(ADDENDUM)
    del _entry(addendum, SECOND)["after"]
    assert la._links(addendum) == ({}, {})
    assert sum("is changed twice" in p for p in la.problems("hardware", addendum)) == 4
    with pytest.raises(LookupError, match="the frozen record holds"):
        la.current("hardware", addendum=addendum)

    # Naming a link is not enough: one that does not hold leaves the pointer
    # changed twice, beside what is wrong with the link.
    named = copy.deepcopy(ADDENDUM)
    _entry(named, SECOND)["after"] = "Makefile — nothing"
    bad = la.problems("hardware", named)
    assert sum("is changed twice" in p for p in bad) == 4
    assert any("which is no entry written before it" in p for p in bad)

    # And an entry that stands alone answers from the freeze, not from just
    # before its own cause: the second change cannot pass as the first.
    alone = copy.deepcopy(ADDENDUM)
    alone["entries"].remove(_entry(alone, FIRST))
    del _entry(alone, SECOND)["after"]
    assert sum("at the freeze and until its cause" in p
               for p in la.problems("hardware", alone)) == 4


def test_a_chain_does_not_fork_and_does_not_reach_forward() -> None:
    addendum = copy.deepcopy(ADDENDUM)
    third = copy.deepcopy(_entry(addendum, SECOND))
    third["id"] = "Makefile — a second continuation"
    addendum["entries"].append(third)
    links, unlinked = la._links(addendum)
    assert links[FIRST] == (None, SECOND) and third["id"] not in links
    assert any("is already continued by" in p for p in unlinked[third["id"]])
    assert any("is already continued by" in p for p in la.problems("hardware", addendum))

    forged = copy.deepcopy(ADDENDUM)
    _first(forged, SECOND, "hardware")["old"] = "0" * 64
    assert any("its old values are not the new values of" in p
               for p in la._links(forged)[1][SECOND])

    forward = copy.deepcopy(ADDENDUM)
    entries = forward["entries"]
    entries.insert(0, entries.pop(entries.index(_entry(forward, SECOND))))
    assert any("which is no entry written before it" in p
               for p in la._links(forward)[1][SECOND])


def test_the_verifiers_read_both_and_the_addendum_holds() -> None:
    for module in MODULES.values():
        assert module.verify() == [], module.__name__
    assert la.check() == []


def test_the_page_is_drawn_from_the_record() -> None:
    assert la.PAGE.read_text(encoding="utf-8") == la.page(ADDENDUM)


# -- R3: each guard red when what it guards is broken -----------------------------------


def _entry(addendum: dict[str, Any], prefix: str) -> dict[str, Any]:
    return next(e for e in addendum["entries"] if e["id"].startswith(prefix))


def _first(addendum: dict[str, Any], prefix: str, record: str) -> dict[str, Any]:
    return next(c for c in _entry(addendum, prefix)["changes"] if c["record"] == record)


def _board_value() -> dict[str, Any]:
    return {"record": "hardware", "pointer": "/items/0/value",
            "old": _frozen("hardware")["items"][0]["value"]}


def _edit_file(monkeypatch: pytest.MonkeyPatch, path: str, edit: Callable[[bytes], bytes]) -> None:
    real = la._now
    monkeypatch.setattr(la, "_now", lambda p: edit(real(p)) if p == path else real(p))


Sabotage = Callable[[dict[str, Any], pytest.MonkeyPatch], None]
TOP, MAKE, PAPAN, ROW = "hcpu_gowin_top.v — cap", "Makefile", "PAPAN.md", "TELEMETRY.md"


def _drop(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    e = _entry(a, TOP)
    e["changes"] = [c for c in e["changes"] if c["pointer"] != "/items/3/source/sha256"]


def _no_line(data: bytes) -> bytes:
    return b"\n".join(ln for ln in data.split(b"\n") if not ln.startswith(b".PHONY"))


SABOTAGES: dict[str, tuple[str, Sabotage, str]] = {
    "a change dropped": ("hardware", _drop, "/items/3/source/sha256"),
    "an old value forged": ("hardware", lambda a, _: _first(a, TOP, "hardware").update(
        old="0" * 64), "the frozen record holds"),
    "a new value forged": ("hardware", lambda a, _: _first(a, TOP, "hardware").update(
        new="0" * 64), "/items/3/source/sha256"),
    "a pointer changed twice": ("hardware", lambda a, _: _entry(a, TOP)["changes"].append(
        dict(_first(a, TOP, "hardware"))), "changed twice"),
    "a change to itself": ("hardware", lambda a, _: _entry(a, MAKE)["changes"].append(
        {**_board_value(), "new": _board_value()["old"]}), "changed to itself"),
    "a change where nothing drifted": ("hardware", lambda a, _: _entry(a, MAKE)["changes"].append(
        {**_board_value(), "new": "Tang Nano 9K"}), "/items/0/value"),
    "no reason": ("hardware", lambda a, _: _entry(a, TOP).update(reason=""), "no reason"),
    "a cause that never changed the file": ("hardware", lambda a, _: _entry(a, MAKE).update(
        cause="a64f319"), "does not change rtl/fpga/gowin/Makefile"),
    "a cause from before the freeze": ("hardware", lambda a, _: _entry(a, MAKE).update(
        cause="08ffbed"), "does not come after"),
    "a cause that is no commit": ("hardware", lambda a, _: _entry(a, MAKE).update(
        cause="0000000"), "is not a commit"),
    "evidence of no kind": ("hardware", lambda a, _: _entry(a, MAKE).update(
        equivalence={"kind": "looks-fine"}), "is not evidence of equivalence"),
    "a line that did not move there": ("hardware", lambda a, _: _entry(a, PAPAN).update(
        equivalence={"kind": "line-moved", "lines": [[1315, 1348], [1321, 1355]]}),
        "at the freeze is not"),
    "a design line changed": ("hardware", lambda a, mp: _edit_file(
        mp, "rtl/fpga/gowin/hcpu_gowin_top.v",
        lambda d: d.replace(b"\nendmodule", b"\nendmodule // edited", 1)),
        "changed in more than comments"),
    "a line removed": ("hardware", lambda a, mp: _edit_file(mp, "rtl/fpga/gowin/Makefile",
                                                           _no_line), "lost or changed a line"),
    "a row that changed its meaning": ("telemetry_sources", lambda a, mp: _edit_file(
        mp, "cosmictera/TELEMETRY.md",
        lambda d: d.replace("| `state_hash` | **belum ada".encode(),
                            "| `state_hash` | **ada".encode(), 1)),
        "changed whether its field has a source"),
    # -- the chain (owner, 5 October 2026) ------------------------------------------
    "a second change with no link": ("hardware", lambda a, _: _entry(a, SECOND).pop("after"),
                                     "the frozen record holds"),
    "a link to an entry that is not there": ("hardware", lambda a, _: _entry(a, SECOND).update(
        after="Makefile — nothing"), "which is no entry written before it"),
    "a link to an entry about another file": ("hardware", lambda a, _: _entry(a, SECOND).update(
        after=_entry(a, TOP)["id"]), "which is about another file"),
    "a link past its predecessor's hash": ("hardware", lambda a, _: _first(
        a, SECOND, "hardware").update(old="0" * 64), "the record after"),
    "a predecessor rewritten under its link": ("hardware", lambda a, _: _first(
        a, FIRST, "hardware").update(new="0" * 64), "the record after"),
    "a link that skips a pointer": ("hardware", lambda a, _: _entry(a, SECOND)["changes"].pop(),
                                    "does not change the pointers"),
    "a link whose cause is not later": ("hardware", lambda a, _: _entry(a, SECOND).update(
        cause=CAUSE), "does not come after"),
    "a link on evidence that is not a whole file's hash": (
        "hardware", lambda a, _: _entry(a, PAPAN).update(after=_entry(a, TOP)["id"]),
        "a chain is only for a whole file's hash"),
    "a last link that is not the file now": ("hardware", lambda a, mp: _edit_file(
        mp, "rtl/fpga/gowin/Makefile", lambda d: d + b"\n# one more line\n"),
        "at its cause and now"),
    "a frozen record edited": ("hardware", lambda a, mp: _edit_file(
        mp, "NUI/hardware_inventory.json", lambda d: d + b"\n"), "is not the object frozen at"),
    "a frozen page edited": ("telemetry_sources", lambda a, mp: _edit_file(
        mp, "NUI/TELEMETRY_SOURCES.md", lambda d: d + b"\n"), "is not the object frozen at"),
}


@pytest.mark.parametrize("name", SABOTAGES)
def test_each_sabotage_turns_its_verifier_red(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    record, sabotage, want = SABOTAGES[name]
    addendum = copy.deepcopy(ADDENDUM)
    sabotage(addendum, monkeypatch)
    monkeypatch.setattr(la, "load", lambda: addendum)
    problems = MODULES[record].verify()
    assert any(want in p for p in problems), (name, problems)


def test_a_change_to_a_record_that_does_not_exist_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    addendum = copy.deepcopy(ADDENDUM)
    _first(addendum, ROW, "telemetry_sources")["record"] = "telemetry_source"
    monkeypatch.setattr(la, "load", lambda: addendum)
    problems = la.check()
    assert any("is no frozen record" in p for p in problems), problems
    assert any(p.endswith("/registry/14/evidence/0/sha256") for p in problems), problems
