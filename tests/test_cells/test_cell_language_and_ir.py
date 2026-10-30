"""Phase 2 & 3 Tests — Native .hcell, .hc Bridge, Two-Layer Proofs, & Prefix Bounds."""

from __future__ import annotations

import pytest

from hijaiyyah.cells.evaluator import CellEvaluator
from hijaiyyah.cells.lexer import HCellLexerError, tokenize_hcell
from hijaiyyah.cells.parser import HCellParseError, parse_hc_to_cell_ir, parse_hcell
from hijaiyyah.cells.semantic import CellSemanticError, SemanticAnalyzer
from hijaiyyah.cells.spec import (
    HSTAR_MARKER_SEMANTICS,
    NATIVE_LETTER_OPCODES,
    RTL_GUARD_WIDE_ADDERS,
    UNIVERSAL_SAFE_ACCUMULATION_LENGTH,
    analyze_h0_letter_accumulation,
    prove_six_guard_closure,
)


def test_native_hcell_rejects_latin_keywords_and_identifiers() -> None:
    """Owner Decision 1 (Option 2): .hcell forbids Latin keywords like `let`, `fn`, `println`."""
    for forbidden_src in (
        "let x = ب;",
        "fn main() {}",
        "println(Θ̂(ب));",
        "bsm := ب + س + م;",
    ):
        with pytest.raises(HCellLexerError, match="Latin keyword or identifier"):
            tokenize_hcell(forbidden_src)


def test_native_hcell_and_hc_compat_produce_equivalent_cell_ir_semantics() -> None:
    """Owner Decision 1: Both .hcell and .hc frontends share SemanticAnalyzer and CellEvaluator."""
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
    g_hcell = parse_hcell(hcell_src)
    g_hc = parse_hc_to_cell_ir(hc_src)

    rep_hcell = SemanticAnalyzer().analyze(g_hcell)
    rep_hc = SemanticAnalyzer().analyze(g_hc)

    assert rep_hcell.valid and rep_hc.valid
    assert rep_hcell.guards_discharged == 1
    assert rep_hc.guards_discharged == 1
    assert len(rep_hcell.guard_certificates) == 1
    assert rep_hcell.guard_certificates[0].all_six_proven_and_hw_isomorphic is True

    ev_hcell = CellEvaluator().evaluate(g_hcell)
    ev_hc = CellEvaluator().evaluate(g_hc)

    assert ev_hcell.outputs == ev_hc.outputs == [10, 6, 4, 112, 9]
    assert ev_hcell.bindings["بسم"] == ev_hc.bindings["bsm"] == (
        10, 0, 0, 1, 0, 1, 0, 0, 1, 2, 2, 0, 0, 1, 1, 2, 5, 0
    )


def test_word_literal_and_arabic_indic_digits_in_hcell() -> None:
    src = """
    ⟦كلم_١⟧ := ⟪ب س م⟫;
    ↦ ⟦كلم_١⟧[٠];
    ↦ Θ₄(⟦كلم_١⟧);
    ↦ ⟨ب, م⟩;
    ↦ Φ(ج);
    """
    g = parse_hcell(src)
    SemanticAnalyzer().analyze(g)
    res = CellEvaluator().evaluate(g)
    assert res.outputs == [10, 2, 8, 24]


def test_delta_domain_c_type_safety_refuses_hybit_only_operations() -> None:
    """Delta(a, b) lies in Z^14 (Domain C), not H, so U(Delta) and ⊢ Delta must fail."""
    bad_guard = """
    فرق := Δ(ب, س);
    ⊢ فرق;
    """
    g1 = parse_hcell(bad_guard)
    with pytest.raises(CellSemanticError, match="requires operand of type hybit, got delta14"):
        SemanticAnalyzer().analyze(g1)

    bad_u = """
    فرق := ب - س;
    ↦ U(فرق);
    """
    g2 = parse_hcell(bad_u)
    with pytest.raises(CellSemanticError, match="requires operand of type hybit, got delta14"):
        SemanticAnalyzer().analyze(g2)


