# NUI Lapis 11 — Komputasi Universal (`src/hijaiyyah/nui/autonomous/layer11_universal.py`)

- **Status**: `IMPLEMENTED_AND_VERIFIED`
- **Modul Kanonik**: `src/hijaiyyah/nui/autonomous/layer11_universal.py`
- **Pengujian**: `tests/test_ai/test_nui_layer11_universal.py`
- **Hubungan ke `NUI/LAYERS.md`**: Mengimplementasikan **Lapis 11 — Komputasi universal** yang menyatukan L0 s.d. L10 ke dalam satu rantai komputasi terverifikasi, di mana setiap sambungan (`J01_L0_TO_L1` s.d. `J11_L10_TO_L11`) memiliki pemeriksaan oracle deterministik yang benar-benar dijalankan.

## 1. Kesebelas Sambungan Ber-Oracle (`J01` – `J11`)

| ID Sambungan | Lapis | Pemeriksaan Oracle yang Dijalankan |
| :--- | :--- | :--- |
| `J01_L0_TO_L1` | `L0 -> L1` | `atom.verify_address_unification()` (28 huruf: indeks Master Table == opcode `0xE0..0xFB` == alamat ROM) + `repository_graph.verified_by("src/hijaiyyah/nui/atom.py")` |
| `J02_L1_TO_L2` | `L1 -> L2` | `program_index.programs()` (`62` HASM, `128` modul Verilog) + `program_graph.unresolved()` (`0` panggilan HASM tak terselesaikan) + `program_summary.explain("rtl/programs/loader.hasm")` |
| `J03_L2_TO_L3` | `L2 -> L3` | Kompilasi `.hcell` / `.hc` ke H-ISA, eksekusi pada `HISAMachine` melalui `execution_trace.run()` (`exit == "halt"`), dan verifikasi `63` lari pada `NUI/execution_model.json` |
| `J04_L3_TO_L4` | `L3 -> L4` | Paritas `CellEvaluator == HISAMachine == [10, 6, 4, 112, 9]`, verifikasi kontainer `HPG1` `4-B'` (`verify_4b_prime_ok`), dan pemeriksaan `NUI/layer4_freeze.json` (`73 PARITY / 2 MISMATCH / 28 UNKNOWN`) |
| `J05_L4_TO_L5` | `L4 -> L5` | Pagar `layer5.guard()` mengizinkan `["uname", "-a"]` dan menolak `["rm", "-rf", "/"]` (`GuardError`), serta memeriksa `stale_after_seconds == 300` dan pemisahan `kworker` di `NUI/layer5_freeze.json` |
| `J06_L5_TO_L6` | `L5 -> L6` | `hardware_state.answer("current", "board clock")` == `UNKNOWN` (`0 LIVE`), `observed` == `MEASURED`, `231` transisi HCPU `0` selisih di `NUI/rtl_function.json`, dan `6` entri `layer6_addendum` |
| `J07_L6_TO_L7` | `L6 -> L7` | `layer7.evaluate` + `layer7_decision.decide` + `verify()` untuk `ALLOW` (`fetch_latch`), `DENY` (`Restart / recovery`), dan `STOP / REPORT` (`HISAB` `KNOWN_DISCREPANCY`) |
| `J08_L7_TO_L8` | `L7 -> L8` | `layer8_diagnostics.diagnose` + `verify_diagnosis` atas `OFF-PRINT-SILICON` (`SILICON_PRINT_CORRUPTION`) dan log burn-in (`OBSERVER_HOST_SLEEP`, `work_accounted=1.0002`) |
| `J09_L8_TO_L9` | `L8 -> L9` | `layer9_reasoning.reason` + `verify_reasoning` atas `opcode ADD` (`PROVEN`), `nui.tail_one_is_not_invertibility` (`FALSIFIED`), dan `hardware current board clock` (`INSUFFICIENT_EVIDENCE_UNKNOWN`) |
| `J10_L9_TO_L10` | `L9 -> L10` | `layer10_engineering.engineer_hasm_program` + `verify_engineering` (8 tahap K3–K6 & 4 gerbang oracle lulus dengan keluaran `[112]`) |
| `J11_L10_TO_L11` | `L10 -> L11` | Verifikasi rantai penuh `.hcell` / `.hc` -> `USR` -> `Cell IR` -> `H-ISA` (`0xE0..0xFB`, `peak_gpr <= 15`) -> `HPG1 4-B'` -> `HISAMachine` (`[10, 6, 4, 112, 9]`) dengan guard `NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION` |

## 2. Cara Verifikasi

```bash
/usr/local/bin/python3 -m hijaiyyah.nui.autonomous.layer11_universal --verify
/usr/local/bin/python3 -B -m pytest -o addopts= -v tests/test_ai/test_nui_layer11_universal.py
```
