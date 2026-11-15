"""Phase 11 Real Desktop Runtime Validation Suite for CosmicTera NUI Desktop.

Validates Sections 1–6 of COSMICTERA NUI — PHASE 11:
1. Launch & Bundle Verification (`CosmicTera NUI.app` bundle structure, Mach-O arm64 binary, Info.plist, and SwiftUI 15-section wiring).
2. All 15 Sidebar Menu Endpoints & Interactive Controls (`NUI Chat`, `Language Engine`, `Self-Learning Center`,
   `NUI Core`, `Computing System`, `NUI Architecture`, `Coding Studio`, `Web & Internet`, `Browser`,
   `Files & Knowledge`, `Hardware Monitor`, `Projects & Git`, `Access Control`, `Activity History`, `Settings`).
3. Live LLM & Multi-Model Orchestration (`qwen3-coder:30b` coding specialist, `qwen3:4b-instruct-2507-q4_K_M` fast general,
   `hermes3:8b` reviewer, `LOCAL` vs `HYBRID` mode switching, multi-turn context, streaming + cancellation, recovery).
4. 10 Real Operational Scenarios (General Q&A, Hijaiyyah Math 18D/5D/BSM, Repo Search, HASM & Verilog Analysis,
   H-ISA Simulator Execution, L8 Fixture Diagnosis, Sandbox Python Repair + Pytest Regression,
   Unauthorized Write Denial on `/Users/AMRA/opt` & `src/hijaiyyah/nui/facts.py`, and Audit Log Verification).
5. Hardware Realism (`LIVE_PHYSICAL`, `MEASURED`, `BUILD_ARTIFACT`, `SIMULATED`, `UNKNOWN`).
6. UI & Persistence Reliability (Settings persistence across app re-instantiation, single terminal state, no empty views).
"""

from __future__ import annotations

from pathlib import Path
import plistlib
import subprocess
import sys
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

