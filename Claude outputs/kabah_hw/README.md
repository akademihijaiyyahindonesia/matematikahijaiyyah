# Celah 3 Ka'bah: HMAC-SHA256 di perangkat keras

Paket ini **belum masuk repositori**. Nama berkas di sini masih sementara dan
menunggu keputusan pemilik (aturan penamaan `AGENTS.md` §2). Dibangun
1 Oktober 2026 di sandbox cloud dengan oss-cad-suite 2026-09-30 (Yosys
0.69+158, Icarus 14.0-devel, nextpnr-himbaechel, gowin_pack).

## Isi

| berkas | fungsi |
|---|---|
| `rtl/sha256_core.v` | kompresi SHA-256 (FIPS 180-4), 1 ronde/clock, 66 clock/blok |
| `rtl/sha256_stream.v` | aliran byte → blok, padding + panjang; opsi blok prefiks untuk HMAC |
| `rtl/hmac_sha256.v` | HMAC-SHA256 (RFC 2104 / FIPS 198-1), kunci ≤ 64 byte |
| `rtl/hmac_gowin_top.v` | wrapper papan Tang Nano 20K, 10 pin, UART 115200 |
| `tb/*.v`, `vec/*.py` | testbench dan pembangkit vektor |
| `scripts/hmac_uart_test.py` | uji papan: hasil papan dibandingkan dengan `signing.sign_bytes` |
| `build/hmac_gowin_top.fs` | bitstream siap muat |

## Hasil terukur (simulasi, sebelum papan)

| uji | hasil |
|---|---|
| `sha256_stream`: vektor NIST FIPS 180-4 (kosong, "abc", 448-bit, 896-bit), semua panjang 0–129 byte, 20 panjang acak sampai 999, dan satu juta 'a' | **155 PASS, 0 FAIL** |
| `hmac_sha256`: RFC 4231 kasus 1–7 dan 60 kunci/pesan acak, ditambah uji kesamaan waktu | **68 PASS, 0 FAIL** |
| `hmac_gowin_top` lewat pin UART (27 MHz, 115200 baud nyata): RFC 4231 1–7 dan 3 acak | **10 PASS, 0 FAIL** |
| Lint Verilator `-Wall` | bersih |
| Waktu tidak bergantung data: 100 byte berisi nol vs 100 byte berisi 0xFF, kunci nol vs kunci 0xFF | **525 = 525 clock** |

Biaya waktu mesin:
- SHA-256: 66 clock per blok 64 byte, sekitar 26 MB/s pada 27 MHz untuk kompresinya saja.
- HMAC pesan ≤ 55 byte: 392 clock, sekitar 14,5 µs pada 27 MHz.

## Sintesis dan place-and-route (GW2AR-LV18QN88C8/I7, `synth_gowin -nodsp`, cst `hcpu_gowin.cst`)

| | terpakai / kapasitas | % |
|---|---:|---:|
| IOB | 10 / 384 | 2% |
| LUT4 | 5.158 / 20.736 | 24% |
| DFF | 3.603 / 15.552 | 23% |
| ALU | 594 / 15.552 | 3% |
| BSRAM | 0 / 46 | 0% |

**Fmax belum boleh dikutip.** nextpnr melaporkan 106,50 MHz setelah placement
dan 199,60 MHz setelah routing. Tapi jalur kritis yang dilaporkan sesudah
routing adalah jalur kendali (enable LED), bukan jalur data ronde SHA-256.
Artinya pemodelan timing rantai carry ALU patut dicurigai. Yang aman
disimpulkan hanya ini: kedua angka jauh di atas 27 MHz tempat papan berjalan.

## Uji di papan (dijalankan pemilik atau agen VS Code di Mac)

```sh
openFPGALoader -b tangnano20k -m build/hmac_gowin_top.fs   # -m = SRAM, hilang saat mati daya
python3 scripts/hmac_uart_test.py /dev/tty.usbserial-XXXX --random 200
```

Lulus jika baris terakhir berbunyi `RESULT: 207 PASS, 0 FAIL, of 207`.

Ini uji laboratorium yang dijalankan manusia, bukan tindakan otonom NUI
Lapis 7. Tabel 7.4 tidak tersentuh.

## Yang belum

- Bitstream ini dibangun dengan toolchain cloud, bukan toolchain terpatok
  repositori di Mac. Untuk evidence tingkat repositori: masukkan ke Makefile
  sebagai target sendiri, lalu bangun ulang di Mac.
- Kunci lebih dari 64 byte di-hash lebih dulu oleh host (RFC 2104). RTL tidak
  melakukannya.
- Belum dihubungkan ke HCPU (MMIO). Wrapper ini berdiri sendiri, seperti
  wrapper Ka'bah.
