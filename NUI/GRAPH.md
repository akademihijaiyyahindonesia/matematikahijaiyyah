# Graf repositori — Lapis 1 NUI

**Perintah pemilik, 21 September 2026.** Bukan pohon berkas, melainkan graf
komputasi: modul apa ada di mana, siapa mengimpor siapa, siapa menguji siapa,
siapa menyentuh perangkat keras, dan apa yang harus gagal kalau sesuatu rusak.

Aturan yang membentuk seluruh desainnya, kalimat pemilik sendiri: *"Seluruh
edge harus berasal dari import nyata, pemanggilan nyata, referensi nyata, path
nyata — bukan inferensi LLM."*

## Bentuknya

```
533 node      python 169 · test 158 · verilog 118 · hasm 62 · fakta 26
1.577 edge    imports 744 · mentions 787 · verifies 46
```

| edge | dari mana | buktinya |
|---|---|---|
| `imports` | pernyataan `import`, diurai `ast`, diselesaikan ke berkas di repo ini | nomor baris |
| `mentions` | path repo yang **tertulis** di dalam berkas — docstring, `.include` HASM, `$readmemh` Verilog. Nama telanjang ikut, **hanya kalau tepat satu berkas di pohon memakainya**: `loader.hasm` terselesaikan, `features.py` tidak | nomor baris |
| `verifies` | fakta Lapis 0 menunjuk ke apa yang membuktikannya | status faktanya |

**Satu relasi = satu edge.** Berkas yang menyebut berkas lain di empat puluh
baris punya satu relasi, bukan empat puluh; `evidence` menyimpan tempat
pertama dan `times` berapa kali berulang. Menghitung kemunculannya membuat 372
relasi jadi **10.736 baris yang mengatakan hal yang sama** — diukur, lalu
diperbaiki.

**Dua relasi diturunkan, dan dinamai begitu**: `verified_by` adalah edge
`imports` yang sumbernya di bawah `tests/`, dan `impact_of` menelusuri edge
`imports` mundur sampai tutupan transitifnya. Keduanya dihitung, tidak pernah
dinyatakan.

## Yang graf ini tidak punya

**Edge pemanggilan.** `ast` bisa melihat modul mengimpor modul; melihat
**fungsi mana memanggil fungsi mana** di bahasa dinamis butuh lebih dari
sebuah parse, dan itu akan jadi inferensi pertama di graf yang dibangun supaya
tidak punya satu pun. Contoh pemilik menyebut "siapa memanggil siapa", dan ia
**tidak ada di sini**. Mengatakannya adalah beda antara celah dan kebohongan.

**Dokumen.** 745 berkas Markdown belum jadi node: dokumen yang menyebut modul
adalah relasi yang lebih lemah daripada yang mengimpornya, dan mencampur
keduanya akan menaruh kutipan dan panggilan di pijakan yang sama. Dokumen
sudah diikat ke pohon oleh `tests/test_integrity/test_agent_notes.py`.

## Lima pertanyaan pemilik, dijawab graf

**Apa yang memverifikasi `atom.py`?**

```
tests/test_ai/test_nui_atom.py
tests/test_ai/test_nui_clockwork.py
tests/test_ai/test_nui_rack.py
```

**Apa hubungan `freeze.py` dengan `loader.hasm`?** Bukan import — `freeze.py`
tidak mengimpor apa pun dari HASM. Ia **kutipan**: `rtl/programs/loader.hasm`
tertulis di dalamnya, dan graf melabelinya `mentions`, bukan `imports`.

**Modul apa yang terhubung ke HCPU?** Tujuh belas berkas menyebut
`rtl/hcpu_top.v`, dan **86 berkas di luar `rtl/`** menyentuh sesuatu di
`rtl/` — termasuk lima fakta Lapis 0.

**Kalau `clockwork.py` rusak, tes mana yang harus gagal?**

```
tests/test_ai/test_nui_clockwork.py
tests/test_ai/test_nui_rack.py
```

Yang kedua **tidak terlihat dengan membaca kepala berkasnya**:
`test_nui_rack.py` mengimpor `clockwork` di dalam sebuah fungsi, baris 63.
Itu persis jenis sambungan yang graf ada untuk temukan.

**Fakta mana yang berasal dari papan?** Delapan, dan masing-masing menandai
dirinya sendiri begitu — lihat `facts/README.md`.

## Menjalankannya

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.repository_index
PYTHONPATH=src python3 -m hijaiyyah.nui.repository_graph
PYTHONPATH=src python3 -m hijaiyyah.nui.repository_graph src/hijaiyyah/nui/atom.py
PYTHONPATH=src python3 -m hijaiyyah.nui.repository_graph src/hijaiyyah/nui/clockwork.py --impact
python3 -m pytest -q tests/test_ai/test_nui_repository_graph.py
```

## Yang dijaga

`tests/test_ai/test_nui_repository_graph.py`, sepuluh tes, dan yang paling
penting bukan bahwa graf menjawab pertanyaan melainkan bahwa **tiap jawaban
bisa ditelusuri balik ke sebuah baris**: tiap edge `imports` harus mendarat di
baris yang benar-benar mengimpor, tiap `mentions` di baris yang benar-benar
menyebut nama berkasnya. Ditambah: tidak ada edge yang keluar dari himpunan
node, tidak ada edge ke diri sendiri, satu relasi tetap satu edge, dan modul
itu sendiri menyatakan apa yang tidak dipunyainya.
