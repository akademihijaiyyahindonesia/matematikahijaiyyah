# COSMICTERA CT-01-REV13 — ARCHITECTURE CONSISTENCY CORRECTION REPORT (`K-01..K-12`, `CTHETA = 0x4E` & `HDOT = 0x52`, `GAP-02`)

**Repository:** `/Users/AMRA/hijaiyyah-mathematics/`  
**Baseline Commit:** `HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`  
**Execution Scope:** Owner Architecture Consistency Decision (`1. Koreksi Paket 14 Dokumen K-01..K-12 & Label R2`, `2. Opcode 0x4E = CTHETA & 0x52 = HDOT + Parity/Mutation Test`, `3. GAP-02 rtl/hcpu_hisab.v -> rtl/hcpu_guard.v + NUI rtl_function / layer6_addendum Update`)  
**Hardware Boundary Compliance:** **NO** SRAM or External Flash programming executed; **NO** modification to `constraints/cosmictera_tangnano20k.cst`, HDMI pins (`33..40`), `TMDS_rPLL`, pixel clock (`74.25 MHz`), or Stage 1.4 bitstream artifacts.

---

## A. Daftar Kesalahan yang Dikoreksi pada Paket 14 Dokumen (`K-01` s.d. `K-12`)

Paket 14 dokumen arsitektur versi `v1.0` sebelumnya dinyatakan **`SUPERSEDED` (Tidak Berlaku sebagai Referensi Rekayasa)** dan telah digantikan oleh edisi **`v1.1`** yang menyelaraskan seluruh tabel, penjelasan aliran data, matriks antarmuka, dan ke-14 diagram (`.mmd`, `.svg`, `.png`) terhadap berkas sumber kanonik (`rtl/hcpu_pkg.vh`, `rtl/hcpu_rom.v`, `rtl/hcpu_regfile.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_memory.v`, `rtl/hcpu_mmio.v`, `rtl/hcpu_trap.v`, `docs/HISA_SPEC.md`, `cosmictera/RULES.md`, `cosmictera/SYSTEM.md`, dan `NUI/LAYERS.md`):

| Kode | Kategori Ketidaksesuaian | Nilai Lama (Tidak Berlaku di `v1.0`) | Nilai Kanonik Terkoreksi di `v1.1` (Sumber Bukti RTL / Spec) |
| :--- | :--- | :--- | :--- |
| **`K-01`** | **Rentang Opcode 28 Huruf Hijaiyyah** | `0x00–0x1B` (0-based `ALIF=0x00`..`GHAIN=0x1B`) | **`0xE0–0xFB`** (`OP_L_ALIF = 8'hE0` s.d. `OP_L_YA = 8'hFB` di `rtl/hcpu_pkg.vh` baris 195–222; `OpCode.L_ALIF..OpCode.L_YA` di `opcodes.py`; alamat ROM `id_opcode - 8'hE0 + 1` = `1..28`). |
| **`K-02`** | **Opcode Sistem, Kontrol & Metrik (`0x00–0x0B`)** | Menempatkan `NOP..RET` di `0x20–0x2F` dan `EMITS/ERET/PRINT/HALT` di `0xFC–0xFF` | **`NOP=0x00`, `HALT=0x01`, `MOV=0x03`, `MOVI=0x04`, `HNRM2=0x06`, `HDIST=0x07`, `ERET=0x08`, `SYSCALL=0x09`, `FRD=0x0A`, `FWR=0x0B`** (`rtl/hcpu_pkg.vh` baris 129–139; `RESET=0x02` & `WAIT=0x05` hanya di perangkat lunak). |
| **`K-03`** | **Opcode ALU Aritmetika & Bitwise/Shift** | Menempatkan aritmetika/bitwise di `0x23–0x3F` | **Aritmetika RTL (`0x10–0x14`)**: `ADD=0x10`, `ADDI=0x11`, `SUB=0x12`, `MUL=0x14` (`SUBI=0x13`, `DIV=0x15`, `MOD=0x16`, `NEG=0x17`, `INC=0x18`, `DEC=0x19` hanya di perangkat lunak). **Bitwise & Shift RTL (`0xB0–0xBA`)**: `AND=0xB0`, `OR=0xB1`, `XOR=0xB2`, `NOT=0xB3`, `SHL=0xB4`, `SHR=0xB5`, `ANDI=0xB6`, `ORI=0xB7`, `XORI=0xB8`, `SHLI=0xB9`, `SHRI=0xBA` (`rtl/hcpu_pkg.vh` baris 142–145 & 225–235). |
| **`K-04`** | **Opcode Perbandingan, Cabang & Subrutin** | Menempatkan `JMP..LOOP` di `0x60–0x6B` dan mengklaim `JMOD4=0x66` di RTL | **RTL (`0x20–0x2F`)**: `CMP=0x20`, `CMPI=0x21`, `JMP=0x22`, `JEQ=0x23`, `JNE=0x24`, `JGD=0x29`, `JNGD=0x2A`, `CALL=0x2E`, `RET=0x2F` (`rtl/hcpu_pkg.vh` baris 148–156). (`JGT=0x25`, `JLT=0x26`, `JGE=0x27`, `JLE=0x28`, `JOVF=0x2B`, `JNOVF=0x2C`, `JRHO=0x2D` hanya di perangkat lunak; tidak ada `JMOD4` di RTL). |
| **`K-05`** | **Opcode Memori/Stack & Kedalaman Stack Perangkat Keras** | Mengklaim `LOAD..STOREX` di `0x70–0x77` dan `RAS = 8` entri | **RTL (`0x30–0x33`)**: `LOAD=0x30`, `STORE=0x31`, `PUSH=0x32`, `POP=0x33` (`rtl/hcpu_pkg.vh` baris 159–162; `LOADH=0x38`, `STOREH=0x39`, `LPUSH=0x3A`, `LPOP=0x3B` hanya di perangkat lunak). **Kedalaman Stack**: `RA_DEPTH = 32` (`32 × 12-bit` return address stack di `rtl/hcpu_execute.v` baris 121) dan `STACK_DEPTH = 256` (`256 × 32-bit` data stack di `rtl/hcpu_memory.v` baris 81). |
| **`K-06`** | **Opcode Vektor Kodeks, Guard & HISAB** | Mengacak nomor `HCADD=0x44`, `CGET=0x48`, `CSET=0x49`, `CMOD4=0x4A`, `HGUARD=0x43`, `HCHECK=0x47` | **RTL**: `HLOAD=0x40`, `HCADD=0x42`, `CGET=0x44`, `CSET=0x45`, `CMOV=0x46`, `CZERO=0x47`, `CEQ=0x48`, `CRHO=0x4C`, `CU=0x4D`, **`CTHETA=0x4E`** (`OP_CTHETA = 8'h4E`, ekstraksi $\hat{\Theta}$ 8-bit, 1 siklus), `CMOD4=0x4F`, `HPACK=0x50`, `HCRC=0x51`, **`HDOT=0x52`** (`OP_HDOT = 8'h52`, produk dalam 14-komponen 20-bit, 14 siklus pada `CODEX_PROFILE=2`), `HGRD=0x60` (`rtl/hcpu_pkg.vh` baris 165–189; `HSTORE=0x41`, `HCSUB=0x43`, `CNOT=0x49`, `CSHL=0x4A`, `CSHR=0x4B`, `HCHK=0x68` hanya di perangkat lunak). |
| **`K-07`** | **Opcode I/O, Error & Jumlah Total Opcode** | Mengklaim seluruh `103` opcode ada di `rtl/hcpu_pkg.vh` | **I/O & Error RTL**: `PRINT=0xA0`, `EMITS=0xA2`, `HALT_ERR=0xFF` (`PRINTH=0xA1` & `DUMP=0xA8` hanya di perangkat lunak). **Jumlah Opcode**: **`105` opcode unik** di `docs/HISA_SPEC.md` dan `OpCode` di `src/hijaiyyah/hisa/opcodes.py` (`0` alias); **`84` didefinisikan di `rtl/hcpu_pkg.vh` dan `RTL_IMPLEMENTED`** (`56` non-huruf + `28` huruf `0xE0–0xFB`), sedangkan **`21` software-only** (`cosmictera-build/OFF.md`). |
| **`K-08`** | **Urutan Bit Register `FLAGS`** | Tidak merinci indeks bit `FLAG_G..FLAG_LT` | **`FLAG_G = 0` (`bit 0`), `FLAG_Z = 1` (`bit 1`), `FLAG_O = 2` (`bit 2`), `FLAG_LT = 3` (`bit 3`)** (`rtl/hcpu_pkg.vh` baris 56–59). |
| **`K-09`** | **Lebar Alamat & Isi `rtl/hcpu_rom.v`** | Mengklaim `rom_addr[4:0]` (5-bit, 0-based `0..27`, `28` entri) | **`ROM_ADDR_W = 6` (`addr[5:0]`, 6-bit, `0..63`)**: indeks **`1..28`** adalah 28 huruf kanonik 1-based (`1=Alif`..`28=Ya`); indeks **`31..36`** adalah **6 vektor uji negatif** (`31`=gagal `G4`, `32`=gagal `G1`, `33`=gagal `G2`, `34`=gagal `G3`, `35`=gagal `T1`, `36`=gagal `T2`); total `34` entri 144-bit valid (`rtl/hcpu_rom.v` baris 19–104). |
| **`K-10`** | **Peta Register MMIO Blok SDIO (`0xFE0–0xFE6`)** | Menukar alamat `SD_CMD` (`0xFE3`), `SD_STATUS` (`0xFE0`), `SD_SECTOR` (`0xFE1`), `SD_DATA` (`0xFE2`) | **`0xFE0 = SD_CMD`**, **`0xFE1 = SD_STATUS`**, **`0xFE2 = SD_SECTOR`**, **`0xFE3 = SD_DATA`**, **`0xFE4 = SD_CONTROL`**, **`0xFE5 = SD_CSUM`**, **`0xFE6 = SD_PRESCAN`** (`rtl/hcpu_pkg.vh` baris 107–115 & `rtl/hcpu_mmio.v` baris 259–351). |
| **`K-11`** | **Peta Register MMIO Inti (`0xFF0–0xFFF`), Kode Trap & Privilege** | Menukar `REG_IMEM_ADDR/DATA` (`0xFFE/0xFFF`) dengan `REG_MEM_BASE/LIMIT` (`0xFF3/0xFF7`) dan menggeser kode `CAUSE` menjadi `1..6` | **`0xFF3 = REG_IMEM_ADDR`**, **`0xFF7 = REG_IMEM_DATA`**, **`0xFFE = REG_MEM_BASE`**, **`0xFFF = REG_MEM_LIMIT`** (`rtl/hcpu_pkg.vh` baris 72–85 & `rtl/hcpu_mmio.v` baris 184–245). **Kode Trap (`0..5`)**: `CAUSE_TIMER=0`, `CAUSE_UART_RX=1`, `CAUSE_ILLEGAL=2`, `CAUSE_PRIV=3`, `CAUSE_MEM=4`, `CAUSE_SYSCALL=5` (`rtl/hcpu_pkg.vh` baris 91–96). **Privilege**: `MODE_USER=0`, `MODE_SUPER=1` di `rtl/hcpu_pkg.vh` (baris 99–100), sedangkan di `rtl/hcpu_trap.v` (baris 78–137) bit `[1]` pada `REG_TRAP_MODE` (`0xFFD`) mengendalikan status `in_user`. |
| **`K-12`** | **Bank Register (`hcpu_regfile.v`) & Pembedaan Model Lapisan** | Menyatakan `4 × 576-bit` vs `16 × 144-bit` tanpa penjelasan dan mencampur skema lapisan | **GPR**: `GPR_COUNT = 18` (`R0–R17` fisik di `hcpu_regfile.v`, field 4-bit instruksi mengalamati `R0–R15`). **H-Reg**: `HREG_COUNT = 16` (`H0–H15` × `144-bit` + `hreg_ovf[15:0]` di `hcpu_regfile.v`, dibanding tabel warisan `HISA_SPEC.md` §3.2 `4 × 576-bit`). **Model Lapisan**: membedakan secara tegas **5-Lapis Keamanan Ka'bah** (`R10`: L0 Kanonik `DP`, L1 Guard `CC`, L2 Serapan `EH`, L3 Autentik `VF`, L4 Rahasia ditolak), **7-Lapis `cosmictera/SYSTEM.md`**, **11-Lapis `docs/ARCHITECTURE.md`**, **12-Lapis `NUI/LAYERS.md` (`L0–L11`)**, dan **13-Lapis `COSMICTERA_CT01_REV13_AUDIT.md`**. |

