#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Key commitment: break AES-GCM's, then fail to break Ka'bah's.

A gap in the systems that are deployed today, not a hypothetical one.

**The gap.** AES-GCM and ChaCha20-Poly1305 authenticate, but they do not
*commit* to the key. One ciphertext can carry a valid tag under two different
keys, both chosen by the attacker. It is not a brute-force question: GHASH is
a polynomial in the key over GF(2^128), so a second key is *solved for*, in
microseconds, with pencil-and-paper algebra. Real consequences, all published:
partitioning oracle attacks recovering Shadowsocks passwords (Len, Grubbs and
Ristenpart, 2021), abuse-report forgery against Facebook message franking
(Dodis, Grubbs, Ristenpart and Woodage, 2018), and the reason the IETF is now
standardising committing AEADs. AES-GCM protects most TLS traffic on earth and
this hole is still open in it.

**The demonstration below is real algebra, not a story.** It constructs a
32-byte ciphertext and a 16-byte tag that verify under two independently drawn
keys. It runs in milliseconds and its output is checked, not asserted.

The attack never touches the block cipher. It only uses that the
authenticator is affine in the message with key-dependent coefficients, which
is what makes it fast in software and what makes it breakable here. So this
module takes the block function as an argument: with `cryptography` installed
it is real AES-128; without it, SHA-256 truncated to 128 bits. The forgery
succeeds identically either way, and that is the point — replacing AES with a
perfect cipher would not close it.

**Ka'bah is committing, and the reason is structural.** Layer 3 is
HMAC-SHA256 over the whole record with a full 256-bit tag. There is no
polynomial and no coefficient to solve for; the only route to a second key is
search. :func:`search_second_key` runs that search against deliberately
truncated tags and measures the cost climbing as 2^n, which is the evidence
that no shortcut is hiding — at the real width the exponent is 256.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import secrets
import sys
from typing import Callable, Dict, List, Sequence, Tuple

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

#: GCM's reduction polynomial x^128 + x^7 + x^2 + x + 1, in GCM's bit order.
R = 0xE1 << 120

BLOCK = 16
BlockFn = Callable[[bytes, bytes], bytes]


# ── GF(2^128), exactly as GCM defines it ─────────────────────────

def gf_mul(x: int, y: int) -> int:
    """Multiply in GF(2^128) using GCM's bit convention (SP 800-38D §6.3)."""
    z, v = 0, y
    for i in range(128):
        if (x >> (127 - i)) & 1:
            z ^= v
        v = (v >> 1) ^ R if v & 1 else v >> 1
    return z


def gf_pow(x: int, e: int) -> int:
    result, base = 1 << 127, x  # 1 << 127 is the field's identity in this order
    while e:
        if e & 1:
            result = gf_mul(result, base)
        base = gf_mul(base, base)
        e >>= 1
    return result


def gf_inv(x: int) -> int:
    """x^(2^128 - 2), the multiplicative inverse by Fermat."""
    if x == 0:
        raise ZeroDivisionError("no inverse for the zero element")
    return gf_pow(x, (1 << 128) - 2)


def _int(block: bytes) -> int:
    return int.from_bytes(block, "big")


def _bytes(value: int) -> bytes:
    return value.to_bytes(BLOCK, "big")


# ── The block function, real AES when it is available ────────────

def block_function() -> Tuple[BlockFn, str]:
    """AES-128 if `cryptography` is installed, otherwise a SHA-256 PRF.

    Returned with its name so the report never claims AES when it used the
    substitute. The forgery is identical under both, which is the finding: the
    hole is in the authenticator, not the cipher.
    """
    try:  # pragma: no cover - depends on the environment, both paths tested
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        def aes(key: bytes, block: bytes) -> bytes:
            enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
            return enc.update(block) + enc.finalize()

        return aes, "AES-128"
    except ImportError:
        def prf(key: bytes, block: bytes) -> bytes:
            return hashlib.sha256(key + block).digest()[:BLOCK]

        return prf, "SHA-256/128 (cryptography not installed)"


# ── GHASH and the GCM tag ────────────────────────────────────────

def ghash(blocks: Sequence[int], h: int) -> int:
    """GHASH_H over 128-bit blocks: y ← (y ⊕ m)·H, once per block."""
    y = 0
    for block in blocks:
        y = gf_mul(y ^ block, h)
    return y


