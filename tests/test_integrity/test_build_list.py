"""
The build list, checked against the build.

A list of what is on is worth exactly as much as its weakest claim, and this
repository has watched a transcription and its guard drift together more than
once -- most recently the place-and-route numbers, where the test compared the
header's text against constants retyped beside it and both stayed still while
the design moved.

So nothing here compares prose to prose. Every figure in cosmictera-build/ is
recomputed from the thing it describes: the opcode tables from the opcode
module, the letter count from the master table, the bench count from the
Makefile, the utilisation from the wrapper header. If the build changes and the
list does not, these fail.
"""

from __future__ import annotations

import re
from pathlib import Path

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "cosmictera-build"
README = (FOLDER / "README.md").read_text(encoding="utf-8")
ON = (FOLDER / "ON.md").read_text(encoding="utf-8")
OFF = (FOLDER / "OFF.md").read_text(encoding="utf-8")
PKG = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
WRAPPER = (ROOT / "rtl" / "fpga" / "gowin" / "hcpu_gowin_top.v").read_text(encoding="utf-8")
TB_MAKEFILE = (ROOT / "rtl" / "tb" / "Makefile").read_text(encoding="utf-8")

PREFIXES = ("rtl/", "src/", "tests/", "docs/", "cosmictera/", "hijrah/",
            "kabah/", "matematika-hijaiyyah/", "cosmic-codex-jim/")


def _cited_paths(text: str) -> set[str]:
    """Repo paths named in backticks or as markdown links."""
    found = set(re.findall(r"`([^`\s]+)`", text))
    found |= set(re.findall(r"\]\(([^)]+)\)", text))
    return {p for p in found if p.startswith(PREFIXES) or p.startswith("../")}


def test_every_path_the_list_cites_exists() -> None:
    """A list that points at files which are gone is worse than no list: it
    reads as current."""
    missing = []
    for doc, text in (("README.md", README), ("ON.md", ON), ("OFF.md", OFF)):
        for cited in _cited_paths(text):
            base = FOLDER if cited.startswith("../") else ROOT
            if "*" in cited:
                # A glob stands for a family of files. One that matches
                # nothing is as broken a citation as a missing path.
                if not list(base.glob(cited)):
                    missing.append(f"{doc}: {cited} (matches nothing)")
            elif not (base / cited).resolve().exists():
                missing.append(f"{doc}: {cited}")
    assert not missing, f"cited paths that do not exist: {missing}"


# ── the machine ─────────────────────────────────────────────────


def test_the_opcode_counts_are_the_real_ones() -> None:
    total = len(list(OpCode))
    done = len(RTL_IMPLEMENTED)
    assert f"**{done} dari {total}**" in ON, (
        f"ON.md must say {done} of {total} opcodes are in RTL"
    )
    assert f"{total - done} opcode belum di RTL" in OFF


def test_off_names_exactly_the_opcodes_that_are_missing() -> None:
    """Naming them is the point. A count alone cannot be checked against
    anything, and a wrong name would survive a count."""
    missing = {o.name for o in OpCode if o not in RTL_IMPLEMENTED}
    block = OFF.split("70 dari 96")[1].split("```")[1]
    listed = set(re.findall(r"\b([A-Z][A-Z0-9_]{2,})\b", block))
    assert listed == missing, (
        f"only in OFF.md: {sorted(listed - missing)}; "
        f"only in the code: {sorted(missing - listed)}"
    )


def test_the_letters_are_whole_instructions_and_all_of_them_reach_rtl() -> None:
    letters = [o for o in OpCode if 0xE0 <= o.value <= 0xFB]
    assert len(letters) == len(MASTER_TABLE.all_entries()) == 28
    assert all(o in RTL_IMPLEMENTED for o in letters)
    assert "**28** (`0xE0`–`0xFB`), semuanya di RTL" in ON


def test_the_trap_and_register_figures_come_from_the_package() -> None:
    causes = int(re.search(r"`define\s+TRAP_CAUSES\s+(\d+)", PKG).group(1))
    depth = int(re.search(r"`define\s+STACK_DEPTH\s+(\d+)", PKG).group(1))
    assert f"**{causes} penyebab**" in ON
    assert f"{depth} entri" in ON
    assert f"{causes} penyebab trap" in README


# ── the benches ─────────────────────────────────────────────────


def test_the_bench_count_matches_the_makefile() -> None:
    body = TB_MAKEFILE.split("\nall:")[1].split("\n\n")[0]
    benches = set(re.findall(r"\bsim_\w+", body))
    assert f"{len(benches)} testbench" in README
    assert f"{len(benches)} bench" in ON


# ── the board, which is the part that is off ────────────────────


def test_fmax_is_not_claimed_as_on() -> None:
    """It was measured once and the design has since outgrown the board. The
    list must not carry the old number forward -- that is precisely the drift
    that put it here."""
    assert "90,14" not in ON, "ON.md quotes an Fmax that no longer holds"
    assert "Fmax HCPU kembali `EH`" in README
    assert "`EH`. Turun dari `CC`" in OFF


def test_the_utilisation_in_off_is_the_wrappers_own() -> None:
    rows = dict(
        (name, int(used.replace(",", "")))
        for name, used, _total in re.findall(
            r"^//\s+(\w+)\s+([\d,]+)\s*/\s*([\d,]+)\s+\d+%", WRAPPER, re.M
        )
    )
    for name, used in rows.items():
        quoted = f"{used:,}".replace(",", ".")
        assert quoted in OFF, f"{name} {quoted} is not the figure OFF.md carries"
    assert "no BELs remaining" in OFF and "no BELs remaining" in WRAPPER


def test_the_bisection_in_off_matches_the_wrappers_record() -> None:
    """Two places carry the table; they have to agree, and the wrapper is the
    one written next to the design."""
    def commits(text: str) -> list[str]:
        return re.findall(r"\b([0-9a-f]{7})\b", text)

    from_wrapper = commits(WRAPPER.split("Bisected")[1].split("One commit did it")[0])
    from_off = commits(OFF.split("Bisect, satu run")[1].split("**Satu komit")[0])
    assert from_wrapper == from_off, f"{from_wrapper} vs {from_off}"
    assert len(from_wrapper) == 6


# ── scope honesty ───────────────────────────────────────────────


def test_the_three_designed_components_are_sorted_correctly() -> None:
    """H-Kernel is built and runs; HFS and HOS are not. Putting all three in
    either column would be the easy lie."""
    assert "**H-Kernel**" in ON
    assert "HFS" not in ON and "HOS" not in ON
    assert "**HFS**" in OFF and "**HOS**" in OFF


def test_only_layer_three_is_said_to_carry_security() -> None:
    assert "satu-satunya pemikul keamanan" in ON
    assert "tidak ada di RTL" in ON


def test_the_kernels_own_limits_are_stated_where_it_is_claimed() -> None:
    """The kernel is in ON. Its gaps have to be reachable from there, or the
    entry overstates itself."""
    assert "dua proses tetap" in ON and "OFF.md" in ON
    assert "`PUSH` tidak dibatasi mode user" in OFF
