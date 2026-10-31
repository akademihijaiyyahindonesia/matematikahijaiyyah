# ruff: noqa: E501
"""Charter Section B — Formal Ecosystem Asset Registry for CosmicTera & Matematika Hijaiyyah.

Maps every mathematical structure, symbolic operator, language frontend, compiler IR,
ISA layer, RTL hardware module, OS/filesystem service, and NUI layer into a formal,
machine-verifiable asset specification (`FormalMathematicalAsset`), explicitly recording:
- symbols, operators, and formal representations;
- syntax and expression formation rules;
- exact mathematical semantics and 8-bit/32-bit hardware semantics;
- transformation rules and validity conditions;
- relationship with conventional mathematics;
- computational algorithms and time/space complexity;
- provable/testable properties;
- mathematical/physical bounds, assumptions, and open research problems.
"""

from __future__ import annotations

from dataclasses import dataclass

from hijaiyyah.cells.dataset_engine import (
    CANONICAL_JSON_SEAL,
    CANONICAL_ROM_SEAL,
    MASTER_TABLE_ENGINE,
)
from hijaiyyah.cells.spec import (
    HSTAR_MARKER_SEMANTICS,
    NATIVE_LETTER_OPCODES,
    RTL_GUARD_WIDE_ADDERS,
    UNIVERSAL_SAFE_ACCUMULATION_LENGTH,
    EpistemicStatus,
    audit_hstar_safety_contract,
)
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode
from hijaiyyah.theorems.test_suite import TheoremTestSuite


@dataclass(frozen=True, slots=True)
class FormalMathematicalAsset:
    """Machine-processable specification of a CosmicTera / Matematika Hijaiyyah asset."""

    asset_id: str
    layer_number: int
    title: str
    module_paths: tuple[str, ...]
    symbols_and_operators: tuple[str, ...]
    domain_and_codomain: str
    syntax_formation_rules: str
    exact_semantics: str
    hardware_semantics: str
    transformation_rules_and_validity: str
    conventional_math_relation: str
    algorithm_and_complexity: str
    provable_properties: tuple[str, ...]
    bounds_assumptions_open_problems: tuple[str, ...]
    epistemic_status: EpistemicStatus


@dataclass(frozen=True, slots=True)
class EcosystemVerificationSummary:
    """Result of verifying all registered formal assets against live repository state."""

    assets: tuple[FormalMathematicalAsset, ...]
    master_table_letters: int
    master_table_json_sha256: str
    master_table_rom_sha256: str
    theorems_total: int
    theorems_passed: int
    rtl_wide_adders_verified: bool
    hstar_laws_verified: bool
    rtl_implemented_opcodes_count: int
    native_letter_opcodes_count: int
    all_verified: bool


