"""The Hijaiyyah Registry: each letter as a mathematical object, and what it is
in HC and in HISA -- read from where each part already lives, none assigned.

    python3 -m hijaiyyah.nui.registry            # the table
    python3 -m hijaiyyah.nui.registry --write    # NUI/hijaiyyah_registry.json

Asked by the owner on 22 September 2026, in the order letter -> operator ->
HC representation -> HISA representation, because a single letter stays a
mathematical object and never becomes a variable name. Every column is read
or measured, and each record says where:

    letter     MASTER_TABLE: the character, its name, its 1-based index and
               its 18-component codex
    operator   two, and both were already in the repository:
                 instruction  OpCode.L_<X>, HREG[0] <- HREG[0] + v(letter) --
                              the letter as a whole instruction
                              (src/hijaiyyah/hisa/opcodes.py). Its ROM address
                              is the one rtl/hcpu_execute.v derives from the
                              opcode, as nui/atom.py already checks
                 face         the letter's 5x5 exomatrix read as a linear map,
                              the object cosmic-codex-jim/ studies: its rank
                              over GF(2), and its (tail, period) over GF(2)
                              and GF(5) from core.exomatrix.matrix_order
    hc         what HC's compiler emits for the bare letter, compiled here,
               and HC's parser refusing the letter as a name -- `let س = 10;`
    hisa       the instruction word, assembled from the letter itself (the
               assembler takes `ج` as an alias for L_JIM), and the HLOAD that
               loads the letter's codex into an H-register

Twenty-eight records, because the Master Table and the opcode slots
0xE0-0xFB hold 28. Nothing here adds a letter, a name or an operator.
"""
from __future__ import annotations

import json
from typing import Any

from ..core.exomatrix import build_exomatrix, gf2_rank, matrix_order
from ..core.master_table import MASTER_TABLE
from ..hisa.assembler import assemble
from ..hisa.opcodes import OpCode
from .atom import ATOMS_BY_CHAR
from .repository_index import ROOT

DB = ROOT / "NUI" / "hijaiyyah_registry.json"
OPCODES = "src/hijaiyyah/hisa/opcodes.py"
Record = dict[str, Any]


def _line(path: str, needle: str) -> str:
    """path:line of the first line holding `needle` -- a source, not a copy."""
    for number, text in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
        if needle in text:
            return f"{path}:{number}"
    raise LookupError(f"{needle!r} is not in {path}")


def build() -> list[Record]:
    from .usr import lower  # the one place HC is compiled for the NUI

    operator = _line(OPCODES, "HREG[0] <- HREG[0] + v(letter)")
    parser = _line("src/hijaiyyah/language/parser.py", '"Expected variable name"')
    out = []
    for entry in MASTER_TABLE.all_entries():
        atom = ATOMS_BY_CHAR[entry.char]
        op = OpCode(atom.opcode)
        face = build_exomatrix(entry.vector)
        gf2 = matrix_order(entry.vector, 2)
        gf5 = matrix_order(entry.vector, 5)
        emitted, _ = lower(f"let h = {entry.char};")
        _, refused = lower(f"let {entry.char} = 10;")
        word = assemble(entry.char)
        out.append({
            "index": entry.index,
            "char": entry.char,
            "name": entry.name,
            "codex": list(entry.vector),
            "operator": {
                "instruction": {"mnemonic": op.name, "opcode": f"{atom.opcode:#04x}",
                                "effect": f"H0 <- H0 + v({entry.char})",
                                "rom_address": atom.rom_address,
                                "source": operator},
                "face": {"rank_gf2": gf2_rank(tuple(tuple(x % 2 for x in row) for row in face)),
                         "gf2": {"tail": gf2[0], "period": gf2[1]},
                         "gf5": {"tail": gf5[0], "period": gf5[1]},
                         "source": "src/hijaiyyah/core/exomatrix.py"},
            },
            "hc": {"literal": entry.char, "compiles_to": emitted[0] if emitted else None,
                   "as_a_name": refused or None,
                   # the compiler emits the HLOAD; the parser refuses the name
                   "source": f"src/hijaiyyah/compiler/codegen.py, {parser}"},
            "hisa": {"letter": entry.char, "word": f"{word[0]:#010x}" if len(word) == 1 else None,
                     "load": f"HLOAD Hn, #{entry.index}",
                     "source": _line(OPCODES, f"L_{entry.name.upper()} ")},
        })
    return out


def write() -> None:
    DB.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load() -> list[Record]:
    data: list[Record] = json.loads(DB.read_text(encoding="utf-8"))
    return data


def by_char(char: str) -> Record | None:
    return next((r for r in load() if r["char"] == char), None)


def main() -> int:
    import sys
    if sys.argv[1:] == ["--write"]:
        write()
        print(f"registry: {DB.relative_to(ROOT)}")
        return 0
    for r in build():
        face, opcode = r["operator"]["face"], r["operator"]["instruction"]["opcode"]
        print(f"{r['index']:>2} {r['char']} {r['name']:<6} {opcode} "
              f"rank {face['rank_gf2']} GF(2) {face['gf2']['period']!s:>4} "
              f"GF(5) {face['gf5']['period']!s:>5}  {r['hc']['compiles_to']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
