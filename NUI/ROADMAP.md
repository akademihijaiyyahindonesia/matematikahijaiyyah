# Peta jalan: dari satu klasifikasi ke kecerdasan yang lebih umum

Ini tentang **NUI di folder ini** — jaringan saraf terlatih di
`src/hijaiyyah/nui/`, program nyata dengan bobot terlatih dan angka terukur.
**Bukan** `src/hijaiyyah/ai/` — itu persona LLM (Hermes/Qwen lewat Ollama)
yang meminjam nama NUI tapi tidak punya satu parameter pun yang dilatih di
repositori ini. Dua hal berbeda yang kebetulan berbagi nama; kebingungan itu
sudah pernah muncul di sesi ini dan sengaja dipisah ulang di sini.

## Batas jujur, sebelum peta jalannya

**"AI umum" dalam arti penuh — kecerdasan yang menjawab pertanyaan apa pun,
tentang domain apa pun, seperti manusia — bukan sesuatu yang bisa dijanjikan
peta jalan mana pun, oleh siapa pun, hari ini.** Itu bukan kerendahan hati
kosong; itu fakta tentang keadaan riset kecerdasan buatan secara global, dan
proyek ini sendiri punya aturan (`cosmictera/RULES.md` R2) yang justru
melarang klaim naik tanpa bukti baru. Menjanjikan AGI di sini akan melanggar
disiplin yang sama yang membuat setiap dokumen lain di repositori ini bisa
dipercaya.

**Yang bisa ditawarkan, dan ini yang peta jalan ini sungguh berisi:** rangkaian
tahap konkret, masing-masing benar-benar memperluas kemampuan NUI dengan
memakai aset yang **sudah ada dan sudah diverifikasi** di proyek ini —
bukan menambah data dari luar, bukan membungkus model lain — bergerak dari
"satu klasifikasi biner" menuju "kecerdasan yang lebih umum **di dalam
domain matematika/komputasi yang proyek ini sendiri sudah bangun**": huruf,
guard, eksomatriks, HISA, kripto Ka'bah. Umum di dalam domain itu, bukan
umum lintas segala hal. Setiap fase berlabel `AT` (Aspirational Target) —
lihat [`cosmictera/RULES.md`](../cosmictera/RULES.md) — karena belum satu
pun dari fase 1-5 di bawah ini yang dibangun. Label naik hanya dengan bukti
baru, persis seperti [`cosmictera-build/ROADMAP.md`](../cosmictera-build/ROADMAP.md)
untuk sisi perangkat keras.

---

## Kenapa NUI ada di rancangan Cosmictera Computing

**Bukan kebetulan nama, satu disiplin yang sama.** `cosmictera/SYSTEM.md`
punya bagian bernama "Lipatan: bit → clock → tera" — jalur nyata yang
ditempuh Ka'bah cipher: bit mentah → byte (8 clock/byte, deserialiser,
INI bottleneck-nya) → clock (gerbang+pencacah, gratis) → lajur → permutasi
(310 clock) → tera. Setiap tahap punya biaya yang **dihitung dari
konstanta nyata**, bukan diasumsikan — dan `CONCRETE.md` bahkan menjelaskan
kenapa satu jejak nyata mengukur 9,66 clock/byte, bukan 10,42 yang
asimtotik, dengan aritmatika eksplisit (383 byte = 2,99 blok rate, 622
klik tertahan persis 2×310), bukan digelapkan sebagai "kira-kira sama."

**`nui/freeze.py`, dibangun di sesi yang sama, menempuh jalur yang
STRUKTURNYA SAMA** — bukan disalin, ditemukan berkali-kali cocok karena
disiplinnya sama: bit UART (`bit_period_seconds`) → clock HCPU
(`clock_period_seconds`) → midpoint sampling (`uart_bit_midpoint_clocks`,
persis argumen "SAMPLING AT BIT CENTRES" `hcpu_uart_rx.v` sendiri) → byte
(`wire_seconds`) → rack (`rack_heartbeat_clocks`). Dan disiplin
"dihitung, bukan diasumsikan"-nya sama persis: `rack_heartbeat_seconds()`
sengaja TIDAK dibuat identik dengan `wire_seconds()` — beda ~0,16% karena
klik nyata dibulatkan bulat, dijelaskan dengan aritmatika eksplisit,
persis cara `CONCRETE.md` menjelaskan 9,66 vs 10,42.

**Dan label kejujuran yang sama.** `SYSTEM.md` menandai FIFO yang belum
dibangun dengan `[EH]` — "belum dibangun, belum diukur." `freeze.py` punya
padanannya sendiri: `machine.cycle` SENGAJA tidak dijadikan klaim latensi
eksekusi nyata, karena `hisa/machine.py` sendiri sudah bilang interpreter
ini tidak memodelkan waktu pipeline — angka itu cuma ada di `CYCLES=`
sungguhan hardware, bukan Python. Dua sistem, dua bagian repositori yang
ditulis pada waktu berbeda, sampai pada aturan yang SAMA: jangan
melaporkan angka yang salah satu sisinya terpaksa berbohong.

**Itu jawabannya:** NUI ada di rancangan Cosmictera Computing bukan
karena dipasang berdampingan secara administratif, tapi karena NUI
DIBANGUN dengan disiplin komputasi yang sama yang sudah membuat Ka'bah
cipher, HCPU, dan seluruh `cosmictera-build/` bisa dipercaya —
`cosmictera/RULES.md`'s R2 (label naik hanya dengan bukti baru) berlaku
sama persis di sini (lihat "Batas jujur" di atas), dan "Lipatan: bit →
clock → tera"-nya CosmicTera ternyata punya versi NUI sendiri, ditemukan
bukan dirancang untuk itu dari awal.

---

## Fase 0 — sudah ada (CC, bukan AT)

Satu tugas: apakah eksomatriks GF(2) dari huruf yang terakumulasi mencapai
orde maksimum (31)? Empat varian embedding diadu, hasil jujur diukur ulang
dan cocok persis (lihat [`README.md`](README.md)). Ini fondasinya, bukan
tujuannya — satu kepala prediksi, satu pertanyaan, jaringan sekecil 385-1.405
parameter.

---

## Atom: satu alamat, dua wujud (`nui/atom.py`, CC — selesai)

