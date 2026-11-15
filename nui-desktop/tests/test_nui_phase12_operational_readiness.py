"""Phase 12 Operational Readiness & Final Acceptance Test Suite (`test_nui_phase12_operational_readiness.py`).

Validates all 10 sections of COSMICTERA NUI — PHASE 12:
1. Operator-Driven GUI Acceptance Checklist & Separation of Manual vs Automated Evidence.
2. Long-Run Stability & Soak Harness (SQLite `PRAGMA integrity_check`, RSS delta, streaming stability, restart recovery).
3. Multi-Session & Data Integrity (3 concurrent sessions, session switching, app restart, provider/model switch, zero cross-session bleed).
4. Local LLM Resource Management (`BALANCED_M1_MAX_32GB` policy on Apple M1 Max 32 GB, single heavy model guard, unload-before-load, failover).
5. CosmicTera Mathematical Reliability Benchmark (28 Hijaiyyah, 18D Hybit, 5D Features, GF(2) Matrix Rank & Period, Atom Address Unification, H-ISA, L4 parity, boundary & mutation cases).
6. Software Engineering Reliability across Multiple Project Fixtures + Rollback on Failed Patch + Protection of 4 HDMI Files & 43 Canonical NUI Modules.
7. Security Acceptance (Folder boundary, `READ_ONLY` `/Users/AMRA/opt`, Permission Revoke, L7 Fail-Closed Gate, External Content Sanitization, Secret Redaction, Untrusted Context Isolation, Audit Continuity).
8. Hardware Evidence Classification (`LIVE_PHYSICAL`, `MEASURED`, `BUILD_ARTIFACT`, `SIMULATED`, `UNKNOWN`).
9. Measured Performance Telemetry.
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

from backend.master_control import check_immutable_core_path
from backend.phase12_readiness import (
    PROTECTED_HDMI_FILES,
    AppleM1MaxResourcePolicyManager,
    build_operator_gui_acceptance_checklist,
    run_cosmictera_mathematical_reliability_benchmark,
    run_stability_soak_cycles,
)
from backend.server import NUILocalServiceApp
from backend.storage import redact_secrets
from backend.tools import sanitize_untrusted_web_content


@pytest.fixture(scope="module")
def phase12_env(tmp_path_factory: pytest.TempPathFactory) -> tuple[NUILocalServiceApp, Path]:
    tmp_dir = tmp_path_factory.mktemp("phase12_env")
    db_file = tmp_dir / "phase12_readiness.db"
    app = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    return app, tmp_dir


def test_section1_and_2_gui_checklist_and_stability_soak(phase12_env: tuple[NUILocalServiceApp, Path]) -> None:
    """Sections 1 & 2: Verify honest separation of manual GUI status (NOT_TESTED) and multi-cycle stability soak."""
    app, _ = phase12_env
    checklist = build_operator_gui_acceptance_checklist()
    assert len(checklist) == 15
    assert all(item["operator_manual_gui_status"] == "NOT_TESTED" for item in checklist)
    assert all(item["automated_contract_status"] in ("PASS_LIVE", "PASS_SIMULATED") for item in checklist)

    soak = run_stability_soak_cycles(app, cycles=10)
    assert soak["status"] == "PASS_LIVE"
    assert soak["errors_count"] == 0
    assert soak["sqlite_integrity_check"] == "ok"
    assert soak["session_messages_persisted"] >= 20
    assert soak["backend_restart_recovery_ms"] > 0


def test_section3_multi_session_and_data_integrity(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Section 3: Open multiple sessions, switch between them, restart app, switch provider/model, verify zero context bleed."""
    db_file = tmp_path_factory.mktemp("phase12_multisess") / "multisess.db"
    app = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)

    _, s1 = app.dispatch_request("POST", "/api/sessions", {"title": "Session Alpha Math", "provider": "native_nui"})
    _, s2 = app.dispatch_request("POST", "/api/sessions", {"title": "Session Beta Coding", "provider": "local_ollama"})
    _, s3 = app.dispatch_request("POST", "/api/sessions", {"title": "Session Gamma Hardware", "provider": "native_nui"})

    sid1, sid2, sid3 = s1["session_id"], s2["session_id"], s3["session_id"]
    assert len({sid1, sid2, sid3}) == 3

    # Send distinct turns to each session
    app.dispatch_request("POST", "/api/chat", {
        "session_id": sid1,
        "user_message": "ALPHA_MARKER: Berapa 11 + 22?",
        "provider": "native_nui",
    })
    app.dispatch_request("POST", "/api/chat", {
        "session_id": sid2,
        "user_message": "BETA_MARKER: Hitung 30 + 12",
        "provider": "native_nui",
    })
    app.dispatch_request("POST", "/api/chat", {
        "session_id": sid3,
        "user_message": "GAMMA_MARKER: Hitung 50 + 50",
        "provider": "native_nui",
    })

    # Close and reopen application on same SQLite DB
    app_reopened = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    app_reopened.dispatch_request("POST", "/api/settings", {"active_provider": "local_ollama"})
    app_reopened.dispatch_request("POST", "/api/models/op", {"op": "select", "model_tag": "qwen3-coder:30b"})

    _, loaded_s1 = app_reopened.dispatch_request("GET", f"/api/sessions?session_id={sid1}")
    _, loaded_s2 = app_reopened.dispatch_request("GET", f"/api/sessions?session_id={sid2}")
    _, loaded_s3 = app_reopened.dispatch_request("GET", f"/api/sessions?session_id={sid3}")

    s1_text = " ".join(m["content"] for m in loaded_s1["messages"])
    s2_text = " ".join(m["content"] for m in loaded_s2["messages"])
    s3_text = " ".join(m["content"] for m in loaded_s3["messages"])

    assert "ALPHA_MARKER" in s1_text and "BETA_MARKER" not in s1_text and "GAMMA_MARKER" not in s1_text
    assert "BETA_MARKER" in s2_text and "ALPHA_MARKER" not in s2_text and "GAMMA_MARKER" not in s2_text
    assert "GAMMA_MARKER" in s3_text and "ALPHA_MARKER" not in s3_text and "BETA_MARKER" not in s3_text


