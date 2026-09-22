# Sesudah burn-in 72 jam — urutan eksekusi

**Disusun 22 September 2026 atas permintaan pemilik**, sementara papan masih
memikul burn-in tingkat 2: *"Dengan begitu Kamis tidak ada keputusan baru di
tengah eksekusi."* Halaman ini perintah, bukan hasil. Tidak satu langkah pun di
bawah sudah dijalankan; yang sudah disiapkan disebut dengan berkasnya.

Burn-in `20260921T053430Z-burn-in-72h` mulai 21 September 2026 05:34:30 UTC,
jadi selesai **24 September 2026 05:34:30 UTC — Kamis 12:34 WIB**. Papan tetap
milik burn-in sampai `burn_in.py` keluar sendiri; `parity_board.py` menolak
berjalan selama prosesnya hidup. **Sampai itu** — pemilik, 22 September 2026 —
`burn_in.py`, RTL, bitstream, dan eksperimen papan tidak disentuh; yang boleh
maju hanya persiapan Lapis 5 dan kontrak kueri NUI.

## Keputusan pemilik, 22 September 2026

| # | keputusan | menyentuh |
|---|---|---|
| K-1 | Dua baris `error` di log lari yang sedang berjalan dicatat sebagai **selisih yang diketahui**. `burn_in.py` tidak diubah sebelum lari 72 jam selesai — pengurai yang aktif adalah bagian observasi, dan mengubahnya di tengah lari mencampur jejak pembuktiannya. Pengurai diperbaiki **sesudah** burn-in | P0 |
| K-2 | Lapis 4 dibekukan dengan **commit dan annotated tag git**, misalnya `layer4-freeze-2026-09-24` — sesudah seluruh bukti Lapis 4 final, **tidak sekarang** | P6 |
| K-3 | Lima dipasang lewat **Homebrew**; `LIMA_HOME=~/cosmictera-layer5/lima-home`; VM **`cosmictera-layer5`**; image di `~/cosmictera-layer5/downloads/`. Template bawaan Lima tidak dipakai | P7 |
| K-4 | `journalctl` dan `ip` masuk daftar izin, **hanya** dalam bentuk `journalctl -b -n 200 --no-pager`, `journalctl -b -u <service> -n 200 --no-pager`, `ip -brief addr`, `ip link`, `ip route` | P7 |

Yang **tidak** diputuskan di hari itu, dan tidak masuk urutan ini: perbaikan
`PRINT` di silikon dan perbaikan instruksi sesudah berhenti. Keduanya RTL, K9
berlaku, dan pemilik sudah menetapkan urutannya: diverifikasi di papan dulu,
diputuskan sesudahnya.

## P0 — tutup burn-in, dan K-1

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
mengulang milik pemilik.

**K-1, dan satu hal yang terukur sebelum Kamis:** urutan pemilik adalah
*simpan log mentah final → hitung ulang dengan parser yang diperbaiki →
pastikan 0 error papan → dokumentasikan*. Tetapi **`burn_in.py` tidak menyimpan
byte mentah dari kabel**: `<id>.jsonl` hanya memuat hasil uraian — sampel tiap
menit, baris `error`, diam, dan teks yang tak terurai. Jadi lari ini tidak bisa
diurai ulang dari byte-nya. Yang bisa, dan cukup untuk memastikan 0 error
papan, adalah dari log yang ada:

1. `rtl/programs/burn_in.hasm` menyatakan pencacah error-nya *"One more error,
   and never a reset"* — kumulatif. Kalau papan pernah menghitung satu error,
   setiap sampel sesudahnya membawa `errors ≥ 1`.
2. Kedua baris `error` (t = 11.713 dan 12.686 detik) masing-masing didahului,
   pada detik yang sama, oleh baris tak terurai `0H` — sebuah angka yang
   menempel pada penanda detak, jadi pemisah barisnya hilang. Medan kedua baris
   itu bergeser dari tetangganya: `errors` berisi 7.440 dan 8.058, angka seukuran
   nomor detak sampel di sekitarnya; `wraps` berisi 0 sedangkan tetangganya
   sekitar 70; `counter_hi` berisi 73 dan 79, seukuran `wraps`.
3. Setiap sampel sesudah keduanya berbunyi `errors 0`.

Pemeriksaan itu dijalankan pada JSONL final dan hasilnya dicatat di
`cosmictera-build/burn-in/README.md`. Sesudah itu `burn_in.py` diperbaiki
sebagai butir sendiri, dengan dua **usulan** yang menunggu pemilik: sebuah
baris yang memuat `H` tetapi bukan `H` saja membuang detak yang sedang
terkumpul; dan byte mentah disimpan di sebelah JSONL, supaya lari berikutnya
bisa diurai ulang dari kabelnya. Perbaikan itu diuji pada kedua baris ini
sebelum dipakai.

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

## P5 — klasifikasi selisih final

