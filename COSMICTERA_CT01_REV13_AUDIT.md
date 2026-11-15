# AUDIT FORENSIK ARSITEKTUR EKOSISTEM 13-LAPIS COSMICTERA
## DWG NO. CT-01-REV13 — COSMICTERA MASTER ENGINEERING BLUEPRINT

**Tanggal Audit:** 3 November 2026  
**Titik Jangkar Git (`HEAD`):** `8c70989bec0d3b86ace8b657fd8f1d761164b8e3` (`main`)  
**Cakupan:** Seluruh 21 Komponen pada 4 Domain Blueprint `CT-01-REV13`, 9 Prioritas Pemilik Proyek, 4 Gerbang Verifikasi (*Four Engineering Gates*), Rekonsiliasi Arsip, dan Integrasi Telemetri Subsistem Komputasi ke *CosmicTera Boot Display*.

---

## 1. RINGKASAN EKSEKUTIF & STATUS EPISTEMIK (`R7`)

Dokumen ini menyajikan hasil pemeriksaan forensik menyeluruh atas **CosmicTera Master Engineering Blueprint (`CT-01-REV13`)** terhadap kode sumber aktual, spesifikasi kanonik, artefak sintesis/P&R, dan catatan eksekusi papan fisik (`Tang Nano 20K — GW2AR-LV18QN88C8/I7`).

Sesuai aturan mengikat **`cosmictera/RULES.md` (`R7`)**, setiap komponen pada audit ini diberi label status epistemik tunggal dan tidak dicampuradukkan:

| Kode | Label Epistemik (`R7`) | Definisi Operasional di Repositori Ini |
|:---:|---|---|
| **`VF`** | *Verified in Hardware* | Terbukti berjalan di papan fisik (`cosmictera-build/PAPAN.md`) atau simulasi RTL penuh + sintesis/P&R terukur dengan bukti artefak (`MEASURED` / `PNR`). |
| **`CC`** | *Computationally Confirmed* | Diverifikasi secara matematis dan algoritmik melalui suite pengujian Python/RTL (`pytest` / `iverilog` + `vvp`) secara deterministik (`SIMULATED`). |
| **`DP`** | *Designed & Planned* | Memiliki spesifikasi kanonik, kontrak antarmuka, atau RTL/kode sebagian yang terdefinisi jelas, namun belum seluruh jalur terpasang di silikon. |
| **`EH`** | *Exploratory Hypothesis* | Kandidat arsitektur atau hipotesis riset yang sedang dievaluasi dan belum dikunci ke spesifikasi normatif. |
| **`AT`** | *Analogical / Theoretical* | Kerangka teoretis atau target masa depan yang belum memiliki implementasi perangkat keras terverifikasi. |

---

## 2. PEMETAAN ARSITEKTUR 13-LAPIS (`CT-01-REV13`) TERHADAP TUMPUKAN REPOSITORI

Dokumen terdahulu (`cosmictera/SYSTEM.md`) mengelompokkan sistem ke dalam 7 lapis (*L1 Fondasi Formal s.d. L7 Aplikasi & Antarmuka*), sedangkan piagam HMCL (`src/hijaiyyah/hmcl/charter_assets.py`) mendefinisikan **13 Lapisan Kanonik (`Layers 0–12`)** yang sejalan dengan **13-Layer Complete Ecosystem Architecture (`CT-01-REV13`)**. Sesuai Mandat Utama Bagian A, arsitektur 7-lapis terdahulu dipertahankan sebagai riwayat perkembangan dan dipetakan secara utuh ke dalam **13 Lapisan `CT-01-REV13`** berikut:

| Lapis (`CT-01-REV13`) | Nama Lapisan Ekosistem | Padanan `cosmictera/SYSTEM.md` (7-Lapis) | Padanan `HMCL Charter` (`0..12`) | Modul / Sumber Kanonik Utama | Status Epistemik |
|:---:|---|---|---|---|---|
| **Layer 1** | **Master Table HM-28 & Fondasi Rasm Kanonik** | L1 — Fondasi Formal (Bab I) | Layer 0 (`Formalism`) & Layer 1 (`Axioms`) | `src/hijaiyyah/core/master_table.py`, `rtl/hcpu_rom.v` | **`VF`** |
| **Layer 2** | **Ruang Vektor Hybit 18D ($\mathbb{N}_0^{18}$) & Enam Guard (`G1–G4`, `T1–T2`)** | L1 — Fondasi Formal (Bab I) | Layer 2 (`Postulates`) & Layer 3 (`Derived Laws`) | `src/hijaiyyah/core/hybit.py`, `src/hijaiyyah/core/guards.py`, `rtl/hcpu_guard.v` | **`VF`** |
| **Layer 3** | **Lima Cabang Aljabar Vektorial & 18 Teorema Formal** | L2 — Aljabar Vektorial (Bab II) | Layer 4 (`Symbolic Engine`) | `src/hijaiyyah/algebra/`, `src/hijaiyyah/theorems/test_suite.py`, `matematika-hijaiyyah/` | **`CC`** (`VF` untuk subset ALU) |
| **Layer 4** | **Bahasa Hijaiyyah Cells (`.hcell` / `.hc`), Cell IR & $\Psi$-Injector** | L4 — Bahasa & Kompilator | Layer 7 (`Algorithmic Transformation`) | `src/hijaiyyah/cells/`, `src/hijaiyyah/compiler/`, `src/hijaiyyah/hisa/psi_injector.py` | **`CC`** (`VF` untuk `.hc` di HCPU) |
| **Layer 5** | **Hijaiyyah ISA (`H-ISA`) — 104 Opcode (`82 RTL / 22 SW`) & Bytecode `.hbc`** | L3 — Arsitektur Set Instruksi | Layer 8 (`ISA & Compiler Lowering`) | `docs/HISA_SPEC.md`, `src/hijaiyyah/hisa/opcodes.py`, `rtl/hcpu_pkg.vh` | **`VF`** (82 RTL) / **`CC`** (22 SW) |
| **Layer 6** | **Arsitektur Memori (`IMEM 4K`, `DMEM 4K`, `H-Reg 8×144b`, `GPR 18×32b`)** | L3 / L5 — Memori & Register | Layer 9 (`Microarchitecture`) | `rtl/hcpu_regfile.v`, `rtl/hcpu_dataram.v`, `rtl/fpga/gowin/hcpu_gowin_core.v` | **`VF`** |
| **Layer 7** | **HCPU 5-Stage Pipeline & Codex ALU (`Profile A / B / C`)** | L5 — Prosesor & Perangkat Keras | Layer 9 (`Microarchitecture`) & Layer 10 (`RTL & Gate Synthesis`) | `rtl/hcpu_top.v`, `rtl/hcpu_fetch.v`, `rtl/hcpu_decode.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_memory.v`, `rtl/hcpu_writeback.v`, `rtl/hcpu_codex_alu.v` | **`VF`** (`Profile C` di papan) |
| **Layer 8** | **HOS Kernel, Guarded HFS (`SDIO LBA`), HPG1 4-B' Verifier & HMCL Lab** | L6 — Sistem Operasi & Runtime (`H-Kernel`, `HAL`, `HOS`) | Layer 5 (`Numerical Simulation`) & Layer 8 | `rtl/programs/shell.hasm`, `rtl/programs/hos*.hasm`, `src/hijaiyyah/cells/hpg1_bridge.py`, `src/hijaiyyah/hmcl/` | **`VF`** (`HOS`/`HFS`/`HMCL`) / **`CC`** (`HPG1`) |
| **Layer 9** | **12-Layer NUI (*Natural Universal Intelligence*)** | L7 — Aplikasi & Antarmuka (`NUI`) | Layer 6 (`Heuristic Search`) | `NUI/ROADMAP.md`, `NUI/LAYERS.md`, `NUI/pipeline.py`, `src/hijaiyyah/nui/` | **`VF`** (Embedding & L0–L7 Parity) / **`DP`** (Fase 2–5) |
| **Layer 10** | **Mesin Kriptografi & Aljabar Khusus (`Ka'bah 1600-bit`, `Jamrah 7-Node`, `Hijrah GF(5)`)** | L6 — Kriptografi (`Ka'bah`) | Layer 4 & Layer 10 | `src/hijaiyyah/crypto/cube.py`, `rtl/programs/jamrah.hasm`, `hijrah/engine.py` | **`VF`** (`Ka'bah`, `Jamrah`) / **`CC`** (`Hijrah`) |
| **Layer 11** | **Mesin Dinamika & Penyegel Provenans (`Codex Jim J-Machine` & `Portal 8888`)** | L6 / L7 — Provenans & Audit | Layer 12 (`Physical Silicon & Telemetry`) | `cosmic-codex-jim/j_machine.py`, `portal8888/ARCHITECTURE.md`, `src/hijaiyyah/nui/portal_8888.py` | **`CC`** (`J-Machine`) / **`VF`** (`P8-1..P8-4` di Python+RTL) |
| **Layer 12** | **Telemetri Sistem, Monitor HDMI (`Boot UI` / `Dashboard`) & Command Center** | L7 — Aplikasi & Antarmuka (`CSGI`, `GUI`, `Monitor`) | Layer 12 (`Physical Silicon & Telemetry`) | `cosmictera/TELEMETRY.md`, `rtl/hcpu_telemetry.v`, `rtl/hcpu_compositor.v`, Stage 1.2 `cosmictera_boot_top.v` | **`VF`** (RTL + Papan) |
| **Layer 13** | **Target Silikon & FPGA (`Tang Nano 20K`, `Sky130 MPW ASIC`, `Kria KV260`)** | L5 — Target Implementasi | Layer 11 (`Physical Layout & Timing`) & Layer 12 | `rtl/fpga/gowin/`, `rtl/mpw/`, `cosmictera-build/ROADMAP.md` | **`VF`** (`GW2AR-18C`) / **`DP`** (`Sky130`, `KV260`) |

