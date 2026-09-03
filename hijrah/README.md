# HIJRAH

**H**ijaiyyah **I**njection **R**aw **H**ertz — mencacah dengan huruf, bukan
dengan bit.

Aliran bit membawa satu bit per denyut. Klaim yang diuji di sini: aliran huruf
membawa jauh lebih banyak, karena huruf **bukan denyut** — ia nilai, fungsi,
relasi, dan laju sekaligus. Diukur sebagai operator, bukan diperdebatkan.

```
  panjang   GF(2)    GF(4)    GF(5)      aliran bit
        1    4,58     4,81     4,81            1,00
        3    3,76     4,45     4,67            1,00
        5    3,22     4,06     4,56            1,00
```

`log₂28 = 4,81` adalah langit-langitnya — huruf tak bisa membawa lebih dari
identitasnya sendiri. Atas GF(5) ia masih **4,56 setelah lima komposisi**:
huruf berperilaku hampir seperti generator bebas di sana.

---

## Dan lapangannya adalah pokoknya

Atas GF(2) **empat pasang huruf runtuh** jadi satu muka:

```
  ح Ha   = ل Lam      ص Shad = ق Qaf
  ش Syin = ن Nun      ع Ain  = ي Ya
```

Sebabnya eksak: **setiap komponen tempat mereka berbeda, berbedanya persis 2 —
dan 2 lenyap mod 2.**

> **Membaca huruf mod 2 adalah membacanya sebagai bit**, dan harganya empat
> huruf plus sepertiga kepadatan. **GF(4)** modulus terkecil yang memisahkan
> ke-28 — dua bit per komponen, bukan satu.

---

## Isi folder

| Berkas | Isi |
|---|---|
| [`UNIT.md`](UNIT.md) | Huruf sebagai satuan: kepadatan, lapangan, dan apa yang hilang mod 2 |
| [`INSTRUCTION.md`](INSTRUCTION.md) | Satu huruf, satu perintah — opcode `0xE0–0xFB` |
| [`JUMP.md`](JUMP.md) | Lompatan cacahan: derajat memilih panel, kejarangan membayarnya |

Dijangkar oleh
[`test_hijrah.py`](../tests/test_integrity/test_hijrah.py),
[`test_letter_instructions.py`](../tests/test_integrity/test_letter_instructions.py),
[`test_degree_panels.py`](../tests/test_integrity/test_degree_panels.py),
[`test_degree_function.py`](../tests/test_integrity/test_degree_function.py) dan
[`test_letter_machines.py`](../tests/test_integrity/test_letter_machines.py) —
41 tes.

Mesin di dalam satu huruf tertentu ada di
[`cosmic-codex-jim/`](../cosmic-codex-jim/README.md).
