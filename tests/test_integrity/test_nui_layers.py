"""The twelve-layer map, held against the repository it describes.

NUI/LAYERS.md answers the owner's demand that every capability carry five
things: goal, existing assets, missing components, verification method, exit
criteria. A map like that fails in one direction only -- a layer quietly
acquiring assets it does not have -- so what is pinned here is the shape of
every layer, the existence of every file it cites, and the two layers that
have nothing at all.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "NUI" / "LAYERS.md"
TEXT = DOC.read_text(encoding="utf-8")
FIELDS = ("**Tujuan.**", "**Aset yang sudah ada", "**Yang belum ada.**",
          "**Cara verifikasi.**", "**Syarat selesai.**")
# Measured 21 September 2026, and the honest half of the map: Linux and
# autonomous engineering have no asset in this repository at all. A layer
# leaving this set has been given something, and that must be deliberate.
EMPTY = {5, 11}


def sections() -> dict[int, str]:
    out = {}
    parts = re.split(r"\n## Lapis (\d+) — ", TEXT)
    for number, body in zip(parts[1::2], parts[2::2], strict=True):
        out[int(number)] = body.split("\n## ")[0]
    return out


def test_the_map_covers_all_twelve_layers() -> None:
    assert sorted(sections()) == list(range(12)), sorted(sections())


def test_every_layer_carries_the_five_fields_the_owner_demanded() -> None:
    for number, body in sections().items():
        for field in FIELDS:
            assert field in body, f"layer {number} is missing {field}"


def test_the_layers_with_nothing_say_so_and_the_others_do_not() -> None:
    """Layer 5 and layer 11 have no asset in this repository. Writing a plan
    into either would be inventing an asset; writing "none" into a layer that
    has twenty-seven tests would be throwing one away."""
    for number, body in sections().items():
        empty = "**Tidak ada.**" in body
        assert empty == (number in EMPTY), (number, empty)


def test_every_file_the_map_cites_exists() -> None:
    """The failure that matters: a layer claiming an asset that is not there."""
    cited = set(re.findall(r"`([a-zA-Z0-9_./]+\.(?:py|md|v|hasm))`", TEXT))
    missing = []
    for name in cited:
        if "/" not in name:            # bare module names, resolved below
            continue
        if not (ROOT / name).exists():
            missing.append(name)
    assert not missing, missing
    for bare in {n for n in cited if "/" not in n}:
        found = list(ROOT.rglob(bare))
        assert found, f"{bare} is cited but nowhere in the tree"


def test_the_counts_in_the_map_are_the_counts_in_the_tree() -> None:
    modules = len(list((ROOT / "src" / "hijaiyyah" / "nui").glob("*.py")))
    programs = (len(list((ROOT / "rtl" / "programs").glob("*.hasm")))
                + len(list((ROOT / "rtl" / "programs" / "bench").glob("*.hasm"))))
    assert f"**{modules} modul**" in TEXT, modules
    assert f"**{programs} program HASM**" in TEXT, programs


def test_the_two_numberings_are_both_kept() -> None:
    """ROADMAP.md's phases predate the owner's layers. Deleting either would
    be tidying a conflict away instead of recording it."""
    assert (ROOT / "NUI" / "ROADMAP.md").exists()
    assert "Fase 0" in TEXT and "Lapis 1" in TEXT
    assert "konflik dicatat" in TEXT


def test_what_may_not_be_claimed_is_written_down() -> None:
    for forbidden in ("AGI", "kesadaran", "inteligensi manusia"):
        assert forbidden in TEXT, forbidden
    assert "R2" in TEXT
