#!/usr/bin/env python3
"""Vectors for tb_ingress and tb_jim, from the reference models (packets.py, model.py).
  python3 ref/vectors.py <outdir>  ->  frames.txt expect.txt  sync_bits.txt sync_expect.txt idx_expect.txt
Formats are the ones the testbenches $fscanf. Seeds are fixed, so the files are byte-identical every run."""
import os, random, sys
import model as M, packets as P
out = sys.argv[1] if len(sys.argv) > 1 else "build"
os.makedirs(out, exist_ok=True)
def w(name, lines):
    with open(os.path.join(out, name), "w") as f: f.write("".join(l + "\n" for l in lines))

# ingress_parse: 3000 random frames, every kind packets.random_frames builds; expected = packets.parse
frames = P.random_frames(3000, random.Random(20261001))
fl, el = [str(len(frames))], []
for kind, f in frames:
    fl.append(str(len(f))); fl += [f"{b:02x}" for b in f]
    st, ver, ip, sp, dp, pr, mac = P.parse(f)
    el.append(f"{st} {ver} {ip.hex()} {sp:04x} {dp:04x} {pr:02x} {(mac or bytes(6)).hex()}")
w("frames.txt", fl); w("expect.txt", el)

# jim_sync: 32 chained k=1 frames (model.build); frame i's marker carries i%4 bit errors, so the stream
# holds markers at Hamming 0,1,2 (must hit, T=2) and 3 (must not). Expected hits are found by brute
# force over the whole stream -- a near-marker inside a payload counts exactly as the RTL sees it.
rng = random.Random(31)
key = bytes(rng.getrandbits(8) for _ in range(32))
fr = M.build([bytes(rng.getrandbits(8) for _ in range(128)) for _ in range(32)], key)
for i, f in enumerate(fr):
    for j in rng.sample(range(31), i % 4): f[j] ^= 1
bits = [b for f in fr for b in f]
hits = [n for n in range(30, len(bits)) if sum(bits[n-30+j] != M.SYNC[j] for j in range(31)) <= 2]
w("sync_bits.txt", [str(b) for b in bits]); w("sync_expect.txt", [str(n) for n in hits])

# jim_index: the GF(5) orbit from (1,0,0,0,0), one state d0..d4 per line, before each step
w("idx_expect.txt", ["".join(map(str, v)) for v in M.IDX_STATES])
print(f"{out}: {len(frames)} frames, {len(bits)} sync bits, {len(hits)} expected hits, {len(M.IDX_STATES)} index states")
