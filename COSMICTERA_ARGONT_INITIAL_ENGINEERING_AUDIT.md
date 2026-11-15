# COSMICTERA REPOSITORY RECONNAISSANCE & ENGINEERING BASELINE AUDIT
# (`COSMICTERA_ARGONT_INITIAL_ENGINEERING_AUDIT.md`)

**Agen Rekayasa:** ARGON (*Architecture, Research, Governance, Optimization & Neural Technology*)  
**Proyek:** COSMICTERA COMPUTING (`COSMICTERA CT-01-REV13`, HCPU/H-ISA `v1.2`)  
**Target Perangkat Keras:** Sipeed Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`family=GW2A-18C`)  
**Tanggal Audit:** 4 November 2026  
**Mode Pemeriksaan:** **100% Read-Only Reconnaissance & Baseline Audit** (`0` perubahan pada source code, RTL, constraints, bitstream, maupun manifes; `0` operasi pemrograman SRAM atau External Flash)

---

## 1. RINGKASAN EKSEKUTIF & PEMISAHAN EPISTEMIK (`R1–R13`)

Audit rekayasa awal ini dijalankan sesuai mandat **Fase 1–3 & Seksi 11 (`INSTRUKSI PERTAMA UNTUK ARGONT`)** dengan memisahkan secara tegas antara **Fakta Repositori yang Ditemukan**, **Klaim Dokumentasi**, **Bukti Implementasi Source Code**, **Hasil Pengukuran/Pengujian Aktual**, **Informasi yang Belum Dapat Diverifikasi**, **Risiko Teknis Sebelum Pengujian Fisik**, dan **Rekomendasi Tindakan Berikutnya**.

Seluruh evaluasi mematuhi kebijakan epistemik resmi `R2` dari [`cosmictera/RULES.md`](cosmictera/RULES.md):
- **`VF` (*Verified Formally*)**: Terbukti secara formal/matematis dan dapat diperiksa ulang.
- **`CC` (*Computationally Confirmed*)**: Diverifikasi secara komputasional pada domain pengujian yang jelas (pytest, simulasi RTL testbench, pemeriksaan paritas).
- **`DP` (*Design Property*)**: Karakteristik yang ditetapkan oleh spesifikasi atau konstruksi desain.
- **`EH` (*Engineering Hypothesis*)**: Hipotesis rekayasa yang didukung bukti parsial atau memiliki kendala struktural yang belum tertutup bukti formal.
- **`AT` (*Aspirational Target*)**: Target masa depan yang belum direalisasikan dalam implementasi aktif.

---

## 2. HASIL AUDIT TARGET A s.d. TARGET J

### Target A & B — Verifikasi Branch, Commit Aktif, dan Status Pohon Kerja Git

| Parameter Git | Klaim Dokumentasi / Mandat | Fakta Aktual yang Ditemukan di Repositori | Status Verifikasi |
| :--- | :--- | :--- | :---: |
| **Direktori Repositori** | `/Users/AMRA/hijaiyyah-mathematics` | `/Users/AMRA/hijaiyyah-mathematics` | **VERIFIED (`CC`)** |
| **Branch Aktif (`git branch --show-current`)** | `stage-1-5-unified-soc` | `stage-1-5-unified-soc` | **VERIFIED (`CC`)** |
| **Commit `HEAD` Aktif (`git rev-parse HEAD`)** | `ea3c5b22` | `ea3c5b22445ed322b8e10348f930b4fa75731885` (`docs(nui): record post-freeze Layer 6 addendum for CTHETA=0x4E and HDOT=0x52 (1aed5e1)`) | **VERIFIED (`CC`)** |
| **Parent Commit (`HEAD~1`)** | `1aed5e1f` | `1aed5e1f548ee3998e43acec77419cf11cdd4db2` (`feat(hcpu,hisa,nui): map CTHETA=0x4E and HDOT=0x52, resolve GAP-02 in hcpu_hisab, update NUI rtl_function and census`) | **VERIFIED (`CC`)** |
| **Commit Sebelumnya (`HEAD~2`)** | `8c70989b` | `8c70989bec0d3b86ace8b657fd8f1d761164b8e3` (`docs: correct HCPU LUT4 utilization in README`) | **VERIFIED (`CC`)** |
| **Daftar Branch Lokal Lain** | Terisolasi dari `main` | `fix/dataset-canonicalization-and-authorship` (`ea3c5b22`), `main` (`c43e10ff`), `gh-pages` (`d8d00b18`) | **VERIFIED (`CC`)** |
| **Status Working Tree (`git status`)** | Artefak Stage 1.5 berada di direktori kerja terisolasi | 1. **2 berkas terlacak berstatus unstaged `deleted`**: `rtl/tb/nui_embedding.hex` dan `rtl/tb/nui_payload.txt` (produk antara testbench).<br>2. **Seluruh direktori `cosmictera-build/stage-1-5-unified-soc/`**, `constraints/`, `rtl/mpw/sky130_sram_macros/`, dan 25 berkas laporan `COSMICTERA_*.md` di root saat ini berstatus **untracked** di Git. | **PERHATIAN REKAYASA** |

---

### Target C & D — Verifikasi Keberadaan Modul RTL Stage 1.5, BSRAM, Netlist, Log, Golden Frame, dan Manifes SHA-256

Pemeriksaan langsung menggunakan `shasum -a 256 -c COSMICTERA_STAGE1_5_SHA256_MANIFEST.txt` di dalam `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/` mengonfirmasi bahwa **seluruh 39 entri artefak Stage 1.5 tersedia secara fisik di disk dan 100% cocok (`39/39 OK`)** dengan manifes SHA-256:

| Kategori Artefak Stage 1.5 | Path Relatif (`cosmictera-build/stage-1-5-unified-soc/`) | SHA-256 Aktual Terukur | Status |
| :--- | :--- | :--- | :---: |
| **Top-Level Unified SoC RTL** | [`rtl/cosmictera_unified_soc_top.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_unified_soc_top.v) | `2c9d7f28f6a37591c0ac644f4d89612c7de0397741192eb973cf895106c470e5` | **OK (`39/39`)** |
| **Top-Level Boot Display RTL** | [`rtl/cosmictera_boot_top.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_top.v) | `318d63afc88852c9730bf42bd8d062e60a814fc8b29abfc2bda9600dee2feb5c` | **OK** |
| **BSRAM Compositor RTL** | [`rtl/cosmictera_boot_compositor.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_compositor.v) | `5e42c2f7702efaa0a905f3994d26adbebd19bf9ba8372004967b8414297f9af1` | **OK** |
| **BSRAM Render Engine RTL** | [`rtl/cosmictera_boot_render.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_render.v) | `819b7b80ec8033ceabd3a876ab4b740c18cc4e522979838ff3db26d6e4a90b7b` | **OK** |
| **BSRAM Logo & Emblem ROM RTL** | [`rtl/cosmictera_boot_logo_rom.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_logo_rom.v) | `309a283ea2d5b349a41f500ce1c7f58393f39678dcfad32d5c01062c731818e7` | **OK** |
| **BSRAM Text ROM RTL** | [`rtl/cosmictera_boot_text_rom.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_text_rom.v) | `cc729d84ae68137262023b4414969359d16f798c6f0f8041b40805fc385bf92a` | **OK** |
| **87-Bit CDC Telemetry Bridge RTL** | [`rtl/cosmictera_boot_subsys_bridge.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_subsys_bridge.v) | `52d4965245b370f307c38d0fd7e86814950df6766b3b9b48ca733cfab520d2f2` | **OK** |
| **Event Console, Reset Seq & Uptime** | `rtl/cosmictera_boot_{events,reset_seq,uptime}.v` | `b966a32e...`, `38f293f3...`, `a582302f...` | **OK** |
| **6 Tabel ROM BSRAM Stage 1.5** | `rtl/boot_{text,comp,cell_tag,bg_x,bg_y,emblem}_rom.hex` | `f5482e8d...`, `a8b44634...`, `7964ad53...`, `aa1c2a7c...`, `375341d7...`, `2fdc5d83...` | **OK** |
| **Logo RLE, Font 8×8 & Firmware** | `rtl/logo_rle_rom.hex`, `rtl/hcpu_font8x8.hex`, `rtl/program.hex` | `1a644ece...`, `e2974acc...`, `d2644984...` (`test_bsm.hasm`, 9 kata) | **OK** |
| **Constraints Stage 1.5 (`.cst`)** | [`constraints/cosmictera_unified_soc_stage1_5.cst`](cosmictera-build/stage-1-5-unified-soc/constraints/cosmictera_unified_soc_stage1_5.cst) | `5a3934da51f1379b9c02a339c300ce41d7347dd9aa7bda3be37184f6f74f3108` | **OK** |
| **4 Berkas Golden Frame (`.raw`)** | `frame_previews/rtl_{hero_logo_512x184,scanlines_startup,scanlines_ready,scanlines_error}.raw` | `33734404...`, `270dde92...`, `72c2aeb5...`, `ffd5b744...` (identik 100% dengan Stage 1.4) | **OK** |
| **Testbench & Log Simulasi (33 PASS)** | [`rtl/tb_unified_soc_stage1_5.v`](cosmictera-build/stage-1-5-unified-soc/rtl/tb_unified_soc_stage1_5.v), [`tb_unified_soc_stage1_5.log`](cosmictera-build/stage-1-5-unified-soc/tb_unified_soc_stage1_5.log) | `7f12146a...`, `d1f13362...` | **OK** |
| **Yosys Netlist & Log Unified SoC** | `cosmictera_unified_soc_stage1_5.json`, [`yosys_unified_soc_stage1_5.log`](cosmictera-build/stage-1-5-unified-soc/yosys_unified_soc_stage1_5.log) | `9ff30c38...`, `d0408562...` | **OK** |
| **Post-P&R Netlist & Log Unified SoC** | `cosmictera_unified_soc_stage1_5_pnr.json`, [`nextpnr_unified_soc_stage1_5.log`](cosmictera-build/stage-1-5-unified-soc/nextpnr_unified_soc_stage1_5.log) | `90a6f23f51b3c75eb7dabbee75ac98889a02e6f519fd350b8f7847d009ea1ce3`, `4a98e499...` | **OK** |
| **Bitstream Unified SoC Stage 1.5** | [`cosmictera_unified_soc_stage1_5.fs`](cosmictera-build/stage-1-5-unified-soc/cosmictera_unified_soc_stage1_5.fs) | **`02c0a44f28dfa35f41389ed34217b9ea22bdfdf42e13911aefb93e948392a3c4`** | **OK** |
| **Bitstream Boot-Only Stage 1.5** | [`cosmictera_boot_top_stage1_5.fs`](cosmictera-build/stage-1-5-unified-soc/cosmictera_boot_top_stage1_5.fs) | `88bb395fb5a55c40b2b90afcfe8a1c946d967700af1fba72ca5f777e470d14af` (tidak dipakai pada uji pertama) | **OK** |

---

### Target E — Audit Konsistensi Laporan Stage 1.5 terhadap Source Code dan Log Aktual

Kami melakukan pemeriksaan silang baris-demi-baris antara [`COSMICTERA_STAGE1_5_UNIFIED_SOC_REPORT.md`](cosmictera-build/stage-1-5-unified-soc/COSMICTERA_STAGE1_5_UNIFIED_SOC_REPORT.md), kode sumber [`cosmictera_unified_soc_top.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_unified_soc_top.v), log sintesis [`yosys_unified_soc_stage1_5.log`](cosmictera-build/stage-1-5-unified-soc/yosys_unified_soc_stage1_5.log), log P&R [`nextpnr_unified_soc_stage1_5.log`](cosmictera-build/stage-1-5-unified-soc/nextpnr_unified_soc_stage1_5.log), dan testbench [`tb_unified_soc_stage1_5.v`](cosmictera-build/stage-1-5-unified-soc/rtl/tb_unified_soc_stage1_5.v).

#### E.1 Fakta yang 100% Konsisten antara Laporan dan Log Aktual
1. **Utilisasi Sel Post-Pack (`nextpnr_unified_soc_stage1_5.log` baris 90–122)**:
   - `LUT4`: **`14.695 / 20.736` (`70,87%`)** — cocok eksak.
   - `ALU`: **`2.600 / 15.552` (`16,72%`)** — cocok eksak.
   - `DFF`: **`5.572 / 15.552` (`35,83%`)** — cocok eksak.
   - `BSRAM`: **`38 / 46` (`82,61%`)** (`8 DPB + 2 SDPX9B + 17 SP + 11 SPX9 = 38` di Yosys) — cocok eksak.
   - `MULT36X36`: **`1 / 12`**, `MULT9X9`: **`14 / 96`** — cocok eksak.
   - `RAM16SDP4` (`SSRAM`): **`6 / 648`** — cocok eksak.
   - `IOB`: **`16 / 384`**, `IOLOGICO (OSER10)`: **`4 / 384`**, `rPLL`: **`1 / 2`**, `CLKDIV`: **`1 / 8`** — cocok eksak.
   - `Unrouted net`: **`0` dari `68.942` routed arcs**, `0 errors, 0 warnings` — cocok eksak.
2. **Timing Post-Route (`nextpnr_unified_soc_stage1_5.log` baris 553–845)**:
   - `u_hcpu_core.clk_27m`: **`120,88 MHz`** (`8,27 ns` = `4,45 ns` logic + `3,83 ns` routing; terhadap periode `27 MHz = 37,037 ns`, slack = **`+28,76 ns`**).
   - `pixel_clk`: **`75,83 MHz`** (`13,19 ns` = `7,68 ns` logic + `5,51 ns` routing; terhadap periode target `74,25 MHz = 13,468 ns`, slack = **`+0,28 ns`**).
   - Cross-domain `posedge u_hcpu_core.clk_27m -> posedge pixel_clk`: **`9,66 ns`** (`4,82 ns` logic + `4,84 ns` routing).

#### E.2 Lima Temuan Ketidaksesuaian / Nuansa Kritis antara Klaim Laporan/Prompt dan Source Code Aktual (`WAJIB DIPERHATIKAN`)

Audit forensik menemukan **lima perbedaan penting** antara narasi dokumentasi/skrip dan implementasi RTL aktual yang wajib diketahui sebelum pengujian fisik:

1. **TEMUAN E-01 (KRITIS — Format Byte ke-4 dan ke-5 pada Golden UART 23-Byte: `0A 0A` vs `0D 0A`)**:
   - **Klaim pada Laporan Stage 1.5 & `run_stage1_5_sram_validation.py`**: Menulis bahwa 23 byte UART adalah `31 31 32 0D 0A 43 59 43 4C 45 53 3D 30 30 30 30 31 42 38 39 0D 0A 0A` (`"112\r\nCYCLES=00001B89\r\n\n"`).
   - **Bukti di RTL Aktual & Testbench `tb_unified_soc_stage1_5.v`**:
     - Di [`tb_unified_soc_stage1_5.v`](cosmictera-build/stage-1-5-unified-soc/rtl/tb_unified_soc_stage1_5.v) baris 7 dan baris 215–220, vektor `gold_uart_23` yang diuji dan **LULUS (`T25 PASS`)** sebenarnya adalah:
       `31 31 32 0A 0A 43 59 43 4C 45 53 3D 30 30 30 30 31 42 38 39 0D 0A 0A` (`"112\n\nCYCLES=00001B89\r\n\n"` — byte ke-4 adalah `0x0A`, bukan `0x0D`!).
     - Sementara itu, di [`rtl/hcpu_top.v`](rtl/hcpu_top.v) baris 293, instruksi `PRINT` mengirim `"112"` diikuti satu byte `0x0A` (`\n`), lalu di [`rtl/fpga/gowin/hcpu_gowin_top.v`](rtl/fpga/gowin/hcpu_gowin_top.v) baris 499–518, mesin pelapor siklus (`MSG_LEN = 19`) mengirim `\r\nCYCLES=00001B89\r\n` (`0D 0A 43 59 43 4C 45 53 3D 30 30 30 30 31 42 38 39 0D 0A`, tepat 19 byte), sehingga pada `hcpu_gowin_core` terdapat transisi dari `core_txd` ke `report_txd`.
     - **Dampak**: Saat pengujian fisik nanti, rekaman mentah UART dari `/dev/cu.usbserial-20250303171` harus dicatat apa adanya (hex per byte + panjang byte + SHA-256) dan dibandingkan baik terhadap urutan byte `31 31 32 0D 0A ... 0D 0A 0A`, urutan testbench `tb_unified_soc_stage1_5.v` (`31 31 32 0A 0A ... 0D 0A 0A`), maupun urutan `31 31 32 0A 0D 0A ... 0D 0A` agar perbedaan byte newline (`0x0A` vs `0x0D`) tidak menimbulkan *false failure* ketika nilai `112` dan `CYCLES=00001B89` sudah 100% benar!

2. **TEMUAN E-02 (KRITIS — Perilaku `live_hcpu_mode` pada Saat Boot Awal SRAM vs Setelah Menekan Tombol `btn_rst_n` Pin 87)**:
   - **Bukti di [`cosmictera_unified_soc_top.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_unified_soc_top.v) baris 62–75 & 286**:
     - Register `reg live_hcpu_mode = 1'b0;` diinisialisasi ke **`0`** saat SRAM pertama kali dimuat (agar pada Frame 0/1 simulasi `T01–T24f`, tampilan Region 5 cocok 100% bit-demi-bit dengan golden frame Stage 1.4 `rtl_scanlines_ready.raw`).
     - `live_hcpu_mode` di-toggle (`live_hcpu_mode <= ~live_hcpu_mode;`) setiap kali terdeteksi tepi turun (`btn_q[1] & ~btn_q[0]`) pada `btn_rst_n` (Pin 87).
   - **Dampak Fisik pada Layar HDMI (Tahap 4 & 5)**:
     - **Segera setelah SRAM dimuat (sebelum Pin 87 ditekan)**: `u_hcpu_core` langsung mengeksekusi `program.hex`, memancarkan UART 23-byte, dan berhenti pada `CY=00001B89` dengan LED menyala. Namun, karena `live_hcpu_mode == 0` (`bridge_telem_en == 0`), baris 56 Region 5 pada layar HDMI akan menampilkan nilai BIST bawaan Stage 1.4:
       `PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE`
     - **Setelah tombol `btn_rst_n` (Pin 87 / S2) ditekan 1 kali**: `live_hcpu_mode` berubah menjadi **`1`** (`bridge_telem_en == 1`), `u_hcpu_core` melakukan reset dan mengeksekusi ulang `program.hex` (memancarkan UART 23-byte sekali lagi), dan baris 56 Region 5 pada layar HDMI beralih menampilkan **telemetri HCPU live yang sesungguhnya**:
       `PC:008 IN:01000000 CY:00001B89 FL:01 G:OK HLT CDC:LIVE`
     - Pengetahuan ini sangat krusial agar operator pengujian fisik memahami bahwa peralihan dari `CY:0002C1C9 ... RUN` ke `CY:00001B89 ... HLT` dipicu oleh penekanan tombol Pin 87 (`btn_rst_n`).

3. **TEMUAN E-03 (PENTING — Bypass Register Snapshot CDC 84-Bit oleh `` `ifdef YOSYS `` di `cosmictera_boot_subsys_bridge.v`)**:
   - **Bukti di [`cosmictera_boot_subsys_bridge.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_boot_subsys_bridge.v) baris 97–105**:
     - Di bawah blok `` `ifdef YOSYS ``, sinyal `snap_pc`, `snap_instr`, `snap_cycles`, dan `snap_flags` (84 bit) di-assign secara kombinasional langsung dari `src_pc`, `src_instr`, `src_cycles`, dan `src_flags` (domain `clk_27m`) tanpa melalui flip-flop `snap_*_r` di domain `pixel_clk`, sedangkan 3 bit status (`snap_halted`, `snap_guard`, `snap_valid`) tetap diregister di domain `pixel_clk` pada saat `ack_edge`.
   - **Dampak Timing & Fisik**:
     - Karena `u_hcpu_core` menyelesaikan eksekusi `program.hex` (`7.049` siklus = **`0,261 ms`**) jauh sebelum `TMDS_rPLL` melewati kualifikasi lock `2,0 ms` (`54.000` siklus), keempat sinyal `hcpu_tele_{pc,instr,cycles,flags}` sudah berada dalam kondisi **diam/konstan (*quasi-static*)** saat video HDMI mulai merender Frame 0.
     - Namun, penyambungan langsung tersebut menyebabkan `nextpnr-himbaechel` menganalisis jalur kombinasional lintas-domain `posedge u_hcpu_core.clk_27m -> posedge pixel_clk` sepanjang **`9,66 ns`** dan memperpanjang jalur kritis internal `pixel_clk` (`u_compositor.cell_tag_rom -> sel_nib -> u_render.cell_s1 -> u_font.rom.AD7`) menjadi **`13,19 ns` (`75,83 MHz`, slack `+0,28 ns`)**.

4. **TEMUAN E-04 (Parameter `USE_DSP = 1` pada Sintesis Unified SoC vs `USE_DSP = 0` pada Testbench `T27`)**:
   - **Bukti di [`cosmictera_unified_soc_top.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_unified_soc_top.v) baris 27 & 105 vs [`tb_unified_soc_stage1_5.v`](cosmictera-build/stage-1-5-unified-soc/rtl/tb_unified_soc_stage1_5.v) baris 115**:
     - Di `cosmictera_unified_soc_top.v`, parameter default adalah `parameter integer USE_DSP = 1;` dan diteruskan ke `u_hcpu_core`. Selain itu, [`run_stage1_5_build_and_pnr.sh`](cosmictera-build/stage-1-5-unified-soc/scripts/run_stage1_5_build_and_pnr.sh) baris 49 menjalankan `synth_gowin -top cosmictera_unified_soc_top` (tanpa `-nodsp`). Akibatnya, netlist `cosmictera_unified_soc_stage1_5.fs` menginstansiasi `hcpu_codex_alu` pada **`CODEX_PROFILE = 1` (`USE_DSP = 1`, menggunakan `14 MULT9X9` dan `1 MULT36X36`)**, di mana `HDOT` selesai dalam **1 siklus** (sedangkan pada `tb_unified_soc_stage1_5.v` baris 115, testbench mengoverride `.USE_DSP(0)` sehingga menguji `CODEX_PROFILE = 2` 14-siklus).
     - Berbeda dengan catatan lama di `hcpu_gowin_top.v` (yang menyebut `gowin_pack` lama gagal mengemas `MULT9X9`), versi `gowin_pack` pada `oss-cad-suite` saat ini berhasil mengemas `1 MULT36X36 + 14 MULT9X9` tanpa error (`exit_code = 0`). Namun perlu diverifikasi di perangkat keras fisik bahwa keberadaan blok DSP aktif tersebut menghasilkan nilai `HNRM2 = 112` yang presisi.

