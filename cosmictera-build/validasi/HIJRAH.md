# Validasi Hijrah — Tang Nano 20K

**20 September 2026.** Laporan validasi kedua dari kerangka laboratorium
pemilik, sesudah [Jamrah](JAMRAH.md). Sasarannya sederhana dan ditetapkan
pemilik: **Python lawan Tang Nano 20K**, dan kalau sama, fondasi matematikanya
tervalidasi di perangkat keras.

## Apa yang divalidasi

HIJRAH (Hijaiyyah Injection Raw Hertz, [`hijrah/`](../../hijrah/README.md))
mengukur berapa banyak yang dibawa satu huruf **sebagai operator**. Muka 5×5
setiap huruf dibaca sebagai peta linier, direduksi mod p, dan dihitung berapa
peta berbeda yang bisa dicapai kata-kata dari muka itu. Logaritma hitungan itu
dibagi panjang kata adalah bit per huruf; `log₂28 = 4,81` langit-langitnya.

Di papan, HCPU menghitungnya **sendiri dari ROM-nya**: ke-28 muka dibangun
dengan `HLOAD`, `CGET`, `CU`, dan `CRHO` — opcode codex yang sudah terbukti di
papan — dalam tata letak `src/hijaiyyah/core/exomatrix.py`. Program:
`rtl/programs/hijrah_sweep.hasm`, 356 kata.

## Hasil — tiga lari dari tiga, identik sampai ke siklusnya

| | yang dihitung papan | Python | |
|---|---|---|---|
| muka | 700 nilai, 28 × 25 | `build_exomatrix` | **700/700** |
| panjang 1, mod 2 / 3 / 4 / 5 | **24 / 27 / 28 / 28** | 24 / 27 / 28 / 28 | sama |
| pasangan runtuh, mod 2 | **ح–ل, ش–ن, ص–ق, ع–ي** | empat pasang `test_hijrah.py` | sama |
| pasangan runtuh, mod 3 | **س–ش** | satu pasang | sama |
| panjang ≤ 2, mod 2 / 3 / 4 / 5 | **321 / 649 / 625 / 714** | `_reachable(p, 2)` | sama |

Kepadatan yang mengikuti dari hitungan itu, `log₂(hitungan) / panjang`:

| | mod 2 | mod 3 | mod 4 | mod 5 | aliran bit |
|---|---:|---:|---:|---:|---:|
| panjang 1 | 4,58 | 4,75 | 4,81 | 4,81 | 1,00 |
| panjang 2 | 4,16 | 4,67 | 4,64 | 4,74 | 1,00 |

Papan membuktikan **hitungannya**; logaritma dikerjakan host atas angka yang
sudah harus benar dulu.

**Kenapa empat pasang itu runtuh atas mod 2** sudah dibuktikan tes Hijrah dan
kini terlihat dari silikon: di setiap komponen tempat kedua huruf berbeda,
bedanya persis 2 — dan 2 lenyap mod 2. Membaca huruf mod 2 adalah membacanya
sebagai bit, dan harganya empat huruf.

## Biaya — mod 5 tanpa instruksi bagi

ISA ini tidak punya instruksi bagi; reduksi mod p dikerjakan dengan pengurangan
berulang. Diukur dengan pencacah bebas 0xFF4, per modulus:

| | membentuk 784 hasil kali | per sel | menghitung 812 peta |
|---|---:|---:|---:|
| mod 2 | 1.372.431 clock | 70,02 | 3.892.436 clock |
| mod 3 | 1.377.012 clock | 70,26 | 5.203.695 clock |
| mod 4 | 1.380.378 clock | 70,43 | 5.147.558 clock |
| mod 5 | 1.384.176 clock | **70,62** | 5.191.206 clock |

Mod 5 hanya **0,86%** lebih mahal dari mod 2: sel hasil kali paling besar
5·(p−1)² = 80, jadi pengurangannya pendek. Untuk skala ini **tidak ada alasan
menambah instruksi bagi** — dan dengan aturan pemilik, yang bisa dibayar dengan
instruksi tidak dibayar dengan LUT4. Yang mahal bukan mod-nya, melainkan
membandingkan 812 peta satu sama lain, O(n²).

## Yang tidak muat di papan ini, terukur

**Panjang 3.** Atas mod 5 ia mencapai 16.359 peta berbeda; dipadatkan tiga kata
per peta, itu ±49.000 kata, sementara memori data 4.096 kata. README Hijrah
mengutip panjang 3 dan 5; keduanya tetap hasil Python, dan tempatnya di KV260.

## Satu hal yang harus dicatat, bukan dirapikan

`hijrah/README.md` memberi kolomnya label **GF(4)**, dan tesnya menghitung
**mod 4**. Keduanya bukan benda yang sama: bilangan bulat mod 4 bukan lapangan —
di sana 2·2 = 0, dan 2 tidak punya invers — sedangkan GF(4) adalah lapangan
empat unsur yang dibangun lain. Angka yang divalidasi di sini adalah **mod 4**,
persis seperti tes dan Python-nya menghitung. Label mana yang benar adalah
keputusan pemilik; laporan ini menyebut "mod 4" di mana ia mengukur mod 4.

## Kesalahan saya sendiri yang ditangkap sebelum papan

Versi pertama program dan pembandingnya **sama-sama** menghitung 784 hasil kali
panjang 2 saja, dan sepakat sempurna: 305 / 630 / 605 / 694. Hijrah menghitung
**kumulatif** — kata panjang 1 **atau** 2 — dan angka yang benar 321 / 649 /
625 / 714. Ketahuan karena hitungan itu dicocokkan dengan pengukuran
`_reachable` yang dibuat lebih dulu dan terpisah, bukan dengan pembandingnya
sendiri. Sekarang PACK1 diletakkan tepat di depan PROD sehingga keduanya
dihitung sebagai satu himpunan, dan
`tests/test_integrity/test_hijrah_board.py` mengikat acuan alat ini ke
`_reachable` milik `test_hijrah.py`.

## Mengulanginya

```bash
python3 rtl/scripts/hijrah_board.py                                  # interpreter
make -C rtl/fpga/gowin bridge                                        # loader di papan
python3 rtl/scripts/hijrah_board.py /dev/tty.usbserial-<port>        # papan
python3 -m pytest -q tests/test_integrity/test_hijrah_board.py       # lab-nya sendiri
```
