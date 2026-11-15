"""Four-corner portal: four Jim/HMAC chains (k=8) joined each round by a portal frame.
ROOT_r = HMAC(K, IDX_r || ROOT_{r-1} || TAG_A_r || TAG_B_r || TAG_C_r || TAG_D_r)."""
import hashlib, hmac, random, model as M
CORNERS="ABCD"
def keys(master):  # key separation per role, HKDF-expand shape (as derive_key in guarded_record.py)
    prk=hmac.new(bytes(32),master,hashlib.sha256).digest()
    return {r:hmac.new(prk,f"JIMPORTAL|{r}".encode()+b"\x01",hashlib.sha256).digest() for r in list(CORNERS)+["PORTAL"]}
def build(rounds, master, rng):
    K=keys(master); prev={c:bytes(32) for c in CORNERS}; root=bytes(32); log=[]
    for r in range(rounds):
        tags={}
        for c in CORNERS:
            p=bytes(rng.getrandbits(8) for _ in range(1024))
            ib=M.idx_bits(r); t=hmac.new(K[c],M.tobytes(ib+[0]*4)+prev[c]+p,hashlib.sha256).digest()
            log.append((r,c,ib,prev[c],p,t)); prev[c]=t; tags[c]=t
        ib=M.idx_bits(r); root=hmac.new(K["PORTAL"],M.tobytes(ib+[0]*4)+root+b"".join(tags[c] for c in CORNERS),hashlib.sha256).digest()
        log.append((r,"P",ib,None,None,root))
    return log
def verify(log, master):
    K=keys(master); prev={c:bytes(32) for c in CORNERS}; root=bytes(32); cur={}; bad=[]
    for (r,c,ib,pv,p,t) in log:
        if c!="P":
            ok=hmac.compare_digest(hmac.new(K[c],M.tobytes(ib+[0]*4)+pv+p,hashlib.sha256).digest(),t) and pv==prev[c]
            if not ok: bad.append((r,c))
            prev[c]=t; cur[c]=t
        else:
            exp=hmac.new(K["PORTAL"],M.tobytes(ib+[0]*4)+root+b"".join(cur[x] for x in CORNERS),hashlib.sha256).digest()
            if not hmac.compare_digest(exp,t): bad.append((r,"PORTAL"))
            root=t
    return bad
rng=random.Random(20261001); MK=hashlib.sha256(b"master-test-only").digest()
log=build(6,MK,rng)
print("bersih            :", verify(log,MK) or "semua sah")
L=list(log); i=[n for n,x in enumerate(L) if x[0]==3 and x[1]=="C"][0]
r,c,ib,pv,p,t=L[i]; L[i]=(r,c,ib,pv,bytes([p[0]^1])+p[1:],t)
print("sudut C putaran 3 dirusak 1 bit:", verify(L,MK))
L=list(log); i=[n for n,x in enumerate(L) if x[0]==2 and x[1]=="P"][0]
r,c,ib,pv,p,t=L[i]; L[i]=(r,c,ib,pv,p,bytes(32))
print("portal putaran 2 dipalsukan    :", verify(L,MK))
