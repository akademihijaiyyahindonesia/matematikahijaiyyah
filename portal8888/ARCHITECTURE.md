# Portal 8888 — Arsitektur Lengkap

**Label: [EH] / DESAIN.** Portal 8888 adalah workstream eksperimental:
tervalidasi di simulasi dan belum punya bukti fisik. Angka yang ditandai
"terukur" berasal dari
simulasi/sintesis yang diulang di Mac 1 Oktober 2026 (`sim/EVIDENCE.md`,
`make`); yang lain adalah desain yang menunggu diukur. Tidak ada klaim yang naik
tanpa bukti baru (R2). Disusun atas arahan pemilik, 1 Oktober 2026. Top
operasional `hijaiyyah_portal8888` sudah disetujui; nama modul lain tetap
menunggu persetujuan pemilik (aturan penamaan `AGENTS.md` §2).

---

## 1. Tujuan

### Kontrak v1 yang terkunci

Top operasional v1 adalah `hijaiyyah_portal8888`, dengan satu domain clock PHY
dan satu stream byte. Cap waktu dibaca pada byte valid pertama (SOF), setelah
UTC diprovisi lewat `provision_time`, `provision_utc_sec`, dan
`provision_uncert_ns`; holdover 50 ppm tetap milik `hijaiyyah_timestamp`.
Kunci lima slot diprovisi sekali lalu dikunci sampai reset — `provision_locked`
kembali 0 saat `rst_n` turun (`rtl/hijaiyyah_portal8888.v:166`) — dan tidak
muncul sebagai port input operasional atau output. Frame sampai 9.216 byte disimpan lalu
di-replay ke SHA-256 agar stall hash tidak mengubah byte yang di-hash. Tidak
ada CDC pada v1. Jika frame melebihi batas atau datang saat buffer sedang
direplay/disegel, v1 menjatuhkannya dan memberi sinyal drop; ia tidak membuat
catatan parsial.

Body kanonik tepat 125 byte, MSB-first:

```text
DEV(8) PORT(1) T_sec(4) T_tick(4) T_source(1) T_uncert_ns(4) CTR(8)
status(1) ver(1) SRC_IP(16) SPORT(2) DPORT(2) PROTO(1) SRC_MAC(6)
FRAME_HASH(32) IDX(2) PREV(32)
```

`ref/portal_ref.py` adalah sumber tunggal layout dan vektor; RTL serta bench
membandingkan body dan HMAC terhadapnya.

Portal 8888 adalah **sistem bukti-tahan-rusak untuk asal dan integritas
sinyal**, dengan tiga guna yang sudah pemilik tetapkan:

1. **Find My / anti-maling:** perangkat kita (HP, laptop) melapor posisinya
   sendiri, disegel, sehingga bila dicuri jejaknya tidak bisa dihapus.
2. **Deteksi akses akun dari lokasi tak wajar:** login dari wilayah atau waktu
   yang mustahil ditandai, seperti peringatan Apple/Windows/Google.
3. **Bukti untuk pemilik:** paket bukti tersegel (IP + waktu tepat +
   port + hash) untuk pemeriksaan, validasi, dan penelusuran oleh pemilik pada tahap pengembangan.

Pola rujukannya adalah Apple "Find My", Windows "Find My Device", dan deteksi
login anomali — bukan penciptaan teknik baru, melainkan menyatukannya di atas
rantai tahan-rollback CosmicTera dengan disiplin bukti yang sama.

---

## 2. Prinsip yang mengikat (dari kontrak pemilik)

- **Yang dibuktikan vs yang tidak dipisah tegas.** Portal membuktikan APA yang
  tiba dan KAPAN, bukan SIAPA yang mengirim. Lokasi tepat datang dari GPS
  perangkat sendiri (bila ada) atau dari data eksternal bila tersedia dan dapat diakses secara sah — tidak pernah
  ditebak dari latensi.
- **NUI mendeteksi dan melaporkan; tidak menindak.** Mengunci atau menghapus
  perangkat jarak jauh, menelusur ke perangkat pihak lain, adalah tindakan
  mutatif: DENIED sampai diotorisasi (Lapis 7).
