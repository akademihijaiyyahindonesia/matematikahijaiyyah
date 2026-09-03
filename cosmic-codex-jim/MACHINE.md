# Mesin di dalam huruf

## 1. Muka

Vektor 18 komponen Jim ditata jadi matriks 5×5 oleh `build_exomatrix`. Tata
letaknya bukan tampilan — ia **menentukan mesinnya**, dan mengubahnya mengubah
periodenya.

```
        Θ̂    U    ρ    0    0        3   0   3   0   0
       Na   Nb   Nd    0  A_N        0   1   0   0   1
       Kp   Kx   Ks   Ka   Kc   →    0   1   0   0   0
       Qp   Qx   Qs   Qa   Qc        1   0   0   0   0
       H*    0    0  A_K  A_Q        0   0   0   1   1
```

8 dari 25 sel terisi. 5×5 = 25 = `STATE_LANES` spons: **satu muka kubus**.

## 2. Iterasi

Baca muka itu sebagai peta linier atas lapangan hingga, lalu kalikan dengan
dirinya berulang: `M, M², M³, …`. Setiap huruf mengendap ke periode tertentu.

```
  lapangan   ekor   periode      maksimum yang mungkin
  GF(2)         1        31      2⁵−1 = 31        ← TERCAPAI
  GF(3)         3         3      3⁵−1 = 242
  mod 4         1        62      (= 2 × 31)
  GF(5)         1      3124      5⁵−1 = 3124      ← TERCAPAI
  GF(7)         1      2400      7⁵−1 = 16806
  mod 8         1       124      (= 4 × 31)
  mod 16        1       248      (= 8 × 31)
  mod 256       1      3968      (= 128 × 31)
```

**Ekor 1** berarti matriksnya sudah berada di dalam siklusnya sendiri — ia
invertibel, bukan sekadar berulang setelah transien.

Dan perhatikan kolom modulus pangkat dua: 31, 62, 124, 248, 3968 — semuanya
`31 × 2ᵏ`. Struktur GF(2)-nya terangkat utuh.

## 3. Primitivitas — pernyataan yang tepat

Periode 31 bukan sekadar besar. **31 = 2⁵−1 adalah orde terbesar yang bisa
dimiliki elemen mana pun di GL(5,2)** — siklus Singer, yakni GF(32)*.

Dan pernyataan yang tepat bukan tentang periodenya, melainkan tentang
polinomialnya:

```
  p(x) = x⁵ + x⁴ + x³ + x² + 1     ← primitif atas GF(2)
```

**Matriks atas GF(2) yang polinomial karakteristiknya primitif ADALAH LFSR
panjang-maksimum dalam bentuk matriks.** Itu konstruksi baku untuk pencacah dan
pembangkit aliran bit. Dari enam polinomial primitif derajat 5 yang ada, dua
muncul di abjad ini sebagai huruf: Jim dan Kha.

## 4. Yang membuat Jim tunggal

| lapangan | maksimum | tercapai oleh |
|---|---:|---|
| GF(2) | 31 | **ج** , خ |
| GF(3) | 242 | ب |
| GF(5) | 3124 | **ج** |
| GF(7) | 16806 | — (terbaik 8403, tepat separuh) |

**Jim satu-satunya yang muncul dua kali.** Kha primitif hanya di GF(2), Ba
hanya di GF(3), dan tidak ada huruf yang primitif di GF(7) sama sekali.

## 5. Titiknya adalah tap-nya

ج ح خ berbagi satu kerangka dan berbeda hanya pada titiknya.

```
  ح Ha    tanpa titik           periode  2
  ج Jim   satu titik, Nb        periode 31     ← maksimum
  خ Kha   satu titik, Na        periode 31     ← maksimum
```

Jim berbeda dari Ha di **satu komponen**: `Nb` naik 0 → 1, dan `A_N` mengikuti
karena G1. Periodenya melompat **2 → 31**.

Uji kausalnya: ambil Ha, pasang satu titik di tiap slot.

| slot | dipakai abjad | periode dari Ha |
|---|---|---:|
| Na (Kha) | 12 huruf | **31** |
| **Nb (Jim)** | **1 huruf — Jim saja** | **31** |
| Nd | 2 huruf | 21 |

**`Nb` punya satu penghuni di seluruh abjad.** "Titik satu di tengah" bukan
gambaran bentuk — ia slot beruang satu, dan slot itu maksimum.

Dan **titik kedua merusaknya**: menggandakan satu slot mengembalikan periode ke
2; dua tap mana pun jatuh di bawah 31.

## 6. Sebagai instruksi

```
  ج   →   0xE4000000      HREG[0] ← HREG[0] + v(Jim)
```

Satu karakter, field operand nol. Opcode `0xE4` di rentang huruf `0xE0–0xFB`.
Di RTL, indeks ROM-nya diturunkan dari offset opcode-nya sendiri, dan keluaran
ROM masuk sebagai operand kedua codex ALU.
