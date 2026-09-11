"""Testing external claims about NUI against this repo's own sealed data.

A PDF titled "Codex NUI 1.1.1 ORBIT" was supplied as a reference for this
project's NUI work. Most of it is unfalsifiable (Quranic verses cited as
evidence for specific rotation angles; the same 270 degrees applied
indiscriminately to DNA, planetary orbits, brainwaves, and emotions; real
physics equations -- the wave equation, Boltzmann entropy -- quoted with no
derivation connecting them to letter geometry). None of that is testable,
so none of it is encoded here.

Two things in it ARE testable against data this repo already has sealed and
guard-checked, and this module tests them rather than assuming them:

  1. AMM (Angular Morphology Mapping) claims specific rotation angles per
     letter, presented as "not made up... deterministic, reproducible" --
     exactly the kind of claim this project's own discipline (VF/CC/EH/AT
     labels; cosmic-codex-jim/LIMITS.md's three retracted readings) says to
     verify rather than repeat.

  2. The document's "3 Kelas Utama NUI" groups letters into three claimed
     functional categories. If that grouping reflects real structure, the
     letters within a group should be measurably more similar to each other
     -- in the geometric features already established in nui/features.py --
     than a random group of the same size.

Both come back negative -- see check_angle_claims() and group_coherence()
below, and tests/test_ai/test_nui_claims.py for the numbers.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..core.master_table import MASTER_TABLE
from .features import vector_features

ENTRIES = {e.char: e for e in MASTER_TABLE.all_entries()}
ALL_CHARS: Tuple[str, ...] = tuple(ENTRIES.keys())


@dataclass(frozen=True)
class AngleClaim:
    letter: str
    claimed_degrees: int
    source: str  # page/slide in the PDF this was transcribed from


#: Every explicit letter -> rotation-angle claim in the document, transcribed
#: exactly as printed, with where it came from. Not a summary of the
#: document's intent -- the literal numbers it wrote down.
DOCUMENT_ANGLE_CLAIMS: Tuple[AngleClaim, ...] = (
    AngleClaim("ج", 270, "p.5 AMM example table; p.6 Sec 1.3; p.7 Sec 1.8"),
    AngleClaim("د", 90, "p.5 AMM example table; p.7 Sec 1.8"),
    AngleClaim("ر", 45, "p.5 AMM example table; p.7 Sec 1.8"),
    AngleClaim("ق", 210, "p.5 AMM example table"),
    AngleClaim("ض", 360, "p.7 Sec 1.8"),
    AngleClaim("ص", 360, "p.7 Sec 1.8; p.6 Sec 1.3 (O=1, theta=360)"),
    AngleClaim("ن", 90, "p.6 Sec 1.3 (T=1, C=1, theta=90)"),
)


def actual_theta_degrees(letter: str) -> int:
    """Theta-hat from the sealed Master Table, in degrees (the quantum is
    90 degrees per unit -- see cosmic-codex-jim/README.md, Jim's own
    Theta-hat=3 -> 270 degrees)."""
    return ENTRIES[letter].vector[0] * 90


def check_angle_claims() -> List[Tuple[AngleClaim, int, bool]]:
    """(claim, actual, matches) for every claim in DOCUMENT_ANGLE_CLAIMS."""
    return [
        (claim, actual_theta_degrees(claim.letter),
         actual_theta_degrees(claim.letter) == claim.claimed_degrees)
        for claim in DOCUMENT_ANGLE_CLAIMS
    ]


#: The document's "3 Kelas Utama NUI" grouping (p.19-20). Group B is left out
#: -- its OCR transcription was internally inconsistent (repeated and
#: reordered characters) in a way A and C's shorter lists were not, and a
#: mis-transcribed group would test the transcription, not the claim. The
#: source PDF names a sixth character for Group C read as hamzah (ء); no 29th
#: Master Table letter exists for it, so Group C is tested at n=5, not 6.
LETTER_GROUPS: Dict[str, Tuple[str, ...]] = {
    "A. Kernel Transformasi": ("ج", "م", "ن", "ا", "ح"),
    "C. Energi, Memori & Koneksi": ("ع", "غ", "هـ", "و", "ي"),
}


def _mean_pairwise_distance(chars: Tuple[str, ...]) -> float:
    features = [vector_features(ENTRIES[c].vector).as_tuple() for c in chars]
    pairs = list(itertools.combinations(features, 2))
    total: float = sum(
        sum((a - b) ** 2 for a, b in zip(x, y, strict=True)) ** 0.5
        for x, y in pairs
    )
    return total / len(pairs)


@dataclass(frozen=True)
class CoherenceResult:
    group: str
    n: int
    observed_mean_distance: float
    random_mean_distance: float
    percentile: float  # observed's rank among random same-size groups, 0-100


def group_coherence(*, samples: int = 20000, seed: int = 0) -> List[CoherenceResult]:
    """For each claimed group, where its mean pairwise feature distance
    ranks among `samples` random same-size groups. A LOW percentile (the
    group is more tightly clustered than most random groups) would support
    the claim; a percentile near 50 means the group is statistically
    indistinguishable from picking that many letters at random.
    """
    rng = random.Random(seed)
    results = []
    for name, chars in LETTER_GROUPS.items():
        n = len(chars)
        observed = _mean_pairwise_distance(chars)
        draws = [
            _mean_pairwise_distance(tuple(rng.sample(ALL_CHARS, n)))
            for _ in range(samples)
        ]
        below = sum(1 for d in draws if d <= observed)
        results.append(CoherenceResult(
            group=name, n=n, observed_mean_distance=observed,
            random_mean_distance=sum(draws) / len(draws),
            percentile=100 * below / len(draws),
        ))
    return results
