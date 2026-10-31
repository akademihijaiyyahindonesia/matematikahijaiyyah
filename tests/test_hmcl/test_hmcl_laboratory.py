"""Comprehensive Test Suite for HMCL (COSMICTERA FUTURE COMPUTING CHARTER Sections A–I)."""

from __future__ import annotations

from hijaiyyah.hmcl import (
    HMCL_VERSION,
    build_ecosystem_asset_registry,
    predict_alt_a1_rtl_cycles,
    predict_dynamic_loop_hvm_steps,
    predict_dynamic_loop_rtl_cycles,
    run_multilevel_hmcl_simulation,
    run_nui_8axis_benchmark,
    simulate_alt_a1_hardware_sticky_guard,
    simulate_alt_a2_hdot_20bit,
    verify_all_ecosystem_assets,
)


def test_charter_section_b_formal_asset_registry_and_verification() -> None:
    """Charter Section B: Verify all formal mathematical & system assets in the ecosystem."""
    assert HMCL_VERSION == "0.1.0-exp"
    assets = build_ecosystem_asset_registry()
    assert len(assets) == 6
    summary = verify_all_ecosystem_assets()
    assert summary.all_verified is True
    assert summary.master_table_letters == 28
    assert summary.theorems_total == summary.theorems_passed == 13
    assert summary.rtl_wide_adders_verified is True
    assert summary.hstar_laws_verified is True
    assert summary.native_letter_opcodes_count == 28


def test_charter_sections_c_d_f_multilevel_simulation_and_zero_error_calibration() -> None:
    """Charter Sections C, D, & F: Verify the 7-level simulation model, zero-error
    microarchitectural cycle calibration across N in (1, 4, 16, 64, 127, 128, 256),
    and Architectural Alternatives A1, A2, and A3."""
    sim = run_multilevel_hmcl_simulation(
        loop_sweep=(1, 4, 16, 64, 127, 128, 256),
        run_rtl=True,
    )
    assert sim.continuous_improvement_cycle_verified is True
    assert len(sim.level4_microarch_calibration) == 7
    for pt in sim.level4_microarch_calibration:
        assert pt.hvm_error == 0, f"HVM prediction error at N={pt.n_target}: {pt.hvm_error}"
        assert pt.rtl_error == 0, f"RTL prediction error at N={pt.n_target}: {pt.rtl_error}"
        assert pt.observed_flag_g == pt.expected_flag_g
        assert pt.three_way_parity is True

    # Verify exact calibrated predictions at boundary points
    assert predict_dynamic_loop_hvm_steps(127) == 3829
    assert predict_dynamic_loop_rtl_cycles(127) == 4215
    assert predict_dynamic_loop_rtl_cycles(128) == 4248
    assert predict_dynamic_loop_rtl_cycles(256) == 8472
    assert predict_alt_a1_rtl_cycles(256) == 3846

    # Verify Architectural Alternatives A1, A2, A3
    alts = {a.alternative_id: a for a in sim.alternatives}
    assert set(alts) == {
        "ALT_A1_HW_STICKY_PREFIX_AND_HSTAR",
        "ALT_A2_NATIVE_OP_HDOT_20BIT",
        "ALT_A3_STREAMING_SDIO_4B_PRIME",
    }
    assert alts["ALT_A1_HW_STICKY_PREFIX_AND_HSTAR"].safety_invariant_preserved is True
    assert alts["ALT_A1_HW_STICKY_PREFIX_AND_HSTAR"].compute_cycle_speedup_x == 2.20
    assert alts["ALT_A2_NATIVE_OP_HDOT_20BIT"].safety_invariant_preserved is True
    assert alts["ALT_A2_NATIVE_OP_HDOT_20BIT"].alternative_compute_cycles == 9


def test_architectural_alternative_a1_18lane_sticky_and_a2_hdot_exactness() -> None:
    """Verify that:
    1. Alternative A1 (18-lane sticky carry-out + coupled H*) accepts 127×Kaf and 255×Alif,
       and rejects 128×Kaf, 256×Kaf, AND 256×Alif (where Theta_hat=0 and H*=0).
    2. Alternative A2 (20-bit OP_HDOT) matches exact inner product even when a_j + b_j > 255
       (where 8-bit polarization wraps modulo 256)."""
    assert simulate_alt_a1_hardware_sticky_guard(["ك"] * 127)["a1_guard_pass"] is True
    assert simulate_alt_a1_hardware_sticky_guard(["ك"] * 128)["a1_guard_pass"] is False
    assert simulate_alt_a1_hardware_sticky_guard(["ك"] * 256)["a1_guard_pass"] is False
    assert simulate_alt_a1_hardware_sticky_guard(["ا"] * 255)["a1_guard_pass"] is True
    a256 = simulate_alt_a1_hardware_sticky_guard(["ا"] * 256)
    assert a256["g1_g4_t1_t2_only"] is True
    assert a256["sticky_ovf"] is True
    assert a256["first_carry_step"] == 256
    assert a256["a1_guard_pass"] is False

    # High-component vectors where a_0 + b_0 = 200 + 100 = 300 > 255:
    vec_a = [200] + [0] * 17
    vec_b = [100] + [0] * 17
    dot_sim = simulate_alt_a2_hdot_20bit(vec_a, vec_b)
    assert dot_sim["exact_dot"] == 20000
    assert dot_sim["a2_dot_20bit"] == 20000
    assert dot_sim["a2_matches_exact"] is True
    assert dot_sim["polarization_matches_exact"] is False


def test_charter_sections_e_and_i_nui_8axis_benchmark_and_scientific_qa() -> None:
    """Charter Sections E & I: Verify all 8 operational NUI benchmark axes and
    all 8 scientific questions."""
    rep = run_nui_8axis_benchmark(run_rtl=True)
    assert rep.all_axes_passed is True
    assert rep.overall_accuracy_pct == 100.0
    assert len(rep.axes) == 8
    for ax in rep.axes:
        assert ax.passed is True, f"NUI Axis {ax.axis_id} failed: {ax.reproducible_evidence}"
    assert len(rep.feature_comparisons) >= 2
    assert len(rep.scientific_qa) == 8
