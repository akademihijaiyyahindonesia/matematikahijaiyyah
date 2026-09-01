# Ka'bah — Spesifikasi dan Undangan Kriptanalisis

**Kriptografi Absorpsi Byte Atas Hijaiyyah**
Versi 1.0 · 1 September 2026 · HMCL

---

## Undangan

Dokumen ini menerbitkan permutasi Ka'bah agar diserang.

Konstruksi ini **belum pernah dikriptanalisis siapa pun**. Yang ada barulah
pengukuran, dan pengukuran bukan kriptanalisis: ia menunjukkan sebuah
konstruksi tidak jelas-jelas rusak, bukan bahwa ia kuat. Satu-satunya cara
sebuah primitif menjadi layak dipercaya adalah bertahan dari serangan publik
selama bertahun-tahun.

Karena itu label epistemiknya **[EH]** — hipotesis rekayasa, dalam pengertian
§I.14 buku *Matematika Hijaiyyah*. Jangan pakai untuk apa pun yang penting.

**Yang paling berguna bagi kami** adalah serangan pada versi ronde-tereduksi.
Berapa ronde yang bisa Anda tembus? Nilai itu, dibandingkan dengan 28, adalah
margin sebenarnya — dan angka itulah yang kami tidak punya.

Kirim temuan ke repositori proyek. Serangan yang gagal pun berguna: catat
berapa ronde yang Anda capai.

---

## 1. Parameter

| | Nilai |
|---|---|
| State | 5 × 5 lane × 64 bit = **1600 bit** |
| Rate | 16 lane (cincin luar) = **1024 bit**, 128 byte |
| Capacity | 9 lane (cincin dalam + pusat) = **576 bit** |
| Tingkat keamanan | ~288 bit (capacity/2) |
| Ronde | 7 sirkuit × 4 tawaf = **28** |

State adalah larik 5×5, diindeks `i = row·5 + col`, tiap lane 64 bit
little-endian.

---

## 2. Substitusi — semi-log GF(2⁸)

**Lapangan.** Dipilih dari `SHA-256` kubus tersegel (§4). Byte ke-0 memilih
salah satu dari 30 polinomial tak-tereduksi derajat 8, urut menaik.

```
polinomial = 0x12B      generator = 2
```

**Tabel log/antilog.** `antilog[0] = 1`, `antilog[i+1] = antilog[i] · g`
dalam GF(2⁸) mod polinomial. `log` adalah inversnya.

**Invers.** `inverse(0) = 0`; selain itu `inverse(x) = antilog[255 − log[x]]`.

**Peta affine.** Untuk konstanta `c`:

```
affine(b) = b ⊕ rotl(b,1) ⊕ rotl(b,2) ⊕ rotl(b,3) ⊕ rotl(b,4) ⊕ c
```

`c` dicari maju dari byte ke-1 digest kubus sampai konstanta pertama yang
membuat S-box **tanpa titik tetap**. Hasilnya `c = 0xE7`.

```
SBOX[x] = affine(inverse(x))
```

**Sifat terukur** — menyeluruh atas 256 nilai:

| | Ka'bah | AES |
|---|---:|---:|
| Keseragaman diferensial | 4 | 4 |
| Nonlinearitas | 112 | 112 |
| Titik tetap | 0 | 0 |
| Involusi | tidak, 0/256 | tidak |

Keempatnya adalah optimum untuk bijeksi 8-bit. Sifat ini berlaku untuk
**setiap** polinomial tak-tereduksi derajat 8 — kubus memilih anggota
keluarga, bukan memberi kekuatannya.

---

## 3. Permutasi

Satu ronde `r`, untuk `r = 0 … 27`:

```
1. SUBSTITUSI   setiap byte tiap lane melewati SBOX

2. BARIS        untuk tiap baris:  acc = XOR seluruh lane di baris itu
                lane[row][col] ^= rotl(acc, col + r + 1)

3. KOLOM        untuk tiap kolom:  acc = XOR seluruh lane di kolom itu
                lane[i] = rotl(lane[i] ^ acc, i + 1)      i = row·5 + col

4. KONSTANTA    lane[0] ^= RC[r]
```

Rotasi adalah rotasi kiri 64-bit; jumlah geser diambil modulo 64.

**Konstanta ronde.** `RC[i] = 8 byte pertama SHA-256(cube_digest ‖ "tawaf" ‖ i)`,
dibaca big-endian.

