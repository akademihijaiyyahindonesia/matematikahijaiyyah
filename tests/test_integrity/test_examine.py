"""
One pass over the data, one sealed report — the four front doors made one.

Before this the system had four entry points: the wave, the memory scanner,
the elemental profile, and the record layers. A caller had to know which to
open and in what order, which is four chances to use it wrongly and no single
answer at the end.
"""

from __future__ import annotations

import random

import pytest

from hijaiyyah.crypto.guarded_record import CryptoRefusal, GuardedRecord
from hijaiyyah.crypto.kabah import Examination, Kabah
from hijaiyyah.crypto.node_counter import bitstream

MASTER = bytes(range(32))
KEY = b"\x9c\x41\x07\x22\xd5"


def _dump(seed: int = 20260902) -> bytes:
    """Text, padding, packed filler, and one XOR-staged PE.

    The filler is seeded rather than drawn from urandom, deliberately. Phase
    recovery measures 159 of 160 across all eight shifts and twenty random
    dumps each — 99.4%, not 100% — so an unseeded fixture makes this suite
    flake about once in a hundred and sixty runs. A flaky test is worse than
    an honest one: the number belongs in the docstring, and the fixture
    belongs pinned.
    """
    pe = bytearray(b"MZ" + b"\x90" * 0x3A)
    pe += (0x40).to_bytes(4, "little") + b"PE\x00\x00" + b"\x64\x86"
    pe += b"This program cannot be run in DOS mode.\r\n" * 40
    pe += b"kernel32.dll\x00VirtualAlloc\x00LoadLibraryA\x00" * 20

    rng = random.Random(seed)
    data = bytearray(b"C:\\Windows\\System32\\ntdll.dll\x00" * 200)
    data += bytes(4096) + bytes(rng.randrange(256) for _ in range(6144))
    data += bytes(b ^ KEY[i % 5] for i, b in enumerate(bytes(pe)))
    data += b"\x90" * 96 + b"HKEY_LOCAL_MACHINE\\Software\\Microsoft\x00" * 120
    return bytes(data)


def _system() -> Kabah:
    return Kabah(MASTER, "forensics", track_replays=False)


# ══════════════════════════════════════════════════════════════════
#  One pass, everything
# ══════════════════════════════════════════════════════════════════

def test_one_call_produces_every_stage_of_the_system() -> None:
    found = _system().examine(_dump())

    assert found.family in ("STRUCTURED", "HIGH_ENTROPY", "TEXT")
    assert sum(found.profile.values()) > 0
    assert any(kind == "XOR_STAGED" for _, _, kind in found.regions)
    assert len(found.recovered) == 1
    assert len(found.fingerprint) == 32

    _offset, key, clue = found.recovered[0]
    assert clue == "DOS/PE stub"
    assert key in {KEY[i:] + KEY[:i] for i in range(len(KEY))}


def test_the_report_is_deterministic_because_keys_are_canonical() -> None:
    """
    Rotation is what makes it stable. A repeating key is recoverable only up
    to a cyclic shift, so two runs over different window alignments return
    the same key wearing different phases. Storing the canonical rotation —
    the lexicographically smallest — makes one input always produce one report,
    which is what lets it be sealed and compared.
    """
    from hijaiyyah.crypto.memscan import canonical

    data = _dump()
    system = _system()
    first, second = system.examine(data), system.examine(data)
    assert first.to_bytes() == second.to_bytes()

    _, key, _ = first.recovered[0]
    assert key == canonical(key), "the stored key is not in canonical rotation"


def test_the_report_is_canonical_and_fixed_width() -> None:
    found = _system().examine(_dump())
    encoded = found.to_bytes()
    assert encoded.startswith(b"HEX1")
    assert len(encoded) > 64


# ══════════════════════════════════════════════════════════════════
#  Folded bit by bit, with no byte boundary given
# ══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("shift", [0, 1, 2, 3, 4, 5, 6, 7])
def test_a_raw_bitstream_recovers_its_own_boundary_at_every_shift(shift: int) -> None:
    """
    `examine` takes bytes, which presumes someone already knew where a byte
    begins; a wire carries no such thing. This takes the bits as they arrive
    and recovers the boundary from the data — the same path the silicon runs.

    Measured across all eight shifts and twenty random dumps each: **159 of
    160**. It is 99.4%, not certainty, and the fixture is seeded so this
    asserts the capability rather than sampling the failure.
    """
    data = _dump()
    found = _system().examine_stream(bitstream(data, shift))

    assert found.phase == (8 - shift) % 8
    assert len(found.recovered) == 1
    assert found.recovered[0][2] == "DOS/PE stub"


