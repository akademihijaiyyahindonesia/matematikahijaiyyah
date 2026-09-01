# Celah yang ditutup, dan celah yang masih terbuka

Sistem baru hanya layak dibangun kalau ia menutup sesuatu yang masih
menganga di sistem yang sudah ada. Itu klaim tentang **sistem lain**, jadi
tidak boleh diasumsikan — harus diuji terhadap sistem itu sendiri. Dokumen
ini memuat daftar kegagalan kriptografi yang punya nama, punya korban, dan
punya publikasi; untuk setiap baris disebutkan apa yang Ka'bah lakukan dan
tes mana yang menahannya.

Semua tes ada di `tests/test_integrity/test_known_failure_modes.py`.

---

## 1. Komitmen kunci — celah yang **masih terbuka** di AES-GCM

Ini baris yang paling penting, karena di sini yang dibobol bukan sistem
mainan melainkan AEAD yang mengangkut hampir seluruh lalu lintas TLS dunia.

**Cacatnya.** AES-GCM dan ChaCha20-Poly1305 mengautentikasi, tetapi tidak
*berkomitmen* pada kunci. Satu ciphertext bisa membawa tag yang sah di bawah
dua kunci berbeda, keduanya dipilih penyerang. Ini bukan soal brute force:
GHASH adalah polinomial dalam kunci atas GF(2^128), jadi kunci kedua
**diselesaikan secara aljabar**, dalam mikrodetik.

**Bukan hipotesis.** Partitioning oracle attack yang memulihkan kata sandi
Shadowsocks (Len, Grubbs, Ristenpart, 2021); pemalsuan laporan
penyalahgunaan terhadap message franking Facebook (Dodis, Grubbs,
Ristenpart, Woodage, 2018); dan itulah sebabnya IETF sekarang membakukan
AEAD yang committing.

**Serangannya dijalankan di suite ini**, bukan diceritakan. `tools/commitment_attack.py`
menyusun ciphertext 32 byte dan tag 16 byte yang sah di bawah dua kunci acak:

```
c1·(H₁³ ⊕ H₂³) ⊕ c2·(H₁² ⊕ H₂²) ⊕ L·(H₁ ⊕ H₂) ⊕ S₁ ⊕ S₂ = 0
```

Satu persamaan linear, dua variabel. Pilih `c1` bebas, `c2` keluar dari satu
inversi lapangan. Tanpa pencarian, tanpa oracle, tanpa kelemahan pada AES.

**Yang Ka'bah lakukan.** Lapis 3 adalah HMAC-SHA256 atas seluruh rekaman
dengan tag 256 bit penuh. Tidak ada polinomial, tidak ada koefisien untuk
diselesaikan — satu-satunya jalan adalah pencarian 2²⁵⁶. Diukur, bukan
diklaim: pada lebar tag yang sengaja dipotong, biaya pencarian mengikuti 2ⁿ.
Kalau ada pintasan aljabar, tag 20 bit akan jatuh jauh di bawah 2²⁰. Tidak.

| | AES-GCM | Ka'bah lapis 3 |
|---|---|---|
| Autentikasi | ya | ya |
| **Komitmen kunci** | **tidak** | **ya** |
| Biaya kunci kedua | ~0 (aljabar) | 2²⁵⁶ (pencarian) |

Tes: `test_the_field_used_to_break_gcm_is_gcms_own`,
`test_one_ciphertext_authenticates_under_two_gcm_keys`,
`test_the_forgery_needs_the_polynomial_not_a_weak_cipher`,
`test_kabah_has_no_equation_to_solve`.

> Catatan kejujuran: lapangan GF(2^128) tidak diverifikasi dengan vektor uji
> yang saya ingat — versi pertama gerbang ini membandingkan dengan konstanta
> SP 800-38D dari ingatan, satu byte-nya salah, dan gerbang itu menembak
> penulisnya sendiri. Yang dipakai sekarang adalah hukum yang mendefinisikan
> lapangan itu: `x^128 = x^7 + x^2 + x + 1`. Tidak ada lapangan lain yang
> memenuhinya.

---

## 2. Debian OpenSSL, 2008 — kunci yang bukan kunci

**Cacatnya.** Dua tahun lamanya Debian menerbitkan kunci dari ruang 15 bit,
dan tidak ada kode pemakai yang menyadarinya, sebab kunci lemah terlihat
persis seperti kunci kuat.

