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

OWNER_USR = {"action": "READ", "object": "FILE", "target": "/var/log/syslog",
             "context": "ubuntu_host", "state": "latest"}
STATUSES = {"ditetapkan", "usulan", "dinyatakan, belum diizinkan", "diukur",
            "contoh pemilik; artinya belum ditetapkan", "ditetapkan tidak sah"}


def test_the_owners_usr_example_is_valid() -> None:
    assert usr.validate(OWNER_USR) == []


@pytest.mark.parametrize("phrase", ["اقرأ ملف nginx.log", "baca file nginx.log",
                                    "read file nginx.log"])
def test_three_languages_reach_the_same_usr(phrase: str) -> None:
    """اقرأ ملف, baca file and read file -- the owner's three -- are one USR."""
    got, why = usr.parse_phrase(phrase)
    assert got == {"action": "READ", "object": "FILE", "target": "nginx.log"}, why


def test_the_owners_bridge_ends_at_cat_and_is_not_run() -> None:
    got, _ = usr.parse_phrase("baca file nginx.log")
    assert got is not None
    assert usr.to_argv(got) == (["cat", "nginx.log"], "ditetapkan")


@pytest.mark.parametrize("bad, reason", [
    ({"action": "RUN", "object": "FILE", "target": "x"}, "unknown action"),
    ({"action": "read", "object": "FILE", "target": "x"}, "unknown action"),
    ({"action": "READ", "object": "FILE"}, "needs a target"),
    ({"action": "READ", "object": "FILE", "target": "-rf"}, "starts with '-'"),
    ({"action": "READ", "object": "FILE", "target": "a\nb"}, "newline"),
    ({"action": "READ", "object": "PROCESS", "target": "1"}, "takes no target"),
    ({"action": "READ", "object": "FILE", "target": "x", "context": "mac"}, "unknown context"),
    ({"action": "READ", "object": "FILE", "target": "x", "shell": "sh"}, "unknown field"),
])
def test_what_the_specification_does_not_know_is_refused(bad: dict, reason: str) -> None:
    assert any(reason in p for p in usr.validate(bad)), usr.validate(bad)


def test_the_first_stage_only_reads() -> None:
    """The owner's order: layer 5 starts read-only. Every action but READ is
    named and refused."""
    stage = {a["name"]: a["stage"] for a in usr.load("usr")["actions"]}
    assert [a for a, s in stage.items() if s == 1] == ["READ"]
    for action in ("WRITE", "COPY", "MOVE", "DELETE"):
        argv, why = usr.to_argv({"action": action, "object": "FILE", "target": "x"})
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
    assert usr.to_argv({"action": "READ", "object": "NETWORK"})[0] is None
    assert usr.unmapped_allowlist() == ["find", "top", "ping", "curl"]


def test_every_hc_name_in_the_dictionary_exists_in_hc() -> None:
    """The owner wrote `function`; HC's keyword is `fn`. The dictionary maps
    to what HC has, and read_file -- which HC does not have -- is listed as
    not HC, not as an entry."""
    kamus = usr.load("hc_kamus")
    assert usr.measure_hc()["hc_names_missing"] == []
    assert {e["hc"] for e in kamus["entries"]} == {"let", "println", "if", "while", "fn"}
    assert "fn" in KEYWORDS and "function" not in KEYWORDS
    assert [x["name"] for x in kamus["not_hc"]] == ["read_file"]


def test_no_keyword_is_a_single_letter() -> None:
    """A single Hijaiyyah letter stays a mathematical object (owner, 21
    September), so no keyword may be one."""
    for e in usr.load("hc_kamus")["entries"]:
        for word in (e["ar"], e["id"]):
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
