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
    nanti lewat `VERSION`, tanpa memecahkan loader lama. *(Cakupannya diperluas
    ke seluruh container oleh K-8 dan K-10, 22–23 September 2026, dan
    diterapkan sebagai `VERSION` 2 di P6, 26 September 2026 — lihat di bawah.)*
  - **`SYSCALL` 9 `LOAD_PROGRAM`**, `R2` = PROGRAM_ID, `R1` = 1 berhasil atau 0
    gagal. Tabel izin sekarang 0xECE–0xED5 untuk panggilan 1–8 dan masih ada
    tempat sampai 0xEFF.

  **Urutannya juga ditetapkan: 2A syscall dulu, 2B baru muat otomatis saat
  boot.** Loader diuji sebagai layanan kernel sebelum ia jadi bagian boot.

  Tiga patokan terakhir, ditetapkan sesudah angkanya diukur:

  - **MAGIC = `HPG1`, 0x48504731.** "Hybit Program Generation 1", entitas yang
    berbeda dari `HFS1`.
  - **Penyangga relokasi 0x300-0x37F, tepat 128 kata** - satu sektor penuh,
    jauh dari heap HOS (0xE01-0xE7F) dan tabel syscall (0xECE-0xED5). Ukurannya
    dari pengukuran: tabel relokasi terbesar 85 kata (`rtl/programs/shell.hasm`, 1.040 kata),
    `hos_hfs_disk` 38, rata-rata 7,2 dari 41 program. Penyangga itu perlu karena
    CPU **tidak bisa membaca memori instruksi** - hanya `IMEM_ADDR`/`IMEM_DATA`
    untuk menulis - jadi relokasi diterapkan sebelum kata ditulis, dan tabelnya
    harus ada di RAM saat kata program mengalir.
  - **FLAGS bit 0 = VALID**; 0 slot kosong, 1 berisi. Bit lain disimpan dan
    **belum diberi arti** (bootable, readonly, signed, encrypted) supaya cabang
    desain baru tidak terbuka sebelum loader dasar terbukti. Sektor kosong yang
    seluruhnya nol karena itu tidak pernah terbaca sebagai program nomor 0.

  **Urutan field entri tabel program berubah** antara dua pesan pemilik, dan
  yang berlaku yang terakhir: PROGRAM_ID, FLAGS, START_SECTOR, SECTOR_COUNT.
  Yang lebih dulu menulis FLAGS di posisi terakhir; dicatat di sini supaya
  pergeserannya tidak diam.

  Yang pemilik nyatakan belum dibuka: multitasking dinamis, swap, overlay
  runtime, demand paging, semantic memory, dan format executable NUI.

- **Batas semantic memory.** Yang terbukti adalah huruf → vektor → operasi
  matematis; huruf → makna → pengetahuan tidak terbukti dan melewati larangan
  `CONTRIBUTING.md` (huruf bukan bunyi atau makna). Jadi semantic memory di
  repo ini adalah memori atas **operasi vektor codex**, bukan arti huruf.
  Syarat terima tahap 5 tetap belum ditetapkan.

### Keputusan pemilik, 18 September 2026 — papan ini laboratorium validasi

Tang Nano 20K bukan papan demo, melainkan **laboratorium validasi CosmicTera**,
dan KV260 baru disentuh sesudah papan ini meluluskan enam tahap:

```
1  simulasi            RTL, bench, pytest      lulus, dan BELUM dianggap selesai
2  di papan            tiap modul masuk FPGA lalu diuji: fungsi, stress,
                       serangan, fault, persistensi, burn-in
3  dokumentasi terukur tiap modul punya halaman hasilnya sendiri
4  full stack          semuanya menyala bersama, 24 / 72 / 168 jam tanpa reset
5  freeze              fitur, protokol, ABI, container, format jadi baseline
6  port ke KV260       memperbesar sistem, bukan menemukan cacat dasar
```

**Burn-in bukan uji stabilitas, melainkan pembangun garis dasar** — pemilik
menegaskannya 18 September 2026. *"Anomali tidak bisa didefinisikan tanpa
mengetahui normal."* Angka normal yang belum pernah diukur membuat 20%, 40%,
dan 80% sama-sama tak berarti. Jadi lari panjang tahap 4 adalah yang membuat
lapisan pengawasan — NUI, Ka'bah, telemetri, daemon guard — punya sesuatu untuk
dibandingkan. Sampai ia ada, "deteksi penyimpangan" berlabel **AT**.

*"Tang Nano = Proof of Function. KV260 = Proof of Scale."* Sebuah komponen
tidak dianggap siap jadi bagian stack KV260 sebelum punya dokumen validasi
Tang Nano 20K sendiri.

**Satu batas fisik yang sudah terukur dan membentuk tahap 2 dan 4.** "Semua
modul masuk ke FPGA" tidak bisa berarti *bersamaan*: jumlah naif ketiga slot
adalah 43.799 LUT4 = **211%** dari papan. Yang mungkin adalah **berurutan**,
lewat rekonfigurasi — biaya rack = slot terbesar, 15.994 LUT4 = 77%
(`rtl/scripts/rack.py`, dan `ec2355b`). Jadi tahap 4 "semuanya menyala
bersama" berlaku untuk apa yang muat dalam satu slot, dan sisanya diuji
bergiliran; mana yang mana adalah keputusan pemilik saat tahap itu dibuka.

### Keputusan pemilik, 20 September 2026 — tahap 2 ditutup dengan opsi B

Tahap 2 ditutup dengan **bukti yang ada**, bukan dengan flash SPI. Alasan
pemilik: loader, boot dari kartu, program 11 sektor, relokasi lintas sektor, dan
shell yang berjalan dari kartu sudah terbukti di silikon, dan host tidak
mengirim satu byte pun saat boot. Yang tidak ada hanyalah menyala dari daya
tanpa JTAG dan tanpa PC — *"lebih merupakan varian metode boot, bukan pembuktian
baru terhadap arsitektur loader."* Karena itu flash SPI tidak dicatat sebagai
utang (K11); citra LiteX pabrikan tetap di tempatnya.

Urutannya ditegaskan: Jamrah → Hijrah → Ka'bah → lab serangan Codex JIM →
burn-in → NUI Core → Command Center Docker → KV260. Jamrah lebih dulu karena
*"paling murah diverifikasi dan hasilnya absolut"*: 256 byte, 256/256 atau
cacat, tanpa wilayah abu-abu. Lab serangan menunggu ketiga validasi, karena
*"lab serangan tanpa baseline validasi akan menghasilkan angka yang sulit
ditafsirkan."*

### Keputusan pemilik, 20 September 2026 — sembilan prioritas sesudah loader

Prioritas lintas sektor dan ACK per sektor **tutup** 18 September 2026, di
simulasi dan di papan (`605a708`, `561b2a6`). Urutan berikutnya dari pemilik:

```
1  tutup tahap 2              flash SPI, atau terima bukti yang ada
2  validasi Jamrah            laporan validasi
3  validasi Hijrah            laporan validasi
4  validasi Ka'bah            laporan validasi
5  lab serangan Codex JIM     JIM sebagai pembangkit serangan
6  burn-in 24 / 72 / 168 jam  laporan keandalan
7  NUI Core                   runtime, penjadwal, agen, monitor
8  Command Center di Docker   di MacBook, dengan UI
9  KV260 sebagai platform master
```

Tiga hal terukur yang harus dibaca bersama daftar itu:

- **Jamrah di repo ini adalah gerbang, bukan detektor statistik.** Ia pohon
  reduksi 8-daun dengan tujuh simpul dalam (`rtl/hijaiyyah_jamrah_gate.v`,
  `rtl/programs/jamrah_gate.hasm`), bagian **Lapis 1 Guard** Ka'bah: menolak
  masukan malformed dalam O(1), tanpa kunci (`istilah/KABAH.md`). Masukannya
  satu byte, jadi ruang masukannya **256 nilai** — ia bisa diuji **tuntas**,
  dan pengujian acak justru lebih lemah dari itu. "Detection rate", false
  positive, dan false negative untuk predikat eksak berarti 256 dari 256 atau
  sebuah cacat, bukan persentase.
- **Hijrah sudah punya angka, tetapi hanya di Python.** Kepadatan 4,58 / 4,81 /
  4,81 bit per huruf atas GF(2) / GF(4) / GF(5), dan empat pasang huruf yang
  runtuh atas GF(2), dijaga 41 tes (`hijrah/README.md`). Validasi di papan
  berarti HCPU menghitungnya sendiri dari ROM-nya.
- **Daftar ini tidak memuat overlay runtime (tahap 3) dan HVM (tahap 4)** dari
  gerbang enam tahap 17 September, padahal pemilik pernah menegaskan HVM harus
  tetap. Dicatat sebagai dua urutan yang belum dipertemukan, bukan dirapikan
  sepihak. Command Center di Docker juga menuntut unduhan perangkat lunak pihak
  ketiga, yang butuh izin pemilik.

### Keputusan pemilik, 20 September 2026 — kontrak telemetri v1

Diambil sementara burn-in tingkat 1 berjalan, ketika pertanyaannya jadi
konkret: apa yang sebenarnya bisa dilaporkan sistem ini tentang dirinya. Tujuh
kelompok — SYSTEM, MEMORY, JAMRAH, KABAH, STORAGE, BOOT, HIJRAH — dan 27
medan. Isinya tinggal di `cosmictera/TELEMETRY.md` beserta sumber tiap medan;
tidak disalin ke sini (R1).

Dua penetapan yang menyertainya menutup pertanyaan yang sempat terbuka:

- **Loader bukan telemetri kontinu, melainkan telemetri kejadian boot** — yang
  disimpan hasil terakhirnya, bukan pembacaan tiap detik.
- **Hijrah bukan daemon, melainkan mesin validasi** — yang hidup bukan
  statusnya melainkan hasil validasi terakhirnya.

**Empat medan belum punya sumber sama sekali**, dan itu dicatat sebagai
keadaan, bukan utang yang dikarang: `anomaly_score` dan `corruption_score`
adalah turunan yang menunggu NUI (prioritas 7, belum dimulai), `state_hash`
menuntut bentuk ringkasan yang belum pemilik tetapkan (tidak ada inti SHA-256
di RTL, R10), dan `last_relocation` adalah langkah yang loader kerjakan tanpa
melaporkannya terpisah. `tests/test_integrity/test_telemetry_contract.py`
menjaga keempatnya tetap ditandai begitu sampai ada yang mengukurnya.