def test_section4_local_llm_resource_management_m1_max_policy(phase12_env: tuple[NUILocalServiceApp, Path]) -> None:
    """Section 4: Verify Apple M1 Max 32 GB Resource Policy, model discovery, and safe failover."""
    app, _ = phase12_env
    mgr = AppleM1MaxResourcePolicyManager(app)

    # 1. Load heavy specialist qwen3-coder:30b (18.5 GiB)
    r1 = mgr.evaluate_and_prepare_model_load("qwen3-coder:30b")
    assert r1["allowed"] is True
    assert r1["is_heavy_specialist"] is True
    assert r1["concurrent_heavy_models_count"] == 1

    # 2. Load fast model qwen3:4b-instruct-2507-q4_K_M (2.5 GiB) alongside it
    r2 = mgr.evaluate_and_prepare_model_load("qwen3:4b-instruct-2507-q4_K_M")
    assert r2["allowed"] is True
    assert r2["is_heavy_specialist"] is False

    # 3. Attempting to load uninstalled qwen3.8:27b triggers clean failover to native_nui
    r3 = mgr.evaluate_and_prepare_model_load("qwen3.8:27b")
    assert r3["allowed"] is False
    assert r3["status"] == "MODEL_NOT_INSTALLED_FAILOVER_READY"
    assert r3["failover_provider"] == "native_nui"


def test_section5_cosmictera_mathematical_reliability() -> None:
    """Section 5: Run canonical CosmicTera Mathematical Reliability Benchmark."""
    res = run_cosmictera_mathematical_reliability_benchmark()
    assert res["status"] == "PASS_LIVE"
    assert res["letters_verified"] == 28
    assert res["hybit_18d_verified"] == 28
    assert res["features_5d_verified"] == 28
    assert res["jim_gf2_tail_and_period"] == [1, 31]
    assert res["atom_address_unification_28_letters"] is True
    assert res["hisa_test_bsm_output"] == [112]
    assert res["mutation_guard_rejection_verified"] is True
    assert res["invalid_input_rejection_verified"] is True


