# Dua belas lapis NUI — peta terhadap yang sudah ada

**Perintah pemilik, 21 September 2026.** NUI — *Natural Universal
Intelligence* — dibangun sebagai lapisan kecerdasan komputasi yang memahami
dan mengoperasikan seluruh ekosistem CosmicTera, dari huruf sampai silikon.
Namanya tetap; tidak ada nama baru, singkatan baru, atau rebranding. Bukan
chatbot, bukan pembungkus LLM, bukan sekadar classifier.

Aturan pemilik yang mengikat halaman ini, dan yang pertama adalah urutannya:
*"Gunakan seluruh aset yang sudah ada di repositori terlebih dahulu. Jangan
membuat sistem baru jika fungsi yang sama sudah ada."*

Halaman ini **peta**, bukan klaim kemampuan. Tiap lapis membawa lima hal:
tujuan, aset yang sudah ada, yang belum ada, cara verifikasi, dan syarat
selesai. Yang belum ada ditulis kosong — bukan diisi rencana yang terdengar
meyakinkan.

## Penomorannya sudah berubah empat kali, dan lapisnya dikunci pada nama

Direktif NUI datang empat kali dan menomori lapisnya empat cara.
**Yang berlaku yang terakhir**, dan pergeserannya dicatat di sini supaya tidak
diam-diam — pola yang sama dipakai ketika urutan field tabel program bergeser
antara dua pesan.

| lapis (nama) | pesan 1 | pesan 2 | pesan 3 | **berlaku** |
|---|---:|---:|---:|---:|
| pengetahuan terverifikasi | 0 | 0 | 0 | **0** |
| pemahaman repositori | 6 | 1 | 1 | **1** |
| pemahaman program | 3 | 2 | 2 | **2** |
| pemahaman eksekusi | — | 3 | 3 | **3** |
| paritas perangkat lunak ↔ keras | 8 | 4 | 4 | **4** |
| integrasi Linux | 5 | 5 | 5 | **5** |
| pemahaman perangkat keras | 7 | 6 | 6 | **6** |
| operasi otonom | — | — | — | **7** |
| diagnostik otonom | — | 8 | 7 | **8** |
| mesin penalaran | — | 9 | 9 | **9** |
| rekayasa | 11 | 10 | 11 | **10** |
| komputasi universal | — | 11 | 10 | **11** |

**Isinya yang tidak berubah adalah asetnya.** Empat penomoran, dan daftar
aset, celah, serta cara verifikasi tiap lapis hampir tidak bergeser — yang
berpindah nomornya. Karena itu halaman ini dikunci pada **nama**: nomornya
atribut, dan tabel di atas satu-satunya tempat ia hidup.

**Dua lapis hilang di sepanjang jalan, dan asetnya tidak ikut hilang.**
*Verifikasi fisik* (pesan 2) — tangga bukti empat tingkat di `AGENTS.md`,
`cosmictera-build/PAPAN.md`, sidik jari place and route, dan fakta `board` di
`facts/` tetap berlaku. *Perencanaan perbaikan otonom* (pesan 3) — isinya kini
keluaran Lapis 8 (akar masalah, bukti, jalur reproduksi), dan disiplinnya
tetap tertulis: K3–K6 dan R3.

Penomoran kelima, Fase 0–5 di `NUI/ROADMAP.md`, juga tidak dihapus:
Fase 2 = Lapis 2, Fase 3 = Lapis 0, dan Fase 4 = Lapis 10.

## Yang sudah berjalan hari ini, diukur

`src/hijaiyyah/nui/` berisi **21 modul**; `tests/test_ai/` berisi **178 tes**
yang lulus, ditambah 10 tes inventaris fakta. PyTorch 2.14.0 terpasang. Semua
angka di halaman ini datang dari menghitung berkasnya.

