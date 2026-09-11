# Percobaan Tang Nano 20K

Sembilan program untuk dijalankan di papan. Semuanya sudah diverifikasi di
simulator (`tests/test_integration/test_bench_programs.py`), jadi yang sampai
ke perangkat sudah diketahui benar — program salah di perangkat keras nyata
menghabiskan satu siklus flash dan sesi penelusuran untuk menemukan sesuatu
yang satu detik simulasi sudah menangkapnya.

## Cara menjalankan

```bash
cd rtl/fpga/gowin
make bitstream PROGRAM=../../programs/bench/e2_guard_x1.hasm
make flash
# lalu baca serial pada 115200 8N1
```

Setelah `HALT`, wrapper menunggu jalur UART senggang selama dua belas waktu-bit,
lalu memancarkan:

```
CYCLES=xxxxxxxx
```

Heksadesimal, bukan desimal — desimal butuh pembagian sepuluh, dan pembagi di
FSM `PRINT` sudah menjadi lintasan topologis terpanjang (86 tingkat). Menambah
pembagi kedua akan memperburuk justru hal yang diukur E1.

## Yang diukur pencacah itu

Dari lepas reset sampai `halted`. Termasuk pengisian pipeline, stall load-use,
stall store-load, dan flush cabang. **Tidak** termasuk waktu UART menguras
byte terakhir, karena pipeline berhenti sebelum itu.

Contoh terverifikasi: `test_bsm.hasm` pensiun 9 instruksi dalam **7.049 siklus**
— cetak "112", tiga digit, tiap digit menahan seluruh pipeline selama satu
bingkai UART penuh, plus isi pipeline lima-tahap yang tidak bisa dilihat oleh
hitungan instruksi statis di `tools/integrity_benchmark.py`. Dulu terbaca 14:
stall `PRINT` di `hcpu_controller.v` lepas begitu `uart_busy` turun di ANTARA
byte-byte satu cetakan, bukan di akhirnya — `HALT` sempat mencapai EX saat
digit masih dikirim. Diperbaiki (lihat `rtl/hcpu_controller.v`,
`rtl/programs/nui_embedding.hasm`); lihat
`tests/test_integration/test_fpga_wrapper.py::test_the_board_reports_its_own_cycle_count`
untuk ceritanya.

## Percobaan

| Berkas | Membuktikan | Bacaan |
|---|---|---|
| `e2_guard_x1` / `e2_guard_x10` | biaya satu `HGRD` dalam siklus | `(siklus_x10 − siklus_x1) / 9` |
| `e2_hisab` | biaya jalur digest sebagai pembanding | bandingkan dengan `e2_guard_x1` |
| `e2_scale_n{02,04,08,12}` | biaya guard **datar** saat n tumbuh | agregasi linear, guard tetap |
| `e3_sweep28` | ROM bersegel dieksekusi benar oleh perangkat | 28 nilai Θ̂ |
| `e4_frame` | frame HISAB 9 byte utuh dari perangkat | 4 nilai, lihat komentar berkas |
| `e5_negative` | G4 menolak vektor rusak **di perangkat keras** | `200` |

`e4_frame` baru mungkin sejak `HPACK` menghormati pemilih katanya; sebelumnya
hanya kata 0 yang pernah terpilih, jadi 4 byte dari 9.

## HDMI Tang Nano 20K

Port HDMI board sudah diuji secara fisik dengan bitstream test pattern resmi
Sipeed, dimuat ke SRAM melalui JTAG. Ini membuktikan konektor, pasangan TMDS,
dan monitor dapat bekerja; uji SRAM tidak mengubah flash program HCPU.

Integrasi lokal tersedia sebagai wrapper terpisah:

- `rtl/fpga/gowin/hcpu_hdmi_top.v` — HCPU + status video 1280x720
- `rtl/fpga/gowin/kabah_hdmi_top.v` — Ka'bah + status video 1280x720
- `rtl/fpga/gowin/dvi_tx_open.v` — encoder TMDS dan OSER10
- `rtl/fpga/gowin/tmds_rpll.v` — PLL 27 MHz ke 371.25 MHz

Kedua wrapper berhasil dikompilasi dan disintesis. Bitstream HDMI belum
tersedia: `nextpnr-himbaechel` saat ini berhenti ketika mem-pack pasangan
`TLVDS_TBUF` pada GW2AR-18C (`pack_io.cc:533`). Karena itu jangan menjalankan
target flash HDMI; target UART di atas tetap merupakan jalur board yang
terverifikasi.

## E1 — frekuensi maksimum

Bukan program. Naikkan batasan clock pada langkah place-and-route sampai gagal:

```bash
make bitstream FREQ=27    # naikkan bertahap
```

Ini satu-satunya angka yang belum ada sama sekali. Simulasi tidak punya konsep
tunda propagasi, jadi lintasan 86 tingkat itu belum pernah diberi satuan waktu.

## Yang tidak dibuktikan papan ini

Tidak ada µm², tidak ada mW, tidak ada timing ASIC — LUT bukan sel standar.
`hcpu_dataram` MPW menjadi BSRAM di FPGA dan selesai; di ASIC 131.072 bit masih
menunggu makro SRAM, dan itu tetap alasan klaim kesiapan ditahan.
