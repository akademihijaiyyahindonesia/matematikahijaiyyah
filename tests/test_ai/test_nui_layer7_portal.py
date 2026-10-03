"""Layer 7, ISOLATE_FAULT for the Portal 8888 slot (src/hijaiyyah/nui/layer7_portal.py).

The owner opened two rows of 7.4 on 3 October 2026 -- reading the board's
identity over JTAG, and ISOLATE_FAULT -- and left writing to the UART and
reconfiguring the board DENIED. These tests hold the module to that: each of
the four faults is found from the source that shows it, a state it cannot
observe stops under its own name, the one command it runs is the detect and
nothing else, and it sends and writes nothing.

The recorded runs are made here by a small model of the board that seals with
portal8888/ref/portal_ref.py, so the checker under test (portal_uart.check) is
never the thing that produced what it checks.
"""
from __future__ import annotations

import ast
import hashlib
import hmac
import struct
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import layer5  # noqa: E402
from hijaiyyah.nui import layer7 as l7  # noqa: E402
from hijaiyyah.nui import layer7_portal as lp  # noqa: E402

U = lp.protocol()
R, P = U.R, U.P
SERIAL = "2025030317"
PORTS = [{"device": "/dev/cu.usbserial-20250303170", "serial_number": SERIAL},
         {"device": "/dev/cu.usbserial-20250303171", "serial_number": SERIAL},
         {"device": "/dev/cu.Bluetooth-Incoming-Port", "serial_number": None}]
AT = datetime(2026, 10, 3, 5, 35, 4, tzinfo=timezone.utc)
LIMIT = layer5.load()["freshness"]["stale_after_seconds"]
DETECTED = ("index 0:\n\tidcode 0x81b\n\tmanufacturer Gowin\n\tfamily GW2A\n"
            "\tmodel  GW2A(R)-18(C)\n\tirlength 8\n")


def _detect(text: str = DETECTED, code: int = 0, calls: list[Any] | None = None) -> Any:
    def run(argv: list[str], **_: Any) -> Any:
        if calls is not None:
            calls.append(argv)
        return SimpleNamespace(returncode=code, stdout=text, stderr="")
    return run


def _board(steps: list[dict[str, Any]], utc: int) -> list[bytes]:
    """What a Portal that works answers to the scenario, sealed with portal_ref."""
    key: list[bytes | None] = [None] * 5
    locked, ctr, rnd, tick = False, 0, 0, 1000
    idx, prev, tag = [0] * 4, [bytes(32)] * 4, [bytes(32)] * 4
    got: set[int] = set()
    root = bytes(32)
    out = []
    for s in steps:
        op = s["cmd"][:1]
        if op in b"KLT":
            if op == b"K" and not locked and key[s["slot"]] is None:
                key[s["slot"]] = s["key"]
            locked = locked or op == b"L"
            ready = locked and all(k is not None for k in key)
            out.append(bytes([0x53, locked << 7 | ready << 6
                              | sum(1 << i for i in range(5) if key[i] is not None)]))
        elif op == b"A":
            out.append(b"A" + struct.pack(">I", rnd) + root + b"".join(tag))
        elif s["reply"] == "?":
            out.append(b"?")
        elif not (locked and all(k is not None for k in key)):
            out.append(b"D\x00")
        elif len(s["frame"]) > R.MAX_FRAME_BYTES:
            ctr += 1
            out.append(b"D\x01")
        else:
            ctr, tick, port = ctr + 1, tick + 5000, s["port"]
            st, ver, ip, sport, dport, proto, mac = P.parse(s["frame"])
            body = R.sealed_body(
                dev=R.DEV, port=port, t_sec=utc, t_tick=tick, t_source=0,
                t_uncert_ns=lp.UNCERT_NS, ctr=ctr, status=st, ver=ver, src_ip=ip, sport=sport,
                dport=dport, proto=proto, src_mac=mac if len(mac) == 6 else bytes(6),
                frame_hash=hashlib.sha256(s["frame"]).digest(), idx=idx[port], prev=prev[port])
            sealed = R.seal(key[port], body)
            out.append(b"R" + body + sealed)
            prev[port] = tag[port] = sealed
            idx[port] += 1
            got.add(port)
            if len(got) == 4:
                root = hmac.new(key[4], struct.pack(">H", rnd) + root + b"".join(tag),
                                hashlib.sha256).digest()
                rnd, got = rnd + 1, set()
    return out


