# Adendum pasca-freeze Lapis 6

Dihasilkan `src/hijaiyyah/nui/layer6_addendum.py` dari `NUI/layer6_addendum.json`. Keputusan pemilik, 1 Oktober 2026, sesudah commit HMAC `4bff781` membuat tiga `--verify` Lapis 6 merah oleh drift pasca-freeze yang diharapkan.

> Registry beku tetap immutable; adendum adalah catatan baru. Tiap entri: pointer/hash lama → keadaan sekarang, alasan konkret, commit penyebab, dan evidence kesetaraan. Tidak ada pemetaan massal tanpa alasan. Verifier membaca keduanya: historical freeze ≠ current repository state.

Catatan beku Lapis 6.1–6.3 — model, halaman, dan spec-nya — tetap byte demi byte objek di tag `layer6-freeze-2026-09-29-final`. Adendum ini catatan baru di sampingnya, bukan bangkitan ulang: **freeze historis ≠ keadaan repositori sekarang**. Keadaan sekarang adalah catatan beku dengan perubahan di bawah ini, dan harus sama dengan yang dibangun buktinya hari ini.

**18 entri, 205 perubahan**: `hardware` 74, `telemetry_sources` 16, `hardware_provenance` 115.

## Bukti kesetaraan

- **comment-only** — setiap baris yang bukan baris kosong dan bukan komentar utuh `//` sama dan berurutan sama di berkas beku dan berkas sekarang — aturan yang dipakai sidik jari place and route; yang berubah hanya komentar, jadi desainnya tidak.
- **insert-only** — setiap baris berkas beku masih ada, utuh dan berurutan, di berkas sekarang; barisnya hanya bertambah, tidak ada yang hilang atau diubah.
- **line-moved** — tiap baris yang dikutip punya teks yang sama persis di nomor barunya — di freeze (atau di pendahulunya pada rantai `after`), tepat sebelum penyebab, di penyebab, dan sekarang.
- **row-meaning** — baris kontrak diurai dengan pola baris `NUI/spec/telemetry_sources.json`: medan dan asalnya sama, dan medannya tetap tanpa sumber — jadi statusnya tetap.
- **remeasured-header** — angka synthesis dan place-and-route di kepala pembungkus FPGA diukur ulang dan diikat ke sidik jari RTL hidup, hash berkas sumber, konfigurasi target/constraint/build, versi perkakas, dan hash laporan mentah synthesis/PnR serta catatan papan, sambil menjaga kelas `SIMULATED` (`PNR/build-derived`) tetap terpisah dari klaim `MEASURED` papan fisik.
- **claim-unchanged** — berkas sumber RTL berubah secara desain sehingga hanya metadata hash/ukuran bukti berkas utuh yang bergeser, sementara kontrak spesifikasi, identitas klaim, sumber, nomor baris, nilai, status, dan baris jangkar arsitekturnya tetap sama.

## Rantai perubahan

Keputusan pemilik, 5 Oktober 2026 (diperluas 2 November 2026 untuk Jalur A), sesudah commit lapis 3 Ka'bah `004b9a0` menambah baris ke `Makefile` yang sudah pernah ditambah `4bff781` dan commit Paket 8 `f9c8349` mencap ulang `hcpu_gowin_top.v` serta memperbarui `hcpu_top.v`: perubahan kedua pada satu berkas tidak diterima karena ia perubahan kedua, melainkan hanya sebagai entri yang menyebut, di `after`, satu entri yang dilanjutkannya — dan tiap mata rantainya diperiksa. Entri yang disebut ditulis lebih dulu dan tentang berkas yang sama; ia dilanjutkan oleh satu entri saja, rantai tidak bercabang; pointer yang diubah persis sama, dan nilai lama di sini adalah nilai baru di sana; commit penyebabnya keturunan commit penyebab entri itu; berkas tepat sebelum penyebabnya ber-hash nilai di penyebab pendahulunya, jadi tidak ada yang menyentuh berkas di antara keduanya; dan bukti kesetaraannya sendiri berlaku sejak penyebab entri itu. Entri yang dilanjutkan lalu menjawab untuk berkas di commit penyebabnya saja, dan entri terakhir rantai untuk berkas sekarang. Hanya hash berkas utuh (`comment-only`, `insert-only`, `claim-unchanged`) dan pergeseran nomor baris linear (`line-moved`) yang berantai. Pointer yang diubah dua kali tanpa mata rantai itu tetap ditolak.

