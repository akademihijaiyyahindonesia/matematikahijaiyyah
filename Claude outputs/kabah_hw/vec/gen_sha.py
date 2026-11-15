# Test vectors for sha256_stream: NIST FIPS 180-4 examples + random lengths.
import hashlib, random
random.seed(20261001)
msgs = [b"", b"abc",
        b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
        b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu"]
# every length around the padding boundaries, then random
for n in list(range(0, 130)) + [random.randrange(130, 1000) for _ in range(20)]:
    msgs.append(bytes(random.randrange(256) for _ in range(n)))
with open("vec/sha.txt", "w") as f:
    f.write(f"{len(msgs)}\n")
    for m in msgs:
        f.write(f"{len(m)}\n")
        for b in m: f.write(f"{b:02x}\n")
        f.write(hashlib.sha256(m).hexdigest() + "\n")
print(len(msgs), "vectors")
