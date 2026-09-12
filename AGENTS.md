# Catatan kerja — baca sebelum menyentuh repositori ini

Catatan ini untuk agent (dan orang) yang melanjutkan pekerjaan di sini. Isinya
lima hal:

0. berkas mana yang wajib dibaca, dan urutannya;
1. dasar semua pekerjaan;
2. arti nama-nama;
3. alur ceritanya;
4. aturan kerja — yang diajarkan pemilik proyek, aturan kuli AI (K1–K15),
   cara masuk kerja, dan syarat naik tahap.

Catatan ini **peta, bukan sumber kedua**. Kebenaran tetap tinggal di tempatnya:

- cerita di pesan commit;
- aturan di `cosmictera/RULES.md` dan `ENGINEERING_STANDARD.md`;
- nama di `teknologi/ISTILAH.md`.

`tests/test_integrity/test_agent_notes.py` memeriksa bahwa setiap commit dan
berkas yang disebut di sini benar-benar ada.

---

## 0. Berkas yang wajib dibaca, dan urutannya

Jangan membaca seluruh repositori. Tujuh berkas ini yang **mengarahkan
pekerjaan**; sisanya dibuka hanya kalau butir yang sedang dikerjakan
menyentuhnya.

### Lapis 1 — wajib, selalu, sebelum menyentuh apa pun

| urutan | berkas | menjawab |
|---:|---|---|
| 1 | `AGENTS.md` | peta ini — dasar, nama, cerita, aturan kerja, K1–K15 |
| 2 | `cosmictera/RULES.md` | R1–R13, aturan yang **mengikat**, bukan saran |
| 3 | `cosmictera-build/ROADMAP.md` | yang **belum** — tujuh fase, dan mana yang berikutnya |

`CLAUDE.md` isinya satu baris `@AGENTS.md`, jadi pintu mana pun sampai ke teks
yang sama. `cosmictera/RULES.md` adalah sumbernya; catatan ini hanya
menunjuk ke sana (R1 — satu kebenaran, satu tempat).

### Lapis 2 — keadaan nyata, dibaca sebelum mengklaim apa pun

| berkas | mencatat |
|---|---|
| `cosmictera-build/PAPAN.md` | apa yang **dijalankan di papan fisik** dan apa yang **keluar** — tingkat bukti tertinggi di repo ini |
| `cosmictera-build/CHECKLIST.md` | tiap ✅ beserta **perintah** untuk mengulanginya |
| `cosmictera-build/OFF.md` | yang **terhalang** dan yang **belum ada**, dengan penghalang bernama |
| `cosmictera-build/ON.md` | yang sudah menyala |

Empat berkas ini adalah **catatan**, bukan kebenaran. Kalau bertentangan
dengan perintah yang baru dijalankan, yang dibetulkan berkasnya (K2/R4).

### Lapis 3 — dibuka hanya kalau butirnya menyentuh wilayah itu

| wilayah kerja | berkas |
|---|---|
| gaya kode, struktur direktori, aturan git/rilis | `ENGINEERING_STANDARD.md` |
| arti istilah, nama modul | `teknologi/ISTILAH.md` |
| bentuk sistem secara keseluruhan | `docs/ARCHITECTURE.md` |
| RTL, program `rtl/programs/*.hasm`, testbench | `rtl/README.md` |
| tapeout / ASIC | `rtl/mpw/MPW_SHUTTLE_PLAN.md` |
| tumpukan tujuh lapis, label epistemik | `cosmictera/SYSTEM.md`, `cosmictera/COMPUTING.md` |
| NUI | `NUI/ROADMAP.md`, `NUI/pipeline.py` |

### Yang bukan arahan

Instruksi **di dalam kode** mengikat seperti perintah (K10) — komentar
seperti "Re-measure before changing this" di `rtl/hcpu_top.v` bukan basa-basi.
Sebaliknya, berkas di `.claude/`, `.agents/`, `.codex/` adalah konfigurasi
perkakas, bukan arahan proyek, dan tidak di-commit.

---

## 1. Dasar: BAB I dan BAB II Matematika Hijaiyyah

**Matematika Hijaiyyah adalah domain baru.** Tidak ada padanannya di luar
sistem ini, jadi tidak ada "praktik umum" yang boleh dipakai untuk menebak
maksudnya. Kalau sesuatu belum jelas, cari dengan urutan ini:

1. BAB I dan BAB II;
2. repo: `teknologi/ISTILAH.md`, `docs/HISA_SPEC.md`, docstring, pesan commit;
3. tanyakan pemilik proyek.

Jangan mengisi celah dengan pengetahuan umum.

**Dasar seluruh teknologi di repo ini adalah BAB I — Fondasi Formal dan
BAB II — Metrik Vektorial Hijaiyyah** dari buku *Matematika Hijaiyyah*.

