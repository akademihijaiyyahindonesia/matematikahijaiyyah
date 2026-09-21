# Lapisan semantik -- USR, katalog Lapis 5, kamus HC, registry Hijaiyyah

Ditarik dari `NUI/spec/*.json`, `NUI/hijaiyyah_registry.json`, dan dari pengukuran oleh `src/hijaiyyah/nui/usr.py`. Status `ditetapkan` milik pemilik; `usulan` menunggu pengesahan pemilik. Tidak ada perintah host yang dijalankan; contoh HC dijalankan di interpreter HISA, di dalam proses.

## USR

| name | required | status | source |
|---|---|---|---|
| `ACTION` | True (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `OBJECT` | True (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `TARGET` | False (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `CONTEXT` | False (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `STATE` | False (usulan) | ditetapkan | pemilik, 21 September 2026 |

Huruf: Kunci medan huruf besar: ACTION, OBJECT, TARGET, CONTEXT, STATE. Nilai ACTION dan OBJECT huruf besar; nilai CONTEXT ditulis seperti pemilik menulisnya (`Ubuntu`, `HC`); nilai STATE huruf kecil (ditetapkan; pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- {"ACTION": "READ", "OBJECT": "FILE", "TARGET": "/etc/hosts", "CONTEXT": "Ubuntu", "STATE": "requested"}. Bergeser dua kali, dan yang berlaku yang terakhir: 21 September semuanya huruf kecil ({"action": "read", "object": "file"}); pesan sebelumnya pada 22 September kuncinya huruf kecil, nilai ACTION/OBJECT huruf besar, dan CONTEXT `ubuntu_host`).

### ACTION

| name | stage | status | source |
|---|---|---|---|
| `READ` | 1 | ditetapkan | pemilik, 22 September 2026 -- satu-satunya aksi tahap pertama: Lapis 5 hanya baca |
| `WRITE` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- target awal Lapis 5: write file |
| `COPY` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- copy file |
| `MOVE` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- move file |
| `DELETE` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- delete file |
| `KILL` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- kill |
| `START` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- systemctl start |
| `STOP` | -- | dinyatakan, belum diizinkan | pemilik, 21 September 2026 -- systemctl stop |
| `PRINT` | -- | ditetapkan | pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- contoh {ACTION PRINT, OBJECT VALUE, TARGET angka + harga, CONTEXT HC, STATE compiled}. Aksi di konteks HC, bukan perintah host, jadi tidak punya tahap Lapis 5 |

### OBJECT

| name | target | status | source |
|---|---|---|---|
| `FILE` | path, wajib (ditetapkan) | ditetapkan | pemilik, 22 September 2026 |
| `PROCESS` | none (usulan) | ditetapkan | pemilik, 22 September 2026 -- katalog: READ PROCESS |
| `SERVICE` | unit (usulan) | ditetapkan | pemilik, 22 September 2026 -- katalog: READ SERVICE |
| `NETWORK` | none (usulan) | ditetapkan | pemilik, 22 September 2026 -- katalog: READ NETWORK |
| `JOURNAL` | unit (usulan) | ditetapkan | pemilik, 22 September 2026 -- katalog: READ JOURNAL |
| `CONTAINER` | none (usulan) | usulan | wilayah Lapis 5 'Container' (pemilik, 21 September 2026) dan `docker ps` di daftar izin; belum ada OBJECT untuknya |
| `DIRECTORY` | path, wajib (usulan) | usulan | `ls` di daftar izin; FILE dengan `cat` tidak bisa membaca direktori |
| `VALUE` | ekspresi HC, wajib (usulan) | ditetapkan | pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- contoh PRINT VALUE |

### TARGET

| rule | applies_to | status | source |
|---|---|---|---|
| TARGET adalah satu string, diteruskan sebagai SATU elemen argv -- tidak pernah lewat shell, jadi ; | & $ ` tidak punya arti apa pun | CONTEXT Ubuntu, dan USR tanpa CONTEXT (usulan) | usulan | keamanan: perintah host dibentuk sebagai daftar argumen |
| TARGET tidak boleh diawali '-': ia akan dibaca perintah sebagai opsi, bukan sebagai nama | CONTEXT Ubuntu, dan USR tanpa CONTEXT (usulan) | usulan | keamanan |
| TARGET tidak boleh memuat baris baru atau karakter NUL | CONTEXT Ubuntu, dan USR tanpa CONTEXT (usulan) | usulan | keamanan |

### CONTEXT dan STATE

| name | status | source |
|---|---|---|
| `Ubuntu` | ditetapkan | pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- menggantikan `ubuntu_host` dari pesan sebelumnya pada 22 September: satu nama untuk satu hal, dan yang berlaku yang terakhir |
| `HC` | ditetapkan | pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- contoh PRINT VALUE |
| `latest` | contoh pemilik; artinya belum ditetapkan | pemilik, 22 September 2026, pesan sebelumnya -- contoh READ FILE /var/log/syslog |
| `requested` | contoh pemilik; artinya belum ditetapkan | pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- contoh READ FILE /etc/hosts |
| `compiled` | contoh pemilik; artinya belum ditetapkan | pemilik, 22 September 2026, pesan 'sambil menunggu burn-in' -- contoh PRINT VALUE |

**Arti STATE, usulan pemilik, belum dikunci.** STATE adalah keadaan aktual target/objek pada saat aksi dinyatakan, bukan tahap pipeline. `requested` dan `compiled` lebih mirip status proses/perintah; `compiled` lebih tepat metadata eksekusi/compiler, bukan STATE semantik. Contoh: `{"ACTION": "READ", "OBJECT": "FILE", "TARGET": "/etc/hosts", "CONTEXT": "Ubuntu", "STATE": "present"}` (pemilik, 22 September 2026, pesan ketiga -- 'Itu usulan definisi, bukan perubahan yang boleh dilakukan agent tanpa Anda menguncinya.' Kosakata STATE dan contoh di atas karena itu tidak diubah; `present` belum termasuk nilai STATE.).

### Contoh pemilik

Ketiganya sah menurut `validate()`, dan diperiksa tes.

```json
{"ACTION": "READ", "OBJECT": "FILE", "TARGET": "/etc/hosts", "CONTEXT": "Ubuntu", "STATE": "requested"}
```
-> argv `cat /etc/hosts`, dikembalikan, tidak dijalankan (ditetapkan; pemilik, 22 September 2026, pesan 'sambil menunggu burn-in')

```json
{"ACTION": "PRINT", "OBJECT": "VALUE", "TARGET": "angka + harga", "CONTEXT": "HC", "STATE": "compiled"}
```
-> CONTEXT HC is not a host: no command is formed for it (ditetapkan; pemilik, 22 September 2026, pesan 'sambil menunggu burn-in')

```json
{"ACTION": "READ", "OBJECT": "FILE", "TARGET": "/var/log/syslog", "CONTEXT": "Ubuntu", "STATE": "latest"}
```
-> argv `cat /var/log/syslog`, dikembalikan, tidak dijalankan (ditetapkan; pemilik, 22 September 2026, pesan sebelumnya -- ditulis ulang dalam bentuk yang berlaku; aslinya {"action": "READ", "object": "FILE", "target": "/var/log/syslog", "context": "ubuntu_host", "state": "latest"})

### Kalimat -> USR

Tata kalimat: <kata kerja> <objek> [<target>] -- target adalah sisa kalimat (usulan).

| action | ar | id | en | status |
|---|---|---|---|---|
| `READ` | `اقرأ` | `baca` | `read` | ditetapkan |

| object | ar | id | en | status |
|---|---|---|---|---|
| `FILE` | `ملف` | `file` | `file` | ditetapkan |

## Katalog Lapis 5

Daftar izin dibaca dari NUI/LAYERS.md, Lapis 5, tabel diizinkan/belum diizinkan -- dibaca dari sana, tidak disalin (R1): diizinkan `ls`, `find`, `cat`, `ps`, `top`, `ping`, `curl`, `journalctl`, `systemctl status`, `docker ps`; belum diizinkan `rm`, `mv`, `kill`, `reboot`, `shutdown`, `systemctl start`, `systemctl stop`, `docker rm`, `docker stop`, `docker exec`.

| USR | argv | di daftar izin | status | sumber |
|---|---|---|---|---|
| `READ FILE` | `cat {target}` | ya | ditetapkan | pemilik, 22 September 2026 -- READ FILE -> cat |
| `READ PROCESS` | `ps aux` | ya | ditetapkan | pemilik, 22 September 2026 -- READ PROCESS -> ps; pemilik, 21 September 2026 -- اعرض العمليات النشطة -> ps aux |
| `READ SERVICE` | `systemctl status {target}` | ya | ditetapkan | pemilik, 22 September 2026 -- READ SERVICE -> systemctl status |
| `READ JOURNAL` | `journalctl` | ya | ditetapkan | pemilik, 22 September 2026 -- READ JOURNAL -> journalctl |
| `READ NETWORK` | `ip` | **tidak** | ditetapkan | pemilik, 22 September 2026 -- READ NETWORK -> ip |
| `READ CONTAINER` | `docker ps` | ya | usulan | `docker ps` di daftar izin |
| `READ DIRECTORY` | `ls {target}` | ya | usulan | `ls` di daftar izin |

Perintah di daftar izin yang belum punya baris katalog: `find`, `top`, `ping`, `curl`.

## Kamus HC

Kamus dibaca per konsep: {KONSEP: {"hc": ..., "arabic": ..., "indonesia": ...}} (ditetapkan; pemilik, 22 September 2026, pesan 'sambil menunggu burn-in'). Dibaca `usr.kamus()` dari `NUI/spec/hc_kamus.json`, satu-satunya tempat ia ditulis:

```json
{
 "VARIABLE": {
  "hc": "let",
  "arabic": "متغير",
  "indonesia": "variabel"
 },
 "PRINT": {
  "hc": "println",
  "arabic": "اطبع",
  "indonesia": "cetak"
 },
 "IF": {
  "hc": "if",
  "arabic": "اذا",
  "indonesia": "jika"
 },
 "FUNCTION": {
  "hc": "fn",
  "arabic": "دالة",
  "indonesia": "fungsi"
 }
}
```

| concept | hc | kind | arabic | indonesia | status | source |
|---|---|---|---|---|---|---|
| VARIABLE (ditetapkan) | `let` | kata kunci | `متغير` | `variabel` | ditetapkan | pemilik, 21 September 2026 dan pemilik, 22 September 2026 |
| PRINT (ditetapkan) | `println` | fungsi bawaan | `اطبع` | `cetak` | ditetapkan | pemilik, 22 September 2026 menulis `println`; pemilik, 21 September 2026 menulis `print`. Keduanya fungsi bawaan HC (src/hijaiyyah/language/evaluator.py) dan keduanya dikompilasi ke PRINT (src/hijaiyyah/compiler/codegen.py) |
| IF (usulan) | `if` | kata kunci | `اذا` | `jika` | ditetapkan | pemilik, 21 September 2026 dan pemilik, 22 September 2026 |
| FUNCTION (usulan) | `fn` | kata kunci | `دالة` | `fungsi` | ditetapkan | pemilik menulis `function`; kata kunci HC untuknya adalah `fn` (src/hijaiyyah/language/tokens.py) |

Ditahan, belum kata kunci tiga bahasa:

| hc | arabic | indonesia | status | reason | source |
|---|---|---|---|---|---|
| `while` | `بينما` | `selama` | ditetapkan | Bentuk Arab dan Indonesianya tidak ditambahkan ke kamus. Diukur: `while` sendiri sudah kata kunci HC dalam bahasa Inggris (src/hijaiyyah/language/tokens.py); yang ditahan adalah permukaan tiga bahasanya. Ada di tabel 21 September, tidak di kedua tabel 22 September. | pemilik, 22 September 2026, pesan ketiga -- 'while tetap belum menjadi keyword. Jangan menambahkannya hanya karena umum di bahasa pemrograman. Itu harus muncul dari kebutuhan HC dan keputusan pemilik.' |

Bukan HC:

| name | arabic | indonesia | status | reason |
|---|---|---|---|---|
| `read_file` | `اقرأ_ملف` | `baca_file` | ditetapkan | tidak ada di HC -- bukan kata kunci, bukan fungsi bawaan, bukan modul. Operasinya adalah USR READ FILE di host, bukan konstruksi bahasa. Tidak dimasukkan tanpa keputusan arsitektur baru. |

### Aturan token

| rule | status | source |
|---|---|---|
| Satu huruf Hijaiyyah -- satu dari 28, termasuk هـ -- tetap literal hybit, tidak pernah kata kunci atau nama | ditetapkan | pemilik, 21 September 2026 |
| Deretan dua huruf Arab atau lebih tanpa pemisah dibaca sebagai SATU kata: kata kunci bila persis ada di tabel, nama bila tidak | ditetapkan | pemilik, 21 September 2026 -- 'nama variabel Arab adalah kata penuh' |
| Huruf yang membentuk kata Arab adalah blok huruf Arab Unicode, termasuk yang bukan anggota 28: hamzah (أ إ آ ء ؤ ئ), ة, ى. Tanpa ini `دالة` dan `اقرأ` pecah, karena hari ini lexer HC hanya mengenal 28 huruf | usulan | diukur: `دالة` pecah jadi د ا ل + nama `ة`, `اقرأ` jadi ا ق ر + nama `أ` |
| Kata kunci Indonesia dicadangkan seperti kata kunci Inggris: `variabel`, `cetak`, `jika`, `fungsi` tidak bisa lagi jadi nama | usulan | diukur: tak satu pun dipakai sebagai nama di kode HC repositori |
| Titik koma boleh dihilangkan, seperti contoh pemilik; HC hari ini sudah menerima pernyataan tanpa `;` | diukur | parser HC |
| Terjemahannya kata demi kata ke HC yang ada, lalu jalur HC -> HISA yang sudah terbukti; tidak ada compiler kedua | ditetapkan | pemilik, 21 September 2026 -- HCL = HC diperluas |

### Contoh

```
متغير angka = 10
متغير harga = 20
اطبع angka + harga
```
-> `let angka = 10; let harga = 20; println(angka + harga);` (ditetapkan; pemilik, 22 September 2026)

```
متغير س = 10
```
-> tidak sah (ditetapkan tidak sah; pemilik, 21 September 2026 -- `س` sudah punya arti matematis)

### Diukur dari repositori

| | |
|---|---:|
| sumber HC (berkas `.hc` dan contoh bawaan) | 19 |
| huruf telanjang di dalamnya | 18 |
| huruf telanjang yang berdampingan | 0 |
| huruf yang lexer HC kenal | 28 |
| kata kunci Arab yang memuat huruf di luar 28 | `دالة` |
| kata kunci Indonesia yang sudah dipakai sebagai nama | tidak ada |

## HC: satu inti, tiga permukaan

HCL adalah HC yang diperluas, bukan bahasa baru (pemilik, 21 September 2026). Satu lexer, satu parser, satu evaluator, satu compiler ke HISA; kata kunci Arab dan Indonesia adalah lapisan sintaks di atasnya, dan implementasinya menunggu sesudah Lapis 5 (pemilik, 22 September 2026).

```
HC   lexer -> parser -> evaluator, dan compiler -> HISA
├── English     let println if fn                berjalan hari ini
├── Arabic      متغير اطبع اذا دالة              dirancang; lexer belum membacanya
└── Indonesian  variabel cetak jika fungsi       dirancang; lexer belum membacanya
```

### Yang dibaca lexer HC hari ini

Diukur, bukan diklaim: inilah yang harus diubah rancangannya.

| hc | Arab dibaca sebagai | Indonesia dibaca sebagai |
|---|---|---|
| `let` | HIJAIYYAH م, HIJAIYYAH ت, HIJAIYYAH غ, HIJAIYYAH ي, HIJAIYYAH ر | IDENTIFIER variabel |
| `println` | HIJAIYYAH ا, HIJAIYYAH ط, HIJAIYYAH ب, HIJAIYYAH ع | IDENTIFIER cetak |
| `if` | HIJAIYYAH ا, HIJAIYYAH ذ, HIJAIYYAH ا | IDENTIFIER jika |
| `fn` | HIJAIYYAH د, HIJAIYYAH ا, HIJAIYYAH ل, IDENTIFIER ة | IDENTIFIER fungsi |

### Sampai HISA

Tiap kata kunci ditanyakan ke compiler HC lewat program HC terkecil yang memakainya. Programnya milik saya, bukan bagian kamus.

| hc | konsep | program uji | sampai HISA | opcode, atau alasan |
|---|---|---|---|---|
| `let` | VARIABLE | `let x = 1;` | ya | `MOVI` |
| `println` | PRINT | `println(1);` | ya | `MOVI`, `PRINT` |
| `if` | IF | `let x = 1; if x { println(x); }` | **tidak** | IfExpr is not compilable yet — this generator handles `let` bindings and expression statements |
| `fn` | FUNCTION | `fn f(a) { return a; }` | **tidak** | FnDecl is not compilable yet — this generator handles `let` bindings and expression statements |

### Contoh pemilik, dari ujung ke ujung

Arab -> HC adalah terjemahan pemilik sendiri dan tidak dijalankan. HC -> HISA dikompilasi compiler HC, dibandingkan dengan HISA yang pemilik tulis, lalu dijalankan di interpreter.

```
متغير angka = 10
متغير harga = 20
اطبع angka + harga
```

```
let angka = 10;
let harga = 20;
println(angka + harga);
```

| compiler HC | ditulis pemilik |
|---|---|
| `MOVI R1, #10` | `MOVI R1,10` |
| `MOVI R2, #20` | `MOVI R2,20` |
| `ADD R3, R1, R2` | `ADD  R3,R1,R2` |
| `PRINT R3` | `PRINT R3` |
| `HALT` | `HALT` |

Sama instruksi demi instruksi: **ya**. Interpreter mencetak **30**. RTL dan papan tidak dijalankan untuk contoh ini.

## Registry Hijaiyyah

Huruf -> operator -> HC -> HISA, dibangun `src/hijaiyyah/nui/registry.py` ke `NUI/hijaiyyah_registry.json`. Tiap kolom dibaca dari tempatnya: Master Table, `OpCode.L_*` dan efeknya `H0 <- H0 + v(huruf)`, muka 5x5 lewat `core.exomatrix.matrix_order` (yang Codex JIM ukur), dan keluaran compiler HC. 28 huruf, karena Master Table dan slot 0xE0-0xFB memuat 28; angka 29 di pesan pemilik adalah salah ketik (pemilik, 22 September 2026, pesan ketiga). Operatornya kedua representasi yang sudah ada, diterima pemilik pada pesan yang sama.

| # | huruf | nama | instruksi | kata | rank GF(2) | periode GF(2) | periode GF(5) | HC | sebagai nama |
|---:|---|---|---|---|---:|---:|---:|---|---|
| 1 | ا | Alif | `L_ALIF` `H0 <- H0 + v(ا)` | `0xe0000000` | 2 | 1 | 1 | `HLOAD H0, #1` | ditolak parser |
| 2 | ب | Ba | `L_BA` `H0 <- H0 + v(ب)` | `0xe1000000` | 4 | 4 | 248 | `HLOAD H0, #2` | ditolak parser |
| 3 | ت | Ta | `L_TA` `H0 <- H0 + v(ت)` | `0xe2000000` | 3 | 1 | 142 | `HLOAD H0, #3` | ditolak parser |
| 4 | ث | Tsa | `L_TSA` `H0 <- H0 + v(ث)` | `0xe3000000` | 4 | 1 | 781 | `HLOAD H0, #4` | ditolak parser |
| 5 | ج | Jim | `L_JIM` `H0 <- H0 + v(ج)` | `0xe4000000` | 5 | 31 | 3124 | `HLOAD H0, #5` | ditolak parser |
| 6 | ح | Ha | `L_HA` `H0 <- H0 + v(ح)` | `0xe5000000` | 4 | 2 | 4 | `HLOAD H0, #6` | ditolak parser |
| 7 | خ | Kha | `L_KHA` `H0 <- H0 + v(خ)` | `0xe6000000` | 5 | 31 | 744 | `HLOAD H0, #7` | ditolak parser |
| 8 | د | Dal | `L_DAL` `H0 <- H0 + v(د)` | `0xe7000000` | 3 | 1 | 1 | `HLOAD H0, #8` | ditolak parser |
| 9 | ذ | Dzal | `L_DZAL` `H0 <- H0 + v(ذ)` | `0xe8000000` | 4 | 3 | 20 | `HLOAD H0, #9` | ditolak parser |
| 10 | ر | Ra | `L_RA` `H0 <- H0 + v(ر)` | `0xe9000000` | 3 | 1 | 1 | `HLOAD H0, #10` | ditolak parser |
| 11 | ز | Zay | `L_ZAY` `H0 <- H0 + v(ز)` | `0xea000000` | 4 | 3 | 20 | `HLOAD H0, #11` | ditolak parser |
| 12 | س | Sin | `L_SIN` `H0 <- H0 + v(س)` | `0xeb000000` | 2 | 1 | 4 | `HLOAD H0, #12` | ditolak parser |
| 13 | ش | Syin | `L_SYIN` `H0 <- H0 + v(ش)` | `0xec000000` | 2 | 1 | 20 | `HLOAD H0, #13` | ditolak parser |
| 14 | ص | Shad | `L_SHAD` `H0 <- H0 + v(ص)` | `0xed000000` | 1 | 1 | 4 | `HLOAD H0, #14` | ditolak parser |
| 15 | ض | Dhad | `L_DHAD` `H0 <- H0 + v(ض)` | `0xee000000` | 1 | 1 | 12 | `HLOAD H0, #15` | ditolak parser |
| 16 | ط | Tha | `L_THA` `H0 <- H0 + v(ط)` | `0xef000000` | 3 | 3 | 20 | `HLOAD H0, #16` | ditolak parser |
| 17 | ظ | Zha | `L_ZHA` `H0 <- H0 + v(ظ)` | `0xf0000000` | 4 | 3 | 60 | `HLOAD H0, #17` | ditolak parser |
| 18 | ع | Ain | `L_AIN` `H0 <- H0 + v(ع)` | `0xf1000000` | 1 | 1 | 4 | `HLOAD H0, #18` | ditolak parser |
| 19 | غ | Ghain | `L_GHAIN` `H0 <- H0 + v(غ)` | `0xf2000000` | 2 | 3 | 12 | `HLOAD H0, #19` | ditolak parser |
| 20 | ف | Fa | `L_FA` `H0 <- H0 + v(ف)` | `0xf3000000` | 4 | 3 | 124 | `HLOAD H0, #20` | ditolak parser |
| 21 | ق | Qaf | `L_QAF` `H0 <- H0 + v(ق)` | `0xf4000000` | 1 | 1 | 24 | `HLOAD H0, #21` | ditolak parser |
| 22 | ك | Kaf | `L_KAF` `H0 <- H0 + v(ك)` | `0xf5000000` | 2 | 1 | 4 | `HLOAD H0, #22` | ditolak parser |
| 23 | ل | Lam | `L_LAM` `H0 <- H0 + v(ل)` | `0xf6000000` | 4 | 2 | 5 | `HLOAD H0, #23` | ditolak parser |
| 24 | م | Mim | `L_MIM` `H0 <- H0 + v(م)` | `0xf7000000` | 2 | 3 | 20 | `HLOAD H0, #24` | ditolak parser |
| 25 | ن | Nun | `L_NUN` `H0 <- H0 + v(ن)` | `0xf8000000` | 2 | 1 | 4 | `HLOAD H0, #25` | ditolak parser |
| 26 | و | Waw | `L_WAW` `H0 <- H0 + v(و)` | `0xf9000000` | 2 | 1 | 4 | `HLOAD H0, #26` | ditolak parser |
| 27 | هـ | Haa | `L_HAA` `H0 <- H0 + v(هـ)` | `0xfa000000` | 2 | 1 | 24 | `HLOAD H0, #27` | ditolak parser |
| 28 | ي | Ya | `L_YA` `H0 <- H0 + v(ي)` | `0xfb000000` | 1 | 1 | 4 | `HLOAD H0, #28` | ditolak parser |

**Ekor 1 tidak berarti invertibel**, jadi rank dicatat sendiri: 7 huruf berekor 1 atas GF(2) dengan rank di bawah 5 -- Dal, Dzal, Tha, Ain, Ghain, Mim, Ya. Docstring `matrix_order` dan `gf2_rank` di `src/hijaiyyah/core/exomatrix.py` membaca ekor 1 sebagai invertibel; itu benar untuk Jim dan Kha, tidak untuk yang lain. Selisih ini dicatat sebagai fakta Lapis 0, `nui.tail_one_is_not_invertibility`, yang dihitung ulang tiap lari tes; matematikanya tidak disunting, dan NUI tidak memakai "ekor 1 berarti invertibel" sebagai aturan sampai definisinya dibuktikan (pemilik, 22 September 2026, pesan ketiga).

## Yang belum ditetapkan

- USR: Arti STATE belum dikunci. Usulan pemilik ada di `state_definition`: keadaan aktual target/objek saat aksi dinyatakan, bukan tahap pipeline -- `present` sebagai contoh, `compiled` sebagai metadata eksekusi. Sampai dikunci, `latest`, `requested`, dan `compiled` tetap tercatat sebagai contoh pemilik.
- USR: CONTEXT selain `Ubuntu` dan `HC` -- misalnya papan HCPU -- belum ada.
- USR: TARGET di CONTEXT HC adalah ekspresi HC; aturan TARGET yang ada ditulis untuk argv host dan hanya berlaku di sana (usulan). Aturan untuk ekspresi HC belum ada.
- USR: Apakah `اطبع angka + harga` diurai jadi USR PRINT VALUE seperti contoh pemilik? Penerjemahnya belum dibangun -- implementasi menunggu sesudah Lapis 5.
- USR: Kosakata kata kerja dan objek selain read/file dalam tiga bahasa belum ditetapkan.
- USR: Apakah satu kalimat boleh mencampur bahasa (`read ملف x`)?
- USR: Contoh pemilik 21 September, `اعرض العمليات النشطة` -> `ps aux`, belum dipetakan: `اعرض` (tampilkan) sebagai READ, `العمليات` sebagai PROCESS, dan `النشطة` (aktif) sebagai STATE adalah tafsiran yang belum disahkan.
- katalog: `ip` (READ NETWORK) tidak ada di daftar izin tahap pertama: masukkan ke daftar izin, atau petakan READ NETWORK ke perintah lain?
- katalog: Opsi perintah (misalnya `journalctl -u <unit>`, `-n <jumlah>`) belum ditetapkan; katalog hanya memakai bentuk yang pemilik tulis.
- kamus: `print` atau `println` untuk `اطبع` / `cetak` -- tabel 21 September menulis `print`, dua tabel 22 September `println`; keduanya ada di HC dan keduanya dikompilasi ke PRINT.
- kamus: Nama konsep untuk `if` dan `fn` (usulan: IF, FUNCTION) -- pemilik baru menamai VARIABLE dan PRINT.
- kamus: Ejaan: `اذا` (tabel pemilik) atau `إذا` (dengan hamzah) -- apakah keduanya diterima?
- kamus: Harakat dan tatweel dalam kata kunci Arab: dibuang sebelum dicocokkan, atau ditolak?