Tiga hal yang kontrak ini **belum** tetapkan, dan tidak boleh dikarang: setiap
berapa lama tiap medan dilaporkan, lewat jalur apa, dan ambang Normal /
Warning / Critical. Yang terakhir menuntut garis dasar selesai lebih dulu.

**Hierarki waktu, ditetapkan hari yang sama: waktu host bukan sumber
kebenaran.** Tingkat 1 pencacah siklus FPGA, tingkat 2 uptime papan, tingkat 3
cap waktu host — yang terakhir untuk mencatat, bukan untuk menilai. Aturan ini
lahir dari pengukuran: lari burn-in diam 140 detik, dan diam itu milik **host**
— jam papan tertinggal 138 detik lalu mengejar, sementara papan tidak pernah
berhenti. Host yang sibuk tidak boleh terbaca sebagai anomali CosmicTera.

**Tiga kontrak masih terbuka** dan pilihannya tercatat beserta angka masing-
masing di `cosmictera/TELEMETRY.md`: bentuk `state_hash` (pemilik menilai opsi
C — host yang menghitung — paling realistis, dan itu penilaian, bukan
keputusan), bentuk `last_relocation`, dan pita `anomaly_score`. Yang terakhir
tidak bisa ditarik dari data sebelum garis dasar ada: empat dari enam
masukannya belum pernah bergerak dari nol.

**`relocation_ok` ditinggalkan pemilik pada hari yang sama**, dan diganti tiga
medan yang mengatakan lebih sedikit: `relocation_count`, `container_loaded`,
`entry_reached` — *"tidak menyatakan lebih dari yang benar-benar telah
dibuktikan."* Alasannya terukur: lab serangan menemukan satu entri relokasi
yang digeser **lolos tanpa penolakan**. Yang ketiga bukan milik loader sama
sekali — sesudah `ERET` loader tidak punya suara, dan hanya program yang
dimuat yang bisa bersaksi.

**Keempat medan turunan diberi status, bukan angka**, supaya dashboard tidak
mengklaim lebih dari yang diukur: `state_hash` pending architecture,
`last_relocation` partial evidence, `anomaly_score` dan `corruption_score`
waiting baseline.

### Perintah pemilik, 21 September 2026 — NUI dalam dua belas lapis

NUI — **Natural Universal Intelligence** — dibangun sebagai sistem komputasi
yang memahami, memverifikasi, memodelkan, dan mensintesis seluruh stack
CosmicTera. **Namanya tetap**: tidak ada nama baru, singkatan baru, atau
rebranding. Bukan chatbot, bukan persona, bukan pembungkus LLM.

Dua belas lapis, dari fakta terverifikasi sampai rekayasa otonom, dipetakan
terhadap aset yang sudah ada di `NUI/LAYERS.md` — tiap lapis membawa lima hal
yang pemilik tuntut: tujuan, aset yang ada, yang belum ada, cara verifikasi,
syarat selesai. Tidak disalin ke sini (R1).

**Aturan yang mengikat pekerjaannya**, dan yang pertama adalah urutannya:
*"Gunakan seluruh aset yang sudah ada di repositori terlebih dahulu. Jangan
menambah kompleksitas baru sebelum semua aset yang sudah ada dimodelkan,
dipetakan, dan diverifikasi oleh NUI."* Lalu: tidak ada klaim tanpa
pengukuran, tidak ada kemampuan yang diasumsikan, tidak ada klaim AGI atau
kesadaran, tidak ada benchmark fiktif, dan label tidak naik tanpa bukti baru
(R2).

**Yang sudah ada terukur**: 13 modul di `src/hijaiyyah/nui/`, 131 tes di
`tests/test_ai/`, PyTorch 2.14.0. **Dua lapis kosong sama sekali** dan dicatat
begitu, bukan diisi rencana: Linux (lapis 5 — tidak ada satu pun sisi host di
repo ini) dan rekayasa otonom (lapis 11).

**Penomoran lapisnya berubah tiga kali pada hari yang sama**, dan yang berlaku
yang terakhir. Lapis 0–6 sama di dua pesan terakhir; yang bergeser ekornya —
diagnostik otonom ke 7, perencanaan perbaikan otonom (baru) ke 8, mesin
penalaran ke 9, komputasi universal ke 10, rekayasa otonom ke 11 — dan satu
lapis pesan kedua, **verifikasi fisik, hilang**. Asetnya tidak ikut hilang:
tangga bukti empat tingkat, `cosmictera-build/PAPAN.md`, sidik jari place and
route, dan lima fakta `board` tetap berlaku.

**Pesan keempat, hari yang sama, menomorinya sekali lagi**: operasi otonom
(baru) jadi 7, diagnostik otonom 8, rekayasa 10, komputasi universal 11, dan
lapis *perencanaan perbaikan otonom* hilang — isinya kini keluaran diagnostik.
Ia juga meminta graf repositori memuat **dokumentasi, kelas, dan fungsi**:
sekarang ada, dan dokumennya diambil dari `git ls-files`. Angka 745 berkas
Markdown yang sempat ditulis salah — ia menghitung folder pribadi di disk;
repositori memuat 90.

**Karena penomorannya bergerak sementara asetnya tidak, `NUI/LAYERS.md`
dikunci pada nama lapis**: nomornya atribut, dan satu tabel di halaman itu
satu-satunya tempat ia hidup. Tabel pergeserannya tidak disalin ke sini (R1).
Penomoran keempat, Fase 0–5 di `NUI/ROADMAP.md`, juga tidak dihapus.

**Satu selisih label dilaporkan, lalu dijawab pemilik.** Pesan kedua menandai
lapis Linux EH; tabel `cosmictera/RULES.md` sendiri mendefinisikan EH sebagai
"terukur, belum dikriptanalisis" dan AT sebagai "belum dikerjakan", dan lapis
tanpa satu pun aset jatuh pada AT. Pesan ketiga menjawabnya: **AT**.

**Medan `confidence` ditambahkan ke inventaris fakta, dan ia bukan
probabilitas.** Angka bergradasi akan dikarang; yang direkam adalah apa yang
menopang faktanya — `recomputed`, `test-backed`, atau `board-measured` — dan
penjaga menuntutnya cocok dengan cara verifikasinya.

### Perintah pemilik, 21 September 2026 — lapis 1–3 dulu, dua cacat RTL menunggu

Tiga perintah lapis datang berurutan, masing-masing dengan berkas keluarannya
sendiri, dan ketiganya sudah berdiri: Lapis 1 graf repositori (`441b2c6`,
diperluas `d0c9e89`), Lapis 2 pemahaman program (`1d7bcc8`), Lapis 3 pemahaman
eksekusi (`0fe74f4`). Isi, angka, dan syarat selesainya di `NUI/LAYERS.md`,
tidak disalin ke sini (R1).

**Aturan Lapis 3, kalimat pemilik:** *"Jangan membangun sistem baru. Jangan
membuat asumsi. Jangan menulis dokumentasi yang tidak berasal dari
pengukuran."* Yang tak bisa dibuktikan ditandai **UNKNOWN**. Dilarang: call
graph spekulatif, probabilitas, confidence score, ringkasan AI, dokumentasi
naratif. Alasan pemilik menaruhnya sebelum penalaran: NUI *"belum boleh
menyimpulkan sesuatu yang belum bisa dibuktikan oleh jejak eksekusinya
sendiri."*

Dua keputusan diambil bersamaan:

- **Burn-in tingkat 2 (72 jam) hanya di slot CPU**, sebagai eksperimen mandiri
  dengan parameter yang sama dengan tingkat 1. Burn-in Ka'bah terpisah,
  sesudahnya.
- **Dua cacat RTL yang burn-in temukan tidak disentuh sampai lapis 1–3
  selesai**: `PRINT` untuk angka besar, dan kartu SD yang gagal init sesudah
  rekonfigurasi — keduanya di `cosmictera-build/OFF.md`. Lapis 1–3 berdiri
  21 September 2026; membuka keduanya tetap keputusan pemilik, bukan
  konsekuensi otomatis.

**Lari pertama Lapis 3 menemukan cacat interpreter**, dan ia diperbaiki
sebagai butir sendiri di bawah K9 (`b218df8`): HC-04 dan HC-05 menulis
`halted`, bukan `_halted`, jadi mesin melaporkan fault lalu terus berjalan —
berlawanan dengan `docs/HISA_SPEC.md` dan `rtl/hcpu_execute.v`. Tes lamanya
hijau karena memeriksa atribut salah ketik itu sendiri.

### Keputusan pemilik, 21 September 2026 — Lapis 4 sebelum dua cacat RTL

Sesudah Lapis 3 menemukan cacat interpreter dan model kehilangan 412 dari 1.890
edge, pemilik **tidak membuka kedua cacat RTL**. Alasannya: *"Layer 4
membutuhkan data Layer 3 yang sudah benar"* — model paritas yang dibangun di
atas edge yang salah akan salah seluruhnya. Tiga penetapan:

- **Lapis 4 berikutnya**, dan tujuannya bukan simulator baru, melainkan bukti
  bahwa Python = interpreter = RTL = papan untuk operasi yang sama — dan kalau
  berbeda: langkah, register, memori, opcode. Keluarannya **model paritas**,
  bukan dokumen atau narasi.
- **`PRINT` angka besar dan SD init sesudah rekonfigurasi dicatat sebagai
  target verifikasi Lapis 4 lebih dulu.** Perbaikannya baru masuk pekerjaan
  berikutnya kalau model paritas menunjuk keduanya sebagai mismatch yang nyata
  dan terukur — dan itu tetap keputusan pemilik.
- **Pertanyaan entry Python untuk rantai `atom → rack → clockwork → freeze →
  multitask` tidak diputuskan sekarang**: itu kebutuhan Lapis 7 atau Lapis 9,
  bukan Lapis 4, yang butuh unit eksekusi terkecil — opcode, trap, MMIO,
  transisi register dan memori.

Urutan sesudahnya, dari pemilik: Lapis 5 Linux/Ubuntu → 6 perangkat keras →
7 operasi otonom → 8 diagnostik otonom → 9 penalaran → 10 rekayasa → 11
komputasi universal, karena penalaran tidak bisa dipercaya sebelum eksekusi,
paritas, host, dan perangkat keras benar.

