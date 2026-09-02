"""
Per-clock stream triage, and the four measurements that bound what it can claim.

The proposal was a malware extractor in the LUT fabric: parse the stream bit by
bit and pull trojans out of it. The architecture is right and half the claim is
true — counting bit by bit really does break the obfuscation most malware
actually uses. The other half is refuted by the same counters, and these tests
assert the refutations, because a detector nobody tried to break is the one
that looks perfect.
"""

from __future__ import annotations

import base64
import gzip
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from hijaiyyah.crypto.guarded_record import CryptoRefusal as CryptoRefusalType
from hijaiyyah.crypto.guarded_record import GuardedRecord as GuardedRecordType
from hijaiyyah.crypto.node_counter import (
    EMPTY,
    HIGH_ENTROPY,
    MODEL_MASK,
    TEXT,
    WINDOW,
    bit_counts,
    classify_window,
    profile,
    recover_repeating_key,
    recover_xor_key,
    scan,
    sweep_period,
)

ROOT = Path(__file__).resolve().parents[2]
TEXT_SAMPLE = (ROOT / "src" / "hijaiyyah" / "crypto" / "cube.py").read_bytes()


# ══════════════════════════════════════════════════════════════════
#  Counting bit by bit recovers a key that popcount cannot
# ══════════════════════════════════════════════════════════════════

def test_a_single_byte_xor_key_falls_out_of_eight_counters() -> None:
    """
    XOR acts on bit positions independently, so a position's bias keeps its
    magnitude and flips its sign. Eight comparisons and one XOR, no search.
    """
    rng = random.Random(4)
    hits = 0
    for _ in range(200):
        start = rng.randrange(0, len(TEXT_SAMPLE) - 1024)
        key = rng.randrange(256)
        window = bytes(b ^ key for b in TEXT_SAMPLE[start : start + 1024])
        hits += recover_xor_key(window) == key
    assert hits / 200 >= 0.90, f"only {hits}/200 keys recovered"


def test_popcount_alone_cannot_do_it() -> None:
    """
    Why the counters are per position. Summing across positions is exactly the
    step that destroys the key: two different keys can give the same popcount,
    so no function of popcount alone can separate them.
    """
    window = TEXT_SAMPLE[:WINDOW]
    by_popcount = {}
    for key in range(256):
        encrypted = bytes(b ^ key for b in window)
        by_popcount.setdefault(sum(bin(b).count("1") for b in encrypted), []).append(key)
    collisions = [keys for keys in by_popcount.values() if len(keys) > 1]
    assert collisions, "popcount would have to be injective in the key, and it is not"


def test_the_recovery_is_a_constant_mask_over_the_counters() -> None:
    """The whole model is one byte, so the hardware is eight comparators."""
    window = bytes(b ^ 0x5A for b in TEXT_SAMPLE[:1024])
    raw = sum((2 * c > len(window)) << i for i, c in enumerate(bit_counts(window)))
    assert recover_xor_key(window) == raw ^ MODEL_MASK == 0x5A


