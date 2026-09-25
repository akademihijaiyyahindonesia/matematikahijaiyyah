# Lab serangan — catatan per lari

**Prioritas 5 pemilik, dibuka 20 September 2026**, sesudah ketiga lapisan punya
laporan validasi: [Jamrah](../validasi/JAMRAH.md) 256/256,
[Hijrah](../validasi/HIJRAH.md) sama dengan Python, [Ka'bah](../validasi/KABAH.md)
avalanche 0,4995. Alasan urutannya kalimat pemilik sendiri: *"lab serangan tanpa
baseline validasi akan menghasilkan angka yang sulit ditafsirkan."*

**Apa lab ini bukan.** Bukan klaim keamanan dan bukan bukti ketahanan. Ia
kumpulan masukan yang **seharusnya ditolak**, dijalankan ke mesin untuk melihat
apakah ditolak. Kasus yang diterima adalah temuan; kasus yang ditolak adalah
satu kasus, bukan jaminan.

Tiap lari menyimpan satu berkas JSON di folder ini: `attack_id`, sasaran,
jumlah masukan, jumlah ditolak, jumlah diterima, temuan, papan, frekuensi
clock, bitstream, dan tiap kasus dengan prediksinya. Field yang tidak berlaku
untuk sebuah sasaran dikatakan tidak berlaku, bukan dikosongkan: spons tidak
punya "jumlah ditolak" karena ia menyerap, tidak menolak.

## Pembangkitnya: mesin Jim, bukan RNG

`rtl/scripts/jim_stream.py` memakai satu-satunya hal yang terukur tentang huruf
Jim: mukanya sebagai peta linier adalah **LFSR panjang-maksimum**. Periodenya
diukur ulang oleh alat itu sendiri dan cocok dengan `cosmic-codex-jim/`:

```
GF(2)   periode keadaan    31   → periode byte    155
GF(5)   periode keadaan 3.124   → periode byte  3.124
```

`cosmic-codex-jim/LIMITS.md` mencatat tiga bacaan tentang Jim yang **gagal
terukur**, dan lab ini tidak memakai satu pun darinya. Jim dipakai sebagai
pembangkit urutan deterministik berperiode diketahui — tidak diklaim lebih baik
dari RNG.

`JimSource` di `rtl/scripts/attack_lab.py` memberi aliran itu permukaan
`random.Random`, sehingga kelas yang sama bisa dijalankan dua kali: sekali
dengan RNG, sekali dengan aliran codex, dan hasilnya dibandingkan. Itu kelas D.

## Kelas A — latensi gerbang Jamrah

Cakupannya sudah tuntas di [laporan Jamrah](../validasi/JAMRAH.md): 256 dari
256, lima lari. Yang tersisa **waktu**, dan `rtl/programs/jamrah_gate.hasm`
membuat klaim tentangnya di komentarnya sendiri: gerbang yang bercabang atas
masukannya memakai jumlah siklus berbeda untuk byte berbeda, *"dan itu kanal
waktu pada pemeriksaan yang justru dimaksudkan murah dan seragam."*

`20260920T000027Z-jamrah.json`. Tiap byte diukur sendiri, di antara dua bacaan
pencacah bebas 0xFF4:

| | hasil di papan |
|---|---|
| gerbang, 5 lari × 256 byte | **33 clock, satu-satunya nilai** — identik byte demi byte di kelima lari |
| pulse tiap lari | 28 lolos, 228 ditolak, 0 selisih dengan `jamrah_vectors.txt` |
| kontrol: predikat sama, ditulis sebagai gelung banding | **29 nilai berbeda, 13 sampai 232 clock** |

**Kontrolnya wajib, bukan hiasan** (R3). Bacaan konstan dari gerbang tidak
membuktikan apa-apa kalau alat ukurnya memang tidak bisa melihat perbedaan.
Kontrol itu milik lab ini, dibangkitkan di `attack_lab.py`, dan **bukan varian
gerbang yang dipakai proyek** — `jamrah_gate.hasm` tidak disentuh.

**Batasnya.** Yang diukur jumlah clock dari bentuk **program**-nya, di jendela
yang berisi badan gerbang ditambah dua instruksi tetap yang sama untuk setiap
byte. Bukan daya, bukan emisi, dan bukan gerbang RTL — yang terakhir memang
tidak ada di silikon papan ini (lihat laporan Jamrah). Jendela ini juga berbeda
dari 36,01 clock per byte di laporan itu: yang di sana memuat empat instruksi
gelung, yang di sini dua.

## Kelas B — loader

### Versi 2, CHECKSUM32 — P6, 26 September 2026

`20260925T191528Z-loader.json`. Loader yang menghitung CHECKSUM32 (K-8, K-10)
dikirim lewat kabel ke bitstream yang sama; tiap kasus ditulis ke kartu lewat
`sd_writer`, lalu papan diminta memuatnya. Vonis yang diharapkan tiap kasus
**tidak ditulis tangan**: ia vonis loader Python di
`rtl/scripts/build_container.py` atas kartu yang sama, dan
`tests/test_integrity/test_checksum32.py` memberikan kartu yang sama itu, bit
demi bit, ke loader HCPU tersimulasi — ketiganya harus sepakat.

| kategori pemilik | kasus | papan |
|---|---|---|
| header | `words_plus_one`, `load_addr_minus_one`, `entry_plus_one` — hanya CHECKSUM32 yang bisa melihatnya | **ditolak, 3** |
| header, pemeriksaan nilai | MAGIC, `version_one`, WORDS = 0, LOAD_ADDR melewati IMEM, ENTRY di luar citra, RELOC_CNT > 128 | **ditolak, 6** |
| tabel program | `table_flags_bit_one`, `table_sector_count` | **ditolak, 2** |
| tabel relokasi | `reloc_index_moved` | **ditolak** |
| badan program | `program_word_flip` | **ditolak** |
| medan checksum | `checksum_flip`, `checksum_by_version_one_rule` | **ditolak, 2** |
| di luar container | `words_after_container` | **diterima** |
| di luar container | `another_table_entry`, `another_sector` | Python dan simulasi saja — `sd_writer` menulis satu entri dan sektor container sendiri |
| kontrol | `intact` | **diterima** |
| batas sebuah jumlah | `words_swapped`, `body_changed_and_resealed` | **diterima, 2** |

**19 kasus di papan, 0 temuan**: 15 ditolak, 4 diterima, dan tiap satu
sesuai vonis loader Python. **Dua kasus yang lolos di versi 1 kini ditolak** —
`words_plus_one` dan `reloc_index_moved`, alasan K-8 ada.

**Kasus tabel program ditulis lewat `sd_writer`** dengan cara yang bisa ia
tulis: container disegel untuk entri yang berbeda — FLAGS 3, atau satu sektor
lebih — sementara `sd_writer` menulis entri `1, 1, 17, n`. Bagi loader itu
sama persis dengan entri yang dirusak sesudah disegel: entri di kartu bukan
entri yang tertutup jumlahnya.

**Batas sebuah jumlah, dan ini bukan cacat implementasi.** CHECKSUM32 adalah
jumlah yang bisa dihitung siapa pun dan tidak melihat urutan. Dua kata program
yang ditukar tempatnya lolos, dan badan program yang diubah lalu disegel ulang
lolos. Keduanya sifat algoritma yang dipilih K-10, dicatat supaya "penyerang
tidak cukup hanya mengubah body" tidak tumbuh jadi klaim bahwa pengubah yang
menghitung ulang jumlahnya tertahan.

**Satu lari gagal sebelum kasus pertama**, dan tidak menulis rekaman:
`sd_writer` tidak mengirim tanda siap dalam lima detik. Itu cocok dengan
cacat yang sudah tercatat di `cosmictera-build/OFF.md` — kartu gagal init
pada lari sesudah papan direkonfigurasi di tengah pembacaan, dan lari
berikutnya sehat. Lari ulang tanpa perubahan apa pun adalah rekaman di atas.

### Versi 1 — 20 September 2026

`20260919T225037Z-loader.json`. Container `test_from_card` @0x900 dibangun
utuh, lalu satu field dirusak per kasus, ditulis ke kartu lewat `sd_writer`,
dan papan diminta memuatnya.

| hasil | kasus |
|---|---|
| **ditolak, 8** | MAGIC dibalik, VERSION dinaikkan, WORDS = 0, LOAD_ADDR melewati memori instruksi, ENTRY di luar citra, RELOC_CNT > 128, CRC dibalik, satu kata program dibalik |
| **diterima, 2** | `words_plus_one`, `reloc_index_moved` |

**Keduanya diterima bukan karena cacat, melainkan karena memang di luar
jangkauan pemeriksaan yang ada** — dan itulah yang lab ini ada untuk
menunjukkan:

- **`words_plus_one`.** WORDS dinaikkan satu, jadi loader menjumlahkan satu
  kata tambahan dari kartu. Kata itu **nol**, padding sektor, sehingga jumlah
  32-bit tidak berubah dan citra dimuat satu kata lebih panjang.
- **`reloc_index_moved`.** Satu entri tabel relokasi diarahkan ke kata program
  lain. **Jumlah 32-bit hanya menutupi kata program** — keputusan pemilik,
  18 September — jadi tabel yang rusak lolos, dan citra direlokasi di kata yang
  salah tanpa satu pun penolakan.

Keduanya konsisten dengan spesifikasi yang berlaku hari lab dijalankan.
Pemilik memutuskan cakupannya diperluas ke seluruh container, 22 September 2026
(K-8, tabel di bawah), dan versi 2 di atas menolak keduanya.

### Tabel keputusan cakupan checksum

Disiapkan 22 September 2026 atas permintaan pemilik: *"Belum perlu mengubah
implementasi. Buat saja tabel keputusan."* Kolom "dilindungi?" diisi pemilik
pada hari yang sama, **keputusan K-8**: checksum adalah integritas container
secara keseluruhan, bukan hanya badan program, *"supaya penyerang tidak cukup
hanya mengubah body"*. Kolom "versi 1" adalah loader sebelum P6; kolom "versi
2" dibaca dari `rtl/programs/hos_prog_load.hasm` sesudah P6, 26 September 2026,
dan kasusnya dijalankan di papan.

| bagian | versi 1 | versi 2, CHECKSUM32 | dilindungi? |
|---|---|---|---|
| kata program | dijumlah 32-bit | dijumlah — `program_word_flip` ditolak | **ya** |
| header: MAGIC, VERSION, RELOC_CNT | tidak dijumlah; pemeriksaan nilai | dijumlah, dan pemeriksaan nilainya tetap | **ya** |
| header: WORDS | tidak dijumlah; `words_plus_one` **diterima** | dijumlah — `words_plus_one` ditolak | **ya** |
| header: LOAD_ADDR dan ENTRY | tidak dijumlah; pemeriksaan rentang | dijumlah — `load_addr_minus_one`, `entry_plus_one` ditolak | **ya** |
| header: medan checksum sendiri | medan pembanding | **dinolkan saat menghitung** — `checksum_flip`, `checksum_by_version_one_rule` ditolak | **dinolkan saat menghitung** |
| tabel relokasi | tidak dijumlah; `reloc_index_moved` **diterima** | dijumlah — `reloc_index_moved` ditolak | **ya** |
| tabel program, sektor 16: entri program, termasuk FLAGS | tidak dijumlah | dijumlah, keempat kata entri — `table_flags_bit_one`, `table_sector_count` ditolak | **ya** |
| data di luar container dan entrinya | tidak dibaca loader | tidak dijumlah — `words_after_container` diterima di papan; `another_table_entry`, `another_sector` di Python dan simulasi | **tidak** |

"Payload" dan "program body" satu baris di tabel pemilik K-8, sama seperti di
container ini — tujuh kata header, tabel relokasi, lalu kata program.

**Algoritmanya dijawab pemilik 23 September 2026, keputusan K-10: jumlah
32-bit, bukan CRC-32.** `CRC(...)` pada uraian K-8 adalah istilah yang keliru
dan diperjelas jadi:

```
CHECKSUM32 = Σ canonical_container_words mod 2^32

           canonical_container_words =
               rekaman program sektor 16
             + header dengan medan CHECKSUM = 0
             + tabel relokasi
             + badan program

           data di luar container tidak ikut
```

Jadi keputusan 18 September tetap berlaku: tidak ada tabel CRC-32 256 entri,
dan arena heap 127 kata tidak perlu diperbesar. Karena jumlah tidak bergantung
urutan, yang dijaga bukan urutannya melainkan **satu cara menghitung**:
kata-kata yang dijumlah adalah representasi word container **sebagaimana ia
tersimpan di kartu**, format on-disk yang sudah ada, supaya tidak ada dua
perhitungan checksum untuk citra yang sama.

**Diterapkan di P6, 26 September 2026**, sesudah burn-in tutup: nama `CRC`
diganti `CHECKSUM32` di `rtl/programs/hos_prog_load.hasm` dan
`rtl/scripts/build_container.py`, cakupannya diperluas, dan `VERSION` naik ke
2 — loader versi 2 menolak container versi 1 lewat pemeriksaan VERSION, bukan
dengan salah membacanya. **Urutan kanonik ditetapkan dan diuji sebelum
implementasi dianggap final**, syarat pemilik: satu kata adalah 32 bit tak
bertanda, byte paling signifikan lebih dulu — cara `rtl/hcpu_sdio.v` mengisi
penyangganya dan cara `send_program.py` mengirimnya. Kasus sabotasenya ada
untuk keenam kategori pemilik, di papan dan di simulasi, di atas.

## Kelas C — Ka'bah, di luar bit tunggal

`20260919T233812Z-kabah.json` (8 percobaan per lebar, benih 20260921);
`20260919T233459Z-kabah.json` adalah lari pertama dengan 4 percobaan dan benih
20260920. Garis dasarnya avalanche **0,4995** dari laporan Ka'bah, yang diukur
atas bit tunggal saja.

| lebar mutasi | rata-rata dari 1.600 bit |
|---:|---|
| 1 bit | **0,4984** |
| 2 bit | 0,5035 |
| 4 bit | 0,5006 |
| 8 bit | 0,4984 |
| 16 bit | 0,5011 |
| 32 bit | 0,5016 |
| 64 bit | 0,5061 |

Menambah bit yang dibalik **tidak menggeser difusinya**: dari satu bit sampai
64 bit angkanya tetap di sekitar setengah. Integritas tidak pernah goyah —
0 kegagalan dari 56 pasang; setiap keadaan masih sama dengan `cube.py`.

| serangan | hasil |
|---|---|
| **permutasi blok**, 4 frame diacak urutannya | keadaan akhir **berbeda**, 0,4975 dari keadaan berubah, kedua lari tetap cocok `cube.py` |
| **frame terpotong**, 64 byte lalu 64 byte | potongan pendek **tidak menarik balasan sama sekali**; penyelesaiannya menjawab 200 byte, dan itu `cube.py` dari **sambungan** kedua potongan |
| **frame diulang**, satu frame 4 kali | 4/4 cocok `cube.py`, 4/4 keadaan berbeda — spons berantai |

**Frame terpotong adalah pernyataan tentang protokol, bukan tentang spons.**
Wrapper menyerap 128 byte tetap dan **tidak punya field panjang**, jadi tidak
ada yang bisa ditolaknya: byte yang datang kemudian — dari siapa pun —
menyelesaikan frame yang menggantung, dan seluruh frame sesudahnya bergeser.
Penolakan replay dan pembingkaian memang bukan milik lapis ini; keduanya ada di
`guarded_record.py`, lapis 5, dan tetap perangkat lunak.

## Kelas D — aliran codex sebagai sumber kasus

Pertanyaannya satu: **apakah sapuan terstruktur menemukan yang tidak ditemukan
acak?** Kelas B dan C dijalankan ulang dengan `JimSource` GF(5) menggantikan
RNG-nya.

| lari | hasil |
|---|---|
| `20260919T234551Z-loader-jim5.json` — 16 kata program dirusak, nilainya dari aliran | **16/16 ditolak.** Target pemilik untuk kategori yang memang harus ditolak adalah 100%, dan ini 100% |
| `20260919T234814Z-kabah-jim5.json` — kelas C seluruhnya, masukan dari aliran | 1 bit **0,5046**; 2–64 bit antara 0,4953 dan 0,5055; permutasi 0,5056; terpotong dan diulang **berperilaku sama persis** |

**Jawabannya, untuk pengukuran ini: tidak.** Aliran codex tidak menemukan satu
pun hal yang tidak ditemukan sumber acak — angkanya bertumpuk di tempat yang
sama. Itu satu perbandingan pada ukuran ini, bukan pernyataan umum tentang
pembangkit terstruktur, dan justru karena itu ia dicatat: kalau nanti ada lari
yang menemukan beda, ada angka untuk membandingkannya.

**Kelas D tidak dijalankan atas Jamrah** — dan itu bukan utang. Ruang masukan
gerbang 256 nilai dan kelas A sudah melewati semuanya; aliran apa pun hanya
bisa menghasilkan bagian dari yang sudah dilewati.

## Mengulanginya

```bash
python3 rtl/scripts/attack_lab.py --target loader                    # rencananya saja
python3 rtl/scripts/attack_lab.py --target jamrah --runs 5 --port /dev/tty.usbserial-<port>
python3 rtl/scripts/attack_lab.py --target loader --port /dev/tty.usbserial-<port>
python3 rtl/scripts/attack_lab.py --target kabah --trials 8 --port /dev/tty.usbserial-<port>
python3 rtl/scripts/attack_lab.py --target loader --source jim5 --cases 16 --port /dev/tty.usbserial-<port>
python3 rtl/scripts/attack_lab.py --target kabah --source jim5 --trials 8 --port /dev/tty.usbserial-<port>
python3 rtl/scripts/jim_stream.py --field 5 --bytes 32
python3 -m pytest -q tests/test_integrity/test_attack_lab.py
```

Sasaran `loader` dan `jamrah` memakai slot CPU (`hcpu_gowin_top_loader.fs`),
sasaran `kabah` memakai slotnya sendiri; alat memilihkannya. Sepuluh kasus
loader ±1 menit 17 detik, lima sapuan Jamrah 31,7 detik, kelas Ka'bah delapan
percobaan per lebar ±5 menit 13 detik — tiap percobaan Ka'bah memuat bitstream
dua kali.

## Batas yang tetap berlaku sesudah keempat kelas

Keempat kelas menyerang **apa yang berjalan di atas** HCPU: gerbang, loader,
dan spons. Tidak satu pun menyerang HCPU sendiri — proteksi memorinya, jendela
supervisor 0xFF0+, batas `mem_base`/`mem_limit`. `AGENTS.md` mencatat bahwa
belum ada satu pun lari seperti itu, dan lab ini tidak mengubahnya; angka di
halaman ini karena itu tidak boleh dibaca sebagai pernyataan tentang CPU-nya.

Empat kelas ini juga mengukur **jawaban**, bukan daya, waktu di luar jumlah
clock, atau emisi.
