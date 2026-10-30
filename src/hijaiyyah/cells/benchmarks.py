"""Priority 3 — Multi-Scale Performance and Scalability Benchmark Suite (Tiers 1–9).

Implements the 9 graduated Hijaiyyah Cells benchmark tiers required by the Owner
Engineering Directive:
1. T1_SINGLE_LETTER: Single letter (`ب`)
2. T2_THREE_LETTER_BSM: Three-letter integration benchmark (`ب + س + م`)
3. T3_ALL_28_LETTERS: Full 28-letter Hijaiyyah alphabet (`ا..ي`)
4. T4_31_LETTER_SAFE_BOUND: 31-letter chain at universal 8-bit hardware limit (`31 × هـ`)
5. T5_32_LETTER_OVERFLOW: 32-letter overflow case (`32 × هـ`, mandatory `HGRD`)
6. T6_NESTED_COMPOSITE: Composite & nested cells (`Θ̂`, `U`, `ρ`, `Θ₄`, `‖·‖², `⟨·,·⟩`, `d₂²`)
7. T7_MULTI_BRANCH_DAG: Diamond dependency DAG with shared intermediate sub-cells
8. T8_CONTROL_FLOW_FN_LOOP: Subroutine (`ƒ`), conditional branch (`?`), and loop (`↻`)
9. T9_IDENTICAL_OUTPUT_COMPARISON: Workload-identical comparison across 4 compilation modes

Collects all 13 required architectural metrics per benchmark tier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.cells.hpg1_bridge import EndToEndPipelineResult, compile_and_execute_cells


@dataclass(frozen=True, slots=True)
class BenchmarkTierMetrics:
    """All 13 required scalability and performance metrics for one benchmark tier."""

    tier_id: str
    description: str
    source_language: str
    source_bytes: int
    token_count: int
    ast_node_count: int
    ir_node_count: int
    ir_edge_count: int
    compile_time_ms: float
    hisa_word_count: int
    compute_word_count: int
    gpr_peak: int
    hreg_peak: int
    dynamic_instruction_count: int
    dynamic_compute_instruction_count: int
    hcpu_compute_cycles: int | None
    hcpu_io_cycles: int | None
    hcpu_total_cycles: int | None
    memory_words_total: int
    verify_4b_cand_a_instr: int
    verify_4b_cand_b_instr: int
    verify_4b_ok: bool
    exact_outputs: list[int]
    hw_outputs: list[int]
    rtl_outputs: list[int] | None
    rtl_flags: int | None
    three_way_parity: bool
    hw_rtl_parity: bool
    epistemic_status: str


def _extract_tier_metrics(
    tier_id: str,
    description: str,
    res: EndToEndPipelineResult,
) -> BenchmarkTierMetrics:
    return BenchmarkTierMetrics(
        tier_id=tier_id,
        description=description,
        source_language=res.graph.source_language,
        source_bytes=res.source_bytes,
        token_count=res.token_count,
        ast_node_count=len(res.graph.nodes),
        ir_node_count=len(res.graph.nodes),
        ir_edge_count=res.graph.edge_count,
        compile_time_ms=res.compile_time_ms,
        hisa_word_count=len(res.compiled.words),
        compute_word_count=len(res.compiled.compute_only_words),
        gpr_peak=res.compiled.peak_gpr_used,
        hreg_peak=res.compiled.peak_hreg_used,
        dynamic_instruction_count=res.hvm_steps,
        dynamic_compute_instruction_count=res.hvm_compute_steps,
        hcpu_compute_cycles=(
            res.rtl_measurement.compute_cycles if res.rtl_measurement else None
        ),
        hcpu_io_cycles=(
            res.rtl_measurement.io_cycles if res.rtl_measurement else None
        ),
        hcpu_total_cycles=(
            res.rtl_measurement.total_cycles if res.rtl_measurement else None
        ),
        memory_words_total=res.cost_estimate.memory_words_total,
        verify_4b_cand_a_instr=res.cost_estimate.verification_instructions_cand_a,
        verify_4b_cand_b_instr=res.cost_estimate.verification_instructions_cand_b,
        verify_4b_ok=res.verify_4b_prime_ok,
        exact_outputs=res.eval_result.outputs,
        hw_outputs=res.hw_eval_result.outputs,
        rtl_outputs=(
            res.rtl_measurement.printed_outputs if res.rtl_measurement else None
        ),
        rtl_flags=(res.rtl_measurement.flags if res.rtl_measurement else None),
        three_way_parity=res.three_way_parity,
        hw_rtl_parity=res.hw_rtl_parity,
        epistemic_status=res.epistemic_status.value,
    )


def build_benchmark_sources() -> dict[str, tuple[str, str]]:
    """Return `(description, hcell_source)` for Benchmark Tiers 1 through 8."""
    all_28 = " ".join(r.char for r in MASTER_TABLE_ENGINE.records)
    haa_31 = " ".join(["هـ"] * 31)
    haa_32 = " ".join(["هـ"] * 32)

    return {
        "T1_SINGLE_LETTER": (
            "1. Satu huruf (ب: Θ̂, U, ρ, ‖ب‖²)",
            """
            خليه := ب;
            ⊢ خليه;
            ↦ Θ̂(خليه);
            ↦ U(خليه);
            ↦ ρ(خليه);
            ↦ ‖خليه‖²;
            """,
        ),
        "T2_THREE_LETTER_BSM": (
            "2. Ekspresi tiga huruf (ب + س + م -> 10, 6, 4, 112, 9)",
            """
            بسم := ب + س + م;
            ⊢ بسم;
            ↦ Θ̂(بسم);
            ↦ U(بسم);
            ↦ ρ(بسم);
            ↦ ‖بسم‖²;
            ↦ d₂²(ب, م);
            """,
        ),
        "T3_ALL_28_LETTERS": (
            "3. Ekspresi 28 huruf kanonik (ا..ي -> 89, 52, 37, 8780)",
            f"""
            ابجد := ⟪{all_28}⟫;
            ⊢ ابجد;
            ↦ Θ̂(ابجد);
            ↦ U(ابجد);
            ↦ ρ(ابجد);
            ↦ ‖ابجد‖²;
            """,
        ),
        "T4_31_LETTER_SAFE_BOUND": (
            "4. Rantai akumulasi 31 huruf pada batas aman 8-bit (31 × هـ -> 248, 248, 0)",
            f"""
            سليم := ⟪{haa_31}⟫;
            ⊢ سليم;
            ↦ Θ̂(سليم);
            ↦ U(سليم);
            ↦ ρ(سليم);
            """,
        ),
        "T5_32_LETTER_OVERFLOW": (
            "5. Kasus overflow 32 huruf (32 × هـ -> Θ̂_hw=0, U_hw=256, ρ_hw=-256, G4 FAIL)",
            f"""
            فيض := ⟪{haa_32}⟫;
            ⊢ فيض;
            ↦ Θ̂(فيض);
            ↦ U(فيض);
            ↦ ρ(فيض);
            """,
        ),
        "T6_NESTED_COMPOSITE": (
            "6. Ekspresi gabungan & nested cells (Θ̂, U, ρ, Θ₄, ‖·‖², ⟨·,·⟩, d₂²)",
            """
            جذر١ := ح + ق;
            جذر٢ := ع + ل + م;
            مركب := جذر١ + جذر٢;
            ⊢ مركب;
            ↦ Θ̂(مركب) + U(جذر١) - ρ(جذر٢);
            ↦ ‖مركب‖²;
            ↦ ⟨جذر١, جذر٢⟩;
            ↦ d₂²(جذر١, جذر٢) + Θ₄(مركب);
            """,
        ),
        "T7_MULTI_BRANCH_DAG": (
            "7. Graf dependensi bercabang (diamond DAG dengan berbagi sub-sel)",
            """
            اصل := ب + س;
            فرع١ := اصل + م;
            فرع٢ := اصل + ن;
            قمه := فرع١ + فرع٢;
            ⊢ قمه;
            ↦ Θ̂(قمه);
            ↦ U(فرع١) + U(فرع٢);
            ↦ ρ(فرع١) + ρ(فرع٢);
            ↦ d₂²(فرع١, فرع٢);
            ↦ ⟨فرع١, فرع٢⟩;
            """,
        ),
        "T8_CONTROL_FLOW_FN_LOOP": (
            "8. Program dengan fungsi (ƒ), percabangan (?), dan perulangan (↻)",
            """
            ƒ @وزن(@س, @ص) := (@س * ٢) + @ص;
            عداد := ٠;
            مجموع := ٠;
            حد := Θ̂(ب + س + م);
            ↻ (عداد < ٣) {
                مجموع := مجموع + @وزن(حد, عداد);
                عداد := عداد + ١;
            }
            ? (مجموع == ٦٣) {
                ↦ مجموع;
            } : {
                ↦ ٠;
            }
            ↦ عداد;
            """,
        ),
    }


def run_all_benchmark_tiers(*, run_rtl: bool = True) -> dict[str, Any]:
    """Execute Benchmark Tiers 1–9 and return a structured report."""
    tiers: list[dict[str, Any]] = []
    sources = build_benchmark_sources()

    for tier_id, (desc, src) in sources.items():
        res = compile_and_execute_cells(
            src,
            use_native_letter_opcodes=True,
            reuse_registers=True,
            run_rtl=run_rtl,
        )
        metrics = _extract_tier_metrics(tier_id, desc, res)
        tiers.append(asdict(metrics))

    # Tier 9: Identical-output comparison across 3 compilable pipelines on `ب + س + م`
    bsm_hcell = sources["T2_THREE_LETTER_BSM"][1]
    bsm_hc = """
    let b = 'ب';
    let s = 'س';
    let m = 'م';
    let bsm = b + s + m;
    bsm.guard();
    println(bsm.theta());
    println(bsm.U());
    println(bsm.rho());
    println(bsm.norm2());
    println(b.dist2(m));
    """
    t9_baseline = _extract_tier_metrics(
        "T9A_BASELINE_NO_LETTER_OPS_NO_REUSE",
        "9a. Baseline HLOAD+HCADD tanpa reuse register (.hcell)",
        compile_and_execute_cells(
            bsm_hcell,
            use_native_letter_opcodes=False,
            reuse_registers=False,
            run_rtl=run_rtl,
        ),
    )
    t9_hc = _extract_tier_metrics(
        "T9B_HC_COMPAT_SHARED_IR",
        "9b. Kompatibilitas .hc v1.0 melalui Shared Cell IR",
        compile_and_execute_cells(
            bsm_hc,
            is_hc_compat=True,
            use_native_letter_opcodes=True,
            reuse_registers=True,
            run_rtl=run_rtl,
        ),
    )
    t9_opt = _extract_tier_metrics(
        "T9C_OPTIMIZED_HCELL_NATIVE",
        "9c. Optimized .hcell (0xE0–0xFB + CU/CRHO + Reuse + HGRD Elision)",
        compile_and_execute_cells(
            bsm_hcell,
            use_native_letter_opcodes=True,
            reuse_registers=True,
            run_rtl=run_rtl,
        ),
    )

    return {
        "tiers_1_to_8": tiers,
        "tier_9_identical_workload_comparison": [
            asdict(t9_baseline),
            asdict(t9_hc),
            asdict(t9_opt),
        ],
    }


__all__ = [
    "BenchmarkTierMetrics",
    "build_benchmark_sources",
    "run_all_benchmark_tiers",
]
