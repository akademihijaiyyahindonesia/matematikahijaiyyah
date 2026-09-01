"""
The web app must compute what the Python implementation computes.

apps/hijaiyyah-seal.html carries its own copy of the Master Table, the guard
formulas and the HKDF/HMAC construction, because a browser cannot import
Python. That is the same shape as hom-gui's JS engine, and the same shape as
every divergence this project has had: one truth in two places.

So the app embeds a known-answer vector produced by
crypto/guarded_record.py and checks itself against it on load. This test
checks the vector is still the right answer, so the app's self-test cannot
pass against a stale constant.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hijaiyyah.core.guards import compute_U
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.crypto.guarded_record import (
    dataset_seal,
    derive_key,
    encode_bytes,
    seal_record,
)

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "hijaiyyah-seal.html"
SOURCE = APP.read_text(encoding="utf-8")


def _kat() -> dict:
    block = SOURCE.split("const KAT = {", 1)[1].split("};", 1)[0]
    out = {}
    for key in ("master", "purpose", "key", "payload", "nonce", "mac"):
        out[key] = re.search(rf'{key}:\s*"([^"]*)"', block).group(1)
    out["letters"] = json.loads(re.search(r"letters:\s*(\[[^\]]*\])", block).group(1))
    return out


def test_the_app_exists_and_carries_a_vector() -> None:
    assert APP.exists()
    assert _kat()["mac"], "no known-answer vector in the app"


def test_the_known_answer_vector_is_still_the_right_answer() -> None:
    """
    Recompute the whole vector in Python. If the sealed table, the encoding or
    the derivation changed, this fails and the app's self-test would otherwise
    have gone on passing against a constant that no longer describes anything.
    """
    kat = _kat()
    master = bytes.fromhex(kat["master"])
    key = derive_key(master, kat["purpose"])
    record = seal_record(
        kat["payload"].encode("ascii"), key, nonce=bytes.fromhex(kat["nonce"])
    )

    assert key.hex() == kat["key"], "derived key drifted"
    assert list(record.letters) == kat["letters"], "encoding drifted"
    assert record.mac.hex() == kat["mac"], "MAC drifted"


def test_the_app_carries_the_current_dataset_seal() -> None:
    seal = re.search(r'const SEAL\s*=\s*"([0-9a-f]{64})"', SOURCE).group(1)
    assert seal == dataset_seal(), (
        "the app is bound to a different sealed release than this build"
    )


def test_the_app_table_matches_the_sealed_table() -> None:
    """All 28 letters, component for component."""
    rows = re.findall(r'\["([^"]+)","([^"]+)",(\[[0-9,]+\])\]', SOURCE)
    assert len(rows) == 28, f"the app carries {len(rows)} letters"

    for (char, _name, vector), entry in zip(rows, MASTER_TABLE.all_entries(), strict=True):
        assert char == entry.char
        assert json.loads(vector) == list(entry.vector), f"{char} differs"


def test_the_app_uses_the_same_turning_budget() -> None:
    """U = Qx + Qs + Qa + 4·Qc, in the app's own notation."""
    formula = re.search(r"const U = v =>([^;]+);", SOURCE).group(1)
    assert "v[10]" in formula and "v[11]" in formula
    assert "v[12]" in formula and "4*v[13]" in formula.replace(" ", "")


def test_the_app_carries_the_decomposition_identity() -> None:
    """
    §IC.1.24 as an equality is what closes the Θ̂ gap G4's inequality leaves.
    Without it the app would report a weaker check than the library does.
    """
    assert "U(v) + rho" in SOURCE
    assert "IC.1.24" in SOURCE


@pytest.mark.parametrize(
    "entry", MASTER_TABLE.all_entries(), ids=[e.char for e in MASTER_TABLE.all_entries()]
)
def test_the_identity_catches_a_theta_flip_on_every_letter(entry) -> None:
    """
    The property the app demonstrates when a letter is tapped. Checked here in
    Python so the demonstration cannot be a UI illusion.
    """
    v = list(entry.vector)
    rho = v[0] - compute_U(v)
    corrupted = list(v)
    corrupted[0] ^= 1
    assert corrupted[0] != compute_U(corrupted) + rho


def test_the_app_carries_a_nonce() -> None:
    """
    Without one the app would seal a payload to the same bytes every time, and
    a captured record would replay forever. The library gained a nonce; the
    page has to carry the same construction or the two disagree.
    """
    assert "NONCE_LEN = 16" in SOURCE
    assert "getRandomValues(new Uint8Array(NONCE_LEN))" in SOURCE


def test_the_app_length_prefixes_the_tag_input() -> None:
    """
    Concatenating variable-length fields without lengths lets two different
    records produce one tag input.
    """
    assert "be(seal.length, 2)" in SOURCE
    assert "be(nonce.length, 2)" in SOURCE
    assert "be(letters.length, 4)" in SOURCE


def test_the_app_refuses_to_encrypt() -> None:
    """
    The refusal has to survive into the app, or the page would imply a
    capability the library deliberately does not provide.
    """
    assert "tidak lakukan: enkripsi" in SOURCE
    assert "AES-256-GCM" in SOURCE


def test_the_app_says_the_guard_is_not_authentication() -> None:
    assert "Guard bukan otentikasi" in SOURCE
    assert "tanpa kunci" in SOURCE


def test_encoding_agrees_with_the_library() -> None:
    """The app's base-28 rule, exercised through the library it must match."""
    assert encode_bytes(b"HYBIT") == tuple(_kat()["letters"])
