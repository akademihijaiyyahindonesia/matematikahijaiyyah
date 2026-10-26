# Layer 7 — Autonomous Operation

Kontrak operasi otonom. Kerangkanya ditulis atas perintah pemilik, 30 September
2026, dan pada hari yang sama pemilik mengunci 7.2, 7.5, dan 7.11. Judul resmi
lapis ini di `NUI/LAYERS.md` adalah *Operasi otonom*; *Autonomous Operation*
adalah padanan yang pemilik pakai untuk dokumen ini.

**Status kini** (dihimpun dari keputusan pemilik yang tercatat; riwayatnya
utuh di bagian *Riwayat status* di akhir dokumen):

```text
7.2  DEFINED / LOCKED                       pemilik, 30 September 2026
7.5  AUTHORIZATION BOUNDARY DEFINED         pemilik, 30 September 2026
7.11 LOCKED                                 pemilik, 30 September 2026
Layer 7 evaluator              GREEN        638d827, 865959e
7.7 post-action success        VALIDATED    b7fa5e8
Decision / Dry-Run             GREEN        46f4b14
SEND_PROGRAM proposal          HARD STOP    590baa6 GREEN
Readiness evidence discovery   GREEN        08f1e36 — loader readiness not observable
SEND_PROGRAM authorization     DENIED
Portal slot: --detect, ISOLATE_FAULT   AUTHORIZED   pemilik, 3 Oktober 2026 — tanpa penulisan UART
Portal slot: RESTART, RECOVER          AUTHORIZED   pemilik, 3 Oktober 2026 — bitstream tercatat, SRAM, paling banyak 3 ulang
Mutative authorization         DENIED       kecuali empat baris slot Portal 8888 dan satu baris RESTART_SERVICE di 7.4
Authorization boundary         EXTENDED     pemilik, 3 Oktober 2026 — izin 9–12 di 7.5
Layer 7                        REOPENED     pemilik, 3 Oktober 2026 — recover / restart / isolate first
Completion condition           mengisolasi, memulihkan, dan merekam — pemilik, 3 Oktober 2026
Freeze tag                     layer7-freeze-2026-10-03 — nama dari pemilik; dipasang sesudah uji papan; tidak mencakup adendum Linux sesudahnya (59a7b0b, 81fcd38, c167893, c325eb4) maupun revisi pasca-freeze pemeriksaan F5 pin LF di bawah
F5 pin model fungsi RTL        REVISI PASCA-FREEZE — `layer7.py` memakai `rtl_function._file_sha` (LF kanonik); hash byte-persis untuk berkas terlindung dan evidence store tetap
Linux service recovery         ADENDUM      pasca-freeze, akhir 7.4 — sesudah tag layer7-freeze-2026-10-03
Linux: VM uji, cron, kelas, ISOLATE_SERVICE   DISETUJUI   pemilik, 6 Oktober 2026 — baca-saja; RESTART_SERVICE dibuka terpisah (baris di bawah)
Linux: ISOLATE_SERVICE                AUTHORIZED   pemilik, 6 Oktober 2026 — baris 7.4 sendiri, izin 13 di 7.5; tanpa tindakan
Linux: RESTART_SERVICE                AUTHORIZED   pemilik, 6 Oktober 2026 — UNIT_INACTIVE saja, 3 percobaan; satu lari di VM uji, 7 Oktober 2026: SUCCESS pada percobaan 1
```

Keputusan ini dokumen dan spec. Ia tidak memberi izin implementasi tindakan
otonom di luar batas yang ditetapkan. Otonomi NUI berada di wilayah
**read → evaluate → verify → evidence**, ditambah dua wilayah mutatif yang
dibedakan: memulai ulang dan memulihkan slot Portal 8888 (pemilik, 3 Oktober
2026, dalam freeze `layer7-freeze-2026-10-03`), dan memulai ulang `cron.service`
di VM uji Linux atas `UNIT_INACTIVE` (pemilik, 6 Oktober 2026, adendum
pasca-freeze) — masing-masing di dalam batas baris 7.4-nya. Tidak ada mutasi
lain tanpa keputusan otorisasi berikutnya.

Isinya menunjuk ke sumber yang sudah terukur, tidak menyalin nilainya (R1). Nilai
yang bisa berubah — misalnya ambang kesegaran atau daftar kolektor — tinggal di
spec asalnya.

---

## 7.1 Tujuan

Tujuan Lapis 7 tertulis di `NUI/LAYERS.md`: menjalankan sistem tanpa pengawasan
manusia — memantau, memulihkan, memulai ulang, mengisolasi kesalahan —
berdasarkan telemetri, diagnostik, dan fakta terverifikasi.

Langkah pertama yang pemilik tetapkan, 29 September 2026, **bukan** membuat
sistem bertindak otonom, melainkan menetapkan kontrak yang dapat diukur, supaya
Lapis 7 tidak mengubah NUI menjadi sekadar lingkar otomatis tanpa guard.

## 7.2 Definisi Operasi Otonom

**Dikunci pemilik, 30 September 2026:**

> Operasi otonom adalah pelaksanaan tindakan yang telah diotorisasi sebelumnya
> oleh sistem tanpa persetujuan manusia pada setiap tindakan, berdasarkan
> observasi yang memenuhi kontrak pembacaan, dalam batas otorisasi yang
> eksplisit, dengan kondisi sebelum tindakan, bukti hasil sesudah tindakan, dan
> penghentian aman ketika kondisi yang diperlukan tidak diketahui, basi, atau
> tidak tercakup.

Konsekuensi normatifnya:

> Otonomi tidak menciptakan kewenangan baru. Sistem hanya boleh memilih dan
> menjalankan tindakan yang telah termasuk dalam batas otorisasi yang berlaku.

*Autonomous ≠ unrestricted.*

**Pagar yang langsung dikunci** (pemilik, 30 September 2026). Lapis 7 tidak
boleh:

- mencabut read-only guard Lapis 5;
- melewati K-4;
- melewati K-12;
- mengubah state hanya karena tidak ada evidence;
- menganggap `UNKNOWN` sebagai izin bertindak;
- menganggap `NOT_COVERED` sebagai keberhasilan;
- mengubah batas otorisasi secara otomatis.

## 7.3 Read Contract

Sumber observasi yang tersedia untuk dikonsumsi operasi otonom, dengan dasar dan
batas yang sudah berlaku. Kontrak ini tidak memperluas satu pun dari dasar itu.

| sumber | tempat | dasar yang sudah berlaku | sifat waktunya |
|---|---|---|---|
| Observasi host Lapis 5 | `~/cosmictera-layer5/observations/<vm_name>/<run_id>/`, di luar repositori (K-11); dibaca lewat `src/hijaiyyah/nui/layer5.py` | Perintah host hanya lewat `layer5.guard`: daftar izin hanya-baca dari `NUI/LAYERS.md`, argumen tanpa karakter shell, bentuk argv utuh (K-4), opsi yang menulis atau mengirim ditolak, perintah yang tidak berhenti sendiri wajib dibatasi. Identitas observasi `(vm_name, run_id)` (K-16). Tiap observasi diverifikasi terhadap ukuran dan SHA-256 di manifest-nya sebelum dipakai | Current, stale, atau unknown menurut aturan kesegaran di `NUI/spec/layer5_collectors.json` |
| Delta antar-run Lapis 5 | `layer5.delta` | Observasi, bukan tindakan (keputusan penutupan Lapis 5) | Antara dua run yang disebut |
| Keadaan hardware Lapis 6 | `src/hijaiyyah/nui/hardware_state.py`, `NUI/HARDWARE_STATE.md` | Precedence LIVE > MEASURED > SIMULATED > UNKNOWN. Rekaman papan historis bukan keadaan hardware sekarang | CURRENT hanya dari sumber live; hari ini tidak ada, jadi `hardware current-state` menjawab UNKNOWN |
| Inventaris, sumber telemetri, provenance, dan korelasi hardware Lapis 6 | `NUI/HARDWARE.md`, `NUI/TELEMETRY_SOURCES.md`, `NUI/HARDWARE_PROVENANCE.md`, `NUI/HARDWARE_CORRELATION.md` | Dibekukan di `NUI/LAYER6.md` (tag `layer6-freeze-2026-09-29-final`) | Historis atau tersimulasi; "sumber yang ada tidak sama dengan sumber yang sedang mengalir" |
| Fungsi RTL Lapis 6 | `NUI/RTL_FUNCTION.md` | Dibandingkan dengan oracle-nya di bawah simulasi, termasuk model HCPU `1c33e30` | Tersimulasi, bukan keadaan perangkat |
| Bukti papan Lapis 4 | `NUI/LAYER4.md` dan rekaman yang ia tunjuk di `cosmictera-build/` | Dibekukan (tag `layer4-freeze-2026-09-26`) | Historis |
| Fakta tersegel Lapis 0 | `facts/` | Pengetahuan rekayasa; bukti runtime tidak pernah masuk ke sini | Bukan keadaan runtime |

Kueri yang sudah ada untuk membaca sebagian sumber ini:
`python3 -m hijaiyyah.nui.knowledge host …` dan
`python3 -m hijaiyyah.nui.knowledge hardware current-state`. Tujuh pertanyaan
kontrak kuerinya ada di `NUI/spec/query_contract.json`.

## 7.4 Action Contract

Status tiap kategori, ditetapkan pemilik 30 September 2026. Daftar tindakan lama
dipertahankan, dengan statusnya. Dua baris yang menyebut slot Portal 8888
dibuka pemilik 3 Oktober 2026; keduanya tidak mengubah papan. Satu baris untuk
VM uji Linux dibuka pemilik 6 Oktober 2026; ia hanya membaca. Satu baris lagi,
dibuka pemilik hari yang sama, memulai satu unit di VM uji itu.

| kategori | asal catatannya | status |
|---|---|---|
| Observasi / read-only | Mekanisme Lapis 5 dan state model Lapis 6 (7.3) | **AUTHORIZED** |
| Evidence, provenance, freshness, delta | Mekanisme Lapis 5 (7.3, 7.6, 7.7) | **AUTHORIZED** |
| Pembacaan identitas papan lewat JTAG (`openFPGALoader --detect`) | Proposal pemulihan slot Portal 8888, di bawah | **AUTHORIZED** |
| Isolasi kesalahan slot Portal 8888 (`ISOLATE_FAULT`) | Proposal pemulihan slot Portal 8888, di bawah | **AUTHORIZED** |
| Konfigurasi ulang papan ke SRAM dengan bitstream Portal 8888 yang SHA-256-nya tercatat | Proposal pemulihan slot Portal 8888, di bawah | **AUTHORIZED** |
| Penulisan UART protokol Portal 8888 sesudah muat ulang pada lari yang sama | Proposal pemulihan slot Portal 8888, di bawah | **AUTHORIZED** |
| Mulai ulang slot Portal 8888 (`RESTART_PORTAL`) | Proposal pemulihan slot Portal 8888, di bawah | **AUTHORIZED** |
| Pemulihan slot Portal 8888 (`RECOVER_PORTAL`) | Proposal pemulihan slot Portal 8888, di bawah | **AUTHORIZED** |
| Penggolongan gangguan `cron.service` di VM uji Linux (`ISOLATE_SERVICE`) | Keputusan pemilik 6 Oktober 2026 atas proposal layanan Linux, di bawah | **AUTHORIZED** |
| Mulai ulang `cron.service` di VM uji Linux (`RESTART_SERVICE`) | Keputusan pemilik 6 Oktober 2026 atas proposal layanan Linux, di bawah | **AUTHORIZED** |
| 10 perintah host lama: `rm`, `mv`, `kill`, `reboot`, `shutdown`, `systemctl start`, `systemctl stop`, `docker rm`, `docker stop`, `docker exec` | Daftar "belum diizinkan" Lapis 5 di `NUI/LAYERS.md` | **DENIED** |
| Konfigurasi ulang papan (`openFPGALoader`) | Dijalankan `rtl/scripts/burn_in.py` di dalam satu lari burn-in (7.9) | **DENIED** |
| Mengirim program ke papan | Dijalankan `rtl/scripts/burn_in.py` di dalam satu lari burn-in (7.9) | **DENIED** |
| Menjaga host tetap terjaga (`caffeinate`) | Dijalankan `rtl/scripts/burn_in.py` selama logger hidup (7.9) | **DENIED** |
| Restart / recovery | Tujuan Lapis 7 di `NUI/LAYERS.md` | **DENIED** |
| Isolasi kesalahan | Tujuan Lapis 7 di `NUI/LAYERS.md` | **DENIED** |
| Mutasi repository / konfigurasi | — | **DENIED** |

