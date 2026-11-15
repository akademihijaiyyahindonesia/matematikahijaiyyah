#!/usr/bin/env python3
"""
Stage 1.5 BSRAM ROM Suite Builder (`build_stage1_5_roms.py`)

Generates all BSRAM initialization tables for the Stage 1.5 Unified SoC
Boot Display subsystem on Tang Nano 20K (`GW2AR-LV18QN88C8/I7`):
  1. `boot_text_rom.hex`     (4,096 x 12-bit, 3 SP BSRAMs): Base 25-row character grid
     with static EV01..EV05 `00:00:00` gold timestamps and FIFO tens `0` pre-baked.
  2. `boot_comp_rom.hex`     (4,096 x 12-bit, 3 SP BSRAMs): 60 dynamic string & P1..P12
     inspector slices indexed by `{comp_slice[5:0], la_col[5:0]}`.
  3. `boot_cell_tag_rom.hex` (4,096 x  8-bit, 2 SP BSRAMs): Per-cell compositor override
     tag `{tag_gold[7], is_r56_nib[6], tag_code[5:0]}` indexed by `rom_addr`.
  4. `boot_bg_x_rom.hex`     (2,048 x  8-bit, 1 SP BSRAM) : Horizontal pixel chrome flags
     stored at index `(x - 1) % 1650` so synchronous read on `h_count[10:0]` aligns with `x`.
  5. `boot_bg_y_rom.hex`     (1,024 x  8-bit, 1 SP BSRAM) : Vertical scanline chrome flags
     indexed by `vla[9:0]` (plus bit 6 `in_hero_y` and bit 7 `is_y75`).
  6. `boot_emblem_rom.hex`   (4,096 x  4-bit, 1 SP BSRAM) : Exact 24x24 Header Mini-Emblem
     pixel color codes stored at `{y[5:0], (x - 1)[5:0]}` for `x = 28..51, y = 18..41`.
"""
from __future__ import annotations

from pathlib import Path

STAGE15_DIR = Path("/Users/AMRA/hijaiyyah-mathematics/cosmictera-build/stage-1-5-unified-soc")
RTL_DIR = STAGE15_DIR / "rtl"

C_DIM, C_WHITE, C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BLUE, C_GOLD = range(8)
G_CHK, G_ERR, G_RNG = 0x01, 0x02, 0x03


def build_text_and_cell_tag_roms() -> None:
    src_lines = (RTL_DIR / "boot_text_rom.hex").read_text(encoding="ascii").splitlines()
    text_rom = [int(x, 16) for x in src_lines]
    assert len(text_rom) == 4096

    def set_text_cell(rom_row: int, col: int, ch: str, attr: int) -> None:
        text_rom[rom_row * 160 + col] = ((attr & 0xF) << 8) | (ord(ch) & 0xFF)

    set_text_cell(16, 45, "0", C_WHITE)
    for r_rom in (17, 18, 19):
        for i, ch in enumerate("00:00:00"):
            set_text_cell(r_rom, 5 + i, ch, C_GOLD)
            set_text_cell(r_rom, 82 + i, ch, C_GOLD)

    out_text = RTL_DIR / "boot_text_rom.hex"
    out_text.write_text("".join(f"{w:03x}\n" for w in text_rom), encoding="ascii")

    tag_rom = [0] * 4096

    def set_tag(rom_row: int, col: int, code: int, gold: bool = False, r56_nib: bool = False) -> None:
        val = (code & 0x3F) | (0x40 if r56_nib else 0) | (0x80 if gold else 0)
        tag_rom[rom_row * 160 + col] = val

    for c in range(108, 128):
        set_tag(0, c, 1)
    for c in range(160):
        set_tag(2, c, 3)
    for c, k in [(83, 0), (84, 1), (86, 2), (87, 3)]:
        set_tag(6, c, 16 + k, gold=True)
    for c, k in [(90, 0), (91, 1), (93, 2), (94, 3), (96, 4), (97, 5)]:
        set_tag(6, c, 16 + k, gold=False)
    for c in range(133, 138):
        set_tag(7, c, 1)
    for c in list(range(13, 25)) + list(range(52, 62)) + list(range(130, 143)):
        set_tag(8, c, 1)
    for c in range(101, 136):
        set_tag(9, c, 1)

    r56_nib_cols = {
        102: 16, 103: 17, 104: 18,
        109: 19, 110: 20, 111: 21, 112: 22, 113: 23, 114: 24, 115: 25, 116: 26,
        121: 27, 122: 28, 123: 29, 124: 30, 125: 31, 126: 32, 127: 33, 128: 34,
        133: 35, 134: 36,
    }
    for c in range(99, 153):
        if c in r56_nib_cols:
            k = r56_nib_cols[c]
            set_tag(22, c, 16 + k, gold=False, r56_nib=True)
        elif c >= 147:
            set_tag(22, c, 2)
        else:
            set_tag(22, c, 1)

    for r_rom in (10, 11, 12, 13, 14):
        for c in list(range(32, 46)) + list(range(77, 91)):
            set_tag(r_rom, c, 1)

    for r_rom in (10, 23, 24, 12, 11, 13, 14, 15):
        for c in [99] + list(range(117, 124)) + [126] + list(range(141, 153)):
            set_tag(r_rom, c, 1)

    set_tag(16, 46, 16 + 12, gold=False)
    for c in range(62, 68):
        set_tag(16, c, 1)

    for c, k in [(82, 6), (83, 7), (85, 8), (86, 9), (88, 10), (89, 11)]:
        set_tag(19, c, 16 + k, gold=True)
    for c in range(129, 137):
        set_tag(19, c, 1)

    for c in list(range(51, 66)) + list(range(98, 101)):
        set_tag(21, c, 1)
    set_tag(21, 81, 16 + 13, gold=False)
    set_tag(21, 82, 16 + 14, gold=False)
    set_tag(21, 118, 4, gold=False)
    set_tag(21, 119, 16 + 15, gold=False)

    out_tag = RTL_DIR / "boot_cell_tag_rom.hex"
    out_tag.write_text("".join(f"{w:02x}\n" for w in tag_rom), encoding="ascii")
    print(f"Generated {out_text.name} & {out_tag.name} (4,096 words each)")


