#!/usr/bin/env python3
"""Build the CosmicTera monitor's static layout, and say where the live fields go.

The screen is 160x90 character cells. Almost all of it never changes: the
headline, the panel frames, the labels, and every field the hardware cannot
yet report. Painting that from logic every frame would cost a sequencer and a
string ROM to draw something that is identical in frame 60 and frame 216,000.

So the fixed part is baked into the text RAM's initial contents and the RTL
painter only writes the handful of cells that carry live numbers. This script
emits both halves from one description, because two hand-maintained copies of
a screen layout drift the moment a label moves one column:

    rtl/hcpu_dashboard.hex      16,384 cells, four hex digits each
    rtl/hcpu_dashboard_pos.vh   the live-field addresses, as `define

WHAT IS NOT HERE: numbers. Not one value on this screen is written by this
script. The live fields are emitted as runs of '.' so an unpainted screen
shows dots rather than a plausible zero, and every field the hardware does
not expose is spelled NOT INSTRUMENTED in full. A monitor that invents a
value is worse than one that admits it has none.

THE FONT HAS NO LOWERCASE. rtl/hcpu_font8x8.hex carries 51 glyphs: A-Z,
0-9, a little punctuation, and five symbols in the control range. Everything
here is uppercase because the alternative is blank cells.
"""
from __future__ import annotations

import sys
from pathlib import Path

COLS, ROWS = 160, 90
DEPTH = 16384

# The display node's ROM covers rows 0..41 directly and folds the footer rows
# 84..89 in behind them. Everything between is blank on screen and absent from
# the ROM. hcpu_text_render.v's caller has to use the same three numbers.
ROM_ROWS_DIRECT = 42
FOOT_FIRST = 84
ROM_DEPTH = 8192

# Colour indices, and they must match hcpu_text_render.v's palette.
DIM, WHITE, CYAN, GREEN, YELLOW, RED, BLUE, GOLD = range(8)

# The two glyphs that are not letters: a bullet for status, a solid block for
# rules. Both are real entries in the font, measured, not assumed.
DOT = 0x04
BLK = 0x05


class Screen:
    def __init__(self) -> None:
        self.cells = [(0x20, DIM)] * DEPTH

    def put(self, col: int, row: int, text: str, attr: int = DIM) -> None:
        if not (0 <= row < ROWS):
            raise ValueError(f"row {row} outside 0..{ROWS - 1}")
        for i, ch in enumerate(text):
            c = col + i
            if c >= COLS:
                raise ValueError(f"text {text!r} runs past column {COLS}")
            self.cells[row * COLS + c] = (ord(ch), attr)

    def glyph(self, col: int, row: int, code: int, attr: int = DIM) -> None:
        self.cells[row * COLS + col] = (code, attr)

    def rule(self, col: int, row: int, width: int, attr: int = CYAN) -> None:
        for i in range(width):
            self.glyph(col + i, row, BLK, attr)

    def hex(self) -> str:
        # Twelve bits: eight of character, four of colour. The spare four
        # of the old sixteen existed because a RAM word was convenient;
        # a ROM has no such excuse and 14,400 cells pay for every bit.
        return "".join(f"{(a << 8) | ch:03x}\n" for ch, a in self.cells)


