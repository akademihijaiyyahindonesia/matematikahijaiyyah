"""The repository graph, held against the files it claims to describe.

The owner's rule for layer 1 is that no edge may be an inference: every one
must come from a real import, a real reference, a real path. So the test that
matters here is not that the graph answers questions -- it is that every
answer can be walked back to a line in a file, and that walking it back finds
what the edge said it would.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui.repository_graph import Edge, build, collapse  # noqa: E402
from hijaiyyah.nui.repository_index import counts, index, resolve  # noqa: E402

GRAPH = build()
ATOM = "src/hijaiyyah/nui/atom.py"
CLOCKWORK = "src/hijaiyyah/nui/clockwork.py"
FREEZE = "src/hijaiyyah/nui/freeze.py"


def test_the_index_finds_every_kind_of_node() -> None:
    kinds = counts()
    for kind in ("python", "test", "hasm", "verilog", "fact"):
        assert kinds.get(kind, 0) > 0, kind
    assert len(index()) == sum(kinds.values())


def test_imports_resolve_to_files_in_this_repository() -> None:
    assert resolve("hijaiyyah.nui.atom") == ATOM
    assert resolve("hijaiyyah.nui.atom.build_atoms") == ATOM
    assert resolve("torch") is None
    assert resolve("json") is None


def test_no_edge_leaves_the_node_set_and_none_points_at_itself() -> None:
    for edge in GRAPH.edges:
        assert edge.source in GRAPH.nodes, edge
        assert edge.target in GRAPH.nodes, edge
        assert edge.source != edge.target, edge


def test_every_edge_can_be_walked_back_to_its_own_line() -> None:
    """The no-inference rule, checked rather than promised. An import edge
    must land on a line that imports; a mention must land on a line naming
    the file."""
    for edge in GRAPH.edges:
        if edge.kind == "verifies" or "line" not in edge.evidence:
            continue
        number = int(edge.evidence.split("line ")[1].split(",")[0])
        line = (ROOT / edge.source).read_text(
            encoding="utf-8", errors="replace").splitlines()[number - 1]
        if edge.kind == "imports":
            assert "import" in line, (edge, line)
        else:
            assert edge.target.rsplit("/", 1)[-1] in line, (edge, line)


def test_the_node_the_directive_used_as_its_example() -> None:
    """The owner wrote out what atom.py's node should look like. It is not a
    sketch -- every line of it is in the graph, including the hardware link
    he named."""
    assert GRAPH.depends_on(ATOM) == [
        "src/hijaiyyah/core/master_table.py",
        "src/hijaiyyah/hisa/opcodes.py",
        "src/hijaiyyah/nui/features.py",
    ]
    assert "tests/test_ai/test_nui_atom.py" in GRAPH.verified_by(ATOM)
    for user in ("src/hijaiyyah/nui/rack.py", "src/hijaiyyah/nui/clockwork.py"):
        assert user in GRAPH.used_by(ATOM), user
    assert "rtl/hcpu_execute.v" in GRAPH.hardware_links(ATOM)


def test_the_relation_between_freeze_and_the_loader_is_a_citation() -> None:
    """The directive asks what relates freeze.py to loader.hasm. It is not an
    import -- freeze.py imports nothing from HASM -- it is a reference in the
    text, and the graph labels it as one."""
    mentions = {e.target for e in GRAPH.out(FREEZE, "mentions")}
    assert "rtl/programs/loader.hasm" in mentions
    assert "rtl/programs/loader.hasm" not in GRAPH.depends_on(FREEZE)


def test_what_must_fail_if_clockwork_breaks() -> None:
    """Both answers are real, and the second is the one a reading by eye
    misses: test_nui_rack.py imports clockwork inside a function, at line 63,
    not at the top of the file."""
    impact = GRAPH.impact_of(CLOCKWORK)
    assert "tests/test_ai/test_nui_clockwork.py" in impact
    assert "tests/test_ai/test_nui_rack.py" in impact
    edge = next(e for e in GRAPH.into(CLOCKWORK, "imports")
                if e.source == "tests/test_ai/test_nui_rack.py")
    number = int(edge.evidence.split("line ")[1])
    line = (ROOT / edge.source).read_text(encoding="utf-8").splitlines()[number - 1]
    assert "clockwork" in line and "import" in line


def test_which_facts_came_from_the_board() -> None:
    from hijaiyyah.nui.facts import load

    board = GRAPH.facts_from_the_board()
    assert board == sorted(f.fact_id for f in load() if f.kind == "board")
    assert "crypto.kabah_avalanche_single_bit" in board
    assert "nui.codex_theta_u_rho_sum" not in board, "that one is recomputed"


def test_one_relation_is_one_edge() -> None:
    """`from x import a, b, c` is one relation. Counting occurrences instead
    turned 372 relations into 10,736 rows saying the same things."""
    seen = {(e.source, e.target, e.kind) for e in GRAPH.edges}
    assert len(seen) == len(GRAPH.edges)
    doubled = [Edge("a.py", "b.py", "imports", "import, line 1"),
               Edge("a.py", "b.py", "imports", "import, line 9")]
    (one,) = collapse(doubled)
    assert one.times == 2
    assert one.evidence == "import, line 1"


def test_the_graph_says_what_it_does_not_have() -> None:
    """Call edges are absent, and the module says so where someone looking
    for them would read."""
    from hijaiyyah.nui import repository_graph

    assert "Call edges." in (repository_graph.__doc__ or "")