**Batas yang jujur.** Entropi **tidak bisa** diperiksa setelah fakta. Diberi
32 byte, tidak ada uji yang memisahkan keluaran CSPRNG dari generator yang
sudah dikompromikan. Modul yang mengaku bisa sedang menjual jaminan palsu.

**Yang bisa diperiksa** adalah kasus degenerat — semua nol, semua 0xFF, isian
konstanta apa pun — yaitu yang benar-benar dihasilkan oleh buffer tak
terinisialisasi, pembacaan terpotong, atau placeholder yang tertinggal di
berkas konfigurasi. Kunci acak 32 byte memicunya dengan peluang 2⁻²⁴⁸.

Pemeriksaan berjalan di **batas tempat kunci masuk** — `seal_record`,
`Kabah.__init__`, pemuat kunci CLI — dan sengaja **tidak** di `derive_key`.
RFC 5869 kasus uji 1 memakai IKM berupa 0x0b diulang 22 kali; primitif yang
menolak isian konstanta tidak bisa diuji terhadap standar yang ia
implementasikan. Menaruh pemeriksaan di sana mematahkan tiga tes
konformansi, dan tes-tes itu benar.

Tes: `test_a_constant_fill_key_is_refused_everywhere_one_enters`,
`test_the_refusal_does_not_fire_on_real_keys`,
`test_the_primitive_still_reproduces_a_published_vector`.

---

## 3. Memori anti-replay tak terbatas

**Cacatnya.** `set` yang tidak pernah lupa itu benar, sekaligus bocor pelan:
verifier yang berjalan lama tumbuh 16 byte per rekaman diterima, selamanya.
Operator baru tahu ketika prosesnya mati berbulan-bulan kemudian. Protokol
terpasang tidak begitu — IPsec dan DTLS sama-sama membawa **jendela**, bukan
riwayat penuh.

**Yang Ka'bah lakukan.** `ReplayWindow` berbatas, default 4096 nonce (64 KiB).
Biayanya nyata dan **disebutkan, bukan disembunyikan**: rekaman yang lebih tua
dari jendela bisa di-replay lagi, dan `ReplayWindow.evicted` menghitung setiap
nonce yang jatuh keluar — jendela yang kekecilan muncul sebagai angka, bukan
sebagai lubang diam. `set` biasa tetap diterima kalau riwayat penuh memang
yang dibutuhkan.

Tes: `test_the_replay_window_does_not_grow_without_limit`,
`test_eviction_is_counted_rather_than_silent`,
`test_replays_inside_the_window_are_still_refused`.

---

## 4. JWT `alg: none` dan kebingungan HS256/RS256

**Cacatnya.** Field header yang **mengarahkan verifikasi** tetapi tidak ikut
diautentikasi. Keluarga yang sama: FREAK, Logjam, SLOTH — permukaan serangan
adalah negosiasinya sendiri.

**Yang Ka'bah lakukan.** Satu suite, tanpa negosiasi. Penanda format ada di
dalam input MAC, jadi menulis ulangnya tidak bisa dibuat lolos verifikasi.

Tes: `test_the_format_identifier_is_covered_by_the_tag`.

---

## 5. Parser longgar — malleability transaksi Bitcoin, bypass tanda tangan BER/DER

**Cacatnya.** Byte yang diabaikan verifier tetapi dibaca oleh pembaca.

**Yang Ka'bah lakukan.** Lapis 0 memberi satu bacaan per nilai; parsernya
menolak byte tambahan, panjang yang tidak cocok, dan tag terpotong. Tidak ada
yang diperbaiki diam-diam.

Tes: `test_trailing_bytes_are_refused`, `test_a_truncated_tag_is_refused`.

---

## 6. Yang **masih terbuka di Ka'bah**

Bagian ini ada supaya dokumen ini bukan brosur.

**S-box sebagai tabel — DITUTUP di perangkat keras, masih terbuka di Python.**
Lookup 256 entri yang diindeks data persis sasaran serangan cache-timing AES
(Bernstein 2005; Osvik, Shamir, Tromer 2006). Ini dulu tercatat terbuka. Yang
menutupnya adalah usulan arsitektur: **jangan pakai tabel — jadikan blok
logika yang selesai per clock.**

GF(2⁸) isomorfik dengan GF((2⁴)²), dan di sana inversi murah:

```
N    = ν·ah² + ah·al + al²             norma, masuk ke GF(2⁴)
A⁻¹  = (ah·N⁻¹)·y + ((ah⊕al)·N⁻¹)
```

Jadi substitusinya menjadi `x → T → invers komposit → T⁻¹ → affine`, dengan T
dan T⁻¹ linear atas GF(2) — artinya pohon XOR. Strukturnya milik Canright;
yang **tidak** dipinjam adalah isomorfismanya: konstanta Canright untuk 0x11B
milik AES, sedangkan cube tersegel memilih 0x12B, jadi ν, β dan kedua matriks
dicari khusus untuk lapangan ini dan dipilih yang bobot XOR-nya terkecil
(ν = 0xD, β = 0x71).

Tidak ada memori di jalur itu. Tidak ada alamat, tidak ada port yang
diperebutkan, tidak ada latensi yang bergantung pada nilai — satu propagation
delay yang sama untuk setiap masukan. Sifat constant-time bukan dipertahankan,
melainkan **tidak ada yang bisa bervariasi**.

Terukur dengan yosys (`abc -lut 4`), bukan ditaksir:

| | logika tower | tabel 256 entri |
|---|---:|---:|
| per S-box | **76 LUT4** | 274 LUT4 |
| router WIDTH=8 | **605 LUT4** | 2209 LUT4 |
| router WIDTH=25 | **2023 LUT4** | 6743 LUT4 |
| — di Tang Nano 9K (8640 LUT4) | **23%** | 78% |

WIDTH=25 adalah seluruh muka cube 5×5 tersubstitusi dalam satu clock. Versi
logika bukan hanya yang tanpa celah timing — ia juga satu-satunya yang
menyisakan ruang untuk sisa sponge, UART dan HCPU di sebelahnya. Versi tabel
tidak muat untuk desain itu.

Bit-exact dengan `cube.SBOX` untuk seluruh 256 masukan, di Python maupun di
Verilog tersimulasi. Berkas: `src/hijaiyyah/crypto/sbox_logic.py`,
`rtl/hijaiyyah_sbox.v`, `rtl/hijaiyyah_sbox_router.v`, dibangkitkan oleh
`tools/gen_sbox_rtl.py` dari polinomial tersegel — `--check` adalah gerbang
supaya RTL tidak pernah tertinggal dari Python.

Yang **masih terbuka**: `cube.py` tetap memakai tabel, dan Python tidak
constant-time apa pun bentuknya — integer CPython, `&` dan `^`-nya bukan
constant-time. Penutupan ini milik silikon. Untuk perangkat lunak yang
memproses rahasia, lapis 3 (HMAC-SHA256 dari pustaka yang sudah ditinjau)
tetap satu-satunya bagian yang menyentuh kunci, dan lapis 2 tetap tanpa kunci.

**Kunci tidak di-zeroize.** Python tidak menjamin penghapusan memori. Kunci
bisa tertinggal di heap dan di swap.

**Lapis 2 tetap [EH].** Terukur bukan terkriptanalisis. Belum ada yang
menyerangnya selain penulisnya sendiri, dan itu bukan kriptanalisis.

**Length extension** ditutup secara struktural oleh sponge dan HMAC, tetapi
di sini baru berupa argumen — belum ada demonstrasi yang dijalankan seperti
pada §1. Argumen struktural bukan bukti dengan mutu yang sama, dan bedanya
sengaja tidak dikaburkan.

---

## 7. Catatan cara kerja

Dua gerbang menembak penulisnya sendiri selama pekerjaan ini, dan keduanya
dicatat di tempat masing-masing, bukan dirapikan:

1. Verifikasi lapangan GF(2^128) awalnya membandingkan dengan konstanta
   SP 800-38D **dari ingatan**; satu byte salah dan run berhenti. Sekarang
   dijangkarkan ke hukum yang mendefinisikan lapangan itu.
2. Invers GF(2⁴) awalnya ditulis sebagai `case`, dan yosys menyimpulkannya
   sebagai memori 16×4 — `1 memories, 64 memory bits` — **di bawah komentar
   yang mengaku "empat LUT4"**. Di papan ini bedanya tidak berakibat, tapi
   netlist yang membantah komentarnya adalah cara sebuah klaim timing menjadi
   salah di tempat yang berakibat. Sekarang ditulis sebagai bentuk normal
   aljabar, yang tidak bisa disimpulkan sebagai memori oleh flow mana pun.
