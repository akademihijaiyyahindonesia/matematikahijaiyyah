# LAPORAN AKHIR: COSMICTERA — NUI CONTROL ALL SYSTEM & PENUTUPAN TIMING POST-ROUTE HDMI (`1280×720 @ 60 Hz`)

- **Tanggal Penyelesaian**: 7 November 2026
- **Branch Kerja**: `feat/realtime-computing-hdmi` (bercabang dari checkpoint penerimaan `920f3e61`)
- **Identitas Build Aktif**: `BUILD:CT-NUI-CAS-V1.3`
- **Checkpoint Dasar yang Dilindungi**:
  - Baseline `stage-1-5-security-integration` (`ea3c5b22445ed322b8e10348f930b4fa75731885`) — **23/23 SHA-256 OK**
  - Checkpoint Opsi A HDMI (`11452b9c`) — **8/8 SHA-256 OK**
  - Checkpoint Perbaikan M5.2B (`920f3e61`) — **7/7 SHA-256 OK**
- **Target Hardware**: Sipeed Tang Nano 20K (`GW2AR-LV18QN88C8/I7`, Gowin `GW2A-18C`)
- **Mode Pemrograman FPGA**: **`SRAM_ONLY`** (`openFPGALoader -b tangnano20k hcpu_hdmi_top.fs`; penulisan ke SPI Flash eksternal dilarang keras)
- **Bitstream Final**: `rtl/fpga/gowin/hcpu_hdmi_top.fs` (`7,261,470 byte`, SHA-256: `7fe32ef6d41e6f371ea6ed1e1c5e648e9bcd8c98384476fdfcb42d8d92c199ab`)
- **RTL Fingerprint (`HDMI_FINGERPRINTED`)**: `5e8402deb52b82a4757f348009c9b9a53e0a09fa2d940eb2976e7c36cc4ce01d`

## 1. Ringkasan Eksekutif Penyelesaian 4 Arahan Penutup Pemilik

Seluruh empat arahan penutup pemilik telah diselesaikan dan diverifikasi secara menyeluruh pada kode RTL, sintesis Yosys, place-and-route `nextpnr-himbaechel`, simulasi Icarus Verilog, suite integritas `pytest`, serta perangkat keras fisik Tang Nano 20K:

| No | Arahan Penutup Pemilik | Target Teknis | Hasil Aktual & Bukti Terukur | Status |
|---|---|---|---|---|
| **1** | **Penutupan Timing `pixel_clk` Post-Route** | `pixel_clk >= 74.25 MHz` dan `u_hcpu.clk_27m >= 27.00 MHz` pada laporan akhir post-route | **`pixel_clk = 86.01 MHz`** post-route (`+11.76 MHz` di atas target `74.25 MHz`; pre-route `118.79 MHz`) dan **`u_hcpu.clk_27m = 119.60 MHz`** post-route (`4.43×` target `27.00 MHz`) pada `hdmi_build_v3.log` | **LULUS PENUH** |
| **2** | **NUI — Control All System (7 Tahap Kendali)** | Siklus kendali `INPUT -> UNDERSTANDING -> COORDINATION -> EXECUTION -> MONITORING -> DECISION -> FEEDBACK` di atas 11 subsistem & `L0–L11` | **16/16 skenario LULUS** (`cosmictera_nui_control_center.py` + `nui_control_all_system_verification.json`), termasuk penolakan tegas operasi tak didukung (`REJECTED`) dan gerbang fail-closed `USSS` + `L7` | **LULUS PENUH** |
| **3** | **NUI Real-Time Control Center pada HDMI & Koreksi TV-Safe Overscan** | Perbaikan terpotongnya kolom kiri/kanan pada TV fisik, pemisahan identitas `BUILD:CT-NUI-CAS-V1.3` vs `BASE:920F3E61`, dan telemetri kendali NUI real-time | Margin kiri Zona 6 digeser ke `col = 4` (`Cols 4..34`), catatan kanan Zona 2 digeser ke `col = 32` (bebas timpaan `u_comp` di `cols 16..31`), `sim_dashboard` **13/13 PASS** | **LULUS PENUH** |
| **4** | **Verifikasi Penutup (4 Pengujian Wajib)** | Timing closure, validasi tombol fisik S1/S2/UPDATE, validasi kendali NUI L0–L11, dan uji stabilitas real-time | `tb_physical_buttons_fault_recovery.v` **19/19 PASS**, `pytest` **162/162 PASS**, dan bukti monitor fisik (`CDFR0x5610 = 22,032 frame`, `RELOCK:00`, `FLRC002E = 14 recovery`) | **LULUS PENUH** |

