"""NUI's knowledge base and the OFF database, held to their sources.

A knowledge answer is only as good as the walk back from it, so the test that
matters is that every item cites a place that exists -- a file, and a line in
it when it names one -- and sits in the domain that reads that place: the
owner's seven, HC HISA RTL OFF PAPAN NUI HOST. Then the owner's questions are asked --
PRINT, loader.hasm, HALT, a letter, a keyword -- and their answers must hold
what the layers measured. The OFF database must be OFF.md read, not a second
copy of it.

HOST reads only observations in the K-11 store, never facts/ (P8.5, 26
September 2026). Every test here sees an empty store unless it builds one
itself through layer5.record(), so what this file holds does not depend on
the machine it runs on. A HOST item must walk back to its run, collector,
evidence file, time and SHA-256, and an observation whose evidence no longer
matches its hash is refused, not answered from.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode  # noqa: E402
from hijaiyyah.nui import knowledge, layer5, off_db  # noqa: E402

DOMAINS = ["HC", "HISA", "RTL", "OFF", "PAPAN", "NUI", "HOST"]
KEYS = {"query", "kind", "subject", *DOMAINS, "tests", "unknown"}
CONTRACT = json.loads((ROOT / "NUI" / "spec" / "query_contract.json").read_text(encoding="utf-8"))
QUERIES = ["opcode PRINT", "opcode HALT", "opcode ADD", "program loader.hasm",
           "program rtl/programs/test_codex.hasm", "off OFF-PRINT-SILICON", "letter ج",
           "letter Kaf", "hc متغير", "hc cetak", "hc if", "hc read_file",
           "file src/hijaiyyah/nui/board_parity.py",
           *[q["query"] for q in CONTRACT["questions"]]]


def _exists(source: str) -> bool:
    path = source.partition("#")[0]
    if ":" in path and path.rsplit(":", 1)[1].isdigit():
        path, line = path.rsplit(":", 1)
        lines = (ROOT / path).read_text(encoding="utf-8", errors="replace").splitlines()
        return (ROOT / path).is_file() and 1 <= int(line) <= len(lines)
    return (ROOT / path).exists()


@pytest.fixture(autouse=True)
def _empty_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    where = tmp_path / "observations"
    where.mkdir()
    monkeypatch.setattr(layer5, "store", lambda: where)
    return where


def test_the_domains_are_the_owners_seven() -> None:
    assert list(knowledge.DOMAINS) == DOMAINS


def test_host_reads_observations_and_nothing_else_reads_them() -> None:
    """The owner's two classes of provenance (P8.5): facts/ is sealed
    engineering knowledge and NUI's; observations/ is runtime HOST evidence and
    HOST's alone. Neither domain may read the other's place."""
    assert knowledge.DOMAINS["HOST"] == (r"observations/",)
    for domain, reads in knowledge.DOMAINS.items():
        takes_observation = any(re.match(r, "observations/x/raw/y.stdout") for r in reads)
        assert takes_observation == (domain == "HOST"), domain
    assert not any(re.match(r, "facts/burnin/x.json") for r in knowledge.DOMAINS["HOST"])
    assert any(re.match(r, "facts/burnin/x.json") for r in knowledge.DOMAINS["NUI"])
    row, = [q for q in CONTRACT["questions"] if q["query"] == "host services"]
    assert row["answers_in"] == [] and row["answers_in_when_measured"] == ["HOST"]
    assert all(d in knowledge.DOMAINS for d in row["answers_in_when_measured"])


def test_with_no_observation_host_is_unknown_for_want_of_evidence() -> None:
    """K-14: unknown means the evidence is not enough, not that the host is
    missing -- the stale "no Ubuntu host exists yet" is gone."""
    a = knowledge.query("host services")
    assert a["HOST"] == []
    assert a["unknown"][0] == "no supporting journal/service observation"
    assert not [u for u in a["unknown"] if "no Ubuntu host" in u]
    b = knowledge.query("host host_identity")
    assert b["HOST"] == [] and b["unknown"] == [
        "no supporting HOST observation: host_identity has no run for cosmictera-layer5 in "
        "the observation store"]


@pytest.mark.parametrize("text", QUERIES)
def test_every_item_walks_back_to_a_place_that_exists(text: str) -> None:
    answer = knowledge.query(text)
    assert set(answer) == KEYS, set(answer) ^ KEYS
    cited = knowledge.sources(answer)
    assert cited, "an answer with no source"
    missing = [s for s in cited if not _exists(s)]
    assert not missing, missing


@pytest.mark.parametrize("text", QUERIES)
def test_every_item_carries_its_own_source(text: str) -> None:
    """Not merely that the sources cited exist: that no item comes without
    one. An answer with one sourced item and nine bare ones would pass the
    test above."""
    answer = knowledge.query(text)
    for key in (*DOMAINS, "tests"):
        for item in answer[key]:
            assert item.get("source"), (key, item)
            for nested in ("first", "control"):
                for inner in item.get(nested, []) if isinstance(item.get(nested), list) else []:
                    assert inner.get("source"), (key, inner)


@pytest.mark.parametrize("text", QUERIES)
def test_every_item_sits_in_the_domain_that_reads_its_source(text: str) -> None:
    """A board record filed under RTL, or a fact under HISA, would make the
    grouping a label rather than a place."""
    answer = knowledge.query(text)
    for domain, reads in knowledge.DOMAINS.items():
        for item in answer[domain]:
            parts = item["source"].split(", ")
            assert any(re.match(r, part) for part in parts for r in reads), (domain, item)


def _one(items: list, what: str) -> dict:
    found = [i for i in items if i.get("what") == what]
    assert len(found) == 1, (what, items)
    return found[0]


def test_what_is_known_about_print() -> None:
    """Interpreter and RTL agree; the board differs on the three recorded
    ladder values; the fact, the OFF entry and HC's println are all found,
    each in its own domain."""
    a = knowledge.query("opcode PRINT")
    assert _one(a["RTL"], "parity")["rtl"] == "PARITY"
    assert _one(a["PAPAN"], "board")["board"] == "MISMATCH"
    assert {b["value"] for b in a["PAPAN"] if b["what"] == "board mismatch"} == {
        1 << 23, 1 << 25, 1 << 31}
    assert "hisa.print_cannot_render_large_values" in {f["fact_id"] for f in a["NUI"]}
    assert "OFF-PRINT-SILICON" in {o["id"] for o in a["OFF"]}
    assert _one(a["HISA"], "execution")["programs"] > 0
    assert _one(a["HISA"], "definition")["value"] == "0xA0"
    assert _one(a["HC"], "dictionary")["concept"] == "PRINT"


def test_what_is_known_about_loader_hasm_is_how_it_hands_over() -> None:
    a = knowledge.query("program loader.hasm")
    with_payload = next(e for e in a["HISA"]
                        if e["scenario"] == "rtl/programs/loader.hasm#with-payload")["control"]
    assert [(c["kind"], c["target"].split("@")[0], c["source"]) for c in with_payload[-3:]] == [
        ("WRITES", "mmio:TRAP_EPC", "rtl/programs/loader.hasm:71"),
        ("WRITES", "mmio:TRAP_MODE", "rtl/programs/loader.hasm:73"),
        ("RESUMES", "pc:0x040", "rtl/programs/loader.hasm:74")]
    assert a["PAPAN"], "PAPAN.md names loader.hasm"


def test_what_is_known_about_halt_includes_the_word_behind_it() -> None:
    a = knowledge.query("opcode HALT")
    assert _one(a["RTL"], "parity")["rtl"] == "MISMATCH"
    assert a["HC"] == [], "HALT closes every compiled program; it is no keyword's"
    keys = {o["key"] for o in a["OFF"]}
    assert "instruksi-sesudah-berhenti-ikut-menulis-register" in keys


def test_what_is_known_about_a_letter_comes_from_the_registry() -> None:
    """Jim, asked by character or by name: the registry's face periods, the
    literal HC refuses as a name, and the instruction that adds its codex."""
    for subject in ("ج", "Jim"):
        a = knowledge.query(f"letter {subject}")
        face = _one(a["NUI"], "registry")["face"]
        assert (face["gf2"]["period"], face["gf5"]["period"]) == (31, 3124)
        literal = _one(a["HC"], "letter literal")
        assert literal["compiles_to"] == "HLOAD H0, #5" and literal["as_a_name"]
        assert _one(a["HISA"], "letter instruction")["word"] == "0xe4000000"


def test_what_is_known_about_a_keyword_in_any_of_its_three_forms() -> None:
    for word in ("let", "متغير", "variabel", "VARIABLE"):
        a = knowledge.query(f"hc {word}")
        assert _one(a["HC"], "dictionary")["hc"] == "let"
        assert _one(a["HC"], "lowering")["reaches_hisa"] is True
    a = knowledge.query("hc jika")
    assert _one(a["HC"], "lowering")["reaches_hisa"] is False
    a = knowledge.query("hc cetak")
    assert _one(a["NUI"], "usr")["ACTION"] == "PRINT"
    a = knowledge.query("hc read_file")
    assert _one(a["HC"], "not HC")["name"] == "read_file"


def test_an_unknown_subject_says_so_rather_than_guessing() -> None:
    for text in ("opcode NOSUCH", "program nosuch.hasm", "off OFF-NOSUCH", "letter X",
                 "hc nosuch"):
        assert knowledge.query(text)["unknown"], text
    for text in ("term NOSUCH", "file nosuch.txt", "rtl nosuch_module", "board today"):
        assert knowledge.query(text)["unknown"], text
    with pytest.raises(ValueError, match="opcode, program, off, letter, hc, term, file, rtl"):
        knowledge.query("word ب")


# -- the owner's seven questions ------------------------------------------------------


@pytest.mark.parametrize("row", CONTRACT["questions"], ids=lambda r: r["query"])
def test_the_query_contract_answers_as_it_says(row: dict) -> None:
    """Each of the owner's questions, asked as its query, answers where the
    contract says it does -- and one that waits says so in `unknown` -- and
    the test named as its verification exists."""
    a = knowledge.query(row["query"])
    for domain in row["answers_in"]:
        assert a[domain], (row["query"], domain)
    if row["status"] in ("sebagian", "unknown"):
        assert a["unknown"], row["query"]
    if row["status"] == "dijawab":
        assert not [u for u in a["unknown"] if "not a" in u], a["unknown"]
    path, _, name = row["verification"].partition("::")
    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), row["verification"]


def test_what_hcpu_is_comes_from_the_glossary() -> None:
    item = _one(knowledge.query("term HCPU")["NUI"], "term")
    assert item["Kepanjangan"] == "Hijaiyyah Core Processing Unit"
    assert item["source"].startswith("teknologi/ISTILAH.md:")


def test_what_an_opcode_does_is_its_definition_and_its_specification_row() -> None:
    a = knowledge.query("opcode PRINT")
    assert _one(a["HISA"], "definition")["does"] == "Print value from GPR"
    assert any("Print GPR[S1]" in s["text"] for s in a["HISA"] if s["what"] == "specification")


def test_what_a_program_calls_is_each_call_with_its_line() -> None:
    """Every call is checked against the line it cites, not trusted."""
    a = knowledge.query("program rtl/programs/shell.hasm")
    calls = [c for c in a["HISA"] if c["what"] == "calls"]
    assert calls
    lines = (ROOT / "rtl/programs/shell.hasm").read_text(encoding="utf-8").splitlines()
    for c in calls:
        line = int(c["source"].rsplit(":", 1)[1])
        assert "CALL" in lines[line - 1] and c["label"] in lines[line - 1], c


def test_what_an_rtl_module_instantiates_and_what_instantiates_it() -> None:
    a = knowledge.query("rtl hcpu_top")
    made = {(i["module"], i["instance"]) for i in a["RTL"] if i["what"] == "instantiates"}
    assert ("hcpu_fetch", "instance u_fetch") in made
    by = [(i["module"], i["source"]) for i in a["RTL"] if i["what"] == "instantiated by"]
    assert ("tb_parity", "rtl/tb/tb_parity.v") in by
    assert len(by) == len(set(by)), "a module with two homes is listed once"


def test_what_the_board_last_measured_is_what_is_committed() -> None:
    """Committed records only, and nothing summarised by hand: the 72-hour run
    closed on 24 September 2026 and its artefacts are committed, so it is the
    latest burn-in now -- read from the run's own summary, not from a page."""
    from hijaiyyah.nui.repository_index import tracked

    a = knowledge.query("board latest")
    records = [i for i in a["PAPAN"] if i["what"] == "latest record"]
    families = {i["family"] for i in records}
    assert {"burn-in", "attack-lab"} <= families
    for item in records:
        assert tracked(item["source"]) == (item["source"],), item
    burn, = [i for i in records if i["family"] == "burn-in"]
    assert burn["stamp"] == "20260921T053430Z"
    assert (burn["ended"], burn["errors"], burn["sd_read_failures"]) == (
        "duration reached", 0, 0)
    # Since P1 the burn-in folder holds three kinds of file. A run's summary
    # and a capture's manifest answer different questions, and a manifest read
    # as a run would report a run's fields as empty, so each is its own family
    # and a record is taken for one only when its own `target` says so.
    capture, = [i for i in records if i["family"] == "burn-in-capture"]
    assert capture["source"].endswith("-capture.json")
    assert capture["bytes"] and capture["raw_sha256"]
    assert burn["source"].endswith("-72h.json")
    assert _one(a["PAPAN"], "latest dated section")["source"].startswith(
        "cosmictera-build/PAPAN.md:")


