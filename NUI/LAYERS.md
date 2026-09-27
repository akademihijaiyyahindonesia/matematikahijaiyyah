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

**Peta jangka panjang pemilik, 22 September 2026 — usulan roadmap, bukan
pengganti tabel di atas.** Pesan "sambil menunggu burn-in" menulis peta
*sesudah Lapis 5*:

```
0 Fondasi   1 Program Graph   2 Program Understanding   3 Execution Understanding
4 RTL Parity   5 Ubuntu Host   6 Docker   7 Python Runtime Semantics
8 KV260   9 Universal Semantic Layer (USR)
```

Lapis 0–5-nya sama nomor dan isinya dengan tabel di atas. Lapis 6–9-nya
**bukan penomoran ulang**: Docker, Python Runtime Semantics, KV260, dan USR
tidak ada sebagai lapis di halaman ini, sedangkan pemahaman perangkat keras,
operasi otonom, diagnostik otonom, mesin penalaran, rekayasa, dan komputasi
universal tidak ada di peta itu. Pesan pemilik berikutnya, hari yang sama,
menjawabnya: peta itu *"sebaiknya diperlakukan sebagai proposal roadmap,
bukan overwrite terhadap Layer 0–11 yang sekarang menjadi struktur resmi."*
Tabel dua belas lapis di atas tetap yang berlaku, dan Linux/Ubuntu, Command
Center Docker, serta integrasi KV260 tetap di luar implementasi aktif sampai
urutannya dibuka.

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

Kata kunci multibahasa tahap pertama semula lima, dan *"jangan tambah sampai
pipeline terbukti"*. Tabelnya tinggal di `NUI/spec/hc_kamus.json`, ditampilkan
di [`SEMANTIK.md`](SEMANTIK.md), dengan dua koreksi terukur atas tabel pemilik:
kata kunci HC untuk *function* adalah `fn`, dan `print` maupun `println`
sama-sama fungsi bawaan HC. Sejak pesan ketiga pemilik, 22 September, kamusnya
**empat**: `let`, `println`, `if`, `fn`. `read_file` bukan kata kunci HC dan
tidak masuk tanpa keputusan arsitektur baru; permukaan tiga bahasa `while`
ditahan sampai HC membutuhkannya dan pemilik memutuskannya, walau `while`
sendiri sudah kata kunci HC dalam bahasa Inggris.

**Spesifikasi lapisan semantik, 22 September 2026**, dikerjakan sambil
menunggu burn-in atas permintaan pemilik: USR, kalimat tiga bahasa → USR,
katalog perintah Lapis 5, dan kamus HC beserta aturan token parsernya.
Semuanya JSON di `NUI/spec/`, dibaca `src/hijaiyyah/nui/usr.py` — yang
memvalidasi dan memetakan ke argv tetapi **tidak menjalankan perintah host
apa pun** — dan ditarik ke [`SEMANTIK.md`](SEMANTIK.md). Tiap entri menyebut miliknya:
`ditetapkan` untuk keputusan pemilik, `usulan` untuk usulan yang menunggu.
Diukur untuk aturan token: dari 19 sumber HC di repositori tidak satu pun
menulis dua huruf telanjang berdampingan, jadi membaca deretan huruf sebagai
kata tidak mematahkan apa pun; dan `دالة` memuat `ة`, huruf di luar 28 yang
lexer HC kenal.

**Pesan kedua pemilik hari itu** meminta lima hal tanpa papan, tanpa Lapis 5,
dan tanpa mengubah compiler, dan semuanya ada di halaman yang sama:

- **Contoh pemilik sampai HISA, diukur.** `let angka = 10; let harga = 20;
  println(angka + harga);` dikompilasi compiler HC menjadi lima instruksi yang
  **sama instruksi demi instruksi** dengan HISA yang pemilik tulis tangan, dan
  interpreter mencetak `30`. Langkah Arab → HC tetap terjemahan pemilik, tidak
  dijalankan.
- **USR bergeser, dan yang berlaku yang terakhir.** Kunci medan kini huruf
  besar (`ACTION` … `STATE`), `ubuntu_host` menjadi `Ubuntu`, CONTEXT `HC`,
  ACTION `PRINT`, OBJECT `VALUE`, dan STATE `requested` serta `compiled`
  masuk dari dua contoh pemilik. Bentuk lama ditolak, tidak diterima
  berdampingan. Arti STATE **dikunci pemilik (K-5)**: *keadaan aktual
  OBJECT/TARGET pada saat representasi semantik dibuat, bukan tahap pipeline,
  status compiler, atau riwayat proses* — `present` contoh kanoniknya,
  `requested` dan `compiled` metadata lifecycle/eksekusi. Yang dikunci maknanya,
  bukan kosakatanya: `present` belum jadi nilai STATE sampai kosakata
  dimigrasi.
- **Kamus per konsep**, dalam bentuk pemilik `{KONSEP: {hc, arabic,
  indonesia}}`: VARIABLE dan PRINT milik pemilik, IF dan FUNCTION usulan.
  Diukur: `let` dan `println` sampai HISA; `if` dan `fn` diurai HC tetapi
  ditolak compiler; lexer hari ini memecah tiap kata kunci Arab jadi huruf dan
  membaca tiap kata Indonesia sebagai nama.
- **Registry Hijaiyyah** (`src/hijaiyyah/nui/registry.py`): huruf → operator
  → HC → HISA untuk **28** huruf; angka 29 di pesan pemilik salah ketik, kata
  pemilik sendiri. Operatornya dua yang sudah ada: instruksi
  `H0 <- H0 + v(huruf)` dan muka 5×5 sebagai peta linier, dengan periode yang
  Codex JIM ukur. HC sudah menolak ke-28 huruf sebagai nama variabel.
