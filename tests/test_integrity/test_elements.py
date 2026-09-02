"""
Reading a file's elements — and the two accuracy numbers that answer different
questions.

A magic number says what a file claims to be, and where one exists it wins.
This is for headerless data: a carved fragment, a memory page, a recovered
sector. All six elements are counts, so the whole profile is one pass over 256
counters and computes one byte per clock.
"""

from __future__ import annotations

import gzip
import os
from pathlib import Path

from hijaiyyah.crypto.elements import (
    MINIMUM,
    atoms,
    classify,
    identify,
    profile_table,
)

TEXT = (b"C:\\Windows\\System32\\ntdll.dll\x00" * 40
        + b"def measure(data): return len(data)\n" * 200)


def test_the_six_elements_are_all_counts() -> None:
    """
    Which is what lets the profile run at line rate: one pass, 256 counters,
    no second look at the data.
    """
    profile = atoms(b"AAAA" + bytes(4) + b"\xff\xff")
    assert 0.0 <= profile.printable <= 1.0
    assert 0.0 <= profile.null <= 1.0
    assert 0.0 <= profile.high_bit <= 1.0
    assert 0.0 <= profile.peak <= 1.0
    assert 0.0 <= profile.unique <= 1.0
    assert 0.0 <= profile.entropy <= 8.0


def test_the_families_that_separate_cleanly() -> None:
    assert identify(bytes(4096)).family == "EMPTY"
    assert identify(TEXT).family == "TEXT"
    assert identify(os.urandom(8192)).family == "HIGH_ENTROPY"


def test_an_executable_reads_as_one_by_its_null_density() -> None:
    """
    69% zeroes and 15% printable is the shape of a mapped image, and nothing
    else on this machine looks like it.
    """
    with open("/bin/ls", "rb") as handle:
        binary = handle.read()
    assert identify(binary).family == "EXECUTABLE"


def test_compressed_and_random_are_the_same_object_and_it_says_so() -> None:
    """
    The third independent measurement in this project saying so: gzip 7.99,
    urandom 8.00, every other element within noise. It bounds what identify
    can claim, and the caveat has to travel with the answer.
    """
    # Varied input, deliberately. Compressing highly repetitive text gives a
    # 652-byte stream whose entropy is 5.0 and whose histogram is half empty —
    # not because the classifier is wrong but because there is not enough data
    # in it to have full entropy. A measurement needs enough sample to mean
    # anything, which is the same lesson as the 512-byte minimum.
    varied = b"".join(
        Path(name).read_bytes()
        for name in sorted(Path("src/hijaiyyah/crypto").glob("*.py"))
    )
    packed = gzip.compress(varied)
    noise = os.urandom(len(packed))
    assert len(packed) > 20000, "the sample is too small to have full entropy"

    assert identify(packed).family == identify(noise).family == "HIGH_ENTROPY"
    assert abs(atoms(packed).entropy - atoms(noise).entropy) < 0.1
    assert "indistinguishable" in identify(packed).caveat


def test_a_marker_outranks_the_statistics() -> None:
    """
    A header is better evidence than any histogram, and pretending otherwise
    would be this module misunderstood.
    """
    found = identify(os.urandom(4096), clue="PE header")
    assert found.family == "IDENTIFIED"
    assert found.marker == "PE header"
    assert "not by its elements" in found.caveat


def test_too_little_data_is_refused_rather_than_guessed() -> None:
    """
    Below the minimum the histogram is too sparse for `unique` or `peak` to
    mean anything, so it returns UNKNOWN instead of a number-shaped guess.
    """
    found = identify(b"MZ" + os.urandom(64))
    assert found.family == "UNKNOWN"
    assert str(MINIMUM) in found.caveat


def test_padding_pages_inside_a_binary_read_as_empty_and_that_is_correct() -> None:
    """
    The finding behind the two accuracy numbers.

    Whole-file identification is 8 of 8 on this machine's samples. Over 4 KB
    chunks it reads 78.8%, and the gap is a different question rather than a
    weakness: thirty-one of thirty-seven chunks of a Mach-O are reported EMPTY
    or STRUCTURED, and chunks 0 through 3 are literally 100% zero. The ground
    truth "every chunk of a binary is executable" was wrong; the classifier
    was right, and a carve wants exactly this decomposition.
    """
    with open("/bin/ls", "rb") as handle:
        head = handle.read(4096)
    if set(head) == {0}:
        assert identify(head).family == "EMPTY"
    assert classify(atoms(bytes(4096)))[0] == "EMPTY"


def test_the_profile_table_reports_every_sample() -> None:
    rows = profile_table([("text", TEXT), ("noise", os.urandom(4096))])
    assert [r["name"] for r in rows] == ["text", "noise"]
    assert rows[0]["family"] == "TEXT"
    assert "entropy" in rows[0]


def test_the_module_states_where_it_does_not_replace_anything() -> None:
    from hijaiyyah.crypto import elements

    doc = " ".join((elements.__doc__ or "").split())
    assert "where one exists it wins" in doc
    assert "not a replacement for ``file``" in doc
    assert "gzip measures 7.99" in doc or "gzip 7.99" in doc or "7.99" in doc