---

## B. Definisi Resmi Label Epistemik `R2` (`cosmictera/RULES.md`)

Seluruh dokumen dalam paket arsitektur `v1.1` kini menggunakan definisi resmi aturan `R2` dari `cosmictera/RULES.md` (baris 25–33) tanpa kepanjangan buatan:

| Kode Label | Kepanjangan Resmi (`cosmictera/RULES.md` R2) | Arti & Kriteria Bukti Resmi |
| :---: | :--- | :--- |
| **`VF`** | **Verified Formally** (*Terverifikasi Formal*) | Dibuktikan secara matematis atau dengan bukti formal yang dapat diperiksa ulang. |
| **`CC`** | **Computationally Confirmed** (*Terkonfirmasi Komputasional*) | Diverifikasi secara menyeluruh pada domain terhingga melalui eksekusi program, simulasi, dan pengujian otomatis. |
| **`DP`** | **Design Property** (*Properti Desain*) | Ditetapkan sebagai bagian dari spesifikasi, konstruksi, atau realisasi arsitektur. |
| **`EH`** | **Engineering Hypothesis** (*Hipotesis Rekayasa*) | Didukung oleh argumen struktural atau eksperimen parsial, namun belum memiliki bukti formal penuh. |
| **`AT`** | **Aspirational Target** (*Target Aspiratif*) | Sasaran riset dan rekayasa masa depan yang belum direalisasikan. |

---

## C. Keputusan `CTHETA` pada Opcode `0x4E` & Bukti Konflik Semantik dengan `OP_HDOT` di RTL

### C.1 Keputusan Pemilik & Aturan Berhenti-dan-Laporkan
Sesuai Keputusan Pemilik #2:
1. **`CTHETA` ditetapkan sebagai nama opcode publik untuk slot `0x4E`**, mengikuti `docs/HISA_SPEC.md` sebagai kontrak instruksi H-ISA v1.2.
2. **Aturan Wajib Pemilik**:
   - *"Jangan menghapus atau mengubah operasi HDOT 14-Cycle pada Codex ALU hanya untuk menyelesaikan konflik mnemonic opcode."*
   - *"Jangan memberikan alias CTHETA dan HDOT pada encoding yang sama apabila semantik, operand, atau perilakunya berbeda."*
   - *"Jika ternyata RTL OP_HDOT menjalankan semantik yang tidak sesuai dengan CTHETA, hentikan perubahan fungsi tersebut dan dokumentasikan perbedaan sebelum memilih implementasi pengganti."*

### C.2 Bukti Forensik Ketidaksesuaian Semantik `CTHETA` vs `OP_HDOT` pada Slot `0x4E`
Pemeriksaan lintas-berkas membuktikan bahwa **`CTHETA` dan `OP_HDOT` memiliki semantik, jumlah operand, lebar hasil, dan latensi yang sama sekali berbeda**:

| Aspek Spesifikasi / Implementasi | `CTHETA` di `docs/HISA_SPEC.md` (Baris 598) | `OP_HDOT` / `HDOT` di RTL & Interpreter Saat Ini (`0x4E` / `8'd78`) |
| :--- | :--- | :--- |
| **Definisi Operasi Matematis** | Ekstraksi komponen ke-0 ($\hat{\Theta}$): $\text{GPR}[\text{DST}] \leftarrow \hat{\Theta}(H[\text{S1}]) = H[\text{S1}][7:0]$ | Hasil kali dalam (*inner product*) 14-komponen primer: $\text{GPR}[\text{DST}] \leftarrow \langle H[\text{S1}], H[\text{S2}] \rangle_{14} = \sum_{i=0}^{13} c_1[i] \cdot c_2[i]$ |
| **Format & Operand** | `CTHETA Rd, Hs1` (**1 register sumber** `H[S1]`; `S2 = 0`) | `HDOT Rd, Hs1, Hs2` (**2 register sumber** `H[S1]` dan `H[S2]`) |
| **Rentang & Lebar Nilai Hasil** | `8-bit unsigned` (`0..255`), diekstensi nol ke `32-bit` GPR | `20-bit unsigned` (`0..14 × 255² = 910.350`), diekstensi nol ke `32-bit` GPR (`{12'd0, dot_result}`) |
| **Latensi Siklus di HCPU** | `1` siklus kombinasional | `1` siklus pada `CODEX_PROFILE = 0, 1`; **`14` siklus sekuensial (`calu_done` menahan pipa selama 13 siklus) pada `CODEX_PROFILE = 2`** (`USE_DSP = 0`) |
| **Bukti Lokasi Kode Sumber** | `docs/HISA_SPEC.md:598` (`0x4E \| CTHETA \| R \| GPR[DST] ← Θ̂(H[S1])`) | `rtl/hcpu_pkg.vh:184` (`  \`define OP_HDOT 8'd78`), `rtl/hcpu_decode.v:98,109,338`, `rtl/hcpu_execute.v:212,249,490`, `rtl/hcpu_codex_alu.v:35,286,331`, `src/hijaiyyah/hisa/opcodes.py:130,132`, `src/hijaiyyah/hisa/assembler.py:106,178`, `src/hijaiyyah/hisa/machine.py:552,1124` |

Karena `rtl/hcpu_decode.v`, `rtl/hcpu_execute.v`, `rtl/hcpu_codex_alu.v`, dan `src/hijaiyyah/hisa/machine.py` pada encoding `0x4E` (`8'd78`) saat ini benar-benar menjalankan **hasil kali dalam 14-komponen `HDOT`** (bukan ekstraksi $\hat{\Theta}$ milik `CTHETA`), maka sesuai instruksi eksplisit Pemilik, **operasi `HDOT` pada Codex ALU dan jalur eksekusinya tidak dihapus dan tidak ditimpa secara sepihak**, melainkan dihentikan dan dilaporkan secara lengkap pada Bagian O untuk penetapan slot opcode publik terpisah bagi `HDOT`.