- **Satu selisih matematis ditandai, tidak diperbaiki**: docstring
  `src/hijaiyyah/core/exomatrix.py` membaca ekor 1 sebagai invertibel,
  sedangkan tujuh huruf berekor 1 punya rank di bawah 5. Ia fakta Lapis 0,
  `nui.tail_one_is_not_invertibility`, dan NUI tidak memakai kalimat itu sebagai
  aturan sampai definisinya dibuktikan.
- **Knowledge base dalam tujuh domain** — enam, ditambah HOST (K-6) — lihat
  Lapis 9.

Prioritasnya bukan bahasa: Lapis 5 lebih dulu, karena NUI harus mampu
mengendalikan sistem nyata sebelum diajak bicara.

**Satu ketidakcocokan kecil di jalur yang akan dipakai arahan ini.**
`src/hijaiyyah/compiler/codegen.py` membagikan register sampai R17, sedangkan
assembler berhenti di R15: program dengan enam belas atau tujuh belas
variabel hidup lolos dikompilasi lalu ditolak assembler dengan keras —
`register R16 is out of range (max R15)`. Tidak ada kompilasi yang diam-diam
salah. Dilaporkan, belum disentuh.

## Yang sudah berjalan hari ini, diukur

`src/hijaiyyah/nui/` berisi **32 modul**; `tests/test_ai/` berisi **479 tes**
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
| `program_index.py` | 62 program HASM, 1.313 fungsi Python, 121 modul Verilog, terurai | `test_nui_program_index.py` (10) |
| `program_graph.py` | `CALL` HASM ke label, instansiasi Verilog ke modul | `test_nui_program_index.py` |
| `program_summary.py` | apa yang dilakukan tiap unit, efek diturunkan dari badannya | `test_nui_program_index.py` |
| `execution_trace.py` | satu lari di interpreter, direkam saat berjalan: sebelum → sesudah tiap langkah | `test_nui_execution.py` (26) |
| `execution_graph.py` | 63 lari, 1.478 edge eksekusi, inventaris UNKNOWN | `test_nui_execution.py` |
| `parity_model.py` | interpreter ↔ RTL ↔ papan per program dan per opcode, selisih pertama dengan langkahnya | `test_nui_parity.py` (25) |
| `board_parity.py` | apa yang dikirim ke papan, jawaban yang dibekukan sebelumnya, dan pembaca rekaman: PARITY/MISMATCH/UNKNOWN per program dan per opcode | `test_nui_board_parity.py` (27) |
| `board_probes.py` | dua eksperimen papan tersendiri: PRINT di silikon, dan kata sesudah HALT atau RET yang gagal | `test_nui_board_parity.py` |
| `layer4_freeze.py` | Lapis 4 dibekukan: bukti P0–P6 dengan hash-nya, status tiap warna, dan laporan selisih final dalam empat kelas, dihitung ulang dari rekaman | `test_nui_layer4_freeze.py` (9) |
| `usr.py` | spesifikasi USR, katalog Lapis 5, kamus HC per konsep, contoh pemilik sampai HISA — divalidasi, tidak dijalankan | `test_nui_usr.py` (43) |
| `layer5.py` | Lapis 5: kolektor, pagar hanya-baca, satu jalan keluar lewat `limactl`, dan `record()` yang menulis evidence store di luar repositori, di namespace tiap VM (K-16); kesegaran menurut aturan eksplisit, dan delta antar-run — dijalankan pertama kali 26 September 2026 (P8.4) | `test_nui_layer5.py` (63) |
| `hardware.py` | inventaris hardware Lapis 6.1: tiap butir MEASURED, SIMULATED, atau UNKNOWN, dibaca dari bukti yang sudah ada dengan sumber dan hash-nya | `test_nui_hardware.py` (13) |
| `layer5_freeze.py` | Lapis 5 dibekukan: baseline utama sebelas kolektor, aturan kesegaran, delta ke run berikutnya, dan riwayat P8 — pointer dan hash saja, isinya tetap di evidence store | `test_nui_layer5_freeze.py` (10) |
| `registry.py` | registry Hijaiyyah: 28 huruf → operator → HC → HISA, tiap kolom dibaca dari tempatnya | `test_nui_registry.py` (7) |
| `off_db.py` | `cosmictera-build/OFF.md` dibaca jadi rekaman, bukan ditulis tangan | `test_nui_knowledge.py` (102) |
| `knowledge.py` | apa yang diketahui tentang opcode, program, butir OFF, huruf, kata kunci HC, istilah, berkas, modul RTL, papan terakhir, host — dalam tujuh domain, HOST hanya dari observasi terverifikasi dan tidak pernah dari `facts/`, tiap butir bersumber, dan kontrak kueri tujuh pertanyaan pemilik | `test_nui_knowledge.py` |

---

## Lapis 0 — Pengetahuan terverifikasi

**Tujuan.** Basis fakta yang tiap butirnya punya sumber, bukti, dan cara
verifikasi.

**Aset yang sudah ada.** `facts/` — 27 fakta di tujuh domain — dimuat dan
diperiksa `src/hijaiyyah/nui/facts.py`, dijaga
`tests/test_integrity/test_facts.py`. Sumber lamanya tetap:
`src/hijaiyyah/core/master_table.py` (tersegel),
`src/hijaiyyah/core/guards.py`, `src/hijaiyyah/core/exomatrix.py`,
`src/hijaiyyah/crypto/cube.py`, `docs/HISA_SPEC.md`,
`cosmictera/TELEMETRY.md`, `src/hijaiyyah/nui/claims.py`,
`src/hijaiyyah/nui/atom.py`.