def test_rtl_wide_adder_capacity_and_hstar_semantics_proof() -> None:
    """Verify RTL wide-adder capacities (`sum_n`, `sum_k`, `sum_q`, `u_val`, `rho_signed`)
    and `H*` (`C_HSTAR`, slot 17) phonological marker semantics."""
    by_id = {spec.guard_id: spec for spec in RTL_GUARD_WIDE_ADDERS}
    assert set(by_id) == {"G1", "G2", "G3", "G4_U", "G4_RHO"}

    assert by_id["G1"].bit_width == 10
    assert by_id["G1"].max_possible_input_value == 765
    assert by_id["G1"].wire_max_capacity == 1023
    assert by_id["G1"].cannot_overflow_internally is True

    assert by_id["G2"].bit_width == 11
    assert by_id["G2"].max_possible_input_value == 1275
    assert by_id["G2"].wire_max_capacity == 2047
    assert by_id["G2"].cannot_overflow_internally is True

    assert by_id["G3"].bit_width == 11
    assert by_id["G3"].max_possible_input_value == 1275
    assert by_id["G3"].wire_max_capacity == 2047
    assert by_id["G3"].cannot_overflow_internally is True

    assert by_id["G4_U"].bit_width == 11
    assert by_id["G4_U"].max_possible_input_value == 1785
    assert by_id["G4_U"].wire_max_capacity == 2047
    assert by_id["G4_U"].cannot_overflow_internally is True

    assert by_id["G4_RHO"].bit_width == 12 and by_id["G4_RHO"].signed is True
    assert by_id["G4_RHO"].min_possible_input_value == -1785 >= -2048
    assert by_id["G4_RHO"].max_possible_input_value == 255 <= 2047
    assert by_id["G4_RHO"].cannot_overflow_internally is True

    # Verify H* semantics and 254, 255, 256 × Kaf ('ك') boundary
    assert HSTAR_MARKER_SEMANTICS.slot_index == 17
    assert HSTAR_MARKER_SEMANTICS.sole_nonzero_canonical_letter == "ك"
    assert HSTAR_MARKER_SEMANTICS.included_in_v14_metric_ops is False
    assert HSTAR_MARKER_SEMANTICS.constrained_by_hardware_hgrd is False

    k127 = analyze_h0_letter_accumulation(["ك"] * 127)
    assert k127.exact_sum_vector[0] == 254
    assert k127.exact_sum_vector[7] == 127
    assert k127.exact_sum_vector[15] == 127
    assert k127.exact_sum_vector[17] == 127
    assert k127.six_guard_proof.hstar_equals_ka_exact is True
    assert k127.six_guard_proof.hstar_2x_le_theta_exact is True
    assert k127.six_guard_proof.hw_hstar_equals_ka is True
    assert k127.six_guard_proof.hw_hstar_le_half_theta is True
    assert k127.guard_elision_permitted is True

    # 128 × Kaf ('ك'): Theta_hat = 256 wraps to 0 while Ka = 128, AK = 128, H* = 128!
    # Hardware HGRD passes AND H* == Ka (128 == 128) passes, ONLY H* <= floor(Theta_hat/2)
    # (128 <= 0) catches the 8-bit overflow of Theta_hat!
    k128 = analyze_h0_letter_accumulation(["ك"] * 128)
    assert k128.exact_sum_vector[0] == 256
    assert k128.exact_sum_vector[7] == 128
    assert k128.exact_sum_vector[15] == 128
    assert k128.exact_sum_vector[17] == 128
    assert k128.exact_U == 0 and k128.exact_rho == 256
    assert k128.hardware_wrapped_vector[0] == 0
    assert k128.hardware_wrapped_vector[7] == 128
    assert k128.hardware_wrapped_vector[15] == 128
    assert k128.hardware_wrapped_vector[17] == 128
    assert k128.hardware_U == 0 and k128.hardware_rho_signed == 0
    assert k128.hardware_passes_guard is True
    assert k128.six_guard_proof.hw_hstar_equals_ka is True
    assert k128.six_guard_proof.hw_hstar_le_half_theta is False
    assert k128.six_guard_proof.hstar_coupled_bound_proven is False
    assert k128.guard_elision_permitted is False

    # 129 × Kaf ('ك'): Theta_hat = 258 -> 2, Ka = 129, AK = 129, H* = 129 (129 <= 1 fails!)
    k129 = analyze_h0_letter_accumulation(["ك"] * 129)
    assert k129.exact_sum_vector[0] == 258 and k129.hardware_wrapped_vector[0] == 2
    assert k129.hardware_wrapped_vector[17] == 129
    assert k129.six_guard_proof.hw_hstar_equals_ka is True
    assert k129.six_guard_proof.hw_hstar_le_half_theta is False
    assert k129.guard_elision_permitted is False

    # 255 × Kaf ('ك'): Theta_hat = 510 -> 254, Ka = 255, AK = 255, H* = 255 (255 <= 127 fails!)
    k255 = analyze_h0_letter_accumulation(["ك"] * 255)
    assert k255.exact_sum_vector[0] == 510 and k255.hardware_wrapped_vector[0] == 254
    assert k255.hardware_wrapped_vector[17] == 255
    assert k255.six_guard_proof.hw_hstar_equals_ka is True
    assert k255.six_guard_proof.hw_hstar_le_half_theta is False
    assert k255.guard_elision_permitted is False

    k256 = analyze_h0_letter_accumulation(["ك"] * 256)
    assert k256.exact_sum_vector[17] == 256
    assert k256.hardware_wrapped_vector[17] == 0
    assert 17 in k256.overflowed_components
    assert k256.guard_elision_permitted is False


