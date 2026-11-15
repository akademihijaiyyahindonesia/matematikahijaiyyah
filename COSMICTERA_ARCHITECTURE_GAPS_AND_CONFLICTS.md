# COSMICTERA — ARCHITECTURAL GAPS, CONFLICTS & HARDWARE CONSTRAINTS (`CT-01-REV13`)

> **REVISION NOTICE (`v1.2 — K-01..K-12, R2, CTHETA=0x4E / HDOT=0x52 & GAP-02 Final Edition`):**  
> Paket dokumentasi arsitektur versi `v1.0` sebelumnya dinyatakan **`SUPERSEDED` (Tidak Berlaku sebagai Referensi Rekayasa)** sesuai Keputusan Pemilik (*Owner Architecture Consistency Decision*). Edisi `v1.2` ini menerapkan: (1) definisi resmi label epistemik `R2` dari `cosmictera/RULES.md` (`VF` = *Verified Formally*, `CC` = *Computationally Confirmed*, `DP` = *Design Property*, `EH` = *Engineering Hypothesis*, `AT` = *Aspirational Target*), (2) koreksi penuh `K-01` s.d. `K-12` terhadap `rtl/hcpu_pkg.vh`, `rtl/hcpu_rom.v`, `rtl/hcpu_regfile.v`, `rtl/hcpu_mmio.v`, dan `docs/HISA_SPEC.md`, (3) penetapan resmi `0x4E = CTHETA` (ekstraksi $\hat{\Theta}(H[\text{S1}])$ 8-bit, 1 siklus) dan `0x52 = HDOT` (perkalian titik 14-komponen $\langle H[\text{S1}], H[\text{S2}] \rangle_{14}$ 20-bit, 14 siklus pada `CODEX_PROFILE=2` / 1 siklus pada `CODEX_PROFILE=0,1`; total `105` opcode H-ISA v1.2, `84` di RTL, `21` software-only, `375/375` `test_isa_parity.py` PASS), serta (4) penyelesaian `GAP-02` pada `rtl/hcpu_hisab.v` yang kini menginstansiasi `rtl/hcpu_guard.v` secara kanonik (`R1`).


**Purpose:** Mendokumentasikan secara jujur, transparan, dan tanpa rekayasa seluruh celah implementasi, perbedaan antara dokumen dan kode, bug perangkat keras/perangkat lunak yang tercatat di `cosmictera-build/OFF.md` dan `NUI/LAYERS.md`, serta kendala kapasitas fisik FPGA (`cosmictera/RULES.md` R2 & R3).

---

## 1. Perbedaan Antara Dokumen Audit/Spesifikasi dan Kode Sumber Aktual