Hasil Lapis 4 dan jawaban atas kedua target ada di `NUI/LAYERS.md` dan
`NUI/PARITY.md`, tidak disalin ke sini (R1). Satu temuan RTL barunya tercatat
di `cosmictera-build/OFF.md`.

### Arah pemilik, 21 September 2026 — NUI sebagai lapisan semantik Hijaiyyah

Sesudah Lapis 0–4, pemilik menetapkan arah NUI: **bukan bahasa pemrograman
baru dari nol**, melainkan lapisan semantik Hijaiyyah di atas mesin yang sudah
terbukti berjalan — HISA, HCPU, RTL, interpreter, host Linux. Tiga bahasa
manusia (Arab, Indonesia, Inggris), satu bahasa komputasi (HCL), dan rantai
bahasa manusia → pohon semantik → USR → compiler Hijaiyyah → HISA → RTL →
FPGA/ASIC. Empat prinsipnya: aset yang ada lebih dulu; tidak ada sistem baru
kalau fungsinya sudah ada; tiap lapis terverifikasi lewat tes, eksekusi, dan
perangkat keras nyata; tidak ada asumsi.

Peta arahan ini terhadap aset yang terukur ada di `NUI/LAYERS.md`, tidak
disalin ke sini (R1).

**Keputusan pemilik, hari yang sama**, sesudah peta itu dilaporkan: *"NUI
tidak boleh dimulai dari bahasa Arab. NUI harus dimulai dari komputasi yang
sudah terbukti."*

1. **HCL = HC**, diperluas. Bukan bahasa baru dan bukan lapisan di atas HC —
   Arab, Indonesia, dan Inggris masuk ke HC, lalu HISA, RTL, FPGA, perangkat
   keras. Nama di repositori tetap HC: satu nama untuk satu hal.
2. **Huruf Hijaiyyah tunggal tetap objek matematika** — *Hybit Symbol*, bukan
   nama variabel. `متغير س = 10` tidak sah, karena `س` sudah punya arti
   matematis. Nama variabel Arab adalah kata penuh: `متغير العدد = 10`.
3. **USR adalah lima medan** — ACTION, OBJECT, TARGET, CONTEXT, STATE. Bukan
   vektor huruf, bukan embedding, bukan LLM. `اقرأ ملف`, `baca file`, dan
   `read file` menuju USR yang sama, `{"action": "read", "object": "file"}`.
   Ini menjaga larangan `CONTRIBUTING.md` tentang huruf sebagai makna.
4. **Kata kunci multibahasa tahap pertama hanya lima** — `let`, `print`, `if`,
   `while`, `function`, dengan padanan Arab dan Indonesia di `NUI/LAYERS.md`.
   *"Belum lebih. Jangan tambah sampai pipeline terbukti."*
5. **Prioritas berikutnya Lapis 5, Ubuntu Linux Layer — bukan bahasa**:
   *"NUI harus mampu mengendalikan sistem nyata terlebih dahulu."* Target
   awalnya di `NUI/LAYERS.md`. Urutan sesudahnya tetap 6 → 11.

**Satu penghalang terukur hari itu**: tidak ada host Ubuntu. Mesin
pengembangan ini macOS 26.6.2 arm64 tanpa perkakas VM atau kontainer, dan
memasangnya adalah unduhan pihak ketiga — butuh izin pemilik.

### Keputusan pemilik, 21 September 2026 — host Lapis 5, baca-saja, dan urutan sesudah burn-in

Keputusan arsitektur NUI yang sudah dicatat di atas **dikunci** pemilik: HC
bahasa utama dan HCL = HC diperluas; huruf Hijaiyyah tunggal tetap objek
matematika; USR lima medan. Ditambah:

- **Host Lapis 5: VM Ubuntu Server 24.04 LTS ARM64** — sesuai Ubuntu
  sungguhan, dengan systemd, `systemctl`, dan `journalctl`, terisolasi dari Mac
  host.
- **Tahap pertama Lapis 5 hanya baca.** Daftar yang diizinkan dan yang belum
  diizinkan ada di `NUI/LAYERS.md`; yang mengubah sistem menunggu seluruh
  pipeline Lapis 5 tervalidasi.
- **PRINT dipisahkan sebagai OFF-PRINT-SILICON**, karena interpreter dan RTL
  simulasi benar, dan hanya perangkat keras yang berbeda.
- **HALT/RET tetap EH, masuk antrean perbaikan RTL sesudah burn-in.** Pemilik
  menilainya lebih serius daripada PRINT: interpreter berhenti, RTL masih
  menulis register.

**Urutan sesudah burn-in 72 jam selesai**, dari pemilik:

```
1  jalankan ulang korpus paritas di papan
2  lengkapi kolom hardware per opcode
3  verifikasi PRINT silikon
4  verifikasi HALT/RET pada papan
5  mulai Lapis 5, host Ubuntu
```

*"Data hardware nyata akan melengkapi Lapis 4 sebelum NUI melangkah ke Linux
Host."* Bahasa Arab dan Indonesia tetap front-end semantik di atas HC, bukan
proyek terpisah.

### Konfirmasi pemilik, 22 September 2026 — nama variabel, dan image sebagai baseline

Keputusan 21 September dikonfirmasi tanpa perubahan, dengan dua rincian:

- **Contoh HC berkata kunci Arab dengan nama variabel kata utuh**:
  `متغير angka = 10`, `متغير harga = 20`, `اطبع angka + harga` menjadi HC
  `let angka = 10; let harga = 20; println(angka + harga);`, lalu HISA.
  Kata kunci Arab dan Indonesia adalah lapisan sintaks HC, bukan bahasa
  terpisah; huruf tunggal seperti `س` tetap objek matematis. Implementasinya
  tetap menunggu sesudah Lapis 5.
- **Image VM Lapis 5 menjadi bagian baseline**: SHA256 diverifikasi sebelum
  dipakai, checksum disimpan di dokumentasi, versi persis dicatat. Berkasnya
  di `NUI/LAYERS.md`.

Urutannya ditegaskan: selesaikan burn-in 72 jam → `rtl/scripts/parity_board.py`
→ kolom hardware per opcode → OFF-PRINT-SILICON di papan → HALT/RET di papan →
Lapis 5 → lapis berikutnya. *"Seluruh temuan papan nyata akan masuk ke basis
pengetahuan NUI sebelum host Linux ditambahkan."*

### Perintah pemilik, 22 September 2026 — NUI sambil menunggu burn-in

Dua pesan pada hari yang sama, dan keduanya **tanpa papan, tanpa Lapis 5,
tanpa mengubah compiler, dan tanpa mengganggu urutan yang sudah dikunci**.
Yang pertama meminta spesifikasi USR, katalog Lapis 5, dan kamus HC
(`c935270`). Yang kedua meminta lima hal yang *"paling aman dikerjakan
sekarang"*: spesifikasi USR, kamus HC–Arab–Indonesia, dokumen HCL = HC
diperluas, registry matematika Hijaiyyah, dan knowledge base NUI — yang
setengah jadi di pohon kerja, untuk ditinjau dan dirapikan dalam enam domain:
HC, HISA, RTL, OFF, PAPAN, NUI. Isinya di `NUI/SEMANTIK.md` dan `NUI/LAYERS.md`,
tidak disalin ke sini (R1). Yang harus diketahui kuli berikutnya:

- **Pergeseran dicatat, dan yang berlaku yang terakhir.** Contoh USR pesan
  kedua memakai kunci huruf besar dan CONTEXT `Ubuntu`; pesan pertama memakai
  kunci huruf kecil dan `ubuntu_host`. Bentuk lama kini **ditolak**, bukan
  diterima berdampingan — satu nama untuk satu hal. Kamus dibaca per konsep,
  bentuk pemilik `{KONSEP: {hc, arabic, indonesia}}`.
- **Contoh pemilik diukur sampai HISA**: compiler HC menghasilkan lima
  instruksi yang sama dengan HISA tulisan pemilik, dan interpreter mencetak
  `30`. Langkah Arab → HC tetap terjemahan pemilik, tidak dijalankan.

**Pesan ketiga, hari yang sama, mengunci lima hal yang tidak boleh dirapikan
sendiri**, sebelum commit:

1. **28 huruf.** Angka 29 di pesan sebelumnya salah ketik dan bukan bagian
   spesifikasi.
2. **`read_file` bukan kata kunci HC** — kelima kata kunci yang diputuskan
   adalah bagian HC yang sudah ada; `read_file` tidak masuk tanpa keputusan
   arsitektur baru.
3. **`while` belum menjadi kata kunci tiga bahasa** — *"jangan menambahkannya
   hanya karena umum di bahasa pemrograman"*. Diukur: `while` sudah kata kunci
   HC dalam bahasa Inggris; yang ditahan adalah bentuk Arab dan Indonesianya.
   Kamusnya kini empat: `let`, `println`, `if`, `fn`.
4. **Arti STATE adalah usulan pemilik, belum dikunci**: keadaan aktual
   target/objek saat aksi dinyatakan, bukan tahap pipeline — `present` sebagai
   contoh, `compiled` sebagai metadata eksekusi. Dicatat di `NUI/spec/usr.json`;
   kosakata STATE tidak diubah sampai dikunci.
5. **Peta jangka panjang Lapis 0–9 adalah usulan roadmap**, bukan pengganti
   dua belas lapis yang berlaku. Linux/Ubuntu, Command Center Docker, dan
   integrasi KV260 tetap di luar implementasi aktif sampai urutannya dibuka.

**Temuan matematis dipisahkan, tidak diperbaiki**: docstring `matrix_order`
dan `gf2_rank` di `src/hijaiyyah/core/exomatrix.py` membaca ekor 1 sebagai
invertibel, sedangkan tujuh huruf berekor 1 atas GF(2) punya rank di bawah 5 —
Dal rank 3. Pemilik: *"Jangan memperbaiki matematika berdasarkan dugaan"*;
selisihnya ditandai sebagai fakta Lapis 0 `nui.tail_one_is_not_invertibility`,
dan NUI tidak memakai "ekor 1 berarti invertibel" sebagai aturan sampai
definisinya dibuktikan.

Menurut pemilik, yang kini berdiri di NUI: pengetahuan terverifikasi → graf
repositori → pemahaman program → pemahaman eksekusi → paritas perangkat lunak
↔ keras → kueri pengetahuan → registry Hijaiyyah → sintaks HC multibahasa →
fondasi USR.