Untuk tiap perubahan: nilai lama adalah nilai catatan beku dan dihasilkan ulang dari berkasnya di freeze dan tepat sebelum commit penyebab; nilai sekarang adalah hasil build hari ini dan dihasilkan ulang dari berkasnya di commit penyebab dan di pohon kerja.

## hcpu_gowin_top.v — cap ulang opsi (a)

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `4bff781` · bukti kesetaraan **comment-only**

Opsi (a) pemilik, 1 Oktober 2026: tiga modul HMAC di `rtl/` menggeser sidik jari HCPU, karena penjaganya membaca `rtl/*.v` lewat wildcard. Place and route HCPU diulang dan setiap angkanya identik, lalu kepala berkas dicap ulang: satu baris komentar sidik jari diganti tujuh baris komentar yang mencatat lari itu. Berkasnya 33.930 → 34.404 byte, jadi hash utuhnya berubah; tidak ada baris desain yang berubah, dan nilai yang dibaca klaim-klaimnya dari berkas ini sama.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_lut4` | `/items/3/source/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_lut4` | `/items/3/evidence/0/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_dff` | `/items/4/source/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_dff` | `/items/4/evidence/0/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_bsram` | `/items/5/source/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_bsram` | `/items/5/evidence/0/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_fmax` | `/items/6/source/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `fpga_fmax` | `/items/6/evidence/0/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `clock_pll` | `/items/14/source/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `clock_pll` | `/items/14/evidence/0/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware` | `uart` | `/items/17/source/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `telemetry_sources` | — | `/rtl_signals/sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/evidence_bytes` | `33930` | `34404` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/evidence_sha256` | `cacdf46a41e0…` | `b4f03c9d1365…` |

## hcpu_gowin_top.v — baris turun enam

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `4bff781` · bukti kesetaraan **line-moved**, baris 280 → 286, 291 → 297, 327 → 333, 328 → 334, 329 → 335, 330 → 336, 331 → 337, 332 → 338

Cap ulang yang sama menambah enam baris komentar bersih di kepala berkas — satu baris diganti tujuh — jadi setiap baris sesudahnya turun enam: PLL 280 → 286, UART 291 → 297, dan keenam port `tele_*` 327–332 → 333–338. Teks tiap baris yang dikutip sama persis di tempat barunya.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `clock_pll` | `/items/14/source/line` | `280` | `286` |
| `hardware` | `uart` | `/items/17/source/line` | `291` | `297` |
| `telemetry_sources` | `tele_pc` | `/rtl_signals/signals/0/line` | `327` | `333` |
| `telemetry_sources` | `tele_instr` | `/rtl_signals/signals/1/line` | `328` | `334` |
| `telemetry_sources` | `tele_halted` | `/rtl_signals/signals/2/line` | `329` | `335` |
| `telemetry_sources` | `tele_guard` | `/rtl_signals/signals/3/line` | `330` | `336` |
| `telemetry_sources` | `tele_cycles` | `/rtl_signals/signals/4/line` | `331` | `337` |
| `telemetry_sources` | `tele_flags` | `/rtl_signals/signals/5/line` | `332` | `338` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/source/line` | `280` | `286` |
| `hardware_provenance` | `6.1:uart` | `/claims/17/source/line` | `291` | `297` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/claim` | `tele_pc = port rtl/fpga/gowin/hcpu_gowin_top.v:327` | `tele_pc = port rtl/fpga/gowin/hcpu_gowin_top.v:333` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/source/line` | `327` | `333` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/claim` | `tele_instr = port rtl/fpga/gowin/hcpu_gowin_top.v:328` | `tele_instr = port rtl/fpga/gowin/hcpu_gowin_top.v:334` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/source/line` | `328` | `334` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/claim` | `tele_halted = port rtl/fpga/gowin/hcpu_gowin_top.v:329` | `tele_halted = port rtl/fpga/gowin/hcpu_gowin_top.v:335` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/source/line` | `329` | `335` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/claim` | `tele_guard = port rtl/fpga/gowin/hcpu_gowin_top.v:330` | `tele_guard = port rtl/fpga/gowin/hcpu_gowin_top.v:336` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/source/line` | `330` | `336` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/claim` | `tele_cycles = port rtl/fpga/gowin/hcpu_gowin_top.v:331` | `tele_cycles = port rtl/fpga/gowin/hcpu_gowin_top.v:337` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/source/line` | `331` | `337` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/claim` | `tele_flags = port rtl/fpga/gowin/hcpu_gowin_top.v:332` | `tele_flags = port rtl/fpga/gowin/hcpu_gowin_top.v:338` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/source/line` | `332` | `338` |

## Makefile — target HMAC

`rtl/fpga/gowin/Makefile` · penyebab `4bff781` · bukti kesetaraan **insert-only**

4bff781 menambahkan `sim_hmac`, `hmac_synth`, `hmac_bitstream`, dan `hmac_flash` — 44 baris, tidak ada yang dihapus atau diubah. Baris 24 dan 25 yang dibaca `fpga_device` dan `fpga_family` tidak berubah dan tidak bergeser; yang berubah hash utuh berkasnya.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_device` | `/items/1/source/sha256` | `8f932fad1b61…` | `9143ca3e6e88…` |
| `hardware` | `fpga_device` | `/items/1/evidence/0/sha256` | `8f932fad1b61…` | `9143ca3e6e88…` |
| `hardware` | `fpga_family` | `/items/2/source/sha256` | `8f932fad1b61…` | `9143ca3e6e88…` |
| `hardware` | `fpga_family` | `/items/2/evidence/0/sha256` | `8f932fad1b61…` | `9143ca3e6e88…` |

