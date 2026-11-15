#!/usr/bin/env python3
"""
COSMICTERA Stage 1.2 — Official Boot Display Asset Generator & Golden Reference Model
Generates:
  1. rtl/logo_rle_rom.hex    (16,384 x 9-bit RLE ROM for 512x184 32-color Chrome Orbit Logo)
  2. rtl/logo_palette.vh     (32 x 24-bit RGB palette matching Chrome Silver, Metallic Gold, Emerald Green)
  3. rtl/boot_text_rom.hex   (4,096 x 12-bit static text + color attribute ROM for 160x90 grid)
  4. rtl/hcpu_font8x8.hex    (unmodified copy of repository 8x8 font ROM)
  5. logo_candidates_metrics.json (quantitative comparison of 4 logo ROM candidates)
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image

REPO_ROOT = Path("/Users/AMRA/hijaiyyah-mathematics")
LOGO_PATH = REPO_ROOT / "cosmictera" / "Logo CosmicTera Chrome Orbit Logo (1).png"
FONT_PATH = REPO_ROOT / "rtl" / "hcpu_font8x8.hex"

WORK_DIR = Path(__file__).resolve().parent
RTL_DIR = WORK_DIR / "rtl"
PREVIEWS_DIR = WORK_DIR / "frame_previews"
WORK_DIR.mkdir(parents=True, exist_ok=True)
RTL_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# 8-color text attribute indices
C_DIM, C_WHITE, C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BLUE, C_GOLD = range(8)

TEXT_PALETTE = {
    C_DIM:    (0x78, 0x90, 0xA8),
    C_WHITE:  (0xD8, 0xE4, 0xF0),
    C_CYAN:   (0x30, 0xC0, 0xD0),
    C_GREEN:  (0x30, 0xD0, 0x70),
    C_YELLOW: (0xE0, 0xB0, 0x40),
    C_RED:    (0xE0, 0x50, 0x50),
    C_BLUE:   (0x40, 0x80, 0xE0),
    C_GOLD:   (0xF0, 0xC8, 0x60),
}

# Control glyphs verified from rtl/hcpu_font8x8.hex
G_CHK = 0x01  # checkmark
G_ERR = 0x02  # cross / X
G_RNG = 0x03  # ring / initializing
G_DOT = 0x04  # solid dot / bullet
G_BLK = 0x05  # solid block

VALID_ASCII = (
    set(range(1, 6))
    | {0x20, 0x25, 0x27, 0x28, 0x29, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F}
    | set(range(ord("0"), ord("9") + 1))
    | {0x3A}
    | set(range(ord("A"), ord("Z") + 1))
)

BG_RGB = np.array([6, 12, 22], dtype=np.float32)  # #060C16


def load_font_bits() -> list[int]:
    lines = FONT_PATH.read_text(encoding="ascii").splitlines()
    assert len(lines) == 1024
    return [int(x, 16) for x in lines]


def kmeans_palette(fg_pixels: np.ndarray, n_colors: int, seed: int = 42, iters: int = 35) -> np.ndarray:
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(fg_pixels), size=min(14000, len(fg_pixels)), replace=False)
    sample = fg_pixels[idx]
    anchors = [
        [242, 246, 250],  # bright chrome highlight
        [185, 198, 212],  # chrome silver
        [120, 136, 154],  # brushed steel
        [68, 82, 98],     # dark steel
        [246, 206, 95],   # bright metallic gold
        [214, 155, 44],   # rich gold
        [152, 98, 22],    # bronze shadow
        [45, 205, 115],   # bright emerald green
        [20, 145, 78],    # mid emerald green
        [10, 82, 46],     # deep emerald shadow
        [10, 16, 28],     # interior dark contour
    ]
    n_rand = max(0, n_colors - len(anchors))
    if n_rand > 0:
        rand_centers = sample[rng.choice(len(sample), size=n_rand, replace=False)]
        centers = np.vstack([np.array(anchors[:n_colors], dtype=np.float32), rand_centers])
    else:
        centers = np.array(anchors[:n_colors], dtype=np.float32)
    for _ in range(iters):
        dists = ((sample[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        for k in range(n_colors):
            m = labels == k
            if m.any():
                centers[k] = sample[m].mean(axis=0)
    lum = 0.299 * centers[:, 0] + 0.587 * centers[:, 1] + 0.114 * centers[:, 2]
    order = np.argsort(lum)
    return np.clip(np.round(centers[order]), 0, 255).astype(np.uint8)


def encode_rle_9bit(idx_map: np.ndarray) -> list[int]:
    words: list[int] = []
    h, w = idx_map.shape
    for y in range(h):
        row = idx_map[y]
        x = 0
        while x < w:
            c = int(row[x])
            run = 1
            while x + run < w and int(row[x + run]) == c:
                run += 1
            x += run
            if c == 0:
                while run >= 16:
                    k = min(16, run // 16)
                    words.append((31 << 4) | (k - 1))
                    run -= k * 16
                if run > 0:
                    words.append((0 << 4) | (run - 1))
            else:
                while run > 0:
                    step = min(16, run)
                    words.append((c << 4) | (step - 1))
                    run -= step
    return words


def decode_rle_9bit(words: list[int], w: int, h: int) -> np.ndarray:
    out = np.zeros(w * h, dtype=np.uint8)
    pos = 0
    for word in words:
        code = (word >> 4) & 0x1F
        cnt = (word & 0x0F) + 1
        if code == 31:
            run = cnt * 16
            if pos + run > w * h:
                run = max(0, w * h - pos)
            out[pos:pos + run] = 0
            pos += run
        else:
            if pos + cnt > w * h:
                cnt = max(0, w * h - pos)
            out[pos:pos + cnt] = code
            pos += cnt
        if pos >= w * h:
            break
    return out.reshape((h, w))


def build_logo_assets() -> tuple[np.ndarray, np.ndarray, list[int], dict]:
    raw_bytes = LOGO_PATH.read_bytes()
    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
    assert sha256_hex == "8bb2bc13577b1c06a9e19edce0ea9a3076b1eee1ce6c57706b0eef2b9ddf8ead"

    im = Image.open(LOGO_PATH)
    arr = np.array(im)
    a = arr[:, :, 3]
    ys, xs = np.where(a >= 8)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    cropped = im.crop((x0, y0, x1 + 1, y1 + 1))

    candidates_report = []

    def eval_direct(name: str, w: int, h: int, n_fg: int, bpp: int):
        resized = np.array(cropped.resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32)
        alpha = resized[:, :, 3] / 255.0
        fg_mask = resized[:, :, 3] >= 36
        comp = resized[:, :, :3] * alpha[:, :, None] + BG_RGB[None, None, :] * (1.0 - alpha[:, :, None])
        comp_u8 = np.clip(np.round(comp), 0, 255).astype(np.uint8)
        pal_fg = kmeans_palette(comp[fg_mask], n_fg)
        full_pal = np.vstack([BG_RGB.astype(np.uint8)[None, :], pal_fg])
        dists = ((comp[fg_mask][:, None, :] - pal_fg[None, :, :].astype(np.float32)) ** 2).sum(axis=2)
        idx_map = np.zeros((h, w), dtype=np.uint8)
        idx_map[fg_mask] = dists.argmin(axis=1).astype(np.uint8) + 1
        recon = full_pal[idx_map]
        mse = float(np.mean((comp_u8.astype(np.float32) - recon.astype(np.float32)) ** 2))
        psnr = float(10.0 * np.log10((255.0 ** 2) / mse))
        mae = float(np.mean(np.abs(comp_u8[fg_mask].astype(np.float32) - recon[fg_mask].astype(np.float32))))
        bits = w * h * bpp
        bsrams = int(np.ceil(bits / 16384.0))
        candidates_report.append({
            "name": name,
            "dimensions": f"{w}x{h}",
            "palette_colors": n_fg + 1,
            "encoding": f"Direct Indexed {bpp}-bit Bitmap",
            "rom_words": w * h,
            "rom_bits": bits,
            "bsram_blocks": bsrams,
            "psnr_db": round(psnr, 2),
            "fg_mae": round(mae, 2),
        })
        return idx_map, full_pal, comp_u8

    eval_direct("Candidate B (480x170 16-Color Direct)", 480, 170, 15, 4)
    eval_direct("Candidate C (512x184 16-Color Direct)", 512, 184, 15, 4)
    idx_32, pal_32, comp_32 = eval_direct("Candidate D (512x184 32-Color Direct)", 512, 184, 30, 5)

    # Candidate A: 512x184 32-Color (30 fg + 1 transparent + 1 skip16 code) with Viterbi RLE optimization
    h, w = 184, 512
    pal_f = pal_32.astype(np.float32)
    comp_f = comp_32.astype(np.float32)
    lam = 720.0
    v_map = np.zeros_like(idx_32)
    for y in range(h):
        row_idx = idx_32[y]
        row_rgb = comp_f[y]
        dp = np.zeros((w, 31), dtype=np.float32)
        back = np.zeros((w, 31), dtype=np.int32)
        costs = ((row_rgb[:, None, :] - pal_f[None, :, :]) ** 2).sum(axis=2)
        trans = (row_idx == 0)
        costs[trans, 1:] = 1e9
        costs[~trans, 0] = 1e9
        dp[0] = costs[0]
        for x in range(1, w):
            prev = dp[x - 1]
            min_prev_idx = int(prev.argmin())
            min_prev_val = prev[min_prev_idx]
            stay = prev
            switch = min_prev_val + lam
            use_switch = switch < stay
            dp[x] = costs[x] + np.where(use_switch, switch, stay)
            back[x] = np.where(use_switch, min_prev_idx, np.arange(31))
        c = int(dp[w - 1].argmin())
        for x in range(w - 1, -1, -1):
            v_map[y, x] = c
            c = back[x, c]

    rle_words = encode_rle_9bit(v_map)
    assert len(rle_words) <= 16384, f"RLE words {len(rle_words)} exceeds 16384"
    dec_map = decode_rle_9bit(rle_words, w, h)
    assert np.array_equal(v_map, dec_map), "RLE roundtrip mismatch!"

    rec_a = pal_32[v_map]
    mse_a = float(np.mean((comp_f - rec_a.astype(np.float32)) ** 2))
    psnr_a = float(10.0 * np.log10((255.0 ** 2) / mse_a))
    fg_m = v_map > 0
    mae_a = float(np.mean(np.abs(comp_f[fg_m] - rec_a[fg_m].astype(np.float32))))

    candidates_report.insert(0, {
        "name": "Candidate A (Selected: 512x184 32-Color 9-bit RLE)",
        "dimensions": "512x184",
        "palette_colors": 32,
        "encoding": "Streaming 9-bit RLE (5b code + 4b run, code 31 = 16x transparent skip)",
        "rom_words_used": len(rle_words),
        "rom_depth_allocated": 16384,
        "rom_bits_used": len(rle_words) * 9,
        "rom_bits_allocated": 16384 * 9,
        "bsram_blocks": 8,
        "psnr_db": round(psnr_a, 2),
        "fg_mae": round(mae_a, 2),
    })

    # Pad RLE words to 16,384 entries with 0x1FF (long transparent skip)
    padded_words = list(rle_words) + [0x1FF] * (16384 - len(rle_words))
    rle_hex_path = RTL_DIR / "logo_rle_rom.hex"
    rle_hex_path.write_text("".join(f"{wrd:03x}\n" for wrd in padded_words), encoding="ascii")

    # Write 32-entry palette include file for Verilog
    pal_lines = [
        "// logo_palette.vh - Generated by build_boot_ui_assets.py from official Chrome Orbit Logo",
        "// 31 colors (0 = transparent background #060C16, 1..30 = Chrome/Gold/Emerald centroids)",
    ]
    for idx_c in range(31):
        r, g, b = int(pal_32[idx_c, 0]), int(pal_32[idx_c, 1]), int(pal_32[idx_c, 2])
        pal_lines.append(f"            5'd{idx_c:2d}: logo_rgb = 24'h{r:02x}{g:02x}{b:02x};")
    pal_lines.append("            default: logo_rgb = 24'h060c16;")
    (RTL_DIR / "logo_palette.vh").write_text("\n".join(pal_lines) + "\n", encoding="ascii")

    # Save candidate logo comparison PNGs for visual inspection
    Image.fromarray(rec_a).save(PREVIEWS_DIR / "logo_512x184_32color_rle.png")

    metrics_info = {
        "master_file": str(LOGO_PATH),
        "file_size_bytes": len(raw_bytes),
        "sha256": sha256_hex,
        "dimensions": "1774x887",
        "color_mode": "RGBA",
        "crop_bbox_alpha_ge_8": [x0, y0, x1, y1],
        "rle_words_used": len(rle_words),
        "rle_words_capacity": 16384,
        "candidates": candidates_report,
    }
    (WORK_DIR / "logo_candidates_metrics.json").write_text(json.dumps(metrics_info, indent=2), encoding="utf-8")
    return v_map, pal_32, padded_words, metrics_info


# 22 active text rows on the 160x90 character grid mapped to compact ROM rows 0..21
# Row 23 in ROM is reserved as all-blank (0x020) for all non-text scanline rows.
ACTIVE_TEXT_ROWS = [
    2,   # ROM row 0:  Region 1 Header primary
    4,   # ROM row 1:  Region 1 Header secondary
    20,  # ROM row 2:  Region 2 Fallback banner (only shown if logo_rom_ok == 0)
    34,  # ROM row 3:  Region 2 Hero subtitle 1
    36,  # ROM row 4:  Region 2 Hero subtitle 2
    41,  # ROM row 5:  Region 3 Metric card headers
    44,  # ROM row 6:  Region 3 Metric primary values
    46,  # ROM row 7:  Region 3 Metric secondary info
    48,  # ROM row 8:  Region 3 Metric live status badges
    54,  # ROM row 9:  Region 4 & Region 5 panel headers
    57,  # ROM row 10: Region 4 Stages 01 & 06 | Region 5 subtitle
    60,  # ROM row 11: Region 4 Stages 02 & 07 | Region 5 Domain row 1
    63,  # ROM row 12: Region 4 Stages 03 & 08 | Region 5 Domain row 2
    66,  # ROM row 13: Region 4 Stages 04 & 09 | Region 5 Domain row 3
    69,  # ROM row 14: Region 4 Stages 05 & 10 | Region 5 Domain row 4
    71,  # ROM row 15: Region 4 Sequence note  | Region 5 Domain row 5
    75,  # ROM row 16: Region 6 Event Console header
    77,  # ROM row 17: Region 6 Events 01 & 04
    79,  # ROM row 18: Region 6 Events 02 & 05
    81,  # ROM row 19: Region 6 Events 03 & 06
    82,  # ROM row 20: Region 6 Event Console summary
    85,  # ROM row 21: Region 7 Footer (y = 680..687, 32 px bottom margin)
]
SCREEN_ROW_TO_ROM_ROW = {r: i for i, r in enumerate(ACTIVE_TEXT_ROWS)}
BLANK_ROM_ROW = 23


SCREEN_ROW_TO_ROM_ROW[56] = 22
SCREEN_ROW_TO_ROM_ROW[59] = 23
SCREEN_ROW_TO_ROM_ROW[61] = 24
# Screen rows 65 & 67 (Region 5 cols >= 96) share ROM rows 11 (row 60) & 13 (row 66)
SCREEN_ROW_TO_ROM_ROW[65] = 11
SCREEN_ROW_TO_ROM_ROW[67] = 13


def build_static_text_rom() -> list[tuple[int, int]]:
    """Build 4,096 x 12-bit ROM (25 rows of 160 cols + padding to 4096)."""
    cells = [(0x20, C_DIM)] * 4096

    def put(screen_row: int, col: int, text: str, attr: int = C_DIM) -> None:
        rom_r = SCREEN_ROW_TO_ROM_ROW[screen_row]
        for i, ch in enumerate(text):
            code = ord(ch)
            assert code in VALID_ASCII, f"Invalid glyph {ch!r} (0x{code:02x}) in {text!r}"
            c = col + i
            assert 0 <= c < 160
            cells[rom_r * 160 + c] = (code, attr)

    def put_glyph(screen_row: int, col: int, code: int, attr: int = C_DIM) -> None:
        assert code in VALID_ASCII
        rom_r = SCREEN_ROW_TO_ROM_ROW[screen_row]
        cells[rom_r * 160 + col] = (code, attr)

    # ── Region 1: Header (rows 2, 4) ─────────────────────────────
    put(2, 8, "COSMICTERA", C_GOLD)
    put(2, 20, "-", C_DIM)
    put(2, 22, "OFFICIAL BOOT DISPLAY SUBSYSTEM", C_WHITE)
    # Col 108..127 is overlaid dynamically by compositor with status badge
    put(2, 108, "DISPLAY READY       ", C_GREEN)
    put(2, 134, "BUILD CT-1.2-8C70", C_WHITE)

    put(4, 8, "NATURAL UNIVERSAL INTELLIGENCE", C_CYAN)
    put(4, 108, "NODE: STANDALONE HDMI SLOT 2", C_DIM)
    put(4, 138, "REV 8C70989B", C_DIM)

    # ── Region 2: Hero Logo Fallback & Subtitles (rows 20, 34, 36) ─
    put(20, 56, "COSMICTERA CHROME ORBIT LOGO ROM FAULT - TEXT FALLBACK", C_RED)
    put(34, 57, "HIJAIYYAH MATHEMATICAL COMPUTING ARCHITECTURE", C_WHITE)
    put(36, 64, "---", C_GOLD)
    put(36, 68, "COMPUTING ECOSYSTEM", C_GREEN)
    put(36, 88, "---", C_GOLD)

    # ── Region 3: Live System Metrics (rows 41, 44, 46, 48) ──────
    # Panel A (cols 3..39), Panel B (cols 42..78), Panel C (cols 81..117), Panel D (cols 120..156)
    put_glyph(41, 5, G_DOT, C_CYAN)
    put(41, 7, "PANEL A: VIDEO MODE", C_CYAN)
    put_glyph(41, 44, G_DOT, C_CYAN)
    put(41, 46, "PANEL B: PIXEL CLOCK", C_CYAN)
    put_glyph(41, 83, G_DOT, C_CYAN)
    put(41, 85, "PANEL C: BOOT ELAPSED", C_CYAN)
    put_glyph(41, 122, G_DOT, C_CYAN)
    put(41, 124, "PANEL D: RENDERER", C_CYAN)

    put(44, 5, "1280X720 60HZ", C_WHITE)
    put(44, 44, "74.25 MHZ CFG", C_WHITE)
    put(44, 83, "00:00", C_GOLD)
    put(44, 89, "(00:00:00)", C_WHITE)
    put(44, 122, "FONT 8X8 : READY", C_GREEN)

    put(46, 5, "FRAME: 1650X750P", C_DIM)
    put(46, 44, "RPLL 371.25 / DIV 5", C_DIM)
    put(46, 83, "27.000 MHZ HW TICK", C_DIM)
    put(46, 122, "LOGO RLE : READY", C_GREEN)

    put(48, 5, "STATUS: ACTIVE      ", C_GREEN)
    put(48, 44, "STATUS: LOCKED      ", C_GREEN)
    put(48, 83, "COUNTER: MONOTONIC  ", C_GREEN)
    put(48, 122, "SCREEN: DISPLAY READY", C_GREEN)

    # ── Region 4 (cols 3..94) & Region 5 (cols 97..156) (rows 54..71) ──
    put_glyph(54, 5, G_DOT, C_GOLD)
    put(54, 7, "DISPLAY NODE BOOT SEQUENCE (10 REAL HARDWARE STAGES)", C_WHITE)
    put_glyph(54, 99, G_DOT, C_GOLD)
    put(54, 101, "COMPUTE ECOSYSTEM - 16/16 ENTRIES  ", C_GREEN)

    # 10 Stages in Region 4: Left column (cols 5..46, stages 1..5), Right column (cols 50..91, stages 6..10)
    # Status field for left col is at col 32..45 (14 chars), right col is at col 77..90 (14 chars)
    stages_left = [
        (57, "01. REFERENCE CLOCK"),
        (60, "02. PLL LOCK"),
        (63, "03. PIXEL CLOCK"),
        (66, "04. CLKDIV"),
        (69, "05. TMDS SERIALIZER"),
    ]
    stages_right = [
        (57, "06. VIDEO TIMING"),
        (60, "07. FONT ROM"),
        (63, "08. LOGO RENDERER"),
        (66, "09. PIXEL COMPOSITOR"),
        (69, "10. VIDEO OUTPUT"),
    ]
    for r, label in stages_left:
        put(r, 5, label, C_CYAN)
        put_glyph(r, 32, G_CHK, C_GREEN)
        put(r, 34, "READY       ", C_GREEN)
    for r, label in stages_right:
        put(r, 50, label, C_CYAN)
        put_glyph(r, 77, G_CHK, C_GREEN)
        put(r, 79, "READY       ", C_GREEN)

    put(71, 5, "RESET ORDER: RPLL QUAL 2MS - CLKDIV.RESETN - OSER10.RESET - TIMING", C_DIM)

    # Region 5: Expanded 16-Entry Compute Ecosystem & Live 87-Bit Telemetry (Stage 1.4)
    put(56, 99, "PC:1A4 IN:4E010200 CY:0002C1C9 FL:04 G:OK RUN CDC:LIVE", C_CYAN)
    domains = [
        (57, "HCPU",            "CC 120M", "HISA",         "CC 82/104 OP"),
        (59, "HIJAIYYAH CELLS", "CC 4GRD", "HOS",          "CC 3-PROC OK"),
        (61, "HFS",             "CC LBA1", "HMCL",         "CC HDOT 14C "),
        (63, "NUI",             "CC/AT  ", "JAMRAH",       "CC 33-CLK/B "),
        (65, "KA'BAH",          "VF/EH  ", "PORTAL 8888",  "EH P8 SEALED"),
        (67, "HYBIT 18D",       "CC 144B", "HIJRAH GF(5)", "CC 700/700  "),
        (69, "CODEX JIM/J-MAC", "CC 5X5 ", "HISAB ENGINE", "CC CRC32/28 "),
        (71, "HM-28/SIX GUARD", "VF/CC  ", "HPG1 / HCVM",  "CC L9/SW-VM "),
    ]
    for r, d_left, b_left, d_right, b_right in domains:
        put_glyph(r, 99, G_CHK, C_GREEN)
        put(r, 101, d_left, C_WHITE)
        put(r, 117, b_left, C_GREEN)
        put_glyph(r, 126, G_CHK, C_GREEN)
        put(r, 128, d_right, C_WHITE)
        put(r, 141, b_right, C_GREEN)

    # ── Region 6: Event Console (rows 75, 77, 79, 81, 83) ────────
    put_glyph(75, 5, G_DOT, C_GOLD)
    put(75, 7, "HARDWARE EVENT CONSOLE", C_WHITE)
    put(75, 32, "(FIFO DEPTH: 06/08  OVERFLOW: NONE  )", C_CYAN)
    put(75, 99, "CLOCK DOMAIN: 27MHZ REF - 74.25MHZ PIXEL CDC", C_DIM)

    # Left events (cols 5..76), Right events (cols 82..153)
    put(77, 5,  "00:00:00  EV01 REF CLK 27.000 MHZ INPUT        OK", C_GREEN)
    put(79, 5,  "00:00:00  EV02 RPLL 371.25 MHZ 2MS QUAL        LOCKED", C_GREEN)
    put(81, 5,  "00:00:00  EV03 CLKDIV DIV5 74.25 MHZ RELEASE   READY", C_GREEN)

    put(77, 82, "00:00:00  EV04 OSER10 TMDS LANES RELEASE       ACTIVE", C_GREEN)
    put(79, 82, "00:00:00  EV05 VESA 1280X720P60 TIMING SYNC    LOCKED", C_GREEN)
    put(81, 82, "00:00:00  EV06 BOOT UI DISPLAY STATE           READY", C_GREEN)

    put(82, 5,  "LAST TRANSITION: ALL 10 DISPLAY STAGES VERIFIED - VIDEO OUTPUT ACTIVE", C_CYAN)

    # ── Region 7: Footer (row 85, y = 680..687, 32 px bottom margin) ──
    put(85, 4,   "COSMICTERA", C_GOLD)
    put(85, 17,  "TANG NANO 20K GW2AR-18C", C_CYAN)
    put(85, 44,  "STATE: DISPLAY READY   ", C_GREEN)
    put(85, 72,  "RELOCKS: 00", C_WHITE)
    put(85, 88,  "FIFO OVF: NO ", C_GREEN)
    put(85, 106, "PIN88 PAGE: 00", C_WHITE)
    put(85, 124, "STAGE 1.4 BOOT UI (8C70989B)", C_DIM)

    rom_hex_path = RTL_DIR / "boot_text_rom.hex"
    rom_hex_path.write_text("".join(f"{(a << 8) | ch:03x}\n" for ch, a in cells), encoding="ascii")
    return cells


def main() -> None:
    shutil.copyfile(FONT_PATH, RTL_DIR / "hcpu_font8x8.hex")
    v_map, pal_32, rle_words, metrics = build_logo_assets()
    cells = build_static_text_rom()
    print(f"Logo RLE ROM generated: { metrics['rle_words_used'] } / 16384 9-bit words, PSNR = {metrics['candidates'][0]['psnr_db']} dB")
    print(f"Boot Text ROM generated: {len(cells)} 12-bit cells ({len(ACTIVE_TEXT_ROWS)} active text rows)")


if __name__ == "__main__":
    main()
