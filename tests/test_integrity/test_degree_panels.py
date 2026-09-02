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
                  key=lambda k: _candidates(chosen + [k]))
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