| ID Konflik | Lokasi Dokumen / Klaim Lama | Fakta Kode Sumber / Pengukuran Aktual | Status & Penanganan |
| :--- | :--- | :--- | :--- |
| **GAP-01: Docstring Invertibilitas Eksomatriks 5×5** | Docstring `src/hijaiyyah/core/exomatrix.py` menyebut bit ekor `1` sebagai penanda matriks invertibel. | Pengujian matematis membuktikan **7 huruf berekor `1` memiliki rank `< 5` atas $\mathbb{F}_2$** (bukan invertibel). | Dicatat sebagai fakta resmi Lapis 0 `nui.tail_one_is_not_invertibility` (`NUI/LAYERS.md` baris 162–167); NUI dilarang menggunakan klaim docstring tersebut sebagai aturan. |
| **GAP-02: Pengecualian Huruf Kaf (`T2`) di `hcpu_hisab.v` vs `hcpu_guard.v`** | `rtl/hcpu_guard.v` (baris 105–108) telah menghapus pengecualian `is_kaf` karena Master Table kanonik menyimpan $K_a=1, K_c=0, Q_c=0$ untuk Kaf. | **DISELESAIKAN (`GAP-02`)**: `rtl/hcpu_hisab.v` telah direfaktor untuk menginstansiasi `hcpu_guard #(.PIPELINE_GUARD(0)) u_guard` secara langsung dan menegakkan `(guard_status == 8'h3F) <=> (guard_pass == 1'b1)`. | **RESOLVED in RTL (`rtl/hcpu_hisab.v`)** sesuai Keputusan Pemilik #3; diverifikasi dengan 46 vektor uji (`test_gap02_guard_hisab_parity.py`), 85/85 pytest `tests/test_hisab/`, dan 39/39 testbench RTL (`LUT1–4` `hcpu_gowin_top` turun `-41` LUT dan `-48` ALU cell). |
| **GAP-03: Rentang Register Compiler HC (`R0–R17`) vs Assembler (`R0–R15`)** | `src/hijaiyyah/compiler/codegen.py` mengalokasikan register hingga `R17` sesuai `GPR_COUNT = 18` di `hcpu_regfile.v`. | Field register pada kata instruksi 32-bit H-ISA hanya 4 bit (`0..15`), sehingga `src/hijaiyyah/hisa/assembler.py` menolak `R16` dan `R17` dengan galat eksplisit. | Terdokumentasi di `NUI/LAYERS.md` (baris 172–177); gagal secara aman (*fail-loud*) saat perakitan tanpa menghasilkan kode salah diam-diam. |
| **GAP-04: Angka `cycle_rate` dan `drift` di `cosmictera/TELEMETRY.md`** | `cosmictera/TELEMETRY.md` mengutip `cycle_rate = 649,4` siklus/detik dan `drift = -3,3` detik (ditulis saat burn-in masih berjalan 20 Sep 2026). | Rekaman baseline final yang di-commit menghasilkan median **`650,42` siklus/detik** dan **`-3,8` detik (24j) / `-4,3` detik (72j)**. | Didokumentasikan secara eksplisit di `NUI/LAYERS.md` (baris 884–889) dan `NUI/TELEMETRY_SOURCES.md`. |
| **GAP-05: Jumlah Berkas Markdown di `NUI/LAYERS.md` Lama (`745` vs `93`)** | Catatan awal sempat menulis `745` berkas Markdown karena perintah `find` di disk ikut menghitung folder lokal yang tidak dilacak Git. | Repositori Git (`git ls-files`) memuat tepat **`93` berkas Markdown** terlacak pada saat pembekuan Lapis 1. | Diperbaiki di `src/hijaiyyah/nui/repository_index.py` dan dijaga oleh `test_nui_repository_graph.py` (`NUI/LAYERS.md` baris 283–287). |

---

## 2. Perbedaan Perilaku Eksekusi Interpreter ↔ RTL (`30` Mismatch Lapis 4 di `NUI/PARITY.md` & `OFF.md`)

Lapis 4 (`src/hijaiyyah/nui/parity_model.py`) menguji `107` run dan melokalisasi seluruh `30` selisih antara `HISAMachine` (Python) dan `hcpu_top.v` (RTL) ke lima kelas penyebab yang eksak:

1. **Instruksi Bayangan Sesudah `HALT` atau `RET` Gagal (`10` program + `3` probe = `13` kasus)**:
   - Di RTL (`rtl/hcpu_top.v`), sinyal `wb_halt` baru menghentikan pipa ketika instruksi `HALT` mencapai tahap Writeback (`WB`), sehingga satu instruksi tepat di belakang `HALT` (atau di belakang `RET` yang gagal karena tumpukan kosong `HC-05`) sempat mengeksekusi dan menulis ke register/memori/UART TX.
   - Terbukti di papan fisik melalui `board_probes.py` (`PRINT` sesudah `HALT` mengirim karakter ke kabel UART). Tercatat resmi di `cosmictera-build/OFF.md`.
2. **Semantik Register `REG_COUNTER` (`0xFF4`) (`8` kasus)**:
   - Interpreter Python menghitung jumlah **instruksi** yang dieksekusi, sedangkan `rtl/hcpu_timer.v` menghitung siklus **clock 27 MHz**.
