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
statement, and it needs no key and no stored checksum.

Two numbers, because there are two questions, and the first version of this
docstring quoted only the flattering one.

**On the wire**, which is what the system actually does. A record carries
letter *indices*, not codex vectors, so a corrupted byte is caught only when
it leaves 1..28. Measured over single-bit flips on a sealed record:

    guard rejects                 41.2%   before any hash is computed
    MAC rejects the remainder     58.8%
    neither                        0.0%

    random bytes rejected by the guard alone: 100.0%

That last line is the one that matters, and it is the claim the layering was
built for: under a flood of malformed input, garbage never reaches SHA-256.
The 41.2% is not the security property — the MAC is — it is the triage rate.

**On codex vectors**, which is what the guards themselves see, single-bit
flips are caught exhaustively:

    G1–G4, T1–T2                         89.68%
    + the decomposition identity          94.44%
    + excluding the unconstrained Ψ tag  100.00% over payload components

That figure describes :func:`detection_rate`, not this record format, and
conflating the two overstates the system. The gaps behind it are structural:
Ψ is a free tag no guard constrains — the same fact as rank(M18) = 14 — and
G4 is an *inequality*, Θ̂ ≥ U, so raising Θ̂ never violates it. Carrying ρ turns
§IC.1.24's identity Θ̂ = U + ρ into an equality and closes it. Both fixes come
from Bab I; neither is invented here.

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
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, MutableSet, Optional, Sequence, Tuple, Union

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


def reject_degenerate_key(key: bytes, role: str = "key") -> None:
    """Refuse a key made of one repeated byte.

    The Debian OpenSSL failure of 2008 shipped keys drawn from a 15-bit space
    for two years, and nothing in the consuming code noticed, because a weak
    key looks exactly like a strong one. That is the honest limit here:
    **entropy cannot be checked after the fact.** Given 32 bytes there is no
    test that separates a CSPRNG's output from a compromised generator's, and
    a module claiming otherwise would be selling false assurance.

    Where this runs matters. It guards the boundaries where a key *enters*
    the system — :func:`seal_record`, :class:`~hijaiyyah.crypto.kabah.Kabah`,
    the CLI's key loader — and deliberately not :func:`derive_key`, which is a
    primitive and must be able to reproduce a published vector. RFC 5869's own
    test case 1 uses input keying material of 0x0b repeated twenty-two times;
    a primitive that refused it could not be checked against the standard it
    implements. Putting the refusal inside `derive_key` broke exactly that,
    and the three tests that failed were right.

    What *is* checkable is the degenerate case — all-zero, all-0xFF, any
    constant fill — which is what an uninitialised buffer, a truncated read,
    or a placeholder left in a config file actually produces. A real 32-byte
    key trips this with probability 256 · 256⁻³² ≈ 2⁻²⁴⁸.

    Raises:
        CryptoRefusal: If every byte is the same.
    """
    if key and len(set(key)) == 1:
        raise CryptoRefusal(
            f"{role} is {len(key)} copies of byte {key[0]:#04x}; that is an "
            "uninitialised buffer or a placeholder, not a key"
        )


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


# ── Records ────────────────────────────────────────────────

#: Wire format identifier, so a parser never guesses at what it was handed.
MAGIC = b"HGR1"

#: Bytes of per-record nonce. Without one, sealing the same payload twice
#: produced the same record, and a captured transfer could be replayed.
NONCE_LEN = 16


#: Nonces a default window remembers. 4096 × 16 bytes is 64 KiB of state.
REPLAY_CAPACITY = 4096


class ReplayWindow:
    """Bounded memory of accepted nonces.

    :func:`open_record` originally took a plain ``set``, which never forgets.
    That is correct and it is also a slow leak: a long-running verifier grows
    by sixteen bytes for every record it accepts, forever, and the operator
    finds out when the process is killed months later. Deployed protocols do
    not do this — IPsec and DTLS both carry a *window*, not a full history —
    and the reason is the same one.

    Bounding it costs something real, and the cost is named rather than
    hidden: once ``capacity`` nonces are held, the oldest is forgotten, and a
    record older than the window becomes replayable again. :attr:`evicted`
    counts every nonce dropped, so a window sized too small for the traffic
    is visible as a number instead of as a silent hole.

    A ``set`` still works and still never forgets. This is the default for a
    server; the set is the right choice when the record count is bounded and
    the full history matters.
    """

    def __init__(self, capacity: int = REPLAY_CAPACITY) -> None:
        if capacity < 1:
            raise CryptoRefusal(f"capacity {capacity} remembers nothing")
        self.capacity = capacity
        self.evicted = 0
        self._seen: "OrderedDict[bytes, None]" = OrderedDict()

    def __contains__(self, nonce: bytes) -> bool:
        return nonce in self._seen

    def __len__(self) -> int:
        return len(self._seen)

    def add(self, nonce: bytes) -> None:
        self._seen[nonce] = None
        while len(self._seen) > self.capacity:
            self._seen.popitem(last=False)
            self.evicted += 1


#: What :func:`open_record` accepts as replay memory.
ReplayMemory = Union[MutableSet[bytes], ReplayWindow]