`rtl/scripts/burn_in.py` tetap **historical evidence**, bukan dasar pemberian
izin.

### Proposal otorisasi: `SEND_PROGRAM`

```text
STATUS: HARD STOP — STOP / REPORT (pemilik, 1 Oktober 2026)
Authorization: DENIED
Tabel 7.4 di atas tidak berubah: "Mengirim program ke papan" tetap DENIED.
Proposal ini tidak memberi izin apa pun.
```

Dipilih pemilik, 1 Oktober 2026, sebagai kandidat proposal pertama.
Alasannya: dari seluruh tindakan mutatif yang tercatat, rantai evidence-nya
paling lengkap — loader punya model fungsi dan verifikasi fisik, relokasi
program pernah diuji di papan, dan ada keluaran deterministik yang bisa dipakai
sebagai postcondition. Jadi proposal tidak perlu mekanisme pengukuran baru.

**Tindakan dan mekanismenya yang sudah ada.** `rtl/scripts/send_program.py`
(`encode()`) mengirim 4 byte jumlah kata N lalu 4N byte program, byte paling
signifikan lebih dulu. Penerimanya `rtl/programs/loader.hasm` di bitstream
`rtl/fpga/gowin/hcpu_gowin_top_loader.fs`. Loader menulis memori instruksi mulai
alamat 64, lalu masuk ke program lewat `ERET` dalam mode supervisor. Program
dirakit host di basis 64 (`LOAD_BASE`). Jawabannya dibaca sebagai byte mentah
sampai laporan `CYCLES=` wrapper (`run_one()` di `rtl/scripts/parity_board.py`),
dan laporan membaca byte mentah itu (aturan Lapis 4).

**Target**: Tang Nano 20K / HCPU yang identitasnya telah diverifikasi,
menjalankan bitstream loader, di port serial 115200.

**Ruang lingkup** (pemilik):
- 1 transfer;
- 1 program yang sudah memiliki evidence fisik;
- tanpa perubahan repository;
- tanpa perubahan konfigurasi VM;
- tanpa perubahan HFS/persistent state, kecuali secara eksplisit menjadi bagian
  dari protokol transfer yang sudah ada.

**Program kandidat: `rtl/programs/test_from_card.hasm`** — dipilih pemilik,
1 Oktober 2026, atas kriteria evidence loader fisik dan keluaran
deterministik `1 2 3`:
- 7 kata di basis 64, payload `a9f0351e…`. Dirakit ulang pada 1 Oktober 2026,
  hasilnya tetap `a9f0351e…`.
- Keluarannya dibekukan sebelum papan ditanya, di `NUI/board_expected.json`:
  `1\n2\n3\n` untuk RTL dan interpreter di basis 64.
- Di papan, lewat jalur yang sama: P2 `20260924T105400Z-parity` mencetak
  `1 2 3`, PARITY, `board_equals_rtl`. Korelasi Lapis 6 mencatatnya sebagai
  tautan DIRECT `ran`.
- Program yang sama mencetak `1 2 3` dari kartu di 2B, lewat relokasi loader
  kartu.
- `JMP` absolutnya membuat `1 2 3` membuktikan program mendarat di basis yang
  dipakai untuk merakitnya. Di jalur UART basis itu dipasang assembler host,
  bukan relokasi loader. Relokasi loader hanya ada di jalur kartu, yang menulis
  kartu SD dan karena itu di luar ruang lingkup ini.
- `rtl/programs/test_distance.hasm` — 11 kata, `1 2 3`, PARITY di P2 yang
  sama, tanpa `JMP` — tetap kandidat alternatif, **bukan kandidat utama**
  proposal pertama (pemilik).
- `rtl/programs/loader.hasm` dan `rtl/programs/test_from_card.hasm` sama-sama
  tidak menyentuh blok kartu `0xFE0`: loader hanya memakai `0xFF0`–`0xFFD`, dan
  program itu tanpa MMIO.

**Prasyarat** (pemilik), dengan mekanisme yang ada dan keadaannya hari ini:

| prasyarat | mekanisme yang ada | hari ini |
|---|---|---|
| target identity = KNOWN | IDENTITY Lapis 6: papan dan FPGA MEASURED, historis; CURRENT hanya dari sumber live | UNKNOWN — tidak ada sumber live, dan CURRENT tidak dipalsukan jadi KNOWN |
| authorization candidate = explicitly proposed | proposal ini, dan tabel 7.4 | diusulkan; 7.4 tetap DENIED |
| required communication = available and verified | port serial. `loader.hasm` tidak memancarkan apa pun sebelum byte pertama datang — ia berputar di `RX_STATUS` — jadi "loader menunggu" tidak bisa diamati tanpa mengirim | UNKNOWN — kesiapan loader dan kesiapan komunikasi |
| source program = known-good / evidence-backed | hash payload terhadap ekspektasi beku; `stale()` di `rtl/scripts/parity_board.py` menolak payload yang bergeser | KNOWN |
| expected outcome = predetermined | `NUI/board_expected.json`, dibekukan sebelum papan ditanya | KNOWN |

**Postcondition yang ditetapkan sebelumnya**, lewat mekanisme yang ada:
- *program transfer completed*: 4 + 4·7 = 32 byte tertulis. Ini satu medan,
  bukan vonis; exit code transfer tidak pernah menjadi satu-satunya bukti.
- *expected loader/program evidence present*: laporan `CYCLES=` wrapper tiba
  sebelum tenggat `deadline_s()`, dan `timed_out` false — tanda programnya
  berhenti.
- *expected deterministic output*: teks program dari byte mentah sama dengan
  `1\n2\n3\n`. Pergeseran satu byte laporan `CYCLES=` ditangani seperti di
  `src/hijaiyyah/nui/board_parity.py`.
- *no unexpected protected-state mutation*: di sisi host, berkas terlindung dan
  evidence store tetap, lewat mekanisme `confirm()` 7.7. Di sisi papan, kartu SD
  tidak teramati dari kabel; yang ada hanya fakta statis bahwa kedua program
  tidak menyentuh blok `0xFE0`.
- *evidence provenance valid*: byte mentah, hash payload, hash bitstream di
  host, dan commit, dalam bentuk rekaman P2. Tempat rekamannya diputuskan
  pemilik: evidence store eksternal (di bawah).

**Hard stop** (pemilik). Proposal berhenti tanpa tindakan bila:

```text
target identity      UNKNOWN / AMBIGUOUS
source program       not evidence-backed
required evidence    STALE
authorization        DENIED / absent
precondition         UNKNOWN
expected outcome     cannot be established
post-action evidence invalid
```

Dan tetap: `self-authorization = forbidden`.

**Sengaja tidak masuk kandidat** (pemilik): board reconfiguration,
restart/recovery, fault isolation, keep-host-awake, repository mutation,
configuration mutation, dan HFS/persistent-state mutation.

**Fakta terukur yang menentukan proposal ini hari ini.** Dalam seluruh evidence
yang ada, keadaan "loader menunggu program" hanya pernah dibuat oleh
rekonfigurasi papan:
- `rtl/scripts/parity_board.py` memanggil `configure()` —
  `openFPGALoader -b tangnano20k` dengan bitstream loader — sebelum **setiap**
  program;
- `rtl/scripts/burn_in.py` melakukannya di tiap peluncuran;
- loader menerima tepat satu program per konfigurasi.
Rekonfigurasi papan DENIED dan dikecualikan dari kandidat ini. Tanpanya,
*target identity* dan *required communication* tetap UNKNOWN. Jadi **menurut
hard stop proposal ini sendiri, `SEND_PROGRAM` berhenti hari ini**, sebelum satu
byte pun dikirim.

Satu risiko ikut terlihat. Byte yang dikirim ke papan yang tidak sedang
menjalankan loader diterima program yang sedang berjalan — shell, misalnya,
membaca tiap karakter sebagai perintah (`p`, `A`). Karena itu prasyarat
komunikasi bukan formalitas.

**Keputusan pemilik atas proposal, 1 Oktober 2026.** Tidak satu pun
membuka otorisasi mutatif.

1. **Rekonfigurasi papan tetap di luar proposal `SEND_PROGRAM`.** Tidak ada
   sinyal read-only yang membuktikan loader sedang menunggu program; keadaan
   itu selama ini baru tercipta sesudah `openFPGALoader`.

   ```text
   loader_ready = UNKNOWN
           ↓
   SEND_PROGRAM = STOP / REPORT
   ```

   Kesiapan **tidak diuji dengan mengirim byte pertama**: evidence-nya justru
   menunjukkan byte itu bisa diterima shell atau program yang sedang berjalan.
   Supaya `SEND_PROGRAM` suatu hari bisa dibuka tanpa rekonfigurasi, dibutuhkan
   **sumber evidence baru yang membuktikan kesiapan loader dan identitas
   target**. Itu pekerjaan spesifikasi tersendiri, dan tidak disimpulkan dari
   tidak adanya respons. Proposal ini karena itu **hard-stop secara benar**,
   bukan belum lengkap.
2. **Evidence pascatindakan tetap di evidence store eksternal**, lewat
   mekanisme evidence store yang sudah dipakai NUI — tidak ada berkas evidence
   di repositori, dan hasil papan tidak masuk `git`. Secara konseptual:

   ```text
   Layer 7 action evidence
           ↓
   external evidence store
           ↓
   action identity
   target identity
   program/payload hash
   pre-action evidence
   raw board response
   post-action observations
   outcome
   manifest/evidence hash
   ```

   Path atau schema baru tidak ditetapkan sekarang. Namespace atau record
   khusus untuk tindakan Lapis 7 baru dibuat sebagai pekerjaan implementasi
   ketika otorisasi tindakan memang dibuka.
3. **Program kandidat: `test_from_card`.**

   ```text
   SEND_PROGRAM
   program = test_from_card
   payload_hash = a9f0351e…
   expected_output = 1 2 3
   ```

**Status proposal sesudah keputusan:**

```text
SEND_PROGRAM
│
├─ program known                 PASS
├─ expected outcome known       PASS
├─ target identity               UNKNOWN  ← STOP
├─ loader readiness              UNKNOWN  ← STOP
└─ communication readiness      UNKNOWN  ← STOP
```

```text
SEND_PROGRAM = STOP / REPORT
Authorization = DENIED
```

