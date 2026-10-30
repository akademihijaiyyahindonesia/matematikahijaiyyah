"""Phase 1 — Authoritative Master Table Data Engine (HM-28-v.1.0-HC18D).

Preserves the exact 28 isolated Hijaiyyah entries, 18-dimensional codex
vectors in canonical slot order:
  [0: Θ̂, 1: Na, 2: Nb, 3: Nd, 4: Kp, 5: Kx, 6: Ks, 7: Ka, 8: Kc,
   9: Qp, 10: Qx, 11: Qs, 12: Qa, 13: Qc, 14: AN, 15: AK, 16: AQ, 17: H*],
derived B=U(h) and R=rho(h) turning quantities, exact angle representations,
H* phonological marker semantics, Unicode canonicalization policy, unambiguous
ROM and JSON seals (252-byte nibble-packed vs 504-byte full-width 144-bit),
direct verification against `rtl/hcpu_rom.v`, and the documented external .hb
artifact gap.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hijaiyyah.core.codex_entry import CodexEntry
from hijaiyyah.core.constants import (
    ALPHABET_SIZE,
    CODEX_DIM,
    H28_ALPHABET,
    H28_SINGLE_CHARS,
    HAA_FIRST,
    HAA_SECOND,
    HAA_SEQUENCE,
    INDEPENDENT_DIM,
    MASTER_TABLE_BYTES,
    V14_SLOTS,
    V18_SLOTS,
)
from hijaiyyah.core.exceptions import HijaiyyahError
from hijaiyyah.core.guards import compute_rho, compute_U, full_guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.core.rom import pack_rom

DATASET_ID: str = "HM-28-v.1.0-HC18D"
SOURCE_DOCUMENT: str = "Buku Matematika Hijaiyyah Edisi v.1.1.1 @2026 HMCL.pdf"

#: Reproducible SHA-256 over canonical compact JSON 28x18 matrix:
#: json.dumps([list(e.vector) for e in entries], separators=(",", ":")).encode("utf-8")
CANONICAL_JSON_SEAL: str = (
    "f82d385917ffe32ae2b5711409b1341e90934c52172ae9d0fa68888e3b9c51c8"
)

#: Reproducible SHA-256 over 252-byte nibble-packed binary ROM (`hm28.rom`,
#: 28 letters × 9 bytes/letter, 2 uint4 nibbles per byte, high nibble first).
CANONICAL_ROM_252B_SEAL: str = (
    "ac60add65c3c0526a20cec6f8be79dbdfa358793bbb9e5a32b56c708d6fc5614"
)
#: Alias preserved for backward compatibility: always refers to the 252-byte
#: nibble-packed `hm28.rom` image.
CANONICAL_ROM_SEAL: str = CANONICAL_ROM_252B_SEAL

#: Reproducible SHA-256 over 504-byte full-width uint8 row-major binary table
#: (28 letters × 18 bytes/letter, 1 uint8 byte per component in canonical order
#: v[0]=Θ̂ .. v[17]=H*).
CANONICAL_ROM_504B_ROW_MAJOR_SEAL: str = (
    "d751447926bf26476a827acb5f6661ca32f8cb351831255063ac4ebf8f8f59b0"
)

#: Reproducible SHA-256 over 504-byte full-width 144-bit big-endian RTL word
#: serialization (28 letters × 18 bytes/letter, each 144-bit word packed as
#: sum(v[j] << (8*j)) serialized big-endian v[17]..v[0], matching `rtl/hcpu_rom.v`).
CANONICAL_ROM_504B_RTL_WORD_BE_SEAL: str = (
    "d77921cd95d43aad32a7f60e6ebd6c7efad88d129471cdb17dafdb252e091583"
)

MASTER_TABLE_504B_BYTES: int = ALPHABET_SIZE * CODEX_DIM  # 28 * 18 = 504 bytes

#: Recorded SHA-256 in data/hm28_manifest.json (artifacts.hb: MH-28-v.1.0-HC18D.hb,
#: 1,036 bytes) and printed on page 79 of the book PDF. The 1,036-byte Normaliz
#: Hilbert-basis file (.hb) is not present in the repository checkout; this hash
#: is tracked explicitly as an external artifact gap and never forged or equated
#: with the JSON or ROM hashes.
RECORDED_HB_MANIFEST_SEAL: str = (
    "f85251e0daf5bb977a381738accaeb599a05445484158fc158e3ea279902302c"
)

#: Visually similar non-canonical Arabic/Persian/Urdu codepoints that must never
#: be silently substituted for canonical H28 letters.
FORBIDDEN_LOOKALIKES: dict[str, str] = {
    "\u06a9": "Persian/Urdu Keheh (U+06A9); use canonical Kaf 'ك' (U+0643)",
    "\u06cc": "Farsi Yeh (U+06CC); use canonical Ya 'ي' (U+064A)",
    "\u0649": "Alef Maksura (U+0649); use canonical Ya 'ي' (U+064A) or Alif 'ا' (U+0627)",
    "\u06c1": "Heh Goal (U+06C1); use canonical Haa 'هـ' (U+0647 U+0640)",
    "\u06be": "Heh Doachashmee (U+06BE); use canonical Haa 'هـ' (U+0647 U+0640)",
    "\u0629": "Teh Marbuta (U+0629); not a member of isolated H28",
    "\u0622": "Alef with Maddah (U+0622); use canonical isolated Alif 'ا' (U+0627)",
    "\u0623": "Alef with Hamza Above (U+0623); use canonical isolated Alif 'ا' (U+0627)",
    "\u0625": "Alef with Hamza Below (U+0625); use canonical isolated Alif 'ا' (U+0627)",
    "\u0624": "Waw with Hamza Above (U+0624); use canonical Waw 'و' (U+0648)",
    "\u0626": "Yeh with Hamza Above (U+0626); use canonical Ya 'ي' (U+064A)",
}


class UnicodePolicyError(HijaiyyahError):
    """Raised when source text violates the Hijaiyyah Unicode encoding policy."""


@dataclass(frozen=True, slots=True)
class SourceErratumRecord:
    """Documented inconsistency in printed source materials, recorded as-is."""

    id: str
    location: str
    printed_value: str
    canonical_value: str
    explanation: str


DOCUMENTED_SOURCE_ERRATA: tuple[SourceErratumRecord, ...] = (
    SourceErratumRecord(
        id="ERRATUM-P79-WAW-INDEX",
        location="Buku Matematika Hijaiyyah Edisi v.1.1.1 hal. 79, baris ke-26 (Waw 'و')",
        printed_value="Nomor urut tercetak '25' (mengulang 25 setelah 25 Nun, lalu 27 Haa)",
        canonical_value="Indeks kanonik = 26 (antara 25 Nun dan 27 Haa)",
        explanation=(
            "Slip penomoran tipografis pada tabel cetak hal. 79; urutan alfabet, "
            "data/hm28.csv, data/hm28.json, dan hcpu_rom.v menempatkan Waw pada indeks 26."
        ),
    ),
    SourceErratumRecord(
        id="ERRATUM-P79-KAF-BR-SWAP",
        location="Buku Matematika Hijaiyyah Edisi v.1.1.1 hal. 79, baris ke-22 (Kaf 'ك')",
        printed_value="Kolom B (U) = 2, R (rho) = 0",
        canonical_value="B = U(ك) = 0, R = rho(ك) = 2",
        explanation=(
            "Kaf memiliki Q(ك) = (0,0,0,0,0) sehingga U = Qx+Qs+Qa+4Qc = 0 dan "
            "rho = Theta_hat - U = 2 - 0 = 2. Tercatat di test_book_anchor.py."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class MasterTableLetterRecord:
    """Complete authoritative record for one letter in HM-28-v.1.0-HC18D."""

    index: int
    char: str
    name: str
    unicode_codepoints: tuple[str, ...]
    theta_hat: int
    theta_degrees: int
    theta_rad_pi_halves: int
    nuqtah: tuple[int, int, int]
    khatt: tuple[int, int, int, int, int]
    qaws: tuple[int, int, int, int, int]
    v14: tuple[int, ...]
    anasir: tuple[int, int, int]
    h_star: int
    v18: tuple[int, ...]
    turning_budget_B: int
    turning_residue_R: int
    native_opcode: int
    har_ref: str


@dataclass(frozen=True, slots=True)
class SealAuditReport:
    """Result of auditing all dataset seals and repository copies."""

    dataset_id: str
    source_document: str
    entry_count: int
    codex_dimension: int
    independent_rank: int
    json_seal_expected: str
    json_seal_computed: str
    json_seal_verified: bool
    rom_seal_expected: str
    rom_seal_computed: str
    rom_seal_verified: bool
    rom_252b_byte_length: int
    rom_504b_row_major_seal_expected: str
    rom_504b_row_major_seal_computed: str
    rom_504b_row_major_verified: bool
    rom_504b_rtl_word_be_seal_expected: str
    rom_504b_rtl_word_be_seal_computed: str
    rom_504b_rtl_word_be_verified: bool
    rom_504b_byte_length: int
    hb_manifest_seal_recorded: str
    hb_artifact_present: bool
    hb_artifact_status: str
    all_guards_pass: bool
    injectivity_pairs_verified: int
    csv_consistent: bool
    json_file_consistent: bool
    rom_file_consistent: bool
    rtl_rom_v_consistent: bool
    documented_errata: tuple[SourceErratumRecord, ...] = field(default_factory=tuple)


def validate_and_normalize_hijaiyyah_text(text: str) -> str:
    """Enforce NFC normalization and reject lookalike or presentation-form glyphs."""
    normalized = unicodedata.normalize("NFC", text)
    for pos, ch in enumerate(normalized):
        cp = ord(ch)
        if ch in FORBIDDEN_LOOKALIKES:
            raise UnicodePolicyError(
                f"Forbidden lookalike character {ch!r} (U+{cp:04X}) at index {pos}: "
                f"{FORBIDDEN_LOOKALIKES[ch]}"
            )
        if (0xFB50 <= cp <= 0xFDFF) or (0xFE70 <= cp <= 0xFEFF):
            raise UnicodePolicyError(
                f"Arabic Presentation Form {ch!r} (U+{cp:04X}) at index {pos} is "
                "forbidden; use canonical isolated UTF-8 codepoints"
            )
        if 0x064B <= cp <= 0x065F or cp == 0x0670:
            raise UnicodePolicyError(
                f"Combining diacritic/harakat (U+{cp:04X}) at index {pos} is "
                "outside the isolated H28 alphabet"
            )
    return normalized


class MasterTableEngine:
    """Machine-readable data engine and integrity auditor for HM-28-v.1.0-HC18D."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or Path(__file__).resolve().parents[3]
        self._records: list[MasterTableLetterRecord] = []
        self._by_char: dict[str, MasterTableLetterRecord] = {}
        self._by_index: dict[int, MasterTableLetterRecord] = {}
        self._by_name: dict[str, MasterTableLetterRecord] = {}
        self._build_records()

    def _build_records(self) -> None:
        entries: list[CodexEntry] = MASTER_TABLE.all_entries()
        if len(entries) != ALPHABET_SIZE:
            raise HijaiyyahError(
                f"Expected {ALPHABET_SIZE} Master Table entries, got {len(entries)}"
            )
        for entry in entries:
            v = tuple(entry.vector)
            if len(v) != CODEX_DIM:
                raise HijaiyyahError(
                    f"Entry {entry.index} ({entry.name}) has {len(v)} components"
                )
            theta_hat = v[0]
            nuqtah = (v[1], v[2], v[3])
            khatt = (v[4], v[5], v[6], v[7], v[8])
            qaws = (v[9], v[10], v[11], v[12], v[13])
            v14 = v[:INDEPENDENT_DIM]
            anasir = (v[14], v[15], v[16])
            h_star = v[17]
            u_val = compute_U(list(v))
            rho_val = compute_rho(list(v))
            codepoints = tuple(f"U+{ord(c):04X}" for c in entry.char)
            rec = MasterTableLetterRecord(
                index=entry.index,
                char=entry.char,
                name=entry.name,
                unicode_codepoints=codepoints,
                theta_hat=theta_hat,
                theta_degrees=theta_hat * 90,
                theta_rad_pi_halves=theta_hat,
                nuqtah=nuqtah,
                khatt=khatt,
                qaws=qaws,
                v14=v14,
                anasir=anasir,
                h_star=h_star,
                v18=v,
                turning_budget_B=u_val,
                turning_residue_R=rho_val,
                native_opcode=0xE0 + (entry.index - 1),
                har_ref=f"HM-28:{entry.index:02d}",
            )
            self._records.append(rec)
            self._by_char[rec.char] = rec
            self._by_index[rec.index] = rec
            self._by_name[rec.name.lower()] = rec

    @property
    def records(self) -> tuple[MasterTableLetterRecord, ...]:
        return tuple(self._records)

    def get_by_char(self, ch: str) -> MasterTableLetterRecord | None:
        norm = validate_and_normalize_hijaiyyah_text(ch)
        if norm == HAA_FIRST:
            norm = HAA_SEQUENCE
        return self._by_char.get(norm)

    def get_by_index(self, index: int) -> MasterTableLetterRecord | None:
        return self._by_index.get(index)

    def get_by_name(self, name: str) -> MasterTableLetterRecord | None:
        return self._by_name.get(name.strip().lower())

    def compute_json_seal(self) -> str:
        payload = json.dumps(
            [list(r.v18) for r in self._records],
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def pack_rom_252b(self) -> bytes:
        """Return the 252-byte nibble-packed binary ROM (`hm28.rom`, 28 × 9 bytes)."""
        packed = pack_rom([list(r.v18) for r in self._records])
        if len(packed) != MASTER_TABLE_BYTES:
            raise HijaiyyahError(f"Expected {MASTER_TABLE_BYTES} ROM bytes, got {len(packed)}")
        return packed

    def compute_rom_seal(self) -> str:
        """Compute SHA-256 of the 252-byte nibble-packed ROM (`hm28.rom`)."""
        return hashlib.sha256(self.pack_rom_252b()).hexdigest()

    def pack_rom_504b_row_major(self) -> bytes:
        """Return the 504-byte full-width uint8 row-major binary table (28 × 18 bytes)."""
        raw = bytes(x & 0xFF for r in self._records for x in r.v18)
        if len(raw) != MASTER_TABLE_504B_BYTES:
            raise HijaiyyahError(f"Expected {MASTER_TABLE_504B_BYTES} bytes, got {len(raw)}")
        return raw

    def compute_rom_504b_row_major_seal(self) -> str:
        """Compute SHA-256 of the 504-byte full-width uint8 row-major representation."""
        return hashlib.sha256(self.pack_rom_504b_row_major()).hexdigest()

    def pack_rom_504b_rtl_word_be(self) -> bytes:
        """Return the 504-byte 144-bit big-endian word serialization (`rtl/hcpu_rom.v`)."""
        raw = b"".join(
            sum((r.v18[j] & 0xFF) << (8 * j) for j in range(CODEX_DIM)).to_bytes(
                CODEX_DIM, "big"
            )
            for r in self._records
        )
        if len(raw) != MASTER_TABLE_504B_BYTES:
            raise HijaiyyahError(f"Expected {MASTER_TABLE_504B_BYTES} bytes, got {len(raw)}")
        return raw

    def compute_rom_504b_rtl_word_be_seal(self) -> str:
        """Compute SHA-256 of the 504-byte 144-bit big-endian RTL word representation."""
        return hashlib.sha256(self.pack_rom_504b_rtl_word_be()).hexdigest()

    def verify_rtl_rom_v(self) -> bool:
        """Parse `rtl/hcpu_rom.v` and verify all 28 144-bit letter vectors match `v18`."""
        rom_v = self._root / "rtl" / "hcpu_rom.v"
        if not rom_v.is_file():
            return False
        text = rom_v.read_text(encoding="utf-8")
        pattern = re.compile(r"6'd(\d+)\s*:\s*data_out\s*=\s*\{([^}]+)\}\s*;")
        found: dict[int, tuple[int, ...]] = {}
        for m in pattern.finditer(text):
            idx = int(m.group(1))
            if 1 <= idx <= ALPHABET_SIZE:
                comps_msb_to_lsb = [int(x) for x in re.findall(r"8'd(\d+)", m.group(2))]
                if len(comps_msb_to_lsb) == CODEX_DIM:
                    found[idx] = tuple(reversed(comps_msb_to_lsb))
        if len(found) != ALPHABET_SIZE:
            return False
        return all(found.get(r.index) == r.v18 for r in self._records)

    def audit(self) -> SealAuditReport:
        json_seal = self.compute_json_seal()
        rom_252_seal = self.compute_rom_seal()
        rom_504_row_seal = self.compute_rom_504b_row_major_seal()
        rom_504_rtl_seal = self.compute_rom_504b_rtl_word_be_seal()

        all_guards = all(
            full_guard_check(list(r.v18))["all_pass"]
            and r.turning_budget_B == r.qaws[1] + r.qaws[2] + r.qaws[3] + 4 * r.qaws[4]
            and r.turning_residue_R == r.theta_hat - r.turning_budget_B >= 0
            and r.h_star == (1 if r.char == "ك" else 0)
            and r.theta_degrees == 90 * r.theta_hat
            for r in self._records
        )

        pairs_ok = 0
        for i in range(len(self._records)):
            for j in range(i + 1, len(self._records)):
                if self._records[i].v18 != self._records[j].v18 and (
                    self._records[i].v14 != self._records[j].v14
                ):
                    pairs_ok += 1

        csv_ok = False
        csv_path = self._root / "data" / "hm28.csv"
        if csv_path.is_file():
            with open(csv_path, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            csv_cols = [
                "Theta_Hat", "Na", "Nb", "Nd",
                "Kp", "Kx", "Ks", "Ka", "Kc",
                "Qp", "Qx", "Qs", "Qa", "Qc",
                "An", "Ak", "Aq", "H_Star",
            ]
            csv_ok = len(rows) == ALPHABET_SIZE and all(
                tuple(int(row[c]) for c in csv_cols) == self._by_index[int(row["#"])].v18
                and int(row["U_Value"]) == self._by_index[int(row["#"])].turning_budget_B
                and int(row["Rho"]) == self._by_index[int(row["#"])].turning_residue_R
                for row in rows
            )

        json_ok = False
        json_path = self._root / "data" / "hm28.json"
        if json_path.is_file():
            doc = json.loads(json_path.read_text(encoding="utf-8"))
            json_ok = (
                doc.get("sha256") == CANONICAL_JSON_SEAL
                and doc.get("letter_count") == ALPHABET_SIZE
                and all(
                    tuple(item["vector"]) == self._by_index[int(item["index"])].v18
                    for item in doc.get("data", {}).values()
                )
            )

        rom_ok = False
        rom_path = self._root / "hm28.rom"
        if rom_path.is_file():
            rom_bytes = rom_path.read_bytes()
            rom_ok = (
                len(rom_bytes) == MASTER_TABLE_BYTES
                and hashlib.sha256(rom_bytes).hexdigest() == CANONICAL_ROM_252B_SEAL
            )

        rtl_rom_ok = self.verify_rtl_rom_v()

        hb_path = self._root / "data" / "MH-28-v.1.0-HC18D.hb"
        hb_present = hb_path.is_file()
        hb_status = (
            "VERIFIED"
            if hb_present
            and hashlib.sha256(hb_path.read_bytes()).hexdigest() == RECORDED_HB_MANIFEST_SEAL
            else "EXTERNAL_ARTIFACT_GAP: MH-28-v.1.0-HC18D.hb (1,036 bytes) recorded in "
                 "data/hm28_manifest.json with SHA-256 f85251e0... is not in repo checkout"
        )

        return SealAuditReport(
            dataset_id=DATASET_ID,
            source_document=SOURCE_DOCUMENT,
            entry_count=len(self._records),
            codex_dimension=CODEX_DIM,
            independent_rank=INDEPENDENT_DIM,
            json_seal_expected=CANONICAL_JSON_SEAL,
            json_seal_computed=json_seal,
            json_seal_verified=(json_seal == CANONICAL_JSON_SEAL),
            rom_seal_expected=CANONICAL_ROM_252B_SEAL,
            rom_seal_computed=rom_252_seal,
            rom_seal_verified=(rom_252_seal == CANONICAL_ROM_252B_SEAL),
            rom_252b_byte_length=MASTER_TABLE_BYTES,
            rom_504b_row_major_seal_expected=CANONICAL_ROM_504B_ROW_MAJOR_SEAL,
            rom_504b_row_major_seal_computed=rom_504_row_seal,
            rom_504b_row_major_verified=(rom_504_row_seal == CANONICAL_ROM_504B_ROW_MAJOR_SEAL),
            rom_504b_rtl_word_be_seal_expected=CANONICAL_ROM_504B_RTL_WORD_BE_SEAL,
            rom_504b_rtl_word_be_seal_computed=rom_504_rtl_seal,
            rom_504b_rtl_word_be_verified=(
                rom_504_rtl_seal == CANONICAL_ROM_504B_RTL_WORD_BE_SEAL
            ),
            rom_504b_byte_length=MASTER_TABLE_504B_BYTES,
            hb_manifest_seal_recorded=RECORDED_HB_MANIFEST_SEAL,
            hb_artifact_present=hb_present,
            hb_artifact_status=hb_status,
            all_guards_pass=all_guards,
            injectivity_pairs_verified=pairs_ok,
            csv_consistent=csv_ok,
            json_file_consistent=json_ok,
            rom_file_consistent=rom_ok,
            rtl_rom_v_consistent=rtl_rom_ok,
            documented_errata=DOCUMENTED_SOURCE_ERRATA,
        )

    def snapshot_dict(self) -> dict[str, Any]:
        """Deterministic machine-readable snapshot preserving all source distinctions."""
        report = self.audit()
        return {
            "dataset_id": DATASET_ID,
            "source_document": SOURCE_DOCUMENT,
            "v14_slots": list(V14_SLOTS),
            "v18_slots": list(V18_SLOTS),
            "seals": {
                "canonical_json_sha256": report.json_seal_computed,
                "canonical_rom_252b_nibble_packed_sha256": report.rom_seal_computed,
                "canonical_rom_252b_byte_length": report.rom_252b_byte_length,
                "canonical_rom_504b_uint8_row_major_sha256": (
                    report.rom_504b_row_major_seal_computed
                ),
                "canonical_rom_504b_rtl_144bit_be_sha256": (
                    report.rom_504b_rtl_word_be_seal_computed
                ),
                "canonical_rom_504b_byte_length": report.rom_504b_byte_length,
                "rtl_hcpu_rom_v_verified": report.rtl_rom_v_consistent,
                "recorded_hb_manifest_sha256": report.hb_manifest_seal_recorded,
                "hb_artifact_status": report.hb_artifact_status,
            },
            "letters": [
                {
                    "index": r.index,
                    "char": r.char,
                    "name": r.name,
                    "unicode_codepoints": list(r.unicode_codepoints),
                    "theta_hat": r.theta_hat,
                    "theta_degrees": r.theta_degrees,
                    "theta_rad": f"{r.theta_rad_pi_halves}*pi/2" if r.theta_rad_pi_halves else "0",
                    "nuqtah": list(r.nuqtah),
                    "khatt": list(r.khatt),
                    "qaws": list(r.qaws),
                    "v14": list(r.v14),
                    "anasir": list(r.anasir),
                    "h_star": r.h_star,
                    "v18": list(r.v18),
                    "B_turning_budget_U": r.turning_budget_B,
                    "R_turning_residue_rho": r.turning_residue_R,
                    "native_opcode_hex": f"0x{r.native_opcode:02X}",
                    "har_ref": r.har_ref,
                }
                for r in self._records
            ],
            "documented_errata": [
                {
                    "id": e.id,
                    "location": e.location,
                    "printed_value": e.printed_value,
                    "canonical_value": e.canonical_value,
                    "explanation": e.explanation,
                }
                for e in DOCUMENTED_SOURCE_ERRATA
            ],
        }


MASTER_TABLE_ENGINE = MasterTableEngine()

__all__ = [
    "CANONICAL_JSON_SEAL",
    "CANONICAL_ROM_252B_SEAL",
    "CANONICAL_ROM_504B_ROW_MAJOR_SEAL",
    "CANONICAL_ROM_504B_RTL_WORD_BE_SEAL",
    "CANONICAL_ROM_SEAL",
    "DATASET_ID",
    "DOCUMENTED_SOURCE_ERRATA",
    "FORBIDDEN_LOOKALIKES",
    "H28_ALPHABET",
    "H28_SINGLE_CHARS",
    "HAA_FIRST",
    "HAA_SECOND",
    "HAA_SEQUENCE",
    "MASTER_TABLE_504B_BYTES",
    "MASTER_TABLE_ENGINE",
    "RECORDED_HB_MANIFEST_SEAL",
    "SOURCE_DOCUMENT",
    "MasterTableEngine",
    "MasterTableLetterRecord",
    "SealAuditReport",
    "SourceErratumRecord",
    "UnicodePolicyError",
    "validate_and_normalize_hijaiyyah_text",
]