def test_which_services_the_host_runs_is_not_known_and_says_so() -> None:
    a = knowledge.query("host services")
    assert a["unknown"][0] == "no supporting journal/service observation"
    assert {i["name"] for i in a["NUI"]} == {"systemd_overview", "journal"}


# -- HOST, from observations (P8.5) ---------------------------------------------------

GUEST = {"cat /etc/os-release": 'PRETTY_NAME="Ubuntu 24.04.5 LTS"\n',
         "systemctl status --no-pager": "State: running\n"}


class _Ran:
    def __init__(self, cmd: list[str]) -> None:
        argv = " ".join(cmd[4:])
        self.returncode, self.stdout, self.stderr = 0, GUEST.get(argv, f"out of {argv}\n"), ""
        if cmd[4] == "journalctl":
            self.returncode, self.stdout = 1, ""
            self.stderr = "No journal files were opened due to insufficient permissions.\n"
        if cmd[4] == "docker":
            self.returncode, self.stdout = 127, ""
            self.stderr = "/bin/bash: line 1: docker: command not found\n"


MAIN, UJI = "cosmictera-layer5", "cosmictera-layer5-uji"


def _record(store: Path, monkeypatch: pytest.MonkeyPatch, vm: str) -> Path:
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    return layer5.record(vm, run=lambda cmd, **_: _Ran(cmd), into=store)