## PAPAN.md — bagian HMAC disisipkan

`cosmictera-build/PAPAN.md` · penyebab `4bff781` · bukti kesetaraan **line-moved**, baris 1315 → 1348, 1321 → 1354

4bff781 menyisipkan bagian *HMAC-SHA256 di slot sendiri — 207 dari 207, 1 Oktober 2026* (33 baris) sebelum *Validasi Ka'bah*, di atas bagian yang dikutip `reset_button`. Judul *Tiga cacat yang hanya papan bisa temukan* turun 1315 → 1348 dan butir reset pin MODE1 1321 → 1354, dengan teks yang sama: hash baris yang dikutip tidak berubah, dan rantai provenance klaim ini tetap hanya gagal di pemeriksaan 6, seperti saat dibekukan.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `reset_button` | `/items/22/source/line` | `1321` | `1354` |
| `hardware` | `reset_button` | `/items/22/evidence/0/lines/0` | `1321` | `1354` |
| `hardware_provenance` | `6.1:reset_button` | `/claims/22/source/line` | `1321` | `1354` |
| `hardware_provenance` | `6.1:reset_button` | `/claims/22/evidence_lines/0` | `1315` | `1348` |
| `hardware_provenance` | `6.1:reset_button` | `/claims/22/evidence_lines/1` | `1321` | `1354` |

## TELEMETRY.md:50 — baris state_hash (K14)

`cosmictera/TELEMETRY.md` · penyebab `4bff781` · bukti kesetaraan **row-meaning**, baris 50

Pembaruan K14 di 4bff781: baris `state_hash` berhenti mengatakan *tidak ada inti SHA-256 di RTL (R10)* dan kini mengatakan inti itu ada sejak 1 Oktober 2026 sebagai slot sendiri, tidak tersambung ke HCPU, jadi tidak meringkas keadaan ini, dan `state_hash` tidak berubah (opsi C). Registry mengutip baris itu dengan hash-nya, jadi hash itu berubah; medannya tetap tanpa sumber dan tetap UNKNOWN.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `telemetry_sources` | `state_hash` | `/registry/14/evidence/0/sha256` | `f5997abd1937…` | `fb93c2c3d3c2…` |

## Makefile — lapis 3 slot UART Ka'bah

`rtl/fpga/gowin/Makefile` · penyebab `004b9a0` · bukti kesetaraan **insert-only** · melanjutkan entri **Makefile — target HMAC**

