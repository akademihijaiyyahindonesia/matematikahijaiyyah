# Model eksekusi — Lapis 3 NUI

Dihasilkan `src/hijaiyyah/nui/execution_graph.py` dari eksekusi di `src/hijaiyyah/hisa/machine.py`, dan ditarik dari `NUI/execution_model.json` oleh `page()`. Yang ditulis tangan hanya judulnya.

## Lari

| | |
|---|---:|
| lari | 63 |
| batas langkah per lari | 20000 |
| keluar `fault` | 6 |
| keluar `halt` | 43 |
| keluar `hcheck` | 2 |
| keluar `step_cap` | 12 |
| cabang terlihat dua arah | 55 |
| cabang terlihat satu arah | 94 |

## Edge

| jenis | jumlah |
|---|---:|
| `EXECUTES` | 623 |
| `READS` | 20 |
| `OBSERVES` | 49 |
| `WRITES` | 136 |
| `MODIFIES` | 308 |
| `CALLS` | 93 |
| `RETURNS` | 182 |
| `RESUMES` | 47 |
| `TRAPS` | 20 |
| **total** | **1478** |

## Node tujuan edge

| jenis | jumlah |
|---|---:|
| `hreg:` | 6 |
| `label:` | 121 |
| `mem:` | 8 |
| `mmio:` | 19 |
| `opcode:` | 78 |
| `pc:` | 131 |
| `reg:` | 16 |
| `trap:` | 4 |

## Bagaimana `loader.hasm` memindahkan kendali

| langkah | edge | target | sumber |
|---:|---|---|---|
| 174 | `WRITES` | `mmio:TRAP_EPC@0xff9` | `rtl/programs/loader.hasm:71` |
| 176 | `WRITES` | `mmio:TRAP_MODE@0xffd` | `rtl/programs/loader.hasm:73` |
| 177 | `RESUMES` | `pc:0x040` | `rtl/programs/loader.hasm:74` |

## Inventaris UNKNOWN

### `branch_seen_one_way` — 24

- `rtl/programs/burn_in.hasm: 8 branch(es)`
- `rtl/programs/flags_board.hasm: 2 branch(es)`
- `rtl/programs/flags_ctx.hasm: 1 branch(es)`
- `rtl/programs/hal_sd.hasm: 1 branch(es)`
- `rtl/programs/hfs_lifecycle.hasm: 8 branch(es)`
- `rtl/programs/hijrah_sweep.hasm: 1 branch(es)`
- `rtl/programs/hos_demo.hasm: 22 branch(es)`
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

### `ran_off_its_code` — 0

- (kosong)

### `registers_the_hardware_lacks` — 0

- (kosong)

### `sd_card_absent_in_interpreter` — 9

- `rtl/programs/burn_in.hasm`
- `rtl/programs/hal_sd.hasm`
- `rtl/programs/sd_writer.hasm`
- `rtl/programs/sdio_probe.hasm`
- `rtl/programs/sdio_verify.hasm`
- `rtl/programs/sdio_write.hasm`
- `rtl/programs/shell.hasm`
- `rtl/programs/test_prog_load.hasm`
- `rtl/programs/test_prog_run.hasm`

### `state_the_machine_never_declared` — 0

- (kosong)

### `stopped_by_interpreter_hcheck` — 2

- `rtl/programs/hfs_lifecycle.hasm: HCHECK CORRUPTION: H0: guard check failed`
- `rtl/programs/hos_demo.hasm: HCHECK CORRUPTION: H0: guard check failed`

### `timer_counts_instructions` — 10

- `rtl/programs/burn_in.hasm`
- `rtl/programs/flags_board.hasm`
- `rtl/programs/flags_ctx.hasm`
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
