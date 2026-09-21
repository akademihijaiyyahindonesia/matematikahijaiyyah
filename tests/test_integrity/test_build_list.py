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
import subprocess
import sys
from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED, OpCode

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "cosmictera-build"
README = (FOLDER / "README.md").read_text(encoding="utf-8")
ON = (FOLDER / "ON.md").read_text(encoding="utf-8")
CHECKLIST = (FOLDER / "CHECKLIST.md").read_text(encoding="utf-8")
OFF = (FOLDER / "OFF.md").read_text(encoding="utf-8")
PAPAN = (FOLDER / "PAPAN.md").read_text(encoding="utf-8")
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


def test_fmax_is_measured_on_the_board_not_synthesised() -> None:
    """A label does not rise without new evidence (R2), and the evidence
    here is the board itself: place-and-route completed, the bitstream was
    flashed, and the UART answered. Synthesis alone would not earn CC."""
    assert "114,65" in ON, "ON.md must carry the Tang Nano 20K's measured Fmax"
    assert "116,44" in README, "the board's post-routing Fmax is the headline"
    assert "Tang Nano 20K" in OFF


def test_the_bisection_lives_in_one_place_only() -> None:
    """The wrapper header carries it; OFF.md must not carry a copy.

    Both files used to hold the table and a test compared them. Two copies
    that agree is still two transcriptions, and the cheaper guarantee is one
    source: the header sits next to the design it measures, so it is the one
    that gets re-run. A copy in OFF.md could only ever drift.
    """
    wrapper_commits = re.findall(
        r"\b([0-9a-f]{7})\b", WRAPPER.split("Bisected")[1].split("One commit did it")[0])
    assert len(wrapper_commits) == 6, f"the wrapper's bisection is {wrapper_commits}"

    for sha in wrapper_commits:
        assert sha not in OFF, (
            f"OFF.md carries commit {sha} again -- the bisection was copied back")


def test_off_holds_only_what_is_still_blocked() -> None:
    """OFF.md is for what does not run, on the board that exists.

    Two entries left it the day they stopped being true, and the test has to
    move with them or it pins the repository to a stale picture:

      the combined top level (105%)  -- dissolved, not fixed. Slots are
      loaded in sequence, so their costs never had to add. See rack.py.

      the five trap/supervisor programs -- they run. Relocation to LOAD_BASE
      and a deadline relative to the free-running counter were what they
      needed, and PAPAN.md carries the board output.

    What remains is genuinely blocked and measured.
    """
    assert "1.665 bit port" in OFF, "the raw Ka'bah module's IOB limit"
    assert "384 IOB" in OFF, "the IOB figure must be this board's"

    assert "105%" not in OFF, (
        "the combined top level is back in OFF.md -- it is not a blocker, it "
        "is a question nobody has to ask (rtl/scripts/rack.py)")
    assert "nol byte" not in OFF, (
        "the five trap/supervisor programs are listed as blocked again, but "
        "they run on the board -- see cosmictera-build/PAPAN.md")


def test_papan_records_the_five_programs_running() -> None:
    """The board output has to live somewhere, or "they run" is a claim."""
    papan = (ROOT / "cosmictera-build" / "PAPAN.md").read_text(encoding="utf-8")
    for name in ("mem_protect", "syscall_io", "trap_timer", "user_mode"):
        assert name in papan, name
    assert "42" in papan and "99" in papan, (
        "syscall_io's result is the sharp one: 42 on the wire and never 99")
    assert "157 detik" in papan, "the free-running counter's wrap must be named"


# ── scope honesty ───────────────────────────────────────────────


def test_the_three_designed_components_are_sorted_correctly() -> None:
    """H-Kernel and HOS are built and run, with their real limits named where
    they are claimed. HFS's WRITE path is real (it is what HOS's guard-on-write
    property demonstrates) but its read path and persistent storage are not --
    so HFS is described in ON.md, not claimed complete there, and its specific
    remaining gaps (no CSET, no persistent medium) stay in OFF.md rather than
    being folded into "HFS is done" or hidden behind "HOS is done"."""
    assert "**H-Kernel**" in ON
    assert "### HOS" in ON
    assert "**setengah**" in ON, "the HFS read-path limit must stay visible where HFS is claimed"
    assert "CSET" in OFF and "persisten" in OFF


def test_only_layer_three_is_said_to_carry_security() -> None:
    assert "satu-satunya pemikul keamanan" in ON
    assert "tidak ada di RTL" in ON