### Perintah pemilik, 22 September 2026 — yang disiapkan tanpa papan sampai burn-in selesai

Sembilan prioritas, dan tiga yang pemilik sebut *"100% tidak mengganggu
burn-in"*: siapkan paritas papan, siapkan eksperimen PRINT dan HALT/RET, siapkan
kerangka Lapis 5 hanya-baca. **Yang tidak boleh disentuh sampai burn-in
selesai**: `rtl/scripts/burn_in.py`, checksum loader, RTL HCPU, bitstream, firmware.

- **Urutan hari Kamis, P0–P8**, beserta empat keputusan yang harus ada
  sebelum hari itu, di `cosmictera-build/PASCA-BURN-IN.md` — tidak disalin ke
  sini (R1).
- **PRINT dan kata sesudah berhenti adalah eksperimen tersendiri**, tidak
  dicampur ke paritas umum: tangga pemilik 2²², 2²³, 2²⁴, 2²⁵, 2²⁶, 2²⁷, 2³¹,
  dan empat probe pemilik untuk HALT/RET. Jawaban yang diharapkan
  **dibekukan sebelum papan ditanya** di `NUI/board_expected.json`.
- **Temuan audit, dibetulkan sebagai cacat implementasi (K9):** docstring
  `rtl/scripts/parity_board.py` menyatakan `src/hijaiyyah/nui/parity_model.py` membaca rekaman
  papan, dan tidak ada kode yang melakukannya. Pembacanya kini ada:
  PARITY/MISMATCH/UNKNOWN per program dan kolom papan per opcode.
- **Cacat saya sendiri, tertangkap sebelum di-commit**: perbandingan pertama
  mencatat 49 program "RTL ≠ interpreter" karena interpreter di bawah loader
  dibandingkan dengan RTL yang mulai dari nol; dalam konteks yang sama
  selisihnya empat, yang membaca `COUNTER` — angka yang sama dengan tes lama.
- **RTL tersimulasi menjawab ya untuk keempat pertanyaan HALT/RET pemilik.**
  Papan hanya bisa menjawab yang lewat kabel.
- **Lapis 5 berpindah dari "tidak ada" ke "ada bahannya"**, labelnya tetap
  AT: kolektor, pagar hanya-baca, dan konfigurasi VM, tanpa host dan tanpa
  satu perintah pun dijalankan. Template Ubuntu 24.04 bawaan Lima 2.2.0 tidak
  bisa dipakai — image lain, URL tanpa digest, dan home Mac terpasang.
- **Tabel keputusan checksum loader** di `cosmictera-build/attack-lab/README.md`;
  implementasinya tidak berubah. **Matriks uji STATE** di
  `tests/test_ai/test_nui_usr.py`; kosakatanya tidak berubah.
- **Kontrak kueri NUI (prioritas 7)** menyusul pada hari yang sama, sesudah
  keputusan K-1–K-4 di bawah — lihat bagian berikutnya.

### Keputusan pemilik, 22 September 2026 — K-1 sampai K-4

Empat keputusan yang runbook Kamis minta sebelum hari itu. Rinciannya di
`cosmictera-build/PASCA-BURN-IN.md`, tidak disalin ke sini (R1).

- **K-1**: dua baris `error` burn-in yang sedang berjalan adalah **selisih yang
  diketahui**; `rtl/scripts/burn_in.py` tidak diubah sebelum lari 72 jam
  selesai, karena pengurai yang aktif adalah bagian observasi. **Terukur
  sesudahnya: pengurai itu tidak menyimpan byte mentah dari kabel**, jadi lari
  ini tidak bisa diurai ulang dari byte-nya. Yang memastikan 0 error papan
  adalah pencacahnya sendiri: `rtl/programs/burn_in.hasm` menyebutnya *"never a
  reset"*, dan tiap sampel sesudah kedua baris itu berbunyi 0.
- **K-2**: Lapis 4 dibekukan dengan commit **dan annotated tag**, misalnya
  `layer4-freeze-2026-09-24`, sesudah bukti papan dan silikon final — tidak
  sekarang.
- **K-3**: Lima lewat Homebrew, `LIMA_HOME=~/cosmictera-layer5/lima-home`, VM
  `cosmictera-layer5`, image di `~/cosmictera-layer5/downloads/`; template
  bawaan Lima tidak dipakai. Langkah P8 pertama menguji `images[].location`
  berkas lokal di Lima 2.2.0 sebelum VM permanen dibuat. **Konsekuensi yang
  dicatat**: tarball Lima yang SHA256-nya diverifikasi bukan yang dipasang
  Homebrew; formula Homebrew hari itu menyebut versi yang sama, 2.2.0, dan
  baseline Lima dicatat ulang saat dipasang.
- **K-4**: `journalctl` dan `ip` masuk daftar izin hanya dalam bentuk
  `journalctl -b -n 200 --no-pager`, `journalctl -b -u <service> -n 200
  --no-pager`, `ip -brief addr`, `ip link`, `ip route`. Pagar Lapis 5
  mencocokkan argv utuh; katalog READ JOURNAL dan READ NETWORK ikut bentuk itu.

**Sampai Kamis**, kata pemilik: `rtl/scripts/burn_in.py`, RTL, bitstream, dan
eksperimen papan tidak disentuh; yang boleh maju hanya persiapan Lapis 5 dan
kontrak kueri NUI. **Kontrak kuerinya** — tujuh pertanyaan pemilik, dipetakan
ke jenis kueri dan dijalankan tesnya sendiri — di
`NUI/spec/query_contract.json`; lima dijawab, satu sebagian, dan satu (layanan
Ubuntu) menunggu Lapis 5.

### Keputusan pemilik, 22 September 2026 — K-5 sampai K-9

Lima keputusan lagi pada hari yang sama, dan pemilik menegaskan tak satu pun
menyentuh burn-in yang sedang berjalan. Rinciannya di tempat masing-masing,
tidak disalin ke sini (R1).

- **K-5 — arti STATE dikunci**: *keadaan aktual OBJECT/TARGET pada saat
  representasi semantik dibuat*, bukan tahap pipeline, status compiler, atau
  riwayat proses. `requested` dan `compiled` bukan STATE semantik, melainkan
  metadata lifecycle/eksekusi. Ini menutup butir 4 pesan ketiga di atas. **Yang
  dikunci maknanya, bukan kosakatanya**: pemilik melarang `present` ditambahkan
  ke daftar nilai pada commit yang sama tanpa migrasi kosakata, jadi
  `NUI/spec/usr.json` memegang arti terkunci di samping kosakata lama yang
  menunggu migrasi — selisih yang diperintahkan, bukan dirapikan.
- **K-6 — domain ketujuh, HOST**: keadaan, proses, service, jaringan,
  filesystem, dan runtime host/OS yang sedang diamati, sedangkan OFF tetap
  fakta perangkat lunak yang tidak bergantung pada host aktif. *"Jangan
  memasukkan fakta HOST ke NUI sebelum collector benar-benar mengukurnya"* —
  karena itu HOST tidak membaca tempat mana pun di
  `src/hijaiyyah/nui/knowledge.py`, dan tes yang menempatkan tiap butir
  menurut sumbernya menolak apa pun yang diletakkan di sana.
- **K-7 — byte mentah kabel jadi bukti primer burn-in**: capture mentah →
  berkas biner → pengurai offline → log terstruktur → analisis, dengan tujuh
  medan metadata per capture. Lari 72 jam sekarang tidak diubah: lognya rekaman
  historis, dan dua baris `error`-nya artefak pengurai. Pengurai diperbaiki
  sesudah lari itu selesai dan diuji terhadap capture mentah lari berikutnya.
- **K-8 — checksum loader menutupi seluruh container**: rekaman program sektor
  16, header dengan medan checksum dinolkan, tabel relokasi, dan kata program;
  yang di luar itu tidak. Tidak diimplementasikan sebelum burn-in selesai, dan
  sesudahnya harus datang bersama kasus sabotase untuk tiap bagian yang baru
  dilindungi. Tabelnya di `cosmictera-build/attack-lab/README.md`. Satu hal
  yang K-8 tidak sebut, dan pemilik jawab sehari kemudian di K-10:
  algoritmanya.
- **K-9 — instance uji Lapis 5 bernama `cosmictera-layer5-uji`**, sekali pakai.
  Jalurnya dibuktikan di sana lebih dulu — lokasi image lokal, Lima create,
  boot Ubuntu, tanpa mount home Mac, kolektor hanya-baca, pagar perintah,
  kontrak kueri — dan `cosmictera-layer5` baru jadi instance utama sesudahnya.

**Urutannya ditegaskan: sampai 24 September 2026 12:34 WIB, burn-in saja.**
Sesudah itu P0–P8 di `cosmictera-build/PASCA-BURN-IN.md`. Satu koreksi dokumentasi diizinkan lebih awal dan
dikerjakan sebagai commit tersendiri: `cosmictera/COMPUTING.md` berhenti
mengutip 384 asersi di 35 bench, angka terukurnya 408 di 39. Angka "36 berkas
bench, 16 lewat pytest" di kalimat yang sama **tidak** diganti sampai diukur
ulang — perintah pemilik.

### Keputusan pemilik, 23 September 2026 — K-10 dan K-11

Dua pertanyaan yang dilaporkan terbuka, dijawab pemilik sebagai **keputusan
arsitektur, tanpa implementasi sampai burn-in selesai**.

- **K-10 — checksum loader adalah jumlah 32-bit, bukan CRC-32.** `CRC(...)` di
  uraian K-8 adalah istilah yang keliru, dan diperjelas jadi `CHECKSUM32 =
  Σ canonical_container_words mod 2^32` atas cakupan K-8 yang sama. Keputusan
  18 September karena itu tetap berlaku: tidak ada tabel CRC-32 256 entri, dan
  arena heap 127 kata tidak diperbesar. Yang ditetapkan bersamanya: kata yang
  dijumlah adalah representasi word container **sebagaimana tersimpan di
  kartu**, supaya tidak ada dua cara menghitung checksum untuk citra yang sama.
  Sesudah Kamis, penggantian nama `CRC` → `CHECKSUM32` datang bersama empat
  kasus sabotase — header, tabel relokasi, badan program, rekaman tabel program.
