"""Phase 3.2 — Machine-Independent Hijaiyyah Cells Intermediate Representation (Cell IR).

Every node preserves:
- Source location (line, col)
- Source glyphs
- Master Table identity (HM-28:01..28) and dataset version (HM-28-v.1.0-HC18D)
- Mathematical operation identity
- Input and dependency references (DAG edges)
- Output type (HYBIT, SCALAR, DELTA14, BOOL, EXOMATRIX, VECTOR3, VECTOR5)
- Static proof & hardware 8-bit safety facts (including two-layer 6-guard + H* proof)
- Control-flow basic block placement (supporting both acyclic DAGs and CFGs
  with branches, bounded loops, subroutines, and official HOS syscalls)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from hijaiyyah.cells.dataset_engine import DATASET_ID
from hijaiyyah.cells.spec import SixGuardClosureProof


class CellValueType(str, Enum):
    """Static and runtime value types in Hijaiyyah Cells IR."""

    HYBIT = "hybit"          # 18D codex vector in N_0^18
    SCALAR = "scalar"        # 32-bit integer scalar
    DELTA14 = "delta14"      # 14D difference vector in Z^14 (Domain C)
    BOOL = "bool"            # Boolean / guard / comparison result
    VECTOR3 = "vector3"      # 3D subvector (Nuqtah or Anasir)
    VECTOR5 = "vector5"      # 5D subvector (Khatt or Qaws)
    EXOMATRIX = "exomatrix"  # 5x5 audit matrix
    VOID = "void"            # Statement with side effect (guard/emit/branch/loop)


class CellOp(str, Enum):
    """Canonical mathematical and system operations in Cell IR."""

    LETTER_CONST = "LETTER_CONST"        # Load canonical letter from HM-28
    WORD_ACCUM = "WORD_ACCUM"            # Sum sequence of canonical letters (0xE0..0xFB / HCADD)
    ZERO_HYBIT = "ZERO_HYBIT"            # Monoid identity 0 in N_0^18
    LOAD_ID = "LOAD_ID"                  # Dynamic/static 1-based letter lookup (§(n) / HLOAD)
    SCALAR_CONST = "SCALAR_CONST"        # Integer literal
    HYBIT_ADD = "HYBIT_ADD"              # Monoid addition u + v in N_0^18
    HYBIT_DELTA = "HYBIT_DELTA"          # Differential Delta(u, v) in Z^14
    HYBIT_EQ = "HYBIT_EQ"                # 18-component hybit equality (CEQ 0x47, incl. H*)
    SCALAR_ADD = "SCALAR_ADD"            # Integer +
    SCALAR_SUB = "SCALAR_SUB"            # Integer -
    SCALAR_MUL = "SCALAR_MUL"            # Integer *
    CMP_EQ = "CMP_EQ"                    # Scalar ==
    CMP_NE = "CMP_NE"                    # Scalar !=
    CMP_LT = "CMP_LT"                    # Scalar <
    CMP_GT = "CMP_GT"                    # Scalar >
    CMP_LE = "CMP_LE"                    # Scalar <=
    CMP_GE = "CMP_GE"                    # Scalar >=
    PROJ_COMPONENT = "PROJ_COMPONENT"    # v[i] for i in 0..17 (CGET)
    PROJ_THETA = "PROJ_THETA"            # Theta_hat(h) = v[0] (CGET #0)
    TURNING_U = "TURNING_U"              # B = U(h) (CU 0x4D)
    TURNING_RHO = "TURNING_RHO"          # R = rho(h) (CRHO 0x4C)
    MOD4_GATE = "MOD4_GATE"              # Theta_hat(h) mod 4 (CMOD4 0x4F)
    NORM2_V14 = "NORM2_V14"              # ||v14(h)||_2^2 (HNRM2 0x06)
    DIST2_V14 = "DIST2_V14"              # d_2^2(a, b) (HDIST 0x07)
    INNER_V14 = "INNER_V14"              # <a, b>_14 (polarization identity)
    PROJ_GROUP_N = "PROJ_GROUP_N"        # N(h) = (Na, Nb, Nd)
    PROJ_GROUP_K = "PROJ_GROUP_K"        # K(h) = (Kp, Kx, Ks, Ka, Kc)
    PROJ_GROUP_Q = "PROJ_GROUP_Q"        # Q(h) = (Qp, Qx, Qs, Qa, Qc)
    PROJ_GROUP_A = "PROJ_GROUP_A"        # A(h) = (AN, AK, AQ)
    PROJ_HSTAR = "PROJ_HSTAR"            # H*(h) = v[17] (CGET #17)
    EXOMATRIX_PHI = "EXOMATRIX_PHI"      # Frobenius energy Phi(h)
    HISAB_PACK = "HISAB_PACK"            # HPACK word 0..2 (0x50)
    HISAB_CRC = "HISAB_CRC"              # HCRC digest (0x51)
    GUARD_CHECK = "GUARD_CHECK"          # Guard G1-G4, T1-T2 (HGRD 0x60)
    EMIT_OUTPUT = "EMIT_OUTPUT"          # Emit scalar to output stream (PRINT 0xA0)
    VAR_ASSIGN = "VAR_ASSIGN"            # Rebind existing cell variable
    COND_BRANCH = "COND_BRANCH"          # Structured conditional branch (? / if)
    WHILE_LOOP = "WHILE_LOOP"            # Structured bounded loop (↻ / while)
    FN_PARAM = "FN_PARAM"                # Subroutine parameter slot
    FN_CALL = "FN_CALL"                  # Subroutine invocation (CALL / RET)
    HOS_SYSCALL = "HOS_SYSCALL"          # Official HOS syscall ⏣(sys_num, arg [, hybit])
    HFS_READ_HYBIT = "HFS_READ_HYBIT"    # Official HFS_READ (SYSCALL 7) returning H0


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """1-based source location span."""

    line: int
    col: int


@dataclass
class CellSubroutineDef:
    """Subroutine definition in a `CellIRGraph`."""

    name: str
    params: list[str] = field(default_factory=list)
    param_node_ids: list[str] = field(default_factory=list)
    body_node_ids: list[str] = field(default_factory=list)
    return_node_id: str = ""
    return_type: CellValueType = CellValueType.SCALAR


@dataclass
class CellIRNode:
    """One computational or control cell in the Hijaiyyah Cells IR."""

    cell_id: str
    op: CellOp
    source_glyphs: str
    span: SourceSpan
    inputs: list[str] = field(default_factory=list)
    output_type: CellValueType = CellValueType.HYBIT
    binding_name: str | None = None
    master_table_id: str | None = None
    dataset_version: str = DATASET_ID
    imm_param: int | None = None
    letter_sequence: tuple[str, ...] = field(default_factory=tuple)

    # Control-flow & subroutine fields
    then_node_ids: list[str] = field(default_factory=list)
    else_node_ids: list[str] = field(default_factory=list)
    loop_cond_node_ids: list[str] = field(default_factory=list)
    loop_body_node_ids: list[str] = field(default_factory=list)
    callee_name: str | None = None

    # Static semantic & Ψ-analysis annotations populated by SemanticAnalyzer
    static_vector: tuple[int, ...] | None = None
    static_scalar: int | None = None
    max_component: int | None = None
    proven_in_H: bool = False
    hardware_8bit_safe: bool = False
    hstar_coupled_bound_proven: bool = False
    guard_discharged: bool = False
    use_h0_native_opcodes: bool = False
    six_guard_proof: SixGuardClosureProof | None = None
    provenance_note: str = ""


@dataclass
class CellBasicBlock:
    """Control-flow graph basic block containing an ordered DAG of CellIRNodes."""

    block_id: str
    node_ids: list[str] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)


@dataclass
class CellIRGraph:
    """Complete Hijaiyyah Cells Intermediate Representation (DAG + CFG)."""

    source_language: str
    dataset_version: str = DATASET_ID
    nodes: dict[str, CellIRNode] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    bindings: dict[str, str] = field(default_factory=dict)
    subroutines: dict[str, CellSubroutineDef] = field(default_factory=dict)
    blocks: dict[str, CellBasicBlock] = field(
        default_factory=lambda: {"entry": CellBasicBlock(block_id="entry")}
    )
    entry_block: str = "entry"

    def add_node(
        self,
        node: CellIRNode,
        block_id: str = "entry",
        *,
        top_level: bool = True,
    ) -> str:
        if node.cell_id in self.nodes:
            raise ValueError(f"Duplicate cell_id in CellIRGraph: {node.cell_id}")
        self.nodes[node.cell_id] = node
        if top_level:
            self.order.append(node.cell_id)
        if block_id not in self.blocks:
            self.blocks[block_id] = CellBasicBlock(block_id=block_id)
        self.blocks[block_id].node_ids.append(node.cell_id)
        if node.binding_name and top_level:
            self.bindings[node.binding_name] = node.cell_id
        return node.cell_id

    @property
    def edge_count(self) -> int:
        """Total number of dependency edges across all nodes in the graph."""
        return sum(len(n.inputs) for n in self.nodes.values())

    def topological_depths(self) -> dict[str, int]:
        """Compute dependency depth of every node in the DAG (1-based)."""
        depths: dict[str, int] = {}
        for cid in self.nodes:
            node = self.nodes[cid]
            if not node.inputs:
                depths[cid] = 1
            else:
                depths[cid] = 1 + max(depths.get(inp, 1) for inp in node.inputs)
        return depths

    @property
    def critical_path_depth(self) -> int:
        depths = self.topological_depths()
        return max(depths.values(), default=0)


__all__ = [
    "CellBasicBlock",
    "CellIRGraph",
    "CellIRNode",
    "CellOp",
    "CellSubroutineDef",
    "CellValueType",
    "SourceSpan",
]
