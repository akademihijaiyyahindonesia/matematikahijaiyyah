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
| **HMAC-SHA256** | **perangkat lunak**, dan **RTL sebagai slot sendiri** | `crypto/signing.py`; `hijaiyyah_hmac.v`, tidak di jalur `hijaiyyah_kabah_top` |
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

Disintesis terhadap Tang Nano 20K (GW2AR-18C: 20.736 LUT4 / 15.552 FF),
yosys 0.68, `synth -flatten` lalu `abc -lut 4`:

| SLICE_BYTES | LUT4 | % papan | FF | clock/permutasi |
|---:|---:|---:|---:|---:|
| 8 | 6.910 | 33,3% | 2.009 | 786 |
| 25 | **8.096** | **39,0%** | 2.007 | 310 |

Keduanya muat. Margin di SLICE=25 adalah **544 LUT4**.

> **Angka ini pernah basi.** Header mencatat 7.426 (85%) dari commit `cd6a29c`;
> commit berikutnya menjadikan gerbang benar-benar menggerbang — `gate_mode`,
> `break_at`, `break_count`, backpressure `bits_ready` — dan sintesis tak pernah
> dijalankan ulang. Biayanya **+670 LUT4**, dan margin turun dari 15% ke 6%.

---

## Yang belum bisa diukur

`hijaiyyah_kabah_top` sendiri masih **[EH]**, dan tetap begitu selamanya —
bukan karena belum sempat, tapi karena itu memang tujuannya: ia menyodorkan
**1.665 bit port** ke perangkat berisi **384 IOB**, dan **tidak akan pernah**
jadi top level yang bisa ditempatkan, persis seperti `hcpu_top` bukan.
Interfacenya lebar dengan sengaja; yang menyempitkannya adalah wrapper, bukan
modul itu sendiri.

## Wrapper Ka'bah: antarmuka 10 pin, dijalankan di papan

`hijaiyyah_kabah_gowin_top.v` adalah wrapper itu — persis seperti
`hcpu_gowin_top` untuk HCPU. `out_state` tetap internal (bisa diakses lewat
hierarki oleh testbench, seperti sebelumnya); yang keluar ke pin papan hanya
clk, reset, UART RX/TX, dan 6 LED — **10 pin**. Diukur 4 September 2026 dengan
yosys 0.68 (`-nodsp`) → nextpnr-himbaechel 0.11.1, Tang Nano 20K
(GW2AR-18C, papan target sekarang), dan direproduksi 5 September 2026 lewat
`make -C rtl/fpga/gowin kabah_bitstream` — target `make` sungguhan sekarang,
bukan lagi command manual yang diingat, dengan fingerprint RTL-nya sendiri
di header (`tests/test_integrity/test_place_and_route.py`):

| | terpakai / kapasitas | % |
|---|---:|---:|
| IOB | 10 / 384 | **2%** |
| LUT4 | 12.061 / 20.736 | **58%** |
| DFF | 1.965 / 15.552 | 12% |
| BSRAM | 0 / 46 | 0% |
| Fmax | **165,98 MHz** (routed, `gowin_pack` sukses, bitstream 4,6 MB) | |

Diukur ulang 10 September 2026, dan kali ini bitstream-nya **dijalankan**:
`kabah_uart_test.py` melaporkan 2/2 frame, 400/400 byte cocok dengan
`cube.py`, berantai lintas frame tanpa reset di antaranya. Fmax naik dari
117,91 MHz karena penyerempak reset berhenti menggerbangi level pin 87
(MODE1) yang ditahan rendah papan — cacat yang sama membuat HCPU bisu pada
bring-up pertama hari itu.

Wrapper ini juga diverifikasi berbeda dari `tb_hijaiyyah_kabah_top.v`: bukan
lewat `bit_in`/`out_state` langsung, tapi lewat framing UART sungguhan (start
bit, 8 bit data, stop bit) — dua blok 128-byte berturut-turut tanpa reset di
antaranya, dan hasilnya cocok persis dengan `cube.py` untuk keduanya, 400/400
byte. Testbench itu sendiri yang menemukan bug nyata di wrapper sebelum lolos:
`tx_data` balapan dengan `dump_idx` pada tepi clock yang sama, jadi byte 0
dari setiap dump selalu terlewat.

**Keduanya berjalan di papan, sendiri-sendiri.** HCPU 14.231 LUT4 (68%),
Fmax 84,26 MHz. Ka'bah-plus-wrapper 12.061 LUT4 (58%), Fmax 165,98 MHz.
Keduanya lewat sintesis + PNR + `gowin_pack` sungguhan, dan keduanya
benar-benar dijalankan: HCPU membalas 23 byte lewat UART, Ka'bah mencocokkan
400/400 byte dengan `cube.py`.

Dijumlah naif 67% + 58% = 125%. **Diukur sebagai satu top level: 105% —
lewat 960 sel.** Selisih antara 125% dan 105% adalah logika yang memang
dipakai bersama. Tapi 960 sel itu **tidak perlu dicarikan tempat**: tak ada
yang menuntut keduanya menempati fabric bersamaan. Papan memuatnya sebagai
slot bitstream berurutan (`rtl/scripts/rack.py`), jadi biaya rack adalah
slot terbesar (HDMI, 70%), bukan jumlahnya — ketiga slot sudah dijalankan
berurutan dalam satu sesi ([PAPAN.md](../cosmictera-build/PAPAN.md)).
