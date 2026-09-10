# Kegunaan di industri nyata

Matematika Hijaiyyah menghasilkan empat kemampuan yang **tidak dimiliki
tumpukan komputasi arus utama**, dan tiap satunya menjawab masalah yang
industri tertentu bayar mahal untuk menyelesaikannya.

Halaman ini menjelaskan kegunaan itu — apa yang bisa dikerjakannya, di
sektor mana, dan kenapa. Angka di tiap bagian terukur dan punya tes yang
menjaganya.

---

## 1. Integritas yang tidak bisa lupa diperiksa

**Kemampuannya.** Guard G1–G4 dan T1–T2 dievaluasi dalam **25 operasi**,
tidak bergantung panjang data. Di silikon ia **satu instruksi** (`HGRD`),
satu siklus — bukan rutin yang dipanggil. Dan `JGD`/`JNGD` menjadikan
integritas sebagai **aliran kendali**: program bercabang atas kondisi "data
ini masih sah" tanpa satu pun pembandingan eksplisit yang bisa lupa ditulis
programmer.

**Kenapa itu berharga.** Di sistem konvensional, verifikasi integritas
adalah langkah terpisah yang bisa dilewati, lupa dipanggil, atau dimatikan
"demi kinerja". Di sini ia melekat pada tipe datanya. Ψ-injector di
kompilator memancangkannya ke kode terkompilasi — bukan pustaka yang bisa
tidak dipakai.

**Industri yang membayar untuk ini:** rekam medis, transaksi keuangan,
rantai pasok berdokumen, arsip hukum — mana pun yang harus bisa membuktikan
data tidak berubah, bukan sekadar berjanji.

Terukur: `hcpu_guard.v`, dijaga `test_guard_coverage.py`,
`test_guard_sweep.py`. Label **CC**.

---

## 2. Muat di perangkat yang paling kecil

**Kemampuannya.** Seluruh tabel kanonik — 28 huruf × 18 dimensi, 504 nilai —
muat dalam **252 byte** setelah nibble-packing. Aritmetika bilangan bulat
penuh, tanpa satu pun operasi floating-point di inti data. Di FPGA,
`hcpu_rom` bahkan tersintesis jadi logika kombinasional alih-alih memori.

**Kenapa itu berharga.** Mikrokontroler kelas bawah tidak punya FPU dan
menghitung memorinya dalam kilobyte. Pustaka kripto dan validasi biasa tidak
muat di sana, atau muat dengan mengorbankan segalanya yang lain. Ini muat
dengan sisa ruang, dan tetap membawa pemeriksaan integritas O(1) yang sama.

**Industri yang membayar untuk ini:** sensor IoT, kartu pintar, tag
industri, perangkat medis tersemat, kendali otomotif — tempat setiap
kilobyte dan setiap miliwatt diperebutkan.

Terukur: `src/hijaiyyah/core/rom.py`, 252 byte. Label **CC**.

---

## 3. Hasil yang sama, di mesin mana pun, bisa dibuktikan

**Kemampuannya.** Dataset-seal yang sama plus protokol yang sama
menghasilkan keluaran yang identik di perangkat keras apa pun. Ini bukan
klaim desain — ia terbukti di titik tersulitnya: keluaran papan FPGA cocok
dengan simulator perangkat lunak **byte-per-byte**, 23 dari 23, dan 28 nilai
Θ̂ dari silikon identik dengan tabel kanonik.

**Kenapa itu berharga.** Sistem berbasis floating-point memberi hasil yang
sedikit berbeda antar prosesor, antar kompilator, kadang antar jalankan.
Untuk sektor teregulasi, "sedikit berbeda" berarti audit tidak bisa
mereproduksi, dan sertifikasi jadi mahal atau mustahil.

**Industri yang membayar untuk ini:** avionik, alat medis bersertifikat,
sistem pemilu, forensik digital, kepatuhan finansial — tempat reproduksi
persis adalah syarat hukum, bukan kemewahan teknis.

Terukur: `test_substrate_independence.py`, `test_execution_parity.py`,
`test_isa_parity.py`. Label **CC**.

---

## 4. Huruf Arab sebagai tipe primitif, bukan string

**Kemampuannya.** Dua puluh delapan huruf Hijaiyyah adalah tipe dasar di
bahasa HC — bukan `string` yang dicari di tabel. Penjumlahan huruf adalah
operasi bahasa dengan aljabar monoid terbatas; anagram punya invarian;
jarak dan norma antar huruf terdefinisi dan dihitung integer.

**Kenapa itu berharga.** Untuk beban kerja yang memang berbasis huruf Arab,
ini memindahkan pekerjaan dari pustaka ke bahasa dan dari perangkat lunak ke
silikon. `HLOAD`, `HCADD`, `HDIST`, `HNRM2` mengerjakannya sebagai instruksi
mesin.

**Industri yang membayar untuk ini:** pemrosesan korpus Al-Qur'an dan
manuskrip, pencarian dan indeks teks Arab, teknologi pendidikan bahasa Arab,
kaligrafi digital, penerbitan.

