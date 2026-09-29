# Layer 7 — Autonomous Operation

Kerangka kontrak operasi otonom, ditulis atas perintah pemilik, 30 September 2026.
Judul resmi lapis ini di `NUI/LAYERS.md` adalah *Operasi otonom*; *Autonomous
Operation* adalah padanan yang pemilik pakai untuk dokumen ini.

**Status: KERANGKA.** Dokumen ini tidak memberi izin tindakan apa pun. Lapis 7
tetap **belum otonom** sesudah dokumen ini ada. Batas otorisasi (7.5) belum
diputuskan, dan tidak ada tindakan di 7.4 yang diizinkan.

Yang **dikunci pemilik** di sini hanya dua: pagar di 7.2 dan status 7.5. Isi
selebihnya adalah **kerangka** yang menunggu pemilik — susunan dan rujukan, bukan
keputusan.

Isinya menunjuk ke sumber yang sudah terukur, tidak menyalin nilainya (R1). Nilai
yang bisa berubah — misalnya ambang kesegaran atau daftar kolektor — tinggal di
spec asalnya.

---

## 7.1 Tujuan

Tujuan Lapis 7 tertulis di `NUI/LAYERS.md`: menjalankan sistem tanpa pengawasan
manusia — memantau, memulihkan, memulai ulang, mengisolasi kesalahan —
berdasarkan telemetri, diagnostik, dan fakta terverifikasi.

Langkah pertama yang pemilik tetapkan, 29 September 2026, **bukan** membuat
sistem bertindak otonom. Langkah pertamanya menetapkan kontrak yang dapat diukur,
supaya Lapis 7 tidak mengubah NUI menjadi sekadar lingkar otomatis tanpa guard.
Dokumen ini adalah kerangka kontrak itu.

## 7.2 Definisi Operasi Otonom

*Usulan kerangka — rumusannya dikunci pemilik, bukan di sini.* Dalam kontrak
ini, **operasi otonom** adalah tindakan yang mengubah keadaan sistem, dijalankan
tanpa perintah manusia untuk tindakan itu. Operasi otonom **hanya sah** bila
keenam unsur kontrak terpenuhi untuk tindakan tersebut:

1. yang ia baca ada di Read Contract (7.3);
2. tindakannya ada di Action Contract (7.4) **dan** diizinkan Authorization
   Boundary (7.5);
3. keadaan sebelum dan sesudahnya diketahui menurut Pre/Post-State Contract (7.6);
4. keberhasilannya dibuktikan menurut Success Evidence Contract (7.7);
5. tidak satu pun kondisi di UNKNOWN / NOT_COVERED Contract (7.8) berlaku.

Membaca, mengukur, dan membandingkan tanpa mengubah keadaan bukan operasi otonom
dalam arti ini. Itu sudah berjalan di Lapis 5 dan 6 di bawah pagarnya sendiri.

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

Sumber observasi yang **tersedia** untuk dikonsumsi operasi otonom, dengan dasar
dan batas yang sudah berlaku. Kontrak ini tidak memperluas satu pun dari dasar
itu.

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

Daftar tindakan yang **mungkin** kelak diotorisasi. Setiap baris berstatus
**BELUM DIIZINKAN**. Daftar ini diambil dari yang sudah tercatat, tidak
dikarang.

| kelas tindakan | asal catatannya | status |
|---|---|---|
| Perintah host yang mengubah sistem: `rm`, `mv`, `kill`, `reboot`, `shutdown`, `systemctl start`, `systemctl stop`, `docker rm`, `docker stop`, `docker exec` | Daftar "belum diizinkan" Lapis 5 di `NUI/LAYERS.md`: belum diizinkan sampai seluruh pipeline Lapis 5 tervalidasi | BELUM DIIZINKAN |
| Mengonfigurasi ulang papan dengan bitstream (`openFPGALoader`) | Dijalankan `rtl/scripts/burn_in.py` di dalam satu lari burn-in (7.9) | BELUM DIIZINKAN |
| Mengirim program ke papan lewat UART | Dijalankan `rtl/scripts/burn_in.py` di dalam satu lari burn-in (7.9) | BELUM DIIZINKAN |
| Menahan host tetap terjaga (`caffeinate`) | Dijalankan `rtl/scripts/burn_in.py` selama logger hidup (7.9) | BELUM DIIZINKAN |
| Memulihkan, memulai ulang, atau mengisolasi kesalahan secara umum | Tujuan Lapis 7 di `NUI/LAYERS.md`; belum ada bentuk tindakannya | BELUM DIIZINKAN |

Tindakan di luar tabel ini tidak ada dalam kontrak. Tindakan yang tercatat di
tabel ini pun tetap tidak diizinkan sampai 7.5 memutuskannya.

## 7.5 Authorization Boundary

```text
STATUS: UNDECIDED
OWNER DECISION REQUIRED
```

## 7.6 Pre/Post-State Contract

Yang wajib diketahui **sebelum** tindakan, dan yang wajib tersedia **sesudahnya**.
Sumbernya sudah ada; pemakaiannya untuk tindakan belum.

**Sebelum:**
- keadaan target dibaca dari sumber 7.3, dengan provenance lengkap: run_id,
  kolektor, berkas evidence, cap waktu, dan SHA-256-nya;
- untuk host, observasinya milik VM target sendiri (K-16) dan berstatus *known
  current* menurut aturan kesegaran di `NUI/spec/layer5_collectors.json`;
