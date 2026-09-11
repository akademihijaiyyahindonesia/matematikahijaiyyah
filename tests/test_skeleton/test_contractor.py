"""SkeletonContractor (IC.1.18-1.21, Bab I) run on real pixel arrays.

Every other test that touched CSGIGraph did so through data already
extracted elsewhere -- test_letter_machines.py, test_jummal_lineage.py,
test_table_as_program.py and test_bab_satu.py all read a graph someone else
built. None of them ran SkeletonContractor.contract() itself, on a pixel
array it has to walk node-by-node. These do, on synthetic shapes chosen for
known topology (open line, closed loop, branch point) rather than a scanned
letter, so the expected node/edge counts are checked here, not assumed from
the book.
"""

from __future__ import annotations

import numpy as np

from hijaiyyah.skeleton.contractor import SkeletonContractor
from hijaiyyah.skeleton.skeletonizer import zhang_suen_thinness


def _degrees(graph) -> list[int]:
    return sorted(n.degree for n in graph.nodes)


def test_a_straight_open_line_contracts_to_two_endpoints_and_one_edge() -> None:
    """Khaṭṭ-like: no belokan, no junction -- the simplest MainPath shape."""
    line = np.zeros((3, 9), dtype=np.uint8)
    line[1, 1:8] = 1

    graph = SkeletonContractor("ا", "Alif").contract(line)

    assert len(graph.nodes) == 2
    assert _degrees(graph) == [1, 1]
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert {edge.u, edge.v} == {0, 1}
    assert len(edge.points) == 7, "one point per skeleton pixel on the line"


def test_a_closed_loop_survives_contraction_as_a_self_loop_edge() -> None:
    """A pure cycle (Qc-style loop, IB.1.10) has degree exactly 2 at every
    pixel, so Step 2's "node where degree != 2" rule finds none. Step 2b
    seeds one node per such component -- in raster order, so deterministic --
    and the trace closes back onto it as an edge with u == v.

    This used to lose the loop entirely: no node with a real degree, no edge,
    the path discarded. It matters because IC.1.11's MainPath candidate set
    includes ClosedPath, so a cycle that does not survive contraction cannot
    be a MainPath candidate at all.
    """
    ring = np.zeros((7, 7), dtype=np.uint8)
    loop_pixels = [(1, 3), (2, 2), (2, 4), (3, 1), (3, 5), (4, 2), (4, 4), (5, 3)]
    for y, x in loop_pixels:
        ring[y, x] = 1

    graph = SkeletonContractor("و", "Waw").contract(ring)

    assert len(graph.nodes) == 1
    node = graph.nodes[0]
    assert node.degree == 2, "its real degree on the cycle, not a placeholder 0"
    assert (node.y, node.x) == loop_pixels[0], "raster-first pixel of the component"

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.u == edge.v == node.id, "a closed loop is an edge onto itself"
    # Eight pixels walked, then the return to the seed closes the circuit.
    assert len(edge.points) == len(loop_pixels) + 1
    assert edge.points[0] == edge.points[-1] == (node.x, node.y)


def test_two_components_are_contracted_independently() -> None:
    """One open line and one closed loop in the same frame: the seeding rule
    must fire for the loop's component without disturbing the line's."""
    frame = np.zeros((9, 14), dtype=np.uint8)
    frame[1, 1:6] = 1
    for y, x in [(4, 10), (5, 9), (5, 11), (6, 10)]:
        frame[y, x] = 1

    graph = SkeletonContractor("x", "Both").contract(frame)

    self_loops = [e for e in graph.edges if e.u == e.v]
    open_edges = [e for e in graph.edges if e.u != e.v]
    assert len(self_loops) == 1, "the ring"
    assert len(open_edges) == 1, "the line"
    assert len([n for n in graph.nodes if n.degree == 1]) == 2, "the line's two ends"


def test_a_branch_point_produces_exactly_the_open_ends_it_should() -> None:
    """A thick T -- horizontal bar with a stem hanging off it -- run through
    the real thinning step first, not hand-drawn as a 1px skeleton, so this
    checks contract() on what skeletonizer.py actually emits rather than on
    an idealised shape contract() alone is unlikely to see.

    8-neighborhood adjacency does not resolve the branch to one clean
    degree-3 pixel here: several pixels next to the true branch point also
    end up degree >= 3, because the stem's first pixel sits diagonally
    adjacent to more than one bar pixel at once. The number of degree-1
    endpoints is the invariant that stays meaningful regardless -- a shape
    with three open arms has exactly three of them, however many nodes the
    branch itself gets split across.
    """
    thick_t = np.zeros((11, 11), dtype=np.uint8)
    thick_t[1:4, 1:10] = 1  # horizontal bar
    thick_t[3:9, 4:7] = 1   # stem hanging down from the middle
    skeleton = zhang_suen_thinness(thick_t)

    graph = SkeletonContractor("ت", "Ta").contract(skeleton)

    endpoints = [n for n in graph.nodes if n.degree == 1]
    assert len(endpoints) == 3, "one arm each: left, right, and the stem"
    # Every node the contractor found is the endpoint of at least one edge --
    # nothing is left dangling with no path connecting it to the rest.
    touched = {e.u for e in graph.edges} | {e.v for e in graph.edges}
    assert touched == {n.id for n in graph.nodes}


def test_the_graph_round_trips_through_json_as_native_python_types() -> None:
    line = np.zeros((3, 5), dtype=np.uint8)
    line[1, 1:4] = 1
    graph = SkeletonContractor("ب", "Ba", "HM-28-v1.0-HC18D").contract(line)

    data = graph.to_dict()
    assert data["letter"] == "ب"
    assert data["release"] == "HM-28-v1.0-HC18D"
    assert data["stats"] == {"node_count": 2, "edge_count": 1}
    assert all(isinstance(n["x"], int) and isinstance(n["y"], int) for n in data["nodes"])
    assert all(isinstance(p, int) for e in data["edges"] for pt in e["points"] for p in pt)

    import json

    reloaded = json.loads(graph.to_json())
    assert reloaded == data
