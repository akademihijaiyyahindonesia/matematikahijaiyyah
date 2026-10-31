"""Phase 4.4 — HPG1 Container & Trusted 4-B' Verification / HCPU Execution Bridge.

Implements the complete end-to-end execution path:
Hijaiyyah Source (.hcell / .hc) -> Lexer -> Parser -> Cell IR -> Semantic Analyzer
-> Reference Evaluator (Exact Z^18 & 8-bit Hardware Model) -> HISA Backend
-> HPG1 Container -> 4-B' Verifier -> HCPU.

Separates pure compute cycles (`rtl_compute_cycles`, measured on `compute_only_words`
without `PRINT` UART waits) from total execution cycles (`rtl_total_cycles`, with
`PRINT` UART waits), and verifies equivalence across:
1. Reference `CellEvaluator` (exact N_0^18 and 8-bit hardware-wrapped `hw_eval_result`)
2. Python `HISAMachine` (both standard and 8-bit hardware-wrapped `hvm_hw_8bit_*`)
3. Hardware `HCPU` RTL (`tb_hcpu_prog_load_card.vvp` + `tb_parity.v`)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hijaiyyah.cells.cost_model import ProgramCostEstimate, build_cost_estimate
from hijaiyyah.cells.evaluator import CellEvaluationResult, CellEvaluator
from hijaiyyah.cells.hisa_backend import CellHISABackend, CompiledHISAProgram
from hijaiyyah.cells.ir import CellIRGraph
from hijaiyyah.cells.lexer import tokenize_hcell
from hijaiyyah.cells.parser import parse_hc_to_cell_ir, parse_hcell
from hijaiyyah.cells.semantic import SemanticAnalysisReport, SemanticAnalyzer
from hijaiyyah.cells.spec import EpistemicStatus
from hijaiyyah.core.guards import guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.language.lexer import Lexer as HCLexer

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT / "rtl" / "scripts"
PROGRAMS_DIR = ROOT / "rtl" / "programs"
TB_DIR = ROOT / "rtl" / "tb"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_container import (  # type: ignore[import-not-found]  # noqa: E402, I001
    build as build_hpg1_container,
    card_image,
    load_check,
)

DEFAULT_OVERLAY_LOAD_ADDR: int = 0x900


@dataclass
class HCPUExecutionMeasurement:
    """Measured or simulated execution state from HCPU RTL (`tb_parity.v`)."""

    halted: bool
    compute_cycles: int
    total_cycles: int
    io_cycles: int
    flags: int
    gpr: dict[int, int]
    hreg: dict[int, tuple[int, ...]]
    printed_outputs: list[int]
    rtl_4b_prime_verdict: dict[str, int] | None


@dataclass
class EndToEndPipelineResult:
    """Complete auditable result of compiling, verifying, and executing a Hijaiyyah program."""

    source_bytes: int
    token_count: int
    compile_time_ms: float
    graph: CellIRGraph
    semantic_report: SemanticAnalysisReport
    eval_result: CellEvaluationResult
    hw_eval_result: CellEvaluationResult
    compiled: CompiledHISAProgram
    container_words: list[int]
    card_sectors: dict[int, list[int]]
    verify_4b_prime_ok: bool
    verify_4b_prime_reason: str
    hvm_outputs: list[int]
    hvm_steps: int
    hvm_compute_steps: int
    hvm_guard_pass: bool
    hvm_hw_8bit_outputs: list[int]
    hvm_hw_8bit_guard_pass: bool
    cost_estimate: ProgramCostEstimate
    rtl_measurement: HCPUExecutionMeasurement | None
    three_way_parity: bool
    hw_rtl_parity: bool
    epistemic_status: EpistemicStatus


_PARITY_SIM_CACHE: Path | None = None


def _get_parity_sim_binary() -> Path | None:
    global _PARITY_SIM_CACHE
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        return None

    out_dir = Path(tempfile.gettempdir()) / "hijaiyyah_cells_rtl_sim"
    out_dir.mkdir(parents=True, exist_ok=True)
    vvp_path = out_dir / "tb_parity_cells.vvp"
    rtl_files = [
        TB_DIR / "tb_parity.v",
        *sorted((ROOT / "rtl").glob("*.v")),
        *sorted((ROOT / "rtl").glob("*.vh")),
    ]
    newest_rtl_mtime = max(p.stat().st_mtime for p in rtl_files if p.is_file())
    if (
        _PARITY_SIM_CACHE is not None
        and _PARITY_SIM_CACHE.is_file()
        and _PARITY_SIM_CACHE.stat().st_mtime >= newest_rtl_mtime
    ):
        return _PARITY_SIM_CACHE

    if not vvp_path.is_file() or vvp_path.stat().st_mtime < newest_rtl_mtime:
        sources = [
            str(TB_DIR / "tb_parity.v"),
            *sorted(str(p) for p in (ROOT / "rtl").glob("*.v")),
        ]
        proc = subprocess.run(
            ["iverilog", "-g2012", "-I", str(ROOT / "rtl"), "-o", str(vvp_path), *sources],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return None
    _PARITY_SIM_CACHE = vvp_path
    return vvp_path


def _run_rtl_words(sim: Path, words: list[int], max_cycles: int = 8000) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".hex", delete=False) as fh:
        fh.write("".join(f"{w:08X}\n" for w in words))
        hex_name = fh.name
    try:
        proc = subprocess.run(
            ["vvp", str(sim), f"+PROGRAM={hex_name}", f"+CYCLES={max_cycles}", "+TRACE"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        Path(hex_name).unlink(missing_ok=True)

    tx_bytes: list[int] = []
    gpr: dict[int, int] = {}
    hreg: dict[int, tuple[int, ...]] = {}
    cycles = 0
    halted = False
    flags = 0

    for line in proc.stdout.splitlines():
        s = line.strip()
        if s.startswith("T ") and " TX " in s:
            tx_bytes.append(int(s.split()[-1], 16))
        elif m := re.fullmatch(r"GPR\[(\d+)\]=([0-9A-Fa-f]{8})", s):
            gpr[int(m.group(1))] = int(m.group(2), 16)
        elif m := re.fullmatch(r"HREG\[(\d+)\]=([0-9A-Fa-f]{36})", s):
            packed = int(m.group(2), 16)
            hreg[int(m.group(1))] = tuple((packed >> (8 * i)) & 0xFF for i in range(18))
        elif m := re.fullmatch(r"CYCLES=(\d+)", s):
            cycles = int(m.group(1))
        elif m := re.fullmatch(r"HALTED=(\d+)", s):
            halted = m.group(1) == "1"
        elif m := re.fullmatch(r"FLAGS=([0-9A-Fa-f]{2})", s):
            flags = int(m.group(1), 16)

    tx_text = bytes(tx_bytes).decode("ascii", errors="replace")
    tx_ints = [int(x) for x in tx_text.strip().splitlines() if x.strip()]
    return {
        "halted": halted,
        "cycles": cycles,
        "flags": flags,
        "gpr": gpr,
        "hreg": hreg,
        "printed_outputs": tx_ints,
    }


def _run_rtl_4b_prime_card(card: dict[int, list[int]]) -> dict[str, int] | None:
    if shutil.which("vvp") is None:
        return None
    bench = TB_DIR / "tb_hcpu_prog_load_card.vvp"
    if not bench.is_file():
        subprocess.run(
            ["make", "-s", "tb_hcpu_prog_load_card.vvp", "shell_progload.hex"],
            cwd=TB_DIR,
            check=True,
            capture_output=True,
        )
    words = [w for s in range(16, 24) for w in card.get(s, [0] * 128)]
    with tempfile.NamedTemporaryFile("w", suffix=".hex", delete=False) as fh:
        fh.write("\n".join(f"{w:08X}" for w in words) + "\n")
        card_hex = fh.name
    try:
        out = subprocess.run(
            ["vvp", bench.name, f"+CARD={card_hex}"],
            cwd=TB_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout
    finally:
        os.unlink(card_hex)
    line = next((ln for ln in out.splitlines() if ln.startswith("DONE=")), None)
    if line is None:
        return None
    return {k: int(v) for k, v in (p.split("=") for p in line.split())}


def _run_hvm_program(
    hvm: HISAMachine,
    words: list[int],
    *,
    enable_hos_syscalls: bool = False,
    suppress_syscall_print: bool = False,
    wrap_hreg_8bit: bool = False,
) -> None:
    """Execute `words` on `HISAMachine`, servicing HOS syscalls if `enable_hos_syscalls` is True."""
    hvm.load_program(words)
    if not enable_hos_syscalls and not wrap_hreg_8bit:
        hvm.run()
        return

    hfs_files: dict[int, tuple[int, ...]] = {}
    hreg_ovf: list[bool] = [False] * 16
    while not hvm._halted and hvm.cycle < 50000:
        pc_before = hvm.regs.pc
        raw_iw = hvm.code[pc_before] if 0 <= pc_before < len(hvm.code) else 0
        op_byte = (raw_iw >> 24) & 0xFF
        dst_idx = (raw_iw >> 20) & 0xF
        s1_idx = (raw_iw >> 16) & 0xF
        s2_idx = (raw_iw >> 12) & 0xF
        step_entry = hvm.step()
        if step_entry is None:
            break
        if wrap_hreg_8bit:
            if op_byte == 0x40 or op_byte == 0x47:  # HLOAD or CZERO clears sticky ovf
                hreg_ovf[dst_idx] = False
            elif op_byte == 0x46:  # CMOV copies sticky ovf
                hreg_ovf[dst_idx] = hreg_ovf[s1_idx]
            elif op_byte == 0x42:  # HCADD latches sticky ovf if any lane > 255
                any_ovf = any(int(c) > 255 for c in hvm.regs.hreg[dst_idx])
                hreg_ovf[dst_idx] = hreg_ovf[s1_idx] or hreg_ovf[s2_idx] or any_ovf
            elif 0xE0 <= op_byte <= 0xFB:  # Letter instruction into H0
                any_ovf = any(int(c) > 255 for c in hvm.regs.hreg[0])
                hreg_ovf[0] = hreg_ovf[0] or any_ovf
            for h_idx in range(len(hvm.regs.hreg)):
                hvm.regs.hreg[h_idx] = [int(c) & 0xFF for c in hvm.regs.hreg[h_idx]]
            if op_byte == 0x4C:  # CRHO in 8-bit hardware returns 32-bit two's complement
                hvm.regs.gpr[dst_idx] = int(hvm.regs.gpr[dst_idx]) & 0xFFFFFFFF
            elif op_byte == 0x60:  # HGRD on 8-bit wrapped H-Reg (coupled H* + sticky ovf)
                v = hvm.regs.hreg[s1_idx]
                hstar_ok = (v[17] == v[7]) and (v[17] <= (v[0] >> 1))
                hvm.regs.sr.guard_pass = bool(
                    guard_check(v) and hstar_ok and not hreg_ovf[s1_idx]
                )
        if hvm._syscall:
            hvm._syscall = False
            sys_num = int(hvm.regs.gpr[1]) & 0xFFFFFFFF
            arg = int(hvm.regs.gpr[2]) & 0xFFFFFFFF
            if sys_num == 1:
                if not suppress_syscall_print:
                    hvm.output.append(arg)
                hvm.regs.gpr[1] = 1
            elif sys_num == 2:
                hvm.regs.gpr[1] = 0
            elif sys_num == 3:
                hvm.regs.gpr[1] = 1
            elif sys_num == 4:
                hvm.regs.gpr[1] = 1
                hvm._halted = True
            elif sys_num == 6:
                if 0 <= arg < 8 and arg not in hfs_files and len(hfs_files) < 8:
                    hfs_files[arg] = (0,) * 18
                    hvm.regs.gpr[1] = 1
                else:
                    hvm.regs.gpr[1] = 0
            elif sys_num == 7:
                if arg in hfs_files:
                    hvm.regs.hreg[0] = list(hfs_files[arg])
                    hvm.regs.gpr[1] = 1
                else:
                    hvm.regs.gpr[1] = 0
            elif sys_num == 8:
                vec = tuple(int(x) & 0xFF for x in hvm.regs.hreg[0])
                if arg in hfs_files and guard_check(list(vec)):
                    hfs_files[arg] = vec
                    hvm.regs.gpr[1] = 1
                else:
                    hvm.regs.gpr[1] = 0
            elif sys_num == 9:
                hvm.regs.gpr[1] = 1 if arg == 1 else 0
            else:
                hvm.regs.gpr[1] = 0


def _build_rtl_syscall_harness_words(
    user_asm: str,
    *,
    suppress_syscall_print: bool = False,
) -> list[int]:
    """Wrap pure user-mode assembly with a supervisor HOS trap dispatcher (`hos.hasm`)."""
    from hijaiyyah.hisa.assembler import assemble

    sys1_body = "        NOP" if suppress_syscall_print else "        PRINT R2"
    harness_asm = f"""; RTL HOS Syscall Trap Harness for tb_parity.v
        MOVI  R0, 0
        CALL  hos_heap_init
        MOVI  R12, _hos_trap_entry
        STORE R12, R0, 0xFF8
        MOVI  R12, 0
        JMP   _user_prog_start

