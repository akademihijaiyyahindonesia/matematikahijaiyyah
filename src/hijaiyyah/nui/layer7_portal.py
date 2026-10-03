"""Layer 7 on the Portal 8888 slot: isolate its fault, restart it, recover it, and record that.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_portal <adapter serial> [<portal_board_*.txt>]
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_portal --recover \\
        <adapter serial> <port> <portal_board_*.txt> <evidence dir>
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer7_portal --restart \\
        <adapter serial> <port> <portal_board_*.txt> <evidence dir>

The owner's decisions of 3 October 2026 on the recovery proposal at the end of
7.4, NUI/LAYER7.md. The first opened reading the board's identity over JTAG and
ISOLATE_FAULT. The second opened what recovering needs, and no more: loading
the Portal bitstream whose SHA-256 is recorded into SRAM, writing the Portal's
protocol to the UART after that load in the same run, RESTART_PORTAL and
RECOVER_PORTAL, with at most three restarts for one fault.

ISOLATE_FAULT sends the board no byte and loads it nothing. It classifies from
three sources that already exist:

    the host's adapter listing        is the board's USB adapter there
    openFPGALoader --detect           does the FPGA answer its IDCODE
    a recorded run's raw reply bytes  did the Portal answer, and did it seal right

and gives one of four faults, in that order, or none:

    ADAPTER_ABSENT        no adapter with the given serial number is listed
    BOARD_NOT_DETECTED    the adapter is there, the FPGA does not answer
    BOARD_SILENT          a recorded run stops short: a reply never came
    SEAL_MISMATCH         a recorded run answers, and the checker refuses it

The recorded run is judged by portal8888/ref/portal_uart.py, the checker the
bench and the board script use, so a fault here is the same verdict.

RESTART_PORTAL and RECOVER_PORTAL act only on a fault ISOLATE_FAULT found in a
recorded run -- BOARD_SILENT or SEAL_MISMATCH -- and stop without acting on
anything else. A restart is LOAD_ARGV and the bitstream, then the read-only
anchor command: round 0 and a zero ROOT say the Portal is in its first state.
A recovery is a restart, then the board script's scenario -- five keys, lock,
time, frames -- judged by the same checker. Every attempt, the loader's exit
code, the raw reply bytes and the verdict go to an evidence directory outside
the repository (K-11), never into git.

What it does not say. A board that is detected and was never asked is UNKNOWN,
not silent, and is not restarted: no fault was observed. A recorded run older
than the freshness limit stops as STALE. A run with captured frames (--pcap) is
not rechecked here. No byte is written before the loader has exited 0 on the
recorded bitstream in the same run. A recovery starts a new chain: the keys,
PREV, ROOT and anchor before the restart are gone, and the keys it provisions
are the laboratory keys of portal8888/ref/portal_ref.py, which are public. The
flash of the board is never written. And `may_send` is false in every isolate
report -- isolating means the caller stops sending.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import layer5, layer7
from .repository_index import ROOT

#: The two 7.4 categories this module needs, by their names in the contract.
DETECT = "Pembacaan identitas papan lewat JTAG (`openFPGALoader --detect`)"
ISOLATE = "Isolasi kesalahan slot Portal 8888 (`ISOLATE_FAULT`)"
#: The four rows the owner opened for recovering, by their names in the contract.
RECONFIGURE = ("Konfigurasi ulang papan ke SRAM dengan bitstream Portal 8888 yang "
               "SHA-256-nya tercatat")
WRITE_UART = "Penulisan UART protokol Portal 8888 sesudah muat ulang pada lari yang sama"
RESTART = "Mulai ulang slot Portal 8888 (`RESTART_PORTAL`)"
RECOVER = "Pemulihan slot Portal 8888 (`RECOVER_PORTAL`)"
#: The command isolating runs. No bitstream file ever follows it.
DETECT_ARGV = ("openFPGALoader", "--detect", "-b", "tangnano20k")
#: The command a restart runs, the bitstream after it: -m is SRAM, never flash.
LOAD_ARGV = ("openFPGALoader", "-b", "tangnano20k", "-m")
BITSTREAM = ROOT / "portal8888" / "build" / "gowin" / "hijaiyyah_portal8888_gowin_top.fs"
#: Where the SHA-256 of the bitstream that ran on the board is recorded (R1).
EVIDENCE = ROOT / "portal8888" / "sim" / "EVIDENCE.md"
SCRIPT = ROOT / "portal8888" / "scripts" / "portal8888_uart_test.py"
#: Seconds a reply is waited for: the board script's own serial timeout.
TIMEOUT_S = 5
RESTARTED, RECOVERED = "RESTARTED", "RECOVERED"
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


def _short(u: Any, steps: list[dict[str, Any]], replies: list[bytes]) -> tuple[int, str] | None:
    """The first command whose reply never came whole, and what did come."""
    for c in range(len(steps)):
        rep = replies[c] if c < len(replies) else b""
        want = u.REPLY.get(chr(rep[0])) if rep else None
        if want is None or len(rep) < want:
            return c, "no reply" if not rep else f"{len(rep)} bytes of a reply"
    return None


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
    short = _short(u, steps, replies)
    if short is not None:
        return {**out, "verdict": BOARD_SILENT, "command": short[0],
                "why": f"command {short[0]} ({steps[short[0]]['what']}): {short[1]}"}
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
        "may_send": False,
        "may_send_why": "isolating sends nothing; 7.4 allows a UART write only after a "
                        "restart in the same run"}

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


def retry_limit(contract: Path | None = None) -> int:
    """How many restarts one fault may get: the owner's number, read from 7.4 (R1)."""
    text = (contract or layer7.CONTRACT).read_text(encoding="utf-8")
    found = re.search(r"^Batas ulang RESTART_PORTAL untuk satu gangguan: (\d+)\b", text,
                      flags=re.M)
    return int(found.group(1)) if found else 0


