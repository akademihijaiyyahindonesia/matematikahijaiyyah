#!/usr/bin/env python3
"""Render pixel-accurate 1280x720 PNG frames of the CosmicTera NUI-Centered
Real-Time Computing & Physical Button / Fault Recovery HDMI Monitor.

Reads the exact hardware ROM files:
  - rtl/hcpu_font8x8.hex
  - rtl/hcpu_dashboard.hex
  - rtl/hcpu_dashboard_lower.hex
  - rtl/hcpu_nui_holo.hex
and applies the exact character/attribute overlays of `hcpu_compositor.v` +
`hcpu_hdmi_top.v` plus the 256x256 BSRAM NUI Holographic Brain engine.
"""

from pathlib import Path
import struct
import zlib

ROOT = Path("/Users/AMRA/hijaiyyah-mathematics")
RTL = ROOT / "rtl"
OUT_DIR = ROOT / "cosmictera-build" / "stage-1-5-unified-soc" / "nui_centered_monitor"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Exact RGB palette from rtl/hcpu_text_render.v
BG_RGB = (0x06, 0x0C, 0x16)
FG_PALETTE = {
    0: (0x58, 0x6E, 0x75),  # C_DIM
    1: (0xEE, 0xE8, 0xD5),  # C_WHITE
    2: (0x2A, 0xA1, 0x98),  # C_CYAN
    3: (0x85, 0x99, 0x00),  # C_GREEN
    4: (0xB5, 0x89, 0x00),  # C_YELLOW
    5: (0xDC, 0x32, 0x2F),  # C_RED
    6: (0x26, 0x8B, 0xD2),  # C_BLUE
    7: (0xCB, 0x4B, 0x16),  # C_GOLD
}


def load_font():
    lines = (RTL / "hcpu_font8x8.hex").read_text().splitlines()
    return [int(x.strip(), 16) for x in lines if x.strip()]


def load_rom(path: Path):
    lines = path.read_text().splitlines()
    return [int(x.strip(), 16) for x in lines if x.strip()]


