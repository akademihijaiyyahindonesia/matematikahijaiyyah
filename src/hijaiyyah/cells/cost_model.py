"""Phase 4.2 — Mathematical & Calibrated Architectural Cost Model for Hijaiyyah Cells.

Implements Owner Decisions 7, 8, and 10:
- Separates pure pipeline compute cycles (`compute_cycles`) from UART `PRINT` I/O
  wait cycles (`io_cycles`).
- Calculates graph structural metrics (cell count, DAG depth, critical path,
  average parallelism), HISA instruction count, register pressure (GPR <= 15,
  H-Reg <= 16), memory footprint `M_program`, Candidate B 4-B' verification cost
  `I_verify_B(W)`, and execution latency `T_execution = cycles / f_clk`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hijaiyyah.cells.ir import CellIRGraph, CellOp
from hijaiyyah.cells.spec import EpistemicStatus

#: Tang Nano 20K physical board clock frequency (27 MHz)
BOARD_CLOCK_HZ: float = 27_000_000.0

#: tb_parity.v simulation clock frequency (50 MHz)
SIM_CLOCK_HZ: float = 50_000_000.0

#: Fixed HCPU 5-stage pipeline fill + drain overhead in tb_parity.v
#: Calibrated against RTL: a W-word straight-line non-I/O program executes in
#: exactly `W + 5` cycles on HCPU RTL (`tb_parity.v`).
PIPELINE_FILL_DRAIN_CYCLES: int = 5


@dataclass(frozen=True, slots=True)
class ProgramCostEstimate:
    """Analytical and calibrated architectural cost profile of a compiled Cell program."""

    cell_count: int
    operation_count: int
    dag_depth: int
    critical_path_cells: int
    average_parallelism: float
    instruction_words: int
    relocation_count: int
    print_instruction_count: int
    compute_instruction_count: int
    gpr_used: int
    hreg_used: int
    predicted_compute_cycles: int
    predicted_io_cycles: int
    predicted_total_cycles: int
    verification_instructions_cand_a: int
    verification_instructions_cand_b: int
    verification_savings_cand_b: int
    memory_words_total: int
    latency_compute_us_27mhz: float
    latency_total_us_27mhz: float
    epistemic_status: EpistemicStatus = EpistemicStatus.PREDICTED


def candidate_a_verification_instructions(words: int) -> int:
    """Exact closed-form instruction count of Q-F9e Candidate A (`436c8b7`) loader:
    I_A(W) = 1984 + 1129 * S1(W) + 696 * S2(W) + 111 * W.
    Verified with 0 error across 15 even/odd points (reconcile_abc.py).
    """
    s1 = math.ceil((7 + words) / 128)
    s2 = (6 + words) // 128
    return 1984 + 1129 * s1 + 696 * s2 + 111 * words


def candidate_b_verification_instructions(words: int) -> int:
    """Exact closed-form instruction count of Q-F9e Candidate B loader:
    I_B(W) = 1969 + 1129 * S1(W) + 696 * S2(W) + 94 * W + 5 * floor((W + 1) / 2).
    Verified with 0 error across 15 even/odd points (reconcile_abc.py).
    """
    s1 = math.ceil((7 + words) / 128)
    s2 = (6 + words) // 128
    return 1969 + 1129 * s1 + 696 * s2 + 94 * words + 5 * ((words + 1) // 2)


def estimate_print_io_cycles(printed_values: list[int]) -> int:
    """Calibrated UART TX + decimal conversion cycle cost in `tb_parity.v`
    (`CLK_HZ = 50_000_000, BAUD = 5_000_000` -> 10 clocks/bit, 100 clocks/byte).
    Each printed integer transmits `len(str(val))` ASCII digits plus `\\n` (`0x0A`).
    """
    if not printed_values:
        return 0
    total_chars = sum(len(str(abs(v))) + 1 for v in printed_values)
    # In hcpu_top.v, P_CONV + P_SEND + UART busy takes ~115 cycles per emitted byte
    return total_chars * 115


def build_cost_estimate(
    graph: CellIRGraph,
    instruction_words: int,
    relocation_count: int,
    gpr_used: int,
    hreg_used: int,
    printed_values: list[int],
) -> ProgramCostEstimate:
    """Compute the full architectural cost profile for a compiled `CellIRGraph`."""
    cell_count = len(graph.order)
    op_count = sum(
        1
        for cid in graph.order
        if graph.nodes[cid].op not in (CellOp.LETTER_CONST, CellOp.SCALAR_CONST)
    )
    depth = graph.critical_path_depth
    parallelism = (cell_count / depth) if depth > 0 else 1.0

    print_count = sum(
        1 for cid in graph.order if graph.nodes[cid].op == CellOp.EMIT_OUTPUT
    )
    compute_instr = max(0, instruction_words - print_count)

    # Pure compute cycles on HCPU 5-stage pipeline for straight-line code:
    # compute_instr + 6 pipeline fill/drain cycles
    pred_compute_cycles = compute_instr + PIPELINE_FILL_DRAIN_CYCLES
    pred_io_cycles = estimate_print_io_cycles(printed_values)
    pred_total_cycles = pred_compute_cycles + pred_io_cycles

    ver_a = candidate_a_verification_instructions(instruction_words)
    ver_b = candidate_b_verification_instructions(instruction_words)

    # M_program = code_size + container_header(7) + relocations + loader_staging
    mem_words = instruction_words + 7 + relocation_count

    lat_comp_us = (pred_compute_cycles / BOARD_CLOCK_HZ) * 1e6
    lat_tot_us = (pred_total_cycles / BOARD_CLOCK_HZ) * 1e6

    return ProgramCostEstimate(
        cell_count=cell_count,
        operation_count=op_count,
        dag_depth=depth,
        critical_path_cells=depth,
        average_parallelism=round(parallelism, 3),
        instruction_words=instruction_words,
        relocation_count=relocation_count,
        print_instruction_count=print_count,
        compute_instruction_count=compute_instr,
        gpr_used=gpr_used,
        hreg_used=hreg_used,
        predicted_compute_cycles=pred_compute_cycles,
        predicted_io_cycles=pred_io_cycles,
        predicted_total_cycles=pred_total_cycles,
        verification_instructions_cand_a=ver_a,
        verification_instructions_cand_b=ver_b,
        verification_savings_cand_b=(ver_a - ver_b),
        memory_words_total=mem_words,
        latency_compute_us_27mhz=round(lat_comp_us, 3),
        latency_total_us_27mhz=round(lat_tot_us, 3),
        epistemic_status=EpistemicStatus.PREDICTED,
    )


__all__ = [
    "BOARD_CLOCK_HZ",
    "PIPELINE_FILL_DRAIN_CYCLES",
    "SIM_CLOCK_HZ",
    "ProgramCostEstimate",
    "build_cost_estimate",
    "candidate_a_verification_instructions",
    "candidate_b_verification_instructions",
    "estimate_print_io_cycles",
]