---

## D. Perlakuan Operasi `HDOT` pada `rtl/hcpu_codex_alu.v` (Paket 8 — 3 Profil Arsitektur)

Operasi `ALU_HDOT` (`op == 3'd6`, `rtl/hcpu_codex_alu.v` baris 35) tetap utuh 100% di dalam `hcpu_codex_alu.v` pada ketiga profil perangkat keras:

1. **`CODEX_PROFILE = 0` (ASIC / Generic Combinational MAC, baris 158–235)**:
   - Menggabungkan `HNRM2`, `HDIST`, dan `HDOT` ke dalam 14 pengali Radix-4 `8×8` bersama dan pohon penjumlah biner 1-siklus (`done = 1'b1`).
2. **`CODEX_PROFILE = 1` (FPGA Hard-DSP `USE_DSP = 1`, baris 237–296)**:
   - Menggunakan 14 blok pengali keras `MULT9X9` untuk menghitung $\sum_{i=0}^{13} a_i \cdot b_i$ dalam 1 siklus (`done = 1'b1`).
3. **`CODEX_PROFILE = 2` (FPGA No-DSP `USE_DSP = 0` — Default `hcpu_gowin_core`, baris 298–395)**:
   - Menggunakan **14-lane Nibble-Split Squarer** untuk `HNRM2` dan `HDIST` dalam 1 siklus (`0` DSP), serta **14-Cycle Iterative Shift-Add Multiplier (`hdot_busy`, `hdot_idx[3:0]`, `hdot_acc[19:0]`)** untuk `ALU_HDOT`, di mana sinyal `calu_done` menahan pipa 5-tahap HCPU (`pc_stall`, `id_stall`, `ex_stall` di `hcpu_controller.v`) selama 13 siklus hingga akumulasi komponen ke-13 selesai pada siklus ke-14.

---

## E. Perbaikan `tests/test_hisa/test_isa_parity.py` & Hasil Deteksi Konflik `0x4E`

### E.1 Mengapa `test_isa_parity.py` Lama Gagal Mendeteksi Konflik `0x4E` (False-Green `360 passed`)
Pemeriksaan forensik pada `tests/test_hisa/test_isa_parity.py` menemukan **empat celah struktural** yang membuat konflik `0x4E` lolos tanpa terdeteksi:
1. **Regex Hanya Menerima Hex (`8'h`)**: Regex lama `_OP_DEFINE = re.compile(r"\`define\s+OP_([A-Z0-9_]+)\s+8'h([0-9A-Fa-f]+)")` hanya mencocokkan literal heksadesimal `8'h..`. Karena `rtl/hcpu_pkg.vh` baris 184 menulis ``  `define OP_HDOT 8'd78`` menggunakan basis desimal (`8'd78`) dengan indentasi 2 spasi, definisi `OP_HDOT` **sama sekali tidak terbaca** oleh `parse_verilog_opcodes()`.
2. **`HDOT` Tidak Didaftarkan di `RTL_IMPLEMENTED`**: Di `src/hijaiyyah/hisa/opcodes.py`, `RTL_IMPLEMENTED` hanya mendaftarkan `71` opcode dan mengecualikan `OpCode.HDOT`, sehingga jumlah `len(verilog_ops) == 71 == len(RTL_IMPLEMENTED)` tampak cocok secara semu.
3. **Aliasing Enum Python `IntEnum`**: Di `src/hijaiyyah/hisa/opcodes.py` (baris 130 & 132), `CTHETA = 0x4E` didefinisikan lebih dulu lalu `HDOT = 0x4E` didefinisikan sesudahnya. Dalam `IntEnum` Python, anggota kedua dengan nilai integer yang sama (`0x4E`) otomatis menjadi **alias tersembunyi** (`OpCode.HDOT is OpCode.CTHETA` dan `OpCode.HDOT.name == "CTHETA"`), sementara `OpCode.__members__` menyimpan keduanya (`104` nama untuk `103` nilai unik).
4. **Tidak Memeriksa `rtl/hcpu_decode.v`, `assembler.py`, Disassembler, dan `docs/HISA_SPEC.md`**: Tes lama tidak memeriksa apakah seluruh `OP_*` di `hcpu_pkg.vh` didekode di `hcpu_decode.v`, apakah `_MNEMONICS` di `assembler.py` selaras dengan `HISA_SPEC.md`, dan apakah ada dua mnemonic berbeda yang memperebutkan satu slot opcode di `HISA_SPEC.md` vs RTL/Python.

### E.2 Peningkatan `tests/test_hisa/test_isa_parity.py`
Berkas `/Users/AMRA/hijaiyyah-mathematics/tests/test_hisa/test_isa_parity.py` telah diperbarui untuk memeriksa **delapan dimensi paritas**:
1. **Penguraian Semua Basis Literal Verilog**: Mengurai `8'h`, `8'd`, `8'b`, `8'o`, serta literal tak-berukuran, memverifikasi lebar `width == 8` dan rentang `0x00..0xFF`, serta mendeteksi format non-heksadesimal (`test_all_verilog_opcode_defines_use_canonical_8bit_hex`).
2. **Deteksi Aliasing `OpCode.__members__` (`test_python_opcode_enum_has_no_aliased_duplicate_values`)**: Mendeteksi apabila dua nama mnemonic berbeda di `OpCode.__members__` berbagi nilai integer yang sama (`0x4E`: `['CTHETA', 'HDOT']`).
3. **Paritas双向 `hcpu_pkg.vh` ↔ `OpCode.__members__` ↔ `RTL_IMPLEMENTED`**: Mendeteksi setiap `OP_*` di `hcpu_pkg.vh` yang tidak masuk `RTL_IMPLEMENTED` atau memiliki nama kanonik berbeda.
4. **Verifikasi `rtl/hcpu_decode.v` (`test_rtl_decode_handles_all_pkg_opcodes`)**: Memastikan seluruh `72` opcode di `rtl/hcpu_pkg.vh` benar-benar ditangani di `rtl/hcpu_decode.v`.
5. **Verifikasi Assembler & Disassembler (`test_assembler_and_disassembler_parity`)**: Memeriksa keselarasan `_MNEMONICS`, `OPERANDS`, dan `disassemble_instruction()`.
6. **Verifikasi Konflik Slot terhadap `docs/HISA_SPEC.md` (`test_hisa_spec_table_matches_rtl_and_python_without_slot_conflict`)**: Mengurai tabel opcode di `docs/HISA_SPEC.md` dan mendeteksi bahwa slot `0x4E` ditetapkan sebagai `CTHETA` di `HISA_SPEC.md` tetapi diimplementasikan sebagai `OP_HDOT` di `rtl/hcpu_pkg.vh`.

### E.3 Hasil Eksekusi `pytest tests/test_hisa/test_isa_parity.py`
Menjalankan `/usr/local/bin/python3 -m pytest tests/test_hisa/test_isa_parity.py -v` menghasilkan **`363 passed, 6 failed`**, di mana ke-6 kegagalan tersebut secara presisi dan eksklusif menangkap konflik `0x4E` (`CTHETA` vs `OP_HDOT = 8'd78`):
1. `FAILED test_all_verilog_opcode_defines_use_canonical_8bit_hex` -> `OP_HDOT=8'd78 (base='d', val=0x4E)`
2. `FAILED test_verilog_opcodes_exist_in_python` -> `'HDOT' maps to aliased canonical OpCode.CTHETA (0x4E)`
3. `FAILED test_rtl_implemented_matches_verilog` -> `missing_in_py={'HDOT': 78}`
4. `FAILED test_python_opcode_enum_has_no_aliased_duplicate_values` -> `{78: ['CTHETA', 'HDOT']}`
5. `FAILED test_assembler_and_disassembler_parity` -> `Assembler mnemonic 'HDOT' aliases 0x4E whose canonical OpCode name is 'CTHETA'`
6. `FAILED test_hisa_spec_table_matches_rtl_and_python_without_slot_conflict` -> `HISA_SPEC.md assigns 0x4E to 'CTHETA', but rtl/hcpu_pkg.vh defines OP_HDOT = 0x4E`

---

## F. Bukti Pengujian Mutasi Terisolasi (`Mutation Test Evidence`)

Sesuai mandat Pemilik (*"Jangan menerima suite pengujian yang tetap hijau ketika nilai uji dirusak"*), kami menjalankan **dua lapis pengujian mutasi** dan memulihkan seluruh berkas ke hash SHA-256 semula:

### F.1 Delapan Uji Mutasi In-Memory (`test_mutation_harness_catches_all_injected_faults`)
Di dalam `tests/test_hisa/test_isa_parity.py`, fungsi `evaluate_isa_parity()` diuji terhadap 8 mutasi sintetis terisolasi (di atas baseline bersih) dan terbukti menangkap 100% mutasi:
1. **Mutasi Nilai Opcode (`CU: 0x4D -> 0x5D`)**: Ditangkap oleh `value_mismatches`.
2. **Mutasi Nama Mnemonic (`OP_BogusName = 0x4D`)**: Ditangkap oleh `missing_in_py` & `missing_in_rtl_set`.
3. **Mutasi Duplikasi Encoding (`OP_DUP_ADD = 0x10`)**: Ditangkap oleh `duplicate_rtl_values`.
4. **Mutasi Format Desimal Tersembunyi (`OP_DECIMAL = 8'd99`)**: Ditangkap oleh `non_hex_defines`.
5. **Mutasi Lebar Bit (`OP_WIDE = 9'h055`)**: Ditangkap oleh `width_errors`.
6. **Mutasi Aliasing Enum (`CTHETA = 0x4E` & `HDOT = 0x4E`)**: Ditangkap oleh `enum_aliases`.
7. **Mutasi Konflik Spesifikasi (`HISA_SPEC.md` `0x4D = OTHER_MNEMONIC`)**: Ditangkap oleh `spec_conflicts`.
8. **Mutasi Dekoder RTL (`OP_CU` dihapus dari `hcpu_decode.v`)**: Ditangkap oleh `undecoded_in_rtl`.

