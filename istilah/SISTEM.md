# Sistem: HOS, HFS, dan apa yang mereka sebut

Kosakata sistem operasi mesin ini. `HOS` dan `HFS` sendiri ada di
[`teknologi/ISTILAH.md`](../teknologi/ISTILAH.md); yang di sini adalah nama-nama
**di dalam** keduanya.

---

## Kernel dan proses

| istilah | arti | di mana |
|---|---|---|
| **H-Kernel** | — **kepanjangan tidak tertulis di mana pun**; empat tanggung jawab: proses, memori, I/O, daemon guard | `rtl/programs/kernel.hasm` |
| **HAL** | lapisan abstraksi perangkat keras; satu-satunya yang menyebut alamat periferal | `rtl/programs/hal.hasm` |
| **PCB** | *process control block*, 32 kata: R0–R15, pc, mem_base, mem_limit, runnable, flags | `rtl/programs/shell.hasm` |
| **daemon guard** | proses yang menyapu codex secara berkala | `rtl/programs/kernel.hasm` |
| **quantum** | jatah waktu sebuah proses sebelum timer mempreempsinya | `rtl/programs/kernel.hasm` |

**FLAGS bagian konteks proses, dan itu tidak selalu benar.** Sampai H-ISA v1.1
tak ada cara menyentuhnya; `FRD` (0x0A) dan `FWR` (0x0B) yang membukanya, dan
`a3e2a15` adalah preseden yang dipakai lagi untuk H0.

---

## Syscall

| istilah | arti | di mana |
|---|---|---|
| **tabel izin syscall** | satu kata per panggilan; menolkan satu menonaktifkan satu | `shell.hasm` `0xECD+n` |
| **lengan** | cabang `serve` untuk satu nomor panggilan | `rtl/programs/kernel.hasm` |
| **ABI HFS v1** | `R2` = selektor objek, `H0` = muatan hybit, `R1` = 1/0 | `tests/test_integrity/test_hfs_abi.py` |
| **slot H0** | 18 kata per proses, tempat H0 pemanggil diselamatkan | `rtl/programs/hos_hctx.hasm` |

**Tidak ada tabel lompat.** `JMP` dan `CALL` keduanya `PC ← IMM`; tidak ada
`JALR`. Jadi `serve` adalah rantai perbandingan, dan tabel syscall hidup di
**memori data** — `0d63a7e` mencatat bahwa bentuk itu dipilih karena ISA ini
tidak punya lompatan terhitung, bukan karena selera.

---

## HFS

| istilah | arti | di mana |
|---|---|---|
| **guard-on-write** | tiap tulis divalidasi guard sebelum disimpan | `rtl/programs/hos.hasm` |
| **tabel berkas** | 8 berkas × 3 kata: ada, ukuran, penunjuk | `hos.hasm` `0xE80` |
| **HFS1** | magic sektor: `0x48465331`, plus VERSION | `rtl/programs/hos_hfs_disk.hasm` |
| **berkas** | **satu vektor hybit 18 komponen** — bukan aliran byte | `hos.hasm` |

> **Sebuah berkas di HFS bukan aliran byte bernama.** Identitasnya bilangan
> 0–7, isinya satu vektor 18 komponen, dan tidak ada nama berkas di mana pun.
> Itu bukan kekurangan yang belum ditambal — itu model datanya, dan mengubahnya
> adalah mengubah apa itu berkas di mesin ini.

**`create` operasi bernama, bukan efek samping tulis pertama.** `b2a0595`
memberi alasannya: berkas yang **ada** tapi kosong bukan berkas yang tak pernah
dibuat, dan tanpa `create` tidak ada cara bertanya.

---

## Kartu

| istilah | arti | di mana |
|---|---|---|
| **N_CC** | ≥8 clock menganggur antar perintah SD | `rtl/hcpu_sdio.v` — `NCC_CLOCKS` |
| **bayangan HALT** | instruksi tepat sesudah `HALT` tetap pensiun | `AGENTS.md`, `sdio_write.hasm` |

**N_CC adalah butir kedua di repo ini yang penghalangnya hanya bisa ditemukan
papan.** Dua belas pemeriksaan hijau, dan kartu SDHC sehat diam seratus
milidetik.

---

## Bukti dan label

| istilah | arti | di mana |
|---|---|---|
| **empat gerbang** | lint/typecheck · pytest · `rtl/tb all` · bitstream — satu lari | `AGENTS.md` |
| **tingkat bukti** | terakit → tersimulasi → tersintesis → **berjalan** | `AGENTS.md` |
| **VF · DP · CC · EH · AT** | label epistemik; tidak naik tanpa bukti baru (R2) | `cosmictera/RULES.md` |
| **K1–K15** | aturan kuli AI: apa yang **tidak** boleh dilakukan | `AGENTS.md` |
| **R1–R13** | aturan yang mengikat, tiap satu lahir dari insiden nyata | `cosmictera/RULES.md` |

**Perangkat keras berhenti di tingkat 4.** Testbench hijau bukan selesai;
`cosmictera-build/PAPAN.md` yang memegang tingkat tertinggi, karena ia mencatat
apa yang benar-benar keluar dari papan.

---

Dijangkarkan oleh `tests/test_integrity/test_hfs_abi.py`,
`test_build_list.py`, dan `test_istilah.py`.