def test_the_kernels_own_limits_are_stated_where_it_is_claimed() -> None:
    """The kernel is in ON. Its gaps have to be reachable from there, or the
    entry overstates itself."""
    assert "OFF.md" in ON
    # The book gives H-Kernel four responsibilities. Two run. Claiming the
    # component without naming the split is the overstatement this catches.
    assert "**empat** tanggung jawab" in ON
    assert "Keempatnya" in ON, "ON.md must say which of the four run"
    # Four of four is the responsibilities, not the scale. What is still
    # missing has to stay named where the component is claimed.
    for limit in ("tiga slot tetap", "tanpa pembuatan proses dinamis",
                  "stack alamat-kembali tidak ikut"):
        assert limit in ON, f"ON.md stops naming a limit: {limit}"
    spec = (ROOT / "docs" / "hybit_pipeline_spec.md").read_text(encoding="utf-8")
    assert "4 of 4" in spec and "three fixed slots" in spec
    spec = (ROOT / "docs" / "hybit_pipeline_spec.md").read_text(encoding="utf-8")
    row = next(ln for ln in spec.splitlines() if ln.startswith("| H-Kernel"))
    # The four responsibilities run, so the row may say OPERATIONAL -- but it
    # has to carry the scale beside it, because "operational" over three fixed
    # slots is not the same claim as "operational" over a process table.
    assert "4 of 4" in row and "three fixed slots" in row, row
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


def test_the_bitstream_row_is_green_and_matches_the_wrapper() -> None:
    """Bitstream is green because the design fits the Tang Nano 20K and the
    board ran it. The percentage is read back from the wrapper, not typed
    twice: it moves every time the design does, and a hard-coded copy here
    would be one more transcription to drift."""
    row = [ln for ln in CHECKLIST.splitlines()
           if ln.startswith("| ✅") and "bitstream" in ln]
    assert row, "the bitstream row is gone from the checklist, or not green"
    pct = re.search(r"LUT4\s+[\d,]+ / [\d,]+\s+(\d+)%", WRAPPER).group(1)
    assert f"{pct}%" in row[0], f"the checklist says {row[0]}, the wrapper says {pct}%"
    assert "make -C rtl/fpga/gowin bitstream" in CHECKLIST.split("Satu tarikan napas")[1]


def test_nothing_blocked_is_ticked_green() -> None:
    """OFF.md and the green column have to stay disjoint. HOS moved out of
    this blacklist once its four properties were actually built (see
    ON.md#hos-heap-hfs-har); "HFS" stays allowed only in the SPECIFIC phrase
    that names what is real about it (its write path), checked separately
    below, not as a blanket word-ban."""
    green = [ln for ln in CHECKLIST.splitlines() if ln.startswith("| ✅")]
    assert len(green) > 20, f"only {len(green)} green rows -- the list shrank"
    # "bitstream" is checked as its own claim below, in
    # test_the_bitstream_row_is_green_and_matches_the_wrapper.
    # "flash" and "Fmax" stay banned from the green ROWS: both are real now
    # (PAPAN.md), but they belong to the board record, not to a checklist
    # tick that a build could satisfy on its own.
    for word in ("flash", "Fmax"):
        assert not [ln for ln in green if word in ln], f"{word} is ticked green"
    # An HFS row may be green only while it names WHICH path it is claiming.
    # There were two phrases once CSET landed: the write path has always been
    # "guard-on-write", and the read path became real when hos_fs_read stopped
    # handing back raw words and started rebuilding a live H-Reg -- proven on
    # the board, 1 1 1 2 1. M4.1 adds a third: the four operations as a
    # lifecycle, with hos_fs_create finally a named operation instead of a
    # side effect of the first write, proven on the board as 1 0 1 1 1 1 0.
    #
    # It carries "di RAM" for the same reason the other two carry their own
    # scope: HFS as a whole is still blocked on PERSISTENT storage (OFF.md),
    # and everything M4.1 proved is gone at reset. A row that says only "HFS"
    # stays refused.
    #
    # The fourth arrived with the card layer: a file written in one boot is
    # read in the next, with data RAM zeroed between them. Its phrase carries
    # "tersimulasi" on purpose -- the card model cannot lose power.
    #
    # The fifth is the board itself, 18 September 2026: "melewati mati daya di
    # papan", the cable pulled and the file read back identical. Until that day
    # no phrase here was allowed to claim the board, because no run had earned
    # it. This one names the physical power cycle, which is the only thing that
    # separates stored from still-in-the-card's-cache, so it is the ONLY phrase
    # in this list that may sit on a row claiming silicon. A row that says just
    # "HFS" is still refused.
    scopes = ("guard-on-write", "baca mengembalikan H-Reg hidup",
              "create → write → read → verify, di RAM",
              "melewati reboot lewat kartu, tersimulasi",
              "melewati mati daya di papan",
              # The burn-in row names HFS only because the magic word is what
              # it compares sector 1 against. It claims a READ, and no HFS
              # operation at all, so it has to say which of the two it is.
              "sektor 1 dibaca, bukan klaim HFS")
    hfs_rows = [ln for ln in green if "HFS" in ln]
    assert hfs_rows, "HOS's HFS row went missing from the checklist"
    for ln in hfs_rows:
        assert any(s in ln for s in scopes), (
            f"HFS ticked green without naming which path is real: {ln}")


