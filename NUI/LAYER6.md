# Lapis 6 dibekukan — pemahaman perangkat keras

Dihasilkan `src/hijaiyyah/nui/layer6_freeze.py` untuk tag `layer6-freeze-2026-09-29-final`. Status: **FROZEN**. Judul resmi *Pemahaman perangkat keras*, alias *Hardware Intelligence*.

Freeze ini tidak membaca pohon kerja. Ia membaca objek git di commit `d003cac` — pencatatan GREEN model HCPU — dan di `80ea5f8`, freeze final Lapis 5 tempat Lapis 6 dibuka. Artefak Lapis 6 semuanya turunan yang dibangun ulang oleh `--verify`-nya masing-masing, jadi yang dibekukan adalah keadaannya di commit itu.

| | commit |
|---|---|
| Lapis 6 dibuka dari | `80ea5f8` |
| model HCPU | `1c33e30` |
| pencatatan GREEN, keadaan yang dibekukan | `d003cac` |
| commit Lapis 6 | 18, berurutan |

## Cakupan

| bagian | langkah | commit | GREEN tercatat | `--verify` | artefak (sha256 di commit beku) |
|---|---|---|---|---|---|
| Inventaris hardware | 6.1 | `cde7d77` | — | `hardware` | `NUI/HARDWARE.md` `8c11b109149c…`; `NUI/hardware_inventory.json` `3ea92840dfd4…`; `NUI/spec/hardware_inventory.json` `ab5bc06fcb38…` |
| Sumber telemetri | 6.2 | `091e611` | — | `telemetry_sources` | `NUI/TELEMETRY_SOURCES.md` `8d8169986a14…`; `NUI/telemetry_sources.json` `6cbe69ec57ab…`; `NUI/spec/telemetry_sources.json` `52a17ffa0bd5…` |
| Provenance hardware | 6.3 | `08ffbed` | `08ffbed` | `hardware_provenance` | `NUI/HARDWARE_PROVENANCE.md` `893ee7919e9c…`; `NUI/hardware_provenance.json` `155d576027f1…`; `NUI/spec/hardware_provenance.json` `bcdb4ab64ca7…` |
| Model keadaan hardware | 6.4 | `d6cfd6c`, `5e4aa03` | `d6cfd6c` | `hardware_state` | `NUI/HARDWARE_STATE.md` `dfd886125e94…`; `NUI/hardware_state.json` `5601c527f304…`; `NUI/spec/hardware_state.json` `a5d914b06bcf…` |
| Korelasi hardware | 6.5 | `3617a31` | `3617a31` | `hardware_correlation` | `NUI/HARDWARE_CORRELATION.md` `d5fa6c09f039…`; `NUI/hardware_correlation.json` `f5642723f182…`; `NUI/spec/hardware_correlation.json` `f816e4dea222…` |
| RTL sebagai fungsi | model RTL sebagai fungsi | `6a9a541`, `b643b88`, `ecb417b`, `604bbb8`, `0e8b699`, `6d8839a`, `bd8158c`, `bf13941`, `e897ed0`, `f590bac` | `ecb417b`, `604bbb8`, `0e8b699`, `6d8839a`, `bd8158c`, `bf13941`, `e897ed0`, `f590bac` | `rtl_function` | `NUI/RTL_FUNCTION.md` `7b2f869c89f7…`; `NUI/rtl_function.json` `9b92b7293fa6…`; `NUI/spec/rtl_function.json` `2d817ff067d9…` |
| Model HCPU prediktif tingkat sistem | model RTL sebagai fungsi | `1c33e30`, `d003cac` | `1c33e30` | `rtl_function` | `NUI/RTL_FUNCTION.md` `7b2f869c89f7…`; `NUI/rtl_function.json` `9b92b7293fa6…`; `NUI/spec/rtl_function.json` `2d817ff067d9…` |

Tiap commit Lapis 6 ada di tepat satu bagian:

