# Burn-in — catatan per lari

**Prioritas 6 pemilik**, dibuka 20 September 2026 sesudah lab serangan tutup.
Pertanyaannya satu, dan simulasi tidak bisa menjawabnya: *"apakah sistem ini
stabil berjalan terus-menerus?"*

Pemilik menetapkan tiga tingkat — **24 jam**, **72 jam**, **168 jam** — dan apa
yang harus dibuktikan tingkat pertama: tidak ada deadlock, tidak ada korupsi
memori, tidak ada watchdog timeout, tidak ada serial yang menggantung.

**Satu dari keempatnya tidak bisa diukur di papan ini, dan itu dikatakan di
muka: tidak ada watchdog.** Tidak ada modul semacam itu di `rtl/`, dan lab ini
tidak berpura-pura menjadi satu. Mesin yang berhenti tidak bisa melaporkan
bahwa ia berhenti; yang bisa diukur adalah **diamnya**, dan itulah yang
dicatat host sebagai jarak antar detak.

## Apa yang dikerjakan papan

`rtl/programs/burn_in.hasm` (332 kata), dikirim lewat `loader.hasm`. Satu
siklus, berulang:

| | yang dikerjakan | yang akan tertangkap |
|---|---|---|
| 1 | gerbang Jamrah atas ke-256 byte, pulse dan ketujuh simpul dijumlah | ALU yang hanyut, bit macet di berkas register, shift yang berhenti menggeser |
| 2 | ke-28 vektor codex dibaca dari ROM (`HLOAD`, `CGET`, `CU`, `CRHO`), dijumlah | ROM yang bacaannya melapuk |
| 3 | enam belas kata memori data, ditulis sekali lalu dibandingkan tiap siklus | **korupsi memori** |
| 4 | satu `PUSH` dan satu `POP` | tumpukan, yang hidup di luar memori data dan tak terlihat oleh 1–3 |
| 5 | sektor 1 kartu, dibaca, kata pertamanya dibandingkan | jalur SDIO, satu-satunya kabel ke perangkat fisik |

Kartu **dibaca, tidak pernah ditulis**: menulis tiap siklus selama seminggu
adalah uji keausan kartu, bukan uji mesin ini.

**Tidak ada yang dibandingkan dengan konstanta yang dirakit ke dalam citra**,
karena konstanta yang salah melaporkan cacat yang tidak ada. Siklus pertama
**menyimpan** apa yang ia hasilkan; setiap siklus sesudahnya membandingkan
terhadap salinan itu. Siklus pertama juga **mencetak** tujuh angka, dan tiga di
antaranya punya jawaban dari luar papan:

```
28    huruf 1..28          rtl/tb/jamrah_vectors.txt
3072  tiga tingkat pohon    tiap tingkat menjumlah 1.024 bit yang menyala di 256 byte
178   theta + U + rho       Master Table
```

Ketiganya cocok di papan pada lari pertama.

## Dua pencacah, karena dua hal berbeda

**errors** menghitung nilai yang berselisih dengan yang mesin ini sendiri
hasilkan lebih dulu. **sd failures** menghitung pembacaan yang tidak
diselesaikan kartu. Mencampurnya akan membuat kartu yang sedang tidak enak
badan terbaca sebagai korupsi memori — dan kriteria tingkat pertama justru
tentang yang kedua.

## Detak

Tiap 1.024 siklus: huruf `H`, lalu enam angka — detak, errors, sd failures,
putaran pencacah, pencacah >> 12, status kartu. Host mengalikan kembali.

**Angka besar tidak dikirim utuh, dan alasannya terukur**: `PRINT` mencetak
nilai besar dengan salah di papan ini — tangga `2^0..2^31` benar sampai
4.194.304 lalu mulai mengeluarkan karakter **di atas `'9'`. Rinciannya di
[OFF.md](../OFF.md). Program ini menjaga tiap angkanya di bawah sejuta.

Pencacah 0xFF4 32-bit pada 27 MHz berputar tiap **159,07 detik** — ±543 kali
dalam 24 jam — jadi uptime adalah putaran dan pencacah bersama-sama. Papan
menghitung putarannya sendiri, host menyimpan jamnya sendiri di sebelahnya,
dan keduanya harus tetap sejalan.

## Pengurainya diuji tanpa papan

