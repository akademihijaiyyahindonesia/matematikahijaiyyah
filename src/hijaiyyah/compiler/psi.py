# -*- coding: utf-8 -*-
"""Ψ-Injector — static closure analysis for HC.

Stage 4 of the HCC pipeline (Bab III §IIIG.3.1.2). The book states its job as
attaching hybit metadata to every ``hybit`` variable — HAR reference, guard
status flags, provenance hash, and pre-computed U and ρ — so that "setiap
variabel hybit membawa bukti validitasnya sendiri", and compares this to
refinement types in Liquid Haskell or dependent types in Idris/Agda.

The interesting half is what that proof buys. Two results from Bab III make it
possible to discharge guard checks at compile time rather than at run time:

* All 28 sealed letters satisfy G1–G4 and T1–T2 (verified 28/28, [CC]).
* ℋ is closed under ``+`` — Proposisi IIIA.3.2.1 — and Lemma IIIA.3.2.2 shows
  that closure holds *because* ``U = Qx + Qs + Qa + 4·Qc`` is linear. A
  non-linear term in U and the monoid would not close.

Together: any expression built only from letter literals and ``+`` is provably
in ℋ without executing a single guard. The runtime check is only needed where
a value enters from outside that closed world — I/O, a function parameter, a
memory load, a decoded frame. That turns the O(1) intrinsic validation the
paradigm is built on into O(0) across the closed fragment.

Two limits are deliberate, and both are recorded on the facts rather than
assumed away:

* ``proven_valid`` currently implies the vector is known, because the only
  sources of proof are a literal and a sum of literals. A future hybit-typed
  function parameter would be valid-but-unknown; the field is kept separate
  from ``vector`` so that extension does not change the meaning of either.
* A proof that holds in Python does not automatically hold on the HCPU. H-Reg
  components are 8-bit unsigned (§IIIJ.3.3.2), and §IIIK.3.3 notes HCADD is
  safe for roughly 30 letters before an 8-bit component overflows. So the
  analysis carries ``hardware_safe`` separately: a sum that is valid here can
  still wrap on silicon, and a guard elided on that basis would be unsound.

Subtraction is never a proof source. ℋ is a commutative monoid, not a group
(Proposisi IIIA.3.2.2): it has no additive inverse, and a difference can leave
ℤ₊ entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from hijaiyyah.core.guards import compute_rho, compute_U, full_guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.language.ast_nodes import (
    AssignStmt,
    BinaryExpr,
    Block,
    CallExpr,
    ConstStmt,
    FnDecl,
    LetStmt,
    Literal,
    MethodCall,
    Program,
    VarRef,
)

#: Widest value an H-Reg component can hold (18 × 8-bit unsigned).
HREG_COMPONENT_MAX = 255

#: Method calls that ask a value whether it satisfies the guard system.
GUARD_METHODS = frozenset({"guard", "guard_check", "is_valid"})

#: Widest component across the 28 sealed letters — Θ̂(هـ) = 8. Derived, not
#: written down, so a table change cannot leave a stale bound behind.
SEALED_COMPONENT_MAX = max(max(e.vector) for e in MASTER_TABLE.all_entries())


@dataclass(frozen=True)
class HybitFacts:
    """What the compiler knows about one expression's hybit value.

    Attributes:
        proven_valid: True when the value is provably in ℋ without a runtime
            guard. False means unknown, never "known invalid".
        vector: The constant-folded 18D codex, when statically known.
        max_component: Upper bound on any component, when one can be proved.
            None means no bound is known, which blocks the hardware claim.
        har_ref: Registry reference, set only for a single sealed letter.
        reason: Why the verdict holds, quoted in diagnostics and the report.
    """

    proven_valid: bool = False
    vector: Optional[Tuple[int, ...]] = None
    max_component: Optional[int] = None
    har_ref: Optional[str] = None
    reason: str = "no information"

    @property
    def theta(self) -> Optional[int]:
        """Θ̂, the global turning of the folded vector, when known."""
        return None if self.vector is None else self.vector[0]

    @property
    def budget_u(self) -> Optional[int]:
        """Pre-computed U, the non-primary turning budget."""
        return None if self.vector is None else compute_U(list(self.vector))

    @property
    def residue_rho(self) -> Optional[int]:
        """Pre-computed ρ = Θ̂ − U, the primary turning residue."""
        return None if self.vector is None else compute_rho(list(self.vector))

    @property
    def guard_flags(self) -> Optional[Dict[str, bool]]:
        """G1–G4 and T1–T2 evaluated on the folded vector."""
        return None if self.vector is None else full_guard_check(list(self.vector))

    @property
    def hardware_safe(self) -> bool:
        """True when every component provably fits the 8-bit H-Reg field.

        An unknown bound is not safe. A guard elided on a value that wraps on
        silicon would be exactly the unsound optimisation this pass exists to
        avoid.
        """
        return self.max_component is not None and self.max_component <= HREG_COMPONENT_MAX

    def can_discharge_guard(self) -> bool:
        """True when a guard check on this value may be folded away.

        Both halves are required: the value must be provably in ℋ, and the
        proof must survive the 8-bit H-Reg components the HCPU actually has.
        """
        return self.proven_valid and self.hardware_safe


UNKNOWN = HybitFacts(reason="not a statically known hybit expression")


@dataclass
class GuardSite:
    """One guard check found in the source, and whether it can be elided."""

    method: str
    facts: HybitFacts
    discharged: bool


@dataclass
class PsiReport:
    """The outcome of one Ψ-injection pass."""

    facts: Dict[int, HybitFacts] = field(default_factory=dict)
    bindings: Dict[str, HybitFacts] = field(default_factory=dict)
    guard_sites: List[GuardSite] = field(default_factory=list)

    @property
    def guards_total(self) -> int:
        return len(self.guard_sites)

    @property
    def guards_discharged(self) -> int:
        return sum(1 for site in self.guard_sites if site.discharged)

    def summary(self) -> str:
        """One line fit for compiler output."""
        total = self.guards_total
        if total == 0:
            return "Ψ: no guard sites"
        done = self.guards_discharged
        return (
            f"Ψ: {done}/{total} guard checks discharged statically "
            f"({total - done} left for run time)"
        )


class PsiInjector:
    """Walks an HC AST and annotates every hybit expression with its proof.

    The pass does not change semantics. It records what is provable, so a
    later stage can fold a guard check to a constant instead of emitting
    ``HGRD``.
    """

    def __init__(self) -> None:
        self._scopes: List[Dict[str, HybitFacts]] = [{}]
        self._reassigned: Set[str] = set()
        self._report = PsiReport()

    # ── Entry point ──────────────────────────────────────────────

    def inject(self, node: Any) -> PsiReport:
        """Analyse a parsed program and return what was proved.

        Args:
            node: The AST root, normally a ``Program``.

        Returns:
            A :class:`PsiReport` holding per-node facts, top-level bindings,
            and every guard site with its verdict.
        """
        self._scopes = [{}]
        self._reassigned = self._collect_reassigned(node)
        self._report = PsiReport()
        self._visit(node)
        self._report.bindings = dict(self._scopes[0])
        return self._report

    # ── Soundness pre-pass ───────────────────────────────────────

    def _collect_reassigned(self, node: Any) -> Set[str]:
        """Names that are ever reassigned, anywhere in the program.

        A binding whose value can change is treated as unknown throughout,
        rather than tracked per program point. That is a coarse
        over-approximation, and it is the safe direction: it can only give up
        a proof, never invent one.
        """
        found: Set[str] = set()
        stack: List[Any] = [node]
        while stack:
            current = stack.pop()
            if isinstance(current, AssignStmt):
                found.add(current.name)
            if isinstance(current, (LetStmt, ConstStmt)) and getattr(
                current, "mutable", False
            ):
                found.add(current.name)
            stack.extend(self._children(current))
        return found

    @staticmethod
    def _children(node: Any) -> List[Any]:
        """Every AST child of a node, without knowing its shape."""
        if not hasattr(node, "__dataclass_fields__"):
            return []
        out: List[Any] = []
        for name in node.__dataclass_fields__:
            value = getattr(node, name, None)
            if isinstance(value, list):
                out.extend(item for item in value if isinstance(item, object))
            elif value is not None:
                out.append(value)
        return out

    # ── Scope handling ───────────────────────────────────────────

    def _lookup(self, name: str) -> HybitFacts:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return UNKNOWN

    def _bind(self, name: str, facts: HybitFacts) -> None:
        self._scopes[-1][name] = facts

    # ── Traversal ────────────────────────────────────────────────

    def _visit(self, node: Any) -> HybitFacts:
        """Analyse one node, record its facts, and return them."""
        if node is None or not hasattr(node, "__dataclass_fields__"):
            return UNKNOWN

        if isinstance(node, Program):
            for stmt in node.body:
                self._visit(stmt)
            return UNKNOWN

        if isinstance(node, Block):
            self._scopes.append({})
            for stmt in node.statements:
                self._visit(stmt)
            self._scopes.pop()
            return UNKNOWN

        if isinstance(node, FnDecl):
            # Parameters arrive from outside the closed world.
            self._scopes.append({})
            self._visit(node.body)
            self._scopes.pop()
            return UNKNOWN

        if isinstance(node, (LetStmt, ConstStmt)):
            facts = self._visit(node.value)
            if node.name in self._reassigned:
                facts = HybitFacts(reason=f"'{node.name}' is reassigned elsewhere")
            self._bind(node.name, facts)
            self._record(node, facts)
            return facts

        if isinstance(node, AssignStmt):
            self._visit(node.value)
            self._bind(node.name, UNKNOWN)
            return UNKNOWN

        if isinstance(node, Literal):
            return self._record(node, self._literal_facts(node))

        if isinstance(node, VarRef):
            return self._record(node, self._lookup(node.name))

        if isinstance(node, BinaryExpr):
            return self._record(node, self._binary_facts(node))

        if isinstance(node, CallExpr):
            return self._record(node, self._call_facts(node))

        if isinstance(node, MethodCall):
            return self._record(node, self._method_facts(node))

        for child in self._children(node):
            self._visit(child)
        return UNKNOWN

    def _record(self, node: Any, facts: HybitFacts) -> HybitFacts:
        self._report.facts[id(node)] = facts
        return facts

    # ── The rules ────────────────────────────────────────────────

    def _literal_facts(self, node: Literal) -> HybitFacts:
        """A sealed letter is proof by itself.

        Every one of the 28 canonical entries satisfies G1–G4 and T1–T2, which
        the project verifies exhaustively in both Python and RTL. Nothing else
        in the grammar produces a hybit constant.
        """
        if node.lit_type != "hybit_ref":
            return HybitFacts(reason=f"{node.lit_type} literal is not a hybit")

        entry = MASTER_TABLE.get_by_char(node.value)
        if entry is None:
            return HybitFacts(reason=f"'{node.value}' is not a canonical letter")

        return HybitFacts(
            proven_valid=True,
            vector=tuple(entry.vector),
            max_component=max(entry.vector),
            har_ref=f"HM-28:{entry.index:02d}",
            reason=f"sealed letter {entry.char} (index {entry.index})",
        )

    def _binary_facts(self, node: BinaryExpr) -> HybitFacts:
        """Closure under ``+``, and nothing else.

        Proposisi IIIA.3.2.1 gives closure for addition. Subtraction is
        excluded on purpose: ℋ has no additive inverse, so a difference can
        leave the non-negative cone and stop being a hybit at all.
        """
        left = self._visit(node.left)
        right = self._visit(node.right)

        if node.op != "+":
            return HybitFacts(
                reason=f"'{node.op}' does not preserve ℋ (monoid, not a group)"
            )

        if not (left.proven_valid and right.proven_valid):
            return HybitFacts(reason="an operand is not a proven hybit")

        bound: Optional[int] = None
        if left.max_component is not None and right.max_component is not None:
            bound = left.max_component + right.max_component

        total: Optional[Tuple[int, ...]] = None
        if left.vector is not None and right.vector is not None:
            total = tuple(a + b for a, b in zip(left.vector, right.vector, strict=True))
            bound = max(total)

        if bound is None:
            note = "closure under + (Proposisi IIIA.3.2.1); component bound unknown"
        elif bound <= HREG_COMPONENT_MAX:
            note = f"closure under + (Proposisi IIIA.3.2.1); widest component {bound}"
        else:
            note = (
                f"closure holds, but component {bound} exceeds the 8-bit H-Reg "
                f"field — the proof does not transfer to the HCPU"
            )

        return HybitFacts(
            proven_valid=True,
            vector=total,
            max_component=bound,
            reason=note,
        )

    def _call_facts(self, node: CallExpr) -> HybitFacts:
        """Builtins whose contract already guarantees a member of ℋ.

        ``load_id(i)`` either returns one of the 28 sealed entries or raises,
        so a value that arrives from it is valid whatever the index was — the
        vector stays unknown, but the bound does not, because no sealed
        component exceeds Θ̂(هـ).

        ``zero()`` is the monoid identity. Proposisi IIIA.3.2.1 needs it in ℋ
        for ℋ to be a monoid at all, and the guard system agrees: the zero
        vector passes G1–G4 and T1–T2 vacuously.
        """
        for arg in node.args:
            self._visit(arg)

        if node.callee == "load_id":
            return HybitFacts(
                proven_valid=True,
                max_component=SEALED_COMPONENT_MAX,
                reason="load_id returns a sealed letter or raises",
            )

        if node.callee == "zero":
            return HybitFacts(
                proven_valid=True,
                vector=tuple([0] * 18),
                max_component=0,
                reason="monoid identity (Proposisi IIIA.3.2.1)",
            )

        return HybitFacts(reason=f"'{node.callee}' has no proven hybit contract")

    def _method_facts(self, node: MethodCall) -> HybitFacts:
        """Record a guard site, and keep walking."""
        receiver = self._visit(node.obj)
        for arg in node.args:
            self._visit(arg)

        if node.method in GUARD_METHODS:
            self._report.guard_sites.append(
                GuardSite(
                    method=node.method,
                    facts=receiver,
                    discharged=receiver.can_discharge_guard(),
                )
            )
        return UNKNOWN


def inject(ast: Any) -> PsiReport:
    """Run Ψ-injection over a parsed HC program.

    Args:
        ast: The AST root produced by :class:`hijaiyyah.language.parser.Parser`.

    Returns:
        The :class:`PsiReport` for that program.
    """
    return PsiInjector().inject(ast)
