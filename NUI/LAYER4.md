# Lapis 4 dibekukan — laporan selisih final

Dihasilkan `src/hijaiyyah/nui/layer4_freeze.py` dari rekaman yang di-commit, untuk tag `layer4-freeze-2026-09-26`. Tidak ada eksperimen yang dijalankan untuknya dan tidak ada ekspektasi yang digeser; yang ditulis tangan hanya judulnya.

Lapis 4 dibekukan bukan karena semuanya hijau, melainkan karena tiap warna punya sumber dan alasan yang bisa diaudit: **PARITY** bukti cocok, **MISMATCH** bukti papan berbeda, **UNKNOWN** bukti belum cukup atau tidak bisa diamati.

## Status

| | PARITY / MISMATCH / UNKNOWN |
|---|---|
| program, korpus P2 | PARITY 73 / MISMATCH 2 / UNKNOWN 28 |
| opcode, kolom perangkat keras P3 | PARITY 74 / MISMATCH 0 / UNKNOWN 31 |
| probe HALT/RET, P5 | PARITY 0 / MISMATCH 3 / UNKNOWN 3 |

| tangga PRINT, P4 | diharapkan | lari 1 | lari 2 | lari 3 |
|---|---|---|---|---|
| 2^22 | `4194304` | `4194304` | `4194304` | `4194304` |
| 2^23 | `8388608` | `838861:` | `8388600` | `8388600` |
| 2^24 | `16777216` | `16777216` | `16777216` | `16777216` |
| 2^25 | `33554432` | `33554436` | `335544:0` | `3355443<` |
| 2^26 | `67108864` | `671090:<` | `671091?>` | `6710903<` |
| 2^27 | `134217728` | `134218058` | `1342177?>` | `134217676` |
| 2^31 | `2147483648` | `2147484:4<` | `2147486?92` | `2147482958` |

Loader, P6: 19 kasus di papan, 15 ditolak, 4 diterima, **0 temuan**; 2 kasus hanya di Python dan simulasi.

## Selisih terukur

- `print_large_values_in_p2`: `rtl/programs/bench/e4_frame.hasm`, `rtl/programs/test_hisab.hasm` (OFF-PRINT-SILICON; `cosmictera-build/parity-board/20260924T105400Z-parity.json`)
- `print_ladder_in_p4`: `2^23`, `2^25`, `2^26`, `2^27`, `2^31` — batas pertama 2^23, 14 dari 15 keluaran salah berbeda satu sama lain (OFF-PRINT-SILICON; `cosmictera-build/parity-board/20260925T141701Z-print.json`)
- `print_behind_a_stop_in_p5`: `stop-probe:ret-then-print`, `stop-probe:halt-then-print`, `stop-probe:ret-then-print-sentinel` (Instruksi sesudah berhenti ikut menulis register; `cosmictera-build/parity-board/20260925T163903Z-stop.json`)

## Beda semantik yang diketahui

- `counter_programs`: `rtl/programs/timer_poll.hasm`, `rtl/programs/trap_resume.hasm`, `rtl/programs/trap_shadow.hasm`, `rtl/programs/trap_timer.hasm` — the interpreter counts instructions, silicon counts clocks (`cosmictera-build/parity-board/20260924T105400Z-parity.json`)

## UNKNOWN / tidak teramati

