#!/usr/bin/env python3
"""Summarise yosys `stat` reports: LUT1-4, ALU, DFF*, MUX2_LUT* per module, and the share of the
Tang Nano 20K's GW2AR-18C (20,736 LUT4, 15,552 FF). Synthesis counts, before place and route."""
import os, re, sys
LUT4, FF = 20736, 15552
print(f"{'modul':24s} {'LUT1-4':>7s} {'ALU':>5s} {'DFF':>6s} {'MUX2':>5s}  {'LUT%':>5s} {'DFF%':>5s}")
for path in sys.argv[1:]:
    c = {}
    for n, cell in re.findall(r"^\s+(\d+)\s+(LUT\d|ALU|DFF\w*|MUX2_LUT\d)\s*$", open(path).read(), re.M):
        c[cell] = c.get(cell, 0) + int(n)
    lut = sum(v for k, v in c.items() if k.startswith("LUT"))
    dff = sum(v for k, v in c.items() if k.startswith("DFF"))
    mux = sum(v for k, v in c.items() if k.startswith("MUX2"))
    name = os.path.basename(path)[:-5]
    print(f"{name:24s} {lut:7d} {c.get('ALU', 0):5d} {dff:6d} {mux:5d}  {100*lut/LUT4:5.1f} {100*dff/FF:5.1f}")
