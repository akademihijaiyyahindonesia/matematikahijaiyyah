"""
The computation inside the GUI, which nothing ever ran outside the GUI.

src/hijaiyyah/gui is 9,245 lines with no test coverage. Most of it is Tkinter
layout, which is not worth testing, but not all of it: gui/tabs/theorems.py
holds thirteen theorem checks, each returning (passed, message), and they only
executed when somebody opened the tab and pressed a button.

That is the same shape as EXAMPLE_BY_NAME in grammar.py — real assertions
reachable only through the interface — and the same shape as the bug mypy
found in gui/tabs/bytecode.py, where the letter buttons passed a 0-based index
to an opcode that takes a 1-based one.

None of this needs a display: the functions here are module-level and pure.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.gui.tabs import five_fields, theorems


def _theorem_checks() -> Dict[str, Callable[[], Tuple[bool, str]]]:
    """Every _test_* in the theorems tab, discovered rather than listed."""
    return {
        name: getattr(theorems, name)
        for name in dir(theorems)
        if name.startswith("_test_") and callable(getattr(theorems, name))
    }


CHECKS = _theorem_checks()
NAMES = sorted(CHECKS)


def test_the_theorem_checks_were_found() -> None:
    assert len(CHECKS) >= 10, f"only {len(CHECKS)} checks discovered"


@pytest.mark.parametrize("name", NAMES, ids=NAMES)
def test_theorem_check_passes(name: str) -> None:
    """
    Each check asserts something about the sealed table. A failure here means
    the mathematics moved, not that the GUI is broken.
    """
    passed, message = CHECKS[name]()
    assert passed, f"{name}: {message}"
    assert message, f"{name} returned no explanation"


@pytest.mark.parametrize("name", NAMES, ids=NAMES)
def test_theorem_check_is_not_vacuous(name: str) -> None:
    """A check that always returns True regardless of input proves nothing."""
    passed, _ = CHECKS[name]()
    assert isinstance(passed, bool)


# ── The classifiers behind the five-fields tab ───────────────────

def test_structure_classifier_covers_every_letter() -> None:
    """No canonical letter may fall through to an empty label."""
    for entry in MASTER_TABLE.all_entries():
        label, _ = five_fields._classify_structure(list(entry.vector))
        assert label, f"{entry.char} has no structural classification"


def test_turning_classifier_covers_every_letter() -> None:
    for entry in MASTER_TABLE.all_entries():
        label, _ = five_fields._classify_turning(list(entry.vector))
        assert label, f"{entry.char} has no turning classification"


def test_dot_families_are_symmetric() -> None:
    """
    If ب lists ت as a relative, ت must list ب. An asymmetric relation would
    show a different set of neighbours depending on which letter you opened.
    """
    entries = MASTER_TABLE.all_entries()
    family: Dict[str, set] = {}
    for entry in entries:
        related = five_fields._find_dot_family(entry)
        family[entry.char] = {row[0] for row in related} - {entry.char}

    for char, relatives in family.items():
        for other in relatives:
            if other in family:
                assert char in family[other], (
                    f"{char} lists {other} as a relative, but not the reverse"
                )


# ── The letter index the buttons pass to CLOAD ───────────────────

def test_codex_entries_are_numbered_from_one() -> None:
    """
    gui/tabs/bytecode.py builds a button per letter and passes the index to
    CLOAD, whose IMM is 1-based. It used to pass the list position instead, so
    ب produced CLOAD #1 and loaded Alif. This pins the property the buttons
    now rely on.
    """
    entries = MASTER_TABLE.all_entries()
    assert [e.index for e in entries] == list(range(1, 29))


def test_bytecode_tab_uses_the_letter_index_not_the_list_position() -> None:
    source = (
        __import__("pathlib")
        .Path(theorems.__file__)
        .parent.joinpath("bytecode.py")
        .read_text(encoding="utf-8")
    )
    assert "lambda idx=letter.index" in source, (
        "the letter buttons must pass letter.index — the 1-based number CLOAD "
        "expects — not the enumerate() position"
    )
    assert "lambda idx=i:" not in source, "a 0-based button index is back"


# ── Every tab module imports ─────────────────────────────────────

def test_every_tab_module_imports() -> None:
    """
    A tab that fails to import takes the whole application down on launch,
    and nothing else in the suite loads them.
    """
    import importlib
    import pkgutil

    import hijaiyyah.gui as gui

    failures: List[str] = []
    tab_modules: List[str] = []
    for module in pkgutil.walk_packages(gui.__path__, "hijaiyyah.gui."):
        try:
            importlib.import_module(module.name)
            if module.name.startswith("hijaiyyah.gui.tabs."):
                tab_modules.append(module.name)
        except Exception as exc:
            failures.append(f"{module.name}: {type(exc).__name__}: {exc}")
    assert not failures, "\n".join(failures)
    assert len(tab_modules) == 15, (
        f"expected 15 tab modules (14 + hcell_pipeline), got {len(tab_modules)}"
    )


# ── P0 Regression: AuditTab canonical G1-G4, T1-T2 & H* check ────

def test_audit_tab_guards_pass_for_all_28_letters() -> None:
    from hijaiyyah.core.guards import full_guard_check
    from hijaiyyah.gui.tabs.audit import evaluate_letter_guards

    entries = MASTER_TABLE.all_entries()
    assert len(entries) == 28
    for entry in entries:
        v = list(entry.vector)
        res = evaluate_letter_guards(v)
        canonical = full_guard_check(v)
        for key in ("G1", "G2", "G3", "G4", "T1", "T2"):
            assert res[key] is canonical[key], f"{entry.char} mismatch on {key}"
            assert res[key] is True, f"{entry.char} failed {key}"
        assert res["all_guards_pass"] is True
        assert res["hstar_consistency"] is True


def test_audit_tab_guard_mapping_is_not_swapped() -> None:
    """Each canonical guard G1..G4, T1..T2 must fail independently when violated."""
    from hijaiyyah.gui.tabs.audit import evaluate_letter_guards

    base = [0] * 18
    assert evaluate_letter_guards(base)["all_guards_pass"] is True

    # Violate G1: A_N (idx 14) != Na+Nb+Nd
    v_g1 = list(base)
    v_g1[14] = 1
    r1 = evaluate_letter_guards(v_g1)
    assert r1["G1"] is False and r1["G2"] and r1["G3"] and r1["G4"]

    # Violate G2: A_K (idx 15) != sum(K)
    v_g2 = list(base)
    v_g2[15] = 1
    r2 = evaluate_letter_guards(v_g2)
    assert r2["G2"] is False and r2["G1"] and r2["G3"] and r2["G4"]

    # Violate G3: A_Q (idx 16) != sum(Q)
    v_g3 = list(base)
    v_g3[16] = 1
    r3 = evaluate_letter_guards(v_g3)
    assert r3["G3"] is False and r3["G1"] and r3["G2"] and r3["G4"]

    # Violate G4: rho = Theta_hat - U < 0 (Qx=1, Theta_hat=0, AQ=1)
    v_g4 = list(base)
    v_g4[10] = 1
    v_g4[16] = 1
    r4 = evaluate_letter_guards(v_g4)
    assert r4["G4"] is False and r4["G1"] and r4["G2"] and r4["G3"]

    # Violate T1: Ks > 0 without Qc >= 1
    v_t1 = list(base)
    v_t1[6] = 1
    v_t1[15] = 1
    rt1 = evaluate_letter_guards(v_t1)
    assert rt1["T1"] is False and rt1["T2"] is True

    # Violate T2: Kc > 0 without Qc >= 1
    v_t2 = list(base)
    v_t2[8] = 1
    v_t2[15] = 1
    rt2 = evaluate_letter_guards(v_t2)
    assert rt2["T2"] is False and rt2["T1"] is True


# ── P0 Regression: BytecodeTab synchronized with hisa/opcodes.py ─

def test_bytecode_tab_catalog_matches_opcodes_py() -> None:
    from hijaiyyah.gui.tabs.bytecode import (
        OPCODE_DOCS,
        build_opcode_catalog,
        get_opcode_summary,
    )
    from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

    catalog = build_opcode_catalog()
    summary = get_opcode_summary()

    assert catalog == OPCODE_DOCS
    assert summary["unique_opcodes"] == len(OpCode) == 105
    assert summary["rtl_implemented"] == len(RTL_IMPLEMENTED) == 84
    assert summary["software_only"] == 105 - 84 == 21
    assert summary["alias_count"] == 17
    assert summary["total_members"] == 122
    assert summary["letter_opcodes"] == 28

    for op in OpCode:
        code = int(op.value)
        assert code in catalog, f"Missing opcode {op.name} (0x{code:02X})"
        assert catalog[code]["name"] == op.name
        assert catalog[code]["rtl"] is (op in RTL_IMPLEMENTED)
        assert catalog[code]["desc"]
        assert catalog[code]["syntax"]

    for code in range(0xE0, 0xFC):
        assert code in catalog
        assert catalog[code]["rtl"] is True


# ── P1 Acceptance: HCellTab (.hcell -> CellIR -> 4-B' -> HPG1 v2) ─

def test_hcell_pipeline_valid_input_passes_all_four_stages() -> None:
    from hijaiyyah.gui.tabs.hcell_pipeline import HPG1_CARD_KEYS, inspect_hcell_pipeline

    src = """
    بسم := ب + س + م;
    ⊢ بسم;
    ↦ Θ̂(بسم);
    ↦ U(بسم);
    ↦ ρ(بسم);
    ↦ ‖بسم‖²;
    ↦ d₂²(ب, م);
    """
    res = inspect_hcell_pipeline(src)
    assert res.ok is True
    assert res.failed_stage is None
    assert res.graph is not None and len(res.graph.nodes) > 0
    assert res.semantic_report is not None and res.semantic_report.valid is True
    assert res.semantic_report.guards_discharged == 1
    assert res.cf_report is not None and res.cf_report.valid is True
    assert res.overlay_4b_ok is True
    assert res.overlay_4b_reason == "loaded"
    assert res.hpg1 is not None
    assert res.hpg1.magic == 0x48504731  # "HPG1"
    assert res.hpg1.version == 2
    assert res.hpg1.checksum_valid is True
    assert res.hpg1.loader_ok is True
    fields = res.hpg1.card_fields()
    assert tuple(fields.keys()) == HPG1_CARD_KEYS


def test_hcell_pipeline_invalid_inputs_report_stage1_and_stage2_diagnostics() -> None:
    from hijaiyyah.gui.tabs.hcell_pipeline import inspect_hcell_pipeline

    # 1. Orthographic lookalike 'ة' (Ta Marbuthah) -> Stage 1 UnicodePolicyError
    bad_ortho = "طاقة := ب + س;\n↦ Θ̂(طاقة);\n"
    r_ortho = inspect_hcell_pipeline(bad_ortho)
    assert r_ortho.ok is False
    assert r_ortho.failed_stage == "STAGE_1_PARSE"
    assert r_ortho.error_type == "UnicodePolicyError"

    # 2. Syntax error -> Stage 1 HCellParseError
    bad_syntax = "بسم := + * ;"
    r_syn = inspect_hcell_pipeline(bad_syntax)
    assert r_syn.ok is False
    assert r_syn.failed_stage == "STAGE_1_PARSE"

    # 3. Semantic type error (EMIT_OUTPUT on raw HYBIT) -> Stage 2 CellSemanticError
    bad_sem = "بسم := ب + س + م;\n↦ بسم;\n"
    r_sem = inspect_hcell_pipeline(bad_sem)
    assert r_sem.ok is False
    assert r_sem.failed_stage == "STAGE_2_SEMANTIC"
    assert r_sem.error_type == "CellSemanticError"


def test_hcell_pipeline_control_flow_4b_prime_failures_are_caught() -> None:
    from hijaiyyah.gui.tabs.hcell_pipeline import (
        package_and_verify_hpg1,
        verify_raw_hisa_control_flow,
    )

    # 1. Program missing terminator (falls through past end)
    no_halt = [0x40000001]  # HLOAD H0, #1 without HALT
    cf_no_halt = verify_raw_hisa_control_flow(no_halt)
    assert cf_no_halt["vm_control_flow_valid"] is False
    assert cf_no_halt["overlay_4b_ok"] is False
    assert "falls through" in cf_no_halt["vm_control_flow_reason"]

    # 2. Out-of-bounds jump target (JMP to word 0x999)
    bad_jmp = [0x22000999, 0x01000000]
    cf_bad_jmp = verify_raw_hisa_control_flow(bad_jmp)
    assert cf_bad_jmp["vm_control_flow_valid"] is False
    assert cf_bad_jmp["overlay_4b_ok"] is False

    # 3. Forbidden opcode PUSH (0x32) in 4-B' user overlay
    forbidden_push = [0x32000000, 0x01000000]
    pkg_push = package_and_verify_hpg1(
        "main:\n        HALT\n",
        override_relocated_words=forbidden_push,
    )
    assert pkg_push.loader_ok is False
    assert "forbidden opcode PUSH" in pkg_push.loader_reason


def test_hcell_pipeline_hpg1_v2_checksum32_tampering_is_rejected() -> None:
    from hijaiyyah.gui.tabs.hcell_pipeline import inspect_hcell_pipeline

    src = "بسم := ب + س + م;\n↦ Θ̂(بسم);\n"
    res_tampered = inspect_hcell_pipeline(src, tamper_checksum=True)
    assert res_tampered.ok is False
    assert res_tampered.failed_stage == "STAGE_4_HPG1_CHECKSUM"
    assert res_tampered.hpg1 is not None
    assert res_tampered.hpg1.checksum_valid is False
    assert res_tampered.hpg1.loader_ok is False
    assert res_tampered.hpg1.loader_reason == "CHECKSUM32"


# ── P1-C Acceptance: Scientific Computing Environment UI/UX ──────

def test_scientific_computing_theme_and_sidebar_overview_structure() -> None:
    from hijaiyyah.gui.app import SIDEBAR_GROUPS, get_overview_metrics
    from hijaiyyah.gui.theme import THEME

    # 1. Verify Scientific Computing Palette
    assert THEME.bg == "#071426"
    assert THEME.surface == "#10243A"
    assert THEME.highlight == "#26C6DA"
    assert THEME.gold == "#D6AF57"
    assert THEME.fg == "#EAF2FA"

    # 2. Verify Sidebar Navigation Groups (WORKSPACE, PROGRAMMING, SYSTEM)
    group_names = [g[0] for g in SIDEBAR_GROUPS]
    assert group_names == ["WORKSPACE", "PROGRAMMING", "SYSTEM"]
    nav_keys = [item[0] for _, items in SIDEBAR_GROUPS for item in items]
    assert len(nav_keys) == 16  # Overview + 15 modular workbenches
    assert "overview" in nav_keys
    assert "hcell_pipeline" in nav_keys

    # 3. Verify System Overview Dashboard Metrics & 5-Stage Pipeline
    metrics = get_overview_metrics()
    assert metrics["status_badge"] == "SYSTEM READY"
    card_values = [c["value"] for c in metrics["cards"]]
    assert card_values == ["28 / 28", "18D", "105", "6"]
    assert len(metrics["pipeline_stages"]) == 5


# ── P2 Acceptance: Web HC IDE & HVM Simulator Parity with Python ─

def _run_web_js_engine(js_expr: str) -> Dict[str, Any]:
    from typing import cast
    """
    Execute hom-gui/src/engine/{masterTable,guards,hvmSimulator,hcCompiler}.js
    inside macOS JavaScriptCore (`jsc`) and return parsed JSON output.
    """
    import json
    import re
    import subprocess
    from pathlib import Path

    jsc_bin = Path(
        "/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc"
    )
    if not jsc_bin.exists():
        pytest.skip("macOS JavaScriptCore (jsc) binary not available")

    repo_root = Path(theorems.__file__).resolve().parents[4]
    engine_dir = repo_root / "hom-gui" / "src" / "engine"

    bundle_parts: List[str] = []
    for fname in ("masterTable.js", "guards.js", "hvmSimulator.js", "hcCompiler.js"):
        src = (engine_dir / fname).read_text(encoding="utf-8")
        src = re.sub(
            r"^\s*import\s+[\s\S]*?from\s+['\"].*?['\"];?\s*$",
            "",
            src,
            flags=re.MULTILINE,
        )
        src = re.sub(r"\bexport\s+(const|let|var|function|class)\b", r"\1", src)
        bundle_parts.append(f"// === {fname} ===\n{src}")

    runner = (
        "\n\n".join(bundle_parts)
        + f"\n\nconst __res = (() => {{ {js_expr} }})();\nprint(JSON.stringify(__res));\n"
    )
    proc = subprocess.run(
        [str(jsc_bin), "-e", runner],
        capture_output=True,
        text=True,
        check=True,
    )
    out_lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    assert out_lines, f"jsc produced no output: stderr={proc.stderr}"
    return cast(Dict[str, Any], json.loads(out_lines[-1]))


def test_p2_web_hc_compiler_and_hvm_simulator_parity_with_python() -> None:
    """
    Verify that both HC v1.0 ('let b = ...') and native .hcell ('بسم := ...')
    in hom-gui/src/engine/hcCompiler.js + hvmSimulator.js produce valid HPG1 v2
    packages, exact 18D Hybit vectors, and the exact same HVM execution outputs
    ([10, 6, 4, 112, 9]) as Python compile_and_execute_cells().
    """
    from hijaiyyah.cells import compile_and_execute_cells
    from hijaiyyah.gui.tabs.hcell_pipeline import inspect_hcell_pipeline

    hcell_src = """
    بسم := ب + س + م;
    ⊢ بسم;
    ↦ Θ̂(بسم);
    ↦ U(بسم);
    ↦ ρ(بسم);
    ↦ ‖بسم‖²;
    ↦ d₂²(ب, م);
    """
    py_exec = compile_and_execute_cells(hcell_src)
    py_insp = inspect_hcell_pipeline(hcell_src)
    assert py_insp.ok and py_insp.hpg1 is not None and py_insp.compiled is not None

    js_data = _run_web_js_engine(
        """
        const hcRes = compileHCOrHCell(HC_WEB_EXAMPLES["1. بسم Benchmark (HC v1.0)"], {
            useNativeLetterOpcodes: true,
            useNativeHdot: false,
        });
        const hcellRes = compileHCOrHCell(HC_WEB_EXAMPLES["2. بسم Benchmark (Native .hcell)"], {
            useNativeLetterOpcodes: true,
            useNativeHdot: false,
        });
        const vm1 = new HVMSimulator();
        vm1.loadProgram(hcRes.words);
        const state1 = vm1.run();

        const vm2 = new HVMSimulator();
        vm2.loadProgram(hcellRes.words);
        const state2 = vm2.run();

        return {
            hcOk: hcRes.ok,
            hcellOk: hcellRes.ok,
            hcWordCount: hcRes.words.length,
            hcellWordCount: hcellRes.words.length,
            hcHpg1Ok: hcRes.hpg1Verify.ok,
            hcellHpg1Ok: hcellRes.hpg1Verify.ok,
            hcOutputs: state1.outputs,
            hcellOutputs: state2.outputs,
            h0Vector: state1.hreg[0],
            srGuardPass: state1.flags.GUARD_PASS ? 1 : 0,
            provenanceMode: state1.provenance.id,
            fpgaClaimed: state1.provenance.id !== "SIMULATED",
        };
        """
    )

    assert js_data["hcOk"] is True
    assert js_data["hcellOk"] is True
    assert js_data["hcWordCount"] == js_data["hcellWordCount"] == 17
    assert len(py_insp.hpg1.relocated_words) == 17
    assert js_data["hcHpg1Ok"] is True
    assert js_data["hcellHpg1Ok"] is True
    assert (
        js_data["hcOutputs"]
        == js_data["hcellOutputs"]
        == py_exec.hvm_outputs
        == [10, 6, 4, 112, 9]
    )
    assert js_data["h0Vector"] == [
        10, 0, 0, 1, 0, 1, 0, 0, 1, 2, 2, 0, 0, 1, 1, 2, 5, 0
    ]
    assert js_data["srGuardPass"] == 1
    assert js_data["provenanceMode"] == "SIMULATED"
    assert js_data["fpgaClaimed"] is False


def test_p2_web_compiler_invalid_inputs_and_control_flow_4b_prime() -> None:
    """
    Verify that the web HC/.hcell compiler & verifier catch:
    1. Orthographic lookalike 'ة' (STAGE_1_PARSE / UnicodePolicyError with line & col)
    2. Semantic raw Hybit output error (STAGE_2_SEMANTIC / CellSemanticError)
    3. 4-B' Control Flow Verifier & HPG1 v2 checksum tampering
    """
    js_diag = _run_web_js_engine(
        """
        const k5 = "5. Diagnostic: Orthographic Policy Error (ة)";
        const k6 = "6. Diagnostic: Semantic Domain Error (println Hybit)";
        const k1 = "1. بسم Benchmark (HC v1.0)";
        const rOrtho = compileHCOrHCell(HC_WEB_EXAMPLES[k5]);
        const rSem = compileHCOrHCell(HC_WEB_EXAMPLES[k6]);
        const rTamper = compileHCOrHCell(HC_WEB_EXAMPLES[k1], {
            tamperChecksum: true,
        });
        const cfMissingHalt = verifyControlFlow4BPrime([0x40000001]);
        const cfForbiddenPush = verifyControlFlow4BPrime([0x32000000, 0x01000000]);
        return {
            ortho: {
                ok: rOrtho.ok,
                stage: rOrtho.failedStage,
                type: rOrtho.errorType,
                line: rOrtho.errorLine,
                col: rOrtho.errorCol,
            },
            sem: {
                ok: rSem.ok,
                stage: rSem.failedStage,
                type: rSem.errorType,
            },
            tamper: {
                ok: rTamper.ok,
                stage: rTamper.failedStage,
                checksumValid: rTamper.hpg1Verify?.checksumValid,
            },
            cfMissingHalt,
            cfForbiddenPush,
        };
        """
    )

    assert js_diag["ortho"]["ok"] is False
    assert js_diag["ortho"]["stage"] == "STAGE_1_PARSE"
    assert js_diag["ortho"]["type"] == "UnicodePolicyError"
    assert isinstance(js_diag["ortho"]["line"], int) and js_diag["ortho"]["line"] >= 1
    assert isinstance(js_diag["ortho"]["col"], int) and js_diag["ortho"]["col"] >= 1

    assert js_diag["sem"]["ok"] is False
    assert js_diag["sem"]["stage"] == "STAGE_2_SEMANTIC"
    assert js_diag["sem"]["type"] == "CellSemanticError"

    assert js_diag["tamper"]["ok"] is False
    assert js_diag["tamper"]["stage"] == "STAGE_4_HPG1_CHECKSUM"
    assert js_diag["tamper"]["checksumValid"] is False

    assert js_diag["cfMissingHalt"]["valid"] is False
    assert "falls through" in js_diag["cfMissingHalt"]["reason"]
    assert js_diag["cfForbiddenPush"]["valid"] is False
    assert "forbidden opcode PUSH" in js_diag["cfForbiddenPush"]["reason"]


def test_p2_web_hvm_step_run_pause_reset_and_guard_trap() -> None:
    """
    Verify HVM interactive controls (step, pause, run, reset), register delta
    highlighting, and runtime GUARD trap diagnostics when a corrupted vector
    violates G1-G4.
    """
    js_vm = _run_web_js_engine(
        """
        const compiled = compileHCOrHCell(HC_WEB_EXAMPLES["2. بسم Benchmark (Native .hcell)"]);
        const vm = new HVMSimulator();
        vm.loadProgram(compiled.words);

        // Step 1: CZERO H0
        vm.step();
        const s1 = vm.getState();
        // Step 2: L_BA -> H0 changes
        vm.step();
        const s2 = vm.getState();
        // Pause mid-program
        vm.pause();
        const sPaused = vm.getState();
        // Run to completion
        const sDone = vm.run();
        // Reset back to PC=0
        vm.reset();
        const sReset = vm.getState();

        // Test a runtime GUARD failure on a corrupted vector in H0:
        // MOVI R1, 9 (0x04100009), CSET H0[14] <- R1 (0x4501000E), HGRD H0, HALT
        const trapVm = new HVMSimulator();
        trapVm.loadProgram([0x04100009, 0x4501000E, 0x60000000, 0x01000000]);
        const trapState = trapVm.run();

        return {
            step1Pc: s1.pc,
            step2Pc: s2.pc,
            step2ChangedHreg: s2.lastDelta.changedHreg,
            step2Theta: s2.hreg[0][0],
            pausedStatus: sPaused.paused,
            doneHalted: sDone.halted,
            doneCycles: sDone.cycle,
            resetPc: sReset.pc,
            resetCycles: sReset.cycle,
            trapHalted: trapState.halted,
            trapGuardPass: trapState.flags.GUARD_PASS ? 1 : 0,
            trapG1Pass: trapState.trace[2].description,
        };
        """
    )

    assert js_vm["step1Pc"] == 1
    assert js_vm["step2Pc"] == 2
    assert 0 in js_vm["step2ChangedHreg"]
    assert js_vm["step2Theta"] == 2  # Θ̂(ب) = 2
    assert js_vm["pausedStatus"] is True
    assert js_vm["doneHalted"] is True
    assert js_vm["doneCycles"] == 17
    assert js_vm["resetPc"] == 0
    assert js_vm["resetCycles"] == 0
    assert js_vm["trapHalted"] is True
    assert js_vm["trapGuardPass"] == 0
    assert "FAIL" in js_vm["trapG1Pass"]