def test_priority_0_two_layer_six_guard_closure_and_31_vs_32_haa_mathematics() -> None:
    """Verify Two-Layer Proof (Layer A mathematical closure vs Layer B hardware prefix safety)
    on 31×Haa vs 32×Haa."""
    assert len(NATIVE_LETTER_OPCODES) == 28
    assert UNIVERSAL_SAFE_ACCUMULATION_LENGTH == 31

    b31 = analyze_h0_letter_accumulation(["هـ"] * 31)
    assert b31.exact_sum_vector == (
        248, 0, 0, 0, 0, 0, 0, 0, 31, 0, 0, 0, 0, 62, 0, 31, 62, 0
    )
    assert b31.prefix_bound.step_count == 31
    assert b31.prefix_bound.prefix_max_by_step == tuple(8 * k for k in range(32))
    assert b31.prefix_bound.first_overflow_step is None
    assert b31.prefix_bound.all_prefixes_fit_8bit is True
    p31 = b31.six_guard_proof
    assert p31.layer_a_all_six_pass is True
    assert p31.layer_b_prefix_and_width_safe is True
    assert p31.all_six_proven_and_hw_isomorphic is True
    assert b31.guard_elision_permitted is True

    # 32 × Haa ('هـ'): Layer A still passes over N_0^18, but Layer B fails at step 32!
    b32 = analyze_h0_letter_accumulation(["هـ"] * 32)
    assert b32.exact_sum_vector == (
        256, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 64, 0, 32, 64, 0
    )
    assert b32.hardware_wrapped_vector == (
        0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 64, 0, 32, 64, 0
    )
    assert b32.overflowed_components == (0,)
    assert b32.prefix_bound.first_overflow_step == 32
    assert b32.prefix_bound.all_prefixes_fit_8bit is False
    p32 = b32.six_guard_proof
    assert p32.layer_a_all_six_pass is True
    assert p32.layer_b_prefix_and_width_safe is False
    assert p32.g4.layer_a_math_holds is True
    assert p32.g4.layer_b_inputs_fit_8bit is False
    assert p32.g4.rtl_holds is False
    assert p32.all_six_proven_and_hw_isomorphic is False
    assert b32.guard_elision_permitted is False


