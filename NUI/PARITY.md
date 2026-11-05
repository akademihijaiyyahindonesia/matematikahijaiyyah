# Model paritas — Lapis 4 NUI

Dihasilkan `src/hijaiyyah/nui/parity_model.py`, dan ditarik dari `NUI/parity_model.json` oleh `page()`. Yang ditulis tangan hanya judulnya.

## Mesin

| mesin | apa |
|---|---|
| board | recorded output dated after 1aed5e1f (2026-11-04), the last change to the CPU's RTL |
| interpreter | src/hijaiyyah/hisa/machine.py |
| python | book functions for HLOAD, HCADD, HNRM2, HDIST; otherwise the interpreter itself (src/hijaiyyah/vm delegates to it) |
| rtl | rtl/*.v under Icarus via rtl/tb/tb_parity.v +TRACE |

## Program: interpreter ↔ RTL

| status | jumlah |
|---|---:|
| PARITY | 70 |
| MISMATCH | 30 |
| UNKNOWN | 7 |

| program | status | selisih pertama |
|---|---|---|
| `rtl/programs/bench/e6_record_triage.hasm` | MISMATCH | step 50 `rtl/programs/bench/e6_record_triage.hasm:65` (`HALT`): the interpreter stops here; the RTL then commits R1=500 at cycle 370 |
| `rtl/programs/burn_in.hasm` | MISMATCH | step 9 `rtl/programs/burn_in.hasm:90` (`LOAD`): interpreter R1=10, RTL R1=13 -- the step read COUNTER |
| `rtl/programs/flags_board.hasm` | MISMATCH | step 108 `rtl/programs/hal.hasm:117` (`LOAD`): interpreter R2=109, RTL R2=165 -- the step read COUNTER |
| `rtl/programs/flags_ctx.hasm` | MISMATCH | step 106 `rtl/programs/hal.hasm:117` (`LOAD`): interpreter R2=107, RTL R2=163 -- the step read COUNTER |
| `rtl/programs/hal_sd.hasm` | MISMATCH | step 310 `rtl/programs/hal_sd.hasm:60` (`RET`): the interpreter stops here; the RTL then commits R1=196 at cycle 606 |
| `rtl/programs/hfs_lifecycle.hasm` | MISMATCH | step 200 `rtl/programs/hos.hasm:371` (`HCHECK`): the interpreter stops on its own check (HCHECK CORRUPTION: H0: guard check failed); the RTL halts later |
| `rtl/programs/hijrah_sweep.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 212240 cycles -- compared as far as both ran |
| `rtl/programs/hos_demo.hasm` | MISMATCH | step 600 `rtl/programs/hos.hasm:415` (`HCHECK`): the interpreter stops on its own check (HCHECK CORRUPTION: H0: guard check failed); the RTL halts later |
| `rtl/programs/hos_hctx.hasm` | MISMATCH | step 3 `rtl/programs/hos_hctx.hasm:77` (`RET`): the interpreter stops here; the RTL then commits R6=0 at cycle 8 |
| `rtl/programs/hos_prog_load.hasm` | MISMATCH | step 5 `rtl/programs/hos_prog_load.hasm:38` (`RET`): the interpreter stops here; the RTL then commits R11=1 at cycle 10 |
| `rtl/programs/kernel.hasm` | MISMATCH | step 123 `rtl/programs/hal.hasm:117` (`LOAD`): interpreter R2=124, RTL R2=174 -- the step read COUNTER |
| `rtl/programs/loader.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 44000 cycles -- compared as far as both ran |
| `rtl/programs/mem_protect.hasm` | MISMATCH | step 28 `rtl/programs/mem_protect.hasm:46` (`HALT`): the interpreter stops here; the RTL then commits R10=xxxxxxxx at cycle 44 |
| `rtl/programs/sd_writer.hasm` | MISMATCH | step 308 `rtl/programs/hal_sd.hasm:48` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/sdio_probe.hasm` | MISMATCH | step 307 `rtl/programs/sdio_probe.hasm:68` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/sdio_verify.hasm` | MISMATCH | step 307 `rtl/programs/sdio_verify.hasm:124` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/sdio_write.hasm` | MISMATCH | step 307 `rtl/programs/sdio_write.hasm:174` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/shell.hasm` | MISMATCH | step 326 `rtl/programs/hal_sd.hasm:48` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/subroutine.hasm` | MISMATCH | step 54 `rtl/programs/subroutine.hasm:35` (`HALT`): the interpreter stops here; the RTL then commits R1=10 at cycle 144 |
| `rtl/programs/syscall.hasm` | MISMATCH | step 30 `rtl/programs/syscall.hasm:48` (`HALT`): the interpreter stops here; the RTL then commits R10=xxxxxxxx at cycle 46 |
| `rtl/programs/syscall_io.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 44360 cycles -- compared as far as both ran |
| `rtl/programs/test_hfs.hasm` | MISMATCH | step 173 `rtl/programs/test_hfs.hasm:39` (`HALT`): the interpreter stops here; the RTL then commits R3=4294967295 at cycle 1096 |
| `rtl/programs/test_prog_load.hasm` | MISMATCH | step 316 `rtl/programs/hal_sd.hasm:48` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/test_prog_run.hasm` | MISMATCH | step 316 `rtl/programs/hal_sd.hasm:48` (`LOAD`): interpreter R1=0, RTL R2=1 -- the step read SD_STATUS |
| `rtl/programs/timer_poll.hasm` | MISMATCH | step 1 `rtl/programs/timer_poll.hasm:14` (`LOAD`): interpreter R1=2, RTL R1=5 -- the step read COUNTER |
| `rtl/programs/trap_epc.hasm` | MISMATCH | step 46 `rtl/programs/trap_epc.hasm:66` (`HALT`): the interpreter stops here; the RTL then commits R6=2 at cycle 544 |
| `rtl/programs/trap_hreg.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 44000 cycles -- compared as far as both ran |
| `rtl/programs/trap_resume.hasm` | MISMATCH | step 13 `rtl/programs/trap_resume.hasm:45` (`LOAD`): interpreter R1=14, RTL R1=17 -- the step read COUNTER |
| `rtl/programs/trap_shadow.hasm` | MISMATCH | step 13 `rtl/programs/trap_shadow.hasm:48` (`LOAD`): interpreter R1=14, RTL R1=17 -- the step read COUNTER |
| `rtl/programs/trap_timer.hasm` | MISMATCH | step 5 `rtl/programs/trap_timer.hasm:35` (`LOAD`): interpreter R2=6, RTL R2=9 -- the step read COUNTER |
| `rtl/programs/user_mode.hasm` | MISMATCH | step 22 `rtl/programs/user_mode.hasm:43` (`HALT`): the interpreter stops here; the RTL then commits R11=xxxxxxxx at cycle 37 |
| `rtl/tb/hfs_persist_probe.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 44000 cycles -- compared as far as both ran |
| `rtl/tb/hfs_syscall_probe.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 44000 cycles -- compared as far as both ran |
| `rtl/tb/prog_load_probe.hasm` | UNKNOWN | interpreter step_cap after 5000 steps; RTL did not halt within 44000 cycles -- compared as far as both ran |
| `stop-probe:halt-then-print` | MISMATCH | step 1 `<stop-probe:halt-then-print>:2` (`HALT`): the interpreter stops here; the RTL then commits TX 53 at cycle 7 |
| `stop-probe:halt-then-store` | MISMATCH | step 2 `<stop-probe:halt-then-store>:3` (`HALT`): the interpreter stops here; the RTL then commits RAM[0x100]=5 at cycle 6 |
| `stop-probe:ret-then-print` | MISMATCH | step 1 `<stop-probe:ret-then-print>:2` (`RET`): the interpreter stops here; the RTL then commits TX 53 at cycle 7 |

## Opcode

| status | jumlah |
|---|---:|
| PARITY | 29 |
| MISMATCH | 3 |
| UNKNOWN | 74 |

| opcode | python | interpreter↔RTL | papan | status |
|---|---|---|---|---|
| `ADD` | SAME ENGINE | PARITY | PARITY | PARITY |
| `ADDI` | SAME ENGINE | PARITY | PARITY | PARITY |
| `AND` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `ANDI` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `CALL` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CDOT` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `CEQ` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CGET` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CHASH` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `CMOD4` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CMOV` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CMP` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `CMPI` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CRHO` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CSET` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CSIGN` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `CSUB` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `CTHETA` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `CU` | SAME ENGINE | PARITY | PARITY | PARITY |
| `CZERO` | SAME ENGINE | PARITY | PARITY | PARITY |
| `EMITS` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `ERET` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `FRD` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `FWR` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `HALT` | SAME ENGINE | MISMATCH | PARITY | MISMATCH |
| `HALT_ERR` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HCADD` | PARITY | PARITY | PARITY | PARITY |
| `HCHK` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HCRC` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `HDCMP` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HDES` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HDIST` | PARITY | PARITY | UNKNOWN | UNKNOWN |
| `HDOT` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HEXMT` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HGRD` | SAME ENGINE | PARITY | PARITY | PARITY |
| `HLOAD` | PARITY | PARITY | PARITY | PARITY |
| `HNRM2` | PARITY | PARITY | PARITY | PARITY |
| `HPACK` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `HPROJ` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `HSER` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `JEQ` | SAME ENGINE | PARITY | PARITY | PARITY |
| `JGD` | SAME ENGINE | PARITY | PARITY | PARITY |
| `JGF` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `JGP` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `JMP` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `JNE` | SAME ENGINE | PARITY | PARITY | PARITY |
| `JNGD` | SAME ENGINE | PARITY | PARITY | PARITY |
| `JNP` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `LOAD` | SAME ENGINE | PARITY | PARITY | PARITY |
| `L_AIN` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_ALIF` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_BA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_DAL` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_DHAD` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_DZAL` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_FA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_GHAIN` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_HA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_HAA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_JIM` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_KAF` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_KHA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_LAM` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_MIM` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_NUN` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_QAF` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_RA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_SHAD` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_SIN` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_SYIN` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_TA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_THA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_TSA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_WAW` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_YA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_ZAY` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `L_ZHA` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `MOV` | SAME ENGINE | PARITY | PARITY | PARITY |
| `MOVI` | SAME ENGINE | PARITY | PARITY | PARITY |
| `MUL` | SAME ENGINE | PARITY | PARITY | PARITY |
| `NOP` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `NOT` | SAME ENGINE | PARITY | PARITY | PARITY |
| `OR` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `ORI` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `POP` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `PRINT` | SAME ENGINE | PARITY | MISMATCH | MISMATCH |
| `PRINTH` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `PUSH` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `RET` | SAME ENGINE | MISMATCH | PARITY | MISMATCH |
| `SHL` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `SHLI` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `SHR` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `SHRI` | SAME ENGINE | PARITY | PARITY | PARITY |
| `STORE` | SAME ENGINE | PARITY | PARITY | PARITY |
| `SUB` | SAME ENGINE | PARITY | PARITY | PARITY |
| `SYSCALL` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `TRAP` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `VDIST` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `VNORM` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `VPROJ_K` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `VPROJ_N` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `VPROJ_Q` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `VPROJ_T` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `VSCL` | SAME ENGINE | UNKNOWN | UNKNOWN | UNKNOWN |
| `XOR` | SAME ENGINE | PARITY | UNKNOWN | UNKNOWN |
| `XORI` | SAME ENGINE | PARITY | PARITY | PARITY |

## Papan

| program | nilai | papan | interpreter | RTL | status | catatan |
|---|---|---|---|---|---|---|
| `rtl/programs/test_bsm.hasm` |  | `112` | `112` | `112` | PARITY | `cosmictera-build/PAPAN.md:618` |
| `rtl/programs/test_codex.hasm` |  | `8 0 0 1 1 0 1 5` | `8 0 0 1 1 0 1 5` | `8 0 0 1 1 0 1 5` | PARITY | `cosmictera-build/PAPAN.md:664` |
| `rtl/programs/test_cset.hasm` |  | `5 6 2 0` | `5 6 2 0` | `5 6 2 0` | PARITY | `cosmictera-build/PAPAN.md:665` |
| `rtl/programs/test_hfs.hasm` |  | `1 1 1 2 1` | `1 1 1 2 1` | `1 1 1 2 1` | PARITY | `cosmictera-build/PAPAN.md:666` |
| `print-ladder` | 1 | `1` | `1` | `1` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 2 | `2` | `2` | `2` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 4 | `4` | `4` | `4` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 8 | `8` | `8` | `8` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 16 | `16` | `16` | `16` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 32 | `32` | `32` | `32` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 64 | `64` | `64` | `64` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 128 | `128` | `128` | `128` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 256 | `256` | `256` | `256` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 512 | `512` | `512` | `512` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 1024 | `1024` | `1024` | `1024` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 2048 | `2048` | `2048` | `2048` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 4096 | `4096` | `4096` | `4096` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 8192 | `8192` | `8192` | `8192` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 16384 | `16384` | `16384` | `16384` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 32768 | `32768` | `32768` | `32768` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 65536 | `65536` | `65536` | `65536` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 131072 | `131072` | `131072` | `131072` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 262144 | `262144` | `262144` | `262144` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 524288 | `524288` | `524288` | `524288` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 1048576 | `1048576` | `1048576` | `1048576` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 2097152 | `2097152` | `2097152` | `2097152` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 4194304 | `4194304` | `4194304` | `4194304` | PARITY | `cosmictera-build/OFF.md:108` |
| `print-ladder` | 8388608 | `8388600` | `8388608` | `8388608` | MISMATCH | `cosmictera-build/OFF.md:109` |
| `print-ladder` | 16777216 | `16777216` | `16777216` | `16777216` | PARITY | `cosmictera-build/OFF.md:110` |
| `print-ladder` | 33554432 | `335544;<` | `33554432` | `33554432` | MISMATCH | `cosmictera-build/OFF.md:111` |
| `print-ladder` | 2147483648 | `2147481?::` | `2147483648` | `2147483648` | MISMATCH | `cosmictera-build/OFF.md:112` |

## Kolom perangkat keras per opcode — korpus papan

Dari rekaman `cosmictera-build/parity-board/20260924T105400Z-parity.json`, 79 program yang dikirim ke papan pada commit `ce663be`. Ekspektasi beku `905cd6111790…`, bitstream `84fdc9123246…`. Tiap sel dihitung ulang dari byte mentah rekaman itu oleh `board_parity.opcode_column`, bukan ditulis tangan.

**Aturan Lapis 4 sejak P2** (pemilik, 24 September 2026): analisis membaca **byte mentah** rekaman lebih dulu, baru mengurai teksnya. Laporan `CYCLES=` yang tiba tergeser satu byte adalah buktinya -- teks yang sebuah rekaman bawa sejak hari ia ditulis tidak bisa dibetulkan dengan membacanya ulang; byte-nya bisa.

**PARITY** hanya bila tiap program yang menjalankannya cocok; **MISMATCH** bila tiap program yang menjalankannya berbeda dari ekspektasi beku; **UNKNOWN** bila belum ada bukti, atau bukti yang ada bercampur sehingga kabel tidak bisa menunjuk instruksi mana yang berbeda. Sebuah opcode tidak pernah dipindahkan ke PARITY untuk melengkapi tabel.

| status | opcode |
|---|---:|
| PARITY | 74 |
| MISMATCH | 0 |
| UNKNOWN | 31 |

| opcode | nama | program | bukti | PARITY | MISMATCH | UNKNOWN | papan | alasan | sumber |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| `0x10` | `ADD` | 8 | 8 | 6 | 0 | 2 | PARITY | -- | `parity:integer_arithmetic` +5 |
| `0x11` | `ADDI` | 19 | 19 | 15 | 0 | 4 | PARITY | -- | `parity:add_immediate_signed` +14 |
| `0xB0` | `AND` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:bitwise_register` +1 |
| `0xB6` | `ANDI` | 44 | 44 | 42 | 0 | 2 | PARITY | -- | `parity:add_immediate_signed` +41 |
| `0x2E` | `CALL` | 4 | 4 | 4 | 0 | 0 | PARITY | -- | `rtl/programs/hfs_lifecycle.hasm` +3 |
| `0x49` | `CDOT` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x48` | `CEQ` | 4 | 4 | 4 | 0 | 0 | PARITY | -- | `parity:codex_equality_sets_zero` +3 |
| `0x44` | `CGET` | 35 | 35 | 35 | 0 | 0 | PARITY | -- | `parity:branch_on_guard` +34 |
| `0x70` | `CHASH` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x4F` | `CMOD4` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:codex_turning_budget_and_residue` +1 |
| `0x46` | `CMOV` | 4 | 4 | 4 | 0 | 0 | PARITY | -- | `parity:codex_copy_and_zero` +3 |
| `0x20` | `CMP` | 5 | 5 | 5 | 0 | 0 | PARITY | -- | `parity:backward_branch_loop` +4 |
| `0x21` | `CMPI` | 12 | 12 | 9 | 0 | 3 | PARITY | -- | `parity:compare_immediate` +8 |
| `0x4C` | `CRHO` | 3 | 3 | 3 | 0 | 0 | PARITY | -- | `parity:codex_negative_residue` +2 |
| `0x45` | `CSET` | 9 | 9 | 9 | 0 | 0 | PARITY | -- | `parity:cset_past_seventeen_names_nothing` +8 |
| `0x72` | `CSIGN` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x43` | `CSUB` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x4E` | `CTHETA` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x4D` | `CU` | 3 | 3 | 3 | 0 | 0 | PARITY | -- | `parity:codex_negative_residue` +2 |
| `0x47` | `CZERO` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:codex_copy_and_zero` +1 |
| `0xA2` | `EMITS` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x08` | `ERET` | 8 | 8 | 5 | 0 | 3 | PARITY | -- | `rtl/programs/mem_protect.hasm` +4 |
| `0x0A` | `FRD` | 58 | 58 | 56 | 0 | 2 | PARITY | -- | `parity:add_immediate_signed` +55 |
| `0x0B` | `FWR` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:flags_survive_a_compare` +1 |
| `0x01` | `HALT` | 79 | 79 | 73 | 2 | 4 | UNKNOWN | executed in agreeing and differing runs: the wire alone cannot say which instruction differed | `rtl/programs/bench/e4_frame.hasm`, `rtl/programs/test_hisab.hasm` |
| `0xFF` | `HALT_ERR` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x42` | `HCADD` | 11 | 11 | 11 | 0 | 0 | PARITY | -- | `parity:codex_add` +10 |
| `0x68` | `HCHK` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x51` | `HCRC` | 4 | 4 | 2 | 2 | 0 | UNKNOWN | executed in agreeing and differing runs: the wire alone cannot say which instruction differed | `rtl/programs/bench/e4_frame.hasm`, `rtl/programs/test_hisab.hasm` |
| `0x56` | `HDCMP` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x58` | `HDES` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x07` | `HDIST` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:distance_between_letters` +1 |
| `0x52` | `HDOT` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x55` | `HEXMT` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x60` | `HGRD` | 22 | 22 | 22 | 0 | 0 | PARITY | -- | `parity:branch_on_guard` +21 |
| `0x40` | `HLOAD` | 42 | 42 | 40 | 2 | 0 | UNKNOWN | executed in agreeing and differing runs: the wire alone cannot say which instruction differed | `rtl/programs/bench/e4_frame.hasm`, `rtl/programs/test_hisab.hasm` |
| `0x06` | `HNRM2` | 3 | 3 | 3 | 0 | 0 | PARITY | -- | `parity:norm_of_a_letter` +2 |
| `0x50` | `HPACK` | 4 | 4 | 2 | 2 | 0 | UNKNOWN | executed in agreeing and differing runs: the wire alone cannot say which instruction differed | `rtl/programs/bench/e4_frame.hasm`, `rtl/programs/test_hisab.hasm` |
| `0x80` | `HPROJ` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x57` | `HSER` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x23` | `JEQ` | 8 | 8 | 6 | 0 | 2 | PARITY | -- | `parity:forward_branch_taken` +5 |
| `0x29` | `JGD` | 5 | 5 | 5 | 0 | 0 | PARITY | -- | `parity:branch_on_guard` +4 |
| `0x2C` | `JGF` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x2B` | `JGP` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x22` | `JMP` | 62 | 62 | 58 | 0 | 4 | PARITY | -- | `parity:add_immediate_signed` +57 |
| `0x24` | `JNE` | 10 | 10 | 9 | 0 | 1 | PARITY | -- | `parity:backward_branch_loop` +8 |
| `0x2A` | `JNGD` | 9 | 9 | 9 | 0 | 0 | PARITY | -- | `parity:branch_on_guard_not_taken` +8 |
| `0x2D` | `JNP` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x30` | `LOAD` | 16 | 16 | 12 | 0 | 4 | PARITY | -- | `parity:mmio_compare_round_trip` +11 |
| `0xF1` | `L_AIN` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE0` | `L_ALIF` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE1` | `L_BA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE7` | `L_DAL` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xEE` | `L_DHAD` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE8` | `L_DZAL` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF3` | `L_FA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF2` | `L_GHAIN` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE5` | `L_HA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xFA` | `L_HAA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE4` | `L_JIM` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` +1 |
| `0xF5` | `L_KAF` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE6` | `L_KHA` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` +1 |
| `0xF6` | `L_LAM` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF7` | `L_MIM` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF8` | `L_NUN` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF4` | `L_QAF` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE9` | `L_RA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xED` | `L_SHAD` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xEB` | `L_SIN` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xEC` | `L_SYIN` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE2` | `L_TA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xEF` | `L_THA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xE3` | `L_TSA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF9` | `L_WAW` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xFB` | `L_YA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xEA` | `L_ZAY` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0xF0` | `L_ZHA` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/letters.hasm` |
| `0x03` | `MOV` | 4 | 4 | 4 | 0 | 0 | PARITY | -- | `parity:move_and_immediate` +3 |
| `0x04` | `MOVI` | 55 | 55 | 51 | 0 | 4 | PARITY | -- | `parity:add_immediate_signed` +50 |
| `0x14` | `MUL` | 4 | 4 | 4 | 0 | 0 | PARITY | -- | `parity:integer_arithmetic` +3 |
| `0x00` | `NOP` | 7 | 7 | 6 | 0 | 1 | PARITY | -- | `parity:move_and_immediate` +5 |
| `0xB3` | `NOT` | 5 | 5 | 5 | 0 | 0 | PARITY | -- | `parity:bitwise_immediate_extension` +4 |
| `0xB1` | `OR` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `parity:bitwise_register` |
| `0xB7` | `ORI` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `parity:bitwise_immediate` |
| `0x33` | `POP` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0xA0` | `PRINT` | 79 | 79 | 73 | 2 | 4 | UNKNOWN | executed in agreeing and differing runs: the wire alone cannot say which instruction differed | `rtl/programs/bench/e4_frame.hasm`, `rtl/programs/test_hisab.hasm` |
| `0xA1` | `PRINTH` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x32` | `PUSH` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `rtl/programs/subroutine.hasm` |
| `0x2F` | `RET` | 4 | 4 | 4 | 0 | 0 | PARITY | -- | `rtl/programs/hfs_lifecycle.hasm` +3 |
| `0xB4` | `SHL` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:bitwise_shift` +1 |
| `0xB9` | `SHLI` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:bitwise_shift` +1 |
| `0xB5` | `SHR` | 2 | 2 | 2 | 0 | 0 | PARITY | -- | `parity:bitwise_shift` +1 |
| `0xBA` | `SHRI` | 46 | 46 | 44 | 0 | 2 | PARITY | -- | `parity:add_immediate_signed` +43 |
| `0x31` | `STORE` | 17 | 17 | 14 | 0 | 3 | PARITY | -- | `parity:mmio_compare_round_trip` +13 |
| `0x12` | `SUB` | 8 | 8 | 7 | 0 | 1 | PARITY | -- | `parity:integer_arithmetic` +6 |
| `0x09` | `SYSCALL` | 3 | 3 | 3 | 0 | 0 | PARITY | -- | `rtl/programs/syscall.hasm` +2 |
| `0x4B` | `VDIST` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x4A` | `VNORM` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x8A` | `VPROJ_K` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x89` | `VPROJ_N` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x8B` | `VPROJ_Q` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x88` | `VPROJ_T` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0x59` | `VSCL` | 0 | 0 | 0 | 0 | 0 | UNKNOWN | no program sent executes it | -- |
| `0xB2` | `XOR` | 1 | 1 | 1 | 0 | 0 | PARITY | -- | `parity:bitwise_register` |
| `0xB8` | `XORI` | 5 | 5 | 5 | 0 | 0 | PARITY | -- | `parity:bitwise_immediate` +4 |

## Python

| opcode | referensi | diperiksa | status |
|---|---|---:|---|
| `HCADD` | `src/hijaiyyah/algebra/aggregametric.py::add_codex` | 49 | PARITY |
| `HDIST` | `src/hijaiyyah/algebra/intrametric.py::distance_decomposition` | 4 | PARITY |
| `HLOAD` | `src/hijaiyyah/core/master_table.py::MasterTable.get_by_index` | 724 | PARITY |
| `HNRM2` | `src/hijaiyyah/algebra/vektronometry.py::norm2` | 4 | PARITY |

## Selisih yang ditanggung register MMIO

- `COUNTER`: `rtl/programs/burn_in.hasm`, `rtl/programs/flags_board.hasm`, `rtl/programs/flags_ctx.hasm`, `rtl/programs/kernel.hasm`, `rtl/programs/timer_poll.hasm`, `rtl/programs/trap_resume.hasm`, `rtl/programs/trap_shadow.hasm`, `rtl/programs/trap_timer.hasm`
- `SD_STATUS`: `rtl/programs/sd_writer.hasm`, `rtl/programs/sdio_probe.hasm`, `rtl/programs/sdio_verify.hasm`, `rtl/programs/sdio_write.hasm`, `rtl/programs/shell.hasm`, `rtl/programs/test_prog_load.hasm`, `rtl/programs/test_prog_run.hasm`

## Inventaris UNKNOWN

### `board_values_not_recorded` — 5

- print-ladder: 2^26
- print-ladder: 2^27
- print-ladder: 2^28
- print-ladder: 2^29
- print-ladder: 2^30

### `opcodes_not_in_rtl` — 21

- CDOT
- CHASH
- CSIGN
- CSUB
- HCHK
- HDCMP
- HDES
- HEXMT
- HPROJ
- HSER
- JGF
- JGP
- JNP
- PRINTH
- VDIST
- VNORM
- VPROJ_K
- VPROJ_N
- VPROJ_Q
- VPROJ_T
- VSCL

### `programs_not_halted` — 7

- rtl/programs/hijrah_sweep.hasm
- rtl/programs/loader.hasm
- rtl/programs/syscall_io.hasm
- rtl/programs/trap_hreg.hasm
- rtl/tb/hfs_persist_probe.hasm
- rtl/tb/hfs_syscall_probe.hasm
- rtl/tb/prog_load_probe.hasm

### `rtl_opcodes_without_an_agreeing_execution` — 5

- CTHETA
- EMITS
- HALT_ERR
- HDOT
- POP

### `scope` — 4

- rtl/programs/loader.hasm#with-payload is not run on the RTL: tb_parity.v has no UART receiver input and no instruction-memory write port
- the board is not run: it carries the 72-hour burn-in. Only records dated after 1aed5e1f are read
- board records of card, wire, generated or Ka'bah-slot programs are not compared: no other engine here has a card, a wire, or that slot
- cosmictera-build/OFF.md's SD init after a mid-read reconfiguration is board-only: no other engine has a card or a reconfiguration

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --verify
PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --opcode PRINT
PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --write
```