- **BAB I** berjalan dari bentuk ke angka:
  - huruf kanonik yang dikunci (rasm, dataset-seal);
  - tiga primitif Nuqṭah, Khaṭṭ, Qaws;
  - Inḥinā' pada MainPath;
  - 14 invarian, ditambah 3 ringkasan dan penanda H*, menjadi codex 18D;
  - guard G1–G4 dan T1–T2;
  - Master Table tersegel.

  Empat prinsip normatifnya: Canonical Lock, Integer-Only,
  Computable & Comparable, Auditable & Reproducible.
- **BAB II** memberi lima operasi atas codex yang sama: Vektronometry,
  Normvektor, Aggregametric, Intrametric, Exometric.

Naskah buku tidak ada di repo: di-gitignore dan tidak dipublikasikan. Di repo:

- Bab I hidup di `src/hijaiyyah/core/`, Bab II di `src/hijaiyyah/algebra/`.
- Keduanya dibaca-silang terhadap halaman buku oleh
  `tests/test_integrity/test_bab_satu.py`, `tests/test_integrity/test_bab_dua.py`
  dan `tests/test_integrity/test_book_anchor.py`.
- Penjelasan resepnya ada di `matematika-hijaiyyah/`.

Dua beda antara buku dan kode sudah diukur dan **sengaja dibiarkan**:

- kode membangun transpose exomatrix buku (`7541245`);
- H* adalah fungsi indikator non-geometris, bukan celah guard (`890cf9d`).

**Alur cerita implementasi dibaca dari commit, bukan dari buku.** BAB III buku
akan dirombak dari hasil commit-commit ini.

---

## 2. Nama adalah fungsi kerja

Tidak ada nama yang asal di proyek ini: tiap nama menyebut fungsi kerjanya.
Kepanjangan Hybit — **Hijaiyyah Hyperdimensional Bit Integration** — adalah
pola kerjanya:

| Kata | Fungsi | Tempatnya |
|---|---|---|
| Hijaiyyah | 28 huruf kanonik tersegel sebagai sumber | `src/hijaiyyah/core/master_table.py` |
| Hyperdimensional | ruang ℕ₀¹⁸ — kata ini menyebut sebuah angka, dan angka itu 18 | `tests/test_core/test_hybit.py` |
| Bit | satuan yang digeneralisasi; hybit berjalan di atas bit, tidak menggantikannya | `CONTRIBUTING.md` |
| Integration | ketertutupan monoid (V, +): hybit ditambah hybit tetap hybit | `src/hijaiyyah/core/hybit.py` |

Cara hybit masuk ke silikon dicatat di `teknologi/README.md`. Sengaja tidak
dicatat di `src/hijaiyyah/core/hybit.py`, karena lapisan itu tidak boleh
menyebut substrat.

Aturan penamaan:

- Kepanjangan dan fungsi setiap istilah lain ada di `teknologi/ISTILAH.md`.
  Baca itu sebagai spesifikasi sebelum menyentuh modulnya.
- Dua nama untuk satu hal, atau satu simbol untuk dua peran, adalah cacat.
  Contoh: Ψ/H* dan `OP_MSB` (`7582ae5`).
- Nama dan slot baru tidak dikarang. `CGET` memakai nama dan nilai yang sudah
  ditetapkan `docs/HISA_SPEC.md` (`730b47f`).

---

## 3. Alur cerita, dari commit

Baca pesan lengkapnya dengan `git log --reverse` — alasan setiap langkah ada
di sana. Daftar di bawah hanya penunjuk bab.

### Maret–April 2026 — rilis awal

- `4a4f81a` HOM v1.0.0: Master Table, bahasa HC, H-ISA, HCVM, CSGI, GUI.
- `7131294` protokol HISAB.
- `552a851` kerangka verifikasi Bab I–III.
- `5a9094f` HCPU Fase 1: pipeline lima tahap, guard perangkat keras, ALU
  vektor 18-lebar. Diverifikasi di simulasi.

### 27–31 Agustus — satu kebenaran, satu tempat

- `b5bd239` Master Table dikanonikkan di semua salinan.
  - Salah satu salinan menyimpang pada ط ظ ك ن, dan ROM HCPU diturunkan dari
    salinan itu.
  - Sintesis dijalankan untuk pertama kali; estimasi diganti angka terukur.
- `1b59c2a` H-ISA dari tiga encoding disatukan ke encoding RTL, lalu dibekukan.
- `121c5c2` rumus U tinggal satu definisi.

### 1 September — dijangkarkan ke buku, rantai bahasa→silikon ditutup

- `9f279e1` implementasi dibandingkan dengan halaman buku, bukan hanya dengan
  salinan lain. Vektor uji G4 di ROM diperbaiki.
- `44ba928` HVM menjalankan semua opcode RTL.
- `ee44fb2` Ψ-Injector.
- `7451cd2` satu assembler, dalam dialek buku.
- `698dd3e` HC dikompilasi ke H-ISA dan berjalan di HCPU; tiga mesin sepakat.
- `730b47f` `CGET` — pola menambah opcode di seluruh rantai, dan tabel
  `EXTENSIONS` di `tests/test_integrity/test_book_anchor.py`.

