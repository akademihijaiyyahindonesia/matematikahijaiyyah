#!/usr/bin/env python3
"""
Bit-Exact Golden Frame Renderer & RTL Pixel-by-Pixel Verification for Stage 1.2
1. Renders full 1280x720 PNG frames for:
   - frame_startup_1280x720.png (SCREEN_STARTUP = 0, uptime = 00:00:00)
   - frame_ready_1280x720.png   (SCREEN_READY   = 1, uptime = 00:05:42)
   - frame_error_1280x720.png   (SCREEN_ERROR   = 2, uptime = 00:12:09, relock = 01, ovf = 1)
2. Compares the RTL simulation dumps (`rtl_hero_logo_512x184.raw`,
   `rtl_scanlines_startup.raw`, `rtl_scanlines_ready.raw`, `rtl_scanlines_error.raw`)
   against the Python golden frames, asserting 0 unexpected pixel mismatches.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from PIL import Image

import build_boot_ui_assets as gen

WORK_DIR = gen.WORK_DIR
RTL_DIR = gen.RTL_DIR
PREVIEWS_DIR = gen.PREVIEWS_DIR

SCANLINE_YS = [0, 18, 34, 62, 76, 274, 290, 320, 330, 354, 386, 434, 450, 458, 474, 482, 490, 506, 522, 538, 554, 570, 602, 618, 650, 682]


def load_rom_hex_12b(path: Path) -> list[tuple[int, int]]:
    lines = path.read_text(encoding="ascii").splitlines()
    return [(int(x, 16) & 0xFF, (int(x, 16) >> 8) & 0xF) for x in lines]


def load_logo_rle(rle_path: Path, pal_vh_path: Path) -> tuple[np.ndarray, np.ndarray]:
    words = [int(x, 16) for x in rle_path.read_text(encoding="ascii").splitlines()]
    idx_map = gen.decode_rle_9bit(words, 512, 184)
    pal = np.zeros((32, 3), dtype=np.uint8)
    pal[:] = [6, 12, 22]
    for line in pal_vh_path.read_text(encoding="ascii").splitlines():
        line = line.strip()
        if line.startswith("5'd"):
            parts = line.split(":")
            idx = int(parts[0].replace("5'd", "").strip())
            hex_val = parts[1].split("24'h")[1].split(";")[0].strip()
            pal[idx] = [int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)]
    return idx_map, pal


def apply_compositor_overrides(
    base_cells: list[tuple[int, int]],
    screen_state: int,
    uptime_str: str,  # "HH:MM:SS"
    ev_ts_list: list[str],
    fifo_count: int,
    fifo_ovf: bool,
    relock_str: str,
    page: int = 0,
    st_timing_ok: bool = True,
    st_pll_locked: bool = True,
    st_vout_ok: bool = True,
    lock_lost_pix: bool = False,
    st_logo_ok: bool = True,
) -> list[tuple[int, int]]:
    """Build 160x90 full screen cell grid (ch, attr) with exact compositor rules."""
    grid = [(0x20, gen.C_DIM)] * (160 * 90)
    for r_scr, r_rom in gen.SCREEN_ROW_TO_ROM_ROW.items():
        for c in range(160):
            if r_scr in (60, 66) and c >= 96:
                continue
            if r_scr in (56, 59, 61, 65, 67) and c < 96:
                continue
            grid[r_scr * 160 + c] = base_cells[r_rom * 160 + c]

    def put_str(r: int, c0: int, width: int, s: str, attr: int) -> None:
        s_pad = s.ljust(width)[:width]
        for i, ch in enumerate(s_pad):
            grid[r * 160 + c0 + i] = (ord(ch), attr)

    # 1. Region 1 Header Status Badge (row 2, cols 108..127)
    if screen_state == 1:
        put_str(2, 108, 20, "DISPLAY READY", gen.C_GREEN)
    elif screen_state == 2:
        put_str(2, 108, 20, "DISPLAY ERROR", gen.C_RED)
    else:
        put_str(2, 108, 20, "DISPLAY INITIALIZING", gen.C_YELLOW)

    # 2. Region 2 Logo Fallback Row (row 20)
    if st_logo_ok:
        put_str(20, 0, 160, "", gen.C_DIM)

    # 3. Region 3 Panel C Live Uptime (row 44, cols 83..98)
    hh_mm = uptime_str[:5]
    put_str(44, 83, 5, hh_mm, gen.C_GOLD)
    grid[44 * 160 + 88] = (0x20, gen.C_DIM)
    put_str(44, 89, 10, f"({uptime_str})", gen.C_WHITE)

    # 4. Region 3 Panel D Live Logo Status (row 46, cols 133..137)
    put_str(46, 133, 5, "READY" if st_logo_ok else "FAULT", gen.C_GREEN if st_logo_ok else gen.C_RED)

    # 5. Region 3 Row 48 Live Status Lines for Panels A, B, D
    if screen_state == 2:
        put_str(48, 13, 10, "FAULT", gen.C_RED)
    elif st_timing_ok:
        put_str(48, 13, 10, "ACTIVE", gen.C_GREEN)
    else:
        put_str(48, 13, 10, "SYNCING", gen.C_YELLOW)

    if lock_lost_pix or screen_state == 2:
        put_str(48, 52, 10, "UNLOCKED", gen.C_RED)
    elif st_pll_locked:
        put_str(48, 52, 10, "LOCKED", gen.C_GREEN)
    else:
        put_str(48, 52, 10, "QUALIFYING", gen.C_YELLOW)

    if screen_state == 1:
        put_str(48, 130, 13, "DISPLAY READY", gen.C_GREEN)
    elif screen_state == 2:
        put_str(48, 130, 13, "DISPLAY ERROR", gen.C_RED)
    else:
        put_str(48, 130, 13, "STARTUP", gen.C_YELLOW)

    # 6. Region 4 Boot Sequence 10 Stages (rows 57, 60, 63, 66, 69)
    is_err = (screen_state == 2)
    m_st1 = 2
    m_st2 = 3 if lock_lost_pix else (2 if st_pll_locked else 1)
    m_st3 = 3 if lock_lost_pix else 2
    m_st4 = 3 if lock_lost_pix else 2
    m_st5 = 3 if is_err else 2
    m_st6 = 3 if is_err else (2 if st_timing_ok else 1)
    m_st7 = 2
    m_st8 = 3 if not st_logo_ok else 2
    m_st9 = 2 if st_timing_ok else 1
    m_st10 = 3 if is_err else (2 if st_vout_ok else (1 if st_timing_ok else 0))

    def set_stage(r: int, c0: int, mode: int) -> None:
        attr = gen.C_GREEN if mode == 2 else (gen.C_RED if mode == 3 else (gen.C_YELLOW if mode == 1 else gen.C_DIM))
        glyph = gen.G_CHK if mode == 2 else (gen.G_ERR if mode == 3 else gen.G_RNG)
        label = "READY" if mode == 2 else ("ERROR" if mode == 3 else ("INITIALIZING" if mode == 1 else "WAITING"))
        grid[r * 160 + c0] = (glyph, attr)
        grid[r * 160 + c0 + 1] = (0x20, attr)
        put_str(r, c0 + 2, 12, label, attr)

    for r, m_l, m_r in [
        (57, m_st1, m_st6),
        (60, m_st2, m_st7),
        (63, m_st3, m_st8),
        (66, m_st4, m_st9),
        (69, m_st5, m_st10),
    ]:
        set_stage(r, 32, m_l)
        set_stage(r, 77, m_r)

    # 6A. Region 5 Compute Ecosystem Header (row 54, cols 101..135)
    if is_err:
        put_str(54, 101, 35, "COMPUTE ECOSYSTEM - FAULT DETECTED ", gen.C_RED)
    elif screen_state == 1:
        put_str(54, 101, 35, "COMPUTE ECOSYSTEM - 16/16 ENTRIES  ", gen.C_GREEN)
    else:
        put_str(54, 101, 35, "COMPUTE ECOSYSTEM - INITIALIZING   ", gen.C_CYAN)

    # 6B. Region 5 Live Telemetry & Multi-Page Inspector Bar (row 56, cols 99..152)
    if page == 0:
        put_str(56, 99, 3, "PC:", gen.C_CYAN)
        put_str(56, 102, 3, "1A4", gen.C_WHITE)
        put_str(56, 105, 4, " IN:", gen.C_CYAN)
        put_str(56, 109, 8, "4E010200", gen.C_WHITE)
        put_str(56, 117, 4, " CY:", gen.C_CYAN)
        put_str(56, 121, 8, "0002C1C9", gen.C_WHITE)
        put_str(56, 129, 4, " FL:", gen.C_CYAN)
        put_str(56, 133, 2, "01" if is_err else "04", gen.C_WHITE)
        put_str(56, 135, 3, " G:", gen.C_CYAN)
        put_str(56, 138, 2, "ER" if is_err else "OK", gen.C_RED if is_err else gen.C_GREEN)
        put_str(56, 140, 1, " ", gen.C_CYAN)
        put_str(56, 141, 3, "HLT" if is_err else "RUN", gen.C_RED if is_err else gen.C_GREEN)
        put_str(56, 144, 5, " CDC:", gen.C_CYAN)
        put_str(56, 149, 4, "ERR " if is_err else "LIVE", gen.C_RED if is_err else gen.C_GREEN)
    else:
        page_strs = {
            1:  "P1 HM-28 ROM:28X72B HYBIT:18D GUARD:G1-G4/T1-T2 VF/CC ",
            2:  "P2 HISA:82/104 RTL CODEX:PROFILE-C HDOT:14-CYC  [CC]  ",
            3:  "P3 CELLS:.HCELL-IR-HISA PSI:331/331 HPG1:4-B'   [CC]  ",
            4:  "P4 HOS:3-PROC PREEMPT HFS:SDIO LBA1+16 PERSIST  [CC]  ",
            5:  "P5 HMCL:L0-L12 A1:DSP A2:RADIX4 A3:NIBBLE-SPLIT [CC]  ",
            6:  "P6 NUI:12-LAYER L0-L7:PARITY THEOREMS:18/18     CC/AT ",
            7:  "P7 JAMRAH:7-NODE 33-CLK/B HIJRAH:GF(5) 700/700  [CC]  ",
            8:  "P8 KABAH:1600B+HMAC-L3 207/207 PORTAL8888:SEAL  VF/EH ",
            9:  "P9 JIM:0XE4 5X5 LFSR/J-MACH GF2:31 GF5:3124 WAVE [CC] ",
            10: "P10 HISAB:JUMMAL/MOD-RED CRC32 RAMAL:CORE+IMPULSE [CC]",
            11: "P11 ALG:STAT/DYN/AGM/ITM/EXM VTM/NMV EXOMATRIX  VF/CC ",
            12: "P12 SW:HCVM HAR HYBIT-AI CSGI HOM-GUI (HOST/SW)  [CC] ",
        }
        s54 = page_strs.get(page, page_strs[12])
        put_str(56, 99, 48, s54[:48], gen.C_CYAN)
        put_str(56, 147, 6, s54[48:54], gen.C_RED if is_err else gen.C_GOLD)

    # 6D. Region 5 Expanded 16-Entry Compute Ecosystem Grid (rows 57, 59, 61, 63, 65, 67, 69, 71)
    sub_mode = 3 if is_err else (2 if screen_state == 1 else 1)
    sub_attr = gen.C_GREEN if sub_mode == 2 else (gen.C_RED if sub_mode == 3 else gen.C_CYAN)
    sub_glyph = gen.G_CHK if sub_mode == 2 else (gen.G_ERR if sub_mode == 3 else gen.G_RNG)
    sub_left_strs = (
        ["ER HALT", "ER GRD ", "ER LBA ", "ER NUI ", "ER MAC ", "ER HREG", "ER WAVE", "ER ROM "]
        if sub_mode == 3
        else (
            ["CC 120M", "CC 4GRD", "CC LBA1", "CC/AT  ", "VF/EH  ", "CC 144B", "CC 5X5 ", "VF/CC  "]
            if sub_mode == 2
            else ["CC 5STG", "CC 4GRD", "CC LBA1", "CC/AT  ", "VF/EH  ", "CC 144B", "CC 5X5 ", "VF/CC  "]
        )
    )
    sub_right_strs = (
        ["ER OPCODE   ", "ER KERNEL   ", "ER CODEX    ", "ER TIMING   ", "ER UNSEALED ", "ER GF5 OP   ", "ER HISAB    ", "ER LOADER   "]
        if sub_mode == 3
        else ["CC 82/104 OP", "CC 3-PROC OK", "CC HDOT 14C ", "CC 33-CLK/B ", "EH P8 SEALED", "CC 700/700  ", "CC CRC32/28 ", "CC L9/SW-VM "]
    )
    for idx, r in enumerate([57, 59, 61, 63, 65, 67, 69, 71]):
        grid[r * 160 + 99] = (sub_glyph, sub_attr)
        put_str(r, 117, 7, sub_left_strs[idx], sub_attr)
        grid[r * 160 + 126] = (sub_glyph, sub_attr)
        put_str(r, 141, 12, sub_right_strs[idx], sub_attr)

    # 7. Region 6 Event Console Header (row 75)
    put_str(75, 45, 2, f"0{fifo_count}", gen.C_WHITE)
    put_str(75, 62, 6, "OVFL  " if fifo_ovf else "NONE  ", gen.C_RED if fifo_ovf else gen.C_GREEN)

    # 8. Region 6 Event Timestamps (rows 77, 79, 81)
    put_str(77, 5, 8, ev_ts_list[0], gen.C_GOLD)
    put_str(79, 5, 8, ev_ts_list[1], gen.C_GOLD)
    put_str(81, 5, 8, ev_ts_list[2], gen.C_GOLD)
    put_str(77, 82, 8, ev_ts_list[3], gen.C_GOLD)
    put_str(79, 82, 8, ev_ts_list[4], gen.C_GOLD)
    put_str(81, 82, 8, ev_ts_list[5], gen.C_GOLD)

    # 9. Region 6 Event 6 Dynamic Status (row 81, cols 129..136)
    if screen_state == 1:
        put_str(81, 129, 8, "READY", gen.C_GREEN)
    elif screen_state == 2:
        put_str(81, 129, 8, "ERROR", gen.C_RED)
    else:
        put_str(81, 129, 8, "STARTUP", gen.C_YELLOW)

    # 10. Region 7 Footer Dynamic Telemetry (row 85, y = 680..687)
    if screen_state == 1:
        put_str(85, 51, 15, "DISPLAY READY", gen.C_GREEN)
    elif screen_state == 2:
        put_str(85, 51, 15, "DISPLAY ERROR", gen.C_RED)
    else:
        put_str(85, 51, 15, "STARTUP", gen.C_YELLOW)
    put_str(85, 81, 2, relock_str, gen.C_WHITE)
    put_str(85, 98, 3, "YES" if fifo_ovf else "NO ", gen.C_RED if fifo_ovf else gen.C_GREEN)
    put_str(85, 118, 2, f"{page:02d}", gen.C_WHITE)

    return grid


def render_golden_frame(
    screen_state: int,
    uptime_str: str,
    ev_ts_list: list[str],
    fifo_count: int,
    fifo_ovf: bool,
    relock_str: str,
    st_timing_ok: bool,
    st_pll_locked: bool,
    st_vout_ok: bool,
    lock_lost_pix: bool = False,
    st_logo_ok: bool = True,
    page: int = 0,
) -> np.ndarray:
    """Render full 1280x720x3 uint8 RGB array matching cosmictera_boot_render.v."""
    base_cells = load_rom_hex_12b(RTL_DIR / "boot_text_rom.hex")
    font_bits = gen.load_font_bits()
    logo_idx_map, logo_pal = load_logo_rle(RTL_DIR / "logo_rle_rom.hex", RTL_DIR / "logo_palette.vh")

    grid = apply_compositor_overrides(
        base_cells=base_cells,
        screen_state=screen_state,
        uptime_str=uptime_str,
        ev_ts_list=ev_ts_list,
        fifo_count=fifo_count,
        fifo_ovf=fifo_ovf,
        relock_str=relock_str,
        page=page,
        st_timing_ok=st_timing_ok,
        st_pll_locked=st_pll_locked,
        st_vout_ok=st_vout_ok,
        lock_lost_pix=lock_lost_pix,
        st_logo_ok=st_logo_ok,
    )

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :] = [0x06, 0x0C, 0x16]

    state_accent = (0xE0, 0x50, 0x50) if screen_state == 2 else ((0x30, 0xD0, 0x70) if screen_state == 1 else (0xE0, 0xB0, 0x40))

    # 1. Background chrome & card borders (matching cosmictera_boot_render.v)
    # Region 1 Header: rows 0..7 (y = 0..63)
    frame[0:64, :] = [0x09, 0x13, 0x22]
    frame[0:2, :] = [0xD6, 0x9B, 0x2C]
    frame[62:64, :] = state_accent
    # Header badge: cols 107..128 (x = 856..1031), y = 11..27
    frame[11:28, 856:1032] = [0x0D, 0x1E, 0x36]
    frame[11, 856:1032] = state_accent
    frame[27, 856:1032] = state_accent
    frame[11:28, 856] = state_accent
    frame[11:28, 1031] = state_accent

    # Region 3 Metric Cards: rows 40..50 (y = 320..407)
    for c_start, c_end, is_c in [(3, 39, False), (42, 78, False), (81, 117, True), (120, 156, False)]:
        x0, x1 = c_start * 8, (c_end + 1) * 8
        y0, y1 = 40 * 8, 51 * 8
        frame[y0:y1, x0:x1] = [0x0A, 0x15, 0x26]
        frame[y0:y1, x0] = [0x1E, 0x3A, 0x5F]
        frame[y0:y1, x1 - 1] = [0x1E, 0x3A, 0x5F]
        frame[y1 - 1, x0:x1] = [0x1E, 0x3A, 0x5F]
        frame[y0:y0 + 2, x0:x1] = [0xF0, 0xC8, 0x60] if is_c else [0x30, 0xC0, 0xD0]

    # Region 4 (cols 3..94) & Region 5 (cols 97..156): rows 53..72 (y = 424..583)
    for c_start, c_end in [(3, 94), (97, 156)]:
        x0, x1 = c_start * 8, (c_end + 1) * 8
        y0, y1 = 53 * 8, 73 * 8
        frame[y0:y1, x0:x1] = [0x09, 0x13, 0x22]
        frame[55 * 8 + 4, x0:x1] = [0x16, 0x2C, 0x48]
        frame[y0, x0:x1] = [0x1E, 0x3A, 0x5F]
        frame[y1 - 1, x0:x1] = [0x1E, 0x3A, 0x5F]
        frame[y0:y1, x0] = [0x1E, 0x3A, 0x5F]
        frame[y0:y1, x1 - 1] = [0x1E, 0x3A, 0x5F]

    # Region 6 Event Console (cols 3..156, rows 74..83, y = 592..671)
    x0, x1 = 3 * 8, 157 * 8
    y0, y1 = 74 * 8, 84 * 8
    r6_bdr = [0xE0, 0x50, 0x50] if screen_state == 2 else [0x1E, 0x3A, 0x5F]
    frame[y0:y1, x0:x1] = [0x08, 0x10, 0x1D]
    frame[76 * 8 + 2, x0:x1] = [0x16, 0x2C, 0x48]
    frame[y0, x0:x1] = r6_bdr
    frame[y1 - 1, x0:x1] = r6_bdr
    frame[y0:y1, x0] = r6_bdr
    frame[y0:y1, x1 - 1] = r6_bdr

    # Region 7 Footer (y = 676..719; text on row 85, y = 680..687, 32 px bottom margin)
    frame[676:720, :] = [0x09, 0x13, 0x22]
    frame[676, :] = [0x1E, 0x3A, 0x5F]

    # 2. Text Glyph Layer
    for r in range(90):
        for c in range(160):
            ch, attr = grid[r * 160 + c]
            if ch == 0x20:
                continue
            rgb = gen.TEXT_PALETTE[attr]
            g_base = (ch & 0x7F) * 8
            y_base = r * 8
            x_base = c * 8
            for sy in range(8):
                b = font_bits[g_base + sy]
                if b == 0:
                    continue
                for sx in range(8):
                    if (b >> (7 - sx)) & 1:
                        frame[y_base + sy, x_base + sx] = rgb

    # 3. Header Mini-Emblem (x = 28..51, y = 18..41)
    for y in range(18, 42):
        for x in range(28, 52):
            ex = (x - 28) - 12
            ey = (y - 18) - 12
            r2 = ex * ex + ey * ey
            abs_ed = abs(ex + ey)
            if r2 <= 18:
                frame[y, x] = [0x2D, 0xCD, 0x73] if r2 <= 6 else [0x14, 0x91, 0x4E]
            elif abs_ed <= 2 and r2 <= 132:
                frame[y, x] = [0xF6, 0xCE, 0x5F] if ex < 0 else [0xD6, 0x9B, 0x2C]
            elif 36 <= r2 <= 80:
                frame[y, x] = [0xF2, 0xF6, 0xFA] if ey < 0 else [0x98, 0xA8, 0xB8]
            elif 80 < r2 <= 110:
                frame[y, x] = [0xD6, 0x9B, 0x2C]

    # 4. Hero Logo (x = 384..895, y = 76..259)
    if st_logo_ok:
        fg_mask = logo_idx_map != 0
        hero_region = frame[76:260, 384:896]
        hero_rgb = logo_pal[logo_idx_map]
        hero_region[fg_mask] = hero_rgb[fg_mask]

    return frame


def main() -> None:
    # 1. Render all 3 golden full-resolution 1280x720 frames
    # Note: on scanlines y < 18, `de_seen` is set on the first active pixel (y=0, x=0),
    # so for y=0, x=0 de_seen was 0 and for y>=1 de_seen is 1.
    frame_startup = render_golden_frame(
        screen_state=0,
        uptime_str="00:00:00",
        ev_ts_list=["00:00:00"] * 6,
        fifo_count=5,
        fifo_ovf=False,
        relock_str="00",
        st_timing_ok=True,
        st_pll_locked=True,
        st_vout_ok=False,
    )
    frame_ready = render_golden_frame(
        screen_state=1,
        uptime_str="00:05:42",
        ev_ts_list=["00:00:00", "00:00:00", "00:00:00", "00:00:00", "00:00:00", "00:00:01"],
        fifo_count=6,
        fifo_ovf=False,
        relock_str="00",
        st_timing_ok=True,
        st_pll_locked=True,
        st_vout_ok=True,
    )
    frame_error = render_golden_frame(
        screen_state=2,
        uptime_str="00:12:09",
        ev_ts_list=["00:00:00", "00:00:00", "00:00:00", "00:00:00", "00:00:00", "00:12:09"],
        fifo_count=8,
        fifo_ovf=True,
        relock_str="01",
        st_timing_ok=True,
        st_pll_locked=True,
        st_vout_ok=True,
    )

    Image.fromarray(frame_startup).save(PREVIEWS_DIR / "frame_startup_1280x720.png")
    Image.fromarray(frame_ready).save(PREVIEWS_DIR / "frame_ready_1280x720.png")
    Image.fromarray(frame_error).save(PREVIEWS_DIR / "frame_error_1280x720.png")

    # Render golden frames for Inspector Pages P1..P12 (1280x720)
    for pg in range(1, 13):
        f_pg = render_golden_frame(
            screen_state=1,
            uptime_str="00:05:42",
            ev_ts_list=["00:00:00", "00:00:00", "00:00:00", "00:00:00", "00:00:00", "00:00:01"],
            fifo_count=6,
            fifo_ovf=False,
            relock_str="00",
            st_timing_ok=True,
            st_pll_locked=True,
            st_vout_ok=True,
            page=pg,
        )
        Image.fromarray(f_pg).save(PREVIEWS_DIR / f"frame_page_p{pg:02d}_1280x720.png")

    # 2. Compare RTL-streamed 512x184 Hero Logo against Python golden Hero Logo
    rtl_logo_bytes = (PREVIEWS_DIR / "rtl_hero_logo_512x184.raw").read_bytes()
    rtl_logo = np.frombuffer(rtl_logo_bytes, dtype=np.uint8).reshape((184, 512, 3))
    golden_logo = frame_ready[76:260, 384:896]
    logo_mismatches = int(np.sum(rtl_logo != golden_logo))
    assert logo_mismatches == 0, f"RTL Hero Logo mismatch count: {logo_mismatches}"
    print(f"[PASS] Golden vs RTL 512x184 Hero Logo comparison: 0 / {512*184} pixel mismatches!")

    # 3. Compare RTL-captured 18 scanlines across STARTUP, READY, and ERROR against Golden
    for state_name, raw_name, golden_frame in [
        ("STARTUP", "rtl_scanlines_startup.raw", frame_startup),
        ("READY",   "rtl_scanlines_ready.raw",   frame_ready),
        ("ERROR",   "rtl_scanlines_error.raw",   frame_error),
    ]:
        raw_bytes = (PREVIEWS_DIR / raw_name).read_bytes()
        rtl_lines = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((len(SCANLINE_YS), 1280, 3))
        golden_lines = golden_frame[SCANLINE_YS, :, :]
        diff_px = int(np.sum(np.any(rtl_lines != golden_lines, axis=2)))
        if diff_px != 0:
            for idx, y_coord in enumerate(SCANLINE_YS):
                row_diff = int(np.sum(np.any(rtl_lines[idx] != golden_lines[idx], axis=1)))
                if row_diff > 0:
                    bad_x = np.where(np.any(rtl_lines[idx] != golden_lines[idx], axis=1))[0]
                    print(f"  {state_name} y={y_coord}: {row_diff} diffs at x={bad_x[:10]} RTL={rtl_lines[idx, bad_x[0]]} GOLD={golden_lines[idx, bad_x[0]]}")
        assert diff_px == 0, f"{state_name} had {diff_px} pixel mismatches!"
        print(f"[PASS] Golden vs RTL {state_name:7s} 26-region scanlines ({len(SCANLINE_YS)*1280} px): 0 pixel mismatches!")


if __name__ == "__main__":
    main()