**Ini bukan salah satu dari lima fase — ini fondasi di bawah semuanya,**
dan jawaban langsung atas satu permintaan: huruf sebagai *pointer/alamat*
yang juga punya wujud fisik nyata, menjembatani NUI (Python) dengan HCPU
(RTL). Bukan ide baru yang dibangun dari nol — tiga hal yang **sudah ada**,
ditulis independen, dan **memang sudah selalu sepakat**, cuma belum pernah
ditulis eksplisit dan dicek bersama:

```
indeks Master Table (1-based, MASTER_TABLE.get_by_char(c).index)
    == opcode − LETTER_OP_FIRST + 1        (hisa.opcodes.OpCode.L_<X>)
    == letter_index di perangkat keras     (rtl/hcpu_execute.v:188-189)
```

Satu bilangan bulat itulah **alamat**: baris di tabel Python, kata opcode
(0xE0-0xFB), dan alamat ROM yang pipeline HCPU sungguhan pakai di silikon —
ketiganya angka yang sama, diverifikasi (`verify_address_unification()`,
`tests/test_ai/test_nui_atom.py`, 6/6 lulus), bukan diasumsikan.

Dua **wujud** dari alamat itu:

- **Perangkat lunak** — `features.vector_features`, lima angka fisika
  (titik/garis/lengkung/theta/rho), embedding "physics" Fase 0.
- **Fisik** — `rtl/programs/nui_embedding.hasm` menghitung lima angka yang
  SAMA di opcode HCPU sungguhan (`L_JIM`, `L_KHA` — alamat atom ini
  sendiri) dan mem-`PRINT`-kannya lewat UART nyata, pada clock nyata 27 MHz
  — bitstream pada Hz sungguhan, bukan deskripsi tentangnya, sudah
  diverifikasi byte-demi-byte di simulasi sesi ini (`tb_hcpu_nui_embedding.v`,
  `"2\n2\n2\n6\n6\n"`).

`test_jim_and_kha_atoms_match_nui_embedding_hasms_proven_physical_output`
mengecek dari sisi Python: fitur fisika Jim+Kha (dari alamatnya) berjumlah
persis (2,2,2,6,6) — cocok dengan yang UART sungguhan sudah cetak, tanpa
perlu menjalankan ulang simulasi RTL untuk membuktikannya lagi.

**Kenapa berlabel `CC`, bukan `AT`:** tidak ada yang dibangun dari nol di
sini — modul ini membuat eksplisit dan menguji sesuatu yang sudah nyata di
tiga tempat berbeda di repositori ini, ditulis pada waktu yang berbeda,
untuk alasan yang berbeda, dan ternyata sudah sepakat. Itulah "atom": bukan
metafora, satu alamat yang sudah punya dua wujud nyata, dipertemukan.

---

## Clockwork: mekanisme berurutan, bukan jaringan saraf (`nui/clockwork.py`, CC — selesai)

**Bukan salah satu dari lima fase juga — ini mekanisme terpisah, dipilih
secara eksplisit sebagai bukan-LLM.** Fase 0 dan 1 adalah jaringan saraf:
ada bobot, ada pelatihan. Ini tidak — tidak ada parameter, tidak ada yang
dilatih. Diberi sekuens huruf **berurutan** (urutan sungguh berpengaruh di
sini, beda dari akumulasi v18 Fase 0/1), ia melangkah satu huruf per
langkah — satu **tick** per huruf — dan tiap tick hanya melihat state yang
sedang berjalan plus huruf berikutnya, tidak pernah seluruh sekuens
sekaligus seperti attention pada LLM.

Mekanisme per-tick-nya `core.exomatrix.compose_step`: perkalian matriks
GF(2) (atau GF(p) apa pun), order-sensitive — sudah diukur di
`nui/pattern_language.py`, ~31% pasangan berurutan memberi rank komposisi
berbeda tergantung huruf mana lebih dulu. `compose_mod` sudah menjalankan
loop yang sama persis secara internal; modul ini mengekspos apa yang lewat
di tiap langkah, bukan cuma matriks akhirnya.

Tiap tick di-ground ke **dua** fakta true/false yang dihitung independen,
bukan satu label di ujung sekuens:

```python
from hijaiyyah.nui.clockwork import run
for tick in run(["ج", "خ"]):
    print(tick.step, tick.char, hex(tick.opcode), tick.rank, tick.full_rank, tick.primitive)
# 1 ج 0xe4 5 True True    -- Jim sendirian: rank penuh, primitif (fakta lama, period 31)
# 2 خ 0xe6 5 True False   -- setelah Kha: rank tetap penuh, primitivitas hilang
```

Huruf tiap tick dialamatkan persis seperti `nui/atom.py`: opcode-nya adalah
alamat yang sama yang menamai barisnya di Master Table dan alamat ROM-nya
di silikon HCPU sungguhan — bukan alamat baru.

`atom.py`'s wujud fisik (`nui_embedding.hasm`) menghitung fitur yang
**dijumlah** (v18) — operasi yang instruksi HCPU-nya sudah ada
(`L_<huruf>`, `CGET`, `ADD`). Mekanisme di sini mengalikan **matriks**
GF(2) (`compose_step`) — operasi yang instruksi HCPU-nya belum ada. Fase 2
di bawah: encoder urutan atas eksekusi `HISAMachine` sungguhan.

### Rack, chip, channel: 28 huruf sebagai bank kode, jalur antar-node bernama

**`nui/rack.py`** memformalkan 28 huruf sebagai **rack** — bank 28 slot
standar, urutan Master Table, persis arti kata "rack" di perangkat keras:
bingkai berisi slot yang jumlahnya tetap. Tiap slot satu **chip**: satu
**node** (alamat — opcode, sama seperti `nui/atom.py`) yang membawa
**data**-nya sendiri (titik/garis/lengkung, plus pasangan puntiran
theta/rho).

```python
from hijaiyyah.nui.rack import RACK, chip_for
len(RACK)              # 28
j = chip_for("ج")
j.opcode, j.point, j.line, j.curve, j.theta, j.rho   # 0xe4, 1, 1, 1, 3, 3
```