def test_bytes_handed_in_aligned_report_no_phase_at_all() -> None:
    """
    -1 rather than 0. "Nobody looked for a boundary" and "the boundary was
    found to be zero" are different claims, and a report that conflates them
    is not reproducible from what it says.
    """
    assert _system().examine(_dump()).phase == -1
    assert _system().examine_stream(bitstream(_dump(), 0)).phase == 0


# ══════════════════════════════════════════════════════════════════
#  Sealing the findings
# ══════════════════════════════════════════════════════════════════

def test_a_sealed_examination_round_trips_and_refuses_tampering() -> None:
    """
    The only layer here that stops a finding being rewritten between this
    machine and whoever acts on it.
    """
    system = _system()
    found = system.examine(_dump())
    record = system.seal_examination(found)
    assert system.open(record) == found.to_bytes()

    tampered = bytearray(record.to_bytes())
    tampered[-1] ^= 0x01
    with pytest.raises(CryptoRefusal):
        system.open(GuardedRecord.from_bytes(bytes(tampered)))


def test_two_purposes_cannot_read_each_others_examinations() -> None:
    audit = Kabah(MASTER, "audit", track_replays=False)
    intake = Kabah(MASTER, "intake", track_replays=False)
    record = audit.seal_examination(audit.examine(_dump()))
    with pytest.raises(CryptoRefusal, match="authentication failed"):
        intake.open(record)


def test_the_summary_names_what_it_found() -> None:
    found = _system().examine(_dump())
    line = found.summary()
    assert "bytes" in line and "regions" in line and "recovered" in line


def test_the_method_says_why_it_exists() -> None:
    doc = " ".join((Kabah.examine.__doc__ or "").split())
    assert "four front doors" in doc
    assert "Rotation is what makes the report stable" in doc


def test_an_empty_input_does_not_invent_findings() -> None:
    found = _system().examine(bytes(4096))
    assert found.recovered == ()
    assert isinstance(found, Examination)


# ══════════════════════════════════════════════════════════════════
#  At volume: the ratio that shapes the design
# ══════════════════════════════════════════════════════════════════

def test_the_sponge_is_the_bottleneck_and_the_arithmetic_says_by_how_much() -> None:
    """
    Triage is a reduction tree and eight counters: one byte per clock, nothing
    waits. The sponge is 128 bytes per 310-clock permutation — 0.41 bytes per
    clock, 2.4x slower.

    That ratio is the whole argument for putting triage in front. Over a
    terabyte at 27 MHz: triage everything in 10.3 hours, sponge everything in
    24.9, or triage everything and sponge the 5% it flags in 11.5. At volume
    the layering is not only about rejecting garbage before spending a hash —
    it is what makes the volume finishable.
    """
    from hijaiyyah.crypto import cube

    numbers = Kabah.throughput()
    paths = numbers["paths"]

    assert paths["triage"]["bytes_per_clock"] == 1.0
    assert abs(paths["sponge_slice_25"]["bytes_per_clock"] - cube.RATE / 310) < 1e-9
    assert 2.4 <= numbers["sponge_slower_by"] < 2.5

    assert 10.0 < paths["triage"]["hours"] < 10.6
    assert 24.5 < paths["sponge_slice_25"]["hours"] < 25.5

    # A wider slice buys clocks, not bytes: the rate is fixed by the sponge.
    assert (paths["sponge_slice_50"]["clocks"]
            < paths["sponge_slice_25"]["clocks"]
            < paths["sponge_slice_8"]["clocks"])


def test_the_throughput_figures_scale_with_the_clock_they_assume() -> None:
    """
    27 MHz is what the crystal offers, not an Fmax this design has been shown
    to close timing at. Doubling the assumed clock must halve every duration —
    if it did not, the figures would be carrying an assumption they do not
    declare.
    """
    slow = Kabah.throughput(hertz=27_000_000)["paths"]["sponge_slice_25"]
    fast = Kabah.throughput(hertz=54_000_000)["paths"]["sponge_slice_25"]
    assert abs(slow["hours"] / fast["hours"] - 2.0) < 1e-9
    assert slow["clocks"] == fast["clocks"]


def test_the_docstring_keeps_the_epistemic_label_on_the_clock() -> None:
    doc = " ".join((Kabah.throughput.__doc__ or "").split())
    assert "[EH] on the clock" in doc
    assert "not an Fmax this design has been shown to close timing at" in doc
