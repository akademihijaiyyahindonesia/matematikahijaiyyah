# Korelasi hardware — Lapis 6.5

Dihasilkan `src/hijaiyyah/nui/hardware_correlation.py` dari `NUI/spec/hardware_correlation.json`, atas `NUI/hardware_provenance.json`, `NUI/hardware_state.json`, `NUI/board_expected.json`, dan rekaman lari papan yang di-commit. Tidak ada RTL, port debug, bitstream, lari papan baru, atau telemetri baru yang disentuh untuknya.

**Tidak ada korelasi karena nama.** `executes` adalah yang interpreter jalankan untuk payload dengan hash yang sama, bukan yang papan jalankan; bukti tingkat opcode hanya kolom P3.

## Kelas

- **DIRECT** — hubungan tertulis eksplisit di bukti: rekaman lari menyebut program dan hash payload-nya, mencetak keluarannya, atau mencatat nilai hardware yang sama dengan klaimnya; atau rantai 6.3 klaim ke larinya.
- **DERIVED** — hubungan yang dihitung dari struktur yang sudah ada: opcode yang interpreter jalankan untuk payload dengan hash yang sama, atau vonis keluaran papan terhadap ekspektasi yang dibekukan sebelum papan ditanya.
- **UNKNOWN** — hubungan yang tidak bisa dibuktikan dari bukti yang ada -- dengan alasannya, dan tanpa nilai.

## Relasi

| relasi | dari → ke | arti | DIRECT | DERIVED | UNKNOWN |
|---|---|---|---|---|---|
| `supports` | run → hardware | lari ini menopang klaim hardware itu -- rantai provenance 6.3 atau kolom P3 | 104 | 0 | 0 |
| `records` | run → hardware | rekaman lari mencatat, di kunci yang disebut, nilai yang sama dengan nilai klaim hardware itu | 11 | 0 | 0 |
| `ran` | run → program | rekaman lari menyebut program itu -- beserta hash payload yang dikirim, bila rekaman menyimpannya | 91 | 0 | 2 |
| `printed` | run → program | yang papan cetak untuk program itu pada lari itu, apa adanya di rekaman | 88 | 0 | 0 |
| `judged` | run → program | vonis keluaran itu terhadap ekspektasi beku, dari laporan lari itu | 0 | 88 | 0 |
| `executes` | program → opcode | opcode yang interpreter jalankan untuk payload dengan hash yang sama, di bawah loader -- yang interpreter jalankan, bukan yang papan jalankan | 0 | 795 | 1 |

## Lari yang dikorelasikan

| run_id | observed_at | rekaman | dikirim | tidak dikirim |
|---|---|---|---|---|
| `20260924T105400Z-parity` | 2026-09-24T10:54:00+00:00 | `cosmictera-build/parity-board/20260924T105400Z-parity.json` | 79 | 24 |
| `20260925T141701Z-print` | 2026-09-25T14:17:01+00:00 | `cosmictera-build/parity-board/20260925T141701Z-print.json` | 1 | 0 |
| `20260925T141737Z-print` | 2026-09-25T14:17:37+00:00 | `cosmictera-build/parity-board/20260925T141737Z-print.json` | 1 | 0 |
| `20260925T141744Z-print` | 2026-09-25T14:17:44+00:00 | `cosmictera-build/parity-board/20260925T141744Z-print.json` | 1 | 0 |
| `20260925T163903Z-stop` | 2026-09-25T16:39:03+00:00 | `cosmictera-build/parity-board/20260925T163903Z-stop.json` | 6 | 0 |
| `20260921T053430Z-burn-in-72h` | 2026-09-21T05:34:30.437711+00:00 | `cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json` | — | — |
| `20260920T013538Z-burn-in-24h` | 2026-09-20T01:35:38.015192+00:00 | `cosmictera-build/burn-in/20260920T013538Z-burn-in-24h.json` | — | — |
| `20260924T073655Z-burn-in` | 2026-09-24T07:36:55.695105+00:00 | `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` | — | — |
| `20260925T191528Z-loader` | 2026-09-25T19:15:28.544410+00:00 | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` | — | — |
| `20260920T000027Z-jamrah` | 2026-09-20T00:00:27.125391+00:00 | `cosmictera-build/attack-lab/20260920T000027Z-jamrah.json` | — | — |

Tidak dikorelasikan:

- `cosmictera-build/parity-board/20260924T104300Z-parity.json` — lari P2 pertama: program pertamanya tercemar 350 detak burn-in basi, selisih alat yang Lapis 4 catat (NUI/LAYER4.md). Kolom P3 dan rantai 6.3 memakai lari P2 kedua, dan korelasi ini juga.

## Kontrak

| kueri | korelasi | UNKNOWN |
|---|---|---|
| `hardware correlation hardware HCPU` | 81 | 6.1:cpu_pipeline: no board run supports or records it<br>6.1:isa_rtl: no board run supports or records it<br>6.1:isa_board_unknown: no board run supports or records it |
| `hardware correlation program rtl/programs/test_hisab.hasm` | 90 | — |
| `hardware correlation opcode PRINT` | 81; bukti opcode 79 program, eksperimen `print-silicon`, `stop-probe:ret-then-print-sentinel` | — |
| `hardware correlation run 20260925T141701Z-print` | 4 | — |
| `hardware correlation run 20260925T191528Z-loader` | 5 | ran:20260925T191528Z-loader->None@20260925T191528Z-loader: rekaman menyebut sasaran (target `loader`), bukan program; tautan ke sebuah berkas program tidak ditarik dari nama |
| `hardware correlation program rtl/programs/burn_in.hasm` | 25 | executes:rtl/programs/burn_in.hasm->None: no frozen expectation holds this program's payload; its opcodes are not read from its name |

## Yang tetap UNKNOWN

- `ran:20260925T191528Z-loader->None@20260925T191528Z-loader` — rekaman menyebut sasaran (target `loader`), bukan program; tautan ke sebuah berkas program tidak ditarik dari nama.
- `ran:20260920T000027Z-jamrah->None@20260920T000027Z-jamrah` — rekaman menyebut sasaran (target `jamrah`), bukan program; tautan ke sebuah berkas program tidak ditarik dari nama.
- `executes:rtl/programs/burn_in.hasm->None` — no frozen expectation holds this program's payload; its opcodes are not read from its name.

## Divergensi yang terukur

`20260925T163903Z-stop`: P5 mengukur bahwa silikon menjalankan PRINT sesudah HALT atau RET fault, sedangkan interpreter berhenti sebelumnya -- executes untuk probe itu adalah yang interpreter jalankan, dan papan terbukti menjalankan lebih dari itu (NUI/LAYER4.md).

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.hardware_correlation --verify
```