| modul | apa yang ia lakukan | tes |
|---|---|---|
| `features.py` | tiap huruf jadi 5 angka geometris dari Master Table tersegel | `test_nui.py` |
| `dataset.py` | akumulasi huruf sungguhan, label primitivitas GF(2)/GF(5), rank | `test_nui.py` |
| `model.py` | jaringan permutation-invariant atas huruf terakumulasi | `test_nui.py` |
| `train.py` | melatih dan **membandingkan empat varian embedding, jujur** | `test_nui.py` |
| `multitask.py` | satu trunk, tiga pertanyaan berbeda | `test_nui_multitask.py` (13) |
| `atom.py` | satu huruf, satu alamat: indeks Master Table = opcode HISA = alamat ROM | `test_nui_atom.py` (6) |
| `rack.py` | 28 huruf sebagai rak chip | `test_nui_rack.py` (8) |
| `clockwork.py` | mekanisme deterministik per tick | `test_nui_clockwork.py` (27) |
| `freeze.py` | protokol kabel loader dipalsukan jamnya, bukan protokolnya | `test_nui_freeze.py` (22) |
| `sram_mock.py` | protokol twin-port makro SRAM sky130 | `test_nui_sram_mock.py` (10) |
| `claims.py` | klaim luar diuji terhadap data tersegel — **keduanya negatif** | `test_nui_claims.py` (6) |
| `pattern_language.py` | "Titik → Transform → Garis" diuji sebagai urutan komposisi | `test_nui_pattern_language.py` (7) |
| `facts.py` | inventaris fakta Lapis 0 | `test_facts.py` (10) |
| `repository_index.py` | node repositori, terklasifikasi | `test_nui_repository_graph.py` (13) |
| `repository_graph.py` | edge repositori, tiap satunya dengan barisnya | `test_nui_repository_graph.py` |
| `program_index.py` | 62 program HASM, 1.123 fungsi Python, 120 modul Verilog, terurai | `test_nui_program_index.py` (9) |
| `program_graph.py` | `CALL` HASM ke label, instansiasi Verilog ke modul | `test_nui_program_index.py` |
| `program_summary.py` | apa yang dilakukan tiap unit, efek diturunkan dari badannya | `test_nui_program_index.py` |
| `execution_trace.py` | satu lari di interpreter, direkam saat berjalan: sebelum → sesudah tiap langkah | `test_nui_execution.py` (25) |
| `execution_graph.py` | 63 lari, 1.890 edge eksekusi, inventaris UNKNOWN | `test_nui_execution.py` |

---

## Lapis 0 — Pengetahuan terverifikasi

**Tujuan.** Basis fakta yang tiap butirnya punya sumber, bukti, dan cara
verifikasi.

**Aset yang sudah ada.** `facts/` — 26 fakta di tujuh domain — dimuat dan
diperiksa `src/hijaiyyah/nui/facts.py`, dijaga
`tests/test_integrity/test_facts.py`. Sumber lamanya tetap:
`src/hijaiyyah/core/master_table.py` (tersegel),
`src/hijaiyyah/core/guards.py`, `src/hijaiyyah/core/exomatrix.py`,
`src/hijaiyyah/crypto/cube.py`, `docs/HISA_SPEC.md`,
`cosmictera/TELEMETRY.md`, `src/hijaiyyah/nui/claims.py`,
`src/hijaiyyah/nui/atom.py`.

Dari 26 fakta: **9 dihitung ulang** tiap kali tes berjalan, **9 dibuktikan
sebuah tes**, **8 diukur di papan** dan ditandai tidak bisa diulang tanpa
perangkat kerasnya. Lima yang terakhir datang dari burn-in tingkat 1 yang
tutup 21 September.

**Yang belum ada.** Cakupan — 26 fakta permulaan, bukan seluruh yang terukur
di repo ini — dan sisi bertanya: basis ini bisa dimuat dan diperiksa, belum
ditanyai per-objek.

**Cara verifikasi.** Sudah berjalan: `derive` dihitung ulang, `pytest`
menyebut node yang harus ada, `board` menyebut perintahnya. Tiga sabotase
diuji dan ketiganya merah.

**Syarat selesai.** Tercapai untuk bentuknya; belum untuk cakupannya.

---

## Lapis 1 — Pemahaman repositori

**Tujuan.** Membaca pohon proyek, memahami modul dan hubungan antar modul.

