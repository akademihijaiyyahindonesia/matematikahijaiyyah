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
    5 October 2026; extended 2 November 2026 for Jalur A), and a second
    change with no link is still refused;
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
CAUSE2 = "004b9a0"
CAUSE_P6 = "48cf0e5"
CAUSE_P8 = "f9c8349"
CAUSE_CTHETA = "1aed5e1"
CAUSE_RECON = "95623b6"
CAUSE_HDMI = "73fc457"
FIRST, SECOND = "Makefile — target HMAC", "Makefile — lapis 3 slot UART Ka'bah"
MAKE_HDMI = "Makefile — Opsi A HDMI tanpa -nodsp"
TOP_CAP_1 = "hcpu_gowin_top.v — cap ulang opsi (a)"
TOP_CAP_2 = "hcpu_gowin_top.v — cap ulang Paket 8"
TOP_CAP_3 = "hcpu_gowin_top.v — cap ulang pasca-1aed5e1f"
TOP_MOV_1 = "hcpu_gowin_top.v — baris turun enam"
TOP_MOV_2 = "hcpu_gowin_top.v — baris turun sembilan belas"
TOP_PNR = "hcpu_gowin_top.v — angka place-and-route Paket 8"
TOP_PNR_2 = "hcpu_gowin_top.v — angka place-and-route pasca-1aed5e1f"
HCPU_TOP_1 = "hcpu_top.v — alternatif RTL A1–A3 (P6)"
HCPU_TOP_2 = "hcpu_top.v — CODEX_PROFILE dan calu_done (Paket 8)"
HCPU_PKG_1 = "hcpu_pkg.vh — alternatif RTL A1–A3 (P6)"
HCPU_PKG_2 = "hcpu_pkg.vh — CTHETA=0x4E dan HDOT=0x52"
README_OP = "teknologi/README.md — sensus 84 opcode RTL"
L4_FREEZE_OP = "NUI/layer4_freeze.json — sensus 105 opcode (CTHETA dan HDOT)"

CHAINS = (
    (HCPU_TOP_1, HCPU_TOP_2, "rtl/hcpu_top.v", CAUSE_P6, CAUSE_P8),
    (HCPU_PKG_1, HCPU_PKG_2, "rtl/hcpu_pkg.vh", CAUSE_P6, CAUSE_CTHETA),
    (TOP_MOV_1, TOP_MOV_2, "rtl/fpga/gowin/hcpu_gowin_top.v", CAUSE, CAUSE_P8),
)


def _frozen(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / la.FROZEN[name][0]).read_text(encoding="utf-8"))
    return data


