"""Layer 6 frozen, held to the git objects it reads and to what a freeze must say.

The owner's close of Layer 6, 29 September 2026: the HCPU system-level model
1c33e30 accepted GREEN, its acceptance recorded in d003cac, and Layer 6 frozen
under the tag layer6-freeze-2026-09-29-final. Every Layer 6 artefact is
derived, so the freeze reads the repository as it stood at d003cac -- git
objects, never the working tree -- and what it writes stays true for as long
as the history exists. What is held here:

    the page is drawn from the freeze, and the freeze reads back exactly;
    every Layer 6 commit is in exactly one part of the owner's scope, and the
    GREEN each part claims is the one AGENTS.md records;
    the HCPU results are the accepted ones, and the non-claims are the
    model's own -- 78 rules not covered, the HISAB discrepancy as measured;
    no RTL, bench or fingerprint changed across Layer 6, and no bitstream is
    tracked;
    and each thing a freeze must say, broken, is red.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import layer6_freeze as l6  # noqa: E402

FROZEN = json.loads(l6.MODEL.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def test_the_page_is_drawn_from_the_freeze() -> None:
    assert l6.PAGE.read_text(encoding="utf-8") == l6.page(FROZEN)


def test_the_freeze_reads_back_exactly() -> None:
    assert l6.verify() == []


def test_the_tag_and_the_commits_are_the_owners() -> None:
    c = FROZEN["commits"]
    assert FROZEN["tag"] == "layer6-freeze-2026-09-29-final"
    assert FROZEN["layer"] == {"title": "Pemahaman perangkat keras",
                               "alias": "Hardware Intelligence", "status": "FROZEN"}
    assert (c["opened_from"][:7], c["hcpu_model"][:7], c["frozen_at"][:7]) == (
        "80ea5f8", "1c33e30", "d003cac")
    assert c["in_order"] and c["layer6"] == 18
    assert _git("rev-parse", "layer5-freeze-2026-09-27-final^{commit}").strip() == c["opened_from"]


def test_every_layer6_commit_is_in_exactly_one_part() -> None:
    c = FROZEN["commits"]
    layer6 = _git("rev-list", f"{c['opened_from']}..{c['frozen_at']}").split()
    listed = [x["commit"] for p in FROZEN["scope"] for x in p["commits"]]
    assert sorted(listed) == sorted(layer6) and len(listed) == len(set(listed))
    assert [p["part"] for p in FROZEN["scope"]] == [
        "Inventaris hardware", "Sumber telemetri", "Provenance hardware",
        "Model keadaan hardware", "Korelasi hardware", "RTL sebagai fungsi",
        "Model HCPU prediktif tingkat sistem"]


def test_the_green_each_part_claims_is_recorded() -> None:
    agents = _git("show", f"{FROZEN['commits']['frozen_at']}:AGENTS.md")
    green = [x["commit"][:7] for p in FROZEN["scope"] for x in p["commits"] if x["green"]]
    assert green == [g for p in l6.SCOPE for g in p["green"]]
    for g in green:
        assert any(f"`{g}`" in para and "GREEN" in para for para in agents.split("\n\n")), g


def test_the_artefacts_are_hashed_at_the_frozen_commit() -> None:
    at = FROZEN["commits"]["frozen_at"]
    for p in FROZEN["scope"]:
        for path, sha in p["artefacts"].items():
            blob = subprocess.run(["git", "show", f"{at}:{path}"], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            assert l6.hashlib.sha256(blob).hexdigest() == sha, path


def test_the_hcpu_results_are_the_accepted_ones() -> None:
    h = FROZEN["hcpu"]
    assert (h["edges"], h["rows"], h["outputs_per_row"], h["terminal_reads"]) == (231, 232, 57, 32)
    assert all(h[k] == 0 for k in ("sampling_mismatched", "one_step_mismatches",
                                   "output_mismatches", "open_loop_mismatches",
                                   "terminal_mismatches", "ram_mismatches", "operands_moved"))
    assert (h["rules"], h["rules_fired"], h["open_loop_reached"]) == (149, 71, 231)
    assert h["bench_said"] == "Total: 15 PASS, 0 FAIL"


def test_the_non_claims_are_the_models_own() -> None:
    nc = FROZEN["non_claims"]
    assert len(nc["not_covered"]) == 78
    assert nc["hisab_discrepancy"]["measured"] == nc["hisab_discrepancy"]["recorded"] == {
        "edges": 13, "consumed": 0, "programs": [5, 10]}
    assert "ra_stack[]" in nc["opaque_state"]
    assert set(nc["subsystems_without_function"]) == {"print", "trap", "sdio", "rom", "guard",
                                                      "hisab"}


def test_nothing_of_the_rtl_moved_across_layer6() -> None:
    i = FROZEN["integrity"]
    assert i["rtl_changed_in_layer6"] == [] and i["bitstreams_tracked"] == []
    assert i["accepted_red"] == {"test": "::".join(l6.ACCEPTED_RED), "present": True}
    assert len(i["verify"]) == 9


# -- R3: what a freeze must say, broken, is red ---------------------------------------------


def _bent(**parts: Any) -> dict[str, Any]:
    return json.loads(json.dumps({**FROZEN, **parts}))


def test_commits_out_of_order_are_red() -> None:
    assert l6.check(_bent(commits={**FROZEN["commits"], "in_order": False}))


def test_a_commit_left_out_of_the_scope_is_red() -> None:
    scope = json.loads(json.dumps(FROZEN["scope"]))
    scope[5]["commits"].pop(0)
    assert any("each of Layer 6" in b for b in l6.check(_bent(scope=scope)))


def test_a_green_without_a_record_is_red(monkeypatch: pytest.MonkeyPatch) -> None:
    scope = json.loads(json.dumps(l6.SCOPE))
    scope[0]["green"] = ["cde7d77"]
    monkeypatch.setattr(l6, "SCOPE", scope)
    assert any("GREEN without a record" in b for b in l6.check(FROZEN))


def test_hcpu_results_that_moved_are_red() -> None:
    assert l6.check(_bent(hcpu={**FROZEN["hcpu"], "one_step_mismatches": 1}))


def test_an_rtl_change_in_layer6_is_red() -> None:
    bent = {**FROZEN["integrity"], "rtl_changed_in_layer6": ["rtl/hcpu_top.v"]}
    assert any("integrity" in b for b in l6.check(_bent(integrity=bent)))


def test_a_hisab_record_that_is_not_the_measurement_is_red() -> None:
    nc = json.loads(json.dumps(FROZEN["non_claims"]))
    nc["hisab_discrepancy"]["recorded"]["edges"] = 12
    assert any("HISAB" in b for b in l6.check(_bent(non_claims=nc)))


def test_a_freeze_that_drifted_is_red() -> None:
    assert l6.verify(_bent(hcpu={**FROZEN["hcpu"], "rules_fired": 70})) != []
