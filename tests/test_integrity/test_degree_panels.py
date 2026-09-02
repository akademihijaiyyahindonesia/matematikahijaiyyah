"""
Theta-hat is degrees, and degrees are the best dispatch key in the vector.

The quantiser is Q90, so Theta-hat counts quarter turns: Jim is 3, which is
270 degrees. That is not a reading imposed on the number -- it is what the
pipeline puts there, and every letter carries its own.

Treating each letter as a node panel indexed by its degree turns out to be the
strongest single-component partition of the alphabet, by a wide margin, and
this file measures how wide. It also records what did NOT hold, because three
other readings of "Jim as the centre" were tested and failed, and a recipe is
worth more with its failures attached.
"""
from __future__ import annotations

import collections
import math

from hijaiyyah.core.guards import _to_vec
from hijaiyyah.core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
VECTORS = [list(_to_vec(e)) for e in ENTRIES]
JIM = 4
SLOTS = ["Θ̂", "Na", "Nb", "Nd", "Kp", "Kx", "Ks", "Ka", "Kc",
         "Qp", "Qx", "Qs", "Qa", "Qc", "AN", "AK", "AQ", "H*"]


def _candidates(keys: list[int]) -> float:
    """Expected candidates left after filtering the alphabet on `keys`."""
    groups = collections.Counter(tuple(v[k] for k in keys) for v in VECTORS)
    return sum(n * n for n in groups.values()) / len(VECTORS)


def test_theta_is_quarter_turns_and_jim_is_270_degrees() -> None:
    assert ENTRIES[JIM].name.lower().startswith("jim")
    assert VECTORS[JIM][0] == 3
    assert VECTORS[JIM][0] * 90 == 270

    # Every letter carries its own, and they span a full two turns.
    degrees = sorted({v[0] * 90 for v in VECTORS})
    assert degrees == [0, 90, 180, 270, 360, 450, 540, 720]


def test_degrees_are_the_best_single_key_in_the_whole_vector() -> None:
    """
    Not marginally: 6.2x against 2.8x for the runner-up. Theta-hat carries
    2.77 bits of the 4.81 an injective naming of 28 letters would need, more
    than any other component.
    """
    scores = sorted((_candidates([k]), SLOTS[k]) for k in range(18))
    assert scores[0][1] == "Θ̂", scores[:3]

    best, runner = scores[0][0], scores[1][0]
    assert 28 / best > 6.0
    assert 28 / best > 2.2 * (28 / runner), "the margin over second place shrank"

    entropy = {}
    for k in range(18):
        counts = collections.Counter(v[k] for v in VECTORS)
        entropy[SLOTS[k]] = -sum(n / 28 * math.log2(n / 28) for n in counts.values())
    assert max(entropy, key=entropy.get) == "Θ̂"


def test_six_components_name_a_letter_and_degrees_come_first() -> None:
    """Greedy from Theta-hat reaches injectivity in six of eighteen."""
    chosen = [0]
    while _candidates(chosen) > 1.0:
        nxt = min((k for k in range(18) if k not in chosen),
                  key=lambda k: _candidates([*chosen, k]))
        before = _candidates(chosen)
        chosen.append(nxt)
        assert _candidates(chosen) < before, "greedy stalled"
    assert len(chosen) == 6, [SLOTS[k] for k in chosen]
    assert chosen[0] == 0


def test_the_270_panel_is_the_largest_and_the_most_central() -> None:
    """
    Jim heads it, and it is where the metric centre of the alphabet sits:
    five of the six most central letters are 270 degrees.
    """
    panels = collections.defaultdict(list)
    for i, v in enumerate(VECTORS):
        panels[v[0]].append(i)
    assert len(panels[3]) == 6 == max(len(p) for p in panels.values())
    assert min(panels[3]) == JIM, "Jim is not the first letter of its panel"

    def total(i: int) -> int:
        return sum(sum((x - y) ** 2 for x, y in zip(VECTORS[i], w, strict=True))
                   for w in VECTORS)

    by_centre = sorted(range(28), key=total)
    # The panel, averaged, is the most central of the eight.
    avg = {t: sum(total(i) for i in ids) / len(ids) for t, ids in panels.items()}
    assert min(avg, key=avg.get) == 3, avg
    assert sum(1 for i in by_centre[:6] if VECTORS[i][0] == 3) == 5


# ══════════════════════════════════════════════════════════════════
#  What did not hold — kept because a recipe is worth its failures
# ══════════════════════════════════════════════════════════════════

def test_centring_the_encoding_on_jim_makes_it_worse_not_better() -> None:
    """
    An obvious-looking move that measurement refuses: 71% of components are
    already zero, so the vector is sparse, and re-centring on any non-zero
    reference destroys that sparsity.
    """
    zeros = sum(1 for v in VECTORS for k in range(18) if v[k] == 0)
    assert zeros / (28 * 18) > 0.70

    def bits(ref: list[int]) -> int:
        return sum(max(1, abs(v[k] - ref[k]).bit_length()
                       + (1 if v[k] - ref[k] < 0 else 0))
                   for v in VECTORS for k in range(18))

    assert bits(VECTORS[JIM]) > bits([0] * 18), "re-centring on Jim now helps"


