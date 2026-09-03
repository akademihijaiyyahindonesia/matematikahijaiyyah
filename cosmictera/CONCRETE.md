# CosmicTera — konkret, lengkap, dengan asal‑usul tiap angka

Tidak ada angka di dokumen ini yang tidak punya sumber. Kolom **asal** menyebut
di mana ia dihasilkan; kalau ia hasil pengukuran, ia bisa dijalankan ulang.

---

## 1. Satu aliran, dari bit sampai segel

Jejak nyata dari `rtl/tb/tb_hijaiyyah_kabah_top.v` — **3.069 bit mentah pada
offset sembarang**:

```
3.069 bit mentah
   │
   ├─ penemuan fase          histogram indeks koinsidensi 256 bin
   │                         (perangkat lunak, sekali per aliran)
   ▼
 383 byte                    8 clock/byte  →  3.064 clock
   │
   ├─ gerbang jamrah         1 huruf digerbangi
   ├─ pencacah node          5 jendela diklasifikasi
   ▼
  47 lajur diserap
   │
   ▼
   2 permutasi               622 clock TERTAHAN  =  2 × 310  tepat
   │                         112 denyut impulser  (2 × 56)
   ▼
keadaan akhir                cocok persis dengan yang dihitung cube.py
   │
   ▼
lapis 3                      HMAC‑SHA256 — perangkat lunak, bukan RTL
```

**Total: 3.698 clock untuk 383 byte = 9,66 clock/byte.**

### Mengapa 9,66 dan bukan 10,42

```
deserialisasi   383 × 8            = 3.064 clock
tertahan        2 permutasi × 310  =   622 clock
                                     ─────
                                     3.686  vs 3.698 teramati
```

383 byte adalah **2,99 blok rate**, jadi hanya dua permutasi menyala. Secara
asimptotik biayanya `8 + 310/128 = 10,42` clock/byte. Jejak pendek ini sedikit
lebih murah per byte justru karena itu.

**Dan 622 = 2 × 310 tepat adalah buktinya**: permutasi menghentikan deserialiser
sepenuhnya, tidak bersembunyi di baliknya.

---

## 2. Biaya, per tahap

| Tahap | clock/byte | MB/s @ 27 MHz | Peran |
|---|---:|---:|---|
| Triase (gerbang + pencacah) | 1,00 | 27,00 | **gratis** — selesai sebelum byte berikutnya dirakit |
| Spons SLICE=25 | 2,42 | 11,15 | 310 clock per 128 byte |
| **Deserialiser** | **8,00** | **3,38** | **← bottleneck**, 3,3× biaya spons |
| **Sistem terbangun** | **10,42** | **2,59** | 8,00 + 2,42; biayanya berjumlah |

> **Ini pernah salah 4×.** 11,15 MB/s dikutip sebagai laju sistem di
> `kabah.py`, dua header RTL, dan empat halaman terbit. Itu laju **spons saja**,
> disuap satu byte per clock. Lihat R5 di [`RULES.md`](RULES.md).

### Per terabyte @ 27 MHz

| | jam |
|---|---:|
| Triase semuanya | 10,3 |
| Spons saja *(byte‑paralel — tidak pernah dibangun)* | 24,9 |
| Deserialiser saja | 82,3 |
| **Sistem terbangun** | **107,2** |

### Akibatnya bagi argumen pelapisan

Triase **gratis** karena tersembunyi di balik deserialiser. Tapi justru karena
itu, melewatkan spons hanya menghemat 2,42‑nya:

```
triase‑semua‑spons‑nol   8,00 clock/byte
spons semuanya          10,42 clock/byte
                         ────────────────
penghematan                      1,30×      bukan 2,42×
```

Ambang break‑even 58,7% yang pernah diturunkan menggambarkan mesin
byte‑paralel yang **tidak pernah dibangun**.

**Triase berhak ada karena apa yang ia temukan, bukan karena apa yang ia
hemat** — dan itu memang selalu argumen yang benar.

---

## 3. Per terabit: mengapa impulser dihitung begitu

