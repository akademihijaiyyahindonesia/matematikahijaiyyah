"""Phase 3.4 — Shared Semantic Analyzer, Two-Layer Six-Guard Prover, & H* Safety Enforcer.

Validates `CellIRGraph` nodes produced by either the native `.hcell` frontend
or the `.hc` v1.0 compatibility bridge:
- Operator validity, input arity, and type compatibility
- Mathematical domain constraints (e.g., `DELTA14` in Z^14 is not in the monoid
  H and cannot be passed to `U`, `rho`, `HGRD`, or `HYBIT_ADD`)
- Two-Layer Six-Guard Proof (`SixGuardClosureProof`) + `H*` (`C_HSTAR`) Safety Contract:
  * Layer A — Mathematical closure of G1, G2, G3, G4, T1, T2 over N_0^18
  * Layer B — Hardware representation, prefix-bound safety (0 <= p_k[j] <= 255
    for all 18 slots j = 0..17), and `H*(v) == Ka(v)` coupling proof.
- Enforces that `HGRD` is never assumed to protect `H*` directly: on any
  unbounded/dynamic path (`WHILE_LOOP`, `HFS_READ_HYBIT`), `hstar_coupled_bound_proven`
  is set to `False` so the backend emits both `HGRD` and an explicit runtime
  `H* == Ka` check (`CGET` #17 vs `CGET` #7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.cells.ir import CellIRGraph, CellIRNode, CellOp, CellValueType
from hijaiyyah.cells.spec import (
    HREG_COMPONENT_MAX,
    MAX_CANONICAL_LETTER_COMPONENT,
    PathSafetyClass,
    SixGuardClosureProof,
    analyze_h0_letter_accumulation,
    analyze_prefix_bounds,
    prove_six_guard_closure,
)
from hijaiyyah.core.exceptions import HijaiyyahError
from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.guards import compute_rho, compute_U


class CellSemanticError(HijaiyyahError):
    """Raised when a Cell IR graph violates type, arity, or mathematical domain rules."""

    def __init__(self, message: str, cell_id: str, line: int = 1, col: int = 1) -> None:
        self.cell_id = cell_id
        self.line = line
        self.col = col
        super().__init__(f"L{line}:{col} [{cell_id}]: {message}")


@dataclass
class SemanticAnalysisReport:
    """Summary of semantic validation and two-layer proof discharge on a `CellIRGraph`."""

    valid: bool
    node_count: int
    guards_total: int = 0
    guards_discharged: int = 0
    guards_mandatory_runtime: int = 0
    runtime_hstar_checks_required: int = 0
    overflow_warnings: list[str] = field(default_factory=list)
    guard_certificates: list[SixGuardClosureProof] = field(default_factory=list)


class SemanticAnalyzer:
    """Shared semantic analyzer for both `.hcell` and `.hc` Cell IR graphs."""

    def __init__(self, *, reject_static_overflow: bool = False) -> None:
        self._reject_overflow = reject_static_overflow

    def analyze(self, graph: CellIRGraph) -> SemanticAnalysisReport:
        report = SemanticAnalysisReport(valid=True, node_count=len(graph.nodes))

        for sub in graph.subroutines.values():
            for cid in sub.body_node_ids:
                self._validate_node(graph, graph.nodes[cid], report)

        for cid in graph.order:
            node = graph.nodes[cid]
            self._validate_node(graph, node, report)

        return report

    def _validate_node(
        self,
        graph: CellIRGraph,
        node: CellIRNode,
        report: SemanticAnalysisReport,
        *,
        in_unbounded_loop: bool = False,
    ) -> None:
        op = node.op
        inputs = [graph.nodes[inp] for inp in node.inputs]

        if op == CellOp.LETTER_CONST:
            self._require_arity(node, inputs, 0)
            if node.imm_param is None:
                raise CellSemanticError(
                    "LETTER_CONST missing Master Table index",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            rec = MASTER_TABLE_ENGINE.get_by_index(node.imm_param)
            if rec is None:
                raise CellSemanticError(
                    f"Invalid Master Table index {node.imm_param}",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            pbound = analyze_prefix_bounds([rec.v18])
            proof = prove_six_guard_closure(
                rec.v18,
                prefix_bound=pbound,
                path_class=PathSafetyClass.STRAIGHT_LINE_BOUNDED,
            )
            node.output_type = CellValueType.HYBIT
            node.static_vector = rec.v18
            node.max_component = max(rec.v18)
            node.six_guard_proof = proof
            node.proven_in_H = proof.layer_a_all_six_pass
            node.hardware_8bit_safe = proof.all_six_proven_and_hw_isomorphic
            node.hstar_coupled_bound_proven = proof.hstar_coupled_bound_proven
            node.provenance_note = (
                f"sealed letter {rec.char} ({rec.name}, {rec.har_ref}); "
                "Layer A (G1-G4,T1-T2)=PASS, Layer B (8-bit, H*==Ka)=PASS"
            )
            return

        if op == CellOp.WORD_ACCUM:
            self._require_arity(node, inputs, 0)
            if not node.letter_sequence:
                raise CellSemanticError(
                    "WORD_ACCUM requires at least one Hijaiyyah letter",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            bound = analyze_h0_letter_accumulation(node.letter_sequence)
            node.output_type = CellValueType.HYBIT
            node.static_vector = bound.exact_sum_vector
            node.max_component = bound.max_exact_component
            node.six_guard_proof = bound.six_guard_proof
            node.proven_in_H = bound.mathematically_in_H
            node.hardware_8bit_safe = bound.six_guard_proof.all_six_proven_and_hw_isomorphic
            node.hstar_coupled_bound_proven = bound.six_guard_proof.hstar_coupled_bound_proven
            node.use_h0_native_opcodes = bound.hardware_isomorphic
            if not bound.hardware_isomorphic:
                msg = (
                    f"Cell {node.cell_id} word accumulation overflows 8-bit H-Reg "
                    f"at indices {list(bound.overflowed_components)} "
                    f"(first overflow step {bound.prefix_bound.first_overflow_step}, "
                    f"max component {bound.max_exact_component} > {HREG_COMPONENT_MAX})"
                )
                report.overflow_warnings.append(msg)
                if self._reject_overflow:
                    raise CellSemanticError(
                        msg, node.cell_id, node.span.line, node.span.col
                    )
            node.provenance_note = (
                f"word accumulation of {len(node.letter_sequence)} letters; "
                f"max_component={bound.max_exact_component}; "
                f"LayerA={bound.mathematically_in_H}, LayerB={node.hardware_8bit_safe}"
            )
            return

        if op == CellOp.ZERO_HYBIT:
            self._require_arity(node, inputs, 0)
            zero_vec = tuple([0] * 18)
            pbound = analyze_prefix_bounds([zero_vec])
            proof = prove_six_guard_closure(
                zero_vec,
                prefix_bound=pbound,
                path_class=PathSafetyClass.STRAIGHT_LINE_BOUNDED,
            )
            node.output_type = CellValueType.HYBIT
            node.static_vector = zero_vec
            node.max_component = 0
            node.six_guard_proof = proof
            node.proven_in_H = True
            node.hardware_8bit_safe = True
            node.hstar_coupled_bound_proven = True
            node.provenance_note = (
                "monoid identity 0 in N_0^18; Layer A (G1-G4,T1-T2)=PASS, Layer B=PASS"
            )
            return

        if op == CellOp.LOAD_ID:
            self._require_arity(node, inputs, 1)
            self._require_type(node, inputs[0], CellValueType.SCALAR)
            idx = inputs[0].static_scalar
            node.output_type = CellValueType.HYBIT
            if idx is not None and not in_unbounded_loop:
                if not 1 <= idx <= 28:
                    raise CellSemanticError(
                        f"load_id({idx}) out of canonical range 1..28",
                        node.cell_id,
                        node.span.line,
                        node.span.col,
                    )
                rec = MASTER_TABLE_ENGINE.get_by_index(idx)
                assert rec is not None
                pbound = analyze_prefix_bounds([rec.v18])
                proof = prove_six_guard_closure(
                    rec.v18,
                    prefix_bound=pbound,
                    path_class=PathSafetyClass.STRAIGHT_LINE_BOUNDED,
                )
                node.static_vector = rec.v18
                node.max_component = max(rec.v18)
                node.six_guard_proof = proof
                node.proven_in_H = proof.layer_a_all_six_pass
                node.hardware_8bit_safe = proof.all_six_proven_and_hw_isomorphic
                node.hstar_coupled_bound_proven = proof.hstar_coupled_bound_proven
                node.imm_param = idx
                node.provenance_note = f"static load_id({idx}) -> {rec.char}"
            else:
                node.static_vector = None
                node.max_component = MAX_CANONICAL_LETTER_COMPONENT
                node.proven_in_H = True
                node.hardware_8bit_safe = True
                node.hstar_coupled_bound_proven = True
                node.provenance_note = (
                    "dynamic load_id returns a sealed letter (max_component <= 8, H*==Ka) or halts"
                )
            return

        if op == CellOp.HFS_READ_HYBIT:
            self._require_arity(node, inputs, 1)
            self._require_type(node, inputs[0], CellValueType.SCALAR)
            node.output_type = CellValueType.HYBIT
            node.static_vector = None
            node.max_component = None
            node.proven_in_H = False
            node.hardware_8bit_safe = False
            node.hstar_coupled_bound_proven = False
            node.provenance_note = (
                "HFS_READ (SYSCALL 7) crosses storage trust boundary: "
                "runtime HGRD + runtime H*==Ka verification required"
            )
            return

        if op == CellOp.HOS_SYSCALL:
            if not 2 <= len(inputs) <= 3:
                raise CellSemanticError(
                    f"HOS_SYSCALL (⏣) requires 2 or 3 arguments, got {len(inputs)}",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            self._require_type(node, inputs[0], CellValueType.SCALAR)
            self._require_type(node, inputs[1], CellValueType.SCALAR)
            if len(inputs) == 3:
                self._require_type(node, inputs[2], CellValueType.HYBIT)
            node.output_type = CellValueType.SCALAR
            return

        if op in (CellOp.SCALAR_CONST, CellOp.FN_PARAM):
            self._require_arity(node, inputs, 0)
            node.output_type = CellValueType.SCALAR
            return

        if op == CellOp.HYBIT_ADD:
            self._require_arity(node, inputs, 2)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            self._require_type(node, inputs[1], CellValueType.HYBIT)
            left, right = inputs[0], inputs[1]
            node.output_type = CellValueType.HYBIT

            if in_unbounded_loop:
                node.static_vector = None
                node.max_component = None
                node.six_guard_proof = None
                node.proven_in_H = left.proven_in_H and right.proven_in_H
                node.hardware_8bit_safe = False
                node.hstar_coupled_bound_proven = False
                node.provenance_note = (
                    "addition inside unbounded loop (UNBOUNDED_OR_DYNAMIC_PATH): "
                    "Layer B 8-bit & H* bound unproven"
                )
                return

            if node.letter_sequence:
                bound = analyze_h0_letter_accumulation(node.letter_sequence)
                node.static_vector = bound.exact_sum_vector
                node.max_component = bound.max_exact_component
                node.six_guard_proof = bound.six_guard_proof
                node.proven_in_H = (
                    left.proven_in_H and right.proven_in_H and bound.mathematically_in_H
                )
                node.hardware_8bit_safe = (
                    node.proven_in_H
                    and left.hardware_8bit_safe
                    and right.hardware_8bit_safe
                    and bound.six_guard_proof.all_six_proven_and_hw_isomorphic
                )
                node.hstar_coupled_bound_proven = (
                    node.hardware_8bit_safe
                    and left.hstar_coupled_bound_proven
                    and right.hstar_coupled_bound_proven
                    and bound.six_guard_proof.hstar_coupled_bound_proven
                )
            elif left.static_vector is not None and right.static_vector is not None:
                vec = tuple(
                    a + b for a, b in zip(left.static_vector, right.static_vector, strict=True)
                )
                pbound = analyze_prefix_bounds([left.static_vector, right.static_vector])
                proof = prove_six_guard_closure(
                    vec,
                    prefix_bound=pbound,
                    path_class=PathSafetyClass.STRAIGHT_LINE_BOUNDED,
                )
                node.static_vector = vec
                node.max_component = max(vec)
                node.six_guard_proof = proof
                node.proven_in_H = (
                    left.proven_in_H and right.proven_in_H and proof.layer_a_all_six_pass
                )
                node.hardware_8bit_safe = (
                    node.proven_in_H
                    and left.hardware_8bit_safe
                    and right.hardware_8bit_safe
                    and proof.all_six_proven_and_hw_isomorphic
                )
                node.hstar_coupled_bound_proven = (
                    node.hardware_8bit_safe
                    and left.hstar_coupled_bound_proven
                    and right.hstar_coupled_bound_proven
                    and proof.hstar_coupled_bound_proven
                )
            else:
                if left.max_component is not None and right.max_component is not None:
                    node.max_component = left.max_component + right.max_component
                else:
                    node.max_component = None
                node.proven_in_H = left.proven_in_H and right.proven_in_H
                node.hardware_8bit_safe = (
                    node.proven_in_H
                    and left.hardware_8bit_safe
                    and right.hardware_8bit_safe
                    and node.max_component is not None
                    and node.max_component <= HREG_COMPONENT_MAX
                )
                node.hstar_coupled_bound_proven = (
                    node.hardware_8bit_safe
                    and left.hstar_coupled_bound_proven
                    and right.hstar_coupled_bound_proven
                )

            if node.letter_sequence and node.hardware_8bit_safe:
                node.use_h0_native_opcodes = True

            if node.max_component is not None and node.max_component > HREG_COMPONENT_MAX:
                msg = (
                    f"Cell {node.cell_id} addition exceeds 8-bit H-Reg component bound: "
                    f"{node.max_component} > {HREG_COMPONENT_MAX}"
                )
                report.overflow_warnings.append(msg)
                if self._reject_overflow:
                    raise CellSemanticError(
                        msg, node.cell_id, node.span.line, node.span.col
                    )
            node.provenance_note = (
                f"monoid closure under + (Layer A: G1-G4,T1-T2={node.proven_in_H}; "
                f"Layer B: max={node.max_component}, hw_8bit_safe={node.hardware_8bit_safe})"
            )
            return

        if op == CellOp.HYBIT_DELTA:
            self._require_arity(node, inputs, 2)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            self._require_type(node, inputs[1], CellValueType.HYBIT)
            node.output_type = CellValueType.DELTA14
            if inputs[0].static_vector is not None and inputs[1].static_vector is not None:
                node.static_vector = tuple(
                    inputs[0].static_vector[i] - inputs[1].static_vector[i]
                    for i in range(14)
                )
            node.proven_in_H = False
            node.hardware_8bit_safe = False
            node.hstar_coupled_bound_proven = False
            node.provenance_note = (
                "Delta(a, b) in Z^14 (Domain C); outside monoid H (no additive inverse)"
            )
            return

        if op == CellOp.HYBIT_EQ:
            self._require_arity(node, inputs, 2)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            self._require_type(node, inputs[1], CellValueType.HYBIT)
            node.output_type = CellValueType.SCALAR
            return

        if op in (CellOp.SCALAR_ADD, CellOp.SCALAR_SUB, CellOp.SCALAR_MUL):
            self._require_arity(node, inputs, 2)
            self._require_type(node, inputs[0], CellValueType.SCALAR)
            self._require_type(node, inputs[1], CellValueType.SCALAR)
            node.output_type = CellValueType.SCALAR
            a_val, b_val = inputs[0].static_scalar, inputs[1].static_scalar
            if a_val is not None and b_val is not None and not in_unbounded_loop:
                if op == CellOp.SCALAR_ADD:
                    node.static_scalar = a_val + b_val
                elif op == CellOp.SCALAR_SUB:
                    node.static_scalar = a_val - b_val
                else:
                    node.static_scalar = a_val * b_val
            return

        if op in (
            CellOp.CMP_EQ,
            CellOp.CMP_NE,
            CellOp.CMP_LT,
            CellOp.CMP_GT,
            CellOp.CMP_LE,
            CellOp.CMP_GE,
        ):
            self._require_arity(node, inputs, 2)
            self._require_type(node, inputs[0], CellValueType.SCALAR)
            self._require_type(node, inputs[1], CellValueType.SCALAR)
            node.output_type = CellValueType.SCALAR
            return

        if op in (
            CellOp.PROJ_COMPONENT,
            CellOp.PROJ_THETA,
            CellOp.PROJ_HSTAR,
            CellOp.TURNING_U,
            CellOp.TURNING_RHO,
            CellOp.MOD4_GATE,
            CellOp.NORM2_V14,
            CellOp.EXOMATRIX_PHI,
            CellOp.HISAB_PACK,
            CellOp.HISAB_CRC,
        ):
            self._require_arity(node, inputs, 1)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            node.output_type = CellValueType.SCALAR
            src = inputs[0]

            if op == CellOp.PROJ_COMPONENT:
                if node.imm_param is None or not 0 <= node.imm_param <= 17:
                    raise CellSemanticError(
                        f"Component index {node.imm_param} out of range 0..17",
                        node.cell_id,
                        node.span.line,
                        node.span.col,
                    )
            if op == CellOp.HISAB_PACK:
                if node.imm_param is None or not 0 <= node.imm_param <= 2:
                    raise CellSemanticError(
                        f"HISAB pack word index {node.imm_param} out of range 0..2",
                        node.cell_id,
                        node.span.line,
                        node.span.col,
                    )

            if src.static_vector is not None and src.hardware_8bit_safe and not in_unbounded_loop:
                v = list(src.static_vector)
                if op == CellOp.PROJ_THETA:
                    node.static_scalar = v[0]
                elif op == CellOp.PROJ_HSTAR:
                    node.static_scalar = v[17]
                elif op == CellOp.PROJ_COMPONENT and node.imm_param is not None:
                    node.static_scalar = v[node.imm_param]
                elif op == CellOp.TURNING_U:
                    node.static_scalar = compute_U(v)
                elif op == CellOp.TURNING_RHO:
                    node.static_scalar = compute_rho(v)
                elif op == CellOp.MOD4_GATE:
                    node.static_scalar = v[0] % 4
                elif op == CellOp.NORM2_V14:
                    node.static_scalar = sum(x * x for x in v[:14])
                elif op == CellOp.EXOMATRIX_PHI:
                    exo = build_exomatrix(v)
                    node.static_scalar = sum(
                        exo[r][c] ** 2 for r in range(5) for c in range(5)
                    )
            return

        if op in (CellOp.PROJ_GROUP_N, CellOp.PROJ_GROUP_A):
            self._require_arity(node, inputs, 1)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            node.output_type = CellValueType.VECTOR3
            return

        if op in (CellOp.PROJ_GROUP_K, CellOp.PROJ_GROUP_Q):
            self._require_arity(node, inputs, 1)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            node.output_type = CellValueType.VECTOR5
            return

        if op in (CellOp.DIST2_V14, CellOp.INNER_V14):
            self._require_arity(node, inputs, 2)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            self._require_type(node, inputs[1], CellValueType.HYBIT)
            node.output_type = CellValueType.SCALAR
            a, b = inputs[0], inputs[1]
            if (
                a.static_vector is not None
                and b.static_vector is not None
                and a.hardware_8bit_safe
                and b.hardware_8bit_safe
                and not in_unbounded_loop
            ):
                if op == CellOp.DIST2_V14:
                    node.static_scalar = sum(
                        (a.static_vector[i] - b.static_vector[i]) ** 2 for i in range(14)
                    )
                else:
                    node.static_scalar = sum(
                        a.static_vector[i] * b.static_vector[i] for i in range(14)
                    )
            return

        if op == CellOp.GUARD_CHECK:
            self._require_arity(node, inputs, 1)
            self._require_type(node, inputs[0], CellValueType.HYBIT)
            target = inputs[0]
            node.output_type = CellValueType.BOOL
            node.six_guard_proof = target.six_guard_proof
            node.hstar_coupled_bound_proven = (
                target.hstar_coupled_bound_proven and not in_unbounded_loop
            )
            if target.six_guard_proof is not None:
                report.guard_certificates.append(target.six_guard_proof)
            report.guards_total += 1
            all_six_ok = (
                target.six_guard_proof.all_six_proven_and_hw_isomorphic
                if target.six_guard_proof is not None
                else (
                    target.proven_in_H
                    and target.hardware_8bit_safe
                    and target.hstar_coupled_bound_proven
                )
            )
            if (
                not in_unbounded_loop
                and target.proven_in_H
                and target.hardware_8bit_safe
                and target.hstar_coupled_bound_proven
                and all_six_ok
            ):
                node.guard_discharged = True
                report.guards_discharged += 1
                node.provenance_note = (
                    f"HGRD discharged statically: {target.provenance_note}"
                )
            else:
                node.guard_discharged = False
                report.guards_mandatory_runtime += 1
                if not node.hstar_coupled_bound_proven:
                    report.runtime_hstar_checks_required += 1
                node.provenance_note = (
                    f"HGRD mandatory at runtime: proven_in_H={target.proven_in_H}, "
                    f"hw_8bit_safe={target.hardware_8bit_safe}, "
                    f"hstar_coupled={node.hstar_coupled_bound_proven} "
                    f"(max_component={target.max_component})"
                )
            return

        if op == CellOp.EMIT_OUTPUT:
            self._require_arity(node, inputs, 1)
            if inputs[0].output_type != CellValueType.SCALAR:
                raise CellSemanticError(
                    f"EMIT_OUTPUT (↦ / PRINT) requires a SCALAR operand, "
                    f"got {inputs[0].output_type.value}",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            node.output_type = CellValueType.VOID
            return

        if op == CellOp.VAR_ASSIGN:
            self._require_arity(node, inputs, 1)
            val_node = inputs[0]
            node.output_type = val_node.output_type
            node.static_vector = val_node.static_vector
            node.max_component = val_node.max_component
            node.proven_in_H = val_node.proven_in_H
            node.hardware_8bit_safe = val_node.hardware_8bit_safe and not in_unbounded_loop
            node.hstar_coupled_bound_proven = (
                val_node.hstar_coupled_bound_proven and not in_unbounded_loop
            )
            node.six_guard_proof = None if in_unbounded_loop else val_node.six_guard_proof
            return

        if op == CellOp.COND_BRANCH:
            self._require_arity(node, inputs, 1)
            if inputs[0].output_type not in (CellValueType.BOOL, CellValueType.SCALAR):
                raise CellSemanticError(
                    "COND_BRANCH condition must be BOOL or SCALAR",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            pre_bounds: dict[str, tuple[bool, bool, bool, int | None]] = {
                bname: (
                    graph.nodes[rcid].proven_in_H,
                    graph.nodes[rcid].hardware_8bit_safe,
                    graph.nodes[rcid].hstar_coupled_bound_proven,
                    graph.nodes[rcid].max_component,
                )
                for bname, rcid in graph.bindings.items()
            }
            then_assigns: dict[str, CellIRNode] = {}
            else_assigns: dict[str, CellIRNode] = {}

            for cid in node.then_node_ids:
                cnode = graph.nodes[cid]
                self._validate_node(graph, cnode, report, in_unbounded_loop=in_unbounded_loop)
                if cnode.op == CellOp.VAR_ASSIGN and cnode.binding_name:
                    then_assigns[cnode.binding_name] = cnode

            for cid in node.else_node_ids:
                cnode = graph.nodes[cid]
                self._validate_node(graph, cnode, report, in_unbounded_loop=in_unbounded_loop)
                if cnode.op == CellOp.VAR_ASSIGN and cnode.binding_name:
                    else_assigns[cnode.binding_name] = cnode

            modified_names = set(then_assigns) | set(else_assigns)
            for bname in modified_names:
                if bname not in graph.bindings:
                    continue
                root_node = graph.nodes[graph.bindings[bname]]
                if root_node.output_type != CellValueType.HYBIT:
                    continue
                pre_in_h, pre_safe, pre_hstar, pre_max = pre_bounds[bname]
                t_in_h = then_assigns[bname].proven_in_H if bname in then_assigns else pre_in_h
                t_safe = (
                    then_assigns[bname].hardware_8bit_safe if bname in then_assigns else pre_safe
                )
                t_hstar = (
                    then_assigns[bname].hstar_coupled_bound_proven
                    if bname in then_assigns
                    else pre_hstar
                )
                t_max = then_assigns[bname].max_component if bname in then_assigns else pre_max

                e_in_h = else_assigns[bname].proven_in_H if bname in else_assigns else pre_in_h
                e_safe = (
                    else_assigns[bname].hardware_8bit_safe if bname in else_assigns else pre_safe
                )
                e_hstar = (
                    else_assigns[bname].hstar_coupled_bound_proven
                    if bname in else_assigns
                    else pre_hstar
                )
                e_max = else_assigns[bname].max_component if bname in else_assigns else pre_max

                join_max = (
                    max(t_max, e_max)
                    if (t_max is not None and e_max is not None)
                    else None
                )
                join_in_h = t_in_h and e_in_h
                join_safe = (
                    join_in_h
                    and t_safe
                    and e_safe
                    and join_max is not None
                    and join_max <= HREG_COMPONENT_MAX
                    and not in_unbounded_loop
                )
                root_node.static_vector = None
                root_node.max_component = join_max
                root_node.proven_in_H = join_in_h
                root_node.hardware_8bit_safe = join_safe
                root_node.hstar_coupled_bound_proven = join_safe and t_hstar and e_hstar
                root_node.six_guard_proof = None
                root_node.provenance_note = (
                    f"branch join ({PathSafetyClass.BRANCH_JOIN_BOUNDED.value}): "
                    f"max_component={join_max}, hw_8bit_safe={join_safe}"
                )
            node.output_type = CellValueType.VOID
            return

        if op == CellOp.WHILE_LOOP:
            self._require_arity(node, inputs, 1)
            for cid in node.loop_cond_node_ids:
                if cid != node.inputs[0]:
                    self._validate_node(graph, graph.nodes[cid], report, in_unbounded_loop=True)
            self._validate_node(graph, inputs[0], report, in_unbounded_loop=True)

            for cid in node.loop_body_node_ids:
                cnode = graph.nodes[cid]
                if cnode.op == CellOp.VAR_ASSIGN and cnode.binding_name in graph.bindings:
                    root_node = graph.nodes[graph.bindings[cnode.binding_name]]
                    root_node.static_vector = None
                    root_node.static_scalar = None
                    root_node.max_component = None
                    root_node.hardware_8bit_safe = False
                    root_node.hstar_coupled_bound_proven = False
                    root_node.six_guard_proof = None
                    root_node.provenance_note = (
                        f"mutated in WHILE_LOOP "
                        f"({PathSafetyClass.UNBOUNDED_OR_DYNAMIC_PATH.value}): "
                        "Layer B prefix & H* bound unproven; mandatory runtime HGRD"
                    )

            for cid in node.loop_body_node_ids:
                self._validate_node(graph, graph.nodes[cid], report, in_unbounded_loop=True)
            node.output_type = CellValueType.VOID
            return

        if op == CellOp.FN_CALL:
            if not node.callee_name or node.callee_name not in graph.subroutines:
                raise CellSemanticError(
                    f"Call to undefined subroutine {node.callee_name!r}",
                    node.cell_id,
                    node.span.line,
                    node.span.col,
                )
            sub = graph.subroutines[node.callee_name]
            self._require_arity(node, inputs, len(sub.params))
            for child in inputs:
                self._require_type(node, child, CellValueType.SCALAR)
            node.output_type = sub.return_type
            return

    @staticmethod
    def _require_arity(
        node: CellIRNode, inputs: list[CellIRNode], expected: int
    ) -> None:
        if len(inputs) != expected:
            raise CellSemanticError(
                f"Operation {node.op.value} requires {expected} input(s), got {len(inputs)}",
                node.cell_id,
                node.span.line,
                node.span.col,
            )

    @staticmethod
    def _require_type(
        node: CellIRNode, child: CellIRNode, expected: CellValueType
    ) -> None:
        if child.output_type != expected:
            raise CellSemanticError(
                f"Operation {node.op.value} requires operand of type {expected.value}, "
                f"got {child.output_type.value} from cell '{child.cell_id}' "
                f"({child.source_glyphs})",
                node.cell_id,
                node.span.line,
                node.span.col,
            )


__all__ = [
    "CellSemanticError",
    "SemanticAnalysisReport",
    "SemanticAnalyzer",
]