**Aset yang sudah ada.** `tests/test_integrity/` sudah mengkodekan banyak
hubungan itu sebagai penjaga: `test_agent_notes.py` (tiap commit dan berkas
yang disebut harus ada), `test_build_list.py`, `test_recipe_folders.py`,
`test_place_and_route.py` (sidik jari RTL terhadap wrapper), dan sekarang
`test_nui_layers.py` serta `test_facts.py`.

**Sejak 21 September 2026 grafnya ada**: `src/hijaiyyah/nui/repository_index.py`
dan `src/hijaiyyah/nui/repository_graph.py` (`imports`, `mentions`,
`references`, `verifies`, `defines`), dijaga `tests/test_ai/test_nui_repository_graph.py` dan
dijelaskan di [`GRAPH.md`](GRAPH.md). Ia menjawab kelima pertanyaan yang
pemilik tuliskan, termasuk "tes mana yang harus gagal kalau berkas ini rusak".

Direktif keempat meminta node **kelas, fungsi, dan dokumentasi** dengan relasi
*references*, dan sekarang keduanya ada: 91 dokumen yang **git lacak** (edge
`references`, tidak pernah dihitung sebagai import) dan 668 definisi tingkat
atas di `src/` (edge `defines`). Graf kini **1.299 node, 3.390 edge**.

**Angka 745 yang dulu tertulis di sini salah.** Ia hasil `find` di disk, yang
ikut menghitung folder pribadi yang tak pernah di-commit. Repositori memuat
**91** berkas Markdown; sumbernya sekarang `git ls-files`, dan satu tes gagal
kalau dokumen diambil dari disk lagi.

**Yang belum ada.** **Edge pemanggilan** — fungsi mana memanggil fungsi mana.
`ast` melihat modul mengimpor modul; melihat panggilan di bahasa dinamis butuh
lebih dari parse, dan itu akan jadi inferensi pertama di graf yang dibangun
supaya tidak punya satu pun.

**Satu contoh yang sudah diukur, dan rantainya tidak seperti yang dikira.**
Perintah pemilik mencontohkan `atom → rack → clockwork → freeze → multitask`.
Diukur dari `import`-nya sendiri:

```
atom      → (tidak mengimpor modul NUI lain)
rack      → atom
clockwork → atom, rack
freeze    → rack           (bukan dari clockwork)
multitask → dataset, model (tidak menyentuh freeze sama sekali)
facts     → atom
model     → dataset
```

Tiga sambungan pertama benar; dua terakhir tidak. Itulah yang lapis ini ada
untuk menghasilkan.

**Cara verifikasi.** Sudah berjalan: tiap edge `imports` harus mendarat di
baris yang benar-benar mengimpor, tiap `mentions` di baris yang benar-benar
menyebut nama berkasnya — diperiksa untuk **seluruh** edge, bukan
sampel.

**Syarat selesai.** Tercapai untuk import, referensi, dan verifikasi; belum
untuk panggilan.

---

## Lapis 2 — Pemahaman program

**Tujuan.** Membaca `.hasm` dan mengeluarkan opcode, operand, alur, efek
register, efek memori.

**Aset yang sudah ada.** `src/hijaiyyah/hisa/assembler.py` dan
`src/hijaiyyah/hisa/machine.py` sebagai **ground truth**, `src/hijaiyyah/hvm/`,
dan **59 program HASM** di `rtl/programs/` dan `rtl/programs/bench/`.

**Sejak 21 September 2026 lapis ini berdiri**:
`src/hijaiyyah/nui/program_index.py` (62 program HASM, 1.123 fungsi Python,
120 modul Verilog), `src/hijaiyyah/nui/program_graph.py` (277 `CALL` dan 125
instansiasi, semuanya terselesaikan), `src/hijaiyyah/nui/program_summary.py`
(apa yang dilakukan tiap unit, diturunkan dari badannya, tiap efek dengan
barisnya), dijaga `tests/test_ai/test_nui_program_index.py` dan dijelaskan di
[`PROGRAMS.md`](PROGRAMS.md).

**Yang belum ada.** Tautan fungsi-ke-fungsi Python — nama yang dipanggil
dicantumkan apa adanya dan ditandai tak terselesaikan. Dan apakah sebuah
register benar-benar tercapai saat berjalan: itu Lapis 3.

