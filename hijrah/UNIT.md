# Huruf sebagai satuan

## Cara mengukurnya

Bukan dengan menghitung identitas — itu cuma pencarian tabel. **Sebagai peta.**

Ambil muka 5×5 tiap huruf sebagai peta linier atas lapangan hingga, susun kata
dengan mengalikannya, dan hitung berapa peta berbeda yang bisa dicapai kata
sepanjang *n*. Logaritma dari cacah itu, dibagi *n*, adalah yang dibawa satu
huruf.

```
  panjang   keadaan GF(5)   bit total   bit/huruf
        1              28        4,81        4,81
        2             714        9,48        4,74
        3          16.359       14,00        4,67
        4         359.690       18,46        4,61
        5       7.262.058       22,79        4,56
```

Aliran bit: **1,00 di setiap panjang.**

## Kenapa GF(2) rugi

| mod | muka berbeda | tabrakan | periode maks |
|---:|---:|---:|---:|
| **2** | **24** | **4** | 31 |
| 3 | 27 | 1 | 242 |
| **4** | **28** | **0** | 62 |
| 5 | 28 | 0 | 3124 |
| 7 | 28 | 0 | 2736 |
| 256 | 28 | 0 | 512 |

Empat huruf hilang di GF(2), dan hilangnya bukan acak. Titik datang berpasangan
dan bertiga; **cacah titik genap tak terlihat oleh pembacaan paritas.**

Tapi kerugiannya bukan soal titik saja — Syin dan Nun juga berbeda di `Qx`.
Yang benar lebih sempit: **setiap komponen yang berbeda, berbedanya tepat 2**,
di mana pun ia duduk. Tabelnya mencacah dalam bilangan bulat; GF(2) hanya
membaca paritasnya.

## Konsekuensinya untuk hasil sebelumnya

Temuan mesin dan gelombang di [`cosmic-codex-jim/`](../cosmic-codex-jim/) tetap
berlaku — tapi keduanya diukur **di satu-satunya lapangan yang membuang apa yang
membuat huruf lebih dari denyut**. Itu dicatat di sana, bukan disembunyikan.