- **Otorisasi adalah otorisasi pemilik, bukan AI.** Kunci izin dipegang pemilik.
  NUI tidak bisa memberi izin pada dirinya sendiri (7.11).
- **Keamanan dipikul kripto standar.** HMAC-SHA256 dan Ed25519, bukan spons
  Ka'bah yang masih [EH] (R10).

---

## 3. Arsitektur berlapis L0–L5

```text
L0  TANGKAP          perangkat keras, sebelum software menyentuh
L1  SUSUN CATATAN    rakit field termasuk WAKTU TEPAT
L2  SEGEL            HMAC di FPGA; kunci diprovisi host (v1), disimpan di key_mem sampai reset
L3  RANTAI           4 sudut + portal + jangkar kepala (anti-rollback)
L4  OTORISASI        Ed25519, kunci pemilik — gerbang tindakan
L5  SERAH & TELUSUR  bukti ke pemilik → sumber eksternal yang tersedia → lokasi
```

### L0 — Tangkap (perangkat keras)

Sinyal masuk ditangkap oleh logika sebelum software host bisa mengubahnya.

| unsur | mekanisme | status |
|---|---|---|
| Baca header jaringan | `ingress_parse.v`: Ethernet/VLAN → IPv4/IPv6 → TCP/UDP | **terukur: 3.000/3.000 frame tepat** |
| Cap waktu tiba | dikunci di **byte pertama (SOF)**, di domain clock PHY | **terukur di simulasi** pada satu stream PHY |
| Basis waktu | `hijaiyyah_timestamp.v`: UTC diprovisi lalu counter di-disiplin **GPS-PPS** | **terukur di simulasi**: disiplin + holdover kontinu; `T_source` turun ke bebas dan `T_uncert_ns` tumbuh 50 ppm ketika PPS hilang |

**Kenapa SOF dan domain PHY:** cap waktu harus diambil tepat saat byte pertama
tiba, di clock PHY, supaya tidak terganggu antrean pipeline atau lintas domain
clock. Ini cacat yang diperbaiki dari versi awal yang hanya punya pengurut
(CTR), bukan waktu.

### L1 — Susun catatan

Satu catatan yang akan disegel:

```text
DEV        identitas perangkat Portal          (8 byte)
PORT       port fisik ingress (sudut A/B/C/D)   (1 byte)
T_sec      detik UTC                            (4 byte)
T_tick     tick clock sejak detik itu           (4 byte)
T_sumber   0 bebas · 1 NTP · 2 GPS-PPS          (1 byte)   ← dicatat apa adanya
T_uncert   ketidakpastian waktu dalam ns        (4 byte)
CTR        pengurut dalam tick yang sama        (8 byte)
OBS        status | ver | IP sumber(16) | port sumber | port tujuan | proto | MAC
FRAME_HASH SHA-256 frame mentah (bukti isi)     (32 byte)
IDX        nomor blok (mesin Jim GF(5))         (periode 3.124)
PREV       TAG blok sebelumnya di sudut ini
```

**Field waktu wajib menyebut sumber dan ketidakpastiannya.** Bila `T_sumber`
bebas, laporan menyatakan cap waktu itu kasar — tidak disembunyikan.

### L2 — Segel (HMAC, kunci pemilik)

```text
TAG = HMAC-SHA256(K_segel, DEV ‖ PORT ‖ T_sec ‖ T_tick ‖ T_sumber ‖ T_uncert ‖ CTR
                           ‖ OBS ‖ FRAME_HASH ‖ IDX ‖ PREV)
```

Pada v1, `K_segel` tidak lahir di FPGA. Host membangkitkan kunci uji menggunakan `random.Random(8888)` (`ref/portal_ref.py:73`), sehingga nilainya bersifat publik, lalu mengirimkannya tanpa enkripsi melalui UART untuk ditulis ke `key_mem`. Karena host melakukan provisioning, host mengetahui nilai kunci tersebut. RTL tidak menyediakan port readback untuk mengeluarkan kembali isi `key_mem` ke host atau NUI. Isi `key_mem` hilang ketika daya mati atau FPGA dikonfigurasi ulang; penguncian provisioning hanya berlaku sampai reset. Setelah disegel, setiap field — termasuk waktu — tidak bisa
diubah tanpa ketahuan.