- **K-11 — rekaman observasi Lapis 5 tinggal di host, di luar repositori**:
  `~/cosmictera-layer5/observations/<run_id>/`, satu direktori per sesi, dengan
  sebuah manifest dan keluaran mentah per kolektor. *"Repository tidak menjadi
  tempat penyimpanan observasi runtime"* — repo memuat kode, spesifikasi, tes,
  dan fakta tersegel. Manifestnya mencatat tujuh medan: run_id, cap waktu,
  kolektor, nama VM, identitas perintah, exit code, dan durasi; enam di
  antaranya sudah ada di rekaman `observe()`, dan hanya run_id yang baru. HOST
  (K-6) baru bisa menjawab sesudah ada rekaman pengukuran aktual; sebelum itu
  `host services` tetap `unknown`.

**Sampai Kamis 24 September 2026 12:34 WIB tetap burn-in saja.** K-10 masuk di
tahap checksum (P6), K-11 dipakai ketika `cosmictera-layer5-uji` mulai diukur
(P8).

### 24 September 2026 — burn-in tingkat 2 tutup, dan urutan P0–P8 dikunci

**Burn-in 72 jam tutup 24 September 2026 05:34:30 UTC dengan `duration reached`
dan 0 error papan.** 259.204,9 detik jam host, 164.668 detak dipancarkan papan,
168.620.032 siklus, 0 baca kartu gagal, dan kerja terhadap jam papan sendiri
1,0002 — papan tidak pernah berhenti. Angka, hash, garis dasar, dan
perbandingannya terhadap tingkat 1 ada di `cosmictera-build/burn-in/README.md`
dan `cosmictera-build/PAPAN.md`, tidak disalin ke sini (R1).

**K-1 terbukti pada log final, bukan pada log setengah jalan**: kedua baris
`error` adalah artefak pengurai — masing-masing didahului pada detik yang sama
oleh baris tak terurai `0H`, medannya bergeser, dan nilai `errors` tertinggi di
seluruh 3.991 sampel adalah 0. **Yang tidak diklaim**, perintah pemilik hari
itu: pengurai **belum** tervalidasi terhadap capture mentah kabel, karena lari
ini tidak menyimpan byte mentah; validasi itu milik lari berikutnya (K-7).

**Sidik jari loader yang berlaku adalah `84fdc912…`**, diukur dari
`rtl/fpga/gowin/hcpu_gowin_top_loader.fs` yang dipakai lari ini. Catatan sesi
sebelumnya menyebut `4a0a1bfd…`, dan angka itu tidak cocok dengan satu pun
bitstream di direktori. Berkas `.fs` di-gitignore, jadi tidak ada riwayat yang
bisa memutuskan. Pemilik: catat sebagai **selisih historis yang tidak bisa
diverifikasi**, jangan direkonstruksi dan jangan "dibetulkan".

**Urutan eksekusi pasca-burn-in dikunci pemilik 23 September 2026, P0–P8**, dan
tidak diubah lagi: P0 tutup burn-in, P1 pengurai dan capture mentah, P2 paritas
papan, P3 kolom opcode perangkat keras, P4 PRINT di silikon, P5 HALT/RET di
silikon, P6 checksum dan sabotasenya, P7 laporan selisih final dan freeze Lapis
4 beserta tag, P8 Lapis 5. Dua pergeseran dari susunan 22 September: pengurai
naik ke P1, mendahului paritas papan, dan klasifikasi selisih pindah ke P7.
**Penomoran ini urutan eksekusi, bukan lapis NUI** — dua belas lapis NUI tidak
bergeser, dan itu perintah pemilik pada hari yang sama.

### 24 September 2026 — P1: byte kabel jadi bukti primer

**Pemilik memisahkan pengurai dari bukti.** Dua alat baru berdiri di samping
`rtl/scripts/burn_in.py`, yang **tidak disentuh** atas perintah pemilik supaya
rekaman lamanya tetap berarti: `rtl/scripts/burn_in_capture.py` menulis byte
kabel apa adanya beserta manifesnya, dan `rtl/scripts/burn_in_parse.py`
menguraikannya sesudahnya, jauh dari papan. Alat capture **tidak mengurai satu
baris pun**, dan sebuah tes membaca sumbernya untuk menjaga itu.

**Capture pendek pertama, 24 September 2026**: bitstream yang sama tanpa
dibangun ulang, 12 menit, 9.940 byte, 457 detak, **0 error papan dan 0 parse
error**, dengan irama detak 1,5736 detik melawan 1,5744 di garis dasar 72 jam.
Angkanya di `cosmictera-build/burn-in/README.md`, tidak disalin ke sini (R1).

**Pengurai baru membaca tata bahasa, bukan menghitung angka**: satu detak
adalah `H` diikuti tepat enam angka desimal. Selebihnya `parse_error` dengan
offset byte dan alasannya, dan medan yang tertunda dibuang — karena begitulah
detak bergeser dibuat. **`parse_error` tidak pernah menjadi `board_error`**, dan
bentuk dua baris tingkat 2 diputar ulang terhadap kedua pengurai untuk
membuktikannya.

**Yang tidak diklaim, perintah pemilik:** pengurai lari 72 jam **tidak**
tervalidasi terhadap capture mentah — lari itu tidak menyimpan byte. Buktinya
tetap yang dikunci di P0; yang tervalidasi P1 adalah capture pendek baru dan
pengurai offline-nya.

### 24 September 2026 — P2: paritas papan, 79 program

**73 PARITY, 2 MISMATCH, 28 UNKNOWN**, dan kolom opcode **74 PARITY, 0
MISMATCH, 29 UNKNOWN**. Dibandingkan **hanya** terhadap `NUI/board_expected.json`
yang dibekukan sebelum papan ditanya; ekspektasi tidak diubah karena hasil
papan, perintah pemilik. Angkanya di `cosmictera-build/PAPAN.md`, tidak disalin
ke sini (R1).

Kedua MISMATCH adalah angka besar dan keduanya **OFF-PRINT-SILICON**, bentuk
yang sama dengan temuan 20 September. Opcode yang berjalan di program yang cocok
**dan** yang berbeda tetap **UNKNOWN**, tidak dipaksa PARITY — kabel saja tidak
bisa menunjuk instruksi mana yang berbeda.

**Dua temuan alat, keduanya di sisi host:**

1. **Lari pertama membaca 75 dari 79 sebagai MISMATCH**, dan penyebabnya
   pembacanya. Laporan `CYCLES=` wrapper tiba **tergeser satu byte** — `0A`
   di depan, bukan `0D 0A`, dan satu `0A` lebih di ujung; panjangnya tetap 19
   byte. Terukur 79 tangkapan dari 79. Itu di RTL wrapper dan **dilaporkan,
   tidak diperbaiki** (K9, `cosmictera-build/OFF.md`); yang dibetulkan
   `src/hijaiyyah/nui/board_parity.py`, yang kini membuang satu baris baru
   milik laporan dan menyimpan milik program.
2. **Program pertama lari itu terkontaminasi 350 detak burn-in** — bernomor
   482 sampai 831 — yang masih tersangkut di penyangga driver sesudah capture P1.
   Angka "482" yang semula tertulis di sini adalah nomor detak pertama yang
   terbaca sebagai jumlahnya; diukur ulang saat P7. `rtl/scripts/parity_board.py`
   sekarang menguras kabel sebelum mengirim.

Keduanya menaikkan satu aturan P1 ke Lapis 4: **laporan membaca byte mentah
rekaman, bukan teks yang rekaman itu bawa**. Dibaca begitu, tanpa papan ditanya
lagi, lari pertama jadi 72 PARITY dan 3 MISMATCH — yang ketiga persis program
yang tercemar — dan lari kedua 73 dan 2. Tidak ada RTL yang diubah, dan tidak
ada ekspektasi yang digeser.

### 24 September 2026 — P3: kolom perangkat keras per opcode

Bukti 79 program jadi **matriks per opcode** di `NUI/PARITY.md`, bagian "Kolom
perangkat keras per opcode": **74 PARITY, 0 MISMATCH, 29 UNKNOWN**, dan tiap
baris membawa cacah buktinya — program yang menjalankannya, yang cocok, yang
berbeda, yang tak bisa diputuskan — beserta program sumbernya. Angkanya tidak
disalin ke sini (R1).

**Tiap sel dihitung ulang dari byte mentah rekaman P2**, bukan ditulis tangan:
`board_corpus()` di `src/hijaiyyah/nui/parity_model.py` memanggil
`board_parity.opcode_column`, dan sebuah tes membandingkan matriks yang
di-commit dengan yang dihitung ulang dari rekaman itu.

**Aturan Lapis 4 yang pemilik tetapkan dari P2**: analisis membaca **byte
mentah** rekaman lebih dulu, baru mengurai teksnya. Laporan `CYCLES=` yang
tiba tergeser satu byte adalah alasannya.

**Lima opcode tetap UNKNOWN selama bukti campur** — `HALT`, `HCRC`, `HLOAD`,
`HPACK`, `PRINT` — dan tidak dipaksa PARITY untuk melengkapi tabel. Khusus
`PRINT`: dua program yang berbeda adalah bukti silikon nyata dan tetap dicatat,
tetapi **status dan selisih adalah dua hal berbeda** (kata pemilik), jadi
kolomnya UNKNOWN sementara tangga PRINT yang terekam tetap MISMATCH.

**Empat program pencacah** — `timer_poll`, `trap_resume`, `trap_shadow`,
`trap_timer` — tetap **UNKNOWN karena semantik pencacah**, bukan cacat
perangkat keras: interpreter menghitung instruksi, silikon menghitung clock.

### 25 September 2026 — P4: PRINT di silikon

Tangga tujuh titik pemilik — 2²², 2²³, 2²⁴, 2²⁵, 2²⁶, 2²⁷, 2³¹ — dijalankan di
papan **tiga kali**, bitstream dan payload sama, tanpa variabel diubah.
**Batas pertama 2²³**, sama dengan 20 September; 2²² dan 2²⁴ benar di setiap
lari. Interpreter, Python, dan RTL tersimulasi benar di ketujuhnya.