Tidak ada alasan membuka `RECONFIGURE_BOARD` hanya supaya proposal
`SEND_PROGRAM` lolos. Kalau rekonfigurasi kelak hendak dibuka, ia harus menjadi
**proposal tindakan terpisah** dengan boundary, precondition, postcondition,
dan evidence-nya sendiri.

#### Readiness evidence discovery

Perintah pemilik, 1 Oktober 2026: petakan dan penuhi evidence kesiapan
`SEND_PROGRAM` — tanpa menjalankan `SEND_PROGRAM` dan tanpa membuka
rekonfigurasi — untuk menghilangkan dua `UNKNOWN` yang menyebabkan hard stop,
hanya lewat sumber observasi yang tidak mengubah papan.

```text
READINESS DISCOVERY
        ↓
read-only evidence
        ↓
target identity
loader readiness
communication readiness
        ↓
KNOWN / UNKNOWN
```

Aturan keras:

```text
UNKNOWN ≠ READY
Tidak ada byte probe
Tidak ada UART write
Tidak ada reconfiguration
Tidak ada send_program
```

Bila tidak ada sumber read-only yang membuktikan keduanya, hasilnya tetap
`UNKNOWN → HARD STOP → SEND_PROGRAM DENIED`. Tidak ada mekanisme baru yang
dibuat hanya supaya proposal menjadi `ALLOW`: yang dibuktikan adalah apakah
kesiapan memang teramati dari arsitektur yang ada.

**Terukur 1 Oktober 2026, 04:08 WIB, hanya pembacaan.** Tidak ada port yang
dibuka dan tidak ada byte yang dikirim.

| sumber yang sudah ada | yang ia buktikan |
|---|---|
| `list_ports.comports()`, yang sudah dipakai `rtl/scripts/burn_in_capture.py`; mengenumerasi tanpa membuka port | adaptor terpasang: `SIPEED` "USB Debugger", VID:PID `0403:6010`, nomor seri `2025030317`, dua antarmuka `/dev/cu.usbserial-20250303170` dan `/dev/cu.usbserial-20250303171` |
| capture P1, `cosmictera-build/burn-in/20260924T073655Z-burn-in-capture.json` | hanya nama port, `/dev/tty.usbserial-20250303171`. Nomor seri dan VID:PID adaptornya tidak pernah terekam |
| `rtl/programs/loader.hasm` | tidak satu pun instruksi keluaran: loader diam sampai byte pertama datang |
| `rtl/hcpu_mmio.v` | tidak ada register data TX; `0xFF2` hanya status TX, dan hanya dibaca. Program berbicara di UART hanya lewat `PRINT` atau `EMITS` |
| `rtl/fpga/gowin/hcpu_gowin_top.v` | wrapper hanya memancarkan laporan `CYCLES=` sesudah `halted` naik. LED papan — halted, laporan terkirim, detak — tidak terbaca host, dan "belum halt, belum ada laporan" sama untuk loader yang menunggu maupun program yang sedang berjalan |
| model keadaan Lapis 6, `NUI/hardware_state.json` | `live_sources` kosong; CURRENT UNKNOWN |
| `rtl/scripts/rack.py --detect`, yaitu `openFPGALoader --detect` | **tidak dijalankan** — lewat JTAG, alat baris DENIED. Menurut kodenya ia hanya menjawab ada tidaknya `GW2A`, bukan bitstream yang termuat dan bukan keadaan loader |

Kesimpulannya:
- **target identity**: adaptor USB papan teramati hari ini. Tetapi FPGA-nya,
  bitstream yang termuat, dan apakah FPGA itu terkonfigurasi sama sekali tetap
  **UNKNOWN**: tidak ada sumber read-only yang menautkan adaptor ke konfigurasi
  FPGA. Tautan ke papan historis juga hanya nama port.
- **loader readiness**: **UNKNOWN, dan tidak teramati di arsitektur yang ada.**
  Satu-satunya jalur dari papan ke host adalah UART, dan loader tidak
  berbicara di sana sebelum menerima.
- **communication readiness**: kanalnya ada — node perangkatnya terpasang —
  tetapi kesiapan penerimanya **UNKNOWN**. Mendengarkan kabel secara pasif
  hanya bisa membuktikan yang sedang berjalan *bukan* loader, lewat lalu lintas
  program lain; ia tidak pernah membuktikan loader siap. Karena itu ia tidak
  dijalankan.

```text
target identity          board/bitstream UNKNOWN   ← STOP
loader readiness         UNKNOWN, tidak teramati   ← STOP
communication readiness  UNKNOWN                   ← STOP
        ↓
HARD STOP dipertahankan — SEND_PROGRAM DENIED
```

Kesimpulan ini dijaga `tests/test_ai/test_nui_layer7.py`: loader tanpa
instruksi keluaran, dan wrapper yang berbicara hanya sesudah halt. Bila salah
satunya berubah, penemuan ini harus diukur ulang.

**Satu temuan alat, sudah diperbaiki.** `device_identity()` di
`rtl/scripts/burn_in_capture.py` dulu mencocokkan jalur `/dev/tty.*` yang
diberikan dengan daftar pyserial, dan di Mac ini daftar itu hanya memuat
`/dev/cu.*`. Karena itu capture P1 mencatat *the port is not in this host's
listing* walaupun adaptornya terpasang. Atas keputusan pemilik, 1 Oktober 2026,
`/dev/tty.X` dan `/dev/cu.X` kini dianggap satu perangkat. Hanya alat capture
yang berubah: rekaman P1 tetap seperti ditulis, dan kesimpulan penemuan ini
tidak bergeser, karena identitas adaptor bukan identitas FPGA.

### Proposal otorisasi: pemulihan slot Portal 8888

```text
STATUS: DIBUKA (pemilik, 3 Oktober 2026, dua keputusan)
openFPGALoader --detect     AUTHORIZED — pembacaan IDCODE saja
ISOLATE_FAULT               AUTHORIZED — tanpa penulisan UART
RESTART_PORTAL              AUTHORIZED — hanya atas gangguan yang tergolong dari rekaman lari
RECOVER_PORTAL              AUTHORIZED — hanya atas gangguan yang tergolong dari rekaman lari
Penulisan UART ke papan     AUTHORIZED — protokol Portal, sesudah muat ulang pada lari yang sama
Konfigurasi ulang papan     AUTHORIZED — bitstream Portal yang SHA-256-nya tercatat, ke SRAM
Batas ulang RESTART_PORTAL untuk satu gangguan: 3
```

Di luar baris-baris itu tabel 7.4 tidak berubah: baris umum *Konfigurasi ulang
papan (`openFPGALoader`)*, *Mengirim program ke papan*, *Restart / recovery*,
dan *Isolasi kesalahan* tetap DENIED. Flash papan tidak pernah ditulis.

Perintah pemilik, 3 Oktober 2026: bagian *memulihkan, memulai ulang,
mengisolasi kesalahan* dari tujuan Lapis 7 diselesaikan lebih dulu. Sesuai
keputusan 30 September, jalannya adalah proposal untuk tindakan tertentu —
target, prasyarat, ruang lingkup otorisasi, postcondition, evidence, dan
kondisi berhenti — dan proposal itu sendiri tidak memberi izin.

**Kenapa slot ini.** `SEND_PROGRAM` berhenti karena kesiapan loader tidak
teramati dan hanya pernah tercipta oleh rekonfigurasi. Slot Portal 8888
(`portal8888/fpga/gowin/hijaiyyah_portal8888_gowin_top.v`) berbeda dalam dua
hal yang terukur:

- **Ia menjawab.** Perintah jangkar `A` protokolnya hanya membaca: jawabannya
  putaran, ROOT, dan TAG terakhir tiap sudut, dan tidak mengubah keadaan
  Portal (`portal8888/ref/portal_uart.py`).
- **Memuat ulang membuat keadaannya diketahui.** Sesudah bitstream dimuat ke
  SRAM, Portal berada di keadaan awal: putaran 0, belum diprovisi, dan frame
  pertama di-drop sebagai belum diprovisi.

Mekanismenya sudah dua kali dijalankan di papan, 3 Oktober 2026, oleh manusia
atas perintah pemilik — muat ke SRAM, provisi, uji, 0 salah (run
`20261003T053504Z` dan `20261003T053754Z`, `portal8888/sim/EVIDENCE.md` §9).
Seperti `rtl/scripts/burn_in.py` di 7.9, itu **historical evidence**, bukan
dasar pemberian izin.

**Target**: satu Tang Nano 20K di adaptor USB yang nomor serinya tercatat,
memuat bitstream Portal yang SHA-256-nya tercatat, di port serial 115200.

**Tiga tindakan yang diusulkan.** Urutannya urutan pembukaan: yang pertama
tidak menyentuh papan sama sekali.

| tindakan | isinya | mekanisme yang sudah ada |
|---|---|---|
| `ISOLATE_FAULT` | menggolongkan gangguan, lalu berhenti mengirim frame ke papan itu. Empat golongan: adaptor tidak terdaftar; adaptor ada tetapi papan tidak terdeteksi; papan terdeteksi tetapi tidak menjawab `A`; papan menjawab dengan segel atau jangkar yang salah | `list_ports.comports()`; `openFPGALoader --detect`; pemeriksa `portal8888/ref/portal_uart.py` |
| `RESTART_PORTAL` | memuat ulang bitstream Portal ke **SRAM** | `openFPGALoader -b tangnano20k -m` |
| `RECOVER_PORTAL` | `RESTART_PORTAL`, lalu provisi lima kunci, lock, waktu, lalu skenario uji | `portal8888/scripts/portal8888_uart_test.py` |

`ISOLATE_FAULT` di sini penggolongan dan penghentian pengiriman. Ia tidak
memutus daya, tidak menyentuh host lain, dan tidak mengubah repositori.

**Yang dibuka pemilik, 3 Oktober 2026**: `openFPGALoader --detect` dan
`ISOLATE_FAULT`. Selama penulisan UART belum dibuka, `ISOLATE_FAULT` tidak
mengirim satu byte pun: dua golongan pertama ia tetapkan dari daftar adaptor
dan `--detect`, dan dua golongan terakhir hanya dari byte mentah lari yang
sudah ada di evidence store — bukan dari perintah `A` yang ia kirim sendiri.
Papan yang terdeteksi tetapi belum pernah ditanya tetap `UNKNOWN`, bukan
"diam".

**`ISOLATE_FAULT` diimplementasi**, 3 Oktober 2026, di
`src/hijaiyyah/nui/layer7_portal.py` — nama modulnya dari pemilik. Satu-satunya
perintah yang ia jalankan adalah `openFPGALoader --detect -b tangnano20k`,
persis, tanpa berkas bitstream; ia tidak menulis berkas dan tidak membuka port
serial. Rekaman lari dinilai oleh pemeriksa yang sama dengan bench dan uji
papan. Rekaman yang lebih tua dari ambang kesegaran berhenti sebagai `STALE`,
dan rekaman dengan frame tangkapan (`--pcap`) tidak dinilai ulang karena
frame-nya tidak ada di rekaman. Hasil ujinya di `NUI/LAYERS.md`, Lapis 7.

**Keputusan pemilik kedua, 3 Oktober 2026**, dalam kata-katanya sendiri:

> batas percobaan ulang 3x, tabel 7.4 sampai di buka lapis 7 bukan
> hanyanmengisolasi tapi memulihkan dan merekam syarat selesai lapis 7 ,
> layer7-freeze-2026-10-03