**Chip bukan cuma data yang diam di RAM — ia yang menjalankan komposisinya
sendiri.** `Chip.boot()` dan `Chip.step(state)` bukan properti yang dibaca:
keduanya method yang benar-benar mengomposisikan (`core.exomatrix.
compose_step`/`build_exomatrix`) dan **mengembalikan** matriks baru — hasil
diserahkan ke pemanggil, bukan disimpan di suatu tempat untuk dibaca
belakangan. `clockwork.run()` sekarang benar-benar memanggil ini
(`chip_for(char).boot(p)` untuk huruf pertama, `chip_for(char).step(state,
p)` untuk sisanya) — bukan lagi menghitung komposisinya sendiri secara
inline. Chip yang jalan; `clockwork` cuma mengurutkan chip mana jalan
kapan.

```python
jim, kha = chip_for("ج"), chip_for("خ")
state = kha.step(jim.boot())     # persis run(["ج", "خ"])[-1].state
```

**`Channel`** (di `clockwork.py`) menamai jalur antar-node yang tadinya
implisit di antara dua `Tick`: node mana yang mengalir masuk, node mana
yang dikomposisikan dengannya, dan state di kedua sisi. Sekali lagi bukan
hitungan baru — `channels(ticks)` cuma membaca `ticks[i].state` dan
`ticks[i+1].state` yang `run()` sudah hitung, memberinya nama sendiri
alih-alih dibiarkan tersirat.

```python
from hijaiyyah.nui.clockwork import run, channels
for ch in channels(run(["ج", "خ", "م"])):
    print(ch.from_node, "->", ch.to_node)
# ج -> خ
# خ -> م
```

**Cara memeriksa:** `pytest tests/test_ai/test_nui_rack.py` (4/4) —
28 slot persis urutan Master Table, tiap chip dicek terhadap `atom_for`
langsung, data Jim dicek terhadap fakta lama (titik=garis=lengkung=1,
theta=rho=3). `channels()` punya 4 tes sendiri di
`test_nui_clockwork.py` — jumlah channel = jumlah tick − 1, satu tick
tidak punya channel sama sekali, dan tiap channel dicek sama persis
dengan state tick yang berdampingan, bukan dihitung ulang.

---

### Catatan mekanis: "crack over the jump per Hz"

Satu istilah untuk sifat yang sudah ada di setiap tes di atas — bukan
properti baru, nama untuk sesuatu yang sudah dibuktikan sebelum diberi
nama.

**Bit-join.** `Channel`/`compose_step` memang operasi penggabungan bit —
perkalian matriks GF(2) itu AND lalu XOR, bit demi bit
(`core.exomatrix._matmul_mod`). "Join" bukan metafora di sini; itu literal
apa yang terjadi di setiap tick.

**Node, cahaya per clocking.** `Tick` menyala — di-ground true/false — satu
per satu, urut, bukan sekaligus. Setiap node punya alamatnya sendiri
(`nui.atom`, opcode yang sama dengan ROM HCPU sungguhan).

**"Crack over the jump per Hz" — nama untuk sifat diskretnya.** Setiap tick
adalah **loncatan** (jump): satu `compose_step`, bukan aliran kontinu. Di
antara dua tick ada **crack** — celah yang sungguh nyata secara matematis,
bukan puitis: tick ke-i cuma melihat state SEBELUMnya plus satu huruf
berikutnya, tidak pernah seluruh sekuens sekaligus (alasan yang sama
`clockwork.py`'s docstring sudah beri untuk kenapa ini bukan attention gaya
LLM). Itulah **parsialitas**-nya: tiap loncatan cuma tahu sepotong, bukan
keseluruhan — dan `test_order_genuinely_changes_the_final_state` adalah
buktinya, bukan klaim kosong: kalau tiap tick "melihat" seluruh sekuens
sekaligus, urutan tidak akan pernah mengubah apa pun.

**"For-load"** — `rtl/tb/tb_gowin_loader_nui.v`, dibangun tepat setelah
catatan ini diminta: huruf beralamat (`L_JIM`/`L_KHA`) dikirim lewat kabel
loader, bukan dibakar ke bitstream, lulus di percobaan pertama. Loncatan
per huruf yang tadinya cuma ada di Python (`clockwork.run()`) sekarang juga
terbukti di jalur fisik pengiriman kode — bukan komputasinya (itu masih
GF(2) matrix, belum ada instruksi HCPU untuknya — lihat `clockwork.py`),
tapi jalur **memuat** huruf demi huruf sebagai program yang berjalan.

