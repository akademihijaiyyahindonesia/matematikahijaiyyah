"""Layer 2, the relations between program units.

Layer 1's graph joins FILES. This one joins the things inside them, and only
where the language itself makes the join explicit:

    HASM      a CALL names a label; the label is defined in the program or in
              a file it .includes. Resolved by name, the way the assembler
              resolves it.
    Verilog   an instance names a module; the module is defined in exactly
              one file under rtl/. Resolved by name.

Python function-to-function edges are NOT built, for the reason layer 1 gave:
which `run` a call to `run` means is not in the text, and guessing would be
the first inference in a layer built to hold none. program_summary lists the
names a function calls, as written, and says they are unresolved.

-- what fails to resolve is a finding, not noise -------------------------
A CALL whose label is nowhere, or an instance of a module no file defines,
is reported by name. Some are expected -- the Gowin primitives (rPLL, OSER10,
ELVDS_OBUF...) are the vendor's, not this repository's -- and those are
listed as external rather than silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .program_index import programs

#: Primitives a vendor flow provides -- Gowin, Xilinx, and the sky130 SRAM
#: macro. Not defined in rtl/ and not expected to be; anything else that fails
#: to resolve is reported. MMCME2_BASE was missing from the first version and
#: came back as the one unresolved instance: a Xilinx clock manager, in the
#: Xilinx wrapper, which is exactly where it belongs.
VENDOR = {"rPLL", "OSER10", "ELVDS_OBUF", "TLVDS_OBUF", "CLKDIV", "DHCEN",
          "IBUF", "OBUF", "IOBUF", "GSR", "BUFG", "PLLVR", "Gowin_rPLL",
          "Gowin_CLKDIV", "MMCME2_BASE", "sky130_sram_1kbyte_1rw1r_32x256_8"}


@dataclass(frozen=True)
class Link:
    source: str      # the unit that names
    target: str      # the unit named
    via: str         # "CALL label" / "instance u_x"
    line: int | None


@lru_cache(maxsize=1)
def hasm_labels() -> dict[str, dict[str, tuple[str, int]]]:
    """program path -> {label: (file defining it, line)}, includes followed."""
    found = programs()
    own = {path: {name: (path, line) for name, line in unit.labels}
           for path, unit in found.hasm.items()}
    out: dict[str, dict[str, tuple[str, int]]] = {}
    for path, unit in found.hasm.items():
        table = dict(own[path])
        stack = list(unit.includes)
        seen: set[str] = set()
        while stack:
            name = stack.pop()
            inc = f"rtl/programs/{name}"
            if inc in seen or inc not in own:
                continue
            seen.add(inc)
            for label, where in own[inc].items():
                table.setdefault(label, where)
            stack += list(found.hasm[inc].includes)
        out[path] = table
    return out


def hasm_calls(path: str) -> tuple[list[Link], list[tuple[str, int]]]:
    """(resolved calls, unresolved (label, line))."""
    unit = programs().hasm[path]
    labels = hasm_labels()[path]
    links, missing = [], []
    for ins in unit.instructions:
        if ins.mnemonic != "CALL" or not ins.operands:
            continue
        label = ins.operands[0]
        if label in labels:
            where, _ = labels[label]
            links.append(Link(path, f"{where}:{label}", f"CALL {label}", ins.line))
        else:
            missing.append((label, ins.line))
    return links, missing


@lru_cache(maxsize=1)
def module_homes() -> dict[str, list[str]]:
    """module name -> every file that defines it."""
    homes: dict[str, list[str]] = {}
    for key, unit in programs().verilog.items():
        homes.setdefault(unit.name, []).append(key.split("::")[0])
    return homes


def verilog_instances(key: str) -> tuple[list[Link], list[str], list[str]]:
    """(resolved, vendor, unresolved) for one module."""
    unit = programs().verilog[key]
    homes = module_homes()
    links, vendor, missing = [], [], []
    for module, instance in unit.instances:
        if module in homes:
            # A module name with two homes -- hcpu_dataram for the FPGA and for
            # the sky130 SRAM macro, hcpu_top as RTL and as a synthesised
            # netlist -- is chosen by the BUILD FLOW, not by the text. Linking
            # to the first file found would be a guess, so every home is
            # linked and the via says so.
            many = len(homes[module]) > 1
            for home in homes[module]:
                via = f"instance {instance}" + (" (one of several homes)" if many else "")
                links.append(Link(key, f"{home}::{module}", via, None))
        elif module in VENDOR:
            vendor.append(module)
        else:
            missing.append(module)
    return links, vendor, missing


def unresolved() -> dict[str, list[str]]:
    """Every join the language makes that this repository does not answer."""
    out: dict[str, list[str]] = {"hasm": [], "verilog": []}
    for path in programs().hasm:
        _, no_label = hasm_calls(path)
        out["hasm"] += [f"{path}:{line} CALL {label}" for label, line in no_label]
    for key in programs().verilog:
        _, _, no_module = verilog_instances(key)
        out["verilog"] += [f"{key} instantiates {m}" for m in no_module]
    return out


def main() -> int:
    found = programs()
    calls = sum(len(hasm_calls(p)[0]) for p in found.hasm)
    inst = sum(len(verilog_instances(k)[0]) for k in found.verilog)
    vendor = sum(len(verilog_instances(k)[1]) for k in found.verilog)
    missing = unresolved()
    print(f"HASM calls resolved       {calls}")
    print(f"Verilog instances resolved {inst}, vendor primitives {vendor}")
    print(f"unresolved: {len(missing['hasm'])} HASM, {len(missing['verilog'])} Verilog")
    for item in missing["hasm"] + missing["verilog"]:
        print(f"  {item}")
    dupes = {m: f for m, f in module_homes().items() if len(f) > 1}
    if dupes:
        print(f"modules defined in more than one file: {len(dupes)}")
        for module, files in sorted(dupes.items())[:10]:
            print(f"  {module}: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
