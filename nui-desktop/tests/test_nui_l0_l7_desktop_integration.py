"""End-to-End Integration Tests for CosmicTera NUI Desktop Canonical Layers L0–L7 (Phases 2 & 3).

Verifies that NUI Desktop (`NUILocalServiceApp`, `NativeNUIProvider`, `NUIToolRegistry`,
and `CanonicalLayersBridge`) directly invokes the canonical `src/hijaiyyah/nui/` modules:
- L0 (`facts.py`, `features.py`, `atom.py`, `claims.py`)
- L1 (`repository_index.py`, `repository_graph.py`)
- L2 (`program_index.py`, `program_graph.py`, `program_summary.py`)
- L3 (`execution_trace.py`, `execution_graph.py`)
- L4 (`parity_model.py`, `board_parity.py`, `layer4_freeze.py` — read-only, non-hardcoded)
- L5 (`layer5.py`, `layer5_freeze.py` — read-only, 300s freshness & kworker separation)
- L6 (`hardware_state.py`, `rtl_function.py`, `telemetry_sources.py`, `layer6_addendum.py` — 0 LIVE)
- L7 (`layer7.py`, `layer7_decision.py`, `layer7_portal.py`, `layer7_linux.py` — fail-closed gate)
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = NUI_DESKTOP_ROOT.parent
SRC_DIR = REPO_ROOT / "src"

for p in (str(NUI_DESKTOP_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.server import NUILocalServiceApp


@pytest.fixture(scope="module")
def app(tmp_path_factory: pytest.TempPathFactory) -> NUILocalServiceApp:
    db_file = tmp_path_factory.mktemp("nui_l0_l7") / "test_nui_l0_l7.db"
    return NUILocalServiceApp(db_path=db_file, use_os_keychain=False)


def test_phase2_l0_canonical_facts_features_atom_and_claims(app: NUILocalServiceApp) -> None:
    """Phase 2.1: L0 adapter connects facts.py, features.py, atom.py, and claims.py to NUI Desktop."""
    code, l0_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L0")
    assert code == 200
    assert l0_ov["layer"] == "L0"
    assert l0_ov["sealed_facts_total"] == 27
    assert sum(l0_ov["evidence_tag_counts"].values()) == 27
    assert l0_ov["verification_kind_counts"]["derive"] == 10
    assert l0_ov["verification_kind_counts"]["pytest"] == 9
    assert l0_ov["verification_kind_counts"]["board"] == 8
    assert l0_ov["jim_kha_sum_5d"] == [2, 2, 2, 6, 6]
    assert l0_ov["address_unification_28_letters_verified"] is True
    assert l0_ov["angle_claims_count"] == 7

    # Inspect atom unification for all 28 letters
    code_u, unif = app.dispatch_request("POST", "/api/layers/query", {"op": "l0_address_unification"})
    assert code_u == 200
    assert unif["total_letters"] == 28
    assert unif["all_28_unified"] is True
    alif_entry = unif["entries"][0]
    assert alif_entry["name"] == "Alif"
    assert alif_entry["master_table_index"] == 1
    assert alif_entry["hisa_opcode_hex"] == "0xE0"
    assert alif_entry["hcpu_rom_address"] == 1
    assert alif_entry["embedding_row"] == 0
    assert alif_entry["unified"] is True

    # Inspect angle claims (7 claims checked against Master Table: 2 verified, 5 falsified)
    code_c, claims = app.dispatch_request("POST", "/api/layers/query", {"op": "l0_claims"})
    assert code_c == 200
    assert claims["claim_count"] == 7
    assert claims["verified_count"] == 2
    assert claims["falsified_count"] == 5


def test_phase2_l1_canonical_repository_graph_and_impact(app: NUILocalServiceApp) -> None:
    """Phase 2.2: L1 adapter invokes canonical repository_index.py and repository_graph.py."""
    code, l1_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L1")
    assert code == 200
    assert l1_ov["layer"] == "L1"
    assert l1_ov["total_files"] >= 1800
    assert l1_ov["graph_nodes"] >= 1800
    assert l1_ov["graph_edges"] >= 4600
    for edge_kind in ("defines", "imports", "mentions", "references", "verifies"):
        assert l1_ov["edge_kinds"].get(edge_kind, 0) > 0

    code_imp, impact = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l1_impact", "path": "src/hijaiyyah/hisa/machine.py"},
    )
    assert code_imp == 200
    assert impact["target_path"] == "src/hijaiyyah/hisa/machine.py"
    assert impact["incoming_count"] > 0
    assert impact["outgoing_count"] > 0
    assert len(impact["verifying_tests"]) > 0
    assert len(impact["impact_tests"]) > 0


def test_phase2_l2_canonical_program_index_graph_and_summary(app: NUILocalServiceApp) -> None:
    """Phase 2.3: L2 adapter invokes canonical program_index.py, program_graph.py, and program_summary.py."""
    code, l2_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L2")
    assert code == 200
    assert l2_ov["layer"] == "L2"
    assert l2_ov["hasm_program_count"] == 62
    assert l2_ov["verilog_module_count"] >= 128
    assert l2_ov["python_function_count"] >= 1500
    assert l2_ov["unresolved_hasm_calls"] == 0
    assert l2_ov["unresolved_verilog_instances"] == 0

    code_exp, exp_v = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l2_explain", "target": "rtl/hcpu_top.v"},
    )
    assert code_exp == 200
    assert exp_v["kind"] == "verilog"
    assert exp_v["name"] == "hcpu_top"
    assert "hcpu_execute" in exp_v["instantiates"]

    code_hasm, exp_h = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l2_explain", "target": "rtl/programs/test_bsm.hasm"},
    )
    assert code_hasm == 200
    assert exp_h["kind"] == "hasm"
    assert exp_h["words"] > 0
    assert exp_h["halts"] is True


def test_phase2_l3_canonical_execution_trace_and_graph(app: NUILocalServiceApp) -> None:
    """Phase 2.4: L3 adapter invokes canonical execution_trace.py & execution_graph.py (ENTRY -> STEP -> CHANGE -> EXIT)."""
    code, l3_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L3")
    assert code == 200
    assert l3_ov["layer"] == "L3"
    assert l3_ov["sealed_execution_runs"] == 63
    assert l3_ov["sealed_halted_runs"] == 43
    assert l3_ov["sealed_causal_edges"] >= 1478

    code_tr, trace_out = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l3_trace", "program": "rtl/programs/test_bsm.hasm"},
    )
    assert code_tr == 200
    assert trace_out["halted"] is True
    assert trace_out["output"] == [112]
    assert trace_out["graph_node_kinds"]["ENTRY"] == 1
    assert trace_out["graph_node_kinds"]["EXIT"] == 1
    assert trace_out["graph_node_kinds"]["STEP"] == trace_out["steps_executed"]
    assert trace_out["graph_node_kinds"].get("CHANGE", 0) > 0
    assert len(trace_out["mmio_writes"]) >= 1
    assert trace_out["mmio_writes"][0]["value"] == 112


def test_phase3_l4_readonly_parity_adapter_honest_metrics(app: NUILocalServiceApp) -> None:
    """Phase 3.1: L4 read-only adapter reads layer4_freeze.json & parity_model.json honestly without hardcoding."""
    code, l4_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L4")
    assert code == 200
    assert l4_ov["layer"] == "L4"
    assert l4_ov["read_only"] is True
    assert l4_ov["freeze_verified_ok"] is True
    assert l4_ov["freeze_tag"] == "layer4-freeze-2026-09-26"

    # P2 Board Parity (73 PARITY, 2 MISMATCH, 28 UNKNOWN)
    assert l4_ov["p2_board_parity_counts"]["PARITY"] == 73
    assert l4_ov["p2_board_parity_counts"]["MISMATCH"] == 2
    assert l4_ov["p2_board_parity_counts"]["UNKNOWN"] == 28
    assert len(l4_ov["p2_board_mismatches"]) == 2
    assert any("e4_frame.hasm" in m for m in l4_ov["p2_board_mismatches"])
    assert any("test_hisab.hasm" in m for m in l4_ov["p2_board_mismatches"])

    # P3 Three-Way Opcode Parity in layer4_freeze.json (74 PARITY, 0 MISMATCH, 31 UNKNOWN)
    assert l4_ov["p3_three_way_opcode_counts"]["PARITY"] == 74
    assert l4_ov["p3_three_way_opcode_counts"]["MISMATCH"] == 0
    assert l4_ov["p3_three_way_opcode_counts"]["UNKNOWN"] in {29, 31}


def test_phase3_l5_readonly_host_observation_adapter(app: NUILocalServiceApp) -> None:
    """Phase 3.2: L5 read-only adapter reads layer5_freeze.json with 300s freshness & kworker separation."""
    code, l5_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L5")
    assert code == 200
    assert l5_ov["layer"] == "L5"
    assert l5_ov["read_only"] is True
    assert l5_ov["freeze_verified_ok"] is True
    assert l5_ov["freshness_window_seconds"] == 300
    assert l5_ov["kworker_separated_from_user_processes"] is True
    assert l5_ov["frozen_snapshot_summary"]["hostname"] == "lima-hijaiyyah"
    assert l5_ov["frozen_snapshot_summary"]["collector_counts"]["OBSERVED"] == 9
    assert l5_ov["frozen_snapshot_summary"]["collector_counts"]["UNAVAILABLE"] == 2


def test_phase3_l6_readonly_hardware_state_and_rtl_function(app: NUILocalServiceApp) -> None:
    """Phase 3.3: L6 read-only adapter enforces LIVE > MEASURED > SIMULATED > UNKNOWN and 0 LIVE sources."""
    code, l6_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L6")
    assert code == 200
    assert l6_ov["layer"] == "L6"
    assert l6_ov["read_only"] is True
    assert l6_ov["freeze_verified_ok"] is True
    assert l6_ov["addendum_verified_ok"] is True
    assert l6_ov["live_telemetry_source_count"] == 0
    assert l6_ov["hierarchy_order"] == ["LIVE", "MEASURED", "SIMULATED", "UNKNOWN"]
    assert l6_ov["current_query_when_no_live"]["status"] == "UNKNOWN"
    assert l6_ov["measured_query_example"]["status"] == "MEASURED"
    assert l6_ov["simulated_query_example"]["status"] == "SIMULATED"
    assert l6_ov["rtl_function_total_tests"] == 104
    assert l6_ov["rtl_function_passed_tests"] == 104

    code_sim, rtl_sim = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l6_rtl_sim", "program": "test_bsm.hasm", "max_cycles": 64},
    )
    assert code_sim == 200
    assert rtl_sim["halted"] is True
    assert rtl_sim["R1"] == 112
    assert rtl_sim["evidence_class"] == "SIMULATED"


def test_phase3_l7_canonical_fail_closed_gate_and_fault_isolation(app: NUILocalServiceApp) -> None:
    """Phase 3.4: L7 adapter invokes layer7.evaluate, layer7_decision.decide, layer7_portal.isolate, and layer7_linux.isolate."""
    code, l7_ov = app.dispatch_request("GET", "/api/layers/canonical?layer=L7")
    assert code == 200
    assert l7_ov["layer"] == "L7"
    assert l7_ov["sample_allow_decision"]["decision"] == "ALLOW"
    assert l7_ov["sample_allow_decision"]["sha256_verified"] is True
    assert l7_ov["sample_deny_decision"]["decision"] == "DENY"
    assert l7_ov["sample_deny_decision"]["sha256_verified"] is True
    assert l7_ov["sample_stop_report_decision"]["decision"] == "STOP / REPORT"
    assert l7_ov["sample_stop_report_decision"]["sha256_verified"] is True

    # Test L7 gate blocking prohibited FLASH_WRITE via NUIToolRegistry when enforce_l7_gate=True
    app.permissions.set_rule(
        category="CODE_EXECUTION",
        target_type="subsystem",
        target_value="TANG_NANO_20K",
        operation="*",
        decision="ALWAYS_ALLOW",
    )
    blocked = app.tools.execute_tool(
        "hardware.control",
        {
            "subsystem": "TANG_NANO_20K",
            "action": "S1_STOP",
            "l7_operation": "FLASH_WRITE",
            "l7_domain": "HARDWARE",
            "enforce_l7_gate": True,
        },
        user_request="Attempt prohibited flash write",
    )
    assert blocked["ok"] is False
    assert blocked["status"] == "DENY"
    assert blocked["decision_source"] == "CANONICAL_L7_FAIL_CLOSED_GATE"
    assert blocked["l7_gate"]["decision"]["sha256_verified"] is True

    # Test Portal 8888 fault isolation (ADAPTER_ABSENT vs BOARD_NOT_DETECTED)
    code_p1, p_absent = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l7_portal_isolate", "has_usb_device": False, "jtag_detected": False},
    )
    assert code_p1 == 200
    assert p_absent["fault_class"] == "ADAPTER_ABSENT"
    assert p_absent["decision"] == "STOP / REPORT"

    code_p2, p_nobrd = app.dispatch_request(
        "POST",
        "/api/layers/query",
        {"op": "l7_portal_isolate", "has_usb_device": True, "jtag_detected": False},
    )
    assert code_p2 == 200
    assert p_nobrd["fault_class"] == "BOARD_NOT_DETECTED"
    assert p_nobrd["decision"] == "STOP / REPORT"
