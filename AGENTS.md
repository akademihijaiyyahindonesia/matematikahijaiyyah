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
| arti istilah, nama modul | `teknologi/ISTILAH.md` — akronim sistem; `istilah/` — kosakata subsistem |
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
  Normivektor, Aggregametric, Intrametric, Exometric.

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

  - `e7b5a2d` `pc_valid` berhenti diikat tinggi, dan proses yang dipreempt
    kembali ke tempatnya.
    - Resepnya sudah tertulis di komentar `rtl/hcpu_top.v` sendiri, dan
      `rtl/tb/tb_hcpu_trap.v` sudah punya pemeriksaan "pc_valid gates entry"
      sejak trap dibangun. Nama portnya juga bukan istilah baru.
    - Papan: `trap_resume` `86 86 27` — delapan preemption, handler tak
      menyentuh `TRAP_EPC`, tiap resume benar. Proses A di
      `rtl/programs/kernel.hasm`: 14.491 → 28.982.
    - Biayanya **+1 DFF** per slot: tepat satu bit keadaan.
    - Caveat terukur: sumber exception adalah pulse satu siklus, jadi kalau
      ia pernah bersamaan dengan `pc_valid` rendah ia **hilang**. Pada
      cakupan yang diuji nol kali. Cakupan bukan bukti universal.
    - Pemeriksaan yang menyembunyikan cacat ini dihapus:
      `rtl/tb/tb_hcpu_kernel.v` dulu hanya menuntut `A > 0`, yang dipenuhi
      sebuah bangkai.

  - `346984d` `TRAP_EPC` mendapat bypass yang sudah dimiliki `TRAP_MODE`.
    - Bentuknya sudah ada enam belas baris di atas gejalanya, di berkas yang
      sama, dan komentarnya sudah menolak jalan keluar lewat `NOP`.
    - Papan: `trap_epc` `1 1 1` — jarak 0, 1, 2 instruksi, masing-masing masuk
      handler tepat sekali. Nol adalah yang dulu berputar tanpa henti.
    - Biayanya **+0 DFF**: ia mux di jalur kembali, bukan register.
    - Dijaga dua tingkat dan keduanya disabotase: `rtl/tb/tb_hcpu_trap.v` #18 untuk
      unitnya, `rtl/tb/tb_hcpu_trap_epc_eret.v` untuk pipeline penuh.
    - Cacat saya sendiri yang ikut tertangkap: pesan `check()` lebih dari 32
      karakter dipotong dari kiri, dan punya saya membelah em-dash — log
      `make` jadi bukan UTF-8 dan tes pencacah asersi patah. Semua pesan di
      bench yang disentuh cabang ini kini ASCII dan muat.

  - `a3e2a15` **H-ISA v1.1** — `FRD` (0x0A) dan `FWR` (0x0B), dan FLAGS masuk
    konteks proses.
    - Keputusan pemilik. Tiga jalan diperiksa dulu dan tak satu pun ada di
      spesifikasi; yang ada hanya **prosedurnya** (§6.0 aturan 2 dan 4).
    - Papan: `flags_board` `5 10 1 1` — dua proses, pola masing-masing utuh
      melewati dua ratus preemption.
    - `FRD` membaca `forwarded_flags`, bukan berkas register, supaya ia tidak
      berselisih dengan cabang tentang apa isi FLAGS.
    - Dua cacat saya sendiri, keduanya ditangkap pekerjaan itu sendiri:
      `FWR` tanpa lengan di `case` decode menghentikan mesin lewat `default`,
      dan `FRD` yang ditaruh sesudah gelung simpan membaca perbandingan
      kernel. Keduanya tercatat di kodenya.
    - Satu perselisihan lama jadi terlihat: `FLAG_LT` di bit 3 melawan §14.1
      yang menyebut bit 3–7 "Reserved", dan field `overflow` di `src/hijaiyyah/hisa/machine.py`
      yang sebenarnya memegang bit tanda. §14.1 dibetulkan mengikuti RTL;
      nama yang keliru **dilaporkan, tidak diganti**.

  - `37cbbad` **`EMITS`** — bentuk stringnya ditetapkan, dan mesin akhirnya
    bisa mencetak satu karakter.
    - Keputusan pemilik: satu karakter ASCII per word 32-bit, word nol sebagai
      penutup. Slot dan namanya sudah ada sejak v1.0; yang hilang tata
      letaknya.
    - Papan: `Hijaiyyah`, lalu shell dengan banner `HIJAIYYAH`, prompt `> `
      tanpa newline, dan `A` menggema sebagai `A`.
    - **Bukan pemancar kedua**: mesin keadaan cetak bertambah tiga keadaan,
      port RAM di-mux, dan penolakan `rtl/hcpu_mmio.v` tetap dipegang.
    - Sabotase pertama **tidak menggigit** dua kali: RAM simulasi mulai nol,
      jadi penutup yang tak ditulis tetap nol. Benchnya sekarang menulis `Z` ke
      word penutupnya lebih dulu. Kalau sebuah sabotase lewat, yang lemah
      tesnya — bukan buktinya.

