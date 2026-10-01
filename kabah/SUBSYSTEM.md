# Subsistem

Ka'bah bukan satu algoritma. Ia sekumpulan bagian yang masing‑masing punya
tugas sempit, dan yang penting adalah **mana yang menanggung apa**.

---

## Lapis 0 — Canonical  `crypto/guarded_record.py`

**Tugas**: satu bacaan per nilai. Byte → huruf → byte tanpa ambiguitas.

Ini bukan kenyamanan. Parser longgar adalah kelas kerentanan tersendiri —
malleability transaksi Bitcoin, bypass tanda tangan BER/DER. Kalau satu rekaman
punya dua penyandian sah, tanda tangan atasnya tidak menutup apa pun.

**Label DP** — benar karena konstruksinya, bukan temuan.

---

## Lapis 1 — Guard  `core/guards.py` · `rtl/hijaiyyah_jamrah_gate.v`

**Tugas**: menolak masukan malformed dalam O(1), **tanpa kunci**.

Enam kendala geometris. Di silikon ia **sirkuit kombinasional, satu siklus** —
`PIPELINE_GUARD = 0`. Tanpa tabel, tanpa nilai tersimpan.

Cakupan terukur: **100% pada 16 dari 18 komponen**. Θ̂ terkunci di 11% oleh
struktur monoid, H* di 0% karena tak ada hukum yang jujur. **93,1% adalah
langit-langitnya**, bukan kekurangan — lihat
[`matematika-hijaiyyah/GUARD.md`](../matematika-hijaiyyah/GUARD.md).

**Ia tidak membuktikan apa pun tentang asal-usul.** Ia menolak sampah dengan
murah supaya jalur mahal tidak terbuang.

---

## Lapis 2 — Absorption  `crypto/cube.py` · `rtl/hijaiyyah_sponge.v`

**Tugas**: menyerap byte ke keadaan 1600 bit dan mengaduknya.

| bagian | berkas | catatan |
|---|---|---|
| Substitusi | `sbox_logic.py` · `hijaiyyah_sbox.v` | GF(2⁸), menara Canright, DU 4, NL 112, 0 titik tetap |
| Lapisan linear | `hijaiyyah_linear.v` | dihasilkan dari `cube.py` |
| Permutasi | `hijaiyyah_rotate_core.v` | π terurai `[12,12,1]`; **lajur 0 tetap** |
| Konstanta ronde | `hijaiyyah_round_constants.v` | 28, dari digest kubus tersegel |

**Lajur 0 tetap adalah tempat konstanta ronde masuk** — `s[0] ^= RC[circuit]`.
Kalau tidak, lajur yang tak bergerak jadi jalur yang tak pernah teraduk.

Geometrinya menanggung pemisahan rate/capacity: masukan hanya menyentuh **16
lajur cincin luar**; **9 lajur inti** tak pernah tersentuh langsung. Itu
geometri, bukan pemeriksaan indeks yang bisa dilewati.

**Label EH.** Terukur, belum dikriptanalisis.

---

## Lapis 3 — Authentic  `crypto/signing.py`

**Tugas**: membuktikan asal-usul. **HMAC-SHA256 atas kunci terikat segel.**

Tag 256 bit penuh, tanpa polinomial dan tanpa koefisien untuk diselesaikan.
Diukur pada lebar tag yang sengaja dipotong: biaya pencarian mengikuti 2ⁿ —
kalau ada pintasan aljabar, tag 20 bit akan jatuh jauh di bawah 2²⁰. Tidak.

Kunci diturunkan lewat **HKDF RFC 5869**, dan primitifnya **lolos vektor
terbitannya** — pemeriksaan tambahan diletakkan di batas sistem, bukan di dalam
primitif, karena kasus uji 1 memakai `0x0b × 22` yang pernah ditolak oleh
pemeriksaan yang salah tempat.

**Label VF. Ini seluruh keamanannya.** Di RTL ia ada sebagai slot sendiri
(`rtl/hijaiyyah_hmac.v`, 1 Oktober 2026), tidak di jalur `hijaiyyah_kabah_top` /
`hijaiyyah_wave`; keluaran Ka'bah tetap belum terautentikasi sampai
ditandatangani.

---

## Lapis 4 — Confidential  **ditolak**

Kerahasiaan tidak disediakan, disengaja. Pakai AES-256-GCM dari pustaka teruji.

Menolak lebih jujur daripada menyediakan primitif yang belum dikriptanalisis.

---

## Subsistem penunjang

### CMASS — penemuan batas byte  `crypto/wave.py`

Aliran masuk **tanpa batas byte yang diketahui**. Batasnya ditemukan lewat
**histogram indeks koinsidensi 256 bin** — statistik *gabungan*. Statistik
marginal tidak bisa melihat batas.

Berjalan **sekali per aliran**, bukan per clock. `phase` adalah *masukan* ke
perangkat keras.

### Pencacah node  `crypto/node_counter.py` · `rtl/hijaiyyah_node_counter.v`

Menghitung per posisi bit, bukan popcount. Pencacahan per posisi **memulihkan
kunci XOR** (95% pada 1024 byte); popcount tidak bisa — ia tidak injektif pada
kunci.

### Impulser  `rtl/hijaiyyah_ramal_impulse.v`

**Tidak berjalan bebas terhadap waktu.** Ia berhenti pada `stall` dan maju
ketika spons butuh permutasi. **56 denyut per permutasi** — 28 linear, 28
substitusi.

### Pemeriksaan & segel  `crypto/program.py` · `crypto/kabah.py`

`HMF1` manifes, `HEX1` pemeriksaan. Manifes menutup **12 pola sumber sistem**
dan mengecualikan **5 produk build** yang bisa diturunkan ulang.
`check_board_hex` **merakit ulang** hex papan dari `PROGRAM` di Makefile dan
membandingkannya.

Fase pemeriksaan default **−1**, bukan 0 — "tidak ada yang melihat" harus bisa
dibedakan dari "diperiksa pada fase 0".

### Forensik  `crypto/memscan.py` · `crypto/elements.py`

Pemindaian memori dengan pemulihan kode tersuntik, dan profil unsur untuk
mengenali jenis berkas dari komposisinya. Keduanya membaca, tak satu pun
menandatangani.