**Cara verifikasi.** Sudah berjalan, dua arah: tiap efek turunan menunjuk ke
baris yang menghasilkannya, dan efek `loader.hasm` diperiksa terhadap
**eksekusi** lewat `freeze_load()`.

**Syarat selesai.** Tercapai untuk HASM dan Verilog; untuk Python sebatas yang
bisa dibaca tanpa menebak.

---

## Lapis 3 — Pemahaman eksekusi

**Tujuan.** Bukan hanya membaca kode, melainkan tahu keadaan **sebelum →
instruksi → sesudah** untuk tiap langkah.

**Aset yang sudah ada.** `HISAMachine.step()` melangkah satu instruksi, dan
setiap akses data — biasa maupun memory-mapped — lewat dua metodenya sendiri,
`_mem_read` dan `_mem_write`. Itulah ground truth yang pemilik sebut, dan
sudah dipakai nyata oleh `rtl/scripts/attack_lab.py` dan
`tests/test_integrity/test_burn_in.py`.

**Sejak 21 September 2026 lapis ini berdiri**:
`src/hijaiyyah/nui/execution_trace.py` merekam satu lari **saat berjalan** —
membungkus kedua metode akses itu, jadi alamat efektif yang tercatat adalah
yang mesin hitung dari register yang benar-benar ia pegang — dan
`src/hijaiyyah/nui/execution_graph.py` menggabungkan semua lari jadi satu
model, `NUI/execution_model.json`. Dijaga
`tests/test_ai/test_nui_execution.py` (25) dan ditarik ke
[`EXECUTION.md`](EXECUTION.md) oleh kodenya sendiri.

- **63 lari**: 62 program HASM, ditambah `loader.hasm` yang membawa program
  tiga kata di kabelnya. Keluar: 43 `halt`, 12 `step_cap`, 6 `end_of_code`,
  2 `hcheck`.
- **1.890 edge** dari sembilan jenis yang pemilik tetapkan, tiap satunya
  dengan langkah pertama dan `berkas:baris` sumbernya. `READS` dan `OBSERVES`
  dibedakan oleh pengukuran — apakah antrean UART menyusut selama baca itu —
  bukan oleh nama registernya. Ke-106 `CALLS` mendarat di label yang diikat
  pass pertama assembler: itu node fungsinya.
- **Jejak penuh tiap lari** — ENTRY, lalu tiap STEP dengan `CHANGE`
  sebelum → sesudah (register, komponen H-register, flag, memori data, code
  memory, dan state mesin di bawah nama atributnya sendiri) atau `NO_CHANGE`,
  lalu EXIT — dicetak `--trace` dan dipegang model lewat SHA-256-nya.

Pertanyaan pemilik, *"Bagaimana loader.hasm memindahkan kontrol?"*, dijawab
dari model, bukan dari kode: langkah 174 `WRITES TRAP_EPC` (`loader.hasm:71`),
176 `WRITES TRAP_MODE` (`:73`), 177 `RESUMES pc:0x040` (`:74`); payload lalu
mencetak 7 dan berhenti. Urutan contoh pemilik — `RX_STATUS`, `RX_DATA`,
`IMEM_ADDR`, `IMEM_DATA`, `TRAP_EPC`, `TRAP_MODE`, `ERET` — ditemukan di
jejak loader dengan urutan yang sama.

**Satu cacat yang lapis ini temukan pada lari pertamanya.** Interpreter
menyatakan `_halted`, tetapi jalur HC-04 (CALL luber) dan HC-05 (RET tanpa
alamat kembali) menulis `halted` — atribut yang tak dibaca siapa pun. Mesin
melaporkan HC-05 lalu **terus berjalan**: `RET` yang diikuti `MOVI R1, 5`,
`PRINT R1`, `HALT` mencetak `5`. `docs/HISA_SPEC.md` (0x2F) dan
`rtl/hcpu_execute.v` sama-sama berhenti di situ. Enam program pustaka yang
dijalankan sendirian mencapainya, dan itulah keenam `end_of_code` di atas.
`tests/test_integrity/test_subroutine.py` tidak melihatnya: ia memeriksa
`m.halted` — atribut yang diciptakan cacat itu sendiri — dan programnya
menaruh `HALT` tepat sesudah `RET`.