- `register_and_ram_after_a_stop` (3): `stop-probe:halt-then-register`, `stop-probe:halt-then-store`, `stop-probe:ret-then-register` — no port of the board carries a GPR or a data-RAM word
- `rtl_record_window` (3): `stop-probe:ret-then-print`, `stop-probe:halt-then-print`, `stop-probe:ret-then-print-sentinel` — the RTL record closes when halted rises and the board's wire does not, so these differences from it are unknown
- `opcodes_with_mixed_evidence` (5): `HALT`, `HCRC`, `HLOAD`, `HPACK`, `PRINT`
- `opcodes_no_sent_program_executes` (26): `CDOT`, `CHASH`, `CSIGN`, `CSUB`, `CTHETA`, `EMITS`, `HALT_ERR`, `HCHK`, `HDCMP`, `HDES`, `HDOT`, `HEXMT`, `HPROJ`, `HSER`, `JGF`, `JGP`, `JNP`, `POP`, `PRINTH`, `VDIST`, `VNORM`, `VPROJ_K`, `VPROJ_N`, `VPROJ_Q`, `VPROJ_T`, `VSCL`
- `programs_not_sent` (24): `rtl/programs/burn_in.hasm`, `rtl/programs/flags_board.hasm`, `rtl/programs/flags_ctx.hasm`, `rtl/programs/hal.hasm`, `rtl/programs/hal_sd.hasm`, `rtl/programs/hijrah_sweep.hasm`, `rtl/programs/hos.hasm`, `rtl/programs/hos_hctx.hasm`, `rtl/programs/hos_hfs_disk.hasm`, `rtl/programs/hos_prog_load.hasm`, `rtl/programs/kernel.hasm`, `rtl/programs/loader.hasm`, `rtl/programs/sd_writer.hasm`, `rtl/programs/sdio_probe.hasm`, `rtl/programs/sdio_verify.hasm`, `rtl/programs/sdio_write.hasm`, `rtl/programs/shell.hasm`, `rtl/programs/syscall_io.hasm`, `rtl/programs/test_prog_load.hasm`, `rtl/programs/test_prog_run.hasm`, `rtl/programs/trap_hreg.hasm`, `rtl/tb/hfs_persist_probe.hasm`, `rtl/tb/hfs_syscall_probe.hasm`, `rtl/tb/prog_load_probe.hasm`

## Selisih alat yang diketahui — bukan selisih perangkat keras

- `burn_in_parser_artifacts` (2): two `error` rows in the 72-hour log that the board never raised; each row shares its second with an unparsed `0H` (2 of 2); the board's own cumulative counter never exceeds 0. Dicatat sebagai: known parser artefact (K-1); the run keeps no raw bytes (`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl`)
- `cycles_report_one_byte_out` (167 dari 167 tangkapan, 6 rekaman): the wrapper's CYCLES= report arrives rotated one byte -- `\n` in front instead of `\r\n`, one `\n` over at the end, nineteen bytes either way. Dicatat sebagai: the reader drops exactly one newline, the report's; the wrapper is reported in cosmictera-build/OFF.md and not repaired (K9) (`cosmictera-build/parity-board/20260924T105400Z-parity.json`)
- `stale_burn_in_bytes_in_the_first_p2_run` (1): the first program of the first P2 run opened with the burn-in's heartbeats still buffered by the driver (350 of them). Dicatat sebagai: the runner drains the wire before sending; the run after is the record of P2, and both records are kept (`cosmictera-build/parity-board/20260924T104300Z-parity.json`)

## Bukti yang dibekukan

