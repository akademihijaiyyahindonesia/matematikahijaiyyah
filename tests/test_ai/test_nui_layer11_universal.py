"""Unit and E2E tests for NUI Layer 11 — Universal Computation (`src/hijaiyyah/nui/autonomous/layer11_universal.py`)."""
from __future__ import annotations

from hijaiyyah.nui.autonomous.layer11_universal import (
    JUNCTION_IDS,
    execute_universal_chain,
    summary,
    verify_universal_chain,
)


def test_l11_universal_chain_executes_all_11_junction_oracles() -> None:
    """L11 exit criterion: every junction J01..J11 across L0..L11 runs an executable oracle and passes."""
    rec = execute_universal_chain(run_rtl=False)
    assert rec.all_junctions_passed is True
    assert rec.junction_ids == JUNCTION_IDS
    assert len(rec.junctions) == 11
    for j in rec.junctions:
        assert j["passed"] is True, f"Junction {j['junction_id']} failed: {j}"
        assert len(j["measurements"]) >= 2

    assert rec.outputs == [10, 6, 4, 112, 9]
    assert rec.expected_outputs == [10, 6, 4, 112, 9]
    assert rec.verify_4b_prime_ok is True
    assert rec.native_letter_opcodes_emitted == 3
    assert rec.peak_gpr_used <= 15
    assert rec.hardware_claim_guard == "NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION"
    assert rec.epistemic_status == "VF"

    ver = verify_universal_chain(rec)
    assert ver["valid"] is True


def test_l11_hc_compat_surface_through_universal_chain() -> None:
    """Verifies `.hc` compatibility source also executes through the full L0–L11 universal chain."""
    hc_src = """
    let b = 'ب';
    let s = 'س';
    let m = 'م';
    let bsm = b + s + m;
    bsm.guard();
    println(bsm.theta());
    println(bsm.U());
    println(bsm.rho());
    println(bsm.norm2());
    println(b.dist2(m));
    """
    rec = execute_universal_chain(
        hc_src,
        is_hc_compat=True,
        expected_outputs=[10, 6, 4, 112, 9],
        run_rtl=False,
    )
    assert rec.all_junctions_passed is True
    assert rec.outputs == [10, 6, 4, 112, 9]
    assert verify_universal_chain(rec)["valid"] is True


def test_l11_sabotage_broken_junction_or_false_hardware_claim_rejected() -> None:
    """R3 sabotage check: a failed junction, tampered junction digest, or false live hardware claim is rejected."""
    rec = execute_universal_chain(run_rtl=False)
    assert verify_universal_chain(rec)["valid"] is True

    # Sabotage 1: Tamper with a junction's measurements without updating its oracle_sha256
    bad_j = rec.to_dict()
    bad_j["junctions"][5]["measurements"]["live_sources_count"] = 99
    v1 = verify_universal_chain(bad_j)
    assert v1["valid"] is False
    assert "J06_L5_TO_L6" in v1["tampered_junctions"]

    # Sabotage 2: Claim LIVE_HARDWARE from a simulated run
    bad_hw = rec.to_dict()
    bad_hw["epistemic_status"] = "LIVE_HARDWARE"
    v2 = verify_universal_chain(bad_hw)
    assert v2["valid"] is False
    assert v2["honest_epistemic_guard"] is False

    s = summary(run_rtl=False)
    assert s["layer"] == 11
    assert s["chain_verified"] is True
    assert s["all_junctions_passed"] is True