Lari sehari tidak bisa diulang untuk menguji penguraiannya, jadi `Feed` di
`burn_in.py` berdiri sendiri dan diuji dari potongan byte yang direkam:
siklus pertama dan detak dibedakan oleh **penanda `H`, bukan oleh jumlah
angka**; baris bercampur seperti `335544;<` **dibuang utuh dan dihitung**,
tidak diperas jadi `335544`; dan byte yang datang terpotong-potong tetap satu
baris. Ketiganya disabotase dan ketiganya merah ketika disabotase.

Pengurai ini pernah salah sekali — ia menghitung angka alih-alih menandai
grup, membaca tujuh nilai siklus pertama sebagai detak enam-kolom, dan menulis
**3.072 kesalahan yang tidak ada** ke dalam catatan. Itu sebabnya ia sekarang
punya tesnya sendiri.

## Dari catatan ke garis dasar

Lari yang berakhir dengan "0 error" mengatakan mesinnya tidak rusak. Ia
**belum** mengatakan seperti apa perilaku biasanya, dan justru angka itu yang
nanti dibandingkan lapisan pengawasan — kalimat pemilik sendiri: *"Anomali
tidak bisa didefinisikan tanpa mengetahui normal."*

`rtl/scripts/burn_in_report.py` membaca satu lari dan menyatakan normal yang ia
temukan: laju kerja, jarak antar detak, dan bagaimana jam papan mengikuti jam
host. Ia menulis `<id>-baseline.json` di sebelah catatannya.

**Satu angka di situ milik host, bukan papan, dan dikatakan begitu.** Jarak
antar detak yang *terukur* dikuantisasi oleh tenggat baca serial host: tingkat 1
berjalan dengan tenggat satu detik, jadi jaraknya menumpuk di 1,0 dan 2,0 detik
padahal papan berdetak tiap **1,58 detik**. Angka papannya diturunkan dari laju
siklus, bukan dari jarak yang terlihat. Lari berikutnya memakai tenggat 0,25
detik; itu tidak mengubah apa yang tingkat 1 ukur, dan angka tingkat 1 tidak
dilabeli ulang diam-diam.

## Membekukan, lalu membandingkan

Sebuah garis dasar yang dibekukan hanya berguna kalau ada yang bisa
membandingkannya. `--against` mencetak **apa yang bergeser** antara sebuah lari
dan garis dasar beku:

```bash
python3 rtl/scripts/burn_in_report.py <id>.jsonl --write            # bekukan
python3 rtl/scripts/burn_in_report.py <lari-baru>.jsonl --against <id>-baseline.json
```

Ia menyatakan **selisih, bukan vonis** — tanpa skor, tanpa ambang. Ambang
Normal / Warning / Critical adalah milik pemilik, dan tidak bisa ditarik jujur
dari data yang belum ada. Alat yang menebaknya sudah menjadi mesin anomali,
dan itu prioritas 7.

## Lari

| lari | tingkat | hasil |
|---|---|---|
| `20260920T013538Z-burn-in-24h` | 24 jam | **tutup, 0 error** — 21 September 2026 01:35 UTC |
| `20260921T044023Z-burn-in-72h-attempt1` | 72 jam | **berhenti di menit ke-33** — host berhibernasi, bukan papan |
| `20260921T053430Z-burn-in-72h` | 72 jam | **tutup, 0 error** — 24 September 2026 05:34 UTC, `duration reached` |

Tingkat 168 jam belum dijalankan.

## Pengamatnya tidur — diukur dari catatan daya host

**Keempat belas diam panjang tingkat 1 adalah MacBook yang tidur.** Catatan
daya mesin ini sendiri (`pmset -g log`) memperlihatkan Mac dalam *Deep Idle*,
di baterai 88%, dengan **DarkWake setiap ±16 menit**: 21:32, 21:48, 22:05,
22:20, 22:37 … waktu lokal. Tingkat 1 dimulai 01:35:38 UTC; detik ke-46.600
jatuh tepat pada **21:32 lokal — DarkWake pertama**. Logger membeku bersama
Mac dan hanya membaca selama tiap DarkWake ±30–45 detik; itulah "diam ±925
detik, lalu ratusan detak terkuras". Papan tetap bekerja karena tidur biasa
tidak memutus daya USB — dan kerja terhadap jam papan 1,0002 sudah
mengatakannya sebelum sebabnya diketahui.

**Percobaan pertama 72 jam mati karena hal yang lebih berat: hibernasi.**

