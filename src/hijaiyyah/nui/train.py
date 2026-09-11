"""Train and honestly compare the physics, exomatrix, and baseline embeddings.

Run as ``python3 -m hijaiyyah.nui.train``. Raw accuracy is not reported
alone: positives (primitive, period 31) are ~4.5% of the natural
distribution, so a model that always predicts "not primitive" scores ~95.5%
while never once being right about the thing this task actually asks --
that always-negative rule is reported explicitly as `baseline_accuracy`
alongside every real result, the same way this project's other benchmarks
report what a null model gets before claiming a trained one beats it.

THE FIRST VERSION OF THIS TRAINING RUN WAS MISCALIBRATED, AND THE FIX IS KEPT
VISIBLE RATHER THAN QUIETLY APPLIED. Training on a 50/50-balanced set (see
dataset.py) teaches a decision boundary calibrated to a 50% prior; the real
world here is ~4.5% positive, so every model -- physics, baseline, and a
raw-18-dimension upper bound tried during development -- scored BELOW the
always-negative baseline on raw accuracy (0.51, 0.61, 0.39 against 0.955)
despite genuinely-above-chance recall (0.68-0.84 against a ~4.5% base rate).
That is the textbook signature of train/eval prior mismatch, not evidence
the features carry no signal. The correction is the standard, analytically
justified one for exactly this situation -- shift the decision threshold by
the known log-odds gap between the training prior (50%) and the measured
natural prior, not a threshold hunted for on the evaluation set itself.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional

import torch
from torch import nn

from .dataset import Dataset, Example, build_dataset
from .model import EXOMATRIX_DIM, PHYSICS_DIM, EmbeddingKind, LetterAccumulatorNet, labels, multihot

#: Measured, not assumed: natural positive rate from a large random sample
#: (see dataset.py's build_dataset docstring and README.md). Recomputed from
#: the dataset actually built each run, not hard-coded, so it cannot drift
#: from what training data really contains.
TRAIN_PRIOR = 0.5


@dataclass
class Metrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    baseline_accuracy: float  # always predicting the majority class (not-primitive)
    n: int
    n_positive: int


def prior_correction(natural_positive_rate: float, train_prior: float = TRAIN_PRIOR) -> float:
    """Log-odds shift from a model trained at `train_prior` to a decision
    calibrated for `natural_positive_rate` -- King & Zeng (2001)'s standard
    correction for training on a class-balanced resample of a rare-event
    population, applied here to a real ~4.5% prior rather than assumed."""

    def logit(p: float) -> float:
        return math.log(p / (1 - p))

    return logit(natural_positive_rate) - logit(train_prior)


def evaluate(
    model: LetterAccumulatorNet, examples: List[Example], *, logit_bias: float = 0.0
) -> Metrics:
    model.eval()
    with torch.no_grad():
        logits = model(multihot(examples)) + logit_bias
        pred = (torch.sigmoid(logits) >= 0.5).float()
    y = labels(examples)

    tp = float(((pred == 1) & (y == 1)).sum())
    fp = float(((pred == 1) & (y == 0)).sum())
    fn = float(((pred == 0) & (y == 1)).sum())
    tn = float(((pred == 0) & (y == 0)).sum())
    n = len(examples)
    n_pos = int(y.sum())

    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    baseline_accuracy = (n - n_pos) / n if n else 0.0

    return Metrics(accuracy, precision, recall, f1, baseline_accuracy, n, n_pos)


def train_one(
    *,
    kind: EmbeddingKind,
    dataset: Dataset,
    epochs: int = 500,
    lr: float = 0.02,
    seed: int = 0,
    embed_dim: Optional[int] = None,
) -> LetterAccumulatorNet:
    torch.manual_seed(seed)
    model = LetterAccumulatorNet(kind=kind, embed_dim=embed_dim)
    optimiser = torch.optim.Adam((p for p in model.parameters() if p.requires_grad), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    x = multihot(dataset.train)
    y = labels(dataset.train)

    model.train()
    for _epoch in range(epochs):
        optimiser.zero_grad()
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        optimiser.step()
    return model


def report(name: str, model: LetterAccumulatorNet, dataset: Dataset, *, bias: float) -> None:
    print(f"\n{name} ({model.trainable_parameter_count()} trainable params)")
    for label, examples in (("natural", dataset.natural), ("real corpus", dataset.real_corpus)):
        raw = evaluate(model, examples, logit_bias=0.0)
        cal = evaluate(model, examples, logit_bias=bias)
        print(
            f"  {label:<11} n={raw.n:<6} positives={raw.n_positive:<4} "
            f"always-negative={raw.baseline_accuracy:.3f}  "
            f"raw acc={raw.accuracy:.3f} f1={raw.f1:.3f}  |  "
            f"calibrated acc={cal.accuracy:.3f} precision={cal.precision:.3f} "
            f"recall={cal.recall:.3f} f1={cal.f1:.3f}"
        )


def main() -> None:
    random.seed(0)
    dataset = build_dataset(sequences=4000, seed=0)
    natural_rate = sum(e.label for e in dataset.natural) / len(dataset.natural)
    bias = prior_correction(natural_rate)
    print(
        f"train={len(dataset.train)} (balanced)  "
        f"natural={len(dataset.natural)} ({natural_rate:.1%} positive)  "
        f"real_corpus={len(dataset.real_corpus)}"
    )
    print(
        f"prior-correction logit bias: {bias:+.3f} "
        f"(trained at 50% positive, natural is {natural_rate:.1%})"
    )

    physics_model = train_one(kind="physics", dataset=dataset)
    report("physics embedding (frozen, 5-dim geometric)", physics_model, dataset, bias=bias)

    baseline5_model = train_one(kind="baseline", embed_dim=PHYSICS_DIM, dataset=dataset)
    report("baseline embedding (trained, 5-dim random init)", baseline5_model, dataset, bias=bias)

    # exomatrix: the same 25-cell structure src/hijaiyyah/crypto/cube.py's
    # build_cube()/cube_digest() stacks over all 28 letters and hashes to
    # seed the Ka'bah S-box -- the one place this experiment and CosmicTera's
    # cryptography already share code (core.exomatrix.build_exomatrix).
    exomatrix_model = train_one(kind="exomatrix", dataset=dataset)
    report(
        "exomatrix embedding (frozen, 25-dim -- Ka'bah's S-box seed structure)",
        exomatrix_model,
        dataset,
        bias=bias,
    )

    baseline25_model = train_one(kind="baseline", embed_dim=EXOMATRIX_DIM, dataset=dataset)
    report("baseline embedding (trained, 25-dim random init)", baseline25_model, dataset, bias=bias)


if __name__ == "__main__":
    main()
