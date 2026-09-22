# Sesudah burn-in 72 jam — urutan eksekusi

**Disusun 22 September 2026 atas permintaan pemilik**, sementara papan masih
memikul burn-in tingkat 2: *"Dengan begitu Kamis tidak ada keputusan baru di
tengah eksekusi."* Halaman ini perintah, bukan hasil. Tidak satu langkah pun di
bawah sudah dijalankan; yang sudah disiapkan disebut dengan berkasnya.

Burn-in `20260921T053430Z-burn-in-72h` mulai 21 September 2026 05:34:30 UTC,
jadi selesai **24 September 2026 05:34:30 UTC — Kamis 12:34 WIB**. Papan tetap
milik burn-in sampai `burn_in.py` keluar sendiri; `parity_board.py` menolak
berjalan selama prosesnya hidup.

## Keputusan yang harus ada sebelum Kamis

Tiap langkah di bawah bisa berjalan tanpa keputusan baru, **kecuali** yang
disebut di sini. Kalau salah satunya belum dijawab pada hari itu, langkah yang
bergantung padanya ditunda — tidak dijawab sendiri.

| # | keputusan | menyentuh | usulan, bukan keputusan |
|---|---|---|---|
| K-1 | Pengurai `burn_in.py` menerima dua baris tergabung sebagai `error` (t = 11.713 dan 12.686 detik); papan sendiri 0 error. Dibetulkan dulu, atau baseline tingkat 2 ditulis dengan keduanya dicatat sebagai selisih yang diketahui? | P0 | catat sebagai selisih; perbaiki pengurai sesudahnya, lari berikutnya yang memakainya |
| K-2 | Bentuk "freeze" Lapis 4: commit biasa, atau juga tag git? Namanya? | P6 | commit, tanpa tag |
| K-3 | Lokasi Lima dan nama instance VM | P7 | `~/cosmictera-layer5/lima-2.2.0/`, instance `cosmictera` |
| K-4 | Opsi `journalctl` (jumlah baris) dan `ip` untuk jaringan | P7 | bentuk pemilik apa adanya; jaringan lewat `ls`/`cat` |

Yang **tidak** diputuskan di hari itu, dan tidak masuk urutan ini: perbaikan
`PRINT` di silikon dan perbaikan instruksi sesudah berhenti. Keduanya RTL, K9
berlaku, dan pemilik sudah menetapkan urutannya: diverifikasi di papan dulu,
diputuskan sesudahnya.

## P0 — tutup burn-in dan simpan jejaknya

```bash
pgrep -f "rtl/scripts/burn_in.py" || echo "selesai"          # tunggu sampai keluar sendiri
python3 -c "import json; print(json.load(open('cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json'))['ended'])"
shasum -a 256 cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.json*
python3 rtl/scripts/burn_in_report.py cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl --write
python3 rtl/scripts/burn_in_report.py cosmictera-build/burn-in/20260921T053430Z-burn-in-72h.jsonl \
    --against cosmictera-build/burn-in/20260920T013538Z-burn-in-24h-baseline.json
```

Syarat lanjut: `ended` berbunyi `duration reached`. Kalau berbunyi
`STOPPED EARLY`, tingkat 2 **tidak** tutup: sebabnya dicatat, dan keputusan
mengulang milik pemilik. Hasil, hash, dan baseline dicatat di
`cosmictera-build/burn-in/README.md`, lalu di-commit dengan path disebut satu
per satu.

Dua hal yang sudah diketahui dan harus terbaca di laporannya, bukan
mengejutkan: diam ±926 detik antara detik ke-5.591 dan ke-20.725 (Mac tidur
karena lid ditutup, 13:50–18:19 WIB 21 September, dari `pmset -g log`), dan
dua baris `error` dari K-1.

## P1 — paritas papan, seluruh korpus

```bash
python3 rtl/scripts/parity_board.py --experiment parity              # rencana
python3 rtl/scripts/parity_board.py --experiment parity --port /dev/tty.usbserial-20250303171
```

79 dari 103 program dikirim. Yang tidak: 9 menyentuh jendela SD — tidak ada
mesin lain di sini yang punya kartu untuk pembanding — dan 15 tidak berhenti di
bawah loader. Jawaban yang diharapkan **sudah dibekukan** di
`NUI/board_expected.json`; runner menolak payload yang hash-nya tidak sama
dengan yang dibekukan. Rekaman dan laporannya ditulis sendiri ke
`cosmictera-build/parity-board/<UTC>-parity.json` dan `.report.json`.

Lama larinya belum diukur untuk 79 program. Patokan terdekat: lab serangan,
10 kasus dengan dua muat bitstream per kasus, ±1 menit 17 detik.