### 13 September — M4.1: HFS punya empat operasi

- `b2a0595` **M4.1** — `create → write → read → verify`, dibaca dari papan
  sebagai tujuh angka: `1 0 1 1 1 1 0`.
  - Angka kedua adalah alasan `create` jadi operasi bernama. Dulu ia efek
    samping tulis pertama — itu berjalan, dan menyembunyikan beda yang dipakai
    sebuah filesystem: berkas yang **ada** tapi kosong bukan berkas yang tak
    pernah dibuat. Sebelum `hos_fs_create` tidak ada cara bertanya. `size`
    tetap 0 sampai ada yang dikomit, jadi bedanya angka, bukan terkaan.
  - Angka kelima adalah yang bisa berbohong dan tidak: `verify` bukan "baca
    mengembalikan sesuatu", melainkan `CEQ` terhadap salinan yang diambil
    **sebelum** tulis — delapan belas komponen termasuk H*, yang tidak
    diturunkan dari tujuh belas lainnya dan karena itu tak bisa benar karena
    kebetulan. H0 sengaja dikotori antara tulis dan baca.
  - **Titik buta yang repo ini sudah catat sekali, dan saya ulangi.** Sabotase
    ketiga tidak menggigit: programnya menyimpan Lam dan mengotori dengan Haa,
    dan H* keduanya 0 — komponen yang paling akhir ditinggalkan rebuild
    separuh bernilai nol di kedua sisi. **Kaf satu-satunya huruf di tabel yang
    H*-nya 1.** `f0dd0f8` sudah mencatat bentuk yang sama persis. Dan
    `HLOAD 23` itu Lam, bukan Kaf: ROM 1-indeks dan Kaf duduk di 22.
  - Tiga sabotase, ketiganya kini merah (R3): `create` tidak menandai entri →
    `1 1 1 1 1 1 0`; satu komponen tersimpan dirusak → verify 0; `CSET`
    terakhir pada baca dihapus → verify 0, tetapi **hanya** sesudah huruf yang
    disimpan diganti Kaf.
  - **Yang tidak diklaim: persistensi.** HFS adalah RAM data dari 0xE00 dan
    hilang saat reset. Ia tetap butir sendiri di `cosmictera-build/OFF.md`, dan
    baris centangnya di `cosmictera-build/CHECKLIST.md` membawa kata "di RAM" —
    `tests/test_integrity/test_build_list.py` menolak centang HFS yang tidak
    menyebut jalur mana yang diklaim.
  - RTL tidak disentuh, jadi kedua sidik jari wrapper tetap seperti yang
    diukur `EMITS`. Di papan `test_hfs` masih menjawab `1 1 1 2 1`.
  - Cacat saya sendiri yang lognya sendiri tunjukkan, dan **sudah pernah
    dicatat di `346984d`**: `check(input [255:0] what)` memuat 32 byte dan
    memotong sisanya **dari kiri**, jadi `ok   : agi: ditolak, file dibuat
    sekali` adalah pesan yang lebih panjang. Tiga di bench baru ini, satu di
    `rtl/tb/tb_hcpu_emits.v`, satu di `rtl/tb/tb_hcpu_shell.v` — semuanya
    dipendekkan. Yang **tidak** disentuh: 34 pesan sepanjang itu di enam bench
    lama, di luar cakupan M4.1, dilaporkan bukan disapu.

