# Portal 8888 — Bukti Simulasi

## V1 active measurement, 1 October 2026

`make sim_portal` completed one end-to-end simulation: five provisioning slots
were written, locked, and a post-lock overwrite was rejected; a 9,216-byte PHY
frame produced the exact 125-byte body and HMAC expected by
`ref/portal_ref.py` (`0 wrong`). `make r3` detected 3/3 reference mutations:
a sealed body field change, SOF timestamp displacement, and frame-hash
mismatch. The RTL bench independently checks post-lock key overwrite.

This is simulation and synthesis only: the v1 synthesis cell count is in §7,
the Tang Nano 20K wrapper is in §9, and no board result is claimed.

Diukur ulang di Mac, 1 Oktober 2026: Icarus Verilog 14.0 (devel s20260301),
Yosys 0.68+138, Python 3.13.15 — semuanya dari oss-cad-suite dan sistem yang
sama dengan gerbang repo. Satu perintah mengulang seluruhnya dari build bersih:

```sh
cd portal8888 && make clean && make      # lima bench + pemeriksaan byte sistem
make ref                                 # model perangkat lunak + kampanye
make synth                               # hitungan sel yosys per modul
```

Mesin HMAC-SHA256 dibaca dari `../rtl`, bukan salinan, dan identik byte demi
byte dengan commit `4bff781` (207/207 di papan):

```
hijaiyyah_hmac.v          6b7ede607f32b7582a96d98e82ef1e6b7ac18c74caba4d4b066d998e48086cbc
hijaiyyah_sha256_core.v   289e5eac4cb6556e7fd31db812943c29a621ed932a4170f21221ea04a67c67d6
hijaiyyah_sha256_stream.v f767fee5cb85170bb223894f41027404cf5c6aeda9b00cb7bb12ddd8892bdd6a
```

Tiap bench keluar non-nol saat gagal, dan tiap pemeriksaan sudah disabotase
(R3) — tabelnya di §8.

## 1. Cap-waktu GPS-PPS (`tb_timestamp`)

Simulasi memakai `TPS` = 200.000 tick/detik, jadi 1 tick = 5.000 ns di sini;
37 ns adalah hitungan untuk 27 MHz, bukan pengukuran.

```
disc sec 0..5 : sec naik 1700000001..1700000006 dari UTC yang diprovisi, tick 0
                tiap PPS, locked=1, ppm_est=50, warn=0
holdover 3 s  : locked=0 holdover=1 drift=149965 ns (50 ppm x 3 s = 150000, dalam 1 tick)
RESULT        : 0 wrong
```

Yang diuji: disiplin PPS dan masuknya holdover. **Yang tidak diuji bench ini,
dan cacat ketika diuji** — diagnostik di luar suite, kristal 50 ppm, PPS hilang
3 detik lalu kembali:

```
detik UTC sebenarnya   7 : sec=4 tick=0     ppm_est=-6262 warn=1
detik UTC sebenarnya   8 : sec=5 tick=0     ppm_est=50
```

- **Tiga detik hilang permanen.** Selama holdover `sec` tidak bergerak dan
  `tick` terus naik melewati `TPS` (600.033 pada detik ke-6); PPS berikutnya
  hanya menambah `sec` satu.
- **`ppm_est` meluap** pada PPS pertama sesudah holdover: ia menghitung tick
  tiga detik terhadap satu `TPS`.
- Selama holdover, `T_tick` yang disegel adalah tick sejak PPS terakhir, bukan
  pecahan detik.
- `sec` menghitung PPS sejak reset. Modul ini tidak punya masukan waktu-hari
  (mis. pesan NMEA), jadi ia mengunci **fase** detik UTC, bukan **nilai** UTC.
- Jalur `ppm_warn` = 1 tidak dijalankan bench (50 ppm < `PPM_WARN` 100).

RTL tidak diubah: memilih perilaku holdover adalah keputusan desain.

## 2. jim_sync + jim_index (`tb_jim`)

Vektor dari `ref/vectors.py`: 32 frame `model.build` k=1 berantai, penanda
frame ke-i membawa i mod 4 bit salah, dan hit yang diharapkan dicari brute
force di seluruh aliran.

