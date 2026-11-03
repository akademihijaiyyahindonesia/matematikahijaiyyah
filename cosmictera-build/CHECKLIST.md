# Daftar cek

Setiap ✅ di bawah ini **dijalankan**, bukan diingat. Kolom terakhir adalah
perintahnya: salin, jalankan, dan Anda mendapat centang yang sama atau tahu
persis apa yang berubah.

Sebuah baris hanya boleh hijau kalau ada pemeriksaan otomatis yang lulus
**sekarang**. Tidak ada centang untuk "sudah ditulis", "pernah jalan", atau
"tinggal sedikit lagi".

---

## Perkakas

| | apa | perintah |
|---|---|---|
| ✅ | Python, pytest, ruff, mypy | `python3 -m pytest --version` |
| ✅ | Icarus Verilog | `iverilog -V` |
| ✅ | yosys | `yosys -V` |
| ✅ | nextpnr-himbaechel | `nextpnr-himbaechel --version` |
| ✅ | gowin_pack | `gowin_pack --help` |
| ✅ | openFPGALoader | `openFPGALoader --Version` |

Kelimanya terpasang di `~/opt/oss-cad-suite`. Satu perintah memeriksa semuanya:
`make -C rtl/fpga/gowin tools`.

---

## Kebersihan pohon

| | apa | perintah |
|---|---|---|
| ✅ | **6.347 tes terkumpul** † | `python3 -m pytest --collect-only -q` |
| ⬜ | lari penuh keluar 1 — hasilnya di † | `python3 -m pytest -q` |
| ✅ | ruff bersih | `make lint` |
| ✅ | mypy bersih, 178 berkas | `make typecheck` |
| ✅ | Master Table utuh | `make verify` |
| ✅ | Citra ROM terbangkitkan | `make rom` |
| ✅ | ROM cocok dengan tabel | `python3 rtl/scripts/cross_verify_rom.py` |
| ✅ | Suite deterministik | 40 jalan berturut `test_memscan`, 0 gagal |

