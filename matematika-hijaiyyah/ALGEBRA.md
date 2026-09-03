# Monoid, dan yang tak dimiliki checksum

`(𝒱, +, 0)` adalah monoid komutatif. Bukan grup: invers aditif gagal, dan
gagalnya karena **domain ℕ₀**, bukan karena guard-nya.

---

## Ketertutupan, diuji sebagaimana ia disandari

`Hybit.cadd` mengembalikan `Hybit(result, _skip_check=True)`. **Tidak ada yang
memvalidasi hasil penjumlahan** — invarian objeknya bersandar seluruhnya pada
Proposisi 3.2.1 benar. Itu optimasi yang bisa dibela, dan dulu tak terbela.

Yang berdiri sebelumnya: tiga asersi atas **satu pasang** huruf, mencakup G1–G4
dan **tidak pernah T1 atau T2** — padahal justru implikasi itulah yang bisa
gagal tanpa sum-check menyadarinya, karena penjumlahan bisa menaikkan Kₛ. Dan
rumus guard-nya disalin ulang di dalam tes, jadi perubahan pada guard tak bisa
menjangkaunya.

Sekarang: **seluruh 784 pasang berurut lewat `guard_check` sendiri**, T1 dan T2
ikut, 2.000 jumlah lima-suku acak, identitas dan komutativitas atas seluruh
tabel. Semua lolos — proposisinya benar, ia hanya belum pernah ditegakkan.

---

## Sifat yang tak dimiliki checksum

Ini alasan guard layak diperkuat sama sekali:

```
  784 penjumlahan, komponen demi komponen:

    guard hybit masih sah          784/784   (100%)
    CRC-32 jumlah dpt diturunkan     0/784   (0%)
```

Menjumlahkan dua rekaman ber-checksum **membatalkan checksum-nya** — ia harus
dihitung ulang atas seluruh hasil. Menjumlahkan dua hybit tidak: **jumlahnya
tetap sah dan tetap terperiksa O(1), tanpa menyentuh suku aslinya.**

Itu bukan efisiensi. Itu **kelas kemampuan yang berbeda**: agregasi tanpa
validasi ulang.

---

## Dan `guard_check` sendiri bukan uji keanggotaan 𝒱

Buku mendefinisikan 𝒱 sebagai himpunan bagian dari ℕ₀¹⁸ — **non-negativitas
adalah domainnya**, dan guard adalah yang diperiksa *di atas* domain itu.
Fungsinya melewatkan domain.

Akibatnya `−h` lolos untuk **setiap huruf yang ρ-nya nol** — sepuluh dari dua
puluh delapan. Sum-check kebal negasi karena linear, `−0 ≥ 0` tetap benar, dan
T1/T2 vacuous saat Kₛ < 0.

Yang menahan garisnya adalah pemeriksaan di `Hybit.__init__`, **bukan fungsi
bebasnya**. Dan `is_valid()` yang berbunyi "O(1) membership check: h* ∈ 𝒱"
mengklaim lebih dari yang ia kerjakan.

---

## Dimensi yang sebenarnya: empat belas

`rank(28×18) = 14`, dan `v₁₄` sendiri berperingkat penuh 14.

Itu **bukan temuan** — halaman 41 buku, butir 4: *"direpresentasikan sebagai
vektor invarian 14-dimensi dan codex 18-dimensi"*. Empat belas adalah
**invarian**; empat sisanya — A_N, A_K, A_Q, H* — adalah yang **dibawa codex**.
