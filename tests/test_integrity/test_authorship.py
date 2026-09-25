"""Authorship attribution must be identical everywhere it appears.

The name of record travels through source code, documentation, a proprietary
LICENSE, patent release declarations, certificates, and release manifests. Each
of those is edited by hand at some point, and a name that drifts in one of them
is invisible until someone reads that file — which, for a legal instrument, may
be long after it matters.

These tests pin every occurrence to the canonical form in AUTHORS.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

import pytest

ROOT = Path(__file__).resolve().parents[2]

CANONICAL_NAME = "Maulana Amratulloh"
CANONICAL_ROLE = "Inventor & Chief Architect"
CANONICAL_KEY_ID = "MA-SIG"
# The foundation is the legal entity of record; HMCL is its research unit, so
# the canonical form names both and in that order. The rights holder is
# deliberately NOT the institution -- patents are held by the inventor
# personally, and AUTHORS says so under its own heading.
INSTITUTION = ("Yayasan Akademi Hijaiyyah Indonesia — HMCL "
               "(Hijaiyyah Mathematics Computational Laboratory)")
DATASET_SEAL = "f82d385917ffe32ae2b5711409b1341e90934c52172ae9d0fa68888e3b9c51c8"

# Directories that are vendored, generated, or otherwise not ours to police.
SKIP_DIRS = {
    ".git", "node_modules", "dist", ".vite", "__pycache__",
    ".venv", ".venv2", ".venv-mac", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "three.js-master", "build",
}
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".ico", ".ttf", ".woff",
                 ".woff2", ".zip", ".rom", ".vvp", ".vcd", ".pyc", ".bin"}


def repo_text_files() -> List[Path]:
    """Every text file in the repo we are responsible for."""
    out: List[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if "egg-info" in str(path):          # regenerated from pyproject.toml
            continue
        out.append(path)
    return out


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


#: The owner's decision, 26 September 2026. ONE file, named by its exact path,
#: may carry the superseded publisher and author names: it is the owner's list
#: of manuscript corrections, kept outside the engineering source on purpose,
#: and a list of corrections names what it corrects. The exception is by path
#: only -- not by name, not by suffix, not by folder -- so any other file that
#: carries an old name is still red, a sibling in the same folder included. It
#: covers the two superseded-name guards and nothing else: a variant spelling
#: of the name of record is still caught in this file. The guard does not read
#: the file at all; neither did the change that put it here.
HISTORICAL_NAMES_ALLOWED = frozenset({
    "Buku Matematika Hijaiyyah/PERBAIKAN_NASKAH_EDISI_I_TAMBAHAN_2026-09-25.txt",
})


def superseded_in(pattern: re.Pattern[str], files: List[Path] | None = None,
                  root: Path = ROOT) -> List[str]:
    """Every file carrying `pattern`, less this file itself and the one path
    the owner allowed to carry historical names -- which is skipped before it
    is read, not read and then forgiven."""
    out = []
    for path in repo_text_files() if files is None else files:
        rel = path.relative_to(root).as_posix()
        if path.name == Path(__file__).name or rel in HISTORICAL_NAMES_ALLOWED:
            continue
        if pattern.search(read(path)):
            out.append(rel)
    return out


# ── the canonical record itself ──────────────────────────────────

def test_authors_file_exists_and_declares_the_canonical_form() -> None:
    text = read(ROOT / "AUTHORS")
    assert CANONICAL_NAME in text
    assert CANONICAL_ROLE in text
    assert INSTITUTION in text


def test_notice_file_exists_and_carries_attribution() -> None:
    text = read(ROOT / "NOTICE")
    assert CANONICAL_NAME in text
    assert CANONICAL_ROLE in text
    assert DATASET_SEAL in text, "NOTICE must cite the canonical dataset seal"


# ── no superseded name may survive anywhere ──────────────────────

# Case-sensitive, and the given name alone is not enough: "firman" is an
# ordinary Indonesian word (as in "Allah berfirman"), so matching it loosely
# flags devotional prose as an authorship defect.
SUPERSEDED = re.compile(r"Firman\s+Arief|Hidayatullah")


# The publisher of record changed once the foundation's notarial deed was
# issued: PT Puri Pertiwi International no longer publishes this work, and
# Yayasan Akademi Hijaiyyah Indonesia does. A superseded PUBLISHER on a patent
# instrument misstates who holds the publishing right -- the same class of
# defect as a superseded author, and it survived in five files (both research
# proposals, twice each, plus a scratch draft) after the folder's own
# certificate had been corrected. The optional "PT." catches "PT. Puri
# Pertiwi" as well.
#
# IGNORECASE is not cosmetic: the first version of this guard was
# case-sensitive, swept the whole repo, reported clean -- and two React
# footers were rendering "PT PURI PERTIWI INTERNATIONAL" in upper case the
# entire time, on the landing page no less. A guard that passes while the
# string is on screen is the exact defect this file exists to catch.
SUPERSEDED_PUBLISHER = re.compile(r"(?:PT\.?\s+)?Puri\s+Pertiwi", re.IGNORECASE)


def test_no_superseded_publisher_remains() -> None:
    """A patent document naming the wrong publisher names the wrong party.

    Rights stay with the inventor personally either way -- see AUTHORS -- but
    the publisher line is a factual claim about a legal entity, and it must
    track the deed rather than whichever draft it was copied from.
    """
    offenders = superseded_in(SUPERSEDED_PUBLISHER)
    assert not offenders, (
        f"superseded publisher (PT Puri Pertiwi International) still present "
        f"in: {offenders}. The publisher of record is "
        f"Yayasan Akademi Hijaiyyah Indonesia."
    )


# The website of record moved with the publisher. hybit.tech remains valid as
# the technology brand; what may not survive is a legal instrument presenting
# it as the official site of the publishing institution.
CANONICAL_WEBSITE = "www.akademihijaiyyahindonesia.com"

PATENT_INSTRUMENTS = [
    "OFFICIAL_PATENT_RELEASE/CERTIFICATE.json",
    "OFFICIAL_PATENT_RELEASE/PATENT_RELEASE_DECLARATION_ID.md",
    "OFFICIAL_PATENT_RELEASE/PATENT_RELEASE_DECLARATION_EN.md",
    "OFFICIAL_PATENT_RELEASE/README.md",
]


def test_patent_certificate_seals_the_canonical_dataset() -> None:
    """The seal on the patent certificate must be the seal of the dataset.

    It was not. `master_table.sha256` carried
    f85251e0daf5bb977a381738accaeb599a05445484158fc158e3ea279902302c, which is
    a real hash in this repo -- `artifacts.hb.hash` in data/hm28_manifest.json,
    the MH-28-v.1.0-HC18D.hb tooling artifact. A tooling artifact is not the
    canonical dataset, so the certificate was sealing the wrong object under
    the right label, and nothing read the two together to notice. NOTICE is
    already pinned to DATASET_SEAL above; this pins the patent instrument to
    the same constant.
    """
    path = book_relative("OFFICIAL_PATENT_RELEASE/CERTIFICATE.json")
    if not path.exists():                                     # pragma: no cover
        pytest.skip("CERTIFICATE.json not present under any *Matematika Hijaiyyah* folder")
    doc = json.loads(read(path))
    assert doc["master_table"]["sha256"] == DATASET_SEAL, (
        "the patent certificate seals a hash that is not the canonical dataset seal")


@pytest.mark.parametrize("tail", PATENT_INSTRUMENTS)
def test_patent_instrument_names_the_foundation_and_its_website(tail: str) -> None:
    """Each instrument must name the publisher of record and its live site."""
    path = book_relative(tail)
    if not path.exists():                                     # pragma: no cover
        pytest.skip(f"{tail} not present under any *Matematika Hijaiyyah* folder")
    text = read(path)
    assert "Yayasan Akademi Hijaiyyah Indonesia" in text, (
        f"{tail} does not name the publisher of record")
    assert CANONICAL_WEBSITE in text, (
        f"{tail} does not carry the live website {CANONICAL_WEBSITE}")



def test_no_superseded_author_name_remains() -> None:
    offenders = superseded_in(SUPERSEDED)
    assert not offenders, f"superseded author name still present in: {offenders}"


def test_the_historical_names_exception_is_one_exact_path() -> None:
    """Narrow by construction: one entry, a whole path to one dated file, no
    wildcard and no folder -- so it cannot quietly grow into 'the manuscript
    folder' or 'every .txt'."""
    assert len(HISTORICAL_NAMES_ALLOWED) == 1
    for rel in HISTORICAL_NAMES_ALLOWED:
        assert not any(c in rel for c in "*?[]"), rel
        assert not rel.endswith("/") and "/" in rel, rel
        assert re.search(r"_\d{4}-\d{2}-\d{2}\.txt$", rel), rel