### 14–15 September — M4.2: kartu bertahan melewati mati daya

- `708a9cd` SDIO 1-bit, dan celah yang membuatnya bisu.
  - Akarnya ditemukan **papan**, bukan bench: `rtl/hcpu_sdio.v` mengirim CMD8 nol
    clock sesudah CMD0, dua belas pemeriksaan tetap hijau, dan kartu SDHC sehat
    di papan diam seratus milidetik — E_CMD8, empat lari. N_CC menuntut
    sekurangnya delapan clock menganggur antar perintah.
  - Pengukuran pertama saya **salah**: saya menghitung dari awal frame ke awal
    frame, sehingga respons 48-bit kartu terlipat ke dalam celahnya, dan saya
    menyimpulkan hanya CMD0→CMD8 yang melanggar. Dihitung benar — clock ketika
    tak ada yang menggerakkan jalurnya — celahnya **nol di setiap batas**.
  - Harganya **+1 LUT4 dan +9 DFF**: satu pencacah delapan bit dan satu keadaan.
  - Lima checkpoint fisik, termasuk mati daya sungguhan.

### 15–17 September — M5: monitor sistem, dan die yang harus dipisah

- `e4c251e` display meninggalkan die CPU, dan slot CPU bisa dibangun lagi.
  - **Cacat yang paling mahal di sesi ini saya sendiri yang buat.** Sideband
    telemetri ditambahkan ke `hcpu_gowin_top` supaya `hcpu_hdmi_top` bisa
    membacanya, dan itu memberi satu modul dua tugas yang tak bisa didamaikan:
    sebagai submodul keluaran tak tersambung itu gratis, sebagai top-level ia
    menuntut pin. `ERROR: Unconstrained IO:tele_pc_OBUF_O_9` — slot tempat
    `shell`, `kernel`, `hos`, dan `test_hfs` berjalan **berhenti bisa dibangun
    selama empat hari**, dan `.fs` basi di direktori menyembunyikannya.
  - `tests/test_integrity/test_board_wiring.py` sudah berusaha mengatakannya dan **tidak bisa**: ia
    crash `AttributeError` alih-alih gagal dengan pesan, karena parser-nya tak
    bisa membaca lebar bermakro. Crash terbaca seperti tes rusak, bukan desain
    rusak. Regexnya juga hanya membaca `input|output`, jadi `sd_cmd` dan
    `sd_dat` **tak pernah diperiksa sama sekali** sejak kartu dipasang.
  - Pemisahan `hcpu_gowin_core` + `hcpu_gowin_top` setipis pin, dengan kontrol
    terukur: DFF tidak bergerak (181 → 181), LUT3 turun 229 sementara LUT4 naik
    213 — pemetaan ulang yosys, bukan logika baru.
  - **Penghalangnya tempat, bukan semantik** — pola yang sama dengan `CDOT` di
    `7eb177a`. Dua arsitektur dashboard ditolak 33 LUT4 berjauhan (16.882 dan
    16.849 melawan kontrol 15.933); dipisah jadi node sendiri, **685 LUT4 (3%)**.
  - Cacat encoder TMDS nyata ditemukan dan diperbaiki (30/256 byte gagal
    round-trip → 0/1024), **dan layar tidak berubah** — yang justru jadi bukti:
    cacat statis itu deterministik, korupsinya tidak.
  - Yang **tidak** selesai: jalur pixel HDMI. Dibekukan sebagai cacat terbuka
    di `cosmictera-build/OFF.md` dengan delapan penyebab tereliminasi beserta
    angkanya. Sidik jari `rtl/fpga/gowin/hcpu_hdmi_top.v` **sengaja tidak
    dicap**, dan satu tes merah adalah konsekuensi yang tercatat, bukan
    regresi.