def _measured_rtl_assertions() -> tuple[int, int]:
    """Run `make -C rtl/tb all` and count what the benches themselves report.

    Two report shapes exist and both must be read, which is how the old
    hard-coded figure hid its error: a numbered summary
    (`ROM Tests: 30 PASS, 0 FAIL`, `HISAB Total: 124 PASS, 0 FAIL`) and an
    Indonesian one (`SEMUA LULUS (7 pemeriksaan)`). A bench that prints
    neither contributes one -- it ran and said `PASS:` once.

    Two double-counts are excluded deliberately, both documented in PAPAN.md:
    tb_hisab's 28-letter sweep of 112 is a SUB-TOTAL inside its own 124, and
    tb_gowin_top prints one cumulative `pass_count` twice. Taking the max per
    bench handles both.
    """
    proc = subprocess.run(
        ["make", "-C", "rtl/tb", "all"],
        cwd=ROOT, capture_output=True, text=True, timeout=1800,
    )
    assert proc.returncode == 0, f"`make -C rtl/tb all` failed:\n{proc.stdout[-3000:]}"
    bad = [ln for ln in proc.stdout.splitlines()
           if "FAIL" in ln and "0 FAIL" not in ln and "FAIL-BRANCHED" not in ln]
    assert not bad, f"a testbench reported a failure: {bad}"

    per: dict[str, int] = {}
    cur: str | None = None
    for line in proc.stdout.splitlines():
        m = re.match(r"\s*vvp (tb_[a-z0-9_]+)\.vvp", line)
        if m:
            cur = m.group(1)
            per.setdefault(cur, 0)
            continue
        if cur is None:
            continue
        text = line.strip()
        numbered = re.search(r"(?:Total|Tests):\s*(\d+) PASS, 0 FAIL", text)
        semua = re.search(r"SEMUA LULUS \((\d+) pemeriksaan\)", text)
        gowin = re.search(r"Gowin wrapper:\s*(\d+) PASS", text)
        if numbered:
            per[cur] = max(per[cur], int(numbered.group(1)))
        elif semua:
            per[cur] = max(per[cur], int(semua.group(1)))
        elif gowin:
            per[cur] = max(per[cur], int(gowin.group(1)))
        elif text.startswith("PASS:") and per[cur] == 0:
            per[cur] = 1

    assert per, f"no testbench output recognised:\n{proc.stdout[-3000:]}"
    silent = [b for b, n in per.items() if n == 0]
    assert not silent, (
        f"{silent} ran but reported no countable assertion. A bench that "
        f"prints no number is counted as one or as nothing depending on who "
        f"is summing -- give it a `SEMUA LULUS (N pemeriksaan)` line."
    )
    return sum(per.values()), len(per)


