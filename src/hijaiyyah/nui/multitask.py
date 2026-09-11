"""Fase 1 of NUI/ROADMAP.md: one trunk, three genuinely different questions.

Fase 0 (train.py) asks one question -- is the accumulated vector's GF(2)
exomatrix primitive? This module asks three, sharing the same embedding and
sum-pooling trunk, differing only in which head reads it:

  gf2_primitive  period 31 over GF(2)   -- Fase 0's own task, carried over
  gf5_primitive  period 3124 over GF(5) -- a different modulus, not tied to
                                            the GF(2) answer by any identity
  rank           gf2_rank(exomatrix)    -- a different KIND of question
                                            (0..5, not yes/no) over the same
                                            25-cell structure

Guard validity (G1-G4, T1, T2 -- core.guards.full_guard_check) was
considered and DROPPED before writing any training code: every one of the 28
canonical letters passes all six individually, and every one is a linear (or,
for G4, a sum-of-non-negatives) identity, so it stays true under ANY
accumulation of canonical letters -- confirmed empirically, 2000 random
subsets, 100% pass on every guard. A label that never varies teaches
nothing; the empirical check is what caught it before it became a task, not
after (see NUI/ROADMAP.md's Fase 1 section).

Run as ``python3 -m hijaiyyah.nui.multitask``.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Union

import torch
from torch import nn

from .dataset import RANK_CLASSES, Dataset, Example, build_dataset
from .model import (
    EXOMATRIX_DIM,
    PHYSICS_DIM,
    EmbeddingKind,
    MultiTaskAccumulatorNet,
    gf5_labels,
    labels,
    multihot,
    rank_labels,
)
from .train import prior_correction

TASKS: Dict[str, int] = {"gf2_primitive": 1, "gf5_primitive": 1, "rank": RANK_CLASSES}


@dataclass
class BinaryMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    baseline_accuracy: float
    n: int
    n_positive: int


@dataclass
class RankMetrics:
    accuracy: float
    baseline_accuracy: float  # always predicting the majority class
    n: int
    per_class_n: Dict[int, int]


def _binary_metrics(logits: torch.Tensor, y: torch.Tensor, *, bias: float = 0.0) -> BinaryMetrics:
    pred = (torch.sigmoid(logits + bias) >= 0.5).float()
    tp = float(((pred == 1) & (y == 1)).sum())
    fp = float(((pred == 1) & (y == 0)).sum())
    fn = float(((pred == 0) & (y == 1)).sum())
    tn = float(((pred == 0) & (y == 0)).sum())
    n = len(y)
    n_pos = int(y.sum())
    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return BinaryMetrics(accuracy, precision, recall, f1, (n - n_pos) / n if n else 0.0, n, n_pos)


def _rank_metrics(logits: torch.Tensor, y: torch.Tensor) -> RankMetrics:
    pred = logits.argmax(dim=-1)
    n = len(y)
    accuracy = float((pred == y).float().mean()) if n else 0.0
    per_class_n = {c: int((y == c).sum()) for c in range(RANK_CLASSES)}
    majority_n = max(per_class_n.values()) if per_class_n else 0
    return RankMetrics(accuracy, majority_n / n if n else 0.0, n, per_class_n)


def train_multi(
    *,
    kind: EmbeddingKind,
    dataset: Dataset,
    epochs: int = 500,
    lr: float = 0.02,
    seed: int = 0,
    embed_dim: int | None = None,
) -> MultiTaskAccumulatorNet:
    torch.manual_seed(seed)
    model = MultiTaskAccumulatorNet(kind=kind, tasks=TASKS, embed_dim=embed_dim)
    optimiser = torch.optim.Adam((p for p in model.parameters() if p.requires_grad), lr=lr)
    bce = nn.BCEWithLogitsLoss()
    ce = nn.CrossEntropyLoss()

    x = multihot(dataset.train)
    y_gf2 = labels(dataset.train)
    y_gf5 = gf5_labels(dataset.train)
    y_rank = rank_labels(dataset.train)

    model.train()
    for _epoch in range(epochs):
        optimiser.zero_grad()
        out = model(x)
        # Summed, not averaged or weighted: each task's loss is on its own
        # scale (BCE for the two binary tasks, CE over 6 classes for rank),
        # and no task is favoured over the others by construction.
        loss = bce(out["gf2_primitive"], y_gf2) + bce(out["gf5_primitive"], y_gf5) \
            + ce(out["rank"], y_rank)
        loss.backward()
        optimiser.step()
    return model


def evaluate_multi(
    model: MultiTaskAccumulatorNet, examples: List[Example], *,
    gf2_bias: float = 0.0, gf5_bias: float = 0.0,
) -> Dict[str, Union[BinaryMetrics, RankMetrics]]:
    model.eval()
    with torch.no_grad():
        out = model(multihot(examples))
    return {
        "gf2_primitive": _binary_metrics(out["gf2_primitive"], labels(examples), bias=gf2_bias),
        "gf5_primitive": _binary_metrics(out["gf5_primitive"], gf5_labels(examples), bias=gf5_bias),
        "rank": _rank_metrics(out["rank"], rank_labels(examples)),
    }


def report(name: str, model: MultiTaskAccumulatorNet, dataset: Dataset,
           *, gf2_bias: float, gf5_bias: float) -> None:
    print(f"\n{name} ({model.trainable_parameter_count()} trainable params)")
    splits = (("natural", dataset.natural), ("real corpus", dataset.real_corpus))
    for split_name, examples in splits:
        m = evaluate_multi(model, examples, gf2_bias=gf2_bias, gf5_bias=gf5_bias)
        gf2 = m["gf2_primitive"]
        gf5 = m["gf5_primitive"]
        rank = m["rank"]
        assert isinstance(gf2, BinaryMetrics) and isinstance(gf5, BinaryMetrics)
        assert isinstance(rank, RankMetrics)
        print(f"  {split_name:<11} n={gf2.n}")
        print(f"    gf2_primitive  always-neg={gf2.baseline_accuracy:.3f}  "
              f"acc={gf2.accuracy:.3f} precision={gf2.precision:.3f} recall={gf2.recall:.3f}")
        print(f"    gf5_primitive  always-neg={gf5.baseline_accuracy:.3f}  "
              f"acc={gf5.accuracy:.3f} precision={gf5.precision:.3f} recall={gf5.recall:.3f}")
        print(f"    rank           always-majority={rank.baseline_accuracy:.3f}  "
              f"acc={rank.accuracy:.3f}  per-class n={rank.per_class_n}")


def main() -> None:
    random.seed(0)
    dataset = build_dataset(sequences=4000, seed=0)
    gf2_rate = sum(e.label for e in dataset.natural) / len(dataset.natural)
    gf5_rate = sum(e.gf5_primitive for e in dataset.natural) / len(dataset.natural)
    gf2_bias = prior_correction(gf2_rate)
    gf5_bias = prior_correction(gf5_rate)
    print(f"train={len(dataset.train)} (balanced on gf2_primitive)  "
          f"natural={len(dataset.natural)} "
          f"(gf2 {gf2_rate:.1%} positive, gf5 {gf5_rate:.1%} positive)  "
          f"real_corpus={len(dataset.real_corpus)}")
    print(f"prior-correction bias: gf2 {gf2_bias:+.3f}  gf5 {gf5_bias:+.3f}  "
          f"(rank is not calibrated -- multi-class, no single rare-positive prior)")

    physics_model = train_multi(kind="physics", dataset=dataset)
    report("physics (frozen, 5-dim, 3 tasks)", physics_model, dataset,
            gf2_bias=gf2_bias, gf5_bias=gf5_bias)

    baseline5_model = train_multi(kind="baseline", embed_dim=PHYSICS_DIM, dataset=dataset)
    report("baseline-5 (trained, 3 tasks)", baseline5_model, dataset,
            gf2_bias=gf2_bias, gf5_bias=gf5_bias)

    exomatrix_model = train_multi(kind="exomatrix", dataset=dataset)
    report("exomatrix (frozen, 25-dim, 3 tasks)", exomatrix_model, dataset,
            gf2_bias=gf2_bias, gf5_bias=gf5_bias)

    baseline25_model = train_multi(kind="baseline", embed_dim=EXOMATRIX_DIM, dataset=dataset)
    report("baseline-25 (trained, 3 tasks)", baseline25_model, dataset,
            gf2_bias=gf2_bias, gf5_bias=gf5_bias)


if __name__ == "__main__":
    main()
