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
CHECKLIST = (FOLDER / "CHECKLIST.md").read_text(encoding="utf-8")
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
    for doc, text in (("README.md", README), ("ON.md", ON), ("OFF.md", OFF),
                      ("CHECKLIST.md", CHECKLIST)):
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
    block = OFF.split("opcode belum di RTL")[1].split("```")[1]
    listed = set(re.findall(r"\b([A-Z][A-Z0-9_]{2,})\b", block))
    assert listed == missing, (
        f"only in OFF.md: {sorted(listed - missing)}; "
        f"only in the code: {sorted(missing - listed)}"
    )


def test_the_letters_are_whole_instructions_and_all_of_them_reach_rtl() -> None:
    """RTL_IMPLEMENTED listing them is not evidence -- it is a declaration,
    and for a while it was a false one: no bench executed a letter opcode, so
    a duplicate `default:` left all twenty-eight writing nothing while every
    suite passed. The claim now has to point at the bench that runs them."""
    letters = [o for o in OpCode if 0xE0 <= o.value <= 0xFB]
    assert len(letters) == len(MASTER_TABLE.all_entries()) == 28
    assert all(o in RTL_IMPLEMENTED for o in letters)
    assert "**28** (`0xE0`–`0xFB`), dijalankan di pipeline" in ON
    assert "rtl/tb/tb_hcpu_letters.v" in ON
    bench = (ROOT / "rtl" / "tb" / "tb_hcpu_letters.v").read_text(encoding="utf-8")
    assert "112" in bench and "10814" in bench


def test_the_codex_case_has_exactly_one_default() -> None:
    """Verilog allows one, and simulators do not agree on which of two wins.
    iverilog took the trailing one, so the letters were dead in hardware and
    verilator refused the file -- which is why the RTL lint had been failing."""
    execute = (ROOT / "rtl" / "hcpu_execute.v").read_text(encoding="utf-8")
    case_body = execute.split("codex_gpr  = {`XLEN{1'b0}};")[1].split("endcase")[0]
    # Count case items, not the word: the comment above the surviving default
    # quotes `default: ;` while explaining what went wrong.
    items = [ln.strip() for ln in case_body.splitlines()
             if ln.strip().startswith("default:")]
    assert len(items) == 1, f"the codex case has {len(items)} defaults: {items}"
    assert "if (is_letter)" in items[0]


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
    assert "OFF.md" in ON
    # The book gives H-Kernel four responsibilities. Two run. Claiming the
    # component without naming the split is the overstatement this catches.
    for missing in ("I/O", "daemon guard"):
        assert missing in ON, f"ON.md stops naming what the kernel lacks: {missing}"
    assert "**empat** tanggung jawab" in ON
    spec = (ROOT / "docs" / "hybit_pipeline_spec.md").read_text(encoding="utf-8")
    row = next(ln for ln in spec.splitlines() if ln.startswith("| H-Kernel"))
    assert "PARTIAL" in row and "OPERATIONAL" not in row, row
    assert "`PUSH` tidak dibatasi mode user" in OFF


# ── the checklist ───────────────────────────────────────────────


def test_every_bench_the_checklist_ticks_is_a_real_target() -> None:
    """A tick beside a command nobody can run is the worst kind: it reads as
    reproducible."""
    cited = set(re.findall(r"make -C rtl/tb ([\w ]+?)`", CHECKLIST))
    targets = set()
    for group in cited:
        targets |= set(group.split())
    targets.discard("all")
    real = set(re.findall(r"^(sim_\w+):", TB_MAKEFILE, re.M))
    assert targets <= real, f"ticked but not a target: {sorted(targets - real)}"
    assert targets, "the checklist stopped naming any bench"


def test_the_checklist_ticks_every_bench_the_makefile_runs() -> None:
    body = TB_MAKEFILE.split("\nall:")[1].split("\n\n")[0]
    benches = set(re.findall(r"\bsim_\w+", body))
    cited = set()
    for group in re.findall(r"make -C rtl/tb ([\w ]+?)`", CHECKLIST):
        cited |= set(group.split())
    missing = benches - cited - {"all"}
    assert not missing, f"benches that run but are not on the checklist: {sorted(missing)}"


def test_the_bitstream_is_red_not_absent() -> None:
    """The one row that must never quietly disappear. A checklist that stops
    before the red line is not a checklist."""
    row = [ln for ln in CHECKLIST.splitlines() if "bitstream" in ln]
    assert row, "the bitstream row is gone from the checklist"
    assert "🔴" in row[0] and "✅" not in row[0]
    # The percentage is read back from the wrapper, not typed twice: it moves
    # every time the design does, and a hard-coded copy here would be one more
    # transcription to drift.
    pct = re.search(r"LUT4\s+[\d,]+ / [\d,]+\s+(\d+)%", WRAPPER).group(1)
    assert f"{pct}%" in row[0], f"the checklist says {row[0]}, the wrapper says {pct}%"
    assert "make -C rtl/fpga/gowin bitstream" in CHECKLIST.split("Satu tarikan napas")[1]


def test_nothing_blocked_is_ticked_green() -> None:
    """OFF.md and the green column have to stay disjoint."""
    green = [ln for ln in CHECKLIST.splitlines() if ln.startswith("| ✅")]
    assert len(green) > 20, f"only {len(green)} green rows -- the list shrank"
    for word in ("bitstream", "flash", "HFS", "HOS", "Fmax"):
        assert not [ln for ln in green if word in ln], f"{word} is ticked green"


def test_the_counts_agree_across_the_folder() -> None:
    """Three files quote the same three numbers. They drift unless something
    reads them together."""
    for figure in ("226 asersi", "14 bench"):
        assert figure in CHECKLIST, f"the checklist lost {figure}"
    # The pytest count is the one figure here nothing can verify -- checking it
    # would mean running pytest inside pytest -- so what is guarded is that the
    # checklist says so, rather than presenting it as though it were checked.
    assert re.search(r"\*\*[\d.]+ tes lulus\*\*, \d+ dilewati †", CHECKLIST)
    assert "tidak dijaga" in CHECKLIST
    assert "226 asersi RTL di 14 testbench" in README
    assert "226 asersi, 14 bench, 0 gagal" in ON
