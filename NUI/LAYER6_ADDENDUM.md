# Adendum pasca-freeze Lapis 6

Dihasilkan `src/hijaiyyah/nui/layer6_addendum.py` dari `NUI/layer6_addendum.json`. Keputusan pemilik, 1 Oktober 2026, sesudah commit HMAC `4bff781` membuat tiga `--verify` Lapis 6 merah oleh drift pasca-freeze yang diharapkan.

> Registry beku tetap immutable; adendum adalah catatan baru. Tiap entri: pointer/hash lama → keadaan sekarang, alasan konkret, commit penyebab, dan evidence kesetaraan. Tidak ada pemetaan massal tanpa alasan. Verifier membaca keduanya: historical freeze ≠ current repository state.

Catatan beku Lapis 6.1–6.3 — model, halaman, dan spec-nya — tetap byte demi byte objek di tag `layer6-freeze-2026-09-29-final`. Adendum ini catatan baru di sampingnya, bukan bangkitan ulang: **freeze historis ≠ keadaan repositori sekarang**. Keadaan sekarang adalah catatan beku dengan perubahan di bawah ini, dan harus sama dengan yang dibangun buktinya hari ini.

**6 entri, 70 perubahan**: `hardware` 23, `telemetry_sources` 8, `hardware_provenance` 39.

## Bukti kesetaraan

- **comment-only** — setiap baris yang bukan baris kosong dan bukan komentar utuh `//` sama dan berurutan sama di berkas beku dan berkas sekarang — aturan yang dipakai sidik jari place and route; yang berubah hanya komentar, jadi desainnya tidak.
- **insert-only** — setiap baris berkas beku masih ada, utuh dan berurutan, di berkas sekarang; barisnya hanya bertambah, tidak ada yang hilang atau diubah.
- **line-moved** — tiap baris yang dikutip punya teks yang sama persis di nomor barunya — di freeze, tepat sebelum penyebab, di penyebab, dan sekarang.
- **row-meaning** — baris kontrak diurai dengan pola baris `NUI/spec/telemetry_sources.json`: medan dan asalnya sama, dan medannya tetap tanpa sumber — jadi statusnya tetap.

## Rantai perubahan

Keputusan pemilik, 5 Oktober 2026, sesudah commit lapis 3 Ka'bah `004b9a0` menambah baris ke `Makefile` yang sudah pernah ditambah `4bff781`: perubahan kedua pada satu berkas tidak diterima karena ia perubahan kedua, melainkan hanya sebagai entri yang menyebut, di `after`, satu entri yang dilanjutkannya — dan tiap mata rantainya diperiksa. Entri yang disebut ditulis lebih dulu dan tentang berkas yang sama; ia dilanjutkan oleh satu entri saja, rantai tidak bercabang; pointer yang diubah persis sama, dan nilai lama di sini adalah nilai baru di sana; commit penyebabnya keturunan commit penyebab entri itu; berkas tepat sebelum penyebabnya ber-hash nilai lamanya, jadi tidak ada yang menyentuh berkas di antara keduanya; dan bukti kesetaraannya sendiri berlaku sejak penyebab entri itu. Entri yang dilanjutkan lalu menjawab untuk berkas di commit penyebabnya saja, dan entri terakhir rantai untuk berkas sekarang. Hanya hash berkas utuh yang berantai (`comment-only`, `insert-only`). Pointer yang diubah dua kali tanpa mata rantai itu tetap ditolak.

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

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_addendum --verify
```