_hos_trap_entry:
        STORE R0, R0, 0xDF0
        MOVI  R0, 0
        STORE R2, R0, 0xDF2
        STORE R3, R0, 0xDF3
        STORE R4, R0, 0xDF4
        STORE R6, R0, 0xDF6
        STORE R7, R0, 0xDF7
        STORE R8, R0, 0xDF8
        STORE R9, R0, 0xDF9
        STORE R10, R0, 0xDFA
        STORE R11, R0, 0xDFB
        STORE R12, R0, 0xDFC
        STORE R13, R0, 0xDFD
        STORE R14, R0, 0xDFE
        STORE R15, R0, 0xDFF
        LOAD  R15, R0, 0xFF9
        ADDI  R15, R15, 1
        STORE R15, R0, 0xFF9
        CMPI  R1, 1
        JEQ   _sys_1
        CMPI  R1, 2
        JEQ   _sys_2
        CMPI  R1, 3
        JEQ   _sys_3
        CMPI  R1, 4
        JEQ   _sys_4
        CMPI  R1, 6
        JEQ   _sys_6
        CMPI  R1, 7
        JEQ   _sys_7
        CMPI  R1, 8
        JEQ   _sys_8
        CMPI  R1, 9
        JEQ   _sys_9
        MOVI  R1, 0
        JMP   _sys_ret