```
12:13:00 +0700  Sleep  "Low Power Sleep" ... Using AC (Charge:1%)
12:13:48 +0700  Wake   from Hibernate ... Using AC (Charge:3%)
```

Baterai habis sesudah berjam-jam di baterai, Mac masuk hibernasi walau sudah
tersambung charger, **hibernasi memutus daya USB**, dan papan kembali
menjalankan image pabrik LiteX dari flash — `No boot medium found`,
`litex>`. Logger mati pada detik yang sama dengan bangunnya Mac, 12:13:48.
Sampai detik itu lari bersih: 1.170 detak, 0 error.

**Dan alat saya berbohong tentang itu.** Ringkasan percobaan pertama menulis
`"ended": "duration reached"`, karena `burn_in.py` menamai setiap keluar
selain Ctrl-C sebagai lari yang selesai. Sekarang ia mencatat sebab
sebenarnya — `STOPPED EARLY: <jenis>: <pesan>` — dan ringkasan percobaan
pertama sudah dibetulkan dari catatan daya, dengan medan yang menyatakan
koreksinya. Berkas JSONL di sebelahnya dibiarkan persis seperti yang alat
tulis.

**Satu cacat lagi di alat saya, dan batas pengaruhnya.** Ringkasan yang
ditulis **di tengah lari** tertinggal satu detak: cacah detak sudah detak
sekarang, siklus dan error masih detak sebelumnya — sehingga laporan atas
lari yang hidup sempat berbunyi 430 terurai melawan 429 dipancarkan. Sudah
dibetulkan. **Ringkasan akhir tidak pernah terkena**: ia ditulis sesudah
detak terakhir selesai diproses, jadi hasil tingkat 1 tidak bergeser.
Percobaan kedua 72 jam dijalankan dengan kode sebelum perbaikan ini, jadi
ringkasan berkalanya akan tetap tertinggal satu detak sampai lari selesai;
ringkasan akhirnya tetap benar.

**Percobaan kedua menahan host tetap terjaga.** `burn_in.py` sekarang
memegang `caffeinate -s -i -w <pid>`: asersi daya macOS yang mencegah tidur
selama proses logger hidup, hanya di daya AC. Ia tidak mengubah satu pun
setelan dan berakhir bersama prosesnya. Satu hal tetap di luar jangkauan
alat: **Mac harus tetap tersambung ke charger yang cukup**, karena hibernasi
akibat baterai habis mengalahkan asersi apa pun.

## Tingkat 1 — hasil, 24 jam penuh

```
86.405,4 detik jam host      86.401,5 detik jam papan sendiri
54.893 detak dipancarkan papan   52.282 terurai host
56.210.432 siklus

0 error                      0 baca kartu gagal
kerja terhadap jam papan sendiri: 1,0002
```

**Keempat kriteria tingkat 1, dijawab dengan angkanya:**

| kriteria pemilik | hasil |
|---|---|
| tidak ada deadlock | **kerja menutupi waktu, 1,0002** — papan tidak pernah berhenti, termasuk di dalam diam-diam panjang yang host tidak melihat |
| tidak ada korupsi memori | **0 error** dari 54.893 detak; enam belas kata, dua jumlah, dan tumpukan dibandingkan tiap siklus |
| tidak ada watchdog timeout | **tidak bisa diukur — tidak ada watchdog di desain ini**, dan itu dikatakan di muka, bukan dilewatkan |
| tidak ada serial menggantung | **9 baris tak terbaca**, semuanya sesudah host berhenti membaca, dan tiap satunya dibuang utuh |

**Garis dasar yang ditinggalkannya** — ini yang lapisan pengawasan nanti
bandingkan, dan ia beku di `20260920T013538Z-burn-in-24h-baseline.json`:

```
laju kerja        638,7 / 650,4 / 660,1 / 661,2 siklus per detik  (min p50 p95 maks)
kerja per siklus  1,5375 ms
irama detak papan 1,5744 detik
jam papan − host  −3,8 detik, kemiringan −0,0292 detik/jam
```

Kemiringan itu **8,1 ppm** terhadap jam host selama sehari penuh — osilator
27 MHz papan diukur relatif terhadap jam mesin pengembangan, bukan terhadap
standar frekuensi.

