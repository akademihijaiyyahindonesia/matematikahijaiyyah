# Seberapa kuat guard-nya

"Memvalidasi diri sendiri" tak bernilai apa-apa kalau sepertiga vektornya tak
terjaga. Jadi ini diukur **per komponen**, bukan dinyatakan.

```
  N, K, Q  (13 komponen)   1.165 korupsi   100% tertangkap
  agregat  (3)               323 korupsi   100% tertangkap
  Θ̂        (1)               133 korupsi    11%
  H*       (1)                85 korupsi     0%
```

Dua celah, dan **keduanya bukan hal yang sama.**

---

## H* bukan celah — ia di luar domainnya

**Koreksi.** Halaman ini sebelumnya menyebut H* "memang celah". Buku
mendefinisikannya, ID.1.3 hal. 74:

```
  H* : ℋ₂₈ → {0,1}        H*(ك) = 1,   H*(h) = 0  ∀h ≠ ك
```

**H\* adalah fungsi indikator untuk fitur NON-GEOMETRIS** — marker hamzah,
berlabel [DP]. Tak ada kendala geometris yang bisa mengikatnya **karena ia
bukan geometri.** Berada di luar domain guard bukan hal yang sama dengan
menjadi lubang di dalamnya.

Dan itu menjelaskan relasi `H* = Ka` yang dikembalikan ruang nol: Kaf satu-
satunya huruf dengan `Ka > 0`, jadi kedua kolom indikator itu berimpit.

Sisa bagian ini tetap berlaku — hanya kerangkanya yang salah.

## Yang terukur tentang H*

Indeks 17 tidak muncul di guard mana pun — `vec[17]` **nol kemunculan** di
`guards.py`. Setiap korupsinya lolos.

Dan relasinya ada: ruang nol mengembalikan `H* = Ka`, eksak di 28/28, tertutup
di bawah penjumlahan, dan menaikkan deteksi dari **88,1% ke 93,1%**.

**Ia ditambahkan sebagai G5, lalu dicabut.**

Sebabnya: G1–G3 **definisional** — A_N *adalah* jumlahnya, menurut konstruksi.
`H* = Ka` **empiris dengan satu titik data**: 27 huruf keduanya nol, satu huruf
(Kaf) keduanya satu. Itu seluruh buktinya.

Dan kini sebabnya bisa dilacak sampai ke akar: **`Ka` dan `H*` sama-sama
penanda, dan keduanya menandai huruf yang sama.** Dua puluh tujuh baris cocok
karena sama-sama nol; baris ke-28 cocok karena itu huruf yang sama. **Satu
pengamatan, bukan dua puluh delapan.**

Ruang nol tidak bisa membedakan hukum dari kebetulan — ia mengembalikan apa pun
yang berlaku pada baris yang diberikan kepadanya.

Jadi H* tetap tak terjaga, dan `crypto/guarded_record.py` **benar**
mengeluarkannya dari payload alih-alih menganggapnya tak berbahaya.

---

## Θ̂ bukan celah — ia harga

Tampak seperti celah. G4 adalah `ρ = Θ̂ − U ≥ 0`, sebuah **pertidaksamaan**,
jadi ia menangkap Θ̂ terlalu kecil dan tak pernah terlalu besar. 118 dari 133
lolos.

Tapi **ρ aditif**: `ρ(a+b) = ρ(a) + ρ(b)`, terverifikasi atas seluruh 784
pasang. Maka **batas atas berhingga apa pun dilanggar oleh jumlah dua hybit
sah.** Satu-satunya batas yang tertutup di bawah penjumlahan adalah tanpa batas
sama sekali, dan ρ identik nol — yang bukan kasusnya.

> **Ketertutupan dan deteksi dua-sisi pada Θ̂ tidak bisa dimiliki bersamaan.**
> Guard-nya memilih ketertutupan, dan ini biayanya.

Sabotase membenarkan arahnya: membuat G4 dua-sisi (`0 ≤ ρ ≤ 3`) menggagalkan
tes ketertutupan.

---

## Jadi 93,1% adalah langit-langitnya

Bukan 100%, dan sisanya bukan pekerjaan yang belum dilakukan:

- **17 dari 18 komponen** bisa mencapai 100%
- **Θ̂** terkunci di 11% oleh struktur monoid
- **H\*** terkunci di 0% oleh tak adanya hukum yang jujur

Itu posisi yang bisa dipertahankan saat diperiksa orang. "100% terjaga" tidak.
