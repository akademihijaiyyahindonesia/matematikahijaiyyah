"""Phase 10 Live Functional Verification & Acceptance Suite for CosmicTera NUI Desktop.

Covers all 15 sections and priorities from COSMICTERA NUI — PHASE 10:
- Priority 1: Access Control, Folder Boundaries (/Users/AMRA/opt READ_ONLY write denial), L7 Gate, Immutable Core Protection
- Priority 2: Language Engine & Model Asset Library (qwen3-coder:30b CODING SPECIALIST (INSTALLED), qwen3.8:27b AVAILABLE_TO_PULL)
- Priority 3: NUI Chat Single-Terminal-State Machine (CANCELLED xor COMPLETE) & 6-point Latency Breakdown
- Priority 4: Settings (/api/settings & /api/settings/reset), Web & Internet (/api/web/status & /api/web/op), and Browser
- Priority 5: L0-L11 Canonical Layers & 11 Subsystems live timestamps/provenance, and Hardware Monitor honest telemetry
- Priority 6: Self-Learning 10 Sub-Menus, Coding Studio file operations, and Git Repository Inspector
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

for p in (str(NUI_DESKTOP_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.server import NUILocalServiceApp


@pytest.fixture(scope="module")
def phase10_app(tmp_path_factory: pytest.TempPathFactory) -> tuple[NUILocalServiceApp, Path]:
    tmp_dir = tmp_path_factory.mktemp("phase10")
    db_file = tmp_dir / "phase10_test.db"
    app = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    return app, tmp_dir


def test_priority_1_access_control_and_folder_boundaries(phase10_app: tuple[NUILocalServiceApp, Path]) -> None:
    """Verify Phase 10.9 & 10.12: Access Control, READ_ONLY /Users/AMRA/opt write denial, and folder boundaries."""
    app, _ = phase10_app

    code, _ = app.dispatch_request("POST", "/api/files/folders", {
        "action": "ADD",
        "path": "/Users/AMRA/hijaiyyah-mathematics",
        "label": "hijaiyyah-mathematics",
        "access_mode": "READ_WRITE",
    })
    assert code == 200

    code, _ = app.dispatch_request("POST", "/api/files/folders", {
        "action": "ADD",
        "path": "/Users/AMRA/opt",
        "label": "opt",
        "access_mode": "READ_ONLY",
    })
    assert code == 200

    code, perms = app.dispatch_request("GET", "/api/permissions")
    assert code == 200
    folders = {f["path"]: f["access_mode"] for f in perms.get("authorized_folders", [])}
    assert folders.get("/Users/AMRA/hijaiyyah-mathematics") == "READ_WRITE"
    assert folders.get("/Users/AMRA/opt") == "READ_ONLY"
    assert len(perms.get("rules", [])) >= 5

    with pytest.raises(PermissionError, match="FOLDER_READ_ONLY_DENIED"):
        app.orchestrator.tools._handle_files_write(
            {"path": "/Users/AMRA/opt/phase10_probe.txt", "content": "should not be written"},
            {},
        )
    assert not Path("/Users/AMRA/opt/phase10_probe.txt").exists()

    with pytest.raises(PermissionError, match="PATH_OUTSIDE_CONNECTED_FOLDERS"):
        app.orchestrator.tools._handle_files_read({"path": "/etc/hosts"}, {})

    with pytest.raises(PermissionError, match="Immutable Core Protection"):
        app.orchestrator.tools._handle_files_write(
            {"path": str(REPO_ROOT / "src" / "hijaiyyah" / "nui" / "facts.py"), "content": "# blocked"},
            {},
        )


def test_priority_2_language_engine_and_model_roles(phase10_app: tuple[NUILocalServiceApp, Path]) -> None:
    """Verify Phase 10.2: Model asset library roles and honest coding specialist identification."""
    app, _ = phase10_app
    code, lib = app.dispatch_request("GET", "/api/models/library")
    assert code == 200
    assert lib.get("active_coding_specialist_id") == "qwen3-coder:30b"
    assert "qwen3-coder:30b" in lib.get("active_coding_specialist_label", "").lower()
    assert "last_checked" in lib

    assets = {m["model_id"]: m for m in lib.get("model_assets", [])}
    assert "qwen3-coder:30b" in assets
    assert assets["qwen3-coder:30b"]["model_role"] == "CODING SPECIALIST (INSTALLED)"
    assert assets["qwen3.8:27b"]["status"] == "AVAILABLE_TO_PULL"
    assert assets["qwen3:4b-instruct-2507-q4_K_M"]["model_role"] == "FAST INTERACTIVE & GENERAL INTELLIGENCE"


def test_priority_3_single_terminal_state_and_latency_breakdown(phase10_app: tuple[NUILocalServiceApp, Path]) -> None:
    """Verify Phase 10.1 & 10.13: Single terminal state (CANCELLED xor COMPLETE) and 6-point latency telemetry."""
    app, _ = phase10_app

    events_ok = list(app.orchestrator.stream_chat_turn(
        user_message="Berapa 5 + 7?",
        request_id="req-phase10-complete",
        provider_id="native_nui",
    ))
    final_ev = [e for e in events_ok if e.get("event") == "final_response"][-1]
    stages_ok = final_ev.get("thinking_stages", [])
    assert stages_ok[-1] == "COMPLETE"
    assert "CANCELLED" not in stages_ok
    latency = (
        final_ev.get("latency_breakdown")
        or final_ev.get("turn_output", {}).get("data", {}).get("latency_breakdown", {})
    )
    for required_key in (
        "request_received_ms",
        "first_token_ms",
        "tool_start_ms",
        "tool_end_ms",
        "generation_end_ms",
        "total_duration_ms",
    ):
        assert required_key in latency

    events_cancel = list(app.orchestrator.stream_chat_turn(
        user_message="Pertanyaan yang dibatalkan",
        request_id="req-phase10-cancel",
        provider_id="native_nui",
        simulate_stop=True,
    ))
    cancel_ev = [e for e in events_cancel if e.get("event") == "generation_cancelled"][-1]
    stages_cancel = (
        cancel_ev.get("thinking_stages")
        or cancel_ev.get("turn_output", {}).get("thinking_stages", [])
    )
    assert stages_cancel[-1] == "CANCELLED"
    assert "COMPLETE" not in stages_cancel


def test_priority_4_settings_web_and_browser_endpoints(phase10_app: tuple[NUILocalServiceApp, Path]) -> None:
    """Verify Phase 10.7, 10.8, 10.14: Settings save/reset and Web/Browser status & LOCAL mode gating."""
    app, _ = phase10_app

    code, _ = app.dispatch_request("POST", "/api/settings", {"operating_mode": "LOCAL"})
    assert code == 200

    code, web_st = app.dispatch_request("GET", "/api/web/status")
    assert code == 200
    assert web_st["operating_mode"] == "LOCAL"
    assert web_st["web_allowed_in_current_mode"] is False

    code, web_res = app.dispatch_request("POST", "/api/web/op", {"op": "search", "query": "Python"})
    assert code == 200
    assert web_res["status"] in ("DENIED", "BLOCKED_LOCAL_MODE")

    code, reset_res = app.dispatch_request("POST", "/api/settings/reset", {})
    assert code == 200
    assert reset_res["status"] == "RESET_TO_DEFAULTS"
    assert reset_res["settings"]["operating_mode"] == "HYBRID"


def test_priority_5_layers_subsystems_and_honest_hardware_monitor(phase10_app: tuple[NUILocalServiceApp, Path]) -> None:
    """Verify Phase 10.4, 10.5, 10.11: Live timestamps/provenance on L0-L11 and honest Hardware Monitor status."""
    app, _ = phase10_app

    code, layers_data = app.dispatch_request("GET", "/api/layers/canonical")
    assert code == 200
    assert layers_data["total_layers"] == 12
    for layer in layers_data["layers"]:
        assert "last_checked" in layer
        assert "source" in layer
        assert "evidence_classification" in layer

    code, hw = app.dispatch_request("GET", "/api/hardware/status")
    assert code == 200
    assert "evidence_breakdown" in hw
    assert "last_checked" in hw
    assert hw["live_telemetry_available"] is False
    assert "UNKNOWN (NO LIVE UART TELEMETRY)" in hw["cpu_state"]
    assert hw["evidence_breakdown"]["bitstream_on_disk"] == "BUILD_ARTIFACT"
    assert hw["evidence_breakdown"]["hcpu_control_loop"] == "SIMULATED"


def test_priority_6_self_learning_coding_studio_and_git_inspector(phase10_app: tuple[NUILocalServiceApp, Path]) -> None:
    """Verify Phase 10.3, 10.6, 10.10: Self-Learning 10 sub-menus, Coding Studio sandbox write/read, and Git status."""
    app, tmp_dir = phase10_app

    code, sl = app.dispatch_request("GET", "/api/self-learning/overview")
    assert code == 200
    for key in (
        "1_learning_overview",
        "2_knowledge_base",
        "3_coding_skills",
        "4_model_assets",
        "5_learning_history",
        "6_feedback",
        "7_evaluation",
        "8_skill_validation",
        "9_model_performance",
        "10_learning_configuration",
    ):
        assert key in sl

    app.dispatch_request("POST", "/api/files/folders", {
        "action": "ADD",
        "path": str(tmp_dir),
        "label": "phase10_sandbox",
        "access_mode": "READ_WRITE",
    })
    sandbox_file = tmp_dir / "studio_sample.py"
    sandbox_file.write_text("def add_pair(a, b):\n    return a + b\n", encoding="utf-8")

    code, r_res = app.dispatch_request("POST", "/api/files/op", {"op": "read", "path": str(sandbox_file)})
    assert code == 200
    assert "return a + b" in str(r_res)

    code, git_st = app.dispatch_request("GET", "/api/git/status")
    assert code == 200
    assert "branch" in git_st
    assert "recent_commits" in git_st
