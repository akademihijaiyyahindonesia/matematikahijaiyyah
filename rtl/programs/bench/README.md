# Percobaan Tang Nano 9K

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

Contoh terverifikasi: `test_bsm.hasm` pensiun 9 instruksi dalam **14 siklus**.
Selisih 5 itu isi pipeline lima-tahap — persis yang tidak bisa dilihat oleh
hitungan instruksi statis di `tools/integrity_benchmark.py`.

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

## E1 — frekuensi maksimum

Bukan program. Naikkan batasan clock pada langkah place-and-route sampai gagal:

```bash
make bitstream FREQ=27    # naikkan bertahap
```

Ini satu-satunya angka yang belum ada sama sekali. Simulasi tidak punya konsep
tunda propagasi, jadi lintasan 86 tingkat itu belum pernah diberi satuan waktu.

## Yang tidak dibuktikan papan ini

Tidak ada µm², tidak ada mW, tidak ada timing ASIC — LUT bukan sel standar.
`hcpu_dataram` menjadi BSRAM di FPGA dan selesai; di ASIC 131.072 bit masih
menunggu makro SRAM, dan itu tetap alasan klaim kesiapan MPW ditahan.