| | nilai |
|---|---:|
| 1 terabit | 10¹² bit = 1,25 × 10¹¹ byte |
| Permutasi | 976.562.500 |
| **Denyut impulser** | **54.687.500.000** (54,7 giga) |
| Clock | 1,30 tera |
| Waktu @ 27 MHz | 13,4 jam |

Denyut per terabit **sama** di ketiga konfigurasi (terbangun, +FIFO,
byte‑paralel), karena **data yang menentukannya, bukan detik**. Itulah satu
satunya satuan di mana biaya impulser konstan.

Dan pada 107 jam per terabyte, **"jalankan lagi" bukan lagi verifikasi.**
Determinisme harus struktural.

> **Node‑hertz terukur: 43,72 giga @ 27 MHz — bukan tera.** Untuk mencapai
> skala tera dibutuhkan 22,9× lipat: misalnya 23 salinan paralel, atau ASIC
> ~400 MHz yang memberi 0,65 tera. Ini **[AT]**, bukan hasil.

---

## 4. Silikon: Tang Nano 9K (GW1NR‑9)

Papan: **8.640 LUT4 / 6.693 FF**.

Diukur ulang dengan yosys 0.68, `synth -flatten` lalu `abc -lut 4`:

| SLICE_BYTES | LUT4 | % papan | FF | clock/permutasi |
|---:|---:|---:|---:|---:|
| 8 | 6.910 | 80,0% | 2.009 | 786 |
| 25 | **8.096** | **93,7%** | 2.007 | 310 |

Keduanya muat. Margin di SLICE=25 adalah **544 LUT4**.

> **Angka ini pernah basi.** Header mencatat 6.231 (72%) dan 7.426 (85%) dari
> commit `cd6a29c`. Commit berikutnya menjadikan gerbang benar‑benar
> menggerbang — `gate_mode`, `break_at`, `break_count`, backpressure
> `bits_ready` — dan sintesis tidak pernah dijalankan ulang. Biayanya **+670
> LUT4**, dan margin turun dari 15% ke 6%. Lihat R4.

**Pemetaan 4‑LUT generik, bukan laporan fitting vendor.** Kabah top belum bisa
di‑place‑and‑route: antarmukanya **1.665 bit port** melawan **276 IOB** papan,
jadi ia butuh wrapper yang menyempitkan antarmuka sebelum bisa ditempatkan sama
sekali. Fmax‑nya tetap **[EH]**.

### HCPU di Tang Nano 9K — ini sudah place‑and‑routed

Dan di sinilah Fmax berhenti jadi [EH]. Rantai penuh dijalankan 3 September 2026:
yosys 0.68 → nextpnr‑himbaechel 0.11.1 → gowin_pack, GW1NR‑LV9QN88PC6/I5.

| Sumber daya | Terpakai | Kapasitas | % |
|---|---:|---:|---:|
| LUT4 | 6.746 | 8.640 | **78%** |
| MUX2_LUT5 | 714 | 4.320 | 16% |
| ALU | 1.544 | 6.480 | 23% |
| DFF | 1.719 | 6.480 | 26% |
| BSRAM | 4 | 26 | 15% |
| IOB | 10 | 276 | 3% |

**Fmax 90,14 MHz** terhadap kristal papan 27 MHz — **margin 3,34×**. Setiap durasi
yang selama ini berskala terbalik terhadap angka tak dikenal sekarang bisa
dinyatakan, **untuk HCPU**.

`-nodsp` wajib, dan sebabnya packer bukan desain: `synth_gowin` menyimpulkan
`MULT9X9` dari perkalian di norma kuadrat `hcpu_codex_alu`, nextpnr menempatkannya
tanpa keluhan, lalu `gowin_pack` mati pada `KeyError: 'IRBY_IREG0BL_0'`. Versi
gowin_pack milik suite sendiri gagal identik, jadi bukan ketidakcocokan versi.

| | LUT4 | Fmax |
|---|---:|---:|
| dengan DSP | 4.550 (52%) | 82,33 MHz |
| `-nodsp` | 6.746 (78%) | **90,14 MHz** |

+2.196 LUT4 dan — tak disangka — **clock lebih cepat**: DSP‑nya ada di jalur kritis.

---

## 5. Parameter, dan dari mana dibacanya

