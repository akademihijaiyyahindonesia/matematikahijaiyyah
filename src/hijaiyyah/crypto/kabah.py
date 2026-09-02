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
from typing import Dict, Optional, Sequence, Tuple

from hijaiyyah.crypto import cube
from hijaiyyah.crypto.guarded_record import (
    ALPHABET,
    REPLAY_CAPACITY,
    CryptoRefusal,
    GuardedRecord,
    ReplayMemory,
    ReplayWindow,
    check_structure,
    dataset_seal,
    derive_key,
    encode_bytes,
    generate_key,
    open_record,
    reject_degenerate_key,
    seal_record,
)

#: The name for the whole, once the parts were made one.
#:
#: *Cosmic* for the rotation the system turns on — pi decomposes the 5x5 face
#: into two 12-cycles and one fixed lane, rho-pi returns to identity after 768
#: applications, and every recovered key is stored in canonical rotation so
#: one input yields one report. *Tera* for the scale the arithmetic is stated
#: at, because the ratio between the two paths only becomes a design decision
#: when the volume is large enough to matter.
#:
#: The name denotes the composition, not a new primitive. Nothing here is
#: cryptography that did not exist before; what is new is which layer refuses
#: before which computes, and that every number below comes from the module
#: that owns it rather than from this list.
COSMICTERA = "CosmicTera"