## 2. Arahan 1 — Audit Jalur Kritis & Penutupan Timing `pixel_clk >= 74.25 MHz` Post-Route

### 2.1 Analisis Jalur Kritis Post-Route Sebelumnya (`61.45 MHz` / `16.27 ns`)
Pada build sebelumnya (`hdmi_build_v2.log`), estimasi pre-route `pixel_clk` mencapai `74.69 MHz`, namun hasil akhir post-route turun ke `61.45 MHz` (`16.27 ns`: `9.43 ns logic + 6.85 ns routing`). Bedah langsung laporan timing `hdmi_build_v2.log` menemukan bahwa jalur kritis `16.27 ns` tersebut berasal dari satu rantai kombinasional panjang menuju register `ch_d`:
1. `0.00 ns -> 6.44 ns`: `u_timing.v_count` / `h_count` -> `u_render.cell_addr` (`ahead = h_count + 2`, `ahead >= 1650`, `la_row * 128 + la_row * 32 + la_col`).
2. `6.44 ns -> 13.49 ns` (`+7.05 ns`): `cell_addr[13:4]` (`rtm_blk`) -> multiplekser `case (rtm_blk)` 43-cabang di `hcpu_hdmi_top.v` -> `rtm_sel_val[15:0]` -> multiplekser `rtm_nib[3:0]`.
3. `13.49 ns -> 16.27 ns` (`+2.78 ns`): `rtm_nib` -> penjumlah rantai carry 8-bit `8'h41 + {4'd0, rtm_nib} - 8'd10` -> multiplekser `any_ch` -> flip-flop `ch_d`.

### 2.2 Perbaikan Arsitektural Pipeline di `rtl/fpga/gowin/hcpu_hdmi_top.v`
Karena `cell_addr = {rtm_blk, rtm_pos}` dengan `160 = 10 × 16` sel per baris, nilai blok `rtm_blk = cell_addr[13:4]` hanya berubah pada batas `rtm_pos == 0` (sekali setiap `16` karakter = **128 siklus `pixel_clk`**), sedangkan `rtm_hex_hit` hanya aktif pada `rtm_pos == 4..7` (**32 hingga 63 siklus `pixel_clk` setelah `rtm_blk` stabil**). Berdasarkan sifat deterministik ini, dilakukan tiga optimasi presisi di `hcpu_hdmi_top.v`:
1. **Registrasi Tahap 1 (`rtm_blk_q`)**: Meregister `rtm_blk_q <= cell_addr[13:4]` pada `posedge pixel_clk`, memutus rantai adder `u_render.cell_addr` dari pohon dekoder 43-cabang.
2. **Registrasi Tahap 2 (`rtm_sel_val_q`, `rtm_sel_at_q`, `rtm_blk_match_q`)**: Mengevaluasi `case (rtm_blk_q)` dan meregister hasilnya ke `rtm_sel_val_q`, `rtm_sel_at_q`, dan `rtm_blk_match_q` pada `posedge pixel_clk` (stabil pada siklus ke-2 dari 128 siklus blok, atau **30 siklus penuh sebelum `rtm_pos == 4` dimulai**).
3. **Tabel LUT Hex Murni & Pipeline Hologram 2-Tahap**: Mengganti operasi aritmetika `8'h41 + {4'd0, rtm_nib} - 8'd10` dengan tabel `case (rtm_nib)` 16-entri murni tanpa carry chain, serta mem-pipeline pembacaan BSRAM `nui_holo_rom` 2 tahap (`h_la2 = h_count + 2` -> `holo_byte_q` -> `holo_rgb_q`).

### 2.3 Perbandingan Terukur Sebelum vs Sesudah Optimasi (`hdmi_build_v2.log` vs `hdmi_build_v3.log`)

