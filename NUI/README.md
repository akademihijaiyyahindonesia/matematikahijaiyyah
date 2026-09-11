# NUI — otak kecerdasan yang benar-benar dibangun

Ini bukan folder catatan. Ini indeks untuk **program nyata** yang membangun
NUI (Natural Universal Intelligence) sebagai jaringan saraf terlatih —
kodenya, tugasnya, dan hasil ukurnya, apa adanya.

Halaman ini mencatat apa yang **sudah** ada. Untuk arah ke depan — dari satu
klasifikasi menuju kecerdasan yang lebih umum, dibangun dari aset proyek ini
sendiri, bukan LLM luar — lihat [`ROADMAP.md`](ROADMAP.md). Fondasi di
bawah semua fase itu — huruf sebagai alamat (indeks Master Table = opcode
HISA = alamat ROM HCPU) dengan dua wujud, perangkat lunak dan fisik
(UART nyata pada 27 MHz) — ada di `nui/atom.py`, dijelaskan di
[`ROADMAP.md`](ROADMAP.md#atom-satu-alamat-dua-wujud-nuiatompy-cc--selesai).

## Jalankan langsung

```bash
pip install .[nui]          # PyTorch, sekali saja
python3 NUI/pipeline.py --quick    # ~20 detik, lintas semua 4 tahap
python3 NUI/pipeline.py            # jalan penuh: 4.000 sekuens, 500 epoch, ~15-20 detik
```

[`pipeline.py`](pipeline.py) ada di folder ini, bukan sekadar menunjuk ke
tempat lain — ia benar-benar mengeksekusi tiap tahap (fitur → dataset →
model → latih & uji) dan mencetak hasilnya baris demi baris.

## Programnya, dan bagaimana ia bekerja

Kode library ada di [`src/hijaiyyah/nui/`](../src/hijaiyyah/nui/) — `pipeline.py`
mengimpornya, bukan menyalinnya. Empat berkas, satu alur:

```
features.py    → tiap huruf jadi 5 angka: titik, garis, lengkung, theta, rho
                  (Nuqthah/Khat/Qaws/Θ̂/ρ — dibaca dari Master Table tersegel,
                  bukan diciptakan untuk proyek ini)
dataset.py      → akumulasi huruf sungguhan (HREG[0] += v(huruf), persis
                  rtl/programs/letters.hasm), berlabel primitivitas GF(2)
                  nyata via core.exomatrix.matrix_order
model.py        → jaringan: multihot(28 huruf) → embedding → jumlah → MLP
                  → prediksi. Permutation-invariant karena tugasnya memang
                  begitu (penjumlahan v18 komutatif, dibuktikan bukan
                  diasumsikan)
train.py        → python3 -m hijaiyyah.nui.train — melatih & membandingkan
                  4 varian embedding sekaligus, jujur soal hasilnya
```

**Otaknya secara harfiah adalah empat varian embedding yang diadu**, semua
memprediksi hal yang sama (apakah eksomatriks huruf yang terakumulasi punya
orde maksimum GF(2), properti yang sama yang `cosmic-codex-jim/` ukur untuk
ج dan خ):

| Embedding | Dim | Sumber | Beku? |
|---|---:|---|---|
| **physics** | 5 | `features.py` (titik/garis/lengkung/theta/rho) | ya |
| **exomatrix** | 25 | `core.exomatrix.build_exomatrix` — persis yang `crypto/cube.py` pakai untuk menurunkan S-box Ka'bah | ya |
| **baseline-5** | 5 | acak, dilatih penuh | tidak |
| **baseline-25** | 25 | acak, dilatih penuh | tidak |

## Hasil terukur (bukan diklaim)

`python3 -m hijaiyyah.nui.train`, 4.000 sekuens akumulasi acak → 76.822
contoh latih seimbang, 17.220 contoh distribusi alami, plus 28 prefix
`letters.hasm` sungguhan:

| | physics | exomatrix | baseline-5 | baseline-25 |
|---|---:|---:|---:|---:|
| parameter terlatih | 385 | 705 | 525 | 1.405 |
| akurasi terkalibrasi | 0,961 | 0,955 | 0,960 | 0,958 |
| precision terkalibrasi | **0,970** | **1,000** | 0,789 | 0,637 |
| recall terkalibrasi | 0,125 | **0,004** | 0,136 | **0,157** |

**Dua temuan nyata, satu positif satu negatif — dilaporkan sama jujurnya.**
Physics (5 angka geometris beku) mengalahkan baseline-5 pada precision
dengan parameter lebih sedikit. Tapi exomatrix — struktur PERSIS yang
kriptografi Ka'bah sendiri pakai untuk seed S-box-nya — adalah varian
**paling konservatif dari semuanya**: precision sempurna tapi recall 0,4%,
nyaris tidak pernah memprediksi positif sama sekali. Baseline-25 yang
dilatih bebas (tanpa prior geometris atau kriptografis apa pun) justru
recall-nya paling tinggi. Rincian penuh, termasuk kenapa kalibrasi prior
diperlukan: [`src/hijaiyyah/nui/README.md`](../src/hijaiyyah/nui/README.md).

## Fase 1 sudah dicoba: satu trunk, tiga tugas

`python3 -m hijaiyyah.nui.multitask` — trunk yang sama, tiga kepala:
GF(2) (di atas), GF(5) (modulus lain, ~5,2% positif), dan rank eksomatriks
(0..5, jenis pertanyaan berbeda, bukan cuma ya/tidak lagi). `rank`
mengalahkan baseline-mayoritas di keempat varian — bukti pertama satu
representasi berguna lintas pertanyaan. `gf5_primitive` nyaris gagal total
di tiga dari empat varian, dicek langsung (bukan diasumsikan bug
kalibrasi). Satu rencana — guard sebagai label tambahan — dicoret sebelum
jadi kode setelah terbukti trivial (selalu benar). Rincian penuh dan angka
lengkap: [`ROADMAP.md`](ROADMAP.md), [`src/hijaiyyah/nui/README.md`](../src/hijaiyyah/nui/README.md).

## Clockwork, rack, dan freeze mode: mekanisme deterministik, bukan jaringan saraf

`pipeline.py`'s Stage 5 menjalankan mekanisme terpisah yang bukan jaringan
saraf sama sekali — tidak ada bobot, tidak ada yang dilatih: 28 huruf
sebagai **rack** (`nui/rack.py`, tiap huruf satu **chip** yang menjalankan
komposisi eksomatriksnya sendiri lewat `Chip.boot()`/`Chip.step()`),
diurutkan dan digroundkan tick demi tick oleh `nui/clockwork.py`
(`run()`, `run_rack()`, `automate()`). Ditutup dengan `nui/freeze.py`:
protokol kabel loader (`rtl/tb/tb_gowin_loader_nui.v`'s klaim fisik)
dipalsukan jamnya — bukan protokolnya — jadi tiap tes berjalan dalam
milidetik, bukan detik simulasi RTL. Rincian penuh, termasuk kenapa ini
bukan LLM dan apa yang belum berjalan di perangkat keras nyata:
[`ROADMAP.md`](ROADMAP.md#clockwork-mekanisme-berurutan-bukan-jaringan-saraf-nuiclockworkpy-cc--selesai).

