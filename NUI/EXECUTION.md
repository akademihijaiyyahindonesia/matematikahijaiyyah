# Model eksekusi — Lapis 3 NUI

Dihasilkan `src/hijaiyyah/nui/execution_graph.py` dari eksekusi di `src/hijaiyyah/hisa/machine.py`, dan ditarik dari `NUI/execution_model.json` oleh `page()`. Yang ditulis tangan hanya judulnya.

## Lari

| | |
|---|---:|
| lari | 63 |
| batas langkah per lari | 20000 |
| keluar `end_of_code` | 6 |
| keluar `halt` | 43 |
| keluar `hcheck` | 2 |
| keluar `step_cap` | 12 |
| cabang terlihat dua arah | 62 |
| cabang terlihat satu arah | 134 |

## Edge

| jenis | jumlah |
|---|---:|
| `EXECUTES` | 695 |
| `READS` | 27 |
| `OBSERVES` | 81 |
| `WRITES` | 182 |
| `MODIFIES` | 340 |
| `CALLS` | 106 |
| `RETURNS` | 392 |
| `RESUMES` | 47 |
| `TRAPS` | 20 |
| **total** | **1890** |

## Node tujuan edge

| jenis | jumlah |
|---|---:|
| `hreg:` | 6 |
| `label:` | 298 |
| `mem:` | 8 |
| `mmio:` | 20 |
| `opcode:` | 78 |
| `pc:` | 147 |
| `reg:` | 16 |
| `trap:` | 4 |

## Bagaimana `loader.hasm` memindahkan kendali

| langkah | edge | target | sumber |
|---:|---|---|---|
| 174 | `WRITES` | `mmio:TRAP_EPC@0xff9` | `rtl/programs/loader.hasm:71` |
| 176 | `WRITES` | `mmio:TRAP_MODE@0xffd` | `rtl/programs/loader.hasm:73` |
| 177 | `RESUMES` | `pc:0x040` | `rtl/programs/loader.hasm:74` |

## Inventaris UNKNOWN

### `branch_seen_one_way` — 27

- `rtl/programs/burn_in.hasm: 8 branch(es)`
- `rtl/programs/flags_board.hasm: 2 branch(es)`
- `rtl/programs/flags_ctx.hasm: 1 branch(es)`
- `rtl/programs/hal_sd.hasm: 1 branch(es)`
- `rtl/programs/hfs_lifecycle.hasm: 8 branch(es)`
- `rtl/programs/hijrah_sweep.hasm: 1 branch(es)`
- `rtl/programs/hos.hasm: 11 branch(es)`
- `rtl/programs/hos_demo.hasm: 22 branch(es)`
- `rtl/programs/hos_hfs_disk.hasm: 14 branch(es)`
- `rtl/programs/hos_prog_load.hasm: 15 branch(es)`
- `rtl/programs/loader.hasm: 1 branch(es)`
- `rtl/programs/loader.hasm#with-payload: 2 branch(es)`
- `rtl/programs/sd_writer.hasm: 2 branch(es)`
- `rtl/programs/sdio_probe.hasm: 1 branch(es)`
- `rtl/programs/sdio_verify.hasm: 4 branch(es)`
- `rtl/programs/sdio_write.hasm: 5 branch(es)`
- `rtl/programs/shell.hasm: 11 branch(es)`
- `rtl/programs/syscall.hasm: 1 branch(es)`
- `rtl/programs/syscall_io.hasm: 2 branch(es)`
- `rtl/programs/test_codex.hasm: 3 branch(es)`
- `rtl/programs/test_hfs.hasm: 7 branch(es)`
- `rtl/programs/test_prog_load.hasm: 2 branch(es)`
- `rtl/programs/test_prog_run.hasm: 3 branch(es)`
- `rtl/programs/trap_flags.hasm: 2 branch(es)`
- `rtl/programs/trap_hreg.hasm: 2 branch(es)`
- `rtl/tb/hfs_persist_probe.hasm: 2 branch(es)`
- `rtl/tb/hfs_syscall_probe.hasm: 1 branch(es)`

### `did_not_halt_within_budget` — 12