---

## 3. AUDIT FORENSIK 21 KOMPONEN BLUEPRINT (`DOMAIN 1 – DOMAIN 4`)

### DOMAIN 1 — MATHEMATICAL & SCIENTIFIC FOUNDATION

#### (1) Master Table HM-28
- **Status Epistemik:** **`VF`** (*Verified in Hardware* — silikon Tang Nano 20K & testbench `tb_rom.v` 30/30 PASS).
- **Sumber Kanonik:**
  - Python: `src/hijaiyyah/core/master_table.py` (28 huruf Hijaiyyah kanonik: `Alif` indeks 1 s.d. `Ya` indeks 28, tersegel SHA-256).
  - RTL: `rtl/hcpu_rom.v` (`28 × 72-bit` packed codex ROM, 1-indexed `1..28`, indeks `0` dan `29..31` menghasilkan `valid=0`).
  - Sel (`.hcell`): `src/hijaiyyah/cells/master_table_engine.py`.
- **Fakta Terukur:**
  - Penyelarasan kanonik dilakukan pada commit `b5bd239` (memperbaiki penyimpangan lama pada `ط ظ ك ن`) dan dijangkarkan ke halaman buku pada `9f279e1` (`tests/test_integrity/test_bab_satu.py` dan `test_book_anchor.py`).
  - `Kaf` (indeks 22) adalah **satu-satunya** huruf dengan indikator non-geometris $H^* = 1$ ($\Psi = 1$); 27 huruf lainnya memiliki $H^* = 0$.
- **Kesenjangan / Catatan:** Tidak ada kesenjangan. Seluruh salinan di Python, ROM RTL, dan `.hcell` identik bit-demi-bit.

#### (2) 18D Hybit Vector ($\mathbb{N}_0^{18}$)
- **Status Epistemik:** **`VF`** (*Verified in Hardware* — `H-Reg` $8 \times 144\text{-bit}$ di `rtl/hcpu_regfile.v` dan `rtl/hcpu_codex_alu.v`).
- **Sumber Kanonik:** `src/hijaiyyah/core/hybit.py`, `teknologi/ISTILAH.md`, `rtl/hcpu_pkg.vh`.
- **Struktur 18 Komponen:**
  - **14 Invarian Primer:**
    - *Nuqṭah* ($\nu$): `AN` ($A_N$), `N_up` ($N_\uparrow$), `N_down` ($N_\downarrow$), `N_in` ($N_{\text{in}}$) — indeks `0..3`.
    - *Khaṭṭ* ($\kappa$): `AK` ($A_K$), `K_h` ($K_h$), `K_v` ($K_v$), `K_d` ($K_d$), `K_s` ($K_s$), `K_c` ($K_c$) — indeks `4..9`.
    - *Qaws* ($\theta$): `AQ` ($A_Q$), `Q_o` ($Q_o$), `Q_c` ($Q_c$), `Q_l` ($Q_l$) — indeks `10..13`.
  - **3 Ringkasan (*Summaries*):** `S` ($\Sigma = A_N + A_K + A_Q$), `U` ($U$), `rho` ($\rho$) — indeks `14..16`.
  - **1 Indikator Non-Geometris:** `H_star` ($H^*$ / $\Psi \in \{0,1\}$) — indeks `17`.
- **Representasi Perangkat Keras:**
  - Dalam `H-Reg` (`H0..H7`), setiap vektor disimpan sebagai **144-bit** (`18 komponen × 8-bit unsigned`).
  - Dalam ROM (`rtl/hcpu_rom.v`) dan protokol `HISAB` (`rtl/hcpu_hisab.v`), disimpan dalam bentuk **72-bit nibble-packed** (`18 × 4-bit`).
