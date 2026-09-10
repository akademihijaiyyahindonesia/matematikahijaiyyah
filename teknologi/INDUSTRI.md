# Kegunaan di industri nyata

**Nol. Belum ada satu pun pihak industri yang memakai teknologi ini.**

Kalimat itu diletakkan di baris pertama dengan sengaja, karena inilah
halaman yang paling mudah dipakai berbohong — dan halaman semacam ini di
proyek lain biasanya dibuka dengan daftar sektor, bukan dengan pengakuan.

Yang bisa halaman ini kerjakan dengan jujur cuma satu hal: memisahkan
**sifat yang sudah terukur** dari **penerapan yang belum ada**, lalu
menjelaskan kenapa sifat itu relevan bagi industri tertentu. Yang pertama
punya angka. Yang kedua berlabel **AT**, seluruhnya, tanpa kecuali.

---

## Bagian 1 — Sifat yang terukur

Ini yang sudah ada angkanya, dan bukan janji.

### Pemeriksaan integritas dalam waktu konstan

Guard G1–G4 dan T1–T2 dievaluasi dalam **25 operasi**, tidak bergantung
panjang data, dan di silikon ia **satu instruksi** (`HGRD`) bukan rutin.
Terukur di `hcpu_guard.v` dan diuji `test_guard_coverage.py`,
`test_guard_sweep.py`. Label: **CC**.

Yang membuatnya tidak biasa: integritas jadi **aliran kendali**. `JGD` dan
`JNGD` membuat program bercabang atas kondisi "vektor ini masih sah" tanpa
satu pun pembandingan eksplisit yang bisa lupa ditulis.

### Determinisme bilangan bulat penuh

Tidak ada floating-point di inti data. Dataset-seal yang sama plus protokol
yang sama menghasilkan keluaran yang sama, di mesin mana pun — dan itu
diuji, bukan diasumsikan (`test_substrate_independence.py`). Label: **CC**.

Bukti terkuatnya justru dari hari bring-up: keluaran papan cocok dengan
simulator **byte-per-byte**, 23 dari 23, dan 28 nilai Θ̂ identik dengan
tabel kanonik.

### Jejak yang sangat kecil

Seluruh tabel kanonik — 28 huruf × 18 dimensi, 504 nilai — muat dalam
**252 byte** ROM setelah nibble-packing. Di FPGA, `hcpu_rom` tersintesis
jadi logika kombinasional, bukan penyimpanan. Label: **CC**.

### Kesetaraan perangkat lunak dan perangkat keras

HVM dan HCPU mengeksekusi bytecode yang sama, dan kesetaraannya diuji atas
program nyata (`test_execution_parity.py`, `test_isa_parity.py`). Label:
**CC**. Inilah yang membuat verifikasi silang mungkin dilakukan sama sekali.

### Provenans yang tersegel

Dataset disegel SHA-256, dan sidik jari RTL mengikat angka yang
terdokumentasi ke desain yang menghasilkannya
(`test_place_and_route.py`). Ubah satu berkas, tesnya gagal dan meminta
pengukuran ulang. Label: **DP** — benar karena konstruksinya.

---

## Bagian 2 — Industri yang peduli pada sifat itu

**Semuanya AT.** Tidak ada purwarupa yang dipasang di lapangan, tidak ada
mitra, tidak ada uji lapangan. Yang tertulis di bawah adalah **alasan
kenapa sifat di Bagian 1 relevan**, bukan laporan penerapan.

### Sistem tersemat dan IoT

252 byte ROM, aritmetika bilangan bulat penuh, dan pemeriksaan integritas
satu instruksi adalah kombinasi yang cocok untuk mikrokontroler tanpa FPU
dan dengan memori yang dihitung kilobyte. Guard yang berjalan O(1)
memungkinkan pemeriksaan setiap kali data disentuh, bukan sesekali saat
sempat. **AT.**

### Sistem yang harus bisa diaudit

Determinisme dan segel provenans menjawab pertanyaan yang mahal di sektor
teregulasi: *apakah keluaran ini bisa direproduksi persis, dan bisakah
dibuktikan datanya tidak berubah sejak disegel?* Rantai dari kurva Bézier
ke graf kanonik ke vektor ke silikon terekam seluruhnya di repositori ini.
**AT.**

### Pemrosesan teks Arab dan korpus Al-Qur'an

Dua puluh delapan huruf Hijaiyyah adalah tipe primitif di sini, bukan string
yang dicari di tabel. Penjumlahan huruf punya aljabar, dan anagram punya
invarian. Untuk beban kerja yang memang berbasis huruf Arab, itu memindahkan
pekerjaan dari pustaka ke bahasa. **AT.**

### Inti IP untuk FPGA/ASIC

HCPU muat di 67% Tang Nano 20K dan berjalan pada 118,43 MHz, Ka'bah 58% dan
165,98 MHz — keduanya dengan alur sintesis sumber terbuka penuh, tanpa IP
vendor berbayar. Jalur MPW-nya sudah dipetakan di `rtl/mpw/`, meski
pemetaan sel standar belum dimulai. **AT.**

### Pendidikan

Ini yang paling dekat jadi nyata, karena bukunya ada dan penerbitnya ada:
Yayasan Akademi Hijaiyyah Indonesia menerbitkan Edisi I (Bab I–II) dan
Edisi II (Cosmictera Hybit beserta seluruh hasil uji fisik). Sistem yang
bisa dijalankan siswa dari `.hc` sampai papan FPGA adalah bahan ajar yang
utuh. **AT** untuk kurikulum; buku itu sendiri sedang berjalan.

---

## Yang membuat halaman ini bisa dipercaya

Setiap angka di Bagian 1 punya berkas tes yang menjaganya:
`test_guard_coverage.py`, `test_guard_sweep.py`,
`test_substrate_independence.py`, `test_place_and_route.py`,
`test_letter_instructions.py`, `test_table_as_program.py`.

Bagian 2 tidak punya satu pun, dan memang tidak boleh punya — karena tidak
ada yang bisa diukur dari sesuatu yang belum dikerjakan. Kalau suatu hari
ada penerapan industri yang nyata, ia pindah ke Bagian 1 dengan angka, atau
tidak pindah sama sekali.
