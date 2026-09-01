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
    sponge = [layer for layer in LAYERS if layer.name == "Absorption"][0]
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