### Keputusan pemilik, 15–17 September 2026

1. **Compute dan display dipisah jadi node sendiri-sendiri.** Bukan mengecilkan
   UI, melainkan mengubah pertanyaannya: dari "muat di sisa fabric CPU" jadi
   "berdiri sendiri". Terukur: 16.849 ditolak → 685 ter-place.
2. **`hcpu_gowin_top` wajib jadi top-level CPU murni.** Telemetri jadi
   antarmuka opsional yang hanya ada ketika wrapper HDMI memakainya — tidak
   memaksa slot CPU membawa 84 bit I/O yang tak pernah keluar papan.
   Urutan yang diperintahkan: pulihkan build → cap ulang → verifikasi `.fs` →
   **baru** putuskan nasib M5.2B.
3. **Investigasi pixel HDMI dibekukan, 17 September 2026.** *"Ketika sebuah
   jalur investigasi sudah menghasilkan puluhan eksperimen tanpa konfirmasi
   akar masalah, keputusan terbaik adalah membekukan statusnya sebagai cacat
   terbuka yang terdokumentasi."* Yang dibekukan penyelidikannya, bukan
   faktanya.
4. **Nasib `rtl/fpga/gowin/hcpu_hdmi_top.v` (M5.2B) ditunda**, dan satu tes
   merah diterima sebagai keadaan yang konsisten dengan penundaan itu.
5. **Eksperimen diagnostik butuh aba-aba khusus**, dengan variabel tunggal
   disebut eksplisit dan seluruh sisanya dinyatakan tetap. Bitstream yang
   kehilangan variabel yang diujinya **tidak boleh di-flash**: hasilnya tak
   bisa ditafsirkan.

### Keputusan pemilik, 17 September 2026 — enam tahap sebelum KV260

Papan berikutnya adalah **Kria KV260**, bukan ASIC. Sebelum pindah, enam tahap,
dan **tak satu pun butir perangkat keras ada di antaranya**:

```
1  HFS ke kartu SD nyata      hos_fs_* menulis sektor, bukan RAM data
2  Loader program             citra datang dari kartu, bukan dari kabel
3  Overlay runtime            citra dihalamankan masuk dan keluar
4  HVM di papan               bytecode ditafsirkan mesinnya sendiri
5  Semantic memory            SEARCH / MATCH / ASSOCIATE atas vektor hybit
6  TCP/IP lewat SLIP          IP di atas UART yang sudah bekerja
```

Semula lima tahap. Semantic memory disisipkan sebagai tahap 5 pada hari yang
sama, dan **HVM tidak diganti olehnya**: *"Semantic Memory membutuhkan runtime
yang matang, mekanisme dispatch, dan persistensi"* — sedangkan HVM membuktikan
bytecode yang sama memberi hasil yang sama di simulator dan di perangkat keras,
fondasi yang lebih rendah. Prioritas tertinggi tetap tahap 1–4, karena
keempatnya langsung menyerang batas 4.096 kata.

Alasannya: kelimanya mengubah **apa yang dipindahkan** — dari CPU dengan
demonstrasi terpasang, jadi komputer yang bisa memuat, menyimpan, menjalankan,
dan berkomunikasi. *"Yang dipindahkan bukan hanya inti CPU, tetapi seluruh
ekosistem HC + HASM + HVM + HOS + HFS + JIM Engine."*

**Ini membuka apa yang 13 September belum dibuka.** Persistensi dan integrasi
kernel ↔ filesystem dulu tercatat "belum dibuka"; tahap 1 dan 2 membukanya.
Metadata, direktori, dan izin **tetap belum** — jangan memulainya.

Dua pengukuran yang membentuk gerbang ini, dan keduanya harus dibaca sebelum
menyentuh tahapnya:

