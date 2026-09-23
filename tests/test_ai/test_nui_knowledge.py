"""NUI's knowledge base and the OFF database, held to their sources.

A knowledge answer is only as good as the walk back from it, so the test that
matters is that every item cites a place that exists -- a file, and a line in
it when it names one -- and sits in the domain that reads that place: the
owner's seven, HC HISA RTL OFF PAPAN NUI HOST. Then the owner's questions are asked --
PRINT, loader.hasm, HALT, a letter, a keyword -- and their answers must hold
what the layers measured. The OFF database must be OFF.md read, not a second
copy of it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode  # noqa: E402
from hijaiyyah.nui import knowledge, off_db  # noqa: E402

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


def test_the_domains_are_the_owners_seven() -> None:
    assert list(knowledge.DOMAINS) == DOMAINS


def test_host_holds_nothing_until_a_collector_measures() -> None:
    """K-6: no HOST fact before a collector has measured it. HOST reads
    nowhere, so an item filed there fails the domain test below; the host
    question still answers `unknown`, with the plan kept under NUI."""
    assert knowledge.DOMAINS["HOST"] == ()
    a = knowledge.query("host services")
    assert a["HOST"] == [] and a["unknown"]
    row, = [q for q in CONTRACT["questions"] if q["query"] == "host services"]
    assert row["answers_in"] == [] and row["answers_in_when_measured"] == ["HOST"]
    assert all(d in knowledge.DOMAINS for d in row["answers_in_when_measured"])


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
    if row["status"] in ("sebagian", "menunggu Lapis 5"):
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
    """Committed records only: the 72-hour run in progress is not read."""
    a = knowledge.query("board latest")
    families = {i["family"] for i in a["PAPAN"] if i["what"] == "latest record"}
    assert {"burn-in", "attack-lab"} <= families
    assert all("20260921T053430Z" not in i["source"] for i in a["PAPAN"])
    assert _one(a["PAPAN"], "latest dated section")["source"].startswith(
        "cosmictera-build/PAPAN.md:")


def test_which_services_the_host_runs_is_not_known_and_says_so() -> None:
    a = knowledge.query("host services")
    assert "no Ubuntu host" in a["unknown"][0]
    assert {i["name"] for i in a["NUI"]} == {"systemd_overview", "journal"}


# -- the OFF database -------------------------------------------------------------


def test_the_database_is_off_md_read_not_written() -> None:
    assert json.loads(off_db.DB.read_text(encoding="utf-8")) == off_db.build()


def test_the_database_holds_every_entry_and_invents_no_name() -> None:
    records = off_db.build()
    headings = [line for line in off_db.OFF.read_text(encoding="utf-8").splitlines()
                if line.startswith("### ")]
    assert len(records) == len(headings) == 10
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