Tiap MISMATCH dari P1–P4 dipilah dari laporannya: sudah dikenal
(OFF-PRINT-SILICON, instruksi sesudah berhenti) atau baru. Yang baru jadi butir
OFF.md dengan angkanya. **Tidak ada RTL yang diubah** di langkah ini.

## P6 — bekukan Lapis 4 (K-2)

Urutan pemilik: paritas papan → kolom opcode perangkat keras → PRINT di
silikon → HALT/RET di silikon → klasifikasi selisih final → **commit
terakhir** → **annotated tag**. Commit itu membawa rekaman dan laporan P1–P4
bersama pembaruan `NUI/PARITY.md`, `NUI/LAYERS.md`, dan
`cosmictera-build/PAPAN.md`, dengan empat gerbang hijau di lari yang sama.
Sesudah tidak ada lagi perubahan pada artefak Lapis 4:

```bash
git tag -a layer4-freeze-2026-09-24 -m "Layer 4 frozen: <isi dari laporan P1-P5>"
git show layer4-freeze-2026-09-24 --stat
```

Annotated, bukan lightweight, supaya tonggaknya membawa metadata. Tag tidak
dibuat sebelum bukti papan dan silikon masuk.

## P7 — mulai Lapis 5, hanya baca (K-3, K-4)

Yang sudah siap: `NUI/spec/layer5_lima.yaml` (image terverifikasi lewat
digest, tanpa mount, mode plain), `NUI/spec/layer5_collectors.json` (sebelas
kolektor, bentuk `journalctl` dan `ip` K-4), `src/hijaiyyah/nui/layer5.py`
(pagar hanya-baca, dan satu jalan keluar lewat `limactl shell` dengan
`LIMA_HOME` pemilik).

**Langkah pertama, sebelum VM permanen dibuat** — pemilik: uji dulu apakah
`images[].location` di Lima 2.2.0 menerima berkas lokal yang sudah
diverifikasi. Dokumentasi Lima mendukung locator dan template dari berkas
lokal; itu tidak sama dengan lokasi disk image instance, dan tidak dianggap
sama tanpa diuji.

```bash
brew info --json=v2 lima          # versi dan sha256 bottle: baseline Lima yang baru
brew install lima
export LIMA_HOME=~/cosmictera-layer5/lima-home
limactl --version

# instance uji -- namanya usulan, belum ditetapkan
limactl start --name=cosmictera-layer5-uji --tty=false NUI/spec/layer5_lima.yaml
limactl list
limactl shell cosmictera-layer5-uji -- cat /etc/os-release
limactl shell cosmictera-layer5-uji -- cat /proc/mounts     # tidak ada mount dari Mac
limactl delete --force cosmictera-layer5-uji
```

Tiga hal yang harus terbukti di instance uji: image diambil dari berkas lokal
itu (bukan diunduh), versi di `/etc/os-release` adalah Ubuntu 24.04, dan
`/proc/mounts` tidak memuat satu pun folder Mac. Lalu uji negatifnya: salinan
YAML dengan satu digit digest diubah **harus ditolak** Lima. Kalau salah satu
gagal, VM permanen tidak dibuat dan temuannya dilaporkan.

Sesudah itu baru VM permanen, lalu kolektor satu per satu:

```bash
limactl start --name=cosmictera-layer5 --tty=false NUI/spec/layer5_lima.yaml
PYTHONPATH=src python3 -m hijaiyyah.nui.layer5                               # rencana
```

**Satu konsekuensi K-3 yang dicatat:** tarball Lima yang SHA256-nya
diverifikasi 22 September bukan yang dipasang Homebrew. Formula Homebrew hari
itu menyebut versi yang sama, 2.2.0, tetapi baseline Lima dicatat ulang dari
`brew info` saat dipasang, di `NUI/LAYERS.md`.

## Paket audit sesudah P7

| isi | tempat |
|---|---|
| commit, hasil empat gerbang, dan tag beku | pesan commit P6, tag `layer4-freeze-…` |
| burn-in 72 jam, hash, baseline, dan pemeriksaan K-1 | `cosmictera-build/burn-in/` |
| paritas papan dan kolom per opcode | `cosmictera-build/parity-board/*-parity.*` |
| PRINT di silikon | `cosmictera-build/parity-board/*-print.*` |
| HALT/RET di silikon | `cosmictera-build/parity-board/*-stop.*` |
| ekspektasi yang dibekukan sebelum papan ditanya | `NUI/board_expected.json` |
| selisih yang diketahui | `cosmictera-build/OFF.md`, fakta `nui.tail_one_is_not_invertibility`, K-1 |
| keputusan yang terbuka | `NUI/SEMANTIK.md` "Yang belum ditetapkan", tabel checksum di `cosmictera-build/attack-lab/README.md` |
| baseline Lapis 5 | SHA256 image, versi dan sha256 Lima dari Homebrew, konfigurasi VM, observasi pertama |
