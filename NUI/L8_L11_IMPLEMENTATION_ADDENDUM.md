# Adendum Implementasi Kanonik Lapis 8 – Lapis 11 (`src/hijaiyyah/nui/autonomous/`)

- **Tanggal Keputusan**: 8 November 2026
- **Keputusan Arsitektur**: **Opsi 2 — Subpaket Otonom Resmi (`src/hijaiyyah/nui/autonomous/`)**
- **Status Kontrak `NUI/LAYERS.md`**: Dipertahankan tanpa perubahan (`43 modul` tingkat atas di `src/hijaiyyah/nui/` tetap terkunci oleh `tests/test_integrity/test_nui_layers.py`).
- **Status Artefak Freeze L4–L7**: Dipertahankan 100% *read-only* (`NUI/layer4_freeze.json`, `NUI/layer5_freeze.json`, `NUI/layer6_addendum.json`, `NUI/LAYER7.md`).

---

## 1. Struktur Modul Resmi L8–L11

Untuk menjaga kontrak integritas `test_the_counts_in_the_map_are_the_counts_in_the_tree` pada `tests/test_integrity/test_nui_layers.py` yang mengunci tepat **43 modul** Python tingkat atas di `src/hijaiyyah/nui/`, implementasi resmi Lapis 8 s.d. Lapis 11 ditempatkan pada subpaket kanonik `src/hijaiyyah/nui/autonomous/`:

| Lapis | Nama Resmi (`NUI/LAYERS.md`) | Modul Implementasi Kanonik | Dokumentasi Spesifikasi & Bukti | Suite Pengujian |
| :--- | :--- | :--- | :--- | :--- |
| **L8** | Diagnostik otonom | `src/hijaiyyah/nui/autonomous/layer8_diagnostics.py` | `NUI/LAYER8.md` | `tests/test_ai/test_nui_layer8_diagnostics.py` (6 tes) |
| **L9** | Mesin penalaran | `src/hijaiyyah/nui/autonomous/layer9_reasoning.py` | `NUI/LAYER9.md` | `tests/test_ai/test_nui_layer9_reasoning.py` (6 tes) |
| **L10** | Rekayasa | `src/hijaiyyah/nui/autonomous/layer10_engineering.py` | `NUI/LAYER10.md` | `tests/test_ai/test_nui_layer10_engineering.py` (4 tes) |
| **L11** | Komputasi universal | `src/hijaiyyah/nui/autonomous/layer11_universal.py` | `NUI/LAYER11.md` | `tests/test_ai/test_nui_layer11_universal.py` (3 tes) |
| **Public API** | Antarmuka Terkontrol L8–L11 | `src/hijaiyyah/nui/autonomous/__init__.py` | `NUI/L8_L11_IMPLEMENTATION_ADDENDUM.md` | `nui-desktop/tests/test_nui_l8_l11_desktop_integration.py` |

---

## 2. Integrasi ke NUI Desktop (`nui-desktop/backend/canonical_layers_adapter.py`)

Seluruh layer L0–L11 diakses secara terpadu oleh CosmicTera NUI Desktop melalui `CanonicalLayersBridge`:

- `CanonicalL8Adapter` (`bridge.l8`) — Memeriksa status L8, memindai seluruh anomali repositori tanpa diarahkan manusia (`scan_all_anomalies`), mendiagnosis gejala/program/log burn-in/traceback (`diagnose`), dan memverifikasi SHA-256 serta keberadaan berkas bukti (`verify_diagnosis`).
- `CanonicalL9Adapter` (`bridge.l9`) — Menjalankan rantai penalaran deduktif 5-tahap (`1_FACTS -> 2_RELATIONS -> 3_PREMISES -> 4_INFERENCE -> 5_CONCLUSION`) di atas basis pengetahuan 7-domain (`knowledge.py`), menegakkan batas provenance P8.5 (`HOST` hanya dari `observations/`), dan menolak premis tanpa bukti (`verify_reasoning`).
- `CanonicalL10Adapter` (`bridge.l10`) — Menjalankan urutan rekayasa otonom 8-tahap (`1_SEARCH -> 2_MEASURE -> 3_VERIFY -> 4_IDENTIFY_GAP -> 5_DESIGN -> 6_BUILD -> 7_TEST -> 8_VALIDATE`) dengan verifikasi terhadap 4 gerbang oracle (`ASSEMBLER_ORACLE`, `INTERPRETER_TRACE_ORACLE`, `FOUR_GUARDS_ORACLE`, `LAYER7_DECISION_ORACLE`) serta perlindungan *Immutable Core*.
- `CanonicalL11Adapter` (`bridge.l11`) — Menjalankan rantai komputasi universal dari L0 s.d. L11 dengan pemeriksaan oracle yang dijalankan pada seluruh **11 sambungan** (`J01_L0_TO_L1` s.d. `J11_L10_TO_L11`), memverifikasi paritas `.hcell` dan `.hc` (`[10, 6, 4, 112, 9]`), serta menjaga batas kejujuran epistemik (`NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION`).

---

## 3. Perintah Verifikasi Lengkap

```bash
/usr/local/bin/python3 -B -m pytest -o addopts= -v \
  tests/test_integrity/test_nui_layers.py \
  tests/test_ai/test_nui_layer8_diagnostics.py \
  tests/test_ai/test_nui_layer9_reasoning.py \
  tests/test_ai/test_nui_layer10_engineering.py \
  tests/test_ai/test_nui_layer11_universal.py \
  nui-desktop/tests/test_nui_master_intelligence.py \
  nui-desktop/tests/test_nui_l0_l7_desktop_integration.py \
  nui-desktop/tests/test_nui_l8_l11_desktop_integration.py
```
