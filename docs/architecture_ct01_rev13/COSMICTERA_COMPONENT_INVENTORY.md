# COSMICTERA — COMPLETE REPOSITORY COMPONENT INVENTORY (`CT-01-REV13`)

> **REVISION NOTICE (`v1.2 — K-01..K-12, R2, CTHETA=0x4E / HDOT=0x52 & GAP-02 Final Edition`):**  
> Paket dokumentasi arsitektur versi `v1.0` sebelumnya dinyatakan **`SUPERSEDED` (Tidak Berlaku sebagai Referensi Rekayasa)** sesuai Keputusan Pemilik (*Owner Architecture Consistency Decision*). Edisi `v1.2` ini menerapkan: (1) definisi resmi label epistemik `R2` dari `cosmictera/RULES.md` (`VF` = *Verified Formally*, `CC` = *Computationally Confirmed*, `DP` = *Design Property*, `EH` = *Engineering Hypothesis*, `AT` = *Aspirational Target*), (2) koreksi penuh `K-01` s.d. `K-12` terhadap `rtl/hcpu_pkg.vh`, `rtl/hcpu_rom.v`, `rtl/hcpu_regfile.v`, `rtl/hcpu_mmio.v`, dan `docs/HISA_SPEC.md`, (3) penetapan resmi `0x4E = CTHETA` (ekstraksi $\hat{\Theta}(H[\text{S1}])$ 8-bit, 1 siklus) dan `0x52 = HDOT` (perkalian titik 14-komponen $\langle H[\text{S1}], H[\text{S2}] \rangle_{14}$ 20-bit, 14 siklus pada `CODEX_PROFILE=2` / 1 siklus pada `CODEX_PROFILE=0,1`; total `105` opcode H-ISA v1.2, `84` di RTL, `21` software-only, `375/375` `test_isa_parity.py` PASS), serta (4) penyelesaian `GAP-02` pada `rtl/hcpu_hisab.v` yang kini menginstansiasi `rtl/hcpu_guard.v` secara kanonik (`R1`).


**Repository Root:** `/Users/AMRA/hijaiyyah-mathematics/`  
**Verified Baseline Commit:** `HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`  
**Working Tree Status:** `0` modified tracked files (`git status --short -uno` clean)  
**Epistemic Labels Used (`cosmictera/RULES.md` R2):** `VF` (Verified Formally), `DP` (Design Property), `CC` (Computationally Confirmed), `EH` (Engineering Hypothesis), `AT` (Aspirational Target).

---

## 1. Ringkasan Eksekutif Inventaris (Kategori `A` s.d. `T`)

Tabel berikut merangkum seluruh `20` kategori komponen (`A`–`T`) yang ditemukan melalui pemeriksaan forensik langsung atas pohon sumber `/Users/AMRA/hijaiyyah-mathematics/`:

| Kategori | Nama Domain / Kelompok Komponen | Path Utama di Repository | Jumlah Berkas / Unit | Label Epistemik |
| :--- | :--- | :--- | :--- | :--- |
| **A** | Dokumen Kanonik, Tata Kelola & Spesifikasi | `AGENTS.md`, `cosmictera/`, `docs/`, `cosmictera-build/`, `teknologi/`, `istilah/` | `93` berkas Markdown terlacak Git (`+` laporan Stage 1.3/1.4) | `VF` / `DP` / `CC` |
| **B** | Fondasi Matematika, Master Table & Guard | `src/hijaiyyah/core/` (`master_table.py`, `guards.py`, `exomatrix.py`, `wallace.py`, `manifold.py`, dll.) | `14` modul Python (`28` huruf × `18` dimensi tersegel SHA-256) | `VF` |
| **C** | Delapan Mesin Aljabar Codex | `src/hijaiyyah/codex/` (`jim.py`, `ya.py`, `wau.py`, `ayin.py`, `alif.py`, `ba.py`, `dal.py`, `zay.py`) + `rtl/programs/codex_*.hasm` | `9` modul Python + `8` program `.hasm` | `VF` (Python/H-ISA) / `DP` (di HCPU) |
| **D** | Kriptografi Ka'bah, Jamrah, Hijrah & Kubus 3D | `src/hijaiyyah/crypto/`, `rtl/hijaiyyah_*.v`, `rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v` | `8` modul Python + `13` modul RTL Ka'bah/Jamrah + `2` modul HMAC/SHA | `DP` (Jamrah, Hijrah, Ka'bah no-HMAC) / `CC` (Ka'bah+HMAC) / `EH` (`hijaiyyah_kabah_top` 1.665 pin) |
| **E** | H-ISA v1.2, Assembler & Mesin Referensi Python | `src/hijaiyyah/hisa/` (`opcodes.py`, `assembler.py`, `machine.py`, `parity_programs.py`, `formats.py`) + `src/hijaiyyah/hvm/` | `11` modul Python (`105` opcode terdaftar: `84` RTL / `21` SW) | `VF` / `DP` |
| **F** | HCPU 5-Stage Pipeline RTL & Co-Engines | `rtl/hcpu_*.v`, `rtl/hcpu_pkg.vh` (`hcpu_top.v`, `hcpu_fetch.v` s.d. `hcpu_sdio.v`) | `20` modul RTL inti HCPU + `1` header `.vh` | `DP` (`15.453` LUT4, `18` BSRAM, `120,63` MHz Fmax) |
| **G** | Sistem Operasi HOS, Kernel, Trap & Shell | `src/hijaiyyah/hos/` + `rtl/programs/{kernel,hos,hos_demo,shell,loader}.hasm` | `6` modul Python + `12` program sistem `.hasm` | `DP` (Loader, Trap, Kernel) / `CC` (HOS API penuh) |
| **H** | Sistem Berkas HFS, Kontainer HAR & SDIO | `src/hijaiyyah/hfs/`, `src/hijaiyyah/har/`, `rtl/hcpu_sdio.v`, `rtl/programs/{boot_sd,hfs_sd,hfs_lifecycle}.hasm` | `8` modul Python + `1` контролер RTL SDIO + `4` program `.hasm` | `DP` (`72` jam burn-in kartu SD di papan) / `CC` |
| **I** | Grafika HPG-1 & Mesin Virtual HCVM | `src/hijaiyyah/hpg1/`, `src/hijaiyyah/hcvm/`, `rtl/programs/{hpg1_scene,hcvm}.hasm` | `8` modul Python + `2` program `.hasm` | `CC` |
| **J** | Bahasa Komputasi HC (Hybit Code) & Compiler | `src/hijaiyyah/language/` (`tokens.py`, `lexer.py`, `parser.py`, `evaluator.py`) + `src/hijaiyyah/compiler/codegen.py` | `9` modul Python + `19` program contoh `.hc` | `CC` |
| **K** | Protokol Jembatan Audit HISAB v1.0 | `src/hijaiyyah/hisab/` + `rtl/hcpu_hisab.v` + `rtl/programs/hisab_demo.hasm` | `5` modul Python + `1` modul RTL single-cycle (`HPACK`, `HCRC`) | `DP` / `CC` |
| **L** | Portal 8888 Hardware Authentication & Replay Guard | `portal8888/rtl/` (`hijaiyyah_portal8888.v`, `ingress_parse_v1.v`, `hijaiyyah_timestamp.v`, `jim_sync.v`, `jim_index.v`) + `portal8888/fpga/gowin/` | `6` modul RTL + `11` testbench (`11/11` PASS) + skrip host | `CC` |
| **M** | NUI (Natural Universal Intelligence) Lapis 0–11 | `src/hijaiyyah/nui/` (`43` modul Python), `NUI/` (`LAYERS.md`, `spec/*.json`, `*.json`), `facts/` (`27` fakta) | `43` modul Python + `1.015` tes `tests/test_ai/` + `10` tes `test_facts.py` | `DP` (L0–L7 & KB L9) / `CC` (USR spec) / `AT` (L8 auto, L9 inferensi, L10–L11) |
| **N** | Subsistem Tampilan HDMI 720p & Boot Display (Stage 1.2–1.4) | `rtl/fpga/gowin/` (`hcpu_hdmi_top.v`, `cosmictera_display_top.v`, `hcpu_video_timing.v`, dll.) + `/tmp/stage1_2_cosmictera_boot_ui/rtl/cosmictera_boot_*.v` | `9` modul RTL di repo + `10` modul RTL Stage 1.4 (`cosmictera_boot_top.v`) | `DP` (Diverifikasi fisik pada TV LG 1280×720 @ 60 Hz) |
| **O** | Pembungkus Top-Level FPGA Gowin (`GW2AR-LV18QN88`) | `rtl/fpga/gowin/` (`hcpu_gowin_top.v`, `hcpu_hdmi_top.v`, `cosmictera_display_top.v`, `hijaiyyah_kabah_gowin_top.v`) + `portal8888/fpga/gowin/hijaiyyah_portal8888_gowin_top.v` | `5` top-level di repo + `1` top-level Stage 1.4 (`cosmictera_boot_top.v`) | `DP` (`hcpu_gowin_top`, `cosmictera_display_top`, `cosmictera_boot_top`) / `CC` |
| **P** | Pembungkus ASIC MPW Caravel SkyWater SKY130 | `rtl/mpw/` (`user_project_wrapper.v`, `hcpu_wishbone_wrapper.v`, `openlane/`) | `2` modul RTL + konfigurasi OpenLane + `1` testbench (`8/8` PASS) | `CC` (RTL & TB) / `AT` (GDSII silikon fisik) |
| **Q** | Kuantum QT-4/5/6, Fisika, Analitik & Visualisasi Python | `src/hijaiyyah/quantum/`, `src/hijaiyyah/physics/`, `src/hijaiyyah/analytics/`, `src/hijaiyyah/visual/`, `src/hijaiyyah/ai/` | `24` modul Python | `CC` |
| **R** | Antarmuka CLI, REST API & Perangkat Keras Python | `src/hijaiyyah/cli/`, `src/hijaiyyah/api/`, `src/hijaiyyah/hardware/` | `9` modul Python | `CC` |
| **S** | Korpus Program `.hasm`, Skrip Papan & Otomasi Build | `rtl/programs/` (`62` berkas `.hasm`), `rtl/scripts/` (`24` skrip Python/Shell), `Makefile` | `62` program `.hasm` + `24` skrip rekayasa/papan | `DP` / `CC` |
| **T** | Constraint Pin `.cst`, Testbench Verilog & Suite Pytest | `constraints/*.cst` (`5` berkas), `rtl/tb/*.v` (`39` TB), `portal8888/tb/*.v` (`11` TB), `tests/` (`3.294+` tes pytest) | `5` `.cst` + `50` testbench Verilog + `95+` berkas pytest | `VF` / `DP` / `CC` |

