# Dua belas lapis NUI — peta terhadap yang sudah ada

**Perintah pemilik, 21 September 2026.** NUI — *Natural Universal
Intelligence* — dibangun sebagai lapisan kecerdasan komputasi yang memahami
dan mengoperasikan seluruh ekosistem CosmicTera, dari huruf sampai silikon.
Namanya tetap; tidak ada nama baru, singkatan baru, atau rebranding. Bukan
chatbot, bukan pembungkus LLM, bukan sekadar classifier.

Aturan pemilik yang mengikat halaman ini, dan yang pertama adalah urutannya:
*"Gunakan seluruh aset yang sudah ada di repositori terlebih dahulu. Jangan
membuat sistem baru jika fungsi yang sama sudah ada."*

Halaman ini **peta**, bukan klaim kemampuan. Tiap lapis membawa lima hal:
tujuan, aset yang sudah ada, yang belum ada, cara verifikasi, dan syarat
selesai. Yang belum ada ditulis kosong — bukan diisi rencana yang terdengar
meyakinkan.

## Penomorannya berubah antara dua pesan pemilik

Perintah pertama (21 September) menomori lapisnya satu cara; perintah kedua
pada hari yang sama menomorinya lain. **Yang berlaku yang terakhir**, dan
pergeserannya dicatat di sini supaya tidak diam-diam:

| dulu | sekarang | lapis |
|---|---|---|
| 0 | **0** | fakta / pengetahuan terverifikasi |
| 6 | **1** | pemahaman repositori |
| 3 | **2** | pemahaman program |
| — | **3** | pemahaman eksekusi (baru) |
| 8 | **4** | paritas perangkat lunak ↔ keras |
| 5 | **5** | integrasi Linux |
| 7 | **6** | pemahaman perangkat keras |
| 9 | **7** | verifikasi fisik |
| — | **8** | diagnostik otonom (baru) |
| — | **9** | penalaran komputasional (baru) |
| 11 | **10** | rekayasa otonom |
| — | **11** | komputasi universal (baru) |

Yang hilang dari penomoran baru: lapis simbol dan lapis struktural (dulu 1 dan
2) — keduanya **sudah selesai** dan hidup di `features.py`, `atom.py`,
`rack.py`, `clockwork.py`, `pattern_language.py`; serta lapis sintesis (dulu
10), yang isinya kini masuk ke rekayasa otonom. `NUI/ROADMAP.md` masih memakai
penomoran ketiga, Fase 0–5, dan tidak dihapus: Fase 2 = Lapis 2, Fase 3 =
Lapis 0, Fase 4 = Lapis 10.

## Yang sudah berjalan hari ini, diukur

`src/hijaiyyah/nui/` berisi **14 modul**; `tests/test_ai/` berisi **131 tes**
yang lulus, ditambah 8 tes inventaris fakta. PyTorch 2.14.0 terpasang. Semua
angka di halaman ini datang dari menghitung berkasnya.

| modul | apa yang ia lakukan | tes |
|---|---|---|
| `features.py` | tiap huruf jadi 5 angka geometris dari Master Table tersegel | `test_nui.py` |
| `dataset.py` | akumulasi huruf sungguhan, label primitivitas GF(2)/GF(5), rank | `test_nui.py` |
| `model.py` | jaringan permutation-invariant atas huruf terakumulasi | `test_nui.py` |
| `train.py` | melatih dan **membandingkan empat varian embedding, jujur** | `test_nui.py` |
| `multitask.py` | satu trunk, tiga pertanyaan berbeda | `test_nui_multitask.py` (13) |
| `atom.py` | satu huruf, satu alamat: indeks Master Table = opcode HISA = alamat ROM | `test_nui_atom.py` (6) |
| `rack.py` | 28 huruf sebagai rak chip | `test_nui_rack.py` (8) |
| `clockwork.py` | mekanisme deterministik per tick | `test_nui_clockwork.py` (27) |
| `freeze.py` | protokol kabel loader dipalsukan jamnya, bukan protokolnya | `test_nui_freeze.py` (22) |
| `sram_mock.py` | protokol twin-port makro SRAM sky130 | `test_nui_sram_mock.py` (10) |
| `claims.py` | klaim luar diuji terhadap data tersegel — **keduanya negatif** | `test_nui_claims.py` (6) |
| `pattern_language.py` | "Titik → Transform → Garis" diuji sebagai urutan komposisi | `test_nui_pattern_language.py` (7) |
| `facts.py` | inventaris fakta Lapis 0 | `test_facts.py` (8) |

---

## Lapis 0 — Pengetahuan terverifikasi

**Tujuan.** Basis fakta yang tiap butirnya punya sumber, bukti, dan cara
verifikasi.