**Mengapa 28 ronde.** Difusi jenuh pada ronde 3, terukur: ronde 1 mencapai 20
dari 25 lane pada avalanche 0,055; ronde 2 mencapai 25 pada 0,302; ronde 3
berada di 0,496 dan tak ada yang bergerak sesudahnya. Tiga adalah lantainya,
selebihnya margin. Dua puluh delapan memberi 9,3× — Keccak memegang 8× dengan
dua puluh empat.

---

## 4. Kubus tersegel

`cube_digest = SHA-256` atas 28 Letter Exomatrix (§IIE.2.1 buku), masing-masing
5×5, dibaca urut ROM huruf, baris demi baris, satu byte per entri.

```
cube_digest = 98e5d08315d249ed…
```

Kubus **hanya** memilih polinomial, konstanta affine, dan konstanta ronde.
Ia tidak mengaduk apa pun.

---

## 5. Sponge

**Absorpsi.** Jalur tawaf menyusuri keliling sebagai satu sirkuit tertutup:

```
[0, 1, 2, 3, 4, 9, 14, 19, 24, 23, 22, 21, 20, 15, 10, 5]
```

Masukan hanya menyentuh keenam-belas lane itu. Sembilan lane yang dikelilinginya
adalah capacity dan tak pernah ditulis dari luar.

- **Per-lane**: lane ke-n di-XOR ke `TAWAF_PATH[n mod 16]`.
- **Per-bit** (spektrum): bit ke-n ke `TAWAF_PATH[n mod 16]` pada posisi
  `n div 16`. Terukur tidak berbeda dari per-lane dalam difusi; ada untuk
  jalur masukan 1-kawat.

Setelah 1024 bit terserap, permutasi berjalan.

**Padding.** Tambahkan `0x01`, lalu `0x00` sampai kelipatan 128 byte, lalu
XOR `0x80` ke byte terakhir.

**Squeeze.** Keluarkan lane menurut `TAWAF_PATH`, little-endian; permutasi lagi
bila perlu lebih banyak.

---

## 6. Vektor uji

Lengkap dalam [`test_vectors.json`](test_vectors.json) — S-box penuh,
28 konstanta ronde, keluaran permutasi, dan digest.

```
digest("")                = 79c6e637cd6577f733c2af82f8d1a80593574a8c1a4c2583367a3afd3ec6186f
digest("a")               = c9bf4839e221831902e31205cb5e2b54607a26e171e2c792ac56b051568d26e1
digest("Ka'bah")          = 276117a27d5b14569705cb01539a4a866a521a5ff5463cd89f0105c3ea08b608
digest(bytes(range(128))) = 1a492f4e198abd9ece7ba09dae851bf71d018a57b29d4231ae4eb7d670049ff8
```

Implementasi rujukan: `src/hijaiyyah/crypto/cube.py`.

---

## 7. Yang **tidak** diklaim

- **Bukan sandi.** Ka'bah tidak mendefinisikan enkripsi. Untuk kerahasiaan
  pakai AES-256-GCM atau ChaCha20-Poly1305 dari pustaka teruji.
- **Bukan pengganti SHA-256.** Untuk apa pun yang penting, pakai SHA-256.
- **Belum terserang.** Nol kriptanalisis publik. Perbandingannya dengan SHA-3
  adalah perbandingan *parameter*, bukan perbandingan kepercayaan.
- **Geometrinya tidak memberi keamanan.** Ia memilih parameter secara
  reprodusibel dan terikat segel. Kekuatannya ada di peta invers dan pada
  jumlah ronde.

Dalam sistem Ka'bah yang lebih besar, permutasi ini adalah **lapis 2** dan
berlabel [EH]. Yang memikul keamanan adalah **lapis 3**: HMAC-SHA256 dengan
kunci turunan HKDF.

---

## 8. Yang akan mengubah statusnya

1. **Serangan ronde-tereduksi** — berapa dari 28 yang bisa ditembus. Ini yang
   paling kami butuhkan.
2. **Analisis diferensial dan linear** atas permutasi penuh, bukan hanya
   S-box-nya.
3. **Sifat aljabar** — derajat, kubus, integral. Peta invers punya struktur
   aljabar yang kaya; apakah lapisan linearnya cukup memecahnya?
4. **Serangan rotasi** — lapisan campurnya bergantung berat pada rotasi.

Sampai ada yang mencoba, [EH] adalah label yang benar.
