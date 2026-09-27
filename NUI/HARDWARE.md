# Inventaris hardware — Lapis 6.1

Dihasilkan `src/hijaiyyah/nui/hardware.py` dari `NUI/spec/hardware_inventory.json`. Tidak ada RTL, papan, sensor, port debug, atau telemetri baru yang disentuh untuknya: tiap nilai dibaca dari bukti yang sudah ada.

**19 MEASURED** (dibuktikan secara fisik), **11 SIMULATED** (RTL atau interpreter — dan hasil synthesis, place-and-route, dan analisis build yang ditandai `PNR/build-derived`: **bukan simulasi perilaku dan bukan pengukuran fisik**, K-18), **4 UNKNOWN** (belum ada jalur observasi, jadi tanpa nilai).

## hardware apa yang sedang dipakai?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| papan | `Tang Nano 20K` | MEASURED | board | `cosmictera-build/attack-lab/20260925T191528Z-loader.json#board` | 20260925T191528Z-loader (P6), rekaman papan paling baru; burn-in 72 jam | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` `5e4a2a52ac26…`<br>`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json` `09302ae1de43…` |
| FPGA | `GW2AR-LV18QN88C8/I7` | MEASURED | board | `rtl/fpga/gowin/Makefile:24` | bitstream loader 84fdc912... yang dibangun untuk device ini mengkonfigurasi papan dan berjalan (capture P1) | `rtl/fpga/gowin/Makefile` `8f932fad1b61…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` `768fdfb0db49…` |
| CPU | `Hijaiyyah Core Processing Unit` | MEASURED | board | `teknologi/ISTILAH.md:44` | paritas papan P2, 79 program dikirim, 73 PARITY | `cosmictera-build/parity-board/20260924T105400Z-parity.json` `f35ec747475e…` |
| bitstream | `84fdc91232465c9600e1f7cc59dba891f309c69cf2441c448d684baaf4a7e261` | MEASURED | board | `NUI/layer4_freeze.json#bitstream_sha256` | tujuh rekaman papan P1-P5 membawa sidik jari yang sama | `NUI/layer4_freeze.json` `86d8e241d314…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` `768fdfb0db49…` |
| watchdog | `0` | SIMULATED | rtl | `facts/burnin/no_watchdog_exists.json#value` | — | `facts/burnin/no_watchdog_exists.json` `a94c18f81455…` |

## FPGA apa?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| FPGA | `GW2AR-LV18QN88C8/I7` | MEASURED | board | `rtl/fpga/gowin/Makefile:24` | bitstream loader 84fdc912... yang dibangun untuk device ini mengkonfigurasi papan dan berjalan (capture P1) | `rtl/fpga/gowin/Makefile` `8f932fad1b61…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` `768fdfb0db49…` |
| FPGA | `GW2A-18C` | MEASURED | board | `rtl/fpga/gowin/Makefile:25` | bitstream yang sama, capture P1 | `rtl/fpga/gowin/Makefile` `8f932fad1b61…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` `768fdfb0db49…` |
| sumber daya FPGA | `15,744 / 20,736` | SIMULATED | PNR/build-derived | `rtl/fpga/gowin/hcpu_gowin_top.v:47` | place and route yang dicap di kepala wrapper, dijaga tests/test_integrity/test_place_and_route.py | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |
| sumber daya FPGA | `5,065 / 15,552` | SIMULATED | PNR/build-derived | `rtl/fpga/gowin/hcpu_gowin_top.v:48` | place and route yang dicap di kepala wrapper | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |
| sumber daya FPGA | `18 /     46` | SIMULATED | PNR/build-derived | `rtl/fpga/gowin/hcpu_gowin_top.v:49` | place and route yang dicap di kepala wrapper | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |
| sumber daya FPGA | `86.18 MHz` | SIMULATED | PNR/build-derived | `rtl/fpga/gowin/hcpu_gowin_top.v:52` | analisis timing nextpnr | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |

## CPU apa?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| CPU | `Hijaiyyah Core Processing Unit` | MEASURED | board | `teknologi/ISTILAH.md:44` | paritas papan P2, 79 program dikirim, 73 PARITY | `cosmictera-build/parity-board/20260924T105400Z-parity.json` `f35ec747475e…` |
| CPU | `5-stage pipeline with forwarding` | SIMULATED | rtl | `rtl/hcpu_top.v:3` | — | `rtl/hcpu_top.v` `98f70974c232…` |
| H-ISA | `82` | SIMULATED | rtl | `teknologi/README.md:34` | — | `teknologi/README.md` `960f357c1436…`<br>`rtl/hcpu_pkg.vh` `bca67ed7cfbd…` |
| H-ISA | `74` | MEASURED | board | `NUI/layer4_freeze.json#status.opcodes.PARITY` | kolom perangkat keras P3, dihitung ulang dari rekaman P2, beku di layer4-freeze-2026-09-26 | `NUI/layer4_freeze.json` `86d8e241d314…`<br>`cosmictera-build/parity-board/20260924T105400Z-parity.json` `f35ec747475e…` |
| H-ISA | — | UNKNOWN | none | — | — | `NUI/layer4_freeze.json` `86d8e241d314…` |

## clock berapa?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| sumber daya FPGA | `86.18 MHz` | SIMULATED | PNR/build-derived | `rtl/fpga/gowin/hcpu_gowin_top.v:52` | analisis timing nextpnr | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |
| clock | `27 MHz` | MEASURED | board | `rtl/fpga/gowin/hcpu_gowin.cst:6` | burn-in 24 jam: jam papan terhadap jam host hanyut -0,0292 detik per jam | `rtl/fpga/gowin/hcpu_gowin.cst` `eaa86f79a1fc…`<br>`facts/burnin/tier1_clock_drift.json` `5c998033f745…`<br>`cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` `0733c06ad3c2…` |
| clock | `-0.0292` | MEASURED | board | `facts/burnin/tier1_clock_drift.json#value` | burn-in 24 jam, 20 September 2026 | `facts/burnin/tier1_clock_drift.json` `5c998033f745…`<br>`cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json` `0733c06ad3c2…` |
| clock | `0` | SIMULATED | rtl | `rtl/fpga/gowin/hcpu_gowin_top.v:280` | — | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |

## memory apa?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| sumber daya FPGA | `18 /     46` | SIMULATED | PNR/build-derived | `rtl/fpga/gowin/hcpu_gowin_top.v:49` | place and route yang dicap di kepala wrapper | `rtl/fpga/gowin/hcpu_gowin_top.v` `cacdf46a41e0…` |
| memori instruksi | `4096` | SIMULATED | rtl | `facts/hisa/instruction_memory_words.json#value` | — | `facts/hisa/instruction_memory_words.json` `1f605f86edf9…` |
| memori data | `4096` | SIMULATED | rtl | `facts/repository/data_memory_words.json#value` | — | `facts/repository/data_memory_words.json` `9a23240237e7…` |
| kartu SD/TF | `M4.2 — kartu menjawab, dan menyimpan, 15 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:485` | M4.2, 15 September 2026 | `cosmictera-build/PAPAN.md` `140ac8ca79e5…` |
| program dari kartu | `Lintas sektor dan ACK — shell naik dari sebelas sektor kartu, 18 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:782` | 18 September 2026 | `cosmictera-build/PAPAN.md` `bf95c4bc981d…` |
| HOS/HFS | `Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:608` | tahap 1, 18 September 2026 | `cosmictera-build/PAPAN.md` `d4587623fe18…` |

