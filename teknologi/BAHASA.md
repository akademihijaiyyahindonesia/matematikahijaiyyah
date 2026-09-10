# Bahasa dan runtime

Dari teks yang ditulis manusia sampai byte yang dieksekusi mesin. Lima
format berkas, dan tiap batas antar-format punya alat yang menyeberanginya.

```
.hc     bahasa HC          ditulis manusia
  │     lexer → parser → evaluator                  src/hijaiyyah/language/
  │     kompilator + Ψ-injector                     src/hijaiyyah/compiler/
  ▼
.hasm   assembly H-ISA     terbaca, satu instruksi per baris
  │     assembler                                   src/hijaiyyah/hisa/assembler.py
  ▼
.hbc    bytecode           dieksekusi HVM atau dimuat ke HCPU
```

---

## HC — bahasa dengan tipe hybit asli

`src/hijaiyyah/language/` — tujuh modul: `tokens`, `lexer`, `grammar`,
`parser`, `ast_nodes`, `evaluator`, `diagnostics`.

Yang membuatnya bukan sekadar bahasa lain: **hybit adalah tipe primitif**,
bukan pustaka. Sebuah huruf bukan `string` yang dicari di tabel — ia nilai
dengan aljabar sendiri, dan penambahan dua huruf adalah operasi bahasa,
bukan pemanggilan fungsi. Monoid terbatas `(V, +, 0)` itulah yang membuat
`+` punya arti pada huruf.

Spesifikasinya: `docs/HC_LANGUAGE_SPEC.md`, `docs/hc_language.md`.

## HCC — kompilator, dan Ψ-injector

`src/hijaiyyah/compiler/codegen.py` dan `psi.py`.

Ψ-injector adalah bagian yang tidak punya padanan di kompilator biasa: ia
menyisipkan pemeriksaan guard ke dalam kode terkompilasi, sehingga korupsi
vektor tertangkap **saat program berjalan**, bukan saat seseorang ingat
memanggil validator. Guard bukan pustaka yang bisa lupa dipakai; ia
dipancangkan kompilator.

## H-ISA — 74 opcode, 9 di antaranya asli-huruf

`src/hijaiyyah/hisa/` — `opcodes`, `registers`, `assembler`, `compiler`,
`machine`, `hbc_format`, `hcheck`. Definisi kanoniknya di
`rtl/hcpu_pkg.vh`, karena silikon dan perangkat lunak harus membaca daftar
yang sama.

Sembilan instruksi tidak bisa diturunkan dari ISA umum mana pun:

| Instruksi | Kerjanya |
|---|---|
| `HLOAD` | memuat huruf sebagai vektor 18 dimensi |
| `HCADD` | menjumlah dua huruf di monoid terbatas |
| `HGRD` | memeriksa guard — O(1), bukan pemindaian |
| `HNRM2` | norma kuadrat, integer |
| `HDIST` | jarak antar huruf |
| `HPACK` | nibble-packing ke bentuk kirim |
| `HCRC` | CRC32 atas bingkai HISAB |
| `JGD` | lompat kalau guard lulus |
| `JNGD` | lompat kalau guard gagal |

Dua yang terakhir menjadikan integritas sebagai **aliran kendali**. Program
bisa bercabang atas kondisi "vektor ini masih sah" tanpa satu pun
pembandingan eksplisit — itu yang tidak dimiliki prosesor lain.

## HVM — mesin virtual

`src/hijaiyyah/vm/`, spesifikasi `docs/hcvm_spec.md`. Mengeksekusi bytecode
yang sama yang dimuat HCPU, sehingga referensi perangkat lunak dan
perangkat keras bisa dibandingkan **byte-per-byte**. Kesetaraan itu bukan
kebetulan yang disyukuri; ia diuji (`test_execution_parity.py`,
`test_isa_parity.py`) dan ia yang membuat bring-up papan bisa divonis benar
atau salah, bukan diperdebatkan.

## HISAB — protokol kirim

`src/hijaiyyah/hisab/` — `serialize`, `protocol`, `digest`, `validate`.
Nibble-packing plus CRC32. Ini yang membuat vektor huruf bisa melintasi
kabel dan tetap bisa dibuktikan utuh di ujung sana.

## HAR — registri alfabet

`src/hijaiyyah/core/har.py`, spesifikasi `docs/har_spec.md`. Satu sumber
kebenaran untuk pemetaan huruf, supaya tidak ada dua tabel yang berbeda
diam-diam.

## Aljabar — lima medan

`src/hijaiyyah/algebra/` — `vektronometry`, `normivektor`, `aggregametric`,
`intrametric`, `exometric`. Bab II buku, sebagai kode yang bisa dijalankan.

## Skeleton dan CSGI

`src/hijaiyyah/skeleton/` — `skeletonizer`, `contractor`, `csgi`,
`mainpath`. Jalur dari bentuk huruf ke graf kanonik: inilah rantai
provenans dari kurva Bézier ke vektor yang kemudian masuk silikon.

---

## Alat baris perintah

| Perintah | Gunanya |
|---|---|
| `hc` | menjalankan dan memeriksa program HC |
| `hom` | mesin utuh — GUI dan alat analisis |
| `kabah` | operasi kripto Ka'bah |
| `hybit-ai` | menjalankan program `.hcai` lewat runtime AI lokal |

---

**Label.** Seluruh tumpukan di halaman ini **CC** — dijalankan, dan
kesetaraan HVM–HCPU diuji atas program nyata, bukan disimpulkan. Yang
**bukan** CC disebut di halamannya sendiri: lihat [KRIPTO.md](KRIPTO.md)
untuk spons yang tetap **EH**.
