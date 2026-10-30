"""Phase 1 Tests — Authoritative Master Table Engine & ROM Seal Reconciliation (Priority 0 & 1)."""

from __future__ import annotations

import pytest

from hijaiyyah.cells.dataset_engine import (
    CANONICAL_JSON_SEAL,
    CANONICAL_ROM_252B_SEAL,
    CANONICAL_ROM_504B_ROW_MAJOR_SEAL,
    CANONICAL_ROM_504B_RTL_WORD_BE_SEAL,
    CANONICAL_ROM_SEAL,
    DATASET_ID,
    DOCUMENTED_SOURCE_ERRATA,
    FORBIDDEN_LOOKALIKES,
    MASTER_TABLE_504B_BYTES,
    MASTER_TABLE_ENGINE,
    RECORDED_HB_MANIFEST_SEAL,
    UnicodePolicyError,
    validate_and_normalize_hijaiyyah_text,
)
from hijaiyyah.core.constants import MASTER_TABLE_BYTES, V18_SLOTS
from hijaiyyah.core.master_table import MASTER_TABLE


def test_all_28_entries_and_18d_vectors_match_canonical() -> None:
    records = MASTER_TABLE_ENGINE.records
    assert len(records) == 28
    assert list(V18_SLOTS) == [
        "Θ̂", "Na", "Nb", "Nd",
        "Kp", "Kx", "Ks", "Ka", "Kc",
        "Qp", "Qx", "Qs", "Qa", "Qc",
        "AN", "AK", "AQ", "H*",
    ]
    for idx, (rec, canon) in enumerate(
        zip(records, MASTER_TABLE.all_entries(), strict=True), start=1
    ):
        assert rec.index == idx == canon.index
        assert rec.char == canon.char
        assert rec.name == canon.name
        assert rec.v18 == tuple(canon.vector)
        assert len(rec.v18) == 18
        assert len(rec.v14) == 14
        assert rec.v14 == rec.v18[:14]
        assert rec.anasir == rec.v18[14:17]
        assert rec.h_star == rec.v18[17]
        assert rec.native_opcode == 0xE0 + (idx - 1)


def test_priority_0_haa_vector_and_turning_quantities() -> None:
    """Priority 0 Audit: Verify exact Haa (`هـ`, index 27) vector positions and U/rho."""
    haa = MASTER_TABLE_ENGINE.get_by_char("هـ")
    assert haa is not None
    assert haa.index == 27
    assert haa.name == "Haa"
    assert haa.native_opcode == 0xFA
    # Canonical 0-based indexing:
    # 0: Θ̂=8, 1..3: N=(0,0,0), 4..8: K=(0,0,0,0,1), 9..13: Q=(0,0,0,0,2),
    # 14..16: A=(0,1,2), 17: H*=0
    assert haa.v18 == (8, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2, 0, 1, 2, 0)
    assert haa.v18[0] == 8    # Inhina (Theta_hat)
    assert haa.v18[8] == 1    # Kc
    assert haa.v18[11] == 0   # Qs (NOT 8!)
    assert haa.v18[13] == 2   # Qc
    assert haa.v18[14] == 0   # AN (NOT 8!)
    assert haa.v18[15] == 1   # AK
    assert haa.v18[16] == 2   # AQ
    assert haa.v18[17] == 0   # H*
    assert haa.turning_budget_B == 8   # U(Haa) = 0 + 0 + 0 + 4*2 = 8
    assert haa.turning_residue_R == 0  # rho(Haa) = 8 - 8 = 0


def test_b_u_and_r_rho_and_angles_and_h_star_separation() -> None:
    for rec in MASTER_TABLE_ENGINE.records:
        _qp, qx, qs, qa, qc = rec.qaws
        expected_u = qx + qs + qa + 4 * qc
        expected_rho = rec.theta_hat - expected_u
        assert rec.turning_budget_B == expected_u
        assert rec.turning_residue_R == expected_rho
        assert rec.turning_residue_R >= 0
        assert rec.theta_degrees == 90 * rec.theta_hat
        assert rec.theta_rad_pi_halves == rec.theta_hat
        if rec.char == "ك":
            assert rec.h_star == 1
            assert rec.turning_budget_B == 0
            assert rec.turning_residue_R == 2
        else:
            assert rec.h_star == 0


