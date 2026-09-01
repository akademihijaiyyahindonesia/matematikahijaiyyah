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
1. θ            C[col] = XOR seluruh lane di kolom itu
                D[col] = C[col−1] ⊕ rotl(C[col+1], 1)
                lane[row][col] ^= D[col]

2. ρ·π          lane[i] dirotasi kiri sebanyak RHO[i], lalu dipindah ke PI[i]

3. SUBSTITUSI   setiap byte tiap lane melewati SBOX

4. KONSTANTA    lane[0] ^= RC[r]
```

`RHO[i] = (i·(i+1)/2) mod 64`, `PI[i] = 5·(i mod 5) + ((i div 5) + 3·(i mod 5)) mod 5`.
Rotasi adalah rotasi kiri 64-bit; jumlah geser diambil modulo 64.

**Mengapa pola θ, bukan paritas kolom sendiri.** Versi pertama menambahkan
paritas sebuah kolom ke kelima lane kolom itu. Itu **tidak invertibel**: lima
salinan sebuah nilai ber-XOR kembali jadi satu, sehingga paritas kolom yang
baru selalu nol dan seluruh state runtuh ke subruang. Terukur atas GF(2),
lapisan linearnya berperingkat **1276 dari 1600** — 324 dimensi hilang, 320 di
antaranya persis lima kolom × enam puluh empat posisi bit. Sponge mensyaratkan
permutasi, dan itu bukan. Menambahkan paritas **tetangga** menghindarinya, dan
lapisan yang ditulis ulang berperingkat 1600.

Pencarian acak tak akan menemukannya: dua puluh ribu state acak tak memberi
satu pun tabrakan, karena ruangnya 2¹⁶⁰⁰. Cacat itu hanya terlihat dengan
membangun matriksnya dan menghitung rank-nya — dan itulah pelajaran yang layak
dibawa: uji statistik atas konstruksi yang patah bisa tampak sempurna.

**Konstanta ronde.** `RC[i] = 8 byte pertama SHA-256(cube_digest ‖ "tawaf" ‖ i)`,
dibaca big-endian.

**Mengapa 28 ronde.** Difusi jenuh pada ronde 3, terukur: ronde 1 mencapai 11
dari 25 lane pada avalanche 0,029; ronde 2 mencapai 25 pada 0,335; ronde 3
berada di 0,499 dan tak ada yang bergerak sesudahnya. Tiga adalah lantainya,
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
digest("")                = b9921d81a84592c27a3ec3d0a6778e52a226cb93a07ef5f4c3d1781181b70208
digest("a")               = 515a1d044720d26d4eedbcf774223f52f42bd40b6d708306fc4bc1102d112e7d
digest("Ka'bah")          = 7a48622af64d532897e83d0aaf286c5f9d5f5d9df0dc34a41d159e512363ace4
digest(bytes(range(128))) = 800dc26abcd86ccbb7d6545f3a943358f8af6c7cf565ec6fad866ad6549bf134
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

`tools/kabah_attack.py` menjalankan enam pemeriksaan: invertibilitas lewat rank
GF(2), mutu S-box, lantai difusi, relasi rotasi, titik tetap, dan bias keluaran.
Semuanya bertahan pada versi ini. Pemeriksaan pertamalah yang menemukan cacat
di atas.

Sampai ada yang mencoba, [EH] adalah label yang benar.
