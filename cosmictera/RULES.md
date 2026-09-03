# Aturan CosmicTera

Aturan di bawah ini **mengikat**. Bukan gaya, bukan preferensi — masing‑masing
lahir dari kesalahan yang benar‑benar terjadi di repositori ini, dan masing‑masing
punya tes yang menegakkannya. Bekas lukanya dicatat karena aturan tanpa insiden
akan dilanggar lagi.

---

## R1 — Satu kebenaran, satu tempat

Setiap fakta hanya boleh punya **satu** definisi. Kalau ia harus muncul di
tempat kedua, tempat kedua itu wajib **diturunkan** dari yang pertama, dan
paritasnya wajib diuji.

> **Bekas luka.** Ini akar penyebab yang paling sering berulang di proyek ini:
> Master Table, encoding H‑ISA, konstanta `U`, sistem guard, `DATA_DEPTH`,
> salinan lapisan linear di alat serang, dan duplikat R5 di
> `language/evaluator.py`. Setiap kali, salinan kedua menyimpang diam‑diam.

**Penegakan.** Tes paritas untuk tiap pasangan, ditambah sabotase yang mengubah
salah satu salinan dan memastikan tesnya gagal.

---

## R2 — Label epistemik mengikat

Setiap klaim membawa label, dan **tidak ada klaim yang naik tanpa bukti baru**.

| Label | Arti |
|---|---|
| **VF** | Verified Formally — terbukti, bukan diuji sampel |
| **CC** | Computationally Confirmed — dijalankan atas ruang yang habis atau sampel besar |
| **DP** | Design Property — benar karena konstruksinya, bukan temuan |
| **EH** | Engineering Hypothesis — terukur, belum dikriptanalisis |
| **AT** | Aspirational Target — belum dikerjakan |

> **Bekas luka.** Spons berlabel [EH] dan tetap [EH]. Aviasi statistik yang bagus
> — avalanche 0,5007, 20.000 keadaan tanpa tabrakan — **bukan** bukti, dan
> pernah menutupi permutasi yang bahkan bukan permutasi (rank 1276/1600).

---

## R3 — Setiap gerbang diuji dengan merusak apa yang dijaganya

Tes yang hanya menjalankan jalur normal tidak menguji gerbang. Gerbang diuji
dengan **sengaja merusak** apa yang ia jaga dan memastikan ia menyala.

> **Bekas luka — dan ini yang paling sering menipu saya.** Enam kali tes
> sabotase saya sendiri **lulus sementara kodenya salah**:
>
> - `standby` butuh dua posisi tahan (di dalam *dan* di luar substitusi)
> - zero‑extend butuh immediate dengan bit 11 menyala *dan* operand dengan bit
>   di atas 11 menyala
> - `ram_we` MMIO: saya menulis ke alamat periferal lalu membaca alamat RAM
>   yang *berbeda* — harus mengamati `ram_we` langsung
> - kedaluwarsa timer: saya menyetel compare *setelah* membersihkan, jadi
>   memeriksa nol yang memang sudah nol
> - tes gerbang jamrah menemukan "JEQ" di dalam komentar yang menyatakan JEQ
>   tidak dipakai
> - sabotase rho: pola `sed` tidak cocok apa pun, jadi build "tersabotase"
>   adalah build aslinya
>
> Pola yang sama terulang **di sesi ini juga**: sabotase ketiga menjalankan
> **nol tes** karena filter `-k` tidak cocok apa pun.

**Penegakan.** Sabotase wajib melaporkan bahwa ia benar‑benar mengubah sesuatu
**dan** bahwa tesnya benar‑benar berjalan (`1 failed`, bukan `no tests ran`).

Dan asersi pada angka harus **memparse tempatnya, bukan mencari di berkas**.
Angka yang muncul dua kali — di tabel dan di prosa sebelahnya — membuat
pencarian substring lolos sementara tabelnya berbohong. Lubang ini muncul
**lima kali** di sesi yang sama: pada biaya, pada geometri, pada hitungan
opcode, pada periode Jim, dan pada identitas 622 = 2×310 di jejak Ka'bah. Setiap kali sabotase yang menemukannya, bukan
pembacaan ulang.