---

## 2. Rincian Inventaris per Kategori (`A` s.d. `T`)

### Kategori A — Dokumen Kanonik, Tata Kelola & Spesifikasi
| Berkas | Peran Arsitektural | Label |
| :--- | :--- | :--- |
| `AGENTS.md` | Aturan tata kelola repositori, tangga bukti 4 tingkat, keputusan pemilik K1–K19 | `VF` |
| `cosmictera/RULES.md` | Enam aturan tetap R1–R6, definisi resmi lima label epistemik (VF, DP, CC, EH, AT) | `VF` |
| `COSMICTERA_CT01_REV13_AUDIT.md` | Audit arsitektur CT-01-REV13 13 lapis dan rekonsiliasi status komponen | `CC` |
| `cosmictera/SYSTEM.md` | Peta sistem kanonik 11 lapis dan batas realisasi fisik vs perangkat lunak | `CC` |
| `cosmictera/COMPUTING.md` | Spesifikasi tumpukan komputasi H-ISA, HCPU, HOS, HFS, HPG-1, HCVM, HAR | `CC` |
| `cosmictera/CONCRETE.md` | Daftar artefak konkret yang dapat diukur dan diverifikasi langsung | `CC` |
| `cosmictera/TELEMETRY.md` | Kontrak 27 medan telemetri HCPU/papan dan protokol observasi | `DP` |
| `teknologi/ISTILAH.md` | Kamus istilah resmi teknologi Hijaiyyah/Hybit/CosmicTera (tanpa rebranding) | `VF` |
| `docs/ARCHITECTURE.md` | Arsitektur 11 lapis repositori hijaiyyah-mathematics | `CC` |
| `docs/HISA_SPEC.md` | Spesifikasi resmi H-ISA v1.2 (105 opcode: 84 RTL / 21 SW, format instruksi 32-bit, MMIO, trap) | `VF` |
| `ENGINEERING_STANDARD.md` | Standar rekayasa perangkat keras/perangkat lunak dan disiplin verifikasi | `VF` |
| `CONTRIBUTING.md` | Batas konseptual: huruf Hijaiyyah sebagai objek matematis, bukan bunyi/makna | `VF` |
| `cosmictera-build/ROADMAP.md` | Peta jalan pembangunan perangkat keras dan perangkat lunak CosmicTera | `CC` |
| `cosmictera-build/ON.md` | Daftar komponen yang aktif berjalan dan terverifikasi | `DP` |
| `cosmictera-build/OFF.md` | Daftar temuan, celah, bug perangkat keras/perangkat lunak, dan item belum aktif | `DP` |
| `cosmictera-build/CHECKLIST.md` | Daftar periksa verifikasi reproducible dengan perintah uji | `DP` |
| `cosmictera-build/PAPAN.md` | Catatan hasil sintesis, Place & Route, dan pengujian fisik papan Tang Nano 20K | `DP` |