**Yang belum ada.** Eksekusi **RTL** tidak dijejak di sini; menyatukannya
dengan jejak interpreter adalah Lapis 4. Eksekusi **Python** juga tidak:
rantai `atom → rack → clockwork → freeze → multitask` dari direktif keempat
masih terukur lewat import saja (Lapis 1), dan entry mana yang dihitung
sebagai satu lari Python belum diputuskan. Tiap program berjalan sendirian di
alamat 0 tanpa masukan UART, kecuali loader; yang bergantung pada kabel, kartu
SD, atau jam nyata dicatat di inventaris UNKNOWN, bukan diisi.

**Cara verifikasi.** Sudah berjalan: `verify()` membangun ulang model dari
repositori dan menamai tiap klaim yang tidak terulang. Ketiga sabotase yang
pemilik wajibkan — edge eksekusi palsu, register palsu, MMIO palsu — merah,
begitu pula bukti yang dipindah langkahnya, jumlah yang salah, dan jejak
palsu. Delapan penjaga baru disabotase satu per satu dan kedelapannya merah.

**Syarat selesai.** Tercapai untuk interpreter: tiap program HASM punya
jejak, tiap MMIO tertelusur ke register bernama, tiap trap punya sumber
(`epc`) dan tujuan (vektor — tiga probe `rtl/tb/` mendarat di vektor 0
karena handlernya dipasang shell, dan tercatat begitu), dan pertanyaan loader
dijawab dari model. RTL dan Python di luar cakupan, tercatat di atas.

---

## Lapis 4 — Paritas perangkat lunak dan perangkat keras

**Tujuan.** Tiap opcode terlacak dari sumber → assemble → interpreter → RTL →
papan.

**Aset yang sudah ada — ini lapis terkuat di repositori.** `698dd3e` tiga
mesin sepakat; `44ba928` HVM menjalankan semua opcode RTL;
`rtl/scripts/jamrah_board.py`, `rtl/scripts/hijrah_board.py`,
`rtl/scripts/kabah_board.py` masing-masing membandingkan papan dengan Python
dan **sudah menemukan beda**.

**Yang belum ada.** Penemuan divergensi yang otomatis dan menyeluruh; hari ini
tiap perbandingan ditulis tangan per modul.

**Cara verifikasi.** Perbandingan yang sudah ada, dan sabotase yang harus
merah (R3).

**Syarat selesai.** Untuk daftar opcode yang disebut, tiap wujudnya
dibandingkan otomatis dan yang berbeda dilaporkan dengan namanya.

---

## Lapis 5 — Integrasi Linux

**Tujuan.** Memahami host nyata: menjalankan program, membaca log,
filesystem, proses, service, runtime. Targetnya Ubuntu Linux.

**Aset yang sudah ada.** **Tidak ada.** `AGENTS.md` sudah mencatatnya: tidak
ada satu pun sisi host di repositori ini — tidak ada driver, layanan,
pustaka, kontainer, atau aplikasi. Yang ada hanya perkakas serial di
`rtl/scripts/`, dan mesin pengembangannya macOS, bukan Ubuntu.

**Yang belum ada.** Seluruhnya.

**Cara verifikasi.** Belum bisa ditetapkan sebelum ada yang dibangun.

**Syarat selesai.** Belum ditetapkan.

**Labelnya sudah diputuskan: AT.** Pesan kedua menandai lapis ini EH; selisih
terhadap definisi `cosmictera/RULES.md` sendiri — EH "terukur, belum
dikriptanalisis" melawan AT "belum dikerjakan" — dilaporkan, dan pesan ketiga
menjawabnya dengan **AT**. Itu label yang cocok dengan tabelnya.

---

## Lapis 6 — Pemahaman perangkat keras

**Tujuan.** Memahami HCPU, UART, SRAM, pipeline, loader, peta memori.

