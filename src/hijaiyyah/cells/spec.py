"""Phase 2 — Formal Hijaiyyah Cells (.hcell) Spec, Two-Layer Proof Engine, & H* Contract.

Implements Owner Engineering Decision 1 (Option 2), the Six-Guard Formal
Verification Requirement, and the Section A `H*` (`C_HSTAR`) Safety Contract:

1. Two-Layer Proof Separation:
   - Layer A — Mathematical Closure over N_0^18:
     Proves independently for G1, G2, G3, G4, T1, and T2 that the invariant set
     H subset N_0^18 is closed under vector addition, while explicitly noting
     that the 8-bit bounded subset H_255 = {v in H : forall j, 0 <= v[j] <= 255}
     is NOT closed under unrestricted addition (e.g., 248 + 8 = 256 > 255).
   - Layer B — Hardware Representation & Prefix-Bound Safety:
     a) Proves that the wide RTL adders in `rtl/hcpu_guard.v` (`sum_n[9:0]`,
        `sum_k[10:0]`, `sum_q[10:0]`, `u_val[10:0]`, `rho_signed[11:0]`) can
        represent the sum of arbitrary 8-bit inputs without internal overflow
        before comparing against the 8-bit `Anasir` / `theta` fields.
     b) Proves that every reachable accumulator prefix p_k (0 <= k <= L) on
        every execution path satisfies 0 <= p_k[j] <= 255 for all j = 0..17.

2. Section A — Formal `H*` (Slot 17, `C_HSTAR`) Safety Contract Across Static & Dynamic Paths:
   - Proves that on the CSET-free canonical monoid <A_28, +, 0> over N_0^18,
     every generator satisfies Law H*-1 (`H*(v) == Ka(v) <= AK(v)`) and Law H*-2
     (`2 * H*(v) <= Theta_hat(v)`).
   - Proves why hardware `HGRD` (`0x60`) NEVER directly protects `H*` (`v[17]`):
     * Failure Mode 1 (Synchronous Modulo-256 Wrap on Unbounded Dynamic Loops):
       At 128 × 'ك', Theta_hat = 256 wraps to 0 while U = 0, so G4 (`0 >= 0`) still
       passes! At 256 × 'ك', Ka = 256 -> 0, AK = 256 -> 0, and H* = 256 -> 0
       wrap synchronously, so G2 (`sum_k = 0 == a_k = 0`) ALSO passes!
     * Failure Mode 2 (External/CSET H-Reg Construction):
       Any vector produced via `CSET` or external storage (`HFS_READ`) can have
       `v[17] != v[7]` without affecting `G1–G4` or `T1–T2`.
   - Enforces the formal rule:
     * Static paths require Layer B prefix bound `0 <= p_k[17] <= 255` AND
       `H*(v) == Ka(v)`.
     * Unbounded/dynamic paths (`WHILE_LOOP`, `HFS_READ_HYBIT`, dynamic `LOAD_ID`)
       cannot rely on `HGRD` alone and must emit an explicit runtime `H* == Ka`
       and bound check (`CGET` slot 17 vs slot 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.core.guards import compute_rho, compute_U, full_guard_check

HCELL_LANGUAGE_VERSION: str = "HCELL-v0.1-exp"
HC_COMPAT_VERSION: str = "HC-v1.0"

HREG_COMPONENT_BITS: int = 8
HREG_COMPONENT_MAX: int = 255
MAX_CANONICAL_LETTER_COMPONENT: int = 8
UNIVERSAL_SAFE_ACCUMULATION_LENGTH: int = (
    HREG_COMPONENT_MAX // MAX_CANONICAL_LETTER_COMPONENT
)


class EpistemicStatus(str, Enum):
    """Required confidence / epistemic status labels (Owner Decision 10)."""

    SPECIFIED = "SPECIFIED"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    PROVEN = "PROVEN"
    SIMULATED = "SIMULATED"
    MEASURED = "MEASURED"
    PREDICTED = "PREDICTED"


class PathSafetyClass(str, Enum):
    """Execution-path classification for Layer B prefix-bound verification."""

    STRAIGHT_LINE_BOUNDED = "STRAIGHT_LINE_BOUNDED"
    BRANCH_JOIN_BOUNDED = "BRANCH_JOIN_BOUNDED"
    STATIC_LOOP_BOUNDED = "STATIC_LOOP_BOUNDED"
    UNBOUNDED_OR_DYNAMIC_PATH = "UNBOUNDED_OR_DYNAMIC_PATH"


@dataclass(frozen=True, slots=True)
class RTLWideAdderSpec:
    """Formal specification of one wide datapath wire in `rtl/hcpu_guard.v`."""

    guard_id: str
    wire_name: str
    bit_width: int
    signed: bool
    input_expression: str
    max_possible_input_value: int
    min_possible_input_value: int
    wire_min_capacity: int
    wire_max_capacity: int
    cannot_overflow_internally: bool
    proof_note: str


RTL_GUARD_WIDE_ADDERS: tuple[RTLWideAdderSpec, ...] = (
    RTLWideAdderSpec(
        guard_id="G1",
        wire_name="sum_n",
        bit_width=10,
        signed=False,
        input_expression="na + nb + nd (3 × uint8)",
        max_possible_input_value=3 * 255,       # 765
        min_possible_input_value=0,
        wire_min_capacity=0,
        wire_max_capacity=(1 << 10) - 1,        # 1023
        cannot_overflow_internally=(3 * 255 <= (1 << 10) - 1),
        proof_note=(
            "10-bit unsigned wire sum_n[9:0] has capacity 1,023 >= 3*255 = 765, "
            "so sum_n represents na + nb + nd exactly without internal carry loss "
            "for all 8-bit inputs. Equality ({2'b00, a_n} == sum_n) then enforces "
            "that the exact sum fits in the 8-bit field a_n (0..255)."
        ),
    ),
    RTLWideAdderSpec(
        guard_id="G2",
        wire_name="sum_k",
        bit_width=11,
        signed=False,
        input_expression="kp + kx + ks + ka + kc (5 × uint8)",
        max_possible_input_value=5 * 255,       # 1275
        min_possible_input_value=0,
        wire_min_capacity=0,
        wire_max_capacity=(1 << 11) - 1,        # 2047
        cannot_overflow_internally=(5 * 255 <= (1 << 11) - 1),
        proof_note=(
            "11-bit unsigned wire sum_k[10:0] has capacity 2,047 >= 5*255 = 1,275, "
            "so sum_k represents kp+kx+ks+ka+kc exactly without internal carry loss "
            "for all 8-bit inputs. Equality ({3'b000, a_k} == sum_k) then enforces "
            "that the exact sum fits in the 8-bit field a_k (0..255)."
        ),
    ),
    RTLWideAdderSpec(
        guard_id="G3",
        wire_name="sum_q",
        bit_width=11,
        signed=False,
        input_expression="qp + qx + qs + qa + qc (5 × uint8)",
        max_possible_input_value=5 * 255,       # 1275
        min_possible_input_value=0,
        wire_min_capacity=0,
        wire_max_capacity=(1 << 11) - 1,        # 2047
        cannot_overflow_internally=(5 * 255 <= (1 << 11) - 1),
        proof_note=(
            "11-bit unsigned wire sum_q[10:0] has capacity 2,047 >= 5*255 = 1,275, "
            "so sum_q represents qp+qx+qs+qa+qc exactly without internal carry loss "
            "for all 8-bit inputs. Equality ({3'b000, a_q} == sum_q) then enforces "
            "that the exact sum fits in the 8-bit field a_q (0..255)."
        ),
    ),
    RTLWideAdderSpec(
        guard_id="G4_U",
        wire_name="u_val",
        bit_width=11,
        signed=False,
        input_expression="qx + qs + qa + 4*qc (3 × uint8 + 4 × uint8)",
        max_possible_input_value=3 * 255 + 4 * 255,  # 1785
        min_possible_input_value=0,
        wire_min_capacity=0,
        wire_max_capacity=(1 << 11) - 1,             # 2047
        cannot_overflow_internally=(7 * 255 <= (1 << 11) - 1),
        proof_note=(
            "11-bit unsigned wire u_val[10:0] has capacity 2,047 >= 3(255)+4(255) = 1,785, "
            "so u_val represents U = Qx+Qs+Qa+4*Qc without internal overflow for all "
            "8-bit Q inputs, and zero-extends to 32-bit u_value for opcode CU (0x4D)."
        ),
    ),
    RTLWideAdderSpec(
        guard_id="G4_RHO",
        wire_name="rho_signed",
        bit_width=12,
        signed=True,
        input_expression="$signed({4'd0, theta}) - $signed({1'b0, u_val})",
        max_possible_input_value=255,
        min_possible_input_value=-1785,
        wire_min_capacity=-(1 << 11),                # -2048
        wire_max_capacity=(1 << 11) - 1,             # +2047
        cannot_overflow_internally=(-1785 >= -(1 << 11) and 255 <= (1 << 11) - 1),
        proof_note=(
            "12-bit signed wire rho_signed[11:0] spans [-2,048, +2,047], which strictly "
            "contains the full input range [-1,785, +255] of theta - u_val. Sign extension "
            "{{20{rho_signed[11]}}, rho_signed} preserves negative residues in 32-bit two's "
            "complement for opcode CRHO (0x4C)."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class HStarMarkerSemantics:
    """Formal semantics and composition rules for slot 17 (`H*`, `C_HSTAR`)."""

    slot_index: int
    rtl_macro: str
    sole_nonzero_canonical_letter: str
    sole_nonzero_letter_index: int
    canonical_value_kaf: int
    canonical_value_others: int
    hardware_accumulation_rule: str
    included_in_v14_metric_ops: bool
    constrained_by_hardware_hgrd: bool
    max_safe_kaf_accumulations: int
    compiler_obligation: str


HSTAR_MARKER_SEMANTICS = HStarMarkerSemantics(
    slot_index=17,
    rtl_macro="C_HSTAR",
    sole_nonzero_canonical_letter="ك",
    sole_nonzero_letter_index=22,
    canonical_value_kaf=1,
    canonical_value_others=0,
    hardware_accumulation_rule=(
        "Additive multiplicity counter in H-Reg[17]: both HCADD (0x41) and native "
        "letter opcodes (0xE0–0xFB, specifically L_KAF 0xF5) add slot 17 modulo 256 "
        "via the 18th parallel 8-bit adder in `rtl/hcpu_codex_alu.v` (`add_result[17]`). "
        "Thus for any word w of length <= 255, H*(w) equals the exact count of Kaf ('ك') "
        "occurrences in w."
    ),
    included_in_v14_metric_ops=False,
    constrained_by_hardware_hgrd=False,
    max_safe_kaf_accumulations=255,
    compiler_obligation=(
        "Because `rtl/hcpu_guard.v` does not reference `vec[8*C_HSTAR +: 8]`, runtime "
        "`HGRD` alone cannot detect an 8-bit wrap on slot 17 (e.g., 256 × 'ك' wraps "
        "H0[17] from 256 to 0 while G1–G4 and T1–T2 still pass) nor a `CSET` write "
        "that sets H* != Ka. Therefore, Layer B static prefix-bound verification must "
        "enforce 0 <= p_k[17] <= 255 alongside slots 0..16, and any dynamic/unproven "
        "path must emit an explicit runtime check (`CGET` slot 17 vs slot 7 `Ka`)."
    ),
)


@dataclass(frozen=True, slots=True)
class HStarSafetyAuditReport:
    """Formal audit of the H* (slot 17) safety contract across all H-Reg producers."""

    canonical_law_hstar_eq_ka: bool
    canonical_law_hstar_le_ak: bool
    canonical_law_2hstar_le_theta: bool
    hgrd_directly_checks_hstar: bool
    kaf_128_wraps_theta_without_g4_fail: bool
    kaf_128_hstar_eq_ka_still_passes: bool
    kaf_128_rejected_by_half_theta_check: bool
    kaf_256_wraps_hstar_ka_ak_without_g2_fail: bool
    dynamic_path_requires_explicit_runtime_hstar_check: bool
    kaf_boundary_cases: dict[int, dict[str, int | bool]]
    hreg_producer_rules: dict[str, str]


def audit_hstar_safety_contract() -> HStarSafetyAuditReport:
    """Verify the mathematical and hardware properties of `H*` across all 28 letters
    and boundary accumulations (127, 128, 129, 255, and 256 × 'ك')."""
    recs = MASTER_TABLE_ENGINE.records
    law_eq_ka = all(r.v18[17] == r.v18[7] for r in recs)
    law_le_ak = all(r.v18[17] <= r.v18[15] for r in recs)
    law_2theta = all(2 * r.v18[17] <= r.v18[0] for r in recs)

    k128 = analyze_h0_letter_accumulation(["ك"] * 128)
    # At 128 × 'ك', Theta_hat = 256 wraps to 0, U = 0, so hardware G4 (0 >= 0) passes!
    k128_silent = (
        k128.exact_sum_vector[0] == 256
        and k128.hardware_wrapped_vector[0] == 0
        and k128.hardware_passes_guard is True
    )
    # Moreover, at 128 × 'ك', H* = 128 == Ka = 128 ALSO passes, whereas H* <= floor(Theta_hat / 2)
    # (128 <= 0) catches and rejects the overflow!
    k128_eq_ka_passes = (
        k128.hardware_wrapped_vector[17] == 128
        and k128.hardware_wrapped_vector[7] == 128
        and (k128.hardware_wrapped_vector[17] == k128.hardware_wrapped_vector[7])
    )
    k128_half_theta_rejects = not (
        k128.hardware_wrapped_vector[17] <= (k128.hardware_wrapped_vector[0] >> 1)
    )

    k256 = analyze_h0_letter_accumulation(["ك"] * 256)
    # At 256 × 'ك', Ka=256->0, AK=256->0, H*=256->0 wrap synchronously, so hardware G2 passes!
    k256_silent = (
        k256.exact_sum_vector[17] == 256
        and k256.hardware_wrapped_vector[17] == 0
        and k256.hardware_wrapped_vector[7] == 0
        and k256.hardware_wrapped_vector[15] == 0
        and k256.hardware_passes_guard is True
    )

    kaf_cases: dict[int, dict[str, int | bool]] = {}
    for m in (127, 128, 129, 255, 256):
        km = analyze_h0_letter_accumulation(["ك"] * m)
        ex_v = km.exact_sum_vector
        hw_v = km.hardware_wrapped_vector
        hw_eq_ka = hw_v[17] == hw_v[7]
        hw_le_half_theta = hw_v[17] <= (hw_v[0] >> 1)
        kaf_cases[m] = {
            "exact_theta": ex_v[0],
            "exact_ka": ex_v[7],
            "exact_ak": ex_v[15],
            "exact_hstar": ex_v[17],
            "exact_U": km.exact_U,
            "exact_rho": km.exact_rho,
            "hw_theta": hw_v[0],
            "hw_ka": hw_v[7],
            "hw_ak": hw_v[15],
            "hw_hstar": hw_v[17],
            "hw_U": km.hardware_U,
            "hw_rho_signed": km.hardware_rho_signed,
            "hw_hgrd_only_passes": km.hardware_passes_guard,
            "hw_hstar_eq_ka_passes": hw_eq_ka,
            "hw_hstar_le_half_theta_passes": hw_le_half_theta,
            "combined_runtime_guard_passes": (
                km.hardware_passes_guard and hw_eq_ka and hw_le_half_theta
            ),
            "static_layer_b_elision_permitted": km.guard_elision_permitted,
        }

    producer_rules = {
        "CZERO (0x46)": "Sets H_d = 0^18; H*=0, Ka=0, AK=0, Theta_hat=0 (exact).",
        "HLOAD (0x02)": (
            "Loads ROM entry 1..28; preserves H* == Ka <= AK and 2*H* <= Theta_hat <= 8 "
            "(for dynamic index outside 1..28, hardware raises HALT_ERR or loads negative "
            "test vector 31..36 with H*=0)."
        ),
        "L_ALIF..L_YA (0xE0..0xFB)": (
            "Adds canonical letter to H0 mod 256; preserves H* == Ka <= AK and 2*H* <= Theta_hat "
            "iff Layer B proves all prefix components <= 255 (safe for any <= 31 letters, "
            "or <= 127 'ك')."
        ),
        "HCADD (0x05/0x41)": (
            "Componentwise 8-bit add H_d = (H_s1 + H_s2) mod 256; preserves H* == Ka and "
            "2*H* <= Theta_hat iff both operands satisfy the invariants AND Layer B proves "
            "no component exceeds 255."
        ),
        "CSET (0x45) / HFS_READ (SYSCALL 7)": (
            "Can write arbitrary byte to slot 17 (`C_HSTAR`) or reconstruct an H-Reg from "
            "external memory; HGRD (0x60) does NOT inspect slot 17, so runtime checks "
            "`H* == Ka` AND `H* <= floor(Theta_hat / 2)` are both mandatory."
        ),
    }

    return HStarSafetyAuditReport(
        canonical_law_hstar_eq_ka=law_eq_ka,
        canonical_law_hstar_le_ak=law_le_ak,
        canonical_law_2hstar_le_theta=law_2theta,
        hgrd_directly_checks_hstar=False,
        kaf_128_wraps_theta_without_g4_fail=k128_silent,
        kaf_128_hstar_eq_ka_still_passes=k128_eq_ka_passes,
        kaf_128_rejected_by_half_theta_check=k128_half_theta_rejects,
        kaf_256_wraps_hstar_ka_ak_without_g2_fail=k256_silent,
        dynamic_path_requires_explicit_runtime_hstar_check=(
            k128_silent and k128_eq_ka_passes and k128_half_theta_rejects and k256_silent
        ),
        kaf_boundary_cases=kaf_cases,
        hreg_producer_rules=producer_rules,
    )


@dataclass(frozen=True, slots=True)
class NativeLetterOpcodeSpec:
    """Formal specification of one native Hijaiyyah letter instruction (0xE0–0xFB)."""

    opcode: int
    mnemonic: str
    glyph: str
    rom_index: int
    encoding_word: int
    implicit_src_hreg: int
    implicit_dst_hreg: int
    vector_added: tuple[int, ...]
    max_delta_component: int
    max_safe_repeats_from_zero: int
    rtl_forwarding_latency_cycles: int
    rtl_stall_cycles: int


@dataclass(frozen=True, slots=True)
class IndividualGuardProof:
    """Two-layer proof record for one of the 6 guards (G1, G2, G3, G4, T1, T2)."""

    guard_id: str
    equation: str
    rtl_wire_equation: str
    wide_adder_capacity_proven: bool
    layer_a_math_holds: bool
    layer_b_inputs_fit_8bit: bool
    rtl_holds: bool
    layer_a_closure_proof: str
    layer_b_hardware_proof: str
    exact_holds: bool


@dataclass(frozen=True, slots=True)
class PrefixBoundAnalysis:
    """Layer B prefix-bound verification across an accumulation sequence p_0 .. p_L."""

    step_count: int
    nonnegative_increments_proven: bool
    prefix_vectors: tuple[tuple[int, ...], ...]
    prefix_max_by_step: tuple[int, ...]
    component_upper_bounds: tuple[int, ...]
    max_prefix_component: int
    first_overflow_step: int | None
    overflowed_slots: tuple[int, ...]
    all_prefixes_fit_8bit: bool
    monotonicity_theorem: str


@dataclass(frozen=True, slots=True)
class SixGuardClosureProof:
    """Two-layer formal verification certificate for all 6 guards (G1–G4, T1–T2) + H*."""

    exact_vector: tuple[int, ...]
    hardware_vector: tuple[int, ...]
    path_class: PathSafetyClass
    prefix_bound: PrefixBoundAnalysis
    all_components_fit_8bit: bool
    overflowed_indices: tuple[int, ...]
    hstar_equals_ka_exact: bool
    hstar_2x_le_theta_exact: bool
    hw_hstar_equals_ka: bool
    hw_hstar_le_half_theta: bool
    hstar_fits_8bit: bool
    hstar_coupled_bound_proven: bool
    exact_U: int
    exact_rho: int
    rtl_u_val_11bit: int
    rtl_rho_signed_12bit: int
    rtl_rho_u32: int
    g1: IndividualGuardProof
    g2: IndividualGuardProof
    g3: IndividualGuardProof
    g4: IndividualGuardProof
    t1: IndividualGuardProof
    t2: IndividualGuardProof
    layer_a_all_six_pass: bool
    layer_b_prefix_and_width_safe: bool
    all_six_exact_pass: bool
    all_six_rtl_pass: bool
    all_six_proven_and_hw_isomorphic: bool
    elimination_decision: str


@dataclass(frozen=True, slots=True)
class AccumulationBoundAnalysis:
    """Static analysis of a sequence of native letter accumulations into H0."""

    letters: tuple[str, ...]
    initial_vector: tuple[int, ...]
    exact_sum_vector: tuple[int, ...]
    hardware_wrapped_vector: tuple[int, ...]
    max_exact_component: int
    overflowed_components: tuple[int, ...]
    exact_U: int
    exact_rho: int
    hardware_U: int
    hardware_rho_signed: int
    hardware_rho_u32: int
    per_guard_exact: dict[str, bool]
    per_guard_hardware: dict[str, bool]
    prefix_bound: PrefixBoundAnalysis
    six_guard_proof: SixGuardClosureProof
    mathematically_in_H: bool
    hardware_isomorphic: bool
    hardware_passes_guard: bool
    guard_elision_permitted: bool
    mandatory_hgrd_reason: str | None


HCELL_EBNF_GRAMMAR: str = r"""
(* ======================================================================== *)
(* Hijaiyyah Cells Native Language (.hcell) — Version HCELL-v0.1-exp        *)
(* Option 2: Hijaiyyah Letters + Approved Matematika Hijaiyyah Symbols      *)
(* Zero Latin Keywords                                                      *)
(* ======================================================================== *)