### 1–2 September — Ka'bah dan CosmicTera

- `a910375` Ka'bah, lima lapis; hanya lapis 3 (HMAC-SHA256) yang memikul
  keamanan.
- `7969121` semi-log dulu — langkah yang dilewati, dan justru yang menentukan.
- `3ccf193` diserang sendiri: permutasinya bukan permutasi (rank 1276/1600).
- `49fb3b3` bottleneck-nya deserialiser: 2,59 MB/s, bukan 11,15.
- `904d9fa` nama CosmicTera untuk keseluruhan.
- `29c92a3` folder `cosmictera/`, termasuk `cosmictera/RULES.md`.

### 2–4 September — prasyarat sistem operasi di HCPU

- Perangkat dasar:
  - `8e92825` bitwise dan shift;
  - `cfb9927` UART terima dan timer;
  - `084ec52` MMIO.
- Mekanisme OS:
  - `c8a3aad` trap;
  - `096e392` mode supervisor;
  - `a606ed5` proteksi memori;
  - `34ca28c` syscall.
- H-Kernel:
  - `05e0a69` dua proses dengan preemption;
  - `c6d3e1b` CALL dan RET;
  - `0361135` I/O lewat kernel;
  - `dc5ae55` guard daemon — H-Kernel empat dari empat tanggung jawab;
  - `e239964` HAL, dan ternyata R16/R17 tidak ada.
- `0c507cf` HOS: heap, HFS terjaga guard, HAR sebagai layanan. Celah `CSET`
  dicatat di `cosmictera-build/OFF.md`.

### 3 September — buku dibaca terhadap kode

- `853cf61` hal. 41: rank 14 adalah pernyataan buku, bukan temuan.
- `890cf9d` Bab I dibaca terhadap kode.
- `7541245` Bab II dibaca terhadap kode.
- `e5bd781` satu huruf adalah satu instruksi utuh.
- `abe9300` opcode huruf ternyata belum pernah jalan di perangkat keras.
  `cosmictera-build/CHECKLIST.md` lahir dari sini.

### 10 September — papan Tang Nano 20K

- `eda6cdc` papan akhirnya jalan, setelah dua cacat:
  - deadlock reset pada pin MODE;
  - memori instruksi yang tak pernah terbawa bitstream mana pun.
- `2e2e3cd` video HDMI.
- `5595774` Ka'bah di papan; bytenya cocok dengan
  `src/hijaiyyah/crypto/cube.py`.
- `13bcf3b` `cosmictera-build/PAPAN.md`: apa yang benar-benar jalan di papan.
- `6781f4f` institusi dan hak.
- `422a07b` suite tanpa tes yang terlewati.

### 11 September — hanya realitas papan

- `e2f32fd` dan `eeb9372` folder `teknologi/`.
- `67ee048` keenam guard terbukti di silikon.
- `7582ae5` nama menyebut fungsi.
- `19b086b` edisi buku diputuskan, belum dibangun.
- `3265214` slot terbuka adalah afordansi, bukan cacat.
- `993d5d9` lattice pada hybit.
- `f115a19` penerima di `src/hijaiyyah/receiver/`.
- `619b87a` yang tidak pernah terjadi dihapus, bukan dijadikan riwayat.
- `ec2355b` rack: slot bitstream dimuat berurutan, jadi biayanya slot terbesar,
  bukan jumlah semua slot (`rtl/scripts/rack.py`).
- `81fbd2e` lima program trap jalan di papan.
- `0a910f0` rack bisa dibangun dari checkout bersih, dan slot HDMI bisa
  dibangun ulang.
- `cf2edcb` tes yang terlewati di checkout bersih, diukur.
- `b3662f0` catatan kerja ini sendiri, beserta tes penjaganya.
- `f0dd0f8` `CSET` (0x45) — separuh tulis dari `CGET`, dan `hos_fs_read`
  mengembalikan H-Reg hidup. Dijalankan di papan: `5 6 2 0` dan `1 1 1 2 1`.

### 12 September — blok codex, dan yang tidak muat

- `7eb177a` enam opcode codex di papan, yang ketujuh dikeluarkan oleh
  pengukuran.
  - `CMOV` `CZERO` `CEQ` `CRHO` `CU` `CMOD4` jalan di papan: `8 0 0 1 1 0 1 5`.
  - `U` dan `ρ` dibaca dari `rtl/hcpu_guard.v`, bukan dihitung ulang (R1).
  - `CDOT` dibangun lalu dicabut: 14 pengali 8×8 membuat slot papan tidak
    ter-place. Penghalangnya **tempat**, bukan semantik — butir pertama di
    repo ini yang begitu.
  - Sabotase menemukan lubangnya sendiri: membandingkan dua register yang
    sama-sama di-`CZERO` tidak bisa melihat `CZERO` yang salah. Diganti
    dengan sifat monoid, `HCADD` lalu `CEQ` (R3).

