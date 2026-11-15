# COSMICTERA CT-01-REV13 — ARCHITECTURE CONSISTENCY REVIEW & GAP CLOSURE (Tahap 1: Rekonsiliasi)

- **Tanggal**: 3 November 2026
- **Baseline**: `HEAD = 8c70989bec0d3b86ace8b657fd8f1d761164b8e3`, 0 berkas terlacak berubah (review read-only).
- **Metode**: setiap angka di bawah dibaca langsung dari sumber kanonik (`rtl/hcpu_pkg.vh`, `src/hijaiyyah/hisa/opcodes.py`, `docs/HISA_SPEC.md`, RTL, `cosmictera/RULES.md`) atau dihitung ulang dengan perintah yang dicantumkan. Tidak ada angka yang disalin dari paket 14 dokumen sebelumnya.

> [!CAUTION]
> Review ini menemukan bahwa **paket 14 dokumen arsitektur sebelumnya (berkas tak terlacak `COSMICTERA_*.md` dan `docs/architecture_ct01_rev13/`) memuat kesalahan faktual serius**, termasuk definisi label epistemik R2 yang salah dan peta opcode/MMIO yang tidak ada di RTL. Paket itu **tidak boleh** dipakai sebagai referensi rekayasa sampai dikoreksi menurut daftar di §7.

---

## 1. Ringkasan keputusan rekonsiliasi

| # | Pertanyaan | Jawaban terukur | Sumber |
|---|---|---|---|
| C-01 | 103 atau 104 opcode? | **104** opcode unik (`OpCode` tanpa alias). **83** didefinisikan di RTL (`define OP_*`), **82** tercatat di `RTL_IMPLEMENTED`, **21** murni software. Angka **103 salah** (keadaan sebelum `HDOT`). | perintah §2 |
| C-02 | "82 RTL / 22 SW" benar? | Hanya benar menurut registry Python yang **tertinggal**: `HDOT` (0x4E) di-decode RTL (`hcpu_decode.v:98,338`, `hcpu_execute.v:249`) tetapi tidak ada di `RTL_IMPLEMENTED`. Faktanya **83 RTL / 21 SW**. | §2 |
| C-03 | Register HCPU | **18 GPR × 32-bit** disimpan (`GPR_COUNT 18`), **hanya R0–R15 dapat dienkode** (field 4-bit). **16 H-Reg × 144-bit** (`HREG_COUNT 16`, `HREG_W 144`). Klaim "H-Reg 8×144b" dan "banking H-Reg per mode privilese" **tidak ada di RTL**. | `hcpu_pkg.vh:20-25`, `hcpu_regfile.v` |
| C-04 | GAP-03 (codegen R17 vs assembler R15) | **Sudah tertutup di kode** oleh `ef209af4` (`GPR_LAST = 15`). Yang tertinggal adalah **catatan** di `NUI/LAYERS.md:173-178` (berkas terlacak) yang masih menyebut R17. | `codegen.py:71-75`, `git log` |
| C-05 | ROM Master Table 144-bit atau 72-bit? | **144-bit per entri** (18 × 8-bit), **34 entri**: huruf 1–28 + vektor negatif 31–36, alamat **6-bit** (`ROM_ADDR_W 6`). "72-bit" adalah lebar **payload nibble HISAB** (9 byte) di `hcpu_hisab.v`, bukan ROM. | `hcpu_rom.v:1-24`, `hcpu_pkg.vh:46-47` |
| C-06 | Empat model lapisan | Model "11-lapis kanonik" **tidak ditemukan** di `docs/ARCHITECTURE.md` (isinya HOM **L0–L7**, delapan lapis) maupun `cosmictera/SYSTEM.md`. Yang terdokumentasi: HOM L0–L7, tumpukan **7 lapis** (`cosmictera/COMPUTING.md`), **13 lapis** CT-01-REV13, NUI Lapis 0–11, dan halaman P0–P12. | §5 |
| C-07 | Unified SoC 17.979 LUT4 aman? | **Tidak.** Tiga pengukuran repo menunjukkan nextpnr menolak penempatan di **16.015**, **16.849** dan **16.882** LUT4; desain teringgi yang ter-place adalah **15.994**. 17.979 berada di atas ketiga titik gagal. | §6 |
| C-08 | Ka'bah tanpa HMAC = autentikasi? | **Tidak.** R10: hanya Lapis 3 (HMAC-SHA256) yang memikul keamanan; Lapis 2 (Absorption) berlabel **EH** dan rank permutasi 1276/1600. | `RULES.md` R8, R10 |

---

## 2. Opcode: angka dan satu lubang gerbang paritas yang baru ditemukan

Perintah (dijalankan 23:47):