program         = { statement } ;

statement       = fn_decl
                | cond_stmt
                | loop_stmt
                | return_stmt
                | cell_decl
                | guard_stmt
                | emit_stmt
                | expr_stmt ;

fn_decl         = 'ƒ' , cell_id , '(' , [ cell_id , { ',' , cell_id } ] , ')' ,
                  ( ( ':=' , expr , [ ';' ] ) | block ) ;

return_stmt     = '⇐' , expr , [ ';' ] ;

cond_stmt       = '?' , [ '(' ] , expr , [ ')' ] , block , [ ':' , block ] ;

loop_stmt       = '↻' , [ '(' ] , expr , [ ')' ] , block ;

block           = '{' , { statement } , '}' ;

cell_decl       = cell_id , ( ':=' | '=' ) , expr , [ ';' ] ;

guard_stmt      = '⊢' , expr , [ ';' ] ;

emit_stmt       = '↦' , expr , [ ';' ] ;

expr_stmt       = expr , [ ';' ] ;

expr            = comparison ;

comparison      = additive , [ ( '==' | '!=' | '<=' | '>=' | '<' | '>' ) , additive ] ;

additive        = multiplicative , { ( '+' | '-' ) , multiplicative } ;

multiplicative  = unary , { '*' , unary } ;

unary           = ( '-' ) , unary
                | postfix ;

