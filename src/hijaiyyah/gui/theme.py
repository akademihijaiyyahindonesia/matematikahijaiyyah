"""Theme configuration for HOM — Hijaiyyah Scientific Computing Environment (v1.2.0)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from tkinter import ttk
from typing import Tuple

APP_TITLE = "HOM — Hijaiyyah Scientific Computing Environment"
APP_VERSION = "HM-28-v1.0-HC18D"
SOFTWARE_VERSION = "v1.2.0"
MIN_SIZE = (1280, 800)
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "Logo HOM.png")
MATH_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "Mathematics Hijaiyyah.png")


@dataclass(frozen=True)
class Theme:
    """
    Hijaiyyah Scientific Computing Environment Palette:
      - Midnight: #071426
      - Surface:  #10243A
      - Cyan:     #26C6DA
      - Gold:     #D6AF57
      - Text:     #EAF2FA
    """

    bg: str = "#071426"          # Midnight primary canvas
    fg: str = "#EAF2FA"          # Crisp clinical text
    accent: str = "#10243A"      # Surface card/panel background
    surface: str = "#10243A"     # Surface card/panel background
    surface_alt: str = "#0C1C30" # Elevated sub-panel / sidebar background
    highlight: str = "#26C6DA"   # Cyan primary accent
    gold: str = "#D6AF57"        # Gold secondary accent
    success: str = "#2ECC71"     # Verified / Guard Pass green
    error: str = "#EF5350"       # Fault / Violation red
    warning: str = "#D6AF57"     # Gold warning / specification badge
    text_bg: str = "#050E1B"     # Deep code/data console background
    header_bg: str = "#050E1B"   # Top header & sidebar brand background
    header_fg: str = "#EAF2FA"   # Header primary text
    hijaiyyah_fg: str = "#26C6DA" # Cyan accent for symbols & titles
    number_fg: str = "#D6AF57"   # Gold accent for numeric metrics
    dim_fg: str = "#8AA0B8"      # Muted slate-blue secondary text
    border: str = "#1C3552"      # Clean 1px structural border

    font_mono: Tuple[str, int] = ("JetBrains Mono", 11)
    font_mono_sm: Tuple[str, int] = ("JetBrains Mono", 10)
    font_mono_lg: Tuple[str, int] = ("JetBrains Mono", 12)
    font_ui: Tuple[str, int] = ("Inter", 10)
    font_ui_bold: Tuple = ("Inter", 10, "bold")
    font_header: Tuple = ("Inter", 14, "bold")
    font_hijaiyyah: Tuple[str, int] = ("Simplified Arabic", 18)


THEME = Theme()


def configure_styles() -> None:
    style = ttk.Style()
    style.theme_use("clam")

    # ── Base frames ──────────────────────────────────────────
    style.configure("TFrame", background=THEME.bg)
    style.configure("Surface.TFrame", background=THEME.surface)
    style.configure("Sidebar.TFrame", background=THEME.surface_alt)
    style.configure("TPanedwindow", background=THEME.bg)
    style.configure("TSeparator", background=THEME.border)

    # ── Labels ───────────────────────────────────────────────
    style.configure("TLabel", background=THEME.bg, foreground=THEME.fg, font=THEME.font_ui)
    style.configure(
        "Surface.TLabel",
        background=THEME.surface,
        foreground=THEME.fg,
        font=THEME.font_ui,
    )
    style.configure(
        "Header.TLabel",
        background=THEME.header_bg,
        foreground=THEME.header_fg,
        font=THEME.font_header,
        padding=8,
    )
    style.configure(
        "Subtitle.TLabel",
        background=THEME.header_bg,
        foreground=THEME.dim_fg,
        font=THEME.font_ui,
        padding=(8, 0),
    )
    style.configure(
        "Status.TLabel",
        background=THEME.surface,
        foreground=THEME.dim_fg,
        font=THEME.font_mono_sm,
        padding=4,
    )
    style.configure(
        "Seal.TLabel",
        background=THEME.surface,
        foreground=THEME.success,
        font=("JetBrains Mono", 9, "bold"),
        padding=4,
    )

    # ── Notebook tabs (internal sub-tabs & headless hidden shell) ─
    style.configure("TNotebook", background=THEME.bg, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=THEME.surface,
        foreground=THEME.dim_fg,
        padding=[14, 7],
        font=THEME.font_ui_bold,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", THEME.highlight)],
        foreground=[("selected", "#071426")],
    )

    # Hidden notebook style for sidebar-driven main navigation
    style.layout("Hidden.TNotebook.Tab", [])
    style.configure("Hidden.TNotebook", background=THEME.bg, borderwidth=0, tabmargins=0)

    # ── Buttons ──────────────────────────────────────────────
    style.configure(
        "TButton",
        background=THEME.surface,
        foreground=THEME.fg,
        font=THEME.font_ui,
        padding=(10, 6),
        borderwidth=1,
        bordercolor=THEME.border,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", THEME.highlight), ("pressed", THEME.highlight)],
        foreground=[("active", "#071426"), ("pressed", "#071426")],
    )
    style.configure(
        "Accent.TButton",
        background=THEME.highlight,
        foreground="#071426",
        font=THEME.font_ui_bold,
        padding=(12, 7),
        borderwidth=0,
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#4DD0E1"), ("pressed", "#00ACC1")],
        foreground=[("active", "#071426")],
    )

    # ── Checkbutton ──────────────────────────────────────────
    style.configure(
        "TCheckbutton",
        background=THEME.bg,
        foreground=THEME.fg,
        font=THEME.font_ui,
    )
    style.map(
        "TCheckbutton",
        background=[("active", THEME.bg)],
        foreground=[("active", THEME.highlight)],
    )

    # ── LabelFrame ───────────────────────────────────────────
    style.configure(
        "TLabelframe",
        background=THEME.bg,
        bordercolor=THEME.border,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=THEME.bg,
        foreground=THEME.highlight,
        font=THEME.font_ui_bold,
    )

    # ── Treeview ─────────────────────────────────────────────
    style.configure(
        "Treeview",
        background=THEME.text_bg,
        foreground=THEME.fg,
        fieldbackground=THEME.text_bg,
        font=THEME.font_mono_sm,
        borderwidth=0,
        rowheight=24,
    )
    style.configure(
        "Treeview.Heading",
        background=THEME.surface,
        foreground=THEME.highlight,
        font=THEME.font_ui_bold,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", THEME.highlight)],
        foreground=[("selected", "#071426")],
    )

    # ── Combobox & Entry ─────────────────────────────────────
    style.configure(
        "TCombobox",
        fieldbackground=THEME.text_bg,
        foreground=THEME.fg,
        background=THEME.surface,
    )
    style.configure(
        "TEntry",
        fieldbackground=THEME.text_bg,
        foreground=THEME.fg,
        insertcolor=THEME.highlight,
    )

    # ── Scrollbar ────────────────────────────────────────────
    style.configure(
        "Vertical.TScrollbar",
        background=THEME.surface,
        troughcolor=THEME.bg,
        borderwidth=0,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=THEME.surface,
        troughcolor=THEME.bg,
        borderwidth=0,
    )
