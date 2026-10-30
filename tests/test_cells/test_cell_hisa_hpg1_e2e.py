"""Phase 4, Priorities 0–5, & Wave 2 Tests — End-to-End Parity, Boundaries, Overlays & Syscalls."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from hijaiyyah.cells.benchmarks import run_all_benchmark_tiers
from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.cells.hpg1_bridge import compile_and_execute_cells
from hijaiyyah.cells.spec import EpistemicStatus, audit_hstar_safety_contract
from hijaiyyah.cells.wave1_overlays import WAVE1_OVERLAYS, run_wave1_overlays
from hijaiyyah.cells.wave2_syscalls import run_wave2_syscalls
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]


def test_official_bsm_integration_benchmark_hcell_and_hc_three_way_parity() -> None:
    """Owner Decision 7 & 8: Official integration benchmark `ب + س + م` must
    produce `(10, 6, 4, 112, 9)` across CellEvaluator, HISAMachine, and HCPU RTL,
    pass 4-B' overlay verification (including RTL card loader), and separate
    pure compute cycles from PRINT I/O cycles."""
    hcell_src = """
    بسم := ب + س + م;
    ⊢ بسم;
    ↦ Θ̂(بسم);
    ↦ U(بسم);
    ↦ ρ(بسم);
    ↦ ‖بسم‖²;
    ↦ d₂²(ب, م);
    """
    hc_src = """
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

    res_hcell = compile_and_execute_cells(
        hcell_src,
        is_hc_compat=False,
        use_native_letter_opcodes=True,
        reuse_registers=True,
        run_rtl=True,
        run_rtl_loader=True,
    )
    res_hc = compile_and_execute_cells(
        hc_src,
        is_hc_compat=True,
        use_native_letter_opcodes=True,
        reuse_registers=True,
        run_rtl=True,
        run_rtl_loader=False,
    )

    assert res_hcell.eval_result.outputs == [10, 6, 4, 112, 9]
    assert res_hcell.hvm_outputs == [10, 6, 4, 112, 9]
    assert res_hc.eval_result.outputs == [10, 6, 4, 112, 9]
    assert res_hc.hvm_outputs == [10, 6, 4, 112, 9]

    assert res_hcell.verify_4b_prime_ok is True
    assert res_hcell.verify_4b_prime_reason == "loaded"
    assert res_hcell.compiled.guards_elided == 1
    assert res_hcell.compiled.guards_emitted == 0
    assert res_hcell.compiled.native_letter_opcodes_emitted == 3
    assert res_hcell.compiled.peak_gpr_used == 1
    assert res_hcell.compiled.peak_hreg_used <= 3
    assert res_hcell.three_way_parity is True

    if res_hcell.rtl_measurement is not None:
        assert res_hcell.epistemic_status == EpistemicStatus.SIMULATED
        assert res_hcell.rtl_measurement.printed_outputs == [10, 6, 4, 112, 9]
        assert res_hcell.rtl_measurement.halted is True
        assert res_hcell.rtl_measurement.compute_cycles == 17
        assert res_hcell.rtl_measurement.total_cycles > res_hcell.rtl_measurement.compute_cycles
        assert res_hcell.rtl_measurement.io_cycles > 0
        assert res_hcell.rtl_measurement.rtl_4b_prime_verdict == {
            "DONE": 1,
            "ANSWER": 1,
            "ABSENT": 0,
        }


