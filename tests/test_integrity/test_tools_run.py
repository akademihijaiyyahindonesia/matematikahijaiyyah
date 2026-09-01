"""
The scripts under tools/, which had no coverage at all.

Two of the five were broken and said nothing useful about it.

codex_calculator.py imported `hijaiyyah.algebra.integral`, a module that has
never existed — the name is `aggregametric` — so it died on import. Ruff cannot
see this: a wrong import path is not a lint error.

csgi_pipeline.py looked for glyphs under data/kfgqpc_seal/, while the files sit
in data/kfgqpc/ and the GUI reads them from there. It reported "Done: 0/28 OK"
and exited successfully, so a caller had to read the number to notice that it
had processed nothing.

The glyph path is checked directly rather than by running the pipeline, which
takes over a minute.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
SRC = ROOT / "src"

SCRIPTS: List[Path] = sorted(TOOLS.glob("*.py"))
IDS = [p.name for p in SCRIPTS]


def test_tools_were_found() -> None:
    assert len(SCRIPTS) >= 4, f"only {len(SCRIPTS)} scripts found under tools/"


@pytest.mark.parametrize("script", SCRIPTS, ids=IDS)
def test_tool_imports(script: Path) -> None:
    """
    Import without executing __main__, which is enough to catch a module path
    that does not resolve.
    """
    name = f"_probe_{script.stem}"
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)

    original = list(sys.path)
    sys.path.insert(0, str(SRC))
    # dataclasses resolves a field's type through sys.modules[cls.__module__],
    # so the module has to be registered before its body runs.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        pass  # a script that parses argv and exits is fine
    finally:
        sys.modules.pop(name, None)
        sys.path[:] = original


# ── The glyph directory, which two files disagreed about ─────────

GLYPHS = ROOT / "data" / "kfgqpc" / "glyphs"


def test_glyph_directory_exists_where_the_code_looks() -> None:
    assert GLYPHS.is_dir(), f"missing {GLYPHS}"
    assert len(list(GLYPHS.glob("*.png"))) == 28, "expected one glyph per letter"


@pytest.mark.parametrize(
    "path",
    [
        Path("tools/csgi_pipeline.py"),
        Path("src/hijaiyyah/gui/tabs/csgi.py"),
        Path("setup_structure.py"),
    ],
    ids=["csgi_pipeline", "gui_csgi_tab", "setup_structure"],
)
def test_no_file_points_at_the_wrong_glyph_directory(path: Path) -> None:
    """
    `kfgqpc_seal` is the name that does not exist. Two files used it while a
    third used the real one, and only the third worked.
    """
    text = (ROOT / path).read_text(encoding="utf-8")
    assert "kfgqpc_seal" not in text, (
        f"{path} refers to data/kfgqpc_seal/, which does not exist — "
        "the glyphs are in data/kfgqpc/"
    )


# ── codex_calculator, the one that could not even import ─────────

def test_codex_calculator_computes_the_reference_identity() -> None:
    """Θ̂ = U + ρ for بسم, which is what the tool prints."""
    result = subprocess.run(
        [sys.executable, str(TOOLS / "codex_calculator.py")],
        capture_output=True,
        text=True,
        timeout=120,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, f"tool failed:\n{result.stderr}"
    assert "Θ̂=10" in result.stdout, result.stdout
    assert "Θ̂=U+ρ: True" in result.stdout, result.stdout


def test_integrity_benchmark_measures_the_two_claims_separately() -> None:
    """
    §IIIC.3.2.1 states "Validasi O(1) vs CRC O(n)" and never puts a number on
    it. tools/integrity_benchmark.py does, and keeps the method claim apart
    from the machine claim — conflating them overstates the case, because only
    the first grows with n.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "integrity_benchmark.py"),
         "--lengths", "1", "10", "100"],
        capture_output=True, text=True, check=True,
    )
    out = result.stdout
    assert "METODE" in out and "MESIN" in out
    assert "diukur" in out, "the HCPU column must be labelled as measured"

    # The method ratio must grow with n; the machine ratio must not.
    import re
    method = [float(m) for m in re.findall(r"(\d+)x$", out, re.M)][:3]
    assert method[0] < method[-1], "the O(1)-vs-O(n) advantage must grow with n"


def test_the_rv32i_reference_sequence_is_in_the_repository() -> None:
    """
    The RV32I side of the benchmark is a static count, not a measurement, so
    the sequence it counts has to be readable and disputable.
    """
    source = (ROOT / "rtl" / "reference" / "guard_g1_g4_t1_t2.rv32i.s")
    assert source.exists(), "the counted sequence must be in the repo"
    text = source.read_text(encoding="utf-8")
    instructions = [
        line for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
        and not line.strip().endswith(":")
    ]
    from tools.integrity_benchmark import RV32I_GUARD  # type: ignore[import-not-found]

    assert len(instructions) == RV32I_GUARD, (
        f"the sequence has {len(instructions)} instructions but the benchmark "
        f"counts {RV32I_GUARD}"
    )
