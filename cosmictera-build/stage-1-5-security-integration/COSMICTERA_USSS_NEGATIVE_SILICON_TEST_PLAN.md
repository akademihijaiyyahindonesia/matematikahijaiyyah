# RENCANA & SPESIFIKASI UJI KEAMANAN NEGATIF PADA SILIKON (`USSS STAGE 1.5`)
# (`COSMICTERA_USSS_NEGATIVE_SILICON_TEST_PLAN.md`)

**Agen Rekayasa:** ARGON (*Architecture, Research, Governance, Optimization & Neural Technology*)  
**Cabang Aktif:** `stage-1-5-security-integration` (`HEAD = ea3c5b22`)  
**Target Perangkat Keras:** Sipeed Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`idcode 0x81b`)  
**Bitstream Baseline Fisik Aktif:** `cosmictera_unified_soc_usss.fs`  
**SHA-256 Bitstream:** `723ce67f0098157042a1bd389071d41fb28cee9a1eeb3282424f8ef4c7fdae18`  
**Mode Operasi:** **SRAM ONLY** (External Flash dilarang diprogram; RTL dan constraints tidak diubah)

---

## 1. AUDIT FORENSIK BUKTI FOTO MONITOR HDMI (`WhatsApp Image 2026-11-05 at 02.33.46.jpeg`)

Pemeriksaan langsung terhadap foto fisik layar HDMI bersama berkas bukti [`logs/sram_load_usss_evidence.json`](logs/sram_load_usss_evidence.json), [`logs/sram_load_usss.log`](logs/sram_load_usss.log), dan [`logs/uart_usss.bin`](logs/uart_usss.bin) mengonfirmasi fakta-fakta perangkat keras berikut:

### 1.1 Elemen yang Terbukti Berjalan Live di Silikon (`PASS`)
1. **Sinkronisasi Video & Waktu Jalan (`Panel A, B, C, D`)**:
   - Resolusi `1280X720 60HZ` (`FRAME: 1650X750P`, `STATUS: ACTIVE`) dan `74.25 MHZ CFG` (`RPLL 371.25 / DIV 5`, `STATUS: LOCKED`) terkunci stabil.
   - `PANEL C: BOOT ELAPSED` menampilkan `00:02 (00:02:13)` (`27.000 MHZ HW TICK`, `COUNTER: MONOTONIC`), membuktikan pencacah BCD 1 Hz di domain `clk_27m` dan jembatan CDC ke `pixel_clk` berjalan terus-menerus selama lebih dari 2 menit 13 detik.
2. **Telemetri HCPU Live (`Region 5` Baris 56)**:
   - Menampilkan `PC:00F IN:00000000 CY:00001B89 FL:01 G:OK HLT CDC:LIVE`.
   - `CY:00001B89` (`7.049` siklus) dan `FL:01 G:OK HLT` cocok 100% dengan rekaman [`logs/uart_usss.bin`](logs/uart_usss.bin) (`31 31 32 0A 0A 43 59 43 4C 45 53 3D 30 30 30 30 31 42 38 39 0D 0A 0A` = `112\n\nCYCLES=00001B89\r\n\n`).
   - Nilai `PC:00F` (`IN:00000000` = `NOP`) adalah alamat *fetch pointer* aktual di silikon setelah instruksi `HALT` pada `imem[8]` mencapai tahap Writeback (`WB`).