| langkah | berkas | byte | sha256 |
|---|---|---:|---|
| P0 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json` | 712 | `09302ae1de43…` |
| P0 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | 855293 | `910deac1b8eb…` |
| P0 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` | 5654 | `6fb0ea23bbe0…` |
| P1 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` | 849 | `768fdfb0db49…` |
| P1 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` | 9940 | `31e69b52ae17…` |
| P1 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.times.jsonl` | 31817 | `fe62931ba62f…` |
| P1 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-parsed.json` | 840 | `34514d9d91d3…` |
| P1 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-parsed.jsonl` | 102107 | `019f2fe51919…` |
| P2 | `cosmictera-build/parity-board/20260924T104300Z-parity.json` | 67100 | `71ec64ceb7f4…` |
| P2 | `cosmictera-build/parity-board/20260924T104300Z-parity.report.json` | 55915 | `a0c9a070a5a0…` |
| P2 | `cosmictera-build/parity-board/20260924T105400Z-parity.json` | 41457 | `f35ec747475e…` |
| P2 | `cosmictera-build/parity-board/20260924T105400Z-parity.report.json` | 55285 | `623f60cd70ce…` |
| P4 | `cosmictera-build/parity-board/20260925T141701Z-print.json` | 812 | `6c825a3475a4…` |
| P4 | `cosmictera-build/parity-board/20260925T141701Z-print.report.json` | 1581 | `116b76417bc9…` |
| P4 | `cosmictera-build/parity-board/20260925T141737Z-print.json` | 812 | `23a414fc26e9…` |
| P4 | `cosmictera-build/parity-board/20260925T141737Z-print.report.json` | 1581 | `acd288008782…` |
| P4 | `cosmictera-build/parity-board/20260925T141744Z-print.json` | 812 | `a4abfed1ec42…` |
| P4 | `cosmictera-build/parity-board/20260925T141744Z-print.report.json` | 1581 | `ebc785b20c07…` |
| P5 | `cosmictera-build/parity-board/20260925T163903Z-stop.json` | 2148 | `33c9bbc949c3…` |
| P5 | `cosmictera-build/parity-board/20260925T163903Z-stop.report.json` | 6264 | `aac473019a50…` |
| P6 | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | 7718 | `5e4a2a52ac26…` |

Turunan pada saat freeze — dibangun dari rekaman, dicatat untuk tag, dan boleh dibangun ulang sesudahnya:

- `NUI/parity_model.json` `62a300199b62…`
- `NUI/board_expected.json` `ebcc2c7bb684…`

Sidik jari bitstream `84fdc9123246…`, dicatat sendiri oleh rekaman berikut:

- `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json`: sama
- `cosmictera-build/parity-board/20260924T104300Z-parity.json`: sama
- `cosmictera-build/parity-board/20260924T105400Z-parity.json`: sama
- `cosmictera-build/parity-board/20260925T141701Z-print.json`: sama
- `cosmictera-build/parity-board/20260925T141737Z-print.json`: sama
- `cosmictera-build/parity-board/20260925T141744Z-print.json`: sama
- `cosmictera-build/parity-board/20260925T163903Z-stop.json`: sama

Rekaman burn-in P0 dan lab loader P6 tidak membawa sidik jarinya sendiri; yang pertama diukur dari berkasnya pada P0, yang kedua menyebut berkasnya.

## Reproduksi

Ekspektasi beku hari ini `ebcc2c7bb684…`. Tiap laporan papan dihitung ulang dari rekamannya dengan kode dan ekspektasi hari ini:

| rekaman | ekspektasi saat itu | vonis sama | berbeda di |
|---|---|---|---|
| `cosmictera-build/parity-board/20260924T104300Z-parity.json` | `905cd6111790…` | ya | `/programs/rtl/programs/hos_prog_load.hasm/reason` |
| `cosmictera-build/parity-board/20260924T105400Z-parity.json` | `905cd6111790…` | ya | `/programs/rtl/programs/hos_prog_load.hasm/reason` |
| `cosmictera-build/parity-board/20260925T141701Z-print.json` | `905cd6111790…` | ya | — |
| `cosmictera-build/parity-board/20260925T141737Z-print.json` | `905cd6111790…` | ya | — |
| `cosmictera-build/parity-board/20260925T141744Z-print.json` | `905cd6111790…` | ya | — |
| `cosmictera-build/parity-board/20260925T163903Z-stop.json` | `6d49df9bf1c3…` | ya | — |

Satu-satunya selisih adalah alasan pengecualian program yang tidak pernah dikirim ke papan, yang langkahnya bergeser saat P6 membekukan ulang ekspektasinya. Laporan P2 tidak ditulis ulang: isinya perbandingan yang benar-benar dilakukan pada harinya.

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.layer4_freeze --verify
PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --verify
```
