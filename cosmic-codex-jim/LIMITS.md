# Apa yang Jim bukan

Tiga bacaan diuji dan **gagal terukur**. Semuanya disimpan, karena resep lebih
berharga dengan kegagalannya terlampir — dan karena ketiganya terdengar masuk
akal sampai diukur.

---

## 1. Jim bukan pusat metrik

"Jadikan Jim pusat cosmic" diuji sebagai **medoid** — huruf dengan jumlah jarak
kuadrat terkecil ke 27 lainnya.

```
  1. خ Kha      254
  2. غ Ghain    262
  3. ح Ha       278
  4. ن Nun      280
  5. ع Ain      286
  6. ج Jim      288    ← peringkat 6 dari 28
```

**Kha yang medoid, bukan Jim.**

Yang benar ada di tingkat **kelas**, bukan huruf: Θ̂=3 (270°) adalah kelas paling
terpusat dari delapan (rata‑rata 296, terendah), lima dari enam huruf paling
tengah ada di dalamnya, dan **Jim huruf pertamanya**. Itu posisi nyata, dan ia
bukan hal yang sama dengan menjadi pusat.

---

## 2. Memusatkan penyandian pada Jim justru memperburuk

Kalau Jim pusat, memakainya sebagai titik asal selisih semestinya memperkecil
angka yang harus dicacah. Diukur, ia **12% lebih buruk**.

Sebabnya langsung terlihat begitu dihitung: **71% komponen sudah bernilai nol**.
Vektornya jarang, dan **nol sudah titik asal alaminya**. Memusatkan ke acuan
tak-nol mana pun merusak kejarangan itu.

---

## 3. Jim pivot metrik yang buruk

Diuji sebagai pivot untuk pemangkasan ketaksamaan segitiga — berapa perhitungan
jarak yang bisa dilewati.

```
  1. ا Alif      53,6%   (Θ̂ = 0°)
  2. هـ Haa      53,4%   (Θ̂ = 720°)
  …
 21. ج Jim       25,7%   ← peringkat 21 dari 28
 28. ي Ya        13,3%
```

**Pivot yang baik justru yang ekstrem, bukan yang di tengah** — itu hasil yang
sudah diketahui di indeks ruang metrik, dan pengukurannya membenarkannya: dua
pemenangnya adalah dua ujung spektrum derajat.

Terpusat itu yang membuat kepala panel bagus dan pivot buruk. **Dua pekerjaan
berbeda.**

---

## 4. Jim + Kha bukan pasangan pilihan

Bacaan pertama saya menyebut mereka *preferred pair*, dengan alasan puncak
korelasi-silang 11 memenuhi `2√31+1 ≈ 12`.

**Ambang itu bukan definisinya.** Pasangan pilihan m-sequence pada n=5 menuntut
korelasi-silang **tiga-nilai**:

```
  dituntut : {−1, −9, 7}          3 nilai
  terukur  : {−9, −5, −1, 3, 7, 11}   6 nilai, puncak 11 > 9
```

Jadi **kode Gold tidak bisa dibangun dari pasangan ini**. Yang bertahan lebih
lemah dan benar: 31 lawan 11 adalah pemisahan 2,8×, cukup membedakan dua node,
tidak cukup untuk keluarga kode.

Penarikan itu disimpan sebagai tes, supaya ia tetap tertarik.

---

## 5. Dan satu yang tidak diklaim sama sekali

Semua di folder ini adalah fakta tentang **satu matriks tertentu**: muka 5×5
yang dibangun dari vektor 18 komponen Jim, di bawah kuantisasi Q₉₀ dan tata
letak `build_exomatrix` tertentu.

Tidak diklaim bahwa ia berlaku untuk rasm lain, kuantisasi lain, atau bahwa ia
punya arti di luar aritmetika. **Tata letak muka itu memikul beban**: tiga
sabotase — menghapus ρ dari baris pertama, memindah A_N ke sel lain, menolkan
baris Q — masing-masing mematahkan sepuluh dari sebelas tesnya.