def build_comp_rom() -> None:
    rom = [(C_DIM << 8) | 0x20] * 4096

    def put_slice_col(slice_id: int, col: int, ch_code: int, attr: int) -> None:
        idx = (slice_id << 6) | (col & 0x3F)
        rom[idx] = ((attr & 0xF) << 8) | (ch_code & 0xFF)

    def put_slice_str(slice_id: int, col_start: int, width: int, text: str, attr: int) -> None:
        s_pad = text.ljust(width)[:width]
        for i, ch in enumerate(s_pad):
            put_slice_col(slice_id, col_start + i, ord(ch), attr)

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
    for pg in range(1, 13):
        s54 = page_strs[pg]
        put_slice_str(pg, 99, 48, s54[:48], C_CYAN)
        put_slice_str(pg, 147, 6, s54[48:54], C_GOLD)

    put_slice_str(13, 101, 35, "COMPUTE ECOSYSTEM - INITIALIZING   ", C_CYAN)
    put_slice_str(14, 101, 35, "COMPUTE ECOSYSTEM - 16/16 ENTRIES  ", C_GREEN)
    put_slice_str(15, 101, 35, "COMPUTE ECOSYSTEM - FAULT DETECTED ", C_RED)

    sub_left_init  = ["CC 5STG", "CC 4GRD", "CC LBA1", "CC/AT  ", "VF/EH  ", "CC 144B", "CC 5X5 ", "VF/CC  "]
    sub_left_ready = ["CC 120M", "CC 4GRD", "CC LBA1", "CC/AT  ", "VF/EH  ", "CC 144B", "CC 5X5 ", "VF/CC  "]
    sub_left_err   = ["ER HALT", "ER GRD ", "ER LBA ", "ER NUI ", "ER MAC ", "ER HREG", "ER WAVE", "ER ROM "]

    sub_right_ok   = ["CC 82/104 OP", "CC 3-PROC OK", "CC HDOT 14C ", "CC 33-CLK/B ", "EH P8 SEALED", "CC 700/700  ", "CC CRC32/28 ", "CC L9/SW-VM "]
    sub_right_err  = ["ER OPCODE   ", "ER KERNEL   ", "ER CODEX    ", "ER TIMING   ", "ER UNSEALED ", "ER GF5 OP   ", "ER HISAB    ", "ER LOADER   "]

    for mode_idx, (attr, glyph, l_list, r_list) in enumerate([
        (C_CYAN,  G_RNG, sub_left_init,  sub_right_ok),
        (C_GREEN, G_CHK, sub_left_ready, sub_right_ok),
        (C_RED,   G_ERR, sub_left_err,   sub_right_err),
    ]):
        for r_idx in range(8):
            sl = 16 + mode_idx * 8 + r_idx
            put_slice_col(sl, 99, glyph, attr)
            put_slice_str(sl, 117, 7, l_list[r_idx], attr)
            put_slice_col(sl, 126, glyph, attr)
            put_slice_str(sl, 141, 12, r_list[r_idx], attr)

    for st_mode, (attr, glyph, label) in enumerate([
        (C_DIM,    G_RNG, "WAITING     "),
        (C_YELLOW, G_RNG, "INITIALIZING"),
        (C_GREEN,  G_CHK, "READY       "),
        (C_RED,    G_ERR, "ERROR       "),
    ]):
        sl = 40 + st_mode
        for c0 in (32, 77):
            put_slice_col(sl, c0, glyph, attr)
            put_slice_col(sl, c0 + 1, 0x20, attr)
            put_slice_str(sl, c0 + 2, 12, label, attr)

    put_slice_str(44, 108, 20, "DISPLAY INITIALIZING", C_YELLOW)
    put_slice_str(44, 129, 8,  "STARTUP ",             C_YELLOW)
    put_slice_str(45, 108, 20, "DISPLAY READY       ", C_GREEN)
    put_slice_str(45, 129, 8,  "READY   ",             C_GREEN)
    put_slice_str(46, 108, 20, "DISPLAY ERROR       ", C_RED)
    put_slice_str(46, 129, 8,  "ERROR   ",             C_RED)

    put_slice_str(47, 130, 13, "STARTUP      ",   C_YELLOW)
    put_slice_str(47, 51,  15, "STARTUP        ", C_YELLOW)
    put_slice_str(48, 130, 13, "DISPLAY READY",   C_GREEN)
    put_slice_str(48, 51,  15, "DISPLAY READY  ", C_GREEN)
    put_slice_str(49, 130, 13, "DISPLAY ERROR",   C_RED)
    put_slice_str(49, 51,  15, "DISPLAY ERROR  ", C_RED)

    put_slice_str(50, 13,  12, "SYNCING     ", C_YELLOW)
    put_slice_str(50, 52,  10, "QUALIFYING",   C_YELLOW)
    put_slice_str(51, 133, 5,  "READY",        C_GREEN)
    put_slice_str(51, 13,  12, "ACTIVE      ", C_GREEN)
    put_slice_str(51, 52,  10, "LOCKED    ",   C_GREEN)
    put_slice_str(51, 62,  6,  "NONE  ",       C_GREEN)
    put_slice_str(51, 98,  3,  "NO ",          C_GREEN)
    put_slice_str(52, 133, 5,  "FAULT",        C_RED)
    put_slice_str(52, 13,  12, "FAULT       ", C_RED)
    put_slice_str(52, 52,  10, "UNLOCKED  ",   C_RED)
    put_slice_str(52, 62,  6,  "OVFL  ",       C_RED)
    put_slice_str(52, 98,  3,  "YES",          C_RED)

    for sv in (0, 1):
        for sh in (0, 1):
            for sg in (0, 1):
                sl = 53 + ((sv << 2) | (sh << 1) | sg)
                put_slice_str(sl, 99,  3, "PC:",   C_CYAN)
                put_slice_str(sl, 105, 4, " IN:",  C_CYAN)
                put_slice_str(sl, 117, 4, " CY:",  C_CYAN)
                put_slice_str(sl, 129, 4, " FL:",  C_CYAN)
                put_slice_str(sl, 135, 3, " G:",   C_CYAN)
                put_slice_str(sl, 138, 2, "ER" if sg else "OK", C_RED if sg else C_GREEN)
                put_slice_str(sl, 140, 1, " ",     C_CYAN)
                put_slice_str(sl, 141, 3, "HLT" if sh else "RUN", C_RED if sh else C_GREEN)
                put_slice_str(sl, 144, 5, " CDC:", C_CYAN)
                if not sv:
                    put_slice_str(sl, 149, 4, "WAIT", C_GOLD)
                elif sg:
                    put_slice_str(sl, 149, 4, "ERR ", C_RED)
                else:
                    put_slice_str(sl, 149, 4, "LIVE", C_GREEN)

    out_path = RTL_DIR / "boot_comp_rom.hex"
    out_path.write_text("".join(f"{w:03x}\n" for w in rom), encoding="ascii")
    print(f"Generated {out_path.name} ({len(rom)} x 12-bit words)")