### Kategori B — Fondasi Matematika (`src/hijaiyyah/core/`)
| Berkas | Baris | Fungsi & Invarian Utama | Label |
| :--- | :---: | :--- | :---: |
| `src/hijaiyyah/core/__init__.py` | `14` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/codex_entry.py` | `114` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/constants.py` | `128` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/exceptions.py` | `45` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/exomatrix.py` | `167` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/guards.py` | `206` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/har.py` | `251` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/hgeo.py` | `232` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/hybit.py` | `256` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/master_table.py` | `127` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |
| `src/hijaiyyah/core/rom.py` | `66` | Modul inti matematika Hijaiyyah / Master Table / Guard / Eksomatriks | `VF` |

### Kategori C — Delapan Mesin Aljabar Codex (`src/hijaiyyah/codex/`)
| Berkas | Baris | Mesin Codex & Struktur Aljabar | Program H-ASM Pasangan | Label |
| :--- | :---: | :--- | :--- | :---: |
| `src/hijaiyyah/codex/jim.py` | `0` | **Codex JIM** — Orbit grup linier `GL(5, GF(2))` & periodisitas operator 5×5 | `rtl/programs/codex_jim.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/ya.py` | `0` | **Codex YA** — Aritmetika gelanggang polinomial `F_2[x]/(x^5 + x^2 + 1)` | `rtl/programs/codex_ya.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/wau.py` | `0` | **Codex WAU** — Dinamika ruang fase 27-keadaan pada Kubus 3D | `rtl/programs/codex_wau.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/ayin.py` | `0` | **Codex 'AYIN** — Geometri insidensi bidang proyektif `PG(2, F_5)` (31 titik/garis) | `rtl/programs/codex_ayin.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/alif.py` | `0` | **Codex ALIF** — Dekomposisi spektral, trace, dan polinomial karakteristik | `rtl/programs/codex_alif.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/ba.py` | `0` | **Codex BA** — Entropi simbolik Shannon/Rényi & kapasitas kanal 18D | `rtl/programs/codex_ba.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/dal.py` | `0` | **Codex DAL** — Topologi graf 28-simpul, matriks Laplacian & konektivitas aljabar | `rtl/programs/codex_dal.hasm` | `VF` / `DP` |
| `src/hijaiyyah/codex/zay.py` | `0` | **Codex ZAY** — Propagator diferensial/linier (DDT/LAT) & reduksi pohon Wallace | `rtl/programs/codex_zay.hasm` | `VF` / `DP` |

### Kategori D — Kriptografi Ka'bah, Jamrah, Hijrah & Kubus (`src/hijaiyyah/crypto/` & `rtl/hijaiyyah_*.v`)
| Berkas | Baris | Fungsi & Status Verifikasi | Label |
| :--- | :---: | :--- | :---: |
| `src/hijaiyyah/crypto/__init__.py` | `5` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/certificate.py` | `41` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/cli.py` | `436` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/cube.py` | `681` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/elements.py` | `203` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/guard_filter.py` | `9` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/guarded_record.py` | `543` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/hashing.py` | `65` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/kabah.py` | `590` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/memscan.py` | `428` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/node_counter.py` | `381` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/program.py` | `482` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/sbox_logic.py` | `239` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/signing.py` | `34` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `src/hijaiyyah/crypto/wave.py` | `168` | Modul kriptografi Python (`crypto/`) | `VF` / `CC` |
| `rtl/hijaiyyah_deserialiser.v` | `74` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_hmac.v` | `140` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_jamrah_gate.v` | `83` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_kabah_top.v` | `296` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_linear.v` | `122` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_node_counter.v` | `151` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_ramal_core.v` | `158` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_ramal_impulse.v` | `129` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_rotate_core.v` | `242` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_round_constants.v` | `50` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_sbox.v` | `123` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_sbox_router.v` | `101` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_sha256_core.v` | `161` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_sha256_stream.v` | `168` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_sponge.v` | `134` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/hijaiyyah_wave.v` | `66` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_gate_mode.v` | `106` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_hmac.v` | `82` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_hmac_gowin_top.v` | `77` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_jamrah_gate.v` | `79` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_kabah_gowin_top.v` | `186` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_kabah_top.v` | `106` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_linear.v` | `46` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_node_counter.v` | `91` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_priority.v` | `35` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_ramal_core.v` | `89` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_ramal_impulse.v` | `82` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_rotate_core.v` | `90` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_sbox.v` | `294` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_sbox_router.v` | `84` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_sha256_stream.v` | `92` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_sponge.v` | `114` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_standby.v` | `120` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |
| `rtl/tb/tb_hijaiyyah_wave.v` | `89` | Modul RTL Kriptografi Ka'bah / Jamrah / SHA-256 / HMAC | `DP` / `CC` |