**Temuan baru: keluaran salahnya tidak berulang.** Nilai yang sama pada lari
yang identik mencetak angka salah yang berbeda — 14 dari 15 keluaran salah
berbeda satu sama lain. Tabelnya di `cosmictera-build/OFF.md`, tidak disalin ke
sini (R1). **Sebabnya tidak diukur dan tidak ditulis**; perbaikan tetap
keputusan pemilik, K9 berlaku, dan tidak ada RTL yang disentuh.

Ulangan dua kali itu adalah eksperimen yang sama persis, bukan eksperimen
diagnostik baru: tanpanya, selisih terhadap tangga 20 September tidak bisa
dibedakan dari dua kondisi yang berbeda.

### 25 September 2026 — P5: HALT dan RET di silikon

**`PRINT` sesudah `HALT` dan sesudah RET fault sampai ke kabel di silikon**;
interpreter berhenti sebelumnya. Pemilik meminta satu probe dengan sentinel
yang dicetak **sebelum** jalur fault, supaya kabel kosong tidak bisa berarti
"program tidak berjalan": di papan `1234` muncul, lalu `5`. Probe itu
dibekukan di `NUI/board_expected.json` sebelum papan ditanya, dan terbukti
tidak menggeser satu pun ekspektasi lama. Tabelnya di
`cosmictera-build/OFF.md`, tidak disalin ke sini (R1).

**Register dan RAM sesudah berhenti: UNKNOWN — tidak teramati dari luar.**
Top-level papan tidak punya port yang membawa GPR atau kata RAM data, dan
atas perintah pemilik tidak ada port debug yang ditambahkan. Alasannya ditulis
di `src/hijaiyyah/nui/board_probes.py` dan dijaga tes yang membaca daftar pin
papan, supaya alasan itu tidak basi kalau top-level kelak berubah. Laporan
yang sempat menandai ketiganya PARITY — karena kabelnya sama-sama kosong —
dibetulkan: kabel kosong berarti program berjalan dan berhenti, bukan isi
register.

**Dua selisih terhadap rekaman RTL tersimulasi tetap UNKNOWN**, bukan silikon
yang menyimpang: rekaman RTL ditutup saat `halted` naik
(`rtl/tb/tb_parity.v`), sedangkan wrapper papan menunggu UART diam
(`rtl/fpga/gowin/hcpu_gowin_top.v`). Logika HALT, RET, dan writeback tidak
diubah — perintah pemilik.

### Keputusan pemilik, 26 September 2026 — satu pengecualian sempit untuk naskah pribadi

Sebuah berkas koreksi naskah pribadi pemilik, di folder yang tidak di-commit,
membuat dua penjaga `tests/test_integrity/test_authorship.py` merah: ia memuat
nama penerbit dan nama penulis yang sudah digantikan. Pemilik: **jangan ubah
dan jangan baca isinya**, dan jangan mengganti nama lama di dalamnya — berkas
itu catatan koreksi yang boleh memuat nama historis. Penjaganya tetap perlu
memeriksa folder itu, karena dokumen paten tinggal di sana.

Jadi pengecualiannya **eksplisit dan sempit**: satu path persis, dengan
alasannya di sebelahnya, hanya untuk dua penjaga nama yang digantikan. Bukan
menurut nama penerbit, nama penulis, akhiran `.txt`, atau seluruh folder
naskah — dan sebuah tes membangun pohon tiruan untuk membuktikan berkas
saudaranya, berkas `.txt` lain, dan berkas bernama sama di subfolder tetap
merah. Penjaga ejaan-varian nama tidak dikecualikan.

### 26 September 2026 — P6: CHECKSUM32 di loader

**Loader program kini menutupi seluruh container** (K-8, K-10): entri tabel
sektor 16, header dengan medan checksumnya sendiri dinolkan, tabel relokasi,
dan kata program, dijumlah 32-bit modulo 2³². `VERSION` naik ke 2, jadi loader
lama menolak container baru lewat pemeriksaan VERSION, bukan salah membacanya.

**Syarat pemilik dipenuhi lebih dulu: satu urutan kanonik.** Satu kata adalah
32 bit tak bertanda, byte paling signifikan lebih dulu — cara
`rtl/hcpu_sdio.v` mengisi penyangganya dan cara `rtl/scripts/send_program.py`
mengirimnya. `tests/test_integrity/test_checksum32.py` menguji urutan itu, lalu
memberikan **kartu yang sama persis** kepada loader Python di
`rtl/scripts/build_container.py` dan kepada loader HCPU tersimulasi
(`rtl/tb/tb_hcpu_prog_load_card.v`): vonisnya sama di ke-21 kasus. Papan
sepakat di ke-19 kasus yang bisa ditulis ke kartu — **0 temuan**. Angkanya di
`cosmictera-build/attack-lab/README.md`, tidak disalin ke sini (R1).

**Kasus yang lolos di versi 1 kini ditolak**: WORDS yang dinaikkan di atas
padding nol, dan entri relokasi yang digeser. **Batas sebuah jumlah dicatat,
bukan disembunyikan**: dua kata program yang ditukar tempat, dan badan yang
diubah lalu disegel ulang, keduanya lolos — sifat algoritma yang dipilih K-10.

**Dua akibat yang diukur.** Shell memuat loader ini, dan tabel relokasinya
berada 125 dari batas 128: pass satu yang baru kehilangan satu cabang, jadi
shell tumbuh tiga kata dan relokasinya turun ke 124. Satu entri ekspektasi
beku ikut bergeser — alasan pengecualian `rtl/programs/hos_prog_load.hasm`, program yang
**tidak** dikirim ke papan, dari fault sesudah 27.016 langkah ke 27.145 —
dan pembekuan ulangnya terbukti tidak menyentuh satu pun ekspektasi yang
dipakai papan.

### 26 September 2026 — P7: Lapis 4 dibekukan

**Lapis 4 resmi dibekukan dengan tag `layer4-freeze-2026-09-26`** — tanggal
freeze, bukan tanggal burn-in selesai, kata pemilik. Tanpa eksperimen baru dan
tanpa ekspektasi yang digeser: laporan selisih finalnya, `NUI/LAYER4.md`,
dihitung ulang dari rekaman P0–P6 oleh `src/hijaiyyah/nui/layer4_freeze.py`.

**Empat kelas pemilik, dan yang terakhir terpisah**: selisih terukur (PRINT
angka besar di P2 dan tangga P4, dan PRINT sesudah berhenti di P5), beda
semantik yang diketahui (empat program pencacah), UNKNOWN atau tidak teramati
(register dan RAM sesudah berhenti, jendela rekaman RTL, opcode dengan bukti
campur atau tanpa bukti, program yang tidak dikirim), dan **selisih alat** —
artefak pengurai burn-in, laporan `CYCLES=` yang tergeser, dan byte burn-in
basi di lari P2 pertama. Alat yang salah membaca kabel bukan papan yang salah
menjawab, dan tes menolak keduanya bercampur.

**Yang dijaga selamanya dan yang tidak.** Rekaman bukti dijaga hash-nya, dan
vonisnya atas rekaman beku tidak boleh berubah. Turunan pada saat freeze —
model paritas dan ekspektasi beku — dicatat hash-nya untuk tag, dan boleh
dibangun ulang sesudahnya. Laporan P2 **tidak ditulis ulang**: dihitung ulang
hari ini, keduanya berbeda di tepat satu jalur, alasan pengecualian program
yang tidak dikirim yang digeser P6 — dan jalur itu dinamai, bukan dihapus.

**Satu kekeliruan saya sendiri dibetulkan di sini**: "482 detak burn-in" di
catatan P2 adalah nomor detak pertama yang terbaca sebagai jumlahnya. Diukur
dari rekamannya: 350 detak, bernomor 482 sampai 831.

### Keputusan pemilik, 26 September 2026 — P8 dibuka: host uji Lapis 5

Sesudah tag P7, pemilik membuka P8 dan memberi **izin eksplisit** untuk
memasang Lima lewat Homebrew dan memakai image Ubuntu ARM64 yang sudah diunduh
dan diverifikasi — **bukan** template bawaan Lima yang pernah diaudit. Lapis 4
tetap beku di `9764d5a` dan tagnya tidak diubah.

**Urutannya tujuh langkah, P8.1 sampai P8.7**, di
`cosmictera-build/PASCA-BURN-IN.md`, tidak disalin ke sini (R1). Tiga pagar
yang paling mudah dilanggar:

- **Tidak ada mount ke home Mac.** Kalau satu muncul di tamu, berhenti — jangan
  lanjut ke kolektor.
- **Bukti runtime tidak pernah masuk `facts/`**, sekalipun hasilnya tampak
  benar: `facts/` adalah pengetahuan rekayasa tersegel, sedangkan
  `/proc/mounts` atau status service adalah bukti keadaan, dan tinggal di
  `~/cosmictera-layer5/observations/<run_id>/`. HOST tetap `unknown` sampai
  observasinya ada.
- **Instance utama `cosmictera-layer5` tidak dibuat** sebelum
  `cosmictera-layer5-uji` hijau di semua pagar. Uji negatif digest memakai
  instance sekali pakai tersendiri, `cosmictera-layer5-digest-uji` — nama dari
  pemilik, dicatat di `NUI/spec/layer5_collectors.json`.

**P8.1–P8.3 tutup hari itu**: Lima 2.2.0 terpasang, image lokal diterima lewat
digest-nya, Ubuntu 24.04.5 ARM64 boot, kelima kriteria isolasi pemilik
terpenuhi, dan satu digit digest yang diubah ditolak Lima sebelum VM pernah
berjalan. Vonis dan hash-nya di `NUI/LAYERS.md`, Lapis 5; rekaman mentahnya di
luar repositori. Satu pengamatan lingkungan yang ikut terukur: lari pytest
P7.4 tampak macet berjam-jam, padahal mesin ini **tidur** 159,7 menit selama
lari itu — pytest sendiri mengukur 770 detik. Lari panjang di mesin ini perlu
`caffeinate`, seperti yang `rtl/scripts/burn_in.py` sudah lakukan.

**P8.4 dijalankan hari yang sama**, lewat `record()` di
`src/hijaiyyah/nui/layer5.py`: kesebelas kolektor sekali, lewat pagar yang
sama, ke satu direktori run di evidence store. Sembilan exit 0. `journal`
gagal karena izin — pengguna tamu `lima` tidak boleh membaca jurnal, dan
membukanya berarti `sudo` atau mengubah grup tamu, dua hal di luar pagar,
jadi ia **didokumentasikan, tidak ditambal**, dan menunggu keputusan pemilik.
`docker` tidak terpasang di tamu. HOST tetap `unknown`; alasan yang
dicetak `src/hijaiyyah/nui/knowledge.py` sudah basi, dan itu wilayah P8.5.