† Cacah **terkumpul** kini dijaga; cacah **lulus** tidak bisa. Catatan ini
pernah berbunyi "satu-satunya angka yang tidak dijaga ... tidak bisa diperiksa
tanpa menjalankan pytest di dalam pytest", dan separuhnya keliru:
`pytest --collect-only -q` mencacah 6.347 dalam ±12 detik tanpa menjalankan satu
tes pun. Selama tak dijaga, ketiga berkas hanyut sendiri-sendiri — halaman ini
mengatakan 4.565 sementara [ON.md](ON.md) dan [README.md](README.md) tertinggal
di 4.454. `test_build_list.py` sekarang mencacah ulang dan menuntut ketiganya
sama. Yang tetap tak terjaga hanyalah berapa yang **lulus**: untuk itu memang
harus menjalankan pytest, dan perintah di sebelahnya yang jadi kebenarannya.
Hasil lari penuh terakhir ditulis di satu tempat saja: bagian
[Lari terakhir](#lari-terakhir) di akhir halaman ini.

**Angka "0 dilewati" yang dulu tertulis di baris pytest pun sebuah koreksi.** Empat
tes dulu melewati diri sendiri dengan pesan `not present` — dokumen paten di
`Matematika Hijaiyyah/OFFICIAL_PATENT_RELEASE/`, folder yang sudah berganti nama
jadi `Buku Matematika Hijaiyyah/`. Berkasnya ada sepanjang waktu; yang tidak ada
adalah jalurnya. Sebuah instrumen hukum berhenti diperiksa karena sebuah
direktori diganti nama — persis kegagalan yang `test_authorship.py` ada untuk
mencegahnya. Kini jalurnya di-glob, bukan disebut, seperti `test_bab_satu.py`
sudah lakukan.

**Dan "0 dilewati" hanya benar di mesin yang memegang naskah dan
bitstream-nya.** Pada checkout bersih repositori ini — diukur di worktree
terpisah pada `0a910f0` — **0 gagal dan 23 dilewati**, dan setiap yang
dilewati disengaja: 9 membutuhkan PDF buku (`test_book_anchor.py`,
`test_bab_satu.py`, `test_bab_dua.py`), 13 membutuhkan `CERTIFICATE.json`
serta dokumen `OFFICIAL_PATENT_RELEASE/` (`test_authorship.py`) — keduanya
di `Buku Matematika Hijaiyyah/`, yang `.gitignore` tahan dari riwayat
publik — dan 1 membutuhkan bitstream yang sudah dibangun (`test_rack.py`),
karena berkas `.fs` adalah keluaran build, bukan isi repositori. Tak satu
pun menandakan cacat; yang berbeda hanya apa yang ada di disk.

Baris terakhir bukan hiasan. `test_every_clue_is_distinctive_enough_to_be_worth_having`
mengambil `os.urandom` lalu menuntut penanda tidak muncul di dalamnya — dua
penanda panjangnya 3 byte, jadi suite gagal kira-kira **1 dari 127 jalan**.
Berkas itu sendiri sudah menulis pelajarannya satu fungsi di atasnya. Sekarang
sifatnya diasersi secara aritmetika dan deraunya berbenih.

---

## Perangkat keras — simulasi

| | apa | perintah |
|---|---|---|
| ✅ | **408 asersi, 39 bench, 0 gagal** | `make -C rtl/tb all` |
| ✅ | ROM 28 huruf | `make -C rtl/tb sim_rom` |
| ✅ | Guard G1–G4, T1–T2 | `make -C rtl/tb sim_guard` |
| ✅ | Codex ALU | `make -C rtl/tb sim_codex_alu` |
| ✅ | HISAB, sapuan 28 huruf | `make -C rtl/tb sim_hisab` |
| ✅ | Integrasi top-level | `make -C rtl/tb sim_top` |
| ✅ | Unit trap, 6 penyebab | `make -C rtl/tb sim_trap` |
| ✅ | MMIO, timer, UART RX | `make -C rtl/tb sim_mmio sim_timer sim_uart_rx` |
| ✅ | **H-Kernel: tiga proses + daemon guard** | `make -C rtl/tb sim_kernel` |
| ✅ | **Shell: perintah masuk lewat UART, jawaban keluar lewat kernel** | `make -C rtl/tb sim_shell` |
| ✅ | **Bayangan redirect: di mana interupsi menyimpan `epc` = 0** | `make -C rtl/tb sim_redirect_shadow` |
| ✅ | **Jarak `STORE TRAP_EPC` sebelum `ERET`: nol pun benar** | `make -C rtl/tb sim_epc_eret` |
| ✅ | **FLAGS milik prosesnya, melewati preemption** | `make -C rtl/tb sim_flags_ctx` |
| ✅ | **`EMITS` mencetak `Hijaiyyah`, penutup menghentikan** | `make -C rtl/tb sim_emits` |
| ✅ | **HFS create → write → read → verify, di RAM** — persistensi terbukti tersimulasi, mati daya fisik masih terbuka, lihat [OFF.md](OFF.md) | `make -C rtl/tb sim_hfs_lifecycle` |
| ✅ | **SDIO 1-bit: init, baca, tulis, baca ulang, dan N_CC 8 clock** — model kartu memeriksa CRC7, menolak transfer sebelum CMD7, dan menjatuhkan perintah yang datang kepagian; disabotase gap 7 → merah | `make -C rtl/tb sim_sdio` |
| ✅ | **Kartu dicapai sebuah program, bukan kabel bench** — `sdio_write.hasm` jalan di pipeline dan menyentuh `0xFE0`–`0xFE4` lewat `LOAD`/`STORE`; kartu model menyimpan polanya, satu CMD17 dan satu CMD24 | `make -C rtl/tb sim_sdio_prog` |
| ✅ | **28 instruksi huruf** | `make -C rtl/tb sim_letters` |
| ✅ | **`CALL`/`RET`, sarang 8 tingkat** | `make -C rtl/tb sim_subroutine` |
| ✅ | **I/O lewat kernel, dua sisi** | `make -C rtl/tb sim_syscall_io` |
| ✅ | Wrapper papan | `make -C rtl/tb sim_board` |
| ✅ | Boot lewat kabel | `make -C rtl/tb sim_loader` |
| ✅ | **Cabang & interupsi bertabrakan** | `make -C rtl/tb sim_branch_trap_race` |
| ✅ | **HOS: heap, HFS guard-on-write, HAR** | `make -C rtl/tb sim_hos` |
| ✅ | NUI: penjumlahan embedding fisika (titik/garis/lengkung/theta/rho) | `make -C rtl/tb sim_nui_embedding` |
| ✅ | NUI: opcode huruf (L_JIM/L_KHA) dimuat lewat kabel loader, bukan disintesis langsung | `make -C rtl/tb sim_loader_nui` |
| ✅ | Video timing generator (hsync/vsync/de) cocok persis standar VESA 640x480@60Hz | `make -C rtl/tb sim_video_timing` |
| ✅ | **Renderer teks 160×90** — generator karakter menoleh dua siklus ke depan, dan sebuah probe pada `ink` internal membuktikan bench-nyalah yang dulu mencuplik satu pixel terlambat, bukan renderernya | `make -C rtl/tb sim_text_render` |
| ✅ | **Compositor memilih sel, bukan menulisnya** — seluruh 14.400 sel disapu dan dihitung: tepat 113 diklaim, sisanya milik layout ROM; tanpa snapshot keenam field hidup berbunyi `NOT INSTRUMENTED`, bukan angka | `make -C rtl/tb sim_dashboard` |
| ✅ | **Snapshot telemetri lintas domain clock** — handshake req/ack, jadi yang terbaca satu potret utuh dan bukan campuran dua siklus | `make -C rtl/tb sim_telemetry` |
| ✅ | **Tombol mode memilih halaman** — debounce, tekan panjang, dan pembungkusan halaman | `make -C rtl/tb sim_page_key` |
| ✅ | **Register codex selamat melewati trap** — handler menjalankan satu `HLOAD` dan H0 pemanggil tetap utuh karena handler menyimpannya lewat perangkat lunak (`hos_hctx.hasm`, 72 instruksi, 0 LUT4); merah kalau kedua `CALL` simpan/pulihkan dicabut, dan memakai Kaf karena hanya huruf itu yang H\*-nya 1 | `make -C rtl/tb sim_trap_hreg` |
| ✅ | **Syscall HFS dari mode pengguna: create → write → read → verify, di RAM**, lewat kernel — sebuah proses memanggil HFS_CREATE, HFS_WRITE (Kaf), lalu HFS_READ dan mendapat kembali vektor yang ditulisnya; lalu di-commit ke kartu — MAGIC `HFS1`, VERSION 1, entri berkas, dan data sektor 2 dibaca langsung dari memori model kartu dan harus sama dengan blok RAM; merah bila `sc_ret` mempercayai R7 melewati `hos_alloc` (CREATE mengembalikan 6) dan bila heap tidak diinisialisasi (ketiganya 0) | `make -C rtl/tb sim_hfs_syscall` |
| ✅ | **`SYSCALL` 9 melintasi sebelas sektor, tersimulasi** — container-nya shell itu sendiri: 1.248 kata, 124 relokasi, 1.379 kata = 11 sektor; header + tabel = 131 kata, jadi **tabel relokasi dan kata program sama-sama menyeberang batas sektor**. Seluruh 1.248 kata di `IMEM` = keluaran perakit di 0x900. Merah bila tabel tidak pindah sektor dan bila kata program tidak pindah sektor — dua sabotase yang **tidak terlihat** oleh bench satu-sektor | `make -C rtl/tb sim_prog_load_multi` |
| ✅ | **`SYSCALL` 9 memuat program dari kartu, tersimulasi** — proses mode pengguna meminta PROGRAM_ID 1; kernel membaca tabel sektor 16, memeriksa MAGIC `HPG1`, VERSION, batas memori, ENTRY, dan **jumlah 32-bit sebelum satu kata pun ditulis**, menyalin tabel relokasi ke 0x300, lalu menulis `IMEM` sambil menambahkan LOAD_ADDR. Citra dibandingkan dengan keluaran perakit di alamat itu (`build_container.py --image`); merah bila satu kata di kartu dirusak (ditolak, 0) dan bila relokasi tidak diterapkan | `make -C rtl/tb sim_prog_load` |
| ✅ | **Container program mendarat di kartu, empat sektor, satu ACK per sektor, tersimulasi** — `sd_writer.hasm` mencetak `0` begitu kartu siap, lalu jumlah sektor tertulis sesudah tiap sektor; bench berlaku seperti `send_container.py`: tunggu `0`, kirim 128 kata, tunggu ACK. Container-nya `test_hfs` @0x200, 437 kata — **yang dulu membuat papan diam**. Kabel `0 1 2 3 4`, lalu `1 4`; sektor 17–20 kata demi kata, tabel `1, VALID, 17, 4`, sektor 21 tak tersentuh. Tanpa menunggu ACK, simulasi **mereproduksi kegagalan papan**: kata ke-128 mendarat `0001310b` alih-alih `11aa0e80` dan tabel tak pernah ditulis | `make -C rtl/tb sim_sd_writer` |
| ✅ | **HFS melewati reboot lewat kartu, tersimulasi** — boot 1 membuat berkas dan menulis Kaf; CPU di-reset dan **seluruh RAM data dinolkan**, kartu dibiarkan; boot 2 memuat HFS dari kartu dan menemukan Kaf. Kabel serial membaca `1 1 1` di boot 1 dan `2` di boot 2 — angka yang sama yang dibaca di papan. Merah bila tabel tak dimuat dari kartu (boot 2 fase 1) atau data tak di-commit (fase 3); merah bila hasil CREATE tak dilaporkan (kabel `11`) dan bila boot tanpa `hos_fs_mount` (kabel `1 0 0` dua kali); **hijau palsu** bila RAM tidak dinolkan, terukur — `hcpu_dataram.v` tidak mengosongkan diri saat reset. Mati daya fisik: dijalankan di papan 18 September 2026, lihat [PAPAN.md](PAPAN.md) | `make -C rtl/tb sim_hfs_persist` |

Lima baris tebal itu baru hijau **hari ini**, dan semuanya sempat berbohong:

- **H-Kernel** hijau karena `B = 127400 = 1274 × 100`. Kelipatan yang bersih
  hanya mungkin bila R1 milik B tak pernah memegang nilai A.
- **Instruksi huruf** hijau karena `||Ba+Sin+Mim||² = 112` lewat jalur huruf —
  angka yang sama yang sudah dibuktikan jalur HLOAD/HCADD. Sebelum hari ini
  jawabannya **0**: `default:` kedua di tengah `case` membuat kedua puluh
  delapan opcode menulis nol, dan tak ada bench yang pernah menjalankan satu
  pun. Enam bench di kolom ini juga tidak punya target `make` sama sekali.
- **`R0`-`R17` bukan enam belas register — kecuali dua tak pernah bisa
  dipakai.** Buku sendiri berkontradiksi: §IIIJ.3.3.1 (hal. 133) memberi GPR
  bank 18 register, R0–R17, bahkan menugaskan R17 sebagai register tautan.
  §IIIF.3.3.1 (hal. 127), format word instruksi, memberi tiap field register
  **4 bit** — tidak bisa menamai lebih dari 15. Assembler dulu memangkas
  dengan `& 0xF` alih-alih memeriksa, jadi `MOVI R16, 7` terakit **identik**
  dengan `MOVI R0, 7`, diam-diam. Kernel yang barusan dibangun sebelum
  temuan ini menyimpan "18 register" per proses — sebenarnya menyimpan R0
  dan R1 dua kali, kebetulan tak merusak apa pun karena mendorong lalu
  memuat nilai yang sama dua kali adalah no-op. Sekarang assembler menolak
  R16/R17 dengan pesan yang mengutip kedua bagian buku, dan kernel menyimpan
  enam belas yang sungguh ada — lihat `MAX_GPR` di
  `src/hijaiyyah/hisa/assembler.py` dan
  [`test_the_code_follows_the_field_width_not_the_count`](../tests/test_integrity/test_book_anchor.py).
- **Cabang yang diambil bisa kalah dari interupsi yang bertepatan — dan
  epc-nya salah, bukan cabangnya.** Ditemukan lewat daemon penjaga: sebuah
  `JGD` yang baru saja lulus guard-nya kembali ke jalur "guard gagal", sekali
  dalam 400.000 siklus. Sebabnya: `pc_now` (yang disimpan interupsi
  maskable sebagai alamat kembali) memakai `if_pc` — tebakan sekuensial
  spekulatif Fetch, satu tahap di depan Execute yang justru sedang
  menyelesaikan cabang itu SAAT itu juga. Jika interupsi tiba tepat di
  siklus itu, `if_pc` masih menunjukkan alamat jatuh-lanjut cabang, bukan
  targetnya — dan cabang itu tak pernah "diputar ulang": efek sampingnya
  (misalnya dorongan stack alamat-kembali `CALL`) sudah terlanjur commit.
  Diperbaiki dengan satu mux: `branch_taken_w ? branch_target_w : if_pc`.
  `tb_hcpu_branch_trap_race.v` mereproduksinya sesuai permintaan, dengan
  menyapu tenggat timer sampai bertepatan persis dengan siklus Execute —
  bukan menunggu 1-dari-532 keberuntungan.
- **FLAGS tidak punya write-through — GPR dan H-Reg punya.** Ditemukan lewat
  HOS: `CMP R1,R2` untuk dua alamat heap yang genuinely berbeda (3587,
  3594) menghasilkan Z=1 (salah — seharusnya 0) tepat di titik `JNE`
  membacanya. `hcpu_regfile.v` punya baris eksplisit "GPR read (with
  transparent write-through)" untuk GPR dan H-Reg —
  `gpr_rdata1 = (gpr_we && gpr_waddr==gpr_raddr1) ? gpr_wdata : gpr[...]` —
  tapi FLAGS hanya `assign flags_out = flags;`, murni nilai teregister
  siklus lalu, tanpa bypass. Rantai forward di `hcpu_execute.v`
  (`forwarded_flags`) menutupi konsumen 1-2 tahap di belakang produsen
  (EX-forward, MEM-forward) lalu jatuh ke `current_flags` — dan `current_flags`
  itulah yang, tanpa write-through, tetap basi tepat di siklus tulisannya
  sendiri commit. Celah ini sempit: **setiap** pasangan CMP-lalu-cabang yang
  sudah ada di seluruh repositori ini berdampingan langsung (jarak nol
  instruksi), selalu masuk jendela EX-forward, tak pernah menyentuh
  register ini sama sekali. `hos_alloc` adalah kode pertama yang punya satu
  instruksi di antara perbandingan dan cabangnya, DAN cukup stall (dari
  interlock load-use pada dua LOAD berurutan) untuk menaruh pembacaan
  cabang itu tepat di siklus tabrakan. Diperbaiki dengan satu baris,
  menyalin pola GPR persis: `assign flags_out = flags_we ? flags_in : flags;`
  Direproduksi minimal di `tb_hcpu_hos.v` dan seluruh 18 bench tetap hijau
  sesudahnya.

