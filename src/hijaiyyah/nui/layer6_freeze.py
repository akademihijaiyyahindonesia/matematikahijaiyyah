"""Layer 6 frozen: hardware understanding, as the repository stood when the HCPU model was accepted.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_freeze --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_freeze --verify

The owner's close of Layer 6, 29 September 2026: the HCPU system-level model
(1c33e30) was accepted GREEN, its acceptance recorded (d003cac), and Layer 6
frozen with the annotated tag layer6-freeze-2026-09-29-final -- the shape of
the Layer 4 and Layer 5 freezes.

What differs from both is what the evidence is. Every Layer 6 artefact is
derived: each rebuilds from the repository by its own --verify, so its hash
may move whenever the repository does. This freeze therefore reads nothing
from the working tree. It reads git objects at one commit, the recording of
the acceptance, and at the commit Layer 6 opened from, the final Layer 5
freeze. What it writes down stays true for as long as the history exists:

    scope        the owner's seven parts, each with the commits that built
                 it -- every commit of Layer 6, once -- its artefacts' SHA-256
                 at the frozen commit, and the GREEN the notes record for it
    hcpu         the accepted model's results, read from its committed model
    non_claims   what the model does not claim: the rules not covered, the
                 HISAB discrepancy, the opaque state, and the subsystems with
                 no function
    integrity    the RTL, the benches and the wrappers' fingerprints unchanged
                 across Layer 6, no bitstream tracked, the one accepted red test,
                 and the gates run before the freeze

Nothing is re-measured here and nothing is smoothed: the HISAB discrepancy
stays a measured discrepancy, and the 78 rules stay not covered.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .repository_index import ROOT

MODEL = ROOT / "NUI" / "layer6_freeze.json"
PAGE = ROOT / "NUI" / "LAYER6.md"
TAG = "layer6-freeze-2026-09-29-final"
#: Layer 6 opened from the final Layer 5 freeze (layer5-freeze-2026-09-27-final).
OPENED_FROM = "80ea5f8"
HCPU_MODEL = "1c33e30"
#: The recording of the acceptance: the frozen state of the repository.
FROZEN_AT = "d003cac"
RTL_FUNCTION = ["NUI/RTL_FUNCTION.md", "NUI/rtl_function.json", "NUI/spec/rtl_function.json"]
#: The owner's scope, in the owner's order. Each commit of Layer 6 is in
#: exactly one part; "green" is what AGENTS.md records as accepted GREEN.
SCOPE: list[dict[str, Any]] = [
    {"part": "Inventaris hardware", "step": "6.1", "commits": ["cde7d77"], "green": [],
     "verify": "hardware",
     "artefacts": ["NUI/HARDWARE.md", "NUI/hardware_inventory.json",
                   "NUI/spec/hardware_inventory.json"]},
    {"part": "Sumber telemetri", "step": "6.2", "commits": ["091e611"], "green": [],
     "verify": "telemetry_sources",
     "artefacts": ["NUI/TELEMETRY_SOURCES.md", "NUI/telemetry_sources.json",
                   "NUI/spec/telemetry_sources.json"]},
    {"part": "Provenance hardware", "step": "6.3", "commits": ["08ffbed"], "green": ["08ffbed"],
     "verify": "hardware_provenance",
     "artefacts": ["NUI/HARDWARE_PROVENANCE.md", "NUI/hardware_provenance.json",
                   "NUI/spec/hardware_provenance.json"]},
    {"part": "Model keadaan hardware", "step": "6.4", "commits": ["d6cfd6c", "5e4aa03"],
     "green": ["d6cfd6c"], "verify": "hardware_state",
     "artefacts": ["NUI/HARDWARE_STATE.md", "NUI/hardware_state.json",
                   "NUI/spec/hardware_state.json"]},
    {"part": "Korelasi hardware", "step": "6.5", "commits": ["3617a31"], "green": ["3617a31"],
     "verify": "hardware_correlation",
     "artefacts": ["NUI/HARDWARE_CORRELATION.md", "NUI/hardware_correlation.json",
                   "NUI/spec/hardware_correlation.json"]},
    {"part": "RTL sebagai fungsi", "step": "model RTL sebagai fungsi",
     "commits": ["6a9a541", "b643b88", "ecb417b", "604bbb8", "0e8b699", "6d8839a", "bd8158c",
                 "bf13941", "e897ed0", "f590bac"],
     "green": ["ecb417b", "604bbb8", "0e8b699", "6d8839a", "bd8158c", "bf13941", "e897ed0",
               "f590bac"],
     "verify": "rtl_function", "artefacts": RTL_FUNCTION},
    {"part": "Model HCPU prediktif tingkat sistem", "step": "model RTL sebagai fungsi",
     "commits": [HCPU_MODEL, FROZEN_AT], "green": [HCPU_MODEL], "verify": "rtl_function",
     "artefacts": RTL_FUNCTION},
]
#: The gates run before this freeze, and the one red the owner accepted.
VERIFY = ["rtl_function", "hardware_correlation", "hardware_state", "hardware_provenance",
          "layer4_freeze", "parity_model", "layer5_freeze", "hardware", "telemetry_sources"]
ACCEPTED_RED = ("tests/test_integrity/test_place_and_route.py",
                "test_the_hdmi_wrapper_records_its_own_fingerprint")


def _git(*args: str) -> str:
    ran = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if ran.returncode != 0:
        raise LookupError(f"git {' '.join(args)}: {ran.stderr.strip()}")
    return ran.stdout


def _blob(commit: str, path: str) -> bytes:
    ran = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True,
                         timeout=120)
    if ran.returncode != 0:
        raise LookupError(f"{path} is not in {commit}")
    return ran.stdout


def _full(commit: str) -> str:
    return _git("rev-parse", "--verify", f"{commit}^{{commit}}").strip()


def _ancestor(a: str, b: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=ROOT,
                          timeout=120).returncode == 0


def _green_recorded(agents: str, commit: str) -> bool:
    """AGENTS.md at the frozen commit names this commit with GREEN in the
    same paragraph."""
    return any(f"`{commit}`" in p and "GREEN" in p for p in agents.split("\n\n"))


def _hcpu(model: dict[str, Any]) -> dict[str, Any]:
    m = next(x for x in model["modules"] if x["name"] == "hcpu")
    fired = sum(1 for r in m["rules"] if r["fired"])
    return {"edges": m["steps"], "rows": m["cycles"],
            "sampling_mismatched": len(m["sampling"]["mismatched"]),
            "one_step_mismatches": len(m["one_step_mismatches"]),
            "outputs_per_row": m["outputs_compared"],
            "output_mismatches": len(m["output_mismatches"]),
            "open_loop_mismatches": len(m["open_loop_mismatches"]),
            "open_loop_reached": m["open_loop_reached"],
            "terminal_reads": len(m["terminal"]),
            "terminal_mismatches": len(m["terminal_mismatches"]),
            "ram_words_checked": m["ram"]["checked"],
            "ram_mismatches": len(m["ram"]["mismatches"]),
            "ram_final": m["ram"]["final"], "operands_moved": m["operands_moved"],
            "not_covered_outputs": m["not_covered_outputs"], "unpredicted": m["unpredicted"],
            "rules": len(m["rules"]), "rules_fired": fired, "bench_said": m["bench_said"],
            "trace_sha256": m["trace_sha256"]}


def build() -> dict[str, Any]:
    frozen, opened, hcpu = _full(FROZEN_AT), _full(OPENED_FROM), _full(HCPU_MODEL)
    layer6 = _git("rev-list", "--reverse", f"{opened}..{frozen}").split()
    agents = _blob(frozen, "AGENTS.md").decode("utf-8")
    model = json.loads(_blob(frozen, "NUI/rtl_function.json"))
    spec = json.loads(_blob(frozen, "NUI/spec/rtl_function.json"))
    m = next(x for x in model["modules"] if x["name"] == "hcpu")
    s = next(x for x in spec["modules"] if x["name"] == "hcpu")
    audit, audit_spec = model["hcpu_audit"], spec["hcpu_audit"]
    fired = {t["id"]: t["fired"] for t in audit["transitions"]}
    test = _blob(frozen, ACCEPTED_RED[0]).decode("utf-8")
    return {
        "generated_by": "src/hijaiyyah/nui/layer6_freeze.py",
        "tag": TAG,
        "layer": {"title": "Pemahaman perangkat keras", "alias": "Hardware Intelligence",
                  "status": "FROZEN"},
        "commits": {"opened_from": opened, "hcpu_model": hcpu, "frozen_at": frozen,
                    "in_order": _ancestor(opened, hcpu) and _ancestor(hcpu, frozen),
                    "layer6": len(layer6)},
        "scope": [{"part": p["part"], "step": p["step"],
                   "commits": [{"commit": _full(c),
                                "subject": _git("log", "-1", "--format=%s", _full(c)).strip(),
                                "in_layer6": _full(c) in layer6,
                                "green": c in p["green"] and _green_recorded(agents, c)}
                               for c in p["commits"]],
                   "verify": p["verify"],
                   "artefacts": {a: hashlib.sha256(_blob(frozen, a)).hexdigest()
                                 for a in p["artefacts"]}}
                  for p in SCOPE],
        "hcpu": _hcpu(model),
        "non_claims": {
            "not_covered": m["not_covered"],
            "hisab_discrepancy": {"measured": m["hisab_discrepancy"],
                                  "recorded": s["known_discrepancy"]["hisab"]["measured"]},
            "opaque_state": list(s["opaque"]),
            "outside_results": {k: list(v) for k, v in s["externals"].items()},
            "subsystems_without_function": {
                sub["id"]: {"transitions": len([t for t in fired
                                                if t.startswith(f"{sub['id']}.")]),
                            "ran": sum(1 for t, n in fired.items()
                                       if t.startswith(f"{sub['id']}.") and n)}
                for sub in audit_spec["subsystems"]
                if sub.get("function") is None and sub["id"] not in s["composed"]}},
        "integrity": {
            "rtl_changed_in_layer6": _git("diff", "--name-only", opened, frozen,
                                          "--", "rtl/").split(),
            "bitstreams_tracked": [p for p in _git("ls-tree", "-r", "--name-only",
                                                   frozen).split() if p.endswith(".fs")],
            "accepted_red": {"test": "::".join(ACCEPTED_RED),
                             "present": f"def {ACCEPTED_RED[1]}(" in test},
            "verify": VERIFY},
    }


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    """The freeze read again from the same git objects: every path that
    differs is returned."""
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError, ValueError) as why:
        return [f"the frozen state no longer reads back: {why}"]
    return _diff(committed, fresh) + check(committed)


def check(model: dict[str, Any]) -> list[str]:
    """What a freeze of Layer 6 must say to be one: the commits in order,
    every Layer 6 commit in exactly one part, the GREEN it claims recorded,
    the model's results as accepted, and the RTL untouched."""
    bad = []
    c = model["commits"]
    if not c["in_order"]:
        bad.append("the commits are not in order: opened_from, hcpu_model, frozen_at")
    listed = [x["commit"] for p in model["scope"] for x in p["commits"]]
    if len(listed) != len(set(listed)) or len(listed) != c["layer6"] or not all(
            x["in_layer6"] for p in model["scope"] for x in p["commits"]):
        bad.append(f"the scope does not hold each of Layer 6's {c['layer6']} commits once")
    claimed = {g for p in SCOPE for g in p["green"]}
    recorded = {x["commit"][:7] for p in model["scope"] for x in p["commits"] if x["green"]}
    if claimed != recorded:
        bad.append(f"GREEN without a record in AGENTS.md: {sorted(claimed - recorded)}")
    h = model["hcpu"]
    zero = ("sampling_mismatched", "one_step_mismatches", "output_mismatches",
            "open_loop_mismatches", "terminal_mismatches", "ram_mismatches", "operands_moved")
    if any(h[k] for k in zero) or h["open_loop_reached"] != h["edges"]:
        bad.append(f"the HCPU model's results are not the accepted ones: {h}")
    nc = model["non_claims"]
    if len(nc["not_covered"]) != h["rules"] - h["rules_fired"]:
        bad.append("the rules not covered are not the rules that never fired")
    if nc["hisab_discrepancy"]["measured"] != nc["hisab_discrepancy"]["recorded"]:
        bad.append("the HISAB discrepancy is not the one recorded")
    i = model["integrity"]
    if i["rtl_changed_in_layer6"] or i["bitstreams_tracked"] or not i["accepted_red"]["present"]:
        bad.append(f"the integrity record does not hold: {i}")
    return bad


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
    """NUI/LAYER6.md, drawn from the model only; the headings and the fixed
    sentences are the only words not taken from it."""
    c, h, nc, i = model["commits"], model["hcpu"], model["non_claims"], model["integrity"]
    out = [f"# Lapis 6 dibekukan — {model['layer']['title'].lower()}", "",
           f"Dihasilkan `{model['generated_by']}` untuk tag `{model['tag']}`. Status: "
           f"**{model['layer']['status']}**. Judul resmi *{model['layer']['title']}*, "
           f"alias *{model['layer']['alias']}*.", "",
           "Freeze ini tidak membaca pohon kerja. Ia membaca objek git di commit "
           f"`{c['frozen_at'][:7]}` — pencatatan GREEN model HCPU — dan di "
           f"`{c['opened_from'][:7]}`, freeze final Lapis 5 tempat Lapis 6 dibuka. Artefak "
           "Lapis 6 semuanya turunan yang dibangun ulang oleh `--verify`-nya masing-masing, "
           "jadi yang dibekukan adalah keadaannya di commit itu.", "",
           "| | commit |", "|---|---|",
           f"| Lapis 6 dibuka dari | `{c['opened_from'][:7]}` |",
           f"| model HCPU | `{c['hcpu_model'][:7]}` |",
           f"| pencatatan GREEN, keadaan yang dibekukan | `{c['frozen_at'][:7]}` |",
           f"| commit Lapis 6 | {c['layer6']}, "
           + ("berurutan" if c["in_order"] else "TIDAK berurutan") + " |", "",
           "## Cakupan", "",
           "| bagian | langkah | commit | GREEN tercatat | `--verify` | artefak (sha256 di "
           "commit beku) |", "|---|---|---|---|---|---|"]
    for p in model["scope"]:
        commits = ", ".join(f"`{x['commit'][:7]}`" for x in p["commits"])
        green = ", ".join(f"`{x['commit'][:7]}`" for x in p["commits"] if x["green"]) or "—"
        arts = "; ".join(f"`{a}` {_short(v)}" for a, v in p["artefacts"].items())
        out.append(f"| {p['part']} | {p['step']} | {commits} | {green} | `{p['verify']}` | "
                   f"{arts} |")
    out += ["", "Tiap commit Lapis 6 ada di tepat satu bagian:", "",
            *[f"- `{x['commit'][:7]}` {x['subject']}" for p in model["scope"]
              for x in p["commits"]], "",
            "## Model HCPU final", "",
            "Satu transisi tingkat sistem, state prediktif parsial, komposisi subsistem yang "
            f"terverifikasi, dipegang pada `rtl/tb/tb_hcpu_top.v`. Jejak RTL "
            f"{_short(h['trace_sha256'])}.", "",
            "| pemeriksaan | hasil |", "|---|---|",
            f"| titik sampel, {h['edges']} tepi | {h['sampling_mismatched']} sinyal berbeda |",
            f"| satu langkah dari keadaan RTL, {h['edges']} tepi | "
            f"{h['one_step_mismatches']} berbeda |",
            f"| keluaran, {h['outputs_per_row']} per baris, {h['rows']} baris | "
            f"{h['output_mismatches']} berbeda; berhenti not covered: "
            + ", ".join(f"{k} ({v} baris)" for k, v in h["not_covered_outputs"].items()) + " |",
            f"| lingkar terbuka dari reset | {h['open_loop_mismatches']} berbeda, sampai tepi "
            f"{h['open_loop_reached']} |",
            f"| RAM | {h['ram_words_checked']} kata port, {h['ram_mismatches']} berbeda; saat "
            f"`$finish` {h['ram_final']['function']} lawan {h['ram_final']['rtl']} kata, "
            f"{len(h['ram_final']['differ'])} berbeda |",
            f"| operand ALU bergerak bersama hasilnya | {h['operands_moved']} baris |",
            f"| bacaan terminal bench | {h['terminal_reads']}, {h['terminal_mismatches']} "
            "berbeda |",
            f"| aturan | {h['rules_fired']} dari {h['rules']} dijalankan |",
            "| register yang tidak diprediksi | "
            + ", ".join(f"{k} ({v} tepi)" for k, v in h["unpredicted"].items()) + " |",
            f"| bench | {h['bench_said']} |", "",
            "## Yang tidak diklaim", "",
            f"- **{len(nc['not_covered'])} aturan NotCovered** — fungsi berhenti di sana, tidak "
            "memprediksi: " + ", ".join(f"`{r}`" for r in nc["not_covered"]) + ".",
            f"- **Ketidaksesuaian HISAB tetap ketidaksesuaian terukur**: "
            f"{nc['hisab_discrepancy']['measured']['edges']} tepi, program "
            + ", ".join(map(str, nc["hisab_discrepancy"]["measured"]["programs"]))
            + f", {nc['hisab_discrepancy']['measured']['consumed']} di tepi yang memakainya. "
            "HISAB adalah hasil luar, dan perbaikan urutan bitnya butir tersendiri.",
            "- **State opaque tidak diklaim paritasnya**: "
            + ", ".join(f"{k}" for k in nc["opaque_state"]) + ".",
            "- **Hasil luar, dari jejak, tidak diprediksi**: "
            + "; ".join(f"{k} ({', '.join(v)})" for k, v in nc["outside_results"].items()) + ".",
            "- **Perilaku subsistem tanpa fungsi tidak disimpulkan**: "
            + "; ".join(f"{k} — {v['ran']} dari {v['transitions']} transisi dijalankan bench, "
                        "tidak satu pun diprediksi"
                        for k, v in nc["subsystems_without_function"].items()) + ".", "",
            "## Integritas", "",
            "- RTL, bench, dan header sidik jari wrapper yang berubah sepanjang Lapis 6 "
            f"(`git diff {c['opened_from'][:7]} {c['frozen_at'][:7]} -- rtl/`): "
            + (", ".join(i["rtl_changed_in_layer6"]) or "tidak ada") + ".",
            "- Bitstream yang dilacak git: "
            + (", ".join(i["bitstreams_tracked"]) or "tidak ada") + " — berkas `.fs` "
            "di-gitignore, jadi \"bitstream tidak berubah\" bersandar pada sidik jari di header "
            "wrapper, yang ada di `rtl/` dan tidak berubah.",
            f"- Satu tes merah yang diterima tetap diterima: `{i['accepted_red']['test']}` "
            "(sidik jari HDMI, M5.2B ditunda).",
            "- Gerbang yang dijalankan sebelum freeze ini: ruff, mypy, pytest penuh, dan "
            + ", ".join(f"`{v}`" for v in i["verify"]) + " `--verify`.", "",
            "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_freeze --verify", "```"]
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
    print("\n".join(problems) if problems else "layer 6 freeze reproduced exactly")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
