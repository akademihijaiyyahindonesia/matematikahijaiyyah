# Portal 8888 — Arsitektur Lengkap

**Label: [EH] / DESAIN.** Dokumen ini hipotesis rekayasa dan draf kontrak,
bukan sistem yang sudah dibangun. Angka yang ditandai "terukur" berasal dari
simulasi/sintesis sandbox (oss-cad-suite 2026-09-30); yang lain adalah desain
yang menunggu diukur. Tidak ada klaim yang naik tanpa bukti baru (R2).
Disusun atas arahan pemilik, 1 Oktober 2026. Nama modul masih sementara,
menunggu persetujuan pemilik (aturan penamaan `AGENTS.md` §2).

---

## 1. Tujuan

Portal 8888 adalah **sistem bukti-tahan-rusak untuk asal dan integritas
sinyal**, dengan tiga guna yang sudah pemilik tetapkan:

1. **Find My / anti-maling:** perangkat kita (HP, laptop) melapor posisinya
   sendiri, disegel, sehingga bila dicuri jejaknya tidak bisa dihapus.
2. **Deteksi akses akun dari lokasi tak wajar:** login dari wilayah atau waktu
   yang mustahil ditandai, seperti peringatan Apple/Windows/Google.
3. **Bukti untuk penegak hukum:** paket bukti tersegel (IP + waktu tepat +
   port + hash) yang bisa diserahkan secara sah untuk menelusur pelaku.

Pola rujukannya adalah Apple "Find My", Windows "Find My Device", dan deteksi
login anomali — bukan penciptaan teknik baru, melainkan menyatukannya di atas
rantai tahan-rollback CosmicTera dengan disiplin bukti yang sama.

---

## 2. Prinsip yang mengikat (dari kontrak pemilik)

- **Yang dibuktikan vs yang tidak dipisah tegas.** Portal membuktikan APA yang
  tiba dan KAPAN, bukan SIAPA yang mengirim. Lokasi tepat datang dari GPS
  perangkat sendiri (bila ada) atau dari data ISP lewat hukum — tidak pernah
  ditebak dari latensi.
- **NUI mendeteksi dan melaporkan; tidak menindak.** Mengunci atau menghapus
  perangkat jarak jauh, menelusur ke perangkat pihak lain, adalah tindakan
  mutatif: DENIED sampai diotorisasi (Lapis 7).
- **Otorisasi adalah otorisasi hukum, bukan AI.** Kunci izin dipegang penegak
  hukum. NUI tidak bisa memberi izin pada dirinya sendiri (7.11).
- **Keamanan dipikul kripto standar.** HMAC-SHA256 dan Ed25519, bukan spons
  Ka'bah yang masih [EH] (R10).

---

## 3. Arsitektur berlapis L0–L5

```text
L0  TANGKAP          perangkat keras, sebelum software menyentuh
L1  SUSUN CATATAN    rakit field termasuk WAKTU TEPAT
L2  SEGEL            HMAC, kunci pemilik, di dalam FPGA
L3  RANTAI           4 sudut + portal + jangkar kepala (anti-rollback)
L4  OTORISASI        Ed25519, kunci penegak hukum — gerbang tindakan
L5  SERAH & TELUSUR  bukti ke penegak hukum → ISP → lokasi
```

### L0 — Tangkap (perangkat keras)

Sinyal masuk ditangkap oleh logika sebelum software host bisa mengubahnya.

| unsur | mekanisme | status |
|---|---|---|
| Baca header jaringan | `ingress_parse.v`: Ethernet/VLAN → IPv4/IPv6 → TCP/UDP | **terukur: 3.000/3.000 frame tepat** |
| Cap waktu tiba | dikunci di **byte pertama (SOF)**, di domain clock PHY | desain |
| Basis waktu | counter di-disiplin **GPS-PPS**, tertaut UTC | desain |

**Kenapa SOF dan domain PHY:** cap waktu harus diambil tepat saat byte pertama
tiba, di clock PHY, supaya tidak terganggu antrean pipeline atau lintas domain
clock. Ini cacat yang diperbaiki dari versi awal yang hanya punya pengurut
(CTR), bukan waktu.

### L1 — Susun catatan

Satu catatan yang akan disegel:

```text
DEV        identitas perangkat Portal          (8 byte)
PORT       port fisik ingress (sudut A/B/C/D)   (1 byte)
T_tiba     waktu UTC, detik + pecahan           (8 byte)
T_sumber   0 bebas · 1 NTP · 2 GPS-PPS          (1 byte)   ← dicatat apa adanya
T_uncert   ketidakpastian waktu dalam ns        (4 byte)
CTR        pengurut dalam tick yang sama        (8 byte)
OBS        status | ver | IP sumber(16) | port sumber | port tujuan | proto | MAC
FRAME_HASH SHA-256 frame mentah (bukti isi)     (32 byte)
LOC        koordinat GPS perangkat, bila ada    (opsional, ditandatangani perangkat)
IDX        nomor blok (mesin Jim GF(5))         (periode 3.124)
PREV       TAG blok sebelumnya di sudut ini
```

**Field waktu wajib menyebut sumber dan ketidakpastiannya.** Bila `T_sumber`
bebas, laporan menyatakan cap waktu itu kasar — tidak disembunyikan.

### L2 — Segel (HMAC, kunci pemilik)

