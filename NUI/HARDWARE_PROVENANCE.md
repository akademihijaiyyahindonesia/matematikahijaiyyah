# Provenance hardware — Lapis 6.3

Dihasilkan `src/hijaiyyah/nui/hardware_provenance.py` dari `NUI/spec/hardware_provenance.json`, atas klaim `NUI/hardware_inventory.json` (6.1) dan `NUI/telemetry_sources.json` (6.2). Tidak ada port debug, RTL, bitstream, atau telemetri live yang disentuh untuknya.

**68 klaim**: 42 MEASURED, 17 SIMULATED, 9 UNKNOWN, 0 LIVE. **65 terverifikasi, 3 belum lengkap.**

## Keadaan hardware sekarang

**UNKNOWN** — no live hardware telemetry source. Rekaman historis terakhir bukan keadaan sekarang.

## Lari papan

Identitas run: `instrumented` bila alat yang menulisnya; `non-instrumented/inferred-from-record` bila ia judul bagian halaman, dipertahankan persis seperti sumbernya.

| run_id | bentuk | identitas | observed_at | bukti | klaim |
|---|---|---|---|---|---|
| `20260925T191528Z-loader` | record | instrumented | 2026-09-25T19:15:28.544410+00:00 | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | 6.1:board, 6.1:loader, 6.2:last_container |
| `20260920T000027Z-jamrah` | record | instrumented | 2026-09-20T00:00:27.125391+00:00 | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | 6.2:pass_count, 6.2:reject_count, 6.2:latency |
| `20260924T073655Z-burn-in` | record | instrumented | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` | 6.1:fpga_device, 6.1:fpga_family, 6.1:uart, 6.1:bitstream_last_measured, 6.1:telemetry_path |
| `20260921T053430Z-burn-in-72h` | record | instrumented | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json`<br>`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl`<br>`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` | 6.1:telemetry_fields, 6.2:uptime, 6.2:cycle_rate, 6.2:drift, 6.2:memory_check, 6.2:stack_check, 6.2:consistency, 6.2:sd_sector_read, 6.2:hfs_signature, 6.2:read_error_count |
| `20260920T013538Z-burn-in-24h` | record | instrumented | 2026-09-20T01:35:38.015192+00:00 | `cosmictera-build/burn-in/20260920T013538Z-burn-in-24h.json`<br>`cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` | 6.1:clock, 6.1:clock_drift |
| `20260924T105400Z-parity` | record | instrumented | 2026-09-24T10:54:00+00:00 | `cosmictera-build/parity-board/20260924T105400Z-parity.json` | 6.1:cpu, 6.1:isa_board |
| `M3 — shell menjawab kabel serial, 12 September 2026` | page | non-instrumented/inferred-from-record | 2026-09-12 | `cosmictera-build/PAPAN.md` | 6.1:hos_shell |
| `M4.2 — kartu menjawab, dan menyimpan, 15 September 2026` | page | non-instrumented/inferred-from-record | 2026-09-15 | `cosmictera-build/PAPAN.md` | 6.1:sd_card |
| `Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026` | page | non-instrumented/inferred-from-record | 2026-09-18 | `cosmictera-build/PAPAN.md` | 6.1:hfs |
| `2B kecil — program dari kartu berjalan sendiri, 18 September 2026` | page | non-instrumented/inferred-from-record | 2026-09-18 | `cosmictera-build/PAPAN.md` | 6.2:last_boot |
| `Lintas sektor dan ACK — shell naik dari sebelas sektor kartu, 18 September 2026` | page | non-instrumented/inferred-from-record | 2026-09-18 | `cosmictera-build/PAPAN.md` | 6.1:shell_from_card |
| `Tiga cacat yang hanya papan bisa temukan` | page | non-instrumented/inferred-from-record | — | `cosmictera-build/PAPAN.md` | 6.1:reset_button |
| `Kartu SD gagal init sesudah rekonfigurasi di tengah pembacaan` | page | non-instrumented/inferred-from-record | 2026-09-20 | `cosmictera-build/OFF.md` | 6.1:sd_init_defect |
| `Pixel HDMI rusak, dan sambungannya sendiri sehat` | page | non-instrumented/inferred-from-record | — | `cosmictera-build/OFF.md` | 6.1:hdmi |
| `Validasi Ka'bah — Tang Nano 20K` | page | non-instrumented/inferred-from-record | 2026-09-20 | `cosmictera-build/validasi/KABAH.md` | 6.2:avalanche, 6.2:integrity, 6.2:replay_state |
| `Validasi Hijrah — Tang Nano 20K` | page | non-instrumented/inferred-from-record | 2026-09-20 | `cosmictera-build/validasi/HIJRAH.md` | 6.2:last_validation, 6.2:density_mod2, 6.2:density_mod4, 6.2:density_mod5, 6.2:collapse_count |