```
jim_sync : 50.528 bit, 24 hit, 0 salah   (Hamming 0,1,2 kena; 3 tidak; ambang 2)
jim_index: 3.124 langkah, 0 salah, kembali ke (1,0,0,0,0) tepat di langkah 3124
```

Bench lama hanya menghitung hit di tempat yang salah. Dengan korelator yang
tidak pernah berbunyi ia melapor `0 hits, 0 wrong` dan keluar 0; kini hit yang
hilang dihitung salah, dan `jim_index` yang tidak kembali ke awal juga.

## 3. ingress_parse (`tb_ingress`)

```
ingress_parse: 3.000 frame, 3.000 tepat, 0 salah
  (Ethernet/VLAN/IPv4/IPv6/TCP/UDP/ARP/ICMP/terpotong/ekstensi-v6)
```

Vektornya `packets.random_frames(3000)` dengan benih 20261001, dan
sabotase offset VLAN memberi tepat 327 salah — angka yang sama dengan lari
sandbox, jadi vektornya sama.

Dua batas, diukur dengan diagnostik di luar suite:

- **Frame harus dipisah sekurangnya satu clock diam.** Byte pertama yang tiba
  pada clock sesudah `last` dibuang: frame kedua terbaca `NOT_IP` dengan MAC
  `223344556608`, seharusnya `OK` dan `112233445566`. Dengan satu clock jeda,
  keduanya benar.
- **Frame lebih dari 2.047 byte salah baca**: pencacah 11 bit membungkus. Frame
  2.358 byte terbaca `NOT_IP` dengan MAC dari isi payload. Frame Ethernet
  standar (≤ 1.522 byte) tidak sampai ke sana; jumbo frame sampai.

## 4. FSM Portal lama satu putaran (`tb_portal8888`) — tidak lagi dijalankan

Bench ini milik top lama (badan sudut 64 byte) dan vektornya tidak lagi
dibangkitkan: `ref/portal_ref.py` kini menulis vektor v1. Hasil di bawah adalah
ukuran 1 Oktober 2026 atas top lama; rantai dan ROOT top v1 diuji di §9.

```
portal8888: round=1  TAG_A..D OK  ROOT OK  (0 mismatch vs ref/portal_ref.py)
```

## 5. Sistem lama: GPS-PPS -> cap-waktu -> segel (`tb_portal8888_system`)

Bench ini menjalankan top lama, `hijaiyyah_portal8888_legacy_unwired`, yang
tinggal di berkas yang sama dengan top v1.

Satu putaran disegel dengan cap-waktu yang dibaca dari jam GPS di dalam
simulasi; `ref/portal_sys_check.py` menghitung ulang tiap byte dengan
hashlib/hmac dan keluar non-nol bila ada yang beda.

```
GPS-PPS: PPS 1 sec=1; PPS 2 sec=2; locked=1 ppm_est=50 holdover=0
  corner 0: sec 2 + tick 50001   527 clock   tag=ef76d4ae..
  corner 1: sec 2 + tick 50529   527 clock   tag=604ffee3..
  corner 2: sec 2 + tick 51057   527 clock   tag=62e0f98a..
  corner 3: sec 2 + tick 51585  1187 clock   tag=b152aa08..   (sudut + portal)
  portal  : round=1  total 2773 clock   root=ce46f59d..
verifikasi Python: corner 0..3 tag OK, portal ROOT OK -> ALL BYTE-EXACT
```

**Arti selisih sub-detiknya.** Keempat rekaman tersedia sejak awal, dan bench
membaca jam pada clock FSM menerima tiap rekaman. Jarak 528 tick adalah 527
clock penyegelan satu sudut ditambah satu clock jabat tangan — jadi cap-waktu
itu mencatat **kapan FSM bebas**, bukan kapan sinyal tiba. Yang terbukti:
FSM menyegel cap-waktu hidup dari modul jam apa adanya, byte demi byte.
Penguncian waktu tiba di byte pertama frame (SOF) — yang L0 `ARCHITECTURE.md`
tuntut justru supaya antrean tidak masuk ke cap-waktu — tidak ada di top lama
ini; top v1 punya, dan itu diuji di §9.