def test_workload_identical_performance_comparison_baseline_vs_native_cells() -> None:
    """Owner Decision 8: Compare identical 5-output workload `(10, 6, 4, 112, 9)`
    between baseline HLOAD+HCADD without register reuse vs optimized native-letter
    + register reuse, separating compute cycles from PRINT I/O cycles."""
    hcell_src = """
    بسم := ب + س + م;
    ⊢ بسم;
    ↦ Θ̂(بسم);
    ↦ U(بسم);
    ↦ ρ(بسم);
    ↦ ‖بسم‖²;
    ↦ d₂²(ب, م);
    """
    baseline = compile_and_execute_cells(
        hcell_src,
        use_native_letter_opcodes=False,
        reuse_registers=False,
        run_rtl=True,
    )
    optimized = compile_and_execute_cells(
        hcell_src,
        use_native_letter_opcodes=True,
        reuse_registers=True,
        run_rtl=True,
    )

    assert baseline.eval_result.outputs == optimized.eval_result.outputs == [10, 6, 4, 112, 9]
    assert baseline.hvm_outputs == optimized.hvm_outputs == [10, 6, 4, 112, 9]
    assert len(optimized.compiled.words) < len(baseline.compiled.words)
    assert optimized.compiled.peak_gpr_used == 1 < baseline.compiled.peak_gpr_used == 5
    assert optimized.compiled.peak_hreg_used == 2 < baseline.compiled.peak_hreg_used == 7

    if baseline.rtl_measurement is not None and optimized.rtl_measurement is not None:
        assert optimized.rtl_measurement.compute_cycles < baseline.rtl_measurement.compute_cycles
        assert optimized.rtl_measurement.io_cycles == baseline.rtl_measurement.io_cycles


def test_all_28_native_letter_opcodes_compile_verify_and_execute_with_parity() -> None:
    """Owner Decision 7: Exercise all 28 native letter opcodes (0xE0–0xFB) in
    a single native `.hcell` program, verify 4-B' acceptance, and confirm
    Evaluator == HISAMachine == HCPU RTL."""
    all_letters = " ".join(r.char for r in MASTER_TABLE_ENGINE.records)
    src = f"""
    ابجد := ⟪{all_letters}⟫;
    ⊢ ابجد;
    ↦ Θ̂(ابجد);
    ↦ U(ابجد);
    ↦ ρ(ابجد);
    ↦ ‖ابجد‖²;
    """
    res = compile_and_execute_cells(src, run_rtl=True)
    assert res.eval_result.outputs == [89, 52, 37, 8780]
    assert res.hvm_outputs == res.eval_result.outputs
    assert res.verify_4b_prime_ok is True
    assert res.compiled.native_letter_opcodes_emitted == 28
    assert res.three_way_parity is True

    emitted_ops = {(w >> 24) for w in res.compiled.words}
    for code in range(0xE0, 0xFC):
        assert code in emitted_ops, f"Missing native letter opcode 0x{code:02X}"
        assert OpCode(code) in RTL_IMPLEMENTED


