# Kontrak Telemetri CosmicTera v1

**Keputusan pemilik, 20 September 2026**, diambil ketika burn-in tingkat 1
sedang berjalan dan pertanyaannya menjadi konkret: apa yang sebenarnya bisa
dilaporkan sistem ini tentang dirinya. Halaman ini **mencatat kontraknya dan
menandai sumber tiap medan** — bukan mengusulkan, bukan mengimplementasikan.
NUI Core adalah prioritas 7 dan belum dimulai.

```
SYSTEM    uptime · cycle_rate · drift · anomaly_score
MEMORY    memory_check · stack_check · corruption_score
JAMRAH    pass_count · reject_count · latency · consistency
KABAH     avalanche · integrity · replay_state · state_hash
STORAGE   sd_sector_read · hfs_signature · read_error_count
BOOT      last_boot · last_container · last_relocation · boot_duration
HIJRAH    last_validation · density_mod2 · density_mod4 · density_mod5 ·
          collapse_count
```

**Dua penetapan pemilik yang menyertainya**, dan keduanya menyelesaikan
pertanyaan yang sempat terbuka:

- **Loader bukan telemetri kontinu, melainkan telemetri kejadian boot.** Yang
  disimpan hasil terakhirnya, bukan pembacaan tiap detik.
- **Hijrah bukan daemon, melainkan mesin validasi.** Yang hidup bukan
  statusnya melainkan hasil validasi terakhirnya.

## Sumber tiap medan, hari ini

Tiga kolom: medan, apakah ada angkanya sekarang, dan dari mana angkanya
datang. Yang belum ada sumbernya ditulis begitu — bukan diisi dengan angka
yang terdengar masuk akal.

| medan | sumber hari ini | dari mana |
|---|---|---|
| `uptime` | **ada** — papan menghitung putaran pencacahnya sendiri, 159,07 detik per putaran | `rtl/programs/burn_in.hasm`, tiap detak |
| `cycle_rate` | **ada** — 649,4 siklus/detik (median), 1,54 ms kerja per siklus | [burn-in/](../cosmictera-build/burn-in/README.md) |
| `drift` | **ada** — jam papan dikurangi jam host, −3,3 detik dan datar | [burn-in/](../cosmictera-build/burn-in/README.md) |
| `anomaly_score` | **belum ada sumbernya** — ia turunan, bukan pengukuran; yang dibutuhkan NUI, prioritas 7 | — |
| `memory_check` | **ada** — enam belas kata ditulis sekali lalu dibandingkan tiap siklus | `rtl/programs/burn_in.hasm` |
| `stack_check` | **ada** — satu `PUSH` dan satu `POP` tiap siklus | `rtl/programs/burn_in.hasm` |
| `corruption_score` | **belum ada sumbernya** — turunan dari pencacah kesalahan yang sudah ada | — |
| `pass_count` | **ada** — 28 per sapuan 256 byte | [validasi/JAMRAH.md](../cosmictera-build/validasi/JAMRAH.md) |
| `reject_count` | **ada** — 228 per sapuan | [validasi/JAMRAH.md](../cosmictera-build/validasi/JAMRAH.md) |
| `latency` | **ada** — 33 clock, nilai yang sama untuk ke-256 byte | [attack-lab/](../cosmictera-build/attack-lab/README.md) |
| `consistency` | **ada** — lima lari identik byte demi byte; burn-in membandingkan dua jumlah tiap siklus | `rtl/programs/burn_in.hasm` |
| `avalanche` | **ada** — 0,4995 atas 32 bit-flip tunggal; 0,4984 sampai 0,5061 untuk 1–64 bit | [validasi/KABAH.md](../cosmictera-build/validasi/KABAH.md) |
| `integrity` | **ada** — 8/8 frame berantai dan 32/32 masukan termutasi cocok `cube.py` | [validasi/KABAH.md](../cosmictera-build/validasi/KABAH.md) |
| `replay_state` | **ada** — dua jawaban: identik sesudah rekonfigurasi, berantai di dalam satu lari | [validasi/KABAH.md](../cosmictera-build/validasi/KABAH.md) |
| `state_hash` | **belum ada sumbernya** — keadaan 200 byte ada, tetapi tak ada yang meringkasnya, dan tidak ada inti SHA-256 di RTL (R10). Bentuk ringkasannya keputusan pemilik | — |
| `sd_sector_read` | **ada** — sektor 1 dibaca tiap siklus, statusnya ikut di tiap detak | `rtl/programs/burn_in.hasm` |
| `hfs_signature` | **ada** — `0x48465331` terbaca dari kartu | [burn-in/](../cosmictera-build/burn-in/README.md) |
| `read_error_count` | **ada** — pencacah baca kartu yang tak selesai, terpisah dari pencacah kesalahan | `rtl/programs/burn_in.hasm` |
| `last_boot` | **ada** — `SYSCALL` 9 menjawab 1 atau 0; papan yang boot dari kartu menjawab `1 2 3` | [PAPAN.md](../cosmictera-build/PAPAN.md) |
| `last_container` | **ada** — loader menerima atau menolak; lab serangan 8 dari 10 lalu 16 dari 16 | [attack-lab/](../cosmictera-build/attack-lab/README.md) |
| `last_relocation` | **belum terpisah** — relokasi diterapkan di dalam pemuatan dan tidak dilaporkan sendiri; buktinya hanya program yang berjalan benar (`1 2 3`, dan `111` ketika `JMP`-nya dihapus) | — |
| `boot_duration` | **ada, diukur sekali** — 579.255 siklus, 21,5 ms dari konfigurasi sampai halt | [CHECKLIST.md](../cosmictera-build/CHECKLIST.md) |
| `last_validation` | **ada** — 700/700 muka; 24 / 27 / 28 / 28 panjang 1; 321 / 649 / 625 / 714 panjang ≤ 2 | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) |
| `density_mod2` | **ada** — 4,58 | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) |
| `density_mod4` | **ada** — 4,81 | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) |
| `density_mod5` | **ada** — 4,81 | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) |
| `collapse_count` | **ada** — 4 pasang runtuh atas mod 2: ح–ل, ش–ن, ص–ق, ع–ي | [validasi/HIJRAH.md](../cosmictera-build/validasi/HIJRAH.md) |

