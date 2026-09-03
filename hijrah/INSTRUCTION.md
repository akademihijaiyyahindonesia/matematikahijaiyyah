# Satu huruf, satu perintah

## Sebelum

Menaruh satu huruf ke akumulator:

```
    MOVI  R1, 2
    HLOAD H1, 2
    HCADD H0, H0, H1
```

Tiga instruksi, **dua angka**, tiga register — untuk satu huruf.

## Sesudah

```
    ب
```

Satu karakter. Opcode `0xE1`, dan **setiap bit di bawah byte opcode adalah nol**.

```
  ب  →  0xE1000000        HREG[0] ← HREG[0] + v(Ba)
```

## Kenapa tanpa operand

Karena tidak ada yang perlu dipilih. Huruf **sudah** membawa nilai, fungsi, dan
laju; menamainya lewat indeks lalu menjumlahkannya lewat register adalah mengeja
ulang yang sudah ada di dalamnya.

Dan akumulator implisit itu **aman, bukan sekadar pendek**:

> Guard tertutup di bawah penjumlahan — terukur atas seluruh 784 pasang dan
> 2.000 jumlah lima-suku. **Program yang tersusun dari huruf tidak bisa keluar
> dari himpunan sah.** Diperiksa tiap langkah, bukan cuma di akhir.

## Akibatnya

**Menulis sebuah kata menghitung codex-nya.**

```
    ب
    س
    م
    HALT
```

Tiga huruf sumber, dan akumulatornya berisi persis apa yang `string_integral`
kembalikan — diuji untuk بسم, جحخ, الله, ملك.

## Peta opcode

`0xE0–0xFB` — tepat 28 slot, kosong di peta buku. `0xFC–0xFE` tetap bebas,
`0xFF` tetap `HALT_ERR`.

Nama enum-nya ASCII (`L_ALIF`, `L_BA`) karena `hcpu_pkg.vh` membutuhkannya dan
identifier Verilog itu ASCII. **Huruf Arabnya terdaftar sebagai alias
assembler**, jadi `ج` dan `L_JIM` merakit identik. Ke-28 huruf sebenarnya valid
sebagai identifier Python — enum-nya bisa memakainya langsung — tapi kemudian
tes paritas tak bisa mencocokkan nama Python dengan define Verilog, dan tes itu
lebih berharga daripada keindahannya.

## Di RTL: satu jalur baru, tanpa perangkat keras baru

ROM sudah memuat 28 huruf. Codex ALU sudah menjumlah. Yang kurang hanya
**keluaran ROM sebagai operand kedua ALU**.

Decode menangkap rentangnya **di dalam `default`, sebelum ia sempat
menghentikan mesin** — satu perbandingan, bukan 28 case. Itu penting: `default`
di Decode adalah `HALT_ERR`, dan `OP_ERET` pernah hilang dari sana selama
beberapa commit, mengalihkan dengan benar lalu menghentikan pipeline.

## Satu ketidaksepakatan VM–silikon

`get_by_index` **berbasis 1**, `all_entries()` berbasis 0. Interpreter memakai
offset berbasis 0 pada akses berbasis 1 dan **diam-diam mengakumulasi huruf yang
salah**. RTL — yang menambah satu untuk mencapai ROM berbasis 1 — benar.

Dikunci di tes, karena tak ada hal lain di paket ini yang membuat beda itu
terlihat.