- Mesin HMAC-SHA256: **tervalidasi di papan Tang Nano 20K, 207/207**
  (run `20261001T000009Z`), PnR repo 5.181 LUT4.

### L3 — Rantai empat sudut + portal + jangkar

```text
sudut A ─ blok ─ blok ─ …   PREV mengikat tiap sudut jadi rantai
sudut B ─ blok ─ blok ─ …
sudut C ─ blok ─ blok ─ …
sudut D ─ blok ─ blok ─ …
              │
   ROOT(r) = HMAC(K_portal, IDX ‖ ROOT(r-1) ‖ TAG_A ‖ TAG_B ‖ TAG_C ‖ TAG_D)
              │
   JANGKAR KEPALA di register FPGA: (putaran, ROOT, CTR, TAG terakhir tiap sudut)
                                    — tidak bisa ditulis host
```

Empat sudut = empat port/sumber fisik. "8888" = empat sudut, masing-masing
k = 8 blok rate Ka'bah (1 KiB per blok).

- `jim_sync` (penanda 31 bit) dan `jim_index` (GF(5)): **terukur 0 salah di
  simulasi, sudah disintesis.**
- Jangkar kepala adalah kunci anti-rollback: tanpa jangkar, penghapusan catatan
  terbaru dan pengembalian ke salinan lama **tidak terdeteksi** (0/300);
  dengan jangkar, **300/300**.

### L4 — Otorisasi (Ed25519, kunci pemilik)

Tindakan sensitif (membuka/mengekspor bukti, mengunci perangkat) butuh
**Otorisasi 8888**: catatan ditandatangani kunci **privat** pemilik.

| | HMAC (penyegelan) | Ed25519 (otorisasi) |
|---|---|---|
| sifat | simetris | asimetris |
| penandatangan | FPGA dengan kunci yang diprovisi host (v1) | **pemilik (kunci privat)** |
| pemverifikasi | FPGA | **NUI (kunci publik saja)** |
| akibat | NUI tak bisa palsukan bukti | **NUI tak bisa palsukan izin** |

Gerbang NUI sebelum tindakan apa pun (gagal di mana pun → STOP / REPORT):

```text
1. rantai Portal utuh?                     (verify == kosong)
2. tanda tangan Ed25519 sah dari pemilik?
3. izin mencakup TEPAT tindakan ini?
4. belum kedaluwarsa, belum dipakai?       (jangkar)
5. tindakan ada di allowlist? (DENIED tetap DENIED)
```

### L5 — Serah bukti & pelacakan lokasi sumber

Lihat bagian 5.

---

## 4. Deteksi anomali (pola Find My)

NUI Lapis 8 (baca-saja) membandingkan catatan baru dengan pola normal. Tiap
ancaman ditangani detektor yang tepat — temuan dari simulasi:

| ancaman | detektor | tindakan | hasil uji (300×) |
|---|---|---|---|
| akun dibobol dari luar | **impossible travel** (butuh waktu tepat) | hard: kunci | 300/300 |
| HP dicuri, dibawa pergi | **lost-mode + geofence** (GPS perangkat) | hard: kunci | 300/300 |
| pelaku menyunting/menghapus jejak | **rantai + jangkar** | hard: kunci | 300/300 |
| pindah kota wajar | geofence / wilayah baru | **soft: minta konfirmasi** | — |
| aktivitas normal di rumah | — | — | 0/300 positif palsu |

- **Impossible travel** memakai dua catatan: bila jarak ÷ selisih waktu
  melebihi kecepatan pesawat (> 1.000 km/jam), itu mustahil → dibobol. Ini
  tidak mungkin tanpa cap waktu tepat — karena itu field waktu adalah inti.
- **Perjalanan wajar hanya soft alert**, karena pemilik memang bisa bepergian:
  "Apakah ini Anda?" — bukan blok.