postfix         = primary , { '[' , expr , ']' } ;

primary         = hijaiyyah_word_lit
                | hijaiyyah_letter
                | operator_app
                | syscall_app
                | norm2_expr
                | inner_prod_expr
                | number_lit
                | fn_call_or_cell_id
                | '(' , expr , ')' ;

hijaiyyah_word_lit = ( '⟪' , hijaiyyah_seq , '⟫' )
                   | ( '«' , hijaiyyah_seq , '»' ) ;

(* Approved Bab I–II mathematical operators + HAR lookup §(idx) *)
operator_app    = ( 'Θ̂' | 'Θ' | 'U' | 'ρ' | 'Θ₄' | 'Δ' | 'd₂²'
                  | 'N' | 'K' | 'Q' | 'A' | 'H*' | 'Φ' | '§' | '⛁' ) ,
                  '(' , expr , { ',' , expr } , ')' ;

(* Official HOS Syscall Gate: ⏣(sys_num, arg [, hybit_payload]) *)
syscall_app     = '⏣' , '(' , expr , { ',' , expr } , ')' ;

norm2_expr      = '‖' , expr , '‖²' ;

inner_prod_expr = '⟨' , expr , ',' , expr , '⟩' ;

hijaiyyah_letter = 'ا' | 'ب' | 'ت' | 'ث' | 'ج' | 'ح' | 'خ' | 'د'
                 | 'ذ' | 'ر' | 'ز' | 'س' | 'ش' | 'ص' | 'ض' | 'ط'
                 | 'ظ' | 'ع' | 'غ' | 'ف' | 'ق' | 'ك' | 'ل' | 'م'
                 | 'ن' | 'و' | 'هـ' | 'ي' ;