| Parameter | Nilai | Sumber |
|---|---:|---|
| Lajur keadaan | 25 | `cube.STATE_LANES` |
| Bit per lajur | 64 | `cube.LANE_BITS` |
| Keadaan | 1600 bit | turunan |
| Cincin luar / inti | 16 / 9 lajur | `cube.OUTER_RING`, `cube.CORE` |
| Rate | 128 byte / 1024 bit | `cube.RATE`, `cube.RATE_BITS` |
| Kapasitas | 576 bit | `cube.CAPACITY_BITS` |
| Keamanan | 288 bit | `cube.SECURITY_BITS` |
| Ronde | 28 (7 CIRCUIT × 4 TAWAF) | `cube.CIRCUITS` |
| Polinomial | `0x12B` | `cube.POLYNOMIAL` |
| Konstanta afin | `0xE7` | `cube.AFFINE_C` |
| Generator | 2 | `cube.GENERATOR` |
| Orde ρ·π | 768 = 12 × 64 | terhitung |
| Marjin ronde | 27,4× di bawah periode | 768 / 28 |
| Deserialiser | 8 clock/byte | `kabah.DESERIAL_CLOCKS_PER_BYTE` |
| Lapis otoritatif | 3 | `kabah.AUTHORITATIVE_LAYER` |
| Opcode H‑ISA | 95 terdefinisi | `program.defined_opcodes()` |
| Opcode berencoding RTL | 73 | `OP_*` di `rtl/` |
| Instruksi huruf | 28 (0xE0–0xFB) | satu huruf, tanpa operand |
| Penyebab trap | 3 terdefinisi, 2 bersumber | `TRAP_CAUSES` di `hcpu_pkg.vh` |
| Pola sumber sistem | 12 | `program.SYSTEM_PATTERNS` |
| Produk build dikecualikan | 5 | `program.BUILD_PRODUCTS` |

---

## 6. Yang terbukti, dan yang tidak

### Terbukti

| Klaim | Label | Bagaimana |
|---|---|---|
| Lapis 3 mengautentikasi | VF | HMAC‑SHA256, kunci terikat segel |
| HKDF benar | VF | lolos vektor RFC 5869 |
| S‑box: DU 4, NL 112, 0 titik tetap | CC | ruang habis, 256 masukan |
| Logika S‑box ≡ tabel | CC | 256/256 identik |
| Program H‑ISA ≡ RTL | CC | gerbang jamrah cocok 256/256 byte |
| Keadaan RTL ≡ `cube.py` | CC | 3.069 bit ujung ke ujung |
| Pemisahan rate/capacity | DP | geometri, bukan pemeriksaan |
| Orde ρ·π = 768 | VF | terhitung |

### Tidak terbukti

| | Label | Kenapa |
|---|---|---|
| Spons tahan kriptanalisis | **EH** | terukur, belum dikriptanalisis |
| Fmax Kabah top | **EH** | 1.665 bit port vs 276 IOB — butuh wrapper sebelum bisa ditempatkan |
| ~~Fmax HCPU~~ | **CC** | **terukur 90,14 MHz**, margin 3,34× atas 27 MHz |
| FIFO akan memberi 8,00 clock/byte | **EH** | belum dibangun |
| Skala tera node‑hertz | **AT** | terukur 43,72 giga; butuh 22,9× |
| Kerahasiaan | — | **ditolak** — pakai AES‑256‑GCM |

---

## 7. Menjalankan ulang angkanya

```bash
# biaya dan bottleneck
python3 -c "import sys; sys.path.insert(0,'src')
from hijaiyyah.crypto.kabah import Kabah
t = Kabah.throughput()
print(t['bottleneck'], t['paths']['system_bit_serial']['hours'])"

# jejak ujung ke ujung (butuh iverilog)
iverilog -o /tmp/tb rtl/*.v rtl/tb/tb_hijaiyyah_kabah_top.v && vvp /tmp/tb

# sintesis (butuh yosys)
yosys -p "read_verilog rtl/hijaiyyah_*.v
          hierarchy -top hijaiyyah_kabah_top -chparam SLICE_BYTES 25
          synth -flatten -top hijaiyyah_kabah_top
          abc -lut 4
          stat"

# seluruh suite
python3 -m pytest -q
```