## Satu angka yang perlu dibetulkan sebelum ia menyebar

Kepadatan **4,75 adalah mod 3**, bukan mod 4. Tabel terukurnya, panjang 1:

```
mod 2   mod 3   mod 4   mod 5
 4,58    4,75    4,81    4,81
```

`hijrah/README.md` menuliskannya dalam kolom GF(2) / GF(4) / GF(5) —
**4,58 / 4,81 / 4,81** — sehingga "GF(4) = 4,75" adalah angka mod 3 yang
berpindah kolom. Dicatat di sini, bukan dirapikan diam-diam, karena kontrak
telemetri adalah tempat angka disalin orang lain.

## Hierarki waktu — keputusan pemilik, 20 September 2026

**Waktu host bukan sumber kebenaran.** Urutannya ditetapkan pemilik:

```
Tingkat 1   pencacah siklus FPGA      0xFF4, 32 bit, 27 MHz
Tingkat 2   uptime papan              putaran pencacah + pencacah sekarang
Tingkat 3   cap waktu host            hanya untuk mencatat, bukan untuk menilai
```

Akibatnya langsung: MacBook yang sibuk, Docker yang sibuk, editor yang macet —
tak satu pun boleh terbaca sebagai anomali CosmicTera.

**Keputusan ini lahir dari pengukuran, bukan dari kehati-hatian.** Lari 24 jam
diam 140 detik pada detik 14.496, dan diam itu **milik host**: detak yang
datang sesudahnya adalah detak lama, jam papan tertinggal 138 detik lalu
mengejar, 127 detak terkuras dalam 61 detik berikutnya. Papan tidak pernah
berhenti. Kalau jam host dipakai sebagai kebenaran, itu terbaca sebagai mesin
menggantung dua menit.

Burn-in sudah bekerja begitu: tiap detak membawa jam papannya sendiri, dan
`rtl/scripts/burn_in_report.py` menggolongkan tiap diam dengan membandingkan
kedua jam — papan yang berhenti meninggalkan jamnya sejalan dengan host dan
cacah detaknya membeku; host yang berhenti meninggalkan jam papan tertinggal.

## Tiga kontrak yang belum diputuskan

Pemilik menamai ketiganya 20 September 2026 dan memberi pilihannya. Yang
tertulis di sini **pilihannya beserta angka yang sudah terukur untuk
masing-masing**, bukan pilihan yang diambil sepihak.

### 1. `state_hash`

| opsi pemilik | yang sudah terukur |
|---|---|
| **A** — simpan keadaan mentah 200 byte | tidak ada yang perlu dibangun: wrapper Ka'bah **sudah** menjawab 200 byte per frame. Di UART 115200 itu **17,4 ms per keadaan**; pada irama detak burn-in (1,58 detik) ia 1,1% dari kabel |
| **B** — sidik jari 64-bit dari Ka'bah sendiri | lipatan XOR 64-bit atas 200 byte, 20.000 pesan acak: **20.000 nilai berbeda, 0 tabrakan**. Angka itu **tidak membuktikan banyak** — harapan ulang tahun pada 2⁶⁴ untuk 20.000 nilai adalah 1,1 × 10⁻¹¹, jadi nol adalah yang diharapkan bahkan dari lipatan yang buruk; yang ia singkirkan hanya kemerosotan kasar. Dan lipatan XOR **linier**: tabrakan bisa dibuat sengaja, jadi ia mendeteksi kecelakaan, bukan lawan |
| **C** — host yang menghitung SHA-256 | **biaya papan nol** — ini persis yang wrapper lakukan sekarang. Tidak ada baris RTL atau HASM yang berubah, dan R10 tidak tersentuh karena tidak ada inti SHA-256 yang dibangun |

