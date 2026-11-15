# NUI Lapis 8 — Diagnostik Otonom (`src/hijaiyyah/nui/autonomous/layer8_diagnostics.py`)

- **Status**: `IMPLEMENTED_AND_VERIFIED`
- **Modul Kanonik**: `src/hijaiyyah/nui/autonomous/layer8_diagnostics.py`
- **Antarmuka Publik**: `src/hijaiyyah/nui/autonomous/__init__.py`
- **Adapter Desktop**: `nui-desktop/backend/canonical_layers_adapter.py` (`CanonicalL8Adapter`)
- **Pengujian**: `tests/test_ai/test_nui_layer8_diagnostics.py`
- **Hubungan ke `NUI/LAYERS.md`**: Mengimplementasikan spesifikasi **Lapis 8 — Diagnostik otonom** tanpa mengubah jumlah 43 modul tingkat atas di `src/hijaiyyah/nui/`.

## 1. Rantai Pipeline 4-Tahap

Setiap diagnosis pada Lapis 8 wajib melewati empat tahap deterministik:

1. `1_ANOMALY_DETECTION` — Mendeteksi anomali dari model paritas L4 (`NUI/parity_model.json`, `NUI/layer4_freeze.json`), registri OFF (`cosmictera-build/OFF.md` melalui `off_db.py`), rekaman burn-in (`cosmictera-build/burn-in/*.jsonl` melalui `burn_in_report.py`), fungsi transisi RTL L6 (`NUI/spec/rtl_function.json`), klaim sudut/matematika L0 (`claims.py`, `facts.py`), dan *traceback* runtime Python.
2. `2_EVIDENCE_COLLECTION` — Mengumpulkan rantai bukti (`evidence_chain`) yang menyertakan path berkas/baris sumber, hash SHA-256 aktual dari berkas bukti di repositori, dan rincian terukur.
3. `3_ROOT_CAUSE_ISOLATION` — Mengisolasi akar masalah dan memisahkan pemilik anomali secara tegas:
   - `SILICON_SYNTHESIS` (`OFF-PRINT-SILICON` pada Tang Nano 20K untuk nilai `PRINT >= 2^23`)
   - `RTL_PIPELINE` (eksekusi 1 instruksi di belakang `HALT` atau `RET` fault HC-05 pada 10 program HASM + 3 *stop-probe*)
   - `KNOWN_SEMANTIC_DIFFERENCE` (`COUNTER` instruksi vs siklus clock, `SD_STATUS` tanpa kartu, `HCHECK` berkala)
   - `HOST_OBSERVER_MACOS` vs `PHYSICAL_BOARD` (jeda keheningan serial burn-in di mana `work_accounted = 1.0002` membuktikan papan tidak pernah berhenti sementara Mac mengalami *sleep/hibernation*)
   - `SOFTWARE_VS_RTL_MODEL` (`HISAB` 13 tepi selisih serialisasi `KNOWN_DISCREPANCY`)
   - `COMPILER_TOOLCHAIN` (batas alokasi register `codegen.py` R16/R17 vs `assembler.py` R0..R15)
   - `DOCUMENTATION_VS_SEALED_MATH` (5 klaim sudut dokumen yang difalsifikasi & `nui.tail_one_is_not_invertibility`)
4. `4_REPRODUCIBLE_DIAGNOSIS` — Menghasilkan objek `DiagnosisRecord` dengan `reproduction_command`, `repair_boundary` (`ALLOWED_IN_SANDBOX`, `REQUIRES_OWNER_DECISION`, `FROZEN_HARDWARE_EVIDENCE`, `OBSERVATION_ONLY_NO_REPAIR`), dan `record_sha256` yang dapat diverifikasi ulang oleh `verify_diagnosis()`.

## 2. Cara Verifikasi

```bash
/usr/local/bin/python3 -m hijaiyyah.nui.autonomous.layer8_diagnostics --verify
/usr/local/bin/python3 -B -m pytest -o addopts= -v tests/test_ai/test_nui_layer8_diagnostics.py
```
