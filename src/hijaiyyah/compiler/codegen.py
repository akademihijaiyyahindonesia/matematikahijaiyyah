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
``a + b`` (hybits)           ``HCADD Hd, Ha, Hb``
``h.guard()``                ``HGRD Hs`` — elided when Ψ proved it
``h.theta()``, ``h.Qc()``…   ``CGET Rd, Hs, #i``
``h.U()``, ``h.rho()``       ``CGET`` + integer arithmetic
``h.norm2()``                ``HNRM2 Rd, Hs``
``a.dist2(b)``               ``HDIST Rd, Ha, Hb``
``load_id(n)``               ``HLOAD Hn, #n``
integers and ``+ - *``       ``MOVI`` / ``ADD`` / ``SUB`` / ``MUL``
``println(x)`` for an int    ``PRINT Rs``
===========================  =========================================

**What cannot compile, and why it is not a limitation of this file**

``h.theta()``, ``h.Na()``, ``h.U()``, ``h.rho()`` — every accessor that reads
one component out of a codex — have no encoding in the frozen H-ISA. The 28
opcodes of §IIIM.3.1 contain no AND, no shift, no DIV and no MOD, and no
opcode that projects a component. ``HPACK`` packs the 18 components into three
GPR words as nibbles, but nothing can mask a nibble back out.

``HPACK`` and ``HCRC`` have the opposite problem: they exist in the ISA and in
``hcpu_hisab.v``, but HC has no surface that produces them — there is no
``.pack()`` or ``.crc()`` method in the evaluator. Two of the twenty-eight
opcodes are unreachable from the language, and giving them one is a language
decision that belongs with the evaluator, not here.

That gap reaches the book: the example program in §IIIF.3.1.2 uses
``PROJ THETA word``, so it cannot be assembled against the instruction table
in §IIIM.3.1 either. Closing it needs a new opcode — a projection that reads
``H[S1][IMM]`` into ``GPR[DST]`` — which is an ISA decision, not a compiler
one. Until then this generator says so rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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

#: Register files, from §IIIJ.3.3. R0 is left free as a scratch slot.
GPR_FIRST, GPR_LAST = 1, 17
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

    @property
    def text(self) -> str:
        return "\n".join(self.lines) + "\n"

    def summary(self) -> str:
        total = self.guards_emitted + self.guards_elided
        if not total:
            return f"{len(self.lines)} baris, tanpa guard"
        return (
            f"{len(self.lines)} baris; {self.guards_elided}/{total} HGRD "
            "dihilangkan oleh Ψ"
        )


