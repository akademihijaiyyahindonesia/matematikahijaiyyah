"""Layer 7 on the Portal 8888 slot (src/hijaiyyah/nui/layer7_portal.py).

The owner opened two rows of 7.4 on 3 October 2026 -- reading the board's
identity over JTAG, and ISOLATE_FAULT -- and, by a second decision the same
day, the four rows recovering needs: loading the recorded Portal bitstream
into SRAM, writing the Portal's protocol to the UART after that load,
RESTART_PORTAL and RECOVER_PORTAL, at most three restarts for one fault.

The first half holds isolating to its row: each of the four faults is found
from the source that shows it, a state it cannot observe stops under its own
name, the one command it runs is the detect, and it sends and writes nothing.
The second half holds recovering to its rows: no fault, no action; no byte
before the loader exits 0; the bitstream is the recorded one; three restarts
and no more, counted from the record; and what happened is written outside
the repository.

The board is a small model here that seals with portal8888/ref/portal_ref.py,
so the checker under test (portal_uart.check) is never the thing that produced
what it checks. No test touches a real board, a real port or a real loader.
"""
from __future__ import annotations

import ast
import hashlib
import hmac
import json
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


class Slot:
    """A Portal that works, answering one command's bytes as the wrapper does."""

    def __init__(self) -> None:
        self.key: list[bytes | None] = [None] * 5
        self.locked, self.ctr, self.rnd, self.tick = False, 0, 0, 1000
        self.utc, self.uncert = 0, 0
        self.idx, self.prev, self.tag = [0] * 4, [bytes(32)] * 4, [bytes(32)] * 4
        self.got: set[int] = set()
        self.root = bytes(32)

    def answer(self, cmd: bytes) -> bytes:
        op = cmd[:1]
        ready = self.locked and all(k is not None for k in self.key)
        if op in b"KLT" and op:
            if op == b"K" and not self.locked and self.key[cmd[1]] is None:
                self.key[cmd[1]] = cmd[2:66]
            if op == b"T":
                self.utc, self.uncert = struct.unpack(">II", cmd[1:9])
            self.locked = self.locked or op == b"L"
            ready = self.locked and all(k is not None for k in self.key)
            return bytes([0x53, self.locked << 7 | ready << 6
                          | sum(1 << i for i in range(5) if self.key[i] is not None)])
        if op == b"A":
            return b"A" + struct.pack(">I", self.rnd) + self.root + b"".join(self.tag)
        if op != b"F" or cmd[2:4] == bytes(2):
            return b"?"
        port, frame = cmd[1], cmd[4:]
        if not ready:
            return b"D\x00"
        self.ctr += 1
        if len(frame) > R.MAX_FRAME_BYTES:
            return b"D\x01"
        self.tick += 5000
        st, ver, ip, sport, dport, proto, mac = P.parse(frame)
        body = R.sealed_body(
            dev=R.DEV, port=port, t_sec=self.utc, t_tick=self.tick, t_source=0,
            t_uncert_ns=self.uncert, ctr=self.ctr, status=st, ver=ver, src_ip=ip, sport=sport,
            dport=dport, proto=proto, src_mac=mac if len(mac) == 6 else bytes(6),
            frame_hash=hashlib.sha256(frame).digest(), idx=self.idx[port],
            prev=self.prev[port])
        key = self.key[port]
        assert key is not None
        sealed = R.seal(key, body)
        self.prev[port] = self.tag[port] = sealed
        self.idx[port] += 1
        self.got.add(port)
        if len(self.got) == 4:
            portal = self.key[4]
            assert portal is not None
            self.root = hmac.new(portal, struct.pack(">H", self.rnd) + self.root
                                 + b"".join(self.tag), hashlib.sha256).digest()
            self.rnd, self.got = self.rnd + 1, set()
        return b"R" + body + sealed


def _board(steps: list[dict[str, Any]], utc: int) -> list[bytes]:
    """What a Portal that works answers to the scenario, sealed with portal_ref."""
    slot = Slot()
    return [slot.answer(s["cmd"]) for s in steps]


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


ISOLATING = ("protocol", "detect", "_short", "read_run", "isolate", "listed")