fn_call_or_cell_id = cell_id , [ '(' , [ expr , { ',' , expr } ] , ')' ] ;

cell_id         = '⟦' , hijaiyyah_id_body , '⟧'
                | '@' , hijaiyyah_id_body
                | hijaiyyah_multi_char_id ;

number_lit      = arabic_indic_digits | ascii_digits ;
"""


def build_native_letter_opcode_table() -> dict[str, NativeLetterOpcodeSpec]:
    """Construct the formal specification table for all 28 native letter opcodes."""
    table: dict[str, NativeLetterOpcodeSpec] = {}
    for rec in MASTER_TABLE_ENGINE.records:
        max_comp = max(rec.v18)
        max_repeats = (
            HREG_COMPONENT_MAX // max_comp if max_comp > 0 else 4096
        )
        spec = NativeLetterOpcodeSpec(
            opcode=rec.native_opcode,
            mnemonic=f"L_{rec.name.upper()}",
            glyph=rec.char,
            rom_index=rec.index,
            encoding_word=(rec.native_opcode << 24),
            implicit_src_hreg=0,
            implicit_dst_hreg=0,
            vector_added=rec.v18,
            max_delta_component=max_comp,
            max_safe_repeats_from_zero=max_repeats,
            rtl_forwarding_latency_cycles=1,
            rtl_stall_cycles=0,
        )
        table[rec.char] = spec
    return table


NATIVE_LETTER_OPCODES: dict[str, NativeLetterOpcodeSpec] = (
    build_native_letter_opcode_table()
)


def analyze_prefix_bounds(
    increments: list[tuple[int, ...]] | tuple[tuple[int, ...], ...],
    initial_vector: tuple[int, ...] | None = None,
) -> PrefixBoundAnalysis:
    """Verify Layer B prefix-bound safety across an accumulation sequence p_0 .. p_L."""
    p0 = tuple(int(x) for x in (initial_vector if initial_vector is not None else (0,) * 18))
    if len(p0) != 18:
        raise ValueError(f"Expected 18 components in initial_vector, got {len(p0)}")

    nonneg = all(x >= 0 for x in p0) and all(
        len(inc) == 18 and all(x >= 0 for x in inc) for inc in increments
    )
    prefixes: list[tuple[int, ...]] = [p0]
    prefix_maxes: list[int] = [max(p0)]
    first_overflow: int | None = 0 if any(x > HREG_COMPONENT_MAX or x < 0 for x in p0) else None
    cur = list(p0)

    for step_idx, inc in enumerate(increments, start=1):
        for j in range(18):
            cur[j] += int(inc[j])
        snap = tuple(cur)
        prefixes.append(snap)
        m_val = max(snap)
        prefix_maxes.append(m_val)
        if first_overflow is None and any(x > HREG_COMPONENT_MAX or x < 0 for x in snap):
            first_overflow = step_idx

    comp_bounds = tuple(max(p[j] for p in prefixes) for j in range(18))
    overflowed_slots = tuple(
        j
        for j in range(18)
        if comp_bounds[j] > HREG_COMPONENT_MAX or any(p[j] < 0 for p in prefixes)
    )
    all_fit = len(overflowed_slots) == 0 and nonneg

    return PrefixBoundAnalysis(
        step_count=len(increments),
        nonnegative_increments_proven=nonneg,
        prefix_vectors=tuple(prefixes),
        prefix_max_by_step=tuple(prefix_maxes),
        component_upper_bounds=comp_bounds,
        max_prefix_component=max(comp_bounds),
        first_overflow_step=first_overflow,
        overflowed_slots=overflowed_slots,
        all_prefixes_fit_8bit=all_fit,
        monotonicity_theorem=(
            "Since every increment v_i in N_0^18 is componentwise nonnegative (v_i[j] >= 0), "
            "0 <= p_0[j] <= p_1[j] <= ... <= p_L[j] for all j in 0..17; thus p_L[j] <= 255 "
            "implies 0 <= p_k[j] <= 255 for every intermediate prefix k in 0..L."
            if nonneg
            else "Non-negativity violated; prefix monotonicity does not apply."
        ),
    )


def prove_six_guard_closure(
    exact_vec: tuple[int, ...] | list[int],
    *,
    prefix_bound: PrefixBoundAnalysis | None = None,
    path_class: PathSafetyClass = PathSafetyClass.STRAIGHT_LINE_BOUNDED,
) -> SixGuardClosureProof:
    """Construct the Two-Layer Six-Guard Formal Verification Certificate
    (Layer A mathematical closure over N_0^18 + Layer B hardware width, prefix, & H* safety)."""
    if len(exact_vec) != 18:
        raise ValueError(f"Expected 18 components, got {len(exact_vec)}")

    ex = tuple(int(x) for x in exact_vec)
    hw = tuple(x & 0xFF for x in ex)
    pbound = prefix_bound if prefix_bound is not None else analyze_prefix_bounds([ex])
    overflowed = pbound.overflowed_slots
    fits_8bit = pbound.all_prefixes_fit_8bit and (
        path_class != PathSafetyClass.UNBOUNDED_OR_DYNAMIC_PATH
    )

    # H* (slot 17) coupling and 8-bit bound check (both H* == Ka AND 2*H* <= Theta_hat)
    hstar_eq_ka = ex[17] == ex[7]
    hstar_2x_theta = (2 * ex[17]) <= ex[0]
    hw_hstar_eq_ka = hw[17] == hw[7]
    hw_hstar_half_theta = hw[17] <= (hw[0] >> 1)
    hstar_8bit = 0 <= ex[17] <= HREG_COMPONENT_MAX
    hstar_coupled_ok = (
        hstar_eq_ka
        and hstar_2x_theta
        and hw_hstar_eq_ka
        and hw_hstar_half_theta
        and hstar_8bit
        and fits_8bit
    )

    # Layer A: Exact mathematical quantities over N_0^18
    ex_sum_n = ex[1] + ex[2] + ex[3]
    ex_sum_k = ex[4] + ex[5] + ex[6] + ex[7] + ex[8]
    ex_sum_q = ex[9] + ex[10] + ex[11] + ex[12] + ex[13]
    ex_u = compute_U(list(ex))
    ex_rho = compute_rho(list(ex))

    ex_g1 = ex[14] == ex_sum_n
    ex_g2 = ex[15] == ex_sum_k
    ex_g3 = ex[16] == ex_sum_q
    ex_g4 = ex_rho >= 0
    ex_t1 = (ex[6] == 0) or (ex[13] >= 1)
    ex_t2 = (ex[8] == 0) or (ex[13] >= 1)

    # Layer B: Exact RTL wire equations from rtl/hcpu_guard.v (lines 66..105)
    rtl_sum_n = (hw[1] + hw[2] + hw[3]) & 0x3FF
    rtl_g1 = hw[14] == rtl_sum_n

    rtl_sum_k = (hw[4] + hw[5] + hw[6] + hw[7] + hw[8]) & 0x7FF
    rtl_g2 = hw[15] == rtl_sum_k

    rtl_sum_q = (hw[9] + hw[10] + hw[11] + hw[12] + hw[13]) & 0x7FF
    rtl_g3 = hw[16] == rtl_sum_q

    rtl_u_val = (hw[10] + hw[11] + hw[12] + (hw[13] << 2)) & 0x7FF
    rtl_g4 = hw[0] >= rtl_u_val
    rtl_rho_signed = hw[0] - rtl_u_val
    rtl_rho_u32 = rtl_rho_signed & 0xFFFFFFFF

    rtl_t1 = (hw[6] == 0) or (hw[13] >= 1)
    rtl_t2 = (hw[8] == 0) or (hw[13] >= 1)

    g1_in_ok = all(0 <= ex[j] <= 255 for j in (1, 2, 3, 14))
    g2_in_ok = all(0 <= ex[j] <= 255 for j in (4, 5, 6, 7, 8, 15))
    g3_in_ok = all(0 <= ex[j] <= 255 for j in (9, 10, 11, 12, 13, 16))
    g4_in_ok = all(0 <= ex[j] <= 255 for j in (0, 10, 11, 12, 13))
    t1_in_ok = (0 <= ex[6] <= 255) and (0 <= ex[13] <= 255)
    t2_in_ok = (0 <= ex[8] <= 255) and (0 <= ex[13] <= 255)

    g1_proof = IndividualGuardProof(
        guard_id="G1",
        equation="A_N == Na + Nb + Nd (v[14] == v[1] + v[2] + v[3])",
        rtl_wire_equation="({2'b00, a_n} == sum_n[9:0])",
        wide_adder_capacity_proven=True,
        layer_a_math_holds=ex_g1,
        layer_b_inputs_fit_8bit=g1_in_ok,
        rtl_holds=rtl_g1,
        layer_a_closure_proof=(
            f"Layer A (N_0^18): A_N(a+b) = (Na+Nb+Nd)(a+b) = {ex_sum_n}, A_N={ex[14]} "
            f"(holds={ex_g1})."
        ),
        layer_b_hardware_proof=(
            f"Layer B (RTL): 10-bit sum_n[9:0] has capacity 1,023 >= 3*255 = 765 (no internal "
            f"adder overflow). Exact inputs fit 8 bits={g1_in_ok}; hw sum_n={rtl_sum_n}, "
            f"hw a_n={hw[14]} -> rtl_G1={rtl_g1}."
        ),
        exact_holds=ex_g1,
    )
    g2_proof = IndividualGuardProof(
        guard_id="G2",
        equation="A_K == Kp + Kx + Ks + Ka + Kc (v[15] == sum_{j=4..8} v[j])",
        rtl_wire_equation="({3'b000, a_k} == sum_k[10:0])",
        wide_adder_capacity_proven=True,
        layer_a_math_holds=ex_g2,
        layer_b_inputs_fit_8bit=g2_in_ok,
        rtl_holds=rtl_g2,
        layer_a_closure_proof=(
            f"Layer A (N_0^18): A_K(a+b) = sum_{{j=4..8}}(a_j+b_j) = {ex_sum_k}, A_K={ex[15]} "
            f"(holds={ex_g2})."
        ),
        layer_b_hardware_proof=(
            f"Layer B (RTL): 11-bit sum_k[10:0] has capacity 2,047 >= 5*255 = 1,275 (no internal "
            f"adder overflow). Exact inputs fit 8 bits={g2_in_ok}; hw sum_k={rtl_sum_k}, "
            f"hw a_k={hw[15]} -> rtl_G2={rtl_g2}."
        ),
        exact_holds=ex_g2,
    )
    g3_proof = IndividualGuardProof(
        guard_id="G3",
        equation="A_Q == Qp + Qx + Qs + Qa + Qc (v[16] == sum_{j=9..13} v[j])",
        rtl_wire_equation="({3'b000, a_q} == sum_q[10:0])",
        wide_adder_capacity_proven=True,
        layer_a_math_holds=ex_g3,
        layer_b_inputs_fit_8bit=g3_in_ok,
        rtl_holds=rtl_g3,
        layer_a_closure_proof=(
            f"Layer A (N_0^18): A_Q(a+b) = sum_{{j=9..13}}(a_j+b_j) = {ex_sum_q}, A_Q={ex[16]} "
            f"(holds={ex_g3})."
        ),
        layer_b_hardware_proof=(
            f"Layer B (RTL): 11-bit sum_q[10:0] has capacity 2,047 >= 5*255 = 1,275 (no internal "
            f"adder overflow). Exact inputs fit 8 bits={g3_in_ok}; hw sum_q={rtl_sum_q}, "
            f"hw a_q={hw[16]} -> rtl_G3={rtl_g3}."
        ),
        exact_holds=ex_g3,
    )
    g4_proof = IndividualGuardProof(
        guard_id="G4",
        equation="rho(v) = Theta_hat(v) - U(v) >= 0, where U(v) = Qx + Qs + Qa + 4*Qc",
        rtl_wire_equation="({3'b000, theta} >= u_val[10:0])",
        wide_adder_capacity_proven=True,
        layer_a_math_holds=ex_g4,
        layer_b_inputs_fit_8bit=g4_in_ok,
        rtl_holds=rtl_g4,
        layer_a_closure_proof=(
            f"Layer A (N_0^18): U(a+b)=U(a)+U(b)={ex_u}, rho(a+b)=rho(a)+rho(b)={ex_rho} >= 0 "
            f"(holds={ex_g4})."
        ),
        layer_b_hardware_proof=(
            f"Layer B (RTL): 11-bit u_val[10:0] max=1,785 <= 2,047; 12-bit signed "
            f"rho_signed[11:0] range [-1,785, +255] subset [-2,048, +2,047]. "
            f"Exact inputs fit 8 bits={g4_in_ok}; hw theta={hw[0]}, hw u_val={rtl_u_val}, "
            f"hw rho_signed={rtl_rho_signed} (u32={rtl_rho_u32}) -> rtl_G4={rtl_g4}."
        ),
        exact_holds=ex_g4,
    )
    t1_proof = IndividualGuardProof(
        guard_id="T1",
        equation="Ks > 0 => Qc >= 1 (v[6] > 0 => v[13] >= 1)",
        rtl_wire_equation="(ks == 8'd0) || (qc >= 8'd1)",
        wide_adder_capacity_proven=True,
        layer_a_math_holds=ex_t1,
        layer_b_inputs_fit_8bit=t1_in_ok,
        rtl_holds=rtl_t1,
        layer_a_closure_proof=(
            f"Layer A (N_0^18): Ks={ex[6]} > 0 => Qc={ex[13]} >= 1 by non-negative "
            f"monotonicity (holds={ex_t1})."
        ),
        layer_b_hardware_proof=(
            f"Layer B (RTL): Both Ks={ex[6]} and Qc={ex[13]} fit in 0..255={t1_in_ok}, "
            f"preventing nonzero Qc from wrapping mod 256 to 8'd0 (hw ks={hw[6]}, "
            f"hw qc={hw[13]} -> rtl_T1={rtl_t1})."
        ),
        exact_holds=ex_t1,
    )
    t2_proof = IndividualGuardProof(
        guard_id="T2",
        equation="Kc > 0 => Qc >= 1 (v[8] > 0 => v[13] >= 1)",
        rtl_wire_equation="(kc == 8'd0) || (qc >= 8'd1)",
        wide_adder_capacity_proven=True,
        layer_a_math_holds=ex_t2,
        layer_b_inputs_fit_8bit=t2_in_ok,
        rtl_holds=rtl_t2,
        layer_a_closure_proof=(
            f"Layer A (N_0^18): Kc={ex[8]} > 0 => Qc={ex[13]} >= 1 by non-negative "
            f"monotonicity (holds={ex_t2})."
        ),
        layer_b_hardware_proof=(
            f"Layer B (RTL): Both Kc={ex[8]} and Qc={ex[13]} fit in 0..255={t2_in_ok}, "
            f"preventing nonzero Qc from wrapping mod 256 to 8'd0 (hw kc={hw[8]}, "
            f"hw qc={hw[13]} -> rtl_T2={rtl_t2})."
        ),
        exact_holds=ex_t2,
    )

    all_ex = ex_g1 and ex_g2 and ex_g3 and ex_g4 and ex_t1 and ex_t2
    all_rtl = rtl_g1 and rtl_g2 and rtl_g3 and rtl_g4 and rtl_t1 and rtl_t2
    both_layers_ok = all_ex and all_rtl and fits_8bit and hstar_coupled_ok and (ex == hw)

    if both_layers_ok:
        decision = (
            f"ELIDE_HGRD: Layer A (G1-G4, T1-T2 over N_0^18) and Layer B "
            f"(path={path_class.value}, all {pbound.step_count} prefixes <= 255, "
            f"H*==Ka={hstar_eq_ka}, max_component={pbound.max_prefix_component}) proven."
        )
    else:
        decision = (
            f"EMIT_MANDATORY_HGRD: Layer A={all_ex}, Layer B prefix_fit_8bit="
            f"{pbound.all_prefixes_fit_8bit} (overflowed_slots={list(overflowed)}, "
            f"first_overflow_step={pbound.first_overflow_step}, H*_coupled={hstar_coupled_ok}), "
            f"path={path_class.value}."
        )

    return SixGuardClosureProof(
        exact_vector=ex,
        hardware_vector=hw,
        path_class=path_class,
        prefix_bound=pbound,
        all_components_fit_8bit=fits_8bit,
        overflowed_indices=overflowed,
        hstar_equals_ka_exact=hstar_eq_ka,
        hstar_2x_le_theta_exact=hstar_2x_theta,
        hw_hstar_equals_ka=hw_hstar_eq_ka,
        hw_hstar_le_half_theta=hw_hstar_half_theta,
        hstar_fits_8bit=hstar_8bit,
        hstar_coupled_bound_proven=hstar_coupled_ok,
        exact_U=ex_u,
        exact_rho=ex_rho,
        rtl_u_val_11bit=rtl_u_val,
        rtl_rho_signed_12bit=rtl_rho_signed,
        rtl_rho_u32=rtl_rho_u32,
        g1=g1_proof,
        g2=g2_proof,
        g3=g3_proof,
        g4=g4_proof,
        t1=t1_proof,
        t2=t2_proof,
        layer_a_all_six_pass=all_ex,
        layer_b_prefix_and_width_safe=fits_8bit and hstar_coupled_ok,
        all_six_exact_pass=all_ex,
        all_six_rtl_pass=all_rtl,
        all_six_proven_and_hw_isomorphic=both_layers_ok,
        elimination_decision=decision,
    )


def analyze_h0_letter_accumulation(
    letters: list[str] | tuple[str, ...],
    initial_vector: tuple[int, ...] | None = None,
) -> AccumulationBoundAnalysis:
    """Analyze exact vs 8-bit hardware-wrapped H0 accumulation and prefix bounds."""
    init = tuple(initial_vector) if initial_vector is not None else tuple([0] * 18)
    if len(init) != 18:
        raise ValueError(f"initial_vector must have 18 components, got {len(init)}")

    exact = list(init)
    hw = [x & 0xFF for x in init]
    increments: list[tuple[int, ...]] = []

    for ch in letters:
        rec = MASTER_TABLE_ENGINE.get_by_char(ch)
        if rec is None:
            raise ValueError(f"Unknown canonical Hijaiyyah letter: {ch!r}")
        increments.append(rec.v18)
        for j in range(18):
            exact[j] += rec.v18[j]
            hw[j] = (hw[j] + rec.v18[j]) & 0xFF

    exact_tuple = tuple(exact)
    hw_tuple = tuple(hw)
    max_comp = max(exact_tuple)
    pbound = analyze_prefix_bounds(increments, initial_vector=init)
    proof = prove_six_guard_closure(
        exact_tuple,
        prefix_bound=pbound,
        path_class=PathSafetyClass.STRAIGHT_LINE_BOUNDED,
    )
    exact_guards = full_guard_check(exact)
    hw_guards = full_guard_check(hw)

    elision_ok = proof.all_six_proven_and_hw_isomorphic
    reason: str | None = None
    if not elision_ok:
        if proof.overflowed_indices:
            reason = (
                f"Layer B hardware 8-bit prefix overflow at slots {list(proof.overflowed_indices)} "
                f"(first overflow at step {pbound.first_overflow_step}, max exact component = "
                f"{max_comp} > {HREG_COMPONENT_MAX}); hardware wraps modulo 256 so Layer A "
                "monoid closure does not transfer"
            )
        elif not proof.layer_a_all_six_pass:
            reason = "Layer A failed: initial H0 state is not proven to satisfy G1-G4, T1-T2"
        else:
            reason = "Layer B failed: hardware vector diverges from exact N_0^18 sum"

    return AccumulationBoundAnalysis(
        letters=tuple(letters),
        initial_vector=init,
        exact_sum_vector=exact_tuple,
        hardware_wrapped_vector=hw_tuple,
        max_exact_component=max_comp,
        overflowed_components=proof.overflowed_indices,
        exact_U=proof.exact_U,
        exact_rho=proof.exact_rho,
        hardware_U=proof.rtl_u_val_11bit,
        hardware_rho_signed=proof.rtl_rho_signed_12bit,
        hardware_rho_u32=proof.rtl_rho_u32,
        per_guard_exact={k: bool(v) for k, v in exact_guards.items() if k != "all_pass"},
        per_guard_hardware={k: bool(v) for k, v in hw_guards.items() if k != "all_pass"},
        prefix_bound=pbound,
        six_guard_proof=proof,
        mathematically_in_H=proof.layer_a_all_six_pass,
        hardware_isomorphic=(exact_tuple == hw_tuple),
        hardware_passes_guard=proof.all_six_rtl_pass,
        guard_elision_permitted=elision_ok,
        mandatory_hgrd_reason=reason,
    )


__all__ = [
    "HCELL_EBNF_GRAMMAR",
    "HCELL_LANGUAGE_VERSION",
    "HC_COMPAT_VERSION",
    "HREG_COMPONENT_BITS",
    "HREG_COMPONENT_MAX",
    "HSTAR_MARKER_SEMANTICS",
    "MAX_CANONICAL_LETTER_COMPONENT",
    "NATIVE_LETTER_OPCODES",
    "RTL_GUARD_WIDE_ADDERS",
    "UNIVERSAL_SAFE_ACCUMULATION_LENGTH",
    "AccumulationBoundAnalysis",
    "EpistemicStatus",
    "HStarMarkerSemantics",
    "HStarSafetyAuditReport",
    "IndividualGuardProof",
    "NativeLetterOpcodeSpec",
    "PathSafetyClass",
    "PrefixBoundAnalysis",
    "RTLWideAdderSpec",
    "SixGuardClosureProof",
    "analyze_h0_letter_accumulation",
    "analyze_prefix_bounds",
    "audit_hstar_safety_contract",
    "build_native_letter_opcode_table",
    "prove_six_guard_closure",
]
