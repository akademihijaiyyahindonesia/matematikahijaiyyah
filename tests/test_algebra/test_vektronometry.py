"""Tests for Field 1: Vectronometry (Bab II-A, Ch 17-21)."""



class TestPrimitiveRatios:
    def test_sum_equals_one(self, hm, all_entries):
        pr = hm["vectronometry"]["primitive_ratios"]
        for e in all_entries:
            v = list(e.vector)
            if v[14] + v[15] + v[16] == 0:
                continue
            r = pr(e)
            total = r["r_N"] + r["r_K"] + r["r_Q"]
            assert abs(total - 1.0) < 1e-9, f"{e.char}: sum={total}"


class TestPythagorean:
    def test_all_28(self, hm, all_entries):
        pc = hm["vectronometry"]["pythagorean_check"]
        for e in all_entries:
            r = pc(e)
            assert r["pass"], f"{e.char}: lhs={r['lhs']} rhs={r['rhs']}"


class TestNorm:
    def test_alif_norm_is_one(self, hm, alif):
        assert hm["vectronometry"]["norm2"](alif) == 1

    def test_haa_norm_is_69(self, hm, haa):
        assert hm["vectronometry"]["norm2"](haa) == 69


class TestCosine:
    def test_non_negative(self, hm, all_entries):
        cos = hm["vectronometry"]["cosine"]
        for i, e1 in enumerate(all_entries):
            for e2 in all_entries[i:]:
                assert cos(e1, e2) >= 0


# ── the zero that used to swallow the undefined case ─────────────

def test_cosine_refuses_a_zero_vector_instead_of_calling_it_orthogonal() -> None:
    """0.0 meant two different things, and one of them was a real answer.

    A zero vector has no direction, so there is no angle to it. The old code
    returned 0.0 -- the same value it returns for genuinely perpendicular
    hybits, of which the sealed table has 54 pairs. Undefined and measured
    were the same number, which is the defect class that let an empty
    instruction memory pass as a program full of NOPs for years.
    """
    import pytest

    from hijaiyyah.algebra.vektronometry import cosine
    from hijaiyyah.core.master_table import MASTER_TABLE

    entries = MASTER_TABLE.all_entries()
    zero = [0] * 18

    with pytest.raises(ValueError, match="undefined against a zero vector"):
        cosine(zero, entries[0])
    with pytest.raises(ValueError, match="undefined against a zero vector"):
        cosine(entries[0], zero)
    with pytest.raises(ValueError, match="undefined against a zero vector"):
        cosine(zero, zero)


def test_real_orthogonal_pairs_still_measure_zero() -> None:
    """The refusal must not have been bought by breaking the real answer."""
    import itertools

    from hijaiyyah.algebra.vektronometry import cosine, norm2
    from hijaiyyah.core.master_table import MASTER_TABLE

    entries = MASTER_TABLE.all_entries()
    assert all(norm2(e) > 0 for e in entries), "a sealed letter now has zero norm"

    orthogonal = [(a.char, b.char) for a, b in itertools.product(entries, repeat=2)
                  if cosine(a, b) == 0.0]
    assert len(orthogonal) == 54, f"{len(orthogonal)} orthogonal pairs, not 54"

    # Range, stated with the float reality rather than an idealised bound.
    # Eleven pairs come back as 1.0000000000000002 -- one ULP over, from
    # ip / (sqrt(n2) * sqrt(n2)) on identical vectors. Harmless as a
    # similarity, and a domain error for any caller that feeds it to acos(),
    # so the number is pinned here instead of being rounded away quietly.
    values = [cosine(a, b) for a, b in itertools.product(entries, repeat=2)]
    assert min(values) == 0.0
    assert max(values) <= 1.0 + 4e-16
    over = [v for v in values if v > 1.0]
    assert len(over) == 11 and all(v - 1.0 < 1e-15 for v in over)