def test_a_repeating_key_needs_the_period_found_first() -> None:
    rng = random.Random(9)
    for period in (1, 5, 7, 13):
        key = bytes(rng.randrange(256) for _ in range(period))
        payload = TEXT_SAMPLE * (4096 // len(TEXT_SAMPLE) + 2)
        cipher = bytes(b ^ key[i % period] for i, b in enumerate(payload[:4096]))
        assert sweep_period(cipher) == period
        assert recover_repeating_key(cipher) == key


def test_the_sweep_takes_the_smallest_period_not_the_strongest() -> None:
    """
    Taking the argmax picked a multiple of the true period every time: a
    period-5 key is also a valid period-10 key, and shorter subsamples carry
    more sampling noise, so the raw score climbs with period for two reasons
    that have nothing to do with the key. Period 13 scored 100% and period 1
    scored 0% — the metric, not the cipher.
    """
    payload = (TEXT_SAMPLE * 4)[:4096]
    cipher = bytes(b ^ 0x3C for b in payload)
    assert sweep_period(cipher) == 1


# ══════════════════════════════════════════════════════════════════
#  What the same counters prove they cannot do
# ══════════════════════════════════════════════════════════════════

def test_real_encryption_leaves_nothing_to_count() -> None:
    """
    The bound on the whole idea. Every bit position of good ciphertext sits at
    balance, so there is no sign to read and the recovery returns noise —
    measured at 0% against 0.4% for blind guessing.
    """
    rng = random.Random(13)
    hits = 0
    for _ in range(200):
        key = rng.randrange(256)
        hits += recover_xor_key(bytes(b ^ key for b in os.urandom(1024))) == key

    # The bound is arithmetic, not taste. Each trial recovers the key by
    # accident with p = 1/256, so 200 trials expect 0.78 hits. A bound of 4
    # fails once in 786 runs — small, but this suite runs often enough that
    # "small" becomes "sometimes", and a test that fails for the reason it is
    # testing against is worse than no test. At 8 the false-failure rate is
    # about 1e-7, and real structure would put hits far above it: recovery
    # against text lands at 95%, which is 190.
    assert hits <= 8, f"{hits}/200 — that would mean structure in urandom"


def test_compressed_and_encrypted_are_the_same_object_here() -> None:
    """
    So 'detects malware' is not a statement this can make: a zip file and a
    packed payload are indistinguishable to it. It detects high entropy, and
    high entropy is not malice.
    """
    compressed = gzip.compress(TEXT_SAMPLE * 6)
    random_bytes = os.urandom(len(compressed))
    for data in (compressed, random_bytes):
        assert profile(data)["ENTROPI-TINGGI"] > 0.60


def test_base64_defeats_the_classifier_completely() -> None:
    """
    One line of encoding, and every window reads as text. Not usually — all of
    it. Any adversary who cares evades this, which is why it is triage.
    """
    encoded = base64.b64encode(os.urandom(40000))
    assert profile(encoded)["TEKS"] > 0.98


# ══════════════════════════════════════════════════════════════════
#  The classifier itself
# ══════════════════════════════════════════════════════════════════

def test_the_classes_separate_the_corpora_they_were_measured_on() -> None:
    assert classify_window(bytes(WINDOW)) == EMPTY
    assert classify_window(TEXT_SAMPLE[:WINDOW]) == TEXT
    assert classify_window(os.urandom(WINDOW)) in (HIGH_ENTROPY, 2)


def test_a_partial_trailing_window_is_dropped_not_padded() -> None:
    """Padding it with zeros would report EMPTY for a fragment that is not."""
    assert len(scan(b"\xff" * (WINDOW * 3 + 7))) == 3


# ══════════════════════════════════════════════════════════════════
#  Verilog agrees, byte for byte
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_verilog_agrees_on_class_and_key() -> None:
    """
    Seventy-two real corpus windows through both implementations.

    The first run showed fourteen mismatches that looked exactly like a design
    fault — windows of zeros scoring 6, 5 and 3 bits set. It was the harness:
    stimulus driven immediately before the posedge races the DUT's sample, and
    the module read the next byte. The testbench drives on the negedge now.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", "/tmp/tb_node_counter",
         "rtl/hijaiyyah_node_counter.v", "rtl/tb/tb_hijaiyyah_node_counter.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_node_counter"], cwd=ROOT,
                         capture_output=True, text=True)
    assert "PASS: 72/72" in run.stdout, run.stdout


# ══════════════════════════════════════════════════════════════════
#  CMASS — the clock period is the unit, and the boundary is found
# ══════════════════════════════════════════════════════════════════

def test_the_byte_boundary_is_recovered_from_a_raw_bitstream() -> None:
    """
    Everything above this point assumed a byte boundary. On a wire there is
    none: bits arrive one per clock and where a byte starts has to be
    discovered. Measured at 100% for every period tested.
    """
    from hijaiyyah.crypto.node_counter import bitstream, find_byte_boundary

    rng = random.Random(21)
    payload = (TEXT_SAMPLE * 4)[:4096]
    for period in (1, 3, 5, 7):
        key = bytes(rng.randrange(256) for _ in range(period))
        cipher = bytes(b ^ key[i % period] for i, b in enumerate(payload))
        for shift in range(8):
            bits = bitstream(cipher, shift)
            assert find_byte_boundary(bits, period) == (8 - shift) % 8


def test_a_marginal_statistic_cannot_find_a_boundary_and_this_is_why() -> None:
    """
    The attempt that failed, kept because it explains the one that works.

    Scoring phases by per-bit-position bias gave 2-5% against a 12.5% chance
    level, and argmax and argmin both scored 0% — the scores were equal to
    three decimals across all eight phases. Regrouping the same bits into
    different bytes leaves every bit where it was; only the partition moves,
    and per-position counts do not depend on the partition. A boundary needs a
    statistic that is joint over the byte.
    """
    from hijaiyyah.crypto.node_counter import assemble, bit_counts, bitstream

    bits = bitstream((TEXT_SAMPLE * 2)[:2048], 3)
    totals = {
        phase: sorted(bit_counts(assemble(bits, phase))) for phase in range(8)
    }
    spread = max(sum(v) for v in totals.values()) - min(sum(v) for v in totals.values())
    assert spread <= 8, "per-position counts barely move with phase, as claimed"


def test_coincidence_survives_the_key_it_is_used_to_break() -> None:
    """XOR permutes the histogram, and permuting bins leaves the sum alone."""
    from hijaiyyah.crypto.node_counter import coincidence

    plain = TEXT_SAMPLE[:2048]
    for key in (0x00, 0x5A, 0xFF):
        assert abs(coincidence(bytes(b ^ key for b in plain))
                   - coincidence(plain)) < 1e-12


def test_alignment_recovers_the_key_up_to_a_rotation() -> None:
    """
    Inherent, not a defect: with no absolute start position the residue
    classes can only be identified up to a cyclic shift of the key.
    """
    from hijaiyyah.crypto.node_counter import align, bitstream

    key = b"\x9c\x41\x07\x22\xd5"
    payload = (TEXT_SAMPLE * 4)[:4096]
    cipher = bytes(b ^ key[i % 5] for i, b in enumerate(payload))
    phase, period, data = align(bitstream(cipher, 3))

    assert (phase, period) == (5, 5)
    found = recover_repeating_key(data)
    rotations = {key[i:] + key[:i] for i in range(5)}
    assert found in rotations, f"{found.hex()} is not a rotation of {key.hex()}"


def test_no_boundary_stands_out_in_encrypted_data() -> None:
    """The negative control for the inversion, matching every other stage."""
    from hijaiyyah.crypto.node_counter import assemble, bitstream, coincidence

    bits = bitstream(os.urandom(4096), 3)
    scores = [coincidence(assemble(bits, phase)) for phase in range(8)]
    assert max(scores) / max(min(scores), 1e-9) < 1.15


# ══════════════════════════════════════════════════════════════════
#  The wave: CMASS, the counter and Ka'bah as one pipeline
# ══════════════════════════════════════════════════════════════════

def test_the_wave_runs_from_bits_to_an_authenticated_report() -> None:
    """
    Bits on a wire with no alignment given, an authenticated report out.
    Nothing new is computed by the composition; what it adds is that the
    findings survive the trip to whoever acts on them.
    """
    from hijaiyyah.crypto.node_counter import bitstream
    from hijaiyyah.crypto.wave import Wave

    key = b"\x9c\x41\x07\x22\xd5"
    payload = (TEXT_SAMPLE * 8)[:8192]
    cipher = bytes(b ^ key[i % 5] for i, b in enumerate(payload))

    wave = Wave(bytes(range(32)), "triage")
    report = wave.open(wave.run(bitstream(cipher, 3)))
    assert (report.phase, report.period) == (5, 5)
    assert sum(report.summary().values()) == len(report.classes) > 0


def test_a_rewritten_verdict_is_refused() -> None:
    """
    The reason the two systems are one system. A classifier's output is worth
    nothing if an attacker can rewrite it downstream, so the report carries
    layer 3's MAC and a flipped verdict does not open.
    """
    from hijaiyyah.crypto.wave import Wave

    wave = Wave(bytes(range(32)), "triage")
    record = wave.seal(Wave.survey_bytes((TEXT_SAMPLE * 4)[:4096]))

    # Both refusal paths, because the layering has two and they split roughly
    # 41/59 over single-bit flips. Asserting only the MAC would have been
    # wrong: this flip pushes a letter index out of 1..28, so layer 1 rejects
    # it in O(1) before a hash is ever computed. That is the design, not a
    # near miss, and the first version of this test expected the wrong one.
    body = bytearray(record.to_bytes())
    body[-40] ^= 0x01
    with pytest.raises(CryptoRefusalType, match="structure rejected"):
        wave.open(GuardedRecordType.from_bytes(bytes(body)))

    # Tampering the tag itself is always structurally valid, so it reaches
    # layer 3 and the MAC is what refuses.
    tag = bytearray(record.to_bytes())
    tag[-1] ^= 0x01
    with pytest.raises(CryptoRefusalType, match="authentication failed"):
        wave.open(GuardedRecordType.from_bytes(bytes(tag)))


def test_the_report_is_canonical_and_round_trips() -> None:
    """Layer 0's property, inherited rather than reinvented: fixed-width
    integers throughout, so two parties cannot read one report differently."""
    from hijaiyyah.crypto.wave import Wave, WaveReport

    report = Wave.survey_bytes((TEXT_SAMPLE * 4)[:4096])
    assert WaveReport.from_bytes(report.to_bytes()) == report
    with pytest.raises(CryptoRefusalType, match="does not match"):
        WaveReport.from_bytes(report.to_bytes() + b"\x00")


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_line_rate_stages_agree_with_the_python() -> None:
    """
    39,997 bits offered one per clock, no boundary given, against the same
    stream in Python. Both sabotages were induced first: shifting the phase by
    one clock and removing the alignment entirely each produce 106 mismatches.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", "-s", "tb_hijaiyyah_wave", "-o", "/tmp/tb_wave",
         "rtl/hijaiyyah_wave.v", "rtl/hijaiyyah_deserialiser.v",
         "rtl/hijaiyyah_node_counter.v", "rtl/tb/tb_hijaiyyah_wave.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_wave"], cwd=ROOT, capture_output=True, text=True)
    assert "PASS: 78/78" in run.stdout, run.stdout


