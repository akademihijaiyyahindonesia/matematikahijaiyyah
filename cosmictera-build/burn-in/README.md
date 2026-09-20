# Burn-in — catatan per lari

**Prioritas 6 pemilik**, dibuka 20 September 2026 sesudah lab serangan tutup.
Pertanyaannya satu, dan simulasi tidak bisa menjawabnya: *"apakah sistem ini
stabil berjalan terus-menerus?"*

Pemilik menetapkan tiga tingkat — **24 jam**, **72 jam**, **168 jam** — dan apa
yang harus dibuktikan tingkat pertama: tidak ada deadlock, tidak ada korupsi
memori, tidak ada watchdog timeout, tidak ada serial yang menggantung.

**Satu dari keempatnya tidak bisa diukur di papan ini, dan itu dikatakan di
muka: tidak ada watchdog.** Tidak ada modul semacam itu di `rtl/`, dan lab ini
tidak berpura-pura menjadi satu. Mesin yang berhenti tidak bisa melaporkan
bahwa ia berhenti; yang bisa diukur adalah **diamnya**, dan itulah yang
dicatat host sebagai jarak antar detak.

## Apa yang dikerjakan papan

`rtl/programs/burn_in.hasm` (332 kata), dikirim lewat `loader.hasm`. Satu
siklus, berulang:

| | yang dikerjakan | yang akan tertangkap |
|---|---|---|
| 1 | gerbang Jamrah atas ke-256 byte, pulse dan ketujuh simpul dijumlah | ALU yang hanyut, bit macet di berkas register, shift yang berhenti menggeser |
| 2 | ke-28 vektor codex dibaca dari ROM (`HLOAD`, `CGET`, `CU`, `CRHO`), dijumlah | ROM yang bacaannya melapuk |
| 3 | enam belas kata memori data, ditulis sekali lalu dibandingkan tiap siklus | **korupsi memori** |
| 4 | satu `PUSH` dan satu `POP` | tumpukan, yang hidup di luar memori data dan tak terlihat oleh 1–3 |
| 5 | sektor 1 kartu, dibaca, kata pertamanya dibandingkan | jalur SDIO, satu-satunya kabel ke perangkat fisik |

Kartu **dibaca, tidak pernah ditulis**: menulis tiap siklus selama seminggu
adalah uji keausan kartu, bukan uji mesin ini.

**Tidak ada yang dibandingkan dengan konstanta yang dirakit ke dalam citra**,
karena konstanta yang salah melaporkan cacat yang tidak ada. Siklus pertama
**menyimpan** apa yang ia hasilkan; setiap siklus sesudahnya membandingkan
terhadap salinan itu. Siklus pertama juga **mencetak** tujuh angka, dan tiga di
antaranya punya jawaban dari luar papan:

```
28    huruf 1..28          rtl/tb/jamrah_vectors.txt
3072  tiga tingkat pohon    tiap tingkat menjumlah 1.024 bit yang menyala di 256 byte
178   theta + U + rho       Master Table
```

Ketiganya cocok di papan pada lari pertama.

## Dua pencacah, karena dua hal berbeda

**errors** menghitung nilai yang berselisih dengan yang mesin ini sendiri
hasilkan lebih dulu. **sd failures** menghitung pembacaan yang tidak
diselesaikan kartu. Mencampurnya akan membuat kartu yang sedang tidak enak
badan terbaca sebagai korupsi memori — dan kriteria tingkat pertama justru
tentang yang kedua.

## Detak

Tiap 1.024 siklus: huruf `H`, lalu enam angka — detak, errors, sd failures,
putaran pencacah, pencacah >> 12, status kartu. Host mengalikan kembali.

**Angka besar tidak dikirim utuh, dan alasannya terukur**: `PRINT` mencetak
nilai besar dengan salah di papan ini — tangga `2^0..2^31` benar sampai
4.194.304 lalu mulai mengeluarkan karakter **di atas `'9'`. Rinciannya di
[OFF.md](../OFF.md). Program ini menjaga tiap angkanya di bawah sejuta.

Pencacah 0xFF4 32-bit pada 27 MHz berputar tiap **159,07 detik** — ±543 kali
dalam 24 jam — jadi uptime adalah putaran dan pencacah bersama-sama. Papan
menghitung putarannya sendiri, host menyimpan jamnya sendiri di sebelahnya,
dan keduanya harus tetap sejalan.

## Lari

| lari | tingkat | hasil |
|---|---|---|
| `20260920T013538Z-burn-in-24h` | 24 jam | **sedang berjalan** sejak 20 September 2026 01:35 UTC |

Tingkat 72 jam dan 168 jam belum dijalankan.

## Dua temuan dari membangun lab ini

Keduanya dicatat penuh di [OFF.md](../OFF.md), keduanya **dilaporkan bukan
diperbaiki** (K9):

1. **`PRINT` salah untuk angka besar** — 2²³ kembali sebagai `8388600`, dan dari
   2²⁵ ke atas muncul karakter `:` sampai `?`, yaitu nilai digit 10–15.
2. **Kartu gagal init sesudah rekonfigurasi di tengah pembacaan** — delapan
   peluncuran dari delapan, berselang-seling. Satu percobaan gagal berharga
   ±3,3 detik, jadi lari yang kartunya tak naik merangkak; `burn_in.hasm`
   karena itu menyerah sesudah delapan percobaan dan `burn_in.py` meluncurkan
   ulang.

Keduanya ditemukan karena lab ini dijalankan di papan sebelum dipercaya sehari
penuh — bukan karena dibaca dari kode.

## Mengulanginya

```bash
python3 rtl/scripts/burn_in.py                                   # rencananya saja
python3 rtl/scripts/burn_in.py --port /dev/tty.usbserial-<port> --hours 24 --label 24h
python3 -m pytest -q tests/test_integrity/test_burn_in.py
```

Alat ini memuat bitstream slot CPU sendiri dan meluncurkan ulang kalau kartu
tidak naik. Sesudah program terkirim **papan tidak membutuhkan host**: kalau
host pergi, yang hilang catatannya, bukan larinya.

Catatan ditulis ke `<id>.jsonl` — tiap detak yang menaikkan pencacah kesalahan,
tiap diam di atas ambang, dan satu contoh per menit — dan ringkasan `<id>.json`
ditulis ulang **tiap menit**, bukan hanya di akhir: lari berhari-hari tidak
boleh kehilangan vonisnya karena host ditutup di menit terakhir.
