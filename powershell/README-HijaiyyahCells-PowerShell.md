# HijaiyyahCells PowerShell Host Module

## Arsitektur Host (Keputusan Pemilik 4 & Aturan R1)

Modul `powershell/HijaiyyahCells.psm1` adalah **pembungkus tipis (*thin host wrapper*)** di atas mesin kompilator dan evaluator kanonik Python `hijaiyyah.cells` (`src/hijaiyyah/cells/`). Sesuai aturan **R1 (Satu kebenaran, satu tempat)**, PowerShell tidak mengimplementasikan salinan kedua dari tabel induk, rumus $U$/$\rho$, atau evaluator sel.

## Fungsi yang Diekspor

1. `Import-HijaiyyahMasterTable` — Mengimpor dan mengaudit dataset resmi `HM-28-v.1.0-HC18D` (28 huruf tersegel, vektor 18D, $B=U(h)$, $R=\rho(h)$, $H^*$, segel JSON `f82d3859...`, segel ROM `ac60add6...`, serta pencatatan celah artefak eksternal `.hb` `f85251e0...`).
2. `Get-HijaiyyahSymbol -Symbol <glif|nama|indeks>` — Mengambil entri huruf dari Master Table beserta opcode HISA native (`0xE0–0xFB`).
3. `Invoke-HijaiyyahCellProgram -Source <kode> [-HCCompat] [-SkipRtl]` — Menjalankan pipeline penuh (`.hcell` atau `.hc` $\rightarrow$ Cell IR $\rightarrow$ Semantic Analyzer $\rightarrow$ Reference Evaluator $\rightarrow$ HISA Backend $\rightarrow$ Kontainer `HPG1` $\rightarrow$ Verifikasi `4-B′` $\rightarrow$ `HISAMachine` & `HCPU` RTL).

## Cara Menjalankan Pengujian

```powershell
pwsh -NoProfile -File powershell/Test-HijaiyyahCells.ps1
```