- **Semua tindakan keras (kunci/hapus) butuh Otorisasi 8888** (L4).

---

## 5. Pelacakan lokasi sumber hacker

Ini bagian yang paling mudah disalahpahami, jadi ditulis paling tegas.

### 5.1 Yang Portal 8888 bisa buktikan secara matematis

```text
IP sumber + WAKTU UTC tepat (±µs) + port fisik + hash frame
→ tersegel, tahan-ubah, tahan-hapus, tahan-rollback
```

### 5.2 Rantai menuju lokasi tepat

```text
Portal 8888  ──(IP + waktu tepat, tersegel)──►  NUI deteksi anomali
     │
     ▼  Otorisasi 8888 (tanda tangan pemilik)
Pemilik menerima paket bukti
     │
     ▼  korelasi sumber eksternal yang tersedia
ISP / operator seluler memetakan: IP + waktu tepat → pelanggan → alamat layanan, bila data tersedia dan pemilik memiliki akses yang sah
     │
     ▼
LOKASI TEPAT + identitas pelanggan
```

**Kenapa waktu tepat adalah kuncinya:** ISP memutar-ganti IP terus-menerus.
IP yang sama milik orang berbeda pada jam berbeda. "IP X pada detik Y yang
terbukti tidak dipalsukan dan tidak diputar-balik" adalah justru yang
dibutuhkan ISP untuk menunjuk pelanggan yang benar. Di sinilah anti-rollback
menjadi kunci lokasi — bukan karena lokasi ada di dalam bit, melainkan karena
ia membuat IP+waktu cukup tepercaya untuk membuka data lokasi yang sah.

### 5.3 Pembagian peran yang tidak boleh dilanggar

| peran | siapa | apa |
|---|---|---|
| deteksi & bukti | Portal 8888 / NUI | IP+waktu+port tersegel; deteksi anomali; lapor |
| otorisasi | pemilik | tanda tangan Ed25519 untuk membuka/ekspor bukti |
| penelusuran | pemilik + sumber eksternal | peta IP→pelanggan→lokasi bila data eksternal tersedia; tindakan di luar sistem tidak menjadi bagian Portal |

**NUI tidak pernah menjangkau atau masuk ke perangkat pihak lain.** Penelusuran
eksternal dilakukan oleh pemilik melalui kanal yang sah dan sesuai kewenangan yang berlaku.
Portal menyediakan bukti yang dapat diperiksa dan diverifikasi pemilik.

### 5.4 Batas fisika (tidak bisa dilewati arsitektur apa pun)

- **Lokasi tepat tidak bisa dihitung dari latensi.** Terukur: 1 node → galat
  ~464 km; 10 landmark → ~162 km. Latensi hanya memberi wilayah kasar, dan
  hanya boleh masuk laporan berlabel perkiraan, di luar segel.
- **IP sumber bisa dipalsukan di asal**, terutama UDP. Portal menyegelnya apa
  adanya; yang dibuktikan adalah apa yang tiba, bukan siapa pengirim.
- **MAC hanya lompatan terakhir** (router/switch lokal), bukan perangkat asal.
- **VPN/Tor/proxy/NAT** menyembunyikan asal; yang terlihat hanya simpul keluar.
- **GeoIP** (IP → kota) perkiraan dari basis data luar, bukan bukti.
- **Lokasi tepat** hanya ada di: (a) GPS perangkat kita sendiri yang melapor;
  atau (b) data pelanggan ISP / triangulasi menara, bila tersedia melalui kanal yang sah.

### 5.5 Penguat bukti yang bisa dibangun

- Catat apakah koneksi TCP **sudah menyelesaikan handshake**: IP pada koneksi
  TCP yang tersambung jauh lebih sulit dipalsukan daripada paket UDP tunggal.
- Cap waktu presisi tinggi (±µs) agar korelasi ISP setepat mungkin.

---

## 6. Kripto dan kunci

