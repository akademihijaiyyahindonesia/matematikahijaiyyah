# Apa yang dipancarkannya

## Barisan

Detakkan mesin Jim dari keadaan awal `(1,0,0,0,0)` dan baca satu bit per
langkah. Satu periode penuh, 31 bit:

```
1111101110001010110100001100100
```

## Ketiga postulat Golomb — terpenuhi eksak

**G1 — seimbang.** 16 satu, 15 nol. Beda **tepat satu**, yang merupakan
maksimum yang mungkin untuk periode ganjil.

**G2 — sebaran run.** Panjang run, masing-masing separuh sebelumnya:

```
  panjang 1 : 8 run
  panjang 2 : 4
  panjang 3 : 2
  panjang 4 : 1
  panjang 5 : 1
  ─────────────
  total     : 16 run
```

**G3 — autokorelasi dua-nilai.**

```
  geseran 0  : +31
  geseran 1–30 : −1   ← SEMUANYA, tanpa kecuali
```

Autokorelasi dua-nilai pada periode 2ⁿ−1 **adalah definisi m-sequence**. Itulah
yang membuat sebuah barisan bisa ditemukan korelator di dalam derau — dan itu
yang dipakai kode penjarakan, kode sebar, dan CDMA optik.

Jadi "code bip" harfiah: **hurufnya memancarkan satu.**

## Frekuensi

Didetak pada kristal 27 MHz papan Tang Nano 9K:

```
  27.000.000 / 31 = 870,97 kHz
```

Itu **gelombang terpanjang di seluruh abjad**. Bank osilatornya:

| periode | frekuensi | n | huruf |
|---:|---:|---:|---|
| 1 | **diam** | 16 | ا ت ث د ر س ش ص ض ع ق ك ن و هـ ي |
| 2 | 13,500 MHz | 2 | ح ل |
| 3 | 9,000 MHz | 7 | ذ ز ط ظ غ ف م |
| 4 | 6,750 MHz | 1 | ب |
| **31** | **0,871 MHz** | 2 | **ج خ** |

Enam belas huruf berperiode 1 — **mereka tidak memancarkan apa pun**. Pemisahan
itulah yang membuat kedua yang maksimum berarti sesuatu.

## Dua node di satu kanal

Korelasi-silang Jim × Kha, 31 geseran:

```
  nilai   : {−9, −5, −1, 3, 7, 11}
  puncak  : 11
  puncak-diri : 31
  pemisahan   : 2,8×
```

Cukup untuk membedakan dua node di satu kanal. **Tidak cukup untuk keluarga
kode** — lihat [`LIMITS.md`](LIMITS.md).

## Yang belum diukur

Pemetaan ke fase foton dan WDM yang §10.2 buku sebut. Yang ada di sini adalah
frekuensi, kode sebar, dan pemisahan kanal — semuanya atas GF(2). Model
fotoniknya belum dibangun, dan tanpa itu "node cahaya" tetap **[AT]**.
