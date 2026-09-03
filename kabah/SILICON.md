# Di silikon

## Pembagiannya

| bagian | tempat | catatan |
|---|---|---|
| Kanonikalisasi | perangkat lunak | penyandian byte↔huruf |
| Penemuan fase | perangkat lunak | sekali per aliran, bukan per clock |
| Gerbang jamrah | **RTL** | `hijaiyyah_jamrah_gate.v` |
| Pencacah node | **RTL** | `hijaiyyah_node_counter.v` |
| Deserialiser | **RTL** | 8 clock/byte |
| S-box | **RTL** | logika, bukan tabel |
| Permutasi & spons | **RTL** | `hijaiyyah_rotate_core.v`, `hijaiyyah_sponge.v` |
| **HMAC-SHA256** | **perangkat lunak** | **tak ada core SHA-256 di repo ini** |
| Manifes & segel | perangkat lunak | `crypto/program.py` |

**Baris paling penting adalah yang kedua dari bawah.** Lapis 3 memikul seluruh
keamanan, dan ia tidak ada di perangkat keras.

---

## S-box: logika, bukan tabel

```
  sebagai tabel   274 LUT4
  sebagai logika   76 LUT4      3,6× lebih kecil
```

Versi logika bukan sekadar lebih kecil — ia yang tanpa celah timing tabel.

Dan satu jebakan yang pernah terjadi: `gf4_inv` ditulis sebagai `case`, dan
yosys **menyimpulkan memori 16×4** di bawah komentar yang berbunyi "empat LUT4".
Diganti dengan ANF.

---

## Ukuran terukur

Disintesis untuk Tang Nano 9K (GW1NR-9: 8.640 LUT4 / 6.693 FF), yosys 0.68,
`synth -flatten` lalu `abc -lut 4`:

| SLICE_BYTES | LUT4 | % papan | FF | clock/permutasi |
|---:|---:|---:|---:|---:|
| 8 | 6.910 | 80,0% | 2.009 | 786 |
| 25 | **8.096** | **93,7%** | 2.007 | 310 |

Keduanya muat. Margin di SLICE=25 adalah **544 LUT4**.

> **Angka ini pernah basi.** Header mencatat 7.426 (85%) dari commit `cd6a29c`;
> commit berikutnya menjadikan gerbang benar-benar menggerbang — `gate_mode`,
> `break_at`, `break_count`, backpressure `bits_ready` — dan sintesis tak pernah
> dijalankan ulang. Biayanya **+670 LUT4**, dan margin turun dari 15% ke 6%.

---

## Yang belum bisa diukur

**Fmax Ka'bah tetap [EH].** Bukan karena belum sempat: `hijaiyyah_kabah_top`
menyodorkan **1.665 bit port** ke perangkat berisi **276 IOB**. Ia **tidak bisa
ditempatkan sama sekali** sampai ada wrapper yang menyempitkan antarmukanya —
persis seperti `hcpu_gowin_top` untuk HCPU.

Sesudah wrapper itu ada, throughput 2,59 MB/s yang selama ini berskala terbalik
terhadap clock tak dikenal jadi angka tetap.

**Dan Ka'bah tidak muat berdampingan HCPU.** Sendiri-sendiri: HCPU 78% LUT4,
Ka'bah SLICE=25 **94%**. Bersama tidak mungkin di papan ini. Itu keputusan
arsitektur yang menunggu — dua chip, satu yang lebih besar, atau berbagi waktu.