def _fresh(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(json.dumps(MODULES[name].build()))
    return data


def test_the_frozen_records_are_the_objects_at_the_tag() -> None:
    """Immutable: each record, its page and its spec, byte for byte, and the tag
    object itself has not moved."""
    tag_obj = subprocess.run(["git", "rev-parse", TAG], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    tag_commit = subprocess.run(["git", "rev-parse", f"{TAG}^{{commit}}"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
    assert tag_obj == "1bb468bfaf8b643249a83dab4fac4dfabe0bf102"
    assert tag_commit == "0a3b44686b2877ed0bfa085d24650f81fd540887"
    for name, paths in la.FROZEN.items():
        for path in paths:
            held = subprocess.run(["git", "show", f"{TAG}:{path}"], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            assert (ROOT / path).read_bytes() == held, path
        assert la.problems(name) == [], name


def test_the_addendum_covers_exactly_the_drift() -> None:
    """Every pointer that moved since the freeze is named, and nothing else."""
    chained_second_ids = {SECOND, HCPU_TOP_2, HCPU_PKG_2, TOP_CAP_2, TOP_MOV_2, TOP_PNR_2}
    chained_third_ids = {TOP_CAP_3, MAKE_HDMI}
    for name in la.FROZEN:
        drift = set(_diff(_frozen(name), _fresh(name)))
        named = [c["pointer"] for c in la.changes(name)]
        assert sorted(set(named)) == sorted(drift), name
        thrice = sorted(p for p in set(named) if named.count(p) == 3)
        want_thrice = sorted(
            c["pointer"]
            for eid in chained_third_ids
            for c in _entry(ADDENDUM, eid)["changes"]
            if c["record"] == name
        )
        assert thrice == want_thrice, name
        twice = sorted(p for p in set(named) if named.count(p) == 2)
        want_twice = sorted(
            set(
                c["pointer"]
                for eid in chained_second_ids
                for c in _entry(ADDENDUM, eid)["changes"]
                if c["record"] == name
            )
            - set(thrice)
        )
        assert twice == want_twice, name
        assert all(named.count(p) in (1, 2, 3) for p in set(named)), name
    assert {n: len(la.changes(n)) for n in la.FROZEN} == {
        "hardware": 74, "telemetry_sources": 16, "hardware_provenance": 115}
    assert len(ADDENDUM["entries"]) == 18


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
    expected_causes = {
        SECOND: CAUSE2,
        MAKE_HDMI: CAUSE_HDMI,
        HCPU_TOP_1: CAUSE_P6,
        HCPU_PKG_1: CAUSE_P6,
        HCPU_TOP_2: CAUSE_P8,
        TOP_CAP_2: CAUSE_P8,
        TOP_MOV_2: CAUSE_P8,
        TOP_PNR: CAUSE_P8,
        HCPU_PKG_2: CAUSE_CTHETA,
        README_OP: CAUSE_CTHETA,
        TOP_CAP_3: CAUSE_RECON,
        TOP_PNR_2: CAUSE_RECON,
        L4_FREEZE_OP: CAUSE_RECON,
    }
    chained_ids = {
        SECOND, MAKE_HDMI, HCPU_TOP_2, HCPU_PKG_2, TOP_CAP_2, TOP_CAP_3, TOP_MOV_2, TOP_PNR_2
    }
    for e in ADDENDUM["entries"]:
        assert e["cause"] == expected_causes.get(e["id"], CAUSE), e["id"]
        assert e["reason"] and e["path"] in touched(e["cause"]), e["id"]
        assert ("after" in e) == (e["id"] in chained_ids), e["id"]
        assert e["equivalence"]["kind"] in la.KINDS, e["id"]
        assert e["changes"] and all(set(c) == {"record", "pointer", "old", "new"}
                                    and c["old"] != c["new"] for c in e["changes"]), e["id"]
    assert list(ADDENDUM["kinds"]) == list(la.KINDS)
    assert {e["equivalence"]["kind"] for e in ADDENDUM["entries"]} == set(la.KINDS)


def _show(commit: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def test_the_chain_is_written_out_and_every_link_of_it_is_checked() -> None:
    """Every multi-step chain (Makefile, hcpu_top.v, hcpu_pkg.vh, and
    hcpu_gowin_top.v whole-file, line-moved, and remeasured-header) is verified
    link by link against git objects."""
    links, unlinked = la._links(ADDENDUM)
    for first_id, second_id, path, c1, c2 in CHAINS:
        first, second = _entry(ADDENDUM, first_id), _entry(ADDENDUM, second_id)
        assert first["path"] == second["path"] == path and second["after"] == first_id
        assert ADDENDUM["entries"].index(first) < ADDENDUM["entries"].index(second)
        assert (first["cause"], second["cause"]) == (c1, c2)
        assert subprocess.run(["git", "merge-base", "--is-ancestor", c1, c2],
                              cwd=ROOT).returncode == 0
        assert links[first_id] == (None, second_id)
        assert links[second_id] == (first_id, None)
        assert unlinked[second_id] == []
        keys = [(c["record"], c["pointer"]) for c in first["changes"]]
        assert keys == [(c["record"], c["pointer"]) for c in second["changes"]]
        left = {(c["record"], c["pointer"]): c["new"] for c in first["changes"]}
        held = {(c["record"], c["pointer"]): c["old"] for c in second["changes"]}
        assert left == held
        assert _show(c1 + "^", path) == _show(TAG, path)
        assert _show(c2 + "^", path) == _show(c1, path)
        if path != "rtl/fpga/gowin/hcpu_gowin_top.v":
            assert (ROOT / path).read_bytes() == _show(c2, path)

    # 3-step whole-file insert-only chain on rtl/fpga/gowin/Makefile
    m_path = "rtl/fpga/gowin/Makefile"
    assert links[FIRST] == (None, SECOND)
    assert links[SECOND] == (FIRST, MAKE_HDMI)
    assert links[MAKE_HDMI] == (SECOND, None)
    assert unlinked[SECOND] == unlinked[MAKE_HDMI] == []
    assert _show(CAUSE + "^", m_path) == _show(TAG, m_path)
    assert _show(CAUSE2 + "^", m_path) == _show(CAUSE, m_path)
    assert _show(CAUSE_HDMI + "^", m_path) == _show(CAUSE2, m_path)
    assert (ROOT / m_path).read_bytes() == _show(CAUSE_HDMI, m_path)

    # 3-step whole-file comment-only chain on hcpu_gowin_top.v
    c_path = "rtl/fpga/gowin/hcpu_gowin_top.v"
    assert links[TOP_CAP_1] == (None, TOP_CAP_2)
    assert links[TOP_CAP_2] == (TOP_CAP_1, TOP_CAP_3)
    assert links[TOP_CAP_3] == (TOP_CAP_2, None)
    assert unlinked[TOP_CAP_2] == unlinked[TOP_CAP_3] == []
    assert _show(CAUSE + "^", c_path) == _show(TAG, c_path)
    assert _show(CAUSE_P8 + "^", c_path) == _show(CAUSE, c_path)
    assert _show(CAUSE_RECON + "^", c_path) == _show(CAUSE_P8, c_path)
    assert (ROOT / c_path).read_bytes() == _show(CAUSE_RECON, c_path)
    assert links[TOP_PNR] == (None, TOP_PNR_2)
    assert links[TOP_PNR_2] == (TOP_PNR, None)


def test_a_chain_is_never_inferred() -> None:
    """Without `after` the second entry is a pointer changed twice, and the
    record is refused before it is built."""
    addendum = copy.deepcopy(ADDENDUM)
    del _entry(addendum, MAKE_HDMI)["after"]
    assert MAKE_HDMI not in la._links(addendum)[0]
    assert sum("is changed twice" in p for p in la.problems("hardware", addendum)) == 4
    with pytest.raises(LookupError, match="the frozen record holds"):
        la.current("hardware", addendum=addendum)

    named = copy.deepcopy(ADDENDUM)
    _entry(named, MAKE_HDMI)["after"] = "Makefile — nothing"
    bad = la.problems("hardware", named)
    assert sum("is changed twice" in p for p in bad) == 4
    assert any("which is no entry written before it" in p for p in bad)

    alone = copy.deepcopy(ADDENDUM)
    alone["entries"].remove(_entry(alone, FIRST))
    del _entry(alone, SECOND)["after"]
    assert sum("at the freeze and until its cause" in p
               for p in la.problems("hardware", alone)) == 4


def test_a_chain_does_not_fork_and_does_not_reach_forward() -> None:
    addendum = copy.deepcopy(ADDENDUM)
    third = copy.deepcopy(_entry(addendum, MAKE_HDMI))
    third["id"] = "Makefile — a second continuation"
    addendum["entries"].append(third)
    links, unlinked = la._links(addendum)
    assert links[SECOND] == (FIRST, MAKE_HDMI) and third["id"] not in links
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
    return next(e for e in addendum["entries"] if e["id"] == prefix or e["id"].startswith(prefix))


def _first(addendum: dict[str, Any], prefix: str, record: str) -> dict[str, Any]:
    return next(c for c in _entry(addendum, prefix)["changes"] if c["record"] == record)


def _board_value() -> dict[str, Any]:
    return {"record": "hardware", "pointer": "/items/0/value",
            "old": _frozen("hardware")["items"][0]["value"]}


def _edit_file(monkeypatch: pytest.MonkeyPatch, path: str, edit: Callable[[bytes], bytes]) -> None:
    real = la._now
    monkeypatch.setattr(la, "_now", lambda p: edit(real(p)) if p == path else real(p))


Sabotage = Callable[[dict[str, Any], pytest.MonkeyPatch], None]
TOP, MAKE, PAPAN, ROW = TOP_CAP_1, FIRST, "PAPAN.md", "TELEMETRY.md"


def _drop(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    e = _entry(a, TOP_CAP_3)
    e["changes"] = [c for c in e["changes"] if c["pointer"] != "/items/3/source/sha256"]


def _no_line(data: bytes) -> bytes:
    return b"\n".join(ln for ln in data.split(b"\n") if not ln.startswith(b".PHONY"))


def _fork_line_moved(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    fork = copy.deepcopy(_entry(a, TOP_MOV_2))
    fork["id"] = "hcpu_gowin_top.v — forked line-moved"
    a["entries"].append(fork)


def _sabotage_remeasured_no_report(a: dict[str, Any], mp: pytest.MonkeyPatch) -> None:
    _edit_file(
        mp,
        "rtl/fpga/gowin/hcpu_gowin_top.v",
        lambda d: d.replace(b"15,367 / 20,736", b"15,360 / 20,736", 1),
    )


def _sabotage_remeasured_bad_fp(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    _entry(a, TOP_PNR)["equivalence"]["rtl_fingerprint"] = "a" * 64


def _sabotage_remeasured_pattern_mismatch(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    items = _entry(a, TOP_PNR)["equivalence"]["items"]
    items["fpga_lut4"]["pnr_pattern"] = r"LUT4:\s+15744/\s+20736\s+75%"


def _sabotage_remeasured_bad_report_sha(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    _entry(a, TOP_PNR)["equivalence"]["reports"]["pnr_sha256"] = "b" * 64


def _sabotage_remeasured_no_archive(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    """An archive that is not there must be red, not skipped -- and not found
    somewhere else either: the first version fell back to a session scratchpad."""
    reports = _entry(a, TOP_PNR)["equivalence"]["reports"]
    reports["archive_dir"] = "~/cosmictera-layer5/paket8-codex-profile2/not-here"


def _sabotage_claim_unchanged_val(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    _entry(a, HCPU_PKG_1)["changes"].append({
        "record": "hardware",
        "pointer": "/items/14/value",
        "old": "37",
        "new": "38",
    })


def _sabotage_claim_unchanged_status(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    _entry(a, HCPU_PKG_1)["changes"].append({
        "record": "hardware_provenance",
        "pointer": "/claims/14/status",
        "old": "MEASURED",
        "new": "SIMULATED",
    })


def _sabotage_claim_unchanged_spec(a: dict[str, Any], mp: pytest.MonkeyPatch) -> None:
    _edit_file(
        mp,
        "NUI/spec/hardware_inventory.json",
        lambda d: d.replace(b"5-stage pipeline", b"6-stage pipeline", 1),
    )


def _sabotage_claim_unchanged_source_line(a: dict[str, Any], _: pytest.MonkeyPatch) -> None:
    _entry(a, HCPU_PKG_1)["changes"].append({
        "record": "hardware",
        "pointer": "/items/14/source/line",
        "old": 185,
        "new": 186,
    })


def _sabotage_claim_unchanged_anchor(a: dict[str, Any], mp: pytest.MonkeyPatch) -> None:
    _edit_file(
        mp,
        "rtl/hcpu_top.v",
        lambda d: d.replace(b"hcpu_writeback u_writeback (", b"hcpu_writeback u_wb_renamed (", 1),
    )


SABOTAGES: dict[str, tuple[str, Sabotage, str]] = {
    "a change dropped": ("hardware", _drop, "/items/3/source/sha256"),
    "an old value forged": ("hardware", lambda a, _: _first(a, TOP, "hardware").update(
        old="0" * 64), "the frozen record holds"),
    "a new value forged": ("hardware", lambda a, _: _first(a, TOP_CAP_3, "hardware").update(
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
    # -- the chain (owner, 5 October 2026 & 2 November 2026) ------------------------
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
    "a link on evidence that is not chainable": (
        "telemetry_sources", lambda a, _: _entry(a, ROW).update(after=_entry(a, TOP)["id"]),
        "a chain is only for a whole file's hash or line-moved"),
    "a last link that is not the file now": ("hardware", lambda a, mp: _edit_file(
        mp, "rtl/fpga/gowin/Makefile", lambda d: d + b"\n# one more line\n"),
        "at its cause and now"),
    "a frozen record edited": ("hardware", lambda a, mp: _edit_file(
        mp, "NUI/hardware_inventory.json", lambda d: d + b"\n"), "is not the object frozen at"),
    "a frozen page edited": ("telemetry_sources", lambda a, mp: _edit_file(
        mp, "NUI/TELEMETRY_SOURCES.md", lambda d: d + b"\n"), "is not the object frozen at"),
    # -- R3 for chained line-moved (Jalur A) ----------------------------------------
    "line-moved chain text altered by one char": (
        "hardware",
        lambda a, mp: _edit_file(
            mp, "rtl/fpga/gowin/hcpu_gowin_top.v",
            lambda d: d.replace(b"parameter BAUD    = 115200", b"parameter BAUD    = 115201", 1),
        ),
        "after 'hcpu_gowin_top.v — baris turun enam' is not",
    ),
    "line-moved chain linked to whole-file predecessor": (
        "hardware",
        lambda a, _: _entry(a, TOP_MOV_2).update(after=TOP_CAP_1),
        "cannot link 'comment-only' to 'line-moved'",
    ),
    "line-moved chain that forks": (
        "hardware",
        _fork_line_moved,
        "is already continued by",
    ),
    "line-moved chain with mismatched line position": (
        "hardware",
        lambda a, _: _entry(a, TOP_MOV_2)["equivalence"]["lines"].__setitem__(0, [285, 305]),
        "do not continue",
    ),
    # -- R3 for remeasured-header (Jalur A) -----------------------------------------
    "remeasured-header figure changed without new report": (
        "hardware",
        _sabotage_remeasured_no_report,
        "fpga_lut4 in rtl/fpga/gowin/hcpu_gowin_top.v (to) is",
    ),
    "remeasured-header with wrong RTL fingerprint": (
        "hardware",
        _sabotage_remeasured_bad_fp,
        "does not record RTL FINGERPRINT",
    ),
    "remeasured-header where report pattern disagrees with header": (
        "hardware",
        _sabotage_remeasured_pattern_mismatch,
        "pnr_pattern",
    ),
    "remeasured-header with mismatched report sha256": (
        "hardware",
        _sabotage_remeasured_bad_report_sha,
        "does not match pnr_sha256",
    ),
    "remeasured-header whose archive is not on this machine": (
        "hardware",
        _sabotage_remeasured_no_archive,
        "is not on this machine",
    ),
    # -- R3 for claim-unchanged (Jalur A) -------------------------------------------
    "claim-unchanged where claim value changed": (
        "hardware",
        _sabotage_claim_unchanged_val,
        "changes claim semantics or value",
    ),
    "claim-unchanged where status changed": (
        "hardware_provenance",
        _sabotage_claim_unchanged_status,
        "changes claim semantics or value",
    ),
    "claim-unchanged where spec contract changed": (
        "hardware",
        _sabotage_claim_unchanged_spec,
        "is not the object frozen at",
    ),
    "claim-unchanged where source line changed": (
        "hardware",
        _sabotage_claim_unchanged_source_line,
        "changes claim semantics or value",
    ),
    "claim-unchanged disguising architectural anchor change": (
        "hardware",
        _sabotage_claim_unchanged_anchor,
        "anchor line 'hcpu_writeback u_writeback (' missing",
    ),
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
