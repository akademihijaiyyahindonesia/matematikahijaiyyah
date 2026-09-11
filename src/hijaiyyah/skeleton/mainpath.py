"""MainPath selection — IC.1.10 to IC.1.17, Bab I, executed rather than cited.

Bab I calls the uniqueness of MainPath the thing the whole codex stands on:
without it the map h -> Theta-hat is not well defined and, in the book's own
words, "seluruh sistem runtuh." The proof is short and constructive:

    IC.1.16  the candidate set is finite and non-empty
    IC.1.15  Score is a STRICT total order on it
    IC.1.17  a finite non-empty totally ordered set has exactly one maximum

Everything before this module took the conclusion on credit. Theta-hat came
out of the sealed Master Table, and no code enumerated a candidate, scored
one, or broke a tie -- the theorem was load-bearing for the argument and
absent from the program. This runs it.

WHAT SCORE IS (IC.1.12), highest priority first:

    Len(P)        edges in P                  longer wins
    -Junc(P)      junctions traversed         fewer wins
    LoopPref(P)   1 if closed, 0 if open      loops win ties
    EmbKey(P)     canonical coordinate key    injective: breaks every tie

EmbKey exists for exactly one reason: to make the order STRICT. It measures
nothing. Two distinct paths must never score equal, or the maximum is not
unique and IC.1.17 does not apply. Because a path and its reverse are the
same path, the key is canonicalised under reversal -- without that, one path
would enter the candidate set under two different keys and could tie with
itself.

WHAT THIS DOES NOT DO. Qc > 0 does not force a closed MainPath (IC.1.14):
LoopPref sits third, below Len, so a longer open path still wins. That is the
book's own rule and the reason Fa and Waw have loops but open MainPaths
(IC.1.29). The turning value is not computed here either -- this selects the
path; quantising its curvature to Theta-hat is a separate step that needs
real glyph geometry, not the graph alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

from .csgi import CSGIGraph

#: Refuse to enumerate past this many candidates. A letter skeleton is small,
#: but simple-path enumeration is exponential in the worst case and a
#: pathological graph must fail loudly rather than hang.
MAX_CANDIDATES = 200_000


@dataclass(frozen=True)
class Candidate:
    """One path through the skeleton graph, with its score components."""

    nodes: Tuple[int, ...]
    edges: Tuple[int, ...]
    closed: bool

    @property
    def length(self) -> int:
        """Len(P): edges in P, the top-priority score component."""
        return len(self.edges)


class MainPathSelector:
    """Enumerates candidates over a CSGIGraph and selects the MainPath."""

    def __init__(self, graph: CSGIGraph) -> None:
        self.graph = graph
        self._degree: Dict[int, int] = {n.id: n.degree for n in graph.nodes}
        self._coord: Dict[int, Tuple[int, int]] = {
            n.id: (n.x, n.y) for n in graph.nodes
        }
        # Adjacency as (neighbour, edge_id). A self-loop is reachable from its
        # own node and is recorded once, not twice: traversing it in either
        # direction is the same circuit.
        self._adj: Dict[int, List[Tuple[int, int]]] = {n.id: [] for n in graph.nodes}
        for edge in graph.edges:
            self._adj[edge.u].append((edge.v, edge.id))
            if edge.u != edge.v:
                self._adj[edge.v].append((edge.u, edge.id))

    # ── IC.1.12: the score ───────────────────────────────────────

    def junctions(self, node_ids: Sequence[int]) -> int:
        """Junc(P): nodes on P with degree >= 3 (IC.1.19's classification)."""
        return sum(1 for n in node_ids if self._degree.get(n, 0) >= 3)

    def emb_key(self, node_ids: Sequence[int]) -> Tuple[Tuple[int, int], ...]:
        """The canonical embedding key -- injective, and only a tiebreaker.

        Canonicalised under reversal so that a path and its mirror produce one
        key, not two. Without this a single path could be scored twice and tie
        with itself, which is precisely the case IC.1.15's strictness rules out.
        """
        forward = tuple(self._coord[n] for n in node_ids)
        backward = tuple(reversed(forward))
        return min(forward, backward)

    def score(self, candidate: Candidate) -> Tuple:
        """Score(P) as a tuple ordered lexicographically, per IC.1.12 --
        with one component the book does not have, and needs.

        IC.1.12 ends at EmbKey and IC.1.15 argues from it that the order is
        strict. That argument holds only while a path is determined by the
        nodes it visits. It is not, once two edges join the SAME pair of
        nodes: both arcs of a letter's loop visit exactly the two junctions
        it hangs from, so they share a node sequence, share coordinates, and
        therefore share an EmbKey while being different paths. Measured on a
        ring-with-two-stems: two distinct candidates, one score, and the
        maximum of IC.1.17 is then not unique.

        The canonical edge sequence is appended as a last resort, below every
        component the book defines. Anything IC.1.12 already separates orders
        exactly as before; this only decides ties it leaves open.
        """
        edges = candidate.edges
        return (
            candidate.length,
            -self.junctions(candidate.nodes),
            1 if candidate.closed else 0,
            self.emb_key(candidate.nodes),
            min(edges, tuple(reversed(edges))),
        )

    # ── IC.1.11: the candidate set ───────────────────────────────

    def endpoints(self) -> List[int]:
        """End(h): degree-1 nodes. IC.1.19 calls these the stroke ends."""
        return sorted(n for n, d in self._degree.items() if d == 1)

    def open_paths(self) -> Iterator[Candidate]:
        """Simple paths between distinct endpoints -- no node visited twice."""
        ends = set(self.endpoints())
        for start in sorted(ends):
            yield from self._walk(start, ends - {start})

    def _walk(self, start: int, targets: Set[int]) -> Iterator[Candidate]:
        stack: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = [
            (start, (start,), ())
        ]
        emitted = 0
        while stack:
            node, path, edges = stack.pop()
            if node in targets and len(path) > 1:
                yield Candidate(nodes=path, edges=edges, closed=False)
                emitted += 1
                if emitted > MAX_CANDIDATES:
                    raise RuntimeError(
                        f"candidate enumeration exceeded {MAX_CANDIDATES}"
                    )
                continue
            for neighbour, edge_id in self._adj[node]:
                if neighbour in path or neighbour == node:
                    continue
                stack.append((neighbour, (*path, neighbour), (*edges, edge_id)))

    def closed_paths(self) -> Iterator[Candidate]:
        """C(h): simple cycles.

        Self-loop edges (the shape Step 2b of the contractor preserves) are
        cycles in their own right. Multi-node cycles are found by walking back
        to the origin, and each is emitted once -- canonicalised by its node
        set so the same circuit is not counted once per starting point and
        direction.
        """
        for edge in self.graph.edges:
            if edge.u == edge.v:
                yield Candidate(nodes=(edge.u,), edges=(edge.id,), closed=True)

        seen: Set[Tuple] = set()
        for origin in sorted(self._adj):
            stack: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = [
                (origin, (origin,), ())
            ]
            while stack:
                node, path, edges = stack.pop()
                for neighbour, edge_id in self._adj[node]:
                    if neighbour == node or edge_id in edges:
                        continue
                    if neighbour == origin:
                        # A circuit closes on three or more nodes, or on TWO
                        # when the return uses a different edge -- two arcs
                        # between the same pair of junctions is a cycle, and
                        # it is the commonest way a letter's loop appears once
                        # the ring has a stem attached to it.
                        if len(path) >= 3 or (len(path) == 2 and edges):
                            circuit = (*edges, edge_id)
                            key = (frozenset(path), frozenset(circuit))
                            if key in seen:
                                continue
                            seen.add(key)
                            yield Candidate(
                                nodes=path, edges=circuit, closed=True
                            )
                        continue
                    # Only extend through nodes above the origin, so each cycle
                    # is reached from its lowest-numbered member alone.
                    if neighbour in path or neighbour < origin:
                        continue
                    stack.append((neighbour, (*path, neighbour), (*edges, edge_id)))

    @staticmethod
    def _canonical(candidate: Candidate) -> Tuple:
        """One representative per UNDIRECTED path.

        Walking s -> t and t -> s produces the same path, and the enumeration
        finds both. Left in, every open path appears twice with an identical
        score -- EmbKey is canonicalised under reversal, so the duplicate ties
        with itself rather than being separated by it -- and IC.1.15's strict
        order fails on a set that is not actually a set. Measured on the T
        fixture before this was added: 23 candidates, 13 distinct scores, and
        all ten collisions were a path against its own mirror.
        """
        forward = (candidate.nodes, candidate.edges)
        backward = (tuple(reversed(candidate.nodes)), tuple(reversed(candidate.edges)))
        return min(forward, backward)

    def candidates(self) -> List[Candidate]:
        """P(h) = OpenPath(h) union C(h), the full set IC.1.11 defines --
        as a genuine set, each undirected path present once."""
        unique: Dict[Tuple, Candidate] = {}
        for candidate in list(self.open_paths()) + list(self.closed_paths()):
            unique.setdefault(self._canonical(candidate), candidate)
        return list(unique.values())

    # ── IC.1.13 / IC.1.17: the selection ─────────────────────────

    def select(self) -> Optional[Candidate]:
        """MainPath = argmax Score. Unique when it exists (IC.1.17).

        Returns None only for a graph with no candidate at all -- a single
        isolated node, which is not a letter.
        """
        pool = self.candidates()
        if not pool:
            return None
        return max(pool, key=self.score)


def select_mainpath(graph: CSGIGraph) -> Optional[Candidate]:
    """Convenience wrapper: the MainPath of one contracted skeleton."""
    return MainPathSelector(graph).select()
