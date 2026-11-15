"""CosmicTera NUI Autonomous Layers (L8–L11) Canonical Subpackage.

Placed under `src/hijaiyyah/nui/autonomous/` per Owner Decision (Option 2) so that:
1. The 43 top-level `.py` modules in `src/hijaiyyah/nui/` remain untouched and locked by `test_nui_layers.py`.
2. L0–L7 frozen artifacts and contracts remain completely unmodified.
3. L8 (Autonomous Diagnostics), L9 (Deductive Reasoning), L10 (Autonomous Engineering),
   and L11 (Universal Computation) operate as first-class canonical NUI layers connected to
   NUI Desktop via `nui-desktop/backend/canonical_layers_adapter.py`.
"""
from __future__ import annotations

from .layer8_diagnostics import (
    ANOMALY_CLASSES,
    REPAIR_BOUNDARIES,
    DiagnosisRecord,
    diagnose,
    diagnose_burnin_log,
    diagnose_traceback,
    scan_all_anomalies,
    summary as layer8_summary,
    verify_diagnosis,
)
from .layer9_reasoning import (
    CONCLUSION_VERDICTS,
    INFERENCE_RULES,
    REASONING_STAGES,
    ReasoningRecord,
    canonical_reasoning_suite,
    reason,
    reason_about_exomatrix_tail_claim,
    reason_about_file_impact,
    reason_about_letter_unification,
    reason_about_opcode,
    reason_about_program,
    reason_about_unknown_boundary,
    summary as layer9_summary,
    verify_reasoning,
)
from .layer10_engineering import (
    ENGINEERING_STAGES,
    REQUIRED_ORACLES,
    EngineeringRecord,
    check_immutable_target,
    engineer_hasm_program,
    engineer_python_sandbox_patch,
    summary as layer10_summary,
    verify_engineering,
)
from .layer11_universal import (
    JUNCTION_IDS,
    OFFICIAL_BSM_HCELL,
    JunctionOracleResult,
    UniversalComputationRecord,
    execute_universal_chain,
    summary as layer11_summary,
    verify_universal_chain,
)

__all__ = [
    "ANOMALY_CLASSES",
    "CONCLUSION_VERDICTS",
    "DiagnosisRecord",
    "ENGINEERING_STAGES",
    "EngineeringRecord",
    "INFERENCE_RULES",
    "JUNCTION_IDS",
    "JunctionOracleResult",
    "OFFICIAL_BSM_HCELL",
    "REASONING_STAGES",
    "REPAIR_BOUNDARIES",
    "REQUIRED_ORACLES",
    "ReasoningRecord",
    "UniversalComputationRecord",
    "canonical_reasoning_suite",
    "check_immutable_target",
    "diagnose",
    "diagnose_burnin_log",
    "diagnose_traceback",
    "engineer_hasm_program",
    "engineer_python_sandbox_patch",
    "execute_universal_chain",
    "layer8_summary",
    "layer9_summary",
    "layer10_summary",
    "layer11_summary",
    "reason",
    "reason_about_exomatrix_tail_claim",
    "reason_about_file_impact",
    "reason_about_letter_unification",
    "reason_about_opcode",
    "reason_about_program",
    "reason_about_unknown_boundary",
    "scan_all_anomalies",
    "verify_diagnosis",
    "verify_engineering",
    "verify_reasoning",
    "verify_universal_chain",
]
