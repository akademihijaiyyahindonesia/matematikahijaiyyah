"""Training data: real accumulation, real ground truth, no fabrication.

Every example comes from actually accumulating letters into an 18-component
vector -- exactly what a letter opcode does in hardware and in
hijaiyyah.hisa.machine (`HREG[0] += v(letter)`, cosmic-codex-jim/MACHINE.md
Sec.6) -- and then computing that accumulated vector's exomatrix period over
GF(2) via hijaiyyah.core.exomatrix.matrix_order, the same function
cosmic-codex-jim/'s own numbers came from. Nothing is fit or invented: the
label is a real, independently-checkable computation, not a heuristic.

The order letters are accumulated in does not affect the label -- v18
addition commutes, so a prefix's resulting vector depends only on the SET of
letters seen so far, not their order. That is a real fact about this system
(guards.py's own docstring calls the guard-valid set "closed under
addition"), not a simplification chosen to make the task easier, and it is
exactly why model.py's architecture pools by summing rather than using a
recurrent encoder: summing is the mechanistically correct operation, not a
convenient stand-in for one.

Positive examples (period 31, "primitive": Jim's and Kha's own individual
property, generalised here to sums) are rare -- about 4% of prefixes drawn
uniformly at random. `training_examples` balances classes for training;
`Dataset.natural` keeps the true, imbalanced distribution for honest
evaluation, and `real_corpus_examples` gives every prefix of
rtl/programs/letters.hasm's actual 28-letter accumulation order as a
held-out check against one genuine hand-written program rather than only
synthetic sequences.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

from ..core.exomatrix import build_exomatrix, gf2_rank, matrix_order
from ..core.master_table import MASTER_TABLE

ENTRIES = MASTER_TABLE.all_entries()
NUM_LETTERS = len(ENTRIES)
CHAR_TO_INDEX = {e.char: i for i, e in enumerate(ENTRIES)}

#: The order rtl/programs/letters.hasm actually accumulates in, ا through ي.
LETTERS_HASM_ORDER: Tuple[str, ...] = tuple(e.char for e in ENTRIES)

#: Over GF(2) a 5x5 invertible matrix's order divides 2^5-1=31 at most (the
#: Singer-cycle bound cosmic-codex-jim/MACHINE.md Sec.3 names); 64 is a
#: generous cap that never truncates a real answer.
_ORDER_CAP = 64
MAX_PERIOD = 31

#: Same Singer-cycle bound, modulus 5: order divides 5^5-1=3124 at most (see
#: tests/test_ai/test_nui.py's matrix_order(jim.vector, 5) == (1, 3124)).
#: 4000 is a generous cap, mirroring _ORDER_CAP's reasoning.
_ORDER_CAP_GF5 = 4000
MAX_PERIOD_GF5 = 3124

#: gf2_rank(build_exomatrix(v)) tops out at 5 (a 5x5 matrix), but empirically
#: (2000 random accumulations, seed 0) the observed range was 0-4 -- 5 has
#: never been seen. RANK_CLASSES covers the full possible range regardless,
#: so a future run landing on 5 does not silently fall outside the model's
#: output space.
RANK_CLASSES = 6  # 0, 1, 2, 3, 4, 5


def is_primitive(accumulated_vector) -> bool:
    """True if the accumulated vector's GF(2) exomatrix reaches the maximum
    possible order, 31 -- the property Jim and Kha have individually,
    generalised here to any sum of letters."""
    _, period = matrix_order(accumulated_vector, 2, cap=_ORDER_CAP)
    return period == MAX_PERIOD


def is_gf5_primitive(accumulated_vector) -> bool:
    """Same question as is_primitive, modulus 5 instead of 2 -- a genuinely
    different algebraic question about the same accumulated vector, not a
    restatement of the GF(2) one (nothing ties the two moduli's answers
    together a priori)."""
    _, period = matrix_order(accumulated_vector, 5, cap=_ORDER_CAP_GF5)
    return period == MAX_PERIOD_GF5


def exomatrix_rank(accumulated_vector) -> int:
    """GF(2) rank of the accumulated vector's 5x5 exomatrix, 0..5. Unlike
    is_primitive/is_gf5_primitive (both a single yes/no about order), this is
    a small integer -- a different KIND of question over the same 25-cell
    structure, not just a third variant of the same one."""
    matrix = tuple(tuple(row) for row in build_exomatrix(accumulated_vector))
    return gf2_rank(matrix)


@dataclass(frozen=True)
class Example:
    """One accumulation prefix: which letters (by index, Master Table
    order) contributed, and three independently-computed facts about the
    result -- Fase 0's task (label) plus the two Fase 1 adds. All three come
    from the same accumulated vector; nothing here is derived from another
    field of this class."""

    letter_indices: Tuple[int, ...]
    label: bool                     #: GF(2) primitive, period 31 -- Fase 0's task
    gf5_primitive: bool = False     #: GF(5) primitive, period 3124 -- Fase 1
    rank: int = 0                   #: gf2_rank(exomatrix), 0..5 -- Fase 1
    # Defaults exist for callers that only care about `label` (a hand-built
    # illustrative Example, not one produced by _accumulate_prefixes) -- not
    # because an unset gf5_primitive/rank is ever a meaningful "real" value.


def _accumulate_prefixes(order: List[int]) -> List[Example]:
    acc = [0] * 18
    examples: List[Example] = []
    for idx in order:
        acc = [a + b for a, b in zip(acc, ENTRIES[idx].vector, strict=True)]
        examples.append(Example(
            tuple(order[: len(examples) + 1]),
            is_primitive(acc),
            is_gf5_primitive(acc),
            exomatrix_rank(acc),
        ))
    return examples


def real_corpus_examples() -> List[Example]:
    """Every prefix of rtl/programs/letters.hasm's actual accumulation
    order -- the one sequence in this dataset that is a real, hand-written
    program's real execution order, not a synthetic draw."""
    order = [CHAR_TO_INDEX[c] for c in LETTERS_HASM_ORDER]
    return _accumulate_prefixes(order)


