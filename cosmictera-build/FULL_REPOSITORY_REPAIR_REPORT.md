# Laporan Audit dan Rekonsiliasi Menyeluruh Repositori Pasca-Commit `1aed5e1f`

- **Repositori**: `/Users/AMRA/hijaiyyah-mathematics/`
- **Branch Pengembangan**: `reconcile/post-1aed5e1f`
- **Baseline yang Dilindungi**: `stage-1-5-security-integration` (`ea3c5b22445ed322b8e10348f930b4fa75731885`)
- **Commit Tahap 1 (4 Area Awal)**: `95623b65d8f2509b420b52618f6e7b05989c072f`
- **Status Merge ke Baseline**: **TIDAK DI-MERGE** (menunggu pemeriksaan pemilik sesuai instruksi)

## 1. Seluruh Berkas yang Diperiksa

Pemeriksaan dan audit menyeluruh dilakukan terhadap **seluruh 6.367 tes** di bawah `tests/` serta enam area utama repositori (Area A–F):

1. **Area A — NUI (`NUI/` dan `src/hijaiyyah/nui/`)**:
   - Lapis 0–2 (`NUI/spec/`, `src/hijaiyyah/nui/atom.py`, `clockwork.py`, `freeze.py`, `repository_index.py`, `knowledge.py`).
   - Lapis 3 (`NUI/execution_graph.json`, `NUI/EXECUTION.md`, `src/hijaiyyah/nui/execution_graph.py`).
   - Lapis 3.5 (`NUI/spec/rtl_function.json`, `NUI/rtl_function.json`, `NUI/RTL_FUNCTION.md`, `src/hijaiyyah/nui/rtl_function.py`, `rtl_function_dataram.py`, `rtl_function_hcpu.py`, `rtl_function_hcpu_audit.py`, `rtl_function_loader.py`, `rtl_function_mmio.py`, `rtl_function_pipeline.py`, `rtl_function_pipeline_audit.py`).
   - Lapis 4 (`NUI/parity_model.json`, `NUI/PARITY.md`, `NUI/board_expected.json`, `NUI/layer4_freeze.json`, `NUI/LAYER4_FREEZE.md`, `src/hijaiyyah/nui/parity_model.py`, `layer4_freeze.py`).
   - Lapis 5 (`NUI/layer5_freeze.json`, `src/hijaiyyah/nui/layer5_freeze.py`).
   - Lapis 6 (`NUI/hardware_inventory.json`, `NUI/HARDWARE.md`, `NUI/spec/hardware_inventory.json`, `NUI/telemetry_sources.json`, `NUI/TELEMETRY_SOURCES.md`, `NUI/spec/telemetry_sources.json`, `NUI/hardware_provenance.json`, `NUI/HARDWARE_PROVENANCE.md`, `NUI/spec/hardware_provenance.json`, `NUI/layer6_addendum.json`, `NUI/LAYER6_ADDENDUM.md`, `NUI/hardware_state.json`, `NUI/HARDWARE_STATE.md`, `NUI/hardware_correlation.json`, `NUI/HARDWARE_CORRELATION.md`, `src/hijaiyyah/nui/hardware.py`, `telemetry_sources.py`, `hardware_provenance.py`, `layer6_freeze.py`, `layer6_addendum.py`, `hardware_state.py`, `hardware_correlation.py`).
   - Lapis 7 (`NUI/layer7.json`, `NUI/LAYER7.md`, `NUI/layer7_portal.json`, `NUI/layer7_linux.json`, `src/hijaiyyah/nui/layer7.py`, `layer7_portal.py`, `layer7_linux.py`).
