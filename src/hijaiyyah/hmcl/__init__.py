"""Hijaiyyah Mathematical Computing Laboratory (HMCL) — CosmicTera Future Computing Charter.

Provides the unified multi-level simulation, formal asset verification, architectural
optimization, and 8-axis operational NUI benchmark suite mandated by the
COSMICTERA FUTURE COMPUTING CHARTER (Sections A–I).
"""

from __future__ import annotations

from hijaiyyah.hmcl.charter_assets import (
    EcosystemVerificationSummary,
    FormalMathematicalAsset,
    build_ecosystem_asset_registry,
    verify_all_ecosystem_assets,
)
from hijaiyyah.hmcl.multilevel_sim import (
    ArchitecturalAlternativeEvaluation,
    FormalPredictionRecord,
    LoopCalibrationPoint,
    MultiLevelSimulationReport,
    predict_alt_a1_rtl_cycles,
    predict_dynamic_loop_hvm_steps,
    predict_dynamic_loop_rtl_cycles,
    run_multilevel_hmcl_simulation,
    simulate_alt_a1_hardware_sticky_guard,
    simulate_alt_a2_hdot_20bit,
)
from hijaiyyah.hmcl.nui_benchmark import (
    HMCLScientificQuestionAnswer,
    NUIBenchmarkAxisResult,
    NUIBenchmarkSuiteReport,
    NUIFeatureSpaceComparison,
    compute_invariant_nui_feature_vector,
    evaluate_nui_feature_space_coherence,
    run_nui_8axis_benchmark,
)

HMCL_VERSION: str = "0.1.0-exp"

__all__ = [
    "HMCL_VERSION",
    "ArchitecturalAlternativeEvaluation",
    "EcosystemVerificationSummary",
    "FormalMathematicalAsset",
    "FormalPredictionRecord",
    "HMCLScientificQuestionAnswer",
    "LoopCalibrationPoint",
    "MultiLevelSimulationReport",
    "NUIBenchmarkAxisResult",
    "NUIBenchmarkSuiteReport",
    "NUIFeatureSpaceComparison",
    "build_ecosystem_asset_registry",
    "compute_invariant_nui_feature_vector",
    "evaluate_nui_feature_space_coherence",
    "predict_alt_a1_rtl_cycles",
    "predict_dynamic_loop_hvm_steps",
    "predict_dynamic_loop_rtl_cycles",
    "run_multilevel_hmcl_simulation",
    "run_nui_8axis_benchmark",
    "simulate_alt_a1_hardware_sticky_guard",
    "simulate_alt_a2_hdot_20bit",
    "verify_all_ecosystem_assets",
]
