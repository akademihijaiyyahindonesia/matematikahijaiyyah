"""Layer 4 frozen: the evidence of P0-P6, and every discrepancy it holds, by class.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer4_freeze --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer4_freeze --verify

The owner's step P7, 26 September 2026. No experiment is run here and no
expectation is moved: everything below is read from records already committed
-- the burn-in, the raw capture, the board parity runs, the opcode column, the
PRINT ladder, the stop probes, the loader cases -- and recomputed from them, so
the report cannot say more than they do.

Layer 4 is not frozen because everything is green. It is frozen because every
colour has a source and a reason:

    PARITY    the board's evidence agrees
    MISMATCH  valid board evidence differs from the frozen expectation
    UNKNOWN   there is not enough evidence, or it cannot be observed

and the discrepancies are kept in the owner's four classes, the last of them
apart from the rest -- a tool that read the wire wrongly is not a board that
answered wrongly:

    measured mismatch           the board, measured, differs
    known semantic difference   the engines count different things
    unknown / not observable    no evidence, mixed evidence, or no path out
    known tooling discrepancy   the host's reading, not the silicon

Two things this module holds and does not smooth over. The P2 reports were
written against the expectation of their day; P6 froze it again and moved one
line -- the exclusion reason of a program never sent -- so recomputing those
reports today differs on exactly that path, and it is named here, not
rewritten. And the burn-in and the loader records do not carry the bitstream's
fingerprint themselves; the ones that do all carry 84fdc912..., and which is
which is listed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .repository_index import ROOT

MODEL = ROOT / "NUI" / "layer4_freeze.json"
PAGE = ROOT / "NUI" / "LAYER4.md"
TAG = "layer4-freeze-2026-09-26"
FINGERPRINT = "84fdc91232465c9600e1f7cc59dba891f309c69cf2441c448d684baaf4a7e261"

BURN = "cosmictera-build/burn-in/"
BOARD = "cosmictera-build/parity-board/"
#: Every piece of evidence the freeze rests on, by the owner's step.
EVIDENCE: list[tuple[str, str]] = [
    ("P0", BURN + "20260921T053430Z-burn-in-72h.json"),
    ("P0", BURN + "20260921T053430Z-burn-in-72h.jsonl"),
    ("P0", BURN + "20260921T053430Z-burn-in-72h-baseline.json"),
    ("P1", BURN + "20260924T073655Z-burn-in-capture.json"),
    ("P1", BURN + "20260924T073655Z-burn-in-capture.raw"),
    ("P1", BURN + "20260924T073655Z-burn-in-capture.times.jsonl"),
    ("P1", BURN + "20260924T073655Z-burn-in-parsed.json"),
    ("P1", BURN + "20260924T073655Z-burn-in-parsed.jsonl"),
    ("P2", BOARD + "20260924T104300Z-parity.json"),
    ("P2", BOARD + "20260924T104300Z-parity.report.json"),
    ("P2", BOARD + "20260924T105400Z-parity.json"),
    ("P2", BOARD + "20260924T105400Z-parity.report.json"),
    ("P4", BOARD + "20260925T141701Z-print.json"),
    ("P4", BOARD + "20260925T141701Z-print.report.json"),
    ("P4", BOARD + "20260925T141737Z-print.json"),
    ("P4", BOARD + "20260925T141737Z-print.report.json"),
    ("P4", BOARD + "20260925T141744Z-print.json"),
    ("P4", BOARD + "20260925T141744Z-print.report.json"),
    ("P5", BOARD + "20260925T163903Z-stop.json"),
    ("P5", BOARD + "20260925T163903Z-stop.report.json"),
    ("P6", "cosmictera-build/attack-lab/20260925T191528Z-loader.json"),
]
#: Built from the records rather than recorded by a board: their hashes are
#: written down as they stood at the freeze, for the tag, and not held to that
#: afterwards -- a program changed later rebuilds them, and that is not the
#: evidence moving. P3's column is recomputed from P2's record instead.
DERIVED_AT_FREEZE = ["NUI/parity_model.json", "NUI/board_expected.json"]
#: What a test holds the committed freeze to for as long as it exists: the
#: records themselves, and what they say.
HELD = ("evidence", "bitstream_carried_by", "status", "discrepancies")
PARITY_OF_RECORD = BOARD + "20260924T105400Z-parity.json"
PARITY_CONTAMINATED = BOARD + "20260924T104300Z-parity.json"
PRINT_RUNS = [BOARD + f"2026092{s}-print.json" for s in
              ("5T141701Z", "5T141737Z", "5T141744Z")]
STOP_RUN = BOARD + "20260925T163903Z-stop.json"
LOADER_RUN = "cosmictera-build/attack-lab/20260925T191528Z-loader.json"
#: The one path a recomputed report may differ on, and why. P6 moved it.
KNOWN_REPORT_DIFFERENCE = "/programs/rtl/programs/hos_prog_load.hasm/reason"


def _load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _diff(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in _diff(a.get(k), b.get(k),
                                                                 f"{path}/{k}")]
    return [] if a == b else [path]


def _statuses(report: dict[str, Any]) -> dict[str, str]:
    return {name: row["status"] for name, row in report["programs"].items()}


def reproducibility() -> list[dict[str, Any]]:
    """Every board report recomputed from its record with today's code and
    today's frozen expectation: the verdicts must be the same, and anything
    else that differs is listed by path."""
    from .board_parity import report

    out = []
    for _, path in EVIDENCE:
        if not path.startswith(BOARD) or path.endswith(".report.json"):
            continue
        record = _load(path)
        committed = _load(path[:-5] + ".report.json")
        again = json.loads(json.dumps(report(record), sort_keys=True))
        out.append({"record": path, "expected_sha256": record["expected_sha256"],
                    "verdicts_reproduce": _statuses(again) == _statuses(committed),
                    "differs_at": _diff(committed, again)})
    return out


def _tooling() -> list[dict[str, Any]]:
    """The host's reading, measured from the records -- never mixed with the
    board's answers."""
    burn = [json.loads(ln) for ln in (ROOT / (BURN + "20260921T053430Z-burn-in-72h.jsonl"))
            .read_text(encoding="utf-8").splitlines() if ln.strip()]
    errors = [r for r in burn if r.get("kind") == "error"]
    zero_h = {round(r["t"]) for r in burn if r.get("kind") == "unparsed" and r.get("text") == "0H"}
    worst = max((r.get("errors", 0) for r in burn if r.get("kind") == "sample"), default=0)

    rotated = total = 0
    captures = [p for _, p in EVIDENCE if p.startswith(BOARD) and not p.endswith(".report.json")]
    for path in captures:
        for got in _load(path)["programs"].values():
            raw = bytes.fromhex(got.get("raw_hex", ""))
            if b"CYCLES=" not in raw:
                continue
            total += 1
            head, _, tail = raw.partition(b"CYCLES=")
            if re.fullmatch(rb"[0-9A-F]{8}\r\n\n", tail) and head.endswith(b"\n") \
                    and not head.endswith(b"\r\n"):
                rotated += 1

    first = next(iter(_load(PARITY_CONTAMINATED)["programs"].items()))
    stale = bytes.fromhex(first[1]["raw_hex"]).count(b"\nH\n")
    return [
        {"id": "burn_in_parser_artifacts",
         "what": "two `error` rows in the 72-hour log that the board never raised",
         "count": len(errors),
         "evidence": BURN + "20260921T053430Z-burn-in-72h.jsonl",
         "measured": (f"each row shares its second with an unparsed `0H` "
                      f"({sum(1 for r in errors if round(r['t']) in zero_h)} of {len(errors)}); "
                      f"the board's own cumulative counter never exceeds {worst}"),
         "kept_as": "known parser artefact (K-1); the run keeps no raw bytes"},
        {"id": "cycles_report_one_byte_out",
         "what": ("the wrapper's CYCLES= report arrives rotated one byte -- `\\n` in front "
                  "instead of `\\r\\n`, one `\\n` over at the end, nineteen bytes either way"),
         "count": rotated, "of": total, "records": len(captures),
         "evidence": PARITY_OF_RECORD,
         "kept_as": ("the reader drops exactly one newline, the report's; the wrapper is "
                     "reported in cosmictera-build/OFF.md and not repaired (K9)")},
        {"id": "stale_burn_in_bytes_in_the_first_p2_run",
         "what": (f"the first program of the first P2 run opened with the burn-in's "
                  f"heartbeats still buffered by the driver ({stale} of them)"),
         "count": 1, "program": first[0],
         "evidence": PARITY_CONTAMINATED,
         "kept_as": ("the runner drains the wire before sending; the run after is the "
                     "record of P2, and both records are kept")},
    ]


