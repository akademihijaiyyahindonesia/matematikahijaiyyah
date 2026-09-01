# -*- coding: utf-8 -*-
"""Ka'bah — Kriptografi Absorpsi Byte Atas Hijaiyyah.

The security system, composed. Everything under this name already exists in
the modules beside it; what was missing was one place that says which layer
carries which guarantee, because a system whose parts are individually honest
can still mislead if the composition is left to the reader.

Five layers, and the number that matters for each:

    0  Canonical    codex encoding             one reading per value
    1  Guard        keyless, O(1)              100% of random garbage
    2  Absorption   tawaf sponge over the cube AES-class S-box   [EH]
    3  Authentic    HMAC-SHA256, HKDF          the actual security
    4  Confidential refused                    use AES-256-GCM

**Stages are not layers, and the difference is worth keeping.** Layers are what
the system guarantees; stages are the order it has to be built in, and
:meth:`Kabah.stages` carries them. Semi-log comes first because there is no
cube without a substitution to fill it, and no circuit without a cube to walk.
Getting that order wrong is not academic: building the substitution as a
shuffle instead of a semi-log map cost 10 against 4 and 92 against 112, and no
later stage could have recovered it.

**Layer 3 is the security.** Layers 0–2 are structure, triage and hypothesis.
If layer 3 were removed the system would have none, and no amount of geometry
would replace it. That sentence is the reason this module exists.

**Layer 1 is not authentication.** It has no key, so anyone can produce a
structurally valid record. Its job is to reject a flood before it reaches
SHA-256, and it does that completely — random bytes never survive it. Reading
it as proof of origin is the one misreading that would matter.

**Layer 2 is [EH] and stays there.** The tawaf sponge is measured — an S-box
at the algebraic optimum (differential uniformity 4, nonlinearity 112, no
fixed points), 28 rounds against a measured diffusion floor of three, capacity
576 bits — and measurement is not cryptanalysis. The margin now matches
Keccak's posture, which removes the last technical objection and none of the
epistemic one: no one has attacked this. It is a candidate, not a primitive.
:func:`fingerprint` says so and points at SHA-256.

**Layer 4 is refused, and that is a security property.** A hand-rolled cipher
is weaker than the standard one it replaces, not stronger.

Why "Ka'bah". The architecture is a cube, absorption circles it, and both come
from the book rather than from the name: §IIE.2.1 gives the 5×5 exomatrix, and
the circuit decomposes its face into a sixteen-lane perimeter that takes the
data and a nine-lane core that input never touches. The name describes the
shape that was already there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set

from hijaiyyah.crypto import cube
from hijaiyyah.crypto.guarded_record import (
    ALPHABET,
    CryptoRefusal,
    GuardedRecord,
    check_structure,
    dataset_seal,
    derive_key,
    encode_bytes,
    generate_key,
    open_record,
    seal_record,
)

#: The expansion, kept here so the name cannot drift from what it stands for.
NAME = "Ka'bah"
EXPANSION = "Kriptografi Absorpsi Byte Atas Hijaiyyah"

#: Layer 3 is the one that carries security. Named rather than implied.
AUTHORITATIVE_LAYER = 3


@dataclass(frozen=True)
class Stage:
    """One construction step, what it produces, and what measures it."""

    order: int
    name: str
    produces: str
    evidence: str


#: How the system is built, in the order it has to be built in. Each stage
#: needs the one before it: there is no cube without a substitution to fill it,
#: no circuit without a cube to walk, and nothing to authenticate until the
#: sponge exists.
STAGES = (
    Stage(
        1, "Semi-log", "the substitution",
        "log/antilog over GF(2⁸); differential uniformity 4, nonlinearity 112, "
        "no fixed points — the algebraic optimum, and AES's figures",
    ),
    Stage(
        2, "Cube", "the state",
        "5×5×28 from the sealed exomatrices (§IIE.2.1); 5×5 lanes of 64 bits "
        "is a 1600-bit state, the size Keccak settled on",
    ),
    Stage(
        3, "Tawaf", "rate and capacity",
        "the circuit splits the face into a 16-lane perimeter and a 9-lane "
        "core; 1024-bit rate, 576-bit capacity, ~288-bit security; four tawaf "
        "of seven circuits is 28 rounds, 9.3x the measured diffusion floor",
    ),
    Stage(
        4, "Absorption", "the input path",
        "one byte or one bit per clock along the circuit; the bit schedule "
        "spreads a byte across eight nodes — measured, and it makes no "
        "difference to diffusion, which is why it is here for the hardware",
    ),
    Stage(
        5, "Composition", "the system",
        "canonical encoding, keyless triage, HMAC-SHA256 over a seal-bound "
        "key; layers 0–2 are structure, layer 3 is the security",
    ),
)


@dataclass(frozen=True)
class Layer:
    """One layer, what it guarantees, and what it does not."""

    index: int
    name: str
    guarantee: str
    label: str
    keyed: bool


LAYERS = (
    Layer(0, "Canonical", "one reading per value; no parsing ambiguity", "DP", False),
    Layer(1, "Guard", "rejects malformed input in O(1), without a key", "CC", False),
    Layer(2, "Absorption", "tawaf sponge, AES-class S-box, 288-bit capacity", "EH", False),
    Layer(3, "Authentic", "HMAC-SHA256 over a seal-bound key", "VF", True),
    Layer(4, "Confidential", "refused — use AES-256-GCM from a vetted library", "—", True),
)


class Kabah:
    """The composed system.

    Args:
        master: Master keying material, at least 16 bytes. Omit to generate one.
        purpose: Domain label. Keys for different purposes never coincide, and
            neither do keys for different sealed releases.
        track_replays: Keep accepted nonces so a captured record cannot be
            replayed. A MAC alone cannot detect that.
    """

    def __init__(
        self,
        master: Optional[bytes] = None,
        purpose: str = "default",
        track_replays: bool = True,
    ) -> None:
        self._master = master if master is not None else generate_key()
        self._key = derive_key(self._master, purpose)
        self._seen: Optional[Set[bytes]] = set() if track_replays else None
        self.purpose = purpose

    # ── Layers 0–3 ───────────────────────────────────────────────

    def seal(self, payload: bytes) -> GuardedRecord:
        """Encode, then authenticate. Layers 0 and 3."""
        return seal_record(payload, self._key)

    def open(self, record: GuardedRecord) -> bytes:
        """Triage, authenticate, reject replays, decode. Layers 1, 3, 0.

        Raises:
            CryptoRefusal: On a foreign seal, broken structure, a failed MAC,
                or a repeated nonce. Nothing is returned from a record that
                fails any of them.
        """
        return open_record(record, self._key, self._seen)

    def triage(self, record: GuardedRecord) -> bool:
        """Layer 1 alone: is this worth spending a hash on?

        Keyless and O(1). A true answer means only that the record is
        well-formed — it says nothing at all about who wrote it.
        """
        return check_structure(record.letters).valid

    # ── Layer 2 ──────────────────────────────────────────────────

    @staticmethod
    def fingerprint(data: bytes, length: int = 32) -> bytes:
        """Tawaf sponge digest. **[EH] — not a vetted hash.**

        Use hashlib.sha256 for anything that matters. This is here to be
        measured and to give the FPGA something to stream.
        """
        return cube.digest(data, length)

    # ── Layer 4 ──────────────────────────────────────────────────

    @staticmethod
    def encrypt(payload: bytes) -> bytes:
        """Not implemented, deliberately.

        Raises:
            CryptoRefusal: Always. Encrypt with AES-256-GCM or
                ChaCha20-Poly1305 from a library whose implementation is
                constant-time, then protect the ciphertext with a record from
                this system. The layers compose; the substitution does not.
        """
        raise CryptoRefusal(
            "Ka'bah defines no cipher. Use AES-256-GCM or ChaCha20-Poly1305 "
            "from a vetted library and seal the ciphertext with layer 3"
        )

    # ── What it is, stated ───────────────────────────────────────

    @staticmethod
    def stages() -> Dict[str, object]:
        """The construction order, and what measures each step.

        Stages are how it is built; layers are what it guarantees. Keeping
        them apart matters: the substitution is stage 1 and belongs to no
        layer, and layer 3 is stage 5's work and not a step of its own.
        """
        return {
            "name": NAME,
            "expansion": EXPANSION,
            "stages": [
                {
                    "order": stage.order,
                    "name": stage.name,
                    "produces": stage.produces,
                    "evidence": stage.evidence,
                }
                for stage in STAGES
            ],
        }

    @staticmethod
    def describe() -> Dict[str, object]:
        """Every layer, its guarantee, its epistemic label, and the numbers."""
        return {
            "name": NAME,
            "expansion": EXPANSION,
            "seal": dataset_seal(),
            "alphabet": ALPHABET,
            "authoritative_layer": AUTHORITATIVE_LAYER,
            "layers": [
                {
                    "index": layer.index,
                    "name": layer.name,
                    "guarantee": layer.guarantee,
                    "label": layer.label,
                    "keyed": layer.keyed,
                }
                for layer in LAYERS
            ],
            "sponge": {
                "state_bits": cube.STATE_LANES * cube.LANE_BITS,
                "rate_bytes": cube.RATE,
                "rate_bits": cube.RATE_BITS,
                "capacity_bits": cube.CAPACITY_BITS,
                "security_bits": cube.SECURITY_BITS,
                "circuits": cube.CIRCUITS,
            },
            "substitution": {
                "polynomial": cube.POLYNOMIAL,
                "generator": cube.GENERATOR,
                "affine_constant": cube.AFFINE_C,
                "differential_uniformity": 4,
                "nonlinearity": 112,
                "fixed_points": 0,
            },
        }


__all__ = [
    "AUTHORITATIVE_LAYER",
    "EXPANSION",
    "LAYERS",
    "NAME",
    "CryptoRefusal",
    "Kabah",
    "Layer",
    "encode_bytes",
    "generate_key",
]
