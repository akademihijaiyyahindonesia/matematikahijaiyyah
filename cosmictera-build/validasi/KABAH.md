# Validasi Ka'bah — Tang Nano 20K

**20 September 2026.** Laporan validasi ketiga, sesudah [Jamrah](JAMRAH.md) dan
[Hijrah](HIJRAH.md). Pemilik menetapkan sasarannya berbeda dari dua yang
pertama: bukan lagi *"apakah hasilnya keluar"*, melainkan **sifat-sifatnya** —
avalanche, tabrakan, integritas di bawah bit-flip, mutasi, dan perilaku replay.

## Batas klaim, dinyatakan lebih dulu

Yang diukur di sini adalah **lapis 2**, spons Tawaf, dan `cube.py` sendiri
menandainya **[EH]**: *"not a vetted hash — use hashlib.sha256 for anything
that matters"*. Yang memikul keamanan di Ka'bah adalah **lapis 3**,
HMAC-SHA256 standar. Tidak satu pun angka di halaman ini klaim keamanan; semua
ini pengukuran difusi sebuah permutasi di silikon.

Avalanche spons sudah pernah diukur **di Python** — `cube.py` mencatat ~0,5 dan
menyebutnya hasil negatif terhadap jadwal absorpsi. Yang belum ada adalah
pengukuran yang sama **di papan**.

## Protokol, tidak diubah

Wrapper menerima tepat 128 byte dan menjawab 200 byte: seluruh keadaan, byte
paling berarti dulu. `load` menyala sekali sesudah reset, jadi frame yang
dikirim berurutan **berantai** menjadi satu absorpsi. Karena itu dua pesan
hanya bisa dibandingkan dari konfigurasi yang segar, dan satu percobaan
avalanche **merekonfigurasi papan di antara dua belahannya**.

Bitstream dibangun ulang dari sumber hari ini sebelum dipakai: 12.061 LUT4
(58%), 1.965 DFF, 0 BSRAM, Fmax 165,98 MHz — angka yang sama dengan catatan
rack, jadi slotnya tidak bergeser sejak terakhir diukur.

## Hasil di papan

| yang diukur | hasil |
|---|---|
| integritas berantai, 8 frame acak | **8/8 cocok dengan `cube.py`**, 200 byte tiap frame |
| replay sesudah rekonfigurasi | **identik** — mesinnya deterministik |
| frame yang sama dua kali tanpa reset | **keadaan berbeda** — spons berantai, dan memang harus |
| avalanche, 32 bit-flip tunggal | **rata-rata 0,4995** dari 1.600 bit (799,2 bit), terendah 0,4700, tertinggi 0,5275 |
| masukan termutasi | **32/32 masih cocok dengan `cube.py`** |
| keadaan yang seharusnya berbeda | **73/73 berbeda** |

**Avalanche 0,4995 di silikon** adalah angka yang sama dengan ~0,5 yang
`cube.py` ukur di Python. Satu bit yang dibalik di masukan memindahkan separuh
dari 1.600 bit keadaan.

**Yang "tabrakan" berarti di sini, dan yang tidak.** 73 keadaan berbeda adalah
pernyataan tentang 73 keadaan — bukan tentang spons. Ruang keadaannya 2¹⁶⁰⁰;
tidak ada pencarian berukuran laboratorium yang bisa mengatakan lebih. Angka
yang pantas dilaporkan adalah bahwa **tidak ada dua keadaan yang seharusnya
berbeda ternyata sama**, dan itu yang diperiksa.

**Replay punya dua jawaban, dan keduanya benar.** Sesudah rekonfigurasi, pesan
yang sama memberi keadaan yang sama persis: mesinnya deterministik. Di dalam
satu lari tanpa reset, frame yang sama dua kali memberi keadaan berbeda: spons
menyerap di atas keadaan sebelumnya. Penolakan replay yang sesungguhnya bukan
milik lapis ini — ia nonce di `guarded_record.py`, lapis 5, dan tetap perangkat
lunak.

## Mengulanginya

```bash
make -C rtl/fpga/gowin kabah_bitstream
python3 rtl/scripts/kabah_board.py                                   # tanpa papan
python3 rtl/scripts/kabah_board.py /dev/tty.usbserial-<port> --avalanche 32
python3 -m pytest -q tests/test_integrity/test_kabah_board.py        # lab-nya sendiri
```

Alat ini merekonfigurasi papan sendiri di antara percobaan; 32 percobaan
avalanche berarti 68 kali muat bitstream, ±2 menit 43 detik seluruhnya.

## Yang belum diukur, dan kenapa

- **Lapis 3 di papan.** HMAC-SHA256 adalah perangkat lunak dan tidak ada inti
  SHA-256 di RTL (R10). Papan ini tidak menjalankannya, dan tidak diklaim
  menjalankannya.
- **Serangan sungguhan.** Halaman ini mengukur difusi dan integritas, bukan
  ketahanan. Lab serangan adalah prioritas 5 pemilik, dan pemilik sendiri
  menulis alasan urutannya: *"lab serangan tanpa baseline validasi akan
  menghasilkan angka yang sulit ditafsirkan."* Baseline itu halaman ini, dan
  [lab serangan kelas C](../attack-lab/README.md) sudah berdiri di atasnya
  pada hari yang sama: mutasi 1 sampai 64 bit tetap memberi difusi ~0,5,
  permutasi blok memindahkan keadaan akhir 0,4975, dan frame terpotong
  **tidak ditolak** — wrapper tidak punya field panjang, jadi potongan
  berikutnya menyambungnya.
- **Tabrakan di luar skala laboratorium** — lihat di atas.