Dibaca sesempit yang masih memenuhinya: empat baris baru di tabel 7.4, persis
selebar butir 1 dan 2 di bawah dan dua tindakan proposal ini; batas ulang 3;
syarat selesai Lapis 7 adalah mengisolasi, memulihkan, dan merekam; dan nama
tag freeze-nya `layer7-freeze-2026-10-03`.

**`RESTART_PORTAL` dan `RECOVER_PORTAL` diimplementasi**, 3 Oktober 2026, di
modul yang sama, fungsi `recover()`:

- Pemicunya hanya gangguan yang `ISOLATE_FAULT` golongkan dari rekaman lari
  yang masih segar: `BOARD_SILENT` atau `SEAL_MISMATCH`. Papan yang belum
  pernah ditanya, adaptor yang tidak ada, dan papan yang tidak terdeteksi
  berhenti tanpa tindakan.
- Perintah muatnya `openFPGALoader -b tangnano20k -m <bitstream>`, dan hanya
  bila SHA-256 berkasnya sama dengan yang tercatat di
  `portal8888/sim/EVIDENCE.md` §9.
- Tidak ada byte yang ditulis sebelum pemuat berakhir 0 pada lari yang sama.
  Sesudah itu perintah `A`; putaran 0 dan ROOT nol berarti Portal di keadaan
  awal. `RECOVER_PORTAL` lalu menjalankan skenario skrip papan, dinilai
  pemeriksa yang sama.
- Port dibuka dengan kunci eksklusif pyserial; port yang tidak bisa dibuka
  sendirian berhenti tanpa tindakan. Kunci itu hanya melihat proses lain yang
  memakai kunci yang sama.
- Tenggat jawaban 5 detik — tenggat serial skrip papan yang sudah ada, dipakai
  apa adanya; pemilik belum menetapkan angka lain.
- **Merekam**: tiap percobaan, kode keluar pemuat, jawaban `A`, byte mentah
  skenario, dan vonisnya ditulis ke direktori evidence di luar repositori
  (K-11) yang disebut pemanggilnya. Batas ulang dihitung dari rekaman itu,
  jadi tidak bisa dilewati dengan memanggil ulang; gangguan yang sudah terjawab
  tidak memicu pemulihan kedua.
- Kunci yang diprovisi adalah kunci laboratorium `portal8888/ref/portal_ref.py`,
  yang ada di repositori publik. Pemulihan ini memulihkan slot ke keadaan uji,
  bukan ke kunci rahasia.

**Terukur di papan satu kali**, 3 Oktober 2026, atas perintah pemilik:
gangguan `SEAL_MISMATCH` yang dibuat dengan sengaja dipulihkan pada percobaan
pertama dan direkam di luar repositori. Angkanya di `NUI/LAYERS.md`, Lapis 7.

**Yang dibuka di tabel 7.4**, dan hanya pemilik yang membukanya (7.11):

1. *Konfigurasi ulang papan* — terbatas pada bitstream Portal yang SHA-256-nya
   tercatat, ke SRAM. Menulis flash papan tetap di luar. **Dibuka**,
   3 Oktober 2026.
2. *Menulis ke UART papan* — terbatas pada protokol Portal, dan hanya sesudah
   `RESTART_PORTAL` berhasil pada lari yang sama, atau perintah `A` saja
   terhadap papan yang identitas bitstream-nya sudah KNOWN dari lari itu.
   **Dibuka**, 3 Oktober 2026.
3. `openFPGALoader --detect` — hanya membaca IDCODE lewat JTAG. **Dibuka**,
   3 Oktober 2026, sebagai pembacaan; `openFPGALoader` dengan berkas bitstream
   tetap baris *Konfigurasi ulang papan*, DENIED.

**Prasyarat**, dengan mekanisme yang ada dan keadaannya hari ini:

| prasyarat | mekanisme yang ada | hari ini |
|---|---|---|
| target identity = KNOWN | nomor seri adaptor dari `list_ports.comports()`; IDCODE dari `--detect` | adaptor dan IDCODE terbaca; bitstream yang termuat tetap UNKNOWN tanpa muat ulang |
| bitstream = evidence-backed | SHA-256 berkas `.fs` terhadap yang tercatat di `portal8888/sim/EVIDENCE.md` §9 | KNOWN untuk bitstream yang diuji di papan; bitstream yang dibangun ulang harus diukur ulang |
| required communication | port serial tidak sedang dipegang proses lain | kunci eksklusif pyserial saat port dibuka |
| expected outcome = predetermined | jawaban `A` sesudah muat ulang: putaran 0, ROOT nol; skenario `portal_uart.scenario()` | KNOWN |
| pemicu = teramati | tidak ada jawaban `A` dalam tenggat, atau pemeriksa menemukan mismatch | KNOWN sebagai mekanisme; tenggat 5 detik dari skrip papan, belum ditetapkan pemilik |
| authorization | tabel 7.4 | AUTHORIZED untuk keenam baris slot Portal (pemilik, 3 Oktober 2026) |

**Postcondition yang ditetapkan sebelumnya:**

- `ISOLATE_FAULT`: golongan gangguan, dengan byte mentah atau keluaran alat
  yang mendasarinya, tercatat; tidak ada byte yang dikirim ke papan sesudah
  golongan ditetapkan.
- `RESTART_PORTAL`: pemuat berakhir tanpa galat — satu medan, bukan vonis —
  **dan** jawaban `A` dalam tenggat menunjukkan putaran 0 dan ROOT nol.
- `RECOVER_PORTAL`: skenario selesai dengan 0 mismatch oleh pemeriksa yang
  sama dengan bench; byte mentah jawaban tersimpan.
- Untuk ketiganya: berkas terlindung dan evidence store tetap, lewat mekanisme
  `confirm()` 7.7; evidence di evidence store eksternal, bukan di `git`.

**Hard stop.** Tanpa tindakan bila:

```text
target identity      UNKNOWN / AMBIGUOUS
bitstream            hash tidak cocok dengan yang tercatat
port serial          dipegang proses lain
authorization        DENIED / absent
pemicu               tidak teramati (tidak ada gangguan yang tergolong)
percobaan            melewati batas ulang
post-action evidence invalid
```

Dan tetap: `self-authorization = forbidden`.

**Batas ulang**: paling banyak tiga `RESTART_PORTAL` berturut-turut untuk satu
gangguan — ditetapkan pemilik, 3 Oktober 2026. Sesudah itu STOP / REPORT.
Angkanya dibaca kode dari blok status proposal ini (R1).

**Yang harus dibaca bersama proposal ini:**

- **Pemulihan memutus rantai.** Kunci, PREV, ROOT, dan jangkar tinggal di SRAM;
  memuat ulang menghapusnya. Catatan sesudah pemulihan adalah rantai baru.
  Jangkar terakhir sebelum gangguan hanya terselamatkan bila sempat terbaca,
  dan pemulihan tidak boleh dilaporkan sebagai kelanjutan rantai lama.
- **Kunci diprovisi host**, jadi pemulihan otonom berarti kunci berada di
  host yang menjalankannya. Itu batas laboratorium yang sama dengan §9.
- **Ini pemulihan slot Portal, bukan sistem komputasi utama.** Tidak ada sisi
  host di repositori yang dipulihkan olehnya.
- **Byte ke papan yang tidak menjalankan Portal** diterima program yang sedang
  berjalan — risiko yang sama dengan `SEND_PROGRAM`. Karena itu penulisan UART
  hanya sesudah muat ulang pada lari yang sama.
- **`confirm()` masih mempercayai `expected` apa adanya**, dan berkas yang
  hilang masih memicu exception. Keduanya belum ditutup. `recover()` tidak
  memakai `confirm()`: ia membandingkan sendiri berkas terlindung dan rekaman
  lama sebelum dan sesudah tindakan.

**Sengaja tidak masuk proposal ini**: menulis flash papan, sepuluh perintah
host lama, menjaga host tetap terjaga, mutasi repositori atau konfigurasi,
`SEND_PROGRAM`, dan slot selain Portal.

### Proposal otorisasi: pemulihan satu layanan di VM Linux

```text
STATUS: DIUSULKAN — adendum pasca-freeze, 3 Oktober 2026
Authorization: DENIED untuk semua tindakan di bawah
Tabel 7.4 tidak berubah. Proposal ini tidak memberi izin apa pun.
```

Arah pemilik, 3 Oktober 2026, dalam kata-katanya: "1. sistem linux kemudian
sistem window dst". Lapis 7 sudah mengisolasi, memulihkan, dan merekam untuk
slot Portal 8888 — bagian dari CosmicTera sendiri. Proposal ini untuk sistem
pertama **di luar** CosmicTera yang dijaga: VM Linux yang sudah diamati
Lapis 5. Ditulis sesudah tag `layer7-freeze-2026-10-03`, jadi ia adendum, dan
commit-nya terpisah.

**Yang sudah ada dan terukur.** VM `cosmictera-layer5` (Ubuntu Server 24.04
ARM64 di bawah Lima) berjalan dan diamati sebelas kolektor baca-saja;
evidence-nya di luar repositori, dengan aturan kesegaran dari
`NUI/spec/layer5_collectors.json`. Membaca satu unit sudah diizinkan: katalog
`READ SERVICE` adalah `systemctl status <unit>`, dan jurnal satu unit adalah
bentuk K-4. Yang tidak ada: tindakan apa pun. `systemctl start`,
`systemctl stop`, `kill`, `reboot`, dan enam perintah lain ada di daftar belum
diizinkan (`NUI/LAYERS.md`, Lapis 5), dan `sudo` tidak diizinkan (K-12).

**Target yang diusulkan**: satu unit, `cron.service`, di instance uji
`cosmictera-layer5-uji` lebih dulu, baru di `cosmictera-layer5`. Alasannya:
unit itu ada di observasi `20260930T154243Z-collectors`; ia bukan jalur
perintah (`ssh.service`), bukan jurnal, dan bukan jaringan; dan menghentikannya
tidak mengganggu unit lain. Unit dan instansinya keputusan pemilik.

**Tiga tindakan yang diusulkan**, dalam urutan pembukaan:

1. *Menggolongkan gangguan layanan* — hanya membaca. Empat golongan: VM tidak
   menjawab; unit aktif (tanpa gangguan); unit tidak aktif; unit gagal.
   Sumbernya `systemctl status <unit>` dan jurnal unit itu, lewat `observe()`
   dan pagarnya yang sudah ada.
2. *Memulai ulang satu unit* — `sudo systemctl start <unit>`, argv persis itu,
   hanya untuk unit yang disebut, dan hanya atas gangguan "tidak aktif" atau
   "gagal" yang tergolong dari observasi yang masih segar.
3. *Merekam* — tiap percobaan, exit code, stdout, stderr, dan pembacaan
   sesudahnya, di evidence store di luar repositori.

**Yang harus dibuka pemilik** (7.11), dan tidak satu pun dibuka di sini:

- `systemctl start`, terbatas pada satu unit yang disebut;
- `sudo`, terbatas pada argv itu saja. Ini membalik sebagian K-12, jadi
  keputusannya tersendiri;
- kelas outcome baru. Hari ini hanya exit 0 yang `PASS`, dan `systemctl status`
  atas unit yang tidak aktif keluar dengan kode bukan nol, jadi terbaca
  `collector_error`. Supaya "unit tidak aktif" bisa digolongkan, kontrak
  outcome perlu satu kelas lagi. Kode keluarnya belum saya ukur di VM ini;