**Keputusan pemilik, hari yang sama — K-12 sampai K-15**, lalu P8.5. Tabelnya
di `cosmictera-build/PASCA-BURN-IN.md`, tidak disalin ke sini (R1). Yang
paling mudah dilanggar:

- **Tidak memperluas allowlist demi PASS.** `journal` tetap
  `unavailable_due_to_permissions` (K-12); `sudo` dan grup tamu tidak disentuh.
- **Ditetapkan tidak sama dengan exit 0** (K-13). Keadaan kolektor dibaca dari
  exit code dan stderr-nya lewat aturan di spesifikasi, bukan dipaksa jadi
  PASS.
- **`unknown` berarti bukti belum cukup, bukan sistem belum ada** (K-14).

**P8.5 tutup hari itu**: HOST membaca evidence store
`~/cosmictera-layer5/observations/` dan hanya itu, sedangkan `facts/` tetap
milik NUI. Tiap observasi diverifikasi terhadap hash-nya
sebelum dipakai, dan tiap butir HOST membawa run_id, kolektor, berkas
evidence, cap waktu, dan sha256-nya. Ketujuh kueri kontrak dijalankan, dan
`host services` tetap `unknown` karena tidak ada observasi service yang
mendukungnya. Angkanya di `NUI/LAYERS.md`, Lapis 5.

**Instance utama, 26–27 September 2026.** `cosmictera-layer5` dibuat dari
artefak yang sama persis — identity check sembilan dari sembilan sebelum boot,
tanpa eksperimen baru — lalu boot, `aarch64`, dan isolasinya identik dengan
instance uji. Sesudah itu dua keputusan pemilik, di tabel runbook yang sama:

- **K-16 — observasi adalah `(vm_name, run_id)`.** `layer5.latest()` menuntut
  VM-nya, dan bukti instance uji **tidak pernah** menjawab untuk instance
  utama. Run baru di `~/cosmictera-layer5/observations/<vm_name>/<run_id>/`;
  run lama tidak dipindahkan.
- **K-17 — instance uji dihentikan, tidak dihapus.** Pensiunnya menunggu
  provenance instance utama terbukti.

Kolektor pertama instance utama, `host_identity` saja, dijalankan ke namespace
barunya dan provenance-nya diperiksa sebelum kolektor lain — perintah pemilik.
Lapis 5 tetap **AT** sampai bukti instance utama benar-benar terkumpul.

**Sepuluh kolektor lainnya menyusul hari yang sama**, atas aba-aba pemilik,
dengan hasil yang sama dengan instance uji — `journal` dan `containers` tetap
unavailable, izin tidak diperluas. Pemeriksaan akhir membuktikan kueri instance
utama tidak pernah jatuh ke bukti uji, dan `host services` **tidak dipaksa
berubah**. Lalu instance uji dipensiunkan: VM dan disknya dihapus, tetapi
berkas kecil direktorinya disalin lebih dulu ke namespace-nya sendiri di
evidence store — **yang dipensiunkan adalah VM, bukan bukti P8.1–P8.5**.
Lapis 5 kini baseline utama dengan satu instance aktif, dan tetap **AT**.

### Perintah pemilik, 27 September 2026 — penutupan operasional Lapis 5

Sebelum Lapis 6 dibuka, dan **tanpa kolektor baru**: bekukan baseline utama,
beri HOST konsep kesegaran, beri NUI delta antar-run, lalu bekukan dengan
laporan, commit, dan annotated tag — bentuk Lapis 4, sebagai *host intelligence
baseline freeze*. Laporannya `NUI/LAYER5.md`, tagnya `layer5-freeze-2026-09-27`.

Tiga hal yang harus diketahui kuli berikutnya:

- **Batas "stale" tidak ditebak** — perintah pemilik. `stale_after_seconds` di
  `NUI/spec/layer5_collectors.json` bernilai `null` sampai pemilik
  menetapkannya, dan selama itu tidak ada observasi yang diklaim current.
- **Delta adalah observasi, bukan tindakan.** Aturan butir tiap kolektor masih
  usulan; `processes` yang dibandingkan pada data nyata hanya menunjukkan
  thread kernel yang berganti nama.
- **Freeze Lapis 5 memuat pointer dan hash saja** (K-11); isi observasinya
  tetap di evidence store, dan `--verify` hanya bisa dijalankan di mesin yang
  punya store itu.

Lapis 6 — *Hardware Intelligence* — tidak boleh berangkat dari asumsi bahwa
Lapis 5 sudah memahami perangkat keras.

**Tiga keputusan pemilik menutupnya, hari yang sama**: `stale_after_seconds` =
**300**, satu ambang global, dan jam mundur tetap *stale*; delta `processes`
dikunci — identitas USER + COMMAND, dan `kworker` saja dipisah sebagai
`kernel_thread_changes`, tidak dibuang; **label Lapis 5 naik ke EH**. Dengan
tes dan `layer5_freeze --verify` kembali *reproduced exactly*, **Lapis 5
selesai**, dan Lapis 6 dibuka atas aba-aba pemilik.

Konfigurasi final Lapis 5 ditandai pemilik dengan tag kedua,
`layer5-freeze-2026-09-27-final` di `80ea5f8`; tag pertama tetap di `02584d6`
dan **tidak dipindahkan**.

### Keputusan pemilik, 27 September 2026 — Lapis 6 dibuka: Hardware Intelligence

Empat langkah — 6.1 inventaris, 6.2 sumber telemetri, 6.3 provenance hardware,
6.4 kueri hardware pertama — dan satu aturan yang paling mudah dilanggar:
**mulai dari bukti hardware yang sudah ada.** Jangan membuat sensor, port
debug, telemetri baru, atau memilih arsitektur KV260 hanya untuk mengisi kolom
yang kosong; yang tidak punya jalur observasi tetap **UNKNOWN**. MEASURED
berarti dibuktikan secara fisik, SIMULATED berarti RTL atau interpreter.

**6.1 tutup hari itu**, tanpa menyentuh RTL atau papan: `NUI/HARDWARE.md`,
dibangun `src/hijaiyyah/nui/hardware.py`. Angkanya di `NUI/LAYERS.md`, Lapis
6. Laporan nextpnr (LUT4, DFF, BSRAM, Fmax) tetap SIMULATED dengan
`evidence_kind` = PNR/build-derived — bukan simulasi perilaku, bukan
pengukuran fisik (K-18). Judul Lapis 6 tetap *Pemahaman perangkat keras*;
*Hardware Intelligence* aliasnya (K-19).

**6.2 tutup hari yang sama**: registry sumber telemetri, `NUI/TELEMETRY_SOURCES.md`.
Pagarnya kalimat pemilik: **sumber yang ada tidak sama dengan sumber yang
sedang mengalir.** Hari ini tidak ada sumber hidup; jalur UART pernah
menghasilkan telemetri, dan itu historis. Keempat medan tanpa sumber tetap
UNKNOWN dan tidak diisi dari nama sinyal RTL.

**6.3 GREEN (`08ffbed`)**: provenance hardware,
`NUI/HARDWARE_PROVENANCE.md`, dibangun `src/hijaiyyah/nui/hardware_provenance.py`.
Karena tidak ada sumber live, **NUI tidak boleh mengklaim keadaan hardware
saat ini**: `hardware current-state` menjawab UNKNOWN — *no live hardware
telemetry source* — dan tidak pernah dari lari historis terakhir. Tiap klaim
6.1 dan 6.2 jadi satu objek kanonik dalam kosakata Lapis 5 — `observed_at` dan
`evidence_sha256`, tanpa `timestamp` atau `sha256` kedua — dengan satu dari
empat jenis sumber: historical_board_evidence, live, simulated, unknown.
Identitas lari papan dibaca dari buktinya sendiri, dan bukti papan tidak diberi
`vm_name`. Angkanya di `NUI/LAYERS.md`, Lapis 6. Yang harus diketahui kuli
berikutnya:

- **Tiga klaim MEASURED rantainya belum lengkap — jangan diisi dan jangan
  diturunkan paksa** (pemilik): HDMI dan reset pin MODE bersandar pada bagian
  halaman yang tidak menanggali pengamatan papannya, dan `boot_duration` pada
  satu baris CHECKLIST.md tanpa identitas run. Status klaim tetap MEASURED,
  verifikasi provenance tetap `incomplete`, dan ketiganya tidak boleh jadi
  dasar keadaan hardware sekarang.
- **Identitas run dari judul bagian ditandai, bukan diberi id baru**
  (pemilik): medan `run_identity` membawa
  *non-instrumented/inferred-from-record* untuk judul halaman yang dipertahankan
  persis, dan `instrumented` untuk run_id yang ditulis alat.
- **`evidence_kind` adalah istilah 6.3 yang tepat, dan registry 6.2 tidak
  diubah** (pemilik) — sekalipun `source_kind` di 6.2 memegang peran yang di
  6.3 bernama `evidence_kind`.
- **`cycle_rate` 649,4 dan `drift` −3,3 di `cosmictera/TELEMETRY.md` adalah
  selisih historis**: dicatat di model provenance, tidak disunting (pemilik).

**6.4 GREEN (`d6cfd6c`)**: model keadaan hardware,
`NUI/HARDWARE_STATE.md`, dibangun `src/hijaiyyah/nui/hardware_state.py` —
arti jawaban NUI atas pertanyaan hardware, bukan telemetri baru. Empat jenis
keadaan pemilik: IDENTITY, CAPABILITY, OBSERVED, CURRENT. Pagar yang paling
penting kalimat pemilik sendiri: **rekaman papan historis bukan keadaan
hardware sekarang** — lari papan terakhir menjawab apa yang terukur pada lari
itu, bukan apa yang sedang terjadi. Kueri CURRENT hanya dijawab sumber live
yang `access()` temukan, dan hari ini tidak ada. Precedence LIVE > MEASURED >
SIMULATED > UNKNOWN. Angkanya di `NUI/LAYERS.md`, Lapis 6. Dua penilaian
pemilik saat menutupnya:

