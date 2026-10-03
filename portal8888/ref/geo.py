"""Constraint-based geolocation: what latency can and cannot pin down.
Physics: light in fibre ~2.0e8 m/s. RTT constrains distance (path >= straight line),
so one measurement = a DISK the target lies within, not a point. N landmarks = intersection."""
import math, random, statistics
C_FIBRE = 2.0e8                     # m/s, ~0.67c
def rtt_ms(dist_km, circuit, jitter_ms, proc_ms, rng):
    # real path is longer than straight line (circuitousness), plus router/queue/processing + jitter
    path_m = dist_km*1000*circuit
    base = 2*path_m/C_FIBRE*1000     # ms round trip
    return base + proc_ms + abs(rng.gauss(0, jitter_ms))
def max_radius_km(rtt, jitter_ms, proc_ms):
    # the honest upper-bound radius a landmark allows (assume best-case straight fibre to not exclude truth)
    usable = max(0.0, rtt - proc_ms - 2*jitter_ms)
    return (usable/1000)*C_FIBRE/2/1000   # km, straight-line equivalent
def locate(target, landmarks, circuit, jitter_ms, proc_ms, rng, grid=160, span=3000):
    # grid search: keep cells consistent with every landmark's disk; report centroid + spread
    radii = []
    for (lx,ly) in landmarks:
        d = math.dist(target,(lx,ly))
        r = rtt_ms(d, circuit, jitter_ms, proc_ms, rng)
        radii.append(((lx,ly), max_radius_km(r, jitter_ms, proc_ms)))
    pts=[]
    for i in range(grid):
        for j in range(grid):
            x=target[0]+(i/(grid-1)-0.5)*span; y=target[1]+(j/(grid-1)-0.5)*span
            if all(math.dist((x,y),c)<=R for c,R in radii): pts.append((x,y))
    if not pts: return None
    cx=statistics.mean(p[0] for p in pts); cy=statistics.mean(p[1] for p in pts)
    err=math.dist((cx,cy),target)
    area=len(pts)*(span/grid)**2
    region_r=math.sqrt(area/math.pi)
    return err, region_r, len(pts)
def trial(nL, jitter_ms, rng, circuit=1.6, proc_ms=2.0, reps=120):
    errs=[]; regs=[]
    for _ in range(reps):
        target=(rng.uniform(-500,500), rng.uniform(-500,500))
        lms=[(rng.uniform(-1500,1500),rng.uniform(-1500,1500)) for _ in range(nL)]
        r=locate(target,lms,circuit,jitter_ms,proc_ms,rng)
        if r: errs.append(r[0]); regs.append(r[1])
    return (statistics.median(errs), statistics.median(regs)) if errs else (None,None)
print("Latensi -> lokasi. circuitousness 1.6x, proc 2ms. Error = jarak pusat dugaan ke target;")
print("Region = radius wilayah yang konsisten (ketidakpastian). Semua dalam KM.\n")
print(f"{'landmark':>8} {'jitter':>8} {'error(km)':>12} {'region(km)':>12}")
rng=random.Random(20261001)
for nL in (1,3,5,10):
    for jit in (0.1,1.0):
        e,r=trial(nL,jit,rng)
        print(f"{nL:>8} {jit:>6}ms {e:>12.1f} {r:>12.1f}")
print("\nBatas fisika: 1 ms RTT = %.0f km radius maksimum (satu arah, serat lurus)."%((1/1000)*C_FIBRE/2/1000))
print("Jitter 0,1 ms saja = ±%.1f km. Satu node = cincin, bukan titik."%((0.1/1000)*C_FIBRE/2/1000))