**"Setiap pengetesan juga cepat" — dan kenapa itu bukan kontradiksi.**
Mekanismenya bicara tentang Hz (clock 27 MHz sungguhan), tapi tes-nya
sendiri tidak menunggu Hz sungguhan: 28 tes Python (`atom`+`clockwork`+
`rack`) selesai < 1 detik gabungan — deterministik, bukan simulasi waktu
nyata sama sekali. Bench RTL (`sim_loader_nui`) yang MEREPRESENTASIKAN
~20 milidetik waktu nyata di 27 MHz selesai dalam hitungan detik simulasi
Icarus. Cepat karena ini **simulasi/logika**, bukan karena mekanismenya
sederhana — persis pembagian yang sudah ditulis di Fase 1: program dulu
(cepat diuji), Hz sungguhan belakangan (`ROADMAP.md`'s Fase 2).

---

### Freeze mode: protokol kabel loader dipalsukan, biar tiap tes ultra cepat (`nui/freeze.py`, CC — selesai)

**"For-load" di atas sudah lulus, tapi lambat** — `sim_loader_nui` sungguh
mensimulasikan UART bit-serial di Icarus, detik demi detik simulasi untuk
merepresentasikan ~20 milidetik waktu nyata. Itu perlu, untuk membuktikan
FRAMING-nya sungguh berjalan di waktu — tapi tidak setiap tes yang memakai
protokol yang sama butuh membuktikan itu ulang.

**Yang dibekukan cuma jamnya, bukan protokolnya.** `nui/freeze.py`'s
`mock_wire(words)` menghasilkan byte yang SAMA persis dengan
`rtl/scripts/send_program.py`'s `encode()` — cacah kata lalu kata-kata,
byte paling signifikan dulu — dicek langsung byte-demi-byte
(`test_mock_wire_matches_send_programs_own_encode_byte_for_byte`), bukan
protokol paralel yang cuma mirip. `freeze_load(program_src)` menaruh byte
itu di `HISAMachine.rx_queue` (list Python biasa — sudah ada sejak
`test_boot_path.py`, cuma belum punya nama dan rumah sendiri) lalu
menjalankan `loader.hasm` sebagai interpreter, satu `step()` per instruksi
— **"satuan bit per klik"** yang sama granularitasnya dengan wire
sungguhan (satu byte per akses `REG_RX_DATA`), cuma tanpa 27 MHz clock
menghitung siklus di antaranya.

```python
from hijaiyyah.nui.freeze import freeze_load
m = freeze_load(nui_embedding_hasm_source, base_dir=...)
m.output        # [2, 2, 2, 6, 6]  -- sama dengan tb_gowin_loader_nui.v
m.imem_waddr    # 112 == 64 + 48   -- write port sungguh maju 48 kali
```

**Klaim fisik yang sama, dua cara berbeda:** `tb_gowin_loader_nui.v`
membuktikannya di simulasi RTL (detik); `freeze_load` membuktikan klaim
YANG SAMA (keluaran `2,2,2,6,6`, `imem_waddr` maju 48) di interpreter Python
(milidetik) — bukan pengganti, pelengkap yang lebih cepat untuk logika yang
sama. Dipilih dengan sengaja mengulang klaim yang sudah terbukti secara
fisik, bukan klaim baru yang belum diverifikasi di jalur manapun.

**"Dim/lit" — kecepatan mock TIDAK diklaim sebagai kecepatan Hz sungguhan,
keduanya dipisah eksplisit.** `freeze_load`'s waktu tempuh (milidetik) cuma
overhead interpreter Python, bukan fakta tentang clock nyata sama sekali —
tapi kecepatan WIRE sungguhan tetap bisa dihitung LANGSUNG, tanpa simulasi,
dari konstanta yang board-nya sendiri sudah pakai: `wire_bytes_per_second()`
= 115200 baud / 10 bit per byte (1 start + 8 data + 1 stop, `hcpu_uart_rx.v`/
`hcpu_uart_tx.v`'s sendiri) = **11.520 byte/detik**, tepat. `wire_seconds(n)`
memberi berapa lama `n` byte SUNGGUH makan waktu di UART nyata — untuk
`nui_embedding.hasm` (196 byte: 4 cacah + 48 kata × 4), itu **17,01 ms** di
papan sungguhan, dibanding ~6-7 ms `freeze_load` makan di Python (angka yang
terakhir itu TIDAK berarti apa-apa soal Hz, cuma kecepatan interpreter host
ini). Dua angka, dua sumber berbeda — satu dihitung dari fisika UART papan
sungguhan, satu diukur dari `time.perf_counter()` di Python — sengaja tidak
dicampur jadi satu klaim.

**Satu tingkat lagi ke bawah — "signal pulling," dihitung bukan diukur:**
`bit_period_seconds()` (durasi satu bit UART sungguhan, ~8,68 µs) dan
`clock_period_seconds()` (durasi satu detak HCPU sungguhan pada kristal
27 MHz `hcpu_gowin_top.v`, ~37,0 ns) — dua angka yang membentuk
`clocks_per_uart_bit()`, persis rumus `DIVISOR = CLK_HZ / BAUD` yang
`hcpu_uart_rx.v` sendiri pakai untuk menyampel tengah tiap bit (**234**,
dihitung ulang independen, bukan disalin dari komentarnya). Detak chip
234× lebih cepat dari satu bit UART — bukan kiasan, angka nyata dari dua
konstanta yang chip-nya sendiri bagi.

**Total waktu boot** = waktu transfer kabel (dihitung di atas, `wire_seconds`)
**plus** waktu eksekusi `loader.hasm` + program yang dimuat sampai HALT.
Komponen kedua tidak dihitung di `freeze.py`: `hisa/machine.py`'s
`REG_COUNTER` — "it counts real clock cycles, and this interpreter does
not model the pipeline's timing." `machine.cycle` (jumlah `step()` yang
`freeze_load` habiskan) dikali `clock_period_seconds()` akan melanggar itu
langsung, jadi tidak dilakukan. Angka waktu-eksekusi ada di satu tempat:
laporan `CYCLES=` yang `rtl/fpga/gowin/hcpu_gowin_top.v`'s wrapper kirim
lewat UART setelah core berhenti (`rtl/tb/tb_gowin_top.v`,
`rtl/tb/tb_parity.v`), atau simulasi RTL/papan sungguhan itu sendiri.

**Midpoint, dan detak jantung rack dalam klik-bit.** `hcpu_uart_rx.v`
sendiri punya argumen kebenaran yang ditulis eksplisit di headernya:
"SAMPLING AT BIT CENTRES" — sampel pertama diambil di TENGAH bit
(`HALF = DIVISOR / 2`), bukan di tepinya, supaya clock yang meleset
beberapa persen tetap membaca nilai yang benar. `uart_bit_midpoint_
clocks()` menamai angka itu — klik ke-**117** dari 234 ke dalam tiap bit
UART sungguhan, dihitung ulang independen, dicek langsung terhadap teks
`hcpu_uart_rx.v` sendiri.

`rack_heartbeat_clocks()`/`rack_heartbeat_seconds()` menerapkan hitungan
klik yang sama ke seluruh **28 node rack** (`nui.rack.NUM_SLOTS`), satu
byte opcode nyata per node, berurutan lewat kabel sungguhan — bukan
`clockwork.run_rack()`'s 28 tick perangkat lunak (itu perkalian matriks
GF(2), nol klik nyata), tapi apa yang 28 node yang SAMA akan makan kalau
opcode-nya benar-benar dikirim satu per satu di kabel: **28 × 10 bit/byte
× 234 klik/bit = 65.520 klik HCPU sungguhan (2,427 ms)** — dekat tapi
SENGAJA tidak identik dengan `wire_seconds(28)`'s 2,431 ms, karena
perangkat keras sungguhan menghitung klik BULAT (`clocks_per_uart_bit()`
membulatkan ke bawah `CLK_HZ/BAUD`), bukan baud pecahan ideal — beda
~0,16%, dicek langsung sebagai kedekatan sekaligus ketidaksamaan, bukan
digelapkan jadi satu angka yang sama.

