"""MainPath selection — IC.1.10 to IC.1.17, Bab I, executed.

Before `skeleton/mainpath.py` existed, the uniqueness theorem was the thing
the codex was argued to stand on and the one thing no code ever ran:
Theta-hat came out of the sealed Master Table, and nothing enumerated a
candidate, scored one, or broke a tie. These tests run it on shapes whose
topology is known by construction.
"""

from __future__ import annotations

import numpy as np

from hijaiyyah.skeleton.contractor import SkeletonContractor
from hijaiyyah.skeleton.mainpath import MainPathSelector, select_mainpath
from hijaiyyah.skeleton.skeletonizer import zhang_suen_thinness


def _graph(pixels: np.ndarray, letter: str = "x"):
    return SkeletonContractor(letter, letter).contract(pixels)


def _ring_with_two_stems() -> np.ndarray:
    """A loop hanging between two stems -- the shape of a letter with Qc > 0.
    The ring reaches the stems at two junctions, so it is two arcs between the
    same pair of nodes."""
    frame = np.zeros((11, 11), dtype=np.uint8)
    for y, x in [(3, 5), (4, 4), (4, 6), (5, 3), (5, 7), (6, 4), (6, 6), (7, 5)]:
        frame[y, x] = 1
    frame[2, 5] = frame[1, 5] = 1
    frame[8, 5] = frame[9, 5] = 1
    return frame


# ── IC.1.15 / IC.1.17: the theorem itself ────────────────────────


def test_score_is_a_strict_total_order_so_the_maximum_is_unique() -> None:
    """IC.1.15 is what IC.1.17 rests on: if two candidates could score equal
    there would be no single maximum and MainPath would not be well defined.
    Checked by scoring every candidate and requiring all scores distinct."""
    shapes = {
        "line": _straight_line(),
        "T": zhang_suen_thinness(_thick_t()),
        "ring": _pure_ring(),
        "ring+stems": _ring_with_two_stems(),
    }
    for name, pixels in shapes.items():
        selector = MainPathSelector(_graph(pixels))
        candidates = selector.candidates()
        scores = [selector.score(c) for c in candidates]
        assert len(set(scores)) == len(scores), f"{name}: scores collide"


def test_every_shape_with_an_edge_selects_exactly_one_mainpath() -> None:
    for pixels in (_straight_line(), _pure_ring(), _ring_with_two_stems()):
        assert select_mainpath(_graph(pixels)) is not None


def test_a_path_and_its_reverse_are_one_candidate_not_two() -> None:
    """Enumeration finds s->t and t->s; they are the same undirected path.
    Left as two they tie with each other -- EmbKey is canonicalised under
    reversal, so the duplicate is not separated by it -- and the order stops
    being strict."""
    selector = MainPathSelector(_graph(_straight_line()))
    assert len(selector.candidates()) == 1


# ── IC.1.12: what the score actually ranks ───────────────────────


def test_the_longest_path_wins_because_len_outranks_everything() -> None:
    graph = _graph(zhang_suen_thinness(_thick_t()))
    selector = MainPathSelector(graph)
    chosen = selector.select()
    longest = max(c.length for c in selector.candidates())
    assert chosen.length == longest


def test_a_loop_does_not_force_a_closed_mainpath() -> None:
    """IC.1.14 states it and IC.1.29 gives Fa and Waw as the real cases:
    Qc > 0 does not close the MainPath, because LoopPref sits third, below
    Len. Here the ring is a two-arc cycle of length 2 while the stem-to-stem
    path is length 3, so the open path must win despite the loop existing."""
    selector = MainPathSelector(_graph(_ring_with_two_stems()))
    candidates = selector.candidates()

    assert any(c.closed for c in candidates), "the loop must be a candidate at all"
    chosen = selector.select()
    assert chosen.closed is False, "the longer open path outranks the loop"
    assert chosen.length > max(c.length for c in candidates if c.closed)


def test_a_pure_cycle_selects_the_closed_path_because_it_is_the_only_one() -> None:
    selector = MainPathSelector(_graph(_pure_ring()))
    chosen = selector.select()
    assert chosen.closed is True


def test_junctions_are_counted_from_node_degree() -> None:
    """Junc(P) is the second component and uses IC.1.19's classification:
    degree >= 3 is a junction."""
    graph = _graph(zhang_suen_thinness(_thick_t()))
    selector = MainPathSelector(graph)
    junction_ids = [n.id for n in graph.nodes if n.degree >= 3]
    assert selector.junctions(junction_ids) == len(junction_ids)
    endpoint_ids = [n.id for n in graph.nodes if n.degree == 1]
    assert selector.junctions(endpoint_ids) == 0


def test_endpoints_are_the_degree_one_nodes() -> None:
    graph = _graph(_straight_line())
    assert MainPathSelector(graph).endpoints() == [
        n.id for n in graph.nodes if n.degree == 1
    ]


# ── the shapes ───────────────────────────────────────────────────


def _straight_line() -> np.ndarray:
    line = np.zeros((3, 9), dtype=np.uint8)
    line[1, 1:8] = 1
    return line


def _pure_ring() -> np.ndarray:
    ring = np.zeros((7, 7), dtype=np.uint8)
    for y, x in [(1, 3), (2, 2), (2, 4), (3, 1), (3, 5), (4, 2), (4, 4), (5, 3)]:
        ring[y, x] = 1
    return ring


def _thick_t() -> np.ndarray:
    thick = np.zeros((11, 11), dtype=np.uint8)
    thick[1:4, 1:10] = 1
    thick[3:9, 4:7] = 1
    return thick
