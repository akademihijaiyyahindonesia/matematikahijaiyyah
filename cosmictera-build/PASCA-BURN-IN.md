# Sesudah burn-in 72 jam — urutan eksekusi

**Disusun 22 September 2026 atas permintaan pemilik**, sementara papan masih
memikul burn-in tingkat 2: *"Dengan begitu Kamis tidak ada keputusan baru di
tengah eksekusi."* Halaman ini perintah, bukan hasil; langkah yang sudah
dijalankan ditandai dengan tanggalnya dan menunjuk ke tempat hasilnya.

Burn-in `20260921T053430Z-burn-in-72h` mulai 21 September 2026 05:34:30 UTC dan
**tutup 24 September 2026 05:34:30 UTC — Kamis 12:34 WIB**, dengan `ended`
berbunyi `duration reached` dan 0 error papan. Sampai jam itu, atas perintah
pemilik, `burn_in.py`, RTL, bitstream, dan eksperimen papan tidak disentuh.

**Urutan P0–P8 dikunci pemilik 23 September 2026**, dan tidak diubah lagi.
Penomoran ini urutan eksekusi, **bukan** lapis NUI: dua belas lapis NUI tetap
seperti di `NUI/LAYERS.md`. Dua pergeseran dari susunan 22 September dicatat
supaya tidak diam: pengurai naik menjadi **P1**, mendahului paritas papan, dan
klasifikasi selisih pindah ke **P7**, bersama pembekuan Lapis 4.

```
P0  tutup burn-in dan bekukan bukti          selesai 24 September 2026
P1  pengurai + capture mentah                selesai 24 September 2026
P2  paritas papan                            selesai 24 September 2026
P3  kolom opcode perangkat keras             selesai 24 September 2026
P4  PRINT di silikon                         selesai 25 September 2026
P5  HALT/RET di silikon                      selesai 25 September 2026
P6  checksum + sabotase                      selesai 26 September 2026
P7  laporan selisih final, freeze Lapis 4, tag selesai 26 September 2026
P8  Lapis 5                                  P8.1–P8.7 selesai 26–27 September 2026
```

## Keputusan pemilik, 22 September 2026

