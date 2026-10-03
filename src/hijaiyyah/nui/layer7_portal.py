"""Layer 7, ISOLATE_FAULT: which fault the Portal 8888 slot has, and nothing sent to it.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_portal <adapter serial> [<portal_board_*.txt>]

The owner's decision of 3 October 2026 on the recovery proposal at the end of
7.4, NUI/LAYER7.md, opened two rows and no more: reading the board's identity
over JTAG, and ISOLATE_FAULT. Writing to the board's UART and reconfiguring it
stay DENIED, so this module sends the board no byte and loads it nothing. It
classifies from three sources that already exist:

    the host's adapter listing        is the board's USB adapter there
    openFPGALoader --detect           does the FPGA answer its IDCODE
    a recorded run's raw reply bytes  did the Portal answer, and did it seal right

and gives one of four faults, in that order, or none:

    ADAPTER_ABSENT        no adapter with the given serial number is listed
    BOARD_NOT_DETECTED    the adapter is there, the FPGA does not answer
    BOARD_SILENT          a recorded run stops short: a reply never came
    SEAL_MISMATCH         a recorded run answers, and the checker refuses it

The one command it runs is DETECT_ARGV, exactly: no bitstream file ever follows
it. The recorded run is judged by portal8888/ref/portal_uart.py, the checker
the bench and the board script use, so a fault here is the same verdict.

What it does not say. A board that is detected and was never asked is UNKNOWN,
not silent: asking is a UART write. A recorded run older than the freshness
limit says what the board did then, not what it does now, and stops as STALE.
A run with captured frames (--pcap) is not rechecked here: its frames are not
in the record. And `may_send` is false in every report -- isolating means the
caller stops sending, and nothing here could send anyway.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import layer5, layer7
from .repository_index import ROOT

#: The two 7.4 categories this module needs, by their names in the contract.
DETECT = "Pembacaan identitas papan lewat JTAG (`openFPGALoader --detect`)"
ISOLATE = "Isolasi kesalahan slot Portal 8888 (`ISOLATE_FAULT`)"
#: The only command. A bitstream file after it would be the DENIED row.
DETECT_ARGV = ("openFPGALoader", "--detect", "-b", "tangnano20k")
#: What --detect prints for the Tang Nano 20K's FPGA.
MODEL = "GW2A(R)-18(C)"
ADAPTER_ABSENT, BOARD_NOT_DETECTED = "ADAPTER_ABSENT", "BOARD_NOT_DETECTED"
BOARD_SILENT, SEAL_MISMATCH = "BOARD_SILENT", "SEAL_MISMATCH"
FAULTS = (ADAPTER_ABSENT, BOARD_NOT_DETECTED, BOARD_SILENT, SEAL_MISMATCH)
ISOLATED, NO_FAULT = "FAULT ISOLATED", "NO FAULT"
PROTOCOL = ROOT / "portal8888" / "ref" / "portal_uart.py"
RUN_NAME = re.compile(r"portal_board_(\d{8}T\d{6}Z)\.txt")
#: The uncertainty portal8888/scripts/portal8888_uart_test.py provisions by default.
UNCERT_NS = 50_000_000


def protocol() -> Any:
    """portal8888/ref/portal_uart.py, the one encoder and checker of the slot."""
    ref = str(PROTOCOL.parent)
    if ref not in sys.path:
        sys.path.insert(0, ref)
    return importlib.import_module("portal_uart")


def detect(run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """`openFPGALoader --detect`: the IDCODE and the model it names, or why not."""
    out: dict[str, Any] = {"argv": list(DETECT_ARGV), "returncode": None, "idcode": None,
                           "model": None}
    try:
        done = run(list(DETECT_ARGV), capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as why:
        return {**out, "why": f"{type(why).__name__}: {why}"}
    text = (done.stdout or "") + (done.stderr or "")
    idcode = re.search(r"idcode\s+(0x[0-9a-fA-F]+)", text)
    model = re.search(r"^\s*model\s+(\S+)\s*$", text, flags=re.M)
    return {**out, "returncode": done.returncode,
            "output_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "idcode": idcode.group(1) if idcode else None,
            "model": model.group(1) if model else None}


def read_run(path: Path, now: datetime | None = None,
             uncert_ns: int = UNCERT_NS) -> dict[str, Any]:
    """One recorded scenario run, judged again from its raw reply bytes."""
    named = RUN_NAME.fullmatch(path.name)
    if named is None or not path.is_file():
        return {"path": str(path), "verdict": layer7.UNKNOWN,
                "why": "not a recorded run: portal_board_<UTC>.txt, as the board script writes"}
    at = datetime.strptime(named.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    raw = path.read_bytes()
    out: dict[str, Any] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                           "observed_at": at.isoformat(),
                           **layer5.freshness(at.isoformat(), now)}
    if out["freshness"] != "current":
        return {**out, "verdict": layer7.STALE,
                "why": "the run says what the board did then, not what it does now"}
    u = protocol()
    steps = u.scenario(False, int(at.timestamp()), uncert_ns)
    lines = [line.split() for line in raw.decode("ascii", "replace").splitlines() if line]
    if len(lines) > len(steps):
        return {**out, "verdict": layer7.UNKNOWN,
                "why": f"{len(lines)} commands for a scenario of {len(steps)}: a run with "
                       "captured frames is not rechecked here"}
    replies = [bytes.fromhex(x[1]) if len(x) > 1 else b"" for x in lines]
    for c, step in enumerate(steps):
        rep = replies[c] if c < len(replies) else b""
        want = u.REPLY.get(chr(rep[0])) if rep else None
        if want is None or len(rep) < want:
            return {**out, "verdict": BOARD_SILENT, "command": c,
                    "why": f"command {c} ({step['what']}): "
                           + ("no reply" if not rep else f"{len(rep)} bytes of a reply")}
    bad, count = u.check(steps, replies)
    if bad:
        return {**out, "verdict": SEAL_MISMATCH, "mismatches": len(bad), "why": bad[0]}
    return {**out, "verdict": NO_FAULT, "counts": count}


def isolate(serial_number: str, ports: list[dict[str, Any]], run_path: Path | None = None,
            now: datetime | None = None, contract: Path | None = None,
            detect_run: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    """The fault of one Portal slot, from the first source that shows one."""
    table = layer7.authorizations(contract)
    authorization = {name: table.get(name) or "unlisted" for name in (ISOLATE, DETECT)}
    report: dict[str, Any] = {
        "action": ISOLATE, "authorization": authorization,
        "target": {"serial_number": serial_number}, "detect": None, "run": None,
        "fault": None, "condition": None,
        "may_send": False, "may_send_why": "writing to the board's UART is DENIED in 7.4"}

    def close(decision: str, why: str, **more: Any) -> dict[str, Any]:
        return {**report, **more, "decision": decision, "why": why}

    if set(authorization.values()) != {"AUTHORIZED"}:
        return close(layer7.STOP, "7.4 does not authorize both rows: fail-closed",
                     condition=layer7.UNAUTHORIZED)
    mine = sorted(str(p.get("device")) for p in ports
                  if p.get("serial_number") == serial_number)
    report["target"]["ports"] = mine
    if not mine:
        return close(ISOLATED, f"no listed adapter has serial number {serial_number}",
                     fault=ADAPTER_ABSENT)
    report["detect"] = found = detect(detect_run)
    if found["returncode"] != 0 or found["model"] is None:
        return close(ISOLATED, "the adapter is listed and the FPGA gave no IDCODE",
                     fault=BOARD_NOT_DETECTED)
    if found["model"] != MODEL:
        return close(layer7.STOP, f"detected `{found['model']}`, not {MODEL}: another device",
                     condition=layer7.AMBIGUOUS)
    if run_path is None:
        return close(layer7.STOP, "the board is detected and was never asked: whether the "
                                  "Portal answers is not observable without a UART write",
                     condition=layer7.UNKNOWN)
    report["run"] = run = read_run(run_path, now)
    if run["verdict"] in (BOARD_SILENT, SEAL_MISMATCH):
        return close(ISOLATED, run["why"], fault=run["verdict"])
    if run["verdict"] == NO_FAULT:
        return close(NO_FAULT, "the adapter, the FPGA and the recorded run show no fault")
    return close(layer7.STOP, run["why"], condition=run["verdict"])


def listed() -> list[dict[str, Any]]:
    """The host's serial adapters, enumerated without opening a port."""
    from serial.tools import list_ports  # pyserial; only a real host needs it

    return [{"device": p.device, "serial_number": p.serial_number, "vid": p.vid, "pid": p.pid}
            for p in list_ports.comports()]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in (1, 2):
        print((__doc__ or "").split("\n\n")[1])
        return 2
    report = isolate(args[0], listed(), Path(args[1]) if len(args) == 2 else None)
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0 if report["decision"] == NO_FAULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