```text
rtl/hcpu_pkg.vh OP_* defines            : 83
OpCode enum unique values               : 104
OpCode enum members incl. aliases       : 121
RTL_IMPLEMENTED                         : 82
In hcpu_pkg.vh but not in RTL_IMPLEMENTED: ['OP_HDOT']
Software-only                           : 21  (JGP JGF JNP CSUB CDOT VNORM VDIST HEXMT HDCMP
                                               HSER HDES VSCL HCHK CHASH CSIGN HPROJ VPROJ_T
                                               VPROJ_N VPROJ_K VPROJ_Q PRINTH)
```

### Temuan baru — GAP-06: `HDOT` lolos dari ketiga gerbang paritas, dan 0x4E punya dua nama

1. `rtl/hcpu_pkg.vh:184` menulis `` `define OP_HDOT 8'd78 `` (desimal), sedangkan regex gerbang `tests/test_hisa/test_isa_parity.py` hanya mengenali `8'h..`. Akibatnya `RTL_OPCODES` **tidak memuat HDOT**, sehingga:
   - `test_rtl_implemented_set_is_exactly_the_rtl_header` lulus walaupun `RTL_IMPLEMENTED` tidak memuat HDOT;
   - `test_spec_documents_every_rtl_opcode` tidak menuntut HDOT ada di spesifikasi;
   - `test_software_only_opcodes_avoid_rtl_encodings` tidak melihat 0x4E sebagai encoding RTL.
2. `docs/HISA_SPEC.md:598` menetapkan **0x4E = `CTHETA`** (`GPR[DST] ← Θ̂(H[S1])`). RTL dan Python menetapkan **0x4E = `HDOT`**. Karena `CTHETA` tidak ada di `OpCode` dan `HDOT` tidak ada di tabel spesifikasi, `test_spec_opcode_value_matches` tidak pernah membandingkan keduanya.
3. Hasil: suite tetap **360 passed** — satu encoding dengan dua arti, persis kelas cacat yang dijaga R1 dan `7582ae5`, tidak terlihat oleh tes.

**Usulan penutupan (butuh keputusan pemilik, karena menyentuh berkas terlacak dan spesifikasi beku):**
- (a) ubah literal ke `8'h4E`; (b) tambah `OpCode.HDOT` ke `RTL_IMPLEMENTED`; (c) putuskan nasib slot 0x4E di §6.2 spesifikasi — `CTHETA` atau `HDOT` — menurut §6.0 aturan 2/4; (d) perketat regex gerbang agar menerima `8'd` dan menolak format lain dengan galat, lalu **sabotase** (R3): kembalikan literal desimal dan pastikan tes merah.

---

## 3. Register dan ROM

| Butir | Nilai RTL | Catatan |
|---|---|---|
| GPR | `reg [31:0] gpr[0:17]` | R16/R17 disimpan tetapi tak bisa dinamai instruksi apa pun. `docs/HISA_SPEC.md §4.1` sudah mencatat kontradiksi buku (hal. 127 vs 133) dan memilih 16 yang dapat dialamatkan. Klaim "R16=SP, R17=FP" di audit sebelumnya **tidak bersumber**. |
| H-Reg | `reg [143:0] hreg[0:15]` + `hreg_ovf[15:0]` | 16, bukan 8. Tidak ada banking. |
| FLAGS | G=bit0, Z=bit1, O=bit2, LT=bit3 | `hcpu_pkg.vh:208-211`. Dokumen HCPU sebelumnya menulis Z=0, LT=1, GT=2, G=3 — **salah**. |
| Return stack | `RA_DEPTH 32` | Dokumen sebelumnya menulis 8. |
| ROM | 34 × 144-bit, alamat 6-bit, kombinasional | Interface matrix sebelumnya menulis `rom_addr[4:0]` dan 28 entri — salah. |
| `HISA_SPEC.md §3.2` | "4 H-Reg × 576-bit", "ROM 252 byte" | Spesifikasi **sendiri** tertinggal dari RTL (16 × 144-bit). Dicatat sebagai konflik dokumen-vs-kode; menurut urutan kewenangan, encoding RTL menang (`opcodes.py` docstring, `HISA_SPEC §6.0`). |

---

## 4. GAP-02 — `hcpu_hisab.v` vs `hcpu_guard.v` (dikonfirmasi, belum ditutup)

| Aspek | `hcpu_guard.v` | `hcpu_hisab.v` |
|---|---|---|
| Lebar perbandingan G1–G3 | penuh 10/11-bit | dipotong `[7:0]` (baris 66-68) |
| G4 | `{3'b0,theta} >= u_val` 11-bit | `theta >= U_val[7:0]` (baris 69) |
| T2 | tanpa pengecualian | `is_kaf` warisan (baris 71-74) |
| H* | `hstar_comb` masuk `guard_pass` | tidak diperiksa |
| Definisi U | satu tempat, diekspor `u_value` | dihitung ulang sendiri (baris 64) — melanggar R1 |

