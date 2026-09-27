"""Layer 6: an RTL module as a function -- first, hcpu_uart_rx.

    PYTHONPATH=src python3 -m hijaiyyah.nui.rtl_function --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.rtl_function --verify

The Layer 6 item the roadmap already names: the next state predicted for a
named module agrees with its bench. The owner, 28 September 2026, chose
hcpu_uart_rx.v first, because it has a bench of its own, and not hcpu_top.v,
where too many subsystems would enter at once. The RTL is not changed.

The module is written here as a state-transition function,

    (state_t, input_t+1) -> (state_t+1, outputs_t+1)

branch for branch from rtl/hcpu_uart_rx.v; NUI/spec/rtl_function.json names
each branch and the RTL lines it comes from. It is held to what the RTL
itself does when its own bench, rtl/tb/tb_hcpu_uart_rx.v, runs: the bench
and the RTL are compiled unchanged with one probe module beside them, which
prints the design's registers at every falling clock edge. No port is added
and no line of either file changes.

Five checks, each against that trace:

    F1  one step -- from the RTL's own state at cycle t and the input at
        t+1, the function gives the RTL's state and outputs at t+1, at every
        cycle of the bench
    F2  open loop -- from reset, given the bench's inputs alone, the function
        produces the RTL's whole trajectory
    F3  the bench's verdict -- the frames, data, glitch and framing error the
        function predicts are the ones the bench checks, and the bench itself
        prints PASS
    F4  coverage -- every transition rule is exercised at least once, or is
        named as not covered
    F5  the RTL and bench compared are the files whose hashes the model holds

One fact about the bench is measured, not assumed: it changes the line in
the same active region as the clock edge at which the design samples it, and
the simulator runs the bench's assignment first -- so the input to the step
from t to t+1 is the line after edge t+1. On the board the line is
asynchronous, and the two synchroniser flops carry that.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import hardware
from .hardware import _sha
from .repository_index import ROOT

SPEC = ROOT / "NUI" / "spec" / "rtl_function.json"
MODEL = ROOT / "NUI" / "rtl_function.json"
PAGE = ROOT / "NUI" / "RTL_FUNCTION.md"
State = dict[str, int]
Step = Callable[[State, int, int, dict[str, int]], tuple[State, list[str]]]


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SPEC.read_text(encoding="utf-8"))
    return data


# -- hcpu_uart_rx, as a function ---------------------------------------------------------

IDLE, START, DATA, STOP = 0, 1, 2, 3


def uart_rx_parameters(clk_hz: int, baud: int) -> dict[str, int]:
    """rtl/hcpu_uart_rx.v lines 35-37."""
    divisor = clk_hz // baud
    return {"DIVISOR": divisor, "HALF": divisor // 2,
            "CNT_W": math.ceil(math.log2(divisor + 1))}


def uart_rx_reset() -> State:
    """Lines 52 and 57-64."""
    return {"rx_meta": 1, "rx_sync": 1, "state": IDLE, "count": 0, "index": 0,
            "shifter": 0, "rx_data": 0, "rx_valid": 0, "rx_frame_err": 0}


def uart_rx_step(s: State, rx_in: int, rst_n: int, p: dict[str, int]) -> tuple[State, list[str]]:
    """One rising clock edge of hcpu_uart_rx: the next state and outputs, and
    the transition rules that fired, by the names the spec gives them."""
    if not rst_n:
        return uart_rx_reset(), ["reset"]
    mask = (1 << p["CNT_W"]) - 1
    n = dict(s)
    n["rx_meta"], n["rx_sync"] = rx_in, s["rx_meta"]
    n["rx_valid"], n["rx_frame_err"] = 0, 0
    fired = ["sync", "outputs_drop"]
    sync, count = s["rx_sync"], s["count"]
    if s["state"] == IDLE:
        if not sync:
            n["state"], n["count"] = START, 0
            fired.append("idle_falling_edge")
        else:
            fired.append("idle_wait")
    elif s["state"] == START:
        if count == p["HALF"] - 1:
            if not sync:
                n["state"], n["count"], n["index"] = DATA, 0, 0
                fired.append("start_confirmed")
            else:
                n["state"] = IDLE
                fired.append("start_glitch")
        else:
            n["count"] = (count + 1) & mask
            fired.append("start_count")
    elif s["state"] == DATA:
        if count == p["DIVISOR"] - 1:
            n["count"] = 0
            n["shifter"] = (sync << 7) | (s["shifter"] >> 1)
            if s["index"] == 7:
                n["state"] = STOP
                fired.append("data_last")
            else:
                n["index"] = s["index"] + 1
                fired.append("data_sample")
        else:
            n["count"] = (count + 1) & mask
            fired.append("data_count")
    else:
        if count == p["DIVISOR"] - 1:
            n["count"], n["state"] = 0, IDLE
            n["rx_data"], n["rx_valid"], n["rx_frame_err"] = s["shifter"], 1, 1 - sync
            fired.append("stop_deliver")
        else:
            n["count"] = (count + 1) & mask
            fired.append("stop_count")
    return n, fired


FUNCTIONS: dict[str, tuple[Callable[[int, int], dict[str, int]], Callable[[], State], Step]] = {
    "hcpu_uart_rx": (uart_rx_parameters, uart_rx_reset, uart_rx_step)}


# -- the RTL's own trace, under its own bench --------------------------------------------


def _probe(m: dict[str, Any]) -> str:
    """A module that sits beside the bench and prints, at every falling edge,
    the bench's stimulus and the design's registers -- nothing is driven."""
    top, inst = m["top"], f"{m['top']}.{m['instance']}"
    names = [f"{top}.{m['stimulus']['rst_n']}", f"{top}.{m['stimulus']['rx_in']}",
             *[f"{inst}.{s}" for s in [*m["state"], *m["outputs"]]]]
    fmt = " ".join(["%0d"] * len(names))
    return (f"module rtl_function_probe;\n  always @(negedge {top}.{m['clock']})\n"
            f"    $display(\"T {fmt}\", {', '.join(names)});\nendmodule\n")


def rtl_trace(m: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """The bench and the RTL, compiled unchanged with the probe beside them,
    and what they print."""
    root = root or ROOT
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("Icarus Verilog is required to run the bench")
    work = Path(tempfile.mkdtemp())
    try:
        (work / "probe.v").write_text(_probe(m), encoding="utf-8")
        compiled = subprocess.run(
            ["iverilog", "-g2012", "-o", str(work / "sim"), str(root / m["bench"]),
             str(root / m["rtl"]), str(work / "probe.v")],
            capture_output=True, text=True, timeout=300)
        if compiled.returncode != 0:
            raise RuntimeError(f"iverilog failed:\n{compiled.stderr}")
        ran = subprocess.run(["vvp", "-n", str(work / "sim")], capture_output=True, text=True,
                             timeout=300)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    keys = ["rst_n", "rx_in", *m["state"], *m["outputs"]]
    rows = [dict(zip(keys, map(int, ln.split()[1:]), strict=True))
            for ln in ran.stdout.splitlines() if ln.startswith("T ")]
    said = [ln for ln in ran.stdout.splitlines() if not ln.startswith("T ")]
    return {"rows": rows, "said": said}


def _parameters(m: dict[str, Any], root: Path) -> dict[str, int]:
    rule = m["parameters"]
    text = (root / rule["from"]).read_text(encoding="utf-8").splitlines()
    got: dict[str, int] = {}
    for ln in text:
        hit = re.match(rule["pattern"], ln)
        if hit:
            got[hit.group(1)] = int(hit.group(2).replace("_", ""))
    return FUNCTIONS[m["name"]][0](got["CLK_HZ"], got["BAUD"]) | {
        "CLK_HZ": got["CLK_HZ"], "BAUD": got["BAUD"]}


def _state(row: dict[str, int], m: dict[str, Any]) -> State:
    return {k: row[k] for k in [*m["state"], *m["outputs"]]}


def compare(m: dict[str, Any], trace: dict[str, Any], root: Path | None = None,
            step: Step | None = None) -> dict[str, Any]:
    """F1-F4 for one module: the function against the RTL's trace."""
    root = root or ROOT
    params = _parameters(m, root)
    _, reset, own_step = FUNCTIONS[m["name"]]
    step = step or own_step
    rows = trace["rows"]
    one_step, fired_count = [], {r["id"]: 0 for r in m["rules"]}
    for t in range(len(rows) - 1):
        want = _state(rows[t + 1], m)
        got, fired = step(_state(rows[t], m), rows[t + 1]["rx_in"], rows[t + 1]["rst_n"], params)
        for f in fired:
            fired_count[f] = fired_count.get(f, 0) + 1
        if got != want:
            one_step.append(t + 1)
    s, open_loop, frames = reset(), [], []
    if _state(rows[0], m) != s:
        open_loop.append(0)
    for t in range(1, len(rows)):
        s, _ = step(s, rows[t]["rx_in"], rows[t]["rst_n"], params)
        if s != _state(rows[t], m):
            open_loop.append(t)
        if s["rx_valid"]:
            frames.append((s["rx_data"], bool(s["rx_frame_err"])))
    verdict = next((ln for ln in trace["said"] if re.match(m["bench_verdict"]["pattern"], ln)),
                   None)
    # the input timing, measured: at each edge where the bench changed the
    # line, which value the first synchroniser flop took
    changed = [t for t in range(len(rows) - 1)
               if rows[t + 1]["rst_n"] and rows[t + 1]["rx_in"] != rows[t]["rx_in"]]
    timing = {"line_changes": len(changed),
              "captured_new": sum(1 for t in changed
                                  if rows[t + 1]["rx_meta"] == rows[t + 1]["rx_in"]),
              "captured_old": sum(1 for t in changed if rows[t + 1]["rx_meta"] == rows[t]["rx_in"])}
    return {"parameters": params, "cycles": len(rows), "input_timing": timing,
            "one_step_mismatches": one_step,
            "open_loop_mismatches": open_loop, "frames": [f[0] for f in frames],
            "frame_errors": [f[1] for f in frames], "bench_said": trace["said"][0],
            "bench_pass": verdict is not None, "rules_fired": fired_count}


