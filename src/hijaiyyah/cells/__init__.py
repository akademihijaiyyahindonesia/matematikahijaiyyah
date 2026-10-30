"""Hijaiyyah Cells — Native Programming Language, Shared Cell IR, and Compiler for CosmicTera.

Provides the unified API and CLI entry point (`python3 -m hijaiyyah.cells`)
used by Python tests and the PowerShell thin host wrapper (`powershell/HijaiyyahCells.psm1`).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from hijaiyyah.cells.benchmarks import (
    BenchmarkTierMetrics,
    build_benchmark_sources,
    run_all_benchmark_tiers,
)
from hijaiyyah.cells.cost_model import (
    BOARD_CLOCK_HZ,
    PIPELINE_FILL_DRAIN_CYCLES,
    SIM_CLOCK_HZ,
    ProgramCostEstimate,
    build_cost_estimate,
    candidate_a_verification_instructions,
    candidate_b_verification_instructions,
    estimate_print_io_cycles,
)
from hijaiyyah.cells.dataset_engine import (
    CANONICAL_JSON_SEAL,
    CANONICAL_ROM_252B_SEAL,
    CANONICAL_ROM_504B_ROW_MAJOR_SEAL,
    CANONICAL_ROM_504B_RTL_WORD_BE_SEAL,
    CANONICAL_ROM_SEAL,
    DATASET_ID,
    DOCUMENTED_SOURCE_ERRATA,
    FORBIDDEN_LOOKALIKES,
    MASTER_TABLE_504B_BYTES,
    MASTER_TABLE_ENGINE,
    RECORDED_HB_MANIFEST_SEAL,
    SOURCE_DOCUMENT,
    MasterTableEngine,
    MasterTableLetterRecord,
    SealAuditReport,
    SourceErratumRecord,
    UnicodePolicyError,
    validate_and_normalize_hijaiyyah_text,
)
from hijaiyyah.cells.evaluator import (
    CellEvaluationError,
    CellEvaluationResult,
    CellEvaluator,
    CellTraceEvent,
)
from hijaiyyah.cells.hisa_backend import (
    GPR_FIRST,
    GPR_LAST,
    GPR_SCRATCH,
    HREG_FIRST,
    HREG_LAST,
    CellBackendError,
    CellHISABackend,
    CompiledHISAProgram,
    SourceInstructionMapEntry,
)
from hijaiyyah.cells.hpg1_bridge import (
    DEFAULT_OVERLAY_LOAD_ADDR,
    EndToEndPipelineResult,
    HCPUExecutionMeasurement,
    compile_and_execute_cells,
)
from hijaiyyah.cells.ir import (
    CellBasicBlock,
    CellIRGraph,
    CellIRNode,
    CellOp,
    CellSubroutineDef,
    CellValueType,
    SourceSpan,
)
from hijaiyyah.cells.lexer import (
    APPROVED_MATH_LATIN_OPERATORS,
    ARABIC_INDIC_DIGITS,
    HCellLexer,
    HCellLexerError,
    HCellToken,
    HCellTokenType,
    tokenize_hcell,
)
from hijaiyyah.cells.parser import (
    HCCompatBridge,
    HCellParseError,
    HCellParser,
    parse_hc_to_cell_ir,
    parse_hcell,
)
from hijaiyyah.cells.semantic import (
    CellSemanticError,
    SemanticAnalysisReport,
    SemanticAnalyzer,
)
from hijaiyyah.cells.spec import (
    HC_COMPAT_VERSION,
    HCELL_EBNF_GRAMMAR,
    HCELL_LANGUAGE_VERSION,
    HREG_COMPONENT_BITS,
    HREG_COMPONENT_MAX,
    HSTAR_MARKER_SEMANTICS,
    MAX_CANONICAL_LETTER_COMPONENT,
    NATIVE_LETTER_OPCODES,
    RTL_GUARD_WIDE_ADDERS,
    UNIVERSAL_SAFE_ACCUMULATION_LENGTH,
    AccumulationBoundAnalysis,
    EpistemicStatus,
    HStarMarkerSemantics,
    HStarSafetyAuditReport,
    IndividualGuardProof,
    NativeLetterOpcodeSpec,
    PathSafetyClass,
    PrefixBoundAnalysis,
    RTLWideAdderSpec,
    SixGuardClosureProof,
    analyze_h0_letter_accumulation,
    analyze_prefix_bounds,
    audit_hstar_safety_contract,
    build_native_letter_opcode_table,
    prove_six_guard_closure,
)
from hijaiyyah.cells.wave1_overlays import (
    WAVE1_OVERLAYS,
    Wave1OverlaySpec,
    run_wave1_overlays,
)
from hijaiyyah.cells.wave2_syscalls import (
    W2_HAR_INSPECTION_UTILITY,
    W2_HFS_LIFECYCLE_CLIENT,
    W2_OVERLAY_VERIFICATION_CLIENT,
    W2_SYSTEM_DIAGNOSTICS,
    Wave2SyscallProgramSpec,
    run_wave2_syscalls,
)


def main(argv: list[str] | None = None) -> int:
    """CLI bridge invoked by PowerShell `HijaiyyahCells.psm1` or command line."""
    parser = argparse.ArgumentParser(description="Hijaiyyah Cells Engine CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("audit-dataset", help="Output JSON audit of HM-28-v.1.0-HC18D")

    p_sym = sub.add_parser("lookup-symbol", help="Look up a letter by glyph, name, or index")
    p_sym.add_argument("query", help="Hijaiyyah glyph, Latin name, or 1..28 index")

    p_run = sub.add_parser("run", help="Compile, verify, and execute .hcell or .hc source")
    p_run.add_argument("--source", required=True, help="Source code string")
    p_run.add_argument("--hc-compat", action="store_true", help="Parse as .hc v1.0")
    p_run.add_argument("--no-rtl", action="store_true", help="Skip RTL simulation")

    p_bench = sub.add_parser("benchmarks", help="Run all 9 benchmark tiers")
    p_bench.add_argument("--no-rtl", action="store_true", help="Skip RTL simulation")

    args = parser.parse_args(argv)

    if args.cmd == "audit-dataset":
        snap = MASTER_TABLE_ENGINE.snapshot_dict()
        rep = MASTER_TABLE_ENGINE.audit()
        snap["audit_summary"] = {
            "json_seal_verified": rep.json_seal_verified,
            "rom_252b_seal_verified": rep.rom_seal_verified,
            "rom_504b_row_major_verified": rep.rom_504b_row_major_verified,
            "rom_504b_rtl_word_be_verified": rep.rom_504b_rtl_word_be_verified,
            "rtl_rom_v_consistent": rep.rtl_rom_v_consistent,
            "hb_artifact_present": rep.hb_artifact_present,
            "hb_artifact_status": rep.hb_artifact_status,
            "all_guards_pass": rep.all_guards_pass,
            "injectivity_pairs_verified": rep.injectivity_pairs_verified,
        }
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "lookup-symbol":
        q = str(args.query).strip()
        rec = None
        if q.isdigit():
            rec = MASTER_TABLE_ENGINE.get_by_index(int(q))
        if rec is None:
            rec = MASTER_TABLE_ENGINE.get_by_name(q)
        if rec is None:
            rec = MASTER_TABLE_ENGINE.get_by_char(q)
        if rec is None:
            print(json.dumps({"error": f"Symbol not found: {q}"}, ensure_ascii=False))
            return 1
        print(
            json.dumps(
                {
                    "index": rec.index,
                    "char": rec.char,
                    "name": rec.name,
                    "v14": list(rec.v14),
                    "anasir": list(rec.anasir),
                    "h_star": rec.h_star,
                    "v18": list(rec.v18),
                    "B_U": rec.turning_budget_B,
                    "R_rho": rec.turning_residue_R,
                    "native_opcode": f"0x{rec.native_opcode:02X}",
                    "har_ref": rec.har_ref,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.cmd == "run":
        res = compile_and_execute_cells(
            args.source,
            is_hc_compat=bool(args.hc_compat),
            run_rtl=not bool(args.no_rtl),
        )
        payload: dict[str, Any] = {
            "source_language": res.graph.source_language,
            "outputs": res.eval_result.outputs,
            "hw_outputs": res.hw_eval_result.outputs,
            "hvm_outputs": res.hvm_outputs,
            "verify_4b_prime_ok": res.verify_4b_prime_ok,
            "verify_4b_prime_reason": res.verify_4b_prime_reason,
            "instruction_words": len(res.compiled.words),
            "compute_instruction_words": len(res.compiled.compute_only_words),
            "peak_gpr_used": res.compiled.peak_gpr_used,
            "peak_hreg_used": res.compiled.peak_hreg_used,
            "guards_elided": res.compiled.guards_elided,
            "guards_emitted": res.compiled.guards_emitted,
            "native_letter_opcodes_emitted": res.compiled.native_letter_opcodes_emitted,
            "three_way_parity": res.three_way_parity,
            "hw_rtl_parity": res.hw_rtl_parity,
            "epistemic_status": res.epistemic_status.value,
            "assembly": res.compiled.assembly_text,
        }
        if res.rtl_measurement is not None:
            payload["rtl"] = {
                "halted": res.rtl_measurement.halted,
                "compute_cycles": res.rtl_measurement.compute_cycles,
                "io_cycles": res.rtl_measurement.io_cycles,
                "total_cycles": res.rtl_measurement.total_cycles,
                "printed_outputs": res.rtl_measurement.printed_outputs,
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "benchmarks":
        rep_bench = run_all_benchmark_tiers(run_rtl=not bool(args.no_rtl))
        print(json.dumps(rep_bench, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "APPROVED_MATH_LATIN_OPERATORS",
    "ARABIC_INDIC_DIGITS",
    "BOARD_CLOCK_HZ",
    "CANONICAL_JSON_SEAL",
    "CANONICAL_ROM_252B_SEAL",
    "CANONICAL_ROM_504B_ROW_MAJOR_SEAL",
    "CANONICAL_ROM_504B_RTL_WORD_BE_SEAL",
    "CANONICAL_ROM_SEAL",
    "DATASET_ID",
    "DEFAULT_OVERLAY_LOAD_ADDR",
    "DOCUMENTED_SOURCE_ERRATA",
    "FORBIDDEN_LOOKALIKES",
    "GPR_FIRST",
    "GPR_LAST",
    "GPR_SCRATCH",
    "HCELL_EBNF_GRAMMAR",
    "HCELL_LANGUAGE_VERSION",
    "HC_COMPAT_VERSION",
    "HREG_COMPONENT_BITS",
    "HREG_COMPONENT_MAX",
    "HREG_FIRST",
    "HREG_LAST",
    "HSTAR_MARKER_SEMANTICS",
    "MASTER_TABLE_504B_BYTES",
    "MASTER_TABLE_ENGINE",
    "MAX_CANONICAL_LETTER_COMPONENT",
    "NATIVE_LETTER_OPCODES",
    "PIPELINE_FILL_DRAIN_CYCLES",
    "RECORDED_HB_MANIFEST_SEAL",
    "RTL_GUARD_WIDE_ADDERS",
    "SIM_CLOCK_HZ",
    "SOURCE_DOCUMENT",
    "UNIVERSAL_SAFE_ACCUMULATION_LENGTH",
    "W2_HAR_INSPECTION_UTILITY",
    "W2_HFS_LIFECYCLE_CLIENT",
    "W2_OVERLAY_VERIFICATION_CLIENT",
    "W2_SYSTEM_DIAGNOSTICS",
    "WAVE1_OVERLAYS",
    "AccumulationBoundAnalysis",
    "BenchmarkTierMetrics",
    "CellBackendError",
    "CellBasicBlock",
    "CellEvaluationError",
    "CellEvaluationResult",
    "CellEvaluator",
    "CellHISABackend",
    "CellIRGraph",
    "CellIRNode",
    "CellOp",
    "CellSemanticError",
    "CellSubroutineDef",
    "CellTraceEvent",
    "CellValueType",
    "CompiledHISAProgram",
    "EndToEndPipelineResult",
    "EpistemicStatus",
    "HCCompatBridge",
    "HCPUExecutionMeasurement",
    "HCellLexer",
    "HCellLexerError",
    "HCellParseError",
    "HCellParser",
    "HCellToken",
    "HCellTokenType",
    "HStarMarkerSemantics",
    "HStarSafetyAuditReport",
    "IndividualGuardProof",
    "MasterTableEngine",
    "MasterTableLetterRecord",
    "NativeLetterOpcodeSpec",
    "PathSafetyClass",
    "PrefixBoundAnalysis",
    "ProgramCostEstimate",
    "RTLWideAdderSpec",
    "SealAuditReport",
    "SemanticAnalysisReport",
    "SemanticAnalyzer",
    "SixGuardClosureProof",
    "SourceErratumRecord",
    "SourceInstructionMapEntry",
    "SourceSpan",
    "UnicodePolicyError",
    "Wave1OverlaySpec",
    "Wave2SyscallProgramSpec",
    "analyze_h0_letter_accumulation",
    "analyze_prefix_bounds",
    "audit_hstar_safety_contract",
    "build_cost_estimate",
    "build_native_letter_opcode_table",
    "candidate_a_verification_instructions",
    "candidate_b_verification_instructions",
    "compile_and_execute_cells",
    "estimate_print_io_cycles",
    "main",
    "parse_hc_to_cell_ir",
    "parse_hcell",
    "prove_six_guard_closure",
    "run_all_benchmark_tiers",
    "run_wave1_overlays",
    "run_wave2_syscalls",
    "tokenize_hcell",
    "validate_and_normalize_hijaiyyah_text",
]