def test_priority_0_31_vs_32_haa_and_254_255_256_rtl_differential_boundaries() -> None:
    """Priority 0 & Six-Guard Formal Verification Requirement:
    - 31 × 'هـ' (248): guard elided, RTL outputs `[248, 248, 0]`.
    - 254 & 255 boundaries (`31 × هـ + ص` = 254, `31 × هـ + ص + د` = 255):
      guard elided, RTL matches exact N_0^18 outputs `[254, 252, 2]` and `[255, 253, 2]`.
    - 32 × 'هـ' (256): mandatory HGRD emitted, RTL wraps H0[0] to 0, outputs
      `[0, 256, 4294967040]`, and clears `FLAG_G = 0`.
    - Unbounded loop accumulating 'هـ' 32 times: compiler refuses guard elision,
      emits mandatory `HGRD`, and RTL catches the 8-bit overflow (`FLAG_G = 0`)!"""
    src_31 = (
        "سليم := ⟪" + " ".join(["هـ"] * 31) + "⟫;\n"
        "⊢ سليم;\n↦ Θ̂(سليم);\n↦ U(سليم);\n↦ ρ(سليم);\n"
    )
    res_31 = compile_and_execute_cells(src_31, run_rtl=True)
    assert res_31.compiled.guards_elided == 1
    assert res_31.compiled.guards_emitted == 0
    assert res_31.eval_result.outputs == [248, 248, 0]
    assert res_31.three_way_parity is True

    # Boundary 254 and 255 on Theta_hat
    src_254 = (
        "حد٢٥٤ := ⟪" + " ".join(["هـ"] * 31 + ["ص"]) + "⟫;\n"
        "⊢ حد٢٥٤;\n↦ Θ̂(حد٢٥٤);\n↦ U(حد٢٥٤);\n↦ ρ(حد٢٥٤);\n"
    )
    res_254 = compile_and_execute_cells(src_254, run_rtl=True)
    assert res_254.compiled.guards_elided == 1
    assert res_254.eval_result.outputs == [254, 252, 2]
    assert res_254.three_way_parity is True

    src_255 = (
        "حد٢٥٥ := ⟪" + " ".join(["هـ"] * 31 + ["ص", "د"]) + "⟫;\n"
        "⊢ حد٢٥٥;\n↦ Θ̂(حد٢٥٥);\n↦ U(حد٢٥٥);\n↦ ρ(حد٢٥٥);\n"
    )
    res_255 = compile_and_execute_cells(src_255, run_rtl=True)
    assert res_255.compiled.guards_elided == 1
    assert res_255.eval_result.outputs == [255, 253, 2]
    assert res_255.three_way_parity is True

    # Boundary 256 (32 × Haa)
    src_32 = (
        "فيض := ⟪" + " ".join(["هـ"] * 32) + "⟫;\n"
        "⊢ فيض;\n↦ Θ̂(فيض);\n↦ U(فيض);\n↦ ρ(فيض);\n"
    )
    res_32 = compile_and_execute_cells(src_32, run_rtl=True)
    assert res_32.compiled.guards_elided == 0
    assert res_32.compiled.guards_emitted == 1
    assert res_32.eval_result.outputs == [256, 256, 0]
    assert res_32.hw_eval_result.outputs == [0, 256, 4294967040]
    assert res_32.hw_rtl_parity is True
    if res_32.rtl_measurement is not None:
        assert res_32.rtl_measurement.printed_outputs == [0, 256, 4294967040]
        assert (res_32.rtl_measurement.flags & 0x01) == 0

    # Loop accumulating 32 × Haa dynamically: compiler preserves mandatory HGRD!
    src_loop_32 = """
    مسار := هـ;
    حرف := هـ;
    عداد := ١;
    ↻ (عداد < ٣٢) {
        مسار := مسار + حرف;
        عداد := عداد + ١;
    }
    ⊢ مسار;
    ↦ Θ̂(مسار);
    ↦ U(مسار);
    ↦ ρ(مسار);
    """
    res_loop_32 = compile_and_execute_cells(src_loop_32, run_rtl=True)
    assert res_loop_32.compiled.guards_elided == 0
    assert res_loop_32.compiled.guards_emitted == 1
    assert res_loop_32.hw_eval_result.outputs == [0, 256, 4294967040]
    assert res_loop_32.hw_rtl_parity is True
    if res_loop_32.rtl_measurement is not None:
        assert res_loop_32.rtl_measurement.printed_outputs == [0, 256, 4294967040]
        assert (res_loop_32.rtl_measurement.flags & 0x01) == 0


