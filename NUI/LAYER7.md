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
- **7.7 NOT YET VALIDATED**: belum ada tindakan mutatif yang diizinkan, jadi
  belum ada observasi pascatindakan. Evaluator baru membuktikan
  read → evaluate → gate → evidence/report, bukan
  action → postcondition → success.
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
