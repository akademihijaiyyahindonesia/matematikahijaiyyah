"""
Hybit is code. Silicon and photonics are the track it runs on.

That is not a slogan, it is a structural claim, and it is falsifiable: if the
hybit layer carries substrate assumptions, then the photonic path in Bab III
§10.2 is not a substitution of tracks but a port, and every property proved
about the algebra would have to be re-proved on the other side.

The two substrates map the SAME vector onto entirely different physics:

    Theta-hat  ->  silicon: a 32-bit word     photonics: photon phase
    N (3)      ->  silicon: three counters    photonics: three wavelengths (WDM)
    K, Q (5+5) ->  silicon: register fields   photonics: time slots and OAM

Nothing in that table can be true if the algebra knows how wide a word is.
So these tests keep the hybit layer free of the track: no clock, no LUT, no
word width, no masks, no shifts. Arithmetic on non-negative integers, and
nothing else.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "src" / "hijaiyyah" / "core"

# The algebra itself. Not hisab/ -- that is transport and framing, where CRC32
# and byte widths are the point rather than a leak.
PURE = ("hybit.py", "guards.py")

SUBSTRATE = {
    r"\bclk\b|\bclock\b|posedge|cycle": "timing",
    r"\bLUT\b|\blut\d|flip-?flop|\bFPGA\b": "gate-level",
    r"0x[0-9A-Fa-f]{4,}|&\s*0xFF|\bmask\b": "word width",
    r"<<|>>|\.bit_length\(|\bctypes\b|struct\.pack": "bit layout",
    r"\bint32\b|\buint32\b|\b32-bit\b|\b64-bit\b": "machine integer",
}


@pytest.mark.parametrize("name", PURE)
def test_the_algebra_names_no_substrate(name: str) -> None:
    text = (CORE / name).read_text(encoding="utf-8")
    for pattern, what in SUBSTRATE.items():
        hits = [
            line for line in text.splitlines()
            if re.search(pattern, line) and not line.lstrip().startswith("#")
        ]
        assert not hits, f"{name} leaks {what}: {hits[:2]}"


@pytest.mark.parametrize("name", PURE)
def test_the_algebra_uses_only_integer_arithmetic(name: str) -> None:
    """
    No bitwise operators anywhere in the parse tree. A shift or a mask is a
    statement about how a number is stored, and a photon's phase is not stored
    that way.
    """
    tree = ast.parse((CORE / name).read_text(encoding="utf-8"))
    banned = (ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor)

    # Annotations are not code. `List[int] | Tuple[int, ...]` parses as BitOr
    # and says nothing about how a number is stored -- the first version of
    # this test flagged it and was wrong.
    annotations = set()
    for node in ast.walk(tree):
        for slot in ("annotation", "returns"):
            ann = getattr(node, slot, None)
            if ann is not None:
                annotations.update(id(n) for n in ast.walk(ann))

    found = [
        (type(node.op).__name__, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp)
        and isinstance(node.op, banned)
        and id(node) not in annotations
    ]
    assert not found, f"{name} uses bitwise operators: {found}"


def test_the_vector_decomposes_the_way_both_substrates_need() -> None:
    """
    The photonic mapping needs the components grouped as 1 + 3 + 5 + 5 + 3 + 1:
    one phase, three wavelengths, two five-way structures, three aggregates and
    the identity. If the shape moved, the mapping in §10.2 would stop being a
    mapping.
    """
    from hijaiyyah.core.guards import _to_vec
    from hijaiyyah.core.master_table import MASTER_TABLE

    v = list(_to_vec(MASTER_TABLE.all_entries()[0]))
    assert len(v) == 18
    theta, N, K, Q, A, H = v[0:1], v[1:4], v[4:9], v[9:14], v[14:17], v[17:18]
    assert (len(theta), len(N), len(K), len(Q), len(A), len(H)) == (1, 3, 5, 5, 3, 1)
    assert sum(map(len, (theta, N, K, Q, A, H))) == 18

    # Three N components is what makes three-wavelength WDM the natural
    # carrier, and A_N is their sum -- so the aggregate is recoverable at the
    # receiver without a fourth channel.
    assert v[14] == sum(N)


def test_the_guard_needs_no_stored_value_to_check_itself() -> None:
    """
    The property that survives the change of track: validity is decided from
    the vector alone. A checksum would need a number carried alongside, and a
    number carried alongside is a number the substrate has to store and the
    channel has to deliver intact.
    """
    import inspect

    from hijaiyyah.core import guards

    source = inspect.getsource(guards.guard_check)
    # No file, no table, no constant lookup -- only the argument.
    for forbidden in ("open(", "MASTER_TABLE", "import ", "TABLE[", "json"):
        assert forbidden not in source, forbidden

    tree = ast.parse(source.lstrip())
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    assert [a.arg for a in fn.args.args] == ["v"], "the guard takes only the vector"
