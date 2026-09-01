"""
Ka'bah as a composition: which layer carries which guarantee.

The parts were each honest on their own. What was missing was one place
saying how they fit, because a system assembled from honest parts can still
mislead if the reader has to infer the composition — and the inference people
reach for is that the geometry provides the security. It does not. Layer 3
does, and these tests hold the module to saying so.
"""

from __future__ import annotations

import pytest

from hijaiyyah.crypto import cube
from hijaiyyah.crypto.kabah import (
    AUTHORITATIVE_LAYER,
    EXPANSION,
    LAYERS,
    NAME,
    CryptoRefusal,
    Kabah,
)

MASTER = bytes(range(32))


# ══════════════════════════════════════════════════════════════════
#  The name and what it stands for
# ══════════════════════════════════════════════════════════════════

def test_the_expansion_matches_the_name_letter_for_letter() -> None:
    """
    Ka'bah has five letters and the expansion has five words. An acronym whose
    expansion does not line up is worse than no acronym: it invites the reader
    to check, and the check fails.
    """
    assert NAME == "Ka'bah"
    letters = [c for c in NAME.upper() if c.isalpha()]
    words = EXPANSION.split()
    assert len(letters) == len(words) == 5
    assert [w[0].upper() for w in words] == letters


def test_every_word_of_the_expansion_is_a_real_word() -> None:
    """
    The first proposal used "Astrac" and "Byttera", which are not words in any
    language. These are.
    """
    assert EXPANSION == "Kriptografi Absorpsi Byte Atas Hijaiyyah"


# ══════════════════════════════════════════════════════════════════
#  Which layer carries the security
# ══════════════════════════════════════════════════════════════════

def test_the_layers_are_ordered_and_complete() -> None:
    assert [layer.index for layer in LAYERS] == [0, 1, 2, 3, 4]
    assert len({layer.name for layer in LAYERS}) == 5


def test_only_the_authoritative_layer_is_labelled_verified() -> None:
    """
    Structure is [DP], triage is [CC], the sponge is [EH]. Exactly one layer
    carries [VF], and it is the one with a key.
    """
    verified = [layer for layer in LAYERS if layer.label == "VF"]
    assert len(verified) == 1
    assert verified[0].index == AUTHORITATIVE_LAYER == 3
    assert verified[0].keyed


def test_the_keyless_layers_are_marked_keyless() -> None:
    """
    Layers 0–2 have no key, so none of them can say anything about origin.
    Marking it is what stops triage being read as authentication.
    """
    for layer in LAYERS[:3]:
        assert not layer.keyed, f"layer {layer.index} claims a key it does not have"


def test_the_docstring_names_the_layer_that_carries_security() -> None:
    from hijaiyyah.crypto import kabah

    doc = " ".join((kabah.__doc__ or "").split())
    assert "Layer 3 is the security" in doc
    assert "Layer 1 is not authentication" in doc
    assert "Layer 2 is [EH] and stays there" in doc


def test_the_sponge_is_reported_as_a_hypothesis() -> None:
    sponge = next(layer for layer in LAYERS if layer.name == "Absorption")
    assert sponge.label == "EH"
    doc = " ".join((Kabah.fingerprint.__doc__ or "").split())
    assert "[EH]" in doc
    assert "sha256 for anything that matters" in doc.lower()


# ══════════════════════════════════════════════════════════════════
#  The composition works
# ══════════════════════════════════════════════════════════════════

def test_a_record_round_trips() -> None:
    system = Kabah(MASTER, "tests")
    payload = b"TRANSFER 1500000 IDR AC-8842"
    assert system.open(system.seal(payload)) == payload


def test_triage_is_keyless_and_proves_nothing_about_origin() -> None:
    """
    A record sealed with a key nobody shares still passes triage. That is the
    property, not a defect — and it is why triage cannot stand alone.
    """
    stranger = Kabah(purpose="not-ours")
    ours = Kabah(MASTER, "tests")
    forged = stranger.seal(b"anything")

    assert ours.triage(forged), "triage should accept any well-formed record"
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        ours.open(forged)


def test_replays_are_refused_by_default() -> None:
    system = Kabah(MASTER, "tests")
    record = system.seal(b"TRANSFER 1000000 IDR")
    assert system.open(record)
    with pytest.raises(CryptoRefusal, match="replay"):
        system.open(record)


def test_replay_tracking_can_be_turned_off_explicitly() -> None:
    """Off is a choice a caller makes, not a default they fall into."""
    system = Kabah(MASTER, "tests", track_replays=False)
    record = system.seal(b"x")
    assert system.open(record) == b"x"
    assert system.open(record) == b"x"


def test_purposes_do_not_share_keys() -> None:
    ledger = Kabah(MASTER, "ledger")
    audit = Kabah(MASTER, "audit")
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        audit.open(ledger.seal(b"x"))


def test_a_generated_master_key_is_used_when_none_is_given() -> None:
    assert Kabah().seal(b"x").mac != Kabah().seal(b"x").mac


