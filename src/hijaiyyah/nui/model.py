"""A permutation-invariant classifier over accumulated letters.

An example is a SET of letters (dataset.py never repeats a letter within one
sequence, matching rtl/programs/letters.hasm's own accumulate-each-once
pattern), and the label depends only on the sum of their v18 vectors --
order genuinely does not matter. So the model sums each selected letter's
embedding and reads a small MLP off the sum: not a simplified stand-in for a
sequence model, but the actual permutation-invariant operation this problem
has (the "Deep Sets" architecture -- sum-pool over a per-element embedding
-- is the standard way to build a network whose output is provably
order-independent, which is what the ground truth actually is here).

Three embedding kinds, same architecture otherwise:

  physics   -- 5-dim, nui.features.feature_matrix() (titik, garis, lengkung,
               theta, rho), FROZEN.
  exomatrix -- 25-dim, each letter's full 5x5 exomatrix (core.exomatrix.
               build_exomatrix), flattened, FROZEN. Not a new representation
               invented for this comparison: it is the exact structure
               src/hijaiyyah/crypto/cube.py's build_cube() stacks over all
               28 letters and hashes (cube_digest()) to derive the Ka'bah
               S-box seed -- the one place NUI's exomatrix work and
               CosmicTera's cryptography already share code. Comparing this
               embedding against physics's 5-number summary asks whether the
               S-box's own seed material carries more signal for THIS task
               than the summary does.
  baseline  -- same dimension as whichever frozen embedding it is being
               compared against, randomly initialised and trained end to
               end: matched capacity, no geometric prior.

Matching the dimension per comparison is what makes it mean something -- a
wider learned baseline would win on capacity alone, not on lacking the
prior.
"""

from __future__ import annotations

from typing import Literal, Optional, Sequence

import torch
from torch import nn

from ..core.exomatrix import build_exomatrix
from ..core.master_table import MASTER_TABLE
from .dataset import NUM_LETTERS, Example
from .features import feature_matrix

PHYSICS_DIM = 5
EXOMATRIX_DIM = 25

EmbeddingKind = Literal["physics", "exomatrix", "baseline"]


def multihot(examples: Sequence[Example]) -> torch.Tensor:
    """[len(examples), NUM_LETTERS] float tensor, 1 where a letter was
    accumulated by that example's prefix."""
    batch = torch.zeros(len(examples), NUM_LETTERS)
    for row, ex in enumerate(examples):
        for idx in ex.letter_indices:
            batch[row, idx] = 1.0
    return batch


def labels(examples: Sequence[Example]) -> torch.Tensor:
    return torch.tensor([1.0 if ex.label else 0.0 for ex in examples])


def gf5_labels(examples: Sequence[Example]) -> torch.Tensor:
    return torch.tensor([1.0 if ex.gf5_primitive else 0.0 for ex in examples])


def rank_labels(examples: Sequence[Example]) -> torch.Tensor:
    """int64, for CrossEntropyLoss -- not float, unlike the two binary tasks."""
    return torch.tensor([ex.rank for ex in examples], dtype=torch.long)


def exomatrix_matrix() -> list:
    """28x25 table, Master Table order: each letter's full 5x5 exomatrix,
    flattened row-major -- the same values src/hijaiyyah/crypto/cube.py's
    build_cube() stacks and cube_digest() hashes to seed the Ka'bah S-box."""
    return [
        [x for row in build_exomatrix(e.vector) for x in row]
        for e in MASTER_TABLE.all_entries()
    ]


def _build_embedding(kind: EmbeddingKind, embed_dim: Optional[int]) -> nn.Embedding:
    """The one place embedding construction happens -- LetterAccumulatorNet
    (Fase 0, one task) and MultiTaskAccumulatorNet (Fase 1, several tasks)
    both call this rather than each keeping its own copy of the
    physics/exomatrix/baseline switch, so the two cannot drift apart on what
    "physics embedding" or "exomatrix embedding" means (R1)."""
    if kind == "physics":
        dim = PHYSICS_DIM
        init = feature_matrix()
    elif kind == "exomatrix":
        dim = EXOMATRIX_DIM
        init = exomatrix_matrix()
    elif kind == "baseline":
        if embed_dim is None:
            raise ValueError("baseline needs embed_dim, to match whatever "
                              "frozen embedding it is being compared against")
        dim = embed_dim
        init = None
    else:
        raise ValueError(f"unknown embedding kind: {kind!r}")

    embedding = nn.Embedding(NUM_LETTERS, dim)
    if init is not None:
        with torch.no_grad():
            embedding.weight.copy_(torch.tensor(init, dtype=torch.float32))
        embedding.weight.requires_grad_(False)
    return embedding


class LetterAccumulatorNet(nn.Module):
    """multihot(28) -> sum-pooled embedding -> MLP -> primitivity logit."""

    def __init__(self, *, kind: EmbeddingKind, hidden: int = 16,
                 embed_dim: Optional[int] = None):
        super().__init__()
        self.kind = kind
        self.embedding = _build_embedding(kind, embed_dim)
        dim = self.embedding.embedding_dim

        self.head = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, multihot_batch: torch.Tensor) -> torch.Tensor:
        # [B, 28] @ [28, dim] -> [B, dim]: the sum of the selected letters'
        # embeddings, which is exactly the accumulation this task measures.
        summed = multihot_batch @ self.embedding.weight
        out: torch.Tensor = self.head(summed).squeeze(-1)
        return out

    def trainable_parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class MultiTaskAccumulatorNet(nn.Module):
    """Same trunk as LetterAccumulatorNet -- multihot(28) -> sum-pooled
    embedding, one embedding kind, exactly the same _build_embedding this
    file already uses -- but one head PER TASK instead of one head total.

    `tasks` maps a task name to its output width: 1 for a binary task
    (BCEWithLogitsLoss, matching LetterAccumulatorNet's convention), or
    >1 for a small classification task (CrossEntropyLoss) such as
    dataset.exomatrix_rank's 0..5 (dataset.RANK_CLASSES). Sharing one trunk
    across genuinely different questions about the same accumulated letters
    is Fase 1's whole point (see NUI/ROADMAP.md) -- if the trunk only ever
    helped one task, it would not be evidence of a shared representation,
    just one model wearing several output layers.
    """

    def __init__(self, *, kind: EmbeddingKind, tasks: dict, hidden: int = 16,
                 embed_dim: Optional[int] = None):
        super().__init__()
        if not tasks:
            raise ValueError("tasks must name at least one task")
        self.kind = kind
        self.task_names = tuple(tasks.keys())
        self.embedding = _build_embedding(kind, embed_dim)
        dim = self.embedding.embedding_dim

        self.heads = nn.ModuleDict({
            name: nn.Sequential(
                nn.Linear(dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, out_dim),
            )
            for name, out_dim in tasks.items()
        })

    def forward(self, multihot_batch: torch.Tensor) -> dict:
        summed = multihot_batch @ self.embedding.weight
        outputs = {}
        for name in self.task_names:
            out = self.heads[name](summed)
            # A width-1 head is a binary logit, squeezed to match
            # LetterAccumulatorNet's [B] convention rather than [B, 1];
            # a wider head is left as [B, num_classes] for CrossEntropyLoss.
            outputs[name] = out.squeeze(-1) if out.shape[-1] == 1 else out
        return outputs

    def trainable_parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