def test_the_exception_reaches_no_other_file(tmp_path: Path) -> None:
    """R3 on the exception itself. The exact path is spared; a sibling in the
    same folder, another .txt, and a file elsewhere carrying the same old
    names are all still named. Built in a scratch tree -- the owner's file is
    neither read nor copied."""
    (allowed,) = HISTORICAL_NAMES_ALLOWED
    old = "PT Puri Pertiwi International, Firman Arief Hidayatullah\n"
    paths = [tmp_path / allowed,
             tmp_path / "Buku Matematika Hijaiyyah" / "PERBAIKAN_NASKAH_LAIN.txt",
             tmp_path / "Buku Matematika Hijaiyyah" / "sub" / Path(allowed).name,
             tmp_path / "NOTES.txt"]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old, encoding="utf-8")
    want = sorted(p.relative_to(tmp_path).as_posix() for p in paths[1:])
    for pattern in (SUPERSEDED_PUBLISHER, SUPERSEDED):
        assert sorted(superseded_in(pattern, paths, root=tmp_path)) == want


# ── the canonical spelling must not drift ────────────────────────

# Any "Maulana …" that is not exactly the canonical name is a drifted variant
# (extra letters, dropped letters, different transliteration).
MAULANA_ANY = re.compile(r"Maulana\s+[A-Za-z]+")


