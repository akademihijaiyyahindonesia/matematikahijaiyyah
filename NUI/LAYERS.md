# Dua belas lapis NUI — peta terhadap yang sudah ada

**Perintah pemilik, 21 September 2026.** NUI — *Natural Universal
Intelligence* — dibangun sebagai sistem komputasi yang memahami,
memverifikasi, memodelkan, dan mensintesis seluruh stack CosmicTera. Namanya
tetap; tidak ada nama baru, singkatan baru, atau rebranding.

**Bukan chatbot, bukan persona, bukan pembungkus LLM.** Dan aturan pemilik
yang mengikat halaman ini: *"Gunakan seluruh aset yang sudah ada di
repositori terlebih dahulu. Jangan menambah kompleksitas baru sebelum semua
aset yang sudah ada dimodelkan, dipetakan, dan diverifikasi oleh NUI."*

Halaman ini **peta**, bukan klaim kemampuan. Tiap lapis membawa lima hal yang
pemilik tuntut: tujuan, aset yang sudah ada, yang belum ada, cara verifikasi,
dan syarat selesai. Yang belum ada ditulis kosong — bukan diisi rencana yang
terdengar meyakinkan.

## Yang sudah berjalan hari ini, diukur

`src/hijaiyyah/nui/` berisi **13 modul**; `tests/test_ai/` berisi **131 tes**
yang lulus. PyTorch 2.14.0 terpasang. Semua angka di halaman ini datang dari
menghitung berkasnya, bukan dari ingatan.

| modul | apa yang ia lakukan | tes |
|---|---|---|
| `features.py` | tiap huruf jadi 5 angka geometris dari Master Table tersegel | `test_nui.py` |
| `dataset.py` | akumulasi huruf sungguhan, label primitivitas GF(2)/GF(5), rank | `test_nui.py` |
| `model.py` | jaringan permutation-invariant atas huruf terakumulasi | `test_nui.py` |
| `train.py` | melatih dan **membandingkan empat varian embedding, jujur** | `test_nui.py` |
| `multitask.py` | satu trunk, tiga pertanyaan berbeda (Fase 1) | `test_nui_multitask.py` (13) |
| `atom.py` | satu huruf, satu alamat: indeks Master Table = opcode HISA = alamat ROM | `test_nui_atom.py` (6) |
| `rack.py` | 28 huruf sebagai rak chip, tiap chip menjalankan komposisi eksomatriksnya | `test_nui_rack.py` (8) |
| `clockwork.py` | mekanisme deterministik per tick: `run`, `run_rack`, `channels`, `automate` | `test_nui_clockwork.py` (27) |
| `freeze.py` | protokol kabel loader dipalsukan jamnya, bukan protokolnya | `test_nui_freeze.py` (22) |
| `sram_mock.py` | protokol twin-port makro SRAM sky130 | `test_nui_sram_mock.py` (10) |
| `claims.py` | klaim luar diuji terhadap data tersegel repo ini — **keduanya negatif** | `test_nui_claims.py` (6) |
| `pattern_language.py` | "Titik → Transform → Garis" diuji sebagai urutan komposisi | `test_nui_pattern_language.py` (7) |

## Dua penomoran, dan keduanya dicatat