def _opcode_column() -> dict[str, dict[str, Any]]:
    """P3's column, from P2's record of record -- not from the model file."""
    from .board_parity import classify, load_expected, opcode_column, reparsed

    section = load_expected()["parity"]
    column = opcode_column(classify(reparsed(_load(PARITY_OF_RECORD)), section), section)
    return {name: {"board": c["board"], "parity": len(c["agreeing"]),
                   "mismatch": len(c["differing"]),
                   "evidence": len(c["agreeing"]) + len(c["differing"])
                   + sum(1 for p in c["undecided"]
                         if section["programs"][p]["sent"])}
            for name, c in column.items()}


def build() -> dict[str, Any]:
    parity = _load(PARITY_OF_RECORD[:-5] + ".report.json")
    column = _opcode_column()
    opcode_counts = {s: sum(1 for c in column.values() if c["board"] == s)
                     for s in ("PARITY", "MISMATCH", "UNKNOWN")}
    stop = _load(STOP_RUN[:-5] + ".report.json")
    loader = _load(LOADER_RUN)
    counts = parity["counts"]

    mismatch_programs = sorted(n for n, r in parity["programs"].items()
                               if r["status"] == "MISMATCH")
    counter = sorted(n for n, r in parity["programs"].items()
                     if r["status"] == "UNKNOWN" and "counter" in r.get("reason", ""))
    not_sent = sorted(n for n, r in parity["programs"].items()
                      if r["status"] == "UNKNOWN" and r.get("reason", "").startswith("not sent"))
    mixed = sorted(n for n, c in column.items() if c["parity"] and c["mismatch"])
    unexercised = sorted(n for n, c in column.items() if c["evidence"] == 0)

    ladder: dict[str, list[str]] = {}
    for path in PRINT_RUNS:
        for row in _load(path[:-5] + ".report.json")["ladder"]:
            ladder.setdefault(str(row["power"]), []).append(row["board"])
    values = {str(r["power"]): r["interpreter"]
              for r in _load(PRINT_RUNS[0][:-5] + ".report.json")["ladder"]}
    failing = sorted((p for p, got in ladder.items() if any(g != values[p] for g in got)),
                     key=int)
    wrong = [(p, g) for p in failing for g in ladder[p] if g != values[p]]

    wire_yes = [r["probe"] for r in stop["probes"] if r.get("board_answer") == "yes"]
    unseen = [r["probe"] for r in stop["probes"]
              if str(r.get("board_answer", "")).startswith("UNKNOWN")]
    windows = [r["probe"] for r in stop["probes"] if "against_rtl" in r]

    carried = [p for _, p in EVIDENCE if p.endswith(".json") and not p.endswith(".report.json")
               and isinstance(_load(p), dict) and _load(p).get("bitstream_sha256")]
    return {
        "generated_by": "src/hijaiyyah/nui/layer4_freeze.py",
        "tag": TAG,
        "bitstream_sha256": FINGERPRINT,
        "bitstream_carried_by": {p: _load(p)["bitstream_sha256"] == FINGERPRINT
                                 for p in carried},
        "evidence": [{"phase": ph, "path": p, "bytes": (ROOT / p).stat().st_size,
                      "sha256": _sha(p)} for ph, p in EVIDENCE],
        "derived_at_freeze": [{"path": p, "sha256": _sha(p)} for p in DERIVED_AT_FREEZE],
        "expectation_today": _sha("NUI/board_expected.json"),
        "reproducibility": reproducibility(),
        "status": {
            "programs": counts,
            "opcodes": opcode_counts,
            "print_ladder": {p: {"expected": values[p], "board": ladder[p]} for p in
                             sorted(ladder, key=int)},
            "stop_probes": stop["counts"],
            "loader_cases": {k: loader[k] for k in
                             ("inputs", "rejected", "accepted", "findings", "not_run")},
        },
        "discrepancies": {
            "measured_mismatch": [
                {"id": "print_large_values_in_p2", "items": mismatch_programs,
                 "evidence": PARITY_OF_RECORD, "off": "OFF-PRINT-SILICON"},
                {"id": "print_ladder_in_p4", "items": [f"2^{p}" for p in failing],
                 "first": f"2^{failing[0]}" if failing else None,
                 "wrong_outputs": len(wrong),
                 "distinct_wrong_outputs": len(set(wrong)),
                 "evidence": PRINT_RUNS[0], "off": "OFF-PRINT-SILICON"},
                {"id": "print_behind_a_stop_in_p5", "items": wire_yes,
                 "evidence": STOP_RUN,
                 "off": "Instruksi sesudah berhenti ikut menulis register",
                 "note": ("the board differs from the interpreter, which stops before "
                          "the PRINT; the simulated RTL gives the same yes")},
            ],
            "known_semantic_difference": [
                {"id": "counter_programs", "items": counter, "evidence": PARITY_OF_RECORD,
                 "note": "the interpreter counts instructions, silicon counts clocks"},
            ],
            "unknown_not_observable": [
                {"id": "register_and_ram_after_a_stop", "items": unseen, "evidence": STOP_RUN,
                 "note": "no port of the board carries a GPR or a data-RAM word"},
                {"id": "rtl_record_window", "items": windows, "evidence": STOP_RUN,
                 "note": ("the RTL record closes when halted rises and the board's wire "
                          "does not, so these differences from it are unknown")},
                {"id": "opcodes_with_mixed_evidence", "items": mixed,
                 "evidence": "NUI/parity_model.json"},
                {"id": "opcodes_no_sent_program_executes", "items": unexercised,
                 "evidence": "NUI/parity_model.json"},
                {"id": "programs_not_sent", "items": not_sent, "evidence": PARITY_OF_RECORD},
            ],
            "known_tooling_discrepancy": _tooling(),
        },
    }


