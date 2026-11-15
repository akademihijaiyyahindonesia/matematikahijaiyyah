# NUI Lapis 10 — Rekayasa Otonom (`src/hijaiyyah/nui/autonomous/layer10_engineering.py`)

- **Status**: `IMPLEMENTED_AND_VERIFIED`
- **Modul Kanonik**: `src/hijaiyyah/nui/autonomous/layer10_engineering.py`
- **Pengujian**: `tests/test_ai/test_nui_layer10_engineering.py`
- **Hubungan ke `NUI/LAYERS.md`**: Mengimplementasikan **Lapis 10 — Rekayasa** dengan disiplin urutan pemilik (`cari aset -> ukur -> verifikasi -> identifikasi celah -> baru bangun`, K3–K6) tanpa menyentuh jumlah 43 modul tingkat atas di `src/hijaiyyah/nui/`.

## 1. Urutan Wajib 8-Tahap (K3–K6)

Setiap proses rekayasa di Lapis 10 wajib tercatat melewati 8 tahap berurutan:

1. `1_SEARCH` — Mencari aset yang sudah ada di repositori (`program_index.py`, `repository_index.py`).
2. `2_MEASURE` — Mengukur metrik dasar dan *ground-truth* matematis (`MASTER_TABLE`, `compute_bsm`, `guard_check`).
3. `3_VERIFY` — Memverifikasi diagnosis L8 dan pembuktian deduktif L9 atas target.
4. `4_IDENTIFY_GAP` — Mengidentifikasi celah spesifik sebelum menulis satu baris kode pun.
5. `5_DESIGN` — Merancang solusi deterministik (mis. program `.hcell` / H-ISA dengan daur ulang register `R1..R15` atau patch Python tervalidasi AST).
6. `6_BUILD` — Membangun artefak di ruang kerja yang diizinkan (menolak keras modifikasi pada `src/hijaiyyah/core/`, `hisa/`, `rtl/`, artefak *freeze* L4–L7, dan 4 berkas HDMI).
7. `7_TEST` — Menguji artefak terhadap 4 gerbang oracle kanonik:
   - `ASSEMBLER_ORACLE` (`hijaiyyah.hisa.assembler.assemble` & pemeriksaan batas GPR `<= R15`)
   - `INTERPRETER_TRACE_ORACLE` (`HISAMachine` + `execution_trace.run`)
   - `FOUR_GUARDS_ORACLE` (`hijaiyyah.core.guards.guard_check` G1–G4 & `4-B'` container check)
   - `LAYER7_DECISION_ORACLE` (`layer7.evaluate` + `layer7_decision.decide` + `check_immutable_target`)
8. `8_VALIDATE` — Menyegel `EngineeringRecord` dengan `record_sha256` yang dapat diverifikasi ulang oleh `verify_engineering()`.

## 2. Cara Verifikasi

```bash
/usr/local/bin/python3 -m hijaiyyah.nui.autonomous.layer10_engineering --verify
/usr/local/bin/python3 -B -m pytest -o addopts= -v tests/test_ai/test_nui_layer10_engineering.py
```