3. **Nilai Default `SD_STATUS` (`0xFE0`) Tanpa Kartu (`7` kasus)**:
   - Tanpa kartu SD terpasang, interpreter Python mengembalikan `0`, sedangkan `rtl/hcpu_sdio.v` mengembalikan `1` (`sd_busy` / status awal).
4. **Pemeriksaan Berkala `HCHECK` Interpreter (`2` kasus — `hfs_lifecycle.hasm` & `hos_demo.hasm`)**:
   - Interpreter menjalankan pengecekan guard berkala otomatis yang menghentikan kedua program tersebut ketika register `H0` belum diinisialisasi ke huruf valid, sedangkan RTL hanya memeriksa guard saat instruksi `HGUARD`/`HCHECK`/`JGD` dipanggil secara eksplisit.

---

## 3. Kendala Fisik Perangkat Keras & Kriptografi yang Terdokumentasi (`EH` / `OFF.md`)

1. **Batas Pin `hijaiyyah_kabah_top.v` Mentah (`1.665` Bit Port vs `384` IOB — `EH`)**:
   - Modul `rtl/hijaiyyah_kabah_top.v` mengekspos keadaan 1.600-bit secara paralel (`1.665` bit port total), sehingga tidak mungkin dipetakan langsung ke pin fisik paket `QN88` (`88` pin total). Solusi arsitektural yang telah diimplementasikan adalah pembungkus serial UART `rtl/fpga/gowin/hijaiyyah_kabah_gowin_top.v` (`10` pin).
2. **Rank Transformasi Putaran Ka'bah Murni (`1.276 / 1.600` — `3ccf193`)**:
   - Transformasi putaran internal Ka'bah bukan permutasi bijektif penuh. Untuk menjamin keamanan autentikasi pesan, `hijaiyyah_kabah_gowin_top.v` dan `hijaiyyah_portal8888.v` menambahkan lapisan **HMAC-SHA256 (`hijaiyyah_hmac.v`)**.
3. **Pemisahan Bitstream Kerja vs Tampilan Boot (`cosmictera_display_top.v` vs `cosmictera_boot_top.v` vs `hcpu_gowin_top.v`)**:
   - Di pohon sumber utama, `rtl/fpga/gowin/cosmictera_display_top.v` mengikat `snap_valid = 1'b0` sehingga menampilkan `NOT INSTRUMENTED`.
   - Pada Stage 1.4 (`/tmp/stage1_2_cosmictera_boot_ui/rtl/cosmictera_boot_top.v`), tampilan boot telah diperluas menjadi 16 entri pada Page 0 dan halaman `P0–P12` dengan jembatan `cosmictera_boot_subsys_bridge.v` (`2.526` LUT4, `12` BSRAM).
   - Penggabungan fisik antara `hcpu_gowin_core` (`15.453` LUT4, `18` BSRAM) dan `cosmictera_boot_top` (`2.526` LUT4, `12` BSRAM -> `8` BSRAM dengan logo 4-BSRAM sesuai Keputusan Opsi 2 Pemilik) menghasilkan estimasi gabungan **`17.979 / 20.736` LUT4 (`86,70%`)** dan **`26–30 / 46` BSRAM (`56,5%–65,2%`)**, yang merupakan langkah integrasi perangkat keras berikutnya (Stage 1.5 / Opsi 2 Unified SoC).

---

## 4. Komponen Berstatus Target Arsitektur (`AT`) — Belum Diimplementasikan

