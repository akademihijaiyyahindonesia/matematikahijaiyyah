# Ka'bah

Tiga belas modul Verilog, 1.722 baris, dan satu angka throughput yang
lebih rendah daripada yang pernah dipercaya.

Folder `kabah/` memegang uraian penuhnya —
[FLOW.md](../kabah/FLOW.md), [SUBSYSTEM.md](../kabah/SUBSYSTEM.md),
[SILICON.md](../kabah/SILICON.md). Halaman ini menempatkannya di dalam
inventaris teknologi.

---

## Yang dijalankan di papan

**10 September 2026, Tang Nano 20K.** `kabah_uart_test.py` mengirim
`bytes(range(256))` sebagai dua bingkai 128 byte **berturut tanpa reset di
antaranya**, lalu membandingkan 400 byte balasan dengan `cube.py`:

```
frame1: PASS, 200/200 bytes match cube.py
frame2: PASS, 200/200 bytes match cube.py
PASS: 2/2 frame(s), 400 bytes total, all match cube.py
```

Dua bingkai tanpa reset itu yang membuat uji ini berarti: ia menguji
**penyerapan berantai lintas blok**, bukan satu blok yang kebetulan benar
sendirian.

```
LUT4   12.061 / 20.736   58%
DFF     1.965 / 15.552   12%
BSRAM       0 /     46    0%
Fmax   165,98 MHz
```

Itu pembungkus tanpa lapis 3. Sejak 3 Oktober 2026 slot UART Ka'bah membawa
HMAC-SHA256 dengan kunci uji publik: 15.030 LUT4 (72%), 4.132 DFF, 0 BSRAM;
Fmax tidak diklaim, dan bitstream itu belum dijalankan di papan.

Nol BSRAM — seluruh keadaan spons ada di flip-flop dan logika.

---

## Modul

`rtl/hijaiyyah_*.v`:

| Modul | Kerjanya |
|---|---|
| `hijaiyyah_kabah_top` | perakit lima tahap |
| `hijaiyyah_deserialiser` | aliran bit → byte, menemukan batas |
| `hijaiyyah_jamrah_gate` | gerbang penyaring sebelum spons |
| `hijaiyyah_node_counter` | pencacah simpul |
| `hijaiyyah_sponge` | spons — penyerap dan pemeras |
| `hijaiyyah_ramal_impulse` | impuls ramal |
| `hijaiyyah_rotate_core` | rotasi |
| `hijaiyyah_linear` | lapis linear |
| `hijaiyyah_sbox` | kotak substitusi |
| `hijaiyyah_round_constants` | konstanta ronde |

Padanan perangkat lunaknya di `src/hijaiyyah/crypto/` — `cube.py`,
`kabah.py`, `sbox_logic.py`, `node_counter.py`, `elements.py`, dan
`guarded_record.py`. Keduanya diuji terhadap vektor yang sama, dan itulah
sebabnya balasan papan bisa divonis benar alih-alih diperdebatkan.

---

## Angka yang harus diingat, bukan yang enak dikutip

**Throughput sistem 2,59 MB/s, bukan 11,15 MB/s.**

Angka 11,15 adalah laju **spons saja, disuap byte-paralel** — kondisi yang
tidak pernah terjadi di sistem sungguhan. Yang menghentikannya bukan spons
melainkan **deserialiser bit-serial**: delapan clock per byte. Uraian
lengkapnya di [kabah/FLOW.md](../kabah/FLOW.md).

Ini dicatat di sini karena angka jenis pertama yang lebih besar itulah yang
biasanya berpindah ke presentasi, lalu ke proposal, lalu jadi klaim yang
tidak bisa ditarik.

---

## Label — dan ini yang paling penting di halaman ini

**Spons berlabel EH, dan tetap EH.**

Statistik avalanche yang bagus — 0,5007, 20.000 keadaan tanpa tabrakan —
**bukan bukti keamanan**. Ia terukur, belum dikriptanalisis. Tidak ada
satu pun analisis diferensial atau linear independen yang pernah
dijalankan terhadap konstruksi ini.

Yang **CC**: bahwa perangkat keras dan perangkat lunak menghasilkan keadaan
yang sama, 400 dari 400 byte, berantai lintas bingkai, di papan fisik.
Itu klaim tentang **kebenaran implementasi**, bukan tentang keamanan.

Membaca yang pertama sebagai yang kedua adalah kesalahan yang halaman ini
ada untuk mencegahnya.