@pytest.fixture()
def observed(_empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One run of all eleven collectors on the main instance, written by
    record() itself -- the instance NUI's HOST answers for."""
    return _record(_empty_store, monkeypatch, MAIN)


def _manifest(run: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    return data


def test_a_host_answer_walks_back_to_run_collector_file_time_and_hash(observed: Path) -> None:
    """The owner's chain, query -> observation -> collector -> evidence file ->
    timestamp, with the SHA-256 that ties the file to the manifest."""
    a = knowledge.query("host host_identity")
    item, = a["HOST"]
    entry, = [e for e in _manifest(observed)["collectors"] if e["collector"] == "host_identity"]
    assert a["unknown"] == [] and item["provenance"] == "observation"
    assert (item["collector"], item["run_id"], item["status"]) == (
        "host_identity", observed.name, "PASS")
    assert item["observed_at"] == entry["timestamp"] and item["vm_name"] == MAIN
    path = f"observations/{MAIN}/{observed.name}/raw/host_identity.stdout"
    assert item["source"] == item["evidence"] == path
    data = layer5.resolve(item["source"]).read_bytes()
    recorded = entry["evidence"]["stdout"]["sha256"]
    assert item["evidence_sha256"] == hashlib.sha256(data).hexdigest() == recorded
    assert item["text"] == data.decode("utf-8")
    for domain, reads in knowledge.DOMAINS.items():
        for got in a[domain]:
            assert any(re.match(r, got["source"]) for r in reads), (domain, got)


def test_host_services_stays_unknown_and_shows_what_it_looked_at(observed: Path) -> None:
    """No collector's evidence answers which services run: journal cannot read
    (K-12) and `systemctl status` is not a list of every active service. The
    two observations looked at stand in HOST with their provenance."""
    a = knowledge.query("host services")
    assert a["unknown"][0] == "no supporting journal/service observation"
    status = {i["collector"]: (i["status"], i["evidence"].rsplit(".", 1)[1]) for i in a["HOST"]}
    assert status == {"systemd_overview": ("PASS", "stdout"),
                      "journal": ("unavailable_due_to_permissions", "stderr")}
    assert "insufficient permissions" in a["unknown"][1]


def test_the_eleven_are_classed_by_the_owners_rules(observed: Path) -> None:
    """K-12, K-13: nine PASS, journal unavailable for permissions, containers
    unavailable because the command is absent -- neither of the two is PASS,
    and neither is a collector error. Anything else not 0 is one."""
    got = {c["name"]: layer5.latest(c["name"], MAIN)["status"]  # type: ignore[index]
           for c in layer5.load()["collectors"]}
    assert got.pop("journal") == "unavailable_due_to_permissions"
    assert got.pop("containers") == "unavailable_command_absent"
    assert set(got.values()) == {"PASS"} and len(got) == 9
    assert layer5.outcome(2, "boom") == "collector_error"
    assert layer5.outcome(127, "something else") == "collector_error"


def _flip_byte(run: Path) -> str:
    path = run / "raw" / "host_identity.stdout"
    data = bytearray(path.read_bytes())
    data[0] ^= 1
    path.write_bytes(bytes(data))
    return "does not match its recorded SHA-256"


def _drop_file(run: Path) -> str:
    (run / "raw" / "host_identity.stdout").unlink()
    return "is missing"


def _rename_run(run: Path) -> str:
    m = _manifest(run)
    m["run_id"] = "20200101T000000Z-collectors"
    (run / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return "does not name this run"


def _forge_hash(run: Path) -> str:
    m = _manifest(run)
    for e in m["collectors"]:
        if e["collector"] == "host_identity":
            e["evidence"]["stdout"]["sha256"] = "0" * 64
    (run / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return "does not match its recorded SHA-256"


@pytest.mark.parametrize("tamper", [_flip_byte, _drop_file, _rename_run, _forge_hash],
                         ids=lambda f: f.__name__)
def test_an_observation_that_fails_its_provenance_is_refused(observed: Path, tamper: Any) -> None:
    """Evidence changed after the run, a file gone, a manifest that names
    another run, a hash that is not the file's: the observation is refused
    with the reason, and HOST says nothing from it."""
    why = tamper(observed)
    a = knowledge.query("host host_identity")
    assert a["HOST"] == []
    assert len(a["unknown"]) == 1 and why in a["unknown"][0], a["unknown"]


# -- the OFF database -------------------------------------------------------------


def test_the_database_is_off_md_read_not_written() -> None:
    assert json.loads(off_db.DB.read_text(encoding="utf-8")) == off_db.build()


def test_the_database_holds_every_entry_and_invents_no_name() -> None:
    records = off_db.build()
    headings = [line for line in off_db.OFF.read_text(encoding="utf-8").splitlines()
                if line.startswith("### ")]
    assert len(records) == len(headings) == 11
    assert [r["id"] for r in records if r["id"]] == ["OFF-PRINT-SILICON"]
    assert all(r["fixed"] is False and r["reproduced"] is None for r in records)
    assert {r["status"] for r in records} <= {"EH", "AT"}
    layered = {r["key"]: r["layer"] for r in records if r["layer"] is not None}
    assert layered == {"print-tidak-bisa-mencetak-angka-besar-di-silikon": 4,
                       "instruksi-sesudah-berhenti-ikut-menulis-register": 4}


def test_every_cited_commit_and_file_exists() -> None:
    """Asked of git directly, not of the parser that filtered them."""
    import subprocess
    cited = 0
    for record in off_db.build():
        for commit in record["evidence"]["commits"]:
            subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT,
                           check=True)
            cited += 1
        for path in record["evidence"]["files"]:
            assert (ROOT / path).exists(), path
            cited += 1
    assert cited > 0, "no entry cites anything"


def test_off_md_counts_the_missing_opcodes_one_way() -> None:
    """The summary said 24 while the entry said 21; the measure says 21."""
    text = off_db.OFF.read_text(encoding="utf-8")
    missing = len([op for op in OpCode if op not in RTL_IMPLEMENTED])
    assert f"### {missing} opcode belum di RTL" in text
    assert f"belum ada {missing} opcode" in text
    assert "top level gabungan" not in text
    assert "persisten tersimulasi, belum di papan" not in text


def test_which_program_wrote_a_file_is_read_from_the_file_or_not_claimed() -> None:
    """A JSON that names its maker is answered from its own `generated_by`; one
    that does not -- a hand-written specification -- is `unknown`, not guessed
    from who happens to mention it."""
    made = knowledge.query("file NUI/board_expected.json")
    assert _one(made["NUI"], "generated by")["by"] == "src/hijaiyyah/nui/board_parity.py"
    written = knowledge.query("file NUI/spec/usr.json")
    assert not [i for i in written["NUI"] if i["what"] == "generated by"]
    assert any("does not say what writes it" in u for u in written["unknown"])


# -- one VM, its own observations (K-16) ----------------------------------------------------


def test_the_test_instance_never_answers_for_the_main_one(
        _empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """K-16: an observation is (vm_name, run_id). The test instance's run is
    real evidence of the test instance, and HOST -- which answers for the
    main instance -- stays unknown."""
    _record(_empty_store, monkeypatch, UJI)
    assert layer5.latest("host_identity", UJI)["status"] == "PASS"  # type: ignore[index]
    assert layer5.latest("host_identity", MAIN) is None
    a = knowledge.query("host host_identity")
    assert a["HOST"] == [] and f"no run for {MAIN}" in a["unknown"][0]


def test_a_run_from_before_k16_is_read_by_the_vm_its_manifest_names(
        _empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The runs of 26 September sit at observations/<run_id>/ and are not
    moved: the vm_name in their manifests decides whose they are."""
    for vm in (UJI, MAIN):
        run = _record(_empty_store, monkeypatch, vm)
        run.rename(_empty_store / run.name)
        (_empty_store / vm).rmdir()
        if vm == UJI:
            time.sleep(1.1)  # run_ids are to the second; the next one must differ
    item, = knowledge.query("host host_identity")["HOST"]
    assert item["vm_name"] == MAIN and item["source"].count("/") == 3, item["source"]
    uji = layer5.latest("host_identity", UJI)
    assert uji["vm_name"] == UJI and uji["run_id"] != item["run_id"]  # type: ignore[index]


def test_a_run_in_one_vms_namespace_naming_another_is_refused(
        _empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A test instance's run filed under the main instance's namespace is not
    the main instance's evidence: it is refused, not answered from."""
    run = _record(_empty_store, monkeypatch, UJI)
    (_empty_store / MAIN).mkdir()
    run.rename(_empty_store / MAIN / run.name)
    seen = layer5.latest("host_identity", MAIN)
    assert seen is not None and "names another VM" in seen["rejected"]
    a = knowledge.query("host host_identity")
    assert a["HOST"] == [] and "names another VM" in a["unknown"][0]


# -- freshness and delta (Layer 5 operational baseline, 27 September 2026) -------------------


def _with_rule(monkeypatch: pytest.MonkeyPatch, seconds: Any) -> None:
    spec = layer5.load()
    spec["freshness"]["stale_after_seconds"] = seconds
    monkeypatch.setattr(layer5, "load", lambda: spec)


def test_a_host_item_carries_the_owners_freshness_fields(observed: Path) -> None:
    """observed_at, run_id, vm_name, collector and evidence_sha256 on every
    HOST item, and its freshness by the owner's rule: 300 seconds, one global
    limit. An observation just made is current."""
    item, = knowledge.query("host host_identity")["HOST"]
    for field in ("observed_at", "run_id", "vm_name", "collector", "evidence_sha256"):
        assert item[field], field
    assert layer5.load()["freshness"]["stale_after_seconds"] == 300
    assert item["freshness"] == "current" and 0 <= item["age_seconds"] <= 300


def test_known_current_known_but_stale_and_unknown(
        observed: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The owner's three states, by the explicit rule and nothing else."""
    _with_rule(monkeypatch, 3600)
    item, = knowledge.query("host host_identity")["HOST"]
    assert item["freshness"] == "current" and 0 <= item["age_seconds"] <= 3600
    _with_rule(monkeypatch, 0)
    time.sleep(0.01)
    item, = knowledge.query("host host_identity")["HOST"]
    assert item["freshness"] == "stale"
    for run in (observed.parent).iterdir():
        for f in sorted(run.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
        run.rmdir()
    a = knowledge.query("host host_identity")
    assert a["HOST"] == [] and a["unknown"], "unknown: no observation at all"


def _second_run(store: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A later run of the main instance whose process list gained one line and
    whose counters moved."""
    time.sleep(1.1)  # run_ids are to the second; the next one must differ

    class _Later(_Ran):
        def __init__(self, cmd: list[str]) -> None:
            super().__init__(cmd)
            if cmd[4:] == ["ps", "aux"]:
                self.stdout = ("USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\n"
                               "root 1 0.0 0.1 1 1 ? Ss 04:37 0:01 /sbin/init\n"
                               "root 99 0.0 0.1 1 1 ? S 05:00 0:00 /usr/bin/newcomer --x\n")
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    return layer5.record(MAIN, run=lambda cmd, **_: _Later(cmd), into=store)


def test_host_delta_says_what_appeared_with_both_runs(
        _empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run A, then run B with one more process: NUI says the process appeared
    in B, and the item walks back to both runs -- run_id, time, evidence and
    its hash. Nothing acts on it."""
    class _First(_Ran):
        def __init__(self, cmd: list[str]) -> None:
            super().__init__(cmd)
            if cmd[4:] == ["ps", "aux"]:
                self.stdout = ("USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\n"
                               "root 1 0.0 0.1 1 1 ? Ss 04:37 0:01 /sbin/init\n")
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    first = layer5.record(MAIN, run=lambda cmd, **_: _First(cmd), into=_empty_store)
    second = _second_run(_empty_store, monkeypatch)
    a = knowledge.query("host delta processes")
    item, = a["HOST"]
    assert (item["what"], item["item"]) == ("appeared", "root /usr/bin/newcomer --x")
    assert (item["from_run"], item["to_run"]) == (first.name, second.name)
    for side, run in (("from", first), ("to", second)):
        prov = item["between"][side]
        data = layer5.resolve(prov["evidence"]).read_bytes()
        assert prov["run_id"] == run.name and prov["vm_name"] == MAIN
        assert prov["evidence_sha256"] == hashlib.sha256(data).hexdigest()
    assert item["source"].startswith(f"observations/{MAIN}/{second.name}/")
    b = knowledge.query("host delta host_identity")
    assert [i["what"] for i in b["HOST"]] == ["unchanged"]


def test_a_delta_needs_two_verified_runs_of_the_same_vm(
        _empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One run of the main instance and one of the test instance are not two
    runs to compare (K-16); and a run that fails its checks is never compared."""
    _record(_empty_store, monkeypatch, UJI)
    first = _record(_empty_store, monkeypatch, MAIN)
    a = knowledge.query("host delta processes")
    assert a["HOST"] == [] and "no two runs" in a["unknown"][0]
    _second_run(_empty_store, monkeypatch)
    _flip_byte(first)
    d = layer5.delta("host_identity", MAIN)
    assert "cannot be compared" in d["unknown"] and "SHA-256" in d["unknown"]



def test_kworker_is_never_reported_as_a_new_process(
        _empty_store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The owner, 27 September 2026: kworker threads come and go with the
    kernel's work queues. They are kept, as kernel_thread_changes, and never
    counted as a process that appeared -- only kworker, not every kernel
    thread."""
    def ps(lines: str) -> Any:
        class _Ps(_Ran):
            def __init__(self, cmd: list[str]) -> None:
                super().__init__(cmd)
                if cmd[4:] == ["ps", "aux"]:
                    self.stdout = ("USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\n"
                                   + lines)
        return lambda cmd, **_: _Ps(cmd)

    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    layer5.record(MAIN, run=ps("root 1 0 0 1 1 ? Ss 04:37 0:01 /sbin/init\n"
                               "root 9 0 0 0 0 ? I 04:37 0:00 [kworker/0:0-events]\n"),
                  into=_empty_store)
    time.sleep(1.1)  # run_ids are to the second
    layer5.record(MAIN, run=ps("root 1 0 0 1 1 ? Ss 04:37 0:01 /sbin/init\n"
                               "root 12 0 0 0 0 ? I 05:00 0:00 [kworker/1:1-cgroup_free]\n"),
                  into=_empty_store)
    a = knowledge.query("host delta processes")
    assert [i["what"] for i in a["HOST"]] == ["unchanged", "kernel_thread_changes"]
    kernel = a["HOST"][1]
    assert kernel["appeared"] == ["root [kworker/1:1-cgroup_free]"]
    assert kernel["disappeared"] == ["root [kworker/0:0-events]"]
    assert kernel["between"]["to"]["run_id"] == kernel["to_run"]