| # | keputusan | menyentuh |
|---|---|---|
| K-1 | Dua baris `error` di log lari yang sedang berjalan dicatat sebagai **selisih yang diketahui**. `burn_in.py` tidak diubah sebelum lari 72 jam selesai — pengurai yang aktif adalah bagian observasi, dan mengubahnya di tengah lari mencampur jejak pembuktiannya. Pengurai diperbaiki **sesudah** burn-in | P0 |
| K-2 | Lapis 4 dibekukan dengan **commit dan annotated tag git**, misalnya `layer4-freeze-2026-09-24` — sesudah seluruh bukti Lapis 4 final | P7 |
| K-3 | Lima dipasang lewat **Homebrew**; `LIMA_HOME=~/cosmictera-layer5/lima-home`; VM **`cosmictera-layer5`**; image di `~/cosmictera-layer5/downloads/`. Template bawaan Lima tidak dipakai | P8 |
| K-4 | `journalctl` dan `ip` masuk daftar izin, **hanya** dalam bentuk `journalctl -b -n 200 --no-pager`, `journalctl -b -u <service> -n 200 --no-pager`, `ip -brief addr`, `ip link`, `ip route` | P8 |
| K-5 | Arti STATE dikunci: keadaan aktual OBJECT/TARGET saat representasi semantik dibuat. Kosakatanya belum dimigrasi (`NUI/spec/usr.json`) | — |
| K-6 | Domain ketujuh NUI, **HOST**: keadaan, proses, service, jaringan, filesystem, dan runtime host yang diamati. Tidak ada fakta HOST sebelum kolektor mengukur | P8 |
| K-7 | **Byte mentah kabel jadi bukti primer burn-in**; pengurai bekerja offline atasnya. Lari 72 jam sekarang tidak diubah — lognya rekaman historis, dan dua error semunya artefak pengurai | P0, P1 |
| K-8 | Checksum loader menutupi **seluruh container**: rekaman sektor 16, header dengan medan checksum dinolkan, tabel relokasi, kata program. Tabelnya di `cosmictera-build/attack-lab/README.md`. Tidak diimplementasikan sebelum burn-in selesai | P6 |
| K-9 | Instance uji Lapis 5 **`cosmictera-layer5-uji`**, sekali pakai; `cosmictera-layer5` jadi instance utama sesudah jalurnya terbukti di sana | P8 |
| K-10 | Algoritma checksum: **jumlah 32-bit mod 2³²**, bukan CRC-32. `CHECKSUM32 = Σ canonical_container_words mod 2^32`, dihitung atas representasi word container sebagaimana tersimpan di kartu — satu cara menghitung, tanpa tabel CRC-32 dan tanpa memperbesar arena heap (23 September 2026) | P6 |
| K-11 | Rekaman observasi Lapis 5 disimpan **di host, di luar repositori**: `~/cosmictera-layer5/observations/<run_id>/`, dengan `manifest.json` dan keluaran mentah per kolektor (23 September 2026) | P8 |
| K-12 | Kolektor `journal` **diterima sebagai batas izin yang terdokumentasi**: tanpa `sudo`, grup `lima` tidak diubah, allowlist tidak diperluas demi PASS. Keadaannya `unavailable_due_to_permissions`, dengan stderr-nya sebagai provenance (26 September 2026) | P8.4, P8.5 |
| K-13 | Keenam kolektor yang masih usulan **ditetapkan**; kesebelasnya berbagi satu kontrak. Ditetapkan berarti kontraknya dikunci, bukan selalu exit 0: 9 PASS, 1 unavailable karena izin, 1 unavailable karena perintahnya tidak ada (26 September 2026) | P8.4, P8.5 |
| K-14 | Alasan `unknown` HOST adalah **bukti belum cukup, bukan sistem belum ada**: "no supporting HOST observation"; `host services` menjawab "no supporting journal/service observation" (26 September 2026) | P8.5 |
| K-15 | Evidence Lapis 5 tetap **teks UTF-8** keluaran perintah; `observe()` tidak diubah jadi tangkapan byte mentah. Bukti kabel UART (P1) byte mentah karena penguraiannya persoalan byte; kolektor yang kelak menghasilkan format bukan teks direkam sebagai biner secara eksplisit (26 September 2026) | P8 |
| K-16 | Identitas kanonik sebuah observasi adalah **`(vm_name, run_id)`**: `layer5.latest(vm_name)` hanya membaca observasi milik VM itu, dan observasi instance uji tidak pernah menjawab untuk instance utama. Run berikutnya di `~/cosmictera-layer5/observations/<vm_name>/<run_id>/`; run lama tidak dipindahkan, dibedakan oleh `vm_name` di manifest-nya (27 September 2026) | P8.6 |
| K-17 | `cosmictera-layer5-uji` **dihentikan, tidak dihapus**: disk dan direktorinya dipertahankan sampai instance utama menjalankan kolektor pertamanya dan provenance-nya terbukti (27 September 2026) | P8.6 |
| K-18 | Laporan nextpnr (LUT4, DFF, BSRAM, Fmax) **tetap SIMULATED** di inventaris 6.1, dengan `evidence_kind` = `PNR/build-derived`, dan dokumentasinya menyatakan eksplisit: hasil synthesis/place-and-route/build analysis, bukan simulasi perilaku dan bukan pengukuran fisik. Tidak ada kelas keempat (27 September 2026) | Lapis 6.1 |
| K-19 | Judul resmi Lapis 6 **tetap *Pemahaman perangkat keras***, bagian peta dua belas lapis yang dikunci; *Hardware Intelligence* adalah nama kerja atau alias (27 September 2026) | Lapis 6 |

Yang **tidak** diputuskan di hari itu, dan tidak masuk urutan ini: perbaikan
`PRINT` di silikon dan perbaikan instruksi sesudah berhenti. Keduanya RTL, K9
berlaku, dan pemilik sudah menetapkan urutannya: diverifikasi di papan dulu,
diputuskan sesudahnya.