**Lima belas diam, dan tidak satu pun milik papan.** Satu 140 detik, lalu
empat belas sejak jam ke-12,9 dengan pola ±925 detik tiap ±960 detik. Setengah
digolongkan "host" dan setengah "unclear"; yang "unclear" adalah **kurasan**
yang mengikuti tiap diam — ratusan detak tiba sekaligus, jadi jam papan maju
lebih jauh daripada jam host di interval itu. Keduanya sisi dari kejadian yang
sama, dan tak satu pun papan yang berhenti.

**Sembilan baris tak terbaca, semuanya sesudah diam**, dan bentuknya sama:
`4H`, `6062H`, `655620H`, `HH` — sebuah angka menempel pada penanda
berikutnya, yaitu satu baris baru yang hilang karena penyangga penerima meluap
selagi host pergi. Pengurainya membuang baris seperti itu utuh. Kalau ia
memeras digitnya, `6062H` akan jadi angka 6062 di dalam sebuah detak dan tak
seorang pun tahu.

**Dua angka di atas dibetulkan sesudah diterbitkan.** Versi pertama halaman
ini menulis 54.882 detak dan kerja 1,0. Alat laporannya mengambil cacah
detak dari sampel terakhir tetapi uptime dari ringkasan — dua momen yang
berselisih sampai semenit. Pada lari yang sudah selesai selisihnya 11 detak,
cukup kecil untuk tak terlihat; pada lari 72 jam yang baru berjalan 33 menit
ia terbaca sebagai host yang mengurai **lebih banyak** detak daripada yang
papan kirim — dan dari situ ketahuan. Sekarang ketiga angka diambil dari
detak yang sama. Kesimpulannya tidak bergeser; angkanya bergeser.

**Yang tidak dibuktikan lari ini**, supaya tidak tumbuh lebih besar dari
buktinya: ia satu lari, di satu papan, pada satu suhu ruangan yang tidak
diukur, dengan satu kartu. Ia mengatakan mesin ini bekerja sehari penuh tanpa
satu pun kesalahan yang bisa dilihat pemeriksaannya sendiri — bukan bahwa
tiap papan akan begitu.

## Tingkat 2 — hasil, 72 jam penuh

Ditutup 24 September 2026 05:34:30 UTC (12:34 WIB), langkah P0 urutan pemilik.
`burn_in.py` keluar sendiri; ringkasannya berbunyi **`duration reached`**, bukan
`STOPPED EARLY`.

```
259.204,9 detik jam host      259.198,5 detik jam papan sendiri
164.668 detak dipancarkan papan   160.967 terurai host
168.620.032 siklus

0 error                      0 baca kartu gagal
kerja terhadap jam papan sendiri: 1,0002
```

**Keempat kriteria yang sama, dijawab dengan angka lari ini:**

| kriteria pemilik | hasil |
|---|---|
| tidak ada deadlock | **kerja menutupi waktu, 1,0002** selama tiga hari — papan tidak pernah berhenti, termasuk di dalam 25 diam yang host tidak melihat |
| tidak ada korupsi memori | **0 error** dari 164.668 detak; pencacah error papan kumulatif, dan sampel terakhir di t = 259.160 detik tetap 0 |
| tidak ada watchdog timeout | **tidak bisa diukur — tidak ada watchdog di desain ini**, sama seperti tingkat 1 |
| tidak ada serial menggantung | **11 baris tak terbaca**, semuanya berbentuk angka yang menempel pada penanda berikutnya, dan semuanya di enam jam pertama |

**Bukti yang dibekukan (P0).** Ketiga artefak beserta sha256-nya:

| artefak | byte | sha256 |
|---|---:|---|
| `20260921T053430Z-burn-in-72h.json` | 712 | `09302ae1de43e7d06430a9aa4c26acf2a45afca7cc60591c33e7cb62b31c6ddf` |
| `20260921T053430Z-burn-in-72h.jsonl` | 855.293 | `910deac1b8ebde20efbde3c96ececf408891aa50baebb1e1e45d7458b12a45ae` |
| `rtl/fpga/gowin/hcpu_gowin_top_loader.fs` | 7.261.470 | `84fdc91232465c9600e1f7cc59dba891f309c69cf2441c448d684baaf4a7e261` |

