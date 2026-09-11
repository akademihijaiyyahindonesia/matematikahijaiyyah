"""AGENTS.md is a map, and a map is checked against the ground it names.

It tells whoever works here next -- an agent or a person -- where the
foundation is, what the names mean, how the story went and which rules bind.
It restates as little as it can: the commits carry the story, RULES.md and
ENGINEERING_STANDARD.md carry the rules. What it does carry are pointers, and
a pointer is the kind of prose that drifts without a sound -- a hash mistyped,
a file moved. So every commit it cites must be in this history, every path it
cites must exist, and CLAUDE.md must stay an import of it rather than a second
copy of it (R1).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

PATH = re.compile(r"^[\w.\-]+(?:/[\w.\-*]+)*/?$")
EXTENSIONS = (".md", ".py", ".v", ".vh", ".hasm", ".json", ".cst", ".toml")
COMMIT = re.compile(r"`([0-9a-f]{7,40})`")


def _code_spans(text: str) -> list[str]:
    return re.findall(r"`([^`\n]+)`", text)


def _private_section() -> str:
    """Paths the notes name as never committed -- absent from a clean checkout on purpose."""
    match = re.search(r"^### Tidak di-commit.*?(?=^#)", TEXT, re.M | re.S)
    assert match, "AGENTS.md lost its 'Tidak di-commit' section"
    return match.group(0)


def _cited_paths() -> list[str]:
    private = set(_code_spans(_private_section()))
    paths = []
    for span in _code_spans(TEXT):
        if span in private or not PATH.match(span):
            continue
        if "/" in span or span.endswith(EXTENSIONS):
            paths.append(span)
    return sorted(set(paths))


def test_claude_md_is_an_import_of_agents_md_not_a_copy() -> None:
    """Claude Code reads CLAUDE.md, other agents read AGENTS.md. One text, two doors."""
    assert (ROOT / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md"


def test_the_parser_found_the_paths() -> None:
    """A parser that matched nothing would make the existence check pass vacuously."""
    paths = _cited_paths()
    assert len(paths) > 20, paths
    assert "cosmictera/RULES.md" in paths


def test_every_cited_path_exists() -> None:
    """One test, not one per path: the notes grow, and the suite total quoted in
    cosmictera-build/ should not move every time a pointer is added."""
    missing = [p for p in _cited_paths()
               if not (list(ROOT.glob(p)) if "*" in p else (ROOT / p).exists())]
    assert not missing, f"AGENTS.md cites paths that do not exist: {missing}"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=False)


def test_every_cited_commit_is_in_this_history() -> None:
    """The story is told by hash, and a hash that names nothing is a missing chapter.

    CI checks out a single commit, so there the history is simply not fetched.
    That is a property of the checkout rather than a verdict on the notes, and
    the test skips instead of failing on it.
    """
    try:
        shallow = _git("rev-parse", "--is-shallow-repository")
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if shallow.returncode != 0:
        pytest.skip("not a git checkout")
    if shallow.stdout.strip() == "true":
        pytest.skip("shallow clone: the history AGENTS.md cites is not fetched here")

    hashes = sorted(set(COMMIT.findall(TEXT)))
    assert len(hashes) > 20, hashes
    missing = [h for h in hashes
               if _git("cat-file", "-e", f"{h}^{{commit}}").returncode != 0]
    assert not missing, f"AGENTS.md cites commits that are not in this history: {missing}"