## P0 — bekukan burn-in: log final (K-1, K-7) — **selesai 24 September 2026**

Hasilnya, beserta ketiga hash, garis dasar, pemeriksaan K-1, dan perbandingan
terhadap tingkat 1, ada di `cosmictera-build/burn-in/README.md` bagian
"Tingkat 2" dan di `cosmictera-build/PAPAN.md`. Tidak disalin ke sini (R1).

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
`cosmictera-build/burn-in/README.md`. Menurut K-7, log lari ini adalah
**rekaman historis**, dan kedua baris `error`-nya dicatat sebagai artefak
pengurai, bukan error papan. Pengurainya diperbaiki sesudahnya, sebagai butir
sendiri — lihat bagian "Pengurai burn-in (K-7)" di bawah.

## P1 — pengurai dan capture mentah (K-7) — **selesai 24 September 2026**

Dua alat baru, `rtl/scripts/burn_in_capture.py` dan `rtl/scripts/burn_in_parse.py`; `burn_in.py` tidak disentuh. Capture pendek
pertama `20260924T073655Z-burn-in` — 9.940 byte, 457 detak, 0 parse error,
0 error papan — dan hasilnya di `cosmictera-build/burn-in/README.md` bagian
"P1". Tidak disalin ke sini (R1).

Pemilik menyetujui perbaikan pengurai dengan satu perubahan arsitektur:
**pengurai tidak lagi menjadi sumber bukti primer**. Buktinya adalah byte yang
benar-benar diterima dari kabel.

```
USB/serial → capture mentah → berkas .raw (bukti biner) → pengurai offline
           → log burn-in terstruktur → analisis
```

Metadata minimal tiap capture, dari pemilik: cap waktu mulai, cap waktu
selesai, identitas serial/perangkat, sidik jari bitstream, nama berkas capture,
jumlah byte, dan versi pengurai.

Lari 72 jam yang sudah tutup **tidak diubah apa pun**, dan lognya tetap rekaman
historis. **Yang tidak boleh diklaim di langkah ini** — perintah pemilik, 24
September 2026: pengurai **belum** tervalidasi terhadap capture mentah kabel,
karena lari 72 jam tidak menyimpan byte mentah. Yang bisa dibuktikan sekarang
adalah laporan pengurai, pencacah papan, dan artefak log yang sudah ada.
Validasi capture mentah baru terjadi pada **lari berikutnya**. Cacat pengurainya sudah terukur (P0): sebuah angka yang menempel
pada penanda detak, `0H`, kehilangan pemisah barisnya. Cara memperbaikinya —
misalnya membuang detak yang sedang terkumpul ketika sebuah baris memuat `H`
tetapi bukan `H` saja — tetap **usulan**, dan diuji pada byte mentah, bukan
pada JSONL.

## P2 — paritas papan, seluruh korpus — **selesai 24 September 2026**

73 PARITY, 2 MISMATCH, 28 UNKNOWN dari 79 program yang dikirim; kolom opcode
74 PARITY, 0 MISMATCH, 29 UNKNOWN. Rekaman `20260924T105400Z-parity.json`,
angkanya di `cosmictera-build/PAPAN.md` (R1).

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

## P3 — kolom perangkat keras per opcode — **selesai 24 September 2026**

Matriksnya di `NUI/PARITY.md`, bagian "Kolom perangkat keras per opcode":
74 PARITY, 0 MISMATCH, 29 UNKNOWN, tiap sel dengan cacah bukti dan program
sumbernya, dihitung ulang dari byte mentah rekaman P2 (R1).

Keluar dari laporan P2: `opcodes` di `<UTC>-parity.report.json`. Aturannya
ditulis di `src/hijaiyyah/nui/board_parity.py`: PARITY kalau opcode hanya
muncul di program yang cocok, MISMATCH kalau hanya di program yang berbeda,
UNKNOWN kalau di keduanya — kabel saja tidak bisa menunjuk instruksi mana yang
berbeda — atau kalau tak satu program yang dikirim menjalankannya. Kolom itu
lalu dipindah ke `NUI/PARITY.md`.

