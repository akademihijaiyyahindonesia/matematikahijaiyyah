# Yang menyala

Enam lapis. Setiap baris menyebut **perintahnya**, **tempatnya**, dan **apa yang
gagal kalau ia rusak** — karena daftar tanpa itu hanya klaim.

---

## 1 — Matematika: dasarnya

| menyala | apa persisnya | bukti |
|---|---|---|
| Master Table | 28 huruf, nilai kanonik dari PDF bersegel | `src/hijaiyyah/core/master_table.py` |
| Aljabar monoid | closure dibuktikan, bukan disampel | `tests/test_algebra/` — 15 tes |
| Guard G1–G4 + T1–T2 | deteksi korupsi vektor, **93,1%** langit-langit | `rtl/hcpu_guard.v`, 34 asersi |
| Teorema | suite penuh | `tests/test_theorems/` |

**93,1% bukan kegagalan menuju 100%.** N/K/Q dan agregatnya tertutup penuh; Θ̂
hanya 11% karena ρ aditif — batas atas berhingga apa pun akan merusak closure —
dan H\* nol karena ia indikator non-geometrik (ID.1.3 di buku). Rinciannya di
[`matematika-hijaiyyah/GUARD.md`](../matematika-hijaiyyah/GUARD.md).

Label: `VF` untuk closure, `CC` untuk cakupan guard.

---

## 2 — Bahasa dan perkakas

| menyala | apa persisnya | bukti |
|---|---|---|
| HVM | mesin virtual, lima komponen | `src/hijaiyyah/vm/`, 45 tes |
| HASM | perakit `.hasm` → kata mesin | `src/hijaiyyah/hisa/assembler.py`, 16 tes |
| HC / HCC | bahasa dan kompilator (**parsial**) | `src/hijaiyyah/compiler/`, 59 tes |
| HAR | registri alfabet (**parsial**) | `src/hijaiyyah/har/`, 15 tes |
| LSP + REPL | `python3 -m hijaiyyah repl` | `src/hijaiyyah/lsp.py`, `cli.py` |
| Bahasa | 102 tes | `tests/test_language/` |

HCC dan HAR ditulis **parsial** di sini dengan sengaja: keduanya berjalan dan
diuji, tapi belum menutup spesifikasinya sendiri. Lihat
`docs/hybit_pipeline_spec.md`.

Label: `CC`.

---

## 3 — Mesin: H-ISA dan HCPU

| menyala | apa persisnya | bukti |
|---|---|---|
| Pipeline HCPU | fetch → decode → execute → mem → writeback | `rtl/hcpu_top.v` |
| Opcode | **72 dari 96** terimplementasi di RTL | `RTL_IMPLEMENTED` di `src/hijaiyyah/hisa/opcodes.py` |
| Opcode huruf | **28** (`0xE0`–`0xFB`), dijalankan di pipeline | `rtl/tb/tb_hcpu_letters.v`, `rtl/programs/letters.hasm` |
| Codex ALU | HCADD, HNRM2, HDIST | `rtl/hcpu_codex_alu.v`, 6 asersi |
| Hisab | penyapuan 28 huruf, 124 asersi | `rtl/hcpu_hisab.v` |
| Interlock | load-use, store-load, **termasuk POP** | `rtl/hcpu_decode.v` |
| Stack perangkat keras | 256 entri, LIFO, PUSH tanpa register basis | `rtl/hcpu_memory.v` |
| **Subrutin** | `CALL`/`RET`, stack kembali 32 tingkat terpisah | `rtl/tb/tb_hcpu_subroutine.v`, `rtl/programs/subroutine.hasm` |
| UART TX + RX | 115200 baud dari 27 MHz | `rtl/hcpu_uart_*.v` |
| Timer | pencacah bebas + satu compare | `rtl/hcpu_timer.v` |

**Satu huruf adalah satu instruksi utuh.** Itu inti resepnya: `0xE0`–`0xFB`
mengindeks ROM codex langsung di tahap Execute, jadi perintah tidak perlu
ditulis sebagai deretan angka.

Sampai `f57793e` klaim itu **salah di perangkat keras**, dan tidak ada yang
mengatakannya: tak satu pun bench atau program pernah menjalankan salah satu
dari dua puluh delapan. `RTL_IMPLEMENTED` mendaftarkannya, tapi himpunan itu
sebuah **deklarasi, bukan pengukuran**. Penyebabnya `default:` kedua di tengah
`case` codex — iverilog memilih yang akhir, jadi setiap huruf menulis nol,
sementara penafsir Python tetap menghitung benar. `tb_hcpu_letters` sekarang
mengadu keduanya: 112 untuk Ba+Sin+Mim lewat jalur huruf, angka yang sama yang
sudah dibuktikan jalur HLOAD/HCADD.

Label: `CC`.

---

## 4 — Sistem operasi: enam prasyarat, lalu kernelnya

