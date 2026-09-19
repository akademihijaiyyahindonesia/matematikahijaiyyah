# Lab serangan — catatan per lari

**Prioritas 5 pemilik, dibuka 20 September 2026**, sesudah ketiga lapisan punya
laporan validasi: [Jamrah](../validasi/JAMRAH.md) 256/256,
[Hijrah](../validasi/HIJRAH.md) sama dengan Python, [Ka'bah](../validasi/KABAH.md)
avalanche 0,4995. Alasan urutannya kalimat pemilik sendiri: *"lab serangan tanpa
baseline validasi akan menghasilkan angka yang sulit ditafsirkan."*

**Apa lab ini bukan.** Bukan klaim keamanan dan bukan bukti ketahanan. Ia
kumpulan masukan yang **seharusnya ditolak**, dijalankan ke mesin untuk melihat
apakah ditolak. Kasus yang diterima adalah temuan; kasus yang ditolak adalah
satu kasus, bukan jaminan.

Tiap lari menyimpan satu berkas JSON di folder ini: `attack_id`, sasaran,
jumlah masukan, jumlah ditolak, jumlah diterima, temuan, papan, bitstream, dan
tiap kasus dengan prediksinya.

## Pembangkitnya: mesin Jim, bukan RNG

`rtl/scripts/jim_stream.py` memakai satu-satunya hal yang terukur tentang huruf
Jim: mukanya sebagai peta linier adalah **LFSR panjang-maksimum**. Periodenya
diukur ulang oleh alat itu sendiri dan cocok dengan `cosmic-codex-jim/`:

```
GF(2)   periode 31
GF(5)   periode 3.124
```

`cosmic-codex-jim/LIMITS.md` mencatat tiga bacaan tentang Jim yang **gagal
terukur**, dan lab ini tidak memakai satu pun darinya. Jim dipakai sebagai
pembangkit urutan deterministik berperiode diketahui — tidak diklaim lebih baik
dari RNG, dan pertanyaan apakah urutan terstruktur menemukan yang tak ditemukan
acak adalah pertanyaan yang belum dijawab lari mana pun.

## Lari pertama — sasaran loader, 10 kasus

`20260919T225037Z-loader.json`. Container `test_from_card` @0x900 dibangun
utuh, lalu satu field dirusak per kasus, ditulis ke kartu lewat `sd_writer`,
dan papan diminta memuatnya.

| hasil | kasus |
|---|---|
| **ditolak, 8** | MAGIC dibalik, VERSION dinaikkan, WORDS = 0, LOAD_ADDR melewati memori instruksi, ENTRY di luar citra, RELOC_CNT > 128, CRC dibalik, satu kata program dibalik |
| **diterima, 2** | `words_plus_one`, `reloc_index_moved` |

**Keduanya diterima bukan karena cacat, melainkan karena memang di luar
jangkauan pemeriksaan yang ada** — dan itulah yang lab ini ada untuk
menunjukkan:

- **`words_plus_one`.** WORDS dinaikkan satu, jadi loader menjumlahkan satu
  kata tambahan dari kartu. Kata itu **nol**, padding sektor, sehingga jumlah
  32-bit tidak berubah dan citra dimuat satu kata lebih panjang.
- **`reloc_index_moved`.** Satu entri tabel relokasi diarahkan ke kata program
  lain. **Jumlah 32-bit hanya menutupi kata program** — keputusan pemilik,
  18 September — jadi tabel yang rusak lolos, dan citra direlokasi di kata yang
  salah tanpa satu pun penolakan.

Keduanya konsisten dengan spesifikasi yang berlaku; yang belum ada adalah
keputusan apakah cakupan jumlah diperluas ke header dan tabel relokasi. Itu
perubahan spesifikasi, dan **keputusan pemilik**.

## Mengulanginya

```bash
python3 rtl/scripts/attack_lab.py --target loader            # rencananya saja
python3 rtl/scripts/attack_lab.py --target loader --port /dev/tty.usbserial-<port>
python3 rtl/scripts/jim_stream.py --field 5 --bytes 32
python3 -m pytest -q tests/test_integrity/test_attack_lab.py
```

Satu lari sepuluh kasus memakan ±1 menit 17 detik; tiap kasus memuat bitstream
dua kali dan menulis ke kartu.

## Yang belum dijalankan

Kelas A (Jamrah), C (Ka'bah), dan D (aliran codex JIM) belum. Kelas A sudah
tuntas di [laporan Jamrah](../validasi/JAMRAH.md) — 256 nilai, seluruhnya —
jadi yang tersisa untuknya bukan cakupan melainkan latensi. Kelas C punya
baseline avalanche 0,4995 yang tinggal didorong dengan mutasi banyak-bit,
frame terpotong, dan frame diulang.