Dari 27 fakta: **10 dihitung ulang** tiap kali tes berjalan, **9 dibuktikan
sebuah tes**, **8 diukur di papan** dan ditandai tidak bisa diulang tanpa
perangkat kerasnya. Lima dari yang diukur di papan datang dari burn-in
tingkat 1 yang tutup 21 September. Yang ke-27, 22 September, adalah sebuah
selisih yang diketahui, bukan aturan: ekor 1 atas GF(2) bukan invertibilitas
(`nui.tail_one_is_not_invertibility`).

**Yang belum ada.** Cakupan — 27 fakta permulaan, bukan seluruh yang terukur
di repo ini. Sisi bertanya kini ada: basis ini ditanyai per objek lewat
`src/hijaiyyah/nui/knowledge.py` (Lapis 9).

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
*references*, dan sekarang keduanya ada: 97 dokumen yang **git lacak** (edge
`references`, tidak pernah dihitung sebagai import) dan 864 definisi tingkat
atas di `src/` (edge `defines`). Graf kini **1.529 node, 4.007 edge**.

**Angka 745 yang dulu tertulis di sini salah.** Ia hasil `find` di disk, yang
ikut menghitung folder pribadi yang tak pernah di-commit. Repositori memuat
**93** berkas Markdown; sumbernya sekarang `git ls-files`, dan satu tes gagal
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
`src/hijaiyyah/nui/program_index.py` (62 program HASM, 1.313 fungsi Python,
121 modul Verilog), `src/hijaiyyah/nui/program_graph.py` (277 `CALL` dan 126
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
ke [`PARITY.md`](PARITY.md), dijaga `tests/test_ai/test_nui_parity.py` (25).
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
proses burn-in hidup. Urutan hari Kamisnya di
`cosmictera-build/PASCA-BURN-IN.md`. Dijaga
`tests/test_ai/test_nui_board_parity.py` (27).

- **Tiga eksperimen, bukan satu** (pemilik, 22 September 2026): paritas
  korpus, PRINT di silikon, dan kata sesudah berhenti — masing-masing lari
  dan rekamannya sendiri, supaya cacat yang satu tidak terbaca sebagai yang
  lain. Tangga PRINT dan probe berhenti tinggal di
  `src/hijaiyyah/nui/board_probes.py`.
- **79 dari 103 program korpus akan dikirim.** Yang tidak: 9 menyentuh jendela
  SD — tak ada mesin lain di sini yang punya kartu untuk pembanding — dan 15
  tidak berhenti di bawah loader.
- **Jawaban yang diharapkan dibekukan sebelum papan ditanya**, di
  `NUI/board_expected.json`: teks interpreter di bawah loader, dan kedua mesin
  pada payload yang sama di alamat 64. Runner menolak payload yang hash-nya
  tidak sama dengan yang dibekukan.
- **Pembacanya kini ada.** Docstring runner dulu menyatakan
  `parity_model.py` membaca rekaman papan terbaru, dan tidak ada kode yang
  melakukannya. Sekarang `classify()` memberi tiap program PARITY, MISMATCH,
  atau UNKNOWN beserta sebabnya, dan `opcode_column()` menggulungnya jadi
  kolom papan per opcode.
- **Register dibaca lewat kabel.** Program yang tidak mencetak apa pun
  mendapat epilog: `HALT` yang benar-benar menghentikannya — diukur, bukan
  dibaca — diganti lompatan ke kode yang mencetak FLAGS, tiap GPR yang ia
  ubah byte demi byte, dan tiap komponen H-register yang ia ubah. Byte tidak
  pernah mencapai OFF-PRINT-SILICON. Tiap epilog dibuktikan di interpreter:
  yang dicetaknya harus persis keadaan saat lompatan.
- **Acuannya interpreter di bawah loader**, dengan HCHECK berkala mati:
  HCHECK itu milik interpreter saja, dan di bawah loader jamnya bergeser
  hingga menghentikan dua program di titik yang tak pernah dihentikan papan.
- **RTL memberi byte yang sama di kabel untuk 75 dari 79 payload korpus**,
  dibandingkan dengan interpreter pada konteks yang sama — alamat 64 di
  belakang NOP; empat sisanya membaca `COUNTER`. Konteks loader mengubah yang
  dicetak 47 program — FLAGS dan register yang ia tinggalkan — jadi teks
  interpreter di bawah loader tidak dibandingkan dengan RTL. Untuk
  `trap_resume`, RTL mencetak `86 86 27`, persis catatan papan di
  `cosmictera-build/PAPAN.md`.
- **Probe berhenti di RTL tersimulasi menjawab ya untuk keempat pertanyaan
  pemilik**: R1 = 7 sesudah HALT dan sesudah RET gagal, `MEM[0x100]` = 5
  sesudah HALT, dan `5` di kabel sesudah RET gagal dan sesudah HALT.
  Interpreter berhenti di semuanya. Papan hanya bisa menjawab yang lewat
  kabel.

**Yang belum ada.** Kolom papan per opcode: pembacanya siap, larinya belum
dijalankan, jadi kolom papan masih dari catatan lama, dan hanya lewat keluaran
cetak. `loader.hasm`
berpayload tidak dijalankan di RTL: `tb_parity.v` tidak punya masukan UART
maupun port tulis memori instruksi. Tujuh program tidak berhenti dalam
anggaran.

**Cara verifikasi.** Sudah berjalan: `verify()` membangun ulang dan menamai
tiap klaim yang tak terulang. PARITY palsu, nilai register palsu, catatan
papan palsu, dan status opcode palsu merah. Mesinnya sendiri juga disabotase:
interpreter yang menambah satu pada `ADD` dinamai di langkah 2, R3, 308 lawan
307. Tujuh penjaga baru dirusak satu per satu dan ketujuhnya merah.

**Syarat selesai.** Tercapai, dan **dibekukan 26 September 2026** dengan tag
`layer4-freeze-2026-09-26` (P7). Bukan karena semuanya hijau: tiap warna —
PARITY, MISMATCH, UNKNOWN — punya sumber dan alasan yang bisa diaudit. Laporan
selisih finalnya di `NUI/LAYER4.md`, dihitung ulang dari rekaman P0–P6 oleh
`src/hijaiyyah/nui/layer4_freeze.py`, dalam empat kelas pemilik: selisih
terukur, beda semantik yang diketahui, UNKNOWN atau tidak teramati, dan selisih
alat — yang terakhir tidak pernah dicampur dengan perangkat keras. Rekaman
buktinya dijaga hash-nya selamanya; vonisnya atas rekaman beku tidak boleh
berubah.

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

**Aset yang sudah ada.** **Tidak ada** sebagai integrasi kendali: NUI kini
membaca host lewat observasi terverifikasi (P8.4, P8.5), tetapi belum
mengendalikannya — tahap pertamanya memang hanya baca. Host-nya ada sejak
26 September 2026 — instance uji `cosmictera-layer5-uji`, di luar repositori,
dengan isolasinya terbukti (P8.1–P8.3, di bawah). Kerangkanya ada sejak
22 September 2026, disiapkan atas permintaan pemilik sementara papan memikul
burn-in, tanpa host:

- `NUI/spec/layer5_collectors.json` — sebelas kolektor observasi: identitas
  host, proses, mount, isi `/`, systemd, jurnal, antarmuka, link, rute, pencacah
  jaringan, kontainer. Lima milik pemilik — dua dari katalog, tiga bentuk `ip`
  K-4 — dan enam usulan.
- `src/hijaiyyah/nui/layer5.py` — pagar hanya-baca yang menolak perintah di
  luar daftar izin, argumen yang bisa dibaca shell, opsi yang menulis atau
  mengirim, dan perintah yang tidak berhenti sendiri; dan satu jalan keluar,
  `limactl shell <instance> -- <argv>`, yang menolak selama `limactl` belum
  terpasang. Lima dipasang lewat Homebrew, state-nya di
  `LIMA_HOME=~/cosmictera-layer5/lima-home`, instance `cosmictera-layer5`
  (pemilik, 22 September 2026, K-3). Instance uji sekali pakainya
  `cosmictera-layer5-uji` (K-9): jalurnya dibuktikan di sana lebih dulu, dan
  `cosmictera-layer5` baru jadi instance utama sesudahnya. Rekaman observasinya
  disimpan **di host, di luar repositori** — satu direktori per sesi di
  `~/cosmictera-layer5/observations/<run_id>/`, dengan `manifest.json` dan
  keluaran mentah per kolektor (pemilik, 23 September 2026, K-11). `observe()`
  mengembalikan rekaman tanpa menulisnya; `record()` menjalankan semua kolektor
  lewat `observe()` sekali dan menulis lari itu ke store, dan menolak store di
  dalam repositori. Dijaga `tests/test_ai/test_nui_layer5.py` (63).
- `NUI/spec/layer5_lima.yaml` — VM yang mengunci image terverifikasi lewat
  digest, tanpa mount, mode plain. Template Ubuntu 24.04 bawaan Lima 2.2.0
  sendiri **tidak bisa dipakai**: ia mengunci `release-20260705`, jatuh ke URL
  "latest" tanpa digest, dan memasang home Mac ke dalam tamu.

**Hostnya diputuskan pemilik, 21 September 2026: VM Ubuntu Server 24.04 LTS
ARM64** — terisolasi, tidak menyentuh Mac host, dengan systemd sungguhan,
sehingga `systemctl` dan `journalctl` nyata. Dan tahap pertamanya **hanya
baca**:

| diizinkan | belum diizinkan, sampai seluruh pipeline Lapis 5 tervalidasi |
|---|---|
| read file, `ls`, `find`, `cat`, `ps`, `top`, `ping`, `curl`, `journalctl`, `systemctl status`, `docker ps`, `ip` | `rm`, `mv`, `kill`, `reboot`, `shutdown`, `systemctl start`, `systemctl stop`, `docker rm`, `docker stop`, `docker exec` |

**`journalctl` dan `ip` hanya dalam bentuk terbatas** (pemilik, 22 September
2026, K-4): `journalctl -b -n 200 --no-pager` dan `journalctl -b -u <service> -n
200 --no-pager`; `ip -brief addr`, `ip link`, `ip route`. Bukan `ip addr add/del`,
`ip link set`, atau `ip route add/del/replace` — Lapis 5 observasi dulu, bukan
kendali jaringan. Bentuk persisnya tinggal di `NUI/spec/layer5_collectors.json`,
dan pagar mencocokkan argv utuh.

**Image VM adalah bagian baseline Lapis 5** (pemilik, 22 September 2026):
SHA256-nya diverifikasi sebelum dipakai, checksum-nya disimpan di
dokumentasi, dan versi persisnya dicatat. **Diunduh 22 September 2026**, atas
izin pemilik hari itu, ke `~/cosmictera-layer5/downloads/` — di luar
repositori, karena repositori ini publik dan image-nya 591 MiB. **Dipakai
26 September 2026** oleh instance uji (P8.2), sesudah diukur ulang hari itu:
masih `7b682958…`.

| berkas | versi persis dan sumber | byte | SHA256 |
|---|---|---:|---|
| `lima-2.2.0-Darwin-arm64.tar.gz` | Lima v2.2.0, rilis resmi github.com/lima-vm/lima, Apache-2.0 | 37.586.365 | `bbdef91774885a0d05f7b048c4eb89ae2bcf3a0c252ae7ca7934e63df76d93c3` |
| `ubuntu-24.04-server-cloudimg-arm64.img` | Ubuntu 24.04 LTS, seri `release-20260911`, cloud-images.ubuntu.com/releases/noble/release-20260911/ | 619.621.888 | `7b682958a67ff5de068e36de6af8b75fa645d296af5a70d6500527f6a33781db` |
| `lima--2.2.0.arm64_tahoe.bottle.tar.gz` | Lima 2.2.0 dari Homebrew, `homebrew/core`, tanpa dependensi runtime — **yang terpasang**, 26 September 2026 | 37.584.563 | `9dfb60d4c7d0c6721eee679ab188d8b502ad61d1063c9914b830b66ce795b4a4` |

Dua baris pertama **cocok** dengan `SHA256SUMS` resmi rilisnya masing-masing.
**Sejak K-3, tarball Lima di baris pertama bukan yang terpasang**: Lima
dipasang lewat Homebrew, dan baris ketiga adalah bottle yang benar-benar
dituang — sha256-nya diukur dari berkasnya dan sama dengan yang
`brew info --json=v2 lima` sebut untuk `arm64_tahoe`, versi yang sama, 2.2.0.
Dipasang tanpa auto-update, jadi yang terpasang persis formula yang diukur
sebelumnya. Baris tarball tetap sebagai catatan unduhan. Berkas
`SHA256SUMS` Lima sendiri bernilai `7da5160e…97312a5f`, sama dengan yang
ditampilkan halaman rilis GitHub; milik Ubuntu `89be81c6…0747b0185`. Yang
**tidak** diverifikasi: tanda tangan GPG kedua berkas checksum itu
(`SHA256SUMS.asc`, `SHA256SUMS.gpg`) — butuh kunci penandatangannya, unduhan
lain. Jadi yang terbukti adalah berkas utuh sesuai yang diumumkan server,
bukan bahwa server itu sendiri asli.

**Host uji, 26 September 2026 — P8.1 sampai P8.3.** Atas izin pemilik hari
itu. Rekaman mentahnya bukti runtime dan tinggal di evidence store K-11, di
luar repositori; yang dicatat di sini hanya vonis dan hash-nya.

- **P8.1.** Lima terpasang (baris ketiga tabel di atas);
  `LIMA_HOME=~/cosmictera-layer5/lima-home` dan
  `~/cosmictera-layer5/observations/` dibuat, keduanya di luar repositori.
- **P8.2 — image lokal.** Lima menerima berkas lokal lewat digest-nya —
  "Downloaded the image from `~/cosmictera-layer5/downloads/…`", tanpa satu URL
  pun di lognya — dan menjawab pertanyaan yang ditinggalkan komentar
  `NUI/spec/layer5_lima.yaml` sendiri. `lima.yaml` di instance **identik
  byte-per-byte** dengan berkas repo (`84849c1e…`). VM `vz`, `aarch64`, 4 CPU,
  4 GiB; dari dalam tamu: `Ubuntu 24.04.5 LTS`, `aarch64`.
- **P8.3 — isolasi**, `observations/20260926T013117Z-isolation/`. Ke-25 mount
  di `/proc/mounts`, `findmnt`, dan `mount` dipilah: 3 disk tamu sendiri, 1 ISO
  cloud-init Lima yang read-only (`/dev/vdb`, 348 sektor = 178.176 byte =
  `cidata.iso` instance), 21 filesystem kernel atau virtual. Tidak satu pun
  virtiofs, 9p, sshfs, nfs, cifs, atau fuse; `/Users` dan `/Volumes` tidak ada
  di tamu; konfigurasi efektif Lima tidak punya medan `mounts` sama sekali dan
  `plain` bernilai true. Kriteria pemilik: Ubuntu PASS, ARM64 PASS, mount home
  Mac ABSENT, filesystem host bersama ABSENT, mount folder host otomatis ABSENT.
- **P8.3 — uji negatif digest**, `observations/20260926T013234Z-digest-negative/`,
  instance sekali pakai `cosmictera-layer5-digest-uji` (nama dari pemilik).
  Satu digit digest diubah, `7b68…` → `8b68…`, tidak ada perubahan lain, dan
  image-nya tidak disentuh. Lima menolak — `expected digest sha256:8b68…, got
  sha256:7b68…`, exit 1 dalam 0,57 detik — instance-nya Stopped dan tidak
  pernah Running, direktorinya tanpa disk, image, maupun cidata. Sesudah
  buktinya disimpan, instance itu dihapus.
- **P8.4 — sebelas kolektor**, `observations/20260926T053008Z-collectors/`,
  lewat `record()`, argv persis yang terkunci dan tiap satunya lolos pagar.
  **Sembilan exit 0.** `journal` **exit 1**, stdout kosong: "No journal files
  were opened due to insufficient permissions" — pengguna tamu `lima` bukan
  anggota `adm` atau `systemd-journal`, dan membukanya butuh `sudo` atau
  mengubah grup tamu, keduanya di luar pagar hanya-baca. Itu failure yang
  didokumentasikan, tidak ditambal; jalan keluarnya keputusan pemilik.
  `containers` **exit 127**, `docker: command not found` — spesifikasinya
  sendiri membaca 127 sebagai tidak ada, bukan galat. `manifest.json`
  (`89829f5c…`) menautkan 11 entri — kolektor, run_id, waktu, VM, argv, exit
  code, durasi — ke 22 berkas evidence, masing-masing dengan path dan
  sha256-nya, dan mencatat sha256 modul dan spesifikasi yang menghasilkannya.
  Stderr `containers` juga menjawab separuh pertanyaan yang tercatat terbuka
  di spesifikasi: `/bin/bash: line 1: …` — argv dijalankan bash tamu sebagai
  satu baris. Cara ia mengutip argumen tetap belum diukur.
- **P8.5 — provenance HOST.** Dua kelas provenance dari pemilik: `facts/`
  pengetahuan rekayasa tersegel yang dibaca NUI, `observations/` bukti runtime
  yang hanya dibaca HOST, dan tes yang menempatkan tiap butir menurut
  sumbernya menjaga keduanya tidak bercampur. `layer5.latest()` mengambil
  observasi terbaru satu kolektor dan **memverifikasinya lebih dulu**: manifest
  dan entrinya menyebut run ini, dan tiap berkas evidence cocok ukuran dan
  sha256 yang tercatat; yang gagal ditolak beserta alasannya, tidak pernah
  dijawab darinya. Tiap butir HOST membawa run_id, kolektor, berkas evidence,
  cap waktu, dan sha256. Keadaannya dibaca dari aturan pemilik di
  spesifikasi (K-12, K-13): 9 `PASS`, `journal` `unavailable_due_to_permissions`
  dengan stderr-nya sebagai provenance, `containers`
  `unavailable_command_absent`. Alasan `unknown` kini "no supporting HOST
  observation" — bukti belum cukup, bukan host belum ada (K-14).
- **Kontrak tujuh kueri dijalankan** atas store nyata: lima dijawab dan satu
  sebagian, seperti sebelumnya, dan `host services` **unknown** — "no
  supporting journal/service observation", karena `journal` tidak bisa membaca
  dan `systemctl status` bukan daftar semua service yang aktif. Dua observasi
  yang diperiksa tampil di HOST beserta provenance-nya. Nol sumber yang hilang,
  dan hash tiap butir HOST cocok dengan berkasnya. `host host_identity`
  dijawab dari observasinya: `Ubuntu 24.04.5 LTS` — dari instance uji, sebelum
  K-16 menetapkan bahwa HOST menjawab untuk instance utama saja.
- **P8.7 — instance utama, 26 September 2026**,
  `observations/20260926T091643Z-isolation/`. Identity check sebelum boot,
  sembilan dari sembilan: digest image `7b682958…`, YAML `84849c1e…` sama
  dengan konfigurasi instance uji, `LIMA_HOME`, ARM64, `mounts: []`, `plain:
  true`, Lima 2.2.0, `validate` OK, dan belum ada instance bernama itu. Boot
  `READY`, exit 0, image dari berkas lokal yang sama. Dari dalam tamu: `Ubuntu
  24.04.5 LTS`, `aarch64`, dan 25 mount dengan pasangan titik mount dan tipe
  yang **persis sama** dengan instance uji — tanpa filesystem host bersama,
  `/Users` dan `/Volumes` tidak ada, konfigurasi efektif tanpa `mounts`.
- **P8.6 — namespace per VM, 27 September 2026.** K-16: identitas kanonik
  observasi adalah `(vm_name, run_id)`. `layer5.latest(collector, vm_name)`
  hanya membaca run milik VM itu — di namespace-nya sendiri,
  `observations/<vm_name>/<run_id>/`, atau run lama berlayout datar yang
  manifest-nya menyebut VM itu; run di namespace sebuah VM yang manifest-nya
  menyebut VM lain ditolak. Run P8.3–P8.7 tidak dipindahkan. K-17: instance
  uji dihentikan, disk dan direktorinya dipertahankan. **Kolektor pertama
  instance utama** — `host_identity` saja, menurut urutan yang terkunci —
  `observations/cosmictera-layer5/20260927T050203Z-collectors/` (manifest
  `0786a762…`): exit 0, 400 byte, sha256 `87458b3b…`. Provenance-nya diperiksa
  sebelum kolektor lain: `host host_identity` dijawab dari run instance utama
  sendiri, instance uji tetap membaca run-nya sendiri, `host services` untuk
  instance utama `unknown` tanpa satu butir bukti instance uji, dan hash run
  yang dibekukan tidak bergerak.
- **Sepuluh kolektor lainnya di instance utama, 27 September 2026**,
  `observations/cosmictera-layer5/20260927T083814Z-collectors/` (manifest
  `cfaa3484…`), dalam urutan kontrak. Instance utama kini punya kesebelasnya:
  9 `PASS`, `journal` `unavailable_due_to_permissions`, `containers`
  `unavailable_command_absent` — sama dengan instance uji, dan izinnya tidak
  diperluas (K-12). Pemeriksaan akhir sebelum apa pun dipensiunkan: 22 berkas
  evidence dalam dua run cocok dengan hash-nya; `latest(…, cosmictera-layer5)`
  mengambil namespace utama untuk kesebelasnya, `latest(…,
  cosmictera-layer5-uji)` tetap mengambil run historisnya; 18 kueri host atas
  instance utama menghasilkan 24 butir HOST, tanpa satu pun dari instance uji.
  `host services` **tidak dipaksa berubah**: `systemd_overview` kini ada di
  instance utama, tetapi ia bukan daftar semua service, dan `journal` yang
  tetap unavailable tidak digantikan — jawabannya tetap "no supporting
  journal/service observation".
- **Instance uji dipensiunkan, 27 September 2026** (K-17): VM dan disknya
  dihapus dengan `limactl delete`. Sebelumnya, berkas kecil di direktorinya —
  `lima.yaml` (`84849c1e…`), log host agent dan serial, `cloud-config.yaml`,
  `cidata.iso` — dan log `limactl start` P8.2 disalin ke namespace-nya sendiri,
  `observations/cosmictera-layer5-uji/20260927T083913Z-retirement/`, beserta
  sha256-nya. Evidence P8.1–P8.5 tidak dipindahkan dan tidak berubah; run
  historisnya tetap terbaca dan terverifikasi tanpa VM-nya. **Lapis 5 masuk
  baseline utama**: `cosmictera-layer5` satu-satunya instance aktif, dan tiap
  kueri HOST berbasis namespace VM yang eksplisit.
- **Penutupan operasional, 27 September 2026** — perintah pemilik, sebelum
  Lapis 6, tanpa kolektor baru:
  - **Baseline utama dibekukan** sebagai snapshot referensi: `host_identity`
    dari `20260927T050203Z`, sepuluh lainnya dari `20260927T083814Z`; `journal`
    dan `containers` tetap apa adanya.
  - **Kesegaran**: tiap butir HOST membawa `observed_at`, `run_id`, `vm_name`,
    `collector`, dan `evidence_sha256`, dan dinilai *known current*, *known but
    stale*, atau *unknown* oleh aturan eksplisit di spesifikasi. Nilai batasnya
    tidak ditebak: ia `null` sampai pemilik menetapkannya pada hari yang sama —
    **`stale_after_seconds` = 300**, satu ambang global tanpa pengecualian per
    kolektor, dan jam yang mundur tetap *stale* sekecil apa pun selisihnya.
  - **Delta antar-run**: `host delta <kolektor>` menyebut butir yang muncul,
    hilang, dan berubah di antara dua run VM yang sama, dengan provenance ke
    kedua run; tidak ada tindakan otomatis. Aturan butir tiap kolektor ada di
    spesifikasi; yang `processes` **dikunci pemilik**: identitas USER + COMMAND,
    dan `kworker` — hanya `kworker`, bukan seluruh kelas thread kernel —
    dikeluarkan dari delta proses utama dan dicatat terpisah sebagai
    `kernel_thread_changes`, tidak dibuang. Yang lain masih usulan. Untuk
    membuktikannya pada data nyata, kesebelas kolektor dijalankan sekali lagi
    (`20260927T095339Z`): dari baseline, delta `processes` **nol** — delapan
    `kworker` yang muncul dan enam yang hilang duduk di `kernel_thread_changes`
    — `root_listing` 2 berubah, `interface_counters` 2 berubah, delapan lainnya
    tetap.
  - **Dibekukan** dengan tag `layer5-freeze-2026-09-27`: `NUI/LAYER5.md` dan
    `NUI/layer5_freeze.json`, dibangun `src/hijaiyyah/nui/layer5_freeze.py`.
    Berbeda dari Lapis 4, yang di-commit hanya pointer dan hash — isi
    observasinya tetap di evidence store (K-11) — dan `--verify` membacanya
    ulang dari sana.

Tiap direktori run menyimpan skrip yang menghasilkannya di sampingnya —
skrip itu tinggal di evidence store, bukan di repositori — sehingga rekamannya
bisa dibaca kembali ke perintahnya.
`NUI/spec/layer5_lima.yaml` sengaja **tidak disunting**, termasuk dua kalimat
komentarnya yang kini sudah terjawab ("Prepared, not started" dan "Not yet
measured"). Menyuntingnya akan mengubah sha256-nya, padahal instance utama
harus dibuat dari byte yang sama yang dibuktikan instance uji.

**Yang belum ada.** Kendali atas host — tahap sesudah hanya-baca, yang belum
dibuka pemilik — dan penguncian aturan butir delta selain `processes`.

**Cara verifikasi.** Tiap operasi dijalankan di host Ubuntu nyata dan hasilnya
dibaca kembali dari host itu sendiri — prinsip ketiga arahan kelima. Host
itu ada sejak P8.2, isolasinya dibaca dari dalam tamu (P8.3), kolektornya
dijalankan di P8.4 dengan tiap berkas evidence dijaga hash di manifest, dan
jawaban HOST diverifikasi terhadap hash itu setiap kali dibaca (P8.5).

**Syarat selesai.** Penutupan operasional pemilik, 27 September 2026:
baseline utama dibekukan, kesegaran dan delta terbukti, lalu laporan, commit,
dan annotated tag `layer5-freeze-2026-09-27`; lalu tiga keputusan pemilik hari
yang sama — batas 300 detik, `kworker` dipisah dari delta proses, dan label EH —
diterapkan, dengan tes dan `layer5_freeze --verify` kembali *reproduced
exactly*. **Lapis 5 selesai.** Kendali atas host tidak termasuk di dalamnya.

**Labelnya sudah diputuskan: AT.** Pesan kedua menandai lapis ini EH; selisih
terhadap definisi `cosmictera/RULES.md` sendiri — EH "terukur, belum
dikriptanalisis" melawan AT "belum dikerjakan" — dilaporkan, dan pesan ketiga
menjawabnya dengan **AT**. Itu label yang cocok dengan tabelnya.

**Label kini EH** — pemilik, 27 September 2026: terukur, belum dikriptanalisis.
Lapis ini kini punya host runtime yang nyata, kolektor, evidence, provenance,
kesegaran, delta, dan baseline yang dibekukan, tetapi bukan pembuktian
menyeluruh atas seluruh perilaku host, dan bukan analisis keamanan. Label itu
untuk lapisnya secara keseluruhan; bukti individualnya tetap dengan statusnya
masing-masing dan tidak dipaksa jadi EH.

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

**Dibuka pemilik 27 September 2026 sebagai *Hardware Intelligence***, sesudah
Lapis 5 final di `80ea5f8` (tag `layer5-freeze-2026-09-27-final`). Empat
langkah: 6.1 inventaris hardware yang sudah terbukti, 6.2 sumber telemetri
yang benar-benar tersedia, 6.3 provenance hardware, 6.4 kueri hardware
pertama. Aturannya: mulai dari bukti hardware yang sudah ada — tanpa menyentuh
RTL atau papan, tanpa sensor, port debug, telemetri baru, atau arsitektur KV260
untuk mengisi kolom kosong — dan pisahkan tegas MEASURED (dibuktikan secara
fisik), SIMULATED (RTL/interpreter), dan UNKNOWN (belum ada jalur observasi).
Lapis 6 tidak berangkat dari asumsi bahwa Lapis 5 sudah memahami perangkat
keras.

**6.1, 27 September 2026 — inventaris hardware**, `NUI/HARDWARE.md`, dibangun
`src/hijaiyyah/nui/hardware.py` dari `NUI/spec/hardware_inventory.json`, yang
hanya menyebut *di mana* tiap nilai dibaca: 19 MEASURED, 11 SIMULATED, 4
UNKNOWN, menjawab kedelapan pertanyaan pemilik. Tiap butir membawa rantai
hardware → bukti → sumber → run → hash: berkas dan rekaman di-hash utuh,
halaman Markdown hanya baris yang dikutip. Semua buktinya sudah di-commit; tak
satu pun dibuat untuk inventaris ini. Yang menonjol: papan `Tang Nano 20K` dan
FPGA `GW2AR-LV18QN88C8/I7` terukur lewat lari papan; clock 27 MHz terukur
lewat hanyutan 8,1 ppm terhadap jam host; 74 opcode terukur di papan dan 29
UNKNOWN; program yang sedang dimuat **UNKNOWN** — tidak ada jalur yang membaca
konfigurasi papan saat ini. Angka sumber daya FPGA (LUT4, DFF, BSRAM, Fmax)
adalah laporan nextpnr, bukan dibaca dari papan, jadi masuk SIMULATED — usulan
kuli, menunggu pemilik.

**Yang belum ada.** Model RTL sebagai fungsi. Yang ada mengurai antarmuka dan
memodelkan dua protokol, bukan perilaku umum. Dari langkah pemilik: 6.2, 6.3,
dan 6.4.

**Cara verifikasi.** 26 testbench di `rtl/tb/` adalah oracle-nya. Untuk
inventarisnya, `python3 -m hijaiyyah.nui.hardware --verify` membacanya ulang
dari buktinya.

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

**Aset yang sudah ada.** **Tidak ada** sebagai penalaran. Yang ada bahannya:
fakta (`facts/`, Lapis 0), relasi (graf Lapis 1 dan graf program Lapis 2),
jejak eksekusi (Lapis 3), dan paritas (Lapis 4).

**Sejak 22 September 2026 ada basis pengetahuannya**, atas permintaan pemilik
sebagai pondasi lapis ini: `src/hijaiyyah/nui/knowledge.py` menjawab *apa
yang diketahui tentang* sebuah opcode, program, butir OFF, huruf, atau kata
kunci HC dengan mengumpulkan yang sudah dipegang lapis-lapis itu, dan setiap
butir jawaban membawa sumbernya. Jawabannya dikelompokkan ke **tujuh domain
pemilik** — HC, HISA, RTL, OFF, PAPAN, NUI, dan HOST sejak K-6 — dan tiap
domain menyebut tempat yang ia baca; sebuah tes menolak butir yang duduk di
domain yang tidak membaca sumbernya. HOST memegang keadaan, proses, service,
jaringan, filesystem, dan runtime host yang diamati, sedangkan OFF tetap fakta
yang tidak bergantung pada host aktif; HOST **hanya membaca observasi** di
evidence store K-11 — tidak pernah `facts/`, yang dibaca NUI — dan tes yang
sama menolak butir yang melintasi batas itu (P8.5, 26 September 2026). Bentuk jawaban pertama pemilik hari itu (`facts`, `tests`,
`board_findings`) masuk ke bentuk kedua: fakta di NUI, catatan papan di PAPAN,
tes tetap di samping domain. Ia **penelusuran, bukan penalaran**: tidak ada
inferensi dan tidak ada skor, dan yang tak bisa dijawab domain mana pun
ditulis di `unknown`. Butir OFF-nya datang dari `src/hijaiyyah/nui/off_db.py`,
yang membaca `cosmictera-build/OFF.md` jadi rekaman (`NUI/off_db.json`) tanpa
menjadi salinan kedua; butir huruf dari registry Hijaiyyah
(`src/hijaiyyah/nui/registry.py`). Dijaga `tests/test_ai/test_nui_knowledge.py`
(102) dan `tests/test_ai/test_nui_registry.py` (7).

**Kontrak kuerinya**, 22 September 2026: tujuh pertanyaan pemilik, kata demi
kata, dipetakan ke jenis kueri di `NUI/spec/query_contract.json` — apa itu
HCPU (`term`), apa yang dilakukan opcode (`opcode`: baris definisinya dan baris
tabel spesifikasinya), berkas ini dari program mana (`file`: medan
`generated_by` berkas itu sendiri, dan relasinya di graf Lapis 1), apa yang
dipanggil program (`program`: tiap `CALL` dengan barisnya), apa yang
diinstansiasi modul RTL (`rtl`), apa yang terakhir diukur papan (`board
latest`: rekaman yang di-commit saja), dan layanan apa yang dijalankan Ubuntu
(`host`: `unknown` — belum ada observasi yang mendukung jawabannya, dan yang
diperiksa tampil di HOST beserta provenance-nya, K-14). Lima dijawab, satu
sebagian — berkas yang tidak menyatakan pembuatnya tidak ditebak — dan satu
unknown karena buktinya belum cukup.
Tiap baris kontrak dijalankan oleh tesnya sendiri.

**Yang belum ada.** Seluruh penalarannya. Lapis ini tidak bisa berdiri sebelum
Lapis 1 punya grafnya dan Lapis 3 punya jejaknya — keduanya kini ada; yang
belum adalah inferensinya.

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