def write_png(path: Path, width: int, height: int, rgb_bytes: bytearray):
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        row_start = y * stride
        raw.extend(rgb_bytes[row_start : row_start + stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def render_frame(
    font,
    upper_rom,
    lower_rom,
    holo_rom,
    *,
    state_str: str,
    state_at: int,
    guard_fault: bool,
    pc_hex: str,
    instr_hex: str,
    cycles_hex: str,
    flags_str: str,
    rtm_blocks: dict,
    holo_pulse_hi: bool = True,
    holo_is_fault: bool = False,
    l0_active: bool = True,
) -> bytearray:
    # Build 160x90 cell grid from Dual-BSRAM ROMs (exact rom_direct / rom_lower / rom_footer mapping)
    cells_ch = [0x20] * (160 * 90)
    cells_at = [0] * (160 * 90)

    for addr in range(14400):
        if addr < 6720:
            val = upper_rom[addr]
        elif addr < 13440:
            val = lower_rom[addr - 6720]
        else:
            val = upper_rom[addr - 6720]
        cells_ch[addr] = val & 0xFF
        cells_at[addr] = (val >> 8) & 0xF

    def put_str(row: int, col: int, s: str, at: int):
        base = row * 160 + col
        for i, ch in enumerate(s):
            cells_ch[base + i] = ord(ch)
            cells_at[base + i] = at

    # hcpu_compositor + rtm_state_override fields:
    # BLK_STATE (row 11, col 16 -> blk 111)
    put_str(11, 16, f"{state_str:<7}"[:7], state_at)
    # BLK_PC (row 12, col 16 -> blk 121): "0x0" + 3 hex digits
    put_str(12, 16, "0x0" + pc_hex[-3:], 1)
    # BLK_INSTR (row 13, col 16 -> blk 131): "0x" + 8 hex digits
    put_str(13, 16, "0x" + instr_hex[-8:], 2)
    # BLK_CYCLES (row 14, col 16 -> blk 141): "0x" + 8 hex digits
    put_str(14, 16, "0x" + cycles_hex[-8:], 1)
    # BLK_FLAGS (row 15, col 16 -> blk 151): 7 chars "Z N C O L G I"
    put_str(15, 16, f"{flags_str:<7}"[:7], 3)
    # BLK_GUARD (row 16, col 16 -> blk 161): "OK   " (green) or "FAULT" (red)
    if guard_fault:
        put_str(16, 16, "FAULT", 5)
    else:
        put_str(16, 16, "OK   ", 3)

    # Apply all rtm_blk 4-hex-digit overlays at pos 4..7 (col = (blk % 10)*16 + 4, row = blk // 10)
    for blk, (val16, at) in rtm_blocks.items():
        row = blk // 10
        col = (blk % 10) * 16 + 4
        put_str(row, col, f"{val16 & 0xFFFF:04X}", at)

    # Render 1280x720 RGB buffer
    width, height = 1280, 720
    rgb = bytearray(width * height * 3)

    # Pre-resolve holo palette
    def get_holo_rgb(nib: int):
        if nib == 1:
            return (0x0A, 0x1A, 0x3A)
        if nib == 2:
            return (0x14, 0x3E, 0x8C) if holo_pulse_hi else (0x10, 0x34, 0x78)
        if nib == 3:
            return (0x90, 0x28, 0x38) if holo_is_fault else ((0x20, 0x78, 0xF0) if holo_pulse_hi else (0x18, 0x64, 0xD8))
        if nib == 4:
            return (0xD0, 0x40, 0x50) if holo_is_fault else ((0x38, 0xC0, 0xFF) if holo_pulse_hi else (0x20, 0xA8, 0xF8))
        if nib == 5:
            return (0xFF, 0x58, 0x68) if holo_is_fault else (0x50, 0xF0, 0xFF)
        if nib == 6:
            return (0xC8, 0xFC, 0xFF)
        if nib == 7:
            return (0x0E, 0x68, 0x38)
        if nib == 8:
            return (0x28, 0xD8, 0x70) if l0_active else (0x1C, 0xB8, 0x60)
        if nib == 9:
            return (0x48, 0xFF, 0x98)
        if nib == 10:
            return (0x88, 0x58, 0x10)
        if nib == 11:
            return (0xF0, 0xB0, 0x30) if l0_active else (0xD8, 0x98, 0x20)
        if nib == 12:
            return (0xFF, 0xE0, 0x58)
        if nib == 13:
            return (0x78, 0x88, 0x98)
        if nib == 14:
            return (0xC0, 0xD0, 0xE0)
        if nib == 15:
            return (0xF4, 0xF8, 0xFF)
        return BG_RGB

    holo_lut = [get_holo_rgb(i) for i in range(16)]

    for y in range(height):
        cell_row = y >> 3
        font_row = y & 7
        row_cell_base = cell_row * 160
        in_holo_y = 208 <= y < 432
        rel_y = y - 208
        for cell_col in range(160):
            cell_idx = row_cell_base + cell_col
            ch = cells_ch[cell_idx] & 0x7F
            at = cells_at[cell_idx] & 0xF
            fg = FG_PALETTE.get(at, (0xEE, 0xE8, 0xD5))
            bits = font[(ch << 3) | font_row]
            x_base = cell_col << 3
            for px in range(8):
                x = x_base + px
                bit_on = (bits >> (7 - px)) & 1
                if bit_on:
                    r, g, b = fg
                elif in_holo_y and (464 <= x < 720):
                    rel_x = x - 464
                    h_addr = ((rel_y >> 1) << 6) | (rel_x >> 2)
                    h_byte = holo_rom[h_addr]
                    nib = (h_byte & 0xF) if ((rel_x >> 1) & 1) else ((h_byte >> 4) & 0xF)
                    if nib != 0:
                        r, g, b = holo_lut[nib]
                    else:
                        r, g, b = BG_RGB
                else:
                    r, g, b = BG_RGB
                idx = (y * width + x) * 3
                rgb[idx] = r
                rgb[idx + 1] = g
                rgb[idx + 2] = b

    return rgb


def main():
    font = load_font()
    upper_rom = load_rom(RTL / "hcpu_dashboard.hex")
    lower_rom = load_rom(RTL / "hcpu_dashboard_lower.hex")
    holo_rom = load_rom(RTL / "hcpu_nui_holo.hex")

    # Common live computation telemetry values from cosmictera_realtime_compute.hasm (Jim 0xE4 & Kha 0xE6)
    base_rtm = {
        # Panel A
        181: (0x4301, 2),  # OP/DST/S1 = 0x4301 (OP_HGRD H0, R1)
        191: (0x001D, 1),  # INST STEPS = 29 (0x001D)
        201: (0x0009, 3),  # LAST PRINT = 9 (HDOT=9)
        # Panel B (Hijaiyyah Math & Hybit 18D)
        114: (0x00E4, 3),  # LETTER OP = 0x00E4 (Jim)
        124: (0x0052, 3),  # CODEX OP  = 0x0052 (HDOT)
        134: (0x000B, 1),  # MATH OPS  = 11 (0x000B)
        144: (0x0070, 3),  # HNRM2(H0) = 112 (0x0070)
        154: (0x000A, 3),  # HDIST     = 10  (0x000A)
        164: (0x0009, 3),  # HDOT      = 9   (0x0009)
        # Panel C (CosmicTera Stack)
        158: (0x0008, 3),  # PRINT EVENTS = 8
        168: (0x0012, 3),  # UART TX BYTES = 18 (0x0012)
        # Zone 6 (NUI L0-L11 Layer Details)
        281: (0x0002, 3),  # L0 TITIK    = 2
        291: (0x0002, 3),  # L0 GARIS    = 2
        301: (0x0002, 3),  # L0 LENGKUNG = 2
        311: (0x0006, 3),  # L0 THETA    = 6
        321: (0x0006, 3),  # L0 RHO      = 6
        331: (0x0008, 2),  # L0 PRINTS   = 8
        # Zone 7B (Live Computation Event Monitor EV0..EV9)
        397: (0x0040, 1),  # EV0 BOOT PC = 0x0040
        398: (0x00E4, 2),  # EV0 OP      = 0x00E4
        407: (0x001D, 1),  # EV1 STEPS   = 0x001D
        408: (0x000B, 3),  # EV1 MATH    = 0x000B
        417: (0x0002, 3),  # EV2 TITIK   = 0x0002
        418: (0x0002, 3),  # EV2 GARIS   = 0x0002
        427: (0x0002, 3),  # EV3 LENGK   = 0x0002
        428: (0x0006, 3),  # EV3 THETA   = 0x0006
        437: (0x0006, 3),  # EV4 RHO     = 0x0006
        438: (0x0008, 2),  # EV4 CNT     = 0x0008
        447: (0x0070, 3),  # EV5 HNRM2   = 0x0070
        448: (0x000A, 3),  # EV5 HDIST   = 0x000A
        457: (0x0009, 3),  # EV6 HDOT    = 0x0009
        458: (0x0009, 3),  # EV6 LAST    = 0x0009
        467: (0x0012, 2),  # EV7 UARTB   = 0x0012
        468: (0x0008, 3),  # EV7 PRINTS  = 0x0008
        477: (0x0004, 1),  # EV8 FLAGS   = 0x0004 (FLAG_G=1)
        487: (0x0240, 1),  # EV9 FRAMES  = 0x0240
        # Footer Row 84
        844: (0x0240, 3),  # CDC FRAMES  = 0x0240
    }

    # 1. RUNNING State Frame
    rtm_running = dict(base_rtm)
    rtm_running.update({
        54:  (0x0000, 3),  # Header STATE=0 (RUNNING), EV=0 (NONE)
        55:  (0x0000, 2),  # Header S1/S2 counts
        288: (0x0000, 3),  # S1 RAW/SYN/DEB/CNT = 0000
        298: (0x0000, 3),  # S2 RAW/SYN/DEB/CNT = 0000
        328: (0x0000, 1),  # FSM STATE=0 (RUNNING), EV=0
        338: (0x0000, 2),  # PRE=0 -> POST=0
        348: (0x0000, 3),  # FLT=0, REC=0
    })
    rgb_run = render_frame(
        font, upper_rom, lower_rom, holo_rom,
        state_str="RUNNING", state_at=3, guard_fault=False,
        pc_hex="049", instr_hex="43010000", cycles_hex="0000018A",
        flags_str="- - - - - G -", rtm_blocks=rtm_running,
        holo_pulse_hi=True, holo_is_fault=False, l0_active=True,
    )
    write_png(OUT_DIR / "frame_nui_centered_running_1280x720.png", 1280, 720, rgb_run)

    # 2. S1 STOPPED State Frame (S1 pressed: USER STOP, STOPPED, GUARD: OK!)
    rtm_stopped = dict(base_rtm)
    rtm_stopped.update({
        54:  (0x0101, 3),  # Header STATE=1 (STOPPED), EV=1 (USER_STOP)
        55:  (0x0100, 2),  # S1 count=1, S2 count=0
        288: (0x0001, 4),  # S1 RAW=0, SYN=0, DEB=0, CNT=1
        298: (0x0000, 3),  # S2 RAW=0, SYN=0, DEB=0, CNT=0
        328: (0x0101, 1),  # FSM STATE=1 (STOPPED), EV=1 (USER_STOP)
        338: (0x0001, 2),  # PRE=0 (RUNNING) -> POST=1 (STOPPED)
        348: (0x0000, 3),  # FLT=0, REC=0 (Zero false GUARD FAULT!)
    })
    rgb_stop = render_frame(
        font, upper_rom, lower_rom, holo_rom,
        state_str="STOPPED", state_at=4, guard_fault=False,
        pc_hex="049", instr_hex="43010000", cycles_hex="0000018A",
        flags_str="- - - - - G -", rtm_blocks=rtm_stopped,
        holo_pulse_hi=False, holo_is_fault=False, l0_active=True,
    )
    write_png(OUT_DIR / "frame_nui_centered_s1_stopped_1280x720.png", 1280, 720, rgb_stop)

    # 3. S2 RESET / FAULT RECOVERY Frame (After S2 recovery -> READY / RUNNING, EV=FAULT_REC, REC=OK)
    rtm_rec = dict(base_rtm)
    rtm_rec.update({
        54:  (0x0604, 3),  # Header STATE=6 (READY), EV=4 (FAULT_REC)
        55:  (0x0101, 2),  # S1 count=1, S2 count=1
        288: (0x0001, 3),  # S1 CNT=1
        298: (0x0001, 2),  # S2 CNT=1
        328: (0x0604, 1),  # FSM STATE=6 (READY), EV=4 (FAULT_REC)
        338: (0x0406, 2),  # PRE=4 (FAULT) -> POST=6 (READY)
        348: (0x0021, 3),  # FLT=0, CODE=0, REC=2 (REC_OK_READY), RECCNT=1
    })
    rgb_rec = render_frame(
        font, upper_rom, lower_rom, holo_rom,
        state_str="READY  ", state_at=3, guard_fault=False,
        pc_hex="040", instr_hex="E4000000", cycles_hex="00000012",
        flags_str="- - - - - G -", rtm_blocks=rtm_rec,
        holo_pulse_hi=True, holo_is_fault=False, l0_active=True,
    )
    write_png(OUT_DIR / "frame_nui_centered_s2_recovery_1280x720.png", 1280, 720, rgb_rec)
    print("Rendered 3 1280x720 PNG frames in", OUT_DIR)


if __name__ == "__main__":
    main()
