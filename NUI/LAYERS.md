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

## Arahan kelima — lapisan semantik di atas mesin yang terbukti

**Arahan pemilik, 21 September 2026, sesudah Lapis 4.** NUI bukan komputer
baru, melainkan sistem komputasi universal berbasis struktur Hijaiyyah yang
berjalan di atas Linux, HISA VM, RTL HCPU, FPGA, dan perangkat keras
berikutnya. Tiga bahasa manusia — Arab, Indonesia, Inggris — dan satu bahasa
komputasi, *Hijaiyyah Computing Language* (HCL). Rantainya: bahasa manusia →
pohon semantik → *Universal Semantic Representation* (USR) → compiler
Hijaiyyah → HISA → RTL HCPU → FPGA/ASIC, dengan Linux sebagai host utama.
Arahan ini tidak menomori ulang lapis; ia menetapkan ke mana lapis-lapis itu
menuju.

Diukur terhadap repositori pada hari yang sama:

| bagian arahan | yang sudah ada, terukur | yang belum ada |
|---|---|---|
| bahasa komputasi | HC — *Hybit Code* (`teknologi/ISTILAH.md` baris 33): lexer, parser, dan evaluator di `src/hijaiyyah/language/`, compiler ke H-ISA di `src/hijaiyyah/compiler/codegen.py` | kata kunci selain Inggris: `src/hijaiyyah/language/tokens.py` hanya punya `let`, `fn`, `if`, dan seterusnya |
| contoh pemilik, `متغير س = 10` / `متغير ص = 20` / `اطبع س + ص` | bentuk HC-nya, `let s = 10; let p = 20; println(s + p);`, jadi lima instruksi (`MOVI MOVI ADD PRINT HALT`); interpreter mencetak `30`, RTL mengirim `30\n` ke kabel | kata kunci Arab ditolak parser; nama variabel Arab juga ditolak, karena di HC huruf Hijaiyyah telanjang adalah **literal hybit** (`src/hijaiyyah/language/lexer.py` baris 89) — `let س = 10` menjawab `Expected variable name (got HIJAIYYAH 'س')` |
| compiler Arab ↔ HISA | jalur HC → H-ISA → interpreter → RTL (`698dd3e`, Lapis 4) | pemetaan kata Arab dan Indonesia ke konstruksi HC — lima kata kunci ditetapkan pemilik, di bawah |
| USR | — | implementasinya; bentuknya ditetapkan pemilik, di bawah |
| antarmuka bahasa alami | `src/hijaiyyah/ai/runtime.py`, yang menjalankan program bergaya HC lewat model Ollama lokal | versi yang deterministik: arahan pertama menolak pembungkus LLM, dan aturan Lapis 3 menolak probabilitas |
| Linux sebagai host | — (Lapis 5, **AT**); mesin pengembangan ini macOS 26.6.2 arm64, dan tidak ada `docker`, `podman`, `colima`, `lima`, `multipass`, `qemu`, UTM, atau OrbStack terpasang | host Ubuntu itu sendiri |

**Dua batas yang tertulis menyentuh arahan ini, dan pemilik menjawab
keduanya pada hari yang sama** (keputusannya di `AGENTS.md`):

- `CONTRIBUTING.md` melarang, pada level konsep, *"memperlakukan huruf sebagai
  bunyi/makna"*. Jawabannya: USR **bukan** vektor huruf, bukan embedding, bukan
  LLM, melainkan lima medan — ACTION, OBJECT, TARGET, CONTEXT, STATE — dan
  huruf Hijaiyyah tunggal tetap objek matematika. Jadi `متغير س = 10` **tidak
  sah**, persis seperti yang parser hari ini jawab; nama variabel Arab adalah
  kata penuh, `متغير العدد = 10`.
- Dua nama untuk satu hal adalah cacat (`7582ae5`). Jawabannya: **HCL = HC**,
  diperluas — bukan bahasa baru, dan bukan lapisan di atas HC. Nama di
  repositori tetap HC.

