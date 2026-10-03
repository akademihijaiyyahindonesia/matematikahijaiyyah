"""Portal 8888 + ingress provenance: each corner = one physical ingress port of the FPGA.
Record sealed inside the FPGA:
  DEV(8B) | PORT(1B) | CTR(8B) | OBS(status,ver,src_ip16,sport,dport,proto,src_mac) | FRAME_HASH(32B) | IDX | PREV | TAG
TAG = HMAC(K_port, "R" || DEV || PORT || CTR || OBS || FRAME_HASH || IDX || PREV)
Portal per round: ROOT = HMAC(K_portal, IDX || ROOT_prev || TAG_A..TAG_D); head anchor (round, ROOT, CTR) in FPGA."""
import hashlib, hmac, random, struct, json, sys
import model as M, packets as P
PORTS = "ABCD"
def keys(master):
    prk = hmac.new(bytes(32), master, hashlib.sha256).digest()
    return {r: hmac.new(prk, f"PORTAL8888|{r}".encode()+b"\x01", hashlib.sha256).digest() for r in list(PORTS)+["P"]}
def IDX(r): return M.tobytes(M.idx_bits(r)+[0]*4)
def obs_bytes(o):
    st, ver, ip, sp, dp, pr, mac = o; mac = mac if len(mac)==6 else bytes(6)
    return struct.pack(">BB16sHHB6s", st, ver, ip, sp, dp, pr, mac)
def tag(K, rec):
    return hmac.new(K[rec["port"]], b"R"+rec["dev"]+rec["port"].encode()+struct.pack(">Q",rec["ctr"])+obs_bytes(rec["obs"])
                    +rec["fhash"]+IDX(rec["idx"])+rec["prev"], hashlib.sha256).digest()
class Portal:
    """the FPGA side: only this object holds keys, the counter and the head anchor"""
    def __init__(self, dev, master):
        self.dev, self.K = dev, keys(master); self.ctr = 0; self.prev = {p: bytes(32) for p in PORTS}
        self.idx = {p: 0 for p in PORTS}; self.root = bytes(32); self.round = -1; self.pending = {}; self.log = []
    def ingress(self, port, frame):                         # bytes arrive on a physical port
        self.ctr += 1
        rec = dict(dev=self.dev, port=port, ctr=self.ctr, obs=P.parse(frame), fhash=hashlib.sha256(frame).digest(),
                   idx=self.idx[port], prev=self.prev[port])
        rec["tag"] = tag(self.K, rec); self.prev[port] = rec["tag"]; self.idx[port] += 1
        self.log.append(rec); self.pending[port] = rec["tag"]
        if len(self.pending) == 4:                          # one round closed: portal record
            self.round += 1
            self.root = hmac.new(self.K["P"], IDX(self.round)+self.root+b"".join(self.pending[p] for p in PORTS), hashlib.sha256).digest()
            self.log.append(dict(port="P", round=self.round, tags=[self.pending[p] for p in PORTS], root=self.root)); self.pending = {}
    def anchor(self):  # head anchor: register file inside the FPGA, not host-writable
        return (self.round, self.root, self.ctr, tuple(self.prev[p] for p in PORTS))
def verify(log, K, anchor):
    flags = []; prev = {p: bytes(32) for p in PORTS}; nxt = {p: 0 for p in PORTS}; root = bytes(32); last = {}; r = -1; lastctr = 0
    for rec in log:
        if rec["port"] == "P":
            r += 1
            if rec["tags"] != [last.get(p) for p in PORTS]: flags.append(("portal-tags", r))
            exp = hmac.new(K["P"], IDX(r)+root+b"".join(rec["tags"]), hashlib.sha256).digest()
            if not hmac.compare_digest(exp, rec["root"]): flags.append(("portal-root", r))
            root = rec["root"]; continue
        p = rec["port"]
        if p not in PORTS: flags.append(("unknown-port", rec.get("ctr"))); continue
        if not hmac.compare_digest(tag(K, rec), rec["tag"]): flags.append(("tag", p, rec["ctr"]))
        if rec["prev"] != prev[p]: flags.append(("chain", p, rec["ctr"]))
        if rec["idx"] != nxt[p]: flags.append(("index", p, rec["ctr"]))
        if rec["ctr"] <= lastctr: flags.append(("counter-order", p, rec["ctr"]))
        lastctr = rec["ctr"]; prev[p] = rec["tag"]; nxt[p] += 1; last[p] = rec["tag"]
    if (r, root, lastctr, tuple(prev[p] for p in PORTS)) != anchor: flags.append(("head-anchor",))
    return flags
