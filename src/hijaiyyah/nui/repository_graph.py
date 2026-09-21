"""Layer 1: who imports whom, who tests whom, who reaches the hardware.

The owner's rule for this layer is the whole of its design: *"Seluruh edge
harus berasal dari import nyata, pemanggilan nyata, referensi nyata, path
nyata -- bukan inferensi LLM."* So every edge here carries its evidence, and
the evidence is a place you can go and look:

    imports    an `import` statement, parsed with `ast`, resolved to a file
               in this repository. Line number recorded.
    mentions   a repo path written inside a file -- "rtl/programs/loader.hasm"
               in a docstring, an `.include` in HASM, a `$readmemh` in
               Verilog. Line number recorded. That is what relates freeze.py
               to loader.hasm: not a call, a citation, and it is labelled as
               a citation. A BARE filename counts too, but only when exactly
               one file in the tree carries that name -- "loader.hasm"
               resolves, "features.py" does not, and the ambiguous ones are
               counted rather than guessed at.
    verifies   a fact from layer 0 pointing at what proves it.

Two relations are DERIVED and named so, because they are questions rather
than edges: `verified_by` is the import edges whose source lives under
tests/, and `impact_of` walks import edges backwards to their transitive
closure. Both are computed from the edges above, never asserted.

-- what this graph does not have -----------------------------------------
Call edges. `ast` can see that a module imports another; seeing which
FUNCTION calls which, across a dynamic language, needs more than a parse and
would be the first inference in a graph built to contain none. The owner's
example lists "siapa memanggil siapa", and it is not here; saying so is the
difference between a gap and a lie.
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from .repository_index import ROOT, Node, index, resolve

EDGE_KINDS = ("imports", "mentions", "verifies")
#: A repo path written inside a file. Anchored on a known top directory so
#: that "features.py" alone -- which could be any of several -- is not guessed.
PATH_IN_TEXT = re.compile(
    r"\b((?:src|tests|rtl|NUI|facts|docs|cosmictera|cosmictera-build|kabah|hijrah)"
    r"/[\w./-]+\.(?:py|v|hasm|json|md|hex|txt|vh))")
#: HASM's own include, which is a real dependency and not a citation.
HASM_INCLUDE = re.compile(r'^\s*\.include\s+"([\w./-]+)"', re.MULTILINE)
#: A bare filename. Resolved only when the tree holds exactly one of them.
BARE_NAME = re.compile(r"\b([\w-]+\.(?:py|v|hasm|vh))\b")


@dataclass(frozen=True)
class Edge:
    """One relation, once. A file that names another on forty lines has one
    relation to it, not forty; `evidence` keeps the first place to look and
    `times` how often it recurs. Counting the occurrences instead turned 372
    relations into 10,736 rows that said the same things."""

    source: str
    target: str
    kind: str
    evidence: str      # "import, line 12" / "line 40" / "pytest node"
    times: int = 1

    def __str__(self) -> str:
        more = f", x{self.times}" if self.times > 1 else ""
        return f"{self.source} -{self.kind}-> {self.target}  ({self.evidence}{more})"


def _import_edges(node: Node, text: str) -> list[Edge]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    edges = []
    for item in ast.walk(tree):
        names: list[str] = []
        # The `else: continue` is what lets `item.lineno` be read below: after
        # it, the loop body only ever holds an Import or an ImportFrom, and
        # both carry a line number. mypy caught the version without it.
        if isinstance(item, ast.Import):
            names = [a.name for a in item.names]
        elif isinstance(item, ast.ImportFrom):
            if item.level:                      # relative: resolve on the package
                package = node.module or node.path
                parts = package.split(".")[:-item.level] if node.module else []
                base = ".".join(parts + ([item.module] if item.module else []))
                names = [f"{base}.{a.name}" for a in item.names] or [base]
            elif item.module:
                names = [f"{item.module}.{a.name}" for a in item.names]
        else:
            continue
        for name in names:
            target = resolve(name)
            if target and target != node.path:
                edges.append(Edge(node.path, target, "imports",
                                  f"import, line {item.lineno}"))
    return edges


@lru_cache(maxsize=1)
def _unique_basenames() -> dict[str, str]:
    """basename -> path, for the names only one file in the tree carries."""
    seen: dict[str, list[str]] = defaultdict(list)
    for path in index():
        seen[path.rsplit("/", 1)[-1]].append(path)
    return {name: paths[0] for name, paths in seen.items() if len(paths) == 1}


def _mention_edges(node: Node, text: str, nodes: dict[str, Node]) -> list[Edge]:
    edges = []
    unique = _unique_basenames()
    for number, line in enumerate(text.splitlines(), 1):
        hits = set(PATH_IN_TEXT.findall(line))
        for hit in hits:
            if hit in nodes and hit != node.path:
                edges.append(Edge(node.path, hit, "mentions", f"line {number}"))
        for bare in BARE_NAME.findall(line):
            target = unique.get(bare)
            if target and target != node.path and target not in hits:
                edges.append(Edge(node.path, target, "mentions",
                                  f"line {number}, unique name"))
    if node.kind == "hasm":
        for name in HASM_INCLUDE.findall(text):
            target = f"rtl/programs/{name}"
            if target in nodes:
                edges.append(Edge(node.path, target, "mentions", ".include"))
    return edges


def _fact_edges(nodes: dict[str, Node]) -> list[Edge]:
    from .facts import load
    edges = []
    for fact in load():
        if fact.path is None:
            continue
        source = fact.path.relative_to(ROOT).as_posix()
        for cited in fact.source + fact.evidence:
            if cited in nodes:
                edges.append(Edge(source, cited, "verifies", fact.status))
        method = fact.verification_method
        if fact.kind == "pytest":
            target = str(method["node"]).split("::")[0]
            if target in nodes:
                edges.append(Edge(source, target, "verifies", "pytest node"))
    return edges


@dataclass(frozen=True)
class Graph:
    nodes: dict[str, Node]
    edges: tuple[Edge, ...]

    def out(self, path: str, kind: str | None = None) -> list[Edge]:
        return [e for e in self.edges
                if e.source == path and (kind is None or e.kind == kind)]

    def into(self, path: str, kind: str | None = None) -> list[Edge]:
        return [e for e in self.edges
                if e.target == path and (kind is None or e.kind == kind)]

    def depends_on(self, path: str) -> list[str]:
        return sorted({e.target for e in self.out(path, "imports")})

    def used_by(self, path: str) -> list[str]:
        return sorted({e.source for e in self.into(path, "imports")})

    def verified_by(self, path: str) -> list[str]:
        """Tests that import it -- derived from import edges, not asserted."""
        return sorted({e.source for e in self.into(path, "imports")
                       if self.nodes[e.source].kind == "test"})

    def hardware_links(self, path: str) -> list[str]:
        """Everything under rtl/ this file names, and everything under rtl/
        that names it."""
        out = {e.target for e in self.out(path) if e.target.startswith("rtl/")}
        out |= {e.source for e in self.into(path) if e.source.startswith("rtl/")}
        return sorted(out)

    def impact_of(self, path: str) -> list[str]:
        """Tests that would have to fail if this file broke: every test that
        reaches it through import edges, at any depth."""
        reverse: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            if edge.kind == "imports":
                reverse[edge.target].add(edge.source)
        seen, frontier = set(), {path}
        while frontier:
            current = frontier.pop()
            for source in reverse[current]:
                if source not in seen:
                    seen.add(source)
                    frontier.add(source)
        return sorted(p for p in seen if self.nodes[p].kind == "test")

    def facts_from_the_board(self) -> list[str]:
        from .facts import load
        return sorted(f.fact_id for f in load() if f.kind == "board")

    def describe(self, path: str) -> str:
        node = self.nodes[path]
        mentions = sorted({e.target for e in self.out(path, "mentions")})
        cited_by = sorted({e.source for e in self.into(path, "verifies")})
        lines = [f"Node:        {node.path}  [{node.kind}]"]
        for label, items in (("Depends On", self.depends_on(path)),
                             ("Used By", self.used_by(path)),
                             ("Verified By", self.verified_by(path)),
                             ("Mentions", mentions),
                             ("Hardware Link", self.hardware_links(path)),
                             ("Facts Citing It", cited_by)):
            if items:
                lines.append(f"{label}:")
                lines += [f"    {item}" for item in items]
        return "\n".join(lines)


@lru_cache(maxsize=1)
def build() -> Graph:
    nodes = index()
    edges: list[Edge] = []
    for node in nodes.values():
        if node.kind == "fact":
            continue
        text = (ROOT / node.path).read_text(encoding="utf-8", errors="replace")
        if node.kind in ("python", "test"):
            edges += _import_edges(node, text)
        edges += _mention_edges(node, text, nodes)
    edges += _fact_edges(nodes)
    return Graph(nodes=nodes, edges=collapse(edges))


def collapse(edges: list[Edge]) -> tuple[Edge, ...]:
    """One edge per (source, target, kind), keeping the first evidence and
    counting the rest. `from x import a, b, c` is one relation, and so is a
    module named on forty lines of a docstring."""
    first: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        key = (edge.source, edge.target, edge.kind)
        if key in first:
            kept = first[key]
            first[key] = Edge(kept.source, kept.target, kept.kind,
                              kept.evidence, kept.times + 1)
        else:
            first[key] = edge
    return tuple(first.values())


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", help="a repo-relative path to describe")
    ap.add_argument("--impact", action="store_true",
                    help="list the tests that would have to fail")
    args = ap.parse_args(argv)
    graph = build()
    if args.path is None:
        kinds: dict[str, int] = {}
        for edge in graph.edges:
            kinds[edge.kind] = kinds.get(edge.kind, 0) + 1
        print(f"{len(graph.nodes)} nodes, {len(graph.edges)} edges")
        for kind, count in sorted(kinds.items()):
            print(f"  {kind:<10} {count}")
        return 0
    if args.path not in graph.nodes:
        print(f"{args.path} is not a node")
        return 1
    print(graph.describe(args.path))
    if args.impact:
        print("Tests That Must Fail If It Breaks:")
        for test in graph.impact_of(args.path):
            print(f"    {test}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