004b9a0 menambahkan `KABAH_L3_DEFINE`, `KABAH_L3_SOURCES`, dan satu baris variabel khusus-target untuk `sim_kabah` dan `kabah_synth`, supaya hanya build slot UART Ka'bah yang membaca `kabah_with_hmac.vh` dan tiga sumber HMAC — 16 baris, tidak ada yang dihapus atau diubah. Baris 24 dan 25 yang dibaca `fpga_device` dan `fpga_family` tidak berubah dan tidak bergeser; yang berubah hash utuh berkasnya, untuk kedua kalinya sejak freeze.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_device` | `/items/1/source/sha256` | `9143ca3e6e88…` | `7a2b150d6247…` |
| `hardware` | `fpga_device` | `/items/1/evidence/0/sha256` | `9143ca3e6e88…` | `7a2b150d6247…` |
| `hardware` | `fpga_family` | `/items/2/source/sha256` | `9143ca3e6e88…` | `7a2b150d6247…` |
| `hardware` | `fpga_family` | `/items/2/evidence/0/sha256` | `9143ca3e6e88…` | `7a2b150d6247…` |

## hcpu_top.v — alternatif RTL A1–A3 (P6)

`rtl/hcpu_top.v` · penyebab `48cf0e5` · bukti kesetaraan **claim-unchanged**, klaim `cpu_pipeline`

48cf0e5 menambahkan pengkabelan alternatif RTL A1–A3 (`calu_add_ovf`, `sd_sector_csum`, `sd_prescan_status`, dan `OP_HDOT`) ke `rtl/hcpu_top.v`. Ukuran berkas bergeser 37.028 → 38.350 byte, tetapi struktur pipeline lima tahap (`5-stage pipeline with forwarding` di baris 7) beserta instansiasi kelima tahapnya dan klaim `cpu_pipeline` tetap tidak berubah.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `cpu_pipeline` | `/items/8/source/sha256` | `98f70974c232…` | `ff79c907ba8b…` |
| `hardware` | `cpu_pipeline` | `/items/8/evidence/0/sha256` | `98f70974c232…` | `ff79c907ba8b…` |
| `hardware_provenance` | `6.1:cpu_pipeline` | `/claims/8/evidence_bytes` | `37028` | `38350` |
| `hardware_provenance` | `6.1:cpu_pipeline` | `/claims/8/evidence_sha256` | `98f70974c232…` | `ff79c907ba8b…` |

## hcpu_pkg.vh — alternatif RTL A1–A3 (P6)

`rtl/hcpu_pkg.vh` · penyebab `48cf0e5` · bukti kesetaraan **claim-unchanged**, klaim `isa_rtl`

48cf0e5 menambahkan konstanta register MMIO kartu `SD_CSUM` (`0x5`), `SD_PRESCAN` (`0x6`), dan `OP_HDOT` (`8'h4E`) ke `rtl/hcpu_pkg.vh`. Ukuran berkas bergeser 21.087 → 21.408 byte; seluruh definisi opcode beku tetap ada, sumber klaim `isa_rtl` di `teknologi/README.md` serta cacah 62 opcode RTL tidak berubah.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `isa_rtl` | `/items/9/evidence/1/sha256` | `bca67ed7cfbd…` | `2e0c3df26eb5…` |
| `hardware_provenance` | `6.1:isa_rtl` | `/claims/9/evidence_bytes` | `21087` | `21408` |
| `hardware_provenance` | `6.1:isa_rtl` | `/claims/9/evidence_sha256` | `bca67ed7cfbd…` | `2e0c3df26eb5…` |

## hcpu_top.v — CODEX_PROFILE dan calu_done (Paket 8)

`rtl/hcpu_top.v` · penyebab `f9c8349` · bukti kesetaraan **claim-unchanged**, klaim `cpu_pipeline` · melanjutkan entri **hcpu_top.v — alternatif RTL A1–A3 (P6)**

