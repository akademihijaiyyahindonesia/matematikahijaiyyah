# -*- coding: utf-8 -*-
"""Stage 5 of HCC: an HC program becomes H-ISA assembly.

This is the step that lets the language run on its own processor. Until now
``hc run`` walked the AST in Python and the HCPU executed hand-written
``.hasm``; the two never met. With ``.hc → .hasm`` in place the same source
reaches HVM and silicon, and ``rtl/tb/tb_parity.v`` can hold them to the same
answer.

The generator refuses more than it accepts, on purpose. Emitting an
approximation of an unsupported construct would put wrong instructions on a
processor that has no second check behind them, so anything outside the
compilable subset raises :class:`CodegenError` naming what is missing.

**What compiles**

===========================  =========================================
HC                           H-ISA
===========================  =========================================
``let h = 'ب'``              ``HLOAD Hn, #2``
``'ب' + 'س' + 'م'``          ``CZERO H0`` + ``ب``, ``س``, ``م`` (0xE0–0xFB)
``a + b`` (hybits)           ``HCADD Hd, Ha, Hb``
``h.guard()``                ``HGRD Hs`` — elided when Ψ proved it
``h.theta()``, ``h.Qc()``…   ``CGET Rd, Hs, #i``
``h.U()``                    ``CU Rd, Hs`` (0x4D)
``h.rho()``                  ``CRHO Rd, Hs`` (0x4C)
``h.pack(i)``, ``h.crc()``   ``HPACK Rd, Hs, i`` / ``HCRC Rd, Hs``
``h.norm2()``                ``HNRM2 Rd, Hs``
``a.dist2(b)``               ``HDIST Rd, Ha, Hb``
``load_id(n)``               ``HLOAD Hn, #n``
integers and ``+ - *``       ``MOVI`` / ``ADD`` / ``SUB`` / ``MUL``
``println(x)`` for an int    ``PRINT Rs``
===========================  =========================================

**Register ABI and Bounds (§IIIF.3.3.1 & §IIIJ.3.3.1)**

The H-ISA instruction word provides 4-bit register fields (`DST` `[23:20]`,
`S1` `[19:16]`, `S2` `[15:12]`), which can address `R0`–`R15` and `H0`–`H15`
(`MAX_GPR = 15` in `hijaiyyah.hisa.assembler`). `R16` and `R17` cannot be
encoded in any 32-bit H-ISA instruction word and are never allocated.

On the HCPU (`rtl/hcpu_regfile.v`, `rtl/hcpu_decode.v`), `R0` is an ordinary
writable 32-bit register (not hardwired to zero). By ABI convention, `R0` is
reserved as the scratch/MMIO base register, while `R1`–`R15` form the
allocatable scalar register pool with temporary register liveness reuse.
`H0`–`H15` form the 144-bit hybit register pool, with `H0` also serving as the
implicit accumulator for native letter instructions (`0xE0`–`0xFB`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from hijaiyyah.core.exceptions import HijaiyyahError
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.language.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ExpressedStmt,
    LetStmt,
    Literal,
    MethodCall,
    Program,
    VarRef,
)
from hijaiyyah.language.evaluator import _SLOT_MAP

from .psi import PsiReport

#: Register files: R0 is reserved by ABI as a scratch/MMIO base slot;
#: R1–R15 are the 15 encodable general-purpose registers (4-bit field limit).
GPR_SCRATCH = 0
GPR_FIRST, GPR_LAST = 1, 15
HREG_FIRST, HREG_LAST = 0, 15

#: Component accessors, compiled with CGET. The map is the evaluator's, so
#: the two ends cannot disagree about which name is which index.
_COMPONENT_METHODS = dict(_SLOT_MAP)

#: Still without an encoding: these return a vector, a matrix or a float, and
#: a GPR holds a 32-bit integer.
_UNENCODABLE_METHODS = frozenset(
    {"total", "array", "norm", "cosine", "dot", "guard_detail", "exomatrix",
     "phi", "hash", "alpha", "r_rho", "r_loop", "proj_theta"}
)

HYBIT, SCALAR = "hybit", "scalar"


class CodegenError(HijaiyyahError):
    """Raised for any construct the generator will not encode."""


@dataclass
class Emitted:
    """The result of one code-generation pass."""

    lines: List[str] = field(default_factory=list)
    guards_emitted: int = 0
    guards_elided: int = 0
    guards_inserted: int = 0

    @property
    def text(self) -> str:
        return "\n".join(self.lines) + "\n"

    def summary(self) -> str:
        total = self.guards_emitted + self.guards_elided
        parts = [f"{len(self.lines)} baris"]
        if total:
            parts.append(f"{self.guards_elided}/{total} HGRD dihilangkan oleh Ψ")
        if self.guards_inserted:
            parts.append(f"{self.guards_inserted} HGRD disisipkan")
        return "; ".join(parts)


class CodeGenerator:
    """Walks a typed HC AST and emits H-ISA assembly.

    Args:
        psi: The Ψ-injection report for the same AST. When given, a guard the
            analysis proved is not emitted at all — the O(1) runtime check
            becomes no check, because closure made it unnecessary.
    """

    def __init__(
        self,
        psi: Optional[PsiReport] = None,
        *,
        insert_guards: bool = False,
        use_native_letter_opcodes: bool = True,
    ) -> None:
        self._psi = psi
        self._insert = insert_guards
        self._use_letter_ops = use_native_letter_opcodes
        self._out = Emitted()
        self._bindings: Dict[str, Tuple[str, int]] = {}
        self._free_h: List[int] = list(range(HREG_FIRST, HREG_LAST + 1))
        self._free_r: List[int] = list(range(GPR_FIRST, GPR_LAST + 1))
        self._bound_h: Set[int] = set()
        self._bound_r: Set[int] = set()

    # ── Allocation & Liveness Reuse ──────────────────────────────

    def _alloc_hybit(self, *, prefer: Optional[int] = None) -> int:
        if not self._free_h:
            raise CodegenError(
                f"out of hybit registers: H{HREG_FIRST}–H{HREG_LAST} are all live."
            )
        if prefer is not None and prefer in self._free_h:
            self._free_h.remove(prefer)
            return prefer
        return self._free_h.pop(0)

    def _alloc_scalar(self) -> int:
        if not self._free_r:
            raise CodegenError(
                f"out of general registers: R{GPR_FIRST}–R{GPR_LAST} are all live."
            )
        return self._free_r.pop(0)

    def _release_if_temp(self, kind: str, reg: int) -> None:
        """Return a temporary register to the free pool if no `let` binding owns it."""
        if kind == SCALAR and reg not in self._bound_r and reg not in self._free_r:
            self._free_r.insert(0, reg)
        elif kind == HYBIT and reg not in self._bound_h and reg not in self._free_h:
            self._free_h.insert(0, reg)

    def _recompute_bound_sets(self) -> None:
        self._bound_r = {reg for k, reg in self._bindings.values() if k == SCALAR}
        self._bound_h = {reg for k, reg in self._bindings.values() if k == HYBIT}

    def _emit(self, text: str) -> None:
        self._out.lines.append(f"        {text}")

    # ── Entry point ──────────────────────────────────────────────

    def generate(self, node: Any) -> Emitted:
        """Compile a program and return its assembly."""
        if not isinstance(node, Program):
            raise CodegenError(f"expected a Program, got {type(node).__name__}")

        self._out = Emitted()
        self._bindings.clear()
        self._free_h = list(range(HREG_FIRST, HREG_LAST + 1))
        self._free_r = list(range(GPR_FIRST, GPR_LAST + 1))
        self._bound_h.clear()
        self._bound_r.clear()

        self._out.lines.append("; dihasilkan oleh HCC — jangan disunting tangan")
        self._out.lines.append("main:")
        for statement in node.body:
            self._statement(statement)
        self._emit("HALT")
        return self._out

    # ── Statements ───────────────────────────────────────────────

    def _statement(self, node: Any) -> None:
        if isinstance(node, LetStmt):
            old_binding = self._bindings.get(node.name)
            kind, register = self._expression(node.value)
            self._bindings[node.name] = (kind, register)
            self._recompute_bound_sets()
            if old_binding is not None:
                self._release_if_temp(old_binding[0], old_binding[1])
            if kind is HYBIT:
                self._maybe_insert_guard(node.value, register, node.name)
            return

        if isinstance(node, ExpressedStmt):
            self._expression_statement(node.expr)
            return

        raise CodegenError(
            f"{type(node).__name__} is not compilable yet — this generator "
            "handles `let` bindings and expression statements"
        )

    def _expression_statement(self, node: Any) -> None:
        """A bare expression: only a guard check and println do work here."""
        if isinstance(node, MethodCall) and node.method == "guard":
            self._guard(node)
            return

        if isinstance(node, CallExpr) and node.callee in ("println", "print"):
            if len(node.args) != 1:
                raise CodegenError(
                    f"{node.callee} compiles with exactly one argument; PRINT "
                    "takes a single register"
                )
            kind, register = self._expression(node.args[0])
            if kind is not SCALAR:
                raise CodegenError(
                    "PRINT takes a scalar register; a hybit has no decimal form"
                )
            self._emit(f"PRINT   R{register}")
            self._release_if_temp(kind, register)
            return

        # Anything else evaluated for its value alone has no effect.
        kind, register = self._expression(node)
        self._release_if_temp(kind, register)

    def _maybe_insert_guard(self, value: Any, register: int, name: str) -> None:
        """Emit HGRD for a hybit the analysis could not prove."""
        if not self._insert or self._psi is None:
            return

        facts = self._psi.facts.get(id(value))
        if facts is not None and facts.can_discharge_guard():
            return

        reason = "no proof available" if facts is None else facts.reason
        self._out.guards_inserted += 1
        self._out.lines.append(f"        ; guard disisipkan untuk '{name}' — {reason}")
        self._emit(f"HGRD    H{register}")

    def _guard(self, node: MethodCall) -> None:
        """Emit HGRD, unless Ψ already proved the value is in ℋ."""
        kind, register = self._expression(node.obj)
        if kind is not HYBIT:
            raise CodegenError("guard() applies to a hybit")

        if self._psi is not None:
            facts = self._psi.facts.get(id(node.obj))
            if facts is not None and facts.can_discharge_guard():
                self._out.guards_elided += 1
                self._out.lines.append(
                    f"        ; HGRD H{register} dihilangkan — {facts.reason}"
                )
                self._release_if_temp(kind, register)
                return

        self._out.guards_emitted += 1
        self._emit(f"HGRD    H{register}")
        self._release_if_temp(kind, register)

    # ── Expressions ──────────────────────────────────────────────

    @staticmethod
    def _extract_literal_letter_chain(node: Any) -> Optional[List[str]]:
        """Return the sequence of canonical Hijaiyyah letters if `node` is a pure
        `+` tree of `hybit_ref` literals (`'ب' + 'س' + 'م'`), else None."""
        if isinstance(node, Literal) and node.lit_type == "hybit_ref":
            entry = MASTER_TABLE.get_by_char(node.value)
            if entry is None:
                return None
            return [entry.char]
        if isinstance(node, BinaryExpr) and node.op == "+":
            left_chain = CodeGenerator._extract_literal_letter_chain(node.left)
            if left_chain is None:
                return None
            right_chain = CodeGenerator._extract_literal_letter_chain(node.right)
            if right_chain is None:
                return None
            return left_chain + right_chain
        return None

    def _expression(self, node: Any) -> Tuple[str, int]:
        if isinstance(node, Literal):
            return self._literal(node)
        if isinstance(node, VarRef):
            if node.name not in self._bindings:
                raise CodegenError(f"'{node.name}' is not bound")
            return self._bindings[node.name]
        if isinstance(node, BinaryExpr):
            return self._binary(node)
        if isinstance(node, MethodCall):
            return self._method(node)
        if isinstance(node, CallExpr):
            return self._call(node)
        raise CodegenError(f"{type(node).__name__} is not compilable yet")

    def _call(self, node: CallExpr) -> Tuple[str, int]:
        """`load_id(n)` is HLOAD, which is the only call with an encoding."""
        if node.callee != "load_id":
            raise CodegenError(
                f"'{node.callee}()' has no H-ISA encoding; load_id is the only "
                "call this generator compiles"
            )
        if len(node.args) != 1:
            raise CodegenError("load_id takes one argument")

        argument = node.args[0]
        if isinstance(argument, Literal) and isinstance(argument.value, int):
            register = self._alloc_hybit()
            self._emit(f"HLOAD   H{register}, #{argument.value}")
            return HYBIT, register

        kind, index = self._expression(argument)
        if kind is not SCALAR:
            raise CodegenError("load_id takes a scalar index")
        register = self._alloc_hybit()
        self._emit(f"HLOAD   H{register}, R{index}")
        self._release_if_temp(kind, index)
        return HYBIT, register

    def _literal(self, node: Literal) -> Tuple[str, int]:
        if node.lit_type == "hybit_ref":
            entry = MASTER_TABLE.get_by_char(node.value)
            if entry is None:
                raise CodegenError(f"'{node.value}' is not a canonical letter")
            register = self._alloc_hybit()
            self._emit(f"HLOAD   H{register}, #{entry.index}   ; {entry.char} {entry.name}")
            return HYBIT, register

        if isinstance(node.value, int) and not isinstance(node.value, bool):
            register = self._alloc_scalar()
            self._emit(f"MOVI    R{register}, #{node.value}")
            return SCALAR, register

        raise CodegenError(
            f"a {node.lit_type} literal has no H-ISA representation"
        )

    def _binary(self, node: BinaryExpr) -> Tuple[str, int]:
        # When compiling a literal letter chain ('ب' + 'س' + 'م') of >= 2 letters
        # with Ψ hardware-safety proof and H0 free, lower directly to native
        # letter opcodes (0xE0–0xFB) accumulating into H0.
        if self._use_letter_ops and node.op == "+" and self._psi is not None:
            chain = self._extract_literal_letter_chain(node)
            facts = self._psi.facts.get(id(node))
            if (
                chain is not None
                and len(chain) >= 2
                and facts is not None
                and facts.can_discharge_guard()
                and 0 in self._free_h
            ):
                reg_h0 = self._alloc_hybit(prefer=0)
                self._emit("CZERO   H0")
                for ch in chain:
                    self._emit(ch)
                return HYBIT, reg_h0

        left_kind, left = self._expression(node.left)
        right_kind, right = self._expression(node.right)

        if left_kind != right_kind:
            raise CodegenError(
                f"cannot combine a {left_kind} with a {right_kind}"
            )

        if left_kind is HYBIT:
            if node.op != "+":
                raise CodegenError(
                    f"'{node.op}' has no hybit encoding — ℋ is a monoid, and "
                    "HCADD is the only codex arithmetic in H-ISA"
                )
            self._release_if_temp(left_kind, left)
            self._release_if_temp(right_kind, right)
            register = self._alloc_hybit()
            self._emit(f"HCADD   H{register}, H{left}, H{right}")
            return HYBIT, register

        mnemonic = {"+": "ADD", "-": "SUB", "*": "MUL"}.get(node.op)
        if mnemonic is None:
            raise CodegenError(f"'{node.op}' has no scalar encoding in H-ISA")
        self._release_if_temp(left_kind, left)
        self._release_if_temp(right_kind, right)
        register = self._alloc_scalar()
        self._emit(f"{mnemonic:<7} R{register}, R{left}, R{right}")
        return SCALAR, register

    def _method(self, node: MethodCall) -> Tuple[str, int]:
        if node.method in _UNENCODABLE_METHODS:
            raise CodegenError(
                f".{node.method}() returns a vector, a matrix or a float; a GPR "
                "holds a 32-bit integer, so there is nowhere for the result to go"
            )

        kind, register = self._expression(node.obj)
        if kind is not HYBIT:
            raise CodegenError(f".{node.method}() applies to a hybit")

        if node.method in _COMPONENT_METHODS:
            index = _COMPONENT_METHODS[node.method]
            self._release_if_temp(kind, register)
            out = self._alloc_scalar()
            self._emit(f"CGET    R{out}, H{register}, #{index}   ; {node.method}")
            return SCALAR, out

        if node.method == "U":
            self._release_if_temp(kind, register)
            out = self._alloc_scalar()
            self._emit(f"CU      R{out}, H{register}   ; U")
            return SCALAR, out

        if node.method == "rho":
            self._release_if_temp(kind, register)
            out = self._alloc_scalar()
            self._emit(f"CRHO    R{out}, H{register}   ; rho")
            return SCALAR, out

        if node.method == "pack":
            if len(node.args) != 1 or not isinstance(node.args[0], Literal):
                raise CodegenError("pack() takes a literal word index 0–2")
            index = node.args[0].value
            if not isinstance(index, int) or not 0 <= index <= 2:
                raise CodegenError(f"pack({index}): HISAB has words 0–2")
            self._release_if_temp(kind, register)
            out = self._alloc_scalar()
            self._emit(f"HPACK   R{out}, H{register}, {index}")
            return SCALAR, out

        if node.method == "crc":
            self._release_if_temp(kind, register)
            out = self._alloc_scalar()
            self._emit(f"HCRC    R{out}, H{register}")
            return SCALAR, out

        if node.method == "norm2":
            self._release_if_temp(kind, register)
            out = self._alloc_scalar()
            self._emit(f"HNRM2   R{out}, H{register}")
            return SCALAR, out

        if node.method == "dist2":
            if len(node.args) != 1:
                raise CodegenError("dist2 takes one hybit argument")
            other_kind, other = self._expression(node.args[0])
            if other_kind is not HYBIT:
                raise CodegenError("dist2 takes a hybit argument")
            self._release_if_temp(kind, register)
            self._release_if_temp(other_kind, other)
            out = self._alloc_scalar()
            self._emit(f"HDIST   R{out}, H{register}, H{other}")
            return SCALAR, out

        raise CodegenError(f".{node.method}() has no H-ISA encoding")


def generate(
    ast: Any,
    psi: Optional[PsiReport] = None,
    *,
    insert_guards: bool = False,
    use_native_letter_opcodes: bool = True,
) -> Emitted:
    """Compile an HC AST into H-ISA assembly."""
    return CodeGenerator(
        psi,
        insert_guards=insert_guards,
        use_native_letter_opcodes=use_native_letter_opcodes,
    ).generate(ast)
