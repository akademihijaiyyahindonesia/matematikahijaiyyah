"""
Tab: HCELL WORKBENCH — Hijaiyyah Cells → CellIR → 4-B′ → HPG1 v2
=================================================================
Redesigned scientific computing workbench for the native Hijaiyyah Cells
(`.hcell`) and `.hc` compatibility pipeline:
  - Top bar: HCELL WORKBENCH + status badge (`READY` / `PASS` / `FAULT`) +
    stage pills (`INPUT`, `CELLIR`, `VERIFY`, `HPG1`) + explicit controls
    (`Inspect Static`, `Execute E2E`, `Diagnostics`)
  - Left pane: Line-numbered SOURCE EDITOR (`HC / .hcell`) with syntax highlighting
    and non-executing sample selector
  - Right upper pane: `CellIR Inspector` with status pills (`Parsed`, `Semantic OK`,
    `Guard OK`) and internal sub-tabs (`Node Tree · Types · Proofs` Treeview &
    `4-B′ Verifier & H-ISA`)
  - Right lower pane: `HPG1 v2 Container` structured key-value card grid
    (`MAGIC`, `VERSION`, `WORDS`, `LOAD_ADDR`, `ENTRY`, `CHECKSUM32`)
  - Collapsible bottom drawer: `Diagnostics & Execution Trace` (can be opened or
    closed at any time)
"""

from __future__ import annotations

import re
import sys
import time
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ...cells.dataset_engine import DATASET_ID, UnicodePolicyError
from ...cells.hisa_backend import CellBackendError, CellHISABackend, CompiledHISAProgram
from ...cells.hpg1_bridge import DEFAULT_OVERLAY_LOAD_ADDR, PROGRAMS_DIR, compile_and_execute_cells
from ...cells.ir import CellIRGraph
from ...cells.lexer import HCellLexerError, tokenize_hcell
from ...cells.parser import HCellParseError, parse_hc_to_cell_ir, parse_hcell
from ...cells.semantic import CellSemanticError, SemanticAnalysisReport, SemanticAnalyzer
from ...language.lexer import Lexer as HCLexer
from ...vm import ControlFlowReport, verify_control_flow
from ..theme import THEME
from ..widgets import OutputWriter, make_text

_SCRIPTS_DIR = PROGRAMS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build_container import (  # type: ignore[import-not-found]  # noqa: E402, I001
    CHECKSUM_AT,
    HEADER_WORDS,
    build as build_hpg1_container,
    card_image,
    checksum32,
    load_check,
    relocate,
    table_record,
    verify_overlay,
)


# ══════════════════════════════════════════════════════════════════
#  SECTION 1 — PURE PIPELINE INSPECTION API (TESTABLE HEADLESSLY)
# ══════════════════════════════════════════════════════════════════


@dataclass
class HPG1PackageSummary:
    """Structured summary of an HPG1 v2 container and its K-8/K-10 CHECKSUM32."""

    magic: int
    version: int
    program_words: int
    load_addr: int
    entry_addr: int
    reloc_count: int
    stored_checksum32: int
    computed_checksum32: int
    checksum_valid: bool
    sector16_record: List[int]
    relocation_indices: List[int]
    container_words: List[int]
    relocated_words: List[int]
    loader_ok: bool
    loader_reason: str

    def card_fields(self) -> Dict[str, str]:
        """Formatted key-value strings for the HPG1 v2 Container UI grid."""
        return {
            "MAGIC": f"0x{self.magic:08X} ('HPG1')",
            "VERSION": f"{self.version}",
            "WORDS": f"{self.program_words}",
            "LOAD_ADDR": f"0x{self.load_addr:03X}",
            "ENTRY": f"0x{self.entry_addr:03X}",
            "CHECKSUM32": f"0x{self.stored_checksum32:08X}",
        }


@dataclass
class HCellPipelineInspection:
    """Complete stage-by-stage diagnostic report for `.hcell` → `CellIR` → `4-B′` → `HPG1 v2`."""

    ok: bool
    failed_stage: Optional[str] = None
    error_type: Optional[str] = None
    error_message: str = ""
    source_language: str = "hcell"
    source_bytes: int = 0
    source_lines: int = 0
    token_count: int = 0
    elapsed_ms: float = 0.0
    graph: Optional[CellIRGraph] = None
    semantic_report: Optional[SemanticAnalysisReport] = None
    compiled: Optional[CompiledHISAProgram] = None
    cf_report: Optional[ControlFlowReport] = None
    overlay_4b_ok: bool = False
    overlay_4b_reason: str = ""
    hpg1: Optional[HPG1PackageSummary] = None
    diagnostics: List[str] = field(default_factory=list)