def build() -> tuple[Screen, dict[str, tuple[int, int, int]]]:
    """Returns the screen and the live fields as name -> (col, row, width)."""
    s = Screen()

    # ── the headline, which is the point of the whole machine ────
    s.rule(0, 0, COLS, GOLD)
    s.put(4, 1, "MATEMATIKA HIJAIYYAH", GOLD)
    s.put(4, 2, "TECHNOLOGY STACK TO COSMICTERA COMPUTING", GOLD)
    s.put(4, 4, "COSMICTERA COMPUTER", WHITE)
    s.put(4, 5, "REAL-TIME SYSTEM MONITOR", CYAN)
    s.put(120, 4, "H-ISA V1.2", WHITE)
    s.put(120, 5, "TANG NANO 20K", DIM)
    s.rule(0, 6, COLS, CYAN)

    fields: dict[str, tuple[int, int, int]] = {}

    # ── panel 1: the CPU, and this is the panel with real data ───
    s.put(4, 8, "HCPU", WHITE)
    s.rule(4, 9, 44, BLUE)

    # THE VALUE COLUMN IS 16, NOT 18, AND THAT IS AN ADDRESS CONSTRAINT.
    # The compositor decides whether a cell is live by comparing the top ten
    # bits of its address, so every field has to start on a multiple of
    # sixteen. Since a row is 160 cells and 160 is a multiple of 16, the row
    # contributes nothing to the remainder -- the column alone decides. An
    # unaligned field would cost a subtractor per field and buy nothing.
    def row_label(col: int, row: int, label: str, width: int, name: str,
                  attr: int = WHITE) -> None:
        s.put(col, row, label, CYAN)
        s.put(16, row, "." * width, attr)
        fields[name] = (16, row, width)

    row_label(4, 11, "STATE", 12, "state", GREEN)
    row_label(4, 12, "PC", 12, "pc")
    row_label(4, 13, "INSTRUCTION", 12, "instr")
    row_label(4, 14, "CYCLE", 12, "cycle")
    row_label(4, 15, "FLAGS", 12, "flags")
    row_label(4, 16, "GUARD", 12, "guard", GREEN)

    # Everything below this line in the CPU panel has no wire behind it.
    s.put(4, 18, "PID", CYAN)
    s.put(18, 18, "NOT INSTRUMENTED", DIM)
    s.put(4, 19, "PROCESS", CYAN)
    s.put(18, 19, "NOT INSTRUMENTED", DIM)
    s.put(4, 20, "TRAP", CYAN)
    s.put(18, 20, "NOT INSTRUMENTED", DIM)
    s.put(4, 21, "PIPELINE", CYAN)
    s.put(18, 21, "NOT INSTRUMENTED", DIM)

    # ── panel 2: the stack, none of it instrumented yet ──────────
    s.put(56, 8, "COSMICTERA STACK", WHITE)
    s.rule(56, 9, 44, BLUE)
    stack = ["HYBIT", "HCVM", "HIJRAH", "JUMRAH", "KA'BAH",
             "JIM", "NUI", "HISAB", "HAR", "HC / HASM / HBC"]
    for i, name in enumerate(stack):
        s.glyph(56, 11 + i, DOT, DIM)
        s.put(58, 11 + i, name, CYAN)
        s.put(78, 11 + i, "NOT INSTRUMENTED", DIM)

    # ── panel 3: devices ─────────────────────────────────────────
    s.put(108, 8, "DEVICE STATUS", WHITE)
    s.rule(108, 9, 44, BLUE)
    devices = ["HDMI", "SDIO", "HFS", "HOS", "MEMORY", "MMIO", "UART", "TIMER"]
    for i, name in enumerate(devices):
        s.glyph(108, 11 + i, DOT, DIM)
        s.put(110, 11 + i, name, CYAN)
        s.put(124, 11 + i, "NOT INSTRUMENTED", DIM)

    # HDMI is the one device this screen can speak for: if these characters
    # are visible, the display engine is running by definition.
    s.glyph(108, 11, DOT, GREEN)
    s.put(124, 11, "ACTIVE 1280X720", GREEN)

    s.rule(0, 24, COLS, CYAN)

    # ── the event log, which has no event bus behind it yet ──────
    s.put(4, 26, "LIVE EVENT LOG", WHITE)
    s.rule(4, 27, 100, BLUE)
    s.put(4, 29, "NOT INSTRUMENTED", DIM)
    s.put(4, 30, "NO EVENT BUS EXISTS IN THIS DESIGN. THE FIELDS ABOVE THAT CARRY", DIM)
    s.put(4, 31, "VALUES ARE READ FROM SIGNALS THAT ALREADY EXISTED AT THE", DIM)
    s.put(4, 32, "WRAPPER BOUNDARY. EVERY OTHER FIELD SAYS SO.", DIM)

    # ── footer: the page indicator, which the button moves ───────
    s.rule(0, 86, COLS, CYAN)
    s.put(4, 88, "PAGE", CYAN)
    s.put(10, 88, ".", WHITE)
    fields["page"] = (10, 88, 1)
    s.put(14, 88, "SHORT PRESS = NEXT PAGE", DIM)
    s.put(44, 88, "LONG PRESS = SYSTEM", DIM)
    s.put(120, 88, "M5.2A DISPLAY", DIM)

    # The banner pages 1..8 paint over: one line, and it tells the truth.
    # Sixteen cells, which is exactly "NOT INSTRUMENTED". The painter
    # writes it on pages 1..8 and blanks it on page 0, so one slot of the
    # field walker covers it.
    # Column 16 for the same alignment reason as the value fields above.
    fields["banner"] = (16, 34, 16)
    s.put(16, 34, " " * 16, WHITE)

    return s, fields