| Metrik Place & Route (`nextpnr-himbaechel`) | Sebelum (`hdmi_build_v2.log`) | Sesudah (`hdmi_build_v3.log`) | Target / Kapasitas | Status |
|---|---|---|---|---|
| **Pre-Route `pixel_clk` Fmax** | `74.69 MHz` | **`118.79 MHz`** | `>= 74.25 MHz` | **LULUS (`+44.54 MHz`)** |
| **Post-Route `pixel_clk` Fmax** | `61.45 MHz` (`16.27 ns`) | **`86.01 MHz`** (`11.63 ns`) | **`>= 74.25 MHz`** (`13.47 ns`) | **LULUS (`+11.76 MHz` / `+15.8%`)** |
| **Post-Route `u_hcpu.clk_27m` Fmax** | `97.64 MHz` | **`119.60 MHz`** (`8.36 ns`) | **`>= 27.00 MHz`** (`37.04 ns`) | **LULUS (`+92.60 MHz` / `4.43×`)** |
| **IOB** | `16 / 384 (4%)` | `16 / 384 (4%)` | `<= 384` | **LULUS** |
| **LUT4** | `15,318 / 20,736 (73%)` | `15,349 / 20,736 (74%)` | `<= 20,736` | **LULUS (`5,387 LUT4` cadangan)** |
| **ALU Carry** | `2,956 / 15,552 (19%)` | `2,952 / 15,552 (18%)` | `<= 15,552` | **LULUS** |
| **DFF Registers** | `6,123 / 15,552 (39%)` | `6,178 / 15,552 (39%)` | `<= 15,552` | **LULUS** |
| **BSRAM Blocks** | `33 / 46 (71%)` | `33 / 46 (71%)` | `<= 46` | **LULUS** |
| **DSP `MULT9X9` / `MULT36X36`** | `14 / 96` & `1 / 12` | `14 / 96 (14%)` & `1 / 12 (8%)` | `<= 96` & `<= 12` | **LULUS** |
| **Setup / Hold Violations** | `0 / 0` | **`0 / 0`** | `0 / 0` | **LULUS** |

## 3. Arahan 2 — NUI Control All System: Audit & Integrasi 11 Subsistem dan Lapisan L0–L11

### 3.1 Siklus Kendali 7 Tahap NUI (`INPUT -> UNDERSTANDING -> COORDINATION -> EXECUTION -> MONITORING -> DECISION -> FEEDBACK`)
Koordinator terpadu `cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/cosmictera_nui_control_center.py` menghubungkan seluruh lapisan NUI yang benar-benar ada di repositori (`src/hijaiyyah/nui/`) dengan antarmuka subsistem riil tanpa melewati mekanisme keamanan `USSS` maupun semantik `H-ISA`:

1. **`INPUT`**: Menerima perintah perangkat keras (`PHYSICAL_BTN_S1` Pin 88, `PHYSICAL_BTN_S2` Pin 87, `UART_LOADER` Pin 70) maupun perintah sistem (`NUI_HOST_API`).
2. **`UNDERSTANDING`**: Mengidentifikasi maksud perintah, memvalidasi apakah subsistem dan operasi didukung (`SUPPORTED_SUBSYSTEM_OPS`), serta menetapkan prioritas tertinggi `HIGHEST_STOP` untuk tombol fisik `S1`.
3. **`COORDINATION`**: Menentukan rute lapisan NUI (`L0 -> L1 -> L2 -> L3 -> L4 -> L5 -> L6 -> L7 -> L9 -> L11`), memeriksa status otorisasi pada kontrak `NUI/LAYER7.md` melalui `hijaiyyah.nui.layer7.evaluate`, dan memblokir eksekusi HCPU apabila sistem sedang berada dalam kondisi `STOPPED`, `PAUSED`, `FAULT`, atau `FAULT_LATCHED`.
4. **`EXECUTION`**: Memanggil antarmuka subsistem yang sah (`HISAMachine`, `MASTER_TABLE`, `vector_features`, `usr.lower`, `assemble`, `HbcFile`, `build_hpg1_container`, `evaluate_nui_feature_space_coherence`, `compute_digest`, `cube.digest`, `full_guard_check`, `knowledge.query`).
5. **`MONITORING`**: Memantau hasil aktual eksekusi, jumlah siklus/langkah, status keutuhan 6-Guard (`G1–G4`, `T1–T2`), penghitung tombol `S1`/`S2`/`recovery`, dan frame CDC (`CDFR`).
6. **`DECISION`**: Mengevaluasi gerbang keputusan fail-closed `hijaiyyah.nui.layer7_decision.decide` beserta penyegelan `record_sha256` (`ALLOW`, `HOLD_USER_STOP`, `STOP`, `STOP_FAULT_LATCHED`, `RECOVERED_READY`, atau `REJECTED`).
7. **`FEEDBACK`**: Menghasilkan struktur telemetri langsung untuk seluruh 10 zona tampilan **CosmicTera NUI-Centered Real-Time Control Center** pada monitor HDMI `1280×720 @ 60 Hz`.