def build_bg_and_emblem_roms() -> None:
    def calc_bg_x_flags(x: int) -> int:
        if x >= 1280:
            return 0
        col = x >> 3
        sx = x & 7
        b0 = 1 if (107 <= col <= 128) else 0
        b1 = 1 if ((col == 107 and sx == 0) or (col == 128 and sx == 7)) else 0
        in_a = (3 <= col <= 39)
        in_b = (42 <= col <= 78)
        in_c = (81 <= col <= 117)
        in_d = (120 <= col <= 156)
        b2 = 1 if (in_a or in_b or in_c or in_d) else 0
        b3 = 1 if in_c else 0
        b4 = 1 if ((col in (3, 42, 81, 120) and sx == 0) or (col in (39, 78, 117, 156) and sx == 7)) else 0
        b5 = 1 if ((3 <= col <= 94) or (97 <= col <= 156)) else 0
        b6 = 1 if ((col in (3, 97) and sx == 0) or (col in (94, 156) and sx == 7)) else 0
        b7 = 1 if (3 <= col <= 156) else 0
        return b0 | (b1 << 1) | (b2 << 2) | (b3 << 3) | (b4 << 4) | (b5 << 5) | (b6 << 6) | (b7 << 7)

    # Store at k = (x - 1) % 1650 so synchronous read on `h_count[10:0]` outputs flags(h_count)
    bg_x = [0] * 2048
    for k in range(1650):
        x_next = (k + 1) % 1650
        bg_x[k] = calc_bg_x_flags(x_next)

    out_bg_x = RTL_DIR / "boot_bg_x_rom.hex"
    out_bg_x.write_text("".join(f"{w:02x}\n" for w in bg_x), encoding="ascii")

    # boot_bg_y_rom.hex (1,024 x 8-bit) indexed by vla[9:0] (0..749):
    #   bits [3:0] : y_zone (0..15)
    #   bit 4      : ftr_top_line (y == 676)
    #   bit 5      : in_footer (y == 677..719)
    #   bit 6      : in_hero_y (y == 76..259)
    #   bit 7      : is_y75 (y == 75)
    bg_y = [0] * 1024
    for y in range(750):
        z = 0
        b4 = 0
        b5 = 0
        b6 = 1 if (76 <= y <= 259) else 0
        b7 = 1 if (y == 75) else 0
        if y in (0, 1):
            z = 1
        elif y in (62, 63):
            z = 2
        elif y in (11, 27):
            z = 3
        elif 12 <= y <= 26:
            z = 4
        elif 0 <= y <= 63:
            z = 5
        elif y == 320:
            z = 6
        elif y == 321:
            z = 7
        elif y == 407:
            z = 8
        elif 322 <= y <= 406:
            z = 9
        elif y in (424, 583):
            z = 10
        elif y == 444:
            z = 11
        elif 425 <= y <= 582:
            z = 12
        elif y in (592, 671):
            z = 13
        elif y == 610:
            z = 14
        elif 593 <= y <= 670:
            z = 15
        elif y == 676:
            b4 = 1
        elif 677 <= y <= 719:
            b5 = 1
        bg_y[y] = z | (b4 << 4) | (b5 << 5) | (b6 << 6) | (b7 << 7)

    out_bg_y = RTL_DIR / "boot_bg_y_rom.hex"
    out_bg_y.write_text("".join(f"{w:02x}\n" for w in bg_y), encoding="ascii")

    # boot_emblem_rom.hex (4,096 x 4-bit = 1 SP BSRAM) indexed by {v_count[5:0], h_count[5:0]}
    # Stored at {y[5:0], (x - 1)[5:0]} so synchronous read at (h_count - 1, v_count) outputs code at (h_count, v_count)
    emblem = [0] * 4096
    for y in range(18, 42):
        for x in range(28, 52):
            ex = (x - 28) - 12
            ey = (y - 18) - 12
            r2 = ex * ex + ey * ey
            abs_ed = abs(ex + ey)
            if r2 <= 18:
                code = 1 if r2 <= 6 else 2
            elif abs_ed <= 2 and r2 <= 132:
                code = 3 if ex < 0 else 4
            elif 36 <= r2 <= 80:
                code = 5 if ey < 0 else 6
            elif 80 < r2 <= 110:
                code = 4
            else:
                code = 0
            idx = ((y & 0x3F) << 6) | ((x - 1) & 0x3F)
            emblem[idx] = code

    out_emblem = RTL_DIR / "boot_emblem_rom.hex"
    out_emblem.write_text("".join(f"{w:01x}\n" for w in emblem), encoding="ascii")
    print(f"Generated {out_bg_x.name} (2048x8), {out_bg_y.name} (1024x8), {out_emblem.name} (4096x4)")


if __name__ == "__main__":
    build_text_and_cell_tag_roms()
    build_comp_rom()
    build_bg_and_emblem_roms()
