"""Portal 8888 as Find-My + anomalous-login, the Apple/Windows pattern.
Exact location = device's OWN GPS, self-reported & sealed (NOT latency).
Anomaly detection = coarse region + the precise TIMESTAMP (impossible travel)."""
import math, random, statistics, hashlib, hmac
R_EARTH = 6371.0
def km(a, b):
    (la1,lo1),(la2,lo2)=a,b
    p1,p2=math.radians(la1),math.radians(la2); dla=p2-p1; dlo=math.radians(lo2-lo1)
    x=math.sin(dla/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dlo/2)**2
    return 2*R_EARTH*math.asin(min(1,math.sqrt(x)))
HOME=(-6.2,106.8)   # Jakarta area
MAX_KMH=1000.0      # faster than any airliner -> physically impossible = breach
def record(dev,loc,t,ip_region,key,prev):
    body=f"{dev}|{loc}|{t}|{ip_region}".encode()
    tag=hmac.new(key,prev+body,hashlib.sha256).digest()
    return dict(dev=dev,loc=loc,t=t,region=ip_region,tag=tag,prev=prev)
def impossible_travel(r_prev,r_now):
    dt_h=abs(r_now["t"]-r_prev["t"])/3600.0
    if dt_h<=0: return r_now["loc"]!=r_prev["loc"]        # same instant, two places
    return km(r_prev["loc"],r_now["loc"])/dt_h > MAX_KMH
def run(scenario, N, rng):
    det=0
    for _ in range(N):
        key=rng.randbytes(32); prev=bytes(32); log=[]
        t=rng.uniform(0,1e5)
        # baseline: a day of normal logins near home
        for _ in range(8):
            loc=(HOME[0]+rng.gauss(0,0.05),HOME[1]+rng.gauss(0,0.05))
            r=record("PHONE-01",loc,t,"ID-Jakarta",key,prev); log.append(r); prev=r["tag"]; t+=rng.uniform(1800,9000)
        flagged=False
        if scenario=="normal":
            loc=(HOME[0]+rng.gauss(0,0.05),HOME[1]+rng.gauss(0,0.05))
            r=record("PHONE-01",loc,t+3600,"ID-Jakarta",key,prev); log.append(r)
        elif scenario=="breach_abroad":        # account login from far region minutes later
            r=record("PHONE-01",(50.1,8.6),t+600,"DE-Frankfurt",key,prev); log.append(r)  # Frankfurt, 10 min later
        elif scenario=="stolen_moving":         # phone reports GPS moving to unknown area fast
            r=record("PHONE-01",(HOME[0]+3.0,HOME[1]+2.0),t+900,"ID-Jakarta",key,prev); log.append(r)
        elif scenario=="tamper_erase":          # attacker edits a record to hide the foreign login
            r=record("PHONE-01",(50.1,8.6),t+600,"DE-Frankfurt",key,prev); log.append(r)
            log[-1]=dict(log[-1]); log[-1]["region"]="ID-Jakarta"  # rewrite region, leave tag
        # detection: chain intact?  + impossible travel?
        prev=bytes(32); chain_ok=True
        for r in log:
            exp=hmac.new(key,prev+f'{r["dev"]}|{r["loc"]}|{r["t"]}|{r["region"]}'.encode(),hashlib.sha256).digest()
            if not hmac.compare_digest(exp,r["tag"]): chain_ok=False
            prev=r["tag"]
        if not chain_ok: flagged=True
        if impossible_travel(log[-2],log[-1]): flagged=True
        if flagged: det+=1
    return det
rng=random.Random(20261001); N=300
print(f"{'skenario':>20} {'ditandai/N':>14}   arti")
print(f"{'normal (di rumah)':>20} {run('normal',N,rng):>8}/{N}     harus ~0 (positif palsu)")
print(f"{'login dari luar neg.':>20} {run('breach_abroad',N,rng):>8}/{N}     impossible travel: Jkt->Frankfurt 10 mnt")
print(f"{'HP bergerak cepat':>20} {run('stolen_moving',N,rng):>8}/{N}     lompat lokasi tak wajar")
print(f"{'sunting catatan':>20} {run('tamper_erase',N,rng):>8}/{N}     rantai putus (sembunyikan jejak)")

# --- finding: impossible-travel misses a slowly-moved stolen device. Add geofence + lost-mode. ---
HOME_RADIUS_KM=150.0; KNOWN_REGIONS={"ID-Jakarta"}
def anomalies(log, key, lost_mode=False):
    f=set(); prev=bytes(32)
    for r in log:
        exp=hmac.new(key,prev+f'{r["dev"]}|{r["loc"]}|{r["t"]}|{r["region"]}'.encode(),hashlib.sha256).digest()
        if not hmac.compare_digest(exp,r["tag"]): f.add("tamper")
        prev=r["tag"]
    if impossible_travel(log[-2],log[-1]): f.add("impossible_travel")
    last=log[-1]
    if km(HOME,last["loc"])>HOME_RADIUS_KM: f.add("left_geofence")      # soft: owner may travel
    if last["region"] not in KNOWN_REGIONS: f.add("new_region")         # soft
    if lost_mode and km(HOME,last["loc"])>HOME_RADIUS_KM: f.add("LOST_MODE_FOUND")  # hard: owner marked lost
    return f
def run2(scn,N,rng,lost=False):
    hard=soft=0
    for _ in range(N):
        key=rng.randbytes(32); prev=bytes(32); log=[]; t=rng.uniform(0,1e5)
        for _ in range(8):
            loc=(HOME[0]+rng.gauss(0,0.05),HOME[1]+rng.gauss(0,0.05))
            r=record("PHONE-01",loc,t,"ID-Jakarta",key,prev); log.append(r); prev=r["tag"]; t+=rng.uniform(1800,9000)
        if scn=="normal": r=record("PHONE-01",(HOME[0]+rng.gauss(0,0.05),HOME[1]+rng.gauss(0,0.05)),t+3600,"ID-Jakarta",key,prev)
        elif scn=="breach_abroad": r=record("PHONE-01",(50.1,8.6),t+600,"DE-Frankfurt",key,prev)
        elif scn=="stolen_moving": r=record("PHONE-01",(HOME[0]+3.0,HOME[1]+2.0),t+7200,"ID-Jakarta",key,prev)
        elif scn=="tamper": 
            r=record("PHONE-01",(50.1,8.6),t+600,"DE-Frankfurt",key,prev); log.append(r); log.append(dict(log[-1])); log[-1]["region"]="ID-Jakarta"; r=None
        if r is not None: log.append(r)
        a=anomalies(log,key,lost_mode=lost)
        if a&{"tamper","impossible_travel","LOST_MODE_FOUND"}: hard+=1
        elif a&{"left_geofence","new_region"}: soft+=1
    return hard,soft
rng=random.Random(7); N=300
print("\n== matriks lengkap (hard=blok/kunci, soft=alert+konfirmasi) ==")
print(f"{'skenario':>22} {'hard':>6} {'soft':>6}")
for s,lost in [("normal",False),("breach_abroad",False),("stolen_moving",True),("tamper",False)]:
    h,so=run2(s,N,rng,lost); print(f"{s:>22} {h:>5}/{N} {so:>5}/{N}".replace(f"{N}",str(N)))