- batas ulang. Untuk Portal pemilik menetapkan 3; angka yang sama diusulkan.

**Prasyarat**: identitas `(vm_name, run_id)` tunggal; observasi segar;
provenance manifest sah; unit yang disebut sama dengan unit di otorisasi;
gangguan tergolong.

**Postcondition yang ditetapkan sebelumnya**: `systemctl status <unit>`
sesudah tindakan menunjukkan unit aktif, dari observasi baru; exit code
perintah mulai hanya satu medan, bukan vonis; berkas terlindung dan rekaman
lama tidak berubah.

**Hard stop.** Tanpa tindakan bila:

```text
target identity      UNKNOWN / AMBIGUOUS
observasi            STALE
unit                 bukan unit yang diotorisasi
gangguan             tidak tergolong, atau VM tidak menjawab
authorization        DENIED / absent
percobaan            melewati batas ulang
post-action evidence invalid
```

Dan tetap: `self-authorization = forbidden`.

**Yang harus dibaca bersama proposal ini:**

- **Gangguan ujinya dibuat manusia.** `systemctl stop` tetap DENIED bagi NUI;
  menghentikan unit untuk uji adalah langkah laboratorium atas perintah
  pemilik, seperti gangguan Portal 3 Oktober 2026.
- **VM yang mati tidak dipulihkan olehnya.** Menyalakan VM (`limactl start`)
  tidak diusulkan; "VM tidak menjawab" berhenti dan melapor.
- **Ini VM di Mac, bukan sistem produksi.** Yang dibuktikan adalah rantai
  lihat → putuskan → bertindak → rekam pada satu layanan Linux.
- **Windows belum punya apa pun di repositori**: tidak ada host, tidak ada
  kolektor, tidak ada daftar izin. Ia butuh keputusan host sendiri, seperti
  keputusan 21 September 2026 untuk Linux, sebelum proposal apa pun.

**Sengaja tidak masuk proposal ini**: `systemctl stop`, `kill`, `reboot`,
`shutdown`, perintah `docker`, `rm`, `mv`, unit selain yang disebut, menyalakan
atau mematikan VM, Mac host, dan Windows.

#### Keputusan pemilik, 6 Oktober 2026 — Linux, sebelum `RESTART_SERVICE`

Empat keputusan, dicatat sebelum evidence Linux dipakai untuk membuka tindakan
apa pun:

| keputusan | status |
|---|---|
| `cosmictera-layer5-uji` dibuat kembali sebagai VM laboratorium | **Disetujui** |
| `cron.service` sebagai target layanan pertama | **Disetujui** |
| `UNIT_INACTIVE` dan `UNIT_FAILED` sebagai klasifikasi lokal Lapis 7 | **Disetujui** |
| `ISOLATE_SERVICE` sebagai tindakan baca-saja di `src/hijaiyyah/nui/layer7_linux.py` | **Disetujui** |

Batasnya, kata pemilik:

```text
Lapis 5 frozen
        ↓
observasi systemctl status
        ↓
Lapis 7 mengklasifikasikan:
  active         → kondisi sehat
  inactive       → UNIT_INACTIVE
  failed         → UNIT_FAILED
  tidak menjawab → VM_UNREACHABLE
```

`UNIT_INACTIVE` dan `UNIT_FAILED` **tidak** ditambahkan ke kontrak outcome
Lapis 5. Di Lapis 5, `systemctl status` atas unit yang tidak aktif tetap
terbaca `collector_error`.

**Namespace evidence.** `~/cosmictera-layer5/linux-service/<waktu>/` adalah
evidence Lapis 7 di luar repositori, **bukan** bagian evidence store Lapis 5 dan
bukan bukti yang mengubah Lapis 5.

**Alat ukur dan provenance-nya.** Alatnya `portal8888/build/diag/measure_unit.py`,
di folder yang di-gitignore. Ia tidak dijadikan source repositori hanya karena
dipakai mengukur, tetapi provenance-nya dicatat di sini supaya evidence dapat
diaudit ulang:

- SHA-256 `5810582e488c78f71393cd4ead795a5007397b689f4dbc76ef01585806966f8a`,
  1.559 byte;
- argv tetap `systemctl status cron.service` di `cosmictera-layer5-uji`, diizinkan
  lewat `layer5.guard` (entri `systemctl status`), dijalankan
  `limactl shell <vm> -- <argv>` dengan `LIMA_HOME` dari `layer5.host()`;
- tiap lari menulis `record.json`, `stdout.txt`, dan `stderr.txt` ke direktori
  bercap waktu, dan `record.json` memuat label, VM, argv, entri izin, waktu
  mulai, exit code, outcome Lapis 5, serta SHA-256 stdout dan stderr.

**Yang terukur sampai keputusan ini:**

| lari | `Active:` | exit | outcome Lapis 5 | SHA-256 stdout |
|---|---|---:|---|---|
| `20261006T151343Z-measure-active` | `active (running)` | 0 | `PASS` | `4398ac39764f…` |
| `20261006T151947Z-measure-inactive` | `inactive (dead)` | 3 | `collector_error` | `4c068df78915…` |
| `20261006T153611Z-measure-failed` | `failed (Result: exit-code)` | 3 | `collector_error` | `61a942fffa2a…` |
| `20261006T153714Z-measure-inactive-after-reset` | `inactive (dead)` | 3 | `collector_error` | `9b26eef8e057…` |
| `20261006T153920Z-measure-vm-missing` | — (stdout kosong) | 1 | `collector_error` | `e3b0c44298fc…` |
| `20261006T153928Z-measure-vm-stopped` | — (stdout kosong) | 1 | `collector_error` | `e3b0c44298fc…` |
| `20261006T154021Z-measure-active-after-boot` | `active (running)` | 0 | `PASS` | `4f60abe00643…` |

Yang dibaca dari tujuh ukuran itu, dan tidak dari kebiasaan systemd:

- **Tidak aktif dan gagal sama-sama keluar dengan kode 3.** Kode keluar tidak
  membedakan keduanya; baris `Active:` yang membedakan. `UNIT_INACTIVE` ≠
  `UNIT_FAILED`.
- **`UNIT_FAILED` yang terukur satu bentuk saja**: `ExecStart` keluar bukan nol
  dengan `Restart=no` (`Result: exit-code`). Unit aslinya `Restart=on-failure`,
  jadi keadaan itu dibuat operator dengan drop-in sementara
  `/run/systemd/system/cron.service.d/lab.conf` (`ExecStart=/bin/false`), lalu
  dihapus, `daemon-reload`, `reset-failed`. Kegagalan karena batas waktu atau
  sinyal tidak terukur.
- **Baris `Main PID` tidak dapat dipakai.** Sesudah `reset-failed`, unit yang
  `inactive (dead)` masih menampilkan `status=1/FAILURE` proses terakhirnya.
- **VM yang tidak menjawab punya dua bentuk terukur**, keduanya dari `limactl`
  sendiri di stderr dengan kode 1 dan stdout kosong: `instance … is stopped`
  (VM uji dihentikan dengan `limactl stop`, lalu dinyalakan lagi) dan
  `instance … does not exist` (nama yang tidak ada). Alat ukur untuk nama VM
  lain adalah salinan `portal8888/build/diag/measure_vm.py`, SHA-256
  `529d874cdb8cd0ec7a7543e165469d3684382452dd77afe44ee80dc71f1b83b5`; bedanya
  hanya nama VM dibaca dari argumen.
- **Jurnal unit bukan sumber.** `journalctl -b -u cron.service -n 200
  --no-pager` lolos pagar, tetapi `unavailable_due_to_permissions` (K-12).
  Penggolongan bersandar pada `systemctl status` saja.
- Sesudah VM uji dinyalakan lagi, unitnya `active (running)`: ia `enabled`.

Menghentikan unit, drop-in, dan `limactl stop`/`start` adalah langkah
laboratorium — tangan operator dan, untuk `limactl`, perintah pemilik — bukan
tindakan NUI.

**`ISOLATE_SERVICE` — AUTHORIZED, baca-saja** (pemilik, 6 Oktober 2026). Kata
pemilik: *"baris AUTHORIZED baru khusus `ISOLATE_SERVICE`. Saya tidak setuju
menyembunyikan tindakan bernama di bawah 'Observasi / read-only'."* Barisnya di
tabel 7.4 di atas; implementasinya `src/hijaiyyah/nui/layer7_linux.py`.

```text
argv        limactl shell <VM uji> -- systemctl status cron.service
pagar       layer5.guard, sebelum dijalankan; tanpa shell, tanpa sudo
target      VM uji dari spec Lapis 5 (`test_instance`) dan `cron.service` saja
hasil       NO FAULT | FAULT ISOLATED (satu dari tiga golongan) | STOP / REPORT
may_act     false, selalu
```

| yang terbaca | golongan |
|---|---|
| `Active: active (running)`, kode 0 | tanpa gangguan |
| `Active: inactive (dead)`, kode 3 | `UNIT_INACTIVE` |
| `Active: failed (Result: exit-code)`, kode 3 | `UNIT_FAILED` |
| `limactl`: instance `is stopped` atau `does not exist`, kode 1, stdout kosong | `VM_UNREACHABLE` |
| apa pun selain itu | `UNKNOWN` → STOP / REPORT |

Hanya bentuk yang terukur yang diberi nama. Baris `Active:` dengan kata lain,
kode keluar yang tidak cocok dengan barisnya, stderr yang tidak kosong, status
unit lain, unit yang tidak ada, dan diam melewati batas waktu semuanya
`UNKNOWN`. VM atau unit selain yang disebut baris ini `UNAUTHORIZED ACTION`.
`cosmictera-layer5`, instance utama, **bukan** target.

**Syarat sebelum `RESTART_SERVICE`.** Evidence `ACTIVE` dan `INACTIVE` yang ada
**tidak** membukanya. Yang masih dibutuhkan:

1. pengukuran `UNIT_FAILED` yang benar-benar terjadi — **ada**, 6 Oktober 2026;
2. implementasi dan tes `ISOLATE_SERVICE` — **ada**, `tests/test_ai/test_nui_layer7_linux.py`;
3. pencatatan keempat keputusan ini di dokumentasi Lapis 7 dan `AGENTS.md`;
4. gerbang untuk perubahan itu.

Sesudah itu, keputusan **terpisah** untuk membuka `RESTART_SERVICE` —
`sudo systemctl start cron.service`, hanya `cron.service`, paling banyak 3
ulang. Keputusan itu ada di bawah.

#### Keputusan pemilik, 6 Oktober 2026 — `RESTART_SERVICE`

Dibuka sesudah `59a7b0b` (`ISOLATE_SERVICE`) dan gerbang penuhnya. Kata
pemilik: *"Saya tetapkan kontrak `RESTART_SERVICE` sekarang, tetapi belum
mengizinkan eksekusi tindakan di VM. Implementasi, test, commit, dan gate harus
selesai lebih dulu."* Lapis 7 Linux bergerak dari *observe → classify* ke
*observe → classify → satu tindakan pemulihan yang sangat sempit → verify →
stop*.

```text
tindakan    RESTART_SERVICE
VM          cosmictera-layer5-uji
argv        sudo systemctl start cron.service
gangguan    UNIT_INACTIVE saja
berhasil    ISOLATE_SERVICE sesudah tindakan membaca Active: active (running)
```

Batas percobaan RESTART_SERVICE untuk satu gangguan: 3

Enam ketetapan pemilik, dan cara masing-masing dipegang:

1. **Baris 7.4 sendiri, AUTHORIZED.** Tabel menjadi 17 baris: 10 AUTHORIZED,
   7 DENIED. Baris umum "10 perintah host lama", yang memuat
   `systemctl start`, **tetap DENIED**: yang dibuka satu argv di satu VM.
2. **`sudo` dibuka; batasnya ditegakkan NUI, bukan OS.** Ini membalik
   sebagian K-12 untuk argv ini saja. NUI membangun argv itu sendiri, utuh, dan
   tidak menerima unit atau perintah dari masukan bebas; pagar Lapis 5 tetap
   menolak `sudo` dan `systemctl start`, dan tidak ditanya untuk argv ini —
   izinnya baris 7.4 ini, bukan daftar izin Lapis 5. NUI tidak menyentuh
   `sudoers`.

   **Diralat pemilik, 7 Oktober 2026.** Ketetapan ini semula meminta `sudo`
   disempitkan juga di OS VM uji, dengan satu aturan `sudoers` yang dipasang
   tangan operator. Aturan itu **tidak dipasang**, dan `sudoers` VM uji
   **tidak diubah**. Yang terukur hari itu, dengan `sudo -l -U lima` dari
   tangan operator di dalam VM uji:

   Pada VM uji ini, akun `lima` memiliki `(ALL) NOPASSWD: ALL`. Karena itu
   batas perintah `RESTART_SERVICE` ditegakkan oleh argv tetap dan guard NUI,
   bukan oleh pembatasan sudoers tingkat OS. Ini merupakan batasan lab, bukan
   model least-privilege OS yang kuat.

   Pemilik memilih tidak mengubahnya untuk lari pertama: mengganti aturan umum
   itu dapat menghilangkan kemampuan operator membuat gangguan, atau mengubah
   perilaku Lima dan cloud-init, dan keduanya belum diukur. Direktori aturan
   VM uji memuat dua berkas, `90-cloud-init-users` (135 byte) dan `README`;
   **isi berkas pertama belum dibaca**, jadi sumber hak itu belum dinyatakan.
3. **Tiga percobaan, total** — bukan tiga ulang sesudah yang pertama. Tidak ada
   percobaan keempat. Angkanya dibaca dari baris di atas (R1) dan dihitung dari
   rekaman yang tersimpan, lintas lari; satu gangguan adalah satu masa
   `inactive (dead) since …`.
4. **`UNIT_INACTIVE` saja.** `UNIT_FAILED` digolongkan dan direkam, **tidak**
   dimulai ulang: kegagalan yang terukur adalah unit yang `start`-nya memang
   gagal, dan memulainya lagi tidak memperbaiki apa pun. `VM_UNREACHABLE` dan
   `UNKNOWN` berhenti dengan cara yang sama.
5. **Berhasil = pembacaan sesudahnya**, bukan kode keluar `start`. `start`
   yang keluar 0 dengan unit yang belum `active (running)` adalah percobaan
   yang belum berhasil, dan pencacah maju.
6. **Gangguan dibuat manusia.** `systemctl stop` tetap tangan operator. NUI
   tidak mendapat `stop`, `kill`, `reboot`, atau bentuk sabotase lain.

```text
UNIT_INACTIVE
      │
      ▼
RESTART_SERVICE percobaan 1
      ├── active (running) → SUCCESS
      └── masih UNIT_INACTIVE → percobaan 2 → percobaan 3 → FAILED_RECOVERY

UNIT_FAILED / VM_UNREACHABLE / UNKNOWN → tanpa start → rekam → STOP / REPORT
```

Dua hal yang dipegang implementasinya di luar enam ketetapan itu, keduanya ke
arah berhenti:

- Bila pembacaan sesudah sebuah percobaan **bukan** `UNIT_INACTIVE` dan bukan
  aktif — misalnya unit menjadi `failed` — ia berhenti di situ dan tidak
  mencoba lagi, sesuai ketetapan 4.
- Tanpa tempat di luar repositori untuk menyimpan rekamannya, tidak ada yang
  dijalankan. Rekaman ditulis sesudah tiap langkah, di
  `~/cosmictera-layer5/linux-service/<waktu>-restart/`.

**Satu lari di VM uji, 7 Oktober 2026 — `SUCCESS` pada percobaan 1.** Atas
perintah pemilik, sesudah `c167893` dan gerbang penuhnya; jam di bawah UTC,
6 Oktober. Gangguannya dibuat tangan operator
(`sudo systemctl stop cron.service`, 19:31:28); tindakannya dijalankan
implementasi NUI (`--restart`), bukan tangan.

```text
RESTART_SERVICE    perangkat keras: tidak — lab VM Linux
VM                 cosmictera-layer5-uji
gangguan           UNIT_INACTIVE — Active: inactive (dead) since 19:31:28, keluar 3
percobaan          1 dari 3 — keluar 0, stdout dan stderr kosong
pembacaan sesudah  Active: active (running), keluar 0, PID 1518 (sebelumnya 680)
jeda teramati      46 ms sesudah unit mulai
hasil              SUCCESS
```

Rekaman mentahnya di luar git, di
`~/cosmictera-layer5/linux-service/20261006T193152Z-restart/`; SHA-256
`record.json`-nya
`52ea59d60fecd6944b8767e1dc28eaef3ab3a0b538536a8fa406864c9f9da125`.

Yang **tidak** dibuktikan lari itu:

- Percobaan 2 dan 3 **belum pernah dijalankan di VM**, dan `FAILED_RECOVERY`
  **belum pernah terjadi di VM**.
- Jalur "pembacaan sesudah bukan aktif dan bukan `UNIT_INACTIVE` → berhenti"
  **belum pernah terjadi di VM**. Ketiga jalur itu baru dipegang tes terhadap
  model VM.
- Unit terbaca hidup 46 ms sesudah mulai. **Tidak ada bukti ia tetap hidup
  sesudah itu.**
- Satu lari atas satu gangguan buatan tangan. **Ini bukan validasi produksi.**
- Akun `lima` di VM itu memiliki `(ALL) NOPASSWD: ALL`: batas perintahnya
  tetap di NUI, bukan least-privilege sudoers OS.

Keluaran `sudo systemctl start cron.service` kini terukur **sekali**: keluar
0, tanpa keluaran. Implementasinya tetap tidak bergantung pada keluaran itu.
Lari kedua bukan bagian dari tonggak ini; menguji ulang-coba dan
`FAILED_RECOVERY` di VM adalah pekerjaan terpisah atas perintah pemilik.

## 7.5 Authorization Boundary

```text
STATUS: DEFINED — least privilege + fail-closed
DECIDED BY: pemilik, 30 September 2026
```

**Diizinkan secara otonom:**

| | izin | mekanisme yang sudah ada |
|---|---|---|
| 1 | Membaca observasi melalui mekanisme Lapis 5 yang sudah ada | `layer5.guard`, `layer5.observations`, `layer5.latest` |
| 2 | Membaca dan mengevaluasi state hardware Lapis 6 | `hardware_state`, `python3 -m hijaiyyah.nui.knowledge hardware …` |
| 3 | Menghitung delta antar-run | `layer5.delta` |
| 4 | Memvalidasi provenance, freshness, manifest hash, dan `outcomes` | verifikasi manifest `layer5`, `layer5.freshness`, `layer5.outcome` |
| 5 | Menjalankan fungsi verifikasi/read-only yang tidak mengubah host, repository, FPGA, program, atau persistent state | `--verify` modul NUI yang sudah ada |
| 6 | Menghasilkan evidence baru dari observasi tersebut | `layer5.record`, ke evidence store di luar repositori (K-11) |
| 7 | Membaca identitas papan lewat JTAG (pemilik, 3 Oktober 2026) | `openFPGALoader --detect` — tanpa berkas bitstream |
| 8 | Menggolongkan gangguan slot Portal 8888 dan berhenti mengirim (pemilik, 3 Oktober 2026) | `ISOLATE_FAULT`, akhir 7.4 — tanpa penulisan UART |
| 9 | Memuat bitstream Portal 8888 yang SHA-256-nya tercatat ke SRAM (pemilik, 3 Oktober 2026) | `openFPGALoader -b tangnano20k -m` — flash tidak ditulis |
| 10 | Menulis protokol Portal 8888 ke UART sesudah muat ulang pada lari yang sama (pemilik, 3 Oktober 2026) | `portal8888/ref/portal_uart.py`, `exchange()` skrip papan |
| 11 | Memulai ulang slot Portal 8888 atas gangguan yang tergolong, paling banyak 3 kali (pemilik, 3 Oktober 2026) | `RESTART_PORTAL`, akhir 7.4 |
| 12 | Memulihkan slot Portal 8888 dan merekam hasilnya di luar repositori (pemilik, 3 Oktober 2026) | `RECOVER_PORTAL`, akhir 7.4 |
| 13 | Menggolongkan gangguan `cron.service` di VM uji Linux, tanpa tindakan (pemilik, 6 Oktober 2026) | `ISOLATE_SERVICE`, akhir 7.4 — `systemctl status` lewat `layer5.guard` |
| 14 | Memulai `cron.service` di VM uji Linux atas `UNIT_INACTIVE`, paling banyak 3 percobaan, dan merekamnya (pemilik, 6 Oktober 2026) | `RESTART_SERVICE`, akhir 7.4 — `sudo systemctl start cron.service`, argv tetap |

**Tetap tidak diizinkan — DENIED pada Lapis 7 awal:**

- konfigurasi ulang papan di luar izin 9;
- mengirim program ke papan;
- mengubah persistent state HFS/SD;
- restart atau recovery otomatis di luar slot Portal 8888 (izin 11 dan 12) dan
  `RESTART_SERVICE` VM uji Linux (izin 14);
- isolasi kesalahan di luar `ISOLATE_FAULT` slot Portal 8888 (izin 8) dan
  `ISOLATE_SERVICE` VM uji Linux (izin 13);
- menjaga host tetap terjaga;
- seluruh 10 perintah host yang pada Lapis 5 berstatus belum diizinkan;
- tindakan jaringan eksternal;
- perubahan repository;
- perubahan konfigurasi sistem;
- tindakan apa pun yang memerlukan pencabutan read-only guard Lapis 5, K-4, atau
  K-12 — kecuali satu argv izin 14, yang membalik K-12 untuk dirinya saja.

**Aturan yang dikunci:**

> Lapis 7 tidak boleh memberikan dirinya sendiri otorisasi, memperluas allowlist,
> atau mengubah authorization boundary.

**Eskalasi.** Bila keadaan menuntut tindakan di luar batas ini:

```text
OBSERVATION
    ↓
EVALUATION
    ↓
ACTION REQUIRED
    ↓
NOT AUTHORIZED
    ↓
STOP / REPORT
```

Yang **dilarang**:

```text
ACTION REQUIRED
    ↓
NUI decides to authorize itself
```

Jadi NUI sudah punya operasi otonom di wilayah read/verify/evidence, dan sejak
3 Oktober 2026 satu wilayah mutatif yang sempit: slot Portal 8888. Urutan itu
disengaja, supaya lapisan pertama dapat diuji sebelum ada kemampuan mutasi
sistem.

## 7.6 Pre/Post-State Contract

**Prasyarat** sebelum tindakan yang sudah masuk allowlist. Minimal harus ada:

| prasyarat | nilai | mekanisme yang sudah ada |
|---|---|---|
| target identity | known | `(vm_name, run_id)` (K-16); `layer5.latest` menuntut VM-nya |
| observation provenance | valid | verifikasi manifest: ukuran dan SHA-256 tiap berkas evidence |
| evidence freshness | current | aturan kesegaran di `NUI/spec/layer5_collectors.json` |
| required state | known | jawaban `known` dari sumber 7.3; hardware CURRENT hanya dari sumber live |
| required rule coverage | covered | cakupan fungsi RTL Lapis 6 dan kedua auditnya |
| authorization | allowed | 7.5 |

**Kondisi yang memaksa tidak bertindak:**

```text
UNKNOWN
STALE
NOT_COVERED
KNOWN_DISCREPANCY
INVALID PROVENANCE
AMBIGUOUS TARGET
UNAUTHORIZED ACTION
```

Semuanya memakai mekanisme yang sudah ada, bukan sistem klasifikasi baru:
- `UNKNOWN`, `STALE`, `NOT_COVERED`, dan `KNOWN_DISCREPANCY` dirinci di 7.8;
- `INVALID PROVENANCE` adalah observasi yang ditolak verifikasi manifest;
- `AMBIGUOUS TARGET` **hanya untuk ambiguitas identitas** (pemilik,
  30 September 2026): `(vm_name, run_id)` tidak menunjuk tepat satu
  target/evidence. Label ini tidak dipakai untuk state hardware opaque,
  subsistem tanpa fungsi, atau ketidaksesuaian HISAB;
- `UNAUTHORIZED ACTION` adalah apa pun di luar 7.5.

Untuk hardware, keadaan CURRENT hanya datang dari sumber live. Hari ini tidak ada
sumber live, jadi keadaan hardware sebelum tindakan tidak dapat diketahui.

**Keputusan operasional — DECIDE, dry-run.** Perintah pemilik, 30 September
2026: NUI bergerak dari

```text
READ
  ↓
EVALUATE
  ↓
GATE
  ↓
DECIDE
  ↓
EVIDENCE / REPORT
```

dengan DECIDE menghasilkan keputusan operasional yang eksplisit **tanpa
memperoleh kewenangan eksekusi**. Setiap kandidat tindakan dari 7.4
menghasilkan salah satu dari `ALLOW`, `DENY`, atau `STOP / REPORT`. Untuk
keadaan sekarang:

```text
read/evidence actions     → ALLOW
mutative actions          → DENY
UNKNOWN / STALE           → STOP / REPORT
NOT_COVERED               → STOP / REPORT
KNOWN_DISCREPANCY         → STOP / REPORT
UNAUTHORIZED ACTION       → STOP / REPORT
AMBIGUOUS TARGET          → STOP / REPORT
```

**ALLOW berarti "lolos kontrak untuk tindakan", bukan berarti tindakannya
dieksekusi.** Eksekusi tetap berada di caller dan dibatasi authorization
boundary 7.5. Modulnya `src/hijaiyyah/nui/layer7_decision.py`, terpisah dari
`src/hijaiyyah/nui/layer7.py`. Ia hanya menerima hasil kontrak dan menghasilkan
decision record deterministik. Tidak ada subprocess, mutasi berkas, perintah
papan, restart, pengiriman program, atau self-authorization. Hasil ujinya di
`NUI/LAYERS.md`, Lapis 7.

Tetap tidak dibuka: board reconfiguration, send program, restart/recovery,
fault isolation, keep host awake, dan repository/config mutation.
`rtl/scripts/burn_in.py` tidak dijadikan allowlist.

*Tiga penerapan DECIDE disetujui pemilik, 30 September 2026:*
- **DENY didahulukan.**

  ```text
  candidate action
        ↓
  authorization check
        ├── DENIED → DENY / UNAUTHORIZED ACTION
        └── ALLOWED → evaluasi kontrak berikutnya
  ```

  Evidence `UNKNOWN`, `STALE`, atau lainnya tidak mengubah tindakan yang sejak
  awal tidak diotorisasi menjadi `STOP` biasa atau `ALLOW`.
- **`reason` sebuah DENY membawa `UNAUTHORIZED ACTION`**: kegagalan otorisasi
  dibedakan dari kegagalan evidence.
- **Masukan yang bukan hasil kontrak kandidat → STOP / UNKNOWN**, termasuk hasil
  `confirm()`. Lapis keputusan tidak memperlakukan keluaran evaluator sebagai
  kandidat tindakan secara implisit.

*Perluasan otorisasi: belum ada alasan untuk memintanya* (pemilik, hari yang
sama). Rantai READ → EVALUATE → GATE → DECIDE → EVIDENCE / REPORT sudah
bekerja tanpa kewenangan mutatif, jadi restart, recovery, send-program,
reconfiguration, fault isolation, dan tindakan lain yang `DENIED` tidak dibuka.
Bila Lapis 7 maju, tahap berikutnya adalah **proposal untuk satu tindakan
kandidat tertentu**: target, precondition, authorization scope, expected
postcondition, evidence, dan stop condition. Proposal itu sendiri tidak memberi
izin sampai ada keputusan pemilik.

**Sesudah tindakan** tersedia:
- observasi baru dari sumber yang sama, dengan cap waktu sesudah tindakan
  selesai;
- delta antara observasi sebelum dan sesudah (`layer5.delta` untuk host);
- rekaman tindakan itu sendiri: perintah, exit code, stdout dan stderr beserta
  hash-nya.

## 7.7 Success Evidence Contract

**Dikunci pemilik, 30 September 2026:**

> Tindakan hanya dinyatakan berhasil apabila terdapat observasi pascatindakan
> yang sesuai dengan outcome yang telah ditentukan untuk tindakan tersebut.

Exit code dapat menjadi bagian evidence, tetapi **bukan satu-satunya bukti**:
proses yang selesai secara teknis tidak otomatis berhasil secara sistem.
`exit code == 0` bukan definisi universal keberhasilan.

Mekanisme evidence yang sudah berjalan:
- **exit code dan stderr, dibaca lewat aturan `outcomes`** di
  `NUI/spec/layer5_collectors.json` (K-13: ditetapkan tidak sama dengan exit 0);
- **evidence dengan hash**: tiap berkas dijaga ukuran dan SHA-256-nya di
  manifest run (K-11);
- **transisi keadaan**: delta sebelum dan sesudah;
- **hasil bench atau `--verify` yang relevan**;
- **byte mentah sebagai bukti primer** untuk apa pun yang lewat kabel papan
  (K-7; aturan P1 dan Lapis 4: laporan membaca byte mentah rekaman, bukan teks
  yang dibawanya).

**Validasi pertama, perintah pemilik 30 September 2026: pada tindakan yang
sudah AUTHORIZED, perekaman evidence melalui `layer5.record`.** Tidak satu pun
tindakan mutatif yang `DENIED` dibuka. 7.7 tidak mensyaratkan tindakan mengubah
FPGA, host, atau sistem. Ia hanya mensyaratkan tindakan yang telah diizinkan,
lalu observasi pascatindakan yang membuktikan outcome yang sudah ditentukan.

```text
PRECONDITION
    ↓
tentukan expected outcome
    ↓
AUTHORIZATION = ALLOWED
    ↓
layer5.record
    ↓
POST-ACTION OBSERVATION
    ↓
compare dengan expected outcome
    ↓
SUCCESS / STOP-REPORT
```

Outcome ditetapkan **sebelum** `layer5.record` dijalankan. Contoh pemilik:
- run_id baru terbentuk;
- manifest hash tersedia;
- evidence record dapat dibaca kembali;
- provenance valid;
- kolektor yang berhasil tetap PASS;
- status freshness konsisten dengan waktu evidence;
- tidak ada perubahan di luar evidence store yang memang diharapkan.

`exit code = 0` tidak dijadikan satu-satunya bukti.

**Uji negatif wajib.** Evidence pascatindakan yang berikut masing-masing harus
menjadi STOP / REPORT, bukan SUCCESS:
- manifest hash salah;
- provenance rusak;
- outcome tidak sesuai;
- evidence menjadi STALE;
- target berubah/ambigu;
- hasil yang diharapkan tidak ditemukan.

**Tetap dilarang selama uji ini**:

```text
board reconfiguration       DENIED
send program                DENIED
restart/recovery            DENIED
fault isolation             DENIED
keep host awake             DENIED
repository mutation         DENIED
configuration mutation      DENIED
self-authorization          DENIED
```

**Kriteria GREEN 7.7:**

```text
authorized action
    + predetermined outcome
    + post-action evidence
    + evidence matches outcome
    = SUCCESS

otherwise
    = STOP / REPORT
```

Implementasinya `expect()` dan `confirm()` di `src/hijaiyyah/nui/layer7.py`;
hasil ujinya di `NUI/LAYERS.md`, Lapis 7.

**Keputusan pemilik sesudah validasi, 30 September 2026.**

*Dua label 7.7 disetujui:*
- **Outcome berbeda dari outcome yang telah ditetapkan sebelum tindakan →
  `KNOWN_DISCREPANCY`.** Objek dan tindakan sudah diketahui, tindakannya memang
  diizinkan, tetapi hasil aktual sesudah tindakan tidak sama dengan outcome
  yang ditetapkan. Kasus ini tidak diturunkan menjadi `NOT_COVERED` atau
  `UNKNOWN`.
- **Perubahan pada protected file atau evidence store di luar perubahan yang
  dihasilkan tindakan yang diotorisasi → `UNAUTHORIZED ACTION`.** Suntingan
  `NUI/LAYER7.md` di antara `expect` dan `confirm` adalah bukti konkret bahwa
  kontrak mendeteksi perubahan di luar boundary tindakan. `UNAUTHORIZED ACTION`
  **tidak pernah dianggap bukti bahwa tindakan yang bersangkutan gagal secara
  fungsional**: ia pelanggaran boundary terhadap kontrak eksekusi.

```text
AUTHORIZATION
    ↓
PRE-ACTION EXPECTATION
    ↓
AUTHORIZED ACTION
    ↓
POST-ACTION EVIDENCE
    ↓
7 CHECKS
    ├─ sesuai → SUCCESS
    ├─ discrepancy → KNOWN_DISCREPANCY → STOP / REPORT
    └─ boundary violation → UNAUTHORIZED ACTION → STOP / REPORT
```

*Baseline harus CURRENT — dikunci.* Baseline yang dipakai `expect()` harus
current pada saat keputusan dibuat. Evidence lama tidak dipakai hanya karena
masih valid secara sintaksis.

```text
baseline record
    ↓
freshness check ≤ 300 s
    ↓
expect()
    ↓
outcome ditetapkan
    ↓
layer5.record
    ↓
confirm()
```

Satu validasi 7.7 karena itu membutuhkan baseline baru bila baseline
sebelumnya sudah STALE. Baseline STALE tidak dipakai ulang untuk tindakan, dan
300 detik tidak dilonggarkan.

*Tabrakan `run_id` pada detik yang sama.* `src/hijaiyyah/nui/layer5.py` beku,
jadi presisi `run_id` **tidak diubah**. `FileExistsError` pada percobaan
pertama adalah evidence valid bahwa mekanismenya gagal dengan aman ketika
identitas run bertabrakan. `confirm` → `UNKNOWN` → STOP / REPORT sesuai
fail-closed. Tidak ada kebutuhan membuka Lapis 5 untuknya.

*Hasilnya.* Percobaan yang gagal tidak membatalkan validasi. Jalur final
diuji ulang sesudah pembetulan CLI, jadi evidence-nya mengacu pada kode
final:

```text
Layer 7 evaluator                 GREEN
7.7 post-action success           VALIDATED
Authorization boundary            UNCHANGED
Mutative DENIED actions            DENIED
```