3. **Telemetri Keamanan USSS Live (`Region 6` Baris 83)**:
   - Menampilkan `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0`.
   - Membuktikan bahwa *power-on self-test* pada [`rtl/cosmictera_usss_subsys.v`](rtl/cosmictera_usss_subsys.v) (baris 387–405, `req_payload_byte = 19` [Huruf Qaf], 24 putaran Ka'bah + HMAC-SHA256 + Jamrah 7-Node Gate + bidang kendali 7-LUT `3–3–3–3–5–6–7`) selesai dieksekusi di silikon dan menghasilkan keputusan terdaftar `auth_grant_reg = 1` (`V:AUTH`), `total_req_cnt = 1` (`RQ:01`), `total_fail_cnt = 0` (`FL:00`), dan `prio_reason_id = 0` (`R:0`).

### 1.2 Catatan Kejujuran Rekayasa atas Pengamatan Visual pada Foto Layar
Sesuai standar komunikasi Seksi 10 (*"Jika menemukan kelemahan desain, laporkan dengan jujur"*), terdapat tiga pengamatan penting pada foto layar yang wajib dicatat secara transparan:
1. **Indikator `RELOCKS: 03`, `FIFO DEPTH: 08/08 OVERFLOW: OVFL`, dan `EV06` pada `00:00:26`**:
   - Pada foto terlihat `00:00:26 EV06 BOOT UI DISPLAY STATE READY`, `RELOCKS: 03`, dan `FIFO OVF: YES`.
   - Hal ini menunjukkan bahwa sekitar detik ke-26 sejak papan dinyalakan (atau saat tombol reset / negosiasi HDMI berlangsung), `TMDS_rPLL` mengalami 3 kali transisi *relock* yang memicu urutan *staged reset recovery* (`u_reset_seq`) dan menambahkan 3 event baru ke dalam FIFO 8-entri (`6 + 3 > 8` sehingga `fifo_overflow = 1`), lalu sistem berhasil pulih kembali ke `STATE: DISPLAY READY` dan berjalan stabil hingga `00:02:13`.
2. **Kerapatan Vertikal Baris Teks pada Region 5 (Baris 56–57) dan Region 6 Kiri (Baris 81–82)**:
   - Pada Region 5, baris 56 (`PC:00F...`) berhimpitan langsung di atas baris 57 (`✓ HCPU CC 120M` / `✓ HISA CC 82/104 OP`).
   - Pada Region 6 sebelah kiri, baris `00:00:00 EV03 CLKDIV DIV5 74.25 MHZ RELEASE READY` (`la_row = 81`) berhimpitan langsung dengan baris `LAST TRANSITION: ALL 10 DISPLAY STAGES VERIFIED - VIDEO OUTPUT ACTIVE` (`la_row = 82`).
3. **Status Pengujian Keamanan Negatif Saat Ini (`SIMULATED 266/266 & 42/42 — BELUM DIUJI DI PAPAN FISIK`)**:
   - Pada foto layar saat ini, nilai `RQ:01 FL:00 R:0` hanya mencerminkan **1 permintaan positif (Power-On BIST)**. Skenario penolakan negatif (`FL > 00`, `V:REJ` / `V:ERR`) belum dijalankan secara fisik di papan karena `program.hex` yang dipanggang di dalam `cosmictera_unified_soc_usss.fs` adalah `test_bsm.hasm` (9 instruksi yang langsung `HALT` tanpa menulis ke register MMIO `0xFE8` `SEC_CTRL`).

---

## 2. PROSEDUR PEMERIKSAAN FISIK HALAMAN `P0–P12` MELALUI TOMBOL S1 (`PIN 88`)

Dengan `cosmictera_unified_soc_usss.fs` (`723ce67f...`) yang sedang aktif di SRAM Tang Nano 20K, pemeriksaan navigasi halaman `P0–P12` dilakukan tanpa mengubah bitstream maupun me-reset papan:

### 2.1 Perilaku Perangkat Keras `cosmictera_boot_compositor.v` Saat Tombol S1 (`Pin 88`) Ditekan
Berdasarkan [`rtl/cosmictera_boot_compositor.v`](rtl/cosmictera_boot_compositor.v):
- **Baris 56 (`la_row == 7'd56`, kolom `99..152`)**:
  `comp_slice = (page == 4'd0) ? (6'd53 + {3'd0, snap_valid, snap_halted, snap_guard}) : {2'b00, page};`
  - Saat `page == 0` (`PIN88 PAGE: 00`), Baris 56 menampilkan telemetri HCPU live (`PC:00F IN:00000000 CY:00001B89 FL:01 G:OK HLT CDC:LIVE`).
  - Saat `page == 1..12` (`PIN88 PAGE: 01..12`), Baris 56 menampilkan baris inspektor arsitektur `P1` s.d. `P12` dari BSRAM `boot_comp_rom.hex` (`slice 1..12`).
- **Baris 83 (`la_row == 7'd83`, kolom `99..153` — Panel USSS)**:
  `comp_slice = 6'd60 + {4'd0, sec_verdict};` dan `in_sec_bar = (la_row == 7'd83) && (la_col >= 8'd99) && (la_col <= 8'd153);`
  - **Tidak bergantung pada `page`!** Artinya, baris `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` pada Baris 83 **wajib tetap tampil utuh dan koheren** di seluruh 13 halaman (`P0` s.d. `P12`).

### 2.2 Daftar Periksa Visual `P0 -> P1..P12 -> P0` pada Monitor HDMI

| Tekanan Tombol S1 (`Pin 88`) | Indikator Footer (`PIN88 PAGE`) | Teks yang Wajib Tampil pada Baris 56 Region 5 (`la_row = 56`) | Teks yang Wajib Tetap Tampil pada Baris 83 Region 6 (`la_row = 83`) |
| :---: | :---: | :--- | :--- |
| **Awal (`0×`)** | `PIN88 PAGE: 00` | `PC:00F IN:00000000 CY:00001B89 FL:01 G:OK HLT CDC:LIVE` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `1×`** | `PIN88 PAGE: 01` | `P1 L1-L2 HM-28 18D (144B) G1-G4 T1-T2 H* MOD4      VF/CC` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `2×`** | `PIN88 PAGE: 02` | `P2 L7 HISA V1.2: 82/104 OP (54 SYS + 28 LETTER)    VF/CC` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `3×`** | `PIN88 PAGE: 03` | `P3 L8 HCPU 5-STG: 18GPR 16HREG 15453LUT 18BSRAM     [CC]` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `4×`** | `PIN88 PAGE: 04` | `P4 L8 HMCL LAB: 14-LANE SQUARER + HDOT 14-CYC       [CC]` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `5×`** | `PIN88 PAGE: 05` | `P5 L9 HOS KERNEL + HFS SDIO LBA1 + HAR CONTAINER    [CC]` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `6×`** | `PIN88 PAGE: 06` | `P6 L10-L11 HC COMPILER + NUI L0-L7 DETERMINISTIC   CC/AT` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `7×`** | `PIN88 PAGE: 07` | `P7 L5 JAMRAH 3-STAGE GATE + HIJRAH GF(5) 700/700    [CC]` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `8×`** | `PIN88 PAGE: 08` | `P8 L5-L6 KA'BAH 1600B +HMAC [VF/EH] PORTAL 8888 [EH/CC]` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `9×`** | `PIN88 PAGE: 09` | `P9 JIM:0XE4 5X5 LFSR/J-MACH GF2:31 GF5:3124 WAVE [CC] ` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `10×`** | `PIN88 PAGE: 10` | `P10 HISAB:JUMMAL/MOD-RED CRC32 RAMAL:CORE+IMPULSE [CC]` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `11×`** | `PIN88 PAGE: 11` | `P11 ALG:STAT/DYN/AGM/ITM/EXM VTM/NMV EXOMATRIX  VF/CC ` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `12×`** | `PIN88 PAGE: 12` | `P12 SW:HCVM HAR HYBIT-AI CSGI HOM-GUI (HOST/SW)  [CC] ` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |
| **Tekan `13×` (Wrap)** | `PIN88 PAGE: 00` | `PC:00F IN:00000000 CY:00001B89 FL:01 G:OK HLT CDC:LIVE` | `USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0` |

---

## 3. ANALISIS ARSITEKTURAL & MEKANISME UJI KEAMANAN NEGATIF PADA SILIKON (TANPA MENGUBAH RTL)

### 3.1 Mengapa Pengujian Negatif pada `cosmictera_usss_subsys.v` Dikendalikan oleh HCPU MMIO `0xFE8` (`SEC_CTRL`)
Di dalam [`rtl/cosmictera_usss_subsys.v`](rtl/cosmictera_usss_subsys.v) dan [`rtl/hcpu_mmio.v`](rtl/hcpu_mmio.v):
- Seluruh gerbang penolakan keamanan (**7-LUT Control Plane**: `LUT3-A`, `LUT3-B`, `LUT3-C`, `LUT3-D`, `LUT5`, `LUT6`, `LUT7`, ditambah `kabah_verify_ok` dan `hijaiyyah_jamrah_gate`) **sudah terimplementasi penuh di silikon** di dalam `cosmictera_unified_soc_usss.fs` (`723ce67f...`).
- Setelah *power-on self-test* (`RQ:01`) selesai pada saat boot, `u_usss` menerima permintaan autentikasi baru melalui instruksi HCPU `STORE` ke alamat MMIO supervisor **`0xFE8` (`SEC_CTRL`)**, dan melaporkan hasilnya ke HCPU melalui instruksi `LOAD` dari **`0xFE9` (`SEC_STATUS`)**, **`0xFEA` (`SEC_REASON`)**, **`0xFEB` (`SEC_EVENT`)**, dan **`0xFEC` (`SEC_COUNTER`)**, sekaligus memperbarui Baris 83 HDMI (`V:AUTH` / `V:REJ` / `V:ERR`, `RQ:xx`, `FL:xx`, `R:x`) secara *live*.

### 3.2 Matriks Pemetaan 8 Skenario Uji Keamanan Negatif & Pemulihan terhadap Register Perangkat Keras `u_usss`

| No | Skenario Uji Mandat | Kata Perintah `SEC_CTRL` (`0xFE8`) | Gerbang LUT / Mesin yang Menolak di Silikon | Nilai Ekspektasi `SEC_STATUS` (`0xFE9`) | Nilai Ekspektasi `SEC_REASON` (`0xFEA`) | Tampilan Baris 83 HDMI (`la_row = 83`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | *(Boot Power-On BIST)* | Otomatis (`letter=19`, `port=0`, `priv=1`, `gate=1`, `sec=1`) | Semua `LUT3-A..D=1`, `LUT5=1`, `LUT6=1`, `LUT7=1` | `AUTH_OK=1` (`bit 2=1`), `REJECT=0`, `ERROR=0`, `LUT=7'b1111111` | `0x0000_0001` (`bit 0`: `RSN_NONE`) | `V:AUTH RQ:01 FL:00 R:0` |
| **1** | **HMAC tag salah** | `0x0001_0539` (`bit 16` `sim_hmac_forge=1`, `letter=5`, `priv=1`, `gate=1`, `sec=1`, `start=1`) | **`LUT3-D` (`hmac_pass = 0`)** -> **`LUT7` (`auth_grant = 0`)** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, `ERROR=0` | `0x0000_0010` (`bit 4`: `RSN_HMAC_FAIL`) | `V:REJ  RQ:02 FL:01 R:4` |
| **2** | **Timestamp kedaluwarsa** | `0x0004_0739` (`bit 18` `sim_replay_err=1` -> `timestamp_ok=0`, `letter=7`, `start=1`) | **`LUT3-B` (`request_fresh = 0`)** -> **`LUT5 = 0`**, **`LUT7 = 0`** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, `ERROR=0` | `0x0000_0034` (`bit 2`: `RSN_REPLAY_TS`) | `V:REJ  RQ:03 FL:02 R:2` |
| **3** | **Nonce digunakan ulang** | `0x0004_0979` (`bit 18` `sim_replay_err=1` -> `nonce_fresh=0` pada Port 1, `letter=9`, `start=1`) | **`LUT3-B` (`request_fresh = 0`)** -> **`LUT5 = 0`**, **`LUT7 = 0`** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, `ERROR=0` | `0x0000_0034` (`bit 2`: `RSN_REPLAY_TS`) | `V:REJ  RQ:04 FL:03 R:2` |
| **4** | **Port tidak diizinkan (`Privilege Denied`)** | `0x0000_0C19` (`bit 5` `privilege_ok_in=0`, `letter=12`, `gate=1`, `sec=1`, `start=1`) | `LUT3-A..D=1`, tetapi **`privilege_ok = 0`** -> **`LUT7` (`auth_grant = 0`)** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, `ERROR=0` | `0x0000_0080` (`bit 7`: `RSN_PRIV_DENIED`) | `V:REJ  RQ:05 FL:04 R:7` |
| **5** | **Simbol di luar alfabet (`byte = 29 > 28`)** | `0x0000_1D39` (`payload_letter = 29` [`0x1D`], `gate_mode=1`, `priv=1`, `sec=1`, `start=1`) | **Jamrah 7-Node Gate (`jamrah_pass = 0`, `kabah_break_latched = 1`)** -> **`LUT6 = 0`**, **`LUT7 = 0`** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, **`ERROR=1` (`bit 4=1`)** | `0x0000_0070` (`bit 6`: `RSN_JAMRAH_BREAK`) | `V:ERR  RQ:06 FL:05 R:4` |
| **6** | **Key belum diprovisikan / Key diblokir** | `0x0000_0E31` (`bit 3` `secure_mode_en=0`, `letter=14`, `priv=1`, `gate=1`, `start=1`) | **`LUT3-C` (`key_enable = 0`, `gated_hmac_key = 0`)** -> `hmac_fault=1`, **`LUT3-D = 0`**, **`LUT7 = 0`** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, **`ERROR=1` (`bit 4=1`)** | `0x0000_0018` (`bit 3`: `RSN_KEY_BLOCKED` + `bit 4`: `RSN_HMAC_FAIL`) | `V:ERR  RQ:07 FL:06 R:3` |
| **7** | **Security abort (Proses dihentikan di tengah putaran Ka'bah)** | Langkah A: `0x0000_1039` (`start=1`, mulai 24 putaran Ka'bah)<br>Langkah B (2 siklus kemudian): `0x0000_0002` (`bit 1` `abort_req=1`) | **`abort_sig = 1`** -> **`LUT6` (`kabah_round_step = 0`)** menghentikan putaran Ka'bah seketika sebelum putaran ke-24 -> **`LUT7 = 0`** | `AUTH_OK=0`, **`REJECT=1` (`bit 3=1`)**, **`ERROR=1` (`bit 4=1`)** | `0x0000_0130` (`bit 8`: `RSN_ABORT_FAULT` + `bit 5`: `RSN_KABAH_MISMATCH`) | `V:ERR  RQ:08 FL:07 R:4` |
| **8** | **Request valid setelah fault (`Recovery -> AUTH_OK`)** | Langkah A: `0x0000_0004` (`clear_status=1`)<br>Langkah B: `0x0000_18B9` (`Port 2`, `letter=24` [Mim], `priv=1`, `gate=1`, `sec=1`, `start=1`) | Semua **`LUT3-A..D = 1`**, **`LUT5 = 1`**, **`LUT6 = 1`** (24 putaran penuh), **`kabah_verify_ok = 1`**, **`jamrah_pass = 1`**, **`LUT7 = 1`** | **`AUTH_OK=1` (`bit 2=1`)**, `REJECT=0`, `ERROR=0`, `LUT=7'b1111111` | `0x0000_0001` (`bit 0`: `RSN_NONE`) | `V:AUTH RQ:09 FL:07 R:0` |

*(Catatan Tambahan Skenario Ka'bah Digest Forgery)*: Selain ke-8 skenario di atas, `u_usss` juga mendukung uji ketidakcocokan digest 24-putaran Ka'bah (`0x0002_0B39`, `bit 17` `sim_kabah_forge = 1`) yang menghasilkan `kabah_verify_ok = 0`, `REJECT = 1`, dan `SEC_REASON = 0x0000_0020` (`RSN_KABAH_MISMATCH`, `R:5`).

---

## 4. DUA OPSI EKSEKUSI FISIK PADA TANG NANO 20K (TANPA MENGUBAH RTL)

Karena di dalam bitstream `cosmictera_unified_soc_usss.fs` (`723ce67f...`) memori instruksi `imem` saat ini berisi `test_bsm.hasm` (9 instruksi yang langsung berhenti pada `HALT`), maka untuk mengeksekusi ke-8 instruksi `STORE 0xFE8` (`SEC_CTRL`) dan mencetak bukti `LOAD 0xFE9..0xFEC` melalui UART fisik pada Tang Nano 20K **tanpa mengubah satu baris pun RTL (`*.v`) maupun constraints (`*.cst`)**, tersedia dua cara yang sepenuhnya menjaga baseline:

1. **Opsi 1 — BSRAM `INIT_RAM` Firmware Patch (`0` Re-Sintesis, `0` Re-P&R, Bitstream Baseline `723ce67f...` Tetap Utuh)**:
   - Menyusun program assembly `usss_negative_silicon_suite.hasm` yang menjalankan `test_bsm` diikuti ke-8 skenario negatif & pemulihan di atas (`STORE` ke `0xFE8`, menunggu selesai, lalu `LOAD` & `PRINT` `SEC_STATUS`, `SEC_REASON`, dan `SEC_COUNTER` ke UART).
   - Menginjeksi kata-kata instruksi tersebut hanya ke dalam parameter `INIT_RAM` blok BSRAM `u_hcpu_core.imem` pada salinan netlist [`cosmictera_unified_soc_usss_pnr.json`](cosmictera_unified_soc_usss_pnr.json) (`9df070e4...`) lalu mengemasnya dengan `gowin_pack` menjadi berkas terpisah `cosmictera_unified_soc_usss_negtest.fs` (proses hanya ~2 detik, tanpa mengubah placement, routing, LUT, maupun timing `pixel_clk = 81,35 MHz`), sementara berkas `cosmictera_unified_soc_usss.fs` (`723ce67f...`) tetap tidak tersentuh.
2. **Opsi 2 — Selesaikan Verifikasi Visual `P0–P12` Terlebih Dahulu pada Bitstream `723ce67f...` yang Sedang Aktif di SRAM**:
   - Selama bitstream `cosmictera_unified_soc_usss.fs` (`723ce67f...`) sedang aktif di SRAM saat ini, tekan tombol **S1 (`Pin 88`)** untuk memverifikasi halaman `P0 -> P1..P12 -> P0` terlebih dahulu, kemudian lanjutkan ke pemuatan SRAM `cosmictera_unified_soc_usss_negtest.fs` untuk merekam bukti UART & HDMI dari ke-8 skenario negatif di silikon.
