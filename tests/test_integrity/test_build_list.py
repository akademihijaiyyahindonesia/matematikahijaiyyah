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

import functools
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
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
LAYERS = (ROOT / "NUI" / "LAYERS.md").read_text(encoding="utf-8")
PKG = (ROOT / "rtl" / "hcpu_pkg.vh").read_text(encoding="utf-8")
WRAPPER = (ROOT / "rtl" / "fpga" / "gowin" / "hcpu_gowin_top.v").read_text(encoding="utf-8")
TB_MAKEFILE = (ROOT / "rtl" / "tb" / "Makefile").read_text(encoding="utf-8")

PREFIXES = ("rtl/", "src/", "tests/", "docs/", "cosmictera/", "hijrah/",
            "kabah/", "matematika-hijaiyyah/", "cosmic-codex-jim/")


def _cited_paths(text: str) -> set[str]:
    """Repo paths named in backticks or as markdown links. A test id names its file
    before `::`; whether the test itself is collected is the run record's check."""
    found = set(re.findall(r"`([^`\s]+)`", text))
    found |= set(re.findall(r"\]\(([^)]+)\)", text))
    return {p.split("::", 1)[0] for p in found if p.startswith(PREFIXES) or p.startswith("../")}


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
    """Layer 3 alone carries the security. In RTL it is a slot of its own
    (1 October 2026), not on Ka'bah's path, so ON.md must not let the HMAC
    core read as authenticating what Ka'bah emits."""
    assert "satu-satunya pemikul keamanan" in ON
    assert "slot sendiri" in ON and "belum terautentikasi sampai" in ON


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
    # NUI/LAYERS.md's layer 6 quoted "26 testbench" from 13 September until
    # 28 September 2026, when it was measured: 26 was what this same count
    # gave then. Held here, by the owner's definition, so it cannot go stale
    # unseen again.
    layers = " ".join(LAYERS.split())
    assert layers.count(f"{benches} testbench yang dijalankan `make -C rtl/tb all`") == 2


# -- The suite figure, and the run's result ------------------------------------------------
# Two numbers, kept apart. How many tests EXIST is what the documents quote: `pytest
# --collect-only` counts it in about twelve seconds and runs none of them. How many PASS only a
# full run can say, so it is written once, as the record of a run, under CHECKLIST.md's
# "Lari terakhir".
#
# Until 20 October 2026 these guards read a "<N> lulus, <n> dilewati" pair from four files and
# demanded N + n == collected. That was true on 10 September (422a07b), when nothing failed.
# Once the accepted HDMI red existed, no true pair could satisfy it -- 6.170 passed + 1 skipped
# is 6.171, not 6.172 -- so the guard made four files say that every test passed (owner,
# 20 October 2026).

# A four-digit figure grouped the Indonesian way, read between digit boundaries so that 15.933
# is never read as 5.933 (owner, 1 October 2026).
_FIGURE = r"(?<![\d.])(\d\.\d{3})(?!\d)"
_SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()
_CHECKLIST = "cosmictera-build/CHECKLIST.md"