**Aset yang sudah ada.** `facts/` — 21 fakta di tujuh domain — dimuat dan
diperiksa `src/hijaiyyah/nui/facts.py`, dijaga
`tests/test_integrity/test_facts.py`. Sumber lamanya tetap:
`src/hijaiyyah/core/master_table.py` (tersegel),
`src/hijaiyyah/core/guards.py`, `src/hijaiyyah/core/exomatrix.py`,
`src/hijaiyyah/crypto/cube.py`, `docs/HISA_SPEC.md`,
`cosmictera/TELEMETRY.md`, `src/hijaiyyah/nui/claims.py`,
`src/hijaiyyah/nui/atom.py`.

Dari 21 fakta: **9 dihitung ulang** tiap kali tes berjalan, **7 dibuktikan
sebuah tes**, **5 diukur di papan** dan ditandai tidak bisa diulang tanpa
perangkat kerasnya.

**Yang belum ada.** Cakupan — 21 fakta permulaan, bukan seluruh yang terukur
di repo ini — dan sisi bertanya: basis ini bisa dimuat dan diperiksa, belum
ditanyai per-objek.

**Cara verifikasi.** Sudah berjalan: `derive` dihitung ulang, `pytest`
menyebut node yang harus ada, `board` menyebut perintahnya. Tiga sabotase
diuji dan ketiganya merah.

**Syarat selesai.** Tercapai untuk bentuknya; belum untuk cakupannya.

---

## Lapis 1 — Pemahaman repositori

**Tujuan.** Membaca pohon proyek, memahami modul dan hubungan antar modul.

**Aset yang sudah ada.** `tests/test_integrity/` sudah mengkodekan banyak
hubungan itu sebagai penjaga: `test_agent_notes.py` (tiap commit dan berkas
yang disebut harus ada), `test_build_list.py`, `test_recipe_folders.py`,
`test_place_and_route.py` (sidik jari RTL terhadap wrapper), dan sekarang
`test_nui_layers.py` serta `test_facts.py`.

**Yang belum ada.** Grafnya sebagai struktur yang bisa ditanyai. Penjaga
memeriksa; ia tidak menjawab "apa yang terdampak kalau berkas ini berubah".

**Satu contoh yang sudah diukur, dan rantainya tidak seperti yang dikira.**
Perintah pemilik mencontohkan `atom → rack → clockwork → freeze → multitask`.
Diukur dari `import`-nya sendiri:

```
atom      → (tidak mengimpor modul NUI lain)
rack      → atom
clockwork → atom, rack
freeze    → rack           (bukan dari clockwork)
multitask → dataset, model (tidak menyentuh freeze sama sekali)
facts     → atom
model     → dataset
```

Tiga sambungan pertama benar; dua terakhir tidak. Itulah yang lapis ini ada
untuk menghasilkan.

**Cara verifikasi.** Graf diuji terhadap `ast` dan `git`: tiap sisi punya
bukti tekstual.

**Syarat selesai.** Untuk berkas yang disebut, graf menyebut modul dan tes
yang memang menyentuhnya.

---

## Lapis 2 — Pemahaman program

**Tujuan.** Membaca `.hasm` dan mengeluarkan opcode, operand, alur, efek
register, efek memori.

**Aset yang sudah ada.** `src/hijaiyyah/hisa/assembler.py` dan
`src/hijaiyyah/hisa/machine.py` sebagai **ground truth**, `src/hijaiyyah/hvm/`,
dan **59 program HASM** di `rtl/programs/` dan `rtl/programs/bench/`.

**Yang belum ada.** Semuanya di sisi NUI: tidak ada modul yang membaca program
lalu menjelaskan efeknya.

**Cara verifikasi.** Bandingkan terhadap `assemble()` dan `HISAMachine`.
Oracle-nya sudah ada dan sudah dipakai ribuan kali.

**Syarat selesai.** Untuk program yang disebut, penjelasan yang dihasilkan
cocok dengan yang assembler dan interpreter hasilkan.

---

## Lapis 3 — Pemahaman eksekusi

**Tujuan.** Bukan hanya membaca kode, melainkan tahu keadaan **sebelum →
instruksi → sesudah** untuk tiap langkah.

**Aset yang sudah ada.** `HISAMachine.run()` mengembalikan daftar
`TraceEntry`, `HISAMachine.step()` melangkah satu instruksi, dan
`dump_state()` memberi keadaan penuh — persis ground truth yang pemilik
sebut. Dipakai nyata oleh `rtl/scripts/attack_lab.py` dan
`tests/test_integrity/test_burn_in.py`, yang menjalankan `burn_in.hasm` di
interpreter dan membandingkan keluarannya.

**Yang belum ada.** Prediksi. Yang ada menjalankan; belum ada yang
memperkirakan keadaan akhir tanpa menjalankan.

**Cara verifikasi.** Prediksi dibandingkan dengan jejak interpreter, langkah
demi langkah.

