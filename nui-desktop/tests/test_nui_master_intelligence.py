"""Mandatory Acceptance Tests (Tests 1–10) for CosmicTera NUI Master Intelligence & Technology Control Architecture.

Verifies Sections A through H of the Master Intelligence Mandate end-to-end:
1. Test 1 — Local LLM Asset Test (Real inventory, uninstalled isolation, 9-dimension benchmark, dynamic model selection)
2. Test 2 — Multi-Model Orchestration Test (4-stage pipeline: Planner -> Specialist -> Reviewer -> Validator)
3. Test 3 — General Intelligence Test (General conversation, coding, and system architecture without irrelevant L0 fact injection)
4. Test 4 — CosmicTera Technology Understanding Test (Full 15-technology stack mapping + Repository Intelligence Engine)
5. Test 5 — Real Software Execution Test (Write code, compile/assemble H-ISA & USR, run pytest, verify real outputs)
6. Test 6 — Debugging & Repair Test (Error-to-source traceback parser + 11-stage Autonomous Engineering Loop with self-repair)
7. Test 7 — CosmicTera System Control Test (Inspect & run CosmicTera subsystems with measured statuses)
8. Test 8 — Hardware / FPGA Workflow Test (OSS CAD Suite toolchain, bitstream SHA-256, board probe, and simulation separating SIMULATED / BUILD_ARTIFACT / MEASURED / LIVE_PHYSICAL)
9. Test 9 — Permission & Security Test (All 7 permission modes including READ_ONLY + Immutable Core Protection blocking unauthorized core/H-ISA/RTL edits)
10. Test 10 — Self-Learning & Engineering Memory Test (4 epistemic states VALIDATED / CANDIDATE / REJECTED / HISTORICAL + 12 Control Center Panels)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = NUI_DESKTOP_ROOT.parent
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.master_control import (
    AutonomousEngineeringLoop,
    CAPABILITY_DIMENSIONS,
    HARDWARE_EVIDENCE_CLASSES,
    MEASURED_SUBSYSTEM_STATUSES,
    MEMORY_EPISTEMIC_STATES,
    check_immutable_core_path,
)
from backend.server import NUILocalServiceApp


@pytest.fixture(scope="module")
def master_app(tmp_path_factory: pytest.TempPathFactory) -> NUILocalServiceApp:
    db_dir = tmp_path_factory.mktemp("nui_master_control")
    app = NUILocalServiceApp(db_path=db_dir / "nui_master_test.db", use_os_keychain=False)
    app.storage.set_setting("active_provider", "local_ollama")
    return app


def test_01_local_llm_asset_registry_and_9d_capabilities(master_app: NUILocalServiceApp) -> None:
    """Test 1 — Local LLM Asset Test:
    - Detects installed local models via Ollama (`qwen3:4b-instruct-2507-q4_K_M`, `qwen3-coder:30b`, `hermes3:8b`, `santri-ai-8b:latest`, `santri-ai-kecil:latest`)
    - Never lists uninstalled models (`qwen3.8:27b`) as active assets
    - Evaluates empirical 9-dimension capabilities and selects optimal model per task
    """
    code, inv = master_app.dispatch_request("GET", "/api/master/llm-inventory")
    assert code == 200
    assert inv["ollama_daemon_reachable"] is True

    active_ids = set(inv["active_model_ids"])
    expected_installed = {
        "qwen3:4b-instruct-2507-q4_K_M",
        "qwen3-coder:30b",
        "hermes3:8b",
        "santri-ai-8b:latest",
        "santri-ai-kecil:latest",
        "cosmictera-nui-native-v1.4",
    }
    assert expected_installed.issubset(active_ids)

    # Uninstalled models must NEVER appear in active_assets
    uninstalled_ids = {u["model_id"] for u in inv["uninstalled_catalog"]}
    for u_id in uninstalled_ids:
        assert u_id not in active_ids

    # Check pull readiness requires explicit user approval
    code_pull, pull_check = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {"op": "check_pull_readiness", "model_id": "qwen3.8:27b", "user_approved": False},
    )
    assert code_pull == 200
    assert pull_check["allowed_to_pull"] is False
    assert pull_check["status"] == "WAITING_FOR_USER_APPROVAL"

    # Run live 9-dimension empirical benchmark on fast interactive local model
    code_bmk, bmk = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "benchmark_model",
            "model_id": "qwen3:4b-instruct-2507-q4_K_M",
            "run_live_probe": True,
        },
    )
    assert code_bmk == 200
    assert bmk["status"] == "VERIFIED"
    assert bmk["http_status"] == 200
    assert bmk["latency_ms"] > 0
    assert set(bmk["scores"].keys()) == set(CAPABILITY_DIMENSIONS)
    assert all(0.75 <= float(v) <= 1.0 for v in bmk["scores"].values())

    # Dynamic model selection for coding vs deterministic math
    _, route_coding = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "select_optimal_model",
            "prompt": "Tulis kode Python dan lakukan code review arsitektur compiler",
            "require_heavy_specialist": True,
        },
    )
    assert route_coding["selected_model"] == "qwen3-coder:30b"

    _, route_math = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {"op": "select_optimal_model", "prompt": "Jalankan MOVI R1, 42 di H-ISA"},
    )
    assert route_math["selected_model"] == "cosmictera-nui-native-v1.4"


def test_02_multi_model_orchestration_pipeline(master_app: NUILocalServiceApp) -> None:
    """Test 2 — Multi-Model Orchestration Test:
    - Executes `Planner -> Specialist -> Reviewer -> Validator` pipeline
    - Verifies real local LLM generation, AST syntax validation, and epistemic check
    """
    code, res = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "multi_model_pipeline",
            "task_prompt": "Buat fungsi Python `def hitung_luas_persegi(sisi: float) -> float:` beserta contoh penggunaannya.",
            "prefer_fast": True,
            "verify_code_syntax": True,
        },
    )
    assert code == 200
    assert res["pipeline"] == "Planner -> Specialist -> Reviewer -> Validator"
    assert len(res["stages"]) == 4
    stage_names = [s["stage"] for s in res["stages"]]
    assert stage_names == ["1_PLANNER", "2_SPECIALIST", "3_REVIEWER", "4_VALIDATOR"]
    assert res["validation"]["python_syntax_valid"] is True
    assert res["validation"]["epistemic_hygiene_passed"] is True
    assert "def " in res["final_output"]
    assert res["ok"] is True


def test_03_general_intelligence_and_zero_irrelevant_facts(master_app: NUILocalServiceApp) -> None:
    """Test 3 — General Intelligence Test:
    - Answers general knowledge, software engineering, and architecture questions via real local LLM
    - Never injects unrelated L0 sealed facts (`burnin.no_watchdog_exists`)
    """
    prompts = [
        "Kamu bisa membantu pengembangan software?",
        "Jelaskan perbedaan arsitektur monolith dan microservices secara singkat.",
    ]
    for p in prompts:
        code, out = master_app.dispatch_request(
            "POST",
            "/api/chat",
            {
                "user_message": p,
                "provider": "local_ollama",
                "model": "qwen3:4b-instruct-2507-q4_K_M",
            },
        )
        assert code == 200
        reply = out["response_text"]
        assert "burnin.no_watchdog_exists" not in reply
        assert "burnin.tier1_clock_drift" not in reply
        assert len(reply) > 60
        proof = out["provider_response"]["data"]["ollama_runtime_proof"]
        assert proof["http_status"] == 200
        assert proof["stream_chunk_count"] >= 2


def test_04_cosmictera_technology_understanding_and_repo_intel(master_app: NUILocalServiceApp) -> None:
    """Test 4 — CosmicTera Technology Understanding Test:
    - Maps all 15 CosmicTera technologies from actual repository files
    - Verifies RepositoryIntelligenceEngine semantic search, dependency/call graph, test mapping, and cross-layer impact analysis
    """
    code_stack, stack = master_app.dispatch_request("GET", "/api/master/stack")
    assert code_stack == 200
    assert stack["total_technologies"] == 15
    assert all(t["status"] == "AVAILABLE" for t in stack["technologies"])
    assert stack["aggregate_counts"]["python_files_scanned"] >= 50
    assert stack["aggregate_counts"]["verilog_files_scanned"] >= 10

    code_graph, graph_info = master_app.dispatch_request("GET", "/api/master/repo-intel")
    assert code_graph == 200
    assert graph_info["repository_index"]["python_module_count"] >= 50
    assert graph_info["repository_dependency_graph"]["edge_count"] > 20
    assert graph_info["program_call_and_instance_graph"]["edge_count"] > 20

    # Semantic code search for HISAMachine
    _, search_res = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {"op": "semantic_search", "query": "HISAMachine compute_bsm", "limit": 5},
    )
    assert search_res["total_symbol_matches"] > 0
    top_names = {m["name"] for m in search_res["top_matches"]}
    assert "HISAMachine" in top_names or "compute_bsm" in top_names

    # Test-to-code mapping for H-ISA
    _, test_map = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {"op": "test_map", "target": "src/hijaiyyah/hisa/vm.py"},
    )
    assert test_map["test_count"] >= 1
    assert any("test_hisa" in tf for tf in test_map["test_files"])

    # Cross-layer impact analysis
    _, impact = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {"op": "impact_analysis", "path": "src/hijaiyyah/core/aggregator.py"},
    )
    assert impact["downstream_impact_count"] >= 1


def test_05_real_software_execution(master_app: NUILocalServiceApp, tmp_path: Path) -> None:
    """Test 5 — Real Software Execution Test:
    - Authorizes workspace folder, writes a Python module + pytest suite, runs USR/H-ISA compiler & VM, and executes pytest
    """
    proj_dir = tmp_path / "exec_workspace"
    proj_dir.mkdir(parents=True, exist_ok=True)
    master_app.storage.add_authorized_folder(proj_dir, label="Exec Workspace", access_mode="READ_WRITE")

    mod_file = proj_dir / "hybit_calc.py"
    test_file = proj_dir / "test_hybit_calc.py"

    # Write module via files.write tool
    w_mod = master_app.tools.execute_tool(
        "files.write",
        {
            "path": str(mod_file),
            "content": "def kalikan_dan_tambah(a: int, b: int, c: int) -> int:\n    return (a * b) + c\n",
        },
    )
    assert w_mod["ok"] is True

    w_test = master_app.tools.execute_tool(
        "files.write",
        {
            "path": str(test_file),
            "content": (
                "from hybit_calc import kalikan_dan_tambah\n\n"
                "def test_kalikan_dan_tambah():\n"
                "    assert kalikan_dan_tambah(7, 8, 4) == 60\n"
            ),
        },
    )
    assert w_test["ok"] is True

    # Run pytest via coding.run_tests
    run_res = master_app.tools.execute_tool(
        "coding.run_tests",
        {"path": str(proj_dir), "target": str(test_file)},
    )
    assert run_res["ok"] is True
    assert run_res["result"]["passed"] is True
    assert run_res["result"]["exit_code"] == 0

    # Also verify real H-ISA / USR compilation & execution via /api/subsystems/execute
    code_hisa, hisa_exec = master_app.dispatch_request(
        "POST",
        "/api/subsystems/execute",
        {
            "kind": "usr",
            "payload": {"source": "let x = 14 + 28\nprint(x)\n"},
        },
    )
    assert code_hisa == 200
    assert hisa_exec["halted"] is True
    assert hisa_exec["output"] == [42]


def test_06_debugging_and_autonomous_11stage_repair_loop(
    master_app: NUILocalServiceApp, tmp_path: Path
) -> None:
    """Test 6 — Debugging & Repair Test:
    - Traces an error stack trace to exact source file & line
    - Runs the 11-stage Autonomous Engineering Loop on a broken module:
      first patch intentionally still has an off-by-one bug, triggering Stage 9 Repair and Stage 10 Re-test until green
    """
    bug_dir = tmp_path / "debug_lab"
    bug_dir.mkdir(parents=True, exist_ok=True)
    target_py = bug_dir / " buggy_accumulator.py".replace(" ", "")
    test_py = bug_dir / "test_buggy_accumulator.py"

    # Initial broken implementation (subtracts instead of summing)
    target_py.write_text(
        "def total_angka(items: list[int]) -> int:\n"
        "    acc = 0\n"
        "    for x in items:\n"
        "        acc -= x\n"
        "    return acc\n",
        encoding="utf-8",
    )
    test_py.write_text(
        "from buggy_accumulator import total_angka\n\n"
        "def test_total_angka():\n"
        "    assert total_angka([10, 20, 30]) == 60\n"
        "    assert total_angka([]) == 0\n",
        encoding="utf-8",
    )

    # Candidate patch 1 has an off-by-one initialization (`acc = 1`), so Stage 7 Test will fail and trigger Stage 9 Repair
    candidate_patch_1 = (
        "def total_angka(items: list[int]) -> int:\n"
        "    acc = 1\n"
        "    for x in items:\n"
        "        acc += x\n"
        "    return acc\n"
    )
    # Repaired patch fixes `acc = 0`
    repaired_patch = (
        "def total_angka(items: list[int]) -> int:\n"
        "    acc = 0\n"
        "    for x in items:\n"
        "        acc += x\n"
        "    return acc\n"
    )

    code, loop_res = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "engineering_loop",
            "task_goal": "Fix total_angka accumulation bug in buggy_accumulator.py",
            "target_file": str(target_py),
            "test_file": str(test_py),
            "candidate_patch_code": candidate_patch_1,
            "repaired_patch_code": repaired_patch,
        },
    )
    assert code == 200
    assert loop_res["initial_test_passed"] is False
    assert loop_res["repair_applied"] is True
    assert loop_res["final_test_passed"] is True
    assert loop_res["ok"] is True
    observed_stages = [s["stage"] for s in loop_res["stages"]]
    assert observed_stages == list(AutonomousEngineeringLoop.STAGE_NAMES)
    assert loop_res["memory_record"]["epistemic_state"] == "VALIDATED"


def test_07_cosmictera_system_control_and_measured_statuses(master_app: NUILocalServiceApp) -> None:
    """Test 7 — CosmicTera System Control Test:
    - Inspects all CosmicTera subsystems with real measured status badges
    - Executes 7-stage NUI Control Loop on HYBIT_18D_MATH
    """
    code, sub_data = master_app.dispatch_request("GET", "/api/master/subsystems")
    assert code == 200
    subsystems = sub_data["subsystems"]
    assert len(subsystems) == 8
    for sub in subsystems:
        assert sub["status"] in MEASURED_SUBSYSTEM_STATUSES
        assert sub["status"] in {"RUNNING", "AVAILABLE"}

    # Execute 7-stage control loop
    code_loop, loop_out = master_app.dispatch_request(
        "POST",
        "/api/subsystems/execute",
        {"subsystem": "HYBIT_18D_MATH", "operation": "COMPUTE_BSM_112_10_9"},
    )
    assert code_loop == 200
    assert loop_out["ok"] is True
    assert loop_out["result"]["decision_stage"]["action"] == "COMMIT_OUTPUT"


def test_08_hardware_and_fpga_workflow_honesty(master_app: NUILocalServiceApp) -> None:
    """Test 8 — Hardware / FPGA Workflow Test:
    - Inspects OSS CAD Suite toolchain, bitstream SHA-256, physical board connection, and H-ISA simulation
    - Strictly distinguishes `LIVE_PHYSICAL`, `BUILD_ARTIFACT`, `MEASURED`, and `SIMULATED`
    """
    code, hw = master_app.dispatch_request(
        "GET", "/api/master/hardware-workflow?simulate_disconnected=1"
    )
    assert code == 200

    assert hw["live_physical"]["board_connected"] is False
    assert hw["live_physical"]["connection_status"] == "DISCONNECTED"
    assert hw["build_artifact"]["evidence_class"] == "BUILD_ARTIFACT"
    assert hw["build_artifact"]["bitstream_exists"] is True
    assert len(hw["build_artifact"]["bitstream_sha256"]) == 64

    assert hw["measured_toolchain"]["evidence_class"] == "MEASURED"
    assert hw["measured_toolchain"]["tools"]["yosys"]["installed"] is True
    assert hw["measured_toolchain"]["tools"]["nextpnr-himbaechel"]["installed"] is True
    assert hw["measured_toolchain"]["tools"]["gowin_pack"]["installed"] is True

    assert hw["simulated_execution"]["evidence_class"] == "SIMULATED"
    assert hw["simulated_execution"]["executed"] is True
    assert hw["simulated_execution"]["halted"] is True
    assert hw["simulated_execution"]["R1"] == 156


def test_09_permission_modes_and_immutable_core_protection(
    master_app: NUILocalServiceApp, tmp_path: Path
) -> None:
    """Test 9 — Permission & Security Test:
    - Verifies `READ_ONLY` allows `READ`/`LIST` but blocks `WRITE`/`DELETE`
    - Verifies `DENY` blocks access and `REVOKE_ACCESS` revokes active rules
    - Verifies `Immutable Core Protection` blocks unauthorized writes/edits to `src/hijaiyyah/core/aggregator.py`, `src/hijaiyyah/hisa/vm.py`, and `rtl/core/hcpu_core.v`
    """
    ro_dir = tmp_path / "readonly_zone"
    ro_dir.mkdir(parents=True, exist_ok=True)
    sample_file = ro_dir / "note.txt"
    sample_file.write_text("safe read content", encoding="utf-8")

    # Set READ_ONLY rule on ro_dir
    master_app.permissions.set_rule(
        category="LOCAL_FILES",
        target_type="path",
        target_value=str(ro_dir),
        operation="*",
        decision="READ_ONLY",
    )

    read_res = master_app.tools.execute_tool("files.read", {"path": str(sample_file)})
    assert read_res["ok"] is True
    assert read_res["decision_source"] == "READ_ONLY"

    write_res = master_app.tools.execute_tool(
        "files.write", {"path": str(sample_file), "content": "mutated"}
    )
    assert write_res["ok"] is False
    assert write_res["status"] == "DENIED"
    assert write_res["decision_source"] == "RULE_READ_ONLY"

    # Verify Immutable Core Protection blocks modifying core math, H-ISA, and RTL even though REPO_ROOT is READ_WRITE
    for protected_rel in (
        "src/hijaiyyah/core/aggregator.py",
        "src/hijaiyyah/hisa/vm.py",
        "rtl/core/hcpu_core.v",
        "AGENTS.md",
        "cosmictera/RULES.md",
    ):
        chk = check_immutable_core_path(protected_rel, explicit_owner_approval=False)
        assert chk["allowed"] is False
        assert chk["status"] == "BLOCKED_IMMUTABLE_CORE_PROTECTION"

    core_file = Path(__file__).resolve().parents[2] / "src" / "hijaiyyah" / "core" / "aggregator.py"
    attempt_write = master_app.tools.execute_tool(
        "files.write",
        {"path": str(core_file), "content": "# unauthorized overwrite"},
    )
    assert attempt_write["ok"] is False
    assert attempt_write["status"] == "ERROR"
    assert "Immutable Core Protection" in attempt_write["error"]


def test_10_self_learning_engineering_memory_and_12_control_panels(
    master_app: NUILocalServiceApp,
) -> None:
    """Test 10 — Self-Learning & Engineering Memory Test:
    - Stores and separates `VALIDATED`, `CANDIDATE`, `REJECTED`, and `HISTORICAL` records
    - Verifies all 12 Control Center Panels (Section G) are populated
    """
    # Create a CANDIDATE record, then supersede it with a VALIDATED record so the first becomes HISTORICAL
    _, cand = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "store_memory",
            "category": "CODING_PATTERN",
            "title": "Draft H-ISA Loop Unrolling",
            "content": "Initial candidate unrolling note",
            "epistemic_state": "CANDIDATE",
        },
    )
    assert cand["epistemic_state"] == "CANDIDATE"

    _, val = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "store_memory",
            "category": "CODING_PATTERN",
            "title": "Verified H-ISA Loop Unrolling",
            "content": "Validated 4x loop unrolling with cycle proof",
            "epistemic_state": "VALIDATED",
            "supersede_memory_id": cand["memory_id"],
        },
    )
    assert val["epistemic_state"] == "VALIDATED"

    _, rej = master_app.dispatch_request(
        "POST",
        "/api/master/op",
        {
            "op": "store_memory",
            "category": "FAILED_HYPOTHESIS",
            "title": "Invalid Clock Multiplier Assumption",
            "content": "Rejected hypothesis",
            "epistemic_state": "REJECTED",
        },
    )
    assert rej["epistemic_state"] == "REJECTED"

    code_mem, mem_breakdown = master_app.dispatch_request("GET", "/api/master/engineering-memory")
    assert code_mem == 200
    counts = mem_breakdown["counts_by_state"]
    assert set(counts.keys()) == MEMORY_EPISTEMIC_STATES
    assert counts["VALIDATED"] >= 1
    assert counts["REJECTED"] >= 1
    assert counts["HISTORICAL"] >= 1

    # Verify all 12 Control Center Panels (Section G)
    code_panels, panels = master_app.dispatch_request("GET", "/api/master/panels")
    assert code_panels == 200
    expected_panel_keys = {
        "1_nui_intelligence",
        "2_local_llm_assets",
        "3_model_orchestrator",
        "4_cosmictera_knowledge",
        "5_technology_stack",
        "6_coding_studio",
        "7_execution_center",
        "8_build_and_test_center",
        "9_hardware_laboratory",
        "10_self_learning",
        "11_permission_center",
        "12_activity_and_audit",
    }
    assert set(panels.keys()) == expected_panel_keys
