#!/usr/bin/env python3
"""
Test fpga/gowin/hijaiyyah_portal8888_gowin_top.v against real hardware over a real port.

    python3 scripts/portal8888_uart_test.py /dev/cu.usbserial-X
    python3 scripts/portal8888_uart_test.py /dev/cu.usbserial-X --pcap capture.pcap
    python3 scripts/portal8888_uart_test.py --replay build     # a recorded run, checked again
    python3 scripts/portal8888_uart_test.py                    # prints the scenario only

The commands and the checker are ref/portal_uart.py's -- the ones the bench
(tb/tb_hijaiyyah_portal8888_gowin_top.v) is judged by -- so a PASS means the
board and the reference agree byte for byte: every sealed body recomputed from
the frame that was sent, every TAG, the per-corner chain, the portal ROOT and
the head anchor recomputed with hmac/hashlib.

The board must have just been loaded or reset: a key slot is write-once and
the lock holds until then, and the scenario's first frame must be dropped as
unprovisioned. The time provisioned is this host's clock, so T_source on the
board is 0 (free-running) and the uncertainty is the one given here.

--pcap adds the Ethernet frames of a classic pcap file (link type 1), in
order, on ports 0..3 in turn, and reads the anchor again after them. A frame
over 9,216 bytes must be dropped.

Every reply byte is written to --out (default build/, which git ignores): the
raw bytes are the evidence, this script's verdict is not.
"""

from __future__ import annotations

import argparse
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "ref"))

import portal_uart as U  # noqa: E402

BAUD = 115200


def pcap_frames(path: Path) -> list[bytes]:
    """The frames of a classic pcap file whose link type is Ethernet."""
    data = path.read_bytes()
    magic = data[:4]
    order = {b"\xd4\xc3\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">",
             b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\x3c\x4d": ">"}.get(magic)
    if order is None:
        raise SystemExit(f"{path}: not a classic pcap file (pcapng is not read)")
    linktype = struct.unpack(order + "I", data[20:24])[0]
    if linktype != 1:
        raise SystemExit(f"{path}: link type {linktype}, not Ethernet (1)")
    out, at = [], 24
    while at + 16 <= len(data):
        incl, orig = struct.unpack(order + "II", data[at + 8:at + 16])
        frame = data[at + 16:at + 16 + incl]
        if len(frame) != incl:
            raise SystemExit(f"{path}: the last packet is cut short")
        if incl != orig:
            raise SystemExit(f"{path}: a packet was captured short ({incl} of {orig} bytes); "
                             "capture with a snap length of at least 9216")
        out.append(frame)
        at += 16 + incl
    return out


def steps_for(utc: int, uncert_ns: int, pcap: Path | None) -> list[dict]:
    steps = U.scenario(False, utc, uncert_ns)
    if pcap is not None:
        for i, frame in enumerate(f for f in pcap_frames(pcap) if f):
            steps.append(dict(what=f"pcap frame {i}, {len(frame)} bytes, on port {i % 4}",
                              cmd=U.cmd_frame(i % 4, frame), port=i % 4, frame=frame,
                              reply="D" if len(frame) > U.R.MAX_FRAME_BYTES else "R"))
        steps.append(dict(what="anchor after the pcap frames", cmd=b"A", reply="A"))
    return steps


def exchange(port, steps: list[dict]) -> list[bytes]:
    """One command, one reply. The reply's first byte says how long it is."""
    replies = []
    for c, s in enumerate(steps):
        port.write(s["cmd"])
        port.flush()
        head = port.read(1)
        if not head or chr(head[0]) not in U.REPLY:
            print(f"command {c} ({s['what']}): no reply" if not head else
                  f"command {c} ({s['what']}): unknown reply type {head.hex()}")
            replies.append(head)
            break
        rest = port.read(U.REPLY[chr(head[0])] - 1)
        replies.append(head + rest)
    return replies


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("port", nargs="?")
    ap.add_argument("--pcap", type=Path)
    ap.add_argument("--replay", type=Path, metavar="DIR",
                    help="check the bench's recorded run in DIR instead of a board")
    ap.add_argument("--uncert-ns", type=int, default=50_000_000,
                    help="uncertainty of this host's clock, provisioned with the time")
    ap.add_argument("--out", type=Path, default=HERE / "build")
    args = ap.parse_args()

    if args.replay is not None:
        steps = U.scenario()
        replies = U.read_replies(args.replay / "portal_top_reply.txt")
        return U.report(*U.check(steps, replies), len(steps))

    utc = int(time.time())
    steps = steps_for(utc, args.uncert_ns, args.pcap)
    if args.port is None:
        for c, s in enumerate(steps):
            print(f"{c:3d}  {len(s['cmd']):5d} bytes -> '{s['reply']}'  {s['what']}")
        return 0

    import serial  # pyserial; only a real port needs it

    with serial.Serial(args.port, BAUD, timeout=5) as port:
        port.reset_input_buffer()
        replies = exchange(port, steps)
    args.out.mkdir(parents=True, exist_ok=True)
    raw = args.out / time.strftime("portal_board_%Y%m%dT%H%M%SZ.txt", time.gmtime(utc))
    raw.write_text("".join(f"{s['cmd'][:4].hex()} {r.hex()}\n" for s, r in zip(steps, replies)))
    print(f"raw replies: {raw}")
    return U.report(*U.check(steps, replies), len(steps))


if __name__ == "__main__":
    raise SystemExit(main())