def build_ecosystem_asset_registry() -> tuple[FormalMathematicalAsset, ...]:
    """Construct the formal asset catalog required by Charter Section B."""
    return (
        FormalMathematicalAsset(
            asset_id="ASSET_L1_MASTER_TABLE_H28",
            layer_number=1,
            title="Matematika Hijaiyyah Canonical 28-Letter Codex & Free Monoid Homomorphism",
            module_paths=(
                "src/hijaiyyah/core/master_table.py",
                "src/hijaiyyah/cells/dataset_engine.py",
                "rtl/hcpu_rom.v",
            ),
            symbols_and_operators=(
                "Ψ: A_28 -> N_0^18",
                "v = (Θ̂, Na, Nb, Nd, Kp, Kx, Ks, Ka, Kc, Qp, Qx, Qs, Qa, Qc, AN, AK, AQ, H*)",
                "+ (componentwise monoid addition)",
            ),
            domain_and_codomain="A_28^* (free word monoid) -> H subset N_0^18 (canonical codex cone)",
            syntax_formation_rules=(
                "Every canonical letter c in A_28 maps to a unique 18-tuple Psi(c) in N_0^18; "
                "words w = c_1 c_2 ... c_L form sums Psi(w) = sum_{i=1}^L Psi(c_i)."
            ),
            exact_semantics=(
                "Exact nonnegative integer vector addition in N_0^18 preserving all 6 linear/"
                "topological invariants (G1-G4, T1-T2) and H* = Ka <= AK, 2*H* <= Theta_hat."
            ),
            hardware_semantics=(
                "144-bit H-Reg packed as 18 x 8-bit unsigned lanes (vec[8*j +: 8], j=0..17) "
                "with 18 parallel 8-bit adders in rtl/hcpu_codex_alu.v."
            ),
            transformation_rules_and_validity=(
                "Isomorphic to exact N_0^18 addition iff every intermediate prefix p_k (1<=k<=L) "
                "satisfies 0 <= p_k[j] <= 255 for all j in 0..17. Universal safe bound L <= 31 "
                "(since max_{c,j} Psi(c)[j] = 8 for 'هـ'); letter-specific bound L <= floor(255/max_j)."
            ),
            conventional_math_relation=(
                "Finitely generated submonoid <Psi(A_28), +, 0> of the free abelian monoid (N_0^18, +, 0) "
                "with quotient homomorphism mod 256 onto (Z / 256 Z)^18 in 8-bit hardware."
            ),
            algorithm_and_complexity="O(1) table lookup per letter; O(L) word accumulation in 18 lanes.",
            provable_properties=(
                "Injectivity of v_14 projection across all 28 letters",
                "Anagram invariance: Psi(pi(w)) == Psi(w) for any permutation pi",
                "JSON SHA-256 f82d3859... and ROM SHA-256 ac60add6... reproducibility",
            ),
            bounds_assumptions_open_problems=(
                f"Universal unconditional 8-bit prefix bound: L <= {UNIVERSAL_SAFE_ACCUMULATION_LENGTH} letters",
                "Open problem: hardware 16-bit extended H-Reg mode (288-bit) for L <= 8,191 without software checks",
            ),
            epistemic_status=EpistemicStatus.PROVEN,
        ),
        FormalMathematicalAsset(
            asset_id="ASSET_L1_SIX_GUARDS_AND_HSTAR",
            layer_number=1,
            title="Two-Layer Six-Guard Formal Verification (G1–G4, T1–T2) & Coupled H* Safety Contract",
            module_paths=(
                "src/hijaiyyah/core/guards.py",
                "src/hijaiyyah/cells/spec.py",
                "rtl/hcpu_guard.v",
            ),
            symbols_and_operators=(
                "G1 (AN = Na+Nb+Nd)",
                "G2 (AK = Kp+Kx+Ks+Ka+Kc)",
                "G3 (AQ = Qp+Qx+Qs+Qa+Qc)",
                "G4 (ρ = Θ̂ - U >= 0, U = Qx+Qs+Qa+4*Qc)",
                "T1 (Ks > 0 => Qc >= 1)",
                "T2 (Kc > 0 => Qc >= 1)",
                "H* == Ka AND H* <= floor(Θ̂ / 2)",
            ),
            domain_and_codomain="N_0^18 -> {True, False} (exact) and {0..255}^18 -> {0, 1} (hardware)",
            syntax_formation_rules="Guard assertion `⊢ expr;` in .hcell or `expr.guard();` in .hc.",
            exact_semantics=(
                "Conjunction of 4 linear/inequality conservation laws (G1-G4), 2 topological implication "
                "laws (T1-T2), and 2 phonological marker coupling laws (H* = Ka and 2*H* <= Theta_hat)."
            ),
            hardware_semantics=(
                "Wide combinational adders in rtl/hcpu_guard.v: sum_n[9:0] (max 765 <= 1023), "
                "sum_k[10:0] (max 1275 <= 2047), sum_q[10:0] (max 1275 <= 2047), u_val[10:0] "
                "(max 1785 <= 2047), rho_signed[11:0] ([-1785, +255] subset [-2048, +2047]), plus "
                "17-instruction branchless H* + sticky loop-prefix check in HISA backend."
            ),
            transformation_rules_and_validity=(
                "HGRD elision is sound iff Layer A (monoid closure in N_0^18), Layer B (all reachable "
                "prefixes p_k[j] <= 255), and H* coupling are statically proven. Dynamic loops require "
                "per-iteration sticky prefix verification."
            ),
            conventional_math_relation=(
                "Polyhedral cone invariance A v = 0, B v >= 0 over Z^18 combined with horn clauses "
                "(v_6 > 0 => v_13 >= 1) and modular wraparound detection."
            ),
            algorithm_and_complexity="O(1) combinational (1 clock cycle for HGRD; 17 cycles with software H* check).",
            provable_properties=(
                "Zero internal adder overflow in rtl/hcpu_guard.v for all 8-bit inputs (0..255)",
                "Complete rejection of 128..255 x Kaf via H* <= floor(Theta_hat/2) and 256 x Kaf via sticky prefix",
                "Independent necessity of G_HGRD, H* == Ka, and H* <= floor(Theta_hat/2)",
            ),
            bounds_assumptions_open_problems=(
                "Current rtl/hcpu_guard.v does not wire C_HSTAR or 18-lane adder carry-out directly",
                "Alternative A1 moves H* and 18-lane sticky carry-out into RTL (saving 18 cycles/loop iter)",
            ),
            epistemic_status=EpistemicStatus.PROVEN,
        ),
        FormalMathematicalAsset(
            asset_id="ASSET_L1_ALGEBRA_AND_THEOREMS",
            layer_number=1,
            title="Five-Field Hijaiyyah Algebra, Exomatrix Φ, & 13 Fundamental Theorems",
            module_paths=(
                "src/hijaiyyah/algebra/intrametric.py",
                "src/hijaiyyah/algebra/exometric.py",
                "src/hijaiyyah/algebra/aggregametric.py",
                "src/hijaiyyah/algebra/vektronometry.py",
                "src/hijaiyyah/theorems/test_suite.py",
            ),
            symbols_and_operators=(
                "‖v‖² (14-dim squared Euclidean norm)",
                "d₂²(a, b) (squared Euclidean distance)",
                "⟨a, b⟩ (14-dim inner product)",
                "Δ(a, b) = a - b in Z^14 (Domain C)",
                "Φ(v) (5x5 Exomatrix Frobenius energy)",
                "Θ₄(v) = Θ̂ mod 4",
            ),
            domain_and_codomain="H x H -> N_0 (metrics) and H x H -> Z^14 (difference vector Δ)",
            syntax_formation_rules=(
                "Operators `‖x‖²`, `d₂²(x, y)`, `⟨x, y⟩`, `Δ(x, y)`, `Φ(x)`, `Θ₄(x)` in .hcell."
            ),
            exact_semantics=(
                "Standard inner-product space operations on the 14 primary codex coordinates "
                "v_{0..13}, plus 5x5 Exomatrix energy Phi(v) > ||v_14||_2^2."
            ),
            hardware_semantics=(
                "Single-cycle HNRM2 (0x06), HDIST (0x07), CU (0x4D), CRHO (0x4C), CMOD4 (0x4F); "
                "7-instruction polarization sequence for INNER_V14."
            ),
            transformation_rules_and_validity=(
                "Domain C (Delta in Z^14) is strictly separated from Domain H (N_0^18); applying "
                "U(), rho(), or Guard to Delta is rejected by SemanticAnalyzer."
            ),
            conventional_math_relation=(
                "Euclidean lattice geometry in Z^14 with polarization identity "
                "<a,b> = (||a+b||^2 - ||a||^2 - ||b||^2) / 2 and Pythagorean decomposition."
            ),
            algorithm_and_complexity="O(1) (14 parallel multiplications + adder tree in hardware).",
            provable_properties=tuple(r.name for r in TheoremTestSuite().run_all()),
            bounds_assumptions_open_problems=(
                "Maximum canonical squared distance: diam^2(A_28) = 70",
                "Polarization lowering of <a,b> overflows 8-bit HCADD if a_j + b_j > 255 (solved by Alternative A2 OP_HDOT)",
            ),
            epistemic_status=EpistemicStatus.PROVEN,
        ),
        FormalMathematicalAsset(
            asset_id="ASSET_L2_CELL_IR_AND_SEMANTIC_ENGINE",
            layer_number=2,
            title="Hijaiyyah Cells Native Language (.hcell), .hc Bridge, & Path-Sensitive Cell IR",
            module_paths=(
                "src/hijaiyyah/cells/lexer.py",
                "src/hijaiyyah/cells/parser.py",
                "src/hijaiyyah/cells/ir.py",
                "src/hijaiyyah/cells/semantic.py",
                "src/hijaiyyah/cells/evaluator.py",
            ),
            symbols_and_operators=(
                ":= (bind)",
                "⊢ (guard)",
                "↦ (emit)",
                "? / : (branch)",
                "↻ (while loop)",
                "ƒ / ⇐ (subroutine / return)",
                "⏣ / ⛁ (HOS syscall / HFS read)",
            ),
            domain_and_codomain="UTF-8 Hijaiyyah source -> CellIRGraph -> Verified SemanticAnalysisReport",
            syntax_formation_rules="EBNF grammar HCELL-v0.1-exp (zero Latin keywords) + HC-v1.0 compatibility.",
            exact_semantics="Deterministic trace evaluation in CellEvaluator over N_0^18 and Z^32.",
            hardware_semantics="8-bit H-Reg wrapped evaluation (`hardware_8bit_wrap=True`) with sticky loop prefix tracking.",
            transformation_rules_and_validity=(
                "NFC normalization + strict rejection of non-H28 lookalikes (e.g. U+0629 Teh Marbuta); "
                "path-sensitive classification into STRAIGHT_LINE_BOUNDED, BRANCH_JOIN_BOUNDED, and "
                "UNBOUNDED_OR_DYNAMIC_PATH."
            ),
            conventional_math_relation="Typed SSA/CFG intermediate representation with abstract interpretation over [0, 255]^18.",
            algorithm_and_complexity="O(|V| + |E|) static analysis; O(steps) reference evaluation.",
            provable_properties=(
                "Frontend equivalence between .hcell and .hc on shared CellIRGraph",
                "Sound guard elision certificate generation",
            ),
            bounds_assumptions_open_problems=(
                "Subroutine ABI currently supports up to 4 scalar arguments (R13, R14, R12, R11)",
            ),
            epistemic_status=EpistemicStatus.TESTED,
        ),
        FormalMathematicalAsset(
            asset_id="ASSET_L3_L4_HISA_AND_HCPU_RTL",
            layer_number=4,
            title="H-ISA (101 Opcodes, Including 28 Native Letter Opcodes 0xE0–0xFB) & 5-Stage HCPU RTL",
            module_paths=(
                "src/hijaiyyah/hisa/opcodes.py",
                "src/hijaiyyah/hisa/machine.py",
                "src/hijaiyyah/cells/hisa_backend.py",
                "rtl/hcpu_top.v",
                "rtl/hcpu_execute.v",
                "rtl/hcpu_codex_alu.v",
            ),
            symbols_and_operators=(
                "L_ALIF (0xE0) .. L_YA (0xFB)",
                "HLOAD, HCADD, HGRD, HNRM2, HDIST, CU, CRHO, CMOD4, CEQ, CGET, CSET, CZERO",
                "FRD, FWR, CMP, CMPI, SYSCALL, ERET",
            ),
            domain_and_codomain="32-bit Instruction Words -> Architectural State (16x32b GPR, 16x144b H-Reg, 8b FLAGS, PC)",
            syntax_formation_rules="Fixed 32-bit encoding: [31:24]=opcode, [23:20]=dst, [19:16]=s1, [15:12]=s2, [11:0]=imm12.",
            exact_semantics="Cycle-accurate state transitions in HISAMachine and 5-stage pipelined HCPU RTL.",
            hardware_semantics=(
                "5-stage pipeline (IF-ID-EX-MEM-WB) with full GPR, H-Reg, and FLAGS forwarding; "
                "CPI_base = 1.0, taken-branch flush penalty = 3 cycles, pipeline drain = 5 cycles."
            ),
            transformation_rules_and_validity=(
                "GPR allocation strictly bounded to R1..R15 with R0 reserved as ABI scratch/MMIO base; "
                "native letter opcodes accumulate directly into H0 with 1-cycle forwarding."
            ),
            conventional_math_relation="RISC scalar pipeline coupled with an 18-lane SIMD 8-bit vector/metric coprocessor.",
            algorithm_and_complexity="1 cycle/instruction throughput (3-cycle penalty on taken control-flow changes).",
            provable_properties=(
                "3-way output and FLAG_G parity across CellEvaluator, HISAMachine, and HCPU RTL",
                "Zero prediction error (Delta_pred = 0 cycles) on linear loop calibration model",
            ),
            bounds_assumptions_open_problems=(
                "4-bit register fields cap architectural registers at 16 GPRs and 16 H-Regs",
            ),
            epistemic_status=EpistemicStatus.SIMULATED,
        ),
        FormalMathematicalAsset(
            asset_id="ASSET_L5_L6_HOS_HPG1_AND_NUI",
            layer_number=6,
            title="HOS Kernel, HFS Storage, Trusted 4-B' Overlay Loader, & NUI Layers 1–7",
            module_paths=(
                "rtl/programs/hos.hasm",
                "rtl/programs/hos_prog_load.hasm",
                "src/hijaiyyah/cells/hpg1_bridge.py",
                "src/hijaiyyah/cells/wave2_syscalls.py",
                "src/hijaiyyah/nui/claims.py",
                "src/hijaiyyah/nui/layer7_decision.py",
            ),
            symbols_and_operators=(
                "HPG1 Container (magic 0x48504731)",
                "4-B' Control-Flow & Call-Depth Verifier",
                "HOS Syscalls 1..9",
                "NUI Layer 7 Policy Gate (ALLOW / DENY / STOP)",
            ),
            domain_and_codomain="SD Card Sectors / Syscall Traps / Telemetry -> Verified Execution & Autonomous Decisions",
            syntax_formation_rules="HPG1 8-word header + code + reloc table + Checksum32; NUI claim & action records.",
            exact_semantics=(
                "Pre-load static verification of control-flow targets, privileged instruction absence, "
                "and call depth <= 8 before overlay jump to 0x900; deterministic policy gating in NUI Layer 7."
            ),
            hardware_semantics="Verified across 39 RTL testbench targets including multi-card SD SPI loader.",
            transformation_rules_and_validity=(
                "HFS_WRITE (syscall 8) enforces full_guard_check on H0 before committing to 8-slot HFS table."
            ),
            conventional_math_relation="Proof-carrying code / bytecode verification + formal safety-gated decision automaton.",
            algorithm_and_complexity="O(W) loader verification; O(1) syscall dispatch and Layer 7 action classification.",
            provable_properties=(
                "Candidate A (436c8b7) + Candidate B (b5c80de) 4-B' security and multi-sector integrity",
                "Deterministic blocking of all 10 destructive host commands in NUI Layer 7",
            ),
            bounds_assumptions_open_problems=(
                "Raw v_14 Euclidean distance yields 34.84%–53.40% group coherence percentile in claims.py; "
                "invariant-weighted feature projection improves semantic separability",
            ),
            epistemic_status=EpistemicStatus.TESTED,
        ),
    )