## peripheral apa?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| UART | `115200` | MEASURED | board | `rtl/fpga/gowin/hcpu_gowin_top.v:291` | setiap rekaman papan datang lewat kabel ini; capture P1 menyimpan byte mentahnya | `rtl/fpga/gowin/hcpu_gowin.cst` `eaa86f79a1fc…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` `31e69b52ae17…` |
| kartu SD/TF | `M4.2 — kartu menjawab, dan menyimpan, 15 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:485` | M4.2, 15 September 2026 | `cosmictera-build/PAPAN.md` `140ac8ca79e5…` |
| kartu SD/TF | `8` | MEASURED | board | `facts/fpga/sd_init_fails_after_interrupted_read.json#value` | delapan peluncuran dari delapan, berselang-seling | `facts/fpga/sd_init_fails_after_interrupted_read.json` `52ca4df62dc4…` |
| HDMI | `Pixel HDMI rusak, dan sambungannya sendiri sehat` | MEASURED | board | `cosmictera-build/OFF.md:20` | M5, 15-17 September 2026 | `cosmictera-build/OFF.md` `39c89c0af55f…` |
| LED | `6` | SIMULATED | rtl | `rtl/fpga/gowin/hcpu_gowin.cst:50` | — | `rtl/fpga/gowin/hcpu_gowin.cst` `eaa86f79a1fc…` |
| tombol reset | `Reset yang digerbangi level pin MODE1` | MEASURED | board | `cosmictera-build/PAPAN.md:1321` | 10 September 2026, cacat yang hanya papan bisa temukan | `cosmictera-build/PAPAN.md` `806d3704ba47…`<br>`rtl/fpga/gowin/hcpu_gowin.cst` `eaa86f79a1fc…` |
| telemetri | `UART` | MEASURED | board | `cosmictera/TELEMETRY.md:188` | capture P1: byte mentah kabel | `cosmictera/TELEMETRY.md` `511715a71e9b…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` `31e69b52ae17…` |

## program apa yang sedang dimuat?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| loader program | `0` | MEASURED | board | `cosmictera-build/attack-lab/20260925T191528Z-loader.json#findings` | P6, 19 kasus di papan | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` `5e4a2a52ac26…` |
| program dari kartu | `Lintas sektor dan ACK — shell naik dari sebelas sektor kartu, 18 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:782` | 18 September 2026 | `cosmictera-build/PAPAN.md` `bf95c4bc981d…` |
| HOS/HFS | `Tahap 1 — berkas bertahan melewati mati daya, 18 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:608` | tahap 1, 18 September 2026 | `cosmictera-build/PAPAN.md` `d4587623fe18…` |
| HOS | `M3 — shell menjawab kabel serial, 12 September 2026` | MEASURED | board | `cosmictera-build/PAPAN.md:253` | M3, 12 September 2026 | `cosmictera-build/PAPAN.md` `3789496d48e3…` |
| bitstream | `84fdc91232465c9600e1f7cc59dba891f309c69cf2441c448d684baaf4a7e261` | MEASURED | board | `NUI/layer4_freeze.json#bitstream_sha256` | tujuh rekaman papan P1-P5 membawa sidik jari yang sama | `NUI/layer4_freeze.json` `86d8e241d314…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` `768fdfb0db49…` |
| program yang sedang dimuat | — | UNKNOWN | none | — | — | `cosmictera-build/attack-lab/20260925T191528Z-loader.json` `5e4a2a52ac26…` |

## telemetry apa yang tersedia?

| hardware | nilai | kelas | jenis bukti | sumber | run | bukti |
|---|---|---|---|---|---|---|
| telemetri | `23` | MEASURED | board | `cosmictera/TELEMETRY.md:36` | burn-in, validasi Jamrah, Ka'bah, Hijrah, dan lab serangan di papan | `cosmictera/TELEMETRY.md` `0f4884c08035…`<br>`cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json` `09302ae1de43…` |
| telemetri | — | UNKNOWN | none | — | — | `facts/telemetry/four_fields_have_no_source.json` `afa9e6d85331…` |
| telemetri | `UART` | MEASURED | board | `cosmictera/TELEMETRY.md:188` | capture P1: byte mentah kabel | `cosmictera/TELEMETRY.md` `511715a71e9b…`<br>`cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.raw` `31e69b52ae17…` |
| telemetri yang sedang mengalir | — | UNKNOWN | none | — | — | `cosmictera/TELEMETRY.md` `48c95af1dc22…` |
| watchdog | `0` | SIMULATED | rtl | `facts/burnin/no_watchdog_exists.json#value` | — | `facts/burnin/no_watchdog_exists.json` `a94c18f81455…` |

## Kenapa