## P4 — PRINT di silikon — **selesai 25 September 2026**

Tiga lari identik: batas pertama 2²³, 2²² dan 2²⁴ benar, dan keluaran salahnya
**tidak berulang** — 14 dari 15 berbeda. Tabelnya di `cosmictera-build/OFF.md`
bagian OFF-PRINT-SILICON (R1).

```bash
python3 rtl/scripts/parity_board.py --experiment print --port /dev/tty.usbserial-20250303171
```

Satu program, tangga pemilik: 2²², 2²³, 2²⁴, 2²⁵, 2²⁶, 2²⁷, 2³¹. Laporannya
berisi `ladder`: nilai, Python, interpreter, RTL tersimulasi, papan, dan
`first_divergence`. Yang diharapkan kedua mesin sudah beku — keduanya mencetak
ketujuh nilai dengan benar. Yang dicari **batas pertama**, bukan perbaikan.

## P5 — HALT dan RET di silikon — **selesai 25 September 2026**

`PRINT` sesudah `HALT` dan sesudah RET fault sampai ke kabel; probe sentinel
membuktikan programnya berjalan. Register dan RAM sesudah berhenti UNKNOWN —
tidak teramati dari luar. Tabelnya di `cosmictera-build/OFF.md` (R1).

```bash
python3 rtl/scripts/parity_board.py --experiment stop --port /dev/tty.usbserial-20250303171
```

Lima probe, empat pertanyaan pemilik dan satu kasus HALT yang terlihat di
kabel. RTL tersimulasi sudah menjawab **ya** untuk keempatnya (R1 = 7 sesudah
HALT dan sesudah RET gagal, `MEM[0x100]` = 5 sesudah HALT, `5` di kabel sesudah
RET gagal dan sesudah HALT). Papan hanya bisa menjawab yang lewat kabel:
register dan RAM sesudah berhenti tidak pernah tercetak, dan laporannya
menyebut itu, bukan mengisinya.

## P6 — checksum (K-8, K-10) — **selesai 26 September 2026**

CHECKSUM32 di builder, di loader Python, dan di loader HCPU, dengan urutan
kanonik diuji lebih dulu. 19 kasus di papan, 0 temuan; 21 kasus di Python dan
simulasi, vonis sama persis. Rinciannya di `cosmictera-build/attack-lab/README.md` (R1).

**Checksum.** Cakupan K-8 dan algoritma K-10 diterapkan di
`rtl/programs/hos_prog_load.hasm` dan `rtl/scripts/build_container.py`:
`CHECKSUM32 = Σ canonical_container_words mod 2^32` atas rekaman sektor 16,
header dengan medan checksum dinolkan, tabel relokasi, dan badan program —
nama `CRC` ikut diganti `CHECKSUM32`. Empat kasus sabotase menyertainya, satu
untuk tiap bagian yang baru dilindungi, dan `VERSION` naik. Tabel
keputusannya di `cosmictera-build/attack-lab/README.md`. Terukur 22 September 2026: keempat
program yang membawa loader kartu — `hos_prog_load`, `shell`, `test_prog_load`,
`test_prog_run` — tidak termasuk yang dikirim P2, jadi mengubah loader di sini
tidak menggeser bukti papan P2–P5. Model Lapis 3 dan Lapis 4 yang memuat
program-program itu dibangun ulang sebelum P7.

## P7 — laporan selisih final dan bekukan Lapis 4 (K-2) — **selesai 26 September 2026**

Laporannya `NUI/LAYER4.md`, tag `layer4-freeze-2026-09-26`. Tanggal tag adalah
tanggal freeze, bukan tanggal burn-in selesai — perintah pemilik.

**Laporan selisih final.** Tiap MISMATCH dari P2–P6 dipilah dari laporannya:
sudah dikenal (OFF-PRINT-SILICON, instruksi sesudah berhenti) atau baru.
**Tidak ada yang baru**: ketiga selisih terukur sudah punya butir OFF.md.
Selisih alat dicatat di kelasnya sendiri, tidak pernah di kelas perangkat
keras. **Tidak ada RTL yang diubah** di langkah ini, dan tidak ada ekspektasi
yang digeser.