def test_directive_a_hstar_safety_contract_and_dynamic_runtime_coupling() -> None:
    """Directive A & Steps 3–6 Hardening: Verify the formal `H*` (`C_HSTAR`, index 17)
    safety contract across all 9 required boundary and dynamic cases:
    1. `127 × ك` (`Kaf`): Theta=254, Ka=127, AK=127, H*=127 -> passes (elided statically
       and passes runtime check `H* == Ka` AND `H* <= floor(Theta/2)` on dynamic loop).
    2. `128 × ك` (`Kaf`): exact Theta=256 wraps to 0 while Ka=128, AK=128, H*=128 ->
       `HGRD` alone passes AND `H* == Ka` (128 == 128) passes, but `H* <= floor(Theta/2)`
       (128 <= 0) REJECTS it (`FLAG_G = 0`) across Evaluator, HISAMachine, and HCPU RTL!
    3. `129 × ك` (`Kaf`): exact Theta=258 -> 2, H*=129 -> `129 <= 1` REJECTS it (`FLAG_G = 0`).
    4. `255 × ك` (`Kaf`): exact Theta=510 -> 254, H*=255 -> `255 <= 127` REJECTS it (`FLAG_G = 0`).
    5. `256 × ك` (`Kaf`): static Layer B prefix bound catches overflow at step 128.
    6. `CSET` on index 17 (`H* != Ka` while `2*H* <= Theta` passes): rejected by `H* == Ka`!
    7. `HFS_READ` (`⛁`) from external vector: emits mandatory runtime dual `H*` check and passes.
    8. Branch (`?`) with one path exceeding bound (`128 × ك` vs `4 × ك`): refuses elision and
       rejects the overflowing path at runtime (`FLAG_G = 0`).
    9. Loop (`↻`) with dynamic bound (`127` passes with `FLAG_G = 1`; `128` and `129` rejected
       with `FLAG_G = 0`)."""
    audit = audit_hstar_safety_contract()
    assert audit.hgrd_directly_checks_hstar is False
    assert audit.canonical_law_hstar_eq_ka is True
    assert audit.canonical_law_hstar_le_ak is True
    assert audit.canonical_law_2hstar_le_theta is True
    assert audit.kaf_128_wraps_theta_without_g4_fail is True
    assert audit.kaf_128_hstar_eq_ka_still_passes is True
    assert audit.kaf_128_rejected_by_half_theta_check is True
    assert audit.kaf_256_wraps_hstar_ka_ak_without_g2_fail is True
    assert audit.dynamic_path_requires_explicit_runtime_hstar_check is True

    # Verify audit table for 127, 128, 129, 255, 256 × Kaf
    assert audit.kaf_boundary_cases[127]["combined_runtime_guard_passes"] is True
    assert audit.kaf_boundary_cases[127]["static_layer_b_elision_permitted"] is True
    for bad_m in (128, 129, 255):
        assert audit.kaf_boundary_cases[bad_m]["hw_hgrd_only_passes"] is True
        assert audit.kaf_boundary_cases[bad_m]["hw_hstar_eq_ka_passes"] is True
        assert audit.kaf_boundary_cases[bad_m]["hw_hstar_le_half_theta_passes"] is False
        assert audit.kaf_boundary_cases[bad_m]["combined_runtime_guard_passes"] is False
        assert audit.kaf_boundary_cases[bad_m]["static_layer_b_elision_permitted"] is False
    assert audit.kaf_boundary_cases[256]["static_layer_b_elision_permitted"] is False

    # Case 1: 127 × Kaf (static word literal) -> elided, outputs [254, 127, 127, 127]
    src_127 = (
        "كاف١٢٧ := ⟪" + " ".join(["ك"] * 127) + "⟫;\n"
        "⊢ كاف١٢٧;\n↦ Θ̂(كاف١٢٧);\n↦ كاف١٢٧[٧];\n↦ كاف١٢٧[١٥];\n↦ H*(كاف١٢٧);\n"
    )
    res_127 = compile_and_execute_cells(src_127, run_rtl=True)
    assert res_127.compiled.guards_elided == 1
    assert res_127.compiled.guards_emitted == 0
    assert res_127.eval_result.outputs == [254, 127, 127, 127]
    assert res_127.hw_eval_result.last_guard_passed is True
    assert res_127.three_way_parity is True

    # Case 2: 128 × Kaf (static word literal) -> refuses elision, emits dual runtime check,
    # and rejects on Evaluator (8-bit), HISAMachine (8-bit), and HCPU RTL (FLAG_G == 0)!
    src_128 = (
        "كاف١٢٨ := ⟪" + " ".join(["ك"] * 128) + "⟫;\n"
        "⊢ كاف١٢٨;\n↦ Θ̂(كاف١٢٨);\n↦ كاف١٢٨[٧];\n↦ كاف١٢٨[١٥];\n↦ H*(كاف١٢٨);\n"
    )
    res_128 = compile_and_execute_cells(src_128, run_rtl=True)
    assert res_128.compiled.guards_elided == 0
    assert res_128.compiled.guards_emitted == 1
    assert res_128.compiled.runtime_hstar_checks_emitted == 1
    assert res_128.eval_result.outputs == [256, 128, 128, 128]
    assert res_128.hw_eval_result.outputs == [0, 128, 128, 128]
    assert res_128.hw_eval_result.last_guard_passed is False
    assert res_128.hvm_hw_8bit_guard_pass is False
    assert res_128.hw_rtl_parity is True
    if res_128.rtl_measurement is not None:
        assert res_128.rtl_measurement.printed_outputs == [0, 128, 128, 128]
        assert (res_128.rtl_measurement.flags & 0x01) == 0

    # Case 3 & 4 & 9: Dynamic loop accumulating N × Kaf for N in (127, 128, 129, 255, 256)
    for n_iters, exp_hw_outputs, exp_guard_pass in (
        (127, [254, 127, 127], True),
        (128, [0, 128, 128], False),
        (129, [2, 129, 129], False),
        (255, [254, 255, 255], False),
        (256, [0, 0, 0], False),
    ):
        src_loop_n = f"""
        مسار := ك;
        حرف := ك;
        عداد := ١;
        ↻ (عداد < {n_iters}) {{
            مسار := مسار + حرف;
            عداد := عداد + ١;
        }}
        ⊢ مسار;
        ↦ Θ̂(مسار);
        ↦ مسار[٧];
        ↦ H*(مسار);
        """
        res_n = compile_and_execute_cells(src_loop_n, run_rtl=True)
        assert res_n.compiled.guards_emitted == 1
        assert res_n.compiled.runtime_hstar_checks_emitted >= 1
        assert res_n.hw_eval_result.outputs == exp_hw_outputs
        assert res_n.hw_eval_result.last_guard_passed is exp_guard_pass
        assert res_n.hvm_hw_8bit_guard_pass is exp_guard_pass
        assert res_n.hw_rtl_parity is True
        if res_n.rtl_measurement is not None:
            assert res_n.rtl_measurement.printed_outputs == exp_hw_outputs
            assert bool(res_n.rtl_measurement.flags & 0x01) is exp_guard_pass

    # Case 5: 256 × Kaf static Layer B check refuses elision (overflows slots 0, 7, 15, 17)
    src_256 = "كاف٢٥٦ := ⟪" + " ".join(["ك"] * 256) + "⟫;\n⊢ كاف٢٥٦;\n↦ H*(كاف٢٥٦);\n"
    res_256 = compile_and_execute_cells(src_256, run_rtl=False)
    assert res_256.compiled.guards_elided == 0
    assert res_256.compiled.guards_emitted == 1
    assert res_256.compiled.runtime_hstar_checks_emitted == 1
    assert res_256.semantic_report.guard_certificates[0].overflowed_indices == (0, 7, 15, 17)

    # Case 6 & Audit C: Targeted RTL truth-table tests where each constituent condition
    # (G_HGRD, H* == Ka, H* <= floor(Theta_hat/2)) fails independently while the other two pass!
    from hijaiyyah.cells.hpg1_bridge import _get_parity_sim_binary, _run_rtl_words
    from hijaiyyah.hisa.assembler import assemble

    guard_seq = """
        HGRD  H0
        FRD   R1
        ANDI  R1, R1, #1
        CGET  R0, H0, #17
        CGET  R2, H0, #7
        CMP   R0, R2
        FRD   R2
        SHRI  R2, R2, #1
        AND   R1, R1, R2
        CGET  R2, H0, #0
        SHRI  R2, R2, #1
        SUB   R0, R2, R0
        SHRI  R0, R0, #31
        XORI  R0, R0, #1
        AND   R0, R0, R1
        ANDI  R0, R0, #1
        FWR   R0
        HALT
    """
    # 6a. (G=1, H*==Ka=0, 2*H*<=Theta=1): 'ب' (Theta=2, Ka=0) with CSET #17 = 1 -> FLAG_G == 0
    cset_hstar_words = list(
        assemble(
            "        HLOAD H0, #2\n        MOVI R1, 1\n        CSET H0, R1, #17\n" + guard_seq
        )
    )
    # 6b. (G=0, H*==Ka=1, 2*H*<=Theta=1): 'ب' with CSET #14 (AN) = 0 -> FLAG_G == 0
    cset_g1_words = list(
        assemble(
            "        HLOAD H0, #2\n        MOVI R1, 0\n        CSET H0, R1, #14\n" + guard_seq
        )
    )
    # 6c. (G=1, H*==Ka=1, 2*H*<=Theta=0): 'ك' with CSET #0 (Theta) = 0 -> FLAG_G == 0
    cset_theta_words = list(
        assemble(
            "        HLOAD H0, #22\n        MOVI R1, 0\n        CSET H0, R1, #0\n" + guard_seq
        )
    )
    # 6d. (G=1, H*==Ka=1, 2*H*<=Theta=1): 'ك' unmodified -> FLAG_G == 1
    cset_ok_words = list(assemble("        HLOAD H0, #22\n" + guard_seq))

    sim_bin = _get_parity_sim_binary()
    if sim_bin is not None:
        for bad_w in (cset_hstar_words, cset_g1_words, cset_theta_words):
            rtl_out = _run_rtl_words(sim_bin, bad_w)
            assert rtl_out["halted"] is True
            assert (rtl_out["flags"] & 0x01) == 0
        rtl_ok = _run_rtl_words(sim_bin, cset_ok_words)
        assert rtl_ok["halted"] is True
        assert (rtl_ok["flags"] & 0x01) == 1

    # Case 7: HFS_READ (⛁) from external vector emits mandatory dual H* runtime check
    src_hfs = """
    ⏣(٦, ٢);
    خل := ب + ك;
    ⏣(٨, ٢, خل);
    مسترجع := ⛁(٢);
    ⊢ مسترجع;
    ↦ Θ̂(مسترجع);
    ↦ H*(مسترجع);
    """
    res_hfs = compile_and_execute_cells(src_hfs, run_rtl=True)
    assert res_hfs.compiled.guards_elided == 0
    assert res_hfs.compiled.guards_emitted == 1
    assert res_hfs.compiled.runtime_hstar_checks_emitted == 1
    assert res_hfs.eval_result.outputs == [4, 1]
    assert res_hfs.three_way_parity is True
    assert res_hfs.hw_rtl_parity is True

    # Case 8: Branch (?) with one path exceeding the 128 × Kaf bound refuses elision
    # and rejects when the overflowing branch is taken
    kaf_4_str = " ".join(["ك"] * 4)
    kaf_128_str = " ".join(["ك"] * 128)
    src_branch_kaf = f"""
    خل := ⟪{kaf_4_str}⟫;
    شرط := ٠;
    ? (شرط == ١) {{
        خل := ⟪{kaf_4_str}⟫;
    }} : {{
        خل := ⟪{kaf_128_str}⟫;
    }}
    ⊢ خل;
    ↦ Θ̂(خل);
    ↦ H*(خل);
    """
    res_branch_kaf = compile_and_execute_cells(src_branch_kaf, run_rtl=True)
    assert res_branch_kaf.compiled.guards_elided == 0
    assert res_branch_kaf.compiled.guards_emitted == 1
    assert res_branch_kaf.compiled.runtime_hstar_checks_emitted == 1
    assert res_branch_kaf.hw_eval_result.outputs == [0, 128]
    assert res_branch_kaf.hw_eval_result.last_guard_passed is False
    assert res_branch_kaf.hw_rtl_parity is True
    if res_branch_kaf.rtl_measurement is not None:
        assert (res_branch_kaf.rtl_measurement.flags & 0x01) == 0