---

## Perangkat keras — sintesis

| | apa | perintah |
|---|---|---|
| ✅ | **Bitstream HCPU, Tang Nano 20K: 74% LUT4, 120,63 MHz** | `make -C rtl/fpga/gowin bitstream` |
| ✅ | **Bitstream Ka'bah, Tang Nano 20K: 72% LUT4 dengan lapis 3 (HMAC-SHA256, kunci uji)** — tanpa lapis 3: 58% LUT4, 165,98 MHz | `make -C rtl/fpga/gowin kabah_bitstream` |
| ✅ | **`CSET` (0x45) dijalankan di papan: `5 6 2 0`** | `make -C rtl/fpga/gowin bridge` lalu `make -C rtl/fpga/gowin send PORT=<port> PROG=../../programs/test_cset.hasm` |
| ✅ | **HFS baca mengembalikan H-Reg hidup di papan: `1 1 1 2 1`** | `make -C rtl/fpga/gowin send PORT=<port> PROG=../../programs/test_hfs.hasm` |
| ✅ | **Kartu MicroSD bertahan melewati mati daya: `1 1 1 10`** — SDIO 1-bit, LBA 1; lima checkpoint `10` → `1 1 0 10` → `1 1 1 1 10` → reset → mati daya ([PAPAN.md](PAPAN.md)) | `make -C rtl/fpga/gowin bridge` lalu `send PROG=../../programs/sdio_verify.hasm` |
| ✅ | **HFS melewati mati daya di papan: `1 1 1` → kabel dicabut → `2`** — CREATE dan WRITE dari mode pengguna menulis tembus ke kartu, boot memuat HFS dari kartu; banner LiteX pabrikan di rekaman membuktikan daya memang putus ([PAPAN.md](PAPAN.md)) | `make -C rtl/tb shell_persist.hex`, `make -C rtl/fpga/gowin PROGRAM=../../tb/shell_persist.hex bitstream`, lalu `openFPGALoader -b tangnano20k rtl/fpga/gowin/hcpu_gowin_top.fs` dan baca UART 115200 |
| ✅ | **Slot CPU hasil pemisahan dijalankan di papan: 23 byte, `112`, `CYCLES=00001B89`** | `make -C rtl/fpga/gowin bitstream` lalu `openFPGALoader -b tangnano20k rtl/fpga/gowin/hcpu_gowin_top.fs`, dan baca UART 115200 — bangun dulu, karena berkas itu membawa `PROGRAM` mana pun yang terakhir dipanggang |
| ✅ | **Papan boot dari kartu tanpa masukan host: `1 2 3`, dua kali** — pemuat dipanggang ke bitstream, host hanya mendengar; 579.255 siklus (21,5 ms) dari konfigurasi sampai halt. Bitstream masih dimuat lewat JTAG ke SRAM ([PAPAN.md](PAPAN.md)) | `make -C rtl/fpga/gowin PROGRAM=../../programs/test_prog_run.hasm bitstream`, muat, baca UART 115200, lalu `make -C rtl/fpga/gowin program.hex` |
| ✅ | **Program dari kartu berjalan di papan: `1 2 3`** — dimuat, direlokasi, lalu diserahkan lewat `TRAP_EPC`+`ERET`; container yang dirusak menjawab `0` dan tidak dijalankan. Gelungnya ditutup `JMP` (absolut), jadi angka itu juga membuktikan relokasi diterapkan; sabotase yang menghapusnya memberi `111` ([PAPAN.md](PAPAN.md)) | `make -C rtl/tb sim_prog_run` |
| ✅ | **Lab serangan, sasaran loader, CHECKSUM32 (K-8, K-10): 19 kasus di papan, 0 temuan** — 15 ditolak, 4 diterima sesuai maksudnya: container utuh, kata sesudah container, dan dua batas sebuah jumlah (kata ditukar, badan diubah lalu disegel ulang). `words_plus_one` dan `reloc_index_moved`, yang lolos di versi 1 pada 20 September, kini ditolak. Dua kasus lagi (entri tabel lain, sektor lain) tak bisa ditulis `sd_writer` dan diperiksa di Python dan simulasi. Pembangkit `jim_stream.py`, periode 31 dan 3.124 terukur ulang ([attack-lab/](attack-lab/README.md)) | `python3 rtl/scripts/attack_lab.py --target loader --port <port>`; `pytest tests/test_integrity/test_checksum32.py tests/test_integrity/test_attack_lab.py` |
| ✅ | **Lab serangan kelas A, latensi Jamrah: 33 clock untuk setiap satu dari 256 byte, lima lari identik byte demi byte** — kontrolnya, predikat sama ditulis sebagai gelung banding, menyebar 13–232 clock di 29 nilai, jadi alat ukurnya terbukti bisa melihat perbedaan (R3). `jamrah_gate.hasm` tidak disentuh ([attack-lab/](attack-lab/README.md)) | `python3 rtl/scripts/attack_lab.py --target jamrah --runs 5 --port <port>` |
| ✅ | **Lab serangan kelas C, Ka'bah di luar bit tunggal: difusi tetap ~0,5 dari 1 sampai 64 bit yang dibalik** — 0,4984 / 0,5035 / 0,5006 / 0,4984 / 0,5011 / 0,5016 / 0,5061 dari 1.600 bit, 56 pasang, 0 kegagalan integritas; permutasi 4 blok memindahkan keadaan akhir 0,4975. Frame terpotong **tidak ditolak**: wrapper tak punya field panjang, jadi 64+64 byte tersambung jadi satu frame ([attack-lab/](attack-lab/README.md)) | `python3 rtl/scripts/attack_lab.py --target kabah --trials 8 --port <port>` |
| ✅ | **Lab serangan kelas D, aliran codex jadi sumber kasus: 16/16 kata program yang dirusak ditolak loader, dan Ka'bah memberi angka yang sama seperti sumber acak** — 0,5046 bit tunggal, 0,4953–0,5055 untuk 2–64 bit. Aliran terstruktur tidak menemukan yang tidak ditemukan acak, pada ukuran ini ([attack-lab/](attack-lab/README.md)) | `python3 rtl/scripts/attack_lab.py --target loader --source jim5 --cases 16 --port <port>`; `--target kabah --source jim5 --trials 8` |
| ✅ | **Burn-in tingkat 1 tutup: 24 jam, 0 error, 0 baca kartu gagal** — 54.893 detak dipancarkan papan, 56.210.432 siklus, dan kerja terhadap jam papan sendiri **1,0002**, yang menutup titik buta lima belas diam milik host. Garis dasar beku: 650,4 siklus/detik, irama detak 1,5744 s, hanyut −0,0292 s/jam ([burn-in/](burn-in/README.md)) | `python3 rtl/scripts/burn_in.py --port <port> --hours 24 --label 24h`; `python3 rtl/scripts/burn_in_report.py <id>.jsonl --write` |
| ✅ | **Lab burn-in berjalan di papan: siklus pertama 28 / 3072 / 178 dan kartu menjawab `HFS1`** — gerbang Jamrah, ke-28 vektor codex, enam belas kata memori, `PUSH`/`POP`, dan **sektor 1 dibaca, bukan klaim HFS** — kata pertamanya dibandingkan, berulang; dua temuan keluar dari membangunnya (`PRINT` salah untuk angka besar; kartu gagal init sesudah rekonfigurasi di tengah pembacaan, 8 dari 8) ([burn-in/](burn-in/README.md)) | `python3 rtl/scripts/burn_in.py --port <port> --hours 24 --label 24h`; `pytest tests/test_integrity/test_burn_in.py` |
| ✅ | **Ka'bah di papan: avalanche 0,4995 dari 1.600 bit, 8/8 frame dan 32/32 masukan termutasi cocok `cube.py`** — spons berantai (frame sama dua kali tanpa reset memberi keadaan berbeda), deterministik sesudah rekonfigurasi, 73/73 keadaan yang seharusnya berbeda memang berbeda. Lapis 2 [EH]; keamanan ada di lapis 3 ([validasi/KABAH.md](validasi/KABAH.md)) | `python3 rtl/scripts/kabah_board.py <port> --avalanche 32`; `pytest tests/test_integrity/test_kabah_board.py` |
| ✅ | **Hijrah di papan: 700/700 nilai muka, 24 / 27 / 28 / 28 dan 321 / 649 / 625 / 714 atas mod 2 / 3 / 4 / 5, tiga lari identik** — HCPU membangun ke-28 muka dari ROM-nya sendiri dan menghitung peta berbeda; empat pasang yang runtuh atas mod 2 keluar dari silikon sebagai ح–ل, ش–ن, ص–ق, ع–ي. Hitungan panjang ≤ 2 diikat ke `_reachable` milik `test_hijrah.py` ([validasi/HIJRAH.md](validasi/HIJRAH.md)) | `python3 rtl/scripts/hijrah_board.py <port>` di atas loader; `pytest tests/test_integrity/test_hijrah_board.py` |
| ✅ | **Jamrah di papan: 256/256 byte, pulse dan ketujuh simpul, lima lari dari lima** — program dibangkitkan dari `jamrah_gate.hasm`, dibandingkan dengan `jamrah_vectors.txt`; 9.218 clock per 256 byte, identik tiap lari. Gerbang RTL-nya **tidak** di papan: di slot Ka'bah ia dipangkas habis ([validasi/JAMRAH.md](validasi/JAMRAH.md)) | `python3 rtl/scripts/jamrah_board.py <port>` di atas loader; `pytest tests/test_integrity/test_jamrah_board.py` |
| ✅ | **Shell naik dari 11 sektor kartu di papan dan menjawab kabel: `HIJAIYYAH`, lalu `A`→`A`, `p`→`2 0 1`** — container 1.377 kata ditulis dengan ACK per sektor (`1` … `11`, lalu `1 11`), dimuat dengan 125 relokasi yang tabelnya sendiri menyeberang sektor, lalu dijalankan. Container 4 sektor yang dulu membuat papan diam kini `1 4` ([PAPAN.md](PAPAN.md)) | `send_container.py <port> <container.hex> --writer ../../programs/sd_writer.hasm`, lalu `send PROG=../../programs/test_prog_run.hasm` |
| ✅ | **Loader membaca container dari kartu di papan: `1`, dan `0` untuk citra yang dirusak** — enam lari berurutan, kontrolnya ikut dijalankan: satu kata di container diganti `DEADBEEF` dan papan menolak ([PAPAN.md](PAPAN.md)). **Tidak** mengklaim isi memori instruksi benar: tidak ada port baca | `make -C rtl/fpga/gowin bridge` lalu `send PROG=../../programs/sd_writer.hasm` diikuti containernya, lalu `send PROG=../../programs/test_prog_load.hasm` |
| ✅ | **Blok codex (`CMOV` `CZERO` `CEQ` `CRHO` `CU` `CMOD4`) di papan: `8 0 0 1 1 0 1 5`** | `make -C rtl/fpga/gowin hdmi_bridge` lalu `make -C rtl/fpga/gowin send PORT=<port> PROG=../../programs/test_codex.hasm` |