VCD seluruh sinyal hanya ditulis dengan `make vcd`.

## 6. Kampanye serangan (model perangkat lunak, `ref/`)

```
rantai 4 sudut + portal + jangkar: 16 kelas x 300 percobaan
  ubah/sisip/hapus/replay/tukar/rollback  -> 300/300 terdeteksi
  (hapus-ekor & rollback: 300/300 DENGAN jangkar, 0/300 tanpa jangkar)
  log bersih: 0/300 positif palsu
bukti asal sinyal (ingress): 9 kelas x 300
  ubah IP/port/MAC, pindah port fisik, ubah urutan, tukar bukti,
  hapus semua catatan satu IP, hapus terbaru, sisip tanpa kunci  -> 300/300
  log bersih: 0/300 positif palsu
  IP dipalsukan di asal (UDP): tercatat apa adanya (batas yang jujur)
```

- Kampanye bukti asal berjalan atas catatan `ref/provenance.py`, bukan atas
  badan yang RTL segel. Badan sudut RTL (64 byte: PORT, T_sec, T_tick, SRC_IP,
  SPORT, DPORT, PROTO, IDX, PREV) **tidak memuat MAC, CTR, DEV, status parse,
  maupun hash frame** — jadi "ubah MAC", "ubah urutan (CTR)", dan "tukar bukti
  frame mentah" 300/300 berlaku untuk model, belum untuk segel RTL. Field
  waktu RTL juga tidak memuat `T_sumber` dan `T_uncert` yang L1 wajibkan.
- "hapus ekor" dan "rollback ke salinan lama" di `campaign.py` adalah operasi
  yang sama — membuang putaran terakhir — jadi keduanya satu kelas, bukan dua.
- Benih per kelas kini `zlib.crc32(nama)`; dulu `hash(nama)`, yang Python acak
  per proses, jadi percobaannya tidak bisa diulang persis.

## 7. Sintesis v1 (GW2AR-18C, `synth_gowin -nodsp`, sebelum place and route)

```
modul                     LUT1-4   ALU    DFF  MUX2   LUT%  DFF%
hijaiyyah_hmac              4207   474   2659   604   20.3  17.1
hijaiyyah_portal8888       12482  1597   7915  2330   60.2  50.9  (L1 v1 + HMAC)
hijaiyyah_timestamp         1480   848    256   492    7.1   1.6
ingress_parse                544   129    470    57    2.6   3.0
ingress_parse_v1             977   182    474   242    4.7   3.0
jim_index                     32    12     15     9    0.2   0.1
jim_sync                     166    18     41   122    0.8   0.3
```

Persen terhadap 20.736 LUT4 dan 15.552 DFF papan. Ini hitungan sel sintesis,
bukan LUT4 sesudah place and route.

- Portal L1 v1 memakai 12.482 LUT1-4 (60,2%), 7.915 DFF (50,9%), dan 6 BSRAM
  (`DPX9B`) dari 46 — terukur 3 Oktober 2026, Yosys 0.68+138. Buffer frame
  9.216 byte dan lima blok kunci 64 byte adalah RAM sinkron tanpa reset; body
  tersegel tidak disalin ke register sendiri, dan FRAME_HASH dibaca langsung
  dari mesin SHA-256 frame (keputusan pemilik, 3 Oktober 2026).
- Dulu: buffer di blok ber-reset asinkron menjadi 73.728 register, 95.670
  LUT1-4 (461,4%) dan 85.290 DFF (548,4%); lalu dengan buffer di RAM tetapi
  kunci dan body di register, 13.437 LUT1-4 dan 11.597 DFF.

## 8. Sabotase (R3)

Tiap baris: satu perubahan pada salinan RTL, bench yang menjaganya, hasilnya.