| lapis | primitif | kunci | tinggal di |
|---|---|---|---|
| Penyegelan bukti | HMAC-SHA256 | K_segel | diprovisi host lewat UART (v1); tidak ada readback dari FPGA; kunci uji publik |
| Otorisasi tindakan | Ed25519 | privat pemilik / publik di NUI | privat di luar jangkauan NUI |
| Identitas perangkat | per-perangkat | kunci perangkat | dalam perangkat |

**Ed25519 belum ada di repo** (seluruh kripto tanda tangan saat ini HMAC).
Menambahkannya untuk lapis otorisasi adalah prasyarat, dan menjadi keputusan
spesifikasi tersendiri.

---

## 7. Status evidence

```text
ingress_parse (baca jaringan)        VALIDATED simulasi (3.000/3.000)
jim_sync / jim_index                 VALIDATED simulasi (0 salah), disintesis
HMAC-SHA256                          VALIDATED papan (207/207)
model rantai + jangkar               VALIDATED simulasi (kampanye 300×/kelas)
cap waktu GPS-PPS                    VALIDATED simulasi: UTC provision, disiplin,
                                     holdover kontinu, sumber dan ketidakpastian
cap waktu tiba di SOF                VALIDATED simulasi pada satu stream PHY
FSM Portal L1 v1                     VALIDATED simulasi: body 125 byte, HMAC
                                     byte-exact, provisioning write-once + lock
jumbo frame 9.216 B                  VALIDATED simulasi: dua frame kontinu
pembungkus UART Tang Nano 20K        VALIDATED simulasi lewat pin UART: rantai
                                     PREV, ROOT, jangkar (`sim/EVIDENCE.md` §9)
PnR Tang Nano 20K                    SELESAI: 15.848 LUT4, 8.080 DFF, 6 BSRAM;
                                     bitstream dimuat, satu lari di papan 0 salah
Ed25519 otorisasi                    DESAIN — belum ada di repo
validasi fisik                       Tang Nano 20K, satu lari lewat UART
                                     (`sim/EVIDENCE.md` §9); PHY dan PPS belum
```

---

## 8. Kepatuhan & privasi — belum final

- Status hukum dan penerimaan sebagai alat bukti belum menjadi klaim Portal pada tahap ini. Persyaratan
  chain of custody dan prosedur pembuktian akan ditentukan pada tahap pemilik setelah desain tervalidasi.
- IP dan lokasi diperlakukan sebagai data pribadi/sensitif; retensi dan akses log memerlukan kebijakan
  pemilik yang jelas dan peninjauan kepatuhan yang sesuai.
- **Pemegang kunci privat Ed25519:** pada tahap ini adalah pemilik; tata kelola, rotasi, dan
  pemulihan kunci masih merupakan bagian spesifikasi yang belum final.

---

## 9. Langkah implementasi (disiplin yang sama: kontrak → RTL → sim → papan)

```text
1. Pemilik mengunci kontrak ini (format catatan, field waktu, batas otorisasi)
2. RTL cap-waktu GPS-PPS            → sim presisi
3. FSM Portal 4 sudut + jangkar     → kampanye serangan diulang di sim RTL
4. Lapis 8 baca-saja (deteksi)      → kontrak + GREEN
5. Ed25519 otorisasi                → spec terpisah
6. Kontrak platform                  → wrapper, synthesis, PnR, uji papan
```

Tidak ada implementasi sebelum kontrak dikunci. Tindakan mutatif
(kunci/hapus/telusur) tetap DENIED sampai dibuka satu per satu lewat proposal,
pola `SEND_PROGRAM`.

---

## 10. Nama modul

```text
ingress_parse.v        → rtl/hijaiyyah_ingress.v        ?
jim_sync.v             → rtl/hijaiyyah_jim_sync.v        ?
jim_index.v            → rtl/hijaiyyah_jim_index.v       ?
(cap waktu)            → rtl/hijaiyyah_timestamp.v       ?
(FSM Portal)           → hijaiyyah_portal8888            disetujui (top v1)
(pembungkus papan)     → hijaiyyah_portal8888_gowin_top  disetujui, 3 Oktober 2026
kontrak                → NUI/PORTAL8888.md               ?
```

Nama dan slot tidak dikarang; pemilik yang menetapkan (`AGENTS.md` §2).
