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
    assert hits <= 4, f"{hits}/200 — that would mean structure in urandom"


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