### Kategori E — H-ISA v1.2, Assembler & Mesin Virtual (`src/hijaiyyah/hisa/` & `src/hijaiyyah/hvm/`)
| Berkas | Baris | Peran dalam Tumpukan Eksekusi | Label |
| :--- | :---: | :--- | :---: |
| `src/hijaiyyah/hisa/__init__.py` | `5` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/assembler.py` | `478` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/compiler.py` | `6` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/hbc_format.py` | `215` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/hcheck.py` | `119` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/machine.py` | `1363` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/opcodes.py` | `392` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/parity_programs.py` | `400` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |
| `src/hijaiyyah/hisa/registers.py` | `50` | Spesifikasi opcode / Assembler 2-pass / Interpreter `HISAMachine` / Korpus Paritas | `VF` / `DP` |

### Kategori F — HCPU 5-Stage Pipeline RTL & Co-Engines (`rtl/hcpu_*.v`)
| Berkas | Baris | Peran Modul Perangkat Keras | Label |
| :--- | :---: | :--- | :---: |
| `rtl/hcpu_codex_alu.v` | `297` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_compositor.v` | `207` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_controller.v` | `101` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_dashboard.v` | `248` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_dataram.v` | `61` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_decode.v` | `396` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_execute.v` | `571` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_fetch.v` | `113` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_font_rom.v` | `60` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_forward.v` | `105` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_guard.v` | `155` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_hisab.v` | `145` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_layout_rom.v` | `62` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_memory.v` | `166` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_mmio.v` | `387` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_mul.v` | `67` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_page_key.v` | `120` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_regfile.v` | `133` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_rom.v` | `271` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_sdio.v` | `862` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_telemetry.v` | `143` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_text_ram.v` | `92` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_text_render.v` | `142` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_timer.v` | `51` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_top.v` | `898` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_trap.v` | `227` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_uart_rx.v` | `119` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_uart_tx.v` | `97` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_video_timing.v` | `110` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_writeback.v` | `49` | Modul RTL inti HCPU / Pipeline / ALU / Guard / HISAB / MMIO / SDIO / Trap | `DP` |
| `rtl/hcpu_pkg.vh` | `367` | Definisi konstanta global HCPU (`XLEN=32`, `HREG_W=144`, `84` RTL opcode dari `105` H-ISA, peta MMIO `0xFE0–0xFFF`) | `DP` |