_sys_1:
{sys1_body}
        MOVI  R1, 1
        JMP   _sys_ret
_sys_2:
        MOVI  R1, 0
        JMP   _sys_ret
_sys_3:
        MOVI  R1, 1
        JMP   _sys_ret
_sys_4:
        MOVI  R1, 1
        HALT
_sys_6:
        MOV   R1, R2
        CALL  hos_fs_create
        JMP   _sys_ret
_sys_7:
        MOV   R1, R2
        CALL  hos_fs_read
        JMP   _sys_ret
_sys_8:
        MOV   R1, R2
        CALL  hos_fs_write
        JMP   _sys_ret
_sys_9:
        CMPI  R2, 1
        JEQ   _sys_9_ok
        MOVI  R1, 0
        JMP   _sys_ret
_sys_9_ok:
        MOVI  R1, 1
        JMP   _sys_ret
_sys_ret:
        MOVI  R0, 0
        LOAD  R2, R0, 0xDF2
        LOAD  R3, R0, 0xDF3
        LOAD  R4, R0, 0xDF4
        LOAD  R6, R0, 0xDF6
        LOAD  R7, R0, 0xDF7
        LOAD  R8, R0, 0xDF8
        LOAD  R9, R0, 0xDF9
        LOAD  R10, R0, 0xDFA
        LOAD  R11, R0, 0xDFB
        LOAD  R12, R0, 0xDFC
        LOAD  R13, R0, 0xDFD
        LOAD  R14, R0, 0xDFE
        LOAD  R15, R0, 0xDFF
        LOAD  R0, R0, 0xDF0
        ERET

        .include "hos.hasm"