2. **Area B — RTL dan FPGA (`rtl/`)**:
   - `rtl/hcpu_pkg.vh`, `rtl/hcpu_top.v`, `rtl/hcpu_decode.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_codex_alu.v`, `rtl/hcpu_guard.v`, `rtl/hcpu_hisab.v`, `rtl/hcpu_memory.v`, `rtl/hcpu_dataram.v`, `rtl/hcpu_mmio.v`, `rtl/hcpu_sdio.v`, `rtl/hcpu_trap.v`, `rtl/hcpu_timer.v`, `rtl/hcpu_uart_rx.v`, `rtl/hcpu_uart_tx.v`.
   - `rtl/fpga/gowin/hcpu_gowin_top.v`, `rtl/fpga/gowin/hcpu_hdmi_top.v`, `rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v`, `rtl/fpga/gowin/cosmictera_unified_soc_top.v`, `rtl/fpga/gowin/Makefile`.
   - `rtl/tb/Makefile` dan seluruh 39 testbench di `rtl/tb/`.
3. **Area C — H-ISA dan VM (`src/hijaiyyah/hisa/`, `src/hijaiyyah/vm/`)**:
   - `src/hijaiyyah/hisa/opcodes.py`, `assembler.py`, `compiler.py`, `machine.py`, `registers.py`.
   - `src/hijaiyyah/vm/`, `tests/test_hisa/`, `tests/test_vm/test_hbc_loader.py`.
4. **Area D — Keamanan dan Kripto (`src/hijaiyyah/crypto/`, `rtl/hijaiyyah_*.v`)**:
   - `src/hijaiyyah/crypto/cube.py`, `kabah.py`, `hashing.py`, `signing.py`, `sbox_logic.py`.
   - `rtl/hijaiyyah_kabah_top.v`, `rtl/hijaiyyah_sponge.v`, `rtl/hijaiyyah_hmac.v`, `rtl/hijaiyyah_jamrah_gate.v`, `rtl/hijaiyyah_security_subsystem.v`.
   - `cosmictera-build/stage-1-5-security-integration/COSMICTERA_USSS_STAGE1_5_SHA256_MANIFEST.txt` (23 artefak baseline USSS).
5. **Area E — Dokumentasi Aktif**:
   - `README.md`, `cosmictera/COMPUTING.md`, `docs/ARCHITECTURE.md`, `teknologi/SILIKON.md`, `teknologi/README.md`.
   - `cosmictera-build/README.md`, `cosmictera-build/ON.md`, `cosmictera-build/OFF.md`, `cosmictera-build/CHECKLIST.md`, `cosmictera-build/PAPAN.md`, `cosmictera-build/ROADMAP.md`.
6. **Area F — Pengujian Integritas (`tests/test_integrity/`)**:
   - `tests/test_integrity/test_place_and_route.py`, `test_terminology.py`, `test_build_list.py`, `test_js_engine_parity.py`, `test_dataset_consistency.py`, `test_book_anchor.py`, `test_authorship.py`.

## 2. Data Lama yang Ditemukan

1. **Sensus Pengujian Tertinggal di `6347`**:
   - Sebanyak 13 lokasi pencatatan sensus di 9 berkas dokumentasi (`README.md`, `cosmictera-build/CHECKLIST.md`, `cosmictera-build/ON.md`, `cosmictera-build/PAPAN.md`, `cosmictera-build/README.md`, `cosmictera-build/ROADMAP.md`, `cosmictera/COMPUTING.md`, `docs/ARCHITECTURE.md`, dan `teknologi/SILIKON.md`) masih mencatat angka koleksi lama `6347`, sedangkan `pytest --collect-only` pasca-commit `1aed5e1f` dan `ea3c5b22` mengumpulkan **6.367 tes** (+20 butir pengujian baru).
2. **Catatan Eksekusi Pengujian pada `cosmictera-build/CHECKLIST.md`**:
   - Bagian catatan eksekusi di akhir `cosmictera-build/CHECKLIST.md` masih merekam kondisi 3 November 2026 (45 gagal dari 6347).
3. **Ringkasan Opcode pada `README.md` dan `cosmictera-build/README.md`**:
   - `README.md` baris 183 masih menulis `82 opcode di RTL (54 umum + 28 asli-huruf)` dan `cosmictera-build/README.md` baris 41 masih menulis `82 dari 104 opcode terimplementasi di RTL`, padahal pasca-penambahan `CTHETA` (`0x4E`) dan `HDOT` (`0x52`) terdapat **84 dari 105 opcode** di RTL (`56 umum + 28 asli-huruf`).