`NUI/ROADMAP.md` sudah punya **Fase 0–5**; perintah pemilik memberi **Lapis
0–11**. Keduanya tidak dihapus salah satunya (R1 dan disiplin "konflik dicatat,
bukan dirapikan sepihak"). Petanya:

```
Fase 0  sudah ada                    → Lapis 1 dan sebagian Lapis 2
Fase 1  selesai, hasil campuran      → Lapis 1
Fase 2  himpunan → urutan, program   → Lapis 3
Fase 3  fakta terverifikasi          → Lapis 0
Fase 4  sintesis program             → Lapis 10
Fase 5  NUI sebagai layanan          → belum dipetakan ke lapis mana pun
```

---

## Lapis 0 — Fakta terverifikasi

**Tujuan.** Basis fakta yang tiap butirnya punya sumber, bukti, dan cara
verifikasi.

**Aset yang sudah ada.** `src/hijaiyyah/core/master_table.py` (tersegel),
`src/hijaiyyah/core/guards.py`, `src/hijaiyyah/core/exomatrix.py`,
`src/hijaiyyah/crypto/cube.py`, `docs/HISA_SPEC.md`; label epistemik
VF/DP/CC/EH/AT di `cosmictera/RULES.md`; `cosmictera/TELEMETRY.md` yang sudah
berbentuk tabel fakta bersumber; dan `src/hijaiyyah/nui/claims.py` sebagai
polanya — klaim luar diuji terhadap data tersegel, dan **dilaporkan negatif**.

**Yang belum ada.** Satu basis fakta yang bisa dibaca mesin. Hari ini fakta
tersebar di tes dan dokumen; tidak ada struktur tunggal yang bisa ditanyai
"fakta ini dibuktikan oleh apa".

**Cara verifikasi.** Tiap fakta menyebut oracle yang menghasilkannya, dan
penjaga menuntut oracle itu ada dan lulus.

**Syarat selesai.** Setiap fakta di basis punya sumber, bukti, dan metode,
dan seluruhnya diperiksa ulang oleh pytest.

---

## Lapis 1 — Kecerdasan simbol

**Tujuan.** Memahami huruf → fitur → eksomatriks → properti.

**Aset yang sudah ada.** `features.py`, `atom.py`, `rack.py`, `dataset.py`,
Master Table tersegel. Terukur dan sudah terbukti: `verify_address_unification`
— indeks Master Table, opcode HISA, dan alamat ROM HCPU adalah **satu alamat**.

**Yang belum ada.** Antarmuka tanya-jawab atas properti itu; hari ini
jawabannya datang dari memanggil fungsi, bukan dari bertanya.

**Cara verifikasi.** `tests/test_ai/test_nui.py`, `test_nui_atom.py`, dan
oracle matematisnya (`core.exomatrix.matrix_order`).

**Syarat selesai.** Setiap properti huruf yang NUI sebut bisa dilacak ke
Master Table dan diperiksa oleh tes yang sudah ada.

---

## Lapis 2 — Kecerdasan struktural

**Tujuan.** Memahami `State(t) → Transform → State(t+1)`; urutan, bukan
himpunan.

**Aset yang sudah ada.** `clockwork.py` (27 tes) dengan `run`, `run_rack`,
`rank_permutations`, `channels`, `automate`; `rack.py`;
`pattern_language.py`, yang menguji urutan komposisi sebagai hipotesis dan
bukan slogan.

**Yang belum ada.** Model urutan atas program nyata — yang ada baru urutan
atas komposisi eksomatriks.

**Cara verifikasi.** `test_nui_clockwork.py`, `test_nui_rack.py`,
`test_nui_pattern_language.py`.

**Syarat selesai.** Urutan yang NUI prediksi cocok dengan `run_rack` tick demi
tick.

---

## Lapis 3 — Kecerdasan program

**Tujuan.** Memahami program sebagai fungsi: baca, jelaskan, prediksi keadaan
akhir.

**Aset yang sudah ada.** `src/hijaiyyah/hisa/machine.py` (`HISAMachine`) sebagai
**ground truth**, assembler, HVM, dan **59 program HASM** di `rtl/programs/` dan `rtl/programs/bench/`.
`NUI/ROADMAP.md` Fase 2 sudah menuliskan rencananya.

**Yang belum ada.** Semuanya di sisi NUI: tidak ada modul yang membaca program
lalu memprediksi keadaan akhirnya.

**Cara verifikasi.** Bandingkan prediksi terhadap `HISAMachine.run()` atas
program yang sama. Oracle-nya sudah ada dan sudah dipakai ribuan kali.

**Syarat selesai.** Prediksi keadaan akhir cocok dengan interpreter untuk
kumpulan program yang disebut, dan yang tidak cocok dilaporkan dengan namanya.

---

## Lapis 4 — Kecerdasan perangkat lunak

**Tujuan.** Memahami fungsi Python sebagai masukan → kebergantungan →
perubahan keadaan → keluaran.

**Aset yang sudah ada.** Repositori itu sendiri: 128 berkas sumber yang mypy
periksa, dan `tests/` sebagai spesifikasi perilakunya.

**Yang belum ada.** Ekstraktor graf fungsi. Tidak ada satu pun modul NUI yang
membaca kode Python hari ini.

**Cara verifikasi.** Graf yang dihasilkan diuji terhadap impor dan panggilan
yang benar-benar ada (`ast`), bukan terhadap tebakan.

**Syarat selesai.** Untuk fungsi yang disebut, graf menyebut kebergantungan
yang sama dengan yang `ast` temukan.

---

## Lapis 5 — Kecerdasan Linux

**Tujuan.** Memahami sistem operasi yang menjalankan CosmicTera.

**Aset yang sudah ada.** **Tidak ada.** `AGENTS.md` sudah mencatatnya: tidak
ada satu pun sisi host di repositori ini — tidak ada driver, layanan, pustaka,
kontainer, atau aplikasi. Yang ada hanya perkakas serial di `rtl/scripts/`.

**Yang belum ada.** Seluruhnya.

**Cara verifikasi.** Belum bisa ditetapkan sebelum ada yang dibangun.

**Syarat selesai.** Belum ditetapkan.

---

## Lapis 6 — Kecerdasan repositori

**Tujuan.** Graf repositori: sumber → tes → build → deploy, dan dampak
perubahan.

**Aset yang sudah ada.** `tests/test_integrity/` sudah mengkodekan banyak
hubungan itu sebagai penjaga: `test_agent_notes.py` (tiap commit dan berkas
yang disebut harus ada), `test_build_list.py`, `test_recipe_folders.py`,
`test_place_and_route.py` (sidik jari RTL terhadap wrapper).

**Yang belum ada.** Grafnya sebagai struktur yang bisa ditanyai; penjaga
memeriksa, tetapi tidak menjawab "apa yang terdampak kalau berkas ini
berubah".

**Cara verifikasi.** Graf diuji terhadap `git` dan `ast`: tiap sisi harus
punya bukti tekstual.

**Syarat selesai.** Untuk berkas yang disebut, graf menyebut tes yang memang
menyentuhnya.

---

## Lapis 7 — Kecerdasan perangkat keras

**Tujuan.** Memahami RTL sebagai fungsi: `State(t) → Logic → State(t+1)`.

**Aset yang sudah ada.** `rtl/scripts/lint_hcpu.py`,
`tests/test_integrity/test_board_wiring.py` (mengurai port Verilog),
`rtl/scripts/rack.py` (biaya slot bitstream), `src/hijaiyyah/nui/sram_mock.py`, dan
`src/hijaiyyah/nui/freeze.py` — keduanya sudah memodelkan protokol perangkat keras di
Python.

**Yang belum ada.** Model RTL sebagai fungsi. Yang ada mengurai antarmuka,
bukan perilaku.

**Cara verifikasi.** Testbench yang sudah ada (`rtl/tb/`, 26 bench, 0 FAIL)
adalah oracle-nya.

**Syarat selesai.** Prediksi keadaan berikutnya untuk modul yang disebut cocok
dengan benchnya.

---

## Lapis 8 — Paritas perangkat lunak dan perangkat keras

**Tujuan.** Membuktikan Python = HISA = RTL = FPGA untuk fungsi yang sama, dan
menemukan perbedaan secara otomatis.

**Aset yang sudah ada — ini lapis terkuat di repositori.** `698dd3e` tiga mesin
sepakat; `44ba928` HVM menjalankan semua opcode RTL;
`rtl/scripts/jamrah_board.py`, `hijrah_board.py`, `kabah_board.py` masing-masing
membandingkan papan dengan Python dan **sudah menemukan beda** (gerbang RTL
Jamrah tidak ada di silikon slot Ka'bah).

**Yang belum ada.** Penemuan divergensi yang otomatis dan menyeluruh; hari ini
tiap perbandingan ditulis tangan per modul.

**Cara verifikasi.** Perbandingan yang sudah ada — dan sabotase yang harus
merah (R3).

**Syarat selesai.** Untuk daftar fungsi yang disebut, tiap wujudnya
dibandingkan otomatis dan yang berbeda dilaporkan dengan namanya.

---

## Lapis 9 — Kecerdasan verifikasi

**Tujuan.** Tiap klaim punya metode pembuktian.

**Aset yang sudah ada.** Empat gerbang (`make lint typecheck`, pytest,
`make -C rtl/tb all`, bitstream), disiplin R3 (gerbang diuji dengan merusak
yang dijaganya), label epistemik, dan `cosmictera-build/CHECKLIST.md` yang
**sudah** memasangkan tiap centang dengan perintah untuk mengulanginya.

**Yang belum ada.** Pemetaan klaim → oracle yang bisa dibaca mesin. CHECKLIST
melakukannya untuk manusia.

**Cara verifikasi.** Penjaga yang menuntut tiap klaim menyebut oracle yang ada.

**Syarat selesai.** Tidak ada klaim di basis fakta tanpa oracle yang bisa
dijalankan.

---

## Lapis 10 — Sintesis

**Tujuan.** Menghasilkan artefak baru yang lolos oracle.

**Aset yang sudah ada.** Polanya sudah ada dan sudah berjalan di papan:
`rtl/scripts/build_container.py` (membangun container dan mengukur
relokasinya), `rtl/scripts/jamrah_board.py` (membangkitkan program dari badan
`jamrah_gate.hasm`, kata demi kata), `rtl/scripts/attack_lab.py`
(membangkitkan program berwaktu dan container rusak), `rtl/scripts/gen_rom.py`.

**Yang belum ada.** Sintesis yang NUI pandu. Yang ada generator yang ditulis
tangan.

**Cara verifikasi.** Artefak harus lolos oracle yang sama dengan artefak
tulisan tangan — assembler, interpreter, bench, papan.

**Syarat selesai.** Artefak yang disintesis lulus keempat gerbang tanpa
perlakuan khusus.

---

## Lapis 11 — Rekayasa otonom

**Tujuan.** Bug → analisis → patch → tes → verifikasi → kandidat commit.

**Aset yang sudah ada.** **Tidak ada.**

**Yang belum ada.** Seluruhnya.

**Cara verifikasi.** Belum bisa ditetapkan.

**Syarat selesai.** Belum ditetapkan.

---

## Yang tidak boleh diklaim

Aturan pemilik, disalin apa adanya karena ia mengikat: **jangan pernah**
mengklaim AGI, kesadaran, inteligensi manusia, atau kemampuan yang belum
diuji. Label epistemik tidak naik tanpa bukti baru (R2).

Dan satu batas yang sudah terukur di repositori ini, supaya tidak hilang di
antara dua belas lapis: dari empat varian embedding yang diadu `train.py`,
varian **eksomatriks** — struktur yang kriptografi Ka'bah sendiri pakai —
adalah yang **paling konservatif**, recall 0,4%. Struktur yang benar secara
matematis tidak otomatis berguna sebagai representasi, dan itu diukur, bukan
diperdebatkan.