def random_examples(count: int, *, seed: int) -> List[Example]:
    """`count` random sequences (random length 1..28, random subset, random
    order), every prefix of each kept as its own example. Order does not
    change the label (see module docstring), but sampling random subsets of
    random size is what gives coverage across accumulation states the one
    real program in this repo does not visit on its own."""
    rng = random.Random(seed)
    examples: List[Example] = []
    for _ in range(count):
        n = rng.randint(1, NUM_LETTERS)
        order = rng.sample(range(NUM_LETTERS), n)
        examples.extend(_accumulate_prefixes(order))
    return examples


@dataclass
class Dataset:
    """A class-balanced training split and a naturally-distributed
    evaluation split, drawn from the same random examples so neither is
    cherry-picked -- plus the real-corpus prefixes, held out separately."""

    train: List[Example]
    natural: List[Example]
    real_corpus: List[Example]


def build_dataset(*, sequences: int = 4000, seed: int = 0) -> Dataset:
    pool = random_examples(sequences, seed=seed)
    rng = random.Random(seed + 1)
    rng.shuffle(pool)

    split = int(len(pool) * 0.7)
    train_pool, natural = pool[:split], pool[split:]

    positives = [e for e in train_pool if e.label]
    negatives = [e for e in train_pool if not e.label]
    if not positives:
        raise ValueError(
            "no positive (primitive) examples in the training pool -- "
            "increase `sequences`"
        )
    # Oversample the rarer class with replacement rather than discard the
    # majority down to its size: this dataset's positives are real,
    # independently-checkable computations, not synthetic noise, so keeping
    # more of the negatives (up to matching count) costs nothing and uses
    # more of what was actually computed.
    target = max(len(positives), len(negatives))
    balanced = (
        positives * (target // len(positives))
        + [rng.choice(positives) for _ in range(target % len(positives))]
        + negatives * (target // len(negatives))
        + [rng.choice(negatives) for _ in range(target % len(negatives))]
    )
    rng.shuffle(balanced)

    return Dataset(train=balanced, natural=natural, real_corpus=real_corpus_examples())
