# COSMICTERA CT-01-REV13 — STAGE 1.4 FOOTER LAYOUT CORRECTION REPORT

- **Tanggal Pelaksanaan**: 3 November 2026
- **Repositori**: `/Users/AMRA/hijaiyyah-mathematics` (`HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`, `git status --short -uno` bersih)
- **Target Perangkat Keras**: Tang Nano 20K (`GW2AR-LV18QN88C8/I7`, family `GW2A-18C`) — **SRAM Mode Only** (External Flash tidak disentuh)
- **Berkas Constraint**: `/Users/AMRA/hijaiyyah-mathematics/constraints/cosmictera_tangnano20k.cst` (`Candidate B`, SHA-256 `3f16df4fc048f967cae125a31bfe0429e19d20c178df8e83352ea1304bf954a7`)

---

## 1. Hasil Source Inspection & Perbandingan Koordinat (Sebelum vs Sesudah)

Pemeriksaan dilakukan pada `/tmp/stage1_2_cosmictera_boot_ui/build_boot_ui_assets.py`, `rtl/boot_text_rom.hex`, `rtl/cosmictera_boot_text_rom.v`, `rtl/cosmictera_boot_compositor.v`, `rtl/cosmictera_boot_render.v`, `rtl/tb_boot_top.v`, dan `verify_frames_and_render_previews.py`.

Pada resolusi aktif `1280 × 720` piksel (`160 kolom × 90 baris karakter`, font `8 × 8` piksel), posisi footer sebelumnya pada **`row 88`** (`y = 704..711`) hanya menyisakan **8 piksel** (`row 89`, `y = 712..719`) dari tepi bawah frame aktif, sehingga terpotong oleh *overscan* / bezel bawah pada TV LG fisik (`stage1_4_lgtv_page0_16entries.jpg`, batas *overscan* fisik sekitar `y ≈ 706`).

### Tabel Koordinat Vertikal (`y`) — Sebelum vs Sesudah Koreksi

| Elemen Tata Letak | Sebelum Koreksi (Stage 1.4 Awal) | Sesudah Koreksi (Stage 1.4 Rev Footer) | Selisih / Celah Aman |
| :--- | :--- | :--- | :--- |
| **Batas Aktif Video (`1280 × 720`)** | `x = 0..1279`, `y = 0..719` (`cols 0..159`, `rows 0..89`) | `x = 0..1279`, `y = 0..719` (`cols 0..159`, `rows 0..89`) | Tidak berubah |
| **Region 6 Box (`in_r6`, Hardware Event Console)** | `rows 74..84` (`y = 592..679`, tinggi `88 px`) | **`rows 74..83` (`y = 592..671`, tinggi `80 px`)** | Batas bawah naik `8 px` |
| **Region 6 Header & Events (`EV01..EV06`)** | `rows 75, 77, 79, 81` (`y = 600..655`) | **`rows 75, 77, 79, 81` (`y = 600..655`)** | Tidak berubah |
| **Region 6 Summary (`LAST TRANSITION...`)** | `row 83` (`y = 664..671`) | **`row 82` (`y = 656..663`)** | Naik `1 baris` (`8 px`); memiliki padding internal bawah `8 px` (`y = 664..670`) sebelum border bawah Region 6 |
| **Region 6 Bottom Border (`r6_border`)** | `row 84, sub_y = 7` (`y = 679`) | **`row 83, sub_y = 7` (`y = 671`)** | Naik `8 px` |
| **Celah Antar-Region (Region 6 → Region 7)** | `y = 680..687` (`8 px`) | **`y = 672..675` (`4 px` deep navy `#060C16`)** | Bebas tumpang tindih (`4 px`) |
| **Garis Pembatas Atas Footer (`ftr_top_line`)** | `v_count = 688` (`row 86, sub_y = 0`) | **`v_count = 676` (`row 84, sub_y = 4`)** | `4 px` di bawah border Region 6 dan **`4 px` di atas teks footer** (tidak memotong huruf) |
| **Latar Belakang Footer (`in_footer`)** | `y = 688..719` (`32 px`) | **`y = 676..719` (`44 px`)** | Diperluas ke atas mengikuti `ftr_top_line` |
| **Teks Footer Region 7 (`8 × 8` piksel)** | `row 88` (`y = 704..711`) | **`row 85` (`y = 680..687`)** | Naik **`24 px` (`3 baris karakter`)**; berada **`19 px` di atas** batas *overscan* fisik TV LG |
| **Margin Bawah di Bawah Teks Footer** | `row 89` (`y = 712..719` = **`8 piksel`**) | **`rows 86..89` (`y = 688..719` = `32 piksel`)** | **Margin bawah 32 piksel (4× lipat sebelumnya)** |

### Tabel Koordinat Horizontal (`x`) Isi Footer pada `row 85` (`y = 680..687`)

