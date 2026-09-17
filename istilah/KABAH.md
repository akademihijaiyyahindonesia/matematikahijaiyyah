# Ka'bah: lima lapis dan pipeline spons

`Ka'bah` sendiri ada di [`teknologi/ISTILAH.md`](../teknologi/ISTILAH.md).
Yang di sini adalah nama-nama di dalamnya — dan satu peringatan yang harus
dibaca sebelum yang lain.

> **Hanya Lapis 3 yang memikul keamanan.** `cosmictera/RULES.md` R10
> menegakkannya. Empat lapis lain punya tugas nyata, tetapi tak satu pun boleh
> dibaca sebagai jaminan kriptografis.

---

## Lima lapis

Dibaca dari `kabah/SUBSYSTEM.md`, yang menamai tiap lapis beserta berkasnya:

| | nama | tugas | di mana |
|---|---|---|---|
| **Lapis 0** | Canonical | bentuk record yang dikunci | `crypto/guarded_record.py` |
| **Lapis 1** | Guard | menolak masukan malformed dalam O(1), **tanpa kunci** | `core/guards.py` · `rtl/hijaiyyah_jamrah_gate.v` |
| **Lapis 2** | Absorption | spons menyerap byte ke dalam keadaan | `crypto/cube.py` |
| **Lapis 3** | Authentic | HMAC-SHA256 — **satu-satunya pemikul keamanan** | `crypto/` |
| **Lapis 4** | Confidential | AES-256-GCM | `crypto/` |

**Lapis 1 triase, bukan otoritas.** Ia tidak punya kunci, jadi siapa pun bisa
membuat byte yang lolos. Terukur: menolak 41,2% pembalikan satu-bit dan 100%
byte acak, satu clock per byte.

---

## Pipeline, tujuh tahap

`kabah/FLOW.md` menggambarkannya dengan angkanya:

| tahap | istilah | terukur |
|---|---|---|
| ① | **penemuan fase** | histogram **indeks koinsidensi** 256 bin — perangkat lunak, sekali per aliran |
| ② | **deserialisasi** | 8 clock/byte → 383 byte · **BOTTLENECK**, 3,3× biaya spons |
| ③ | **gerbang jamrah** | 1 huruf digerbangi |
| ④ | **pencacah node** | 5 jendela diklasifikasi |
| ⑤ | **perakitan lajur** | 47 **lajur** **cincin luar** |
| ⑥ | **permutasi** | 2 × 310 clock = 622 **tertahan** · 112 **denyut impulser** |
| ⑦ | lapis 3 | perangkat lunak, **bukan RTL** |

---

## Kosakata spons

| istilah | arti | di mana |
|---|---|---|
| **spons** | konstruksi serap-peras; keadaan 25 lajur | `crypto/cube.py` |
| **lajur** | satu kolom keadaan spons; 25 seluruhnya, 47 di cincin luar | `crypto/cube.py` |
| **cincin luar** | lajur yang dirakit tiap putaran | `kabah/FLOW.md` |
| **absorpsi** | memasukkan byte ke keadaan | `crypto/cube.py` |
| **permutasi** | fungsi putaran; **bukan permutasi** menurut ukurannya sendiri | `3ccf193` |
| **impulser** | pembangkit denyut yang menggerakkan putaran | `rtl/hijaiyyah_*.v` |
| **denyut** | satu pulsa impulser; 112 per permutasi | `kabah/FLOW.md` |
| **deserialiser** | pengubah bit-serial ke byte, 8 clock/byte | `kabah/SILICON.md` |
| **S-box** | **logika, bukan tabel** — diturunkan, tidak disalin | `crypto/cube.py` · `kabah/SILICON.md` |
| **SLICE_BYTES** | berapa byte diserap per irisan | `rtl/scripts/` |
| **komitmen kunci** | *key commitment* | `kabah/SUBSYSTEM.md` |
| **HKDF** | derivasi kunci, RFC 5869 | `crypto/` |

---

## Dua angka yang dikoreksi oleh pengukuran

**Permutasinya bukan permutasi.** `3ccf193` — Ka'bah menyerang dirinya sendiri
dan menemukan rank 1276/1600. Sifat yang diasumsikan, lalu diukur, lalu gugur.

**Throughput 2,59 MB/s, bukan 11,15.** `49fb3b3` — dan yang menahannya
**deserialiser bit-serial**, bukan sponsnya. Delapan clock per byte, dan itu
3,3× biaya permutasi yang selama ini disangka penghambatnya.

Keduanya ada di sini karena kamus yang mencatat nama tanpa mencatat koreksinya
akan membuat orang berikutnya mengulang asumsi yang sama.

---

Dijangkarkan oleh `tests/test_integrity/test_kabah_folder.py`,
`test_sbox_logic.py`, dan `test_istilah.py`.
