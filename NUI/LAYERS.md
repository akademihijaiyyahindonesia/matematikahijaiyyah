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

`src/hijaiyyah/nui/` berisi **41 modul**; `tests/test_ai/` berisi **962 tes**
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
| `program_index.py` | 62 program HASM, 1.541 fungsi Python, 128 modul Verilog, terurai | `test_nui_program_index.py` (10) |
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
| `hardware.py` | inventaris hardware Lapis 6.1: tiap butir MEASURED, SIMULATED, atau UNKNOWN, dibaca dari bukti yang sudah ada dengan sumber dan hash-nya | `test_nui_hardware.py` (14) |
| `telemetry_sources.py` | registry sumber telemetri Lapis 6.2: 27 medan kontrak, jenis sumber, historis atau hidup, lari papan, dan hash; batas akses historical / live / simulated / unknown | `test_nui_telemetry_sources.py` (17) |
| `hardware_provenance.py` | provenance hardware Lapis 6.3: tiap klaim 6.1 dan 6.2 jadi satu objek kanonik — jenis sumber, lari papan dan asal identitasnya, bukti, `observed_at`, `evidence_sha256`, status — diperiksa terhadap berkasnya sendiri; keadaan hardware sekarang UNKNOWN | `test_nui_hardware_provenance.py` (40) |
| `hardware_correlation.py` | korelasi hardware Lapis 6.5: hardware ↔ lari papan ↔ program ↔ opcode ↔ keluaran papan, tiap tautan DIRECT, DERIVED, atau UNKNOWN, diperiksa terhadap berkas, kunci, dan hash buktinya; bukti tingkat opcode hanya kolom P3 | `test_nui_hardware_correlation.py` (25) |
| `rtl_function.py` | model RTL sebagai fungsi, Lapis 6: `hcpu_uart_rx`, `hcpu_mmio`, `hcpu_uart_tx`, dan `hcpu_dataram` sebagai fungsi transisi keadaan, dicocokkan per siklus dengan jejak RTL di bawah oracle masing-masing — bench khusus untuk dua yang pertama, `tb_hcpu_top.v` untuk UART TX, `tb_parity.v` atas korpus Lapis 4 untuk RAM data — dan `loader.hasm` di batas baca MMIO-nya di bawah kedua bench loader; satu langkah, keluaran, dan lingkar terbuka — ditambah audit oracle pipeline di bawah `tb_hcpu_top.v`, lalu pipeline sebagai satu fungsi atas keempat bundle registernya, audit oracle integrasi HCPU di bawah bench yang sama, lalu HCPU sebagai satu fungsi atas bagian yang punya oracle, dengan hasil luar dan state opaque dinamai | `test_nui_rtl_function.py` (16), `test_nui_rtl_function_mmio.py` (16), `test_nui_rtl_function_uart_tx.py` (24), `test_nui_rtl_function_dataram.py` (21), `test_nui_rtl_function_loader.py` (19), `test_nui_rtl_function_pipeline_audit.py` (13), `test_nui_rtl_function_pipeline.py` (31), `test_nui_rtl_function_hcpu_audit.py` (25), `test_nui_rtl_function_hcpu.py` (21) |
| `hardware_state.py` | model keadaan hardware Lapis 6.4: IDENTITY, CAPABILITY, OBSERVED, CURRENT untuk tiap klaim dan tiap opcode kolom P3, precedence LIVE > MEASURED > SIMULATED > UNKNOWN, dan kueri CURRENT yang tidak pernah jatuh ke lari historis | `test_nui_hardware_state.py` (29) |
| `layer5_freeze.py` | Lapis 5 dibekukan: baseline utama sebelas kolektor, aturan kesegaran, delta ke run berikutnya, dan riwayat P8 — pointer dan hash saja, isinya tetap di evidence store | `test_nui_layer5_freeze.py` (10) |
| `layer6_freeze.py` | Lapis 6 dibekukan: tujuh bagian cakupan pemilik dengan tiap commit Lapis 6 di tepat satu bagian, hash artefak di commit beku, hasil model HCPU yang diterima, yang tidak diklaim, dan RTL yang tidak berubah — dibaca dari objek git, bukan pohon kerja | `test_nui_layer6_freeze.py` (16) |
| `layer6_addendum.py` | adendum pasca-freeze Lapis 6: catatan beku 6.1–6.3 tetap objek di tag, dan tiap perubahan sesudahnya satu baris — pointer, nilai lama → sekarang, alasan, commit penyebab, dan bukti kesetaraan yang diperiksa dari objek git; ketiga verifiernya membaca catatan beku dan adendum | `test_nui_layer6_addendum.py` (25) |
| `layer7.py` | evaluator Lapis 7, baca-saja: keenam prasyarat 7.6 untuk satu observasi host, keadaan hardware CURRENT, atau satu nama fungsi RTL, tiap yang gagal dengan namanya sendiri — `AMBIGUOUS TARGET` hanya untuk identitas `(vm_name, run_id)`, state opaque dan hasil luar `NOT_COVERED`, ketidaksesuaian HISAB `KNOWN_DISCREPANCY` — lalu PASS atau STOP / REPORT; dan 7.7: `expect()` menetapkan outcome sebelum `layer5.record`, `confirm()` memegang evidence pascatindakan terhadapnya, SUCCESS atau STOP / REPORT; tidak menjalankan perintah dan tidak menulis berkas | `test_nui_layer7.py` (41) |
| `layer7_decision.py` | DECIDE Lapis 7: satu hasil kontrak `layer7.evaluate` atau `layer7.expect` jadi satu decision record deterministik — ALLOW, DENY, atau STOP / REPORT, dengan `record_sha256` dan `verify()`; ALLOW bukan eksekusi, dan tidak ada yang dijalankan | `test_nui_layer7_decision.py` (37) |
| `registry.py` | registry Hijaiyyah: 28 huruf → operator → HC → HISA, tiap kolom dibaca dari tempatnya | `test_nui_registry.py` (7) |
| `off_db.py` | `cosmictera-build/OFF.md` dibaca jadi rekaman, bukan ditulis tangan | `test_nui_knowledge.py` (168) |
| `knowledge.py` | apa yang diketahui tentang opcode, program, butir OFF, huruf, kata kunci HC, istilah, berkas, modul RTL, papan terakhir, host, hardware beserta jenis keadaannya dan korelasinya — dalam tujuh domain, HOST hanya dari observasi terverifikasi dan tidak pernah dari `facts/`, tiap butir bersumber, dan kontrak kueri tujuh pertanyaan pemilik | `test_nui_knowledge.py` |

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
*references*, dan sekarang keduanya ada: 98 dokumen yang **git lacak** (edge
`references`, tidak pernah dihitung sebagai import) dan 875 definisi tingkat
atas di `src/` (edge `defines`). Graf kini **1.828 node, 4.689 edge**.

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
`src/hijaiyyah/nui/program_index.py` (62 program HASM, 1.541 fungsi Python,
128 modul Verilog), `src/hijaiyyah/nui/program_graph.py` (277 `CALL` dan 131
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

**Aset yang sudah ada.** `rtl/` (30 modul HCPU, 13 modul Ka'bah, 39
testbench yang dijalankan `make -C rtl/tb all`), `rtl/fpga/`, `rtl/mpw/`;
`rtl/scripts/lint_hcpu.py`;
`tests/test_integrity/test_board_wiring.py` yang mengurai port Verilog;
`rtl/scripts/rack.py` untuk biaya slot bitstream; dan dua model perangkat
keras yang sudah berjalan di Python — `src/hijaiyyah/nui/sram_mock.py`
(protokol twin-port) dan `src/hijaiyyah/nui/freeze.py` (protokol kabel
loader).

**Dibuka pemilik 27 September 2026.** Judul resmi lapis ini tetap *Pemahaman
perangkat keras* — bagian peta dua belas lapis yang dikunci — dan *Hardware
Intelligence* adalah nama kerja atau aliasnya, bukan penggantian judul
(pemilik, K-19). Dibuka sesudah Lapis 5 final di `80ea5f8` (tag
`layer5-freeze-2026-09-27-final`). Empat
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
adalah hasil synthesis dan place-and-route nextpnr, ditandai
`PNR/build-derived`: kelasnya SIMULATED karena bukan pengukuran fisik, tetapi
**bukan simulasi perilaku** — tanpa kelas keempat (pemilik, K-18).

**6.2, 27 September 2026 — sumber telemetri**, `NUI/TELEMETRY_SOURCES.md`,
dibangun `src/hijaiyyah/nui/telemetry_sources.py`. Inventaris sumber, bukan
modifikasi hardware; dan **sumber yang ada tidak sama dengan sumber yang sedang
mengalir**. Registry 27 medan dibaca dari tabel kontrak `cosmictera/TELEMETRY.md`,
bukan disalin: tiap medan dengan sumber, jenis sumber (program papan, dihitung
host dari rekaman papan, atau lari validasi), historis atau hidup, lari papan,
bukti, dan sha256. Matriks pemilik: 23/27 medan MEASURED dari lari papan lewat
UART, 8 lari papan atau halamannya sebagai bukti historis, **0 sumber hidup** —
tidak ada yang mengalir sekarang — 4 medan tanpa sumber tetap UNKNOWN, dan enam
sinyal `tele_*` di RTL SIMULATED, tersedia di desain tetapi bukan aliran papan
yang hidup, tidak dipetakan ke medan mana pun. Batas aksesnya, `access()`,
membedakan historical board evidence, live board source, simulated RTL
telemetry, dan unknown. Yang ditemukan dan **dilaporkan, tidak diubah**:
`cosmictera/TELEMETRY.md` mengutip `cycle_rate` 649,4 siklus/detik dan `drift`
−3,3 detik, ditulis 20 September saat burn-in tingkat 1 masih berjalan;
baseline yang di-commit memberi median 650,42 dan −3,8 (24 jam) atau −4,3
(72 jam) detik.

**6.3, 27 September 2026 — provenance hardware**, `NUI/HARDWARE_PROVENANCE.md`,
dibangun `src/hijaiyyah/nui/hardware_provenance.py` dari
`NUI/spec/hardware_provenance.json`. Bukan telemetri baru: karena 6.2
membuktikan 0 sumber live, NUI **tidak boleh mengklaim keadaan hardware saat
ini**. Tiap klaim 6.1 dan 6.2 — 34 butir inventaris, 27 medan kontrak, enam
sinyal `tele_*` — ditambah satu pertanyaan pemilik, keadaan hardware sekarang,
jadi satu objek kanonik dalam kosakata Lapis 5: `observed_at` dan
`evidence_sha256`, tanpa `timestamp` atau `sha256` kedua. Jenis sumbernya satu
dari empat yang 6.2 buktikan — historical_board_evidence, live, simulated,
unknown — tanpa kelas baru. Identitas lari papan dibaca dari buktinya sendiri:
`attack_id` atau `run_id` rekaman, nama berkas yang diberi alatnya, atau, untuk
lari yang hanya dicatat halaman, judul bagian yang mencatatnya; bukti papan
tidak diberi `vm_name`, karena (vm_name, run_id) milik bukti VM. **68 klaim:
42 MEASURED, 17 SIMULATED, 9 UNKNOWN, 0 LIVE.** Sepuluh pemeriksaan pemilik,
ditambah objek kanonik dan UNKNOWN yang tetap UNKNOWN, dijalankan terhadap
berkasnya: **65 terverifikasi, 3 belum lengkap**, dan ketiganya dilaporkan,
tidak diisi — HDMI dan reset pin MODE bersandar pada bagian halaman yang tidak
menanggali pengamatan papannya, dan `boot_duration` pada satu baris
`cosmictera-build/CHECKLIST.md` tanpa identitas run dan tanpa tanggal. Kueri
`hardware current-state` menjawab **UNKNOWN — no live hardware telemetry
source**, bukan lari historis terakhir; `hardware FPGA resources` SIMULATED
dengan `PNR/build-derived`; `hardware tele_pc` SIMULATED, bukan telemetri papan
yang hidup. Angka kontrak `cycle_rate` 649,4 dan `drift` −3,3 dicatat di
modelnya sebagai **selisih historis** terhadap baseline, tidak disunting
(pemilik). Satu nama dua peran, **dilaporkan, tidak diganti**: `source_kind`
di registry 6.2 berarti program papan, dihitung host, atau validasi, sedangkan
di 6.3 pemilik menetapkannya empat kelas; objek 6.3 membawa yang pertama
sebagai `evidence_kind`.

**6.3 dinyatakan GREEN oleh pemilik (`08ffbed`)**, dengan tiga penetapan.
Ketiga klaim yang rantainya belum lengkap **tidak diisi dan tidak diturunkan**:
status klaimnya tetap MEASURED dan verifikasi provenance-nya tetap
`incomplete`, dan ketiganya tidak boleh jadi dasar keadaan hardware sekarang.
Identitas run yang hanya berasal dari judul bagian dipertahankan persis seperti
sumbernya dan **ditandai** — medan `run_identity` kini membawa
`non-instrumented/inferred-from-record` untuk 16 klaim itu dan `instrumented`
untuk 25 klaim yang run_id-nya ditulis alat — bukan run ID baru seolah dari
alat. `evidence_kind` sebagai istilah 6.3 tepat, dan registry 6.2 tidak diubah.

**6.4, 27 September 2026 — model keadaan hardware**, `NUI/HARDWARE_STATE.md`,
dibangun `src/hijaiyyah/nui/hardware_state.py` dari
`NUI/spec/hardware_state.json`. Bukan telemetri baru: arti jawaban NUI atas
pertanyaan hardware — kueri → klaim → klasifikasi → semantik keadaan →
provenance. Tiap klaim diberi satu dari empat jenis keadaan pemilik: IDENTITY
(apa perangkatnya, 4), CAPABILITY (apa yang dirancang atau dikonfigurasi, 19 —
17 SIMULATED, dan clock serta UART MEASURED sesudah koreksi taksonomi di bawah),
OBSERVED (apa yang pernah diukur, 145), dan CURRENT (apa
keadaannya sekarang, 3). OBSERVED ikut memuat kolom perangkat keras per opcode
P3 yang dibekukan Lapis 4 — 103 opcode, 79 dijalankan sekurangnya satu program
yang dikirim ke papan dan 24 tidak pernah — masing-masing dibangun dan
diperiksa mesin 6.3 terhadap rekaman P2 yang menghitungnya. **Rekaman papan
historis bukan keadaan sekarang**: kueri CURRENT hanya dijawab sumber live yang
`access()` temukan terdaftar — hari ini tidak ada — dan tanpa itu UNKNOWN, *no
live hardware telemetry source*, apa pun riwayat di belakangnya. Keadaan
jawaban mengikuti satu precedence, LIVE > MEASURED > SIMULATED > UNKNOWN, atas
klaim yang boleh menjawab jenis kueri itu. Kontrak kueri sepuluh baris —
enam contoh pemilik dan empat pagar — dijawab seperti yang ditulis:
`hardware identity HCPU` MEASURED, `hardware capability FPGA resources`
SIMULATED dengan `PNR/build-derived`, `hardware observed opcode PRINT` dan
`hardware observed board clock` MEASURED historis, `hardware current program`
dan `hardware current board clock` UNKNOWN, dan kueri historis yang memuat
ketiga klaim belum lengkap menandainya. **0 LIVE tetap 0 LIVE.** Eksperimen P4
dan P5 tidak digabung ke kueri opcode: pemilik menetapkannya bukti tingkat
program atau eksperimen, bukan tingkat opcode.

**6.4 dinyatakan GREEN oleh pemilik (`d6cfd6c`)**, dengan dua penilaian.
**Koreksi taksonomi**: clock 27 MHz dan UART 115200 secara semantik adalah
CAPABILITY/konfigurasi, bukan IDENTITY. `d6cfd6c` tidak diubah surut — ia
baseline 6.4 yang terverifikasi — dan koreksinya diterapkan sebagai commit
pemeliharaan tersendiri sesudah 6.5 GREEN. Ia sempat ditolak build 6.4 sendiri:
CAPABILITY hanya mengizinkan SIMULATED, sedangkan kedua klaim itu MEASURED
dengan bukti papan. Pemilik memutuskan, 28 September 2026: **CAPABILITY
menerima MEASURED** — konfigurasi yang dibuktikan papan — dan status klaimnya
tetap seperti di 6.1 dan 6.3. Keputusan tidak
menggabungkan P4/P5 ke kueri opcode dinilai benar: kolom P3 adalah bukti
tingkat opcode, P4 dan P5 bukti tingkat program atau eksperimen. **Satu premis
saya dibetulkan**: saya sempat menulis bahwa rekaman P4/P5 menautkan opcode
hanya lewat nama program. Keliru — rekamannya membawa `payload_sha256` yang
sama dengan ekspektasi beku, dan ekspektasi itu mencatat opcode yang interpreter
jalankan untuk payload tersebut, persis cara P3 diturunkan dari P2. Yang
membuat P5 tetap bukan bukti opcode adalah pengukurannya sendiri: silikon
menjalankan PRINT sesudah HALT atau RET fault, yang interpreter tidak pernah
jalankan, jadi opcode turunan interpreter bukan yang papan jalankan.

**6.5, 28 September 2026 — korelasi hardware**, `NUI/HARDWARE_CORRELATION.md`,
dibangun `src/hijaiyyah/nui/hardware_correlation.py` dari
`NUI/spec/hardware_correlation.json`. Bukan telemetri baru: tautan antara
tingkat bukti yang sudah ada — hardware ↔ lari papan ↔ program ↔ opcode, dan
apa yang papan cetak. Tiap tautan satu korelasi berkelas: **DIRECT** bila
tertulis eksplisit di bukti (rekaman lari menyebut program dan hash payload
yang dikirimnya, keluarannya, atau nilai hardware yang sama dengan klaimnya;
atau rantai 6.3), **DERIVED** bila dihitung dari struktur yang ada (opcode yang
interpreter jalankan untuk payload dengan hash yang sama; vonis keluaran
terhadap ekspektasi beku), dan **UNKNOWN** bila tidak bisa dibuktikan, dengan
alasannya. Sepuluh lari dikorelasikan — P2, tiga lari P4, P5, dua burn-in,
capture, lab loader dan Jamrah — dan **1.180 korelasi**: `supports` 104,
`records` 11, `ran` 91 DIRECT dan 2 UNKNOWN, `printed` 88, `judged` 88 DERIVED,
`executes` 795 DERIVED dan 1 UNKNOWN. **Tidak ada tautan karena nama**: rekaman
lab loader dan Jamrah hanya menyebut sasaran, jadi programnya UNKNOWN, dan
`burn_in.hasm` tidak punya ekspektasi beku atas payload-nya, jadi opcode-nya
UNKNOWN. Bukti tingkat opcode tetap kolom P3 saja, dan untuk 79 opcode sama
persis dengan kolomnya; program P4/P5 yang menjalankan PRINT ditampilkan
sebagai tingkat eksperimen, tidak pernah dihitung. Rantai contoh pemilik
berjalan utuh: HCPU (`6.1:cpu`, DIRECT) → lari P2 → `test_hisab.hasm` (DIRECT,
hash payload) → PRINT (DERIVED) → keluaran papan `65824 2586908910` (DIRECT) →
vonis MISMATCH (DERIVED), dengan lari dan hash di tiap langkah. Lari P2
pertama tidak dikorelasikan: program pertamanya tercemar byte burn-in basi,
selisih alat yang Lapis 4 catat.

**6.5 dinyatakan GREEN oleh pemilik (`3617a31`)**, dan tiga hal dikunci: P4/P5
tetap tingkat eksperimen, tetapi korelasi ke programnya sah karena payload-nya
terbukti identik dengan ekspektasi beku; lari P2 `104300Z` tetap dikeluarkan —
jangan dimasukkan lagi hanya karena hasil akhirnya bisa dibaca; dan model
korelasi 19.379 baris jadi baseline 6.5 karena `--verify` menghasilkannya ulang
persis. **Lapis 6 keseluruhan belum selesai.**

**Model RTL sebagai fungsi, 28 September 2026 — modul pertama `hcpu_uart_rx`**,
`NUI/RTL_FUNCTION.md`, dibangun `src/hijaiyyah/nui/rtl_function.py` dari
`NUI/spec/rtl_function.json`. Butir Lapis 6 yang roadmap sudah tetapkan, tanpa
definisi baru; pemilik memilih `rtl/hcpu_uart_rx.v` lebih dulu karena ia punya
bench khusus, `rtl/tb/tb_hcpu_uart_rx.v`, dan bukan `hcpu_top.v`, tempat terlalu
banyak subsistem masuk sekaligus. Modul itu ditulis sebagai fungsi transisi
keadaan — (keadaan t, input t+1) → (keadaan dan keluaran t+1) — cabang demi
cabang dari RTL-nya, 13 aturan dengan baris RTL masing-masing. Ia dipegang pada
jejak yang RTL sendiri hasilkan di bawah bench khususnya: bench dan RTL
dikompilasi apa adanya dengan satu modul probe di sampingnya yang mencetak
register desain di tiap tepi turun clock; **RTL dan bench tidak diubah**.
Satu langkah, 15.915 transisi: 0 berbeda. Lingkar terbuka dari reset, 15.916
siklus: 0 berbeda. Frame yang diprediksi 0x41, 0x00, 0xFF, 0x5A, 0x3C dengan
framing error hanya pada yang terakhir — yang bench periksa — dan bench
mencetak PASS. Ke-13 aturan dijalankan bench; `start_glitch` dua kali: glitch
bench, dan jalur yang masih rendah oleh stop bit buruk. Satu fakta bench
diukur, tidak diasumsikan: bench mengubah `line` di region aktif yang sama
dengan tepi tempat desain menyampelnya, dan di ke-24 perubahan simulator
memberi flop nilai baru — jadi input langkah t→t+1 adalah `line` sesudah tepi
t+1. Enam sabotase aturan transisi merah, dan lima sabotase pada berkas nyata
(modul, spec, model) merah.

**Modul kedua, 28 September 2026 — `hcpu_mmio` (peta memori).** Urutan
pemilik untuk sisa butir ini: UART RX, peta memori, UART TX, `hcpu_dataram`/SRAM
(oracle-nya perlu ditetapkan), loader, pipeline, lalu HCPU sebagai sistem
penuh. `rtl/hcpu_mmio.v` dimodelkan bersama timer yang ia miliki dan penerima
yang dijalankan lewat fungsi UART RX yang sudah terbukti; pengendali kartu, RAM
data, dan unit trap **di luar model** — keluarannya masuk sebagai input, tidak
diprediksi. Dipegang pada bench khususnya, `rtl/tb/tb_hcpu_mmio.v`: satu
langkah 7.757 transisi 0 berbeda, keluaran kombinasional 7.758 siklus 0
berbeda, lingkar terbuka dari reset 0 berbeda, dan kesembilan baca yang bench
periksa terprediksi — RAM di 0x010, compare, pencacah yang maju, ready yang
naik lalu turun karena dibaca, byte 0x41, dan overrun — tanpa satu pun tulis
RAM di jendela periferal. Yang bench tidak pernah jalankan **dinamai, tidak
diklaim**: jendela proteksi, port tulis memori instruksi, seluruh blok kartu,
register trap, status pengirim, dan akses tak terpetakan — 19 aturan, tiap
satunya dengan alasannya di spec. Satu pelajaran pengambilan sampel, dicatat:
sampel 7 ns sesudah tepi naik terbukti salah pada dua perubahan jalur yang
bench lakukan sesudah tepi turun; dicetak `$strobe` di akhir timestep tepi
naik, baris memegang persis yang tepi itu ambil, 18 dari 18.

**Modul ketiga, 28 September 2026 — `hcpu_uart_tx`, dengan oracle
`rtl/tb/tb_hcpu_top.v`.** Pemilik menetapkan bench top-level sebagai oracle-nya
dan membatasi klaim pada perilaku TX yang bench itu benar-benar jalankan dan
amati: bench top-level yang melewati modul itu tidak membuat aturannya
terbukti. Diukur sebelum model ditulis: kesebelas program bench tidak
menjalankan `PRINT` atau `EMITS`. Jadi di ke-233 tepi naik `tx_start` 0,
pemancar tidak pernah meninggalkan S_IDLE, pencacah bit tidak pernah bergerak,
`tx_busy` 0, dan pin `uart_tx` 1. Bench juga tidak membaca apa pun dari
pemancar — `uart_tx` hanya dideklarasikan dan disambung — dan `uart_busy` masuk
ke `hcpu_controller` tanpa dipakai. Yang terbukti karena itu hanya `reset` dan
`idle_wait`: satu langkah 232 transisi, keluaran (`tx_busy` dan pin) 233
siklus, dan lingkar terbuka dari reset, semuanya 0 berbeda, dan bench mencetak
`Total: 15 PASS, 0 FAIL`. Start bit, bit data, stop bit, waktu bit, dan busy —
sembilan aturan — ditulis di fungsi cabang demi cabang dan **dinamai tidak
tercakup**. Batas yang tercakup ikut dinamai: reset hanya pernah dijalankan atas
nilai reset-nya sendiri, dan jalur diam tinggi hanya pernah dipertahankan,
tidak dipulihkan. R3 menunjukkan kedua sisi: sabotase atas aturan yang tercakup
merah, sedangkan sabotase atas aturan yang tidak tercakup — start bit dikirim
tinggi, bit data MSB lebih dulu, satu clock kurang per bit, stop bit rendah —
**tetap tak terlihat**, tepat karena bench tidak menjalankannya.

**Modul keempat, 28 September 2026 — `hcpu_dataram`, dengan oracle
`rtl/tb/tb_parity.v` atas korpus Lapis 4.** Tidak ada bench RAM khusus, dan
tidak ada yang dibuat. Pemilik meminta oracle ditetapkan lebih dulu atas tiga
level — model perangkat lunak, jalur RAM RTL, bukti papan — dan pengukurannya:
`src/hijaiyyah/nui/sram_mock.py` memodelkan makro sky130, perangkat lain yang
oracle-nya tidak di-commit, jadi bukan oracle modul ini; bench yang sudah
dipakai hampir tidak menyentuh RAM (`rtl/tb/tb_hcpu_mmio.v` 1 tulis dan 2 baca,
`rtl/tb/tb_hcpu_top.v` 2 tulis dan 2 baca). Pemilik memilih harness paritas
atas korpus Lapis 4 — jalur `hcpu_top.u_dataram` yang sama dengan yang di papan
jadi BSRAM — dan harness, korpus, serta model paritas beku hanya dibaca.
Hasilnya: 107 lari, 826.030 siklus, 20 program menyentuh RAM; satu langkah,
keluaran, dan lingkar terbuka — termasuk isi RAM utuh di akhir tiap lari —
semuanya 0 berbeda, dan jejak tulis RAM harness sama dengan 26.578 tulisan yang
fungsi ambil. Satu aturan **tidak tercakup**: read-first — baca dan tulis di
tepi yang sama tidak pernah terjadi di korpus, dan sabotasenya tetap tak
terlihat. Nol awal RAM terbukti untuk simulasi saja, karena blok `initial`-nya
dibuang sintesis. Vonis Lapis 4 yang beku dikutip, tidak dinilai ulang:
satu-satunya perpisahan pertama berjenis RAM adalah `stop-probe:halt-then-store`
— tulisan sesudah `HALT` yang sampai ke port dari pipeline, dan RAM
menyimpannya persis seperti yang fungsi ramalkan. Bukti papan tetap tingkat
program: `LOAD` dan `STORE` PARITY di kolom P3.

**Butir kelima, 28 September 2026 — `rtl/programs/loader.hasm`, dengan
oracle `rtl/tb/tb_gowin_loader.v` dan `rtl/tb/tb_gowin_loader_nui.v`.** Loader
adalah program, bukan modul, dan RTL tidak membawa PC melewati tahap decode.
Karena itu fungsinya berdiri di batas baca MMIO: di tiap baca RX_STATUS atau
RX_DATA, posisi loader, R1–R7, dan penunjuk tulis memori instruksi semuanya
teramati, dan semua yang terjadi di antara dua baca — tulis GPR, tulis MMIO,
tulis port memori instruksi, `ERET` — dibandingkan dalam urutan program.
Kedua bench diukur sendiri-sendiri, tidak dianggap satu: N = 3 dan N = 48,
5.379 dan 65.688 batas. Hasilnya: 71.065 langkah, satu langkah, kejadian di
antaranya, dan lingkar terbuka dari reset semuanya 0 berbeda, dan 71.063 baca
semuanya membawa `rdata` satu siklus sesudah permintaannya. Cakupan gabungan
sama dengan irisannya — dua belas aturan. Satu jalan **tidak tercakup**:
N = 0, langsung ke `done` tanpa satu kata. Status bukan nol hanya pernah
bernilai 1, jadi bit framing error dan overrun tidak diklaim. Daftar pemilik
— RX_STATUS, RX_DATA, IMEM_ADDR, IMEM_DATA, TRAP_EPC, TRAP_MODE, ERET —
muncul di jejak RTL sendiri dengan urutan itu, dan alamat masuk 64 **tidak
pernah diambil fetch sebelum `ERET`** di kedua bench: satu-satunya `JMP`
loader adalah gelung terimanya. Sasaran dan mode sesudah `ERET` milik unit
trap, diamati, tidak diprediksi. Satu hal yang terlihat di sini dan tidak
mengubah modul lain: `imem_addr_write` dan `imem_data_advance` milik
`rtl/hcpu_mmio.v`, yang tidak tercakup bench MMIO sendiri, berjalan di bawah
kedua bench loader. Status model MMIO tetap menurut oracle-nya.

**Pipeline, 28 September 2026 — audit oracle dulu, belum model.** Oracle
sistemnya `rtl/tb/tb_hcpu_top.v`, dan tidak ada bench per tahap. Karena itu
pemilik memerintahkan peta cakupan sebelum satu fungsi pun ditulis: keadaan
yang teramati, titik sampel, instruksi yang lewat tiap tahap, transisi yang
dapat diprediksi, dan aturan yang tidak pernah dijalankan. Tidak ada bench
baru, RTL tidak diubah, dan interpreter bukan pengganti oracle. Petanya di
`NUI/RTL_FUNCTION.md`, bagian Pipeline. Tiap tepi dicatat dua kali — yang tepi
ambil dan yang tepi tinggalkan — dan pengukurannya sendiri diperiksa: di 178
tepi hidup, yang diambil tiap tepi sama dengan yang ditinggalkan tepi
sebelumnya. Identitas instruksi di EX/MEM dan MEM/WB, yang tidak membawa PC,
diturunkan dari aturan latch RTL dan cocok dengan `id_pc`, `id_opcode`, dan
`ex_opcode` di setiap tepi. Hasilnya **45 dari 78 transisi** dan **26 dari 53
arm opcode decode** dijalankan kesebelas program. Yang tidak tercakup dinamai
dengan alasannya. Dua di antaranya tidak terjangkau dari kabelnya sendiri:
flush tanpa redirect, dan flush execute yang diikat `1'b0`. Satu temuan
membentuk model nanti: **stall global tidak pernah diambil tepi hidup**.
Bench mereset pada tepi sesudah `halted` naik, jadi pembekuan pipeline saat
berhenti tidak pernah teramati; FLAGS untuk cabang pun selalu datang dari
EX/MEM, tidak pernah dari register.

**Fungsi pipeline, 28 September 2026 — bentuk dari pemilik.** Sesudah audit
diterima (`bd8158c`), pemilik menetapkan bentuknya: **satu fungsi transisi
sinkron atas keempat bundle register tahap**, bukan lima fungsi tahap. Input
`rst_n` dan `imem_data`; hasil ROM, guard, ALU codex, HISAB, unit trap, RAM
dan peta memori diambil dari jejak, tidak diprediksi ulang. Dua keadaan di
luar keempat bundle ikut dimodelkan karena kriteria pemilik sendiri
menuntutnya, dan keduanya dinamai: register file, tujuan port tulis WB yang
dibaca decode dan pemeriksaan terminal, serta `halted`, yang ditulis aturan
tercakup `ctrl_halt_latch`. Hasilnya di bawah `rtl/tb/tb_hcpu_top.v`:
satu langkah dari keadaan RTL 231 tepi transisi, keluaran 232 baris, dan
lingkar terbuka dari reset semuanya 0 berbeda. Fungsi menembakkan tepat 45 aturan
dengan hitungan per aturan sama persis dengan audit. Ke-32 bacaan bench — GPR,
H2[7:0], `guard_led` — sama dengan konstanta yang bench sendiri tulis. Yang di
luar cakupan berhenti dengan `NotCovered`, tidak diprediksi. **Satu fakta baru
dari lari ini**: probe model mencetak baris sesudah tepi terakhir, sesudah
HALT program 11 (bench memanggil `$finish` di situ tanpa reset), sedangkan
probe audit tidak. Di baris itu `halted = 1` dan setiap sinyal tertahan, tetapi
ada tidaknya baris itu bergantung pada urutan `$strobe` terhadap `$finish`.
Pemilik memutuskan (28 September 2026): baris itu **terminal snapshot**,
dicatat dan tidak dipakai sebagai oracle transisi, jadi `ctrl_halted_stall`
tetap not covered; tanpa baris itu hasil lainnya tidak bergeser. Kalimat
alasan audit untuk keempat aturan stall dipersempit sesuai itu, sebagai commit
pemeliharaan tersendiri. Sepuluh reset yang menyusul HALT membiarkan `stack_rd`
tidak diprediksi, karena ia digerbang stall yang sama. Register file adalah
companion state fungsi — diturunkan dari writeback-nya sendiri, bukan input
oracle — keputusan pemilik yang sama.

**HCPU, 28 September 2026 — audit oracle integrasi dulu, belum model.** Sesudah
fungsi pipeline diterima (`bf13941`), pemilik menetapkan langkah berikutnya:
model HCPU tingkat sistem dengan `rtl/tb/tb_hcpu_top.v` sebagai oracle
integrasi, tetapi audit cakupannya lebih dulu, dengan prinsip yang sama seperti
pipeline. Petanya di `NUI/RTL_FUNCTION.md`, bagian HCPU. Bench dan kesebelas
programnya milik audit pipeline, dan probe-nya mencakup setiap subsistem lain.
Di bawah bench itu **input HCPU hanya `rst_n` dan `imem_data`**: `uart_rx`,
`sd_cmd_in`, dan `sd_dat_in` tidak disambung (z), dan `dbg_gpr_raddr` diikat 0.
Titik sampel audit pipeline berlaku untuk setiap sinyal probe di 178 tepi
hidup. **Batas keadaannya 171 register di 21 berkas**, dibaca dari penugasan
non-blocking RTL sendiri, dan cocok persis dengan batas di spec. Tiga hal
dinamai tersendiri: `ra_stack[]`, yang ditulis CALL dan dibaca
RET — keduanya tidak tercakup — dan tidak ada di keadaan fungsi pipeline;
register `pc` di register file, yang `pc_we`-nya diikat 0; dan tujuh register
guard yang tidak dielaborasi karena `PIPELINE_GUARD(0)`. Di luar pipeline,
**47 dari 162 transisi** dijalankan; pipeline sendiri tetap 45 dari 78. Mesin
keadaan cetak, unit trap, penerima UART, pengendali kartu, dan pemancar tidak
pernah meninggalkan keadaan diamnya, bus data membawa empat akses di seluruh
bench, dan 17 register pengendali kartu tanpa reset tetap x di setiap tepi.
Delapan aturan baca MMIO yang tercakup hanyalah register baca yang diperbarui
dari alamat bus tiap siklus: `periph_sel` 0 di setiap tepi, jadi tidak ada baca
MMIO yang terbukti. Pemancar, satu-satunya subsistem lain yang oracle fungsinya
bench yang sama, disepakati kedua derivasi: reset dan diam.

**Fungsi HCPU, 29 September 2026 — bentuk dari pemilik.** Sesudah audit
diterima (`f590bac`), pemilik menetapkan **satu fungsi transisi tingkat
sistem dengan state prediktif parsial**: hanya state yang punya aturan
tercakup dan dapat diverifikasi. Fungsi yang sudah punya oracle sendiri
dikomposisikan apa adanya — pipeline, peta memori dengan penerima UART di
dalamnya, RAM data, dan pemancar, yang terakhir hanya reset dan diam. ALU codex
dan pengali adalah handler interpreter yang sudah ada, dijalankan pada register
sementara, tanpa rumusnya disalin. ROM Master Table, guard, HISAB, unit trap,
mesin keadaan cetak, dan pengendali kartu menjadi hasil luar dari jejak.
`ra_stack[]`, ke-17 register x, dan register yang tidak dielaborasi tetap
opaque, tidak diprediksi, dan tidak diberi nilai. Dua keputusan pemilik yang
lahir dari pengukuran: HISAB tetap hasil luar karena
`src/hijaiyyah/hisab/serialize.py` berbeda dari `rtl/hcpu_hisab.v` di 13 tepi
(0 di tepi yang memakainya), dan urutan bit status guard yang kanonik adalah
urutan RTL dan `src/hijaiyyah/core/guards.py`. `src/hijaiyyah/hisab/protocol.py`
dan sisa `is_kaf` di `rtl/hcpu_hisab.v` tidak disentuh.
Hasilnya di bawah `rtl/tb/tb_hcpu_top.v`: satu langkah dari keadaan RTL 231
tepi, 57 keluaran di tiap baris, dan lingkar terbuka dari reset semuanya 0
berbeda. RAM cocok di 115 kata port dan saat `$finish`, dan ke-32 bacaan
terminal bench sama. Fungsi menjalankan 71 dari 149 aturan, dengan hitungan
per aturan sama persis dengan kedua audit. Hasil ALU yang lebih lebar dari
kabel RTL berhenti dengan `NotCovered`, dan di bench ini tidak pernah terjadi.
**Dinyatakan GREEN oleh pemilik (`1c33e30`)**, tanpa klaim paritas untuk 78
aturan not covered dan ketidaksesuaian HISAB. Keputusan arsitekturnya tidak
dibuka kembali.

**Lapis 6 dibekukan, 29 September 2026.** Keputusan pemilik: definisi selesai
lapis ini — prediksi keadaan berikutnya untuk modul yang dimodelkan cocok dengan
oracle-nya — terpenuhi. Membuka bench trap, kartu, EMITS, ALU, guard, HISAB,
atau ROM sekarang akan memperluas cakupan Lapis 6, bukan menyelesaikan
kewajibannya. Laporannya `NUI/LAYER6.md`, dibangun
`src/hijaiyyah/nui/layer6_freeze.py` dari objek git di `d003cac`, bukan dari
pohon kerja: artefak Lapis 6 semuanya turunan, jadi yang dibekukan adalah
keadaannya di commit itu. Tagnya annotated, `layer6-freeze-2026-09-29-final`, di commit freeze-nya sendiri
(`0a3b446`).
Kedelapan belas commit Lapis 6 masing-masing ada di tepat satu dari tujuh bagian
cakupan pemilik. `git diff 80ea5f8 d003cac -- rtl/` kosong: RTL, bench, dan
sidik jari wrapper tidak berubah sepanjang Lapis 6. HISAB tidak diubah supaya
freeze tampak bersih — urutan bitnya butir tersendiri.

**Adendum pasca-freeze, 1 Oktober 2026.** Commit HMAC `4bff781` menggeser apa
yang dikutip catatan beku 6.1–6.3: hash utuh `rtl/fpga/gowin/hcpu_gowin_top.v`
dan `rtl/fpga/gowin/Makefile`, nomor baris di `rtl/fpga/gowin/hcpu_gowin_top.v`
dan `cosmictera-build/PAPAN.md`, dan hash baris `state_hash` di
`cosmictera/TELEMETRY.md`. Keputusan pemilik: catatan beku tetap immutable, dan
perubahannya catatan baru, `NUI/layer6_addendum.json` — lima entri, 66
perubahan, tiap satunya dengan nilai lama → sekarang, alasan, commit penyebab,
dan bukti kesetaraan yang diperiksa dari objek git. Halamannya
`NUI/LAYER6_ADDENDUM.md`. Ketiga verifier membaca keduanya: **freeze historis ≠
keadaan repositori sekarang**.

**Yang belum ada.** Tidak ada yang tertunda untuk menutup Lapis 6. Yang tidak
diklaim — bukan utang, melainkan batas yang tercatat di `NUI/LAYER6.md`:
- 78 aturan yang kedua audit namai tetap not covered;
- unit trap, mesin keadaan cetak, dan pengendali kartu tidak punya fungsi;
- RAM data tanpa read-first, loader tanpa N = 0, dan UART TX sebatas reset dan
  diam.
Bench khusus yang belum dimodelkan tetap bukti yang tersedia.

**Cara verifikasi.** 39 testbench yang dijalankan `make -C rtl/tb all` adalah
oracle-nya. Untuk
inventarisnya, `python3 -m hijaiyyah.nui.hardware --verify` membacanya ulang
dari buktinya, `python3 -m hijaiyyah.nui.hardware_provenance --verify`
membaca ulang tiap rantai provenance dari berkasnya, dan
`python3 -m hijaiyyah.nui.hardware_state --verify` membangun ulang tiap
klasifikasi dan jawaban kontrak, dan
`python3 -m hijaiyyah.nui.hardware_correlation --verify` membangun ulang tiap
korelasi dan memeriksanya terhadap rekamannya sendiri, dan
`python3 -m hijaiyyah.nui.rtl_function --verify` menjalankan ulang oracle tiap
fungsi RTL — bench khusus, korpus Lapis 4, kedua bench loader, dan
`rtl/tb/tb_hcpu_top.v` untuk pemancar, pipeline, dan HCPU — beserta kedua
audit, lalu membandingkan tiap fungsi per siklus. Freeze-nya dibaca ulang oleh
`python3 -m hijaiyyah.nui.layer6_freeze --verify` dari objek git yang sama. Adendumnya
dibaca ulang oleh `python3 -m hijaiyyah.nui.layer6_addendum --verify`, yang juga
menuntut catatan beku, halaman, dan spec 6.1–6.3 tetap objek di tag.

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

**Dibuka pemilik 29 September 2026**, sesudah Lapis 6 dibekukan (`0a3b446`,
tag `layer6-freeze-2026-09-29-final`). Langkah pertamanya **bukan** membuat
sistem bertindak otonom, melainkan menetapkan **kontrak operasi otonom yang
dapat diukur**, dengan enam unsur:
- apa yang boleh dibaca;
- tindakan apa yang boleh dilakukan;
- batas otorisasi;
- keadaan sebelum dan sesudah tindakan;
- bukti keberhasilan;
- kondisi `UNKNOWN` dan `NOT_COVERED`.
Tujuannya supaya Lapis 7 tidak mengubah NUI menjadi sekadar lingkar otomatis
tanpa guard.

**Kontraknya, 30 September 2026**, ada di `NUI/LAYER7.md`: sebelas bagian dari
pemilik, dengan keenam unsur sebagai struktur resmi. Pada hari yang sama pemilik
mengunci tiga hal:
- definisi operasi otonom (7.2);
- batas otorisasi (7.5), model *least privilege + fail-closed*;
- aturan perubahan (7.11).
Yang diizinkan secara otonom hanya baca, evaluasi, verifikasi, dan evidence;
setiap tindakan mutatif **DENIED**. Bila keadaan menuntut tindakan di luar
batas, alurnya berhenti dan melapor — NUI tidak mengotorisasi dirinya sendiri.
`rtl/scripts/burn_in.py` tetap bukti historis, bukan dasar izin.

**Implementasi pertama, 30 September 2026 — evaluator baca-saja.** Perintah
pemilik: uji kontrak read/verify/evidence terhadap observasi nyata Lapis 5 dan
state model Lapis 6 sebelum satu pun tindakan mutatif dibuka.
`src/hijaiyyah/nui/layer7.py` menjawab keenam prasyarat 7.6 untuk tiga jenis
target — satu observasi host, keadaan hardware CURRENT, atau satu nama fungsi
RTL — lewat mekanisme yang sudah ada:
- `layer5.observations` dan verifikasi manifestnya;
- `layer5.freshness` dengan batas dari spec;
- kelas `outcomes`;
- `hardware_state.answer`;
- hash dan aturan `not_covered` di `NUI/rtl_function.json`, serta state
  opaque, hasil luar, dan `known_discrepancy` yang dinamai
  `NUI/spec/rtl_function.json`;
- tabel 7.4 `NUI/LAYER7.md`, dibaca dari halamannya, dan apa pun yang tidak
  tercantum ditolak.
Tiap prasyarat yang gagal membawa namanya sendiri — `UNKNOWN`, `STALE`,
`NOT_COVERED`, `KNOWN_DISCREPANCY`, `INVALID PROVENANCE`, `AMBIGUOUS TARGET`,
`UNAUTHORIZED ACTION` — dan keputusannya PASS atau STOP / REPORT. Rekaman `acted` selalu
`false`. Evidence baru dibuat oleh `layer5.record`, di luar evaluator, tanpa
mengubah konfigurasi VM, batas 300 detik, daftar kolektor, atau mekanisme
Lapis 5.

Terukur pada bukti nyata, 30 September 2026:
- **Run lama** `20260927T095339Z-collectors`: kesebelas kolektor STALE, umur
  ±239.103 detik, STOP / REPORT. `journal` dan `containers` juga UNKNOWN.
- **Run segar** `20260930T041907Z-collectors` dari `layer5.record`:
  - dievaluasi di bawah satu detik, 9 kolektor PASS;
  - `journal` STOP UNKNOWN (`unavailable_due_to_permissions`), `containers`
    STOP UNKNOWN (`unavailable_command_absent`);
  - dengan jam nyata masih PASS pada 191 dan 238 detik, dan STALE pada 817
    detik untuk kesebelasnya.
- Sebelum dan sesudah run:
  - hash `NUI/spec/layer5_lima.yaml` dan `lima.yaml` instance-nya sama;
  - hash `NUI/spec/layer5_collectors.json` dan `src/hijaiyyah/nui/layer5.py`
    sama;
  - status, CPU, memori, disk, jenis VM, dan arsitektur yang `limactl`
    laporkan sama;
  - HEAD git dan status pohon kerjanya sama.
- **RTL**: `hcpu fetch_redirect_trap` STOP NOT_COVERED, dan `hcpu fetch_latch`
  PASS.
- **Hardware**: `board clock` STOP UNKNOWN, *no live hardware telemetry
  source*.
- **Tindakan DENIED**, `Restart / recovery` atas `hcpu fetch_latch` yang PASS
  untuk baca: STOP UNAUTHORIZED ACTION.

**GREEN pemilik untuk `638d827`, 30 September 2026**, sebagai implementasi
evaluator baca-saja, dengan penyelarasan terminologi kontrak:
- `AMBIGUOUS TARGET` hanya untuk ambiguitas identitas: `(vm_name, run_id)`
  tidak menunjuk tepat satu target/evidence.
- State opaque dan subsistem tanpa fungsi prediktif → `NOT_COVERED`:
  targetnya diketahui, coverage perilakunya belum tersedia.
- Ketidaksesuaian HISAB → `KNOWN_DISCREPANCY`, label baru di 7.8. Ia punya
  evidence dan hasil pengukuran, jadi bukan `UNKNOWN` dan bukan `NOT_COVERED`.
  Ia tidak pernah jadi PASS dan tidak pernah jadi alasan bertindak.
- 7.7 NOT YET VALIDATED: belum ada tindakan mutatif yang diizinkan.

Labelnya dipancarkan `src/hijaiyyah/nui/layer7.py`, jadi pemetaannya diubah
di sana. Keputusan fail-closed tidak berubah, dan tidak ada tindakan yang
dibuka. Terukur pada nama-nama spec yang sesungguhnya:
- `hcpu`: kedelapan state opaque — termasuk `ra_stack[]`, `pengendali kartu`,
  `guard berregister`, dan `register pc di register file` — dan kelima hasil
  luar selain HISAB STOP NOT_COVERED;
- `HISAB` STOP KNOWN_DISCREPANCY, baik di `hcpu` maupun di `pipeline`, dengan
  angka `known_discrepancy` spec yang terbawa di laporannya;
- `pipeline`: keenam hasil luar selain HISAB STOP NOT_COVERED;
- `AMBIGUOUS TARGET` tidak muncul di satu pun target selain host.

**Nama yang tidak dapat dipetakan → `UNKNOWN`**, keputusan pemilik hari yang
sama. Tabel pemisahan keempat label ada di 7.8 `NUI/LAYER7.md`. Yang berhenti
`UNKNOWN`:
- subjek hardware yang tidak menunjuk klaim;
- nama modul yang bukan fungsi model;
- nama yang bukan aturan, state opaque, hasil luar, atau ketidaksesuaian;
- jenis target yang tidak dikenal.
Subsistem tanpa fungsi dikenali lewat nama yang spec berikan, misalnya
`pengendali kartu`, bukan lewat nama berkas RTL-nya. `rtl hcpu_sdio …` berhenti
`UNKNOWN`, karena spec tidak menyediakan pemetaan nama itu, dan hubungan nama
berkas → subsistem tidak dikarang.

**`865959e` GREEN, 30 September 2026** — evaluator baca-saja dengan label yang
diselaraskan. Cakupannya READ → EVALUATE → GATE → EVIDENCE / REPORT, dan
otorisasi mutatif tetap DENIED. Status resminya di `NUI/LAYER7.md`.

`tests/test_ai/test_nui_layer7.py`, 25 tes untuk evaluator, di store sementara yang dibangun
`layer5.record` sendiri:
- tiap prasyarat dan tiap kondisi stop diuji satu per satu, dengan batas 300
  detik inklusif dibaca dari spec;
- sumbernya diperiksa tidak memuat mekanisme tindakan;
- evaluasi dijalankan sementara semua jalan menjalankan perintah atau menulis
  berkas dibuat gagal, dan store tetap identik;
- daftar kondisi 7.6 di `NUI/LAYER7.md` sama dengan label yang evaluator
  pancarkan.
Lima belas sabotase membuatnya merah (R3). Tujuh yang pertama pada evaluator
`638d827`, dan ketujuhnya diulang pada evaluator sesudah pemetaan label:
- kesegaran diabaikan;
- otorisasi fail-open;
- UNKNOWN dianggap known;
- NOT_COVERED dianggap covered;
- provenance tidak sah diloloskan;
- target ambigu diloloskan;
- satu tulisan berkas.
Tujuh untuk pemetaan label:
- ketidaksesuaian dilabeli NOT_COVERED;
- nama yang tak menunjuk apa pun dilabeli AMBIGUOUS;
- state opaque dan hasil luar diabaikan;
- subjek hardware dilabeli AMBIGUOUS;
- label dicabut dari prasyarat coverage ketidaksesuaian;
- label dicabut dari kedua prasyaratnya, sehingga ia PASS;
- `KNOWN_DISCREPANCY` dihapus dari daftar 7.6 kontrak.
Sabotase kelima semula **tidak menggigit**: prasyarat state masih membawa
label, jadi keputusannya tetap STOP. Yang lemah tesnya, dan kini tes menuntut
kedua prasyarat membawa labelnya.
Satu untuk keputusan `UNKNOWN`: tautan `hcpu_sdio` → `pengendali kartu`
dikarang di tempat nama modul diselesaikan. Bentuk pertamanya, yang ditaruh di
pembaca spec, tidak pernah tereksekusi — modul yang bukan fungsi berhenti lebih
dulu — dan yang cacat sabotasenya, bukan tesnya.

**7.7 pada `layer5.record`, perintah pemilik 30 September 2026.** Tindakan yang
divalidasi adalah satu-satunya yang AUTHORIZED dan menghasilkan evidence; tidak
ada tindakan DENIED yang dibuka. `src/hijaiyyah/nui/layer7.py` tetap tidak
menjalankan tindakan apa pun:
- `expect(vm_name)` mengevaluasi keenam prasyarat 7.6 untuk merekam evidence VM
  itu, lalu menetapkan outcome **sebelum** tindakan. Prasyaratnya:
  - identitas `(vm_name, run_id)`;
  - provenance baseline, yaitu observasi terbaru tiap kolektor VM itu;
  - baseline current, dengan batas 300 detik yang tidak dilonggarkan;
  - outcome baseline tergolong salah satu kelas `outcomes` spec;
  - kontrak kolektornya `ditetapkan`;
  - kategori 7.4 *Evidence, provenance, freshness, delta* AUTHORIZED.
  Outcome yang ditetapkan adalah kelas outcome baseline tiap kolektor: yang PASS
  tetap PASS, yang lain tetap di kelasnya. Ditambah daftar run dan hash seluruh
  evidence store serta berkas terlindung sebelum tindakan.
- Pemanggil menjalankan `layer5.record` hanya bila `expect` PASS.
- `confirm(expected)` memegang evidence pascatindakan terhadap outcome itu dengan
  tujuh pemeriksaan dari contoh pemilik, lewat verifikasi `layer5` sendiri. Exit
  code hanya satu medan, bukan vonis.

**Label pemeriksaan 7.7.** Hanya tujuh nama 7.6 yang dipakai. Dua disetujui
pemilik 30 September 2026; lima lainnya penerapan pelaksana atas definisi 7.6
dan 7.8 yang sudah ada:

| pemeriksaan yang gagal | label | dasar |
|---|---|---|
| tidak ada run baru | `UNKNOWN` | penerapan pelaksana |
| lebih dari satu run baru, atau run baru milik VM lain | `AMBIGUOUS TARGET` | penerapan pelaksana |
| manifest tak terbaca atau tanpa hash; provenance ditolak | `INVALID PROVENANCE` | penerapan pelaksana |
| evidence tidak terbaca kembali | `UNKNOWN` | penerapan pelaksana |
| outcome berbeda dari yang ditetapkan | `KNOWN_DISCREPANCY` | **pemilik** |
| evidence bercap sebelum keputusan, atau tidak current saat konfirmasi | `STALE` | penerapan pelaksana |
| perubahan di store selain run baru, atau berkas terlindung berubah | `UNAUTHORIZED ACTION` | **pemilik** — pelanggaran boundary, bukan bukti tindakan gagal secara fungsional |

Berkas terlindung: `NUI/LAYER7.md`, `NUI/spec/layer5_collectors.json`,
`NUI/spec/layer5_lima.yaml`, `src/hijaiyyah/nui/layer5.py`,
`src/hijaiyyah/nui/layer7.py`, dan `lima.yaml` instance itu. Sejak 3 Oktober
2026, atas keputusan pemilik menutup celah ini, juga yang dibaca pagar Lapis 5
sebelum perintah apa pun berjalan — allowlist di `NUI/LAYERS.md` dan katalog
`NUI/spec/layer5_catalog.json`, keduanya lewat `src/hijaiyyah/nui/usr.py` — dan
`src/hijaiyyah/nui/layer7_decision.py`.

**Terukur di VM `cosmictera-layer5`, 30 September 2026**, tanpa caffeinate:
- **`expect` atas baseline lama** `20260930T041907Z-collectors`: STOP STALE,
  umur 34.604 detik. Tidak ada tindakan.
- **Baseline segar** `20260930T135604Z-collectors` dibuat lewat
  `layer5.record`.
- **Percobaan pertama**: `expect` PASS, lalu `layer5.record` jatuh di detik yang
  sama dengan baseline. run_id-nya berpresisi detik, jadi ia ditolak
  `FileExistsError`, exit 1, tanpa menimpa apa pun. `confirm` menjawab STOP
  UNKNOWN, *the expected result is not there*, dan di luar store tidak ada yang
  berubah. `src/hijaiyyah/nui/layer5.py` beku, jadi ini **dilaporkan, tidak
  diubah**.
- **Percobaan kedua**: `expect` PASS pada 13:56:29Z, umur baseline 25,2 detik.
  `layer5.record` membuat `20260930T135629Z-collectors`, exit 0. `confirm`
  menjawab **SUCCESS**: ketujuh pemeriksaan terpenuhi, sembilan kolektor PASS,
  `journal` dan `containers` tetap di kelasnya, manifest `200e84ca…`.
- **Sebelum dan sesudah** tindakan, semuanya identik:
  - hash `lima.yaml` instance, spec, `layer5.py`, `layer7.py`, dan
    `NUI/LAYER7.md`;
  - keadaan VM yang `limactl` laporkan;
  - HEAD git dan status pohon kerja.
- **Semenit kemudian**, `confirm` yang sama menjawab STOP UNAUTHORIZED ACTION:
  `NUI/LAYER7.md` berubah di antara keputusan dan konfirmasi, oleh suntingan
  saya sendiri pada kontrak ini. Pemeriksaan tidak menilai siapa pengubahnya.
- **Sesudah 300 detik**, dengan jam nyata pada 14:01:41Z: STOP STALE untuk
  kesebelas kolektor, bersama UNAUTHORIZED ACTION yang sama.
- Lari-lari di atas memakai `src/hijaiyyah/nui/layer7.py` sebelum satu
  pembetulan CLI: `--action` yang diberikan eksplisit ke `expect` dulu diganti
  diam-diam. Karena itu jalurnya **diulang dengan kode yang di-commit**:
  - baseline `20260930T140258Z-collectors`;
  - `expect` PASS pada 14:07:24Z, umur baseline 266,0 detik;
  - `layer5.record` membuat `20260930T140724Z-collectors`, exit 0;
  - `confirm` **SUCCESS**, ketujuh pemeriksaan terpenuhi, manifest
    `541ae72f…`;
  - keadaan sebelum dan sesudah identik lagi.

`tests/test_ai/test_nui_layer7.py` menambah 14 tes untuk 7.7, di store
sementara dengan jam yang digerakkan tes:
- satu jalur SUCCESS;
- exit 0 di semua kolektor tetap STOP bila outcome berbeda dari yang ditetapkan;
- keenam uji negatif pemilik, masing-masing STOP / REPORT;
- evidence bercap sebelum keputusan;
- perubahan pada run lama dan pada berkas terlindung;
- prasyarat yang menahan tindakan: kategori DENIED, VM tak dikenal, baseline
  basi, dan tanpa baseline;
- ekspektasi yang STOP tidak mengonfirmasi apa pun, dan run yang tetap muncul
  jadi UNAUTHORIZED ACTION;
- `expect` dan `confirm` dijalankan sementara semua jalan bertindak dibuat
  gagal;
- jalur baris perintah yang dipakai lari nyata.
Sebelas sabotase pada kode 7.7 membuatnya merah:
- outcome diabaikan;
- kesegaran diabaikan;
- run pertama dari banyak diterima;
- penolakan provenance diabaikan;
- perubahan di luar diabaikan;
- kategori tindakan diabaikan;
- ekspektasi STOP tetap dikonfirmasi;
- baseline basi diabaikan;
- hasil yang tak ditemukan diloloskan;
- `expect` menulis berkas;
- pelanggaran boundary dibaca sebagai kegagalan fungsional tindakan.
Kelima belas sabotase lama diulang pada kode ini, dan semuanya tetap merah.

**Status dari pemilik, 30 September 2026:** 7.7 *post-action success*
VALIDATED pada `layer5.record`, dengan evidence yang mengacu pada kode final.
Baseline current dikunci, dan presisi `run_id` tidak diubah. Rinciannya di 7.7
`NUI/LAYER7.md`. **`b7fa5e8` GREEN**, hari yang sama; status resminya di kepala
`NUI/LAYER7.md`.

**DECIDE, dry-run — perintah pemilik 30 September 2026.**
`src/hijaiyyah/nui/layer7_decision.py` menerima satu hasil kontrak — dari
`layer7.evaluate` atau `layer7.expect` — dan memberi satu decision record: target,
run_identity, required_action, authorization, preconditions, reason, decision,
expected_outcome, dan `record_sha256` atas medan-medan itu. `verify(record,
result)` menghitung ulang record dari hasil kontraknya dan menyebut tiap medan
yang berubah. Keputusannya diturunkan dari keenam prasyarat hasil itu sendiri:
- kategori DENIED di 7.4 → `DENY`;
- prasyarat mana pun yang berhenti → `STOP / REPORT`, dengan tiap kondisi di
  `reason`;
- kategori AUTHORIZED tanpa satu pun kondisi → `ALLOW`.
Status 7.4 dibaca ulang dari `NUI/LAYER7.md`. Hasil yang mengaku `allowed`
untuk kategori DENIED berhenti sebagai `UNAUTHORIZED ACTION`: tidak ada hasil
yang mengotorisasi dirinya sendiri.

**Disetujui pemilik, 30 September 2026** — semula penerapan pelaksana; alasan
pemilik di 7.6 `NUI/LAYER7.md`:
- **DENY didahulukan atas kondisi lain.** Kategori DENIED tetap `DENY` meski
  evidence-nya juga STALE. Kondisi lainnya tetap tertulis di `reason`.
- **`reason` sebuah `DENY` membawa `UNAUTHORIZED ACTION`**, karena itulah stop
  yang prasyarat otorisasi berikan untuk kategori DENIED. Keputusannya tetap
  `DENY`; `STOP / REPORT` karena `UNAUTHORIZED ACTION` hanya untuk tindakan
  yang tidak tercantum di 7.4, atau hasil yang mengaku lebih dari 7.4.
- **Yang bukan hasil kontrak kandidat → `STOP / REPORT` dengan `UNKNOWN`.**
  Ini termasuk hasil `confirm()`, yang menilai tindakan yang sudah berjalan,
  dan hasil yang putusannya berselisih dengan prasyaratnya sendiri.

Terukur pada evidence VM `cosmictera-layer5`, 30 September 2026. Tiap kali ada
14 hasil kontrak: kesembilan kategori 7.4 atas observasi `processes` terbaru,
hardware `board clock`, `rtl hcpu fetch_redirect_trap`, `rtl hcpu HISAB`, VM
tak dikenal, dan `expect()`.
- **Evidence basi**, `20260930T140724Z-collectors`:
  - kedua kategori AUTHORIZED → STOP STALE;
  - ketujuh kategori mutatif → DENY;
  - hardware → STOP UNKNOWN;
  - RTL → STOP NOT_COVERED dan STOP KNOWN_DISCREPANCY;
  - VM tak dikenal → STOP AMBIGUOUS TARGET;
  - `expect` → STOP STALE.
- **Sesudah satu baseline `layer5.record`**, `20260930T154243Z-collectors`:
  - kedua kategori AUTHORIZED dan `expect` → ALLOW. Record `expect` membawa
    outcome yang ditetapkan dan run_identity baseline-nya;
  - ketujuh kategori mutatif → DENY;
  - keempat target lain STOP seperti di atas.
- Di kedua keadaan, daftar run di evidence store sama sebelum dan sesudah
  DECIDE. ALLOW tidak menjalankan apa pun.
- Hasil kontrak yang sama memberi rekaman keputusan yang identik byte demi
  byte.

**`46f4b14` GREEN, pemilik 30 September 2026**: Decision / Dry-Run GREEN.
Perluasan otorisasi belum diminta, karena rantainya bekerja tanpa kewenangan
mutatif. Status resminya di kepala `NUI/LAYER7.md`.

**Proposal pertama: `SEND_PROGRAM`, dipilih pemilik 1 Oktober 2026 — HARD STOP, STOP / REPORT, otorisasi DENIED.**
Proposalnya di akhir 7.4 `NUI/LAYER7.md`: target, ruang lingkup, program
kandidat, prasyarat, postcondition, hard stop, dan yang dikecualikan.
Tabel 7.4 tidak berubah, dan sebuah tes menjaga agar mengirim program tetap
DENIED. Diukur terhadap evidence yang ada:
- dua prasyarat KNOWN: program ber-evidence dan outcome yang dibekukan;
- dua prasyarat UNKNOWN: *target identity*, karena tidak ada sumber live, dan
  *required communication*, karena loader tidak memancarkan tanda siap.
Keadaan "loader menunggu" hanya pernah dibuat oleh rekonfigurasi papan, yang
dikecualikan. Jadi proposal itu, menurut hard stop-nya sendiri, berhenti hari
ini.

Keputusan pemilik atas proposal itu, 1 Oktober 2026:
- rekonfigurasi tetap di luar, jadi `loader_ready = UNKNOWN` →
  `SEND_PROGRAM = STOP / REPORT`;
- kesiapan tidak diuji dengan mengirim byte pertama;
- evidence pascatindakan tinggal di evidence store eksternal, tanpa path atau
  schema baru sampai otorisasi dibuka;
- program kandidatnya `test_from_card`.
Proposal itu hard-stop secara benar. Membukanya tanpa rekonfigurasi menuntut
sumber evidence baru untuk kesiapan loader dan identitas target, sebagai
pekerjaan spesifikasi tersendiri.

**`590baa6` GREEN, pemilik 1 Oktober 2026** — status resminya di kepala
`NUI/LAYER7.md`. Lalu **readiness evidence discovery**, perintah pemilik hari
yang sama: apakah kesiapan `SEND_PROGRAM` teramati dari arsitektur yang ada,
tanpa byte probe, tulisan UART, rekonfigurasi, atau `send_program`. Terukur
04:08 WIB, hanya pembacaan:
- adaptor USB papan teramati: `SIPEED` "USB Debugger", `0403:6010`, lewat
  `list_ports.comports()` tanpa membuka port;
- FPGA, bitstream yang termuat, dan kesiapan loader tidak teramati:
  - loader tanpa instruksi keluaran;
  - peta MMIO tanpa register data TX;
  - wrapper hanya berbicara sesudah halt;
  - LED tidak terbaca host;
  - sumber hidup Lapis 6 kosong.
`openFPGALoader --detect` tidak dijalankan: alat baris DENIED, dan kodenya
hanya menjawab ada tidaknya `GW2A`. **Hard stop dipertahankan.** Rinciannya
dan satu temuan alat di `rtl/scripts/burn_in_capture.py` ada di 7.4
`NUI/LAYER7.md`.

`tests/test_ai/test_nui_layer7_decision.py`, 37 tes:
- tiap baris tabel pemilik;
- kesembilan kandidat 7.4, segar dan basi;
- determinisme dan `record_sha256`;
- keputusan tidak mengubah masukannya;
- tujuh medan record yang diubah tertangkap `verify` — termasuk sesudah
  disegel ulang;
- hasil yang mengotorisasi dirinya sendiri, putusan yang berselisih dengan
  prasyaratnya, dan masukan yang bukan hasil kontrak;
- pemindai panggilan AST dan uji tanpa efek samping, dengan evaluator, `expect`,
  dan `confirm` ikut dibuat gagal;
- jalur baris perintah.
Sebelas sabotase membuatnya merah (R3):
- DENY hilang;
- kondisi diabaikan;
- self-authorization diterima;
- putusan tak diperiksa;
- digest buta satu medan;
- `verify` buta satu medan;
- masukan longgar;
- outcome dibuang;
- identitas run salah;
- mutatif diizinkan;
- `decide` menulis berkas.

**Yang belum ada.** Tindakan mutatif — seluruhnya DENIED, dan evaluator ini
tidak membukanya. 7.7 VALIDATED hanya pada satu tindakan AUTHORIZED yang tidak
mutatif, `layer5.record`. `INVALID PROVENANCE` diuji hanya pada observasi
host. Hari ini jawaban hardware CURRENT tidak punya basis, dan
provenance hardware live tidak dibuat untuk memicunya. Aset
`rtl/scripts/burn_in.py` terbatas pada satu harness dan satu jenis kegagalan. Tidak ada yang memulai ulang layanan atau memulihkan
kegagalan di luar burn-in, dan tidak ada yang bisa memulihkan host yang
berhibernasi — itu yang membunuh percobaan pertama 72 jam.

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