## 7.8 UNKNOWN / NOT_COVERED Contract

Keadaan ketika sistem **wajib berhenti**, dari klaim maupun dari tindakan (7.6).

**UNKNOWN** — bukti belum cukup, bukan sistem belum ada (K-14):
- tidak ada observasi yang mendukung, seperti `host services` hari ini;
- observasi *known but stale* (**STALE**): melewati ambang kesegaran, atau jam
  mundur;
- observasi yang ditolak karena ukuran atau hash-nya tidak cocok dengan manifest;
- kolektor berstatus `unavailable_due_to_permissions`,
  `unavailable_command_absent`, atau `collector_error`;
- keadaan hardware CURRENT: tidak ada sumber telemetri live;
- tautan atau klaim yang Lapis 6 tandai UNKNOWN di provenance atau korelasinya.

**NOT_COVERED** — perilaku tanpa oracle. Targetnya diketahui, tetapi coverage
perilakunya belum tersedia (pemilik, 30 September 2026):
- aturan yang fungsi RTL Lapis 6 hentikan dengan `NotCovered`, termasuk 78
  aturan model HCPU (`NUI/LAYER6.md`);
- state opaque Lapis 6, yang tidak punya coverage prediktif di model beku —
  misalnya `ra_stack[]`, tujuh belas register x pengendali kartu, tujuh
  register guard yang tidak dielaborasi, dan register pc di register file;
- subsistem tanpa fungsi prediktif yang tervalidasi.

**KNOWN_DISCREPANCY** — selisih yang sudah terukur, ditambahkan pemilik
30 September 2026. Ketidaksesuaian HISAB punya evidence dan hasil pengukuran,
jadi ia bukan `UNKNOWN` dan bukan sekadar tidak tercakup. Ia tidak boleh
ditransformasikan menjadi PASS, dan tidak boleh dipakai sebagai alasan untuk
melakukan tindakan. Angkanya tinggal di `NUI/spec/rtl_function.json`
(`known_discrepancy`), tidak disalin ke sini (R1).

**Pemisahan label**, keputusan pemilik 30 September 2026:

| kondisi | label |
|---|---|
| Identitas host `(vm_name, run_id)` tidak tunggal | `AMBIGUOUS TARGET` |
| Target dapat diidentifikasi, tetapi tidak punya predictive coverage | `NOT_COVERED` |
| Ada evidence terukur, tetapi menyimpang dari baseline/model | `KNOWN_DISCREPANCY` |
| Nama/subjek/modul tidak dapat dipetakan ke objek yang dikenal | `UNKNOWN` |

```text
UNKNOWN           = kita tidak dapat menentukan objek/semantiknya
NOT_COVERED       = objek diketahui, tetapi coverage prediktif tidak tersedia
KNOWN_DISCREPANCY = objek diketahui dan terukur, tetapi hasil menyimpang
```

Jadi `rtl hcpu_sdio …` → `UNKNOWN`: `NUI/spec/rtl_function.json` tidak
menyediakan pemetaan nama itu. Hubungan `hcpu_sdio` → subsistem tertentu
**tidak dikarang** hanya dari nama RTL. Semua label selain PASS berujung
STOP / REPORT, termasuk `UNKNOWN`: nama yang tidak dikenal tidak pernah menjadi
alasan Lapis 7 bertindak.

**Kolektor yang tidak dikenal → `UNKNOWN`** (pemilik, 3 Oktober 2026). Nama
kolektor yang tidak ada di spec Lapis 5 adalah nama yang tak terpetakan, bukan
identitas yang ambigu. VM dan `run_id` tetap `AMBIGUOUS TARGET`.

Untuk ketiganya, dari pagar 7.2: `UNKNOWN` bukan izin bertindak,
`NOT_COVERED` bukan keberhasilan, `KNOWN_DISCREPANCY` bukan paritas, dan
ketiadaan evidence bukan alasan mengubah state.

## 7.9 Existing Evidence

**Historical evidence only.** Ini bukti bahwa mekanisme tindakan otomatis
pernah dieksekusi, sesuai catatan yang sudah ada — bukan dasar pemberian izin.

- **`rtl/scripts/burn_in.py`**: di dalam satu lari yang dimulai manusia, ia
  mencoba hingga `--launches` peluncuran. Tiap peluncuran mengonfigurasi ulang
  papan dan mengirim programnya, dan diterima hanya bila siklus pertama tiba.
  Tiap percobaan tercatat sebagai baris `launch` di lognya. Di log burn-in yang
  di-commit di `cosmictera-build/burn-in/`:

  | lari | baris `launch` | siklus pertama tiba |
  |---|---:|---|
  | `20260920T013538Z-burn-in-24h` | 1 | percobaan 1 |
  | `20260921T043655Z-burn-in-probe72` | 3 | percobaan 3 |
  | `20260921T044023Z-burn-in-72h-attempt1` | 2 | percobaan 2 |
  | `20260921T053430Z-burn-in-72h` | 1 | percobaan 1 |

- **Host dijaga terjaga**: lari 72 jam final mencatat `keeping_host_awake`
  benar. Ketiga lari sebelumnya tidak mencatat medan itu.
- **`rtl/scripts/burn_in_report.py`**: menggolongkan tiap diam milik papan atau
  milik host dengan membandingkan kedua jam. Itu penggolongan atas rekaman,
  bukan tindakan yang mengubah keadaan.

Mekanisme itu terbatas pada satu harness dan satu jenis kegagalan
(`NUI/LAYERS.md`, Lapis 7).

## 7.10 Explicit Non-Claims

- Tidak ada tindakan mutatif yang diizinkan. Otonomi hanya di wilayah
  read/verify/evidence (7.5).
- **Implementasi Lapis 7 hanya evaluator baca-saja**,
  `src/hijaiyyah/nui/layer7.py`, atas perintah pemilik 30 September 2026. Ia
  membaca observasi Lapis 5, state model Lapis 6, model fungsi RTL, dan tabel
  7.4 halaman ini, lalu menjawab PASS atau STOP / REPORT beserta alasannya.
  Ia tidak menjalankan perintah, tidak menulis berkas, dan tidak bertindak.
  **PASS berarti prasyarat untuk memakai sebuah observasi terpenuhi**, bukan
  bahwa sesuatu dikerjakan. Hasil ujinya di `NUI/LAYERS.md`, Lapis 7.
- **7.7 VALIDATED hanya pada satu tindakan AUTHORIZED yang tidak mutatif,
  `layer5.record`** (pemilik, 30 September 2026). Tindakan mutatif tetap
  DENIED, jadi tidak ada observasi pascatindakan atas tindakan mutatif mana
  pun, dan tidak ada klaim 7.7 untuknya.
- **ALLOW dari DECIDE bukan eksekusi.** `src/hijaiyyah/nui/layer7_decision.py`
  tidak menjalankan kandidat yang ia putuskan ALLOW, dan tidak memperoleh
  kewenangan apa pun darinya.
- Evaluator hanya menjawab keadaan hardware CURRENT, bukan klaim historis
  Lapis 6. Hardware CURRENT tetap UNKNOWN, dan tidak ada provenance hardware
  live yang dibuat untuk memicu `INVALID PROVENANCE` di jalur itu.
- `burn_in.py` bukan dasar pemberian izin. Ia hanya bukti bahwa mekanisme
  tindakan otomatis pernah dieksekusi di dalam satu harness.
- Kontrak ini tidak memperluas daftar izin Lapis 5, tidak menyentuh `sudo` atau
  grup tamu, dan tidak mengubah pagar hanya-baca.
- Keadaan hardware sekarang tidak diklaim: tidak ada sumber telemetri live.
- Paritas di luar yang Lapis 6 bekukan tidak diklaim.

## 7.11 Freeze/Change Rules

**Dikunci pemilik, 30 September 2026:**

> Setiap perubahan terhadap kontrak operasi, authorization boundary, allowlist,
> denylist, atau kondisi eskalasi merupakan perubahan spesifikasi yang
> memerlukan keputusan pemilik dan tidak boleh dilakukan oleh operasi otonom itu
> sendiri.

Tidak ada *self-modifying authority* pada Lapis 7. Yang sudah berlaku di
sampingnya:
- keputusan pemilik dicatat bertanggal di `AGENTS.md`;
- nilai yang dirujuk kontrak ini tetap tinggal di sumbernya. Bila sumbernya
  berubah — ambang kesegaran, daftar kolektor, daftar izin — yang berlaku adalah
  sumbernya, bukan salinan di sini (R1);
- nama dan slot baru tidak dikarang. Nama tag freeze Lapis 7, bila tiba
  waktunya, dari pemilik, seperti Lapis 4–6.

---

## Riwayat status

Blok status sebagaimana ditulis pada tanggalnya, dipindah utuh dari kepala
dokumen 3 Oktober 2026 atas perintah pemilik. Yang berlaku adalah *Status kini*
di atas; blok yang lebih tua dibaca sebagai keadaan pada hari itu.

**Status keputusan** (pemilik, 30 September 2026):

```text
7.2  DEFINED / LOCKED
7.3  EXISTING CONTRACT
7.4  READ ACTIONS AUTHORIZED
     MUTATING ACTIONS DENIED
7.5  AUTHORIZATION BOUNDARY DEFINED
7.6  EXISTING CONTRACT
7.7  EXISTING CONTRACT
7.8  EXISTING UNKNOWN / NOT_COVERED CONTRACT
7.9  HISTORICAL EVIDENCE ONLY
7.10 NON-CLAIMS PRESERVED
7.11 LOCKED
```

**Status sesudah evaluator baca-saja** (pemilik, 30 September 2026):

```text
638d827
Lapis 7 evaluator read-only: GREEN

7.6:
AMBIGUOUS TARGET = identity ambiguity only

7.8:
UNKNOWN              → STOP / REPORT
NOT_COVERED          → STOP / REPORT
KNOWN_DISCREPANCY    → STOP / REPORT
STALE                → STOP / REPORT
INVALID PROVENANCE   → STOP / REPORT
UNAUTHORIZED ACTION  → STOP / REPORT

7.7:
NOT YET VALIDATED — no authorized mutative action exists
```

**Status resmi sesudah label diselaraskan** (pemilik, 30 September 2026):

```text
Layer 7 read-only evaluator
Commit: 865959e
Status: GREEN
Scope: READ → EVALUATE → GATE → EVIDENCE / REPORT
Mutative authorization: DENIED
```

**Status resmi sesudah 7.7 divalidasi** (pemilik, 30 September 2026):

```text
Layer 7 evaluator                 GREEN
7.7 post-action success           VALIDATED
Commit                            b7fa5e8
Authorization boundary            UNCHANGED
Mutative DENIED actions            DENIED
```

**Status resmi sesudah DECIDE** (pemilik, 30 September 2026):

```text
Layer 7 evaluator              GREEN
7.7 post-action success        VALIDATED
Decision / Dry-Run             GREEN
Authorization boundary         UNCHANGED
Mutative actions               DENIED
Commit                         46f4b14
```

**Status resmi sesudah proposal `SEND_PROGRAM`** (pemilik, 1 Oktober 2026):

```text
Layer 7 evaluator              GREEN
7.7 post-action success        VALIDATED
Decision / Dry-Run             GREEN
SEND_PROGRAM proposal          HARD STOP
SEND_PROGRAM authorization     DENIED
Mutative authorization         DENIED
Commit                         590baa6
```
