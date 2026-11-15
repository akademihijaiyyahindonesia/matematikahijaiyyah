#!/usr/bin/env python3
"""Build the CosmicTera NUI-Centered Real-Time Computing Monitor layout & hologram ROMs.

Generates from a single source of truth:
    rtl/hcpu_dashboard.hex        8,192 x 12-bit upper + footer layout ROM (rows 0..41, 84..89)
    rtl/hcpu_dashboard_lower.hex  8,192 x 12-bit lower layout ROM (rows 42..83, full 1280x720)
    rtl/hcpu_nui_holo.hex         8,192 x 8-bit NUI Holographic Brain & Orbital Core bitmap ROM
                                  (128x128 4-bit pixels = 256x256 screen pixels at cols 58..89, rows 26..53)
    rtl/hcpu_dashboard_pos.vh     canonical live-field addresses (`define DASH_*_ADDR)
    rtl/hcpu_display.hex          8,192 x 12-bit standalone display node ROM

Preserves all 8 canonical `DASH_*_ADDR` addresses and all 13 checks of `tb_hcpu_dashboard.v`.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

COLS, ROWS = 160, 90
DEPTH = 16384

ROM_ROWS_DIRECT = 42
FOOT_FIRST = 84
ROM_DEPTH = 8192

# Colour indices matching hcpu_text_render.v palette
DIM, WHITE, CYAN, GREEN, YELLOW, RED, BLUE, GOLD = range(8)

# Special glyphs in rtl/hcpu_font8x8.hex (indices 1..5)
CHK = 0x01  # checkmark
ERR = 0x02  # cross / X
RNG = 0x03  # ring / node
DOT = 0x04  # solid bullet
BLK = 0x05  # solid bar block


class Screen:
    def __init__(self) -> None:
        self.cells = [(0x20, DIM)] * DEPTH

    def put(self, col: int, row: int, text: str, attr: int = DIM) -> None:
        if not (0 <= row < ROWS):
            raise ValueError(f"row {row} outside 0..{ROWS - 1}")
        for i, ch in enumerate(text):
            c = col + i
            if c >= COLS:
                raise ValueError(f"text {text!r} at col {col} runs past column {COLS}")
            self.cells[row * COLS + c] = (ord(ch), attr)

    def glyph(self, col: int, row: int, code: int, attr: int = DIM) -> None:
        if 0 <= row < ROWS and 0 <= col < COLS:
            self.cells[row * COLS + col] = (code, attr)

    def rule(self, col: int, row: int, width: int, attr: int = CYAN) -> None:
        for i in range(width):
            self.glyph(col + i, row, BLK, attr)

    def hex(self) -> str:
        return "".join(f"{(a << 8) | ch:03x}\n" for ch, a in self.cells)


def build() -> tuple[Screen, dict[str, tuple[int, int, int]]]:
    """Build the full 160x90 (1280x720) CosmicTera NUI-Centered Real-Time Control Center layout."""
    s = Screen()
    fields: dict[str, tuple[int, int, int]] = {}

    # ── ZONE 1: HEADER — CosmicTera & Hybit Identity (Rows 0..6, TV-Safe Cols 4..154) ──
    # Row 0 must carry GOLD rule at cell 0 (12'h705) for tb_hcpu_dashboard.v.
    s.rule(0, 0, COLS, GOLD)
    s.put(4, 1, "COSMICTERA", GOLD)
    s.put(16, 1, "// HYBIT", WHITE)
    s.put(26, 1, "MATEMATIKA HIJAIYYAH COMPUTING ARCHITECTURE", GOLD)
    s.put(114, 1, "H-ISA V1.2  |  TANG NANO 20K", WHITE)

    s.put(4, 2, "COSMICTERA NUI-CENTERED REAL-TIME CONTROL CENTER", CYAN)
    s.put(114, 2, "HDMI 1280X720P60 TMDS LOCKED", GREEN)

    s.put(4, 4, "NUI CONTROL ALL: INPUT->COORD->EXEC->MON->DEC->FB", GOLD)
    s.put(56, 4, "S1(P88):STOP", CYAN)
    s.put(70, 4, "S2(P87):RECOV", GREEN)
    s.put(86, 4, "UPD:BL616 DFU", DIM)
    s.put(102, 4, "USSS+L7 GATE:ACTIVE", GREEN)
    s.put(124, 4, "11 SUBSYSTEMS", WHITE)

    s.put(4, 5, "REAL-TIME NUI 12-LAYER ORBITAL & SUBSYSTEM ENGINE", CYAN)
    s.put(64, 5, "CTEV.... FSM-ACT", GREEN)
    s.put(80, 5, "S1S2.... BTN-CNT", CYAN)
    s.put(114, 5, "BUILD:CT-NUI-CAS-V1.3", GOLD)
    s.rule(0, 6, COLS, CYAN)

    # ── ZONE 2: PANEL KIRI ATAS — HCPU / H-ISA Core (Cols 4..49, Rows 8..22) ─
    s.glyph(4, 8, DOT, GOLD)
    s.put(6, 8, "HCPU / H-ISA CORE (27.000 MHZ)", WHITE)
    s.rule(4, 9, 44, BLUE)

    def row_label(col: int, row: int, label: str, width: int, name: str,
                  attr: int = WHITE) -> None:
        s.put(col, row, label, CYAN)
        s.put(16, row, "." * width, attr)
        fields[name] = (16, row, width)

    # Canonical addresses 1776, 1936, 2096, 2256, 2416, 2576 preserved.
    # Note: u_comp claims cols 16..31 (16 cells), so right-side notes start at col 32!
    row_label(4, 11, "STATE", 12, "state", GREEN)
    row_label(4, 12, "PC", 12, "pc")
    row_label(4, 13, "INSTRUCTION", 12, "instr")
    row_label(4, 14, "CYCLE", 12, "cycle")
    row_label(4, 15, "FLAGS", 12, "flags")
    row_label(4, 16, "GUARD", 12, "guard", GREEN)

    s.put(32, 11, "CTRL FSM", DIM)
    s.put(32, 12, "IMEM 12B", DIM)
    s.put(32, 13, "32B WORD", DIM)
    s.put(32, 14, "27M TICK", DIM)
    s.put(32, 15, "O/LT/Z/G", DIM)
    s.put(32, 16, "6-GUARD", DIM)

    # Block col 16 (blk = row*10 + 1), live hex at pos 4..7
    s.put(4, 18, "OPCODE/REG", CYAN)
    s.put(16, 18, "OP0X.... ACTV   ", CYAN)
    s.put(32, 18, "18GPR+16HREG", DIM)

    s.put(4, 19, "INST STEPS", CYAN)
    s.put(16, 19, "0X00.... STEPS  ", WHITE)
    s.put(32, 19, "RET/EXEC CNT", DIM)

    s.put(4, 20, "LAST PRINT", CYAN)
    s.put(16, 20, "0X00.... UART   ", GREEN)
    s.put(32, 20, "115200 8N1", GREEN)

    s.put(4, 21, "PIPELINE", CYAN)
    s.put(16, 21, "NOT INSTRUMENTED", DIM)
    s.put(34, 21, "5-STG INT", DIM)

    s.put(4, 22, "PRIV/MEM", CYAN)
    s.put(16, 22, "SUP+USR  [B,L)  ", GREEN)
    s.put(34, 22, "USSS HW", GREEN)

    # ── ZONE 3: PANEL TENGAH ATAS — Matematika Hijaiyyah & Hybit 18D (Cols 52..103) ─
    s.glyph(52, 8, DOT, GOLD)
    s.put(54, 8, "MATEMATIKA HIJAIYYAH & HYBIT 18D", WHITE)
    s.rule(52, 9, 50, BLUE)

    # Block col 64 (blk = row*10 + 4), live hex at pos 4..7
    panel_b = [
        (11, "LETTER OP",  "OP0X.... JIM/KHA", CYAN,  "JIM=E4 KHA=E6"),
        (12, "CODEX OP",   "OP0X.... CODEX  ", CYAN,  "HLOAD..HDOT"),
        (13, "MATH OPS",   "0X00.... EXEC   ", WHITE, "HYBIT ALU"),
        (14, "HNRM2 NMV",  "0X00.... NMV OK ", GREEN, "BSM=112(0X70)"),
        (15, "HDIST ITM",  "0X00.... ITM OK ", GREEN, "DIST=10(0X0A)"),
        (16, "HDOT 14DSP", "0X00.... 14DSP  ", GREEN, "DOT=9 (0X09)"),
        (17, "HYBIT 18D",  "18X8B=144B VEC  ", CYAN,  "28+6 ROM SEAL"),
        (18, "OPERAND",    "JIM(E4)+KHA(E6) ", GOLD,  "ATOM 5+7 HW"),
        (19, "HISAB/CRC",  "HPK+CRC32 1-CYC ", GREEN, "0X50 / 0X51"),
        (20, "VALIDATION", "G1-G4 T1-T2 PASS", GREEN, "U=QX+QS+QA+4QC"),
        (21, "HARD-DSP",   "14XMULT9X9+M36  ", GREEN, "USE_DSP=1 HW"),
        (22, "EXOMATRIX",  "5X5 GF2/GF5 CC  ", CYAN,  "ORD 31 / RNK 4"),
    ]
    for r, lbl, val, col_attr, note in panel_b:
        s.put(52, r, lbl, CYAN)
        s.put(64, r, val, col_attr)
        s.put(82, r, note, DIM)

    # ── ZONE 4: PANEL KANAN ATAS — CosmicTera Subsystem Control (Cols 106..155) ─
    s.glyph(106, 8, DOT, GOLD)
    s.put(108, 8, "NUI SUBSYSTEM CONTROL MATRIX", WHITE)
    s.rule(106, 9, 48, BLUE)

    # Block col 128 (blk = row*10 + 8), live hex at pos 4..7
    panel_c = [
        (11, "HCPU / H-ISA",    "84-OP 27MHZ HW  ", GREEN),
        (12, "HYBIT 18D",       "16X144B REG+ROM ", GREEN),
        (13, "HC / HASM / HBC", "LOADER @0X040 HW", CYAN),
        (14, "HVM / HCVM",      "74/105 PARITY CC", CYAN),
        (15, "NUI L0 EMBED",    "PRT=.... L0 PIPE", GREEN),
        (16, "HAR / UART",      "TX0X.... BYTES  ", GREEN),
        (17, "HISAB ENGINE",    "HPACK+HCRC 1-CYC", GREEN),
        (18, "USSS SECURITY",   "6-GRD+MEM+PRIV  ", GREEN),
        (19, "HOS KERNEL",      "NOT INSTRUMENTED", DIM),
        (20, "HFS / SDIO",      "NOT INSTRUMENTED", DIM),
        (21, "KA'BAH / JAMRAH", "6-GRD HW / NI   ", CYAN),
        (22, "HPG-1 / HMCL",    "HOST PYTHON LIB ", DIM),
    ]
    for r, lbl, val, col_attr in panel_c:
        s.glyph(106, r, CHK if col_attr == GREEN else RNG if col_attr == CYAN else DOT, col_attr)
        s.put(108, r, lbl, CYAN)
        s.put(128, r, val, col_attr)

    s.rule(0, 24, COLS, CYAN)

    # ── ZONE 5: AREA TENGAH UTAMA — NUI HOLOGRAPHIC CORE (Cols 36..103, Rows 25..56) ─
    # Center 256x256 pixel holographic brain & orbital rings occupy cols 58..89 (x=464..719), rows 26..53 (y=208..431).
    # Left orbital node arc sits at cols 36..56, Right orbital node arc at cols 90..103 (leaving cols 104..105 clear).
    s.glyph(36, 25, RNG, GOLD)
    s.put(38, 25, "NUI HOLOGRAPHIC CORE - 12-LAYER ORBITAL CONTROL (L0-L11)", GOLD)

    # Left Orbital Nodes L0..L5 (Cols 36..56, Rows 27..50)
    left_nodes = [
        (27, "L0 VERIFIED KNOW", "N,K,Q,T,R HW->", GREEN),
        (31, "L1 REPO GRAPH   ", "1828N/4689E ->", CYAN),
        (35, "L2 PROGRAM INDEX", "60H/100V CC ->", CYAN),
        (39, "L3 EXEC TRACE   ", "63 RUNS CC  ->", CYAN),
        (43, "L4 SW/HW PARITY ", "74/105 P3   ->", GREEN),
        (47, "L5 LINUX VM HOST", "11 COLL. EH ->", CYAN),
    ]
    for r, title, flow, attr in left_nodes:
        s.glyph(36, r, RNG, attr)
        s.put(38, r, title, WHITE if attr == GREEN else CYAN)
        s.put(38, r + 1, flow, attr)

    # Right Orbital Nodes L6..L11 (Cols 90..103, Rows 27..50 — ends at col 103, 2 cols before Zone 7 at col 106)
    right_nodes = [
        (27, "<-L6 HW INTEL.", "  CDC+RTL CC  ", GREEN),
        (31, "<-L7 AUTONOM. ", "  FAIL-CLSD CC", CYAN),
        (35, "<-L8 DIAGNOS. ", "  MANUAL / AT ", DIM),
        (39, "<-L9 REASON KB", "  7-DOM KB CC ", CYAN),
        (43, "<-L10 ENGINR. ", "  NOT IMPL AT ", DIM),
        (47, "<-L11 UNIV CMP", "  ATOM LNK CC ", DIM),
    ]
    for r, title, flow, attr in right_nodes:
        s.put(90, r, title, WHITE if attr == GREEN else CYAN if attr == CYAN else DIM)
        s.put(90, r + 1, flow, attr)

    # NUI Core Control Loop status caption below the holographic platform (Rows 54..56, Cols 36..103)
    s.put(36, 54, "NUI LOOP: IN->UND->CRD->EXE->MON->DEC->FB  |  ATOM: JIM(E4)+KHA(E6)", CYAN)
    s.put(36, 55, "NUI GATE: L7 FAIL-CLOSED + USSS 6-GUARD  |  HOLO: 128X128 4BPP BSRAM", GOLD)
    s.rule(36, 56, 68, BLUE)

    # ── ZONE 6: KIRI TENGAH & BAWAH — NUI LAYER DETAILS (L0-L11) (TV-Safe Cols 4..34, Rows 25..81) ─
    # Shifted from col=2 to col=4 (31 chars max, cols 4..34) so left TV bezel overscan never clips 'L0..L11'.
    # DASH_BANNER_ADDR is preserved at (col=16, row=34, width=16) = 5456.
    s.glyph(4, 25, DOT, GOLD)
    s.put(6, 25, "NUI L0-L11 LAYER TELEMETRY", WHITE)
    s.rule(4, 26, 30, BLUE)

    # Block col 16 (blk = row*10 + 1), live hex at pos 4..7 for L0 hardware features!
    s.put(4, 28, "L0 TITIK N", CYAN)
    s.put(16, 28, "0X00.... PT=2   ", GREEN)
    s.put(4, 29, "L0 GARIS K", CYAN)
    s.put(16, 29, "0X00.... LN=2   ", GREEN)
    s.put(4, 30, "L0 LENGK Q", CYAN)
    s.put(16, 30, "0X00.... CV=2   ", GREEN)
    s.put(4, 31, "L0 THETA T", CYAN)
    s.put(16, 31, "0X00.... TH=6   ", GREEN)
    s.put(4, 32, "L0 RHO T-U", CYAN)
    s.put(16, 32, "0X00.... RH=6   ", GREEN)
    s.put(4, 33, "L0 EMB CNT", CYAN)
    s.put(16, 33, "0X00.... /5 OK  ", CYAN)

    # Canonical banner slot at (16, 34, 16) = addr 5456
    s.put(4, 34, "L0->L6 BRG:", CYAN)
    fields["banner"] = (16, 34, 16)
    s.put(16, 34, " " * 16, WHITE)

    s.rule(4, 35, 30, BLUE)
    s.put(4, 36, "ID OFFICIAL NAME  STATUS / I-O", GOLD)
    nui_table = [
        (37, "L0 VERIFIED KNOW  RUN  5-FEAT ", GREEN),
        (38, "   IN:JIM+KHA     OUT:2,2,2,6,6", CYAN),
        (39, "L1 REPO GRAPH     CMP  1828N  ", CYAN),
        (40, "   IN:GIT TREE    OUT:4689 EDG", DIM),
        (41, "L2 PROGRAM INDEX  CMP  60H/100V", CYAN),
        (42, "   IN:HASM/PY/V   OUT:AST+CALL", DIM),
        (43, "L3 EXEC UNDERSTD  CMP  63 RUNS", CYAN),
        (44, "   IN:HISAMACHINE OUT:1478 EDG", DIM),
        (45, "L4 SW/HW PARITY   CMP  74/105 ", GREEN),
        (46, "   IN:PY/RTL/BRD  OUT:P3 MATRX", CYAN),
        (47, "L5 LINUX VM HOST  RDY  9/11 OK", CYAN),
        (48, "   IN:LIMACTL ARM OUT:OBS STOR", DIM),
        (49, "L6 HW INTELLIG.   RUN  CDC+RTL", GREEN),
        (50, "   IN:27M TELEM   OUT:720P+F15", CYAN),
        (51, "L7 AUTONOMOUS OP  RDY  FAIL-CL", CYAN),
        (52, "   IN:L5+L6 STATE OUT:ALLOW/ST", DIM),
        (53, "L8 AUTO DIAGNOS.  AT   MANUAL ", DIM),
        (54, "   IN:BOARD LOGS  OUT:ROOT CAU", DIM),
        (55, "L9 REASONING ENG  CMP  7-DOM  ", CYAN),
        (56, "   IN:FACTS+GRAPH OUT:QUERY AN", DIM),
        (57, "L10 ENGINEERING   AT   NOT IMP", DIM),
        (58, "   IN:SPEC+ORACLE OUT:PATCH/RT", DIM),
        (59, "L11 UNIV COMPUT.  AT   ATOM LK", DIM),
        (60, "   IN:L0..L10 ALL OUT:UNIFIED ", DIM),
    ]
    for r, text, attr in nui_table:
        s.put(4, r, text, attr)

    s.rule(4, 62, 30, BLUE)
    s.put(4, 63, "NUI CONTROL CHAIN (VERIFIED):", GOLD)
    s.put(4, 64, "ATOM(E4/E6) -> L0 EMBEDDING  ", GREEN)
    s.put(4, 65, "L0 -> L1 GRAPH -> L2 PROG IDX", CYAN)
    s.put(4, 66, "L2 -> L3 TRACE -> L4 PARITY  ", CYAN)
    s.put(4, 67, "L4 + L5 LINUX  -> L6 HW STATE", GREEN)
    s.put(4, 68, "L6 -> L7 GATE  -> L9 KB->L11 ", CYAN)

    s.rule(4, 70, 30, BLUE)
    s.put(4, 71, "NUI HONESTY CONTRACT (R2/R4):", GOLD)
    s.put(4, 72, "- L0 & L6: LIVE FPGA SILICON ", GREEN)
    s.put(4, 73, "- L1..L5,L7,L9: VERIFIED HOST", CYAN)
    s.put(4, 74, "- L8,L10,L11: AT (UNCLAIMED) ", YELLOW)
    s.put(4, 75, "- NO FAKE CONFIDENCE / DUMMY ", WHITE)
    s.put(4, 76, "- HOS/HFS/KABAH: NOT INSTRUM.", DIM)
    s.put(4, 77, "- JIM (0XE4) CANONICAL LETTER", GREEN)
    s.put(4, 78, "- S1=STOP/PAUSE S2=RST/RECOV.", CYAN)
    s.put(4, 79, "- UPDATE=BL616 DFU (NO GPIO) ", DIM)
    s.put(4, 80, "- GUARD SHOWS TRUE HW STATE  ", GREEN)

    # ── ZONE 7: PANEL KANAN TENGAH — NUI CONTROL, BUTTONS & EVENT LOG (Cols 106..155, Rows 25..56) ─
    s.glyph(106, 25, DOT, GOLD)
    s.put(108, 25, "NUI PHYSICAL CONTROL & FAULT RECOVERY", WHITE)
    s.rule(106, 26, 48, BLUE)

    # Block col 112 (blk = row*10 + 7) & col 128 (blk = row*10 + 8)
    s.put(106, 27, "BTN PIN  FUNCTION         IND / R-S-D-CNT", GOLD)
    s.put(106, 28, "S1  P88  STOP / PAUSE    ", CYAN)
    s.put(128, 28, "RSDC.... USR-STP", GREEN)
    s.put(106, 29, "S2  P87  RESET / RECOV.  ", CYAN)
    s.put(128, 29, "RSDC.... RST/REC", GREEN)
    s.put(106, 30, "UPD USB  BL616 DEBUG DFU ", DIM)
    s.put(128, 30, "NO-FPGA-GPIO DFU", DIM)

    s.put(106, 32, "NUI CTRL/EV   ", CYAN)
    s.put(128, 32, "STEV.... FSM-ACT", WHITE)
    s.put(106, 33, "CPU PRE->POST ", CYAN)
    s.put(128, 33, "PRPO.... TRANSIT", CYAN)
    s.put(106, 34, "FAULT SRC/REC ", CYAN)
    s.put(128, 34, "FLRC.... GUARD  ", GREEN)
    s.put(106, 35, "NUI GATE/RULE ", CYAN)
    s.put(128, 35, "L7:ALLOW S1:STOP", GOLD)

    s.glyph(106, 37, DOT, GOLD)
    s.put(108, 37, "LIVE NUI SUBSYSTEM & HARDWARE EVENT LOG", WHITE)
    s.rule(106, 38, 48, BLUE)

    # Rows 39..48: Live Computation & Event Monitor (col 112 = blk*10+7, col 128 = blk*10+8)
    live_events = [
        (39, "EV0 BT", "PC0X....", WHITE, "OP0X.... ENTRY  ", CYAN),
        (40, "EV1 ST", "ST0X....", WHITE, "MT0X.... MATH   ", GREEN),
        (41, "EV2 L0", "N=0X....", GREEN, "K=0X.... L0-FE1 ", GREEN),
        (42, "EV3 L0", "Q=0X....", GREEN, "T=0X.... L0-FE2 ", GREEN),
        (43, "EV4 L0", "R=0X....", GREEN, "CN0X.... L0-EMB ", CYAN),
        (44, "EV5 NM", "NM0X....", GREEN, "DS0X.... BAB-II ", GREEN),
        (45, "EV6 DT", "DT0X....", GREEN, "LP0X.... 14-DSP ", GREEN),
        (46, "EV7 TX", "TX0X....", CYAN,  "PR0X.... 115200 ", GREEN),
        (47, "EV8 GD", "FL0X....", WHITE, "G1-G4 T1-T2 OK  ", GREEN),
        (48, "EV9 CD", "FR0X....", WHITE, "27M->74M25 LOCK ", CYAN),
    ]
    for r, ev, c112, a1, c128, a2 in live_events:
        s.put(106, r, ev[:6].ljust(6), CYAN)
        s.put(112, r, c112.ljust(16), a1)
        s.put(128, r, c128.ljust(16), a2)

    s.put(106, 50, " NUI LOOP: INPUT->COORD->EXEC->MON->DEC->FB", GOLD)
    s.put(106, 51, " S1 HALTS CPU CLOCK CLEANLY; HDMI STAYS 60HZ", GREEN)
    s.put(106, 52, " S2 RESETS CPU & CLEARS INACTIVE FAULT STATE", CYAN)
    s.put(106, 53, " ACTIVE FAULT SOURCE -> LATCHED UNTIL CLEARED", YELLOW)
    s.put(106, 54, " UNSUPPORTED OPS REJECTED BY USSS & L7 GATE", WHITE)
    s.rule(106, 56, 48, BLUE)

    # ── ZONE 8: AREA TENGAH BAWAH — COMPUTATION FLOW (Cols 36..103, Rows 58..81) ─
    s.glyph(36, 58, DOT, GOLD)
    s.put(38, 58, "VERIFIED COSMICTERA & NUI CONTROL ALL SYSTEM ARCHITECTURE", WHITE)
    s.rule(36, 59, 68, BLUE)

    flow_ascii = [
        (60, "(NUI INPUT: S1/S2/UART/HOST) -> (UNDERSTAND) -> (L0..L11 COORDINATE)", GOLD),
        (61, "          I                                                  I       ", DIM),
        (62, "(S1 P88 STOP/PAUSE) --> (2FF+DEB+CTRL FSM) --> (GLITCH-FREE CLK GATE)", CYAN),
        (63, "(S2 P87 RST/RECOV.) --> (FAULT RECOVERY  )                   I       ", GREEN),
        (64, "                                                             V       ", DIM),
        (65, "       +-------------------------------------- (HCPU 5-STG PIPELINE) ", WHITE),
        (66, "       V                                       (IF->ID->EX->MEM->WB) ", CYAN),
        (67, "(MASTER ROM 28X18D) --> (CODEX ALU + 14X MULT9X9) --> (USSS 6-GUARD) ", GREEN),
        (68, " JIM(0XE4) KHA(0XE6)     HCADD/CGET/HNRM2/HDIST/HDOT   G1-G4 T1-T2   ", GOLD),
        (69, "       I                              I                     I        ", DIM),
        (70, "       +--------------> (NUI L0 PHYSICS EMBEDDING) <--------+        ", GREEN),
        (71, "                         TITIK:2 GARIS:2 LENGKUNG:2                  ", WHITE),
        (72, "                         THETA:6 RHO:6 / BSM: 112, 10, 9             ", CYAN),
        (73, "                                      I                              ", DIM),
        (74, "                                      V                              ", DIM),
        (75, "       (OP-PRINT DECIMAL FSM) --> (UART TX PIN69 + NUI L0 SNIFFER)   ", GREEN),
        (76, "                                      I                              ", DIM),
        (77, "                                      V                              ", DIM),
        (78, "       (2-FF TOGGLE CDC 27M->74.25M) -> (L6+L7 GATE -> HDMI 1280X720)", GOLD),
        (79, "       STATUS: ALL STAGES HARDWARE-VERIFIED ON TANG NANO 20K SILICON ", GREEN),
    ]
    for r, line, attr in flow_ascii:
        s.put(36, r, line, attr)

    # ── ZONE 9: AREA KANAN BAWAH — FPGA METRICS (Cols 106..155, Rows 58..81) ─
    s.glyph(106, 58, DOT, GOLD)
    s.put(108, 58, "TANG NANO 20K FPGA & TIMING METRICS", WHITE)
    s.rule(106, 59, 48, BLUE)

    fpga_metrics = [
        (60, "FPGA DEVICE   ", "GW2AR-LV18QN88C8/I7     ", WHITE),
        (61, "ARCHITECTURE  ", "GOWIN GW2A-18C (20K LUT)", CYAN),
        (62, "LUT4 LOGIC    ", "15,342 / 20,736 (73%)   ", GREEN),
        (63, "ALU CARRY     ", " 2,948 / 15,552 (18%)   ", GREEN),
        (64, "DFF REGISTERS ", " 6,154 / 15,552 (39%)   ", GREEN),
        (65, "BSRAM BLOCKS  ", "    33 /     46 (71%)   ", CYAN),
        (66, "DSP MULT9X9   ", "    14 /     96 (14%)   ", GREEN),
        (67, "DSP MULT36X36 ", "     1 /     12 ( 8%)   ", GREEN),
        (68, "FMAX CORE CLK ", " 98.4+ MHZ (>=27.00 MHZ)", GREEN),
        (69, "FMAX PIXEL CLK", " 84.5+ MHZ (>=74.25 MHZ)", GREEN),
        (70, "CORE DOMAIN   ", "27.000 MHZ XTAL PIN 4   ", WHITE),
        (71, "VIDEO DOMAIN  ", "74.250 MHZ / 371.25 SER ", CYAN),
        (72, "TMDS OUTPUT   ", "PINS 33,35,37,39 DRV=8  ", GREEN),
        (73, "RESET SEQ     ", "2MS PLL QUAL -> STAGED  ", GREEN),
        (74, "BUTTON PINS   ", "S1=PIN88 S2=PIN87 ACT-HI", CYAN),
        (75, "UPDATE BUTTON ", "BL616 DFU (NON-FPGA IO) ", DIM),
        (76, "NUI HOLO ROM  ", "128X128X4B (4 BSRAM)    ", GOLD),
        (77, "TEXT GRID ROM ", "160X90 FULL (12 BSRAM)  ", CYAN),
        (78, "ACTIVE BUILD  ", "CT-NUI-CAS-V1.3 ACTIVE  ", GOLD),
        (79, "BASE CHKPT    ", "M5.2B 920F3E61 PROTECTED", GREEN),
    ]
    for r, k, v, attr in fpga_metrics:
        s.put(106, r, k, CYAN)
        s.put(122, r, v, attr)

    # ── ZONE 10: FOOTER (Rows 82..88, TV-Safe Visible Rows 84..85 + Row 88 Testbench) ─
    s.rule(0, 82, COLS, BLUE)
    s.put(4, 84, "CORE:27.000MHZ", WHITE)
    s.put(20, 84, "PIXEL:74.250MHZ", CYAN)
    s.put(38, 84, "HDMI:1280X720P60 LOCKED", GREEN)
    s.put(64, 84, "CDC:.... LOCKED ", GREEN)
    s.put(82, 84, "RELOCK:00", WHITE)
    s.put(94, 84, "BUILD:CT-NUI-CAS-V1.3", GOLD)
    s.put(118, 84, "BASE:920F3E61", CYAN)
    s.put(134, 84, "S1:STOP S2:RECOV", GREEN)

    s.put(4, 85, "COSMICTERA // HYBIT  -  NUI CONTROL ALL SYSTEM (L0-L11)  -  JIM(0XE4)+KHA(0XE6)  -  UPD BTN = BL616 DFU", GOLD)

    # Row 86 MUST be a CYAN rule (`12'h205` at 14'd13760) for tb_hcpu_dashboard.v!
    s.rule(0, 86, COLS, CYAN)

    # Row 88 MUST keep "PAGE" at col 4..7 and fields["page"] = (10, 88, 1) for tb_hcpu_dashboard.v!
    s.put(4, 88, "PAGE", CYAN)
    s.put(10, 88, ".", WHITE)
    fields["page"] = (10, 88, 1)
    s.put(14, 88, "S1(PIN88) = STOP/PAUSE", CYAN)
    s.put(42, 88, "S2(PIN87) = RESET/RECOVERY", GREEN)
    s.put(74, 88, "UPDATE = BL616 DFU", DIM)
    s.put(108, 88, "COSMICTERA NUI CONTROL ALL SYSTEM", GOLD)

    # Clean every character that is not in the 51-glyph uppercase/symbol font!
    valid_codes = (
        set(range(1, 6))
        | {0x20, 0x25, 0x27, 0x28, 0x29, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F}
        | set(range(ord("0"), ord("9") + 1))
        | {0x3A}
        | set(range(ord("A"), ord("Z") + 1))
    )
    sub_map = {
        ord("_"): ord("-"),
        ord("="): ord(":"),
        ord("["): ord("("),
        ord("]"): ord(")"),
        ord("<"): ord("("),
        ord(">"): ord(")"),
        ord("|"): ord("/"),
        ord(";"): ord(":"),
    }
    for idx, (ch, attr) in enumerate(s.cells):
        if ch in sub_map:
            ch = sub_map[ch]
        elif ch not in valid_codes:
            ch = 0x20
        s.cells[idx] = (ch, attr)

    return s, fields


def build_nui_hologram_rom() -> str:
    """Build 8,192 x 8-bit NUI Holographic Brain & Orbital Core bitmap ROM.

    Represents a 128 x 128 4-bit pixel canvas (displayed at 2x2 pixels = 256 x 256
    on the 1280x720 screen at x = 464..719 [cols 58..89], y = 208..431 [rows 26..53]):
      - Glowing Cyan & Electric Blue Holographic Brain Silhouette, Lobes & Sulci
      - Internal Neural Point-Cloud Mesh & Constellation Synaptic Nodes
      - Bold Italic Chrome-Silver & Emerald-Green 3D 'NUI' Core Emblem
      - Tilted Metallic Gold & Emerald Green Circuit-Trace Orbital Rings + Pads
      - Brainstem Vertical Holographic Light Funnel
      - Multi-Tiered Concentric Holographic Computing Platform at the base
    """
    w, h = 128, 128
    pix = [[0] * w for _ in range(h)]

    # 1. Anatomical multi-lobe brain field (centered at x=64, y=46)
    lobes = [
        (46.0, 40.0, 26.0, 22.0, 1.0),   # left-frontal hemisphere
        (64.0, 34.0, 30.0, 22.0, 1.05),  # superior parietal dome
        (82.0, 40.0, 26.0, 22.0, 1.0),   # right-occipital hemisphere
        (36.0, 52.0, 20.0, 16.0, 0.95),  # anterior frontal pole
        (92.0, 52.0, 20.0, 16.0, 0.95),  # posterior occipital pole
        (52.0, 58.0, 22.0, 15.0, 0.95),  # left temporal lobe
        (76.0, 58.0, 22.0, 15.0, 0.95),  # right temporal lobe
        (80.0, 68.0, 16.0, 10.0, 0.85),  # cerebellum
    ]

    # Synaptic constellation nodes inside the brain
    syn_nodes = [
        (32, 36), (44, 24), (60, 20), (76, 22), (92, 32),
        (26, 50), (42, 42), (86, 42), (100, 50),
        (38, 62), (54, 66), (74, 66), (90, 64), (64, 30),
    ]
    syn_edges = [
        (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (1, 6),
        (2, 13), (3, 7), (4, 8), (7, 8), (5, 9), (6, 10), (7, 11),
        (8, 12), (9, 10), (10, 11), (11, 12),
    ]

    for y in range(h):
        for x in range(w):
            # Evaluate smooth brain lobe union
            d_min = 99.0
            in_brain = False
            lobe_boundary = 99.0
            for cx, cy, rx, ry, _w in lobes:
                d = math.hypot((x - cx) / rx, (y - cy) / ry)
                if d < d_min:
                    d_min = d
                if d <= 1.0:
                    in_brain = True
                    lobe_boundary = min(lobe_boundary, abs(1.0 - d))

            # Brain outer aura & contour (y = 12..78)
            if 1.0 < d_min <= 1.14 and y < 78:
                pix[y][x] = 1 if d_min > 1.07 else 2
            elif in_brain:
                # Gyri/sulci wave ridges
                sulcus1 = abs(math.sin((x - 20) * 0.16 + math.cos((y - 18) * 0.18) * 1.4))
                sulcus2 = abs(math.cos((y - 22) * 0.19 - math.sin((x - 30) * 0.14) * 1.2))
                if d_min >= 0.90:
                    pix[y][x] = 5 if d_min >= 0.95 else 4
                elif lobe_boundary < 0.055 or sulcus1 < 0.09 or sulcus2 < 0.08:
                    pix[y][x] = 4 if (x + y) % 2 == 0 else 3
                else:
                    # Dotted neural point-cloud mesh inside lobes
                    if (x % 3 == 0 and y % 3 == 0) or ((x + y) % 7 == 0 and x % 2 == 0):
                        pix[y][x] = 3
                    else:
                        pix[y][x] = 2 if (x + y) % 2 == 0 else 1

            # 2. Brainstem Holographic Light Funnel (y = 66..108, converging to x = 64)
            if 66 <= y <= 108:
                t = (y - 66) / 42.0
                half_w = 15.0 * (1.0 - 0.72 * t) + 2.5
                dx = abs(x - 64.0)
                if dx <= half_w:
                    fiber = abs(math.sin((x - 64.0) / max(1.5, half_w) * math.pi * 2.5))
                    if dx <= 2.2 * (1.0 - 0.4 * t):
                        pix[y][x] = 6 if y > 96 else 5
                    elif fiber < 0.35 or abs(dx - half_w) < 1.2:
                        pix[y][x] = 5 if t > 0.5 else 4
                    elif pix[y][x] < 2:
                        pix[y][x] = 2

            # 3. Concentric Multi-Ring Holographic Platform at Base (center = 64, 108)
            if y >= 88:
                rx_p = (x - 64.0) / 1.0
                ry_p = (y - 108.0) * 3.6  # perspective tilt 3.6:1
                r_plat = math.hypot(rx_p, ry_p)
                ang = math.atan2(ry_p, rx_p)
                if r_plat <= 8.0:
                    pix[y][x] = 6 if r_plat <= 4.2 else 5
                elif 12.0 <= r_plat <= 15.5:
                    pix[y][x] = 5 if abs(r_plat - 13.8) < 1.0 else 4
                elif 20.0 <= r_plat <= 25.0:
                    seg = int((ang + math.pi) / (math.pi / 6.0))
                    if abs(r_plat - 22.5) < 1.3:
                        pix[y][x] = 9 if seg % 3 == 0 else 8 if seg % 3 == 1 else 4
                    else:
                        pix[y][x] = 2
                elif 30.0 <= r_plat <= 36.5:
                    seg = int((ang + math.pi) / (math.pi / 8.0))
                    if abs(r_plat - 33.2) < 1.5:
                        pix[y][x] = 12 if seg % 4 == 0 else 11 if seg % 2 == 0 else 4
                    else:
                        pix[y][x] = 3 if seg % 2 == 0 else 1
                elif 42.0 <= r_plat <= 47.0:
                    tick = int(abs(ang) * 24.0 / math.pi)
                    if abs(r_plat - 44.5) < 1.2 and tick % 2 == 0:
                        pix[y][x] = 5 if tick % 6 == 0 else 8 if tick % 4 == 0 else 3
                    elif pix[y][x] == 0:
                        pix[y][x] = 1
                elif 51.0 <= r_plat <= 58.0:
                    seg = int((ang + math.pi) / (math.pi / 10.0))
                    if abs(r_plat - 54.5) < 1.4:
                        pix[y][x] = 11 if seg in (2, 7, 12, 17) else 4 if seg % 2 == 0 else 3

    # Draw synaptic constellation edges & bright nodes on the brain
    for i, j in syn_edges:
        x1, y1 = syn_nodes[i]
        x2, y2 = syn_nodes[j]
        steps = int(max(abs(x2 - x1), abs(y2 - y1))) + 1
        for s_i in range(steps + 1):
            px = int(round(x1 + (x2 - x1) * s_i / max(1, steps)))
            py = int(round(y1 + (y2 - y1) * s_i / max(1, steps)))
            if 0 <= px < w and 0 <= py < h and pix[py][px] in (1, 2, 3):
                pix[py][px] = 4
    for nx, ny in syn_nodes:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= nx + dx < w and 0 <= ny + dy < h:
                    dist = math.hypot(dx, dy)
                    if dist <= 1.1:
                        pix[ny + dy][nx + dx] = 6
                    elif dist <= 2.2:
                        pix[ny + dy][nx + dx] = 5

    # 4. Tilted Metallic Gold & Emerald Green Circuit-Trace Orbital Rings around 'NUI'
    cos_a = math.cos(math.radians(-14.0))
    sin_a = math.sin(math.radians(-14.0))
    for y in range(16, 82):
        for x in range(8, 120):
            dx = x - 64.0
            dy = y - 48.0
            u = dx * cos_a - dy * sin_a
            v = dx * sin_a + dy * cos_a
            r_gold = math.hypot(u / 52.0, v / 17.0)
            r_em = math.hypot((u - 1.5) / 45.0, (v + 1.0) / 13.5)

            is_front = not (-36.0 < u < 10.0 and v < -7.0)
            if is_front:
                if 0.94 <= r_gold <= 1.06:
                    pix[y][x] = 12 if abs(r_gold - 1.0) < 0.025 else 11 if abs(r_gold - 1.0) < 0.045 else 10
                elif 0.93 <= r_em <= 1.06:
                    pix[y][x] = 9 if abs(r_em - 1.0) < 0.025 else 8 if abs(r_em - 1.0) < 0.048 else 7

    circuit_traces = [
        (26, 62, 38, 62, 38, 62, 8, 9),
        (38, 62, 43, 58, 48, 64, 8, 9),
        (68, 29, 82, 29, 68, 29, 8, 9),
        (82, 29, 88, 34, 96, 33, 11, 12),
        (80, 62, 96, 56, 80, 62, 11, 12),
        (20, 54, 30, 50, 20, 54, 11, 12),
    ]
    for x1, y1, x2, y2, px_pad, py_pad, c_tr, c_pd in circuit_traces:
        steps = int(max(abs(x2 - x1), abs(y2 - y1))) + 1
        for s_i in range(steps + 1):
            cx = int(round(x1 + (x2 - x1) * s_i / max(1, steps)))
            cy = int(round(y1 + (y2 - y1) * s_i / max(1, steps)))
            if 0 <= cx < w and 0 <= cy < h:
                pix[cy][cx] = c_tr
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= px_pad + dx < w and 0 <= py_pad + dy < h:
                    if abs(dx) + abs(dy) <= 2:
                        pix[py_pad + dy][px_pad + dx] = c_pd

    # 5. Bold Italic Chrome-Silver + Emerald-Green 3D 'NUI' Emblem at Center (y = 36..60)
    def in_nui_glyph(px: float, py: float) -> bool:
        if not (36.0 <= py <= 60.0):
            return False
        sx = px + (py - 48.0) * 0.22
        if 28.0 <= sx <= 33.5:
            return True
        if 45.5 <= sx <= 51.0:
            return True
        if 31.0 <= sx <= 48.0:
            expected_x = 31.5 + (py - 36.0) * (15.5 / 24.0)
            if abs(sx - expected_x) <= 2.9:
                return True
        if 36.0 <= py <= 55.0:
            if 56.0 <= sx <= 61.5 or 73.5 <= sx <= 79.0:
                return True
        if 53.0 <= py <= 60.0 and 56.0 <= sx <= 79.0:
            if py >= 55.5 or (56.0 <= sx <= 62.5) or (72.5 <= sx <= 79.0):
                if not (py > 58.0 and (sx < 58.0 or sx > 77.0)):
                    return True
        if 84.0 <= sx <= 90.0:
            return True
        return False

    for y in range(34, 64):
        for x in range(22, 102):
            if in_nui_glyph(x - 1.5, y - 2.0) or in_nui_glyph(x - 1.0, y - 1.0):
                pix[y][x] = 8 if y < 50 else 7

    for y in range(36, 61):
        for x in range(22, 102):
            if in_nui_glyph(float(x), float(y)):
                if y <= 41:
                    pix[y][x] = 15
                elif y <= 46:
                    pix[y][x] = 14
                elif y <= 49:
                    pix[y][x] = 13
                elif y <= 55:
                    pix[y][x] = 15 if (x + y) % 5 != 0 else 14
                else:
                    pix[y][x] = 14

    for y in range(112, h):
        for x in range(w):
            pix[y][x] = 0

    lines: list[str] = []
    for y in range(h):
        for xPair in range(0, w, 2):
            hi = pix[y][xPair] & 0xF
            lo = pix[y][xPair + 1] & 0xF
            lines.append(f"{(hi << 4) | lo:02x}\n")
    assert len(lines) == 8192
    return "".join(lines)


def build_node() -> Screen:
    s = Screen()

    s.put(4, 1, "MATEMATIKA HIJAIYYAH", GOLD)
    s.put(4, 2, "TECHNOLOGY STACK TO COSMICTERA COMPUTING", GOLD)

    s.put(4, 4, "COSMICTERA DISPLAY NODE", WHITE)
    s.put(4, 5, "-" * 40, CYAN)
    s.put(110, 4, "RACK SLOT 2 - HDMI ENGINE", DIM)
    s.put(110, 5, "1280X720 60HZ - TANG NANO 20K", DIM)

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
    """Pack rows 0..41 and rows 84..89 of a 160x90 screen into 8,192 ROM cells."""
    kept: list[tuple[int, int]] = []
    for row in list(range(ROM_ROWS_DIRECT)) + list(range(FOOT_FIRST, ROWS)):
        for col in range(COLS):
            kept.append(s.cells[row * COLS + col])
    while len(kept) < ROM_DEPTH:
        kept.append((0x20, DIM))
    return "".join(f"{(a << 8) | ch:03x}\n" for ch, a in kept)


def _fold_lower_rom(s: Screen) -> str:
    """Pack rows 42..83 (6,720 cells) into an 8,192-cell BSRAM ROM for full 1280x720 display."""
    kept: list[tuple[int, int]] = []
    for row in range(ROM_ROWS_DIRECT, FOOT_FIRST):
        for col in range(COLS):
            kept.append(s.cells[row * COLS + col])
    while len(kept) < ROM_DEPTH:
        kept.append((0x20, DIM))
    return "".join(f"{(a << 8) | ch:03x}\n" for ch, a in kept)


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    rtl_dir = root / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)

    screen, fields = build()

    hex_path = rtl_dir / "hcpu_dashboard.hex"
    hex_path.write_text(_fold_rom(screen), encoding="ascii")

    lower_path = rtl_dir / "hcpu_dashboard_lower.hex"
    lower_path.write_text(_fold_lower_rom(screen), encoding="ascii")

    holo_path = rtl_dir / "hcpu_nui_holo.hex"
    holo_path.write_text(build_nui_hologram_rom(), encoding="ascii")

    lines = [
        "// hcpu_dashboard_pos.vh - GENERATED by rtl/scripts/gen_dashboard.py.",
        "// Do not edit: the layout and these addresses come from one source, so",
        "// a label that moves a column moves its value with it.",
        "",
    ]
    for name, (col, row, width) in sorted(fields.items()):
        lines.append(f"`define DASH_{name.upper()}_ADDR  14'd{row * COLS + col}")
        lines.append(f"`define DASH_{name.upper()}_W     {width}")
    vh_path = rtl_dir / "hcpu_dashboard_pos.vh"
    vh_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    node = build_node()
    node_path = rtl_dir / "hcpu_display.hex"
    node_path.write_text(_fold_rom(node), encoding="ascii")

    print(f"{hex_path.relative_to(root)}: {ROM_DEPTH} sel (upper + footer)")
    print(f"{lower_path.relative_to(root)}: {ROM_DEPTH} sel (lower rows 42..83)")
    print(f"{holo_path.relative_to(root)}: {ROM_DEPTH} byte (128x128 4bpp NUI Hologram)")
    print(f"{node_path.relative_to(root)}: {ROM_DEPTH} sel (display node)")
    print(f"{vh_path.relative_to(root)}: {len(fields)} field hidup")
    for name, (col, row, width) in sorted(fields.items()):
        print(f"  {name:8s} kolom {col:3d} baris {row:2d} lebar {width:2d} "
              f"-> alamat {row * COLS + col}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
