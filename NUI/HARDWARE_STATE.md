# Model keadaan hardware — Lapis 6.4

Dihasilkan `src/hijaiyyah/nui/hardware_state.py` dari `NUI/spec/hardware_state.json`, atas provenance `NUI/hardware_provenance.json` (6.3) dan kolom opcode papan `NUI/parity_model.json` (P3). Tidak ada RTL, port debug, bitstream, lari papan baru, atau telemetri baru yang disentuh untuknya.

**Rekaman papan historis bukan keadaan hardware sekarang.** Lari papan terakhir menjawab apa yang terukur pada lari itu, bukan apa yang sedang terjadi. Sumber live terdaftar: 0.

## Empat jenis keadaan

| kategori | arti | status klaim | menjawab kueri | klaim |
|---|---|---|---|---|
| IDENTITY | apa perangkatnya? | MEASURED, SIMULATED | MEASURED, SIMULATED | 4 |
| CAPABILITY | apa yang dirancang/dikonfigurasi dapat dilakukannya? | MEASURED, SIMULATED | MEASURED, SIMULATED | 19 |
| OBSERVED | apa yang pernah benar-benar diukur? | MEASURED, UNKNOWN | MEASURED | 147 |
| CURRENT | apa keadaan perangkat sekarang? | LIVE, UNKNOWN | LIVE | 3 |

Precedence: **LIVE > MEASURED > SIMULATED > UNKNOWN**. Pemilik: LIVE > MEASURED observed > SIMULATED capability > UNKNOWN, dan LIVE hanya bila access() menemukan sumber live terdaftar -- keberadaan data historis tidak pernah mengalahkan ketiadaan sumber live untuk kueri CURRENT.

## Kontrak kueri

| kueri | keadaan | dasar | provenance belum lengkap | alasan |
|---|---|---|---|---|
| `hardware identity HCPU` | **MEASURED** (historical_board_evidence) | `6.1:cpu` | — | — |
| `hardware capability FPGA resources` | **SIMULATED** (simulated) | `6.1:fpga_lut4`, `6.1:fpga_dff`, `6.1:fpga_bsram`, `6.1:fpga_fmax` | — | — |
| `hardware observed opcode PRINT` | **MEASURED** (historical_board_evidence) | `P3:PRINT` | — | — |
| `hardware observed board clock` | **MEASURED** (historical_board_evidence) | `6.1:clock_drift` | — | — |
| `hardware current program` | **UNKNOWN** (unknown) | — | — | no live hardware telemetry source |
| `hardware provenance HCPU` | **MEASURED** (historical_board_evidence) | `6.1:cpu`, `6.1:isa_board` | — | — |
| `hardware current board clock` | **UNKNOWN** (unknown) | — | — | no live hardware telemetry source |
| `hardware observed peripheral` | **MEASURED** (historical_board_evidence) | `6.1:sd_card`, `6.1:sd_init_defect`, `6.1:hdmi`, `6.1:reset_button`, `6.1:telemetry_path` | `6.1:hdmi`, `6.1:reset_button` | — |
| `hardware observed telemetry` | **MEASURED** (historical_board_evidence) | `6.1:telemetry_fields`, `6.1:telemetry_path`, `6.2:uptime`, `6.2:cycle_rate`, `6.2:drift`, `6.2:memory_check`, `6.2:stack_check`, `6.2:pass_count`, `6.2:reject_count`, `6.2:latency`, `6.2:consistency`, `6.2:avalanche`, `6.2:integrity`, `6.2:replay_state`, `6.2:sd_sector_read`, `6.2:hfs_signature`, `6.2:read_error_count`, `6.2:last_boot`, `6.2:last_container`, `6.2:boot_duration`, `6.2:last_validation`, `6.2:density_mod2`, `6.2:density_mod4`, `6.2:density_mod5`, `6.2:collapse_count` | `6.2:boot_duration` | — |
| `hardware observed opcode CDOT` | **UNKNOWN** (unknown) | — | — | no OBSERVED claim of `opcode CDOT` is MEASURED |
| `hardware capability clock` | **MEASURED** (historical_board_evidence) | `6.1:clock` | — | — |

