# Matematika: BAB I dan BAB II

Kosakata yang datang dari buku, bukan dari rekayasa. Tiap entri menyebut modul
yang mengerjakannya; yang tidak punya modul tidak ada di sini.

---

## Tiga primitif — titik, garis, lengkung

Urutannya adalah urutan konstruksi, dan namanya Arab untuk unsur pembentuk
huruf. `docs/csgi_algorithm_spec.md` §4.1 memutuskannya: tiap edge diukur
simpangannya dari garis lurus, lalu ditandai `KHATT` atau `QAWS`.

| istilah | arti | slot | di mana |
|---|---|---|---|
| **nuqṭah** | titik | Na · Nb · Nd | `core/constants.py` |
| **khaṭṭ** | garis lurus | Kp · Kx · Ks · Ka · Kc | `skeleton/csgi.py` |
| **qaws** | lengkung | Qp · Qx · Qs · Qa · Qc | `skeleton/csgi.py` |

**Lingkaran bukan blok keempat.** Ia lengkung yang menutup, dan masuk sebagai
**koefisien**: `U = Qx + Qs + Qa + 4·Qc`. Angka 4 itu harga satu kurva tertutup
dalam perempat putaran — dari sanalah kuantum 90° berasal.

| istilah | arti | di mana |
|---|---|---|
| **Inḥinā'** | kelengkungan pada MainPath | `src/hijaiyyah/skeleton/csgi.py` |
| **MainPath** | jalur utama rangka huruf, tempat Inḥinā' diukur | `skeleton/csgi.py` |
| **rasm** | bentuk kanonik huruf yang dikunci | `core/master_table.py` |

---

## Agregat dan tiga simbol

| istilah | arti | di mana |
|---|---|---|
| **A_N** · **AK** · **AQ** | jumlah tiap blok; G1–G3 mendefinisikannya | `hcpu_guard.v` |
| **Θ̂** | komponen 0 — sudut, kelipatan 90° | `hcpu_pkg.vh` |
| **U** | *turning budget*, `Qx + Qs + Qa + 4·Qc` | `hcpu_codex_alu.v` — `CU` 0x4D |
| **ρ** | residu turning, `Θ̂ − U` | `hcpu_codex_alu.v` — `CRHO` 0x4C |
| **Mod-4** | `Θ̂ mod 4`, kuantum 90° = 360/4 | `hcpu_codex_alu.v` — `CMOD4` 0x4F |

**H\*** sendiri ada di [`teknologi/ISTILAH.md`](../teknologi/ISTILAH.md), dan
**ia yang paling mudah salah baca.** `890cf9d` mengukurnya: ia fungsi
indikator non-geometris, **bukan celah guard**. Dan hanya **Kaf** yang H\*-nya
1 — sifat yang membuat sabotase bisa menggigit, dan yang ketiadaannya sudah dua
kali membuat sabotase gagal menggigit (`f0dd0f8`, `b2a0595`).

---

## Guard — enam, dan tiga di antaranya definisional

Dibaca dari `rtl/hcpu_guard.v`, yang memikulnya di silikon:

```
G1:  A_N = Na + Nb + Nd
G2:  A_K = Kp + Kx + Ks + Ka + Kc
G3:  A_Q = Qp + Qx + Qs + Qa + Qc
G4:  ρ = Θ̂ − U ≥ 0        di mana U = Qx + Qs + Qa + 4×Qc
T1:  Ks > 0  ⇒  Qc ≥ 1
T2:  Kc > 0  ⇒  Qc ≥ 1
```

`matematika-hijaiyyah/GUARD.md` memisahkan jenisnya: **G1–G3 definisional** —
A_N *adalah* jumlahnya — sementara **G4 pertidaksamaan**, satu-satunya yang
bisa ditolak tanpa merusak definisi. **T1/T2 topologis**: garis yang menutup
menuntut sebuah kurva tertutup ada.

Halaman itu juga mencatat langit-langitnya: **93,1%**, bukan kekurangan.
Θ̂ terkunci di 11% oleh struktur monoid, H\* di 0% karena tak ada hukum yang
jujur untuknya.

---

## Lima operasi BAB II — Metrik-Vektorial

`cosmictera-build/README.md` menyingkatnya jadi satu baris — `L2
Metrik-Vektorial VTM · NMV · AGM · ITM · EXM` — dan tiap huruf punya modulnya.
**Tidak satu pun dari kelimanya ada di `teknologi/ISTILAH.md`.**

| | kepanjangan | pertanyaannya | modul | bab |
|---|---|---|---|---|
| **VTM** | Vektronometry | bagaimana huruf diukur sebagai vektor | `algebra/vektronometry.py` | II-A, hal 17–21 |
| **NMV** | Normvektor | apa yang membedakan dua huruf | `algebra/normvektor.py` | II-B, hal 22–24 |
| **AGM** | Aggregametric | bagaimana banyak huruf dijumlahkan | `algebra/aggregametric.py` | II-C, hal 25–28 |
| **ITM** | Intrametric | jarak di dalam satu huruf | `algebra/intrametric.py` | II-D, hal 29–31 |
| **EXM** | Exometric | jarak antar huruf | `algebra/exometric.py` | II-E, hal 32–36 |

> **Ejaannya `Normvektor`, bukan `Normvektor`.** Kode memakai bentuk pertama
> dua belas kali (`algebra/normvektor.py`, `cosmictera/CODEX.md`); `AGENTS.md`
> baris 101 memakai bentuk kedua satu kali. Kode sumbernya, prosa yang
> menyimpang — dan ini dicatat, bukan dirapikan sepihak.

---

## Master Table dan segelnya

| istilah | arti | di mana |
|---|---|---|
| **Master Table** | 28 huruf × 18 komponen, tersegel | `core/master_table.py` |
| **HM-28** | penandanya: `HM-28-v1.2-HC18D` | header tiap wrapper, `SECURITY.md` |
| **dataset seal** | hash kanonik tabel | `ARCHITECTURE.md` — `SEAL()` |
| **JUMMAL** | — **kepanjangan tidak tertulis di mana pun** | `src/hijaiyyah/core/` |

`matematika-hijaiyyah/GUARD.md` membalik cara membaca tabel itu: **Master Table
adalah delapan belas pengklasifikasi**, dan guard-nya **ruang nol abjad**.
Dimensinya yang sebenarnya **empat belas**, bukan delapan belas — tiga ringkasan
dan H\* tidak menambah kebebasan.

---

Dijangkarkan oleh `tests/test_integrity/test_bab_satu.py`,
`test_bab_dua.py`, dan `test_istilah.py`.
