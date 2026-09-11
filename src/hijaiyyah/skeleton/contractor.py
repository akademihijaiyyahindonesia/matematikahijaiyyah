"""Skeleton graph contraction: pixel skeleton → node/edge graph."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

import numpy as np

from .csgi import CSGIEdge, CSGIGraph, CSGINode


class SkeletonContractor:
    """Contracts a skeleton image into a CSGi graph."""

    def __init__(
        self,
        letter_hijaiyyah: str = "",
        letter_name: str = "",
        release_id: str = "",
    ) -> None:
        self.letter = letter_hijaiyyah
        self.name = letter_name
        self.release = release_id

    def contract(self, skeleton: np.ndarray) -> CSGIGraph:
        """
        Contract skeleton pixels into a graph.

        Nodes: pixels with degree != 2 (endpoints and junctions)
        Edges: polylines connecting nodes through degree-2 pixels
        """
        rows, cols = skeleton.shape
        nodes: List[CSGINode] = []
        edges: List[CSGIEdge] = []
        node_map: Dict[Tuple[int, int], int] = {}
        node_id = 0

        # ── Step 1: find all skeleton pixels and compute degrees ──
        pixel_degree: Dict[Tuple[int, int], int] = {}
        all_points: List[Tuple[int, int]] = []

        for y in range(rows):
            for x in range(cols):
                if skeleton[y, x] == 0:
                    continue
                all_points.append((int(y), int(x)))
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < rows and 0 <= nx < cols:
                            if skeleton[ny, nx] > 0:
                                count += 1
                pixel_degree[(int(y), int(x))] = count

        # ── Step 2: identify nodes (degree != 2) ─────────────────
        for (y, x), deg in pixel_degree.items():
            if deg != 2:
                node = CSGINode(
                    id=int(node_id),
                    x=int(x),
                    y=int(y),
                    degree=int(deg),
                )
                nodes.append(node)
                node_map[(y, x)] = node_id
                node_id += 1

        # ── Step 2b: a pure cycle has no node at all ─────────────
        # Every pixel on a closed loop has degree exactly 2, so Step 2 finds
        # nothing there, and Step 3 -- which iterates node_map -- would then
        # trace nothing, losing the loop entirely. That matters beyond
        # tidiness: Bab I's MainPath candidate set (IC.1.11) explicitly
        # includes ClosedPath, so a cycle has to survive contraction to be
        # selectable at all, and the nine letters with Qc > 0 are exactly the
        # ones that carry them. Seed one node per such component, taken in
        # raster order so the choice is deterministic rather than arbitrary.
        seen: Set[Tuple[int, int]] = set()
        for origin in all_points:
            if origin in seen:
                continue
            component: List[Tuple[int, int]] = []
            stack = [origin]
            seen.add(origin)
            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))
                for ddy in (-1, 0, 1):
                    for ddx in (-1, 0, 1):
                        if ddy == 0 and ddx == 0:
                            continue
                        neighbour = (cy + ddy, cx + ddx)
                        if neighbour in pixel_degree and neighbour not in seen:
                            seen.add(neighbour)
                            stack.append(neighbour)

            if any(p in node_map for p in component):
                continue

            sy, sx = min(component)  # (y, x) -- raster order
            nodes.append(
                CSGINode(
                    id=int(node_id),
                    x=int(sx),
                    y=int(sy),
                    degree=int(pixel_degree[(sy, sx)]),
                )
            )
            node_map[(sy, sx)] = node_id
            node_id += 1

        # ── Step 3: trace edges between nodes ────────────────────
        visited_edges: Set[Tuple[Tuple[int, int], ...]] = set()
        edge_id = 0

        for start_pos, start_nid in node_map.items():
            sy, sx = start_pos

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = int(sy + dy), int(sx + dx)
                    if (ny, nx) not in pixel_degree:
                        continue

                    # Trace path
                    path: List[Tuple[int, int]] = [(sx, sy), (nx, ny)]
                    current = (ny, nx)
                    prev = (sy, sx)
                    reached_node = False

                    while True:
                        # Returning to start_pos closes a loop and is a real
                        # edge (u == v), not a dead end -- but only once the
                        # walk has actually gone somewhere. len(path) > 3
                        # rejects the degenerate start -> neighbour -> start
                        # bounce while admitting the shortest genuine cycle.
                        if current in node_map and (
                            current != start_pos or len(path) > 3
                        ):
                            reached_node = True
                            break

                        if current not in pixel_degree:
                            break

                        cy, cx = current
                        found_next = False

                        for ddy in (-1, 0, 1):
                            for ddx in (-1, 0, 1):
                                if ddy == 0 and ddx == 0:
                                    continue
                                nny = int(cy + ddy)
                                nnx = int(cx + ddx)
                                if (nny, nnx) == prev:
                                    continue
                                if (nny, nnx) in pixel_degree:
                                    path.append((nnx, nny))
                                    prev = current
                                    current = (nny, nnx)
                                    found_next = True
                                    break
                            if found_next:
                                break

                        if not found_next:
                            break

                    if reached_node and current in node_map:
                        end_nid = node_map[current]
                        # Key on the TRACED PATH, not on its endpoints.
                        # (min(u), max(v)) allowed only one edge per node
                        # pair, so a loop formed by two arcs between the same
                        # two junctions -- a ring with a stem, which is the
                        # shape of every letter with Qc > 0 -- collapsed into
                        # a single edge and stopped being a cycle at all.
                        # MainPath could then never see it as a ClosedPath
                        # candidate (IC.1.11). Canonicalising the point
                        # sequence under reversal still dedupes the same arc
                        # walked from both ends, which is what the old key
                        # was actually for.
                        canonical = tuple(path)
                        edge_key = min(canonical, tuple(reversed(canonical)))
                        if edge_key not in visited_edges:
                            visited_edges.add(edge_key)
                            edge = CSGIEdge(
                                id=int(edge_id),
                                u=int(start_nid),
                                v=int(end_nid),
                                points=[(int(px), int(py)) for px, py in path],
                            )
                            edges.append(edge)
                            edge_id += 1

        # The old "Handle empty case" fallback stood here: if Step 2 found no
        # nodes it dropped in one degree-0 placeholder and returned a graph
        # with no edges. Step 2b subsumes it -- every component now gets a
        # real node with its real degree, and the loop through it is traced --
        # so the fallback was unreachable for any non-empty skeleton and
        # contradicted the behaviour above for the one case it did cover.

        return CSGIGraph(
            letter=self.letter,
            name=self.name,
            nodes=nodes,
            edges=edges,
            adjacency="8-neighborhood",
            release_id=self.release,
        )
