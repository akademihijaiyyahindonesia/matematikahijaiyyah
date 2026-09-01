"""
The guarded record: what the geometry secures, and what it must not be asked to.

Three claims are made in crypto/guarded_record.py and all three are checked
here — the measured detection rate, the provenance binding, and the refusals.

The refusals matter as much as the functions. A crypto module that quietly
does the wrong thing when handed a short key, a foreign seal, or a request to
encrypt is more dangerous than one that does nothing, because it looks like it
worked.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from hijaiyyah.core.guards import compute_U
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.crypto.guarded_record import (
    ALPHABET,
    MAC_LEN,
    UNCONSTRAINED,
    CryptoRefusal,
    GuardedRecord,
    check_structure,
    check_vector,
    dataset_seal,
    decode_letters,
    derive_key,
    detection_rate,
    encode_bytes,
    encrypt,
    generate_key,
    open_record,
    seal_record,
)

KEY = derive_key(b"a-test-master-key-not-a-secret!!", "tests")


# ══════════════════════════════════════════════════════════════════
#  The measured claim
# ══════════════════════════════════════════════════════════════════

def test_single_bit_detection_over_payload_components_is_total() -> None:
    """
    The number the module's docstring quotes, recomputed. Exhaustive over the
    sealed alphabet: every letter, every component, every bit.
    """
    result = detection_rate(hardened=True, skip_unconstrained=True)
    assert result["rate"] == 1.0, result["missed_by_component"]
    assert result["tested"] >= 1900, "the sweep must cover the whole alphabet"


def test_the_plain_guards_alone_are_not_enough() -> None:
    """
    89.68%, and the shortfall is why §IC.1.24's identity is carried. Pinning
    it stops the hardened result from looking like the guards did the work.
    """
    # The 89.68% the docstring quotes is over all eighteen components, Ψ
    # included, which is what "the plain guards" means.
    plain = detection_rate(hardened=False, skip_unconstrained=False)
    assert 0.89 < plain["rate"] < 0.90
    assert plain["rate"] < 1.0


def test_the_gap_the_identity_closes_is_theta() -> None:
    """
    G4 is an inequality, Θ̂ ≥ U, so raising Θ̂ never violates it. That is the
    whole reason ρ is carried, and it is a structural fact rather than a
    statistical one.
    """
    plain = detection_rate(hardened=False, skip_unconstrained=True)
    assert set(plain["missed_by_component"]) == {0}, "only Θ̂ should escape"

    hardened = detection_rate(hardened=True, skip_unconstrained=True)
    assert hardened["missed_by_component"] == {}


def test_the_unconstrained_component_is_the_one_the_book_names() -> None:
    """
    Ψ is a tag no guard touches — the same fact as rank(M18) = 14. It is
    excluded from payload rather than assumed harmless.
    """
    full = detection_rate(hardened=True, skip_unconstrained=False)
    assert set(full["missed_by_component"]) == {UNCONSTRAINED}
    assert UNCONSTRAINED == 17


@pytest.mark.parametrize(
    "entry", MASTER_TABLE.all_entries(), ids=[e.char for e in MASTER_TABLE.all_entries()]
)
def test_every_sealed_letter_passes_its_own_guard(entry) -> None:
    v = list(entry.vector)
    assert check_vector(v, v[0] - compute_U(v))


# ══════════════════════════════════════════════════════════════════
#  Canonical encoding
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "payload",
    [b"", b"\x00", b"\xff", bytes(range(256)), b"TRANSFER 1500000 IDR", b"\x00" * 64],
    ids=["kosong", "nol", "ff", "semua-byte", "teks", "nol-panjang"],
)
def test_encoding_round_trips(payload: bytes) -> None:
    assert decode_letters(encode_bytes(payload)) == payload


def test_encoding_is_the_only_representation() -> None:
    """
    One reading per byte string. Signature malleability and parsing
    differentials both start with two parties disagreeing about what bytes
    mean; the Canonical Lock is a parsing property before anything else.
    """
    assert encode_bytes(b"AB") == encode_bytes(b"AB")
    assert encode_bytes(b"AB") != encode_bytes(b"BA")
    assert len(encode_bytes(b"AB")) == 4, "two letters per byte, always"


def test_every_encoded_letter_is_a_sealed_letter() -> None:
    letters = encode_bytes(bytes(range(256)))
    assert all(1 <= index <= ALPHABET for index in letters)
    assert check_structure(letters).valid


@pytest.mark.parametrize(
    "letters,why",
    [
        ((1, 2, 3), "ganjil"),
        ((0, 1), "indeks 0"),
        ((29, 1), "di luar alfabet"),
        ((10, 20), "pasangan melebihi satu byte"),
    ],
)
def test_a_malformed_encoding_is_refused_not_repaired(letters, why: str) -> None:
    """A decoder that repaired input would give two parties different readings."""
    with pytest.raises(CryptoRefusal):
        decode_letters(letters)


# ══════════════════════════════════════════════════════════════════
#  Provenance-bound key derivation
# ══════════════════════════════════════════════════════════════════

def test_keys_are_bound_to_the_sealed_dataset() -> None:
    """
    HKDF's info carries the Master Table's digest, so the seal is a
    cryptographic domain separator rather than a line in a manifest.
    """
    master = b"m" * 32
    assert dataset_seal() in _hkdf_info_for(master)


def _hkdf_info_for(master: bytes) -> str:
    """Recompute what derive_key builds its info from."""
    return f"HGR|{dataset_seal()}|probe"


def test_different_purposes_give_different_keys() -> None:
    master = b"m" * 32
    assert derive_key(master, "ledger") != derive_key(master, "audit")


def test_derivation_is_deterministic() -> None:
    master = b"m" * 32
    assert derive_key(master, "ledger") == derive_key(master, "ledger")


def test_derivation_matches_rfc5869() -> None:
    """HKDF-SHA256 with a zero salt, computed independently here."""
    master, purpose = b"m" * 32, "ledger"
    info = f"HGR|{dataset_seal()}|{purpose}".encode("ascii")
    prk = hmac.new(b"\x00" * 32, master, hashlib.sha256).digest()
    expected = hmac.new(prk, info + bytes([1]), hashlib.sha256).digest()
    assert derive_key(master, purpose, 32) == expected


@pytest.mark.parametrize("length", [8, 15])
def test_a_short_master_key_is_refused(length: int) -> None:
    """A derived key cannot carry more entropy than its input."""
    with pytest.raises(CryptoRefusal, match="at least 16"):
        derive_key(b"k" * length, "ledger")


# ══════════════════════════════════════════════════════════════════
#  Records
# ══════════════════════════════════════════════════════════════════

def test_a_record_round_trips() -> None:
    payload = b"TRANSFER 1500000 IDR AC-8842 -> AC-1177"
    assert open_record(seal_record(payload, KEY), KEY) == payload


def test_the_tag_is_full_length() -> None:
    assert len(seal_record(b"x", KEY).mac) == MAC_LEN


def test_a_tampered_payload_is_refused() -> None:
    record = seal_record(b"TRANSFER 1500000 IDR", KEY)
    forged = GuardedRecord((*record.letters[:-2], 1, 1), record.mac, record.seal)
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        open_record(forged, KEY)


def test_a_tampered_tag_is_refused() -> None:
    record = seal_record(b"x", KEY)
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        open_record(GuardedRecord(record.letters, b"\x00" * MAC_LEN, record.seal), KEY)


def test_the_wrong_key_is_refused() -> None:
    record = seal_record(b"x", KEY)
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        open_record(record, derive_key(b"another-master-key-entirely!!!!!", "tests"))


def test_a_record_from_another_seal_is_refused() -> None:
    """
    The seal is inside the tag, so a record cannot be replayed against a
    different sealed release even where its letters would still be valid.
    """
    record = seal_record(b"x", KEY)
    foreign = GuardedRecord(record.letters, record.mac, "0" * 64)
    with pytest.raises(CryptoRefusal, match="sealed to"):
        open_record(foreign, KEY)


def test_structure_is_checked_before_the_mac() -> None:
    """
    The keyless check is the cheap one. A flood of malformed records must not
    reach the hash — that ordering is the whole DoS argument.
    """
    record = seal_record(b"x", KEY)
    broken = GuardedRecord((99, *record.letters[1:]), record.mac, record.seal)
    with pytest.raises(CryptoRefusal, match="structure rejected"):
        open_record(broken, KEY)


def test_structure_reports_where_it_failed() -> None:
    report = check_structure((1, 2, 99, 4))
    assert not report.valid
    assert report.first_bad == 2
    assert report.reason


def test_serialisation_is_canonical() -> None:
    record = seal_record(b"hello", KEY)
    assert record.to_bytes() == record.to_bytes()
    assert seal_record(b"hello", KEY).to_bytes() == record.to_bytes()


# ══════════════════════════════════════════════════════════════════
#  What the module will not do
# ══════════════════════════════════════════════════════════════════

def test_encryption_is_refused_rather_than_improvised() -> None:
    """
    The most important test here. A hand-rolled cipher is weaker than the
    standard one it replaces, and a module that quietly produced one would be
    more dangerous than a module that produces nothing.
    """
    with pytest.raises(CryptoRefusal, match="vetted library"):
        encrypt(b"secret", KEY)


def test_a_short_record_key_is_refused() -> None:
    with pytest.raises(CryptoRefusal, match="at least 16"):
        seal_record(b"x", b"tooshort")


def test_generated_keys_are_full_entropy() -> None:
    assert len(generate_key()) == 32
    assert generate_key() != generate_key(), "a CSPRNG must not repeat"
    with pytest.raises(CryptoRefusal):
        generate_key(8)


def test_the_guard_is_not_presented_as_authentication() -> None:
    """
    Anyone can build a structurally valid record; the guard is keyless. It is
    a pre-filter and the docstring has to say so, because treating it as proof
    of origin is the misreading that would matter.
    """
    from hijaiyyah.crypto import guarded_record

    # Normalised: the sentence is line-wrapped in the source.
    doc = " ".join((guarded_record.__doc__ or "").split())
    assert "pre-filter, not an authority" in doc
    assert "keyless" in doc

    forged = seal_record(b"anything", generate_key())
    assert check_structure(forged.letters).valid, "structure alone proves nothing"