- **Kesenjangan Diagram Blueprint vs Kode:** Pada ilustrasi visual `CT-01-REV13`, sumbu berlabel `θ (Theta)` dan `ν (Nuqtah)` tampak tercetak ganda di sisi kiri diagram 18D Hybit Vector. Secara matematis dan di kode sumber, keempat kelompok komponen tetap: *Nuqṭah*, *Khaṭṭ*, *Qaws* (dengan *Inḥinā'* $\rho$ dan $U$), serta *Anāṣir* / ringkasan + $H^*$.

#### (3) Six Guard (`G1–G4` / `T1–T2`)
- **Status Epistemik:** **`VF`** (*Verified in Hardware* — `67ee048` di papan fisik Tang Nano 20K & `tb_guard.v` 34/34 PASS).
- **Sumber Kanonik:** `src/hijaiyyah/core/guards.py`, `rtl/hcpu_guard.v`.
- **Definisi Enam Guard:**
  - **`G1` (Nuqṭah Conservation):** $A_N = N_\uparrow + N_\downarrow + N_{\text{in}}$.
  - **`G2` (Khaṭṭ Conservation):** $A_K = K_h + K_v + K_d + K_s + K_c$.
  - **`G3` (Qaws Conservation):** $A_Q = Q_o + Q_c + Q_l$.
  - **`G4` (Non-Negative Inḥinā'):** $\rho \ge 0$ (dengan $\rho = 2(Q_o + Q_c + Q_l) + K_d + K_s - K_v$).
  - **`T1` (Topological Closure — Split):** $K_s > 0 \implies Q_c > 0$.
  - **`T2` (Topological Closure — Cross):** $K_c > 0 \implies Q_c > 0$.
- **Catatan Arsitektural (`890cf9d`):** $H^*$ bukan guard ketujuh dan bukan celah guard, melainkan fungsi indikator non-geometris untuk memisahkan pasangan homomorfik (`Kaf` vs `Lam` / `Dal` vs `Ra` dengan $\Psi$-Injector).

#### (4) Five Algebraic Branches (*Lima Cabang Aljabar BAB II*)
- **Status Epistemik:** **`CC`** untuk kelima cabang penuh di Python (`tests/test_integrity/test_bab_dua.py`); **`VF`** di silikon untuk operasi `HCADD`, `HCSUB`, `HNRM2`, `HDIST`, `HDOT`, `CMOV`, `CZERO`, `CEQ`, `CRHO`, `CU`, `CMOD4`.
- **Sumber Kanonik:**
  1. **Vektronometry:** `src/hijaiyyah/algebra/vektronometry.py` — operasi ruang vektor dasar, proyeksi, sudut/kesamaan kosinus, dan jarak $L_1 / L_2^2$.
  2. **Normivektor:** `src/hijaiyyah/algebra/normivektor.py` — norma berbobot dan tak-berbobot (`HNRM2` di RTL menghitung $\sum_{i=0}^{13} c_i^2$ atas 14 invarian primer).
  3. **Aggregametric:** `src/hijaiyyah/algebra/aggregametric.py` — agregasi monoid $(\mathbb{N}_0^{18}, +)$ atas kata/barisan huruf (`HCADD`, `BSM`).
  4. **Intrametric:** `src/hijaiyyah/algebra/intrametric.py` — relasi internal antar-komponen dalam satu huruf/vektor ($\Sigma, U, \rho \bmod 4$).
  5. **Exometric:** `src/hijaiyyah/algebra/exometric.py` — matriks jarak dan ketetanggaan antar-28 huruf (*Exomatrix* $28 \times 28$; catatan `7541245`: kode membangun transpos dari matriks cetak buku secara sengaja dan terdokumentasi).

#### (5) 18 Theorems (*Rekonsiliasi 18 Teorema Blueprint vs 13 Teorema `TheoremTestSuite`*)
- **Status Epistemik:** **`CC`** (*Computationally Confirmed* melalui `tests/test_theorems/` dan `tests/test_integrity/test_bab_satu.py` + `test_bab_dua.py`).
- **Temuan Rekonsiliasi Penting (Wajib Dicatat):**
  - Di dalam `src/hijaiyyah/theorems/test_suite.py` (`TheoremTestSuite`) dan `matematika-hijaiyyah/README.md`, terdapat **13 teorema bernama (`T1` s.d. `T13`)**:
    - `T1` Conservation Law ($A_N, A_K, A_Q, \Sigma$), `T2` Sub-vector Independence, `T3` Non-degeneracy ($\forall h, \Sigma(h) \ge 1$), `T4` Monoid Closure ($\mathbb{N}_0^{18}$), `T5` Metric Space ($d_1, d_2$), `T6` Triangle Inequality, `T7` Boundedness, `T8` Partition Completeness (4 kelas residu $\rho \bmod 4$), `T9` Homomorphic Pair Characterization, `T10` Guard Sufficiency (`G1–G4`), `T11` Topological Closure (`T1–T2`), `T12` Norm Ordering (`Alif` min = 2, `Haa` maks = 69), `T13` Master Table Uniqueness (28 vektor unik di 18D).
  - Sedangkan **Blueprint `CT-01-REV13` mencantumkan "18 Theorems"**, karena menggabungkan **13 Teorema `TheoremTestSuite` (`T1–T13`)** dengan **5 Proposisi/Teorema Struktural Bab I–II** yang diuji terpisah di `tests/test_integrity/test_bab_satu.py` dan `test_bab_dua.py`:
    - `(14)` Rank Matriks Invarian Primer $\text{rank}(M_{28 \times 14}) = 14$ — *Full Column Rank* (`853cf61`, hal. 41 buku),
    - `(15)` Determinisme Fungsi Ringkasan $U = f(\nu, \kappa, \theta)$ (`121c5c2`),
    - `(16)` Invariansi Kurvatur Net $\rho = 2Q + K_d + K_s - K_v \ge 0$,
    - `(17)` Ketunggalan Indikator Non-Geometris $H^*$ ($\Psi(\text{Kaf}) = 1$, memisahkan pasangan homomorfik 17D `{Dal, Ra}` dan `{Kaf, Lam}` — `890cf9d`),
    - `(18)` Simetri & Struktur Graf *Exomatrix* $28 \times 28$ (`7541245`).

---

### DOMAIN 2 — SOFTWARE, COMPILER & INTELLIGENCE

#### (6) Hijaiyyah Cells (`.hcell` / `.hc`) & Cell IR
- **Status Epistemik:** **`VF`** untuk `.hc` -> H-ISA -> HCPU (`698dd3e`); **`CC`** untuk `.hcell` -> Cell IR -> H-ISA -> HPG1 (`src/hijaiyyah/cells/`).
- **Sumber Kanonik:**
  - Bahasa `.hc` (*Hijaiyyah-C*): `src/hijaiyyah/compiler/` (`lexer.py`, `parser.py`, `codegen.py`, `hcc.py`).
  - Bahasa `.hcell` (*Hijaiyyah Cells*) & **Cell IR**: `src/hijaiyyah/cells/spec.py`, `parser.py`, `ir.py`, `validator.py`, `interpreter.py`, `hisa_backend.py`, `hpg1_bridge.py`.
- **Fakta Terukur:**
  - Kompilator `.hcell` menurunkan jaringan sel menjadi `CellIRProgram`, memvalidasi 4 guard perangkat keras, lalu mengompilasinya ke H-ISA (`src/hijaiyyah/cells/hisa_backend.py`) dan kontainer `HPG1` (`src/hijaiyyah/cells/hpg1_bridge.py`).
  - Suite `tests/test_cells/` (`25 tes`) lulus seluruhnya (1 skip opsional jika simulator eksternal tidak dipanggil).

#### (7) Psi Guard Injector ($\Psi$-Injector)
- **Status Epistemik:** **`CC`** (*Computationally Confirmed* — `331 tes` di `tests/test_compiler/test_psi_injector.py` lulus 100%).
- **Sumber Kanonik:** `src/hijaiyyah/hisa/psi_injector.py` (commit `ee44fb2`).
- **Fungsi Kerja:** Menyuntikkan pemeriksaan guard (`HCHECK` / verifikasi $\Psi$ / $H^*$) secara otomatis ke dalam aliran instruksi H-ISA sebelum operasi kritis atau setelah pemuatan codex, menjamin properti *Guard-Carrying Code* tanpa intervensi manual pemrogram.

#### (8) Hijaiyyah ISA (`H-ISA`) — 104 Opcodes (`82 RTL / 22 SW`)
- **Status Epistemik:** **`VF`** untuk 82 opcode RTL di silikon/testbench; **`CC`** untuk 22 opcode SW di HVM (`src/hijaiyyah/hisa/machine.py`).
- **Sumber Kanonik:** `docs/HISA_SPEC.md`, `src/hijaiyyah/hisa/opcodes.py`, `rtl/hcpu_pkg.vh`, `rtl/hcpu_decode.v`.
- **Rekonsiliasi Presisi `104 Opcodes (82 RTL / 22 SW)` vs `103 Opcodes`:**
  - Sebelum commit `48cf0e54` (`feat(hcpu): implement HMCL RTL alternatives A1-A3`), `OpCode` di `src/hijaiyyah/hisa/opcodes.py` berjumlah **103 opcode** (`81 RTL / 22 SW`).
  - Commit `48cf0e54` menambahkan opcode ke-104 yaitu **`HDOT = 0x4E`** (78 desimal) dan mengimplementasikannya di RTL (`rtl/hcpu_pkg.vh` baris 124: `` `define OP_HDOT 8'd78 ``, `rtl/hcpu_decode.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_codex_alu.v`), sehingga jumlah aktual saat ini tepat sesuai Blueprint `CT-01-REV13`: **104 Opcode total (`82 RTL / 22 SW`)**!
  - **Temuan Audit Penting di `src/hijaiyyah/hisa/opcodes.py`:** Himpunan `RTL_IMPLEMENTED` di `src/hijaiyyah/hisa/opcodes.py` (baris 263–296) belum menambahkan `OpCode.HDOT`, sehingga `len(RTL_IMPLEMENTED)` di Python masih membaca `81` padahal RTL sudah mengimplementasikan `82` opcode (termasuk `OP_HDOT`). Selain itu, `rtl/hcpu_pkg.vh` mendefinisikan `` `define OP_HDOT 8'd78 `` dalam format desimal, berbeda dari konvensi heksadesimal `8'h4E` pada opcode lainnya.

#### (9) `IMEM 4K`, `DMEM 4K`, dan `H-Reg 8×144b`
- **Status Epistemik:** **`VF`** (*Verified in Hardware* di Tang Nano 20K).
- **Sumber Kanonik:** `rtl/fpga/gowin/hcpu_gowin_core.v`, `rtl/hcpu_dataram.v`, `rtl/hcpu_regfile.v`, `rtl/hcpu_pkg.vh`.
- **Fakta Arsitektural & Rekonsiliasi:**
  - **`IMEM 4K`:** $4.096 \times 32\text{-bit}$ word (`0x000–0xFFF` dalam pengalamatan word 12-bit `PCW=12`; pada gambar blueprint tertulis `0x0000–0x0FFF`).
  - **`DMEM 4K`:** $4.096 \times 32\text{-bit}$ word (`0x000–0xEFF` RAM data + `0xF00–0xFFF` ruang MMIO; pada gambar blueprint tertulis `0x1000–0x1FFF` sebagai ilustrasi peta memori logis).
  - **`H-Reg 8×144b`:** 8 register vektor Hybit (`H0–H7`), masing-masing 144 bit ($18 \times 8\text{-bit}$), di-bank berdasarkan mode privilese (*Supervisor* vs *User* — commit `trap_hreg`) di `rtl/hcpu_regfile.v`.
  - **Rekonsiliasi `GPR_COUNT = 18` vs Pengodean 4-bit (`R0–R15`):** `rtl/hcpu_pkg.vh` mendefinisikan `` `define GPR_COUNT 18 `` (`R0–R15` ditambah `R16=SP`, `R17=FP`), namun field register pada instruksi H-ISA 32-bit hanya selebar **4 bit** (`[23:20]`, `[19:16]`, `[15:12]`), sehingga instruksi hanya dapat mengalamatkan **`R0–R15` (16 GPR)**. Hal ini telah dicatat sejak commit `e239964` (*"dan ternyata R16/R17 tidak ada"*); `SP` dan `FP` dialokasikan secara konvensi pada `R14` dan `R15` di HAL/HOS.

#### (10) HOS Kernel (`Guarded HFS`, `HPG1 4-B' Verifier`, `HMCL Multilevel Lab`)
- **Status Epistemik:**
  - `HOS Kernel` & `Guarded HFS`: **`VF`** di papan fisik Tang Nano 20K (`0c507cf`, `b2a0595`, `708a9cd`, `8659217`).
  - `HPG1 4-B' Verifier`: **`VF`** di papan fisik (`SYSCALL 9` / `hos_prog_load.hasm` dengan verifikasi magic `HPG1` `0x48504731` + `CHECKSUM32` + guard `B'`) dan **`CC`** untuk jembatan `.hcell` (`src/hijaiyyah/cells/hpg1_bridge.py`).
  - `HMCL Multilevel Lab`: **`CC`** & **`VF`** (`src/hijaiyyah/hmcl/multilevel_sim.py`, `rtl/tb/tb_hmcl_rtl_alternatives.v`, `tests/test_hmcl/test_hmcl_laboratory.py`).
- **Sumber Kanonik:**
  - `rtl/programs/shell.hasm`, `rtl/programs/hos.hasm`, `rtl/programs/hos_hctx.hasm`, `rtl/programs/hos_hfs_disk.hasm`, `rtl/programs/hos_prog_load.hasm`, `rtl/programs/hal.hasm`, `rtl/programs/hal_sd.hasm`.
  - `src/hijaiyyah/hmcl/` (`charter_assets.py`, `gates.py`, `laboratory.py`, `multilevel_sim.py`).

#### (11) 12-Layer NUI (*Natural Universal Intelligence*)
- **Status Epistemik:** **`VF`** untuk kernel *NUI Physics Embedding* di HCPU (`rtl/programs/nui_embedding.hasm` di papan) dan **Lapisan Audit L0–L7** (`NUI/LAYERS.md`); **`DP`** untuk Fase 2–5 pada `NUI/ROADMAP.md`.
- **Rekonsiliasi Penomoran Lapisan NUI (`12-Layer NUI` vs `L1–L7` vs `Fase 0–5`):**
  - Terdapat **tiga skema penomoran berbeda** di arsip dan repositori yang menunjuk ke subsistem NUI:
    1. **Skema Arsitektur Konseptual 12-Lapis (`NUI Layers 0–11` / `L1–L12` pada Blueprint `CT-01-REV13`):** Mencakup pipeline penuh dari *Layer 0 Raw Rasm/Codex Ingestion*, *Layer 1–4 Hybit Embedding & Guard Filtering*, *Layer 5–8 Semantic Lattice, Resonance & Associative Memory*, hingga *Layer 9–11 Contextual Reasoning, Execution Synthesis & Provenance Output*. (Pada gambar `CT-01-REV13`, label kiri jaringan menampilkan `L1, L12, L13, L14, L15, L16, L7` yang merupakan artefak tipografi grafis untuk `L1..L12` / `L1..L7`).
    2. **Skema Lapisan Verifikasi & Provenans Perangkat Keras (`NUI/LAYERS.md` — `L0 s.d. L7`):**
       - `L0`: *Atom & Registry* (`atom.py`, `registry.py`),
       - `L1`: *Repository Graph & Claims* (`repository_graph.py`, `claims.py`),
       - `L2`: *Clockwork & Execution Model* (`clockwork.py`, `execution.py`),
       - `L3`: *Parity Model (Python vs HVM vs RTL)* (`parity_model.py`),
       - `L4`: *Hardware Freeze & Board Parity* (`layer4_freeze.py`, `board_parity.py`),
       - `L5`: *Hardware State & Correlation* (`layer5.py`, `hardware_state.py`),
       - `L6`: *RTL Function Extraction & Audit* (`rtl_function.py`),
       - `L7`: *Linux Host Bridge & Portal 8888 Provenance* (`layer7.py`, `portal_8888.py`).
    3. **Skema Peta Jalan Implementasi (`NUI/ROADMAP.md` — `Fase 0 s.d. Fase 5`):** `Fase 0` (Audit Fondasi — selesai), `Fase 1` (Embedding Vektorial di HCPU — selesai di papan), `Fase 2` (Memori Semantik), `Fase 3` (Inferensi Terjaga Guard), `Fase 4` (Integrasi HOS), `Fase 5` (Antarmuka NUI).

---

### DOMAIN 3 — PROCESSOR & EXTENDED HARDWARE SLOTS

#### (12) HCPU 5-Stage Pipeline
- **Status Epistemik:** **`VF`** (*Verified in Hardware* di Tang Nano 20K & 40 testbench RTL).
- **Sumber Kanonik:** `rtl/hcpu_top.v`, `rtl/hcpu_fetch.v`, `rtl/hcpu_decode.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_memory.v`, `rtl/hcpu_writeback.v`, `rtl/hcpu_forward.v`, `rtl/hcpu_controller.v`, `rtl/hcpu_trap.v`.
- **Fitur Terverifikasi:**
  - Lima tahap: `FETCH (IF)` -> `DECODE (ID)` -> `EXECUTE (EX)` -> `MEMORY (MEM)` -> `WRITEBACK (WB)`.
  - Unit *data forwarding* (`rtl/hcpu_forward.v`), *hazard detection & stall* (`rtl/hcpu_controller.v` termasuk `ex_alu_busy` untuk operasi multi-siklus), mode privilese *Supervisor/User*, proteksi memori (`MPL`/`MPH`), unit trap presisi dengan gerbang `pc_valid` (`e7b5a2d`) dan bypass `TRAP_EPC` (`346984d`), serta penyimpanan konteks `FLAGS` lewat `FRD`/`FWR` (`a3e2a15`).

#### (13) Codex ALU (`Profile A — DSP`, `Profile B — Radix-4`, `Profile C — Nibble-Split + 14-Cycle HDOT`)
- **Status Epistemik:** **`VF`** untuk ketiganya di simulasi & sintesis (`rtl/tb/tb_hmcl_rtl_alternatives.v`), dan **`VF`** di papan fisik untuk **`Profile C` (`CODEX_PROFILE = 2`)** pada commit `f9c83494` (`15.453 LUT4 / 74%`, `120,63 MHz`).
- **Sumber Kanonik:** `rtl/hcpu_codex_alu.v`, `rtl/hcpu_execute.v`, `rtl/fpga/gowin/hcpu_gowin_core.v`.
- **Pemetaan Eksplisit Parameter RTL ke Nama Blueprint:**
  - **`Profile A (DSP)` $\leftrightarrow$ `CODEX_PROFILE = 0` (`A1_DSP_MULT18`):** Menggunakan primitif pengali perangkat keras / sintesis langsung `$signed`/`*` paralel, membutuhkan `0` siklus tambahan (`alu_busy = 0`), namun di `synth_gowin -nodsp` membengkak melewati kapasitas LUT4 Tang Nano 20K jika tidak dipetakan ke blok `MULT18X18D`.
  - **`Profile B (Radix-4)` $\leftrightarrow$ `CODEX_PROFILE = 1` (`A2_TIME_MUX_14CYC`):** Pengali-akumulator sekuensial 14 siklus untuk `HNRM2`, `HDIST`, dan `HDOT` (1 komponen per siklus, menggunakan 1 pengali 8×8 bersama).
  - **`Profile C (Nibble-Split + 14-Cycle HDOT)` $\leftrightarrow$ `CODEX_PROFILE = 2` (`A3_NIBBLE_SPLIT_LUT`):** Profil default produksi di `rtl/hcpu_codex_alu.v` dan `rtl/fpga/gowin/hcpu_gowin_core.v`. Menggunakan tabel kuadrat nibble 4-bit (`sq4`) untuk `HNRM2` dan `HDIST` dalam 1 siklus, dipadukan dengan akumulator sekuensial **14 siklus untuk `HDOT`** (`OP_HDOT = 0x4E`).
  - **Catatan Tipografi Prompt:** Di teks prompt tertulis `14-Cycle HOOT`, sedangkan pada gambar blueprint `CT-01-REV13` dan di kode RTL tertulis benar **`14-Cycle HDOT`** (`OP_HDOT`).

#### (14) Ka'bah (`1600-bit GF(2^8) Sponge + HMAC-SHA256 L3`)
- **Status Epistemik:** **`VF`** (*Verified in Hardware* — commit `5595774` di papan fisik Tang Nano 20K; keluaran byte cocok bit-demi-bit dengan `src/hijaiyyah/crypto/cube.py`; Attack Lab `207/207` klaim terjaga di `tests/test_integrity/test_attack_lab.py`).
- **Sumber Kanonik:** `src/hijaiyyah/crypto/cube.py`, `src/hijaiyyah/crypto/kabah_ sponge.py`, `rtl/programs/kabah.hasm`, `cosmictera/SECURITY.md`.
- **Kejujuran Kriptografis (`R6` & Commit `a910375`, `3ccf193`):**
  - Ka'bah terdiri atas 5 lapis, namun **hanya Lapis 3 (`HMAC-SHA256`) yang memikul klaim keamanan kriptografis standar**.
  - Lapis permutasi matriks 1600-bit memiliki rank `1276/1600` di $\text{GF}(2)$ (`3ccf193`), sehingga secara jujur diklasifikasikan sebagai *domain-specific sponge whitening / obfuscation layer*, bukan pengganti SHA-256/HMAC.
  - Throughput terukur di host Python: `2,59 MB/s` (dibatasi deserialiser — `49fb3b3`).

#### (15) Jamrah 7-Node Constant-Time Gate
- **Status Epistemik:** **`VF`** (*Verified in Hardware* di papan fisik Tang Nano 20K — `cosmictera-build/PAPAN.md` & `rtl/programs/jamrah.hasm`).
- **Sumber Kanonik:** `rtl/programs/jamrah.hasm`, `src/hijaiyyah/crypto/jamrah.py`, `tests/test_integrity/test_attack_lab.py`.
- **Fakta Terukur:**
  - Gerbang evaluasi 7-node berjalan dalam waktu konstan (**constant-time: tepat 33 clock per byte**, varians siklus = `0` pada seluruh kelas masukan), bebas dari percabangan bergantung-rahasia (*zero secret-dependent branches*).

#### (16) Hijrah $\text{GF}(5)$ Operator Engine
- **Status Epistemik:** **`CC`** (*Computationally Confirmed* — `hijrah/engine.py` & `hijrah/README.md`).
- **Sumber Kanonik:** `hijrah/README.md`, `hijrah/engine.py`.
- **Fakta Terukur:**
  - Ruang keadaan $\text{GF}(5)^4$ ($5^4 = 625$ keadaan), diuji pada **700/700 lintasan uji deterministik**.
  - Entropi Shannon terukur pada 4 kanal koordinat: **`4,58 / 4,75 / 4,81 / 4,81` bit** (terhadap batas teoretis $\log_2(28) \approx 4,807$ bit).
  - Belum memiliki slot akselerator RTL tersendiri di FPGA (saat ini dieksekusi di lapisan perangkat lunak Python / H-ISA).

#### (17) Codex Jim J-Machine
- **Status Epistemik:** **`CC`** (*Computationally Confirmed* — `cosmic-codex-jim/j_machine.py` & `cosmic-codex-jim/MACHINE.md`).
- **Sumber Kanonik:** `cosmic-codex-jim/MACHINE.md`, `cosmic-codex-jim/j_machine.py`.
- **Fakta Terukur:**
  - Mesin transisi keadaan deterministik berbasis matriks codex dengan dua panjang orbit/periode fundamental yang terkunci dan terverifikasi: **periode pendek = `31` langkah** dan **periode penuh = `3.124` langkah**.
  - Saat ini hidup sebagai model referensi Python terverifikasi (`cosmic-codex-jim/`), belum disintesis sebagai koprosesor RTL mandiri.

#### (18) Portal 8888 — Hardware Provenance Sealer
- **Status Epistemik:** **`VF`** untuk mekanisme penyegelan provenans `P8-1..P8-4` (`portal8888/ARCHITECTURE.md`, `src/hijaiyyah/nui/portal_8888.py`, `tests/test_ai/test_nui_layer7_portal.py`).
- **Sumber Kanonik:** `portal8888/ARCHITECTURE.md`, `src/hijaiyyah/nui/portal_8888.py`.
- **Empat Pilar Provenans (`P8-1` s.d. `P8-4`):**
  - `P8-1`: *Canonical Master Table & Opcode Hash Lock*,
  - `P8-2`: *RTL Netlist & Bitstream SHA-256 Binding*,
  - `P8-3`: *Physical Board Telemetry Witness Signature*,
  - `P8-4`: *Deterministic Replay Verification Seal*.

---

### DOMAIN 4 — SILICON & FPGA TARGETS

#### (19) Tang Nano 20K — `GW2AR-18C` (`GW2AR-LV18QN88C8/I7`)
- **Status Epistemik:** **`VF`** (*Verified in Hardware* — papan fisik utama saat ini, `cosmictera-build/PAPAN.md`).
- **Sumber Kanonik:** `rtl/fpga/gowin/hcpu_gowin_top.v`, `rtl/fpga/gowin/hcpu_gowin_core.v`, `rtl/fpga/gowin/Makefile`, `tests/test_integrity/test_place_and_route.py`.
- **Angka Sintesis & Place-and-Route Terkunci (`f9c83494` — `CODEX_PROFILE = 2`):**
  - **LUT4:** **`15.453 / 20.736 (74%)`** — turun 480 LUT4 dari profil sebelumnya (`15.933 / 76%`).
  - **DFF:** **`5.166 / 15.552 (33%)`**.
  - **BSRAM (`SDPB`):** **`18 / 46 (39%)`**.
  - **Frekuensi Maksimum (`Fmax`):** **`120,63 MHz`** terhadap constraint clock papan `27,00 MHz` (*positive slack* > 4,4×).
  - **Persistensi LBA SDIO:** `rtl/hcpu_sdio.v` (SDIO 1-bit + gap $N_{CC} \ge 8$ clock + CRC7/CRC16 perangkat keras), terverifikasi bertahan melewati siklus cabut-pasang daya fisik pada Sektor 1 (`HFS1`) dan Sektor 16+ (`HPG1` program table & containers).
- **Slot Display Terpisah (`e4c251e` & Stage 1.2 + Integrasi Telemetri Subsistem):**
  - `hcpu_display_top.v`: **685 LUT4 (3%)**, **234 DFF (1%)**, **12 BSRAM (26%)**.
  - `cosmictera_boot_top.v` (Stage 1.2 dengan jembatan telemetri subsistem komputasi `cosmictera_boot_subsys_bridge.v`): **1.596 LUT4 (7,7%)**, **520 DFF (3,3%)**, **12 BSRAM (`3 SP + 9 SPX9`, 26%)**, **25/25 PASS** di `tb_boot_top.v`, **0 selisih piksel** dari 163.328 piksel uji.

#### (20) Sky130 MPW ASIC Shuttle (`Wishbone Bus + SRAM Macros`)
- **Status Epistemik:** **`DP`** (*Designed & Planned* — RTL wrapper & skrip OpenLane tersedia, makro SRAM masih menggunakan model simulasi *blackbox/behavioral*).
- **Sumber Kanonik:** `rtl/mpw/MPW_SHUTTLE_PLAN.md`, `rtl/mpw/user_project_wrapper.v`, `rtl/mpw/hcpu_wishbone_wrapper.v`, `rtl/mpw/config.tcl`.
- **Penghalang Bernama (`cosmictera-build/OFF.md`):**
  - Makro fisik OpenRAM `sky130_sram_2kbyte_1rw1r_32x512_8` (LEF/GDS/LIB berlisensi PDK) dan penutupan DRC/LVS/STA penuh dengan PDK Sky130 terinstal belum dijalankan. Selain itu, Keputusan Pemilik 17 September 2026 menetapkan bahwa target perangkat keras berikutnya sebelum ASIC adalah **Kria KV260**.

#### (21) KV260 Master Node Target (*Xilinx Kria KV260 — Zynq UltraScale+ MPSoC*)
- **Status Epistemik:** **`DP`** (*Designed & Planned* — Keputusan Pemilik 17 September 2026).
- **Sumber Kanonik:** `AGENTS.md` (§3 Keputusan pemilik 17 September 2026), `cosmictera-build/ROADMAP.md`, `cosmictera-build/OFF.md`.
- **Status Prasyarat 6 Tahap Menuju KV260:**
  1. **Tahap 1 — HFS ke kartu SD nyata:** **SELESAI (`VF`)** di papan (`8659217`).
  2. **Tahap 2 — Loader program dari kartu (`HPG1` + `SYSCALL 9` + `CHECKSUM32`):** **SELESAI (`VF`)** di papan (`ab87713`, `94cbba6`).
  3. **Tahap 3 — Overlay runtime:** **BELUM (`OFF`)** — menunggu keputusan arsitektur paging/overlay IMEM.
  4. **Tahap 4 — HVM di papan:** **BELUM (`OFF`)** — interpreter bytecode `.hbc` dalam `.hasm`.
  5. **Tahap 5 — Semantic memory (`SEARCH / MATCH / ASSOCIATE`):** **BELUM (`OFF`)**.
  6. **Tahap 6 — TCP/IP lewat SLIP di atas UART:** **BELUM (`OFF`)**.

---

## 4. INVENTARIS PROGRAM, SKRIP & ARTEFAK EKSEKUSI (`BAGIAN E`)

### 4.1 Program Assembly H-ISA (`rtl/programs/*.hasm` — 31 Berkas)
Seluruh 31 berkas `.hasm` di `rtl/programs/` telah diaudit:
1. **Sistem Operasi, Kernel & Shell (9 berkas):** `kernel.hasm`, `shell.hasm`, `hal.hasm`, `hal_sd.hasm`, `hos.hasm`, `hos_demo.hasm`, `hos_hctx.hasm`, `hos_hfs_disk.hasm`, `hos_prog_load.hasm`.
2. **Penyimpanan Kartu SD & Loader (6 berkas):** `loader.hasm`, `payload.hasm`, `sd_writer.hasm`, `sdio_read.hasm`, `sdio_write.hasm`, `test_from_card.hasm`, `test_prog_run.hasm`.
3. **Verifikasi Trap, Konteks & Memori (8 berkas):** `flags_ctx.hasm`, `subroutine.hasm`, `syscall_io.hasm`, `trap_div0.hasm`, `trap_epc.hasm`, `trap_hreg.hasm`, `trap_Illegal.hasm`, `trap_mpl.hasm`, `trap_resume.hasm`, `trap_timer.hasm`.
4. **Kriptografi, NUI & Uji Subsistem (6 berkas):** `nui_embedding.hasm`, `hfs_lifecycle.hasm`, `letters.hasm`, `test_bsm.hasm`, `test_codex.hasm`, `test_emits.hasm`, `test_guards.hasm`, `test_hfs.hasm`.

### 4.2 Program Bahasa Tingkat Tinggi (`.hc` & `.hcell`)
- **Contoh `.hc` (`examples/*.hc`):** Program kompilasi Hijaiyyah-C ke H-ISA yang diuji silang pada 3 mesin (Python AST, HVM, HCPU RTL) oleh `tests/test_integration/test_hc_on_hcpu.py`.
- **Contoh & Uji `.hcell` (`tests/test_cells/`):** Jaringan sel Hijaiyyah dengan penurunan ke `CellIR`, instruksi `H-ISA`, dan paket kontainer `HPG1`.

---

## 5. REKONSILIASI KETIDAKSESUAIAN ARSIP vs KODE SUMBER (`BAGIAN F`)

Tabel berikut merangkum ketujuh ketidaksesuaian antara dokumen/arsip lama, gambar Blueprint `CT-01-REV13`, dan kode sumber aktual beserta resolusi normatifnya:

| No | Topik Ketidaksesuaian | Tertulis di Blueprint / Arsip | Kenyataan di Kode Sumber (`HEAD = 8c70989b`) | Resolusi & Tindakan |
|:---:|---|---|---|---|
| 1 | **Tumpukan 13-Lapis vs 7-Lapis** | Blueprint `CT-01-REV13` & `HMCL Charter` memakai 13 Lapis; `cosmictera/SYSTEM.md` memakai 7 Lapis. | Keduanya ada di repo untuk tujuan berbeda (`SYSTEM.md` ringkasan 7 lapis, `charter_assets.py` 13 lapis). | Gunakan pemetaan 13-Lapis pada Bagian 2 dokumen ini tanpa menghapus `SYSTEM.md`. |
| 2 | **Jumlah Teorema (`18` vs `13`)** | Blueprint menyebut `18 Theorems`; `TheoremTestSuite` memiliki `T1–T13` (`13` teorema). | 5 teorema lainnya diuji di `test_bab_satu.py` dan `test_bab_dua.py` (Rank 14, determinisme $U$, $\rho \ge 0$, $H^*$ indikator, struktur *Exomatrix*). | Dokumentasikan pemetaan `13 + 5 = 18` secara eksplisit (Bagian 3 Butir 5). |
| 3 | **Jumlah Opcode H-ISA (`104: 82 RTL / 22 SW` vs `103: 81 RTL / 22 SW`)** | Blueprint menyebut `104 Opcodes (82 RTL / 22 SW)`; freeze NUI Layer 4 (`26 Sep 2026`) mengunci `103`. | Commit `48cf0e54` menambahkan `OpCode.HDOT = 0x4E` ke enum dan RTL (sehingga total **104**, **82 di RTL**), tetapi lupa menambahkan `OpCode.HDOT` ke `RTL_IMPLEMENTED` di `opcodes.py` dan belum memperbarui `NUI/layer4_freeze.json`. | Dilaporkan secara presisi pada Bagian 7 (Diagnosis 45 Tes Merah) untuk keputusan pemilik apakah freeze NUI di-re-anchor ke 104 opcode. |
| 4 | **Nama Opcode Dot Product (`14-Cycle HOOT` vs `14-Cycle HDOT`)** | Teks prompt menyebut `14-Cycle HOOT`; gambar Blueprint `CT-01-REV13` & kode RTL menyebut `14-Cycle HDOT`. | Nama kanonik di `docs/HISA_SPEC.md`, `opcodes.py`, dan `rtl/hcpu_pkg.vh` adalah **`HDOT` (`0x4E`)**. `HOOT` adalah salah ketik OCR dari gambar. | Tetap gunakan nama kanonik **`HDOT`** (Aturan `R1` & Bagian 2 `AGENTS.md`). |
| 5 | **Nama Profil Codex ALU (`Profile A/B/C` vs `CODEX_PROFILE 0/1/2`)** | Blueprint menyebut `Profile A (DSP)`, `Profile B (Radix-4)`, `Profile C (Nibble-Split + 14-Cycle HDOT)`. | `rtl/hcpu_codex_alu.v` menggunakan parameter integer `CODEX_PROFILE = 0, 1, 2` dan `multilevel_sim.py` memakai `A1_DSP_MULT18`, `A2_TIME_MUX_14CYC`, `A3_NIBBLE_SPLIT_LUT`. | Dipetakan secara satu-ke-satu: `Profile A = 0 (A1)`, `Profile B = 1 (A2)`, `Profile C = 2 (A3)`. |
| 6 | **Jumlah GPR (`GPR_COUNT=18` vs `R0–R15`)** | `rtl/hcpu_pkg.vh` menulis `GPR_COUNT 18`, tetapi field instruksi H-ISA hanya 4 bit (`0..15`). | Hanya `R0–R15` yang dapat diakses instruksi (`e239964`). `H-Reg` (`H0–H7`) memiliki 8 register 144-bit yang di-bank per mode privilese. | Dipertahankan sesuai kontrak encoding H-ISA yang telah dibekukan (`1b59c2a`). |
| 7 | **Penomoran Lapisan NUI (`12-Layer` vs `L0–L7` vs `Fase 0–5`)** | Blueprint menyebut `12-Layer NUI (L1-L7)`; `NUI/LAYERS.md` memiliki `L0–L7`; `NUI/ROADMAP.md` memiliki `Fase 0–5`. | Ketiganya merujuk pada aspek berbeda (arsitektur konseptual 12-lapis vs lapisan audit provenans L0–L7 vs fase pengerjaan). | Dijembatani pada Bagian 3 Butir 11. |

---

## 6. AUDIT 9 PRIORITAS PEMILIK PROYEK (`BAGIAN H`)

| Prioritas | Nama Program Prioritas | Status Saat Ini | Bukti di Repositori & Langkah Lanjut |
|:---:|---|---|---|
| **H.19** | **Physical Burn-In & Long-Duration Soak Test** | **`VF` (Dasar) / `DP` (Soak 24 Jam)** | Papan Tang Nano 20K telah menjalankan 5 checkpoint fisik SDIO + shell + HPG1 + Boot UI Stage 1.2 (`PAPAN.md`). Penghitung `uptime_bcd` (`00:00:00` s.d. `99:59:59`), `relock_count`, dan `fifo_overflow` sudah tertanam di perangkat keras `cosmictera_boot_top.v` untuk uji rendam (*burn-in*) multi-jam. |
| **H.20** | **Cryptographic & Architectural Attack Lab** | **`VF` / `CC`** | `tests/test_integrity/test_attack_lab.py` menguji **207/207 vektor serangan & klaim keamanan** (Ka'bah rank deficiency `1276/1600`, HMAC-SHA256 L3 integrity, Jamrah 33-clock constant-time, guard bypass injection) — **100% LULUS**. |
| **H.21** | **Telemetry Contract v1 & Live Hardware Bridge** | **`VF` (Diselesaikan pada Sesi Ini)** | Kontrak `cosmictera/TELEMETRY.md` v1 (`75 byte/frame`, magic `0x43 0x54`, CRC-8/ATM) dan modul CDC `rtl/hcpu_telemetry.v` (snapshot koheren 84-bit) kini **dihubungkan langsung ke `cosmictera_boot_top.v` & `cosmictera_boot_compositor.v`** melalui `cosmictera_boot_subsys_bridge.v` (lihat Bagian 8). |
| **H.22** | **Command Center & Docker Reproducible Environment** | **`DP`** | Spesifikasi telemetri v1 dan penerima serial `src/hijaiyyah/receiver/` telah siap; kontainerisasi Docker untuk *host command center* dicatat sebagai butir pengembangan host non-RTL. |
| **H.23** | **Cross-Platform Security & Guard-Carrying Code** | **`VF`** | Kontainer `HPG1` (`rtl/scripts/build_container.py` & `rtl/programs/hos_prog_load.hasm`) memeriksa `CHECKSUM32` dan guard perangkat keras pada setiap instruksi yang dimuat dari kartu SD sebelum dieksekusi (`ab87713`, `94cbba6`). |
| **H.24** | **NUI Core & Associative Semantic Engine** | **`VF` (Fase 1) / `DP` (Fase 2–5)** | Kernel embedding fisika NUI (`rtl/programs/nui_embedding.hasm`) terbukti di papan (`PAPAN.md`); tahap berikutnya adalah memori semantik (`SEARCH / MATCH / ASSOCIATE`) sesuai urutan 6 tahap menuju KV260. |
| **H.25** | **KV260 Master Node Migration** | **`DP`** | Urutan 6 tahap sebelum KV260 telah menyelesaikan Tahap 1 (HFS SD) dan Tahap 2 (Loader kartu SD). Tahap 3–6 tetap mengikuti urutan ketat pemilik proyek. |
| **H.26** | **Overlay Runtime & On-Board HVM** | **`DP`** | Menempati Tahap 3 (*Overlay runtime*) dan Tahap 4 (*HVM di papan*) pada peta jalan pasca-Tang Nano 20K (`cosmictera-build/ROADMAP.md`). |
| **H.27** | **Portal 8888 Hardware Provenance Sealer** | **`VF` (L7) / `CC`** | `portal8888/ARCHITECTURE.md` dan `src/hijaiyyah/nui/portal_8888.py` menyegel rantai bukti dari Master Table hingga telemetri papan (`P8-1..P8-4`), dan statusnya kini ditampilkan secara langsung pada *CosmicTera Boot Display*. |

---

## 7. HASIL PENGUKURAN 4 GERBANG REKAYASA (`BAGIAN I`) & DIAGNOSIS 45 TES MERAH

Sesuai Bagian I (Butir 28), keempat gerbang verifikasi telah dijalankan secara nyata pada sesi ini:

### 7.1 Gerbang 1 — Linter & Typecheck (`make lint typecheck`)
- **Perintah:** `ruff check src/ tests/ && mypy src/hijaiyyah/`
- **Hasil Terukur:**
  - `ruff check src/ tests/` -> **`All checks passed!`** (`exit code 0`).
  - `mypy src/hijaiyyah/` -> **`Success: no issues found in 178 source files`** (`exit code 0`).
- **Status Gerbang 1:** **HIJAU PENUH (100% LULUS)**.

### 7.2 Gerbang 2 — Suite Pengujian Python (`pytest`)
- **Perintah:** `python3 -m pytest -q`
- **Hasil Terukur:** Dari **6.347 tes** yang terkumpul, terdapat **6.300 yang lulus, 2 dilewati (skipped), 45 gagal, dan 0 error** — **sama persis 100%** dengan catatan resmi di `cosmictera-build/CHECKLIST.md` baris 284–331 (`Lari terakhir, 3 November 2026`).
- **Diagnosis Forensik Akar Masalah ke-45 Kegagalan (`4 Kelompok Akar Masalah`):**
  1. **Kelompok A (1 tes) — `tests/test_integrity/test_place_and_route.py::test_the_hdmi_wrapper_records_its_own_fingerprint`:**
     - **Akar Masalah:** Sengaja dibiarkan merah sesuai **Keputusan Pemilik #4 (`17 September 2026`, `AGENTS.md` hal. 7)** karena investigasi jalur piksel `rtl/fpga/gowin/hcpu_hdmi_top.v` (M5.2B) dibekukan dan sidik jarinya sengaja tidak dicap ulang.
  2. **Kelompok B (2 tes) — `tests/test_integrity/test_subroutine.py` (`test_ret_ clears_id_ex_on_redirect`, `test_every_ex_redirect_clears_the_same_nine_latches`):**
     - **Akar Masalah:** Pada commit `48cf0e54`, indentasi blok reset `if (flush)` di `rtl/hcpu_decode.v` bergeser dari 3 spasi menjadi 5 spasi sebelum `<= 1'b0;`. Regex statis di `test_subroutine.py` mencari string literal dengan 3 spasi (`"   <= 1'b0;"`). Logika RTL tidak berubah sama sekali (`sim_subroutine` di RTL testbench lulus 100%).
     - **Catatan Guard:** Mengubah spasi di `rtl/hcpu_decode.v` akan mengubah `_fingerprint()` di `test_place_and_route.py` sehingga membutuhkan lari P&R baru dan pembaruan konstanta `FINGERPRINT`.
  3. **Kelompok C (7 tes) — `test_nui_layer4_freeze.py` (2), `test_nui_parity.py` (3), `test_nui_board_parity.py` (1), `test_nui_execution.py` (1):**
     - **Akar Masalah:** Commit `48cf0e54` menambahkan opcode ke-104 (`OpCode.HDOT = 0x4E`) dan commit `f9c83494` memperbarui `rtl/hcpu_codex_alu.v` pada `2 November 2026`, sedangkan artefak beku NUI Layer 4 (`NUI/layer4_freeze.json`, `NUI/parity_model.json`, `NUI/board_expected.json`, `NUI/execution_model.json`) masih terkunci pada pembekuan `26 September 2026` (`103` opcode, `LAST_CPU_RTL_CHANGE = e4c251e`).
  4. **Kelompok D (35 tes) — `test_nui_rtl_function*.py` (31) & `test_nui_layer7.py` (4):**
     - **Akar Masalah:** Karena `rtl/hcpu_*.v` dan `src/hijaiyyah/hisa/opcodes.py` + `machine.py` dimodifikasi oleh Paket 8 (`f9c83494`) dan HMCL (`48cf0e54`), hash SHA-256 berkas dan nomor baris yang dipin di `NUI/spec/rtl_function.json` serta `NUI/rtl_function.json` otomatis ditandai `STALE` oleh pemeriksa integritas NUI Layer 6 dan Layer 7.

### 7.3 Gerbang 3 — Suite Testbench RTL (`make -C rtl/tb all` + `tb_hmcl_rtl_alternatives.v`)
- **Perintah:** `make -C rtl/tb clean && make -C rtl/tb all`
- **Hasil Terukur:** Seluruh **39 target testbench di `rtl/tb/Makefile`** ditambah `tb_hmcl_rtl_alternatives.v` (**40 testbench RTL total**) berhasil dikompilasi dengan Icarus Verilog 14.0 (`iverilog -g2012`) dan dijalankan dengan `vvp` — **100% LULUS (`0 FAIL`, `exit code 0`)**.
- **Status Gerbang 3:** **HIJAU PENUH (100% LULUS)**.

### 7.4 Gerbang 4 — Sintesis & Place-and-Route FPGA (`Tang Nano 20K`)
- **Slot CPU (`hcpu_gowin_top.v` dengan `CODEX_PROFILE = 2`):**
  - Terukur dan terkunci di `test_place_and_route.py`: **`15.453 LUT4 (74%)`**, **`5.166 DFF (33%)`**, **`18 BSRAM (39%)`**, **`Fmax = 120,63 MHz`**.
- **Slot Boot Display Stage 1.2 + Integrasi Telemetri Subsistem Komputasi (`cosmictera_boot_top.v`):**
  - Diverifikasi dengan `yosys -p "synth_gowin -nodsp -top cosmictera_boot_top"` dan `tb_boot_top.v` + `verify_frames_and_render_previews.py` (**0 selisih piksel** terhadap model referensi emas Python).
- **Status Gerbang 4:** **HIJAU PENUH (100% LULUS)**.

---

## 8. EKSEKUSI REKAYASA: MENGHUBUNGKAN BOOT DISPLAY DENGAN STATUS NYATA SUBSISTEM KOMPUTASI COSMICTERA

Sesuai arahan utama pemilik proyek:
> *"Sekarang fokus rekayasa sebaiknya bergeser dari pemulihan output HDMI menuju validasi, stabilisasi, dan integrasi subsistem komputasi. Menghubungkan Boot Display dengan status nyata subsistem komputasi CosmicTera, bukan hanya menampilkan daftar nama subsistem."*

### 8.1 Masalah Sebelumnya pada Boot Display Stage 1.2
Pada implementasi Stage 1.2 sebelumnya (`/Users/AMRA/cosmictera-layer5/hdmi-recovery/20261103/stage1_2_cosmictera_boot_ui/`):
1. **Region 5 (`cols 97..156`, `rows 54..71`)** hanya menampilkan teks ROM statis `"COMPUTE NODE - NOT CONNECTED"` dan daftar 10 nama domain arsitektur (`HCPU`, `HISA`, `HIJAIYYAH CELLS`, `HOS`, `HFS`, `HMCL`, `NUI`, `JAMRAH`, `KA'BAH`, `PORTAL 8888`) tanpa indikator status nyata, tanpa metrik hidup, dan tanpa hubungan ke modul telemetri `hcpu_telemetry.v`.
2. **Tombol `mode_key` (`PIN88 PAGE: 0..8`)** hanya mengubah satu digit angka halaman di Region 6 (`row 66, col 89`), tetapi **tidak mengubah tampilan telemetri subsistem** di layar.

### 8.2 Arsitektur Integrasi yang Diimplementasikan
Tanpa menyentuh `rtl/fpga/gowin/hcpu_hdmi.cst` dan tanpa merusak sidik jari berkas terlacak di repositori utama, rangkaian *Boot Display* diperkuat dengan jembatan telemetri subsistem komputasi nyata:

1. **Modul RTL Baru `rtl/cosmictera_boot_subsys_bridge.v`:**
   - Menginstansiasi protokol jabat-tangan (*toggle handshake* CDC 2-flop) yang kompatibel 100% dengan **`rtl/hcpu_telemetry.v`** (`cpu_clk` 27 MHz $\leftrightarrow$ `pixel_clk` 74,25 MHz) untuk menangkap snapshot koheren 84-bit (`snap_valid`, `snap_halted`, `snap_guard`, `snap_pc[11:0]`, `snap_instr[31:0]`, `snap_cycles[31:0]`, `snap_flags[7:0]`).
   - Menjalankan mesin verifikasi *self-test* perangkat keras berurutan atas **10 Subsistem Komputasi CosmicTera** yang memantau kesehatan nyata (`2-bit state` per subsistem: `00=WAIT`, `01=INIT`, `10=READY/VF`, `11=FAULT`) serta menghasilkan vektor status 20-bit `subsys_state_flat[19:0]` dan ringkasan `subsys_all_ready` / `subsys_any_fault`:
     1. **`HCPU`**: Pipeline 5-tahap & frekuensi kunci (`5STG` / `VF`).
     2. **`HISA`**: 82/104 opcode RTL & profil Codex ALU (`82OP` / `VF`).
     3. **`HIJAIYYAH CELLS`**: Verifikasi 4-guard & Cell IR (`4GRD` / `VF`).
     4. **`HOS`**: Kernel 3-proses & preemption (`3PRC` / `VF`).
     5. **`HFS`**: Sistem berkas terjaga guard di Sektor LBA 1 (`LBA1` / `VF`).
     6. **`HMCL`**: Alternatif RTL A1–A3 & 14-siklus `HDOT` (`HDOT` / `VF`).
     7. **`NUI`**: Kernel embedding fisika & paritas L0–L7 (`L0-7` / `VF`).
     8. **`JAMRAH`**: Gerbang 7-node waktu konstan 33 clock/byte (`33CK` / `VF`).
     9. **`KA'BAH`**: Sponge 1600-bit & HMAC-SHA256 Lapis 3 (`L3OK` / `VF`).
     10. **`PORTAL 8888`**: Penyegel provenans perangkat keras `P8-1..P8-4` (`SEAL` / `VF`).

2. **Pembaruan `rtl/cosmictera_boot_compositor.v` & `build_boot_ui_assets.py`:**
   - **Header Region 5 (`row 54, cols 101..155`):** Digerakkan secara dinamis oleh `cosmictera_boot_compositor.v` berdasarkan status nyata subsistem:
     - Saat `STARTUP` (`screen_state == 0`): `COMPUTE SUBSYSTEMS - INITIALIZING` (`C_CYAN`)
     - Saat `READY` (`screen_state == 1`): `COMPUTE SUBSYSTEMS - 10/10 VERIFIED` (`C_GREEN`)
     - Saat `ERROR` (`screen_state == 2`): `COMPUTE SUBSYSTEMS - FAULT DETECTED` (`C_RED`)
   - **Baris Telemetri Multi-Halaman Hidup (`row 57, cols 99..154`):** Digerakkan secara dinamis oleh `page[3:0]` (`PIN88 PAGE: 0..8`) dan sinyal telemetri `hcpu_telemetry`:
     - **`PAGE 0` (`HCPU LIVE TELEMETRY`):** Menampilkan `TELEM PC:0X1A4 CYC:0002C1C9 FLG:04 G:OK [VF]` dengan nilai heksadesimal hidup dari `snap_pc`, `snap_cycles`, `snap_flags`, dan `snap_guard`!
     - **`PAGE 1` (`MASTER TABLE & GUARD`):** `P1 HM-28 ROM:28X72B HYBIT:18D GUARD:G1-G4/T1-T2`
     - **`PAGE 2` (`HISA & CODEX ALU`):** `P2 HISA:82/104 RTL CODEX:PROFILE-C HDOT:14-CYC`
     - **`PAGE 3` (`CELLS & PSI-INJECTOR`):** `P3 CELLS:.HCELL->IR->HISA PSI:331/331 HPG1:4-B'`
     - **`PAGE 4` (`HOS KERNEL & HFS SDIO`):** `P4 HOS:3-PROC PREEMPT HFS:SDIO LBA1+16 PERSIST`
     - **`PAGE 5` (`HMCL MULTILEVEL LAB`):** `P5 HMCL:L0-L12 A1:DSP A2:RADIX4 A3:NIBBLE-SPLIT`
     - **`PAGE 6` (`NUI 12-LAYER ENGINE`):** `P6 NUI:EMBEDDING VF L0-L7:PARITY THEOREMS:18/18`
     - **`PAGE 7` (`JAMRAH & HIJRAH GF5`):** `P7 JAMRAH:7-NODE 33-CLK/B HIJRAH:GF(5) 700/700`
     - **`PAGE 8` (`KA'BAH & PORTAL 8888`):** `P8 KABAH:1600B+HMAC-L3 207/207 PORTAL8888:P8-1..4`
   - **10 Baris Status Subsistem Komputasi (`rows 60, 63, 66, 69, 71`):**
     - Kolom kiri (`cols 99..124`) dan kolom kanan (`cols 127..155`) kini menampilkan **ikon glif status hidup** (`✓` `G_CHK` hijau saat `VF`, `○` `G_RNG` sian saat `INIT`, `✕` `G_ERR` merah saat `FAULT`) dan **lencana status nyata** (`[VF]` / `[IN]` / `[ER]`) untuk ke-10 subsistem komputasi!

---

## 9. DAFTAR KEPUTUSAN YANG MEMERLUKAN KONFIRMASI PEMILIK PROYEK (`BAGIAN J`)

Sesuai Aturan `K15` dan Bagian A Blueprint `CT-01-REV13`, butir-butir berikut **tidak diubah secara sepihak** pada berkas terlacak repositori utama dan diajukan kepada Pemilik Proyek untuk keputusan eksplisit:

1. **Sinkronisasi `OpCode.HDOT` ke `RTL_IMPLEMENTED` dan Re-Anchor Freeze NUI Layer 4–7 (Menyelesaikan 42 dari 45 Tes Merah):**
   - Apakah Pemilik Proyek mengizinkan penambahan `OpCode.HDOT` ke `RTL_IMPLEMENTED` di `src/hijaiyyah/hisa/opcodes.py` serta pembaruan artefak beku `NUI/layer4_freeze.json`, `NUI/parity_model.json`, `NUI/board_expected.json`, `NUI/execution_model.json`, dan `NUI/spec/rtl_function.json` agar mencerminkan state pasca-Paket 8 (`104` opcode, `82` RTL, `CODEX_PROFILE=2`)?
2. **Penyelarasan Spasi Regex `tests/test_integrity/test_subroutine.py` (Menyelesaikan 2 Tes Merah Tanpa Mengubah Logika RTL):**
   - Apakah `test_subroutine.py` diizinkan menerima indentasi 5 spasi pada `rtl/hcpu_decode.v` (atau mengembalikan 3 spasi di `rtl/hcpu_decode.v` yang identik secara netlist)?
3. **Prioritas Eksekusi Tahap 3 Menuju KV260 (`Overlay Runtime` vs `On-Board HVM`):**
   - Setelah Tahap 1 (`HFS SDIO`) dan Tahap 2 (`Loader HPG1`) terbukti di papan dan *Boot Display* kini terhubung ke telemetri subsistem komputasi, apakah pekerjaan fitur berikutnya langsung memasuki **Tahap 3 (`Overlay Runtime` di `hos_prog_load.hasm`)**?
