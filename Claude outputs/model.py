"""Reference model: Jim-sync block parser + chained HMAC-SHA256 (Ka'bah lapis 3).
Frame (bits):  SYNC 31 | IDX 12 (GF(5) state, base-5, 0..3124) | PREV 256 | PAYLOAD k*1024 | TAG 256
TAG_i = HMAC-SHA256(K_mac, IDX_i || PREV_i || PAYLOAD_i),  PREV_i = TAG_{i-1}  (PREV_0 = 0^256)
"""
import hashlib, hmac, random
FACE = [[3,0,3,0,0],[0,1,0,0,1],[0,1,0,0,0],[1,0,0,0,0],[0,0,0,1,1]]   # cosmic-codex-jim/MACHINE.md §1
def step(v, p): return [sum(FACE[r][c]*v[c] for c in range(5)) % p for r in range(5)]
def orbit(p, v=(1,0,0,0,0)):
    out=[list(v)]
    while True:
        v=step(out[-1],p)
        if v==out[0]: return out
        out.append(v)
SYNC=[s[0] for s in orbit(2)]
IDX_STATES=orbit(5)
assert "".join(map(str,SYNC))=="1111101110001010110100001100100", "Jim sync differs from WAVE.md"
assert len(SYNC)==31 and len(IDX_STATES)==3124
def idx_bits(i):
    v=IDX_STATES[i % 3124]; n=sum(d*5**k for k,d in enumerate(reversed(v)))
    return [int(b) for b in format(n,'012b')]
def bits(b): return [int(x) for byte in b for x in format(byte,'08b')]
def tobytes(bl): return bytes(int("".join(map(str,bl[i:i+8])),2) for i in range(0,len(bl),8))
HDR=31+12+256; TAGB=256
def build(chain_payloads, key):
    prev=bytes(32); out=[]
    for i,p in enumerate(chain_payloads):
        ib=idx_bits(i)
        tag=hmac.new(key, tobytes(ib+[0,0,0,0])+prev+p, hashlib.sha256).digest()
        out.append(SYNC+ib+bits(prev)+bits(p)+bits(tag)); prev=tag
    return out
def parse(stream, key, k, t=2):
    L=HDR+k*1024+TAGB; res=[]; i=0; prev=None; expect=None
    while i<=len(stream)-31:
        if sum(stream[i+j]!=SYNC[j] for j in range(31))<=t and i+L<=len(stream):
            f=stream[i:i+L]; ib=f[31:43]; pv=tobytes(f[43:299]); pl=tobytes(f[299:299+k*1024]); tg=tobytes(f[299+k*1024:])
            n=int("".join(map(str,ib)),2)
            ok_tag=hmac.compare_digest(hmac.new(key, tobytes(ib+[0,0,0,0])+pv+pl, hashlib.sha256).digest(), tg)
            if not ok_tag: res.append(("REJECT_TAG",i)); i+=1; continue
            if prev is not None and pv!=prev: res.append(("CHAIN_BREAK",i,n))
            if expect is not None and n!=expect: res.append(("INDEX_GAP",i,n))
            res.append(("OK",i,n)); prev=tg
            pos=[s for s in range(3124) if int("".join(map(str,idx_bits(s))),2)==n]
            expect=int("".join(map(str,idx_bits(pos[0]+1))),2) if pos else None
            i+=L
        else: i+=1
    return res