## Klaim

| id | status | source_kind | jenis bukti | run_id | observed_at | evidence | sha256 | verifikasi |
|---|---|---|---|---|---|---|---|---|
| `6.1:board` | MEASURED | historical_board_evidence | board | `20260925T191528Z-loader` | 2026-09-25T19:15:28.544410+00:00 | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | `5e4a2a52ac26…` | verified |
| `6.1:fpga_device` | MEASURED | historical_board_evidence | board | `20260924T073655Z-burn-in` | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` | `768fdfb0db49…` | verified |
| `6.1:fpga_family` | MEASURED | historical_board_evidence | board | `20260924T073655Z-burn-in` | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` | `768fdfb0db49…` | verified |
| `6.1:fpga_lut4` | SIMULATED | simulated | PNR/build-derived | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.1:fpga_dff` | SIMULATED | simulated | PNR/build-derived | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.1:fpga_bsram` | SIMULATED | simulated | PNR/build-derived | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.1:fpga_fmax` | SIMULATED | simulated | PNR/build-derived | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.1:cpu` | MEASURED | historical_board_evidence | board | `20260924T105400Z-parity` | 2026-09-24T10:54:00+00:00 | `cosmictera-build/parity-board/20260924T105400Z-parity.json` | `f35ec747475e…` | verified |
| `6.1:cpu_pipeline` | SIMULATED | simulated | rtl | — | — | `rtl/hcpu_top.v` | `98f70974c232…` | verified |
| `6.1:isa_rtl` | SIMULATED | simulated | rtl | — | — | `rtl/hcpu_pkg.vh` | `bca67ed7cfbd…` | verified |
| `6.1:isa_board` | MEASURED | historical_board_evidence | board | `20260924T105400Z-parity` | 2026-09-24T10:54:00+00:00 | `cosmictera-build/parity-board/20260924T105400Z-parity.json` | `f35ec747475e…` | verified |
| `6.1:isa_board_unknown` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.1:clock` | MEASURED | historical_board_evidence | board | `20260920T013538Z-burn-in-24h` | 2026-09-20T01:35:38.015192+00:00 | `cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` | `0733c06ad3c2…` | verified |
| `6.1:clock_drift` | MEASURED | historical_board_evidence | board | `20260920T013538Z-burn-in-24h` | 2026-09-20T01:35:38.015192+00:00 | `cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` | `0733c06ad3c2…` | verified |
| `6.1:clock_pll` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.1:imem_words` | SIMULATED | simulated | rtl | — | — | `facts/hisa/instruction_memory_words.json` | `1f605f86edf9…` | verified |
| `6.1:dmem_words` | SIMULATED | simulated | rtl | — | — | `facts/repository/data_memory_words.json` | `9a23240237e7…` | verified |
| `6.1:uart` | MEASURED | historical_board_evidence | board | `20260924T073655Z-burn-in` | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` | `31e69b52ae17…` | verified |
| `6.1:sd_card` | MEASURED | historical_board_evidence | board | `M4.2 — kartu menjawab, dan menyimpan, 15 September 2026` | 2026-09-15 | `cosmictera-build/PAPAN.md` baris 485 | `140ac8ca79e5…` | verified |
| `6.1:sd_init_defect` | MEASURED | historical_board_evidence | board | `Kartu SD gagal init sesudah rekonfigurasi di tengah pembacaan` | 2026-09-20 | `cosmictera-build/OFF.md` baris 273, 275 | `39b22a313f97…` | verified |
| `6.1:hdmi` | MEASURED | historical_board_evidence | board | `Pixel HDMI rusak, dan sambungannya sendiri sehat` | — | `cosmictera-build/OFF.md` baris 20 | `39c89c0af55f…` | incomplete |
| `6.1:leds` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin.cst` | `eaa86f79a1fc…` | verified |
| `6.1:reset_button` | MEASURED | historical_board_evidence | board | `Tiga cacat yang hanya papan bisa temukan` | — | `cosmictera-build/PAPAN.md` baris 1315, 1321 | `fcdddebec21b…` | incomplete |
| `6.1:loader` | MEASURED | historical_board_evidence | board | `20260925T191528Z-loader` | 2026-09-25T19:15:28.544410+00:00 | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | `5e4a2a52ac26…` | verified |
| `6.1:shell_from_card` | MEASURED | historical_board_evidence | board | `Lintas sektor dan ACK — shell naik dari sebelas sektor kartu, 18 September 2026` | 2026-09-18 | `cosmictera-build/PAPAN.md` baris 782 | `bf95c4bc981d…` | verified |
| `6.1:hfs` | MEASURED | historical_board_evidence | board | `Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026` | 2026-09-18 | `cosmictera-build/PAPAN.md` baris 608 | `d4587623fe18…` | verified |
| `6.1:hos_shell` | MEASURED | historical_board_evidence | board | `M3 — shell menjawab kabel serial, 12 September 2026` | 2026-09-12 | `cosmictera-build/PAPAN.md` baris 253 | `3789496d48e3…` | verified |
| `6.1:bitstream_last_measured` | MEASURED | historical_board_evidence | board | `20260924T073655Z-burn-in` | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` | `768fdfb0db49…` | verified |
| `6.1:program_now` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.1:telemetry_fields` | MEASURED | historical_board_evidence | board | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json` | `09302ae1de43…` | verified |
| `6.1:telemetry_no_source` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.1:telemetry_path` | MEASURED | historical_board_evidence | board | `20260924T073655Z-burn-in` | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` | `31e69b52ae17…` | verified |
| `6.1:telemetry_live` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.1:watchdog` | SIMULATED | simulated | rtl | — | — | `facts/burnin/no_watchdog_exists.json` | `a94c18f81455…` | verified |
| `6.2:uptime` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:cycle_rate` | MEASURED | historical_board_evidence | host_from_board | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` | `6fb0ea23bbe0…` | verified |
| `6.2:drift` | MEASURED | historical_board_evidence | host_from_board | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` | `6fb0ea23bbe0…` | verified |
| `6.2:anomaly_score` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.2:memory_check` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:stack_check` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:corruption_score` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.2:pass_count` | MEASURED | historical_board_evidence | board_validation | `20260920T000027Z-jamrah` | 2026-09-20T00:00:27.125391+00:00 | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | `ff5856ba1732…` | verified |
| `6.2:reject_count` | MEASURED | historical_board_evidence | board_validation | `20260920T000027Z-jamrah` | 2026-09-20T00:00:27.125391+00:00 | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | `ff5856ba1732…` | verified |
| `6.2:latency` | MEASURED | historical_board_evidence | board_validation | `20260920T000027Z-jamrah` | 2026-09-20T00:00:27.125391+00:00 | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | `ff5856ba1732…` | verified |
| `6.2:consistency` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:avalanche` | MEASURED | historical_board_evidence | board_validation | `Validasi Ka'bah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/KABAH.md` baris 1, 3, 39 | `86a324ea85a0…` | verified |
| `6.2:integrity` | MEASURED | historical_board_evidence | board_validation | `Validasi Ka'bah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/KABAH.md` baris 1, 3, 36, 40 | `0a88540b31fc…` | verified |
| `6.2:replay_state` | MEASURED | historical_board_evidence | board_validation | `Validasi Ka'bah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/KABAH.md` baris 1, 3, 38 | `45b29f32bd94…` | verified |
| `6.2:state_hash` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.2:sd_sector_read` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:hfs_signature` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:read_error_count` | MEASURED | historical_board_evidence | board_program | `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl` | `910deac1b8eb…` | verified |
| `6.2:last_boot` | MEASURED | historical_board_evidence | board_validation | `2B kecil — program dari kartu berjalan sendiri, 18 September 2026` | 2026-09-18 | `cosmictera-build/PAPAN.md` baris 725, 727 | `40448d0012bd…` | verified |
| `6.2:last_container` | MEASURED | historical_board_evidence | board_validation | `20260925T191528Z-loader` | 2026-09-25T19:15:28.544410+00:00 | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | `5e4a2a52ac26…` | verified |
| `6.2:last_relocation` | UNKNOWN | unknown | none | — | — | — | — | verified |
| `6.2:boot_duration` | MEASURED | historical_board_evidence | board_validation | — | — | `cosmictera-build/CHECKLIST.md` baris 196 | `6bd0a327f657…` | incomplete |
| `6.2:last_validation` | MEASURED | historical_board_evidence | board_validation | `Validasi Hijrah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/HIJRAH.md` baris 1, 3, 25, 26, 29 | `5649d5f2ce8f…` | verified |
| `6.2:density_mod2` | MEASURED | historical_board_evidence | host_from_board | `Validasi Hijrah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/HIJRAH.md` baris 1, 3, 26, 35, 38 | `4d8f63594f15…` | verified |
| `6.2:density_mod4` | MEASURED | historical_board_evidence | host_from_board | `Validasi Hijrah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/HIJRAH.md` baris 1, 3, 26, 35, 38 | `4d8f63594f15…` | verified |
| `6.2:density_mod5` | MEASURED | historical_board_evidence | host_from_board | `Validasi Hijrah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/HIJRAH.md` baris 1, 3, 26, 35, 38 | `4d8f63594f15…` | verified |
| `6.2:collapse_count` | MEASURED | historical_board_evidence | board_validation | `Validasi Hijrah — Tang Nano 20K` | 2026-09-20 | `cosmictera-build/validasi/HIJRAH.md` baris 1, 3, 27 | `4cf4615537fb…` | verified |
| `6.2:tele_pc` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.2:tele_instr` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.2:tele_halted` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.2:tele_guard` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.2:tele_cycles` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.2:tele_flags` | SIMULATED | simulated | rtl | — | — | `rtl/fpga/gowin/hcpu_gowin_top.v` | `cacdf46a41e0…` | verified |
| `6.3:current-state` | UNKNOWN | unknown | none | — | — | — | — | verified |

