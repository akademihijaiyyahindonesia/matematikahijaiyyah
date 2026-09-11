"""Testing "Point -> Transform -> Line" as a composition order, not a slogan.

nui/claims.py tested the external document's specific numbers and found
most of them wrong. This module tests something the document never stated
precisely enough to test: whether ORDERING letters titik-first, garis-last
before composing them -- the shape "Point -> ... -> Line" the document's
Codex-j formula gestures at -- has any measurable effect at all.

It can only have one if the composition is order-sensitive, and
dataset.py's accumulation (v18 addition) provably is not: order does not
touch the label there, because addition commutes. So this module uses a
DIFFERENT, genuinely order-sensitive operation already available in this
codebase -- composing letters' exomatrices by GF(2) MATRIX MULTIPLICATION
(core.exomatrix.compose_mod) rather than summing their vectors. Swapping two
letters changes the composed rank for about 31% of ordered pairs (see
tests/test_ai/test_nui_pattern_language.py) -- confirmed before any
hypothesis was tested, not assumed.

The hypothesis: for a fixed SET of letters, composing them in
"pipeline order" -- sorted titik-heavy first, garis-heavy last, using the
same (titik, garis, lengkung) features already measured in features.py --
produces a composed matrix with a different (specifically: higher) GF(2)
rank than composing the same set in a random order. Held fixed across
pipeline order and every random comparison: the SET of letters. Only order
changes, so any effect found is about order, not about which letters were
picked.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

from ..core.exomatrix import compose_mod, gf2_rank
from ..core.master_table import MASTER_TABLE
from .features import vector_features

ENTRIES = {e.char: e for e in MASTER_TABLE.all_entries()}
ALL_CHARS: Tuple[str, ...] = tuple(ENTRIES.keys())


def pipeline_order(letters: Tuple[str, ...]) -> Tuple[str, ...]:
    """Sort `letters` titik-heavy first, garis-heavy last -- the shape
    "Point -> Transform -> Line" names, made precise: descending
    (titik - garis), ties broken by Master Table index for determinism (not
    because the tie-break carries meaning -- it does not, and is not
    claimed to)."""
    def key(ch: str) -> Tuple[int, int]:
        f = vector_features(ENTRIES[ch].vector)
        return (-(f.titik - f.garis), ENTRIES[ch].index)
    return tuple(sorted(letters, key=key))


def composed_rank(letters: Tuple[str, ...], p: int = 2) -> int:
    vectors = [ENTRIES[c].vector for c in letters]
    return gf2_rank(compose_mod(vectors, p))


@dataclass(frozen=True)
class PipelineTrial:
    letters: Tuple[str, ...]          # the set drawn (unordered)
    pipeline_rank: int                # rank composing in pipeline_order
    random_ranks: Tuple[int, ...]     # rank composing in each random shuffle
    percentile: float                 # pipeline_rank's rank among random_ranks, 0-100


def run_trials(*, subsets: int = 500, shuffles_per_subset: int = 200,
               min_size: int = 3, max_size: int = 8, seed: int = 0) -> List[PipelineTrial]:
    """`subsets` random letter sets, each composed once in pipeline order
    and `shuffles_per_subset` times in a random order of the SAME set --
    a paired design, so every trial isolates order from selection."""
    rng = random.Random(seed)
    trials = []
    for _ in range(subsets):
        n = rng.randint(min_size, max_size)
        letters = tuple(rng.sample(ALL_CHARS, n))
        pline = pipeline_order(letters)
        prank = composed_rank(pline)

        random_ranks = []
        for _ in range(shuffles_per_subset):
            shuffled = list(letters)
            rng.shuffle(shuffled)
            random_ranks.append(composed_rank(tuple(shuffled)))

        below = sum(1 for r in random_ranks if r <= prank)
        trials.append(PipelineTrial(
            letters=letters, pipeline_rank=prank,
            random_ranks=tuple(random_ranks),
            percentile=100 * below / len(random_ranks),
        ))
    return trials


@dataclass(frozen=True)
class Summary:
    n_trials: int
    mean_percentile: float          # 50.0 would mean "no effect, on average"
    pipeline_rank_higher: int       # trials where pipeline beat every random shuffle's mean
    pipeline_rank_lower: int
    pipeline_rank_tied: int
    mean_pipeline_rank: float
    mean_random_rank: float


def summarize(trials: List[PipelineTrial]) -> Summary:
    higher = lower = tied = 0
    for t in trials:
        random_mean = sum(t.random_ranks) / len(t.random_ranks)
        if t.pipeline_rank > random_mean:
            higher += 1
        elif t.pipeline_rank < random_mean:
            lower += 1
        else:
            tied += 1
    all_random = [r for t in trials for r in t.random_ranks]
    return Summary(
        n_trials=len(trials),
        mean_percentile=sum(t.percentile for t in trials) / len(trials),
        pipeline_rank_higher=higher,
        pipeline_rank_lower=lower,
        pipeline_rank_tied=tied,
        mean_pipeline_rank=sum(t.pipeline_rank for t in trials) / len(trials),
        mean_random_rank=sum(all_random) / len(all_random),
    )
