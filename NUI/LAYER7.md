# Layer 7 — Autonomous Operation

Kontrak operasi otonom. Kerangkanya ditulis atas perintah pemilik, 30 September
2026, dan pada hari yang sama pemilik mengunci 7.2, 7.5, dan 7.11. Judul resmi
lapis ini di `NUI/LAYERS.md` adalah *Operasi otonom*; *Autonomous Operation*
adalah padanan yang pemilik pakai untuk dokumen ini.

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

Keputusan ini dokumen dan spec. Ia tidak memberi izin implementasi tindakan
otonom di luar batas yang ditetapkan. Otonomi NUI saat ini hanya di wilayah
**read → evaluate → verify → evidence**. Tidak ada mutasi sistem tanpa
keputusan otorisasi berikutnya.

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
dipertahankan, dengan statusnya.

| kategori | asal catatannya | status |
|---|---|---|
| Observasi / read-only | Mekanisme Lapis 5 dan state model Lapis 6 (7.3) | **AUTHORIZED** |
| Evidence, provenance, freshness, delta | Mekanisme Lapis 5 (7.3, 7.6, 7.7) | **AUTHORIZED** |
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

**Tetap tidak diizinkan — DENIED pada Lapis 7 awal:**

- konfigurasi ulang papan;
- mengirim program ke papan;
- mengubah persistent state HFS/SD;
- restart atau recovery otomatis;
- isolasi kesalahan;
- menjaga host tetap terjaga;
- seluruh 10 perintah host yang pada Lapis 5 berstatus belum diizinkan;
- tindakan jaringan eksternal;
- perubahan repository;
- perubahan konfigurasi sistem;
- tindakan apa pun yang memerlukan pencabutan read-only guard Lapis 5, K-4, atau
  K-12.

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

Jadi NUI sudah punya operasi otonom, tetapi hanya di wilayah read/verify/evidence.
Itu disengaja, supaya lapisan pertama dapat diuji sebelum ada kemampuan mutasi
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
