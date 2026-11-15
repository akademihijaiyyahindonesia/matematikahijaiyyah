# LAPORAN TEKNIS — PERBAIKAN KONTROL FISIK S1, S2, UPDATE, DAN FAULT RECOVERY COSMICTERA

- **Target Perangkat Keras**: Sipeed Tang Nano 20K (`GW2AR-LV18QN88C8/I7`, Revisi Skematik `Tang_Nano_20K_3921`)
- **Repositori & Branch Kerja**: [`/Users/AMRA/hijaiyyah-mathematics`](file:///Users/AMRA/hijaiyyah-mathematics) (`feat/realtime-computing-hdmi`)
- **Modul Top-Level HDMI**: [`rtl/fpga/gowin/hcpu_hdmi_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi_top.v)
- **Constraint Pin Fisik**: [`rtl/fpga/gowin/hcpu_hdmi.cst`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi.cst)
- **Core HCPU & Reset Synchronizer**: [`rtl/fpga/gowin/hcpu_gowin_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_gowin_top.v), [`rtl/hcpu_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_top.v)
- **Testbench Verifikasi 12 Skenario**: [`cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/tb_physical_buttons_fault_recovery.v`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/tb_physical_buttons_fault_recovery.v) (**19 / 19 Pemeriksaan PASS**)

## 1. Hasil Audit Koneksi Fisik & Skematik Tombol (`S1`, `S2`, `UPDATE`)

Berdasarkan pemeriksaan skematik resmi Sipeed Tang Nano 20K (`Tang_Nano_20K_3921`) dan jejak elektris di papan (`rtl/fpga/gowin/hcpu_gowin_top.v:255-268`, [`rtl/fpga/gowin/hcpu_hdmi.cst`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi.cst)):

| Tombol Fisik | Nama Skematik | Pin FPGA (`GW2AR-18C`) | Port RTL di `hcpu_hdmi_top.v` | Rangkaian Elektris Board | Level Idle (Tidak Ditekan) | Level Aktif (Ditekan) | Konfigurasi Pad `.cst` | Fungsi Aplikasi Resmi |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S1** | `KEY_S1` / `PIN88_MODE0_KEY1` | **Pin 88** | `mode_key` | Pull-down eksternal board ke `GND`; sakelar menghubungkan ke `+3.3V` melalui resistor seri `1 kΩ` | **LOW (`1'b0`)** | **HIGH (`1'b1`)** (Active-High) | `IO_LOC "mode_key" 88; IO_PORT "mode_key" IO_TYPE=LVCMOS33 PULL_MODE=DOWN;` | **STOP / PAUSE** (Prioritas kontrol aplikasi tertinggi; membekukan eksekusi HCPU secara aman tanpa mematikan HDMI atau memicu `GUARD: FAULT`) |
| **S2** | `KEY_S2` / `PIN87_MODE1_KEY2` | **Pin 87** | `btn_rst_n` | Pull-down eksternal board ke `GND`; sakelar menghubungkan ke `+3.3V` melalui resistor seri `1 kΩ` | **LOW (`1'b0`)** | **HIGH (`1'b1`)** (Active-High) | `IO_LOC "btn_rst_n" 87; IO_PORT "btn_rst_n" IO_TYPE=LVCMOS33 PULL_MODE=DOWN;` | **RESET / RECOVERY** (Mereset pipeline HCPU & membersihkan status fault yang sudah tidak aktif; menolak pembersihan palsu bila sumber fault masih aktif) |
| **UPDATE** | `BOOT` / `UPDATE` (dekat konektor HDMI) | **Tidak Terhubung ke GPIO FPGA** | Tidak ada (`N/A`) | Terhubung langsung ke pin boot/DFU mikrokontroler onboard **Bouffalo Lab BL616** (USB-JTAG/UART debugger) | Dikendalikan oleh sirkuit internal BL616 | Memasukkan BL616 ke mode **USB DFU Firmware Upgrade** bila ditahan saat kabel USB dicolokkan | Tidak dipetakan ke `.cst` FPGA | **BL616 USB Debugger DFU Button** (Bukan tombol aplikasi FPGA; ditampilkan secara jujur sebagai `UPD USB: BL616 DEBUG DFU / NO-FPGA-GPIO DFU`) |

## 2. Pembuktian Akar Masalah Mengapa Sistem Sebelumnya Terkunci di `GUARD: FAULT`

Audit menyeluruh terhadap RTL sebelumnya ([`rtl/hcpu_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_top.v), [`rtl/hcpu_regfile.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_regfile.v), [`rtl/hcpu_page_key.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_page_key.v), [`rtl/hcpu_compositor.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_compositor.v), dan [`rtl/fpga/gowin/hcpu_hdmi_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi_top.v)) membuktikan secara eksak empat penyebab mengapa sistem masuk dan terkunci pada kondisi `GUARD: FAULT`:

1. **Inversi Langsung `FLAG_G` Sebelum `OP_HGRD` Dieksekusi (`comp_guard_fault = ~snap_guard`)**:
   - Pada [`rtl/hcpu_top.v:778`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_top.v), sinyal output `guard_led` (`tele_guard`) dihubungkan langsung ke `flags_out[FLAG_G]`.
   - Pada [`rtl/hcpu_regfile.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_regfile.v), seluruh register `flags` diinisialisasi ke `8'h00` saat reset (`FLAG_G = 1'b0`) dan bit `FLAG_G` hanya diperbarui ketika instruksi `OP_HGRD` (`0x43`) dieksekusi di tahap Execute.
   - Program bootloader [`rtl/programs/loader.hasm`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/programs/loader.hasm) yang terpanggang di ROM menunggu byte UART pada loop `PC = 0x008` tanpa pernah mengeksekusi `OP_HGRD`, sehingga selama mode tunggu bootloader maupun saat program sedang berjalan sebelum `OP_HGRD`, nilai `tele_guard` adalah `1'b0`.
   - Sebelumnya, `hcpu_hdmi_top.v` menghitung `wire comp_guard_fault = ~snap_guard;` (`~1'b0 = 1'b1`). Akibatnya, `hcpu_compositor.v` langsung merender **`GUARD: FAULT` (merah)** sejak siklus pertama setelah reset!
2. **Kesalahan Asumsi Polaritas Tombol & `PULL_MODE=UP` pada Pin 87/88**:
   - Pada board Tang Nano 20K (`Tang_Nano_20K_3921`), pin 88 (`MODE0 / KEY_S1`) dan pin 87 (`MODE1 / KEY_S2`) ditahan **LOW (`0`)** oleh resistor pull-down board untuk memilih mode konfigurasi FPGA saat power-on, dan menjadi **HIGH (`1`)** ketika tombol ditekan (menghubungkan ke `+3.3V` via `1 kΩ`).
   - Constraint sebelumnya memasang `PULL_MODE=UP` yang melawan pull-down board, dan `hcpu_page_key.v` mengasumsikan tombol active-low (`wire pressed = ~key_s2;`).
3. **Tombol S1 (`mode_key`, Pin 88) Sebelumnya Dihubungkan ke `hcpu_page_key` dan Mengubah `page` dari `0` ke `1..8`**:
   - Pada [`rtl/hcpu_compositor.v:96`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_compositor.v), seluruh 6 field telemetri utama (`STATE`, `PC`, `INSTRUCTION`, `CYCLE`, `FLAGS`, `GUARD`) hanya aktif sebagai nilai live ketika `page == 4'd0` (`wire live = (page == 4'd0) && snap_valid;`).
   - Ketika pengguna menekan S1, `page` berpindah dari `0` ke `1..8`, sehingga `hcpu_compositor.v` mematikan tampilan telemetri live dan menggantinya dengan teks statis `NOT INSTRUMENTED`, tanpa pernah menghentikan HCPU!
4. **Tombol S2 (`btn_rst_n`, Pin 87) Hanya Mereset CPU Kembali ke `loader.hasm` di Mana `FLAG_G = 0`**:
   - Ketika S2 ditekan, `hcpu_gowin_core` mendeteksi tepi jatuh `btn_rst_n` dan mereset HCPU kembali ke `PC = 0x000` (`loader.hasm`) serta mereset `flags` ke `8'h00` (`FLAG_G = 0`). Karena `comp_guard_fault = ~snap_guard` langsung mengevaluasi `~0 = 1`, layar tetap terkunci pada `GUARD: FAULT` dan baik S1 maupun S2 tidak dapat memulihkan status layar.

## 3. Arsitektur Jalur Sinyal Tombol & 7-State Control / Fault Recovery FSM

Perbaikan diimplementasikan langsung di [`rtl/fpga/gowin/hcpu_hdmi_top.v`](file:///Users/AMRA/hijaiyyah-mathematics/rtl/fpga/gowin/hcpu_hdmi_top.v) mengikuti rantai perangkat keras deterministik:

```
RAW BUTTON PAD (Pin 88 S1 / Pin 87 S2, PULL_MODE=DOWN, Active-HIGH)
  ──► 2-FF SYNCHRONIZER (s1_meta -> s1_sync, s2_meta -> s2_sync @ clk_27m)
  ──► 10.0 ms DEBOUNCE FILTER (BTN_DEB_CLKS = 270,000 siklus @ 27 MHz)
  ──► EDGE & LONG-HOLD DETECTOR (s1_rise, s1_fall, s1_long_pulse, s2_rise, s2_fall, s2_long_pulse)
  ──► 7-STATE CONTROL & FAULT RECOVERY FSM (ctrl_state[2:0])
```

### 3.1 Definisi 7 State Kontrol (`ctrl_state[2:0]`) & Prioritas Transisi

| Kode | Nama State | Indikator Layar (`BLK_STATE`) | Perilaku Eksekusi HCPU & Video HDMI |
| :--- | :--- | :--- | :--- |
| `3'd0` | `CTRL_RUNNING` | `RUNNING` (Hijau) / `HALTED` (bila program selesai normal) | `cpu_run_enable = 1'b1`; HCPU mengeksekusi instruksi di bawah clock global `clk_27m`, telemetri & NUI L0–L11 diperbarui setiap frame (60 Hz). |
| `3'd1` | `CTRL_STOPPED` | `STOPPED` (Kuning) | `cpu_run_enable = 1'b0`; register telemetri (`tele_pc`, `tele_instr`, `tele_cycles`, `tele_flags`) dan jalur `hcpu_uart_rxd` dibekukan secara sinkron; HDMI 1280×720 @ 60 Hz dan log event tetap aktif penuh. |
| `3'd2` | `CTRL_PAUSED` | `PAUSED ` (Kuning) | State transisi saat tombol S1 sedang ditahan (`s1_deb == 1'b1`); berpindah otomatis ke `CTRL_STOPPED` saat S1 dilepas (`s1_fall`) tanpa osilasi meskipun S1 ditahan lama. |
| `3'd3` | `CTRL_RESETTING` | `RESET  ` (Cyan) | Dipicu oleh S2 (`s2_rise`) ketika penyebab fault sudah tidak aktif; membangkitkan pulsa reset sinkron `core_rst_trig` (`1 -> 0 -> 1` selama 5 siklus `clk_27m`), membersihkan counter monitor, dan memverifikasi penyebab fault telah hilang. |
| `3'd4` | `CTRL_FAULT` | `FAULT  ` (Merah) | Masuk secara otomatis apabila terdeteksi fault perangkat keras nyata: (a) `hw_guard_fault` (`OP_HGRD` telah dieksekusi dan `FLAG_G == 0`), (b) `hw_halterr_fault` (CPU halt tanpa instruksi `OP_HALT`/`OP_RET`, misalnya opcode ilegal), atau (c) `sim_fault_source_active`. |
| `3'd5` | `CTRL_FAULT_LATCHED` | `FLT LAT` (Merah) | Dipicu apabila S2 ditekan untuk mencoba recovery tetapi sumber fault perangkat keras **masih aktif**; sistem menolak membersihkan status fault secara palsu (`recovery_result = REC_FAIL_ACTIVE`) dan mengunci indikator `FAULT LATCHED`. |
| `3'd6` | `CTRL_READY` | `READY  ` (Hijau) | State verifikasi pasca-reset (`rst_seq_cnt = 0..7`) setelah `CTRL_RESETTING` berhasil membersihkan fault yang sudah tidak aktif (`recovery_result = REC_OK_READY`), sebelum kembali otomatis ke `CTRL_RUNNING`. |

### 3.2 Aturan Kejujuran Perangkat Keras (`True Hardware Guard Fault`)

- Sinyal `true_guard_fault` **tidak pernah dipaksa `OK` (hijau) secara palsu**:
  - Sebelum `OP_HGRD` (`0x43`) dieksekusi (misalnya saat `loader.hasm` menunggu program di `PC = 0x008`), belum ada pelanggaran invarian 6-Guard sehingga status adalah `OK`.
  - Begitu `OP_HGRD` dieksekusi (`rtm_seen_hgrd == 1'b1` dan pipeline selesai menulis `FLAG_G`), nilai `tele_guard` dari perangkat keras `hcpu_guard.v` diteruskan apa adanya: jika `FLAG_G == 1'b0`, maka `hw_guard_fault = 1'b1`, `fault_latched = 1'b1`, `fault_code = FLT_GUARD (3'd1)`, `GUARD` menampilkan **`FAULT` (merah)**, dan `ctrl_state` masuk ke **`CTRL_FAULT`**.
  - Menekan S1 (`STOP / PAUSE`) saat `RUNNING`, `HALTED`, maupun `FAULT` **tidak pernah memicu `GUARD: FAULT`** dan selalu berhasil menghentikan sistem ke `CTRL_PAUSED` -> `CTRL_STOPPED` (`EV_BTN_USER_STOP`).

## 4. Hasil Verifikasi Simulasi 12 Skenario Wajib (`19 / 19 PASS`)

Testbench [`tb_physical_buttons_fault_recovery.v`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/tb_physical_buttons_fault_recovery.v) menguji seluruh 12 skenario wajib pada modul `hcpu_hdmi_top`:

| No | Skenario Uji Wajib | Kondisi Awal | Aksi Stimulus | State & Hasil Aktual di Simulasi RTL | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | Boot Awal (`loader.hasm`) | Reset selesai | Tidak ada tombol ditekan | `ctrl_state = RUNNING (0)`, `true_guard_fault = 0`, `page = 0` (tidak ada false `GUARD: FAULT`) | **PASS** |
| 1 | **S1 ditekan saat `RUNNING`** | `CTRL_RUNNING` | Tekan & lepas S1 (`mode_key = 1 -> 0`) | Masuk `CTRL_PAUSED (2)` -> `CTRL_STOPPED (1)`, `last_btn_event = EV_BTN_USER_STOP (1)`, siklus HCPU membeku (`cyc_after == cyc_before`), timing piksel HDMI tetap berjalan (`h_count` terus bertambah) | **PASS** |
| 2 | **S1 ditekan saat `HALTED`** | `tele_halted = 1` (normal halt) | Tekan & lepas S1 | Masuk `CTRL_STOPPED (1)` secara bersih dengan `true_guard_fault = 0` | **PASS** |
| 3 | **S1 ditekan saat `FAULT`** | `CTRL_FAULT (4)`, `fault_latched = 1` | Tekan & lepas S1 | Prioritas S1 menghentikan sistem ke `CTRL_STOPPED (1)` (`EV_BTN_USER_STOP`), tidak terkunci di `FAULT` | **PASS** |
| 4 | **S1 ditekan & dilepas berulang kali** | `CTRL_RUNNING` | 3× siklus tekan/lepas S1 | Berpindah deterministik `RUNNING <-> STOPPED` dan `page` tetap terkunci pada `0` | **PASS** |
| 5 | **S2 ditekan saat `STOPPED`** | `CTRL_STOPPED (1)` | Tekan & lepas S2 (`btn_rst_n = 1 -> 0`) | Masuk `CTRL_RESETTING (3)` (`EV_BTN_USER_RESET`) -> `CTRL_READY (6)` (`REC_OK_READY`) -> `CTRL_RUNNING (0)` | **PASS** |
| 6 | **S2 ditekan saat `FAULT LATCHED` (sumber fault masih aktif)** | `CTRL_FAULT_LATCHED (5)`, `sim_fault_source_active = 1` | Tekan & lepas S2 | Menolak pembersihan palsu; tetap di `CTRL_FAULT_LATCHED (5)` dengan `fault_latched = 1` dan `recovery_result = REC_FAIL_ACTIVE (3)` | **PASS** |
| 7 | **S2 ditekan saat penyebab `FAULT` masih aktif** | `CTRL_FAULT (4)`, `sim_fault_source_active = 1` | Tekan & lepas S2 | Transisi ke `CTRL_FAULT_LATCHED (5)` (`EV_BTN_FLT_LATCHED`), menampilkan kode sumber fault `FLT_EXT_ACTIVE (3)` | **PASS** |
| 8 | **S2 ditekan setelah penyebab `FAULT` tidak lagi aktif** | `CTRL_FAULT_LATCHED (5)`, lalu `sim_fault_source_active = 0` | Tekan & lepas S2 | Masuk `CTRL_RESETTING (3)` (`EV_BTN_FAULT_REC (4)`), membangkitkan pulsa reset `core_rst_trig`, membersihkan `fault_latched = 0` | **PASS** |
| 9 | **S1 dan S2 ditekan bersamaan** | `CTRL_RUNNING (0)` | `mode_key = 1` & `btn_rst_n = 1` serentak | Prioritas tertinggi S1 (`STOP`) menang -> `CTRL_STOPPED (1)` dengan event `EV_BTN_S1_S2_STOP (6)` | **PASS** |
| 10 | **Bounce pada tombol** | `CTRL_RUNNING (0)` | 5× pulsa glitch `< BTN_DEB_CLKS` pada S1 | Disaring sepenuhnya oleh debounce counter (`s1_deb = 0`), tidak ada perubahan state palsu | **PASS** |
| 11 | **Tombol ditahan lama (`Long Hold`)** | `CTRL_RUNNING (0)` | Tahan S1 selama `> BTN_LONG_CLKS` | Hanya 1 event penekanan tercatat (`s1_press_cnt` bertambah tepat `+1`), `s1_long_lat = 1`, tidak ada osilasi state | **PASS** |
| 12 | **Sistem kembali ke `RUNNING` setelah recovery** | Pasca-recovery Skenario 8 | Lepas S2 & amati eksekusi | `CTRL_RESETTING -> CTRL_READY -> CTRL_RUNNING (0)`, `fault_latched = 0`, `fault_code = 0`, dan siklus HCPU kembali bertambah aktif (`cyc_after > cyc_before`) | **PASS** |