class CodeGenerator:
    """Walks a typed HC AST and emits H-ISA assembly.

    Args:
        psi: The Ψ-injection report for the same AST. When given, a guard the
            analysis proved is not emitted at all — the O(1) runtime check
            becomes no check, because closure made it unnecessary.
    """

    def __init__(self, psi: Optional[PsiReport] = None) -> None:
        self._psi = psi
        self._out = Emitted()
        self._bindings: Dict[str, Tuple[str, int]] = {}
        self._next_h = HREG_FIRST
        self._next_r = GPR_FIRST

    # ── Allocation ───────────────────────────────────────────────

    def _alloc_hybit(self) -> int:
        if self._next_h > HREG_LAST:
            raise CodegenError(
                f"out of hybit registers: H{HREG_FIRST}–H{HREG_LAST} are all live. "
                "This generator does not reuse registers yet."
            )
        self._next_h += 1
        return self._next_h - 1

    def _alloc_scalar(self) -> int:
        if self._next_r > GPR_LAST:
            raise CodegenError(
                f"out of general registers: R{GPR_FIRST}–R{GPR_LAST} are all live."
            )
        self._next_r += 1
        return self._next_r - 1

    def _emit(self, text: str) -> None:
        self._out.lines.append(f"        {text}")

    # ── Entry point ──────────────────────────────────────────────

    def generate(self, node: Any) -> Emitted:
        """Compile a program and return its assembly.

        Args:
            node: The AST root, a :class:`Program`.

        Returns:
            The emitted assembly and the guard statistics.

        Raises:
            CodegenError: On any construct outside the compilable subset.
        """
        if not isinstance(node, Program):
            raise CodegenError(f"expected a Program, got {type(node).__name__}")

        self._out = Emitted()
        self._bindings.clear()
        self._next_h, self._next_r = HREG_FIRST, GPR_FIRST

        self._out.lines.append("; dihasilkan oleh HCC — jangan disunting tangan")
        self._out.lines.append("main:")
        for statement in node.body:
            self._statement(statement)
        self._emit("HALT")
        return self._out

    # ── Statements ───────────────────────────────────────────────

    def _statement(self, node: Any) -> None:
        if isinstance(node, LetStmt):
            kind, register = self._expression(node.value)
            self._bindings[node.name] = (kind, register)
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
            return

        # Anything else evaluated for its value alone has no effect.
        self._expression(node)

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
                return

        self._out.guards_emitted += 1
        self._emit(f"HGRD    H{register}")

    # ── Expressions ──────────────────────────────────────────────

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

        register = self._alloc_hybit()
        argument = node.args[0]
        if isinstance(argument, Literal) and isinstance(argument.value, int):
            self._emit(f"HLOAD   H{register}, #{argument.value}")
            return HYBIT, register

        kind, index = self._expression(argument)
        if kind is not SCALAR:
            raise CodegenError("load_id takes a scalar index")
        self._emit(f"HLOAD   H{register}, R{index}")
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
            register = self._alloc_hybit()
            self._emit(f"HCADD   H{register}, H{left}, H{right}")
            return HYBIT, register

        mnemonic = {"+": "ADD", "-": "SUB", "*": "MUL"}.get(node.op)
        if mnemonic is None:
            raise CodegenError(f"'{node.op}' has no scalar encoding in H-ISA")
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
            out = self._alloc_scalar()
            self._emit(f"CGET    R{out}, H{register}, #{index}   ; {node.method}")
            return SCALAR, out

        if node.method == "U":
            return self._budget(register)

        if node.method == "rho":
            # ρ = Θ̂ − U, the decomposition identity of §IC.1.24.
            theta = self._alloc_scalar()
            self._emit(f"CGET    R{theta}, H{register}, #0   ; theta")
            _, budget = self._budget(register)
            out = self._alloc_scalar()
            self._emit(f"SUB     R{out}, R{theta}, R{budget}")
            return SCALAR, out

        if node.method == "norm2":
            out = self._alloc_scalar()
            self._emit(f"HNRM2   R{out}, H{register}")
            return SCALAR, out

        if node.method == "dist2":
            if len(node.args) != 1:
                raise CodegenError("dist2 takes one hybit argument")
            other_kind, other = self._expression(node.args[0])
            if other_kind is not HYBIT:
                raise CodegenError("dist2 takes a hybit argument")
            out = self._alloc_scalar()
            self._emit(f"HDIST   R{out}, H{register}, H{other}")
            return SCALAR, out

        raise CodegenError(f".{node.method}() has no H-ISA encoding")

    def _budget(self, register: int) -> Tuple[str, int]:
        """U = Qx + Qs + Qa + 4·Qc, built out of CGET and integer arithmetic.

        The linearity that makes the monoid close (Lemma IIIA.3.2.2) is also
        what makes this four reads and three adds rather than a special
        opcode.
        """
        parts = []
        for name, index in (("Qx", 10), ("Qs", 11), ("Qa", 12), ("Qc", 13)):
            slot = self._alloc_scalar()
            self._emit(f"CGET    R{slot}, H{register}, #{index}   ; {name}")
            parts.append(slot)

        four = self._alloc_scalar()
        self._emit(f"MOVI    R{four}, #4")
        scaled = self._alloc_scalar()
        self._emit(f"MUL     R{scaled}, R{parts[3]}, R{four}   ; 4*Qc")

        total = parts[0]
        for nxt in (parts[1], parts[2], scaled):
            acc = self._alloc_scalar()
            self._emit(f"ADD     R{acc}, R{total}, R{nxt}")
            total = acc
        return SCALAR, total


def generate(ast: Any, psi: Optional[PsiReport] = None) -> Emitted:
    """Compile an HC AST into H-ISA assembly.

    Args:
        ast: The parsed program.
        psi: Optional Ψ report, used to drop guards already proved.

    Returns:
        The emitted assembly.
    """
    return CodeGenerator(psi).generate(ast)
