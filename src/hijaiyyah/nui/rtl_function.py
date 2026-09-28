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

The third module, hcpu_uart_tx, is the first held to a bench that is not its
own. The owner named rtl/tb/tb_hcpu_top.v its oracle and limited what may be
claimed to what that bench makes the transmitter do. Measured, that is its
reset and its idle: the bench runs no PRINT and no EMITS. Every rule that
sends a bit is written here, branch for branch, and named not covered in the
spec -- not claimed because the top-level bench passes through the module.

The fourth, hcpu_dataram, has no bench of its own, and none is made. The
owner named rtl/tb/tb_parity.v over the Lapis 4 corpus its oracle: every
program, run the way parity_model runs it, with the probe beside the
harness. sram_mock.py models another device -- the sky130 macro -- and is
not its oracle.

The fifth is a program, rtl/programs/loader.hasm, held to both of its
benches, each measured on its own. The RTL carries no PC past decode, so the
loader is stepped at its MMIO reads: where it is, its registers and the write
pointer are all observable there, and everything between two reads -- its
register writes, its stores, the instruction-memory writes, ERET -- is
compared in program order.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from . import hardware, parity_model
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


# -- hcpu_mmio, as a function ------------------------------------------------------------

RX_KEYS = ("rx_meta", "rx_sync", "state", "count", "index", "shifter", "rx_data", "rx_valid",
           "rx_frame_err")
TRAP_SELS = (0x8, 0x9, 0xA, 0xB, 0xC, 0xD)       # hcpu_pkg.vh, REG_TRAP_VECTOR .. REG_TRAP_MODE
PERIPH_WINDOW = 0xFE0                             # hcpu_pkg.vh
MASK32 = 0xFFFF_FFFF


def mmio_reset() -> State:
    """rtl/hcpu_mmio.v's own registers at reset (lines 150-154, 188-190, 238-239,
    270-276, 330-333), its receiver's (hcpu_uart_rx), and its timer's
    (hcpu_timer.v lines 32-34)."""
    own = {"rx_held": 0, "rx_ready": 0, "rx_held_err": 0, "rx_overrun": 0, "mem_base": 0,
           "mem_limit": 0xFFF, "imem_waddr": 0, "sd_sector": 0, "sd_index": 0, "sd_div": 0,
           "sd_start": 0, "sd_op": 0, "sd_soft_rst": 0, "periph_rdata": 0, "periph_sel": 0,
           "sd_data_sel": 0}
    rx = {f"u_rx.{k}": v for k, v in uart_rx_reset().items()}
    return {**own, **rx, "u_timer.counter": 0, "u_timer.compare": MASK32, "u_timer.expired": 0}


def _decode(addr: int) -> tuple[bool, bool, bool, int]:
    """Lines 123-126: one comparator, and addr[4] for the block."""
    periph = addr >= PERIPH_WINDOW
    return periph, periph and bool(addr >> 4 & 1), periph and not addr >> 4 & 1, addr & 0xF


def mmio_step(s: State, inp: dict[str, Any], p: dict[str, int]) -> tuple[State, list[str]]:
    """One rising clock edge of hcpu_mmio: every register it holds, its
    receiver's and its timer's, from the bus request and the world's inputs.
    The card controller, the data RAM and the trap unit are outside: what
    they hand in is an input here, never predicted."""
    if not inp["rst_n"]:
        return mmio_reset(), ["reset"]
    n, fired = dict(s), ["decode"]
    re_, we_, addr, wdata = inp["re"], inp["we"], inp["addr"], inp["wdata"]
    periph, core, sd, sel = _decode(addr)
    # the receiver -- the function already held to its own bench
    rx = {k: s[f"u_rx.{k}"] for k in RX_KEYS}
    rx_next, rx_fired = uart_rx_step(rx, inp["uart_rx_in"], 1, p)
    n.update({f"u_rx.{k}": v for k, v in rx_next.items()})
    fired += [f"u_rx.{f}" for f in rx_fired]
    # one byte of holding, and the overrun flag -- lines 156-164
    if rx["rx_valid"]:
        n["rx_held"], n["rx_held_err"], n["rx_ready"] = rx["rx_data"], rx["rx_frame_err"], 1
        fired.append("rx_hold")
        if s["rx_ready"]:
            n["rx_overrun"] = 1
            fired.append("rx_overrun_set")
    elif re_ and core and sel == 0x0:
        n["rx_ready"], n["rx_overrun"] = 0, 0
        fired.append("rx_read_clear")
    # the timer -- hcpu_timer.v lines 36-45, written through lines 172-179
    n["u_timer.counter"] = (s["u_timer.counter"] + 1) & MASK32
    fired.append("timer_count")
    if we_ and core and sel == 0x5:
        n["u_timer.compare"], n["u_timer.expired"] = wdata, 0
        fired.append("timer_compare_write")
    elif we_ and core and sel == 0x6:
        n["u_timer.expired"] = 0
        fired.append("timer_clear")
    elif s["u_timer.counter"] == s["u_timer.compare"]:
        n["u_timer.expired"] = 1
        fired.append("timer_expire")
    # the protection window -- lines 184-193
    if we_ and core and sel == 0xE:
        n["mem_base"] = wdata & 0xFFF
        fired.append("mem_base_write")
    if we_ and core and sel == 0xF:
        n["mem_limit"] = wdata & 0xFFF
        fired.append("mem_limit_write")
    # the instruction memory write port -- lines 228-245
    if we_ and core and sel == 0x3:
        n["imem_waddr"] = wdata & 0xFFF
        fired.append("imem_addr_write")
    elif we_ and core and sel == 0x7:
        n["imem_waddr"] = (s["imem_waddr"] + 1) & 0xFFF
        fired.append("imem_data_advance")
    # the card's registers -- lines 259-296
    n["sd_start"], n["sd_soft_rst"] = 0, 0
    if we_ and sd and sel == 0x0:
        n["sd_start"], n["sd_op"] = 1, wdata & 0x3
        fired.append("sd_cmd_write")
    if we_ and sd and sel == 0x2:
        n["sd_sector"] = wdata
        fired.append("sd_sector_write")
    if we_ and sd and sel == 0x4:
        n["sd_div"] = wdata >> 2 & 0x3
        if wdata & 1:
            n["sd_index"] = 0
        if wdata & 2:
            n["sd_soft_rst"] = 1
        fired.append("sd_control_write")
    elif sd and sel == 0x3 and (we_ or re_):
        n["sd_index"] = (s["sd_index"] + 1) & 0x7F
        fired.append("sd_data_advance")
    # the registered read path, updated every cycle from addr -- lines 329-373
    n["periph_sel"] = int(bool(re_ and periph))
    n["sd_data_sel"] = int(bool(re_ and sd and sel == 0x3))
    value: Any
    if sd:
        status = (inp["sd_err_code"] << 4 | inp["sd_card_ready"] << 3 | inp["sd_err"] << 2
                  | inp["sd_ok"] << 1 | inp["sd_busy"])
        value, rule = {0x1: (status, "read_sd_status"), 0x2: (s["sd_sector"], "read_sd_sector"),
                       0x4: (s["sd_div"] << 2, "read_sd_control")}.get(sel, (0, "read_sd_other"))
    elif sel in TRAP_SELS:
        value, rule = inp["trap_reg_rdata"], "read_trap"
    else:
        value, rule = {
            0x0: (s["rx_held"], "read_rx_data"),
            0x1: (s["rx_overrun"] << 2 | s["rx_held_err"] << 1 | s["rx_ready"], "read_rx_status"),
            0x2: (inp["uart_tx_busy"], "read_tx_status"),
            0x3: (s["imem_waddr"], "read_imem_addr"),
            0x4: (s["u_timer.counter"], "read_counter"),
            0x5: (s["u_timer.compare"], "read_compare"),
            0x6: (s["u_timer.expired"], "read_timer_status"),
            0xE: (s["mem_base"], "read_mem_base"),
            0xF: (s["mem_limit"], "read_mem_limit"),
        }.get(sel, (0, "read_other"))
    n["periph_rdata"] = value
    fired.append(rule)
    return n, fired