5. **TEMUAN E-05 (Isi `program.hex` yang Dipanggang di Bitstream `cosmictera_unified_soc_stage1_5.fs`)**:
   - **Bukti di [`cosmictera-build/stage-1-5-unified-soc/rtl/program.hex`](cosmictera-build/stage-1-5-unified-soc/rtl/program.hex)**:
     - Program yang dipanggang ke dalam BSRAM `imem` pada `cosmictera_unified_soc_stage1_5.fs` adalah **`test_bsm.hasm` (9 instruksi)**:
       `HLOAD H0, 2` (`Ba`), `HLOAD H1, 12` (`Sin`), `HLOAD H3, 24` (`Mim`), `HCADD H2, H0, H1`, `HCADD H2, H2, H3`, `HGRD H2`, `HNRM2 R0, H2`, `PRINT R0` (`112`), `HALT`.
     - Program ini **tidak** memuat `loader.hasm` dan **tidak** mengeksekusi opcode `CTHETA (0x4E)`, `HDOT (0x52)`, atau `HPACK (0x50)` saat boot dari SRAM. Pengujian `CTHETA = 8`, `HDOT = 69`, dan `HPACK guard_status = 0x3F` dilakukan pada simulasi testbench `T27` dengan menyuntikkan 6 instruksi ke `dut.u_hcpu_core.imem[0..5]`. Karena `cosmictera_unified_soc_stage1_5.fs` memanggang `test_bsm.hasm` (bukan `loader.hasm`), papan fisik tidak dapat menerima program baru lewat kabel UART tanpa mengganti `PROGRAM_HEX` (yang dilarang selama pengujian bitstream ini).

---

### Target F — Status Implementasi & Bukti Verifikasi Komponen Ekosistem (`HCPU`, `H-ISA`, `GAP-02`, `HMCL`, `HOS`, `HFS`, `HAR`, `HC`, `HVM/HCVM`, `NUI`)

Kami memverifikasi langsung kode sumber dan menjalankan suite pengujian paritas (`pytest tests/test_hisa/test_isa_parity.py tests/test_hisab/test_gap02_guard_hisab_parity.py` -> **`378 passed in 0.45s`**):

| Subsistem / Komponen | Lokasi Source Kanonik | Status Bukti & Verifikasi Aktual | Label Epistemik (`R2`) |
| :--- | :--- | :--- | :---: |
| **Fondasi Matematika & Master Table 28×18D** | `src/hijaiyyah/core/master_table.py`, `rtl/hcpu_rom.v` (`ROM_ADDR_W=6`, `1..28` huruf + `31..36` vektor negatif) | Segel SHA-256 Master Table utuh; paritas 100% antara Python dan `rtl/hcpu_rom.v`. | **`VF` / `CC`** |
| **H-ISA v1.2 (`CTHETA=0x4E`, `HDOT=0x52`)** | `rtl/hcpu_pkg.vh` (baris 184 `OP_CTHETA = 8'h4E`, baris 195 `OP_HDOT = 8'h52`), `docs/HISA_SPEC.md`, `src/hijaiyyah/hisa/opcodes.py` | **105 opcode unik** (`0` alias), **84 diimplementasikan di RTL** (`56` non-huruf + `28` huruf `0xE0–0xFB`), **21 software-only**. `test_isa_parity.py`: **`375 / 375 PASS`**. | **`VF` / `CC`** |
| **`GAP-02` (`hcpu_hisab.v` -> `hcpu_guard.v`)** | `rtl/hcpu_hisab.v` (baris 61–76), `rtl/hcpu_guard.v` | `hcpu_hisab.v` menginstansiasi `hcpu_guard #(.PIPELINE_GUARD(0)) u_guard` secara langsung (`0` duplikasi rumus, memeriksa `G1..G4, T1..T2, H*`). `test_gap02_guard_hisab_parity.py`: **`3 / 3 PASS` (46 vektor + simulasi pipa HCPU)**. | **`CC`** |
| **HCPU 5-Stage Pipeline & Standalone Wrapper** | `rtl/hcpu_top.v`, `rtl/hcpu_*.v`, `rtl/fpga/gowin/hcpu_gowin_top.v` | Terbukti di silikon Tang Nano 20K (`cosmictera-build/PAPAN.md`: 24 program HCPU + 11 bench + burn-in 72 jam). Bitstream di repo: `rtl/fpga/gowin/hcpu_gowin_top.fs` (`SHA-256 = 38956d88...`, Paket 8 `USE_DSP=0`, `15.453` LUT4). | **`CC` (Sim/P&R) & Validasi Fisik (`PAPAN.md`)** |
| **HMCL (*Hijaiyyah Mathematics Computer Laboratory*)** | `src/hijaiyyah/hmcl/`, `rtl/tb/tb_hmcl_rtl_alternatives.v` | Laboratorium simulasi multi-level dan eksplorasi alternatif arsitektur (`CODEX_PROFILE 0/1/2`); terpisah dari HCPU runtime dan NUI. | **`CC`** |
| **HOS, HFS & HAR** | `src/hijaiyyah/{hos,hfs,har}/`, `rtl/programs/{loader,kernel,hos,shell,hos_hfs_disk,hos_prog_load}.hasm` | `loader.hasm`, `kernel.hasm`, `hos.hasm`, `shell.hasm`, dan persistensi SDIO/HFS lulus testbench RTL (`39/39`) dan pengujian papan di `PAPAN.md`. | **`CC`** |
| **Bahasa HC, Compiler, HVM & HCVM** | `src/hijaiyyah/language/`, `src/hijaiyyah/compiler/codegen.py`, `src/hijaiyyah/hvm/vm.py`, `src/hijaiyyah/hcvm/` | Compiler `.hc -> .hasm` dan VM berjalan deterministik (`CC`); batas alokasi register `R0–R17` vs field 4-bit `R0–R15` tercatat sebagai `GAP-03`. Kata kunci Arab/Indonesia langsung di lexer masih `AT`. | **`CC` (`AT` untuk lexer multibahasa)** |
| **NUI (*Natural Universal Intelligence*, L0–L11)** | `src/hijaiyyah/nui/*.py` (43 modul), `NUI/LAYERS.md`, `NUI/LAYER6_ADDENDUM.md` | L0 (Facts), L1 (Repo Graph), L2 (Program Graph), L3 (Execution Trace), L4 (SW/HW Parity), L5 (Lima Read-Only Gate), L6 (Hardware Provenance & Addendum `ea3c5b22`), L7 (Fail-Closed Decision), dan KB L9 telah terimplementasi dan teruji (`CC`). L8 (pemicu otonom penuh), mesin inferensi deduktif L9, L10, dan L11 berstatus `AT`. | **`CC` (L0–L7, KB L9) / `AT` (L8, Inf L9, L10–L11)** |
| **Unified SoC Stage 1.5 (`cosmictera_unified_soc_top`)** | `cosmictera-build/stage-1-5-unified-soc/` | Lulus 33/33 testbench RTL, 0/194.048 selisih piksel golden frame, lulus Yosys & `nextpnr-himbaechel` (`14.695` LUT4, `38` BSRAM). **Belum divalidasi pada papan fisik.** | **`CC` (Sim & P&R PASS — Physical Validation PENDING)** |