Rekaman dan laporan P0–P6 sudah di-commit di langkahnya masing-masing; commit
P7 membawa pembekuannya — `src/hijaiyyah/nui/layer4_freeze.py`,
`NUI/layer4_freeze.json`, `NUI/LAYER4.md` — sesudah pemeriksaan P7.4 pemilik
(`git status --short`, `git diff --check`, `parity_model --verify`, pytest
penuh, `make -C rtl/tb all`) di lari yang sama. Lalu, perintah pemilik:

```bash
git commit -m "freeze Layer 4 hardware parity evidence"
git tag -a layer4-freeze-2026-09-26 -m "CosmicTera Layer 4 hardware parity freeze"
git show layer4-freeze-2026-09-26 --no-patch
```

Annotated, bukan lightweight, supaya tonggaknya membawa metadata. Tag tidak
dibuat sebelum bukti papan dan silikon masuk.

## P8 — mulai Lapis 5, hanya baca (K-3, K-4, K-6, K-9)

**Dibuka pemilik 26 September 2026**, dengan izin memasang Lima lewat Homebrew
dan memakai image yang sudah diverifikasi — template bawaan Lima tidak. Urutan
pemilik hari itu:

```
P8.1  persiapan host: LIMA_HOME, evidence store di luar repo    selesai
P8.2  uji image lokal: diterima, VM ARM64, Ubuntu boot          selesai
P8.3  isolasi tamu, dan uji negatif digest                      selesai
      commit bukti host/image
P8.4  sebelas kolektor hanya-baca -> evidence store             selesai,
      9 exit 0, journal gagal karena izin (terdokumentasi), docker tidak ada
P8.5  provenance HOST: facts/ tersegel, observations/ runtime   selesai
P8.6  tujuh kueri yang dibekukan        dijalankan di dalam P8.5, perintah pemilik
P8.7  cosmictera-layer5-uji hijau -> baru cosmictera-layer5   selesai 26 September
P8.6  (pemilik, 27 September) namespace per VM K-16, uji dihentikan K-17,
      kolektor pertama instance utama                          selesai
      sepuluh kolektor lainnya di instance utama, pemeriksaan
      akhir, instance uji dipensiunkan                          selesai
```

Sesudah itu Lapis 5 masuk **baseline utama**: `cosmictera-layer5` satu-satunya
instance aktif, dan tiap kueri HOST berbasis namespace VM yang eksplisit.

**Penutupan operasional Lapis 5, 27 September 2026** — perintah pemilik,
sebelum Lapis 6: baseline utama dibekukan, kesegaran (aturan eksplisit, nilai
batas menunggu pemilik), delta antar-run dengan provenance kedua run, lalu
laporan `NUI/LAYER5.md`, commit, dan tag `layer5-freeze-2026-09-27`. Lalu tiga
keputusan pemilik hari itu: batas kesegaran 300 detik, `kworker` dipisah dari
delta proses sebagai `kernel_thread_changes`, dan label Lapis 5 EH. **Lapis 5
selesai.** Angkanya di `NUI/LAYERS.md`, Lapis 5.

Nomor P8.6 dipakai pemilik dua kali: 26 September untuk tujuh kueri, yang lalu
dijalankan di dalam P8.5, dan 27 September untuk namespace per VM. Yang
berlaku yang terakhir; yang pertama dicatat supaya pergeserannya tidak diam.

Uji negatif digest memakai instance sekali pakai dengan nama dari pemilik,
`cosmictera-layer5-digest-uji`, bukan instance uji. Kolektor P8.4 dijalankan
dengan `PYTHONPATH=src python3 -m hijaiyyah.nui.layer5 --record
cosmictera-layer5-uji`. Angka dan vonis P8.1–P8.4
ada di `NUI/LAYERS.md`, Lapis 5; rekaman mentahnya di
`~/cosmictera-layer5/observations/`, dan **tidak pernah** masuk `facts/` —
pagar pemilik.

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

