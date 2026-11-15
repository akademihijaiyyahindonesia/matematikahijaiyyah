#!/usr/bin/env python3
"""
Test hmac_gowin_top.v against real hardware over a real port.

The wrapper's protocol, one request per frame:
    host -> board   64-byte key block (K zero-padded), 2-byte length L
                    (big-endian), then L message bytes
    board -> host   32-byte HMAC-SHA256, then 4-byte engine clock count

The reference is the repository's own software path,
hijaiyyah.crypto.signing.sign_bytes (hmac.new(key, data, sha256)) -- the
Ka'bah lapis 3 the board is replacing -- so a PASS means the silicon and the
software agree byte for byte, not merely that the board matches a table.

Vectors: RFC 4231 test cases 1-7 (keys longer than 64 bytes are replaced by
SHA-256(K) on the host, as RFC 2104 specifies and the RTL expects), then
--random extra cases with keys of 1..64 bytes and messages of 0..1000 bytes.

    python3 rtl/scripts/hmac_uart_test.py /dev/tty.usbserial-X
    python3 rtl/scripts/hmac_uart_test.py /dev/tty.usbserial-X --random 200

With no port, it prints the expected MACs only.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    from hijaiyyah.crypto.signing import sign_bytes  # noqa: E402
except ImportError:      # outside the repository: same construction
    def sign_bytes(data: bytes, key: bytes) -> bytes:
        return hmac.new(key, data, hashlib.sha256).digest()

MAC_BYTES = 32
CLOCK_BYTES = 4
BLOCK = 64

RFC4231 = [
    (b"\x0b" * 20, b"Hi There",
     "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
    (b"Jefe", b"what do ya want for nothing?",
     "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"),
    (b"\xaa" * 20, b"\xdd" * 50,
     "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"),
    (bytes(range(1, 26)), b"\xcd" * 50,
     "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"),
    (b"\x0c" * 20, b"Test With Truncation",
     "a3b6167473100ee06e0c796c2955552b"),             # RFC gives 128 bits
    (b"\xaa" * 131, b"Test Using Larger Than Block-Size Key - Hash Key First",
     "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
    (b"\xaa" * 131,
     b"This is a test using a larger than block-size key and a larger than "
     b"block-size data. The key needs to be hashed before being used by the "
     b"HMAC algorithm.",
     "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"),
]


def key_block(key: bytes) -> bytes:
    if len(key) > BLOCK:
        key = hashlib.sha256(key).digest()
    return key + bytes(BLOCK - len(key))


def frame(key: bytes, message: bytes) -> bytes:
    if len(message) > 0xFFFF:
        raise ValueError("message longer than the 16-bit length field")
    return key_block(key) + len(message).to_bytes(2, "big") + message


def cases(n_random: int, seed: int) -> list[tuple[str, bytes, bytes, bytes]]:
    out = []
    for i, (k, m, rfc) in enumerate(RFC4231, 1):
        want = sign_bytes(m, k)
        if not want.hex().startswith(rfc):
            raise SystemExit(f"RFC 4231 case {i}: software disagrees with the RFC")
        out.append((f"RFC4231-{i}", k, m, want))
    rng = random.Random(seed)
    for j in range(n_random):
        k = rng.randbytes(rng.randint(1, BLOCK))
        m = rng.randbytes(rng.randint(0, 1000))
        out.append((f"random-{j}", k, m, sign_bytes(m, k)))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", help="serial device; omit to print only")
    ap.add_argument("--random", type=int, default=50, help="extra random cases")
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args(argv)

    todo = cases(args.random, args.seed)
    if args.port is None:
        for name, k, m, want in todo:
            print(f"{name}: key={len(k)}B msg={len(m)}B want={want.hex()}")
        return 0

    try:
        import serial  # pyserial, optional
    except ImportError:
        print("pyserial is not installed: pip install pyserial", file=sys.stderr)
        return 2

    passed = failed = 0
    with serial.Serial(args.port, args.baud, timeout=10) as link:
        link.reset_input_buffer()
        for name, k, m, want in todo:
            t0 = time.monotonic()
            link.write(frame(k, m))
            link.flush()
            got = link.read(MAC_BYTES + CLOCK_BYTES)
            wall = time.monotonic() - t0
            if len(got) != MAC_BYTES + CLOCK_BYTES:
                print(f"{name}: only {len(got)}/{MAC_BYTES + CLOCK_BYTES} bytes "
                      f"-- timed out", file=sys.stderr)
                failed += 1
                continue
            mac, clocks = got[:MAC_BYTES], int.from_bytes(got[MAC_BYTES:], "big")
            ok = mac == want
            passed += ok
            failed += not ok
            print(f"{name}: key={len(k)}B msg={len(m)}B engine_clocks={clocks} "
                  f"wall={wall:.3f}s {'PASS' if ok else 'FAIL'}"
                  + ("" if ok else f" got={mac.hex()} want={want.hex()}"))

    print(f"RESULT: {passed} PASS, {failed} FAIL, of {len(todo)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