### 3.2 Matriks Integrasi & Verifikasi 11 Subsistem CosmicTera di Bawah Kendali NUI

| No | Subsistem CosmicTera | Rute Lapisan NUI | Antarmuka Riil yang Dikendalikan NUI | Hasil Verifikasi (`cosmictera_nui_control_center.py`) | Status di HDMI Slot |
|---|---|---|---|---|---|
| **1** | **HCPU & H-ISA** | `L0 -> L2 -> L3 -> L4 -> L6 -> L7` | `HISAMachine`, `hcpu_gowin_core`, `S1 (STOP/PAUSE)`, `S2 (RESET/RECOVERY)` | `CMD-01`: `test_bsm.hasm` menghasilkan `[112]`, `HALTED`, `DECISION=ALLOW` | **LIVE HARDWARE (`27 MHz`)** |
| **2** | **Hybit 18D & Matematika Hijaiyyah** | `L0 -> L4 -> L6 -> L9` | `MASTER_TABLE`, `vector_features`, `build_exomatrix`, `Jim (0xE4)` + `Kha (0xE6)` | `CMD-02`: Fitur L0 `Jim+Kha = [2, 2, 2, 6, 6]` & BSM `[112, 10, 9]`, Exomatrix `5×5` | **LIVE HARDWARE (`14× MULT9X9`)** |
| **3** | **HC, HASM, HBC** | `L1 -> L2 -> L3 -> L4` | `hijaiyyah.nui.usr.lower`, `assemble`, `HbcFile.to_bytes/from_bytes` | `CMD-03`: Kompilasi `let a=5; let b=7; print(a+b);` -> round-trip HBC eksak -> output `[12]` | **LOADER @ `0x040` HW** |
| **4** | **HVM & HCVM** | `L2 -> L3 -> L4` | `HISAMachine` vs `NUI/parity_model.json` | `CMD-04`: Paritas `test_bsm` `[112]` cocok 100%, `74` opcode berstatus `MATCH (P3)` | **74/105 PARITY CC** |
| **5** | **HOS & HFS** | `L2 -> L3 -> L5 -> L7` | `rtl/programs/kernel.hasm` (`157` kata) & `test_hfs.hasm` (`44` kata) di simulator host | `CMD-05`: Output simulasi HFS `[1, 1, 1, 2, 1]`; jujur dilaporkan `NOT INSTRUMENTED` pada slot HDMI | **`NOT INSTRUMENTED` (Jujur)** |
| **6** | **HAR & HPG-1** | `L0 -> L2 -> L9` | `HARRegistry` (`28` entri kanonik) & `build_hpg1_container` | `CMD-06`: Kontainer HPG-1 untuk `ج` (`Jim 0xE4`) terbangun dan tervalidasi | **HOST PYTHON LIB** |
| **7** | **HMCL** | `L0 -> L4 -> L9` | `evaluate_nui_feature_space_coherence` (koherensi ruang fitur 28 huruf) | `CMD-07`: Koherensi ruang fitur NUI lintas 28 huruf Hijaiyyah terverifikasi | **HOST PYTHON LIB** |
| **8** | **HISAB** | `L0 -> L4 -> L6` | `compute_digest` (CRC32) & instruksi hardware `HPACK (0x50)` / `HCRC (0x51)` | `CMD-08`: `HPACK` dan `HCRC` 1-siklus untuk `Jim (#5)` cocok dengan engine HISAB | **LIVE HARDWARE (1-Siklus)** |
| **9** | **Ka'bah & Jamrah** | `L0 -> L4 -> L6` | `hijaiyyah.crypto.cube.digest` & `cube_digest` + 6-Guard Jamrah di hardware | `CMD-09`: Permutasi spons Ka'bah menghasilkan digest deterministik `32 byte` | **6-GRD HW / FULL SPONGE SEP. SLOT** |
| **10** | **USSS** | `L0 -> L4 -> L6 -> L7` | `full_guard_check` (`G1–G4`, `T1–T2`), proteksi memori `[BASE, LIMIT)`, mode privilese | `CMD-10`: Vektor `Jim` valid lolos 6-Guard (`True`); vektor rusak `A_N=99` tertangkap (`True`); `CMD-16`: upaya bypass USSS ditolak (`REJECTED`) | **LIVE HARDWARE (6-Guard + MMIO)** |
| **11** | **CosmicTera HDMI Monitor** | `L0 -> L6 -> L7 -> L9` | `hcpu_hdmi_top.v` (`1280×720p60`), `knowledge.query("letter ج")`, `registry.by_char("ج")` | `CMD-11`: Frame CDC diperbarui, query L9 menjawab domain `['HC', 'HISA', 'RTL', 'PAPAN', 'NUI']` dengan opcode `0xe4` | **LIVE HARDWARE (`86.01 MHz`)** |