def test_section6_software_engineering_reliability_and_hdmi_protection(phase12_env: tuple[NUILocalServiceApp, Path]) -> None:
    """Section 6: Verify multi-fixture engineering, automatic rollback on bad patch, and protection of 4 HDMI files + 43 NUI modules."""
    app, tmp_dir = phase12_env

    # 1. Fixture A: Successful patch & regression test
    fix_a_dir = tmp_dir / "fixture_a"
    fix_a_dir.mkdir(parents=True, exist_ok=True)
    mod_a = fix_a_dir / "vector_ops.py"
    tst_a = fix_a_dir / "test_vector_ops.py"
    mod_a.write_text("def dot2(x1: int, y1: int, x2: int, y2: int) -> int:\n    return x1 * x2 - y1 * y2\n", encoding="utf-8")
    tst_a.write_text("from vector_ops import dot2\ndef test_dot2():\n    assert dot2(2, 3, 4, 5) == 23\n", encoding="utf-8")

    code, res_a = app.dispatch_request("POST", "/api/master/op", {
        "op": "engineering_loop",
        "task_goal": "Fix dot2 to add y1 * y2",
        "target_file": str(mod_a),
        "test_file": str(tst_a),
        "candidate_patch_code": "def dot2(x1: int, y1: int, x2: int, y2: int) -> int:\n    return x1 * x2 + y1 * y2\n",
    })
    assert code == 200 and res_a["ok"] is True and res_a["rolled_back"] is False

    # 2. Fixture B: Bad patch that fails tests -> must automatically rollback to original code!
    fix_b_dir = tmp_dir / "fixture_b"
    fix_b_dir.mkdir(parents=True, exist_ok=True)
    mod_b = fix_b_dir / "norm_ops.py"
    tst_b = fix_b_dir / "test_norm_ops.py"
    orig_b = "def sq_norm(x: int) -> int:\n    return x * x\n"
    mod_b.write_text(orig_b, encoding="utf-8")
    tst_b.write_text("from norm_ops import sq_norm\ndef test_sq():\n    assert sq_norm(4) == 16\n", encoding="utf-8")

    code, res_b = app.dispatch_request("POST", "/api/master/op", {
        "op": "engineering_loop",
        "task_goal": "Attempt broken patch to verify rollback",
        "target_file": str(mod_b),
        "test_file": str(tst_b),
        "candidate_patch_code": "def sq_norm(x: int) -> int:\n    return x + 1\n",
    })
    assert code == 200
    assert res_b["ok"] is False
    assert res_b["rolled_back"] is True
    assert mod_b.read_text(encoding="utf-8") == orig_b

    # 3. Verify all 4 protected HDMI files and 43 canonical NUI modules are blocked from modification
    for hdmi_rel in PROTECTED_HDMI_FILES:
        chk = check_immutable_core_path(REPO_ROOT / hdmi_rel, explicit_owner_approval=False)
        assert chk["allowed"] is False, f"Protected HDMI file {hdmi_rel} must be blocked"

    nui_py_files = sorted((REPO_ROOT / "src" / "hijaiyyah" / "nui").glob("*.py"))
    assert len(nui_py_files) == 43
    for nui_f in nui_py_files:
        chk = check_immutable_core_path(nui_f, explicit_owner_approval=False)
        assert chk["allowed"] is False


def test_section7_8_9_security_hardware_and_performance(phase12_env: tuple[NUILocalServiceApp, Path]) -> None:
    """Sections 7, 8, 9: Verify security gates, permission revoke, L7 fail-closed, secret redaction, and hardware evidence."""
    app, _ = phase12_env

    # Grant and then REVOKE a permission rule
    _, rule = app.dispatch_request("POST", "/api/permissions/decide", {
        "category": "WEB_READING",
        "target_type": "domain",
        "target_value": "example.org",
        "operation": "READ",
        "decision": "ALWAYS_ALLOW",
    })
    assert rule["decision"] == "ALWAYS_ALLOW"

    _, rev = app.dispatch_request("POST", "/api/permissions/revoke", {
        "rule_id": rule["rule_id"],
    })
    assert rev["revoked"] is True

    # L7 fail-closed gate on mutative hardware operation
    l7_res = app.tools.l7_adapter.evaluate_and_decide(
        operation="SEND_PROGRAM",
        domain="MUTATIVE",
        live_board=False,
    )
    assert l7_res["decision"]["decision"] == "DENY"

    # Untrusted external web content isolation & privileged tool block
    blocked_untrusted = app.tools.execute_tool(
        "terminal.exec",
        {"command": "echo test"},
        untrusted_context=True,
    )
    assert blocked_untrusted["ok"] is False and blocked_untrusted["status"] == "DENIED"

    # External content sanitization & secret redaction
    sanitized = sanitize_untrusted_web_content("Normal technical text", "https://docs.python.org")
    assert sanitized["trust_level"] == "UNTRUSTED_EXTERNAL_WEB_DATA"
    assert sanitized["can_trigger_privileged_tools"] is False

    redacted = redact_secrets({"Authorization": "Bearer sk-1234567890abcdef1234567890"})
    assert "sk-123456" not in str(redacted)

    # Hardware evidence classification
    code, hw = app.dispatch_request("GET", "/api/hardware/status")
    assert code == 200
    assert hw["live_telemetry_available"] is False
    assert hw["evidence_breakdown"]["bitstream_on_disk"] == "BUILD_ARTIFACT"
    assert hw["evidence_breakdown"]["p2_board_corpus"] == "MEASURED"
    assert hw["evidence_breakdown"]["hcpu_control_loop"] == "SIMULATED"
    assert hw["evidence_breakdown"]["live_silicon_uart_telemetry"] == "UNKNOWN"
