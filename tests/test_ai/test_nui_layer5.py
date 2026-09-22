"""Layer 5's skeleton, held before any host exists.

Nothing here runs a command. What is held: every collector the plan lists
passes the read-only guard, and the guard refuses what the first stage must
not do -- a forbidden command, a command off the allowlist, an argument a
shell could read, an option that writes or sends, a command that never stops.
The only way out is `limactl shell` in the VM, and on a machine without
limactl it refuses before calling anything. The VM configuration pins the
image digest recorded in NUI/LAYERS.md, mounts nothing, and names no URL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import layer5, usr  # noqa: E402


def test_every_collector_passes_the_guard() -> None:
    plan = layer5.plan()
    assert len(plan) == 9
    assert not [r for r in plan if "refused" in r], plan
    assert {r["area"] for r in plan} == {"host", "proses", "filesystem", "service",
                                        "jaringan", "kontainer"}


def test_a_catalog_collector_takes_its_argv_from_the_catalog() -> None:
    """R1: READ PROCESS is written once, in layer5_catalog.json."""
    catalog = {(e["action"], e["object"]): e["argv"]
               for e in usr.load("layer5_catalog")["entries"]}
    by_name = {c["name"]: c for c in layer5.load()["collectors"]}
    assert layer5.argv_of(by_name["processes"]) == catalog[("READ", "PROCESS")]
    assert layer5.argv_of(by_name["journal"]) == catalog[("READ", "JOURNAL")]
    assert "argv" not in by_name["processes"]


@pytest.mark.parametrize("argv, reason", [
    (["rm", "-rf", "/tmp/x"], "not-yet-allowed"),
    (["mv", "a", "b"], "not-yet-allowed"),
    (["kill", "1"], "not-yet-allowed"),
    (["systemctl", "stop", "ssh"], "not-yet-allowed"),
    (["docker", "rm", "x"], "not-yet-allowed"),
    (["ip", "addr"], "not on the read-only allowlist"),
    (["bash", "-c", "ls"], "not on the read-only allowlist"),
    (["ls", "/;", "rm"], "shell character"),
    (["cat", "a b"], "shell character"),
    (["cat", "$(id)"], "shell character"),
    (["find", "/tmp", "-delete"], "writes or sends"),
    (["find", "/", "-exec", "rm", "{}"], "shell character"),
    (["find", "/", "-execdir", "id"], "writes or sends"),
    (["curl", "-o", "/tmp/x", "http://h"], "writes or sends"),
    (["curl", "--output=/tmp/x", "http://h"], "writes or sends"),
    (["curl", "-X", "POST", "http://h"], "writes or sends"),
    (["journalctl", "--vacuum-size=1M"], "writes or sends"),
    (["journalctl", "--rotate"], "writes or sends"),
    (["ping", "host"], "does not stop"),
    (["top"], "does not stop"),
    (["top", "-b"], "does not stop"),
    ([], "non-empty"),
])
def test_the_guard_refuses_what_the_first_stage_must_not_do(argv: list[str],
                                                            reason: str) -> None:
    with pytest.raises(layer5.Refused, match=reason):
        layer5.guard(argv)


@pytest.mark.parametrize("argv, entry", [
    (["ping", "-c", "1", "localhost"], "ping"),
    (["top", "-b", "-n", "1"], "top"),
    (["systemctl", "status", "ssh"], "systemctl status"),
    (["curl", "-s", "http://localhost"], "curl"),
    (["find", "/etc", "-maxdepth", "1", "-name", "hosts"], "find"),
])
def test_the_guard_lets_bounded_reads_through(argv: list[str], entry: str) -> None:
    assert layer5.guard(argv) == entry


def test_nothing_runs_without_limactl(monkeypatch: pytest.MonkeyPatch) -> None:
    """On this machine limactl is not installed, and observe() refuses before
    it calls anything at all."""
    def must_not(*_: Any, **__: Any) -> None:
        raise AssertionError("a command was run")

    monkeypatch.setattr(layer5.shutil, "which", lambda _: None)
    with pytest.raises(layer5.Refused, match="not installed"):
        layer5.observe("processes", "cosmictera", run=must_not)


def test_the_one_way_out_is_limactl_in_the_vm(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    class Done:
        returncode, stdout, stderr = 0, "PRETTY_NAME=x\n", ""

    def fake(cmd: list[str], **kwargs: Any) -> Done:
        calls.append((cmd, kwargs))
        return Done()

    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/usr/local/bin/limactl")
    record = layer5.observe("host_identity", "cosmictera", run=fake)
    (cmd, kwargs), = calls
    assert cmd == ["limactl", "shell", "cosmictera", "--", "cat", "/etc/os-release"]
    assert "shell" not in kwargs, "never through a shell on this Mac"
    assert record["allowed_by"] == "cat" and record["exit_code"] == 0
    assert set(record) == {"collector", "argv", "allowed_by", "transport", "started_utc",
                           "seconds", "exit_code", "stdout", "stderr", "stdout_sha256"}
    with pytest.raises(layer5.Refused, match="instance name"):
        layer5.observe("host_identity", "a;b", run=fake)


def test_the_module_never_asks_for_a_shell() -> None:
    text = (ROOT / "src" / "hijaiyyah" / "nui" / "layer5.py").read_text(encoding="utf-8")
    assert "shell=True" not in text and "os.system" not in text


def test_the_vm_pins_the_recorded_image_and_mounts_nothing() -> None:
    """The digest is the SHA256 recorded in NUI/LAYERS.md; there is one image,
    a local file, no URL to fall back to, no mount of the Mac, plain mode."""
    yaml = layer5.LIMA.read_text(encoding="utf-8")
    body = "\n".join(line for line in yaml.splitlines() if not line.startswith("#"))
    assert layer5.lima_digest() == layer5.image_baseline()["sha256"]
    assert body.count("- location:") == 1
    assert "http" not in body
    assert re.search(r"^mounts: \[\]$", body, re.M)
    assert re.search(r"^plain: true$", body, re.M)
    assert re.search(r"^upgradePackages: false$", body, re.M)


def test_every_collector_says_whose_it_is() -> None:
    spec = layer5.load()
    for item in spec["collectors"] + spec["guard"]:
        assert item["status"] in {"ditetapkan", "usulan"}, item
        assert item["source"], item
