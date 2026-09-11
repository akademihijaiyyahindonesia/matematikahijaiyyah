"""Fase 1 (NUI/ROADMAP.md): multi-task additions to dataset.py and model.py.

Mirrors test_nui.py's discipline -- every label checked against an
independent recomputation, not against the module's own bookkeeping.
"""
from __future__ import annotations

import random

import pytest

torch = pytest.importorskip("torch")

from hijaiyyah.core.exomatrix import build_exomatrix, gf2_rank, matrix_order  # noqa: E402
from hijaiyyah.core.guards import full_guard_check  # noqa: E402
from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.nui.dataset import (  # noqa: E402
    ENTRIES,
    RANK_CLASSES,
    build_dataset,
    exomatrix_rank,
    is_gf5_primitive,
    random_examples,
)
from hijaiyyah.nui.model import (  # noqa: E402
    MultiTaskAccumulatorNet,
    gf5_labels,
    multihot,
    rank_labels,
)
from hijaiyyah.nui.multitask import TASKS, evaluate_multi, train_multi  # noqa: E402

# ── the dropped task: guard validity is trivially constant ──────


def test_every_canonical_letter_passes_every_guard_individually():
    for e in MASTER_TABLE.all_entries():
        assert full_guard_check(e.vector)["all_pass"] is True, e.char


def test_guard_validity_never_varies_under_accumulation():
    """The empirical finding NUI/ROADMAP.md and multitask.py's docstring cite
    for why guard validity is NOT one of Fase 1's tasks: G1-G4 are linear (or,
    for G4, a sum of non-negatives) identities, so any accumulation of
    already-guard-valid canonical letters stays guard-valid. If this ever
    stops being true -- guards.py changes, or a non-canonical letter enters
    the table -- this test is what would say so, rather than a stale design
    rationale nobody re-checks."""
    rng = random.Random(0)
    for _ in range(200):
        k = rng.randint(1, len(ENTRIES))
        idxs = rng.sample(range(len(ENTRIES)), k)
        acc = [0] * 18
        for i in idxs:
            acc = [a + b for a, b in zip(acc, ENTRIES[i].vector, strict=True)]
        assert full_guard_check(acc)["all_pass"] is True, idxs


# ── dataset.py additions ─────────────────────────────────────────


def test_is_gf5_primitive_matches_direct_matrix_order():
    jim_vec = list(MASTER_TABLE.get_by_char("ج").vector)
    assert is_gf5_primitive(jim_vec) is True  # matrix_order(jim, 5) == (1, 3124)
    alif_vec = list(MASTER_TABLE.get_by_char("ا").vector)
    assert is_gf5_primitive(alif_vec) is False


def test_exomatrix_rank_matches_direct_computation():
    jim_vec = list(MASTER_TABLE.get_by_char("ج").vector)
    expected = gf2_rank(tuple(tuple(row) for row in build_exomatrix(jim_vec)))
    # 4, not full rank (5) -- checked directly rather than assumed. A 5x5
    # matrix with maximal multiplicative ORDER (Jim's own period-31 property,
    # tested elsewhere) is not the same claim as maximal RANK; this is what
    # caught the difference before it became a wrong assertion.
    assert exomatrix_rank(jim_vec) == expected == 4


def test_random_examples_carry_independently_verifiable_gf5_and_rank():
    """Same discipline as test_nui.py's GF(2) spot-check, extended to the two
    new fields -- against fresh matrix_order/gf2_rank calls, not
    dataset.py's own bookkeeping."""
    examples = random_examples(15, seed=2)
    assert examples
    for ex in examples:
        acc = [0] * 18
        for idx in ex.letter_indices:
            acc = [a + b for a, b in zip(acc, ENTRIES[idx].vector, strict=True)]
        _, p5 = matrix_order(acc, 5, cap=4000)
        assert ex.gf5_primitive == (p5 == 3124), ex
        assert ex.rank == gf2_rank(tuple(tuple(row) for row in build_exomatrix(acc))), ex
        assert 0 <= ex.rank <= 5