def _record(tmp: Path, replies: list[bytes] | None = None, at: datetime = AT) -> Path:
    steps = U.scenario(False, int(at.timestamp()), lp.UNCERT_NS)
    replies = _board(steps, int(at.timestamp())) if replies is None else replies
    path = tmp / at.strftime("portal_board_%Y%m%dT%H%M%SZ.txt")
    path.write_text("".join(f"{s['cmd'][:4].hex()} {r.hex()}\n"
                            for s, r in zip(steps, replies, strict=False)))
    return path


def _good(tmp: Path) -> list[bytes]:
    return _board(U.scenario(False, int(AT.timestamp()), lp.UNCERT_NS), int(AT.timestamp()))


def _isolate(run: Path | None = None, **more: Any) -> dict[str, Any]:
    more.setdefault("detect_run", _detect())
    more.setdefault("now", AT + timedelta(seconds=10))
    return lp.isolate(SERIAL, more.pop("ports", PORTS), run, **more)


def test_the_two_rows_are_the_contracts_own() -> None:
    table = l7.authorizations()
    assert table[lp.ISOLATE] == "AUTHORIZED" and table[lp.DETECT] == "AUTHORIZED"
    assert table["Konfigurasi ulang papan (`openFPGALoader`)"] == "DENIED"


def test_a_working_slot_shows_no_fault(tmp_path: Path) -> None:
    r = _isolate(_record(tmp_path))
    assert r["decision"] == lp.NO_FAULT and r["fault"] is None and r["condition"] is None
    assert r["run"]["counts"]["sealed"] == 8 and r["target"]["ports"] == sorted(
        p["device"] for p in PORTS[:2])


def test_an_adapter_that_is_not_listed_is_the_fault_and_nothing_is_run() -> None:
    calls: list[Any] = []
    r = _isolate(ports=PORTS[2:], detect_run=_detect(calls=calls))
    assert (r["decision"], r["fault"]) == (lp.ISOLATED, lp.ADAPTER_ABSENT)
    assert calls == [] and r["detect"] is None


@pytest.mark.parametrize("run", [
    _detect(text="unable to open ftdi device\n", code=1),
    _detect(text="index 0:\n", code=0),
])
def test_an_fpga_that_does_not_answer_is_the_fault(run: Any) -> None:
    r = _isolate(detect_run=run)
    assert (r["decision"], r["fault"]) == (lp.ISOLATED, lp.BOARD_NOT_DETECTED)


def test_a_loader_that_cannot_run_is_not_a_detected_board() -> None:
    def missing(*_: Any, **__: Any) -> Any:
        raise FileNotFoundError("openFPGALoader")
    r = _isolate(detect_run=missing)
    assert r["fault"] == lp.BOARD_NOT_DETECTED and "FileNotFoundError" in r["detect"]["why"]


def test_another_device_stops_ambiguous_and_is_no_fault_of_this_board() -> None:
    r = _isolate(detect_run=_detect(text=DETECTED.replace("GW2A(R)-18(C)", "GW1N-9C")))
    assert (r["decision"], r["condition"], r["fault"]) == (l7.STOP, l7.AMBIGUOUS, None)


def test_a_detected_board_never_asked_is_unknown_not_silent() -> None:
    r = _isolate(None)
    assert (r["decision"], r["condition"], r["fault"]) == (l7.STOP, l7.UNKNOWN, None)


def test_a_run_that_stops_short_is_a_silent_board(tmp_path: Path) -> None:
    good = _good(tmp_path)
    for replies in ([*good[:9], b""], [*good[:9], good[9][:40]]):
        r = _isolate(_record(tmp_path, replies))
        assert (r["decision"], r["fault"]) == (lp.ISOLATED, lp.BOARD_SILENT)
        assert r["run"]["command"] == 9


def test_a_wrong_seal_is_a_mismatch(tmp_path: Path) -> None:
    good = _good(tmp_path)
    sealed = next(i for i, x in enumerate(good) if x[:1] == b"R")
    good[sealed] = good[sealed][:-1] + bytes([good[sealed][-1] ^ 1])
    r = _isolate(_record(tmp_path, good))
    assert (r["decision"], r["fault"]) == (lp.ISOLATED, lp.SEAL_MISMATCH)
    assert "TAG is not HMAC" in r["why"]


