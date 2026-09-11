# Codex — dari Matematika Hijaiyyah Bab I & II ke Cosmictera Computing

[`COMPUTING.md`](COMPUTING.md) menyebut empat program (HCPU, Ka'bah, tumpukan
tujuh lapis, NUI) dan satu disiplin yang mengikat semuanya. Dokumen ini
menunjuk ke lapis di BAWAH keempatnya: Bab I dan Bab II buku *Matematika
Hijaiyyah* (`Buku Matematika Hijaiyyah/Buku Matematika Hijaiyyah Edisi
v.1.1.1 @2026 HMCL/41.pdf` … `111.pdf`) — matematika murni yang, sebelum
jadi HCPU atau Ka'bah, dulu jadi **codex**: vektor integer 18-dimensi per
huruf. Setiap baris tabel di sini menunjuk section buku (dengan nomor
halaman nyata) ke modul kode yang mengimplementasikannya dan tes yang
memverifikasinya — bukan ringkasan naratif, tapi peta yang bisa dijalankan
ulang.

---

## Bab I — Fondasi Formal (hal 41–86)

| Section buku | Apa | Kode | Tes |
|---|---|---|---|
| IA.1.8, hal 46 | Empat invarian: Θ̂ (Inḥinā'), N, K, Q — 1+3+5+5=14D | [`core/codex_entry.py`](../src/hijaiyyah/core/codex_entry.py) — `CodexEntry.theta_hat/na/nb/nd/kp…qc` | `tests/test_core/test_codex_entry.py` |
| IB.1.1–1.3, hal 49–50 | Tiga primitif Nuqṭah/Khaṭṭ/Qaws, uji Δφ, mutual exclusivity | sama — 14 komponen inti `CodexEntry.vector[1:14]` | `test_codex_entry.py` |
| IC.1.1–1.9, hal 56–65 | Inḥinā' Θ̂: total turning, kuantisasi ke kelipatan 90° | `CodexEntry.theta_hat` (vector[0]) | `test_codex_entry.py` |
| IC.1.10–1.17, hal 65–67 | MainPath: himpunan kandidat (OpenPath ∪ ClosedPath), Skor leksikografis `(Len, −Junc, LoopPref, EmbKey)`, **Teorema Keunikan** | [`skeleton/mainpath.py`](../src/hijaiyyah/skeleton/mainpath.py) — `MainPathSelector.candidates/score/select` | `tests/test_skeleton/test_mainpath.py` — **8/8 lulus** |
| IC.1.18–1.21, hal 67–70 | CSGI: citra glyph → graf skeleton (binarisasi → pisah nuqṭah → thinning → graf → pruning) | [`skeleton/csgi.py`](../src/hijaiyyah/skeleton/csgi.py) (`CSGINode/CSGIEdge/CSGIGraph`), [`skeleton/contractor.py`](../src/hijaiyyah/skeleton/contractor.py) (`SkeletonContractor`), [`skeleton/skeletonizer.py`](../src/hijaiyyah/skeleton/skeletonizer.py) (`zhang_suen_thinness`) | `tests/test_skeleton/` — **21/21 lulus** |
| IC.1.22–1.23, hal 71–72 | Budget turning `U=Qx+Qs+Qa+4Qc`, residu `ρ=Θ̂−U` | `CodexEntry.U`/`.rho`; [`core/guards.py`](../src/hijaiyyah/core/guards.py) — `compute_U`/`compute_rho` | `test_codex_entry.py`, `tests/test_core/test_guards.py` |
| IC.1.26–1.27, hal 72–73 | Teorema Mod-4: MainPath tertutup ⟹ Θ̂≡0 (mod 4) | [`theorems/mod4_gate.py`](../src/hijaiyyah/theorems/mod4_gate.py) — `Mod4Gate.check`/`.check_all` | `tests/test_full_verification.py`, `tests/test_integrity/test_bab_satu.py` |
| ID.1.1–1.4, hal 74–75 | Codex 14D (inti) + 3 ringkasan (A_N/A_K/A_Q) + 1 marker Hamzah (H*) = 18D | `CodexEntry.vector` (18 slot), `CodexEntry.a_n/a_k/a_q/h_star`; [`core/constants.py`](../src/hijaiyyah/core/constants.py) — `V14_SLOTS` | `test_codex_entry.py` |
| ID.1.5, hal 76 | Injektivitas — 378 pasangan huruf, semua unik | [`integrity/injectivity.py`](../src/hijaiyyah/integrity/injectivity.py) — `InjectivityVerifier.verify`/`.collision_pairs` | `tests/test_integrity/test_injectivity.py` — **2/2 lulus** |
| ID.1.7, hal 77 | Guard G1–G4 (sum-check N/K/Q, cross-constraint ρ≥0) + T1–T2 topologis | [`core/guards.py`](../src/hijaiyyah/core/guards.py) — `guard_check`/`full_guard_check`/`guard_detail` | `tests/test_core/test_guards.py` |
| IE.1.1, hal 79 | Master Table 28×18, disegel SHA-256 | [`core/master_table.py`](../src/hijaiyyah/core/master_table.py) — `MasterTable`, `_RAW` | `tests/test_core/test_master_table.py` |

**CSGI: dua bug diperbaiki, lalu disambungkan ke Ψ-Compiler.** Menulis
`tests/test_skeleton/` — 21 tes yang menjalankan kodenya sendiri pada array
piksel, bukan pada data yang sudah diekstraksi — memunculkan dua cacat yang
sama-sama mematikan loop, dan keduanya justru mengenai sembilan huruf ber-Qc>0:

1. **Cycle murni hilang seluruhnya.** Step 2 hanya membuat node di piksel
   berderajat ≠2; sebuah loop tertutup berderajat 2 di *semua* pikselnya, jadi
   tidak ada node, tidak ada edge, dan fallback lama hanya menyisipkan satu
   node berderajat 0 — jalurnya tidak direkam. **Step 2b** sekarang menyemai
   satu node per komponen semacam itu (urutan raster, deterministik) dan
   trace-nya menutup balik jadi edge dengan `u == v`.
2. **Dua busur antara pasangan simpul yang sama runtuh jadi satu.** Kunci
   dedup edge dulu `(min(u), max(v))` — satu edge per pasangan simpul. Padahal
   cincin yang punya tangkai bertemu tangkainya di dua junction, jadi loop-nya
   **adalah** dua busur antar pasangan yang sama; satu tertimpa, cycle-nya
   lenyap, dan MainPath tak pernah bisa melihatnya sebagai kandidat
   ClosedPath. Kuncinya sekarang lintasan yang ditelusuri itu sendiri,
   dikanonikkan terhadap pembalikan — tetap men-dedup busur yang sama yang
   ditelusuri dari dua ujung, yang memang tujuan kunci lama.

Sesudah keduanya, `pipeline/__init__.py` disambungkan: `PsiCompiler.extract_glyph`
menerima `image` opsional dan menjalankan **thinning → kontraksi → seleksi
MainPath** sungguhan (`_run_csgi`). Yang **tidak** ikut: `measurement`-nya
tetap dari Master Table tersegel, karena Θ̂ butuh integrasi kurvatur sepanjang
lintasan terpilih (IC.1.1) dan N-K-Q butuh pemisahan nuqṭah yang belum ada
implementasinya di mana pun. Jadi `.hgeo` hasil jalur citra membawa **struktur
yang diturunkan** dan **ukuran yang diwarisi** — dan itu dinyatakan, bukan
dikaburkan (`tests/test_pipeline/test_psi_compiler.py::TestPsiCompilerRunsCSGI`).

**Teorema Keunikan MainPath sekarang dijalankan, dan menjalankannya menemukan
satu lubang di definisi buku.** `skeleton/mainpath.py` mengeksekusi IC.1.11
(himpunan kandidat), IC.1.12 (Skor leksikografis), dan IC.1.13/IC.1.17
(argmax). Dua hal muncul yang tidak muncul selama teorema itu hanya dibaca:

- **Kandidat harus benar-benar himpunan.** Enumerasi menemukan `s→t` dan
  `t→s`; itu lintasan yang sama. Dibiarkan berdua, keduanya berskor identik —
  EmbKey dikanonikkan terhadap pembalikan, jadi duplikatnya justru *seri
  dengan dirinya sendiri* — dan urutan ketat IC.1.15 gugur. Terukur pada
  fixture T sebelum diperbaiki: 23 kandidat, 13 skor berbeda, kesepuluh
  tabrakannya lintasan lawan cerminnya.
- **EmbKey buku tidak injektif kalau ada busur paralel.** IC.1.12 berhenti di
  EmbKey dan IC.1.15 menyimpulkan urutannya ketat dari situ. Kesimpulan itu
  hanya berlaku selama lintasan ditentukan oleh simpul yang dilewatinya —
  dan itu **tidak** berlaku begitu dua edge menghubungkan pasangan simpul
  yang sama. Kedua busur loop sebuah huruf melewati persis dua junction yang
  sama, jadi urutan simpulnya sama, koordinatnya sama, EmbKey-nya sama,
  padahal lintasannya berbeda. Terukur pada cincin-bertangkai: dua kandidat
  berbeda, satu skor, dan maksimum IC.1.17 tidak lagi tunggal. Perbaikannya
  minimal — urutan edge kanonik ditambahkan sebagai komponen **terakhir**, di
  bawah semua yang buku definisikan, jadi apa pun yang IC.1.12 sudah pisahkan
  tetap terurut persis seperti semula; ia hanya memutus seri yang buku
  tinggalkan terbuka.

Dan satu hal yang buku benar dan sekarang terbukti berjalan: **Qc > 0 tidak
memaksa MainPath tertutup** (IC.1.14, dengan ف dan و sebagai kasus nyatanya di
IC.1.29). Pada cincin-bertangkai, loop-nya panjang 2 dan lintasan
tangkai-ke-tangkai panjang 3 — `Len` berperingkat di atas `LoopPref`, jadi
lintasan terbuka menang meski loop-nya ada. Itu bukan diklaim, itu dijalankan:
`test_a_loop_does_not_force_a_closed_mainpath`.

---

## Bab II — Metrik Vektorial Hijaiyyah (hal 88–111)

Lima operasi, satu modul per operasi, semua di
[`src/hijaiyyah/algebra/`](../src/hijaiyyah/algebra/):

| Section buku | Operasi | Pertanyaan | Kode |
|---|---|---|---|
| IIA, hal 90–97 | Vektronometry (VTM) | Terbuat dari apa sebuah huruf? | [`algebra/vektronometry.py`](../src/hijaiyyah/algebra/vektronometry.py) — `primitive_ratios`, `turning_ratios`, `comp_angle`, `project` |
| IIB, hal 97–100 | Normvektor (NMV) | Apa yang membedakan dua huruf? | [`algebra/normivektor.py`](../src/hijaiyyah/algebra/normivektor.py) — `diff`, `norm_decomposition`, `diff_theta`, `diff_N` |
| IIC, hal 100–102 | Aggregametric (AGM) | Berapa total codex sebuah string? | [`algebra/aggregametric.py`](../src/hijaiyyah/algebra/aggregametric.py) — `string_integral`, `add_codex`, `layer_integrals` |
| IID, hal 103–105 | Intrametric (ITM) | Seberapa jauh dua huruf? | [`algebra/intrametric.py`](../src/hijaiyyah/algebra/intrametric.py) — `euclidean`, `manhattan`, `hamming` |
| IIE, hal 105–109 | Exometric (EXM) | Apakah data konsisten? | [`core/exomatrix.py`](../src/hijaiyyah/core/exomatrix.py) — `build_exomatrix` (struktur 5×5, IIE.2.1) + [`algebra/exometric.py`](../src/hijaiyyah/algebra/exometric.py) — `audit` (R1–R5), `row_sums`, `grand_sum`, `phi` (Frobenius energy) |

**Tes:** `tests/test_algebra/test_{vektronometry,normivektor,aggregametric,
intrametric,exometric}.py` — **15 lulus**; `tests/test_core/` — **55 lulus**
(dihitung terpisah: 70 adalah jumlah keduanya, bukan angka test_algebra
sendiri). Buku menutup Bab II dengan **683 pemeriksaan, 683 PASS** (IIF.2.2,
hal 111); `tests/test_full_verification.py` memecahnya per bab — **Bab I 658,
Bab II 683, Bab III 39 = 1.380, semuanya lulus** (dijalankan ulang, bukan
diambil dari header berkas itu sendiri).

---

## Bagaimana codex ini menjadi Hybit

Definisi formal hybit ada di **Bab III**, bukan Bab I/II — `core/hybit.py`
mengutipnya sendiri sebagai "Definition 3.1.1 (Bab III)", dan Bab III berada
di luar cakupan dokumen ini (belum dibaca untuk berkas ini). Yang Bab I
berikan adalah posisinya dalam rantai, hal 44: `Codex → Guard validation →
Hybit → Master Table → Dataset-Seal`. Isinya sendiri: elemen himpunan valid
`V ⊂ ℕ₀¹⁸` (vektor 18D yang lolos G1–G4 dan T1–T2).
[`core/hybit.py`](../src/hijaiyyah/core/hybit.py)'s kelas `Hybit`
merealisasikan definisi ini secara harfiah: constructor menolak vektor yang
gagal `guard_check` — tidak ada `Hybit` yang bisa dibuat di luar `V`.
`(V,+)` sebagai monoid komutatif (bukan ruang vektor, IA.1.11/IIA.2.3) juga
persis: `Hybit` tidak mengekspos pengurangan atau perkalian skalar.

## Bagaimana codex ini menyambung ke Ka'bah

Ini sambungan Bab II yang paling harfiah, dan `crypto/cube.py`'s header
sendiri yang menyatakannya: *"Bab II §IIE.2.1 already defines the Letter
Exomatrix E(h), a 5×5 matrix per letter, and the alphabet is 28 letters.
Stacking them gives a 5×5×28 cube that is **derived rather than invented**."*
Rantainya, dengan angka yang bisa dicek di `cube.py`:

| Dari | Ke | Angka |
|---|---|---|
| Exomatrix 5×5 (IIE.2.1) | kubus tersegel, 28 huruf ditumpuk | 5×5×28 |
| Muka 5×5 itu | grid lajur spons | `STATE_LANES = ROWS*COLS` = 25 |
| Sirkuit tawaf memotong muka | rate vs kapasitas | `OUTER_RING` 16 lajur → `RATE` 128 B; `CORE` 9 lajur → `CAPACITY_BITS` 576 |

Perhatikan bahwa **25×64 = 1600 bit adalah keadaan spons, bukan kubusnya** —
dua struktur berbeda yang mudah tertukar ([`ON.md`](../cosmictera-build/ON.md)
menyebut yang pertama "Spons"; kubus tersegelnya 5×5×28).

`core/exomatrix.py`'s `compose_step` memakai Exomatrix yang sama sebagai
peta linier — satu tick perkalian matriks mod p — dipakai langsung oleh
`nui/clockwork.py`, dan dibaca `cosmic-codex-jim/` atas GF(2) untuk periode
LFSR-nya.

**Batas yang `cube.py` sendiri pasang, dan tidak boleh dilewati di sini.**
Modul itu berlabel **[EH]** — hipotesis rekayasa, bukan cipher yang layak
dipakai; permutasi baru belum punya kriptanalisis publik. Dan soal andil
geometri: *"The geometry selects a member of a family, and crediting it with
the algebra's work would be false"* — kekuatan S-box datang dari invers
GF(2⁸) (DU 4, NL 112, sama seperti AES), bukan dari huruf. Geometri huruf
memilih **field mana** dan konstanta affine-nya; ia tidak mengerjakan
aljabarnya. Karena itu
[`crypto/sbox_logic.py`](../src/hijaiyyah/crypto/sbox_logic.py) bukan
turunan Bab I/II sama sekali — ia rekayasa GF((2⁴)²) standar (Canright)
di hilir polinomial tersegel `cube.py`.

## Bagaimana codex ini menyambung ke HCPU

Codex 18D masuk silikon secara harfiah: `rtl/hcpu_rom.v` menyimpan
**28 entri × 144 bit** — persis 18 komponen × 8 bit per huruf (headernya
sendiri: *"28 letters × 18 components × 8 bits"*), dialamati indeks huruf
1–28. Guard G1–G4 dan T1–T2 dijaga ulang di gerbang oleh `rtl/hcpu_guard.v`,
dengan rumus yang sama persis seperti `core/guards.py` — diperiksa langsung
di berkasnya: `G4: ρ = Θ̂ − U ≥ 0 where U = Qx + Qs + Qa + 4×Qc`.

**Dan "dua mesin yang harus setuju" pernah TIDAK setuju di sini.**
`tests/test_integrity/test_dataset_consistency.py`'s header mencatat
insidennya: `data/hm28.json` — sumber yang menurunkan ROM — berbeda dari
tabel kanonik pada **Tha, Zha, Kaf, dan Nun**, jadi silikon menjalankan
alfabet yang berbeda dari suite tes, dan entri Kaf yang rusak melanggar
guard T2 — yang lalu ditutupi oleh override `is_kaf` di `hcpu_guard.v`
sendiri. Keduanya sudah dicabut: override-nya hilang (komentar di
`hcpu_guard.v` menyebutnya sebagai yang "prior"), dan 12 tes di berkas itu
sekarang memaku setiap salinan tabel — Python, ROM perangkat keras, GUI web —
ke `core.master_table`. **12/12 lulus.** Ini contoh paling tajam kenapa
peta di dokumen ini harus tes, bukan prosa: prosa yang sama akan tetap
terbaca benar selama empat huruf itu salah.

---

## Verifikasi terdalam: buku dibaca ulang saat tes jalan

`tests/test_integrity/test_bab_satu.py` dan `test_bab_dua.py` tidak
membandingkan kode dengan ringkasan buku — keduanya membuka PDF halaman
asli (`_page()`, lewat `pymupdf`) SAAT TES BERJALAN dan mencocokkan klaim
teks itu terhadap `MASTER_TABLE` langsung. Dan itu menangkap **satu kalimat
buku yang terlalu jauh**, terukur, bukan sekadar dicurigai.

ID.1.1 (hal 74) berbunyi: *"rank(M14)=14 — seluruh 14 dimensi diperlukan
secara aljabar. Penghapusan satu dimensi menyebabkan collision."*

- **Paruh pertama benar** dan diverifikasi: `_rank(V14) == 14`.
- **Paruh kedua overstate.** Dua sifat berbeda diperlakukan sebagai satu:
  independensi linier (tidak ada kolom yang kombinasi kolom lain — benar
  untuk keempat belas, itulah arti rank 14) versus injektivitas (tidak ada
  dua huruf yang sama pada sisanya). Diukur: menjatuhkan salah satu dari
  **10 komponen K dan Q tetap menyisakan 28 huruf yang bisa dibedakan**.
  Hanya **empat** dimensi yang benar-benar menimbulkan collision saat
  dijatuhkan — `Θ̂, Na, Nb, Nd` — yaitu belokan dan ketiga zona titik.
  Assertion-nya sendiri: `assert collides == [0, 1, 2, 3]`.

Kolom bisa independen secara linier dan tetap tidak memisahkan pasangan mana
pun; rank penuh tidak menyiratkan yang kedua. 14/14 lulus (dijalankan
barusan) — artinya bukan "buku dan kode identik di semua klaim," melainkan
titik-titik yang diperiksa cocok persis, **termasuk satu yang sengaja
dicatat TIDAK cocok** alih-alih dihaluskan.

---

Angka hari ini (jalankan ulang, jangan dikutip dari sini):
`python3 -m pytest tests/test_core tests/test_algebra -q` → 70 lulus;
`python3 -m pytest tests/test_full_verification.py -q` → 1.380 lulus;
`python3 -m pytest tests/test_integrity/test_bab_satu.py
tests/test_integrity/test_bab_dua.py tests/test_integrity/test_injectivity.py -q`
→ 16 lulus; `python3 -m pytest tests/test_skeleton/ -q` → 21 lulus;
`python3 -m pytest tests/test_integrity/test_dataset_consistency.py -q` → 12 lulus.
