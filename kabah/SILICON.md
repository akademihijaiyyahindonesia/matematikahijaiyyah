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
keamanan, dan di perangkat keras ia baru ada dengan kunci uji.

Sejak 3 Oktober 2026 pembungkus slot UART, `hijaiyyah_kabah_gowin_top.v`,
menginstansiasi `hijaiyyah_hmac` dan mengirim tag HMAC-SHA256 32 byte di belakang
200 byte keadaan. Kuncinya **kunci uji publik** — RFC 4231 kasus uji 1, dua puluh
byte `0x0b`, ditanam di bitstream: ia membuktikan jalurnya, bukan mengamankan apa
pun. Ka'bah-HDMI dan top gabungan tetap tanpa HMAC: lapis 3 hanya
dibangun bila `KABAH_WITH_HMAC` didefinisikan, dan hanya build slot UART yang
mendefinisikannya.

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

Tabel di atas adalah pembungkus **tanpa lapis 3** (`KABAH_WITH_HMAC` tidak didefinisikan). Dengan
lapis 3, yang sejak 3 Oktober 2026 menjadi bawaan `make kabah_bitstream`:

| | terpakai / kapasitas | % |
|---|---:|---:|
| IOB | 10 / 384 | 2% |
| LUT4 | 15.030 / 20.736 | **72%** |
| DFF | 4.132 / 15.552 | 26% |
| ALU | 604 / 15.552 | 3% |
| BSRAM | 0 / 46 | 0% |

Bitstream 4.618.782 byte, sha256
`fdc84e3d1cf2a565fa495ecbdd3b10d792464f1e8385240d77e3c39492a86b49`. **Fmax
tidak diklaim**: nextpnr mencetak 97,93 MHz sesudah routing dan menilainya
terhadap batas bawaan 12 MHz; yang ditunjukkan angka itu hanya jarak di atas
27 MHz. Di simulasi lewat pin UART: 400/400 byte keadaan cocok `cube.py` dan
64/64 byte tag cocok `hmac`/`hashlib`; sebelas sabotase jalur tanda tangan
membuat bench merah.

**Di papan, 6 Oktober 2026.** Bitstream itu — sha256 di atas — dimuat ke Tang
Nano 20K lewat **SRAM, bukan flash**, dan menjalankan **satu run dua frame**
(`rtl/scripts/kabah_uart_test.py`, vektor `bytes(range(256))`): 2/2 frame,
**400/400 byte keadaan** cocok `cube.py`, **64/64 byte tag** cocok
`hmac`/`hashlib` yang dihitung host sendiri atas byte yang diterimanya,
exit 0. Batasnya: satu run, dengan kunci uji publik RFC 4231. Ini membuktikan
jalur HMAC bekerja di FPGA ini; **bukan** uji ketahanan, dan **bukan**
keamanan produksi. Log menyimpan putusan tiap frame, bukan byte-nya.

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