- `0d63a7e` M3 — shell menjawab kabel serial, dan empat penghalang dinamai.
  - `A`→`65`, `p`→`2 0 1` di papan; rute `shell → SYSCALL → kernel → HAL → UART`
    adalah satu-satunya yang ada.
  - Tabel syscall di memori data, bukan tabel lompat: ISA ini tidak punya
    lompatan terhitung.
  - **Tidak ada RTL yang disentuh.** Empat penghalang diukur lalu dicatat:
    tidak ada jalur keluaran karakter; proses yang dipreempt timer tidak pernah
    berjalan lagi (cacat lama di `rtl/programs/kernel.hasm`, benchnya tidak
    melihat); FLAGS
    bukan bagian konteks; `STORE` ke `TRAP_EPC` tepat sebelum `ERET`.
  - Benchnya menegaskan mesin **apa adanya** — baris terakhirnya menunggu pid 0
    *tidak* maju, supaya cacat yang diketahui tidak diam-diam jadi klaim.

### 13 September — penghalang A diisolasi

- `073b968` interupsi termaskable menyimpan nol di bayangan sebuah redirect.
  - `rtl/hcpu_fetch.v` menolkan `if_pc` saat redirect dan menurunkan
    `fetch_valid`; `rtl/hcpu_top.v` membaca `if_pc` **tanpa** menanyakan
    `fetch_valid`. Selama dua siklus yang dibayar sebuah redirect, `epc`
    tersimpan **0**.
  - Perbaikan lama (`rtl/tb/tb_hcpu_branch_trap_race.v`) menutup siklus yang
    **dibagi** trap dan cabang; dua siklus **sesudahnya** tidak tertutup.
  - Diukur: 60 fire, 21 menyimpan 0, dan tepat yang di bayangan.
    Papan menjawab sama: `0 0 88 89 88 0 0 88`.
  - **Tidak diperbaiki.** Perbaikannya di unit trap — keputusan pemilik.
  - `cosmictera-build/ON.md` berhenti mengklaim "tiga proses, dipreempt":
    yang terbukti hanya jalur **masuk** trap, bukan jalur kembalinya.

### Berikutnya — keputusan pemilik, 11 September 2026

Pekerjaan berikutnya sudah tercatat di `cosmictera-build/ROADMAP.md` (Fase 5–7)
dan `cosmictera-build/OFF.md`. Untuk tiga butir yang diperintahkan, pemilik
memutuskan:

1. **Lint Verilator** (`cosmictera-build/CHECKLIST.md`): RTL **tidak** diubah
   demi peringatan lint.
2. **Fase 5, opcode.** Ikuti `docs/HISA_SPEC.md`: kerjakan yang didefinisikan
   spesifikasi dan tidak bertanda "perangkat lunak saja".
   - `CSET` 0x45 **sudah selesai** (`f0dd0f8`), termasuk di papan.
   - Berikutnya dari daftar yang sama, mengikuti pola `730b47f` dan `f0dd0f8`:
     `CSUB` 0x43, `CMOV` 0x46, `CZERO` 0x47, `CEQ` 0x48, `CDOT` 0x49,
     `CNORM` 0x4A, `CDIST` 0x4B, `CRHO` 0x4C.
   - `VPROJ_T`, `VPROJ_N`, `VPROJ_K`, `VPROJ_Q` dan `HCHK` **tidak ada di
     spesifikasi** — tanyakan pemilik
     sebelum menyentuhnya. `CHASH`/`CSIGN` (0x70/0x72) menyentuh aturan R10
     (tak ada inti SHA-256 di RTL), jadi juga ditanyakan dulu.
3. **Fase 6, PDK:** Efabless SKY130 (`rtl/mpw/MPW_SHUTTLE_PLAN.md`).

### Keputusan pemilik, 12 September 2026

1. **Target papan dikecilkan dan dinamai: COSMICTERA COMPUTER M0.** Bukan
   desktop penuh — satu komputer CosmicTera minimal yang hidup di papan, dengan
   tangga M1–M12. Seluruhnya dicatat di `cosmictera-build/ROADMAP.md`; baca
   bagian itu sebelum mengambil butir berikutnya.
2. **`CSUB` (0x43) ditunda.** Selisihnya meninggalkan monoid dan bisa negatif,
   sementara komponen H-Reg adalah byte tak bertanda. *"Jangan mengarang
   semantik hardware sebelum pemilik spesifikasi menetapkannya."* Statusnya di
   `cosmictera-build/OFF.md`.
3. **Konflik di dalam spesifikasi dicatat, bukan dirapikan sepihak.**
   `AND`/`OR`/`XOR`/`NOT`/`SHL`/`SHR` muncul di dua blok `docs/HISA_SPEC.md`
   (0x17–0x1C dan 0xB0–0xB5). RTL yang terverifikasi adalah bukti implementasi;
   dokumen diperbaiki ketika **pemilik** memutuskan begitu.