- `cde7d77` feat(nui): Layer 6.1 -- the hardware inventory, from evidence that already exists
- `091e611` feat(nui): Layer 6.2 -- where telemetry comes from, and that none of it is flowing now
- `08ffbed` feat(nui): Layer 6.3 -- every hardware claim walked back to its evidence, and nothing said about now
- `d6cfd6c` feat(nui): Layer 6.4 -- what a hardware answer means, and history never standing in for now
- `5e4aa03` fix(nui): Layer 6.4 taxonomy -- the 27 MHz clock and UART 115200 are capabilities
- `3617a31` feat(nui): Layer 6.5 -- hardware, runs, programs and opcodes linked, none by a name
- `6a9a541` feat(nui): Layer 6 -- hcpu_uart_rx as a function, held to its own bench cycle by cycle
- `b643b88` docs(nui): layer 6's "26 testbench" -- 39, by the definition it was written with
- `ecb417b` feat(nui): Layer 6 -- hcpu_mmio as a function, and what its bench never touches named
- `604bbb8` feat(nui): Layer 6 -- hcpu_uart_tx as a function, held to tb_hcpu_top.v, which only idles it
- `0e8b699` feat(nui): Layer 6 -- hcpu_dataram as a function, held to tb_parity.v over the Lapis 4 corpus
- `6d8839a` feat(nui): Layer 6 -- loader.hasm as a function, at its MMIO reads, under both loader benches
- `bd8158c` feat(nui): Layer 6 -- the pipeline's oracle audited, a coverage map before any model
- `bf13941` feat(nui): Layer 6 -- the pipeline as one function over its four bundles, held to tb_hcpu_top.v
- `e897ed0` fix(nui): Layer 6 -- the row after the last HALT is a terminal snapshot, and the stall reasons say so
- `f590bac` feat(nui): Layer 6 -- the HCPU's integration oracle audited, a coverage map before any HCPU model
- `1c33e30` feat(nui): Layer 6 -- the HCPU as one function over the parts that have an oracle, held to tb_hcpu_top.v
- `d003cac` docs(nui): Layer 6 -- the HCPU function accepted GREEN (1c33e30), and how rtl_function verifies

## Model HCPU final

Satu transisi tingkat sistem, state prediktif parsial, komposisi subsistem yang terverifikasi, dipegang pada `rtl/tb/tb_hcpu_top.v`. Jejak RTL `7ae2e5792098…`.

| pemeriksaan | hasil |
|---|---|
| titik sampel, 231 tepi | 0 sinyal berbeda |
| satu langkah dari keadaan RTL, 231 tepi | 0 berbeda |
| keluaran, 57 per baris, 232 baris | 0 berbeda; berhenti not covered: ctrl_halted_stall (11 baris) |
| lingkar terbuka dari reset | 0 berbeda, sampai tepi 231 |
| RAM | 115 kata port, 0 berbeda; saat `$finish` 2 lawan 2 kata, 0 berbeda |
| operand ALU bergerak bersama hasilnya | 0 baris |
| bacaan terminal bench | 32, 0 berbeda |
| aturan | 71 dari 149 dijalankan |
| register yang tidak diprediksi | stack_rd (10 tepi) |
| bench | Total: 15 PASS, 0 FAIL |

## Yang tidak diklaim