def test_differential_boundary_values_0_1_254_255_256_across_all_six_guards() -> None:
    """Differential boundary tests across 0, 1, 254, 255, 256 for G1, G2, G3, G4, T1, T2."""
    # 1. G4 (Theta_hat at slot 0): 0, 1, 254, 255, 256
    assert analyze_h0_letter_accumulation(["ا"]).exact_sum_vector[0] == 0
    assert analyze_h0_letter_accumulation(["د"]).exact_sum_vector[0] == 1
    g4_254 = analyze_h0_letter_accumulation(["هـ"] * 31 + ["ص"])
    assert g4_254.exact_sum_vector[0] == 254 and g4_254.guard_elision_permitted is True
    g4_255 = analyze_h0_letter_accumulation(["هـ"] * 31 + ["ص", "د"])
    assert g4_255.exact_sum_vector[0] == 255 and g4_255.guard_elision_permitted is True
    g4_256 = analyze_h0_letter_accumulation(["هـ"] * 32)
    assert g4_256.exact_sum_vector[0] == 256 and g4_256.guard_elision_permitted is False
    assert g4_256.per_guard_hardware["G4"] is False

    # 2. G1 (Nuqtah / AN at slot 14): 0, 1, 254, 255, 256
    assert analyze_h0_letter_accumulation(["ا"]).exact_sum_vector[14] == 0
    assert analyze_h0_letter_accumulation(["ب"]).exact_sum_vector[14] == 1
    g1_254 = analyze_h0_letter_accumulation(["ث"] * 84 + ["ت"])
    assert g1_254.exact_sum_vector[14] == 254 and g1_254.guard_elision_permitted is True
    g1_255 = analyze_h0_letter_accumulation(["ث"] * 85)
    assert g1_255.exact_sum_vector[14] == 255 and g1_255.guard_elision_permitted is True
    # 85 × 'ت' (Na=170 <= 255) + 86 × 'ب' (Nd=86 <= 255) -> AN = 256 wraps to 0 while sum_n = 256!
    g1_256_vec = (0, 170, 0, 86, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 256, 0, 0, 0)
    p_g1_256 = prove_six_guard_closure(g1_256_vec)
    assert p_g1_256.g1.layer_a_math_holds is True
    assert p_g1_256.g1.layer_b_inputs_fit_8bit is False
    assert p_g1_256.g1.rtl_holds is False

    # 3. G2 (Khatt / AK at slot 15): 0, 1, 254, 255, 256
    assert analyze_h0_letter_accumulation(["د"]).exact_sum_vector[15] == 0
    assert analyze_h0_letter_accumulation(["ا"]).exact_sum_vector[15] == 1
    g2_254 = analyze_h0_letter_accumulation(["ا"] * 254)
    assert g2_254.exact_sum_vector[15] == 254 and g2_254.guard_elision_permitted is True
    g2_255 = analyze_h0_letter_accumulation(["ا"] * 255)
    assert g2_255.exact_sum_vector[15] == 255 and g2_255.guard_elision_permitted is True
    # Kp=200 <= 255, Kx=56 <= 255 -> AK = 256 wraps to 0 while sum_k[10:0] = 256!
    g2_256 = analyze_h0_letter_accumulation(["ا"] * 200 + ["ل"] * 56)
    assert g2_256.exact_sum_vector[15] == 256
    assert g2_256.six_guard_proof.g2.layer_a_math_holds is True
    assert g2_256.six_guard_proof.g2.rtl_holds is False
    assert g2_256.guard_elision_permitted is False

    # 4. G3 (Qaws / AQ at slot 16): 0, 1, 254, 255, 256
    assert analyze_h0_letter_accumulation(["ا"]).exact_sum_vector[16] == 0
    assert analyze_h0_letter_accumulation(["د"]).exact_sum_vector[16] == 1
    g3_254 = analyze_h0_letter_accumulation(["د"] * 200 + ["ر"] * 54)
    assert g3_254.exact_sum_vector[16] == 254 and g3_254.guard_elision_permitted is True
    g3_255 = analyze_h0_letter_accumulation(["د"] * 200 + ["ر"] * 55)
    assert g3_255.exact_sum_vector[16] == 255 and g3_255.guard_elision_permitted is True
    # Qa=128 <= 255, Qs=128 <= 255 -> AQ = 256 wraps to 0 while sum_q[10:0] = 256!
    g3_256_vec = (255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 128, 128, 0, 0, 0, 256, 0)
    p_g3_256 = prove_six_guard_closure(g3_256_vec)
    assert p_g3_256.g3.layer_a_math_holds is True
    assert p_g3_256.g3.rtl_holds is False

    # 5. T1 & T2: when Qc = 256 wraps to 0 in hardware while Ks=1 or Kc=1
    t1_256_vec = (1024, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 256, 0, 1, 256, 0)
    p_t1_256 = prove_six_guard_closure(t1_256_vec)
    assert p_t1_256.t1.layer_a_math_holds is True
    assert p_t1_256.t1.rtl_holds is False

    t2_256_vec = (1024, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 256, 0, 1, 256, 0)
    p_t2_256 = prove_six_guard_closure(t2_256_vec)
    assert p_t2_256.t2.layer_a_math_holds is True
    assert p_t2_256.t2.rtl_holds is False