**Byte/bit dan cosmic speed adalah DUA BACAAN dari satu latensi yang
sama, bukan dua angka kebetulan cocok.** Membagi `rack_heartbeat_clocks()`
(65.520 klik) dengan rasio cosmic speed (`clocks_per_uart_bit()` = 234×)
mengembalikan PERSIS cacah bit yang jadi titik tolak hitungan byte/bit-nya:
**65.520 ÷ 234 = 280 bit**, sama dengan 28 byte × 10 bit/byte — dicek
sebagai pembagian bulat tanpa sisa (`% == 0`), bukan didekati.

**Apakah urutan rack selamat lewat kabel?** Ini pertanyaan yang belum
benar-benar dijawab sebelumnya — `rack_heartbeat_*` cuma menghitung WAKTU,
bukan membuktikan URUTAN selamat. `rtl/programs/letters.hasm` (fakta
sungguhan yang sudah ada: `HNRM2==112` untuk Ba+Sin+Mim, dibuktikan di
`tb_gowin_top`) mengakumulasi Ba, Sin, Mim, lalu SEMUA 28 huruf persis
urutan Master Table — persis urutan `nui.rack.RACK`. Dijalankan lewat
`freeze_load(letters.hasm)` (dirakit → dikirim lewat kabel yang dipalsukan
→ dimuat `loader.hasm` → dieksekusi instruksi demi instruksi), lalu
`executed_letters(machine)` membaca LANGSUNG dari `machine.trace` huruf
mana yang benar-benar tereksekusi dan urutannya — bukan dari program
sumbernya. 28 huruf terakhir yang tereksekusi cocok PERSIS urutan
`RACK` — kalau urutan byte, urutan word, kemajuan write-port, atau
serah-terima ERET-nya salah, ini akan tampak sebagai urutan yang acak
walau H0 akhirnya (penjumlahan v18, tidak peduli urutan) masih terlihat
benar. Dicek DUA hal sekaligus, bukan cuma satu: urutan (`fired[-28:] ==
[c.char for c in RACK]`) DAN nilai (`data_mem[0x100] == 112`, fakta yang
sama yang `tb_gowin_top` baca di silikon).

**Cara memeriksa:** `pytest tests/test_ai/test_nui_freeze.py` (18/18), semua
< 0,15 detik gabungan — termasuk pengecekan langsung bahwa `mock_wire`
setuju dengan `encode()` sungguhan, `UART_BAUD`/`HCPU_CLK_HZ` dicek
terhadap konstanta RTL sungguhan (`hcpu_uart_rx.v`, `hcpu_gowin_top.v`'s
`OSC_HZ` — bukan `hcpu_uart_tx.v`'s default 50 MHz yang papan ini tidak
pernah pakai), `wire_bytes_per_second()`/`wire_seconds()`/
`clocks_per_uart_bit()`/`uart_bit_midpoint_clocks()` dicek dengan
aritmatika langsung DAN terhadap teks `hcpu_uart_rx.v`'s `HALF` sendiri,
`rack_heartbeat_seconds()` dicek dekat TAPI tidak identik dengan
`wire_seconds(28)` (bukan cuma salah satunya), pembagian balik cosmic
speed ↔ cacah bit dicek tanpa sisa, `executed_letters()` dicek urutan
DAN nilai sekaligus lewat `letters.hasm` sungguhan, disclaimer
`REG_COUNTER` di `hisa/machine.py` dicek kata-demi-kata (bukan cuma
dikutip), dan pengecekan waktu yang memastikan "ultra cepat" bukan klaim
kosong (< 1 detik per `freeze_load`).

---

### `automate()`: boot → bend → emit, tiga tahap bernama

`run()` di atas sudah *melakukan* semua ini; `automate()` cuma memberinya
nama tiga tahap yang eksplisit, dipetakan langsung ke tiga primitif
geometris yang sudah jadi inti NUI sejak Fase 0 — titik/garis/lengkung:

- **BOOT** ("garis," aliran lurus) — tick pertama `run()` sendiri: eksomatriks
  huruf pertama, apa adanya, belum dikomposisi dengan apa pun. Garis lurus:
  yang masuk persis yang keluar.
- **BEND** ("lengkung," dibengkokkan) — setiap tick sesudahnya: `compose_step`
  membengkokkan state lurus itu jadi sesuatu yang bukan lagi eksomatriks
  satu huruf saja. Ini `run()`'s tick loop sendiri, tidak ada yang dihitung
  baru — tahap ini cuma menamai apa yang sudah terjadi.
- **EMIT** ("titik," lubang kecil, di bawah tekanan komputasi nyata) —
  state yang berjalan, satu matriks 5×5 penuh, diperas jadi SATU bit: satu
  grounding true/false, bukan matriksnya sendiri. `Automation.emitted`
  betulan satu `bool`, dibaca dari `full_rank` atau `primitive` tick
  terakhir — tidak ada yang dihitung baru di sini juga.

```python
from hijaiyyah.nui.clockwork import automate
a = automate(["ج", "خ"], ground="primitive")
a.boot_char   # 'ج' -- garis, aliran lurus pertama
a.ticks       # semua tick -- lengkung, dibengkokkan langkah demi langkah
a.emitted     # False -- titik, satu bit keluar dari lubang kecil
```

**Cara memeriksa:** `pytest tests/test_ai/test_nui_clockwork.py` (27/27) —
tiap tick dicek ulang terhadap `compose_mod` dari prefiks yang sama
(bukan cuma dipercaya benar), groundings dicek ulang terhadap `gf2_rank`/
`matrix_order_of` langsung, `test_order_genuinely_changes_the_final_state`
membuktikan sensitivitas urutan pada satu pasangan konkret (Jim/Kha) bukan
cuma mengutip angka 31% dari `pattern_language.py`, dan lima tes tambahan
mengecek `automate()` tidak menghitung ulang apa pun yang `run()` belum
hitung — `a.ticks == tuple(run(letters))`, persis.

---

### `rank_permutations()`: urutan rack diacak, di-ranking per tick/bit

28 huruf rack punya 28! urutan — tidak bisa dienumerasi. `rank_permutations()`
mengambil sampel acak (`random.Random(seed)`, direproduksi persis dengan
seed sama), menjalankan tiap urutan lewat `run()`, dan me-ranking hasilnya
berdasar tiga angka yang `Tick` sudah hitung — bukan hitungan baru:

```python
from hijaiyyah.nui.clockwork import rank_permutations
scores = rank_permutations(count=1000, seed=0)
scores[0].order              # urutan 28 huruf dengan skor tertinggi
scores[0].full_rank_ticks    # cacah tick rank==5 -- kunci ranking utama
scores[0].primitive_ticks    # cacah tick primitif -- pemutus seri
scores[0].final_rank         # rank tick terakhir -- pemutus seri kedua
```

**Angka terukur** (1000 sampel, seed=0, RACK's 28 huruf penuh):

| | Nilai |
|---|---:|
| `full_rank_ticks` maksimum | 2 dari 28 |
| `primitive_ticks` maksimum | 1 dari 28 |
| `final_rank` == 0 | 999/1000 sampel |
| `final_rank` maksimum teramati | 1 |

`run_rack()` sendiri (urutan Master Table, bukan sampel acak) juga
berakhir di `final_rank == 0` — sama dengan 999 dari 1000 sampel acak.
Mengomposisikan 28 eksomatriks lewat `compose_step` membuat matriks yang
berjalan singular hampir tanpa peduli urutan, bukan cuma di satu urutan
tertentu.

**Cara memeriksa:** 8 tes `rank_permutations` di
`tests/test_ai/test_nui_clockwork.py` — termasuk pengecekan langsung
bahwa skor teratas cocok dengan `run()` dihitung ulang dari urutannya
sendiri, bahwa seed yang sama memberi sampel yang sama persis, dan angka
999/1000 di atas dipin sebagai tes (`test_rank_permutations_most_
orderings_end_at_rank_zero`), bukan cuma dikutip di sini.

---

## Fase 1 — SELESAI (dicoba, hasil campuran, dilaporkan apa adanya)

**Kenapa ini langkah pertama menuju "umum".** Kecerdasan berarti menjawab
lebih dari satu pertanyaan tetap.

**Satu rencana di draf pertama peta jalan ini gugur sebelum ditulis jadi
kode — dan itu justru contoh disiplinnya bekerja.** Guard G1-G4/T1/T2
(`guards.full_guard_check`) direncanakan sebagai sumber label tambahan.
Dicek dulu secara empiris (bukan diasumsikan): **ke-28 huruf kanonik lolos
semua guard secara individual, dan G1-G3 adalah identitas linear (G4 jumlah
dari nilai tak-negatif)** — jadi akumulasi APA PUN dari huruf kanonik tetap
lolos semua guard. 2.000 subset acak, seed 0: **100% lolos, semua guard,
setiap kali.** Label yang tidak pernah berubah tidak mengajari apa-apa;
dicoret sebelum satu baris kode latih ditulis, bukan sesudah hasil buruk
muncul. Diverifikasi ulang di
`tests/test_ai/test_nui_multitask.py::test_guard_validity_never_varies_under_accumulation`.

**Yang benar-benar dibangun dan dilatih** — trunk (embedding+sum) yang sama
dari Fase 0, tiga kepala di atasnya (`model.MultiTaskAccumulatorNet`),
dilatih bersama (`multitask.py`, `python3 -m hijaiyyah.nui.multitask`):

| Tugas | Sumber (sudah ada) | Sifatnya |
|---|---|---|
| `gf2_primitive` | `exomatrix.matrix_order(v, 2)` | Fase 0's tugas, dibawa serta |
| `gf5_primitive` | `exomatrix.matrix_order(v, 5)` | Modulus lain, ~5,2% positif — tidak terikat identitas apa pun ke jawaban GF(2) |
| `rank` | `exomatrix.gf2_rank(build_exomatrix(v))` | 0..5, JENIS pertanyaan berbeda (bukan ya/tidak) atas struktur 25-sel yang sama |

**Hasil terukur** (4.000 sekuens, 500 epoch, seimbang pada `gf2_primitive`,
natural n=17.220):

| | physics (5, beku) | baseline-5 (5, latih) | exomatrix (25, beku) | baseline-25 (25, latih) |
|---|---:|---:|---:|---:|
| parameter | 1.240 | 1.380 | 2.200 | 2.900 |
| `gf2_primitive` precision/recall | 0,970/0,125 | 0,955/0,137 | 1,000/0,004 | 0,536/0,144 |
| `gf5_primitive` precision/recall | 0,000/0,000 | 0,000/0,000 | 0,000/0,000 | **1,000/0,053** |
| `rank` akurasi (selalu-mayoritas 0,397) | **0,516** | **0,606** | **0,536** | **0,684** |

**Tiga temuan, tiga arah berbeda — dilaporkan sejujur Fase 0:**

- **`rank` adalah bukti nyata pertama bahwa satu trunk berguna untuk lebih
  dari satu jenis pertanyaan.** Keempat varian mengalahkan baseline
  selalu-mayoritas (0,397), termasuk `physics` yang cuma 5 angka beku —
  representasi yang sama yang membantu `gf2_primitive` juga membawa sinyal
  untuk pertanyaan aljabar yang sama sekali berbeda (rank, bukan orde).
- **`gf5_primitive` nyaris gagal total pada tiga dari empat varian** — bukan
  bug kalibrasi: dicek langsung, probabilitas mentah (sebelum kalibrasi)
  tidak pernah melewati 0,468, dan pemisahan kelas positif/negatif nyata
  tapi kecil (rata-rata 0,084 vs 0,056). Hanya `baseline-25` — kapasitas
  terbesar, tanpa prior — dapat sinyal sama sekali. Modulus 5 genuinely
  lebih sulit dipelajari arsitektur ini daripada modulus 2, pada skala ini.
- **`gf2_primitive` kira-kira mereproduksi Fase 0**, tidak identik (latihan
  bersama tiga tugas mengubah dinamika optimisasi dibanding latihan
  tunggal) — `baseline-25`'s precision turun dari 0,637 (Fase 0) ke 0,536
  di sini, sisanya dekat.

**Cara memeriksa:** `python3 -m hijaiyyah.nui.multitask` (menit, bukan
detik — `matrix_order` modulus 5 jauh lebih mahal dari modulus 2);
`pytest tests/test_ai/test_nui_multitask.py` (13/13, termasuk uji empiris
guard di atas dan satu bug yang ditemukan di tes ini sendiri saat ditulis:
asumsi "eksomatriks Jim rank penuh" ternyata salah — rank-nya 4, bukan 5,
diperbaiki begitu dijalankan, bukan diasumsikan benar).

---

## Fase 2 — Dari himpunan ke urutan: program HASM sungguhan, bukan cuma kumpulan huruf

**Kenapa ini melampaui Fase 1.** Fase 0 dan 1 memperlakukan input sebagai
**himpunan** huruf (sengaja — penjumlahan v18 komutatif, urutan tidak
mengubah label). Tapi program nyata (`rtl/programs/*.hasm`) adalah
**urutan instruksi**: `ADD`, `CGET`, `PRINT`, cabang — di sinilah urutan
justru menentukan segalanya. Kecerdasan yang cuma bisa menalar himpunan,
tidak pernah urutan, punya batas keras.

**Sumber data sudah ada, gratis, tak terbatas, dan berground-truth:**
`hijaiyyah.hisa.assembler.assemble()` mengubah teks `.hasm` jadi kata mesin;
`hijaiyyah.hisa.machine.HISAMachine.run()` menjalankannya sungguhan dan
`dump_state()` memberi keadaan akhir — mesin yang sama yang sudah dipercaya
`tools/integrity_benchmark.py`. Ini oracle kebenaran gratis: bangkitkan
program acak (dalam batas ISA, 96 opcode — `hisa.opcodes`), jalankan,
catat hasilnya. Tidak perlu manusia melabeli satu contoh pun.

**Langkah konkret:** ganti sum-pooling dengan encoder urutan kecil (RNN atau
transformer ringan) atas token opcode+operand, vocab dari `hisa.opcodes`.
Tugas yang terbuka olehnya: prediksi keadaan register akhir, prediksi
apakah suatu trap tersulut, prediksi cacah siklus (persis yang
`hcpu_gowin_top.v`'s wrapper hitung secara fisik — hubungan langsung ke sisi
perangkat keras proyek ini).

**Cara memeriksa:** akurasi terhadap `HISAMachine` sungguhan sebagai
ground truth, bukan simulator lain — program yang sudah ada di
`rtl/programs/` jadi set uji nyata pertama, bukan cuma data sintetis.

---

## Fase 3 — Fakta terverifikasi proyek ini sebagai sinyal, bukan sekadar angka

Sumber (sudah ada, sudah diverifikasi): cakupan guard 93,1%
(`matematika-hijaiyyah/GUARD.md`), sifat Jim (`cosmic-codex-jim/`),
properti Ka'bah (DU=4, NL=112, avalanche 0,5007, `crypto/sbox_logic.py`).

**(a) Pra-latih mandiri.** Kepala tambahan di `MultiTaskAccumulatorNet`,
dilatih sebelum/bersama tugas utama, dua tugas baru:
- prediksi byte keluaran S-box (`sbox_logic.substitute(x)`, 256 pasangan
  input→output, ground truth langsung dari fungsi itu, bukan dibangkitkan)
- prediksi kelas cakupan guard per subset huruf (`guards.full_guard_check`
  atas subset acak, label = lolos/gagal per guard)

Cara memeriksa: akurasi terhadap `sbox_logic.py`/`guards.py` dipanggil
langsung sebagai ground truth, sama seperti Fase 1's `exomatrix.matrix_order`.

**(b) Lapis retrieval.** `nui/atom.py`'s `ATOMS_BY_CHAR` + Master Table
sudah jadi index alamat→fakta. Tambahkan fungsi lookup (huruf → fakta
terverifikasi terkait, dibaca dari `GUARD.md`/`cosmic-codex-jim/` saat
build, bukan saat inferensi) yang dipanggil sebelum menjawab pertanyaan
tentang huruf itu.

Cara memeriksa: jawaban dicocokkan byte-demi-byte terhadap fakta di
sumbernya, bukan dinilai kualitatif.

Belum dibangun — `AT`. Langkah berikutnya: pilih (a) atau (b), bangun,
ukur, laporkan — pola yang sama dengan Fase 0/1.

---

## Fase 4 — Kompositional/generatif: sintesis program

Bukan memprediksi properti program yang sudah ada — **menghasilkan**
program HASM baru yang mencapai target: "sekuens akumulasi terpendek yang
mencapai primitivitas," "urutan yang lolos keempat guard."

**Langkah konkret.** `HISAMachine` sebagai oracle verifikasi: assemble?
jalan sampai HALT (bukan HALT_ERR)? target tercapai? Ruang aksi = 96
opcode `hisa.opcodes`. Reward = 1 kalau target tercapai dalam N langkah,
0 kalau tidak.

Cara memeriksa: program keluaran dijalankan lewat `HISAMachine` sungguhan,
target dicek langsung terhadap fungsi yang sama Fase 0/1 pakai
(`matrix_order` untuk primitivitas, `full_guard_check` untuk guard) —
bukan dinilai kualitatif.

Belum dibangun — `AT`.

---

## Fase 5 — NUI sebagai layanan Hybit

Syarat: salah satu dari Fase 1-4 cukup kecil untuk inferensi murah
(Fase 0's precedent: `physics`, 385 parameter beku, precision 0,970 —
mendekati `exomatrix`'s 1,000 dengan parameter jauh lebih sedikit;
`baseline-25`, 1.405 parameter terlatih bebas — TERBANYAK — precision
0,637, TERENDAH dari keempat varian).

**Langkah konkret.** Bobot terlatih (mis. Fase 1's `physics`, 1.240
parameter) dibekukan jadi tabel/fungsi tetap, dipanggil lewat `SYSCALL`
(opcode `0x09`, sudah dicadangkan di `hisa.opcodes`) dari program HASM —
pola pemanggilan yang sama `rtl/programs/hos.hasm`'s `hos_har_get` pakai
untuk layanan kernel lain (`CALL` ke rutin tetap, bukan `SYSCALL` itu
sendiri, tapi hierarki layanan yang sama).

Cara memeriksa: hasil `SYSCALL` dari HASM dicocokkan terhadap hasil
model Python yang sama, input yang sama — paritas, bukan perkiraan.

**Footprint bobot NUI vs masalah memori HCPU.** Fase 0's `physics` (385
parameter) = 1.540 byte @ float32; Fase 1's `physics` (1.240 parameter) =
4.960 byte @ float32, atau 1.240 byte @ int8 — muat di SATU macro SRAM
2 KB (`rtl/mpw/sky130_sram_macros/sky130_sram_2kbyte_1rw1r_32x512_8`),
tidak perlu susunan 16-macro yang `hcpu_dataram`'s 16 KB butuhkan
(rasio: dataram 3,3× lebih besar dari bobot NUI terbesar yang sudah
diukur). Bobot NUI sendiri BUKAN penyebab kebutuhan `sky130_sram_macros`.

