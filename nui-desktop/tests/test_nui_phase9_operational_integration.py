"""
COSMICTERA NUI — PHASE 9: UNIFIED OPERATIONAL INTELLIGENCE INTEGRATION TESTS
=============================================================================
Menguji integrasi operasional penuh L0–L11, Local Ollama LLM roles,
Hijaiyyah Mathematical Intelligence, 12-Step Autonomous Engineering Workflow,
Immutable Core Protection, Reliability/Recovery, Multi-Turn Follow-ups,
serta Live Acceptance Scenarios A–J.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

for p in (str(NUI_DESKTOP_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.operational_intelligence import (
    OPERATIONAL_CYCLE_STAGES,
    OPERATIONAL_INTENTS,
    UnifiedOperationalIntelligence,
)
from backend.server import NUILocalServiceApp


@pytest.fixture(scope="module")
def phase9_app(tmp_path_factory: pytest.TempPathFactory) -> NUILocalServiceApp:
    db_file = tmp_path_factory.mktemp("phase9") / "phase9_test.db"
    return NUILocalServiceApp(db_path=db_file, use_os_keychain=False)


def test_phase9_operational_intents_and_11_stage_cycle(phase9_app: NUILocalServiceApp) -> None:
    """Verifikasi 9 kelas intent operasional dan siklus 11 tahap (UNDERSTAND -> LEARN)."""
    assert len(OPERATIONAL_INTENTS) == 9
    assert len(OPERATIONAL_CYCLE_STAGES) == 11
    assert OPERATIONAL_CYCLE_STAGES[0] == "UNDERSTAND"
    assert OPERATIONAL_CYCLE_STAGES[-1] == "LEARN"

    status_code, status_payload = phase9_app.dispatch_request("GET", "/api/phase9/status")
    assert status_code == 200
    assert status_payload["phase"] == "PHASE_9_UNIFIED_OPERATIONAL_INTELLIGENCE"
    assert len(status_payload["layers_live_matrix"]) == 12
    assert all(
        item["status"] in ("IMPLEMENTED_AND_VERIFIED", "FROZEN_WITH_KNOWN_GAPS")
        for item in status_payload["layers_live_matrix"]
    )


def test_scenario_a_and_b_natural_conversation_and_coding(phase9_app: NUILocalServiceApp) -> None:
    """
    Scenario A — Natural Conversation: tidak menyuntikkan fakta watchdog/clock drift.
    Scenario B — General Software Engineering: menghasilkan rencana & memilih spesialis coding.
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Scenario A & B")["session_id"]

    res_a = uoi.execute_operational_cycle("Halo NUI, apa kabar hari ini?", sess_id)
    assert res_a["operational_intent"] == "GENERAL_CONVERSATION"
    assert res_a["cycle_stages_completed"] == list(OPERATIONAL_CYCLE_STAGES)
    assert "watchdog" not in res_a["verified_context_block"].lower()
    assert "clock_drift" not in res_a["verified_context_block"].lower()

    res_b = uoi.execute_operational_cycle(
        "Tolong perbaiki bug fungsi skala di sandbox menggunakan workflow rekayasa otonom L10.",
        sess_id,
    )
    assert res_b["operational_intent"] == "SOFTWARE_ENGINEERING"
    roles = res_b["plan"]["model_roles"]["roles"]
    assert "Planner" in roles and "Specialist" in roles and "Reviewer" in roles and "Validator" in roles


