# Matematika Hijaiyyah — SD / Ula (Ibtidaiyah)

Setingkat **Sekolah Dasar (SD)** atau **Madrasah Ibtidaiyah (MI)**; dalam
penjenjangan pesantren disebut **Ula**. Masa belajar umumnya **6 tahun**.

## Bahan ajar

| Berkas | Kelas | Isi | Slide |
|---|---|---|---|
| [`Kelas 4 - Nuqtah.html`](Kelas%204%20-%20Nuqtah.html) | 4 | Nuqṭah: titik terpisah dari badan, tiga zona (atas/tengah/bawah), menulisnya sebagai (Na, Nb, Nd) | 14 |
| [`Kelas 5 - Khatt dan Qaws.html`](Kelas%205%20-%20Khatt%20dan%20Qaws.html) | 5 | Khaṭṭ dan Qaws: garis vs lengkung, ujinya "apakah membelok", satu goresan satu nama, dihitung utuh | 16 |
| [`Kelas 6 - Al-Anasir.html`](Kelas%206%20-%20Al-Anasir.html) | 6 | Al-Anāṣir: ketiga unsur disatukan (A_N, A_K, A_Q), jumlah A, cara memeriksa hitungan sendiri, kelengkapan 28/28 | 16 |

Urutannya bertingkat: kelas 4 menghitung titik yang **terpisah** dari badan,
kelas 5 menghitung **badannya sendiri**, kelas 6 menyatukan keduanya lalu
menambahkan satu hal baru — **memeriksa hitungan sendiri**.

Bahasa kelas 6 sengaja lebih rinci daripada dua kelas sebelumnya: kalimatnya
lebih panjang, istilahnya disebut dengan nama Arabnya, dan tiap aturan diberi
alasan, bukan hanya bunyinya.

Presentasinya satu berkas HTML yang berdiri sendiri — buka langsung di
peramban, tidak perlu internet dan tidak perlu pemasangan apa pun. Navigasi
dengan tombol panah, spasi, atau tombol di bawah layar.

**Setiap bentuk huruf di dalamnya adalah gambar glyph KFGQPC tersegel**
(`data/kfgqpc/glyphs/`), ditanam sebagai data URI — bukan teks Arab Unicode.
Alasannya Canonical Lock (IE.1.6): teks Unicode dirender memakai font apa pun
yang kebetulan ada di komputer pembaca, dan font itu bukan KFGQPC. Kalau bentuk
hurufnya boleh berubah-ubah mengikuti mesin yang membukanya, seluruh dasar
pengukuran Matematika Hijaiyyah ikut hilang.

Angka-angkanya dihasilkan langsung dari `MASTER_TABLE`, bukan diketik ulang,
lalu diperiksa ulang terhadap tabel itu setelah berkasnya jadi.

### Catatan untuk guru

Slide "Satu badan, titik berbeda" hanya memakai **tiga** huruf — Ba, Ta, Tsa —
karena hanya ketiganya yang badannya benar-benar identik dalam data tersegel:
Θ̂=2, K=(0,1,0,0,0), Q=(1,0,0,0,0), dan cuma N yang berbeda.

**Nun sengaja tidak dimasukkan.** Buku (ID.1.5, hal 76) mendaftar ب ت ث ن dalam
satu kelompok, tetapi Master Table menunjukkan Nun punya K=(0,0,0,0,0) — tanpa
komponen Khaṭṭ sama sekali, sedangkan ketiga huruf lain punya Kx=1. Jadi Nun
mirip secara penglihatan, tidak identik secara ukuran. Versi pertama slide ini
memasukkan Nun dan salah; pemeriksaan terhadap Master Table yang menangkapnya.

## Usulan cakupan kelas 5–6 (belum ditetapkan)

Jenjang ini bisa berdiri sepenuhnya di atas **menghitung benda yang kelihatan**,
tanpa aljabar sama sekali. Yang tersedia dari buku:

| Dari buku | Isinya | Kenapa cocok untuk SD |
|---|---|---|
| IB.1.7, hal 51 | **Nuqṭah** — titik, dihitung per zona: atas (Na), tengah (Nb), bawah (Nd) | Murni membilang. ب = (0,0,1), ت = (2,0,0), ث = (3,0,0), ج = (0,1,0) |
| IB.1.9, hal 53 | **Khaṭṭ** — garis lurus | Membedakan lurus dan melengkung dengan mata |
| IB.1.10, hal 54 | **Qaws** — lengkung | Sama, sisi sebaliknya |
| IB.1.2, hal 50 | Tiga primitif itu **cukup dan lengkap** untuk 28 huruf | Bisa dibuktikan sendiri di kelas: cari huruf yang bukan titik/garis/lengkung — tidak ada |

Semuanya bilangan bulat tak-negatif, semuanya bisa dihitung dengan menunjuk
gambar hurufnya. Tidak perlu Θ̂, tidak perlu vektor, tidak perlu guard.

Satu fakta yang mungkin menarik untuk kelas: **ج satu-satunya huruf dengan
titik di zona tengah** (Nb=1) — dari 28 huruf, hanya satu.

## Yang harus tidak dilakukan

Jangan mengarang nilai untuk memudahkan contoh. Angka SD di sini adalah angka
yang sama persis dengan yang dipakai HCPU di silikon; sumbernya Master Table,
hal 79.
