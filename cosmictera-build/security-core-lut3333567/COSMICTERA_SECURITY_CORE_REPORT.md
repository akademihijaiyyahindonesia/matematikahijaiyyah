# LAPORAN ENGINEERING: COSMICTERA SECURITY CORE (ARSITEKTUR LUT `3 – 3 – 3 – 3 – 5 – 6 – 7`)

**Tanggal:** 14 April 2026  
**Target Perangkat Keras:** GOWIN `GW2AR-LV18QN88C8/I7` (Tang Nano 20K)  
**Direktori Kerja Terisolasi:** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/security-core-lut3333567/`  
**Status Modul Eksisting (`rtl/` & `portal8888/rtl/`):** Tidak dimodifikasi (`0` perubahan pada berkas sumber Ka'bah maupun Portal 8888)  
**Status Verifikasi Testbench:** **266 / 266 PASS (`0` error)**  
**Status Sintesis Yosys (`synth_gowin`):** **TERVERIFIKASI (`18` unit LUT4 ekuivalen tepat sesuai spesifikasi UG288)**

## 1. Ringkasan Eksekutif

Prototipe **COSMICTERA Security Core** (`cosmictera_security_core.v`) telah selesai dirancang, diintegrasikan, diverifikasi secara menyeluruh dengan simulator Icarus Verilog (`266/266` pengujian lulus), dan disintesis menggunakan Yosys (`synth_gowin -family gw2a`). Arsitektur pengendali keamanan menerapkan hierarki tujuh fungsi LUT kaskade dengan ukuran input **`3 – 3 – 3 – 3 – 5 – 6 – 7`** yang mengoordinasikan empat subsistem kriptografi utama:

1. **Portal 8888 (`hijaiyyah_portal8888.v`)** — Akuisisi frame PHY, parser header L2/L3/L4 (`ingress_parse_v1.v`), disiplin waktu UTC/GPS-PPS (`hijaiyyah_timestamp.v`), SHA-256 frame streaming (`hijaiyyah_sha256_stream.v`), dan penyegelan rantai per-port (`sealed_body` 125 byte / 1000 bit beserta `sealed_tag` 256 bit).
2. **Ka'bah Cryptographic Engine (`hijaiyyah_kabah_top.v` & `hijaiyyah_sponge.v`)** — Deserialiser bit-ke-byte (`hijaiyyah_deserialiser.v`), sponge 1600-bit dengan rate 25 byte (200 bit) dan 24 putaran permutasi (`hijaiyyah_rotate_core.v`, `hijaiyyah_sbox_router.v`, `hijaiyyah_linear.v`), serta pembangkit impuls Ramal 28 langkah (`hijaiyyah_ramal_impulse.v`).
3. **Layer-3 HMAC-SHA256 (`hijaiyyah_hmac.v`)** — Mesin verifikasi autentikasi pesan berbasis kunci 512-bit dan tag 256-bit.
4. **Jamrah 7-Node Gate (`hijaiyyah_jamrah_gate.v`)** — Gerbang kombinatorial 7 simpul (`node0..node6`, `root`, `pulse`) yang memvalidasi alfabet Hijaiyyah (`1..28`).

## 2. Tahap 1 — Pemetaan Sinyal Nyata terhadap Tujuh Blok LUT (`3 – 3 – 3 – 3 – 5 – 6 – 7`)

Hasil pemeriksaan RTL pada repositori menunjukkan pemetaan langsung antara sinyal perangkat keras nyata dan ketujuh fungsi LUT sebagai berikut:

| Blok LUT | Ukuran Input | Modul RTL | Persamaan Logika | Sinyal Kandidat Nyata pada `cosmictera_security_core.v` |
| :--- | :---: | :--- | :--- | :--- |
| **LUT3-A** | 3 | `cosmictera_lut3_a_frame_ok` | `frame_ok = frame_sync & version_ok & length_ok` | `frame_sync = record_latched & ~overflow_fault_latched & ~dropped_fault_latched`<br>`version_ok = (rec_ver == 4'd4) \|\| (rec_ver == 4'd6)`<br>`length_ok = (rec_status == 2'b00)` |
| **LUT3-B** | 3 | `cosmictera_lut3_b_request_fresh` | `request_fresh = timestamp_ok & nonce_fresh & sequence_ok` | `timestamp_ok = (rec_tsec >= min_utc_sec) && (rec_uncert <= max_uncert_ns)`<br>`nonce_fresh = (rec_ctr > last_accepted_ctr)`<br>`sequence_ok = (rec_idx == expected_port_idx[rec_port])` |
| **LUT3-C** | 3 | `cosmictera_lut3_c_key_enable` | `key_enable = auth_job_active & key_slot_valid & secure_mode` | `auth_job_active = (core_state == ST_DISPATCH \|\| ST_AUTH_RUN \|\| ST_DECIDE)`<br>`key_slot_valid = portal_provisioned && portal_provision_written[active_key_slot]`<br>`secure_mode = portal_provision_locked && secure_mode_en && ~security_abort` |
| **LUT3-D** | 3 | `cosmictera_lut3_d_hmac_pass` | `hmac_pass = hmac_done & digest_equal & ~hmac_error` | `hmac_done = verify_hmac_done_latched`<br>`digest_equal = (verify_hmac_mac_latched == expected_tag_mux)`<br>`hmac_error = hmac_fault_latched` |
| **LUT5** | 5 | `cosmictera_lut5_request_start` | `request_start = request_available & frame_ok & request_fresh & hmac_ready & kabah_ready` | `request_available = record_latched && (core_state == ST_EVAL_PRE)`<br>`frame_ok` (keluaran `LUT3-A`)<br>`request_fresh` (keluaran `LUT3-B`)<br>`hmac_ready = verify_hmac_idle`<br>`kabah_ready = ~kabah_permuting && kabah_bits_ready` |
| **LUT6** | 6 | `cosmictera_lut6_kabah_round_step` | `kabah_round_step = kabah_busy & state_valid & round_valid & step_enable & ~abort & reset_n` | `kabah_busy = (core_state == ST_AUTH_RUN) && ~kabah_done_latched`<br>`state_valid = kabah_state_seeded`<br>`round_valid = (kabah_step_cnt < 6'd25)`<br>`step_enable = kabah_step_en`<br>`abort = security_abort \|\| kabah_break_latched`<br>`reset_n = rst_n` |
| **LUT7** | 7 | `cosmictera_lut7_auth_grant` | `auth_grant = frame_ok & request_fresh & hmac_pass & kabah_verify_ok & jamrah_pass & privilege_ok & security_state_ok` | `frame_ok` (`LUT3-A`), `request_fresh` (`LUT3-B`), `hmac_pass` (`LUT3-D`)<br>`kabah_verify_ok = kabah_done_latched && (\|kabah_out_state[255:0]) && ~kabah_break_latched`<br>`jamrah_pass = ~jamrah_violation && ~kabah_break_latched`<br>`privilege_ok = privilege_req_ok && (rec_dport == 16'd8888 \|\| rec_dport == 16'd0)`<br>`security_state_ok = lut3_c_key_enable && (core_state == ST_DECIDE) && ~fault` |

### Jaminan Isolasi Kunci Internal (`LUT3-C`)

Sesuai prinsip keamanan yang ditetapkan:
- Memori kunci (`protected_key_vault`, 5 slot × 512 bit) bersifat **write-only** saat fase provisioning sebelum `prov_lock` dikunci.
- **Tidak ada** port keluaran modul, jalur debug, maupun register MMIO yang dapat membaca isi kunci keluar dari `cosmictera_security_core`.
- Sinyal `lut3_c_key_enable` hanya mengizinkan pengiriman kunci secara internal ke port `.key(gated_hmac_key)` pada `hijaiyyah_hmac` melalui gerbang `gated_hmac_key = lut3_c_key_enable ? protected_key_vault[active_key_slot] : 512'd0`.

## 3. Tahap 2 & 3 — Hasil Verifikasi Simulasi RTL (`266 / 266 PASS`)

Testbench `tb/tb_cosmictera_security_core.v` menguji dua kelompok verifikasi:

### A. Verifikasi Tabel Kebenaran Menyeluruh (256 Vektor pada 7 Blok LUT)

| Blok LUT | Jumlah Kombinasi Uji | Hasil | Keterangan |
| :--- | :---: | :---: | :--- |
| `LUT3-A` (`frame_ok`) | $2^3 = 8$ vektor | **8 / 8 PASS** | Hanya bernilai `1` saat `frame_sync=1, version_ok=1, length_ok=1` |
| `LUT3-B` (`request_fresh`) | $2^3 = 8$ vektor | **8 / 8 PASS** | Hanya bernilai `1` saat `timestamp_ok=1, nonce_fresh=1, sequence_ok=1` |
| `LUT3-C` (`key_enable`) | $2^3 = 8$ vektor | **8 / 8 PASS** | Hanya bernilai `1` saat `auth_job_active=1, key_slot_valid=1, secure_mode=1` |
| `LUT3-D` (`hmac_pass`) | $2^3 = 8$ vektor | **8 / 8 PASS** | Hanya bernilai `1` saat `hmac_done=1, digest_equal=1, hmac_error=0` |
| `LUT5` (`request_start`) | $2^5 = 32$ vektor | **32 / 32 PASS** | Menguji seluruh kombinasi 5 input dispatch Portal 8888 |
| `LUT6` (`kabah_round_step`) | $2^6 = 64$ vektor | **64 / 64 PASS** | Menguji seluruh kombinasi 6 input kendali putaran Ka'bah (`abort=0, reset_n=1`) |
| `LUT7` (`auth_grant`) | $2^7 = 128$ vektor | **128 / 128 PASS** | Menguji seluruh kombinasi 7 input keputusan autentikasi akhir |
| **Total Tabel Kebenaran** | **256 vektor** | **256 / 256 PASS** | **0 kesalahan logika** |

### B. Verifikasi Skenario Keamanan End-to-End (S1 – S9)

| Skenario | Kondisi Pengujian | Respons LUT | Keputusan Akhir (`AUTH_OK`, `REJECT`, `ERROR`) | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Init Vault** | Provisioning 5×64B key slots + `prov_lock` + GPS PPS | `portal_provisioned=1`, `portal_ready=1` | Siap menerima frame | **PASS** |
| **S1 — Valid Request** | Paket IPv4/UDP valid ke port `8888` + payload Hijaiyyah `1..28` | `LUT3-A..D=1`, `LUT5=1`, `LUT6=1`, `LUT7=1` | `AUTH_OK=1, REJECT=0, ERROR=0` | **PASS** |
| **S2 — Frame Rusak** | Frame Ethernet terpotong (10 byte, `TRUNC`) | `LUT3-A=0`, `LUT5=0`, `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=0` | **PASS** |
| **S3 — Replay / Timestamp Kedaluwarsa** | `rec_tsec < min_utc_sec` (uji anti-replay/stale timestamp) | `LUT3-B=0`, `LUT5=0`, `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=0` | **PASS** |
| **S4 — Akses Kunci Diblokir** | `secure_mode_en=0` sehingga kunci internal dipaksa `0` | `LUT3-C=0`, `LUT3-D=0`, `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=1` | **PASS** |
| **S5 — Pemalsuan Tag HMAC** | Tag HMAC 256-bit tidak cocok dengan hasil `hijaiyyah_hmac` | `LUT3-D=0`, `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=0` | **PASS** |
| **S6 — Pelanggaran Gerbang Jamrah** | Karakter di luar alfabet Hijaiyyah (`byte=29 > 28`) pada `gate_mode=1` | `jamrah_pass=0`, `kabah_break_valid=1`, `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=1` | **PASS** |
| **S7 — Pelanggaran Hak Akses (Privilege)** | Paket valid tetapi menuju port UDP `9999 != 8888` | `LUT3-A..D=1`, `privilege_ok=0`, `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=0` | **PASS** |
| **S8 — Abort Mesin Ka'bah** | Sinyal `security_abort=1` di tengah pemrosesan sponge 1600-bit | `LUT6=0` (langkah sponge berhenti), `LUT7=0` | `AUTH_OK=0, REJECT=1, ERROR=1` | **PASS** |
| **S9 — Pemulihan Pasca-Fault** | Paket valid berikutnya pada Port 2 setelah kondisi fault S8 | `LUT3-A..D=1`, `LUT5=1`, `LUT6=1`, `LUT7=1` | `AUTH_OK=1, REJECT=0, ERROR=0` | **PASS** |

## 4. Tahap 4 — Hasil Sintesis Yosys (`synth_gowin`) pada Arsitektur CFU Gowin GW2AR-18

Sintesis dilakukan dengan `synth_gowin -top cosmictera_security_lut_plane -family gw2a` (`synth/yosys_lut_plane_hier.log`). Hasil pemetaan aktual Yosys membuktikan kesesuaian eksak dengan spesifikasi arsitektur Configurable Function Unit (CFU) GOWIN UG288:

| Blok Fungsi | Modul RTL | Sel Primitif Hasil Sintesis Yosys (`synth_gowin`) | Unit LUT4 Ekuivalen (Teori UG288) | Unit LUT4 Ekuivalen (Aktual Yosys) | Struktur CLS Gowin |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **LUT3-A** | `cosmictera_lut3_a_frame_ok` | `1 × LUT3` | 1 | **1** | 0,5 CLS |
| **LUT3-B** | `cosmictera_lut3_b_request_fresh` | `1 × LUT3` | 1 | **1** | 0,5 CLS |
| **LUT3-C** | `cosmictera_lut3_c_key_enable` | `1 × LUT3` | 1 | **1** | 0,5 CLS |
| **LUT3-D** | `cosmictera_lut3_d_hmac_pass` | `1 × LUT3` | 1 | **1** | 0,5 CLS |
| **LUT5** | `cosmictera_lut5_request_start` | `1 × LUT1 + 1 × LUT4 + 1 × MUX2_LUT5` | 2 | **2** | 1 CLS |
| **LUT6** | `cosmictera_lut6_kabah_round_step` | `3 × LUT1 + 1 × LUT4 + 2 × MUX2_LUT5 + 1 × MUX2_LUT6` | 4 | **4** | 2 CLS |
| **LUT7** | `cosmictera_lut7_auth_grant` | `7 × LUT1 + 1 × LUT4 + 4 × MUX2_LUT5 + 2 × MUX2_LUT6 + 1 × MUX2_LUT7` | 8 | **8** | 4 CLS |
| **Total 7 Blok** | `cosmictera_security_lut_plane` | **`11 LUT1 + 4 LUT3 + 3 LUT4` + `7 MUX2_LUT5 + 3 MUX2_LUT6 + 1 MUX2_LUT7`** | **18 LUT4** | **18 LUT4** (`0,087%` dari 20.736) | **9 CLS** |

## 5. Daftar Berkas Artefak

- **RTL Wrapper & 7-LUT Control Plane:** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/security-core-lut3333567/rtl/cosmictera_security_core.v`
- **Testbench Verifikasi (266 Pengujian):** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/security-core-lut3333567/tb/tb_cosmictera_security_core.v`
- **Log Simulasi RTL:** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/security-core-lut3333567/logs/tb_cosmictera_security_core.log`
- **Log Sintesis Yosys 7-LUT Plane:** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/security-core-lut3333567/synth/yosys_lut_plane_hier.log`
- **Log Sintesis Yosys Full Security Core:** `/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/security-core-lut3333567/synth/yosys_security_core_full.log`