def test_the_isolating_functions_send_load_and_write_nothing() -> None:
    """Read from the call nodes of the functions isolating runs: one `run`,
    inside detect(), and no call that writes, opens a port, loads or removes
    anything. Since the owner's second decision the module also recovers; the
    isolating half must not reach it."""
    source = (ROOT / "src/hijaiyyah/nui/layer7_portal.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert set(ISOLATING) <= set(defs)
    called = [ast.unparse(n.func).rsplit(".", 1)[-1] for name in ISOLATING
              for n in ast.walk(defs[name]) if isinstance(n, ast.Call)]
    assert called.count("run") == 1
    assert not set(called) & {"Popen", "system", "record", "observe", "write_text",
                              "write_bytes", "mkdir", "unlink", "rmtree", "rename", "open",
                              "touch", "Serial", "write", "flush", "recover", "load_run",
                              "_open", "_script", "exchange", "open_port"}
    names = {n.id for name in ISOLATING for n in ast.walk(defs[name])
             if isinstance(n, ast.Name)}
    assert not names & {"LOAD_ARGV", "BITSTREAM", "RECONFIGURE", "WRITE_UART", "RESTART",
                        "RECOVER", "recover", "_open", "_script"}
    for name in ("send_program", "caffeinate", "limactl", "--write-flash", '"-f"'):
        assert name not in source, name
    assert "run" in {ast.unparse(n.func) for n in ast.walk(defs["detect"])
                     if isinstance(n, ast.Call)}


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


# -- RESTART_PORTAL and RECOVER_PORTAL: the owner's second decision of 3 October 2026 ------------

DEVICE = PORTS[1]["device"]
ROWS = (lp.DETECT, lp.ISOLATE, lp.RECONFIGURE, lp.WRITE_UART, lp.RESTART, lp.RECOVER)


class Bench:
    """A board on a bench: a loader that puts a fresh Slot in it, and its port.

    `loads` are the loader's exit codes in turn (the last repeats), `silent`
    the attempts after which the slot answers nothing, `wrong` the attempts
    whose seals it gets wrong. Every load and every write is kept in `events`.
    """

    def __init__(self, loads: tuple[int, ...] = (0,), silent: tuple[int, ...] = (),
                 wrong: tuple[int, ...] = (), held: bool = False) -> None:
        self.loads, self.silent, self.wrong, self.held = loads, silent, wrong, held
        self.slot: Slot | None = None
        self.events: list[tuple[str, Any]] = []
        self.n = 0
        self.buffer = b""
        self.t = int(AT.timestamp()) + 100

    def clock(self) -> float:
        self.t += 7
        return float(self.t)

    def load(self, argv: list[str], **_: Any) -> Any:
        self.n += 1
        code = self.loads[min(self.n, len(self.loads)) - 1]
        self.events.append(("load", argv))
        self.slot = Slot() if code == 0 else None
        return SimpleNamespace(returncode=code, stdout="", stderr="" if code == 0 else "fail")

    def open(self, device: str) -> Any:
        if self.held:
            raise OSError(f"[Errno 35] Could not exclusively lock port {device}")
        self.events.append(("open", device))
        return self

    def __enter__(self) -> Bench:
        return self

    def __exit__(self, *_: Any) -> None:
        self.events.append(("close", None))

    def reset_input_buffer(self) -> None:
        self.buffer = b""

    def flush(self) -> None:
        pass

    def write(self, data: bytes) -> None:
        self.events.append(("write", data[:1]))
        if self.slot is None or self.n in self.silent:
            return
        reply = self.slot.answer(data)
        if self.n in self.wrong and reply[:1] == b"R":
            reply = reply[:-1] + bytes([reply[-1] ^ 1])
        self.buffer += reply

    def read(self, count: int) -> bytes:
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out


@pytest.fixture
def bitstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stand-in bitstream whose SHA-256 is the recorded one for this test."""
    fs = tmp_path / "portal.fs"
    fs.write_bytes(b"not a real bitstream")
    monkeypatch.setattr(lp, "recorded_bitstream",
                        lambda: hashlib.sha256(fs.read_bytes()).hexdigest())
    return fs


def _fault(tmp: Path, kind: str = lp.BOARD_SILENT) -> Path:
    good = _good(tmp)
    if kind == lp.BOARD_SILENT:
        return _record(tmp, [*good[:9], b""])
    sealed = next(i for i, x in enumerate(good) if x[:1] == b"R")
    good[sealed] = good[sealed][:-1] + bytes([good[sealed][-1] ^ 1])
    return _record(tmp, good)


def _recover(tmp: Path, bench: Bench, fs: Path, run: Path | None = None,
             **more: Any) -> dict[str, Any]:
    more.setdefault("detect_run", _detect())
    more.setdefault("now", AT + timedelta(seconds=10))
    more.setdefault("action", lp.RECOVER)
    return lp.recover(SERIAL, more.pop("ports", PORTS), more.pop("device", DEVICE),
                      _fault(tmp) if run is None else run, more.pop("into", tmp / "store"),
                      bitstream=fs, load_run=bench.load, open_port=bench.open,
                      clock=bench.clock, **more)


def test_the_six_rows_are_the_contracts_own() -> None:
    table = l7.authorizations()
    assert all(table[row] == "AUTHORIZED" for row in ROWS)
    assert lp.retry_limit() == 3
    assert lp.LOAD_ARGV == ("openFPGALoader", "-b", "tangnano20k", "-m")


def test_the_recorded_bitstream_is_read_from_its_evidence_page() -> None:
    recorded = lp.recorded_bitstream()
    assert recorded is not None and len(recorded) == 64
    assert recorded in lp.EVIDENCE.read_text(encoding="utf-8")
    assert recorded not in (ROOT / "src/hijaiyyah/nui/layer7_portal.py").read_text()


@pytest.mark.parametrize("kind", [lp.BOARD_SILENT, lp.SEAL_MISMATCH])
def test_a_fault_in_a_recorded_run_is_recovered_and_recorded(tmp_path: Path, bitstream: Path,
                                                             kind: str) -> None:
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, _fault(tmp_path, kind))
    assert r["decision"] == lp.RECOVERED and r["condition"] is None
    assert r["trigger"]["fault"] == kind and len(r["attempts"]) == 1
    at = r["attempts"][0]
    assert at["restarted"] and at["verdict"] == lp.NO_FAULT and at["mismatches"] == 0
    assert at["counts"]["sealed"] == 8
    assert r["post"] == {"protected_unchanged": True, "store_kept": True}
    assert "not a continuation" in r["chain"]
    out = Path(r["evidence"])
    assert out.parent == (tmp_path / "store").resolve() and out.name.endswith("-recover")
    kept = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert kept["decision"] == lp.RECOVERED and kept["attempts"] == r["attempts"]
    raw = out / at["run"]["name"]
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == at["run"]["sha256"]
    # the record it wrote is one ISOLATE_FAULT can read back: no fault now
    again = lp.isolate(SERIAL, PORTS, raw, detect_run=_detect(),
                       now=datetime.fromtimestamp(at["utc"] + 5, tz=timezone.utc))
    assert again["decision"] == lp.NO_FAULT


def test_no_byte_is_written_before_the_loader_has_exited_zero(tmp_path: Path,
                                                              bitstream: Path) -> None:
    bench = Bench()
    _recover(tmp_path, bench, bitstream)
    kinds = [k for k, _ in bench.events]
    assert kinds[:3] == ["open", "load", "write"] and bench.events[2] == ("write", b"A")
    assert bench.events[1] == ("load", ["openFPGALoader", "-b", "tangnano20k", "-m",
                                         str(bitstream)])
    assert kinds[-1] == "close" and kinds.count("load") == 1


def test_a_restart_alone_asks_only_the_anchor(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, action=lp.RESTART)
    assert r["decision"] == lp.RESTARTED and Path(r["evidence"]).name.endswith("-restart")
    assert [e for e in bench.events if e[0] == "write"] == [("write", b"A")]
    assert "run" not in r["attempts"][0]
    assert bytes.fromhex(r["attempts"][0]["anchor"])[1:37] == bytes(36)


@pytest.mark.parametrize("run, condition", [
    (None, l7.UNKNOWN),          # detected, never asked
    ("good", l7.UNKNOWN),        # a run with no fault
    ("stale", l7.STALE),
])
def test_without_an_observed_fault_nothing_is_done(tmp_path: Path, bitstream: Path,
                                                   run: str | None, condition: str) -> None:
    bench = Bench()
    more: dict[str, Any] = {}
    path = _record(tmp_path) if run == "good" else _fault(tmp_path)
    if run == "stale":
        more["now"] = AT + timedelta(seconds=LIMIT + 1)
    if run is None:
        r = lp.recover(SERIAL, PORTS, DEVICE, None, tmp_path / "store",  # type: ignore[arg-type]
                       bitstream=bitstream, load_run=bench.load, open_port=bench.open,
                       detect_run=_detect(), clock=bench.clock)
    else:
        r = _recover(tmp_path, bench, bitstream, path, **more)
    assert (r["decision"], r["condition"]) == (l7.STOP, condition)
    assert bench.events == [] and not (tmp_path / "store").exists()


@pytest.mark.parametrize("ports, detect_run", [
    (PORTS[2:], _detect()),                                   # ADAPTER_ABSENT
    (PORTS, _detect(text="unable to open\n", code=1)),        # BOARD_NOT_DETECTED
])
def test_a_board_that_cannot_be_reached_is_not_restarted(tmp_path: Path, bitstream: Path,
                                                         ports: Any, detect_run: Any) -> None:
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, ports=ports, detect_run=detect_run)
    assert r["decision"] == l7.STOP and r["trigger"]["decision"] == lp.ISOLATED
    assert bench.events == []


@pytest.mark.parametrize("row", ROWS)
def test_without_every_row_nothing_is_done(tmp_path: Path, bitstream: Path, row: str) -> None:
    text = l7.CONTRACT.read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if x.startswith(f"| {row} |"))
    contract = tmp_path / "LAYER7.md"
    contract.write_text(text.replace(line, line.replace("**AUTHORIZED**", "**DENIED**")),
                        encoding="utf-8")
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, contract=contract)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED)
    assert bench.events == []


def test_a_restart_does_not_need_the_recover_row(tmp_path: Path, bitstream: Path) -> None:
    text = l7.CONTRACT.read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if x.startswith(f"| {lp.RECOVER} |"))
    contract = tmp_path / "LAYER7.md"
    contract.write_text(text.replace(line, line.replace("**AUTHORIZED**", "**DENIED**")),
                        encoding="utf-8")
    r = _recover(tmp_path, Bench(), bitstream, contract=contract, action=lp.RESTART)
    assert r["decision"] == lp.RESTARTED


def test_an_action_by_another_name_is_refused(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, action=lp.ISOLATE)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED) and not bench.events


def test_another_bitstream_is_never_loaded(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench()
    other = tmp_path / "other.fs"
    other.write_bytes(b"another design")
    for fs in (other, tmp_path / "absent.fs"):
        r = _recover(tmp_path, bench, fs)
        assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNKNOWN)
        assert r["bitstream"]["sha256"] != r["bitstream"]["recorded_sha256"]
    assert bench.events == []


def test_a_port_of_another_adapter_is_refused(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, device=PORTS[2]["device"])
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.AMBIGUOUS) and not bench.events


def test_a_port_that_is_held_stops_before_the_load(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench(held=True)
    r = _recover(tmp_path, bench, bitstream)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNKNOWN)
    assert "exclusively lock" in r["why"] and bench.events == []


def test_evidence_inside_the_repository_is_refused(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench()
    r = _recover(tmp_path, bench, bitstream, into=ROOT / "portal8888" / "build" / "x")
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED) and not bench.events


def test_a_failed_load_writes_no_byte_and_is_tried_again(tmp_path: Path,
                                                         bitstream: Path) -> None:
    bench = Bench(loads=(1, 0))
    r = _recover(tmp_path, bench, bitstream)
    assert r["decision"] == lp.RECOVERED and [a["n"] for a in r["attempts"]] == [1, 2]
    assert r["attempts"][0]["loader"]["returncode"] == 1 and "anchor" not in r["attempts"][0]
    kinds = [k for k, _ in bench.events]
    assert kinds[:4] == ["open", "load", "load", "write"]


def test_a_loader_that_cannot_run_is_an_attempt_and_no_byte(tmp_path: Path,
                                                            bitstream: Path) -> None:
    bench = Bench()

    def missing(*_: Any, **__: Any) -> Any:
        raise FileNotFoundError("openFPGALoader")

    r = lp.recover(SERIAL, PORTS, DEVICE, _fault(tmp_path), tmp_path / "store",
                   bitstream=bitstream, load_run=missing, open_port=bench.open,
                   detect_run=_detect(), now=AT + timedelta(seconds=10), clock=bench.clock)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.KNOWN_DISCREPANCY)
    assert len(r["attempts"]) == 3 and not [e for e in bench.events if e[0] == "write"]


@pytest.mark.parametrize("bench", [Bench(silent=(1, 2, 3)), Bench(wrong=(1, 2, 3)),
                                   Bench(loads=(1,))])
def test_three_restarts_and_no_more(tmp_path: Path, bitstream: Path, bench: Bench) -> None:
    run = _fault(tmp_path)
    r = _recover(tmp_path, bench, bitstream, run)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.KNOWN_DISCREPANCY)
    assert len(r["attempts"]) == 3 == bench.n and "STOP / REPORT" in r["why"]
    assert (Path(r["evidence"]) / "manifest.json").is_file()
    # the limit is counted from the record: calling again does not load again
    again = _recover(tmp_path, bench, bitstream, run)
    assert (again["decision"], again["condition"]) == (l7.STOP, l7.KNOWN_DISCREPANCY)
    assert again["retry"] == {"limit": 3, "spent_before": 3, "answered_by": None}
    assert bench.n == 3 and again["attempts"] == []


def test_the_third_restart_may_still_recover(tmp_path: Path, bitstream: Path) -> None:
    bench = Bench(silent=(1,), wrong=(2,))
    r = _recover(tmp_path, bench, bitstream)
    assert r["decision"] == lp.RECOVERED and len(r["attempts"]) == 3
    assert [a.get("verdict") for a in r["attempts"]] == [None, lp.SEAL_MISMATCH, lp.NO_FAULT]
    assert r["attempts"][0]["restarted"] is False


def test_a_fault_that_was_answered_is_not_recovered_twice(tmp_path: Path,
                                                          bitstream: Path) -> None:
    bench, run = Bench(), _fault(tmp_path)
    first = _recover(tmp_path, bench, bitstream, run)
    again = _recover(tmp_path, bench, bitstream, run)
    assert first["decision"] == lp.RECOVERED
    assert (again["decision"], again["condition"]) == (l7.STOP, l7.STALE)
    assert again["retry"]["answered_by"] == Path(first["evidence"]).name and bench.n == 1


def test_the_limit_is_the_contracts_number(tmp_path: Path, bitstream: Path) -> None:
    text = l7.CONTRACT.read_text(encoding="utf-8")
    line = "Batas ulang RESTART_PORTAL untuk satu gangguan: 3"
    assert text.count(line) == 1
    for shown, limit in ((line.replace(": 3", ": 1"), 1), ("", 0)):
        contract = tmp_path / f"LAYER7-{limit}.md"
        contract.write_text(text.replace(line, shown), encoding="utf-8")
        bench = Bench(silent=(1, 2, 3))
        r = _recover(tmp_path, bench, bitstream, contract=contract,
                     into=tmp_path / f"store{limit}")
        assert r["decision"] == l7.STOP and bench.n == limit == lp.retry_limit(contract)


def test_an_earlier_record_that_changes_makes_the_evidence_invalid(
        tmp_path: Path, bitstream: Path) -> None:
    store = tmp_path / "store"
    (store / "earlier").mkdir(parents=True)
    kept = store / "earlier" / "note.txt"
    kept.write_text("before\n")

    class Meddling(Bench):
        def load(self, argv: list[str], **more: Any) -> Any:
            kept.write_text("after\n")
            return super().load(argv, **more)

    r = _recover(tmp_path, Meddling(), bitstream)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.KNOWN_DISCREPANCY)
    assert r["post"] == {"protected_unchanged": True, "store_kept": False}


def test_recovering_writes_only_under_its_evidence_directory(tmp_path: Path,
                                                             bitstream: Path) -> None:
    run = _fault(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    r = _recover(tmp_path, Bench(), bitstream, run)
    new = {p for p in tmp_path.rglob("*") if p.is_file()} - set(before)
    assert new and all(Path(r["evidence"]) in p.parents for p in new)
    assert all(p.read_bytes() == data for p, data in before.items())