### 3.3 Audit Jujur Lapisan NUI L0–L11 (Tanpa Klaim Palsu)

| Lapisan | Nama Resmi di Repositori | Status Jujur | Peran Fungsional dalam Rantai Kendali NUI |
|---|---|---|---|
| **L0** | Verified Knowledge & 5-Feature Embedding | **RUNNING (Silicon + Host)** | Mengekstrak 5 fitur geometris `(titik=2, garis=2, lengkung=2, theta=6, rho=6)` dari `Jim (0xE4) + Kha (0xE6)` secara langsung di silikon dan Python (`features.py`). |
| **L1** | Repository Knowledge Graph | **COMPLETE (`1828N / 4689E`)** | Memetakan ketergantungan penuh berkas repositori yang dilacak git (`repository_graph.py`). |
| **L2** | Program Index & Call/Instance Graph | **COMPLETE (`60 HASM / 100 Verilog`)** | Mengindeks seluruh 60 program `.hasm` dan 100 modul Verilog beserta graf panggilan/instansiasi (`program_index.py`, `program_graph.py`). |
| **L3** | Execution Understanding & Trace | **COMPLETE (`63 Runs`)** | Merekam jejak eksekusi deterministik dan aliran kontrol (`CALLS`, `TRAPS`, `RESUMES`) (`execution_trace.py`). |
| **L4** | Software-Hardware Parity Verification | **COMPLETE (`74/105 P3`)** | Memverifikasi kesamaan bit-for-bit antara interpreter Python, simulasi RTL, dan papan FPGA (`parity_model.py`). |
| **L5** | Linux VM Host Observation Engine | **READY (`9/11 Collectors`)** | Mengumpulkan observasi host bermeterai SHA-256 dengan pemeriksaan kesegaran (`layer5.py`). |
| **L6** | Hardware Intelligence & Real-Time HDMI | **RUNNING (`CDC + RTL F1–F5`)** | Menjembatani telemetri 27 MHz -> 74.25 MHz dan memodelkan fungsi RTL secara eksak (`rtl_function.py`, `hcpu_hdmi_top.v`). |
| **L7** | Autonomous Operation Fail-Closed Gate | **READY (`ALLOW / DENY / STOP`)** | Mengevaluasi 6 prasyarat kontrak 7.6 dan menyegel keputusan operasional dengan `record_sha256` (`layer7.py`, `layer7_decision.py`). |
| **L8** | Automated Diagnostics | **`AT` (Manual / Belum Diklaim)** | Ditampilkan secara jujur sebagai `AT   MANUAL` sesuai kontrak kejujuran R2/R4. |
| **L9** | 7-Domain Reasoning & Knowledge Base | **COMPLETE (`7 Domains`)** | Menjawab query lintas 7 domain (`HC`, `HISA`, `RTL`, `OFF`, `PAPAN`, `NUI`, `HOST`) dengan bukti sumber `file:line` (`knowledge.py`). |
| **L10** | Autonomous Engineering | **`AT` (`NOT IMPL`)** | Ditampilkan secara jujur sebagai `AT   NOT IMP` sesuai kontrak kejujuran R2/R4. |
| **L11** | Universal Computing Synthesis | **`AT` (`ATOM LNK`)** | Ditampilkan secara jujur sebagai `AT   ATOM LK` sesuai kontrak kejujuran R2/R4. |