**Syarat selesai.** Untuk kumpulan program yang disebut, prediksi cocok; yang
tidak cocok dilaporkan dengan namanya.

---

## Lapis 4 — Paritas perangkat lunak dan perangkat keras

**Tujuan.** Tiap opcode terlacak dari sumber → assemble → interpreter → RTL →
papan.

**Aset yang sudah ada — ini lapis terkuat di repositori.** `698dd3e` tiga
mesin sepakat; `44ba928` HVM menjalankan semua opcode RTL;
`rtl/scripts/jamrah_board.py`, `rtl/scripts/hijrah_board.py`,
`rtl/scripts/kabah_board.py` masing-masing membandingkan papan dengan Python
dan **sudah menemukan beda**.

**Yang belum ada.** Penemuan divergensi yang otomatis dan menyeluruh; hari ini
tiap perbandingan ditulis tangan per modul.

**Cara verifikasi.** Perbandingan yang sudah ada, dan sabotase yang harus
merah (R3).

**Syarat selesai.** Untuk daftar opcode yang disebut, tiap wujudnya
dibandingkan otomatis dan yang berbeda dilaporkan dengan namanya.

---

## Lapis 5 — Integrasi Linux

**Tujuan.** Memahami host nyata: menjalankan program, membaca log,
filesystem, proses, service, runtime. Targetnya Ubuntu Linux.

**Aset yang sudah ada.** **Tidak ada.** `AGENTS.md` sudah mencatatnya: tidak
ada satu pun sisi host di repositori ini — tidak ada driver, layanan,
pustaka, kontainer, atau aplikasi. Yang ada hanya perkakas serial di
`rtl/scripts/`, dan mesin pengembangannya macOS, bukan Ubuntu.

**Yang belum ada.** Seluruhnya.

**Cara verifikasi.** Belum bisa ditetapkan sebelum ada yang dibangun.

**Syarat selesai.** Belum ditetapkan.

**Satu selisih label yang dicatat, bukan dirapikan.** Pemilik menandai lapis
ini **EH**. Tabel `cosmictera/RULES.md` sendiri mendefinisikan EH sebagai
"terukur, belum dikriptanalisis" dan **AT** sebagai "belum dikerjakan". Lapis
tanpa satu pun aset jatuh pada definisi AT, bukan EH. Selisihnya dilaporkan;
labelnya keputusan pemilik.

---

## Lapis 6 — Pemahaman perangkat keras

**Tujuan.** Memahami HCPU, UART, SRAM, pipeline, loader, peta memori.

**Aset yang sudah ada.** `rtl/` (30 modul HCPU, 13 modul Ka'bah, 26
testbench), `rtl/fpga/`, `rtl/mpw/`; `rtl/scripts/lint_hcpu.py`;
`tests/test_integrity/test_board_wiring.py` yang mengurai port Verilog;
`rtl/scripts/rack.py` untuk biaya slot bitstream; dan dua model perangkat
keras yang sudah berjalan di Python — `src/hijaiyyah/nui/sram_mock.py`
(protokol twin-port) dan `src/hijaiyyah/nui/freeze.py` (protokol kabel
loader).

**Yang belum ada.** Model RTL sebagai fungsi. Yang ada mengurai antarmuka dan
memodelkan dua protokol, bukan perilaku umum.

**Cara verifikasi.** 26 testbench di `rtl/tb/` adalah oracle-nya.

**Syarat selesai.** Prediksi keadaan berikutnya untuk modul yang disebut cocok
dengan benchnya.

---

## Lapis 7 — Verifikasi fisik

**Tujuan.** Membedakan simulasi dari perangkat keras nyata, dengan kategori
VF / CC / DP / EH / AT sesuai RULES.

**Aset yang sudah ada — dan lapis ini sudah berjalan.** Tangga bukti empat
tingkat (terakit → tersimulasi → tersintesis → **berjalan**) ada di
`AGENTS.md` dan mengikat; `cosmictera-build/PAPAN.md` mencatat apa yang
benar-benar keluar dari papan; `cosmictera-build/CHECKLIST.md` memasangkan
tiap centang dengan perintah untuk mengulanginya;
`tests/test_integrity/test_place_and_route.py` menolak sidik jari yang tidak
diukur ulang; dan inventaris fakta menandai lima faktanya **board** —
tidak bisa dijalankan ulang tanpa perangkat kerasnya.

**Yang belum ada.** Tidak ada yang hilang dari bentuknya. Yang belum adalah
cakupan yang sama luasnya dengan repositori.

**Cara verifikasi.** `test_facts.py` menuntut tiap fakta `board` menyebut
perintahnya; `test_build_list.py` menuntut tiap centang menyebut jalurnya.