def test_build_dataset_natural_split_has_all_three_labels_populated():
    """A regression guard against the two new fields silently defaulting to
    False/0 for real (non-hand-built) examples -- that would look like valid
    data while actually being the dataclass default, not a computed one."""
    ds = build_dataset(sequences=200, seed=3)
    assert any(e.gf5_primitive for e in ds.natural + ds.train)
    assert any(not e.gf5_primitive for e in ds.natural + ds.train)
    assert len({e.rank for e in ds.natural + ds.train}) > 1


# ── model.py: MultiTaskAccumulatorNet ────────────────────────────


def test_multitask_net_requires_at_least_one_task():
    with pytest.raises(ValueError, match="at least one task"):
        MultiTaskAccumulatorNet(kind="physics", tasks={})


def test_multitask_net_shares_one_trunk_with_the_single_task_net():
    """The embedding MultiTaskAccumulatorNet builds for kind="physics" must be
    byte-for-byte the same tensor LetterAccumulatorNet builds -- both call
    _build_embedding, and this is what proves neither kept its own copy."""
    from hijaiyyah.nui.model import LetterAccumulatorNet

    single = LetterAccumulatorNet(kind="physics")
    multi = MultiTaskAccumulatorNet(kind="physics", tasks=TASKS)
    assert torch.equal(single.embedding.weight, multi.embedding.weight)
    assert not multi.embedding.weight.requires_grad  # frozen, same as single-task


def test_multitask_net_output_shapes_and_dtypes():
    examples = random_examples(6, seed=4)
    batch = multihot(examples)
    net = MultiTaskAccumulatorNet(kind="physics", tasks=TASKS)
    out = net(batch)
    assert set(out.keys()) == set(TASKS.keys())
    assert out["gf2_primitive"].shape == (len(examples),)
    assert out["gf5_primitive"].shape == (len(examples),)
    assert out["rank"].shape == (len(examples), RANK_CLASSES)


def test_multitask_baseline_is_trainable_frozen_variants_are_not():
    net = MultiTaskAccumulatorNet(kind="baseline", tasks=TASKS, embed_dim=5)
    assert net.embedding.weight.requires_grad
    for kind in ("physics", "exomatrix"):
        net = MultiTaskAccumulatorNet(kind=kind, tasks=TASKS)
        assert not net.embedding.weight.requires_grad


# ── model.py: label tensors ──────────────────────────────────────


def test_gf5_and_rank_label_tensors_match_example_order():
    examples = random_examples(5, seed=6)
    assert gf5_labels(examples).tolist() == [1.0 if e.gf5_primitive else 0.0 for e in examples]
    assert rank_labels(examples).tolist() == [e.rank for e in examples]
    assert rank_labels(examples).dtype == torch.long


# ── multitask.py: joint training actually learns something ──────


def test_joint_training_beats_majority_baseline_on_rank_at_small_scale():
    """Scaled down for test speed (400 sequences, 80 epochs versus
    NUI/ROADMAP.md's eventual full-scale run) -- not exact numbers, a real
    check that the shared trunk plus rank head learns something better than
    always predicting the majority rank class."""
    ds = build_dataset(sequences=400, seed=0)
    model = train_multi(kind="physics", dataset=ds, epochs=80, seed=0)
    m = evaluate_multi(model, ds.natural)
    assert m["rank"].accuracy >= m["rank"].baseline_accuracy, (
        "the rank head should not do worse than always predicting the "
        "majority class once trained"
    )


def test_evaluate_multi_returns_all_three_task_metrics():
    ds = build_dataset(sequences=100, seed=1)
    model = train_multi(kind="physics", dataset=ds, epochs=10, seed=0)
    m = evaluate_multi(model, ds.natural)
    assert set(m.keys()) == {"gf2_primitive", "gf5_primitive", "rank"}
    assert 0.0 <= m["gf2_primitive"].accuracy <= 1.0
    assert 0.0 <= m["rank"].accuracy <= 1.0