def package_and_verify_hpg1(
    assembly_text: str,
    *,
    load_addr: int = DEFAULT_OVERLAY_LOAD_ADDR,
    tamper_word_index: Optional[int] = None,
    tamper_xor_mask: int = 0x1,
    override_relocated_words: Optional[Sequence[int]] = None,
) -> HPG1PackageSummary:
    """
    Build an HPG1 v2 container via `build_container.py`, optionally apply a
    diagnostic tamper or custom instruction stream, and run `load_check` + `verify_overlay`.
    """
    container = list(build_hpg1_container(assembly_text, PROGRAMS_DIR, load_addr))
    record = list(table_record(len(container)))

    if tamper_word_index is not None and 0 <= tamper_word_index < len(container):
        container[tamper_word_index] = (container[tamper_word_index] ^ tamper_xor_mask) & 0xFFFFFFFF

    computed_csum = int(checksum32(record, container))
    stored_csum = int(container[CHECKSUM_AT])
    csum_ok = computed_csum == stored_csum

    sectors = card_image(container, record=record)
    loader_ok, loader_reason = load_check(sectors, overlay=True)

    _, relocated = relocate(container)
    if override_relocated_words is not None:
        relocated = [int(w) & 0xFFFFFFFF for w in override_relocated_words]
        ov_ok, ov_reason = verify_overlay(relocated, container[3], container[4])
        if not ov_ok:
            loader_ok = False
            loader_reason = ov_reason

    reloc_cnt = int(container[5])
    reloc_indices = list(container[HEADER_WORDS : HEADER_WORDS + reloc_cnt])

    return HPG1PackageSummary(
        magic=int(container[0]),
        version=int(container[1]),
        program_words=int(container[2]),
        load_addr=int(container[3]),
        entry_addr=int(container[4]),
        reloc_count=reloc_cnt,
        stored_checksum32=stored_csum,
        computed_checksum32=computed_csum,
        checksum_valid=csum_ok,
        sector16_record=record,
        relocation_indices=reloc_indices,
        container_words=container,
        relocated_words=relocated,
        loader_ok=loader_ok,
        loader_reason=loader_reason,
    )


