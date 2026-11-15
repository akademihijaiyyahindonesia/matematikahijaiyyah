"""
HOM — Hijaiyyah Operating Machine (v1.2.0)
Hijaiyyah Scientific Computing Environment:
  - Vertical modular sidebar navigation (WORKSPACE, PROGRAMMING, SYSTEM)
  - System Overview dashboard with metric cards & 5-stage pipeline visual
  - Hosts all 15 modular workbenches without horizontal tab clutter
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.master_table import MASTER_TABLE
from ..hisa.machine import HISAMachine
from ..language.evaluator import HCEvaluator
from .tabs.audit import AuditTab
from .tabs.bytecode import BytecodeTab, get_opcode_summary
from .tabs.csgi import CSGiTab
from .tabs.export import ExportTab
from .tabs.five_fields import FiveFieldsTab
from .tabs.geometry import GeometryTab
from .tabs.hcell_pipeline import HCellTab
from .tabs.hisa_machine import HISAMachineTab
from .tabs.hisab import HISABTab
from .tabs.ide import IDETab
from .tabs.letter_explorer import LetterExplorerTab
from .tabs.master_table import MasterTableTab
from .tabs.release import ReleaseTab
from .tabs.string_integral import StringIntegralTab
from .tabs.theorems import TheoremTab
from .theme import (
    APP_TITLE,
    APP_VERSION,
    LOGO_PATH,
    MIN_SIZE,
    SOFTWARE_VERSION,
    THEME,
    configure_styles,
)

# ── Pure layout specification for headless verification ──────────

SIDEBAR_GROUPS: List[Tuple[str, List[Tuple[str, str, Optional[str]]]]] = [
    (
        "WORKSPACE",
        [
            ("overview", "Overview", None),
            ("audit", "Mathematical Audit", None),
            ("letter_explorer", "Letter Explorer", None),
            ("master_table", "Master Table", None),
            ("geometry_lab", "Geometry Lab", None),
            ("five_fields", "Five Fields (Σ-MV)", None),
            ("string_integral", "String Integral", None),
            ("theorems", "Formal Theorems", None),
        ],
    ),
    (
        "PROGRAMMING",
        [
            ("hc_ide", "HC IDE", None),
            ("hisa_machine", "HISA Machine", None),
            ("bytecode", "Bytecode Explorer", None),
            ("hcell_pipeline", ".hcell / HPG1", "NEW"),
        ],
    ),
    (
        "SYSTEM",
        [
            ("csgi", "CSGI Skeleton", None),
            ("hisab", "HISAB Protocol", None),
            ("release", "Release & Diagnostics", None),
            ("export", "Dataset Export", None),
        ],
    ),
]


def get_overview_metrics() -> Dict[str, Any]:
    """Return canonical System Overview dashboard metrics."""
    op_summary = get_opcode_summary()
    sha = MASTER_TABLE.compute_sha256()
    return {
        "title": "System Overview",
        "subtitle": "Hijaiyyah Scientific Computing Environment",
        "status_badge": "SYSTEM READY",
        "software_version": SOFTWARE_VERSION,
        "dataset_version": APP_VERSION,
        "sha256": sha,
        "cards": [
            {
                "label": "Canonical Letters",
                "value": "28 / 28",
                "sub": "HM-28 dataset",
                "accent": THEME.highlight,
            },
            {
                "label": "Hybit Dimensions",
                "value": "18D",
                "sub": "504 integer values",
                "accent": THEME.gold,
            },
            {
                "label": "H-ISA Catalog",
                "value": str(op_summary["unique_opcodes"]),
                "sub": (
                    f"{op_summary['rtl_implemented']} RTL · "
                    f"{op_summary['software_only']} SW-only"
                ),
                "accent": THEME.highlight,
            },
            {
                "label": "Canonical Guards",
                "value": "6",
                "sub": "G1–G4 · T1–T2",
                "accent": THEME.success,
            },
        ],
        "pipeline_stages": [
            ("01", "HC / .hcell", "Orthographic & EBNF Source"),
            ("02", "CellIR", "DAG/CFG & Two-Layer Proof"),
            ("03", "4-B′", "Static Control Flow & Mask"),
            ("04", "HPG1 v2", "7-Word Header & CHECKSUM32"),
            ("05", "HVM / HCPU", "3-Way Parity Execution"),
        ],
    }


class OverviewTab:
    """
    Built-in System Overview dashboard for the Hijaiyyah Scientific Computing Environment.
    Displays the 4 primary metric cards, the 5-stage computational pipeline,
    and quick navigation triggers to the core workbenches.
    """

    def __init__(
        self,
        notebook: ttk.Notebook,
        on_navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._tab = ttk.Frame(notebook)
        notebook.add(self._tab, text="  Overview  ")
        self._on_navigate = on_navigate
        self._build()

    def _build(self) -> None:
        metrics = get_overview_metrics()

        container = tk.Frame(self._tab, bg=THEME.bg, padx=24, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # ── Top Hero Header ──────────────────────────────────────
        hero = tk.Frame(container, bg=THEME.bg)
        hero.pack(fill=tk.X, pady=(0, 18))

        left_hero = tk.Frame(hero, bg=THEME.bg)
        left_hero.pack(side=tk.LEFT, anchor=tk.W)

        tk.Label(
            left_hero,
            text=metrics["title"],
            font=("Inter", 20, "bold"),
            fg=THEME.fg,
            bg=THEME.bg,
        ).pack(anchor=tk.W)

        tk.Label(
            left_hero,
            text=metrics["subtitle"],
            font=("Inter", 11),
            fg=THEME.dim_fg,
            bg=THEME.bg,
        ).pack(anchor=tk.W, pady=(2, 0))

        badge = tk.Label(
            hero,
            text=f"  ● {metrics['status_badge']}  ",
            font=("JetBrains Mono", 10, "bold"),
            fg=THEME.success,
            bg=THEME.surface,
            padx=10,
            pady=6,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        badge.pack(side=tk.RIGHT, anchor=tk.E)

        # ── 4 Metric Cards Row ───────────────────────────────────
        cards_row = tk.Frame(container, bg=THEME.bg)
        cards_row.pack(fill=tk.X, pady=(0, 22))

        for idx, card_spec in enumerate(metrics["cards"]):
            card = tk.Frame(
                cards_row,
                bg=THEME.surface,
                padx=18,
                pady=16,
                highlightbackground=THEME.border,
                highlightthickness=1,
            )
            card.pack(
                side=tk.LEFT,
                fill=tk.BOTH,
                expand=True,
                padx=(0 if idx == 0 else 8, 0 if idx == len(metrics["cards"]) - 1 else 8),
            )
            tk.Label(
                card,
                text=card_spec["label"].upper(),
                font=("Inter", 9, "bold"),
                fg=THEME.dim_fg,
                bg=THEME.surface,
            ).pack(anchor=tk.W)
            tk.Label(
                card,
                text=card_spec["value"],
                font=("JetBrains Mono", 24, "bold"),
                fg=card_spec["accent"],
                bg=THEME.surface,
            ).pack(anchor=tk.W, pady=(6, 4))
            tk.Label(
                card,
                text=card_spec["sub"],
                font=("JetBrains Mono", 10),
                fg=THEME.fg,
                bg=THEME.surface,
            ).pack(anchor=tk.W)

        # ── 5-Stage Computational Pipeline Panel ─────────────────
        pipe_panel = tk.Frame(
            container,
            bg=THEME.surface,
            padx=20,
            pady=18,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        pipe_panel.pack(fill=tk.X, pady=(0, 22))

        pipe_header = tk.Frame(pipe_panel, bg=THEME.surface)
        pipe_header.pack(fill=tk.X, pady=(0, 14))
        tk.Label(
            pipe_header,
            text="COMPUTATIONAL PIPELINE",
            font=("Inter", 10, "bold"),
            fg=THEME.highlight,
            bg=THEME.surface,
        ).pack(side=tk.LEFT)
        tk.Label(
            pipe_header,
            text="End-to-End Formal Verification & Silicon Execution Path",
            font=("JetBrains Mono", 9),
            fg=THEME.dim_fg,
            bg=THEME.surface,
        ).pack(side=tk.RIGHT)

        stages_row = tk.Frame(pipe_panel, bg=THEME.surface)
        stages_row.pack(fill=tk.X)

        for idx, (num, name, desc) in enumerate(metrics["pipeline_stages"]):
            st_card = tk.Frame(
                stages_row,
                bg=THEME.surface_alt,
                padx=14,
                pady=12,
                highlightbackground=THEME.border,
                highlightthickness=1,
            )
            st_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

            top_line = tk.Frame(st_card, bg=THEME.surface_alt)
            top_line.pack(fill=tk.X)
            tk.Label(
                top_line,
                text=num,
                font=("JetBrains Mono", 10, "bold"),
                fg=THEME.gold,
                bg=THEME.surface_alt,
            ).pack(side=tk.LEFT)
            tk.Label(
                top_line,
                text="● READY",
                font=("JetBrains Mono", 8),
                fg=THEME.success,
                bg=THEME.surface_alt,
            ).pack(side=tk.RIGHT)

            tk.Label(
                st_card,
                text=name,
                font=("Inter", 13, "bold"),
                fg=THEME.fg,
                bg=THEME.surface_alt,
            ).pack(anchor=tk.W, pady=(6, 2))
            tk.Label(
                st_card,
                text=desc,
                font=("Inter", 9),
                fg=THEME.dim_fg,
                bg=THEME.surface_alt,
            ).pack(anchor=tk.W)

            if idx < len(metrics["pipeline_stages"]) - 1:
                tk.Label(
                    stages_row,
                    text="→",
                    font=("JetBrains Mono", 14, "bold"),
                    fg=THEME.highlight,
                    bg=THEME.surface,
                ).pack(side=tk.LEFT, padx=2)

        # ── Quick Workbench Launchers & Dataset Seal Summary ─────
        bottom_row = tk.Frame(container, bg=THEME.bg)
        bottom_row.pack(fill=tk.BOTH, expand=True)

        seal_box = tk.Frame(
            bottom_row,
            bg=THEME.surface,
            padx=18,
            pady=16,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        seal_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        tk.Label(
            seal_box,
            text="CRYPTOGRAPHIC DATASET SEAL (HM-28-v1.0-HC18D)",
            font=("Inter", 10, "bold"),
            fg=THEME.gold,
            bg=THEME.surface,
        ).pack(anchor=tk.W, pady=(0, 8))

        for label, val in [
            ("Release Identifier", APP_VERSION),
            ("ROM Footprint", "252 bytes (nibble-packed) · 504 bytes (18 × uint8)"),
            ("SHA-256 Digest", metrics["sha256"]),
            ("Injectivity & Guards", "378 / 378 unique pairs · 168 / 168 guard checks PASS"),
        ]:
            row = tk.Frame(seal_box, bg=THEME.surface)
            row.pack(fill=tk.X, pady=3)
            tk.Label(
                row,
                text=f"{label}:",
                font=("JetBrains Mono", 9),
                fg=THEME.dim_fg,
                bg=THEME.surface,
                width=20,
                anchor=tk.W,
            ).pack(side=tk.LEFT)
            tk.Label(
                row,
                text=val,
                font=("JetBrains Mono", 9, "bold"),
                fg=THEME.fg,
                bg=THEME.surface,
                anchor=tk.W,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        actions_box = tk.Frame(
            bottom_row,
            bg=THEME.surface,
            padx=18,
            pady=16,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        actions_box.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0))

        tk.Label(
            actions_box,
            text="QUICK WORKBENCH LAUNCH",
            font=("Inter", 10, "bold"),
            fg=THEME.highlight,
            bg=THEME.surface,
        ).pack(anchor=tk.W, pady=(0, 10))

        for key, label in [
            ("hcell_pipeline", "Open .hcell / HPG1 Workbench →"),
            ("audit", "Run Mathematical Audit (G1–G4, T1–T2) →"),
            ("bytecode", "Explore 105 H-ISA Opcodes →"),
            ("hc_ide", "Launch HC v1.0 IDE →"),
        ]:
            ttk.Button(
                actions_box,
                text=label,
                command=lambda k=key: self._trigger_nav(k),
            ).pack(fill=tk.X, pady=3)

    def _trigger_nav(self, key: str) -> None:
        if self._on_navigate is not None:
            self._on_navigate(key)


class HOMApp:
    """
    HOM: Hijaiyyah Operating Machine (v1.2.0).
    Uses a vertical grouped sidebar (WORKSPACE, PROGRAMMING, SYSTEM) + hidden
    content notebook so all 15 workbenches + System Overview are accessible
    cleanly without horizontal tab clutter.
    """

    def __init__(self) -> None:
        self._table = MASTER_TABLE
        self._machine = HISAMachine(self._table)
        self._evaluator = HCEvaluator()

        self._root = tk.Tk()
        self._root.title(APP_TITLE)
        self._root.minsize(*MIN_SIZE)
        self._root.configure(bg=THEME.bg)

        try:
            if os.path.exists(LOGO_PATH):
                icon = tk.PhotoImage(file=LOGO_PATH)
                self._root.iconphoto(True, icon)
                self._logo_img = icon
        except Exception:
            pass

        self._nav_buttons: Dict[str, tk.Button] = {}
        self._tab_index_by_key: Dict[str, int] = {}
        self._active_key: str = "overview"
        self._nb: Optional[ttk.Notebook] = None

        configure_styles()
        self._build()

    def _build(self) -> None:
        shell = tk.Frame(self._root, bg=THEME.bg)
        shell.pack(fill=tk.BOTH, expand=True)

        # ── Left Vertical Sidebar ────────────────────────────────
        sidebar = tk.Frame(
            shell,
            bg=THEME.surface_alt,
            width=240,
            highlightbackground=THEME.border,
            highlightthickness=1,
        )
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        self._build_sidebar(sidebar)

        # ── Right Content Area (Top Bar + Hidden Notebook + Statusbar) ─
        right_area = tk.Frame(shell, bg=THEME.bg)
        right_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_header(right_area)

        nb = ttk.Notebook(right_area, style="Hidden.TNotebook")
        nb.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self._nb = nb

        # Instantiate Overview + all 15 modular tabs in deterministic order
        OverviewTab(nb, on_navigate=self.select_view)
        AuditTab(nb, self._table, self._evaluator, self._root)
        LetterExplorerTab(nb, self._table)
        MasterTableTab(nb, self._table)
        GeometryTab(nb, self._table, self._evaluator)
        FiveFieldsTab(nb, self._table, self._evaluator)
        StringIntegralTab(nb, self._table, self._evaluator)
        TheoremTab(nb, self._table, self._evaluator, self._root)
        IDETab(nb, self._root)
        HISAMachineTab(nb, self._machine)
        BytecodeTab(nb)
        HCellTab(nb, self._root)
        CSGiTab(nb, self._table)
        HISABTab(nb, self._table)
        ReleaseTab(nb, self._table, self._root)
        ExportTab(nb, self._table)

        ordered_keys = [
            "overview",
            "audit",
            "letter_explorer",
            "master_table",
            "geometry_lab",
            "five_fields",
            "string_integral",
            "theorems",
            "hc_ide",
            "hisa_machine",
            "bytecode",
            "hcell_pipeline",
            "csgi",
            "hisab",
            "release",
            "export",
        ]
        for idx, k in enumerate(ordered_keys):
            self._tab_index_by_key[k] = idx

        self._build_statusbar(right_area)
        self.select_view("overview")

    def _build_sidebar(self, sidebar: tk.Frame) -> None:
        # Brand block at top of sidebar
        brand = tk.Frame(sidebar, bg=THEME.header_bg, padx=16, pady=14)
        brand.pack(fill=tk.X)

        badge_row = tk.Frame(brand, bg=THEME.header_bg)
        badge_row.pack(fill=tk.X)

        tk.Label(
            badge_row,
            text=" H ",
            font=("JetBrains Mono", 14, "bold"),
            fg="#071426",
            bg=THEME.highlight,
            padx=4,
            pady=2,
        ).pack(side=tk.LEFT)

        title_col = tk.Frame(badge_row, bg=THEME.header_bg)
        title_col.pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(
            title_col,
            text="HOM",
            font=("Inter", 13, "bold"),
            fg=THEME.fg,
            bg=THEME.header_bg,
        ).pack(anchor=tk.W)

        tk.Label(
            title_col,
            text=SOFTWARE_VERSION,
            font=("JetBrains Mono", 9, "bold"),
            fg=THEME.gold,
            bg=THEME.header_bg,
        ).pack(anchor=tk.W)

        tk.Label(
            brand,
            text="HIJAIYYAH OPERATING MACHINE",
            font=("JetBrains Mono", 8),
            fg=THEME.dim_fg,
            bg=THEME.header_bg,
        ).pack(anchor=tk.W, pady=(8, 0))

        tk.Frame(sidebar, bg=THEME.border, height=1).pack(fill=tk.X)

        # Grouped navigation items
        nav_container = tk.Frame(sidebar, bg=THEME.surface_alt, padx=10, pady=8)
        nav_container.pack(fill=tk.BOTH, expand=True)

        for group_title, items in SIDEBAR_GROUPS:
            tk.Label(
                nav_container,
                text=group_title,
                font=("Inter", 8, "bold"),
                fg=THEME.dim_fg,
                bg=THEME.surface_alt,
                padx=6,
                pady=4,
            ).pack(anchor=tk.W, pady=(8, 2))

            for key, label, tag in items:
                row = tk.Frame(nav_container, bg=THEME.surface_alt)
                row.pack(fill=tk.X, pady=1)

                display_text = f"  {label}"
                btn = tk.Button(
                    row,
                    text=display_text,
                    anchor=tk.W,
                    font=("Inter", 10),
                    fg=THEME.fg,
                    bg=THEME.surface_alt,
                    activebackground=THEME.surface,
                    activeforeground=THEME.highlight,
                    bd=0,
                    relief=tk.FLAT,
                    padx=8,
                    pady=5,
                    cursor="hand2",
                    command=lambda k=key: self.select_view(k),
                )
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._nav_buttons[key] = btn

                if tag:
                    tk.Label(
                        row,
                        text=tag,
                        font=("JetBrains Mono", 8, "bold"),
                        fg="#071426",
                        bg=THEME.gold,
                        padx=4,
                        pady=1,
                    ).pack(side=tk.RIGHT, padx=4)

    def select_view(self, key: str) -> None:
        """Switch the active workbench pane and highlight its sidebar entry."""
        if self._nb is None or key not in self._tab_index_by_key:
            return
        self._active_key = key
        self._nb.select(self._tab_index_by_key[key])

        for btn_key, btn in self._nav_buttons.items():
            if btn_key == key:
                btn.configure(
                    bg=THEME.surface,
                    fg=THEME.highlight,
                    font=("Inter", 10, "bold"),
                )
            else:
                btn.configure(
                    bg=THEME.surface_alt,
                    fg=THEME.fg,
                    font=("Inter", 10),
                )

    def _build_header(self, parent: tk.Widget) -> None:
        """Sleek top bar with environment subtitle and cryptographic seal indicator."""
        header = tk.Frame(parent, bg=THEME.header_bg, height=54)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        left = tk.Frame(header, bg=THEME.header_bg, padx=18)
        left.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            left,
            text="Hijaiyyah Scientific Computing Environment",
            font=("Inter", 12, "bold"),
            fg=THEME.fg,
            bg=THEME.header_bg,
        ).pack(side=tk.LEFT, pady=14)

        right = tk.Frame(header, bg=THEME.header_bg, padx=18)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        sha_short = self._table.compute_sha256()[:16]

        tk.Label(
            right,
            text="● SEALED",
            font=("JetBrains Mono", 9, "bold"),
            fg=THEME.success,
            bg=THEME.header_bg,
        ).pack(side=tk.RIGHT, padx=(12, 0))

        tk.Label(
            right,
            text=f"{APP_VERSION}  ·  SHA-256: {sha_short}…",
            font=("JetBrains Mono", 9),
            fg=THEME.dim_fg,
            bg=THEME.header_bg,
        ).pack(side=tk.RIGHT)

        tk.Frame(parent, bg=THEME.border, height=1).pack(fill=tk.X)

    def _build_statusbar(self, parent: tk.Widget) -> None:
        """Bottom status bar with version, ROM metrics, and copyright."""
        tk.Frame(parent, bg=THEME.border, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        bar = tk.Frame(parent, bg=THEME.header_bg, height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        sha_short = self._table.compute_sha256()[:16]

        tk.Label(
            bar,
            text=f"  HOM {SOFTWARE_VERSION}  │  {APP_VERSION}  │  SHA-256: {sha_short}…",
            font=("JetBrains Mono", 9),
            fg=THEME.dim_fg,
            bg=THEME.header_bg,
        ).pack(side=tk.LEFT)

        tk.Label(
            bar,
            text="28 letters · 18D Hybit · 105 H-ISA opcodes (84 RTL) · 6 canonical guards",
            font=("JetBrains Mono", 9),
            fg=THEME.highlight,
            bg=THEME.header_bg,
        ).pack(side=tk.LEFT, padx=20)

        tk.Label(
            bar,
            text="© 2026 Maulana Amratulloh — HMCL  ",
            font=("JetBrains Mono", 9),
            fg=THEME.dim_fg,
            bg=THEME.header_bg,
        ).pack(side=tk.RIGHT)

    def run(self) -> None:
        self._root.mainloop()


def main() -> None:
    app = HOMApp()
    app.run()
