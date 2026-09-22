"""The semantic layer's specifications, held to the owner's words and to HC.

Nothing here runs a command. What is held: the owner's own examples pass and
mean what the owner wrote; what the specification does not know is refused
by name; the catalog stays inside the read-only allowlist the owner set, read
from where the owner set it; every HC name in the dictionary exists in HC; the parser
rules rest on counts recomputed from the repository; and every entry says
whose it is -- the owner's, or a proposal waiting for the owner.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.language import KEYWORDS  # noqa: E402
from hijaiyyah.language.lexer import H28_SINGLE_CHARS  # noqa: E402
from hijaiyyah.nui import usr  # noqa: E402

#: The owner's two examples of 22 September, as the owner wrote them.
OWNER_USR = [
    {"ACTION": "READ", "OBJECT": "FILE", "TARGET": "/etc/hosts", "CONTEXT": "Ubuntu",
     "STATE": "requested"},
    {"ACTION": "PRINT", "OBJECT": "VALUE", "TARGET": "angka + harga", "CONTEXT": "HC",
     "STATE": "compiled"},
]
STATUSES = {"ditetapkan", "usulan", "dinyatakan, belum diizinkan", "diukur",
            "contoh pemilik; artinya belum ditetapkan", "ditetapkan tidak sah"}


@pytest.mark.parametrize("example", OWNER_USR)
def test_the_owners_usr_examples_are_valid(example: dict) -> None:
    assert usr.validate(example) == []


def test_every_example_the_specification_holds_is_valid() -> None:
    """Including the earlier one, rewritten in the form that now applies --
    and the owner's two are among them word for word."""
    examples = [ex["usr"] for ex in usr.load("usr")["examples"]]
    assert all(usr.validate(ex) == [] for ex in examples)
    assert all(ex in examples for ex in OWNER_USR)


def test_the_shift_to_capital_keys_is_the_one_that_applies() -> None:
    """The earlier form -- lowercase keys, `ubuntu_host` -- is refused now,
    not quietly accepted beside the new one: one name for one thing."""
    old = {"action": "READ", "object": "FILE", "target": "/var/log/syslog",
           "context": "ubuntu_host", "state": "latest"}
    problems = usr.validate(old)
    assert "unknown field: action" in problems
    assert "unknown context: ubuntu_host" in usr.validate(
        {"ACTION": "READ", "OBJECT": "FILE", "TARGET": "x", "CONTEXT": "ubuntu_host"})


def test_an_hc_context_forms_no_host_command() -> None:
    """PRINT VALUE lives in HC. Its target is an HC expression, so the argv
    rules do not reach it, and no command is formed for it."""
    hc = {"ACTION": "PRINT", "OBJECT": "VALUE", "TARGET": "-1", "CONTEXT": "HC"}
    assert usr.validate(hc) == []
    argv, why = usr.to_argv(OWNER_USR[1])
    assert argv is None and "not a host" in why
    assert usr.to_argv(OWNER_USR[0]) == (["cat", "/etc/hosts"], "ditetapkan")


@pytest.mark.parametrize("phrase", ["اقرأ ملف nginx.log", "baca file nginx.log",
                                    "read file nginx.log"])
def test_three_languages_reach_the_same_usr(phrase: str) -> None:
    """اقرأ ملف, baca file and read file -- the owner's three -- are one USR."""
    got, why = usr.parse_phrase(phrase)
    assert got == {"ACTION": "READ", "OBJECT": "FILE", "TARGET": "nginx.log"}, why


def test_the_owners_bridge_ends_at_cat_and_is_not_run() -> None:
    got, _ = usr.parse_phrase("baca file nginx.log")
    assert got is not None
    assert usr.to_argv(got) == (["cat", "nginx.log"], "ditetapkan")


@pytest.mark.parametrize("bad, reason", [
    ({"ACTION": "RUN", "OBJECT": "FILE", "TARGET": "x"}, "unknown action"),
    ({"ACTION": "read", "OBJECT": "FILE", "TARGET": "x"}, "unknown action"),
    ({"ACTION": "READ", "OBJECT": "FILE"}, "needs a target"),
    ({"ACTION": "READ", "OBJECT": "FILE", "TARGET": "-rf"}, "starts with '-'"),
    ({"ACTION": "READ", "OBJECT": "FILE", "TARGET": "-rf", "CONTEXT": "Ubuntu"}, "starts with '-'"),
    ({"ACTION": "READ", "OBJECT": "FILE", "TARGET": "a\nb"}, "newline"),
    ({"ACTION": "READ", "OBJECT": "PROCESS", "TARGET": "1"}, "takes no target"),
    ({"ACTION": "READ", "OBJECT": "FILE", "TARGET": "x", "CONTEXT": "mac"}, "unknown context"),
    ({"ACTION": "READ", "OBJECT": "FILE", "TARGET": "x", "shell": "sh"}, "unknown field"),
    ({"ACTION": "PRINT", "OBJECT": "VALUE", "CONTEXT": "HC"}, "needs a target"),
])
def test_what_the_specification_does_not_know_is_refused(bad: dict, reason: str) -> None:
    assert any(reason in p for p in usr.validate(bad)), usr.validate(bad)