def inspect_hcell_pipeline(
    source: str,
    *,
    is_hc_compat: bool = False,
    use_native_letter_opcodes: bool = True,
    reuse_registers: bool = True,
    use_native_hdot: bool = False,
    load_addr: int = DEFAULT_OVERLAY_LOAD_ADDR,
    tamper_checksum: bool = False,
) -> HCellPipelineInspection:
    """
    Run the static compilation & verification pipeline without executing the program:
      Stage 1: Lexer & Parser (`.hcell` or `.hc` compat)
      Stage 2: `CellIR` & `SemanticAnalyzer` (Two-Layer G1–G4/T1–T2 + H* proof)
      Stage 3: `CellHISABackend` & `4-B′ Control Flow Verifier`
      Stage 4: `HPG1 v2` Container Packaging & `CHECKSUM32` Verification
    """
    t0 = time.perf_counter()
    src_bytes = len(source.encode("utf-8"))
    src_lines = source.count("\n") + 1 if source else 0
    lang = "hc_v1_compat" if is_hc_compat else "hcell"
    diags: List[str] = []

    # ── Stage 1: Lex & Parse ─────────────────────────────────────
    try:
        if is_hc_compat:
            tokens = HCLexer(source).tokenize()
            tok_cnt = len(tokens)
            graph = parse_hc_to_cell_ir(source)
        else:
            hcell_tokens = tokenize_hcell(source)
            tok_cnt = len(hcell_tokens)
            graph = parse_hcell(source)
        diags.append(
            f"[PASS] Stage 1 (INPUT): {tok_cnt} tokens → "
            f"{len(graph.nodes)} CellIR nodes ({len(graph.subroutines)} subroutines)."
        )
    except (UnicodePolicyError, HCellLexerError, HCellParseError) as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        msg = f"{type(exc).__name__}: {exc}"
        diags.append(f"[FAIL] Stage 1 (INPUT / Orthographic Policy): {msg}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_1_PARSE",
            error_type=type(exc).__name__,
            error_message=str(exc),
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            elapsed_ms=round(elapsed, 3),
            diagnostics=diags,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        msg = f"{type(exc).__name__}: {exc}"
        diags.append(f"[FAIL] Stage 1 (INPUT Parse Error): {msg}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_1_PARSE",
            error_type=type(exc).__name__,
            error_message=str(exc),
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            elapsed_ms=round(elapsed, 3),
            diagnostics=diags,
        )

    # ── Stage 2: CellIR Semantic Analysis & Two-Layer Proof ──────
    try:
        sem_report = SemanticAnalyzer().analyze(graph)
        diags.append(
            f"[PASS] Stage 2 (CELLIR): {sem_report.node_count} nodes validated; "
            f"guards discharged={sem_report.guards_discharged}, "
            f"runtime mandatory={sem_report.guards_mandatory_runtime}."
        )
        for warn in sem_report.overflow_warnings:
            diags.append(f"[WARN] Layer B 8-Bit Prefix Bound: {warn}")
    except CellSemanticError as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        diags.append(f"[FAIL] Stage 2 (CELLIR Semantic / Domain Error): {exc}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_2_SEMANTIC",
            error_type=type(exc).__name__,
            error_message=str(exc),
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            token_count=tok_cnt,
            elapsed_ms=round(elapsed, 3),
            graph=graph,
            diagnostics=diags,
        )

    # ── Stage 3: H-ISA Lowering & 4-B′ Control Flow Verification ─
    try:
        backend = CellHISABackend(
            use_native_letter_opcodes=use_native_letter_opcodes,
            reuse_registers=reuse_registers,
            use_native_hdot=use_native_hdot,
        )
        compiled = backend.compile(graph)
    except (CellBackendError, Exception) as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        diags.append(f"[FAIL] Stage 3 (VERIFY H-ISA Codegen Error): {exc}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_3_CODEGEN",
            error_type=type(exc).__name__,
            error_message=str(exc),
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            token_count=tok_cnt,
            elapsed_ms=round(elapsed, 3),
            graph=graph,
            semantic_report=sem_report,
            diagnostics=diags,
        )

    cf_report = verify_control_flow(compiled.words, entry_point=0, base=0)
    if not cf_report.valid:
        elapsed = (time.perf_counter() - t0) * 1000.0
        diags.append(f"[FAIL] Stage 3 (VERIFY 4-B′ Static Control Flow): {cf_report.reason}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_3_CONTROL_FLOW_4B",
            error_type="ControlFlowVerificationError",
            error_message=cf_report.reason,
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            token_count=tok_cnt,
            elapsed_ms=round(elapsed, 3),
            graph=graph,
            semantic_report=sem_report,
            compiled=compiled,
            cf_report=cf_report,
            diagnostics=diags,
        )

    # ── Stage 4: HPG1 v2 Packaging & Overlay Verifier ────────────
    try:
        tamper_idx = HEADER_WORDS if tamper_checksum else None
        hpg1 = package_and_verify_hpg1(
            compiled.assembly_text,
            load_addr=load_addr,
            tamper_word_index=tamper_idx,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        diags.append(f"[FAIL] Stage 4 (HPG1 v2 Packaging): {exc}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_4_HPG1_PACKAGE",
            error_type=type(exc).__name__,
            error_message=str(exc),
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            token_count=tok_cnt,
            elapsed_ms=round(elapsed, 3),
            graph=graph,
            semantic_report=sem_report,
            compiled=compiled,
            cf_report=cf_report,
            diagnostics=diags,
        )

    ov_ok, ov_reason = verify_overlay(
        hpg1.relocated_words, hpg1.load_addr, hpg1.entry_addr
    )
    elapsed = (time.perf_counter() - t0) * 1000.0

    if not ov_ok:
        diags.append(f"[FAIL] Stage 3 (VERIFY 4-B′ Overlay Verifier): {ov_reason}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_3_CONTROL_FLOW_4B",
            error_type="OverlayVerificationError",
            error_message=ov_reason,
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            token_count=tok_cnt,
            elapsed_ms=round(elapsed, 3),
            graph=graph,
            semantic_report=sem_report,
            compiled=compiled,
            cf_report=cf_report,
            overlay_4b_ok=False,
            overlay_4b_reason=ov_reason,
            hpg1=hpg1,
            diagnostics=diags,
        )

    diags.append(
        f"[PASS] Stage 3 (VERIFY 4-B′): CFG valid ({cf_report.words} words) & "
        f"Overlay 4-B′ status='{ov_reason}'."
    )

    if not hpg1.checksum_valid or not hpg1.loader_ok:
        err_reason = (
            f"CHECKSUM32 mismatch (stored=0x{hpg1.stored_checksum32:08X}, "
            f"computed=0x{hpg1.computed_checksum32:08X})"
            if not hpg1.checksum_valid
            else hpg1.loader_reason
        )
        diags.append(f"[FAIL] Stage 4 (HPG1 v2 Integrity): {err_reason}")
        return HCellPipelineInspection(
            ok=False,
            failed_stage="STAGE_4_HPG1_CHECKSUM",
            error_type="HPG1IntegrityError",
            error_message=err_reason,
            source_language=lang,
            source_bytes=src_bytes,
            source_lines=src_lines,
            token_count=tok_cnt,
            elapsed_ms=round(elapsed, 3),
            graph=graph,
            semantic_report=sem_report,
            compiled=compiled,
            cf_report=cf_report,
            overlay_4b_ok=ov_ok,
            overlay_4b_reason=ov_reason,
            hpg1=hpg1,
            diagnostics=diags,
        )

    diags.append(
        f"[PASS] Stage 4 (HPG1 v2): MAGIC=0x{hpg1.magic:08X} ('HPG1'), "
        f"VERSION={hpg1.version}, WORDS={hpg1.program_words}, RELOC={hpg1.reloc_count}, "
        f"CHECKSUM32=0x{hpg1.stored_checksum32:08X} (VERIFIED)."
    )

    return HCellPipelineInspection(
        ok=True,
        failed_stage=None,
        source_language=lang,
        source_bytes=src_bytes,
        source_lines=src_lines,
        token_count=tok_cnt,
        elapsed_ms=round(elapsed, 3),
        graph=graph,
        semantic_report=sem_report,
        compiled=compiled,
        cf_report=cf_report,
        overlay_4b_ok=ov_ok,
        overlay_4b_reason=ov_reason,
        hpg1=hpg1,
        diagnostics=diags,
    )


def verify_raw_hisa_control_flow(
    words: Sequence[int],
    *,
    load_addr: int = DEFAULT_OVERLAY_LOAD_ADDR,
) -> Dict[str, Any]:
    """
    Run both `vm.verify_control_flow` (at base 0) and `build_container.verify_overlay`
    (relocated at `load_addr`) on a raw H-ISA instruction stream.
    """
    cf = verify_control_flow(words, entry_point=0, base=0)
    ov_ok, ov_reason = verify_overlay(list(words), load_addr, load_addr)
    return {
        "vm_control_flow_valid": cf.valid,
        "vm_control_flow_reason": cf.reason,
        "vm_first_bad_word": cf.first_bad,
        "overlay_4b_ok": ov_ok,
        "overlay_4b_reason": ov_reason,
        "all_valid": cf.valid and ov_ok,
    }


# ══════════════════════════════════════════════════════════════════
#  SECTION 2 — SAMPLE PROGRAMS FOR INTERACTIVE INSPECTION
# ══════════════════════════════════════════════════════════════════

HCELL_EXAMPLES: Dict[str, str] = {
    "1. بسم Benchmark (.hcell)": """\
بسم := ب + س + م;
⊢ بسم;
↦ Θ̂(بسم);
↦ U(بسم);
↦ ρ(بسم);
↦ ‖بسم‖²;
↦ d₂²(ب, م);
""",
    "2. Subroutine ƒ + Loop ↻ + Branch ?": """\
ƒ @وزن(@س, @ص) := (@س * ٢) + @ص;
عداد := ٠;
مجموع := ٠;
حد := Θ̂(ب + س + م);
↻ (عداد < ٣) {
    مجموع := مجموع + @وزن(حد, عداد);
    عداد := عداد + ١;
}
? (مجموع == ٦٣) {
    ↦ مجموع;
} : {
    ↦ ٠;
}
↦ عداد;
""",
    "3. All 28 Letters Native Opcodes (0xE0–0xFB)": """\
ابجد := ⟪ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن و هـ ي⟫;
⊢ ابجد;
↦ Θ̂(ابجد);
↦ U(ابجد);
↦ ρ(ابجد);
↦ ‖ابجد‖²;
""",
    "4. Diagnostic: Forbidden Lookalike (ة)": """\
// Uses Ta Marbuthah 'ة' (U+0629) outside canonical H_28 -> Stage 1 Policy Error
طاقة := ب + س;
↦ Θ̂(طاقة);
""",
    "5. Diagnostic: Semantic Type Error (↦ Hybit)": """\
// EMIT_OUTPUT (↦) requires a SCALAR, not a raw 18D HYBIT -> Stage 2 Semantic Error
بسم := ب + س + م;
↦ بسم;
""",
}

HPG1_CARD_KEYS: Tuple[str, ...] = (
    "MAGIC",
    "VERSION",
    "WORDS",
    "LOAD_ADDR",
    "ENTRY",
    "CHECKSUM32",
)


# ══════════════════════════════════════════════════════════════════
#  SECTION 3 — REDESIGNED HCELL WORKBENCH (TKINTER)
# ══════════════════════════════════════════════════════════════════


class HCellTab:
    """
    HCELL WORKBENCH — Scientific Computing Workbench for `.hcell` / `CellIR` / `4-B′` / `HPG1 v2`.

    Hierarchy:
      - Header bar: `HCELL WORKBENCH` + status badge (`READY`) + stage pills
        (`INPUT`, `CELLIR`, `VERIFY`, `HPG1`) + explicit action buttons
        (`Inspect Static`, `Execute E2E`, `Diagnostics`)
      - Left pane: Line-numbered `SOURCE EDITOR` (`HC / .hcell`) with syntax highlighting
      - Right upper pane: `CellIR Inspector` (`Parsed`, `Semantic OK`, `Guard OK`) +
        tabbed node tree (`Treeview`) & `4-B′` / H-ISA view
      - Right lower pane: `HPG1 v2 Container` structured 6-field card grid
      - Collapsible bottom drawer: `Diagnostics` (can be toggled open/closed)
    """

    def __init__(self, notebook: ttk.Notebook, root: tk.Tk) -> None:
        self._root = root
        self._tab = ttk.Frame(notebook)
        notebook.add(self._tab, text="  ◈ .hcell / HPG1  ")

        self._hc_compat_var = tk.BooleanVar(value=False)
        self._native_ops_var = tk.BooleanVar(value=True)
        self._native_hdot_var = tk.BooleanVar(value=False)
        self._tamper_csum_var = tk.BooleanVar(value=False)
        self._sample_var = tk.StringVar(value="1. بسم Benchmark (.hcell)")

        self._status_badge: Optional[tk.Label] = None
        self._stage_pills: Dict[str, tk.Label] = {}
        self._ir_badges: Dict[str, tk.Label] = {}
        self._hpg1_value_labels: Dict[str, tk.Label] = {}

        self._line_gutter: Optional[tk.Text] = None
        self._editor: Optional[tk.Text] = None
        self._ir_tree: Optional[ttk.Treeview] = None
        self._cf_out: Optional[OutputWriter] = None

        self._diag_frame: Optional[tk.Frame] = None
        self._diag_visible: bool = False
        self._diag_out: Optional[OutputWriter] = None

        self._build()

    def _build(self) -> None:
        outer = tk.Frame(self._tab, bg=THEME.bg, padx=16, pady=12)
        outer.pack(fill=tk.BOTH, expand=True)

        # ── 1. Top Workbench Header & Stage Pills ────────────────
        top_bar = tk.Frame(
            outer,
            bg=THEME.surface,
            padx=14,
            pady=10,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        top_bar.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            top_bar,
            text="HCELL WORKBENCH",
            font=("Inter", 13, "bold"),
            fg=THEME.fg,
            bg=THEME.surface,
        ).pack(side=tk.LEFT)

        self._status_badge = tk.Label(
            top_bar,
            text=" READY ",
            font=("JetBrains Mono", 9, "bold"),
            fg=THEME.highlight,
            bg=THEME.surface_alt,
            padx=8,
            pady=3,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        self._status_badge.pack(side=tk.LEFT, padx=(10, 18))

        # 4 Stage Pills: INPUT -> CELLIR -> VERIFY -> HPG1
        pills_frame = tk.Frame(top_bar, bg=THEME.surface)
        pills_frame.pack(side=tk.LEFT)

        for idx, (stage_key, label) in enumerate(
            [
                ("INPUT", "INPUT"),
                ("CELLIR", "CELLIR"),
                ("VERIFY", "VERIFY"),
                ("HPG1", "HPG1"),
            ]
        ):
            pill = tk.Label(
                pills_frame,
                text=f" {label} ",
                font=("JetBrains Mono", 9, "bold"),
                fg=THEME.dim_fg,
                bg=THEME.surface_alt,
                padx=8,
                pady=3,
                highlightbackground=THEME.border,
                highlightthickness=1,
            )
            pill.pack(side=tk.LEFT, padx=2)
            self._stage_pills[stage_key] = pill
            if idx < 3:
                tk.Label(
                    pills_frame,
                    text="›",
                    font=("JetBrains Mono", 11, "bold"),
                    fg=THEME.dim_fg,
                    bg=THEME.surface,
                ).pack(side=tk.LEFT, padx=2)

        # Right-aligned Action Buttons
        actions = tk.Frame(top_bar, bg=THEME.surface)
        actions.pack(side=tk.RIGHT)

        ttk.Button(
            actions,
            text="Inspect Static",
            style="Accent.TButton",
            command=self._run_inspect,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            actions,
            text="Execute E2E",
            command=self._run_execute,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            actions,
            text="Diagnostics ▾",
            command=self._toggle_diagnostics,
        ).pack(side=tk.LEFT, padx=4)

        # ── 2. Secondary Options Strip ───────────────────────────
        opt_bar = tk.Frame(outer, bg=THEME.bg)
        opt_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            opt_bar,
            text="Sample:",
            font=("Inter", 9, "bold"),
            fg=THEME.dim_fg,
            bg=THEME.bg,
        ).pack(side=tk.LEFT)

        sample_combo = ttk.Combobox(
            opt_bar,
            textvariable=self._sample_var,
            values=list(HCELL_EXAMPLES.keys()),
            width=36,
            state="readonly",
        )
        sample_combo.pack(side=tk.LEFT, padx=(6, 10))
        sample_combo.bind(
            "<<ComboboxSelected>>",
            lambda _: self._load_example(self._sample_var.get()),
        )

        ttk.Button(opt_bar, text="Open", command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(opt_bar, text="Save", command=self._save_file).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            opt_bar,
            text="HC v1.0 Compat",
            variable=self._hc_compat_var,
        ).pack(side=tk.RIGHT, padx=6)

        ttk.Checkbutton(
            opt_bar,
            text="Simulate CHECKSUM32 Tamper",
            variable=self._tamper_csum_var,
        ).pack(side=tk.RIGHT, padx=6)

        ttk.Checkbutton(
            opt_bar,
            text="HDOT (0x52)",
            variable=self._native_hdot_var,
        ).pack(side=tk.RIGHT, padx=6)

        ttk.Checkbutton(
            opt_bar,
            text="0xE0–0xFB Letter Ops",
            variable=self._native_ops_var,
        ).pack(side=tk.RIGHT, padx=6)

        # ── 3. Main Split Workspace: Source Editor (Left) & Inspectors (Right) ─
        workspace = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        workspace.pack(fill=tk.BOTH, expand=True)

        # Left Pane: Line-Numbered SOURCE EDITOR
        left_card = tk.Frame(
            workspace,
            bg=THEME.surface,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        workspace.add(left_card, weight=5)
        self._build_source_editor(left_card)

        # Right Pane: Stacked CellIR Inspector (top) + HPG1 v2 Container (bottom)
        right_col = tk.Frame(workspace, bg=THEME.bg)
        workspace.add(right_col, weight=7)

        self._build_cellir_inspector(right_col)
        self._build_hpg1_card_grid(right_col)

        # ── 4. Collapsible Diagnostics Drawer (Bottom) ───────────
        self._diag_frame = tk.Frame(
            outer,
            bg=THEME.surface,
            highlightbackground=THEME.border,
            highlightthickness=1,
            height=170,
        )
        diag_header = tk.Frame(self._diag_frame, bg=THEME.surface_alt, padx=10, pady=4)
        diag_header.pack(fill=tk.X)
        tk.Label(
            diag_header,
            text="DIAGNOSTICS & EXECUTION TRACE",
            font=("Inter", 9, "bold"),
            fg=THEME.highlight,
            bg=THEME.surface_alt,
        ).pack(side=tk.LEFT)
        tk.Button(
            diag_header,
            text="✕ Close",
            font=("JetBrains Mono", 8),
            fg=THEME.dim_fg,
            bg=THEME.surface_alt,
            bd=0,
            command=self._toggle_diagnostics,
        ).pack(side=tk.RIGHT)

        diag_body = tk.Frame(self._diag_frame, bg=THEME.text_bg)
        diag_body.pack(fill=tk.BOTH, expand=True)
        diag_text, _ = make_text(diag_body, font=THEME.font_mono_sm, wrap=tk.NONE)
        self._diag_out = OutputWriter(diag_text)
        self._diag_out.add_tags(
            {
                "header": {"foreground": THEME.highlight, "font": (*THEME.font_mono_sm, "bold")},
                "pass": {"foreground": THEME.success, "font": (*THEME.font_mono_sm, "bold")},
                "error": {"foreground": THEME.error, "font": (*THEME.font_mono_sm, "bold")},
                "field": {"foreground": THEME.gold},
                "value": {"foreground": THEME.fg},
                "dim": {"foreground": THEME.dim_fg},
            }
        )

        # Load initial sample passively (NO auto-execution)
        self._load_example("1. بسم Benchmark (.hcell)")

    def _build_source_editor(self, parent: tk.Frame) -> None:
        hdr = tk.Frame(parent, bg=THEME.surface_alt, padx=12, pady=8)
        hdr.pack(fill=tk.X)

        tk.Label(
            hdr,
            text="SOURCE EDITOR",
            font=("Inter", 9, "bold"),
            fg=THEME.dim_fg,
            bg=THEME.surface_alt,
        ).pack(side=tk.LEFT)

        tk.Label(
            hdr,
            text="HC / .hcell",
            font=("JetBrains Mono", 9, "bold"),
            fg=THEME.gold,
            bg=THEME.surface_alt,
        ).pack(side=tk.RIGHT)

        tk.Frame(parent, bg=THEME.border, height=1).pack(fill=tk.X)

        body = tk.Frame(parent, bg=THEME.text_bg)
        body.pack(fill=tk.BOTH, expand=True)

        self._line_gutter = tk.Text(
            body,
            width=4,
            padx=6,
            pady=10,
            font=THEME.font_mono_lg,
            bg=THEME.surface_alt,
            fg=THEME.dim_fg,
            bd=0,
            state=tk.DISABLED,
            takefocus=0,
        )
        self._line_gutter.pack(side=tk.LEFT, fill=tk.Y)

        self._editor = tk.Text(
            body,
            font=THEME.font_mono_lg,
            bg=THEME.text_bg,
            fg=THEME.fg,
            insertbackground=THEME.highlight,
            selectbackground=THEME.surface,
            wrap=tk.NONE,
            undo=True,
            bd=0,
            padx=10,
            pady=10,
        )
        y_scroll = ttk.Scrollbar(body, command=self._on_editor_scroll)
        self._editor.configure(yscrollcommand=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Syntax highlight tags
        self._editor.tag_configure("operator", foreground=THEME.highlight)
        self._editor.tag_configure("number", foreground=THEME.gold)
        self._editor.tag_configure("comment", foreground=THEME.dim_fg)

        self._editor.bind("<KeyRelease>", lambda _: self._refresh_editor_decorations())

    def _on_editor_scroll(self, *args: Any) -> None:
        if self._editor is not None:
            self._editor.yview(*args)
        if self._line_gutter is not None:
            self._line_gutter.yview(*args)

    def _refresh_editor_decorations(self) -> None:
        if self._editor is None or self._line_gutter is None:
            return
        content = self._editor.get("1.0", "end-1c")
        line_count = max(1, content.count("\n") + 1)
        gutter_text = "\n".join(f"{i:02d}" for i in range(1, line_count + 1))

        self._line_gutter.config(state=tk.NORMAL)
        self._line_gutter.delete("1.0", tk.END)
        self._line_gutter.insert("1.0", gutter_text)
        self._line_gutter.config(state=tk.DISABLED)

        # Lightweight syntax highlighting
        for tag in ("operator", "number", "comment"):
            self._editor.tag_remove(tag, "1.0", tk.END)

        for line_idx, line in enumerate(content.splitlines(), 1):
            if "//" in line:
                col = line.index("//")
                self._editor.tag_add("comment", f"{line_idx}.{col}", f"{line_idx}.end")
            for m in re.finditer(r"(:=|⊢|↦|↻|\?|ƒ|⟪|⟫|Θ̂|d₂²|‖|⏣|⛁|§)", line):
                self._editor.tag_add(
                    "operator", f"{line_idx}.{m.start()}", f"{line_idx}.{m.end()}"
                )
            for m in re.finditer(r"[0-9٠-٩]+", line):
                self._editor.tag_add(
                    "number", f"{line_idx}.{m.start()}", f"{line_idx}.{m.end()}"
                )

    def _build_cellir_inspector(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            bg=THEME.surface,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        card.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))

        hdr = tk.Frame(card, bg=THEME.surface_alt, padx=12, pady=8)
        hdr.pack(fill=tk.X)

        tk.Label(
            hdr,
            text="CellIR Inspector",
            font=("Inter", 10, "bold"),
            fg=THEME.fg,
            bg=THEME.surface_alt,
        ).pack(side=tk.LEFT)

        tk.Label(
            hdr,
            text="Node tree · Types · Proofs",
            font=("JetBrains Mono", 9),
            fg=THEME.dim_fg,
            bg=THEME.surface_alt,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Status pills: Parsed | Semantic OK | Guard OK
        badges_box = tk.Frame(hdr, bg=THEME.surface_alt)
        badges_box.pack(side=tk.RIGHT)
        for key, text in [
            ("parsed", "Parsed"),
            ("semantic", "Semantic OK"),
            ("guard", "Guard OK"),
        ]:
            lbl = tk.Label(
                badges_box,
                text=f" {text} ",
                font=("JetBrains Mono", 8, "bold"),
                fg=THEME.dim_fg,
                bg=THEME.surface,
                padx=6,
                pady=2,
            )
            lbl.pack(side=tk.LEFT, padx=3)
            self._ir_badges[key] = lbl

        tk.Frame(card, bg=THEME.border, height=1).pack(fill=tk.X)

        # Internal Notebook: Tab 1 = Node Tree, Tab 2 = 4-B' Verifier & H-ISA
        sub_nb = ttk.Notebook(card)
        sub_nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tree_frame = ttk.Frame(sub_nb)
        sub_nb.add(tree_frame, text="  Node Tree · Types · Proofs  ")

        cols = ("cell_id", "op", "type", "layer_a", "layer_b", "glyphs")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=7)
        tree.heading("cell_id", text="Cell ID")
        tree.heading("op", text="Operation")
        tree.heading("type", text="Type")
        tree.heading("layer_a", text="In H (G1–T2)")
        tree.heading("layer_b", text="8-Bit Safe")
        tree.heading("glyphs", text="Source Glyphs")

        tree.column("cell_id", width=80, anchor=tk.W)
        tree.column("op", width=130, anchor=tk.W)
        tree.column("type", width=75, anchor=tk.CENTER)
        tree.column("layer_a", width=95, anchor=tk.CENTER)
        tree.column("layer_b", width=85, anchor=tk.CENTER)
        tree.column("glyphs", width=180, anchor=tk.W)

        t_scroll = ttk.Scrollbar(tree_frame, command=tree.yview)
        tree.configure(yscrollcommand=t_scroll.set)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        self._ir_tree = tree

        cf_frame = ttk.Frame(sub_nb)
        sub_nb.add(cf_frame, text="  4-B′ Verifier & H-ISA Assembly  ")
        cf_text, _ = make_text(cf_frame, font=THEME.font_mono_sm, wrap=tk.NONE)
        self._cf_out = OutputWriter(cf_text)
        self._cf_out.add_tags(
            {
                "header": {"foreground": THEME.highlight, "font": (*THEME.font_mono_sm, "bold")},
                "pass": {"foreground": THEME.success, "font": (*THEME.font_mono_sm, "bold")},
                "error": {"foreground": THEME.error, "font": (*THEME.font_mono_sm, "bold")},
                "value": {"foreground": THEME.gold},
                "dim": {"foreground": THEME.dim_fg},
            }
        )

    def _build_hpg1_card_grid(self, parent: tk.Frame) -> None:
        card = tk.Frame(
            parent,
            bg=THEME.surface,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        card.pack(fill=tk.X, padx=(8, 0), pady=(0, 0))

        hdr = tk.Frame(card, bg=THEME.surface_alt, padx=12, pady=8)
        hdr.pack(fill=tk.X)

        tk.Label(
            hdr,
            text="HPG1 v2 Container",
            font=("Inter", 10, "bold"),
            fg=THEME.fg,
            bg=THEME.surface_alt,
        ).pack(side=tk.LEFT)

        tk.Label(
            hdr,
            text=f"Dataset Seal: {DATASET_ID}",
            font=("JetBrains Mono", 8),
            fg=THEME.dim_fg,
            bg=THEME.surface_alt,
        ).pack(side=tk.RIGHT)

        tk.Frame(card, bg=THEME.border, height=1).pack(fill=tk.X)

        grid = tk.Frame(card, bg=THEME.surface, padx=12, pady=10)
        grid.pack(fill=tk.X)

        for idx, key in enumerate(HPG1_CARD_KEYS):
            r, c = divmod(idx, 3)
            cell = tk.Frame(
                grid,
                bg=THEME.surface_alt,
                padx=12,
                pady=8,
                highlightbackground=THEME.border,
                highlightthickness=1,
            )
            cell.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            grid.grid_columnconfigure(c, weight=1)

            tk.Label(
                cell,
                text=key,
                font=("JetBrains Mono", 8, "bold"),
                fg=THEME.dim_fg,
                bg=THEME.surface_alt,
            ).pack(anchor=tk.W)

            val_lbl = tk.Label(
                cell,
                text="—",
                font=("JetBrains Mono", 11, "bold"),
                fg=THEME.gold if key == "CHECKSUM32" else THEME.fg,
                bg=THEME.surface_alt,
            )
            val_lbl.pack(anchor=tk.W, pady=(3, 0))
            self._hpg1_value_labels[key] = val_lbl

    # ── Interactive State Helpers ────────────────────────────────

    def _toggle_diagnostics(self) -> None:
        if self._diag_frame is None:
            return
        if self._diag_visible:
            self._diag_frame.pack_forget()
            self._diag_visible = False
        else:
            self._diag_frame.pack(fill=tk.X, pady=(8, 0))
            self._diag_visible = True

    def _open_diagnostics_if_closed(self) -> None:
        if not self._diag_visible:
            self._toggle_diagnostics()

    def _reset_indicators(self) -> None:
        if self._status_badge is not None:
            self._status_badge.configure(text=" READY ", fg=THEME.highlight)
        for pill in self._stage_pills.values():
            pill.configure(fg=THEME.dim_fg, bg=THEME.surface_alt)
        for badge in self._ir_badges.values():
            badge.configure(fg=THEME.dim_fg, bg=THEME.surface)
        for val_lbl in self._hpg1_value_labels.values():
            val_lbl.configure(text="—", fg=THEME.dim_fg)
        if self._ir_tree is not None:
            for item in self._ir_tree.get_children():
                self._ir_tree.delete(item)

    def _load_example(self, name: str) -> None:
        """Load sample text into editor WITHOUT executing or compiling automatically."""
        if self._editor is None:
            return
        src = HCELL_EXAMPLES.get(name, "")
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", src)
        self._refresh_editor_decorations()
        self._reset_indicators()

        if self._diag_out is not None:
            self._diag_out.clear()
            self._diag_out.writeln("HCELL WORKBENCH — IDLE (NO AUTO-EXECUTION)", "header")
            self._diag_out.writeln(f"  Loaded sample: {name}", "value")
            self._diag_out.writeln(
                "  Press 'Inspect Static' to validate .hcell → CellIR → 4-B′ → HPG1 v2.", "dim"
            )

    def _open_file(self) -> None:
        if self._editor is None:
            return
        path = filedialog.askopenfilename(
            filetypes=[("Hijaiyyah Cells", "*.hcell"), ("HC Source", "*.hc"), ("All Files", "*.*")]
        )
        if not path:
            return
        content = Path(path).read_text(encoding="utf-8")
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", content)
        self._hc_compat_var.set(path.endswith(".hc"))
        self._refresh_editor_decorations()
        self._reset_indicators()

    def _save_file(self) -> None:
        if self._editor is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".hcell",
            filetypes=[("Hijaiyyah Cells", "*.hcell"), ("HC Source", "*.hc"), ("All Files", "*.*")],
        )
        if path:
            Path(path).write_text(self._editor.get("1.0", tk.END), encoding="utf-8")

    def _run_inspect(self) -> None:
        if self._editor is None:
            return
        src = self._editor.get("1.0", tk.END).strip()
        res = inspect_hcell_pipeline(
            src,
            is_hc_compat=self._hc_compat_var.get(),
            use_native_letter_opcodes=self._native_ops_var.get(),
            use_native_hdot=self._native_hdot_var.get(),
            tamper_checksum=self._tamper_csum_var.get(),
        )
        self._render_inspection(res)
        if not res.ok:
            self._open_diagnostics_if_closed()

    def _run_execute(self) -> None:
        if self._editor is None:
            return
        src = self._editor.get("1.0", tk.END).strip()
        res = inspect_hcell_pipeline(
            src,
            is_hc_compat=self._hc_compat_var.get(),
            use_native_letter_opcodes=self._native_ops_var.get(),
            use_native_hdot=self._native_hdot_var.get(),
            tamper_checksum=self._tamper_csum_var.get(),
        )
        self._render_inspection(res)
        self._open_diagnostics_if_closed()
        if not res.ok or self._diag_out is None:
            return

        try:
            e2e = compile_and_execute_cells(
                src,
                is_hc_compat=self._hc_compat_var.get(),
                use_native_letter_opcodes=self._native_ops_var.get(),
                use_native_hdot=self._native_hdot_var.get(),
                run_rtl=False,
                run_rtl_loader=False,
            )
            self._diag_out.writeln()
            self._diag_out.writeln("EXPLICIT EXECUTION TRACE (CellEvaluator + HVM)", "header")
            self._diag_out.writeln(f"  Exact N₀¹⁸ Outputs:   {e2e.eval_result.outputs}", "pass")
            self._diag_out.writeln(f"  HW 8-Bit Outputs:     {e2e.hw_eval_result.outputs}", "value")
            self._diag_out.writeln(f"  HVM Outputs:          {e2e.hvm_outputs}", "value")
            self._diag_out.writeln(
                f"  HVM Steps (Compute):  {e2e.hvm_steps} total ({e2e.hvm_compute_steps} compute)",
                "dim",
            )
            self._diag_out.writeln(
                f"  Guard Flag (SR.G):    {e2e.hvm_guard_pass} "
                f"(8-bit HW model: {e2e.hvm_hw_8bit_guard_pass})",
                "pass" if e2e.hvm_guard_pass else "error",
            )
        except Exception as exc:
            self._diag_out.writeln(f"\n[EXECUTION ERROR] {type(exc).__name__}: {exc}", "error")

    def _render_inspection(self, res: HCellPipelineInspection) -> None:
        self._reset_indicators()

        s1_ok = res.failed_stage != "STAGE_1_PARSE"
        s2_ok = s1_ok and res.failed_stage != "STAGE_2_SEMANTIC"
        s3_ok = s2_ok and res.failed_stage not in ("STAGE_3_CODEGEN", "STAGE_3_CONTROL_FLOW_4B")
        s4_ok = res.ok

        for key, passed, reached in [
            ("INPUT", s1_ok, True),
            ("CELLIR", s2_ok, s1_ok),
            ("VERIFY", s3_ok, s2_ok),
            ("HPG1", s4_ok, s3_ok),
        ]:
            pill = self._stage_pills.get(key)
            if pill is not None and reached:
                pill.configure(fg=THEME.success if passed else THEME.error)

        if self._status_badge is not None:
            if res.ok:
                self._status_badge.configure(text=" VERIFIED ", fg=THEME.success)
            else:
                self._status_badge.configure(text=" FAULT ", fg=THEME.error)

        # Update CellIR Inspector badges & Treeview
        if s1_ok and "parsed" in self._ir_badges:
            self._ir_badges["parsed"].configure(fg=THEME.success)
        if s2_ok and "semantic" in self._ir_badges:
            self._ir_badges["semantic"].configure(fg=THEME.success)
        if s2_ok and res.semantic_report is not None and "guard" in self._ir_badges:
            self._ir_badges["guard"].configure(
                fg=THEME.success if res.semantic_report.valid else THEME.error
            )

        if self._ir_tree is not None and res.graph is not None:
            for cid, node in res.graph.nodes.items():
                self._ir_tree.insert(
                    "",
                    tk.END,
                    values=(
                        cid,
                        node.op.value,
                        node.output_type.value,
                        "PASS" if node.proven_in_H else "DYNAMIC",
                        "SAFE" if node.hardware_8bit_safe else "RUNTIME",
                        node.source_glyphs,
                    ),
                )

        # Update 4-B' Verifier & H-ISA sub-tab
        if self._cf_out is not None:
            self._cf_out.clear()
            if res.compiled is None:
                self._cf_out.writeln("H-ISA codegen not available.", "error")
            else:
                c = res.compiled
                self._cf_out.writeln(
                    f"Words: {len(c.words)} ({len(c.compute_only_words)} compute)  ·  "
                    f"GPR: {c.peak_gpr_used}/15  ·  H-Reg: {c.peak_hreg_used}/16  ·  "
                    f"Letter Ops: {c.native_letter_opcodes_emitted}",
                    "value",
                )
                self._cf_out.writeln(
                    f"Overlay 4-B′ Verdict: {'PASS ✓' if res.overlay_4b_ok else 'FAIL ✗'} "
                    f"({res.overlay_4b_reason})",
                    "pass" if res.overlay_4b_ok else "error",
                )
                self._cf_out.writeln("─" * 58, "dim")
                for line in c.assembly_lines:
                    self._cf_out.writeln(line, "dim")

        # Update HPG1 v2 Container Card Grid
        if res.hpg1 is not None:
            fields = res.hpg1.card_fields()
            for k, val_str in fields.items():
                lbl = self._hpg1_value_labels.get(k)
                if lbl is not None:
                    color = (
                        (THEME.success if res.hpg1.checksum_valid else THEME.error)
                        if k == "CHECKSUM32"
                        else THEME.fg
                    )
                    lbl.configure(text=val_str, fg=color)

        # Update Diagnostics drawer
        if self._diag_out is not None:
            self._diag_out.clear()
            self._diag_out.writeln(
                f"STATIC PIPELINE DIAGNOSTICS ({res.elapsed_ms:.2f} ms)", "header"
            )
            for d in res.diagnostics:
                tag = (
                    "pass"
                    if d.startswith("[PASS]")
                    else ("error" if d.startswith("[FAIL]") else "field")
                )
                self._diag_out.writeln(f"  {d}", tag)