def test_the_counts_agree_across_the_folder() -> None:
    """Three files quote the same three numbers. They drift unless something
    reads them together.

    Agreeing with each other is NOT the same as being right, and this test
    used to check only the first. It read "269 asersi" out of three files,
    found them identical, and passed -- while no run of `make -C rtl/tb all`
    had ever produced 269. cosmictera-build/PAPAN.md carried the same class of
    error independently ("160 pemeriksaan" beside its own detail row summing
    to 308), which is what prompted counting the log instead of the files.
    The measured figure is 253: one summary line per testbench, with
    tb_hisab's 28-letter sweep of 112 recognised as a SUB-TOTAL inside its own
    124 rather than an addition to it, and tb_gowin_top's "1" then "2" as one
    cumulative pass_count printed twice (tb_gowin_top.v:137,194) rather than
    two separate summaries. Both of those are exactly the double-counts that
    produced 308. A transcription can agree with another transcription
    forever; only the log can say what ran.

    And this test then hard-coded 253 as a string, which made it one more
    transcription -- a fourth copy, in Python, of a number no run produced
    either. It was wrong by seven for as long as it existed:
    `tb_hcpu_video_timing` guards eight VESA properties and printed
    `ALL PASS` with no number beside it, so every sum counted it as one or as
    nothing depending on how it was read. The figure now comes from the
    Makefile's own output, so the docstring above finally describes the test
    below it."""
    measured, benches = _measured_rtl_assertions()
    for figure in (f"{measured} asersi", f"{benches} bench"):
        assert figure in CHECKLIST, f"the checklist lost {figure}"
    assert f"{measured} asersi RTL di {benches} testbench" in README
    assert f"{measured} asersi, {benches} bench, 0 gagal" in ON
    assert f"{benches} testbench, {measured} pemeriksaan, 0 gagal" in PAPAN


def _quoted_pytest_counts() -> dict[str, tuple[int, int]]:
    """The passed/skipped pair each file quotes, as ints."""
    out: dict[str, tuple[int, int]] = {}
    for name, text in (("CHECKLIST", CHECKLIST), ("ON", ON),
                       ("README", README), ("PAPAN", PAPAN)):
        m = re.search(r"([\d.]+) (?:tes )?(?:tes Python )?lulus\*{0,2},? "
                      r"(\d+) dilewati", text)
        assert m, f"{name} no longer quotes a pytest passed/skipped pair"
        out[name] = (int(m.group(1).replace(".", "")), int(m.group(2)))
    return out


def test_the_quoted_pytest_counts_agree_with_each_other() -> None:
    """They drifted apart the moment nothing read them together.

    The guard this replaces checked only that CHECKLIST matched the SHAPE
    `**<number> tes lulus**, <n> dilewati` -- and the number sub-pattern
    matched any number at all. ON.md and README.md were not read for this figure whatsoever. All
    three were free to drift independently, and did: CHECKLIST said 4.565
    while ON.md and README.md sat at 4.454, a figure no run had produced for
    weeks. Same class of defect as the "269 asersi" above, and found the same
    way -- by measuring instead of comparing transcriptions.
    """
    counts = _quoted_pytest_counts()
    distinct = set(counts.values())
    assert len(distinct) == 1, f"the folder disagrees with itself: {counts}"


# Four files outside cosmictera-build/ quote the same suite figure, and the
# guard above never read one of them. Left unwatched they drifted to four
# DIFFERENT numbers -- 4.606, 4.570, 4.570 and 4.540 -- none of which any run
# had produced, plus the root README's tree annotation still at 1.649, roughly
# three thousand tests stale. The folder guard was doing its job perfectly and
# the drift simply moved to where it was not looking.
OUTSIDE_FOLDER = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "teknologi/SILIKON.md",
    "cosmictera/COMPUTING.md",
    "cosmictera-build/ROADMAP.md",
]

@pytest.mark.parametrize("relpath", OUTSIDE_FOLDER)
def test_a_file_outside_the_folder_quotes_the_same_suite_figure(relpath: str) -> None:
    """One number, measured once, quoted identically everywhere it appears."""
    quoted, _ = _quoted_pytest_counts()["CHECKLIST"]
    grouped = f"{quoted // 1000}.{quoted % 1000:03d}"
    text = (ROOT / relpath).read_text(encoding="utf-8")
    assert grouped in text, (
        f"{relpath} no longer quotes {grouped}, the figure "
        f"cosmictera-build/CHECKLIST.md carries. If the suite grew, update "
        f"every file in OUTSIDE_FOLDER together with the four in the folder."
    )