### Kategori G, H, I, J, K — Perangkat Lunak Sistem (`hos/`, `hfs/`, `har/`, `hpg1/`, `hcvm/`, `language/`, `compiler/`, `hisab/`)
| Subpaket | Berkas Modul Python | Total Baris | Program `.hasm` Terkait | Label |
| :--- | :--- | :---: | :--- | :---: |
| `src/hijaiyyah/hos/` |  | `0` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/hfs/` |  | `0` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/har/` | `__init__.py` | `288` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/hpg1/` |  | `0` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/hcvm/` |  | `0` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/language/` | `__init__.py`, `ast_nodes.py`, `diagnostics.py`, `evaluator.py`, `grammar.py`, `lexer.py`, `parser.py`, `tokens.py` | `3209` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/compiler/` | `__init__.py`, `codegen.py`, `psi.py` | `1203` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |
| `src/hijaiyyah/hisab/` | `__init__.py`, `digest.py`, `protocol.py`, `serialize.py`, `validate.py` | `786` | Program `.hasm` di `rtl/programs/` | `DP` / `CC` |

### Kategori L — Portal 8888 Hardware Authentication (`portal8888/`)
| Berkas | Baris | Fungsi Arsitektural | Label |
| :--- | :---: | :--- | :---: |
| `portal8888/build/diag/kabah_hmac_trial/kabah_hmac_trial_top.v` | `341` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/build/diag/top.v` | `12` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/build/diag/v5/hijaiyyah_kabah_gowin_top.v` | `577` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/fpga/gowin/hijaiyyah_portal8888_gowin_top.v` | `257` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/rtl/hijaiyyah_portal8888.v` | `358` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/rtl/hijaiyyah_timestamp.v` | `92` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/rtl/ingress_parse.v` | `87` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/rtl/ingress_parse_v1.v` | `83` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/rtl/jim_index.v` | `52` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/rtl/jim_sync.v` | `31` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_hijaiyyah_portal8888_gowin_top.v` | `110` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_ingress.v` | `28` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_ingress_v1.v` | `28` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_jim.v` | `38` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_portal8888.v` | `61` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_portal8888_system.v` | `76` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_portal8888_v1.v` | `71` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |
| `portal8888/tb/tb_timestamp.v` | `49` | Modul RTL / Testbench / Skrip Portal 8888 | `CC` |

