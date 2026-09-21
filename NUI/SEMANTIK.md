# Lapisan semantik -- USR, katalog Lapis 5, kamus HC

Ditarik dari `NUI/spec/*.json` dan dari pengukuran oleh `src/hijaiyyah/nui/usr.py`. Status `ditetapkan` milik pemilik; `usulan` menunggu pengesahan pemilik. Tidak ada perintah yang dijalankan.

## USR

| name | required | status | source |
|---|---|---|---|
| `action` | True (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `object` | True (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `target` | False (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `context` | False (usulan) | ditetapkan | pemilik, 21 September 2026 |
| `state` | False (usulan) | ditetapkan | pemilik, 21 September 2026 |

Huruf: ACTION dan OBJECT huruf besar; CONTEXT dan STATE huruf kecil (ditetapkan; pemilik, 22 September 2026 -- contoh {"action": "READ", "object": "FILE", ..., "context": "ubuntu_host", "state": "latest"}; contoh 21 September memakai huruf kecil ({"action": "read", "object": "file"}), dan yang berlaku yang terakhir).

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

### TARGET

| rule | status | source |
|---|---|---|
| TARGET adalah satu string, diteruskan sebagai SATU elemen argv -- tidak pernah lewat shell, jadi ; | & $ ` tidak punya arti apa pun | usulan | keamanan: perintah host dibentuk sebagai daftar argumen |
| TARGET tidak boleh diawali '-': ia akan dibaca perintah sebagai opsi, bukan sebagai nama | usulan | keamanan |
| TARGET tidak boleh memuat baris baru atau karakter NUL | usulan | keamanan |

### CONTEXT dan STATE

| name | status | source |
|---|---|---|
| `ubuntu_host` | ditetapkan | pemilik, 22 September 2026 |
| `latest` | contoh pemilik; artinya belum ditetapkan | pemilik, 22 September 2026 |

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

| hc | kind | ar | id | status | source |
|---|---|---|---|---|---|
| `let` | kata kunci | `متغير` | `variabel` | ditetapkan | pemilik, 21 September 2026 dan pemilik, 22 September 2026 |
| `println` | fungsi bawaan | `اطبع` | `cetak` | ditetapkan | pemilik, 22 September 2026 menulis `println`; pemilik, 21 September 2026 menulis `print`. Keduanya fungsi bawaan HC (src/hijaiyyah/language/evaluator.py) dan keduanya dikompilasi ke PRINT (src/hijaiyyah/compiler/codegen.py) |
| `if` | kata kunci | `اذا` | `jika` | ditetapkan | pemilik, 21 September 2026 dan pemilik, 22 September 2026 |
| `while` | kata kunci | `بينما` | `selama` | ditetapkan | pemilik, 21 September 2026; tidak ada di tabel pemilik, 22 September 2026 |
| `fn` | kata kunci | `دالة` | `fungsi` | ditetapkan | pemilik menulis `function`; kata kunci HC untuknya adalah `fn` (src/hijaiyyah/language/tokens.py) |

Bukan HC:

| name | ar | id | reason |
|---|---|---|---|
| `read_file` | `اقرأ_ملف` | `baca_file` | tidak ada di HC -- bukan kata kunci, bukan fungsi bawaan, bukan modul. Operasinya adalah USR READ FILE di host, bukan konstruksi bahasa; menambahkannya ke HC adalah keputusan bahasa, dan aturan 21 September berbunyi 'jangan tambah sampai pipeline terbukti' |

### Aturan token

| rule | status | source |
|---|---|---|
| Satu huruf Hijaiyyah -- satu dari 28, termasuk هـ -- tetap literal hybit, tidak pernah kata kunci atau nama | ditetapkan | pemilik, 21 September 2026 |
| Deretan dua huruf Arab atau lebih tanpa pemisah dibaca sebagai SATU kata: kata kunci bila persis ada di tabel, nama bila tidak | ditetapkan | pemilik, 21 September 2026 -- 'nama variabel Arab adalah kata penuh' |
| Huruf yang membentuk kata Arab adalah blok huruf Arab Unicode, termasuk yang bukan anggota 28: hamzah (أ إ آ ء ؤ ئ), ة, ى. Tanpa ini `دالة` dan `اقرأ` pecah, karena hari ini lexer HC hanya mengenal 28 huruf | usulan | diukur: `دالة` pecah jadi د ا ل + nama `ة`, `اقرأ` jadi ا ق ر + nama `أ` |
| Kata kunci Indonesia dicadangkan seperti kata kunci Inggris: `variabel`, `cetak`, `jika`, `selama`, `fungsi` tidak bisa lagi jadi nama | usulan | diukur: tak satu pun dipakai sebagai nama di kode HC repositori |
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

## Yang belum ditetapkan

- USR: Apa arti STATE `latest`: isi saat ini, atau entri terbaru saja?
- USR: CONTEXT selain `ubuntu_host` -- misalnya papan HCPU -- belum ada.
- USR: Kosakata kata kerja dan objek selain read/file dalam tiga bahasa belum ditetapkan.
- USR: Apakah satu kalimat boleh mencampur bahasa (`read ملف x`)?
- USR: Contoh pemilik 21 September, `اعرض العمليات النشطة` -> `ps aux`, belum dipetakan: `اعرض` (tampilkan) sebagai READ, `العمليات` sebagai PROCESS, dan `النشطة` (aktif) sebagai STATE adalah tafsiran yang belum disahkan.
- katalog: `ip` (READ NETWORK) tidak ada di daftar izin tahap pertama: masukkan ke daftar izin, atau petakan READ NETWORK ke perintah lain?
- katalog: Opsi perintah (misalnya `journalctl -u <unit>`, `-n <jumlah>`) belum ditetapkan; katalog hanya memakai bentuk yang pemilik tulis.
- kamus: `print` atau `println` untuk `اطبع` / `cetak` -- dua tabel pemilik berbeda; keduanya ada di HC.
- kamus: `while` ada di tabel 21 September, tidak di tabel 22 September -- tetap, atau dikeluarkan?
- kamus: Ejaan: `اذا` (tabel pemilik) atau `إذا` (dengan hamzah) -- apakah keduanya diterima?
- kamus: Harakat dan tatweel dalam kata kunci Arab: dibuang sebelum dicocokkan, atau ditolak?