def test_jim_is_a_poor_metric_pivot_because_centres_always_are() -> None:
    """
    Pivot pruning wants a point FAR from the others, so the triangle-inequality
    bound is tight. Alif at 0 degrees and Haa at 720 -- the two extremes -- are
    the best pivots; Jim ranks 21st of 28. Being central is what makes a good
    panel head and a bad pivot, and those are different jobs.
    """
    dist = [[math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))
             for b in VECTORS] for a in VECTORS]

    def pruned(p: int) -> float:
        saved = total = 0
        for q in range(28):
            if q == p:
                continue
            best = float("inf")
            for x in sorted((i for i in range(28) if i != q),
                            key=lambda x: abs(dist[q][p] - dist[x][p])):
                total += 1
                if abs(dist[q][p] - dist[x][p]) >= best:
                    saved += 1
                    continue
                best = min(best, dist[q][x])
        return saved / total

    ranked = sorted(range(28), key=pruned, reverse=True)
    assert ranked.index(JIM) > 15, "Jim became a good pivot — recheck the claim"
    assert VECTORS[ranked[0]][0] in (0, 8), "the best pivot is no longer extreme"


# ══════════════════════════════════════════════════════════════════
#  The exomatrix panel — where the counting jump actually is
# ══════════════════════════════════════════════════════════════════

def test_the_exomatrix_is_one_face_of_the_cube() -> None:
    """
    5x5 = 25 cells, and the sponge state is 25 lanes. Each letter is literally
    one face. That is what "panel" means here -- not a metaphor and not an
    index, a face.
    """
    from hijaiyyah.core.exomatrix import build_exomatrix
    from hijaiyyah.crypto import cube

    m = build_exomatrix(ENTRIES[JIM])
    assert len(m) == 5 and all(len(r) == 5 for r in m)
    assert len(m) * len(m[0]) == cube.STATE_LANES == 25


def test_the_panel_is_sparse_and_low_rank_at_the_same_time() -> None:
    """
    74% of cells are zero, and the average rank is 3.71 of 5. Either alone
    would be worth something; together they are why the panel costs a fraction
    of its 25 cells.
    """
    from fractions import Fraction

    from hijaiyyah.core.exomatrix import build_exomatrix

    def rank(m: list[list[int]]) -> int:
        a = [[Fraction(x) for x in row] for row in m]
        r = 0
        for c in range(5):
            p = next((i for i in range(r, 5) if a[i][c]), None)
            if p is None:
                continue
            a[r], a[p] = a[p], a[r]
            for i in range(5):
                if i != r and a[i][c]:
                    f = a[i][c] / a[r][c]
                    a[i] = [x - f * y for x, y in zip(a[i], a[r], strict=True)]
            r += 1
        return r

    mats = [build_exomatrix(e) for e in ENTRIES]
    zeros = sum(1 for m in mats for row in m for x in row if x == 0)
    assert zeros / (28 * 25) > 0.70

    ranks = [rank(m) for m in mats]
    assert max(ranks) <= 5
    assert sum(ranks) / 28 < 4.0, "the panels stopped being low-rank"


def test_the_counting_jump_and_where_each_factor_comes_from() -> None:
    """
    The recipe said there was a jump in the counting, and there is. It is the
    product of two things acting on different axes, which is why it multiplies
    rather than adds:

        degree picks the panel     28 candidates -> 4.50    6.2x
        the panel is sparse        125 MACs      -> 9.8    12.7x
                                                          -----
        together                   3500          -> 44      79x

    Neither half is impressive alone. The reason they compose is that one
    decides WHICH panels are touched and the other decides HOW MUCH each
    touched panel costs.
    """
    import itertools

    from hijaiyyah.core.exomatrix import build_exomatrix

    mats = [build_exomatrix(e) for e in ENTRIES]

    def sparse_macs(a: list[list[int]], b: list[list[int]]) -> int:
        return sum(1 for i in range(5) for k in range(5) if a[i][k]
                   for j in range(5) if b[k][j])

    costs = [sparse_macs(mats[x], mats[y])
             for x, y in itertools.product(range(28), repeat=2)]
    mean_cost = sum(costs) / len(costs)

    assert 125 / mean_cost > 12.0, f"sparsity gain fell to {125 / mean_cost:.1f}x"
    assert 125 / max(costs) > 5.0, "even the worst case must beat dense"

    candidates = _candidates([0])
    dense_full = 28 * 125
    sparse_panel = candidates * mean_cost
    assert dense_full / sparse_panel > 70.0, (
        f"the combined jump fell to {dense_full / sparse_panel:.0f}x")