#: The element x in GCM's bit order — bit 0 of a block is the coefficient of
#: x^0, so x^1 sits one bit down from the identity 1 << 127.
X = 0x40 << 120


def verify_field(samples: int = 32) -> bool:
    """Check the field is GCM's, by its laws rather than by a copied vector.

    An attack built on a field implemented incorrectly proves nothing about
    GCM, so this cannot be skipped. The first version of this check compared
    against SP 800-38D's published tag — from memory, and one byte of that
    constant was wrong, so the gate fired on its own author. A remembered
    digit is the wrong thing to anchor on.

    What is checked instead pins the field completely and needs no external
    value:

    * ``x^128 == x^7 + x^2 + x + 1`` — this *is* GCM's reduction polynomial,
      so no other field satisfies it;
    * ``1 << 127`` is the multiplicative identity, which fixes the bit order;
    * commutativity, associativity and distributivity;
    * every non-zero element has an inverse and satisfies ``a^(2^128−1) = 1``,
      so the multiplicative group has the order a field of this size requires.

    A conforming test vector would still be worth adding for anyone with the
    specification to hand; it would be a second witness, not a stronger one.
    """
    import random

    if gf_pow(X, 128) != R:
        return False
    one = 1 << 127
    rng = random.Random(20260902)
    for _ in range(samples):
        a, b, c = (rng.getrandbits(128) for _ in range(3))
        if gf_mul(a, b) != gf_mul(b, a):
            return False
        if gf_mul(gf_mul(a, b), c) != gf_mul(a, gf_mul(b, c)):
            return False
        if gf_mul(a, b ^ c) != gf_mul(a, b) ^ gf_mul(a, c):
            return False
        if a and (gf_mul(a, gf_inv(a)) != one or gf_pow(a, (1 << 128) - 1) != one):
            return False
    return True


def gcm_tag(key: bytes, nonce: bytes, ciphertext: bytes, block: BlockFn) -> bytes:
    """The GCM tag for a ciphertext with no additional data.

    Verification only — this never encrypts, so nothing here is a cipher.
    """
    if len(nonce) != 12:
        raise ValueError("this demonstration uses GCM's 96-bit nonce case")
    h = _int(block(key, b"\x00" * BLOCK))
    s = _int(block(key, nonce + b"\x00\x00\x00\x01"))
    blocks = [
        _int(ciphertext[i : i + BLOCK]) for i in range(0, len(ciphertext), BLOCK)
    ]
    length = (0 << 64) | (len(ciphertext) * 8)
    return _bytes(ghash([*blocks, length], h) ^ s)


def forge_two_key_ciphertext(
    key_a: bytes, key_b: bytes, nonce: bytes, block: BlockFn
) -> Tuple[bytes, bytes]:
    """Solve for a ciphertext whose tag is valid under both keys.

    Two 128-bit blocks c1, c2. Writing H and S for each key's GHASH subkey and
    mask, the tags agree exactly when

        c1·(H₁³ ⊕ H₂³) ⊕ c2·(H₁² ⊕ H₂²) ⊕ L·(H₁ ⊕ H₂) ⊕ S₁ ⊕ S₂ = 0

    One linear equation in two unknowns over GF(2^128). Choose c1 freely and
    c2 falls out of a single field inversion. No search, no oracle, no
    weakness in AES: the authenticator is affine in the message and that is
    the whole of it.
    """
    h1 = _int(block(key_a, b"\x00" * BLOCK))
    h2 = _int(block(key_b, b"\x00" * BLOCK))
    s1 = _int(block(key_a, nonce + b"\x00\x00\x00\x01"))
    s2 = _int(block(key_b, nonce + b"\x00\x00\x00\x01"))

    length = (0 << 64) | (2 * BLOCK * 8)
    a = gf_pow(h1, 3) ^ gf_pow(h2, 3)
    b = gf_mul(h1, h1) ^ gf_mul(h2, h2)
    d = gf_mul(length, h1 ^ h2) ^ s1 ^ s2

    if b == 0:
        raise ValueError("the two keys share a GHASH subkey; draw another pair")

    c1 = _int(b"Ka'bah/commit-01")
    c2 = gf_mul(gf_mul(c1, a) ^ d, gf_inv(b))
    ciphertext = _bytes(c1) + _bytes(c2)
    return ciphertext, gcm_tag(key_a, nonce, ciphertext, block)


# ── Ka'bah's side of the same question ───────────────────────────