def test_priority_1_rom_252b_vs_504b_and_dataset_seal_reconciliation() -> None:
    """Priority 1 Audit: Unambiguously separate 252-byte nibble-packed `hm28.rom`
    from 504-byte full-width 144-bit representations, JSON seal, and `.hb` gap."""
    report = MASTER_TABLE_ENGINE.audit()
    assert report.dataset_id == DATASET_ID
    assert report.entry_count == 28
    assert report.codex_dimension == 18
    assert report.independent_rank == 14

    # 1. JSON 28x18 compact seal
    assert report.json_seal_computed == CANONICAL_JSON_SEAL
    assert report.json_seal_verified is True

    # 2. 252-byte nibble-packed ROM (`hm28.rom`, 28 * 9 = 252 bytes)
    rom_252 = MASTER_TABLE_ENGINE.pack_rom_252b()
    assert len(rom_252) == MASTER_TABLE_BYTES == 252
    assert report.rom_252b_byte_length == 252
    assert report.rom_seal_computed == CANONICAL_ROM_252B_SEAL == CANONICAL_ROM_SEAL
    assert report.rom_seal_verified is True

    # 3. 504-byte full-width uint8 row-major (28 * 18 = 504 bytes)
    rom_504_row = MASTER_TABLE_ENGINE.pack_rom_504b_row_major()
    assert len(rom_504_row) == MASTER_TABLE_504B_BYTES == 504
    assert report.rom_504b_byte_length == 504
    assert report.rom_504b_row_major_seal_computed == CANONICAL_ROM_504B_ROW_MAJOR_SEAL
    assert report.rom_504b_row_major_verified is True

    # 4. 504-byte full-width 144-bit big-endian RTL word layout (`rtl/hcpu_rom.v`)
    rom_504_rtl = MASTER_TABLE_ENGINE.pack_rom_504b_rtl_word_be()
    assert len(rom_504_rtl) == MASTER_TABLE_504B_BYTES == 504
    assert report.rom_504b_rtl_word_be_seal_computed == CANONICAL_ROM_504B_RTL_WORD_BE_SEAL
    assert report.rom_504b_rtl_word_be_verified is True
    assert report.rtl_rom_v_consistent is True

    # Ensure 252B and 504B hashes are never conflated
    assert CANONICAL_ROM_252B_SEAL != CANONICAL_ROM_504B_ROW_MAJOR_SEAL
    assert CANONICAL_ROM_252B_SEAL != CANONICAL_ROM_504B_RTL_WORD_BE_SEAL
    assert CANONICAL_ROM_504B_ROW_MAJOR_SEAL != CANONICAL_ROM_504B_RTL_WORD_BE_SEAL

    # 5. External .hb manifest gap
    assert report.hb_manifest_seal_recorded == RECORDED_HB_MANIFEST_SEAL
    assert "EXTERNAL_ARTIFACT_GAP" in report.hb_artifact_status
    assert report.all_guards_pass is True
    assert report.injectivity_pairs_verified == 378
    assert report.csv_consistent is True
    assert report.json_file_consistent is True
    assert report.rom_file_consistent is True
    assert len(report.documented_errata) == len(DOCUMENTED_SOURCE_ERRATA) == 2


def test_unicode_policy_rejects_lookalikes_presentation_forms_and_harakat() -> None:
    assert validate_and_normalize_hijaiyyah_text("ب س م هـ") == "ب س م هـ"
    for bad_char in FORBIDDEN_LOOKALIKES:
        with pytest.raises(UnicodePolicyError, match="Forbidden lookalike"):
            validate_and_normalize_hijaiyyah_text(bad_char)

    with pytest.raises(UnicodePolicyError, match="Presentation Form"):
        validate_and_normalize_hijaiyyah_text("\ufe8f")

    with pytest.raises(UnicodePolicyError, match="diacritic"):
        validate_and_normalize_hijaiyyah_text("ب\u064e")


def test_snapshot_round_trip_integrity() -> None:
    snap = MASTER_TABLE_ENGINE.snapshot_dict()
    assert snap["dataset_id"] == DATASET_ID
    assert len(snap["letters"]) == 28
    assert snap["seals"]["canonical_json_sha256"] == CANONICAL_JSON_SEAL
    assert snap["seals"]["canonical_rom_252b_nibble_packed_sha256"] == CANONICAL_ROM_252B_SEAL
    assert (
        snap["seals"]["canonical_rom_504b_uint8_row_major_sha256"]
        == CANONICAL_ROM_504B_ROW_MAJOR_SEAL
    )
    assert (
        snap["seals"]["canonical_rom_504b_rtl_144bit_be_sha256"]
        == CANONICAL_ROM_504B_RTL_WORD_BE_SEAL
    )
    assert snap["seals"]["recorded_hb_manifest_sha256"] == RECORDED_HB_MANIFEST_SEAL