4. **Kriteria batch opcode berikutnya:** pilih yang tidak punya ambiguitas
   representasi dan tidak menduplikasi semantik yang sudah berjalan.
5. **`CDOT` (0x49) dikeluarkan dari batch.** Batchnya turun dari tujuh ke enam:
   `CMOV`, `CZERO`, `CEQ`, `CRHO`, `CU`, `CMOD4`. Penghalangnya **tempat, bukan
   semantik** — RTL-nya benar dan lulus bench, tetapi 14 pengali 8×8 membawa
   `hcpu_gowin_top` ke 16.015 LUT4 dan nextpnr menolak menempatkannya; tanpa
   `CDOT` slot yang sama 14.714 LUT4, ter-place, dan dijalankan di papan.
   `CDOT` tetap berjalan di HVM dan tercatat di `cosmictera-build/OFF.md`
   dengan penghalang bernama.
6. **M3 dijalankan dari implementasi yang ada, tanpa desain baru.** *"Jangan
   membuat desain baru. Jangan mengubah ISA, RTL, matematika, atau menambah
   opcode yang belum diperintahkan."* Yang **BLOCKED** dan tidak boleh
   dikerjakan atas inisiatif sendiri: `PRINTH` 0xA1 dan `EMITS` 0xA2 di RTL,
   driver TX kedua, `rtl/hcpu_font8x8.hex`, dan mengubah semantik `PRINT`.
   Bentuk string `EMITS` di RAM 32-bit juga **tidak** boleh ditetapkan sendiri
   — spesifikasi belum menetapkannya.
   **M3 belum boleh disebut selesai** sampai jalur keluaran karakter disahkan
   pemilik desain dan berjalan di papan fisik. Yang terhalang dicatat di
   `cosmictera-build/OFF.md` dengan alasan terukur, bukan dirapikan.

### Kesimpulan resmi M3 — pemilik, 13 September 2026

> *"akar A sudah ditemukan; belum diperbaiki; B/C/D masih terbuka; M4 belum
> boleh dimulai."*

Empat kalimat itu adalah keadaan M3, dan yang keempat mengikat: **jangan
memulai M4.** Yang boleh dikerjakan hanyalah penghalang yang pemilik putuskan,
satu pada satu waktu, lalu empat gerbang dan uji fisik Tang Nano 20K.

| | penghalang | keadaan |
|---|---|---|
| A | resume setelah preemption timer | **akar ditemukan** (`073b968`), belum diperbaiki — perbaikannya di unit trap |
| B | FLAGS bukan bagian konteks proses | terbuka |
| C | `STORE` `TRAP_EPC` → `ERET` | terbuka |
| D | keluaran karakter (`PRINTH`/`EMITS` + bentuk string) | terbuka, **BLOCKED** |

Semuanya di `cosmictera-build/OFF.md` dengan angkanya. M3 tidak boleh disebut
selesai sampai jalur keluaran karakter disahkan pemilik **dan** berjalan di
papan fisik.

---

## 4. Aturan kerja

### Yang sudah mengikat di repo

- `cosmictera/RULES.md` R1–R13. Setiap aturan lahir dari insiden nyata.
  Paling sering dilanggar:
  - R1 — satu kebenaran, satu tempat;
  - R3 — gerbang diuji dengan merusak apa yang dijaganya;
  - R4 — angka yang tidak diukur ulang adalah klaim tentang desain yang sudah
    tidak ada;
  - R13 — commit hanya setelah status keluar tes diperiksa.
- Label epistemik VF/DP/CC/EH/AT tidak naik tanpa bukti baru (R2).
- `ENGINEERING_STANDARD.md` — penempatan modul; satu invarian, satu definisi.
- `CONTRIBUTING.md` — larangan tingkat konsep: huruf bukan bunyi atau makna,
  dan hybit tidak menggantikan bit.
- Sidik jari RTL di header wrapper papan dijaga
  `tests/test_integrity/test_place_and_route.py`. RTL berubah berarti place and
  route diulang lalu dicap ulang — bukan dicap tanpa mengukur.

### Yang diajarkan pemilik proyek

1. **Kuli, bukan perancang.** Desain, matematika, dan arsitekturnya sudah benar
   dan terukur. Agent menerapkannya persis:
   - tidak mengubah desain;
   - tidak bereksperimen;
   - tidak berasumsi;
   - tidak mengarang penjelasan sendiri — di kode, header, dokumen, maupun
     pesan.
2. **Baca dan review dulu, baru kerja.** Sebelum menyentuh sebuah butir:
   - baca definisinya yang tercatat (`cosmictera-build/ROADMAP.md`,
     `cosmictera-build/OFF.md`, `cosmictera-build/ON.md`,
     `cosmictera-build/CHECKLIST.md`, `cosmictera-build/PAPAN.md`);
   - baca dokumen desainnya, commit yang membangunnya, dan komentar di kodenya;
   - jalankan apa yang ada untuk melihat keadaan nyatanya.