Kata kunci multibahasa tahap pertama hanya lima, dan *"jangan tambah sampai
pipeline terbukti"*:

| HC | Arab | Indonesia |
|---|---|---|
| `let` | `متغير` | `variabel` |
| `print` | `اطبع` | `cetak` |
| `if` | `اذا` | `jika` |
| `while` | `بينما` | `selama` |
| `function` | `دالة` | `fungsi` |

Prioritasnya bukan bahasa: Lapis 5 lebih dulu, karena NUI harus mampu
mengendalikan sistem nyata sebelum diajak bicara.

**Satu ketidakcocokan kecil di jalur yang akan dipakai arahan ini.**
`src/hijaiyyah/compiler/codegen.py` membagikan register sampai R17, sedangkan
assembler berhenti di R15: program dengan enam belas atau tujuh belas
variabel hidup lolos dikompilasi lalu ditolak assembler dengan keras —
`register R16 is out of range (max R15)`. Tidak ada kompilasi yang diam-diam
salah. Dilaporkan, belum disentuh.

## Yang sudah berjalan hari ini, diukur

`src/hijaiyyah/nui/` berisi **23 modul**; `tests/test_ai/` berisi **208 tes**
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
| `program_index.py` | 62 program HASM, 1.172 fungsi Python, 120 modul Verilog, terurai | `test_nui_program_index.py` (9) |
| `program_graph.py` | `CALL` HASM ke label, instansiasi Verilog ke modul | `test_nui_program_index.py` |
| `program_summary.py` | apa yang dilakukan tiap unit, efek diturunkan dari badannya | `test_nui_program_index.py` |
| `execution_trace.py` | satu lari di interpreter, direkam saat berjalan: sebelum → sesudah tiap langkah | `test_nui_execution.py` (26) |
| `execution_graph.py` | 63 lari, 1.478 edge eksekusi, inventaris UNKNOWN | `test_nui_execution.py` |
| `parity_model.py` | interpreter ↔ RTL ↔ papan per program dan per opcode, selisih pertama dengan langkahnya | `test_nui_parity.py` (19) |
| `board_parity.py` | apa yang dikirim ke papan dan apa yang harus kembali, dengan epilog pembaca register | `test_nui_board_parity.py` (10) |

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
*references*, dan sekarang keduanya ada: 92 dokumen yang **git lacak** (edge
`references`, tidak pernah dihitung sebagai import) dan 722 definisi tingkat
atas di `src/` (edge `defines`). Graf kini **1.360 node, 3.581 edge**.