f9c8349 meneruskan parameter `CODEX_PROFILE` dan `HDOT_ENABLE` ke `hcpu_codex_alu` serta `hcpu_decode`, dan menahan pipeline lewat `calu_done` selama `OP_HDOT` 14 siklus pada profil 2. Ukuran berkas bergeser 38.350 → 38.892 byte; struktur lima tahap pipeline pada baris 7 dan klaim `cpu_pipeline` tetap tidak berubah.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `cpu_pipeline` | `/items/8/source/sha256` | `ff79c907ba8b…` | `b903847fe23f…` |
| `hardware` | `cpu_pipeline` | `/items/8/evidence/0/sha256` | `ff79c907ba8b…` | `b903847fe23f…` |
| `hardware_provenance` | `6.1:cpu_pipeline` | `/claims/8/evidence_bytes` | `38350` | `38892` |
| `hardware_provenance` | `6.1:cpu_pipeline` | `/claims/8/evidence_sha256` | `ff79c907ba8b…` | `b903847fe23f…` |

## hcpu_gowin_top.v — cap ulang Paket 8

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `f9c8349` · bukti kesetaraan **comment-only** · melanjutkan entri **hcpu_gowin_top.v — cap ulang opsi (a)**

f9c8349 mencap ulang kepala `rtl/fpga/gowin/hcpu_gowin_top.v` sesudah place-and-route Paket 8 (`CODEX_PROFILE=2` pada `USE_DSP=0`): 19 baris komentar bersih ditambahkan untuk mencatat hasil pengukuran baru dan sidik jari `c9fdd83e97fe…`, sementara seluruh baris kode Verilog di dalam berkas ini tetap identik (`comment-only`, 34.404 → 35.688 byte).

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_lut4` | `/items/3/source/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_lut4` | `/items/3/evidence/0/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_dff` | `/items/4/source/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_dff` | `/items/4/evidence/0/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_bsram` | `/items/5/source/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_bsram` | `/items/5/evidence/0/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_fmax` | `/items/6/source/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `fpga_fmax` | `/items/6/evidence/0/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `clock_pll` | `/items/14/source/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `clock_pll` | `/items/14/evidence/0/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware` | `uart` | `/items/17/source/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `telemetry_sources` | — | `/rtl_signals/sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/evidence_bytes` | `34404` | `35688` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/evidence_sha256` | `b4f03c9d1365…` | `7e42e6890d25…` |

## hcpu_gowin_top.v — baris turun sembilan belas

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `f9c8349` · bukti kesetaraan **line-moved**, baris 286 → 305, 297 → 316, 333 → 352, 334 → 353, 335 → 354, 336 → 355, 337 → 356, 338 → 357 · melanjutkan entri **hcpu_gowin_top.v — baris turun enam**