def _grouped(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _number(text: str) -> int:
    return int(text.replace(".", ""))


def _line(text: str, at: int) -> int:
    return text.count("\n", 0, at) + 1


@dataclass(frozen=True)
class _Collection:
    collected: int
    module_skips: int
    nodes: frozenset[str]


@functools.cache
def _collection() -> _Collection:
    """One `--collect-only` over the whole of tests/, shared by every check below.

    No -k, --ignore or --deselect: the count has to include this file's own tests, because
    changing this file changes it. -qq on top of the configured -v prints one node id per line.
    -rs lists the modules skipped at import, which yield no node but count once each in a
    run's skipped total (422a07b); `SKIPPED [n]` is summed, not counted, because -rs folds
    identical reasons into one line.

    -p no:cacheprovider keeps the child from writing the parent's cache.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-qq", "-rs",
         "-p", "no:cacheprovider", str(ROOT / "tests")],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    return _read_collection(proc.returncode, proc.stdout, proc.stderr)


def _read_collection(returncode: int, stdout: str, stderr: str) -> _Collection:
    """What one `--collect-only` reported, accepted only when it exited 0.

    A collection that fails still prints a count: a test file that does not import exits 2 with
    "6199 tests collected, 1 error", and its tests are missing from the count and the node ids
    alike, so the two still agree. Measured 22 October 2026 on a copy with one broken file: G2,
    G6 and G7 all passed. A non-zero exit is therefore never read as a count (owner,
    22 October 2026)."""
    assert returncode == 0, (
        f"pytest --collect-only exited {returncode}, so its count is not the suite's.\n"
        f"stdout (last 2000 characters):\n{stdout[-2000:]}\n"
        f"stderr (last 2000 characters):\n{stderr[-2000:]}")
    m = re.search(r"^(\d+) tests? collected", stdout, re.M)
    assert m, f"could not read a collected count:\n{stdout[-2000:]}"
    nodes = frozenset(re.findall(r"^(tests/\S+?\.py::.+)$", stdout, re.M))
    skips = sum(int(n) for n in re.findall(r"^SKIPPED \[(\d+)\]", stdout, re.M))
    return _Collection(int(m.group(1)), skips, nodes)


@functools.cache
def _tracked_markdown() -> dict[str, str]:
    """Every tracked .md, by repository path.

    Tracked, not every .md on disk. On 20 October 2026 the sweep that walked the disk read 305
    files in the source tree: 108 tracked, and 197 more from a vendored three.js, two
    virtualenvs, a pytest cache and the owner's private folders -- none of them this
    repository's documents, and none present in a clean clone.
    """
    out = subprocess.run(["git", "ls-files", "-z", "--", "*.md"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return {rel: (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            for rel in out.split("\0") if rel}


# An exception is a place, not a kind of sentence: a path, the exact text, and why. Each one
# must match exactly once, so an exception whose text has gone cannot sit in the list unseen.
_Except = tuple[str, str, str]


def _excepted(rel: str, text: str, m: re.Match[str], exceptions: tuple[_Except, ...]) -> bool:
    for path, exact, _why in exceptions:
        at = text.find(exact) if path == rel else -1
        if at != -1 and at <= m.start() and m.end() <= at + len(exact):
            return True
    return False


def _exception_problems(docs: dict[str, str], exceptions: tuple[_Except, ...],
                        pattern: str) -> list[str]:
    problems = []
    for path, exact, _why in exceptions:
        n = docs.get(path, "").count(exact)
        if n != 1:
            problems.append(f"the exception {exact!r} matches {n} times in {path}, not once")
        elif not re.search(pattern, exact):
            problems.append(f"the exception {exact!r} in {path} no longer excepts anything")
    return problems


# G1 -- the four folder files each state the collected figure once, in their own sentence, and
# agree. This is the folder agreeing with itself; whether it agrees with pytest is G2.
_HEADLINES = {
    _CHECKLIST: rf"\*\*{_FIGURE} tes terkumpul\*\* †",
    "cosmictera-build/ON.md": rf"# {_FIGURE} tes terkumpul; hasil: CHECKLIST\.md †",
    "cosmictera-build/README.md": rf"{_FIGURE} tes Python terkumpul",
    "cosmictera-build/PAPAN.md": rf"\| {_FIGURE} tes terkumpul; hasil lari terakhir",
}


def _folder_problems(docs: dict[str, str]) -> list[str]:
    problems, figures = [], {}
    for rel, pattern in _HEADLINES.items():
        found = re.findall(pattern, docs.get(rel, ""))
        if len(found) != 1:
            problems.append(f"{rel} states the collected figure {len(found)} times, not once")
        else:
            figures[rel] = found[0]
    if len(set(figures.values())) > 1:
        problems.append(f"the folder disagrees with itself: {figures}")
    return problems


# G2 -- the folder's figure is what pytest collects, and pytest was asked about everything.
def _collected_problems(docs: dict[str, str], col: _Collection) -> list[str]:
    problems = []
    if len(col.nodes) != col.collected:
        problems.append(f"read {len(col.nodes)} node ids, but pytest collected {col.collected}")
    if not any(n.startswith(f"{_SELF}::") for n in col.nodes):
        problems.append(f"the collection does not hold {_SELF}'s own tests")
    m = re.search(_HEADLINES[_CHECKLIST], docs.get(_CHECKLIST, ""))
    if not m:
        problems.append(f"{_CHECKLIST} states no collected figure")
    elif _number(m.group(1)) != col.collected:
        problems.append(
            f"{_CHECKLIST} quotes {m.group(1)} collected tests; pytest collects "
            f"{_grouped(col.collected)}. Run `python3 -m pytest --collect-only -q` and update "
            f"every place G7 lists, then re-run the suite for the record under \"Lari terakhir\".")
    return problems


# G4 -- any "<figure> tes|test" in a tracked .md is the collected figure, unless it is listed
# below with its reason. Nothing is. Until 20 October 2026 a paragraph was exempt when it held
# any of eight words ("dulu", "sementara", ...); measured that day, those words exempted no
# figure at all, and words that common could have exempted the next stale one.
_STALE_EXCEPTIONS: tuple[_Except, ...] = ()
_COUNT = rf"{_FIGURE}\s+(?:tes|test)\b"


def _stale_problems(docs: dict[str, str], collected: int) -> list[str]:
    problems = _exception_problems(docs, _STALE_EXCEPTIONS, _COUNT)
    for rel, text in sorted(docs.items()):
        for m in re.finditer(_COUNT, text):
            if m.group(1) != _grouped(collected) and not _excepted(rel, text, m,
                                                                   _STALE_EXCEPTIONS):
                problems.append(f"{rel}:{_line(text, m.start())} quotes {m.group(1)}")
    return problems


# G5 -- no tracked .md says how many tests passed, except the run's record and the three
# places below. The defect this guards is the one the old pair guard forced: a collected count
# written as a pass count.
_PASS = rf"{_FIGURE}\s+(?:tes\s+)?(?:Python\s+)?lulus"
_PASS_EXCEPTIONS: tuple[_Except, ...] = (
    ("cosmictera-build/PAPAN.md", "berbunyi 4.519 lulus / 16 dilewati",
     "a correction note, quoting what the line used to say"),
    ("cosmictera-build/PAPAN.md", "> 4.961 lulus, 0 dilewati, 0 gagal",
     "a dated result inside the same quoted history"),
    ("cosmictera/CODEX.md",
     "`python3 -m pytest tests/test_full_verification.py -q` → 1.380 lulus",
     "one file's count, not the suite's; its figure is not checked here"),
)


def _pass_problems(docs: dict[str, str]) -> list[str]:
    problems = _exception_problems(docs, _PASS_EXCEPTIONS, _PASS)
    records = [(rel, m.span()) for rel, m in _records(docs)]
    for rel, text in sorted(docs.items()):
        for m in re.finditer(_PASS, text):
            if _excepted(rel, text, m, _PASS_EXCEPTIONS):
                continue
            if any(r == rel and a <= m.start() < b for r, (a, b) in records):
                continue
            problems.append(f"{rel}:{_line(text, m.start())} says {m.group(0)!r}; how many "
                            f"tests passed is written only in {_CHECKLIST}'s record")
    return problems


# G6 -- the record of a run: one place, consistent with the collection, failures and errors
# named and kept apart. It checks that the record is consistent, never that it is true: only a
# full run says how many passed, and a test that starts failing without the count changing is
# invisible here (R13 is what covers that).
_RECORD = re.compile(
    r"Lari\s+terakhir,\s+\d{1,2}\s+\w+\s+\d{4}:\s+\*\*(?P<P>[\d.]+)\s+lulus,\s+"
    r"(?P<S>[\d.]+)\s+dilewati,\s+(?P<F>[\d.]+)\s+gagal,\s+(?P<E>[\d.]+)\s+error\s+dari\s+"
    r"(?P<C>[\d.]+)\s+terkumpul\*\*\.(?P<rest>.*?)(?=\n\n|\Z)", re.S)
_NODE = r"`(tests/[^`\s]+?\.py::[^`]+)`"


def _records(docs: dict[str, str]) -> list[tuple[str, re.Match[str]]]:
    return [(rel, m) for rel, text in sorted(docs.items()) for m in _RECORD.finditer(text)]


def _record_problems(docs: dict[str, str], col: _Collection) -> list[str]:
    found = _records(docs)
    if len(found) != 1:
        return [f"the run's record appears {len(found)} times, not once: "
                f"{[rel for rel, _ in found]}"]
    rel, m = found[0]
    problems = [] if rel == _CHECKLIST else [f"the run's record is in {rel}, not {_CHECKLIST}"]
    p, s, f, e, c = (_number(m.group(k)) for k in "PSFEC")
    if c != col.collected:
        problems.append(f"the record is of {_grouped(c)} tests; pytest collects "
                        f"{_grouped(col.collected)} -- the suite changed and was not re-run")
    if p + s + f + e != col.collected + col.module_skips:
        problems.append(f"passed + skipped + failed + errors = {p + s + f + e}, but pytest "
                        f"collects {col.collected} and skips {col.module_skips} module(s) at "
                        f"import, for {col.collected + col.module_skips}")
    lists = re.fullmatch(r"\s*Yang\s+gagal:(?P<gagal>.*?)Yang\s+error:(?P<error>.*)", m["rest"],
                         re.S)
    if not lists:
        return [*problems, "the record does not list `Yang gagal:` and then `Yang error:`"]
    named: dict[str, list[str]] = {}
    for label, count in (("gagal", f), ("error", e)):
        section = lists[label]
        ids = re.findall(_NODE, section)
        named[label] = ids
        if count == 0 and (ids or not re.match(r"\s*tidak\s+ada\b", section)):
            problems.append(f"`Yang {label}:` must say `tidak ada` when the record counts 0")
        if count != 0 and len(ids) != count:
            problems.append(f"the record counts {count} {label} but names {len(ids)}")
        if len(set(ids)) != len(ids):
            problems.append(f"`Yang {label}:` names a test twice")
        problems += [f"`Yang {label}:` names {i}, which pytest does not collect"
                     for i in ids if i not in col.nodes]
    problems += [f"{i} is named as both failed and errored; a run that counts one test twice "
                 f"cannot be recorded until it is fixed"
                 for i in sorted(set(named["gagal"]) & set(named["error"]))]
    return problems


# G7 -- every place the collected figure is quoted, by position, each matching once. Thirteen
# places in nine files. Before this, five of them were checked only as "the figure appears
# somewhere in the file", and CHECKLIST.md's "mencacah" was not checked at all.
_POSITIONS: tuple[tuple[str, str], ...] = (
    ("README.md", rf"tests/ +{_FIGURE} test\b"),
    (_CHECKLIST, rf"\*\*{_FIGURE} tes terkumpul\*\* †"),
    (_CHECKLIST, rf"mencacah {_FIGURE} dalam"),
    (_CHECKLIST, rf"error\s+dari\s+{_FIGURE}\s+terkumpul\*\*"),
    (_CHECKLIST, rf"# {_FIGURE} tes terkumpul; hasilnya di † atas"),
    ("cosmictera-build/ON.md", rf"# {_FIGURE} tes terkumpul; hasil: CHECKLIST\.md †"),
    ("cosmictera-build/PAPAN.md", rf"dan {_FIGURE} tes Python\. Simulasi bukan$"),
    ("cosmictera-build/PAPAN.md", rf"\| {_FIGURE} tes terkumpul; hasil lari terakhir"),
    ("cosmictera-build/README.md", rf"{_FIGURE} tes Python terkumpul"),
    ("cosmictera-build/ROADMAP.md", rf"← sekarang {_FIGURE}"),
    ("cosmictera/COMPUTING.md", rf"{_FIGURE} tes Python terkumpul —"),
    ("docs/ARCHITECTURE.md", rf"dan {_FIGURE} tes Python\.$"),
    ("teknologi/SILIKON.md", rf"dan {_FIGURE} tes Python\. Simulasi bukan lalai"),
)


def _position_problems(docs: dict[str, str], col: _Collection) -> list[str]:
    problems = []
    for rel, pattern in _POSITIONS:
        found = re.findall(pattern, docs.get(rel, ""), re.M)
        if len(found) != 1:
            problems.append(f"{rel}: {pattern!r} matches {len(found)} times, not once")
        elif _number(found[0]) != col.collected:
            problems.append(f"{rel} quotes {found[0]}; pytest collects {_grouped(col.collected)}")
    return problems


_GUARDS: dict[str, Callable[[dict[str, str], _Collection], list[str]]] = {
    "G1": lambda docs, col: _folder_problems(docs),
    "G2": _collected_problems,
    "G4": lambda docs, col: _stale_problems(docs, col.collected),
    "G5": lambda docs, col: _pass_problems(docs),
    "G6": _record_problems,
    "G7": _position_problems,
}


def test_the_folder_states_one_collected_figure() -> None:
    """G1. The folder agreeing with itself, before anyone asks pytest."""
    assert _folder_problems(_tracked_markdown()) == []


def test_the_collected_figure_is_what_pytest_collects() -> None:
    """G2. A figure that agrees across four files is still a transcription until it is
    compared with the collection -- the "269 asersi" lesson above, for the pytest count."""
    assert _collected_problems(_tracked_markdown(), _collection()) == []


def test_no_document_quotes_a_suite_figure_that_is_not_the_current_one() -> None:
    """G4. A file added tomorrow with a fresh transcription of today's number would pass every
    per-file check by not being in any list. This one sweeps every tracked .md instead, so a
    stale figure fails on the commit that introduces it."""
    assert _stale_problems(_tracked_markdown(), _collection().collected) == []


def test_no_document_says_how_many_tests_passed_but_the_record() -> None:
    """G5. The defect the pair guard forced, now refused wherever it is written."""
    assert _pass_problems(_tracked_markdown()) == []


def test_the_run_is_recorded_once_and_consistently() -> None:
    """G6. Consistency, not truth: P + S + F + E == C + I, the failures and the errors named
    apart and found in the collection."""
    assert _record_problems(_tracked_markdown(), _collection()) == []


def test_every_place_the_figure_is_quoted_holds_the_collected_figure() -> None:
    """G7. Position by position, each matching once."""
    assert _position_problems(_tracked_markdown(), _collection()) == []


def test_the_m5_control_figure_is_the_one_measured() -> None:
    """e4c251e (17 September 2026) measured the CPU-slot control at 15.933
    LUT4, the figure the two rejected dashboard layouts are set against.
    Test-count sweeps that replaced the suite total as a bare substring
    rewrote it four times -- 865959e, b7fa5e8, 46f4b14, 08f1e36 -- because
    "5.933" sits inside "15.933". A measured figure is not a count to sweep:
    count updates match the total only between digit boundaries (owner,
    1 October 2026)."""
    assert "melawan kontrol 15.933 yang terrout bersih" in PAPAN


# What pytest printed on 22 October 2026: a clean collection, one with a test file that does
# not import, and one with nothing to collect.
_COLLECTED = "tests/test_a.py::test_a\n\n1 test collected in 0.29s\n"
_NOT_COLLECTED = {
    2: "tests/test_a.py::test_a\n!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection "
       "!!!!!!!!!!!!!!!!!!!!\n1 test collected, 1 error in 0.17s\n",
    5: "no tests collected in 0.09s\n",
}


@pytest.mark.parametrize("code", sorted(_NOT_COLLECTED),
                         ids=["2: a test file does not import", "5: nothing to collect"])
def test_a_failed_collection_is_never_read_as_a_count(code: int) -> None:
    """Exit 2 still says "1 test collected", and its one node id agrees with it: only the exit
    code tells that collection failed. The control is the same reader on a clean collection."""
    assert _read_collection(0, _COLLECTED, "") == _Collection(
        1, 0, frozenset({"tests/test_a.py::test_a"}))
    with pytest.raises(AssertionError) as refused:
        _read_collection(code, _NOT_COLLECTED[code], "what pytest wrote to stderr")
    said = str(refused.value)  # pytest indents a multi-line message, so read it line by line
    assert f"exited {code}" in said and "what pytest wrote to stderr" in said, said
    assert all(line in said for line in _NOT_COLLECTED[code].splitlines()), said


def test_a_figure_inside_a_larger_number_is_not_read() -> None:
    """15.933 is a measured LUT4 control, not a count; read without digit boundaries it holds
    a "5.933". None of the patterns above may see it."""
    text = "kontrol 15.933 tes, 15.933 lulus, 15.933 test"
    assert re.findall(_COUNT, text) == [] and re.findall(_PASS, text) == []
    assert _stale_problems({"x.md": text}, 1) == []
    assert _pass_problems({**_tracked_markdown(), "x.md": text}) == []


# -- Each guard refuses the damage it exists for (R3) --------------------------------------
# Pure checks over in-memory copies: no document or test is touched. Every case first proves
# its guard passes on the control, so a red sabotage is the damage, not a guard already red.
Docs = dict[str, str]
Inputs = tuple[Docs, _Collection]


def _swap(docs: Docs, rel: str, old: str, new: str) -> Docs:
    assert docs[rel].count(old) == 1, f"the sabotage did not apply: {old!r} in {rel}"
    return {**docs, rel: docs[rel].replace(old, new)}


def _swap_figure(docs: Docs, rel: str, pattern: str, new: int) -> Docs:
    text = docs[rel]
    (m,) = list(re.finditer(pattern, text, re.M))
    return {**docs, rel: text[: m.start(1)] + _grouped(new) + text[m.end(1):]}


def _record(docs: Docs) -> re.Match[str]:
    ((_rel, m),) = _records(docs)
    return m


def _with_record(docs: Docs, *, p: int = 0, f: int = 0, e: int = 0, gagal: str | None = None,
                 error: str | None = None) -> Docs:
    """The record rewritten: P, F and E shifted by p, f and e, and either list replaced."""
    m, text = _record(docs), docs[_CHECKLIST]
    lists = re.fullmatch(r"(\s*Yang\s+gagal:)(.*?)(Yang\s+error:)(.*)", m["rest"], re.S)
    assert lists
    rest = (lists[1] + (lists[2] if gagal is None else f" {gagal}\n") + lists[3]
            + (lists[4] if error is None else f" {error}"))
    head = text[m.start(): m.start("rest")]
    head = re.sub(r"\*\*[\d.]+ lulus", f"**{_grouped(_number(m['P']) + p)} lulus", head, count=1)
    head = re.sub(r"[\d.]+(?=\s+gagal,)", str(_number(m["F"]) + f), head, count=1)
    head = re.sub(r"[\d.]+(?=\s+error\s+dari)", str(_number(m["E"]) + e), head, count=1)
    return {**docs, _CHECKLIST: text[: m.start()] + head + rest + text[m.end():]}


def _first_failed(docs: Docs) -> str:
    return re.findall(_NODE, _record(docs)["rest"].split("Yang error:")[0])[0]


def _not_failed(docs: Docs, col: _Collection) -> str:
    return sorted(col.nodes - set(re.findall(_NODE, _record(docs)["rest"])))[0]


def _with_one_failure(docs: Docs, col: _Collection) -> tuple[Docs, str]:
    """Ensure a valid 1-failure control exists even when the live record has 0 failures."""
    existing = re.findall(_NODE, _record(docs)["rest"].split("Yang error:")[0])
    if existing:
        return docs, existing[0]
    node = _not_failed(docs, col)
    return _with_record(docs, p=-1, f=1, gagal=f"`{node}`."), node


def _sabotages() -> list[tuple[str, str, Callable[[Inputs], tuple[Inputs, Inputs]]]]:
    def same(change: Callable[[Docs, _Collection], Inputs]) -> Callable[[Inputs], tuple[
            Inputs, Inputs]]:
        return lambda real: (real, change(*real))

    def every_figure(docs: Docs, col: _Collection) -> Inputs:
        old, new = _grouped(col.collected), _grouped(col.collected + 1)
        return {r: re.sub(rf"(?<![\d.]){re.escape(old)}(?!\d)", new, t)
                for r, t in docs.items()}, col

    def failure_without_name(real: Inputs) -> tuple[Inputs, Inputs]:
        docs, col = real
        control, _ = _with_one_failure(docs, col)
        return (control, col), (_with_record(control, gagal="tidak ada."), col)

    def unknown_failure_name(real: Inputs) -> tuple[Inputs, Inputs]:
        docs, col = real
        control, first = _with_one_failure(docs, col)
        return (control, col), (_swap(control, _CHECKLIST, f"`{first}`", f"`{first}_gone`"), col)

    def double_counted(real: Inputs) -> tuple[Inputs, Inputs]:
        docs, col = real
        control, first = _with_one_failure(docs, col)
        node = f"`{first}`"
        return (control, col), (_with_record(control, p=-1, e=1, error=node), col)

    def duplicate_failure_name(real: Inputs) -> tuple[Inputs, Inputs]:
        docs, col = real
        control, first = _with_one_failure(docs, col)
        failed = _record(control)["rest"].split("Yang error:")[0].split("Yang gagal:")[1].strip()
        return (control, col), (_with_record(control, p=-1, f=1, gagal=f"{failed} `{first}`"), col)

    def error_as_failure(real: Inputs) -> tuple[Inputs, Inputs]:
        docs, col = real
        node = f"`{_not_failed(docs, col)}`"
        control = _with_record(docs, p=-1, e=1, error=node)
        failed = _record(control)["rest"].split("Yang error:")[0].split("Yang gagal:")[1].strip()
        gagal_list = f"`{node}`." if failed.startswith("tidak ada") else f"{failed} {node}"
        return (control, col), (_with_record(control, gagal=gagal_list, error="tidak ada."), col)

    def moved_record(docs: Docs, col: _Collection) -> Inputs:
        record = _record(docs).group(0)
        docs = _swap(docs, _CHECKLIST, record, "")
        return {**docs, "cosmictera-build/ON.md": docs["cosmictera-build/ON.md"]
                + "\n\n" + record + "\n"}, col

    on_headline = "# {} tes terkumpul; hasil: CHECKLIST.md †"
    head = _HEADLINES[_CHECKLIST]
    return [
        ("S1 one folder file is off by one", "G1",
         same(lambda d, c: (_swap_figure(d, _CHECKLIST, head, c.collected + 1), c))),
        ("S1 one folder file is off by one", "G7",
         same(lambda d, c: (_swap_figure(d, _CHECKLIST, head, c.collected + 1), c))),
        ("S1b a folder file states its figure twice", "G1",
         same(lambda d, c: (_swap(d, "cosmictera-build/ON.md", on_headline.format(
             _grouped(c.collected)), on_headline.format(_grouped(c.collected)) * 2), c))),
        ("S2 every place agrees on one more", "G2", same(every_figure)),
        ("S2 every place agrees on one more", "G7", same(every_figure)),
        ("S3 a file outside the folder changes its figure", "G7",
         same(lambda d, c: (_swap_figure(d, "README.md", _POSITIONS[0][1], c.collected - 1),
                            c))),
        ("S3b a position is quoted twice", "G7",
         same(lambda d, c: (_swap(d, "README.md", f"tests/           {_grouped(c.collected)} test",
                                  f"tests/           {_grouped(c.collected)} test\n" * 2), c))),
        ("S4 a stale figure in another document", "G4",
         same(lambda d, c: ({**d, "docs/ARCHITECTURE.md": d["docs/ARCHITECTURE.md"]
                             + f"\nAda {_grouped(c.collected - 100)} tes di sini.\n"}, c))),
        ("S5 the pass claim back in ON.md", "G5",
         same(lambda d, c: (_swap(d, "cosmictera-build/ON.md",
                                  f"# {_grouped(c.collected)} tes terkumpul; hasil: CHECKLIST.md †",
                                  f"# {_grouped(c.collected)} lulus, 0 dilewati"), c))),
        ("S6a the stale one-breath claim back", "G5",
         same(lambda d, c: (_swap(d, _CHECKLIST,
                                  f"# {_grouped(c.collected)} tes terkumpul; hasilnya di † atas",
                                  "# 5.019 lulus, 0 dilewati"), c))),
        ("S6b an exception no longer matches", "G5",
         same(lambda d, c: (_swap(d, "cosmictera-build/PAPAN.md", "berbunyi 4.519 lulus",
                                  "berbunyi 4.520 lulus"), c))),
        ("S6c an exception's sentence is gone", "G5",
         same(lambda d, c: (_swap(d, "cosmictera-build/PAPAN.md",
                                  "berbunyi 4.519 lulus / 16 dilewati", "berbunyi lain"), c))),
        ("S7 the record's pass count is off by one", "G6",
         same(lambda d, c: (_with_record(d, p=1), c))),
        ("S7b the record names another collected figure", "G6",
         same(lambda d, c: (_swap_figure(d, _CHECKLIST, _POSITIONS[3][1], c.collected + 1),
                            c))),
        ("S8 one more test, nothing re-measured", "G2",
         same(lambda d, c: (d, _Collection(c.collected + 1, c.module_skips,
                                           c.nodes | {"tests/test_new.py::test_new"})))),
        ("S8 one more test, nothing re-measured", "G6",
         same(lambda d, c: (d, _Collection(c.collected + 1, c.module_skips,
                                           c.nodes | {"tests/test_new.py::test_new"})))),
        ("S8 one more test, nothing re-measured", "G7",
         same(lambda d, c: (d, _Collection(c.collected + 1, c.module_skips,
                                           c.nodes | {"tests/test_new.py::test_new"})))),
        ("S8b the collection leaves this file out", "G2",
         same(lambda d, c: (d, _Collection(c.collected, c.module_skips, frozenset(
             n.replace(f"{_SELF}::", "tests/test_elsewhere.py::") for n in c.nodes))))),
        ("S8c a node id the parser missed", "G2",
         same(lambda d, c: (d, _Collection(c.collected, c.module_skips,
                                           c.nodes - {sorted(c.nodes)[0]})))),
        ("S9a the record is gone", "G6",
         same(lambda d, c: (_swap(d, _CHECKLIST, "Lari terakhir,", "Lari lain,"), c))),
        ("S9b the record is written twice", "G6",
         same(lambda d, c: ({**d, "cosmictera-build/ON.md": d["cosmictera-build/ON.md"]
                             + "\n\n" + _record(d).group(0) + "\n"}, c))),
        ("S9c the record leaves CHECKLIST.md", "G6", same(moved_record)),
        ("S10a a failure without its name", "G6", failure_without_name),
        ("S10b a name the collection does not hold", "G6", unknown_failure_name),
        ("S10c one test both failed and errored", "G6", double_counted),
        ("S10e a name under a list that counts 0", "G6",
         same(lambda d, c: (_with_record(d, error=f"`{_not_failed(d, c)}`."), c))),
        ("S10f one failure named twice", "G6", duplicate_failure_name),
        ("S10d an error written as a failure", "G6", error_as_failure),
    ]


@pytest.mark.parametrize(("case", "guard", "build"), _sabotages(),
                         ids=[f"{case} -> {guard}" for case, guard, _ in _sabotages()])
def test_each_sabotage_is_refused_by_its_guard(
    case: str, guard: str, build: Callable[[Inputs], tuple[Inputs, Inputs]],
) -> None:
    (docs, col), (bad_docs, bad_col) = build((dict(_tracked_markdown()), _collection()))
    assert _GUARDS[guard](docs, col) == [], f"{guard} is already red before {case!r}"
    assert _GUARDS[guard](bad_docs, bad_col), f"{guard} let {case!r} through"


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
