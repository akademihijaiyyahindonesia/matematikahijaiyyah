"""Two board experiments kept apart from the parity corpus: PRINT in silicon, and
what happens to the word behind a stop.

The owner, 22 September 2026: both run as their own experiments rather than
inside the general board parity run, so a PRINT fault cannot be read as a
parity result and a stop fault cannot hide behind PRINT's. Each is a small
program sent the way every board program is -- loader.hasm in the bitstream,
the payload over the wire to address 64 -- and each has its expected answer
written down, from the interpreter and from the simulated RTL, before the
board is asked (NUI/board_expected.json, built by board_parity.py).

-- PRINT in silicon --------------------------------------------------------------
cosmictera-build/OFF.md, OFF-PRINT-SILICON: on the board 2^22 and 2^24 came
back right, 2^23, 2^25 and 2^31 wrong, and 2^26..2^30 were never recorded. The
simulated RTL prints all of them right. The values sent are the owner's list
-- 2^22, 2^23, 2^24, 2^25, 2^26, 2^27, 2^31 -- one PRINT each, and the goal is
the first value where silicon departs from the simulation. Nothing here
proposes a fix: rtl/hcpu_top.v marks the conversion "Re-measure before
changing this", and the fix is the owner's.

-- the word behind a stop ---------------------------------------------------------
cosmictera-build/OFF.md, "Instruksi sesudah berhenti ikut menulis register":
on the RTL the word after HALT, or after a RET that stops the machine as
HC-05, commits once. The owner's four questions, one probe each:

    halt-then-register   does a register change after HALT?
    halt-then-store      does RAM change after HALT?
    ret-then-register    does writeback still happen after a RET fault?
    ret-then-print       does a PRINT still happen after a RET fault?

Three of them already exist as layer 4's stop probes and are read from there,
not copied (R1); the two register probes are new here. halt-then-print, also
layer 4's, is kept beside them: it is the only HALT case the board can show.

The board is seen through its wire and nothing else. A register or a RAM
word written after the machine stops is never printed, so the board cannot
answer the register and store questions; the simulated RTL does, and the
record says which engine answered what rather than filling the gap.
"""
from __future__ import annotations

from typing import Any

from ..hisa.assembler import assemble
from .board_parity import BoardProgram, run_under_loader
from .freeze import LOAD_BASE
from .parity_model import STOP_PROBES, _printed_text

#: The owner's ladder, 22 September 2026.
PRINT_VALUES = [1 << 22, 1 << 23, 1 << 24, 1 << 25, 1 << 26, 1 << 27, 1 << 31]
PRINT_NAME = "print-silicon"

#: What each stop probe asks, and what the board can see of the answer.
STOP_QUESTIONS: dict[str, dict[str, str]] = {
    "stop-probe:halt-then-register": {"question": "does a register change after HALT?",
                                      "board": "not visible: nothing is printed after a stop"},
    "stop-probe:halt-then-store": {"question": "does RAM change after HALT?",
                                   "board": "not visible: nothing is printed after a stop"},
    "stop-probe:ret-then-register": {"question": "does writeback happen after a RET fault?",
                                     "board": "not visible: nothing is printed after a stop"},
    "stop-probe:ret-then-print": {"question": "does a PRINT happen after a RET fault?",
                                  "board": "the wire: a '5' is the answer yes"},
    "stop-probe:halt-then-print": {"question": "does a PRINT happen after HALT?",
                                   "board": "the wire: a '5' is the answer yes"},
}

#: The two probes layer 4 does not have. Each writes R1 = 5, stops, and has one
#: word behind the stop that would make R1 = 7 if it committed.
NEW_STOP_PROBES = {
    "stop-probe:halt-then-register": "        MOVI  R1, 5\n        HALT\n        MOVI  R1, 7\n",
    "stop-probe:ret-then-register": "        MOVI  R1, 5\n        RET\n        MOVI  R1, 7\n"
                                    "        HALT\n",
}
#: Where each probe's answer lives when it is not on the wire.
WATCH = {"stop-probe:halt-then-register": ("gpr", 1),
         "stop-probe:ret-then-register": ("gpr", 1),
         "stop-probe:halt-then-store": ("ram", 0x100)}