```
jim_sync     hit tidak pernah berbunyi      bench lama: 0 hits, 0 wrong, exit 0
                                            bench kini: missed hit, exit 1
jim_sync     ambang <= T jadi < T           16 dari 24 hit, exit 1
jim_index    baris d4 jadi (0,0,0,1,0)      3108 salah, exit 1
ingress      offset VLAN 18 jadi 17         327 salah, exit 1
timestamp    skala ppm 1e6 jadi 1e5         ppm_est=5, 6 salah, exit 1
timestamp    holdover tak naik saat timeout 1 salah, exit 1
portal       SPORT/DPORT bertukar           TAG+ROOT BAD; cek sistem 5 MISMATCH, exit 1
portal       urutan TAG_A/TAG_B di ROOT     ROOT BAD; cek sistem ROOT MISMATCH, exit 1
portal v1    alamat baca buffer tak maju    tag BAD, 3 salah, exit 1
portal v1    byte pertama frame tak ditulis tag BAD, 3 salah, exit 1
```

`make sim_system` menghapus `portal_sys_result.txt` sebelum lari: tanpa itu,
bench yang gagal dikompilasi meninggalkan hasil lama, dan pemeriksaan byte
membaca hasil lama itu lalu melapor OK. Itu terjadi sekali saat sabotase ini
dijalankan.

## 9. Pembungkus Tang Nano 20K lewat UART (`tb_hijaiyyah_portal8888_gowin_top`)

`fpga/gowin/hijaiyyah_portal8888_gowin_top.v`, terukur di Mac 3 Oktober 2026.
Bench hanya menggerakkan pin UART pada clock 27 MHz dan tidak menilai apa pun:
tiap byte jawaban ditulis ke `build/portal_top_reply.txt`, dan
`ref/portal_uart.py check` menghitung ulang semuanya dengan hashlib/hmac.

```
make sim_gowin_top          23 perintah, 2.700.000 baud (10 clock per bit):
                            8 segel, 2 drop, 3 jangkar, 8 status, 2 ditolak -> 0 salah
make sim_gowin_top_115200   12 perintah pada 115200, laju papan:
                            4 segel, 1 jangkar, 7 status -> 0 salah
```

Yang dijalankan skenario penuh, dan baru di sini RTL v1 menjalankannya:

- frame sebelum provisioning di-drop; lima kunci, lock, lalu penimpaan slot 2
  sesudah lock tidak mengubah apa pun — segel sudut C tetap sah di bawah kunci
  yang pertama;
- delapan catatan di empat port: IPv4 TCP, IPv6 UDP, VLAN, ARP, IPv4 dengan
  opsi, ICMP, frame terpotong 27 byte, dan jumbo 9.216 byte. Tiap body 125
  byte dibongkar, tiap field amatan dihitung ulang dari frame yang dikirim, dan
  TAG = HMAC(K_sudut, body);
- **rantai PREV dan IDX per sudut**, **ROOT dua putaran**, dan **jangkar
  kepala** (putaran, ROOT, TAG_A..D), dibaca tiga kali;
- frame 9.217 byte di-drop dengan flag overflow, dan catatan sesudahnya tetap
  sah;
- cap waktu tiap catatan sama dengan jam Portal pada byte pertama frame, yang
  bench catat sendiri di `build/portal_top_sof.txt`.

Satu perilaku RTL yang terukur dan **tidak tertulis di kontrak**: frame yang
sudah mulai ditangkap lalu overflow tetap mengambil satu nilai `CTR`, jadi
catatan berikutnya melompat dua; frame yang tiba sebelum provisioning tidak
mengambilnya. Pemeriksa memodelkan perilaku itu apa adanya.

Sabotase (R3), tiap baris satu perubahan pada salinan, bench dan pemeriksa
penuh:

```
pembungkus   last satu byte lebih awal            9 salah, bench berhenti, exit 1
pembungkus   tagA dan tagB tertukar               3 jangkar salah, exit 1
pembungkus   flag overflow dibuang                1 salah, exit 1
portal v1    cap waktu bergeser satu tick         8 salah, exit 1
portal v1    urutan TAG di ROOT                   3 jangkar salah, exit 1
portal v1    PREV tidak dirantai                  4 salah, exit 1
portal v1    IDX sudut C tidak naik               1 salah, exit 1
portal v1    kunci bisa ditimpa sesudah lock      2 salah (TAG sudut C), exit 1
portal v1    muat kunci berhenti satu byte awal   11 salah, exit 1
portal v1    ROOT disegel dengan kunci sudut D    3 jangkar salah, exit 1
portal v1    kunci sudut selalu slot 0            6 salah, exit 1
portal v1    FRAME_HASH nol di body               8 salah, exit 1
```