### Kategori M — NUI (Natural Universal Intelligence) Lapis 0–11 (`src/hijaiyyah/nui/`)
| Berkas Modul NUI | Baris | Lapis NUI & Tanggung Jawab | Label |
| :--- | :---: | :--- | :---: |
| `src/hijaiyyah/nui/__init__.py` | `22` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/atom.py` | `125` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/board_parity.py` | `547` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/board_probes.py` | `245` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/claims.py` | `134` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/clockwork.py` | `219` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/dataset.py` | `186` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/execution_graph.py` | `331` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/execution_trace.py` | `482` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/facts.py` | `244` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/features.py` | `78` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/freeze.py` | `246` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/hardware.py` | `240` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/hardware_correlation.py` | `433` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/hardware_provenance.py` | `631` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/hardware_state.py` | `374` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/knowledge.py` | `874` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer4_freeze.py` | `401` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer5.py` | `545` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer5_freeze.py` | `224` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer6_addendum.py` | `903` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer6_freeze.py` | `359` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer7.py` | `566` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer7_decision.py` | `159` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer7_linux.py` | `437` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/layer7_portal.py` | `434` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/model.py` | `193` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/multitask.py` | `193` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/off_db.py` | `112` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/parity_model.py` | `1084` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/pattern_language.py` | `126` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/program_graph.py` | `153` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/program_index.py` | `246` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/program_summary.py` | `178` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/rack.py` | `95` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/registry.py` | `127` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/repository_graph.py` | `327` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/repository_index.py` | `150` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/rtl_function.py` | `3711` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/sram_mock.py` | `88` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/telemetry_sources.py` | `231` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/train.py` | `172` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |
| `src/hijaiyyah/nui/usr.py` | `518` | Modul kecerdasan deterministik NUI (`src/hijaiyyah/nui/`) | `DP` / `CC` |

### Kategori N, O, P — Top-Level Wrappers FPGA Gowin, Boot Display & ASIC MPW (`rtl/fpga/gowin/`, `/tmp/stage1_2_cosmictera_boot_ui/rtl/`, `rtl/mpw/`)
| Berkas | Baris | Target Fisik & Utilisasi Terukur | Label |
| :--- | :---: | :--- | :---: |
| `rtl/fpga/gowin/cosmictera_display_top.v` | `167` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/cosmictera_vidtest_top.v` | `170` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/dvi_tx_open.v` | `166` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/hcpu_gowin_top.v` | `708` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/hcpu_hdmi_top.v` | `351` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/hijaiyyah_cosmictera_gowin_top.v` | `72` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/hijaiyyah_hmac_gowin_top.v` | `206` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v` | `618` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/kabah_hdmi_top.v` | `163` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/fpga/gowin/tmds_rpll.v` | `21` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/hcpu_dataram_sky130.v` | `116` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/hcpu_mpw_top.v` | `182` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/hcpu_synth_netlist.v` | `1422574` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/hcpu_wb_adapter.v` | `144` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/sky130_sram_macros/sky130_sram_1kbyte_1rw1r_32x256_8/sky130_sram_1kbyte_1rw1r_32x256_8.v` | `114` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/sky130_sram_macros/sky130_sram_1kbyte_1rw1r_8x1024_8/sky130_sram_1kbyte_1rw1r_8x1024_8.v` | `108` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/sky130_sram_macros/sky130_sram_2kbyte_1rw1r_32x512_8/sky130_sram_2kbyte_1rw1r_32x512_8.v` | `114` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `rtl/mpw/sky130_sram_macros/sram_1rw1r_32_256_8_sky130/sram_1rw1r_32_256_8_sky130.v` | `104` | Wrapper FPGA Gowin Tang Nano 20K / Display HDMI / MPW Caravel Sky130 | `DP` / `CC` |
| `/tmp/stage1_2_cosmictera_boot_ui/rtl/cosmictera_boot_top.v` (+ `9` submodul `cosmictera_boot_*.v`) | `2.840` | Stage 1.4 Official Boot Display (`2.526` LUT4 / `12,18%`, `12` BSRAM, `84,53` MHz Fmax, teruji di TV LG) | `DP` |

### Kategori Q, R, S, T — Simulasi Kuantum/Fisika, CLI/API, Program `.hasm`, Constraint `.cst` & Suite Pengujian
- **Paket `quantum/`, `physics/`, `analytics/`, `visual/`, `ai/`, `cli/`, `api/`, `hardware/`**: `3` modul Python (`CC`).
- **Program `.hasm` (`rtl/programs/` & `rtl/programs/bench/`)**: `59` berkas program assembly H-ISA (`DP` / `CC`).
- **Constraint Pin `.cst` (`constraints/`)**: ``constraints/cosmictera_tangnano20k.cst`` (`DP`).
- **Testbench Verilog (`rtl/tb/` & `portal8888/tb/`)**: `62` testbench di `rtl/tb/` + `8` testbench di `portal8888/tb/` = `70` testbench (`VF` / `DP` / `CC`).