---

### Target G — Klasifikasi Berkas Repositori: Kanonik vs Superseded vs Eksperimen/Prototipe

| Klasifikasi | Lokasi Berkas / Direktori | Keterangan & Aturan Perlindungan |
| :--- | :--- | :--- |
| **1. KANONIK (Wajib Dilindungi, Dilarang Diubah Tanpa Otorisasi)** | - `rtl/hcpu_*.v`, `rtl/hcpu_pkg.vh`<br>- `rtl/fpga/gowin/hcpu_gowin_top.v`, `rtl/fpga/gowin/hcpu_gowin.cst`<br>- `constraints/cosmictera_tangnano20k.cst` (`SHA-256 = 3f16df4f...`)<br>- `src/hijaiyyah/**`, `tests/**`, `NUI/**`, `facts/**`<br>- `cosmictera/RULES.md`, `cosmictera/SYSTEM.md`, `cosmictera/CONCRETE.md`, `docs/HISA_SPEC.md`<br>- `cosmictera-build/{PAPAN,ON,OFF,CHECKLIST,ROADMAP}.md`<br>- Bitstream di `rtl/fpga/gowin/*.fs` (`hcpu_gowin_top.fs` `38956d88...`, `hcpu_gowin_top_loader.fs` `84fdc912...`, dll.)<br>- Paket 14 dokumen arsitektur edisi **`v1.2`** (`COSMICTERA_MASTER_SYSTEM_ARCHITECTURE_CT01_REV13.md`, dll.) | Merupakan kontrak spesifikasi, implementasi teruji, dan catatan bukti fisik silikon. |
| **2. SUPERSEDED (Tidak Berlaku sebagai Referensi Implementasi Baru)** | - Klaim paket dokumentasi arsitektur versi `v1.0` yang telah dikoreksi oleh `K-01..K-12` (tercatat di `COSMICTERA_CONSISTENCY_CORRECTION_REPORT.md`)<br>- Bagian C–E di `COSMICTERA_CONSISTENCY_CORRECTION_REPORT.md` yang merekam kondisi *sebelum* commit `1aed5e1f` (ketika `OP_HDOT` masih di `0x4E` sebelum dipindah ke `0x52`)<br>- Berkas kandidat CST lama `cand_A`, `cand_C`, `cand_D`, `cand_E`, `cand_F` di `/tmp/stage1_2_cosmictera_boot_ui/`<br>- `rtl/fpga/gowin/cosmictera_display_top.v` (`NOT INSTRUMENTED`, mendahului Boot UI Stage 1.3/1.4/1.5) | Dipertahankan hanya sebagai catatan sejarah audit; jangan digunakan sebagai acuan encoding atau pinout. |
| **3. PROTOTIPE TERISOLASI / EKSPERIMEN AKTIF** | - **`cosmictera-build/stage-1-5-unified-soc/**`** (`cosmictera_unified_soc_top.v`, `cosmictera_unified_soc_stage1_5.fs` `02c0a44f...`, `cosmictera_boot_top_stage1_5.fs` `88bb395f...`)<br>- `/tmp/stage1_2_cosmictera_boot_ui/**` (artefak kerja Stage 1.2–1.4) | Berada pada direktori kerja terisolasi untuk pengujian fisik SRAM Stage 1.5. Tidak boleh menimpa artefak kanonik. |

*(Catatan Audit Forensik tentang `hcpu_gowin_top_standalone.fs`)*: Dokumen `COSMICTERA_STAGE1_5_UNIFIED_SOC_REPORT.md` menyebut nama berkas `hcpu_gowin_top_standalone.fs` (`961af9b9...`, `15.377` LUT4, `54,69 MHz`), tetapi pencarian menyeluruh di `/Users/AMRA/hijaiyyah-mathematics` dan `/tmp` menunjukkan bahwa berkas dengan nama `hcpu_gowin_top_standalone.fs` tidak berada di pohon direktori saat ini; bitstream standalone HCPU yang tersimpan secara fisik di repositori adalah `rtl/fpga/gowin/hcpu_gowin_top.fs` (`SHA-256 = 38956d8842bd1bb191477dbc3f4094afa5c833fdb2645dd97b25453891947abd`, `15.453` LUT4), `hcpu_gowin_top_loader.fs` (`84fdc912...`), `hcpu_gowin_top_boot.fs` (`831b10e7...`), dan `hcpu_gowin_top_persist.fs` (`19815000...`). Keempatnya utuh dan tidak tersentuh.

---

### Target H — Peta Arsitektur Lengkap Unified SoC Stage 1.5

#### H.1 Hierarki Modul Top-Level (`cosmictera_unified_soc_top.v`)

