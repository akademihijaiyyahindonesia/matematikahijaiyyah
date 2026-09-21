# CosmicTera Computing — daftar build

**Draf.** Ini daftar apa yang **sudah menyala** untuk komputasi, apa yang belum,
dan apa yang terbangun tapi tidak bisa dijalankan. Bukan rencana dan bukan
janji: setiap baris menyebut tempatnya di pohon ini dan apa yang membuktikannya.

| berkas | isinya |
|---|---|
| [CHECKLIST.md](CHECKLIST.md) | daftar cek — tiap centang punya perintahnya |
| [ON.md](ON.md) | yang menyala — enam lapis, dengan bukti per baris |
| [OFF.md](OFF.md) | yang belum, dan yang terbangun tapi terhalang |
| [ROADMAP.md](ROADMAP.md) | dari Tang Nano 20K ke HCPU fisik, berfase — bukan daftar cek, peta |

## Cara membaca

Sebuah baris masuk **ON** hanya jika ia bisa dijalankan sekarang, di pohon ini,
dengan satu perintah — dan sesuatu yang otomatis akan gagal bila ia rusak. Kalau
buktinya cuma "pernah jalan" atau "ada kodenya", tempatnya di OFF.

Label epistemik proyek tetap berlaku dan mengikat:

| label | artinya |
|---|---|
| `VF` | terbukti secara formal |
| `CC` | terhitung dan tereproduksi di pohon ini |
| `DP` | tergantung pada data yang belum tetap |
| `EH` | hipotesis; belum terukur |
| `AT` | terarah, belum dibangun |

Tidak ada baris yang naik label tanpa bukti baru. **Fmax HCPU adalah `CC`:
116,44 MHz pasca-perutean di Tang Nano 20K**, dan bukan angka sintesis —
papan menjalankannya, UART membalas 23 byte yang cocok byte-per-byte dengan
simulasi.

## Angka utuh, hari ini

```
5.196 tes Python lulus, 0 dilewati          ruff bersih, mypy bersih
    1 dari 5.196 gagal hari ini: sidik jari HDMI, M5.2B ditunda (OFF.md)
  408 asersi RTL di 39 testbench, 0 gagal
   82 dari 103 opcode terimplementasi di RTL
   28 huruf, 28 opcode huruf (0xE0–0xFB), semuanya di RTL
    6 penyebab trap, 6 prasyarat OS tertutup, H-Kernel 4 dari 4
    3 bitstream muat & terrout (HCPU 71%, Ka'bah 58%, HDMI 73% LUT4)
    3 dari ketiganya di-flash dan dijalankan di papan fisik
```

**Dua baris terakhir dulu berbunyi "2 bitstream" dan "0 dari keduanya pernah
benar-benar di-flash".** Itu benar sampai 10 September 2026 dan tidak lagi
benar sesudahnya: ketiga slot dimuat berurutan ke papan yang sama dan
menjawab — rekamannya per program di [PAPAN.md](PAPAN.md). Daftar yang hanya
memuat kabar baik bukan daftar build, tapi daftar yang menyangkal pengukuran
sendiri lebih buruk lagi; lihat [ROADMAP.md](ROADMAP.md) untuk langkah yang
masih belum diambil.

## Apa yang menjaga daftar ini

[`tests/test_integrity/test_build_list.py`](../tests/test_integrity/test_build_list.py)
— dan ia tidak membandingkan tulisan dengan tulisan. Setiap angka di sini
dihitung ulang dari benda yang diwakilinya: cacah opcode dari modul opcode,
cacah huruf dari Master Table, cacah bench dari Makefile, utilisasi dari header
wrapper. Naikkan satu klaim tanpa menaikkan buildnya dan tes ini jatuh; ketiga
sabotase itu sudah dicoba.

Itu penting karena repo ini pernah tertipu justru oleh penjaga yang
membandingkan transkripsi dengan transkripsi: angka place-and-route dan tesnya
diam bersama-sama selama desainnya bergerak. Daftar tanpa jangkar akan
mengulanginya.

## Folder resep lain

| folder | isinya |
|---|---|
| [`cosmictera/`](../cosmictera/) | aturan, sistem, dan angka konkret CosmicTera |
| [`cosmic-codex-jim/`](../cosmic-codex-jim/) | Jim sebagai pusat: mesin, gelombang, batas |
| [`hijrah/`](../hijrah/) | satuan, instruksi, dan lompatan cacahan |
| [`matematika-hijaiyyah/`](../matematika-hijaiyyah/) | guard, aljabar, silsilah |
| [`kabah/`](../kabah/) | subsistem kripto, alur, silikon |

Folder ini tidak mengulang isi mereka. Ia hanya menjawab satu pertanyaan:
**apa yang menyala.**