3. **Instruksi yang tertulis di kode mengikat.** Contoh: `rtl/hcpu_top.v`
   mencatat bahwa konversi desimal PRINT sengaja memakai `/ 10` dan `% 10`,
   ditutup kalimat "Re-measure before changing this". Mengubahnya tanpa
   perintah berarti merusak.
4. **"Lanjutkan" artinya melanjutkan** pekerjaan yang sedang berjalan atau yang
   tercatat sebagai berikutnya — bukan memilih arah baru.
5. **Temuan dilaporkan sebagai fakta polos, lalu tunggu perintah.**
   - Jangan mengubah RTL, desain, atau matematika atas temuan sendiri.
   - Kalau hasil di papan salah setelah agent membangun dan membakar
     bitstream, periksa pekerjaan sendiri dulu. Jangan menyalahkan papan atau
     simulasi.
6. **Kalau pemilik berkata "kembalikan", kembalikan semuanya** ke keadaan
   sebelumnya. Cadangannya disimpan di luar repo.
7. **Hanya realitas papan.**
   - Yang tidak pernah terjadi dihapus, bukan dijadikan riwayat.
   - Pekerjaan perangkat keras selesai ketika berjalan di papan Tang Nano 20K,
     bukan ketika testbench hijau.
8. **Unduhan** — PDK, perkakas, berkas pihak ketiga — hanya dengan izin
   pemilik.
9. **Bahasa.**
   - Pesan untuk pemilik dalam bahasa Indonesia.
   - Artefak mengikuti bahasa berkasnya: pesan commit dan komentar kode
     berbahasa Inggris, folder resep berbahasa Indonesia.

### Cara masuk kerja — enam perintah pertama, sebelum menyentuh apa pun

Kuli yang baru datang tidak bertanya "kerjakan apa?" — ia **membaca keadaan**.
Jalankan keenam ini dulu, berurutan, dan keluarannya yang menjawab:

```bash
git log --oneline -5                 # 1. cerita berhenti di mana
git status --porcelain               # 2. ada yang setengah jalan?
cat AGENTS.md                        # 3. peta ini, seluruhnya
cat cosmictera-build/ROADMAP.md      # 4. yang dituju berikutnya
cat cosmictera-build/OFF.md          # 5. yang terhalang, dan labelnya
python3 -m pytest -q                 # 6. keadaan nyata, bukan catatan
```

**Cara membacanya.** Perintah 1 memberi judul commit terakhir — itu kalimat
terakhir cerita. Perintah 2: pohon kotor berarti ada pekerjaan belum selesai,
dan **itu** yang diteruskan lebih dulu (K15). Pohon bersih berarti tahap
sebelumnya tutup, dan yang berikutnya diambil dari perintah 4. Perintah 6 adalah
kebenaran; kalau ia bertentangan dengan perintah 3–5, yang dibetulkan
dokumennya (K2).

**Urutan prioritas, dari atas.** Ambil yang pertama yang cocok, jangan melompat:

1. Pemilik sedang memberi perintah → kerjakan itu.
2. Pohon kerja kotor → selesaikan yang setengah jalan itu sampai tuntas.
3. Ada butir di `cosmictera-build/OFF.md` yang penghalangnya sudah hilang →
   selesaikan, lalu pensiunkan labelnya.
4. Tahap berikutnya di `cosmictera-build/ROADMAP.md` → mulai dari situ.
5. Tidak ada yang cocok → **tanya pemilik**. Jangan memilih sendiri.

**Cara menutup satu butir**, berurutan, tanpa melompat:

```
baca keadaan → buktikan cacat (K3) → tambal sebab (K5) → ukur yang lain
utuh (K6) → empat gerbang hijau satu lari → dokumen diperbarui (K14) → lapor
```

