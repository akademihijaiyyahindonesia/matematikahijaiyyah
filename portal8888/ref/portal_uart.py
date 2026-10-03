#!/usr/bin/env python3
"""The UART protocol of fpga/gowin/hijaiyyah_portal8888_gowin_top.v.

One encoder and one checker, used by the bench (tb/tb_hijaiyyah_portal8888_gowin_top.v)
and by the board script (scripts/portal8888_uart_test.py) alike, so the board
is judged by exactly what judged the simulation.

    python3 ref/portal_uart.py vec   <dir> [short]   the commands the bench sends
    python3 ref/portal_uart.py check <dir> [short]   the bench's replies, recomputed

The checker does not trust a reply's own claims. Every sealed body is unpacked,
each observed field is recomputed from the frame that was sent (packets.parse,
SHA-256), the body is packed again by portal_ref.sealed_body, and the tag, the
per-corner PREV chain, the block index, the counter, the portal ROOT and the
head anchor are recomputed with hmac/hashlib from the keys that were
provisioned. The time fields come from the board: with the bench's SOF log
they must equal the clock at the frame's first byte; without it (a real board)
they must be free-running, at or after the provisioned second, and never
go backwards.

What the counter does on a dropped frame is the RTL's measured behaviour, not
a sentence of the contract: a frame that began capture and overflowed still
takes a counter value, a frame that arrived unprovisioned does not.
"""
from __future__ import annotations

import hashlib
import hmac
import random
import struct
import sys
from pathlib import Path

import packets as P
import portal_ref as R

#: bytes in each reply, by its type byte
REPLY = {"S": 2, "R": 1 + R.BODY_BYTES + 32, "D": 2, "A": 1 + 4 + 32 + 4 * 32, "?": 1}
UTC, UNCERT = 0x6553F100, 4000
TPS = 27_000_000
BODY = struct.Struct(">8s B I I B I Q B B 16s H H B 6s 32s H 32s")
FIELDS = ("dev", "port", "t_sec", "t_tick", "t_source", "t_uncert_ns", "ctr", "status",
          "ver", "src_ip", "sport", "dport", "proto", "src_mac", "frame_hash", "idx", "prev")
assert BODY.size == R.BODY_BYTES


def key_block(key: bytes) -> bytes:
    return key + bytes(64 - len(key))


def cmd_key(slot: int, key: bytes) -> bytes:
    return b"K" + bytes([slot]) + key_block(key)


def cmd_time(sec: int, uncert_ns: int) -> bytes:
    return b"T" + struct.pack(">II", sec, uncert_ns)


def cmd_frame(port: int, frame: bytes) -> bytes:
    return b"F" + bytes([port]) + struct.pack(">H", len(frame)) + frame


def keys() -> list[bytes]:
    """The five keys of portal_ref.sample(): corners A..D and the portal."""
    return R.sample()[0]


def frames() -> dict[str, bytes]:
    rng = random.Random(20261003)
    mac = lambda: rng.randbytes(6)  # noqa: E731
    s4, d4 = bytes([203, 0, 113, 9]), bytes([198, 51, 100, 7])
    s6, d6 = rng.randbytes(16), rng.randbytes(16)
    jumbo = R.sample()[1]
    return {
        "v4tcp": P.eth(mac(), mac(), 0x0800) + P.ipv4(s4, d4, 6, P.l4(51515, 22, 6)),
        "v6udp": P.eth(mac(), mac(), 0x86DD)
                 + P.ipv6(s6, d6, 17, P.l4(40000, 8888, 17) + rng.randbytes(31)),
        "vlan4": P.eth(mac(), mac(), 0x0800, vlan=88)
                 + P.ipv4(s4, d4, 17, P.l4(5353, 5353, 17) + rng.randbytes(64)),
        "arp": P.eth(mac(), mac(), 0x0806) + rng.randbytes(28),
        "v4opt": P.eth(mac(), mac(), 0x0800)
                 + P.ipv4(s4, d4, 6, P.l4(443, 50000, 6), opts=rng.randbytes(8)),
        "icmp": P.eth(mac(), mac(), 0x0800) + P.ipv4(s4, d4, 1, rng.randbytes(8)),
        "trunc": (P.eth(mac(), mac(), 0x0800) + P.ipv4(s4, d4, 6, P.l4(1, 2, 6)))[:27],
        "jumbo": jumbo,
        "over": jumbo + b"\x00",
    }


