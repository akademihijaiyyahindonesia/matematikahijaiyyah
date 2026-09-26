"""Layer 5's read-only observation, held without a host.

Nothing here runs a command in a VM: the runner is faked throughout. What is
held: every collector the plan lists passes the read-only guard, and the guard
refuses what the first stage must not do -- a forbidden command, a command off
the allowlist, an argument a shell could read, an option that writes or sends,
a command that never stops.
`journalctl` and `ip` pass only in the owner's exact forms (K-4). The only
way out is `limactl shell` in the VM named cosmictera-layer5, with Lima's
state in the owner's own LIMA_HOME (K-3); on a machine without limactl it
refuses before calling anything. The VM configuration pins the image digest
recorded in NUI/LAYERS.md, mounts nothing, and names no URL. record() writes
one run of every collector to the K-11 store with the owner's P8.4 fields --
collector, run_id, timestamp, VM name, command identity, exit code, duration,
evidence path and SHA-256 -- and refuses a store inside the repository.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
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


def test_the_host_is_the_owners_k3_and_k9() -> None:
    """Lima through Homebrew, its state in its own LIMA_HOME, the VM named
    cosmictera-layer5 (K-3); the disposable instance that proves the path
    first named cosmictera-layer5-uji (K-9) -- the owner, 22 September 2026.
    The guard takes the test instance's name like any other."""
    h = layer5.load()["host"]
    assert (h["lima"], h["lima_home"], h["instance"], h["test_instance"]) == (
        "dipasang lewat Homebrew", "~/cosmictera-layer5/lima-home", "cosmictera-layer5",
        "cosmictera-layer5-uji")
    assert "K-9" in h["test_instance_source"]
    assert layer5.host()["instance"] == "cosmictera-layer5"
    assert layer5.SAFE_ARG.fullmatch(h["test_instance"])


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


def test_where_an_observation_is_kept_is_the_owners_k11() -> None:
    """K-11: one directory per session under ~/cosmictera-layer5/observations/,
    on the host and outside the repository -- the repo holds code, specs, tests
    and sealed facts, not live observations. Every manifest field the owner
    named comes from a field `observe()` already returns, except run_id, which
    is the session itself."""
    spec = layer5.load()["observations"]
    assert spec["per_run"] == "~/cosmictera-layer5/observations/<run_id>/"
    where = Path(spec["dir"]).expanduser().resolve()
    assert not where.is_relative_to(ROOT), "an observation would land in the repository"
    assert [f["field"] for f in spec["manifest"]] == [
        "run_id", "timestamp", "collector", "vm_name", "command_identity", "exit_code",
        "duration"]
    record = {"collector", "argv", "allowed_by", "transport", "started_utc", "seconds",
              "exit_code", "stdout", "stderr", "stdout_sha256"}
    new = [f["field"] for f in spec["manifest"] if f["from"] == "baru"]
    assert new == ["run_id"], new
    for field in spec["manifest"]:
        if field["from"] != "baru":
            assert field["from"].split(".")[0] in record, field


def test_the_owners_forms_are_exact() -> None:
    """K-4: two journalctl forms, three ip forms, nothing else."""
    forms = layer5.forms()
    assert forms["journalctl"] == [["journalctl", "-b", "-n", "200", "--no-pager"],
                                   ["journalctl", "-b", "-u", "<service>", "-n", "200",
                                    "--no-pager"]]
    assert forms["ip"] == [["ip", "-brief", "addr"], ["ip", "link"], ["ip", "route"]]


# -- the K-11 store, written by record() (P8.4, 26 September 2026) ----------------------

OWNER_FIELDS = ("collector", "run_id", "timestamp", "vm_name", "command_identity",
                "exit_code", "duration")


class _Done:
    def __init__(self, cmd: list[str]) -> None:
        self.returncode = 127 if cmd[4:6] == ["docker", "ps"] else 0
        self.stdout = "out of " + " ".join(cmd[4:]) + "\n"
        self.stderr = "docker: not found\n" if self.returncode else ""