`SYSCALL` di atas cuma berarti sesuatu di silikon nyata kalau HCPU
sendiri sudah tapeout — dan itu diblokir oleh `hcpu_dataram`'s 131.072
flip-flop yang tidak muat 700x700 um die (`rtl/mpw/MPW_SHUTTLE_PLAN.md`),
bukan oleh apa pun yang NUI butuhkan sendiri. Fase 5 bergantung ke HCPU
tapeout, HCPU tapeout bergantung ke `sky130_sram_macros`'s macro terpasang
di `hcpu_dataram`/`hcpu_memory` — rantai transitif, bukan kebutuhan NUI
langsung.

Belum dibangun — `AT`, bergantung Fase 1-4 dan HCPU tapeout
(`rtl/mpw/MPW_SHUTTLE_PLAN.md`).

**Satu potong dari rantai itu sudah di-mock dan diverifikasi; percobaan
menyambungkannya ke RTL nyata sudah dicoba dan TERUKUR GAGAL, bukan
"belum dikerjakan."** `nui/sram_mock.py`'s `TwinPortSRAM` memalsukan
protokol port macro SRAM yang divendor (`clk0/csb0/web0/wmask0/addr0/
din0/dout0` + `clk1/csb1/addr1/dout1`, "1rw1r" di setiap nama macro) —
diverifikasi langsung terhadap model perilaku Verilog sungguhan lewat
Icarus, bukan diasumsikan dari komentarnya. Ini masih benar dan berdiri.

