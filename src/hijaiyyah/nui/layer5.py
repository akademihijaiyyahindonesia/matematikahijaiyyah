"""Layer 5: observing an Ubuntu host, read only.

    python3 -m hijaiyyah.nui.layer5                       # the plan: every collector, guarded
    python3 -m hijaiyyah.nui.layer5 --record <instance> [<collector> ...]
                                                          # into the store, under the VM's namespace

The owner's decisions: the host is a VM, Ubuntu Server 24.04 LTS ARM64, isolated
from this Mac (21 September 2026); its first stage only reads; its image is
part of the baseline, SHA256 verified and recorded (22 September 2026); and on
22 September the owner asked for this skeleton while the board holds the
burn-in -- observation first, no write, no control. The owner opened it on
26 September 2026 (P8), on the test instance cosmictera-layer5-uji.

Three parts, each read from where it is written:

    NUI/spec/layer5_collectors.json   what to observe -- argv of its own, or a
                                      row of the layer 5 catalog (usr.py)
    NUI/spec/layer5_lima.yaml         the VM: the verified image by digest, no
                                      mounts, plain mode
    NUI/LAYERS.md                     the owner's read-only allowlist, and the
                                      image's recorded SHA256

-- the guard ---------------------------------------------------------------------
guard() refuses before anything could run: a command off the owner's
allowlist or on its not-yet list; an argument with a space or a shell
character -- `limactl shell` hands the command to the guest's shell over SSH,
and how it quotes has not been measured, so nothing is left to quoting; for
`journalctl` and `ip`, anything but the owner's exact forms (K-4, 22 September
2026: journalctl bounded to 200 lines of this boot, ip observing only); an
option of another allowed command that writes or sends (find -delete, curl
-o); and a command that would not stop by itself (ping without -c, top
without -b and -n).

-- the one way out ----------------------------------------------------------------
observe() runs one collector as `limactl shell <instance> -- <argv>` and
nothing else: never a shell, never on this Mac. Lima's state lives in the
owner's own LIMA_HOME and the instance has the owner's name (K-3). It refuses
when limactl is not installed, as it was until Homebrew installed it on
26 September 2026. An observation keeps argv, exit code, stdout, stderr and a
hash of stdout; nothing is parsed -- what the parsing must be is not decided.

-- where it is kept ----------------------------------------------------------------
K-11, 23 September 2026: the observations store on the host, outside this
repository, which holds code, specifications, tests and sealed facts -- not
runtime observations. K-16, 27 September 2026: an observation's canonical
identity is (vm_name, run_id), and a run is written under its VM's own
namespace, ~/cosmictera-layer5/observations/<vm_name>/<run_id>/. The runs
written before that sit at observations/<run_id>/ and are not moved: they are
frozen evidence, and the vm_name in their manifests tells them apart.
observe() returns a record and
writes nothing; record() runs every collector through it once and writes the
run: each collector's stdout and stderr under raw/, and a manifest.json that
links each to its collector, run, time, VM, command, exit code, duration,
path and SHA-256 (the owner's fields for P8.4, 26 September 2026). A store
inside this repository is refused. The evidence is the command's output as
UTF-8 text, not raw bytes (K-15): a host command's output already is the
observation, unlike the UART wire, whose parsing is a question of bytes.

-- reading it back ------------------------------------------------------------------
latest() hands NUI's HOST domain the newest observation of one collector on
one VM -- never another VM's -- and only after checking it: the run's
manifest and its entry name that VM and that run, and
every evidence file has the size and SHA-256 the manifest recorded. Anything
else is returned as rejected, with why. outcome() classes a run by the
owner's rules in the spec (K-12, K-13) -- PASS, unavailable for permissions,
unavailable because the command is absent, otherwise a collector error.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import usr
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "layer5_collectors.json"
LIMA = ROOT / "NUI" / "spec" / "layer5_lima.yaml"
IMAGE = "ubuntu-24.04-server-cloudimg-arm64.img"
SAFE_ARG = re.compile(r"[A-Za-z0-9._/:@%+=,-]+")
#: Options that write or send, refused even when the command is allowed.
WRITES = {
    "find": ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0",
             "-fprintf", "-fls"),
    "curl": ("-o", "--output", "-O", "--remote-name", "--remote-name-all", "-T",
             "--upload-file", "-d", "--data", "-F", "--form", "-X", "--request", "-K",
             "--config"),
}
#: Commands that run until stopped, and the options that stop them.
BOUNDED = {"ping": ("-c",), "top": ("-b", "-n")}


class Refused(Exception):
    """A command the read-only stage does not run, and why."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