Seluruh 7 kolom informasi footer dipertahankan utuh di dalam rentang horizontal `1280` piksel (`cols 4..151`, `x = 32..1215`, dengan margin kiri `32 px` dan margin kanan `64 px`):

| Field Footer (`row 85`) | Kolom Karakter (`col`) | Koordinat Piksel (`x`) | Warna / Atribut | Sumber Data |
| :--- | :--- | :--- | :--- | :--- |
| `COSMICTERA` | `col 4..13` (`10` kar) | `x = 32..111` | `C_GOLD` (`#F0C860`) | Statis (`ROM row 21`) |
| `TANG NANO 20K GW2AR-18C` | `col 17..39` (`23` kar) | `x = 136..319` | `C_CYAN` (`#30C0D0`) | Statis (`ROM row 21`) |
| `STATE: DISPLAY READY` | `col 44..66` (`23` kar) | `x = 352..535` | `C_GREEN` / Dinamis | Statis `STATE:` + Overlay `col 51..65` (`screen_state`) |
| `RELOCKS: 00` | `col 72..82` (`11` kar) | `x = 576..663` | `C_WHITE` (`#D8E4F0`) | Statis `RELOCKS:` + Overlay `col 81..82` (`relock_count_pix`) |
| `FIFO OVF: NO ` | `col 88..100` (`13` kar) | `x = 704..807` | `C_GREEN` / `C_RED` | Statis `FIFO OVF:` + Overlay `col 98..100` (`fifo_overflow`) |
| `PIN88 PAGE: 00` | `col 106..119` (`14` kar) | `x = 848..959` | `C_WHITE` (`#D8E4F0`) | Statis `PIN88 PAGE:` + Overlay `col 118..119` (`page` `00..12`) |
| `STAGE 1.4 BOOT UI (8C70989B)` | `col 124..151` (`28` kar) | `x = 992..1215` | `C_DIM` (`#7890A8`) | Statis (`ROM row 21`) |

---

## 2. Verifikasi Simulasi RTL & Golden Frame (`P0–P12`)

1. **Regenerasi ROM & Golden Frame (`build_boot_ui_assets.py` & `verify_frames_and_render_previews.py`)**:
   - `rtl/boot_text_rom.hex` diregenerasi (`4.096 × 12-bit`, SHA-256 `421f4455f0fdcb128e6e5ddca2fa2f830c1d9a752689ec5efba3b1e3ce7b6507` tetap identik karena `ROM row 20` dan `ROM row 21` memuat string yang sama persis dan didekode ke `screen row 82` dan `screen row 85` oleh `cosmictera_boot_text_rom.v`).
   - Seluruh 15 frame referensi emas `1280 × 720` (`frame_startup_1280x720.png`, `frame_ready_1280x720.png`, `frame_error_1280x720.png`, serta `frame_page_p01_1280x720.png` s.d. `frame_page_p12_1280x720.png`) telah dirender ulang dan diperiksa secara visual: teks footer pada `row 85` (`y = 680..687`) tampil utuh dengan margin bawah `32 px` dan tanpa tumpang tindih dengan *Hardware Event Console* (`y = 592..671`) maupun garis pembatas (`y = 676`).
2. **Hasil Testbench RTL (`tb_boot_top.v`)**:
   - **30 PASS, 0 FAIL** (`tb_boot_top_stage1_4.log`), mencakup verifikasi *scanline* footer baru pada `y = 682` (`row 85, sub_y = 2`) dan navigasi `Pin 88` (`P0 → P8 → P9 → P10 → P11 → P12 → P0`).
3. **Komparasi Piksel-demi-Piksel terhadap Golden Model Python**:
   - Hero Logo `512 × 184`: **0 / 94.208** selisih piksel (`PASS`)
   - 26 scanline lintas Region 1–7 (`STARTUP`): **0 / 33.280** selisih piksel (`PASS`)
   - 26 scanline lintas Region 1–7 (`READY`): **0 / 33.280** selisih piksel (`PASS`)
   - 26 scanline lintas Region 1–7 (`ERROR`): **0 / 33.280** selisih piksel (`PASS`)
   - **Total**: **0 / 194.048 selisih piksel** (`100% bit-exact`).

---

## 3. Perbandingan Resource Sintesis Yosys & Place-and-Route (`nextpnr-himbaechel`)

Seluruh desain yang sudah tervalidasi (pemetaan pin HDMI `Candidate B`, `rPLL 371.25 MHz`, `CLKDIV /5 = 74.25 MHz`, `OSER10`, 16 entri *Compute Ecosystem*, label epistemik `R2`, telemetri HCPU 87-bit, dan navigasi `P0–P12`) dipertahankan tanpa perubahan.

