import random, hashlib, copy, json, provenance as V, packets as P
N = 300
def scenario(rng):
    portal = V.Portal(b"TN20K-01", rng.randbytes(32))
    frames = P.random_frames(40, rng)
    for k, f in frames: portal.ingress(rng.choice(V.PORTS), f)
    return portal
def recs(log): return [i for i, x in enumerate(log) if x["port"] != "P"]
def ip_records(log): return [i for i in recs(log) if log[i]["obs"][0] == P.OK]
def a_change_ip(log, rng, K):
    i = rng.choice(ip_records(log)); o = list(log[i]["obs"]); o[2] = rng.randbytes(16); log[i]["obs"] = tuple(o); return log
def a_change_port_field(log, rng, K):
    i = rng.choice(ip_records(log)); o = list(log[i]["obs"]); o[3] ^= 1; log[i]["obs"] = tuple(o); return log
def a_change_mac(log, rng, K):
    i = rng.choice(recs(log)); o = list(log[i]["obs"]); o[6] = rng.randbytes(6); log[i]["obs"] = tuple(o); return log
def a_move_ingress(log, rng, K):          # claim the frame arrived on another physical port
    i = rng.choice(recs(log)); log[i]["port"] = rng.choice([p for p in V.PORTS if p != log[i]["port"]]); return log
def a_change_ctr(log, rng, K):            # claim a different arrival order/time
    i = rng.choice(recs(log)); log[i]["ctr"] += rng.choice([-1, 1, 1000]); return log
def a_swap_evidence(log, rng, K):         # replace the raw frame hash (swap the evidence body)
    i = rng.choice(recs(log)); log[i]["fhash"] = hashlib.sha256(rng.randbytes(64)).digest(); return log
def a_wipe_attacker(log, rng, K):         # delete every record from one source IP (log wiping by malware)
    i = rng.choice(ip_records(log)); ip = log[i]["obs"][2]
    return [x for x in log if not (x["port"] != "P" and x["obs"][2] == ip)]
def a_wipe_tail(log, rng, K): return log[:-rng.randint(1, 5)]
def a_host_forge(log, rng, K):            # host software inserts a record claiming port A, no key
    i = rng.randrange(len(log)); fake = dict(log[rng.choice(recs(log))]); fake["obs"] = P.parse(P.random_frames(1, rng)[0][1])
    return log[:i] + [fake] + log[i:]
tests = [("ubah IP sumber", a_change_ip), ("ubah port TCP/UDP", a_change_port_field), ("ubah MAC sumber", a_change_mac),
         ("klaim masuk lewat port fisik lain", a_move_ingress), ("ubah urutan/waktu tiba (CTR)", a_change_ctr),
         ("tukar bukti frame mentah", a_swap_evidence), ("hapus semua catatan satu IP", a_wipe_attacker),
         ("hapus catatan terbaru", a_wipe_tail), ("host menyisipkan catatan palsu", a_host_forge)]
print(f"{'serangan atas bukti asal':36s} terdeteksi")
for name, atk in tests:
    rng = random.Random(name); det = 0
    for _ in range(N):
        pt = scenario(rng); log = atk(copy.deepcopy(pt.log), rng, pt.K)
        if V.verify(log, pt.K, pt.anchor()): det += 1
    print(f"{name:36s} {det}/{N}")
rng = random.Random(9); fp = sum(1 for _ in range(N) if V.verify((pt := scenario(rng)).log, pt.K, pt.anchor()))
print(f"{'log bersih (positif palsu)':36s} {fp}/{N}")
# limitation: spoofed source at origin -- the frame itself lies; sealing is honest about what was observed
rng = random.Random(5); pt = V.Portal(b"TN20K-01", rng.randbytes(32))
spoof = P.eth(rng.randbytes(6), rng.randbytes(6), 0x0800) + P.ipv4(bytes([8,8,8,8]), rng.randbytes(4), 17, P.l4(53, 4444, 17))
pt.ingress("A", spoof); [pt.ingress(p, P.random_frames(1, rng)[0][1]) for p in "BCD"]
print("IP sumber dipalsukan di asal (UDP, klaim 8.8.8.8): verifikasi =", V.verify(pt.log, pt.K, pt.anchor()) or "SAH (tercatat apa adanya)")