def test_scenario_c_cosmictera_knowledge_and_epistemic_rules(phase9_app: NUILocalServiceApp) -> None:
    """
    Scenario C — CosmicTera Architecture: menjelaskan L0–L11 dan membedakan DP = Design Property
    (bukan Dynamic Programming).
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Scenario C")["session_id"]

    res_c = uoi.execute_operational_cycle(
        "Jelaskan arsitektur NUI L0 sampai L11 dan aturan epistemik CosmicTera!",
        sess_id,
    )
    assert res_c["operational_intent"] in ("MULTI_LAYER_REASONING", "COSMICTERA_KNOWLEDGE")
    assert "Design Property" in res_c["verified_context_block"]
    assert "BUKAN Dynamic Programming" in res_c["verified_context_block"]
    lm = res_c["knowledge_bundle"]["layers_live_matrix"]
    assert lm["total_layers"] == 12
    assert lm["implemented_count"] == 12


def test_scenario_d_hijaiyyah_mathematical_intelligence(phase9_app: NUILocalServiceApp) -> None:
    """
    Scenario D — Hijaiyyah Mathematical Computation:
    Natural Language -> Mathematical Intent -> Canonical Formula ->
    Deterministic Computation -> Independent Validation -> Explanation.
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Scenario D")["session_id"]

    res_d = uoi.execute_operational_cycle(
        "Hitung vektor Hybit 18D, koordinat 5D, dan jarak intim untuk huruf Jim dan Kha!",
        sess_id,
    )
    assert res_d["operational_intent"] == "MATHEMATICAL_COMPUTATION"
    mc = res_d["knowledge_bundle"]["mathematical_computation"]
    assert mc["primary_letter"]["name"] == "Jim"
    assert mc["secondary_letter"]["name"] == "Kha"
    assert mc["primary_letter"]["features_5d"] == [1, 1, 1, 3, 3]
    assert mc["secondary_letter"]["features_5d"] == [1, 1, 1, 3, 3]
    assert mc["pair_operations"]["sum_5d_features"] == [2, 2, 2, 6, 6]
    assert mc["bsm_canonical_reference"]["bsm_an_norm_squared"] == 112
    assert mc["bsm_canonical_reference"]["bsm_full_18d_norm_squared"] == 142
    assert mc["bsm_canonical_reference"]["l11_junctions_passed"] == 11
    assert mc["independent_validation"]["passed"] is True


def test_scenario_e_and_f_l8_diagnostics_and_l9_reasoning(phase9_app: NUILocalServiceApp) -> None:
    """
    Scenario E — L8 Self-Diagnostics: mendiagnosa anomali dengan verifikasi SHA-256.
    Scenario F — L9 Deductive Reasoning: menyusun rantai deduksi berbasis bukti L0–L7.
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Scenario E & F")["session_id"]

    res_e = uoi.execute_operational_cycle(
        "Jalankan diagnostik sistem L8 untuk memeriksa kesehatan layanan dan anomali.",
        sess_id,
    )
    assert res_e["operational_intent"] == "SYSTEM_DIAGNOSTICS"
    d8 = res_e["knowledge_bundle"]["l8_diagnostics"]
    assert d8["verification"]["valid"] is True
    assert d8["total_known_anomalies_scanned"] >= 5

    res_f = uoi.execute_operational_cycle(
        "Gunakan penalaran deduktif Layer 9 dan rantai L11 untuk membuktikan properti H-ISA.",
        sess_id,
    )
    assert res_f["operational_intent"] == "MULTI_LAYER_REASONING"
    assert res_f["knowledge_bundle"]["l9_verification"]["valid"] is True
    assert res_f["knowledge_bundle"]["l11_verification"]["valid"] is True


def test_scenario_g_and_h_hardware_realism_and_l10_engineering(phase9_app: NUILocalServiceApp) -> None:
    """
    Scenario G — Hardware Realism: memisahkan LIVE > MEASURED > SIMULATED > UNKNOWN tanpa klaim palsu.
    Scenario H — L10 Autonomous Engineering: menjalankan 12 langkah di sandbox dengan 4 oracle & L11 check.
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Scenario G & H")["session_id"]

    res_g = uoi.execute_operational_cycle(
        "Bagaimana status perangkat keras FPGA Tang Nano 9K dan sinyal HDMI saat ini?",
        sess_id,
    )
    assert res_g["operational_intent"] == "HARDWARE_ANALYSIS"
    hw = res_g["knowledge_bundle"]["hardware_analysis"]
    assert hw["precedence_rule"] == "LIVE > MEASURED > SIMULATED > UNKNOWN"
    assert len(hw["protected_hdmi_files"]) == 4

    res_h = uoi.execute_operational_cycle(
        "Jalankan rekayasa otonom Layer 10 di sandbox untuk memperbaiki fungsi skala BSM.",
        sess_id,
    )
    assert res_h["operational_intent"] == "SOFTWARE_ENGINEERING"
    ae = res_h["knowledge_bundle"]["autonomous_engineering"]
    assert ae["status"] == "COMPLETED"
    assert ae["decision"] == "ACCEPT_IN_SANDBOX"
    assert ae["steps_completed"] == 12
    assert ae["l11_impact"]["passed_junctions"] == 11