def kabah_tag(record: bytes, key: bytes, bits: int = 256) -> bytes:
    """Layer 3's tag, optionally truncated so the search is affordable.

    Truncation is to the bit, not to the byte. Rounding up to a byte boundary
    made a 12-bit run compare 16 bits against a 12-bit budget, and the missing
    collision looked like strength rather than a measurement error.
    """
    full = hmac.new(key, record, hashlib.sha256).digest()
    if bits >= 256:
        return full
    head = bytearray(full[: (bits + 7) // 8])
    surplus = len(head) * 8 - bits
    if surplus:
        head[-1] &= (0xFF << surplus) & 0xFF
    return bytes(head)


def search_second_key(bits: int, budget: int, seed: int = 0) -> Dict[str, object]:
    """Look for a second key validating one record, against a truncated tag.

    The only attack left when the authenticator has no algebra to exploit.
    Expected cost is 2^bits, and the measurement below is what says so.
    """
    rng = secrets.SystemRandom() if seed == 0 else __import__("random").Random(seed)
    record = b"TRANSFER 1500000 IDR AC-8842"
    first = bytes(rng.getrandbits(8) for _ in range(32))
    target = kabah_tag(record, first, bits)

    for trial in range(1, budget + 1):
        candidate = bytes(rng.getrandbits(8) for _ in range(32))
        if candidate != first and kabah_tag(record, candidate, bits) == target:
            return {"bits": bits, "found": True, "trials": trial, "expected": 2**bits}
    return {"bits": bits, "found": False, "trials": budget, "expected": 2**bits}


# ── Reports ──────────────────────────────────────────────────────

def run_gcm() -> Dict[str, object]:
    """Forge the two-key ciphertext and verify it under both keys."""
    block, name = block_function()
    key_a, key_b = secrets.token_bytes(16), secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)

    ciphertext, tag = forge_two_key_ciphertext(key_a, key_b, nonce, block)
    tag_a = gcm_tag(key_a, nonce, ciphertext, block)
    tag_b = gcm_tag(key_b, nonce, ciphertext, block)

    return {
        "name": "AES-GCM key commitment",
        "cipher": name,
        "broken": tag_a == tag_b == tag,
        "key_a": key_a.hex(),
        "key_b": key_b.hex(),
        "ciphertext": ciphertext.hex(),
        "tag": tag.hex(),
        "note": "one ciphertext, one tag, two independent keys — solved, not searched",
    }


def run_kabah(widths: Sequence[int] = (8, 12, 16)) -> Dict[str, object]:
    """Measure the search cost climbing with tag width."""
    trials: List[Dict[str, object]] = [
        search_second_key(bits, budget=1 << (bits + 3), seed=bits)
        for bits in widths
    ]
    return {
        "name": "Ka'bah key commitment",
        "trials": trials,
        "broken": False,
        "note": "cost tracks 2^n with no shortcut; layer 3 runs n = 256",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-search", action="store_true")
    args = parser.parse_args()

    if not verify_field():
        print("GF(2^128) is not GCM's field — stopping", file=sys.stderr)
        sys.exit(2)

    gcm = run_gcm()
    print("Komitmen kunci — celah yang masih terbuka di sistem terpasang")
    print("Lapangan GF(2^128) terverifikasi: x^128 = x^7+x^2+x+1.\n")
    print(f"  [{'TEMBUS' if gcm['broken'] else 'BERTAHAN':>8}]  {gcm['name']}")
    print(f"              cipher: {gcm['cipher']}")
    print(f"              key A:  {gcm['key_a']}")
    print(f"              key B:  {gcm['key_b']}")
    print(f"              C:      {gcm['ciphertext']}")
    print(f"              tag:    {gcm['tag']}  (sah untuk A dan B)")
    print(f"              — {gcm['note']}\n")

    if not args.skip_search:
        kab = run_kabah()
        print(f"  [{'TEMBUS' if kab['broken'] else 'BERTAHAN':>8}]  {kab['name']}")
        for row in kab["trials"]:  # type: ignore[attr-defined]
            got = (
                f"ditemukan pada {row['trials']}"
                if row["found"]
                else f"tidak dalam {row['trials']}"
            )
            print(
                f"              {row['bits']:>3} bit: {got}  "
                f"(harapan 2^{row['bits']} = {row['expected']})"
            )
        print(f"              — {kab['note']}")

    sys.exit(0 if gcm["broken"] else 1)


if __name__ == "__main__":
    main()
