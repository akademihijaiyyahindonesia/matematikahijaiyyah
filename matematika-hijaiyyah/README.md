# Matematika Hijaiyyah, dibaca sebagai komputasi

Bukan bahasa yang dimatematikakan. **Tabelnya sendiri adalah program**, dan
guard-nya bukan pemeriksaan yang ditempelkan padanya.

---

## Master Table adalah delapan belas pengklasifikasi

`docs/csgi_algorithm_spec.md` bagian 4 adalah programnya. `classify_khatt` dan
`classify_qaws` menyusuri graf sebuah huruf dan mengembalikan **satu keranjang
per komponen**, atas predikat geometris: `is_standalone`, `touches_loop`,
`on_mainpath`, `has_angle`, `is_vertical`. Lalu `K[bucket] += 1`.

Tidak ada hal lain yang menulis sel-sel itu. Jadi tiap sel adalah **cacahan
berapa kali sebuah pengklasifikasi menyala.**

Dibaca begitu, kolomnya terbagi tiga peran — dan pembagiannya tegas:

| peran | n | kolom |
|---|---:|---|
| **PENANDA** | 8 | Nb, Nd, Kp, Ks, Ka, Kc, Qa, H* |
| **PEMBEDA** | 4 | Θ̂, Na, A_N, A_Q |
| **PENCACAH** | 6 | Kx, Qp, Qx, Qs, Qc, A_K |

Empat menyala **tepat sekali**: `Nb`→ج, `Kp`→ا, `Ka`→ك, `H*`→ك.

---

## Dan guard-nya adalah ruang nol abjad

Hitung ruang nol matriks 28×18 dan ia mengembalikan **tepat empat relasi
kolom** — tanpa dicari:

```
  A_N = Na + Nb + Nd              ← G1, persis
  A_K = Kp + Kx + Ks + Ka + Kc    ← G2, persis
  A_Q = Qp + Qx + Qs + Qa + Qc    ← G3, persis
  H*  = Ka                        ← tak ada yang memeriksanya
```

**G1–G3 bukan pemeriksaan yang dipaksakan pada data.** `classify_khatt`
mengembalikan tepat satu keranjang per komponen, jadi keranjangnya **niscaya**
berjumlah sebanyak komponennya — dan itulah isi A_K. Guard-nya menyatakan bahwa
**pengklasifikasinya adalah sebuah fungsi**. Definisional, bukan empiris.

Yang keempat ditambahkan sebagai G5 lalu **dicabut** — lihat
[`GUARD.md`](GUARD.md).

---

## Isi folder

| Berkas | Isi |
|---|---|
| [`GUARD.md`](GUARD.md) | Seberapa kuat guard-nya per komponen, dan mengapa satu celahnya tak bisa ditutup |
| [`ALGEBRA.md`](ALGEBRA.md) | Monoid: ketertutupan, dan sifat yang tak dimiliki checksum |
| [`LINEAGE.md`](LINEAGE.md) | Hisab al-Jummal: nilai yang ditetapkan vs bentuk yang diukur |

Dijangkar oleh
[`test_table_as_program.py`](../tests/test_integrity/test_table_as_program.py),
[`test_guard_coverage.py`](../tests/test_integrity/test_guard_coverage.py),
[`test_monoid_closure.py`](../tests/test_integrity/test_monoid_closure.py),
[`test_substrate_independence.py`](../tests/test_integrity/test_substrate_independence.py) dan
[`test_jummal_lineage.py`](../tests/test_integrity/test_jummal_lineage.py) —
26 tes.

---

## Dan aljabarnya tidak menyebut substrat sama sekali

`core/hybit.py` dan `core/guards.py` dipindai: **nol** clock, **nol** LUT,
**nol** lebar kata, **nol** mask, **nol** operator bit, **nol** tipe integer
mesin. Satu-satunya "32" di dekat lapis ini adalah CRC32 di `hisab/digest.py`
— itu transport, tempat lebar byte memang pokoknya.

Karena itu jalur fotonik §10.2 adalah **penggantian lintasan, bukan porting**:
Θ̂ → fase foton, tiga N → tiga panjang gelombang, K/Q → slot waktu dan momentum
sudut orbital. Tak ada properti aljabar yang perlu dibuktikan ulang di sana.