- **Sumber daya paling langka bukan LUT4, melainkan 4.096 kata memori
  instruksi.** HOS + kernel + shell digabung sudah ≈1.150 kata (387 + 363 +
  399). Seluruh Layer 11 dan 12 berbiaya nol fabric dan berbagi citra yang
  sama. Tahap 3 ada untuk itu.
- **ISA ini tidak punya lompatan terhitung.** `OP_JMP` dan `OP_CALL` keduanya
  `PC ← IMM`; tidak ada `JALR`. Jadi tidak ada tabel lompat, pointer fungsi,
  atau dispatch terindeks. Mesin keadaan protokol (tahap 5) dan gelung dispatch
  interpreter (tahap 4) membayar rantai perbandingan — dan membayarnya dengan
  kata instruksi, sumber daya yang paling langka itu. `0d63a7e` sudah menemui
  bentuk yang sama: tabel syscall ditaruh di memori data, bukan tabel lompat.

Spesifikasi lengkap dua belas lapis beserta triase A/B/C-nya ada sebagai
artefak terpisah, bukan di repo — angkanya menunjuk ke header wrapper dan
`cosmictera-build/`, bukan menyalinnya (R1).

Dua penetapan lain dari keputusan yang sama:

- **Codex JIM adalah primitif matematis** — bukan bahasa pemrograman, bukan
  semantic memory. Perannya generator urutan: LFSR, pembangkit aliran,
  permutasi alamat, transformasi codex. Yang terukur ada di
  `cosmic-codex-jim/`; yang **gagal** terukur ada di `cosmic-codex-jim/LIMITS.md`
  dan membatasi apa yang boleh diklaim darinya.
- **Di Tang Nano 20K, yang bisa dibayar dengan instruksi tidak dibayar dengan
  LUT4.** *"Jika masalah bisa diselesaikan dengan instruksi, jangan bayar
  dengan LUT4"* — pola yang pemilik tarik dari M5: bank H-register di RTL
  ditolak placement dua kali (+3.286 dan +336 LUT4), simpan-pulihkan perangkat
  lunak lolos dengan 72 instruksi dan nol LUT4. LUT4 adalah sumber daya yang
  benar-benar habis di papan ini; kata instruksi langka, tetapi tidak habis.
- **Tata letak HFS di kartu, 17 September 2026.** Sektor mentah 1–3 di celah
  sebelum partisi pertama, jalur yang M4.2 sudah buktikan: sektor 1 membawa
  MAGIC `HFS1`, VERSION, lalu tabel berkas; sektor 2 dan 3 membawa data
  berkas 0–3 dan 4–7. CREATE dan WRITE langsung menulis ke kartu, tanpa SYNC;
  boot memuat HFS sesudah heap dan sebelum proses; kartu tanpa `HFS1` v1
  dimuat sebagai HFS kosong dan tidak ditulisi. VERSION adalah tambahan
  pemilik. Rinciannya tinggal di kepala `rtl/programs/hos_hfs_disk.hasm`,
  tidak disalin ke sini (R1).
- **Peran HCPU di KV260 belum diputuskan.** Tiga jalur, dinamai pemilik
  18 September 2026: **Jalur A** — HCPU CPU utama, ARM hanya boot dan layanan;
  **Jalur B** — ARM CPU utama, HCPU koprosesor di bawah Linux, dan banyak bagian
  HOS turun jadi pustaka; **Jalur C** — HCPU sebagai emulator di atas Linux.
  Dua penilaian pemilik tercatat dan saling tarik: investasi pada HC, HASM, HFS,
  HOS, dan HVM *"lebih konsisten dengan Jalur A"*, dan Jalur B *"jauh lebih
  menarik"*. Keduanya penilaian, bukan keputusan — belum ada pengukuran yang
  cukup untuk memilih, dan tidak ada pekerjaan KV260 yang boleh berangkat dari
  salah satu jalur sebelum pemilik memilih.

### Keputusan pemilik, 18 September 2026 — tahap 1 ditutup di papan dulu

