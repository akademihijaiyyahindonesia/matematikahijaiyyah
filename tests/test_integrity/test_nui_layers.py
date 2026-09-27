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
# Measured 21 September 2026 against the fourth directive: Linux had no asset
# in this repository at all. It left this set on 22 September 2026, when its
# skeleton -- collectors, a read-only guard, a VM configuration -- was built at
# the owner's request with no host to run it on. A layer leaving this set has
# been given something, and that must be deliberate.
EMPTY: set[int] = set()
#: Nothing as a NUI capability, with materials or hand-written tools nearby.
#: Writing "none" would throw the materials away; listing them as assets
#: would claim the capability.
PARTIAL = {5, 9, 10}


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


def test_the_layers_with_materials_but_no_capability_say_both() -> None:
    """Reasoning and engineering are neither full nor empty: the pieces exist,
    the NUI capability does not. Writing "none" would throw away the first
    half; writing an asset list would claim the second."""
    for number in PARTIAL:
        assert "**Tidak ada** sebagai" in sections()[number], number
    assert "Lapis 3 punya jejaknya" in sections()[9]
    assert "ditulis tangan" in sections()[10]
    assert "belum\nmengendalikannya" in sections()[5]


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


def test_every_numbering_is_kept_and_the_layers_are_keyed_by_name() -> None:
    """Three messages in one day numbered these layers three ways while the
    assets under them barely moved. The map is therefore keyed by NAME, the
    number is an attribute, and one table is the only place it lives.
    ROADMAP.md's Fase 0-5 is a fourth numbering and is mapped, not deleted."""
    assert (ROOT / "NUI" / "ROADMAP.md").exists()
    assert "| lapis (nama) | pesan 1 | pesan 2 | pesan 3 | **berlaku** |" in TEXT
    assert "Fase 2 = Lapis 2" in TEXT
    assert "Fase 4 = Lapis 10" in TEXT
    assert "Yang berlaku yang terakhir" in TEXT
    assert "dikunci pada **nama**" in TEXT


def test_the_layers_dropped_along_the_way_keep_their_assets() -> None:
    """Two layers stopped being numbered layers. Their assets did not stop
    existing, and a map that let them fall out with a number would be losing
    measurements to an edit."""
    assert "*Verifikasi fisik* (pesan 2)" in TEXT
    assert "*Perencanaan perbaikan otonom* (pesan 3)" in TEXT
    for kept in ("tangga bukti empat tingkat", "PAPAN.md", "place and route",
                 "fakta `board`", "K3–K6"):
        assert kept in TEXT, kept


def test_the_label_disagreement_and_its_answer_are_both_kept() -> None:
    """The second message marked Linux EH, which disagreed with RULES.md's own
    table; the third answered AT. Both halves stay: a page that kept only the
    answer would lose why it was asked. On 27 September 2026 the owner raised
    it to EH, once the host was measured -- and that stays beside the history."""
    layer5 = sections()[5]
    assert "EH" in layer5 and "**AT**" in layer5
    assert "dilaporkan" in layer5
    assert "**Label kini EH**" in layer5
    rules = (ROOT / "cosmictera" / "RULES.md").read_text(encoding="utf-8")
    assert "belum dikerjakan" in rules, "AT's definition moved"


def test_the_import_chain_the_map_prints_is_the_one_the_code_has() -> None:
    """Layer 1's example is a measurement, so it is re-measured here. The
    owner's chain had atom -> rack -> clockwork -> freeze -> multitask; the
    last two links are not there, and the map says so."""
    import ast

    nui = ROOT / "src" / "hijaiyyah" / "nui"
    names = {p.stem for p in nui.glob("*.py")}
    deps = {}
    for stem in ("atom", "rack", "clockwork", "freeze", "multitask"):
        tree = ast.parse((nui / f"{stem}.py").read_text(encoding="utf-8"))
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                tail = node.module.lstrip(".").split(".")[-1]
                if tail in names:
                    found.add(tail)
        deps[stem] = found
    assert deps["rack"] == {"atom"}
    assert deps["clockwork"] == {"atom", "rack"}
    assert deps["freeze"] == {"rack"}, "freeze imports rack, not clockwork"
    assert "freeze" not in deps["multitask"], "multitask does not touch freeze"
    section = sections()[1]
    assert "freeze    → rack" in section
    assert "multitask → dataset, model" in section


def test_what_may_not_be_claimed_is_written_down() -> None:
    for forbidden in ("AGI", "kesadaran", "inteligensi manusia"):
        assert forbidden in TEXT, forbidden
    assert "R2" in TEXT