- untuk hardware, keadaan CURRENT hanya dari sumber live. Hari ini tidak ada
  sumber live, jadi keadaan hardware sebelum tindakan **tidak dapat diketahui**
  — dan menurut 7.8 itu menghentikan tindakan.

**Sesudah:**
- observasi baru dari sumber yang sama, dengan cap waktu sesudah tindakan
  selesai;
- delta antara observasi sebelum dan sesudah (`layer5.delta` untuk host);
- rekaman tindakan itu sendiri: perintah, exit code, stdout dan stderr beserta
  hash-nya.

## 7.7 Success Evidence Contract

Observasi konkret yang dapat membuktikan tindakan berhasil. Semuanya mekanisme
yang sudah berjalan:
- **exit code dan stderr, dibaca lewat aturan `outcomes`** di
  `NUI/spec/layer5_collectors.json` (K-13: ditetapkan tidak sama dengan exit 0);
- **evidence dengan hash**: tiap berkas dijaga ukuran dan SHA-256-nya di
  manifest run (K-11);
- **transisi keadaan**: delta sebelum/sesudah yang menunjukkan perubahan yang
  dituju, dan tidak lebih;
- **hasil bench atau `--verify` yang relevan**, untuk tindakan yang menyentuh
  artefak yang punya verifikator;
- **byte mentah sebagai bukti primer** untuk apa pun yang lewat kabel papan
  (K-7; aturan P1 dan Lapis 4: laporan membaca byte mentah rekaman, bukan teks
  yang dibawanya).

## 7.8 UNKNOWN / NOT_COVERED Contract

Keadaan ketika sistem **wajib berhenti** — dari klaim maupun dari tindakan.

**UNKNOWN** — bukti belum cukup, bukan sistem belum ada (K-14):
- tidak ada observasi yang mendukung, seperti `host services` hari ini;
- observasi *known but stale*: melewati ambang kesegaran, atau jam mundur;
- observasi yang ditolak karena ukuran atau hash-nya tidak cocok dengan manifest;
- kolektor berstatus `unavailable_due_to_permissions`,
  `unavailable_command_absent`, atau `collector_error`;
- keadaan hardware CURRENT: tidak ada sumber telemetri live;
- tautan atau klaim yang Lapis 6 tandai UNKNOWN di provenance atau korelasinya.

**NOT_COVERED** — perilaku tanpa oracle:
- aturan yang fungsi RTL Lapis 6 hentikan dengan `NotCovered`, termasuk 78
  aturan model HCPU (`NUI/LAYER6.md`);
- state opaque Lapis 6 dan subsistem tanpa fungsi;
- ketidaksesuaian HISAB yang terukur, yang tetap ketidaksesuaian dan bukan
  paritas.

Berlaku untuk keduanya, dari pagar 7.2: `UNKNOWN` bukan izin bertindak,
`NOT_COVERED` bukan keberhasilan, dan ketiadaan evidence bukan alasan mengubah
state.

## 7.9 Existing Evidence

Bukti bahwa mekanisme tindakan otomatis **pernah dieksekusi**, sesuai catatan
yang sudah ada. **Bukan preseden** bahwa tindakan itu termasuk tindakan yang
boleh dilakukan NUI.

- **`rtl/scripts/burn_in.py`**: di dalam satu lari yang dimulai manusia, ia
  mencoba hingga `--launches` peluncuran. Tiap peluncuran mengonfigurasi ulang
  papan dan mengirim programnya, lalu diterima hanya bila siklus pertama tiba.
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

Mekanisme itu terbatas pada satu harness dan satu jenis kegagalan (`NUI/LAYERS.md`,
Lapis 7).

## 7.10 Explicit Non-Claims

- Lapis 7 **belum otonom**. Kerangka ini tidak memberi izin tindakan apa pun.
- Tidak ada tindakan di 7.4 yang diizinkan, dan 7.5 belum diputuskan.
- `burn_in.py` bukan preseden. Ia hanya bukti bahwa mekanisme tindakan otomatis
  pernah dieksekusi di dalam satu harness.
- Kerangka ini tidak memperluas daftar izin Lapis 5, tidak menyentuh `sudo` atau
  grup tamu, dan tidak mengubah pagar hanya-baca.
- Keadaan hardware sekarang tidak diklaim: tidak ada sumber telemetri live.
- Paritas di luar yang Lapis 6 bekukan tidak diklaim.

## 7.11 Freeze/Change Rules

Yang sudah berlaku:
- Batas otorisasi tidak pernah berubah secara otomatis (pagar 7.2).
- Keputusan pemilik dicatat bertanggal di `AGENTS.md`, jadi isi 7.4 dan 7.5
  hanya berubah lewat keputusan yang tercatat di sana.
- Nilai yang dirujuk kontrak ini tetap tinggal di sumbernya. Bila sumbernya
  berubah — ambang kesegaran, daftar kolektor, daftar izin — yang berlaku adalah
  sumbernya, bukan salinan di sini (R1).
- Nama dan slot baru tidak dikarang. Nama tag freeze Lapis 7, bila tiba
  waktunya, dari pemilik, seperti Lapis 4–6.

*Usulan kerangka, menunggu pemilik:* setiap implementasi Lapis 7 kelak menunjuk
bagian kontrak yang ia penuhi, dan tindakan yang tidak bisa menunjuk keenam
bagian 7.3–7.8 tidak sah.