## 4. Arahan 3 — Perbaikan Tata Letak TV-Safe & Identitas Build pada Monitor HDMI (`1280×720 @ 60 Hz`)

Berdasarkan inspeksi langsung terhadap 2 foto dan 1 video monitor fisik yang dikirimkan pemilik:
1. **Perbaikan Margin Kiri Zona 6 (`Cols 4..34`)**: Sebelumnya Zona 6 dimulai pada `col = 2`, sehingga overscan bezel kiri TV memotong huruf `L` pada `L0..L11`. Kini seluruh isi Zona 6 digeser ke `col = 4` (`Cols 4..34`, lebar 31 karakter), sejajar dengan Zona 1 dan Zona 2 yang terbukti tampil utuh di layar TV fisik.
2. **Perbaikan Kolom Catatan Kanan Zona 2 (`col = 32`)**: Sebelumnya catatan `CTRL FSM`, `IMEM 12B`, `32B WORD`, `27M TICK`, `O/LT/Z/G`, dan `6-GUARD` diletakkan pada `col = 30`, sehingga 2 kolom terakhir area `u_comp` (`cols 16..31`, lebar 16 sel) menimpa `cols 30..31` dengan spasi (`CTRL FSM` tampak sebagai `RL FSM`). Kini seluruh catatan kanan Zona 2 digeser ke `col = 32` sehingga tampil utuh `CTRL FSM`.
3. **Pemisahan Identitas Build Aktif vs Checkpoint Dasar**:
   - Baris 5 (Header), Baris 78 (Zona 9), dan Baris 84 (Footer) secara eksplisit menampilkan identitas build aktif **`BUILD:CT-NUI-CAS-V1.3`** (`CT-NUI-CAS-V1.3 ACTIVE`).
   - Baris 79 (Zona 9) dan Baris 84 (Footer) secara terpisah menampilkan **`BASE CHKPT: M5.2B 920F3E61 PROTECTED`** (`BASE:920F3E61`).

## 5. Arahan 4 — Hasil 4 Pengujian Penutup Wajib

1. **Verifikasi Penutupan Timing (`hdmi_build_v3.log`)**:
   - `u_hcpu.clk_27m`: **`119.60 MHz`** post-route (target `27.00 MHz` -> **LULUS**).
   - `pixel_clk`: **`86.01 MHz`** post-route (target `74.25 MHz` -> **LULUS**).
2. **Validasi Tombol Fisik (`tb_physical_buttons_fault_recovery.v` & Monitor Fisik)**:
   - Simulasi RTL 12 skenario wajib: **19/19 PASS** (`0 FAILED`).
   - Bukti fisik di monitor HDMI Tang Nano 20K: `STATE: RUNNING` + `GUARD: OK` (`CDFR0x5610 = 22,032 frame`, `S1S20B0E`, `FLRC002E`) dan `STATE: STOPPED` + `GUARD: OK` (`CTEV0101`, `PRPO0001`).
3. **Validasi Kendali NUI L0–L11 & 11 Subsistem (`cosmictera_nui_control_center.py` & `pytest`)**:
   - `cosmictera_nui_control_center.py`: **16/16 PASS** (termasuk `CMD-12..CMD-16` untuk prioritas `S1 STOP`, blokir saat `STOPPED`, `FAULT_LATCHED` saat sumber fault masih aktif, pemulihan `S2` ke `RUNNING`, dan penolakan `REJECTED` untuk operasi tak didukung).
   - Suite integritas `pytest`: **162/162 PASS** (`test_place_and_route.py`, `test_hdmi_wrappers.py`, `test_rack.py`, `test_nui_program_index.py`, `test_nui_layer6_addendum.py`, `test_nui_layer6_freeze.py`, `test_nui_layers.py`, `test_nui_layer7_decision.py`).
   - Testbench compositor `sim_dashboard`: **13/13 PASS**.
4. **Uji Stabilitas Real-Time**:
   - Berjalan stabil secara kontinu dengan `RELOCK:00` dan sinkronisasi 2-FF toggle CDC tanpa sobekan frame maupun penguncian `GUARD: FAULT` palsu.
