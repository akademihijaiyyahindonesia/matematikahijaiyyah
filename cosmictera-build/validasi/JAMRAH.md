# Validasi Jamrah — Tang Nano 20K

**20 September 2026.** Laporan validasi pertama dari kerangka laboratorium
pemilik (`AGENTS.md`, keputusan 18 dan 20 September): tiap modul membuktikan
dirinya di papan sebelum dianggap siap untuk KV260.

## Apa yang divalidasi

Jamrah di repositori ini adalah **gerbang**, bukan detektor statistik: pohon
reduksi 8-daun dengan tujuh simpul dalam, bagian Lapis 1 Guard Ka'bah. Ia
menolak masukan malformed dalam O(1), tanpa kunci. Satu byte masuk, dan dua hal
keluar: apakah byte itu menamai huruf (1..28), dan ketujuh simpul pohonnya —
akarnya adalah popcount.

Masukannya satu byte, jadi **ruang masukannya 256 nilai**. Ia diuji tuntas,
bukan diambil sampelnya: hasilnya 256 dari 256, atau sebuah cacat.

**Ia triase, bukan otoritas.** Tanpa kunci, siapa pun bisa membangun byte yang
lolos. Validasi ini membuktikan gerbang menghitung apa yang ia klaim hitung —
bukan bahwa ia menahan penyerang.

## Hasil

| bentuk | di mana | tingkat bukti | hasil |
|---|---|---|---|
| acuan | `rtl/tb/jamrah_vectors.txt`, 256 baris | definisi | 28 byte lolos, 228 ditolak; n6 = popcount di ke-256 baris |
| RTL `rtl/hijaiyyah_jamrah_gate.v` | simulasi, `rtl/tb/tb_hijaiyyah_jamrah_gate.v` | 2 — tersimulasi | **256/256**, pulse dan ketujuh simpul |
| RTL di slot Ka'bah papan | sintesis ulang dari sumber, 20 September | 3 — tersintesis | **tidak ada di silikon** — lihat di bawah |
| HASM `rtl/programs/jamrah_gate.hasm` | interpreter | 2 — tersimulasi | **256/256**, 33,02 instruksi per byte |
| HASM di papan | Tang Nano 20K, slot CPU | **4 — berjalan** | **256/256, lima lari dari lima**, pulse dan ketujuh simpul |

**Deteksi.** Di papan, lima lari berturut-turut: 256/256 setiap kali. Tidak ada
false positive (byte di luar 1..28 yang lolos) dan tidak ada false negative
(huruf yang ditolak) — dan untuk predikat eksak itu satu-satunya jawaban yang
bukan cacat.

**Waktu, di papan.** Satu lintasan 256 byte tanpa pencetakan, diapit dua
bacaan pencacah bebas 0xFF4: **9.218 clock, identik di kelima lari** —
**36,01 clock per byte**, sudah termasuk empat instruksi gelung (`MOV`, `ADDI`,
`CMPI`, `JNE`). Pada 27 MHz itu ±750 ribu byte per detik untuk bentuk
programnya. Di interpreter lintasan yang sama 33,02 **instruksi** per byte;
selisihnya biaya pipeline, dan kedua angka tidak dibandingkan sebagai satuan
yang sama.

**Tiap byte sendiri-sendiri, 20 September 2026.** Angka di atas satu angka
untuk seluruh lintasan; yang tidak dijawabnya adalah apakah byte yang berbeda
memakai waktu yang berbeda. [Lab serangan kelas A](../attack-lab/README.md)
mengukurnya: **33 clock untuk setiap satu dari 256 byte**, satu nilai saja,
identik byte demi byte di lima lari — jendelanya badan gerbang ditambah dua
instruksi tetap, bukan empat instruksi gelung yang ikut di angka 36,01.

**Biaya.** Bentuk program: nol LUT, 29 kata instruksi untuk badan gerbangnya.
Bentuk RTL, disintesis sendirian (`synth_gowin`): 12 LUT (1 LUT1, 8 LUT2,
1 LUT3, 2 LUT4), 1 MUX2_LUT5, 16 ALU, 19 DFF; keluarannya teregister, jadi
secara desain satu byte per clock dengan latensi satu clock — **belum pernah
diukur di papan**.

## Temuan: gerbang RTL tidak ada di papan

Di wrapper slot Ka'bah, `rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v`, keluaran
gerbang dibiarkan tak tersambung (`.gate_pulse ()`), dan `gate_mode` adalah
parameter waktu-sintesis yang bernilai 0. Disintesis ulang dari sumber pada
20 September, satu-satunya jejak `u_gate` di netlist slot itu adalah sel
`$scopeinfo` **tanpa satu sambungan pun** — penanda hierarki yang tertinggal
sesudah seluruh logikanya dibuang karena tak terpakai. Pemeriksaan
penggantinya di `rtl/hijaiyyah_kabah_top.v`, `gate_pulse_now`, ikut terlipat,
karena dengan `gate_mode` 0 setiap byte diterima.

Jadi 256/256 untuk bentuk RTL adalah hasil **simulasi**, dan di papan ini
Jamrah yang berjalan hanyalah bentuk programnya. Menghadirkan gerbang RTL di
silikon menuntut wrapper yang menyambungkan keluarannya — perubahan RTL,
keputusan pemilik.

## Satu kejadian yang dicatat, sebabnya belum terbukti

Lari pertama di papan kehilangan **baris pertamanya** — kata pengukur waktu —
sehingga setiap kelompok sesudahnya bergeser satu nilai dan hasilnya terbaca
0/256. Tangkapan mentah lari berikutnya bersih, dan data papan tergeser utuh,
jadi yang gagal adalah pengurai host, bukan papan. Sebab hilangnya baris itu
tidak terbukti. Pengurai kini membuang byte tak-tercetak sambil menghitungnya,
melaporkan setiap baris yang bukan angka, dan menyimpan tangkapan mentah; lima
lari sesudahnya tidak mengulanginya.

## Mengulanginya

```bash
python3 rtl/scripts/jamrah_board.py                                  # interpreter
make -C rtl/fpga/gowin bridge                                        # loader di papan
python3 rtl/scripts/jamrah_board.py /dev/tty.usbserial-<port>        # papan
python3 -m pytest -q tests/test_integrity/test_jamrah_board.py       # lab-nya sendiri
```

Program yang dikirim ke papan **dibangkitkan** dari `jamrah_gate.hasm`, tidak
diketik ulang: badan gerbangnya disalin kata demi kata ke dalam gelung.
`tests/test_integrity/test_jamrah_board.py` menjaganya, termasuk sabotase yang
harus merah — satu simpul tingkat dua dihitung dengan `SUB`, bukan `ADD`.