def argv_of(collector: dict[str, Any]) -> list[str]:
    """A collector's argv: its own, or its catalog row's (R1)."""
    if "argv" in collector:
        return list(collector["argv"])
    action, obj = collector["catalog"].split()
    entry = next(e for e in usr.load("layer5_catalog")["entries"]
                 if (e["action"], e["object"]) == (action, obj))
    if "{target}" in entry["argv"]:
        raise Refused(f"{collector['catalog']} needs a target; a collector takes none")
    return list(entry["argv"])


def forms() -> dict[str, list[list[str]]]:
    """The owner's exact forms for journalctl and ip (K-4), from the spec."""
    rule = next(g for g in load()["guard"] if "forms" in g)
    data: dict[str, list[list[str]]] = rule["forms"]
    return data


def _matches(argv: list[str], form: list[str]) -> bool:
    return len(argv) == len(form) and all(
        a == f or (f.startswith("<") and f.endswith(">") and SAFE_ARG.fullmatch(a) is not None
                   and not a.startswith("-"))
        for a, f in zip(argv, form, strict=True))


def guard(argv: list[str]) -> str:
    """The allowlist entry that permits argv, or Refused with the reason."""
    if not argv or not all(isinstance(a, str) and a for a in argv):
        raise Refused("argv must be a non-empty list of non-empty strings")
    allowed, forbidden = usr.allowlist()
    if usr._command(argv, forbidden):
        raise Refused(f"`{usr._command(argv, forbidden)}` is on the not-yet-allowed list")
    entry = usr._command(argv, allowed)
    if entry is None:
        raise Refused(f"`{argv[0]}` is not on the read-only allowlist")
    for arg in argv:
        if not SAFE_ARG.fullmatch(arg):
            raise Refused(f"argument {arg!r} holds a space or a shell character")
    allowed_forms = forms().get(argv[0])
    if allowed_forms is not None and not any(_matches(argv, f) for f in allowed_forms):
        raise Refused(f"`{' '.join(argv)}` is not one of the owner's forms for {argv[0]}")
    for option in WRITES.get(argv[0], ()):
        if any(a == option or a.startswith(option + "=") for a in argv[1:]):
            raise Refused(f"`{argv[0]} {option}` writes or sends")
    for option in BOUNDED.get(argv[0], ()):
        if option not in argv[1:]:
            raise Refused(f"`{argv[0]}` without {option} does not stop by itself")
    return entry


def plan() -> list[dict[str, Any]]:
    """Every collector, its argv, and the guard's verdict -- nothing runs."""
    out = []
    for c in load()["collectors"]:
        row: dict[str, Any] = {"name": c["name"], "area": c["area"], "status": c["status"]}
        try:
            row["argv"] = argv_of(c)
            row["allowed_by"] = guard(row["argv"])
        except Refused as why:
            row["refused"] = str(why)
        out.append(row)
    return out