```text
cosmictera_unified_soc_top (cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_unified_soc_top.v)
├── [Domain clk_27m: 27,000 MHz (Pin 4)]
│   ├── Reset & Mode Toggle Synchronizer (btn_rst_n Pin 87 -> btn_pulse_rst_n, live_hcpu_mode toggle)
│   └── u_hcpu_core : hcpu_gowin_core (rtl/fpga/gowin/hcpu_gowin_top.v, USE_PLL=0, USE_DSP=1, BAUD=115200)
│       ├── imem [0:4095] (32-bit x 4096 = 8 BSRAM, diinisialisasi dengan program.hex = test_bsm.hasm)
│       ├── u_hcpu : hcpu_top (rtl/hcpu_top.v — Pipa 5-Tahap IF -> ID -> EX -> MEM -> WB)
│       │   ├── u_fetch      : hcpu_fetch
│       │   ├── u_decode     : hcpu_decode (84 opcode RTL, CTHETA=0x4E, HDOT=0x52)
│       │   ├── u_forward    : hcpu_forward (EX->ID & MEM->ID GPR + 144-bit H-Reg bypass)
│       │   ├── u_execute    : hcpu_execute (RA_DEPTH=32 RAS, ALU, branch/jump, privilege checks)
│       │   │   └── u_mul    : hcpu_mul (MULT36X36)
│       │   ├── u_memory     : hcpu_memory (STACK_DEPTH=256 hardware stack = 1 BSRAM)
│       │   ├── u_writeback  : hcpu_writeback
│       │   ├── u_regfile    : hcpu_regfile (18x32b GPR R0..R17 + 16x144b H-Reg H0..H15, RAM16SDP4/DFF)
│       │   ├── u_rom        : hcpu_rom (6-bit addr: 1..28 Huruf Kanonik + 31..36 Vektor Negatif)
│       │   ├── u_guard      : hcpu_guard (G1..G4, T1..T2, H*, U, rho bertanda)
│       │   ├── u_codex_alu  : hcpu_codex_alu (USE_DSP=1 -> 14x MULT9X9 pada netlist; USE_DSP=0 -> 14-cyc HDOT)
│       │   ├── u_hisab      : hcpu_hisab -> u_guard : hcpu_guard (GAP-02 terintegrasi)
│       │   ├── u_uart       : hcpu_uart_tx (PRINT & EMITS transmitter -> core_txd)
│       │   ├── u_mmio       : hcpu_mmio (Jendela 0xFE0..0xFFF)
│       │   │   ├── u_rx     : hcpu_uart_rx (Pin 70 uart_rxd)
│       │   │   ├── u_timer  : hcpu_timer (32-bit counter/compare)
│       │   │   └── u_sdio   : hcpu_sdio (Pins 80..85 SDIO 1-bit + 128-word sector buffer = 1 BSRAM)
│       │   ├── u_trap       : hcpu_trap (6 causes, EPC, User/Supervisor mode)
│       │   ├── u_dataram    : hcpu_dataram (4096 x 32-bit Data RAM = 8 BSRAM)
│       │   └── u_controller : hcpu_controller (stall & flush orchestration)
│       └── u_report_tx : hcpu_uart_tx (19-byte "\r\nCYCLES=XXXXXXXX\r\n" reporter -> Pin 69 uart_txd)
│
├── [ Sintesis Clock Video & Reset Bertahap ]
│   ├── u_tmds_rpll  : TMDS_rPLL (27,000 MHz -> 371,250 MHz serial_clk + pll_locked)
│   ├── u_clkdiv     : CLKDIV /5 (371,250 MHz -> 74,250 MHz pixel_clk)
│   └── u_reset_seq  : cosmictera_boot_reset_seq (Kualifikasi lock 2 ms = 54.000 siklus clk_27m;
│                      urutan pelepasan: clkdiv_rst_n -> oser_rst -> vid_rst_n)
│
├── [ Jembatan CDC (`clk_27m` <-> `pixel_clk`) ]
│   ├── u_uptime        : cosmictera_boot_uptime (1 Hz BCD counter @ 27 MHz -> toggle CDC -> pixel_clk)
│   └── u_subsys_bridge : cosmictera_boot_subsys_bridge (87-bit telemetry bridge + 16-entry ecosystem state)
│
└── [Domain pixel_clk: 74,250 MHz & serial_clk: 371,250 MHz]
    ├── u_timing     : hcpu_video_timing (1280x720@60Hz VESA: 1650x750 total, HSYNC/VSYNC positif)
    ├── u_page       : hcpu_page_key (Pin 88 mode_key debounce -> page 0..12 [P0..P12])
    ├── u_events     : cosmictera_boot_events (8-entry hardware event FIFO EV01..EV06)
    ├── u_logo       : cosmictera_boot_logo_rom (8 SPX9 BSRAM logo_rle_rom + 1 SP BSRAM boot_emblem_rom)
    ├── u_text_rom   : cosmictera_boot_text_rom (3 SP BSRAM boot_text_rom)
    ├── u_compositor : cosmictera_boot_compositor (3 SP BSRAM boot_comp_rom + 2 SP BSRAM boot_cell_tag_rom)
    ├── u_font       : hcpu_font_rom (1 SPX9 BSRAM hcpu_font8x8)
    ├── u_render     : cosmictera_boot_render (1 SP BSRAM boot_bg_x_rom + 1 SP BSRAM boot_bg_y_rom;
    │                  3-stage synchronous pixel pipeline -> red_dvi, green_dvi, blue_dvi)
    └── u_dvi_tx     : DVI_TX_Top (3x TMDS 8b/10b encoders + 4x OSER10 10:1 -> Pins 33, 35, 37, 39)
```

#### H.2 Pemetaan Alokasi 38 Blok BSRAM (`18` HCPU + `20` Boot Display)
1. **Subsistem HCPU (`18` BSRAM)**:
   - `imem` (`4.096 × 32-bit`): **`8` BSRAM** (`DPB`/`SP`).
   - `u_dataram` (`4.096 × 32-bit`): **`8` BSRAM** (`SP`).
   - `u_memory` (`STACK_DEPTH = 256 × 32-bit` hardware data stack): **`1` BSRAM** (`SDPX9B`).
   - `u_sdio` (`128 × 32-bit` sector buffer): **`1` BSRAM** (`SDPX9B`).
2. **Subsistem Boot Display Stage 1.5 (`20` BSRAM)**:
   - `logo_rle_rom.hex` (`16.384 × 9-bit` Hero Logo `512×184` RLE): **`8` BSRAM** (`SPX9`).
   - `boot_text_rom.hex` (`4.096 × 12-bit` matriks teks statis 25 baris): **`3` BSRAM** (`SP`).
   - `boot_comp_rom.hex` (`4.096 × 12-bit` 60 slice dinamis & halaman `P1–P12`): **`3` BSRAM** (`SP`).
   - `boot_cell_tag_rom.hex` (`4.096 × 8-bit` tag koordinat sel `160×90`): **`2` BSRAM** (`SP`).
   - `boot_bg_x_rom.hex` (`2.048 × 8-bit` dekoder chrome horizontal): **`1` BSRAM** (`SP`).
   - `boot_bg_y_rom.hex` (`1.024 × 8-bit` dekoder chrome vertikal): **`1` BSRAM** (`SP`).
   - `boot_emblem_rom.hex` (`4.096 × 4-bit` emblem header `24×24`): **`1` BSRAM** (`SP`).
   - `hcpu_font8x8.hex` (`1.024 × 8-bit` bitmap font `8×8`): **`1` BSRAM** (`SPX9`).
   - **Total**: **`38 / 46` BSRAM (`82,61%`)**, menyisakan `8` BSRAM bebas.

#### H.3 Pipeline Sinkron BSRAM 3-Tahap pada Boot Display (`74,25 MHz`)
- **Stage 0 (`la_col`, `la_row` — 2 piksel di depan `h_count`)**: `cosmictera_boot_render` menghitung koordinat lookahead `la_col` dan `la_row`. `u_text_rom` dan `u_compositor` (`comp_rom` + `cell_tag_rom`) menerima alamat baca BSRAM pada tepi naik `pixel_clk`.
- **Stage 1 (`comp_rom_q`, `tag_rom_q`, `text_rom_data` — 1 piksel di depan `h_count`)**: `u_compositor` mendekode `tag_code`, memilih nibble dinamis (`sel_nib`), dan menghasilkan `comp_cell_s1 = {attr[3:0], glyph[7:0]}`. `u_render` memilih `cell_s1 = (|comp_cell_s1[7:0]) ? comp_cell_s1 : text_rom_data`, mengumpankan `font_glyph = cell_s1[6:0]` dan `font_row = row_d` ke BSRAM `u_font` (`hcpu_font_rom`), sekaligus membaca `bg_x_rom[h_count]` dan `bg_y_rom[vla]`.
- **Stage 2 (`font_bits`, `attr_d2`, `bg_x_q`, `bg_y_q` — selaras dengan `h_count, v_count`)**: `u_render` memilih bit piksel `font_bits[7 - h_count[2:0]]`, menggabungkannya dengan `logo_pixel_rgb`, `text_rgb`, atau `bg_rgb`, lalu mendaftarkannya ke register pipa DVI (`red_dvi`, `green_dvi`, `blue_dvi`, `de_dvi`, `hsync_dvi`, `vsync_dvi`) sebelum masuk ke `DVI_TX_Top`.

---

### Target I — Identifikasi Risiko Paling Penting Sebelum Pengujian Fisik