def test_the_first_stage_only_reads() -> None:
    """The owner's order: layer 5 starts read-only. Every action but READ is
    named and refused."""
    stage = {a["name"]: a["stage"] for a in usr.load("usr")["actions"]}
    assert [a for a, s in stage.items() if s == 1] == ["READ"]
    for action in ("WRITE", "COPY", "MOVE", "DELETE"):
        argv, why = usr.to_argv({"ACTION": action, "OBJECT": "FILE", "TARGET": "x"})
        assert argv is None and "read-only" in why, action


def test_the_allowlist_is_read_from_where_the_owner_set_it() -> None:
    allowed, forbidden = usr.allowlist()
    assert allowed == ["ls", "find", "cat", "ps", "top", "ping", "curl", "journalctl",
                       "systemctl status", "docker ps"]
    assert "rm" in forbidden and "systemctl stop" in forbidden


def test_the_catalog_stays_inside_the_allowlist() -> None:
    """No catalog command is on the not-yet-allowed list, and every one on
    neither list is refused by name -- `ip`, which the owner wrote for READ
    NETWORK and which the owner's allowlist does not hold."""
    allowed, forbidden = usr.allowlist()
    spec = usr.load("usr")
    actions = {a["name"] for a in spec["actions"]}
    objects = {o["name"] for o in spec["objects"]}
    outside = []
    for e in usr.load("layer5_catalog")["entries"]:
        assert e["action"] in actions and e["object"] in objects, e
        assert usr._command(e["argv"], forbidden) is None, e
        if usr._command(e["argv"], allowed) is None:
            outside.append(e["argv"][0])
    assert outside == ["ip"]
    assert usr.to_argv({"ACTION": "READ", "OBJECT": "NETWORK"})[0] is None
    assert usr.unmapped_allowlist() == ["find", "top", "ping", "curl"]


def test_every_hc_name_in_the_dictionary_exists_in_hc() -> None:
    """The owner wrote `function`; HC's keyword is `fn`. The dictionary maps
    to what HC has. read_file, which HC does not have, is not HC -- the owner
    locked it so on 22 September, pending a new architecture decision. while
    is withheld from the three-language table by the same message, though HC
    already has it in English."""
    kamus = usr.load("hc_kamus")
    assert usr.measure_hc()["hc_names_missing"] == []
    assert {e["hc"] for e in kamus["entries"]} == {"let", "println", "if", "fn"}
    assert "fn" in KEYWORDS and "function" not in KEYWORDS
    assert [(x["name"], x["status"]) for x in kamus["not_hc"]] == [("read_file", "ditetapkan")]
    assert [(x["hc"], x["status"]) for x in kamus["withheld"]] == [("while", "ditetapkan")]
    assert "while" in KEYWORDS, "the withheld keyword is HC's in English; only its surfaces wait"


def test_no_keyword_is_a_single_letter() -> None:
    """A single Hijaiyyah letter stays a mathematical object (owner, 21
    September), so no keyword may be one."""
    for e in usr.load("hc_kamus")["entries"]:
        for word in (e["arabic"], e["indonesia"]):
            assert len(word) >= 2 and word not in H28_SINGLE_CHARS, word


def test_the_parser_rules_rest_on_what_the_repository_holds() -> None:
    """Recounted, not remembered: no HC program in the repository writes two
    bare letters side by side, so reading such a run as a word breaks none of
    them; no Indonesian keyword is already a name; and one Arabic keyword,
    دالة, holds a letter outside the 28 -- which is why the proposal for what
    makes an Arabic word names the letters outside them."""
    hc = usr.measure_hc()
    assert hc["adjacent_letter_pairs"] == 0 and hc["hc_sources"] == 19
    assert hc["indonesian_keywords_used_as_names"] == []
    assert hc["keywords_outside_the_28"] == ["دالة"]
    assert hc["letters"] == 28


def test_a_proposal_never_rides_on_a_decision() -> None:
    """The owner decided the five fields and the objects; which fields are
    required, and what target each object other than FILE takes, are mine."""
    spec = usr.load("usr")
    assert {f["required_status"] for f in spec["fields"]} == {"usulan"}
    targets = {o["name"]: o["target"]["status"] for o in spec["objects"]}
    assert targets.pop("FILE") == "ditetapkan"
    assert set(targets.values()) == {"usulan"}


def test_every_entry_says_whose_it_is() -> None:
    for name in ("usr", "layer5_catalog", "hc_kamus"):
        spec = usr.load(name)
        for key, items in spec.items():
            if not isinstance(items, list) or key == "open":
                continue
            for item in items:
                if isinstance(item, dict) and "status" in item:
                    assert item["status"] in STATUSES or item["status"].startswith(
                        "ditetapkan"), (name, item)
                    assert item.get("source") or item.get("source_note"), (name, item)