def verify(committed: dict[str, Any] | None = None) -> list[str]:
    """What the records say today against what the freeze wrote down -- the
    parts the freeze is held to, HELD. Paths that differ are returned."""
    committed = committed if committed is not None else json.loads(
        MODEL.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(build()))
    return _diff({k: committed[k] for k in HELD}, {k: fresh[k] for k in HELD})


def _short(sha: str) -> str:
    return f"`{sha[:12]}…`"


def page(model: dict[str, Any]) -> str:
    """NUI/LAYER4.md, drawn from the model only; the headings are the only
    words not taken from it."""
    s, d = model["status"], model["discrepancies"]
    row = lambda c: " / ".join(f"{k} {c[k]}" for k in ("PARITY", "MISMATCH", "UNKNOWN"))  # noqa: E731
    out = ["# Lapis 4 dibekukan — laporan selisih final", "",
           f"Dihasilkan `{model['generated_by']}` dari rekaman yang di-commit, untuk tag "
           f"`{model['tag']}`. Tidak ada eksperimen yang dijalankan untuknya dan tidak "
           "ada ekspektasi yang digeser; yang ditulis tangan hanya judulnya.", "",
           "Lapis 4 dibekukan bukan karena semuanya hijau, melainkan karena tiap warna "
           "punya sumber dan alasan yang bisa diaudit: **PARITY** bukti cocok, "
           "**MISMATCH** bukti papan berbeda, **UNKNOWN** bukti belum cukup atau tidak "
           "bisa diamati.", "",
           "## Status", "", "| | PARITY / MISMATCH / UNKNOWN |", "|---|---|",
           f"| program, korpus P2 | {row(s['programs'])} |",
           f"| opcode, kolom perangkat keras P3 | {row(s['opcodes'])} |",
           f"| probe HALT/RET, P5 | {row(s['stop_probes'])} |", "",
           "| tangga PRINT, P4 | diharapkan | lari 1 | lari 2 | lari 3 |",
           "|---|---|---|---|---|"]
    for p, v in s["print_ladder"].items():
        out.append(f"| 2^{p} | `{v['expected']}` | " + " | ".join(f"`{b}`" for b in v["board"])
                   + " |")
    lc = s["loader_cases"]
    out += ["", f"Loader, P6: {lc['inputs']} kasus di papan, {lc['rejected']} ditolak, "
            f"{lc['accepted']} diterima, **{lc['findings']} temuan**; {lc['not_run']} kasus "
            "hanya di Python dan simulasi.", "",
            "## Selisih terukur", ""]
    for e in d["measured_mismatch"]:
        extra = ""
        if e["id"] == "print_ladder_in_p4":
            extra = (f" — batas pertama {e['first']}, {e['distinct_wrong_outputs']} dari "
                     f"{e['wrong_outputs']} keluaran salah berbeda satu sama lain")
        out.append(f"- `{e['id']}`: " + ", ".join(f"`{i}`" for i in e["items"]) + extra
                   + f" ({e['off']}; `{e['evidence']}`)")
    out += ["", "## Beda semantik yang diketahui", ""]
    for e in d["known_semantic_difference"]:
        out.append(f"- `{e['id']}`: " + ", ".join(f"`{i}`" for i in e["items"])
                   + f" — {e['note']} (`{e['evidence']}`)")
    out += ["", "## UNKNOWN / tidak teramati", ""]
    for e in d["unknown_not_observable"]:
        items = ", ".join(f"`{i}`" for i in e["items"])
        note = f" — {e['note']}" if e.get("note") else ""
        out.append(f"- `{e['id']}` ({len(e['items'])}): {items}{note}")
    out += ["", "## Selisih alat yang diketahui — bukan selisih perangkat keras", ""]
    for e in d["known_tooling_discrepancy"]:
        count = (f"{e['count']} dari {e['of']} tangkapan, {e['records']} rekaman"
                 if "of" in e else str(e["count"]))
        measured = f"; {e['measured']}" if e.get("measured") else ""
        out.append(f"- `{e['id']}` ({count}): {e['what']}{measured}. Dicatat sebagai: "
                   f"{e['kept_as']} (`{e['evidence']}`)")
    out += ["", "## Bukti yang dibekukan", "", "| langkah | berkas | byte | sha256 |",
            "|---|---|---:|---|"]
    for e in model["evidence"]:
        out.append(f"| {e['phase']} | `{e['path']}` | {e['bytes']} | {_short(e['sha256'])} |")
    out += ["", "Turunan pada saat freeze — dibangun dari rekaman, dicatat untuk tag, dan "
            "boleh dibangun ulang sesudahnya:", ""]
    out += [f"- `{e['path']}` {_short(e['sha256'])}" for e in model["derived_at_freeze"]]
    out += ["", f"Sidik jari bitstream {_short(model['bitstream_sha256'])}, dicatat sendiri "
            "oleh rekaman berikut:", ""]
    out += [f"- `{p}`: {'sama' if ok else 'BERBEDA'}"
            for p, ok in model["bitstream_carried_by"].items()]
    out += ["", "Rekaman burn-in P0 dan lab loader P6 tidak membawa sidik jarinya sendiri; "
            "yang pertama diukur dari berkasnya pada P0, yang kedua menyebut berkasnya.", "",
            "## Reproduksi", "",
            f"Ekspektasi beku hari ini {_short(model['expectation_today'])}. Tiap laporan "
            "papan dihitung ulang dari rekamannya dengan kode dan ekspektasi hari ini:", "",
            "| rekaman | ekspektasi saat itu | vonis sama | berbeda di |", "|---|---|---|---|"]
    for r in model["reproducibility"]:
        where = ", ".join(f"`{p}`" for p in r["differs_at"]) or "—"
        out.append(f"| `{r['record']}` | {_short(r['expected_sha256'])} | "
                   f"{'ya' if r['verdicts_reproduce'] else 'TIDAK'} | {where} |")
    out += ["", "Satu-satunya selisih adalah alasan pengecualian program yang tidak pernah "
            "dikirim ke papan, yang langkahnya bergeser saat P6 membekukan ulang "
            "ekspektasinya. Laporan P2 tidak ditulis ulang: isinya perbandingan yang "
            "benar-benar dilakukan pada harinya.", "",
            "## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.layer4_freeze --verify",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.parity_model --verify", "```"]
    return "\n".join(out) + "\n"


def write() -> Path:
    fresh = json.loads(json.dumps(build()))
    if MODEL.exists():
        committed = json.loads(MODEL.read_text(encoding="utf-8"))
        model = {**committed, **{k: fresh[k] for k in HELD}}
    else:
        model = fresh
    MODEL.write_text(json.dumps(model, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    PAGE.write_text(page(model), encoding="utf-8")
    return MODEL


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--write"]:
        print(f"model: {write().relative_to(ROOT)}, page: {PAGE.relative_to(ROOT)}")
        return 0
    problems = verify()
    print("\n".join(problems) if problems else "layer 4 freeze reproduced exactly")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