**Syarat selesai.** Tidak ada klaim di repo ini yang tidak bisa ditelusuri ke
salah satu dari empat tingkat itu.

---

## Lapis 8 — Diagnostik otonom

**Tujuan.** Menemukan mismatch, regresi, kegagalan paritas, dan asumsi yang
patah — secara otomatis.

**Aset yang sudah ada.** Alat yang menemukan, tetapi dijalankan tangan:
`jamrah_board.py`, `hijrah_board.py`, `kabah_board.py`,
`rtl/scripts/attack_lab.py`, `rtl/scripts/burn_in_report.py`, empat gerbang,
dan disiplin R3.

**Yang sudah benar-benar ditemukan**, supaya daftarnya tetap yang nyata:
gerbang RTL Jamrah **tidak ada di slot Ka'bah** (dipangkas habis, hanya
`$scopeinfo` tersisa); permutasi Ka'bah **bukan permutasi** (rank 1276/1600,
`3ccf193`); celah N_CC SDIO yang **papan** temukan, bukan bench (`708a9cd`);
`PRINT` salah untuk nilai besar; kartu gagal init sesudah rekonfigurasi di
tengah pembacaan; dan diam 140 detik yang ternyata milik host.

**Mismatch latensi SRAM tidak ada di daftar itu.** `sram_mock.py` memodelkan
latensi satu siklus dan 10 tesnya hijau; tidak ada catatan mismatch yang
pernah ditemukan. Dicatat supaya contoh tidak jadi sejarah.

**Yang belum ada.** Yang otomatisnya.

**Cara verifikasi.** Temuan harus reproducible dengan perintah yang dicatat,
seperti tiap baris CHECKLIST.

**Syarat selesai.** Untuk kelas mismatch yang disebut, alat menemukannya tanpa
diberi tahu di mana harus melihat.

---

## Lapis 9 — Penalaran komputasional

**Tujuan.** Menalar dampak lintas lapis: kalau SRAM berubah, apa efeknya ke
pipeline, RTL, timing, tapeout.

**Aset yang sudah ada.** **Tidak ada** sebagai penalaran. Yang ada adalah
bahannya: graf yang belum dibangun (Lapis 1), sidik jari place and route yang
menolak angka basi, dan `rtl/mpw/MPW_SHUTTLE_PLAN.md`.

**Yang belum ada.** Seluruh penalarannya. Lapis ini tidak bisa berdiri sebelum
Lapis 1 punya grafnya.

**Cara verifikasi.** Jawaban harus menyebut kebergantungan yang nyata dan bisa
ditunjukkan, bukan yang masuk akal.

**Syarat selesai.** Belum ditetapkan.

---

## Lapis 10 — Rekayasa otonom

**Tujuan.** Mengusulkan patch, tes, benchmark, dokumentasi — semuanya
terverifikasi, dan tidak ada kode yang berubah tanpa bukti.

**Aset yang sudah ada.** Polanya sudah ada sebagai generator yang ditulis
tangan: `rtl/scripts/build_container.py`, `rtl/scripts/jamrah_board.py`
(membangkitkan program dari badan `jamrah_gate.hasm` kata demi kata),
`rtl/scripts/attack_lab.py`, `rtl/scripts/gen_rom.py`.

**Yang belum ada.** Sisi otonomnya.

**Cara verifikasi.** Artefak harus lolos oracle yang sama dengan artefak
tulisan tangan — assembler, interpreter, bench, papan, empat gerbang.

**Syarat selesai.** Artefak yang diusulkan lulus keempat gerbang tanpa
perlakuan khusus.

---

## Lapis 11 — Komputasi universal

**Tujuan.** Seluruh CosmicTera sebagai satu model pengetahuan: huruf →
matematika → eksomatriks → codex → HISA → program → kernel → Linux → RTL →
FPGA → ASIC → silikon.

**Aset yang sudah ada.** **Tidak ada.**

**Yang belum ada.** Seluruhnya.

**Cara verifikasi.** Belum bisa ditetapkan.

**Syarat selesai.** Belum ditetapkan. Status **AT**, dan pemilik sendiri
menandainya begitu.

---

## Yang tidak boleh diklaim

Aturan pemilik, disalin apa adanya karena ia mengikat: **jangan pernah**
mengklaim AGI, kesadaran, inteligensi manusia, atau kemampuan yang belum
diuji. Label epistemik tidak naik tanpa bukti baru (R2).

Dan satu batas yang sudah terukur, supaya tidak hilang di antara dua belas
lapis: dari empat varian embedding yang diadu `train.py`, varian
**eksomatriks** — struktur yang kriptografi Ka'bah sendiri pakai — adalah yang
**paling konservatif**, recall 0,4%. Struktur yang benar secara matematis
tidak otomatis berguna sebagai representasi, dan itu diukur, bukan
diperdebatkan.