**Instance ujinya `cosmictera-layer5-uji`** (K-9), sekali pakai. Urutan yang
harus terbukti di sana, dari pemilik: lokasi image lokal → Lima create → boot
Ubuntu → tanpa mount home Mac → kolektor hanya-baca → pagar perintah → kontrak
kueri. Baru sesudah jalur itu terbukti `cosmictera-layer5` jadi instance
utama.

```bash
brew info --json=v2 lima          # versi dan sha256 bottle: baseline Lima yang baru
brew install lima
export LIMA_HOME=~/cosmictera-layer5/lima-home
limactl --version

# instance uji (K-9)
limactl start --name=cosmictera-layer5-uji --tty=false NUI/spec/layer5_lima.yaml
limactl list
limactl shell cosmictera-layer5-uji -- cat /etc/os-release
limactl shell cosmictera-layer5-uji -- cat /proc/mounts     # tidak ada mount dari Mac
```

Yang harus terbukti di instance uji, berurutan:

1. image diambil dari berkas lokal itu, bukan diunduh; versi di
   `/etc/os-release` adalah Ubuntu 24.04; `/proc/mounts` tidak memuat satu pun
   folder Mac. Uji negatifnya: salinan YAML dengan satu digit digest diubah
   **harus ditolak** Lima;
2. kolektor hanya-baca, satu per satu, lewat `layer5.observe(<nama>,
   "cosmictera-layer5-uji")`;
3. pagar perintah: perintah yang ditolak tidak pernah sampai ke `limactl`;
4. kontrak kueri: `host services` dijawab dari rekaman kolektor di domain
   HOST (K-6). Rekamannya ditulis lebih dulu ke evidence store K-11,
   `~/cosmictera-layer5/observations/<run_id>/` — `manifest.json` (run_id, cap
   waktu, kolektor, nama VM, identitas perintah, exit code, durasi), satu
   berkas per wilayah, dan keluaran mentah di `raw/`. Store itu **di luar
   repositori**; `observe()` hari ini mengembalikan rekaman tanpa menulisnya,
   jadi penulisannya bagian dari langkah ini.

Kalau salah satu gagal, VM permanen tidak dibuat dan temuannya dilaporkan.
Sesudah keempatnya terbukti, instance uji dibuang:
`limactl delete --force cosmictera-layer5-uji`.

Sesudah itu baru VM permanen, lalu kolektor satu per satu:

```bash
limactl start --name=cosmictera-layer5 --tty=false NUI/spec/layer5_lima.yaml
PYTHONPATH=src python3 -m hijaiyyah.nui.layer5                               # rencana
```

**Satu konsekuensi K-3 yang dicatat:** tarball Lima yang SHA256-nya
diverifikasi 22 September bukan yang dipasang Homebrew. Formula Homebrew hari
itu menyebut versi yang sama, 2.2.0, tetapi baseline Lima dicatat ulang dari
`brew info` saat dipasang, di `NUI/LAYERS.md`.

## Paket audit sesudah P8

| isi | tempat |
|---|---|
| commit, hasil empat gerbang, dan tag beku | pesan commit P7, tag `layer4-freeze-…` |
| burn-in 72 jam, hash, baseline, dan pemeriksaan K-1 | `cosmictera-build/burn-in/` |
| paritas papan dan kolom per opcode | `cosmictera-build/parity-board/*-parity.*` |
| PRINT di silikon | `cosmictera-build/parity-board/*-print.*` |
| HALT/RET di silikon | `cosmictera-build/parity-board/*-stop.*` |
| ekspektasi yang dibekukan sebelum papan ditanya | `NUI/board_expected.json` |
| selisih yang diketahui | `cosmictera-build/OFF.md`, fakta `nui.tail_one_is_not_invertibility`, K-1 |
| keputusan yang terbuka | `NUI/SEMANTIK.md` "Yang belum ditetapkan" (migrasi kosakata STATE) dan `open` di `NUI/spec/layer5_collectors.json`. Algoritma checksum tidak lagi terbuka: K-10 |
| baseline Lapis 5 | SHA256 image, versi dan sha256 Lima dari Homebrew, konfigurasi VM, observasi pertama |
