"""Layer 1, first half: what is in this repository, as nodes.

The graph in `repository_graph` needs something to hang edges on, and that
something has to be decided once and written down: which files are nodes,
what kind each one is, and how a dotted import name turns back into a path.

-- the scope ---------------------------------------------------------------
Nodes are code, facts, and -- since the owner's fourth directive asked for
them -- DOCUMENTATION. A document naming a module is a weaker relation than
importing it, so it gets its own edge kind in the graph (`references`) and is
never counted as an import or a code mention.

Documents come from `git ls-files`, not from walking the disk, and that is
the point: the disk holds private folders that are never committed, and the
first count of Markdown files -- 745 -- included them. The repository holds
90. Asking git is how the graph describes the repository and nothing beside
it.
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


@lru_cache(maxsize=None)
def tracked(pattern: str) -> tuple[str, ...]:
    """Every file git tracks that matches `pattern`. Empty if git is not
    available -- a caller then says it found nothing rather than guessing at
    the disk, where private folders sit beside the repository's own."""
    import subprocess
    try:
        out = subprocess.run(["git", "ls-files", pattern], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return ()
    return tuple(sorted(line for line in out.splitlines() if line))


def tracked_docs() -> tuple[str, ...]:
    """Every Markdown file git tracks."""
    return tracked("*.md")


@lru_cache(maxsize=1)
def index() -> dict[str, Node]:
    """Every node, keyed by repo-relative path."""
    nodes: dict[str, Node] = {}
    for rel in tracked_docs():
        nodes[rel] = Node(path=rel, kind="doc", module=None)
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