Dan penjaganya harus **hash berkas, bukan hitungan kemunculan**. Hitungan
kemunculan buta terhadap **sisipan**: sabotase yang menambahkan baris di depan
pola meninggalkan hitungannya tetap 1, dan penjaga melaporkan "tidak berubah"
padahal berkasnya berubah. Itu terjadi persis begitu saat menguji trap, dan
sabotase yang sah nyaris dibuang sebagai gagal.

---

## R4 — Angka yang tidak diukur ulang adalah klaim tentang desain yang sudah tidak ada

Setiap angka hasil pengukuran — sintesis, throughput, jumlah clock — **kedaluwarsa
saat modulnya berubah**. Mengutipnya setelah itu bukan ketidaktelitian; itu
pernyataan tentang desain yang tidak ada lagi.

> **Bekas luka.** Header `rtl/hijaiyyah_kabah_top.v` mencatat 7.426 LUT4 (85%)
> di commit `cd6a29c`. Commit **berikutnya** (`4e0555e`) menjadikan gerbang
> benar‑benar menggerbang — `gate_mode`, `break_at`, `break_count`,
> backpressure `bits_ready` — dan angkanya tidak pernah dijalankan ulang.
> Sintesis ulang: **8.096 LUT4 (94%)**. Gerbang itu memakan +670 LUT4 dan
> margin papan turun dari 15% ke **6%**.

---

## R5 — Laju komponen bukan laju sistem

Laju satu tahap **tidak boleh** dikutip sebagai laju sistem sampai terbukti
tahap itulah bottleneck‑nya.

> **Bekas luka.** 11,15 MB/s adalah laju spons disuap satu byte per clock. Ia
> dikutip sebagai throughput sistem di `kabah.py`, di dua header RTL, dan di
> empat halaman terbit — **terlalu tinggi 4×**. Sistem disuap aliran bit;
> deserialiser membayar 8 clock per byte, 3,3× biaya spons. Spons bukan
> bottleneck; front end‑nya. Laju sebenarnya **2,59 MB/s**.

**Penegakan.** `Kabah.throughput()` mengembalikan kunci `bottleneck`. Pakai itu.

---

## R6 — Lipatan menghasilkan orbit; rotasi menjadikannya nilai

Keluaran lipatan **bukan** sebuah nilai sampai wakil kanonik orbit rotasinya
dipilih. Orbit tidak bisa disegel.

Tiga geseran fase memberi tiga laporan yang semuanya "benar" dan semuanya
berbeda. Yang menjadikannya satu jawaban adalah pemilihan wakil, bukan
perhitungannya.

> **Bekas luka.** Saya menyajikan siklus, clock, dan node sebagai **tiga
> prinsip sejajar**, dan itu salah. Strukturnya satu mekanisme dan satu
> rangkuman: lipatan dirangkum oleh rotasi, dan pemecahan node adalah *bagaimana*
> lipatan dilakukan. Pemilik proyek yang mengoreksinya.
>
> Dan sekali lagi di deserialiser: bit pertama ditaruh di `shifter[0]`, sehingga
> **hanya byte pertama setiap aliran** yang salah. `tb_hijaiyyah_wave` lulus
> 78/78 dengan cacat itu masih di dalamnya. Hanya perakitan lajur terhadap
> `cube.py` yang menyingkapnya.

---

## R7 — Impulser dihitung per data, bukan per detik

Impulser **tidak berjalan bebas**. Ia berhenti pada `stall` dan maju hanya
ketika spons butuh permutasi. Karena itu satuannya **denyut per data**, dan
biayanya konstan hanya dalam satuan itu.

Terukur: **56 denyut per permutasi** (28 linear + 28 substitusi), **1 permutasi
per 128 byte**. Per terabit: 976.562.500 permutasi, 54,7 giga denyut.

> **Bekas luka.** Saya menyatakan "pada skala tera rasionya menjadi keputusan
> desain". Pengukuran membantahnya: ambang 58,7% itu **invarian terhadap
> skala** — ia rasio, dan rasio tidak berubah karena volumenya membesar. Alasan
> tera yang benar sama sekali lain: pada 107 jam per terabyte, **"jalankan
> lagi" bukan lagi verifikasi**, jadi determinisme harus struktural.
>
> Sebelum itu saya juga mengira impulser berjalan bebas terhadap waktu. Ia
> tidak: ia berhenti pada `stall`. Tidak ada jumlah detik yang memajukannya
> tanpa data.

