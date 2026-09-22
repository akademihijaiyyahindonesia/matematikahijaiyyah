"""Layer 5's skeleton, held before any host exists.

Nothing here runs a command. What is held: every collector the plan lists
passes the read-only guard, and the guard refuses what the first stage must
not do -- a forbidden command, a command off the allowlist, an argument a
shell could read, an option that writes or sends, a command that never stops.
`journalctl` and `ip` pass only in the owner's exact forms (K-4). The only
way out is `limactl shell` in the VM named cosmictera-layer5, with Lima's
state in the owner's own LIMA_HOME (K-3); on a machine without limactl it
refuses before calling anything. The VM configuration pins the image digest
recorded in NUI/LAYERS.md, mounts nothing, and names no URL.
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
    assert len(plan) == 11
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
    (["ip", "addr"], "not one of the owner's forms"),
    (["ip"], "not one of the owner's forms"),
    (["ip", "addr", "add", "10.0.0.1/24", "dev", "eth0"], "not one of the owner's forms"),
    (["ip", "addr", "del", "10.0.0.1/24", "dev", "eth0"], "not one of the owner's forms"),
    (["ip", "link", "set", "eth0", "down"], "not one of the owner's forms"),
    (["ip", "route", "add", "default", "via", "10.0.0.1"], "not one of the owner's forms"),
    (["ip", "route", "del", "default"], "not one of the owner's forms"),
    (["ip", "route", "replace", "default", "via", "10.0.0.1"], "not one of the owner's forms"),
    (["journalctl"], "not one of the owner's forms"),
    (["journalctl", "-b", "-n", "500", "--no-pager"], "not one of the owner's forms"),
    (["journalctl", "-b", "-u", "-f", "-n", "200", "--no-pager"], "not one of the owner's forms"),
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
    (["journalctl", "--vacuum-size=1M"], "not one of the owner's forms"),
    (["journalctl", "--rotate"], "not one of the owner's forms"),
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
    (["journalctl", "-b", "-n", "200", "--no-pager"], "journalctl"),
    (["journalctl", "-b", "-u", "ssh", "-n", "200", "--no-pager"], "journalctl"),
    (["ip", "-brief", "addr"], "ip"),
    (["ip", "link"], "ip"),
    (["ip", "route"], "ip"),
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
    record = layer5.observe("host_identity", run=fake)
    (cmd, kwargs), = calls
    assert cmd == ["limactl", "shell", "cosmictera-layer5", "--", "cat", "/etc/os-release"]
    assert "shell" not in kwargs, "never through a shell on this Mac"
    home = str(Path("~/cosmictera-layer5/lima-home").expanduser())
    assert kwargs["env"]["LIMA_HOME"] == home, "the owner's own Lima namespace (K-3)"
    assert record["transport"] == {"kind": "lima", "instance": "cosmictera-layer5",
                                   "lima_home": home}
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


def test_the_host_is_the_owners_k3() -> None:
    """Lima through Homebrew, its state in its own LIMA_HOME, the VM named
    cosmictera-layer5 -- the owner, 22 September 2026."""
    h = layer5.load()["host"]
    assert (h["lima"], h["lima_home"], h["instance"]) == (
        "dipasang lewat Homebrew", "~/cosmictera-layer5/lima-home", "cosmictera-layer5")
    assert layer5.host()["instance"] == "cosmictera-layer5"


def test_every_catalog_form_passes_the_guard() -> None:
    """What usr.to_argv returns for the host must be something the guard lets
    run -- including the per-unit journal form."""
    for e in usr.load("layer5_catalog")["entries"]:
        for key in ("argv", "argv_target"):
            if key not in e:
                continue
            argv = [("ssh" if part == "{target}" else part) for part in e[key]]
            try:
                layer5.guard(argv)
            except layer5.Refused as why:
                raise AssertionError(f"{e['action']} {e['object']} {key}: {why}") from None


def test_the_owners_forms_are_exact() -> None:
    """K-4: two journalctl forms, three ip forms, nothing else."""
    forms = layer5.forms()
    assert forms["journalctl"] == [["journalctl", "-b", "-n", "200", "--no-pager"],
                                   ["journalctl", "-b", "-u", "<service>", "-n", "200",
                                    "--no-pager"]]
    assert forms["ip"] == [["ip", "-brief", "addr"], ["ip", "link"], ["ip", "route"]]