## Belum lengkap

Klaim ini tetap memakai kelas 6.1/6.2-nya; yang belum lengkap adalah rantainya, dan tidak diisi.

- `6.1:hdmi` — pemeriksaan 6 (observed_at valid): bagian ini menanggali keputusan pembekuan pemilik, bukan pengamatan papannya.
- `6.1:reset_button` — pemeriksaan 6 (observed_at valid): bagian ini tidak mencatat tanggal lari papannya.
- `6.2:boot_duration` — pemeriksaan 1 (run_id ada): CHECKLIST.md mencatat 579.255 siklus di satu baris tabel, tanpa judul bagian dan tanpa tanggal lari.
- `6.2:boot_duration` — pemeriksaan 6 (observed_at valid): CHECKLIST.md mencatat 579.255 siklus di satu baris tabel, tanpa judul bagian dan tanpa tanggal lari.

## Selisih historis — dicatat, tidak disunting

Angka kontrak ditulis 20 September 2026 (68b684f) ketika burn-in tingkat 1 masih berjalan; garis dasar yang di-commit sesudahnya memberi median yang lain. Dicatat sebagai selisih historis, tidak disunting (pemilik, 27 September 2026).

| medan | kontrak | baris | garis dasar |
|---|---|---|---|
| `cycle_rate` | 649,4 | `cosmictera/TELEMETRY.md:37` | `cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` `cycles_per_second.p50` = 650.4234527687142<br>`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` `cycles_per_second.p50` = 650.4234527687913 |
| `drift` | −3,3 | `cosmictera/TELEMETRY.md:38` | `cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` `board_minus_host_s.p50` = -3.8000000000029104<br>`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h-baseline.json` `board_minus_host_s.p50` = -4.300000000017462 |

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_provenance --verify
```
