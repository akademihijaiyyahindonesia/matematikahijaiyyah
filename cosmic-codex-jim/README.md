# Cosmic Codex Jim (ج)

> Satu huruf yang **berisi mesin panjang-maksimum di dua lapangan berbeda** —
> dan satu-satunya di antara 28.

Ini bukan penafsiran atas huruf ج. Ini catatan pengukuran: apa yang terjadi
kalau muka 5×5 sebuah huruf dibaca sebagai peta linier dan diiterasikan.

```
GF(2)   maksimum 2⁵−1 = 31       tercapai: ج  خ
GF(3)   maksimum 3⁵−1 = 242      tercapai: ب
GF(5)   maksimum 5⁵−1 = 3124     tercapai: ج   ← sendirian
GF(7)   maksimum 7⁵−1 = 16806    tercapai: —   (terbaik 8403, tepat separuh)
```

**Jim satu-satunya yang muncul dua kali.** Kha primitif hanya di GF(2); Ba hanya
di GF(3). Tidak ada huruf lain yang primitif di lebih dari satu lapangan.

---

## Kenapa "codex", bukan "simbol"

Muka Jim adalah 5×5 = 25 sel, dan keadaan spons juga 25 lajur. Huruf itu **satu
muka kubus** — harfiah, bukan kiasan. Dan muka itu, atas GF(2), adalah **LFSR
panjang-maksimum dalam bentuk matriks**: konstruksi baku untuk pencacah dan
pembangkit aliran bit.

Jadi ج tidak *melambangkan* sebuah mesin. **Ia sebuah mesin.**

| | |
|---|---|
| indeks | 4 |
| opcode H-ISA | `0xE4` |
| Θ̂ | 3 → **270°** |
| ρ | 3 (U = 0 — tak ada lengkung yang menjelaskan belokannya) |
| muka | 8 dari 25 sel terisi |
| nilai jummal | 3 |

---

## Isi folder

| Berkas | Isi |
|---|---|
| [`MACHINE.md`](MACHINE.md) | Mesin di dalam huruf: periode per lapangan, primitivitas, dan titik sebagai tap |
| [`WAVE.md`](WAVE.md) | Apa yang dipancarkannya: m-sequence, ketiga postulat Golomb, frekuensi |
| [`LIMITS.md`](LIMITS.md) | Apa yang Jim **bukan** — tiga bacaan yang gagal terukur |

Angka di ketiganya diikat oleh
[`tests/test_integrity/test_cosmic_codex_jim.py`](../tests/test_integrity/test_cosmic_codex_jim.py),
dan mesin serta gelombangnya oleh
[`test_letter_machines.py`](../tests/test_integrity/test_letter_machines.py).

---

## Peringatan yang harus dibaca lebih dulu

Folder ini mudah disalahbaca sebagai klaim tentang keistimewaan huruf ج. Ia
bukan.

**Yang terukur**: muka 5×5 yang dibangun dari vektor 18 komponen Jim, dibaca
sebagai peta linier atas lapangan hingga, punya orde maksimum di GF(2) dan
GF(5). Itu fakta tentang satu matriks tertentu.

**Yang tidak terukur, dan tidak diklaim**: bahwa ini berlaku untuk rasm lain,
untuk kuantisasi selain Q₉₀, atau bahwa ia punya arti di luar aritmetika.
Ubah tata letak muka dan periodenya berubah — tiga sabotase di tesnya
membuktikan itu.