| Metrik Resource / Timing | Stage 1.4 Baseline (`row 88`) | Stage 1.4 Footer Corrected (`row 85`) | Delta | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Yosys Total Cells** | `4.544` | `4.708` | `+164` | PASS (`0 errors`) |
| **Yosys Total LUT (`LUT1..LUT4`)** | `3.125` (`468 / 557 / 660 / 1.440`) | `3.650` (`484 / 597 / 731 / 1.838`) | `+525` | PASS |
| **Yosys Wide Mux (`MUX2_LUT5..8`)** | `591` (`438 / 108 / 34 / 11`) | `1.011` (`740 / 188 / 61 / 22`) | `+420` | PASS |
| **Yosys ALU Carry (`ALU`)** | `45` | `45` | `0` | Identik |
| **Total Flip-Flops (`DFF*`)** | `770` | `770` | **`0`** | **Identik (`0` DFF tambahan)** |
| **BSRAM (`SP` + `SPX9`)** | `12 / 46` (`26%`) | `12 / 46` (`26%`) | **`0`** | **Identik (`12` blok)** |
| **DSP (`MULT*` / `ALU54D`)** | `0` | `0` | **`0`** | **Identik (`-nodsp`)** |
| **Post-Pack `nextpnr` `LUT4`** | `5.438 / 20.736` (`26%`) | `5.548 / 20.736` (`26%`) | `+110` (`+0,53%`) | PASS |
| **Primitives (`rPLL / CLKDIV / OSER10 / IOB`)** | `1 / 1 / 4 / 7` | `1 / 1 / 4 / 7` | `0` | Identik |
| **STA `clk_27m` Fmax** | `142,27 MHz` | `140,27 MHz` | `-2,00 MHz` | PASS (`5,20×` dari `27 MHz`) |
| **STA `pixel_clk` Post-Place / Post-Route** | `75,55 MHz` / `60,18 MHz` | `74,60 MHz` / `62,48 MHz` | **`+2,30 MHz` post-route** | Meningkat `+2,30 MHz` |

---

## 4. Sidik Jari SHA-256 Berkas & Bukti Pemuatan SRAM Tang Nano 20K

| Berkas | SHA-256 |
| :--- | :--- |
| `/tmp/stage1_2_cosmictera_boot_ui/build_boot_ui_assets.py` | `883a105b130ffd1655015034f5cdee0e529ac1d397877c7dcbe0782040525b27` |
| `/tmp/stage1_2_cosmictera_boot_ui/verify_frames_and_render_previews.py` | `5b04dcb0aaf5c550d913a7b1d402af6be550952837b6f975a5574ba59426c200` |
| `/tmp/stage1_2_cosmictera_boot_ui/rtl/boot_text_rom.hex` | `421f4455f0fdcb128e6e5ddca2fa2f830c1d9a752689ec5efba3b1e3ce7b6507` |
| `/tmp/stage1_2_cosmictera_boot_ui/rtl/cosmictera_boot_text_rom.v` | `abacf7bd12d1accbed04d31698151cd67a8246f68074fd2528681d4b1e8ac3db` |
| `/tmp/stage1_2_cosmictera_boot_ui/rtl/cosmictera_boot_compositor.v` | `8f6c80a55b19bb1298ab390eb6f7b4e9dfd6188cb9966c9101117276ee130426` |
| `/tmp/stage1_2_cosmictera_boot_ui/rtl/cosmictera_boot_render.v` | `531604c2779b731a30368bbd12dad42eb114faf52a7759341704a4db9c8a1d7b` |
| `/tmp/stage1_2_cosmictera_boot_ui/rtl/tb_boot_top.v` | `f393e98542161e26d9cf485a3a6ea391f43132deaf7596af6c2f8eb0e852952f` |
| `/tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4.json` | `152382af6441f478a830e7c82bc577dbb8e9f93b15e9476318ca5de99ad595ae` |
| `/tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4_pnr.json` | `b22459072c4fabfc57b24aa831319ae0dfa5d341a903c56798c6e93cce4d8219` |
| `/tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4.fs` | `c2a715edf524fa67ba28108bcea5a864bc9d41a00dc743444cb9ccc7f842ffc2` |
| `/tmp/stage1_2_cosmictera_boot_ui/frame_previews/frame_ready_1280x720.png` | `320cce2e162a1614ac863aea3c6d1d24f6e7ce9d32c69eed4b1416d0e23cbdc3` |

### Log Pemuatan SRAM (`sram_load_stage1_4.log`)

```text
Jtag frequency : requested 6.00MHz    -> real 6.00MHz
index 0:
	idcode 0x81b
	manufacturer Gowin
	family GW2A
	model  GW2A(R)-18(C)
	irlength 8
Parse file Parse /tmp/stage1_2_cosmictera_boot_ui/cosmictera_boot_top_stage1_4.fs:
Done
DONE
Erase SRAM Load SRAM
Load SRAM: [==================================================] 100.00%
Done
DONE
```

- **Status Verifikasi Perangkat Keras Footer (`row 85`)**: **MENUNGGU KONFIRMASI FOTO TV LG** (sesuai protokol, klaim `HARDWARE PASS` untuk visibilitas penuh footer pada TV LG baru ditetapkan setelah foto tampilan fisik TV LG dikonfirmasi).

