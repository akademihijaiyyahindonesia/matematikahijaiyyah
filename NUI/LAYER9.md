# NUI Lapis 9 — Mesin Penalaran Deduktif (`src/hijaiyyah/nui/autonomous/layer9_reasoning.py`)

- **Status**: `IMPLEMENTED_AND_VERIFIED`
- **Modul Kanonik**: `src/hijaiyyah/nui/autonomous/layer9_reasoning.py`
- **Pondasi Pengetahuan 7-Domain**: `src/hijaiyyah/nui/knowledge.py`, `src/hijaiyyah/nui/registry.py`, `src/hijaiyyah/nui/off_db.py`, `src/hijaiyyah/nui/usr.py`
- **Pengujian**: `tests/test_ai/test_nui_layer9_reasoning.py`
- **Hubungan ke `NUI/LAYERS.md`**: Mengimplementasikan **Lapis 9 — Mesin penalaran** di atas basis pengetahuan 7-domain (`HC`, `HISA`, `RTL`, `OFF`, `PAPAN`, `NUI`, `HOST`), graf repositori L1, graf program L2, dan jejak kausal eksekusi L3 tanpa mengubah jumlah 43 modul tingkat atas di `src/hijaiyyah/nui/`.

## 1. Rantai Deduktif 5-Tahap

Sesuai aturan pemilik (*"fakta → relasi → inferensi → kesimpulan, dan penalaran tidak boleh mendahului bukti"*), setiap objek `ReasoningRecord` wajib melewati:

1. `1_FACTS` — Mengumpulkan fakta terverifikasi dari ketujuh domain (`HC`, `HISA`, `RTL`, `OFF`, `PAPAN`, `NUI`, `HOST`) dengan menegakkan batas provenance P8.5 (`HOST` hanya membaca `observations/` dan tidak pernah membaca `facts/`).
2. `2_RELATIONS` — Menarik relasi eksplisit dari `repository_graph.py` (L1), `program_graph.py` (L2), `NUI/execution_model.json` (L3), dan `NUI/parity_model.json` (L4).
3. `3_PREMISES` — Menyusun premis formal (`P1`, `P2`, ...) yang masing-masing wajib menunjuk ke `supported_by_facts` dan `supported_by_relations`. Premis tanpa bukti ditolak oleh `verify_reasoning()`.
4. `4_INFERENCE` — Menerapkan aturan inferensi deterministik (`RULE_THREE_ENGINE_PARITY`, `RULE_SILICON_DIVERGENCE_ISOLATION`, `RULE_CONTROL_TRANSFER_CAUSALITY`, `RULE_REVERSE_DEPENDENCY_IMPACT`, `RULE_ADDRESS_UNIFICATION_BIJECTION`, `RULE_EXOMATRIX_COUNTEREXAMPLE_FALSIFICATION`, `RULE_FAIL_CLOSED_UNKNOWN_GUARD`, `RULE_SEMANTIC_LOWERING_EQUIVALENCE`).
5. `5_CONCLUSION` — Menghasilkan kesimpulan dengan `verdict` (`PROVEN`, `FALSIFIED`, `BOUNDED_BY_KNOWN_DISCREPANCY`, atau `INSUFFICIENT_EVIDENCE_UNKNOWN`), `epistemic_ceiling` (batas kepastian epistemik tertinggi yang diizinkan oleh premis, R2), dan `record_sha256`.

## 2. Cara Verifikasi

```bash
/usr/local/bin/python3 -m hijaiyyah.nui.autonomous.layer9_reasoning --verify
/usr/local/bin/python3 -B -m pytest -o addopts= -v tests/test_ai/test_nui_layer9_reasoning.py
```