def _recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
              run: Any) -> tuple[Path, dict[str, Any]]:
    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    out = layer5.record("cosmictera-layer5-uji", run=run, into=tmp_path)
    return out, json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def test_record_writes_every_collector_with_the_owners_fields(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One run directory; every collector in the spec's order, each carrying
    the owner's nine things -- the seven K-11 fields, the evidence path and its
    SHA-256 -- and every hash is the hash of the file it names."""
    calls: list[list[str]] = []

    def fake(cmd: list[str], **_: Any) -> _Done:
        calls.append(cmd)
        return _Done(cmd)

    out, manifest = _recorded(tmp_path, monkeypatch, fake)
    assert re.fullmatch(r"\d{8}T\d{6}Z-collectors", out.name)
    assert manifest["run_id"] == out.name and manifest["vm_name"] == "cosmictera-layer5-uji"
    names = [c["name"] for c in layer5.load()["collectors"]]
    assert [e["collector"] for e in manifest["collectors"]] == names
    written = {"manifest.json"} | {f"raw/{n}.{s}" for n in names for s in ("stdout", "stderr")}
    assert {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()} == written
    for e, plan in zip(manifest["collectors"], layer5.plan(), strict=True):
        assert all(e.get(f) is not None for f in OWNER_FIELDS), e
        assert e["run_id"] == out.name and e["command_identity"] == plan["argv"]
        for stream in ("stdout", "stderr"):
            ev = e["evidence"][stream]
            data = (out / ev["path"]).read_bytes()
            assert ev["sha256"] == hashlib.sha256(data).hexdigest() and ev["bytes"] == len(data)
    assert calls == [["limactl", "shell", "cosmictera-layer5-uji", "--", *p["argv"]]
                     for p in layer5.plan()]
    containers = manifest["collectors"][-1]
    assert (containers["collector"], containers["exit_code"]) == ("containers", 127)
    produced = manifest["produced_by"]
    assert produced["spec_sha256"] == hashlib.sha256(layer5.SPEC.read_bytes()).hexdigest()


def test_a_failing_collector_is_recorded_and_the_rest_still_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(cmd: list[str], **_: Any) -> _Done:
        if cmd[4] == "journalctl":
            raise subprocess.TimeoutExpired(cmd, 120)
        return _Done(cmd)

    _, manifest = _recorded(tmp_path, monkeypatch, fake)
    by_name = {e["collector"]: e for e in manifest["collectors"]}
    assert "TimeoutExpired" in by_name["journal"]["failure"]
    assert "evidence" not in by_name["journal"]
    assert all("evidence" in e for n, e in by_name.items() if n != "journal")


def test_a_command_off_the_allowlist_never_reaches_the_vm(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The store is written through observe(), so through the guard: a
    collector the guard refuses is recorded as refused, and the runner never
    sees it."""
    spec = layer5.load()
    spec["collectors"].append({"name": "wipe", "area": "filesystem", "argv": ["rm", "-rf", "/"],
                               "status": "usulan", "source": "sabotage"})
    monkeypatch.setattr(layer5, "load", lambda: spec)
    seen: list[list[str]] = []

    def fake(cmd: list[str], **_: Any) -> _Done:
        seen.append(cmd)
        return _Done(cmd)

    _, manifest = _recorded(tmp_path, monkeypatch, fake)
    wipe = manifest["collectors"][-1]
    assert wipe["collector"] == "wipe" and wipe["failure"].startswith("Refused")
    assert not [c for c in seen if "rm" in c]


def test_the_store_is_refused_inside_the_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not(*_: Any, **__: Any) -> None:
        raise AssertionError("a command was run")

    monkeypatch.setattr(layer5.shutil, "which", lambda _: "/opt/homebrew/bin/limactl")
    inside = ROOT / "observations-sabotage"
    assert not inside.exists(), f"{inside} is left over from an earlier run"
    try:
        with pytest.raises(layer5.Refused, match="inside the repository"):
            layer5.record("cosmictera-layer5-uji", run=must_not, into=inside)
        assert not inside.exists()
    finally:
        shutil.rmtree(inside, ignore_errors=True)
    assert layer5.store() == Path("~/cosmictera-layer5/observations").expanduser()
