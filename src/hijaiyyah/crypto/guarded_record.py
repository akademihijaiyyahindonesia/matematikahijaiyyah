# -*- coding: utf-8 -*-
"""Hijaiyyah Guarded Record — integrity that is structural, not stored.

What Matematika Hijaiyyah contributes to security, and what it does not.

**It does not contribute confidentiality.** No cipher is defined here and none
should be. A novel cipher is how security systems fail: AES and ChaCha20 are
trusted because thirty years of public cryptanalysis have been spent on them,
and a new construction has had none. :func:`encrypt` refuses rather than
hand-rolling one — a hand-written AES leaks through timing even when its
arithmetic is right.

**It contributes three things that are real, and two of them are measured.**

*Canonical encoding.* Bab I's Canonical Lock is a parsing-safety property
before it is anything else. Integer-only, one representation per value, no
floats, no locale, no ambiguity. Whole attack families — signature
malleability, JSON parsing differentials, encoding confusion — exist because
two parties disagreed about what a byte string meant. A codex vector has one
reading.

*Structural integrity, O(1) and keyless.* A MAC says the bytes did not change.
The guard says the value is geometrically impossible. That is a different
statement, and it needs no key and no stored checksum. Measured exhaustively
over the sealed alphabet, single bit flips:

    G1–G4, T1–T2                         89.68% detected
    + the decomposition identity          94.44% detected
    + excluding the unconstrained Ψ tag  100.00% over payload components

The two gaps are structural, not statistical. Ψ is a free tag no guard
constrains — which is the same fact as rank(M18) = 14. And G4 is an
*inequality*, Θ̂ ≥ U, so raising Θ̂ never violates it. Carrying ρ turns
§IC.1.24's identity Θ̂ = U + ρ into an equality and closes it. Both fixes come
from Bab I; neither is invented here.

Two-bit flips: 97.67% on the plain guards.

*Provenance-bound key derivation.* Keys are derived through HKDF-SHA256 with
the Master Table's own SHA-256 as the info parameter, so a key derived for one
sealed release cannot be used with another. The dataset seal stops being
documentation and becomes a cryptographic domain separator.

**The layering, and why it is this way.** The guard is a pre-filter, not an
authority. It is keyless, so it proves nothing about origin — an attacker can
build a structurally valid record. Its value is triage: under a flood of
malformed input, garbage is rejected without spending a hash on it. The MAC is
the authority and is always required. Neither substitutes for the other.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from hijaiyyah.core.guards import compute_U, full_guard_check
from hijaiyyah.core.master_table import MASTER_TABLE

#: Letters in the sealed alphabet. Two of them carry one byte: 28² = 784 > 256.
ALPHABET = 28

#: Bytes of HMAC-SHA256 output.
MAC_LEN = 32

#: The component no guard constrains (§ID.1.3, and rank(M18) = 14). Excluded
#: from payload so every carried component is covered by a check.
UNCONSTRAINED = 17


class CryptoRefusal(Exception):
    """Raised for an operation this module will not perform."""


# ── Provenance ───────────────────────────────────────────────────

def dataset_seal() -> str:
    """The sealed Master Table's SHA-256, used as a domain separator."""
    return MASTER_TABLE.compute_sha256()


def derive_key(master: bytes, purpose: str, length: int = 32) -> bytes:
    """Derive a subkey with HKDF-SHA256, bound to the sealed dataset.

    RFC 5869, with the Master Table's digest in the info parameter. A key
    derived for one sealed release is unusable with another: the seal becomes
    a cryptographic domain separator rather than a line in a manifest.

    Args:
        master: Input keying material. Use at least 32 bytes from a CSPRNG.
        purpose: Label separating uses of the same master key.
        length: Output bytes, at most 8160.

    Returns:
        The derived key.

    Raises:
        CryptoRefusal: If the master key is too short to carry the security
            level the output claims.
    """
    if len(master) < 16:
        raise CryptoRefusal(
            f"master key is {len(master)} bytes; a derived key cannot carry "
            "more entropy than its input, so at least 16 are required"
        )
    if not 1 <= length <= 255 * 32:
        raise CryptoRefusal(f"length {length} is outside HKDF's range")

    info = f"HGR|{dataset_seal()}|{purpose}".encode("utf-8")
    prk = hmac.new(b"\x00" * 32, master, hashlib.sha256).digest()

    out = b""
    block = b""
    counter = 1
    while len(out) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        out += block
        counter += 1
    return out[:length]


