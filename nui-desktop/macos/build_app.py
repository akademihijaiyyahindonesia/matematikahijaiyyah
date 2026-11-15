#!/usr/bin/env python3
"""Build script for native macOS application bundle `CosmicTera NUI.app` (v1.5.0).

1. Generates aspect-ratio-preserving `.icns` icon and copies the official CosmicTera Chrome Orbit Logo
   into `Contents/Resources/` without distortion.
2. Compiles `nui-desktop/macos/Sources/CosmicTeraNUIApp.swift` with `swiftc` linking `SwiftUI`, `AppKit`, and `WebKit`.
3. Writes `Contents/Info.plist` for `com.cosmictera.nui.desktop` (v1.5.0).
4. Terminates any stale pre-1.5.0 `server.py` daemon recorded in `nui-desktop/data/active_service.json`.
"""
from __future__ import annotations

import json
import os
import plistlib
import shutil
import signal
import subprocess
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
MACOS_DIR = Path(__file__).resolve().parent
BUILD_DIR = MACOS_DIR / "build"
APP_BUNDLE = BUILD_DIR / "CosmicTera NUI.app"
LOGO_SRC = REPO_ROOT / "cosmictera" / "Logo CosmicTera Chrome Orbit Logo (1).png"
SWIFT_SRC = MACOS_DIR / "Sources" / "CosmicTeraNUIApp.swift"
ACTIVE_SERVICE_JSON = REPO_ROOT / "nui-desktop" / "data" / "active_service.json"


def make_square_icon_preserving_aspect(src_img: Image.Image, size: int) -> Image.Image:
    """Place official logo centered on a square transparent canvas without stretching."""
    canvas = Image.new("RGBA", (size, size), (6, 12, 22, 0))
    w, h = src_img.size
    scale = min(size / w, size / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    offset_x = (size - new_w) // 2
    offset_y = (size - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y), resized if resized.mode == "RGBA" else None)
    return canvas


def terminate_stale_daemon() -> None:
    """Terminate any pre-1.5.0 daemon recorded in active_service.json so v1.5.0 binds cleanly."""
    if not ACTIVE_SERVICE_JSON.exists():
        return
    try:
        info = json.loads(ACTIVE_SERVICE_JSON.read_text(encoding="utf-8"))
        ver = str(info.get("version") or "")
        old_pid = int(info.get("pid") or 0)
        if ver != "1.5.0" and old_pid > 0 and old_pid != os.getpid():
            os.kill(old_pid, signal.SIGTERM)
    except Exception:
        pass


def build_app() -> Path:
    contents_dir = APP_BUNDLE / "Contents"
    macos_bin_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    macos_bin_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy official logo & generate AppIcon.icns preserving exact proportions
    if LOGO_SRC.exists():
        shutil.copy2(LOGO_SRC, resources_dir / "CosmicTeraLogo.png")
        iconset_dir = BUILD_DIR / "AppIcon.iconset"
        iconset_dir.mkdir(parents=True, exist_ok=True)
        src_img = Image.open(LOGO_SRC).convert("RGBA")
        for sz in (16, 32, 64, 128, 256, 512):
            img1 = make_square_icon_preserving_aspect(src_img, sz)
            img1.save(iconset_dir / f"icon_{sz}x{sz}.png")
            img2 = make_square_icon_preserving_aspect(src_img, sz * 2)
            img2.save(iconset_dir / f"icon_{sz}x{sz}@2x.png")
        subprocess.run(
            ["/usr/bin/iconutil", "-c", "icns", str(iconset_dir), "-o", str(resources_dir / "AppIcon.icns")],
            check=False,
            capture_output=True,
        )

    # 2. Write Info.plist
    info_plist = {
        "CFBundleName": "CosmicTera NUI",
        "CFBundleDisplayName": "CosmicTera NUI Desktop",
        "CFBundleIdentifier": "com.cosmictera.nui.desktop",
        "CFBundleVersion": "1.5.0",
        "CFBundleShortVersionString": "1.5.0",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": "CosmicTeraNUI",
        "CFBundleIconFile": "AppIcon",
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    }
    with (contents_dir / "Info.plist").open("wb") as f:
        plistlib.dump(info_plist, f)

    # 2B. Write Entitlements.plist with com.apple.security.network.client = true
    entitlements_path = MACOS_DIR / "Entitlements.plist"
    entitlements_plist = {
        "com.apple.security.network.client": True,
        "com.apple.security.network.server": True,
        "com.apple.security.files.user-selected.read-write": True,
    }
    with entitlements_path.open("wb") as f:
        plistlib.dump(entitlements_plist, f)
    with (contents_dir / "Entitlements.plist").open("wb") as f:
        plistlib.dump(entitlements_plist, f)

    # 3. Compile SwiftUI + AppKit + WebKit binary with explicit deployment target (arm64-apple-macos14.0)
    bin_path = macos_bin_dir / "CosmicTeraNUI"
    subprocess.run(
        [
            "/usr/bin/swiftc",
            "-parse-as-library",
            "-target",
            "arm64-apple-macos14.0",
            str(SWIFT_SRC),
            "-o",
            str(bin_path),
            "-framework",
            "SwiftUI",
            "-framework",
            "AppKit",
            "-framework",
            "WebKit",
        ],
        check=True,
    )
    bin_path.chmod(0o755)
    subprocess.run(
        [
            "/usr/bin/codesign",
            "--force",
            "--deep",
            "--entitlements",
            str(entitlements_path),
            "--sign",
            "-",
            str(APP_BUNDLE),
        ],
        check=False,
        capture_output=True,
    )
    subprocess.run(
        [
            "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister",
            "-f",
            str(APP_BUNDLE),
        ],
        check=False,
        capture_output=True,
    )
    terminate_stale_daemon()
    print(f"Built native macOS app bundle: {APP_BUNDLE}")
    return APP_BUNDLE


if __name__ == "__main__":
    build_app()