def image_baseline() -> dict[str, str]:
    """The image's recorded SHA256, read from NUI/LAYERS.md's table (R1)."""
    text = (ROOT / "NUI" / "LAYERS.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(f"| `{IMAGE}`"))
    digest = re.findall(r"`([0-9a-f]{64})`", row)[0]
    return {"file": IMAGE, "sha256": digest}


def lima_digest() -> str:
    """The digest the VM configuration pins, read from the YAML's text: PyYAML
    is not installed, and adding it needs the owner's leave."""
    m = re.search(r'digest:\s*"sha256:([0-9a-f]{64})"', LIMA.read_text(encoding="utf-8"))
    if m is None:
        raise LookupError(f"{LIMA} pins no digest")
    return m.group(1)


Runner = Callable[..., Any]


def host() -> dict[str, str]:
    """Where Lima keeps its state and what the VM is called (K-3)."""
    h = load()["host"]
    return {"lima_home": os.path.expanduser(h["lima_home"]), "instance": h["instance"]}


def observe(name: str, instance: str | None = None,
            run: Runner = subprocess.run) -> dict[str, Any]:
    """One collector, run in the VM through limactl, and what came back."""
    where = host()
    instance = instance or where["instance"]
    collector = next((c for c in load()["collectors"] if c["name"] == name), None)
    if collector is None:
        raise Refused(f"no collector named {name}")
    argv = argv_of(collector)
    allowed_by = guard(argv)
    if not SAFE_ARG.fullmatch(instance):
        raise Refused(f"instance name {instance!r} holds a space or a shell character")
    if shutil.which("limactl") is None:
        raise Refused("limactl is not installed: layer 5 has not started")
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    proc = run(["limactl", "shell", instance, "--", *argv],
               capture_output=True, text=True, timeout=120,
               env={**os.environ, "LIMA_HOME": where["lima_home"]})
    return {"collector": name, "argv": argv, "allowed_by": allowed_by,
            "transport": {"kind": "lima", "instance": instance,
                          "lima_home": where["lima_home"]},
            "started_utc": started.isoformat(), "seconds": round(time.monotonic() - t0, 3),
            "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
            "stdout_sha256": hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest()}


def store() -> Path:
    """The K-11 evidence store on the host, read from the spec (R1)."""
    return Path(os.path.expanduser(load()["observations"]["dir"]))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


VM_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def record(instance: str, run: Runner = subprocess.run, into: Path | None = None,
           only: list[str] | None = None) -> Path:
    """Every collector once -- or the ones `only` names, in the spec's order --
    through observe() and its guard, written to one run directory under the
    VM's own namespace of the K-11 store, observations/<vm_name>/<run_id>/
    (K-16): each collector's stdout and stderr under raw/, and a manifest.json
    that links every one of them to its VM, run, collector, time, command,
    exit code, duration, path and SHA-256.

    A collector that fails is recorded with why, and the others still run. The
    store is refused inside this repository: it holds code, specs, tests and
    sealed facts, not runtime observations (K-11)."""
    if not VM_NAME.fullmatch(instance):
        raise Refused(f"instance name {instance!r} cannot name a directory of its own")
    names = [c["name"] for c in load()["collectors"]]
    if only is not None and (not only or set(only) - set(names)):
        raise Refused(f"no collector named {sorted(set(only) - set(names))}")
    base = (into or store()).resolve()
    if base == ROOT or ROOT in base.parents:
        raise Refused(f"{base} is inside the repository; observations live outside it (K-11)")
    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + "-collectors"
    out = base / instance / run_id
    (out / "raw").mkdir(parents=True, exist_ok=False)
    entries: list[dict[str, Any]] = []
    for name in names:
        if only is not None and name not in only:
            continue
        entry: dict[str, Any] = {"collector": name, "run_id": run_id, "vm_name": instance}
        try:
            got = observe(name, instance, run=run)
        except (Refused, subprocess.TimeoutExpired, UnicodeDecodeError, OSError) as why:
            entry.update({"timestamp": datetime.now(timezone.utc).isoformat(),
                          "failure": f"{type(why).__name__}: {why}"})
            entries.append(entry)
            continue
        evidence = {}
        for stream in ("stdout", "stderr"):
            data = got[stream].encode("utf-8")
            path = f"raw/{name}.{stream}"
            (out / path).write_bytes(data)
            evidence[stream] = {"path": path, "bytes": len(data), "sha256": _sha(data)}
        entry.update({"timestamp": got["started_utc"], "vm_name": got["transport"]["instance"],
                      "command_identity": got["argv"], "allowed_by": got["allowed_by"],
                      "exit_code": got["exit_code"], "duration": got["seconds"],
                      "evidence": evidence})
        entries.append(entry)
    manifest = {
        "run_id": run_id, "vm_name": instance, "started_utc": started.isoformat(),
        "identity": "(vm_name, run_id), K-16", "lima_home": host()["lima_home"],
        "transport": "limactl shell <instance> -- <argv>, guarded by layer5.guard()",
        "produced_by": {
            "module": "src/hijaiyyah/nui/layer5.py",
            "module_sha256": _sha((ROOT / "src" / "hijaiyyah" / "nui" / "layer5.py").read_bytes()),
            "spec": "NUI/spec/layer5_collectors.json", "spec_sha256": _sha(SPEC.read_bytes())},
        "collectors": entries,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    return out


RUN = re.compile(r"\d{8}T\d{6}Z-collectors")


def outcome(exit_code: int | None, stderr: str) -> str:
    """One run of a collector, classed by its own exit code and stderr, by the
    owner's rules in the spec (K-12, K-13): the first class that matches."""
    rules = load()["outcomes"]
    for rule in rules["classes"]:
        if "exit_code" in rule and rule["exit_code"] != exit_code:
            continue
        if "stderr_contains" in rule and rule["stderr_contains"] not in stderr:
            continue
        return str(rule["status"])
    return str(rules["otherwise"])


def resolve(source: str) -> Path:
    """Where an observation source, `observations/...`, lies on the host."""
    return store().parent / source


def _runs(vm_name: str) -> list[tuple[Path, bool]]:
    """Collector runs that may belong to one VM, newest first: those in its
    own namespace, observations/<vm_name>/<run_id>/ (K-16), and the runs
    written before K-16 at observations/<run_id>/, frozen where they are and
    told apart by the vm_name in their manifests. True marks the namespace."""
    base = store()
    found = []
    for where, own in ((base / vm_name, True), (base, False)):
        if where.is_dir():
            found += [(p, own) for p in where.iterdir() if p.is_dir() and RUN.fullmatch(p.name)]
    return sorted(found, key=lambda r: r[0].name, reverse=True)


def _verified(run_dir: Path, own: bool, collector: str, vm_name: str) -> dict[str, Any] | None:
    """One collector's observation in one run of one VM, checked: the run's
    manifest names this VM and this run, the entry names this VM, run and
    collector, and every evidence file has the size and SHA-256 the manifest
    recorded. A run that fails any of that comes back rejected, with why.
    None when the run is not this VM's or does not hold the collector."""
    prefix = "/".join([store().name, *([vm_name] if own else []), run_dir.name])
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as why:
        if not own:
            return None
        return {"collector": collector, "run_id": run_dir.name, "vm_name": vm_name,
                "rejected": f"manifest unreadable: {why}"}
    if not own and manifest.get("vm_name") != vm_name:
        return None
    entry = next((e for e in manifest.get("collectors", [])
                  if e.get("collector") == collector), None)
    if entry is None:
        return None
    found: dict[str, Any] = {"collector": collector, "run_id": run_dir.name,
                             "manifest": f"{prefix}/manifest.json"}
    if manifest.get("vm_name") != vm_name or entry.get("vm_name") != vm_name:
        return {**found, "vm_name": vm_name,
                "rejected": f"the manifest names another VM than {vm_name}"}
    if manifest.get("run_id") != run_dir.name or entry.get("run_id") != run_dir.name:
        return {**found, "rejected": "the manifest does not name this run"}
    found.update({"vm_name": entry.get("vm_name"), "observed_at": entry.get("timestamp"),
                  "command_identity": entry.get("command_identity"),
                  "exit_code": entry.get("exit_code")})
    if "failure" in entry:
        return {**found, "status": "collector_error", "failure": entry["failure"]}
    texts = {}
    for stream in ("stdout", "stderr"):
        ev = entry.get("evidence", {}).get(stream)
        if not ev:
            return {**found, "rejected": f"no {stream} evidence recorded"}
        try:
            data = (run_dir / ev["path"]).read_bytes()
        except OSError:
            return {**found, "rejected": f"{ev['path']} is missing"}
        if len(data) != ev["bytes"] or _sha(data) != ev["sha256"]:
            return {**found, "rejected": f"{ev['path']} does not match its recorded SHA-256"}
        texts[stream] = data.decode("utf-8")
        found[stream] = {"source": f"{prefix}/{ev['path']}", "sha256": ev["sha256"]}
    found["status"] = outcome(entry["exit_code"], texts["stderr"])
    found["stdout_text"], found["stderr_text"] = texts["stdout"], texts["stderr"]
    return found


def observations(collector: str, vm_name: str) -> list[dict[str, Any]]:
    """Every run of one VM that holds the collector, newest first, each one
    checked by _verified() -- rejected ones included, so a caller never skips
    past a run that failed its checks without seeing it."""
    out = []
    for run_dir, own in _runs(vm_name):
        seen = _verified(run_dir, own, collector, vm_name)
        if seen is not None:
            out.append(seen)
    return out


def latest(collector: str, vm_name: str) -> dict[str, Any] | None:
    """The newest observation of one collector on one VM, verified before it
    is handed out. The canonical identity of an observation is (vm_name,
    run_id) (K-16): another VM's run never answers for this one. A run that
    fails its checks is returned as rejected, with why, and never as an
    observation. None when no run of this VM has the collector."""
    seen = observations(collector, vm_name)
    return seen[0] if seen else None


def freshness(observed_at: str, now: datetime | None = None) -> dict[str, Any]:
    """How old one observation is and whether it is current, by the explicit
    rule in the spec: current only when its age is within stale_after_seconds.
    With no value set, or a clock that went back, nothing is claimed current."""
    rule = load()["freshness"]
    limit = rule["stale_after_seconds"]
    age = round(((now or datetime.now(timezone.utc))
                 - datetime.fromisoformat(observed_at)).total_seconds(), 3)
    judged: dict[str, Any] = {"age_seconds": age, "stale_after_seconds": limit}
    if limit is None:
        return {**judged, "freshness": "stale",
                "freshness_why": "no stale_after_seconds is set in "
                                 "NUI/spec/layer5_collectors.json, so no observation is "
                                 "claimed current"}
    if age < 0:
        return {**judged, "freshness": "stale",
                "freshness_why": "observed after now: the host clock went back"}
    return {**judged, "freshness": "current" if age <= limit else "stale"}


def items(collector: str, text: str) -> dict[str, str]:
    """The items of one collector's output, keyed by the spec's rule for it:
    what the delta between two runs is taken over. Nothing else is parsed."""
    rule = load()["delta"]["items"][collector]
    kind = rule["kind"]
    lines = [ln for ln in text.splitlines()[rule.get("skip", 0):] if ln.strip()]
    out: dict[str, str] = {}
    if kind == "findall":
        for name in re.findall(rule["pattern"], text):
            out[name] = str(int(out.get(name, "0")) + 1)
        return out
    for line in lines:
        if kind == "kv":
            key, sep, value = line.partition(rule["sep"])
            if sep:
                out[key.strip()] = value.strip()
        elif kind == "line":
            out[line.strip()] = ""
        elif kind == "match":
            m = re.match(rule["pattern"], line)
            if m:
                out[m.group("key")] = line.strip()
        elif kind == "fields":
            fields = line.split()
            parts = [fields[i] for i in rule["key"] if i < len(fields)]
            if "rest_from" in rule:
                parts.append(" ".join(fields[rule["rest_from"]:]))
            key = " ".join(p for p in parts if p)
            if rule.get("count"):
                out[key] = str(int(out.get(key, "0")) + 1)
            else:
                out[key] = line.strip()
        else:
            raise ValueError(f"no item rule of kind {kind!r}")
    return out


def _provenance(seen: dict[str, Any]) -> dict[str, Any]:
    """Where one side of a delta comes from: the items are read from stdout,
    and stderr is kept beside it as the provenance of a status that is not
    PASS."""
    return {"vm_name": seen["vm_name"], "run_id": seen["run_id"],
            "observed_at": seen["observed_at"], "status": seen["status"],
            "evidence": seen["stdout"]["source"], "evidence_sha256": seen["stdout"]["sha256"],
            "stderr": seen["stderr"]["source"], "stderr_sha256": seen["stderr"]["sha256"]}


def delta(collector: str, vm_name: str, run_from: str | None = None,
          run_to: str | None = None) -> dict[str, Any]:
    """What changed in one collector's output between two runs of the same VM
    -- by default its two newest -- with the provenance of both. Items that
    appeared, disappeared, or kept their key and changed their value, by the
    spec's item rule. Only an observation: nothing acts on it. Two runs that
    are not both verified give no delta, and say why."""
    seen = observations(collector, vm_name)
    by_id = {s["run_id"]: s for s in seen}
    pair: list[dict[str, Any] | None]
    if run_to is None and run_from is None:
        pair = list(seen[1::-1]) if len(seen) >= 2 else []
    else:
        pair = [by_id.get(run_from or ""), by_id.get(run_to or "")]
    if len(pair) != 2 or None in pair:
        return {"collector": collector, "vm_name": vm_name,
                "unknown": f"no two runs of {collector} for {vm_name} to compare"}
    old, new = pair[0], pair[1]
    for s in (old, new):
        if s is not None and ("rejected" in s or "failure" in s):
            return {"collector": collector, "vm_name": vm_name,
                    "unknown": f"{collector} in {s['run_id']} cannot be compared -- "
                               f"{s.get('rejected') or s.get('failure')}"}
    assert old is not None and new is not None
    a, b = items(collector, old["stdout_text"]), items(collector, new["stdout_text"])
    return {"collector": collector, "vm_name": vm_name,
            "from": _provenance(old), "to": _provenance(new),
            "appeared": sorted(set(b) - set(a)), "disappeared": sorted(set(a) - set(b)),
            "changed": [{"item": k, "from": a[k], "to": b[k]}
                        for k in sorted(set(a) & set(b)) if a[k] != b[k]]}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--record"] and len(args) >= 2:
        out = record(args[1], only=args[2:] or None)
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        print(out)
        for e in manifest["collectors"]:
            what = e.get("failure") or (f"exit {e['exit_code']}  {e['duration']}s  "
                                        f"stdout {e['evidence']['stdout']['bytes']} B")
            print(f"  {e['collector']:<20} {what}")
        return 0
    base = image_baseline()
    print(f"image {base['file']} sha256 {base['sha256'][:16]}... "
          f"(VM config pins {'the same' if lima_digest() == base['sha256'] else 'ANOTHER'})")
    for row in plan():
        verdict = f"allowed by `{row['allowed_by']}`" if "allowed_by" in row else row["refused"]
        print(f"  {row['name']:<20} {row['status']:<10} "
              f"{' '.join(row.get('argv', [])):<32} {verdict}")
    print("limactl:", shutil.which("limactl") or "not installed -- nothing can run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