Sesuai aturan `R2` (`cosmictera/RULES.md`), komponen berikut dicatat secara tegas sebagai **`AT` (*Aspirational Target*)** dan tidak boleh diklaim telah berjalan:
1. **Lexer/Parser Kata Kunci Bahasa Arab & Indonesia secara Langsung di Compiler HC**: Saat ini kamus 4 konsep (`VARIABLE`, `PRINT`, `IF`, `FUNCTION`) telah dispesifikasikan di `NUI/spec/hc_kamus.json` dan divalidasi oleh `usr.py`, tetapi `src/hijaiyyah/language/lexer.py` masih hanya menerima kata kunci bahasa Inggris (`let`, `println`, `if`, `fn`) dan compiler `codegen.py` belum menurunkan konstruksi `if` dan `fn` penuh dari USR.
2. **NUI Lapis 8 (Pemicu Diagnostik Otonom Tanpa Manusia)**: Alat diagnostik papan sudah ada dan terbukti menemukan bug, tetapi masih dijalankan oleh operator manusia.
3. **NUI Lapis 9 (Mesin Inferensi Deduktif)**: Basis pengetahuan 7-domain dan 7 kontrak kueri di `knowledge.py` sudah berjalan (`DP`), namun mesin inferensi rantai `fakta -> relasi -> inferensi -> kesimpulan` belum diimplementasikan (`AT`).
4. **NUI Lapis 10 (Sintesis Rekayasa Otonom) & Lapis 11 (Rantai Komputasi Universal Penuh)**: Berstatus `AT`.
5. **Fabrikasi Silikon Fisik ASIC SkyWater SKY130 (`rtl/mpw/`) & Integrasi Papan KV260 / Cluster Docker**: Pembungkus RTL Wishbone Caravel sudah `CC` (`8/8` TB pass), namun GDSII silikon fisik dan target KV260 masih `AT`.


---

## Lampiran Verifikasi Forensik `v1.2`: Matriks Kebenaran Kanonik `K-01` s.d. `K-12` (`rtl/hcpu_pkg.vh`, `rtl/hcpu_rom.v`, `rtl/hcpu_mmio.v`, `docs/HISA_SPEC.md`)

Tabel berikut mengunci parameter perangkat keras dan encoding instruksi aktual langsung dari berkas RTL kanonik (`rtl/hcpu_pkg.vh`, `rtl/hcpu_rom.v`, `rtl/hcpu_regfile.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_memory.v`, `rtl/hcpu_mmio.v`, `rtl/hcpu_trap.v`):