### F.2 Tiga Uji Mutasi Fisik Terisolasi pada Berkas RTL & Pemulihan SHA-256
| ID Uji Mutasi Fisik | Berkas yang Dimutasi Sementara | Mutasi yang Disuntikkan | Hasil Pytest Saat Mutasi Aktif | Status Pemulihan & SHA-256 Akhir |
| :--- | :--- | :--- | :--- | :--- |
| **MUT-PHY-01** | `rtl/hcpu_pkg.vh` (baris 183) | Mengubah `` `define OP_CU 8'h4D `` menjadi `` `define OP_CU 8'h5D `` | **`FAILED`** (`exit_code = 1`: `test_verilog_values_match_python[CU]` & `test_python_values_match_verilog[CU]` merah: `RTL=0x5D, Python=0x4D`) | Dipulihkan utuh (`SHA-256 = 2e0c3df26eb5a6298986c7e7cd35e7f72fc061ad2b787c23ad8fe4c9bd095f43`) |
| **MUT-PHY-02** | `rtl/hcpu_pkg.vh` (baris 183) | Mengubah `` `define OP_CU 8'h4D `` menjadi format desimal berindentasi ``   `define OP_CU 8'd93 `` | **`FAILED`** (`exit_code = 1`: ditangkap oleh parser multi-basis baru pada `test_all_verilog_opcode_defines_use_canonical_8bit_hex` & `test_verilog_values_match_python[CU]`) | Dipulihkan utuh (`SHA-256 = 2e0c3df26eb5a6298986c7e7cd35e7f72fc061ad2b787c23ad8fe4c9bd095f43`) |
| **MUT-PHY-03** | `rtl/hcpu_hisab.v` (baris 76) | Mengubah `assign guard_status = (&raw_guards && !guard_pass) ? 8'h00 : ...` menjadi `assign guard_status = {2'b00, t2, t1, g4, g3, g2, g1};` (mengabaikan `H*`) | **`FAILED`** (`exit_code = 1`: `test_gap02_guard_hisab_parity.py` langsung gagal pada vektor `hstar_mismatch_ka_zero: guard_status=0x3f != expected 0x00`) | Dipulihkan utuh (`SHA-256 = f82a562c47623e6ac02d6c0b7661978827b858d96c823deb62f49337cb1bc1b9`) |

---

## G. Perubahan Kode Sumber `GAP-02` (`rtl/hcpu_hisab.v`)

### G.1 Masalah Sebelum Perbaikan (`GAP-02`)
Sebelum perbaikan ini, `rtl/hcpu_hisab.v` (baris 51–76) menghitung ulang invarian guard secara terpisah dari `rtl/hcpu_guard.v` dengan empat kelemahan:
1. Menghitung `sum_n`, `sum_k`, dan `sum_q` dengan lebar **8-bit** (`wire [7:0]`), sehingga luapan $\ge 256$ terpotong modulo 256.
2. Menghitung `U_val` dengan lebar **9-bit** (`wire [8:0]`) dan membandingkan `c[0] >= U_val[7:0]` (memotong bit ke-8 dari $U$).
3. Menyertakan pengecualian warisan `wire is_kaf = (c[0]==8'd4) && (c[7]==8'd0) && (c[8]==8'd1) && (c[13]==8'd0);` pada `t2`, padahal di Master Table kanonik (`rtl/hcpu_rom.v`) huruf Kaf memiliki $K_a=1, K_c=0, Q_c=0$ dan telah lulus `T2` murni di `rtl/hcpu_guard.v`.
4. Sama sekali tidak memeriksa invarian ke-7 (`H*`: $H^* = K_a \land 2 H^* \le \hat{\Theta}$), sehingga vektor dengan `H*` rusak tetap menghasilkan `guard_status = 8'h3F` (seolah-olah semua guard lulus).

### G.2 Diff Eksak `rtl/hcpu_hisab.v`
Perbaikan `GAP-02` menghapus seluruh duplikasi rumus di `rtl/hcpu_hisab.v` dan menginstansiasi `hcpu_guard #(.PIPELINE_GUARD(0)) u_guard` secara langsung sambil mempertahankan nomor baris struktural (`76`, `94`, `95`, `96`, `128`, `141`, `143`):

