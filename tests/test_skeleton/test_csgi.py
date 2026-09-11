"""CSGINode/CSGIEdge/CSGIGraph and the numpy-safe JSON path (IC.1.21, Bab I).

test_contractor.py exercises these through SkeletonContractor's own output,
where every field is already a native int by the time it reaches to_dict()
(each dataclass's __post_init__ casts on construction). NumpySafeEncoder's
own numpy-handling branch is therefore dead from that path -- these tests
hit it directly, and check the dataclasses' construction-time casts in
isolation from the contractor that happens to always feed them clean ints.
"""

from __future__ import annotations

import json

import numpy as np

from hijaiyyah.skeleton.csgi import CSGIEdge, CSGIGraph, CSGINode, NumpySafeEncoder


def test_csgi_node_casts_numpy_scalars_to_native_int_on_construction() -> None:
    node = CSGINode(id=np.int64(3), x=np.int32(10), y=np.int32(20), degree=np.int64(1))

    assert (node.id, node.x, node.y, node.degree) == (3, 10, 20, 1)
    assert all(
        isinstance(v, int) for v in (node.id, node.x, node.y, node.degree)
    ), "each field must be a plain int, not a numpy scalar wearing an int's clothes"


def test_csgi_edge_casts_numpy_scalars_including_its_point_list() -> None:
    edge = CSGIEdge(
        id=np.int64(0), u=np.int64(1), v=np.int64(2),
        points=[(np.int32(1), np.int32(2)), (np.int64(3), np.int64(4))],
    )

    assert edge.points == [(1, 2), (3, 4)]
    assert all(isinstance(x, int) and isinstance(y, int) for x, y in edge.points)


def test_numpy_safe_encoder_handles_scalar_and_array_types_directly() -> None:
    payload = {
        "int64": np.int64(5),
        "float32": np.float32(2.5),
        "array": np.array([1, 2, 3]),
    }
    encoded = json.dumps(payload, cls=NumpySafeEncoder)
    decoded = json.loads(encoded)

    assert decoded["int64"] == 5
    assert decoded["array"] == [1, 2, 3]
    assert abs(decoded["float32"] - 2.5) < 1e-6


def test_empty_graph_still_serialises_a_well_formed_shape() -> None:
    graph = CSGIGraph(letter="ا", name="Alif", nodes=[], edges=[])

    data = graph.to_dict()
    assert data["stats"] == {"node_count": 0, "edge_count": 0}
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["adjacency"] == "8-neighborhood"
    # release_id defaults to "" -- to_dict() must not turn a missing release
    # into null, which would fail elsewhere expecting a string key.
    assert data["release"] == ""
