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

Tidak ada baris yang naik label tanpa bukti baru. Sebelumnya ada satu yang
turun — Fmax HCPU jadi `EH` karena desainnya tidak lagi muat di Tang Nano 9K —
dan sekarang naik lagi dengan bukti baru sungguhan, bukan diklaim balik begitu
saja: **Fmax HCPU adalah `CC` lagi, 114,65 MHz di Tang Nano 20K**, papan yang
menggantikan 9K. Riwayatnya ada di [OFF.md](OFF.md), bukan disembunyikan.

## Angka utuh, hari ini

```
4.593 tes Python lulus, 0 dilewati          ruff bersih, mypy bersih
  253 asersi RTL di 20 testbench, 0 gagal
   72 dari 96 opcode terimplementasi di RTL
   28 huruf, 28 opcode huruf (0xE0–0xFB), semuanya di RTL
    6 penyebab trap, 6 prasyarat OS tertutup, H-Kernel 4 dari 4
    2 bitstream muat & terrout (HCPU 67% LUT4, Ka'bah 58%, Tang Nano 20K)
    0 dari keduanya pernah benar-benar di-flash ke papan fisik
```

Baris terakhir sengaja ada di sini. Enam lapis menyala termasuk bitstream-nya
sekarang, tapi tak satu pun pernah dinyalakan di perangkat keras yang
benar-benar dipegang — `gowin_pack` sukses bukan papan menyala. Daftar yang
hanya memuat kabar baik bukan daftar build; lihat [ROADMAP.md](ROADMAP.md)
untuk langkah yang masih belum diambil.

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