**Angka 745 yang dulu tertulis di sini salah.** Ia hasil `find` di disk, yang
ikut menghitung folder pribadi yang tak pernah di-commit. Repositori memuat
**92** berkas Markdown; sumbernya sekarang `git ls-files`, dan satu tes gagal
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
`src/hijaiyyah/nui/program_index.py` (62 program HASM, 1.172 fungsi Python,
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
`tests/test_ai/test_nui_execution.py` (26) dan ditarik ke
[`EXECUTION.md`](EXECUTION.md) oleh kodenya sendiri.

- **63 lari**: 62 program HASM, ditambah `loader.hasm` yang membawa program
  tiga kata di kabelnya. Keluar: 43 `halt`, 12 `step_cap`, 6 `fault`,
  2 `hcheck`.
- **1.478 edge** dari sembilan jenis yang pemilik tetapkan, tiap satunya
  dengan langkah pertama dan `berkas:baris` sumbernya. `READS` dan `OBSERVES`
  dibedakan oleh pengukuran — apakah antrean UART menyusut selama baca itu —
  bukan oleh nama registernya. Ke-93 `CALLS` mendarat di label yang diikat
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

**Satu cacat yang lapis ini temukan pada lari pertamanya, dan sudah
diperbaiki.** Interpreter menyatakan `_halted`, tetapi jalur HC-04 (CALL
luber) dan HC-05 (RET tanpa alamat kembali) menulis `halted` — atribut yang
tak dibaca siapa pun. Mesin melaporkan HC-05 lalu **terus berjalan**: `RET`
yang diikuti `MOVI R1, 5`, `PRINT R1`, `HALT` mencetak `5`.
`docs/HISA_SPEC.md` (0x2F) dan `rtl/hcpu_execute.v` sama-sama berhenti di
situ. `tests/test_integrity/test_subroutine.py` tidak melihatnya: ia memeriksa
`m.halted` — atribut yang diciptakan cacat itu sendiri — dan programnya
menaruh `HALT` tepat sesudah `RET`. Sesudah perbaikan, keenam program pustaka
yang dijalankan sendirian berhenti di `RET` pertamanya sebagai `fault`, dan
model kehilangan **412 dari 1.890 edge** — semuanya buatan mesin yang terus
berjalan menembus setiap fungsi sesudahnya.

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

**Tujuan.** Membuktikan Python = interpreter = RTL = papan untuk operasi yang
sama, dan kalau berbeda: di langkah berapa, register mana, memori mana, opcode
mana.

**Aset yang sudah ada — ini lapis terkuat di repositori.** `698dd3e` tiga
mesin sepakat; `44ba928` HVM menjalankan semua opcode RTL;
`tests/test_hisa/test_execution_parity.py` dengan `rtl/tb/tb_parity.v`
membandingkan keadaan akhir 41 program; `rtl/scripts/jamrah_board.py`,
`rtl/scripts/hijrah_board.py`, `rtl/scripts/kabah_board.py` masing-masing
membandingkan papan dengan Python dan **sudah menemukan beda**.

**Sejak 21 September 2026 lapis ini berdiri**, tanpa mesin baru:
`src/hijaiyyah/nui/parity_model.py` menjalankan kata yang sama di interpreter
(lewat perekam Lapis 3) dan di RTL (lewat `rtl/tb/tb_parity.v`, yang mendapat
mode `+TRACE` — hanya membaca sinyal yang sudah ada, keluaran bawaannya tidak
berubah), lalu membaca catatan papan. Hasilnya `NUI/parity_model.json`, ditarik
ke [`PARITY.md`](PARITY.md), dijaga `tests/test_ai/test_nui_parity.py` (19).
Korpus 41 program paritas dipindah ke `src/hijaiyyah/hisa/parity_programs.py`
supaya tes lama dan lapis ini memakai satu korpus (R1).

- **107 lari** — 41 program paritas, 62 program HASM, tangga `PRINT`
  2⁰–2³¹, dan tiga probe berhenti. Interpreter ↔ RTL: **70 PARITY,
  30 MISMATCH, 7 UNKNOWN**. Yang
  UNKNOWN tidak berhenti dan dibandingkan sejauh keduanya berjalan
  (5.000 langkah interpreter).
- **Ke-30 MISMATCH semuanya menunjuk langkah, register, dan opcode-nya**, dan
  terbagi lima:
  - 10 — instruksi tepat sesudah `HALT` (7) atau sesudah `RET` yang
    menghentikan mesin sebagai HC-05 (3) **ikut menulis register di RTL**,
    sesudah interpreter berhenti. Sebelum berhenti tidak ada satu pun selisih.
    `subroutine.hasm`: interpreter R1 = 3, RTL R1 = 10 (3 + `ADDI` 7 sesudah
    `HALT`). Temuan baru; tercatat di `cosmictera-build/OFF.md`.
  - 3 — probe berhenti, satu kata di belakang penghenti, untuk jenis yang
    kesepuluh program itu tidak punya: `STORE` sesudah `HALT` menulis
    `MEM[0x100] = 5`, dan `PRINT` sesudah `HALT` atau sesudah `RET` HC-05
    mengirim byte `'5'` ke kabel. Yang terakhir itulah yang membuat cacat ini
    **terlihat di papan**.
  - 8 — langkahnya membaca `COUNTER`: interpreter menghitung instruksi, RTL
    menghitung clock. Dibebankan ke register itu, bukan ke `LOAD`.
  - 7 — langkahnya membaca `SD_STATUS`: tanpa kartu interpreter membaca 0,
    RTL membaca 1.
  - 2 — HCHECK berkala interpreter menghentikan `hfs_lifecycle` dan
    `hos_demo`; RTL tidak.
- **Opcode, kolom RTL**: 78 PARITY; `HALT` dan `RET` MISMATCH; `EMITS`,
  `POP`, `HALT_ERR` tanpa eksekusi yang disepakati kedua mesin; 21 tidak ada
  di RTL. `TRAP` punya baris sendiri dan ditandai bukan opcode.
- **Python**: empat opcode punya fungsi buku yang tidak dipanggil interpreter,
  dan keempatnya sama pada setiap eksekusi — `HLOAD` 724, `HCADD` 49,
  `HNRM2` 4, `HDIST` 4. Untuk opcode lain Python **adalah** interpreter
  (`src/hijaiyyah/vm` mendelegasikan ke sana), dan model menyebutnya begitu.
- **Papan**, dari catatan sesudah perubahan RTL CPU terakhir (`e4c251e`):
  keluaran `test_bsm`, `test_codex`, `test_cset`, `test_hfs` sama dengan
  interpreter dan RTL. Dari 27 nilai tangga yang tercatat, 24 sama dan 3
  berbeda.

**Dua cacat RTL yang pemilik jadikan target verifikasi Lapis 4.**

- **`PRINT` angka besar — nyata dan terukur, tetapi tidak di RTL sebagaimana
  disimulasikan.** Simulasi mencetak ke-32 nilai tangga persis seperti
  interpreter, termasuk 8.388.608, 33.554.432, dan 2.147.483.648; papan mencetak
  `8388600`, `335544;<`, `2147481?::`. Selisihnya muncul antara RTL yang
  disimulasikan dan silikon.
- **Kartu SD gagal init sesudah rekonfigurasi — tidak bisa jadi baris
  paritas.** Tidak ada mesin lain di sini yang punya kartu atau rekonfigurasi,
  jadi ia dicatat hanya-papan, UNKNOWN.

**Lari papan sudah disiapkan, belum dijalankan** — ia menunggu burn-in, sesuai
urutan pemilik. `src/hijaiyyah/nui/board_parity.py` menentukan apa yang
dikirim dan apa yang harus kembali; `rtl/scripts/parity_board.py` mengirimnya
lewat `loader.hasm` dan menyimpan tangkapan mentah, dan menolak jalan selama
proses burn-in hidup. Dijaga `tests/test_ai/test_nui_board_parity.py` (10).

- **83 dari 107 program akan dikirim.** Yang tidak: 9 menyentuh jendela SD —
  kartunya milik burn-in —, 10 tidak berhenti, dan 5 pustaka berhenti sebagai
  fault HC-05.
- **Register dibaca lewat kabel.** Program yang tidak mencetak apa pun
  mendapat epilog: `HALT` yang benar-benar menghentikannya — diukur, bukan
  dibaca — diganti lompatan ke kode yang mencetak FLAGS, tiap GPR yang ia
  ubah byte demi byte, dan tiap komponen H-register yang ia ubah. Byte tidak
  pernah mencapai OFF-PRINT-SILICON. Tiap epilog dibuktikan di interpreter:
  yang dicetaknya harus persis keadaan saat lompatan.
- **Acuannya interpreter di bawah loader**, dengan HCHECK berkala mati:
  HCHECK itu milik interpreter saja, dan di bawah loader jamnya bergeser
  hingga menghentikan dua program di titik yang tak pernah dihentikan papan.
- **RTL memberi byte yang sama di kabel untuk 76 dari 80 payload**; empat
  sisanya membaca `COUNTER`. Untuk `trap_resume`, RTL mencetak `86 86 27` —
  persis catatan papan di `cosmictera-build/PAPAN.md`.

**Yang belum ada.** Kolom papan per opcode: lari di atas belum dijalankan,
jadi kolom papan masih dari catatan lama, dan hanya lewat keluaran cetak. `loader.hasm`
berpayload tidak dijalankan di RTL: `tb_parity.v` tidak punya masukan UART
maupun port tulis memori instruksi. Tujuh program tidak berhenti dalam
anggaran.

**Cara verifikasi.** Sudah berjalan: `verify()` membangun ulang dan menamai
tiap klaim yang tak terulang. PARITY palsu, nilai register palsu, catatan
papan palsu, dan status opcode palsu merah. Mesinnya sendiri juga disabotase:
interpreter yang menambah satu pada `ADD` dinamai di langkah 2, R3, 308 lawan
307. Tujuh penjaga baru dirusak satu per satu dan ketujuhnya merah.

**Syarat selesai.** Tercapai untuk interpreter ↔ RTL atas korpus ini, dan
untuk papan sejauh catatannya. Kolom papan per opcode menunggu lari papan
yang sudah disiapkan, sesudah burn-in.

---

## Lapis 5 — Integrasi Linux

**Tujuan.** Lapis ini adalah **Ubuntu Linux Layer** (keputusan pemilik,
21 September 2026): NUI mengendalikan dan membaca host nyata. Target awalnya,
dari pemilik:

| wilayah | operasi |
|---|---|
| filesystem | baca, tulis, salin, pindah, hapus berkas |
| proses | `ps`, `top`, `kill` |
| jaringan | `ping`, `curl`, `wget` |
| service | `systemctl`, `journalctl` |
| kontainer | `docker`, `podman` |

**Aset yang sudah ada.** **Tidak ada.** `AGENTS.md` sudah mencatatnya: tidak
ada satu pun sisi host di repositori ini — tidak ada driver, layanan,
pustaka, kontainer, atau aplikasi. Yang ada hanya perkakas serial di
`rtl/scripts/`, dan mesin pengembangannya macOS, bukan Ubuntu.

**Hostnya diputuskan pemilik, 21 September 2026: VM Ubuntu Server 24.04 LTS
ARM64** — terisolasi, tidak menyentuh Mac host, dengan systemd sungguhan,
sehingga `systemctl` dan `journalctl` nyata. Dan tahap pertamanya **hanya
baca**:

| diizinkan | belum diizinkan, sampai seluruh pipeline Lapis 5 tervalidasi |
|---|---|
| read file, `ls`, `find`, `cat`, `ps`, `top`, `ping`, `curl`, `journalctl`, `systemctl status`, `docker ps` | `rm`, `mv`, `kill`, `reboot`, `shutdown`, `systemctl start`, `systemctl stop`, `docker rm`, `docker stop`, `docker exec` |

**Image VM adalah bagian baseline Lapis 5** (pemilik, 22 September 2026):
SHA256-nya diverifikasi sebelum dipakai, checksum-nya disimpan di
dokumentasi, dan versi persisnya dicatat. Yang disiapkan, **belum diunduh**:

| berkas | sumber | ukuran |
|---|---|---|
| `lima-2.2.0-Darwin-arm64.tar.gz`, dengan `SHA256SUMS` | rilis resmi Lima di GitHub, Apache-2.0 | 37,6 MB |
| `ubuntu-24.04-server-cloudimg-arm64.img`, dengan `SHA256SUMS` | cloud-images.ubuntu.com, Ubuntu 24.04 LTS | 591 MB |

**Yang belum ada.** Seluruhnya, mulai dari host itu sendiri: diukur
21 September 2026, mesin ini macOS 26.6.2 arm64 tanpa satu pun perkakas VM
atau kontainer, dan tanpa host SSH yang terdaftar. Memasangnya adalah unduhan
pihak ketiga, dan tiap unduhan butuh izin pemilik atas berkas, sumber, dan
ukurannya. Lapis ini dimulai sesudah langkah papan pasca-burn-in (`AGENTS.md`).

**Cara verifikasi.** Tiap operasi dijalankan di host Ubuntu nyata dan hasilnya
dibaca kembali dari host itu sendiri — prinsip ketiga arahan kelima. Belum
bisa dijalankan: host belum ada.

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