def scenario(short: bool = False, utc: int = UTC, uncert_ns: int = UNCERT) -> list[dict]:
    """The commands, in order, each with the reply type it must draw."""
    f, k = frames(), keys()
    step = lambda what, cmd, reply, **more: dict(what=what, cmd=cmd, reply=reply, **more)  # noqa: E731
    frame = lambda port, name: step(f"frame {name} on port {port}", cmd_frame(port, f[name]),  # noqa: E731
                                    "R", port=port, frame=f[name])
    out = []
    if not short:
        out.append(step("frame before provisioning", cmd_frame(0, f["v4tcp"]), "D",
                        port=0, frame=f["v4tcp"]))
    out += [step(f"key slot {s}", cmd_key(s, k[s]), "S", slot=s, key=k[s]) for s in range(5)]
    out.append(step("lock", b"L", "S"))
    if not short:
        out.append(step("key slot 2 after lock", cmd_key(2, b"\xff" * 64), "S", slot=2,
                        key=b"\xff" * 64))
    out.append(step("time", cmd_time(utc, uncert_ns), "S", utc=utc, uncert_ns=uncert_ns))
    out += [frame(0, "v4tcp"), frame(1, "v6udp"), frame(2, "vlan4"), frame(3, "arp"),
            step("anchor after round 1", b"A", "A")]
    if not short:
        out += [frame(2, "v4opt"), frame(0, "jumbo"),
                step("frame over 9,216 bytes on port 1", cmd_frame(1, f["over"]), "D",
                     port=1, frame=f["over"]),
                frame(1, "icmp"), frame(3, "trunc"),
                step("anchor after round 2", b"A", "A"),
                step("unknown command", b"Z", "?"),
                step("frame of length 0", b"F\x00\x00\x00", "?"),
                step("anchor again", b"A", "A")]
    return out


def write_vectors(outdir: str, short: bool) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    steps = scenario(short)
    lines = [str(len(steps))]
    for s in steps:
        lines.append(f"{REPLY[s['reply']]} {len(s['cmd'])}")
        lines.extend(f"{b:02x}" for b in s["cmd"])
    (out / "portal_top_cmd.txt").write_text("\n".join(lines) + "\n")