def test_a_wrong_anchor_is_a_mismatch(tmp_path: Path) -> None:
    good = _good(tmp_path)
    anchor = max(i for i, x in enumerate(good) if x[:1] == b"A")
    good[anchor] = good[anchor][:5] + bytes(32) + good[anchor][37:]
    r = _isolate(_record(tmp_path, good))
    assert r["fault"] == lp.SEAL_MISMATCH


def test_an_old_run_is_stale_and_names_no_fault(tmp_path: Path) -> None:
    good = _good(tmp_path)
    path = _record(tmp_path, [*good[:9], b""])
    r = _isolate(path, now=AT + timedelta(seconds=LIMIT + 1))
    assert (r["decision"], r["condition"], r["fault"]) == (l7.STOP, l7.STALE, None)
    assert _isolate(path, now=AT + timedelta(seconds=LIMIT))["fault"] == lp.BOARD_SILENT


def test_a_run_with_captured_frames_is_not_rechecked(tmp_path: Path) -> None:
    path = _record(tmp_path)
    path.write_text(path.read_text() + "46000036 44\n")
    r = _isolate(path)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNKNOWN)


def test_a_file_that_is_no_recorded_run_is_unknown(tmp_path: Path) -> None:
    other = tmp_path / "notes.txt"
    other.write_text("x\n")
    for path in (other, tmp_path / "portal_board_20261003T053504Z.txt"):
        assert _isolate(path)["condition"] == l7.UNKNOWN


@pytest.mark.parametrize("row", [lp.ISOLATE, lp.DETECT])
def test_without_both_rows_nothing_is_run(tmp_path: Path, row: str) -> None:
    text = l7.CONTRACT.read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if x.startswith(f"| {row} |"))
    contract = tmp_path / "LAYER7.md"
    contract.write_text(text.replace(line, line.replace("**AUTHORIZED**", "**DENIED**")),
                        encoding="utf-8")
    calls: list[Any] = []
    r = _isolate(_record(tmp_path), contract=contract, detect_run=_detect(calls=calls))
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED)
    assert calls == [] and r["fault"] is None


def test_no_report_ever_allows_sending(tmp_path: Path) -> None:
    for r in (_isolate(_record(tmp_path)), _isolate(None), _isolate(ports=[])):
        assert r["may_send"] is False


def test_the_one_command_is_the_detect_exactly() -> None:
    calls: list[Any] = []
    _isolate(None, detect_run=_detect(calls=calls))
    assert calls == [["openFPGALoader", "--detect", "-b", "tangnano20k"]]
    assert lp.DETECT_ARGV == tuple(calls[0])


def test_the_source_sends_loads_and_writes_nothing() -> None:
    """Read from the call nodes: one `run`, inside detect(), and no call that
    writes, opens a port or removes anything. No bitstream is named anywhere."""
    source = (ROOT / "src/hijaiyyah/nui/layer7_portal.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = [ast.unparse(n.func).rsplit(".", 1)[-1] for n in ast.walk(tree)
              if isinstance(n, ast.Call)]
    assert called.count("run") == 1
    assert not set(called) & {"Popen", "system", "record", "observe", "write_text",
                              "write_bytes", "mkdir", "unlink", "rmtree", "rename", "open",
                              "touch", "Serial", "write", "flush"}
    for name in (".fs", "\"-m\"", "'-m'", "send_program", "caffeinate", "limactl", "Serial("):
        assert name not in source, name
    detect = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "detect")
    assert "run" in {ast.unparse(n.func) for n in ast.walk(detect) if isinstance(n, ast.Call)}


def test_isolating_has_no_side_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _record(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}

    def refuse(*_: Any, **__: Any) -> Any:
        raise AssertionError("a side effect was attempted")

    for obj, name in ((subprocess, "run"), (subprocess, "Popen"), (layer5, "record"),
                      (Path, "write_text"), (Path, "write_bytes"), (Path, "mkdir"),
                      (Path, "unlink"), (Path, "rename")):
        monkeypatch.setattr(obj, name, refuse)
    r = _isolate(path)
    monkeypatch.undo()
    assert r["decision"] == lp.NO_FAULT
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
