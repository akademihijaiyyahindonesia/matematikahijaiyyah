"""Layer 1, first half: what is in this repository, as nodes.

The graph in `repository_graph` needs something to hang edges on, and that
something has to be decided once and written down: which files are nodes,
what kind each one is, and how a dotted import name turns back into a path.

-- the scope, and why it is not everything -------------------------------
Nodes are CODE and FACTS -- Python, HASM, Verilog, and the JSON facts of
layer 0. Not the 745 Markdown files: a document mentioning a module is a
weaker relation than importing it, and mixing the two would put a citation
and a call on the same footing. Documents are already held to the tree by
tests/test_integrity/ (test_agent_notes.py checks every file a note names
exists), so nothing is unguarded -- it is just not part of this graph yet,
and the page says so rather than implying coverage it does not have.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
#: Where a node may come from, and what it is called.
TREES = {
    "src": ("python",),
    "tests": ("test",),
    "rtl": ("python", "hasm", "verilog"),
    "NUI": ("python",),
    "facts": ("fact",),
}
SUFFIX_KIND = {".py": "python", ".hasm": "hasm", ".v": "verilog", ".json": "fact"}
SKIP = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache", "build", "dist"}


@dataclass(frozen=True)
class Node:
    """One file the graph can talk about."""

    path: str          # repo-relative, always with forward slashes
    kind: str          # python | test | hasm | verilog | fact
    module: str | None  # dotted name, for importable Python only

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]


def _kind(path: Path) -> str | None:
    suffix = SUFFIX_KIND.get(path.suffix)
    if suffix is None:
        return None
    top = path.relative_to(ROOT).parts[0]
    if top not in TREES:
        return None
    if top == "tests" and suffix == "python":
        return "test"
    if suffix not in TREES[top] and not (top == "tests" and suffix == "python"):
        return None
    return suffix


def _module(path: Path) -> str | None:
    """The dotted name an import would use, for files under src/."""
    rel = path.relative_to(ROOT)
    if rel.parts[0] != "src" or path.suffix != ".py":
        return None
    parts = list(rel.parts[1:])
    parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


@lru_cache(maxsize=1)
def index() -> dict[str, Node]:
    """Every node, keyed by repo-relative path."""
    nodes: dict[str, Node] = {}
    for tree in TREES:
        base = ROOT / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or SKIP & set(path.parts):
                continue
            kind = _kind(path)
            if kind is None:
                continue
            rel = path.relative_to(ROOT).as_posix()
            nodes[rel] = Node(path=rel, kind=kind, module=_module(path))
    return nodes


@lru_cache(maxsize=1)
def by_module() -> dict[str, str]:
    """Dotted module name -> path, for resolving imports."""
    return {n.module: n.path for n in index().values() if n.module}


def resolve(dotted: str) -> str | None:
    """`hijaiyyah.nui.atom` -> `src/hijaiyyah/nui/atom.py`, or None when the
    name belongs to something outside this repository (`json`, `torch`)."""
    table = by_module()
    if dotted in table:
        return table[dotted]
    # `from hijaiyyah.nui.atom import build_atoms` also resolves when the
    # tail is a name inside the module rather than a module itself.
    head = dotted.rsplit(".", 1)[0]
    return table.get(head)


def counts() -> dict[str, int]:
    out: dict[str, int] = {}
    for node in index().values():
        out[node.kind] = out.get(node.kind, 0) + 1
    return out


def main() -> int:
    for kind, count in sorted(counts().items()):
        print(f"{kind:<9} {count}")
    print(f"{'total':<9} {len(index())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