# -- the model -------------------------------------------------------------------------------


def build(root: Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    spec = load()
    modules = []
    for m in spec["modules"]:
        rtl_lines = (root / m["rtl"]).read_text(encoding="utf-8").splitlines()
        cited = sorted({n for r in m["rules"] for n in r["lines"]})
        if cited[-1] > len(rtl_lines):
            raise LookupError(f"{m['name']}: a rule cites line {cited[-1]} of "
                              f"{len(rtl_lines)}")
        trace = rtl_trace(m, root)
        result = compare(m, trace, root)
        text = "\n".join(" ".join(str(r[k]) for k in r) for r in trace["rows"])
        modules.append({
            "name": m["name"], "rtl": m["rtl"], "rtl_sha256": _sha((root / m["rtl"]).read_bytes()),
            "bench": m["bench"], "bench_sha256": _sha((root / m["bench"]).read_bytes()),
            "trace_sha256": _sha(text.encode("utf-8")), **result,
            "rules": [{"id": r["id"], "lines": r["lines"], "fired": result["rules_fired"][r["id"]]}
                      for r in m["rules"]],
            "not_covered": [r["id"] for r in m["rules"] if not result["rules_fired"][r["id"]]]})
    tool = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout
    return {"generated_by": "src/hijaiyyah/nui/rtl_function.py",
            "spec": "NUI/spec/rtl_function.json",
            "simulator": tool.splitlines()[0] if tool else None, "modules": modules}


def check(model: dict[str, Any]) -> list[str]:
    """F1-F5 on a built model, against the spec's expectations of the bench."""
    spec, bad = load(), []
    for m, s in zip(model["modules"], spec["modules"], strict=True):
        if m["one_step_mismatches"]:
            bad.append(f"F1 {m['name']}: {len(m['one_step_mismatches'])} cycles differ, "
                       f"first {m['one_step_mismatches'][0]}")
        if m["open_loop_mismatches"]:
            bad.append(f"F2 {m['name']}: the trajectory leaves the RTL's at cycle "
                       f"{m['open_loop_mismatches'][0]}")
        want = s["bench_expects"]
        if (m["frames"], m["frame_errors"]) != (want["frames"], want["frame_errors"]) \
                or not m["bench_pass"]:
            bad.append(f"F3 {m['name']}: predicted {m['frames']} {m['frame_errors']}, bench "
                       f"{'PASS' if m['bench_pass'] else m['bench_said']}")
        if m["not_covered"]:
            bad.append(f"F4 {m['name']}: rules the bench never runs: {m['not_covered']}")
        timing = m["input_timing"]
        if timing["captured_new"] != timing["line_changes"] or timing["captured_old"]:
            bad.append(f"F1 {m['name']}: the input timing the function assumes does not hold: "
                       f"{timing}")
        if (m["rtl_sha256"], m["bench_sha256"]) != (_sha((ROOT / s["rtl"]).read_bytes()),
                                                   _sha((ROOT / s["bench"]).read_bytes())):
            bad.append(f"F5 {m['name']}: the RTL or bench is not the one the model holds")
    return bad


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    try:
        fresh = json.loads(json.dumps(build()))
    except (LookupError, OSError, KeyError, ValueError, RuntimeError) as why:
        return [f"the RTL function model no longer reads back: {why}"]
    return hardware._diff(committed, fresh) + check(committed)


def page(model: dict[str, Any]) -> str:
    spec = load()
    out = ["# Model RTL sebagai fungsi — Lapis 6", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}`. RTL dan bench "
           "dikompilasi apa adanya dengan satu modul probe di sampingnya yang mencetak register "
           f"desain di tiap tepi turun clock; tidak ada port atau baris yang berubah. "
           f"Simulator: {model['simulator']}.", ""]
    for m, s in zip(model["modules"], spec["modules"], strict=True):
        p = m["parameters"]
        out += [f"## `{m['name']}`", "",
                f"`{m['rtl']}` `{m['rtl_sha256'][:12]}…`, bench `{m['bench']}` "
                f"`{m['bench_sha256'][:12]}…`. CLK_HZ {p['CLK_HZ']}, BAUD {p['BAUD']}, DIVISOR "
                f"{p['DIVISOR']}, HALF {p['HALF']}, CNT_W {p['CNT_W']}.", "",
                "| pemeriksaan | hasil |", "|---|---|",
                f"| F1 satu langkah, {m['cycles'] - 1} transisi | "
                f"{len(m['one_step_mismatches'])} berbeda |",
                f"| F2 lingkar terbuka dari reset, {m['cycles']} siklus | "
                f"{len(m['open_loop_mismatches'])} berbeda |",
                f"| F3 frame yang diprediksi | {', '.join(f'0x{b:02X}' for b in m['frames'])}; "
                f"framing error {m['frame_errors']} |",
                f"| F3 bench | {m['bench_said']} |",
                f"| waktu input: perubahan line, ditangkap nilai baru, ditangkap nilai lama | "
                f"{m['input_timing']['line_changes']}, {m['input_timing']['captured_new']}, "
                f"{m['input_timing']['captured_old']} |",
                f"| jejak RTL | `{m['trace_sha256'][:12]}…` |", "",
                "| aturan | baris RTL | arti | dijalankan bench |", "|---|---|---|---|"]
        means = {r["id"]: r["means"] for r in s["rules"]}
        out += [f"| `{r['id']}` | {', '.join(map(str, r['lines']))} | {means[r['id']]} | "
                f"{r['fired']} |" for r in m["rules"]]
        out += ["", f"Tidak tercakup bench: {', '.join(m['not_covered']) or 'tidak ada'}.", "",
                f"**Waktu input.** {s['input_timing']['rule']}: {s['input_timing']['why']}.", ""]
    out += ["## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.rtl_function --verify", "```"]
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
    print("\n".join(problems) if problems else "RTL function model reproduced exactly")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