| ID Risiko | Tingkat Risiko | Deskripsi Masalah & Bukti Teknis | Dampak pada Pengujian Fisik | Mitigasi Saat Validasi Fisik |
| :--- | :---: | :--- | :--- | :--- |
| **RISK-01: Margin Timing `pixel_clk` Tipis (`+0,28 ns`)** | **TINGGI** | `nextpnr_unified_soc_stage1_5.log` mencatat Fmax `pixel_clk` = **`75,83 MHz`** (`13,19 ns`) terhadap target `74,25 MHz` (`13,47 ns`), menyisakan slack hanya **`+0,28 ns`**. Jalur kritis melalui `u_compositor.cell_tag_rom -> sel_nib -> u_render.cell_s1 -> u_font.rom.AD7`. | Potensi artefak piksel/karakter pada teks dinamis (terutama baris 56 Region 5) atau gangguan sinkronisasi saat suhu chip meningkat selama operasi 30 menit. | Prioritaskan inspeksi visual dekat pada teks baris 56 Region 5 (`P0–P12`), logo Chrome Orbit, dan jalankan uji stabilitas termal 30 menit pada TV HDMI. |
| **RISK-02: Bypass Register CDC 84-Bit oleh `` `ifdef YOSYS ``** | **SEDANG** | Di `cosmictera_boot_subsys_bridge.v` baris 97–105, `` `ifdef YOSYS `` menghubungkan `snap_pc`, `snap_instr`, `snap_cycles`, dan `snap_flags` langsung dari `src_*` tanpa register snapshot `pixel_clk` (`9,66 ns` jalur lintas-domain). | Karena `test_bsm.hasm` selesai dalam `0,261 ms` dan berhenti (`halted = 1`), nilai telemetri bersifat *quasi-static* setelah boot. Namun jika di masa depan HCPU menjalankan loop tak-berhenti, baris 56 dapat mengalami flicker nibble. | Pada pengujian `test_bsm.hasm` saat ini, amati apakah string `CY:00001B89` tampil bersih dan stabil tanpa perubahan digit acak setelah `HLT`. |
| **RISK-03: Toggle `live_hcpu_mode` via Pin 87 (`btn_rst_n`)** | **SEDANG** | Pada saat SRAM baru selesai dimuat, `live_hcpu_mode` bernilai `0` sehingga layar HDMI menampilkan nilai BIST statis Stage 1.4 (`CY:0002C1C9 ... RUN`). `live_hcpu_mode` baru bernilai `1` (`CY:00001B89 ... HLT`) setelah Pin 87 (`btn_rst_n`) ditekan satu kali. | Operator dapat mengira jembatan telemetri CDC gagal bekerja pada saat boot awal (sebelum menekan tombol Pin 87), atau bingung mengapa penekanan Pin 87 berikutnya mengembalikan tampilan ke `CY:0002C1C9`. | Dalam prosedur Run 1 & Run 2, catat tampilan awal (`live_hcpu_mode = 0`), lalu tekan tombol S2/Pin 87 satu kali untuk memverifikasi mode live (`CY:00001B89 ... G:OK HLT CDC:LIVE`) sekaligus menangkap ulang pancaran UART 23-byte. |
| **RISK-04: Perbedaan Urutan Newline pada Skrip `run_stage1_5_sram_validation.py` vs RTL Aktual** | **SEDANG** | `run_stage1_5_sram_validation.py` baris 22 mengharapkan `31 31 32 0D 0A ... 0D 0A 0A`, `tb_unified_soc_stage1_5.v` baris 215 memeriksa `31 31 32 0A 0A ... 0D 0A 0A`, sedangkan `hcpu_top.v` + `hcpu_gowin_top.v` memancarkan `31 31 32 0A 0D 0A ... 0D 0A` (`"112\n\r\nCYCLES=00001B89\r\n"`, 23 byte). | Jika hanya menggunakan perbandingan `== EXPECTED_UART_BYTES` di skrip tanpa memeriksa byte mentah, pengujian yang sebenarnya berhasil (`112` dan `CYCLES=00001B89` tepat 23 byte) bisa dilaporkan sebagai `[WARN]`. | Rekam seluruh byte mentah UART dalam format heksadesimal dan ASCII beserta SHA-256-nya, lalu verifikasi payload `"112"` dan `"CYCLES=00001B89"` serta jumlah tepat 23 byte. |
| **RISK-05: Perbedaan Binary `openFPGALoader` (`/opt/homebrew/bin` vs `oss-cad-suite`)** | **RENDAH–SEDANG** | `run_stage1_5_sram_validation.py` menunjuk ke `/Users/AMRA/opt/oss-cad-suite/bin/openFPGALoader`, sedangkan validasi fisik Stage 1.3 & 1.4 yang berhasil (`COSMICTERA_STAGE1_4_HARDWARE_VALIDATION.md`) menggunakan `/opt/homebrew/bin/openFPGALoader -b tangnano20k`. Selain itu, eksekusi dari dalam sandbox tanpa izin akses perangkat USB akan ditolak (`unable to open ftdi device: -3`). | Pemanggilan `openFPGALoader` gagal membuka FTDI JTAG jika dijalankan di dalam sandbox terisolasi atau menggunakan binary yang tidak terhubung dengan `libftdi` sistem. | Gunakan `/opt/homebrew/bin/openFPGALoader -b tangnano20k` (atau pastikan akses perangkat USB diizinkan oleh operator) dalam mode **SRAM ONLY** (tanpa flag `-f` / `--write-flash`). |
| **RISK-06: Blok Hard-DSP (`1 MULT36X36 + 14 MULT9X9`) Aktif pada Bitstream Stage 1.5** | **RENDAH** | Bitstream `cosmictera_unified_soc_stage1_5.fs` disintesis dengan `USE_DSP = 1` (tanpa `-nodsp`), berbeda dari `hcpu_gowin_top.fs` standalone yang memakai `-nodsp`. | Jika `gowin_pack` mengemas atribut `MULT36X36` pada `hcpu_mul` atau `MULT9X9` pada `hcpu_codex_alu` secara akurat, sistem bekerja normal (`test_bsm.hasm` memakai `HNRM2`). | Verifikasi bahwa keluaran UART pada papan fisik tetap menghasilkan `112` (`HNRM2 R0, H2` = $6^2 + 6^2 + 4^2 + 2^2 + 2^2 + 4^2 = 112$). Jika `112` keluar dengan tepat, maka blok DSP terbukti berfungsi secara fisik di silikon! |

---

## 3. TABEL PEMISAHAN FAKTA, KLAIM, BUKTI SOURCE, HASIL UJI, DAN ITEM BELUM TERVERIFIKASI

