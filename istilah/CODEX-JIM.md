# Codex Jim: kosakata pengukuran

`cosmic-codex-jim/` **bukan bahasa pemrograman** dan bukan semantic memory. Ia
catatan pengukuran atas satu huruf, dan kosakatanya kosakata aljabar lapangan
hingga.

> **Peringatan yang ada di foldernya sendiri harus dibaca lebih dulu.**
> `LIMITS.md` mencatat **empat** bacaan yang gagal terukur. Nama-nama di bawah
> menyebut sifat yang nyata; sifat itu tidak membuat Jim "pusat" apa pun.

---

## Muka dan mesinnya

| istilah | arti | di mana |
|---|---|---|
| **muka** | vektor 18 komponen ditata 5×5; **tata letaknya menentukan mesinnya** | `MACHINE.md` §1 |
| **tap** | sadapan pada simpul; §5 berjudul *"Titiknya adalah tap-nya"* | `cosmic-codex-jim/MACHINE.md` |
| **orde matriks** | periode iterasi `M, M², M³, …` | `WAVE.md` |
| **periode kawat** | periode aliran bit keluarannya | `WAVE.md` |
| **ekor** | langkah sebelum barisan masuk periodenya | `MACHINE.md` §2 |
| **m-sequence** | barisan panjang-maksimum | `WAVE.md` |
| **postulat Golomb** | tiga syarat keacakan — **terpenuhi eksak** | `WAVE.md` |

> **Orde matriks bukan periode kawat.** `WAVE.md` memuat itu sebagai
> **koreksi** berjudul sendiri: keduanya sempat dikira satu hal.

---

## Yang terukur

```
GF(2)   maksimum 2⁵−1 = 31       tercapai:  ج  خ
GF(3)   maksimum 3⁵−1 = 242      tercapai:  ب
GF(5)   maksimum 5⁵−1 = 3124     tercapai:  ج      ← sendirian
GF(7)   maksimum 7⁵−1 = 16806    tercapai:  —      (terbaik 8403, tepat separuh)
```

**Jim satu-satunya yang muncul dua kali.** Kha primitif hanya di GF(2); Ba
hanya di GF(3). Itu sifatnya, dan itu saja.

---

## Empat bacaan yang gagal terukur

`LIMITS.md` menyimpannya, *"karena resep lebih berharga dengan kegagalannya
terlampir — dan karena ketiganya terdengar masuk akal sampai diukur"*:

| | bacaan | hasilnya |
|---|---|---|
| 1 | Jim pusat metrik | **peringkat 6 dari 28** sebagai medoid; **Kha** yang menang |
| 2 | memusatkan penyandian pada Jim | **12% lebih buruk** — 71% komponen sudah nol, dan nol titik asal alaminya |
| 3 | Jim pivot metrik | **peringkat 21 dari 28**; pivot baik justru yang ekstrem |
| 4 | Jim + Kha pasangan pilihan | gagal terukur |

| istilah | arti | di mana |
|---|---|---|
| **medoid** | huruf dengan jumlah jarak kuadrat terkecil ke 27 lainnya | `cosmic-codex-jim/LIMITS.md` |
| **pivot metrik** | huruf yang dipakai memangkas perhitungan jarak lewat ketaksamaan segitiga | `cosmic-codex-jim/LIMITS.md` |

**Yang benar ada di tingkat kelas, bukan huruf:** Θ̂=3 (270°) kelas paling
terpusat dari delapan, dan **Jim huruf pertamanya**. Itu posisi nyata, dan ia
bukan hal yang sama dengan menjadi pusat.

---

Dijangkarkan oleh `tests/test_integrity/test_node_counter.py` dan
`test_istilah.py`.