Bitstream itu bertanggal 18 September 2026 21:14, tiga hari sebelum lari mulai,
dan **tidak dibangun ulang** selama lari. **Satu selisih historis yang tidak bisa
diverifikasi:** catatan sesi sebelumnya menyebut sidik jari loader
`4a0a1bfd…`, dan angka itu tidak cocok dengan satu pun dari sembilan `.fs` di
direktori dan tidak ada di berkas mana pun di repositori. Berkas `.fs`
di-gitignore, jadi tidak ada riwayat yang bisa memutuskan. Yang berlaku mulai
sekarang adalah `84fdc912…`; angka lama dicatat sebagai selisih historis,
**tidak direkonstruksi dan tidak "dibetulkan"** (perintah pemilik, 24 September
2026).

**Dua baris `error` adalah artefak pengurai, bukan error papan** — K-1, dan
sekarang diperiksa pada JSONL final, bukan pada log setengah jalan:

1. `rtl/programs/burn_in.hasm` menyebut pencacah error-nya *"One more error, and
   never a reset"* — kumulatif. Satu error yang pernah dihitung papan akan
   terbawa di **setiap** sampel sesudahnya.
2. Kedua baris itu, di t = 11.713,148 dan 12.685,786 detik, masing-masing
   didahului **pada detik yang sama** oleh baris tak terurai `0H`. Medannya
   bergeser: `errors` berisi 7.440 dan 8.058 — seukuran nomor detak di
   sekitarnya, yang berbunyi 7.194 dan 7.812 — sementara `wraps` berisi 0 dan
   `counter_hi` 73 dan 79, seukuran `wraps` tetangganya. Kesebelas baris tak
   terurai berbentuk sama: `33H`, `10H`, `52H`, `0H`, `0H`, `9729H`, `1H`,
   `4400H`, `1H`, `2H`, `3777H`. Yang membedakan kedua baris ini hanyalah
   angkanya kebetulan `0`.
3. **3.901 sampel sesudah baris kedua semuanya berbunyi `errors 0`**, dan nilai
   `errors` tertinggi di seluruh 3.991 sampel adalah **0** — dari sampel pertama
   di t = 5,5 detik sampai terakhir di t = 259.160,2 detik.

**Yang tidak diklaim lari ini: pengurainya belum tervalidasi terhadap capture
mentah.** `burn_in.py` tidak menyimpan byte dari kabel, jadi lari ini tidak bisa
diurai ulang dari byte-nya. Yang dibuktikan di atas adalah laporan pengurai,
pencacah papan, dan artefak log yang ada — bukan pengurai yang diadu dengan
kabelnya. Validasi itu menunggu lari berikutnya (K-7, langkah P1).

**Diam berhenti sesudah enam jam pertama.** 25 diam, total 14.904 detik,
seluruhnya antara t = 5,5 dan t = 20.724,9 detik; tujuh digolongkan milik host,
tujuh belas "unclear" — kurasan yang mengikuti tiap diam, ratusan detak tiba
sekaligus. Sesudah itu **66,2 jam tanpa satu pun diam**, dan tak satu diam pun
milik papan.

**Garis dasarnya**, beku di `20260921T053430Z-burn-in-72h-baseline.json`:

```
laju kerja        647,3 / 650,4 / 652,5 / 671,2 siklus per detik  (min p50 p95 maks)
kerja per siklus  1,5375 ms
irama detak papan 1,5744 detik
jam papan − host  −4,3 detik (p50), −6,4 detik di akhir, kemiringan −0,0375 detik/jam
```

**Terhadap garis dasar 24 jam — selisih, bukan vonis:**

| besaran | garis dasar 24 jam | terukur 72 jam | selisih |
|---|---:|---:|---:|
| siklus per detik, p50 | 650,4234527687 | 650,4234527688 | +0,000% |
| siklus per detik, p95 | 660,099 | 652,549 | −1,144% |
| irama detak seperti dilihat host, p50 | 2,012 s | 1,543 s | −23,310% |
| irama detak seperti dilihat host, p95 | 2,021 s | 1,800 s | −10,935% |
| jam papan − host, p50 | −3,8 s | −4,3 s | +13,158% |
| kemiringan | −0,0292 s/jam | −0,0375 s/jam | +28,425% |
| irama detak papan | 1,5744 s | 1,5744 s | +0,000% |
| kerja per siklus | 1,5375 ms | 1,5375 ms | +0,000% |
| kerja terhadap jam papan | 1,0002 | 1,0002 | +0,000% |
| error | 0 | 0 | — |
| baca kartu gagal | 0 | 0 | — |
| baris tak terbaca | 9 | 11 | +2 |

