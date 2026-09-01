"""
The published specification must describe the implementation it publishes.

docs/kabah/SPEC.md exists so someone can reimplement the permutation and
attack it. A specification that has drifted from the code is worse than none:
an attacker who finds nothing has told you nothing, because they attacked a
different construction.

So every number the spec quotes is recomputed here, and every test vector is
regenerated rather than trusted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hijaiyyah.crypto import cube as C

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "kabah" / "SPEC.md"
VECTORS = ROOT / "docs" / "kabah" / "test_vectors.json"

TEXT = SPEC.read_text(encoding="utf-8")
DATA = json.loads(VECTORS.read_text(encoding="utf-8"))


# ── The vectors are the implementation's own output ──────────────

def test_the_sbox_vector_is_the_sbox() -> None:
    assert DATA["sbox"] == list(C.SBOX)
    assert len(DATA["sbox"]) == 256


def test_the_round_constants_are_the_round_constants() -> None:
    assert [int(c, 16) for c in DATA["round_constants"]] == list(C.ROUND_CONSTANTS)
    assert len(DATA["round_constants"]) == C.CIRCUITS == 28


def test_the_field_parameters_match() -> None:
    field = DATA["field"]
    assert field["polynomial"] == C.POLYNOMIAL
    assert field["generator"] == C.GENERATOR
    assert field["affine_constant"] == C.AFFINE_C


def test_the_tawaf_path_matches() -> None:
    assert DATA["tawaf_path"] == list(C.TAWAF_PATH)


def test_every_parameter_matches() -> None:
    p = DATA["parameters"]
    assert p["lane_bits"] == C.LANE_BITS
    assert p["state_lanes"] == C.STATE_LANES
    assert p["rate_bytes"] == C.RATE
    assert p["capacity_bits"] == C.CAPACITY_BITS
    assert p["circuit"] == C.CIRCUIT
    assert p["tawaf"] == C.TAWAF
    assert p["rounds"] == C.CIRCUITS


@pytest.mark.parametrize(
    "name,message",
    [
        ("empty", b""),
        ("a", b"a"),
        ("kabah", "Ka'bah".encode()),
        ("range128", bytes(range(128))),
        ("zeros1024", bytes(1024)),
    ],
)
def test_each_published_digest_is_reproducible(name: str, message: bytes) -> None:
    """Regenerated, not trusted. A stale vector would send an attacker astray."""
    assert DATA["digests"][name] == C.digest(message).hex()


def test_the_published_permutation_outputs_are_reproducible() -> None:
    perm = DATA["permutation"]
    assert [int(x, 16) for x in perm["zero_state"]] == C.permute([0] * 25)
    assert [int(x, 16) for x in perm["unit_state"]] == C.permute([1] + [0] * 24)


# ── The prose quotes the same numbers ────────────────────────────

def test_the_spec_quotes_the_current_round_count() -> None:
    assert "7 sirkuit × 4 tawaf = **28**" in TEXT
    assert str(C.CIRCUITS) == "28"


def test_the_spec_quotes_the_current_field() -> None:
    assert f"polinomial = 0x{C.POLYNOMIAL:03X}" in TEXT
    assert f"generator = {C.GENERATOR}" in TEXT
    assert f"`c = 0x{C.AFFINE_C:02X}`" in TEXT


def test_the_spec_quotes_the_digests_it_publishes() -> None:
    for name in ("empty", "a", "kabah", "range128"):
        assert DATA["digests"][name] in TEXT, f"{name} is in the JSON but not the prose"


def test_the_spec_quotes_the_measured_sbox_properties() -> None:
    assert "| Keseragaman diferensial | 4 | 4 |" in TEXT
    assert "| Nonlinearitas | 112 | 112 |" in TEXT
    assert C.differential_uniformity() == 4
    assert C.nonlinearity() == 112


def test_the_spec_quotes_the_measured_diffusion_floor() -> None:
    """The round count rests on this measurement; the spec has to show it."""
    assert "jenuh pada ronde 3" in TEXT
    assert "9,3×" in TEXT


# ── What the spec must refuse to claim ───────────────────────────

def test_the_spec_labels_itself_a_hypothesis() -> None:
    assert "**[EH]**" in TEXT
    assert "belum pernah dikriptanalisis" in TEXT


def test_the_spec_invites_attack_and_says_what_kind() -> None:
    """
    A publication without a concrete ask gets nothing back. Reduced-round
    attacks are the number the project does not have.
    """
    assert "Undangan" in TEXT
    assert "ronde-tereduksi" in TEXT


def test_the_spec_disclaims_what_it_must() -> None:
    assert "Bukan sandi" in TEXT
    assert "Bukan pengganti SHA-256" in TEXT
    assert "Geometrinya tidak memberi keamanan" in TEXT


def test_the_spec_names_which_layer_carries_security() -> None:
    assert "lapis 3" in TEXT.lower()
    assert "HMAC-SHA256" in TEXT


# ── The inheritance argument, and its numbers ────────────────────

def test_the_spec_states_what_is_inherited_and_what_is_not() -> None:
    """
    The strongest claim the design can make is that it recombines components
    whose analysis is mature. It is only honest while the spec also says what
    that does not cover — the composition — and gives the flaw as evidence.
    """
    assert "Apa yang diwarisi" in TEXT
    assert "Yang tidak diwarisi" in TEXT
    assert "rank 1276" in TEXT, "the composition failure has to be the evidence"


def test_keccak_chi_really_has_the_properties_the_spec_quotes() -> None:
    """
    The comparison is only worth making if it is right, so χ is recomputed
    here rather than cited.
    """
    chi = [
        sum(
            (((x >> i) & 1) ^ ((1 - ((x >> ((i + 1) % 5)) & 1)) & ((x >> ((i + 2) % 5)) & 1)))
            << i
            for i in range(5)
        )
        for x in range(32)
    ]
    worst = 0
    for a in range(1, 32):
        counts = [0] * 32
        for x in range(32):
            counts[chi[x] ^ chi[x ^ a]] += 1
        worst = max(worst, max(counts))
    assert worst == 8, f"χ differential uniformity is {worst}, spec says 8"
    assert "| Keseragaman diferensial | 8 (relatif 0,250) | 4 (relatif **0,016**) |" in TEXT


def test_the_degree_argument_is_stated_with_its_arithmetic() -> None:
    """
    Algebraic degree is what sets a round count. The spec has to show the
    arithmetic, not just assert the conclusion.
    """
    assert "2^11 = 2048" in TEXT and "7^4 = 2401" in TEXT
    assert "ronde 11" in TEXT and "ronde 4" in TEXT


def test_the_spec_does_not_claim_inherited_trust() -> None:
    """The distinction the whole section rests on."""
    assert "Bukan bahwa Ka'bah mewarisi kepercayaan — ia tidak" in TEXT
