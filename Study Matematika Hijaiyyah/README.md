# Study Matematika Hijaiyyah

Bahan ajar Matematika Hijaiyyah untuk tiga jenjang sekolah. Sumbernya satu dan
sama dengan seluruh repositori ini: buku *Matematika Hijaiyyah* Edisi v.1.1.1
(`Buku Matematika Hijaiyyah/`) dan Master Table tersegel HM-28 yang diturunkan
darinya — bukan penyederhanaan yang mengarang angka sendiri.

Penamaannya memakai dua sistem sekaligus — jenjang nasional dan jenjang pondok
pesantren — karena bahan yang sama dipakai keduanya:

| Folder | Jenjang nasional | Jenjang pesantren | Madrasah | Masa belajar |
|---|---|---|---|---|
| [`… SD - Ula Ibtidaiyah/`](Matematika%20Hijaiyyah%20SD%20-%20Ula%20Ibtidaiyah/) | Sekolah Dasar (SD) | **Ula** | Madrasah Ibtidaiyah (MI) | umumnya 6 tahun |
| [`… SMP - Wustha Tsanawiyah/`](Matematika%20Hijaiyyah%20SMP%20-%20Wustha%20Tsanawiyah/) | Sekolah Menengah Pertama (SMP) | **Wustha** | Madrasah Tsanawiyah (MTs) | 3 tahun |
| [`… SMA - Ulya Aliyah/`](Matematika%20Hijaiyyah%20SMA%20-%20Ulya%20Aliyah/) | Sekolah Menengah Atas (SMA) | **Ulya** | Madrasah Aliyah (MA) | 3 tahun |

Ula (أُولَى) — Wustha (وُسْطَى) — Ulya (عُلْيَا): pertama, tengah, atas. Tiga
tingkat yang dipakai pendidikan diniyah/salafiyah, sejajar dengan SD–SMP–SMA.

## Keadaan sekarang

**Ketiganya masih kosong.** Belum ada satu pun bahan ajar di dalamnya — folder
ini baru kerangkanya. README di tiap jenjang mencatat materi mana dari buku
yang jatuh ke jenjang itu, sebagai titik awal yang masih bisa diubah, bukan
kurikulum yang sudah ditetapkan.

## Aturan yang tetap berlaku di sini

Bahan ajar boleh menyederhanakan bahasa; ia tidak boleh menyederhanakan angka.
Setiap nilai yang muncul di jenjang mana pun harus nilai yang sama dengan yang
dipakai kode dan RTL — Master Table adalah sumbernya, dan
`tests/test_integrity/test_dataset_consistency.py` memaku setiap salinannya.
Satu angka yang "dibulatkan supaya mudah" akan membuat murid dan silikon
menjalankan alfabet yang berbeda, dan itu persis kesalahan yang pernah terjadi
di repositori ini pada empat huruf (ط ظ ك ن).
