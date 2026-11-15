# Technical Architecture Specification — hijaiyyahmathematic.tech

## 1. Posisi & Arsitektur Tiga Subsistem Sejajar
**hijaiyyahmathematic.tech** adalah portal ilmiah resmi Matematika Hijaiyyah yang menggabungkan tiga subsistem sejajar di atas satu sumber data kanonik tunggal (*Single Source of Truth*):

1. **Public Scientific Portal (`hijaiyyahmathematic.tech`)**: Pusat pengetahuan matematika, provenans glyph, publikasi ilmiah (jurnal & monograf buku), serta dokumentasi teknis.
2. **Interactive Explorer & Web Laboratory**: Lingkungan eksplorasi ke-28 huruf kanonik (`/explorer/letter/[slug]`), visualisasi Codex 18D, dan kalkulator interaktif lima operasi metrik BAB II (`/laboratory/[op]`) + `CSGI`.
3. **HOM Suite (`Hijaiyyah Operating Machine`)**: Lingkungan komputasi interaktif yang mencakup `HC IDE` dan `HVM Web Simulator` (`/simulator`), terhubung dengan spesifikasi perangkat keras `HCPU`.

Ketiga subsistem di atas bersifat **independen secara layanan** dan membaca secara *read-only* satu sumber data resmi:
- **Master Table**: `HM-28-v1.0-HC18D` (`28 × 18 = 504` nilai, `148` sel bukan nol, rank(M14) = 14)
- **Dataset Hash**: `SHA-256: f82d385917ff…` (diekspor dari `src/hijaiyyah/core/master_table.py`)

## 2. Ketetapan Istilah & Urutan Kanonik
1. **Hybit**: *Hijaiyyah Hyperdimensional Bit Integration Technology*
2. **HMCL**: *Hijaiyyah Mathematical Computing Laboratory* (*Laboratorium Komputasi Matematis Hijaiyyah*)
3. **Lima Operasi Metrik-Vektorial BAB II (Σ-MV)**:
   - `VTM` — **Vektronometry** (`/[locale]/laboratory/vektronometry`)
   - `NMV` — **Normvektor** (`/[locale]/laboratory/normvektor`)
   - `AGM` — **Aggregametric** (`/[locale]/laboratory/aggregametric`)
   - `ITM` — **Intrametric** (`/[locale]/laboratory/intrametric`)
   - `EXM` — **Exometric** (`/[locale]/laboratory/exometric`)
4. **Urutan 28 Huruf Kanonik (`01–28`)**: Tiga indeks terakhir dikunci pada **26 = و (`Waw`), 27 = هـ (`Haa`), 28 = ي (`Ya`)**.
5. **Lima Label Epistemik Kanonik**:
   - `VF` = *Verified Formally*
   - `CC` = *Computationally Confirmed*
   - `DP` = *Design Property*
   - `EH` = *Engineering Hypothesis*
   - `AT` = *Aspirational Target*
   Status simulasi `HVM` di web (`CC`) selalu dibedakan secara eksplisit dari bukti eksekusi silikon pada FPGA Tang Nano 20K (`PAPAN`).

## 3. Pipeline Pengembangan Program pada Menu Computing
1. `01` **.hcell / HC** — Source program berbasis tipe primitif hybit 18D
2. `02` **CellIR & Ψ-Injector** — Representasi menengah & penyisipan otomatis 6 guard
3. `03` **4-B′ Verifier** — Verifikasi alur kontrol statis sebelum eksekusi
4. `04` **HPG1 v2 · CHECKSUM32** — Container biner berheader 7 kata dengan checksum 32-bit
5. `05` **H-ISA · 105 Opcode** — 84 opcode RTL, 21 opcode software-only (termasuk 28 opcode huruf `0xE0–0xFB`)
6. `06` **HVM / HCPU** — Mesin virtual (`CC`) dan prosesor 5-tahap di FPGA (`PAPAN`)
