"""End-to-End Desktop Integration Tests for NUI Layers L8–L11 (`nui-desktop/tests/test_nui_l8_l11_desktop_integration.py`).

Verifies that CosmicTera NUI Desktop (`NUILocalServiceApp` & `CanonicalLayersBridge`) can:
1. Inspect live status of L8, L9, L10, and L11.
2. Execute layer functions on demand (L8 diagnostics, L9 deductive reasoning, L10 8-stage engineering, L11 11-junction universal computation).
3. Send and receive structured evidence with SHA-256 provenance.
4. Trace inter-layer relationships across L0–L11.
5. Verify results deterministically.
6. Log all actions and outcomes in the bridge action log.
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

from backend.server import NUILocalServiceApp


@pytest.fixture(scope="module")
def desktop_app(tmp_path_factory: pytest.TempPathFactory) -> NUILocalServiceApp:
    db_dir = tmp_path_factory.mktemp("nui_l8_l11_desktop")
    return NUILocalServiceApp(db_path=db_dir / "nui_l8_l11.db", use_os_keychain=False)


def test_desktop_l0_to_l11_live_matrix_all_implemented_or_frozen(desktop_app: NUILocalServiceApp) -> None:
    """Verifies `/api/layers/canonical` returns all 12 layers with L8–L11 marked IMPLEMENTED_AND_VERIFIED."""
    code, data = desktop_app.dispatch_request("GET", "/api/layers/canonical")
    assert code == 200
    layers = {row["layer"]: row for row in data["layers"]}
    assert set(layers.keys()) == {f"L{i}" for i in range(12)}

    for lid in ("L0", "L1", "L2", "L3", "L8", "L9", "L10", "L11"):
        assert layers[lid]["status"] == "IMPLEMENTED_AND_VERIFIED", f"{lid} status={layers[lid]['status']}"
    for lid in ("L4", "L5", "L6", "L7"):
        assert layers[lid]["status"] == "FROZEN_WITH_KNOWN_GAPS", f"{lid} status={layers[lid]['status']}"


def test_desktop_l8_autonomous_diagnostics_integration(desktop_app: NUILocalServiceApp) -> None:
    """Verifies NUI Desktop can inspect L8 status, run anomaly scan & symptom diagnosis, and verify evidence."""
    code_s, s = desktop_app.dispatch_request("GET", "/api/layers/canonical?layer=L8")
    assert code_s == 200
    assert s["layer"] == "L8"
    assert s["all_records_verified"] is True
    assert s["total_diagnosed_anomalies"] >= 8

    code_d, diag = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l8_diagnose", "symptom": "OFF-PRINT-SILICON e4_frame.hasm"},
    )
    assert code_d == 200
    assert diag["record"]["diagnosis_id"] == "L8-DIAG-OFF-PRINT-SILICON"
    assert diag["record"]["anomaly_class"] == "SILICON_PRINT_CORRUPTION"
    assert diag["verification"]["valid"] is True


def test_desktop_l9_deductive_reasoning_integration(desktop_app: NUILocalServiceApp) -> None:
    """Verifies NUI Desktop can inspect L9 status and run 5-stage deductive reasoning with provenance verification."""
    code_s, s = desktop_app.dispatch_request("GET", "/api/layers/canonical?layer=L9")
    assert code_s == 200
    assert s["layer"] == "L9"
    assert s["all_proofs_verified"] is True

    code_r, res = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l9_reason", "query": "program rtl/programs/loader.hasm"},
    )
    assert code_r == 200
    assert res["record"]["conclusion"]["verdict"] == "PROVEN"
    assert "RESUMES pc:0x040" in res["record"]["conclusion"]["statement"]
    assert res["verification"]["valid"] is True


def test_desktop_l10_autonomous_engineering_integration(
    desktop_app: NUILocalServiceApp, tmp_path: Path
) -> None:
    """Verifies NUI Desktop can run L10 H-ISA synthesis (4 oracles) and sandbox Python repair while blocking Immutable Core."""
    code_s, s = desktop_app.dispatch_request("GET", "/api/layers/canonical?layer=L10")
    assert code_s == 200
    assert s["layer"] == "L10"
    assert s["canonical_synthesis_verified"] is True
    assert s["immutable_core_guard_active"] is True

    code_h, syn = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l10_engineer_hasm", "letters": ["ب", "س", "م"]},
    )
    assert code_h == 200
    assert syn["record"]["status"] == "VALIDATED"
    assert syn["record"]["artifact"]["printed_outputs"] == [112]
    assert syn["verification"]["valid"] is True
    assert syn["verification"]["all_oracles_passed"] is True

    # Verify Immutable Core blocking through Desktop API
    core_file = REPO_ROOT / "src" / "hijaiyyah" / "core" / "master_table.py"
    dummy_test = tmp_path / "test_noop.py"
    dummy_test.write_text("def test_noop(): assert True\n", encoding="utf-8")
    code_b, blocked = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {
            "op": "l10_engineer_python",
            "target_file": str(core_file),
            "test_file": str(dummy_test),
            "patch_code": "# blocked\n",
            "goal": "Attempt protected edit",
        },
    )
    assert code_b == 200
    assert blocked["record"]["status"] == "BLOCKED_BY_PERMISSION"
    assert blocked["record"]["artifact"]["mutated"] is False


def test_desktop_l11_universal_computation_and_interlayer_trace_and_logging(
    desktop_app: NUILocalServiceApp,
) -> None:
    """Verifies NUI Desktop can run L11 11-junction Universal Computation, trace inter-layer links, and record action logs."""
    code_s, s = desktop_app.dispatch_request("GET", "/api/layers/canonical?layer=L11")
    assert code_s == 200
    assert s["layer"] == "L11"
    assert s["all_junctions_passed"] is True
    assert s["chain_verified"] is True

    code_u, univ = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l11_execute_chain", "run_rtl": False},
    )
    assert code_u == 200
    assert univ["record"]["all_junctions_passed"] is True
    assert univ["record"]["outputs"] == [10, 6, 4, 112, 9]
    assert univ["record"]["hardware_claim_guard"] == "NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION"
    assert univ["verification"]["valid"] is True

    # Trace inter-layer relationships L0 -> L11
    code_tr, tr = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "trace_interlayer", "subject": "PRINT"},
    )
    assert code_tr == 200
    assert tr["subject"] == "PRINT"
    assert len(tr["interlayer_chain"]) == 12

    # Check action log recorded all L8–L11 invocations and their verification results
    code_log, log_data = desktop_app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "action_log"},
    )
    assert code_log == 200
    assert log_data["total_logged_actions"] >= 4
    logged_layers = {entry["layer"] for entry in log_data["actions"]}
    assert {"L8", "L9", "L10", "L11"}.issubset(logged_layers)