- `board` — nama papan dicatat oleh lari papan itu sendiri.
- `fpga_device` — nomor part dari Makefile; buktinya fisik karena bitstream untuknya dimuat ke papan dan berjalan.
- `fpga_family` — keluarga device yang dipakai gowin_pack untuk bitstream yang berjalan di papan.
- `fpga_lut4` — angka nextpnr untuk slot CPU, bukan dibaca dari papan.
- `fpga_dff` — angka nextpnr, bukan dibaca dari papan.
- `fpga_bsram` — blok BSRAM yang dipakai slot CPU, menurut nextpnr.
- `fpga_fmax` — frekuensi maksimum menurut analisis timing; papan berjalan di 27 MHz.
- `cpu` — HCPU menjalankan program di papan; kepanjangannya dari glosarium.
- `cpu_pipeline` — struktur pipeline dari RTL; tidak ada jalur yang mengamatinya dari luar papan.
- `isa_rtl` — opcode yang diimplementasikan RTL, dihitung dari rtl/hcpu_pkg.vh.
- `isa_board` — opcode yang perilakunya di papan cocok dengan interpreter.
- `isa_board_unknown` — opcode tanpa bukti papan yang bisa memutuskan: tak satu pun program yang dikirim menjalankannya, atau buktinya campur. Jumlahnya di status.opcodes.UNKNOWN freeze Lapis 4.
- `clock` — osilator di pin 4 menurut batasan pin; slot CPU berjalan langsung darinya (USE_PLL = 0), dan jam papan yang dihitung darinya hanyut 8,1 ppm terhadap jam host -- relatif terhadap jam host, bukan standar frekuensi.
- `clock_drift` — detik per jam, jam papan dikurangi jam host.
- `clock_pll` — 0 berarti clock sistem langsung dari osilator 27 MHz, tanpa rPLL.
- `imem_words` — kata 32-bit, dihitung ulang dari desain.
- `dmem_words` — kata 32-bit; enam belas kata teratas adalah peripheral.
- `uart` — baud, 8N1, pin 69 kirim dan 70 terima.
- `sd_card` — SDIO 1-bit; kartu SDHC menjawab dan menyimpan di papan.
- `sd_init_defect` — percobaan init yang gagal sesudah rekonfigurasi di tengah baca -- cacat terbuka.
- `hdmi` — node display berjalan di papan sebagai slot sendiri; jalur pixel-nya cacat terbuka, penyelidikannya dibekukan pemilik.
- `leds` — pin yang dipasang; keadaan LED tidak pernah direkam dari papan.
- `reset_button` — btn_rst_n di pin 87; cacat reset-nya ditemukan di papan dan dibetulkan lewat batasan pin.
- `loader` — temuan lab serangan loader CHECKSUM32 di papan; 15 ditolak dan 4 diterima, seperti yang dimaksud tiap kategori.
- `shell_from_card` — shell dimuat dari sebelas sektor kartu dan berjalan.
- `hfs` — CREATE, WRITE, cabut daya, nyalakan, READ identik.
- `hos_shell` — shell -> SYSCALL -> kernel -> HAL -> UART menjawab di papan.
- `bitstream_last_measured` — sidik jari bitstream loader yang dipakai lari-lari Lapis 4.
- `program_now` — tidak ada jalur yang membaca konfigurasi papan saat ini; rekaman papan paling baru adalah lab loader P6, 25 September 2026 19:15 UTC.
- `telemetry_fields` — medan kontrak telemetri v1 yang sumbernya lari papan.
- `telemetry_no_source` — anomaly_score, corruption_score, state_hash, last_relocation belum punya sumber (fakta telemetry.four_fields_have_no_source).
- `telemetry_path` — satu-satunya jalur keluar papan hari ini; PRINT tidak bisa mencetak angka besar, jadi medan 32-bit dipecah.
- `telemetry_live` — tidak ada lari papan yang sedang diamati; irama dan jalur pelaporan telemetri belum ditetapkan pemilik.
- `watchdog` — tidak ada modul watchdog di rtl/; mesin yang berhenti tidak bisa melaporkan bahwa ia berhenti.

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.hardware --verify
```