- **Tahap 1 tutup di papan pada hari yang sama, 18 September 2026**: `1 1 1`,
  kabel dicabut, `2` — angkanya dan alasan tiap larinya di
  `cosmictera-build/PAPAN.md`. Slot CPU hasil pemisahan `e4c251e` ikut
  dijalankan di papan pada sesi yang sama (23 byte, `112`), jadi kedua lubang
  verifikasi yang tercatat hari itu tertutup. **Tahap 2 belum dibuka** — itu
  keputusan pemilik, bukan konsekuensi otomatis.
- **Tahap 2 tidak dibuka sebelum tahap 1 tutup di papan fisik.** Yang belum
  terbukti bukan algoritma HFS atau driver kartu, melainkan integrasinya di
  silikon, dan pola repo ini berulang: simulator hijau, papan menemukan
  masalah. Syarat tutupnya tetap CREATE → WRITE → cabut daya → nyalakan →
  READ identik. Persiapan loader boleh berjalan sambil menunggu papan, **tanpa
  mengklaim tahap 2 dimulai**; format citra dan header program tetap keputusan
  pemilik.
- **Bentuk tahap 2 ditetapkan, 18 September 2026 — loader program dari kartu.**
  Empat keputusan, diambil di atas angka yang diukur hari itu (sisa memori
  instruksi 3.056 kata dari 4.096; `IMEM_ADDR` 0xFF3 dan `IMEM_DATA` 0xFF7
  hanya bisa ditulis mode supervisor; satu sektor 128 kata; satu berkas HFS
  tepat 18 kata):

  1. **Citra program adalah container berheader**, bukan citra sektor mentah:
     MAGIC, VERSION, WORDS, ENTRY, RELOC_CNT, CRC, lalu tabel relokasi, lalu
     kata-kata programnya. Alasannya terukur, bukan kenyamanan: label absolut
     pernah rusak ketika basis muat berubah, dan tanpa tabel relokasi loader
     tidak punya cara membetulkannya.
  2. **Alamat muat datang dari header**, bukan satu alamat tetap — supaya
     beberapa program tidak dipaksa ke tempat yang sama.
  3. **Kernel yang memuat, lewat syscall.** Bukan proses pengguna: perangkat
     kerasnya sendiri menolak akses mode pengguna ke jendela itu.
  4. **Area program terpisah dari HFS.** HFS tetap satu berkas = satu vektor
     codex = 18 kata, kontrak yang baru saja tutup di papan; mengubah unit
     alokasinya sekarang berarti membuka kembali yang sudah ditutup.

  Empat rincian yang sempat terbuka ditutup pemilik pada hari yang sama:

  - **Header tujuh kata**, `LOAD_ADDR` dan `ENTRY` **terpisah**: 0 MAGIC,
    1 VERSION, 2 WORDS, 3 LOAD_ADDR, 4 ENTRY, 5 RELOC_CNT, 6 CRC. Program yang
    punya bootstrap kecil atau tabel awal tidak harus mulai tepat di alamat
    muatnya.
  - **Tata letak kartu diperluas, HFS tidak disentuh**: sektor 1–3 tetap HFS;
    **sektor 16 tabel program** (PROGRAM_ID, FIRST_SECTOR, SECTOR_COUNT,
    FLAGS), **sektor 17 ke atas citra program**. Bukan sektor tetap per
    program.
  - **Integritas tahap 2 adalah jumlah 32-bit**, bukan CRC-32, dan alasannya
    terukur: arena heap hanya 127 kata, jadi tabel CRC-32 256 entri tidak muat,
    sementara yang dibutuhkan tahap ini hanya memisahkan citra utuh dari citra
    rusak. Yang dijumlah **hanya kata program**, header tidak ikut. Naik ke CRC
    nanti lewat `VERSION`, tanpa memecahkan loader lama.
  - **`SYSCALL` 9 `LOAD_PROGRAM`**, `R2` = PROGRAM_ID, `R1` = 1 berhasil atau 0
    gagal. Tabel izin sekarang 0xECE–0xED5 untuk panggilan 1–8 dan masih ada
    tempat sampai 0xEFF.

  **Urutannya juga ditetapkan: 2A syscall dulu, 2B baru muat otomatis saat
  boot.** Loader diuji sebagai layanan kernel sebelum ia jadi bagian boot.

  Yang pemilik nyatakan belum dibuka: multitasking dinamis, swap, overlay
  runtime, demand paging, semantic memory, dan format executable NUI.