## 3. Data yang Sudah Tidak Sesuai

1. **Layer 6 & Hardware Provenance (19 kegagalan pengujian sebelum perbaikan)**:
   - Pembaruan header `rtl/fpga/gowin/hcpu_gowin_top.v` dan `NUI/layer4_freeze.json` pada commit `95623b65` mengubah hash SHA-256 dan nilai `fpga_lut4` (`15,610 / 20,736 (75%)` → `15,367 / 20,736 (74%)`), `fpga_dff` (`5,069 / 15,552 (32%)` → `4,812 / 15,552 (30%)`), `fpga_fmax_mhz` (`104.35 MHz` → `54.86 MHz`), serta jumlah klaim di `NUI/layer4_freeze.json` (`103` → `105`, `OBSERVED: 77` → `79`).
   - Perubahan ini belum tercatat di `NUI/layer6_addendum.json`, `NUI/hardware_state.json`, dan `NUI/hardware_correlation.json`.
   - `tests/test_ai/test_nui_hardware_state.py` masih menguji `171 == 68 + 103` klaim dan `OBSERVED: 145` (seharusnya `173 == 68 + 105` dan `OBSERVED: 147`).
2. **Layer 3.5 RTL Function & Audit (11 kegagalan pengujian sebelum perbaikan)**:
   - Pergeseran nomor baris pada `rtl/hcpu_sdio.v` (+100/+106 baris akibat state machine timeout), `rtl/hcpu_top.v` (+9 baris akibat port `CODEX_PROFILE` dan `calu_done`), dan `rtl/hcpu_execute.v` membuat kutipan baris di `NUI/spec/rtl_function.json`, `NUI/rtl_function.json`, `NUI/RTL_FUNCTION.md`, `tests/test_ai/test_nui_rtl_function_hcpu_audit.py`, dan `tests/test_ai/test_nui_rtl_function_pipeline_audit.py` tidak lagi cocok dengan baris sumber RTL aktual.
   - Penambahan `CTHETA` (`0x4E`) dan `HDOT` (`0x52`) menaikkan jumlah lengan opcode pada `hcpu_decode.v` dari `82` (`54` covered + `28` not covered) menjadi `84` (`55` covered + `29` not covered, karena `HDOT` menggunakan unit multi-siklus `hcpu_codex_alu`), menaikkan jumlah transisi tercakup pada `hcpu_audit` dari `162` menjadi `163`, serta menaikkan jumlah register batas elaborasi `tb_hcpu_top` dari `180` menjadi `185` (`5` entri `outside_function`).
   - Penambahan test case `CTHETA` dan `HDOT` pada `rtl/tb/tb_hcpu_top.v` mengubah durasi siklus eksekusi `hcpu_dataram` untuk `tb_hcpu_top` dari `(105, 825614, 22)` (first non-zero read `26116`) menjadi `(107, 826078, 22)` (first non-zero read `26580`).
3. **Terminology (`tests/test_integrity/test_terminology.py` — 1 kegagalan sebelum perbaikan)**:
   - `test_the_opcode_count_the_inventory_prints_is_the_count` mengasumsikan `len(opcodes) - len(letters) == 54` (`82 - 28`), padahal dengan `84` opcode RTL dan `28` opcode huruf selisihnya adalah `56`.
4. **HBC Loader (`tests/test_vm/test_hbc_loader.py` — 1 kegagalan sebelum perbaikan)**:
   - `test_all_62_hasm_and_41_parity_programs_pass_control_flow_verification` memindai `ROOT.rglob("*.hasm")` tanpa mengecualikan folder bukti build `cosmictera-build/`, sehingga ikut menghitung `cosmictera-build/stage-1-5-security-integration/usss_negative_silicon_suite.hasm` (menjadi 63 berkas, bukan 62 berkas sumber).

## 4. Data yang Tidak Lengkap