def test_no_variant_spelling_of_the_canonical_name() -> None:
    bad = []
    for path in repo_text_files():
        if path.name == Path(__file__).name:
            continue
        for match in MAULANA_ANY.finditer(read(path)):
            if match.group(0) != CANONICAL_NAME:
                bad.append(f"{path.relative_to(ROOT)}: {match.group(0)!r}")
    assert not bad, f"variant spelling of the name of record: {bad}"


# ── legal instruments carry name and role ────────────────────────


def book_relative(tail: str) -> Path:
    """Resolve a path under the book folder, whichever name it carries.

    The folder was renamed 'Matematika Hijaiyyah/' -> 'Buku Matematika
    Hijaiyyah/' and .gitignore deliberately ignores BOTH spellings, so this
    list went on naming the old one and four tests skipped themselves as
    "not present" while the documents sat on disk the whole time. A skip
    reads like an absent file; it was an absent PATH. tests/test_integrity/
    test_bab_satu.py already globbed for the folder rather than naming it,
    which is the idiom this now borrows -- a legal instrument that stops
    being checked because a directory was renamed is the failure mode these
    tests exist to prevent.
    """
    for parent in sorted(ROOT.glob("*Matematika Hijaiyyah*")):
        candidate = parent / tail
        if candidate.exists():
            return candidate
    return ROOT / "Matematika Hijaiyyah" / tail


LEGAL_DOCS = [
    "LICENSE",
    "NOTICE",
    "AUTHORS",
    "release/HL-18E-v1.0/PATENT_RELEASE.md",
]

# Under the book folder, which is gitignored and whose name changed -- see
# book_relative. These are the patent instruments themselves.
BOOK_LEGAL_DOCS = [
    "OFFICIAL_PATENT_RELEASE/PATENT_RELEASE_DECLARATION_ID.md",
    "OFFICIAL_PATENT_RELEASE/PATENT_RELEASE_DECLARATION_EN.md",
    "OFFICIAL_PATENT_RELEASE/README.md",
]


@pytest.mark.parametrize("relpath", LEGAL_DOCS)
def test_legal_document_names_the_inventor(relpath: str) -> None:
    path = ROOT / relpath
    if not path.exists():                                     # pragma: no cover
        pytest.skip(f"{relpath} not present")
    assert CANONICAL_NAME in read(path), f"{relpath} does not name the inventor"


@pytest.mark.parametrize("tail", BOOK_LEGAL_DOCS)
def test_book_legal_document_names_the_inventor(tail: str) -> None:
    """The book folder is not in git, so a checkout without it skips here --
    but a checkout WITH it must be checked, and until book_relative existed
    these three skipped even then."""
    path = book_relative(tail)
    if not path.exists():                                     # pragma: no cover
        pytest.skip(f"{tail} not present under any *Matematika Hijaiyyah* folder")
    assert CANONICAL_NAME in read(path), f"{tail} does not name the inventor"


