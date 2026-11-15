"""Unit and E2E tests for NUI Layer 10 — Autonomous Engineering (`src/hijaiyyah/nui/autonomous/layer10_engineering.py`)."""
from __future__ import annotations

from pathlib import Path

from hijaiyyah.nui.autonomous.layer10_engineering import (
    ENGINEERING_STAGES,
    REQUIRED_ORACLES,
    check_immutable_target,
    engineer_hasm_program,
    engineer_python_sandbox_patch,
    summary,
    verify_engineering,
)


def test_l10_hasm_program_synthesis_passes_all_four_oracles() -> None:
    """Synthesizes an H-ISA program via the 8-stage pipeline and verifies all 4 canonical oracles."""
    rec = engineer_hasm_program(letters=("ب", "س", "م"))
    assert rec.status == "VALIDATED"
    assert rec.pipeline_stages == ENGINEERING_STAGES
    assert [s["stage"] for s in rec.stage_log] == list(ENGINEERING_STAGES)
    assert set(rec.oracles.keys()) == set(REQUIRED_ORACLES)
    for oracle_name, oracle_res in rec.oracles.items():
        assert oracle_res["passed"] is True, f"Oracle {oracle_name} failed: {oracle_res}"

    # Ba + Sin + Mim norm2 is 112
    assert rec.artifact["expected_bsm"] == 112
    assert rec.artifact["printed_outputs"] == [112]
    assert verify_engineering(rec)["valid"] is True


def test_l10_python_sandbox_patch_and_pytest_verification(tmp_path: Path) -> None:
    """Runs the 8-stage engineering loop on a broken Python module in an authorized sandbox."""
    mod_file = tmp_path / "calc_mod.py"
    test_file = tmp_path / "test_calc_mod.py"

    mod_file.write_text(
        "def hitung_bsm_sederhana(a: int, b: int) -> int:\n    return a - b\n",
        encoding="utf-8",
    )
    test_file.write_text(
        "from calc_mod import hitung_bsm_sederhana\n\n"
        "def test_hitung():\n"
        "    assert hitung_bsm_sederhana(70, 42) == 112\n",
        encoding="utf-8",
    )

    good_patch = "def hitung_bsm_sederhana(a: int, b: int) -> int:\n    return a + b\n"
    rec = engineer_python_sandbox_patch(
        target_file=mod_file,
        test_file=test_file,
        patch_code=good_patch,
        goal="Fix subtraction bug in hitung_bsm_sederhana",
    )
    assert rec.status == "VALIDATED"
    assert verify_engineering(rec)["valid"] is True
    assert mod_file.read_text(encoding="utf-8") == good_patch


def test_l10_immutable_core_and_frozen_artifacts_strictly_blocked(tmp_path: Path) -> None:
    """Verifies L10 blocks any attempt to modify core math, H-ISA, RTL, frozen L4-L7 files, or the 4 HDMI files."""
    for protected in (
        "src/hijaiyyah/core/master_table.py",
        "src/hijaiyyah/hisa/machine.py",
        "rtl/hcpu_top.v",
        "NUI/layer4_freeze.json",
        "NUI/LAYERS.md",
        "rtl/fpga/gowin/hcpu_hdmi_top.v",
    ):
        chk = check_immutable_target(protected, explicit_owner_approval=False)
        assert chk["allowed"] is False

    # Even with explicit_owner_approval=True, frozen and HDMI files remain blocked
    hdmi_chk = check_immutable_target("rtl/fpga/gowin/hcpu_hdmi_top.v", explicit_owner_approval=True)
    assert hdmi_chk["allowed"] is False
    assert hdmi_chk["status"] == "BLOCKED_FROZEN_OR_PROTECTED_ARTIFACT"

    # Attempting to run engineer_python_sandbox_patch on a protected core file is blocked without touching the file
    core_path = Path(__file__).resolve().parents[2] / "src" / "hijaiyyah" / "core" / "master_table.py"
    before_bytes = core_path.read_bytes()
    dummy_test = tmp_path / "test_dummy.py"
    dummy_test.write_text("def test_ok(): assert True\n", encoding="utf-8")

    blocked_rec = engineer_python_sandbox_patch(
        target_file=core_path,
        test_file=dummy_test,
        patch_code="# unauthorized overwrite\n",
        goal="Attempt unauthorized core overwrite",
    )
    assert blocked_rec.status == "BLOCKED_BY_PERMISSION"
    assert blocked_rec.artifact["mutated"] is False
    assert core_path.read_bytes() == before_bytes
    assert verify_engineering(blocked_rec)["valid"] is True


def test_l10_sabotage_skipped_search_or_failed_oracle_rejected() -> None:
    """R3 sabotage check: skipping 1_SEARCH or marking VALIDATED with a failed oracle is rejected."""
    rec = engineer_hasm_program()
    assert verify_engineering(rec)["valid"] is True

    # Sabotage 1: Remove 1_SEARCH from stage_log (building without searching first)
    bad_stages = rec.to_dict()
    bad_stages["stage_log"] = bad_stages["stage_log"][1:]
    v1 = verify_engineering(bad_stages)
    assert v1["valid"] is False
    assert v1["stages_complete"] is False

    # Sabotage 2: Failed oracle but status claims VALIDATED
    bad_oracle = rec.to_dict()
    bad_oracle["oracles"]["FOUR_GUARDS_ORACLE"]["passed"] = False
    v2 = verify_engineering(bad_oracle)
    assert v2["valid"] is False
    assert v2["all_oracles_passed"] is False

    s = summary()
    assert s["layer"] == 10
    assert s["canonical_synthesis_verified"] is True
    assert s["immutable_core_guard_active"] is True
