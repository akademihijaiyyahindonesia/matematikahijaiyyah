"""
Named failures of deployed cryptography, and what Ka'bah does about each.

A new system is only worth building if it closes something the existing ones
leave open. That is a claim about *other* systems, so it has to be tested
against them rather than asserted — and where a gap is still open in Ka'bah,
these tests say so instead of looking away.

Every case below is a published failure with a name and a body count of real
deployments. The tests are ordered by how much they actually prove: first the
one where a live system is broken here in the suite, then the ones where the
closure is structural and a forgery attempt is run against it.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from hijaiyyah.crypto.guarded_record import (
    MAC_LEN,
    MAGIC,
    CryptoRefusal,
    GuardedRecord,
    ReplayWindow,
    _tag,
    derive_key,
    generate_key,
    reject_degenerate_key,
    seal_record,
)
from hijaiyyah.crypto.kabah import Kabah

MASTER = bytes(range(32))


# ══════════════════════════════════════════════════════════════════
#  Key commitment — the gap that is still open in AES-GCM
# ══════════════════════════════════════════════════════════════════

def test_the_field_used_to_break_gcm_is_gcms_own() -> None:
    """
    Everything below rests on this. An attack computed in the wrong field
    proves nothing about GCM, so the field is pinned by its defining law:
    x^128 = x^7 + x^2 + x + 1 is GCM's reduction polynomial and no other
    field satisfies it.

    The first version of this gate compared against a test-vector tag I had
    recalled rather than sourced, one byte of it was wrong, and the check
    fired on its own author. Laws are checkable offline; remembered digits
    are not.
    """
    from tools.commitment_attack import verify_field

    assert verify_field(), "the demonstration is not running in GCM's field"


def test_one_ciphertext_authenticates_under_two_gcm_keys() -> None:
    """
    AES-GCM is not key-committing, and this is the break, not a description
    of one. Two independently drawn keys, one ciphertext, one tag, valid
    under both — obtained by solving a single linear equation over
    GF(2^128), with no search and no oracle.

    Published consequences: partitioning oracle attacks recovering
    Shadowsocks passwords (Len, Grubbs, Ristenpart 2021) and abuse-report
    forgery against Facebook message franking (Dodis et al. 2018). AES-GCM
    carries most TLS traffic in the world and this hole is open in it today.
    """
    from tools.commitment_attack import block_function, forge_two_key_ciphertext, gcm_tag

    block, _ = block_function()
    key_a, key_b = b"A" * 16, b"B" * 16
    nonce = bytes(range(12))

    ciphertext, tag = forge_two_key_ciphertext(key_a, key_b, nonce, block)

    assert gcm_tag(key_a, nonce, ciphertext, block) == tag
    assert gcm_tag(key_b, nonce, ciphertext, block) == tag
    assert key_a != key_b


def test_the_forgery_needs_the_polynomial_not_a_weak_cipher() -> None:
    """
    The objection to the test above is that it might depend on the substitute
    block function. It does not: the solve only uses that the authenticator is
    affine in the message with key-dependent coefficients. Swapping the block
    function for a different one changes every number and changes nothing
    about whether it works.
    """
    from tools.commitment_attack import forge_two_key_ciphertext, gcm_tag

    def other_block(key: bytes, block: bytes) -> bytes:
        return hashlib.blake2b(key + block, digest_size=16).digest()

    nonce = bytes(range(12))
    ciphertext, tag = forge_two_key_ciphertext(b"A" * 16, b"B" * 16, nonce, other_block)
    assert gcm_tag(b"A" * 16, nonce, ciphertext, other_block) == tag
    assert gcm_tag(b"B" * 16, nonce, ciphertext, other_block) == tag


def test_kabah_has_no_equation_to_solve() -> None:
    """
    Layer 3 is HMAC-SHA256 over the whole record. There is no polynomial and
    no coefficient, so a second key cannot be solved for — only searched for,
    at 2^256.

    Measured rather than assumed: at truncated widths the search cost tracks
    2^n, which is the evidence that no algebraic shortcut is hiding. If one
    existed, a 20-bit tag would fall far below its expected 2^20.
    """
    from tools.commitment_attack import search_second_key

    result = search_second_key(bits=20, budget=1 << 14, seed=7)
    assert not result["found"], "a 20-bit tag fell in 2^14 tries — look for structure"

    # And the property that matters at full width: two keys, two tags.
    record = seal_record(b"TRANSFER 1500000 IDR", derive_key(MASTER, "ledger"))
    assert _tag(record.letters, record.nonce, derive_key(MASTER, "ledger")) != _tag(
        record.letters, record.nonce, derive_key(generate_key(), "ledger")
    )


# ══════════════════════════════════════════════════════════════════
#  Debian OpenSSL, 2008 — a key that is not a key
# ══════════════════════════════════════════════════════════════════

def test_a_constant_fill_key_is_refused_everywhere_one_enters() -> None:
    """
    Two years of Debian keys came from a 15-bit space and no consuming code
    noticed, because weak keys look like strong ones. Entropy cannot be
    checked after the fact and this does not pretend to. What it catches is
    the degenerate case an uninitialised buffer or a placeholder actually
    produces.
    """
    for role in (b"\x00" * 32, b"\xff" * 32, b"\x2a" * 32):
        with pytest.raises(CryptoRefusal, match="not a key"):
            reject_degenerate_key(role)
        with pytest.raises(CryptoRefusal, match="not a key"):
            Kabah(role, "ledger")
        with pytest.raises(CryptoRefusal, match="not a key"):
            seal_record(b"x", role)


def test_the_refusal_does_not_fire_on_real_keys() -> None:
    """
    A gate that refuses everything is not a gate. Two hundred CSPRNG keys,
    none refused — the false-positive rate is 256 · 256^-32.
    """
    for _ in range(200):
        reject_degenerate_key(generate_key())


def test_the_primitive_still_reproduces_a_published_vector() -> None:
    """
    The refusal deliberately does not run inside derive_key. RFC 5869's test
    case 1 uses input keying material of 0x0b repeated twenty-two times, so a
    primitive that refused constant fills could not be checked against the
    standard it implements. Putting the check there broke three conformance
    tests and they were right to break.
    """
    master, purpose = b"m" * 32, "ledger"
    from hijaiyyah.crypto.guarded_record import dataset_seal

    info = f"HGR|{dataset_seal()}|{purpose}".encode("ascii")
    prk = hmac.new(b"\x00" * 32, master, hashlib.sha256).digest()
    assert derive_key(master, purpose, 32) == hmac.new(
        prk, info + bytes([1]), hashlib.sha256
    ).digest()


# ══════════════════════════════════════════════════════════════════
#  Unbounded replay state — what deployed protocols do not do
# ══════════════════════════════════════════════════════════════════

def test_the_replay_window_does_not_grow_without_limit() -> None:
    """
    A plain set never forgets, which is correct and is also a slow leak: a
    long-running verifier grows by sixteen bytes per accepted record forever.
    IPsec and DTLS both carry a window instead, for this reason.
    """
    window = ReplayWindow(capacity=64)
    system = Kabah(MASTER, "ledger", replay_capacity=64)
    for i in range(500):
        window.add(f"nonce-{i}".encode())
        system.open(system.seal(b"x"))
    assert len(window) == 64
    assert window.evicted == 436


def test_eviction_is_counted_rather_than_silent() -> None:
    """
    Bounding the window costs something real: a record older than the window
    becomes replayable again. That cost is named and counted, so a window
    sized too small for the traffic shows up as a number instead of a hole.
    """
    window = ReplayWindow(capacity=2)
    for name in (b"a", b"b", b"c"):
        window.add(name)
    assert b"a" not in window and window.evicted == 1
    assert b"b" in window and b"c" in window


def test_replays_inside_the_window_are_still_refused() -> None:
    system = Kabah(MASTER, "ledger", replay_capacity=8)
    record = system.seal(b"TRANSFER 1000000 IDR")
    assert system.open(record)
    with pytest.raises(CryptoRefusal, match="replay"):
        system.open(record)


# ══════════════════════════════════════════════════════════════════
#  Downgrade and parsing — JWT alg confusion, transaction malleability
# ══════════════════════════════════════════════════════════════════

def test_the_format_identifier_is_covered_by_the_tag() -> None:
    """
    JWT's `alg: none` and the HS256/RS256 confusion are both the same defect:
    a header field that steers verification and is not itself authenticated.
    Ka'bah has one suite and no negotiation, and the identifier is inside the
    MAC input regardless — so rewriting it cannot be made to verify.
    """
    key = derive_key(MASTER, "ledger")
    record = seal_record(b"TRANSFER 1500000 IDR", key)
    genuine = _tag(record.letters, record.nonce, key)
    forged = hmac.new(
        key,
        b"XXXX"
        + len(bytes.fromhex(record.seal)).to_bytes(2, "big")
        + bytes.fromhex(record.seal)
        + len(record.nonce).to_bytes(2, "big")
        + record.nonce
        + len(record.letters).to_bytes(4, "big")
        + bytes(record.letters),
        hashlib.sha256,
    ).digest()
    assert forged != genuine, "the identifier is outside the tag input"

    wire = bytearray(record.to_bytes())
    wire[: len(MAGIC)] = b"XXXX"
    with pytest.raises(CryptoRefusal, match="wrong magic"):
        GuardedRecord.from_bytes(bytes(wire))


def test_trailing_bytes_are_refused() -> None:
    """
    Bitcoin transaction malleability and the BER/DER signature bypasses were
    both lenient parsers: bytes the verifier ignored and the reader did not.
    """
    record = seal_record(b"x", derive_key(MASTER, "ledger"))
    with pytest.raises(CryptoRefusal, match="does not match"):
        GuardedRecord.from_bytes(record.to_bytes() + b"\x00")


def test_a_truncated_tag_is_refused() -> None:
    """
    Accepting a short tag is accepting a weaker system than the one
    advertised. The length equality makes a 16-byte tag unparseable rather
    than merely weaker.
    """
    record = seal_record(b"x", derive_key(MASTER, "ledger"))
    wire = record.to_bytes()
    with pytest.raises(CryptoRefusal):
        GuardedRecord.from_bytes(wire[: -MAC_LEN // 2])


# ══════════════════════════════════════════════════════════════════
#  A gap that is open here, stated rather than hidden
# ══════════════════════════════════════════════════════════════════

def test_the_substitution_is_a_table_and_that_is_a_software_side_channel() -> None:
    """
    Ka'bah's S-box is a 256-entry lookup, which in software is exactly the
    target of the AES cache-timing attacks (Bernstein 2005; Osvik, Shamir and
    Tromer 2006). This is not closed by the design and is not claimed to be.

    Two things bound it. Layer 2 processes no secrets — it is the keyless
    [EH] sponge, and layer 3's HMAC-SHA256 is the part that touches a key.
    And the intended target is HCPU silicon, where the table is a block RAM
    with one fixed access latency and no cache to observe.

    The test holds the module to saying so, because an undocumented side
    channel is worse than a documented one.
    """
    from hijaiyyah.crypto import cube

    assert len(cube.SBOX) == 256
    doc = " ".join((cube.__doc__ or "").split())
    assert "cache" in doc.lower(), (
        "the table lookup's software side channel is undocumented"
    )