Aturan hari itu: lari **tidak dihentikan karena MISMATCH** — semua program
dikirim, semua jawaban disimpan. Rekonfigurasi di tengah pembacaan kartu
merusak init kartu berikutnya (OFF.md), tapi tak satu program yang dikirim
menyentuh kartu.

## P2 — kolom perangkat keras per opcode

Keluar dari laporan P1: `opcodes` di `<UTC>-parity.report.json`. Aturannya
ditulis di `src/hijaiyyah/nui/board_parity.py`: PARITY kalau opcode hanya
muncul di program yang cocok, MISMATCH kalau hanya di program yang berbeda,
UNKNOWN kalau di keduanya — kabel saja tidak bisa menunjuk instruksi mana yang
berbeda — atau kalau tak satu program yang dikirim menjalankannya. Kolom itu
lalu dipindah ke `NUI/PARITY.md`.

## P3 — PRINT di silikon

```bash
python3 rtl/scripts/parity_board.py --experiment print --port /dev/tty.usbserial-20250303171
```

Satu program, tangga pemilik: 2²², 2²³, 2²⁴, 2²⁵, 2²⁶, 2²⁷, 2³¹. Laporannya
berisi `ladder`: nilai, Python, interpreter, RTL tersimulasi, papan, dan
`first_divergence`. Yang diharapkan kedua mesin sudah beku — keduanya mencetak
ketujuh nilai dengan benar. Yang dicari **batas pertama**, bukan perbaikan.

## P4 — HALT dan RET di silikon

```bash
python3 rtl/scripts/parity_board.py --experiment stop --port /dev/tty.usbserial-20250303171
```

Lima probe, empat pertanyaan pemilik dan satu kasus HALT yang terlihat di
kabel. RTL tersimulasi sudah menjawab **ya** untuk keempatnya (R1 = 7 sesudah
HALT dan sesudah RET gagal, `MEM[0x100]` = 5 sesudah HALT, `5` di kabel sesudah
RET gagal dan sesudah HALT). Papan hanya bisa menjawab yang lewat kabel:
register dan RAM sesudah berhenti tidak pernah tercetak, dan laporannya
menyebut itu, bukan mengisinya.

## P5 — analisis selisih

Tiap MISMATCH dari P1–P4 dipilah dari laporannya: sudah dikenal
(OFF-PRINT-SILICON, instruksi sesudah berhenti) atau baru. Yang baru jadi butir
OFF.md dengan angkanya. **Tidak ada RTL yang diubah** di langkah ini.

## P6 — bekukan Lapis 4

Rekaman dan laporan P1–P4 di-commit bersama pembaruan `NUI/PARITY.md`,
`NUI/LAYERS.md`, dan `cosmictera-build/PAPAN.md`, dengan empat gerbang hijau
di lari yang sama. Bentuk bekunya K-2.

## P7 — mulai Lapis 5, hanya baca

Yang sudah siap: `NUI/spec/layer5_lima.yaml` (image terverifikasi lewat
digest, tanpa mount, mode plain), `NUI/spec/layer5_collectors.json` (sembilan
kolektor), `src/hijaiyyah/nui/layer5.py` (pagar hanya-baca dan satu jalan keluar
lewat `limactl shell`).

```bash
shasum -a 256 ~/cosmictera-layer5/downloads/lima-2.2.0-Darwin-arm64.tar.gz   # bbdef917...
# pasang di lokasi K-3, lalu:
limactl start --name=cosmictera NUI/spec/layer5_lima.yaml
limactl list
PYTHONPATH=src python3 -m hijaiyyah.nui.layer5                                # rencana
```

Diverifikasi pada `limactl start` pertama, karena belum pernah diukur: Lima
menerima path lokal untuk image, menolak image dengan digest lain, dan
instance berjalan tanpa mount. Sesudah itu baru kolektor dijalankan satu per
satu dan observasinya disimpan.

## Paket audit sesudah P7

| isi | tempat |
|---|---|
| commit dan hasil empat gerbang | pesan commit P6 |
| burn-in 72 jam, hash, baseline | `cosmictera-build/burn-in/` |
| paritas papan dan kolom per opcode | `cosmictera-build/parity-board/*-parity.*` |
| PRINT di silikon | `cosmictera-build/parity-board/*-print.*` |
| HALT/RET di silikon | `cosmictera-build/parity-board/*-stop.*` |
| ekspektasi yang dibekukan sebelum papan ditanya | `NUI/board_expected.json` |
| selisih yang diketahui | `cosmictera-build/OFF.md`, fakta `nui.tail_one_is_not_invertibility`, K-1 |
| keputusan yang terbuka | tabel di atas, `NUI/SEMANTIK.md` "Yang belum ditetapkan", tabel checksum di `cosmictera-build/attack-lab/README.md` |
| baseline Lapis 5 | SHA256 image dan Lima di `NUI/LAYERS.md`, konfigurasi VM, observasi pertama |