---

## R8 — Statistik sempurna pada konstruksi rusak tetap terlihat sempurna

Uji distribusi **tidak** bisa melihat cacat struktural. Struktur diuji dengan
alat struktur.

> **Bekas luka.** Avalanche 0,5007 dan 20.000 keadaan bebas tabrakan tidak
> melihat bahwa permutasinya bukan permutasi. Hanya perhitungan rank atas
> `GF(2)` yang melihatnya: **1276 dari 1600**.

---

## R9 — Segel menutup semua penentu, atau ia tidak menutup apa pun

Segel yang menutup data tetapi tidak menutup kode yang memprosesnya bukan
segel. Siapa pun bisa mengubah satu berkas RTL dan setiap program tersegel
tetap lolos sementara papan melakukan hal lain.

Karena itu manifes CosmicTera menutup **12 pola sumber sistem** — RTL, wrapper
FPGA, testbench, vektor, header, berkas papan, skrip alat — dan mengecualikan
**5 produk build** yang bisa diturunkan ulang.

> **Bekas luka.** Ringkasan manifes pernah menulis "90 program, 479.626
> instruksi" karena program (instruksi) dan sumber (byte) dihitung menyatu.
> Dan `image_of` pernah memakai `compile_hc`, yang menulis berkas lalu
> mengembalikan status — sehingga 10 entri `.hc` membawa SHA‑256 dari **string
> kosong**.

---

## R10 — Lapis 3 satu‑satunya pemikul keamanan

| Lapis | Nama | Label | Berkunci | Menanggung keamanan |
|---|---|---|---|---|
| 0 | Canonical | DP | tidak | tidak |
| 1 | Guard | CC | tidak | tidak |
| 2 | Absorption | EH | tidak | **tidak** |
| 3 | Authentic | VF | ya | **ya — seluruhnya** |
| 4 | Confidential | — | ya | ditolak |

Lapis 0–2 adalah kanonikalisasi dan triase tanpa kunci. Mereka menolak dan
mengklasifikasi dengan murah supaya jalur mahal tidak terbuang — dan mereka
**tidak membuktikan apa pun tentang asal‑usul**.

> **Bekas luka.** Triase pernah dibela dengan penghematan waktu: "rasio 2,4×,
> itulah seluruh alasan menaruhnya di depan." Setelah bottleneck sebenarnya
> ketemu, penghematannya cuma **1,30×**. **Triase berhak ada karena apa yang ia
> temukan, bukan karena apa yang ia hemat** — dan itu memang selalu argumen
> yang benar.

---

## R11 — Primitif harus mereproduksi vektor terbitannya

Pemeriksaan tambahan tidak boleh diletakkan di dalam primitif sampai ia lolos
vektor uji standar.

> **Bekas luka.** `reject_degenerate_key` diletakkan di dalam `derive_key` dan
> mematahkan 3 tes RFC 5869 — kasus 1 memakai `0x0b × 22`, yang ditolaknya.
> Pemeriksaan itu milik batas sistem, bukan primitif.

---

## R12 — Konstanta dikutip dari hukumnya, bukan dari ingatan

> **Bekas luka.** GHASH pernah diverifikasi terhadap konstanta SP 800‑38D yang
> diingat — satu byte salah, dan gerbangnya menyala pada penulisnya sendiri.
> Diganti dengan hukum pendefinisi lapangannya: `x¹²⁸ = x⁷ + x² + x + 1`.

---

## R13 — Commit hanya setelah keluaran tes benar‑benar diperiksa

> **Bekas luka.** Dua kali commit dengan tes gagal, karena `pytest | tail`
> mengembalikan status keluar `tail`, bukan `pytest`. Sekarang keluaran
> dialihkan ke berkas dan status keluarnya diperiksa langsung.
>
> Dan satu lagi: survei melaporkan "10 dikompilasi, 0 gagal" karena saya
> mencetak "ok" setiap kali tidak ada eksepsi, tanpa memeriksa
> `result.success`. Angka sebenarnya: **0 dari 10**.