def test_priority_2_control_flow_branches_loops_and_subroutines_hcell_and_hc() -> None:
    """Priority 2: Verify branches (`?` / `if`), bounded loops (`↻` / `while`),
    and subroutines (`ƒ` / `fn` -> `CALL`/`RET`) compile through `HPG1` + `4-B'`
    and execute with 3-way parity across `.hcell`, `.hc`, `HISAMachine`, and HCPU RTL."""
    hcell_cfg = """
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
    """
    hc_cfg = """
    fn weight(x, y) {
        return (x * 2) + y;
    }
    let cnt = 0;
    let total = 0;
    let bsm = 'ب' + 'س' + 'م';
    let lim = bsm.theta();
    while (cnt < 3) {
        total = total + weight(lim, cnt);
        cnt = cnt + 1;
    }
    if (total == 63) {
        println(total);
    } else {
        println(0);
    }
    println(cnt);
    """
    res_hcell = compile_and_execute_cells(hcell_cfg, run_rtl=True)
    res_hc = compile_and_execute_cells(hc_cfg, is_hc_compat=True, run_rtl=True)

    assert res_hcell.eval_result.outputs == [63, 3]
    assert res_hcell.hvm_outputs == [63, 3]
    assert res_hcell.verify_4b_prime_ok is True
    assert res_hcell.three_way_parity is True

    assert res_hc.eval_result.outputs == [63, 3]
    assert res_hc.hvm_outputs == [63, 3]
    assert res_hc.verify_4b_prime_ok is True
    assert res_hc.three_way_parity is True