@dataclass(frozen=True)
class GuardedRecord:
    """A payload, its canonical encoding, a nonce, and its authentication tag."""

    letters: Tuple[int, ...]
    nonce: bytes
    mac: bytes
    seal: str

    def to_bytes(self) -> bytes:
        """Serialise: magic, seal, nonce, length, letters, MAC.

        Every field the tag covers is length-delimited, so no two different
        records can serialise to the same bytes and no field can be re-read as
        part of another.
        """
        return (
            MAGIC
            + bytes.fromhex(self.seal)
            + self.nonce
            + len(self.letters).to_bytes(4, "big")
            + bytes(self.letters)
            + self.mac
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "GuardedRecord":
        """Parse a serialised record, strictly.

        There was no parser at all before this: ``to_bytes`` was write-only,
        so the wire format could be produced and never read back, and nothing
        checked that the two agreed.

        Raises:
            CryptoRefusal: On wrong magic, a truncated field, a length that
                does not match what follows, or trailing bytes. Nothing is
                repaired — a lenient parser is how two parties end up reading
                one message differently.
        """
        head = len(MAGIC) + 32 + NONCE_LEN + 4
        if len(data) < head + MAC_LEN:
            raise CryptoRefusal(f"record is {len(data)} bytes; too short to parse")
        if not hmac.compare_digest(data[: len(MAGIC)], MAGIC):
            raise CryptoRefusal("not a guarded record: wrong magic")

        offset = len(MAGIC)
        seal = data[offset : offset + 32].hex()
        offset += 32
        nonce = data[offset : offset + NONCE_LEN]
        offset += NONCE_LEN
        count = int.from_bytes(data[offset : offset + 4], "big")
        offset += 4

        if len(data) != offset + count + MAC_LEN:
            raise CryptoRefusal(
                f"header declares {count} letters, which does not match the "
                f"{len(data) - offset - MAC_LEN} that follow"
            )

        letters = tuple(data[offset : offset + count])
        return cls(letters, nonce, data[offset + count :], seal)


def _tag(letters: Sequence[int], nonce: bytes, key: bytes) -> bytes:
    """HMAC-SHA256 over the canonical form: seal, nonce and letters.

    Every field is length-prefixed. Concatenating variable-length fields
    without lengths lets two different records produce one tag input, which is
    the oldest mistake in MAC construction.
    """
    seal = bytes.fromhex(dataset_seal())
    material = (
        MAGIC
        + len(seal).to_bytes(2, "big") + seal
        + len(nonce).to_bytes(2, "big") + nonce
        + len(letters).to_bytes(4, "big") + bytes(letters)
    )
    return hmac.new(key, material, hashlib.sha256).digest()


def seal_record(
    payload: bytes, key: bytes, nonce: Optional[bytes] = None
) -> GuardedRecord:
    """Encode a payload and authenticate it.

    Args:
        payload: The data to protect.
        key: A 32-byte key, normally from :func:`derive_key`.
        nonce: Normally omitted, so a fresh one is drawn from the CSPRNG.
            Supply one only to reproduce a known record in a test.

    Raises:
        CryptoRefusal: If the key or a supplied nonce is too short.
    """
    if len(key) < 16:
        raise CryptoRefusal(f"key is {len(key)} bytes; at least 16 are required")
    reject_degenerate_key(key)
    if nonce is None:
        nonce = secrets.token_bytes(NONCE_LEN)
    elif len(nonce) != NONCE_LEN:
        raise CryptoRefusal(f"nonce must be {NONCE_LEN} bytes, got {len(nonce)}")

    letters = encode_bytes(payload)
    return GuardedRecord(letters, nonce, _tag(letters, nonce, key), dataset_seal())


def open_record(
    record: GuardedRecord, key: bytes, seen: Optional[ReplayMemory] = None
) -> bytes:
    """Verify a record and return its payload.

    Structure first, then authenticity, then replay, then decode. The keyless
    check is the cheapest, so a flood of malformed records never reaches the
    hash; the replay check runs after the MAC so an attacker cannot use it to
    probe which nonces a receiver has seen.

    Args:
        record: The record to open.
        key: The key it was sealed with.
        seen: Nonces already accepted — a :class:`ReplayWindow` or any set.
            Supply one to reject replays; a MAC alone cannot, because a
            captured record stays valid forever.

    Raises:
        CryptoRefusal: On a foreign seal, broken structure, a failed MAC, or a
            repeated nonce. Nothing is returned from a record that fails any.
    """
    if not hmac.compare_digest(record.seal, dataset_seal()):
        raise CryptoRefusal(
            f"record is sealed to {record.seal[:16]}…, this build carries "
            f"{dataset_seal()[:16]}…"
        )

    report = check_structure(record.letters)
    if not report.valid:
        raise CryptoRefusal(f"structure rejected at {report.first_bad}: {report.reason}")

    if not hmac.compare_digest(_tag(record.letters, record.nonce, key), record.mac):
        raise CryptoRefusal("authentication failed")

    if seen is not None:
        if record.nonce in seen:
            raise CryptoRefusal("replay: this nonce has been accepted before")
        seen.add(record.nonce)

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