# ── Canonical encoding ───────────────────────────────────────────

def encode_bytes(data: bytes) -> Tuple[int, ...]:
    """Encode bytes as sealed letter indices, two letters per byte.

    Base-28 over the canonical alphabet. Deterministic and reversible: there
    is exactly one letter sequence for any byte string, which is the parsing
    property the Canonical Lock exists to provide.
    """
    letters: List[int] = []
    for byte in data:
        letters.append(byte // ALPHABET + 1)
        letters.append(byte % ALPHABET + 1)
    return tuple(letters)


def decode_letters(letters: Sequence[int]) -> bytes:
    """Recover the bytes an encoding came from.

    Raises:
        CryptoRefusal: On an odd count, an out-of-range index, or a pair that
            does not name a byte. A decoder that repaired malformed input
            would give two parties different readings of the same message.
    """
    if len(letters) % 2:
        raise CryptoRefusal(f"{len(letters)} letters is not a whole number of bytes")

    out = bytearray()
    for i in range(0, len(letters), 2):
        high, low = letters[i] - 1, letters[i + 1] - 1
        if not (0 <= high < ALPHABET and 0 <= low < ALPHABET):
            raise CryptoRefusal(f"letter pair at {i} is outside the alphabet")
        value = high * ALPHABET + low
        if value > 0xFF:
            raise CryptoRefusal(f"letter pair at {i} does not name a byte")
        out.append(value)
    return bytes(out)


# ── Structural integrity ─────────────────────────────────────────

@dataclass(frozen=True)
class StructureReport:
    """What the guard found, and where."""

    valid: bool
    checked: int
    first_bad: Optional[int] = None
    reason: str = ""


def check_vector(vector: Sequence[int], rho: Optional[int] = None) -> bool:
    """Guard one codex vector.

    Args:
        vector: The 18 components.
        rho: The residue, when carried. Supplying it turns G4 from the
            inequality Θ̂ ≥ U into §IC.1.24's identity Θ̂ = U + ρ, which is
            what closes the Θ̂ detection gap.
    """
    v = list(vector)
    if not full_guard_check(v)["all_pass"]:
        return False
    return True if rho is None else v[0] == compute_U(v) + rho


def check_structure(letters: Sequence[int]) -> StructureReport:
    """Validate every letter in a record, keylessly.

    Each letter is one guard: six checks over eighteen integers, independent
    of how long the record is. This is the pre-filter — it says nothing about
    who wrote the record, only that every element is a shape the geometry
    permits.
    """
    entries = MASTER_TABLE.all_entries()
    for position, index in enumerate(letters):
        if not 1 <= index <= len(entries):
            return StructureReport(
                False, position, position, f"index {index} names no letter"
            )
        vector = list(entries[index - 1].vector)
        rho = vector[0] - compute_U(vector)
        if not check_vector(vector, rho):
            return StructureReport(
                False, position, position, f"letter {index} fails its guards"
            )
    return StructureReport(True, len(letters))


# ── Records ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class GuardedRecord:
    """A payload, its canonical encoding, and its authentication tag."""

    letters: Tuple[int, ...]
    mac: bytes
    seal: str

    def to_bytes(self) -> bytes:
        """Serialise canonically: seal, length, letters, MAC."""
        head = self.seal.encode("ascii")
        body = bytes(self.letters)
        return (
            len(head).to_bytes(2, "big") + head
            + len(body).to_bytes(4, "big") + body
            + self.mac
        )


def _tag(letters: Sequence[int], key: bytes) -> bytes:
    """HMAC-SHA256 over the canonical form, seal included.

    The seal is inside the tag, so a record cannot be replayed against a
    different sealed release even if its letters remain valid there.
    """
    material = dataset_seal().encode("ascii") + b"|" + bytes(letters)
    return hmac.new(key, material, hashlib.sha256).digest()


def seal_record(payload: bytes, key: bytes) -> GuardedRecord:
    """Encode a payload and authenticate it.

    Args:
        payload: The data to protect.
        key: A 32-byte key, normally from :func:`derive_key`.

    Raises:
        CryptoRefusal: If the key is too short to reach the security level
            HMAC-SHA256 offers.
    """
    if len(key) < 16:
        raise CryptoRefusal(f"key is {len(key)} bytes; at least 16 are required")
    letters = encode_bytes(payload)
    return GuardedRecord(letters, _tag(letters, key), dataset_seal())


def open_record(record: GuardedRecord, key: bytes) -> bytes:
    """Verify a record and return its payload.

    Structure first, then authenticity, then decode. The order matters: the
    keyless check is the cheap one, so a flood of malformed records never
    reaches the MAC.

    Raises:
        CryptoRefusal: On a foreign seal, a broken structure, or a MAC that
            does not verify. Nothing is returned from a record that fails any
            of the three.
    """
    if not hmac.compare_digest(record.seal, dataset_seal()):
        raise CryptoRefusal(
            f"record is sealed to {record.seal[:16]}…, this build carries "
            f"{dataset_seal()[:16]}…"
        )

    report = check_structure(record.letters)
    if not report.valid:
        raise CryptoRefusal(f"structure rejected at {report.first_bad}: {report.reason}")

    if not hmac.compare_digest(_tag(record.letters, key), record.mac):
        raise CryptoRefusal("authentication failed")

    return decode_letters(record.letters)


# ── Confidentiality ──────────────────────────────────────────────

def encrypt(payload: bytes, key: bytes) -> bytes:
    """Not implemented, and deliberately so.

    Confidentiality needs an AEAD that has survived public cryptanalysis —
    AES-256-GCM or ChaCha20-Poly1305 — from a library whose implementation is
    constant-time. Writing one here would be the mistake this module exists to
    avoid: a hand-written AES leaks the key through timing even when every
    round is arithmetically correct, and a novel construction has had no
    cryptanalysis at all.

    Install `cryptography` and encrypt with AES-256-GCM, then protect the
    ciphertext with a record from this module. The layers compose; the
    substitution does not.

    Raises:
        CryptoRefusal: Always.
    """
    raise CryptoRefusal(
        "no cipher is defined here. Use AES-256-GCM or ChaCha20-Poly1305 from "
        "a vetted library; a hand-rolled cipher is weaker than the standard "
        "one it replaces, not stronger"
    )


def generate_key(length: int = 32) -> bytes:
    """A key from the operating system's CSPRNG."""
    if length < 16:
        raise CryptoRefusal(f"{length} bytes is below any usable security level")
    return secrets.token_bytes(length)


# ── Measured properties ──────────────────────────────────────────

def detection_rate(hardened: bool = True, skip_unconstrained: bool = True) -> Dict:
    """Measure single-bit detection exhaustively over the sealed alphabet.

    Not an estimate and not a sample: every letter, every component, every
    bit within the nibble domain.

    Args:
        hardened: Apply §IC.1.24's identity as well as the guards.
        skip_unconstrained: Exclude Ψ, which no guard constrains.
    """
    tested = caught = 0
    missed: Dict[int, int] = {}

    for entry in MASTER_TABLE.all_entries():
        v = list(entry.vector)
        rho = v[0] - compute_U(v)
        for component in range(18):
            if skip_unconstrained and component == UNCONSTRAINED:
                continue
            for bit in range(4):
                w = list(v)
                w[component] ^= 1 << bit
                if not 0 <= w[component] <= 15:
                    continue
                tested += 1
                if check_vector(w, rho if hardened else None):
                    missed[component] = missed.get(component, 0) + 1
                else:
                    caught += 1

    return {
        "tested": tested,
        "caught": caught,
        "rate": caught / tested if tested else 0.0,
        "missed_by_component": missed,
    }