def test_priority_3_all_9_benchmark_tiers_execute_and_collect_13_metrics() -> None:
    """Priority 3: Run all 9 benchmark tiers and verify every tier passes 4-B'
    and matches hardware/evaluator parity."""
    report = run_all_benchmark_tiers(run_rtl=True)
    tiers = report["tiers_1_to_8"]
    assert len(tiers) == 8
    for t in tiers:
        assert t["verify_4b_ok"] is True, f"Tier {t['tier_id']} failed 4-B'"
        assert t["hw_rtl_parity"] is True, f"Tier {t['tier_id']} failed HW/RTL parity"
        if t["tier_id"] != "T5_32_LETTER_OVERFLOW":
            assert t["three_way_parity"] is True, f"Tier {t['tier_id']} failed 3-way parity"

    t9 = report["tier_9_identical_workload_comparison"]
    assert len(t9) == 3
    for mode in t9:
        assert mode["exact_outputs"] == [10, 6, 4, 112, 9]
        assert mode["three_way_parity"] is True


def test_priority_4_wave1_system_overlays_pass_4b_prime_and_rtl_parity() -> None:
    """Priority 4: Verify all 5 Wave 1 system-programming overlays compile from
    native `.hcell`, pass `HPG1` + `4-B'`, and execute with 3-way parity on HCPU RTL."""
    results = run_wave1_overlays(run_rtl=True, run_rtl_loader=False)
    assert len(results) == len(WAVE1_OVERLAYS) == 5
    for spec in WAVE1_OVERLAYS:
        res = results[spec.overlay_id]
        assert res.verify_4b_prime_ok is True, f"{spec.overlay_id} failed 4-B'"
        assert res.eval_result.outputs == spec.expected_outputs
        assert res.hvm_outputs == spec.expected_outputs
        assert res.three_way_parity is True
        if res.rtl_measurement is not None:
            assert res.rtl_measurement.printed_outputs == spec.expected_outputs