def test_nothing_in_the_semantic_layer_can_run_a_command() -> None:
    """Layer 5 has not started and there is no host. The module that maps USR
    to argv imports nothing that could run one."""
    text = (ROOT / "src" / "hijaiyyah" / "nui" / "usr.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith(("#", '"')))
    for name in ("subprocess", "os.system", "Popen", "pty", "os.exec"):
        assert not re.search(rf"\b{re.escape(name)}\b", code), name


def test_the_page_is_drawn_from_the_specifications() -> None:
    assert usr.PAGE.read_text(encoding="utf-8") == usr.page()


def test_the_dictionary_reads_in_the_owners_shape() -> None:
    """{CONCEPT: {hc, arabic, indonesia}} -- the owner's two entries word for
    word, and the concepts the owner has not named marked as proposals."""
    kamus = usr.kamus()
    assert kamus["PRINT"] == {"hc": "println", "arabic": "اطبع", "indonesia": "cetak"}
    assert kamus["VARIABLE"] == {"hc": "let", "arabic": "متغير", "indonesia": "variabel"}
    status = {e["concept"]: e["concept_status"] for e in usr.load("hc_kamus")["entries"]}
    assert {c for c, s in status.items() if s == "ditetapkan"} == {"PRINT", "VARIABLE"}
    assert {c for c, s in status.items() if s == "usulan"} == {"IF", "FUNCTION"}


def test_the_owners_example_compiles_to_the_owners_hisa_and_prints_30() -> None:
    """The owner wrote the HISA by hand; HC's own compiler reaches the same
    five instructions, and the interpreter -- not the compiler -- prints 30."""
    chain = usr.example_chain()
    assert chain["error"] == ""
    assert chain["same"], (chain["compiled"], chain["owner_hisa"])
    assert chain["compiled"] == ["MOVI R1, #10", "MOVI R2, #20", "ADD R3, R1, R2",
                                 "PRINT R3", "HALT"]
    assert chain["output"] == [30]


def test_which_keywords_reach_hisa_is_measured() -> None:
    """let and println compile; if and fn parse in HC but the compiler
    refuses them by name. A compiler that learns one of them changes this
    page, and this test is where that surfaces."""
    reach = {r["hc"]: (r["reaches_hisa"], r["opcodes"]) for r in usr.lowering()}
    assert reach["let"] == (True, ["MOVI"])
    assert reach["println"] == (True, ["MOVI", "PRINT"])
    for hc, node in (("if", "IfExpr"), ("fn", "FnDecl")):
        row = next(r for r in usr.lowering() if r["hc"] == hc)
        assert not row["reaches_hisa"] and node in row["error"], row


def test_the_new_surfaces_are_designed_not_read() -> None:
    """The page says the lexer does not read the Arabic and Indonesian
    keywords yet. Held here: each Arabic keyword still falls apart into
    letters, each Indonesian one is still an ordinary name."""
    indonesian = {e["hc"]: e["indonesia"] for e in usr.load("hc_kamus")["entries"]}
    for row in usr.surfaces():
        assert all(t.startswith(("HIJAIYYAH ", "IDENTIFIER ")) for t in row["arabic"]), row
        assert len(row["arabic"]) > 1, row
        assert row["indonesia"] == [f"IDENTIFIER {indonesian[row['hc']]}"], row


def test_the_owners_state_definition_is_held_as_a_proposal() -> None:
    """STATE as the actual state of the target when the action is stated, not
    a pipeline stage -- the owner's proposed definition, and the owner's own
    words: not a change the agent may make before it is locked. So it is
    recorded, and the vocabulary does not move: its example's `present` is
    not yet a STATE value."""
    spec = usr.load("usr")
    definition = spec["state_definition"]
    assert definition["status"] == "usulan pemilik, belum dikunci"
    assert {s["name"] for s in spec["states"]} == {"latest", "requested", "compiled"}
    assert usr.validate(definition["example"]) == ["unknown state: present"]


#: The owner's candidates for READ FILE /etc/hosts, 22 September 2026, and
#: what the vocabulary says today. STATE is not locked: this matrix is the test
#: that must change when it is, not a decision.
STATE_MATRIX = [
    ("REQUESTED", False), ("PRESENT", False), ("COMPILED", False), ("LATEST", False),
    ("requested", True), ("present", False), ("compiled", True), ("latest", True),
]


@pytest.mark.parametrize("state, accepted", STATE_MATRIX)
def test_state_candidates_against_todays_vocabulary(state: str, accepted: bool) -> None:
    """Capitals are refused because STATE values are lowercase by the case
    rule; `present`, the owner's proposed example, waits for the lock."""
    usr_ = {"ACTION": "READ", "OBJECT": "FILE", "TARGET": "/etc/hosts",
            "CONTEXT": "Ubuntu", "STATE": state}
    assert (usr.validate(usr_) == []) is accepted, usr.validate(usr_)