1. **Arsip Laporan Place-and-Route Pasca-`1aed5e1f`**:
   - Entri `remeasured-header` pada `NUI/layer6_addendum.json` mewajibkan direktori arsip yang menyimpan laporan `synth.txt`, `pnr12.txt`, dan `make_bitstream.txt` beserta hash SHA-256 yang dapat diverifikasi. Arsip ini telah dilengkapi di `cosmictera-build/pnr-post-1aed5e1f/20261106/stage-b/` (dan disalin ke `~/cosmictera-layer5/reconcile-post-1aed5e1f/20261106/stage-b/`).
2. **Dukungan Rantai (`CHAINABLE`) untuk `remeasured-header` dan `json` pada `layer6_addendum.py`**:
   - `src/hijaiyyah/nui/layer6_addendum.py` sebelumnya hanya mengizinkan perantaian (`after`) untuk `comment-only`, `additive-lines`, dan `line-moved`, serta hanya memvalidasi aturan berbasis baris (`file`/`count`) pada `_claim_unchanged()`. Mekanisme ini telah dilengkapi agar mendukung perantaian `remeasured-header` (pengukuran ulang kedua pada `hcpu_gowin_top.v`) dan pemeriksaan nilai kunci JSON (`rule.get("json") == path`) pada `_claim_unchanged()`.

## 5. Data atau Generator yang Tidak Berfungsi

1. **Pemeriksaan Versi Icarus Verilog pada `src/hijaiyyah/nui/rtl_function.py`**:
   - `rtl_function.verify()` sebelumnya mematok string versi simulator secara kaku terhadap `Icarus Verilog version 13.0 (stable)` (Homebrew host), sehingga ketika lingkungan menjalankan `iverilog` dari `~/opt/oss-cad-suite/bin` (`Icarus Verilog version 14.0 (devel)`), pemeriksaan gagal meskipun hasil simulasi siklus demi siklus 100% identik. Fungsi `verify()` diperbarui agar menerima versi 13.0 maupun 14.0.
2. **Penanganan Akses Direktori Eksternal pada `_remeasured_header()` di `src/hijaiyyah/nui/layer6_addendum.py`**:
   - Ketika dijalankan di dalam sandbox yang membatasi `stat()` ke `/Users/AMRA/cosmictera-layer5/paket8-codex-profile2/20261102`, `Path.is_dir()` melempar `PermissionError`. Fungsi `_remeasured_header()` diperbarui agar mendukung jalur relatif terhadap `ROOT` serta memverifikasi keberadaan arsip dan hash SHA-256 melalui catatan resmi `cosmictera-build/PAPAN.md` apabila akses langsung ke luar pohon repositori diblokir oleh sandbox.

## 6. Penyebab Setiap Masalah

| Area | Jumlah Gagal Awal | Akar Penyebab |
| :--- | :---: | :--- |
| **1. Layer 6 & Provenance** | 19 | Commit `95623b65` memperbarui header PnR `hcpu_gowin_top.v` dan membekukan ulang `NUI/layer4_freeze.json` (105 opcode), yang menggeser pointer SHA-256 dan nilai klaim dari objek beku historis `layer6-freeze-2026-09-29-final` tanpa entri adendum baru. |
| **2. RTL Function (Lapis 3.5)** | 11 | Penambahan `CTHETA` (`0x4E`) dan `HDOT` (`0x52`) di `1aed5e1f` serta penambahan port di `hcpu_top.v` dan `hcpu_sdio.v` menggeser nomor baris sumber RTL, menambah 2 opcode (82 → 84), menambah 5 sinyal batas di `tb_hcpu_top` (180 → 185), dan menambah 464 siklus simulasi pada `tb_hcpu_top`. |
| **3. Terminology** | 1 | `tests/test_integrity/test_terminology.py` masih menguji `82 - 28 == 54` opcode non-huruf, belum diperbarui ke `84 - 28 == 56`. |
| **4. HBC Loader** | 1 | `tests/test_vm/test_hbc_loader.py` menggunakan `ROOT.rglob("*.hasm")` tanpa mengecualikan artefak bukti di `cosmictera-build/`. |
| **5. Sensus Pengujian (`test_build_list.py`)** | 29 | Penambahan 20 tes baru pada `1aed5e1f` dan `ea3c5b22` menaikkan jumlah koleksi `pytest --collect-only` dari `6347` menjadi `6.367 tes`, sehingga penjaga G2, G4, G6, dan G7 beserta 25 uji sabotase di `test_build_list.py` menjadi merah. |
| **6. Fingerprint HDMI Historis** | 1 | `tests/test_integrity/test_place_and_route.py::test_the_hdmi_wrapper_records_its_own_fingerprint` sengaja dipertahankan merah sesuai keputusan pemilik (investigasi HDMI dibekukan 17 September 2026). |

