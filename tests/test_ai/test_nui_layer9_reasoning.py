"""Unit and E2E tests for NUI Layer 9 — Deductive Reasoning Engine (`src/hijaiyyah/nui/autonomous/layer9_reasoning.py`)."""
from __future__ import annotations

from hijaiyyah.nui.autonomous.layer9_reasoning import (
    CONCLUSION_VERDICTS,
    INFERENCE_RULES,
    REASONING_STAGES,
    canonical_reasoning_suite,
    reason,
    reason_about_exomatrix_tail_claim,
    reason_about_file_impact,
    reason_about_letter_unification,
    reason_about_opcode,
    reason_about_program,
    reason_about_unknown_boundary,
    summary,
    verify_reasoning,
)


def test_l9_canonical_reasoning_suite_and_5_stage_chain() -> None:
    """Every canonical proof executes 1_FACTS -> 2_RELATIONS -> 3_PREMISES -> 4_INFERENCE -> 5_CONCLUSION and verifies."""
    suite = canonical_reasoning_suite()
    assert len(suite) == 8
    for rec in suite:
        assert rec.pipeline_stages == REASONING_STAGES
        assert rec.conclusion["verdict"] in CONCLUSION_VERDICTS
        v = verify_reasoning(rec)
        assert v["valid"] is True, f"{rec.reasoning_id} failed verification: {v}"

    s = summary()
    assert s["layer"] == 9
    assert s["all_proofs_verified"] is True


def test_l9_opcode_parity_vs_silicon_divergence_deduction() -> None:
    """Deductively distinguishes full parity opcode (ADD) from silicon-divergent opcode (PRINT)."""
    add_rec = reason_about_opcode("ADD")
    assert add_rec.conclusion["verdict"] == "PROVEN"
    assert add_rec.inferences[0]["rule"] == "RULE_THREE_ENGINE_PARITY"
    assert verify_reasoning(add_rec)["valid"] is True

    print_rec = reason_about_opcode("PRINT")
    assert print_rec.conclusion["verdict"] == "BOUNDED_BY_KNOWN_DISCREPANCY"
    assert print_rec.inferences[0]["rule"] == "RULE_SILICON_DIVERGENCE_ISOLATION"
    assert verify_reasoning(print_rec)["valid"] is True


def test_l9_program_control_transfer_causality_on_loader() -> None:
    """Deductively proves how loader.hasm transfers control via WRITES TRAP_EPC -> WRITES TRAP_MODE -> RESUMES pc:0x040."""
    loader_rec = reason_about_program("rtl/programs/loader.hasm")
    assert loader_rec.conclusion["verdict"] == "PROVEN"
    assert "RESUMES pc:0x040" in loader_rec.conclusion["statement"]
    assert any(r["kind"] == "RESUMES" for r in loader_rec.relations)
    assert verify_reasoning(loader_rec)["valid"] is True


def test_l9_exomatrix_counterexample_falsification_and_letter_unification() -> None:
    """Proves address unification for Jim and falsifies the tail_one invertibility claim."""
    jim_rec = reason_about_letter_unification("ج")
    assert jim_rec.conclusion["verdict"] == "PROVEN"
    assert "0xE4" in jim_rec.conclusion["statement"]
    assert verify_reasoning(jim_rec)["valid"] is True

    tail_rec = reason_about_exomatrix_tail_claim()
    assert tail_rec.conclusion["verdict"] == "FALSIFIED"
    assert tail_rec.inferences[0]["rule"] == "RULE_EXOMATRIX_COUNTEREXAMPLE_FALSIFICATION"
    assert verify_reasoning(tail_rec)["valid"] is True


def test_l9_reasoning_never_precedes_evidence_on_unknowns() -> None:
    """When evidence is absent (hardware current with 0 LIVE sources or host services), L9 stops at INSUFFICIENT_EVIDENCE_UNKNOWN."""
    hw_cur = reason("hardware current board clock")
    assert hw_cur.conclusion["verdict"] == "INSUFFICIENT_EVIDENCE_UNKNOWN"
    assert hw_cur.conclusion["epistemic_ceiling"] == "UNKNOWN"
    assert len(hw_cur.unknown_boundaries) >= 1
    assert verify_reasoning(hw_cur)["valid"] is True

    host_srv = reason_about_unknown_boundary("host services")
    assert host_srv.conclusion["verdict"] == "INSUFFICIENT_EVIDENCE_UNKNOWN"
    assert verify_reasoning(host_srv)["valid"] is True


def test_l9_sabotage_ungrounded_premise_and_p85_violation_rejected() -> None:
    """R3 sabotage check: ungrounded premises, invalid inference rules, or P8.5 HOST provenance violations are rejected."""
    rec = reason_about_file_impact("src/hijaiyyah/nui/atom.py")
    assert verify_reasoning(rec)["valid"] is True

    # Sabotage 1: Premise without supporting facts or relations
    bad_premise = rec.to_dict()
    bad_premise["premises"][0]["supported_by_facts"] = []
    bad_premise["premises"][0]["supported_by_relations"] = []
    v1 = verify_reasoning(bad_premise)
    assert v1["valid"] is False
    assert "P1" in v1["ungrounded_premises"]

    # Sabotage 2: HOST fact reading from facts/ (violating P8.5)
    bad_p85 = rec.to_dict()
    bad_p85["facts"].append(
        {
            "fact_id": "F99",
            "domain": "HOST",
            "what": "illegal_fact",
            "summary": "illegal",
            "source": "facts/host.json",
        }
    )
    v2 = verify_reasoning(bad_p85)
    assert v2["valid"] is False
    assert "F99" in v2["p85_violations" if "p85_violations" in v2 else "p85_provenance_violations"]