Akibat praktis: byte guard dalam frame HISAB (dan CRC-nya) bisa menyatakan "lulus" untuk vektor yang ditolak `HGRD`, misalnya bila jumlah komponen melewati 255 atau bila H* tidak sesuai. Penutupan yang selaras dengan R1: `hcpu_hisab` menerima `g1..t2` (dan H*) **dari** `u_guard` alih-alih menghitung ulang; ukur ulang LUT4 sesudahnya (R4), dan sabotase dengan vektor ber-carry di atas bit 7. Ini perubahan RTL → **keputusan pemilik**.

---

## 5. Model lapisan — dipisahkan, tidak digabung

| Model | Sumber terlacak | Jumlah | Fungsi |
|---|---|---|---|
| HOM | `docs/ARCHITECTURE.md` | L0–L7 (8) + GUI + 3 engine | arsitektur perangkat lunak HOM v1.0 |
| Tumpukan CosmicTera Computing | `cosmictera/COMPUTING.md` §3 | 7 (Perangkat keras → Aplikasi) | status OS/runtime di HCPU |
| CT-01-REV13 | blueprint pemilik | 13 | arah arsitektur tujuan |
| NUI | `NUI/LAYERS.md` | Lapis 0–11 (12), dikunci menurut **nama** | subsistem NUI saja |
| Boot Display | `cosmictera_boot_compositor.v` | P0–P12 (13 halaman) | navigasi UI, bukan lapisan |
| Ka'bah | `cosmictera/RULES.md` R10 | Lapis 0–4 | lapisan kriptografi |

Tidak ada model "11-lapis kanonik" di sumber terlacak; label itu dikarang oleh paket sebelumnya dan **harus dihapus** (melanggar larangan membuat struktur baru). Penomoran keenam model tidak boleh saling dipetakan sebagai padanan nomor-ke-nomor.

---

## 6. Anggaran Unified SoC — bukti batas praktis

| Desain | LUT4 | Hasil | Sumber |
|---|---:|---|---|
| `hcpu_gowin_top` Paket 8 | 15.453 | ter-place, dijalankan | `cosmictera/SYSTEM.md` §8 |
| `hcpu_hdmi_top` (13 Sep, pra-Paket 8) | 15.994 | ter-place | header `hcpu_hdmi_top.v:11-16` |
| `hcpu_gowin_top` + `CDOT` | 16.015 | **"Unable to find legal placement"** ×2 | `cosmictera-build/OFF.md:324` |
| dashboard ROM + compositor | 16.849 | **ditolak** | `cosmictera-build/PAPAN.md:563` |
| dashboard RAM + painter | 16.882 | **ditolak** | `cosmictera_display_top.v:7` |
| Usulan Unified SoC (penjumlahan kasar) | 17.979 | belum diukur | — |

Angka `18.370 LUT4 / 35 BSRAM` untuk `hcpu_hdmi_top` di paket sebelumnya **tidak ditemukan di sumber mana pun**; header berkas mencatat 15.994 / 18 BSRAM (dan, per R4, angka itu sendiri kedaluwarsa sejak Paket 8).

Kesimpulan: dengan bukti yang ada, Unified SoC **tidak dapat diklaim layak** sampai (a) Boot UI dipangkas jauh (mis. buang logo RLE besar, teks ROM lebih kecil, mini-emblem tanpa pengali), atau (b) HCPU dikonfigurasi tanpa sebagian co-engine, lalu **satu build gabungan nyata** dijalankan. Penjumlahan modul bukan pengukuran (R4/R5).

---

## 7. Koreksi wajib pada paket 14 dokumen sebelumnya