def test_the_rtl_says_what_it_does_not_contain() -> None:
    """
    A pipeline diagram that overstates its own extent is the most convincing
    wrong thing a design can carry. Phase discovery needs a 256-bin histogram
    and runs once per stream; layer 3 needs a SHA-256 core that does not exist
    in this repository. The header has to keep saying both.
    """
    source = (ROOT / "rtl" / "hijaiyyah_wave.v").read_text(encoding="utf-8")
    assert "NOT here" in source
    assert "no SHA-256 core" in source
    assert "does not authenticate" in source


# ══════════════════════════════════════════════════════════════════
#  Jamrah: seven throws, one gate
# ══════════════════════════════════════════════════════════════════

def test_a_byte_reduces_through_exactly_seven_nodes() -> None:
    """
    Jamrat al-Aqabah is seven pebbles at one pillar, and the byte has the same
    shape for the same reason: an 8-leaf binary reduction tree has exactly
    4 + 2 + 1 = 7 internal nodes and one root. Not a metaphor over the
    arithmetic — the arithmetic.
    """
    levels = []
    width = 8
    while width > 1:
        width //= 2
        levels.append(width)
    assert levels == [4, 2, 1]
    assert sum(levels) == 7


def test_the_taps_carry_what_the_root_throws_away() -> None:
    """
    Why tap all seven rather than read the root. The root is the popcount, and
    popcount is exactly the statistic that cannot recover an XOR key, because
    summing across bit positions destroys where the key lives. Two bytes can
    share a root and differ at every node below it.
    """
    def nodes(byte: int):
        n0 = (byte & 1) + ((byte >> 1) & 1)
        n1 = ((byte >> 2) & 1) + ((byte >> 3) & 1)
        n2 = ((byte >> 4) & 1) + ((byte >> 5) & 1)
        n3 = ((byte >> 6) & 1) + ((byte >> 7) & 1)
        return (n0, n1, n2, n3, n0 + n1, n2 + n3, n0 + n1 + n2 + n3)

    for byte in range(256):
        assert nodes(byte)[6] == bin(byte).count("1")

    same_root = [b for b in range(256) if bin(b).count("1") == 4]
    assert len({nodes(b)[:4] for b in same_root}) > 1, (
        "the taps would carry nothing the root does not"
    )


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_jamrah_gate_agrees_on_all_256_bytes() -> None:
    """
    Every node checked, not only the root — a popcount would still look right
    with the tree's internals wrong. Both sabotages induced first: truncating
    node4 gives 192 mismatches, widening the alphabet to 29 gives one.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", "/tmp/tb_jamrah",
         "rtl/hijaiyyah_jamrah_gate.v", "rtl/tb/tb_hijaiyyah_jamrah_gate.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_jamrah"], cwd=ROOT, capture_output=True, text=True)
    assert "PASS: 256/256" in run.stdout, run.stdout


def test_the_gate_is_triage_and_says_so() -> None:
    """
    It has no key, so anyone can build a byte that passes. hcpu_guard.v is the
    geometric check on a full codex vector; this is the cheap gate in front of
    it. Reading it as authority is the one misreading that would matter.
    """
    raw = (ROOT / "rtl" / "hijaiyyah_jamrah_gate.v").read_text(encoding="utf-8")
    source = " ".join(raw.replace("//", " ").split())
    assert "triage and not authority" in source
    assert "no key" in source
