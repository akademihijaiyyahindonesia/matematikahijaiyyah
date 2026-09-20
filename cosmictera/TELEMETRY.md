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