def print_source(values: list[int] | None = None) -> str:
    """One register, shifted up to each value in turn, printed each time.
    Every value is a power of two, so SHLI reaches each from the last."""
    values = values or PRINT_VALUES
    lines = ["MOVI  R1, 1"]
    shift = 0
    for v in values:
        k = v.bit_length() - 1
        if v != 1 << k or k < shift:
            raise ValueError(f"{v} is not a larger power of two than the one before")
        if k > shift:
            lines.append(f"SHLI  R1, R1, {k - shift}")
            shift = k
        lines.append("PRINT R1")
    lines.append("HALT")
    return "".join(f"        {line}\n" for line in lines)


def print_programs() -> list[BoardProgram]:
    payload = assemble(print_source(), base=LOAD_BASE)
    run = run_under_loader(PRINT_NAME, payload)
    return [BoardProgram(PRINT_NAME, payload, expected=_printed_text(run.events["TX"]),
                         run=run)]


def stop_sources() -> dict[str, str]:
    """Layer 4's three, read from where they live, and the two new ones."""
    return {**STOP_PROBES, **NEW_STOP_PROBES}


def stop_programs() -> list[BoardProgram]:
    out = []
    for name in STOP_QUESTIONS:
        payload = assemble(stop_sources()[name], base=LOAD_BASE)
        run = run_under_loader(name, payload)
        # Sent even though the interpreter prints nothing: nothing is the
        # answer being tested.
        out.append(BoardProgram(name, payload, expected=_printed_text(run.events["TX"]),
                                run=run))
    return out


def print_table(expected: dict[str, Any], board_text: str | None = None) -> list[dict[str, Any]]:
    """Per value: what Python says, what the interpreter and the simulated RTL
    printed, what the board printed if it has been asked, and whether this is
    the first value the board departs on."""
    entry = expected["programs"][PRINT_NAME]
    interp = entry["interpreter"].split("\n")
    rtl = entry["rtl_at_64"].split("\n")
    # A text that ends in a newline has no line after it: a value the board
    # never sent is None, not an empty line.
    board = board_text.split("\n") if board_text is not None else None
    if board and board[-1] == "":
        board.pop()
    rows, first = [], None
    for i, v in enumerate(PRINT_VALUES):
        got = board[i] if board is not None and i < len(board) else None
        differs = board is not None and got != str(v)
        if differs and first is None:
            first = v
        rows.append({"value": v, "power": v.bit_length() - 1, "python": str(v),
                     "interpreter": interp[i] if i < len(interp) else None,
                     "rtl": rtl[i] if i < len(rtl) else None,
                     "board": got, "first_divergence": differs and first == v})
    return rows


def _ram(events: list[Any], address: int) -> int | str:
    """The last value written to `address`, or 0 if nothing was."""
    values = [e.value for e in events if e.key == address]
    return values[-1] if values else 0


def after_stop(name: str, interp: Any, rtl: Any) -> dict[str, Any]:
    """The location a probe watches, as each engine left it. The interpreter
    stops at the stop; the simulated RTL shows whether the word behind it
    committed."""
    watch = WATCH.get(name)
    if watch is None:
        return {"watch": "wire"}
    kind, where = watch
    if kind == "gpr":
        return {"watch": f"R{where}", "interpreter": interp.final["gpr"][where],
                "rtl": rtl.final["gpr"][where]}
    return {"watch": f"MEM[{where:#05x}]", "interpreter": _ram(interp.events["RAM"], where),
            "rtl": _ram(rtl.events["RAM"], where)}


def stop_table(expected: dict[str, Any], record: dict[str, Any] | None = None
               ) -> list[dict[str, Any]]:
    """Per probe: the owner's question, what the interpreter and the simulated
    RTL answer, and what the board answered where the wire can carry it."""
    rows = []
    for name, question in STOP_QUESTIONS.items():
        exp = expected["programs"][name]
        got = (record or {}).get("programs", {}).get(name, {})
        row: dict[str, Any] = {"probe": name, **question,
                               "interpreter_wire": exp["interpreter"],
                               "rtl_wire": exp["rtl_at_64"],
                               "board_wire": got.get("text")}
        if exp["after_stop"]["watch"] != "wire":
            row.update({"watch": exp["after_stop"]["watch"],
                        "interpreter": exp["after_stop"]["interpreter"],
                        "rtl": exp["after_stop"]["rtl"]})
        rows.append(row)
    return rows