def check(steps: list[dict], replies: list[bytes],
          sof: dict[int, tuple[int, int]] | None = None) -> tuple[list[str], dict[str, int]]:
    """Every reply against the model. Returns the mismatches and the counts."""
    bad: list[str] = []
    count = {"sealed": 0, "dropped": 0, "anchors": 0, "status": 0, "refused": 0}
    key: list[bytes | None] = [None] * 5
    locked = False
    utc = uncert = None
    ctr = rnd = 0
    idx, prev, tag = [0] * 4, [bytes(32)] * 4, [bytes(32)] * 4
    got: set[int] = set()
    root = bytes(32)
    last_time = (0, 0)
    if len(replies) != len(steps):
        bad.append(f"{len(replies)} replies for {len(steps)} commands")
    for c, (s, rep) in enumerate(zip(steps, replies)):
        where = f"command {c} ({s['what']})"
        kind = chr(rep[0]) if rep else ""
        provisioned = locked and all(x is not None for x in key)
        op = s["cmd"][:1]
        # what the model says must come back
        if op == b"K":
            if not locked and s["slot"] < 5 and key[s["slot"]] is None:
                key[s["slot"]] = s["key"]
        elif op == b"L":
            locked = True
        elif op == b"T":
            utc, uncert, last_time = s["utc"], s["uncert_ns"], (s["utc"], 0)
        if op in b"KLT":
            provisioned = locked and all(x is not None for x in key)
            want = bytes([0x53, locked << 7 | provisioned << 6
                          | sum(1 << i for i in range(5) if key[i] is not None)])
            count["status"] += 1
            if rep != want:
                bad.append(f"{where}: status {rep.hex()}, expected {want.hex()}")
            continue
        if op == b"A":
            want = b"A" + struct.pack(">I", rnd) + root + b"".join(tag)
            count["anchors"] += 1
            if rep != want:
                bad.append(f"{where}: anchor differs (round {rep[1:5].hex()}, "
                           f"root {rep[5:13].hex()}.., expected round {rnd}, {root[:8].hex()}..)")
            continue
        if s["reply"] == "?":
            count["refused"] += 1
            if rep != b"?":
                bad.append(f"{where}: {rep.hex()}, expected '?'")
            continue
        # a frame
        frame, port = s["frame"], s["port"]
        if not provisioned or len(frame) > R.MAX_FRAME_BYTES:
            over = len(frame) > R.MAX_FRAME_BYTES and provisioned
            ctr += provisioned            # a capture that began took a counter value
            count["dropped"] += 1
            if rep != bytes([0x44, over]):
                bad.append(f"{where}: {rep[:4].hex()}, expected drop with flags {int(over)}")
            continue
        ctr += 1
        if kind != "R" or len(rep) != REPLY["R"]:
            bad.append(f"{where}: reply '{kind}' of {len(rep)} bytes, expected a sealed record")
            continue
        body, mac = rep[1:1 + R.BODY_BYTES], rep[1 + R.BODY_BYTES:]
        b = dict(zip(FIELDS, BODY.unpack(body)))
        st, ver, ip, sport, dport, proto, smac = P.parse(frame)
        want = {"dev": R.DEV, "port": port, "t_source": 0, "ctr": ctr, "status": st,
                "ver": ver, "src_ip": ip, "sport": sport, "dport": dport, "proto": proto,
                "src_mac": smac if len(smac) == 6 else bytes(6),
                "frame_hash": hashlib.sha256(frame).digest(), "idx": idx[port],
                "prev": prev[port]}
        for name, value in want.items():
            if b[name] != value:
                show = lambda v: v.hex() if isinstance(v, bytes) else v  # noqa: E731
                bad.append(f"{where}: {name} = {show(b[name])}, expected {show(value)}")
        now = (b["t_sec"], b["t_tick"])
        if sof is not None:
            if sof.get(c) != now:
                bad.append(f"{where}: sealed time {now}, the clock at the first byte was "
                           f"{sof.get(c)}")
        elif not (utc is not None and b["t_sec"] >= utc and b["t_tick"] < TPS
                  and now > last_time):
            bad.append(f"{where}: sealed time {now} is not after {last_time}")
        if utc is not None and b["t_uncert_ns"] < uncert:
            bad.append(f"{where}: uncertainty {b['t_uncert_ns']} below the provisioned {uncert}")
        last_time = now
        if R.sealed_body(**b) != body:
            bad.append(f"{where}: the body does not pack back to itself")
        if not hmac.compare_digest(R.seal(key[port], body), mac):
            bad.append(f"{where}: TAG is not HMAC(K_{'ABCD'[port]}, body)")
        count["sealed"] += 1
        # the chain moves on what the board sealed, as a verifier's would
        prev[port] = tag[port] = mac
        idx[port] += 1
        got.add(port)
        if len(got) == 4:
            root = hmac.new(key[4], struct.pack(">H", rnd & 0xFFFF) + root + b"".join(tag),
                            hashlib.sha256).digest()
            rnd += 1
            got = set()
    return bad, count


def read_replies(path: Path) -> list[bytes]:
    return [bytes.fromhex(line.strip()) for line in path.read_text().splitlines()]


def read_sof(path: Path) -> dict[int, tuple[int, int]]:
    out = {}
    for line in path.read_text().splitlines():
        c, sec, tick = line.split()
        out[int(c)] = (int(sec, 16), int(tick, 16))
    return out


def report(bad: list[str], count: dict[str, int], commands: int) -> int:
    for line in bad:
        print("MISMATCH", line)
    print(f"portal8888 gowin top: {commands} commands, {count['sealed']} sealed, "
          f"{count['dropped']} dropped, {count['anchors']} anchors, {count['status']} status, "
          f"{count['refused']} refused -> {len(bad)} wrong")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in ("vec", "check") \
            or sys.argv[3:] not in ([], ["short"]):
        raise SystemExit(__doc__.split("\n\n")[2])
    short = sys.argv[3:] == ["short"]
    if sys.argv[1] == "vec":
        write_vectors(sys.argv[2], short)
    else:
        d = Path(sys.argv[2])
        steps = scenario(short)
        bad, count = check(steps, read_replies(d / "portal_top_reply.txt"),
                           read_sof(d / "portal_top_sof.txt"))
        raise SystemExit(report(bad, count, len(steps)))