def test_license_states_the_role() -> None:
    assert CANONICAL_ROLE in read(ROOT / "LICENSE")


# ── signing key id ───────────────────────────────────────────────

# The key id is derived from the name of record, so it drifts for the same
# reason the name does — and it appears in signature blocks that are read as
# provenance. "FAH-SIG" carried the superseded initials.
SUPERSEDED_KEY_ID = "FAH-SIG"

KEY_ID_SITES = [
    "LICENSE",
    "CHANGELOG.md",
    "src/hijaiyyah/gui/tabs/release.py",
]


@pytest.mark.parametrize("relpath", KEY_ID_SITES)
def test_signature_key_id_is_canonical(relpath: str) -> None:
    text = read(ROOT / relpath)
    assert SUPERSEDED_KEY_ID not in text, f"{relpath} still carries {SUPERSEDED_KEY_ID}"
    assert CANONICAL_KEY_ID in text, f"{relpath} does not carry {CANONICAL_KEY_ID}"


def test_release_tab_key_id_constant() -> None:
    from hijaiyyah.gui.tabs.release import AUTHOR_KEY_ID, AUTHOR_NAME

    assert AUTHOR_KEY_ID == CANONICAL_KEY_ID
    assert AUTHOR_NAME == CANONICAL_NAME


# ── machine-readable records carry name and role ─────────────────

CERTIFICATES = [
    ("release/HL-18E-v1.0/CERTIFICATE.json", "author"),
    ("release/HL-18E-v1.0/MANIFEST.json", "author"),
]

BOOK_CERTIFICATES = [("OFFICIAL_PATENT_RELEASE/CERTIFICATE.json", "inventor")]


@pytest.mark.parametrize("tail,key", BOOK_CERTIFICATES)
def test_book_certificate_records_name_and_role(tail: str, key: str) -> None:
    """Same rename, same silent skip -- see book_relative."""
    path = book_relative(tail)
    if not path.exists():                                     # pragma: no cover
        pytest.skip(f"{tail} not present under any *Matematika Hijaiyyah* folder")
    doc = json.loads(read(path))
    assert doc.get(key) == CANONICAL_NAME, f"{tail}: {key} drifted"
    assert doc.get(f"{key}_role") == CANONICAL_ROLE, f"{tail}: {key}_role drifted"


# The release folder seals the dataset too, and it sealed a value that
# measured nothing at all. Both files carried
# 81af756ba05a47940e45c6d2958c2a6af92eeb8cc4542b344e4a4889435e3af2 while
# PATENT_RELEASE.md beside them quoted the canonical seal -- three files in one
# directory, two of them wrong, and no test read any two of them together.
# Unlike the book certificate's f85251e0 (which was at least a real hash of a
# real artifact, just the wrong object), 81af756b matches nothing: not the
# dataset seal, not the SHA-256 of data/hm28.json as bytes
# (38338183d2005be624cb1cbe965e0ac360624af6301c3e9e3ef413e61d0c891e), not any
# file under 5 MB in this repository. It was a number, not a measurement.
RELEASE_SEALS = [
    ("release/HL-18E-v1.0/CERTIFICATE.json", "master_table_sha256"),
    ("release/HL-18E-v1.0/MANIFEST.json", "sha256"),
]

def test_the_canonical_seal_constant_is_what_the_table_actually_hashes() -> None:
    """DATASET_SEAL is a transcription until something measures it.

    Every other test in this file compares one transcription against another:
    NOTICE quotes the seal, the certificates quote the seal, and they are
    asserted equal to a string literal at the top of this file. If the table
    itself ever changed, all of those would agree with each other and all of
    them would be wrong together -- which is precisely how three different
    values came to claim the same label. This test is the one place the
    constant meets the object it names.
    """
    from hijaiyyah.core.master_table import MASTER_TABLE

    assert MASTER_TABLE.compute_sha256() == DATASET_SEAL, (
        "the Master Table no longer hashes to the seal every legal instrument "
        "in this repository quotes -- either the table changed or the seal did, "
        "and both need a deliberate decision, not a test edit")