**Kalimat ini dulu berbunyi "belum ada `openFPGALoader` yang benar-benar
dijalankan terhadap perangkat keras dalam sejarah repositori ini". Itu tidak
lagi benar sejak 10 September 2026.** Kedua bitstream dipanggang ke papan
fisik dan dijalankan: HCPU mencetak `112` lalu `CYCLES=00001B89` di kabel
serial — 7.049 siklus, byte-per-byte identik dengan `make sim` — dan Ka'bah
mengembalikan 2/2 frame, 400/400 byte cocok dengan `cube.py`. Kedua angka
Fmax di atas adalah pengukuran ulang **pasca** bring-up, bukan angka pra-papan
yang digantikannya (114,65 dan 117,91): keduanya naik karena penyerempak reset
berhenti menggerbangi level pin 87 (MODE1) yang ditahan rendah oleh papan.

**Angka HCPU diukur ulang dua kali pada 13 September.** Sesudah `pc_valid`
berhenti diikat tinggi: 115,66 → 120,31 MHz, 14.714 → 14.726 LUT4, DFF naik
**satu** — tepat satu bit keadaan. Lalu sesudah `TRAP_EPC` mendapat bypass yang
sama dengan `TRAP_MODE`: 120,31 → 114,50 MHz, 14.726 → 14.746 LUT4, DFF **tidak
bergerak** — ia mux, bukan register. Sebelumnya, 12
September setelah blok codex: 84,26 → 115,66 MHz, 14.231 → 14.714 LUT4, DFF
tidak bergerak sama sekali — keenam opcode tidak menambah state. Jalur kritis yang dilaporkan
nextpnr masih di dalam Execute: berangkat dari `ex_gpr_we`, lewat `codex_hvec`
dan `would_addr`, berakhir di `ex_gpr_result`. Kenaikan Fmax tidak dipisah
antara desain dan penempatan, dan run ini tidak mengklaimnya. Yang tidak
berubah: papan menjalankannya, dan clock papan 27 MHz. (Pengukuran 11
September, setelah `CSET`: 118,43 → 84,26 MHz, 14.005 → 14.231 LUT4.)
Apa yang benar-benar keluar dari papan dicatat di [PAPAN.md](PAPAN.md); yang
masih belum ada di [ROADMAP.md](ROADMAP.md).