Percobaan pertama menyambungkannya ke `hcpu_dataram` sungguhan
(`rtl/mpw/hcpu_dataram_sky130.v`, enam belas macro + dekoder alamat) SUDAH
dibangun dan diuji langsung terhadap `hcpu_dataram.v` asli — dekoding
alamat dan write-mask byte-lane TERBUKTI benar, tapi latensi baca TIDAK
cocok dengan kontrak satu-klik `hcpu_dataram.v` sendiri (butuh dua klik,
diukur langsung, bukan diasumsikan), dan bahkan pada latensi dua-kliknya
sendiri, akses back-to-back tanpa jeda (LOAD/STORE beruntun ke macro
berbeda — kode biasa, bukan kasus langka) memberi hasil salah di >95%
kasus pada uji diferensial 500 siklus. **Belum dikoneksikan ke
`config.json`** (masih `hcpu_dataram.v` asli) justru karena temuan ini —
lihat `rtl/mpw/MPW_SHUTTLE_PLAN.md` untuk rincian penuh dan akar masalahnya
(satu register `sel_r`/`re_r` tidak cukup untuk lebih dari satu akses yang
sedang "dalam penerbangan"). Menyambungkan macro sungguhan ke pipeline
HCPU kemungkinan butuh PERUBAHAN PIPELINE (stall untuk LOAD/STORE, atau
tahap memori direstrukturisasi) — bukan sekadar penggantian modul.

---

## Ringkasan

| Fase | Apa | Aset yang dipakai (sudah ada) | Label |
|---|---|---|---|
| atom | Satu alamat (indeks↔opcode↔ROM), dua wujud (software+fisik) | `hisa.opcodes`, `hcpu_execute.v`, `nui_embedding.hasm` | **CC — selesai, fondasi di bawah semua fase** |
| clockwork | Mekanisme berurutan (bukan jaringan saraf): satu tick per huruf, ground true/false per tick, dinamai boot→bend→emit (`automate()`) | `exomatrix.compose_step`, `gf2_rank`, `matrix_order_of` | **CC — selesai**, belum di perangkat keras |
| rack | 28 huruf sebagai bank kode (chip = node+data), jalur antar-node bernama (`Channel`) | `nui.atom`, `nui.features` | **CC — selesai** |
| for-load | Huruf beralamat dikirim lewat loader (bukan bitstream), lulus percobaan pertama | `rtl/tb/tb_gowin_loader_nui.v`, `sim_loader_nui` | **CC — selesai** |
| freeze mode | Protokol kabel loader dipalsukan (bukan jamnya) -- klaim fisik yang sama, milidetik bukan detik | `nui/freeze.py`, `HISAMachine.rx_queue` | **CC — selesai** |
| rank_permutations | 1000 urutan acak rack, di-ranking per full-rank/primitive tick -- 999/1000 berakhir final_rank 0 | `clockwork.rank_permutations`, `random.Random(seed)` | **CC — selesai** |
| 0 | Satu klasifikasi, 4 varian embedding | `features.py`, `dataset.py`, `model.py` | **CC — selesai** |
| 1 | Multi-task: GF(2) + GF(5) + rank, satu trunk | `exomatrix.matrix_order(p=5)`, `gf2_rank` — guard dicoret, terbukti trivial | **CC — dicoba, hasil campuran** |
| 2 | Urutan program HASM sungguhan | `hisa.assembler`, `hisa.machine.HISAMachine`, `hisa.opcodes` (96 token) | AT |
| 3 | Fakta terverifikasi sebagai sinyal/retrieval | `cosmic-codex-jim/`, `matematika-hijaiyyah/GUARD.md`, `crypto/cube.py` | AT, arsitektur belum diputuskan |
| 4 | Sintesis program (generatif) | `HISAMachine` sebagai oracle reward | AT, riset terbuka |
| 5 | NUI sebagai layanan Hybit (`SYSCALL`) | H-Kernel, HAR, pola `hos_har_get` | AT, bergantung 1-4 |

Fase 1 naik ke `CC` bukan karena semuanya berhasil — `gf5_primitive` nyaris
gagal total pada tiga dari empat varian — tapi karena diukur, dilaporkan,
dan `rank` memberi bukti nyata pertama bahwa satu trunk membawa sinyal
lintas pertanyaan. `CC` = "dijalankan dan diperiksa," bukan "semuanya
bagus." "Umum" di judul berkas ini = *lebih dari satu tugas tetap*.