## Klasifikasi klaim 6.3

| id | kategori | status | source_kind | verifikasi |
|---|---|---|---|---|
| `6.1:board` | IDENTITY | MEASURED | historical_board_evidence | verified |
| `6.1:fpga_device` | IDENTITY | MEASURED | historical_board_evidence | verified |
| `6.1:fpga_family` | IDENTITY | MEASURED | historical_board_evidence | verified |
| `6.1:fpga_lut4` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:fpga_dff` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:fpga_bsram` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:fpga_fmax` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:cpu` | IDENTITY | MEASURED | historical_board_evidence | verified |
| `6.1:cpu_pipeline` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:isa_rtl` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:isa_board` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:isa_board_unknown` | OBSERVED | UNKNOWN | unknown | verified |
| `6.1:clock` | CAPABILITY | MEASURED | historical_board_evidence | verified |
| `6.1:clock_drift` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:clock_pll` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:imem_words` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:dmem_words` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:uart` | CAPABILITY | MEASURED | historical_board_evidence | verified |
| `6.1:sd_card` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:sd_init_defect` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:hdmi` | OBSERVED | MEASURED | historical_board_evidence | incomplete |
| `6.1:leds` | CAPABILITY | SIMULATED | simulated | verified |
| `6.1:reset_button` | OBSERVED | MEASURED | historical_board_evidence | incomplete |
| `6.1:loader` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:shell_from_card` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:hfs` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:hos_shell` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:bitstream_last_measured` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:program_now` | CURRENT | UNKNOWN | unknown | verified |
| `6.1:telemetry_fields` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:telemetry_no_source` | OBSERVED | UNKNOWN | unknown | verified |
| `6.1:telemetry_path` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.1:telemetry_live` | CURRENT | UNKNOWN | unknown | verified |
| `6.1:watchdog` | CAPABILITY | SIMULATED | simulated | verified |
| `6.2:uptime` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:cycle_rate` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:drift` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:anomaly_score` | OBSERVED | UNKNOWN | unknown | verified |
| `6.2:memory_check` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:stack_check` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:corruption_score` | OBSERVED | UNKNOWN | unknown | verified |
| `6.2:pass_count` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:reject_count` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:latency` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:consistency` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:avalanche` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:integrity` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:replay_state` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:state_hash` | OBSERVED | UNKNOWN | unknown | verified |
| `6.2:sd_sector_read` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:hfs_signature` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:read_error_count` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:last_boot` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:last_container` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:last_relocation` | OBSERVED | UNKNOWN | unknown | verified |
| `6.2:boot_duration` | OBSERVED | MEASURED | historical_board_evidence | incomplete |
| `6.2:last_validation` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:density_mod2` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:density_mod4` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:density_mod5` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:collapse_count` | OBSERVED | MEASURED | historical_board_evidence | verified |
| `6.2:tele_pc` | CAPABILITY | SIMULATED | simulated | verified |
| `6.2:tele_instr` | CAPABILITY | SIMULATED | simulated | verified |
| `6.2:tele_halted` | CAPABILITY | SIMULATED | simulated | verified |
| `6.2:tele_guard` | CAPABILITY | SIMULATED | simulated | verified |
| `6.2:tele_cycles` | CAPABILITY | SIMULATED | simulated | verified |
| `6.2:tele_flags` | CAPABILITY | SIMULATED | simulated | verified |
| `6.3:current-state` | CURRENT | UNKNOWN | unknown | verified |

## Opcode teramati di papan — kolom P3

105 opcode dari kolom perangkat keras P3: 79 dijalankan sekurangnya satu program yang dikirim ke papan (MEASURED), 26 tidak pernah (UNKNOWN). Vonis kolomnya dibawa di klaim.

| opcode | status | klaim | run_id |
|---|---|---|---|
| `P3:ADD` | MEASURED | ADD di papan = kolom PARITY; 6 PARITY, 0 MISMATCH, 2 UNKNOWN dari 8 program yang dikirim | `20260924T105400Z-parity` |
| `P3:ADDI` | MEASURED | ADDI di papan = kolom PARITY; 15 PARITY, 0 MISMATCH, 4 UNKNOWN dari 19 program yang dikirim | `20260924T105400Z-parity` |
| `P3:AND` | MEASURED | AND di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:ANDI` | MEASURED | ANDI di papan = kolom PARITY; 42 PARITY, 0 MISMATCH, 2 UNKNOWN dari 44 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CALL` | MEASURED | CALL di papan = kolom PARITY; 4 PARITY, 0 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CDOT` | UNKNOWN | CDOT di papan = UNKNOWN | — |
| `P3:CEQ` | MEASURED | CEQ di papan = kolom PARITY; 4 PARITY, 0 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CGET` | MEASURED | CGET di papan = kolom PARITY; 35 PARITY, 0 MISMATCH, 0 UNKNOWN dari 35 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CHASH` | UNKNOWN | CHASH di papan = UNKNOWN | — |
| `P3:CMOD4` | MEASURED | CMOD4 di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CMOV` | MEASURED | CMOV di papan = kolom PARITY; 4 PARITY, 0 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CMP` | MEASURED | CMP di papan = kolom PARITY; 5 PARITY, 0 MISMATCH, 0 UNKNOWN dari 5 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CMPI` | MEASURED | CMPI di papan = kolom PARITY; 9 PARITY, 0 MISMATCH, 3 UNKNOWN dari 12 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CRHO` | MEASURED | CRHO di papan = kolom PARITY; 3 PARITY, 0 MISMATCH, 0 UNKNOWN dari 3 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CSET` | MEASURED | CSET di papan = kolom PARITY; 9 PARITY, 0 MISMATCH, 0 UNKNOWN dari 9 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CSIGN` | UNKNOWN | CSIGN di papan = UNKNOWN | — |
| `P3:CSUB` | UNKNOWN | CSUB di papan = UNKNOWN | — |
| `P3:CTHETA` | UNKNOWN | CTHETA di papan = UNKNOWN | — |
| `P3:CU` | MEASURED | CU di papan = kolom PARITY; 3 PARITY, 0 MISMATCH, 0 UNKNOWN dari 3 program yang dikirim | `20260924T105400Z-parity` |
| `P3:CZERO` | MEASURED | CZERO di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:EMITS` | UNKNOWN | EMITS di papan = UNKNOWN | — |
| `P3:ERET` | MEASURED | ERET di papan = kolom PARITY; 5 PARITY, 0 MISMATCH, 3 UNKNOWN dari 8 program yang dikirim | `20260924T105400Z-parity` |
| `P3:FRD` | MEASURED | FRD di papan = kolom PARITY; 56 PARITY, 0 MISMATCH, 2 UNKNOWN dari 58 program yang dikirim | `20260924T105400Z-parity` |
| `P3:FWR` | MEASURED | FWR di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HALT` | MEASURED | HALT di papan = kolom UNKNOWN; 73 PARITY, 2 MISMATCH, 4 UNKNOWN dari 79 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HALT_ERR` | UNKNOWN | HALT_ERR di papan = UNKNOWN | — |
| `P3:HCADD` | MEASURED | HCADD di papan = kolom PARITY; 11 PARITY, 0 MISMATCH, 0 UNKNOWN dari 11 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HCHK` | UNKNOWN | HCHK di papan = UNKNOWN | — |
| `P3:HCRC` | MEASURED | HCRC di papan = kolom UNKNOWN; 2 PARITY, 2 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HDCMP` | UNKNOWN | HDCMP di papan = UNKNOWN | — |
| `P3:HDES` | UNKNOWN | HDES di papan = UNKNOWN | — |
| `P3:HDIST` | MEASURED | HDIST di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HDOT` | UNKNOWN | HDOT di papan = UNKNOWN | — |
| `P3:HEXMT` | UNKNOWN | HEXMT di papan = UNKNOWN | — |
| `P3:HGRD` | MEASURED | HGRD di papan = kolom PARITY; 22 PARITY, 0 MISMATCH, 0 UNKNOWN dari 22 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HLOAD` | MEASURED | HLOAD di papan = kolom UNKNOWN; 40 PARITY, 2 MISMATCH, 0 UNKNOWN dari 42 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HNRM2` | MEASURED | HNRM2 di papan = kolom PARITY; 3 PARITY, 0 MISMATCH, 0 UNKNOWN dari 3 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HPACK` | MEASURED | HPACK di papan = kolom UNKNOWN; 2 PARITY, 2 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:HPROJ` | UNKNOWN | HPROJ di papan = UNKNOWN | — |
| `P3:HSER` | UNKNOWN | HSER di papan = UNKNOWN | — |
| `P3:JEQ` | MEASURED | JEQ di papan = kolom PARITY; 6 PARITY, 0 MISMATCH, 2 UNKNOWN dari 8 program yang dikirim | `20260924T105400Z-parity` |
| `P3:JGD` | MEASURED | JGD di papan = kolom PARITY; 5 PARITY, 0 MISMATCH, 0 UNKNOWN dari 5 program yang dikirim | `20260924T105400Z-parity` |
| `P3:JGF` | UNKNOWN | JGF di papan = UNKNOWN | — |
| `P3:JGP` | UNKNOWN | JGP di papan = UNKNOWN | — |
| `P3:JMP` | MEASURED | JMP di papan = kolom PARITY; 58 PARITY, 0 MISMATCH, 4 UNKNOWN dari 62 program yang dikirim | `20260924T105400Z-parity` |
| `P3:JNE` | MEASURED | JNE di papan = kolom PARITY; 9 PARITY, 0 MISMATCH, 1 UNKNOWN dari 10 program yang dikirim | `20260924T105400Z-parity` |
| `P3:JNGD` | MEASURED | JNGD di papan = kolom PARITY; 9 PARITY, 0 MISMATCH, 0 UNKNOWN dari 9 program yang dikirim | `20260924T105400Z-parity` |
| `P3:JNP` | UNKNOWN | JNP di papan = UNKNOWN | — |
| `P3:LOAD` | MEASURED | LOAD di papan = kolom PARITY; 12 PARITY, 0 MISMATCH, 4 UNKNOWN dari 16 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_AIN` | MEASURED | L_AIN di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_ALIF` | MEASURED | L_ALIF di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_BA` | MEASURED | L_BA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_DAL` | MEASURED | L_DAL di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_DHAD` | MEASURED | L_DHAD di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_DZAL` | MEASURED | L_DZAL di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_FA` | MEASURED | L_FA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_GHAIN` | MEASURED | L_GHAIN di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_HA` | MEASURED | L_HA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_HAA` | MEASURED | L_HAA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_JIM` | MEASURED | L_JIM di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_KAF` | MEASURED | L_KAF di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_KHA` | MEASURED | L_KHA di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_LAM` | MEASURED | L_LAM di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_MIM` | MEASURED | L_MIM di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_NUN` | MEASURED | L_NUN di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_QAF` | MEASURED | L_QAF di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_RA` | MEASURED | L_RA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_SHAD` | MEASURED | L_SHAD di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_SIN` | MEASURED | L_SIN di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_SYIN` | MEASURED | L_SYIN di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_TA` | MEASURED | L_TA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_THA` | MEASURED | L_THA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_TSA` | MEASURED | L_TSA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_WAW` | MEASURED | L_WAW di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_YA` | MEASURED | L_YA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_ZAY` | MEASURED | L_ZAY di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:L_ZHA` | MEASURED | L_ZHA di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:MOV` | MEASURED | MOV di papan = kolom PARITY; 4 PARITY, 0 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:MOVI` | MEASURED | MOVI di papan = kolom PARITY; 51 PARITY, 0 MISMATCH, 4 UNKNOWN dari 55 program yang dikirim | `20260924T105400Z-parity` |
| `P3:MUL` | MEASURED | MUL di papan = kolom PARITY; 4 PARITY, 0 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:NOP` | MEASURED | NOP di papan = kolom PARITY; 6 PARITY, 0 MISMATCH, 1 UNKNOWN dari 7 program yang dikirim | `20260924T105400Z-parity` |
| `P3:NOT` | MEASURED | NOT di papan = kolom PARITY; 5 PARITY, 0 MISMATCH, 0 UNKNOWN dari 5 program yang dikirim | `20260924T105400Z-parity` |
| `P3:OR` | MEASURED | OR di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:ORI` | MEASURED | ORI di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:POP` | UNKNOWN | POP di papan = UNKNOWN | — |
| `P3:PRINT` | MEASURED | PRINT di papan = kolom UNKNOWN; 73 PARITY, 2 MISMATCH, 4 UNKNOWN dari 79 program yang dikirim | `20260924T105400Z-parity` |
| `P3:PRINTH` | UNKNOWN | PRINTH di papan = UNKNOWN | — |
| `P3:PUSH` | MEASURED | PUSH di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:RET` | MEASURED | RET di papan = kolom PARITY; 4 PARITY, 0 MISMATCH, 0 UNKNOWN dari 4 program yang dikirim | `20260924T105400Z-parity` |
| `P3:SHL` | MEASURED | SHL di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:SHLI` | MEASURED | SHLI di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:SHR` | MEASURED | SHR di papan = kolom PARITY; 2 PARITY, 0 MISMATCH, 0 UNKNOWN dari 2 program yang dikirim | `20260924T105400Z-parity` |
| `P3:SHRI` | MEASURED | SHRI di papan = kolom PARITY; 44 PARITY, 0 MISMATCH, 2 UNKNOWN dari 46 program yang dikirim | `20260924T105400Z-parity` |
| `P3:STORE` | MEASURED | STORE di papan = kolom PARITY; 14 PARITY, 0 MISMATCH, 3 UNKNOWN dari 17 program yang dikirim | `20260924T105400Z-parity` |
| `P3:SUB` | MEASURED | SUB di papan = kolom PARITY; 7 PARITY, 0 MISMATCH, 1 UNKNOWN dari 8 program yang dikirim | `20260924T105400Z-parity` |
| `P3:SYSCALL` | MEASURED | SYSCALL di papan = kolom PARITY; 3 PARITY, 0 MISMATCH, 0 UNKNOWN dari 3 program yang dikirim | `20260924T105400Z-parity` |
| `P3:VDIST` | UNKNOWN | VDIST di papan = UNKNOWN | — |
| `P3:VNORM` | UNKNOWN | VNORM di papan = UNKNOWN | — |
| `P3:VPROJ_K` | UNKNOWN | VPROJ_K di papan = UNKNOWN | — |
| `P3:VPROJ_N` | UNKNOWN | VPROJ_N di papan = UNKNOWN | — |
| `P3:VPROJ_Q` | UNKNOWN | VPROJ_Q di papan = UNKNOWN | — |
| `P3:VPROJ_T` | UNKNOWN | VPROJ_T di papan = UNKNOWN | — |
| `P3:VSCL` | UNKNOWN | VSCL di papan = UNKNOWN | — |
| `P3:XOR` | MEASURED | XOR di papan = kolom PARITY; 1 PARITY, 0 MISMATCH, 0 UNKNOWN dari 1 program yang dikirim | `20260924T105400Z-parity` |
| `P3:XORI` | MEASURED | XORI di papan = kolom PARITY; 5 PARITY, 0 MISMATCH, 0 UNKNOWN dari 5 program yang dikirim | `20260924T105400Z-parity` |

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_state --verify
```
