"""Unit and E2E tests for NUI Layer 8 — Autonomous Diagnostics (`src/hijaiyyah/nui/autonomous/layer8_diagnostics.py`)."""
from __future__ import annotations

import pytest

from hijaiyyah.nui.autonomous.layer8_diagnostics import (
    ANOMALY_CLASSES,
    PIPELINE_STAGES,
    REPAIR_BOUNDARIES,
    diagnose,
    diagnose_burnin_log,
    diagnose_traceback,
    scan_all_anomalies,
    summary,
    verify_diagnosis,
)


def test_l8_scan_all_anomalies_without_human_direction() -> None:
    """L8 exit criterion: scans repository and finds all major anomaly classes without being told where to look."""
    records = scan_all_anomalies()
    assert len(records) >= 8

    found_classes = {r.anomaly_class for r in records}
    assert "SILICON_PRINT_CORRUPTION" in found_classes
    assert "POST_STOP_EXECUTION" in found_classes
    assert "SEMANTIC_REGISTER_DIVERGENCE" in found_classes
    assert "OBSERVER_HOST_SLEEP" in found_classes
    assert "RTL_KNOWN_DISCREPANCY" in found_classes
    assert "COMPILER_REGISTER_CEILING" in found_classes
    assert "MATHEMATICAL_CLAIM_FALSIFICATION" in found_classes
    assert "INCOMPLETE_HARDWARE_PROVENANCE" in found_classes

    for rec in records:
        assert rec.pipeline_stages == PIPELINE_STAGES
        assert rec.anomaly_class in ANOMALY_CLASSES
        assert rec.repair_boundary in REPAIR_BOUNDARIES
        assert len(rec.evidence_chain) >= 1
        assert len(rec.reproduction_command) > 5
        v = verify_diagnosis(rec)
        assert v["valid"] is True, f"{rec.diagnosis_id} failed verification: {v}"


def test_l8_diagnose_silicon_print_vs_post_stop_execution() -> None:
    """Separates physical silicon PRINT corruption (OFF-PRINT-SILICON) from RTL post-stop pipeline execution."""
    rec_print = diagnose("OFF-PRINT-SILICON e4_frame.hasm test_hisab.hasm")
    assert rec_print.diagnosis_id == "L8-DIAG-OFF-PRINT-SILICON"
    assert rec_print.anomaly_class == "SILICON_PRINT_CORRUPTION"
    assert rec_print.owner_domain == "SILICON_SYNTHESIS"
    assert rec_print.epistemic_status == "MEASURED"
    assert "rtl/programs/e4_frame.hasm" in rec_print.affected_targets
    assert "rtl/programs/test_hisab.hasm" in rec_print.affected_targets

    rec_stop = diagnose("subroutine.hasm R1=10 after HALT stop-probe")
    assert rec_stop.diagnosis_id == "L8-DIAG-RTL-POST-STOP-EXECUTION"
    assert rec_stop.anomaly_class == "POST_STOP_EXECUTION"
    assert rec_stop.owner_domain == "RTL_PIPELINE"
    assert len(rec_stop.affected_targets) == 13


def test_l8_diagnose_burnin_distinguishes_host_sleep_from_board_stop() -> None:
    """Proves L8 separates host MacBook sleep/silence from physical board halt using board cycle counter."""
    rec = diagnose_burnin_log()
    assert rec.anomaly_class == "OBSERVER_HOST_SLEEP"
    assert rec.owner_domain == "HOST_OBSERVER_MACOS"
    assert "1.0002" in rec.root_cause
    assert verify_diagnosis(rec)["valid"] is True


def test_l8_diagnose_traceback_maps_to_repository_and_verifying_tests() -> None:
    """Parses a Python traceback and links it to tracked repository file + L1 verifying tests."""
    sample_tb = (
        "Traceback (most recent call last):\n"
        '  File "src/hijaiyyah/hisa/assembler.py", line 45, in assemble\n'
        "    raise ValueError('register R16 is out of range (max R15)')\n"
        "ValueError: register R16 is out of range (max R15)\n"
    )
    rec = diagnose_traceback(sample_tb)
    assert rec.anomaly_class == "PYTHON_RUNTIME_TRACEBACK"
    assert "src/hijaiyyah/hisa/assembler.py" in rec.affected_targets
    assert rec.repair_boundary == "ALLOWED_IN_SANDBOX"
    assert verify_diagnosis(rec)["valid"] is True


def test_l8_tamper_detection_on_diagnosis_record() -> None:
    """R3 sabotage check: mutating any field or citing a nonexistent file invalidates verify_diagnosis()."""
    rec = diagnose("HISAB serialize known_discrepancy")
    assert verify_diagnosis(rec)["valid"] is True

    tampered = rec.to_dict()
    tampered["root_cause"] = "fabricated root cause"
    v_tampered = verify_diagnosis(tampered)
    assert v_tampered["valid"] is False
    assert v_tampered["sha256_match"] is False

    bad_source = rec.to_dict()
    bad_source["evidence_chain"] = [{"source": "nonexistent/fake_file.py:1", "sha256": "00", "detail": "fake"}]
    v_bad_source = verify_diagnosis(bad_source)
    assert v_bad_source["valid"] is False
    assert "nonexistent/fake_file.py" in v_bad_source["missing_sources"]


def test_l8_summary_and_unknown_symptom_honesty() -> None:
    """Unknown symptom is honestly classified as UNKNOWN_ANOMALY rather than guessed."""
    s = summary()
    assert s["layer"] == 8
    assert s["all_records_verified"] is True
    assert s["total_diagnosed_anomalies"] >= 8

    unk = diagnose("gejala fiktif yang tidak pernah ada di repositori xyz987")
    assert unk.anomaly_class == "UNKNOWN_ANOMALY"
    assert unk.epistemic_status == "UNKNOWN"
    assert unk.repair_boundary == "OBSERVATION_ONLY_NO_REPAIR"
    assert verify_diagnosis(unk)["valid"] is True
