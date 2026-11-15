# LAPORAN INTEGRASI PERANGKAT KERAS & SUBSISTEM COSMICTERA (`COSMICTERA_NUI_HARDWARE_INTEGRATION_REPORT.md`)

- **Modul Implementasi**: [`nui-desktop/backend/tools.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/tools.py), [`nui-desktop/backend/providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py), dan [`cosmictera_nui_control_center.py`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc/nui_centered_monitor/cosmictera_nui_control_center.py)
- **Suite Verifikasi**: [`nui-desktop/tests/test_nui_desktop_full.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_desktop_full.py) (`test_hardware_honesty_and_7stage_subsystem_control`)

## 1. Kejujuran Deteksi Perangkat Keras Tang Nano 20K (`Section 11`)

Sesuai aturan kejujuran `R2/R4` dan Section 11.2, `hardware.status` melakukan pemeriksaan fisik langsung terhadap port `/dev/cu.usbserial-*` dan `openFPGALoader -b tangnano20k --detect`:

| Kondisi Papan Fisik | Status yang Dilaporkan `hardware.status` | Perilaku Telemetri |
|---|---|---|
| **Terhubung (`CONNECTED`)** | Menampilkan port aktual (`/dev/cu.usbserial-20250303170`, `/dev/cu.usbserial-20250303171`), IDCODE `0x81b` (`GW2A(R)-18(C)`), SHA-256 bitstream `rtl/fpga/gowin/hcpu_hdmi_top.fs`, dan status `RUNNING` / `STOPPED` / `FAULT_LATCHED`. | Telemetri riil aktif; kebijakan pemrograman dikunci pada **`SRAM_ONLY`** (flag flash `--write-flash` dan `--external-flash` dilarang keras). |
| **Tidak Terhubung (`DISCONNECTED`)** | Melaporkan `connection_state = "DISCONNECTED"`, `live_telemetry_available = False`, `cpu_state = "UNKNOWN (NO LIVE HARDWARE CONNECTION)"`, dan `hdmi_state = "UNKNOWN (NO LIVE HARDWARE CONNECTION)"`. | **Nol data palsu**: Aplikasi tidak pernah menampilkan angka siklus, PC, atau status HDMI simulasi seolah-olah berasal dari perangkat keras yang sedang dicabut. |

## 2. Kendali 7 Tahap NUI & Tombol Fisik (`S1 STOP`, `S2 RECOVERY`, Workload H-ISA)

Melalui `hardware.control` dan `cosmictera.control_loop`, pengguna dapat menjalankan siklus kendali 7 tahap (`INPUT -> UNDERSTANDING -> COORDINATION -> EXECUTION -> MONITORING -> DECISION -> FEEDBACK`):
1. **`S1_STOP` (`STOP_PAUSE_S1`)**: Menghentikan eksekusi HCPU ke state `STOPPED` dengan prioritas tertinggi tanpa merusak sinyal HDMI atau memicu `GUARD: FAULT` palsu. Saat `STOPPED`, pengiriman beban kerja HCPU baru diblokir (`BLOCKED`) hingga di-resume atau di-reset.
2. **`S2_RECOVERY` (`RESET_RECOVERY_S2`)**:
   - Apabila sumber fault perangkat keras masih aktif (`fault_source_active=True`), sistem menolak pembersihan palsu dan mengunci state pada `FAULT_LATCHED` (`guard_ok=False`).
   - Apabila sumber fault telah hilang (`fault_source_active=False`), sistem melakukan pemulihan bersih kembali ke `RUNNING` (`guard_ok=True`).
3. **`EXEC_WORKLOAD` (`EXEC_HASM`)**: Menjalankan program H-ISA kanonik (seperti `test_bsm.hasm` yang menghitung norma kuadrat `Ba + Sin + Mim -> [112]`) dan memverifikasi keutuhan Six-Guard (`G1–G4`, `T1–T2`).