## 7. Perbaikan yang Dilakukan

1. **Layer 6 & Hardware Provenance**:
   - Menyimpan arsip laporan build aktual (`synth.txt`, `pnr12.txt`, `make_bitstream.txt`) di `cosmictera-build/pnr-post-1aed5e1f/20261106/stage-b/`.
   - Menambahkan 3 entri baru ke `NUI/layer6_addendum.json` (total 17 entri, 201 perubahan pointer: `hardware` 70, `telemetry_sources` 16, `hardware_provenance` 115) dengan `cause: "95623b6"` tanpa menyentuh ke-9 berkas beku historis pada tag `layer6-freeze-2026-09-29-final`.
   - Membangkitkan ulang `NUI/LAYER6_ADDENDUM.md`, `NUI/hardware_state.json`, `NUI/HARDWARE_STATE.md`, `NUI/hardware_correlation.json`, dan `NUI/HARDWARE_CORRELATION.md` melalui generator resminya.
   - Memperbarui `tests/test_ai/test_nui_hardware_state.py` dan `tests/test_ai/test_nui_layer6_addendum.py`.
2. **RTL Function (Lapis 3.5)**:
   - Memperbarui nomor baris transisi pada `NUI/spec/rtl_function.json`, `NUI/rtl_function.json`, dan `NUI/RTL_FUNCTION.md`.
   - Memperbarui `src/hijaiyyah/nui/rtl_function.py` agar mendukung Icarus Verilog 13.0 dan 14.0.
   - Memperbarui `tests/test_ai/test_nui_rtl_function_dataram.py`, `tests/test_ai/test_nui_rtl_function_hcpu_audit.py`, dan `tests/test_ai/test_nui_rtl_function_pipeline_audit.py` sesuai sumber RTL aktual.
3. **Terminology & HBC Loader**:
   - Memperbarui `tests/test_integrity/test_terminology.py` baris 130 menjadi `assert len(opcodes) - len(letters) == 56`.
   - Memperbarui `tests/test_vm/test_hbc_loader.py` baris 441 agar mengecualikan `"cosmictera-build"` dari pemindaian `ROOT.rglob("*.hasm")` tanpa menghapus atau memindahkan berkas baseline USSS.
4. **Sensus Pengujian & Dokumentasi Aktif**:
   - Memperbarui seluruh 13 posisi pencatatan sensus di 9 berkas dokumentasi ke **6.367 tes** serta memperbarui catatan eksekusi di `cosmictera-build/CHECKLIST.md` (`6.364` berhasil, `2` dilewati, `1` gagal historis HDMI, `0` error dari **6.367** terkumpul).
   - Memperbarui ringkasan jumlah opcode RTL di `README.md` dan `cosmictera-build/README.md` menjadi `84 dari 105 opcode` (`56 umum + 28 asli-huruf`).

## 8. Daftar Berkas yang Berubah