def test_path_sensitive_branch_and_loop_guard_elision_rules() -> None:
    """Confirm that:
    1. A branch where both arms are 8-bit safe (e.g. 3×Haa vs 5×Haa) allows HGRD elision.
    2. A branch where either arm overflows 8 bits (32×Haa vs 3×Haa) forbids HGRD elision.
    3. A loop that mutates a hybit variable NEVER elides HGRD on that variable."""
    haa_3 = " ".join(["هـ"] * 3)
    haa_5 = " ".join(["هـ"] * 5)
    haa_32 = " ".join(["هـ"] * 32)

    safe_branch_src = f"""
    خل := ⟪{haa_3}⟫;
    شرط := ١;
    ? (شرط == ١) {{
        خل := ⟪{haa_5}⟫;
    }} : {{
        خل := ⟪{haa_3}⟫;
    }}
    ⊢ خل;
    """
    rep_safe = SemanticAnalyzer().analyze(parse_hcell(safe_branch_src))
    assert rep_safe.guards_total == 1
    assert rep_safe.guards_discharged == 1
    assert rep_safe.guards_mandatory_runtime == 0

    unsafe_branch_src = f"""
    خل := ⟪{haa_3}⟫;
    شرط := ١;
    ? (شرط == ١) {{
        خل := ⟪{haa_3}⟫;
    }} : {{
        خل := ⟪{haa_32}⟫;
    }}
    ⊢ خل;
    """
    rep_unsafe = SemanticAnalyzer().analyze(parse_hcell(unsafe_branch_src))
    assert rep_unsafe.guards_total == 1
    assert rep_unsafe.guards_discharged == 0
    assert rep_unsafe.guards_mandatory_runtime == 1

    loop_src = """
    مسار := هـ;
    عداد := ٠;
    ↻ (عداد < ٥) {
        مسار := مسار + هـ;
        عداد := عداد + ١;
    }
    ⊢ مسار;
    """
    rep_loop = SemanticAnalyzer().analyze(parse_hcell(loop_src))
    assert rep_loop.guards_total == 1
    assert rep_loop.guards_discharged == 0
    assert rep_loop.guards_mandatory_runtime == 1


def test_parser_reports_precise_location_on_unknown_cell() -> None:
    with pytest.raises(HCellParseError, match="L1:3: Undefined Hijaiyyah cell"):
        parse_hcell("↦ مجهول;")
