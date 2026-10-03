"""Portal 8888 attack campaign: logical / remote attack classes, many randomized trials.
Records: (round, corner, idx, prev, payload, tag). Corners A-D: k=8 (1 KiB payload). Portal P per round.
Head anchor = (last round, last ROOT) held inside the FPGA (not writable by host software)."""
import hashlib, hmac, random, sys, zlib
import model as M
CORN="ABCD"
def keys(master):
    prk=hmac.new(bytes(32),master,hashlib.sha256).digest()
    return {r:hmac.new(prk,f"JIMPORTAL|{r}".encode()+b"\x01",hashlib.sha256).digest() for r in list(CORN)+["P"]}
def IDX(r): return M.tobytes(M.idx_bits(r)+[0]*4)
def mac(K,*parts): return hmac.new(K,b"".join(parts),hashlib.sha256).digest()
def build(R,K,rng):
    prev={c:bytes(32) for c in CORN}; root=bytes(32); recs=[]
    for r in range(R):
        tags=[]
        for c in CORN:
            p=rng.randbytes(1024); t=mac(K[c],c.encode(),IDX(r),prev[c],p)
            recs.append([r,c,IDX(r),prev[c],p,t]); prev[c]=t; tags.append(t)
        root=mac(K["P"],b"P",IDX(r),root,*tags); recs.append([r,"P",IDX(r),None,None,root])
    return recs,(R-1,root)
def verify(recs,K,anchor=None):
    """returns list of flags; checks tag, chain, index continuity, portal root, head anchor."""
    flags=[]; prev={c:bytes(32) for c in CORN}; nexti={c:0 for c in CORN}; root=bytes(32); cur={}; lastr=-1
    nextp=0
    for (r,c,ib,pv,p,t) in recs:
        if c=="P":
            if ib!=IDX(nextp): flags.append(("P-index",r))
            exp=mac(K["P"],b"P",ib,root,*[cur.get(x,b"") for x in CORN])
            if not hmac.compare_digest(exp,t): flags.append(("P-root",r))
            root=t; nextp+=1; lastr=r; continue
        if c not in K: flags.append(("unknown-corner",r)); continue
        if not hmac.compare_digest(mac(K[c],c.encode(),ib,pv,p),t): flags.append(("tag",r,c))
        if pv!=prev[c]: flags.append(("chain",r,c))
        if ib!=IDX(nexti[c]): flags.append(("index",r,c))
        prev[c]=t; cur[c]=t; nexti[c]+=1
    if anchor is not None and (lastr,root)!=anchor: flags.append(("head-anchor",))
    return flags
def run(name, attack, N, R=8, use_anchor=True, seed=1):
    rng=random.Random(seed); K=keys(rng.randbytes(32)); det=0
    for _ in range(N):
        recs,anchor=build(R,K,rng); recs=[list(x) for x in recs]
        recs=attack(recs,rng,K)
        if verify([tuple(x) for x in recs],K,anchor if use_anchor else None): det+=1
    return det
def flipbits(field,n):
    def a(recs,rng,K):
        cand=[x for x in recs if x[1]!="P"] if field!="root" else [x for x in recs if x[1]=="P"]
        x=rng.choice(cand); col={"payload":4,"prev":3,"tag":5,"idx":2,"root":5}[field]
        b=bytearray(x[col]); 
        for i in rng.sample(range(len(b)*8),n): b[i//8]^=1<<(i%8)
        x[col]=bytes(b); return recs
    return a
def delete_mid(recs,rng,K):
    i=rng.randrange(0,len(recs)-6); return recs[:i]+recs[i+1:]
def delete_round(recs,rng,K):   # remove a whole round (4 corners + portal) from the middle
    r=rng.randrange(1,6); return [x for x in recs if x[0]!=r]
def delete_tail(recs,rng,K):    # attacker erases the newest round(s) -- classic log wiping
    n=rng.randint(1,3); return [x for x in recs if x[0]<8-n]
def replay(recs,rng,K):
    x=rng.choice([y for y in recs if y[1]!="P"]); i=rng.randrange(len(recs)); return recs[:i]+[list(x)]+recs[i:]
def reorder(recs,rng,K):
    c=rng.choice(CORN); idx=[i for i,x in enumerate(recs) if x[1]==c]; a,b=rng.sample(idx,2); recs[a],recs[b]=recs[b],recs[a]; return recs
def cross_corner(recs,rng,K):   # move a valid frame of corner A into corner B's slot (relabel)
    x=rng.choice([y for y in recs if y[1]=="A"]); x[1]="B"; return recs
def forge_insert(recs,rng,K):   # attacker w/o key appends a fake frame with a random tag
    i=rng.randrange(len(recs)); r=recs[i][0]; c=rng.choice(CORN)
    return recs[:i]+[[r,c,IDX(r),rng.randbytes(32),rng.randbytes(1024),rng.randbytes(32)]]+recs[i:]
def substitute_recompute_nokey(recs,rng,K):  # rewrite payload and recompute tag with a GUESSED key
    x=rng.choice([y for y in recs if y[1]!="P"]); x[4]=rng.randbytes(1024)
    x[5]=mac(rng.randbytes(32),x[1].encode(),x[2],x[3],x[4]); return recs
def rollback(recs,rng,K):       # replace whole log with an older valid copy (state rollback)
    n=rng.randint(1,4); return [x for x in recs if x[0]<8-n]
N=int(sys.argv[1]) if len(sys.argv)>1 else 300
tests=[("1 bit payload",flipbits("payload",1)),("8 bit payload",flipbits("payload",8)),("64 bit payload",flipbits("payload",64)),
 ("1 bit PREV",flipbits("prev",1)),("1 bit TAG",flipbits("tag",1)),("1 bit IDX",flipbits("idx",1)),("1 bit ROOT portal",flipbits("root",1)),
 ("hapus 1 rekaman tengah",delete_mid),("hapus 1 putaran tengah",delete_round),("hapus ekor (1-3 putaran)",delete_tail),
 ("replay rekaman",replay),("tukar urutan",reorder),("pindah sudut A->B",cross_corner),("sisip palsu tanpa kunci",forge_insert),
 ("ganti isi + TAG kunci tebakan",substitute_recompute_nokey),("rollback ke salinan lama",rollback)]
print(f"N={N} percobaan per kelas, 8 putaran x (4 sudut k=8 + portal)")
print(f"{'kelas serangan':34s} {'dengan jangkar':>15s} {'tanpa jangkar':>15s}")
for name,a in tests:
    d1=run(name,a,N,use_anchor=True,seed=zlib.crc32(name.encode())); d0=run(name,a,N,use_anchor=False,seed=zlib.crc32(name.encode()))
    print(f"{name:34s} {d1:>7d}/{N:<7d} {d0:>7d}/{N:<7d}")
# false positives on clean logs
rng=random.Random(7); K=keys(rng.randbytes(32)); fp=0
for _ in range(N):
    recs,anc=build(8,K,rng)
    if verify(recs,K,anc): fp+=1
print(f"{'log bersih (positif palsu)':34s} {fp:>7d}/{N:<7d}")