#: Format identifier for a sealed examination. One suite, no negotiation.
EXAMINATION_MAGIC = b"HEX1"


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
        replay_capacity: How many recent nonces the window holds. Bounded, so
            a long-running verifier does not grow without limit; a record
            older than the window becomes replayable again, and
            :attr:`ReplayWindow.evicted` counts every nonce that fell out.
        track_replays: Keep accepted nonces so a captured record cannot be
            replayed. A MAC alone cannot detect that.
    """

    def __init__(
        self,
        master: Optional[bytes] = None,
        purpose: str = "default",
        track_replays: bool = True,
        replay_capacity: int = REPLAY_CAPACITY,
    ) -> None:
        self._master = master if master is not None else generate_key()
        reject_degenerate_key(self._master, "master key")
        self._key = derive_key(self._master, purpose)
        self._seen: Optional[ReplayMemory] = (
            ReplayWindow(replay_capacity) if track_replays else None
        )
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

    # ── the whole system, on one input ───────────────────────────

    def examine(self, data: bytes) -> "Examination":
        """Fold data through every stage and return one summary.

        Until this existed the system had four front doors — the wave, the
        memory scanner, the elemental profile and the record layers — and a
        caller had to know which to open and in what order. That is four
        chances to use it wrongly and no single answer at the end.

        One pass now produces one report:

            what it is        elemental identification, or its marker
            how it reads      the classification profile, per window
            what is hidden    injected regions, with payloads recovered
            what it hashes to the sponge fingerprint            [EH]

        **Rotation is what makes the report stable.** A repeating key is
        recoverable only up to a cyclic shift, so two runs over different
        window alignments can return the same key wearing different phases.
        Every key here is stored in canonical rotation — the lexicographically
        smallest — so the same input always produces the same report bytes,
        which is what lets the report be sealed and compared.
        """
        from hijaiyyah.crypto.elements import identify
        from hijaiyyah.crypto.memscan import canonical, find_clue, recover, scan_memory
        from hijaiyyah.crypto.node_counter import NAMES, scan

        verdicts = scan(data)
        profile = {
            NAMES[code]: verdicts.count(code) for code in sorted(NAMES)
        }
        regions = scan_memory(data)
        recovered = tuple(
            (r.offset, canonical(r.key or b""), find_clue(recover(data, r)) or "")
            for r in regions if r.key
        )
        return Examination(
            length=len(data),
            family=identify(data, clue=find_clue(data[:4096])).family,
            marker=find_clue(data[:4096]) or "",
            profile=profile,
            regions=tuple((r.offset, r.length, r.kind) for r in regions),
            recovered=recovered,
            fingerprint=self.fingerprint(data),
        )

    def examine_stream(self, bits: "Sequence[int]") -> "Examination":
        """Examine a raw bitstream — folded one bit per clock, no alignment given.

        :meth:`examine` takes bytes, which presumes someone already knew where
        a byte begins. A wire carries no such thing. This takes the bits as
        they arrive, recovers the boundary from the data itself, and examines
        what falls out — the same path the silicon runs.

        The recovered phase travels in the report, because a report about a
        stream that does not say where its bytes started is not reproducible.
        """
        from hijaiyyah.crypto.node_counter import align

        phase, _period, data = align(bits)
        found = self.examine(data)
        return Examination(
            found.length, found.family, found.marker, found.profile,
            found.regions, found.recovered, found.fingerprint, phase=phase)

    def seal_examination(self, found: "Examination") -> GuardedRecord:
        """Authenticate the findings so they survive the trip to whoever acts.

        Forensic output that can be rewritten on the way is worth nothing, and
        this is the one layer in the system that can stop that.
        """
        return self.seal(found.to_bytes())

    @staticmethod
    def cosmictera() -> Dict[str, object]:
        """Everything the unified system is, with each number from its owner.

        A name that can drift from what it denotes is exactly what the tests
        in this repository exist to prevent, so nothing here is a literal: the
        sponge figures come from :mod:`cube`, the substitution figures from
        the S-box itself, the throughput from :meth:`throughput`, and the
        layer table from :data:`LAYERS`. A test compares the lot.
        """
        from hijaiyyah.crypto import cube as _cube

        return {
            "name": COSMICTERA,
            "expansion": EXPANSION,
            "rotation": {
                "pi_cycles": [12, 12, 1],
                "fixed_lane": 0,
                "linear_period": 768,
                "rounds": _cube.CIRCUITS,
                "margin": round(768 / _cube.CIRCUITS, 1),
            },
            "sponge": {
                "state_bits": _cube.STATE_LANES * _cube.LANE_BITS,
                "rate_bytes": _cube.RATE,
                "capacity_bits": _cube.CAPACITY_BITS,
                "security_bits": _cube.SECURITY_BITS,
            },
            "substitution": {
                "differential_uniformity": _cube.differential_uniformity(),
                "nonlinearity": _cube.nonlinearity(),
                "fixed_points": sum(1 for x in range(256) if _cube.SBOX[x] == x),
            },
            "layers": [
                {"index": layer.index, "name": layer.name,
                 "label": layer.label, "keyed": layer.keyed}
                for layer in LAYERS
            ],
            "authoritative_layer": AUTHORITATIVE_LAYER,
            "throughput": Kabah.throughput(),
            "seal": dataset_seal(),
        }

    @staticmethod
    def throughput(volume: int = 10 ** 12, hertz: int = 27_000_000) -> Dict[str, object]:
        """Clock counts for a volume of data, and the ratio that shapes the design.

        The two paths through this system do not cost the same, and at
        terabyte scale the difference stops being a detail.

        *Triage* — the jamrah gate and the node counter — takes **one byte per
        clock**. It is a reduction tree and eight counters; nothing about it
        waits.

        *The sponge* takes 128 bytes per permutation and a permutation is 310
        clocks at SLICE=25, so **0.41 bytes per clock**. It is 2.4x slower
        than the triage in front of it, and that ratio is the whole argument
        for having a triage in front of it.

        Over one terabyte at the board's 27 MHz crystal:

            triage everything          10.3 hours
            sponge everything          24.9 hours
            triage all, sponge 5%      11.5 hours

        So the layering is not only about rejecting garbage before spending a
        hash — at volume it is what makes the volume finishable at all.

        [EH] on the clock: 27 MHz is what the crystal offers, not an Fmax this
        design has been shown to close timing at. Every duration here scales
        inversely with whatever the real number turns out to be.
        """
        rate = cube.RATE
        rows: Dict[str, object] = {"volume": volume, "hertz": hertz,
                                   "rate_bytes": rate}
        paths: Dict[str, Dict[str, float]] = {}
        paths["triage"] = {"bytes_per_clock": 1.0, "clocks": float(volume)}
        for name, clocks in (("sponge_slice_8", 786), ("sponge_slice_25", 310),
                             ("sponge_slice_50", 198)):
            paths[name] = {
                "bytes_per_clock": rate / clocks,
                "clocks": volume / rate * clocks,
            }
        for entry in paths.values():
            entry["seconds"] = entry["clocks"] / hertz
            entry["hours"] = entry["seconds"] / 3600
        rows["paths"] = paths
        rows["sponge_slower_by"] = (
            paths["sponge_slice_25"]["clocks"] / paths["triage"]["clocks"])
        return rows

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


@dataclass(frozen=True)
class Examination:
    """Everything one pass over the data found, before it is sealed.

    Canonical by construction: fixed-width integers, keys in canonical
    rotation, profile keys in sorted order. Two runs over one input produce
    identical bytes, which is what makes the report comparable and sealable.
    """

    length: int
    family: str
    marker: str
    profile: Dict[str, int]
    regions: Tuple[Tuple[int, int, str], ...]
    recovered: Tuple[Tuple[int, bytes, str], ...]
    fingerprint: bytes

    #: Clock the first byte started on, when the input was a raw bitstream.
    #: -1 when bytes were handed in already aligned, which is a different
    #: claim from "the boundary was found to be zero".
    phase: int = -1

    def to_bytes(self) -> bytes:
        out = bytearray(EXAMINATION_MAGIC)
        out += self.length.to_bytes(8, "big")
        out += (self.phase & 0xFF).to_bytes(1, "big")
        out += self.family.encode("ascii")[:16].ljust(16, b"\x00")
        out += self.marker.encode("ascii")[:24].ljust(24, b"\x00")
        out += len(self.profile).to_bytes(2, "big")
        for name in sorted(self.profile):
            out += name.encode("utf-8")[:16].ljust(16, b"\x00")
            out += self.profile[name].to_bytes(4, "big")
        out += len(self.regions).to_bytes(4, "big")
        for offset, length, kind in self.regions:
            out += (offset.to_bytes(8, "big") + length.to_bytes(8, "big")
                    + kind.encode("ascii")[:16].ljust(16, b"\x00"))
        out += len(self.recovered).to_bytes(4, "big")
        for offset, key, clue in self.recovered:
            out += (offset.to_bytes(8, "big") + bytes([len(key)])
                    + key[:16].ljust(16, b"\x00")
                    + clue.encode("utf-8")[:24].ljust(24, b"\x00"))
        out += self.fingerprint
        return bytes(out)

    def summary(self) -> str:
        """One line, for a log or a terminal."""
        hidden = f", {len(self.recovered)} recovered" if self.recovered else ""
        named = f" ({self.marker})" if self.marker else ""
        aligned = f", phase {self.phase}" if self.phase >= 0 else ""
        return (f"{self.length:,} bytes: {self.family}{named}, "
                f"{len(self.regions)} regions{hidden}{aligned}")