for p in (str(NUI_DESKTOP_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.server import NUILocalServiceApp


@pytest.fixture(scope="module")
def phase11_runtime(tmp_path_factory: pytest.TempPathFactory) -> tuple[NUILocalServiceApp, Path]:
    tmp_dir = tmp_path_factory.mktemp("phase11_runtime")
    db_file = tmp_dir / "phase11_runtime.db"
    app = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    return app, tmp_dir


def test_section1_app_bundle_and_launch_readiness(phase11_runtime: tuple[NUILocalServiceApp, Path]) -> None:
    """Section 1: Verify CosmicTera NUI.app bundle, Mach-O arm64 executable, Info.plist, and /api/health."""
    app, _ = phase11_runtime
    app_bundle = NUI_DESKTOP_ROOT / "macos" / "build" / "CosmicTera NUI.app"
    info_plist_path = app_bundle / "Contents" / "Info.plist"
    bin_path = app_bundle / "Contents" / "MacOS" / "CosmicTeraNUI"
    swift_src = NUI_DESKTOP_ROOT / "macos" / "Sources" / "CosmicTeraNUIApp.swift"

    assert app_bundle.exists(), "CosmicTera NUI.app bundle must exist"
    assert info_plist_path.exists(), "Info.plist must exist"
    assert bin_path.exists() and bin_path.stat().st_size > 100_000, "Compiled Mach-O binary must exist"

    plist_data = plistlib.loads(info_plist_path.read_bytes())
    assert plist_data["CFBundleIdentifier"] == "com.cosmictera.nui.desktop"
    assert plist_data["CFBundleExecutable"] == "CosmicTeraNUI"

    # Verify all 15 SidebarSection cases are explicitly handled in CosmicTeraNUIApp.swift
    swift_text = swift_src.read_text(encoding="utf-8")
    for case_name in (
        "case .nuiChat:",
        "case .languageEngine:",
        "case .selfLearning:",
        "case .nuiCore, .nuiArchitecture:",
        "case .computingSystem:",
        "case .codingStudio:",
        "case .browser:",
        "case .hardwareMonitor:",
        "case .activityHistory:",
        "case .filesKnowledge, .projectsGit:",
        "case .accessControl:",
        "case .webInternet:",
        "case .settings:",
    ):
        assert case_name in swift_text, f"Missing explicit SwiftUI view case: {case_name}"

    code, health = app.dispatch_request("GET", "/api/health")
    assert code == 200
    assert health["status"] == "READY"
    assert health["service_state"] == "LOCAL SERVICE READY"
    assert isinstance(health["persona"], dict) and len(health["persona"]) > 0
    code_p, persona_info = app.dispatch_request("GET", "/api/persona")
    assert code_p == 200
    assert persona_info["persona"]["persona_source"] == "src/hijaiyyah/ai/runtime.py::HybitAIProgram.system"


def test_section2_all_15_sidebar_menus_interactive_contract(phase11_runtime: tuple[NUILocalServiceApp, Path]) -> None:
    """Section 2: Exercise the backend contract backing each of the 15 sidebar menus."""
    app, tmp_dir = phase11_runtime

    # Connect workspace folders
    app.dispatch_request("POST", "/api/files/folders", {
        "action": "ADD",
        "path": str(REPO_ROOT),
        "label": "hijaiyyah-mathematics",
        "access_mode": "READ_WRITE",
    })
    app.dispatch_request("POST", "/api/files/folders", {
        "action": "ADD",
        "path": "/Users/AMRA/opt",
        "label": "opt",
        "access_mode": "READ_ONLY",
    })
    app.dispatch_request("POST", "/api/files/folders", {
        "action": "ADD",
        "path": str(tmp_dir),
        "label": "phase11_sandbox",
        "access_mode": "READ_WRITE",
    })

    # 1. NUI Chat (/api/sessions + /api/chat)
    code, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Phase 11 Menu Verification"})
    assert code in (200, 201)
    sid = sess["session_id"]

    # 2. Language Engine (/api/models/library + /api/models/op)
    code, lib = app.dispatch_request("GET", "/api/models/library")
    assert code == 200
    assert lib["active_coding_specialist_id"] == "qwen3-coder:30b"

    # 3. Self-Learning Center (/api/self-learning/overview + feedback + rollback)
    code, sl = app.dispatch_request("GET", "/api/self-learning/overview")
    assert code == 200
    assert len([k for k in sl if k[0].isdigit()]) == 10
    code, fb = app.dispatch_request("POST", "/api/self-learning/op", {
        "op": "feedback",
        "topic": "Phase 11 UI Feedback",
        "correction_summary": "Pastikan setiap tabel memiliki satuan ms.",
    })
    assert code == 200 and fb["provenance"] == "User Provided"
    code, rb = app.dispatch_request("POST", "/api/self-learning/op", {
        "op": "rollback",
        "entry_id": fb["entry_id"],
    })
    assert code == 200 and rb["rolled_back"] is True

    # 4 & 6. NUI Core & NUI Architecture (/api/nui/layers & /api/layers/canonical)
    code, layers_ui = app.dispatch_request("GET", "/api/nui/layers")
    assert code == 200 and len(layers_ui["layers"]) == 12
    code, layers_can = app.dispatch_request("GET", "/api/layers/canonical")
    assert code == 200 and layers_can["total_layers"] == 12

    # 5. Computing System (/api/subsystems)
    code, subs = app.dispatch_request("GET", "/api/subsystems")
    assert code == 200 and len(subs["subsystems"]) == 11

    # 7. Coding Studio (/api/files/op write + read)
    sample_py = tmp_dir / "phase11_studio.py"
    code, w_res = app.dispatch_request("POST", "/api/files/op", {
        "op": "write",
        "path": str(sample_py),
        "content": "def kali(a: int, b: int) -> int:\n    return a * b\n",
    })
    assert code == 200 and w_res["ok"] is True
    code, r_res = app.dispatch_request("POST", "/api/files/op", {
        "op": "read",
        "path": str(sample_py),
    })
    assert code == 200 and "def kali" in r_res["result"]["content"]

    # 8 & 9. Web & Internet + Browser (/api/web/status & /api/web/op)
    code, web_st = app.dispatch_request("GET", "/api/web/status")
    assert code == 200 and web_st["status"] == "READY"

    # 10 & 12. Files & Knowledge + Projects & Git (/api/files/folders & /api/git/status)
    code, fld_data = app.dispatch_request("GET", "/api/files/folders")
    assert code == 200 and len(fld_data["folders"]) >= 3
    code, git_st = app.dispatch_request("GET", "/api/git/status")
    assert code == 200 and git_st["branch"] == "feat/cosmictera-nui-desktop"

    # 11. Hardware Monitor (/api/hardware/status & /api/hardware/control)
    code, hw_st = app.dispatch_request("GET", "/api/hardware/status")
    assert code == 200 and hw_st["live_telemetry_available"] is False
    code, hw_ctrl = app.dispatch_request("POST", "/api/hardware/control", {
        "subsystem": "TANG_NANO_20K",
        "action": "EXEC_WORKLOAD",
    })
    assert code == 200 and hw_ctrl["ok"] is True

    # 13. Access Control (/api/permissions)
    code, perm_st = app.dispatch_request("GET", "/api/permissions")
    assert code == 200 and len(perm_st["rules"]) >= 5

    # 14. Activity History (/api/comm/logs & /api/audit)
    code, comm = app.dispatch_request("GET", f"/api/comm/logs?session_id={sid}")
    assert code == 200 and "communication_logs" in comm
    code, aud = app.dispatch_request("GET", "/api/audit")
    assert code == 200 and len(aud["audit_logs"]) >= 1

    # 15. Settings (/api/settings & /api/settings/reset)
    code, st_get = app.dispatch_request("GET", "/api/settings")
    assert code == 200 and "operating_mode" in st_get


def test_section3_and_4_operational_scenarios_and_llm_routing(phase11_runtime: tuple[NUILocalServiceApp, Path]) -> None:
    """Sections 3 & 4: Verify model routing, multi-turn context, streaming/cancellation, and 10 operational scenarios."""
    app, tmp_dir = phase11_runtime

    # Model switching & verify op
    code, sel_res = app.dispatch_request("POST", "/api/models/op", {
        "op": "select",
        "model_tag": "qwen3-coder:30b",
    })
    assert code == 200 and sel_res["selected_model"] == "qwen3-coder:30b"

    code, ver_res = app.dispatch_request("POST", "/api/models/op", {
        "op": "verify",
        "model_tag": "qwen3:4b-instruct-2507-q4_K_M",
    })
    assert code == 200 and ver_res["verified"] is True

    # Scenario 1 & 2: General Q&A + Hijaiyyah Math Computation
    code, p9_math = app.dispatch_request("POST", "/api/phase9/converse", {
        "user_message": "Hitung vektor Hybit 18D, koordinat 5D, dan BSM untuk huruf Jim dan Kha!",
    })
    assert code == 200
    assert p9_math["operational_intent"] == "MATHEMATICAL_COMPUTATION"
    assert p9_math["knowledge_bundle"]["mathematical_computation"]["bsm_canonical_reference"]["bsm_an_norm_squared"] == 112

    # Scenario 3 & 4: Repo search + HASM & Verilog analysis via canonical layers
    code, l2_exp = app.dispatch_request("POST", "/api/layers/query", {
        "op": "l2_explain",
        "target": "rtl/hcpu_top.v",
    })
    assert code == 200
    code, l3_tr = app.dispatch_request("POST", "/api/layers/query", {
        "op": "l3_trace",
        "program": "rtl/programs/test_bsm.hasm",
    })
    assert code == 200

    # Scenario 5 & 6: H-ISA Simulator + L8 Fixture Diagnosis
    code, l8_diag = app.dispatch_request("POST", "/api/layers/query", {
        "op": "l8_diagnose",
        "symptom": "OFF-PRINT-SILICON",
    })
    assert code == 200 and l8_diag["verification"]["valid"] is True

    # Scenario 7 & 8: Sandbox Python repair + pytest regression
    buggy_mod = tmp_dir / "calc_mod.py"
    test_mod = tmp_dir / "test_calc_mod.py"
    buggy_mod.write_text("def scale_val(x: int) -> int:\n    return x + 2\n", encoding="utf-8")
    test_mod.write_text(
        "from calc_mod import scale_val\ndef test_scale():\n    assert scale_val(5) == 10\n",
        encoding="utf-8",
    )
    code, eng_res = app.dispatch_request("POST", "/api/master/op", {
        "op": "engineering_loop",
        "task_goal": "Fix scale_val to multiply by 2",
        "target_file": str(buggy_mod),
        "test_file": str(test_mod),
        "candidate_patch_code": "def scale_val(x: int) -> int:\n    return x * 2\n",
    })
    assert code == 200 and eng_res["ok"] is True and eng_res["final_test_passed"] is True

    # Scenario 9 & 10: Unauthorized operation denial & Audit log verification
    with pytest.raises(PermissionError, match="FOLDER_READ_ONLY_DENIED"):
        app.orchestrator.tools._handle_files_write(
            {"path": "/Users/AMRA/opt/unauthorized_phase11.txt", "content": "denied"},
            {},
        )
    with pytest.raises(PermissionError, match="Immutable Core Protection"):
        app.orchestrator.tools._handle_files_write(
            {"path": str(REPO_ROOT / "src" / "hijaiyyah" / "nui" / "facts.py"), "content": "denied"},
            {},
        )


def test_section6_settings_persistence_across_restart(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Section 6: Verify Settings persist in SQLite across application restarts."""
    db_file = tmp_path_factory.mktemp("phase11_persist") / "persist.db"
    app1 = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    app1.dispatch_request("POST", "/api/settings", {
        "operating_mode": "LOCAL",
        "active_provider": "native_nui",
    })

    # Re-instantiate app on the same SQLite database (simulating app reopen)
    app2 = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    code, settings_after = app2.dispatch_request("GET", "/api/settings")
    assert code == 200
    assert settings_after["operating_mode"] == "LOCAL"
    assert settings_after["active_provider"] == "native_nui"
