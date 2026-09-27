# Model RTL sebagai fungsi — Lapis 6

Dihasilkan `src/hijaiyyah/nui/rtl_function.py` dari `NUI/spec/rtl_function.json`. RTL dan bench dikompilasi apa adanya dengan satu modul probe di sampingnya yang mencetak register desain di tiap tepi turun clock; tidak ada port atau baris yang berubah. Simulator: Icarus Verilog version 14.0 (devel) (s20260301-394-g9edaf7b6a-dirty).

## `hcpu_uart_rx`

`rtl/hcpu_uart_rx.v` `3dbb9f127825…`, bench `rtl/tb/tb_hcpu_uart_rx.v` `0b422f1855e6…`. CLK_HZ 27000000, BAUD 115200, DIVISOR 234, HALF 117, CNT_W 8.

| pemeriksaan | hasil |
|---|---|
| F1 satu langkah, 15915 transisi | 0 berbeda |
| F2 lingkar terbuka dari reset, 15916 siklus | 0 berbeda |
| F3 frame yang diprediksi | 0x41, 0x00, 0xFF, 0x5A, 0x3C; framing error [False, False, False, False, True] |
| F3 bench | PASS: 5 frames, glitch rejected, framing error caught |
| waktu input: perubahan line, ditangkap nilai baru, ditangkap nilai lama | 24, 24, 0 |
| jejak RTL | `106c5aaa8cbd…` |

| aturan | baris RTL | arti | dijalankan bench |
|---|---|---|---|
| `reset` | 52, 57, 64 | rst_n rendah: sinkroniser 11, IDLE, semua nol | 2 |
| `sync` | 53 | dua flop sinkroniser: rx_meta <- rx_in, rx_sync <- rx_meta | 15913 |
| `outputs_drop` | 66, 67 | rx_valid dan rx_frame_err hanya satu siklus | 15913 |
| `idle_wait` | 70, 75 | IDLE, rx_sync tinggi: tetap | 4557 |
| `idle_falling_edge` | 71, 72, 73 | IDLE, rx_sync rendah: START, count 0 | 7 |
| `start_count` | 86, 87 | START sebelum tengah bit: count + 1 | 812 |
| `start_confirmed` | 78, 79, 80, 81, 82 | START di tengah bit dan masih rendah: DATA, count 0, index 0 | 5 |
| `start_glitch` | 78, 83, 84 | START di tengah bit dan sudah tinggi: kembali IDLE | 2 |
| `data_count` | 97, 98 | DATA sebelum tengah bit: count + 1 | 9320 |
| `data_sample` | 92, 93, 94, 96 | DATA di tengah bit: geser rx_sync masuk dari atas (LSB dulu), index + 1 | 35 |
| `data_last` | 92, 93, 94, 95 | DATA di tengah bit ke-8: geser, lalu STOP | 5 |
| `stop_count` | 109, 110 | STOP sebelum tengah bit: count + 1 | 1165 |
| `stop_deliver` | 103, 104, 105, 106, 107, 108 | STOP di tengah bit: IDLE, rx_data <- shifter, rx_valid 1, rx_frame_err <- bukan rx_sync | 5 |

Tidak tercakup bench: tidak ada.

**Waktu input.** input transisi t -> t+1 adalah line sesudah posedge t+1: bench mengubah line di region aktif yang sama dengan posedge tempat DUT menyampel rx_in; iverilog menjalankan penugasan bench lebih dulu. Diukur ulang tiap build dan disimpan di model (input_timing): di tiap perubahan line, rx_meta menangkap nilai baru, tidak pernah nilai lama. Ini sifat penjadwalan bench di simulator, bukan sifat kabel -- di papan line asinkron dan dua flop sinkroniser menanggungnya.

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.rtl_function --verify
```
