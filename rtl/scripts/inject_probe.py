#!/usr/bin/env python3
"""inject_probe.py — put a test process into a copy of an image, for a bench.

    inject_probe.py SHELL.hasm LABEL PROBE.hasm BASE > image.hex

Assembles SHELL.hasm, assembles PROBE.hasm at BASE, and replaces the first word
at LABEL with an absolute jump to BASE. Everything else in the shell image is
byte-for-byte what asm2hex.py emits for it.

Why a copy and not an edit: shell.hasm has no process that calls its own HFS
syscalls, and adding one would change what the shell does -- a design decision,
not a test. The bench needs a caller; the shipped image does not.

It refuses to overlap: if the probe would start inside the shell image, the
patched word would jump into the shell's own code, so that is an error rather
than a quiet corruption.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hijaiyyah.hisa.assembler import (  # noqa: E402
    assemble,
    assemble_line,
    collect_labels,
    expand_includes,
)

CODE_DEPTH = 4096


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    shell_path, label, probe_path, base_s = sys.argv[1:]
    base = int(base_s, 0)
    shell_p, probe_p = Path(shell_path), Path(probe_path)

    shell_src = shell_p.read_text(encoding="utf-8")
    shell = assemble(shell_src, base_dir=shell_p.parent)
    labels = collect_labels(expand_includes(shell_src.splitlines(), shell_p.parent))
    if label not in labels:
        sys.exit(f"inject_probe: {shell_p.name} has no label {label!r}")
    if base < len(shell):
        sys.exit(f"inject_probe: probe base {base:#x} lies inside the "
                 f"{len(shell)}-word shell image")

    probe = assemble(probe_p.read_text(encoding="utf-8"),
                     base_dir=probe_p.parent, base=base)
    if base + len(probe) > CODE_DEPTH:
        sys.exit(f"inject_probe: probe ends at {base + len(probe):#x}, past "
                 f"the {CODE_DEPTH}-word instruction memory")

    image = list(shell) + [0] * (base - len(shell)) + list(probe)
    image[labels[label]] = assemble_line(f"JMP {base}", {}, 0)
    for word in image:
        print(f"{word & 0xFFFFFFFF:08X}")


if __name__ == "__main__":
    main()