| menyala | apa persisnya | bukti |
|---|---|---|
| 1 Bitwise | `0xB0`–`0xBA` | `rtl/hcpu_execute.v` |
| 2 UART RX + timer | dua sumber level-sensitif | `rtl/tb/tb_hcpu_uart_rx.v`, `tb_hcpu_timer.v` |
| 3 Trap | **6 penyebab**, prioritas indeks terendah | `rtl/hcpu_trap.v`, `tb_hcpu_trap.v` |
| 4 Mode supervisor | jendela periferal tertutup bagi user | `rtl/hcpu_execute.v` |
| 5 Proteksi memori | jendela `[base, limit)` per proses | `rtl/hcpu_mmio.v` |
| 6 Syscall | `0x09`, non-maskable, epc menunjuk dirinya | `rtl/programs/syscall.hasm` |
| **H-Kernel** | **dua proses, dipreempt, register masing-masing** | `rtl/programs/kernel.hasm` |

H-Kernel berjalan di **dua tempat**: penafsir Python dan pipeline RTL.

```
make -C rtl/tb sim_kernel
  ticks 2550   A (dipreempt) 1012   B (menyerah) 127400 = 1274 × 100
```

Angka B itu buktinya. Kedua proses menghitung di **R1** — A menambah 1, B
menambah 100 — jadi total B tetap kelipatan bersih 100 **hanya jika** R1-nya
tak pernah sekali pun memegang nilai A. Itu definisi register privat, diukur.

A dipreempt timer dan B menyerah lewat `SYSCALL`, jadi kedua jalur masuk trap
teruji sekaligus: tanpa `epc` dimajukan untuk cause 5, B akan mengulang
`SYSCALL`-nya sendiri selamanya.

Ruang lingkupnya jujur, dan buku menetapkan ukurannya. H-Kernel di sana punya
**empat** tanggung jawab — proses, memori, I/O, daemon guard. Yang berjalan
**dua**, dan keduanya sebagian:

| tanggung jawab | keadaan |
|---|---|
| proses | dua slot tetap, round-robin — tanpa pembuatan dinamis |
| memori | jendela `[base, limit)` per proses — tanpa heap |
| I/O | **belum** — proses user tidak bisa melakukan I/O sama sekali |
| daemon guard | **belum** — tak ada yang menjadwalkan HCHECK |

Karena itu spec pipeline menyebutnya `PARTIAL (2 of 4)`, bukan `OPERATIONAL`.
Rinciannya di [OFF.md](OFF.md).

Label: `CC`.

---

## 5 — Kripto Ka'bah

| menyala | apa persisnya | bukti |
|---|---|---|
| Spons | 25×64 = 1600 bit, rate 128 B, kapasitas 576 | `rtl/hijaiyyah_sponge.v` |
| Permutasi | 28 ronde = 7 CIRCUIT × 4 TAWAF | `rtl/hijaiyyah_rotate_core.v` |
| S-box + router | 28 huruf | `rtl/hijaiyyah_sbox*.v` |
| Gerbang Jamrah | mode gerbang | `rtl/hijaiyyah_jamrah_gate.v` |
| Lapis 3 (HMAC-SHA256) | **satu-satunya pemikul keamanan** | `src/hijaiyyah/crypto/kabah.py` |

**Hanya lapis 3 yang memikul keamanan**, dan ia **tidak ada di RTL**. Empat
lapis lain adalah struktur, bukan jaminan. Menyebut sistem ini "aman" karena
ada lima lapis adalah salah membaca susunannya.

Throughput terukur, dan hambatannya bukan yang diduga:

```
deserialiser   8,00 clock/byte   ← hambatan
sponge (25)    2,42 clock/byte
sistem        10,42 clock/byte = 2,59 MB/s pada 27 MHz
```

Biayanya **dijumlah, bukan disembunyikan**: permutasi menghentikan aliran, jadi
deserialiser bit-serial 8 clock/byte menentukan hasilnya.

Label: `CC` untuk angka, `EH` untuk ketahanan kriptanalisis.

---

## 6 — Jembatan papan

| menyala | apa persisnya | bukti |
|---|---|---|
| Loader | program masuk lewat kabel, bukan resintesis | `rtl/programs/loader.hasm` |
| Format kawir | 4 byte cacah + 4N byte, MSB dulu | `rtl/scripts/send_program.py` |
| Bench boot | tiga kata mendarat di 64, 65, 66 lalu berjalan | `rtl/tb/tb_gowin_loader.v` |
| Wrapper papan | 27 MHz, UART pada pin papan | `rtl/fpga/gowin/hcpu_gowin_top.v` |

Ini menyala **dalam simulasi**. Bitstream-nya tidak — lihat [OFF.md](OFF.md).

Label: `CC` dalam simulasi, `EH` di silikon.

---

## Menjalankan semuanya

```bash
python3 -m pytest -q          # 4.279 lulus, 4 dilewati
make -C rtl/tb all            # 226 asersi, 14 bench, 0 gagal
make lint && make typecheck   # ruff, mypy
```
