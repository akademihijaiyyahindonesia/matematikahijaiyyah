"""Phase 4.1 — Deterministic Reference Evaluator for Hijaiyyah Cells IR.

Executes `CellIRGraph` in topological/program order, recording a complete
`CellTraceEvent` per cell and supporting both exact N_0^18 mathematical
semantics and 8-bit hardware-wrapped H-Reg simulation (`hardware_8bit_wrap=True`),
including structured branches (`?`), bounded loops (`↻`), subroutines (`ƒ`),
18-component hybit equality (`HYBIT_EQ`), and official HOS syscalls (`⏣`, `⛁`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.cells.ir import CellIRGraph, CellIRNode, CellOp
from hijaiyyah.core.exceptions import HijaiyyahError
from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.guards import compute_rho, compute_U, full_guard_check
from hijaiyyah.hisab.serialize import (
    _compute_guard_status,
    _nibble_pack,
    serialize_letter,
)


class CellEvaluationError(HijaiyyahError):
    """Raised on runtime evaluation errors (e.g. failed guard assertion)."""


@dataclass(frozen=True, slots=True)
class CellTraceEvent:
    """One recorded step in the reference evaluation trace."""

    step: int
    cell_id: str
    op: str
    source_glyphs: str
    value: Any
    guard_discharged: bool = False


@dataclass
class CellEvaluationResult:
    """Deterministic result of evaluating a `CellIRGraph`."""

    values: dict[str, Any] = field(default_factory=dict)
    bindings: dict[str, Any] = field(default_factory=dict)
    outputs: list[int] = field(default_factory=list)
    hfs_files: dict[int, tuple[int, ...] | None] = field(default_factory=dict)
    syscall_log: list[tuple[int, int, int]] = field(default_factory=list)
    guard_checks_executed: int = 0
    guard_checks_discharged: int = 0
    last_guard_passed: bool = True
    sticky_hybit_ok: dict[str, bool] = field(default_factory=dict)
    trace: list[CellTraceEvent] = field(default_factory=list)


class CellEvaluator:
    """Reference evaluator for `CellIRGraph`."""

    def __init__(
        self,
        *,
        hardware_8bit_wrap: bool = False,
        fail_on_guard_error: bool = True,
        max_loop_iterations: int = 4096,
        valid_overlay_ids: set[int] | None = None,
    ) -> None:
        self._hw_wrap = hardware_8bit_wrap
        self._fail_on_guard = fail_on_guard_error
        self._max_iters = max_loop_iterations
        self._valid_overlays = valid_overlay_ids if valid_overlay_ids is not None else {1}
        self._step_counter = 0

    def _wrap_vec(self, vec: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        if self._hw_wrap:
            return tuple(x & 0xFF for x in vec)
        return tuple(vec)

    @staticmethod
    def _check_hybit_invariants(vec: tuple[int, ...] | list[int]) -> bool:
        v_chk = list(vec)
        hstar_ok = (v_chk[17] == v_chk[7]) and (v_chk[17] <= (v_chk[0] >> 1))
        return bool(full_guard_check(v_chk)["all_pass"]) and hstar_ok

    def evaluate(
        self,
        graph: CellIRGraph,
        dynamic_inputs: dict[str, Any] | None = None,
    ) -> CellEvaluationResult:
        res = CellEvaluationResult()
        preset = dynamic_inputs or {}
        self._step_counter = 0

        for cid in graph.order:
            self._exec_node_id(graph, cid, res, preset)

        return res

    def _exec_node_id(
        self,
        graph: CellIRGraph,
        cid: str,
        res: CellEvaluationResult,
        preset: dict[str, Any],
    ) -> Any:
        node = graph.nodes[cid]
        if cid in preset:
            val = preset[cid]
        else:
            val = self._eval_node(graph, node, res, preset)

        res.values[cid] = val
        if node.binding_name and node.op != CellOp.VAR_ASSIGN:
            res.bindings[node.binding_name] = val
            if isinstance(val, tuple) and len(val) == 18:
                res.sticky_hybit_ok[cid] = self._check_hybit_invariants(val)

        self._step_counter += 1
        res.trace.append(
            CellTraceEvent(
                step=self._step_counter,
                cell_id=cid,
                op=node.op.value,
                source_glyphs=node.source_glyphs,
                value=val,
                guard_discharged=node.guard_discharged,
            )
        )
        return val

    def _eval_node(
        self,
        graph: CellIRGraph,
        node: CellIRNode,
        res: CellEvaluationResult,
        preset: dict[str, Any],
    ) -> Any:
        op = node.op

        if op == CellOp.COND_BRANCH:
            cond_val = bool(res.values[node.inputs[0]])
            branch_ids = node.then_node_ids if cond_val else node.else_node_ids
            for bcid in branch_ids:
                self._exec_node_id(graph, bcid, res, preset)
            return int(cond_val)

        if op == CellOp.WHILE_LOOP:
            iters = 0
            while True:
                for ccid in node.loop_cond_node_ids:
                    self._exec_node_id(graph, ccid, res, preset)
                cond_val = bool(res.values[node.inputs[0]])
                if not cond_val:
                    break
                iters += 1
                if iters > self._max_iters:
                    raise CellEvaluationError(
                        f"Loop {node.cell_id} exceeded max iterations ({self._max_iters})"
                    )
                for bcid in node.loop_body_node_ids:
                    self._exec_node_id(graph, bcid, res, preset)
            return iters

        in_vals = [res.values[inp] for inp in node.inputs]

        if op == CellOp.VAR_ASSIGN:
            val = in_vals[0]
            if node.binding_name:
                res.bindings[node.binding_name] = val
                if node.binding_name in graph.bindings:
                    root_cid = graph.bindings[node.binding_name]
                    res.values[root_cid] = val
                    if isinstance(val, tuple) and len(val) == 18:
                        res.sticky_hybit_ok[root_cid] = (
                            res.sticky_hybit_ok.get(root_cid, True)
                            and self._check_hybit_invariants(val)
                        )
            return val

        if op == CellOp.FN_PARAM:
            return res.values.get(node.cell_id, 0)

        if op == CellOp.FN_CALL:
            assert node.callee_name is not None
            sub = graph.subroutines[node.callee_name]
            saved_vals = {pid: res.values.get(pid) for pid in sub.param_node_ids}
            for pid, arg_val in zip(sub.param_node_ids, in_vals, strict=True):
                res.values[pid] = arg_val
            ret_val: Any = 0
            for bcid in sub.body_node_ids:
                if graph.nodes[bcid].op == CellOp.FN_PARAM:
                    continue
                self._exec_node_id(graph, bcid, res, preset)
            if sub.return_node_id:
                ret_val = res.values[sub.return_node_id]
            for pid, old_v in saved_vals.items():
                if old_v is not None:
                    res.values[pid] = old_v
            return ret_val

        if op == CellOp.HOS_SYSCALL:
            sys_num = int(in_vals[0])
            arg = int(in_vals[1])
            ret_status = 0
            if sys_num == 1:  # write (PRINT R2)
                res.outputs.append(arg)
                ret_status = 1
            elif sys_num == 2:  # read (non-blocking UART RX -> 0 when empty)
                ret_status = 0
            elif sys_num == 3:  # yield
                ret_status = 1
            elif sys_num == 4:  # exit
                ret_status = 1
            elif sys_num == 6:  # HFS_CREATE (file_id 0..7)
                if 0 <= arg <= 7 and arg not in res.hfs_files:
                    res.hfs_files[arg] = None
                    ret_status = 1
                else:
                    ret_status = 0
            elif sys_num == 7:  # HFS_READ status check
                vec = res.hfs_files.get(arg)
                ret_status = 1 if (0 <= arg <= 7 and vec is not None) else 0
            elif sys_num == 8:  # HFS_WRITE (file_id 0..7, hybit in H0)
                if len(in_vals) == 3 and 0 <= arg <= 7 and arg in res.hfs_files:
                    payload = tuple(in_vals[2])
                    if full_guard_check(list(payload))["all_pass"]:
                        res.hfs_files[arg] = payload
                        ret_status = 1
            elif sys_num == 9:  # LOAD_PROGRAM
                ret_status = 1 if arg in self._valid_overlays else 0
            res.syscall_log.append((sys_num, arg, ret_status))
            return ret_status

        if op == CellOp.HFS_READ_HYBIT:
            fid = int(in_vals[0])
            vec = res.hfs_files.get(fid)
            status = 1 if (0 <= fid <= 7 and vec is not None) else 0
            res.syscall_log.append((7, fid, status))
            if vec is None:
                return tuple([0] * 18)
            return vec

        if op == CellOp.LETTER_CONST:
            assert node.imm_param is not None
            rec = MASTER_TABLE_ENGINE.get_by_index(node.imm_param)
            if rec is None:
                raise CellEvaluationError(f"Unknown letter index {node.imm_param}")
            return rec.v18

        if op == CellOp.WORD_ACCUM:
            acc = [0] * 18
            for ch in node.letter_sequence:
                rec = MASTER_TABLE_ENGINE.get_by_char(ch)
                if rec is None:
                    raise CellEvaluationError(f"Unknown letter {ch!r}")
                for j in range(18):
                    acc[j] = acc[j] + rec.v18[j]
                    if self._hw_wrap:
                        acc[j] &= 0xFF
            return tuple(acc)

        if op == CellOp.ZERO_HYBIT:
            return tuple([0] * 18)

        if op == CellOp.LOAD_ID:
            idx = int(in_vals[0])
            rec = MASTER_TABLE_ENGINE.get_by_index(idx)
            if rec is None:
                raise CellEvaluationError(f"load_id({idx}) out of range 1..28")
            return rec.v18

        if op == CellOp.SCALAR_CONST:
            assert node.imm_param is not None
            return int(node.imm_param)

        if op == CellOp.HYBIT_ADD:
            a, b = in_vals[0], in_vals[1]
            return self._wrap_vec([a[i] + b[i] for i in range(18)])

        if op == CellOp.HYBIT_DELTA:
            a, b = in_vals[0], in_vals[1]
            return tuple(a[i] - b[i] for i in range(14))

        if op == CellOp.HYBIT_EQ:
            return int(tuple(in_vals[0]) == tuple(in_vals[1]))

        if op == CellOp.SCALAR_ADD:
            return (int(in_vals[0]) + int(in_vals[1])) & 0xFFFFFFFF

        if op == CellOp.SCALAR_SUB:
            return (int(in_vals[0]) - int(in_vals[1])) & 0xFFFFFFFF

        if op == CellOp.SCALAR_MUL:
            return (int(in_vals[0]) * int(in_vals[1])) & 0xFFFFFFFF

        if op == CellOp.CMP_EQ:
            return int(int(in_vals[0]) == int(in_vals[1]))

        if op == CellOp.CMP_NE:
            return int(int(in_vals[0]) != int(in_vals[1]))

        if op == CellOp.CMP_LT:
            return int(int(in_vals[0]) < int(in_vals[1]))

        if op == CellOp.CMP_GT:
            return int(int(in_vals[0]) > int(in_vals[1]))

        if op == CellOp.CMP_LE:
            return int(int(in_vals[0]) <= int(in_vals[1]))

        if op == CellOp.CMP_GE:
            return int(int(in_vals[0]) >= int(in_vals[1]))

        if op == CellOp.PROJ_THETA:
            return int(in_vals[0][0])

        if op == CellOp.PROJ_HSTAR:
            return int(in_vals[0][17])

        if op == CellOp.PROJ_COMPONENT:
            assert node.imm_param is not None
            if not 0 <= node.imm_param <= 17:
                return 0
            return int(in_vals[0][node.imm_param])

        if op == CellOp.TURNING_U:
            u_val = compute_U(list(in_vals[0]))
            return (u_val & 0x7FF) if self._hw_wrap else u_val

        if op == CellOp.TURNING_RHO:
            rho_val = compute_rho(list(in_vals[0]))
            return (rho_val & 0xFFFFFFFF) if self._hw_wrap else rho_val

        if op == CellOp.MOD4_GATE:
            return int(in_vals[0][0]) & 0x3

        if op == CellOp.NORM2_V14:
            v = in_vals[0]
            return sum(int(v[i]) ** 2 for i in range(14))

        if op == CellOp.DIST2_V14:
            a, b = in_vals[0], in_vals[1]
            return sum((int(a[i]) - int(b[i])) ** 2 for i in range(14))

        if op == CellOp.INNER_V14:
            a, b = in_vals[0], in_vals[1]
            return sum(int(a[i]) * int(b[i]) for i in range(14))

        if op == CellOp.PROJ_GROUP_N:
            v = in_vals[0]
            return (v[1], v[2], v[3])

        if op == CellOp.PROJ_GROUP_K:
            v = in_vals[0]
            return (v[4], v[5], v[6], v[7], v[8])

        if op == CellOp.PROJ_GROUP_Q:
            v = in_vals[0]
            return (v[9], v[10], v[11], v[12], v[13])

        if op == CellOp.PROJ_GROUP_A:
            v = in_vals[0]
            return (v[14], v[15], v[16])

        if op == CellOp.EXOMATRIX_PHI:
            exo = build_exomatrix(list(in_vals[0]))
            return sum(exo[r][c] ** 2 for r in range(5) for c in range(5))

        if op == CellOp.HISAB_PACK:
            assert node.imm_param is not None
            v_list = list(in_vals[0])
            packed = _nibble_pack(v_list)
            words = [
                int.from_bytes(packed[0:4], "little"),
                int.from_bytes(packed[4:8], "little"),
                (_compute_guard_status(v_list) << 8) | packed[8],
            ]
            return words[node.imm_param]

        if op == CellOp.HISAB_CRC:
            return serialize_letter(list(in_vals[0])).digest

        if op == CellOp.GUARD_CHECK:
            if node.guard_discharged and not self._hw_wrap:
                res.guard_checks_discharged += 1
                res.last_guard_passed = True
                return True
            res.guard_checks_executed += 1
            v_chk = list(in_vals[0])
            sticky_ok = res.sticky_hybit_ok.get(node.inputs[0], True)
            ok = self._check_hybit_invariants(v_chk) and sticky_ok
            res.last_guard_passed = ok
            if not ok and self._fail_on_guard:
                raise CellEvaluationError(
                    f"Guard check failed on cell {node.inputs[0]} ({node.source_glyphs})"
                )
            return ok

        if op == CellOp.EMIT_OUTPUT:
            scalar = int(in_vals[0])
            res.outputs.append(scalar)
            return scalar

        raise CellEvaluationError(f"Unsupported CellOp in evaluator: {op}")


__all__ = [
    "CellEvaluationError",
    "CellEvaluationResult",
    "CellEvaluator",
    "CellTraceEvent",
]