def mmio_outputs(s: State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    """What the module drives combinationally at a moment, from its registers
    and the bus as it stands -- lines 128-131, 212-214, 220-221, 227, 235, 376."""
    re_, we_, addr, wdata = inp["re"], inp["we"], inp["addr"], inp["wdata"]
    periph, core, _, sel = _decode(addr)
    held = inp["sd_buf_rdata"] if s["sd_data_sel"] else s["periph_rdata"]
    return {"rdata": held if s["periph_sel"] else inp["ram_rdata"],
            "ram_re": int(bool(re_ and not periph)), "ram_we": int(bool(we_ and not periph)),
            "ram_addr": addr, "ram_wdata": wdata,
            "trap_reg_we": int(bool(we_ and core and sel in TRAP_SELS)), "trap_reg_sel": sel,
            "trap_reg_wdata": wdata, "src_timer": s["u_timer.expired"],
            "src_uart_rx": s["rx_ready"], "imem_we": int(bool(we_ and core and sel == 0x7)),
            "imem_wdata": wdata}


# -- hcpu_uart_tx, as a function ---------------------------------------------------------


def uart_tx_parameters(clk_hz: int, baud: int) -> dict[str, int]:
    """rtl/hcpu_uart_tx.v lines 23-24."""
    per_bit = clk_hz // baud
    return {"CLKS_PER_BIT": per_bit, "CNT_W": math.ceil(math.log2(per_bit + 1))}


def uart_tx_reset() -> State:
    """Lines 40-45: idle, and the line high."""
    return {"state": IDLE, "clk_cnt": 0, "bit_idx": 0, "tx_shift": 0, "tx_out": 1}


def uart_tx_step(s: State, inp: dict[str, Any], p: dict[str, int]) -> tuple[State, list[str]]:
    """One rising clock edge of hcpu_uart_tx, branch for branch (lines 39-95).
    Under tb_hcpu_top.v only reset and idle_wait ever run; the other branches
    are written here and named not covered in the spec, not claimed."""
    if not inp["rst_n"]:
        return uart_tx_reset(), ["reset"]
    n, last, mask = dict(s), p["CLKS_PER_BIT"] - 1, (1 << p["CNT_W"]) - 1
    count, state = s["clk_cnt"], s["state"]
    if state == IDLE:
        n["tx_out"] = 1
        if not inp["tx_start"]:
            return n, ["idle_wait"]
        n["tx_shift"], n["state"], n["clk_cnt"] = inp["tx_data"], START, 0
        return n, ["idle_start"]
    if state == START:
        n["tx_out"] = 0
        if count != last:
            n["clk_cnt"] = (count + 1) & mask
            return n, ["start_count"]
        n["clk_cnt"], n["bit_idx"], n["state"] = 0, 0, DATA
        return n, ["start_end"]
    if state == DATA:
        n["tx_out"] = s["tx_shift"] >> s["bit_idx"] & 1
        if count != last:
            n["clk_cnt"] = (count + 1) & mask
            return n, ["data_count"]
        n["clk_cnt"] = 0
        if s["bit_idx"] != 7:
            n["bit_idx"] = s["bit_idx"] + 1
            return n, ["data_next"]
        n["state"] = STOP
        return n, ["data_last"]
    if state == STOP:
        n["tx_out"] = 1
        if count != last:
            n["clk_cnt"] = (count + 1) & mask
            return n, ["stop_count"]
        n["clk_cnt"], n["state"] = 0, IDLE
        return n, ["stop_end"]
    n["state"] = IDLE
    return n, ["default"]


def uart_tx_outputs(s: State, inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    """Line 37, and the pin: hcpu_top.v wires tx_out straight to uart_tx (line 713)."""
    return {"tx_busy": int(s["state"] != IDLE), "uart_tx": s["tx_out"]}


# -- hcpu_dataram, as a function ---------------------------------------------------------


def dataram_reset() -> dict[str, Any]:
    """rtl/hcpu_dataram.v lines 36-37 and 55-58: every word zero -- the
    initial block, simulation only -- and rdata_r with no reset at all, so x
    until the first read. mem holds only the words written through the port."""
    return {"mem": {}, "rdata": "x"}


def dataram_step(s: dict[str, Any], inp: dict[str, Any],
                 p: dict[str, int]) -> tuple[dict[str, Any], list[str]]:
    """One rising clock edge of hcpu_dataram (lines 43-48). One port, one
    addr: a read and a write in the same edge are the same word, and both
    right-hand sides see it as it was before the edge."""
    re_, we_, addr = inp["re"] == 1, inp["we"] == 1, inp["addr"]
    n, fired = {"mem": s["mem"], "rdata": s["rdata"]}, []
    if we_:
        n["mem"] = {**s["mem"], addr: inp["wdata"]}
        fired.append("write")
    if not re_:
        fired.append("hold")
        return n, fired
    n["rdata"] = s["mem"].get(addr, 0)
    fired.append("read_first" if we_ else "read")
    if addr not in s["mem"]:
        fired.append("initial_zero")
    return n, fired


def dataram_outputs(s: dict[str, Any], inp: dict[str, Any], p: dict[str, int]) -> dict[str, Any]:
    """Line 50: the port is the register."""
    return {"rdata": s["rdata"]}


# -- rtl/programs/loader.hasm, as a function ---------------------------------------------

RX_DATA, RX_STATUS, IMEM_ADDR, IMEM_DATA, TRAP_EPC, TRAP_MODE = (
    0xFF0, 0xFF1, 0xFF3, 0xFF7, 0xFF9, 0xFFD)      # loader.hasm's own operands


def loader_reset() -> dict[str, Any]:
    """The machine out of reset: every GPR zero (hcpu_regfile.v), the write
    pointer zero (hcpu_mmio.v line 239), and the loader at its first word."""
    return {"at": "start", **{f"R{r}": 0 for r in range(1, 8)}, "waddr": 0}


def loader_step(s: dict[str, Any], value: Any,
                p: dict[str, int]) -> tuple[dict[str, Any], list[list[Any]], list[str]]:
    """From one MMIO read boundary to the next, branch for branch from
    rtl/programs/loader.hasm: the value the hardware returned for this
    boundary's read, and what the loader does with it -- every GPR it writes,
    every MMIO store, the instruction-memory writes hcpu_mmio makes of them,
    and ERET -- until it asks for the next read. The write pointer is
    hcpu_mmio's (lines 228-244); the loader only relies on it."""
    n, events, fired = dict(s), [], []

    def gpr(r: int, v: int) -> None:
        n[f"R{r}"] = v & MASK32
        events.append(["gpr", r, n[f"R{r}"]])

    def store(addr: int, v: int) -> None:
        events.append(["write", addr, v])
        if addr == IMEM_ADDR:
            n["waddr"] = v & 0xFFF
            fired.append("imem_addr_write")
        elif addr == IMEM_DATA:
            events.append(["imem", n["waddr"], v])
            n["waddr"] = (n["waddr"] + 1) & 0xFFF
            fired.append("imem_data_advance")

    def words(rule_more: str, rule_done: str) -> None:
        if n["R6"] != 0:                                   # words: CMPI R6, 0; JEQ done
            gpr(3, 0)
            gpr(4, 4)
            n["at"] = "w_status"
            fired.append(rule_more)
        else:                                              # done:
            gpr(7, 64)
            store(TRAP_EPC, n["R7"])
            gpr(7, 2)
            store(TRAP_MODE, n["R7"])
            events.append(["eret"])
            n["at"] = "done"
            fired.append(rule_done)

    at = s["at"]
    phase = at.split("_")[0]
    if at == "start":
        gpr(5, 0)
        gpr(3, 0)
        gpr(4, 4)
        n["at"] = "cnt_status"
        fired.append("start")
    elif at.endswith("_status"):
        gpr(1, value)
        ready = n["R1"] != 0                               # CMPI R1, 0; JEQ
        n["at"] = f"{phase}_data" if ready else at
        fired.append(("count" if phase == "cnt" else "word") + ("_ready" if ready else "_spin"))
    elif at.endswith("_data"):
        gpr(2, value)
        gpr(3, s["R3"] << 8)
        gpr(3, n["R3"] | n["R2"])
        gpr(4, s["R4"] - 1)
        if n["R4"] != 0:                                   # CMPI R4, 0; JNE
            n["at"] = f"{phase}_status"
            fired.append("count_byte" if phase == "cnt" else "word_byte")
        elif phase == "cnt":
            gpr(6, n["R3"])                                # MOV R6, R3 -- N
            gpr(7, 64)
            store(IMEM_ADDR, n["R7"])
            words("count_last_byte", "count_empty")
        else:
            store(IMEM_DATA, n["R3"])
            gpr(6, n["R6"] - 1)                            # then JMP words: the loop
            words("word_stored", "last_word")
    return n, events, fired


# -- the drivers: how each module's trace is read into its function -------------------------


def _uart_inputs(rows: list[dict[str, Any]], t: int) -> tuple[Any, ...]:
    return rows[t + 1]["rx_in"], rows[t + 1]["rst_n"]


def _mmio_inputs(rows: list[dict[str, Any]], t: int) -> tuple[Any, ...]:
    """The rows are struck at the end of each rising edge's timestep, so row
    t+1 holds the bus and the line exactly as edge t+1 took them -- however
    the bench timed them (measured, input_timing). What the modules outside
    hand in is registered in them, so edge t+1 takes what row t shows."""
    now, nxt = rows[t], rows[t + 1]
    return ({**{k: nxt[k] for k in ("rst_n", "re", "we", "addr", "wdata", "uart_tx_busy")},
             **{k: now[k] for k in ("sd_busy", "sd_ok", "sd_err", "sd_card_ready",
                                    "sd_err_code", "trap_reg_rdata")},
             "uart_rx_in": nxt["line"]},)


def _line_timing(rows: list[dict[str, Any]], line: str, meta: str) -> dict[str, int]:
    """At each edge where the bench changed the line, which value the first
    synchroniser flop took."""
    changed = [t for t in range(len(rows) - 1)
               if rows[t + 1]["rst_n"] and rows[t + 1][line] != rows[t][line]]
    return {"line_changes": len(changed),
            "captured_new": sum(1 for t in changed if rows[t + 1][meta] == rows[t + 1][line]),
            "captured_old": sum(1 for t in changed if rows[t + 1][meta] == rows[t][line])}


def _uart_observe(states: list[State], rows: list[dict[str, Any]], p: dict[str, int],
                  m: dict[str, Any]) -> dict[str, Any]:
    frames = [(s["rx_data"], bool(s["rx_frame_err"])) for s in states[1:] if s["rx_valid"]]
    return {"frames": [f[0] for f in frames], "frame_errors": [f[1] for f in frames]}


def _mmio_observe(states: list[State], rows: list[dict[str, Any]], p: dict[str, int],
                  m: dict[str, Any]) -> dict[str, Any]:
    """What the bench looks at, predicted: the word each bus read returns one
    cycle later, and whether a RAM write ever went out while the address was
    in the peripheral window."""
    outs = [mmio_outputs(s, r, p) for s, r in zip(states, rows, strict=True)]
    reads = [[rows[t]["addr"], outs[t]["rdata"]] for t in range(len(rows)) if rows[t]["re"]]
    window = sum(1 for t, o in enumerate(outs)
                 if rows[t]["rst_n"] and o["ram_we"] and rows[t]["addr"] >= 0xFF0)
    return {"reads": reads, "ram_writes_in_window": window}


def _tx_inputs(rows: list[dict[str, Any]], t: int) -> tuple[Any, ...]:
    """rst_n as edge t+1 took it, from row t+1. tx_start and tx_data are
    registered in hcpu_top's print state machine, so edge t+1 takes what row t
    shows -- the MMIO rule for what a module outside hands in."""
    return ({"rst_n": rows[t + 1]["rst_n"], "tx_start": rows[t]["tx_start"],
             "tx_data": rows[t]["tx_data"]},)


def _start_timing(rows: list[dict[str, Any]]) -> dict[str, int]:
    """At each edge where tx_start changed while the transmitter sat idle,
    whether it took the new value or the one the row before showed."""
    changed = [t for t in range(len(rows) - 1)
               if rows[t + 1]["rst_n"] and rows[t]["state"] == IDLE
               and rows[t + 1]["tx_start"] != rows[t]["tx_start"]]

    def took(t: int, row: dict[str, Any]) -> bool:
        return bool(rows[t + 1]["state"] == START) == bool(row["tx_start"])

    return {"line_changes": len(changed),
            "captured_new": sum(1 for t in changed if took(t, rows[t + 1])),
            "captured_old": sum(1 for t in changed if took(t, rows[t]))}


# The owner's list for the transmitter -- idle, start bit, data bits, stop
# bit, bit timing, busy and ready -- as predicates on one row of the RTL's trace.
TX_SEEN: dict[str, Callable[[dict[str, Any]], bool]] = {
    "reset": lambda r: not r["rst_n"],
    "idle": lambda r: bool(r["rst_n"]) and r["state"] == IDLE,
    "start_bit": lambda r: r["state"] == START,
    "data_bits": lambda r: r["state"] == DATA,
    "stop_bit": lambda r: r["state"] == STOP,
    "counter_moving": lambda r: r["clk_cnt"] != 0,
    "busy": lambda r: r["tx_busy"] == 1,
    "ready": lambda r: r["tx_busy"] == 0,
    "tx_start": lambda r: r["tx_start"] == 1,
    "line_low": lambda r: r["uart_tx"] == 0,
}


def _tx_observe(states: list[State], rows: list[dict[str, Any]], p: dict[str, int],
                m: dict[str, Any]) -> dict[str, Any]:
    """The bytes the function starts to send, from its own trajectory, and how
    many edges of the RTL's trace show each behaviour the owner named."""
    started = [b["tx_shift"] for a, b in itertools.pairwise(states)
               if a["state"] == IDLE and b["state"] == START]
    return {"tx_started": started,
            "seen": {k: sum(1 for r in rows if f(r)) for k, f in TX_SEEN.items()}}


DRIVERS: dict[str, dict[str, Any]] = {
    "hcpu_uart_rx": {"parameters": uart_rx_parameters, "reset": uart_rx_reset,
                     "step": uart_rx_step, "inputs": _uart_inputs,
                     "timing": lambda rows: _line_timing(rows, "rx_in", "rx_meta"),
                     "observe": _uart_observe},
    "hcpu_mmio": {"parameters": uart_rx_parameters, "reset": mmio_reset, "step": mmio_step,
                  "inputs": _mmio_inputs, "outputs": mmio_outputs,
                  "timing": lambda rows: _line_timing(rows, "line", "u_rx.rx_meta"),
                  "observe": _mmio_observe},
    "hcpu_uart_tx": {"parameters": uart_tx_parameters, "reset": uart_tx_reset,
                     "step": uart_tx_step, "inputs": _tx_inputs, "outputs": uart_tx_outputs,
                     "timing": _start_timing, "observe": _tx_observe},
}


# -- the RTL's own trace, under its own bench --------------------------------------------


def _signals(m: dict[str, Any]) -> list[tuple[str, str]]:
    """(key, hierarchical name) of everything the probe prints."""
    top, inst = m["top"], f"{m['top']}.{m['instance']}"
    if "probe" in m:
        return [(sig["key"], f"{top}.{sig['path']}") for sig in m["probe"]["signals"]]
    return [("rst_n", f"{top}.{m['stimulus']['rst_n']}"),
            ("rx_in", f"{top}.{m['stimulus']['rx_in']}"),
            *[(k, f"{inst}.{k}") for k in [*m["state"], *m["outputs"]]]]


def _probe(m: dict[str, Any]) -> str:
    """A module that sits beside the bench and prints the bench's stimulus and
    the design's registers once a cycle -- nothing is driven."""
    names = [path for _, path in _signals(m)]
    fmt = " ".join(["%0d"] * len(names))
    clock = f"{m['top']}.{m['clock']}"
    if "probe" in m:
        return (f"module rtl_function_probe;\n  always @({m['probe']['edge']} {clock})\n"
                f"    $strobe(\"T {fmt}\", {', '.join(names)});\nendmodule\n")
    return (f"module rtl_function_probe;\n  always @(negedge {clock})\n"
            f"    $display(\"T {fmt}\", {', '.join(names)});\nendmodule\n")


def _value(text: str) -> Any:
    """A printed value: an integer, or the simulator's x or z kept as text --
    equal only to itself."""
    return int(text) if text.lstrip("-").isdigit() else text


def rtl_trace(m: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """The bench and the RTL, compiled unchanged with the probe beside them,
    and what they print."""
    root = root or ROOT
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("Icarus Verilog is required to run the bench")
    # A pattern is expanded the way rtl/tb/Makefile expands RTL_SRC, not
    # copied into a hand-kept list.
    sources = [str(f) for pattern in m.get("compile", [m["rtl"]])
               for f in (sorted(root.glob(pattern)) if "*" in pattern else [root / pattern])]
    include = ["-I", str(root / m["include"])] if "include" in m else []
    work = Path(tempfile.mkdtemp())
    try:
        (work / "probe.v").write_text(_probe(m), encoding="utf-8")
        compiled = subprocess.run(
            ["iverilog", "-g2012", *include, "-o", str(work / "sim"), str(root / m["bench"]),
             *sources, str(work / "probe.v")],
            capture_output=True, text=True, timeout=300)
        if compiled.returncode != 0:
            raise RuntimeError(f"iverilog failed:\n{compiled.stderr}")
        # Run where the bench's own $dumpfile lands with the rest of the work.
        ran = subprocess.run(["vvp", "-n", str(work / "sim")], capture_output=True, text=True,
                             timeout=300, cwd=work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    keys = [k for k, _ in _signals(m)]
    rows = [dict(zip(keys, map(_value, ln.split()[1:]), strict=True))
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
    if "CLK_HZ" not in got:
        return got      # a module with no clock-derived parameters: the values as read
    params: dict[str, int] = DRIVERS[m["name"]]["parameters"](got["CLK_HZ"], got["BAUD"])
    return params | {"CLK_HZ": got["CLK_HZ"], "BAUD": got["BAUD"]}


def rules(m: dict[str, Any]) -> list[dict[str, Any]]:
    """A module's rules, and those of each submodule it runs through a
    function already held to its own bench -- named there, not copied."""
    own = [{**r, "file": r.get("file", m["rtl"])} for r in m["rules"]]
    for sub in m.get("submodules", []):
        other = next(x for x in load()["modules"] if x["name"] == sub["module"])
        own += [{**r, "id": f"{sub['instance']}.{r['id']}", "file": other["rtl"]}
                for r in other["rules"] if r["id"] != "reset"]
    return own


# -- hcpu_dataram's oracle: tb_parity.v over the Lapis 4 corpus -----------------------------

RAM_TAKEN = ("re", "we", "addr", "wdata", "rdata_before", "word_before")
RAM_AFTER = ("rdata", "port", "word_after", "re_after", "we_after", "addr_after", "wdata_after")
RAM_INPUTS = ("re", "we", "addr", "wdata")


def _dataram_probe(m: dict[str, Any], p: dict[str, int]) -> str:
    """Beside the harness, reading only. In each rising edge's active region
    -- before any non-blocking update lands -- it holds what the edge takes:
    the port, rdata_r, and the word at the address. At the end of that
    timestep it prints them with what the edge left: rdata_r, the port, the
    same word, and the inputs the next edge will see. At $finish it prints
    every non-zero word of mem. Icarus takes only plain signals in $strobe,
    so the word after the edge reaches it through a net."""
    inst, clock = f"{m['top']}.{m['instance']}", f"{m['top']}.{m['clock']}"
    xlen, aw = p["XLEN"], p["DATA_ADDR_W"]
    fmt = " ".join(["%0d"] * (len(RAM_TAKEN) + len(RAM_AFTER)))
    return (
        "module rtl_function_probe;\n"
        f"  reg t_re, t_we;\n  reg [{aw - 1}:0] t_addr;\n"
        f"  reg [{xlen - 1}:0] t_wdata, t_rdata, t_word;\n  integer k;\n"
        f"  wire [{xlen - 1}:0] word_after = {inst}.mem[t_addr];\n"
        f"  always @(posedge {clock}) begin\n"
        f"    t_re = {inst}.re; t_we = {inst}.we; t_addr = {inst}.addr;"
        f" t_wdata = {inst}.wdata;\n"
        f"    t_rdata = {inst}.rdata_r; t_word = {inst}.mem[{inst}.addr];\n"
        f"    $strobe(\"P {fmt}\", t_re, t_we, t_addr, t_wdata, t_rdata, t_word,\n"
        f"            {inst}.rdata_r, {inst}.rdata, word_after,\n"
        f"            {inst}.re, {inst}.we, {inst}.addr, {inst}.wdata);\n"
        "  end\n"
        f"  final for (k = 0; k < {p['DATA_DEPTH']}; k = k + 1)\n"
        f"    if ({inst}.mem[k] !== 0) $display(\"M %0d %0d\", k, {inst}.mem[k]);\n"
        "endmodule\n")


def dataram_runs(m: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    """Every program of the Lapis 4 corpus through tb_parity.v with +TRACE,
    as parity_model.run_rtl runs it, and the probe beside the harness. The
    corpus and each run's cycle budget are read from parity_model, not
    copied; the harness and the RTL are compiled unchanged."""
    root = root or ROOT
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("Icarus Verilog is required to run the harness")
    progs = parity_model.corpus()
    budgets = {p.name: parity_model.cycle_budget(parity_model.run_interpreter(p))
               for p in progs}
    sources = [str(f) for pattern in m["compile"] for f in sorted(root.glob(pattern))]
    work = Path(tempfile.mkdtemp())
    try:
        (work / "probe.v").write_text(_dataram_probe(m, _parameters(m, root)),
                                      encoding="utf-8")
        compiled = subprocess.run(
            ["iverilog", "-g2012", "-I", str(root / m["include"]), "-o", str(work / "sim"),
             str(root / m["bench"]), *sources, str(work / "probe.v")],
            capture_output=True, text=True, timeout=600)
        if compiled.returncode != 0:
            raise RuntimeError(f"iverilog failed:\n{compiled.stderr}")

        def one(i: int) -> dict[str, Any]:
            prog = progs[i]
            hexfile = work / f"program{i}.hex"
            hexfile.write_text("".join(f"{w:08X}\n" for w in prog.words), encoding="utf-8")
            ran = subprocess.run(["vvp", "-n", str(work / "sim"), f"+PROGRAM={hexfile}",
                                  f"+CYCLES={budgets[prog.name]}", "+TRACE"],
                                 capture_output=True, text=True, timeout=1800, cwd=work)
            rows, harness, final, said = [], [], {}, []
            for ln in ran.stdout.splitlines():
                f = ln.split()
                if f[:1] == ["P"]:
                    rows.append(dict(zip((*RAM_TAKEN, *RAM_AFTER), map(_value, f[1:]),
                                         strict=True)))
                elif f[:1] == ["M"]:
                    final[int(f[1])] = _value(f[2])
                elif f[:1] == ["T"] and f[2:3] == ["RAM"]:
                    harness.append([int(f[3], 16), int(f[4], 16)])
                elif f[:1] != ["T"]:
                    said.append(ln)
            if ran.returncode != 0 or not rows:
                raise RuntimeError(f"{prog.name}: the harness printed no probe row, "
                                   f"exit {ran.returncode}:\n{ran.stdout[-1500:]}{ran.stderr}")
            return {"program": prog.name, "rows": rows, "harness": harness, "final": final,
                    "said": said}

        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
            return list(pool.map(one, range(len(progs))))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _dataram_trace_sha(runs: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for run in runs:
        digest.update(f"{run['program']}\n".encode())
        for r in run["rows"]:
            digest.update((" ".join(str(r[k]) for k in (*RAM_TAKEN, *RAM_AFTER)) + "\n")
                          .encode())
        digest.update(f"{sorted(run['final'].items())}\n".encode())
    return digest.hexdigest()


def _lapis4(names: list[str]) -> dict[str, Any]:
    """What the frozen Lapis 4 model says of the programs that touch the RAM,
    and the board's LOAD and STORE rows -- read from it, not re-run."""
    frozen = json.loads(parity_model.MODEL.read_text(encoding="utf-8"))
    verdicts = {n: {"status": frozen["programs"][n]["status"],
                    "first_divergence": (frozen["programs"][n]["first_divergence"] or {})
                    .get("kind")} for n in names}
    board = {op: {k: frozen["board_corpus"]["opcodes"][op][k]
                  for k in ("board", "programs", "parity", "mismatch", "unknown")}
             for op in ("LOAD", "STORE")}
    return {"lapis4": verdicts, "board": board}


def dataram_compare(m: dict[str, Any], runs: list[dict[str, Any]], root: Path | None = None,
                    step: Callable[..., tuple[dict[str, Any], list[str]]] | None = None,
                    outputs: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    """F1-F4 for the data RAM, over every run of the corpus.

    One step starts from the RTL's own state as the edge found it: rdata_r,
    and the word at the address -- the only word an edge can touch. Open loop
    starts from reset and takes the inputs alone; at every edge its rdata and
    its word at the address must be the RTL's, and at the end of each run its
    whole memory must be the dump. Rules are counted on the open loop, the
    only pass that knows which words were ever written."""
    root = root or ROOT
    params = _parameters(m, root)
    step = step or dataram_step
    outputs = outputs or dataram_outputs
    one_step: list[str] = []
    open_loop: list[str] = []
    output_bad: list[str] = []
    harness_bad: list[str] = []
    fired_count = {r["id"]: 0 for r in rules(m)}
    timing = {"line_changes": 0, "captured_new": 0, "captured_old": 0}
    touching: list[str] = []
    cycles = 0
    for run in runs:
        name, rows = run["program"], run["rows"]
        cycles += len(rows)
        s, writes, used = dataram_reset(), [], False
        for t, r in enumerate(rows):
            inp = {k: r[k] for k in RAM_INPUTS}
            own = {"mem": {r["addr"]: r["word_before"]}, "rdata": r["rdata_before"]}
            got, _ = step(own, inp, params)
            if got["rdata"] != r["rdata"] or got["mem"][r["addr"]] != r["word_after"]:
                one_step.append(f"{name}:{t}")
            before = s["mem"].get(r["addr"], 0)
            s, fired = step(s, inp, params)
            for f in fired:
                fired_count[f] = fired_count.get(f, 0) + 1
            if (before != r["word_before"] or s["rdata"] != r["rdata"]
                    or s["mem"].get(r["addr"], 0) != r["word_after"]):
                open_loop.append(f"{name}:{t}")
            if outputs(s, inp, params)["rdata"] != r["port"]:
                output_bad.append(f"{name}:{t}")
            if inp["we"] == 1:
                writes.append([r["addr"], r["wdata"]])
            used = used or inp["we"] == 1 or inp["re"] == 1
            if t:
                was = tuple(rows[t - 1][k] for k in RAM_INPUTS)
                shown = tuple(rows[t - 1][f"{k}_after"] for k in RAM_INPUTS)
                now = tuple(r[k] for k in RAM_INPUTS)
                if now != was:
                    timing["line_changes"] += 1
                    timing["captured_old"] += now == shown
                    timing["captured_new"] += now != shown and now == tuple(
                        r[f"{k}_after"] for k in RAM_INPUTS)
        if {a: v for a, v in s["mem"].items() if v != 0} != run["final"]:
            open_loop.append(f"{name}:final")
        if writes != run["harness"]:
            harness_bad.append(name)
        if used:
            touching.append(name)
    halted = [run["program"] for run in runs
              if any(re.match(m["bench_verdict"]["pattern"], ln) for ln in run["said"])]
    return {"parameters": params, "cycles": cycles, "runs": len(runs),
            "ram_programs": touching, "input_timing": timing,
            "one_step_mismatches": one_step, "open_loop_mismatches": open_loop,
            "output_mismatches": output_bad, "harness_trace_mismatches": harness_bad,
            "harness_ram_writes": sum(len(run["harness"]) for run in runs),
            **_lapis4(touching),
            "bench_said": f"{len(halted)} of {len(runs)} runs reached the harness's final "
                          "block (HALTED=)",
            "bench_pass": len(halted) == len(runs), "rules_fired": fired_count}


DRIVERS["hcpu_dataram"] = {"runs": dataram_runs, "compare": dataram_compare,
                           "trace_sha": _dataram_trace_sha}


# -- loader.hasm's oracle: tb_gowin_loader.v and tb_gowin_loader_nui.v -----------------------

LOADER_PROBE = (
    ("rst_n", "rst_n"), ("re", "u_mmio.re"), ("we", "u_mmio.we"), ("addr", "u_mmio.addr"),
    ("wdata", "u_mmio.wdata"), ("rdata", "u_mmio.rdata"), ("gpr_we", "u_regfile.gpr_we"),
    ("gpr_waddr", "u_regfile.gpr_waddr"), ("gpr_wdata", "u_regfile.gpr_wdata"),
    ("eret", "trap_is_eret_w"), ("waddr", "u_mmio.imem_waddr"), ("mode", "u_trap.mode"),
    ("epc", "u_trap.epc"))
LOADER_BOARD = (("imem_we", "imem_we"), ("imem_waddr", "imem_waddr"),
                ("imem_wdata", "imem_wdata"), ("fetch", "imem_addr"))


def _loader_probe(top: str) -> str:
    """Beside the bench, reading only: at each rising edge, in its active
    region, what the edge takes -- the MMIO bus, the register file's write
    port, the instruction-memory write port, ERET, and the fetch address."""
    core, board = f"{top}.u_board.u_hcpu", f"{top}.u_board"
    names = [f"{core}.{p}" for _, p in LOADER_PROBE] + [f"{board}.{p}" for _, p in LOADER_BOARD]
    fmt = " ".join(["%0d"] * len(names))
    return (f"module rtl_function_probe;\n  always @(posedge {core}.clk)\n"
            f"    $display(\"L {fmt}\", {', '.join(names)});\nendmodule\n")


def loader_runs(m: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    """Each bench, built the way rtl/tb/Makefile builds it: loader.hex from
    asm2hex.py, the payload from send_program.py one byte a line, the bench
    with the board wrapper and every hcpu_*.v -- and the probe beside it."""
    root = root or ROOT
    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        raise RuntimeError("Icarus Verilog is required to run the benches")
    keys = [k for k, _ in (*LOADER_PROBE, *LOADER_BOARD)]
    sources = [str(f) for pattern in m["compile"] for f in sorted(root.glob(pattern))]
    runs = []
    for b in m["benches"]:
        work = Path(tempfile.mkdtemp())
        try:
            loader_hex = subprocess.run(
                [sys.executable, str(root / "rtl/scripts/asm2hex.py"), str(root / m["rtl"])],
                capture_output=True, text=True, check=True).stdout
            (work / "loader.hex").write_text(loader_hex, encoding="utf-8")
            wire = subprocess.run(
                [sys.executable, str(root / "rtl/scripts/send_program.py"),
                 str(root / b["payload"])], capture_output=True, check=True).stdout
            (work / b["payload_file"]).write_text("".join(f"{x:02x}\n" for x in wire),
                                                  encoding="utf-8")
            (work / "probe.v").write_text(_loader_probe(b["top"]), encoding="utf-8")
            compiled = subprocess.run(
                ["iverilog", "-g2012", "-I", str(root / m["include"]), "-o", str(work / "sim"),
                 str(root / b["bench"]), *sources, str(work / "probe.v")],
                capture_output=True, text=True, timeout=600)
            if compiled.returncode != 0:
                raise RuntimeError(f"iverilog failed:\n{compiled.stderr}")
            ran = subprocess.run(["vvp", "-n", str(work / "sim")], capture_output=True,
                                 text=True, timeout=3600, cwd=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        rows = [dict(zip(keys, map(_value, ln.split()[1:]), strict=True))
                for ln in ran.stdout.splitlines() if ln.startswith("L ")]
        if ran.returncode != 0 or not rows:
            raise RuntimeError(f"{b['bench']}: no probe row, exit {ran.returncode}:\n"
                               f"{ran.stdout[-1500:]}{ran.stderr}")
        runs.append({"bench": b["bench"], "rows": rows,
                     "said": [ln for ln in ran.stdout.splitlines() if not ln.startswith("L ")]})
    return runs


def loader_boundaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The RTL's own trace cut at its MMIO reads, in program order: within a
    cycle the register write belongs to the oldest instruction (writeback),
    the bus to the next (memory), ERET to the youngest (execute). Each
    boundary carries the loader's state as the RTL holds it -- where it is,
    read off the address it reads and whether IMEM_ADDR has been written;
    R1-R7 from the register writes so far; the write pointer -- and the value
    the read returned, one cycle after it was asked. The trace ends at ERET."""
    regs = dict.fromkeys(range(1, 8), 0)
    live = [t for t, r in enumerate(rows) if r["rst_n"] == 1]
    first = live[0]
    bounds = [{"at": "start", "state": {"at": "start", **{f"R{i}": 0 for i in regs},
                                        "waddr": rows[first]["waddr"]}, "cycle": first}]
    segments: list[list[list[Any]]] = [[]]
    words_phase, eret_at, timing = False, None, [0, 0, 0]
    for t in live:
        r = rows[t]
        if r["gpr_we"] == 1:
            regs[r["gpr_waddr"]] = r["gpr_wdata"]
            segments[-1].append(["gpr", r["gpr_waddr"], r["gpr_wdata"]])
        if r["re"] == 1:
            at = ("w" if words_phase else "cnt") + {RX_STATUS: "_status",
                                                    RX_DATA: "_data"}.get(r["addr"], "_other")
            value = rows[t + 1]["rdata"]
            bounds.append({"at": at, "cycle": t, "value": value,
                           "state": {"at": at, **{f"R{i}": v for i, v in regs.items()},
                                     "waddr": r["waddr"]}})
            segments.append([])
            # which rdata the LOAD's own register write carries
            dst = 1 if r["addr"] == RX_STATUS else 2
            wb = next(rows[u]["gpr_wdata"] for u in range(t + 1, len(rows))
                      if rows[u]["gpr_we"] == 1 and rows[u]["gpr_waddr"] == dst)
            timing[0] += 1
            timing[1] += wb == value
            timing[2] += wb == r["rdata"] and wb != value
        if r["we"] == 1:
            segments[-1].append(["write", r["addr"], r["wdata"]])
            words_phase = words_phase or r["addr"] == IMEM_ADDR
        if r["imem_we"] == 1:
            segments[-1].append(["imem", r["imem_waddr"], r["imem_wdata"]])
        if r["eret"] == 1:
            segments[-1].append(["eret"])
            eret_at = t
            bounds.append({"at": "done", "cycle": t,
                           "state": {"at": "done", **{f"R{i}": v for i, v in regs.items()},
                                     "waddr": r["waddr"]}})
            break
    return {"bounds": bounds, "segments": segments, "eret": eret_at,
            "timing": dict(zip(("line_changes", "captured_new", "captured_old"), timing,
                               strict=True))}


def _loader_trace_sha(runs: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for run in runs:
        cut = loader_boundaries(run["rows"])["eret"]
        digest.update(f"{run['bench']}\n".encode())
        for r in run["rows"][:cut + 1]:
            digest.update((" ".join(str(v) for v in r.values()) + "\n").encode())
    return digest.hexdigest()


def loader_compare(m: dict[str, Any], runs: list[dict[str, Any]], root: Path | None = None,
                   step: Callable[..., tuple[dict[str, Any], list[list[Any]], list[str]]]
                   | None = None) -> dict[str, Any]:
    """F1-F4 for the loader, bench by bench, at its MMIO read boundaries.

    One step starts from the RTL's own state at a boundary and the value its
    read returned; the state at the next boundary and the events between must
    be the RTL's. Open loop starts from reset and takes only the values the
    reads returned. Coverage is kept per bench, then as union and
    intersection -- the two benches are not assumed to be one."""
    step = step or loader_step
    one_step: list[str] = []
    open_loop: list[str] = []
    outputs: list[str] = []
    fired_total = {r["id"]: 0 for r in rules(m)}
    per_bench: dict[str, Any] = {}
    timing = {"line_changes": 0, "captured_new": 0, "captured_old": 0}
    cycles, verdicts = 0, 0
    for run, spec_b in zip(runs, m["benches"], strict=True):
        name = run["bench"].rsplit("/", 1)[-1].removesuffix(".v")
        cut = loader_boundaries(run["rows"])
        bounds, segments = cut["bounds"], cut["segments"]
        for k, v in cut["timing"].items():
            timing[k] += v
        cycles += cut["eret"] - bounds[0]["cycle"] + 1
        fired = {r["id"]: 0 for r in rules(m)}
        s, imem = loader_reset(), {}
        for k in range(len(bounds) - 1):
            value = bounds[k].get("value")
            got, events, _ = step(bounds[k]["state"], value, {})
            if got != bounds[k + 1]["state"]:
                one_step.append(f"{name}:{k}")
            if events != segments[k]:
                outputs.append(f"{name}:{k}")
            s, events, rules_now = step(s, value, {})
            for f in rules_now:
                fired[f] += 1
                fired_total[f] += 1
            for e in events:
                if e[0] == "imem":
                    imem[str(e[1])] = e[2]
            if s != bounds[k + 1]["state"] or events != segments[k]:
                open_loop.append(f"{name}:{k}")
        rows = run["rows"]
        entry = 64
        fetched_early = any(rows[t]["fetch"] == entry
                            for t in range(bounds[0]["cycle"], cut["eret"] + 1))
        after = next((t for t in range(cut["eret"] + 1, len(rows))
                      if rows[t]["fetch"] == entry), None)
        verdict = next((ln for ln in run["said"] if re.match(spec_b["verdict"], ln)), None)
        verdicts += verdict is not None
        per_bench[name] = {
            "boundaries": len(bounds), "reads": len(bounds) - 2,
            "rules_fired": fired, "imem_written": imem, "waddr": s["waddr"],
            "entry_fetched_before_eret": fetched_early,
            "entry_fetched_cycles_after_eret": None if after is None else after - cut["eret"],
            "after_eret": {"epc": rows[cut["eret"] + 1]["epc"],
                           "mode": rows[cut["eret"] + 1]["mode"]},
            "bench_said": verdict}
    covered = {n: [r for r, c in b["rules_fired"].items() if c] for n, b in per_bench.items()}
    sets = [set(c) for c in covered.values()]
    order = [r["id"] for r in rules(m)]
    return {"parameters": {}, "cycles": cycles, "runs": len(runs),
            "steps": sum(b["boundaries"] - 1 for b in per_bench.values()), "input_timing": timing,
            "one_step_mismatches": one_step, "open_loop_mismatches": open_loop,
            "output_mismatches": outputs, "benches": per_bench,
            "coverage": {**covered,
                         "union": [r for r in order if r in set.union(*sets)],
                         "intersection": [r for r in order if r in set.intersection(*sets)]},
            "bench_said": f"{verdicts} of {len(runs)} benches print PASS",
            "bench_pass": verdicts == len(runs), "rules_fired": fired_total}


DRIVERS["loader"] = {"runs": loader_runs, "compare": loader_compare,
                     "trace_sha": _loader_trace_sha}


def compare(m: dict[str, Any], trace: dict[str, Any], root: Path | None = None,
            step: Callable[..., tuple[State, list[str]]] | None = None) -> dict[str, Any]:
    """F1-F4 for one module: the function against the RTL's trace."""
    root = root or ROOT
    d = DRIVERS[m["name"]]
    params = _parameters(m, root)
    step = step or d["step"]
    keys = list(m["state"]) if "outputs" in d else [*m["state"], *m["outputs"]]
    rows = trace["rows"]

    def held(row: dict[str, Any]) -> State:
        return {k: row[k] for k in keys}

    one_step: list[int] = []
    fired_count = {r["id"]: 0 for r in rules(m)}
    for t in range(len(rows) - 1):
        got, fired = step(held(rows[t]), *d["inputs"](rows, t), params)
        for f in fired:
            fired_count[f] = fired_count.get(f, 0) + 1
        if got != held(rows[t + 1]):
            one_step.append(t + 1)
    s = d["reset"]()
    states, open_loop = [s], [] if held(rows[0]) == s else [0]
    for t in range(1, len(rows)):
        s, _ = step(s, *d["inputs"](rows, t - 1), params)
        states.append(s)
        if s != held(rows[t]):
            open_loop.append(t)
    verdict = next((ln for ln in trace["said"] if re.match(m["bench_verdict"]["pattern"], ln)),
                   None)
    result: dict[str, Any] = {"parameters": params, "cycles": len(rows),
                              "input_timing": d["timing"](rows),
                              "one_step_mismatches": one_step,
                              "open_loop_mismatches": open_loop}
    if "outputs" in d:
        result["output_mismatches"] = [
            t for t in range(len(rows))
            if d["outputs"](held(rows[t]), rows[t], params) != {k: rows[t][k]
                                                               for k in m["outputs"]}]
    return {**result, **d["observe"](states, rows, params, m),
            "bench_said": verdict if verdict is not None else trace["said"][0],
            "bench_pass": verdict is not None,
            "rules_fired": fired_count}


# -- the model -------------------------------------------------------------------------------


def build(root: Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    spec = load()
    modules = []
    for m in spec["modules"]:
        for r in rules(m):
            length = len((root / r["file"]).read_text(encoding="utf-8").splitlines())
            if max(r["lines"]) > length:
                raise LookupError(f"{m['name']}: rule {r['id']} cites line {max(r['lines'])} "
                                  f"of {r['file']}'s {length}")
        d = DRIVERS[m["name"]]
        if "runs" in d:
            # an oracle that is a corpus of runs, not one bench
            runs = d["runs"](m, root)
            result, trace_sha = d["compare"](m, runs, root), d["trace_sha"](runs)
        else:
            trace = rtl_trace(m, root)
            result = compare(m, trace, root)
            text = "\n".join(" ".join(str(r[k]) for k in r) for r in trace["rows"])
            trace_sha = _sha(text.encode("utf-8"))
        entry = {"name": m["name"], "rtl": m["rtl"],
                 "rtl_sha256": _sha((root / m["rtl"]).read_bytes()),
                 "bench": m["bench"], "bench_sha256": _sha((root / m["bench"]).read_bytes())}
        if "modelled" in m:
            entry["modelled_sha256"] = {f: _sha((root / f).read_bytes()) for f in m["modelled"]}
        if "pinned" in m:
            entry["pinned_sha256"] = {f: _sha((root / f).read_bytes()) for f in m["pinned"]}
        modules.append({
            **entry, "trace_sha256": trace_sha, **result,
            "rules": [{"id": r["id"], **({"file": r["file"]} if r["file"] != m["rtl"] else {}),
                       "lines": r["lines"], "fired": result["rules_fired"][r["id"]]}
                      for r in rules(m)],
            "not_covered": [r["id"] for r in rules(m) if not result["rules_fired"][r["id"]]]})
    tool = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout
    return {"generated_by": "src/hijaiyyah/nui/rtl_function.py",
            "spec": "NUI/spec/rtl_function.json",
            "simulator": tool.splitlines()[0] if tool else None, "modules": modules}


def _expects(m: dict[str, Any], s: dict[str, Any]) -> str | None:
    """F3: what the bench checks, against what the function predicts. None
    when they agree."""
    want = s["bench_expects"]
    if m["name"] == "loader":
        # Each bench checks its own things; both see where the entry was fetched.
        for b in s["benches"]:
            name = b["bench"].rsplit("/", 1)[-1].removesuffix(".v")
            got, exp = m["benches"][name], b["expects"]
            words = {a: got["imem_written"].get(a) for a in exp.get("imem", {})}
            if words != exp.get("imem", {}) or got["waddr"] != exp["waddr"]:
                return f"{name}: predicted words {words} and pointer {got['waddr']}, the bench " \
                       f"wants {exp}"
            if got["entry_fetched_before_eret"] != want["entry_fetched_before_eret"]:
                return f"{name}: the entry was fetched before ERET"
        return None
    if m["name"] == "hcpu_dataram":
        # The harness observes the write side; the frozen Lapis 4 model is
        # the verdict on what reached the port, quoted, not re-judged.
        if m["harness_trace_mismatches"]:
            return f"the harness's RAM trace is not the function's writes in " \
                   f"{m['harness_trace_mismatches']}"
        ram = sorted(n for n, v in m["lapis4"].items() if v["first_divergence"] == "RAM")
        if ram != want["lapis4_ram_divergences"]:
            return f"the frozen Lapis 4 model diverges first at RAM in {ram}, the spec names " \
                   f"{want['lapis4_ram_divergences']}"
        return None
    if m["name"] == "hcpu_uart_tx":
        # The bench reads nothing of the transmitter; an expectation here
        # would be a claim the bench does not make.
        return None if want == {} else f"the bench observes nothing of the transmitter: {want}"
    if m["name"] == "hcpu_uart_rx":
        got = (m["frames"], m["frame_errors"])
        return None if got == (want["frames"], want["frame_errors"]) else f"predicted {got}"
    reads, previous = m["reads"], None
    if len(reads) != len(want["reads"]):
        return f"{len(reads)} reads predicted, the bench makes {len(want['reads'])}"
    for (addr, value), w in zip(reads, want["reads"], strict=True):
        ok = addr == w["addr"] and (
            value == w["equals"] if "equals" in w else
            (value >> w["bit"] & 1) == w["is"] if "bit" in w else
            value > previous if w.get("greater_than_previous") else isinstance(value, int))
        if not ok:
            return f"the read of 0x{addr:03X} returns {value}, the bench wants {w}"
        previous = value
    if m["ram_writes_in_window"] != want["ram_writes_in_window"]:
        return f"{m['ram_writes_in_window']} RAM writes in the peripheral window"
    return None


def check(model: dict[str, Any]) -> list[str]:
    """F1-F5 on a built model, against the spec's expectations of the bench."""
    spec, bad = load(), []
    built = {m["name"]: m for m in model["modules"]}
    for s in spec["modules"]:
        m = built.get(s["name"])
        if m is None:
            bad.append(f"F5 {s['name']}: the model holds no result for it")
            continue
        if m["one_step_mismatches"] or m.get("output_mismatches"):
            bad.append(f"F1 {m['name']}: {len(m['one_step_mismatches'])} transitions and "
                       f"{len(m.get('output_mismatches', []))} outputs differ")
        timing = m["input_timing"]
        takes = s["input_timing"].get("takes", "new")
        other = "old" if takes == "new" else "new"
        if timing[f"captured_{takes}"] != timing["line_changes"] or timing[f"captured_{other}"]:
            bad.append(f"F1 {m['name']}: the input timing the function assumes does not hold: "
                       f"{timing}")
        if m["open_loop_mismatches"]:
            bad.append(f"F2 {m['name']}: the trajectory leaves the RTL's at cycle "
                       f"{m['open_loop_mismatches'][0]}")
        why = _expects(m, s)
        if why or not m["bench_pass"]:
            bad.append(f"F3 {m['name']}: {why or m['bench_said']}")
        if m["not_covered"] != list(s.get("not_covered", {})):
            bad.append(f"F4 {m['name']}: rules the bench never runs are {m['not_covered']}, "
                       f"the spec names {list(s.get('not_covered', {}))}")
        held = {s["rtl"]: m["rtl_sha256"], s["bench"]: m["bench_sha256"],
                **m.get("modelled_sha256", {}), **m.get("pinned_sha256", {})}
        if any(_sha((ROOT / f).read_bytes()) != h for f, h in held.items()):
            bad.append(f"F5 {m['name']}: an RTL or bench file is not the one the model holds")
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
    spec = {m["name"]: m for m in load()["modules"]}
    out = ["# Model RTL sebagai fungsi — Lapis 6", "",
           f"Dihasilkan `{model['generated_by']}` dari `{model['spec']}`. RTL dan bench "
           "dikompilasi apa adanya dengan satu modul probe di sampingnya yang mencetak register "
           "desain sekali tiap siklus; tidak ada port atau baris yang berubah. "
           f"Simulator: {model['simulator']}.", ""]
    for m in model["modules"]:
        s, p = spec[m["name"]], m["parameters"]
        timing = m["input_timing"]
        first = [k for k in ("CLK_HZ", "BAUD") if k in p]
        named = ", ".join(f"{k} {p[k]}" for k in [*first, *(k for k in p if k not in first)])
        out += [f"## `{m['name']}`", "",
                f"`{m['rtl']}` `{m['rtl_sha256'][:12]}…`, bench `{m['bench']}` "
                f"`{m['bench_sha256'][:12]}…`." + (f" {named}." if named else ""), ""]
        if "oracle" in s:
            out += [f"**Oracle.** {s['oracle']}.", ""]
        if "granularity" in s:
            out += [f"**Satu langkah.** {s['granularity']}.", ""]
        if "levels" in s:
            out += ["Tiga level bukti, dan batas masing-masing:", "",
                    *[f"- **{k}** — {v}." for k, v in s["levels"].items()], ""]
        if "modelled_sha256" in m:
            out += ["Ikut dimodelkan: " + ", ".join(f"`{f}` `{h[:12]}…`" for f, h in
                                                   m["modelled_sha256"].items()) + ".", ""]
        if "outside" in s:
            out += ["Di luar model — masuk sebagai input, tidak diprediksi:", ""]
            out += [f"- `{k}` — {v}." for k, v in s["outside"].items()]
            out.append("")
        # A corpus row holds its edge's state before and after, so every row
        # is a step; one bench's rows are states, and the steps fall between.
        steps = m["cycles"] if "runs" in m else m["cycles"] - 1
        out += ["| pemeriksaan | hasil |", "|---|---|"]
        if "steps" in m:
            out += [f"| F1 satu langkah, dari keadaan RTL di tiap batas baca, {m['steps']} langkah "
                    f"| {len(m['one_step_mismatches'])} berbeda |",
                    f"| F1 kejadian di antara dua batas (GPR, MMIO, port IMEM, ERET), "
                    f"{m['steps']} langkah | {len(m['output_mismatches'])} berbeda |",
                    f"| F2 lingkar terbuka dari reset, {m['steps']} langkah, {m['cycles']} siklus "
                    f"sampai ERET | {len(m['open_loop_mismatches'])} berbeda |"]
        else:
            out.append(f"| F1 satu langkah, {steps} transisi | "
                       f"{len(m['one_step_mismatches'])} berbeda |")
        if "output_mismatches" in m and "steps" not in m:
            out.append(f"| F1 keluaran kombinasional, {m['cycles']} siklus | "
                       f"{len(m['output_mismatches'])} berbeda |")
        if "steps" not in m:
            out.append(f"| F2 lingkar terbuka dari reset, {m['cycles']} siklus | "
                       f"{len(m['open_loop_mismatches'])} berbeda |")
        if "frames" in m:
            out.append(f"| F3 frame yang diprediksi | "
                       f"{', '.join(f'0x{b:02X}' for b in m['frames'])}; framing error "
                       f"{m['frame_errors']} |")
        if "reads" in m:
            out.append("| F3 baca yang diprediksi | "
                       + ", ".join(f"0x{a:03X} → {v}" for a, v in m["reads"])
                       + f"; tulis RAM di jendela periferal: {m['ram_writes_in_window']} |")
        if "tx_started" in m:
            out.append("| byte yang mulai dikirim, diprediksi fungsi | "
                       + (", ".join(f"0x{b:02X}" for b in m["tx_started"]) or "tidak ada")
                       + " |")
        if "bench_observes" in s:
            out.append(f"| F3 yang bench amati dari modul ini | {s['bench_observes']} |")
        if "lapis4" in m:
            out += [f"| lari korpus | {m['runs']}, {len(m['ram_programs'])} menyentuh RAM |",
                    f"| F3 jejak tulis RAM harness = tulisan yang fungsi ambil, "
                    f"{m['harness_ram_writes']} tulis | "
                    f"{len(m['harness_trace_mismatches'])} program berbeda |"]
        signal = s["input_timing"].get("signal", "line")
        out += [f"| F3 bench | {m['bench_said']} |",
                f"| waktu input: perubahan {signal}, ditangkap nilai baru, ditangkap nilai lama | "
                f"{timing['line_changes']}, {timing['captured_new']}, {timing['captured_old']} |",
                f"| jejak RTL | `{m['trace_sha256'][:12]}…` |", ""]
        if "seen" in m:
            out += [f"Daftar pemilik, di jejak RTL — {s['seen_why']}.", "",
                    "| perilaku | tepi naik |", "|---|---|",
                    *[f"| {s['seen'][k]} | {v} |" for k, v in m["seen"].items()], ""]
        if "lapis4" in m:
            out += ["Program korpus yang menyentuh RAM, dan vonis model paritas Lapis 4 yang beku "
                    f"atasnya — dikutip, tidak dinilai ulang. {s['bench_expects_why']}.", "",
                    "| program | Lapis 4 | perpisahan pertama |", "|---|---|---|",
                    *[f"| `{n}` | {v['status']} | {v['first_divergence'] or '—'} |"
                      for n, v in m["lapis4"].items()], "",
                    "Bukti papan untuk jalur yang sama, kolom P3 (tingkat program):", "",
                    "| opcode | papan | program | cocok | berbeda | tak bisa diputuskan |",
                    "|---|---|---|---|---|---|",
                    *[f"| `{op}` | {b['board']} | {b['programs']} | {b['parity']} | "
                      f"{b['mismatch']} | {b['unknown']} |" for op, b in m["board"].items()],
                    ""]
        if "coverage" in m:
            out += ["Per bench — kedua bench tidak dianggap satu:", "",
                    "| bench | batas baca | aturan dijalankan | penunjuk tulis akhir "
                    "| alamat masuk diambil sebelum ERET | sesudah ERET: EPC, mode | vonis |",
                    "|---|---|---|---|---|---|---|",
                    *[f"| `{n}` | {b['boundaries']} | {len(m['coverage'][n])} | {b['waddr']} | "
                      f"{'ya' if b['entry_fetched_before_eret'] else 'tidak'} — diambil "
                      f"{b['entry_fetched_cycles_after_eret']} siklus sesudah ERET | "
                      f"{b['after_eret']['epc']}, {b['after_eret']['mode']} | {b['bench_said']} |"
                      for n, b in m["benches"].items()], "",
                    f"Gabungan: {', '.join(m['coverage']['union'])}. Irisan: "
                    f"{', '.join(m['coverage']['intersection'])}.", "",
                    f"{s['bench_expects_why']}.", "",
                    *[f"- `{b['bench']}` juga memeriksa {b['observes_beyond']}."
                      for b in s["benches"]], ""]
        out += ["| aturan | baris RTL | arti | dijalankan bench |", "|---|---|---|---|"]
        means = {r["id"]: r["means"] for r in rules(s)}
        for r in m["rules"]:
            where = ", ".join(map(str, r["lines"]))
            if "file" in r:
                where = f"`{r['file'].rsplit('/', 1)[-1]}` {where}"
            out.append(f"| `{r['id']}` | {where} | {means[r['id']]} | {r['fired']} |")
        uncovered = s.get("not_covered", {})
        out += ["", f"Tidak tercakup bench: {', '.join(m['not_covered']) or 'tidak ada'}."]
        if uncovered:
            out += ["", *[f"- `{k}` — {v}." for k, v in uncovered.items()]]
        if "covered_limits" in s:
            out += ["", f"Batas yang tercakup — {s['covered_limits_why']}:", "",
                    *[f"- `{k}` — {v}." for k, v in s["covered_limits"].items()]]
        out += ["", f"**Waktu input.** {s['input_timing']['rule']}: {s['input_timing']['why']}.",
                ""]
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