def build_node() -> Screen:
    """The display node's screen: no CPU behind it, and it says so.

    ── why this is one column and almost no rules ──────────────────
    The first version drew four bars of 160 solid blocks from edge to edge
    and underlined three panels. On a monitor that is four stripes eight
    pixels tall and 1280 wide, and the screen read as a test pattern with
    text in it rather than as a system monitor. It also collided: the left
    panel's caption ran 51 columns from column 4 and the middle panel began
    at 56, so a line ended "...ON THIS NODE.* JIM" with no gap at all.

    So: one column, dark ground, and separators drawn with '-' rather than
    the solid-block glyph. '-' inks a single row six pixels wide in the
    middle of its cell; the block glyph inks all sixty-four. That is the
    whole difference between a rule and a stripe.

    Nothing here is telemetry. The four subsystems marked READY are true by
    the fact that you can read this screen at all -- there is no way to draw
    the word without the timing, the renderer, the font and the layout.
    """
    s = Screen()

    s.put(4, 1, "MATEMATIKA HIJAIYYAH", GOLD)
    s.put(4, 2, "TECHNOLOGY STACK TO COSMICTERA COMPUTING", GOLD)

    s.put(4, 4, "COSMICTERA DISPLAY NODE", WHITE)
    s.put(4, 5, "-" * 40, CYAN)
    s.put(110, 4, "RACK SLOT 2 - HDMI ENGINE", DIM)
    s.put(110, 5, "1280X720 60HZ - TANG NANO 20K", DIM)

    # True by construction: these four drew the words.
    for i, name in enumerate(["VIDEO TIMING", "RENDERER", "FONT ROM", "PAGE KEY"]):
        s.put(4, 7 + i, name, CYAN)
        s.put(22, 7 + i, "READY", GREEN)

    s.put(4, 13, "COSMICTERA STACK", WHITE)
    s.put(4, 14, "-" * 40, CYAN)
    stack = ["HCPU", "H-ISA", "HYBIT", "HCVM", "HIJRAH",
             "KA'BAH", "JUMRAH", "JIM", "NUI"]
    for i, name in enumerate(stack):
        s.put(4, 15 + i, name, CYAN)
        s.put(22, 15 + i, "NOT INSTRUMENTED", DIM)

    s.put(4, 26, "TELEMETRY LINK", WHITE)
    s.put(4, 27, "-" * 40, CYAN)
    s.put(4, 28, "COMPUTE NODE", CYAN)
    s.put(22, 28, "NOT CONNECTED", DIM)
    s.put(4, 30, "A LIVE LINK NEEDS A SECOND BOARD. ONE IS PRESENT.", DIM)
    s.put(4, 31, "SEQUENTIAL RACK SLOTS ARE NOT LIVE TELEMETRY.", DIM)

    s.put(4, 88, "PAGE", CYAN)
    s.put(10, 88, ".", WHITE)
    s.put(14, 88, "SHORT PRESS = NEXT PAGE", DIM)
    s.put(44, 88, "LONG PRESS = SYSTEM", DIM)
    s.put(120, 88, "M5.3A DISPLAY NODE", DIM)
    s.put(16, 34, " " * 16, WHITE)
    return s


def _fold_rom(s: Screen) -> str:
    """Pack a 160x90 screen into 8,192 ROM cells (rows 0..41 + rows 84..89)."""
    kept: list[tuple[int, int]] = []
    for row in list(range(ROM_ROWS_DIRECT)) + list(range(FOOT_FIRST, ROWS)):
        for col in range(COLS):
            kept.append(s.cells[row * COLS + col])
    while len(kept) < ROM_DEPTH:
        kept.append((0x20, DIM))
    return "".join(f"{(a << 8) | ch:03x}\n" for ch, a in kept)


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    screen, fields = build()

    hex_path = root / "rtl" / "hcpu_dashboard.hex"
    hex_path.write_text(_fold_rom(screen), encoding="ascii")

    lines = [
        "// hcpu_dashboard_pos.vh - GENERATED by rtl/scripts/gen_dashboard.py.",
        "// Do not edit: the layout and these addresses come from one source, so",
        "// a label that moves a column moves its value with it.",
        "",
    ]
    for name, (col, row, width) in sorted(fields.items()):
        lines.append(f"`define DASH_{name.upper()}_ADDR  14'd{row * COLS + col}")
        lines.append(f"`define DASH_{name.upper()}_W     {width}")
    vh_path = root / "rtl" / "hcpu_dashboard_pos.vh"
    vh_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    # The display node's ROM holds only the rows that carry ink: 0..41 as
    # themselves, then 84..89 folded up behind them. Rows 42..83 are blank on
    # screen and absent here, which is what turns a 196,608-bit ROM that did
    # not fit into a 98,304-bit one that does.
    node = build_node()
    node_path = root / "rtl" / "hcpu_display.hex"
    node_path.write_text(_fold_rom(node), encoding="ascii")

    print(f"{hex_path.relative_to(root)}: {ROM_DEPTH} sel")
    print(f"{node_path.relative_to(root)}: {ROM_DEPTH} sel (display node)")
    print(f"{vh_path.relative_to(root)}: {len(fields)} field hidup")
    for name, (col, row, width) in sorted(fields.items()):
        print(f"  {name:8s} kolom {col:3d} baris {row:2d} lebar {width:2d} "
              f"-> alamat {row * COLS + col}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