| # | Kesalahan di paket sebelumnya | Yang benar | Berkas terdampak |
|---|---|---|---|
| K-01 | R2 didefinisikan "Verified Fact / Demonstrated Prototype / Code Complete / Experimental Hardware / Architectural Target" (dan di audit: "Verified in Hardware / Designed & Planned …") | **VF** Verified Formally · **CC** Computationally Confirmed · **DP** Design Property · **EH** Engineering Hypothesis · **AT** Aspirational Target (`RULES.md` R2). Seluruh label komponen harus ditetapkan ulang menurut arti ini. | semua 14 dokumen, `COSMICTERA_CT01_REV13_AUDIT.md` |
| K-02 | "103 opcode", 8 keluarga dengan huruf di 0x00–0x1B, `HALT=0xFF`, `JMP=0x60`, `LOAD=0x70` dsb. | 104/83/82/21 (§2); huruf **0xE0–0xFB**, `HALT=0x01`, `HALT_ERR=0xFF`, `JMP=0x22`, `LOAD=0x30` (`hcpu_pkg.vh`) | HCPU_HISA, MASTER, INVENTORY, LAYER_RECONCILIATION |
| K-03 | Peta SD: `0xFE0` STATUS, `0xFE3` CMD | `0xFE0` SD_CMD, `0xFE1` SD_STATUS, `0xFE2` SD_SECTOR, `0xFE3` SD_DATA, `0xFE4` SD_CONTROL, `0xFE5` SD_CSUM, `0xFE6` SD_PRESCAN | HCPU_HISA, INTERFACE_MATRIX, DATA_FLOW |
| K-04 | IMEM loader di `0xFFE/0xFFF`, MEM_BASE/LIMIT di `0xFF3/0xFF7` | **`0xFF3` IMEM_ADDR, `0xFF7` IMEM_DATA, `0xFFE` MEM_BASE, `0xFFF` MEM_LIMIT** | HCPU_HISA, DATA_FLOW (Flow 4), INTERFACE_MATRIX IF-02 |
| K-05 | Trap cause 1–6 | **0** timer, **1** UART RX, **2** illegal, **3** priv, **4** mem, **5** syscall | HCPU_HISA |
| K-06 | FLAGS Z=0 … G=3 | G=0, Z=1, O=2, LT=3 | HCPU_HISA |
| K-07 | H-Reg 8×144, banking privilese; RA stack 8 | 16×144, tanpa banking; RA 32 | AUDIT, HCPU_HISA |
| K-08 | ROM 28×72-bit / `rom_addr[4:0]` | 34×144-bit, 6-bit | AUDIT, INTERFACE_MATRIX |
| K-09 | GAP-03 terbuka | tertutup di kode (`ef209af4`); hanya catatan `NUI/LAYERS.md` yang basi | GAPS_AND_CONFLICTS |
| K-10 | "11-lapis kanonik" | tidak ada; lihat §5 | LAYER_RECONCILIATION, MASTER |
| K-11 | `hcpu_hdmi_top` 18.370 LUT4 / 35 BSRAM | header: 15.994 / 18 (kedaluwarsa per R4) | HARDWARE |
| K-12 | Unified SoC 17.979 "langkah berikutnya" | di atas tiga titik gagal terukur (§6) | GAPS_AND_CONFLICTS, HARDWARE |

---

## 8. Daftar gap setelah rekonsiliasi

| ID | Status | Jenis | Tindakan | Butuh pemilik? |
|---|---|---|---|---|
| GAP-01 | terbuka (dicatat sebagai fakta L0) | docstring `exomatrix.py` | biarkan sampai definisi dibuktikan | ya |
| GAP-02 | **terbuka** | RTL, R1 | §4 | **ya** (RTL) |
| GAP-03 | **tertutup di kode** | catatan basi | perbarui `NUI/LAYERS.md:173-178` | ya (berkas terlacak) |
| GAP-06 | **baru** | encoding + gerbang tes | §2 (a)–(d) | **ya** (spesifikasi beku) |
| GAP-07 | **baru** | spesifikasi tertinggal | `HISA_SPEC §3.2` (4×576-bit, ROM 252 B) vs RTL 16×144 | ya |
| GAP-08 | terbuka | paritas Lapis 4 | 4 kelas, 30 mismatch (HALT/RET shadow, REG_COUNTER, SD_STATUS, HCHECK) — angka per kelas wajib dihitung ulang dari `NUI/layer4_freeze.json`, bukan dikutip | sebagian |
| GAP-09 | **baru** | paket dokumen | koreksi K-01…K-12 | tidak (berkas tak terlacak) |

---

## 9. Urutan kerja berikutnya (usulan)

1. **Koreksi paket dokumen** (K-01…K-12) — tidak menyentuh berkas terlacak.
2. **Keputusan pemilik GAP-06** (slot 0x4E) — lalu perbaiki literal, registry, regex gerbang, dengan sabotase.
3. **Keputusan pemilik GAP-02** — `hcpu_hisab` membaca `hcpu_guard`, ukur ulang LUT4.
4. **GAP-08** — hitung ulang empat kelas dari `layer4_freeze.json`, putuskan mana yang diperbaiki di RTL (bayangan HALT) dan mana yang dinyatakan "perbedaan semantik yang diketahui" (REG_COUNTER).
5. **Persistensi HFS** di kartu: write → readback → cabut daya → readback.
6. **Baru kemudian** eksperimen Unified SoC dengan target LUT4 di bawah ~15.900 dan satu build gabungan nyata.