- **78 aturan NotCovered** — fungsi berhenti di sana, tidak memprediksi: `fetch_redirect_trap`, `fetch_flush_only`, `decode_stall`, `decode_letter`, `decode_halt_err`, `hazard_pop_use`, `hazard_store_load`, `fwd_hreg_s2_mem`, `ex_stall`, `ex_flush`, `flags_forward_self`, `flags_forward_rf`, `branch_jmp`, `branch_call`, `branch_ret`, `jeq_taken`, `jeq_not_taken`, `jgd_taken`, `jgd_not_taken`, `jngd_not_taken`, `ra_overflow`, `ra_underflow`, `hc01_invalid_rom`, `priv_fault`, `mem_fault`, `eret`, `syscall`, `flags_fwr`, `mem_stall`, `stack_overflow`, `stack_underflow`, `ctrl_print_stall`, `ctrl_halted_stall`, `mmio.rx_hold`, `mmio.rx_overrun_set`, `mmio.rx_read_clear`, `mmio.timer_compare_write`, `mmio.timer_clear`, `mmio.timer_expire`, `mmio.mem_base_write`, `mmio.mem_limit_write`, `mmio.imem_addr_write`, `mmio.imem_data_advance`, `mmio.sd_cmd_write`, `mmio.sd_sector_write`, `mmio.sd_control_write`, `mmio.sd_data_advance`, `mmio.read_counter`, `mmio.read_mem_base`, `mmio.read_other`, `mmio.read_sd_status`, `mmio.read_sd_sector`, `mmio.read_sd_control`, `mmio.read_sd_other`, `mmio.u_rx.idle_falling_edge`, `mmio.u_rx.start_count`, `mmio.u_rx.start_confirmed`, `mmio.u_rx.start_glitch`, `mmio.u_rx.data_count`, `mmio.u_rx.data_sample`, `mmio.u_rx.data_last`, `mmio.u_rx.stop_count`, `mmio.u_rx.stop_deliver`, `uart_tx.idle_start`, `uart_tx.start_count`, `uart_tx.start_end`, `uart_tx.data_count`, `uart_tx.data_next`, `uart_tx.data_last`, `uart_tx.stop_count`, `uart_tx.stop_end`, `uart_tx.default`, `dataram.read_first`, `dataram.initial_zero`, `calu.letter`, `calu.hdist`, `calu.default`, `mul.mul`.
- **Ketidaksesuaian HISAB tetap ketidaksesuaian terukur**: 13 tepi, program 5, 10, 0 di tepi yang memakainya. HISAB adalah hasil luar, dan perbaikan urutan bitnya butir tersendiri.
- **State opaque tidak diklaim paritasnya**: unit trap, mesin keadaan cetak, pengendali kartu, ra_stack[], register pc di register file, guard berregister, is_kaf di hcpu_hisab.v, kata RAM yang belum ditulis.
- **Hasil luar, dari jejak, tidak diprediksi**: ROM Master Table (rom_data, rom_valid); guard (guard_pass, guard_u, guard_rho); HISAB (hisab_pack0, hisab_pack1, hisab_pack2, hisab_crc); unit trap (trap_redirect_w, trap_in_user_w, trap_reg_rdata); mesin keadaan cetak (print_active, tx_start, tx_data, emits_busy, str_addr); pengendali kartu (sd_busy, sd_ok, sd_err, sd_card_ready, sd_err_code, sd_buf_rdata).
- **Perilaku subsistem tanpa fungsi tidak disimpulkan**: print — 3 dari 22 transisi dijalankan bench, tidak satu pun diprediksi; trap — 2 dari 19 transisi dijalankan bench, tidak satu pun diprediksi; sdio — 5 dari 33 transisi dijalankan bench, tidak satu pun diprediksi; rom — 2 dari 3 transisi dijalankan bench, tidak satu pun diprediksi; guard — 4 dari 9 transisi dijalankan bench, tidak satu pun diprediksi; hisab — 5 dari 5 transisi dijalankan bench, tidak satu pun diprediksi.

## Integritas

- RTL, bench, dan header sidik jari wrapper yang berubah sepanjang Lapis 6 (`git diff 80ea5f8 d003cac -- rtl/`): tidak ada.
- Bitstream yang dilacak git: tidak ada — berkas `.fs` di-gitignore, jadi "bitstream tidak berubah" bersandar pada sidik jari di header wrapper, yang ada di `rtl/` dan tidak berubah.
- Satu tes merah yang diterima tetap diterima: `tests/test_integrity/test_place_and_route.py::test_the_hdmi_wrapper_records_its_own_fingerprint` (sidik jari HDMI, M5.2B ditunda).
- Gerbang yang dijalankan sebelum freeze ini: ruff, mypy, pytest penuh, dan `rtl_function`, `hardware_correlation`, `hardware_state`, `hardware_provenance`, `layer4_freeze`, `parity_model`, `layer5_freeze`, `hardware`, `telemetry_sources` `--verify`.

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_freeze --verify
```