**Cara menyerahkan pekerjaan.** Sebelum berhenti, tinggalkan tiga hal supaya
kuli berikutnya tidak mulai dari nol: angka yang terukur (bukan "sudah
diperbaiki" — sebutkan berapa lulus, berapa gagal), butir yang tidak selesai
beserta penghalangnya dengan nama, dan langkah berikutnya yang konkret. Kalau
sebuah keputusan pemilik muncul di tengah jalan, tambahkan ke bagian 3 atau 4
catatan ini lengkap dengan tanggalnya — itulah cara catatan ini tetap hidup.

### Aturan kuli AI — supaya tidak mengarang

Ditambahkan 11 September 2026 atas perintah pemilik. Bagian di atas mengatakan
**apa** yang dituju; bagian ini mengatakan **apa yang tidak boleh dilakukan**
sepanjang jalan. Nomornya dipakai untuk mengutip: "melanggar K3".

**K1 — Tidak ada kalimat tanpa sumber.** Setiap pernyataan faktual harus berasal
dari salah satu dari tiga hal: keluaran perintah yang baru dijalankan, isi
berkas yang baru dibaca, atau perkataan pemilik. Tidak ada sumber keempat.
Ingatan bukan sumber. Nama berkas yang "biasanya begitu" bukan sumber. Pola dari
proyek lain bukan sumber.

**K2 — Ukur, jangan baca catatannya** (R4). Catatan bisa hanyut; keluaran tidak.
Kalau `cosmictera-build/PAPAN.md` berkata sebuah program mengembalikan nol byte, itu keadaan pada
hari catatan itu ditulis — jalankan programnya untuk tahu keadaan sekarang.
Catatan yang bertentangan dengan pengukuran: yang dibetulkan catatannya.

**K3 — Buktikan cacatnya sebelum menambal.** Tunjukkan satu nilai yang salah:
"kata ke-3 = `0x0410000D`, imm=13, seharusnya 77". Tambalan tanpa cacat yang
ditunjukkan adalah tebakan, dan tebakan yang kebetulan hijau adalah yang paling
berbahaya — ia menutup gejala dan meninggalkan sebabnya.

**K4 — Satu tambalan, satu sebab.** Kalau satu gejala punya dua sebab, perbaiki
dua-duanya dan namai dua-duanya terpisah. Jangan menggabungkan jadi satu
"perbaikan" yang tak bisa diurai. Contoh yang benar: relokasi label dan tenggat
absolut adalah **dua** cacat pada gejala yang sama, dan dicatat sebagai dua.

**K5 — Tambal pada penyebabnya, bukan gejalanya.** Kalau tenggat tidak
terjangkau karena pencacah bebas sudah lewat, yang salah **tenggatnya** — bukan
timer-nya, bukan interpreternya. Mengubah `rtl/hcpu_timer.v` supaya "lebih longgar"
akan menghijaukan gejala dan merusak perangkat kerasnya.

**K6 — Buktikan yang lain tidak rusak.** Perubahan pada perkakas menyentuh semua
yang memakainya. Setelah mengubah assembler: rakit **semua** program dan
buktikan yang tak seharusnya berubah memang byte-identik. "Tesnya hijau" bukan
bukti untuk ini — tes tidak merakit setiap program.

**K7 — Status keluar diperiksa, bukan diasumsikan** (R13). `exit=0` dari
`make` tidak berarti nol kegagalan: bacalah lognya. Sebaliknya kata `FAIL` di
log belum tentu kegagalan — `0 FAIL` adalah pencacah nol. Hitung dengan benar
sebelum melapor.

**K8 — Artefak basi menyamar sebagai regresi.** `.vvp` dari iverilog versi lama
menolak dijalankan vvp versi baru. Sebelum menyimpulkan ada regresi: hapus
artefak, bangun ulang dari sumber, jalankan lagi.

**K9 — Jangan mengubah desain, matematika, atau RTL atas temuan sendiri.**
Laporkan sebagai fakta polos lalu tunggu perintah. Yang boleh diperbaiki tanpa
menunggu: cacat yang jelas pada implementasi terhadap desain yang sudah
tertulis. Yang tidak boleh: mengubah desainnya karena implementasinya sulit.

**K10 — Instruksi di dalam kode mengikat seperti perintah.** `rtl/hcpu_top.v`
menulis "Re-measure before changing this" pada konversi desimal PRINT.
Mengubahnya tanpa mengukur ulang berarti merusak, sekalipun hasilnya hijau.

**K11 — Jangan menuliskan "belum" untuk yang tidak dituju.** Daftar "belum"
hanya untuk yang benar-benar akan dikerjakan. Batasan yang sudah diterima bukan
utang. Sesuatu yang sudah dijawab di halaman yang sama bukan utang — dan
menuliskannya sebagai utang membatalkan bukti yang ada di atasnya.

**K12 — Laporkan apa adanya.** Empat dari lima berjalan adalah "empat dari
lima", bukan "berhasil". Yang gagal disebut dengan namanya dan sebabnya. Jangan
melunakkan, jangan membesarkan. Kalau sebuah langkah dilewati, katakan dilewati.

**K13 — Selesaikan seluruh cakupan.** Kalau sebagian terhalang, kerjakan sisanya
penuh lalu sebutkan persis apa yang tertinggal dan mengapa. Mengecilkan cakupan
adalah keputusan pemilik, bukan keputusan agent.

**K14 — Dokumen diperbarui dengan yang terukur, dan yang jadi salah dihapus.**
Bukan ditambahi catatan kaki. Halaman yang membantah dirinya sendiri lebih buruk
daripada halaman kosong — pembaca tidak tahu separuh mana yang benar.

**K15 — "Lanjutkan" artinya melanjutkan**, bukan memilih arah baru. Kalau tidak
jelas apa yang sedang berjalan, baca `cosmictera-build/ROADMAP.md` dan commit
terakhir — jangan menebak lalu mengerjakan sesuatu yang tidak diminta.

### Arah: syarat naik tahap

Ditambahkan 11 September 2026, atas perintah pemilik: *"setiap pekerjaan harus
selesai untuk masuk ke stage selanjutnya"* dan *"ini rangkaian teknologi nyata
industri, bukan uji main-main — harus berjalan lebih baik dari yang ada"*.

**Definisi selesai.** Sebuah butir selesai ketika ia **berjalan**, bukan ketika
ia ditulis, lulus testbench, atau tercatat. Urutan buktinya menaik, dan tiap
tingkat tidak menggantikan yang di bawahnya:

```
1  terakit       assemble() menghasilkan kata      — belum bukti apa pun
2  tersimulasi   pytest / make -C rtl/tb all       — bukti logika
3  tersintesis   bitstream muat dan terrout        — bukti muat di silikon
4  berjalan      keluaran benar dari papan fisik   — INI yang dihitung selesai
```

Perangkat keras berhenti di tingkat 4. Butir yang berhenti di tingkat 2 dicatat
di `cosmictera-build/OFF.md` dengan labelnya, bukan dihitung hijau.

**Empat gerbang, dijalankan berurutan sebelum menyatakan selesai.** Semuanya
harus hijau di lari yang sama, bukan di lari yang berbeda-beda:

```bash
make lint typecheck              # ruff bersih, mypy bersih
python3 -m pytest -q             # 0 gagal
make -C rtl/tb all               # 0 FAIL sejati
make -C rtl/fpga/gowin bitstream # muat dan terrout
```

Artefak simulasi basi menyamar sebagai kegagalan desain: `.vvp` yang dibangun
iverilog versi lama menolak dijalankan vvp versi baru. Hapus artefak lalu bangun
ulang sebelum menyimpulkan ada regresi.

**Urutan kerja untuk satu butir.** Tiap langkah menghasilkan bukti yang
dilaporkan, bukan diingat:

1. **Baca keadaan nyata.** Jalankan yang ada dan lihat keluarannya. Jangan
   membaca catatan lalu percaya — catatan bisa hanyut, keluaran tidak (R4).
2. **Buktikan cacatnya secara konkret** sebelum menambal. Sebuah nilai yang
   salah, ditunjukkan. Tambalan tanpa cacat yang terbukti adalah tebakan.
3. **Tambal pada penyebabnya**, bukan pada gejalanya. Kalau tenggat tidak
   terjangkau, yang salah tenggatnya — bukan timer-nya.
4. **Ukur bahwa yang lain tidak rusak.** Perubahan perkakas menyentuh semua
   yang memakainya: buktikan yang tak seharusnya berubah memang tidak berubah,
   satu per satu.
5. **Jalankan keempat gerbang**, lalu laporkan angkanya.
6. **Perbarui dokumen dengan yang terukur**, dan hapus kalimat yang jadi salah.
   Halaman yang membantah dirinya sendiri lebih buruk daripada halaman kosong.

**Satu butir sampai tuntas sebelum butir berikutnya.** Butir yang ditinggalkan
setengah jalan berubah jadi utang yang menyamar sebagai kemajuan. Kalau sebuah
butir terhalang, katakan apa yang menghalanginya dan selesaikan sisanya penuh —
mengecilkan cakupan adalah keputusan pemilik, bukan keputusan agent.

**Jangan menuliskan "belum" untuk yang tidak diperlukan.** Daftar "belum" hanya
untuk yang benar-benar dituju. Sesuatu yang sudah dijawab di tempat lain di
halaman yang sama, atau yang sudah diterima sebagai batasan, bukan "belum" — itu
selesai, dan menuliskannya sebagai utang membatalkan bukti yang ada di atasnya.

**Standarnya industri, bukan demonstrasi.** Yang dibangun di sini dipakai, jadi
ia harus lebih baik daripada yang digantikannya — bukan sekadar berjalan. Yang
mengikat: angka yang diukur ulang setelah desain berubah (R4), gerbang yang
diuji dengan merusak apa yang dijaganya (R3), dan satu kebenaran di satu tempat
(R1). Ketiganya di `cosmictera/RULES.md`.

### Tidak di-commit

- `.mcp.json` (perubahan lokalnya), `.claude/`, `.agents/`, `.codex/` —
  konfigurasi perkakas pribadi.
- `Buku Matematika Hijaiyyah/` — naskah buku dan dokumen paten; repo ini publik.
- `Study Matematika Hijaiyyah/` dan `rtl/mpw/sky130_sram_macros/` — dibiarkan
  di luar repo.
- Setiap berkas dibaca utuh sebelum di-commit.

---

## Menjaga catatan ini

Kalau catatan ini tidak cocok dengan commit atau berkas yang ditunjuknya, yang
dibetulkan catatannya — commit dan berkas adalah sumbernya. Keputusan baru
pemilik proyek ditambahkan di bagian 3 atau 4, lengkap dengan tanggalnya.