Cap ulang Paket 8 di `f9c8349` menyisipkan 19 baris komentar bersih di kepala `rtl/fpga/gowin/hcpu_gowin_top.v`, sehingga setiap baris di bawah blok riwayat turun 19 baris dari posisinya sesudah `4bff781`: PLL 286 → 305, UART 297 → 316, dan keenam port `tele_*` 333–338 → 352–357, dengan teks baris yang dikutip tetap identik byte demi byte.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `clock_pll` | `/items/14/source/line` | `286` | `305` |
| `hardware` | `uart` | `/items/17/source/line` | `297` | `316` |
| `telemetry_sources` | `tele_pc` | `/rtl_signals/signals/0/line` | `333` | `352` |
| `telemetry_sources` | `tele_instr` | `/rtl_signals/signals/1/line` | `334` | `353` |
| `telemetry_sources` | `tele_halted` | `/rtl_signals/signals/2/line` | `335` | `354` |
| `telemetry_sources` | `tele_guard` | `/rtl_signals/signals/3/line` | `336` | `355` |
| `telemetry_sources` | `tele_cycles` | `/rtl_signals/signals/4/line` | `337` | `356` |
| `telemetry_sources` | `tele_flags` | `/rtl_signals/signals/5/line` | `338` | `357` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/source/line` | `286` | `305` |
| `hardware_provenance` | `6.1:uart` | `/claims/17/source/line` | `297` | `316` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/claim` | `tele_pc = port rtl/fpga/gowin/hcpu_gowin_top.v:333` | `tele_pc = port rtl/fpga/gowin/hcpu_gowin_top.v:352` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/source/line` | `333` | `352` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/claim` | `tele_instr = port rtl/fpga/gowin/hcpu_gowin_top.v:334` | `tele_instr = port rtl/fpga/gowin/hcpu_gowin_top.v:353` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/source/line` | `334` | `353` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/claim` | `tele_halted = port rtl/fpga/gowin/hcpu_gowin_top.v:335` | `tele_halted = port rtl/fpga/gowin/hcpu_gowin_top.v:354` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/source/line` | `335` | `354` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/claim` | `tele_guard = port rtl/fpga/gowin/hcpu_gowin_top.v:336` | `tele_guard = port rtl/fpga/gowin/hcpu_gowin_top.v:355` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/source/line` | `336` | `355` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/claim` | `tele_cycles = port rtl/fpga/gowin/hcpu_gowin_top.v:337` | `tele_cycles = port rtl/fpga/gowin/hcpu_gowin_top.v:356` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/source/line` | `337` | `356` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/claim` | `tele_flags = port rtl/fpga/gowin/hcpu_gowin_top.v:338` | `tele_flags = port rtl/fpga/gowin/hcpu_gowin_top.v:357` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/source/line` | `338` | `357` |

## hcpu_gowin_top.v — angka place-and-route Paket 8

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `f9c8349` · bukti kesetaraan **remeasured-header**, sidik jari `c9fdd83e97fe…`, laporan `9fcd5714b007…`

Paket 8 (`f9c8349`) mengukur ulang slot HCPU (`USE_DSP=0`, `CODEX_PROFILE=2`: squarer nibble 1 siklus untuk `HNRM2`/`HDIST` dan `HDOT` 14 siklus) dengan `make -C rtl/fpga/gowin bitstream` pada Tang Nano 20K (`GW2AR-LV18QN88C8/I7`): LUT4 15.744 → 15.453 (baris 47 → 48), DFF 5.065 → 5.166 (baris 48 → 49), BSRAM tetap 18 / 46 (baris 49 → 50), dan Fmax pasca-routing 86.18 → 120.63 MHz (baris 52 → 53). Klaim tetap berkelas `SIMULATED` (`PNR/build-derived`, K-18), terpisah dari bukti fisik papan Stage B dan Stage C di `cosmictera-build/PAPAN.md`.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_lut4` | `/items/3/source/line` | `47` | `48` |
| `hardware` | `fpga_lut4` | `/items/3/value` | `15,744 / 20,736` | `15,453 / 20,736` |
| `hardware` | `fpga_dff` | `/items/4/source/line` | `48` | `49` |
| `hardware` | `fpga_dff` | `/items/4/value` | `5,065 / 15,552` | `5,166 / 15,552` |
| `hardware` | `fpga_bsram` | `/items/5/source/line` | `49` | `50` |
| `hardware` | `fpga_fmax` | `/items/6/source/line` | `52` | `53` |
| `hardware` | `fpga_fmax` | `/items/6/value` | `86.18 MHz` | `120.63 MHz` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/claim` | `sumber daya FPGA = 15,744 / 20,736` | `sumber daya FPGA = 15,453 / 20,736` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/source/line` | `47` | `48` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/claim` | `sumber daya FPGA = 5,065 / 15,552` | `sumber daya FPGA = 5,166 / 15,552` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/source/line` | `48` | `49` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/source/line` | `49` | `50` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/claim` | `sumber daya FPGA = 86.18 MHz` | `sumber daya FPGA = 120.63 MHz` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/source/line` | `52` | `53` |

## hcpu_pkg.vh — CTHETA=0x4E dan HDOT=0x52

`rtl/hcpu_pkg.vh` · penyebab `1aed5e1` · bukti kesetaraan **claim-unchanged**, klaim `isa_rtl` · melanjutkan entri **hcpu_pkg.vh — alternatif RTL A1–A3 (P6)**

1aed5e1 memisahkan slot opcode publik `OP_CTHETA` (`8'h4E`, ekstraksi Theta 1 siklus) dan `OP_HDOT` (`8'h52`, produk titik 14-komponen via `ALU_HDOT`) dalam format heksadesimal kanonik di `rtl/hcpu_pkg.vh`. Ukuran berkas bergeser 21.408 → 21.477 byte; seluruh definisi opcode beku tetap utuh dan terverifikasi terhadap 84 opcode di `RTL_IMPLEMENTED`.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `isa_rtl` | `/items/9/evidence/1/sha256` | `2e0c3df26eb5…` | `7422d98c4e01…` |
| `hardware_provenance` | `6.1:isa_rtl` | `/claims/9/evidence_bytes` | `21408` | `21477` |
| `hardware_provenance` | `6.1:isa_rtl` | `/claims/9/evidence_sha256` | `2e0c3df26eb5…` | `7422d98c4e01…` |

## teknologi/README.md — sensus 84 opcode RTL

`teknologi/README.md` · penyebab `1aed5e1` · bukti kesetaraan **claim-unchanged**, klaim `isa_rtl`

1aed5e1 memperbarui baris inventaris `Opcode H-ISA` pada `teknologi/README.md` baris 34 dari `82` menjadi `84` untuk mencerminkan 84 opcode perangkat keras di `rtl/hcpu_pkg.vh` dan `RTL_IMPLEMENTED` sesudah pemisahan `CTHETA = 0x4E` dan `HDOT = 0x52`.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `isa_rtl` | `/items/9/value` | `82` | `84` |
| `hardware` | `isa_rtl` | `/items/9/source/sha256` | `960f357c1436…` | `6c8a721921bc…` |
| `hardware` | `isa_rtl` | `/items/9/evidence/0/sha256` | `960f357c1436…` | `6c8a721921bc…` |
| `hardware_provenance` | `6.1:isa_rtl` | `/claims/9/claim` | `H-ISA = 82` | `H-ISA = 84` |

## hcpu_gowin_top.v — cap ulang pasca-1aed5e1f

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `95623b6` · bukti kesetaraan **comment-only** · melanjutkan entri **hcpu_gowin_top.v — cap ulang Paket 8**

95623b6 mencap ulang kepala `rtl/fpga/gowin/hcpu_gowin_top.v` sesudah place-and-route pasca-`1aed5e1f` (`CTHETA=0x4E`, `HDOT=0x52`, dan `GAP-02` di `hcpu_hisab.v`): komentar kepala diperbarui untuk mencatat hasil pengukuran baru dan sidik jari `a866810782d7…`, sementara seluruh baris kode Verilog di dalam berkas ini tetap identik (`comment-only`, 35.688 → 35.764 byte).

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_lut4` | `/items/3/source/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_lut4` | `/items/3/evidence/0/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_dff` | `/items/4/source/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_dff` | `/items/4/evidence/0/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_bsram` | `/items/5/source/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_bsram` | `/items/5/evidence/0/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_fmax` | `/items/6/source/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `fpga_fmax` | `/items/6/evidence/0/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `clock_pll` | `/items/14/source/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `clock_pll` | `/items/14/evidence/0/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware` | `uart` | `/items/17/source/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `telemetry_sources` | — | `/rtl_signals/sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.1:fpga_dff` | `/claims/4/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.1:fpga_bsram` | `/claims/5/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.1:clock_pll` | `/claims/14/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.2:tele_pc` | `/claims/61/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.2:tele_instr` | `/claims/62/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.2:tele_halted` | `/claims/63/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.2:tele_guard` | `/claims/64/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.2:tele_cycles` | `/claims/65/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/evidence_bytes` | `35688` | `35764` |
| `hardware_provenance` | `6.2:tele_flags` | `/claims/66/evidence_sha256` | `7e42e6890d25…` | `6c521441c8e9…` |