def test_no_document_quotes_a_suite_figure_that_is_not_the_current_one() -> None:
    """The half a per-file check cannot do: find the ones nobody listed.

    A file added tomorrow with a fresh transcription of today's number would
    pass every test above by simply not being in any list. This one sweeps
    every tracked .md instead and demands that any four-digit figure presented
    as a test count be the current one -- so a new stale figure fails on the
    commit that introduces it, not months later.

    Figures inside correction notes are exempt by construction: those sentences
    say what a number USED to be, and rewriting them would erase the record of
    the drift. They are recognised by the words that mark them as history.
    """
    quoted, _ = _quoted_pytest_counts()["CHECKLIST"]
    grouped = f"{quoted // 1000}.{quoted % 1000:03d}"
    historical = ("pernah berbunyi", "dulu", "tertinggal", "sementara",
                  "SUDAH BASI", "per Maret", "sebelumnya", "Maret 2026")

    stale: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith((".claude/", ".agents/", "node_modules/")):
            continue
        if "/node_modules/" in rel or "/.claude/" in rel or "/.agents/" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(\d\.\d{3})\s+(?:tes|test)\b", text):
            figure = m.group(1)
            if figure == grouped:
                continue
            start = text.rfind("\n\n", 0, m.start()) + 1
            end = text.find("\n\n", m.end())
            para = text[start : end if end != -1 else len(text)]
            if any(word in para for word in historical):
                continue
            line = text[: m.start()].count("\n") + 1
            stale.append(f"{rel}:{line} quotes {figure}")

    assert not stale, (
        f"the suite collects {grouped}, but these read as current figures and "
        f"are not: {stale}. Re-run `python3 -m pytest -q` and update them, or "
        f"mark the sentence as history if it is describing a past value."
    )


def test_the_quoted_pytest_total_is_what_pytest_actually_collects() -> None:
    """Not pytest inside pytest -- collection, which runs no test at all.

    CHECKLIST.md's footnote used to say this figure "cannot be checked without
    running pytest inside pytest". Half true: what CANNOT be checked is how
    many PASS. How many EXIST is `--collect-only`, ~12 seconds, executing
    nothing.

    But `passed + skipped == collected` was one term short, and the missing
    term cost a real investigation: the run reported 12 skipped while only 9
    SKIPPED lines existed, and the totals disagreed by exactly 3 no matter
    which figure the folder quoted. A module skipped at import -- three of
    them here, `pytest.importorskip("torch")` at the top of test_nui.py,
    test_nui_atom.py and test_nui_multitask.py -- counts once in the summary's
    skipped total and yields no collected item at all. The nine pymupdf skips
    sit inside their files, so those ARE collected and do appear per test.

    So the identity is: quoted passed + quoted skipped == collected + the
    skips that happen during collection. Both halves come from the same
    ~12-second run, because -rs lists them there too.

    -p no:cacheprovider keeps the child from writing the parent's cache.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-rs",
         "-p", "no:cacheprovider", str(ROOT / "tests")],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    m = re.search(r"(\d+) tests? collected", proc.stdout)
    assert m, f"could not read a collected count:\n{proc.stdout[-2000:]}"
    collected = int(m.group(1))
    module_skips = len(re.findall(r"^SKIPPED ", proc.stdout, re.M))

    passed, skipped = _quoted_pytest_counts()["CHECKLIST"]
    assert passed + skipped == collected + module_skips, (
        f"the folder quotes {passed} passed + {skipped} skipped = "
        f"{passed + skipped}, but pytest collects {collected} and skips "
        f"{module_skips} more module(s) at import, for {collected + module_skips}. "
        f"Re-run `python3 -m pytest -q` and update CHECKLIST.md, ON.md, "
        f"README.md and PAPAN.md together."
    )


def test_the_quoted_mypy_file_count_is_what_mypy_actually_checks() -> None:
    """The same drift as the pytest figure, one row below it in the same table.

    CHECKLIST.md said "mypy bersih, 108 berkas" while mypy reported 128 --
    twenty files' worth of stale, in the single place the number appears. It
    drifted for the ordinary reason: the row is green as long as mypy exits
    zero, so nobody re-read the count beside it, and `make typecheck` says
    nothing about whether the table agrees with it.

    The count matters more than a cosmetic figure would. It is the only thing
    on the page that says how much of the tree mypy is looking at, so a
    silently shrinking number would read exactly like a clean run -- the same
    green tick over a narrower sweep.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "src/hijaiyyah"],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    m = re.search(r"no issues found in (\d+) source files?", proc.stdout)
    assert m, f"mypy did not report a clean sweep:\n{proc.stdout[-2000:]}"
    measured = int(m.group(1))

    text = (ROOT / "cosmictera-build" / "CHECKLIST.md").read_text(encoding="utf-8")
    q = re.search(r"mypy bersih, (\d+) berkas", text)
    assert q, "CHECKLIST.md no longer states a mypy file count at all"
    quoted = int(q.group(1))

    assert quoted == measured, (
        f"CHECKLIST.md quotes {quoted} files for `make typecheck`; mypy checks "
        f"{measured}. Re-run `make typecheck` and put its own number on the row."
    )