| Aspek Pemeriksaan | Klaim Dokumentasi (`COSMICTERA_STAGE1_5_UNIFIED_SOC_REPORT.md`) | Bukti dari Source Code & Log Build | Hasil Pengujian Aktual Saat Ini | Informasi yang Belum Dapat Diverifikasi (Menunggu Uji Fisik) |
| :--- | :--- | :--- | :--- | :--- |
| **Integrasi Top-Level Unified SoC** | Menggabungkan `hcpu_gowin_core` + `cosmictera_boot_top` Stage 1.5 dalam satu FPGA. | [`cosmictera_unified_soc_top.v`](cosmictera-build/stage-1-5-unified-soc/rtl/cosmictera_unified_soc_top.v) menginstansiasi `u_hcpu_core`, `u_tmds_rpll`, `u_clkdiv`, `u_reset_seq`, `u_subsys_bridge`, `u_compositor`, `u_render`, `u_dvi_tx`. | **SIM & P&R PASS (`CC`)**: `33/33` TB pass; `0` unrouted net. | Operasi simultan fisik HCPU + HDMI TMDS pada papan Tang Nano 20K. |
| **Utilisasi Sumber Daya FPGA** | `14.695` LUT4 (`70,87%`), `2.600` ALU, `5.572` DFF, `38` BSRAM (`82,61%`), `1` MULT36X36, `14` MULT9X9. | Terbukti eksak di [`nextpnr_unified_soc_stage1_5.log`](cosmictera-build/stage-1-5-unified-soc/nextpnr_unified_soc_stage1_5.log) baris 90–122. | **MEASURED IN P&R (`CC`)**. | Konsumsi daya dan suhu papan saat 38 BSRAM + 15 DSP + HDMI aktif bersama. |
| **Keluaran UART 23-Byte (`test_bsm.hasm`)** | Memancarkan `112` dan `CYCLES=00001B89` (23 byte) pada 115.200 baud Pin 69. | `program.hex` berisi 9 kata `test_bsm.hasm`; `hcpu_gowin_core` memiliki FSM pelapor `CYCLES=`. | **SIM PASS (`T25`)**: `cycle_count = 0x00001B89`, `led[0]=0, led[1]=0`. | Rekaman fisik 23 byte dari `/dev/cu.usbserial-20250303171` pada Run 1 & Run 2 untuk `cosmictera_unified_soc_stage1_5.fs`. |
| **Jembatan Telemetri CDC (`Region 5` Baris 56)** | Menampilkan `CY:00001B89`, `G:OK`, `HLT`, `CDC:LIVE` dari HCPU nyata. | `u_subsys_bridge` menghubungkan `hcpu_tele_*` ketika `bridge_telem_en = 1` (diaktifkan oleh toggle `btn_rst_n` Pin 87). | **SIM PASS (`T26`)**. | Tampilan visual nyata baris 56 pada TV HDMI sebelum dan sesudah menekan tombol S2 (`Pin 87`). |
| **Navigasi Halaman `P0–P12` (`Pin 88`)** | Tombol S1 (`Pin 88`) menggilir halaman `P0 -> P1..P12 -> P0` tanpa merusak teks/logo. | `u_page` (`PAGES=13`) dan `boot_comp_rom.hex` memuat seluruh slice halaman `P1–P12`. | **SIM PASS (`T24a–T24f`)** & `0 / 194.048` selisih piksel golden frame. | Pengamatan visual fisik seluruh halaman `P0–P12` pada TV HDMI dengan bitstream Stage 1.5. |
| **Paritas H-ISA `CTHETA=0x4E`, `HDOT=0x52`, & `GAP-02`** | `CTHETA=8`, `HDOT=69`, dan `HPACK guard_status=0x3F`. | Terbukti di `rtl/hcpu_pkg.vh`, `rtl/hcpu_execute.v`, `rtl/hcpu_codex_alu.v`, `rtl/hcpu_hisab.v`. | **SIM & PYTEST PASS (`CC`)**: `378/378` pytest + `T27` di `tb_unified_soc_stage1_5.v`. | Karena `program.hex` di bitstream Stage 1.5 adalah `test_bsm.hasm` (bukan `loader.hasm`), instruksi `CTHETA`/`HDOT`/`HPACK` tidak dieksekusi saat boot SRAM kecuali diuji via bitstream `loader.hasm` terpisah. |

---

## 4. REKOMENDASI TINDAKAN BERIKUTNYA (TARGET J)

Berdasarkan temuan objektif di atas, berikut adalah urutan langkah rekayasa yang direkomendasikan untuk menuntaskan **Prioritas 1 — Physical Validation Unified SoC Stage 1.5 (SRAM ONLY)**:

1. **Pertahankan Isolasi dan Perlindungan Artefak (`Wajib`)**:
   - Jangan mengubah satu byte pun pada `cosmictera_unified_soc_stage1_5.fs` (`02c0a44f28dfa35f41389ed34217b9ea22bdfdf42e13911aefb93e948392a3c4`), RTL, maupun constraints selama sesi validasi fisik ini.
   - Pastikan kedua berkas terlacak yang terhapus di working tree (`rtl/tb/nui_embedding.hex` dan `rtl/tb/nui_payload.txt`) dipulihkan dengan `git checkout -- rtl/tb/nui_embedding.hex rtl/tb/nui_payload.txt` bila pemilik menghendaki working tree terlacak yang bersih.
2. **Jalankan Tahap 1, Run 1, dan Run 2 Pemrograman SRAM + Rekaman UART dengan Akses Perangkat USB**:
   - Gunakan programmer `/opt/homebrew/bin/openFPGALoader -b tangnano20k` (atau `/Users/AMRA/opt/oss-cad-suite/bin/openFPGALoader -b tangnano20k` dengan izin akses USB di luar sandbox) dalam **mode SRAM ONLY** (tanpa flag `-f` / `--write-flash`).
   - Buka port serial `/dev/cu.usbserial-20250303171` pada `115200 8N1 raw` **sebelum** pemuatan SRAM selesai agar seluruh 23 byte pancaran awal (`0,261 ms` pasca-konfigurasi) tertangkap utuh pada **Run 1** dan **Run 2**.
   - Simpan byte mentah apa adanya (`uart_run1_stage1_5.bin` dan `uart_run2_stage1_5.bin`), cetak representasi hex 23-byte dan SHA-256-nya, serta verifikasi kesamaan deterministik 100% antara Run 1 dan Run 2 (`112` dan `CYCLES=00001B89`).
3. **Prosedur Pengujian Visual HDMI, Toggle Telemetri Live (`Pin 87`), dan Halaman `P0–P12` (`Pin 88`)**:
   - **Langkah Visual A (Saat Boot SRAM Awal, `live_hcpu_mode = 0`)**: Amati layar HDMI `1280×720 @ 60 Hz`, pastikan gambar terkunci stabil, Logo Chrome Orbit `512×184` dan Emblem `24×24` utuh, ke-16 entri ekosistem tampil hijau (`✓`), dan baris 56 menampilkan snapshot BIST awal (`PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE`).
   - **Langkah Visual B (Aktifkan Telemetri HCPU Live dengan Menekan Tombol S2 / `Pin 87` Satu Kali)**: Tekan tombol `btn_rst_n` (`Pin 87`) satu kali. Verifikasi bahwa:
     1. HCPU melakukan reset dan memancarkan ulang 23 byte UART (`112` & `CYCLES=00001B89`) ke terminal serial.
     2. `live_hcpu_mode` bertransisi menjadi `1`, sehingga baris 56 Region 5 pada layar HDMI berubah secara live menjadi:
        `PC:008 IN:01000000 CY:00001B89 FL:01 G:OK HLT CDC:LIVE`
     3. LED onboard aktif-rendah menyala sesuai status `guard_ok` (`LED[0]`) dan `halted` (`LED[1]`).
   - **Langkah Visual C (Inspeksi Halaman `P0–P12` via Tombol S1 / `Pin 88`)**: Tekan tombol `mode_key` (`Pin 88`) secara bertahap dari `P0` -> `P1` .. `P12` -> kembali ke `P0`, dan dokumentasikan foto/rekaman tampilan.
   - **Langkah Visual D (Uji Stabilitas `pixel_clk` Selama 30 Menit)**: Biarkan papan beroperasi selama ~30 menit sambil memantau apakah margin `+0,28 ns` pada `pixel_clk` (`75,83 MHz`) tetap bebas dari pergeseran piksel, perubahan warna, kehilangan sinkronisasi HDMI (`RELOCK COUNT` tetap `00`), atau artefak karakter pada baris 56.

---

**Status Akhir Saat Ini:**
- **Audit Baseline & Rekonstruksi Arsitektur (`Target A–J`)**: **SELESAI (`PASS`)**.
- **Status Unified SoC Stage 1.5**: **`P&R PASS — PHYSICAL VALIDATION PENDING`** (siap dieksekusi ke SRAM Tang Nano 20K begitu akses perangkat USB JTAG/UART diizinkan oleh pemilik).