@pytest.mark.parametrize("relpath,key", RELEASE_SEALS)
def test_release_record_seals_the_canonical_dataset(relpath: str, key: str) -> None:
    """A patent release that seals an unmeasurable number seals nothing."""
    path = ROOT / relpath
    if not path.exists():                                     # pragma: no cover
        pytest.skip(f"{relpath} not present")
    doc = json.loads(read(path))
    assert doc.get(key) == DATASET_SEAL, (
        f"{relpath}: {key} is not the canonical dataset seal")

def test_the_release_folder_agrees_with_itself_about_the_seal() -> None:
    """PATENT_RELEASE.md sat beside two JSONs disagreeing with it.

    It was the only one of the three that was right, and being right in
    isolation is worth nothing when the two machine-readable files a verifier
    would actually parse said something else.
    """
    md = ROOT / "release/HL-18E-v1.0/PATENT_RELEASE.md"
    if not md.exists():                                       # pragma: no cover
        pytest.skip("PATENT_RELEASE.md not present")
    assert DATASET_SEAL in read(md), (
        "PATENT_RELEASE.md no longer quotes the canonical dataset seal")

@pytest.mark.parametrize("relpath,key", CERTIFICATES)
def test_certificate_records_name_and_role(relpath: str, key: str) -> None:
    path = ROOT / relpath
    if not path.exists():                                     # pragma: no cover
        pytest.skip(f"{relpath} not present")
    doc = json.loads(read(path))
    assert doc.get(key) == CANONICAL_NAME, f"{relpath}: {key} drifted"
    assert doc.get(f"{key}_role") == CANONICAL_ROLE, f"{relpath}: {key}_role drifted"


# ── the book certificate's verification summary ──────────────────

# Ten figures sat in `verification_summary` since March 2026 and nothing read
# any of them. Measured on 11 September 2026, four were exactly right and two
# were badly stale (software_tests said 1611 against a suite of 4.798;
# rtl_hardware_tests said 174 against 253 assertions in 20 benches). The four
# that were right are pinned here, because being right by luck for six months
# is what every other defect in this file started as.
#
# The chapter figures are deliberately NOT pinned: the whole patent release is
# to be reworked against the final Tang Nano 20K results, with BAB III rebuilt
# to match, so fixing them to today's values would pin a number that is already
# scheduled to change.
CERTIFICATE_MEASURED_FIGURES = [
    ("guard_g1_g4", "112/112 PASS"),
    ("guard_t1_t2", "56/56 PASS"),
    ("exometric_r1_r5", "140/140 PASS"),
    ("injectivity_pairs", "378/378 UNIQUE"),
]

@pytest.mark.parametrize("key,value", CERTIFICATE_MEASURED_FIGURES)
def test_certificate_verification_figure_holds(key: str, value: str) -> None:
    """Each of these was measured against the code and matched."""
    path = book_relative("OFFICIAL_PATENT_RELEASE/CERTIFICATE.json")
    if not path.exists():                                     # pragma: no cover
        pytest.skip("CERTIFICATE.json not present under any *Matematika Hijaiyyah* folder")
    summary = json.loads(read(path))["verification_summary"]
    assert summary.get(key) == value, f"{key} drifted from the measured value"

def test_the_certificate_figures_are_what_the_guards_actually_produce() -> None:
    """28 letters x 4 structural guards, x 2 turning guards, x 5 exometric.

    Each product is asserted separately rather than as one total, because a
    total can stay right while two of its terms move in opposite directions --
    which is how 308 came to be both a sum of the details and wrong.
    """
    import itertools

    from hijaiyyah.algebra import exometric
    from hijaiyyah.core.guards import guard_detail
    from hijaiyyah.core.master_table import MASTER_TABLE

    entries = MASTER_TABLE.all_entries()
    details = [guard_detail(e) for e in entries]

    assert sum(1 for d in details for k in ("R1", "R2", "R3", "R4")
               if d[k] is True) == 112, "guard_g1_g4 is no longer 112/112"
    assert sum(1 for d in details for k in ("T1", "T2")
               if d[k] is True) == 56, "guard_t1_t2 is no longer 56/56"

    audits = [exometric.audit(exometric.build(e)) for e in entries]
    assert sum(1 for a in audits for k in ("R1", "R2", "R3", "R4", "R5")
               if a[k] is True) == 140, "exometric_r1_r5 is no longer 140/140"

    pairs = list(itertools.combinations(entries, 2))
    assert len(pairs) == 378 and all(
        tuple(a.vector) != tuple(b.vector) for a, b in pairs
    ), "injectivity_pairs is no longer 378/378 unique"