## hcpu_gowin_top.v — angka place-and-route pasca-1aed5e1f

`rtl/fpga/gowin/hcpu_gowin_top.v` · penyebab `95623b6` · bukti kesetaraan **remeasured-header**, sidik jari `a866810782d7…`, laporan `b7ea812862a8…` · melanjutkan entri **hcpu_gowin_top.v — angka place-and-route Paket 8**

95623b6 mengukur ulang slot HCPU pasca-`1aed5e1f` (`CTHETA=0x4E`, `HDOT=0x52`, dan `GAP-02` di `hcpu_hisab.v`) dengan `make -C rtl/fpga/gowin bitstream` pada Tang Nano 20K (`GW2AR-LV18QN88C8/I7`): LUT4 15.453 → 15.367 (baris 48), DFF tetap 5.166 / 15.552 (baris 49), BSRAM tetap 18 / 46 (baris 50), dan Fmax pasca-routing 120.63 → 54.86 MHz (baris 53). Klaim tetap berkelas `SIMULATED` (`PNR/build-derived`, K-18).

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_lut4` | `/items/3/value` | `15,453 / 20,736` | `15,367 / 20,736` |
| `hardware` | `fpga_fmax` | `/items/6/value` | `120.63 MHz` | `54.86 MHz` |
| `hardware_provenance` | `6.1:fpga_lut4` | `/claims/3/claim` | `sumber daya FPGA = 15,453 / 20,736` | `sumber daya FPGA = 15,367 / 20,736` |
| `hardware_provenance` | `6.1:fpga_fmax` | `/claims/6/claim` | `sumber daya FPGA = 120.63 MHz` | `sumber daya FPGA = 54.86 MHz` |

## NUI/layer4_freeze.json — sensus 105 opcode (CTHETA dan HDOT)

`NUI/layer4_freeze.json` · penyebab `95623b6` · bukti kesetaraan **claim-unchanged**, klaim `isa_board`, `isa_board_unknown`, `bitstream_last_measured`

95623b6 memperbarui `NUI/layer4_freeze.json` sesudah pemisahan `CTHETA=0x4E` dan `HDOT=0x52` pada `1aed5e1f` (`status.opcodes.UNKNOWN` 29 → 31, `opcodes_no_sent_program_executes` 12 → 14), sementara `status.opcodes.PARITY = 74`, bukti rekaman papan P0–P6, dan `bitstream_sha256 = 84fdc912…` tetap identik.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `isa_board` | `/items/10/source/sha256` | `86d8e241d314…` | `1cdf31cd3579…` |
| `hardware` | `isa_board` | `/items/10/evidence/0/sha256` | `86d8e241d314…` | `1cdf31cd3579…` |
| `hardware` | `isa_board_unknown` | `/items/11/evidence/0/sha256` | `86d8e241d314…` | `1cdf31cd3579…` |
| `hardware` | `bitstream_last_measured` | `/items/27/source/sha256` | `86d8e241d314…` | `1cdf31cd3579…` |
| `hardware` | `bitstream_last_measured` | `/items/27/evidence/0/sha256` | `86d8e241d314…` | `1cdf31cd3579…` |

## Makefile — Opsi A HDMI tanpa -nodsp

`rtl/fpga/gowin/Makefile` · penyebab `73fc457` · bukti kesetaraan **insert-only** · melanjutkan entri **Makefile — lapis 3 slot UART Ka'bah**

73fc457 menambahkan satu baris override khusus-target `hdmi_synth: YOSYS_FLAGS =` (beserta satu baris komentar penjelasan) di atas `hdmi_synth` supaya sintesis wrapper HDMI Opsi A berjalan tanpa `-nodsp` (`USE_DSP=1`), tanpa mengubah `YOSYS_FLAGS ?= -nodsp` untuk target lain — 2 baris ditambahkan, tidak ada baris yang dihapus atau diubah. Baris 24 dan 25 yang dibaca `fpga_device` dan `fpga_family` tidak berubah dan tidak bergeser; yang berubah hash utuh berkasnya.

| catatan | butir | pointer | lama | sekarang |
|---|---|---|---|---|
| `hardware` | `fpga_device` | `/items/1/source/sha256` | `7a2b150d6247…` | `282ed72d9018…` |
| `hardware` | `fpga_device` | `/items/1/evidence/0/sha256` | `7a2b150d6247…` | `282ed72d9018…` |
| `hardware` | `fpga_family` | `/items/2/source/sha256` | `7a2b150d6247…` | `282ed72d9018…` |
| `hardware` | `fpga_family` | `/items/2/evidence/0/sha256` | `7a2b150d6247…` | `282ed72d9018…` |

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_addendum --verify
```
