#!/usr/bin/env python3
"""Verify the system run: recompute every corner TAG and the portal ROOT from the
exact bytes the RTL sealed (keys from portal_sys_keys.py, live GPS timestamps and
tags from rtl/portal_sys_result.txt), byte-exact."""
import hmac, hashlib, struct, sys
K = {}
fields = {}
for line in open("rtl/portal_sys_keys.txt" if len(sys.argv) < 2 else sys.argv[1]):
    t = line.split()
    if t[0].startswith("K"): K[t[0][1:]] = bytes.fromhex(t[1])[:32]   # strip the zero pad
    elif t[0] == "REC":
        p = int(t[1]); fields[p] = (bytes.fromhex(t[2]), int(t[3],16), int(t[4],16), int(t[5],16), int(t[6],16))
    elif t[0] == "PIDX": PIDX = int(t[1],16)
def mac(key, body): return hmac.new(key, body, hashlib.sha256).digest()
# results: lines "COR p sec tick tag" and "ROOT hex"
res = {}; root_rtl = None
for line in open("rtl/portal_sys_result.txt"):
    t = line.split()
    if t[0] == "COR": res[int(t[1])] = (int(t[2]), int(t[3]), bytes.fromhex(t[4]))
    elif t[0] == "ROOT": root_rtl = bytes.fromhex(t[1])
prev = {0:bytes(32),1:bytes(32),2:bytes(32),3:bytes(32)}
tags = {}; bad = 0
for p in range(4):
    sec, tick, tag_rtl = res[p]
    ip, sport, dport, proto, idx = fields[p]
    body = bytes([p]) + struct.pack(">II", sec, tick) + ip + struct.pack(">HHB", sport, dport, proto) \
           + struct.pack(">H", idx) + prev[p]
    assert len(body) == 64
    t = mac(K["ABCD"[p]], body)
    ok = (t == tag_rtl); bad += (not ok); tags[p] = t; prev[p] = t
    print(f"corner {p}: T={sec}.{tick:09d}  tag {'OK' if ok else 'MISMATCH'}")
pbody = struct.pack(">H", PIDX) + bytes(32) + tags[0]+tags[1]+tags[2]+tags[3]
root = mac(K["P"], pbody)
rok = (root == root_rtl); bad += (not rok)
print(f"portal ROOT: {'OK' if rok else 'MISMATCH'}")
print(f"RESULT: {'ALL BYTE-EXACT' if bad==0 else str(bad)+' MISMATCH'} (RTL sealed with live GPS timestamps)")
sys.exit(1 if bad else 0)