**Place and route selesai** sesudah perampingan, `make portal8888_bitstream`,
3 Oktober 2026, yosys 0.68+138 -> nextpnr-himbaechel 0.11.1-19 -> gowin_pack,
GW2AR-LV18QN88C8/I7, flag bawaan, 17 menit:

```
IOB           10 /    384    2%
LUT4      15.848 / 20.736   76%
DFF        8.080 / 15.552   51%
ALU        1.840 / 15.552   11%
BSRAM          6 /     46   13%
bitstream  7.261.470 byte, sha256 bbf91a4d6c883983f667de00b24d123a421189172f52674aab6cacb7f31162b3
```

nextpnr mencetak 77,03 MHz sesudah routing untuk clock 27 MHz ini. **Fmax tidak
diklaim**, dengan alasan yang sama seperti pada pembungkus HMAC; yang
ditunjukkan angka itu hanya jarak di atas 27 MHz.

**Di papan, 3 Oktober 2026 (run `20261003T053504Z`).** Bitstream itu dimuat ke
SRAM dengan `openFPGALoader -b tangnano20k -m` atas perintah pemilik (papan
terdeteksi GW2A(R)-18(C)), lalu `scripts/portal8888_uart_test.py` lewat
`/dev/cu.usbserial-20250303171` pada 115200, skenario penuh, dengan pemeriksa
yang sama dengan bench:

```
portal8888 gowin top: 23 commands, 8 sealed, 2 dropped, 3 anchors, 8 status,
2 refused -> 0 wrong
```

Dari byte mentahnya: delapan catatan di empat port, `T_source` = 0 di atas
detik UTC host, `T_uncert_ns` naik dari 50.000.000 ke 50.105.046 selama dua
detik berjalan bebas (50 ppm), `CTR` melompat 6 -> 8 melewati frame yang
overflow, dan jangkar terbaca putaran 1 lalu putaran 2. Byte mentah jawaban
ada di `build/portal_board_20261003T053504Z.txt`, di luar git, sha256
`bb9450d76ea61990...`. 
**Frame asli, run `20261003T053754Z`.** Bitstream yang sama dimuat ulang, lalu
skrip yang sama dengan `--pcap`: 200 frame Ethernet yang pemilik tangkap di
`en0` Mac ini dengan `tcpdump` (61.534 byte, 54 sampai 1.454 byte; 85 IPv4 dan
115 IPv6; 177 TCP, 22 UDP, 1 ICMPv6), bergiliran di port 0..3 sesudah skenario:

```
portal8888 gowin top: 224 commands, 208 sealed, 2 dropped, 4 anchors, 8 status,
2 refused -> 0 wrong
```

Jangkar terakhir terbaca putaran 52. Byte mentah jawaban di
`build/portal_board_20261003T053754Z.txt`, sha256 `4ede09355d1ba00f...`;
tangkapannya `/tmp/portal8888_capture.pcap`, sha256 `865c644e7a7ce537...`, di
luar repo. Dua lari, satu papan; frame tetap dikirim host lewat UART, dan lari
berulang belum dijalankan.

Yang dirampingkan (keputusan pemilik, 3 Oktober 2026), tiap langkah dengan
bench penuh: lima kunci ke RAM blok, ditulis per byte dan dimuat ke `h_key`
sebelum HMAC; `sealed_body` tidak lagi register; `cur_hash` dibuang. Kebutuhan
situs LUT turun dari 25.487 ke 20.344 lalu ke 19.240 (92,8%).

**Sebelum perampingan place and route tidak selesai.** 3 Oktober 2026,
nextpnr-himbaechel dari oss-cad-suite dengan flag bawaan. Pengemasan
melaporkan 17.840 LUT4 (86%), 12.290 DFF (79%), 1.848 ALU, 5 BSRAM dari 46,
dan 10 IOB. Sesudah itu penempat analitik utama berjalan 60 menit atas 20.813
sel tanpa menyelesaikan satu iterasi pun, lalu dihentikan. Tidak ada
bitstream dan tidak ada angka timing.

