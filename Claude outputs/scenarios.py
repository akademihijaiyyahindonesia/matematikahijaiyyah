import random, hashlib, hmac, model as M
rng=random.Random(20261001); KEY=hashlib.sha256(b"test-key-not-real").digest()
def payloads(n,k): return [bytes(rng.getrandbits(8) for _ in range(k*128)) for _ in range(n)]
def flat(frames): return [b for f in frames for b in f]
def summary(r): 
    from collections import Counter; return dict(Counter(x[0] for x in r))
for k in (1,8):
    L=M.HDR+k*1024+M.TAGB
    print(f"\n== k={k}: frame {L} bits, payload {k*1024} bits, overhead {100*(L-k*1024)/L:.2f}%")
    P=payloads(12,k); F=M.build(P,KEY)
    print("clean          ", summary(M.parse(flat(F),KEY,k)))
    G=[list(f) for f in F]; G[5]=G[5][:len(G[5])//3]                      # truncation
    print("truncate #5    ", summary(M.parse(flat(G),KEY,k)))
    G=[list(f) for f in F]; G[6][400]^=1                                     # 1 bit flip in payload
    print("bitflip #6     ", summary(M.parse(flat(G),KEY,k)))
    G=[list(f) for f in F]; del G[4]                                         # drop
    print("drop #4        ", summary(M.parse(flat(G),KEY,k)))
    G=[list(f) for f in F]; G.insert(7,list(F[6]))                           # duplicate/replay
    print("replay #6      ", summary(M.parse(flat(G),KEY,k)))
    G=[list(f) for f in F]; G[3],G[4]=G[4],G[3]                              # reorder
    print("swap #3/#4     ", summary(M.parse(flat(G),KEY,k)))
    # attacker without key rewrites payload and recomputes a sum-like "checksum" -> must be REJECT_TAG
    G=[list(f) for f in F]; forged=bytes(rng.getrandbits(8) for _ in range(k*128))
    G[8]=G[8][:299]+M.bits(forged)+G[8][299+k*1024:]
    print("forge #8 nokey ", summary(M.parse(flat(G),KEY,k)))
    # stream with 3 random garbage bytes inserted before frame 2 (misalignment)
    G=[list(f) for f in F]; G[2]=[rng.getrandbits(1) for _ in range(19)]+G[2]
    print("misalign +19b  ", summary(M.parse(flat(G),KEY,k)))
