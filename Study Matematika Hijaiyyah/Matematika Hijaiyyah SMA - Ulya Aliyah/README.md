# Matematika Hijaiyyah — SMA / Ulya (Aliyah)

Setingkat **Sekolah Menengah Atas (SMA)** atau **Madrasah Aliyah (MA)**; dalam
penjenjangan pesantren disebut **Ulya** (عُلْيَا — "atas"). Masa belajar 3 tahun.

**Kosong.** Belum ada bahan ajar di folder ini.

## Usulan cakupan (belum ditetapkan)

Jenjang ini bisa memakai **vektor, ruang, dan jarak** — yaitu Bab II hampir
seutuhnya, ditambah satu teorema dari Bab I.

| Dari buku | Isinya | Kenapa cocok untuk SMA |
|---|---|---|
| ID.1.1–1.4, hal 74–75 | **Codex 14D dan 18D** — huruf sebagai vektor | Vektor dengan komponen bermakna, bukan angka abstrak |
| IIA.2.4, hal 90 | **Empat subruang ortogonal** Θ̂(1) ⊕ N(3) ⊕ K(5) ⊕ Q(5) = 14 | Ortogonalitas yang bisa dilihat sebabnya: indeksnya disjoint karena objeknya memang beda jenis |
| IIA.2.19–2.20, hal 95 | Norma dan **Pythagoras** `‖v‖² = ‖Θ̂‖² + ‖N‖² + ‖K‖² + ‖Q‖²` | Pythagoras di dimensi 14, suku silangnya nol karena ortogonal |
| IID.2.1–2.2, hal 103 | **Tiga jarak** (Euclid, Manhattan, Hamming) dan aksioma ruang metrik M1–M4 | Ruang metrik konkret dengan 28 titik |
| IIB.2.3, hal 98 | Dekomposisi selisih **per lapisan** | Bukan cuma "dua huruf ini beda 5", tapi "bedanya 100% di titik" |
| IIC.2.2, hal 101 | **Invarian anagram**: `Cod(ab) = Cod(ba)` | Fungsi multiset — dan kenapa urutan butuh mekanisme terpisah |
| IC.1.26–1.27, hal 72–73 | **Teorema Mod-4** dari Umlaufsatz (Hopf, 1935) | Lintasan tertutup ⟹ Θ̂ ≡ 0 (mod 4). Kontrapositifnya jadi tes O(1) |

## Tiga fakta yang layak jadi bahan diskusi

1. **Alif ortogonal terhadap seluruh alfabet** (IID.2.5, hal 104). Ia satu-satunya
   huruf dengan Kp>0, jadi ⟨ا,h⟩ = 0 untuk setiap huruf lain — ia menempati
   dimensi yang tidak dihuni siapa pun. Dan ia satu ujung diameter alfabet
   (ا↔ه = 70), ujung lainnya huruf paling kompleks.
2. **Huruf yang beda hanya titiknya, bedanya seluruhnya di subruang N** — 9 dari
   9 pasangan (IIA.2.6). Itu temuan tentang bagaimana aksara ini dibangun, bukan
   akibat definisi.
3. **Satu kalimat di buku yang terlalu jauh.** ID.1.1 menulis "penghapusan satu
   dimensi menyebabkan collision." Diukur: menjatuhkan salah satu dari 10
   komponen K/Q **tetap** menyisakan 28 huruf yang bisa dibedakan; hanya empat
   dimensi (Θ̂, Na, Nb, Nd) yang benar-benar menimbulkan collision. Independensi
   linier bukan injektivitas — dan ini contoh bagus bahwa buku pun harus diperiksa
   ([`tests/test_integrity/test_bab_satu.py`](../../tests/test_integrity/test_bab_satu.py)).

Nomor 3 itu bahan pelajaran terbaik di folder ini: cara memeriksa klaim, bukan
menghafalnya.