Dua di antaranya punya sebab terukur, bukan misteri. **Irama detak yang dilihat
host turun 23%** karena tingkat 1 berjalan dengan timeout baca satu detik dan
angkanya menumpuk di 1,0 dan 2,0 detik; lari ini memakai timeout lebih pendek,
jadi angkanya lebih dekat ke irama papan yang sebenarnya, 1,5744 detik — yang
**tidak bergerak sama sekali** di antara kedua lari. **Kemiringan jam** naik
dari −0,0292 jadi −0,0375 detik/jam, yaitu dari 8,1 ppm ke 10,4 ppm terhadap
jam host. Itu pengukuran burn-in, bukan kegagalan: osilator 27 MHz papan diukur
relatif terhadap jam MacBook, bukan terhadap standar frekuensi, dan −6,4 detik
dalam 72 jam adalah bentuk yang sama dengan −3,9 detik dalam 24 jam.

**Yang tidak dibuktikan lari ini**: satu lari, satu papan, satu kartu, satu suhu
ruangan yang tidak diukur, dan satu bitstream. Ia mengatakan mesin ini bekerja
tiga hari penuh tanpa satu pun kesalahan yang bisa dilihat pemeriksaannya
sendiri — bukan bahwa tiap papan akan begitu. Tingkat 168 jam belum dijalankan.

## P1 — byte kabel jadi bukti primer, 24 September 2026

Perintah pemilik sesudah P0: *"raw capture menjadi evidence primer; parser
tidak lagi menjadi sumber bukti primer."* Bentuknya sekarang dua alat, dan
`burn_in.py` **tidak disentuh** — perintah pemilik hari yang sama, supaya
seluruh rekaman yang pernah ditulisnya tetap berarti seperti dulu.

```
UART/USB → burn_in_capture.py → <id>-capture.raw       byte, apa adanya
                              → <id>-capture.times.jsonl  offset dan jam host
                              → <id>-capture.json         manifes
         → burn_in_parse.py   → <id>-parsed.jsonl      detak dan parse error
                              → <id>-parsed.json       ringkasan
```

`burn_in_capture.py` **tidak mengurai satu baris pun** — itu inti pemisahannya,
dan sebuah tes membaca sumbernya untuk memastikan ia tidak belajar mengurai.
Manifesnya mencatat tujuh hal yang pemilik minta: byte mentah, jam host, identitas
perangkat, sidik jari bitstream, waktu mulai dan selesai, jumlah byte, dan
SHA256. Sidik jari dihitung dari berkas yang dimuat, bukan dikutip dari catatan.

### Capture pendek pertama

Bitstream yang sama dengan lari 72 jam, **tanpa dibangun ulang**:
`hcpu_gowin_top_loader.fs`, sha256 `84fdc912…`.

| | |
|---|---|
| lari | `20260924T073655Z-burn-in` |
| mulai / selesai | 2026-09-24 07:36:55 UTC → 07:48:59 UTC (12,0 menit) |
| byte | **9.940** dalam 462 pembacaan |
| sha256 raw | `31e69b52ae17d44063a5e18a6a2ec36bf0fe8e0629b358a3887ed691596a13ae` |
| berhenti karena | `duration reached` |

Diurai **offline** dari byte itu, bukan dari kabel:

| | |
|---|---|
| baris | 3.206 |
| detak | **457**, bernomor 1..457 |
| siklus pertama | 28, 3072, 178 — dan kata kartu `0x48465331`, yaitu `HFS1` |
| **board errors** | **0** |
| gagal baca kartu | 0 |
| **parse errors** | **0** |

**Konsisten dengan garis dasar 72 jam**, dan itu yang membuat capture ini
berarti: irama detak papan **1,5736 detik** melawan 1,5744 di garis dasar, dan
**650,72 siklus per detik** melawan 650,423. Jam papan berjalan +0,124 detik
terhadap jam host selama 717 detik — **bukan** pengukuran hanyut: pembacaan host
bergrain 0,25 detik, sedangkan kemiringan garis dasar hanya −0,0075 detik
sepanjang dua belas menit. Capture sependek ini tidak bisa mengukur hanyut, dan
tidak mengklaimnya.