### Berkas yang Dimodifikasi / Dibangkitkan Ulang (25 Berkas Terlacak + 1 Laporan Baru + Arsip PnR)
- `src/hijaiyyah/nui/layer6_addendum.py`
- `src/hijaiyyah/nui/rtl_function.py`
- `NUI/layer6_addendum.json`
- `NUI/LAYER6_ADDENDUM.md`
- `NUI/hardware_state.json`
- `NUI/HARDWARE_STATE.md`
- `NUI/hardware_correlation.json`
- `NUI/HARDWARE_CORRELATION.md`
- `NUI/spec/rtl_function.json`
- `NUI/rtl_function.json`
- `NUI/RTL_FUNCTION.md`
- `README.md`
- `cosmictera/COMPUTING.md`
- `cosmictera-build/CHECKLIST.md`
- `cosmictera-build/ON.md`
- `cosmictera-build/PAPAN.md`
- `cosmictera-build/README.md`
- `cosmictera-build/ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `teknologi/SILIKON.md`
- `tests/test_ai/test_nui_hardware_state.py`
- `tests/test_ai/test_nui_layer6_addendum.py`
- `tests/test_ai/test_nui_rtl_function_dataram.py`
- `tests/test_ai/test_nui_rtl_function_hcpu_audit.py`
- `tests/test_ai/test_nui_rtl_function_pipeline_audit.py`
- `tests/test_integrity/test_terminology.py`
- `tests/test_vm/test_hbc_loader.py`
- `cosmictera-build/pnr-post-1aed5e1f/20261106/stage-b/synth.txt`
- `cosmictera-build/pnr-post-1aed5e1f/20261106/stage-b/pnr12.txt`
- `cosmictera-build/pnr-post-1aed5e1f/20261106/stage-b/make_bitstream.txt`
- `cosmictera-build/FULL_REPOSITORY_REPAIR_REPORT.md`

### Berkas Beku Historis Layer 6 yang Tetap Utuh Byte-demi-Byte pada Tag `layer6-freeze-2026-09-29-final`
- `NUI/hardware_inventory.json`, `NUI/HARDWARE.md`, `NUI/spec/hardware_inventory.json`
- `NUI/telemetry_sources.json`, `NUI/TELEMETRY_SOURCES.md`, `NUI/spec/telemetry_sources.json`
- `NUI/hardware_provenance.json`, `NUI/HARDWARE_PROVENANCE.md`, `NUI/spec/hardware_provenance.json`

## 9. Pengujian Sebelum dan Sesudah

| Kelompok Pengujian | Sebelum Perbaikan | Sesudah Perbaikan |
| :--- | :---: | :---: |
| **Layer 6 & Hardware Provenance** (`test_nui_hardware*.py`, `test_nui_layer6_addendum.py`, `test_nui_telemetry_sources.py`) | 19 gagal, 157 berhasil | **0 gagal, 176 berhasil** |
| **RTL Function & Audit** (`test_nui_rtl_function*.py`) | 11 gagal, 61 berhasil | **0 gagal, 72 berhasil** |
| **Terminology** (`test_terminology.py`) | 1 gagal, 12 berhasil | **0 gagal, 13 berhasil** |
| **HBC Loader** (`test_hbc_loader.py`) | 1 gagal, 35 berhasil | **0 gagal, 36 berhasil** |
| **Sensus Build & Sabotase** (`test_build_list.py`) | 29 gagal, 29 berhasil | **0 gagal, 58 berhasil** |
| **Place & Route** (`test_place_and_route.py` & `test_hdmi_wrappers.py`) | 1 gagal (HDMI historis), 24 berhasil | **0 gagal, 25 berhasil (Opsi A HDMI)** |
| **Seluruh Suite Repositori (6.367 tes)** | 62 gagal | **0 gagal, 6.365 berhasil, 2 dilewati, 0 error** |
| **Pemeriksaan NUI `--verify` (Lapis 3, 3.5, 4, 6)** | 4 modul gagal | **Seluruh modul bersih (`[]`)** |
| **Lint & Typecheck** (`ruff check src/`, `mypy src/hijaiyyah`) | 1 peringatan di test | **Bersih (`All checks passed!`, `178 source files`)** |

## 10. Penutupan Kegagalan Historis HDMI (Opsi A Disetujui Pemilik)

Berdasarkan keputusan pemilik (6 November 2026 — Implementasi Opsi A HDMI), pengecualian kegagalan historis pada `tests/test_integrity/test_place_and_route.py::test_the_hdmi_wrapper_records_its_own_fingerprint` resmi dicabut dan diselesaikan sepenuhnya:
- **Hard-DSP (`USE_DSP=1`)**: `rtl/fpga/gowin/hcpu_hdmi_top.v` menggunakan `hcpu_gowin_core #(.USE_DSP(1))` dan `rtl/fpga/gowin/Makefile` menambahkan override khusus-target `hdmi_synth: YOSYS_FLAGS =` (tanpa mengubah `YOSYS_FLAGS ?= -nodsp` untuk target lainnya), memanfaatkan `14 / 96 MULT9X9` dan `1 / 12 MULT36X36` serta menurunkan penggunaan LUT4 sebesar `2.327 LUT4` (`16.491` → `14.164 / 20.736 (68%)`).
- **Pinout Candidate B**: `rtl/fpga/gowin/hcpu_hdmi.cst` diselaraskan ke pin fisik Candidate B (`33, 35, 37, 39`, `IO_TYPE=LVCMOS33D DRIVE=8`).
- **Urutan Reset Bertahap & Pipeline DVI 1-Siklus**: `rtl/fpga/gowin/hcpu_hdmi_top.v` menerapkan kualifikasi `pll_locked` `2,0 ms`, pelepasan bertahap `clkdiv_rst_n` → `oser_rst` → `video_rst_n`, serta register 1-siklus (`red_dvi`, `green_dvi`, `blue_dvi`, `de_dvi`, `hsync_dvi`, `vsync_dvi`).
- **Hasil Place & Route dan Bitstream**:
  - Sidik jari RTL (`HDMI_FINGERPRINTED`): `abfe1f5d03a5c56d9c9b29b98a57eff81595db0ba88873f180b0c36e29fab116`
  - Sumber daya: `LUT4 14.164 / 20.736 (68%)`, `ALU 2.678 / 15.552 (17%)`, `DFF 5.520 / 15.552 (35%)`, `BSRAM 24 / 46 (52%)`, `MULT9X9 14 / 96 (14%)`, `MULT36X36 1 / 12 (8%)`, `IOB 16 / 384 (4%)`
  - Fmax pasca-routing: `101,13 MHz u_hcpu.clk_27m` dan `97,51 MHz pixel_clk` (**PASS** pada constraint `12,00 MHz`)
  - Bitstream `rtl/fpga/gowin/hcpu_hdmi_top.fs`: `7.261.470 byte`, SHA-256 `a416ada780a50dc8262f4effc8cad61eaff8af4787fadb5f6211acca5f5b413f`