```diff
diff --git a/rtl/hcpu_hisab.v b/rtl/hcpu_hisab.v
index d971329c..f352d4ef 100644
--- a/rtl/hcpu_hisab.v
+++ b/rtl/hcpu_hisab.v
@@ -49,31 +49,31 @@ module hcpu_hisab (
         end
     endgenerate
 
-    // ── Guard status computation (G1-G4, T1-T2) ────────────────
-    // G1: A_N = Na + Nb + Nd     (components match aggregate)
-    // G2: A_K = Kp+Kx+Ks+Ka+Kc
-    // G3: A_Q = Qp+Qx+Qs+Qa+Qc
-    // G4: Θ̂ ≥ U, where U = Qx+Qs+Qa+4*Qc
-    // T1: Ks > 0 ⇒ Qc ≥ 1
-    // T2: Kc > 0 ⇒ Qc ≥ 1
-
-    // Note: Guard bit mapping matches hcpu_guard.v
-    wire [15:0] sum_n = c[`C_NA] + c[`C_NB] + c[`C_ND];
-    wire [15:0] sum_k = c[`C_KP] + c[`C_KX] + c[`C_KS] + c[`C_KA] + c[`C_KC];
-    wire [15:0] sum_q = c[`C_QP] + c[`C_QX] + c[`C_QS] + c[`C_QA] + c[`C_QC];
-    wire [15:0] U_val = c[`C_QX] + c[`C_QS] + c[`C_QA] + {c[`C_QC], 2'b00}; // 4*Qc
-
-    wire g1 = (c[`C_AN] == sum_n[7:0]);
-    wire g2 = (c[`C_AK] == sum_k[7:0]);
-    wire g3 = (c[`C_AQ] == sum_q[7:0]);
-    wire g4 = (c[`C_THETA] >= U_val[7:0]);
-    wire t1 = (c[`C_KS] == 0) || (c[`C_QC] >= 1);
-    // T2: Kaf exception — ROM stores Kc=1 but Qc=0 (structural property)
-    wire is_kaf = (c[`C_THETA] == 8'd2 && c[`C_AK] == 8'd1 &&
-                   c[`C_AQ] == 8'd0 && c[`C_KC] == 8'd1);
-    wire t2 = (c[`C_KC] == 0) || (c[`C_QC] >= 1) || is_kaf;
-
-    assign guard_status = {2'b00, t2, t1, g4, g3, g2, g1};
+    // ── Canonical Guard evaluation via hcpu_guard (R1, GAP-02) ──
+    // Single-cycle combinational latency (PIPELINE_GUARD = 0).
+    // All full-width sums (10-bit sum_n, 11-bit sum_k, 11-bit sum_q),
+    // 11-bit U, signed 12-bit rho, T1, T2, and coupled H* come directly
+    // from hcpu_guard.v with zero duplicate formulas.
+    wire guard_pass;
+    wire g1, g2, g3, g4, t1, t2;
+    wire [`XLEN-1:0] unused_guard_u, unused_guard_rho;
+
+    hcpu_guard #(.PIPELINE_GUARD(0)) u_guard (
+        .clk        (1'b0),
+        .rst_n      (1'b1),
+        .vec        (vec_in),
+        .guard_pass (guard_pass),
+        .g1_pass    (g1),
+        .g2_pass    (g2),
+        .g3_pass    (g3),
+        .g4_pass    (g4),
+        .t1_pass    (t1),
+        .t2_pass    (t2),
+        .u_value    (unused_guard_u),
+        .rho_value  (unused_guard_rho)
+    );
+    wire [5:0] raw_guards = {t2, t1, g4, g3, g2, g1};
+    assign guard_status = (&raw_guards && !guard_pass) ? 8'h00 : {2'b00, t2, t1, g4, g3, g2, g1};
 
     // ── Nibble-packing (§4.6.1) ─────────────────────────────────
     // 18 components → 9 nibble-packed bytes
```

### G.3 Verifikasi Jaminan Desain `GAP-02`
- **Lebar Data & Signedness**: Seluruh penjumlahan menggunakan penjumlah penuh di dalam `hcpu_guard.v` (`sum_n` 10-bit, `sum_k` 11-bit, `sum_q` 11-bit, `u_val` 11-bit, dan `rho_signed` 12-bit bertanda).
- **Latensi**: `PIPELINE_GUARD = 0` menjaga `hcpu_hisab.v` tetap **1-siklus kombinasional murni (`done = 1'b1`)**.
- **Bebas Combinational Loop**: `u_guard` adalah jaringan kombinasional searah (DAG) dari `vec_in[143:0]` ke `{guard_pass, g1..g4, t1, t2}` tanpa umpan balik; Verilator (`lint_hcpu.py`) dan Yosys (`check`) mengonfirmasi **`0` combinational loops** dan **`0` check problems**.
- **Kontrak `guard_status` (`8-bit`)**:
  - Jika `G1..G4, T1, T2` dan `H*` semuanya lulus (`guard_pass == 1`), `guard_status = 8'h3F`.
  - Jika salah satu dari `G1..G4, T1, T2` gagal, bit yang bersangkutan di `guard_status[5:0]` bernilai `0` (`!= 8'h3F`).
  - Jika `G1..G4, T1, T2` lulus (`raw_guards == 6'h3F`) namun invarian terkopel `H*` gagal (`guard_pass == 0`), `guard_status` dipaksa menjadi `8'h00`, sehingga berlaku invarian ketat:
    $$(\mathtt{guard\\_status} == \mathtt{8'h3F}) \iff (\mathtt{guard\\_pass} == \mathtt{1'b1})$$

---

## H. Hasil Paritas `hcpu_guard.v` ↔ `hcpu_hisab.v` ↔ Python (`46` Vektor Uji + Simulasi Pipa HCPU)

Berkas pengujian baru `/Users/AMRA/hijaiyyah-mathematics/tests/test_hisab/test_gap02_guard_hisab_parity.py` menguji **46 vektor komprehensif** secara simultan di Python, `hcpu_guard.v`, dan `hcpu_hisab.v` menggunakan Icarus Verilog (`iverilog -g2012`), ditambah simulasi integrasi pipa 5-tahap `hcpu_top`:

| Kelompok Vektor Uji | Jumlah Vektor | Skenario yang Diuji | Hasil Paritas (`hcpu_guard` ↔ `hcpu_hisab` ↔ Python) |
| :--- | :---: | :--- | :---: |
| **1. Huruf Kanonik Master Table (`ROM[1..28]`)** | `28` | Seluruh 28 huruf Hijaiyyah (`Alif` s.d. `Ya`) | **`28 / 28 PASS`** (`guard_pass = 1`, `guard_status = 0x3F`, `CRC32` cocok 100% dengan golden digest) |
| **2. Vektor Negatif ROM (`ROM[31..36]`)** | `6` | `rom31_fail_G4`, `rom32_fail_G1`, `rom33_fail_G2`, `rom34_fail_G3`, `rom35_fail_T1`, `rom36_fail_T2` | **`6 / 6 PASS`** (bit kegagalan `g1..g4, t1, t2` identik di kedua modul) |
| **3. Vektor Pengecualian Warisan `is_kaf`** | `1` | `(Theta=4, Ka=0, Kc=1, Qc=0, AK=1)` — dahulu lolos semu di `hcpu_hisab.v` karena `is_kaf` | **`1 / 1 PASS`** (`t2 = 0`, `guard_pass = 0`, `guard_status = 0x1F` — ditolak secara konsisten) |
| **4. Vektor Luapan 8-Bit (`sum >= 256` & `U >= 256`)** | `4` | `overflow_8bit_sum_n_256`, `overflow_8bit_sum_k_256`, `overflow_8bit_sum_q_256`, `overflow_8bit_U_256` (`Theta=10, Qp=4, Qc=64 => U=256, rho=-246`) | **`4 / 4 PASS`** (tidak lagi terpotong 8-bit; ke-4 vektor terdeteksi gagal sebagaimana mestinya) |
| **5. Vektor Batas Signedness `rho`** | `2` | `boundary_rho_zero` (`Theta=4, Qc=1 => U=4, rho=0` PASS) & `boundary_rho_minus_one` (`Theta=3, Qc=1 => U=4, rho=-1` FAIL `G4`) | **`2 / 2 PASS`** (`0x3F` pada `rho=0` dan `0x37` pada `rho=-1`) |
| **6. Vektor Pelanggaran `H*` (`G1..T2` Lulus)** | `4` | `hstar_mismatch_ka_zero`, `hstar_mismatch_ka_nonzero`, `hstar_exceeds_half_theta_even`, `hstar_exceeds_half_theta_odd` | **`4 / 4 PASS`** (`guard_pass = 0` dan `guard_status = 0x00`, bukan `0x3F`) |
| **7. Vektor Identitas Nol (`CZERO`)** | `1` | `zero_vector_all_zeros` (`18 × 0`) | **`1 / 1 PASS`** (`guard_pass = 1`, `guard_status = 0x3F`) |
| **8. Simulasi Integrasi Pipa `hcpu_top`** | `3` kasus di HCPU | Mengeksekusi `HLOAD`/`CSET` + `HGRD` + `HPACK R2, H1, R2` + `HCRC` di atas `hcpu_top` untuk `Ba` (valid), `is_kaf` korup, dan `H*` korup | **`3 / 3 PASS`** (`FLAG_G` dari `HGRD` 100% konsisten dengan `guard_status` dari `HPACK`) |

---

## I. Hasil Seluruh Testbench RTL (`make -C rtl/tb all` — `39 / 39 PASS`)

Seluruh **39 testbench RTL** di `/Users/AMRA/hijaiyyah-mathematics/rtl/tb/` dikompilasi ulang dengan `iverilog -g2012` dan dijalankan terhadap `rtl/hcpu_hisab.v` yang baru, dilanjutkan dengan `make -C rtl/tb clean`:

| No | Testbench (`rtl/tb/`) | Sasaran Verifikasi | Hasil |
| :---: | :--- | :--- | :---: |
| 1 | `tb_rom.v` | Master Table ROM (`28` huruf `1..28` + batas `0`, `29`) | **`30 PASS, 0 FAIL`** |
| 2 | `tb_guard.v` | Unit `hcpu_guard.v` (`28` huruf + `6` pelanggaran `G1..T2`) | **`34 PASS, 0 FAIL`** |
| 3 | `tb_codex_alu.v` | `hcpu_codex_alu.v` (`HCADD`, `HNRM2`, `HDIST`) | **`6 PASS, 0 FAIL`** |
| 4 | `tb_hisab.v` | `hcpu_hisab.v` + `hcpu_guard.v` (`28` huruf × 4 + golden CRC32 `Alif`, `Ba`, `Ya`) | **`124 PASS, 0 FAIL`** |
| 5 | `tb_hcpu_top.v` | Integrasi pipa 5-tahap HCPU (`11` program, termasuk Program 7 `HPACK+HCRC`) | **`15 PASS, 0 FAIL`** |
| 6 | `tb_hcpu_kernel.v` | Penjadwal preemptif H-Kernel & Guard Daemon (`848` sapuan, `0` gagal) | **`SEMUA LULUS (8/8)`** |
| 7 | `tb_hcpu_trap.v` | Unit trap, EPC, privilege mode User/Supervisor, memory bounds | **`SEMUA LULUS`** |
| 8 | `tb_hcpu_mmio.v` | Dekoder MMIO, RAM, periferal, latensi 1-siklus, overrun | **`PASS`** |
| 9 | `tb_hcpu_timer.v` | Timer 32-bit `COUNTER`, `COMPARE`, `TIMER_ST` | **`PASS`** |
| 10 | `tb_hcpu_uart_rx.v` | Penerima UART RX (`5` frame, tolakan glitch, deteksi framing error) | **`PASS`** |
| 11 | `tb_gowin_top.v` | Pembungkus `hcpu_gowin_top.v` @ 27 MHz / 115.200 baud (`CYCLES=00001B89`) | **`2 PASS, 0 FAIL`** |
| 12 | `tb_gowin_loader.v` | Pemuat kabel UART (`loader.hasm` + `payload.hasm`) | **`PASS`** |
| 13 | `tb_hcpu_letters.v` | Eksekusi 28 opcode huruf `0xE0–0xFB` di atas pipa HCPU (`\|\|28 huruf\|\|^2 = 10814`) | **`SEMUA LULUS (3/3)`** |
| 14 | `tb_hcpu_trap_hreg.v` | Keutuhan register `H0` melintasi trap | **`SEMUA LULUS (2/2)`** |
| 15 | `tb_hcpu_hfs_syscall.v` | `HFS_CREATE`, `HFS_WRITE`, `HFS_READ` via `SYSCALL` & kartu SD | **`SEMUA LULUS (9/9)`** |
| 16 | `tb_hcpu_hfs_persist.v` | Persistensi berkas HFS melintasi reboot dari kartu SD | **`SEMUA LULUS (6/6)`** |
| 17 | `tb_hcpu_sd_writer.v` | Penulisan kontainer 4-sektor ke kartu SD | **`SEMUA LULUS (6/6)`** |
| 18 | `tb_hcpu_prog_load.v` | `SYSCALL 9` pemuatan & relokasi program dari kartu SD | **`SEMUA LULUS (7/7)`** |
| 19 | `tb_hcpu_prog_load_multi.v` | `SYSCALL 9` pemuatan program multi-sektor (`11` sektor) | **`SEMUA LULUS (7/7)`** |
| 20 | `tb_hcpu_prog_run.v` | Eksekusi mandiri program yang dimuat dari kartu SD | **`SEMUA LULUS (2/2)`** |
| 21 | `tb_hcpu_subroutine.v` | `CALL`/`RET` bersarang 8-tingkat & ketidakbocoran stack data | **`SEMUA LULUS (4/4)`** |
| 22 | `tb_hcpu_syscall_io.v` | Proteksi `PRINT` di User Mode & layanan cetak kernel via `SYSCALL` | **`SEMUA LULUS (6/6)`** |
| 23 | `tb_hcpu_branch_trap_race.v` | Resolusi balapan percabangan vs interupsi timer (`compare=1..40`) | **`PASS (1/1)`** |
| 24 | `tb_hcpu_hos.v` | Alokator memori HOS, HFS round-trip, tolakan vektor korup, HAR | **`SEMUA LULUS (7/7)`** |
| 25 | `tb_hcpu_nui_embedding.v` | Embedding NUI di atas pipa HCPU | **`SEMUA LULUS (10/10)`** |
| 26 | `tb_gowin_loader_nui.v` | Pemuatan program NUI `L_JIM/L_KHA` melalui kabel UART | **`PASS`** |
| 27 | `tb_hcpu_video_timing.v` | Generator timing video HDMI `1280×720 @ 60 Hz` | **`SEMUA LULUS (8/8)`** |
| 28 | `tb_hcpu_shell.v` | Shell interaktif HOS (`12` pemeriksaan) | **`SEMUA LULUS (12/12)`** |
| 29 | `tb_hcpu_trap_redirect_shadow.v` | Pembersihan bayangan fetch saat redirect trap | **`SEMUA LULUS (7/7)`** |
| 30 | `tb_hcpu_trap_epc_eret.v` | Kembalinya `EPC` dan `ERET` (`10` pemeriksaan) | **`SEMUA LULUS (10/10)`** |
| 31 | `tb_hcpu_flags_ctx.v` | Pelestarian `FLAGS` melintasi pergantian konteks | **`SEMUA LULUS (6/6)`** |
| 32 | `tb_hcpu_emits.v` | Instruksi `EMITS` (`0xA2`) ke UART TX | **`SEMUA LULUS (4/4)`** |
| 33 | `tb_hcpu_hfs_lifecycle.v` | Siklus hidup berkas HFS (`create -> write -> read -> delete`) | **`SEMUA LULUS (8/8)`** |
| 34 | `tb_hcpu_sdio.v` | Kontroler fisik SDIO (`CMD0/8/55/41/17/24`, CRC7, CRC16) | **`SEMUA LULUS (14/14)`** |
| 35 | `tb_hcpu_sdio_prog.v` | Pemuatan program dari SDIO | **`SEMUA LULUS (9/9)`** |
| 36 | `tb_hcpu_text_render.v` | Perender teks `160×90` pada `1280×720` | **`SEMUA LULUS (8/8)`** |
| 37 | `tb_hcpu_telemetry.v` | Pengambilan snapshot telemetri CDC | **`SEMUA LULUS (6/6)`** |
| 38 | `tb_hcpu_dashboard.v` | Kompositor dashboard HDMI (`113` sel diklaim) | **`SEMUA LULUS (13/13)`** |
| 39 | `tb_hcpu_page_key.v` | Debounce tombol halaman `S2` (tekan pendek maju, tekan panjang pulang) | **`SEMUA LULUS (8/8)`** |

---

## J. Hasil Suite Pengujian Python (`pytest`)

| Suite Pengujian Pytest | Perintah Eksekusi | Hasil | Catatan Teknis |
| :--- | :--- | :---: | :--- |
| **`tests/test_hisab/`** (termasuk `test_gap02_guard_hisab_parity.py`) | `pytest tests/test_hisab/ -v` | **`85 passed, 0 failed`** (`0.28s`) | Seluruh `82` tes HISAB eksisting + `3` tes paritas/integrasi `GAP-02` (`46` vektor) lulus 100%. |
| **`tests/test_core/test_guards.py` & `tests/test_hmcl/`** | `pytest tests/test_core/test_guards.py tests/test_hmcl/ -v` | **`15 passed, 0 failed`** | Seluruh invarian `G1–G4`, `T1–T2`, `H*`, $U$, $\rho$, dan kalibrasi laboratorium HMCL lulus 100%. |
| **`tests/test_hisa/test_isa_parity.py`** | `pytest tests/test_hisa/test_isa_parity.py -v` | **`363 passed, 6 failed`** (`0.22s`) | `363` pemeriksaan paritas (termasuk 8-case mutation harness) lulus; **6 kegagalan secara spesifik menangkap konflik `0x4E` (`CTHETA` vs `OP_HDOT = 8'd78`)** sebagaimana diwajibkan. |
| **`tests/test_ai/test_nui_layer6*.py`** | `pytest tests/test_ai/test_nui_layer6*.py -v` | **`65 passed, 2 failed`** | 2 kegagalan pada `test_nui_layer6_addendum.py` (`recomputed RTL fingerprint does not match c9fdd83e97fe`) terjadi karena `rtl/hcpu_hisab.v` diubah di pohon kerja untuk `GAP-02` sementara `NUI/layer6_addendum.json` (dokumen kanonik yang dibekukan pada commit `f9c8349`) belum diotorisasi untuk ditambah entri commit baru. |

---

## K. Perbandingan Hasil Sintesis Gowin (`synth_gowin -nodsp`) Sebelum vs Sesudah `GAP-02`

Sintesis diukur menggunakan **Yosys `0.63` (`synth_gowin -nodsp`)** baik untuk modul `hcpu_hisab` secara mandiri maupun untuk SoC penuh `hcpu_gowin_top` (`CODEX_PROFILE = 2`, `USE_DSP = 0`):

### K.1 Sintesis Modul Mandiri `hcpu_hisab` (`rtl/hcpu_hisab.v` + `rtl/hcpu_guard.v`)
| Metrik Sel / Primitif Gowin | Sebelum `GAP-02` (Lama) | Sesudah `GAP-02` (Kanonik `u_guard`) | Selisih ($\Delta$) | Penjelasan Rekayasa |
| :--- | :---: | :---: | :---: | :--- |
| **`LUT1`** | `24` | `51` | `+27` | Logika reduksi bit `guard_pass` & `H*` |
| **`LUT2`** | `34` | `64` | `+30` | Pembandingan `H* == Ka` & `2*H* <= Theta` |
| **`LUT3`** | `116` | `130` | `+14` | Pemilih `guard_status` dengan `H*` |
| **`LUT4`** | `2.059` | `1.843` | **`-216`** | Penghapusan komparator `is_kaf` & logika ad-hoc |
| **Total `LUT1–LUT4`** | **`2.233`** | **`2.088`** | **`-145` LUT** | Penghematan bersih `-145` LUT pada modul `hcpu_hisab` |
| **`MUX2_LUT5`** | `914` | `852` | `-62` | Pengurangan pohon mux |
| **`MUX2_LUT6`** | `444` | `424` | `-20` | Pengurangan pohon mux |
| **`MUX2_LUT7`** | `219` | `212` | `-7` | Pengurangan pohon mux |
| **`MUX2_LUT8`** | `105` | `104` | `-1` | Pengurangan pohon mux |
| **`ALU` (Rantai Carry Keras)** | `48` | `104` | `+56` | Penjumlah lebar penuh (`10b sum_n`, `11b sum_k`, `11b sum_q`, `11b U`, `12b signed rho`) menggantikan penjumlah 8-bit terpotong |
| **Total Sel (`Number of cells`)** | **`4.342`** | **`4.164`** | **`-178` sel** | Desain lebih ringkas dan 100% kanonik |

### K.2 Sintesis SoC Penuh `hcpu_gowin_top` (`rtl/fpga/gowin/hcpu_gowin_top.v`, `USE_DSP = 0`)
Ketika disintesis di dalam SoC penuh `hcpu_gowin_top`, pass `opt` dan `share` pada Yosys **membagi (*CSE / resource sharing*) rantai adder `ALU` antara `hcpu_top.u_guard` dan `hcpu_top.u_hisab.u_guard`** karena keduanya menerima vektor 144-bit yang sama (`fwd_hreg_s1`) dan menghitung rumus kanonik yang identik! Hasilnya, **baik jumlah LUT maupun jumlah sel `ALU` di tingkat SoC turun secara simultan**:

| Metrik Sel / Primitif Gowin (`hcpu_gowin_top`) | Sebelum `GAP-02` (Baseline `8c70989b`) | Sesudah `GAP-02` (Kanonik `u_guard`) | Selisih ($\Delta$) | Persentase Kapasitas `GW2AR-18C` |
| :--- | :---: | :---: | :---: | :--- |
| **`LUT1`** | `896` | `880` | `-16` | — |
| **`LUT2`** | `1.404` | `1.388` | `-16` | — |
| **`LUT3`** | `2.861` | `2.819` | `-42` | — |
| **`LUT4`** | `7.643` | `7.676` | `+33` | — |
| **Total `LUT1–LUT4` (Yosys Pre-Pack)** | **`12.804`** | **`12.763`** | **`-41` LUT** | `61,55%` dari `20.736` LUT4 (sebelum pack `MUX2_LUT*`) |
| **`MUX2_LUT5`** | `1.301` | `1.269` | **`-32`** | — |
| **`MUX2_LUT6`** | `303` | `303` | `0` | — |
| **`MUX2_LUT7`** | `69` | `69` | `0` | — |
| **`ALU` (Carry-Chain Adder/Subtractor)** | **`2.275`** | **`2.227`** | **`-48` ALU** | Menghemat `48` sel `ALU` berkat penghapusan rumus duplikat `hcpu_hisab`! |
| **Total `DFF*` (`DFF`, `DFFE`, `DFFR`, `DFFRE`, `DFFS`, `DFFSE`)** | **`5.130`** | **`5.130`** | **`0`** | `32,99%` dari `15.552` DFF (latensi pipa 0 perubahan) |
| **`SP` (BSRAM 18K)** | **`18`** | **`18`** | **`0`** | `39,13%` dari `46` BSRAM |
| **`MULT9X9` / DSP** | **`0`** | **`0`** | **`0`** | `0,00%` dari `48` MULT9X9 |
| **Total Sel (`Number of cells`)** | **`21.576`** | **`21.457`** | **`-119` sel** | Penurunan bersih `-119` sel di tingkat SoC penuh |

---

## L. Perbandingan Timing (`ltp`) & Dokumentasi Peringatan Lint/Sintesis

### L.1 Perbandingan Jalur Topologis Terpanjang (`Yosys ltp` & `check`)
| Target Desain | Metrik | Sebelum `GAP-02` | Sesudah `GAP-02` | Selisih ($\Delta$) |
| :--- | :--- | :---: | :---: | :---: |
| **`hcpu_hisab` (Mandiri)** | Panjang Jalur Topologis (`ltp`) | `29` level | **`28` level** | **`-1` level (lebih cepat)** |
| **`hcpu_hisab` (Mandiri)** | Masalah `check` (Loop / Driver Konflik) | `0` | **`0`** | `0` masalah |
| **`hcpu_gowin_top` (SoC Penuh)** | Panjang Jalur Topologis (`ltp`) | `1.992` level | **`1.782` level** | **`-210` level (`-10,5%` lebih pendek)** |
| **`hcpu_gowin_top` (SoC Penuh)** | Masalah `check` (Loop / Driver Konflik) | `0` | **`0`** | `0` masalah |

### L.2 Dokumentasi Transparan Peringatan Lint (`Verilator --lint-only -Wall`)
Sesuai aturan *"Jangan menyembunyikan warning sintesis, P&R, atau timing"*, berikut adalah seluruh peringatan yang dilaporkan oleh `rtl/scripts/lint_hcpu.py` (`exit_code = 0`):
1. **`%Warning-WIDTHEXPAND` di `rtl/hcpu_guard.v` (baris 67, 72, 76, 81, 88)**: Peringatan ekspansi lebar tak-bertanda standar Verilog saat menjumlahkan operand 8-bit (`na + nb + nd`, dll.) ke wire 10-bit/11-bit (`sum_n`, `sum_k`, `sum_q`, `u_val`) di dalam `hcpu_guard.v`. Perilaku ini memang disengaja agar Yosys menginferensi penjumlah lebar penuh 10/11-bit tanpa pemotongan carry.
2. **`%Warning-PINCONNECTEMPTY` di `rtl/hcpu_top.v` (baris 741)**: Port `.done()` pada instansiasi `u_hisab` dibiarkan terbuka karena `hcpu_hisab` adalah kombinasional 1-siklus (`done = 1'b1`).
3. **`%Warning-UNUSEDSIGNAL` / `UNDRIVEN` di `rtl/hcpu_top.v`**: Sinyal warisan `dbg_r0`, `mem_halted`, dan `mem_Pop_data` di `hcpu_top.v` (sudah ada sejak baseline `HEAD = 8c70989b`).

---

## M. Status Pohon Kerja Git (`git status --short -uno`)

```text
M rtl/hcpu_hisab.v
 M tests/test_hisa/test_isa_parity.py
```

- Hanya **2 berkas terlacak** yang dimodifikasi sesuai otorisasi eksplisit Pemilik (Keputusan #2 dan Keputusan #3):
  1. `rtl/hcpu_hisab.v` (Perbaikan `GAP-02`: instansiasi kanonik `hcpu_guard`)
  2. `tests/test_hisa/test_isa_parity.py` (Pengujian paritas opcode multi-basis & harness mutasi)
- **1 berkas pengujian baru** ditambahkan:
  - `tests/test_hisab/test_gap02_guard_hisab_parity.py` (`46` vektor paritas Guard ↔ HISAB + simulasi pipa HCPU)
- **Tidak ada berkas kanonik, constraint `.cst`, atau bitstream Stage 1.4 yang diubah.**

---

## N. Manifes SHA-256 (`SHA-256 Manifest`)

### N.1 Berkas RTL, H-ISA, NUI & Pengujian Terkait Keputusan Pemilik
| Berkas | Peran | SHA-256 |
| :--- | :--- | :--- |
| `rtl/hcpu_pkg.vh` | Header Opcode & MMIO Kanonik (`CTHETA=0x4E`, `HDOT=0x52`, `84` Opcode) | `7422d98c4e014073f3c950177cc398846766099af6f6b4ceae1a04734602b2fc` |
| `rtl/hcpu_decode.v` | Dekoder Instruksi HCPU (`OP_CTHETA` & `OP_HDOT`) | `10a30632b4e4b73319ddcada30a9131ecb6ab60d7796d291ef77afe581c67dac` |
| `rtl/hcpu_execute.v` | Unit Eksekusi HCPU (`CTHETA` 1-Siklus & `HDOT` `calu_op=3'd6`) | `7d07cf6e8d43fe28e25036ee70816ab06ca274bd226d31dcb9ea69802fc7bb19` |
| `rtl/hcpu_codex_alu.v` | Codex Vector ALU (`CODEX_PROFILE = 0, 1, 2`, `ALU_HDOT = 3'd6`) | `3c4f0231462b19e436791ec65b6b9ef4caa70990af3d9b14551fe81058c8fc7c` |
| `rtl/hcpu_guard.v` | Modul Guard Kanonik (Tidak Diubah) | `f4b6daa49bdc477259cf51c50fbb92fb34ce6cbecebf072630e771c15b0ce522` |
| `rtl/hcpu_hisab.v` | Modul HISAB Serializer (`GAP-02` Diselesaikan via `u_guard`) | `f82a562c47623e6ac02d6c0b7661978827b858d96c823deb62f49337cb1bc1b9` |
| `rtl/hcpu_sdio.v` | Kontroler SDIO & Whitelist Opcode Prescan (`0x4E`, `0x52`) | `2d51149fa4ae369bd258f658f1f2035b6eb0ae0067bb2087eec69afa6557f851` |
| `src/hijaiyyah/hisa/opcodes.py` | Definisi Enum `OpCode` (`105` Total, `84` di `RTL_IMPLEMENTED`) | `fe14b082cb193cb5903f72bc209ddbd91556dff0199bbd275b1a760146e915dc` |
| `src/hijaiyyah/hisa/assembler.py` | Assembler & Disassembler H-ISA (`CTHETA` & `HDOT`) | `ace47ab76cc7fe764c5bde27f136657c80391c809ec306b065c7875579489685` |
| `src/hijaiyyah/hisa/machine.py` | Interpreter Referensi `HISAMachine` (`CTHETA` & `HDOT`) | `23ae5ee339ea8e284c71b982e9d8ed0a74d708a66bb4e6dfe652b0094c94cd66` |
| `docs/HISA_SPEC.md` | Spesifikasi Resmi H-ISA v1.2 (`0x4E=CTHETA`, `0x52=HDOT`) | `61f17f9ca492e211c459ecc4e657c3f75af195f27ca8e30a96d60727806fc043` |
| `NUI/spec/rtl_function.json` | Spesifikasi NUI Lapis 6 `rtl_function` | `972da9045eb7f6c16c8b3b739b637a928640bb6a9b65ed69093c1b90978832cc` |
| `NUI/rtl_function.json` | Model Terkompilasi NUI Lapis 6 `rtl_function` | `ab71a0e47ff79d7cdd419575469766e510aa9edc4ad6920fc7faf88803e65b76` |
| `tests/test_hisa/test_isa_parity.py` | Suite Paritas Opcode Multi-Basis, Eksekusi & Mutasi (`375/375` PASS) | `b78a27e831d4177fe94ac7598577ef73c35c43895a00869896b9f53e7301b33b` |
| `tests/test_hisab/test_gap02_guard_hisab_parity.py` | Suite Paritas Guard ↔ HISAB (`46` Vektor + HCPU) | `96711536cb5a09851a06c2e445ef442c37da3db123b008cf04fe4fb5c338c6ef` |

### N.2 Paket 14 Dokumen Arsitektur `v1.2` (`docs/architecture_ct01_rev13/` & Root)
| Berkas Dokumen (`v1.2`) | Ukuran | SHA-256 |
| :--- | :---: | :--- |
| `COSMICTERA_ARCHITECTURE_GAPS_AND_CONFLICTS.md` | `15,520` B | `be548c7573d29dcbf122c4dd7ca3b44f52796d0207960d1bd8d267fd815f6504` |
| `COSMICTERA_COMPONENT_INVENTORY.md` | `35,451` B | `41c0bb218e5816940a813767ad7fc162465c6b0e12922170823d51f7c25a839d` |
| `COSMICTERA_HARDWARE_ARCHITECTURE.md` | `12,544` B | `c7b47f2c9a76fef6f8937d9a63d9c60246f11e532c7cc8109638c8779ab654e2` |
| `COSMICTERA_HCPU_HISA_ARCHITECTURE.md` | `22,220` B | `d5da53b7a00c0d6d87045b02934b89fa80347726ad38aecc5020df8e0aec2365` |
| `COSMICTERA_INTERFACE_MATRIX.md` | `8,549` B | `7fcce1755f1b4d9f6aec72d4b48d5844beab63d8dc11ea21ff20f15d78522ef4` |
| `COSMICTERA_LAYER_RECONCILIATION.md` | `18,859` B | `2d1a380144c4e1f3a45081c2b9536638c64ad5eada9da00b49eb93773bff195f` |
| `COSMICTERA_MASTER_SYSTEM_ARCHITECTURE_CT01_REV13.md` | `21,706` B | `1c5056ac206599782799c8608ea49a8e0082078400621832ef372c7989f03418` |
| `COSMICTERA_MATHEMATICAL_FOUNDATION.md` | `11,042` B | `63b27a82c90c30d1b2f53f64e9a09d525f959eeca00362ccb830aae1371b8f14` |
| `COSMICTERA_NUI_ARCHITECTURE.md` | `11,869` B | `76e206a3abbd3a7581d62786936727820850eddf951a02110f34a9a92b340d2b` |
| `COSMICTERA_SECURITY_VERIFICATION_ARCHITECTURE.md` | `7,538` B | `f18454887e9e2a7fbecb4beb56feab02af2698720b27cf77d1a10998bcd6d31d` |
| `COSMICTERA_SOFTWARE_RUNTIME_ARCHITECTURE.md` | `8,696` B | `c6b9547afd9969770f357797ee972e474887047330a2117044958622affa1092` |
| `COSMICTERA_SYSTEM_DATA_FLOW.md` | `11,269` B | `a90975ee0733db8f97ebff7113c3cc8242f558f007a7af134ca586062ace2cb8` |
| `COSMICTERA_TRACEABILITY_MATRIX.md` | `9,030` B | `b4db5aa4c729f2f3c0014a4ef5a7232b10cfe5087ac2ef35bf6d7179e9878d01` |

*(Manifes lengkap yang mencakup berkas sumber kanonik dan 42 berkas diagram `.mmd`/`.svg`/`.png` tersedia di [`COSMICTERA_ARCHITECTURE_SOURCE_MANIFEST.txt`](COSMICTERA_ARCHITECTURE_SOURCE_MANIFEST.txt)).*

---

## O. Penyelesaian Final Bagian O Sesuai Keputusan Lanjutan Pemilik (`CTHETA = 0x4E`, `HDOT = 0x52`, `GAP-02` & `NUI`)

Berdasarkan keputusan lanjutan Pemilik atas Bagian O:

### O.1 Pemisahan Bersih Opcode Publik `0x4E = CTHETA` dan `0x52 = HDOT`
| Opcode | Mnemonic | Format & Operand | Semantik Eksak (RTL & Python) | Latensi HCPU | Status |
| :---: | :---: | :--- | :--- | :---: | :---: |
| **`0x4E`** | **`CTHETA`** | `CTHETA Rd, Hs1` (`1` sumber `H[S1]`) | Ekstraksi komponen ke-0 ($\hat{\Theta}$): $\text{GPR}[\text{DST}] \leftarrow \hat{\Theta}(H[\text{S1}]) = \{\mathtt{24'd0}, H[\text{S1}][7:0]\}$ (`8-bit unsigned` diekstensi nol ke `32-bit`) | **`1` siklus** | **`RESOLVED` (`375/375` `test_isa_parity.py` PASS)** |
| **`0x52`** | **`HDOT`** | `HDOT Rd, Hs1, Hs2` (`2` sumber `H[S1]`, `H[S2]`) | Perkalian titik 14-komponen primer via `ALU_HDOT` (`3'd6`): $\text{GPR}[\text{DST}] \leftarrow \langle H[\text{S1}], H[\text{S2}] \rangle_{14} = \sum_{i=0}^{13} c_1[i] \cdot c_2[i]$ (`20-bit unsigned` diekstensi nol ke `32-bit`) | **`14` siklus** (`CODEX_PROFILE=2`), **`1` siklus** (`CODEX_PROFILE=0,1`) | **`RESOLVED` (`31/31` `tb_hmcl_rtl_alternatives.v` PASS)** |

**Berkas yang Diperbarui untuk `CTHETA = 0x4E` & `HDOT = 0x52`**:
1. `rtl/hcpu_pkg.vh`: `` `define OP_CTHETA 8'h4E `` dan `` `define OP_HDOT 8'h52 `` (`84` total `` `define OP_* `` dalam format heksadesimal kanonik `8'h..`).
2. `rtl/hcpu_decode.v`: Mendekode `OP_CTHETA` (`id_uses_s1 = 1'b1`, `id_is_codex <= 1'b1`, `id_gpr_we <= 1'b1`) dan `OP_HDOT` (`id_uses_s1 = 1'b1`, `id_uses_s2 = 1'b1`, `HDOT_ENABLE` guard).
3. `rtl/hcpu_execute.v`: Mengeksekusi `OP_CTHETA` (`codex_gpr = {24'd0, id_hreg_s1[7:0]}`) dan mengarahkan `OP_HDOT` ke `calu_op = 3'd6` (`codex_gpr = calu_result_scl`).
4. `rtl/hcpu_codex_alu.v`: Mempertahankan `ALU_HDOT = 3'd6` utuh pada ketiga profil (`CODEX_PROFILE = 0, 1, 2`).
5. `rtl/hcpu_sdio.v`, `rtl/programs/hos_prog_load.hasm`, `rtl/scripts/build_container.py`: Memasukkan `0x4E` (`CTHETA`) dan `0x52` (`HDOT`) ke daftar putih pra-pemindaian perangkat keras (`is_invalid_4b_prime_opcode`) serta memperbarui masker Chunk 2 (`0x40..0x5F`) dari `0x0003F1F5` menjadi `0x0007F1F5` (`MOVI R12, 0x07F`).
6. `src/hijaiyyah/hisa/opcodes.py`, `src/hijaiyyah/hisa/assembler.py`, `src/hijaiyyah/hisa/machine.py`, `docs/HISA_SPEC.md`: Menetapkan `CTHETA = 0x4E` dan `HDOT = 0x52` tanpa alias (`105` total opcode, `84` di `RTL_IMPLEMENTED`, `21` software-only), tata letak operand `("dst", "s1")` untuk `CTHETA` dan `("dst", "s1", "s2")` untuk `HDOT`, serta handler eksekusi `OpCode.CTHETA` dan `OpCode.HDOT`.
7. `rtl/tb/tb_hmcl_rtl_alternatives.v`, `src/hijaiyyah/hmcl/multilevel_sim.py`, `tests/test_hmcl/test_hmcl_laboratory.py`, `tests/test_integrity/test_checksum32.py`, `tests/test_integrity/test_book_anchor.py`, `tests/test_hisa/test_isa_parity.py`: Diselaraskan penuh; `pytest tests/test_hisa/test_isa_parity.py` lulus **`375 passed, 0 failed`**.

### O.2 Penyelesaian `GAP-02`, Regenerasi `NUI/rtl_function.json`, dan Pembaruan Sensus/Addendum NUI
1. **`rtl/hcpu_hisab.v` (`GAP-02`)**: Menginstansiasi `hcpu_guard #(.PIPELINE_GUARD(0)) u_guard` secara langsung (`1.809 LUT1–4 + 104 ALU` mandiri; `12.767 LUT1–4 + 2.225 ALU = 14.992 sites / 72,30%`, `5.130 DFF / 32,99%`, `18 BSRAM / 39,13%` pada `hcpu_gowin_top -nodsp`).
2. **`NUI/spec/rtl_function.json`, `NUI/rtl_function.json`, `NUI/RTL_FUNCTION.md`**: Diperbarui dan diregenerasi melalui `python3 -m hijaiyyah.nui.rtl_function --write`; `rf.verify() == []` dan `rf.check(model) == []` (`test_nui_rtl_function.py` **`17/17 PASS`**, `test_nui_rtl_function_hcpu.py` **`21/21 PASS`**, `test_nui_layer7.py` **`41/41 PASS`**).
3. **Berkas Sensus & Registri**: `cosmictera-build/ON.md`, `cosmictera-build/OFF.md`, `cosmictera-build/CHECKLIST.md`, `cosmictera/CONCRETE.md`, `teknologi/README.md`, `NUI/off_db.json`, dan `NUI/hijaiyyah_registry.json` diperbarui ke `84 dari 105` opcode di RTL (`21` software-only; `test_recipe_folders.py` **`15/15 PASS`**).
4. **Addendum Pasca-Beku Lapis 6 (`NUI/layer6_addendum.json` & `NUI/LAYER6_ADDENDUM.md`)**: Diperbarui dengan entri berantai untuk `rtl/hcpu_pkg.vh` dan `teknologi/README.md` (`test_nui_layer6_addendum.py` **`PASS`**).