- **Batas semantic memory.** Yang terbukti adalah huruf → vektor → operasi
  matematis; huruf → makna → pengetahuan tidak terbukti dan melewati larangan
  `CONTRIBUTING.md` (huruf bukan bunyi atau makna). Jadi semantic memory di
  repo ini adalah memori atas **operasi vektor codex**, bukan arti huruf.
  Syarat terima tahap 5 tetap belum ditetapkan.

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
   **Keempat penghalang M3 ditutup 13 September 2026** dan terbukti di papan
   fisik: resume setelah preemption, FLAGS sebagai konteks, hazard
   `TRAP_EPC`→`ERET`, dan jalur keluaran karakter. Sesudah itu **pemilik
   membuka M4**, dan hanya butir pertamanya. Yang terhalang dicatat di
   `cosmictera-build/OFF.md` dengan alasan terukur, bukan dirapikan.

### Kesimpulan resmi M3 — pemilik, 13 September 2026

> *"akar A sudah ditemukan; belum diperbaiki; B/C/D masih terbuka; M4 belum
> boleh dimulai."*

Empat kalimat itu adalah keadaan M3 **pada hari itu**, dan yang keempat
mengikat selama ia berlaku: satu penghalang pada satu waktu, diputuskan
pemilik, lalu empat gerbang dan uji fisik Tang Nano 20K. Keempatnya sudah
ditutup dengan urutan itu, dan pemilik membuka M4 sesudahnya — lihat bagian
berikutnya.

| | penghalang | keadaan |
|---|---|---|
| A | resume setelah preemption timer | **selesai** — akar `073b968`, perbaikan `e7b5a2d`, terbukti di papan; caveat pulse exception tercatat |
| B | FLAGS bukan bagian konteks proses | **selesai** — H-ISA v1.1: `FRD` 0x0A, `FWR` 0x0B, keputusan pemilik 13 September. Papan menjawab `5 10 1 1` |
| C | `STORE` `TRAP_EPC` → `ERET` | **selesai** — `epc_at_eret` mengikuti bentuk `prev_at_eret`; papan menjawab `1 1 1` pada jarak 0, 1, 2 instruksi. Biaya +20 LUT4, +0 DFF |
| D | keluaran karakter | **selesai** — `EMITS` 0xA2, satu karakter per word, penutup nol; keputusan pemilik 13 September. Papan mencetak `Hijaiyyah`, shell punya banner dan prompt |

Semuanya di `cosmictera-build/OFF.md` dengan angkanya. Syarat terakhir M3 —
jalur keluaran karakter disahkan pemilik **dan** berjalan di papan fisik —
dipenuhi `37cbbad`: papan mencetak `Hijaiyyah`, dan shell punya banner serta
prompt.

### Keputusan pemilik, 13 September 2026 — M4 dibuka

> *"M4 — HFS + System Services. … M4.1 dimulai dari HFS physical storage path,
> bukan langsung membuat filesystem besar: `create → write → read → verify` di
> papan Tang Nano 20K, lalu baru metadata, persistence, dan service layer."*

Urutannya bagian dari perintah: jalur simpan fisik lebih dulu, sendirian.

- **M4.1 selesai** (`b2a0595`), terbukti di papan: `1 0 1 1 1 1 0`.
- **Belum dibuka**: metadata, persistensi, lapisan layanan HAR, dan integrasi
  kernel ↔ filesystem. Jangan memulainya sebelum pemilik menyebutnya — M4
  bukan satu butir, dan "M4 dibuka" bukan izin untuk keempatnya.

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