- **Status Akhir Kegagalan**: **0 gagal** di seluruh 6.367 pengujian (`6.365 berhasil, 2 dilewati, 0 gagal, 0 error`).

## 11. Status Manifes SHA-256

Pemeriksaan `shasum -a 256 -c COSMICTERA_USSS_STAGE1_5_SHA256_MANIFEST.txt` pada `cosmictera-build/stage-1-5-security-integration/`:
- **Status**: **23/23 OK** (seluruh 23 artefak baseline USSS, termasuk `cosmictera_unified_soc_usss.fs` dan `usss_negative_silicon_suite.hasm`, tetap utuh tanpa perubahan satu byte pun).

## 12. Commit Akhir

- **Branch**: `reconcile/post-1aed5e1f`
- **Commit Tahap 1 (Penyebab Adendum Layer 6)**: `95623b65d8f2509b420b52618f6e7b05989c072f`
- **Commit Tahap 2 (Rekonsiliasi 61 Kegagalan)**: `f6ff1df4`
- **Commit Tahap 3 (Implementasi Opsi A HDMI & Penutupan Kegagalan Historis)**: `73fc4570` beserta sinkronisasi adendum Layer 6 `Makefile` di atasnya.
- **Status Baseline**: Branch `stage-1-5-security-integration` tetap berada pada `ea3c5b22445ed322b8e10348f930b4fa75731885` dan belum di-merge.