def test_directive_c_and_d_wave2_syscall_utilities_e2e_and_rtl_parity() -> None:
    """Directive C & D: Verify all 4 Wave 2 `.hcell` system utilities
    (`w2_har_inspection`, `w2_hfs_lifecycle`, `w2_overlay_verifier`, `w2_sys_diagnostics`)
    compile without Latin keywords, pass `HPG1` + `4-B'` (including RTL card loader),
    and execute with 3-way differential parity across `CellEvaluator`, `HISAMachine`,
    and `HCPU` RTL."""
    specs = run_wave2_syscalls(run_rtl=True, run_rtl_loader=True)
    assert len(specs) == 4
    for sp in specs:
        res = sp.result
        assert res.verify_4b_prime_ok is True, f"{sp.program_id} failed 4-B'"
        assert res.verify_4b_prime_reason == "loaded"
        assert res.compiled.syscalls_emitted > 0
        assert res.eval_result.outputs == sp.expected_outputs, (
            f"{sp.program_id} eval outputs {res.eval_result.outputs} != {sp.expected_outputs}"
        )
        assert res.hvm_outputs == sp.expected_outputs, (
            f"{sp.program_id} HVM outputs {res.hvm_outputs} != {sp.expected_outputs}"
        )
        assert res.three_way_parity is True, f"{sp.program_id} failed 3-way parity"
        assert res.hw_rtl_parity is True, f"{sp.program_id} failed HW/RTL parity"
        if res.rtl_measurement is not None:
            assert res.rtl_measurement.printed_outputs == sp.expected_outputs
            if sp.program_id == "w2_overlay_verifier":
                assert res.rtl_measurement.rtl_4b_prime_verdict == {
                    "DONE": 1,
                    "ANSWER": 1,
                    "ABSENT": 0,
                }


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh not installed")
def test_powershell_host_wrapper_passes_end_to_end() -> None:
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(ROOT / "powershell" / "Test-HijaiyyahCells.ps1")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"PowerShell test failed:\n{proc.stdout}\n{proc.stderr}"
    assert "ALL POWERSHELL HOST CHECKS PASSED!" in proc.stdout