Pemilik menilai **C paling realistis untuk tahap awal**. Dicatat sebagai
penilaian; tidak ada pekerjaan yang berangkat darinya sebelum ia dinyatakan
sebagai keputusan.

### 2. `last_relocation`

Pemilik mempersempitnya 20 September 2026, tepat karena `relocation_ok` akan
mengklaim lebih dari yang terbukti. Tiga medan menggantikannya:

```
relocation_count    container_loaded    entry_reached
```

*"dan tidak menyatakan lebih dari yang benar-benar telah dibuktikan."*
Masing-masing, hari ini:

| medan | yang bisa dikatakannya sekarang |
|---|---|
| `relocation_count` | **ada** — kata ke-5 header container, dibaca loader untuk bekerja. Terukur: 125 untuk `shell.hasm`, 38 untuk `hos_hfs_disk`, rata-rata 7,2 dari 41 program |
| `container_loaded` | **ada** — `R1` yang dikembalikan `hos_prog_load.hasm`: 1 atau 0, jawaban `SYSCALL` 9 |
| `entry_reached` | **bukan milik loader** — sesudah `ERET` loader tidak punya suara lagi; hanya program yang dimuat yang bisa bersaksi ia berjalan, dan hari ini kesaksiannya adalah keluarannya sendiri (`1 2 3` di papan) |

**Kenapa `relocation_ok` ditinggalkan, dengan angkanya:** lab serangan mengukur
satu entri tabel relokasi yang diarahkan ke kata program lain **lolos tanpa
satu pun penolakan**, karena jumlah 32-bit hanya menutupi kata program
([attack-lab/](../cosmictera-build/attack-lab/README.md)). Medan bernama "ok"
akan berbohong pada kasus itu. Memperluasnya menuntut keputusan yang masih
terbuka sejak kelas B: apakah cakupan jumlah diperluas ke header dan tabel
relokasi.

Satu batas lagi yang menempel di sini dan sudah tertulis di kodenya:
**ENTRY tidak dikembalikan loader** — `rtl/programs/test_prog_run.hasm`
menuliskannya sendiri sebelum `ERET`, dan mengembalikan ENTRY lewat ABI
`SYSCALL` 9 adalah keputusan pemilik yang belum diambil.

### 3. `anomaly_score`

Pemilik menyarankan lima pita — 0–20 NORMAL, 21–40 NOTICE, 41–60 WARNING,
61–80 ALERT, 81–100 CRITICAL — atas cycle drift, memory mismatch, stack
mismatch, Jamrah mismatch, Ka'bah integrity mismatch, dan SD read failure.

Enam masukan itu **semuanya sudah punya sumber** (lihat tabel di atas). Yang
belum ada adalah **normalnya**, dan itu justru yang sedang dikerjakan tingkat 1:
sebuah ambang yang ditetapkan sebelum garis dasar selesai adalah angka yang
dikarang. Empat dari enam masukan itu sejauh lari ini **belum pernah bergerak
dari nol sama sekali**, jadi pita untuk mereka tidak bisa ditarik dari data —
hanya dari keputusan.

## Status empat medan turunan — pemilik, 20 September 2026

Supaya dashboard tidak mengklaim lebih dari yang diukur, keempatnya diberi
status, bukan angka:

```
state_hash        = pending architecture
last_relocation   = partial evidence
anomaly_score     = waiting baseline
corruption_score  = waiting baseline
```

`tests/test_integrity/test_telemetry_contract.py` menjaga keempat status itu
tetap tertulis persis begitu sampai ada yang mengukurnya.

## Apa yang kontrak ini belum tentukan

Kontrak menyebut **apa** yang dilaporkan. Yang belum ditetapkan pemilik, dan
tidak boleh dikarang:

- **Setiap berapa lama** tiap medan dilaporkan. Burn-in memakai satu detak per
  1.024 siklus (±1,58 detik) dan itu kontrak burn-in, bukan kontrak sistem.
- **Lewat jalur apa.** Hari ini satu-satunya jalur keluar papan adalah UART
  115200 8N1, dan `PRINT` **tidak bisa mencetak angka besar dengan benar**
  ([OFF.md](../cosmictera-build/OFF.md)). Medan 32-bit apa pun harus dipecah,
  seperti yang burn-in lakukan.
- **Ambang untuk Normal / Warning / Critical.** Itu menuntut garis dasar
  selesai lebih dulu; tingkat 1 masih berjalan.
