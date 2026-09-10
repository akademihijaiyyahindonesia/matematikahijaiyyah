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

Didetak pada kristal 27 MHz papan Tang Nano 20K:

```
  27.000.000 / 31 = 870,97 kHz
```

Itu **gelombang terpanjang di seluruh abjad**. Bank osilatornya:

| periode | frekuensi | n | huruf |
|---:|---:|---:|---|
| 1 | **diam** | 22 | ا ب ت ث ح د ر س ش ص ض ط ظ ع ق ك ل م ن و هـ ي |
| 3 | 9,000 MHz | 4 | ذ ز غ ف |
| **31** | 0,871 MHz | 2 | **ج خ** |

**Dua puluh dua huruf tidak memancarkan apa pun** — bukan enam belas.
Pemisahan itulah yang membuat kedua yang maksimum berarti sesuatu.

### Koreksi: orde matriks bukan periode kawat

Versi sebelumnya menabulasikan **orde matriks** — periode M, M², M³… atas
GF(2) — lalu menyebutnya frekuensi yang dipancarkan. Untuk enam huruf itu
angka yang berbeda:

| orde | n | huruf |
|---:|---:|---|
| 1 | 16 | ا ت ث د ر س ش ص ض ع ق ك ن و هـ ي |
| 2 | 2 | ح ل |
| 3 | 7 | ذ ز ط ظ غ ف م |
| 4 | 1 | ب |
| **31** | 2 | **ج خ** |

Yang berbeda: **ب ح ط ظ ل م**. `ب` berorde 4 dan memancarkan `0000` —
matriksnya berputar, keluarannya konstan. `ح` dan `ل` berorde 2 dan
memancarkan `11`. `ط ظ م` berorde 3 dan memancarkan konstan.

Tiga besaran yang sempat terbaca sebagai satu:

| Besaran | Apa itu | Terlihat penerima |
|---|---|:--:|
| orde matriks | periode M, M², M³… | tidak |
| siklus keadaan | periode lintasan keadaan | tidak |
| **periode kawat** | periode fundamental bit yang keluar | **ya** |

Hanya yang ketiga boleh disebut frekuensi. Perhitungannya tidak salah —
`test_letter_machines.py` menghitung orde matriks dengan benar. Yang salah
adalah kalimat yang menempelkan orde itu pada apa yang **dipancarkan**.

Tabel di halaman ini sekarang **diturunkan, bukan disalin**:
`hijaiyyah.receiver.tabulate` menghasilkannya dari eksomatriks dan
`test_wave_md_table_is_derived_not_transcribed` menggagalkan suite kalau
halaman ini menyimpang lagi. Untuk mencetak ulang:

```bash
PYTHONPATH=src python3 -m hijaiyyah.receiver.tabulate
```

### Fase memisahkan yang frekuensi tidak bisa

Keempat huruf 9 MHz tidak identik di kawat:

```
  ذ ز ف  ->  110
  غ      ->  101
```

`101` adalah `110` yang bergeser satu — nada yang sama, fase berbeda.
Penerima yang hanya mengukur frekuensi mengembalikan keempatnya; yang
mengukur fase memisahkan `غ`. Itu sebabnya `receiver/identify.py` menyimpan
motifnya, bukan hanya periodenya.

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