_user_prog_start:
{user_asm}
"""
    return list(assemble(harness_asm, base_dir=PROGRAMS_DIR))


def compile_and_execute_cells(
    source: str,
    *,
    is_hc_compat: bool = False,
    use_native_letter_opcodes: bool = True,
    reuse_registers: bool = True,
    use_hw_sticky_guard: bool = False,
    use_native_hdot: bool = False,
    run_rtl: bool = True,
    run_rtl_loader: bool = False,
    load_addr: int = DEFAULT_OVERLAY_LOAD_ADDR,
) -> EndToEndPipelineResult:
    """Run the complete end-to-end Hijaiyyah Cells pipeline on `.hcell` or `.hc` source."""
    src_bytes = len(source.encode("utf-8"))
    t0 = time.perf_counter()
    if is_hc_compat:
        tok_cnt = len(HCLexer(source).tokenize())
        graph = parse_hc_to_cell_ir(source)
    else:
        tok_cnt = len(tokenize_hcell(source))
        graph = parse_hcell(source)

    sem_report = SemanticAnalyzer().analyze(graph)
    backend = CellHISABackend(
        use_native_letter_opcodes=use_native_letter_opcodes,
        reuse_registers=reuse_registers,
        use_hw_sticky_guard=use_hw_sticky_guard,
        use_native_hdot=use_native_hdot,
    )
    compiled = backend.compile(graph)
    compile_ms = (time.perf_counter() - t0) * 1000.0

    eval_result = CellEvaluator(
        hardware_8bit_wrap=False, fail_on_guard_error=False
    ).evaluate(graph)
    hw_eval_result = CellEvaluator(
        hardware_8bit_wrap=True, fail_on_guard_error=False
    ).evaluate(graph)

    container = build_hpg1_container(compiled.assembly_text, PROGRAMS_DIR, load_addr)
    card = card_image(container)
    v_ok, v_reason = load_check(card, overlay=True)

    has_syscalls = compiled.syscalls_emitted > 0

    # Execute full program on HISAMachine (assembled at base 0)
    hvm = HISAMachine(MASTER_TABLE, hcheck_interval=0)
    _run_hvm_program(
        hvm,
        compiled.words,
        enable_hos_syscalls=has_syscalls,
        suppress_syscall_print=False,
        wrap_hreg_8bit=False,
    )

    # Execute full program on HISAMachine with 8-bit H-Reg wrapping
    hvm_hw8 = HISAMachine(MASTER_TABLE, hcheck_interval=0)
    _run_hvm_program(
        hvm_hw8,
        compiled.words,
        enable_hos_syscalls=has_syscalls,
        suppress_syscall_print=False,
        wrap_hreg_8bit=True,
    )

    # Execute compute-only program on HISAMachine (without PRINT)
    hvm_comp = HISAMachine(MASTER_TABLE, hcheck_interval=0)
    _run_hvm_program(
        hvm_comp,
        compiled.compute_only_words,
        enable_hos_syscalls=has_syscalls,
        suppress_syscall_print=True,
        wrap_hreg_8bit=False,
    )

    cost = build_cost_estimate(
        graph=graph,
        instruction_words=len(compiled.words),
        relocation_count=container[5],
        gpr_used=compiled.peak_gpr_used,
        hreg_used=compiled.peak_hreg_used,
        printed_values=eval_result.outputs,
    )

    rtl_meas: HCPUExecutionMeasurement | None = None
    status = EpistemicStatus.TESTED

    if run_rtl:
        sim = _get_parity_sim_binary()
        if sim is not None:
            rtl_full_words = (
                _build_rtl_syscall_harness_words(
                    compiled.assembly_text, suppress_syscall_print=False
                )
                if has_syscalls
                else compiled.words
            )
            rtl_comp_words = (
                _build_rtl_syscall_harness_words(
                    compiled.compute_only_assembly_text, suppress_syscall_print=True
                )
                if has_syscalls
                else compiled.compute_only_words
            )
            max_cyc = 25000
            full_rtl = _run_rtl_words(sim, rtl_full_words, max_cycles=max_cyc)
            comp_rtl = _run_rtl_words(sim, rtl_comp_words, max_cycles=max_cyc)
            loader_verdict = _run_rtl_4b_prime_card(card) if run_rtl_loader else None
            compute_cyc = int(comp_rtl["cycles"])
            total_cyc = int(full_rtl["cycles"])
            rtl_meas = HCPUExecutionMeasurement(
                halted=bool(full_rtl["halted"]),
                compute_cycles=compute_cyc,
                total_cycles=total_cyc,
                io_cycles=max(0, total_cyc - compute_cyc),
                flags=int(full_rtl["flags"]),
                gpr=dict(full_rtl["gpr"]),
                hreg=dict(full_rtl["hreg"]),
                printed_outputs=list(full_rtl["printed_outputs"]),
                rtl_4b_prime_verdict=loader_verdict,
            )
            status = EpistemicStatus.SIMULATED

    guard_flag_checked = compiled.guards_emitted > 0
    parity = (eval_result.outputs == list(hvm.output)) and v_ok
    hw_parity = (
        v_ok
        and (list(hvm_hw8.output) == hw_eval_result.outputs)
        and (
            not guard_flag_checked
            or (bool(hvm_hw8.regs.sr.guard_pass) == hw_eval_result.last_guard_passed)
        )
    )
    if rtl_meas is not None:
        hw_parity = (
            hw_parity
            and (rtl_meas.printed_outputs == hw_eval_result.outputs)
            and (
                not guard_flag_checked
                or (bool(rtl_meas.flags & 0x01) == hw_eval_result.last_guard_passed)
            )
            and rtl_meas.halted
        )
        parity = parity and (rtl_meas.printed_outputs == eval_result.outputs) and rtl_meas.halted
        if rtl_meas.rtl_4b_prime_verdict is not None:
            verdict_ok = rtl_meas.rtl_4b_prime_verdict == {
                "DONE": 1,
                "ANSWER": 1,
                "ABSENT": 0,
            }
            parity = parity and verdict_ok
            hw_parity = hw_parity and verdict_ok

    return EndToEndPipelineResult(
        source_bytes=src_bytes,
        token_count=tok_cnt,
        compile_time_ms=round(compile_ms, 3),
        graph=graph,
        semantic_report=sem_report,
        eval_result=eval_result,
        hw_eval_result=hw_eval_result,
        compiled=compiled,
        container_words=container,
        card_sectors=card,
        verify_4b_prime_ok=v_ok,
        verify_4b_prime_reason=v_reason,
        hvm_outputs=list(hvm.output),
        hvm_steps=hvm.cycle,
        hvm_compute_steps=hvm_comp.cycle,
        hvm_guard_pass=bool(hvm.regs.sr.guard_pass),
        hvm_hw_8bit_outputs=list(hvm_hw8.output),
        hvm_hw_8bit_guard_pass=bool(hvm_hw8.regs.sr.guard_pass),
        cost_estimate=cost,
        rtl_measurement=rtl_meas,
        three_way_parity=parity,
        hw_rtl_parity=hw_parity,
        epistemic_status=status,
    )


__all__ = [
    "DEFAULT_OVERLAY_LOAD_ADDR",
    "EndToEndPipelineResult",
    "HCPUExecutionMeasurement",
    "compile_and_execute_cells",
]
