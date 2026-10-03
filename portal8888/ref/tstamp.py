"""Timestamp precision for Portal 8888: what a 27 MHz counter really gives,
and why it must be disciplined for ISP correlation. The gap I missed:
CTR orders events; it does not TIME them, and ISP IP-rotation lookup needs time."""
import random, statistics
F = 27_000_000
print(f"Resolusi 1 tick @27MHz = {1e9/F:.1f} ns  (cukup halus)\n")
print("Tapi resolusi != akurasi. Kristal punya drift (ppm). Tanpa disiplin:")
print(f"{'drift(ppm)':>10} {'galat/jam':>12} {'galat/hari':>12}")
for ppm in (20,50,100):
    print(f"{ppm:>10} {ppm*3600:>9.0f} us {ppm*86400/1e6:>9.2f} s")
print("\nArtinya: counter bebas 50 ppm meleset ~0,18 s/jam, ~4,3 s/hari.")
print("ISP memutar IP; korelasi butuh akurasi < ~1 s. Jadi counter bebas GAGAL dalam hitungan jam.\n")
# simulate: free-running vs GPS-PPS-disciplined (re-sync each second)
def drift_sim(ppm, discipline_s, hours, rng):
    err=0.0; worst=0.0; t=0.0
    ppm_now=rng.gauss(ppm,ppm*0.3)
    for s in range(int(hours*3600)):
        err += ppm_now*1e-6                      # seconds of error added this second
        if discipline_s and (s % discipline_s)==0:
            err = rng.gauss(0, 1e-6)             # re-sync to PPS, ~us residual
            ppm_now=rng.gauss(ppm,ppm*0.3)
        worst=max(worst,abs(err))
    return worst
rng=random.Random(20261001)
print(f"{'skema':>34} {'galat maks (8 jam)':>20}")
print(f"{'counter bebas 50ppm':>34} {drift_sim(50,0,8,rng):>17.3f} s")
print(f"{'disiplin NTP tiap 60s':>34} {drift_sim(50,60,8,rng)*1000:>14.2f} ms")
print(f"{'disiplin GPS-PPS tiap 1s':>34} {drift_sim(50,1,8,rng)*1e6:>13.1f} us")
print("\nKesimpulan: field waktu WAJIB mencatat sumber & ketidakpastiannya,")
print("dan di-disiplinkan PPS. Tanpa itu cap waktu tidak sah sebagai bukti.")