def recorded_bitstream() -> str | None:
    """The SHA-256 of the bitstream that ran on the board, as its evidence page records it."""
    found = re.search(r"^bitstream\s.*sha256 ([0-9a-f]{64})\s*$",
                      EVIDENCE.read_text(encoding="utf-8"), flags=re.M)
    return found.group(1) if found else None


def _script() -> Any:
    """portal8888/scripts/portal8888_uart_test.py: its baud rate and its exchange()."""
    spec = importlib.util.spec_from_file_location("portal8888_uart_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _open(device: str) -> Any:
    """The port, refused if another process holds pyserial's lock on it."""
    import serial  # pyserial; only a real port needs it

    return serial.Serial(device, _script().BAUD, timeout=TIMEOUT_S, exclusive=True)


def _files(base: Path) -> dict[str, str]:
    return {str(f.relative_to(base)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(base.rglob("*")) if f.is_file()} if base.is_dir() else {}


def _protected(bitstream: Path) -> dict[str, str | None]:
    paths = [*layer7.PROTECTED, Path(__file__), PROTOCOL, SCRIPT, EVIDENCE, bitstream]
    return {str(f): hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
            for f in paths}


def _answered(base: Path, fault_sha: str) -> tuple[int, str | None]:
    """The restarts already recorded for one fault, and the run that answered it, if any."""
    spent, by = 0, None
    for manifest in sorted(base.glob("*/manifest.json")) if base.is_dir() else []:
        try:
            kept = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if ((kept.get("trigger") or {}).get("run") or {}).get("sha256") != fault_sha:
            continue
        spent += len(kept.get("attempts") or [])
        if kept.get("decision") in (RESTARTED, RECOVERED):
            by = manifest.parent.name
    return spent, by


def recover(serial_number: str, ports: list[dict[str, Any]], device: str, run_path: Path,
            into: Path, action: str = RECOVER, bitstream: Path = BITSTREAM,
            now: datetime | None = None, contract: Path | None = None,
            detect_run: Callable[..., Any] = subprocess.run,
            load_run: Callable[..., Any] = subprocess.run,
            open_port: Callable[[str], Any] | None = None,
            clock: Callable[[], float] = time.time) -> dict[str, Any]:
    """RESTART_PORTAL or RECOVER_PORTAL on one slot whose fault a recorded run shows."""
    table = layer7.authorizations(contract)
    rows = (DETECT, ISOLATE, RECONFIGURE, WRITE_UART, RESTART,
            *((RECOVER,) if action == RECOVER else ()))
    authorization = {name: table.get(name) or "unlisted" for name in rows}
    report: dict[str, Any] = {
        "action": action, "authorization": authorization,
        "target": {"serial_number": serial_number, "device": device}, "trigger": None,
        "bitstream": None, "retry": None, "attempts": [], "evidence": None, "post": None,
        "condition": None, "chain": None}

    def close(decision: str, why: str, **more: Any) -> dict[str, Any]:
        return {**report, **more, "decision": decision, "why": why}

    if action not in (RESTART, RECOVER) or set(authorization.values()) != {"AUTHORIZED"}:
        return close(layer7.STOP, "7.4 does not authorize every row this needs: fail-closed",
                     condition=layer7.UNAUTHORIZED)
    base = Path(into).resolve()
    if base == ROOT or ROOT in base.parents:
        return close(layer7.STOP, f"{base} is inside the repository; evidence lives outside "
                                  "it (K-11)", condition=layer7.UNAUTHORIZED)
    report["trigger"] = seen = isolate(serial_number, ports, run_path, now, contract, detect_run)
    if seen["decision"] != ISOLATED or seen["fault"] not in (BOARD_SILENT, SEAL_MISMATCH):
        return close(layer7.STOP, "no fault that a restart answers was observed: "
                     + seen["why"], condition=seen["condition"] or layer7.UNKNOWN)
    if device not in seen["target"]["ports"]:
        return close(layer7.STOP, f"{device} is not a port of adapter {serial_number}",
                     condition=layer7.AMBIGUOUS)
    recorded = recorded_bitstream()
    have = hashlib.sha256(bitstream.read_bytes()).hexdigest() if bitstream.is_file() else None
    report["bitstream"] = {"path": str(bitstream), "sha256": have, "recorded_sha256": recorded}
    if have is None or have != recorded:
        return close(layer7.STOP, "the bitstream is not the one whose SHA-256 is recorded",
                     condition=layer7.UNKNOWN)
    limit = retry_limit(contract)
    spent, by = _answered(base, seen["run"]["sha256"])
    report["retry"] = {"limit": limit, "spent_before": spent, "answered_by": by}
    if by is not None:
        return close(layer7.STOP, f"this fault was answered by {by}: the record no longer "
                                  "says what the board does now", condition=layer7.STALE)
    if spent >= limit:
        return close(layer7.STOP, f"{spent} restarts are recorded for this fault and the "
                                  f"limit is {limit}: STOP / REPORT",
                     condition=layer7.KNOWN_DISCREPANCY)
    protected, kept = _protected(bitstream), _files(base)
    try:
        port = (open_port or _open)(device)
    except OSError as why:
        return close(layer7.STOP, f"the port could not be had alone: {type(why).__name__}: "
                                  f"{why}", condition=layer7.UNKNOWN)
    u = protocol()
    attempts: list[dict[str, Any]] = report["attempts"]
    raws: dict[str, str] = {}
    done_as: str | None = None
    with port:
        for n in range(spent, limit):
            utc = int(clock())
            at: dict[str, Any] = {"n": n + 1, "utc": utc, "restarted": False}
            attempts.append(at)
            argv = [*LOAD_ARGV, str(bitstream)]
            try:
                loaded = load_run(argv, capture_output=True, text=True, timeout=120,
                                  check=False)
            except (OSError, subprocess.TimeoutExpired) as why:
                at["loader"] = {"argv": argv, "why": f"{type(why).__name__}: {why}"}
                continue
            text = (loaded.stdout or "") + (loaded.stderr or "")
            at["loader"] = {"argv": argv, "returncode": loaded.returncode,
                            "output_sha256": hashlib.sha256(text.encode()).hexdigest()}
            if loaded.returncode != 0:
                continue
            port.reset_input_buffer()
            port.write(b"A")
            port.flush()
            anchor = port.read(u.REPLY["A"])
            at["anchor"] = anchor.hex()
            at["restarted"] = (len(anchor) == u.REPLY["A"] and anchor[:1] == b"A"
                               and anchor[1:37] == bytes(36))
            if not at["restarted"]:
                continue
            if action == RESTART:
                done_as = RESTARTED
                break
            steps = u.scenario(False, utc, UNCERT_NS)
            replies = _script().exchange(port, steps)
            name = time.strftime("portal_board_%Y%m%dT%H%M%SZ.txt", time.gmtime(utc))
            raws[name] = "".join(f"{s['cmd'][:4].hex()} {r.hex()}\n"
                                 for s, r in zip(steps, replies, strict=False))
            at["run"] = {"name": name,
                         "sha256": hashlib.sha256(raws[name].encode()).hexdigest()}
            short = _short(u, steps, replies)
            if short is not None:
                at["verdict"] = BOARD_SILENT
                at["why"] = f"command {short[0]} ({steps[short[0]]['what']}): {short[1]}"
                continue
            bad, count = u.check(steps, replies)
            at["verdict"] = SEAL_MISMATCH if bad else NO_FAULT
            at["mismatches"], at["counts"] = len(bad), count
            if bad:
                at["why"] = bad[0]
                continue
            done_as = RECOVERED
            break
    out = base / (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(attempts[0]["utc"]))
                  + ("-recover" if action == RECOVER else "-restart"))
    (out).mkdir(parents=True, exist_ok=False)
    for name, raw in raws.items():
        (out / name).write_text(raw, encoding="ascii")
    report["evidence"] = str(out)
    report["chain"] = ("new: the keys, PREV, ROOT and anchor before the restart are gone; "
                       "this is not a continuation of the chain the fault was found in")
    if done_as is None:
        result = close(layer7.STOP, f"{len(attempts)} restart(s) this run, {spent} before, "
                                    f"and the limit is {limit}: STOP / REPORT",
                       condition=layer7.KNOWN_DISCREPANCY)
    else:
        result = close(done_as, f"attempt {attempts[-1]['n']} of {limit}")
    (out / "manifest.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    after = _files(base)
    post = {"protected_unchanged": _protected(bitstream) == protected,
            "store_kept": all(after.get(k) == v for k, v in kept.items())}
    if not all(post.values()):
        return {**result, "post": post, "decision": layer7.STOP,
                "condition": layer7.KNOWN_DISCREPANCY,
                "why": "post-action evidence invalid: a protected file or an earlier "
                       "record changed"}
    return {**result, "post": post}


def listed() -> list[dict[str, Any]]:
    """The host's serial adapters, enumerated without opening a port."""
    from serial.tools import list_ports  # pyserial; only a real host needs it

    return [{"device": p.device, "serial_number": p.serial_number, "vid": p.vid, "pid": p.pid}
            for p in list_ports.comports()]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] in (["--recover"], ["--restart"]) and len(args) == 5:
        done = recover(args[1], listed(), args[2], Path(args[3]), Path(args[4]),
                       RECOVER if args[0] == "--recover" else RESTART)
        print(json.dumps(done, indent=1, ensure_ascii=False, default=str))
        return 0 if done["decision"] in (RESTARTED, RECOVERED) else 1
    if len(args) not in (1, 2) or args[0].startswith("--"):
        print((__doc__ or "").split("\n\n")[1])
        return 2
    report = isolate(args[0], listed(), Path(args[1]) if len(args) == 2 else None)
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0 if report["decision"] == NO_FAULT else 1


if __name__ == "__main__":
    raise SystemExit(main())
