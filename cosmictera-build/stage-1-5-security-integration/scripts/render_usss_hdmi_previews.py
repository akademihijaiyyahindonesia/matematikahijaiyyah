#!/usr/bin/env python3
"""
Renders 1280x720 HDMI Frame PNGs for Stage 1.5 + USSS by taking the verified
Stage 1.5 golden frames and rendering the exact RTL Row 83 (y=664..671, cols 99..153)
COSMICTERA SECURITY MONITOR (USSS) telemetry panel using rtl/hcpu_font8x8.hex.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

BASE_DIR = Path("/Users/AMRA/hijaiyyah-mathematics/cosmictera-build")
S15_PREVIEWS = BASE_DIR / "stage-1-5-unified-soc" / "frame_previews"
USSS_DIR = BASE_DIR / "stage-1-5-security-integration"
RTL_DIR = USSS_DIR / "rtl"
OUT_DIR = USSS_DIR / "frame_previews"
OUT_DIR.mkdir(parents=True, exist_ok=True)

C_DIM = 0
C_WHITE = 1
C_GOLD = 2
C_CYAN = 3
C_GREEN = 4
C_YELLOW = 5
C_RED = 6
C_SUBTLE = 7

TEXT_PALETTE: dict[int, tuple[int, int, int]] = {
    0: (0x54, 0x6A, 0x82),
    1: (0xF2, 0xF6, 0xFA),
    2: (0xF0, 0xC8, 0x60),
    3: (0x30, 0xC0, 0xD0),
    4: (0x30, 0xD0, 0x70),
    5: (0xE0, 0xB0, 0x40),
    6: (0xE0, 0x50, 0x50),
    7: (0x88, 0x9C, 0xB4),
}


def load_font_bits(path: Path) -> list[int]:
    return [int(x, 16) for x in path.read_text(encoding="ascii").splitlines() if x.strip()]


def overlay_usss_row83(frame: np.ndarray, font_bits: list[int], mode: str) -> np.ndarray:
    """
    Overlay Row 83 (y = 664..671, cols 99..153) matching cosmictera_boot_compositor.v:
      "USSS P8:ACT KB:RDY HM:RDY JM:RDY V:AUTH RQ:01 FL:00 R:0"
    """
    out = frame.copy()
    is_err = mode == "error"
    is_ready = mode == "ready"

    segments: list[tuple[int, str, int]] = [
        (99, "USSS", C_GOLD),
        (103, " P8:", C_CYAN),
        (107, "ERR" if is_err else "ACT", C_RED if is_err else C_GREEN),
        (110, " KB:", C_CYAN),
        (114, "ERR" if is_err else "RDY", C_RED if is_err else C_GREEN),
        (117, " HM:", C_CYAN),
        (121, "ERR" if is_err else "RDY", C_RED if is_err else C_GREEN),
        (124, " JM:", C_CYAN),
        (128, "ERR" if is_err else "RDY", C_RED if is_err else C_GREEN),
        (131, " V:", C_CYAN),
        (134, "REJ!" if is_err else ("AUTH" if is_ready else "WAIT"), C_RED if is_err else (C_GREEN if is_ready else C_GOLD)),
        (138, " RQ:", C_CYAN),
        (142, "02" if is_err else ("01" if is_ready else "00"), C_WHITE),
        (144, " FL:", C_CYAN),
        (148, "01" if is_err else "00", C_RED if is_err else C_GREEN),
        (150, " R:", C_CYAN),
        (153, "5" if is_err else "0", C_RED if is_err else C_GREEN),
    ]

    r = 83
    y_base = r * 8  # y = 664..671 (inside Region 6 Event Console background [0x08, 0x10, 0x1D], border at y=671)
    # Clear cell background on y=664..670, x=99*8..154*8 while preserving bottom border at y=671
    out[y_base : y_base + 7, 99 * 8 : 154 * 8] = [0x08, 0x10, 0x1D]

    for c0, text, attr in segments:
        rgb = TEXT_PALETTE[attr]
        for idx, ch in enumerate(text):
            c = c0 + idx
            x_base = c * 8
            g_base = (ord(ch) & 0x7F) * 8
            for sy in range(7):  # sy=0..6 so y=671 border line remains untouched
                b = font_bits[g_base + sy]
                if b == 0:
                    continue
                for sx in range(8):
                    if (b >> (7 - sx)) & 1:
                        out[y_base + sy, x_base + sx] = rgb

    return out


def main() -> None:
    font_bits = load_font_bits(RTL_DIR / "hcpu_font8x8.hex")

    mapping = [
        ("frame_startup_1280x720.png", "frame_startup_usss_1280x720.png", "startup"),
        ("frame_ready_1280x720.png", "frame_ready_usss_1280x720.png", "ready"),
        ("frame_error_1280x720.png", "frame_error_usss_1280x720.png", "error"),
    ]
    for src_name, dst_name, mode in mapping:
        img = np.array(Image.open(S15_PREVIEWS / src_name).convert("RGB"), dtype=np.uint8)
        out_img = overlay_usss_row83(img, font_bits, mode)
        Image.fromarray(out_img).save(OUT_DIR / dst_name)
        Image.fromarray(out_img).save(OUT_DIR / src_name)
        print(f"[OK] Saved {OUT_DIR / dst_name}")

    for pg in range(1, 13):
        pg_name = f"frame_page_p{pg:02d}_1280x720.png"
        img = np.array(Image.open(S15_PREVIEWS / pg_name).convert("RGB"), dtype=np.uint8)
        out_img = overlay_usss_row83(img, font_bits, "ready")
        Image.fromarray(out_img).save(OUT_DIR / pg_name)
    print("[OK] Saved P01..P12 1280x720 HDMI frames with Row 83 USSS Security Monitor.")


if __name__ == "__main__":
    main()