Terukur: sembilan instruksi asli-huruf di `rtl/hcpu_pkg.vh`, dijaga
`test_letter_instructions.py`, `test_table_as_program.py`. Label **CC**.

---

## 5. Kripto yang keluarannya bisa dibuktikan, bukan dipercaya

**Kemampuannya.** Ka'bah berjalan di silikon sejak 10 September 2026.
Dua bingkai 128 byte dikirim berturut **tanpa reset di antaranya**, dan 400
byte balasan papan cocok **seluruhnya** dengan referensi perangkat lunak
`cube.py` — bukan satu blok yang kebetulan benar, melainkan penyerapan
berantai lintas blok. **165,98 MHz, nol BSRAM**: seluruh keadaan spons ada
di flip-flop dan logika.

**Kenapa itu berharga.** Perangkat keras kripto biasanya diuji terhadap
vektor uji tetap. Di sini padanan perangkat lunaknya berjalan penuh, jadi
implementasi silikon bisa dibandingkan **byte-per-byte terhadap keadaan
internalnya sendiri**, bukan hanya terhadap keluaran akhir. Jalurnya
bilangan bulat penuh dan alur sintesisnya sumber terbuka seluruhnya —
tidak ada blok tertutup yang harus dipercaya begitu saja.

**Industri yang peduli:** modul keamanan perangkat keras, elemen aman,
kedaulatan kripto nasional — tempat "kami tidak bisa memeriksa isi cip itu"
adalah masalah, bukan detail.

**Dan batasnya, yang harus dibaca bersama yang di atas:** ini klaim tentang
**kebenaran implementasi**, bukan tentang keamanan. Spons berlabel **EH** dan
tetap **EH** — terukur, belum dikriptanalisis. Avalanche 0,5007 dan 20.000
keadaan tanpa tabrakan **bukan bukti**. Tidak ada analisis diferensial atau
linear independen yang pernah dijalankan terhadap konstruksi ini, dan sampai
ada, ia tidak boleh dipakai melindungi apa pun yang nyata. Untuk kerahasiaan,
proyek ini sendiri menolak Ka'bah dan menunjuk AES-256-GCM
([CONCRETE.md](../cosmictera/CONCRETE.md)).

Terukur: `rtl/scripts/kabah_uart_test.py`, dijaga `test_kabah_folder.py`,
`test_crypto.py`. Label **CC** untuk kesetaraan; **EH** untuk keamanan.

---

## 6. Inti prosesor yang bisa dilisensikan

**Kemampuannya.** HCPU muat di **67%** Tang Nano 20K dan berjalan pada
**118,43 MHz**; Ka'bah **58%** pada **165,98 MHz**. Keduanya lewat alur
sintesis sumber terbuka penuh — yosys, nextpnr, gowin_pack — tanpa satu pun
IP vendor berbayar.

**Kenapa itu berharga.** Inti prosesor komersial datang dengan biaya lisensi
per-chip dan rantai perkakas tertutup. Ini tidak.

**Industri yang membayar untuk ini:** perancang ASIC/FPGA, riset akademik,
kedaulatan teknologi nasional — tempat "tidak bergantung lisensi asing"
adalah syarat, bukan preferensi.

Terukur: `test_place_and_route.py`, `kabah/SILICON.md`. Label **CC** untuk
FPGA; jalur ASIC di `rtl/mpw/` masih **AT**.

---

## 7. Pendidikan yang utuh dari matematika sampai silikon

**Kemampuannya.** Seorang siswa bisa menulis `.hc`, melihatnya dikompilasi
ke bytecode, dijalankan di mesin virtual, lalu **dijalankan di papan FPGA di
mejanya sendiri** — dan membandingkan keluaran keduanya byte-per-byte.
Rantai itu utuh dan seluruhnya ada di repositori ini.

**Kenapa itu berharga.** Hampir tidak ada bahan ajar yang menyambungkan
aljabar abstrak ke silikon yang benar-benar berjalan tanpa memotong di
tengah.

**Yang sedang berjalan:** Yayasan Akademi Hijaiyyah Indonesia menerbitkan
Edisi I (Bab I–II) dan Edisi II (Cosmictera Hybit beserta seluruh hasil uji
fisik).

---

## Status penerapan

Kegunaan di atas terukur — angkanya ada, tesnya ada, dan sebagiannya sudah
berjalan di perangkat keras fisik sejak 10 September 2026.

Yang **belum**: belum ada pemasangan di lapangan, mitra industri, atau uji
lapangan untuk sektor mana pun di atas. Itu **AT** — pekerjaan yang belum
dikerjakan, bukan kemampuan yang belum ada. Membedakan keduanya adalah
seluruh guna label di proyek ini: kemampuan diukur, penerapan dijadwalkan.

Ketika satu penerapan industri terjadi, ia dicatat di sini dengan angkanya
sendiri — nama pihak, tanggal, dan apa yang diukur — bukan sebagai kalimat
yang melunak.
