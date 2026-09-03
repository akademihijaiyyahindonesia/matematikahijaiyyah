# Lompatan cacahan

Dua hal bekerja di sumbu berbeda, jadi keduanya **berlipat**, bukan
berjumlah.

```
  derajat memilih panel     28 kandidat →  4,50     6,2×
  panelnya jarang           125 MAC     →  9,8     12,7×
                                                   ─────
  bersama                   3.500       →   44      79×
```

Satu menentukan **panel mana** yang disentuh; satu lagi **berapa biaya** tiap
panel yang tersentuh.

---

## 1. Derajat sebagai kunci panel

Θ̂ terkuantisasi Q₉₀, jadi ia mencacah seperempat putaran. **Ia kunci pemilah
terbaik dari seluruh 18 komponen**, dan tidak dekat:

| kunci | kelas | kandidat | percepatan |
|---|---:|---:|---:|
| **Θ̂** | 8 | 4,50 | **6,22×** |
| A_N | 4 | 10,07 | 2,78× |
| A_Q | 4 | 11,21 | 2,50× |
| … | | | |
| Nb | 2 | 26,07 | 1,07× |

Ia menang karena membawa **entropi terbanyak**: 2,77 bit dari 4,81 yang
dibutuhkan untuk menamai 28 huruf unik.

Menambah A_N mencapai **15,1×**, dan penelusuran serakah dari Θ̂ menamai setiap
huruf unik dengan **enam komponen dari delapan belas**:

```
  Θ̂ → +A_N → +A_K → +Q_s → +N_a → +K_s     injektif
```

## 2. Panelnya jarang dan berperingkat rendah sekaligus

Exomatrix 5×5 = 25 sel, dan `STATE_LANES` spons juga 25: **huruf adalah satu
muka kubus**, harfiah.

```
  sel nol           74%
  rank rata-rata    3,71 dari 5
  sel tak-nol       6,6 rata-rata (min 2, maks 10)
```

Perkalian padat 5×5 selalu 125 kali-tambah. Atas seluruh 784 pasang huruf,
perkalian jarangnya **rata-rata 9,8**, terburuk 22 — **12,7× tipikal, 5,7×
bahkan di kasus terburuk.**

Metrik agregat menumpang kejarangan yang sama: `grand_sum` atas 25 sel adalah
6,6 suku tak-nol, **3,8×**.

---

## Derajat juga sebuah fungsi

```
  Θ̂ = U + ρ        U = Qₓ + Qₛ + Qₐ + 4·Q_c
```

**Angka 4 itu Umlaufsatz** — lengkung tertutup berputar penuh 360°, jadi satu
loop bernilai tepat empat perempat. هـ punya dua loop, U = 8, Θ̂ = 8 = 720°,
ρ = 0.

**Dan Qp sengaja tidak ada di U.** Kelengkungan lengkung *primer* tidak
diramalkan, jadi ia jatuh ke residu. Terukur: `ρ > 0 ⟺ Qp > 0 atau Ka > 0`,
berlaku 28/28 dan bertahan melewati penjumlahan. Kaf melengkapinya — tanpa
lengkung primer, tapi `Ka = 1`, sudut siku, dan ρ = 2.

Itu **[EH]**, dan tetap di luar guard: G1–G3 definisional, ini klaim tentang
bentuk apa yang kebetulan ada di abjad.

**630° tidak ada** di huruf mana pun. Derajatnya 0, 90, 180, 270, 360, 450,
540, 720. Itu fakta tentang 28 bentuk ini, **bukan kendala** — vektor sah
ber-Θ̂ = 7 dikonstruksikan di dalam tesnya supaya celah itu tidak disalahartikan
sebagai hukum.