---

## Matematika dan angka

| | apa | bukti |
|---|---|---|
| ✅ | 28 huruf kanonik dari PDF bersegel | `make verify` |
| ✅ | Closure monoid dibuktikan, bukan disampel | `tests/test_algebra/` |
| ✅ | Cakupan guard **93,1%**, dan itu langit-langitnya | `matematika-hijaiyyah/GUARD.md` |
| ✅ | Throughput **2,59 MB/s**, hambatan = deserialiser | `src/hijaiyyah/crypto/kabah.py` |
| ✅ | 84 dari 105 opcode di RTL, 21 sisanya dinamai | [OFF.md](OFF.md) |

---

## Belum hijau

Satu, dan itu dinamai supaya centang di atas berarti sesuatu.

| | apa | keadaan |
|---|---|---|
| ⬜ | `python3 rtl/scripts/lint_hcpu.py` | **0 error struktural** (dulu 1), sisa **76 peringatan** — keluar bukan-nol |

Error Verilator hilang justru karena `default:` ganda itu diperbaiki — jadi
lint yang selama ini merah sebenarnya sedang menunjuk cacat huruf, dan tak ada
yang membacanya. Peringatan yang tersisa soal bit yang tak terpakai.

Bitstream pindah dari baris ini ke bagian hijau di bawah: desain muat dan
terrout di Tang Nano 20K (**75% LUT4, 116,44 MHz**, diukur 14 September),
papan di-flash, dan UART membalas 23 byte yang cocok byte-per-byte dengan
simulasi.
Rekamannya di [PAPAN.md](PAPAN.md).

