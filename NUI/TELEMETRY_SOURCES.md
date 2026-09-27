# Sumber telemetri — Lapis 6.2

Dihasilkan `src/hijaiyyah/nui/telemetry_sources.py` dari `NUI/spec/telemetry_sources.json` dan kontrak `cosmictera/TELEMETRY.md`. Inventaris sumber, bukan modifikasi hardware: tidak ada port debug, perubahan `hcpu_top`, telemetri baru, atau bitstream yang dibuat untuknya. **Sumber yang ada tidak sama dengan sumber yang sedang mengalir.**

## Matriks sumber

| sumber | status | cakupan |
|---|---|---|
| UART/Tang Nano board runs | **MEASURED source** | 23/27 medan kontrak |
| historical board recordings | **MEASURED evidence** | 8 lari papan atau halamannya, semuanya di-commit |
| live hardware telemetry sekarang | **UNKNOWN / tidak mengalir** | 0 sumber hidup terdaftar -- belum ada stream aktif |
| 4 medan tanpa sumber | **UNKNOWN** | anomaly_score, corruption_score, state_hash, last_relocation |
| RTL telemetry signals tele_* | **SIMULATED / available in design** | 6 sinyal -- bukan aliran papan yang hidup |

## Registry — 27 medan kontrak

| medan | status | batas akses | jenis sumber | sumber | lari papan | sha256 |
|---|---|---|---|---|---|---|
| `uptime` | MEASURED | historical board evidence | board_program | `rtl/programs/burn_in.hasm`, tiap detak | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `cycle_rate` | MEASURED | historical board evidence | host_from_board | [burn-in/](../cosmictera-build/burn-in/README.md) | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` | `6fb0ea23bbe0…` |
| `drift` | MEASURED | historical board evidence | host_from_board | [burn-in/](../cosmictera-build/burn-in/README.md) | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` | `6fb0ea23bbe0…` |
| `anomaly_score` | UNKNOWN | unknown | none | — | — | — |
| `memory_check` | MEASURED | historical board evidence | board_program | `rtl/programs/burn_in.hasm` | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `stack_check` | MEASURED | historical board evidence | board_program | `rtl/programs/burn_in.hasm` | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `corruption_score` | UNKNOWN | unknown | none | — | — | — |
| `pass_count` | MEASURED | historical board evidence | board_validation | [validasi/JAMRAH.md](../cosmictera-build/validasi/JAMRAH.md) | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | `ff5856ba1732…` |
| `reject_count` | MEASURED | historical board evidence | board_validation | [validasi/JAMRAH.md](../cosmictera-build/validasi/JAMRAH.md) | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | `ff5856ba1732…` |
| `latency` | MEASURED | historical board evidence | board_validation | [attack-lab/](../cosmictera-build/attack-lab/README.md) | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | `ff5856ba1732…` |
| `consistency` | MEASURED | historical board evidence | board_program | `rtl/programs/burn_in.hasm` | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `avalanche` | MEASURED | historical board evidence | board_validation | [validasi/KABAH.md](../cosmictera-build/validasi/KABAH.md) | `cosmictera-build/validasi/KABAH.md` | `d49358d0f8d0…` |
| `integrity` | MEASURED | historical board evidence | board_validation | [validasi/KABAH.md](../cosmictera-build/validasi/KABAH.md) | `cosmictera-build/validasi/KABAH.md` | `01e225a4f09c…` |
| `replay_state` | MEASURED | historical board evidence | board_validation | [validasi/KABAH.md](../cosmictera-build/validasi/KABAH.md) | `cosmictera-build/validasi/KABAH.md` | `9aad7b8f698d…` |
| `state_hash` | UNKNOWN | unknown | none | — | — | — |
| `sd_sector_read` | MEASURED | historical board evidence | board_program | `rtl/programs/burn_in.hasm` | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `hfs_signature` | MEASURED | historical board evidence | board_program | [burn-in/](../cosmictera-build/burn-in/README.md) | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `read_error_count` | MEASURED | historical board evidence | board_program | `rtl/programs/burn_in.hasm` | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` |
| `last_boot` | MEASURED | historical board evidence | board_validation | [PAPAN.md](../cosmictera-build/PAPAN.md) | `cosmictera-build/PAPAN.md` | `39472cc1126d…` |
| `last_container` | MEASURED | historical board evidence | board_validation | [attack-lab/](../cosmictera-build/attack-lab/README.md) | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | `5e4a2a52ac26…` |
| `last_relocation` | UNKNOWN | unknown | none | — | — | — |
| `boot_duration` | MEASURED | historical board evidence | board_validation | [CHECKLIST.md](../cosmictera-build/CHECKLIST.md) | `cosmictera-build/CHECKLIST.md` | `6bd0a327f657…` |
| `last_validation` | MEASURED | historical board evidence | board_validation | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) | `cosmictera-build/validasi/HIJRAH.md` | `d5574a4988a0…` |
| `density_mod2` | MEASURED | historical board evidence | host_from_board | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) | `cosmictera-build/validasi/HIJRAH.md` | `3741e2f3cedb…` |
| `density_mod4` | MEASURED | historical board evidence | host_from_board | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) | `cosmictera-build/validasi/HIJRAH.md` | `3741e2f3cedb…` |
| `density_mod5` | MEASURED | historical board evidence | host_from_board | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) | `cosmictera-build/validasi/HIJRAH.md` | `3741e2f3cedb…` |
| `collapse_count` | MEASURED | historical board evidence | board_validation | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) | `cosmictera-build/validasi/HIJRAH.md` | `b9a22d3b7467…` |

## Medan tanpa sumber — tetap UNKNOWN

Tidak diisi dari nama sinyal RTL atau dari dugaan.

| medan | status | kenapa |
|---|---|---|
| `anomaly_score` | UNKNOWN | turunan yang menunggu NUI dan garis dasar |
| `corruption_score` | UNKNOWN | turunan dari pencacah kesalahan yang sudah ada, belum dibuat |
| `state_hash` | UNKNOWN | bentuk ringkasannya keputusan pemilik; tidak ada inti SHA-256 di RTL (R10) |
| `last_relocation` | UNKNOWN | relokasi diterapkan di dalam pemuatan dan tidak dilaporkan sendiri |

## Sinyal telemetri RTL — tersedia di desain, bukan aliran hidup

`rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…`: `tele_pc`, `tele_instr`, `tele_halted`, `tele_guard`, `tele_cycles`, `tele_flags`. Tidak dipetakan ke medan kontrak mana pun.

## Batas akses

- **historical board evidence** — pernah diukur di papan dan terekam; tidak ada yang mengalirkannya sekarang.
- **live board source** — sumber papan yang sedang mengalir dan diamati sekarang -- hari ini tidak ada.
- **simulated RTL telemetry** — sinyal yang ada di desain RTL, bukan aliran papan yang hidup.
- **unknown** — tidak ada jalur, atau tidak dikenal.

Sumber hidup yang terdaftar: 0. Tidak ada lari papan yang sedang diamati: inventaris 6.1 mencatat telemetri yang mengalir sebagai UNKNOWN, dan irama serta jalur pelaporan belum ditetapkan pemilik.

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.telemetry_sources --verify
```
