#!/usr/bin/env python3
"""Emit keys + fixed record fields (no timestamps) for the system testbench.
Timestamps come live from the GPS-PPS timestamp module inside the sim."""
import random
rng = random.Random(20261001)
K = {c: rng.randbytes(32) for c in "ABCDP"}
recs = []
for i in range(4):
    recs.append(dict(ip=bytes([203,0,113,10+i])+bytes(12),
                     sport=51000+i, dport=22, proto=6, idx=100+i))
PIDX = 7
if __name__ == "__main__":
    for c in "ABCDP":
        print(f"K{c} {(K[c]+bytes(32)).hex()}")
    for i,r in enumerate(recs):
        print(f"REC {i} {r['ip'].hex()} {r['sport']:04x} {r['dport']:04x} {r['proto']:02x} {r['idx']:04x}")
    print(f"PIDX {PIDX:04x}")