- `rtl/programs/burn_in.hasm: 20000 steps; last 200 read no register read`
- `rtl/programs/flags_board.hasm: 20000 steps; last 200 read no register read`
- `rtl/programs/flags_ctx.hasm: 20000 steps; last 200 read no register read`
- `rtl/programs/hijrah_sweep.hasm: 20000 steps; last 200 read no register read`
- `rtl/programs/kernel.hasm: 20000 steps; last 200 read TRAP_CAUSE, TRAP_EPC`
- `rtl/programs/loader.hasm: 20000 steps; last 200 read RX_STATUS`
- `rtl/programs/shell.hasm: 20000 steps; last 200 read no register read`
- `rtl/programs/syscall_io.hasm: 20000 steps; last 200 read no register read`
- `rtl/programs/trap_hreg.hasm: 20000 steps; last 200 read no register read`
- `rtl/tb/hfs_persist_probe.hasm: 20000 steps; last 200 read no register read`
- `rtl/tb/hfs_syscall_probe.hasm: 20000 steps; last 200 read no register read`
- `rtl/tb/prog_load_probe.hasm: 20000 steps; last 200 read no register read`

### `ran_off_its_code` — 6

- `rtl/programs/hal.hasm: included by another program`
- `rtl/programs/hal_sd.hasm: included by another program`
- `rtl/programs/hos.hasm: included by another program`
- `rtl/programs/hos_hctx.hasm: included by another program`
- `rtl/programs/hos_hfs_disk.hasm: included by another program`
- `rtl/programs/hos_prog_load.hasm: included by another program`

### `registers_the_hardware_lacks` — 0

- (kosong)

### `sd_card_absent_in_interpreter` — 11

- `rtl/programs/burn_in.hasm`
- `rtl/programs/hal_sd.hasm`
- `rtl/programs/hos_hfs_disk.hasm`
- `rtl/programs/hos_prog_load.hasm`
- `rtl/programs/sd_writer.hasm`
- `rtl/programs/sdio_probe.hasm`
- `rtl/programs/sdio_verify.hasm`
- `rtl/programs/sdio_write.hasm`
- `rtl/programs/shell.hasm`
- `rtl/programs/test_prog_load.hasm`
- `rtl/programs/test_prog_run.hasm`

### `state_the_machine_never_declared` — 6

- `rtl/programs/hal.hasm: halted first set at step 2, rtl/programs/hal.hasm:27`
- `rtl/programs/hal_sd.hasm: halted first set at step 310, rtl/programs/hal_sd.hasm:60`
- `rtl/programs/hos.hasm: halted first set at step 3, rtl/programs/hos.hasm:61`
- `rtl/programs/hos_hctx.hasm: halted first set at step 3, rtl/programs/hos_hctx.hasm:77`
- `rtl/programs/hos_hfs_disk.hasm: halted first set at step 5, rtl/programs/hos_hfs_disk.hasm:49`
- `rtl/programs/hos_prog_load.hasm: halted first set at step 5, rtl/programs/hos_prog_load.hasm:51`

### `stopped_by_interpreter_hcheck` — 2

- `rtl/programs/hfs_lifecycle.hasm: HCHECK CORRUPTION: H0: guard check failed`
- `rtl/programs/hos_demo.hasm: HCHECK CORRUPTION: H0: guard check failed`

### `timer_counts_instructions` — 14

- `rtl/programs/burn_in.hasm`
- `rtl/programs/flags_board.hasm`
- `rtl/programs/flags_ctx.hasm`
- `rtl/programs/hal.hasm`
- `rtl/programs/hos.hasm`
- `rtl/programs/hos_hfs_disk.hasm`
- `rtl/programs/hos_prog_load.hasm`
- `rtl/programs/kernel.hasm`
- `rtl/programs/shell.hasm`
- `rtl/programs/timer_poll.hasm`
- `rtl/programs/trap_resume.hasm`
- `rtl/programs/trap_shadow.hasm`
- `rtl/programs/trap_timer.hasm`
- `rtl/programs/user_mode.hasm`

### `trap_to_an_uninstalled_vector` — 3

- `rtl/tb/hfs_persist_probe.hasm: cause [5]`
- `rtl/tb/hfs_syscall_probe.hasm: cause [5]`
- `rtl/tb/prog_load_probe.hasm: cause [5]`

### `scope`

- RTL execution is not traced here -- Verilog runs in rtl/tb/, and joining the two is layer 4
- Python execution is not traced -- function-to-function calls stay unresolved, as layers 1 and 2 left them
- each program runs alone at address 0 with nothing on its UART, except rtl/programs/loader.hasm#with-payload, which carries a three-word payload

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.execution_graph --verify
PYTHONPATH=src python3 -m hijaiyyah.nui.execution_graph --trace rtl/programs/loader.hasm#with-payload
PYTHONPATH=src python3 -m hijaiyyah.nui.execution_graph --write
```
