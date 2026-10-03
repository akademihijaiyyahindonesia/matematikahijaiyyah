#!/usr/bin/env python3
"""Canonical Portal 8888 v1 sealed-record layout and simulation vectors.

This is the single source for the 125-byte L1 body.  Every multibyte field is
big-endian (MSB first); L1 v1 deliberately has no LOC field.
"""
from __future__ import annotations

import hashlib
import hmac
import random
import struct
import sys
from pathlib import Path

import packets as P

DEV = b"PORT8888"
BODY_BYTES = 125
MAX_FRAME_BYTES = 9216
KEY_COUNT = 5


def sealed_body(
    *,
    dev: bytes,
    port: int,
    t_sec: int,
    t_tick: int,
    t_source: int,
    t_uncert_ns: int,
    ctr: int,
    status: int,
    ver: int,
    src_ip: bytes,
    sport: int,
    dport: int,
    proto: int,
    src_mac: bytes,
    frame_hash: bytes,
    idx: int,
    prev: bytes,
) -> bytes:
    """Pack the locked v1 order exactly once, using MSB-first integers."""
    if not (len(dev) == 8 and len(src_ip) == 16 and len(src_mac) == 6):
        raise ValueError("invalid fixed-width Portal v1 field")
    if not (len(frame_hash) == 32 and len(prev) == 32):
        raise ValueError("invalid Portal v1 hash field")
    body = b"".join((
        dev,
        struct.pack(">B I I B I Q B B", port, t_sec, t_tick, t_source,
                    t_uncert_ns, ctr, status, ver),
        src_ip,
        struct.pack(">H H B", sport, dport, proto),
        src_mac,
        frame_hash,
        struct.pack(">H", idx),
        prev,
    ))
    if len(body) != BODY_BYTES:
        raise AssertionError(f"Portal v1 body is {len(body)}, not {BODY_BYTES} bytes")
    return body


def seal(key: bytes, body: bytes) -> bytes:
    if len(body) != BODY_BYTES:
        raise ValueError("Portal v1 seals exactly 125 bytes")
    return hmac.new(key, body, hashlib.sha256).digest()


def sample() -> tuple[list[bytes], bytes, dict[str, int | bytes], bytes, bytes]:
    """Return deterministic provisioning, frame, fields, body, and tag."""
    rng = random.Random(8888)
    keys = [rng.randbytes(32) for _ in range(KEY_COUNT)]
    port = 2
    src_mac = bytes.fromhex("001122334455")
    dst_mac = bytes.fromhex("aabbccddeeff")
    src_ip = bytes([203, 0, 113, 99])
    dst_ip = bytes([198, 51, 100, 7])
    # Ethernet (14) + IPv4 (20) + UDP (8) + payload = exactly the v1 limit.
    payload = bytes(i & 0xFF for i in range(MAX_FRAME_BYTES - 14 - 20 - 8))
    frame = P.eth(dst_mac, src_mac, 0x0800) + P.ipv4(src_ip, dst_ip, 17, P.l4(41000, 8888, 17) + payload)
    if len(frame) != MAX_FRAME_BYTES:
        raise AssertionError(f"jumbo vector is {len(frame)}, not {MAX_FRAME_BYTES}")
    status, ver, ip, sport, dport, proto, mac = P.parse(frame)
    fields: dict[str, int | bytes] = {
        "port": port,
        "t_sec": 0x6553F100,
        "t_tick": 1,
        "t_source": 0,
        "t_uncert_ns": 4000,
        "ctr": 1,
        "status": status,
        "ver": ver,
        "src_ip": ip,
        "sport": sport,
        "dport": dport,
        "proto": proto,
        "src_mac": mac,
        "frame_hash": hashlib.sha256(frame).digest(),
        "idx": 0,
        "prev": bytes(32),
    }
    body = sealed_body(dev=DEV, **fields)
    return keys, frame, fields, body, seal(keys[port], body)


def write_vectors(outdir: str) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    keys, frame, fields, body, tag = sample()
    (out / "portal_frame.txt").write_text(
        f"{len(frame)}\n" + "\n".join(f"{byte:02x}" for byte in frame) + "\n"
    )
    lines = [f"KEY {slot} {(key + bytes(32)).hex()}" for slot, key in enumerate(keys)]
    lines.extend((
        f"DEV {DEV.hex()}",
        f"TIME {fields['t_sec']:08x} {fields['t_tick']:08x} {fields['t_source']:02x} {fields['t_uncert_ns']:08x}",
        f"BODY {body.hex()}",
        f"TAG {tag.hex()}",
        f"FRAME_HASH {fields['frame_hash'].hex()}",
    ))
    (out / "portal_v1.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "vec":
        raise SystemExit("usage: portal_ref.py vec <output-directory>")
    write_vectors(sys.argv[2])