# ── the release notes quote measurable numbers ───────────────────

# Every figure in RELEASE_NOTES.md is measurable, so none of them has any
# business being a transcription. They were all correct when measured on
# 11 September 2026 -- but so was PATENT_RELEASE.md's seal while the two JSONs
# beside it were wrong, and correctness that nothing re-measures is just a
# number that has not drifted yet.
#
# The diameter deserves its own note. `intrametric.diameter_sq()` sums over
# `range(14)`, not all 18 components -- the intra metric is defined on the
# first fourteen. Measured across all 18 the diameter is 8.602, not 8.367, so
# a reader who reimplements it from the vector width alone gets a different
# number and concludes the release notes are wrong. They are not; the metric
# is narrower than the vector.
RELEASE_NOTES_FIGURES = [
    ("13/13 theorem tests pass", "13/13"),
    ("28/28 letters guard-verified", "28/28"),
    ("378/378 injectivity pairs confirmed", "378/378"),
]

@pytest.mark.parametrize("line,figure", RELEASE_NOTES_FIGURES)
def test_release_notes_figure_is_present(line: str, figure: str) -> None:
    path = ROOT / "release/HL-18E-v1.0/RELEASE_NOTES.md"
    if not path.exists():                                     # pragma: no cover
        pytest.skip("RELEASE_NOTES.md not present")
    assert line in read(path), f"RELEASE_NOTES.md no longer states {figure}"

def test_the_release_notes_figures_are_what_the_code_measures() -> None:
    """The half that matters: the numbers, measured, not read."""
    import itertools

    from hijaiyyah.algebra import intrametric
    from hijaiyyah.core.guards import guard_check
    from hijaiyyah.core.master_table import MASTER_TABLE
    from hijaiyyah.theorems.test_suite import TheoremTestSuite

    results = TheoremTestSuite().run_all()
    failed = [f"{r.ref} {r.name}: {r.message}" for r in results if not r.passed]
    assert len(results) == 13 and not failed, f"not 13/13: {failed}"

    entries = MASTER_TABLE.all_entries()
    assert sum(1 for e in entries if guard_check(e)) == 28, "not 28/28 guard-verified"

    pairs = list(itertools.combinations(entries, 2))
    assert len(pairs) == 378, "C(28,2) is not 378 -- the alphabet changed size"
    assert all(tuple(a.vector) != tuple(b.vector) for a, b in pairs), (
        "two letters share a vector -- injectivity is broken")

    assert intrametric.diameter_sq() == 70, (
        "diam^2 is no longer 70, so the release notes' sqrt(70) is now a false claim")

def test_the_patent_release_does_not_claim_a_lockdown_it_does_not_have() -> None:
    """It claimed one for months, and measurement said otherwise.

    "all underlying data files ... have been **permanently locked (Read-Only)**
    at the filesystem level" -- measured, all seven sealed paths were mode 0o644
    or 0o700, every one writable by the owner. The claim was not merely stale;
    it was never true, and a patent instrument asserting a protection that does
    not exist is worse than one asserting none. The paragraph now describes the
    protection that does exist, which is measurement.
    """
    path = ROOT / "release/HL-18E-v1.0/PATENT_RELEASE.md"
    if not path.exists():                                     # pragma: no cover
        pytest.skip("PATENT_RELEASE.md not present")
    text = read(path)
    assert "permanently locked (Read-Only)** at the filesystem" not in text, (
        "the filesystem-lockdown claim is back, and it is still not true")
    assert "sealed by **measurement**" in text, (
        "PATENT_RELEASE.md no longer states how the dataset is actually sealed")

# ── package metadata ─────────────────────────────────────────────

def test_package_author_matches() -> None:
    from hijaiyyah import __author__

    assert __author__ == CANONICAL_NAME


def test_pyproject_author_matches() -> None:
    try:
        import tomllib
    except ModuleNotFoundError:                               # pragma: no cover
        pytest.skip("tomllib requires Python 3.11+")
    data = tomllib.loads(read(ROOT / "pyproject.toml"))
    names = [a.get("name") for a in data["project"]["authors"]]
    assert CANONICAL_NAME in names, f"pyproject authors: {names}"