- **Clock 27 MHz dan UART 115200 adalah CAPABILITY/konfigurasi, bukan
  IDENTITY.** `d6cfd6c` tidak diubah surut; koreksinya commit pemeliharaan
  tersendiri sesudah 6.5 GREEN. Karena keduanya MEASURED, pemilik memutuskan
  (28 September 2026) **CAPABILITY menerima MEASURED** — konfigurasi yang
  dibuktikan papan — bukan menurunkan status klaimnya.
- **P4 dan P5 bukan bukti tingkat opcode**: kolom P3 bukti tingkat opcode, P4
  dan P5 bukti tingkat program atau eksperimen. Jangan memaksakannya demi
  cakupan. Premis saya bahwa rekaman P4/P5 menautkan opcode hanya lewat nama
  keliru, dan dibetulkan di `NUI/LAYERS.md`: yang membuat P5 bukan bukti opcode
  adalah silikon yang menjalankan PRINT sesudah HALT, yang interpreter tidak
  pernah jalankan.

**6.5 GREEN (`3617a31`)**: korelasi hardware,
`NUI/HARDWARE_CORRELATION.md`, dibangun
`src/hijaiyyah/nui/hardware_correlation.py` — tautan hardware ↔ lari papan ↔
program ↔ opcode ↔ keluaran papan, bukan telemetri baru. Tiap tautan DIRECT
(tertulis eksplisit di bukti), DERIVED (dihitung dari struktur yang ada), atau
UNKNOWN (dengan alasannya). **Tidak ada tautan karena nama program tampak
mengandung sesuatu** — rekaman yang hanya menyebut sasaran punya program
UNKNOWN. `executes` adalah yang interpreter jalankan untuk payload dengan hash
yang sama, bukan yang papan jalankan, dan bukti tingkat opcode tetap kolom P3
saja. Angkanya di `NUI/LAYERS.md`, Lapis 6. Dikunci pemilik saat menutupnya:
P4/P5 tetap tingkat eksperimen; lari P2 `104300Z` tetap dikeluarkan dan tidak
dimasukkan lagi hanya karena hasilnya bisa dibaca; model korelasinya baseline
6.5. **Lapis 6 keseluruhan belum selesai**, dan nama atau arsitektur 6.6 tidak
dikarang — butir berikutnya diambil dari yang roadmap tetapkan.

### Arah pemilik, 18 September 2026 — lapisan di atas, bukan pengganti

CosmicTera **tidak dimaksudkan menggantikan** Windows, Linux, Android, server,
atau cloud. Ia lapisan di atas yang sudah berjalan: penguat, keamanan,
validasi, otomasi, dan pemulihan. Sistem utama tetap bekerja; CosmicTera
memeriksa, mengawasi, dan menyiapkan pemulihan di sampingnya, dengan NUI
sebagai pengawas dan pengorkestrasi. Komponennya bisa duduk di beberapa
tingkat — perangkat keras, firmware, driver, layanan, pustaka, kontainer,
aplikasi.

**Ini arah, bukan butir kerja**, dan pemiliknya sendiri yang menuliskan
syaratnya: apakah mekanisme itu lebih aman, lebih cepat, atau lebih tahan
serangan *"perlu dibuktikan melalui pengujian dan pengukuran pada implementasi
nyata"*. Empat pengukuran yang sudah ada membatasi apa yang boleh diklaim
sementara itu:

- **Yang memikul keamanan di Ka'bah hanya lapis 3**, HMAC-SHA256 standar
  (`a910375`, `kabah/README.md`). Lapis 4 — kerahasiaan — ditolak dengan
  sengaja, dan tidak ada inti SHA-256 di RTL (R10). Lapisan keamanan yang
  dijanjikan visi ini berdiri di atas satu lapis itu, bukan di atas lima.
- **Throughput terukur 2,59 MB/s**, hambatannya deserialiser (`49fb3b3`). Itu
  angka yang harus dipegang setiap kalimat tentang "mesin verifikasi di depan
  basis data".
- **Tidak ada satu pun sisi host di repo ini**: tidak ada driver, layanan,
  pustaka, kontainer, atau aplikasi. Yang ada hanya perkakas serial di
  `rtl/scripts/`. Seluruh baris tabel lintas platform berlabel **AT**.
- **Pola yang menetapkan cara membuktikannya sudah ada**: `3ccf193`
  menyerang sistem ini sendiri dan menemukan permutasinya bukan permutasi
  (rank 1276/1600). Klaim ketahanan tanpa lari serangan adalah klaim kosong.

### Arah pemilik, 18 September 2026 — KV260 sebagai node master

Bentuk akhirnya bukan papan pengembangan, melainkan **satu alat**: KV260 berisi
stack yang sudah lulus di Tang Nano 20K — NUI, Ka'bah, Codex, Hijrah, HISAB,
HOS/HFS, otomasi, pemulihan — dinyalakan, disambungkan ke jaringan, lalu
bekerja sebagai lapisan keamanan, pemantauan, otomasi, cadangan, dan pemulihan
bagi PC, server, atau laptop yang tersambung. Tang Nano membuktikan fungsi;
KV260 mengkonsolidasikan.

Empat hal terukur yang harus dibaca bersama gambar itu:

- **Sisi jaringan alat itu bukan HCPU.** Tidak ada satu baris pun tentang
  Ethernet atau TCP/IP di `rtl/` maupun `src/`; yang direncanakan hanyalah
  SLIP di atas UART, tahap 6 gerbang KV260, dan belum dimulai. KV260 punya
  GbE di sisi PS-nya, yaitu ARM — jadi gambar "sambungkan ke LAN" bersandar
  pada sisi ARM, dan itu **menyentuh pilihan Jalur A/B/C yang belum pemilik
  putuskan**.
- **`hijrah/` sudah ada dan sudah punya angka** — HIJRAH, Hijaiyyah Injection
  Raw Hertz, dengan langit-langit `log₂28 = 4,81` dan 4,56 sesudah lima
  komposisi atas GF(5) — tetapi **belum pernah dijalankan di papan**: ia tidak
  ada di `cosmictera-build/PAPAN.md`.
- **NUI hari ini adalah Python** (`NUI/`, `src/hijaiyyah/nui/atom.py`), dan
  yang pernah menyentuh papan hanyalah `rtl/programs/nui_embedding.hasm` —
  lima angka, `2 2 2 6 6`.
  "NUI Core sebagai otak sistem" berlabel **AT**.
- **Konsolidasi bukan penjumlahan.** Di papan ini ketiga slot berjumlah 211%
  dan hanya bisa bergiliran; alat yang menjalankan semuanya **bersamaan**
  adalah pertanyaan kapasitas KV260, bukan kesimpulan dari Tang Nano.

### Arah pemilik, 18 September 2026 — beda arsitektur, dan pengawasan aktif

Dua kalimat pemilik, dan keduanya arah, bukan butir kerja:

1. KV260 lebih sulit diserang **bukan karena kebal**, melainkan karena
   arsitekturnya berbeda: penyerang tidak hanya berhadapan dengan Windows atau
   Linux, tetapi juga dengan Hybit, Codex, Hijrah, Ka'bah, HOS, HFS, HISAB, dan
   NUI.
2. CosmicTera bukan lapisan yang bangun **sesudah** serangan, melainkan
   pengawas aktif atas laju, pola, dan integritas, supaya gejala terlihat lebih
   awal.

**Dua sifat yang mendukung kalimat pertama ada di RTL dan bisa diukur, jadi
bukan klaim.** Keduanya menutup satu kelas serangan yang paling umum di mesin
lain:

- **Alamat kembali tidak ada di memori data.** `ra_stack` hidup di
  `rtl/hcpu_execute.v`, 32 entri (`RA_DEPTH`), selebar alamat kode, dan tidak
  bisa dijangkau `LOAD`/`STORE` sama sekali. Melimpahi sebuah buffer di memori
  data karena itu tidak bisa menimpa alamat kembali.
- **Tumpukan `PUSH`/`POP` juga bukan memori data.** `stack` di
  `rtl/hcpu_memory.v`, 256 entri (`STACK_DEPTH`), dengan deteksi limpah dan
  kurang-isi (HC-02, HC-03). Ditambah tidak adanya lompatan terhitung, rantai
  gadget bergaya ROP tidak punya jalan yang biasa dipakainya.

**Dan inilah batasnya, supaya kalimat itu tidak tumbuh lebih besar dari
buktinya.** Yang masih di memori data dan bisa ditulis kernel: tabel syscall
(0xECE+), blok proses (0xF10+), tabel HFS (0xE80+), dan penyangga relokasi
loader (0x300). Proses pengguna dibatasi `mem_base`/`mem_limit` dan ditolak di
jendela 0xFF0+ — itu terbukti di papan — tetapi **belum ada satu pun lari
serangan terhadap HCPU**. Satu-satunya serangan yang pernah dijalankan proyek
ini adalah terhadap Ka'bah, dan ia menemukan cacat (`3ccf193`).

**Untuk kalimat kedua, yang kurang bukan mekanismenya, melainkan
garis dasarnya.** Yang sudah ada: daemon guard (`dc5ae55`), snapshot telemetri,
dashboard, pencacah siklus bebas, dan timer. Yang belum ada: pengukuran
"normal" untuk dibandingkan — lari terpanjang di papan ini masih hitungan
milidetik. Anomali laju hanya bisa dinamai sesudah laju normal diukur, dan itu
persis tahap 4 kerangka laboratorium (burn-in 24/72/168 jam).

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
- **Jangan pernah `git add -A` atau `git add .` di repositori ini.** Sebutkan
  path satu per satu. Terukur 18 September 2026: satu `git add -A` menarik 442
  berkas terlarang — `.agents/`, `.claude/`, `.codex/`, dan
  `Study Matematika Hijaiyyah/` — ke dalam sebuah commit, 860.181 baris,
  termasuk materi yang pemilik jaga di luar repo publik. Commit-nya dibatalkan
  sebelum jadi riwayat; yang mencegahnya berulang adalah kebiasaan ini, bukan
  `.gitignore` (berkas-berkas itu memang tidak terabaikan, hanya tidak
  di-commit).

---

## Menjaga catatan ini

Kalau catatan ini tidak cocok dengan commit atau berkas yang ditunjuknya, yang
dibetulkan catatannya — commit dan berkas adalah sumbernya. Keputusan baru
pemilik proyek ditambahkan di bagian 3 atau 4, lengkap dengan tanggalnya.
