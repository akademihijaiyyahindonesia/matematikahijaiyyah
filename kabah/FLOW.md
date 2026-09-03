# Cara kerjanya

Perjalanan satu aliran, dari kabel sampai rekaman tersegel. Setiap angka di
sini terukur dari jejak `tb_hijaiyyah_kabah_top` — **3.069 bit mentah pada
offset sembarang**.

```
   aliran bit mentah                        3.069 bit
        │
        │   ① penemuan fase — perangkat lunak, sekali per aliran
        │      histogram indeks koinsidensi 256 bin
        ▼
   ② deserialisasi                          8 clock/byte → 383 byte
        │                                    ← BOTTLENECK, 3,3× biaya spons
        ├─→ ③ gerbang jamrah                1 huruf digerbangi
        ├─→ ④ pencacah node                 5 jendela diklasifikasi
        ▼
   ⑤ perakitan lajur                        47 lajur cincin luar
        │
        ▼
   ⑥ permutasi                              2 × 310 clock = 622 TERTAHAN
        │                                    112 denyut impulser
        ▼
   keadaan akhir                             cocok persis dengan cube.py
        │
        │   ⑦ lapis 3 — perangkat lunak, BUKAN RTL
        ▼
   HMAC-SHA256 atas kunci terikat segel      ← baru di sini ia terautentikasi
```

**Total: 3.698 clock untuk 383 byte = 9,66 clock/byte.**

---

## Yang penting di tiap langkah

**① Fase ditemukan, bukan diasumsikan.** Aliran datang tanpa batas byte.
Indeks koinsidensi adalah statistik gabungan — ia melihat batas yang tak bisa
dilihat statistik marginal. Sekali per aliran, bukan per clock.

**② Deserialiser adalah bottleneck-nya**, dan ini pernah salah dikutip selama
berpuluh commit. Spons berbiaya 2,42 clock/byte; deserialiser **8,00**. Laju
11,15 MB/s adalah laju **spons saja disuap byte-paralel** — sistemnya
**2,59 MB/s**.

**③④ Triase gratis.** Gerbang dan pencacah berbiaya 1 clock/byte, dan byte
berikutnya baru tiba 8 clock kemudian. Mereka selesai jauh sebelumnya.

Tapi justru karena gratis, **melewatkan spons hanya menghemat 2,42-nya** —
triase-semua-spons-nol cuma **1,30×** lebih cepat, bukan 2,42× yang disiratkan
suapan byte-paralel.

> **Triase berhak ada karena apa yang ia temukan, bukan karena apa yang ia
> hemat.**

**⑥ Permutasi tidak bersembunyi.** Ia menegaskan backpressure dan menghentikan
deserialiser selama 310 clock penuh, jadi biayanya **berjumlah**: 8,00 + 2,42 =
10,42 clock/byte.

Buktinya di jejak: **622 clock tertahan = tepat 2 × 310** — dua permutasi yang
menyala, masing-masing menghentikan penuh.

FIFO akan memulihkan sebagian besar — 310 clock muat di dalam 1.024 clock
kedatangan 128 byte berikutnya. **Belum dibangun, belum diukur — [EH].**

**⑦ Yang keluar dari perangkat keras belum terautentikasi.** Tak ada core
SHA-256 di RTL. Lapis 3 adalah perangkat lunak, dan lapis 3 adalah seluruh
keamanannya.

---

## Rotasi menuju inti

Masukan **tidak pernah** menyentuh 9 lajur inti. Rotasi yang membawanya ke
sana — **satu ronde untuk mencapai, tiga untuk menjenuhkan**, 290 dari 576 bit.

Pemisahan itulah capacity-nya. Bukan aturan yang ditegakkan; **geometri**.

Dan π terurai jadi siklus `[12, 12, 1]` — **lajur 0 tetap**, dan di situlah
konstanta ronde masuk. Orde ρ·π bersama **768 = 12 × 64**, jadi 28 ronde
berjalan **27,4× di bawah periodenya**.

---

## Per terabyte, kalau perlu angkanya

| | jam @ 27 MHz |
|---|---:|
| Triase semuanya *(gratis, tersembunyi)* | 10,3 |
| Spons saja *(byte-paralel — tak pernah dibangun)* | 24,9 |
| Deserialiser saja | 82,3 |
| **Sistem terbangun** | **107,2** |

Dan **pada 107 jam, "jalankan lagi" bukan lagi verifikasi.** Determinisme harus
struktural — itulah sebabnya rotasi kanonik dan segel ada.
