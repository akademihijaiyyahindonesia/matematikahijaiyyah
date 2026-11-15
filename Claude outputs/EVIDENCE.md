# Portal 8888 — Bukti Simulasi

Semua dijalankan di toolchain oss-cad-suite (Icarus 14, Yosys 0.69+158),
**terhadap mesin HMAC-SHA256 yang identik byte demi byte dengan repo** (commit
`4bff781`, 207/207 di papan):

```
hijaiyyah_hmac.v          6b7ede607f32b7582a96d98e82ef1e6b7ac18c74caba4d4b066d998e48086cbc
hijaiyyah_sha256_core.v   289e5eac4cb6556e7fd31db812943c29a621ed932a4170f21221ea04a67c67d6
hijaiyyah_sha256_stream.v f767fee5cb85170bb223894f41027404cf5c6aeda9b00cb7bb12ddd8892bdd6a
```

## 1. Cap-waktu GPS-PPS (`tb_timestamp`)

```
disc sec 0..5: sec naik 1..6, tick reset 0 tiap PPS, locked=1, ppm_est=50, warn=0
holdover 3s  : locked=0 holdover=1  drift=150000 ns  (= 50 ppm x 3 s)
RESULT       : ppm_est=50 (drift kristal sebenarnya 50), baca terkunci tepat 1 tick
```

- Disiplin PPS terkunci, `sec`/`tick` melacak UTC.
- Saat PPS hilang: `holdover`=1, dan error tumbuh 150000 ns persis = 50 ppm × 3 s.
- Resolusi 1 tick @27 MHz = **37 ns**; terkunci GPS ⇒ akurasi di bawah ~100 ns.

## 2. jim_sync + jim_index (`tb_jim`)

```
jim_sync : 49.604 bit, 158 hit, 0 salah (penanda 31-bit, ambang 2)
jim_index: 3.124 langkah, 0 salah, kembali ke awal tepat di langkah 3124
```

## 3. ingress_parse (`tb_ingress`)

```
ingress_parse: 3.000 frame, 3.000 tepat, 0 salah
  (Ethernet/VLAN/IPv4/IPv6/TCP/UDP/ARP/ICMP/terpotong/ekstensi-v6)
sabotase 1 offset VLAN -> 327 salah (penjaga aktif)
```

## 4. FSM Portal satu putaran, byte-exact (`tb_portal8888`)

```
portal8888: round=1  TAG_A..D OK  ROOT OK  (0 mismatch vs ref/portal_ref.py)
```

## 5. SISTEM penuh: GPS-PPS -> cap-waktu -> segel (`tb_portal8888_system`)

Satu putaran disegel dengan timestamp **hidup** dari jam GPS; `portal_sys_check.py`
memverifikasi tiap byte dengan hashlib/hmac Python.

```
GPS-PPS: PPS 1 sec=1; PPS 2 sec=2; locked=1 ppm_est=50 holdover=0
seal (tiap sudut 64 byte, HMAC bergiliran):
  corner 0: T=2.250005000s (tick 50001)  527 clocks  tag=ef76d4ae..
  corner 1: T=2.252645000s (tick 50529)  527 clocks  tag=604ffee3..
  corner 2: T=2.255285000s (tick 51057)  527 clocks  tag=62e0f98a..
  corner 3: T=2.257925000s (tick 51585) 1187 clocks  tag=b152aa08..
  portal  : round=1  total 2773 clocks   root=ce46f59d..
verifikasi Python: corner 0..3 tag OK, portal ROOT OK
RESULT: ALL BYTE-EXACT (RTL menyegel dengan timestamp GPS hidup)
```

**Detail penting:** sub-detik tiap sudut berbeda (50001, 50529, 51057, 51585)
karena jam GPS berjalan terus selama HMAC bekerja — bukti bahwa cap-waktu di
dalam segel adalah waktu nyata saat sinyal tiba, bukan nilai tetap. Inilah yang
dibutuhkan korelasi IP+waktu di ISP.

VCD seluruh sinyal per clock (`portal8888_system.vcd`, ~75 MB) dibangkitkan saat
dijalankan; tidak di-commit karena ukurannya.

## 6. Kampanye serangan (model perangkat lunak, `ref/`)

```
rantai 4 sudut + portal + jangkar: 16 kelas x 300 percobaan
  ubah/sisip/hapus/replay/tukar/rollback  -> 300/300 terdeteksi
  (hapus-ekor & rollback: 300/300 DENGAN jangkar, 0/300 tanpa jangkar)
  log bersih: 0/300 positif palsu
bukti asal sinyal (ingress): 9 kelas x 300
  ubah IP/port/MAC, pindah port fisik, ubah waktu, tukar bukti,
  hapus semua catatan satu IP, sisip tanpa kunci  -> 300/300
  IP dipalsukan di asal (UDP): tercatat apa adanya (batas yang jujur)
```

## 7. Sintesis (GW2A-18C, `synth_gowin -nodsp`)

```
hijaiyyah_timestamp : ~490 LUT + 762 ALU  (ppm_est kali-bagi; target optimasi)
jim_sync            : 166 LUT, 41 FF
jim_index           : 32 LUT, 15 FF (tabel mod-5, bukan pembagi)
ingress_parse       : ~540 LUT, ~940 FF
hijaiyyah_portal8888+HMAC: ~8.475 LUT (41%), ~11.600 DFF (75%)
```

DFF 75% berat untuk Tang Nano; ingress jaringan + FSM penuh sebaiknya di KV260.

## Status

```
model software + kampanye        VALIDATED
ingress_parse                    VALIDATED sim (3000/3000)
cap-waktu GPS-PPS                VALIDATED sim
jim_sync / jim_index             VALIDATED sim
FSM 4 sudut + portal + jangkar   VALIDATED sim (byte-exact)
sistem GPS->cap-waktu->segel     VALIDATED sim (byte-exact, timestamp hidup)
PnR repo + integrasi gerbang     BELUM
Ed25519 otorisasi                BELUM (desain)
papan                            tidak diuji (sesuai arahan; pindah ke KV260)
```
