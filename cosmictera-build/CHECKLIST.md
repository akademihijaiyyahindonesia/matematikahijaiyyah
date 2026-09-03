# Daftar cek

Setiap ✅ di bawah ini **dijalankan**, bukan diingat. Kolom terakhir adalah
perintahnya: salin, jalankan, dan Anda mendapat centang yang sama atau tahu
persis apa yang berubah.

Sebuah baris hanya boleh hijau kalau ada pemeriksaan otomatis yang lulus
**sekarang**. Tidak ada centang untuk "sudah ditulis", "pernah jalan", atau
"tinggal sedikit lagi".

---

## Perkakas

| | apa | perintah |
|---|---|---|
| ✅ | Python, pytest, ruff, mypy | `python3 -m pytest --version` |
| ✅ | Icarus Verilog | `iverilog -V` |
| ✅ | yosys | `yosys -V` |
| ✅ | nextpnr-himbaechel | `nextpnr-himbaechel --version` |
| ✅ | gowin_pack | `gowin_pack --help` |
| ✅ | openFPGALoader | `openFPGALoader --Version` |

Kelimanya terpasang di `~/opt/oss-cad-suite`. Satu perintah memeriksa semuanya:
`make -C rtl/fpga/gowin tools`.

---

## Kebersihan pohon

| | apa | perintah |
|---|---|---|
| ✅ | **4.300 tes lulus**, 4 dilewati † | `python3 -m pytest -q` |
| ✅ | ruff bersih | `make lint` |
| ✅ | mypy bersih, 108 berkas | `make typecheck` |
| ✅ | Master Table utuh | `make verify` |
| ✅ | Citra ROM terbangkitkan | `make rom` |
| ✅ | ROM cocok dengan tabel | `python3 rtl/scripts/cross_verify_rom.py` |
| ✅ | Suite deterministik | 40 jalan berturut `test_memscan`, 0 gagal |

† Satu-satunya angka di halaman ini yang **tidak dijaga**. Cacah bench dan
asersi dibaca ulang dari Makefile oleh
[`test_build_list.py`](../tests/test_integrity/test_build_list.py), tapi cacah
pytest tidak bisa diperiksa tanpa menjalankan pytest di dalam pytest. Ia
cuplikan 3 September 2026; perintah di sebelahnya yang menjadi kebenarannya.

Baris terakhir bukan hiasan. `test_every_clue_is_distinctive_enough_to_be_worth_having`
mengambil `os.urandom` lalu menuntut penanda tidak muncul di dalamnya — dua
penanda panjangnya 3 byte, jadi suite gagal kira-kira **1 dari 127 jalan**.
Berkas itu sendiri sudah menulis pelajarannya satu fungsi di atasnya. Sekarang
sifatnya diasersi secara aritmetika dan deraunya berbenih.

---

## Perangkat keras — simulasi

| | apa | perintah |
|---|---|---|
| ✅ | **232 asersi, 15 bench, 0 gagal** | `make -C rtl/tb all` |
| ✅ | ROM 28 huruf | `make -C rtl/tb sim_rom` |
| ✅ | Guard G1–G4, T1–T2 | `make -C rtl/tb sim_guard` |
| ✅ | Codex ALU | `make -C rtl/tb sim_codex_alu` |
| ✅ | HISAB, sapuan 28 huruf | `make -C rtl/tb sim_hisab` |
| ✅ | Integrasi top-level | `make -C rtl/tb sim_top` |
| ✅ | Unit trap, 6 penyebab | `make -C rtl/tb sim_trap` |
| ✅ | MMIO, timer, UART RX | `make -C rtl/tb sim_mmio sim_timer sim_uart_rx` |
| ✅ | **H-Kernel: dua proses** | `make -C rtl/tb sim_kernel` |
| ✅ | **28 instruksi huruf** | `make -C rtl/tb sim_letters` |
| ✅ | **`CALL`/`RET`, sarang 8 tingkat** | `make -C rtl/tb sim_subroutine` |
| ✅ | **I/O lewat kernel, dua sisi** | `make -C rtl/tb sim_syscall_io` |
| ✅ | Wrapper papan | `make -C rtl/tb sim_board` |
| ✅ | Boot lewat kabel | `make -C rtl/tb sim_loader` |

Dua baris tebal itu baru hijau **hari ini**, dan keduanya sempat berbohong:

- **H-Kernel** hijau karena `B = 127400 = 1274 × 100`. Kelipatan yang bersih
  hanya mungkin bila R1 milik B tak pernah memegang nilai A.
- **Instruksi huruf** hijau karena `||Ba+Sin+Mim||² = 112` lewat jalur huruf —
  angka yang sama yang sudah dibuktikan jalur HLOAD/HCADD. Sebelum hari ini
  jawabannya **0**: `default:` kedua di tengah `case` membuat kedua puluh
  delapan opcode menulis nol, dan tak ada bench yang pernah menjalankan satu
  pun. Enam bench di kolom ini juga tidak punya target `make` sama sekali.

---

## Matematika dan angka

| | apa | bukti |
|---|---|---|
| ✅ | 28 huruf kanonik dari PDF bersegel | `make verify` |
| ✅ | Closure monoid dibuktikan, bukan disampel | `tests/test_algebra/` |
| ✅ | Cakupan guard **93,1%**, dan itu langit-langitnya | `matematika-hijaiyyah/GUARD.md` |
| ✅ | Throughput **2,59 MB/s**, hambatan = deserialiser | `src/hijaiyyah/crypto/kabah.py` |
| ✅ | 72 dari 96 opcode di RTL, 24 sisanya dinamai | [OFF.md](OFF.md) |

---

## Belum hijau

Dua, dan keduanya dinamai supaya centang di atas berarti sesuatu.

| | apa | keadaan |
|---|---|---|
| ⬜ | `python3 rtl/scripts/lint_hcpu.py` | **0 error struktural** (dulu 1), sisa **74 peringatan** — keluar bukan-nol |
| 🔴 | `make -C rtl/fpga/gowin bitstream` | **gagal**: 13.948 / 8.640 LUT4 = **161%** |

Error Verilator hilang justru karena `default:` ganda itu diperbaiki — jadi
lint yang selama ini merah sebenarnya sedang menunjuk cacat huruf, dan tak ada
yang membacanya. Peringatan yang tersisa soal bit yang tak terpakai.

Bitstream merah, bukan kosong: **papan tidak bisa di-flash dari komit ini.**
Sebabnya satu komit dan sudah dibisect — lihat [OFF.md](OFF.md).

---

## Satu tarikan napas

```bash
make -C rtl/fpga/gowin tools     # 5/5 perkakas
make lint typecheck verify rom   # bersih
python3 -m pytest -q             # 4.300 lulus, 4 dilewati
make -C rtl/tb all               # 232 asersi, 15 bench, 0 gagal
make -C rtl/fpga/gowin bitstream # ← merah, dan memang seharusnya terlihat
```

Perintah terakhir sengaja ikut. Daftar cek yang berhenti sebelum baris merah
bukan daftar cek.