def test_scenario_i_and_j_l11_universal_and_immutable_core_protection(phase9_app: NUILocalServiceApp) -> None:
    """
    Scenario I — L11 Universal Computation: 11/11 sambungan PASS.
    Scenario J — Permission & Immutable Core Protection: menolak modifikasi 43 modul kanonik.
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Scenario I & J")["session_id"]

    res_i = uoi.execute_operational_cycle(
        "Verifikasi 11 sambungan rantai komputasi universal Layer 11 untuk BSM!",
        sess_id,
    )
    assert res_i["operational_intent"] == "MULTI_LAYER_REASONING"
    u11 = res_i["knowledge_bundle"]["l11_universal_chain"]
    assert u11["all_junctions_passed"] is True
    assert len(u11["junctions"]) == 11

    target_mod = "/".join(["src", "hijaiyyah", "nui", "facts.py"])
    prompt_j = f"Tolong ubah isi {target_mod} sekarang."
    code, turn_j = phase9_app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sess_id, "user_message": prompt_j, "provider": "native_nui"},
    )
    assert code == 200
    assert "DITOLAK" in turn_j["response_text"]
    assert "IMMUTABLE_CORE_PROTECTION" in turn_j["response_text"]
    p9_meta = turn_j["data"]["phase9_operational"]
    assert p9_meta["permission_decision"] == "DENY_IMMUTABLE_CORE"


def test_phase9_multi_turn_follow_ups_and_reliability(phase9_app: NUILocalServiceApp) -> None:
    """
    Menguji ke-5 kalimat tindak lanjut multi-turn dan fitur Reliability/Recovery Phase 9.7.
    """
    uoi: UnifiedOperationalIntelligence = phase9_app.operational_intelligence
    sess_id = phase9_app.storage.create_session(title="Multi-Turn & Reliability")["session_id"]

    r1 = uoi.execute_operational_cycle("Hitung koordinat 5D untuk huruf Jim dan Kha!", sess_id)
    assert r1["operational_intent"] == "MATHEMATICAL_COMPUTATION"

    f1 = uoi.execute_operational_cycle("Tunjukkan sumbernya.", sess_id)
    assert f1["follow_up_type"] == "SHOW_SOURCE"
    assert "src/hijaiyyah/nui/features.py" in f1["knowledge_bundle"]["verified_sources"]

    f2 = uoi.execute_operational_cycle("Kenapa hasilnya berbeda?", sess_id)
    assert f2["follow_up_type"] == "WHY_DIFFERENT"
    assert "discrepancy_analysis" in f2["knowledge_bundle"]

    f3 = uoi.execute_operational_cycle("Apa dampaknya?", sess_id)
    assert f3["follow_up_type"] == "WHAT_IMPACT"
    assert f3["knowledge_bundle"]["impact_analysis"]["l11_11junction_integrity"] == "11/11 PASS"

    f4 = uoi.execute_operational_cycle("Jalankan lagi.", sess_id)
    assert f4["follow_up_type"] == "RUN_AGAIN"
    assert f4["knowledge_bundle"]["rerun_result"]["independent_validation"]["passed"] is True

    f5 = uoi.execute_operational_cycle("Perbaiki.", sess_id)
    assert f5["follow_up_type"] == "FIX_IT"
    assert f5["operational_intent"] == "SOFTWARE_ENGINEERING"
    assert f5["knowledge_bundle"]["autonomous_engineering"]["decision"] == "ACCEPT_IN_SANDBOX"

    fresh = uoi.reliability.evaluate_evidence_freshness(time.time() - 10.0)
    assert fresh["freshness_status"] == "LIVE_VERIFIED"
    assert fresh["is_stale"] is False

    stale = uoi.reliability.evaluate_evidence_freshness(time.time() - 450.0)
    assert stale["freshness_status"] == "STALE_EVIDENCE"
    assert stale["is_stale"] is True

    dup1 = uoi.reliability.check_duplicate_mutative_action("write:sandbox/x.py", is_mutative=True)
    dup2 = uoi.reliability.check_duplicate_mutative_action("write:sandbox/x.py", is_mutative=True)
    assert dup1["allowed"] is True
    assert dup2["allowed"] is False
    assert dup2["duplicate_detected"] is True

    ro_retry = uoi.reliability.safe_retry_policy(is_mutative=False, attempt=1)
    mut_retry = uoi.reliability.safe_retry_policy(is_mutative=True, attempt=1)
    assert ro_retry["auto_retry_allowed"] is True
    assert mut_retry["auto_retry_allowed"] is False
