# Laporan Baseline Resmi COSMICTERA Unified Security Subsystem (USSS) — Stage 1.5

**Status Baseline**: **DITETAPKAN SEBAGAI BASELINE RESMI (`LOCKED BASELINE`)**  
**Waktu Penetapan**: 5 November 2026, `23:56 WIB`  
**Cabang Git**: `stage-1-5-security-integration`  
**Target Perangkat Keras**: Sipeed Tang Nano 20K — Gowin `GW2AR-LV18QN88C8/I7` (`family=GW2A-18C`, JTAG `idcode 0x81b`)  
**Bitstream Baseline**: `cosmictera_unified_soc_usss.fs` (`7.261.470 byte`)  
**SHA-256 Bitstream**: `723ce67f0098157042a1bd389071d41fb28cee9a1eeb3282424f8ef4c7fdae18`  
**SHA-256 Routed Netlist (`cosmictera_unified_soc_usss_pnr.json`)**: `9df070e48a48ca3b94e62207b8e70708240cc5fe49120b06c3efbc04c0d21ff3`  
**Manifes SHA-256**: `COSMICTERA_USSS_STAGE1_5_SHA256_MANIFEST.txt` (`23 / 23 OK`)  
**Mode Pemrograman**: **SRAM ONLY (`openFPGALoader -b tangnano20k`, `0` Flag Flash — External Flash Tidak Disentuh)**

## 1. Ringkasan Baseline yang Ditetapkan

Prototipe **Unified SoC Stage 1.5 + COSMICTERA Unified Security Subsystem (USSS)** kini resmi ditetapkan sebagai **baseline terverifikasi** berdasarkan bukti simulasi RTL, sintesis Yosys, *Place & Route* `nextpnr-himbaechel`, serta pengujian fisik **Run 1** dan **Run 2** pada silikon **Tang Nano 20K**:

| Kategori Baseline | Parameter / Bukti | Nilai Terkunci | Status |
| :--- | :--- | :--- | :--- |
| **Arsitektur Keamanan** | `cosmictera_usss_subsys.v` | Bidang kendali **7-LUT (`3-3-3-3-5-6-7` = `18 LUT4 ekuivalen`)**, Portal 8888, Ka'bah 24-putaran (`kabah_verify_ok` kanonik), HMAC-SHA256, Jamrah 7-Node Gate, dan `auth_grant_reg` terdaftar | **LOCKED** |
| **Antarmuka MMIO HCPU** | `0xFE8–0xFEC` (`hcpu_pkg.vh`, `hcpu_mmio.v`) | `SEC_CTRL` (`0xFE8`), `SEC_STATUS` (`0xFE9`), `SEC_REASON` (`0xFEA`), `SEC_EVENT` (`0xFEB`), `SEC_COUNTER` (`0xFEC`) — proteksi supervisor & `0` kebocoran kunci/state | **LOCKED** |
| **Jembatan CDC & HDMI Baris 83** | `cosmictera_boot_subsys_bridge.v`, `cosmictera_boot_compositor.v` | Snapshot koheren `27 MHz -> 74,25 MHz` (`snap_sec_bus[31:0]`) & panel Baris 83 (`USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0`) pada `slice 60..63` (`+0 BSRAM`) | **LOCKED** |
| **Regresi Simulasi & Paritas Piksel** | `logs/tb_unified_soc_usss.log` | `266 / 266 PASS` (7-LUT Standalone) + `42 / 42 PASS` (`T01..T33d` Unified SoC + USSS) + `0 / 194.048` perbedaan piksel *golden frame* | **LOCKED** |
| **Utilisasi & Timing Silikon** | `logs/nextpnr_unified_soc_usss.log` | `15.879 / 20.736 LUT4 (76,58%)`, `38 / 46 BSRAM (82,61%)`, `5.991 DFF`, `clk_27m = 93,42 MHz` (`+26,33 ns`), `pixel_clk = 81,35 MHz` (`+1,18 ns`) | **LOCKED** |
| **Bukti Fisik Run 1 (Baseline SRAM & UART)** | `logs/sram_load_usss_evidence.json` | JTAG `0x81b`, SRAM `100%`, UART `23B` (`31 31 32 0A 0A 43 59 43 4C 45 53 3D 30 30 30 30 31 42 38 39 0D 0A 0A`, `SHA-256: f26ae51f...`) | **LOCKED** |
| **Bukti Fisik Run 2 (SRAM, UART, HDMI & Tombol)** | `logs/sram_load_usss_run2_evidence.json` + 2 Foto Monitor HDMI (`23.40.33` & `23.40.34`) | JTAG `0,065 s`, SRAM `3,255 s`, UART `2,003 s` (`23B` identik), HDMI `1280×720 @ 60 Hz` stabil (`RELOCKS: 00`, `FIFO OVF: NO`), Baris 83 `USSS ... V:AUTH`, transisi Baris 56 via Tombol S2 (`CY:00001B89 ... HLT CDC:LIVE`), serta navigasi `P1–P2` via Tombol S1 | **LOCKED** |
