# CosmicTera

> **Bahan sama. Racikan dan rumus caranya berbeda.**

Itu seluruh tesisnya, dan itu juga batasnya. CosmicTera tidak menemukan
primitif kriptografis baru. Ia memakai bahan yang sudah dimiliki semua orang —
lapangan `GF(2⁸)` yang sama dengan AES, konstruksi spons yang sama dengan
Keccak, LUT4 yang sama di silikon, HMAC‑SHA256 yang sama dari standar. Yang
berbeda adalah **bagaimana bahan itu diracik**: bagaimana keadaan dibaca,
bagaimana lipatan dilakukan, apa yang menentukan iramanya, dan apa yang
disegel.

Sistem yang mengklaim primitif baru harus membuktikan primitifnya. Sistem yang
mengklaim racikan baru harus membuktikan racikannya — dan itu klaim yang jauh
lebih kecil, jauh lebih bisa diuji, dan karena itu jauh lebih jujur.

---

## Bahan yang sama

| Bahan | Dari mana | Dipakai apa adanya |
|---|---|---|
| `GF(2⁸)`, polinomial `0x12B` | lapangan hingga standar | ya |
| Inversi lewat menara `GF((2⁴)²)` | teknik Canright untuk S‑box AES | ya |
| Konstruksi spons | Keccak / SHA‑3 | ya |
| HMAC‑SHA256 | RFC 2104 / FIPS 198 | ya, dari pustaka teruji |
| HKDF | RFC 5869 | ya, lolos vektor terbitannya |
| LUT4 | primitif FPGA | ya |

Tidak ada satu pun di kolom kiri yang diklaim sebagai temuan. Kalau ada yang
harus dipercaya di sini, itu bukan bahannya.

## Racikan yang berbeda

| | Cara lazim | Cara CosmicTera | Akibatnya |
|---|---|---|---|
| **Keadaan** | vektor datar 1600 bit | kubus dibaca sebagai **cincin luar 16 lajur + inti 9 lajur** | pemisahan rate/capacity jadi *geometri*, bukan aturan yang ditegakkan |
| **Masukan** | byte per clock | **aliran bit**; batas byte harus *ditemukan*, bukan diasumsikan | 8 clock per byte, dan front end jadi bottleneck |
| **Irama** | clock bebas berjalan | impulser **berhenti pada `stall`**, maju saat spons butuh permutasi | biayanya konstan per data, bukan per detik |
| **Keluaran** | keadaan mentah | **wakil kanonik** dari orbit rotasi | lipatan menghasilkan orbit; rotasi menjadikannya nilai |
| **Segel** | menutup data | menutup **setiap penentu**, termasuk RTL yang menghitungnya | mengubah satu berkas RTL tidak lagi lolos diam‑diam |

---

## Mekanisme dan rangkumannya

Struktur CosmicTera **bukan** tiga prinsip sejajar. Ia satu mekanisme dan satu
rangkuman:

> **Lipatan** (bit → clock → tera) **dirangkum oleh rotasi.**
> Pemecahan node adalah *bagaimana* lipatan itu dilakukan — bukan prinsip
> ketiga.

Empat bagiannya tidak berdiri sendiri, dan itu yang membuatnya satu sistem:

- **Lipatan tanpa rotasi** menghasilkan orbit, bukan nilai. Tiga geseran
  memberi tiga laporan, dan orbit tidak bisa disegel.
- **Rotasi tanpa tera** hanya kenyamanan. Pada skala kecil, determinisme bisa
  dicapai dengan mengulang.
- **Tera tanpa impulser data‑driven** tak punya satuan. Biaya per detik
  berubah dengan clock; biaya per terabit tidak.
- **Semuanya tanpa segel** hanya perhitungan.

Dan alasan **tera** menjadi satuannya bukan karena besar terdengar mengesankan:
pada 107 jam per terabyte, **"jalankan lagi" bukan lagi verifikasi.**
Determinisme harus struktural, bukan empiris.

---

## Isi folder ini

| Berkas | Isi |
|---|---|
| [`RULES.md`](RULES.md) | Aturan yang mengikat. Setiap aturan punya bekas luka — insiden yang melahirkannya. |
| [`SYSTEM.md`](SYSTEM.md) | Penjelasan sistem teknis: geometri, lipatan, rotasi, impulser, segel. |
| [`CONCRETE.md`](CONCRETE.md) | Penjelasan konkret lengkap: jalur satu aliran dari bit sampai segel, dengan setiap angka dan asalnya. |
| [`COMPUTING.md`](COMPUTING.md) | Apa itu "Cosmictera Computing" secara program: empat program nyata (HCPU, Ka'bah, tumpukan tujuh lapis, NUI) dan disiplin yang sama-sama mereka taati. |
| [`CODEX.md`](CODEX.md) | Bab I & II buku *Matematika Hijaiyyah* dipetakan ke modul kode (`core/`, `algebra/`, `skeleton/`) dan tes yang memverifikasinya — lapis matematika di bawah keempat program itu. |

Angka di ketiganya diikat oleh
[`tests/test_integrity/test_cosmictera_docs.py`](../tests/test_integrity/test_cosmictera_docs.py).
Dokumen yang menyimpang dari kode adalah dokumen yang berbohong, dan di sini ia
menggagalkan tes.

---

## Batas, dinyatakan di depan

- **Lapis 3 (HMAC‑SHA256) satu‑satunya pemikul keamanan.** Lapis 0–2 adalah
  kanonikalisasi dan triase tanpa kunci; mereka tidak membuktikan apa pun
  tentang asal‑usul.
- **Spons berlabel [EH]** — terukur, belum dikriptanalisis. Tidak ada klaim
  keamanan yang bertumpu padanya.
- **Lapis 4 ditolak.** Untuk kerahasiaan, pakai AES‑256‑GCM dari pustaka
  teruji.
- **Fmax HCPU [CC].** Tang Nano 20K menjalankannya: **14.005 LUT4 (67%),
  4.480 DFF (28%), 17 BSRAM, Fmax 118,43 MHz pasca-perutean**, dan UART
  membalas 23 byte yang cocok byte-per-byte dengan simulasi. Ka'bah terpisah
  juga terukur: **12.061 LUT4 (58%), Fmax 165,98 MHz**.
- **HCPU dan Ka'bah tidak perlu jadi satu top level.** Digabung, keduanya
  diukur **105% — lewat 960 sel** — tapi tak ada yang menuntut keduanya
  menempati fabric bersamaan. Papan memuatnya sebagai **slot bitstream
  berurutan** (`rtl/scripts/rack.py`), jadi biaya rack adalah slot
  terbesar, 67%, bukan jumlahnya. Modul Ka'bah mentah tetap tak bisa
  ditempatkan: 1.665 bit port melawan 384 IOB. Yang berjalan di papan
  adalah wrapper-nya.
