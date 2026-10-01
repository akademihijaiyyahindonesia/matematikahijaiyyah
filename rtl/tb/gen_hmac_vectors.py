#!/usr/bin/env python3
"""Golden vectors for the HMAC-SHA256 benches, from Python's hashlib/hmac.

    python3 rtl/tb/gen_hmac_vectors.py

writes rtl/tb/sha256_vectors.txt (tb_hijaiyyah_sha256_stream.v) and
rtl/tb/hmac_vectors.txt (tb_hijaiyyah_hmac.v, tb_hijaiyyah_hmac_gowin_top.v).

SHA-256: the four FIPS 180-4 example messages, every length 0..129 (every
padding boundary of one and two blocks), then twenty random lengths up to 999.
HMAC: RFC 4231 cases 1-7, each cross-checked against the RFC text before it is
written, then sixty random keys (1..64 bytes) and messages (0..299 bytes).
Keys longer than 64 bytes are written as SHA-256(K), as RFC 2104 specifies
and the RTL expects its caller to do. Seeded, so the files are reproducible.
"""
import hashlib
import hmac
import random
from pathlib import Path

TB = Path(__file__).resolve().parent

random.seed(20261001)
msgs = [b"", b"abc",
        b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
        b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu"]
# every length around the padding boundaries, then random
for n in list(range(0, 130)) + [random.randrange(130, 1000) for _ in range(20)]:
    msgs.append(bytes(random.randrange(256) for _ in range(n)))
with open(str(TB / "sha256_vectors.txt"), "w") as f:
    f.write(f"{len(msgs)}\n")
    for m in msgs:
        f.write(f"{len(m)}\n")
        for b in m: f.write(f"{b:02x}\n")
        f.write(hashlib.sha256(m).hexdigest() + "\n")
print(len(msgs), "sha256 vectors")

random.seed(20261001)
rfc = [
 (b"\x0b"*20, b"Hi There",
  "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
 (b"Jefe", b"what do ya want for nothing?",
  "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"),
 (b"\xaa"*20, b"\xdd"*50,
  "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"),
 (bytes(range(1,26)), b"\xcd"*50,
  "82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b"),
 (b"\x0c"*20, b"Test With Truncation",
  "a3b6167473100ee06e0c796c2955552b"),   # truncated to 128 bits
 (b"\xaa"*131, b"Test Using Larger Than Block-Size Key - Hash Key First",
  "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"),
 (b"\xaa"*131, b"This is a test using a larger than block-size key and a larger than block-size data. The key needs to be hashed before being used by the HMAC algorithm.",
  "9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2"),
]
cases = []
for i,(k,m,exp) in enumerate(rfc, 1):
    full = hmac.new(k, m, hashlib.sha256).hexdigest()
    assert full.startswith(exp), f"RFC 4231 case {i} disagrees with python"
    cases.append((k, m, full, f"RFC4231-{i}"))
for j in range(60):
    k = bytes(random.randrange(256) for _ in range(random.choice([1,16,32,32,48,63,64])))
    m = bytes(random.randrange(256) for _ in range(random.randrange(0, 300)))
    cases.append((k, m, hmac.new(k, m, hashlib.sha256).hexdigest(), f"rand-{j}"))
with open(str(TB / "hmac_vectors.txt"),"w") as f:
    f.write(f"{len(cases)}\n")
    for k,m,mac,name in cases:
        kk = hashlib.sha256(k).digest() if len(k) > 64 else k
        f.write((kk + bytes(64-len(kk))).hex() + "\n")
        f.write(f"{len(m)}\n")
        for b in m: f.write(f"{b:02x}\n")
        f.write(mac + "\n")
print(len(cases), "cases; RFC 4231 cross-check OK")