| Kode Koreksi | Domain Arsitektur | Spesifikasi Eksak di Sumber Kanonik (`rtl/` & `docs/HISA_SPEC.md`) |
| :--- | :--- | :--- |
| **`K-01`** | **Opcode Huruf Hijaiyyah (`28` Huruf)** | **`0xE0–0xFB`** (`OP_L_ALIF = 8'hE0` s.d. `OP_L_YA = 8'hFB` di `rtl/hcpu_pkg.vh` baris 195–222; `OpCode.L_ALIF..OpCode.L_YA` di `opcodes.py`). Alamat ROM dihitung sebagai `id_opcode - OP_L_ALIF + 1` (`1..28`, 1-based). |
| **`K-02`** | **Opcode Sistem & Kontrol (`0x00–0x0B`)** | `NOP = 0x00`, `HALT = 0x01`, `MOV = 0x03`, `MOVI = 0x04`, `HNRM2 = 0x06`, `HDIST = 0x07`, `ERET = 0x08`, `SYSCALL = 0x09`, `FRD = 0x0A`, `FWR = 0x0B` (`rtl/hcpu_pkg.vh` baris 129–139). (`RESET = 0x02` dan `WAIT = 0x05` hanya di perangkat lunak). |
| **`K-03`** | **Opcode Aritmetika (`0x10–0x14`) & Bitwise (`0xB0–0xBA`)** | **Aritmetika RTL**: `ADD = 0x10`, `ADDI = 0x11`, `SUB = 0x12`, `MUL = 0x14` (`SUBI=0x13`, `DIV=0x15`, `MOD=0x16`, `NEG=0x17`, `INC=0x18`, `DEC=0x19` hanya di perangkat lunak). **Bitwise/Shift RTL**: `AND = 0xB0`, `OR = 0xB1`, `XOR = 0xB2`, `NOT = 0xB3`, `SHL = 0xB4`, `SHR = 0xB5`, `ANDI = 0xB6`, `ORI = 0xB7`, `XORI = 0xB8`, `SHLI = 0xB9`, `SHRI = 0xBA` (`rtl/hcpu_pkg.vh` baris 142–145 & 225–235). |
| **`K-04`** | **Opcode Compare, Branch & Call (`0x20–0x2F`)** | **RTL**: `CMP = 0x20`, `CMPI = 0x21`, `JMP = 0x22`, `JEQ = 0x23`, `JNE = 0x24`, `JGD = 0x29` (cabang jika `FLAG_G == 1`), `JNGD = 0x2A` (cabang jika `FLAG_G == 0`), `CALL = 0x2E`, `RET = 0x2F` (`rtl/hcpu_pkg.vh` baris 148–156). (`JGT=0x25`, `JLT=0x26`, `JGE=0x27`, `JLE=0x28`, `JOVF=0x2B`, `JNOVF=0x2C`, `JRHO=0x2D` hanya di perangkat lunak; tidak ada `JMOD4` di RTL). |
| **`K-05`** | **Opcode Memori & Stack (`0x30–0x33`) & Kedalaman Stack** | **RTL**: `LOAD = 0x30`, `STORE = 0x31`, `PUSH = 0x32`, `POP = 0x33` (`rtl/hcpu_pkg.vh` baris 159–162; `LOADH=0x38`, `STOREH=0x39`, `LPUSH=0x3A`, `LPOP=0x3B` hanya di perangkat lunak). **Return Address Stack (`CALL`/`RET`)**: `RA_DEPTH = 32` (`32 × 12-bit` di `rtl/hcpu_execute.v` baris 121). **Data Stack (`PUSH`/`POP`)**: `STACK_DEPTH = 256` (`256 × 32-bit` di `rtl/hcpu_memory.v` baris 81). |
| **`K-06`** | **Opcode Codex, Guard & HISAB (`0x40–0x60`)** | **RTL**: `HLOAD = 0x40`, `HCADD = 0x42`, `CGET = 0x44`, `CSET = 0x45`, `CMOV = 0x46`, `CZERO = 0x47`, `CEQ = 0x48`, `CRHO = 0x4C`, `CU = 0x4D`, **`CTHETA = 0x4E`** (`OP_CTHETA = 8'h4E`, ekstraksi $\hat{\Theta}(H[\text{S1}])$ 8-bit, 1 siklus), `CMOD4 = 0x4F`, `HPACK = 0x50`, `HCRC = 0x51`, **`HDOT = 0x52`** (`OP_HDOT = 8'h52`, produk dalam 14-komponen 20-bit via `ALU_HDOT`, 14 siklus pada `CODEX_PROFILE=2`), `HGRD = 0x60` (`HCHK = 0x68` hanya di perangkat lunak). |
| **`K-07`** | **Opcode I/O & Error (`0xA0–0xFF`) & Total Opcode** | **RTL**: `PRINT = 0xA0`, `EMITS = 0xA2`, `HALT_ERR = 0xFF` (`PRINTH = 0xA1` dan `DUMP = 0xA8` hanya di perangkat lunak). **Total Opcode**: **`105` opcode unik** di `docs/HISA_SPEC.md` dan `OpCode` di `src/hijaiyyah/hisa/opcodes.py` (`0` alias); **`84` diimplementasikan di RTL** (`rtl/hcpu_pkg.vh` & `RTL_IMPLEMENTED`, termasuk `28` opcode huruf `0xE0–0xFB`, `CTHETA = 0x4E`, dan `HDOT = 0x52`) serta **`21` software-only** (`cosmictera-build/OFF.md`). |
| **`K-08`** | **Pemetaan Bit `FLAGS` (`rtl/hcpu_pkg.vh` baris 56–59)** | `FLAG_G = 0` (`bit 0`: Guard pass), `FLAG_Z = 1` (`bit 1`: Zero), `FLAG_O = 2` (`bit 2`: Overflow), `FLAG_LT = 3` (`bit 3`: Less-than). |
| **`K-09`** | **Struktur `rtl/hcpu_rom.v` (`ROM_ADDR_W = 6`)** | Alamat **6-bit (`addr[5:0]`, `0..63`)**: indeks **`1..28`** adalah 28 huruf Hijaiyyah kanonik (1-based: `1 = Alif` .. `28 = Ya`); indeks **`31..36`** adalah **6 vektor uji negatif** untuk verifikasi perangkat keras (`31` gagal `G4`, `32` gagal `G1`, `33` gagal `G2`, `34` gagal `G3`, `35` gagal `T1`, `36` gagal `T2`); indeks `0`, `29`, `30`, `37..63` mengembalikan `valid = 0` dan `144'd0`. Total entri valid = `34` (`28 + 6`). |
| **`K-10`** | **Peta MMIO Blok SDIO (`0xFE0–0xFE6`)** | `0xFE0 = SD_CMD` (W: `1`=INIT, `2`=READ, `3`=WRITE), `0xFE1 = SD_STATUS` (R: `{24'd0, err_code[3:0], card_ready, err, ok, busy}`), `0xFE2 = SD_SECTOR` (RW: 32-bit LBA), `0xFE3 = SD_DATA` (RW: 128-word buffer port, auto-inc `sd_index`), `0xFE4 = SD_CONTROL` (RW: bit 0 reset index, bit 1 soft reset, bits `[3:2]` clock div), `0xFE5 = SD_CSUM` (R: XOR checksum), `0xFE6 = SD_PRESCAN` (R: `{30'd0, all_zero, has_magic}`). `0xFE7–0xFEF` tidak terpakai (`0`). |
| **`K-11`** | **Peta MMIO Blok Inti (`0xFF0–0xFFF`), Trap & Privilege** | `0xFF0 = REG_RX_DATA`, `0xFF1 = REG_RX_STATUS`, `0xFF2 = REG_TX_STATUS`, **`0xFF3 = REG_IMEM_ADDR`**, `0xFF4 = REG_COUNTER`, `0xFF5 = REG_COMPARE`, `0xFF6 = REG_TIMER_ST`, **`0xFF7 = REG_IMEM_DATA`**, `0xFF8 = REG_TRAP_VECTOR`, `0xFF9 = REG_TRAP_EPC`, `0xFFA = REG_TRAP_CAUSE` (**`0`=Timer, `1`=UART_RX, `2`=Illegal, `3`=Priv, `4`=Mem, `5`=Syscall**), `0xFFB = REG_TRAP_ENABLE`, `0xFFC = REG_TRAP_PENDING`, `0xFFD = REG_TRAP_MODE` (**`MODE_USER = 0`, `MODE_SUPER = 1`** di `hcpu_pkg.vh`; bit `[1]` di `hcpu_trap.v` mengaktifkan proteksi User), **`0xFFE = REG_MEM_BASE`**, **`0xFFF = REG_MEM_LIMIT`**. |
| **`K-12`** | **Bank Register (`hcpu_regfile.v`) & Model Lapisan** | **GPR**: `GPR_COUNT = 18` (`R0–R17` × 32-bit fisik di `hcpu_regfile.v`, sedangkan field instruksi 4-bit mengalamati `R0–R15`). **H-Reg**: `HREG_COUNT = 16` (`H0–H15` × `144-bit` + `hreg_ovf[15:0]` di `hcpu_regfile.v`; berbeda dari tabel warisan `HISA_SPEC.md` §3.2 yang mencantumkan `4` `H0–H3` × `576-bit`). **Model Lapisan**: membedakan secara eksplisit (a) **5-Lapis Keamanan Ka'bah** (`cosmictera/RULES.md` R10: L0 Kanonik `DP`, L1 Guard `CC`, L2 Serapan `EH`, L3 Autentik `VF`, L4 Rahasia ditolak), (b) **7-Lapis `cosmictera/SYSTEM.md`**, (c) **11-Lapis `docs/ARCHITECTURE.md`**, (d) **12-Lapis `NUI/LAYERS.md` (`L0–L11`)**, dan (e) **13-Lapis `COSMICTERA_CT01_REV13_AUDIT.md`**. |