**Aset yang sudah ada.** `rtl/` (30 modul HCPU, 13 modul Ka'bah, 26
testbench), `rtl/fpga/`, `rtl/mpw/`; `rtl/scripts/lint_hcpu.py`;
`tests/test_integrity/test_board_wiring.py` yang mengurai port Verilog;
`rtl/scripts/rack.py` untuk biaya slot bitstream; dan dua model perangkat
keras yang sudah berjalan di Python — `src/hijaiyyah/nui/sram_mock.py`
(protokol twin-port) dan `src/hijaiyyah/nui/freeze.py` (protokol kabel
loader).

**Yang belum ada.** Model RTL sebagai fungsi. Yang ada mengurai antarmuka dan
memodelkan dua protokol, bukan perilaku umum.

**Cara verifikasi.** 26 testbench di `rtl/tb/` adalah oracle-nya.

**Syarat selesai.** Prediksi keadaan berikutnya untuk modul yang disebut cocok
dengan benchnya.

---

## Lapis 7 — Operasi otonom

**Tujuan.** Menjalankan sistem tanpa pengawasan manusia: memantau, memulihkan,
memulai ulang, mengisolasi kesalahan — berdasarkan telemetri, diagnostik, dan
fakta terverifikasi.

**Aset yang sudah ada, kecil dan nyata, dan sudah berjalan di papan.**
`rtl/scripts/burn_in.py` **memulihkan sendiri**: kalau kartu SD tidak naik
sesudah rekonfigurasi, ia mengkonfigurasi ulang papan dan mengirim programnya
lagi — dan itu sudah terjadi di perangkat keras (percobaan pertama 72 jam
butuh dua peluncuran, probe sebelumnya tiga). Ia **menjaga pengamatnya**:
`caffeinate` menahan host tetap terjaga selama logger hidup.
`rtl/scripts/burn_in_report.py` **mengisolasi kesalahan**: tiap diam
digolongkan milik papan atau milik host dengan membandingkan kedua jam.

**Yang belum ada.** Semua itu terbatas pada satu harness dan satu jenis
kegagalan. Tidak ada yang memulai ulang layanan atau memulihkan kegagalan di
luar burn-in, dan tidak ada yang bisa memulihkan host yang berhibernasi —
itu yang membunuh percobaan pertama 72 jam.

**Cara verifikasi.** Pemulihan dihitung dari catatan lari: berapa peluncuran,
berapa diam, milik siapa.

**Syarat selesai.** Belum ditetapkan.

---

## Lapis 8 — Diagnostik otonom

**Tujuan.** Mendeteksi dan menjelaskan masalah: akar masalah, bukti, dan jalur
reproduksinya.

**Aset yang sudah ada.** Alat yang menemukan, tetapi dijalankan tangan:
`rtl/scripts/jamrah_board.py`, `rtl/scripts/hijrah_board.py`,
`rtl/scripts/kabah_board.py`, `rtl/scripts/attack_lab.py`,
`rtl/scripts/burn_in_report.py`, empat gerbang, dan disiplin R3. Perencanaan
perbaikan, yang dulu lapis sendiri, kini keluaran lapis ini — dan disiplinnya
tertulis: K3–K6, dan `073b968` yang menemukan akar lalu sengaja tidak
menambal karena perbaikannya keputusan pemilik.

**Yang sudah benar-benar ditemukan**, masing-masing dengan akar, bukti, dan
jalur reproduksinya: gerbang RTL Jamrah **tidak ada di slot Ka'bah**;
permutasi Ka'bah **bukan permutasi** (rank 1276/1600, `3ccf193`); celah N_CC
SDIO yang **papan** temukan (`708a9cd`); `PRINT` salah untuk nilai besar;
kartu gagal init sesudah rekonfigurasi di tengah pembacaan; dan — yang
membedakan kegagalan papan dari kegagalan pengamat — diam-diam burn-in yang
ternyata **MacBook yang tidur**, dan percobaan 72 jam pertama yang mati karena
Mac **berhibernasi**, keduanya dibuktikan dari catatan daya host sendiri.

**Mismatch latensi SRAM tidak ada di daftar itu.**
`src/hijaiyyah/nui/sram_mock.py` memodelkan latensi satu siklus dan 10 tesnya
hijau; tidak ada catatan mismatch yang pernah ditemukan.

