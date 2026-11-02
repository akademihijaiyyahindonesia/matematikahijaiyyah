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
from hijaiyyah.hmcl.multilevel_sim import predict_alt_a1_hvm_steps


def test_charter_section_b_formal_asset_registry_and_verification() -> None:
    """Charter Section B: Verify all formal mathematical & system assets in the ecosystem,
    including the Paket 8 three-profile RTL bench (`rtl/tb/tb_hmcl_rtl_alternatives.v`)."""
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

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

    if shutil.which("iverilog") is not None and shutil.which("vvp") is not None:
        root_dir = Path(__file__).resolve().parents[2]
        tb_file = root_dir / "rtl" / "tb" / "tb_hmcl_rtl_alternatives.v"
        rtl_sources = [
            str(tb_file),
            *[str(p) for p in sorted((root_dir / "rtl").glob("hcpu_*.v"))],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            vvp_out = Path(tmpdir) / "tb_hmcl_rtl_alternatives.vvp"
            subprocess.run(
                [
                    "iverilog",
                    "-g2012",
                    "-I",
                    str(root_dir / "rtl"),
                    "-o",
                    str(vvp_out),
                    *rtl_sources,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            run_res = subprocess.run(
                ["vvp", str(vvp_out)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert "31 PASS, 0 FAIL" in run_res.stdout


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
    assert predict_alt_a1_hvm_steps(127) == 1527
    assert predict_alt_a1_hvm_steps(128) == 1539
    assert predict_alt_a1_hvm_steps(256) == 3075
    assert predict_alt_a1_rtl_cycles(127) == 1913
    assert predict_alt_a1_rtl_cycles(128) == 1928
    assert predict_alt_a1_rtl_cycles(256) == 3848

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
    assert "2,788 LUTs" in alts["ALT_A2_NATIVE_OP_HDOT_20BIT"].hardware_cost_delta
    assert "14x MULT9X9" in alts["ALT_A2_NATIVE_OP_HDOT_20BIT"].hardware_cost_delta
    assert sim.level7_physical_summary["codex_alu_profile0_asic_generic_cells"] == 9362
    assert sim.level7_physical_summary["codex_alu_gowin_nodsp_luts"] == 2788
    assert sim.level7_physical_summary["codex_alu_gowin_nodsp_alus"] == 726
    assert sim.level7_physical_summary["codex_alu_gowin_nodsp_sites"] == 3514
    assert sim.level7_physical_summary["codex_alu_gowin_dsp_luts"] == 1322
    assert sim.level7_physical_summary["codex_alu_gowin_dsp_mult9x9"] == 14
    assert sim.level7_physical_summary["hcpu_gowin_top_nodsp_sites"] == 15063
    assert sim.level7_physical_summary["hcpu_gowin_top_dsp_sites"] == 12612
    assert sim.level7_physical_summary["seven_module_generic_cells_paket8"] == 44358
    assert alts["ALT_A3_STREAMING_SDIO_4B_PRIME"].safety_invariant_preserved is True
    assert alts["ALT_A3_STREAMING_SDIO_4B_PRIME"].alternative_compute_cycles == 17681
    assert alts["ALT_A3_STREAMING_SDIO_4B_PRIME"].compute_cycle_speedup_x == 1.74


def test_architectural_alternative_a1_18lane_sticky_and_a2_hdot_exactness() -> None:
    """Verify that:
    1. Alternative A1 (18-lane sticky carry-out + coupled H*) accepts 127×Kaf and 255×Alif,
       and rejects 128×Kaf, 256×Kaf, AND 256×Alif (where Theta_hat=0 and H*=0), with
       zero cycle prediction error across all N in (1, 4, 16, 64, 127, 128, 256).
    2. Alternative A2 (20-bit OP_HDOT) matches exact inner product across extreme per-lane
       patterns (0x00*0xFF, 0x80*0xFF unsigned, 14*255*255 = 910,350, lanes 14..17)."""
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

    # Extreme per-lane and unsigned byte tests on HVM + RTL
    from hijaiyyah.cells.hpg1_bridge import compile_and_execute_cells
    from hijaiyyah.core.master_table import MasterTable
    from hijaiyyah.hisa.assembler import assemble
    from hijaiyyah.hisa.machine import HISAMachine

    # Verify A1 analytical cycle equations against measured RTL across all 7 sweep points
    for n_val in (1, 4, 16, 64, 127, 128, 256):
        kaf_src = (
            "مسار := ك;\nحرف := ك;\nعداد := ١;\n"
            f"↻ (عداد < {n_val}) {{ مسار := مسار + حرف; عداد := عداد + ١; }}\n"
            "⊢ مسار;\n↦ Θ̂(مسار);\n↦ مسار[٧];\n↦ H*(مسار);\n"
        )
        res_a1 = compile_and_execute_cells(
            kaf_src,
            run_rtl=True,
            use_hw_sticky_guard=True,
        )
        assert res_a1.hw_rtl_parity is True
        assert res_a1.hvm_compute_steps == predict_alt_a1_hvm_steps(n_val)
        if res_a1.rtl_measurement is not None:
            assert res_a1.rtl_measurement.compute_cycles == predict_alt_a1_rtl_cycles(n_val)
            assert (res_a1.rtl_measurement.flags & 0x01) == (1 if n_val <= 127 else 0)

    alif256_src = (
        "مسار := ا;\nحرف := ا;\nعداد := ١;\n"
        "↻ (عداد < 256) { مسار := مسار + حرف; عداد := عداد + ١; }\n"
        "⊢ مسار;\n↦ مسار[٤];\n"
    )
    res_a1_alif256 = compile_and_execute_cells(
        alif256_src,
        run_rtl=True,
        use_hw_sticky_guard=True,
    )
    if res_a1_alif256.rtl_measurement is not None:
        assert (res_a1_alif256.rtl_measurement.flags & 0x01) == 0

    res_a2_dot = compile_and_execute_cells(
        "↦ ⟨ب, م⟩;\n",
        run_rtl=True,
        run_rtl_loader=True,
        use_native_hdot=True,
    )
    assert len(res_a2_dot.compiled.compute_only_words) == 4
    assert res_a2_dot.verify_4b_prime_ok is True
    assert res_a2_dot.verify_4b_prime_reason == "loaded"
    assert res_a2_dot.three_way_parity is True
    assert res_a2_dot.hw_rtl_parity is True
    assert res_a2_dot.eval_result.outputs == [8]
    if res_a2_dot.rtl_measurement is not None:
        assert res_a2_dot.rtl_measurement.compute_cycles == 9
        assert res_a2_dot.rtl_measurement.printed_outputs == [8]
        assert res_a2_dot.rtl_measurement.rtl_4b_prime_verdict == {
            "DONE": 1,
            "ANSWER": 1,
            "ABSENT": 0,
        }

    # Verify HVM HDOT extreme unsigned lane cases (0x80 * 0xFF = 32640, 14 * 255 * 255 = 910350)
    mt = MasterTable()
    words = assemble("HDOT R3, H1, H2\nHALT\n")
    vm = HISAMachine(mt)
    vm.load_program(words)
    vm.regs.hreg[1] = [255] * 18
    vm.regs.hreg[2] = [255] * 18
    vm.run()
    assert vm.regs.gpr[3] == 910350

    vm2 = HISAMachine(mt)
    vm2.load_program(words)
    vm2.regs.hreg[1] = [0x80] + [0] * 13 + [0xFF] * 4
    vm2.regs.hreg[2] = [0xFF] + [0] * 13 + [0xFF] * 4
    vm2.run()
    assert vm2.regs.gpr[3] == 32640

    # Verify HISAMachine SDIO MMIO (0xFE0..0xFE6) parity with tb_hmcl_rtl_alternatives.v
    sd_words = assemble(
        "MOVI R12, 0\n"
        "MOVI R1, 1\n"
        "STORE R1, R12, 0xFE4\n"  # rewind SD_CONTROL
        "LOAD R2, R12, 0x100\n"
        "STORE R2, R12, 0xFE3\n"  # word 0: 0x04100005 (MOVI)
        "LOAD R2, R12, 0x101\n"
        "STORE R2, R12, 0xFE3\n"  # word 1: 0x4E312000 (HDOT 0x4E)
        "LOAD R3, R12, 0xFE5\n"   # SD_CSUM after 2 valid words
        "LOAD R4, R12, 0xFE6\n"   # SD_PRESCAN after 2 valid words (expect 0)
        "LOAD R2, R12, 0x102\n"
        "STORE R2, R12, 0xFE3\n"  # word 2: 0x08000000 (ERET -> forbidden!)
        "LOAD R5, R12, 0xFE6\n"   # SD_PRESCAN (expect 0x08010201)
        "MOVI R2, 0\n"
        "STORE R2, R12, 0xFE3\n"  # word 3: NOP
        "STORE R2, R12, 0xFE3\n"  # word 4: NOP
        "STORE R2, R12, 0xFE3\n"  # word 5: NOP
        "STORE R2, R12, 0xFE3\n"  # word 6: NOP
        "LOAD R2, R12, 0x103\n"
        "STORE R2, R12, 0xFE3\n"  # word 7: 0xFF000000 (HALT_ERR -> body_bad!)
        "LOAD R6, R12, 0xFE6\n"   # SD_PRESCAN (expect 0x08020203)
        "HALT\n"
    )
    vm_sd = HISAMachine(mt, hcheck_interval=0)
    vm_sd.load_program(sd_words)
    vm_sd.data_mem[0x100] = 0x04100005
    vm_sd.data_mem[0x101] = 0x4E312000
    vm_sd.data_mem[0x102] = 0x08000000
    vm_sd.data_mem[0x103] = 0xFF000000
    vm_sd.run()
    assert vm_sd.regs.gpr[3] == (0x04100005 + 0x4E312000) & 0xFFFFFFFF
    assert vm_sd.regs.gpr[4] == 0x00000000
    assert vm_sd.regs.gpr[5] == 0x08010201
    assert vm_sd.regs.gpr[6] == 0x08020203


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