```text
TAG = HMAC-SHA256(K_segel, DEV ‖ PORT ‖ T_tiba ‖ T_sumber ‖ T_uncert ‖ CTR
                           ‖ OBS ‖ FRAME_HASH ‖ LOC ‖ IDX ‖ PREV)
```

`K_segel` lahir dan tinggal **di dalam FPGA**, tidak pernah ke software host
atau ke NUI. Setelah disegel, setiap field — termasuk waktu — tidak bisa
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

### L4 — Otorisasi (Ed25519, kunci penegak hukum)

Tindakan sensitif (membuka/mengekspor bukti, mengunci perangkat) butuh
**Otorisasi 8888**: catatan ditandatangani kunci **privat** penegak hukum.

| | HMAC (penyegelan) | Ed25519 (otorisasi) |
|---|---|---|
| sifat | simetris | asimetris |
| penandatangan | pemilik (dalam FPGA) | **penegak hukum (kunci privat)** |
| pemverifikasi | FPGA | **NUI (kunci publik saja)** |
| akibat | NUI tak bisa palsukan bukti | **NUI tak bisa palsukan izin** |

Gerbang NUI sebelum tindakan apa pun (gagal di mana pun → STOP / REPORT):

```text
1. rantai Portal utuh?                     (verify == kosong)
2. tanda tangan Ed25519 sah dari penegak hukum?
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
     ▼  Otorisasi 8888 (tanda tangan penegak hukum)
Penegak hukum menerima paket bukti
     │
     ▼  surat perintah
ISP / operator seluler memetakan: IP + waktu tepat → pelanggan → alamat layanan
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
| otorisasi | penegak hukum | tanda tangan Ed25519 untuk membuka/ekspor bukti |
| penelusuran & penangkapan | penegak hukum + ISP | peta IP→pelanggan→lokasi; menangkap pelaku |

**NUI tidak pernah menjangkau atau masuk ke perangkat pelaku.** Itu ranah
forensik penegak hukum dengan surat perintah mereka. Penegak hukum yang
menelusur; Portal menyediakan bukti yang membuat penelusuran itu sah dan tepat.

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
  atau (b) data pelanggan ISP / triangulasi menara, dibuka lewat hukum.

### 5.5 Penguat bukti yang bisa dibangun

- Catat apakah koneksi TCP **sudah menyelesaikan handshake**: IP pada koneksi
  TCP yang tersambung jauh lebih sulit dipalsukan daripada paket UDP tunggal.
- Cap waktu presisi tinggi (±µs) agar korelasi ISP setepat mungkin.

---

## 6. Kripto dan kunci

| lapis | primitif | kunci | tinggal di |
|---|---|---|---|
| Penyegelan bukti | HMAC-SHA256 | K_segel | dalam FPGA, tak pernah keluar |
| Otorisasi tindakan | Ed25519 | privat penegak hukum / publik di NUI | privat di luar jangkauan NUI |
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
cap waktu GPS-PPS                     DESAIN — belum dibangun/diukur
FSM Portal terpadu 4 sudut           DESAIN — belum dibangun
Ed25519 otorisasi                    DESAIN — belum ada di repo
integrasi papan penuh                BELUM
```

Platform: Tang Nano 20K **tidak punya port Ethernet**. Ingress jaringan butuh
PHY Ethernet — KV260 (sudah di roadmap) atau modul PHY tambahan.

---

## 8. Dasar hukum (ditinjau pengacara, bukan insinyur)

- **Alat bukti elektronik** (UU ITE, KUHAP): syarat agar log Portal diterima
  sebagai bukti, dan rantai pengawasannya (*chain of custody*).
- **UU PDP 27/2022:** alamat IP dan lokasi adalah data pribadi; retensi dan
  akses log perlu dasar hukum dan kebijakan tertulis.
- **Pemegang kunci privat Ed25519:** siapa yang sah, dan bagaimana dikelola.

---

## 9. Langkah implementasi (disiplin yang sama: kontrak → RTL → sim → papan)

```text
1. Pemilik mengunci kontrak ini (format catatan, field waktu, batas otorisasi)
2. RTL cap-waktu GPS-PPS            → sim presisi
3. FSM Portal 4 sudut + jangkar     → kampanye serangan diulang di sim RTL
4. Lapis 8 baca-saja (deteksi)      → kontrak + GREEN
5. Ed25519 otorisasi                → spec terpisah
6. Integrasi papan (PHY Ethernet)   → uji papan, evidence
```

Tidak ada implementasi sebelum kontrak dikunci. Tindakan mutatif
(kunci/hapus/telusur) tetap DENIED sampai dibuka satu per satu lewat proposal,
pola `SEND_PROGRAM`.

---

## 10. Nama modul (menunggu persetujuan pemilik)

```text
ingress_parse.v        → rtl/hijaiyyah_ingress.v        ?
jim_sync.v             → rtl/hijaiyyah_jim_sync.v        ?
jim_index.v            → rtl/hijaiyyah_jim_index.v       ?
(cap waktu)            → rtl/hijaiyyah_timestamp.v       ?
(FSM Portal)           → rtl/hijaiyyah_portal8888.v      ?
kontrak                → NUI/PORTAL8888.md               ?
```

Nama dan slot tidak dikarang; pemilik yang menetapkan (`AGENTS.md` §2).