**Yang belum ada.** Yang otomatisnya — hari ini semua alat itu diarahkan orang.

**Cara verifikasi.** Temuan harus reproducible dengan perintah yang dicatat,
seperti tiap baris `cosmictera-build/CHECKLIST.md`.

**Syarat selesai.** Untuk kelas masalah yang disebut, alat menemukannya tanpa
diberi tahu di mana harus melihat.

---

## Lapis 9 — Mesin penalaran

**Tujuan.** Penalaran berbasis fakta, dengan urutan pemilik: fakta → relasi →
inferensi → kesimpulan, dan penalaran tidak boleh mendahului bukti.

**Aset yang sudah ada.** **Tidak ada** sebagai penalaran. Yang ada bahannya,
dan kini tiga dari empat anak tangganya: fakta (`facts/`, Lapis 0), relasi
(graf Lapis 1 dan graf program Lapis 2), dan jejak interpreter (Lapis 3,
belum dibangun).

**Yang belum ada.** Seluruh penalarannya. Lapis ini tidak bisa berdiri sebelum
Lapis 1 punya grafnya — yang sekarang ada — dan Lapis 3 punya jejaknya.

**Cara verifikasi.** Setiap kesimpulan harus bisa ditelusuri kembali ke bukti.

**Syarat selesai.** Belum ditetapkan.

---

## Lapis 10 — Rekayasa

**Tujuan.** Menghasilkan perubahan sistem — patch, refaktor, modifikasi RTL,
optimasi — dengan urutan pemilik: cari aset, ukur, verifikasi, identifikasi
celah, **baru** bangun.

**Aset yang sudah ada.** **Tidak ada** sebagai kemampuan NUI. Yang mendekat
adalah generator yang ditulis tangan — `rtl/scripts/build_container.py`,
`rtl/scripts/jamrah_board.py` yang membangkitkan program dari badan
`jamrah_gate.hasm` kata demi kata, `rtl/scripts/attack_lab.py`,
`rtl/scripts/gen_rom.py` — tetapi tak satu pun memutuskan apa yang dibangun.
Urutan pemilik itu sendiri sudah dipegang tangan: ia persis K3–K6.

**Yang belum ada.** Seluruhnya.

**Cara verifikasi.** Artefak harus lolos oracle yang sama dengan artefak
tulisan tangan: assembler, interpreter, bench, papan, empat gerbang.

**Syarat selesai.** Belum ditetapkan.

---

## Lapis 11 — Komputasi universal

**Tujuan.** Menyatukan semua lapis jadi satu model: perangkat lunak,
perangkat keras, sistem operasi, repositori, eksekusi, fakta, dan rekayasa.

**Aset yang sudah ada.** Satu sambungan dari rantai itu **sudah terbukti dan
terukur**: `src/hijaiyyah/nui/atom.py` membuktikan indeks Master Table, opcode
H-ISA, dan alamat ROM HCPU adalah satu alamat — huruf sampai mesin, untuk
ke-28 huruf. Sisanya ada sebagai bagian yang belum dijahit.

**Yang belum ada.** Penyatuannya. Satu sambungan bukan rantai.

**Cara verifikasi.** Tiap sambungan harus punya oracle seperti
`verify_address_unification` punya.

**Syarat selesai.** Tiap sambungan dalam rantai punya pemeriksaan yang
dijalankan, bukan diagram.

---

## Yang tidak boleh diklaim

Aturan pemilik, disalin apa adanya karena ia mengikat: **jangan pernah**
mengklaim AGI, kesadaran, inteligensi manusia, atau kemampuan yang belum
diuji. Label epistemik tidak naik tanpa bukti baru (R2).

Dan satu batas yang sudah terukur, supaya tidak hilang di antara dua belas
lapis: dari empat varian embedding yang diadu `train.py`, varian
**eksomatriks** — struktur yang kriptografi Ka'bah sendiri pakai — adalah yang
**paling konservatif**, recall 0,4%. Struktur yang benar secara matematis
tidak otomatis berguna sebagai representasi, dan itu diukur, bukan
diperdebatkan.
