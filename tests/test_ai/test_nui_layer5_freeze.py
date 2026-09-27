"""Layer 5 frozen, held to the store it points at and to what it may hold.

The owner's operational close of Layer 5, 27 September 2026: the main
instance's run frozen as the reference, freshness and delta proven, then a
freeze in Layer 4's shape. Unlike Layer 4, the evidence is not in the
repository (K-11), so the committed freeze may hold pointers and hashes only.

What runs here needs no host and no store: the committed freeze is held to
its own page, to the owner's baseline and to what it may contain, and
verify() is held to a store built in a temporary directory by layer5.record()
itself -- green while the store matches, red the moment one byte does not.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import layer5  # noqa: E402
from hijaiyyah.nui import layer5_freeze as l5  # noqa: E402

FROZEN = json.loads(l5.MODEL.read_text(encoding="utf-8"))
POINTER = {"run_id", "observed_at", "status", "exit_code", "stdout", "stdout_sha256",
           "stderr", "stderr_sha256"}
COLLECTORS = [c["name"] for c in layer5.load()["collectors"]]


def test_the_page_is_drawn_from_the_freeze() -> None:
    assert l5.PAGE.read_text(encoding="utf-8") == l5.page(FROZEN)


def test_the_baseline_is_the_owners() -> None:
    """Eleven collectors on the main instance at the run the owner froze:
    nine PASS, journal unavailable for permissions, containers unavailable
    because the command is absent -- as they are, not widened (K-12, K-13)."""
    base = FROZEN["baseline"]
    assert FROZEN["vm_name"] == "cosmictera-layer5" and list(base) == COLLECTORS
    status = {c: p["status"] for c, p in base.items()}
    assert status.pop("journal") == "unavailable_due_to_permissions"
    assert status.pop("containers") == "unavailable_command_absent"
    assert set(status.values()) == {"PASS"} and len(status) == 9
    for c, p in base.items():
        assert p["run_id"] == l5.BASELINE[c]
        for key in ("stdout", "stderr"):
            assert p[key].startswith(f"observations/cosmictera-layer5/{p['run_id']}/"), p[key]


def test_the_freeze_holds_pointers_and_hashes_never_the_observation() -> None:
    """K-11: the repository holds no runtime observation. Every baseline and
    comparison entry is a pointer and its hashes; every delta is counts and
    the hash of its items."""
    for part in ("baseline", "compared_with"):
        for pointer in FROZEN[part].values():
            assert set(pointer) == POINTER
    for d in FROZEN["delta"].values():
        assert set(d) == {"from", "to", "status", "appeared", "disappeared", "changed",
                          "items_sha256"}
        assert all(isinstance(d[k], int) for k in ("appeared", "disappeared", "changed"))


def test_the_freshness_rule_is_recorded_and_not_held() -> None:
    """Its value is the owner's to set after the freeze; at the freeze it is
    unset, and so nothing was claimed current."""
    assert "freshness_rule" not in l5.HELD
    assert FROZEN["freshness_rule"]["stale_after_seconds"] is None


def test_the_tag_carries_the_day_of_the_freeze() -> None:
    assert FROZEN["tag"] == l5.TAG == "layer5-freeze-2026-09-27"


class _Ran:
    def __init__(self, cmd: list[str], extra: str = "") -> None:
        self.returncode, self.stdout, self.stderr = 0, f"out of {' '.join(cmd[4:])}\n{extra}", ""
        if cmd[4] == "journalctl":
            self.returncode, self.stdout = 1, ""
            self.stderr = "No journal files were opened due to insufficient permissions.\n"
        if cmd[4] == "docker":
            self.returncode, self.stdout, self.stderr = 127, "", "docker: command not found\n"


@pytest.fixture()
def frozen_here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], Path]:
    """Two runs of the main instance in a store of its own, and a freeze of
    them, built the way the real one was."""
    store = tmp_path / "observations"
    store.mkdir()
    monkeypatch.setattr(layer5, "store", lambda: store)
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    first = layer5.record(l5.VM, run=lambda cmd, **_: _Ran(cmd), into=store)
    time.sleep(1.1)  # run_ids are to the second
    second = layer5.record(l5.VM, run=lambda cmd, **_: _Ran(cmd, "a new line\n"), into=store)
    monkeypatch.setattr(l5, "BASELINE", {c: first.name for c in COLLECTORS})
    monkeypatch.setattr(l5, "COMPARED_WITH", second.name)
    monkeypatch.setattr(l5, "HISTORY", [("first", f"{l5.VM}/{first.name}"),
                                        ("second", f"{l5.VM}/{second.name}")])
    return json.loads(json.dumps(l5.build())), first


def test_verify_is_green_while_the_store_matches(frozen_here: tuple[dict[str, Any], Path]) -> None:
    model, _ = frozen_here
    assert l5.verify(model) == []
    for part in ("baseline", "compared_with"):
        assert all(set(p) == POINTER for p in model[part].values()), "what build() holds"
    assert all(isinstance(d["items_sha256"], str) for d in model["delta"].values())
    assert model["delta"]["routes"]["appeared"] == 1, "a whole-line rule sees the new line"
    assert model["delta"]["host_identity"]["appeared"] == 0, "a KEY=VALUE rule does not"


def test_verify_is_red_the_moment_one_byte_does_not(
        frozen_here: tuple[dict[str, Any], Path]) -> None:
    model, first = frozen_here
    path = first / "raw" / "routes.stdout"
    data = bytearray(path.read_bytes())
    data[0] ^= 1
    path.write_bytes(bytes(data))
    problems = l5.verify(model)
    assert problems and "no longer reads back" in problems[0] and "SHA-256" in problems[0]


def test_verify_names_a_moved_history_manifest(frozen_here: tuple[dict[str, Any], Path]) -> None:
    model, first = frozen_here
    manifest = first / "manifest.json"
    manifest.write_text(manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert "/history/0/sha256" in l5.verify(model)


def test_verify_says_when_the_store_is_not_there(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(layer5, "store", lambda: tmp_path / "nowhere")
    problems = l5.verify(FROZEN)
    assert problems and "is not on this machine" in problems[0]