**Sebabnya terukur: desain itu tidak muat seperti yang disintesis.** Di papan
ini flip-flop yang masukan D-nya bukan dari LUT-nya sendiri tetap memakai satu
situs LUT. Dari netlist: 12.290 flip-flop, 4.489 berpasangan dengan LUT-nya
(angka yang sama dengan `Constrained 4489 LUTFF pairs` nextpnr), 154 diberi
ALU, dan 7.647 tidak berpasangan — 7.001 di antaranya diberi langsung oleh
flip-flop lain, 639 oleh mux lebar. Kebutuhan situs LUT jadi 17.840 + 7.647 =
25.487 dari 20.736 (123%), kelebihan sekitar 4.750 situs. Yang jelas asalnya:
lima kunci (2.568 flip-flop), `h_key` (512), dan register geser kunci di
pembungkus (504).

Aturan itu diuji terpisah dengan desain buatan (register geser di samping awan
LUT, tanpa satu pun pasangan), alat dan flag yang sama:

```
LUT4  6.235 (30%) + DFF 4.000 (25%) = 10.235 situs   penempatan selesai
LUT4  8.203 (39%) + DFF 5.000 (32%) = 13.203 situs   penempatan selesai
LUT4 13.524 (65%) + DFF 9.000 (57%) = 22.524 situs   ERROR: Unable to find legal
                                                     placement for all cells
LUT4 14.371 (69%) + DFF 9.000 (57%) = 23.371 situs   ERROR yang sama
```

Keempatnya di bawah kapasitas LUT dan DFF masing-masing; yang gagal adalah
dua yang jumlahnya melewati 20.736, keduanya dalam setengah menit. Pembanding lain, pembungkus HMAC (LUT4 5.181, DFF
3.603), selesai dalam 57 detik dengan iterasi tercetak tiap kurang dari satu
detik. Pada Portal, log `--debug-placer` menunjukkan penempat berputar di
legalisasi: 104.888 baris `Legalising` di menit pertama, sebagian besar
flip-flop, dengan sel yang sama diulang sampai 7.605 kali.

Batasnya: kunci datang dari host, jadi host mengenalnya — provisioning
laboratorium, bukan akar kepercayaan. Tidak ada pin PPS, jadi tiap catatan
membawa `T_source` = 0 di atas detik UTC yang host provisi. Frame datang dari
host lewat UART, bukan dari kabel jaringan.

## Status

```
model software + kampanye        VALIDATED (Mac, benih stabil)
ingress_parse legacy             VALIDATED sim (3000/3000); batas legacy tetap
                                 frame > 2047 B dan frame tanpa jeda
ingress_parse v1                 VALIDATED sim: dua jumbo 9.216 B kontinu benar
cap-waktu GPS-PPS v1             VALIDATED sim: UTC provision, disiplin,
                                 holdover kontinu, sumber dan ketidakpastian
jim_sync / jim_index             VALIDATED sim
FSM Portal L1 v1                 VALIDATED sim: body 125 B, SOF, SHA-256,
                                 provisioning write-once + lock, byte-exact
R3 L1 v1                         VALIDATED sim: body, SOF, hash 3/3; overwrite
                                 kunci setelah lock terdeteksi oleh bench
pembungkus UART Tang Nano 20K    VALIDATED sim lewat pin UART (§9): rantai PREV,
                                 ROOT, jangkar, drop; R3 12/12
PnR Tang Nano 20K                SELESAI (§9): 15.848 LUT4, 8.080 DFF, 6 BSRAM;
                                 bitstream 7.261.470 byte; Fmax tidak diklaim
papan Tang Nano 20K              VALIDATED dua lari (§9): skenario 23 perintah, lalu
                                 200 frame asli (224 perintah), 0 salah; lewat UART,
                                 tanpa PPS
Ed25519 otorisasi                BELUM (desain)
```