---

## Satu tarikan napas

```bash
make -C rtl/fpga/gowin tools     # 5/5 perkakas
make lint typecheck verify rom   # bersih
python3 -m pytest -q             # 6.347 tes terkumpul; hasilnya di † atas
make -C rtl/tb all               # 408 asersi, 39 bench, 0 gagal
make -C rtl/fpga/gowin bitstream # ← hijau di Tang Nano 20K
```

---

## Lari terakhir

Lari terakhir, 3 November 2026: **6.300 lulus, 2 dilewati, 45 gagal, 0 error dari
6.347 terkumpul**. Yang gagal:
`tests/test_ai/test_nui_board_parity.py::test_the_frozen_expectations_are_what_the_engines_give_today`,
`tests/test_ai/test_nui_execution.py::test_the_committed_model_is_what_the_repository_produces`,
`tests/test_ai/test_nui_layer4_freeze.py::test_every_colour_is_counted_and_none_is_forced`,
`tests/test_ai/test_nui_layer4_freeze.py::test_what_the_records_say_is_what_the_freeze_wrote_down`,
`tests/test_ai/test_nui_layer7.py::test_not_covered_stops_under_its_own_name`,
`tests/test_ai/test_nui_layer7.py::test_opaque_state_and_subsystems_without_a_function_are_not_covered`,
`tests/test_ai/test_nui_layer7.py::test_the_command_line_reports_and_acts_on_nothing`,
`tests/test_ai/test_nui_layer7.py::test_the_hisab_discrepancy_is_known_not_merely_not_covered`,
`tests/test_ai/test_nui_parity.py::test_board_records_postdate_the_last_change_to_the_cpu_rtl`,
`tests/test_ai/test_nui_parity.py::test_the_committed_model_is_what_the_repository_produces`,
`tests/test_ai/test_nui_parity.py::test_the_hardware_column_is_recomputed_from_the_record_not_written_down`,
`tests/test_ai/test_nui_rtl_function.py::test_a_pin_holds_whichever_line_ending_the_checkout_wrote`,
`tests/test_ai/test_nui_rtl_function.py::test_the_function_is_the_rtl_at_every_cycle_of_its_bench`,
`tests/test_ai/test_nui_rtl_function.py::test_the_model_reads_back_exactly`,
`tests/test_ai/test_nui_rtl_function_dataram.py::test_the_function_as_written_now_agrees_with_the_rtl`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_a_result_wider_than_the_rtl_is_not_covered`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_a_rule_the_audit_does_not_cover_stops_the_step`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_a_sampling_the_trace_does_not_hold_is_red`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_an_op_the_case_does_not_name_is_not_covered`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_hisab_is_an_outside_result`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_alu_is_the_interpreters_handler`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_alu_reads_its_ops_and_outputs_from_the_rtl`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_function_is_the_rtl_at_every_edge`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_memory_map_is_the_composed_function`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_ram_is_the_composed_function`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_run_now_is_the_committed_one`,
`tests/test_ai/test_nui_rtl_function_hcpu.py::test_the_transmitter_is_the_composed_function`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_a_register_left_out_of_the_boundary_is_red`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_an_unelaborated_register_not_named_so_is_red`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_every_line_the_spec_cites_says_what_it_names`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_the_audit_run_now_is_the_committed_one`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_the_measurement_is_sound`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_the_state_boundary_is_the_rtls_own`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_the_unreachable_are_unreachable_by_the_lines_cited`,
`tests/test_ai/test_nui_rtl_function_hcpu_audit.py::test_what_is_named_outside_a_function_is_as_the_rtl_says`,
`tests/test_ai/test_nui_rtl_function_loader.py::test_every_boundary_of_both_benches_is_the_rtls`,
`tests/test_ai/test_nui_rtl_function_mmio.py::test_every_register_and_output_is_the_rtls_at_every_cycle`,
`tests/test_ai/test_nui_rtl_function_pipeline.py::test_every_edge_every_output_and_the_open_loop_are_the_rtls`,
`tests/test_ai/test_nui_rtl_function_pipeline_audit.py::test_the_audit_run_now_is_the_committed_one`,
`tests/test_ai/test_nui_rtl_function_pipeline_audit.py::test_the_measurement_is_sound`,
`tests/test_ai/test_nui_rtl_function_pipeline_audit.py::test_the_opcode_arms_are_read_from_the_decoder`,
`tests/test_ai/test_nui_rtl_function_pipeline_audit.py::test_two_transitions_are_unreachable_by_the_wiring_cited`,
`tests/test_integrity/test_place_and_route.py::test_the_hdmi_wrapper_records_its_own_fingerprint`,
`tests/test_integrity/test_subroutine.py::test_decode_clears_them_on_every_bubble[id_is_call]`,
`tests/test_integrity/test_subroutine.py::test_decode_clears_them_on_every_bubble[id_is_ret]`.
Yang error: tidak ada.
