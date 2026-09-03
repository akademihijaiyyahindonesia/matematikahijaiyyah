# Ka'bah

**K**riptografi **A**bsorpsi **B**yte **A**tas **H**ijaiyyah — lima lapis, dan
**hanya satu yang memikul keamanan**.

Itu kalimat pertama karena ia yang paling sering salah dibaca. Empat lapis
lainnya berguna, terukur, dan **tidak membuktikan apa pun tentang asal‑usul**.

```
  0  Canonical      DP           satu bacaan per nilai; tanpa ambiguitas parsing
  1  Guard          CC           menolak masukan malformed dalam O(1), tanpa kunci
  2  Absorption     EH           spons tawaf, S-box kelas AES, kapasitas 288 bit
  3  Authentic      VF  kunci    HMAC-SHA256 atas kunci terikat segel   ← SELURUHNYA
  4  Confidential   —   kunci    DITOLAK — pakai AES-256-GCM dari pustaka teruji
```

**Lapis 3 adalah keamanannya**, dan lapis 3 adalah HMAC-SHA256 standar — bukan
temuan. Lapis 2 berlabel **[EH]**: terukur, belum dikriptanalisis. Tidak ada
klaim yang bertumpu padanya.

---

## Kenapa ia ada

Bukan karena "lebih cepat" atau "lebih aman" secara umum. **Satu celah spesifik**,
dan serangannya dijalankan di suite ini — bukan diceritakan.

| | AES-GCM | Ka'bah lapis 3 |
|---|---|---|
| Autentikasi | ya | ya |
| **Komitmen kunci** | **tidak** | **ya** |
| Biaya kunci kedua | ~0 — aljabar | 2²⁵⁶ — pencarian |

Satu ciphertext bisa dibuat sah di bawah **dua kunci berbeda** di GCM. Itu bukan
kelemahan pada AES — itu aljabar polinomial GHASH sendiri: satu persamaan
linear, dua variabel, pilih satu koefisien bebas dan yang lain keluar dari satu
inversi lapangan.

Lapis 3 **tidak punya persamaan untuk diselesaikan.**

---

## Isi folder

| Berkas | Isi |
|---|---|
| [`SUBSYSTEM.md`](SUBSYSTEM.md) | Setiap subsistem: tugasnya, di mana ia hidup, berapa biayanya |
| [`FLOW.md`](FLOW.md) | Cara kerjanya — perjalanan satu byte dari kabel sampai rekaman tersegel |
| [`SILICON.md`](SILICON.md) | Apa yang di perangkat keras, apa yang perangkat lunak, dan angkanya |

Spesifikasi kriptografisnya ada di [`docs/kabah/SPEC.md`](../docs/kabah/SPEC.md);
perbandingan terhadap celah nyata di
[`docs/kabah/GAPS.md`](../docs/kabah/GAPS.md). Folder ini melengkapi keduanya
dengan pandangan **sistem**, bukan mengulanginya.

Dijangkar oleh
[`test_kabah_folder.py`](../tests/test_integrity/test_kabah_folder.py),
[`test_crypto.py`](../tests/test_integrity/test_crypto.py),
[`test_guarded_record.py`](../tests/test_integrity/test_guarded_record.py),
[`test_examine.py`](../tests/test_integrity/test_examine.py) dan
[`test_program.py`](../tests/test_integrity/test_program.py).

---

## Parameter, sekali saja

| | |
|---|---:|
| Keadaan spons | 25 × 64 = **1600 bit** |
| Rate | **128 byte** (1024 bit) |
| Kapasitas | **576 bit** → keamanan **288 bit** |
| Cincin luar / inti | **16 / 9** lajur |
| Ronde | **28** = 7 CIRCUIT × 4 TAWAF |
| Polinomial S-box | `0x12B`, afin `0xE7` |
| Orde ρ·π | **768** = 12 × 64 — 27,4× di atas jumlah ronde |
