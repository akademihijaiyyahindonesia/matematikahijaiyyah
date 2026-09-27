"""Layer 5 frozen: the main instance's host baseline, its freshness rule, and what changed after it.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer5_freeze --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer5_freeze --verify

The owner's operational close of Layer 5, 27 September 2026: freeze the main
instance's run as the reference snapshot, give HOST a notion of how fresh an
observation is, give NUI the delta between two runs, and then freeze -- the
same shape as Layer 4's hardware parity freeze, as a host intelligence
baseline freeze.

What differs from Layer 4 is where the evidence lives. Layer 4's records are
committed; Layer 5's are not, by the owner's K-11: runtime HOST evidence stays
in the observation store on the host, outside this repository. So what this
module writes into the repository is pointers and hashes only -- which VM,
which run, which collector, when, which status, and the SHA-256 of every
evidence file and of every delta -- never the observed text. Anyone with the
store reproduces it exactly; nobody without it can read the host from here.

    baseline      each of the eleven collectors on cosmictera-layer5, at the run
                  the owner froze as the reference
    compared_with the first run after the baseline, and the delta from the
                  baseline to it, per collector: counts, and the SHA-256 of the
                  items themselves
    history       the manifests of every P8 run, the test instance's included,
                  by hash -- the evidence the baseline stands on

Nothing is inferred and nothing acts: the freeze reads what layer5 already
verifies, and the freshness rule it records is the spec's, value and all.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from . import layer5
from .repository_index import ROOT

MODEL = ROOT / "NUI" / "layer5_freeze.json"
PAGE = ROOT / "NUI" / "LAYER5.md"
TAG = "layer5-freeze-2026-09-27"
VM = "cosmictera-layer5"
FIRST, TEN = "20260927T050203Z-collectors", "20260927T083814Z-collectors"
#: The owner's reference snapshot: host_identity from the main instance's
#: first run, the other ten from the run that followed it.
BASELINE: dict[str, str] = {"host_identity": FIRST, **{c: TEN for c in (
    "processes", "mounts", "root_listing", "systemd_overview", "journal", "interfaces",
    "links", "routes", "interface_counters", "containers")}}
#: The first run of all eleven after the baseline, taken to prove the delta.
COMPARED_WITH = "20260927T095339Z-collectors"
#: Every P8 run the baseline stands on, by the step that made it.
HISTORY: list[tuple[str, str]] = [
    ("P8.3 isolation, test instance", "20260926T013117Z-isolation"),
    ("P8.3 negative digest", "20260926T013234Z-digest-negative"),
    ("P8.4 eleven collectors, test instance", "20260926T053008Z-collectors"),
    ("P8.7 promotion, main instance", "20260926T091643Z-isolation"),
    ("P8.6 first main collector", f"{VM}/{FIRST}"),
    ("ten main collectors", f"{VM}/{TEN}"),
    ("first run after the baseline", f"{VM}/{COMPARED_WITH}"),
    ("test instance retired (K-17)", "cosmictera-layer5-uji/20260927T083913Z-retirement"),
]
#: What a freeze is held to for as long as it exists. The freshness rule is
#: recorded, not held: its value is the owner's to set after the freeze.
HELD = ("vm_name", "baseline", "compared_with", "delta", "history")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _at(collector: str, run_id: str) -> dict[str, Any]:
    seen = next((s for s in layer5.observations(collector, VM) if s["run_id"] == run_id), None)
    if seen is None:
        raise LookupError(f"{collector} has no run {run_id} for {VM}")
    if "rejected" in seen or "failure" in seen:
        raise LookupError(f"{collector} in {run_id}: {seen.get('rejected') or seen['failure']}")
    return seen


def _pointer(seen: dict[str, Any]) -> dict[str, Any]:
    return {"run_id": seen["run_id"], "observed_at": seen["observed_at"],
            "status": seen["status"], "exit_code": seen["exit_code"],
            "stdout": seen["stdout"]["source"], "stdout_sha256": seen["stdout"]["sha256"],
            "stderr": seen["stderr"]["source"], "stderr_sha256": seen["stderr"]["sha256"]}


def _delta(collector: str) -> dict[str, Any]:
    d = layer5.delta(collector, VM, run_from=BASELINE[collector], run_to=COMPARED_WITH)
    if "unknown" in d:
        raise LookupError(d["unknown"])
    apart = [k for k in d if k not in ("collector", "vm_name", "from", "to", "appeared",
                                        "disappeared", "changed")]
    body = {k: d[k] for k in ("appeared", "disappeared", "changed", *apart)}
    return {"from": d["from"]["run_id"], "to": d["to"]["run_id"],
            "status": [d["from"]["status"], d["to"]["status"]],
            "appeared": len(d["appeared"]), "disappeared": len(d["disappeared"]),
            "changed": len(d["changed"]),
            **{name: {part: len(d[name][part]) for part in ("appeared", "disappeared", "changed")}
               for name in apart},
            "items_sha256": _sha(json.dumps(body, sort_keys=True, ensure_ascii=False).encode())}


def build() -> dict[str, Any]:
    names = [c["name"] for c in layer5.load()["collectors"]]
    base = layer5.store()
    rule = layer5.load()["freshness"]
    return {
        "generated_by": "src/hijaiyyah/nui/layer5_freeze.py",
        "tag": TAG,
        "vm_name": VM,
        "baseline": {c: _pointer(_at(c, BASELINE[c])) for c in names},
        "compared_with": {c: _pointer(_at(c, COMPARED_WITH)) for c in names},
        "delta": {c: _delta(c) for c in names},
        "history": [{"step": step, "manifest": f"{base.name}/{run}/manifest.json",
                     "sha256": _sha((base / run / "manifest.json").read_bytes())}
                    for step, run in HISTORY],
        "freshness_rule": {k: rule[k] for k in ("stale_after_seconds", "clock", "rule",
                                                  "value_status")},
        "delta_rule_status": {"block": layer5.load()["delta"]["status"],
                              "locked": sorted(c for c, r in layer5.load()["delta"]["items"].items()
                                               if r.get("status") == "ditetapkan")},
    }


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    """What the store says today against what the freeze wrote down -- the
    parts it is held to, HELD. Paths that differ are returned; a machine
    without the store says so rather than passing."""
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    if not layer5.store().is_dir():
        return [f"the observation store {layer5.store()} is not on this machine"]
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError) as why:
        return [f"the frozen evidence no longer reads back: {why}"]
    return _diff({k: committed[k] for k in HELD}, {k: fresh[k] for k in HELD})


def _diff(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in _diff(a.get(k), b.get(k),
                                                                 f"{path}/{k}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b, strict=True))
                for d in _diff(x, y, f"{path}/{i}")]
    return [] if a == b else [path]


def _short(sha: str) -> str:
    return f"`{sha[:12]}…`"


def page(model: dict[str, Any]) -> str:
    """NUI/LAYER5.md, drawn from the model only; the headings and the fixed
    sentences are the only words not taken from it."""
    out = ["# Lapis 5 dibekukan — baseline intelijen host", "",
           f"Dihasilkan `{model['generated_by']}` dari evidence store, untuk tag "
           f"`{model['tag']}`. Instance: `{model['vm_name']}`. Yang di-commit hanya "
           "pointer dan hash; teks observasinya tetap di "
           "`~/cosmictera-layer5/observations/`, di luar repositori (K-11).", "",
           "## Baseline", "",
           "| kolektor | status | run | observed_at | stdout sha256 | stderr sha256 |",
           "|---|---|---|---|---|---|"]
    for c, p in model["baseline"].items():
        out.append(f"| `{c}` | {p['status']} | `{p['run_id']}` | {p['observed_at'][:19]} | "
                   f"{_short(p['stdout_sha256'])} | {_short(p['stderr_sha256'])} |")
    rule = model["freshness_rule"]
    value = rule["stale_after_seconds"]
    out += ["", "## Kesegaran", "",
            f"`stale_after_seconds` = `{json.dumps(value)}` — {rule['value_status']}.", "",
            f"Aturannya: {rule['rule']}.", "", f"Jamnya: {rule['clock']}.", "",
            "Kesegaran dinilai saat kueri dijawab, bukan dibekukan di sini: yang dibekukan "
            "adalah `observed_at` tiap observasi dan aturannya.", "",
            "## Delta dari baseline ke run berikutnya", "",
            f"Run pembanding: `{next(iter(model['compared_with'].values()))['run_id']}`. "
            f"Aturan butir: {model['delta_rule_status']['block']}, kecuali yang dikunci "
            "pemilik: " + ", ".join(f"`{c}`" for c in model["delta_rule_status"]["locked"])
            + ".", "",
            "| kolektor | muncul | hilang | berubah | status | sha256 butir |",
            "|---|---:|---:|---:|---|---|"]
    for c, d in model["delta"].items():
        status = d["status"][0] if d["status"][0] == d["status"][1] else " → ".join(d["status"])
        out.append(f"| `{c}` | {d['appeared']} | {d['disappeared']} | {d['changed']} | "
                   f"{status} | {_short(d['items_sha256'])} |")
    for c, d in model["delta"].items():
        for name, n in d.items():
            if isinstance(n, dict):
                out += ["", f"`{c}` — dicatat terpisah sebagai `{name}`, bukan perubahan "
                        f"`{c}` itu sendiri: {n['appeared']} muncul, {n['disappeared']} hilang, "
                        f"{n['changed']} berubah."]
    out += ["", "Isi butirnya dibaca dari evidence store dengan "
            "`python3 -m hijaiyyah.nui.knowledge host delta <kolektor>`, lengkap dengan "
            "provenance kedua run. Tidak ada tindakan otomatis atas delta.", "",
            "## Riwayat P8", "", "| langkah | manifest | sha256 |", "|---|---|---|"]
    for h in model["history"]:
        out.append(f"| {h['step']} | `{h['manifest']}` | {_short(h['sha256'])} |")
    out += ["", "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.layer5_freeze --verify", "```"]
    return "\n".join(out) + "\n"


def write() -> Path:
    model = json.loads(json.dumps(build()))
    MODEL.write_text(json.dumps(model, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    PAGE.write_text(page(model), encoding="utf-8")
    return MODEL


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--write"]:
        print(f"model: {write().relative_to(ROOT)}, page: {PAGE.relative_to(ROOT)}")
        return 0
    problems = verify()
    print("\n".join(problems) if problems else "layer 5 freeze reproduced exactly")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