def verify_all_ecosystem_assets() -> EcosystemVerificationSummary:
    """Verify all registered formal assets against live repository state."""
    assets = build_ecosystem_asset_registry()
    thm_results = TheoremTestSuite().run_all()
    thm_passed = sum(1 for r in thm_results if r.passed)
    adders_ok = all(a.cannot_overflow_internally for a in RTL_GUARD_WIDE_ADDERS)
    hstar_audit = audit_hstar_safety_contract()
    hstar_ok = (
        hstar_audit.canonical_law_hstar_eq_ka
        and hstar_audit.canonical_law_hstar_le_ak
        and hstar_audit.canonical_law_2hstar_le_theta
        and hstar_audit.kaf_128_rejected_by_half_theta_check
        and hstar_audit.dynamic_path_requires_explicit_runtime_hstar_check
    )
    rtl_ops = len(RTL_IMPLEMENTED)
    letter_ops = len(NATIVE_LETTER_OPCODES)
    assert HSTAR_MARKER_SEMANTICS.slot_index == 17
    assert len( list(OpCode) ) >= rtl_ops

    all_ok = (
        len(MASTER_TABLE_ENGINE.records) == 28
        and thm_passed == len(thm_results) == 13
        and adders_ok
        and hstar_ok
        and letter_ops == 28
    )
    return EcosystemVerificationSummary(
        assets=assets,
        master_table_letters=len(MASTER_TABLE_ENGINE.records),
        master_table_json_sha256=CANONICAL_JSON_SEAL,
        master_table_rom_sha256=CANONICAL_ROM_SEAL,
        theorems_total=len(thm_results),
        theorems_passed=thm_passed,
        rtl_wide_adders_verified=adders_ok,
        hstar_laws_verified=hstar_ok,
        rtl_implemented_opcodes_count=rtl_ops,
        native_letter_opcodes_count=letter_ops,
        all_verified=all_ok,
    )


__all__ = [
    "EcosystemVerificationSummary",
    "FormalMathematicalAsset",
    "build_ecosystem_asset_registry",
    "verify_all_ecosystem_assets",
]