def test_encryption_is_refused() -> None:
    with pytest.raises(CryptoRefusal, match="vetted library"):
        Kabah.encrypt(b"secret")


# ══════════════════════════════════════════════════════════════════
#  What describe() reports must be what the modules hold
# ══════════════════════════════════════════════════════════════════

def test_the_description_quotes_the_sponge_it_actually_uses() -> None:
    """
    A summary that drifted from the implementation would be the most
    convincing wrong thing in the repository.
    """
    sponge = Kabah.describe()["sponge"]
    assert sponge["state_bits"] == cube.STATE_LANES * cube.LANE_BITS == 1600
    assert sponge["rate_bytes"] == cube.RATE
    assert sponge["capacity_bits"] == cube.CAPACITY_BITS == 576
    assert sponge["security_bits"] == cube.SECURITY_BITS == 288
    assert sponge["circuits"] == cube.CIRCUITS == 7


def test_the_description_quotes_the_current_seal() -> None:
    from hijaiyyah.crypto.guarded_record import dataset_seal

    assert Kabah.describe()["seal"] == dataset_seal()


def test_the_description_names_the_authoritative_layer() -> None:
    description = Kabah.describe()
    assert description["authoritative_layer"] == AUTHORITATIVE_LAYER
    labels = {entry["name"]: entry["label"] for entry in description["layers"]}
    assert labels["Authentic"] == "VF"
    assert labels["Absorption"] == "EH"


# ══════════════════════════════════════════════════════════════════
#  Stages: the order it has to be built in
# ══════════════════════════════════════════════════════════════════

def test_the_stages_are_ordered_and_start_with_the_substitution() -> None:
    """
    Semi-log is stage 1 because there is no cube without a substitution to
    fill it, and no circuit without a cube to walk. Building the substitution
    as a shuffle instead cost 10 against 4 and 92 against 112, and no later
    stage could have recovered it.
    """
    from hijaiyyah.crypto.kabah import STAGES

    assert [stage.order for stage in STAGES] == [1, 2, 3, 4, 5]
    assert STAGES[0].name == "Semi-log"
    assert STAGES[-1].name == "Composition"


def test_stages_are_not_layers() -> None:
    """
    Layers are what the system guarantees; stages are how it is built. The
    substitution belongs to no layer, and layer 3 is stage 5's work rather
    than a step of its own — collapsing the two would hide both.
    """
    from hijaiyyah.crypto.kabah import STAGES

    assert len(STAGES) == len(LAYERS) == 5
    assert {s.name for s in STAGES} != {layer.name for layer in LAYERS}


def test_the_reported_substitution_is_the_one_in_use() -> None:
    substitution = Kabah.describe()["substitution"]
    assert substitution["polynomial"] == cube.POLYNOMIAL
    assert substitution["generator"] == cube.GENERATOR
    assert substitution["affine_constant"] == cube.AFFINE_C
    assert substitution["differential_uniformity"] == cube.differential_uniformity()
    assert substitution["nonlinearity"] == cube.nonlinearity()
    assert substitution["fixed_points"] == len(
        [x for x in range(256) if cube.SBOX[x] == x]
    ) == 0


def test_bit_absorption_spreads_a_byte_across_nodes() -> None:
    """
    Stage 4's spectrum schedule. Eight bits reach eight nodes; lane-major
    would put all eight in one.
    """
    state, step = [0] * cube.STATE_LANES, 0
    for _ in range(8):
        state, step = cube.absorb_bit(state, 1, step)
    assert sum(1 for lane in state if lane) == 8
    assert step == 8


def test_the_bit_schedule_is_documented_as_a_negative_result() -> None:
    """
    It makes no difference to diffusion, measured at every message length.
    Saying so is worth more than a justification invented afterwards, and the
    docstring has to keep saying it.
    """
    doc = " ".join((cube.absorb_bit.__doc__ or "").split())
    assert "the result is negative" in doc
    assert "for the hardware" in doc or "input path" in doc


def test_the_bit_and_lane_paths_differ_but_lose_nothing() -> None:
    """
    They do not, and that is the design: the bit path spreads across the ring
    where the lane path fills one lane. What must hold is that neither loses
    or invents a bit.
    """
    # All ones, so every node on the ring receives a set bit. A patterned
    # value such as 0xA5A5… only reaches eight of the sixteen, which is a
    # property of the pattern and not of the schedule.
    value = (1 << cube.LANE_BITS) - 1
    expected = bin(value).count("1")

    by_bit, step = [0] * cube.STATE_LANES, 0
    for i in range(cube.LANE_BITS):
        by_bit, step = cube.absorb_bit(by_bit, (value >> i) & 1, step)

    by_lane, _ = cube.absorb_lane([0] * cube.STATE_LANES, value, 0)

    assert sum(bin(lane).count("1") for lane in by_bit) == expected
    assert sum(bin(lane).count("1") for lane in by_lane) == expected
    assert by_bit != by_lane, "the two schedules are meant to differ"
    assert sum(1 for lane in by_bit if lane) == cube.RATE_LANES
    assert sum(1 for lane in by_lane if lane) == 1