Byte yang sama diurai dua kali memberi ringkasan yang identik, dan pengurai
menolak berjalan kalau SHA256 berkas raw tidak lagi sama dengan yang dicatat
manifes.

### Baris rusak ditolak, dan tidak pernah jadi error papan

Pengurainya membaca tata bahasa, bukan menghitung angka: satu detak adalah `H`
diikuti **tepat enam** angka desimal di bawah 2³². Di luar itu **parse error**,
membawa offset byte, teksnya apa adanya, dan alasannya — dan **fields yang
sedang tertunda dibuang**, karena persis begitulah sebuah detak bergeser dibuat.

| yang pemilik daftarkan | alasan yang dicatat |
|---|---|
| merged record | `merged_record` — `0H`, `HH`, `12H34` |
| truncated record / medan hilang | `truncated_record` |
| medan tidak sah | `non_numeric_field` — `335544;<`, `1A2B`, `error` |
| jumlah medan tak terduga | `unexpected_field_count` |
| baris sebagian | `partial_line` |

Pemilik menulis "invalid hexadecimal field"; kabel ini desimal — PRINT mencetak
desimal, dan programnya menjaga tiap angka di bawah sejuta karena PRINT salah di
atas 2²² — jadi digit heksadesimal adalah satu kasus `non_numeric_field`, dan
tidak disebut heksadesimal supaya format yang papan tidak pancarkan tidak ikut
diklaim.

**Bentuk tingkat 2 diputar ulang terhadap kedua pengurai**, dengan angkanya
sendiri: sebuah detak terbuka dan memberi medan pertamanya 7.194; newline
sebelum penanda berikutnya hilang, jadi `0H` tiba sebagai satu baris; medan
sesudahnya milik detak lain, 7.440 di antaranya. Pengurai lama membuang baris
gabungan itu tetapi **menyimpan yang tertunda**, jadi medan-medan itu menutup
detak yang terbuka satu tempat bergeser — `errors` memegang nomor detak 7.440 —
dan menulis baris `error` yang ada di log. Pengurai baru menolak baris gabungan
itu, membuang yang tertunda, dan hitungan papan tetap 0.

### Yang P1 tidak klaim

**Pengurai lari 72 jam tidak tervalidasi terhadap capture mentah.** Lari itu
tidak menyimpan byte, jadi tidak bisa diurai ulang dari kabelnya; buktinya tetap
yang dikunci di P0. Yang tervalidasi di sini adalah **capture pendek baru dan
pengurai offline**-nya.

## Dua temuan dari membangun lab ini

Keduanya dicatat penuh di [OFF.md](../OFF.md), keduanya **dilaporkan bukan
diperbaiki** (K9):

1. **`PRINT` salah untuk angka besar** — 2²³ kembali sebagai `8388600`, dan dari
   2²⁵ ke atas muncul karakter `:` sampai `?`, yaitu nilai digit 10–15.
2. **Kartu gagal init sesudah rekonfigurasi di tengah pembacaan** — delapan
   peluncuran dari delapan, berselang-seling. Satu percobaan gagal berharga
   ±3,3 detik, jadi lari yang kartunya tak naik merangkak; `burn_in.hasm`
   karena itu menyerah sesudah delapan percobaan dan `burn_in.py` meluncurkan
   ulang.

Keduanya ditemukan karena lab ini dijalankan di papan sebelum dipercaya sehari
penuh — bukan karena dibaca dari kode.

## Mengulanginya

```bash
python3 rtl/scripts/burn_in.py                                   # rencananya saja
python3 rtl/scripts/burn_in.py --port /dev/tty.usbserial-<port> --hours 24 --label 24h
python3 rtl/scripts/burn_in_report.py cosmictera-build/burn-in/<id>.jsonl --write
python3 -m pytest -q tests/test_integrity/test_burn_in.py
```

Alat ini memuat bitstream slot CPU sendiri dan meluncurkan ulang kalau kartu
tidak naik. Sesudah program terkirim **papan tidak membutuhkan host**: kalau
host pergi, yang hilang catatannya, bukan larinya.

Catatan ditulis ke `<id>.jsonl` — tiap detak yang menaikkan pencacah kesalahan,
tiap diam di atas ambang, dan satu contoh per menit — dan ringkasan `<id>.json`
ditulis ulang **tiap menit**, bukan hanya di akhir: lari berhari-hari tidak
boleh kehilangan vonisnya karena host ditutup di menit terakhir.
