"""Phase 4.3 — HISA Backend Compiler for Hijaiyyah Cells IR.

Implements Owner Engineering Decisions 2, 5, and 7, Priority 2 Backend Correctness,
Section A H* Safety Contract, and Wave 2 Official HOS Syscall Lowering:
- Never allocates GPRs above R15 (`GPR_FIRST = 1, GPR_LAST = 15`).
- Enforces the `R0` ABI rule (`R0` is a writable 32-bit register on HCPU reserved
  as the compiler/ABI scratch & MMIO base register).
- Lowers `TURNING_U` (`U(x)`) to hardware `CU` (`0x4D`, 1 instruction, 1 GPR).
- Lowers `TURNING_RHO` (`ρ(x)`) to hardware `CRHO` (`0x4C`, 1 instruction, 1 GPR).
- Lowers `MOD4_GATE` (`Θ₄(x)`) to hardware `CMOD4` (`0x4F`, 1 instruction, 1 GPR).
- Lowers `HYBIT_EQ` (`a == b` for hybits) to hardware `CEQ` (`0x47`, 18 components
  including `H*`).
- Lowers `HOS_SYSCALL` (`⏣`) and `HFS_READ_HYBIT` (`⛁`) to official `SYSCALL` (`0x09`)
  sequences preserving caller-live `R1`, `R2`, and `H0`.
- Elides `HGRD` if and only if the shared SemanticAnalyzer proved Layer A (all 6
  guards), Layer B (`max_component <= 255` across all prefixes), and `H* == Ka`.
  When `hstar_coupled_bound_proven` is `False` on a dynamic path, emits both
  `HGRD` and a runtime `H* == Ka` check (`CGET` #17 vs `CGET` #7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hijaiyyah.cells.dataset_engine import MASTER_TABLE_ENGINE
from hijaiyyah.cells.ir import CellIRGraph, CellIRNode, CellOp, CellSubroutineDef
from hijaiyyah.core.exceptions import HijaiyyahError
from hijaiyyah.hisa.assembler import assemble

GPR_SCRATCH: int = 0
GPR_FIRST: int = 1
GPR_LAST: int = 15

HREG_FIRST: int = 0
HREG_LAST: int = 15


class CellBackendError(HijaiyyahError):
    """Raised when a CellIRGraph cannot be lowered within HCPU hardware limits."""


@dataclass(frozen=True, slots=True)
class SourceInstructionMapEntry:
    """Auditable mapping from one Cell IR node to emitted HISA instructions."""

    cell_id: str
    op: str
    source_glyphs: str
    emitted_instructions: tuple[str, ...]
    allocated_register: str | None


@dataclass
class CompiledHISAProgram:
    """Compiled HISA assembly, machine words, and resource accounting."""

    assembly_lines: list[str] = field(default_factory=list)
    compute_only_assembly_lines: list[str] = field(default_factory=list)
    words: list[int] = field(default_factory=list)
    compute_only_words: list[int] = field(default_factory=list)
    mapping: list[SourceInstructionMapEntry] = field(default_factory=list)
    peak_gpr_used: int = 0
    peak_hreg_used: int = 0
    guards_emitted: int = 0
    guards_elided: int = 0
    runtime_hstar_checks_emitted: int = 0
    syscalls_emitted: int = 0
    native_letter_opcodes_emitted: int = 0

    @property
    def assembly_text(self) -> str:
        return "\n".join(self.assembly_lines) + "\n"

    @property
    def compute_only_assembly_text(self) -> str:
        return "\n".join(self.compute_only_assembly_lines) + "\n"


class CellHISABackend:
    """Compiles a validated `CellIRGraph` into HISA assembly and machine words."""

    def __init__(
        self,
        *,
        use_native_letter_opcodes: bool = True,
        reuse_registers: bool = True,
        use_hw_sticky_guard: bool = False,
        use_native_hdot: bool = False,
    ) -> None:
        self._use_letter_ops = use_native_letter_opcodes
        self._reuse = reuse_registers
        self._use_hw_sticky_guard = use_hw_sticky_guard
        self._use_native_hdot = use_native_hdot
        self._label_counter = 0

    def _new_label(self, prefix: str) -> str:
        self._label_counter += 1
        return f"L_{prefix}_{self._label_counter}"

    def compile(self, graph: CellIRGraph) -> CompiledHISAProgram:
        self._label_counter = 0
        out = CompiledHISAProgram()
        out.assembly_lines.append("; dihasilkan oleh Hijaiyyah Cells HISA Backend")
        out.assembly_lines.append("main:")
        out.compute_only_assembly_lines.append(
            "; dihasilkan oleh Hijaiyyah Cells HISA Backend (compute-only)"
        )
        out.compute_only_assembly_lines.append("main:")

        has_cfg_or_fn = bool(graph.subroutines) or any(
            n.op
            in (
                CellOp.COND_BRANCH,
                CellOp.WHILE_LOOP,
                CellOp.VAR_ASSIGN,
                CellOp.FN_CALL,
                CellOp.HOS_SYSCALL,
                CellOp.HFS_READ_HYBIT,
            )
            for n in graph.nodes.values()
        )

        absorbed: set[str] = set()
        chain_roots: set[str] = set()
        if self._use_letter_ops:
            for cid in reversed(graph.order):
                if cid in absorbed:
                    continue
                node = graph.nodes[cid]
                if (
                    node.op in (CellOp.HYBIT_ADD, CellOp.WORD_ACCUM)
                    and len(node.letter_sequence) >= 2
                ):
                    chain_roots.add(cid)
                    chain_members: set[str] = {cid}
                    self._collect_chain_members(graph, node, chain_members)
                    for member_id in chain_members:
                        if member_id == cid:
                            continue
                        users_outside = [
                            other_id
                            for other_id in graph.nodes
                            if member_id in graph.nodes[other_id].inputs
                            and other_id not in chain_members
                        ]
                        if not users_outside:
                            absorbed.add(member_id)

        remaining_uses: dict[str, int] = {cid: 0 for cid in graph.nodes}
        for cid, node in graph.nodes.items():
            if cid in absorbed or cid in chain_roots:
                continue
            for inp in node.inputs:
                remaining_uses[inp] = remaining_uses.get(inp, 0) + 1

        pinned_cids: set[str] = set()
        loop_mutated_hybit_roots: set[str] = set()
        if has_cfg_or_fn:
            for node in graph.nodes.values():
                if node.binding_name and node.binding_name in graph.bindings:
                    pinned_cids.add(graph.bindings[node.binding_name])

            def _scan_loop_body(nids: list[str]) -> None:
                for nid in nids:
                    nd = graph.nodes[nid]
                    if nd.op == CellOp.VAR_ASSIGN and nd.binding_name in graph.bindings:
                        rcid = graph.bindings[nd.binding_name]
                        if graph.nodes[rcid].output_type.value == "hybit":
                            loop_mutated_hybit_roots.add(rcid)
                    if nd.then_node_ids:
                        _scan_loop_body(nd.then_node_ids)
                    if nd.else_node_ids:
                        _scan_loop_body(nd.else_node_ids)
                    if nd.loop_body_node_ids:
                        _scan_loop_body(nd.loop_body_node_ids)

            for node in graph.nodes.values():
                if node.op == CellOp.WHILE_LOOP:
                    _scan_loop_body(node.loop_body_node_ids)

        free_r = list(range(GPR_FIRST, GPR_LAST + 1))
        free_h = list(range(HREG_FIRST, HREG_LAST + 1))
        reg_of: dict[str, tuple[str, int]] = {}
        sticky_reg_of: dict[str, int] = {}
        active_r: set[int] = set()
        active_h: set[int] = set()

        sub_labels: dict[str, str] = {
            sub_name: f"fn_sub_{idx + 1}"
            for idx, sub_name in enumerate(graph.subroutines)
        }

        def alloc_r(prefer: int | None = None, avoid: set[int] | None = None) -> int:
            if not free_r:
                raise CellBackendError(
                    f"Out of general scalar registers: R{GPR_FIRST}..R{GPR_LAST} "
                    "are all simultaneously live (R0 is reserved by ABI; R16..R17 "
                    "are unencodable in 4-bit H-ISA fields)"
                )
            if prefer is not None and prefer in free_r:
                free_r.remove(prefer)
                r = prefer
            elif avoid:
                candidates = [x for x in free_r if x not in avoid]
                r = candidates[0] if candidates else free_r[0]
                free_r.remove(r)
            else:
                r = free_r.pop(0)
            active_r.add(r)
            out.peak_gpr_used = max(out.peak_gpr_used, len(active_r))
            return r

        def alloc_h(prefer: int | None = None, avoid: set[int] | None = None) -> int:
            if not free_h:
                raise CellBackendError(
                    f"Out of hybit registers: H{HREG_FIRST}..H{HREG_LAST} "
                    "are all simultaneously live"
                )
            if prefer is not None and prefer in free_h:
                free_h.remove(prefer)
                h = prefer
            elif avoid:
                candidates = [x for x in free_h if x not in avoid]
                h = candidates[0] if candidates else free_h[0]
                free_h.remove(h)
            else:
                h = free_h.pop(0)
            active_h.add(h)
            out.peak_hreg_used = max(out.peak_hreg_used, len(active_h))
            return h

        def maybe_free(cid_key: str) -> None:
            if not self._reuse or cid_key in pinned_cids:
                return
            if remaining_uses.get(cid_key, 0) == 0 and cid_key in reg_of:
                kind, r_idx = reg_of[cid_key]
                if kind == "R" and r_idx in active_r:
                    active_r.remove(r_idx)
                    free_r.insert(0, r_idx)
                elif kind == "H" and r_idx in active_h:
                    active_h.remove(r_idx)
                    free_h.insert(0, r_idx)

        def consume(input_cid: str) -> None:
            remaining_uses[input_cid] = max(0, remaining_uses.get(input_cid, 0) - 1)
            maybe_free(input_cid)

        def emit_instr(line: str, *, is_io: bool = False, is_label: bool = False) -> None:
            formatted = line if is_label else f"        {line}"
            out.assembly_lines.append(formatted)
            if not is_io:
                out.compute_only_assembly_lines.append(formatted)

        def record_and_emit(
            target_list: list[str],
            line: str,
            *,
            is_io: bool = False,
            is_label: bool = False,
        ) -> None:
            target_list.append(line)
            emit_instr(line, is_io=is_io, is_label=is_label)

        def emit_node_list(node_ids: list[str]) -> None:
            for cid in node_ids:
                if cid in absorbed:
                    continue
                emit_single_node(cid)

        def emit_hybit_check_to_r0(
            step_lines: list[str], sh: int, *, include_hstar: bool = True
        ) -> None:
            record_and_emit(step_lines, f"HGRD    H{sh}")
            if not include_hstar:
                return
            out.runtime_hstar_checks_emitted += 1
            g_r = alloc_r()
            tmp_r = alloc_r()
            record_and_emit(
                step_lines, f"FRD     R{g_r}   ; save FLAGS immediately after HGRD before CMP"
            )
            record_and_emit(
                step_lines, f"ANDI    R{g_r}, R{g_r}, #1   ; R{g_r} = G in {{0,1}}"
            )
            record_and_emit(
                step_lines, f"CGET    R0, H{sh}, #17   ; H* runtime check"
            )
            record_and_emit(
                step_lines, f"CGET    R{tmp_r}, H{sh}, #7   ; Ka reference"
            )
            record_and_emit(
                step_lines, f"CMP     R0, R{tmp_r}   ; Z=1 iff H* == Ka"
            )
            record_and_emit(
                step_lines, f"FRD     R{tmp_r}   ; read FLAGS after CMP"
            )
            record_and_emit(
                step_lines, f"SHRI    R{tmp_r}, R{tmp_r}, #1   ; bit0 = Z = (H* == Ka)"
            )
            record_and_emit(
                step_lines, f"AND     R{g_r}, R{g_r}, R{tmp_r}   ; R{g_r} = G & (H* == Ka)"
            )
            record_and_emit(
                step_lines, f"CGET    R{tmp_r}, H{sh}, #0   ; Theta_hat"
            )
            record_and_emit(
                step_lines,
                f"SHRI    R{tmp_r}, R{tmp_r}, #1   ; floor(Theta_hat / 2)",
            )
            record_and_emit(
                step_lines,
                f"SUB     R0, R{tmp_r}, R0   ; floor(Theta_hat/2) - H*",
            )
            record_and_emit(
                step_lines, "SHRI    R0, R0, #31   ; 1 if H* > floor(Theta/2)"
            )
            record_and_emit(
                step_lines, "XORI    R0, R0, #1   ; 1 iff 2*H* <= Theta_hat"
            )
            record_and_emit(
                step_lines,
                f"AND     R0, R0, R{g_r}   ; combine (2*H*<=Theta) & G & (H*==Ka)",
            )
            record_and_emit(
                step_lines, "ANDI    R0, R0, #1   ; final guard_pass bit"
            )
            active_r.remove(tmp_r)
            free_r.insert(0, tmp_r)
            active_r.remove(g_r)
            free_r.insert(0, g_r)

        def emit_single_node(cid: str) -> None:
            node = graph.nodes[cid]
            step_lines: list[str] = []
            alloc_label: str | None = None
            op = node.op

            if cid in chain_roots:
                if 0 in free_h:
                    dst_h = alloc_h(prefer=0)
                    record_and_emit(step_lines, "CZERO   H0")
                    for ch in node.letter_sequence:
                        record_and_emit(step_lines, ch)
                        out.native_letter_opcodes_emitted += 1
                else:
                    dst_h = alloc_h()
                    if free_h:
                        scratch_h = free_h[0]
                        record_and_emit(step_lines, f"CMOV    H{scratch_h}, H0")
                        record_and_emit(step_lines, "CZERO   H0")
                        for ch in node.letter_sequence:
                            record_and_emit(step_lines, ch)
                            out.native_letter_opcodes_emitted += 1
                        record_and_emit(step_lines, f"CMOV    H{dst_h}, H0")
                        record_and_emit(step_lines, f"CMOV    H0, H{scratch_h}")
                    else:
                        first_rec = MASTER_TABLE_ENGINE.get_by_char(node.letter_sequence[0])
                        assert first_rec is not None
                        record_and_emit(step_lines, f"HLOAD   H{dst_h}, #{first_rec.index}")
                        for ch in node.letter_sequence[1:]:
                            rec = MASTER_TABLE_ENGINE.get_by_char(ch)
                            assert rec is not None
                            record_and_emit(step_lines, f"HLOAD   H0, #{rec.index}")
                            record_and_emit(step_lines, f"HCADD   H{dst_h}, H{dst_h}, H0")

                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                maybe_free(cid)

            elif op == CellOp.WORD_ACCUM:
                first_rec = MASTER_TABLE_ENGINE.get_by_char(node.letter_sequence[0])
                assert first_rec is not None
                dst_h = alloc_h()
                record_and_emit(step_lines, f"HLOAD   H{dst_h}, #{first_rec.index}")
                for ch in node.letter_sequence[1:]:
                    rec = MASTER_TABLE_ENGINE.get_by_char(ch)
                    assert rec is not None
                    tmp_h = alloc_h()
                    record_and_emit(step_lines, f"HLOAD   H{tmp_h}, #{rec.index}")
                    record_and_emit(step_lines, f"HCADD   H{dst_h}, H{dst_h}, H{tmp_h}")
                    active_h.remove(tmp_h)
                    free_h.insert(0, tmp_h)
                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                maybe_free(cid)

            elif op == CellOp.LETTER_CONST:
                assert node.imm_param is not None
                rec = MASTER_TABLE_ENGINE.get_by_index(node.imm_param)
                assert rec is not None
                dst_h = alloc_h(prefer=1 if 1 in free_h else None)
                record_and_emit(
                    step_lines,
                    f"HLOAD   H{dst_h}, #{rec.index}   ; {rec.char} {rec.name}",
                )
                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                maybe_free(cid)

            elif op == CellOp.ZERO_HYBIT:
                dst_h = alloc_h()
                record_and_emit(step_lines, f"CZERO   H{dst_h}")
                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                maybe_free(cid)

            elif op == CellOp.LOAD_ID:
                inp_cid = node.inputs[0]
                inp_node = graph.nodes[inp_cid]
                dst_h = alloc_h()
                if inp_node.static_scalar is not None:
                    consume(inp_cid)
                    record_and_emit(step_lines, f"HLOAD   H{dst_h}, #{inp_node.static_scalar}")
                else:
                    _, r_idx = reg_of[inp_cid]
                    consume(inp_cid)
                    record_and_emit(step_lines, f"HLOAD   H{dst_h}, R{r_idx}")
                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                maybe_free(cid)

            elif op == CellOp.SCALAR_CONST:
                assert node.imm_param is not None
                if not -2048 <= node.imm_param < 4096:
                    raise CellBackendError(
                        f"Scalar constant {node.imm_param} does not fit 12-bit HISA immediate"
                    )
                dst_r = alloc_r()
                if node.imm_param >= 0:
                    record_and_emit(step_lines, f"MOVI    R{dst_r}, #{node.imm_param}")
                else:
                    record_and_emit(step_lines, f"MOVI    R{dst_r}, #0")
                    record_and_emit(step_lines, f"ADDI    R{dst_r}, R{dst_r}, #{node.imm_param}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.HYBIT_ADD:
                l_cid, r_cid = node.inputs[0], node.inputs[1]
                _, lh = reg_of[l_cid]
                _, rh = reg_of[r_cid]
                consume(l_cid)
                consume(r_cid)
                inplace_target_h: int | None = None
                if self._use_hw_sticky_guard and remaining_uses.get(cid, 0) == 1:
                    for other_nd in graph.nodes.values():
                        if (
                            other_nd.op == CellOp.VAR_ASSIGN
                            and len(other_nd.inputs) == 1
                            and other_nd.inputs[0] == cid
                            and other_nd.binding_name in graph.bindings
                        ):
                            root_c = graph.bindings[other_nd.binding_name]
                            if root_c in reg_of and reg_of[root_c][0] == "H":
                                inplace_target_h = reg_of[root_c][1]
                            break
                dst_h = inplace_target_h if inplace_target_h is not None else alloc_h()
                record_and_emit(step_lines, f"HCADD   H{dst_h}, H{lh}, H{rh}")
                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                if inplace_target_h is None:
                    maybe_free(cid)

            elif op == CellOp.HYBIT_EQ:
                l_cid, r_cid = node.inputs[0], node.inputs[1]
                _, lh = reg_of[l_cid]
                _, rh = reg_of[r_cid]
                consume(l_cid)
                consume(r_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"CEQ     H{lh}, H{rh}")
                record_and_emit(step_lines, f"FRD     R{dst_r}")
                record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #1")
                record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op in (CellOp.SCALAR_ADD, CellOp.SCALAR_SUB, CellOp.SCALAR_MUL):
                l_cid, r_cid = node.inputs[0], node.inputs[1]
                _, lr = reg_of[l_cid]
                _, rr = reg_of[r_cid]
                consume(l_cid)
                consume(r_cid)
                dst_r = alloc_r()
                mnem = {
                    CellOp.SCALAR_ADD: "ADD",
                    CellOp.SCALAR_SUB: "SUB",
                    CellOp.SCALAR_MUL: "MUL",
                }[op]
                record_and_emit(step_lines, f"{mnem:<7} R{dst_r}, R{lr}, R{rr}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op in (
                CellOp.CMP_EQ,
                CellOp.CMP_NE,
                CellOp.CMP_LT,
                CellOp.CMP_GT,
                CellOp.CMP_LE,
                CellOp.CMP_GE,
            ):
                l_cid, r_cid = node.inputs[0], node.inputs[1]
                _, lr = reg_of[l_cid]
                _, rr = reg_of[r_cid]
                consume(l_cid)
                consume(r_cid)
                dst_r = alloc_r()
                if op == CellOp.CMP_EQ:
                    record_and_emit(step_lines, f"CMP     R{lr}, R{rr}")
                    record_and_emit(step_lines, f"FRD     R{dst_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #1")
                    record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                elif op == CellOp.CMP_NE:
                    record_and_emit(step_lines, f"CMP     R{lr}, R{rr}")
                    record_and_emit(step_lines, f"FRD     R{dst_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #1")
                    record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                    record_and_emit(step_lines, f"XORI    R{dst_r}, R{dst_r}, #1")
                elif op == CellOp.CMP_LT:
                    record_and_emit(step_lines, f"CMP     R{lr}, R{rr}")
                    record_and_emit(step_lines, f"FRD     R{dst_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #3")
                    record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                elif op == CellOp.CMP_GT:
                    record_and_emit(step_lines, f"CMP     R{rr}, R{lr}")
                    record_and_emit(step_lines, f"FRD     R{dst_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #3")
                    record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                elif op == CellOp.CMP_LE:
                    record_and_emit(step_lines, f"CMP     R{rr}, R{lr}")
                    record_and_emit(step_lines, f"FRD     R{dst_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #3")
                    record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                    record_and_emit(step_lines, f"XORI    R{dst_r}, R{dst_r}, #1")
                elif op == CellOp.CMP_GE:
                    record_and_emit(step_lines, f"CMP     R{lr}, R{rr}")
                    record_and_emit(step_lines, f"FRD     R{dst_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #3")
                    record_and_emit(step_lines, f"ANDI    R{dst_r}, R{dst_r}, #1")
                    record_and_emit(step_lines, f"XORI    R{dst_r}, R{dst_r}, #1")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op in (CellOp.PROJ_THETA, CellOp.PROJ_HSTAR, CellOp.PROJ_COMPONENT):
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                slot = (
                    0
                    if op == CellOp.PROJ_THETA
                    else (17 if op == CellOp.PROJ_HSTAR else int(node.imm_param or 0))
                )
                record_and_emit(step_lines, f"CGET    R{dst_r}, H{sh}, #{slot}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.TURNING_U:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"CU      R{dst_r}, H{sh}   ; B = U(h)")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.TURNING_RHO:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"CRHO    R{dst_r}, H{sh}   ; R = rho(h)")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.MOD4_GATE:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"CMOD4   R{dst_r}, H{sh}   ; Theta_hat mod 4")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.NORM2_V14:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"HNRM2   R{dst_r}, H{sh}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.DIST2_V14:
                a_cid, b_cid = node.inputs[0], node.inputs[1]
                _, ah = reg_of[a_cid]
                _, bh = reg_of[b_cid]
                consume(a_cid)
                consume(b_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"HDIST   R{dst_r}, H{ah}, H{bh}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.INNER_V14:
                a_cid, b_cid = node.inputs[0], node.inputs[1]
                _, ah = reg_of[a_cid]
                _, bh = reg_of[b_cid]
                if self._use_native_hdot:
                    dst_r = alloc_r()
                    record_and_emit(step_lines, f"HDOT    R{dst_r}, H{ah}, H{bh}")
                    consume(a_cid)
                    consume(b_cid)
                    reg_of[cid] = ("R", dst_r)
                    alloc_label = f"R{dst_r}"
                    maybe_free(cid)
                else:
                    tmp_h = alloc_h()
                    dst_r = alloc_r()
                    tmp_r = alloc_r()
                    record_and_emit(step_lines, f"HCADD   H{tmp_h}, H{ah}, H{bh}")
                    record_and_emit(step_lines, f"HNRM2   R{dst_r}, H{tmp_h}")
                    record_and_emit(step_lines, f"HNRM2   R{tmp_r}, H{ah}")
                    record_and_emit(step_lines, f"SUB     R{dst_r}, R{dst_r}, R{tmp_r}")
                    record_and_emit(step_lines, f"HNRM2   R{tmp_r}, H{bh}")
                    record_and_emit(step_lines, f"SUB     R{dst_r}, R{dst_r}, R{tmp_r}")
                    record_and_emit(step_lines, f"SHRI    R{dst_r}, R{dst_r}, #1")
                    active_h.remove(tmp_h)
                    free_h.insert(0, tmp_h)
                    active_r.remove(tmp_r)
                    free_r.insert(0, tmp_r)
                    consume(a_cid)
                    consume(b_cid)
                    reg_of[cid] = ("R", dst_r)
                    alloc_label = f"R{dst_r}"
                    maybe_free(cid)

            elif op == CellOp.HISAB_PACK:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                assert node.imm_param is not None
                record_and_emit(step_lines, f"HPACK   R{dst_r}, H{sh}, {node.imm_param}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.HISAB_CRC:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                dst_r = alloc_r()
                record_and_emit(step_lines, f"HCRC    R{dst_r}, H{sh}")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.GUARD_CHECK:
                src_cid = node.inputs[0]
                _, sh = reg_of[src_cid]
                consume(src_cid)
                if node.guard_discharged:
                    out.guards_elided += 1
                    comment = f"; HGRD H{sh} dihilangkan — {node.provenance_note}"
                    record_and_emit(step_lines, comment)
                elif self._use_hw_sticky_guard:
                    out.guards_emitted += 1
                    record_and_emit(
                        step_lines,
                        f"HGRD    H{sh}   ; HW A1 coupled H* + sticky prefix overflow guard",
                    )
                else:
                    out.guards_emitted += 1
                    emit_hybit_check_to_r0(
                        step_lines, sh, include_hstar=not node.hstar_coupled_bound_proven
                    )
                    if not node.hstar_coupled_bound_proven:
                        if src_cid in sticky_reg_of:
                            record_and_emit(
                                step_lines,
                                f"AND     R0, R0, R{sticky_reg_of[src_cid]}"
                                "   ; enforce sticky loop-prefix safety",
                            )
                        record_and_emit(
                            step_lines,
                            "FWR     R0   ; enforce G1-G4,T1-T2 & H*==Ka & 2*H*<=Theta",
                        )

            elif op == CellOp.EMIT_OUTPUT:
                src_cid = node.inputs[0]
                _, sr = reg_of[src_cid]
                consume(src_cid)
                record_and_emit(step_lines, f"PRINT   R{sr}", is_io=True)

            elif op == CellOp.HOS_SYSCALL:
                sys_cid, arg_cid = node.inputs[0], node.inputs[1]
                _, sys_r = reg_of[sys_cid]
                _, arg_r = reg_of[arg_cid]
                hyb_h: int | None = None
                if len(node.inputs) == 3:
                    _, hyb_h = reg_of[node.inputs[2]]

                # Preserve any live values in R1, R2, or H0 before setting syscall ABI regs
                save_r1: int | None = None
                save_r2: int | None = None
                save_h0: int | None = None
                if 1 in active_r and sys_r != 1 and arg_r != 1:
                    save_r1 = alloc_r(avoid={1, 2})
                    record_and_emit(step_lines, f"MOV     R{save_r1}, R1")
                if 2 in active_r and sys_r != 2 and arg_r != 2:
                    save_r2 = alloc_r(avoid={1, 2})
                    record_and_emit(step_lines, f"MOV     R{save_r2}, R2")
                if hyb_h is not None and hyb_h != 0:
                    if 0 in active_h:
                        save_h0 = alloc_h(avoid={0})
                        record_and_emit(step_lines, f"CMOV    H{save_h0}, H0")
                    record_and_emit(step_lines, f"CMOV    H0, H{hyb_h}")

                # Move sys_r -> R1 and arg_r -> R2 safely (handling R1/R2 swap if needed)
                if sys_r == 2 and arg_r == 1:
                    record_and_emit(step_lines, "MOV     R0, R1")
                    record_and_emit(step_lines, "MOV     R1, R2")
                    record_and_emit(step_lines, "MOV     R2, R0")
                elif arg_r == 1:
                    record_and_emit(step_lines, "MOV     R2, R1")
                    if sys_r != 1:
                        record_and_emit(step_lines, f"MOV     R1, R{sys_r}")
                else:
                    if sys_r != 1:
                        record_and_emit(step_lines, f"MOV     R1, R{sys_r}")
                    if arg_r != 2:
                        record_and_emit(step_lines, f"MOV     R2, R{arg_r}")

                is_write_sc = graph.nodes[sys_cid].static_scalar == 1
                record_and_emit(step_lines, "SYSCALL", is_io=is_write_sc)
                out.syscalls_emitted += 1

                for inp_c in node.inputs:
                    consume(inp_c)

                dst_r = alloc_r(avoid={1, 2} if (save_r1 or save_r2) else None)
                if dst_r != 1:
                    record_and_emit(step_lines, f"MOV     R{dst_r}, R1")
                if save_r1 is not None:
                    record_and_emit(step_lines, f"MOV     R1, R{save_r1}")
                    active_r.remove(save_r1)
                    free_r.insert(0, save_r1)
                if save_r2 is not None:
                    record_and_emit(step_lines, f"MOV     R2, R{save_r2}")
                    active_r.remove(save_r2)
                    free_r.insert(0, save_r2)
                if save_h0 is not None:
                    record_and_emit(step_lines, f"CMOV    H0, H{save_h0}")
                    active_h.remove(save_h0)
                    free_h.insert(0, save_h0)

                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            elif op == CellOp.HFS_READ_HYBIT:
                fid_cid = node.inputs[0]
                _, fid_r = reg_of[fid_cid]
                save_r1 = None
                save_r2 = None
                save_h0 = None
                if 1 in active_r and fid_r != 1:
                    save_r1 = alloc_r(avoid={1, 2})
                    record_and_emit(step_lines, f"MOV     R{save_r1}, R1")
                if 2 in active_r and fid_r != 2:
                    save_r2 = alloc_r(avoid={1, 2})
                    record_and_emit(step_lines, f"MOV     R{save_r2}, R2")
                if 0 in active_h:
                    save_h0 = alloc_h(avoid={0})
                    record_and_emit(step_lines, f"CMOV    H{save_h0}, H0")

                if fid_r != 2:
                    record_and_emit(step_lines, f"MOV     R2, R{fid_r}")
                record_and_emit(step_lines, "MOVI    R1, #7   ; HFS_READ")
                record_and_emit(step_lines, "SYSCALL")
                out.syscalls_emitted += 1
                consume(fid_cid)

                dst_h = alloc_h(
                    prefer=0 if save_h0 is None else None,
                    avoid={0} if save_h0 else None,
                )
                if dst_h != 0:
                    record_and_emit(step_lines, f"CMOV    H{dst_h}, H0")
                if save_h0 is not None:
                    record_and_emit(step_lines, f"CMOV    H0, H{save_h0}")
                    active_h.remove(save_h0)
                    free_h.insert(0, save_h0)
                if save_r1 is not None:
                    record_and_emit(step_lines, f"MOV     R1, R{save_r1}")
                    active_r.remove(save_r1)
                    free_r.insert(0, save_r1)
                if save_r2 is not None:
                    record_and_emit(step_lines, f"MOV     R2, R{save_r2}")
                    active_r.remove(save_r2)
                    free_r.insert(0, save_r2)

                reg_of[cid] = ("H", dst_h)
                alloc_label = f"H{dst_h}"
                maybe_free(cid)

            elif op == CellOp.VAR_ASSIGN:
                val_cid = node.inputs[0]
                v_kind, vr = reg_of[val_cid]
                assert node.binding_name is not None
                root_cid = graph.bindings[node.binding_name]
                _, target_r = reg_of[root_cid]
                if v_kind == "R":
                    if vr != target_r:
                        record_and_emit(step_lines, f"MOV     R{target_r}, R{vr}")
                else:
                    if vr != target_r:
                        record_and_emit(step_lines, f"CMOV    H{target_r}, H{vr}")
                    if root_cid in sticky_reg_of:
                        emit_hybit_check_to_r0(step_lines, target_r, include_hstar=True)
                        record_and_emit(
                            step_lines,
                            f"AND     R{sticky_reg_of[root_cid]}, R{sticky_reg_of[root_cid]}, R0"
                            "   ; sticky per-iteration prefix guard",
                        )
                consume(val_cid)
                reg_of[cid] = (v_kind, target_r)
                alloc_label = f"{v_kind}{target_r}"

            elif op == CellOp.COND_BRANCH:
                cond_cid = node.inputs[0]
                _, cr = reg_of[cond_cid]
                consume(cond_cid)
                else_lbl = self._new_label("else")
                end_lbl = self._new_label("endif")
                record_and_emit(step_lines, f"CMPI    R{cr}, #0")
                if node.else_node_ids:
                    record_and_emit(step_lines, f"JEQ     {else_lbl}")
                    emit_node_list(node.then_node_ids)
                    record_and_emit(step_lines, f"JMP     {end_lbl}")
                    record_and_emit(step_lines, f"{else_lbl}:", is_label=True)
                    emit_node_list(node.else_node_ids)
                    record_and_emit(step_lines, f"{end_lbl}:", is_label=True)
                else:
                    record_and_emit(step_lines, f"JEQ     {end_lbl}")
                    emit_node_list(node.then_node_ids)
                    record_and_emit(step_lines, f"{end_lbl}:", is_label=True)

            elif op == CellOp.WHILE_LOOP:
                start_lbl = self._new_label("loop")
                end_lbl = self._new_label("endloop")
                record_and_emit(step_lines, f"{start_lbl}:", is_label=True)
                emit_node_list(node.loop_cond_node_ids)
                cond_cid = node.inputs[0]
                _, cr = reg_of[cond_cid]
                consume(cond_cid)
                record_and_emit(step_lines, f"CMPI    R{cr}, #0")
                record_and_emit(step_lines, f"JEQ     {end_lbl}")
                emit_node_list(node.loop_body_node_ids)
                record_and_emit(step_lines, f"JMP     {start_lbl}")
                record_and_emit(step_lines, f"{end_lbl}:", is_label=True)

            elif op == CellOp.FN_CALL:
                assert node.callee_name is not None
                fn_lbl = sub_labels[node.callee_name]
                arg_abi_regs = [13, 14, 12, 11]
                for idx, arg_cid in enumerate(node.inputs):
                    _, ar = reg_of[arg_cid]
                    abi_r = arg_abi_regs[idx]
                    if ar != abi_r:
                        record_and_emit(step_lines, f"MOV     R{abi_r}, R{ar}")
                    consume(arg_cid)
                record_and_emit(step_lines, f"CALL    {fn_lbl}")
                dst_r = alloc_r()
                if dst_r != 15:
                    record_and_emit(step_lines, f"MOV     R{dst_r}, R15")
                reg_of[cid] = ("R", dst_r)
                alloc_label = f"R{dst_r}"
                maybe_free(cid)

            else:
                raise CellBackendError(
                    f"Cell operation {op.value} ({node.source_glyphs}) is not "
                    f"supported by HCPU hardware backend (returns {node.output_type.value})"
                )

            if (
                not self._use_hw_sticky_guard
                and cid in loop_mutated_hybit_roots
                and cid not in sticky_reg_of
                and cid in reg_of
                and reg_of[cid][0] == "H"
            ):
                sticky_r = alloc_r()
                sticky_reg_of[cid] = sticky_r
                emit_hybit_check_to_r0(step_lines, reg_of[cid][1], include_hstar=True)
                record_and_emit(
                    step_lines,
                    f"MOV     R{sticky_r}, R0   ; init sticky loop-prefix guard",
                )

            out.mapping.append(
                SourceInstructionMapEntry(
                    cell_id=cid,
                    op=op.value,
                    source_glyphs=node.source_glyphs,
                    emitted_instructions=tuple(step_lines),
                    allocated_register=alloc_label,
                )
            )

        emit_node_list(graph.order)
        emit_instr("HALT", is_io=False)

        for sub_name, sub_def in graph.subroutines.items():
            self._emit_subroutine(
                graph,
                sub_def,
                sub_labels[sub_name],
                out,
                emit_instr,
            )

        out.words = assemble(out.assembly_text)
        out.compute_only_words = assemble(out.compute_only_assembly_text)
        return out

    def _emit_subroutine(
        self,
        graph: CellIRGraph,
        sub_def: CellSubroutineDef,
        fn_label: str,
        out: CompiledHISAProgram,
        emit_instr: Any,
    ) -> None:
        emit_instr(f"{fn_label}:", is_io=False, is_label=True)
        arg_abi_regs = [13, 14, 12, 11]
        local_reg: dict[str, int] = {}
        next_temp = 10
        for idx, pid in enumerate(sub_def.param_node_ids):
            local_reg[pid] = arg_abi_regs[idx]
            out.peak_gpr_used = max(out.peak_gpr_used, 2 + idx)

        for cid in sub_def.body_node_ids:
            node = graph.nodes[cid]
            if node.op == CellOp.FN_PARAM:
                continue
            if node.op == CellOp.SCALAR_CONST:
                assert node.imm_param is not None
                r = next_temp
                next_temp = max(1, next_temp - 1)
                emit_instr(f"MOVI    R{r}, #{node.imm_param}", is_io=False)
                local_reg[cid] = r
            elif node.op in (CellOp.SCALAR_ADD, CellOp.SCALAR_SUB, CellOp.SCALAR_MUL):
                lr = local_reg[node.inputs[0]]
                rr = local_reg[node.inputs[1]]
                r = next_temp
                next_temp = max(1, next_temp - 1)
                mnem = {
                    CellOp.SCALAR_ADD: "ADD",
                    CellOp.SCALAR_SUB: "SUB",
                    CellOp.SCALAR_MUL: "MUL",
                }[node.op]
                emit_instr(f"{mnem:<7} R{r}, R{lr}, R{rr}", is_io=False)
                local_reg[cid] = r
            else:
                raise CellBackendError(
                    f"Unsupported node {node.op.value} inside subroutine {sub_def.name}"
                )

        ret_r = local_reg.get(sub_def.return_node_id, 15)
        if ret_r != 15:
            emit_instr(f"MOV     R15, R{ret_r}", is_io=False)
        emit_instr("RET", is_io=False)

    def _collect_chain_members(
        self,
        graph: CellIRGraph,
        node: CellIRNode,
        members: set[str],
    ) -> None:
        """Collect all ancestor HYBIT_ADD / LETTER_CONST nodes belonging to a letter chain."""
        for inp_id in node.inputs:
            child = graph.nodes[inp_id]
            if child.op in (CellOp.HYBIT_ADD, CellOp.LETTER_CONST) and child.letter_sequence:
                members.add(inp_id)
                self._collect_chain_members(graph, child, members)


__all__ = [
    "GPR_FIRST",
    "GPR_LAST",
    "GPR_SCRATCH",
    "HREG_FIRST",
    "HREG_LAST",
    "CellBackendError",
    "CellHISABackend",
    "CompiledHISAProgram",
    "SourceInstructionMapEntry",
]
